from skat_ai.matador_inference import (
    get_trump_order_for_matadors,
    infer_matadors_from_declarer_cards,
)


def test_get_trump_order_for_matadors_returns_jacks_for_grand() -> None:
    assert get_trump_order_for_matadors("grand") == ["CJ", "SJ", "HJ", "DJ"]


def test_get_trump_order_for_matadors_returns_jacks_and_suit_for_spades() -> None:
    assert get_trump_order_for_matadors("spades") == [
        "CJ",
        "SJ",
        "HJ",
        "DJ",
        "SA",
        "S10",
        "SK",
        "SQ",
        "S9",
        "S8",
        "S7",
    ]


def test_get_trump_order_for_matadors_returns_empty_for_null() -> None:
    assert get_trump_order_for_matadors("null") == []


def test_infer_matadors_returns_none_for_null_game() -> None:
    assert infer_matadors_from_declarer_cards(
        game_type="null",
        declarer_cards=["CJ", "SJ"],
    ) is None


def test_infer_matadors_returns_none_without_declarer_cards() -> None:
    assert infer_matadors_from_declarer_cards(
        game_type="grand",
        declarer_cards=[],
    ) is None


def test_infer_matadors_counts_with_top_trumps() -> None:
    assert infer_matadors_from_declarer_cards(
        game_type="grand",
        declarer_cards=["CJ", "SJ", "HJ", "D7"],
    ) == 3


def test_infer_matadors_stops_with_gap_when_holding_top_trump() -> None:
    assert infer_matadors_from_declarer_cards(
        game_type="grand",
        declarer_cards=["CJ", "HJ", "D7"],
    ) == 1


def test_infer_matadors_counts_without_top_trumps() -> None:
    assert infer_matadors_from_declarer_cards(
        game_type="grand",
        declarer_cards=["HJ", "D7"],
    ) == 2


def test_infer_matadors_counts_without_one_when_second_trump_is_owned() -> None:
    assert infer_matadors_from_declarer_cards(
        game_type="grand",
        declarer_cards=["SJ", "D7"],
    ) == 1


def test_infer_matadors_counts_suit_trumps_after_jacks() -> None:
    assert infer_matadors_from_declarer_cards(
        game_type="spades",
        declarer_cards=["CJ", "SJ", "HJ", "DJ", "SA", "S10", "D7"],
    ) == 6


def test_infer_matadors_counts_without_into_suit_trumps() -> None:
    assert infer_matadors_from_declarer_cards(
        game_type="spades",
        declarer_cards=["S10", "D7"],
    ) == 5