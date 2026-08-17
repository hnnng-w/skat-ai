from __future__ import annotations

from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import Any, Final

from skat_ai.fixed_three_player_list_rotation import (
    FIXED_THREE_PLAYER_LIST_TABLE_PLACES,
)
from skat_ai.match_capture_contracts import MatchCaptureDefinitionV1
from skat_ai.opponent_profile_derivation import (
    OpponentProfileDerivation,
    derive_opponent_profile,
)
from skat_ai.opponent_statistics import (
    build_player_profile_from_opponent_statistics,
)
from skat_ai.performance_rating import validate_stable_list_entry_identifier
from skat_ai.player_profile import PlayerProfile
from skat_ai.rfc3339 import parse_rfc3339_datetime

MATCH_PLAYER_STATISTICS_CONTEXT_VERSION = 1

MATCH_PLAYER_STATISTICS_TEMPORAL_STATUSES: Final[tuple[str, ...]] = (
    "absent",
    "eligible",
    "match_time_unavailable",
    "captured_not_before_match",
)

MATCH_PLAYER_STATISTICS_SNAPSHOT_POLICY = (
    "one_match_bound_snapshot_per_participant"
)
MATCH_PLAYER_STATISTICS_TEMPORAL_POLICY = "captured_strictly_before_match_start"
MATCH_PLAYER_STATISTICS_PROFILE_POLICY = "reuse_existing_rule_based_derivation"
MATCH_PLAYER_STATISTICS_HISTORY_POLICY = (
    "later_matches_use_separate_immutable_snapshots"
)

_RELATIVE_PLAYER_IDS = frozenset({"me", "left", "right"})
_CONFIDENCE_SCOPES = ("overall", "declarer", "defender")


def classify_match_player_statistics_temporal_status_v1(
    *,
    captured_at: str,
    played_at: str | None,
) -> str:
    """Classifies source-Match eligibility without deriving a Profile."""
    captured_instant = parse_rfc3339_datetime(captured_at, "captured_at")
    if played_at is None:
        return "match_time_unavailable"
    played_instant = parse_rfc3339_datetime(played_at, "played_at")
    return "eligible" if captured_instant < played_instant else "captured_not_before_match"


def _serialize_player_profile(profile: PlayerProfile) -> dict[str, int | float | None]:
    return {
        "games_played": profile.games_played,
        "solo_games_played": profile.solo_games_played,
        "defender_games_played": profile.defender_games_played,
        "solo_rate": profile.solo_rate,
        "defender_rate": profile.defender_rate,
        "solo_win_rate": profile.solo_win_rate,
        "hand_game_rate": profile.hand_game_rate,
        "suit_game_rate": profile.suit_game_rate,
        "grand_rate": profile.grand_rate,
        "null_game_rate": profile.null_game_rate,
        "defender_win_rate": profile.defender_win_rate,
    }


def _serialize_profile_derivation(
    derivation: OpponentProfileDerivation,
) -> dict[str, Any]:
    return {
        "profile_derivation_version": derivation.profile_derivation_version,
        "confidence": {
            scope: {
                "level": derivation.confidence[scope].level,
                "evidence_count": derivation.confidence[scope].evidence_count,
                "evidence_kind": derivation.confidence[scope].evidence_kind,
            }
            for scope in _CONFIDENCE_SCOPES
        },
        "signals": [
            {
                "code": signal.code,
                "source_field": signal.source_field,
                "observed_value": signal.observed_value,
                "comparison_operator": signal.comparison_operator,
                "threshold": signal.threshold,
                "confidence_scope": signal.confidence_scope,
                "confidence_level": signal.confidence_level,
                "value_threshold_matched": signal.value_threshold_matched,
                "actionable": signal.actionable,
                "reason_code": signal.reason_code,
            }
            for signal in derivation.signals
        ],
        "classification": derivation.classification,
        "recommended_policy_preset": derivation.recommended_policy_preset,
        "actionable_policy_preset": derivation.actionable_policy_preset,
        "derivation_status": derivation.derivation_status,
        "decisive_signal_codes": list(derivation.decisive_signal_codes),
        "explanations": list(derivation.explanations),
    }


@dataclass(frozen=True, slots=True, kw_only=True)
class MatchPlayerStatisticsContextV1:
    """One Match participant's retained statistics and temporal preparation."""

    match_player_statistics_context_version: int = (
        MATCH_PLAYER_STATISTICS_CONTEXT_VERSION
    )
    player_id: str
    table_place: str
    snapshot_id: str | None
    observed_at: str | None
    temporal_status: str
    eligible_for_match_analysis: bool
    normalized_profile: PlayerProfile | None
    profile_derivation: OpponentProfileDerivation | None

    def __post_init__(self) -> None:
        if (
            type(self.match_player_statistics_context_version) is not int
            or self.match_player_statistics_context_version
            != MATCH_PLAYER_STATISTICS_CONTEXT_VERSION
        ):
            raise ValueError(
                "match_player_statistics_context_version must equal "
                f"{MATCH_PLAYER_STATISTICS_CONTEXT_VERSION}."
            )
        validate_stable_list_entry_identifier(self.player_id, "player_id")
        if self.player_id in _RELATIVE_PLAYER_IDS:
            raise ValueError("player_id must be a stable, non-relative Player ID.")
        if self.table_place not in FIXED_THREE_PLAYER_LIST_TABLE_PLACES:
            raise ValueError(
                "table_place must be one of "
                f"{list(FIXED_THREE_PLAYER_LIST_TABLE_PLACES)}."
            )
        if self.temporal_status not in MATCH_PLAYER_STATISTICS_TEMPORAL_STATUSES:
            raise ValueError(
                "temporal_status must be one of "
                f"{list(MATCH_PLAYER_STATISTICS_TEMPORAL_STATUSES)}."
            )
        if type(self.eligible_for_match_analysis) is not bool:
            raise ValueError("eligible_for_match_analysis must be a boolean.")

        if self.temporal_status == "absent":
            if any(
                value is not None
                for value in (
                    self.snapshot_id,
                    self.observed_at,
                    self.normalized_profile,
                    self.profile_derivation,
                )
            ):
                raise ValueError("An absent Context cannot contain Snapshot or Profile data.")
        else:
            validate_stable_list_entry_identifier(self.snapshot_id, "snapshot_id")
            validate_stable_list_entry_identifier(self.observed_at, "observed_at")
            parse_rfc3339_datetime(self.observed_at, "observed_at")
            if type(self.normalized_profile) is not PlayerProfile:
                raise ValueError("A retained Snapshot requires normalized_profile.")
            if type(self.profile_derivation) is not OpponentProfileDerivation:
                raise ValueError("A retained Snapshot requires profile_derivation.")
            object.__setattr__(
                self,
                "profile_derivation",
                replace(
                    self.profile_derivation,
                    confidence=MappingProxyType(
                        dict(self.profile_derivation.confidence)
                    ),
                ),
            )
        if self.eligible_for_match_analysis != (self.temporal_status == "eligible"):
            raise ValueError(
                "eligible_for_match_analysis must be true exactly for eligible status."
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_player_statistics_context_version": (
                self.match_player_statistics_context_version
            ),
            "player_id": self.player_id,
            "table_place": self.table_place,
            "snapshot_id": self.snapshot_id,
            "observed_at": self.observed_at,
            "temporal_status": self.temporal_status,
            "eligible_for_match_analysis": self.eligible_for_match_analysis,
            "normalized_profile": (
                None
                if self.normalized_profile is None
                else _serialize_player_profile(self.normalized_profile)
            ),
            "profile_derivation": (
                None
                if self.profile_derivation is None
                else _serialize_profile_derivation(self.profile_derivation)
            ),
        }


def build_match_player_statistics_context_v1(
    match_definition: MatchCaptureDefinitionV1,
    *,
    player_id: str,
) -> MatchPlayerStatisticsContextV1:
    """Builds one descriptive Context without applying its derived Profile."""
    if type(match_definition) is not MatchCaptureDefinitionV1:
        raise ValueError("match_definition must be a MatchCaptureDefinitionV1.")
    participant = next(
        (
            participant
            for participant in match_definition.participants
            if participant.player_id == player_id
        ),
        None,
    )
    if participant is None:
        raise ValueError("player_id must reference exactly one Match participant.")
    snapshot = participant.statistics_snapshot
    if snapshot is None:
        return MatchPlayerStatisticsContextV1(
            player_id=participant.player_id,
            table_place=participant.table_place,
            snapshot_id=None,
            observed_at=None,
            temporal_status="absent",
            eligible_for_match_analysis=False,
            normalized_profile=None,
            profile_derivation=None,
        )

    profile = build_player_profile_from_opponent_statistics(snapshot.statistics_record)
    derivation = derive_opponent_profile(profile)
    temporal_status = classify_match_player_statistics_temporal_status_v1(
        captured_at=snapshot.statistics_record.source.captured_at,
        played_at=match_definition.played_at,
    )
    return MatchPlayerStatisticsContextV1(
        player_id=participant.player_id,
        table_place=participant.table_place,
        snapshot_id=snapshot.snapshot_id,
        observed_at=snapshot.observed_at,
        temporal_status=temporal_status,
        eligible_for_match_analysis=temporal_status == "eligible",
        normalized_profile=profile,
        profile_derivation=derivation,
    )
