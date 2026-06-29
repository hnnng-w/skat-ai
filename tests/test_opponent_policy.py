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
    determine_current_trick_winner_index,
    get_losing_legal_cards,
    get_non_trump_cards,
    get_opponent_policy_settings_for_player,
    get_partner_safe_legal_cards,
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


def test_determine_current_trick_winner_index_returns_zero_for_one_card() -> None:
    assert determine_current_trick_winner_index(["CJ"], "spades") == 0


def test_determine_current_trick_winner_index_rejects_empty_cards() -> None:
    try:
        determine_current_trick_winner_index([], "spades")
    except ValueError as error:
        assert "empty trick" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_determine_current_trick_winner_index_keeps_earliest_card_on_tie() -> None:
    assert determine_current_trick_winner_index(["SA", "SA"], "grand") == 0


def test_suit_game_jack_beats_suit_trump_ace_when_jack_is_currently_winning() -> None:
    assert determine_current_trick_winner_index(["CJ", "SA"], "spades") == 0


def test_suit_game_jack_beats_suit_trump_ace_when_jack_is_played_second() -> None:
    assert determine_current_trick_winner_index(["SA", "CJ"], "spades") == 1


def test_suit_game_jack_order_uses_canonical_order() -> None:
    assert determine_current_trick_winner_index(["SJ", "CJ"], "spades") == 1
    assert determine_current_trick_winner_index(["HJ", "SJ"], "spades") == 1
    assert determine_current_trick_winner_index(["DJ", "HJ"], "spades") == 1


def test_suit_game_lowest_jack_beats_suit_trump_ace() -> None:
    assert determine_current_trick_winner_index(["DJ", "SA"], "spades") == 0
    assert determine_current_trick_winner_index(["SA", "DJ"], "spades") == 1


def test_suit_game_non_jack_trump_ordering() -> None:
    assert determine_current_trick_winner_index(["S10", "SA"], "spades") == 1


def test_suit_game_non_trump_following_suit_ordering() -> None:
    assert determine_current_trick_winner_index(["H10", "HA"], "spades") == 1


def test_grand_jack_order_remains_canonical() -> None:
    assert determine_current_trick_winner_index(["SJ", "CJ"], "grand") == 1
    assert determine_current_trick_winner_index(["HJ", "SJ"], "grand") == 1
    assert determine_current_trick_winner_index(["DJ", "HJ"], "grand") == 1


def test_grand_non_jacks_follow_lead_suit() -> None:
    assert determine_current_trick_winner_index(["S10", "SA"], "grand") == 1


def test_grand_off_suit_non_jacks_do_not_win() -> None:
    assert determine_current_trick_winner_index(["S10", "HA"], "grand") == 0


def test_null_rank_order_remains_canonical() -> None:
    assert determine_current_trick_winner_index(["C10", "CJ"], "null") == 1


def test_null_treats_jacks_as_non_trump() -> None:
    assert determine_current_trick_winner_index(["S7", "CJ"], "null") == 0


def test_null_off_suit_cards_do_not_beat_lead_suit_card() -> None:
    assert determine_current_trick_winner_index(["C7", "SA"], "null") == 0


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


def test_get_winning_legal_cards_does_not_treat_suit_trump_ace_as_winning_over_jack(
) -> None:
    winning_cards = get_winning_legal_cards(
        hand=["SA"],
        current_trick=["CJ"],
        game_type="spades",
        player_index=1,
    )

    assert winning_cards == []


def test_get_winning_legal_cards_treats_jack_as_winning_over_suit_trump_ace() -> None:
    winning_cards = get_winning_legal_cards(
        hand=["CJ"],
        current_trick=["SA"],
        game_type="spades",
        player_index=1,
    )

    assert winning_cards == ["CJ"]


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
        current_trick=["DA"],
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
        current_trick=["DA"],
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


def test_get_partner_safe_legal_cards_keeps_partner_winning() -> None:
    safe_cards = get_partner_safe_legal_cards(
        hand=["DK", "DQ", "DA"],
        current_trick=["D10"],
        game_type="grand",
        partner_index=0,
    )

    assert safe_cards == ["DK", "DQ"]


def test_get_partner_safe_legal_cards_keeps_partner_jack_winning_over_suit_trump(
) -> None:
    safe_cards = get_partner_safe_legal_cards(
        hand=["SA"],
        current_trick=["CJ"],
        game_type="spades",
        partner_index=0,
    )

    assert safe_cards == ["SA"]


def test_choose_basic_defender_response_smears_without_overtaking_partner() -> None:
    selected_card = choose_basic_defender_response_card(
        hand=["DK", "DQ", "DA"],
        current_trick=["D10"],
        game_type="grand",
        player_index=1,
        partner_currently_winning=True,
    )

    assert selected_card == "DK"


def test_choose_basic_defender_response_uses_weakest_card_for_equal_point_safe_smear(
) -> None:
    selected_card = choose_basic_defender_response_card(
        hand=["SJ", "HJ", "DJ"],
        current_trick=["CJ"],
        game_type="grand",
        player_index=1,
        partner_currently_winning=True,
    )

    assert selected_card == "DJ"


def test_choose_basic_defender_response_minimizes_forced_partner_overtake() -> None:
    selected_card = choose_basic_defender_response_card(
        hand=["DA", "D10", "DK"],
        current_trick=["D7"],
        game_type="grand",
        player_index=1,
        partner_currently_winning=True,
    )

    assert selected_card == "DK"


def test_choose_basic_defender_response_uses_weakest_card_when_forced_to_overtake_partner(
) -> None:
    selected_card = choose_basic_defender_response_card(
        hand=["CJ", "SJ", "HJ"],
        current_trick=["DJ"],
        game_type="grand",
        player_index=1,
        partner_currently_winning=True,
    )

    assert selected_card == "HJ"


def test_get_losing_legal_cards_returns_cards_that_do_not_win() -> None:
    losing_cards = get_losing_legal_cards(
        hand=["C10", "CK", "C9"],
        current_trick=["CA"],
        game_type="grand",
        player_index=1,
    )

    assert losing_cards == ["C10", "CK", "C9"]


def test_get_losing_legal_cards_does_not_classify_jack_over_suit_trump_as_losing(
) -> None:
    losing_cards = get_losing_legal_cards(
        hand=["CJ"],
        current_trick=["SA"],
        game_type="spades",
        player_index=1,
    )

    assert losing_cards == []


def test_choose_basic_defender_response_discards_lowest_points_when_unable_to_win() -> None:
    selected_card = choose_basic_defender_response_card(
        hand=["C10", "CK", "C9"],
        current_trick=["CA"],
        game_type="grand",
        player_index=1,
        partner_currently_winning=False,
    )

    assert selected_card == "C9"


def test_choose_basic_defender_response_still_wins_when_possible() -> None:
    selected_card = choose_basic_defender_response_card(
        hand=["CA", "C9", "D7"],
        current_trick=["C10"],
        game_type="grand",
        player_index=1,
        partner_currently_winning=False,
    )

    assert selected_card == "CA"


def test_choose_basic_defender_response_conserves_trump_on_zero_point_second_hand_trick(
) -> None:
    selected_card = choose_basic_defender_response_card(
        hand=["CJ", "D7", "H9"],
        current_trick=["S7"],
        game_type="grand",
        player_index=1,
        partner_currently_winning=False,
    )

    assert selected_card == "D7"


def test_choose_basic_defender_response_conserves_suit_game_trump_on_zero_point_second_hand_trick(
) -> None:
    selected_card = choose_basic_defender_response_card(
        hand=["S7", "D7", "C9"],
        current_trick=["H7"],
        game_type="spades",
        player_index=1,
        partner_currently_winning=False,
    )

    assert selected_card == "D7"


def test_choose_basic_defender_response_wins_on_point_bearing_second_hand_lead(
) -> None:
    selected_card = choose_basic_defender_response_card(
        hand=["HJ", "DJ", "D7"],
        current_trick=["S10"],
        game_type="grand",
        player_index=1,
        partner_currently_winning=False,
    )

    assert selected_card == "DJ"


def test_choose_basic_defender_response_does_not_conserve_trump_in_rear_hand(
) -> None:
    selected_card = choose_basic_defender_response_card(
        hand=["DJ", "D7", "C9"],
        current_trick=["S7", "H8"],
        game_type="grand",
        player_index=2,
        partner_currently_winning=False,
    )

    assert selected_card == "DJ"


def test_choose_basic_defender_response_uses_weakest_card_for_equal_point_win(
) -> None:
    selected_card = choose_basic_defender_response_card(
        hand=["CJ", "SJ", "HJ"],
        current_trick=["DJ"],
        game_type="grand",
        player_index=1,
        partner_currently_winning=False,
    )

    assert selected_card == "HJ"


def test_get_non_trump_cards_filters_trumps_in_suit_game() -> None:
    non_trump_cards = get_non_trump_cards(
        cards=["SJ", "SA", "HA", "D7", "C9"],
        game_type="spades",
    )

    assert non_trump_cards == ["HA", "D7", "C9"]


def test_get_non_trump_cards_filters_jacks_in_grand() -> None:
    non_trump_cards = get_non_trump_cards(
        cards=["CJ", "SJ", "SA", "D7"],
        game_type="grand",
    )

    assert non_trump_cards == ["SA", "D7"]


def test_choose_basic_defender_lead_card_prefers_lowest_point_non_trump() -> None:
    selected_card = choose_basic_defender_lead_card(
        hand=["SJ", "SA", "HA", "D7"],
        game_type="spades",
    )

    assert selected_card == "D7"


def test_choose_basic_defender_lead_card_falls_back_to_lowest_point_when_only_trumps() -> None:
    selected_card = choose_basic_defender_lead_card(
        hand=["SJ", "SA", "S9"],
        game_type="spades",
    )

    assert selected_card == "S9"
