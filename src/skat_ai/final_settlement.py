from typing import Any


def get_missing_final_settlement_inputs(
    game_value_summary: dict[str, Any],
    game_result_summary: dict[str, Any],
) -> list[str]:
    """
    Returns missing inputs that prevent final settlement calculation.
    """
    missing_inputs = []

    if not game_result_summary["is_complete"]:
        missing_inputs.append("complete_card_points")

    if game_value_summary["game_value"] is None:
        missing_inputs.append("game_value")

    return missing_inputs


def is_declarer_winner_by_card_points(
    game_result_summary: dict[str, Any],
) -> bool | None:
    """
    Returns whether the declarer won by card points.

    Returns None if the card-point result is not complete.
    """
    if not game_result_summary["is_complete"]:
        return None

    return game_result_summary["winner"] == "declarer"


def build_final_settlement_summary(
    game_value_summary: dict[str, Any],
    game_result_summary: dict[str, Any],
) -> dict[str, Any]:
    """
    Builds a placeholder final settlement summary.

    This is intentionally conservative. Full Skat settlement logic such as
    lost-game doubling and overbid handling is not implemented yet.
    """
    missing_inputs = get_missing_final_settlement_inputs(
        game_value_summary=game_value_summary,
        game_result_summary=game_result_summary,
    )
    is_complete = len(missing_inputs) == 0
    declarer_won_by_card_points = is_declarer_winner_by_card_points(
        game_result_summary
    )

    return {
        "is_complete": is_complete,
        "missing_inputs": missing_inputs,
        "declarer_won_by_card_points": declarer_won_by_card_points,
        "winner": game_result_summary["winner"] if is_complete else None,
        "game_value": game_value_summary["game_value"],
        "settlement_score": None,
        "is_loss": (
            declarer_won_by_card_points is False
            if declarer_won_by_card_points is not None
            else None
        ),
        "is_overbid": None,
        "notes": [
            "Final settlement scoring is not fully implemented yet.",
            "Lost-game doubling is not implemented yet.",
            "Overbid handling is not implemented yet.",
        ],
    }