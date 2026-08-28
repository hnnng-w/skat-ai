import json
from dataclasses import FrozenInstanceError, fields, replace

import pytest
from test_historical_declarer_concession import build_concession_prefix
from test_session_decision_checkpoint import _checkpoint
from test_session_position_export import _options
from test_session_transitions import (
    _apply,
    _play_commands_from_data,
    _retrospective_before_play,
)

import skatmind.session_decision_observation as observation_module
from skatmind.session_commands import (
    RecordSessionDealtCardCommandV1,
    RecordSessionPlayCommandV1,
    SetSessionGameEndCommandV1,
    SetSessionGameMetadataCommandV1,
)
from skatmind.session_decision_checkpoint import build_session_decision_checkpoint_v1
from skatmind.session_decision_observation import (
    SESSION_DECISION_OBSERVATION_POLICY,
    SESSION_DECISION_OBSERVATION_REASON_CODES,
    SESSION_DECISION_OBSERVATION_STATUSES,
    SESSION_DECISION_OBSERVATION_VERSION,
    SessionDecisionObservationV1,
    observe_session_decision_checkpoint_v1,
)
from skatmind.session_history import (
    build_session_state_from_accepted_prefix_v1,
    correct_session_command_v1,
)
from skatmind.session_history_contracts import SessionCommandCorrectionV1
from skatmind.session_position_export import export_session_position_analysis_request_v1


def _observed():
    state, _, checkpoint = _checkpoint()
    observed_state = _apply(
        state,
        RecordSessionPlayCommandV1(
            expected_revision=state.revision,
            player_id=checkpoint.acting_player_id,
            card="CA",
        ),
    )
    return state, observed_state, checkpoint


def _diverged_state(state):
    deal_revision = next(
        record.revision
        for record in state.command_log
        if record.command.kind == "record_dealt_card"
    )
    original = state.command_log[deal_revision - 1].command
    replacement_card = "SK" if original.card != "SK" else "SA"
    result = correct_session_command_v1(
        state,
        SessionCommandCorrectionV1(
            expected_revision=state.revision,
            target_revision=deal_revision,
            replacement_command=RecordSessionDealtCardCommandV1(
                expected_revision=deal_revision - 1,
                destination="player_hand",
                player_id="player-a",
                card=replacement_card,
            ),
        ),
    )
    assert result.status == "applied"
    return result.state


def _ended_without_play():
    data = build_concession_prefix(
        completed_trick_count=4,
        current_trick_card_count=2,
    )
    state = _play_commands_from_data(
        _retrospective_before_play(data, local_player_id="player-c"),
        data,
    )
    position_export = export_session_position_analysis_request_v1(state, _options())
    checkpoint = build_session_decision_checkpoint_v1(
        state=state,
        position_export=position_export,
    )
    ended_state = _apply(
        state,
        SetSessionGameEndCommandV1(
            expected_revision=state.revision,
            game_end_reason=data["game_end_reason"],
            game_end=data["game_end"],
        ),
    )
    return ended_state, checkpoint


def test_observation_identity_contract_and_serialization_are_exact() -> None:
    _, observed_state, checkpoint = _observed()
    observation = observe_session_decision_checkpoint_v1(
        state=observed_state,
        checkpoint=checkpoint,
    )
    assert SESSION_DECISION_OBSERVATION_VERSION == 1
    assert (
        SESSION_DECISION_OBSERVATION_POLICY
        == "first_observed_local_play_after_checkpoint"
    )
    assert SESSION_DECISION_OBSERVATION_STATUSES == (
        "observed",
        "pending",
        "future",
        "diverged",
        "ended_without_play",
    )
    assert SESSION_DECISION_OBSERVATION_REASON_CODES == (
        "local_play_not_recorded",
        "state_before_checkpoint",
        "checkpoint_diverged",
        "game_ended_before_local_play",
    )
    assert [field.name for field in fields(SessionDecisionObservationV1)] == [
        "session_decision_observation_version",
        "status",
        "session_id",
        "checkpoint_revision",
        "state_revision",
        "decision_index",
        "lineage",
        "observed_play_revision",
        "actual_card",
        "reason_codes",
    ]
    assert not hasattr(observation, "__dict__")
    assert list(observation.to_dict()) == [field.name for field in fields(observation)]
    json.dumps(observation.to_dict())
    with pytest.raises(FrozenInstanceError):
        observation.status = "pending"
    with pytest.raises(TypeError):
        SessionDecisionObservationV1(*observation.to_dict().values())


def test_observed_card_comes_from_exact_first_later_local_play() -> None:
    state, _, checkpoint = _observed()
    state = _apply(
        state,
        SetSessionGameMetadataCommandV1(
            expected_revision=state.revision,
            game_id="intervening-metadata",
        ),
    )
    state = _apply(
        state,
        RecordSessionPlayCommandV1(
            expected_revision=state.revision,
            player_id=checkpoint.acting_player_id,
            card="CA",
        ),
    )
    before = checkpoint.to_dict()
    observation = observe_session_decision_checkpoint_v1(
        state=state,
        checkpoint=checkpoint,
    )
    assert observation.status == "observed"
    assert observation.lineage.relationship == "ancestor"
    assert observation.observed_play_revision == checkpoint.source_revision + 2
    assert observation.actual_card == "CA"
    assert observation.reason_codes == ()
    assert checkpoint.to_dict() == before


def test_pending_future_and_diverged_are_explicit_and_never_infer_a_card() -> None:
    state, _, checkpoint = _checkpoint()
    pending = observe_session_decision_checkpoint_v1(
        state=state,
        checkpoint=checkpoint,
    )
    assert (
        pending.status,
        pending.lineage.relationship,
        pending.reason_codes,
        pending.observed_play_revision,
        pending.actual_card,
    ) == ("pending", "current", ("local_play_not_recorded",), None, None)

    prefix = build_session_state_from_accepted_prefix_v1(
        state,
        target_revision=state.revision - 1,
    )
    future = observe_session_decision_checkpoint_v1(
        state=prefix,
        checkpoint=checkpoint,
    )
    assert future.status == "future"
    assert future.lineage.relationship == "future"
    assert future.reason_codes == ("state_before_checkpoint",)
    assert future.actual_card is None

    diverged = observe_session_decision_checkpoint_v1(
        state=_diverged_state(state),
        checkpoint=checkpoint,
    )
    assert diverged.status == "diverged"
    assert diverged.lineage.relationship == "diverged"
    assert diverged.reason_codes == ("checkpoint_diverged",)
    assert diverged.actual_card is None


def test_game_end_before_local_play_is_explicit() -> None:
    ended_state, checkpoint = _ended_without_play()
    observation = observe_session_decision_checkpoint_v1(
        state=ended_state,
        checkpoint=checkpoint,
    )
    assert observation.status == "ended_without_play"
    assert observation.lineage.relationship == "ancestor"
    assert observation.observed_play_revision is None
    assert observation.actual_card is None
    assert observation.reason_codes == ("game_ended_before_local_play",)


def test_observation_calls_lineage_classification_once(monkeypatch) -> None:
    _, observed_state, checkpoint = _observed()
    count = 0
    original = observation_module.classify_session_decision_checkpoint_v1

    def counted(state, value):
        nonlocal count
        count += 1
        return original(state, value)

    monkeypatch.setattr(
        observation_module,
        "classify_session_decision_checkpoint_v1",
        counted,
    )
    result = observation_module.observe_session_decision_checkpoint_v1(
        state=observed_state,
        checkpoint=checkpoint,
    )
    assert result.status == "observed"
    assert count == 1


@pytest.mark.parametrize(
    ("changes", "message"),
    (
        ({"session_decision_observation_version": True}, "version"),
        ({"checkpoint_revision": True}, "checkpoint_revision"),
        ({"state_revision": 1.0}, "state_revision"),
        ({"decision_index": 0}, "decision_index"),
        ({"reason_codes": ("local_play_not_recorded",)}, "reason_codes"),
        ({"observed_play_revision": None}, "observed_play_revision"),
        ({"actual_card": "invalid"}, "actual_card"),
    ),
)
def test_observed_contract_rejects_invalid_version_status_data(
    changes: dict,
    message: str,
) -> None:
    _, observed_state, checkpoint = _observed()
    observation = observe_session_decision_checkpoint_v1(
        state=observed_state,
        checkpoint=checkpoint,
    )
    with pytest.raises(ValueError, match=message):
        replace(observation, **changes)


def test_observation_rejects_wrong_input_types() -> None:
    state, _, checkpoint = _checkpoint()
    with pytest.raises(ValueError, match="SessionStateV1"):
        observe_session_decision_checkpoint_v1(state=object(), checkpoint=checkpoint)
    with pytest.raises(ValueError, match="SessionDecisionCheckpointV1"):
        observe_session_decision_checkpoint_v1(state=state, checkpoint=object())
