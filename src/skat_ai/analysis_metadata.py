from dataclasses import dataclass, field
from typing import Any

from skat_ai.opponent_profile_policy import choose_opponent_policy_preset_for_profile
from skat_ai.player_profile import (
    PlayerProfile,
    build_default_player_profile,
    build_player_profile_from_dict,
)
from skat_ai.strategic_metadata import (
    StrategicMetadata,
    build_default_strategic_metadata,
    build_strategic_metadata_from_dict,
)


@dataclass(frozen=True)
class AnalysisMetadata:
    """
    Bundles optional metadata for an analysis.

    This metadata is prepared for future use and does not currently change
    simulation decisions.
    """
    strategic_metadata: StrategicMetadata = field(
        default_factory=build_default_strategic_metadata
    )
    left_player_profile: PlayerProfile = field(
        default_factory=build_default_player_profile
    )
    right_player_profile: PlayerProfile = field(
        default_factory=build_default_player_profile
    )


def build_default_analysis_metadata() -> AnalysisMetadata:
    """
    Builds default analysis metadata.
    """
    return AnalysisMetadata()


def build_analysis_metadata_from_input(
    data: dict[str, Any],
) -> AnalysisMetadata:
    """
    Builds analysis metadata from input JSON data.

    Supported optional top-level fields:
    - analysis_mode
    - skat_visibility
    - game_end_reason
    - left_player_profile
    - right_player_profile
    """
    strategic_metadata = build_strategic_metadata_from_dict(
        {
            "analysis_mode": data.get("analysis_mode", "live_decision"),
            "skat_visibility": data.get("skat_visibility", "unknown"),
            "game_end_reason": data.get("game_end_reason", "not_ended"),
        }
    )

    left_player_profile = build_player_profile_from_dict(
        data.get("left_player_profile", {})
    )
    right_player_profile = build_player_profile_from_dict(
        data.get("right_player_profile", {})
    )

    return AnalysisMetadata(
        strategic_metadata=strategic_metadata,
        left_player_profile=left_player_profile,
        right_player_profile=right_player_profile,
    )


def build_serializable_player_profile(
    profile: PlayerProfile,
) -> dict[str, int | float | None]:
    """
    Builds a JSON-serializable player profile.
    """
    return {
        "games_played": profile.games_played,
        "solo_games_played": profile.solo_games_played,
        "defender_games_played": profile.defender_games_played,
        "solo_rate": profile.solo_rate,
        "solo_win_rate": profile.solo_win_rate,
        "hand_game_rate": profile.hand_game_rate,
        "suit_game_rate": profile.suit_game_rate,
        "grand_rate": profile.grand_rate,
        "null_game_rate": profile.null_game_rate,
        "defender_win_rate": profile.defender_win_rate,
    }


def build_serializable_analysis_metadata(
    metadata: AnalysisMetadata,
) -> dict[str, Any]:
    """
    Builds a JSON-serializable analysis metadata representation.
    """
    return {
        "strategic_metadata": {
            "analysis_mode": metadata.strategic_metadata.analysis_mode,
            "skat_visibility": metadata.strategic_metadata.skat_visibility,
            "game_end_reason": metadata.strategic_metadata.game_end_reason,
        },
        "left_player_profile": build_serializable_player_profile(
            metadata.left_player_profile
        ),
        "right_player_profile": build_serializable_player_profile(
            metadata.right_player_profile
        ),
        "recommended_opponent_policy_presets": (
            build_recommended_opponent_policy_presets_from_metadata(metadata)
        ),
    }

def build_recommended_opponent_policy_presets_from_metadata(
    metadata: AnalysisMetadata,
) -> dict[str, str]:
    """
    Builds recommended opponent policy presets from player profiles.

    This is currently informational and does not automatically affect simulation.
    """
    return {
        "left_player_recommended_preset": choose_opponent_policy_preset_for_profile(
            metadata.left_player_profile
        ),
        "right_player_recommended_preset": choose_opponent_policy_preset_for_profile(
            metadata.right_player_profile
        ),
    }