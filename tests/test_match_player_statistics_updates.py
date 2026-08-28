import json
from dataclasses import FrozenInstanceError, fields, replace

import pytest
from test_match_capture_contracts import _statistics_record
from test_match_workspace_contracts import _definition, _observed_game

from skatmind.match_player_statistics_updates import (
    MATCH_PLAYER_STATISTICS_UPDATE_OPERATIONS,
    MATCH_PLAYER_STATISTICS_UPDATE_STATUSES,
    MATCH_PLAYER_STATISTICS_UPDATE_VERSION,
    MatchPlayerStatisticsUpdateResultV1,
    build_default_match_player_statistics_snapshot_id_v1,
    clear_match_player_statistics_snapshot_v1,
    set_match_player_statistics_snapshot_v1,
)
from skatmind.match_workspace_contracts import create_match_workspace_v1
from skatmind.match_workspace_operations import set_match_workspace_observed_game_v1


def _workspace_with_snapshot():
    definition = _definition()
    workspace = create_match_workspace_v1(definition)
    return set_match_player_statistics_snapshot_v1(
        workspace,
        player_id="player-a",
        observed_at="2026-07-23T10:00:00Z",
        statistics_record=_statistics_record("player-a"),
        expected_revision=0,
    ).workspace_change.workspace


def test_versions_tuples_and_result_fields_are_exact() -> None:
    assert MATCH_PLAYER_STATISTICS_UPDATE_VERSION == 1
    assert MATCH_PLAYER_STATISTICS_UPDATE_OPERATIONS == (
        "set_snapshot",
        "clear_snapshot",
    )
    assert MATCH_PLAYER_STATISTICS_UPDATE_STATUSES == (
        "applied",
        "unchanged",
        "revision_conflict",
    )
    assert tuple(field.name for field in fields(MatchPlayerStatisticsUpdateResultV1)) == (
        "match_player_statistics_update_version",
        "operation",
        "status",
        "player_id",
        "workspace_change",
        "player_context",
        "preparation",
    )


@pytest.mark.parametrize("version", (2, True, 1.0))
def test_update_result_rejects_wrong_version(version) -> None:
    workspace = create_match_workspace_v1(_definition())
    result = clear_match_player_statistics_snapshot_v1(
        workspace,
        player_id="player-a",
        expected_revision=0,
    )
    with pytest.raises(ValueError):
        replace(result, match_player_statistics_update_version=version)


def test_default_snapshot_id_is_revision_bound_and_deterministic() -> None:
    workspace = create_match_workspace_v1(_definition())
    assert build_default_match_player_statistics_snapshot_id_v1(
        workspace,
        player_id="player-b",
    ) == "match-160-player-b-statistics-r1"
    occupied = set_match_workspace_observed_game_v1(
        workspace,
        _observed_game(workspace.match_definition),
        expected_revision=0,
    ).workspace
    assert build_default_match_player_statistics_snapshot_id_v1(
        occupied,
        player_id="player-b",
    ) == "match-160-player-b-statistics-r2"


def test_set_applies_once_preserves_source_and_all_slots() -> None:
    source = create_match_workspace_v1(_definition())
    result = set_match_player_statistics_snapshot_v1(
        source,
        player_id="player-a",
        observed_at="2026-07-23T10:00:00Z",
        statistics_record=_statistics_record("player-a"),
        expected_revision=0,
    )
    assert result.operation == "set_snapshot"
    assert result.status == result.workspace_change.status == "applied"
    assert result.workspace_change.operation == "replace_definition"
    assert result.workspace_change.current_revision == 1
    assert result.workspace_change.workspace.slots == source.slots
    assert source.revision == 0
    assert source.match_definition.participants[0].statistics_snapshot is None
    snapshot = result.workspace_change.workspace.match_definition.participants[
        0
    ].statistics_snapshot
    assert snapshot.snapshot_id == "match-160-player-a-statistics-r1"
    assert result.player_context.snapshot_id == snapshot.snapshot_id
    assert result.preparation.eligible_player_ids == ("player-a",)


def test_equal_semantic_submission_preserves_id_and_is_unchanged() -> None:
    workspace = _workspace_with_snapshot()
    existing = workspace.match_definition.participants[0].statistics_snapshot
    result = set_match_player_statistics_snapshot_v1(
        workspace,
        player_id="player-a",
        observed_at="2026-07-23T12:00:00+02:00",
        statistics_record=_statistics_record("player-a"),
        expected_revision=workspace.revision,
    )
    assert result.status == "unchanged"
    assert result.workspace_change.workspace is workspace
    assert result.workspace_change.workspace.revision == 1
    assert result.player_context.snapshot_id == existing.snapshot_id


def test_replace_accepts_explicit_new_id_and_rejects_reuse_with_changed_content() -> None:
    workspace = _workspace_with_snapshot()
    changed_record = _statistics_record("player-a", "manual_entry")
    replaced = set_match_player_statistics_snapshot_v1(
        workspace,
        player_id="player-a",
        observed_at="2026-08-10T10:00:00Z",
        statistics_record=changed_record,
        expected_revision=1,
        snapshot_id="explicit-replacement",
    )
    assert replaced.status == "applied"
    assert replaced.workspace_change.workspace.revision == 2
    assert replaced.player_context.snapshot_id == "explicit-replacement"
    with pytest.raises(ValueError, match="cannot be reused"):
        set_match_player_statistics_snapshot_v1(
            workspace,
            player_id="player-a",
            observed_at="2026-08-10T10:00:00Z",
            statistics_record=changed_record,
            expected_revision=1,
            snapshot_id=workspace.match_definition.participants[
                0
            ].statistics_snapshot.snapshot_id,
        )


def test_set_enforces_player_label_time_and_unique_snapshot_ids() -> None:
    workspace = _workspace_with_snapshot()
    with pytest.raises(ValueError, match="Player ID"):
        set_match_player_statistics_snapshot_v1(
            workspace,
            player_id="player-b",
            observed_at="2026-07-23T10:00:00Z",
            statistics_record=_statistics_record("player-a"),
            expected_revision=1,
        )
    labeled = replace(_statistics_record("player-c"), player_label="Different Label")
    with pytest.raises(ValueError, match="labels must agree"):
        set_match_player_statistics_snapshot_v1(
            workspace,
            player_id="player-c",
            observed_at="2026-07-23T10:00:00Z",
            statistics_record=labeled,
            expected_revision=1,
        )
    unlabeled = replace(_statistics_record("player-b"), player_label=None)
    with pytest.raises(ValueError, match="same instant"):
        set_match_player_statistics_snapshot_v1(
            workspace,
            player_id="player-b",
            observed_at="2026-07-23T10:00:01Z",
            statistics_record=unlabeled,
            expected_revision=1,
        )
    with pytest.raises(ValueError, match="unique"):
        set_match_player_statistics_snapshot_v1(
            workspace,
            player_id="player-b",
            observed_at="2026-07-23T10:00:00Z",
            statistics_record=unlabeled,
            expected_revision=1,
            snapshot_id=workspace.match_definition.participants[
                0
            ].statistics_snapshot.snapshot_id,
        )


def test_revision_conflict_precedes_snapshot_payload_semantics() -> None:
    workspace = create_match_workspace_v1(_definition())
    result = set_match_player_statistics_snapshot_v1(
        workspace,
        player_id="player-a",
        observed_at="invalid",
        statistics_record="invalid",
        expected_revision=9,
        snapshot_id=" invalid",
    )
    assert result.status == "revision_conflict"
    assert result.workspace_change.workspace is workspace
    assert result.player_context.temporal_status == "absent"
    assert result.preparation.status == "unavailable"


def test_clear_applies_once_then_is_unchanged_and_conflict_preserves_revision() -> None:
    workspace = _workspace_with_snapshot()
    cleared = clear_match_player_statistics_snapshot_v1(
        workspace,
        player_id="player-a",
        expected_revision=1,
    )
    assert cleared.status == "applied"
    assert cleared.workspace_change.workspace.revision == 2
    assert cleared.workspace_change.workspace.slots == workspace.slots
    assert cleared.player_context.temporal_status == "absent"
    unchanged = clear_match_player_statistics_snapshot_v1(
        cleared.workspace_change.workspace,
        player_id="player-a",
        expected_revision=2,
    )
    assert unchanged.status == "unchanged"
    assert unchanged.workspace_change.workspace is cleared.workspace_change.workspace
    conflicted = clear_match_player_statistics_snapshot_v1(
        workspace,
        player_id="player-a",
        expected_revision=99,
    )
    assert conflicted.status == "revision_conflict"
    assert conflicted.workspace_change.workspace is workspace


def test_result_is_frozen_slotted_and_defensively_serialized() -> None:
    source = create_match_workspace_v1(_definition())
    result = set_match_player_statistics_snapshot_v1(
        source,
        player_id="player-a",
        observed_at="2026-07-23T10:00:00Z",
        statistics_record=_statistics_record("player-a"),
        expected_revision=0,
    )
    assert not hasattr(result, "__dict__")
    with pytest.raises(FrozenInstanceError):
        result.status = "unchanged"
    first = result.to_dict()
    second = result.to_dict()
    first["preparation"]["eligible_player_ids"].clear()
    first["workspace_change"]["workspace"]["slots"].clear()
    assert second == result.to_dict()
    json.dumps(second, allow_nan=False)


def test_internal_updates_accept_historical_statistics_records() -> None:
    workspace = create_match_workspace_v1(_definition())
    result = set_match_player_statistics_snapshot_v1(
        workspace,
        player_id="player-a",
        observed_at="2026-07-20T19:00:00+02:00",
        statistics_record=_statistics_record("player-a", "historical_games"),
        expected_revision=0,
    )
    assert result.status == "applied"
    snapshot = result.workspace_change.workspace.match_definition.participants[
        0
    ].statistics_snapshot
    assert snapshot.statistics_record.source.source_type == "historical_games"
    assert snapshot.statistics_record.source.historical_aggregation is not None
