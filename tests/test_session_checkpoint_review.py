import json
from dataclasses import FrozenInstanceError, fields, replace

import pytest
from test_session_decision_checkpoint import _checkpoint
from test_session_decision_observation import (
    _diverged_state,
    _ended_without_play,
    _observed,
)

import skat_ai.session_checkpoint_review as review_module
from skat_ai.input_loader import build_position_from_document
from skat_ai.session_checkpoint_review import (
    SESSION_CHECKPOINT_REVIEW_EXPORT_POLICY,
    SESSION_CHECKPOINT_REVIEW_EXPORT_STATUSES,
    SESSION_CHECKPOINT_REVIEW_EXPORT_VERSION,
    SessionCheckpointReviewExportV1,
    export_session_checkpoint_review_request_v1,
)
from skat_ai.session_history import build_session_state_from_accepted_prefix_v1


def test_review_export_identity_contract_and_serialization_are_exact() -> None:
    _, observed_state, checkpoint = _observed()
    result = export_session_checkpoint_review_request_v1(
        state=observed_state,
        checkpoint=checkpoint,
    )
    assert SESSION_CHECKPOINT_REVIEW_EXPORT_VERSION == 1
    assert (
        SESSION_CHECKPOINT_REVIEW_EXPORT_POLICY
        == "frozen_request_plus_observed_card"
    )
    assert SESSION_CHECKPOINT_REVIEW_EXPORT_STATUSES == (
        "available",
        "unavailable",
        "diverged",
    )
    assert [field.name for field in fields(SessionCheckpointReviewExportV1)] == [
        "session_checkpoint_review_export_version",
        "status",
        "session_id",
        "checkpoint_revision",
        "observation_revision",
        "observation",
        "request",
        "diagnostics",
    ]
    assert not hasattr(result, "__dict__")
    assert list(result.to_dict()) == [field.name for field in fields(result)]
    json.dumps(result.to_dict())
    with pytest.raises(FrozenInstanceError):
        result.status = "unavailable"
    with pytest.raises(TypeError):
        SessionCheckpointReviewExportV1(*result.to_dict().values())


def test_available_review_changes_only_mode_and_observed_card() -> None:
    _, observed_state, checkpoint = _observed()
    frozen_before = checkpoint.request.to_dict()["document"]
    result = export_session_checkpoint_review_request_v1(
        state=observed_state,
        checkpoint=checkpoint,
    )
    assert result.status == "available"
    assert result.observation.status == "observed"
    assert result.observation_revision == observed_state.revision
    assert result.request is not checkpoint.request
    review_root = result.request.to_dict()["document"]
    assert review_root["analysis_mode"] == "post_game_review"
    assert review_root["actual_card_played"] == "CA"
    assert build_position_from_document(review_root) == review_root
    assert {
        key
        for key in review_root.keys() | frozen_before.keys()
        if review_root.get(key) != frozen_before.get(key)
    } == {"analysis_mode", "actual_card_played"}
    assert checkpoint.request.to_dict()["document"] == frozen_before
    assert result.diagnostics == ()


def test_review_preserves_frozen_recommendation_search_and_private_cutoff() -> None:
    _, observed_state, checkpoint = _observed()
    frozen_root = checkpoint.request.to_dict()["document"]
    result = export_session_checkpoint_review_request_v1(
        state=observed_state,
        checkpoint=checkpoint,
    )
    root = result.request.to_dict()["document"]
    for field_name in (
        "hand",
        "current_trick",
        "completed_tricks",
        "skat",
        "sample_count",
        "random_seed",
        "use_basic_opponent_strategy",
    ):
        assert root[field_name] == frozen_root[field_name]
    assert "command_log" not in root
    assert "validation" not in root
    assert "result" not in result.to_dict()


def test_pending_future_and_diverged_review_exports_execute_nothing() -> None:
    state, _, checkpoint = _checkpoint()
    pending = export_session_checkpoint_review_request_v1(
        state=state,
        checkpoint=checkpoint,
    )
    assert pending.status == "unavailable"
    assert pending.observation.status == "pending"
    assert pending.request is None

    prefix = build_session_state_from_accepted_prefix_v1(
        state,
        target_revision=state.revision - 1,
    )
    future = export_session_checkpoint_review_request_v1(
        state=prefix,
        checkpoint=checkpoint,
    )
    assert future.status == "unavailable"
    assert future.observation.status == "future"
    assert future.request is None

    diverged = export_session_checkpoint_review_request_v1(
        state=_diverged_state(state),
        checkpoint=checkpoint,
    )
    assert diverged.status == "diverged"
    assert diverged.observation.status == "diverged"
    assert diverged.request is None

    ended_state, ended_checkpoint = _ended_without_play()
    ended = export_session_checkpoint_review_request_v1(
        state=ended_state,
        checkpoint=ended_checkpoint,
    )
    assert ended.status == "unavailable"
    assert ended.observation.status == "ended_without_play"
    assert ended.request is None


def test_review_derives_one_observation_and_validates_position_once(monkeypatch) -> None:
    _, observed_state, checkpoint = _observed()
    observation_count = 0
    builder_count = 0
    original_observation = review_module.observe_session_decision_checkpoint_v1
    original_builder = review_module.build_position_from_document

    def counted_observation(**values):
        nonlocal observation_count
        observation_count += 1
        return original_observation(**values)

    def counted_builder(root):
        nonlocal builder_count
        builder_count += 1
        return original_builder(root)

    monkeypatch.setattr(
        review_module,
        "observe_session_decision_checkpoint_v1",
        counted_observation,
    )
    monkeypatch.setattr(review_module, "build_position_from_document", counted_builder)
    result = review_module.export_session_checkpoint_review_request_v1(
        state=observed_state,
        checkpoint=checkpoint,
    )
    assert result.status == "available"
    assert observation_count == builder_count == 1


def test_unavailable_review_does_not_call_position_builder(monkeypatch) -> None:
    state, _, checkpoint = _checkpoint()

    def forbidden(_root):
        raise AssertionError("Position builder must not run")

    monkeypatch.setattr(review_module, "build_position_from_document", forbidden)
    result = review_module.export_session_checkpoint_review_request_v1(
        state=state,
        checkpoint=checkpoint,
    )
    assert result.status == "unavailable"


def test_review_contract_rejects_mismatched_status_request_and_revisions() -> None:
    _, observed_state, checkpoint = _observed()
    result = export_session_checkpoint_review_request_v1(
        state=observed_state,
        checkpoint=checkpoint,
    )
    with pytest.raises(ValueError, match="version"):
        replace(result, session_checkpoint_review_export_version=True)
    with pytest.raises(ValueError, match="identity"):
        replace(result, observation_revision=result.observation_revision + 1)
    with pytest.raises(ValueError, match="unavailable"):
        replace(result, status="unavailable")
    with pytest.raises(ValueError, match="requires no diagnostics"):
        replace(result, diagnostics=(observed_state.validation.diagnostics[0],))


def test_review_rejects_wrong_input_types() -> None:
    state, _, checkpoint = _checkpoint()
    with pytest.raises(ValueError, match="SessionStateV1"):
        export_session_checkpoint_review_request_v1(
            state=object(),
            checkpoint=checkpoint,
        )
    with pytest.raises(ValueError, match="SessionDecisionCheckpointV1"):
        export_session_checkpoint_review_request_v1(
            state=state,
            checkpoint=object(),
        )
