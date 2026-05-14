from skat_ai.deck import get_full_deck
from skat_ai.game_state import GameState
from skat_ai.sampling_validation import (
    get_available_card_count_for_sampling,
    validate_enough_cards_for_opponent_sampling,
)


def test_get_available_card_count_for_sampling() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA"],
        current_trick=["S7"],
        played_cards=["C7"],
        skat=[],
    )

    available_count = get_available_card_count_for_sampling(state)

    assert available_count == len(get_full_deck()) - 3


def test_validate_enough_cards_for_opponent_sampling_accepts_enough_cards() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA"],
        current_trick=["S7"],
    )

    validate_enough_cards_for_opponent_sampling(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
    )


def test_validate_enough_cards_for_opponent_sampling_rejects_too_many_cards() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=get_full_deck()[:-1],
        current_trick=[],
    )

    try:
        validate_enough_cards_for_opponent_sampling(
            state=state,
            left_hand_size=1,
            right_hand_size=1,
        )
    except ValueError as error:
        assert "Not enough available cards for opponent sampling" in str(error)
        assert "required 2" in str(error)
        assert "available 1" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")