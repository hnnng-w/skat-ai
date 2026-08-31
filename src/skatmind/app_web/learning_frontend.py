from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from skatmind.corpus_web.context import LearningCorpusWebContextV1
from skatmind.corpus_web.contracts import LearningCorpusWebResultV1
from skatmind.corpus_web.downloads import (
    LearningCorpusPreparedDownloadV1,
    build_learning_corpus_prepared_download_v1,
)
from skatmind.corpus_web.operations import (
    clear_strategy_teacher_reports_from_learning_corpus_web_v1,
    import_match_workspace_into_learning_corpus_web_v1,
    import_strategy_teacher_report_into_learning_corpus_web_v1,
    initialize_learning_corpus_web_v1,
    reload_learning_corpus_web_v1,
    remove_strategy_teacher_report_from_learning_corpus_web_v1,
    select_current_learning_corpus_snapshot_web_v1,
)
from skatmind.corpus_web.preparation import prepare_learning_corpus_artifacts_web_v1
from skatmind.corpus_web.state import build_learning_corpus_web_state_v1
from skatmind.corpus_web.uploads import LearningCorpusMultipartUploadV1
from skatmind.learning_corpus_strategy_teacher import (
    LearningCorpusStrategyTeacherReportSourceV1,
    build_learning_corpus_strategy_teacher_report_source_v1,
)
from skatmind.match_analysis_report_source_codec import (
    resume_match_analysis_report_source_export_v1,
)

from .managed_item_contracts import DiscoveredManagedItemV1
from .managed_item_import import decode_managed_item_json_object_v1
from .managed_item_storage import (
    build_managed_item_storage_path_v1,
    validate_managed_direct_child_path_v1,
)


@dataclass(slots=True, kw_only=True)
class UnifiedLearningContextV1:
    """One active managed Corpus over the unchanged Corpus operation context."""

    category_root: Path = field(repr=False)
    path: Path = field(repr=False)
    handle: str
    corpus: LearningCorpusWebContextV1 = field(repr=False)
    last_result: LearningCorpusWebResultV1 | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.category_root, Path) or not isinstance(self.path, Path):
            raise ValueError("Managed Corpus paths must be private Paths.")
        if self.path.parent != self.category_root:
            raise ValueError("Managed Corpus must be one direct category child.")
        if type(self.handle) is not str or len(self.handle) != 64:
            raise ValueError("handle must be one opaque managed handle.")
        if type(self.corpus) is not LearningCorpusWebContextV1:
            raise ValueError("corpus must be an exact Learning Corpus Web context.")


def create_unified_learning_corpus_v1(
    category_root: Path,
    *,
    handle: str,
    corpus_id: str,
) -> UnifiedLearningContextV1:
    path = build_managed_item_storage_path_v1(
        category_root,
        family="corpora",
        product_id=corpus_id,
    )
    if os.path.lexists(path):
        raise FileExistsError("A managed Corpus already uses this Product identity.")
    corpus = LearningCorpusWebContextV1.open(path)
    result = initialize_learning_corpus_web_v1(corpus, corpus_id=corpus_id)
    if result.status != "applied" or corpus.store is None:
        raise RuntimeError("New managed Corpus was not initialized exactly once.")
    return UnifiedLearningContextV1(
        category_root=category_root,
        path=path,
        handle=handle,
        corpus=corpus,
        last_result=result,
    )


def open_unified_learning_corpus_v1(
    category_root: Path,
    entry: DiscoveredManagedItemV1,
) -> UnifiedLearningContextV1:
    if entry.summary.family != "corpora" or entry.summary.status != "available":
        raise ValueError("Only one available discovered Corpus can be opened.")
    validate_managed_direct_child_path_v1(
        category_root,
        entry.path,
        expected_kind="directory",
    )
    corpus = LearningCorpusWebContextV1.open(entry.path)
    if (
        corpus.store is None
        or corpus.store.document.catalog.corpus_id
        != entry.summary.semantic_product_id
    ):
        raise ValueError("Managed Corpus identity changed after discovery.")
    return UnifiedLearningContextV1(
        category_root=category_root,
        path=entry.path,
        handle=entry.summary.handle,
        corpus=corpus,
    )


def reload_unified_learning_corpus_v1(
    context: UnifiedLearningContextV1,
) -> LearningCorpusWebResultV1:
    with context.corpus.lock:
        validate_managed_direct_child_path_v1(
            context.category_root,
            context.path,
            expected_kind="directory",
        )
        result = reload_learning_corpus_web_v1(context.corpus)
    context.last_result = result
    return result


def build_unified_learning_state_v1(
    context: UnifiedLearningContextV1,
) -> dict[str, object]:
    with context.corpus.lock:
        validate_managed_direct_child_path_v1(
            context.category_root,
            context.path,
            expected_kind="directory",
        )
        return build_learning_corpus_web_state_v1(context.corpus)


def import_workspace_bytes_into_unified_learning_v1(
    context: UnifiedLearningContextV1,
    workspace_bytes: bytes,
    *,
    selection_mode: str,
    same_revision_resolution: str,
    expected_catalog_revision: int,
) -> LearningCorpusWebResultV1:
    upload = LearningCorpusMultipartUploadV1(
        fields={},
        file_field="workspace_file",
        file_content=workspace_bytes,
    )
    with upload.temporary_file() as raw_path:
        with context.corpus.lock:
            validate_managed_direct_child_path_v1(
                context.category_root,
                context.path,
                expected_kind="directory",
            )
            result = import_match_workspace_into_learning_corpus_web_v1(
                context.corpus,
                Path(raw_path),
                selection_mode=selection_mode,
                same_revision_resolution=same_revision_resolution,
                expected_catalog_revision=expected_catalog_revision,
            )
    context.last_result = result
    return result


def select_unified_learning_current_snapshot_v1(
    context: UnifiedLearningContextV1,
    *,
    match_id: str,
    match_snapshot_id: str,
    expected_catalog_revision: int,
) -> LearningCorpusWebResultV1:
    with context.corpus.lock:
        validate_managed_direct_child_path_v1(
            context.category_root,
            context.path,
            expected_kind="directory",
        )
        result = select_current_learning_corpus_snapshot_web_v1(
            context.corpus,
            match_id=match_id,
            match_snapshot_id=match_snapshot_id,
            expected_catalog_revision=expected_catalog_revision,
        )
    context.last_result = result
    return result


def import_report_source_into_unified_learning_v1(
    context: UnifiedLearningContextV1,
    source: LearningCorpusStrategyTeacherReportSourceV1,
) -> LearningCorpusWebResultV1:
    with context.corpus.lock:
        validate_managed_direct_child_path_v1(
            context.category_root,
            context.path,
            expected_kind="directory",
        )
        result = import_strategy_teacher_report_into_learning_corpus_web_v1(
            context.corpus,
            source,
        )
    context.last_result = result
    return result


def import_report_source_bytes_into_unified_learning_v1(
    context: UnifiedLearningContextV1,
    source_bytes: bytes,
    *,
    match_snapshot_id: str,
) -> LearningCorpusWebResultV1:
    document = decode_managed_item_json_object_v1(source_bytes)
    exported = resume_match_analysis_report_source_export_v1(document)
    source = build_learning_corpus_strategy_teacher_report_source_v1(
        match_snapshot_id=match_snapshot_id,
        report=exported.report,
    )
    return import_report_source_into_unified_learning_v1(context, source)


def remove_unified_learning_report_source_v1(
    context: UnifiedLearningContextV1,
    *,
    source_binding_id: str,
) -> LearningCorpusWebResultV1:
    with context.corpus.lock:
        validate_managed_direct_child_path_v1(
            context.category_root,
            context.path,
            expected_kind="directory",
        )
        result = remove_strategy_teacher_report_from_learning_corpus_web_v1(
            context.corpus,
            source_binding_id=source_binding_id,
        )
    context.last_result = result
    return result


def clear_unified_learning_report_sources_v1(
    context: UnifiedLearningContextV1,
) -> LearningCorpusWebResultV1:
    with context.corpus.lock:
        validate_managed_direct_child_path_v1(
            context.category_root,
            context.path,
            expected_kind="directory",
        )
        result = clear_strategy_teacher_reports_from_learning_corpus_web_v1(
            context.corpus
        )
    context.last_result = result
    return result


def prepare_unified_learning_artifacts_v1(
    context: UnifiedLearningContextV1,
    *,
    dataset_id: str,
    known_player_seed: int,
    unseen_player_seed: int,
    train_weight: int,
    validation_weight: int,
    test_weight: int,
) -> LearningCorpusWebResultV1:
    with context.corpus.lock:
        validate_managed_direct_child_path_v1(
            context.category_root,
            context.path,
            expected_kind="directory",
        )
    result = prepare_learning_corpus_artifacts_web_v1(
        context.corpus,
        dataset_id=dataset_id,
        known_player_seed=known_player_seed,
        unseen_player_seed=unseen_player_seed,
        train_weight=train_weight,
        validation_weight=validation_weight,
        test_weight=test_weight,
    )
    context.last_result = result
    return result


def build_unified_learning_download_v1(
    context: UnifiedLearningContextV1,
    *,
    kind: str,
) -> LearningCorpusPreparedDownloadV1:
    with context.corpus.lock:
        validate_managed_direct_child_path_v1(
            context.category_root,
            context.path,
            expected_kind="directory",
        )
        return build_learning_corpus_prepared_download_v1(context.corpus, kind=kind)
