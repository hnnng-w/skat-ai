from skat_ai.input_loader import (
    build_game_state_from_input,
    get_analysis_metadata_from_input,
    get_game_declaration_from_input,
    get_left_opponent_policy_settings_from_input,
    get_list_analysis_results_from_input,
    get_list_game_contributions_from_input,
    get_list_performance_input_from_input,
    get_opponent_policy_settings_from_input,
    get_performance_rating_system_from_input,
    get_profile_preset_settings_from_input,
    get_right_opponent_policy_settings_from_input,
    get_simulation_settings_from_input,
)


def test_build_game_state_from_input() -> None:
    data = {
        "game_type": "grand",
        "player_role": "declarer",
        "player_position": "forehand",
        "trick_leader": "left",
        "hand": ["SA", "S10", "S9"],
        "current_trick": ["D7"],
        "played_cards": ["H7"],
        "skat": ["C7", "D8"],
        "completed_tricks": [
            {
                "cards": ["CA", "C10", "CK"],
                "winner_role": "declarer",
            }
        ],
        "declarer_points": 10,
        "defender_points": 5,
        "next_player": "right",
    }

    state = build_game_state_from_input(data)

    assert state.game_type == "grand"
    assert state.player_role == "declarer"
    assert state.declarer_player == "me"
    assert state.player_position == "forehand"
    assert state.trick_leader == "left"
    assert state.hand == ["SA", "S10", "S9"]
    assert state.current_trick == ["D7"]
    assert state.played_cards == ["H7"]
    assert state.skat == ["C7", "D8"]
    assert state.completed_tricks == [
        {
            "cards": ["CA", "C10", "CK"],
            "winner_role": "declarer",
        }
    ]
    assert state.declarer_points == 10
    assert state.defender_points == 5
    assert state.next_player == "right"


def test_build_game_state_from_input_uses_defaults_for_optional_lists() -> None:
    data = {
        "game_type": "grand",
        "player_role": "declarer",
        "hand": ["SA", "S10", "S9"],
        "current_trick": [],
    }

    state = build_game_state_from_input(data)

    assert state.played_cards == []
    assert state.skat == []
    assert state.player_position == "unknown"
    assert state.declarer_player == "me"
    assert state.trick_leader == "unknown"
    assert state.completed_tricks == []
    assert state.declarer_points == 0
    assert state.defender_points == 0
    assert state.next_player == "unknown"


def test_build_game_state_from_input_loads_defender_declarer_identity() -> None:
    data = {
        "game_type": "grand",
        "player_role": "defender",
        "declarer_player": "right",
        "hand": ["SA", "S10", "S9"],
        "current_trick": [],
    }

    state = build_game_state_from_input(data)

    assert state.declarer_player == "right"


def test_get_simulation_settings_from_input() -> None:
    data = {
        "left_hand_size": 5,
        "right_hand_size": 5,
        "sample_count": 1000,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
    }

    settings = get_simulation_settings_from_input(data)

    assert settings == {
        "left_hand_size": 5,
        "right_hand_size": 5,
        "sample_count": 1000,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
    }


def test_get_simulation_settings_from_input_uses_default_strategy_flag() -> None:
    data = {
        "left_hand_size": 5,
        "right_hand_size": 5,
        "sample_count": 1000,
        "random_seed": 42,
    }

    settings = get_simulation_settings_from_input(data)

    assert settings["use_basic_opponent_strategy"] is True

def test_get_analysis_metadata_from_input_defaults() -> None:
    metadata = get_analysis_metadata_from_input({})

    assert metadata.strategic_metadata.analysis_mode == "live_decision"
    assert metadata.strategic_metadata.skat_visibility == "unknown"
    assert metadata.strategic_metadata.game_end_reason == "not_ended"


def test_get_analysis_metadata_from_input_reads_metadata() -> None:
    metadata = get_analysis_metadata_from_input(
        {
            "analysis_mode": "post_game_review",
            "skat_visibility": "known_post_game",
            "game_end_reason": "normal_completion",
            "left_player_profile": {
                "games_played": 1240,
                "solo_rate": 0.31,
            },
            "right_player_profile": {
                "games_played": 520,
                "defender_win_rate": 0.49,
            },
        }
    )

    assert metadata.strategic_metadata.analysis_mode == "post_game_review"
    assert metadata.left_player_profile.games_played == 1240
    assert metadata.right_player_profile.defender_win_rate == 0.49

def test_get_opponent_policy_settings_from_input_defaults() -> None:
    settings = get_opponent_policy_settings_from_input({})

    assert settings == {
        "opponent_lead_policy": "lowest_point",
        "opponent_response_policy": "lowest_point",
    }


def test_get_opponent_policy_settings_from_input_reads_values() -> None:
    settings = get_opponent_policy_settings_from_input(
        {
            "opponent_lead_policy": "highest_point",
            "opponent_response_policy": "basic_trick_play",
        }
    )

    assert settings == {
        "opponent_lead_policy": "highest_point",
        "opponent_response_policy": "basic_trick_play",
    }

def test_get_opponent_policy_settings_from_input_reads_basic_defender_response() -> None:
    settings = get_opponent_policy_settings_from_input(
        {
            "opponent_lead_policy": "lowest_point",
            "opponent_response_policy": "basic_defender_response",
        }
    )

    assert settings == {
        "opponent_lead_policy": "lowest_point",
        "opponent_response_policy": "basic_defender_response",
    }

def test_get_opponent_policy_settings_from_input_reads_basic_defender_lead() -> None:
    settings = get_opponent_policy_settings_from_input(
        {
            "opponent_lead_policy": "basic_defender_lead",
            "opponent_response_policy": "basic_defender_response",
        }
    )

    assert settings == {
        "opponent_lead_policy": "basic_defender_lead",
        "opponent_response_policy": "basic_defender_response",
    }

def test_get_opponent_policy_settings_from_input_applies_preset() -> None:
    settings = get_opponent_policy_settings_from_input(
        {
            "opponent_policy_preset": "cautious_defender",
        }
    )

    assert settings == {
        "opponent_lead_policy": "basic_defender_lead",
        "opponent_response_policy": "basic_defender_response",
    }


def test_get_opponent_policy_settings_from_input_explicit_values_override_preset() -> None:
    settings = get_opponent_policy_settings_from_input(
        {
            "opponent_policy_preset": "cautious_defender",
            "opponent_lead_policy": "highest_point",
        }
    )

    assert settings == {
        "opponent_lead_policy": "highest_point",
        "opponent_response_policy": "basic_defender_response",
    }

def test_get_profile_preset_settings_from_input_defaults() -> None:
    settings = get_profile_preset_settings_from_input({})

    assert settings == {
        "use_profile_presets": False,
    }


def test_get_profile_preset_settings_from_input_reads_value() -> None:
    settings = get_profile_preset_settings_from_input(
        {
            "use_profile_presets": True,
        }
    )

    assert settings == {
        "use_profile_presets": True,
    }

def test_get_game_declaration_from_input_defaults() -> None:
    declaration = get_game_declaration_from_input(
        {
            "game_type": "grand",
        }
    )

    assert declaration.game_type == "grand"
    assert declaration.hand_game is False
    assert declaration.ouvert is False
    assert declaration.schneider_announced is False
    assert declaration.schwarz_announced is False
    assert declaration.matadors is None


def test_get_game_declaration_from_input_reads_values() -> None:
    declaration = get_game_declaration_from_input(
        {
            "game_type": "grand",
            "hand_game": True,
            "ouvert": False,
            "schneider_announced": True,
            "schwarz_announced": False,
            "matadors": 2,
        }
    )

    assert declaration.game_type == "grand"
    assert declaration.hand_game is True
    assert declaration.ouvert is False
    assert declaration.schneider_announced is True
    assert declaration.schwarz_announced is False
    assert declaration.matadors == 2

def test_get_game_declaration_from_input_reads_bid_value() -> None:
    data = {
        "game_type": "grand",
        "bid_value": 72,
    }

    declaration = get_game_declaration_from_input(data)

    assert declaration.bid_value == 72


def test_get_game_declaration_from_input_reads_nested_values() -> None:
    data = {
        "game_type": "grand",
        "game_declaration": {
            "hand_game": True,
            "ouvert": False,
            "schneider_announced": True,
            "schwarz_announced": False,
            "matadors": 2,
            "bid_value": 48,
        },
    }

    declaration = get_game_declaration_from_input(data)

    assert declaration.game_type == "grand"
    assert declaration.hand_game is True
    assert declaration.ouvert is False
    assert declaration.schneider_announced is True
    assert declaration.schwarz_announced is False
    assert declaration.matadors == 2
    assert declaration.bid_value == 48


def test_get_performance_rating_system_from_input_defaults_to_none() -> None:
    assert get_performance_rating_system_from_input({}) is None


def test_get_performance_rating_system_from_input_reads_value() -> None:
    assert get_performance_rating_system_from_input(
        {
            "performance_rating_system": "isko_list",
        }
    ) == "isko_list"


def test_get_list_performance_input_from_input_defaults_to_none() -> None:
    assert get_list_performance_input_from_input({}) is None


def test_get_list_performance_input_from_input_reads_value() -> None:
    list_performance_input = {
        "player_game_points": 120,
        "own_games_won": 3,
        "own_games_lost": 1,
        "other_players_lost_games": 2,
    }

    assert get_list_performance_input_from_input(
        {
            "list_performance_input": list_performance_input,
        }
    ) == list_performance_input


def test_get_list_game_contributions_from_input_defaults_to_none() -> None:
    assert get_list_game_contributions_from_input({}) is None


def test_get_list_game_contributions_from_input_reads_value() -> None:
    list_game_contributions = [
        {
            "player_role": "declarer",
            "game_outcome": "declarer_win",
            "settlement_score": 96,
        },
    ]

    assert get_list_game_contributions_from_input(
        {
            "list_game_contributions": list_game_contributions,
        }
    ) == list_game_contributions


def test_get_list_game_contributions_from_input_preserves_empty_list() -> None:
    assert get_list_game_contributions_from_input(
        {
            "list_game_contributions": [],
        }
    ) == []


def test_get_list_analysis_results_from_input_defaults_to_none() -> None:
    assert get_list_analysis_results_from_input({}) is None


def test_get_list_analysis_results_from_input_reads_value() -> None:
    list_analysis_results = [
        {
            "position": {
                "player_role": "declarer",
            },
            "final_settlement_summary": {
                "is_complete": True,
                "is_loss": False,
                "settlement_score": 96,
            },
        },
    ]

    assert get_list_analysis_results_from_input(
        {
            "list_analysis_results": list_analysis_results,
        }
    ) == list_analysis_results


def test_get_list_analysis_results_from_input_preserves_empty_list() -> None:
    assert get_list_analysis_results_from_input(
        {
            "list_analysis_results": [],
        }
    ) == []


def test_get_left_opponent_policy_settings_defaults_to_global_values() -> None:
    assert get_left_opponent_policy_settings_from_input(
        {
            "opponent_lead_policy": "highest_point",
            "opponent_response_policy": "basic_trick_play",
        }
    ) == {
        "opponent_lead_policy": "highest_point",
        "opponent_response_policy": "basic_trick_play",
    }


def test_get_right_opponent_policy_settings_defaults_to_global_values() -> None:
    assert get_right_opponent_policy_settings_from_input(
        {
            "opponent_lead_policy": "highest_point",
            "opponent_response_policy": "basic_trick_play",
        }
    ) == {
        "opponent_lead_policy": "highest_point",
        "opponent_response_policy": "basic_trick_play",
    }


def test_get_left_opponent_policy_settings_reads_specific_values() -> None:
    assert get_left_opponent_policy_settings_from_input(
        {
            "opponent_lead_policy": "lowest_point",
            "opponent_response_policy": "lowest_point",
            "left_opponent_lead_policy": "highest_point",
            "left_opponent_response_policy": "basic_trick_play",
        }
    ) == {
        "opponent_lead_policy": "highest_point",
        "opponent_response_policy": "basic_trick_play",
    }


def test_get_right_opponent_policy_settings_reads_specific_values() -> None:
    assert get_right_opponent_policy_settings_from_input(
        {
            "opponent_lead_policy": "lowest_point",
            "opponent_response_policy": "lowest_point",
            "right_opponent_lead_policy": "highest_point",
            "right_opponent_response_policy": "basic_trick_play",
        }
    ) == {
        "opponent_lead_policy": "highest_point",
        "opponent_response_policy": "basic_trick_play",
    }


def test_left_and_right_opponent_policy_settings_can_differ() -> None:
    data = {
        "opponent_lead_policy": "lowest_point",
        "opponent_response_policy": "lowest_point",
        "left_opponent_lead_policy": "highest_point",
        "left_opponent_response_policy": "basic_trick_play",
        "right_opponent_lead_policy": "lowest_point",
        "right_opponent_response_policy": "highest_point",
    }

    assert get_left_opponent_policy_settings_from_input(data) == {
        "opponent_lead_policy": "highest_point",
        "opponent_response_policy": "basic_trick_play",
    }
    assert get_right_opponent_policy_settings_from_input(data) == {
        "opponent_lead_policy": "lowest_point",
        "opponent_response_policy": "highest_point",
    }


def test_left_right_opponent_policy_settings_fall_back_to_global_preset() -> None:
    data = {
        "opponent_policy_preset": "aggressive_points",
    }

    assert get_left_opponent_policy_settings_from_input(data) == {
        "opponent_lead_policy": "highest_point",
        "opponent_response_policy": "highest_point",
    }
    assert get_right_opponent_policy_settings_from_input(data) == {
        "opponent_lead_policy": "highest_point",
        "opponent_response_policy": "highest_point",
    }
