from typing import Any

from skat_ai.game_history import build_score_summary
from skat_ai.game_state import GameState
from skat_ai.information_set_search_multi_step import (
    InformationSetSearchMultiStepDecisionV1,
)
from skat_ai.information_set_search_workflow import (
    INFORMATION_SET_SEARCH_EFFECTIVE_METHOD,
)
from skat_ai.multi_step_recommendation import MultiStepRecommendationDecision
from skat_ai.recommendation_workflow import (
    AUTO_METHOD,
    BOUNDED_SEARCH_METHOD,
    COMPATIBLE_WORLD_MINIMAX_METHOD,
)


def build_multi_step_score_summary(
    initial_state: GameState,
    final_state: GameState,
) -> dict[str, int]:
    """
    Builds a compact score summary for a multi-step simulation.
    """
    initial_score_summary = build_score_summary(initial_state)
    final_score_summary = build_score_summary(final_state)

    initial_declarer_points = initial_score_summary["total_declarer_points"]
    initial_defender_points = initial_score_summary["total_defender_points"]
    final_declarer_points = final_score_summary["total_declarer_points"]
    final_defender_points = final_score_summary["total_defender_points"]

    declarer_points_gained = final_declarer_points - initial_declarer_points
    defender_points_gained = final_defender_points - initial_defender_points
    final_point_swing = declarer_points_gained - defender_points_gained
    local_point_swing = final_point_swing

    if initial_state.player_role == "defender":
        local_point_swing = defender_points_gained - declarer_points_gained

    return {
        "initial_declarer_points": initial_declarer_points,
        "initial_defender_points": initial_defender_points,
        "final_declarer_points": final_declarer_points,
        "final_defender_points": final_defender_points,
        "declarer_points_gained": declarer_points_gained,
        "defender_points_gained": defender_points_gained,
        "final_point_swing": final_point_swing,
        "local_point_swing": local_point_swing,
    }


def build_multi_step_summary(
    multi_step_result: dict[str, Any],
) -> dict[str, Any]:
    """
    Builds a compact summary for a multi-step simulation result.
    """
    score_summary = build_multi_step_score_summary(
        initial_state=multi_step_result["initial_state"],
        final_state=multi_step_result["final_state"],
    )

    summary = {
        "requested_step_count": multi_step_result["requested_step_count"],
        "steps_simulated": multi_step_result["steps_simulated"],
        "stop_reason": multi_step_result["stop_reason"],
        "card_selection_policy": multi_step_result["card_selection_policy"],
        "strict_context": multi_step_result.get("strict_context", False),
        "score_summary": score_summary,
        "context_summary": multi_step_result.get("context_summary", {}),
    }
    if multi_step_result["card_selection_policy"] in {
        BOUNDED_SEARCH_METHOD,
        AUTO_METHOD,
        "information_set_search",
    }:
        decisions = [
            step["recommendation_decision"] for step in multi_step_result["steps"]
        ]
        stopped_decision = multi_step_result.get("stopped_recommendation_decision")
        if stopped_decision is not None:
            decisions.append(stopped_decision)
        if not all(
            isinstance(
                item,
                (
                    MultiStepRecommendationDecision,
                    InformationSetSearchMultiStepDecisionV1,
                ),
            )
            for item in decisions
        ):
            raise ValueError("Search-aware Multi-Step decisions have an invalid type.")
        if any(
            item.requested_method != multi_step_result["card_selection_policy"]
            for item in decisions
        ):
            raise ValueError("Search-aware decision methods must match the path policy.")
        decisions_executed = len(multi_step_result["steps"])
        search_recommendations_used = sum(
            item.effective_method
            in {
                COMPATIBLE_WORLD_MINIMAX_METHOD,
                INFORMATION_SET_SEARCH_EFFECTIVE_METHOD,
            }
            for item in decisions
        )
        immediate_fallbacks_used = sum(item.fallback_used for item in decisions)
        no_recommendation_count = sum(
            item.recommendation_card is None for item in decisions
        )
        decisions_attempted = len(decisions)
        if no_recommendation_count not in {0, 1}:
            raise ValueError("A Search-aware path can stop without a recommendation once.")
        expected_stop = no_recommendation_count == 1
        if expected_stop != (stopped_decision is not None):
            raise ValueError("Stopped recommendation decision counts do not reconcile.")
        if expected_stop != (
            multi_step_result["stop_reason"] == "local_policy_no_recommendation"
        ):
            raise ValueError("No-recommendation count and stop reason do not reconcile.")
        if decisions_attempted != decisions_executed + no_recommendation_count:
            raise ValueError("Search-aware decision attempt counts do not reconcile.")
        if decisions_executed != search_recommendations_used + immediate_fallbacks_used:
            raise ValueError("Executed Search-aware decision counts do not reconcile.")
        if multi_step_result["card_selection_policy"] == BOUNDED_SEARCH_METHOD and (
            immediate_fallbacks_used
        ):
            raise ValueError("Strict bounded Search cannot report Immediate fallback.")
        if multi_step_result["card_selection_policy"] != AUTO_METHOD and (
            immediate_fallbacks_used
        ):
            raise ValueError("Only auto may report Immediate fallback.")
        if multi_step_result["card_selection_policy"] == "information_set_search" and not all(
            type(item) is InformationSetSearchMultiStepDecisionV1 for item in decisions
        ):
            raise ValueError("Information-set Multi-Step decisions have an invalid type.")
        if multi_step_result["card_selection_policy"] != "information_set_search" and not all(
            isinstance(item, MultiStepRecommendationDecision) for item in decisions
        ):
            raise ValueError("Bounded Search Multi-Step decisions have an invalid type.")
        summary.update(
            {
                "requested_method": multi_step_result["card_selection_policy"],
                "decisions_attempted": decisions_attempted,
                "decisions_executed": decisions_executed,
                "search_recommendations_used": search_recommendations_used,
                "immediate_fallbacks_used": immediate_fallbacks_used,
                "no_recommendation_count": no_recommendation_count,
            }
        )
    return summary
