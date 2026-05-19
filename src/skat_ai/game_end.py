from typing import Any

from skat_ai.game_result import build_game_result_summary_from_points

REMAINING_POINTS_TO_DECLARER_REASONS = [
    "declarer_claimed_remaining_tricks",
    "defenders_conceded_remaining_tricks",
]

REMAINING_POINTS_TO_DEFENDERS_REASONS = [
    "declarer_conceded_remaining_tricks",
]

NO_REMAINING_POINTS_ASSIGNMENT_REASONS = [
    "not_ended",
    "normal_completion",
]

VALID_GAME_END_REASONS = (
    NO_REMAINING_POINTS_ASSIGNMENT_REASONS
    + REMAINING_POINTS_TO_DECLARER_REASONS
    + REMAINING_POINTS_TO_DEFENDERS_REASONS
)

ACTIVE_REMAINING_POINTS_ASSIGNMENT_REASONS = [
    "declarer_claimed_remaining_tricks",
    "declarer_conceded_remaining_tricks",
    "defenders_conceded_remaining_tricks",
]


def get_remaining_points_recipient(
    game_end_reason: str,
) -> str | None:
    """
    Returns who receives remaining card points for a game-end reason.

    Possible return values:
    - declarer
    - defenders
    - None
    """
    validate_game_end_reason(game_end_reason)

    if game_end_reason in REMAINING_POINTS_TO_DECLARER_REASONS:
        return "declarer"

    if game_end_reason in REMAINING_POINTS_TO_DEFENDERS_REASONS:
        return "defenders"

    return None


def apply_remaining_points_assignment(
    game_result_summary: dict[str, Any],
    game_end_reason: str,
) -> dict[str, Any]:
    """
    Assigns remaining card points based on game_end_reason.

    If no assignment applies, the original summary is returned as a copy.
    """
    points_remaining = game_result_summary["points_remaining"]
    validate_game_end_reason_for_points(
        game_end_reason=game_end_reason,
        points_remaining=points_remaining,
    )
    recipient = get_remaining_points_recipient(game_end_reason)

    if recipient is None:
        updated_summary = game_result_summary.copy()
        updated_summary["game_end_reason"] = game_end_reason
        updated_summary["remaining_points_recipient"] = None
        updated_summary["remaining_points_assigned"] = 0
        return updated_summary

    declarer_points = game_result_summary["declarer_points"]
    defender_points = game_result_summary["defender_points"]

    if recipient == "declarer":
        declarer_points += points_remaining

    if recipient == "defenders":
        defender_points += points_remaining

    updated_summary = build_game_result_summary_from_points(
        declarer_points=declarer_points,
        defender_points=defender_points,
    )
    updated_summary["game_end_reason"] = game_end_reason
    updated_summary["remaining_points_recipient"] = recipient
    updated_summary["remaining_points_assigned"] = points_remaining

    return updated_summary

def validate_game_end_reason(
    game_end_reason: str,
) -> None:
    """
    Validates a game-end reason.
    """
    if game_end_reason not in VALID_GAME_END_REASONS:
        raise ValueError(f"Unknown game_end_reason: {game_end_reason}")


def validate_game_end_reason_for_points(
    game_end_reason: str,
    points_remaining: int,
) -> None:
    """
    Validates whether game_end_reason is consistent with remaining card points.
    """
    validate_game_end_reason(game_end_reason)

    if points_remaining < 0:
        raise ValueError("points_remaining cannot be negative.")

    if game_end_reason == "not_ended" and points_remaining == 0:
        raise ValueError("not_ended requires remaining card points.")

    if game_end_reason == "normal_completion" and points_remaining != 0:
        raise ValueError("normal_completion requires zero remaining card points.")

    if (
        game_end_reason in ACTIVE_REMAINING_POINTS_ASSIGNMENT_REASONS
        and points_remaining == 0
    ):
        raise ValueError(f"{game_end_reason} requires remaining card points.")