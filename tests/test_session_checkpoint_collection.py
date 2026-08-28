import json
from dataclasses import FrozenInstanceError, fields, replace

import pytest
from test_session_decision_checkpoint import _ready_live_state
from test_session_position_export import _live_ouvert_defender_state, _options

import skatmind.session_checkpoint_collection as collection_module
from skatmind.session_checkpoint_collection import (
    SESSION_CHECKPOINT_COLLECTION_POLICY,
    SESSION_CHECKPOINT_COLLECTION_STATUSES,
    SESSION_CHECKPOINT_COLLECTION_VERSION,
    SessionCheckpointCollectionResultV1,
    collect_session_decision_checkpoint_v1,
)


def test_collection_identity_contract_and_serialization_are_exact() -> None:
    state = _ready_live_state()
    result = collect_session_decision_checkpoint_v1(
        state=state,
        export_options=_options(),
        decision_checkpoints=(),
    )
    assert SESSION_CHECKPOINT_COLLECTION_VERSION == 1
    assert (
        SESSION_CHECKPOINT_COLLECTION_POLICY
        == "exact_position_ready_revision_and_request"
    )
    assert SESSION_CHECKPOINT_COLLECTION_STATUSES == (
        "collected",
        "existing",
        "unavailable",
    )
    assert [field.name for field in fields(SessionCheckpointCollectionResultV1)] == [
        "session_checkpoint_collection_version",
        "status",
        "session_id",
        "source_revision",
        "checkpoint",
        "decision_checkpoints",
        "diagnostics",
    ]
    assert not hasattr(result, "__dict__")
    assert list(result.to_dict()) == [field.name for field in fields(result)]
    json.dumps(result.to_dict())
    with pytest.raises(FrozenInstanceError):
        result.status = "existing"
    with pytest.raises(TypeError):
        SessionCheckpointCollectionResultV1(*result.to_dict().values())


def test_collection_returns_unavailable_and_preserves_checkpoints() -> None:
    ready_state = _ready_live_state()
    collected = collect_session_decision_checkpoint_v1(
        state=ready_state,
        export_options=_options(),
        decision_checkpoints=(),
    )
    unavailable_state = _live_ouvert_defender_state()
    unavailable = collect_session_decision_checkpoint_v1(
        state=unavailable_state,
        export_options=_options(),
        decision_checkpoints=collected.decision_checkpoints,
    )
    assert unavailable.status == "unavailable"
    assert unavailable.checkpoint is None
    assert unavailable.decision_checkpoints == collected.decision_checkpoints
    assert unavailable.diagnostics
    assert all(
        diagnostic.blocks_position_export for diagnostic in unavailable.diagnostics
    )


def test_collection_collects_then_reuses_exact_checkpoint() -> None:
    state = _ready_live_state()
    first = collect_session_decision_checkpoint_v1(
        state=state,
        export_options=_options(),
        decision_checkpoints=(),
    )
    second = collect_session_decision_checkpoint_v1(
        state=state,
        export_options=_options(),
        decision_checkpoints=first.decision_checkpoints,
    )
    assert first.status == "collected"
    assert len(first.decision_checkpoints) == 1
    assert first.checkpoint == first.decision_checkpoints[0]
    assert second.status == "existing"
    assert second.checkpoint is first.checkpoint
    assert second.decision_checkpoints == first.decision_checkpoints


def test_same_revision_different_requests_are_retained_in_canonical_order() -> None:
    state = _ready_live_state()
    default = collect_session_decision_checkpoint_v1(
        state=state,
        export_options=_options(),
        decision_checkpoints=(),
    )
    alternate = collect_session_decision_checkpoint_v1(
        state=state,
        export_options=_options(recommendation_method="immediate_expected_value"),
        decision_checkpoints=default.decision_checkpoints,
    )
    assert alternate.status == "collected"
    assert len(alternate.decision_checkpoints) == 2
    assert {
        checkpoint.source_revision for checkpoint in alternate.decision_checkpoints
    } == {state.revision}
    assert alternate.decision_checkpoints[0] != alternate.decision_checkpoints[1]

    reverse = SessionCheckpointCollectionResultV1(
        status="existing",
        session_id=state.session_id,
        source_revision=state.revision,
        checkpoint=alternate.checkpoint,
        decision_checkpoints=tuple(reversed(alternate.decision_checkpoints)),
        diagnostics=(),
    )
    assert reverse.decision_checkpoints == alternate.decision_checkpoints


def test_collection_uses_one_replay_and_one_replay_aware_export(monkeypatch) -> None:
    state = _ready_live_state()
    replay_count = 0
    export_count = 0
    build_count = 0
    original_replay = collection_module.replay_session_state_v1
    original_export = (
        collection_module._export_replayed_session_position_analysis_request_v1
    )
    original_build = collection_module._build_replayed_session_decision_checkpoint_v1

    def counted_replay(value):
        nonlocal replay_count
        replay_count += 1
        return original_replay(value)

    def counted_export(**values):
        nonlocal export_count
        export_count += 1
        return original_export(**values)

    def counted_build(**values):
        nonlocal build_count
        build_count += 1
        return original_build(**values)

    monkeypatch.setattr(collection_module, "replay_session_state_v1", counted_replay)
    monkeypatch.setattr(
        collection_module,
        "_export_replayed_session_position_analysis_request_v1",
        counted_export,
    )
    monkeypatch.setattr(
        collection_module,
        "_build_replayed_session_decision_checkpoint_v1",
        counted_build,
    )
    result = collection_module.collect_session_decision_checkpoint_v1(
        state=state,
        export_options=_options(),
        decision_checkpoints=(),
    )
    assert result.status == "collected"
    assert replay_count == export_count == build_count == 1


def test_unavailable_collection_does_not_build_checkpoint(monkeypatch) -> None:
    state = _live_ouvert_defender_state()

    def forbidden(**_values):
        raise AssertionError("Checkpoint builder must not run")

    monkeypatch.setattr(
        collection_module,
        "_build_replayed_session_decision_checkpoint_v1",
        forbidden,
    )
    result = collection_module.collect_session_decision_checkpoint_v1(
        state=state,
        export_options=_options(),
        decision_checkpoints=(),
    )
    assert result.status == "unavailable"


def test_collection_contract_rejects_duplicates_and_invalid_relationships() -> None:
    state = _ready_live_state()
    result = collect_session_decision_checkpoint_v1(
        state=state,
        export_options=_options(),
        decision_checkpoints=(),
    )
    with pytest.raises(ValueError, match="version"):
        replace(result, session_checkpoint_collection_version=True)
    with pytest.raises(ValueError, match="duplicate"):
        replace(
            result,
            decision_checkpoints=(result.checkpoint, result.checkpoint),
        )
    with pytest.raises(ValueError, match="must not contain"):
        replace(result, status="unavailable")


def test_collection_rejects_wrong_input_types() -> None:
    state = _ready_live_state()
    options = _options()
    with pytest.raises(ValueError, match="SessionStateV1"):
        collect_session_decision_checkpoint_v1(
            state=object(),
            export_options=options,
            decision_checkpoints=(),
        )
    with pytest.raises(ValueError, match="SessionPositionExportOptionsV1"):
        collect_session_decision_checkpoint_v1(
            state=state,
            export_options=object(),
            decision_checkpoints=(),
        )
    with pytest.raises(ValueError, match="tuple"):
        collect_session_decision_checkpoint_v1(
            state=state,
            export_options=options,
            decision_checkpoints=[],
        )
