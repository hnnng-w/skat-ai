import copy
import json
from dataclasses import asdict
from pathlib import Path

import pytest
from test_historical_declarer_card_exposure import build_exposure_prefix
from test_historical_declarer_concession import build_concession_prefix
from test_historical_defender_concession import build_defender_concession_prefix
from test_historical_game import build_historical_input
from test_historical_opponent_profiles import stub_expected_value_recommendation
from test_training_dataset import build_training_input

from skat_ai.dataset_partition_audit import audit_training_dataset_partitions
from skat_ai.defender_open_play import (
    DefenderOpenPlay,
    adjudicate_defender_open_play,
    validate_exact_remaining_play_state,
)
from skat_ai.final_settlement import build_final_settlement_summary
from skat_ai.game_result import build_game_result_summary_from_score_summary
from skat_ai.historical_decision_snapshot import build_historical_decision_snapshots
from skat_ai.historical_game import (
    build_historical_game_record,
    build_historical_game_summary_from_input,
)
from skat_ai.historical_game_review import build_historical_game_review_summary
from skat_ai.historical_opponent_profile_binding import (
    resolve_historical_opponent_profile_bindings,
)
from skat_ai.historical_opponent_statistics import (
    aggregate_historical_opponent_statistics,
    build_exportable_opponent_statistics_input,
)
from skat_ai.historical_play_prefix import replay_historical_play_prefix
from skat_ai.historical_player_mapping import build_historical_player_mapping
from skat_ai.input_loader import load_opponent_statistics_from_json
from skat_ai.rolling_opponent_policy_evaluation import (
    build_serializable_rolling_opponent_policy_evaluation,
    evaluate_rolling_opponent_policy_predictions,
)
from skat_ai.training_dataset import (
    build_training_dataset_input,
    build_training_dataset_summary,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OPEN_PLAY_EXAMPLE_PATH = (
    PROJECT_ROOT / "examples" / "historical_grand_defender_open_play.json"
)
NORMAL_EXAMPLE_PATH = PROJECT_ROOT / "examples" / "historical_grand_normal_completion.json"


def load_historical_data(path: Path = OPEN_PLAY_EXAMPLE_PATH) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)["historical_game_input"]


def build_open_play_prefix(
    *, completed_trick_count: int = 8, current_trick_card_count: int = 0
) -> dict:
    data = load_historical_data()
    normal = load_historical_data(NORMAL_EXAMPLE_PATH)
    tricks = copy.deepcopy(normal["tricks"][:completed_trick_count])
    if current_trick_card_count:
        current = copy.deepcopy(normal["tricks"][completed_trick_count])
        current["plays"] = current["plays"][:current_trick_card_count]
        tricks.append(current)
    data["tricks"] = tricks
    exposing_id = data["game_end"]["exposing_defender_player_id"]
    hand = list(
        next(
            player["initial_hand"]
            for player in data["players"]
            if player["player_id"] == exposing_id
        )
    )
    for trick in tricks:
        for play in trick["plays"]:
            if play["player_id"] == exposing_id:
                hand.remove(play["card"])
    data["game_end"]["exposed_cards"] = hand
    return data


def _decision_state(snapshot) -> dict:
    state = asdict(snapshot)
    state.pop("source_game_id", None)
    state.pop("source_played_at", None)
    return state


def test_version_one_event_is_canonical_and_uses_stable_defender_identity() -> None:
    data = build_open_play_prefix()
    data["game_end"]["exposed_cards"].reverse()
    record = build_historical_game_record(data)
    summary = build_historical_game_summary_from_input(data)

    assert record.game_end.exposed_cards == ("C7", "S10")
    assert summary["record"]["game_end"] == {
        "schema_version": 1,
        "kind": "defender_open_play",
        "exposing_defender_player_id": "player-a",
        "exposed_cards": ["C7", "S10"],
        "declarer_response": "accept_adjudication",
    }
    assert build_historical_game_summary_from_input(summary["record"]) == summary


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda event: event.update({"schema_version": 2}), "schema_version"),
        (lambda event: event.update({"kind": "defender_concession"}), "kind must match"),
        (lambda event: event.update({"extra": True}), "unsupported"),
        (
            lambda event: event.update({"exposing_defender_player_id": "player-b"}),
            "stable defender",
        ),
        (
            lambda event: event.update({"exposing_defender_player_id": "left"}),
            "relative",
        ),
        (
            lambda event: event.update({"declarer_response": "request_continued_play"}),
            "game_events contract",
        ),
    ],
)
def test_event_union_rejects_invalid_identity_version_and_continuation(
    mutation, message: str
) -> None:
    data = build_open_play_prefix()
    mutation(data["game_end"])

    with pytest.raises(ValueError, match=message):
        build_historical_game_record(data)


def test_all_participants_must_use_stable_non_relative_ids() -> None:
    data = build_open_play_prefix()
    for player in data["players"]:
        if player["player_id"] == "player-c":
            player["player_id"] = "right"
    for trick in data["tricks"]:
        if trick["leader_player_id"] == "player-c":
            trick["leader_player_id"] = "right"
        for play in trick["plays"]:
            if play["player_id"] == "player-c":
                play["player_id"] = "right"

    with pytest.raises(ValueError, match="must not use relative identities"):
        build_historical_game_record(data)


@pytest.mark.parametrize("cards", [[], ["C7", "C7"], ["X1"]])
def test_event_rejects_empty_duplicate_and_invalid_exposed_cards(cards: list[str]) -> None:
    data = build_open_play_prefix()
    data["game_end"]["exposed_cards"] = cards

    with pytest.raises(ValueError, match="exposed_cards"):
        build_historical_game_record(data)


@pytest.mark.parametrize("cards", [["C7"], ["C7", "S10", "D9"]])
def test_exposed_cards_must_equal_the_complete_reconstructed_current_hand(
    cards: list[str],
) -> None:
    data = build_open_play_prefix()
    data["game_end"]["exposed_cards"] = cards

    with pytest.raises(ValueError, match="exactly equal"):
        build_historical_game_summary_from_input(data)


def test_exact_five_trick_bound_and_terminal_rejections() -> None:
    five_remaining = build_open_play_prefix(completed_trick_count=5)
    assert build_historical_game_summary_from_input(five_remaining)[
        "historical_game_end_summary"
    ]["remaining_trick_count"] == 5

    with pytest.raises(ValueError, match="between 1 and 5 cards"):
        build_historical_game_summary_from_input(
            build_open_play_prefix(completed_trick_count=4)
        )

    all_played = build_open_play_prefix(completed_trick_count=10)
    all_played["game_end"]["exposed_cards"] = ["C7"]
    with pytest.raises(ValueError, match="after all 30 playable cards"):
        build_historical_game_summary_from_input(all_played)


@pytest.mark.parametrize("current_card_count", [1, 2])
def test_one_and_two_card_incomplete_final_tricks_are_exactly_reconstructed(
    current_card_count: int,
) -> None:
    summary = build_historical_game_summary_from_input(
        build_open_play_prefix(current_trick_card_count=current_card_count)
    )

    assert summary["play_prefix_summary"]["played_card_count"] == 24 + current_card_count
    assert summary["play_prefix_summary"]["current_trick_card_count"] == current_card_count
    assert summary["incomplete_current_trick"]["next_player_id"] == (
        "player-b" if current_card_count == 1 else "player-c"
    )
    assert summary["historical_game_end_summary"]["event_during_incomplete_trick"] is True


def test_valid_proof_assigns_all_unresolved_tricks_and_points_to_defenders() -> None:
    summary = build_historical_game_summary_from_input(load_historical_data())
    end = summary["historical_game_end_summary"]
    points = summary["point_accounting"]

    assert end["exact_proof"]["status"] == "valid"
    assert end["rest_trick_assignment"] == {
        "source": "defender_open_play_adjudication",
        "recipient": "defenders",
        "remaining_trick_count": 2,
        "assigned_card_count": 6,
        "assigned_card_points": 13,
    }
    assert points["observed_declarer_points"] == 22
    assert points["observed_defender_points"] == 85
    assert points["total_unresolved_points"] == 13
    assert points["assigned_declarer_points"] == 0
    assert points["assigned_defender_points"] == 13
    assert (points["final_declarer_points"], points["final_defender_points"]) == (22, 98)
    assert summary["final_settlement_summary"]["settlement_score"] == -144


def test_invalid_proof_assigns_points_to_declarer_but_preserves_preexisting_loss() -> None:
    data = build_open_play_prefix(completed_trick_count=9)
    replacements = {"D7": "SA", "SA": "S10", "S10": "S7", "S7": "D7"}
    for player in data["players"]:
        player["initial_hand"] = [
            replacements.get(card, card) for card in player["initial_hand"]
        ]
    data["skat"] = [replacements.get(card, card) for card in data["skat"]]
    for trick in data["tricks"]:
        for play in trick["plays"]:
            play["card"] = replacements.get(play["card"], play["card"])
    data["game_end"]["exposed_cards"] = ["S7"]

    summary = build_historical_game_summary_from_input(data)

    assert summary["historical_game_end_summary"]["exact_proof"]["status"] == "invalid"
    assert summary["game_result_summary"]["rest_tricks_recipient"] == "declarer"
    assert summary["point_accounting"]["assigned_declarer_points"] == 11
    assert summary["game_result_summary"]["decision_state_before_game_end"] == (
        "defenders_already_won"
    )
    assert summary["winner"] == "defenders"


def test_proof_is_complete_deterministic_memoized_and_uses_required_quantifiers() -> None:
    first = build_historical_game_summary_from_input(load_historical_data())[
        "historical_game_end_summary"
    ]["exact_proof"]
    second = build_historical_game_summary_from_input(load_historical_data())[
        "historical_game_end_summary"
    ]["exact_proof"]

    assert first == second
    assert first["proof_complete"] is True
    assert first["evaluated_state_count"] == 32
    assert first["memoized_state_count"] == 32
    assert first["quantifier_policy"] == {
        "exposing_defender": "exists_legal_strategy",
        "declarer": "all_legal_plays",
        "non_exposing_defender": "all_legal_plays",
    }


def test_proof_output_uses_stable_ids_and_redacts_both_private_hands() -> None:
    summary = build_historical_game_summary_from_input(load_historical_data())
    end = summary["historical_game_end_summary"]
    line = end["exact_proof"]["successful_line"]

    assert {move["player_id"] for move in line} == {
        "player-a",
        "player-b",
        "player-c",
    }
    assert all(
        move["card"] is not None
        if move["player_id"] == "player-a"
        else move["card"] is None
        for move in line
    )
    assert all(
        move["trick_winner_player_id"] in {None, "player-a", "player-b", "player-c"}
        for move in line
    )
    serialized = json.dumps(summary)
    assert "remaining_hands" not in serialized
    for relative_identity in ('"me"', '"left"', '"right"'):
        assert relative_identity not in serialized


def test_historical_result_and_settlement_match_equivalent_flat_adjudication() -> None:
    data = load_historical_data()
    record = build_historical_game_record(data)
    replay = replay_historical_play_prefix(record)
    mapping = build_historical_player_mapping(record)
    hands = {
        mapping.to_flat(player_id): cards for player_id, cards in replay.remaining_hands
    }
    event = DefenderOpenPlay(
        1,
        "defender_open_play",
        mapping.to_flat("player-a"),
        tuple((player, hands[player]) for player in ("me", "left", "right")),
        "accept_adjudication",
    )
    completed = [
        {
            "cards": [card for _, card in trick.plays],
            "winner_role": trick.winner_side,
        }
        for trick in replay.completed_tricks
    ]
    context = validate_exact_remaining_play_state(
        {
            "game_type": "grand",
            "declarer_player": "me",
            "completed_tricks": completed,
            "current_trick": [],
            "trick_leader": mapping.to_flat(replay.next_player_id),
            "next_player": mapping.to_flat(replay.next_player_id),
            "skat": list(record.discarded_cards),
            "hand": list(hands["me"]),
            "left_hand_size": len(hands["left"]),
            "right_hand_size": len(hands["right"]),
            "played_cards": [],
        },
        event,
    )
    historical = build_historical_game_summary_from_input(data)
    raw_result = build_game_result_summary_from_score_summary(
        {
            "total_declarer_points": 22,
            "total_defender_points": 85,
        }
    )
    flat = adjudicate_defender_open_play(
        event,
        context,
        raw_result,
        historical["game_value_summary"],
        historical["overbid_summary"],
        completed,
    )
    flat_settlement = build_final_settlement_summary(
        historical["game_value_summary"],
        flat.game_result_summary,
        historical["overbid_summary"],
        completed,
    )

    assert flat.game_result_summary == historical["game_result_summary"]
    assert flat_settlement == historical["final_settlement_summary"]


def test_shared_prefix_parity_with_every_previously_supported_end_reason() -> None:
    normal = build_historical_input()
    open_play = build_open_play_prefix(completed_trick_count=5, current_trick_card_count=2)
    open_play["played_at"] = normal.get("played_at")
    expected = build_historical_decision_snapshots(
        build_historical_game_summary_from_input(open_play)
    )
    normal_rows = build_historical_decision_snapshots(
        build_historical_game_summary_from_input(normal)
    )
    assert [_decision_state(row) for row in expected.snapshots] == [
        _decision_state(row) for row in normal_rows.snapshots[:17]
    ]

    prior_reasons = [
        build_concession_prefix(completed_trick_count=5, current_trick_card_count=2),
        build_defender_concession_prefix(
            completed_trick_count=5, current_trick_card_count=2
        ),
        build_exposure_prefix(completed_trick_count=5, current_trick_card_count=2),
    ]
    for prior in prior_reasons:
        prior["played_at"] = open_play["played_at"]
        rows = build_historical_decision_snapshots(
            build_historical_game_summary_from_input(prior)
        )
        assert [_decision_state(row) for row in rows.snapshots] == [
            _decision_state(row) for row in expected.snapshots
        ]


def test_event_identity_proof_and_settlement_do_not_leak_into_decisions_or_training() -> None:
    first = load_historical_data()
    second = copy.deepcopy(first)
    second["game_end"]["exposing_defender_player_id"] = "player-c"
    second["game_end"]["exposed_cards"] = ["DQ", "D9"]
    first_rows = build_historical_decision_snapshots(
        build_historical_game_summary_from_input(first)
    )
    second_rows = build_historical_decision_snapshots(
        build_historical_game_summary_from_input(second)
    )
    assert [_decision_state(row) for row in first_rows.snapshots] == [
        _decision_state(row) for row in second_rows.snapshots
    ]

    dataset = build_training_dataset_input(
        build_training_input([build_historical_input(), first], ["train", "validation"])
    )
    training = build_training_dataset_summary(dataset)
    assert training["target"] == "actual_card_played"
    assert training["feature_generation_version"] == 1
    assert training["records"][1]["sample_count"] == 24
    assert [sample["features"] for sample in training["records"][1]["samples"]] == [
        sample["features"] for sample in training["records"][0]["samples"][:24]
    ]
    serialized = json.dumps(training["records"][1]["samples"])
    for forbidden in (
        '"defender_open_play"',
        '"exposing_defender_player_id"',
        '"exposed_cards"',
        '"exact_proof"',
        '"rest_trick_assignment"',
        '"final_settlement_summary"',
    ):
        assert forbidden not in serialized


def test_review_external_profiles_partition_statistics_and_export_use_one_game(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "skat_ai.historical_game_review.recommend_card_by_expected_value",
        stub_expected_value_recommendation,
    )
    data = load_historical_data()
    record = build_historical_game_record(data)
    summary = build_historical_game_summary_from_input(data)
    snapshots = build_historical_decision_snapshots(summary)
    statistics = load_opponent_statistics_from_json(
        str(PROJECT_ROOT / "examples" / "historical_opponent_statistics.json")
    )
    bindings = resolve_historical_opponent_profile_bindings(
        record,
        statistics,
        statistics_input_file="examples/historical_opponent_statistics.json",
    )
    review = build_historical_game_review_summary(
        snapshots,
        record,
        sample_count=1,
        base_random_seed=42,
        opponent_profile_bindings=bindings,
    )
    dataset = build_training_dataset_input(build_training_input([data], ["train"]))
    audit = audit_training_dataset_partitions(dataset, "known_opponent")
    aggregation = aggregate_historical_opponent_statistics(dataset)
    exported = build_exportable_opponent_statistics_input(aggregation)

    assert snapshots.snapshot_count == 24
    assert review["decision_count"] == 24
    assert "defender_open_play" not in json.dumps(review["decisions"])
    assert audit.partition_summary["train"]["distinct_player_count"] == 3
    assert aggregation.source_game_count == 1
    assert len(aggregation.records) == 3
    assert all(record.games_played == 1 for record in exported.records)
    records = {
        row.statistics_record.player_id: row.statistics_record
        for row in aggregation.records
    }
    assert records["player-b"].exact_counts.solo_games_won == 0
    assert records["player-a"].exact_counts.defender_games_won == 1
    assert records["player-c"].exact_counts.defender_games_won == 1


def test_rolling_uses_one_source_game_and_only_actual_target_card_decisions() -> None:
    source = load_historical_data()
    source["played_at"] = "2026-07-10T12:00:00Z"
    target = build_open_play_prefix(completed_trick_count=5, current_trick_card_count=2)
    target["game_id"] = "historical-open-play-target"
    target["played_at"] = "2026-07-11T12:00:00Z"
    dataset = build_training_dataset_input(
        build_training_input([source, target], ["train", "validation"])
    )
    result = build_serializable_rolling_opponent_policy_evaluation(
        evaluate_rolling_opponent_policy_predictions(dataset)
    )
    target_summary = result["target_games"][0]

    assert target_summary["as_of_source_game_count"] == 1
    assert target_summary["decision_count"] == 17
    assert len(target_summary["decisions"]) == 17
    assert result["selection"]["target_decision_count"] == 17
    serialized = json.dumps(target_summary["decisions"])
    for forbidden in (
        "defender_open_play",
        "exact_proof",
        "rest_trick_assignment",
        "exposed_cards",
    ):
        assert forbidden not in serialized


def test_package_version_remains_0_8_0() -> None:
    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'version = "0.8.0"' in pyproject
