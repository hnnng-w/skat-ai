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
    assert result["final_settlement_summary"]["effective_game_value"] == 72
    assert result["final_settlement_summary"]["settlement_score"] == 72
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
    assert result["performance_rating_summary"]["settlement_score"] == 72
    assert result["performance_rating_summary"]["rating_score"] == 122
    assert result["performance_rating_summary"]["declarer_rating_score"] == 122
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