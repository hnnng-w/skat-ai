import json
from dataclasses import FrozenInstanceError, fields, replace
from types import MappingProxyType

import pytest
from test_match_capture_contracts import _capture, _participants, _snapshot

from skat_ai.match_player_snapshot import MatchPlayerStatisticsSnapshotV1
from skat_ai.match_player_statistics_context import (
    MATCH_PLAYER_STATISTICS_CONTEXT_VERSION,
    MATCH_PLAYER_STATISTICS_HISTORY_POLICY,
    MATCH_PLAYER_STATISTICS_PROFILE_POLICY,
    MATCH_PLAYER_STATISTICS_SNAPSHOT_POLICY,
    MATCH_PLAYER_STATISTICS_TEMPORAL_POLICY,
    MATCH_PLAYER_STATISTICS_TEMPORAL_STATUSES,
    MatchPlayerStatisticsContextV1,
    build_match_player_statistics_context_v1,
)
from skat_ai.match_player_statistics_preparation import (
    MATCH_PLAYER_STATISTICS_INPUT_POLICY,
    MATCH_PLAYER_STATISTICS_PREPARATION_STATUSES,
    MATCH_PLAYER_STATISTICS_PREPARATION_VERSION,
    MatchPlayerStatisticsPreparationV1,
    build_match_player_statistics_preparation_v1,
)
from skat_ai.opponent_profile_derivation import derive_opponent_profile
from skat_ai.opponent_statistics import (
    build_player_profile_from_opponent_statistics,
    build_serializable_opponent_statistics_input,
)


def _capture_with_snapshots(*, played_at="2026-08-09T18:00:00Z", snapshots=()):
    participants = list(_participants(snapshots=False))
    for index, snapshot in enumerate(snapshots):
        participants[index] = replace(
            participants[index],
            statistics_snapshot=snapshot,
        )
    return _capture(played_at=played_at, participants=tuple(participants))


def test_versions_tuples_policies_and_fields_are_exact() -> None:
    assert MATCH_PLAYER_STATISTICS_CONTEXT_VERSION == 1
    assert MATCH_PLAYER_STATISTICS_PREPARATION_VERSION == 1
    assert MATCH_PLAYER_STATISTICS_TEMPORAL_STATUSES == (
        "absent",
        "eligible",
        "match_time_unavailable",
        "captured_not_before_match",
    )
    assert MATCH_PLAYER_STATISTICS_PREPARATION_STATUSES == (
        "available",
        "unavailable",
    )
    assert MATCH_PLAYER_STATISTICS_SNAPSHOT_POLICY == (
        "one_match_bound_snapshot_per_participant"
    )
    assert MATCH_PLAYER_STATISTICS_TEMPORAL_POLICY == (
        "captured_strictly_before_match_start"
    )
    assert MATCH_PLAYER_STATISTICS_PROFILE_POLICY == (
        "reuse_existing_rule_based_derivation"
    )
    assert MATCH_PLAYER_STATISTICS_INPUT_POLICY == (
        "eligible_records_in_canonical_table_place_order"
    )
    assert MATCH_PLAYER_STATISTICS_HISTORY_POLICY == (
        "later_matches_use_separate_immutable_snapshots"
    )
    assert tuple(field.name for field in fields(MatchPlayerStatisticsContextV1)) == (
        "match_player_statistics_context_version",
        "player_id",
        "table_place",
        "snapshot_id",
        "observed_at",
        "temporal_status",
        "eligible_for_match_analysis",
        "normalized_profile",
        "profile_derivation",
    )
    assert tuple(
        field.name for field in fields(MatchPlayerStatisticsPreparationV1)
    ) == (
        "match_player_statistics_preparation_version",
        "status",
        "match_id",
        "match_played_at",
        "participant_contexts",
        "opponent_statistics_input",
        "eligible_player_ids",
        "actionable_player_ids",
    )


@pytest.mark.parametrize(
    ("played_at", "expected_status", "eligible"),
    (
        ("2026-08-09T18:00:00Z", "eligible", True),
        (None, "match_time_unavailable", False),
        ("2026-07-23T10:00:00Z", "captured_not_before_match", False),
        ("2026-07-23T09:59:59Z", "captured_not_before_match", False),
        ("2026-07-23T12:00:00+02:00", "captured_not_before_match", False),
    ),
)
def test_context_temporal_status_is_strict_and_offset_aware(
    played_at: str | None,
    expected_status: str,
    eligible: bool,
) -> None:
    capture = _capture_with_snapshots(played_at=played_at, snapshots=(_snapshot(),))
    context = build_match_player_statistics_context_v1(
        capture,
        player_id="player-a",
    )
    assert context.temporal_status == expected_status
    assert context.eligible_for_match_analysis is eligible
    assert context.snapshot_id == "snapshot-a"
    assert context.observed_at == "2026-07-23T10:00:00Z"


def test_absent_context_has_no_snapshot_or_profile_values() -> None:
    context = build_match_player_statistics_context_v1(
        _capture_with_snapshots(),
        player_id="player-b",
    )
    assert context.to_dict() == {
        "match_player_statistics_context_version": 1,
        "player_id": "player-b",
        "table_place": "place_2",
        "snapshot_id": None,
        "observed_at": None,
        "temporal_status": "absent",
        "eligible_for_match_analysis": False,
        "normalized_profile": None,
        "profile_derivation": None,
    }


def test_context_reuses_existing_profile_conversion_and_derivation_exactly() -> None:
    capture = _capture_with_snapshots(snapshots=(_snapshot(),))
    context = build_match_player_statistics_context_v1(
        capture,
        player_id="player-a",
    )
    record = capture.participants[0].statistics_snapshot.statistics_record
    expected_profile = build_player_profile_from_opponent_statistics(record)
    expected_derivation = derive_opponent_profile(expected_profile)
    assert context.normalized_profile == expected_profile
    assert context.profile_derivation == expected_derivation
    assert type(context.profile_derivation.confidence) is MappingProxyType
    with pytest.raises(TypeError):
        context.profile_derivation.confidence["overall"] = None
    assert context.profile_derivation.confidence["overall"].level == "medium"
    assert context.profile_derivation.classification == "aggressive"
    assert context.profile_derivation.derivation_status == "insufficient_confidence"
    assert context.profile_derivation.actionable_policy_preset is None


def _actionable_snapshot(player_id: str, snapshot_id: str):
    source = _snapshot(player_id, snapshot_id)
    return MatchPlayerStatisticsSnapshotV1(
        snapshot_id=snapshot_id,
        observed_at=source.observed_at,
        statistics_record=replace(source.statistics_record, games_played=1000),
    )


def test_context_exposes_existing_actionable_profile_behavior() -> None:
    context = build_match_player_statistics_context_v1(
        _capture_with_snapshots(
            snapshots=(_actionable_snapshot("player-a", "snapshot-a"),)
        ),
        player_id="player-a",
    )
    assert context.profile_derivation.confidence["declarer"].level == "medium"
    assert context.profile_derivation.classification == "aggressive"
    assert context.profile_derivation.derivation_status == "actionable"
    assert context.profile_derivation.recommended_policy_preset == "aggressive_points"
    assert context.profile_derivation.actionable_policy_preset == "aggressive_points"


def test_preparation_uses_canonical_eligible_order_and_keeps_perspective_player() -> None:
    capture = _capture_with_snapshots(
        snapshots=(
            _actionable_snapshot("player-a", "snapshot-a"),
            _actionable_snapshot("player-b", "snapshot-b"),
            _actionable_snapshot("player-c", "snapshot-c"),
        )
    )
    preparation = build_match_player_statistics_preparation_v1(capture)
    assert preparation.status == "available"
    assert preparation.match_id == capture.match_id
    assert preparation.match_played_at == capture.played_at
    assert tuple(
        (context.table_place, context.player_id)
        for context in preparation.participant_contexts
    ) == (
        ("place_1", "player-a"),
        ("place_2", "player-b"),
        ("place_3", "player-c"),
    )
    assert preparation.eligible_player_ids == (
        "player-a",
        "player-b",
        "player-c",
    )
    assert preparation.actionable_player_ids == (
        "player-a",
        "player-b",
        "player-c",
    )
    assert preparation.opponent_statistics_input is not None
    assert tuple(
        record.player_id for record in preparation.opponent_statistics_input.records
    ) == preparation.eligible_player_ids
    serialized = preparation.to_dict()["opponent_statistics_input"]
    assert serialized == build_serializable_opponent_statistics_input(
        preparation.opponent_statistics_input
    )["opponent_statistics_input"]


def test_preparation_excludes_ineligible_records_but_retains_contexts() -> None:
    capture = _capture_with_snapshots(
        played_at=None,
        snapshots=(_snapshot(), _snapshot("player-b", "snapshot-b")),
    )
    preparation = build_match_player_statistics_preparation_v1(capture)
    assert preparation.status == "unavailable"
    assert preparation.opponent_statistics_input is None
    assert preparation.eligible_player_ids == ()
    assert preparation.actionable_player_ids == ()
    assert tuple(context.temporal_status for context in preparation.participant_contexts) == (
        "match_time_unavailable",
        "match_time_unavailable",
        "absent",
    )


def test_context_and_preparation_are_frozen_slotted_and_defensively_serialized() -> None:
    preparation = build_match_player_statistics_preparation_v1(
        _capture_with_snapshots(snapshots=(_snapshot(),))
    )
    context = preparation.participant_contexts[0]
    assert not hasattr(context, "__dict__")
    assert not hasattr(preparation, "__dict__")
    with pytest.raises(FrozenInstanceError):
        context.temporal_status = "absent"
    first = preparation.to_dict()
    second = preparation.to_dict()
    first["participant_contexts"][0]["normalized_profile"]["games_played"] = 1
    first["participant_contexts"][0]["profile_derivation"]["signals"].clear()
    assert second == preparation.to_dict()
    json.dumps(second, allow_nan=False)


@pytest.mark.parametrize("version", (2, True, 1.0))
def test_context_and_preparation_reject_wrong_versions(version) -> None:
    context = build_match_player_statistics_context_v1(
        _capture_with_snapshots(),
        player_id="player-a",
    )
    with pytest.raises(ValueError):
        replace(context, match_player_statistics_context_version=version)
    preparation = build_match_player_statistics_preparation_v1(
        _capture_with_snapshots()
    )
    with pytest.raises(ValueError):
        replace(preparation, match_player_statistics_preparation_version=version)
