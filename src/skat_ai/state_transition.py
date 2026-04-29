from copy import deepcopy
from typing import Any

from skat_ai.game_state import GameState
from skat_ai.rules import get_trick_points


def remove_card_from_hand(hand: list[str], card: str) -> list[str]:
    """
    Returns a new hand with one occurrence of card removed.
    """
    if card not in hand:
        raise ValueError("Card must be in hand to remove it.")

    updated_hand = hand.copy()
    updated_hand.remove(card)

    return updated_hand


def determine_next_player_from_completed_trick(
    completed_trick: dict[str, Any],
    player_role: str,
) -> str:
    """
    Determines the next player after a completed trick.

    If winner_player is available, that player leads the next trick.
    If only winner_role is available, fall back to legacy behavior.
    """
    winner_player = completed_trick.get("winner_player", "unknown")

    if winner_player in ["me", "left", "right"]:
        return winner_player

    winner_role = completed_trick["winner_role"]

    if player_role == "declarer":
        if winner_role == "declarer":
            return "me"

        return "unknown"

    if player_role == "defender":
        if winner_role == "defenders":
            return "me"

        return "unknown"

    return "unknown"


def apply_completed_trick_to_points(
    declarer_points: int,
    defender_points: int,
    completed_trick: dict[str, Any],
) -> tuple[int, int]:
    """
    Applies completed trick points to declarer or defender points.
    """
    trick_points = get_trick_points(completed_trick["cards"])
    winner_role = completed_trick["winner_role"]

    if winner_role == "declarer":
        return declarer_points + trick_points, defender_points

    if winner_role == "defenders":
        return declarer_points, defender_points + trick_points

    raise ValueError(f"Invalid completed trick winner role: {winner_role}")


def advance_state_after_detailed_trick(
    state: GameState,
    candidate_card: str,
    detailed_result: dict[str, Any],
) -> GameState:
    """
    Builds the next GameState after applying a detailed immediate-trick result.

    The old state is not mutated.
    """
    completed_trick = detailed_result["completed_trick"]

    updated_hand = remove_card_from_hand(
        hand=state.hand,
        card=candidate_card,
    )

    updated_completed_tricks = deepcopy(state.completed_tricks)
    updated_completed_tricks.append(deepcopy(completed_trick))

    updated_declarer_points, updated_defender_points = apply_completed_trick_to_points(
        declarer_points=state.declarer_points,
        defender_points=state.defender_points,
        completed_trick=completed_trick,
    )

    next_player = determine_next_player_from_completed_trick(
        completed_trick=completed_trick,
        player_role=state.player_role,
    )

    return GameState(
        game_type=state.game_type,
        player_role=state.player_role,
        hand=updated_hand,
        current_trick=[],
        played_cards=state.played_cards.copy(),
        skat=state.skat.copy(),
        player_position=state.player_position,
        trick_leader=next_player,
        completed_tricks=updated_completed_tricks,
        declarer_points=updated_declarer_points,
        defender_points=updated_defender_points,
        next_player=next_player,
    )