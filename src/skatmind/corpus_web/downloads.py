from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Final

from skatmind.learning_corpus_human_evidence_export import (
    build_learning_corpus_human_evidence_export_v1,
    serialize_learning_corpus_human_evidence_export_v1,
)
from skatmind.learning_corpus_strategy_teacher_export import (
    build_learning_corpus_strategy_teacher_evidence_export_v1,
    serialize_learning_corpus_strategy_teacher_evidence_export_v1,
)
from skatmind.learning_corpus_tactical_coaching_export import (
    build_learning_corpus_tactical_cross_game_coaching_export_v1,
    serialize_learning_corpus_tactical_cross_game_coaching_export_v1,
)
from skatmind.learning_corpus_tactical_motif_export import (
    build_learning_corpus_tactical_motif_cross_game_summary_export_v1,
    build_learning_corpus_tactical_motif_evidence_export_v1,
    serialize_learning_corpus_tactical_motif_cross_game_summary_export_v1,
    serialize_learning_corpus_tactical_motif_evidence_export_v1,
)
from skatmind.learning_dataset_v2_export import (
    build_learning_dataset_v2_export_v1,
    serialize_learning_dataset_v2_export_v1,
)
from skatmind.learning_dataset_v2_partition_export import (
    build_learning_dataset_partition_preparation_export_v1,
    serialize_learning_dataset_partition_preparation_export_v1,
)
from skatmind.learning_dataset_v2_summary_export import (
    build_learning_dataset_v2_cross_game_summary_export_v1,
    serialize_learning_dataset_v2_cross_game_summary_export_v1,
)

from .context import LearningCorpusWebContextV1
from .contracts import (
    LearningCorpusPreparedArtifactsV1,
    LearningCorpusTacticalCoachingPreparedArtifactsV1,
    LearningCorpusTacticalPreparedArtifactsV1,
)

LEARNING_CORPUS_PREPARED_DOWNLOAD_KINDS: Final[tuple[str, ...]] = (
    "player_catalog",
    "human_evidence",
    "strategy_teacher_evidence",
    "learning_dataset_v2",
    "known_player_partitions",
    "unseen_player_partitions",
    "cross_game_summary",
)
LEARNING_CORPUS_TACTICAL_PREPARED_DOWNLOAD_KINDS: Final[tuple[str, ...]] = (
    "tactical_motif_evidence",
    "tactical_motif_cross_game_summary",
)
LEARNING_CORPUS_TACTICAL_COACHING_PREPARED_DOWNLOAD_KINDS: Final[
    tuple[str, ...]
] = ("tactical_cross_game_coaching",)
LEARNING_CORPUS_ALL_PREPARED_DOWNLOAD_KINDS: Final[tuple[str, ...]] = (
    *LEARNING_CORPUS_PREPARED_DOWNLOAD_KINDS,
    *LEARNING_CORPUS_TACTICAL_PREPARED_DOWNLOAD_KINDS,
    *LEARNING_CORPUS_TACTICAL_COACHING_PREPARED_DOWNLOAD_KINDS,
)
LEARNING_CORPUS_PREPARED_DOWNLOAD_UNAVAILABLE_REASONS: Final[tuple[str, ...]] = (
    "missing",
    "source_mismatch",
)

_KIND_SUFFIX = {
    "player_catalog": "player-catalog",
    "human_evidence": "human-evidence",
    "strategy_teacher_evidence": "strategy-teacher-evidence",
    "learning_dataset_v2": "learning-dataset-v2",
    "known_player_partitions": "known-player-partitions",
    "unseen_player_partitions": "unseen-player-partitions",
    "cross_game_summary": "cross-game-summary",
    "tactical_motif_evidence": "tactical-motif-evidence",
    "tactical_motif_cross_game_summary": "tactical-motif-cross-game-summary",
    "tactical_cross_game_coaching": "tactical-cross-game-coaching",
}
_UNSAFE_FILENAME_RUN = re.compile(r"[^A-Za-z0-9._-]+")


class LearningCorpusPreparedDownloadUnavailableError(ValueError):
    def __init__(self, reason: str) -> None:
        if reason not in LEARNING_CORPUS_PREPARED_DOWNLOAD_UNAVAILABLE_REASONS:
            raise ValueError("reason must identify a prepared-download failure.")
        self.reason = reason
        super().__init__(reason)


@dataclass(frozen=True, slots=True, kw_only=True)
class LearningCorpusPreparedDownloadV1:
    kind: str
    filename: str
    content: bytes

    def __post_init__(self) -> None:
        if self.kind not in LEARNING_CORPUS_ALL_PREPARED_DOWNLOAD_KINDS:
            raise ValueError("kind must identify one prepared artifact.")
        if (
            not isinstance(self.filename, str)
            or not self.filename
            or not self.filename.endswith(".json")
            or any(separator in self.filename for separator in ("/", "\\"))
            or not self.filename.isascii()
        ):
            raise ValueError("filename must be one ASCII-safe JSON basename.")
        if type(self.content) is not bytes:
            raise ValueError("content must be immutable bytes.")


def build_learning_corpus_artifact_filename_v1(
    *,
    source_id: str,
    artifact_identity: str,
    kind: str,
) -> str:
    if not isinstance(source_id, str):
        raise ValueError("source_id must be text.")
    if (
        not isinstance(artifact_identity, str)
        or len(artifact_identity) != 64
        or any(character not in "0123456789abcdef" for character in artifact_identity)
    ):
        raise ValueError("artifact_identity must be a lowercase SHA-256 value.")
    if kind not in LEARNING_CORPUS_ALL_PREPARED_DOWNLOAD_KINDS:
        raise ValueError("kind must identify one prepared artifact.")
    readable = _UNSAFE_FILENAME_RUN.sub("-", source_id).strip("._-")
    readable = readable[:64].rstrip("._-") or "artifact"
    return f"{readable}-{_KIND_SUFFIX[kind]}-{artifact_identity[:12]}.json"


def _canonical_pretty_json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            allow_nan=False,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")


def _download_value(
    prepared: LearningCorpusPreparedArtifactsV1,
    tactical: LearningCorpusTacticalPreparedArtifactsV1,
    coaching: LearningCorpusTacticalCoachingPreparedArtifactsV1,
    kind: str,
) -> tuple[str, str, bytes]:
    if kind == "player_catalog":
        return (
            prepared.player_catalog.corpus_id,
            prepared.player_catalog.player_catalog_fingerprint,
            _canonical_pretty_json_bytes(prepared.player_catalog.to_dict()),
        )
    if kind == "human_evidence":
        export = build_learning_corpus_human_evidence_export_v1(prepared.human_evidence)
        return (
            prepared.human_evidence.corpus_id,
            export.export_id,
            serialize_learning_corpus_human_evidence_export_v1(export),
        )
    if kind == "strategy_teacher_evidence":
        export = build_learning_corpus_strategy_teacher_evidence_export_v1(
            prepared.strategy_teacher_evidence
        )
        return (
            prepared.strategy_teacher_evidence.corpus_id,
            export.export_id,
            serialize_learning_corpus_strategy_teacher_evidence_export_v1(export),
        )
    if kind == "learning_dataset_v2":
        export = build_learning_dataset_v2_export_v1(prepared.learning_dataset)
        return (
            prepared.dataset_id,
            export.export_id,
            serialize_learning_dataset_v2_export_v1(export),
        )
    if kind in {"known_player_partitions", "unseen_player_partitions"}:
        result = (
            prepared.known_player_partition_result
            if kind == "known_player_partitions"
            else prepared.unseen_player_partition_result
        )
        export = build_learning_dataset_partition_preparation_export_v1(result)
        return (
            prepared.dataset_id,
            export.export_id,
            serialize_learning_dataset_partition_preparation_export_v1(export),
        )
    if kind == "cross_game_summary":
        export = build_learning_dataset_v2_cross_game_summary_export_v1(prepared.cross_game_summary)
        return (
            prepared.dataset_id,
            export.export_id,
            serialize_learning_dataset_v2_cross_game_summary_export_v1(export),
        )
    if kind == "tactical_motif_evidence":
        collection = tactical.tactical_motif_collection
        export = build_learning_corpus_tactical_motif_evidence_export_v1(collection)
        return (
            collection.corpus_id,
            export.export_id,
            serialize_learning_corpus_tactical_motif_evidence_export_v1(export),
        )
    if kind == "tactical_motif_cross_game_summary":
        summary = tactical.tactical_motif_cross_game_summary
        export = build_learning_corpus_tactical_motif_cross_game_summary_export_v1(
            summary
        )
        return (
            summary.corpus_id,
            export.export_id,
            serialize_learning_corpus_tactical_motif_cross_game_summary_export_v1(
                export
            ),
        )
    if kind == "tactical_cross_game_coaching":
        report = coaching.tactical_cross_game_coaching_report
        export = build_learning_corpus_tactical_cross_game_coaching_export_v1(report)
        return (
            report.corpus_id,
            export.export_id,
            serialize_learning_corpus_tactical_cross_game_coaching_export_v1(export),
        )
    raise ValueError("kind must identify one prepared artifact.")


def build_learning_corpus_prepared_download_v1(
    context: LearningCorpusWebContextV1,
    *,
    kind: str,
) -> LearningCorpusPreparedDownloadV1:
    """Serializes one cached artifact without rebuilding any source artifact."""
    if type(context) is not LearningCorpusWebContextV1:
        raise ValueError("context must be an exact LearningCorpusWebContextV1.")
    if kind not in LEARNING_CORPUS_ALL_PREPARED_DOWNLOAD_KINDS:
        raise ValueError("kind must identify one prepared artifact.")
    with context.lock:
        prepared = context.prepared_artifacts
        tactical = context.tactical_prepared_artifacts
        coaching = context.tactical_coaching_prepared_artifacts
        if prepared is None or tactical is None or coaching is None:
            raise LearningCorpusPreparedDownloadUnavailableError("missing")
        store = context.store
        mismatch = (
            store is None
            or context._prepared_store is not store
            or context._prepared_generation != context.generation
            or context._prepared_source_revision != context.strategy_source_store.revision
            or prepared.source_catalog_revision != store.document.catalog.revision
            or prepared.source_catalog_content_fingerprint != store.document.content_fingerprint
            or tactical.source_catalog_revision != store.document.catalog.revision
            or tactical.source_catalog_content_fingerprint
            != store.document.content_fingerprint
            or tactical.player_catalog_fingerprint
            != prepared.player_catalog.player_catalog_fingerprint
            or coaching.source_catalog_revision != store.document.catalog.revision
            or coaching.source_catalog_content_fingerprint
            != store.document.content_fingerprint
            or coaching.player_catalog_fingerprint
            != prepared.player_catalog.player_catalog_fingerprint
            or coaching.strategy_teacher_collection_fingerprint
            != prepared.strategy_teacher_evidence.strategy_teacher_collection_fingerprint
            or coaching.tactical_motif_collection_fingerprint
            != tactical.tactical_motif_collection.tactical_motif_collection_fingerprint
            or coaching.tactical_motif_cross_game_summary_fingerprint
            != (
                tactical.tactical_motif_cross_game_summary
                .tactical_motif_cross_game_summary_fingerprint
            )
        )
        if mismatch:
            raise LearningCorpusPreparedDownloadUnavailableError("source_mismatch")
        source_id, identity, content = _download_value(
            prepared,
            tactical,
            coaching,
            kind,
        )
        return LearningCorpusPreparedDownloadV1(
            kind=kind,
            filename=build_learning_corpus_artifact_filename_v1(
                source_id=source_id,
                artifact_identity=identity,
                kind=kind,
            ),
            content=content,
        )
