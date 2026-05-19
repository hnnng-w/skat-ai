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
            "status": "unknown_bid_value",
        }

    if game_value is None:
        return {
            "bid_value": bid_value,
            "game_value": None,
            "is_overbid": None,
            "margin": None,
            "status": "unknown_game_value",
        }

    margin = game_value - bid_value

    if bid_value > game_value:
        return {
            "bid_value": bid_value,
            "game_value": game_value,
            "is_overbid": True,
            "margin": margin,
            "status": "overbid",
        }

    return {
        "bid_value": bid_value,
        "game_value": game_value,
        "is_overbid": False,
        "margin": margin,
        "status": "not_overbid",
    }