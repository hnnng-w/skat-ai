from skat_ai.game_state import GameState
from skat_ai.known_cards import (
    get_cards_from_completed_tricks,
    get_duplicate_cards,
    get_known_cards_from_state,
    get_unique_cards_preserving_order,
    validate_no_duplicate_known_cards,
)


def test_get_cards_from_completed_tricks() -> None:
    completed_tricks = [
        {
            "cards": ["CA", "C10", "CK"],
            "winner_role": "defenders",
        },
        {
            "cards": ["S7", "SA", "S8"],
            "winner_role": "declarer",
        },
    ]

    cards = get_cards_from_completed_tricks(completed_tricks)

    assert cards == ["CA", "C10", "CK", "S7", "SA", "S8"]


def test_get_known_cards_from_state() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA"],
        current_trick=["S7"],
        played_cards=["C7"],
        skat=["D7"],
        completed_tricks=[
            {
                "cards": ["CA", "C10", "CK"],
                "winner_role": "defenders",
            }
        ],
    )

    known_cards = get_known_cards_from_state(state)

    assert known_cards == ["SA", "S7", "C7", "D7", "CA", "C10", "CK"]


def test_get_duplicate_cards() -> None:
    duplicates = get_duplicate_cards(["SA", "S7", "SA", "D7", "S7"])

    assert duplicates == ["SA", "S7"]


def test_get_unique_cards_preserving_order() -> None:
    unique_cards = get_unique_cards_preserving_order(["SA", "S7", "SA", "D7"])

    assert unique_cards == ["SA", "S7", "D7"]


def test_validate_no_duplicate_known_cards_accepts_unique_cards() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA"],
        current_trick=["S7"],
        played_cards=["C7"],
        skat=["D7"],
    )

    validate_no_duplicate_known_cards(state)


def test_validate_no_duplicate_known_cards_rejects_duplicates() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA"],
        current_trick=["S7"],
        played_cards=["SA"],
        skat=[],
    )

    try:
        validate_no_duplicate_known_cards(state)
    except ValueError as error:
        assert "Duplicate known cards detected" in str(error)
        assert "SA" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")