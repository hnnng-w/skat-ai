import copy
import json
from dataclasses import FrozenInstanceError, fields, replace
from types import MappingProxyType

import pytest
from test_historical_game import build_historical_input
from test_session_position_export import _options, _state_for_decision
from test_session_transitions import _apply, _live_declaration_state

import skat_ai.session_decision_checkpoint as checkpoint_module
import skat_ai.session_position_export as position_export_module
from skat_ai.api.v1.contracts import RequestDocumentV1, WorkflowV1
from skat_ai.errors import SkatAIInvariantError
from skat_ai.game_declaration import GameDeclaration
from skat_ai.session_commands import (
    PromoteSessionToRetrospectiveCommandV1,
    RecordSessionPlayCommandV1,
    SetSessionDeclarationCommandV1,
    SetSessionDeclarerCommandV1,
    SetSessionGameEventCommandV1,
)
from skat_ai.session_decision_checkpoint import (
    SESSION_DECISION_CHECKPOINT_POLICY,
    SESSION_DECISION_CHECKPOINT_VERSION,
    SESSION_DECISION_INFORMATION_CUTOFF,
    SessionDecisionCheckpointV1,
    build_session_decision_checkpoint_v1,
)
from skat_ai.session_position_export import (
    export_session_position_analysis_request_v1,
)


def _ready_live_state():
    state = _live_declaration_state()
    state = _apply(
        state,
        SetSessionDeclarerCommandV1(
            expected_revision=state.revision,
            declarer_player_id="player-a",
        ),
    )
    return _apply(
        state,
        SetSessionDeclarationCommandV1(
            expected_revision=state.revision,
            declaration=GameDeclaration(
                game_type="grand",
                hand_game=True,
                bid_value=24,
            ),
        ),
    )


def _checkpoint():
    state = _ready_live_state()
    position_export = export_session_position_analysis_request_v1(state, _options())
    return (
        state,
        position_export,
        build_session_decision_checkpoint_v1(
            state=state,
            position_export=position_export,
        ),
    )


def test_checkpoint_constants_shape_immutability_and_serialization_are_exact() -> None:
    state, position_export, checkpoint = _checkpoint()
    assert SESSION_DECISION_CHECKPOINT_VERSION == 1
    assert SESSION_DECISION_CHECKPOINT_POLICY == "frozen_pre_play_request"
    assert SESSION_DECISION_INFORMATION_CUTOFF == "before_local_play"
    assert [field.name for field in fields(SessionDecisionCheckpointV1)] == [
        "session_decision_checkpoint_version",
        "session_id",
        "source_revision",
        "source_capture_mode",
        "decision_index",
        "trick_number",
        "play_index",
        "acting_player_id",
        "acting_seat",
        "information_cutoff",
        "relative_player_map",
        "request",
    ]
    assert not hasattr(checkpoint, "__dict__")
    assert isinstance(checkpoint.relative_player_map, MappingProxyType)
    assert checkpoint.session_id == state.session_id
    assert checkpoint.source_revision == state.revision
    assert checkpoint.source_capture_mode == "live"
    assert checkpoint.decision_index == checkpoint.trick_number == checkpoint.play_index == 1
    assert checkpoint.acting_player_id == "player-a"
    assert checkpoint.acting_seat == "forehand"
    assert checkpoint.relative_player_map == {
        "me": "player-a",
        "left": "player-b",
        "right": "player-c",
    }
    assert checkpoint.request == position_export.request
    assert list(checkpoint.to_dict()) == [field.name for field in fields(checkpoint)]
    json.dumps(checkpoint.to_dict())
    with pytest.raises(FrozenInstanceError):
        checkpoint.source_revision = 0
    with pytest.raises(TypeError):
        checkpoint.relative_player_map["me"] = "changed"
    with pytest.raises(TypeError):
        SessionDecisionCheckpointV1(*checkpoint.to_dict().values())


@pytest.mark.parametrize("version", (2, True, 1.0))
def test_checkpoint_rejects_wrong_version(version: object) -> None:
    _, _, checkpoint = _checkpoint()
    values = checkpoint.to_dict()
    values["session_decision_checkpoint_version"] = version
    values["request"] = checkpoint.request
    with pytest.raises(ValueError, match="session_decision_checkpoint_version"):
        SessionDecisionCheckpointV1(**values)


@pytest.mark.parametrize(
    ("field_name", "value"),
    (
        ("source_revision", True),
        ("source_capture_mode", "unknown"),
        ("decision_index", 0),
        ("trick_number", 11),
        ("play_index", 4),
        ("acting_player_id", "me"),
        ("acting_seat", "unknown"),
        ("information_cutoff", "after_local_play"),
    ),
)
def test_checkpoint_rejects_invalid_scalar_invariants(
    field_name: str,
    value: object,
) -> None:
    _, _, checkpoint = _checkpoint()
    values = checkpoint.to_dict()
    values[field_name] = value
    values["request"] = checkpoint.request
    with pytest.raises(ValueError):
        SessionDecisionCheckpointV1(**values)


def test_checkpoint_rejects_relative_map_and_request_mismatches() -> None:
    _, _, checkpoint = _checkpoint()
    values = checkpoint.to_dict()
    values["request"] = checkpoint.request
    for relative_map in (
        {"me": "player-b", "left": "player-a", "right": "player-c"},
        {"me": "player-a", "left": "player-b"},
        {"me": "player-a", "left": "player-b", "right": "player-b"},
    ):
        with pytest.raises(ValueError, match="relative_player_map"):
            SessionDecisionCheckpointV1(
                **{**values, "relative_player_map": relative_map}
            )

    root = checkpoint.request.to_dict()["document"]
    root["next_player"] = "left"
    wrong_request = RequestDocumentV1(
        workflow=WorkflowV1.POSITION_ANALYSIS,
        document=root,
    )
    with pytest.raises(ValueError, match="pre-Play"):
        SessionDecisionCheckpointV1(**{**values, "request": wrong_request})

    with pytest.raises(ValueError, match="indexes"):
        SessionDecisionCheckpointV1(
            **{
                **values,
                "decision_index": 4,
                "trick_number": 2,
                "play_index": 1,
            }
        )


def test_checkpoint_builder_requires_matching_available_position_export() -> None:
    state, position_export, _ = _checkpoint()
    with pytest.raises(ValueError, match="SessionStateV1"):
        build_session_decision_checkpoint_v1(
            state=object(),
            position_export=position_export,
        )
    with pytest.raises(ValueError, match="SessionRequestExportV1"):
        build_session_decision_checkpoint_v1(
            state=state,
            position_export=object(),
        )

    unavailable_state = _live_declaration_state()
    unavailable = export_session_position_analysis_request_v1(
        unavailable_state,
        _options(),
    )
    with pytest.raises(ValueError, match="available Position"):
        build_session_decision_checkpoint_v1(
            state=unavailable_state,
            position_export=unavailable,
        )


def test_checkpoint_builder_detects_session_revision_and_forged_request() -> None:
    state, position_export, _ = _checkpoint()
    with pytest.raises(SkatAIInvariantError, match="Session ID"):
        build_session_decision_checkpoint_v1(
            state=state,
            position_export=replace(position_export, session_id="other-session"),
        )
    with pytest.raises(SkatAIInvariantError, match="revision"):
        build_session_decision_checkpoint_v1(
            state=state,
            position_export=replace(
                position_export,
                source_revision=state.revision - 1,
            ),
        )

    forged_root = position_export.request.to_dict()["document"]
    forged_root["player_role"] = "defender"
    forged_root["declarer_player"] = "left"
    forged_request = RequestDocumentV1(
        workflow=WorkflowV1.POSITION_ANALYSIS,
        document=forged_root,
    )
    forged_export = replace(position_export, request=forged_request)
    with pytest.raises(SkatAIInvariantError, match="expected Session Request"):
        build_session_decision_checkpoint_v1(
            state=state,
            position_export=forged_export,
        )


def test_checkpoint_is_frozen_against_later_play_event_promotion_and_caller_mutation() -> None:
    state, _, checkpoint = _checkpoint()
    before = checkpoint.to_dict()

    played_state = _apply(
        state,
        RecordSessionPlayCommandV1(
            expected_revision=state.revision,
            player_id="player-a",
            card="CA",
        ),
    )
    assert played_state.revision == state.revision + 1

    event_state = _apply(
        state,
        SetSessionGameEventCommandV1(
            expected_revision=state.revision,
            event={
                "schema_version": 1,
                "kind": "declarer_card_exposure_continuation",
                "after_play_count": 0,
                "exposure": {
                    "form": "shown_to_defender",
                    "shown_to_defender_player_id": "player-b",
                },
                "claimed_play_level": "simple",
                "defender_responses": [
                    {
                        "defender_player_id": "player-b",
                        "response": "continue",
                        "form": "explicit",
                    },
                    {
                        "defender_player_id": "player-c",
                        "response": "accept",
                        "form": "explicit",
                    },
                ],
                "public_declarer_cards": list(
                    checkpoint.request.document["hand"]
                ),
            },
        ),
    )
    assert event_state.revision == state.revision + 1

    promoted_state = _apply(
        state,
        PromoteSessionToRetrospectiveCommandV1(expected_revision=state.revision),
    )
    assert promoted_state.capture_mode == "retrospective"

    mutable = checkpoint.to_dict()
    mutable["relative_player_map"]["me"] = "changed"
    mutable["request"]["document"]["hand"].clear()
    assert checkpoint.to_dict() == before
    assert "actual_card_played" not in json.dumps(before)
    assert "game_end" not in before["request"]["document"]


def test_checkpoint_build_uses_one_replay_and_one_expected_request_reconstruction(
    monkeypatch,
) -> None:
    state = _ready_live_state()
    position_export = export_session_position_analysis_request_v1(state, _options())
    replay_count = 0
    builder_count = 0
    original_replay = checkpoint_module.replay_session_state_v1
    original_builder = position_export_module.build_position_from_document

    def counted_replay(value):
        nonlocal replay_count
        replay_count += 1
        return original_replay(value)

    def counted_builder(value):
        nonlocal builder_count
        builder_count += 1
        return original_builder(value)

    monkeypatch.setattr(checkpoint_module, "replay_session_state_v1", counted_replay)
    monkeypatch.setattr(
        position_export_module,
        "build_position_from_document",
        counted_builder,
    )
    checkpoint = checkpoint_module.build_session_decision_checkpoint_v1(
        state=state,
        position_export=position_export,
    )
    assert checkpoint.request == position_export.request
    assert replay_count == 1
    assert builder_count == 1


def test_checkpoint_serialization_contains_no_result_timestamp_id_or_private_state() -> None:
    _, _, checkpoint = _checkpoint()
    serialized = json.dumps(checkpoint.to_dict())
    forbidden = {
        "actual_card",
        "result",
        "timestamp",
        "checkpoint_id",
        "fingerprint",
        "command_log",
        "private_hand",
        "search_worlds",
        "simulation_ownership",
        "principal_variation",
        "field_provenance",
    }
    assert all(f'"{field}"' not in serialized for field in forbidden)


def test_checkpoint_request_defensive_copy_survives_forged_caller_document_mutation() -> None:
    state = _ready_live_state()
    position_export = export_session_position_analysis_request_v1(state, _options())
    caller_root = copy.deepcopy(position_export.request.to_dict()["document"])
    caller_request = RequestDocumentV1(
        workflow=WorkflowV1.POSITION_ANALYSIS,
        document=caller_root,
    )
    equal_export = replace(position_export, request=caller_request)
    checkpoint = build_session_decision_checkpoint_v1(
        state=state,
        position_export=equal_export,
    )
    caller_root["hand"].clear()
    assert checkpoint.request.document["hand"]


def test_retrospective_checkpoint_and_repeated_build_are_equal() -> None:
    state = _state_for_decision(build_historical_input(), 2)
    position_export = export_session_position_analysis_request_v1(state, _options())
    first = build_session_decision_checkpoint_v1(
        state=state,
        position_export=position_export,
    )
    second = build_session_decision_checkpoint_v1(
        state=state,
        position_export=position_export,
    )
    assert first == second
    assert first.source_capture_mode == "retrospective"
    assert first.decision_index == 2


def test_checkpoint_contract_rejects_extra_position_request_fields() -> None:
    _, _, checkpoint = _checkpoint()
    root = checkpoint.request.to_dict()["document"]
    root["output_path"] = "result.json"
    request = RequestDocumentV1(
        workflow=WorkflowV1.POSITION_ANALYSIS,
        document=root,
    )
    values = checkpoint.to_dict()
    values["request"] = request
    with pytest.raises(ValueError, match="complete flat Position"):
        SessionDecisionCheckpointV1(**values)
