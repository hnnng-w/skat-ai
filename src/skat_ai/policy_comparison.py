from typing import Any

from skat_ai.card_selection import VALID_CARD_SELECTION_POLICIES
from skat_ai.game_state import GameState
from skat_ai.multi_step_simulation import simulate_multiple_steps
from skat_ai.objective_utility import calculate_null_horizon_utility_from_states
from skat_ai.strategic_metadata import StrategicMetadata


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
    strategic_metadata: StrategicMetadata | None = None,
    opponent_lead_policy: str = "lowest_point",
    opponent_response_policy: str = "lowest_point",
    left_opponent_policy_settings: dict[str, str] | None = None,
    right_opponent_policy_settings: dict[str, str] | None = None,
    opponent_response_policy_by_player: dict[str, str] | None = None,
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
            strategic_metadata=strategic_metadata,
            opponent_lead_policy=opponent_lead_policy,
            opponent_response_policy=opponent_response_policy,
            left_opponent_policy_settings=left_opponent_policy_settings,
            right_opponent_policy_settings=right_opponent_policy_settings,
            opponent_response_policy_by_player=opponent_response_policy_by_player,
        )

        summary = multi_step_result["summary"]
        score_summary = summary["score_summary"]

        policy_result = {
            "policy": policy,
            "requested_step_count": summary["requested_step_count"],
            "steps_simulated": summary["steps_simulated"],
            "stop_reason": summary["stop_reason"],
            "strict_context": summary["strict_context"],
            "declarer_points_gained": score_summary["declarer_points_gained"],
            "defender_points_gained": score_summary["defender_points_gained"],
            "final_point_swing": score_summary["final_point_swing"],
            "local_point_swing": score_summary.get(
                "local_point_swing",
                score_summary["final_point_swing"],
            ),
            "context_summary": summary["context_summary"],
        }

        if state.game_type == "null":
            policy_result["_objective_utility"] = calculate_null_horizon_utility_from_states(
                player_role=state.player_role,
                initial_completed_tricks=state.completed_tricks,
                final_completed_tricks=multi_step_result["final_state"].completed_tricks,
            )

        policy_results.append(policy_result)

    sorted_policy_results = sort_policy_results_by_local_point_swing(policy_results)

    comparison_result = {
        "requested_step_count": step_count,
        "random_seed": random_seed,
        "expected_value_sample_count": expected_value_sample_count,
        "use_basic_opponent_strategy": use_basic_opponent_strategy,
        "strict_context": strict_context,
        "opponent_lead_policy": opponent_lead_policy,
        "opponent_response_policy": opponent_response_policy,
        "policies": selected_policies,
        "policy_results": sorted_policy_results,
    }

    comparison_result["recommended_policy"] = build_policy_recommendation(comparison_result)

    return comparison_result


def find_best_policy_by_final_point_swing(
    comparison_result: dict[str, Any],
) -> dict[str, Any]:
    """
    Returns the best policy result using local-perspective ordering.
    """
    return find_best_policy_by_local_point_swing(comparison_result)


def find_best_policy_by_local_point_swing(
    comparison_result: dict[str, Any],
) -> dict[str, Any]:
    """
    Returns the best policy result using the same ordering as the comparison table.
    """
    policy_results = comparison_result["policy_results"]

    if not policy_results:
        raise ValueError("No policy results available.")

    return sort_policy_results_by_local_point_swing(policy_results)[0]


def sort_policy_results_by_final_point_swing(
    policy_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Sorts policy results by local-perspective quality, best first.
    """
    return sort_policy_results_by_local_point_swing(policy_results)


def sort_policy_results_by_local_point_swing(
    policy_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Sorts policy results by local-perspective quality, best first.

    Tie-breakers:
    1. Higher local point swing
    2. Higher final point swing
    3. Higher declarer points gained
    4. Lower defender points gained
    5. Higher number of simulated steps
    6. Policy name alphabetically
    """
    def build_sort_key(result: dict[str, Any]) -> tuple:
        point_sort_key = (
            -result.get("local_point_swing", result["final_point_swing"]),
            -result["final_point_swing"],
            -result["declarer_points_gained"],
            result["defender_points_gained"],
            -result["steps_simulated"],
            result["policy"],
        )

        if "_objective_utility" in result:
            return (-result["_objective_utility"], *point_sort_key)

        return point_sort_key

    return sorted(policy_results, key=build_sort_key)


def build_policy_recommendation(
    comparison_result: dict[str, Any],
) -> dict[str, Any]:
    """
    Builds a compact policy recommendation from a policy comparison result.
    """
    best_policy = find_best_policy_by_local_point_swing(comparison_result)

    reason = "Best final point swing after tie-breakers."
    if "_objective_utility" in best_policy:
        reason = "Best Null contract objective after tie-breakers."

    return {
        "policy": best_policy["policy"],
        "reason": reason,
        "final_point_swing": best_policy["final_point_swing"],
        "local_point_swing": best_policy.get(
            "local_point_swing",
            best_policy["final_point_swing"],
        ),
        "declarer_points_gained": best_policy["declarer_points_gained"],
        "defender_points_gained": best_policy["defender_points_gained"],
        "steps_simulated": best_policy["steps_simulated"],
        "stop_reason": best_policy["stop_reason"],
    }
