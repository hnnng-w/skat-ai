import copy
import json
from dataclasses import asdict
from pathlib import Path

import pytest
from test_historical_declarer_concession import build_concession_prefix
from test_historical_game import build_historical_input
from test_historical_opponent_profiles import stub_expected_value_recommendation
from test_training_dataset import build_training_input

from skat_ai.dataset_partition_audit import audit_training_dataset_partitions
from skat_ai.defender_concession import (
    DefenderConcession,
    adjudicate_defender_concession,
)
from skat_ai.final_settlement import build_final_settlement_summary
from skat_ai.game_result import build_game_result_summary_from_score_summary
from skat_ai.historical_decision_snapshot import build_historical_decision_snapshots
from skat_ai.historical_game import (
    build_historical_game_record,
    build_historical_game_summary_from_input,
)
from skat_ai.historical_game_review import build_historical_game_review_summary
from skat_ai.historical_opponent_statistics import (
    aggregate_historical_opponent_statistics,
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
NORMAL_EXAMPLE_PATH = PROJECT_ROOT / "examples" / "historical_grand_normal_completion.json"
CONCESSION_EXAMPLE_PATH = (
    PROJECT_ROOT / "examples" / "historical_grand_defender_concession.json"
)


def test_package_version_is_0_17_0() -> None:
    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'version = "0.17.0"' in pyproject


def load_historical_data(path: Path = NORMAL_EXAMPLE_PATH) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)["historical_game_input"]


def build_defender_concession_prefix(
    *,
    completed_trick_count: int = 0,
    current_trick_card_count: int = 0,
    conceding_defender_player_id: str = "player-a",
    concession_form: str = "explicit_verbal",
) -> dict:
    data = load_historical_data()
    tricks = copy.deepcopy(data["tricks"][:completed_trick_count])
    if current_trick_card_count:
        current = copy.deepcopy(data["tricks"][completed_trick_count])
        current["plays"] = current["plays"][:current_trick_card_count]
        tricks.append(current)
    data.update(
        {
            "game_id": "test-historical-defender-concession",
            "game_end_reason": "defender_concession",
            "game_end": {
                "schema_version": 1,
                "kind": "defender_concession",
                "conceding_defender_player_id": conceding_defender_player_id,
                "concession_form": concession_form,
            },
            "tricks": tricks,
        }
    )
    return data


@pytest.mark.parametrize(
    ("completed_tricks", "current_cards", "expected_plays"),
    [(0, 0, 0), (0, 1, 1), (0, 2, 2), (4, 0, 12), (4, 1, 13), (4, 2, 14)],
)
def test_exact_empty_complete_and_incomplete_prefixes_are_supported(
    completed_tricks: int,
    current_cards: int,
    expected_plays: int,
) -> None:
    summary = build_historical_game_summary_from_input(
        build_defender_concession_prefix(
            completed_trick_count=completed_tricks,
            current_trick_card_count=current_cards,
        )
    )

    assert summary["play_prefix_summary"]["played_card_count"] == expected_plays
    assert summary["play_prefix_summary"]["completed_trick_count"] == completed_tricks
    assert summary["play_prefix_summary"]["current_trick_card_count"] == current_cards
    assert ("incomplete_current_trick" in summary) is bool(current_cards)
    if current_cards:
        assert "winner_player_id" not in summary["incomplete_current_trick"]
        assert "trick_points" not in summary["incomplete_current_trick"]


def test_twenty_nine_plays_are_supported_but_thirty_are_rejected() -> None:
    data = build_defender_concession_prefix(completed_trick_count=9)
    final_trick = copy.deepcopy(load_historical_data()["tricks"][9])
    final_trick["plays"] = final_trick["plays"][:2]
    data["tricks"].append(final_trick)

    assert build_historical_game_summary_from_input(data)["play_prefix_summary"][
        "played_card_count"
    ] == 29

    data["tricks"] = copy.deepcopy(load_historical_data()["tricks"])
    with pytest.raises(ValueError, match="after all 30 playable cards"):
        build_historical_game_summary_from_input(data)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda data: data.pop("game_end"), "game_end is required"),
        (
            lambda data: data["game_end"].update({"kind": "declarer_concession"}),
            "kind must match",
        ),
        (
            lambda data: data["game_end"].update({"schema_version": 2}),
            "schema_version must be exactly 1",
        ),
        (
            lambda data: data["game_end"].update({"statement_text": "We give up"}),
            "unsupported fields",
        ),
        (
            lambda data: data["game_end"].update({"thrown_cards": []}),
            "unsupported fields",
        ),
        (
            lambda data: data["game_end"].update({"consent": True}),
            "unsupported fields",
        ),
    ],
)
def test_event_union_and_classification_boundaries_are_strict(mutation, message: str) -> None:
    data = build_defender_concession_prefix()
    mutation(data)

    with pytest.raises(ValueError, match=message):
        build_historical_game_record(data)


@pytest.mark.parametrize(
    "player_id",
    ["player-b", "unknown-player", " player-a", "player-a "],
)
def test_conceding_player_must_be_an_exact_stable_defender_id(player_id: str) -> None:
    data = build_defender_concession_prefix(conceding_defender_player_id=player_id)

    with pytest.raises(ValueError, match="conceding_defender_player_id"):
        build_historical_game_record(data)


@pytest.mark.parametrize(
    "concession_form",
    ["explicit_verbal", "adjudicated_unambiguous_conduct"],
)
def test_supported_forms_are_scoring_neutral_and_bind_both_defenders(
    concession_form: str,
) -> None:
    summary = build_historical_game_summary_from_input(
        build_defender_concession_prefix(
            completed_trick_count=4,
            current_trick_card_count=2,
            concession_form=concession_form,
        )
    )
    end = summary["historical_game_end_summary"]

    assert end["conceding_defender_player_id"] == "player-a"
    assert end["non_conceding_defender_player_id"] == "player-c"
    assert end["liable_party"] == "defenders"
    assert end["joint_liability"] is True
    assert end["continued_play_requested"] is False
    assert summary["winner"] == "declarer"
    assert summary["final_settlement_summary"]["settlement_score"] == 48


@pytest.mark.parametrize(
    "concession_form",
    ["ambiguous_conduct", " explicit_verbal", "explicit_verbal "],
)
def test_unsupported_or_padded_forms_are_rejected(concession_form: str) -> None:
    with pytest.raises(ValueError, match="concession_form"):
        build_historical_game_record(
            build_defender_concession_prefix(concession_form=concession_form)
        )


@pytest.mark.parametrize(
    ("declarer_id", "discards", "conceding_id", "expected_other"),
    [
        ("player-b", ["SK", "SQ"], "player-a", "player-c"),
        ("player-a", ["C8", "C7"], "player-b", "player-c"),
        ("player-a", ["C8", "C7"], "player-c", "player-b"),
    ],
)
def test_forehand_middlehand_and_rearhand_defenders_can_concede(
    declarer_id: str,
    discards: list[str],
    conceding_id: str,
    expected_other: str,
) -> None:
    data = build_defender_concession_prefix(conceding_defender_player_id=conceding_id)
    data["declarer_player_id"] = declarer_id
    data["discarded_cards"] = discards

    end = build_historical_game_summary_from_input(data)["historical_game_end_summary"]
    assert end["conceding_defender_player_id"] == conceding_id
    assert end["non_conceding_defender_player_id"] == expected_other


def test_observed_and_unresolved_points_reconcile_without_assignment_or_privacy_leak() -> None:
    summary = build_historical_game_summary_from_input(
        load_historical_data(CONCESSION_EXAMPLE_PATH)
    )
    points = summary["point_accounting"]

    assert points == {
        "completed_trick_declarer_points": 15,
        "completed_trick_defender_points": 25,
        "skat_points": 7,
        "observed_declarer_points": 22,
        "observed_defender_points": 25,
        "unresolved_current_trick_points": 14,
        "unresolved_remaining_hand_points": 59,
        "total_unresolved_points": 73,
        "total_card_points": 120,
    }
    assert summary["game_result_summary"]["remaining_points_recipient"] is None
    assert summary["game_result_summary"]["remaining_points_assigned"] == 0
    serialized = json.dumps(summary)
    assert "remaining_hands" not in serialized
    assert build_historical_game_summary_from_input(summary["record"]) == summary


def _build_changed_declarer_prefix(declarer_id: str, completed_tricks: int) -> dict:
    data = build_defender_concession_prefix(completed_trick_count=completed_tricks)
    used_cards = {
        play["card"] for trick in data["tricks"] for play in trick["plays"]
    }
    hand = next(
        player["initial_hand"]
        for player in data["players"]
        if player["player_id"] == declarer_id
    )
    data["declarer_player_id"] = declarer_id
    data["discarded_cards"] = [card for card in hand if card not in used_cards][:2]
    data["game_end"]["conceding_defender_player_id"] = next(
        player["player_id"]
        for player in data["players"]
        if player["player_id"] != declarer_id
    )
    return data


@pytest.mark.parametrize(
    ("data", "expected_state", "expected_winner"),
    [
        (build_defender_concession_prefix(), "undecided", "declarer"),
        (_build_changed_declarer_prefix("player-a", 6), "declarer_already_won", "declarer"),
        (
            build_defender_concession_prefix(completed_trick_count=6),
            "defenders_already_won",
            "defenders",
        ),
    ],
)
def test_undecided_and_preexisting_results_are_preserved(
    data: dict,
    expected_state: str,
    expected_winner: str,
) -> None:
    summary = build_historical_game_summary_from_input(data)

    assert summary["historical_game_end_summary"][
        "decision_state_before_concession"
    ] == expected_state
    assert summary["winner"] == expected_winner
    assert summary["final_settlement_summary"]["winner"] == expected_winner


def test_preexisting_observed_schneider_win_is_preserved() -> None:
    summary = build_historical_game_summary_from_input(
        _build_changed_declarer_prefix("player-a", 8)
    )

    assert summary["winner"] == "declarer"
    assert summary["game_result_summary"]["effective_schneider_status"] == (
        "declarer_made_schneider"
    )
    assert summary["final_settlement_summary"]["settlement_basis"][
        "achieved_schneider_applied"
    ] is True


@pytest.mark.parametrize("game_type", ["clubs", "spades", "hearts", "diamonds", "grand"])
def test_suit_and_grand_use_simple_declared_value_without_optional_levels(
    game_type: str,
) -> None:
    data = build_defender_concession_prefix()
    data["declaration"]["game_type"] = game_type

    summary = build_historical_game_summary_from_input(data)
    basis = summary["final_settlement_summary"]["settlement_basis"]
    assert summary["winner"] == "declarer"
    assert basis["achieved_schneider_applied"] is False
    assert basis["achieved_schwarz_applied"] is False


@pytest.mark.parametrize(
    "declaration_updates",
    [
        {"hand_game": True, "schneider_announced": True},
        {
            "hand_game": True,
            "schneider_announced": True,
            "schwarz_announced": True,
        },
        {
            "hand_game": True,
            "schneider_announced": True,
            "schwarz_announced": True,
            "ouvert": True,
        },
    ],
)
def test_declared_mandatory_levels_are_awarded_by_existing_bounded_rules(
    declaration_updates: dict,
) -> None:
    data = build_defender_concession_prefix()
    data["declaration"].update(declaration_updates)
    data["discarded_cards"] = []

    summary = build_historical_game_summary_from_input(data)
    basis = summary["final_settlement_summary"]["settlement_basis"]
    assert basis["mandatory_level_awarded"] is True
    assert basis["mandatory_level_source"] == "declared_announcement"
    assert "4.1.5" in summary["historical_game_end_summary"]["rule_sections"]


def test_already_failed_mandatory_level_preserves_declarer_loss() -> None:
    data = build_defender_concession_prefix(completed_trick_count=6)
    data["declaration"].update({"hand_game": True, "schneider_announced": True})
    data["discarded_cards"] = []

    summary = build_historical_game_summary_from_input(data)
    assert summary["winner"] == "defenders"
    assert summary["historical_game_end_summary"][
        "decision_state_before_concession"
    ] == "defenders_already_won"
    assert summary["final_settlement_summary"]["settlement_score"] < 0
    assert summary["final_settlement_summary"]["settlement_basis"][
        "mandatory_level_awarded"
    ] is False


def test_supported_overbid_required_value_is_preserved() -> None:
    data = build_defender_concession_prefix()
    data["declaration"]["bid_value"] = 49

    summary = build_historical_game_summary_from_input(data)
    assert summary["overbid_summary"]["is_overbid"] is True
    assert summary["final_settlement_summary"]["settlement_basis"][
        "overbid_required_value_applied"
    ] is True
    assert summary["final_settlement_summary"]["settlement_basis"][
        "mandatory_level_awarded"
    ] is True


@pytest.mark.parametrize(
    ("hand_game", "ouvert", "expected_value"),
    [(False, False, 23), (True, False, 35), (False, True, 46), (True, True, 59)],
)
def test_all_null_variants_win_before_a_declarer_trick_and_preserve_later_loss(
    hand_game: bool,
    ouvert: bool,
    expected_value: int,
) -> None:
    win_data = build_defender_concession_prefix()
    win_data["declaration"] = {
        "game_type": "null",
        "hand_game": hand_game,
        "ouvert": ouvert,
        "bid_value": 18,
    }
    win_data["discarded_cards"] = [] if hand_game else ["SK", "SQ"]
    win = build_historical_game_summary_from_input(win_data)

    loss_data = copy.deepcopy(win_data)
    loss_data["declarer_player_id"] = "player-a"
    loss_data["game_end"]["conceding_defender_player_id"] = "player-b"
    loss_data["discarded_cards"] = [] if hand_game else ["C8", "C7"]
    loss_data["tricks"] = copy.deepcopy(load_historical_data()["tricks"][:1])
    loss = build_historical_game_summary_from_input(loss_data)

    assert win["winner"] == "declarer"
    assert win["final_settlement_summary"]["settlement_score"] == expected_value
    assert loss["winner"] == "defenders"
    assert loss["final_settlement_summary"]["settlement_score"] == -2 * expected_value
    assert win["schneider_status"] == win["schwarz_status"] == "not_applicable"


def test_historical_result_and_settlement_match_flat_defender_concession() -> None:
    summary = build_historical_game_summary_from_input(
        build_defender_concession_prefix(
            completed_trick_count=4, current_trick_card_count=2
        )
    )
    completed_tricks = [
        {"winner_role": trick["winner_side"]} for trick in summary["derived_tricks"]
    ]
    raw_result = build_game_result_summary_from_score_summary(
        {
            "total_declarer_points": summary["declarer_points"],
            "total_defender_points": summary["defender_points"],
        },
        game_type=summary["record"]["declaration"]["game_type"],
        completed_tricks=completed_tricks,
        game_end_reason="defender_concession",
    )
    flat = adjudicate_defender_concession(
        DefenderConcession(1, "defender_concession", "left", "explicit_verbal"),
        raw_result,
        summary["game_value_summary"],
        summary["overbid_summary"],
        completed_tricks,
    )
    flat_settlement = build_final_settlement_summary(
        summary["game_value_summary"],
        flat.game_result_summary,
        summary["overbid_summary"],
        completed_tricks,
    )

    assert flat.game_result_summary == summary["game_result_summary"]
    assert flat_settlement == summary["final_settlement_summary"]


def _decision_state(snapshot) -> dict:
    result = asdict(snapshot)
    result.pop("source_game_id", None)
    result.pop("source_played_at", None)
    return result


def test_shared_prefix_snapshots_and_training_features_do_not_leak_event_facts() -> None:
    normal = build_historical_input()
    defender = build_defender_concession_prefix(
        completed_trick_count=4, current_trick_card_count=2
    )
    defender["played_at"] = normal.get("played_at")
    normal_snapshots = build_historical_decision_snapshots(
        build_historical_game_summary_from_input(normal)
    )
    defender_snapshots = build_historical_decision_snapshots(
        build_historical_game_summary_from_input(defender)
    )

    assert defender_snapshots.snapshot_count == 14
    assert [_decision_state(row) for row in defender_snapshots.snapshots] == [
        _decision_state(row) for row in normal_snapshots.snapshots[:14]
    ]
    declarer = build_concession_prefix(
        completed_trick_count=4, current_trick_card_count=2
    )
    declarer["played_at"] = defender["played_at"]
    declarer_snapshots = build_historical_decision_snapshots(
        build_historical_game_summary_from_input(declarer)
    )
    assert [_decision_state(row) for row in defender_snapshots.snapshots] == [
        _decision_state(row) for row in declarer_snapshots.snapshots
    ]

    changed = copy.deepcopy(defender)
    changed["game_end"]["conceding_defender_player_id"] = "player-c"
    changed["game_end"]["concession_form"] = "adjudicated_unambiguous_conduct"
    changed_snapshots = build_historical_decision_snapshots(
        build_historical_game_summary_from_input(changed)
    )
    assert [_decision_state(row) for row in changed_snapshots.snapshots] == [
        _decision_state(row) for row in defender_snapshots.snapshots
    ]

    dataset = build_training_dataset_input(
        build_training_input([normal, defender, build_defender_concession_prefix()])
    )
    training = build_training_dataset_summary(dataset)
    assert [record["sample_count"] for record in training["records"]] == [30, 14, 0]
    assert training["feature_generation_version"] == 1
    assert training["target"] == "actual_card_played"
    assert [sample["features"] for sample in training["records"][1]["samples"]] == [
        sample["features"] for sample in training["records"][0]["samples"][:14]
    ]
    features = json.dumps(training["records"][1]["samples"])
    for forbidden in (
        "defender_concession",
        "conceding_defender_player_id",
        "concession_form",
        "final_settlement_summary",
    ):
        assert forbidden not in features

    changed_training = build_training_dataset_summary(
        build_training_dataset_input(build_training_input([changed]))
    )
    assert [
        sample["features"] for sample in changed_training["records"][0]["samples"]
    ] == [sample["features"] for sample in training["records"][1]["samples"]]


def test_review_uses_actual_plays_and_never_adds_a_terminal_event(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "skat_ai.historical_game_review.recommend_card_by_expected_value",
        stub_expected_value_recommendation,
    )
    for data, expected_count in (
        (build_defender_concession_prefix(), 0),
        (
            build_defender_concession_prefix(
                completed_trick_count=4, current_trick_card_count=2
            ),
            14,
        ),
    ):
        record = build_historical_game_record(data)
        snapshots = build_historical_decision_snapshots(
            build_historical_game_summary_from_input(data)
        )
        review = build_historical_game_review_summary(
            snapshots,
            record,
            sample_count=1,
            base_random_seed=42,
        )
        assert review["decision_count"] == expected_count
        assert len(review["decisions"]) == expected_count
        assert sum(row["decision_count"] for row in review["player_summaries"]) == (
            expected_count
        )


def test_zero_sample_partition_membership_and_opponent_statistics_are_game_weighted() -> None:
    zero = build_defender_concession_prefix()
    zero["played_at"] = "2026-07-10T12:00:00Z"
    dataset = build_training_dataset_input(build_training_input([zero], ["train"]))
    training = build_training_dataset_summary(dataset)
    audit = audit_training_dataset_partitions(dataset, "known_opponent")
    aggregation = aggregate_historical_opponent_statistics(dataset)
    records = {
        record.statistics_record.player_id: record.statistics_record
        for record in aggregation.records
    }

    assert training["sample_count"] == 0
    assert audit.partition_summary["train"]["distinct_player_count"] == 3
    assert records["player-b"].exact_counts.solo_games_won == 1
    assert records["player-a"].exact_counts.defender_games_won == 0
    assert records["player-c"].exact_counts.defender_games_won == 0
    assert all(record.games_played == 1 for record in records.values())


def test_preexisting_defender_win_counts_for_both_defenders() -> None:
    data = build_defender_concession_prefix(completed_trick_count=6)
    data["played_at"] = "2026-07-10T12:00:00Z"
    dataset = build_training_dataset_input(build_training_input([data], ["train"]))
    aggregation = aggregate_historical_opponent_statistics(dataset)
    records = {
        record.statistics_record.player_id: record.statistics_record
        for record in aggregation.records
    }

    assert records["player-b"].exact_counts.solo_games_won == 0
    assert records["player-a"].exact_counts.defender_games_won == 1
    assert records["player-c"].exact_counts.defender_games_won == 1


@pytest.mark.parametrize("target_play_count", [0, 14])
def test_rolling_evaluation_uses_prior_concession_as_one_source_and_actual_targets(
    target_play_count: int,
) -> None:
    source = build_defender_concession_prefix()
    source["played_at"] = "2026-07-10T12:00:00Z"
    complete_tricks, current_cards = divmod(target_play_count, 3)
    target = build_defender_concession_prefix(
        completed_trick_count=complete_tricks,
        current_trick_card_count=current_cards,
        conceding_defender_player_id="player-c",
        concession_form="adjudicated_unambiguous_conduct",
    )
    target["played_at"] = "2026-07-11T12:00:00Z"
    dataset = build_training_dataset_input(
        build_training_input([source, target], ["train", "validation"])
    )
    result = build_serializable_rolling_opponent_policy_evaluation(
        evaluate_rolling_opponent_policy_predictions(dataset)
    )
    target_summary = result["target_games"][0]

    assert target_summary["as_of_source_game_count"] == 1
    assert target_summary["decision_count"] == target_play_count
    assert len(target_summary["decisions"]) == target_play_count
    assert result["selection"]["target_decision_count"] == target_play_count
    assert result["coverage"]["target_decisions"] == target_play_count
    assert "concession" not in json.dumps(target_summary["decisions"])
