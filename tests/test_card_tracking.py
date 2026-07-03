from skat_ai.card_tracking import get_seen_cards, get_unseen_cards, get_unseen_cards_for_state
from skat_ai.deck import get_full_deck
from skat_ai.game_state import GameState
from skat_ai.input_loader import build_local_game_state_from_input


def test_full_deck_contains_32_cards() -> None:
    deck = get_full_deck()

    assert len(deck) == 32
    assert len(set(deck)) == 32


def test_full_deck_contains_expected_cards() -> None:
    deck = get_full_deck()

    assert "CA" in deck
    assert "CJ" in deck
    assert "S10" in deck
    assert "D7" in deck


def test_seen_cards_include_hand_current_trick_played_cards_and_skat() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["CJ", "SA", "S9"],
        current_trick=["H10"],
        played_cards=["D7", "C10"],
        skat=["D8", "C7"],
    )

    assert get_seen_cards(state) == ["CJ", "SA", "S9", "H10", "D7", "C10", "D8", "C7"]


def test_unseen_cards_exclude_seen_cards() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["CJ", "SA", "S9"],
        current_trick=["H10"],
        played_cards=["D7", "C10"],
        skat=["D8", "C7"],
    )

    unseen_cards = get_unseen_cards(state)

    assert len(unseen_cards) == 24
    assert "CJ" not in unseen_cards
    assert "SA" not in unseen_cards
    assert "H10" not in unseen_cards
    assert "D7" not in unseen_cards
    assert "D8" not in unseen_cards


def test_unseen_cards_include_private_skat_after_local_defender_view() -> None:
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
    unseen_cards = get_unseen_cards(state)

    assert "C7" in unseen_cards
    assert "D8" in unseen_cards


def test_unseen_cards_exclude_private_skat_after_local_declarer_view() -> None:
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
    unseen_cards = get_unseen_cards(state)

    assert "C7" not in unseen_cards
    assert "D8" not in unseen_cards


def test_seen_cards_include_completed_tricks() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA"],
        current_trick=[],
        completed_tricks=[
            {
                "cards": ["CA", "C10", "CK"],
                "winner_role": "declarer",
            }
        ],
    )

    seen_cards = get_seen_cards(state)

    assert "CA" in seen_cards
    assert "C10" in seen_cards
    assert "CK" in seen_cards

def test_get_unseen_cards_for_state_excludes_known_cards() -> None:
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

    unseen_cards = get_unseen_cards_for_state(state)

    assert "SA" not in unseen_cards
    assert "S7" not in unseen_cards
    assert "C7" not in unseen_cards
    assert "D7" not in unseen_cards
    assert "CA" not in unseen_cards
    assert "C10" not in unseen_cards
    assert "CK" not in unseen_cards
