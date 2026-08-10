import copy
import json
from dataclasses import FrozenInstanceError, fields
from pathlib import Path
from types import MappingProxyType
from unittest.mock import patch

import pytest
from jsonschema import Draft202012Validator
from test_historical_game import build_historical_input
from test_session_decision_checkpoint import _checkpoint
from test_session_persistence_codec import _commands
from test_session_transitions import _complete_retrospective_session

import skat_ai.api.v1 as api_v1
import skat_ai.api.v1.session as session
import skat_ai.api.v1.session.execution as session_execution
import skat_ai.session_provenance as session_provenance
from skat_ai.api.v1.session.schema_validation import validate_session_result_document
from skat_ai.errors import (
    SkatAISchemaError,
    SkatAISerializationError,
    SkatAIValidationError,
)
from skat_ai.field_provenance_coverage import enumerate_json_leaf_paths
from skat_ai.session_commands import SetSessionGameMetadataCommandV1

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SESSION_EXPORTS = (
    "PUBLIC_SESSION_API_VERSION",
    "PUBLIC_SESSION_API_NAMESPACE",
    "PUBLIC_SESSION_API_COMPATIBILITY_POLICY",
    "SESSION_API_OPERATIONS",
    "SESSION_FIELD_PROVENANCE_VERSION",
    "SESSION_FIELD_PROVENANCE_DOCUMENT_SCOPE",
    "SessionApiVersionInfoV1",
    "SessionApiOptionsV1",
    "SessionApiResultV1",
    "SessionProvenanceContextV1",
    "SessionFieldProvenanceAttachmentV1",
    "SessionFieldProvenanceBundleV1",
    "get_session_api_version_info_v1",
    "SessionPlayerV1",
    "SessionStateV1",
    "SessionCommandRecordV1",
    "SessionCommandV1",
    "SetSessionGameMetadataCommandV1",
    "RecordSessionDealtCardCommandV1",
    "SetSessionDeclarerCommandV1",
    "SetSessionDeclarationCommandV1",
    "RecordSessionDiscardCommandV1",
    "RecordSessionPlayCommandV1",
    "SetSessionGameEventCommandV1",
    "SetSessionGameEndCommandV1",
    "PromoteSessionToRetrospectiveCommandV1",
    "SetSessionPublicHandCommandV1",
    "SessionValidationDiagnosticV1",
    "SessionExportReadinessV1",
    "SessionValidationResultV1",
    "SessionTransitionResultV1",
    "SessionPositionExportOptionsV1",
    "SessionRequestExportV1",
    "SessionDecisionCheckpointV1",
    "SessionUndoResultV1",
    "SessionCommandCorrectionV1",
    "SessionCorrectionResultV1",
    "SessionCheckpointLineageV1",
    "SessionPersistenceDocumentV1",
    "SessionResumeResultV1",
    "parse_session_command",
    "create_session",
    "apply_session_command",
    "rewind_session",
    "correct_session_command",
    "export_session_position_request",
    "export_session_historical_request",
    "build_session_decision_checkpoint",
    "classify_session_decision_checkpoint",
    "build_session_persistence_document",
    "resume_session_document",
    "serialize_session_result",
    "SESSION_DECISION_OBSERVATION_VERSION",
    "SESSION_CHECKPOINT_REVIEW_EXPORT_VERSION",
    "SessionDecisionObservationV1",
    "SessionCheckpointReviewExportV1",
    "observe_session_decision_checkpoint",
    "export_session_checkpoint_review_request",
    "files",
)


def _players() -> tuple[session.SessionPlayerV1, ...]:
    return (
        session.SessionPlayerV1(
            player_id="player-a",
            player_label="Player A",
            seat="forehand",
        ),
        session.SessionPlayerV1(
            player_id="player-b",
            player_label=None,
            seat="middlehand",
        ),
        session.SessionPlayerV1(
            player_id="player-c",
            player_label=None,
            seat="rearhand",
        ),
    )


def _created_state(*, include_provenance: bool = False) -> session.SessionApiResultV1:
    return session.create_session(
        session_id="public-session",
        players=_players(),
        capture_mode="retrospective",
        options=session.SessionApiOptionsV1(
            include_provenance=include_provenance,
        ),
    )


def _metadata_document(expected_revision: int = 0) -> dict[str, object]:
    return {
        "command_version": 1,
        "kind": "set_game_metadata",
        "expected_revision": expected_revision,
        "game_id": "game-1",
        "played_at": None,
    }


def _position_options() -> session.SessionPositionExportOptionsV1:
    return session.SessionPositionExportOptionsV1(
        sample_count=1,
        random_seed=0,
        use_basic_opponent_strategy=False,
        recommendation_method=None,
        bounded_search_settings=None,
    )


def test_public_session_namespace_and_version_contract_are_exact() -> None:
    assert api_v1.session is session
    assert session.__all__ == SESSION_EXPORTS
    assert len(session.__all__) == 59
    assert session.PUBLIC_SESSION_API_VERSION == 1
    assert session.PUBLIC_SESSION_API_NAMESPACE == "skat_ai.api.v1.session"
    assert session.PUBLIC_SESSION_API_COMPATIBILITY_POLICY == "additive_until_v1_0"
    assert session.SESSION_API_OPERATIONS == (
        "create",
        "apply_command",
        "rewind",
        "correct",
        "export_position",
        "export_historical",
        "build_checkpoint",
        "classify_checkpoint",
        "build_persistence_document",
        "resume_persistence_document",
        "observe_checkpoint",
        "export_checkpoint_review",
    )
    assert not hasattr(session, "SessionProjectionV1")
    assert not hasattr(session, "SessionPersistenceWriteResultV1")
    assert not hasattr(session, "save_session_persistence_file_v1")
    assert not hasattr(session, "load_session_persistence_file_v1")

    info = session.get_session_api_version_info_v1()
    assert not hasattr(info, "__dict__")
    assert [field.name for field in fields(type(info))] == [
        "api_contract_version",
        "public_session_api_version",
        "namespace",
        "compatibility_policy",
        "operations",
        "session_contract_version",
        "session_command_version",
        "transition_engine_version",
        "projection_version",
        "request_export_version",
        "decision_checkpoint_version",
        "history_edit_version",
        "checkpoint_lineage_version",
        "persistence_version",
        "decision_observation_version",
        "checkpoint_review_export_version",
    ]
    assert info.to_dict()["operations"] == list(session.SESSION_API_OPERATIONS)
    with pytest.raises(FrozenInstanceError):
        info.namespace = "changed"


def test_public_session_reexports_preserve_internal_type_identity() -> None:
    from skat_ai.session_commands import SetSessionGameMetadataCommandV1 as InternalCommand
    from skat_ai.session_contracts import SessionPlayerV1 as InternalPlayer
    from skat_ai.session_persistence_contracts import (
        SessionPersistenceDocumentV1 as InternalDocument,
    )

    assert session.SetSessionGameMetadataCommandV1 is InternalCommand
    assert session.SessionPlayerV1 is InternalPlayer
    assert session.SessionPersistenceDocumentV1 is InternalDocument


def test_options_and_result_are_strict_immutable_and_omit_null_provenance() -> None:
    options = session.SessionApiOptionsV1()
    assert options.to_dict() == {
        "validate_output": True,
        "include_provenance": False,
    }
    assert not hasattr(options, "__dict__")
    with pytest.raises(FrozenInstanceError):
        options.validate_output = False
    with pytest.raises(SkatAIValidationError, match="validate_output"):
        session.SessionApiOptionsV1(validate_output=1)
    with pytest.raises(SkatAIValidationError, match="include_provenance"):
        session.SessionApiOptionsV1(include_provenance=0)

    result = _created_state()
    serialized = session.serialize_session_result(result)
    assert serialized == result.to_dict()
    assert "field_provenance" not in serialized
    serialized["value"]["session_id"] = "changed"
    assert result.value.session_id == "public-session"
    with pytest.raises(SkatAISerializationError):
        session.serialize_session_result(result.to_dict())
    with pytest.raises(SkatAIValidationError, match="value"):
        session.SessionApiResultV1(operation="apply_command", value=result.value)


def test_command_parser_uses_strict_schema_and_exact_internal_type() -> None:
    document = _metadata_document()
    command = session.parse_session_command(document)
    assert type(command) is SetSessionGameMetadataCommandV1
    assert command.to_dict() == document
    document["game_id"] = "changed"
    assert command.game_id == "game-1"

    for mutation in (
        lambda value: value.__setitem__("unknown", True),
        lambda value: value.pop("played_at"),
        lambda value: value.__setitem__("kind", "unknown"),
        lambda value: value.__setitem__("expected_revision", -1),
    ):
        invalid = _metadata_document()
        mutation(invalid)
        with pytest.raises(SkatAISchemaError):
            session.parse_session_command(invalid)


def test_command_parser_reconstructs_all_ten_command_kinds() -> None:
    commands = _commands()
    assert len(commands) == 10
    for command in commands:
        parsed = session.parse_session_command(command.to_dict())
        assert type(parsed) is type(command)
        assert parsed == command


def test_create_apply_history_export_persistence_and_resume_facade_parity() -> None:
    created = _created_state()
    assert created.operation == "create"
    assert created.value.revision == 0

    applied = session.apply_session_command(created.value, _metadata_document())
    assert applied.operation == "apply_command"
    assert applied.value.status == "applied"
    state = applied.value.state

    position_export = session.export_session_position_request(state, _position_options())
    historical_export = session.export_session_historical_request(state)
    assert position_export.value.target == "position_analysis"
    assert position_export.value.status == "unavailable"
    assert historical_export.value.target == "historical_game"
    assert historical_export.value.status == "unavailable"

    unchanged = session.correct_session_command(
        state,
        session.SessionCommandCorrectionV1(
            expected_revision=1,
            target_revision=1,
            replacement_command=applied.value.command,
        ),
    )
    assert unchanged.operation == "correct"
    assert unchanged.value.status == "unchanged"

    rewound = session.rewind_session(
        state,
        expected_revision=1,
        target_revision=0,
    )
    assert rewound.operation == "rewind"
    assert rewound.value.status == "applied"
    assert rewound.value.state == created.value

    persistence = session.build_session_persistence_document(state)
    assert persistence.operation == "build_persistence_document"
    original_document = persistence.value.to_dict()
    resumed = session.resume_session_document(original_document)
    assert resumed.operation == "resume_persistence_document"
    assert resumed.value.document == persistence.value
    original_document["state"]["session_id"] = "changed"
    assert resumed.value.document.state.session_id == "public-session"


def test_checkpoint_operations_delegate_to_existing_values() -> None:
    state, position_export, checkpoint = _checkpoint()
    built = session.build_session_decision_checkpoint(
        state=state,
        position_export=position_export,
    )
    assert built.operation == "build_checkpoint"
    assert built.value == checkpoint

    classified = session.classify_session_decision_checkpoint(
        state=state,
        checkpoint=checkpoint,
    )
    assert classified.operation == "classify_checkpoint"
    assert classified.value.relationship == "current"


def test_each_facade_call_invokes_the_matching_operation_once() -> None:
    created = _created_state()
    applied = session.apply_session_command(created.value, _metadata_document())
    state = applied.value.state
    checkpoint_state, checkpoint_export, checkpoint = _checkpoint()
    persistence = session.build_session_persistence_document(state).value
    correction = session.SessionCommandCorrectionV1(
        expected_revision=state.revision,
        target_revision=1,
        replacement_command=applied.value.command,
    )
    options = session.SessionApiOptionsV1(include_provenance=True)
    cases = (
        (
            "create_session_state_v1",
            lambda: session.create_session(
                session_id="call-count",
                players=_players(),
                capture_mode="retrospective",
                options=options,
            ),
        ),
        (
            "apply_session_command_v1",
            lambda: session.apply_session_command(
                state,
                _metadata_document(expected_revision=state.revision),
                options=options,
            ),
        ),
        (
            "rewind_session_state_v1",
            lambda: session.rewind_session(
                state,
                expected_revision=state.revision,
                target_revision=0,
                options=options,
            ),
        ),
        (
            "correct_session_command_v1",
            lambda: session.correct_session_command(
                state,
                correction,
                options=options,
            ),
        ),
        (
            "export_session_position_analysis_request_v1",
            lambda: session.export_session_position_request(
                state,
                _position_options(),
                options=options,
            ),
        ),
        (
            "export_session_historical_game_request_v1",
            lambda: session.export_session_historical_request(
                state,
                options=options,
            ),
        ),
        (
            "build_session_decision_checkpoint_v1",
            lambda: session.build_session_decision_checkpoint(
                state=checkpoint_state,
                position_export=checkpoint_export,
                options=options,
            ),
        ),
        (
            "classify_session_decision_checkpoint_v1",
            lambda: session.classify_session_decision_checkpoint(
                state=checkpoint_state,
                checkpoint=checkpoint,
                options=options,
            ),
        ),
        (
            "build_session_persistence_document_v1",
            lambda: session.build_session_persistence_document(
                state,
                options=options,
            ),
        ),
        (
            "resume_session_document_v1",
            lambda: session.resume_session_document(
                persistence.to_dict(),
                options=options,
            ),
        ),
    )
    for internal_name, invoke in cases:
        internal_operation = getattr(session_execution, internal_name)
        with patch.object(
            session_execution,
            internal_name,
            wraps=internal_operation,
        ) as operation_spy:
            invoke()
        assert operation_spy.call_count == 1, internal_name


def test_default_path_does_not_build_or_redact_provenance(monkeypatch) -> None:
    def unexpected_provenance(**_kwargs):
        raise AssertionError("default path built provenance")

    monkeypatch.setattr(
        session_provenance,
        "build_session_field_provenance_bundle_v1",
        unexpected_provenance,
    )
    assert _created_state().field_provenance is None


def test_opt_in_provenance_is_complete_immutable_and_covers_only_the_value() -> None:
    result = _created_state(include_provenance=True)
    bundle = result.field_provenance
    assert bundle is not None
    assert bundle.operation == "create"
    assert bundle.result.session_context == MappingProxyType(
        {
            "capture_mode": "retrospective",
            "operation": "create",
            "phase": "setup",
            "revision": 0,
            "session_id": "public-session",
        }
    )
    assert bundle.result.coverage_summary["provenance_complete"] is True
    assert bundle.result.coverage_summary["uncovered_paths"] == ()
    assert bundle.result.coverage_summary["overlapping_paths"] == ()
    assert bundle.result.ledger["limitations"] == (
        "private_dependencies_redacted",
    )
    assert all(
        reference["visibility"] != "engine_private"
        for entry in bundle.result.ledger["entries"]
        for reference in entry["source_references"]
    )
    value_leaf_paths = set(enumerate_json_leaf_paths(result.value.to_dict()))
    entry_paths = {
        entry["field_path"] for entry in bundle.result.ledger["entries"]
    }
    assert entry_paths == value_leaf_paths
    assert not any(path.startswith("/field_provenance") for path in entry_paths)
    with pytest.raises(TypeError):
        bundle.result.ledger["status"] = "changed"

    serialized = session.serialize_session_result(result)
    assert serialized["field_provenance"]["operation"] == "create"
    serialized["field_provenance"]["result"]["ledger"]["entries"].clear()
    assert bundle.result.ledger["entries"]


def test_result_rejects_provenance_unrelated_to_its_exact_value() -> None:
    created = _created_state(include_provenance=True)
    genuine = created.field_provenance
    unrelated_attachment = session.SessionFieldProvenanceAttachmentV1(
        attachment_name="session_operation_result",
        document_role="result",
        document_scope="session_operation_value",
        ledger={
            "provenance_version": 1,
            "status": "complete",
            "entries": [],
            "exemptions": [],
            "limitations": [],
        },
        coverage_summary={
            "leaf_path_count": 0,
            "provenanced_path_count": 0,
            "exempted_path_count": 0,
            "uncovered_paths": [],
            "orphaned_entry_paths": [],
            "orphaned_exemption_paths": [],
            "overlapping_paths": [],
            "all_paths_accounted_for": True,
            "provenance_complete": True,
        },
        session_context=genuine.result.session_context,
    )
    with pytest.raises(SkatAIValidationError, match="coverage"):
        session.SessionApiResultV1(
            operation="create",
            value=created.value,
            field_provenance=session.SessionFieldProvenanceBundleV1(
                operation="create",
                result=unrelated_attachment,
            ),
        )

    mismatched_context = dict(genuine.result.session_context)
    mismatched_context["session_id"] = "another-session"
    context_attachment = session.SessionFieldProvenanceAttachmentV1(
        attachment_name="session_operation_result",
        document_role="result",
        document_scope="session_operation_value",
        ledger=genuine.result.ledger,
        coverage_summary=genuine.result.coverage_summary,
        session_context=mismatched_context,
    )
    with pytest.raises(SkatAIValidationError, match="context"):
        session.SessionApiResultV1(
            operation="create",
            value=created.value,
            field_provenance=session.SessionFieldProvenanceBundleV1(
                operation="create",
                result=context_attachment,
            ),
        )


def test_public_redaction_removes_engine_references_without_mutating_internal_ledger(
    monkeypatch,
) -> None:
    original_redaction = (
        session_provenance.redact_field_provenance_ledger_for_public_output
    )
    captured = {}

    def capture_redaction(ledger):
        captured["internal"] = ledger
        redacted = original_redaction(ledger)
        captured["redacted"] = redacted
        return redacted

    monkeypatch.setattr(
        session_provenance,
        "redact_field_provenance_ledger_for_public_output",
        capture_redaction,
    )
    result = _created_state(include_provenance=True)
    internal = captured["internal"]
    redacted = captured["redacted"]
    assert any(
        reference.visibility == "engine_private"
        for entry in internal.entries
        for reference in entry.source_references
    )
    assert internal.limitations == ()
    assert all(
        reference.visibility != "engine_private"
        for entry in redacted.entries
        for reference in entry.source_references
    )
    assert redacted.limitations == ("private_dependencies_redacted",)
    assert result.field_provenance.result.ledger["limitations"] == (
        "private_dependencies_redacted",
    )


def test_provenance_context_tracks_result_state_for_apply_rewind_and_resume() -> None:
    options = session.SessionApiOptionsV1(include_provenance=True)
    created = _created_state(include_provenance=True)
    applied = session.apply_session_command(
        created.value,
        _metadata_document(),
        options=options,
    )
    assert applied.field_provenance.result.session_context["revision"] == 1

    rewound = session.rewind_session(
        applied.value.state,
        expected_revision=1,
        target_revision=0,
        options=options,
    )
    assert rewound.field_provenance.result.session_context["revision"] == 0

    persistence = session.build_session_persistence_document(
        applied.value.state,
        options=options,
    )
    resumed = session.resume_session_document(
        persistence.value.to_dict(),
        options=options,
    )
    assert resumed.field_provenance.result.session_context["revision"] == 1


def test_export_checkpoint_and_lineage_provenance_preserve_information_boundaries() -> None:
    options = session.SessionApiOptionsV1(include_provenance=True)
    state, _, _ = _checkpoint()
    position = session.export_session_position_request(
        state,
        _position_options(),
        options=options,
    )
    assert position.value.status == "available"
    position_entries = position.field_provenance.result.ledger["entries"]
    hand_entries = [
        entry
        for entry in position_entries
        if entry["field_path"].startswith("/request/document/hand/")
    ]
    assert hand_entries
    assert {entry["visibility"] for entry in hand_entries} == {"local_private"}
    assert {entry["perspective_player_id"] for entry in hand_entries} == {
        state.local_player_id
    }

    checkpoint = session.build_session_decision_checkpoint(
        state=state,
        position_export=position.value,
        options=options,
    )
    lineage = session.classify_session_decision_checkpoint(
        state=state,
        checkpoint=checkpoint.value,
        options=options,
    )
    assert checkpoint.field_provenance.result.session_context["revision"] == state.revision
    assert lineage.value.relationship == "current"
    assert lineage.field_provenance.result.session_context["revision"] == state.revision


def test_historical_export_provenance_marks_complete_hands_post_game_only() -> None:
    state = _complete_retrospective_session(build_historical_input())
    result = session.export_session_historical_request(
        state,
        options=session.SessionApiOptionsV1(include_provenance=True),
    )
    assert result.value.status == "available"
    entries = result.field_provenance.result.ledger["entries"]
    hand_entries = [
        entry for entry in entries if "/initial_hand/" in entry["field_path"]
    ]
    assert hand_entries
    assert {entry["visibility"] for entry in hand_entries} == {"post_game_only"}
    assert {entry["available_from"] for entry in hand_entries} == {"game_end"}
    assert {entry["origin"] for entry in hand_entries} == {
        "retrospective_attachment"
    }


def test_promoted_persistence_keeps_frozen_checkpoint_hand_local_private() -> None:
    state, _, checkpoint = _checkpoint()
    promoted = session.apply_session_command(
        state,
        session.PromoteSessionToRetrospectiveCommandV1(
            expected_revision=state.revision,
        ),
    ).value.state
    result = session.build_session_persistence_document(
        promoted,
        decision_checkpoints=(checkpoint,),
        options=session.SessionApiOptionsV1(include_provenance=True),
    )
    entries = result.field_provenance.result.ledger["entries"]
    hand_entries = [
        entry
        for entry in entries
        if "/decision_checkpoints/0/request/document/hand/" in entry["field_path"]
    ]
    assert hand_entries
    assert {entry["visibility"] for entry in hand_entries} == {"local_private"}
    assert {entry["perspective_player_id"] for entry in hand_entries} == {
        checkpoint.acting_player_id
    }


def test_validate_output_false_skips_only_final_session_result_schema(monkeypatch) -> None:
    def unexpected_validation(_document):
        raise AssertionError("final output validation ran")

    monkeypatch.setattr(
        session_execution,
        "validate_session_result_document",
        unexpected_validation,
    )
    result = session.create_session(
        session_id="public-session",
        players=_players(),
        capture_mode="retrospective",
        options=session.SessionApiOptionsV1(validate_output=False),
    )
    assert result.value.revision == 0

    with pytest.raises(SkatAIValidationError):
        session.create_session(
            session_id="",
            players=_players(),
            capture_mode="retrospective",
            options=session.SessionApiOptionsV1(validate_output=False),
        )


def test_session_schema_is_draft_2020_12_strict_packaged_and_byte_identical() -> None:
    authoritative_path = PROJECT_ROOT / "schemas" / "session.schema.json"
    packaged_path = (
        PROJECT_ROOT
        / "src"
        / "skat_ai"
        / "schema_resources"
        / "session.schema.json"
    )
    assert authoritative_path.read_bytes() == packaged_path.read_bytes()
    schema_document = json.loads(authoritative_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema_document)
    assert schema_document["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema_document["$defs"]["session_api_result"]["additionalProperties"] is False
    assert schema_document["$defs"]["session_persistence_document"]["additionalProperties"] is False
    for definition in (
        "set_game_metadata_command",
        "record_dealt_card_command",
        "set_declarer_command",
        "set_declaration_command",
        "record_discard_command",
        "record_play_command",
        "set_game_event_command",
        "set_game_end_command",
        "promote_to_retrospective_command",
        "set_public_hand_command",
        "session_player",
        "session_command_record",
        "diagnostic",
        "export_readiness",
        "validation_result",
        "transition_result",
        "session_state",
        "position_export_options",
        "request_export",
        "decision_checkpoint",
        "undo_result",
        "command_correction",
        "correction_result",
        "checkpoint_lineage",
        "session_persistence_document",
        "resume_result",
        "session_provenance_context",
        "session_provenance_attachment",
        "session_provenance_bundle",
        "session_api_options",
        "session_api_result",
    ):
        assert definition in schema_document["$defs"]


def test_resume_schema_rejects_unknown_nested_fields_before_internal_resume() -> None:
    state = session.apply_session_command(
        _created_state().value,
        _metadata_document(),
    ).value.state
    document = session.build_session_persistence_document(state).value.to_dict()
    invalid = copy.deepcopy(document)
    invalid["state"]["validation"]["unknown"] = True
    with pytest.raises(SkatAISchemaError):
        session.resume_session_document(invalid)


def test_session_result_schema_rejects_status_and_checkpoint_workflow_tampering() -> None:
    created = _created_state()
    applied = session.apply_session_command(created.value, _metadata_document())
    invalid_transition = applied.to_dict()
    invalid_transition["value"]["status"] = "rejected"
    with pytest.raises(SkatAISchemaError):
        validate_session_result_document(invalid_transition)

    state, position_export, _ = _checkpoint()
    checkpoint = session.build_session_decision_checkpoint(
        state=state,
        position_export=position_export,
    ).to_dict()
    checkpoint["value"]["request"]["workflow"] = "historical_game"
    with pytest.raises(SkatAISchemaError):
        validate_session_result_document(checkpoint)
