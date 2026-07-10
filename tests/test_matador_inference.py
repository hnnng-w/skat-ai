from skat_ai.matador_inference import (
    get_trump_order_for_matadors,
    infer_matadors_from_concrete_declarer_known_ownership,
    infer_matadors_from_declarer_cards,
    infer_matadors_from_local_declarer_known_ownership,
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


def test_infer_matadors_from_completed_trick_ownership_counts_with_two() -> None:
    assert infer_matadors_from_local_declarer_known_ownership(
        game_type="grand",
        player_role="declarer",
        declarer_cards=["CJ"],
        completed_tricks=[
            {
                "cards": ["SJ", "H7", "HJ"],
                "players": ["me", "left", "right"],
            }
        ],
    ) == 2


def test_infer_matadors_from_completed_trick_ownership_counts_without_two() -> None:
    assert infer_matadors_from_local_declarer_known_ownership(
        game_type="grand",
        player_role="declarer",
        declarer_cards=[],
        completed_tricks=[
            {
                "cards": ["CJ", "SJ", "HJ"],
                "players": ["left", "right", "me"],
            }
        ],
    ) == 2


def test_infer_matadors_from_completed_trick_ownership_requires_known_boundary() -> None:
    assert infer_matadors_from_local_declarer_known_ownership(
        game_type="grand",
        player_role="declarer",
        declarer_cards=["CJ"],
        completed_tricks=[
            {
                "cards": ["HJ", "D7", "D8"],
                "players": ["left", "me", "right"],
            }
        ],
    ) is None


def test_infer_matadors_from_completed_tricks_ignores_tricks_without_players() -> None:
    assert infer_matadors_from_local_declarer_known_ownership(
        game_type="grand",
        player_role="declarer",
        declarer_cards=[],
        completed_tricks=[
            {
                "cards": ["CJ", "SJ", "HJ"],
            }
        ],
    ) is None


def test_infer_matadors_from_completed_tricks_requires_local_declarer() -> None:
    assert infer_matadors_from_local_declarer_known_ownership(
        game_type="grand",
        player_role="defender",
        declarer_cards=[],
        completed_tricks=[
            {
                "cards": ["CJ", "SJ", "HJ"],
                "players": ["left", "right", "me"],
            }
        ],
    ) is None


def test_infer_matadors_from_completed_tricks_with_concrete_declarer() -> None:
    assert infer_matadors_from_concrete_declarer_known_ownership(
        game_type="grand",
        declarer_player="left",
        declarer_cards=[],
        completed_tricks=[
            {
                "cards": ["CJ", "H7", "D7"],
                "players": ["left", "right", "me"],
            },
            {
                "cards": ["SJ", "HJ", "D8"],
                "players": ["left", "right", "me"],
            },
        ],
    ) == 2


def test_infer_without_matadors_from_defender_played_top_trumps() -> None:
    assert infer_matadors_from_concrete_declarer_known_ownership(
        game_type="grand",
        declarer_player="left",
        declarer_cards=[],
        completed_tricks=[
            {
                "cards": ["HJ", "CJ", "D7"],
                "players": ["left", "right", "me"],
            },
            {
                "cards": ["D8", "SJ", "D9"],
                "players": ["left", "right", "me"],
            },
        ],
    ) == 2


def test_infer_matadors_combines_declarer_cards_with_completed_tricks() -> None:
    assert infer_matadors_from_concrete_declarer_known_ownership(
        game_type="grand",
        declarer_player="me",
        declarer_cards=["CJ", "SJ"],
        completed_tricks=[
            {
                "cards": ["D7", "HJ", "D8"],
                "players": ["me", "left", "right"],
            }
        ],
    ) == 2


def test_infer_matadors_ignores_completed_tricks_without_concrete_declarer() -> None:
    assert infer_matadors_from_concrete_declarer_known_ownership(
        game_type="grand",
        declarer_player="unknown",
        declarer_cards=[],
        completed_tricks=[
            {
                "cards": ["CJ", "SJ", "HJ"],
                "players": ["left", "right", "me"],
            }
        ],
    ) is None


def test_infer_matadors_does_not_use_winner_role_alone() -> None:
    assert infer_matadors_from_concrete_declarer_known_ownership(
        game_type="grand",
        declarer_player="left",
        declarer_cards=[],
        completed_tricks=[
            {
                "cards": ["CJ", "SJ", "HJ"],
                "winner_role": "declarer",
            }
        ],
    ) is None


def test_infer_matadors_from_completed_tricks_returns_none_for_null() -> None:
    assert infer_matadors_from_concrete_declarer_known_ownership(
        game_type="null",
        declarer_player="left",
        declarer_cards=[],
        completed_tricks=[
            {
                "cards": ["CJ", "SJ", "HJ"],
                "players": ["left", "right", "me"],
            }
        ],
    ) is None
