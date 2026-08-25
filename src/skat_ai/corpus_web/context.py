from __future__ import annotations

import os
import stat
import threading
from dataclasses import dataclass, field
from pathlib import Path

from skat_ai.learning_corpus_persistence import load_learning_corpus_directory_v1
from skat_ai.learning_corpus_persistence_contracts import (
    LearningCorpusStoreResumeResultV1,
)

from .contracts import (
    LearningCorpusPreparedArtifactsV1,
    LearningCorpusTacticalCoachingPreparedArtifactsV1,
    LearningCorpusTacticalPreparedArtifactsV1,
)
from .source_store import LearningCorpusStrategyTeacherSourceStoreV1


@dataclass(slots=True)
class LearningCorpusWebContextV1:
    """Synchronized state for one explicit private Learning Corpus root."""

    corpus_root: Path
    store: LearningCorpusStoreResumeResultV1 | None
    strategy_source_store: LearningCorpusStrategyTeacherSourceStoreV1 = field(
        default_factory=LearningCorpusStrategyTeacherSourceStoreV1,
        repr=False,
    )
    prepared_artifacts: LearningCorpusPreparedArtifactsV1 | None = field(
        default=None,
        repr=False,
    )
    tactical_prepared_artifacts: LearningCorpusTacticalPreparedArtifactsV1 | None = field(
        default=None,
        repr=False,
    )
    tactical_coaching_prepared_artifacts: (
        LearningCorpusTacticalCoachingPreparedArtifactsV1 | None
    ) = field(default=None, repr=False)
    generation: int = 0
    lock: threading.RLock = field(default_factory=threading.RLock, repr=False)
    _prepared_store: LearningCorpusStoreResumeResultV1 | None = field(
        default=None,
        init=False,
        repr=False,
    )
    _prepared_generation: int | None = field(default=None, init=False, repr=False)
    _prepared_source_revision: int | None = field(
        default=None,
        init=False,
        repr=False,
    )

    def __post_init__(self) -> None:
        if not isinstance(self.corpus_root, Path):
            raise ValueError("corpus_root must be an explicit Path.")
        if self.store is not None and type(self.store) is not LearningCorpusStoreResumeResultV1:
            raise ValueError("store must be null or an exact Learning Corpus Store.")
        if type(self.strategy_source_store) is not LearningCorpusStrategyTeacherSourceStoreV1:
            raise ValueError("strategy_source_store must use the exact bounded store.")
        if type(self.generation) is not int or self.generation < 0:
            raise ValueError("generation must be a non-negative integer.")

    @classmethod
    def open(
        cls,
        root_path: str | os.PathLike[str],
    ) -> LearningCorpusWebContextV1:
        path = Path(root_path).expanduser()
        parent_mode = os.stat(path.parent).st_mode
        if not stat.S_ISDIR(parent_mode):
            raise NotADirectoryError("Learning Corpus parent must be an existing directory.")
        try:
            root_mode = os.stat(path).st_mode
        except FileNotFoundError:
            return cls(corpus_root=path, store=None)
        if not stat.S_ISDIR(root_mode):
            raise NotADirectoryError("Learning Corpus root must be a directory.")
        with os.scandir(path) as scanned:
            if next(scanned, None) is None:
                return cls(corpus_root=path, store=None)
        return cls(
            corpus_root=path,
            store=load_learning_corpus_directory_v1(path),
        )

    def _invalidate_prepared_locked(self) -> None:
        self.prepared_artifacts = None
        self.tactical_prepared_artifacts = None
        self.tactical_coaching_prepared_artifacts = None
        self._prepared_store = None
        self._prepared_generation = None
        self._prepared_source_revision = None

    def _invalidate_prepared_lineage_locked(
        self,
        *,
        store: LearningCorpusStoreResumeResultV1,
        source_revision: int,
        generation: int,
    ) -> None:
        if (
            self._prepared_store is store
            and self._prepared_source_revision == source_revision
            and self._prepared_generation == generation
        ):
            self._invalidate_prepared_locked()

    def invalidate_prepared(self) -> None:
        with self.lock:
            self._invalidate_prepared_locked()

    def source_changed(self) -> None:
        with self.lock:
            self._invalidate_prepared_locked()
            self.generation += 1

    def publish_prepared(
        self,
        artifacts: LearningCorpusPreparedArtifactsV1,
        tactical_artifacts: LearningCorpusTacticalPreparedArtifactsV1,
        tactical_coaching_artifacts: LearningCorpusTacticalCoachingPreparedArtifactsV1,
        *,
        store: LearningCorpusStoreResumeResultV1,
        source_revision: int,
        generation: int,
    ) -> None:
        if type(artifacts) is not LearningCorpusPreparedArtifactsV1:
            raise ValueError("artifacts must be exact Prepared Artifacts.")
        if type(tactical_artifacts) is not LearningCorpusTacticalPreparedArtifactsV1:
            raise ValueError("tactical_artifacts must be exact Tactical Prepared Artifacts.")
        if (
            type(tactical_coaching_artifacts)
            is not LearningCorpusTacticalCoachingPreparedArtifactsV1
        ):
            raise ValueError(
                "tactical_coaching_artifacts must be exact Tactical Coaching Prepared Artifacts."
            )
        if (
            artifacts.source_catalog_revision != tactical_artifacts.source_catalog_revision
            or artifacts.source_catalog_revision
            != tactical_coaching_artifacts.source_catalog_revision
            or artifacts.source_catalog_content_fingerprint
            != tactical_artifacts.source_catalog_content_fingerprint
            or artifacts.source_catalog_content_fingerprint
            != tactical_coaching_artifacts.source_catalog_content_fingerprint
            or artifacts.player_catalog.player_catalog_fingerprint
            != tactical_artifacts.player_catalog_fingerprint
            or artifacts.player_catalog.player_catalog_fingerprint
            != tactical_coaching_artifacts.player_catalog_fingerprint
            or artifacts.strategy_teacher_evidence.strategy_teacher_collection_fingerprint
            != tactical_coaching_artifacts.strategy_teacher_collection_fingerprint
            or tactical_artifacts.tactical_motif_collection.tactical_motif_collection_fingerprint
            != tactical_coaching_artifacts.tactical_motif_collection_fingerprint
            or (
                tactical_artifacts.tactical_motif_cross_game_summary
                .tactical_motif_cross_game_summary_fingerprint
            )
            != tactical_coaching_artifacts.tactical_motif_cross_game_summary_fingerprint
        ):
            raise ValueError("Prepared artifact families must use one exact source.")
        self.prepared_artifacts = artifacts
        self.tactical_prepared_artifacts = tactical_artifacts
        self.tactical_coaching_prepared_artifacts = tactical_coaching_artifacts
        self._prepared_store = store
        self._prepared_source_revision = source_revision
        self._prepared_generation = generation

    def reload(self) -> LearningCorpusStoreResumeResultV1:
        """Strictly loads once and replaces context only after complete success."""
        with self.lock:
            store = load_learning_corpus_directory_v1(self.corpus_root)
            self.store = store
            self._invalidate_prepared_locked()
            self.generation += 1
            return store

    def shutdown(self) -> None:
        with self.lock:
            self.strategy_source_store.clear()
            self._invalidate_prepared_locked()
            self.generation += 1
