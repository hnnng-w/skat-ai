import math
from typing import Any


def build_overbid_summary(
    game_value_summary: dict[str, Any],
    bid_value: int | None,
) -> dict[str, Any]:
    """
    Builds an overbid summary from game value and bid value.
    """
    game_value = game_value_summary["game_value"]

    if bid_value is None:
        return {
            "bid_value": None,
            "game_value": game_value,
            "is_overbid": None,
            "margin": None,
            "required_game_value": None,
            "status": "unknown_bid_value",
        }

    if game_value is None:
        return {
            "bid_value": bid_value,
            "game_value": None,
            "is_overbid": None,
            "margin": None,
            "required_game_value": None,
            "status": "unknown_game_value",
        }

    margin = game_value - bid_value
    base_value = game_value_summary.get("base_value")
    is_null_game = game_value_summary.get("is_null_game", False)
    required_game_value = None

    if base_value is not None and not is_null_game:
        required_game_value = calculate_required_overbid_game_value(
            bid_value=bid_value,
            base_value=base_value,
        )

    if bid_value > game_value:
        return {
            "bid_value": bid_value,
            "game_value": game_value,
            "is_overbid": True,
            "margin": margin,
            "required_game_value": required_game_value,
            "status": "overbid",
        }

    return {
        "bid_value": bid_value,
        "game_value": game_value,
        "is_overbid": False,
        "margin": margin,
        "required_game_value": game_value,
        "status": "not_overbid",
    }

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