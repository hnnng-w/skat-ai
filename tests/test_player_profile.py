from skat_ai.player_profile import (
    PlayerProfile,
    build_default_player_profile,
    build_player_profile_from_dict,
)


def test_build_default_player_profile() -> None:
    profile = build_default_player_profile()

    assert profile == PlayerProfile()


def test_build_player_profile_from_dict() -> None:
    profile = build_player_profile_from_dict(
        {
            "games_played": 1240,
            "solo_games_played": 380,
            "defender_games_played": 860,
            "solo_rate": 0.31,
            "defender_rate": 0.69,
            "solo_win_rate": 0.7,
            "hand_game_rate": 0.1,
            "suit_game_rate": 0.45,
            "grand_rate": 0.25,
            "null_game_rate": 0.05,
            "defender_win_rate": 0.55,
        }
    )

    assert profile.games_played == 1240
    assert profile.solo_games_played == 380
    assert profile.defender_games_played == 860
    assert profile.solo_rate == 0.31
    assert profile.defender_rate == 0.69
    assert profile.solo_win_rate == 0.7
    assert profile.hand_game_rate == 0.1
    assert profile.suit_game_rate == 0.45
    assert profile.grand_rate == 0.25
    assert profile.null_game_rate == 0.05
    assert profile.defender_win_rate == 0.55


def test_build_player_profile_from_partial_dict() -> None:
    profile = build_player_profile_from_dict(
        {
            "games_played": 1240,
            "solo_rate": 0.35,
            "grand_rate": 0.25,
        }
    )

    assert profile.games_played == 1240
    assert profile.solo_rate == 0.35
    assert profile.grand_rate == 0.25
    assert profile.solo_games_played is None
    assert profile.defender_rate is None
    assert profile.solo_win_rate is None
    assert profile.defender_win_rate is None
