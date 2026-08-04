import copy
import json
from dataclasses import asdict
from pathlib import Path

import pytest
from test_historical_declarer_card_exposure import build_exposure_prefix
from test_historical_declarer_concession import build_concession_prefix
from test_historical_defender_concession import build_defender_concession_prefix
from test_historical_defender_open_play import build_open_play_prefix
from test_historical_game import build_historical_input
from test_historical_opponent_profiles import stub_expected_value_recommendation
from test_training_dataset import build_training_input

from skat_ai.dataset_partition_audit import audit_training_dataset_partitions
from skat_ai.historical_decision_snapshot import build_historical_decision_snapshots
from skat_ai.historical_game import (
    build_historical_game_record,
    build_historical_game_summary_from_input,
)
from skat_ai.historical_game_review import build_historical_game_review_summary
from skat_ai.historical_opponent_statistics import (
    aggregate_historical_opponent_statistics,
    build_exportable_opponent_statistics_input,
)
from skat_ai.rolling_opponent_policy_evaluation import (
    build_serializable_rolling_opponent_policy_evaluation,
    evaluate_rolling_opponent_policy_predictions,
)
from skat_ai.training_dataset import (
    build_training_dataset_input,
    build_training_dataset_summary,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_PATH = PROJECT_ROOT / "examples" / "historical_grand_open_card_throw.json"


def load_example() -> dict:
    with EXAMPLE_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)["historical_game_input"]


def build_throw_prefix(
    *,
    completed_trick_count: int = 8,
    current_trick_card_count: int = 0,
    throwing_player_id: str = "player-a",
    game_type: str = "grand",
    hand_game: bool = False,
    ouvert: bool = False,
    declarer_player_id: str = "player-b",
) -> dict:
    data = build_historical_input(
        game_type=game_type,
        hand_game=hand_game,
        declarer_player_id=declarer_player_id,
    )
    tricks = copy.deepcopy(data["tricks"][:completed_trick_count])
    if current_trick_card_count:
        current = copy.deepcopy(data["tricks"][completed_trick_count])
        current["plays"] = current["plays"][:current_trick_card_count]
        tricks.append(current)
    data["tricks"] = tricks
    data["game_end_reason"] = "open_card_throw"
    data["declaration"]["ouvert"] = ouvert
    if game_type == "null":
        data["declaration"].pop("matadors", None)
    playable_hand = list(
        next(
            player["initial_hand"]
            for player in data["players"]
            if player["player_id"] == throwing_player_id
        )
    )
    if throwing_player_id == data["declarer_player_id"] and not hand_game:
        playable_hand.extend(data["skat"])
        for card in data["discarded_cards"]:
            playable_hand.remove(card)
    for trick in tricks:
        for play in trick["plays"]:
            if play["player_id"] == throwing_player_id:
                playable_hand.remove(play["card"])
    data["game_end"] = {
        "schema_version": 1,
        "kind": "open_card_throw",
        "throwing_player_id": throwing_player_id,
        "thrown_cards": playable_hand,
        "statement_classification": "attempted_level_limitation",
    }
    return data


def _decision_state(snapshot) -> dict:
    state = asdict(snapshot)
    state.pop("source_game_id", None)
    state.pop("source_played_at", None)
    return state


def test_version_one_event_is_canonical_and_uses_one_stable_participant() -> None:
    data = load_example()
    data["game_end"]["thrown_cards"].reverse()
    summary = build_historical_game_summary_from_input(data)

    assert summary["record"]["game_end"] == {
        "schema_version": 1,
        "kind": "open_card_throw",
        "throwing_player_id": "player-a",
        "thrown_cards": ["C7", "S10"],
        "statement_classification": "attempted_level_limitation",
    }
    assert build_historical_game_summary_from_input(summary["record"]) == summary


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda event: event.update({"schema_version": 2}), "schema_version"),
        (lambda event: event.update({"kind": "defender_concession"}), "kind must match"),
        (lambda event: event.update({"extra": True}), "unsupported"),
        (lambda event: event.update({"throwing_player_id": "left"}), "relative"),
        (lambda event: event.update({"throwing_player_id": "unknown"}), "stable participant"),
        (lambda event: event.update({"statement_classification": "I take one"}), "statement"),
        (lambda event: event.update({"future_trick_assertion": 1}), "specific future-trick"),
    ],
)
def test_event_union_rejects_invalid_version_identity_statement_and_claim(
    mutation, message: str
) -> None:
    data = load_example()
    mutation(data["game_end"])

    with pytest.raises(ValueError, match=message):
        build_historical_game_record(data)


@pytest.mark.parametrize("cards", [[], ["C7", "C7"], ["X1"]])
def test_event_rejects_empty_duplicate_and_invalid_cards(cards: list[str]) -> None:
    data = load_example()
    data["game_end"]["thrown_cards"] = cards

    with pytest.raises(ValueError, match="thrown_cards"):
        build_historical_game_record(data)


@pytest.mark.parametrize("cards", [["C7"], ["C7", "S10", "D9"], ["DQ", "D9"]])
def test_thrown_cards_must_equal_only_the_reconstructed_complete_hand(
    cards: list[str],
) -> None:
    data = load_example()
    data["game_end"]["thrown_cards"] = cards

    with pytest.raises(ValueError, match="exactly equal"):
        build_historical_game_summary_from_input(data)


@pytest.mark.parametrize(
    ("completed_count", "current_count", "thrower", "played_count"),
    [
        (0, 0, "player-a", 0),
        (0, 1, "player-b", 1),
        (0, 2, "player-c", 2),
        (9, 2, "player-c", 29),
    ],
)
def test_zero_through_twenty_nine_plays_and_incomplete_tricks_are_supported(
    completed_count: int,
    current_count: int,
    thrower: str,
    played_count: int,
) -> None:
    summary = build_historical_game_summary_from_input(
        build_throw_prefix(
            completed_trick_count=completed_count,
            current_trick_card_count=current_count,
            throwing_player_id=thrower,
        )
    )

    assert summary["play_prefix_summary"]["played_card_count"] == played_count
    assert summary["historical_game_end_summary"]["event_after_play_count"] == played_count
    assert summary["historical_game_end_summary"]["event_during_incomplete_trick"] is (
        current_count > 0
    )
    assert sum(summary["historical_game_end_summary"]["final_trick_counts"].values()) == 10


def test_all_thirty_plays_and_an_empty_throwing_hand_are_rejected() -> None:
    data = build_throw_prefix(completed_trick_count=9, current_trick_card_count=2)
    data["tricks"] = build_historical_input()["tricks"]
    data["game_end"]["thrown_cards"] = ["C7"]
    with pytest.raises(ValueError, match="after all 30 playable cards"):
        build_historical_game_summary_from_input(data)

    empty_hand = build_throw_prefix(
        completed_trick_count=9,
        current_trick_card_count=2,
        throwing_player_id="player-a",
    )
    empty_hand["game_end"]["thrown_cards"] = ["C7"]
    with pytest.raises(ValueError, match="at least one remaining hand card"):
        build_historical_game_summary_from_input(empty_hand)


@pytest.mark.parametrize(
    ("thrower", "party", "opposing", "joint"),
    [
        ("player-b", "declarer", "defenders", False),
        ("player-a", "defenders", "declarer", True),
        ("player-c", "defenders", "declarer", True),
    ],
)
def test_stable_thrower_derives_party_opposition_and_joint_liability(
    thrower: str, party: str, opposing: str, joint: bool
) -> None:
    end = build_historical_game_summary_from_input(
        build_throw_prefix(throwing_player_id=thrower)
    )["historical_game_end_summary"]

    assert end["throwing_party"] == party
    assert end["opposing_party"] == opposing
    assert end["joint_liability"] is joint
    assert end["rest_tricks_recipient"] == opposing


def test_rule_assignment_counts_current_cards_and_points_exactly_once() -> None:
    summary = build_historical_game_summary_from_input(
        build_throw_prefix(completed_trick_count=5, current_trick_card_count=2)
    )
    end = summary["historical_game_end_summary"]
    points = summary["point_accounting"]

    assert end["remaining_trick_count"] == 5
    assert end["rest_trick_assignment"]["assigned_card_count"] == 15
    assert points["observed_declarer_points"] + points["observed_defender_points"] + points[
        "total_unresolved_points"
    ] == 120
    assert points["final_declarer_points"] + points["final_defender_points"] == 120
    assert sum(end["observed_trick_counts"].values()) == 5
    assert sum(end["rule_assigned_trick_counts"].values()) == 5


def test_statement_classifications_are_scoring_neutral() -> None:
    results = []
    for classification in ("none", "generic_concession", "attempted_level_limitation"):
        data = load_example()
        data["game_end"]["statement_classification"] = classification
        summary = build_historical_game_summary_from_input(data)
        results.append(
            (
                summary["game_result_summary"],
                summary["final_settlement_summary"],
            )
        )
    assert results[0] == results[1] == results[2]


def test_defender_and_declarer_throw_assign_opposing_party_without_future_proof() -> None:
    defender = build_historical_game_summary_from_input(load_example())
    declarer = build_historical_game_summary_from_input(
        build_throw_prefix(throwing_player_id="player-b")
    )

    assert defender["game_result_summary"]["rest_tricks_recipient"] == "declarer"
    assert declarer["game_result_summary"]["rest_tricks_recipient"] == "defenders"
    assert defender["winner"] == "defenders"
    assert declarer["winner"] == "defenders"
    serialized = json.dumps(defender)
    assert "exact_proof" not in serialized
    assert "remaining_hands" not in serialized
    assert all(identity not in serialized for identity in ('"me"', '"left"', '"right"'))


@pytest.mark.parametrize(
    "hand_game,ouvert,expected_value",
    [(False, False, 23), (True, False, 35), (False, True, 46), (True, True, 59)],
)
def test_all_four_null_variants_use_assigned_trick_ownership(
    hand_game: bool, ouvert: bool, expected_value: int
) -> None:
    declarer_throw = build_historical_game_summary_from_input(
        build_throw_prefix(
            completed_trick_count=0,
            throwing_player_id="player-b",
            game_type="null",
            hand_game=hand_game,
            ouvert=ouvert,
        )
    )
    defender_throw = build_historical_game_summary_from_input(
        build_throw_prefix(
            completed_trick_count=0,
            throwing_player_id="player-a",
            game_type="null",
            hand_game=hand_game,
            ouvert=ouvert,
        )
    )

    assert declarer_throw["winner"] == "declarer"
    assert declarer_throw["final_settlement_summary"]["settlement_score"] == expected_value
    assert defender_throw["winner"] == "defenders"
    assert defender_throw["final_settlement_summary"]["settlement_score"] == -2 * expected_value
    assert declarer_throw["schneider_status"] == "not_applicable"
    assert declarer_throw["schwarz_status"] == "not_applicable"


def test_preexisting_null_loss_is_not_reversed_by_later_declarer_throw() -> None:
    declarer_id, first_declarer_trick = next(
        (
            declarer_id,
            next(
                trick["trick_number"]
                for trick in build_historical_game_summary_from_input(
                    build_historical_input(
                        game_type="null", declarer_player_id=declarer_id
                    )
                )["derived_tricks"]
                if trick["winner_side"] == "declarer"
            ),
        )
        for declarer_id in ("player-a", "player-b", "player-c")
        if any(
            trick["winner_side"] == "declarer"
            for trick in build_historical_game_summary_from_input(
                build_historical_input(
                    game_type="null", declarer_player_id=declarer_id
                )
            )["derived_tricks"]
        )
    )
    data = build_throw_prefix(
        completed_trick_count=first_declarer_trick,
        throwing_player_id=declarer_id,
        game_type="null",
        declarer_player_id=declarer_id,
    )
    summary = build_historical_game_summary_from_input(data)

    assert summary["game_result_summary"]["decision_state_before_game_end"] == (
        "defenders_already_won"
    )
    assert summary["winner"] == "defenders"
    assert summary["game_result_summary"]["winner_basis"] == "preexisting_game_decision"


def test_shared_prefix_matches_every_prior_terminal_kind_and_longer_normal_game() -> None:
    throw = build_throw_prefix(completed_trick_count=5, current_trick_card_count=2)
    normal = build_historical_input()
    expected = build_historical_decision_snapshots(
        build_historical_game_summary_from_input(throw)
    )
    normal_rows = build_historical_decision_snapshots(
        build_historical_game_summary_from_input(normal)
    )
    assert [_decision_state(row) for row in expected.snapshots] == [
        _decision_state(row) for row in normal_rows.snapshots[:17]
    ]

    prior_records = [
        build_concession_prefix(completed_trick_count=5, current_trick_card_count=2),
        build_defender_concession_prefix(
            completed_trick_count=5, current_trick_card_count=2
        ),
        build_exposure_prefix(completed_trick_count=5, current_trick_card_count=2),
        build_open_play_prefix(completed_trick_count=5, current_trick_card_count=2),
    ]
    for prior in prior_records:
        rows = build_historical_decision_snapshots(
            build_historical_game_summary_from_input(prior)
        )
        assert [_decision_state(row) for row in rows.snapshots] == [
            _decision_state(row) for row in expected.snapshots
        ]


def test_snapshots_training_and_review_include_only_actual_card_decisions(monkeypatch) -> None:
    monkeypatch.setattr(
        "skat_ai.historical_game_review.recommend_card_by_expected_value",
        stub_expected_value_recommendation,
    )
    data = build_throw_prefix(completed_trick_count=5, current_trick_card_count=2)
    record = build_historical_game_record(data)
    summary = build_historical_game_summary_from_input(data)
    snapshots = build_historical_decision_snapshots(summary)
    review = build_historical_game_review_summary(
        snapshots,
        record,
        sample_count=1,
        base_random_seed=42,
    )
    dataset = build_training_dataset_input(build_training_input([data], ["train"]))
    training = build_training_dataset_summary(dataset)

    assert snapshots.snapshot_count == 17
    assert review["decision_count"] == 17
    assert training["feature_generation_version"] == 1
    assert training["target"] == "actual_card_played"
    assert training["sample_count"] == 17
    serialized = json.dumps([asdict(row) for row in snapshots.snapshots]) + json.dumps(
        training["records"][0]["samples"]
    )
    for forbidden in (
        "open_card_throw",
        "throwing_player_id",
        "thrown_cards",
        "statement_classification",
        "rest_trick_assignment",
        "theoretical_schwarz_assessment",
        "final_settlement_summary",
    ):
        assert forbidden not in serialized


def test_zero_play_partition_statistics_export_and_rolling_remain_game_weighted() -> None:
    source = build_throw_prefix(completed_trick_count=0)
    source["played_at"] = "2026-07-10T12:00:00Z"
    target = build_throw_prefix(completed_trick_count=0, throwing_player_id="player-b")
    target["game_id"] = "zero-play-open-throw-target"
    target["played_at"] = "2026-07-11T12:00:00Z"
    dataset = build_training_dataset_input(
        build_training_input([source, target], ["train", "validation"])
    )
    audit = audit_training_dataset_partitions(dataset, "known_opponent")
    aggregation = aggregate_historical_opponent_statistics(dataset)
    exported = build_exportable_opponent_statistics_input(aggregation)
    rolling = build_serializable_rolling_opponent_policy_evaluation(
        evaluate_rolling_opponent_policy_predictions(dataset)
    )

    assert audit.partition_summary["train"]["record_count"] == 1
    assert audit.partition_summary["train"]["distinct_player_count"] == 3
    assert build_training_dataset_summary(dataset)["sample_count"] == 0
    assert aggregation.source_game_count == 2
    assert len(aggregation.records) == 3
    assert all(record.games_played == 2 for record in exported.records)
    assert rolling["selection"]["target_decision_count"] == 0
    assert rolling["target_games"][0]["as_of_source_game_count"] == 1
    assert rolling["target_games"][0]["decisions"] == []


def test_package_version_is_0_11_0() -> None:
    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'version = "0.11.0"' in pyproject
