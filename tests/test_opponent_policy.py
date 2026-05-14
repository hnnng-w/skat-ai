import random

from skat_ai.opponent_policy import (
    choose_basic_trick_play_card,
    choose_highest_point_card,
    choose_lowest_point_card,
    choose_opponent_lead_card_by_policy,
    choose_opponent_response_card_by_policy,
    choose_random_card,
    get_winning_legal_cards,
    validate_opponent_card_policy,
)


def test_validate_opponent_card_policy_accepts_valid_policy() -> None:
    validate_opponent_card_policy("basic_trick_play")


def test_validate_opponent_card_policy_rejects_invalid_policy() -> None:
    try:
        validate_opponent_card_policy("reckless")
    except ValueError as error:
        assert "Invalid opponent card policy" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_choose_lowest_point_card() -> None:
    assert choose_lowest_point_card(["SA", "S10", "S9"]) == "S9"


def test_choose_lowest_point_card_rejects_empty_list() -> None:
    try:
        choose_lowest_point_card([])
    except ValueError as error:
        assert "empty card list" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_choose_highest_point_card() -> None:
    assert choose_highest_point_card(["SA", "S10", "S9"]) == "SA"


def test_choose_highest_point_card_rejects_empty_list() -> None:
    try:
        choose_highest_point_card([])
    except ValueError as error:
        assert "empty card list" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_choose_random_card_is_reproducible() -> None:
    first_card = choose_random_card(
        cards=["SA", "S10", "S9"],
        random_generator=random.Random(42),
    )
    second_card = choose_random_card(
        cards=["SA", "S10", "S9"],
        random_generator=random.Random(42),
    )

    assert first_card == second_card


def test_get_winning_legal_cards_returns_cards_that_win() -> None:
    winning_cards = get_winning_legal_cards(
        hand=["SA", "S9", "H10"],
        current_trick=["S7"],
        game_type="grand",
        player_index=1,
    )

    assert winning_cards == ["SA", "S9"]


def test_get_winning_legal_cards_returns_empty_list_when_no_card_wins() -> None:
    winning_cards = get_winning_legal_cards(
        hand=["S9", "S8", "H10"],
        current_trick=["SA"],
        game_type="grand",
        player_index=1,
    )

    assert winning_cards == []


def test_choose_basic_trick_play_card_wins_with_lowest_point_winning_card() -> None:
    selected_card = choose_basic_trick_play_card(
        hand=["SA", "S10", "S9"],
        current_trick=["S7"],
        game_type="grand",
        player_index=1,
    )

    assert selected_card == "S9"


def test_choose_basic_trick_play_card_plays_lowest_point_when_cannot_win() -> None:
    selected_card = choose_basic_trick_play_card(
        hand=["S9", "S8", "H10"],
        current_trick=["SA"],
        game_type="grand",
        player_index=1,
    )

    assert selected_card == "S9"


def test_choose_opponent_lead_card_by_lowest_point_policy() -> None:
    selected_card = choose_opponent_lead_card_by_policy(
        hand=["SA", "S10", "S9"],
        policy="lowest_point",
    )

    assert selected_card == "S9"


def test_choose_opponent_lead_card_by_highest_point_policy() -> None:
    selected_card = choose_opponent_lead_card_by_policy(
        hand=["SA", "S10", "S9"],
        policy="highest_point",
    )

    assert selected_card == "SA"


def test_choose_opponent_lead_card_by_random_policy_is_reproducible() -> None:
    first_card = choose_opponent_lead_card_by_policy(
        hand=["SA", "S10", "S9"],
        policy="random_legal",
        random_generator=random.Random(42),
    )
    second_card = choose_opponent_lead_card_by_policy(
        hand=["SA", "S10", "S9"],
        policy="random_legal",
        random_generator=random.Random(42),
    )

    assert first_card == second_card


def test_choose_opponent_response_card_by_lowest_point_policy() -> None:
    selected_card = choose_opponent_response_card_by_policy(
        hand=["SA", "S10", "S9", "H10"],
        current_trick=["S7"],
        game_type="grand",
        player_index=1,
        policy="lowest_point",
    )

    assert selected_card == "S9"


def test_choose_opponent_response_card_by_highest_point_policy() -> None:
    selected_card = choose_opponent_response_card_by_policy(
        hand=["SA", "S10", "S9", "H10"],
        current_trick=["S7"],
        game_type="grand",
        player_index=1,
        policy="highest_point",
    )

    assert selected_card == "SA"


def test_choose_opponent_response_card_by_basic_trick_play_policy() -> None:
    selected_card = choose_opponent_response_card_by_policy(
        hand=["SA", "S10", "S9", "H10"],
        current_trick=["S7"],
        game_type="grand",
        player_index=1,
        policy="basic_trick_play",
    )

    assert selected_card == "S9"