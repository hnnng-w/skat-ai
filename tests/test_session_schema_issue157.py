import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from test_public_session_files import _document
from test_session_decision_observation import _observed

from skatmind.api.v1.session.contracts import SessionApiResultV1
from skatmind.api.v1.session.files.contracts import (
    SessionFileApiOptionsV1,
    SessionFileApiResultV1,
)
from skatmind.api.v1.session.schema_validation import (
    _validate_session_definition,
    validate_session_correction_document,
    validate_session_create_document,
    validate_session_result_document,
)
from skatmind.errors import SkatMindSchemaError
from skatmind.session_checkpoint_review import (
    export_session_checkpoint_review_request_v1,
)
from skatmind.session_decision_observation import (
    observe_session_decision_checkpoint_v1,
)
from skatmind.session_persistence_codec import resume_session_document_v1
from skatmind.session_persistence_contracts import SessionPersistenceWriteResultV1

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _create_document() -> dict[str, object]:
    return {
        "session_id": "schema-session",
        "capture_mode": "retrospective",
        "local_player_id": "player-a",
        "players": [
            {
                "player_id": "player-a",
                "player_label": "Player A",
                "seat": "forehand",
            },
            {
                "player_id": "player-b",
                "player_label": None,
                "seat": "middlehand",
            },
            {
                "player_id": "player-c",
                "player_label": None,
                "seat": "rearhand",
            },
        ],
    }


def _correction_document() -> dict[str, object]:
    return {
        "session_history_edit_version": 1,
        "expected_revision": 1,
        "target_revision": 1,
        "replacement_command": {
            "command_version": 1,
            "kind": "set_game_metadata",
            "expected_revision": 0,
            "game_id": "corrected-game",
            "played_at": None,
        },
    }


def test_issue157_definitions_are_strict_valid_and_byte_identical() -> None:
    authoritative = PROJECT_ROOT / "schemas" / "session.schema.json"
    packaged = PROJECT_ROOT / "src" / "skatmind" / "schema_resources" / "session.schema.json"
    assert authoritative.read_bytes() == packaged.read_bytes()
    schema = json.loads(authoritative.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)

    strict_definitions = {
        "session_create_input",
        "session_persistence_write_result",
        "session_file_api_options",
        "session_file_api_result",
        "decision_observation",
        "checkpoint_review_export",
    }
    assert strict_definitions <= schema["$defs"].keys()
    assert all(
        schema["$defs"][definition]["additionalProperties"] is False
        for definition in strict_definitions
    )
    assert "actual_card_played" in schema["$defs"]["position_document"]["properties"]
    assert schema["$defs"]["session_operation"]["enum"][-2:] == [
        "observe_checkpoint",
        "export_checkpoint_review",
    ]


def test_create_and_correction_input_validators_are_recursive_and_strict() -> None:
    validate_session_create_document(_create_document())
    validate_session_correction_document(_correction_document())

    invalid_create = _create_document()
    invalid_create["unknown"] = True
    with pytest.raises(SkatMindSchemaError):
        validate_session_create_document(invalid_create)

    invalid_nested_create = _create_document()
    invalid_nested_create["players"][0]["unknown"] = True
    with pytest.raises(SkatMindSchemaError):
        validate_session_create_document(invalid_nested_create)

    live_without_local_player = _create_document()
    live_without_local_player["capture_mode"] = "live"
    live_without_local_player["local_player_id"] = None
    with pytest.raises(SkatMindSchemaError):
        validate_session_create_document(live_without_local_player)

    duplicate_seat = _create_document()
    duplicate_seat["players"][2]["seat"] = "middlehand"
    with pytest.raises(SkatMindSchemaError):
        validate_session_create_document(duplicate_seat)

    invalid_correction = _correction_document()
    invalid_correction["replacement_command"]["unknown"] = True
    with pytest.raises(SkatMindSchemaError):
        validate_session_correction_document(invalid_correction)


def test_persistence_write_and_file_api_discrimination_are_strict() -> None:
    write_result = SessionPersistenceWriteResultV1(
        status="saved",
        session_id="schema-session",
        revision=0,
        expected_content_fingerprint=None,
        existing_content_fingerprint=None,
        requested_content_fingerprint="a" * 64,
    )
    save_result = SessionFileApiResultV1(
        operation="save",
        value=write_result,
    ).to_dict()
    _validate_session_definition(SessionFileApiOptionsV1().to_dict(), "session_file_api_options")
    _validate_session_definition(save_result, "session_file_api_result")

    resume_result = resume_session_document_v1(_document("schema-load").to_dict())
    load_result = SessionFileApiResultV1(
        operation="load",
        value=resume_result,
    ).to_dict()
    _validate_session_definition(load_result, "session_file_api_result")

    wrong_operation = copy.deepcopy(save_result)
    wrong_operation["operation"] = "load"
    with pytest.raises(SkatMindSchemaError):
        _validate_session_definition(wrong_operation, "session_file_api_result")

    unknown_nested_field = copy.deepcopy(save_result)
    unknown_nested_field["value"]["path"] = "private.json"
    with pytest.raises(SkatMindSchemaError):
        _validate_session_definition(unknown_nested_field, "session_file_api_result")

    unchanged_with_null_fingerprints = write_result.to_dict()
    unchanged_with_null_fingerprints["status"] = "unchanged"
    with pytest.raises(SkatMindSchemaError):
        _validate_session_definition(
            unchanged_with_null_fingerprints,
            "session_persistence_write_result",
        )

    conflict_with_two_null_fingerprints = write_result.to_dict()
    conflict_with_two_null_fingerprints["status"] = "conflict"
    with pytest.raises(SkatMindSchemaError):
        _validate_session_definition(
            conflict_with_two_null_fingerprints,
            "session_persistence_write_result",
        )


def test_observation_result_schema_enforces_operation_status_and_nested_shape() -> None:
    _, observed_state, checkpoint = _observed()
    observation = observe_session_decision_checkpoint_v1(
        state=observed_state,
        checkpoint=checkpoint,
    )
    result = SessionApiResultV1(
        operation="observe_checkpoint",
        value=observation,
    ).to_dict()
    validate_session_result_document(result)

    missing_observed_card = copy.deepcopy(result)
    missing_observed_card["value"]["actual_card"] = None
    with pytest.raises(SkatMindSchemaError):
        validate_session_result_document(missing_observed_card)

    wrong_reason = copy.deepcopy(result)
    wrong_reason["value"]["reason_codes"] = ["local_play_not_recorded"]
    with pytest.raises(SkatMindSchemaError):
        validate_session_result_document(wrong_reason)

    unknown_lineage_field = copy.deepcopy(result)
    unknown_lineage_field["value"]["lineage"]["unknown"] = True
    with pytest.raises(SkatMindSchemaError):
        validate_session_result_document(unknown_lineage_field)

    wrong_operation = copy.deepcopy(result)
    wrong_operation["operation"] = "export_checkpoint_review"
    with pytest.raises(SkatMindSchemaError):
        validate_session_result_document(wrong_operation)


def test_review_export_schema_accepts_review_card_and_enforces_status_relationships() -> None:
    pending_state, observed_state, checkpoint = _observed()
    available = export_session_checkpoint_review_request_v1(
        state=observed_state,
        checkpoint=checkpoint,
    )
    available_result = SessionApiResultV1(
        operation="export_checkpoint_review",
        value=available,
    ).to_dict()
    validate_session_result_document(available_result)
    assert available_result["value"]["request"]["document"]["actual_card_played"] == "CA"

    unavailable = export_session_checkpoint_review_request_v1(
        state=pending_state,
        checkpoint=checkpoint,
    )
    validate_session_result_document(
        SessionApiResultV1(
            operation="export_checkpoint_review",
            value=unavailable,
        ).to_dict()
    )

    wrong_status = copy.deepcopy(available_result)
    wrong_status["value"]["status"] = "unavailable"
    with pytest.raises(SkatMindSchemaError):
        validate_session_result_document(wrong_status)

    live_review_request = copy.deepcopy(available_result)
    live_review_request["value"]["request"]["document"]["analysis_mode"] = "live_decision"
    with pytest.raises(SkatMindSchemaError):
        validate_session_result_document(live_review_request)

    unknown_position_field = copy.deepcopy(available_result)
    unknown_position_field["value"]["request"]["document"]["unknown"] = True
    with pytest.raises(SkatMindSchemaError):
        validate_session_result_document(unknown_position_field)
