from dataclasses import dataclass
from typing import Any, Literal

from skat_ai.effective_opponent_policy import EffectiveOpponentPolicySettings
from skat_ai.live_opponent_profile_binding import (
    BoundExternalOpponentProfile,
    LiveOpponentProfileBindings,
)
from skat_ai.player_profile import PlayerProfile

ProfileSource = Literal["external_statistics", "manual_profile", "none"]


@dataclass(frozen=True)
class EffectiveLiveOpponentProfiles:
    """Effective side profiles after manual/external source precedence."""

    left: PlayerProfile
    right: PlayerProfile
    left_source: ProfileSource
    right_source: ProfileSource


def select_effective_live_opponent_profiles(
    data: dict[str, Any],
    manual_left_profile: PlayerProfile,
    manual_right_profile: PlayerProfile,
    bindings: LiveOpponentProfileBindings,
) -> EffectiveLiveOpponentProfiles:
    """Selects manual profiles before external profiles without merging them."""
    if "left_player_profile" in data:
        left_profile = manual_left_profile
        left_source: ProfileSource = "manual_profile"
    elif bindings.left is not None:
        left_profile = bindings.left.profile
        left_source = "external_statistics"
    else:
        left_profile = manual_left_profile
        left_source = "none"

    if "right_player_profile" in data:
        right_profile = manual_right_profile
        right_source: ProfileSource = "manual_profile"
    elif bindings.right is not None:
        right_profile = bindings.right.profile
        right_source = "external_statistics"
    else:
        right_profile = manual_right_profile
        right_source = "none"

    return EffectiveLiveOpponentProfiles(
        left=left_profile,
        right=right_profile,
        left_source=left_source,
        right_source=right_source,
    )


def _build_external_profile_summary(
    binding: BoundExternalOpponentProfile,
) -> dict[str, Any]:
    source = binding.source
    derivation = binding.derivation
    confidence = derivation["confidence"]
    decisive_codes = set(derivation["decisive_signal_codes"])
    decisive_confidence_levels = [
        signal["confidence_level"]
        for signal in derivation["signals"]
        if signal["code"] in decisive_codes
    ]
    confidence_ranks = {"unknown": 0, "low": 1, "medium": 2, "high": 3}
    confidence_level = (
        min(decisive_confidence_levels, key=lambda level: confidence_ranks[level])
        if decisive_confidence_levels
        else confidence["overall"]["level"]
    )
    result = {
        "source_type": source["source_type"],
        "source_name": source["source_name"],
        "source_player_id": source.get("source_player_id"),
        "captured_at": source["captured_at"],
        "profile_derivation_version": derivation["profile_derivation_version"],
        "classification": derivation["classification"],
        "derivation_status": derivation["derivation_status"],
        "confidence_level": confidence_level,
        "recommended_policy_preset": derivation["recommended_policy_preset"],
        "actionable_policy_preset": derivation["actionable_policy_preset"],
    }
    if "notes" in source:
        result["notes"] = source["notes"]
    return result


def _build_side_application_summary(
    relative_player: Literal["left", "right"],
    binding: BoundExternalOpponentProfile | None,
    profile_source: ProfileSource,
    effective_settings: EffectiveOpponentPolicySettings,
) -> dict[str, Any]:
    lead_policy = getattr(effective_settings, f"{relative_player}_lead_policy")
    response_policy = getattr(effective_settings, f"{relative_player}_response_policy")
    if binding is None:
        return {
            "relative_player": relative_player,
            "bound_player_id": None,
            "binding_status": "not_requested",
            "effective_profile_source": profile_source,
            "external_profile": None,
            "application_status": "not_requested",
            "not_applied_reason": "not_requested",
            "applied_policy_preset": None,
            "effective_lead_policy": lead_policy,
            "effective_response_policy": response_policy,
        }

    external_profile = _build_external_profile_summary(binding)
    if profile_source == "manual_profile":
        application_status = "manual_profile_precedence"
        not_applied_reason = "manual_profile_precedence"
        applied_preset = None
    else:
        derivation_status = binding.derivation["derivation_status"]
        actionable_preset = binding.derivation["actionable_policy_preset"]
        if actionable_preset is None:
            application_status = "not_actionable"
            not_applied_reason = {
                "insufficient_confidence": "insufficient_confidence",
                "neutral": "neutral_profile",
                "insufficient_data": "insufficient_data",
            }[derivation_status]
            applied_preset = None
        else:
            lead_source = getattr(effective_settings, f"{relative_player}_lead_source")
            response_source = getattr(
                effective_settings, f"{relative_player}_response_source"
            )
            if lead_source == "profile" and response_source == "profile":
                application_status = "applied"
                not_applied_reason = None
                applied_preset = actionable_preset
            else:
                application_status = "explicit_policy_precedence"
                not_applied_reason = "explicit_policy_precedence"
                applied_preset = None

    return {
        "relative_player": relative_player,
        "bound_player_id": binding.player_id,
        "binding_status": "matched",
        "effective_profile_source": profile_source,
        "external_profile": external_profile,
        "application_status": application_status,
        "not_applied_reason": not_applied_reason,
        "applied_policy_preset": applied_preset,
        "effective_lead_policy": lead_policy,
        "effective_response_policy": response_policy,
    }


def build_opponent_profile_application_summary(
    statistics_input_file: str,
    use_profile_presets: bool,
    bindings: LiveOpponentProfileBindings,
    effective_profiles: EffectiveLiveOpponentProfiles,
    effective_settings: EffectiveOpponentPolicySettings,
) -> dict[str, Any]:
    """Builds the stable live external-profile application summary."""
    return {
        "enabled": True,
        "statistics_input_file": statistics_input_file,
        "use_profile_presets": use_profile_presets,
        "left": _build_side_application_summary(
            "left",
            bindings.left,
            effective_profiles.left_source,
            effective_settings,
        ),
        "right": _build_side_application_summary(
            "right",
            bindings.right,
            effective_profiles.right_source,
            effective_settings,
        ),
    }
