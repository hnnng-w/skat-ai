from typing import Any

SUPPORTED_PERFORMANCE_RATING_SYSTEMS = [
    "placeholder",
    "isko_list",
]


def get_game_outcome_for_rating(
    final_settlement_summary: dict[str, Any],
) -> str:
    """
    Returns the settlement outcome used as basis for later performance rating.

    This does not calculate list or tournament points yet.
    """
    if not final_settlement_summary["is_complete"]:
        return "incomplete"

    if final_settlement_summary["is_loss"] is True:
        return "declarer_loss"

    if final_settlement_summary["is_loss"] is False:
        return "declarer_win"

    return "unknown"

def get_performance_rating_unsupported_reason(
    rating_system: str | None,
) -> str:
    """
    Returns why performance rating is not implemented yet.
    """
    if rating_system == "isko_list":
        return "isko_list_rating_not_implemented"

    return "performance_rating_not_implemented"


def build_performance_rating_summary(
    final_settlement_summary: dict[str, Any],
    rating_system: str | None = None,
) -> dict[str, Any]:
    """
    Builds a performance rating scaffold.

    Performance rating is intentionally separated from individual game settlement.
    It will later cover list, series, and tournament scoring.
    """
    if (
        rating_system is not None
        and rating_system not in SUPPORTED_PERFORMANCE_RATING_SYSTEMS
    ):
        raise ValueError(f"Unknown performance rating system: {rating_system}")

    game_outcome = get_game_outcome_for_rating(final_settlement_summary)

    return {
        "is_implemented": False,
        "rating_system": rating_system,
        "basis": "individual_game_settlement",
        "game_outcome": game_outcome,
        "settlement_score": final_settlement_summary["settlement_score"],
        "rating_score": None,
        "declarer_rating_points": None,
        "defender_rating_points": None,
        "unsupported_reason": get_performance_rating_unsupported_reason(
            rating_system
        ),
        "notes": [
            "Performance rating is separate from individual game settlement.",
            "List, series, and tournament rating are not implemented yet.",
            "final_settlement_summary remains the source for single-game settlement.",
        ],
    }