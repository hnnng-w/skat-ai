import copy
import json
import random
from dataclasses import asdict
from pathlib import Path

import pytest
from test_historical_game import (
    build_historical_input,
    build_stub_expected_value_recommendation,
)
from test_training_dataset import build_training_input

from skat_ai.dataset_partition_audit import audit_training_dataset_partitions
from skat_ai.historical_decision_snapshot import build_historical_decision_snapshots
from skat_ai.historical_defender_open_play_continuation import (
    build_historical_continuation_public_hand_state,
    validate_historical_defender_open_play_continuation,
)
from skat_ai.historical_game import (
    build_historical_game_record,
    build_historical_game_summary,
    build_historical_game_summary_from_input,
    build_serializable_historical_record,
)
from skat_ai.historical_game_review import build_historical_game_review_summary
from skat_ai.historical_opponent_statistics import (
    aggregate_historical_opponent_statistics,
    build_exportable_opponent_statistics_input,
)
from skat_ai.historical_play_prefix import replay_historical_state_at_play_boundary
from skat_ai.historical_snapshot_adapter import build_position_from_historical_snapshot
from skat_ai.rolling_opponent_policy_evaluation import (
    build_serializable_rolling_opponent_policy_evaluation,
    evaluate_rolling_opponent_policy_predictions,
)
from skat_ai.simulation import generate_sampled_hidden_state
from skat_ai.training_dataset import (
    build_training_dataset_input,
    build_training_dataset_summary,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
NORMAL_EXAMPLE_PATH = PROJECT_ROOT / "examples" / "historical_grand_normal_completion.json"
CONTINUATION_EXAMPLE_PATH = (
    PROJECT_ROOT
    / "examples"
    / "historical_grand_defender_open_play_continuation.json"
)


def load_historical_data(path: Path = CONTINUATION_EXAMPLE_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))["historical_game_input"]


def build_event_record(
    after_play_count: int = 12,
    exposing_defender_player_id: str = "player-a",
) -> dict:
    data = load_historical_data(NORMAL_EXAMPLE_PATH)
    replay = replay_historical_state_at_play_boundary(
        build_historical_game_record(data),
        after_play_count,
    )
    data["game_id"] = "historical-grand-defender-open-play-continuation-test"
    data["game_events"] = [
        {
            "schema_version": 1,
            "kind": "defender_open_play_continuation",
            "after_play_count": after_play_count,
            "exposing_defender_player_id": exposing_defender_player_id,
            "exposed_cards": list(
                replay.remaining_hand_for(exposing_defender_player_id)
            ),
            "declarer_response": "request_continued_play",
        }
    ]
    return data


def decision_state(snapshot) -> dict:
    value = asdict(snapshot)
    value.pop("source_game_id")
    value.pop("source_played_at")
    return value


def test_event_is_canonical_round_trips_and_preserves_normal_completion() -> None:
    data = load_historical_data()
    record = build_historical_game_record(data)
    summary = build_historical_game_summary(record)
    event = summary["historical_game_events_summary"]["events"][0]

    assert record.game_end is None
    assert record.game_end_reason == "normal_completion"
    assert len(record.tricks) == 10
    assert sum(len(trick.plays) for trick in record.tricks) == 30
    assert build_serializable_historical_record(record)["game_events"] == [
        {
            "schema_version": 1,
            "kind": "defender_open_play_continuation",
            "after_play_count": 12,
            "exposing_defender_player_id": "player-a",
            "exposed_cards": ["CQ", "CJ", "C9", "C8", "C7", "S10"],
            "declarer_response": "request_continued_play",
        }
    ]
    assert event["card_reconciliation"] == "confirmed"
    assert event["after_completed_trick_count"] == 4
    assert event["event_during_incomplete_trick"] is False
    assert event["next_player_id"] == "player-a"
    assert event["non_exposing_defender_player_id"] == "player-c"
    assert event["first_affected_decision_index"] == 13
    assert event["actual_plays_after_event"] == 18
    actual_plays = tuple(
        play.card for trick in record.tricks for play in trick.plays
    )
    assert build_historical_continuation_public_hand_state(
        record.game_events[0], actual_plays[12:]
    ) == ()
    assert build_historical_game_summary_from_input(summary["record"]) == summary


def test_existing_normal_record_serialization_and_behavior_remain_unchanged() -> None:
    data = load_historical_data(NORMAL_EXAMPLE_PATH)
    summary = build_historical_game_summary_from_input(data)

    assert "game_events" not in summary["record"]
    assert "historical_game_events_summary" not in summary


@pytest.mark.parametrize("after_play_count", [0, 1, 2, 12, 13, 14, 29])
def test_all_supported_event_boundaries_are_exactly_replayed(
    after_play_count: int,
) -> None:
    exposing_defender_player_id = "player-c" if after_play_count == 29 else "player-a"
    data = build_event_record(after_play_count, exposing_defender_player_id)
    summary = build_historical_game_summary_from_input(data)
    event = summary["historical_game_events_summary"]["events"][0]

    assert event["after_play_count"] == after_play_count
    assert event["after_completed_trick_count"] == after_play_count // 3
    assert event["event_during_incomplete_trick"] is (after_play_count % 3 != 0)
    assert event["actual_plays_after_event"] == 30 - after_play_count
    assert event["exposed_card_count"] == len(data["game_events"][0]["exposed_cards"])


@pytest.mark.parametrize("after_play_count", [-1, True, 30, 31])
def test_invalid_event_boundaries_are_rejected(after_play_count) -> None:
    data = build_event_record()
    data["game_events"][0]["after_play_count"] = after_play_count

    with pytest.raises(ValueError, match="after_play_count"):
        build_historical_game_record(data)


def test_mid_trick_boundary_derives_exact_turn_hands_and_observed_points() -> None:
    record = build_historical_game_record(build_event_record(13))
    replay = replay_historical_state_at_play_boundary(record, 13)
    context = validate_historical_defender_open_play_continuation(
        record,
        record.game_events[0],
        replay,
    )

    assert replay.current_trick is not None
    assert replay.current_trick.leader_player_id == "player-a"
    assert replay.current_trick.plays == (("player-a", "CQ"),)
    assert replay.next_player_id == "player-b"
    assert {player_id: len(cards) for player_id, cards in replay.remaining_hands} == {
        "player-a": 5,
        "player-b": 6,
        "player-c": 6,
    }
    assert context.observed_declarer_points == 22
    assert context.observed_defender_points == 25


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda events: events.clear(), "exactly one"),
        (lambda events: events.append(copy.deepcopy(events[0])), "exactly one"),
        (lambda events: events[0].update({"schema_version": 2}), "schema_version"),
        (lambda events: events[0].update({"kind": "future_event"}), "unsupported"),
        (lambda events: events[0].pop("after_play_count"), "missing required fields"),
        (lambda events: events[0].update({"extra": True}), "unsupported fields"),
        (
            lambda events: events[0].update({"declarer_response": "accept_adjudication"}),
            "terminal game_end_reason",
        ),
        (
            lambda events: events[0].update({"declarer_response": " request_continued_play"}),
            "declarer_response",
        ),
    ],
)
def test_version_one_event_union_is_strict(mutation, message: str) -> None:
    data = build_event_record()
    mutation(data["game_events"])

    with pytest.raises(ValueError, match=message):
        build_historical_game_record(data)


@pytest.mark.parametrize(
    ("exposing_id", "message"),
    [
        ("player-b", "defender"),
        ("missing-player", "stable participant"),
        (" player-a", "non-padded"),
        ("left", "relative identity"),
    ],
)
def test_exposing_player_requires_an_exact_stable_defender(
    exposing_id: str,
    message: str,
) -> None:
    data = build_event_record()
    data["game_events"][0]["exposing_defender_player_id"] = exposing_id

    with pytest.raises(ValueError, match=message):
        build_historical_game_record(data)


@pytest.mark.parametrize(
    "cards",
    [[], ["CQ", "CQ"], ["X1"], ["CQ"], ["CQ", "CJ", "C9", "C8", "C7", "S10", "D9"]],
)
def test_exposed_cards_must_be_valid_unique_and_exact(cards: list[str]) -> None:
    data = build_event_record()
    data["game_events"][0]["exposed_cards"] = cards

    with pytest.raises(ValueError, match="exposed_cards"):
        build_historical_game_summary_from_input(data)


@pytest.mark.parametrize(
    "path_name",
    [
        "historical_grand_declarer_concession.json",
        "historical_grand_defender_concession.json",
        "historical_grand_declarer_card_exposure.json",
        "historical_grand_defender_open_play.json",
        "historical_grand_open_card_throw.json",
    ],
)
def test_continuation_event_cannot_be_combined_with_a_terminal_end(
    path_name: str,
) -> None:
    data = load_historical_data(PROJECT_ROOT / "examples" / path_name)
    data["game_events"] = copy.deepcopy(build_event_record()["game_events"])

    with pytest.raises(ValueError, match="requires game_end_reason='normal_completion'"):
        build_historical_game_record(data)


def test_snapshot_boundary_is_exact_and_known_hand_only_shrinks() -> None:
    event_summary = build_historical_game_summary_from_input(build_event_record())
    no_event_summary = build_historical_game_summary_from_input(
        load_historical_data(NORMAL_EXAMPLE_PATH)
    )
    event_rows = build_historical_decision_snapshots(event_summary)
    no_event_rows = build_historical_decision_snapshots(no_event_summary)

    assert event_rows.snapshot_count == 30
    assert [decision_state(row) for row in event_rows.snapshots[:12]] == [
        decision_state(row) for row in no_event_rows.snapshots[:12]
    ]
    assert all(
        not row.visible_state.public_exposed_cards
        for row in event_rows.snapshots[:12]
    )
    assert event_rows.snapshots[12].visible_state.public_exposed_cards[0].cards == (
        "CQ",
        "CJ",
        "C9",
        "C8",
        "C7",
        "S10",
    )
    assert event_rows.snapshots[13].visible_state.public_exposed_cards[0].cards == (
        "CJ",
        "C9",
        "C8",
        "C7",
        "S10",
    )
    exposed_sets = [
        set(row.visible_state.public_exposed_cards[0].cards)
        for row in event_rows.snapshots[12:]
    ]
    assert all(
        later <= earlier
        for earlier, later in zip(exposed_sets, exposed_sets[1:], strict=False)
    )
    assert event_rows.snapshots[-1].visible_state.public_exposed_cards[0].cards == ()


def test_zero_and_twenty_nine_boundaries_affect_exactly_the_expected_snapshots() -> None:
    all_post_event = build_historical_decision_snapshots(
        build_historical_game_summary_from_input(build_event_record(0))
    ).snapshots
    final_only = build_historical_decision_snapshots(
        build_historical_game_summary_from_input(build_event_record(29, "player-c"))
    ).snapshots

    assert all(row.visible_state.public_exposed_cards for row in all_post_event)
    assert all(
        not row.visible_state.public_exposed_cards for row in final_only[:29]
    )
    assert final_only[29].visible_state.public_exposed_cards[0].cards == ("D9",)


def test_exposing_defender_need_not_be_the_next_player() -> None:
    summary = build_historical_game_summary_from_input(
        build_event_record(12, "player-c")
    )
    event = summary["historical_game_events_summary"]["events"][0]

    assert event["exposing_defender_player_id"] == "player-c"
    assert event["next_player_id"] == "player-a"


def test_public_defender_cards_improve_only_authorized_visible_matador_inference() -> None:
    event_rows = build_historical_decision_snapshots(
        build_historical_game_summary_from_input(build_event_record())
    ).snapshots
    no_event_rows = build_historical_decision_snapshots(
        build_historical_game_summary_from_input(
            load_historical_data(NORMAL_EXAMPLE_PATH)
        )
    ).snapshots

    assert [row.visible_state.declaration.matadors for row in event_rows[:12]] == [
        row.visible_state.declaration.matadors for row in no_event_rows[:12]
    ]
    assert no_event_rows[14].visible_state.declaration.matadors is None
    assert event_rows[14].visible_state.declaration.matadors == 1
    assert [
        index
        for index, (without_event, with_event) in enumerate(
            zip(no_event_rows, event_rows, strict=True),
            start=1,
        )
        if without_event.visible_state.declaration.matadors
        != with_event.visible_state.declaration.matadors
    ] == [15]


def test_declared_ouvert_and_continuation_hands_remain_independent_and_ordered() -> None:
    data = build_historical_input(game_type="null", hand_game=True)
    data["declaration"]["ouvert"] = True
    record_without_event = build_historical_game_record(data)
    replay = replay_historical_state_at_play_boundary(record_without_event, 12)
    data["game_events"] = [
        {
            "schema_version": 1,
            "kind": "defender_open_play_continuation",
            "after_play_count": 12,
            "exposing_defender_player_id": "player-a",
            "exposed_cards": list(replay.remaining_hand_for("player-a")),
            "declarer_response": "request_continued_play",
        }
    ]
    rows = build_historical_decision_snapshots(
        build_historical_game_summary_from_input(data)
    ).snapshots

    assert [exposure.player_id for exposure in rows[11].visible_state.public_exposed_cards] == [
        "player-b"
    ]
    assert [exposure.player_id for exposure in rows[12].visible_state.public_exposed_cards] == [
        "player-a",
        "player-b",
    ]
    position = build_position_from_historical_snapshot(rows[12], record_without_event)
    assert [constraint.source for constraint in position.public_hand_constraints] == [
        "defender_open_play_continuation",
        "declared_ouvert",
    ]
    assert set(position.public_hand_constraints[0].cards).isdisjoint(
        position.public_hand_constraints[1].cards
    )
    sampled = generate_sampled_hidden_state(
        position.state,
        position.left_hand_size,
        position.right_hand_size,
        random.Random(42),
        position.public_hand_constraints,
    )
    sampled_by_player = {
        "left": sampled.left_hand,
        "right": sampled.right_hand,
    }
    for constraint in position.public_hand_constraints:
        if constraint.player != "me":
            assert sampled_by_player[constraint.player] == list(constraint.cards)


@pytest.mark.parametrize("decision_index", [13, 14, 15])
def test_review_adapter_maps_the_public_defender_to_me_left_and_right(
    decision_index: int,
) -> None:
    data = build_event_record()
    record = build_historical_game_record(data)
    snapshots = build_historical_decision_snapshots(build_historical_game_summary(record))
    snapshot = snapshots.snapshots[decision_index - 1]
    position = build_position_from_historical_snapshot(snapshot, record)
    constraint = position.public_hand_constraints[0]
    expected_relative = {
        stable_id: relative
        for relative, stable_id in snapshot.relative_player_map.items()
    }["player-a"]

    assert constraint.player == expected_relative
    assert constraint.source == "defender_open_play_continuation"
    assert constraint.visibility_scope == "all_players"
    if constraint.player in {"left", "right"}:
        sampled = generate_sampled_hidden_state(
            position.state,
            position.left_hand_size,
            position.right_hand_size,
            random.Random(42),
            position.public_hand_constraints,
        )
        sampled_hand = sampled.left_hand if constraint.player == "left" else sampled.right_hand
        assert sampled_hand == list(constraint.cards)


def test_review_reuses_the_same_exact_constraint_without_event_decisions(
    monkeypatch,
) -> None:
    captured_constraints = []

    def capture_constraint(*args, public_hand_constraints=(), **kwargs):
        captured_constraints.append(public_hand_constraints)
        return build_stub_expected_value_recommendation(
            *args,
            public_hand_constraints=public_hand_constraints,
            **kwargs,
        )

    monkeypatch.setattr(
        "skat_ai.historical_game_review.recommend_card_by_expected_value",
        capture_constraint,
    )
    data = build_event_record()
    record = build_historical_game_record(data)
    snapshots = build_historical_decision_snapshots(build_historical_game_summary(record))
    review = build_historical_game_review_summary(
        snapshots,
        record,
        sample_count=1,
        base_random_seed=42,
    )

    assert review["decision_count"] == 30
    assert review["reviewed_decision_count"] == 30
    assert captured_constraints[:12] == [()] * 12
    assert all(len(constraints) == 1 for constraints in captured_constraints[12:])
    assert all(
        constraints[0].source == "defender_open_play_continuation"
        for constraints in captured_constraints[12:]
    )


def test_training_retains_thirty_actual_card_targets_and_safe_event_boundary() -> None:
    event_data = build_event_record()
    dataset = build_training_dataset_input(
        build_training_input([event_data], ["train"])
    )
    training = build_training_dataset_summary(dataset)
    samples = training["records"][0]["samples"]

    assert training["feature_generation_version"] == 1
    assert training["target"] == "actual_card_played"
    assert len(samples) == 30
    assert [sample["sample_id"] for sample in samples] == [
        f"record-001:{index}" for index in range(1, 31)
    ]
    assert all(not sample["features"]["public_exposed_cards"] for sample in samples[:12])
    assert samples[12]["features"]["public_exposed_cards"][0]["cards"] == [
        "CQ",
        "CJ",
        "C9",
        "C8",
        "C7",
        "S10",
    ]
    serialized_features = json.dumps([sample["features"] for sample in samples])
    for forbidden in (
        "declarer_response",
        "rest_trick_claim",
        "final_settlement_summary",
    ):
        assert forbidden not in serialized_features


def test_final_result_settlement_statistics_and_partition_match_no_event_game() -> None:
    normal_data = load_historical_data(NORMAL_EXAMPLE_PATH)
    event_data = build_event_record()
    normal = build_historical_game_summary_from_input(normal_data)
    event = build_historical_game_summary_from_input(event_data)
    parity_fields = (
        "derived_tricks",
        "declarer_trick_points",
        "defender_trick_points",
        "declarer_points",
        "defender_points",
        "winner",
        "schneider_status",
        "schwarz_status",
        "game_result_summary",
        "game_value_summary",
        "overbid_summary",
        "final_settlement_summary",
    )
    assert all(normal[field] == event[field] for field in parity_fields)

    event_dataset = build_training_dataset_input(
        build_training_input([event_data], ["train"])
    )
    normal_dataset = build_training_dataset_input(
        build_training_input([normal_data], ["train"])
    )
    event_statistics = build_exportable_opponent_statistics_input(
        aggregate_historical_opponent_statistics(event_dataset)
    )
    normal_statistics = build_exportable_opponent_statistics_input(
        aggregate_historical_opponent_statistics(normal_dataset)
    )
    assert event_statistics.records == normal_statistics.records
    audit = audit_training_dataset_partitions(event_dataset, "known_opponent")
    assert audit.partition_summary["train"]["record_count"] == 1
    assert audit.partition_summary["train"]["distinct_player_count"] == 3


def test_rolling_source_and_target_remain_one_game_and_thirty_decisions() -> None:
    source = build_event_record()
    source["played_at"] = "2026-07-10T12:00:00Z"
    target = build_event_record()
    target["game_id"] = "historical-continuation-target"
    target["played_at"] = "2026-07-11T12:00:00Z"
    dataset = build_training_dataset_input(
        build_training_input([source, target], ["train", "validation"])
    )
    result = build_serializable_rolling_opponent_policy_evaluation(
        evaluate_rolling_opponent_policy_predictions(dataset)
    )

    assert result["selection"]["source_record_count"] == 1
    assert result["selection"]["target_decision_count"] == 30
    assert result["target_games"][0]["decision_count"] == 30
    serialized = json.dumps(result["target_games"][0]["decisions"])
    assert "request_continued_play" not in serialized
    assert "rest_trick_claim" not in serialized


def test_continuation_never_invokes_exact_rest_trick_proof(
    monkeypatch,
) -> None:
    def fail_proof(*args, **kwargs):
        raise AssertionError("The continuation event must not invoke exact proof.")

    monkeypatch.setattr("skat_ai.defender_open_play.prove_defender_rest_tricks", fail_proof)
    monkeypatch.setattr(
        "skat_ai.historical_game_review.recommend_card_by_expected_value",
        build_stub_expected_value_recommendation,
    )
    data = build_event_record()
    record = build_historical_game_record(data)
    summary = build_historical_game_summary(record)
    snapshots = build_historical_decision_snapshots(summary)
    review = build_historical_game_review_summary(snapshots, record, sample_count=1)

    event = summary["historical_game_events_summary"]["events"][0]
    assert review["decision_count"] == 30
    assert event["exact_proof_applied"] is False
    assert event["game_end_applied"] is False
    assert event["settlement_applied"] is False
    assert "point_accounting" not in summary
    assert "historical_game_end_summary" not in summary


def test_package_version_is_0_9_0() -> None:
    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'version = "0.9.0"' in pyproject
