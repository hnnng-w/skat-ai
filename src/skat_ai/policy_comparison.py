from typing import Any

from skat_ai.card_selection import VALID_CARD_SELECTION_POLICIES
from skat_ai.game_state import GameState
from skat_ai.multi_step_simulation import simulate_multiple_steps


def compare_multi_step_policies(
    state: GameState,
    left_hand_size: int,
    right_hand_size: int,
    step_count: int,
    policies: list[str] | None = None,
    random_seed: int | None = None,
    use_basic_opponent_strategy: bool = True,
    expected_value_sample_count: int = 100,
    strict_context: bool = False,
) -> dict[str, Any]:
    """
    Compares multiple card-selection policies on the same multi-step setup.
    """
    selected_policies = policies or VALID_CARD_SELECTION_POLICIES

    policy_results = []

    for policy in selected_policies:
        multi_step_result = simulate_multiple_steps(
            state=state,
            left_hand_size=left_hand_size,
            right_hand_size=right_hand_size,
            step_count=step_count,
            random_seed=random_seed,
            use_basic_opponent_strategy=use_basic_opponent_strategy,
            card_selection_policy=policy,
            expected_value_sample_count=expected_value_sample_count,
            strict_context=strict_context,
        )

        summary = multi_step_result["summary"]
        score_summary = summary["score_summary"]

        policy_results.append(
            {
                "policy": policy,
                "requested_step_count": summary["requested_step_count"],
                "steps_simulated": summary["steps_simulated"],
                "stop_reason": summary["stop_reason"],
                "strict_context": summary["strict_context"],
                "declarer_points_gained": score_summary["declarer_points_gained"],
                "defender_points_gained": score_summary["defender_points_gained"],
                "final_point_swing": score_summary["final_point_swing"],
                "context_summary": summary["context_summary"],
            }
        )

    sorted_policy_results = sort_policy_results_by_final_point_swing(policy_results)

    return {
        "requested_step_count": step_count,
        "random_seed": random_seed,
        "expected_value_sample_count": expected_value_sample_count,
        "use_basic_opponent_strategy": use_basic_opponent_strategy,
        "strict_context": strict_context,
        "policies": selected_policies,
        "policy_results": sorted_policy_results,
    }


def find_best_policy_by_final_point_swing(
    comparison_result: dict[str, Any],
) -> dict[str, Any]:
    """
    Returns the policy result with the highest final point swing.
    """
    policy_results = comparison_result["policy_results"]

    if not policy_results:
        raise ValueError("No policy results available.")

    return max(
        policy_results,
        key=lambda result: result["final_point_swing"],
    )

def sort_policy_results_by_final_point_swing(
    policy_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Sorts policy results by final point swing, best first.
    """
    return sorted(
        policy_results,
        key=lambda result: result["final_point_swing"],
        reverse=True,
    )