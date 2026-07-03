from skat_ai.game_state import GameState
from skat_ai.input_loader import build_local_game_state_from_input
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


def test_known_cards_exclude_local_defender_private_skat_after_local_view() -> None:
    state = build_local_game_state_from_input(
        {
            "game_type": "grand",
            "player_role": "defender",
            "declarer_player": "left",
            "hand": ["SA"],
            "current_trick": [],
            "skat": ["C7", "D8"],
            "skat_visibility": "known_to_declarer",
        }
    )

    assert get_known_cards_from_state(state) == ["SA"]


def test_known_cards_include_local_declarer_private_skat_after_local_view() -> None:
    state = build_local_game_state_from_input(
        {
            "game_type": "grand",
            "player_role": "declarer",
            "declarer_player": "me",
            "hand": ["SA"],
            "current_trick": [],
            "skat": ["C7", "D8"],
            "skat_visibility": "known_to_declarer",
        }
    )

    assert get_known_cards_from_state(state) == ["SA", "C7", "D8"]


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
