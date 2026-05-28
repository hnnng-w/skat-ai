from skat_ai.input_validation import (
    calculate_known_card_points_from_input,
    validate_boolean,
    validate_cards,
    validate_completed_tricks,
    validate_current_trick,
    validate_ended_game_requires_post_game_review,
    validate_game_type,
    validate_live_completed_trick_metadata,
    validate_live_decision_has_no_known_skat_cards,
    validate_live_decision_is_not_complete_game,
    validate_next_player,
    validate_no_duplicate_cards,
    validate_non_negative_integer,
    validate_optional_analysis_metadata,
    validate_optional_game_declaration,
    validate_optional_opponent_policies,
    validate_optional_player_profile,
    validate_optional_profile_preset_settings,
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

def test_validate_optional_opponent_policies_accepts_basic_defender_response() -> None:
    validate_optional_opponent_policies(
        {
            "opponent_response_policy": "basic_defender_response",
        }
    )

def test_validate_optional_opponent_policies_accepts_basic_defender_lead() -> None:
    validate_optional_opponent_policies(
        {
            "opponent_lead_policy": "basic_defender_lead",
        }
    )

def test_validate_optional_opponent_policies_accepts_preset() -> None:
    validate_optional_opponent_policies(
        {
            "opponent_policy_preset": "cautious_defender",
        }
    )


def test_validate_optional_opponent_policies_rejects_invalid_preset() -> None:
    try:
        validate_optional_opponent_policies(
            {
                "opponent_policy_preset": "reckless",
            }
        )
    except ValueError as error:
        assert "Invalid opponent policy preset" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")

def test_validate_optional_profile_preset_settings_accepts_boolean() -> None:
    validate_optional_profile_preset_settings(
        {
            "use_profile_presets": True,
        }
    )


def test_validate_optional_profile_preset_settings_rejects_non_boolean() -> None:
    try:
        validate_optional_profile_preset_settings(
            {
                "use_profile_presets": "yes",
            }
        )
    except ValueError as error:
        assert "use_profile_presets" in str(error)
        assert "boolean" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")

def test_validate_optional_game_declaration_accepts_valid_declaration() -> None:
    validate_optional_game_declaration(
        {
            "game_type": "grand",
            "hand": True,
            "schneider_announced": True,
            "matadors": 2,
        }
    )


def test_validate_optional_game_declaration_rejects_invalid_null_declaration() -> None:
    try:
        validate_optional_game_declaration(
            {
                "game_type": "null",
                "schneider_announced": True,
            }
        )
    except ValueError as error:
        assert "Null games cannot have schneider announced" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")

def test_validate_position_input_rejects_inconsistent_completed_trick_sequence() -> None:
    data = {
        "game_type": "grand",
        "player_role": "declarer",
        "player_position": "middlehand",
        "trick_leader": "left",
        "hand": ["SA", "S10", "S9"],
        "current_trick": ["S7"],
        "played_cards": [],
        "completed_tricks": [
            {
                "cards": ["CJ", "SJ", "DJ"],
                "players": ["me", "left", "right"],
                "winner_role": "declarer",
                "winner_player": "me",
            }
        ],
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "me",
        "skat": [],
        "left_hand_size": 3,
        "right_hand_size": 3,
        "sample_count": 100,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
    }

    try:
        validate_position_input(data)
    except ValueError as error:
        assert "trick_leader is inconsistent" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_position_input_rejects_inconsistent_winner_role() -> None:
    data = {
        "game_type": "grand",
        "player_role": "declarer",
        "player_position": "middlehand",
        "trick_leader": "me",
        "hand": ["SA", "S10", "S9"],
        "current_trick": [],
        "played_cards": [],
        "completed_tricks": [
            {
                "cards": ["CJ", "SJ", "DJ"],
                "players": ["me", "left", "right"],
                "winner_role": "defenders",
                "winner_player": "me",
            }
        ],
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "me",
        "skat": [],
        "left_hand_size": 3,
        "right_hand_size": 3,
        "sample_count": 100,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
    }

    try:
        validate_position_input(data)
    except ValueError as error:
        assert "winner_role is inconsistent" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_position_input_rejects_rule_wrong_completed_trick_winner() -> None:
    data = {
        "game_type": "grand",
        "player_role": "unknown",
        "player_position": "middlehand",
        "trick_leader": "unknown",
        "hand": ["S10", "S9", "D7"],
        "current_trick": [],
        "played_cards": [],
        "completed_tricks": [
            {
                "cards": ["S7", "S8", "SA"],
                "players": ["left", "right", "me"],
                "winner_role": "declarer",
                "winner_player": "left",
            }
        ],
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "unknown",
        "skat": [],
        "left_hand_size": 3,
        "right_hand_size": 3,
        "sample_count": 100,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
    }

    try:
        validate_position_input(data)
    except ValueError as error:
        assert "winner_player is inconsistent with trick rules" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")

def test_validate_position_input_rejects_zero_bid_value() -> None:
    data = {
        "game_type": "grand",
        "player_role": "declarer",
        "player_position": "middlehand",
        "trick_leader": "unknown",
        "hand": ["SA", "S10", "S9"],
        "current_trick": [],
        "played_cards": [],
        "completed_tricks": [],
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "unknown",
        "skat": [],
        "left_hand_size": 3,
        "right_hand_size": 3,
        "sample_count": 100,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
        "bid_value": 0,
    }

    try:
        validate_position_input(data)
    except ValueError as error:
        assert "bid_value must be a positive integer" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")

def test_validate_position_input_rejects_non_integer_bid_value() -> None:
    data = {
        "game_type": "grand",
        "player_role": "declarer",
        "player_position": "middlehand",
        "trick_leader": "unknown",
        "hand": ["SA", "S10", "S9"],
        "current_trick": [],
        "played_cards": [],
        "completed_tricks": [],
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "unknown",
        "skat": [],
        "left_hand_size": 3,
        "right_hand_size": 3,
        "sample_count": 100,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
        "bid_value": "72",
    }

    try:
        validate_position_input(data)
    except ValueError as error:
        assert "bid_value must be a positive integer" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")

def test_validate_position_input_accepts_known_performance_rating_system() -> None:
    data = {
        "game_type": "grand",
        "player_role": "declarer",
        "player_position": "middlehand",
        "trick_leader": "unknown",
        "hand": ["SA", "S10", "S9"],
        "current_trick": [],
        "played_cards": [],
        "completed_tricks": [],
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "unknown",
        "skat": [],
        "left_hand_size": 3,
        "right_hand_size": 3,
        "sample_count": 100,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
        "performance_rating_system": "isko_list",
    }

    validate_position_input(data)

def test_validate_position_input_rejects_unknown_performance_rating_system() -> None:
    data = {
        "game_type": "grand",
        "player_role": "declarer",
        "player_position": "middlehand",
        "trick_leader": "unknown",
        "hand": ["SA", "S10", "S9"],
        "current_trick": [],
        "played_cards": [],
        "completed_tricks": [],
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "unknown",
        "skat": [],
        "left_hand_size": 3,
        "right_hand_size": 3,
        "sample_count": 100,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
        "performance_rating_system": "unknown_system",
    }

    try:
        validate_position_input(data)
    except ValueError as error:
        assert "Unknown performance rating system" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")

def test_validate_position_input_rejects_live_known_post_game_skat() -> None:
    data = {
        "game_type": "grand",
        "player_role": "declarer",
        "player_position": "middlehand",
        "trick_leader": "unknown",
        "hand": ["SA", "S10", "S9"],
        "current_trick": [],
        "played_cards": [],
        "completed_tricks": [],
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "unknown",
        "skat": [],
        "left_hand_size": 3,
        "right_hand_size": 3,
        "sample_count": 100,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
        "analysis_mode": "live_decision",
        "skat_visibility": "known_post_game",
    }

    try:
        validate_position_input(data)
    except ValueError as error:
        assert "known_post_game" in str(error)
        assert "post_game_review" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")

def test_validate_live_decision_has_no_known_skat_cards_accepts_live_empty_skat() -> None:
    validate_live_decision_has_no_known_skat_cards(
        analysis_mode="live_decision",
        skat=[],
    )


def test_validate_live_decision_has_no_known_skat_cards_accepts_post_game_known_skat() -> None:
    validate_live_decision_has_no_known_skat_cards(
        analysis_mode="post_game_review",
        skat=["C7", "D8"],
    )


def test_validate_live_decision_has_no_known_skat_cards_rejects_live_known_skat() -> None:
    try:
        validate_live_decision_has_no_known_skat_cards(
            analysis_mode="live_decision",
            skat=["C7", "D8"],
        )
    except ValueError as error:
        assert "Known skat cards" in str(error)
        assert "live_decision" in str(error)
        assert "post_game_review" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")
    
def test_validate_position_input_rejects_live_decision_with_known_skat_cards() -> None:
    data = {
        "game_type": "grand",
        "player_role": "declarer",
        "player_position": "middlehand",
        "trick_leader": "unknown",
        "hand": ["SA", "S10", "S9"],
        "current_trick": [],
        "played_cards": [],
        "completed_tricks": [],
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "unknown",
        "skat": ["C7", "D8"],
        "left_hand_size": 3,
        "right_hand_size": 3,
        "sample_count": 100,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
        "analysis_mode": "live_decision",
        "skat_visibility": "unknown",
    }

    try:
        validate_position_input(data)
    except ValueError as error:
        assert "Known skat cards" in str(error)
        assert "live_decision" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")

def test_validate_position_input_accepts_post_game_review_with_known_skat_cards() -> None:
    data = {
        "game_type": "grand",
        "player_role": "declarer",
        "player_position": "middlehand",
        "trick_leader": "unknown",
        "hand": ["SA", "S10", "S9"],
        "current_trick": [],
        "played_cards": [],
        "completed_tricks": [],
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "unknown",
        "skat": ["C7", "D8"],
        "left_hand_size": 3,
        "right_hand_size": 3,
        "sample_count": 100,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
        "analysis_mode": "post_game_review",
        "skat_visibility": "known_post_game",
    }

    validate_position_input(data)

def test_live_trick_accepts_without_winner_metadata() -> None:
    validate_live_completed_trick_metadata(
        analysis_mode="live_decision",
        completed_tricks=[
            {
                "cards": ["CJ", "SJ", "DJ"],
            }
        ],
    )


def test_live_trick_accepts_players_and_winner() -> None:
    validate_live_completed_trick_metadata(
        analysis_mode="live_decision",
        completed_tricks=[
            {
                "cards": ["CJ", "SJ", "DJ"],
                "players": ["me", "left", "right"],
                "winner_player": "me",
                "winner_role": "declarer",
            }
        ],
    )


def test_post_game_trick_accepts_winner_without_players() -> None:
    validate_live_completed_trick_metadata(
        analysis_mode="post_game_review",
        completed_tricks=[
            {
                "cards": ["CJ", "SJ", "DJ"],
                "winner_player": "me",
                "winner_role": "declarer",
            }
        ],
    )


def test_live_trick_rejects_winner_player_without_players() -> None:
    try:
        validate_live_completed_trick_metadata(
            analysis_mode="live_decision",
            completed_tricks=[
                {
                    "cards": ["CJ", "SJ", "DJ"],
                    "winner_player": "me",
                }
            ],
        )
    except ValueError as error:
        assert "winner_player" in str(error)
        assert "players" in str(error)
        assert "live_decision" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_live_trick_rejects_winner_role_without_players() -> None:
    try:
        validate_live_completed_trick_metadata(
            analysis_mode="live_decision",
            completed_tricks=[
                {
                    "cards": ["CJ", "SJ", "DJ"],
                    "winner_role": "declarer",
                }
            ],
        )
    except ValueError as error:
        assert "winner_role" in str(error)
        assert "players" in str(error)
        assert "live_decision" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_position_input_rejects_live_winner_player_without_players() -> None:
    data = {
        "game_type": "grand",
        "player_role": "declarer",
        "player_position": "middlehand",
        "trick_leader": "unknown",
        "hand": ["SA", "S10", "S9"],
        "current_trick": [],
        "played_cards": [],
        "completed_tricks": [
            {
                "cards": ["CJ", "SJ", "DJ"],
                "winner_player": "me",
                "winner_role": "declarer",
            }
        ],
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "unknown",
        "skat": [],
        "left_hand_size": 3,
        "right_hand_size": 3,
        "sample_count": 100,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
        "analysis_mode": "live_decision",
        "skat_visibility": "unknown",
    }

    try:
        validate_position_input(data)
    except ValueError as error:
        assert "winner_player" in str(error)
        assert "players" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")
    

def test_position_input_accepts_live_trick_with_players_and_winner() -> None:
    data = {
        "game_type": "grand",
        "player_role": "declarer",
        "player_position": "middlehand",
        "trick_leader": "me",
        "hand": ["SA", "S10", "S9"],
        "current_trick": [],
        "played_cards": [],
        "completed_tricks": [
            {
                "cards": ["CJ", "SJ", "DJ"],
                "players": ["me", "left", "right"],
                "winner_player": "me",
                "winner_role": "declarer",
            }
        ],
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "unknown",
        "skat": [],
        "left_hand_size": 3,
        "right_hand_size": 3,
        "sample_count": 100,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
        "analysis_mode": "live_decision",
        "skat_visibility": "unknown",
    }

    validate_position_input(data)


def test_ended_game_rule_accepts_live_not_ended() -> None:
    validate_ended_game_requires_post_game_review(
        analysis_mode="live_decision",
        game_end_reason="not_ended",
    )


def test_ended_game_rule_accepts_post_game_normal_completion() -> None:
    validate_ended_game_requires_post_game_review(
        analysis_mode="post_game_review",
        game_end_reason="normal_completion",
    )


def test_ended_game_rule_accepts_post_game_claim() -> None:
    validate_ended_game_requires_post_game_review(
        analysis_mode="post_game_review",
        game_end_reason="declarer_claimed_remaining_tricks",
    )


def test_ended_game_rule_rejects_live_normal_completion() -> None:
    try:
        validate_ended_game_requires_post_game_review(
            analysis_mode="live_decision",
            game_end_reason="normal_completion",
        )
    except ValueError as error:
        assert "game_end_reason" in str(error)
        assert "not_ended" in str(error)
        assert "post_game_review" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_ended_game_rule_rejects_live_claim() -> None:
    try:
        validate_ended_game_requires_post_game_review(
            analysis_mode="live_decision",
            game_end_reason="declarer_claimed_remaining_tricks",
        )
    except ValueError as error:
        assert "game_end_reason" in str(error)
        assert "post_game_review" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")
    

def test_live_decision_accepts_incomplete_known_points() -> None:
    validate_live_decision_is_not_complete_game(
        analysis_mode="live_decision",
        known_card_points=119,
    )


def test_post_game_accepts_complete_known_points() -> None:
    validate_live_decision_is_not_complete_game(
        analysis_mode="post_game_review",
        known_card_points=120,
    )


def test_live_decision_rejects_complete_known_points() -> None:
    try:
        validate_live_decision_is_not_complete_game(
            analysis_mode="live_decision",
            known_card_points=120,
        )
    except ValueError as error:
        assert "live_decision" in str(error)
        assert "120" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_calculate_known_card_points_from_input_combines_explicit_and_tricks() -> None:
    assert calculate_known_card_points_from_input(
        {
            "declarer_points": 20,
            "defender_points": 10,
            "completed_tricks": [
                {
                    "cards": ["CA", "C10", "CK"],
                }
            ],
        }
    ) == 55


def test_validate_position_input_rejects_live_normal_completion() -> None:
    data = {
        "game_type": "grand",
        "player_role": "declarer",
        "player_position": "middlehand",
        "trick_leader": "unknown",
        "hand": ["SA", "S10", "S9"],
        "current_trick": [],
        "played_cards": [],
        "completed_tricks": [],
        "declarer_points": 70,
        "defender_points": 50,
        "next_player": "unknown",
        "skat": [],
        "left_hand_size": 3,
        "right_hand_size": 3,
        "sample_count": 100,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
        "analysis_mode": "live_decision",
        "skat_visibility": "unknown",
        "game_end_reason": "normal_completion",
    }

    try:
        validate_position_input(data)
    except ValueError as error:
        assert "game_end_reason" in str(error)
        assert "not_ended" in str(error)
        assert "post_game_review" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_position_input_rejects_live_complete_points() -> None:
    data = {
        "game_type": "grand",
        "player_role": "declarer",
        "player_position": "middlehand",
        "trick_leader": "unknown",
        "hand": ["SA", "S10", "S9"],
        "current_trick": [],
        "played_cards": [],
        "completed_tricks": [],
        "declarer_points": 70,
        "defender_points": 50,
        "next_player": "unknown",
        "skat": [],
        "left_hand_size": 3,
        "right_hand_size": 3,
        "sample_count": 100,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
        "analysis_mode": "live_decision",
        "skat_visibility": "unknown",
        "game_end_reason": "not_ended",
    }

    try:
        validate_position_input(data)
    except ValueError as error:
        assert "live_decision" in str(error)
        assert "120" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_position_input_accepts_post_game_complete_points() -> None:
    data = {
        "game_type": "grand",
        "player_role": "declarer",
        "player_position": "middlehand",
        "trick_leader": "unknown",
        "hand": ["SA", "S10", "S9"],
        "current_trick": [],
        "played_cards": [],
        "completed_tricks": [],
        "declarer_points": 70,
        "defender_points": 50,
        "next_player": "unknown",
        "skat": [],
        "left_hand_size": 3,
        "right_hand_size": 3,
        "sample_count": 100,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
        "analysis_mode": "post_game_review",
        "skat_visibility": "unknown",
        "game_end_reason": "normal_completion",
    }

    validate_position_input(data)