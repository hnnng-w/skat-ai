from typing import Any

from skat_ai.game_state import GameState


def build_multi_step_score_summary(
    initial_state: GameState,
    final_state: GameState,
) -> dict[str, int]:
    """
    Builds a compact score summary for a multi-step simulation.
    """
    declarer_points_gained = final_state.declarer_points - initial_state.declarer_points
    defender_points_gained = final_state.defender_points - initial_state.defender_points
    final_point_swing = declarer_points_gained - defender_points_gained
    local_point_swing = final_point_swing

    if initial_state.player_role == "defender":
        local_point_swing = defender_points_gained - declarer_points_gained

    return {
        "initial_declarer_points": initial_state.declarer_points,
        "initial_defender_points": initial_state.defender_points,
        "final_declarer_points": final_state.declarer_points,
        "final_defender_points": final_state.defender_points,
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

    return {
        "requested_step_count": multi_step_result["requested_step_count"],
        "steps_simulated": multi_step_result["steps_simulated"],
        "stop_reason": multi_step_result["stop_reason"],
        "card_selection_policy": multi_step_result["card_selection_policy"],
        "strict_context": multi_step_result.get("strict_context", False),
        "score_summary": score_summary,
        "context_summary": multi_step_result.get("context_summary", {}),
    }
