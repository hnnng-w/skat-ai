from typing import Any

from skat_ai.deck import get_full_deck
from skat_ai.game_state import GameState


def get_cards_from_completed_tricks(completed_tricks: list[dict[str, Any]]) -> list[str]:
    """
    Returns all cards from completed tricks.
    """
    cards = []

    for completed_trick in completed_tricks:
        cards.extend(completed_trick.get("cards", []))

    return cards


def get_seen_cards(state: GameState) -> list[str]:
    """
    Returns all cards known to the player.

    Seen cards include:
    - cards in the player's hand
    - cards in the current trick
    - cards already played in previous tricks
    - skat cards, if known
    - cards in completed tricks
    """
    seen_cards = []

    seen_cards.extend(state.hand)
    seen_cards.extend(state.current_trick)
    seen_cards.extend(state.played_cards)
    seen_cards.extend(state.skat)
    seen_cards.extend(get_cards_from_completed_tricks(state.completed_tricks))

    return seen_cards


def get_unseen_cards(state: GameState) -> list[str]:
    """
    Returns all cards that are not known to the player.
    """
    seen_cards = set(get_seen_cards(state))

    return [
        card for card in get_full_deck()
        if card not in seen_cards
    ]