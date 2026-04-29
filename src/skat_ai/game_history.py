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


def get_completed_trick_winner_player(completed_trick: dict[str, Any]) -> str:
    """
    Returns the concrete winner player from one completed trick.

    Older completed_trick entries may not contain winner_player yet.
    """
    return completed_trick.get("winner_player", "unknown")


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
    trick_players: list[str] | None = None,
) -> dict[str, Any]:
    """
    Builds a completed trick entry from exactly three trick cards.

    Completed trick format:
    {
        "cards": ["S7", "SA", "S8"],
        "players": ["left", "me", "right"],
        "winner_role": "declarer",
        "winner_player": "me"
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

    if trick_players is None:
        trick_players = ["unknown", "unknown", "unknown"]

    winner_player = (
        get_winner_player_from_trick_players(
            winner_index=winner_index,
            trick_players=trick_players,
        )
        if "unknown" not in trick_players
        else "unknown"
    )

    if winner_player == "unknown":
        winner_role = get_winner_role_for_trick_winner(
            winner_index=winner_index,
            player_index=player_index,
            player_role=player_role,
        )
    else:
        winner_role = get_winner_role_for_winner_player(
            winner_player=winner_player,
            player_role=player_role,
        )

    return {
        "cards": cards,
        "players": trick_players,
        "winner_role": winner_role,
        "winner_player": winner_player,
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

    trick_players = (
        get_players_for_trick_leader(state.trick_leader)
        if state.trick_leader != "unknown"
        else None
    )

    return build_completed_trick_from_cards(
        cards=completed_trick_cards,
        game_type=state.game_type,
        player_index=player_index,
        player_role=state.player_role,
        trick_players=trick_players,
    )


def get_players_for_trick_leader(trick_leader: str) -> list[str]:
    """
    Returns the player order for a trick based on who led the trick.

    Player order always represents the order of cards in the trick.
    """
    if trick_leader == "me":
        return ["me", "left", "right"]

    if trick_leader == "left":
        return ["left", "me", "right"]

    if trick_leader == "right":
        return ["right", "left", "me"]

    raise ValueError(f"Cannot determine trick players for trick leader: {trick_leader}")


def get_winner_player_from_trick_players(
    winner_index: int,
    trick_players: list[str],
) -> str:
    """
    Returns the concrete winner player from winner_index and trick player order.
    """
    if winner_index not in [0, 1, 2]:
        raise ValueError("winner_index must be 0, 1, or 2.")

    if len(trick_players) != 3:
        raise ValueError("trick_players must contain exactly 3 players.")

    return trick_players[winner_index]


def get_winner_role_for_winner_player(
    winner_player: str,
    player_role: str,
) -> str:
    """
    Determines whether the concrete winner player belongs to declarer or defenders.
    """
    if winner_player not in ["me", "left", "right"]:
        raise ValueError(f"Invalid winner player: {winner_player}")

    if player_role not in ["declarer", "defender"]:
        raise ValueError(f"Unsupported player role for winner-role detection: {player_role}")

    if player_role == "declarer":
        if winner_player == "me":
            return "declarer"

        return "defenders"

    if winner_player == "me":
        return "defenders"

    return "declarer"