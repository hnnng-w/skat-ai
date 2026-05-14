from skat_ai.deck import get_full_deck
from skat_ai.game_history import get_played_cards_from_completed_tricks
from skat_ai.game_state import GameState
from skat_ai.known_cards import get_known_cards_from_state


def get_seen_cards(state: GameState) -> list[str]:
    """
    Returns all cards known to the player.

    Seen cards include:
    - cards in the player's hand
    - cards in the current trick
    - legacy played_cards
    - skat cards, if known
    - cards in completed tricks
    """
    seen_cards = []

    seen_cards.extend(state.hand)
    seen_cards.extend(state.current_trick)
    seen_cards.extend(state.played_cards)
    seen_cards.extend(state.skat)
    seen_cards.extend(get_played_cards_from_completed_tricks(state.completed_tricks))

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

def get_unseen_cards_for_state(
    state: GameState,
) -> list[str]:
    """
    Returns all cards that are not known in the current state.
    """
    full_deck = get_full_deck()
    known_cards = get_known_cards_from_state(state)

    return [
        card for card in full_deck
        if card not in known_cards
    ]