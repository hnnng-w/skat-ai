import random
from pathlib import Path

from main import build_analysis_result
from skat_ai.analysis_report import build_card_analysis_report
from skat_ai.dataset_partition_audit import audit_training_dataset_partitions
from skat_ai.historical_game import build_historical_game_summary
from skat_ai.input_loader import (
    build_game_state_from_input,
    get_left_opponent_policy_settings_from_input,
    get_opponent_policy_settings_from_input,
    get_right_opponent_policy_settings_from_input,
    get_simulation_settings_from_input,
    load_historical_game_from_json,
    load_opponent_statistics_from_json,
    load_position_from_json,
    load_training_dataset_from_json,
)
from skat_ai.multi_step_simulation import (
    prepare_state_for_player_action,
    simulate_multiple_steps,
)
from skat_ai.opponent_statistics import build_opponent_statistics_summary
from skat_ai.rolling_opponent_policy_evaluation import (
    evaluate_rolling_opponent_policy_predictions,
)
from skat_ai.rules import get_legal_cards
from skat_ai.training_dataset import build_training_dataset_summary

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_PATH = PROJECT_ROOT / "input_position.json"


def get_example_json_files() -> list[Path]:
    examples_dir = Path("examples")

    return sorted(examples_dir.glob("*.json"))


def get_position_example_json_files() -> list[Path]:
    return [
        path
        for path in get_example_json_files()
        if path.name
        not in {
            "historical_grand_normal_completion.json",
            "historical_opponent_policy_evaluation_dataset.json",
            "historical_opponent_statistics.json",
            "opponent_statistics.json",
            "training_dataset_normal_play.json",
            "training_dataset_partition_audit.json",
        }
    ]


def test_examples_folder_contains_json_files() -> None:
    example_files = get_example_json_files()

    assert len(example_files) > 0


def test_all_example_json_files_can_be_loaded_and_validated() -> None:
    example_files = get_example_json_files()

    for example_file in example_files:
        if example_file.name == "historical_grand_normal_completion.json":
            record = load_historical_game_from_json(str(example_file))
            assert record.game_id == "historical-grand-001"
            continue
        if example_file.name in {
            "historical_opponent_policy_evaluation_dataset.json",
            "training_dataset_normal_play.json",
            "training_dataset_partition_audit.json",
        }:
            dataset = load_training_dataset_from_json(str(example_file))
            assert dataset.dataset_id in {
                "online-games-2026",
                "opponent-policy-evaluation-example",
                "dataset-partition-audit-example",
            }
            continue
        if example_file.name in {
            "historical_opponent_statistics.json",
            "opponent_statistics.json",
        }:
            statistics_input = load_opponent_statistics_from_json(str(example_file))
            assert len(statistics_input.records) == 2
            continue

        data = load_position_from_json(str(example_file))

        assert isinstance(data, dict)


def test_all_example_json_files_can_build_game_state_and_settings() -> None:
    example_files = get_position_example_json_files()

    for example_file in example_files:
        data = load_position_from_json(str(example_file))
        state = build_game_state_from_input(data)
        settings = get_simulation_settings_from_input(data)

        assert state.game_type in [
            "clubs",
            "spades",
            "hearts",
            "diamonds",
            "grand",
            "null",
        ]
        assert isinstance(state.hand, list)
        assert isinstance(state.current_trick, list)
        assert settings["sample_count"] > 0


def test_all_example_json_files_have_legal_cards() -> None:
    example_files = get_position_example_json_files()

    for example_file in example_files:
        data = load_position_from_json(str(example_file))
        state = build_game_state_from_input(data)

        legal_cards = get_legal_cards(
            hand=state.hand,
            current_trick=state.current_trick,
            game_type=state.game_type,
        )

        assert len(legal_cards) > 0


def test_all_example_json_files_can_build_analysis_report() -> None:
    example_files = get_position_example_json_files()

    for example_file in example_files:
        data = load_position_from_json(str(example_file))
        state = build_game_state_from_input(data)
        settings = get_simulation_settings_from_input(data)

        report = build_card_analysis_report(
            state=state,
            left_hand_size=settings["left_hand_size"],
            right_hand_size=settings["right_hand_size"],
            sample_count=20,
            random_seed=settings["random_seed"],
            use_basic_opponent_strategy=settings["use_basic_opponent_strategy"],
        )

        assert len(report) > 0
        assert report[0]["is_recommended"] is True


def test_historical_game_example_builds_complete_summary() -> None:
    path = Path("examples/historical_grand_normal_completion.json")
    summary = build_historical_game_summary(load_historical_game_from_json(str(path)))

    assert summary["game_id"] == "historical-grand-001"
    assert summary["status"] == "complete"
    assert summary["played_at"] == "2026-07-24T18:30:00+02:00"
    assert len(summary["derived_tricks"]) == 10
    assert summary["declarer_points"] + summary["defender_points"] == 120


def test_training_dataset_example_builds_sixty_samples() -> None:
    path = Path("examples/training_dataset_normal_play.json")
    summary = build_training_dataset_summary(load_training_dataset_from_json(str(path)))

    assert summary["record_count"] == 2
    assert summary["sample_count"] == 60
    assert summary["partition_counts"]["train"] == {
        "record_count": 1,
        "sample_count": 30,
    }
    assert summary["partition_counts"]["validation"] == {
        "record_count": 1,
        "sample_count": 30,
    }


def test_rolling_opponent_policy_evaluation_example_builds_target_results() -> None:
    path = Path("examples/historical_opponent_policy_evaluation_dataset.json")
    evaluation = evaluate_rolling_opponent_policy_predictions(
        load_training_dataset_from_json(str(path))
    )

    assert evaluation.selection["target_game_count"] == 1
    assert evaluation.coverage["target_decisions"] == 30
    assert evaluation.coverage["decisions_with_insufficient_confidence"] == 30


def test_dataset_partition_audit_example_has_three_way_overlap() -> None:
    path = Path("examples/training_dataset_partition_audit.json")
    dataset = load_training_dataset_from_json(str(path))
    audit = audit_training_dataset_partitions(dataset, "known_opponent")

    assert len(dataset.records) == 3
    assert audit.compliance_status == "compliant"
    assert audit.overlap_summary["train_validation_test"]["player_ids"] == [
        "player-a",
        "player-b",
        "player-c",
    ]


def test_opponent_statistics_example_preserves_two_ordered_players() -> None:
    path = Path("examples/opponent_statistics.json")
    summary = build_opponent_statistics_summary(
        load_opponent_statistics_from_json(str(path))
    )

    assert summary["record_count"] == 2
    assert [record["player_id"] for record in summary["records"]] == [
        "opponent-123",
        "opponent-789",
    ]
    assert summary["records"][1]["statistics"]["solo_games_played_percent"] == 42.5
    assert summary["records"][0]["profile_derivation"]["classification"] == (
        "cautious_defender"
    )
    assert summary["records"][1]["profile_derivation"]["classification"] == "aggressive"


def test_historical_opponent_statistics_example_matches_stable_player_ids() -> None:
    path = Path("examples/historical_opponent_statistics.json")
    summary = build_opponent_statistics_summary(load_opponent_statistics_from_json(str(path)))

    assert [record["player_id"] for record in summary["records"]] == [
        "player-a",
        "player-c",
    ]
    assert [
        record["profile_derivation"]["actionable_policy_preset"] for record in summary["records"]
    ] == ["cautious_defender", "aggressive_points"]


def test_default_input_position_is_runtime_valid_local_action() -> None:
    data = load_position_from_json(str(DEFAULT_INPUT_PATH))
    state = build_game_state_from_input(data)
    legal_cards = get_legal_cards(
        hand=state.hand,
        current_trick=state.current_trick,
        game_type=state.game_type,
    )
    result = build_analysis_result(
        file_path=str(DEFAULT_INPUT_PATH),
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

    assert state.next_player == "me"
    assert legal_cards
    assert result["recommendation"]["card"] in legal_cards


def build_example_analysis_result(file_name: str) -> dict:
    return build_analysis_result(
        file_path=f"examples/{file_name}",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )


def build_example_opponent_turn_context(file_name: str) -> dict:
    data = load_position_from_json(f"examples/{file_name}")
    state = build_game_state_from_input(data)
    settings = get_simulation_settings_from_input(data)
    opponent_policy_settings = get_opponent_policy_settings_from_input(data)
    left_opponent_policy_settings = get_left_opponent_policy_settings_from_input(data)
    right_opponent_policy_settings = get_right_opponent_policy_settings_from_input(data)

    prepared_state, opponent_lead_result = prepare_state_for_player_action(
        current_state=state,
        left_hand_size=settings["left_hand_size"],
        right_hand_size=settings["right_hand_size"],
        random_generator=random.Random(settings["random_seed"]),
        opponent_lead_policy=opponent_policy_settings["opponent_lead_policy"],
        opponent_response_policy=opponent_policy_settings["opponent_response_policy"],
        left_opponent_policy_settings=left_opponent_policy_settings,
        right_opponent_policy_settings=right_opponent_policy_settings,
    )

    multi_step_result = simulate_multiple_steps(
        state=state,
        left_hand_size=settings["left_hand_size"],
        right_hand_size=settings["right_hand_size"],
        step_count=1,
        random_seed=settings["random_seed"],
        use_basic_opponent_strategy=settings["use_basic_opponent_strategy"],
        card_selection_policy="highest_point",
        opponent_lead_policy=opponent_policy_settings["opponent_lead_policy"],
        opponent_response_policy=opponent_policy_settings["opponent_response_policy"],
        left_opponent_policy_settings=left_opponent_policy_settings,
        right_opponent_policy_settings=right_opponent_policy_settings,
    )

    return {
        "state": state,
        "prepared_state": prepared_state,
        "opponent_lead_result": opponent_lead_result,
        "multi_step_result": multi_step_result,
    }

def assert_adjusted_result_metadata(
    result: dict,
    game_end_reason: str,
    remaining_points_recipient: str | None,
    remaining_points_assigned: int,
) -> None:
    adjusted_result = result["adjusted_game_result_summary"]

    assert adjusted_result["game_end_reason"] == game_end_reason
    assert adjusted_result["remaining_points_recipient"] == remaining_points_recipient
    assert adjusted_result["remaining_points_assigned"] == remaining_points_assigned


def assert_final_settlement_uses_adjusted_result(
    result: dict,
) -> None:
    adjusted_result = result["adjusted_game_result_summary"]
    final_settlement = result["final_settlement_summary"]

    if not final_settlement["is_complete"]:
        return

    assert final_settlement["winner"] == adjusted_result["winner"]
    assert final_settlement["declarer_won_by_card_points"] == (
        adjusted_result["winner"] == "declarer"
    )

def test_not_ended_example_adjusted_result_invariants() -> None:
    result = build_example_analysis_result("grand_second_position.json")

    assert result["game_result_summary"]["is_complete"] is False
    assert result["adjusted_game_result_summary"]["is_complete"] is False

    assert result["adjusted_game_result_summary"]["declarer_points"] == (
        result["game_result_summary"]["declarer_points"]
    )
    assert result["adjusted_game_result_summary"]["defender_points"] == (
        result["game_result_summary"]["defender_points"]
    )
    assert result["adjusted_game_result_summary"]["points_remaining"] == (
        result["game_result_summary"]["points_remaining"]
    )

    assert_adjusted_result_metadata(
        result=result,
        game_end_reason="not_ended",
        remaining_points_recipient=None,
        remaining_points_assigned=0,
    )

    assert result["information_policy_summary"]["live_information_enforced"] is True
    assert result["information_policy_summary"]["known_skat_cards_allowed"] is False
    assert result["information_policy_summary"]["ended_game_allowed"] is False

def test_normal_completion_example_adjusted_result_invariants() -> None:
    result = build_example_analysis_result("grand_complete_declarer_win.json")

    assert result["game_result_summary"]["is_complete"] is True
    assert result["adjusted_game_result_summary"]["is_complete"] is True

    assert result["adjusted_game_result_summary"]["declarer_points"] == (
        result["game_result_summary"]["declarer_points"]
    )
    assert result["adjusted_game_result_summary"]["defender_points"] == (
        result["game_result_summary"]["defender_points"]
    )
    assert result["adjusted_game_result_summary"]["points_remaining"] == 0

    assert_adjusted_result_metadata(
        result=result,
        game_end_reason="normal_completion",
        remaining_points_recipient=None,
        remaining_points_assigned=0,
    )

    assert_final_settlement_uses_adjusted_result(result)

    assert result["information_policy_summary"]["live_information_enforced"] is False
    assert result["information_policy_summary"]["known_skat_cards_allowed"] is True
    assert result["information_policy_summary"]["ended_game_allowed"] is True

def test_complete_declarer_win_example_settlement_invariants() -> None:
    result = build_example_analysis_result("grand_complete_declarer_win.json")

    assert result["game_value_summary"]["game_value"] == 72
    assert result["game_value_summary"]["details"]["is_complete"] is True

    assert result["game_result_summary"]["is_complete"] is True
    assert result["game_result_summary"]["winner"] == "declarer"
    assert result["game_result_summary"]["declarer_points"] == 90
    assert result["game_result_summary"]["defender_points"] == 30
    assert result["game_result_summary"]["effective_schneider_status"] == (
        "declarer_made_schneider"
    )
    assert result["game_result_summary"]["effective_schwarz_status"] == "none"

    assert result["final_settlement_summary"]["is_complete"] is True
    assert result["final_settlement_summary"]["missing_inputs"] == []
    assert result["final_settlement_summary"]["winner"] == "declarer"
    assert result["final_settlement_summary"]["game_value"] == 72
    assert result["final_settlement_summary"]["effective_game_value"] == 96
    assert result["final_settlement_summary"]["settlement_score"] == 96
    assert result["final_settlement_summary"]["is_loss"] is False
    assert result["final_settlement_summary"]["overbid_required_game_value"] == 72

    assert result["game_declaration"]["bid_value"] == 72

    assert result["overbid_summary"] == {
        "bid_value": 72,
        "game_value": 72,
        "is_overbid": False,
        "margin": 0,
        "required_game_value": 72,
        "status": "not_overbid",
    }

    assert result["performance_rating_summary"]["is_implemented"] is False
    assert result["performance_rating_summary"]["is_partially_implemented"] is True
    assert result["performance_rating_summary"]["implemented_scope"] == (
        "declarer_single_game_rating"
    )
    assert result["performance_rating_summary"]["unsupported_scope"] == (
        "full_list_series_tournament_rating"
    )
    assert result["performance_rating_summary"]["rating_system"] == "isko_list"
    assert result["performance_rating_summary"]["game_outcome"] == "declarer_win"
    assert result["performance_rating_summary"]["settlement_score"] == 96
    assert result["performance_rating_summary"]["rating_score"] == 146
    assert result["performance_rating_summary"]["declarer_rating_score"] == 146
    assert result["performance_rating_summary"]["declarer_rating_points"] == 50
    assert result["performance_rating_summary"]["counterparty_rating_points"] == 0
    assert result["performance_rating_summary"]["defender_rating_points"] == 0
    assert result["performance_rating_summary"]["unsupported_reason"] == (
        "full_list_series_tournament_rating_not_implemented"
    )
    
def test_complete_declarer_loss_example_settlement_invariants() -> None:
    result = build_example_analysis_result("grand_complete_declarer_loss.json")

    assert result["game_value_summary"]["game_value"] == 72
    assert result["game_value_summary"]["details"]["is_complete"] is True

    assert result["game_result_summary"]["is_complete"] is True
    assert result["game_result_summary"]["winner"] == "defenders"
    assert result["game_result_summary"]["declarer_points"] == 50
    assert result["game_result_summary"]["defender_points"] == 70
    assert result["game_result_summary"]["effective_schneider_status"] == "none"
    assert result["game_result_summary"]["effective_schwarz_status"] == "none"

    assert result["final_settlement_summary"]["is_complete"] is True
    assert result["final_settlement_summary"]["missing_inputs"] == []
    assert result["final_settlement_summary"]["winner"] == "defenders"
    assert result["final_settlement_summary"]["game_value"] == 72
    assert result["final_settlement_summary"]["settlement_score"] == -144
    assert result["final_settlement_summary"]["is_loss"] is True

    assert result["performance_rating_summary"]["rating_system"] == "isko_list"
    assert result["performance_rating_summary"]["table_player_count"] == 3
    assert result["performance_rating_summary"]["game_outcome"] == "declarer_loss"
    assert result["performance_rating_summary"]["settlement_score"] == -144
    assert result["performance_rating_summary"]["rating_score"] == -194
    assert result["performance_rating_summary"]["declarer_rating_score"] == -194
    assert result["performance_rating_summary"]["declarer_rating_points"] == -50
    assert result["performance_rating_summary"]["counterparty_rating_points"] == 40
    assert result["performance_rating_summary"]["defender_rating_points"] == 40
    assert result["performance_rating_summary"]["is_partially_implemented"] is True
    assert result["performance_rating_summary"]["implemented_scope"] == (
        "declarer_single_game_rating"
    )
    assert result["performance_rating_summary"]["unsupported_scope"] == (
        "full_list_series_tournament_rating"
    )


def test_list_performance_input_example_adds_aggregated_summary() -> None:
    baseline_result = build_example_analysis_result("grand_complete_declarer_win.json")
    result = build_example_analysis_result("grand_list_performance_input.json")

    assert result["performance_rating_summary"] == baseline_result[
        "performance_rating_summary"
    ]
    assert result["list_performance_summary"] == {
        "rating_system": "isko_list",
        "basis": "aggregated_list_or_series_totals",
        "table_size": 3,
        "player_game_points": 120,
        "own_games_won": 3,
        "own_games_lost": 1,
        "other_players_lost_games": 2,
        "own_game_bonus_points": 100,
        "opponent_loss_bonus_points": 80,
        "total_performance_points": 300,
    }


def test_list_game_contributions_example_adds_aggregated_summary() -> None:
    baseline_result = build_example_analysis_result("grand_complete_declarer_win.json")
    result = build_example_analysis_result("grand_list_game_contributions.json")

    assert "performance_rating_summary" in result
    assert result["performance_rating_summary"] == baseline_result[
        "performance_rating_summary"
    ]
    assert result["list_performance_summary"] == {
        "rating_system": "isko_list",
        "basis": "normalized_game_contributions",
        "table_size": 3,
        "player_game_points": 24,
        "own_games_won": 1,
        "own_games_lost": 1,
        "other_players_lost_games": 1,
        "own_game_bonus_points": 0,
        "opponent_loss_bonus_points": 40,
        "total_performance_points": 64,
    }


def test_list_analysis_results_example_adds_aggregated_summary() -> None:
    baseline_result = build_example_analysis_result("grand_complete_declarer_win.json")
    result = build_example_analysis_result("grand_list_analysis_results.json")

    assert "performance_rating_summary" in result
    assert result["performance_rating_summary"] == baseline_result[
        "performance_rating_summary"
    ]
    assert result["list_performance_summary"] == {
        "rating_system": "isko_list",
        "basis": "local_analysis_results",
        "table_size": 3,
        "player_game_points": 24,
        "own_games_won": 1,
        "own_games_lost": 1,
        "other_players_lost_games": 1,
        "own_game_bonus_points": 0,
        "opponent_loss_bonus_points": 40,
        "total_performance_points": 64,
    }


def test_list_standings_input_example_adds_three_player_standings() -> None:
    result = build_example_analysis_result("grand_list_standings_input.json")

    assert "list_performance_summary" not in result
    assert result["list_standings_summary"] == {
        "rating_system": "isko_list",
        "basis": "fixed_three_player_game_results",
        "table_size": 3,
        "player_count": 3,
        "game_count": 3,
        "ranking_status": "final",
        "lot_required_player_ids": [],
        "applied_lot_order": None,
        "standings": [
            {
                "rank": 1,
                "input_order": 1,
                "player_id": "alice",
                "player_label": "Alice",
                "games_played": 3,
                "declarer_games": 1,
                "defender_games": 2,
                "own_games_won": 1,
                "own_games_lost": 0,
                "defender_games_won": 1,
                "defender_games_lost": 1,
                "other_players_lost_games": 1,
                "player_game_points": 96,
                "own_game_bonus_points": 50,
                "opponent_loss_bonus_points": 40,
                "total_performance_points": 186,
            },
            {
                "rank": 2,
                "input_order": 3,
                "player_id": "carol",
                "player_label": "Carol",
                "games_played": 3,
                "declarer_games": 1,
                "defender_games": 2,
                "own_games_won": 1,
                "own_games_lost": 0,
                "defender_games_won": 1,
                "defender_games_lost": 1,
                "other_players_lost_games": 1,
                "player_game_points": 48,
                "own_game_bonus_points": 50,
                "opponent_loss_bonus_points": 40,
                "total_performance_points": 138,
            },
            {
                "rank": 3,
                "input_order": 2,
                "player_id": "bob",
                "player_label": "Bob",
                "games_played": 3,
                "declarer_games": 1,
                "defender_games": 2,
                "own_games_won": 0,
                "own_games_lost": 1,
                "defender_games_won": 0,
                "defender_games_lost": 2,
                "other_players_lost_games": 0,
                "player_game_points": -72,
                "own_game_bonus_points": -50,
                "opponent_loss_bonus_points": 0,
                "total_performance_points": -122,
            },
        ],
    }


def test_midgame_declarer_ahead_example_score_invariants() -> None:
    result = build_example_analysis_result("grand_midgame_declarer_ahead.json")

    assert result["score_summary"]["completed_trick_declarer_points"] == 31
    assert result["score_summary"]["completed_trick_defender_points"] == 25
    assert result["score_summary"]["total_declarer_points"] == 31
    assert result["score_summary"]["total_defender_points"] == 25

    assert result["game_value_summary"]["game_value"] == 72
    assert result["game_result_summary"]["is_complete"] is False
    assert result["game_result_summary"]["winner"] == "undecided"
    assert result["final_settlement_summary"]["is_complete"] is False
    assert result["final_settlement_summary"]["missing_inputs"] == [
        "complete_card_points"
    ]

def test_midgame_defenders_ahead_example_score_invariants() -> None:
    result = build_example_analysis_result("grand_midgame_defenders_ahead.json")

    assert result["score_summary"]["completed_trick_declarer_points"] == 6
    assert result["score_summary"]["completed_trick_defender_points"] == 50
    assert result["score_summary"]["total_declarer_points"] == 6
    assert result["score_summary"]["total_defender_points"] == 50

    assert result["game_value_summary"]["game_value"] == 48
    assert result["game_result_summary"]["is_complete"] is False
    assert result["game_result_summary"]["winner"] == "undecided"
    assert result["final_settlement_summary"]["is_complete"] is False
    assert result["final_settlement_summary"]["missing_inputs"] == [
        "complete_card_points"
    ]


def test_midgame_profile_preset_example_metadata_invariants() -> None:
    result = build_example_analysis_result("grand_midgame_profile_preset_live.json")

    assert result["analysis_metadata"]["strategic_metadata"] == {
        "analysis_mode": "live_decision",
        "skat_visibility": "unknown",
        "game_end_reason": "not_ended",
    }
    assert result["profile_preset_settings"] == {
        "use_profile_presets": True,
    }
    assert result["opponent_policy_settings"] == {
        "opponent_lead_policy": "basic_defender_lead",
        "opponent_response_policy": "basic_defender_response",
    }
    assert result["analysis_metadata"]["left_player_profile"]["games_played"] == 860
    assert result["analysis_metadata"]["right_player_profile"]["solo_rate"] == 0.42
    assert result["analysis_metadata"]["recommended_opponent_policy_presets"] == {
        "left_player_recommended_preset": "cautious_defender",
        "right_player_recommended_preset": "aggressive_points",
    }

def test_spades_midgame_defender_live_example_invariants() -> None:
    result = build_example_analysis_result(
        "spades_midgame_defender_rearhand_live.json"
    )

    assert result["position"]["player_role"] == "defender"
    assert result["position"]["declarer_player"] == "left"
    assert result["position"]["player_position"] == "rearhand"
    assert result["position"]["current_trick"] == ["C10", "CQ"]
    assert result["position"]["skat"] == []

    assert result["analysis_metadata"]["strategic_metadata"] == {
        "analysis_mode": "live_decision",
        "skat_visibility": "unknown",
        "game_end_reason": "not_ended",
    }
    assert result["information_policy_summary"]["live_information_enforced"] is True
    assert result["information_policy_summary"]["known_skat_cards_allowed"] is False
    assert result["information_policy_summary"]["ended_game_allowed"] is False

    assert result["score_summary"]["completed_trick_declarer_points"] == 59
    assert result["score_summary"]["completed_trick_defender_points"] == 21
    assert result["score_summary"]["total_declarer_points"] == 59
    assert result["score_summary"]["total_defender_points"] == 21

    assert result["game_value_summary"]["game_value"] == 22
    assert result["game_result_summary"]["is_complete"] is False
    assert result["final_settlement_summary"]["is_complete"] is False


def test_late_game_history_heavy_live_example_invariants() -> None:
    result = build_example_analysis_result("grand_late_game_history_heavy_live.json")

    assert result["position"]["player_role"] == "defender"
    assert result["position"]["declarer_player"] == "left"
    assert result["position"]["current_trick"] == ["D8", "D9"]
    assert result["position"]["hand"] == ["D7"]
    assert len(result["position"]["completed_tricks"]) == 9
    assert result["settings"]["left_hand_size"] == 0
    assert result["settings"]["right_hand_size"] == 0

    assert result["legal_cards"] == ["D7"]
    assert result["recommendation"]["card"] == "D7"

    assert result["game_declaration"]["matadors"] == 2
    assert result["game_value_summary"]["game_value"] == 72
    assert result["game_value_summary"]["details"]["matadors"] == 2

    assert result["score_summary"]["completed_trick_declarer_points"] == 106
    assert result["score_summary"]["completed_trick_defender_points"] == 6
    assert result["information_policy_summary"]["live_information_enforced"] is True
    assert result["information_policy_summary"][
        "unverifiable_completed_trick_winner_metadata_allowed"
    ] is False


def test_post_game_known_skat_example_metadata_invariants() -> None:
    result = build_example_analysis_result("grand_post_game_known_skat.json")

    assert result["analysis_metadata"]["strategic_metadata"] == {
        "analysis_mode": "post_game_review",
        "skat_visibility": "known_post_game",
        "game_end_reason": "normal_completion",
    }

    assert result["position"]["skat"] == ["C7", "D8"]
    assert result["position"]["trick_leader"] == "left"
    assert result["position"]["next_player"] == "left"
    assert result["position"]["current_trick"] == []

    assert result["score_summary"]["total_declarer_points"] == 75
    assert result["score_summary"]["total_defender_points"] == 45
    assert result["adjusted_game_result_summary"]["is_complete"] is True
    assert result["final_settlement_summary"]["is_complete"] is True
    assert result["final_settlement_summary"]["settlement_score"] == 72

    assert (
        result["analysis_metadata"]["recommended_opponent_policy_presets"][
            "left_player_recommended_preset"
        ]
        == "cautious_defender"
    )
    assert (
        result["analysis_metadata"]["recommended_opponent_policy_presets"][
            "right_player_recommended_preset"
        ]
        == "aggressive_points"
    )


def test_post_game_mistake_actual_card_example_has_gap_details() -> None:
    result = build_example_analysis_result("grand_post_game_mistake_actual_card.json")

    summary = result["post_game_review_summary"]

    assert summary["is_available"] is True
    assert summary["actual_card_played"] == "S9"
    assert summary["recommended_card"] == "SA"
    assert summary["expected_point_swing_difference"] == 11.0
    assert summary["decision_quality"] == "mistake"
    assert summary["decision_factors"] == [
        "lower_expected_point_swing_than_recommendation",
        "large_expected_point_swing_gap",
    ]
    assert summary["actual_card_rank"] == 3
    assert summary["recommended_card_rank"] == 1
    assert summary["candidate_count"] == 3
    assert summary["better_card_count"] == 2


def test_post_game_acceptable_actual_card_example_has_small_gap() -> None:
    result = build_example_analysis_result("grand_post_game_acceptable_actual_card.json")

    summary = result["post_game_review_summary"]

    assert summary["is_available"] is True
    assert summary["actual_card_played"] == "S10"
    assert summary["recommended_card"] == "SA"
    assert summary["expected_point_swing_difference"] == 1.0
    assert summary["decision_quality"] == "acceptable"
    assert summary["decision_factors"] == [
        "lower_expected_point_swing_than_recommendation",
        "small_expected_point_swing_gap",
    ]
    assert summary["actual_card_rank"] == 2
    assert summary["recommended_card_rank"] == 1
    assert summary["candidate_count"] == 3
    assert summary["better_card_count"] == 1


def test_null_post_game_objective_example_uses_null_objective() -> None:
    result = build_example_analysis_result("null_post_game_objective_actual_card.json")

    summary = result["post_game_review_summary"]

    assert result["position"]["game_type"] == "null"
    assert summary["is_available"] is True
    assert summary["actual_card_played"] == "C8"
    assert summary["recommended_card"] == "C7"
    assert summary["actual_expected_point_swing"] != (
        summary["recommended_expected_point_swing"]
    )
    assert summary["decision_quality"] == "optimal"
    assert summary["decision_factors"] == ["no_missed_null_objective"]
    assert "Null contract-objective utility" in summary["decision_explanation"]
    assert summary["actual_card_rank"] == 2
    assert summary["recommended_card_rank"] == 1
    assert summary["candidate_count"] == 2
    assert summary["better_card_count"] == 0


def test_post_game_defender_actual_card_example_uses_defender_perspective() -> None:
    result = build_example_analysis_result("spades_post_game_defender_actual_card.json")

    summary = result["post_game_review_summary"]

    assert result["position"]["player_role"] == "defender"
    assert result["position"]["declarer_player"] == "left"
    assert summary["is_available"] is True
    assert summary["actual_card_played"] == "CK"
    assert summary["recommended_card"] == "C7"
    assert summary["expected_point_swing_difference"] == 4.0
    assert summary["decision_quality"] == "suboptimal"
    assert summary["decision_factors"] == [
        "lower_expected_point_swing_than_recommendation",
        "medium_expected_point_swing_gap",
    ]
    assert summary["actual_card_rank"] == 2
    assert summary["recommended_card_rank"] == 1
    assert summary["candidate_count"] == 2
    assert summary["better_card_count"] == 1

def test_default_grand_second_position_infers_game_value() -> None:
    result = build_example_analysis_result("grand_second_position.json")

    assert result["game_declaration"]["matadors"] == 4
    assert result["game_value_summary"]["game_level"] == 5
    assert result["game_value_summary"]["game_value"] == 120
    assert result["game_value_summary"]["details"]["matadors"] == 4
    assert result["game_value_summary"]["details"]["matador_multiplier"] == 5
    assert result["game_value_summary"]["details"]["is_complete"] is True


def test_left_right_opponent_policy_example_uses_distinct_policy_settings() -> None:
    result = build_example_analysis_result("grand_left_right_opponent_policies.json")

    assert result["opponent_policy_settings"] == {
        "opponent_lead_policy": "lowest_point",
        "opponent_response_policy": "lowest_point",
    }
    assert result["left_opponent_policy_settings"] == {
        "opponent_lead_policy": "highest_point",
        "opponent_response_policy": "basic_trick_play",
    }
    assert result["right_opponent_policy_settings"] == {
        "opponent_lead_policy": "basic_defender_lead",
        "opponent_response_policy": "basic_defender_response",
    }


def test_left_to_act_live_example_prepares_local_third_hand_decision() -> None:
    context = build_example_opponent_turn_context("grand_left_to_act_live.json")
    state = context["state"]
    prepared_state = context["prepared_state"]
    opponent_lead_result = context["opponent_lead_result"]
    multi_step_result = context["multi_step_result"]

    assert state.next_player == "left"
    assert opponent_lead_result == {
        "leader": "left",
        "lead_card": "H9",
        "responder": "right",
        "response_card": "C8",
        "next_state": prepared_state,
    }
    assert prepared_state.trick_leader == "left"
    assert prepared_state.current_trick == ["H9", "C8"]
    assert prepared_state.next_player == "me"
    assert set(prepared_state.current_trick).isdisjoint(state.hand)

    legal_cards = get_legal_cards(
        hand=prepared_state.hand,
        current_trick=prepared_state.current_trick,
        game_type=prepared_state.game_type,
    )

    assert legal_cards == state.hand

    step = multi_step_result["steps"][0]

    assert multi_step_result["steps_simulated"] == 1
    assert step["opponent_lead_result"]["leader"] == "left"
    assert step["opponent_lead_result"]["responder"] == "right"
    assert step["candidate_card"] in legal_cards
    assert step["detailed_result"]["trick"] == ["H9", "C8", "SA"]


def test_right_to_act_live_example_prepares_local_second_hand_decision() -> None:
    context = build_example_opponent_turn_context("grand_right_to_act_live.json")
    state = context["state"]
    prepared_state = context["prepared_state"]
    opponent_lead_result = context["opponent_lead_result"]
    multi_step_result = context["multi_step_result"]

    assert state.next_player == "right"
    assert opponent_lead_result == {
        "leader": "right",
        "lead_card": "C8",
        "next_state": prepared_state,
    }
    assert prepared_state.trick_leader == "right"
    assert prepared_state.current_trick == ["C8"]
    assert prepared_state.next_player == "me"
    assert set(prepared_state.current_trick).isdisjoint(state.hand)

    legal_cards = get_legal_cards(
        hand=prepared_state.hand,
        current_trick=prepared_state.current_trick,
        game_type=prepared_state.game_type,
    )

    assert legal_cards == state.hand

    step = multi_step_result["steps"][0]

    assert multi_step_result["steps_simulated"] == 1
    assert step["opponent_lead_result"]["leader"] == "right"
    assert step["candidate_card"] in legal_cards
    assert step["detailed_result"]["trick"] == ["C8", "SA", "CK"]
    assert step["detailed_result"]["completed_trick"]["players"] == [
        "right",
        "me",
        "left",
    ]

def test_claimed_remaining_tricks_example_adjusts_result() -> None:
    result = build_example_analysis_result("grand_claimed_remaining_tricks.json")

    assert result["game_result_summary"]["declarer_points"] == 46
    assert result["game_result_summary"]["defender_points"] == 45
    assert result["game_result_summary"]["points_remaining"] == 29
    assert result["game_result_summary"]["is_complete"] is False

    assert result["adjusted_game_result_summary"]["declarer_points"] == 75
    assert result["adjusted_game_result_summary"]["defender_points"] == 45
    assert result["adjusted_game_result_summary"]["points_remaining"] == 0
    assert result["adjusted_game_result_summary"]["is_complete"] is True
    assert result["adjusted_game_result_summary"]["winner"] == "declarer"
    assert_adjusted_result_metadata(
        result=result,
        game_end_reason="declarer_claimed_remaining_tricks",
        remaining_points_recipient="declarer",
        remaining_points_assigned=29,
    )

    assert result["final_settlement_summary"]["is_complete"] is True
    assert result["final_settlement_summary"]["winner"] == "declarer"
    assert result["final_settlement_summary"]["settlement_score"] == 72
    assert result["final_settlement_summary"]["is_loss"] is False
    assert_adjusted_result_metadata(
        result=result,
        game_end_reason="declarer_claimed_remaining_tricks",
        remaining_points_recipient="declarer",
        remaining_points_assigned=29,
    )

    assert_final_settlement_uses_adjusted_result(result)

def test_declarer_conceded_remaining_tricks_example_adjusts_result() -> None:
    result = build_example_analysis_result(
        "grand_declarer_conceded_remaining_tricks.json"
    )

    assert result["game_result_summary"]["declarer_points"] == 36
    assert result["game_result_summary"]["defender_points"] == 55
    assert result["game_result_summary"]["points_remaining"] == 29
    assert result["game_result_summary"]["is_complete"] is False

    assert result["adjusted_game_result_summary"]["declarer_points"] == 36
    assert result["adjusted_game_result_summary"]["defender_points"] == 84
    assert result["adjusted_game_result_summary"]["points_remaining"] == 0
    assert result["adjusted_game_result_summary"]["is_complete"] is True
    assert result["adjusted_game_result_summary"]["winner"] == "defenders"
    assert (
        result["adjusted_game_result_summary"]["game_end_reason"]
        == "declarer_conceded_remaining_tricks"
    )
    assert result["adjusted_game_result_summary"]["remaining_points_recipient"] == (
        "defenders"
    )
    assert result["adjusted_game_result_summary"]["remaining_points_assigned"] == 29

    assert result["final_settlement_summary"]["is_complete"] is True
    assert result["final_settlement_summary"]["winner"] == "defenders"
    assert result["final_settlement_summary"]["settlement_score"] == -144
    assert result["final_settlement_summary"]["is_loss"] is True
    assert result["performance_rating_summary"]["game_outcome"] == "declarer_loss"
    assert result["performance_rating_summary"]["settlement_score"] == -144
    assert_adjusted_result_metadata(
        result=result,
        game_end_reason="declarer_conceded_remaining_tricks",
        remaining_points_recipient="defenders",
        remaining_points_assigned=29,
    )

    assert_final_settlement_uses_adjusted_result(result)


def test_structured_declarer_concession_example_adjudicates_without_points() -> None:
    result = build_example_analysis_result("declarer_concession.json")
    raw = result["game_result_summary"]
    adjusted = result["adjusted_game_result_summary"]
    settlement = result["final_settlement_summary"]

    assert raw["declarer_points"] == 0
    assert raw["defender_points"] == 0
    assert raw["points_remaining"] == 120
    assert raw["is_complete"] is False
    assert adjusted["declarer_points"] == 0
    assert adjusted["defender_points"] == 0
    assert adjusted["points_remaining"] == 120
    assert adjusted["is_complete"] is True
    assert adjusted["winner"] == "defenders"
    assert adjusted["status"] == "final_adjudicated"
    assert adjusted["remaining_points_recipient"] is None
    assert adjusted["remaining_points_assigned"] == 0
    assert result["game_shortening_summary"]["rule_sections"] == ["4.4.1"]
    assert result["game_shortening_summary"]["hand_card_count_reconciliation"] == (
        "confirmed"
    )
    assert settlement["game_value"] == 72
    assert settlement["effective_game_value"] == 72
    assert settlement["settlement_score"] == -144
    assert settlement["settlement_basis"]["achieved_schneider_applied"] is False
    assert settlement["settlement_basis"]["achieved_schwarz_applied"] is False

def test_defenders_conceded_remaining_tricks_example_adjusts_result() -> None:
    result = build_example_analysis_result(
        "grand_defenders_conceded_remaining_tricks.json"
    )

    assert result["game_result_summary"]["declarer_points"] == 44
    assert result["game_result_summary"]["defender_points"] == 47
    assert result["game_result_summary"]["points_remaining"] == 29
    assert result["game_result_summary"]["is_complete"] is False

    assert result["adjusted_game_result_summary"]["declarer_points"] == 73
    assert result["adjusted_game_result_summary"]["defender_points"] == 47
    assert result["adjusted_game_result_summary"]["points_remaining"] == 0
    assert result["adjusted_game_result_summary"]["is_complete"] is True
    assert result["adjusted_game_result_summary"]["winner"] == "declarer"
    assert (
        result["adjusted_game_result_summary"]["game_end_reason"]
        == "defenders_conceded_remaining_tricks"
    )
    assert result["adjusted_game_result_summary"]["remaining_points_recipient"] == (
        "declarer"
    )
    assert result["adjusted_game_result_summary"]["remaining_points_assigned"] == 29

    assert result["final_settlement_summary"]["is_complete"] is True
    assert result["final_settlement_summary"]["winner"] == "declarer"
    assert result["final_settlement_summary"]["settlement_score"] == 72
    assert result["final_settlement_summary"]["is_loss"] is False
    assert_adjusted_result_metadata(
        result=result,
        game_end_reason="defenders_conceded_remaining_tricks",
        remaining_points_recipient="declarer",
        remaining_points_assigned=29,
    )

    assert_final_settlement_uses_adjusted_result(result)

def test_overbid_example_declarer_wins_card_points_but_loses_settlement() -> None:
    result = build_example_analysis_result(
        "grand_overbid_declarer_card_points_win.json"
    )

    assert result["game_result_summary"]["is_complete"] is True
    assert result["game_result_summary"]["winner"] == "declarer"

    assert result["game_value_summary"]["game_value"] == 48

    assert result["overbid_summary"] == {
        "bid_value": 60,
        "game_value": 48,
        "is_overbid": True,
        "margin": -12,
        "required_game_value": 72,
        "status": "overbid",
    }

    assert result["final_settlement_summary"]["is_complete"] is True
    assert result["final_settlement_summary"]["winner"] == "declarer"
    assert result["final_settlement_summary"]["declarer_won_by_card_points"] is True
    assert result["final_settlement_summary"]["is_overbid"] is True
    assert result["final_settlement_summary"]["is_loss"] is True
    assert result["performance_rating_summary"]["game_outcome"] == "declarer_loss"
    assert result["performance_rating_summary"]["settlement_score"] == -144
    assert result["final_settlement_summary"]["game_value"] == 48
    assert result["final_settlement_summary"]["effective_game_value"] == 72
    assert result["final_settlement_summary"]["bid_value"] == 60
    assert result["final_settlement_summary"]["settlement_score"] == -144


def test_impossible_null_settlement_example() -> None:
    result = build_example_analysis_result(
        "null_impossible_declaration_settlement.json"
    )

    assert result["game_declaration"] == {
        "game_type": "null",
        "hand_game": True,
        "ouvert": True,
        "schneider_announced": False,
        "schwarz_announced": False,
        "matadors": None,
        "bid_value": 60,
    }
    assert result["game_value_summary"]["game_value"] == 59
    replacement = result["overbid_summary"]["impossible_null_settlement"]
    assert replacement == {
        "replacement_game_type": "clubs",
        "matadors": 1,
        "hand_game": True,
        "base_value": 12,
        "minimum_game_value": 36,
        "required_game_value": 60,
    }
    assert "ouvert" not in replacement
    assert result["adjusted_game_result_summary"]["winner"] == "defenders"
    assert result["adjusted_game_result_summary"][
        "effective_schwarz_status"
    ] == "not_applicable"
    assert result["final_settlement_summary"]["is_complete"] is True
    assert result["final_settlement_summary"]["settlement_score"] == -120
