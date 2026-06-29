from skat_ai.game_state import GameState
from skat_ai.policy_comparison import (
    build_policy_recommendation,
    compare_multi_step_policies,
    find_best_policy_by_final_point_swing,
    find_best_policy_by_local_point_swing,
    sort_policy_results_by_final_point_swing,
    sort_policy_results_by_local_point_swing,
)
from skat_ai.strategic_metadata import StrategicMetadata


def test_compare_multi_step_policies_returns_expected_keys() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9"],
        current_trick=["S7"],
        next_player="me",
    )

    result = compare_multi_step_policies(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        step_count=1,
        policies=["first_legal", "lowest_point"],
        random_seed=42,
        use_basic_opponent_strategy=True,
        expected_value_sample_count=20,
        strict_context=False,
    )

    assert set(result.keys()) == {
        "requested_step_count",
        "random_seed",
        "expected_value_sample_count",
        "use_basic_opponent_strategy",
        "strict_context",
        "policies",
        "policy_results",
        "recommended_policy",
        "opponent_lead_policy",
        "opponent_response_policy",
    }


def test_compare_multi_step_policies_runs_selected_policies() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9"],
        current_trick=["S7"],
        next_player="me",
    )

    result = compare_multi_step_policies(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        step_count=1,
        policies=["first_legal", "lowest_point"],
        random_seed=42,
        use_basic_opponent_strategy=True,
        expected_value_sample_count=20,
        strict_context=False,
    )

    assert result["policies"] == ["first_legal", "lowest_point"]
    assert len(result["policy_results"]) == 2
    assert {
        policy_result["policy"]
        for policy_result in result["policy_results"]
    } == {
        "first_legal",
        "lowest_point",
    }


def test_compare_multi_step_policies_policy_result_contains_score_fields() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9"],
        current_trick=["S7"],
        next_player="me",
    )

    result = compare_multi_step_policies(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        step_count=1,
        policies=["highest_point"],
        random_seed=42,
        use_basic_opponent_strategy=True,
        expected_value_sample_count=20,
        strict_context=False,
    )

    policy_result = result["policy_results"][0]

    assert "declarer_points_gained" in policy_result
    assert "defender_points_gained" in policy_result
    assert "final_point_swing" in policy_result
    assert "local_point_swing" in policy_result
    assert "steps_simulated" in policy_result
    assert "stop_reason" in policy_result


def test_find_best_policy_by_final_point_swing() -> None:
    comparison_result = {
        "policy_results": [
            {
                "policy": "lowest_point",
                "final_point_swing": -3,
                "declarer_points_gained": 4,
                "defender_points_gained": 7,
                "steps_simulated": 1,
            },
            {
                "policy": "highest_point",
                "final_point_swing": 12,
                "declarer_points_gained": 14,
                "defender_points_gained": 2,
                "steps_simulated": 1,
            },
            {
                "policy": "first_legal",
                "final_point_swing": 4,
                "declarer_points_gained": 8,
                "defender_points_gained": 4,
                "steps_simulated": 1,
            },
        ]
    }

    best_policy = find_best_policy_by_final_point_swing(comparison_result)

    assert best_policy["policy"] == "highest_point"
    assert best_policy["final_point_swing"] == 12


def test_find_best_policy_by_local_point_swing() -> None:
    comparison_result = {
        "policy_results": [
            {
                "policy": "good_for_declarer",
                "final_point_swing": 12,
                "local_point_swing": -12,
                "declarer_points_gained": 14,
                "defender_points_gained": 2,
                "steps_simulated": 1,
            },
            {
                "policy": "good_for_defenders",
                "final_point_swing": -3,
                "local_point_swing": 3,
                "declarer_points_gained": 4,
                "defender_points_gained": 7,
                "steps_simulated": 1,
            },
        ]
    }

    best_policy = find_best_policy_by_local_point_swing(comparison_result)

    assert best_policy["policy"] == "good_for_defenders"


def test_find_best_policy_by_final_point_swing_uses_tie_breakers() -> None:
    comparison_result = {
        "policy_results": [
            {
                "policy": "lower_defender_gain",
                "final_point_swing": 10,
                "declarer_points_gained": 12,
                "defender_points_gained": 1,
                "steps_simulated": 1,
            },
            {
                "policy": "higher_declarer_gain",
                "final_point_swing": 10,
                "declarer_points_gained": 13,
                "defender_points_gained": 3,
                "steps_simulated": 1,
            },
        ]
    }

    best_policy = find_best_policy_by_final_point_swing(comparison_result)

    assert best_policy["policy"] == "higher_declarer_gain"

def test_find_best_policy_by_final_point_swing_rejects_empty_results() -> None:
    comparison_result = {
        "policy_results": [],
    }

    try:
        find_best_policy_by_final_point_swing(comparison_result)
    except ValueError as error:
        assert "No policy results available" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")

def test_sort_policy_results_by_final_point_swing() -> None:
    policy_results = [
        {
            "policy": "lowest_point",
            "final_point_swing": -3,
            "declarer_points_gained": 4,
            "defender_points_gained": 7,
            "steps_simulated": 1,
        },
        {
            "policy": "highest_point",
            "final_point_swing": 12,
            "declarer_points_gained": 14,
            "defender_points_gained": 2,
            "steps_simulated": 1,
        },
        {
            "policy": "first_legal",
            "final_point_swing": 4,
            "declarer_points_gained": 8,
            "defender_points_gained": 4,
            "steps_simulated": 1,
        },
    ]

    sorted_results = sort_policy_results_by_final_point_swing(policy_results)

    assert [result["policy"] for result in sorted_results] == [
        "highest_point",
        "first_legal",
        "lowest_point",
    ]


def test_sort_policy_results_by_local_point_swing() -> None:
    policy_results = [
        {
            "policy": "good_for_declarer",
            "final_point_swing": 12,
            "local_point_swing": -12,
            "declarer_points_gained": 14,
            "defender_points_gained": 2,
            "steps_simulated": 1,
        },
        {
            "policy": "good_for_defenders",
            "final_point_swing": -3,
            "local_point_swing": 3,
            "declarer_points_gained": 4,
            "defender_points_gained": 7,
            "steps_simulated": 1,
        },
    ]

    sorted_results = sort_policy_results_by_local_point_swing(policy_results)

    assert [result["policy"] for result in sorted_results] == [
        "good_for_defenders",
        "good_for_declarer",
    ]


def test_sort_policy_results_uses_tie_breakers() -> None:
    policy_results = [
        {
            "policy": "z_policy",
            "final_point_swing": 10,
            "declarer_points_gained": 12,
            "defender_points_gained": 2,
            "steps_simulated": 1,
        },
        {
            "policy": "a_policy",
            "final_point_swing": 10,
            "declarer_points_gained": 12,
            "defender_points_gained": 2,
            "steps_simulated": 1,
        },
        {
            "policy": "more_steps",
            "final_point_swing": 10,
            "declarer_points_gained": 12,
            "defender_points_gained": 2,
            "steps_simulated": 2,
        },
        {
            "policy": "lower_defender_gain",
            "final_point_swing": 10,
            "declarer_points_gained": 12,
            "defender_points_gained": 1,
            "steps_simulated": 1,
        },
        {
            "policy": "higher_declarer_gain",
            "final_point_swing": 10,
            "declarer_points_gained": 13,
            "defender_points_gained": 3,
            "steps_simulated": 1,
        },
        {
            "policy": "higher_swing",
            "final_point_swing": 11,
            "declarer_points_gained": 0,
            "defender_points_gained": 0,
            "steps_simulated": 1,
        },
    ]

    sorted_results = sort_policy_results_by_final_point_swing(policy_results)

    assert [result["policy"] for result in sorted_results] == [
        "higher_swing",
        "higher_declarer_gain",
        "lower_defender_gain",
        "more_steps",
        "a_policy",
        "z_policy",
    ]

def test_compare_multi_step_policies_returns_sorted_policy_results() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9"],
        current_trick=["S7"],
        next_player="me",
    )

    result = compare_multi_step_policies(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        step_count=1,
        policies=["first_legal", "lowest_point", "highest_point"],
        random_seed=42,
        use_basic_opponent_strategy=True,
        expected_value_sample_count=20,
        strict_context=False,
    )

    swings = [
        policy_result["final_point_swing"]
        for policy_result in result["policy_results"]
    ]

    assert swings == sorted(swings, reverse=True)


def test_build_policy_recommendation() -> None:
    comparison_result = {
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
                "local_point_swing": -6,
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
                "local_point_swing": 12,
                "context_summary": {},
            },
        ]
    }

    recommendation = build_policy_recommendation(comparison_result)

    assert recommendation == {
        "policy": "highest_point",
        "reason": "Best final point swing after tie-breakers.",
        "final_point_swing": 12,
        "local_point_swing": 12,
        "declarer_points_gained": 14,
        "defender_points_gained": 2,
        "steps_simulated": 1,
        "stop_reason": "Requested step count reached.",
    }


def test_compare_multi_step_policies_returns_recommended_policy() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9"],
        current_trick=["S7"],
        next_player="me",
    )

    result = compare_multi_step_policies(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        step_count=1,
        policies=["first_legal", "lowest_point"],
        random_seed=42,
        use_basic_opponent_strategy=True,
        expected_value_sample_count=20,
        strict_context=False,
    )

    assert "recommended_policy" in result
    assert result["recommended_policy"]["policy"] in ["first_legal", "lowest_point"]
    assert result["recommended_policy"]["reason"] == (
        "Best final point swing after tie-breakers."
    )

def test_compare_multi_step_policies_accepts_strategic_metadata() -> None:
    metadata = StrategicMetadata(
        analysis_mode="post_game_review",
        skat_visibility="known_post_game",
        game_end_reason="normal_completion",
    )
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9"],
        current_trick=["S7"],
        next_player="me",
    )

    result = compare_multi_step_policies(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        step_count=1,
        policies=["highest_point"],
        random_seed=42,
        use_basic_opponent_strategy=True,
        expected_value_sample_count=20,
        strict_context=False,
        strategic_metadata=metadata,
    )

    context_summary = result["policy_results"][0]["context_summary"]

    assert context_summary["strategic_metadata"] == {
        "analysis_mode": "post_game_review",
        "skat_visibility": "known_post_game",
        "game_end_reason": "normal_completion",
    }

def test_compare_multi_step_policies_returns_opponent_policy_settings() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9"],
        current_trick=[],
        next_player="left",
    )

    result = compare_multi_step_policies(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        step_count=1,
        policies=["highest_point"],
        random_seed=42,
        opponent_lead_policy="highest_point",
        opponent_response_policy="basic_trick_play",
    )

    assert result["opponent_lead_policy"] == "highest_point"
    assert result["opponent_response_policy"] == "basic_trick_play"


def test_compare_multi_step_policies_threads_response_policy_map(monkeypatch) -> None:
    calls = []

    def fake_simulate_multiple_steps(**kwargs):
        calls.append(kwargs.copy())

        return {
            "summary": {
                "requested_step_count": kwargs["step_count"],
                "steps_simulated": 1,
                "stop_reason": "Requested step count reached.",
                "strict_context": kwargs["strict_context"],
                "score_summary": {
                    "declarer_points_gained": 0,
                    "defender_points_gained": 0,
                    "final_point_swing": 0,
                },
                "context_summary": {},
            }
        }

    monkeypatch.setattr(
        "skat_ai.policy_comparison.simulate_multiple_steps",
        fake_simulate_multiple_steps,
    )
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA"],
        current_trick=[],
        next_player="me",
    )

    result = compare_multi_step_policies(
        state=state,
        left_hand_size=1,
        right_hand_size=1,
        step_count=1,
        policies=["first_legal", "highest_point"],
        random_seed=42,
        opponent_response_policy_by_player={"left": "highest_point"},
    )

    assert result["policies"] == ["first_legal", "highest_point"]
    assert [call["card_selection_policy"] for call in calls] == [
        "first_legal",
        "highest_point",
    ]
    assert all(
        call["opponent_response_policy_by_player"] == {"left": "highest_point"}
        for call in calls
    )
