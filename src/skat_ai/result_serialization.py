from typing import Any

from skat_ai.bounded_search_result import build_serializable_bounded_search_result
from skat_ai.game_state import GameState
from skat_ai.information_set_search_multi_step import (
    InformationSetSearchMultiStepDecisionV1,
    SearchAwareMultiStepDecision,
    build_serializable_information_set_search_multi_step_decision_v1,
)
from skat_ai.multi_step_recommendation import MultiStepRecommendationDecision
from skat_ai.opponent_sequence import build_serializable_opponent_sequence_result


def build_serializable_game_state(
    state: GameState,
) -> dict[str, Any]:
    """
    Builds a JSON-serializable representation of a GameState.
    """
    return {
        "game_type": state.game_type,
        "player_role": state.player_role,
        "hand": state.hand,
        "current_trick": state.current_trick,
        "played_cards": state.played_cards,
        "skat": state.skat,
        "player_position": state.player_position,
        "declarer_player": state.declarer_player,
        "trick_leader": state.trick_leader,
        "completed_tricks": state.completed_tricks,
        "declarer_points": state.declarer_points,
        "defender_points": state.defender_points,
        "next_player": state.next_player,
    }


def build_serializable_multi_step_recommendation_decision(
    decision: SearchAwareMultiStepDecision,
    *,
    executed_card: str | None,
) -> dict[str, Any]:
    """Serializes one aggregate-only Search-aware Multi-Step decision."""
    if type(decision) is InformationSetSearchMultiStepDecisionV1:
        return build_serializable_information_set_search_multi_step_decision_v1(
            decision,
            executed_card=executed_card,
        )
    if not isinstance(decision, MultiStepRecommendationDecision):
        raise ValueError("Invalid Multi-Step recommendation decision.")
    if decision.recommendation_card != executed_card:
        raise ValueError("Recommendation decision card must match the executed card.")
    return {
        "step_index": decision.step_index,
        "requested_method": decision.requested_method,
        "effective_method": decision.effective_method,
        "search_attempted": decision.search_attempted,
        "recommendation_card": decision.recommendation_card,
        "recommendation_reason": decision.recommendation_reason,
        "fallback_used": decision.fallback_used,
        "fallback_method": decision.fallback_method,
        "bounded_search_result": build_serializable_bounded_search_result(
            decision.bounded_search_result
        ),
    }


def build_serializable_multi_step_step(
    step: dict[str, Any],
) -> dict[str, Any]:
    """
    Builds a JSON-serializable representation of one multi-step result step.
    """
    serialized_step = {
        "step_index": step["step_index"],
        "opponent_lead_result": build_serializable_opponent_sequence_result(
            step["opponent_lead_result"]
        ),
        "prepared_state": build_serializable_game_state(step["prepared_state"]),
        "candidate_card": step["candidate_card"],
        "card_selection_policy": step["card_selection_policy"],
        "detailed_result": {
            key: step["detailed_result"][key]
            for key in (
                "trick",
                "did_win",
                "candidate_card_won",
                "local_side_won",
                "trick_points",
                "completed_trick",
            )
            if key in step["detailed_result"]
        },
    }
    if "coherence_summary" in step:
        serialized_step["coherence_summary"] = step["coherence_summary"]
    if "hidden_card_inference_summary" in step:
        serialized_step["hidden_card_inference_summary"] = step[
            "hidden_card_inference_summary"
        ]
    if "recommendation_decision" in step:
        serialized_step["recommendation_decision"] = (
            build_serializable_multi_step_recommendation_decision(
                step["recommendation_decision"],
                executed_card=step["candidate_card"],
            )
        )
    return serialized_step


def build_serializable_multi_step_result(
    result: dict[str, Any],
) -> dict[str, Any]:
    """
    Builds a JSON-serializable multi-step result.
    """
    serialized_result = {
        "card_selection_policy": result["card_selection_policy"],
        "requested_step_count": result["requested_step_count"],
        "steps_simulated": result["steps_simulated"],
        "stop_reason": result["stop_reason"],
        "strict_context": result["strict_context"],
        "opponent_policy_settings": result.get("opponent_policy_settings", {}),
        "left_opponent_policy_settings": result.get("left_opponent_policy_settings"),
        "right_opponent_policy_settings": result.get("right_opponent_policy_settings"),
        "summary": result["summary"],
        "context_summary": result["context_summary"],
        "steps": [
            build_serializable_multi_step_step(step)
            for step in result["steps"]
        ],
        "final_state": build_serializable_game_state(result["final_state"]),
    }
    if "hidden_card_inference_summary" in result:
        serialized_result["hidden_card_inference_summary"] = result[
            "hidden_card_inference_summary"
        ]
    if "stopped_recommendation_decision" in result:
        serialized_result["stopped_recommendation_decision"] = (
            build_serializable_multi_step_recommendation_decision(
                result["stopped_recommendation_decision"],
                executed_card=None,
            )
        )
    return serialized_result


def build_serializable_policy_comparison_result(
    result: dict[str, Any],
) -> dict[str, Any]:
    """
    Builds a JSON-serializable policy comparison result.
    """
    serializable_result = {
        "requested_step_count": result["requested_step_count"],
        "random_seed": result["random_seed"],
        "expected_value_sample_count": result["expected_value_sample_count"],
        "use_basic_opponent_strategy": result["use_basic_opponent_strategy"],
        "strict_context": result["strict_context"],
        "opponent_lead_policy": result.get("opponent_lead_policy", "lowest_point"),
        "opponent_response_policy": result.get("opponent_response_policy", "lowest_point"),
        "policies": result["policies"],
        "policy_results": [
            {
                "policy": policy_result["policy"],
                "requested_step_count": policy_result["requested_step_count"],
                "steps_simulated": policy_result["steps_simulated"],
                "stop_reason": policy_result["stop_reason"],
                "strict_context": policy_result["strict_context"],
                "declarer_points_gained": policy_result["declarer_points_gained"],
                "defender_points_gained": policy_result["defender_points_gained"],
                "final_point_swing": policy_result["final_point_swing"],
                "local_point_swing": policy_result.get(
                    "local_point_swing",
                    policy_result["final_point_swing"],
                ),
                "context_summary": policy_result["context_summary"],
                **(
                    {
                        "eligible_for_recommendation": policy_result[
                            "eligible_for_recommendation"
                        ],
                        "ineligible_reason": policy_result["ineligible_reason"],
                    }
                    if "eligible_for_recommendation" in policy_result
                    else {}
                ),
                **(
                    {
                        "recommendation_summary": policy_result[
                            "recommendation_summary"
                        ],
                        "search_decision_diagnostics": policy_result[
                            "search_decision_diagnostics"
                        ],
                    }
                    if "recommendation_summary" in policy_result
                    else {}
                ),
            }
            for policy_result in result["policy_results"]
        ],
    }

    if "recommended_policy" in result:
        serializable_result["recommended_policy"] = result["recommended_policy"]
    if "hidden_world" in result:
        serializable_result["hidden_world"] = result["hidden_world"]
    if "hidden_card_inference_summary" in result:
        serializable_result["hidden_card_inference_summary"] = result[
            "hidden_card_inference_summary"
        ]

    return serializable_result
