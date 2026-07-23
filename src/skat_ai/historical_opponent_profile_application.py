from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

from skat_ai.effective_opponent_policy import EffectiveOpponentPolicySettings
from skat_ai.historical_decision_snapshot import HistoricalDecisionSnapshot
from skat_ai.historical_game import HistoricalGameRecord
from skat_ai.historical_opponent_profile_binding import HistoricalMatchedOpponentProfile


@dataclass(frozen=True)
class HistoricalDecisionOpponentProfiles:
    """Stable identities and optional matched profiles for one local decision view."""

    left_player_id: str
    right_player_id: str
    left: HistoricalMatchedOpponentProfile | None
    right: HistoricalMatchedOpponentProfile | None


def resolve_historical_opponent_profiles_for_decision(
    historical_game: HistoricalGameRecord,
    decision_snapshot: HistoricalDecisionSnapshot,
    matched_profiles: Mapping[str, HistoricalMatchedOpponentProfile],
) -> HistoricalDecisionOpponentProfiles:
    """Uses the snapshot's existing local mapping to resolve stable opponent profiles."""
    if decision_snapshot.source_game_id != historical_game.game_id:
        raise ValueError("Historical snapshot and profile-binding game IDs must match.")
    relative_map = decision_snapshot.relative_player_map
    if set(relative_map) != {"me", "left", "right"}:
        raise ValueError("Historical snapshot relative player mapping is incomplete.")
    acting_player_id = decision_snapshot.acting_player_id
    left_player_id = relative_map["left"]
    right_player_id = relative_map["right"]
    if relative_map["me"] != acting_player_id:
        raise ValueError("Historical snapshot acting player must map to me.")
    if len({acting_player_id, left_player_id, right_player_id}) != 3:
        raise ValueError("Historical decision opponents must be distinct from the acting player.")
    participant_ids = {player.player_id for player in historical_game.players}
    if {acting_player_id, left_player_id, right_player_id} != participant_ids:
        raise ValueError("Historical snapshot relative mapping must contain all participants.")
    return HistoricalDecisionOpponentProfiles(
        left_player_id=left_player_id,
        right_player_id=right_player_id,
        left=matched_profiles.get(left_player_id),
        right=matched_profiles.get(right_player_id),
    )


def _build_side_application(
    side: Literal["left", "right"],
    player_id: str,
    profile: HistoricalMatchedOpponentProfile | None,
    effective_settings: EffectiveOpponentPolicySettings,
) -> dict[str, Any]:
    lead_policy = getattr(effective_settings, f"{side}_lead_policy")
    response_policy = getattr(effective_settings, f"{side}_response_policy")
    if profile is None:
        return {
            "relative_player": side,
            "opponent_player_id": player_id,
            "profile_match_status": "unmatched",
            "classification": None,
            "derivation_status": None,
            "actionable_policy_preset": None,
            "application_status": "unmatched",
            "not_applied_reason": "unmatched_player",
            "applied_policy_preset": None,
            "effective_lead_policy": lead_policy,
            "effective_response_policy": response_policy,
        }

    derivation = profile.derivation
    actionable_preset = derivation["actionable_policy_preset"]
    if actionable_preset is None:
        application_status = "not_actionable"
        not_applied_reason = {
            "insufficient_confidence": "insufficient_confidence",
            "neutral": "neutral_profile",
            "insufficient_data": "insufficient_data",
        }[derivation["derivation_status"]]
        applied_preset = None
    else:
        lead_source = getattr(effective_settings, f"{side}_lead_source")
        response_source = getattr(effective_settings, f"{side}_response_source")
        if lead_source == "profile" and response_source == "profile":
            application_status = "applied"
            not_applied_reason = None
            applied_preset = actionable_preset
        else:
            application_status = "explicit_policy_precedence"
            not_applied_reason = "explicit_policy_precedence"
            applied_preset = None

    return {
        "relative_player": side,
        "opponent_player_id": player_id,
        "profile_match_status": "matched",
        "classification": derivation["classification"],
        "derivation_status": derivation["derivation_status"],
        "actionable_policy_preset": actionable_preset,
        "application_status": application_status,
        "not_applied_reason": not_applied_reason,
        "applied_policy_preset": applied_preset,
        "effective_lead_policy": lead_policy,
        "effective_response_policy": response_policy,
    }


def build_historical_decision_opponent_profile_application(
    acting_player_id: str,
    profiles: HistoricalDecisionOpponentProfiles,
    effective_settings: EffectiveOpponentPolicySettings,
) -> dict[str, Any]:
    """Serializes profile actionability and the policies resolved for one decision."""
    return {
        "acting_player_id": acting_player_id,
        "left_opponent_player_id": profiles.left_player_id,
        "right_opponent_player_id": profiles.right_player_id,
        "left": _build_side_application(
            "left", profiles.left_player_id, profiles.left, effective_settings
        ),
        "right": _build_side_application(
            "right", profiles.right_player_id, profiles.right, effective_settings
        ),
    }
