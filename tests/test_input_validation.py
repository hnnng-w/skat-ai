from skat_ai.input_validation import (
    validate_boolean,
    validate_cards,
    validate_completed_tricks,
    validate_current_trick,
    validate_game_type,
    validate_next_player,
    validate_no_duplicate_cards,
    validate_non_negative_integer,
    validate_optional_analysis_metadata,
    validate_optional_opponent_policies,
    validate_optional_player_profile,
    validate_optional_random_seed,
    validate_player_position,
    validate_player_role,
    validate_position_input,
    validate_positive_integer,
    validate_required_keys,
    validate_trick_leader,
    validate_trick_leader_matches_current_trick,
)


def test_validate_required_keys_accepts_complete_input() -> None:
    data = {
        "game_type": "grand",
        "player_role": "declarer",
        "hand": ["SA"],
        "current_trick": [],
        "left_hand_size": 5,
        "right_hand_size": 5,
        "sample_count": 100,
    }

    validate_required_keys(data)


def test_validate_required_keys_rejects_missing_keys() -> None:
    data = {
        "game_type": "grand",
        "player_role": "declarer",
    }

    try:
        validate_required_keys(data)
    except ValueError as error:
        assert "Missing required input keys" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_game_type_accepts_valid_game_type() -> None:
    validate_game_type("grand")


def test_validate_game_type_rejects_invalid_game_type() -> None:
    try:
        validate_game_type("invalid_game")
    except ValueError as error:
        assert "Invalid game type" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_player_role_accepts_valid_player_role() -> None:
    validate_player_role("declarer")


def test_validate_player_role_rejects_invalid_player_role() -> None:
    try:
        validate_player_role("attacker")
    except ValueError as error:
        assert "Invalid player role" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_cards_accepts_valid_cards() -> None:
    validate_cards(["SA", "S10", "D7"], "hand")


def test_validate_cards_rejects_invalid_cards() -> None:
    try:
        validate_cards(["SA", "S1O"], "hand")
    except ValueError as error:
        assert "Invalid cards in hand" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_no_duplicate_cards_accepts_unique_cards() -> None:
    data = {
        "hand": ["SA", "S10"],
        "current_trick": ["H7"],
        "played_cards": ["D7"],
        "skat": ["C7", "C8"],
    }

    validate_no_duplicate_cards(data)


def test_validate_no_duplicate_cards_rejects_duplicates() -> None:
    data = {
        "hand": ["SA", "S10"],
        "current_trick": ["SA"],
        "played_cards": [],
        "skat": [],
    }

    try:
        validate_no_duplicate_cards(data)
    except ValueError as error:
        assert "Duplicate known cards" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_current_trick_accepts_up_to_two_cards() -> None:
    validate_current_trick([])
    validate_current_trick(["SA"])
    validate_current_trick(["SA", "S10"])


def test_validate_current_trick_rejects_three_cards() -> None:
    try:
        validate_current_trick(["SA", "S10", "S9"])
    except ValueError as error:
        assert "at most 2 cards" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_positive_integer_accepts_positive_integer() -> None:
    validate_positive_integer(100, "sample_count")


def test_validate_positive_integer_rejects_zero() -> None:
    try:
        validate_positive_integer(0, "sample_count")
    except ValueError as error:
        assert "positive integer" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_optional_random_seed_accepts_integer_or_none() -> None:
    validate_optional_random_seed(42)
    validate_optional_random_seed(None)


def test_validate_optional_random_seed_rejects_string() -> None:
    try:
        validate_optional_random_seed("42")
    except ValueError as error:
        assert "random_seed" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_boolean_accepts_bool() -> None:
    validate_boolean(True, "use_basic_opponent_strategy")
    validate_boolean(False, "use_basic_opponent_strategy")


def test_validate_boolean_rejects_non_bool() -> None:
    try:
        validate_boolean("true", "use_basic_opponent_strategy")
    except ValueError as error:
        assert "boolean" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_position_input_accepts_valid_input() -> None:
    data = {
        "game_type": "grand",
        "player_role": "declarer",
        "hand": ["SA", "S10", "S9"],
        "current_trick": [],
        "played_cards": [],
        "skat": [],
        "left_hand_size": 5,
        "right_hand_size": 5,
        "sample_count": 100,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
    }

    validate_position_input(data)


def test_validate_position_input_rejects_invalid_input() -> None:
    data = {
        "game_type": "grand",
        "player_role": "declarer",
        "hand": ["SA", "S1O"],
        "current_trick": [],
        "played_cards": [],
        "skat": [],
        "left_hand_size": 5,
        "right_hand_size": 5,
        "sample_count": 100,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
    }

    try:
        validate_position_input(data)
    except ValueError as error:
        assert "Invalid cards" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_player_position_accepts_valid_player_position() -> None:
    validate_player_position("forehand")
    validate_player_position("middlehand")
    validate_player_position("rearhand")
    validate_player_position("unknown")


def test_validate_player_position_rejects_invalid_player_position() -> None:
    try:
        validate_player_position("button")
    except ValueError as error:
        assert "Invalid player position" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_trick_leader_accepts_valid_trick_leader() -> None:
    validate_trick_leader("me")
    validate_trick_leader("left")
    validate_trick_leader("right")
    validate_trick_leader("unknown")


def test_validate_trick_leader_rejects_invalid_trick_leader() -> None:
    try:
        validate_trick_leader("opponent")
    except ValueError as error:
        assert "Invalid trick leader" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_trick_leader_matches_empty_current_trick() -> None:
    validate_trick_leader_matches_current_trick("me", [])
    validate_trick_leader_matches_current_trick("unknown", [])


def test_validate_trick_leader_rejects_left_when_current_trick_is_empty() -> None:
    try:
        validate_trick_leader_matches_current_trick("left", [])
    except ValueError as error:
        assert "current_trick is empty" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_trick_leader_rejects_me_when_current_trick_is_not_empty() -> None:
    try:
        validate_trick_leader_matches_current_trick("me", ["S7"])
    except ValueError as error:
        assert "cannot be 'me'" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_position_input_accepts_position_fields() -> None:
    data = {
        "game_type": "grand",
        "player_role": "declarer",
        "player_position": "forehand",
        "trick_leader": "left",
        "hand": ["SA", "S10", "S9"],
        "current_trick": ["D7"],
        "played_cards": [],
        "skat": [],
        "left_hand_size": 5,
        "right_hand_size": 5,
        "sample_count": 100,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
    }

    validate_position_input(data)


def test_validate_position_input_rejects_invalid_position_fields() -> None:
    data = {
        "game_type": "grand",
        "player_role": "declarer",
        "player_position": "button",
        "trick_leader": "left",
        "hand": ["SA", "S10", "S9"],
        "current_trick": ["D7"],
        "played_cards": [],
        "skat": [],
        "left_hand_size": 5,
        "right_hand_size": 5,
        "sample_count": 100,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
    }

    try:
        validate_position_input(data)
    except ValueError as error:
        assert "Invalid player position" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_completed_tricks_accepts_valid_completed_trick() -> None:
    validate_completed_tricks(
        [
            {
                "cards": ["CA", "C10", "CK"],
                "winner_role": "declarer",
            }
        ]
    )


def test_validate_completed_tricks_rejects_invalid_card() -> None:
    try:
        validate_completed_tricks(
            [
                {
                    "cards": ["CA", "C1O", "CK"],
                    "winner_role": "declarer",
                }
            ]
        )
    except ValueError as error:
        assert "Invalid cards in completed_tricks" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_completed_tricks_rejects_invalid_winner_role() -> None:
    try:
        validate_completed_tricks(
            [
                {
                    "cards": ["CA", "C10", "CK"],
                    "winner_role": "unknown",
                }
            ]
        )
    except ValueError as error:
        assert "Invalid completed trick winner role" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_next_player_accepts_valid_next_player() -> None:
    validate_next_player("me")
    validate_next_player("left")
    validate_next_player("right")
    validate_next_player("unknown")


def test_validate_next_player_rejects_invalid_next_player() -> None:
    try:
        validate_next_player("dealer")
    except ValueError as error:
        assert "Invalid next player" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_non_negative_integer_accepts_zero_and_positive_integer() -> None:
    validate_non_negative_integer(0, "declarer_points")
    validate_non_negative_integer(10, "declarer_points")


def test_validate_non_negative_integer_rejects_negative_integer() -> None:
    try:
        validate_non_negative_integer(-1, "declarer_points")
    except ValueError as error:
        assert "non-negative integer" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_completed_tricks_accepts_players_and_winner_player() -> None:
    validate_completed_tricks(
        [
            {
                "cards": ["CA", "C10", "CK"],
                "players": ["left", "me", "right"],
                "winner_role": "defenders",
                "winner_player": "left",
            }
        ]
    )


def test_validate_completed_tricks_rejects_invalid_players() -> None:
    try:
        validate_completed_tricks(
            [
                {
                    "cards": ["CA", "C10", "CK"],
                    "players": ["left", "me", "dealer"],
                    "winner_role": "defenders",
                    "winner_player": "left",
                }
            ]
        )
    except ValueError as error:
        assert "Invalid completed trick players" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_completed_tricks_rejects_invalid_winner_player() -> None:
    try:
        validate_completed_tricks(
            [
                {
                    "cards": ["CA", "C10", "CK"],
                    "players": ["left", "me", "right"],
                    "winner_role": "defenders",
                    "winner_player": "dealer",
                }
            ]
        )
    except ValueError as error:
        assert "Invalid completed trick winner player" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")

def test_validate_optional_player_profile_accepts_valid_profile() -> None:
    validate_optional_player_profile(
        {
            "games_played": 1240,
            "solo_rate": 0.31,
            "solo_win_rate": 0.66,
        },
        "left_player_profile",
    )


def test_validate_optional_player_profile_rejects_negative_games_played() -> None:
    try:
        validate_optional_player_profile(
            {
                "games_played": -1,
            },
            "left_player_profile",
        )
    except ValueError as error:
        assert "games_played" in str(error)
        assert "non-negative integer" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_optional_player_profile_rejects_invalid_rate() -> None:
    try:
        validate_optional_player_profile(
            {
                "solo_rate": 1.5,
            },
            "left_player_profile",
        )
    except ValueError as error:
        assert "solo_rate" in str(error)
        assert "between 0 and 1" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_optional_analysis_metadata_accepts_valid_metadata() -> None:
    validate_optional_analysis_metadata(
        {
            "analysis_mode": "post_game_review",
            "skat_visibility": "known_post_game",
            "game_end_reason": "normal_completion",
            "left_player_profile": {
                "games_played": 1240,
                "solo_rate": 0.31,
            },
        }
    )


def test_validate_optional_analysis_metadata_rejects_invalid_analysis_mode() -> None:
    try:
        validate_optional_analysis_metadata(
            {
                "analysis_mode": "future_mode",
            }
        )
    except ValueError as error:
        assert "Invalid analysis mode" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")

def test_validate_optional_opponent_policies_accepts_valid_policies() -> None:
    validate_optional_opponent_policies(
        {
            "opponent_lead_policy": "highest_point",
            "opponent_response_policy": "basic_trick_play",
        }
    )


def test_validate_optional_opponent_policies_rejects_invalid_policy() -> None:
    try:
        validate_optional_opponent_policies(
            {
                "opponent_lead_policy": "reckless",
            }
        )
    except ValueError as error:
        assert "Invalid opponent card policy" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")