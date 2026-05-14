from typing import Any

from skat_ai.game_state import GameState
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
        "trick_leader": state.trick_leader,
        "completed_tricks": state.completed_tricks,
        "declarer_points": state.declarer_points,
        "defender_points": state.defender_points,
        "next_player": state.next_player,
    }


def build_serializable_multi_step_step(
    step: dict[str, Any],
) -> dict[str, Any]:
    """
    Builds a JSON-serializable representation of one multi-step result step.
    """
    return {
        "step_index": step["step_index"],
        "opponent_lead_result": build_serializable_opponent_sequence_result(
            step["opponent_lead_result"]
        ),
        "candidate_card": step["candidate_card"],
        "card_selection_policy": step["card_selection_policy"],
        "detailed_result": step["detailed_result"],
    }


def build_serializable_multi_step_result(
    result: dict[str, Any],
) -> dict[str, Any]:
    """
    Builds a JSON-serializable multi-step result.
    """
    return {
        "card_selection_policy": result["card_selection_policy"],
        "requested_step_count": result["requested_step_count"],
        "steps_simulated": result["steps_simulated"],
        "stop_reason": result["stop_reason"],
        "strict_context": result["strict_context"],
        "opponent_policy_settings": result.get("opponent_policy_settings", {}),
        "summary": result["summary"],
        "context_summary": result["context_summary"],
        "steps": [
            build_serializable_multi_step_step(step)
            for step in result["steps"]
        ],
        "final_state": build_serializable_game_state(result["final_state"]),
    }


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
                "context_summary": policy_result["context_summary"],
            }
            for policy_result in result["policy_results"]
        ],
    }

    if "recommended_policy" in result:
        serializable_result["recommended_policy"] = result["recommended_policy"]

    return serializable_result