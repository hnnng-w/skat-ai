from typing import Any

DECLARER_WIN_POINT_THRESHOLD = 61
DEFENDER_WIN_POINT_THRESHOLD = 60
TOTAL_CARD_POINTS = 120
SCHNEIDER_POINT_THRESHOLD = 30
SCHWARZ_POINT_THRESHOLD = 0
COMPLETED_TRICK_COUNT = 10
VALID_COMPLETED_TRICK_WINNER_ROLES = ["declarer", "defenders"]


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


def get_schneider_status(
    declarer_points: int,
    defender_points: int,
) -> str:
    """
    Returns Schneider status based on card points.

    Possible values:
    - declarer_made_schneider
    - defenders_made_schneider
    - none
    """
    if defender_points <= SCHNEIDER_POINT_THRESHOLD:
        return "declarer_made_schneider"

    if declarer_points <= SCHNEIDER_POINT_THRESHOLD:
        return "defenders_made_schneider"

    return "none"


def get_schwarz_status(
    declarer_points: int,
    defender_points: int,
) -> str:
    """
    Returns Schwarz status based on card points.

    Possible values:
    - declarer_made_schwarz
    - defenders_made_schwarz
    - none
    """
    if defender_points == SCHWARZ_POINT_THRESHOLD:
        return "declarer_made_schwarz"

    if declarer_points == SCHWARZ_POINT_THRESHOLD:
        return "defenders_made_schwarz"

    return "none"


def get_effective_schneider_status(
    declarer_points: int,
    defender_points: int,
) -> str:
    """
    Returns Schneider status only when all card points are assigned.

    Possible values:
    - declarer_made_schneider
    - defenders_made_schneider
    - none
    - pending
    """
    if not is_card_point_result_complete(
        declarer_points=declarer_points,
        defender_points=defender_points,
    ):
        return "pending"

    return get_schneider_status(
        declarer_points=declarer_points,
        defender_points=defender_points,
    )


def get_effective_schwarz_status(
    declarer_points: int,
    defender_points: int,
) -> str:
    """
    Returns Schwarz status only when all card points are assigned.

    Possible values:
    - declarer_made_schwarz
    - defenders_made_schwarz
    - none
    - pending
    """
    if not is_card_point_result_complete(
        declarer_points=declarer_points,
        defender_points=defender_points,
    ):
        return "pending"

    return get_schwarz_status(
        declarer_points=declarer_points,
        defender_points=defender_points,
    )


def get_completed_trick_schwarz_status(
    completed_tricks: list[dict[str, Any]],
) -> str:
    """
    Returns Schwarz status from reliable completed-trick ownership.

    Possible values:
    - declarer
    - defenders
    - none
    - unresolved
    """
    if len(completed_tricks) < COMPLETED_TRICK_COUNT:
        return "unresolved"

    if len(completed_tricks) > COMPLETED_TRICK_COUNT:
        raise ValueError(
            "Completed Schwarz result requires exactly ten completed tricks."
        )

    declarer_trick_count = 0
    defender_trick_count = 0

    for trick_index, completed_trick in enumerate(completed_tricks):
        if not isinstance(completed_trick, dict):
            raise ValueError(
                f"completed_tricks[{trick_index}] must be an object "
                "for completed Schwarz result."
            )

        if "winner_role" not in completed_trick:
            raise ValueError(
                "completed_tricks["
                f"{trick_index}].winner_role is required for completed Schwarz result."
            )

        winner_role = completed_trick["winner_role"]
        if winner_role not in VALID_COMPLETED_TRICK_WINNER_ROLES:
            raise ValueError(
                "Invalid completed Schwarz trick winner_role at index "
                f"{trick_index}: {winner_role}"
            )

        if winner_role == "declarer":
            declarer_trick_count += 1
        else:
            defender_trick_count += 1

    if defender_trick_count == 0:
        return "declarer"

    if declarer_trick_count == 0:
        return "defenders"

    return "none"


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
        "raw_schneider_status": get_schneider_status(
            declarer_points=declarer_points,
            defender_points=defender_points,
        ),
        "raw_schwarz_status": get_schwarz_status(
            declarer_points=declarer_points,
            defender_points=defender_points,
        ),
        "effective_schneider_status": get_effective_schneider_status(
            declarer_points=declarer_points,
            defender_points=defender_points,
        ),
        "effective_schwarz_status": get_effective_schwarz_status(
            declarer_points=declarer_points,
            defender_points=defender_points,
        ),
        "thresholds": {
            "declarer_win": DECLARER_WIN_POINT_THRESHOLD,
            "defender_win": DEFENDER_WIN_POINT_THRESHOLD,
            "schneider": SCHNEIDER_POINT_THRESHOLD,
            "schwarz": SCHWARZ_POINT_THRESHOLD,
            "total_card_points": TOTAL_CARD_POINTS,
        },
    }


def get_null_contract_winner_from_completed_tricks(
    completed_tricks: list[dict[str, Any]],
) -> str | None:
    """
    Returns the completed Null contract winner from reliable trick ownership.

    Null games are won by the declarer only if the declarer took no tricks.
    The function returns None when fewer than ten tricks are available, because
    an incomplete Null history must not be promoted to a win.
    """
    if len(completed_tricks) < COMPLETED_TRICK_COUNT:
        return None

    if len(completed_tricks) > COMPLETED_TRICK_COUNT:
        raise ValueError(
            "Completed Null result requires exactly ten completed tricks."
        )

    declarer_trick_count = 0

    for trick_index, completed_trick in enumerate(completed_tricks):
        if not isinstance(completed_trick, dict):
            raise ValueError(
                f"completed_tricks[{trick_index}] must be an object "
                "for completed Null result."
            )

        if "winner_role" not in completed_trick:
            raise ValueError(
                "completed_tricks["
                f"{trick_index}].winner_role is required for completed Null result."
            )

        winner_role = completed_trick["winner_role"]
        if winner_role not in VALID_COMPLETED_TRICK_WINNER_ROLES:
            raise ValueError(
                "Invalid completed Null trick winner_role at index "
                f"{trick_index}: {winner_role}"
            )

        if winner_role == "declarer":
            declarer_trick_count += 1

    if declarer_trick_count == 0:
        return "declarer"

    return "defenders"


def build_incomplete_null_result_summary(
    game_result_summary: dict[str, Any],
) -> dict[str, Any]:
    """
    Returns an incomplete Null result without applying card-point fallback.
    """
    updated_summary = game_result_summary.copy()
    updated_summary["is_complete"] = False
    updated_summary["winner"] = "undecided"
    updated_summary["status"] = "in_progress"
    updated_summary["effective_schneider_status"] = "pending"
    updated_summary["effective_schwarz_status"] = "pending"

    return updated_summary


def apply_completed_null_contract_result(
    game_result_summary: dict[str, Any],
    completed_tricks: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Applies completed Null contract semantics when ownership is reliable.
    """
    contract_winner = get_null_contract_winner_from_completed_tricks(
        completed_tricks
    )

    if contract_winner is None:
        return build_incomplete_null_result_summary(game_result_summary)

    updated_summary = game_result_summary.copy()
    updated_summary["is_complete"] = True
    updated_summary["winner"] = contract_winner
    updated_summary["status"] = "final_decided"

    return updated_summary


def build_game_result_summary_from_score_summary(
    score_summary: dict[str, int],
    game_type: str | None = None,
    completed_tricks: list[dict[str, Any]] | None = None,
    game_end_reason: str | None = None,
) -> dict[str, Any]:
    """
    Builds a result summary from an existing score summary.
    """
    game_result_summary = build_game_result_summary_from_points(
        declarer_points=score_summary["total_declarer_points"],
        defender_points=score_summary["total_defender_points"],
    )

    if game_type == "null" and game_end_reason == "normal_completion":
        return apply_completed_null_contract_result(
            game_result_summary=game_result_summary,
            completed_tricks=completed_tricks or [],
        )

    return game_result_summary
