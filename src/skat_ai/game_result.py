from typing import Any

DECLARER_WIN_POINT_THRESHOLD = 61
DEFENDER_WIN_POINT_THRESHOLD = 60
TOTAL_CARD_POINTS = 120


def get_points_remaining(
    declarer_points: int,
    defender_points: int,
) -> int:
    """
    Returns the number of card points not yet assigned.
    """
    points_remaining = TOTAL_CARD_POINTS - declarer_points - defender_points

    if points_remaining < 0:
        raise ValueError("Assigned card points exceed total card points.")

    return points_remaining


def is_card_point_result_complete(
    declarer_points: int,
    defender_points: int,
) -> bool:
    """
    Returns whether all card points have been assigned.
    """
    return get_points_remaining(
        declarer_points=declarer_points,
        defender_points=defender_points,
    ) == 0


def get_card_point_winner(
    declarer_points: int,
    defender_points: int,
) -> str:
    """
    Returns the current or final winner by card points.

    Possible values:
    - declarer
    - defenders
    - undecided
    """
    if declarer_points >= DECLARER_WIN_POINT_THRESHOLD:
        return "declarer"

    if defender_points >= DEFENDER_WIN_POINT_THRESHOLD:
        return "defenders"

    return "undecided"


def get_card_point_result_status(
    declarer_points: int,
    defender_points: int,
) -> str:
    """
    Returns a status for the current card-point result.
    """
    winner = get_card_point_winner(
        declarer_points=declarer_points,
        defender_points=defender_points,
    )
    is_complete = is_card_point_result_complete(
        declarer_points=declarer_points,
        defender_points=defender_points,
    )

    if winner != "undecided" and is_complete:
        return "final_decided"

    if winner != "undecided":
        return "currently_decided"

    if is_complete:
        return "final_undecided"

    return "in_progress"


def build_game_result_summary_from_points(
    declarer_points: int,
    defender_points: int,
) -> dict[str, Any]:
    """
    Builds a JSON-serializable result summary from card points.
    """
    points_remaining = get_points_remaining(
        declarer_points=declarer_points,
        defender_points=defender_points,
    )
    winner = get_card_point_winner(
        declarer_points=declarer_points,
        defender_points=defender_points,
    )

    return {
        "declarer_points": declarer_points,
        "defender_points": defender_points,
        "points_remaining": points_remaining,
        "is_complete": points_remaining == 0,
        "winner": winner,
        "status": get_card_point_result_status(
            declarer_points=declarer_points,
            defender_points=defender_points,
        ),
        "thresholds": {
            "declarer_win": DECLARER_WIN_POINT_THRESHOLD,
            "defender_win": DEFENDER_WIN_POINT_THRESHOLD,
            "total_card_points": TOTAL_CARD_POINTS,
        },
    }


def build_game_result_summary_from_score_summary(
    score_summary: dict[str, int],
) -> dict[str, Any]:
    """
    Builds a result summary from an existing score summary.
    """
    return build_game_result_summary_from_points(
        declarer_points=score_summary["total_declarer_points"],
        defender_points=score_summary["total_defender_points"],
    )