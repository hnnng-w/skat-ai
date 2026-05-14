from skat_ai.analysis_metadata import (
    AnalysisMetadata,
    build_analysis_metadata_from_input,
    build_default_analysis_metadata,
    build_recommended_opponent_policy_presets_from_metadata,
    build_serializable_analysis_metadata,
)
from skat_ai.player_profile import PlayerProfile
from skat_ai.strategic_metadata import StrategicMetadata


def test_build_default_analysis_metadata() -> None:
    metadata = build_default_analysis_metadata()

    assert metadata == AnalysisMetadata()


def test_build_analysis_metadata_from_empty_input() -> None:
    metadata = build_analysis_metadata_from_input({})

    assert metadata.strategic_metadata == StrategicMetadata()
    assert metadata.left_player_profile == PlayerProfile()
    assert metadata.right_player_profile == PlayerProfile()


def test_build_analysis_metadata_from_input() -> None:
    metadata = build_analysis_metadata_from_input(
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
    assert metadata.strategic_metadata.skat_visibility == "known_post_game"
    assert metadata.strategic_metadata.game_end_reason == "normal_completion"
    assert metadata.left_player_profile.games_played == 1240
    assert metadata.left_player_profile.solo_rate == 0.31
    assert metadata.right_player_profile.games_played == 520
    assert metadata.right_player_profile.defender_win_rate == 0.49


def test_build_serializable_analysis_metadata() -> None:
    metadata = AnalysisMetadata(
        strategic_metadata=StrategicMetadata(
            analysis_mode="post_game_review",
            skat_visibility="known_post_game",
            game_end_reason="normal_completion",
        ),
        left_player_profile=PlayerProfile(
            games_played=1240,
            solo_rate=0.31,
        ),
        right_player_profile=PlayerProfile(
            games_played=520,
            defender_win_rate=0.49,
        ),
    )

    result = build_serializable_analysis_metadata(metadata)

    assert result["strategic_metadata"] == {
        "analysis_mode": "post_game_review",
        "skat_visibility": "known_post_game",
        "game_end_reason": "normal_completion",
    }
    assert result["left_player_profile"]["games_played"] == 1240
    assert result["left_player_profile"]["solo_rate"] == 0.31
    assert result["right_player_profile"]["games_played"] == 520
    assert result["right_player_profile"]["defender_win_rate"] == 0.49
    assert result["recommended_opponent_policy_presets"] == {
        "left_player_recommended_preset": "simple_lowest",
        "right_player_recommended_preset": "simple_lowest",
    }

def test_build_recommended_opponent_policy_presets_from_metadata() -> None:
    metadata = AnalysisMetadata(
        left_player_profile=PlayerProfile(
            games_played=1000,
            solo_rate=0.25,
            grand_rate=0.15,
            hand_game_rate=0.03,
            defender_win_rate=0.55,
        ),
        right_player_profile=PlayerProfile(
            games_played=1000,
            solo_rate=0.38,
            grand_rate=0.27,
        ),
    )

    presets = build_recommended_opponent_policy_presets_from_metadata(metadata)

    assert presets == {
        "left_player_recommended_preset": "cautious_defender",
        "right_player_recommended_preset": "aggressive_points",
    }