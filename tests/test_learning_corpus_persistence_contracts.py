import json
import tomllib
from dataclasses import FrozenInstanceError, fields, replace
from pathlib import Path

import pytest
from test_learning_corpus_match_snapshot import _annotated_workspace, _snapshot_for_workspace

import skat_ai
import skat_ai.api.v1 as api_v1
from scripts.validate_generated_outputs_schema import SCENARIOS
from skat_ai.api.v1.contracts import WorkflowV1
from skat_ai.learning_corpus_catalog import (
    build_learning_corpus_catalog_v1,
    build_learning_corpus_current_match_selection_v1,
    build_learning_corpus_match_snapshot_catalog_entry_v1,
    create_empty_learning_corpus_catalog_v1,
)
from skat_ai.learning_corpus_persistence_codec import (
    build_learning_corpus_catalog_persistence_document_v1,
)
from skat_ai.learning_corpus_persistence_contracts import (
    LEARNING_CORPUS_CATALOG_CHANGE_OPERATIONS,
    LEARNING_CORPUS_CATALOG_CHANGE_STATUSES,
    LEARNING_CORPUS_CATALOG_CHANGE_VERSION,
    LEARNING_CORPUS_CATALOG_DOCUMENT_KIND,
    LEARNING_CORPUS_CATALOG_FILENAME,
    LEARNING_CORPUS_CATALOG_FINGERPRINT_POLICY,
    LEARNING_CORPUS_CATALOG_WRITE_POLICY,
    LEARNING_CORPUS_CONFLICT_POLICY,
    LEARNING_CORPUS_CONTENT_FINGERPRINT_POLICY,
    LEARNING_CORPUS_IMPORT_POLICY,
    LEARNING_CORPUS_IMPORT_SELECTION_MODES,
    LEARNING_CORPUS_IMPORT_VERSION,
    LEARNING_CORPUS_LAYOUT_POLICY,
    LEARNING_CORPUS_MATCH_SNAPSHOT_OBJECT_DIRECTORY,
    LEARNING_CORPUS_OBJECT_FILE_SUFFIX,
    LEARNING_CORPUS_OBJECT_WRITE_POLICY,
    LEARNING_CORPUS_OBJECT_WRITE_STATUSES,
    LEARNING_CORPUS_OBJECTS_DIRECTORY,
    LEARNING_CORPUS_ORPHAN_POLICY,
    LEARNING_CORPUS_PERSISTENCE_VERSION,
    LEARNING_CORPUS_RESUME_POLICY,
    LEARNING_CORPUS_SAME_REVISION_RESOLUTIONS,
    LEARNING_CORPUS_SELECTION_UPDATE_POLICY,
    LEARNING_CORPUS_STORE_OPERATION_STATUSES,
    LEARNING_CORPUS_STORE_VERSION,
    LEARNING_CORPUS_WRITE_STATUSES,
    LearningCorpusCatalogChangeResultV1,
    LearningCorpusCatalogPersistenceDocumentV1,
    LearningCorpusCatalogWriteResultV1,
    LearningCorpusStoreResumeResultV1,
    LearningCorpusWorkspaceImportResultV1,
)
from skat_ai.training_dataset import TRAINING_DATASET_SCHEMA_VERSION, TRAINING_TARGET

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _one_snapshot_catalog(revision=1):
    _, snapshot = _snapshot_for_workspace(_annotated_workspace())
    entry = build_learning_corpus_match_snapshot_catalog_entry_v1(snapshot)
    selection = build_learning_corpus_current_match_selection_v1(
        match_id=snapshot.match_id,
        match_snapshot_id=snapshot.match_snapshot_id,
    )
    catalog = build_learning_corpus_catalog_v1(
        corpus_id="corpus-172",
        revision=revision,
        match_snapshots=(entry,),
        current_matches=(selection,),
    )
    return snapshot, catalog


def test_versions_tuples_layout_policies_and_contract_fields_are_exact() -> None:
    assert (
        LEARNING_CORPUS_PERSISTENCE_VERSION,
        LEARNING_CORPUS_STORE_VERSION,
        LEARNING_CORPUS_CATALOG_CHANGE_VERSION,
        LEARNING_CORPUS_IMPORT_VERSION,
    ) == (1, 1, 1, 1)
    assert LEARNING_CORPUS_WRITE_STATUSES == ("saved", "unchanged", "conflict")
    assert LEARNING_CORPUS_OBJECT_WRITE_STATUSES == (
        "saved",
        "unchanged",
        "not_required",
    )
    assert LEARNING_CORPUS_CATALOG_CHANGE_OPERATIONS == (
        "import_match_snapshot",
        "select_current_snapshot",
    )
    assert LEARNING_CORPUS_CATALOG_CHANGE_STATUSES == (
        "applied",
        "unchanged",
        "revision_conflict",
        "resolution_required",
    )
    assert LEARNING_CORPUS_STORE_OPERATION_STATUSES == (
        "applied",
        "unchanged",
        "revision_conflict",
        "persistence_conflict",
        "resolution_required",
    )
    assert LEARNING_CORPUS_IMPORT_SELECTION_MODES == (
        "select_imported",
        "keep_current",
    )
    assert LEARNING_CORPUS_SAME_REVISION_RESOLUTIONS == ("reject", "retain")
    assert LEARNING_CORPUS_CATALOG_DOCUMENT_KIND == "skat_ai_learning_corpus_catalog"
    assert LEARNING_CORPUS_CATALOG_FILENAME == "catalog.json"
    assert LEARNING_CORPUS_OBJECTS_DIRECTORY == "objects"
    assert LEARNING_CORPUS_MATCH_SNAPSHOT_OBJECT_DIRECTORY == (
        "match_workspace_snapshot"
    )
    assert LEARNING_CORPUS_OBJECT_FILE_SUFFIX == ".json"
    assert LEARNING_CORPUS_LAYOUT_POLICY == (
        "explicit_root_catalog_and_content_addressed_objects"
    )
    assert LEARNING_CORPUS_CATALOG_FINGERPRINT_POLICY == (
        "sha256_canonical_learning_corpus_catalog_v1"
    )
    assert LEARNING_CORPUS_CONTENT_FINGERPRINT_POLICY == (
        "sha256_canonical_document_without_content_fingerprint"
    )
    assert LEARNING_CORPUS_CONFLICT_POLICY == (
        "expected_catalog_content_fingerprint_compare_and_swap"
    )
    assert LEARNING_CORPUS_OBJECT_WRITE_POLICY == (
        "immutable_no_clobber_content_addressed_publish"
    )
    assert LEARNING_CORPUS_CATALOG_WRITE_POLICY == (
        "same_directory_temp_file_atomic_replace"
    )
    assert LEARNING_CORPUS_RESUME_POLICY == (
        "strict_catalog_and_referenced_object_validation"
    )
    assert LEARNING_CORPUS_IMPORT_POLICY == (
        "strict_workspace_file_to_immutable_match_snapshot"
    )
    assert LEARNING_CORPUS_ORPHAN_POLICY == (
        "catalog_authoritative_unreferenced_objects_reported_not_deleted"
    )
    assert LEARNING_CORPUS_SELECTION_UPDATE_POLICY == (
        "explicit_select_imported_or_keep_current"
    )
    assert tuple(
        field.name for field in fields(LearningCorpusCatalogPersistenceDocumentV1)
    ) == (
        "learning_corpus_persistence_version",
        "document_kind",
        "catalog_fingerprint",
        "content_fingerprint",
        "catalog",
    )
    assert tuple(field.name for field in fields(LearningCorpusStoreResumeResultV1)) == (
        "learning_corpus_store_version",
        "document",
        "match_snapshots",
        "orphan_match_snapshot_ids",
    )
    assert tuple(field.name for field in fields(LearningCorpusCatalogChangeResultV1)) == (
        "learning_corpus_catalog_change_version",
        "operation",
        "status",
        "relation",
        "selection_mode",
        "same_revision_resolution",
        "match_id",
        "match_snapshot_id",
        "expected_revision",
        "source_revision",
        "current_revision",
        "snapshot_added",
        "selection_changed",
        "previous_current_snapshot_id",
        "current_snapshot_id",
        "catalog",
    )
    assert tuple(field.name for field in fields(LearningCorpusCatalogWriteResultV1)) == (
        "learning_corpus_persistence_version",
        "status",
        "corpus_id",
        "revision",
        "expected_content_fingerprint",
        "existing_content_fingerprint",
        "requested_content_fingerprint",
    )
    assert tuple(field.name for field in fields(LearningCorpusWorkspaceImportResultV1)) == (
        "learning_corpus_import_version",
        "status",
        "selection_mode",
        "same_revision_resolution",
        "classification",
        "catalog_change",
        "object_write_status",
        "catalog_write_status",
        "store",
    )


def test_document_and_store_are_frozen_slotted_defensive_and_path_free() -> None:
    snapshot, catalog = _one_snapshot_catalog()
    document = build_learning_corpus_catalog_persistence_document_v1(catalog)
    store = LearningCorpusStoreResumeResultV1(
        document=document,
        match_snapshots=(snapshot,),
        orphan_match_snapshot_ids=(),
    )
    assert not hasattr(document, "__dict__")
    assert not hasattr(store, "__dict__")
    with pytest.raises(FrozenInstanceError):
        document.content_fingerprint = "0" * 64
    first = store.to_dict()
    first["document"]["catalog"]["revision"] = 999
    assert store.to_dict()["document"]["catalog"]["revision"] == 1
    serialized = json.dumps(store.to_dict())
    assert '"path"' not in serialized
    assert '"timestamp"' not in serialized


def test_write_result_relationships_match_existing_persistence_contracts() -> None:
    requested = "3" * 64
    prior = "2" * 64
    saved = LearningCorpusCatalogWriteResultV1(
        status="saved",
        corpus_id="corpus-172",
        revision=1,
        expected_content_fingerprint=prior,
        existing_content_fingerprint=prior,
        requested_content_fingerprint=requested,
    )
    unchanged = replace(
        saved,
        status="unchanged",
        expected_content_fingerprint=requested,
        existing_content_fingerprint=requested,
    )
    conflict = replace(
        saved,
        status="conflict",
        existing_content_fingerprint=requested,
    )
    assert (saved.status, unchanged.status, conflict.status) == (
        "saved",
        "unchanged",
        "conflict",
    )
    with pytest.raises(ValueError, match="three equal"):
        replace(unchanged, existing_content_fingerprint=prior)


def test_store_rejects_nonreconciling_snapshot_and_unsorted_orphans() -> None:
    snapshot, catalog = _one_snapshot_catalog()
    document = build_learning_corpus_catalog_persistence_document_v1(catalog)
    empty_document = build_learning_corpus_catalog_persistence_document_v1(
        create_empty_learning_corpus_catalog_v1("corpus-172")
    )
    with pytest.raises(ValueError, match="one-for-one"):
        LearningCorpusStoreResumeResultV1(
            document=empty_document,
            match_snapshots=(snapshot,),
            orphan_match_snapshot_ids=(),
        )
    with pytest.raises(ValueError, match="sorted"):
        LearningCorpusStoreResumeResultV1(
            document=document,
            match_snapshots=(snapshot,),
            orphan_match_snapshot_ids=("f" * 64, "0" * 64),
        )


def test_persistence_and_import_remain_private_compatibility_additions_only() -> None:
    assert not hasattr(skat_ai, "LearningCorpusStoreResumeResultV1")
    assert not hasattr(api_v1, "LearningCorpusStoreResumeResultV1")
    assert len(WorkflowV1) == 7
    assert TRAINING_DATASET_SCHEMA_VERSION == 1
    assert TRAINING_TARGET == "actual_card_played"
    assert len(SCENARIOS) == 85
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text())
    assert pyproject["project"]["version"] == "0.15.0"
    assert pyproject["project"]["requires-python"] == ">=3.13"
    assert pyproject["project"]["scripts"] == {"skat-ai": "skat_ai.cli:main"}
    assert len(tuple((PROJECT_ROOT / "schemas").glob("*.schema.json"))) == 63
    assert len(
        tuple((PROJECT_ROOT / "src/skat_ai/schema_resources").glob("*.schema.json"))
    ) == 63
    assert len(tuple((PROJECT_ROOT / "examples").glob("session_*.json"))) == 6
    assert not tuple((PROJECT_ROOT / "schemas").glob("*learning_corpus*.schema.json"))
    assert not tuple((PROJECT_ROOT / "examples").glob("*learning_corpus*.json"))
