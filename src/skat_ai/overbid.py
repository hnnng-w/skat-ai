import math
from typing import Any


def build_overbid_summary(
    game_value_summary: dict[str, Any],
    bid_value: int | None,
    game_end_reason: str = "not_ended",
    impossible_null_settlement: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Builds an overbid summary from game value and bid value.
    """
    game_value = game_value_summary["game_value"]

    if bid_value is None:
        summary = {
            "bid_value": None,
            "game_value": game_value,
            "is_overbid": None,
            "margin": None,
            "required_game_value": None,
            "status": "unknown_bid_value",
        }
        return add_impossible_null_settlement_summary(
            summary, game_end_reason, impossible_null_settlement
        )

    if game_value is None:
        summary = {
            "bid_value": bid_value,
            "game_value": None,
            "is_overbid": None,
            "margin": None,
            "required_game_value": None,
            "status": "unknown_game_value",
        }
        return add_impossible_null_settlement_summary(
            summary, game_end_reason, impossible_null_settlement
        )

    margin = game_value - bid_value
    base_value = game_value_summary.get("base_value")
    is_null_game = game_value_summary.get("is_null_game", False)
    required_game_value = None

    if base_value is not None and not is_null_game:
        required_game_value = calculate_required_overbid_game_value(
            bid_value=bid_value,
            base_value=base_value,
        )

    if impossible_null_settlement is not None:
        required_game_value = impossible_null_settlement["required_game_value"]

    if bid_value > game_value:
        summary = {
            "bid_value": bid_value,
            "game_value": game_value,
            "is_overbid": True,
            "margin": margin,
            "required_game_value": required_game_value,
            "status": "overbid",
        }
        return add_impossible_null_settlement_summary(
            summary, game_end_reason, impossible_null_settlement
        )

    summary = {
        "bid_value": bid_value,
        "game_value": game_value,
        "is_overbid": False,
        "margin": margin,
        "required_game_value": game_value,
        "status": "not_overbid",
    }
    return add_impossible_null_settlement_summary(
        summary, game_end_reason, impossible_null_settlement
    )


def add_impossible_null_settlement_summary(
    summary: dict[str, Any],
    game_end_reason: str,
    impossible_null_settlement: dict[str, Any] | None,
) -> dict[str, Any]:
    """Adds the dedicated nullable summary only for impossible Null declarations."""
    if game_end_reason == "impossible_null_declaration":
        summary["impossible_null_settlement"] = impossible_null_settlement

    return summary

def calculate_required_overbid_game_value(
    bid_value: int,
    base_value: int,
) -> int:
    """
    Calculates the smallest reachable game value that covers the bid.

    This applies to suit and grand games, where game values are multiples
    of the base value.
    """
    if bid_value <= 0:
        raise ValueError("bid_value must be a positive integer.")

    if base_value <= 0:
        raise ValueError("base_value must be a positive integer.")

    multiplier = math.ceil(bid_value / base_value)

    return multiplier * base_value
