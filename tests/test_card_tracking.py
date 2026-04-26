from skat_ai.card_tracking import get_seen_cards, get_unseen_cards
from skat_ai.deck import get_full_deck
from skat_ai.game_state import GameState


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
