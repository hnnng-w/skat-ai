import json
from dataclasses import FrozenInstanceError, fields, replace

import pytest
from test_match_workspace_contracts import _definition

from skatmind.match_workspace_contracts import create_match_workspace_v1
from skatmind.match_workspace_persistence_codec import (
    build_match_workspace_persistence_document_v1,
)
from skatmind.match_workspace_persistence_contracts import (
    MATCH_WORKSPACE_CONFLICT_POLICY,
    MATCH_WORKSPACE_CONTENT_FINGERPRINT_POLICY,
    MATCH_WORKSPACE_DOCUMENT_KIND,
    MATCH_WORKSPACE_PERSISTENCE_ENCODING,
    MATCH_WORKSPACE_PERSISTENCE_VERSION,
    MATCH_WORKSPACE_RESUME_POLICY,
    MATCH_WORKSPACE_STATE_FINGERPRINT_POLICY,
    MATCH_WORKSPACE_WRITE_POLICY,
    MATCH_WORKSPACE_WRITE_STATUSES,
    MatchWorkspacePersistenceDocumentV1,
    MatchWorkspaceResumeResultV1,
    MatchWorkspaceWriteResultV1,
)
from skatmind.match_workspace_progress import build_match_workspace_progress_v1


def _document():
    return build_match_workspace_persistence_document_v1(
        create_match_workspace_v1(_definition())
    )


def test_persistence_constants_policies_and_contract_fields_are_exact() -> None:
    assert MATCH_WORKSPACE_PERSISTENCE_VERSION == 1
    assert MATCH_WORKSPACE_DOCUMENT_KIND == "skatmind_match_workspace"
    assert (
        MATCH_WORKSPACE_STATE_FINGERPRINT_POLICY
        == "sha256_canonical_match_workspace_v1"
    )
    assert (
        MATCH_WORKSPACE_CONTENT_FINGERPRINT_POLICY
        == "sha256_canonical_document_without_content_fingerprint"
    )
    assert MATCH_WORKSPACE_CONFLICT_POLICY == (
        "expected_content_fingerprint_compare_and_swap"
    )
    assert MATCH_WORKSPACE_WRITE_POLICY == "same_directory_temp_file_atomic_replace"
    assert MATCH_WORKSPACE_RESUME_POLICY == (
        "strict_parse_fingerprint_validate_and_progress"
    )
    assert MATCH_WORKSPACE_PERSISTENCE_ENCODING == "utf-8"
    assert MATCH_WORKSPACE_WRITE_STATUSES == ("saved", "unchanged", "conflict")
    assert [item.name for item in fields(MatchWorkspacePersistenceDocumentV1)] == [
        "match_workspace_persistence_version",
        "document_kind",
        "workspace_fingerprint",
        "content_fingerprint",
        "workspace",
    ]
    assert [item.name for item in fields(MatchWorkspaceResumeResultV1)] == [
        "match_workspace_persistence_version",
        "document",
        "progress",
    ]
    assert [item.name for item in fields(MatchWorkspaceWriteResultV1)] == [
        "match_workspace_persistence_version",
        "status",
        "match_id",
        "revision",
        "expected_content_fingerprint",
        "existing_content_fingerprint",
        "requested_content_fingerprint",
    ]


def test_persistence_contracts_are_frozen_slotted_keyword_only_and_defensive() -> None:
    document = _document()
    progress = build_match_workspace_progress_v1(document.workspace)
    resumed = MatchWorkspaceResumeResultV1(document=document, progress=progress)
    assert not hasattr(document, "__dict__")
    assert not hasattr(resumed, "__dict__")
    assert list(document.to_dict()) == [item.name for item in fields(document)]
    first = document.to_dict()
    second = document.to_dict()
    first["workspace"]["slots"][0]["slot_kind"] = "passed_deal"
    first["workspace"]["match_definition"]["source"]["source_title"] = "Changed"
    assert second == document.to_dict()
    json.dumps(resumed.to_dict())
    with pytest.raises(FrozenInstanceError):
        document.content_fingerprint = "0" * 64
    with pytest.raises(TypeError):
        MatchWorkspacePersistenceDocumentV1(*document.to_dict().values())


@pytest.mark.parametrize("field_name", ("workspace_fingerprint", "content_fingerprint"))
@pytest.mark.parametrize("value", (None, "A" * 64, "0" * 63, 1))
def test_document_rejects_invalid_fingerprint_shapes(
    field_name: str,
    value: object,
) -> None:
    with pytest.raises(ValueError, match=field_name):
        replace(_document(), **{field_name: value})


@pytest.mark.parametrize("field_name", ("workspace_fingerprint", "content_fingerprint"))
def test_document_rejects_valid_shaped_wrong_fingerprint_identity(
    field_name: str,
) -> None:
    document = _document()
    wrong = "0" * 64 if getattr(document, field_name) != "0" * 64 else "1" * 64
    with pytest.raises(ValueError, match=field_name):
        replace(document, **{field_name: wrong})


def test_resume_result_requires_progress_for_the_exact_revision() -> None:
    document = _document()
    progress = build_match_workspace_progress_v1(document.workspace)
    result = MatchWorkspaceResumeResultV1(document=document, progress=progress)
    assert list(result.to_dict()) == [item.name for item in fields(result)]
    with pytest.raises(ValueError, match="revision"):
        replace(result, progress=replace(progress, revision=1))


def test_write_result_saved_unchanged_and_conflict_relationships_are_exact() -> None:
    requested = "3" * 64
    prior = "2" * 64
    saved_new = MatchWorkspaceWriteResultV1(
        status="saved",
        match_id="match-163",
        revision=0,
        expected_content_fingerprint=None,
        existing_content_fingerprint=None,
        requested_content_fingerprint=requested,
    )
    saved_existing = replace(
        saved_new,
        expected_content_fingerprint=prior,
        existing_content_fingerprint=prior,
    )
    unchanged = replace(
        saved_new,
        status="unchanged",
        expected_content_fingerprint=requested,
        existing_content_fingerprint=requested,
    )
    conflict = replace(
        saved_new,
        status="conflict",
        expected_content_fingerprint=prior,
        existing_content_fingerprint=requested,
    )
    assert [
        saved_new.status,
        saved_existing.status,
        unchanged.status,
        conflict.status,
    ] == ["saved", "saved", "unchanged", "conflict"]
    assert "path" not in conflict.to_dict()
    with pytest.raises(ValueError, match="expected existing"):
        replace(saved_new, expected_content_fingerprint=prior)
    with pytest.raises(ValueError, match="unchanged"):
        replace(saved_existing, requested_content_fingerprint=prior)
    with pytest.raises(ValueError, match="three equal"):
        replace(unchanged, existing_content_fingerprint=prior)
    with pytest.raises(ValueError, match="different expected"):
        replace(conflict, existing_content_fingerprint=prior)


def test_persistence_contracts_exclude_transport_analysis_and_materialization() -> None:
    serialized = json.dumps(_document().to_dict())
    forbidden = {
        "file_path",
        "timestamp",
        "host",
        "progress",
        "search_worlds",
        "simulation_ownership",
        "analysis_result",
        "field_provenance",
        "historical_game_input",
        "fixed_three_player_historical_list_input",
    }
    assert all(f'"{field}"' not in serialized for field in forbidden)
