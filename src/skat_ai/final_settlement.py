from typing import Any


def get_missing_final_settlement_inputs(
    game_value_summary: dict[str, Any],
    game_result_summary: dict[str, Any],
    overbid_summary: dict[str, Any] | None = None,
) -> list[str]:
    """
    Returns missing inputs that prevent final settlement calculation.
    """
    missing_inputs = []

    if not game_result_summary["is_complete"]:
        missing_inputs.append("complete_card_points")

    if game_value_summary["game_value"] is None:
        missing_inputs.append("game_value")

    if overbid_summary is not None and not is_overbid_settlement_supported(
        overbid_summary
    ):
        missing_inputs.append("overbid_required_game_value")

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
    Builds the final single-game settlement summary.

    This uses simplified Skat settlement logic. Lost games are counted as
    -2 * effective_game_value. Supported Suit/Grand overbid cases use the
    required game value from overbid_summary. Full official settlement nuances
    are not completely modeled yet.
    """
    if overbid_summary is None:
        overbid_summary = build_default_overbid_summary()

    missing_inputs = get_missing_final_settlement_inputs(
        game_value_summary=game_value_summary,
        game_result_summary=game_result_summary,
        overbid_summary=overbid_summary,
    )
    is_complete = len(missing_inputs) == 0
    declarer_won_by_card_points = is_declarer_winner_by_card_points(
        game_result_summary
    )
    effective_game_value = None

    if (
        is_complete
        and game_value_summary["game_value"] is not None
        and is_overbid_settlement_supported(overbid_summary)
    ):
        effective_game_value = get_effective_settlement_game_value(
            game_value=game_value_summary["game_value"],
            overbid_summary=overbid_summary,
        )
        effective_game_value = apply_achieved_schneider_settlement_level(
            settlement_game_value=effective_game_value,
            game_value_summary=game_value_summary,
            game_result_summary=game_result_summary,
            overbid_summary=overbid_summary,
        )

    if overbid_summary["is_overbid"] is True:
        effective_declarer_won = False
    elif is_schneider_announcement_failed(
        game_value_summary=game_value_summary,
        game_result_summary=game_result_summary,
    ):
        effective_declarer_won = False
    else:
        effective_declarer_won = declarer_won_by_card_points
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
            "Lost declarer games are counted as -2 * effective_game_value.",
            "Overbid settlement is supported for suit and grand games when "
            "required_game_value is available.",
        ],
    }


def apply_achieved_schneider_settlement_level(
    settlement_game_value: int,
    game_value_summary: dict[str, Any],
    game_result_summary: dict[str, Any],
    overbid_summary: dict[str, Any],
) -> int:
    """
    Adds one base-value level for achieved Schneider in completed suit/grand games.

    When Schneider was announced, game_value already includes the announcement
    level. Only declarer-made Schneider adds the separate achieved level.
    """
    if overbid_summary["is_overbid"] is True:
        return settlement_game_value

    if not game_result_summary["is_complete"]:
        return settlement_game_value

    if game_value_summary.get("is_null_game") is not False:
        return settlement_game_value

    base_value = game_value_summary.get("base_value")

    if base_value is None:
        return settlement_game_value

    effective_schneider_status = game_result_summary.get(
        "effective_schneider_status"
    )

    if effective_schneider_status not in [
        "declarer_made_schneider",
        "defenders_made_schneider",
    ]:
        return settlement_game_value

    if (
        is_schneider_announced(game_value_summary)
        and effective_schneider_status != "declarer_made_schneider"
    ):
        return settlement_game_value

    return settlement_game_value + base_value


def is_schneider_announced(
    game_value_summary: dict[str, Any],
) -> bool:
    """
    Returns whether Schneider was announced in the declared game value model.
    """
    details = game_value_summary.get("details", {})

    if not isinstance(details, dict):
        return False

    return details.get("schneider_announced") is True


def is_schneider_announcement_failed(
    game_value_summary: dict[str, Any],
    game_result_summary: dict[str, Any],
) -> bool:
    """
    Returns whether an announced Schneider was missed in a completed suit/grand game.
    """
    if not game_result_summary["is_complete"]:
        return False

    if game_value_summary.get("is_null_game") is not False:
        return False

    if not is_schneider_announced(game_value_summary):
        return False

    return (
        game_result_summary.get("effective_schneider_status")
        != "declarer_made_schneider"
    )

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

def is_overbid_settlement_supported(
    overbid_summary: dict[str, Any],
) -> bool:
    """
    Returns whether overbid settlement can be scored.
    """
    if overbid_summary["is_overbid"] is not True:
        return True

    return overbid_summary["required_game_value"] is not None
