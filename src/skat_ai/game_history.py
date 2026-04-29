from typing import Any

from skat_ai.game_state import GameState
from skat_ai.rules import get_trick_points


def get_completed_trick_cards(completed_trick: dict[str, Any]) -> list[str]:
    """
    Returns the cards from one completed trick.
    """
    return completed_trick["cards"]


def get_completed_trick_winner_role(completed_trick: dict[str, Any]) -> str:
    """
    Returns the winner role from one completed trick.
    """
    return completed_trick["winner_role"]


def get_completed_trick_points(completed_trick: dict[str, Any]) -> int:
    """
    Returns the point value of one completed trick.
    """
    return get_trick_points(get_completed_trick_cards(completed_trick))


def calculate_completed_trick_points_by_side(
    completed_tricks: list[dict[str, Any]],
) -> dict[str, int]:
    """
    Calculates declarer and defender points from completed tricks.

    Completed trick format:
    {
        "cards": ["SA", "S7", "S8"],
        "winner_role": "declarer"
    }
    """
    declarer_points = 0
    defender_points = 0

    for completed_trick in completed_tricks:
        trick_points = get_completed_trick_points(completed_trick)
        winner_role = get_completed_trick_winner_role(completed_trick)

        if winner_role == "declarer":
            declarer_points += trick_points
        elif winner_role == "defenders":
            defender_points += trick_points
        else:
            raise ValueError(f"Invalid completed trick winner role: {winner_role}")

    return {
        "declarer_points": declarer_points,
        "defender_points": defender_points,
    }


def build_score_summary(state: GameState) -> dict[str, int]:
    """
    Builds a score summary from explicit points and completed trick history.
    """
    completed_points = calculate_completed_trick_points_by_side(state.completed_tricks)

    return {
        "explicit_declarer_points": state.declarer_points,
        "explicit_defender_points": state.defender_points,
        "completed_trick_declarer_points": completed_points["declarer_points"],
        "completed_trick_defender_points": completed_points["defender_points"],
        "total_declarer_points": state.declarer_points + completed_points["declarer_points"],
        "total_defender_points": state.defender_points + completed_points["defender_points"],
    }