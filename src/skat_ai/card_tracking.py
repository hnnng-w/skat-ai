from skat_ai.deck import get_full_deck
from skat_ai.game_state import GameState


def get_seen_cards(state: GameState) -> list[str]:
    """
    Returns all cards known to the player.

    Seen cards include:
    - cards in the player's hand
    - cards in the current trick
    - cards already played in previous tricks
    - skat cards, if known
    """
    seen_cards = []

    seen_cards.extend(state.hand)
    seen_cards.extend(state.current_trick)
    seen_cards.extend(state.played_cards)
    seen_cards.extend(state.skat)

    return seen_cards


def get_unseen_cards(state: GameState) -> list[str]:
    """
    Returns all cards that are not known to the player.
    """
    seen_cards = set(get_seen_cards(state))

    return [card for card in get_full_deck() if card not in seen_cards]
