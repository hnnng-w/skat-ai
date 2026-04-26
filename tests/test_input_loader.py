from skat_ai.input_loader import (
    build_game_state_from_input,
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
