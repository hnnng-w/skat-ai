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


def build_default_overbid_summary() -> dict[str, Any]:
    """
    Builds a default unknown overbid summary.
    """
    return {
        "bid_value": None,
        "game_value": None,
        "is_overbid": None,
        "margin": None,
        "required_game_value": None,
        "status": "unknown",
    }

def build_final_settlement_summary(
    game_value_summary: dict[str, Any],
    game_result_summary: dict[str, Any],
    overbid_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Builds a placeholder final settlement summary.

    This is intentionally conservative. Full Skat settlement logic such as
    lost-game doubling and overbid handling is not implemented yet.
    """
    if overbid_summary is None:
        overbid_summary = build_default_overbid_summary()

    missing_inputs = get_missing_final_settlement_inputs(
        game_value_summary=game_value_summary,
        game_result_summary=game_result_summary,
    )
    is_complete = len(missing_inputs) == 0
    declarer_won_by_card_points = is_declarer_winner_by_card_points(
        game_result_summary
    )
    effective_game_value = (
        get_effective_settlement_game_value(
            game_value=game_value_summary["game_value"],
            overbid_summary=overbid_summary,
        )
        if is_complete and game_value_summary["game_value"] is not None
        else None
    )

    effective_declarer_won = (
        False
        if overbid_summary["is_overbid"] is True
        else declarer_won_by_card_points
    )
    is_loss = (
        effective_declarer_won is False
        if effective_declarer_won is not None
        else None
    )

    settlement_score = (
        calculate_basic_settlement_score(
            game_value=effective_game_value,
            declarer_won_by_card_points=effective_declarer_won,
        )
        if is_complete
        and effective_game_value is not None
        and effective_declarer_won is not None
        else None
    )

    return {
        "is_complete": is_complete,
        "missing_inputs": missing_inputs,
        "declarer_won_by_card_points": declarer_won_by_card_points,
        "winner": game_result_summary["winner"] if is_complete else None,
        "game_value": game_value_summary["game_value"],
        "effective_game_value": effective_game_value,
        "bid_value": overbid_summary["bid_value"],
        "settlement_score": settlement_score,
        "is_loss": is_loss,
        "is_overbid": overbid_summary["is_overbid"],
        "overbid_margin": overbid_summary["margin"],
        "overbid_status": overbid_summary["status"],
        "overbid_required_game_value": overbid_summary["required_game_value"],
        "notes": [
            "Settlement score uses simplified Skat logic.",
            "Lost declarer games are counted as -2 * game_value.",
            "Overbid handling is not implemented yet.",
        ],
    }

def get_effective_settlement_game_value(
    game_value: int,
    overbid_summary: dict[str, Any],
) -> int:
    """
    Returns the game value used for final settlement scoring.

    In normal cases, this is the declared game value.
    In overbid cases, this is the smallest reachable game value
    that covers the bid.
    """
    if overbid_summary["is_overbid"] is True:
        required_game_value = overbid_summary["required_game_value"]

        if required_game_value is None:
            raise ValueError("Overbid settlement requires required_game_value.")

        return required_game_value

    return game_value