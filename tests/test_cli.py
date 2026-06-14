import json

from main import (
    apply_cli_overrides,
    apply_opponent_policy_cli_overrides,
    apply_profile_preset_cli_overrides,
    apply_single_opponent_policy_cli_overrides,
    build_analysis_result,
    build_effective_immediate_response_policy_map,
    print_multi_step_result,
    print_policy_comparison_result,
    run_json_position_analysis,
)
from skat_ai.player_profile import PlayerProfile


def test_apply_cli_overrides_keeps_settings_when_no_overrides_are_given() -> None:
    settings = {
        "left_hand_size": 5,
        "right_hand_size": 5,
        "sample_count": 1000,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
    }

    updated_settings = apply_cli_overrides(
        settings=settings,
        sample_count=None,
        random_seed=None,
        opponent_strategy=None,
    )

    assert updated_settings == settings


def test_apply_cli_overrides_updates_sample_count() -> None:
    settings = {
        "left_hand_size": 5,
        "right_hand_size": 5,
        "sample_count": 1000,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
    }

    updated_settings = apply_cli_overrides(
        settings=settings,
        sample_count=500,
        random_seed=None,
        opponent_strategy=None,
    )

    assert updated_settings["sample_count"] == 500
    assert updated_settings["random_seed"] == 42


def test_apply_cli_overrides_updates_random_seed() -> None:
    settings = {
        "left_hand_size": 5,
        "right_hand_size": 5,
        "sample_count": 1000,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
    }

    updated_settings = apply_cli_overrides(
        settings=settings,
        sample_count=None,
        random_seed=123,
        opponent_strategy=None,
    )

    assert updated_settings["sample_count"] == 1000
    assert updated_settings["random_seed"] == 123


def test_apply_cli_overrides_updates_sample_count_and_random_seed() -> None:
    settings = {
        "left_hand_size": 5,
        "right_hand_size": 5,
        "sample_count": 1000,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
    }

    updated_settings = apply_cli_overrides(
        settings=settings,
        sample_count=500,
        random_seed=123,
        opponent_strategy=None,
    )

    assert updated_settings["sample_count"] == 500
    assert updated_settings["random_seed"] == 123


def test_apply_cli_overrides_does_not_mutate_original_settings() -> None:
    settings = {
        "left_hand_size": 5,
        "right_hand_size": 5,
        "sample_count": 1000,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
    }

    updated_settings = apply_cli_overrides(
        settings=settings,
        sample_count=500,
        random_seed=123,
        opponent_strategy=None,
    )

    assert settings["sample_count"] == 1000
    assert settings["random_seed"] == 42
    assert updated_settings["sample_count"] == 500
    assert updated_settings["random_seed"] == 123

def test_apply_cli_overrides_sets_basic_opponent_strategy() -> None:
    settings = {
        "left_hand_size": 5,
        "right_hand_size": 5,
        "sample_count": 1000,
        "random_seed": 42,
        "use_basic_opponent_strategy": False,
    }

    updated_settings = apply_cli_overrides(
        settings=settings,
        sample_count=None,
        random_seed=None,
        opponent_strategy="basic",
    )

    assert updated_settings["use_basic_opponent_strategy"] is True


def test_apply_cli_overrides_sets_random_opponent_strategy() -> None:
    settings = {
        "left_hand_size": 5,
        "right_hand_size": 5,
        "sample_count": 1000,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
    }

    updated_settings = apply_cli_overrides(
        settings=settings,
        sample_count=None,
        random_seed=None,
        opponent_strategy="random",
    )

    assert updated_settings["use_basic_opponent_strategy"] is False


def test_apply_cli_overrides_updates_all_cli_options() -> None:
    settings = {
        "left_hand_size": 5,
        "right_hand_size": 5,
        "sample_count": 1000,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
    }

    updated_settings = apply_cli_overrides(
        settings=settings,
        sample_count=500,
        random_seed=123,
        opponent_strategy="random",
    )

    assert updated_settings["sample_count"] == 500
    assert updated_settings["random_seed"] == 123
    assert updated_settings["use_basic_opponent_strategy"] is False

def test_build_analysis_result_returns_expected_top_level_keys() -> None:
    result = build_analysis_result(
        file_path="examples/grand_leading.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

    assert set(result.keys()) == {
        "input_file",
        "position",
        "settings",
        "analysis_metadata",
        "legal_cards",
        "analysis_report",
        "strategic_summary",
        "score_summary",
        "recommendation",
        "opponent_policy_settings",
        "left_opponent_policy_settings",
        "right_opponent_policy_settings",
        "profile_preset_settings",
        "game_declaration",
        "game_value_summary",
        "game_result_summary",
        "final_settlement_summary",
        "adjusted_game_result_summary",
        "overbid_summary",
        "performance_rating_summary",
        "information_policy_summary",
        "post_game_review_summary",
    }
    assert "list_performance_summary" not in result


def test_build_analysis_result_omits_list_performance_summary_when_input_absent() -> None:
    result = build_analysis_result(
        file_path="examples/grand_leading.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

    assert "list_performance_summary" not in result


def test_build_analysis_result_contains_recommendation() -> None:
    result = build_analysis_result(
        file_path="examples/grand_leading.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

    assert "card" in result["recommendation"]
    assert "reason" in result["recommendation"]
    assert result["recommendation"]["card"] in result["legal_cards"]


def test_build_analysis_result_applies_cli_overrides() -> None:
    result = build_analysis_result(
        file_path="examples/grand_leading.json",
        sample_count_override=20,
        random_seed_override=123,
        opponent_strategy_override="random",
    )

    assert result["settings"]["sample_count"] == 20
    assert result["settings"]["random_seed"] == 123
    assert result["settings"]["use_basic_opponent_strategy"] is False

def test_build_analysis_result_includes_overbid_summary() -> None:
    result = build_analysis_result(
        file_path="examples/grand_second_position.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

    assert result["overbid_summary"] == {
        "bid_value": None,
        "game_value": 120,
        "is_overbid": None,
        "margin": None,
        "status": "unknown_bid_value",
        "required_game_value": None,
    }

def test_build_analysis_result_includes_performance_rating_summary() -> None:
    result = build_analysis_result(
        file_path="examples/grand_second_position.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

    assert result["performance_rating_summary"] == {
        "is_implemented": False,
        "implemented_scope": None,
        "unsupported_scope": "performance_rating_not_implemented",
        "rating_system": None,
        "basis": "individual_game_settlement",
        "game_outcome": "incomplete",
        "settlement_score": None,
        "rating_score": None,
        "declarer_rating_score": None,
        "declarer_rating_points": None,
        "defender_rating_points": None,
        "unsupported_reason": "performance_rating_not_implemented",
        "is_partially_implemented": False,
        "table_player_count": 3,
        "counterparty_rating_points": None,
        "notes": [
            "Performance rating is separate from individual game settlement.",
            "rating_score currently represents the declarer's rating score.",
            "List, series, and tournament rating are not fully implemented yet.",
            "final_settlement_summary remains the source for single-game settlement.",
        ],
    }


def build_list_performance_cli_input() -> dict[str, object]:
    return {
        "game_type": "grand",
        "player_role": "declarer",
        "player_position": "middlehand",
        "trick_leader": "left",
        "hand": ["SA", "S10", "S9", "H10", "D7"],
        "current_trick": ["S7"],
        "played_cards": [],
        "completed_tricks": [],
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "me",
        "skat": [],
        "left_hand_size": 5,
        "right_hand_size": 5,
        "sample_count": 1000,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
        "performance_rating_system": "isko_list",
    }


def test_build_analysis_result_includes_list_performance_summary(tmp_path) -> None:
    input_path = tmp_path / "list_performance_input.json"
    data = build_list_performance_cli_input()
    data["list_performance_input"] = {
        "player_game_points": 120,
        "own_games_won": 3,
        "own_games_lost": 1,
        "other_players_lost_games": 2,
    }
    input_path.write_text(json.dumps(data), encoding="utf-8")

    result = build_analysis_result(
        file_path=str(input_path),
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

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
    assert result["performance_rating_summary"]["basis"] == (
        "individual_game_settlement"
    )
    assert result["performance_rating_summary"]["game_outcome"] == "incomplete"
    assert result["performance_rating_summary"]["settlement_score"] is None
    assert result["performance_rating_summary"]["rating_score"] is None


def test_build_analysis_result_includes_contribution_list_performance_summary(
    tmp_path,
) -> None:
    input_path = tmp_path / "list_game_contributions.json"
    data = build_list_performance_cli_input()
    data["list_game_contributions"] = [
        {
            "player_role": "declarer",
            "game_outcome": "declarer_win",
            "settlement_score": 96,
        },
        {
            "player_role": "defender",
            "game_outcome": "declarer_loss",
            "settlement_score": -144,
        },
    ]
    input_path.write_text(json.dumps(data), encoding="utf-8")

    result = build_analysis_result(
        file_path=str(input_path),
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

    assert result["list_performance_summary"] == {
        "rating_system": "isko_list",
        "basis": "normalized_game_contributions",
        "table_size": 3,
        "player_game_points": 96,
        "own_games_won": 1,
        "own_games_lost": 0,
        "other_players_lost_games": 1,
        "own_game_bonus_points": 50,
        "opponent_loss_bonus_points": 40,
        "total_performance_points": 186,
    }
    assert result["performance_rating_summary"]["basis"] == (
        "individual_game_settlement"
    )
    assert result["performance_rating_summary"]["game_outcome"] == "incomplete"
    assert result["performance_rating_summary"]["settlement_score"] is None
    assert result["performance_rating_summary"]["rating_score"] is None


def test_build_analysis_result_includes_empty_contribution_list_performance_summary(
    tmp_path,
) -> None:
    input_path = tmp_path / "empty_list_game_contributions.json"
    data = build_list_performance_cli_input()
    data["list_game_contributions"] = []
    input_path.write_text(json.dumps(data), encoding="utf-8")

    result = build_analysis_result(
        file_path=str(input_path),
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

    assert result["list_performance_summary"] == {
        "rating_system": "isko_list",
        "basis": "normalized_game_contributions",
        "table_size": 3,
        "player_game_points": 0,
        "own_games_won": 0,
        "own_games_lost": 0,
        "other_players_lost_games": 0,
        "own_game_bonus_points": 0,
        "opponent_loss_bonus_points": 0,
        "total_performance_points": 0,
    }


def test_build_analysis_result_includes_analysis_result_list_performance_summary(
    tmp_path,
) -> None:
    input_path = tmp_path / "list_analysis_results.json"
    data = build_list_performance_cli_input()
    data["list_analysis_results"] = [
        {
            "position": {
                "player_role": "declarer",
            },
            "final_settlement_summary": {
                "is_complete": True,
                "is_loss": False,
                "settlement_score": 96,
            },
        },
        {
            "position": {
                "player_role": "defender",
            },
            "final_settlement_summary": {
                "is_complete": True,
                "is_loss": True,
                "settlement_score": -144,
            },
        },
    ]
    input_path.write_text(json.dumps(data), encoding="utf-8")

    result = build_analysis_result(
        file_path=str(input_path),
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

    assert result["list_performance_summary"] == {
        "rating_system": "isko_list",
        "basis": "local_analysis_results",
        "table_size": 3,
        "player_game_points": 96,
        "own_games_won": 1,
        "own_games_lost": 0,
        "other_players_lost_games": 1,
        "own_game_bonus_points": 50,
        "opponent_loss_bonus_points": 40,
        "total_performance_points": 186,
    }
    assert result["performance_rating_summary"]["basis"] == (
        "individual_game_settlement"
    )
    assert result["performance_rating_summary"]["game_outcome"] == "incomplete"


def test_build_analysis_result_includes_empty_analysis_result_list_summary(
    tmp_path,
) -> None:
    input_path = tmp_path / "empty_list_analysis_results.json"
    data = build_list_performance_cli_input()
    data["list_analysis_results"] = []
    input_path.write_text(json.dumps(data), encoding="utf-8")

    result = build_analysis_result(
        file_path=str(input_path),
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

    assert result["list_performance_summary"] == {
        "rating_system": "isko_list",
        "basis": "local_analysis_results",
        "table_size": 3,
        "player_game_points": 0,
        "own_games_won": 0,
        "own_games_lost": 0,
        "other_players_lost_games": 0,
        "own_game_bonus_points": 0,
        "opponent_loss_bonus_points": 0,
        "total_performance_points": 0,
    }


def test_build_analysis_result_includes_only_skipped_analysis_result_list_summary(
    tmp_path,
) -> None:
    input_path = tmp_path / "skipped_list_analysis_results.json"
    data = build_list_performance_cli_input()
    data["list_analysis_results"] = [
        {
            "position": {
                "player_role": "declarer",
            },
            "final_settlement_summary": {
                "is_complete": False,
            },
        },
        {
            "position": {
                "player_role": "unknown",
            },
            "final_settlement_summary": {
                "is_complete": True,
                "is_loss": False,
                "settlement_score": 96,
            },
        },
    ]
    input_path.write_text(json.dumps(data), encoding="utf-8")

    result = build_analysis_result(
        file_path=str(input_path),
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

    assert result["list_performance_summary"] == {
        "rating_system": "isko_list",
        "basis": "local_analysis_results",
        "table_size": 3,
        "player_game_points": 0,
        "own_games_won": 0,
        "own_games_lost": 0,
        "other_players_lost_games": 0,
        "own_game_bonus_points": 0,
        "opponent_loss_bonus_points": 0,
        "total_performance_points": 0,
    }


def test_run_json_position_analysis_supports_multi_step() -> None:
    run_json_position_analysis(
        file_path="examples/grand_second_position.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
        output_path=None,
        multi_step_count=1,
        card_selection_policy="first_legal",
        expected_value_sample_count=20,
    )


def test_run_json_position_analysis_rejects_zero_multi_step_count() -> None:
    try:
        run_json_position_analysis(
            file_path="examples/grand_second_position.json",
            sample_count_override=20,
            random_seed_override=42,
            opponent_strategy_override="basic",
            output_path=None,
            multi_step_count=0,
            card_selection_policy="first_legal",
            expected_value_sample_count=20,
        )
    except ValueError as error:
        assert "multi_step_count" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_run_json_position_analysis_supports_highest_expected_value_multi_step() -> None:
    run_json_position_analysis(
        file_path="examples/grand_second_position.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
        output_path=None,
        multi_step_count=1,
        card_selection_policy="highest_expected_value",
        expected_value_sample_count=20,
    )


def test_print_multi_step_result_outputs_summary(capsys) -> None:
    from skat_ai.game_state import GameState

    result = {
        "card_selection_policy": "first_legal",
        "requested_step_count": 1,
        "steps_simulated": 1,
        "stop_reason": "Requested step count reached.",
        "context_summary": {
            "simulated_opponent_card_count": 2,
            "unique_simulated_opponent_card_count": 2,
            "duplicate_simulated_opponent_cards": [],
            "event_count": 1,
        },
        "steps": [
            {
                "step_index": 0,
                "opponent_lead_result": None,
                "candidate_card": "SA",
                "detailed_result": {
                    "trick": ["S7", "SA", "S8"],
                    "did_win": True,
                    "trick_points": 11,
                    "completed_trick": {
                        "cards": ["S7", "SA", "S8"],
                        "winner_role": "declarer",
                    },
                },
            }
        ],
        "final_state": GameState(
            game_type="grand",
            player_role="declarer",
            hand=["S10", "S9"],
            current_trick=[],
            completed_tricks=[
                {
                    "cards": ["S7", "SA", "S8"],
                    "winner_role": "declarer",
                }
            ],
            declarer_points=11,
            defender_points=0,
            next_player="me",
        ),
        "summary": {
            "requested_step_count": 1,
            "steps_simulated": 1,
            "stop_reason": "Requested step count reached.",
            "card_selection_policy": "first_legal",
            "strict_context": False,
            "score_summary": {
                "initial_declarer_points": 0,
                "initial_defender_points": 0,
                "final_declarer_points": 11,
                "final_defender_points": 0,
                "declarer_points_gained": 11,
                "defender_points_gained": 0,
                "final_point_swing": 11,
            },
            "context_summary": {
                "simulated_opponent_card_count": 2,
                "unique_simulated_opponent_card_count": 2,
                "duplicate_simulated_opponent_cards": [],
                "event_count": 1,
            },
        },
    }

    print_multi_step_result(result)

    captured = capsys.readouterr()

    assert "Multi-step simulation" in captured.out
    assert "Card selection policy: first_legal" in captured.out
    assert "Requested steps: 1" in captured.out
    assert "Steps simulated: 1" in captured.out
    assert "Stop reason: Requested step count reached." in captured.out
    assert "Context summary:" in captured.out
    assert "Context warning: none" in captured.out
    assert "Candidate card: SA" in captured.out
    assert "Final state" in captured.out
    assert "Multi-step score summary" in captured.out
    assert "Final point swing: 11" in captured.out


def test_print_multi_step_result_outputs_opponent_lead(capsys) -> None:
    from skat_ai.game_state import GameState

    result = {
        "card_selection_policy": "first_legal",
        "requested_step_count": 1,
        "steps_simulated": 1,
        "stop_reason": "Requested step count reached.",
        "steps": [
            {
                "step_index": 0,
                "opponent_lead_result": {
                    "leader": "right",
                    "lead_card": "D7",
                },
                "candidate_card": "DA",
                "detailed_result": {
                    "trick": ["D7", "DA", "D8"],
                    "did_win": True,
                    "trick_points": 11,
                    "completed_trick": {
                        "cards": ["D7", "DA", "D8"],
                        "players": ["right", "me", "left"],
                        "winner_role": "declarer",
                        "winner_player": "me",
                    },
                },
            }
        ],
        "final_state": GameState(
            game_type="grand",
            player_role="declarer",
            hand=["S10", "S9"],
            current_trick=[],
            completed_tricks=[
                {
                    "cards": ["D7", "DA", "D8"],
                    "players": ["right", "me", "left"],
                    "winner_role": "declarer",
                    "winner_player": "me",
                }
            ],
            declarer_points=11,
            defender_points=0,
            next_player="me",
        ),
        "summary": {
            "requested_step_count": 1,
            "steps_simulated": 1,
            "stop_reason": "Requested step count reached.",
            "card_selection_policy": "first_legal",
            "strict_context": False,
            "score_summary": {
                "initial_declarer_points": 0,
                "initial_defender_points": 0,
                "final_declarer_points": 11,
                "final_defender_points": 0,
                "declarer_points_gained": 11,
                "defender_points_gained": 0,
                "final_point_swing": 11,
            },
            "context_summary": {
                "simulated_opponent_card_count": 2,
                "unique_simulated_opponent_card_count": 2,
                "duplicate_simulated_opponent_cards": [],
                "event_count": 1,
            },
        },
    }

    print_multi_step_result(result)

    captured = capsys.readouterr()

    assert "Opponent lead player: right" in captured.out
    assert "Opponent lead card: D7" in captured.out
    assert "Candidate card: DA" in captured.out


def test_print_multi_step_result_outputs_opponent_response(capsys) -> None:
    from skat_ai.game_state import GameState

    result = {
        "card_selection_policy": "first_legal",
        "requested_step_count": 1,
        "steps_simulated": 1,
        "stop_reason": "Requested step count reached.",
        "steps": [
            {
                "step_index": 0,
                "opponent_lead_result": {
                    "leader": "left",
                    "lead_card": "D7",
                    "responder": "right",
                    "response_card": "D9",
                },
                "candidate_card": "DA",
                "detailed_result": {
                    "trick": ["D7", "D9", "DA"],
                    "did_win": True,
                    "trick_points": 11,
                    "completed_trick": {
                        "cards": ["D7", "D9", "DA"],
                        "players": ["left", "right", "me"],
                        "winner_role": "declarer",
                        "winner_player": "me",
                    },
                },
            }
        ],
        "final_state": GameState(
            game_type="grand",
            player_role="declarer",
            hand=["S10", "S9"],
            current_trick=[],
            completed_tricks=[
                {
                    "cards": ["D7", "D9", "DA"],
                    "players": ["left", "right", "me"],
                    "winner_role": "declarer",
                    "winner_player": "me",
                }
            ],
            declarer_points=11,
            defender_points=0,
            next_player="me",
        ),
        "summary": {
            "requested_step_count": 1,
            "steps_simulated": 1,
            "stop_reason": "Requested step count reached.",
            "card_selection_policy": "first_legal",
            "strict_context": False,
            "score_summary": {
                "initial_declarer_points": 0,
                "initial_defender_points": 0,
                "final_declarer_points": 11,
                "final_defender_points": 0,
                "declarer_points_gained": 11,
                "defender_points_gained": 0,
                "final_point_swing": 11,
            },
            "context_summary": {
                "simulated_opponent_card_count": 2,
                "unique_simulated_opponent_card_count": 2,
                "duplicate_simulated_opponent_cards": [],
                "event_count": 1,
            },
        },
    }

    print_multi_step_result(result)

    captured = capsys.readouterr()

    assert "Opponent lead player: left" in captured.out
    assert "Opponent lead card: D7" in captured.out
    assert "Opponent response player: right" in captured.out
    assert "Opponent response card: D9" in captured.out
    assert "Candidate card: DA" in captured.out

def test_print_multi_step_result_outputs_duplicate_context_warning(capsys) -> None:
    from skat_ai.game_state import GameState

    result = {
        "card_selection_policy": "first_legal",
        "requested_step_count": 1,
        "steps_simulated": 1,
        "stop_reason": "Requested step count reached.",
        "context_summary": {
            "simulated_opponent_card_count": 3,
            "unique_simulated_opponent_card_count": 2,
            "duplicate_simulated_opponent_cards": ["S7"],
            "event_count": 1,
        },
        "steps": [
            {
                "step_index": 0,
                "opponent_lead_result": None,
                "candidate_card": "SA",
                "detailed_result": {
                    "trick": ["S7", "SA", "S8"],
                    "did_win": True,
                    "trick_points": 11,
                    "completed_trick": {
                        "cards": ["S7", "SA", "S8"],
                        "winner_role": "declarer",
                    },
                },
            }
        ],
        "final_state": GameState(
            game_type="grand",
            player_role="declarer",
            hand=["S10", "S9"],
            current_trick=[],
            completed_tricks=[
                {
                    "cards": ["S7", "SA", "S8"],
                    "winner_role": "declarer",
                }
            ],
            declarer_points=11,
            defender_points=0,
            next_player="me",
        ),
        "summary": {
            "requested_step_count": 1,
            "steps_simulated": 1,
            "stop_reason": "Requested step count reached.",
            "card_selection_policy": "first_legal",
            "strict_context": False,
            "score_summary": {
                "initial_declarer_points": 0,
                "initial_defender_points": 0,
                "final_declarer_points": 11,
                "final_defender_points": 0,
                "declarer_points_gained": 11,
                "defender_points_gained": 0,
                "final_point_swing": 11,
            },
            "context_summary": {
                "simulated_opponent_card_count": 2,
                "unique_simulated_opponent_card_count": 2,
                "duplicate_simulated_opponent_cards": [],
                "event_count": 1,
            },
        },
    }

    print_multi_step_result(result)

    captured = capsys.readouterr()

    assert "Context summary:" in captured.out
    assert "Context warning: duplicate simulated opponent cards detected:" in captured.out
    assert "['S7']" in captured.out

def test_run_json_position_analysis_supports_strict_context() -> None:
    run_json_position_analysis(
        file_path="examples/grand_second_position.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
        output_path=None,
        multi_step_count=1,
        card_selection_policy="highest_expected_value",
        expected_value_sample_count=20,
        strict_context=True,
    )

def test_print_policy_comparison_result_outputs_summary(capsys) -> None:
    result = {
        "requested_step_count": 2,
        "random_seed": 42,
        "expected_value_sample_count": 20,
        "use_basic_opponent_strategy": True,
        "strict_context": False,
        "policies": ["lowest_point", "highest_point"],
        "policy_results": [
            {
                "policy": "lowest_point",
                "requested_step_count": 2,
                "steps_simulated": 1,
                "stop_reason": "Requested step count reached.",
                "strict_context": False,
                "declarer_points_gained": 4,
                "defender_points_gained": 10,
                "final_point_swing": -6,
                "context_summary": {},
            },
            {
                "policy": "highest_point",
                "requested_step_count": 2,
                "steps_simulated": 1,
                "stop_reason": "Requested step count reached.",
                "strict_context": False,
                "declarer_points_gained": 14,
                "defender_points_gained": 2,
                "final_point_swing": 12,
                "context_summary": {},
            },
        ],
        "recommended_policy": {
            "policy": "highest_point",
            "reason": "Best final point swing after tie-breakers.",
            "final_point_swing": 12,
            "declarer_points_gained": 14,
            "defender_points_gained": 2,
            "steps_simulated": 1,
            "stop_reason": "Requested step count reached.",
        },
    }

    print_policy_comparison_result(result)

    captured = capsys.readouterr()

    assert "Policy comparison" in captured.out
    assert "lowest_point" in captured.out
    assert "highest_point" in captured.out
    assert "Recommended policy: highest_point" in captured.out
    assert "Recommendation reason: Best final point swing after tie-breakers." in captured.out
    assert "Recommended final point swing: 12" in captured.out

def test_run_json_position_analysis_supports_policy_comparison() -> None:
    run_json_position_analysis(
        file_path="examples/grand_second_position.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
        output_path=None,
        multi_step_count=1,
        card_selection_policy="highest_expected_value",
        expected_value_sample_count=20,
        strict_context=False,
        compare_policies=True,
    )


def test_run_json_position_analysis_writes_policy_comparison_to_output(tmp_path) -> None:
    import json

    output_path = tmp_path / "policy_comparison.json"

    run_json_position_analysis(
        file_path="examples/grand_second_position.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
        output_path=str(output_path),
        multi_step_count=1,
        card_selection_policy="highest_expected_value",
        expected_value_sample_count=20,
        strict_context=False,
        compare_policies=True,
    )

    with output_path.open("r", encoding="utf-8") as file:
        result = json.load(file)

    assert "policy_comparison_result" in result
    assert "policy_results" in result["policy_comparison_result"]
    assert "recommended_policy" in result["policy_comparison_result"]
    assert len(result["policy_comparison_result"]["policy_results"]) >= 1


def test_run_json_position_analysis_supports_comparison_only(capsys) -> None:
    run_json_position_analysis(
        file_path="examples/grand_second_position.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
        output_path=None,
        multi_step_count=1,
        card_selection_policy="highest_expected_value",
        expected_value_sample_count=20,
        strict_context=False,
        compare_policies=True,
        comparison_only=True,
    )

    captured = capsys.readouterr()

    assert "Policy comparison" in captured.out
    assert "Recommended policy:" in captured.out
    assert "Multi-step simulation" not in captured.out
    assert "Multi-step score summary" not in captured.out

def test_run_json_position_analysis_rejects_comparison_only_without_compare_policies() -> None:
    try:
        run_json_position_analysis(
            file_path="examples/grand_second_position.json",
            sample_count_override=20,
            random_seed_override=42,
            opponent_strategy_override="basic",
            output_path=None,
            multi_step_count=1,
            card_selection_policy="highest_expected_value",
            expected_value_sample_count=20,
            strict_context=False,
            compare_policies=False,
            comparison_only=True,
        )
    except ValueError as error:
        assert "comparison_only requires compare_policies" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")

def test_build_analysis_result_includes_default_analysis_metadata() -> None:
    result = build_analysis_result(
        file_path="examples/grand_second_position.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

    assert result["analysis_metadata"]["strategic_metadata"] == {
        "analysis_mode": "live_decision",
        "skat_visibility": "unknown",
        "game_end_reason": "not_ended",
    }

def test_build_analysis_result_includes_information_policy_summary() -> None:
    result = build_analysis_result(
        file_path="examples/grand_second_position.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

    assert result["information_policy_summary"] == {
        "analysis_mode": "live_decision",
        "skat_visibility": "unknown",
        "game_end_reason": "not_ended",
        "live_information_enforced": True,
        "known_post_game_skat_allowed": False,
        "known_skat_cards_allowed": False,
        "ended_game_allowed": False,
        "unverifiable_completed_trick_winner_metadata_allowed": False,
    }
    

def test_build_analysis_result_reads_analysis_metadata() -> None:
    result = build_analysis_result(
        file_path="examples/grand_second_position_with_metadata.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

    assert result["analysis_metadata"]["strategic_metadata"] == {
        "analysis_mode": "post_game_review",
        "skat_visibility": "known_post_game",
        "game_end_reason": "not_ended",
    }
    assert result["analysis_metadata"]["left_player_profile"]["games_played"] == 1240
    assert result["analysis_metadata"]["right_player_profile"]["games_played"] == 520

def test_build_analysis_result_includes_opponent_policy_settings() -> None:
    result = build_analysis_result(
        file_path="examples/grand_second_position.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

    assert result["opponent_policy_settings"] == {
        "opponent_lead_policy": "lowest_point",
        "opponent_response_policy": "lowest_point",
    }


def test_apply_opponent_policy_cli_overrides() -> None:
    settings = apply_opponent_policy_cli_overrides(
        opponent_policy_settings={
            "opponent_lead_policy": "lowest_point",
            "opponent_response_policy": "lowest_point",
        },
        opponent_lead_policy="highest_point",
        opponent_response_policy="basic_trick_play",
    )

    assert settings == {
        "opponent_lead_policy": "highest_point",
        "opponent_response_policy": "basic_trick_play",
    }


def test_apply_opponent_policy_cli_overrides_applies_preset() -> None:
    settings = apply_opponent_policy_cli_overrides(
        opponent_policy_settings={
            "opponent_lead_policy": "lowest_point",
            "opponent_response_policy": "lowest_point",
        },
        opponent_policy_preset="cautious_defender",
    )

    assert settings == {
        "opponent_lead_policy": "basic_defender_lead",
        "opponent_response_policy": "basic_defender_response",
    }


def test_apply_opponent_policy_cli_overrides_explicit_values_override_preset() -> None:
    settings = apply_opponent_policy_cli_overrides(
        opponent_policy_settings={
            "opponent_lead_policy": "lowest_point",
            "opponent_response_policy": "lowest_point",
        },
        opponent_policy_preset="cautious_defender",
        opponent_response_policy="highest_point",
    )

    assert settings == {
        "opponent_lead_policy": "basic_defender_lead",
        "opponent_response_policy": "highest_point",
    }


def test_apply_profile_preset_cli_overrides_defaults_to_unchanged() -> None:
    settings = {
        "use_profile_presets": False,
    }

    updated_settings = apply_profile_preset_cli_overrides(
        profile_preset_settings=settings,
        use_profile_presets=False,
    )

    assert updated_settings == {
        "use_profile_presets": False,
    }
    assert updated_settings is not settings


def test_apply_profile_preset_cli_overrides_enables_profile_presets() -> None:
    settings = {
        "use_profile_presets": False,
    }

    updated_settings = apply_profile_preset_cli_overrides(
        profile_preset_settings=settings,
        use_profile_presets=True,
    )

    assert updated_settings == {
        "use_profile_presets": True,
    }


def test_build_analysis_result_includes_profile_preset_settings() -> None:
    result = build_analysis_result(
        file_path="examples/grand_second_position.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

    assert result["profile_preset_settings"] == {
        "use_profile_presets": False,
    }

def test_build_analysis_result_applies_profile_presets_from_input() -> None:
    result = build_analysis_result(
        file_path="examples/grand_second_position_with_metadata.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

    if result["profile_preset_settings"]["use_profile_presets"]:
        assert result["opponent_policy_settings"]["opponent_lead_policy"] in [
            "lowest_point",
            "basic_defender_lead",
            "highest_point",
        ]

def test_build_analysis_result_includes_game_declaration() -> None:
    result = build_analysis_result(
        file_path="examples/grand_second_position.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

    assert result["game_declaration"] == {
        "game_type": "grand",
        "hand_game": False,
        "ouvert": False,
        "schneider_announced": False,
        "schwarz_announced": False,
        "matadors": 4,
        "bid_value": None,
    }

def test_build_analysis_result_includes_game_value_summary() -> None:
    result = build_analysis_result(
        file_path="examples/grand_second_position.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

    assert result["game_value_summary"] == {
        "game_type": "grand",
        "is_null_game": False,
        "base_value": 24,
        "game_level": 5,
        "game_value": 120,
        "details": {
            "matadors": 4,
            "matador_multiplier": 5,
            "hand_game": False,
            "schneider_announced": False,
            "schwarz_announced": False,
            "ouvert": False,
            "modifier_multiplier": 0,
            "is_complete": True,
        },
    }

def test_build_analysis_result_includes_game_result_summary() -> None:
    result = build_analysis_result(
        file_path="examples/grand_second_position.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

    assert result["game_result_summary"] == {
        "declarer_points": 0,
        "defender_points": 0,
        "points_remaining": 120,
        "is_complete": False,
        "winner": "undecided",
        "status": "in_progress",
        "raw_schneider_status": "declarer_made_schneider",
        "raw_schwarz_status": "declarer_made_schwarz",
        "effective_schneider_status": "pending",
        "effective_schwarz_status": "pending",
        "thresholds": {
            "declarer_win": 61,
            "defender_win": 60,
            "schneider": 30,
            "schwarz": 0,
            "total_card_points": 120,
        },
    }

def test_build_analysis_result_includes_final_settlement_summary() -> None:
    result = build_analysis_result(
        file_path="examples/grand_second_position.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

    assert result["final_settlement_summary"] == {
        "is_complete": False,
        "missing_inputs": ["complete_card_points"],
        "declarer_won_by_card_points": None,
        "winner": None,
        "game_value": 120,
        "bid_value": None,
        "settlement_score": None,
        "is_loss": None,
        "is_overbid": None,
        "overbid_margin": None,
        "overbid_status": "unknown_bid_value",
        "effective_game_value": None,
        "overbid_required_game_value": None,
        "notes": [
            "Settlement score uses simplified Skat logic.",
            "Lost declarer games are counted as -2 * effective_game_value.",
            "Overbid settlement is supported for suit and grand games when "
            "required_game_value is available."
        ],
    }

def test_build_analysis_result_includes_adjusted_game_result_summary() -> None:
    result = build_analysis_result(
        file_path="examples/grand_second_position.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

    assert result["adjusted_game_result_summary"] == {
        "declarer_points": 0,
        "defender_points": 0,
        "points_remaining": 120,
        "is_complete": False,
        "winner": "undecided",
        "status": "in_progress",
        "raw_schneider_status": "declarer_made_schneider",
        "raw_schwarz_status": "declarer_made_schwarz",
        "effective_schneider_status": "pending",
        "effective_schwarz_status": "pending",
        "thresholds": {
            "declarer_win": 61,
            "defender_win": 60,
            "schneider": 30,
            "schwarz": 0,
            "total_card_points": 120,
        },
        "game_end_reason": "not_ended",
        "remaining_points_recipient": None,
        "remaining_points_assigned": 0,
    }

def test_build_analysis_result_includes_left_right_opponent_policy_settings() -> None:
    result = build_analysis_result(
        file_path="examples/grand_second_position.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

    assert result["left_opponent_policy_settings"] == {
        "opponent_lead_policy": "lowest_point",
        "opponent_response_policy": "lowest_point",
    }
    assert result["right_opponent_policy_settings"] == {
        "opponent_lead_policy": "lowest_point",
        "opponent_response_policy": "lowest_point",
    }


def test_apply_single_opponent_policy_cli_overrides_updates_values() -> None:
    settings = {
        "opponent_lead_policy": "lowest_point",
        "opponent_response_policy": "lowest_point",
    }

    updated_settings = apply_single_opponent_policy_cli_overrides(
        opponent_policy_settings=settings,
        opponent_lead_policy="highest_point",
        opponent_response_policy="basic_trick_play",
    )

    assert updated_settings == {
        "opponent_lead_policy": "highest_point",
        "opponent_response_policy": "basic_trick_play",
    }
    assert settings == {
        "opponent_lead_policy": "lowest_point",
        "opponent_response_policy": "lowest_point",
    }


def test_build_analysis_result_applies_left_right_policy_overrides() -> None:
    result = build_analysis_result(
        file_path="examples/grand_second_position.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
        left_opponent_lead_policy_override="highest_point",
        left_opponent_response_policy_override="basic_trick_play",
        right_opponent_lead_policy_override="lowest_point",
        right_opponent_response_policy_override="highest_point",
    )

    assert result["left_opponent_policy_settings"] == {
        "opponent_lead_policy": "highest_point",
        "opponent_response_policy": "basic_trick_play",
    }
    assert result["right_opponent_policy_settings"] == {
        "opponent_lead_policy": "lowest_point",
        "opponent_response_policy": "highest_point",
    }


def build_immediate_response_policy_input(
    policy_fields: dict[str, object] | None = None,
) -> dict[str, object]:
    data: dict[str, object] = {
        "game_type": "grand",
        "player_role": "declarer",
        "player_position": "forehand",
        "trick_leader": "me",
        "hand": ["S7"],
        "current_trick": [],
        "played_cards": [],
        "completed_tricks": [],
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "me",
        "skat": [],
        "left_hand_size": 2,
        "right_hand_size": 2,
        "sample_count": 1,
        "random_seed": 1,
        "use_basic_opponent_strategy": True,
        "analysis_mode": "live_decision",
        "skat_visibility": "unknown",
        "game_end_reason": "not_ended",
        "hand_game": False,
        "ouvert": False,
        "schneider_announced": False,
        "schwarz_announced": False,
        "matadors": 1,
    }

    if policy_fields is not None:
        data.update(policy_fields)

    return data


def build_immediate_response_policy_map_for_test(
    policy_fields: dict[str, object] | None = None,
    left_player_profile: PlayerProfile | None = None,
    right_player_profile: PlayerProfile | None = None,
    opponent_policy_preset_override: str | None = None,
    opponent_response_policy_override: str | None = None,
    use_profile_presets_override: bool = False,
    left_opponent_response_policy_override: str | None = None,
    right_opponent_response_policy_override: str | None = None,
) -> dict[str, str] | None:
    return build_effective_immediate_response_policy_map(
        data=build_immediate_response_policy_input(policy_fields),
        left_player_profile=left_player_profile or PlayerProfile(),
        right_player_profile=right_player_profile or PlayerProfile(),
        opponent_policy_preset_override=opponent_policy_preset_override,
        opponent_response_policy_override=opponent_response_policy_override,
        use_profile_presets_override=use_profile_presets_override,
        left_opponent_response_policy_override=left_opponent_response_policy_override,
        right_opponent_response_policy_override=right_opponent_response_policy_override,
    )


def build_immediate_response_policy_result(
    tmp_path,
    monkeypatch,
    policy_fields: dict[str, object] | None = None,
    opponent_policy_preset_override: str | None = None,
    opponent_response_policy_override: str | None = None,
    use_profile_presets_override: bool = False,
    left_opponent_response_policy_override: str | None = None,
    right_opponent_response_policy_override: str | None = None,
) -> dict[str, object]:
    def fake_generate_random_opponent_hands(
        state,
        left_hand_size: int,
        right_hand_size: int,
        random_generator=None,
    ) -> tuple[list[str], list[str]]:
        _ = (state, left_hand_size, right_hand_size, random_generator)
        return ["S8", "S10"], ["S9", "SA"]

    monkeypatch.setattr(
        "skat_ai.simulation.generate_random_opponent_hands",
        fake_generate_random_opponent_hands,
    )
    input_path = tmp_path / "immediate_response_policy.json"
    input_path.write_text(
        json.dumps(build_immediate_response_policy_input(policy_fields)),
        encoding="utf-8",
    )

    return build_analysis_result(
        file_path=str(input_path),
        sample_count_override=1,
        random_seed_override=1,
        opponent_strategy_override="basic",
        opponent_policy_preset_override=opponent_policy_preset_override,
        opponent_response_policy_override=opponent_response_policy_override,
        use_profile_presets_override=use_profile_presets_override,
        left_opponent_response_policy_override=left_opponent_response_policy_override,
        right_opponent_response_policy_override=right_opponent_response_policy_override,
    )


def get_only_analysis_report_row(result: dict[str, object]) -> dict[str, object]:
    report = result["analysis_report"]

    assert isinstance(report, list)
    assert len(report) == 1

    row = report[0]
    assert isinstance(row, dict)

    return row


def build_aggressive_profile() -> PlayerProfile:
    return PlayerProfile(
        games_played=1000,
        solo_rate=0.38,
    )


def build_cautious_profile() -> PlayerProfile:
    return PlayerProfile(
        games_played=1000,
        solo_rate=0.25,
        grand_rate=0.15,
        hand_game_rate=0.03,
        defender_win_rate=0.55,
    )


def test_immediate_policy_map_defaults_to_none() -> None:
    policy_map = build_immediate_response_policy_map_for_test()

    assert policy_map is None


def test_immediate_policy_map_ignores_profiles_when_disabled() -> None:
    policy_map = build_immediate_response_policy_map_for_test(
        left_player_profile=build_cautious_profile(),
        right_player_profile=build_aggressive_profile(),
    )

    assert policy_map is None


def test_immediate_policy_map_ignores_false_profile_flag() -> None:
    policy_map = build_immediate_response_policy_map_for_test(
        policy_fields={
            "use_profile_presets": False,
        },
        left_player_profile=build_cautious_profile(),
        right_player_profile=build_aggressive_profile(),
    )

    assert policy_map is None


def test_immediate_policy_map_applies_global_json_policy() -> None:
    policy_map = build_immediate_response_policy_map_for_test(
        policy_fields={
            "opponent_response_policy": "highest_point",
        },
    )

    assert policy_map == {
        "left": "highest_point",
        "right": "highest_point",
    }


def test_immediate_policy_map_keeps_side_only_policy_sparse() -> None:
    policy_map = build_immediate_response_policy_map_for_test(
        policy_fields={
            "left_opponent_response_policy": "highest_point",
        },
    )

    assert policy_map == {
        "left": "highest_point",
    }


def test_immediate_policy_map_explicit_lowest_activates() -> None:
    policy_map = build_immediate_response_policy_map_for_test(
        policy_fields={
            "left_opponent_response_policy": "lowest_point",
        },
    )

    assert policy_map == {
        "left": "lowest_point",
    }


def test_immediate_policy_map_side_json_overrides_global_json() -> None:
    policy_map = build_immediate_response_policy_map_for_test(
        policy_fields={
            "opponent_response_policy": "highest_point",
            "right_opponent_response_policy": "lowest_point",
        },
    )

    assert policy_map == {
        "left": "highest_point",
        "right": "lowest_point",
    }


def test_immediate_policy_map_input_preset_activates_both_sides() -> None:
    policy_map = build_immediate_response_policy_map_for_test(
        policy_fields={
            "opponent_policy_preset": "cautious_defender",
        },
    )

    assert policy_map == {
        "left": "basic_defender_response",
        "right": "basic_defender_response",
    }


def test_immediate_policy_map_global_json_overrides_input_preset() -> None:
    policy_map = build_immediate_response_policy_map_for_test(
        policy_fields={
            "opponent_policy_preset": "cautious_defender",
            "opponent_response_policy": "highest_point",
        },
    )

    assert policy_map == {
        "left": "highest_point",
        "right": "highest_point",
    }


def test_immediate_policy_map_side_json_overrides_preset_and_global() -> None:
    policy_map = build_immediate_response_policy_map_for_test(
        policy_fields={
            "opponent_policy_preset": "aggressive_points",
            "opponent_response_policy": "basic_trick_play",
            "left_opponent_response_policy": "lowest_point",
        },
    )

    assert policy_map == {
        "left": "lowest_point",
        "right": "basic_trick_play",
    }


def test_immediate_policy_map_input_profile_presets_apply_by_side() -> None:
    policy_map = build_immediate_response_policy_map_for_test(
        policy_fields={
            "use_profile_presets": True,
        },
        left_player_profile=build_cautious_profile(),
        right_player_profile=build_aggressive_profile(),
    )

    assert policy_map == {
        "left": "basic_defender_response",
        "right": "highest_point",
    }


def test_immediate_policy_map_keeps_non_applicable_profile_side_absent() -> None:
    policy_map = build_immediate_response_policy_map_for_test(
        policy_fields={
            "use_profile_presets": True,
        },
        right_player_profile=build_aggressive_profile(),
    )

    assert policy_map == {
        "right": "highest_point",
    }


def test_immediate_policy_map_cli_profile_presets_apply_by_side() -> None:
    policy_map = build_immediate_response_policy_map_for_test(
        left_player_profile=build_cautious_profile(),
        right_player_profile=build_aggressive_profile(),
        use_profile_presets_override=True,
    )

    assert policy_map == {
        "left": "basic_defender_response",
        "right": "highest_point",
    }


def test_immediate_policy_map_side_json_overrides_profile_policy() -> None:
    policy_map = build_immediate_response_policy_map_for_test(
        policy_fields={
            "use_profile_presets": True,
            "left_opponent_response_policy": "lowest_point",
        },
        left_player_profile=build_cautious_profile(),
        right_player_profile=build_aggressive_profile(),
    )

    assert policy_map == {
        "left": "lowest_point",
        "right": "highest_point",
    }


def test_immediate_policy_map_cli_preset_overrides_input_side() -> None:
    policy_map = build_immediate_response_policy_map_for_test(
        policy_fields={
            "left_opponent_response_policy": "basic_trick_play",
        },
        opponent_policy_preset_override="aggressive_points",
    )

    assert policy_map == {
        "left": "highest_point",
        "right": "highest_point",
    }


def test_immediate_policy_map_cli_profile_overrides_cli_preset_side() -> None:
    policy_map = build_immediate_response_policy_map_for_test(
        right_player_profile=build_cautious_profile(),
        opponent_policy_preset_override="random",
        use_profile_presets_override=True,
    )

    assert policy_map == {
        "left": "random_legal",
        "right": "basic_defender_response",
    }


def test_immediate_policy_map_global_cli_response_overrides_profile() -> None:
    policy_map = build_immediate_response_policy_map_for_test(
        policy_fields={
            "use_profile_presets": True,
        },
        right_player_profile=build_aggressive_profile(),
        opponent_response_policy_override="lowest_point",
    )

    assert policy_map == {
        "left": "lowest_point",
        "right": "lowest_point",
    }


def test_immediate_policy_map_global_cli_response_overrides_input_side() -> None:
    policy_map = build_immediate_response_policy_map_for_test(
        policy_fields={
            "left_opponent_response_policy": "basic_trick_play",
        },
        opponent_response_policy_override="highest_point",
    )

    assert policy_map == {
        "left": "highest_point",
        "right": "highest_point",
    }


def test_immediate_policy_map_side_cli_response_is_final() -> None:
    policy_map = build_immediate_response_policy_map_for_test(
        opponent_response_policy_override="highest_point",
        left_opponent_response_policy_override="lowest_point",
    )

    assert policy_map == {
        "left": "lowest_point",
        "right": "highest_point",
    }


def test_immediate_policy_map_side_only_cli_response_is_sparse() -> None:
    policy_map = build_immediate_response_policy_map_for_test(
        right_opponent_response_policy_override="highest_point",
    )

    assert policy_map == {
        "right": "highest_point",
    }


def test_build_analysis_result_without_explicit_response_policy_keeps_legacy_immediate_result(
    tmp_path,
    monkeypatch,
) -> None:
    result = build_immediate_response_policy_result(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
    )
    row = get_only_analysis_report_row(result)

    assert row["card"] == "S7"
    assert row["average_trick_points"] == 0.0


def test_build_analysis_result_applies_explicit_global_response_policy_to_both_sides(
    tmp_path,
    monkeypatch,
) -> None:
    result = build_immediate_response_policy_result(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        policy_fields={
            "opponent_response_policy": "highest_point",
        },
    )
    row = get_only_analysis_report_row(result)

    assert row["card"] == "S7"
    assert row["average_trick_points"] == 21.0


def test_build_analysis_result_right_response_policy_overrides_global_response_policy(
    tmp_path,
    monkeypatch,
) -> None:
    result = build_immediate_response_policy_result(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        policy_fields={
            "opponent_response_policy": "highest_point",
            "right_opponent_response_policy": "lowest_point",
        },
    )
    row = get_only_analysis_report_row(result)

    assert row["card"] == "S7"
    assert row["average_trick_points"] == 10.0


def test_build_analysis_result_left_response_policy_overrides_global_response_policy(
    tmp_path,
    monkeypatch,
) -> None:
    result = build_immediate_response_policy_result(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        policy_fields={
            "opponent_response_policy": "highest_point",
            "left_opponent_response_policy": "lowest_point",
        },
    )
    row = get_only_analysis_report_row(result)

    assert row["card"] == "S7"
    assert row["average_trick_points"] == 11.0


def test_build_analysis_result_applies_cli_response_policy_to_immediate_analysis(
    tmp_path,
    monkeypatch,
) -> None:
    result = build_immediate_response_policy_result(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        opponent_response_policy_override="highest_point",
    )
    row = get_only_analysis_report_row(result)

    assert row["card"] == "S7"
    assert row["average_trick_points"] == 21.0


def test_build_analysis_result_applies_cli_preset_to_immediate_analysis(
    tmp_path,
    monkeypatch,
) -> None:
    result = build_immediate_response_policy_result(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        opponent_policy_preset_override="aggressive_points",
    )
    row = get_only_analysis_report_row(result)

    assert row["card"] == "S7"
    assert row["average_trick_points"] == 21.0


def test_build_analysis_result_applies_profile_presets_to_immediate_analysis(
    tmp_path,
    monkeypatch,
) -> None:
    result = build_immediate_response_policy_result(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        policy_fields={
            "right_player_profile": {
                "games_played": 1000,
                "solo_rate": 0.38,
            },
        },
        use_profile_presets_override=True,
    )
    row = get_only_analysis_report_row(result)

    assert row["card"] == "S7"
    assert row["average_trick_points"] == 11.0


def test_build_analysis_result_side_cli_policy_uses_correct_immediate_responder(
    tmp_path,
    monkeypatch,
) -> None:
    from skat_ai.opponent_policy import choose_opponent_response_card_by_policy

    calls = []

    def fake_generate_random_opponent_hands(
        state,
        left_hand_size: int,
        right_hand_size: int,
        random_generator=None,
    ) -> tuple[list[str], list[str]]:
        _ = (state, left_hand_size, right_hand_size, random_generator)
        return ["S9", "SA"], ["S10", "H7"]

    def recording_choose_opponent_response_card_by_policy(
        hand,
        current_trick,
        game_type,
        player_index,
        policy="basic_trick_play",
        random_generator=None,
        partner_currently_winning=False,
    ):
        selected_card = choose_opponent_response_card_by_policy(
            hand=hand,
            current_trick=current_trick,
            game_type=game_type,
            player_index=player_index,
            policy=policy,
            random_generator=random_generator,
            partner_currently_winning=partner_currently_winning,
        )
        calls.append(
            {
                "hand": hand.copy(),
                "policy": policy,
                "selected_card": selected_card,
            }
        )
        return selected_card

    monkeypatch.setattr(
        "skat_ai.simulation.generate_random_opponent_hands",
        fake_generate_random_opponent_hands,
    )
    monkeypatch.setattr(
        "skat_ai.simulation.choose_opponent_response_card_by_policy",
        recording_choose_opponent_response_card_by_policy,
    )

    input_path = tmp_path / "immediate_left_responder_policy.json"
    input_path.write_text(
        json.dumps(
            {
                "game_type": "grand",
                "player_role": "declarer",
                "player_position": "middlehand",
                "trick_leader": "right",
                "hand": ["S8"],
                "current_trick": ["S7"],
                "played_cards": [],
                "completed_tricks": [],
                "declarer_points": 0,
                "defender_points": 0,
                "next_player": "me",
                "skat": [],
                "left_hand_size": 2,
                "right_hand_size": 2,
                "sample_count": 1,
                "random_seed": 1,
                "use_basic_opponent_strategy": True,
                "analysis_mode": "live_decision",
                "skat_visibility": "unknown",
                "game_end_reason": "not_ended",
                "hand_game": False,
                "ouvert": False,
                "schneider_announced": False,
                "schwarz_announced": False,
                "matadors": 1,
            }
        ),
        encoding="utf-8",
    )

    result = build_analysis_result(
        file_path=str(input_path),
        sample_count_override=1,
        random_seed_override=1,
        opponent_strategy_override="basic",
        left_opponent_response_policy_override="highest_point",
    )
    row = get_only_analysis_report_row(result)

    assert row["card"] == "S8"
    assert row["average_trick_points"] == 11.0
    assert calls
    assert all(call["hand"] == ["S9", "SA"] for call in calls)
    assert all(call["policy"] == "highest_point" for call in calls)
    assert all(call["selected_card"] == "SA" for call in calls)


def test_run_json_position_analysis_supports_left_right_policy_overrides() -> None:
    run_json_position_analysis(
        file_path="examples/grand_second_position.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
        output_path=None,
        multi_step_count=None,
        card_selection_policy="highest_expected_value",
        expected_value_sample_count=20,
        strict_context=False,
        compare_policies=False,
        comparison_only=False,
        left_opponent_lead_policy_override="highest_point",
        left_opponent_response_policy_override="basic_trick_play",
        right_opponent_lead_policy_override="lowest_point",
        right_opponent_response_policy_override="highest_point",
    )


def test_run_json_position_analysis_threads_left_right_policies_to_multi_step() -> None:
    run_json_position_analysis(
        file_path="examples/grand_second_position.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
        output_path=None,
        multi_step_count=1,
        card_selection_policy="highest_expected_value",
        expected_value_sample_count=20,
        strict_context=False,
        compare_policies=False,
        comparison_only=False,
        left_opponent_lead_policy_override="highest_point",
        left_opponent_response_policy_override="basic_trick_play",
        right_opponent_lead_policy_override="lowest_point",
        right_opponent_response_policy_override="highest_point",
    )


def test_run_json_position_analysis_writes_left_right_policy_settings_to_output(
    tmp_path,
) -> None:
    import json

    output_path = tmp_path / "result.json"

    run_json_position_analysis(
        file_path="examples/grand_second_position.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
        output_path=str(output_path),
        multi_step_count=1,
        card_selection_policy="highest_expected_value",
        expected_value_sample_count=20,
        strict_context=False,
        compare_policies=False,
        comparison_only=False,
        left_opponent_lead_policy_override="highest_point",
        left_opponent_response_policy_override="basic_trick_play",
        right_opponent_lead_policy_override="lowest_point",
        right_opponent_response_policy_override="highest_point",
    )

    with output_path.open("r", encoding="utf-8") as file:
        result = json.load(file)

    assert result["left_opponent_policy_settings"] == {
        "opponent_lead_policy": "highest_point",
        "opponent_response_policy": "basic_trick_play",
    }
    assert result["right_opponent_policy_settings"] == {
        "opponent_lead_policy": "lowest_point",
        "opponent_response_policy": "highest_point",
    }


def test_run_json_position_analysis_accepts_random_left_right_policy_overrides() -> None:
    run_json_position_analysis(
        file_path="examples/grand_second_position.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
        output_path=None,
        multi_step_count=1,
        card_selection_policy="highest_expected_value",
        expected_value_sample_count=20,
        strict_context=False,
        compare_policies=False,
        comparison_only=False,
        left_opponent_lead_policy_override="random_legal",
        left_opponent_response_policy_override="random_legal",
        right_opponent_lead_policy_override="random_legal",
        right_opponent_response_policy_override="random_legal",
    )


def test_run_json_position_analysis_writes_updated_policy_settings_to_output(
    tmp_path,
) -> None:
    output_path = tmp_path / "result.json"

    run_json_position_analysis(
        file_path="examples/grand_second_position.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
        output_path=str(output_path),
        multi_step_count=1,
        card_selection_policy="highest_expected_value",
        expected_value_sample_count=20,
        strict_context=False,
        compare_policies=False,
        comparison_only=False,
        opponent_lead_policy_override="highest_point",
        opponent_response_policy_override="basic_trick_play",
        left_opponent_lead_policy_override="lowest_point",
        left_opponent_response_policy_override="basic_defender_response",
        right_opponent_lead_policy_override="basic_defender_lead",
        right_opponent_response_policy_override="highest_point",
    )

    with output_path.open("r", encoding="utf-8") as file:
        result = json.load(file)

    assert result["opponent_policy_settings"] == {
        "opponent_lead_policy": "highest_point",
        "opponent_response_policy": "basic_trick_play",
    }
    assert result["left_opponent_policy_settings"] == {
        "opponent_lead_policy": "lowest_point",
        "opponent_response_policy": "basic_defender_response",
    }
    assert result["right_opponent_policy_settings"] == {
        "opponent_lead_policy": "basic_defender_lead",
        "opponent_response_policy": "highest_point",
    }
    assert result["multi_step_result"]["opponent_policy_settings"] == {
        "opponent_lead_policy": "highest_point",
        "opponent_response_policy": "basic_trick_play",
    }
    assert result["multi_step_result"]["left_opponent_policy_settings"] == {
        "opponent_lead_policy": "lowest_point",
        "opponent_response_policy": "basic_defender_response",
    }
    assert result["multi_step_result"]["right_opponent_policy_settings"] == {
        "opponent_lead_policy": "basic_defender_lead",
        "opponent_response_policy": "highest_point",
    }


def test_run_json_position_analysis_applies_profile_presets_to_left_right_output(
    tmp_path,
) -> None:
    output_path = tmp_path / "result.json"

    run_json_position_analysis(
        file_path="examples/grand_midgame_profile_preset_live.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
        output_path=str(output_path),
        multi_step_count=1,
        card_selection_policy="highest_point",
        expected_value_sample_count=20,
        strict_context=False,
        compare_policies=False,
        comparison_only=False,
    )

    with output_path.open("r", encoding="utf-8") as file:
        result = json.load(file)

    assert result["profile_preset_settings"] == {
        "use_profile_presets": True,
    }
    assert result["left_opponent_policy_settings"] == {
        "opponent_lead_policy": "basic_defender_lead",
        "opponent_response_policy": "basic_defender_response",
    }
    assert result["right_opponent_policy_settings"] == {
        "opponent_lead_policy": "highest_point",
        "opponent_response_policy": "highest_point",
    }
    assert result["multi_step_result"]["left_opponent_policy_settings"] == {
        "opponent_lead_policy": "basic_defender_lead",
        "opponent_response_policy": "basic_defender_response",
    }
    assert result["multi_step_result"]["right_opponent_policy_settings"] == {
        "opponent_lead_policy": "highest_point",
        "opponent_response_policy": "highest_point",
    }


def test_run_json_position_analysis_keeps_left_right_cli_overrides_final(
    tmp_path,
) -> None:
    output_path = tmp_path / "result.json"

    run_json_position_analysis(
        file_path="examples/grand_midgame_profile_preset_live.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
        output_path=str(output_path),
        multi_step_count=1,
        card_selection_policy="highest_point",
        expected_value_sample_count=20,
        strict_context=False,
        compare_policies=False,
        comparison_only=False,
        left_opponent_lead_policy_override="lowest_point",
        left_opponent_response_policy_override="lowest_point",
        right_opponent_lead_policy_override="basic_defender_lead",
        right_opponent_response_policy_override="basic_defender_response",
    )

    with output_path.open("r", encoding="utf-8") as file:
        result = json.load(file)

    assert result["left_opponent_policy_settings"] == {
        "opponent_lead_policy": "lowest_point",
        "opponent_response_policy": "lowest_point",
    }
    assert result["right_opponent_policy_settings"] == {
        "opponent_lead_policy": "basic_defender_lead",
        "opponent_response_policy": "basic_defender_response",
    }
    assert result["multi_step_result"]["left_opponent_policy_settings"] == {
        "opponent_lead_policy": "lowest_point",
        "opponent_response_policy": "lowest_point",
    }
    assert result["multi_step_result"]["right_opponent_policy_settings"] == {
        "opponent_lead_policy": "basic_defender_lead",
        "opponent_response_policy": "basic_defender_response",
    }


def write_position_file(tmp_path, data: dict[str, object]) -> str:
    input_path = tmp_path / "position.json"
    input_path.write_text(json.dumps(data), encoding="utf-8")
    return str(input_path)


def build_completed_null_defender_tricks() -> list[dict[str, object]]:
    return [
        {"cards": ["CA", "C10", "CK"], "winner_role": "defenders"},
        {"cards": ["CQ", "CJ", "C9"], "winner_role": "defenders"},
        {"cards": ["C8", "C7", "SA"], "winner_role": "defenders"},
        {"cards": ["S10", "SK", "SQ"], "winner_role": "defenders"},
        {"cards": ["SJ", "S9", "S8"], "winner_role": "defenders"},
        {"cards": ["S7", "HA", "H10"], "winner_role": "defenders"},
        {"cards": ["HK", "HQ", "HJ"], "winner_role": "defenders"},
        {"cards": ["H9", "H8", "H7"], "winner_role": "defenders"},
        {"cards": ["DA", "D10", "DK"], "winner_role": "defenders"},
        {"cards": ["DQ", "DJ", "D9"], "winner_role": "defenders"},
    ]


def build_stub_analysis_report() -> list[dict[str, object]]:
    return [
        {
            "card": "D8",
            "win_rate": 0.0,
            "average_trick_points": 0.0,
            "average_points_won": 0.0,
            "average_points_lost": 0.0,
            "expected_point_swing": 0.0,
            "is_recommended": True,
        }
    ]


def build_post_game_position_input() -> dict[str, object]:
    return {
        "game_type": "spades",
        "player_role": "declarer",
        "player_position": "middlehand",
        "trick_leader": "left",
        "hand": ["C7", "SA", "S7"],
        "current_trick": ["CA"],
        "played_cards": [],
        "completed_tricks": [],
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "me",
        "skat": [],
        "left_hand_size": 10,
        "right_hand_size": 10,
        "sample_count": 10,
        "random_seed": 1,
        "use_basic_opponent_strategy": True,
        "analysis_mode": "post_game_review",
        "skat_visibility": "known_post_game",
    }


def test_build_analysis_result_includes_unavailable_post_game_review_summary(
    tmp_path,
) -> None:
    data = build_post_game_position_input()
    input_path = write_position_file(tmp_path, data)

    result = build_analysis_result(input_path)

    assert "post_game_review_summary" in result
    assert result["post_game_review_summary"]["is_available"] is False
    assert (
        result["post_game_review_summary"]["reason"]
        == "actual_card_played_not_provided"
    )
    assert result["post_game_review_summary"]["actual_card_played"] is None
    assert (
        result["post_game_review_summary"]["decision_quality"]
        == "not_available"
    )


def test_build_analysis_result_uses_completed_null_ownership(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "main.recommend_card_by_expected_value",
        lambda **_kwargs: ("D8", "Stubbed recommendation.", {}),
    )
    monkeypatch.setattr(
        "main.build_card_analysis_report",
        lambda **_kwargs: build_stub_analysis_report(),
    )
    data = {
        "game_type": "null",
        "player_role": "declarer",
        "player_position": "forehand",
        "trick_leader": "me",
        "hand": ["D8", "D7"],
        "current_trick": [],
        "played_cards": [],
        "completed_tricks": build_completed_null_defender_tricks(),
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "me",
        "skat": [],
        "left_hand_size": 1,
        "right_hand_size": 1,
        "sample_count": 1,
        "random_seed": 1,
        "use_basic_opponent_strategy": True,
        "analysis_mode": "post_game_review",
        "skat_visibility": "unknown",
        "game_end_reason": "normal_completion",
        "hand_game": False,
        "ouvert": False,
        "bid_value": 23,
        "performance_rating_system": "isko_list",
    }
    input_path = write_position_file(tmp_path, data)

    result = build_analysis_result(input_path)

    assert result["score_summary"]["total_declarer_points"] == 0
    assert result["score_summary"]["total_defender_points"] == 120

    assert result["game_result_summary"]["is_complete"] is True
    assert result["game_result_summary"]["winner"] == "declarer"
    assert result["adjusted_game_result_summary"]["is_complete"] is True
    assert result["adjusted_game_result_summary"]["winner"] == "declarer"
    assert result["adjusted_game_result_summary"]["game_end_reason"] == (
        "normal_completion"
    )

    assert result["final_settlement_summary"]["is_complete"] is True
    assert result["final_settlement_summary"]["winner"] == "declarer"
    assert result["final_settlement_summary"]["declarer_won_by_card_points"] is True
    assert result["final_settlement_summary"]["game_value"] == 23
    assert result["final_settlement_summary"]["effective_game_value"] == 23
    assert result["final_settlement_summary"]["settlement_score"] == 23
    assert result["final_settlement_summary"]["is_loss"] is False

    assert result["performance_rating_summary"]["game_outcome"] == "declarer_win"
    assert result["performance_rating_summary"]["settlement_score"] == 23
    assert result["performance_rating_summary"]["rating_score"] == 73


def test_build_analysis_result_includes_available_post_game_review_summary(
    tmp_path,
) -> None:
    data = build_post_game_position_input()
    data["actual_card_played"] = "C7"
    input_path = write_position_file(tmp_path, data)

    result = build_analysis_result(input_path)
    summary = result["post_game_review_summary"]

    assert summary["is_available"] is True
    assert summary["reason"] == "actual_card_played_provided"
    assert summary["actual_card_played"] == "C7"
    assert summary["recommended_card"] is not None
    assert isinstance(summary["actual_expected_point_swing"], float)
    assert isinstance(summary["recommended_expected_point_swing"], float)
    assert isinstance(summary["expected_point_swing_difference"], float)
    assert summary["decision_quality"] in {
        "optimal",
        "acceptable",
        "suboptimal",
        "mistake",
    }


def test_run_json_position_analysis_prints_available_post_game_review_summary(
    capsys,
) -> None:
    run_json_position_analysis(
        file_path="examples/spades_post_game_actual_card_played.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
        output_path=None,
        multi_step_count=None,
        card_selection_policy="highest_expected_value",
        expected_value_sample_count=20,
        strict_context=False,
        compare_policies=False,
        comparison_only=False,
    )

    captured = capsys.readouterr()

    assert "Post-game review summary" in captured.out
    assert "Actual card played: C7" in captured.out
    assert "Recommended card: C7" in captured.out
    assert "Actual expected point swing:" in captured.out
    assert "Recommended expected point swing:" in captured.out
    assert "Expected point swing difference:" in captured.out
    assert "Decision quality: optimal" in captured.out
    assert "Decision factors: no_missed_expected_point_swing" in captured.out
    assert (
        "Decision explanation: The actual card matches the recommended card "
        "or has no missed expected point swing."
    ) in captured.out
    assert "Actual card rank: 1" in captured.out
    assert "Recommended card rank: 1" in captured.out
    assert "Candidate count: 1" in captured.out
    assert "Better card count: 0" in captured.out


def test_run_json_position_analysis_prints_unavailable_post_game_review_summary(
    capsys,
) -> None:
    run_json_position_analysis(
        file_path="examples/grand_leading.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
        output_path=None,
        multi_step_count=None,
        card_selection_policy="highest_expected_value",
        expected_value_sample_count=20,
        strict_context=False,
        compare_policies=False,
        comparison_only=False,
    )

    captured = capsys.readouterr()

    assert "Post-game review summary" in captured.out
    assert "Not available: actual_card_played_not_provided" in captured.out
    assert "Decision factors: actual_card_played_not_provided" in captured.out
    assert (
        "Decision explanation: No post-game review decision quality is available "
        "because actual_card_played was not provided."
    ) in captured.out
    assert "Actual card rank: not available" in captured.out
    assert "Recommended card rank: 1" in captured.out
    assert "Candidate count:" in captured.out
    assert "Better card count: not available" in captured.out


def test_build_analysis_result_infers_missing_matadors_from_known_declarer_cards(
    tmp_path,
) -> None:
    data = {
        "game_type": "grand",
        "player_role": "declarer",
        "player_position": "middlehand",
        "trick_leader": "me",
        "hand": ["CJ", "SJ", "HJ", "D7"],
        "current_trick": [],
        "played_cards": [],
        "completed_tricks": [],
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "me",
        "skat": ["C7", "D8"],
        "left_hand_size": 10,
        "right_hand_size": 10,
        "sample_count": 10,
        "random_seed": 1,
        "use_basic_opponent_strategy": True,
        "analysis_mode": "post_game_review",
        "skat_visibility": "known_post_game",
        "game_declaration": {
            "hand_game": False,
            "ouvert": False,
            "schneider_announced": False,
            "schwarz_announced": False
        },
    }
    input_path = write_position_file(tmp_path, data)

    result = build_analysis_result(input_path)

    assert result["game_declaration"]["matadors"] == 3
    assert result["game_value_summary"]["details"]["matadors"] == 3
    assert result["game_value_summary"]["game_level"] == 4
    assert result["game_value_summary"]["game_value"] == 96


def test_build_analysis_result_uses_completed_trick_ownership_for_matadors(
    tmp_path,
) -> None:
    data = {
        "game_type": "grand",
        "player_role": "declarer",
        "player_position": "middlehand",
        "trick_leader": "me",
        "hand": ["CJ", "D7", "D8", "D9"],
        "current_trick": [],
        "played_cards": [],
        "completed_tricks": [
            {
                "cards": ["SJ", "H7", "HJ"],
                "players": ["me", "left", "right"],
                "winner_role": "declarer",
                "winner_player": "me",
            }
        ],
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "me",
        "skat": ["C7", "C8"],
        "left_hand_size": 9,
        "right_hand_size": 9,
        "sample_count": 10,
        "random_seed": 1,
        "use_basic_opponent_strategy": True,
        "analysis_mode": "post_game_review",
        "skat_visibility": "known_post_game",
        "game_declaration": {
            "hand_game": False,
            "ouvert": False,
            "schneider_announced": False,
            "schwarz_announced": False,
        },
    }
    input_path = write_position_file(tmp_path, data)

    result = build_analysis_result(input_path)

    assert result["game_declaration"]["matadors"] == 2
    assert result["game_value_summary"]["details"]["matadors"] == 2
    assert result["game_value_summary"]["details"]["matador_multiplier"] == 3
    assert result["game_value_summary"]["game_level"] == 3
    assert result["game_value_summary"]["game_value"] == 72
    assert result["game_value_summary"]["details"]["is_complete"] is True


def test_build_analysis_result_keeps_explicit_matadors_over_inference(
    tmp_path,
) -> None:
    data = {
        "game_type": "grand",
        "player_role": "declarer",
        "player_position": "middlehand",
        "trick_leader": "me",
        "hand": ["CJ", "SJ", "HJ", "D7"],
        "current_trick": [],
        "played_cards": [],
        "completed_tricks": [],
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "me",
        "skat": ["C7", "D8"],
        "left_hand_size": 10,
        "right_hand_size": 10,
        "sample_count": 10,
        "random_seed": 1,
        "use_basic_opponent_strategy": True,
        "analysis_mode": "post_game_review",
        "skat_visibility": "known_post_game",
        "game_declaration": {
            "hand_game": False,
            "ouvert": False,
            "schneider_announced": False,
            "schwarz_announced": False,
            "matadors": 1
        },
    }
    input_path = write_position_file(tmp_path, data)

    result = build_analysis_result(input_path)

    assert result["game_declaration"]["matadors"] == 1
    assert result["game_value_summary"]["details"]["matadors"] == 1
    assert result["game_value_summary"]["game_level"] == 2
    assert result["game_value_summary"]["game_value"] == 48


def test_build_analysis_result_uses_inferred_matadors_for_final_settlement(
    tmp_path,
) -> None:
    data = {
        "game_type": "grand",
        "player_role": "declarer",
        "player_position": "middlehand",
        "trick_leader": "me",
        "hand": ["CJ", "SJ", "HJ", "D7"],
        "current_trick": [],
        "played_cards": [],
        "completed_tricks": [
            {
                "cards": ["CA", "C10", "CK"],
                "winner_role": "declarer",
            },
            {
                "cards": ["SA", "S10", "SK"],
                "winner_role": "declarer",
            },
            {
                "cards": ["HA", "H10", "HK"],
                "winner_role": "defenders",
            },
            {
                "cards": ["DA", "D10", "DK"],
                "winner_role": "defenders",
            },
        ],
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "me",
        "skat": ["C7", "D8"],
        "left_hand_size": 6,
        "right_hand_size": 6,
        "sample_count": 10,
        "random_seed": 1,
        "use_basic_opponent_strategy": True,
        "analysis_mode": "post_game_review",
        "skat_visibility": "known_post_game",
        "game_end_reason": "defenders_conceded_remaining_tricks",
        "game_declaration": {
            "hand_game": False,
            "ouvert": False,
            "schneider_announced": False,
            "schwarz_announced": False,
        },
    }
    input_path = write_position_file(tmp_path, data)

    result = build_analysis_result(input_path)

    assert result["game_declaration"]["matadors"] == 3
    assert result["game_value_summary"]["details"]["matadors"] == 3
    assert result["game_value_summary"]["game_level"] == 4
    assert result["game_value_summary"]["game_value"] == 96

    assert result["adjusted_game_result_summary"]["is_complete"] is True
    assert result["adjusted_game_result_summary"]["winner"] == "declarer"

    assert result["final_settlement_summary"]["is_complete"] is True
    assert result["final_settlement_summary"]["winner"] == "declarer"
    assert result["final_settlement_summary"]["game_value"] == 96
    assert result["final_settlement_summary"]["settlement_score"] == 96
