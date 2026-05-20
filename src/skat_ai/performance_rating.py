from typing import Any


def build_performance_rating_summary(
    final_settlement_summary: dict[str, Any],
) -> dict[str, Any]:
    """
    Builds a placeholder performance rating summary.

    Performance rating is intentionally separated from individual game settlement.
    It will later cover list, series, and tournament scoring.
    """
    return {
        "is_implemented": False,
        "basis": "individual_game_settlement",
        "settlement_score": final_settlement_summary["settlement_score"],
        "rating_score": None,
        "rating_system": None,
        "notes": [
            "Performance rating is separate from individual game settlement.",
            "List, series, and tournament rating are not implemented yet.",
            "final_settlement_summary remains the source for single-game settlement.",
        ],
    }