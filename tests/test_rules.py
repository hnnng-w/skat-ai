from skat_ai.rules import (
    get_legal_cards,
    get_trick_points,
    get_trick_winner,
    is_trump,
)


def test_grand_only_jacks_are_trump() -> None:
    assert is_trump("CJ", "grand") is True
    assert is_trump("SJ", "grand") is True
    assert is_trump("SA", "grand") is False
    assert is_trump("H10", "grand") is False


def test_suit_game_jacks_and_trump_suit_are_trump() -> None:
    assert is_trump("CJ", "hearts") is True
    assert is_trump("DJ", "hearts") is True
    assert is_trump("HA", "hearts") is True
    assert is_trump("H10", "hearts") is True
    assert is_trump("SA", "hearts") is False


def test_null_has_no_trump() -> None:
    assert is_trump("CJ", "null") is False
    assert is_trump("HA", "null") is False
    assert is_trump("D7", "null") is False


def test_legal_cards_follow_spades_in_grand() -> None:
    hand = ["CJ", "SA", "S9", "H10", "D7"]
    current_trick = ["S10"]

    assert get_legal_cards(hand, current_trick, "grand") == ["SA", "S9"]


def test_legal_cards_follow_trump_in_grand() -> None:
    hand = ["HJ", "SA", "S9", "H10", "D7"]
    current_trick = ["CJ"]

    assert get_legal_cards(hand, current_trick, "grand") == ["HJ"]


def test_legal_cards_follow_clubs_in_null_when_jack_is_led() -> None:
    hand = ["C9", "SA", "H10", "D7"]
    current_trick = ["CJ"]

    assert get_legal_cards(hand, current_trick, "null") == ["C9"]


def test_grand_spades_trick_ace_wins() -> None:
    trick = ["S10", "SA", "S7"]

    assert get_trick_winner(trick, "grand") == 1


def test_grand_jack_trick_highest_jack_wins() -> None:
    trick = ["HJ", "DJ", "SJ"]

    assert get_trick_winner(trick, "grand") == 2


def test_hearts_trump_beats_non_trump() -> None:
    trick = ["S10", "S7", "H7"]

    assert get_trick_winner(trick, "hearts") == 2


def test_suit_game_jack_beats_suit_trump_ace() -> None:
    trick = ["CJ", "SA", "S7"]

    assert get_trick_winner(trick, "spades") == 0


def test_suit_game_jack_beats_suit_trump_ace_when_played_second() -> None:
    trick = ["SA", "CJ", "S7"]

    assert get_trick_winner(trick, "spades") == 1


def test_null_jack_is_normal_suit_card() -> None:
    trick = ["CJ", "CA", "C7"]

    assert get_trick_winner(trick, "null") == 1


def test_trick_points() -> None:
    trick = ["CA", "C10", "CK"]

    assert get_trick_points(trick) == 25
