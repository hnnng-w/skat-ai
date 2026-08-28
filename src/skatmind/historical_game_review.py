from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from skatmind.analysis_report import build_card_analysis_report_from_values
from skatmind.effective_opponent_policy import (
    EffectiveOpponentPolicySettings,
    build_effective_opponent_policy_settings,
)
from skatmind.game_value import get_null_game_value
from skatmind.hidden_card_inference import (
    build_hidden_card_inference_model,
    build_hidden_card_inference_summary,
)
from skatmind.historical_decision_snapshot import (
    HistoricalDecisionSnapshot,
    HistoricalDecisionSnapshotSummary,
)
from skatmind.historical_game import HistoricalGameRecord
from skatmind.historical_opponent_profile_application import (
    build_historical_decision_opponent_profile_application,
    resolve_historical_opponent_profiles_for_decision,
)
from skatmind.historical_opponent_profile_binding import (
    HistoricalOpponentProfileBindings,
)
from skatmind.historical_snapshot_adapter import (
    HistoricalSnapshotPosition,
    build_position_from_historical_snapshot,
)
from skatmind.input_validation import MAX_SAMPLE_COUNT, validate_positive_integer_maximum
from skatmind.post_game_review import (
    ACCEPTABLE_DECISION_QUALITY,
    MISTAKE_DECISION_QUALITY,
    NOT_AVAILABLE_DECISION_QUALITY,
    OPTIMAL_DECISION_QUALITY,
    SUBOPTIMAL_DECISION_QUALITY,
    build_post_game_review_summary,
)
from skatmind.public_hand_constraint import (
    DECLARED_OUVERT_SOURCE,
    build_serializable_public_hand_constraints,
)
from skatmind.recommender import recommend_card_by_expected_value
from skatmind.simulation import DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT

if TYPE_CHECKING:
    from skatmind.historical_review_provenance import (
        HistoricalReviewProvenanceCollector,
    )

HISTORICAL_GAME_REVIEW_SCHEMA_VERSION = 1
HISTORICAL_GAME_REVIEW_ANALYSIS_METHOD = "immediate_expected_value"
HISTORICAL_GAME_REVIEW_INFORMATION_POLICY = "decision_time"
QUALITY_NAMES = (
    OPTIMAL_DECISION_QUALITY,
    ACCEPTABLE_DECISION_QUALITY,
    SUBOPTIMAL_DECISION_QUALITY,
    MISTAKE_DECISION_QUALITY,
    NOT_AVAILABLE_DECISION_QUALITY,
)


@dataclass(frozen=True)
class HistoricalGameReviewSettings:
    """The fixed settings shared by all decisions in one historical review."""

    sample_count: int = DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT
    base_random_seed: int | None = None
    opponent_policy_mode: Literal["default", "external_profiles"] = "default"


@dataclass(frozen=True)
class HistoricalImmediateDecisionPreActualAnalysis:
    """Retained Immediate values produced before the observed card is read."""

    position: HistoricalSnapshotPosition
    effective_random_seed: int | None
    recommended_card: str
    recommendation_reason: str
    analysis_report: tuple[dict[str, Any], ...]
    hidden_card_inference_summary: dict[str, Any] | None
    opponent_profile_application: dict[str, Any] | None


def _build_empty_quality_counts() -> dict[str, int]:
    return {quality: 0 for quality in QUALITY_NAMES}


def _build_decision_identity(
    snapshot: HistoricalDecisionSnapshot,
) -> dict[str, str | int]:
    result: dict[str, str | int] = {
        "source_game_id": snapshot.source_game_id,
        "decision_index": snapshot.decision_index,
        "trick_number": snapshot.trick_number,
        "play_index": snapshot.play_index,
        "acting_player_id": snapshot.acting_player_id,
        "acting_seat": snapshot.acting_seat,
        "acting_side": snapshot.acting_side,
        "actual_card_played": snapshot.actual_card_played,
    }
    if snapshot.source_played_at is not None:
        result["source_played_at"] = snapshot.source_played_at
    return result


def _build_reviewed_decision_pre_actual_analysis(
    snapshot: HistoricalDecisionSnapshot,
    historical_record: HistoricalGameRecord,
    sample_count: int,
    effective_random_seed: int | None,
    opponent_response_policy_by_player: dict[str, str] | None = None,
    opponent_profile_application: dict[str, Any] | None = None,
) -> HistoricalImmediateDecisionPreActualAnalysis:
    position = build_position_from_historical_snapshot(
        snapshot=snapshot,
        historical_record=historical_record,
    )
    hidden_card_inference_model = build_hidden_card_inference_model(
        position.state,
        position.left_hand_size,
        position.right_hand_size,
        position.public_hand_constraints,
    )
    recommended_card, recommendation_reason, values = (
        recommend_card_by_expected_value(
            state=position.state,
            left_hand_size=position.left_hand_size,
            right_hand_size=position.right_hand_size,
            sample_count=sample_count,
            random_seed=effective_random_seed,
            opponent_response_policy_by_player=opponent_response_policy_by_player,
            public_hand_constraints=position.public_hand_constraints,
        )
    )
    analysis_report = build_card_analysis_report_from_values(
        state=position.state,
        values=values,
    )
    recommended_rows = [
        row for row in analysis_report if row["is_recommended"] is True
    ]
    if len(recommended_rows) != 1 or recommended_rows[0]["card"] != recommended_card:
        raise ValueError("Historical recommendation and analysis report are inconsistent.")

    inference_summary = build_hidden_card_inference_summary(
        hidden_card_inference_model
    )
    return HistoricalImmediateDecisionPreActualAnalysis(
        position=position,
        effective_random_seed=effective_random_seed,
        recommended_card=recommended_card,
        recommendation_reason=recommendation_reason,
        analysis_report=tuple(dict(row) for row in analysis_report),
        hidden_card_inference_summary=inference_summary,
        opponent_profile_application=(
            dict(opponent_profile_application)
            if opponent_profile_application is not None
            else None
        ),
    )


def _build_reviewed_decision(
    snapshot: HistoricalDecisionSnapshot,
    historical_record: HistoricalGameRecord,
    sample_count: int,
    effective_random_seed: int | None,
    opponent_response_policy_by_player: dict[str, str] | None = None,
    opponent_profile_application: dict[str, Any] | None = None,
    provenance_collector: HistoricalReviewProvenanceCollector | None = None,
) -> dict[str, Any]:
    pre_actual = _build_reviewed_decision_pre_actual_analysis(
        snapshot=snapshot,
        historical_record=historical_record,
        sample_count=sample_count,
        effective_random_seed=effective_random_seed,
        opponent_response_policy_by_player=opponent_response_policy_by_player,
        opponent_profile_application=opponent_profile_application,
    )
    position = pre_actual.position
    analysis_report = [dict(row) for row in pre_actual.analysis_report]
    if provenance_collector is not None:
        provenance_collector.capture_immediate_analysis(
            snapshot=snapshot,
            document={
                "legal_cards": list(position.legal_cards),
                "recommendation": {
                    "card": pre_actual.recommended_card,
                    "reason": pre_actual.recommendation_reason,
                },
                "analysis_report": analysis_report,
                "hidden_card_inference_summary": (
                    pre_actual.hidden_card_inference_summary
                ),
                "opponent_profile_application": (
                    pre_actual.opponent_profile_application
                ),
            },
        )

    game_value = (
        get_null_game_value(position.game_declaration)
        if position.state.game_type == "null"
        else None
    )
    post_game_review_summary = build_post_game_review_summary(
        actual_card_played=snapshot.actual_card_played,
        analysis_report=analysis_report,
        game_type=position.state.game_type,
        player_role=position.state.player_role,
        game_value=game_value,
    )
    result = {
        **_build_decision_identity(snapshot),
        "status": "reviewed",
        "unavailable_reason": None,
        "effective_random_seed": effective_random_seed,
        "legal_cards": list(position.legal_cards),
        "recommendation": {
            "card": pre_actual.recommended_card,
            "reason": pre_actual.recommendation_reason,
        },
        "analysis_report": analysis_report,
        "post_game_review_summary": post_game_review_summary,
    }
    if pre_actual.opponent_profile_application is not None:
        result["opponent_profile_application"] = (
            pre_actual.opponent_profile_application
        )
    if pre_actual.hidden_card_inference_summary is not None:
        result["hidden_card_inference_summary"] = (
            pre_actual.hidden_card_inference_summary
        )
    if any(
        constraint.source == DECLARED_OUVERT_SOURCE
        for constraint in position.public_hand_constraints
    ):
        result["public_hand_constraints"] = build_serializable_public_hand_constraints(
            position.public_hand_constraints
        )
    if provenance_collector is not None:
        provenance_collector.capture_immediate_assessment(
            snapshot=snapshot,
            document={
                "actual_card_played": snapshot.actual_card_played,
                "post_game_review_summary": post_game_review_summary,
            },
        )
    return result


def _build_decision_profile_application(
    snapshot: HistoricalDecisionSnapshot,
    historical_record: HistoricalGameRecord,
    bindings: HistoricalOpponentProfileBindings,
    opponent_policy_preset_override: str | None,
    opponent_lead_policy_override: str | None,
    opponent_response_policy_override: str | None,
    left_opponent_lead_policy_override: str | None,
    left_opponent_response_policy_override: str | None,
    right_opponent_lead_policy_override: str | None,
    right_opponent_response_policy_override: str | None,
) -> tuple[EffectiveOpponentPolicySettings, dict[str, Any]]:
    profiles = resolve_historical_opponent_profiles_for_decision(
        historical_record,
        snapshot,
        bindings.profiles_by_player_id,
    )
    left_profile = (
        profiles.left.profile
        if profiles.left is not None
        and profiles.left.derivation["actionable_policy_preset"] is not None
        else None
    )
    right_profile = (
        profiles.right.profile
        if profiles.right is not None
        and profiles.right.derivation["actionable_policy_preset"] is not None
        else None
    )
    effective_settings = build_effective_opponent_policy_settings(
        data={"use_profile_presets": True},
        left_player_profile=left_profile,
        right_player_profile=right_profile,
        opponent_policy_preset_override=opponent_policy_preset_override,
        opponent_lead_policy_override=opponent_lead_policy_override,
        opponent_response_policy_override=opponent_response_policy_override,
        left_opponent_lead_policy_override=left_opponent_lead_policy_override,
        left_opponent_response_policy_override=left_opponent_response_policy_override,
        right_opponent_lead_policy_override=right_opponent_lead_policy_override,
        right_opponent_response_policy_override=right_opponent_response_policy_override,
    )
    application = build_historical_decision_opponent_profile_application(
        snapshot.acting_player_id,
        profiles,
        effective_settings,
    )
    return effective_settings, application


def _build_profile_application_counts(
    decisions: list[dict[str, Any]],
) -> dict[str, Any]:
    counts_by_player_id: dict[str, int] = {}
    counts_by_preset: dict[str, int] = {}
    matched_decisions = 0
    applied_left = 0
    applied_right = 0
    no_actionable = 0
    for decision in decisions:
        application = decision["opponent_profile_application"]
        sides = [application["left"], application["right"]]
        if any(side["profile_match_status"] == "matched" for side in sides):
            matched_decisions += 1
        if all(side["actionable_policy_preset"] is None for side in sides):
            no_actionable += 1
        for side_name, side in zip(("left", "right"), sides, strict=True):
            if side["application_status"] != "applied":
                continue
            if side_name == "left":
                applied_left += 1
            else:
                applied_right += 1
            player_id = side["opponent_player_id"]
            preset = side["applied_policy_preset"]
            counts_by_player_id[player_id] = counts_by_player_id.get(player_id, 0) + 1
            counts_by_preset[preset] = counts_by_preset.get(preset, 0) + 1
    return {
        "total_decisions": len(decisions),
        "decisions_with_matched_opponent_profile": matched_decisions,
        "decisions_with_applied_left_profile": applied_left,
        "decisions_with_applied_right_profile": applied_right,
        "decisions_with_no_actionable_external_profile": no_actionable,
        "application_counts_by_player_id": counts_by_player_id,
        "application_counts_by_preset": counts_by_preset,
    }


def _build_player_summaries(
    historical_record: HistoricalGameRecord,
    decisions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    summaries = []
    for player in historical_record.players:
        player_decisions = [
            decision
            for decision in decisions
            if decision["acting_player_id"] == player.player_id
        ]
        quality_counts = _build_empty_quality_counts()
        for decision in player_decisions:
            quality = decision["post_game_review_summary"]["decision_quality"]
            quality_counts[quality] += 1
        reviewed_count = sum(
            decision["status"] == "reviewed" for decision in player_decisions
        )
        unavailable_count = len(player_decisions) - reviewed_count
        summaries.append(
            {
                "player_id": player.player_id,
                "player_label": player.player_label,
                "seat": player.seat,
                "side": (
                    "declarer"
                    if player.player_id == historical_record.declarer_player_id
                    else "defenders"
                ),
                "decision_count": len(player_decisions),
                "reviewed_decision_count": reviewed_count,
                "unavailable_decision_count": unavailable_count,
                "quality_counts": quality_counts,
            }
        )
    return summaries


def build_historical_game_review_summary(
    snapshot_summary: HistoricalDecisionSnapshotSummary,
    historical_record: HistoricalGameRecord,
    sample_count: int = DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT,
    base_random_seed: int | None = None,
    opponent_profile_bindings: HistoricalOpponentProfileBindings | None = None,
    opponent_policy_preset_override: str | None = None,
    opponent_lead_policy_override: str | None = None,
    opponent_response_policy_override: str | None = None,
    left_opponent_lead_policy_override: str | None = None,
    left_opponent_response_policy_override: str | None = None,
    right_opponent_lead_policy_override: str | None = None,
    right_opponent_response_policy_override: str | None = None,
    provenance_collector: HistoricalReviewProvenanceCollector | None = None,
) -> dict[str, Any]:
    """Evaluates all historical decisions through the immediate review pipeline."""
    cardinality = snapshot_summary.cardinality
    if historical_record.game_end_reason != cardinality.game_end_reason:
        raise ValueError(
            "Historical game review record and snapshot end reasons do not match."
        )
    if (
        snapshot_summary.snapshot_count
        != cardinality.expected_review_decision_count
        or len(snapshot_summary.snapshots)
        != cardinality.expected_review_decision_count
    ):
        raise ValueError(
            "Historical game review snapshot count does not match the validated play prefix."
        )
    validate_positive_integer_maximum(
        sample_count,
        "sample_count",
        MAX_SAMPLE_COUNT,
    )

    settings = HistoricalGameReviewSettings(
        sample_count=sample_count,
        base_random_seed=base_random_seed,
        opponent_policy_mode=(
            "external_profiles" if opponent_profile_bindings is not None else "default"
        ),
    )
    decisions = []
    for snapshot in snapshot_summary.snapshots:
        effective_random_seed = (
            None
            if settings.base_random_seed is None
            else settings.base_random_seed + snapshot.decision_index - 1
        )
        effective_policy_settings = None
        opponent_profile_application = None
        if opponent_profile_bindings is not None:
            effective_policy_settings, opponent_profile_application = (
                _build_decision_profile_application(
                    snapshot=snapshot,
                    historical_record=historical_record,
                    bindings=opponent_profile_bindings,
                    opponent_policy_preset_override=opponent_policy_preset_override,
                    opponent_lead_policy_override=opponent_lead_policy_override,
                    opponent_response_policy_override=opponent_response_policy_override,
                    left_opponent_lead_policy_override=(left_opponent_lead_policy_override),
                    left_opponent_response_policy_override=(left_opponent_response_policy_override),
                    right_opponent_lead_policy_override=(right_opponent_lead_policy_override),
                    right_opponent_response_policy_override=(
                        right_opponent_response_policy_override
                    ),
                )
            )
            if provenance_collector is not None:
                provenance_collector.capture_profile_application(
                    snapshot=snapshot,
                    external_profile_application=opponent_profile_application,
                    effective_opponent_policies={
                        "global_lead_policy": (
                            effective_policy_settings.global_lead_policy
                        ),
                        "global_response_policy": (
                            effective_policy_settings.global_response_policy
                        ),
                        "left_lead_policy": effective_policy_settings.left_lead_policy,
                        "left_response_policy": (
                            effective_policy_settings.left_response_policy
                        ),
                        "right_lead_policy": effective_policy_settings.right_lead_policy,
                        "right_response_policy": (
                            effective_policy_settings.right_response_policy
                        ),
                        "immediate_response_policy_by_player": (
                            effective_policy_settings.immediate_response_policy_by_player
                        ),
                    },
                )
        decision = _build_reviewed_decision(
            snapshot=snapshot,
            historical_record=historical_record,
            sample_count=settings.sample_count,
            effective_random_seed=effective_random_seed,
            opponent_response_policy_by_player=(
                effective_policy_settings.immediate_response_policy_by_player
                if effective_policy_settings is not None
                else None
            ),
            opponent_profile_application=opponent_profile_application,
            provenance_collector=provenance_collector,
        )
        decisions.append(decision)

    quality_counts = _build_empty_quality_counts()
    for decision in decisions:
        quality = decision["post_game_review_summary"]["decision_quality"]
        quality_counts[quality] += 1
    reviewed_count = sum(decision["status"] == "reviewed" for decision in decisions)
    unavailable_count = len(decisions) - reviewed_count
    player_summaries = _build_player_summaries(
        historical_record=historical_record,
        decisions=decisions,
    )

    if len(player_summaries) != 3:
        raise ValueError("Historical game review requires exactly three player summaries.")
    if sum(summary["decision_count"] for summary in player_summaries) != len(decisions):
        raise ValueError("Historical player decision totals do not reconcile.")
    if sum(summary["reviewed_decision_count"] for summary in player_summaries) != reviewed_count:
        raise ValueError("Historical player reviewed-decision totals do not reconcile.")
    if sum(
        summary["unavailable_decision_count"] for summary in player_summaries
    ) != unavailable_count:
        raise ValueError("Historical player unavailable-decision totals do not reconcile.")
    for quality in QUALITY_NAMES:
        if sum(
            summary["quality_counts"][quality] for summary in player_summaries
        ) != quality_counts[quality]:
            raise ValueError("Historical player quality totals do not reconcile.")
    if reviewed_count + unavailable_count != len(decisions):
        raise ValueError("Historical review availability totals do not reconcile.")
    if sum(quality_counts.values()) != len(decisions):
        raise ValueError("Historical review quality totals do not reconcile.")
    for summary in player_summaries:
        if (
            summary["reviewed_decision_count"]
            + summary["unavailable_decision_count"]
            != summary["decision_count"]
            or sum(summary["quality_counts"].values()) != summary["decision_count"]
        ):
            raise ValueError("Historical player review counts do not reconcile.")

    result = {
        "schema_version": HISTORICAL_GAME_REVIEW_SCHEMA_VERSION,
        "analysis_method": HISTORICAL_GAME_REVIEW_ANALYSIS_METHOD,
        "information_policy": HISTORICAL_GAME_REVIEW_INFORMATION_POLICY,
        "decision_count": len(decisions),
        "reviewed_decision_count": reviewed_count,
        "unavailable_decision_count": unavailable_count,
        "settings": {
            "sample_count": settings.sample_count,
            "base_random_seed": settings.base_random_seed,
            "opponent_policy_mode": settings.opponent_policy_mode,
        },
        "quality_counts": quality_counts,
        "player_summaries": player_summaries,
        "decisions": decisions,
    }
    if opponent_profile_bindings is not None:
        result["opponent_profile_application_counts"] = _build_profile_application_counts(decisions)
    return result
