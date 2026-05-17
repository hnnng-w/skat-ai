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


def calculate_basic_settlement_score(
    game_value: int,
    declarer_won_by_card_points: bool,
) -> int:
    """
    Calculates a basic settlement score.

    Current simplified model:
    - declarer win: +game_value
    - declarer loss: -2 * game_value
    """
    if declarer_won_by_card_points:
        return game_value

    return -2 * game_value


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
    is_loss = (
        declarer_won_by_card_points is False
        if declarer_won_by_card_points is not None
        else None
    )
    settlement_score = (
        calculate_basic_settlement_score(
            game_value=game_value_summary["game_value"],
            declarer_won_by_card_points=declarer_won_by_card_points,
        )
        if is_complete and declarer_won_by_card_points is not None
        else None
    )

    return {
        "is_complete": is_complete,
        "missing_inputs": missing_inputs,
        "declarer_won_by_card_points": declarer_won_by_card_points,
        "winner": game_result_summary["winner"] if is_complete else None,
        "game_value": game_value_summary["game_value"],
        "settlement_score": settlement_score,
        "is_loss": is_loss,
        "is_overbid": None,
        "notes": [
            "Settlement score uses simplified Skat logic.",
            "Lost declarer games are counted as -2 * game_value.",
            "Overbid handling is not implemented yet.",
        ],
    }