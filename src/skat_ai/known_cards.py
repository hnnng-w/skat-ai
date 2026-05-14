from typing import Any

from skat_ai.game_state import GameState


def get_cards_from_completed_tricks(
    completed_tricks: list[dict[str, Any]],
) -> list[str]:
    """
    Returns all cards from completed tricks.
    """
    cards = []

    for completed_trick in completed_tricks:
        cards.extend(completed_trick["cards"])

    return cards


def get_known_cards_from_state(
    state: GameState,
) -> list[str]:
    """
    Returns all cards that are known in the current state.

    Known cards include:
    - player's hand
    - current trick
    - played cards
    - skat
    - completed trick cards
    """
    known_cards = []
    known_cards.extend(state.hand)
    known_cards.extend(state.current_trick)
    known_cards.extend(state.played_cards)
    known_cards.extend(state.skat)
    known_cards.extend(get_cards_from_completed_tricks(state.completed_tricks))

    return known_cards


def get_duplicate_cards(
    cards: list[str],
) -> list[str]:
    """
    Returns duplicate cards while preserving first duplicate discovery order.
    """
    duplicates = []

    for card in cards:
        if cards.count(card) > 1 and card not in duplicates:
            duplicates.append(card)

    return duplicates


def get_unique_cards_preserving_order(
    cards: list[str],
) -> list[str]:
    """
    Returns unique cards while preserving order.
    """
    unique_cards = []

    for card in cards:
        if card not in unique_cards:
            unique_cards.append(card)

    return unique_cards


def validate_no_duplicate_known_cards(
    state: GameState,
) -> None:
    """
    Raises a ValueError if known cards contain duplicates.
    """
    known_cards = get_known_cards_from_state(state)
    duplicates = get_duplicate_cards(known_cards)

    if duplicates:
        raise ValueError(f"Duplicate known cards detected: {duplicates}")