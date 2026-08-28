import json
from dataclasses import FrozenInstanceError, fields, replace
from inspect import signature

import pytest
from test_session_decision_checkpoint import _checkpoint

from skatmind.session_history_contracts import SessionCheckpointLineageV1
from skatmind.session_persistence_codec import build_session_persistence_document_v1
from skatmind.session_persistence_contracts import (
    SESSION_PERSISTENCE_CHECKPOINT_POLICY,
    SESSION_PERSISTENCE_CONFLICT_POLICY,
    SESSION_PERSISTENCE_CONTENT_FINGERPRINT_POLICY,
    SESSION_PERSISTENCE_DOCUMENT_KIND,
    SESSION_PERSISTENCE_ENCODING,
    SESSION_PERSISTENCE_RESUME_POLICY,
    SESSION_PERSISTENCE_STATE_FINGERPRINT_POLICY,
    SESSION_PERSISTENCE_STATE_POLICY,
    SESSION_PERSISTENCE_VERSION,
    SESSION_PERSISTENCE_WRITE_POLICY,
    SESSION_PERSISTENCE_WRITE_STATUSES,
    SessionPersistenceDocumentV1,
    SessionPersistenceWriteResultV1,
    SessionResumeResultV1,
)


def _document():
    state, _, checkpoint = _checkpoint()
    return build_session_persistence_document_v1(
        state,
        decision_checkpoints=(checkpoint,),
    )


def test_persistence_constants_policies_and_contract_fields_are_exact() -> None:
    assert SESSION_PERSISTENCE_VERSION == 1
    assert SESSION_PERSISTENCE_DOCUMENT_KIND == "skatmind_session"
    assert SESSION_PERSISTENCE_STATE_POLICY == "authoritative_accepted_log_state"
    assert SESSION_PERSISTENCE_CHECKPOINT_POLICY == "caller_supplied_frozen_checkpoints"
    assert SESSION_PERSISTENCE_STATE_FINGERPRINT_POLICY == "sha256_canonical_session_state_v1"
    assert (
        SESSION_PERSISTENCE_CONTENT_FINGERPRINT_POLICY
        == "sha256_canonical_document_without_content_fingerprint"
    )
    assert SESSION_PERSISTENCE_CONFLICT_POLICY == "expected_content_fingerprint_compare_and_swap"
    assert SESSION_PERSISTENCE_WRITE_POLICY == "same_directory_temp_file_atomic_replace"
    assert SESSION_PERSISTENCE_RESUME_POLICY == "strict_parse_fingerprint_replay_and_lineage"
    assert SESSION_PERSISTENCE_ENCODING == "utf-8"
    assert SESSION_PERSISTENCE_WRITE_STATUSES == ("saved", "unchanged", "conflict")
    assert [item.name for item in fields(SessionPersistenceDocumentV1)] == [
        "session_persistence_version",
        "document_kind",
        "state_fingerprint",
        "content_fingerprint",
        "state",
        "decision_checkpoints",
    ]
    assert tuple(signature(SessionPersistenceDocumentV1).parameters) == (
        "session_persistence_version",
        "document_kind",
        "state_fingerprint",
        "content_fingerprint",
        "state",
        "decision_checkpoints",
    )
    assert [item.name for item in fields(SessionResumeResultV1)] == [
        "session_persistence_version",
        "document",
        "checkpoint_lineage",
    ]
    assert [item.name for item in fields(SessionPersistenceWriteResultV1)] == [
        "session_persistence_version",
        "status",
        "session_id",
        "revision",
        "expected_content_fingerprint",
        "existing_content_fingerprint",
        "requested_content_fingerprint",
    ]


def test_persistence_document_is_frozen_slotted_keyword_only_and_defensive() -> None:
    document = _document()
    assert not hasattr(document, "__dict__")
    assert list(document.to_dict()) == [item.name for item in fields(document)]
    assert isinstance(document.decision_checkpoints, tuple)
    first = document.to_dict()
    second = document.to_dict()
    first["state"]["players"][0]["player_label"] = "Changed"
    first["decision_checkpoints"][0]["request"]["document"]["hand"].clear()
    assert second == document.to_dict()
    json.dumps(second)
    with pytest.raises(FrozenInstanceError):
        document.content_fingerprint = "0" * 64
    with pytest.raises(TypeError):
        SessionPersistenceDocumentV1(*document.to_dict().values())


@pytest.mark.parametrize("field_name", ("state_fingerprint", "content_fingerprint"))
@pytest.mark.parametrize("value", (None, "A" * 64, "0" * 63, 1))
def test_document_rejects_invalid_fingerprint_shapes(field_name: str, value: object) -> None:
    document = _document()
    with pytest.raises(ValueError, match=field_name):
        replace(document, **{field_name: value})


@pytest.mark.parametrize("field_name", ("state_fingerprint", "content_fingerprint"))
def test_document_rejects_valid_shaped_wrong_fingerprint_identity(field_name: str) -> None:
    document = _document()
    wrong = "0" * 64 if getattr(document, field_name) != "0" * 64 else "1" * 64
    with pytest.raises(ValueError, match=field_name):
        replace(document, **{field_name: wrong})


def test_document_reconciles_session_ids_rejects_duplicates_and_canonicalizes() -> None:
    document = _document()
    checkpoint = document.decision_checkpoints[0]
    with pytest.raises(ValueError, match="duplicate"):
        replace(document, decision_checkpoints=(checkpoint, checkpoint))
    with pytest.raises(ValueError, match="Session State ID"):
        replace(
            document,
            decision_checkpoints=(replace(checkpoint, session_id="other-session"),),
        )


def test_resume_result_requires_lineage_in_checkpoint_order() -> None:
    document = _document()
    checkpoint = document.decision_checkpoints[0]
    lineage = SessionCheckpointLineageV1(
        relationship="current",
        session_id=document.state.session_id,
        checkpoint_revision=checkpoint.source_revision,
        state_revision=document.state.revision,
    )
    result = SessionResumeResultV1(document=document, checkpoint_lineage=(lineage,))
    assert list(result.to_dict()) == [item.name for item in fields(result)]
    with pytest.raises(ValueError, match="one-for-one"):
        replace(result, checkpoint_lineage=())
    with pytest.raises(ValueError, match="revisions"):
        replace(
            result,
            checkpoint_lineage=(replace(lineage, checkpoint_revision=0),),
        )


def test_write_result_saved_unchanged_and_conflict_relationships_are_exact() -> None:
    requested = "3" * 64
    prior = "2" * 64
    saved_new = SessionPersistenceWriteResultV1(
        status="saved",
        session_id="session-155",
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
    assert list(conflict.to_dict()) == [item.name for item in fields(conflict)]
    assert "path" not in conflict.to_dict()

    with pytest.raises(ValueError, match="expected existing"):
        replace(saved_new, expected_content_fingerprint=prior)
    with pytest.raises(ValueError, match="unchanged"):
        replace(saved_existing, requested_content_fingerprint=prior)
    with pytest.raises(ValueError, match="three equal"):
        replace(unchanged, existing_content_fingerprint=prior)
    with pytest.raises(ValueError, match="different expected"):
        replace(conflict, existing_content_fingerprint=prior)


def test_persistence_contracts_exclude_transport_and_history_edit_metadata() -> None:
    serialized = json.dumps(_document().to_dict())
    forbidden = {
        "file_path",
        "timestamp",
        "host",
        "undo_result",
        "correction_result",
        "removed_suffix",
        "discarded_suffix",
        "redo",
        "search_worlds",
        "simulation_ownership",
        "principal_variation",
        "field_provenance",
    }
    assert all(f'"{field}"' not in serialized for field in forbidden)
