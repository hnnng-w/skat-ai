from skat_ai.deck import get_full_deck
from skat_ai.game_state import GameState
from skat_ai.known_cards import get_known_cards_from_state


def get_available_card_count_for_sampling(
    state: GameState,
) -> int:
    """
    Returns the number of cards available for opponent-hand sampling.
    """
    known_cards = get_known_cards_from_state(state)
    full_deck = get_full_deck()

    return len([
        card for card in full_deck
        if card not in known_cards
    ])


def validate_enough_cards_for_opponent_sampling(
    state: GameState,
    left_hand_size: int,
    right_hand_size: int,
) -> None:
    """
    Raises a ValueError if there are not enough cards available
    to sample opponent hands.
    """
    required_cards = left_hand_size + right_hand_size
    available_cards = get_available_card_count_for_sampling(state)

    if available_cards < required_cards:
        raise ValueError(
            "Not enough available cards for opponent sampling: "
            f"required {required_cards}, available {available_cards}."
        )