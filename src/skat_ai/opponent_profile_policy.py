from skat_ai.opponent_policy_preset import (
    apply_opponent_policy_preset,
    validate_opponent_policy_preset,
)
from skat_ai.player_profile import PlayerProfile

PROFILE_DATA_CONFIDENCE_RANKS = {
    "unknown": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
}

NON_SIMPLE_PROFILE_POLICY_PRESETS = [
    "aggressive_points",
    "cautious_defender",
]


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

    The returned preset can be used as metadata even when it is not actionable.
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


def choose_actionable_profile_policy_preset(
    profile: PlayerProfile,
) -> str | None:
    """
    Chooses a profile-derived preset that is safe to apply to strategy.

    simple_lowest is a neutral informational recommendation here; it must not
    overwrite existing explicit or default policy settings.
    """
    preset = choose_opponent_policy_preset_for_profile(profile)

    if preset not in NON_SIMPLE_PROFILE_POLICY_PRESETS:
        return None

    return preset


def choose_combined_actionable_profile_policy_preset(
    left_profile: PlayerProfile,
    right_profile: PlayerProfile,
) -> str | None:
    """
    Chooses one actionable combined preset from both opponent profiles.
    """
    left_preset = choose_actionable_profile_policy_preset(left_profile)
    right_preset = choose_actionable_profile_policy_preset(right_profile)

    if left_preset is None and right_preset is None:
        return None

    if left_preset is None:
        return right_preset

    if right_preset is None:
        return left_preset

    if left_preset != right_preset:
        left_confidence_rank = PROFILE_DATA_CONFIDENCE_RANKS[
            get_profile_data_confidence(left_profile)
        ]
        right_confidence_rank = PROFILE_DATA_CONFIDENCE_RANKS[
            get_profile_data_confidence(right_profile)
        ]

        if left_confidence_rank > right_confidence_rank:
            return left_preset

        if right_confidence_rank > left_confidence_rank:
            return right_preset

    if "aggressive_points" in [left_preset, right_preset]:
        return "aggressive_points"

    return left_preset


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
    preset = choose_combined_actionable_profile_policy_preset(
        left_profile=left_profile,
        right_profile=right_profile,
    )

    return preset or "simple_lowest"


def apply_profile_based_policy_preset(
    opponent_policy_settings: dict[str, str],
    left_profile: PlayerProfile,
    right_profile: PlayerProfile,
    use_profile_presets: bool,
) -> dict[str, str]:
    """
    Applies a profile-derived opponent policy preset if enabled.

    If disabled or no actionable profile preset exists, settings are returned
    unchanged.
    """
    if not use_profile_presets:
        return opponent_policy_settings.copy()

    preset = choose_combined_actionable_profile_policy_preset(
        left_profile=left_profile,
        right_profile=right_profile,
    )

    return apply_opponent_policy_preset(
        opponent_policy_settings=opponent_policy_settings,
        preset=preset,
    )


def apply_profile_based_side_policy_preset(
    opponent_policy_settings: dict[str, str],
    profile: PlayerProfile,
    use_profile_presets: bool,
) -> dict[str, str]:
    """
    Applies a non-simple profile-derived policy preset for one opponent side.

    If disabled or the profile produces no actionable preset, settings are
    returned unchanged.
    """
    if not use_profile_presets:
        return opponent_policy_settings.copy()

    preset = choose_actionable_profile_policy_preset(profile)

    if preset is None:
        return opponent_policy_settings.copy()

    return apply_opponent_policy_preset(
        opponent_policy_settings=opponent_policy_settings,
        preset=preset,
    )
