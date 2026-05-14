from typing import Any

from skat_ai.opponent_policy import validate_opponent_card_policy

VALID_OPPONENT_POLICY_PRESETS = [
    "simple_lowest",
    "cautious_defender",
    "aggressive_points",
    "random",
]


OPPONENT_POLICY_PRESETS = {
    "simple_lowest": {
        "opponent_lead_policy": "lowest_point",
        "opponent_response_policy": "lowest_point",
    },
    "cautious_defender": {
        "opponent_lead_policy": "basic_defender_lead",
        "opponent_response_policy": "basic_defender_response",
    },
    "aggressive_points": {
        "opponent_lead_policy": "highest_point",
        "opponent_response_policy": "highest_point",
    },
    "random": {
        "opponent_lead_policy": "random_legal",
        "opponent_response_policy": "random_legal",
    },
}


def validate_opponent_policy_preset(
    preset: str,
) -> None:
    """
    Validates an opponent policy preset.
    """
    if preset not in VALID_OPPONENT_POLICY_PRESETS:
        raise ValueError(f"Invalid opponent policy preset: {preset}")


def get_opponent_policy_settings_for_preset(
    preset: str,
) -> dict[str, str]:
    """
    Returns opponent policy settings for a preset.
    """
    validate_opponent_policy_preset(preset)

    settings = OPPONENT_POLICY_PRESETS[preset]

    validate_opponent_card_policy(settings["opponent_lead_policy"])
    validate_opponent_card_policy(settings["opponent_response_policy"])

    return settings.copy()


def apply_opponent_policy_preset(
    opponent_policy_settings: dict[str, str],
    preset: str | None,
) -> dict[str, str]:
    """
    Applies an opponent policy preset to existing opponent policy settings.

    If preset is None, the original settings are returned unchanged.
    """
    if preset is None:
        return opponent_policy_settings.copy()

    preset_settings = get_opponent_policy_settings_for_preset(preset)
    updated_settings = opponent_policy_settings.copy()
    updated_settings.update(preset_settings)

    return updated_settings


def build_serializable_opponent_policy_presets() -> dict[str, Any]:
    """
    Builds a JSON-serializable representation of available presets.
    """
    return {
        "valid_presets": VALID_OPPONENT_POLICY_PRESETS,
        "presets": OPPONENT_POLICY_PRESETS,
    }