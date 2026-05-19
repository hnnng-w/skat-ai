from pathlib import Path

from main import build_analysis_result
from skat_ai.analysis_report import build_card_analysis_report
from skat_ai.input_loader import (
    build_game_state_from_input,
    get_simulation_settings_from_input,
    load_position_from_json,
)
from skat_ai.rules import get_legal_cards


def get_example_json_files() -> list[Path]:
    examples_dir = Path("examples")

    return sorted(examples_dir.glob("*.json"))


def test_examples_folder_contains_json_files() -> None:
    example_files = get_example_json_files()

    assert len(example_files) > 0


def test_all_example_json_files_can_be_loaded_and_validated() -> None:
    example_files = get_example_json_files()

    for example_file in example_files:
        data = load_position_from_json(str(example_file))

        assert isinstance(data, dict)


def test_all_example_json_files_can_build_game_state_and_settings() -> None:
    example_files = get_example_json_files()

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
    example_files = get_example_json_files()

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
    example_files = get_example_json_files()

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

def build_example_analysis_result(file_name: str) -> dict:
    return build_analysis_result(
        file_path=f"examples/{file_name}",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

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
    assert result["final_settlement_summary"]["settlement_score"] == 72
    assert result["final_settlement_summary"]["is_loss"] is False

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

def test_post_game_known_skat_example_metadata_invariants() -> None:
    result = build_example_analysis_result("grand_post_game_known_skat.json")

    assert result["analysis_metadata"]["strategic_metadata"] == {
        "analysis_mode": "post_game_review",
        "skat_visibility": "known_post_game",
        "game_end_reason": "normal_completion",
    }

    assert result["position"]["skat"] == ["C7", "D8"]
    assert result["position"]["trick_leader"] == "unknown"
    assert result["position"]["next_player"] == "unknown"
    assert result["position"]["current_trick"] == []

    assert result["score_summary"]["total_declarer_points"] == 51
    assert result["score_summary"]["total_defender_points"] == 35
    assert result["game_value_summary"]["game_value"] == 72
    assert result["final_settlement_summary"]["is_complete"] is False

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

def test_default_grand_second_position_has_incomplete_game_value() -> None:
    result = build_example_analysis_result("grand_second_position.json")

    assert result["game_declaration"]["matadors"] is None
    assert result["game_value_summary"]["game_value"] is None
    assert result["game_value_summary"]["details"]["is_complete"] is False
    assert result["final_settlement_summary"]["is_complete"] is False
    assert result["final_settlement_summary"]["missing_inputs"] == [
        "complete_card_points",
        "game_value",
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
    assert (
        result["adjusted_game_result_summary"]["game_end_reason"]
        == "declarer_claimed_remaining_tricks"
    )
    assert result["adjusted_game_result_summary"]["remaining_points_recipient"] == (
        "declarer"
    )
    assert result["adjusted_game_result_summary"]["remaining_points_assigned"] == 29

    assert result["final_settlement_summary"]["is_complete"] is True
    assert result["final_settlement_summary"]["winner"] == "declarer"
    assert result["final_settlement_summary"]["settlement_score"] == 72
    assert result["final_settlement_summary"]["is_loss"] is False

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