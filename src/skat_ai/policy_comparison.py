import random
from typing import Any

from skat_ai.card_selection import (
    DEFAULT_POLICY_COMPARISON_POLICIES,
    SEARCH_AWARE_MULTI_STEP_POLICIES,
)
from skat_ai.coherent_hidden_world import (
    build_coherent_hidden_world,
    copy_coherent_hidden_world,
    derive_simulation_child_seed,
)
from skat_ai.effective_opponent_policy import EffectiveOpponentPolicySettings
from skat_ai.game_declaration import GameDeclaration
from skat_ai.game_state import GameState
from skat_ai.hidden_card_inference import (
    build_hidden_card_inference_model,
    build_hidden_card_inference_summary,
)
from skat_ai.information_set_search_multi_step import (
    InformationSetSearchMultiStepDecisionV1,
    build_compact_information_set_search_decision_diagnostic_v1,
)
from skat_ai.multi_step_recommendation import (
    LOCAL_POLICY_NO_RECOMMENDATION,
    build_compact_search_decision_diagnostic,
)
from skat_ai.multi_step_simulation import simulate_multiple_steps
from skat_ai.objective_utility import calculate_null_horizon_utility_from_states
from skat_ai.public_hand_constraint import PublicHandConstraint
from skat_ai.recommendation_workflow import RecommendationMethodConfiguration
from skat_ai.simulation_provenance import (
    DecisionProvenanceHook,
    RecommendationDecisionObserver,
)
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
    public_hand_constraints: tuple[PublicHandConstraint, ...] = (),
    game_declaration: GameDeclaration | None = None,
    recommendation_configuration: RecommendationMethodConfiguration | None = None,
    effective_opponent_policy_settings: EffectiveOpponentPolicySettings | None = None,
    decision_provenance_hook: DecisionProvenanceHook | None = None,
    recommendation_decision_observer: RecommendationDecisionObserver | None = None,
) -> dict[str, Any]:
    """
    Compares multiple card-selection policies on the same multi-step setup.
    """
    if policies is not None and not policies:
        raise ValueError("Policy Comparison requires at least one policy.")
    selected_policies = list(
        DEFAULT_POLICY_COMPARISON_POLICIES if policies is None else policies
    )
    if len(selected_policies) != len(set(selected_policies)):
        raise ValueError("Policy Comparison policies must be unique.")
    search_policy = None
    if (
        recommendation_configuration is not None
        and recommendation_configuration.requested_method
        in SEARCH_AWARE_MULTI_STEP_POLICIES
    ):
        search_policy = recommendation_configuration.requested_method
        if game_declaration is None:
            raise ValueError("Search-inclusive Policy Comparison requires a declaration.")
        selected_policies = [
            policy for policy in selected_policies if policy != search_policy
        ]
        selected_policies.append(search_policy)
    unexpected_search_policies = [
        policy
        for policy in selected_policies
        if policy in SEARCH_AWARE_MULTI_STEP_POLICIES and policy != search_policy
    ]
    if unexpected_search_policies:
        raise ValueError(
            "Policy Comparison Search policy requires matching Search configuration."
        )

    comparison_setup_seed = derive_simulation_child_seed(
        random_seed,
        "policy_comparison_setup",
    )
    shared_inference_model = build_hidden_card_inference_model(
        state,
        left_hand_size,
        right_hand_size,
        public_hand_constraints,
    )
    shared_initial_hidden_world = build_coherent_hidden_world(
        state=state,
        left_hand_size=left_hand_size,
        right_hand_size=right_hand_size,
        random_generator=random.Random(comparison_setup_seed),
        public_hand_constraints=public_hand_constraints,
        hidden_card_inference_model=shared_inference_model,
    )

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
            public_hand_constraints=public_hand_constraints,
            initial_hidden_world=copy_coherent_hidden_world(
                shared_initial_hidden_world
            ),
            initial_hidden_card_inference_model=shared_inference_model,
            game_declaration=game_declaration,
            recommendation_configuration=(
                recommendation_configuration if policy == search_policy else None
            ),
            effective_opponent_policy_settings=(
                effective_opponent_policy_settings if policy == search_policy else None
            ),
            decision_provenance_hook=decision_provenance_hook,
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
        if search_policy is not None:
            eligible = multi_step_result["stop_reason"] != LOCAL_POLICY_NO_RECOMMENDATION
            policy_result["eligible_for_recommendation"] = eligible
            policy_result["ineligible_reason"] = (
                None if eligible else LOCAL_POLICY_NO_RECOMMENDATION
            )
        if policy == search_policy:
            policy_result["recommendation_summary"] = {
                key: summary[key]
                for key in (
                    "requested_method",
                    "decisions_attempted",
                    "decisions_executed",
                    "search_recommendations_used",
                    "immediate_fallbacks_used",
                    "no_recommendation_count",
                )
            }
            decisions = [
                step["recommendation_decision"]
                for step in multi_step_result["steps"]
            ]
            stopped = multi_step_result.get("stopped_recommendation_decision")
            if stopped is not None:
                decisions.append(stopped)
            if recommendation_decision_observer is not None:
                for decision in decisions:
                    recommendation_decision_observer(policy, decision)
            policy_result["search_decision_diagnostics"] = [
                (
                    build_compact_information_set_search_decision_diagnostic_v1(
                        decision
                    )
                    if type(decision) is InformationSetSearchMultiStepDecisionV1
                    else build_compact_search_decision_diagnostic(decision)
                )
                for decision in decisions
            ]

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
        "hidden_world": {
            "mode": "coherent_path",
            "shared_root_world": True,
            "root_sample_count": 1,
            "policy_path_count": len(selected_policies),
            "independent_path_worlds": True,
            "hidden_cards_emitted": False,
        },
    }
    inference_summary = build_hidden_card_inference_summary(shared_inference_model)
    if inference_summary is not None:
        comparison_result["hidden_card_inference_summary"] = inference_summary

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
    policy_results = [
        result
        for result in comparison_result["policy_results"]
        if result.get("eligible_for_recommendation", True)
    ]

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
            not result.get("eligible_for_recommendation", True),
            -result.get("local_point_swing", result["final_point_swing"]),
            -result["final_point_swing"],
            -result["declarer_points_gained"],
            result["defender_points_gained"],
            -result["steps_simulated"],
            result["policy"],
        )

        if "_objective_utility" in result:
            return (
                point_sort_key[0],
                -result["_objective_utility"],
                *point_sort_key[1:],
            )

        return point_sort_key

    return sorted(policy_results, key=build_sort_key)


def build_policy_recommendation(
    comparison_result: dict[str, Any],
) -> dict[str, Any] | None:
    """
    Builds a compact policy recommendation from a policy comparison result.
    """
    try:
        best_policy = find_best_policy_by_local_point_swing(comparison_result)
    except ValueError:
        return None

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
