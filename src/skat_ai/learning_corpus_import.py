from __future__ import annotations

import os

from skat_ai.learning_corpus_catalog import (
    classify_learning_corpus_match_snapshot_v1,
)
from skat_ai.learning_corpus_catalog_operations import (
    _apply_learning_corpus_match_snapshot_import_v1,
    _build_learning_corpus_import_revision_conflict_v1,
    select_learning_corpus_current_match_snapshot_v1,
)
from skat_ai.learning_corpus_match_snapshot import (
    build_learning_corpus_match_snapshot_v1,
)
from skat_ai.learning_corpus_persistence import (
    load_learning_corpus_directory_v1,
    publish_learning_corpus_match_snapshot_object_v1,
    save_learning_corpus_catalog_v1,
)
from skat_ai.learning_corpus_persistence_codec import (
    build_learning_corpus_catalog_persistence_document_v1,
)
from skat_ai.learning_corpus_persistence_contracts import (
    LEARNING_CORPUS_IMPORT_SELECTION_MODES,
    LEARNING_CORPUS_SAME_REVISION_RESOLUTIONS,
    LearningCorpusCurrentSelectionUpdateResultV1,
    LearningCorpusWorkspaceImportResultV1,
)
from skat_ai.match_workspace_persistence import load_match_workspace_file_v1


def _require_non_negative_integer(value: object, field_name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer.")
    return value


def _require_identifier(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{field_name} must be a non-empty, non-padded string.")
    return value


def _require_fingerprint(value: object, field_name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{field_name} must be a lowercase SHA-256 hexadecimal value.")
    return value


def _require_import_options(selection_mode: object, same_revision_resolution: object) -> None:
    if selection_mode not in LEARNING_CORPUS_IMPORT_SELECTION_MODES:
        raise ValueError(
            f"selection_mode must be one of {list(LEARNING_CORPUS_IMPORT_SELECTION_MODES)}."
        )
    if same_revision_resolution not in LEARNING_CORPUS_SAME_REVISION_RESOLUTIONS:
        raise ValueError(
            "same_revision_resolution must be one of "
            f"{list(LEARNING_CORPUS_SAME_REVISION_RESOLUTIONS)}."
        )


def _import_result(
    *,
    status: str,
    selection_mode: str,
    same_revision_resolution: str,
    classification,
    catalog_change,
    object_write_status: str,
    catalog_write_status: str,
    store,
) -> LearningCorpusWorkspaceImportResultV1:
    return LearningCorpusWorkspaceImportResultV1(
        status=status,
        selection_mode=selection_mode,
        same_revision_resolution=same_revision_resolution,
        classification=classification,
        catalog_change=catalog_change,
        object_write_status=object_write_status,
        catalog_write_status=catalog_write_status,
        store=store,
    )


def import_match_workspace_file_into_learning_corpus_v1(
    root_path: str | os.PathLike[str],
    workspace_file_path: str | os.PathLike[str],
    *,
    expected_catalog_revision: int,
    expected_catalog_content_fingerprint: str,
    selection_mode: str,
    same_revision_resolution: str,
) -> LearningCorpusWorkspaceImportResultV1:
    """Strictly imports one Workspace file through object-before-Catalog writes."""
    expected_revision = _require_non_negative_integer(
        expected_catalog_revision,
        "expected_catalog_revision",
    )
    expected_fingerprint = _require_fingerprint(
        expected_catalog_content_fingerprint,
        "expected_catalog_content_fingerprint",
    )
    _require_import_options(selection_mode, same_revision_resolution)

    source_store = load_learning_corpus_directory_v1(root_path)
    source_document = source_store.document
    source_catalog = source_document.catalog
    if expected_revision != source_catalog.revision:
        change = _build_learning_corpus_import_revision_conflict_v1(
            source_catalog,
            expected_revision=expected_revision,
            selection_mode=selection_mode,
            same_revision_resolution=same_revision_resolution,
        )
        return _import_result(
            status="revision_conflict",
            selection_mode=selection_mode,
            same_revision_resolution=same_revision_resolution,
            classification=None,
            catalog_change=change,
            object_write_status="not_required",
            catalog_write_status="not_required",
            store=source_store,
        )
    if expected_fingerprint != source_document.content_fingerprint:
        return _import_result(
            status="persistence_conflict",
            selection_mode=selection_mode,
            same_revision_resolution=same_revision_resolution,
            classification=None,
            catalog_change=None,
            object_write_status="not_required",
            catalog_write_status="not_required",
            store=source_store,
        )

    workspace_document = load_match_workspace_file_v1(workspace_file_path).document
    snapshot = build_learning_corpus_match_snapshot_v1(workspace_document)
    classification = classify_learning_corpus_match_snapshot_v1(
        source_catalog,
        snapshot,
    )
    change = _apply_learning_corpus_match_snapshot_import_v1(
        source_catalog,
        snapshot,
        expected_revision=expected_revision,
        selection_mode=selection_mode,
        same_revision_resolution=same_revision_resolution,
        classification=classification,
    )
    if change.status != "applied":
        status = change.status
        return _import_result(
            status=status,
            selection_mode=selection_mode,
            same_revision_resolution=same_revision_resolution,
            classification=classification,
            catalog_change=change,
            object_write_status="not_required",
            catalog_write_status="not_required",
            store=source_store,
        )

    object_write_status = "not_required"
    if change.snapshot_added:
        object_write_status = publish_learning_corpus_match_snapshot_object_v1(
            root_path,
            snapshot,
        )
    requested_document = build_learning_corpus_catalog_persistence_document_v1(
        change.catalog
    )
    catalog_write = save_learning_corpus_catalog_v1(
        root_path,
        requested_document,
        expected_content_fingerprint=source_document.content_fingerprint,
    )
    final_store = load_learning_corpus_directory_v1(root_path)
    if catalog_write.status == "conflict":
        return _import_result(
            status="persistence_conflict",
            selection_mode=selection_mode,
            same_revision_resolution=same_revision_resolution,
            classification=classification,
            catalog_change=change,
            object_write_status=object_write_status,
            catalog_write_status="conflict",
            store=final_store,
        )
    return _import_result(
        status="applied",
        selection_mode=selection_mode,
        same_revision_resolution=same_revision_resolution,
        classification=classification,
        catalog_change=change,
        object_write_status=object_write_status,
        catalog_write_status=catalog_write.status,
        store=final_store,
    )


def set_learning_corpus_current_match_snapshot_file_v1(
    root_path: str | os.PathLike[str],
    *,
    match_id: str,
    match_snapshot_id: str,
    expected_catalog_revision: int,
    expected_catalog_content_fingerprint: str,
) -> LearningCorpusCurrentSelectionUpdateResultV1:
    """Persists one explicit Current selection without writing an object file."""
    requested_match_id = _require_identifier(match_id, "match_id")
    requested_snapshot_id = _require_fingerprint(
        match_snapshot_id,
        "match_snapshot_id",
    )
    expected_revision = _require_non_negative_integer(
        expected_catalog_revision,
        "expected_catalog_revision",
    )
    expected_fingerprint = _require_fingerprint(
        expected_catalog_content_fingerprint,
        "expected_catalog_content_fingerprint",
    )
    source_store = load_learning_corpus_directory_v1(root_path)
    source_document = source_store.document
    source_catalog = source_document.catalog

    if expected_revision != source_catalog.revision:
        change = select_learning_corpus_current_match_snapshot_v1(
            source_catalog,
            match_id=requested_match_id,
            match_snapshot_id=requested_snapshot_id,
            expected_revision=expected_revision,
        )
        return LearningCorpusCurrentSelectionUpdateResultV1(
            status="revision_conflict",
            catalog_change=change,
            catalog_write_status="not_required",
            store=source_store,
        )
    if expected_fingerprint != source_document.content_fingerprint:
        return LearningCorpusCurrentSelectionUpdateResultV1(
            status="persistence_conflict",
            catalog_change=None,
            catalog_write_status="not_required",
            store=source_store,
        )

    change = select_learning_corpus_current_match_snapshot_v1(
        source_catalog,
        match_id=requested_match_id,
        match_snapshot_id=requested_snapshot_id,
        expected_revision=expected_revision,
    )
    if change.status == "unchanged":
        return LearningCorpusCurrentSelectionUpdateResultV1(
            status="unchanged",
            catalog_change=change,
            catalog_write_status="not_required",
            store=source_store,
        )
    requested_document = build_learning_corpus_catalog_persistence_document_v1(
        change.catalog
    )
    catalog_write = save_learning_corpus_catalog_v1(
        root_path,
        requested_document,
        expected_content_fingerprint=source_document.content_fingerprint,
    )
    final_store = load_learning_corpus_directory_v1(root_path)
    if catalog_write.status == "conflict":
        return LearningCorpusCurrentSelectionUpdateResultV1(
            status="persistence_conflict",
            catalog_change=change,
            catalog_write_status="conflict",
            store=final_store,
        )
    return LearningCorpusCurrentSelectionUpdateResultV1(
        status="applied",
        catalog_change=change,
        catalog_write_status=catalog_write.status,
        store=final_store,
    )
