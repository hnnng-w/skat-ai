from main import (
    apply_cli_overrides,
    build_analysis_result,
    build_serializable_policy_comparison_result,
    print_multi_step_result,
    print_policy_comparison_result,
    run_json_position_analysis,
)


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
        "legal_cards",
        "analysis_report",
        "strategic_summary",
        "score_summary",
        "recommendation",
    }


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


def test_build_serializable_policy_comparison_result() -> None:
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
                "context_summary": {
                    "simulated_opponent_card_count": 2,
                    "unique_simulated_opponent_card_count": 2,
                    "duplicate_simulated_opponent_cards": [],
                    "event_count": 1,
                },
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
                "context_summary": {
                    "simulated_opponent_card_count": 2,
                    "unique_simulated_opponent_card_count": 2,
                    "duplicate_simulated_opponent_cards": [],
                    "event_count": 1,
                },
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

    serializable_result = build_serializable_policy_comparison_result(result)

    assert serializable_result == result


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