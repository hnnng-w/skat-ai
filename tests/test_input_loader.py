from skat_ai.input_loader import (
    build_game_state_from_input,
    get_analysis_metadata_from_input,
    get_opponent_policy_settings_from_input,
    get_profile_preset_settings_from_input,
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
    assert state.trick_leader == "unknown"
    assert state.completed_tricks == []
    assert state.declarer_points == 0
    assert state.defender_points == 0
    assert state.next_player == "unknown"


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