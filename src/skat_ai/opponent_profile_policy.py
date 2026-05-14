from skat_ai.opponent_policy_preset import validate_opponent_policy_preset
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