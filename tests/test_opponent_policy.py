import random

from skat_ai.opponent_policy import (
    choose_basic_defender_lead_card,
    choose_basic_defender_response_card,
    choose_basic_trick_play_card,
    choose_highest_point_card,
    choose_lowest_point_card,
    choose_opponent_lead_card_by_policy,
    choose_opponent_response_card_by_policy,
    choose_random_card,
    get_opponent_policy_settings_for_player,
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

def test_validate_opponent_card_policy_accepts_basic_defender_response() -> None:
    validate_opponent_card_policy("basic_defender_response")


def test_choose_basic_defender_response_smears_when_partner_is_winning() -> None:
    selected_card = choose_basic_defender_response_card(
        hand=["D10", "D9", "H7"],
        current_trick=["D7"],
        game_type="grand",
        player_index=1,
        partner_currently_winning=True,
    )

    assert selected_card == "D10"


def test_choose_basic_defender_response_uses_basic_play_when_partner_is_not_winning() -> None:
    selected_card = choose_basic_defender_response_card(
        hand=["D10", "D9", "H7"],
        current_trick=["DA"],
        game_type="grand",
        player_index=1,
        partner_currently_winning=False,
    )

    assert selected_card == "D9"


def test_choose_opponent_response_card_by_basic_defender_response_policy_smears() -> None:
    selected_card = choose_opponent_response_card_by_policy(
        hand=["D10", "D9", "H7"],
        current_trick=["D7"],
        game_type="grand",
        player_index=1,
        policy="basic_defender_response",
        partner_currently_winning=True,
    )

    assert selected_card == "D10"


def test_choose_opponent_lead_card_by_basic_defender_response_policy() -> None:
    selected_card = choose_opponent_lead_card_by_policy(
        hand=["SA", "S10", "S9"],
        policy="basic_defender_response",
    )

    assert selected_card == "S9"

def test_validate_opponent_card_policy_accepts_basic_defender_lead() -> None:
    validate_opponent_card_policy("basic_defender_lead")


def test_choose_basic_defender_lead_prefers_low_point_non_trump() -> None:
    selected_card = choose_basic_defender_lead_card(
        hand=["CJ", "SA", "S9", "H10", "D7"],
        game_type="grand",
    )

    assert selected_card == "S9"


def test_choose_basic_defender_lead_falls_back_to_lowest_point_when_only_trumps() -> None:
    selected_card = choose_basic_defender_lead_card(
        hand=["CJ", "SJ", "HJ"],
        game_type="grand",
    )

    assert selected_card == "CJ"


def test_choose_opponent_lead_card_by_basic_defender_lead_policy() -> None:
    selected_card = choose_opponent_lead_card_by_policy(
        hand=["CJ", "SA", "S9", "H10", "D7"],
        policy="basic_defender_lead",
        game_type="grand",
    )

    assert selected_card == "S9"


def test_choose_opponent_response_card_by_basic_defender_lead_policy_falls_back_to_basic_play(
) -> None:
    selected_card = choose_opponent_response_card_by_policy(
        hand=["SA", "S10", "S9", "H10"],
        current_trick=["S7"],
        game_type="grand",
        player_index=1,
        policy="basic_defender_lead",
    )

    assert selected_card == "S9"


def test_get_opponent_policy_settings_for_player_returns_left_settings() -> None:
    global_settings = {
        "opponent_lead_policy": "lowest_point",
        "opponent_response_policy": "lowest_point",
    }
    left_settings = {
        "opponent_lead_policy": "highest_point",
        "opponent_response_policy": "basic_trick_play",
    }
    right_settings = {
        "opponent_lead_policy": "lowest_point",
        "opponent_response_policy": "highest_point",
    }

    assert get_opponent_policy_settings_for_player(
        player="left",
        opponent_policy_settings=global_settings,
        left_opponent_policy_settings=left_settings,
        right_opponent_policy_settings=right_settings,
    ) == left_settings


def test_get_opponent_policy_settings_for_player_returns_right_settings() -> None:
    global_settings = {
        "opponent_lead_policy": "lowest_point",
        "opponent_response_policy": "lowest_point",
    }
    left_settings = {
        "opponent_lead_policy": "highest_point",
        "opponent_response_policy": "basic_trick_play",
    }
    right_settings = {
        "opponent_lead_policy": "lowest_point",
        "opponent_response_policy": "highest_point",
    }

    assert get_opponent_policy_settings_for_player(
        player="right",
        opponent_policy_settings=global_settings,
        left_opponent_policy_settings=left_settings,
        right_opponent_policy_settings=right_settings,
    ) == right_settings


def test_get_opponent_policy_settings_for_player_falls_back_to_global() -> None:
    global_settings = {
        "opponent_lead_policy": "lowest_point",
        "opponent_response_policy": "lowest_point",
    }

    assert get_opponent_policy_settings_for_player(
        player="unknown",
        opponent_policy_settings=global_settings,
    ) == global_settings