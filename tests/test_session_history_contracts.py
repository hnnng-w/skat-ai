import json
from dataclasses import FrozenInstanceError, fields, replace

import pytest
from test_session_contracts import _all_commands
from test_session_transitions import _apply, _players

from skat_ai.session_commands import (
    PromoteSessionToRetrospectiveCommandV1,
    RecordSessionDealtCardCommandV1,
    SetSessionGameMetadataCommandV1,
)
from skat_ai.session_history import (
    correct_session_command_v1,
    rewind_session_state_v1,
)
from skat_ai.session_history_contracts import (
    SESSION_BRANCHING_POLICY,
    SESSION_CHECKPOINT_LINEAGE_VERSION,
    SESSION_CHECKPOINT_RELATIONSHIPS,
    SESSION_CORRECTION_POLICY,
    SESSION_CORRECTION_STATUSES,
    SESSION_CORRECTION_SUFFIX_POLICY,
    SESSION_HISTORY_EDIT_VERSION,
    SESSION_HISTORY_STATE_POLICY,
    SESSION_REDO_POLICY,
    SESSION_UNDO_POLICY,
    SESSION_UNDO_STATUSES,
    SessionCheckpointLineageV1,
    SessionCommandCorrectionV1,
    SessionCorrectionResultV1,
    SessionUndoResultV1,
)
from skat_ai.session_transitions import create_session_state_v1


def _metadata_state():
    state = create_session_state_v1(
        session_id="session-history-contracts",
        players=_players(),
        capture_mode="live",
        local_player_id="player-a",
    )
    return _apply(
        state,
        SetSessionGameMetadataCommandV1(
            expected_revision=0,
            game_id="game-original",
        ),
    )


def _promoted_private_suffix_state():
    state = create_session_state_v1(
        session_id="session-history-partial",
        players=_players(),
        capture_mode="live",
        local_player_id="player-a",
    )
    state = _apply(
        state,
        RecordSessionDealtCardCommandV1(
            expected_revision=0,
            destination="player_hand",
            player_id="player-a",
            card="CA",
        ),
    )
    state = _apply(
        state,
        PromoteSessionToRetrospectiveCommandV1(expected_revision=1),
    )
    return _apply(
        state,
        RecordSessionDealtCardCommandV1(
            expected_revision=2,
            destination="player_hand",
            player_id="player-b",
            card="D7",
        ),
    )


def test_history_constants_policies_statuses_and_relationships_are_exact() -> None:
    assert SESSION_HISTORY_EDIT_VERSION == 1
    assert SESSION_UNDO_POLICY == "immutable_strict_prefix_rewind"
    assert SESSION_CORRECTION_POLICY == "replace_one_command_then_replay_suffix"
    assert SESSION_CORRECTION_SUFFIX_POLICY == "stop_before_first_rejected_command"
    assert SESSION_HISTORY_STATE_POLICY == "accepted_log_length_per_immutable_state"
    assert SESSION_BRANCHING_POLICY == "unsupported"
    assert SESSION_REDO_POLICY == "caller_retained_suffix_only"
    assert SESSION_UNDO_STATUSES == (
        "applied",
        "unchanged",
        "rejected",
        "revision_conflict",
    )
    assert SESSION_CORRECTION_STATUSES == (
        "applied",
        "unchanged",
        "partial",
        "rejected",
        "revision_conflict",
    )
    assert SESSION_CHECKPOINT_LINEAGE_VERSION == 1
    assert SESSION_CHECKPOINT_RELATIONSHIPS == (
        "current",
        "ancestor",
        "future",
        "diverged",
    )


def test_undo_result_shape_statuses_immutability_and_serialization_are_exact() -> None:
    source = _metadata_state()
    results = (
        rewind_session_state_v1(source, expected_revision=1, target_revision=0),
        rewind_session_state_v1(source, expected_revision=1, target_revision=1),
        rewind_session_state_v1(source, expected_revision=1, target_revision=2),
        rewind_session_state_v1(source, expected_revision=2, target_revision=2),
    )
    assert tuple(result.status for result in results) == SESSION_UNDO_STATUSES
    assert [field.name for field in fields(SessionUndoResultV1)] == [
        "session_history_edit_version",
        "status",
        "session_id",
        "expected_revision",
        "source_revision",
        "target_revision",
        "current_revision",
        "state",
        "removed_records",
        "diagnostics",
    ]
    assert all(not hasattr(result, "__dict__") for result in results)
    assert results[0].removed_records == source.command_log
    assert results[1].state is source
    assert results[2].diagnostics[0].code == "history_revision_violation"
    assert results[3].diagnostics[0].code == "revision_conflict"

    first = results[0].to_dict()
    second = results[0].to_dict()
    first["removed_records"][0]["command"]["game_id"] = "changed"
    first["state"]["players"][0]["player_label"] = "changed"
    assert second["removed_records"][0]["command"]["game_id"] == "game-original"
    assert second["state"]["players"][0]["player_label"] == "Alice"
    json.dumps(second)
    with pytest.raises(FrozenInstanceError):
        results[0].status = "unchanged"


@pytest.mark.parametrize("field_name", ("expected_revision", "source_revision"))
@pytest.mark.parametrize("value", (-1, True, 1.0))
def test_undo_result_rejects_invalid_revisions(field_name: str, value: object) -> None:
    result = rewind_session_state_v1(
        _metadata_state(),
        expected_revision=1,
        target_revision=0,
    )
    with pytest.raises(ValueError):
        replace(result, **{field_name: value})


@pytest.mark.parametrize("session_id", ("", " padded", "padded "))
def test_undo_result_rejects_invalid_session_id(session_id: str) -> None:
    result = rewind_session_state_v1(
        _metadata_state(),
        expected_revision=1,
        target_revision=0,
    )
    with pytest.raises(ValueError, match="session_id"):
        replace(result, session_id=session_id)


def test_undo_result_rejects_invalid_suffix_and_status_relationships() -> None:
    state = _metadata_state()
    state = _apply(
        state,
        RecordSessionDealtCardCommandV1(
            expected_revision=1,
            destination="player_hand",
            player_id="player-a",
            card="CA",
        ),
    )
    applied = rewind_session_state_v1(state, expected_revision=2, target_revision=0)
    with pytest.raises(ValueError, match="contiguous"):
        replace(applied, removed_records=tuple(reversed(applied.removed_records)))
    with pytest.raises(ValueError):
        replace(applied, current_revision=1)

    unchanged = rewind_session_state_v1(state, expected_revision=2, target_revision=2)
    with pytest.raises(ValueError):
        replace(unchanged, target_revision=1)
    rejected = rewind_session_state_v1(state, expected_revision=2, target_revision=3)
    with pytest.raises(ValueError):
        replace(rejected, diagnostics=())
    conflict = rewind_session_state_v1(state, expected_revision=3, target_revision=3)
    with pytest.raises(ValueError):
        replace(conflict, expected_revision=2)


def test_correction_request_shape_all_commands_and_serialization_are_exact() -> None:
    requests = tuple(
        SessionCommandCorrectionV1(
            expected_revision=1,
            target_revision=1,
            replacement_command=command,
        )
        for command in _all_commands(expected_revision=0)
    )
    assert [field.name for field in fields(SessionCommandCorrectionV1)] == [
        "session_history_edit_version",
        "expected_revision",
        "target_revision",
        "replacement_command",
    ]
    assert tuple(request.replacement_command.kind for request in requests) == tuple(
        command.kind for command in _all_commands()
    )
    assert all(not hasattr(request, "__dict__") for request in requests)
    first = requests[6].to_dict()
    second = requests[6].to_dict()
    first["replacement_command"]["event"]["nested"]["cards"][0] = "D7"
    assert second["replacement_command"]["event"]["nested"]["cards"] == ["CA"]
    json.dumps(second)
    with pytest.raises(FrozenInstanceError):
        requests[0].target_revision = 2


@pytest.mark.parametrize(
    ("expected_revision", "target_revision"),
    ((True, 1), (-1, 1), (1, 0), (1, True), (1, 2)),
)
def test_correction_request_rejects_invalid_revision_relationships(
    expected_revision: object,
    target_revision: object,
) -> None:
    with pytest.raises(ValueError):
        SessionCommandCorrectionV1(
            expected_revision=expected_revision,
            target_revision=target_revision,
            replacement_command=SetSessionGameMetadataCommandV1(
                expected_revision=0,
                game_id="replacement",
            ),
        )


def test_correction_request_requires_exact_command_and_matching_header() -> None:
    with pytest.raises(ValueError, match="SessionCommandV1"):
        SessionCommandCorrectionV1(
            expected_revision=1,
            target_revision=1,
            replacement_command=object(),
        )
    with pytest.raises(ValueError, match="target_revision - 1"):
        SessionCommandCorrectionV1(
            expected_revision=2,
            target_revision=2,
            replacement_command=SetSessionGameMetadataCommandV1(
                expected_revision=0,
                game_id="replacement",
            ),
        )


def test_correction_result_shape_all_statuses_and_serialization_are_exact() -> None:
    metadata = _metadata_state()
    applied = correct_session_command_v1(
        metadata,
        SessionCommandCorrectionV1(
            expected_revision=1,
            target_revision=1,
            replacement_command=SetSessionGameMetadataCommandV1(
                expected_revision=0,
                game_id="replacement",
            ),
        ),
    )
    unchanged = correct_session_command_v1(
        metadata,
        SessionCommandCorrectionV1(
            expected_revision=1,
            target_revision=1,
            replacement_command=metadata.command_log[0].command,
        ),
    )
    rejected = correct_session_command_v1(
        metadata,
        SessionCommandCorrectionV1(
            expected_revision=1,
            target_revision=1,
            replacement_command=RecordSessionDealtCardCommandV1(
                expected_revision=0,
                destination="player_hand",
                player_id="player-b",
                card="CA",
            ),
        ),
    )
    partial_source = _promoted_private_suffix_state()
    partial = correct_session_command_v1(
        partial_source,
        SessionCommandCorrectionV1(
            expected_revision=3,
            target_revision=2,
            replacement_command=SetSessionGameMetadataCommandV1(
                expected_revision=1,
                game_id="without-promotion",
            ),
        ),
    )
    conflict = correct_session_command_v1(
        metadata,
        SessionCommandCorrectionV1(
            expected_revision=2,
            target_revision=1,
            replacement_command=SetSessionGameMetadataCommandV1(
                expected_revision=0,
                game_id="future",
            ),
        ),
    )
    results = (applied, unchanged, partial, rejected, conflict)
    assert tuple(result.status for result in results) == SESSION_CORRECTION_STATUSES
    assert [field.name for field in fields(SessionCorrectionResultV1)] == [
        "session_history_edit_version",
        "status",
        "session_id",
        "expected_revision",
        "source_revision",
        "target_revision",
        "current_revision",
        "replacement_command",
        "state",
        "original_record",
        "replayed_suffix_records",
        "discarded_suffix_records",
        "failed_original_revision",
        "diagnostics",
    ]
    assert applied.state.command_log[0].command.game_id == "replacement"
    assert unchanged.state is metadata
    assert partial.failed_original_revision == 3
    assert rejected.failed_original_revision == 1
    assert conflict.original_record is None
    assert all(not hasattr(result, "__dict__") for result in results)

    first = partial.to_dict()
    second = partial.to_dict()
    first["discarded_suffix_records"][0]["command"]["card"] = "D8"
    assert second["discarded_suffix_records"][0]["command"]["card"] == "D7"
    json.dumps(second)


def test_correction_result_rejects_status_specific_invariant_failures() -> None:
    source = _metadata_state()
    applied = correct_session_command_v1(
        source,
        SessionCommandCorrectionV1(
            expected_revision=1,
            target_revision=1,
            replacement_command=SetSessionGameMetadataCommandV1(
                expected_revision=0,
                game_id="replacement",
            ),
        ),
    )
    with pytest.raises(ValueError):
        replace(applied, current_revision=0)
    with pytest.raises(ValueError):
        replace(applied, failed_original_revision=1)

    partial_source = _promoted_private_suffix_state()
    partial = correct_session_command_v1(
        partial_source,
        SessionCommandCorrectionV1(
            expected_revision=3,
            target_revision=2,
            replacement_command=SetSessionGameMetadataCommandV1(
                expected_revision=1,
                game_id="without-promotion",
            ),
        ),
    )
    with pytest.raises(ValueError):
        replace(partial, failed_original_revision=2)
    with pytest.raises(ValueError):
        replace(partial, discarded_suffix_records=())


def test_checkpoint_lineage_contract_is_strict_frozen_and_deterministic() -> None:
    lineage = SessionCheckpointLineageV1(
        relationship="ancestor",
        session_id="session-lineage",
        checkpoint_revision=4,
        state_revision=7,
    )
    assert [field.name for field in fields(SessionCheckpointLineageV1)] == [
        "session_checkpoint_lineage_version",
        "relationship",
        "session_id",
        "checkpoint_revision",
        "state_revision",
    ]
    assert lineage.to_dict() == {
        "session_checkpoint_lineage_version": 1,
        "relationship": "ancestor",
        "session_id": "session-lineage",
        "checkpoint_revision": 4,
        "state_revision": 7,
    }
    assert lineage.to_dict() == lineage.to_dict()
    with pytest.raises(FrozenInstanceError):
        lineage.relationship = "current"
    with pytest.raises(ValueError):
        replace(lineage, relationship="unknown")
    with pytest.raises(ValueError):
        replace(lineage, checkpoint_revision=True)
    with pytest.raises(ValueError):
        replace(lineage, state_revision=-1)
