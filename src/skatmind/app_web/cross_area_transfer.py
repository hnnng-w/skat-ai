from __future__ import annotations

from dataclasses import dataclass

from skatmind.learning_corpus_strategy_teacher import (
    build_learning_corpus_strategy_teacher_report_source_v1,
)
from skatmind.match_analysis_report_source_export import (
    build_match_analysis_report_source_export_v1,
)

from .learning_frontend import (
    UnifiedLearningContextV1,
    import_report_source_into_unified_learning_v1,
    import_workspace_bytes_into_unified_learning_v1,
)
from .managed_item_contracts import FRONTEND_CROSS_AREA_TRANSFER_VERSION
from .match_frontend import (
    UnifiedMatchContextV1,
    build_unified_match_workspace_download_v1,
    get_unified_match_report_v1,
)

FRONTEND_CROSS_AREA_TRANSFER_OPERATIONS = (
    "match_workspace_to_corpus",
    "match_report_to_corpus",
)


@dataclass(frozen=True, slots=True, kw_only=True)
class FrontendCrossAreaTransferResultV1:
    """Path-free summary of one explicit source-verified cross-area transfer."""

    frontend_cross_area_transfer_version: int = FRONTEND_CROSS_AREA_TRANSFER_VERSION
    operation: str
    status: str
    source_match_id: str
    source_workspace_revision: int
    source_report_id: str | None
    target_corpus_id: str
    target_catalog_revision: int
    message: str

    def __post_init__(self) -> None:
        if self.frontend_cross_area_transfer_version != FRONTEND_CROSS_AREA_TRANSFER_VERSION:
            raise ValueError("frontend_cross_area_transfer_version must equal 1.")
        if self.operation not in FRONTEND_CROSS_AREA_TRANSFER_OPERATIONS:
            raise ValueError("operation must identify one cross-area transfer.")
        for field_name in ("status", "source_match_id", "target_corpus_id", "message"):
            value = getattr(self, field_name)
            if type(value) is not str or not value:
                raise ValueError(f"{field_name} must be non-empty text.")
        if type(self.source_workspace_revision) is not int or self.source_workspace_revision < 0:
            raise ValueError("source_workspace_revision must be non-negative.")
        if self.source_report_id is not None and (
            type(self.source_report_id) is not str or len(self.source_report_id) != 64
        ):
            raise ValueError("source_report_id must be null or one report hash.")
        if type(self.target_catalog_revision) is not int or self.target_catalog_revision < 0:
            raise ValueError("target_catalog_revision must be non-negative.")

    def to_dict(self) -> dict[str, object]:
        return {
            "frontend_cross_area_transfer_version": (
                self.frontend_cross_area_transfer_version
            ),
            "operation": self.operation,
            "status": self.status,
            "source_match_id": self.source_match_id,
            "source_workspace_revision": self.source_workspace_revision,
            "source_report_id": self.source_report_id,
            "target_corpus_id": self.target_corpus_id,
            "target_catalog_revision": self.target_catalog_revision,
            "message": self.message,
        }


def transfer_active_match_workspace_to_corpus_v1(
    source: UnifiedMatchContextV1,
    target: UnifiedLearningContextV1,
    *,
    selection_mode: str,
    same_revision_resolution: str,
    expected_catalog_revision: int,
) -> FrontendCrossAreaTransferResultV1:
    """Copies verified immutable Workspace bytes before entering the Corpus lock."""

    with source.capture.lock:
        workspace = source.capture.workspace
        if workspace is None:
            raise ValueError("Open a managed Match before transferring it.")
        source_match_id = workspace.match_definition.match_id
        source_revision = workspace.revision
        workspace_bytes = build_unified_match_workspace_download_v1(source)
    result = import_workspace_bytes_into_unified_learning_v1(
        target,
        workspace_bytes,
        selection_mode=selection_mode,
        same_revision_resolution=same_revision_resolution,
        expected_catalog_revision=expected_catalog_revision,
    )
    with target.corpus.lock:
        store = target.corpus.store
        if store is None:
            raise RuntimeError("Transferred Corpus unexpectedly has no Store.")
        target_corpus_id = store.document.catalog.corpus_id
        target_revision = store.document.catalog.revision
    return FrontendCrossAreaTransferResultV1(
        operation="match_workspace_to_corpus",
        status=result.status,
        source_match_id=source_match_id,
        source_workspace_revision=source_revision,
        source_report_id=None,
        target_corpus_id=target_corpus_id,
        target_catalog_revision=target_revision,
        message=result.message,
    )


def transfer_active_match_report_to_corpus_v1(
    source: UnifiedMatchContextV1,
    target: UnifiedLearningContextV1,
    *,
    report_id: str,
    match_snapshot_id: str,
) -> FrontendCrossAreaTransferResultV1:
    """Copies one exact eligible Report before entering the Corpus lock."""

    status, report = get_unified_match_report_v1(source, report_id)
    if status != "found" or report is None:
        raise ValueError("The selected Match Report is missing or stale.")
    exported = build_match_analysis_report_source_export_v1(report)
    source_value = exported.report
    source_binding = build_learning_corpus_strategy_teacher_report_source_v1(
        match_snapshot_id=match_snapshot_id,
        report=source_value,
    )
    result = import_report_source_into_unified_learning_v1(
        target,
        source_binding,
    )
    with target.corpus.lock:
        store = target.corpus.store
        if store is None:
            raise RuntimeError("Transferred Corpus unexpectedly has no Store.")
        target_corpus_id = store.document.catalog.corpus_id
        target_revision = store.document.catalog.revision
    return FrontendCrossAreaTransferResultV1(
        operation="match_report_to_corpus",
        status=result.status,
        source_match_id=source_value.match_id,
        source_workspace_revision=source_value.workspace_revision,
        source_report_id=source_value.report_id,
        target_corpus_id=target_corpus_id,
        target_catalog_revision=target_revision,
        message=result.message,
    )
