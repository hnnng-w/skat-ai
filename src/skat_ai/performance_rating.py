from typing import Any

SUPPORTED_PERFORMANCE_RATING_SYSTEMS = [
    "placeholder",
    "isko_list",
]
ISKO_DECLARER_WIN_POINTS = 50
ISKO_DECLARER_LOSS_POINTS = -50
ISKO_COUNTERPARTY_LOSS_BONUS_THREE_PLAYER_TABLE = 40
ISKO_FIXED_TABLE_PLAYER_COUNT = 3


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

def calculate_isko_declarer_rating_points(
    game_outcome: str,
) -> int | None:
    """
    Calculates basic ISkO-style declarer rating points.

    This only covers the declarer's basic win/loss rating points.
    Defender and tournament/list-specific additions are added later.
    """
    if game_outcome == "declarer_win":
        return ISKO_DECLARER_WIN_POINTS

    if game_outcome == "declarer_loss":
        return ISKO_DECLARER_LOSS_POINTS

    return None

def is_performance_rating_partially_implemented(
    rating_system: str | None,
) -> bool:
    """
    Returns whether the selected rating system has partial implementation.
    """
    return rating_system == "isko_list"

def get_performance_rating_implemented_scope(
    rating_system: str | None,
) -> str | None:
    """
    Returns the scope that is currently implemented for the selected rating system.
    """
    if rating_system == "isko_list":
        return "declarer_single_game_rating"

    return None


def get_performance_rating_unsupported_scope(
    rating_system: str | None,
) -> str:
    """
    Returns the scope that is not implemented yet for the selected rating system.
    """
    if rating_system == "isko_list":
        return "full_list_series_tournament_rating"

    return "performance_rating_not_implemented"

def get_performance_rating_unsupported_reason(
    rating_system: str | None,
) -> str:
    """
    Returns why performance rating is not implemented yet.
    """
    if rating_system == "isko_list":
        return "full_list_series_tournament_rating_not_implemented"

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
    validate_performance_rating_system(rating_system)

    game_outcome = get_game_outcome_for_rating(final_settlement_summary)

    declarer_rating_points = None
    counterparty_rating_points = None
    declarer_rating_score = None

    if rating_system == "isko_list":
        declarer_rating_points = calculate_isko_declarer_rating_points(
            game_outcome
        )
        counterparty_rating_points = calculate_isko_counterparty_rating_points(
            game_outcome
        )
        declarer_rating_score = calculate_isko_declarer_rating_score(
            settlement_score=final_settlement_summary["settlement_score"],
            declarer_rating_points=declarer_rating_points,
        )

    return {
        "is_implemented": False,
        "is_partially_implemented": is_performance_rating_partially_implemented(
            rating_system
        ),
        "implemented_scope": get_performance_rating_implemented_scope(
            rating_system
        ),
        "unsupported_scope": get_performance_rating_unsupported_scope(
            rating_system
        ),
        "rating_system": rating_system,
        "table_player_count": ISKO_FIXED_TABLE_PLAYER_COUNT,
        "basis": "individual_game_settlement",
        "game_outcome": game_outcome,
        "settlement_score": final_settlement_summary["settlement_score"],
        "rating_score": declarer_rating_score,
        "declarer_rating_score": declarer_rating_score,
        "declarer_rating_points": declarer_rating_points,
        "counterparty_rating_points": counterparty_rating_points,
        "defender_rating_points": counterparty_rating_points,
        "unsupported_reason": get_performance_rating_unsupported_reason(
            rating_system
        ),
        "notes": [
            "Performance rating is separate from individual game settlement.",
            "rating_score currently represents the declarer's rating score.",
            "List, series, and tournament rating are not fully implemented yet.",
            "final_settlement_summary remains the source for single-game settlement.",
        ],
    }

def validate_performance_rating_system(
    rating_system: str | None,
) -> None:
    """
    Validates the optional performance rating system.
    """
    if rating_system is None:
        return

    if rating_system not in SUPPORTED_PERFORMANCE_RATING_SYSTEMS:
        raise ValueError(f"Unknown performance rating system: {rating_system}")

def calculate_isko_counterparty_rating_points(
    game_outcome: str,
) -> int | None:
    """
    Calculates ISkO-style counterparty rating points per counterparty member.

    This project assumes a fixed three-player table.
    """
    if game_outcome == "declarer_win":
        return 0

    if game_outcome == "declarer_loss":
        return ISKO_COUNTERPARTY_LOSS_BONUS_THREE_PLAYER_TABLE

    return None

def calculate_isko_declarer_rating_score(
    settlement_score: int | None,
    declarer_rating_points: int | None,
) -> int | None:
    """
    Calculates the declarer's partial ISkO-style rating score.

    This combines the individual game settlement score with the declarer's
    win/loss rating points.
    """
    if settlement_score is None or declarer_rating_points is None:
        return None

    return settlement_score + declarer_rating_points