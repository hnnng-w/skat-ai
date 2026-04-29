from typing import Any

from skat_ai.game_state import GameState
from skat_ai.rules import get_trick_points, get_trick_winner


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


def get_played_cards_from_completed_tricks(
    completed_tricks: list[dict[str, Any]],
) -> list[str]:
    """
    Returns all played cards from completed tricks.
    """
    played_cards = []

    for completed_trick in completed_tricks:
        played_cards.extend(get_completed_trick_cards(completed_trick))

    return played_cards


def get_all_played_cards(state: GameState) -> list[str]:
    """
    Returns all played cards known from both legacy played_cards
    and completed_tricks.

    This keeps backward compatibility while allowing completed_tricks
    to become the preferred source over time.
    """
    all_played_cards = []

    all_played_cards.extend(state.played_cards)
    all_played_cards.extend(get_played_cards_from_completed_tricks(state.completed_tricks))

    return all_played_cards


def get_winner_role_for_trick_winner(
    winner_index: int,
    player_index: int,
    player_role: str,
) -> str:
    """
    Determines whether the completed trick was won by the declarer or defenders.

    Args:
        winner_index: Index of the winning card in the completed trick.
        player_index: Index of the player's card in the completed trick.
        player_role: Role of the player, usually "declarer" or "defender".
    """
    if player_role not in ["declarer", "defender"]:
        raise ValueError(f"Unsupported player role for winner-role detection: {player_role}")

    if winner_index == player_index:
        if player_role == "declarer":
            return "declarer"

        return "defenders"

    if player_role == "declarer":
        return "defenders"

    return "declarer"


def build_completed_trick_from_cards(
    cards: list[str],
    game_type: str,
    player_index: int,
    player_role: str,
) -> dict[str, Any]:
    """
    Builds a completed trick entry from exactly three trick cards.

    Completed trick format:
    {
        "cards": ["S7", "SA", "S8"],
        "winner_role": "declarer"
    }
    """
    if len(cards) != 3:
        raise ValueError("A completed trick must contain exactly 3 cards.")

    if player_index not in [0, 1, 2]:
        raise ValueError("player_index must be 0, 1, or 2.")

    winner_index = get_trick_winner(
        trick=cards,
        game_type=game_type,
    )

    winner_role = get_winner_role_for_trick_winner(
        winner_index=winner_index,
        player_index=player_index,
        player_role=player_role,
    )

    return {
        "cards": cards,
        "winner_role": winner_role,
    }


def build_completed_trick_from_state_and_candidate(
    state: GameState,
    completed_trick_cards: list[str],
) -> dict[str, Any]:
    """
    Builds a completed trick entry from a GameState and completed trick cards.

    The player's card index is inferred from len(state.current_trick), because the
    candidate card is played after the existing cards in current_trick.
    """
    player_index = len(state.current_trick)

    return build_completed_trick_from_cards(
        cards=completed_trick_cards,
        game_type=state.game_type,
        player_index=player_index,
        player_role=state.player_role,
    )