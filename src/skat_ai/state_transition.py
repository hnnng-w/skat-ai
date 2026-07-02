from copy import deepcopy
from typing import Any

from skat_ai.game_state import GameState


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
    declarer_player: str = "unknown",
) -> str:
    """
    Determines the next player after a completed trick.

    If winner_player is available, that player leads the next trick.
    If only side-level ownership is available, return a concrete player only
    when that player is known from declarer identity.
    """
    winner_player = completed_trick.get("winner_player", "unknown")

    if winner_player in ["me", "left", "right"]:
        return winner_player

    winner_role = completed_trick["winner_role"]

    if winner_role == "declarer" and declarer_player in ["me", "left", "right"]:
        return declarer_player

    if player_role == "declarer" and winner_role == "declarer":
        return "me"

    return "unknown"


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

    next_player = determine_next_player_from_completed_trick(
        completed_trick=completed_trick,
        player_role=state.player_role,
        declarer_player=state.declarer_player,
    )

    return GameState(
        game_type=state.game_type,
        player_role=state.player_role,
        hand=updated_hand,
        current_trick=[],
        played_cards=state.played_cards.copy(),
        skat=state.skat.copy(),
        player_position=state.player_position,
        declarer_player=state.declarer_player,
        trick_leader=next_player,
        completed_tricks=updated_completed_tricks,
        declarer_points=state.declarer_points,
        defender_points=state.defender_points,
        next_player=next_player,
    )
