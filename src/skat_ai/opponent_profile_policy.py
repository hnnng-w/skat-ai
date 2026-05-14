from skat_ai.opponent_policy_preset import (
    apply_opponent_policy_preset,
    validate_opponent_policy_preset,
)
from skat_ai.player_profile import PlayerProfile


def get_profile_data_confidence(
    profile: PlayerProfile,
) -> str:
    """
    Returns a rough confidence level for a player profile.

    This is based on games_played only for now.
    """
    if profile.games_played is None:
        return "unknown"

    if profile.games_played < 100:
        return "low"

    if profile.games_played < 500:
        return "medium"

    return "high"


def is_aggressive_profile(
    profile: PlayerProfile,
) -> bool:
    """
    Returns whether a player profile looks aggressive.

    Current rough indicators:
    - high solo rate
    - high grand rate
    - high hand-game rate
    """
    return (
        profile.solo_rate is not None
        and profile.solo_rate >= 0.35
    ) or (
        profile.grand_rate is not None
        and profile.grand_rate >= 0.25
    ) or (
        profile.hand_game_rate is not None
        and profile.hand_game_rate >= 0.10
    )


def is_cautious_defender_profile(
    profile: PlayerProfile,
) -> bool:
    """
    Returns whether a player profile looks like a reliable defender.

    Current rough indicators:
    - enough data confidence
    - good defender win rate
    - not overly aggressive
    """
    confidence = get_profile_data_confidence(profile)

    return (
        confidence in ["medium", "high"]
        and profile.defender_win_rate is not None
        and profile.defender_win_rate >= 0.52
        and not is_aggressive_profile(profile)
    )


def choose_opponent_policy_preset_for_profile(
    profile: PlayerProfile,
) -> str:
    """
    Chooses a rough opponent policy preset for a player profile.

    This does not yet affect the simulation automatically.
    """
    confidence = get_profile_data_confidence(profile)

    if confidence == "unknown" or confidence == "low":
        preset = "simple_lowest"
    elif is_aggressive_profile(profile):
        preset = "aggressive_points"
    elif is_cautious_defender_profile(profile):
        preset = "cautious_defender"
    else:
        preset = "simple_lowest"

    validate_opponent_policy_preset(preset)

    return preset

def choose_combined_profile_policy_preset(
    left_profile: PlayerProfile,
    right_profile: PlayerProfile,
) -> str:
    """
    Chooses one combined opponent policy preset from both opponent profiles.

    Current simple rule:
    - If either opponent looks aggressive, use aggressive_points.
    - Else if either opponent looks like a cautious defender, use cautious_defender.
    - Else use simple_lowest.
    """
    left_preset = choose_opponent_policy_preset_for_profile(left_profile)
    right_preset = choose_opponent_policy_preset_for_profile(right_profile)

    if "aggressive_points" in [left_preset, right_preset]:
        return "aggressive_points"

    if "cautious_defender" in [left_preset, right_preset]:
        return "cautious_defender"

    return "simple_lowest"


def apply_profile_based_policy_preset(
    opponent_policy_settings: dict[str, str],
    left_profile: PlayerProfile,
    right_profile: PlayerProfile,
    use_profile_presets: bool,
) -> dict[str, str]:
    """
    Applies a profile-derived opponent policy preset if enabled.

    If disabled, settings are returned unchanged.
    """
    if not use_profile_presets:
        return opponent_policy_settings.copy()

    preset = choose_combined_profile_policy_preset(
        left_profile=left_profile,
        right_profile=right_profile,
    )

    return apply_opponent_policy_preset(
        opponent_policy_settings=opponent_policy_settings,
        preset=preset,
    )