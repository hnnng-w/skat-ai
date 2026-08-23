from __future__ import annotations

from collections.abc import Mapping
from dataclasses import InitVar, dataclass
from types import MappingProxyType
from typing import Any

from skat_ai.bounded_search_result import WORLD_COVERAGE_VALUES
from skat_ai.historical_game import (
    HISTORICAL_SEATS,
    HistoricalGameRecord,
    build_historical_game_summary,
)
from skat_ai.historical_information_set_search_review import (
    HISTORICAL_INFORMATION_SET_SEARCH_INFORMATION_POLICY,
    HISTORICAL_INFORMATION_SET_SEARCH_REVIEW_METHOD,
    HISTORICAL_INFORMATION_SET_SEARCH_REVIEW_VERSION,
    HistoricalInformationSetSearchReviewSummaryV1,
    build_serializable_historical_information_set_search_review_settings_v1,
)
from skat_ai.information_set_replay_coaching_assessment import (
    INFORMATION_SET_REPLAY_COACHING_ASSESSMENT_POLICY,
    INFORMATION_SET_REPLAY_COACHING_ASSESSMENT_STATUSES,
    INFORMATION_SET_REPLAY_COACHING_EVIDENCE_BASES,
    INFORMATION_SET_REPLAY_COACHING_IMPACT_TIERS,
    InformationSetReplayCoachingDecisionAssessmentV1,
    build_retained_information_set_replay_coaching_decision_assessment_v1,
    build_serializable_information_set_replay_coaching_decision_assessment_v1,
)
from skat_ai.information_set_replay_coaching_evidence import (
    INFORMATION_SET_REPLAY_COACHING_INFORMATION_POLICY,
    INFORMATION_SET_REPLAY_COACHING_PRIMARY_EVIDENCE_POLICY,
    INFORMATION_SET_REPLAY_COACHING_PUBLIC_POLICY,
    INFORMATION_SET_REPLAY_COACHING_SOURCE_POLICY,
    build_information_set_replay_coaching_decision_time_evidence_v1,
)
from skat_ai.information_set_search_comparison import METHOD_NOT_AVAILABLE
from skat_ai.information_set_search_contracts import INFORMATION_SET_SEARCH_STATUSES
from skat_ai.replay_coaching_guidance import (
    ReplayCoachingGuidanceResult,
    build_replay_coaching_guidance,
    build_serializable_replay_coaching_guidance_result,
)
from skat_ai.replay_coaching_patterns import REPLAY_COACHING_PATTERN_SCOPES
from skat_ai.replay_coaching_prioritization import (
    ReplayCoachingPrioritizationResult,
    build_replay_coaching_prioritization_result,
    build_serializable_replay_coaching_prioritization_result,
    validate_replay_coaching_assessment_sequence,
)
from skat_ai.replay_coaching_report_context import (
    ReplayCoachingGameContext,
    ReplayCoachingOutcomeContext,
    build_replay_coaching_game_context,
    build_replay_coaching_outcome_context,
    build_serializable_replay_coaching_game_context,
    build_serializable_replay_coaching_outcome_context,
)

INFORMATION_SET_REPLAY_COACHING_REPORT_VERSION = 1
INFORMATION_SET_REPLAY_COACHING_METHOD = (
    "historical_information_set_replay_coaching_v1"
)
INFORMATION_SET_REPLAY_COACHING_PRIORITIZATION_POLICY = (
    "existing_objective_priority_without_baseline_fallback"
)
INFORMATION_SET_REPLAY_COACHING_GUIDANCE_POLICY = (
    "existing_deterministic_templates_without_tactical_inference"
)
INFORMATION_SET_REPLAY_COACHING_OUTCOME_POLICY = "final_context_after_coaching"
INFORMATION_SET_REPLAY_COACHING_LIMITATIONS = (
    "outcome_context_not_decision_evidence",
    "single_recorded_game_only",
    "bounded_three_trick_information_set_search",
    "controlled_player_selected_world_consistency",
    "fixed_opponent_policy_model",
    "sampled_compatible_worlds",
    "search_unavailable",
    "observed_card_not_ground_truth",
    "incomplete_assessment_coverage",
    "no_equilibrium_or_global_optimality_claim",
    "no_tactical_motif_inference",
    "no_causal_outcome_claim",
    "no_player_skill_rating",
)

_INFORMATION_SET_STATUS_VALUES = (*INFORMATION_SET_SEARCH_STATUSES, METHOD_NOT_AVAILABLE)
_AGREEMENT_VALUES = ("same", "different", "not_available")
_PRIVATE_REPORT_FIELDS = {
    "initial_hand",
    "initial_hands",
    "hand",
    "hands",
    "skat",
    "skat_cards",
    "discarded_cards",
    "discards",
    "remaining_hands",
    "controlled_policy",
    "information_set",
    "observation",
    "observations",
    "selected_worlds",
    "selected_compatible_worlds",
    "exact_state",
    "exact_states",
    "ownership",
    "ownership_assignments",
    "cache",
    "caches",
    "branches",
    "principal_variation",
    "principal_variations",
    "derived_child_seed",
    "derived_child_seeds",
}


def _freeze_json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {key: _freeze_json_value(item) for key, item in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json_value(item) for item in value)
    return value


def _thaw_json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_json_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json_value(item) for item in value]
    return value


def _validate_public_report(value: Any, field_name: str = "report") -> None:
    if isinstance(value, Mapping):
        private = tuple(key for key in value if key in _PRIVATE_REPORT_FIELDS)
        if private:
            raise ValueError(f"{field_name} contains private fields: {private}.")
        for key, item in value.items():
            _validate_public_report(item, f"{field_name}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _validate_public_report(item, f"{field_name}[{index}]")


def _count_values(
    assessments: tuple[InformationSetReplayCoachingDecisionAssessmentV1, ...],
    field_name: str,
    canonical_values: tuple[str, ...],
) -> tuple[tuple[str, int], ...]:
    return tuple(
        (
            value,
            sum(getattr(assessment, field_name) == value for assessment in assessments),
        )
        for value in canonical_values
    )


def _information_set_status(
    assessment: InformationSetReplayCoachingDecisionAssessmentV1,
) -> str:
    analysis = assessment.decision_time_evidence.information_set_pre_actual_analysis
    if analysis.information_set_result is not None:
        return analysis.information_set_result.status
    if analysis.information_set_public_result is not None:
        status = analysis.information_set_public_result.get("status")
        if isinstance(status, str):
            return status
    return METHOD_NOT_AVAILABLE


def _world_coverage(
    assessment: InformationSetReplayCoachingDecisionAssessmentV1,
) -> str:
    analysis = assessment.decision_time_evidence.information_set_pre_actual_analysis
    if analysis.information_set_result is not None:
        return analysis.information_set_result.world_coverage
    if analysis.information_set_public_result is not None:
        coverage = analysis.information_set_public_result.get("world_coverage")
        if isinstance(coverage, str):
            return coverage
    return "none"


def _agreement(
    assessment: InformationSetReplayCoachingDecisionAssessmentV1,
    field_name: str,
) -> str:
    value = getattr(assessment.comparison, field_name)
    if value is None:
        return "not_available"
    return "same" if value else "different"


def _validate_counts(
    counts: tuple[tuple[str, int], ...],
    canonical_values: tuple[str, ...],
    decision_count: int,
    field_name: str,
) -> None:
    if (
        not isinstance(counts, tuple)
        or tuple(value for value, _count in counts) != canonical_values
        or any(
            isinstance(count, bool) or not isinstance(count, int) or count < 0
            for _value, count in counts
        )
        or sum(count for _value, count in counts) != decision_count
    ):
        raise ValueError(f"{field_name} must be complete canonical counts.")


@dataclass(frozen=True, slots=True, kw_only=True)
class InformationSetReplayCoachingCoverageV1:
    decision_count: int
    assessable_decision_count: int
    forced_move_count: int
    best_or_equivalent_count: int
    strictly_below_best_count: int
    not_assessable_count: int
    high_impact_decision_count: int
    key_decision_count: int
    turning_point_count: int
    pattern_count: int
    actionable_pattern_count: int
    decision_recommendation_count: int
    pattern_recommendation_count: int
    information_set_recommendation_count: int
    pimc_recommendation_count: int
    immediate_recommendation_count: int
    assessment_status_counts: tuple[tuple[str, int], ...]
    evidence_basis_counts: tuple[tuple[str, int], ...]
    impact_tier_counts: tuple[tuple[str, int], ...]
    information_set_status_counts: tuple[tuple[str, int], ...]
    world_coverage_counts: tuple[tuple[str, int], ...]
    information_set_pimc_agreement_counts: tuple[tuple[str, int], ...]
    information_set_immediate_agreement_counts: tuple[tuple[str, int], ...]

    def __post_init__(self) -> None:
        for field_name in (
            "decision_count",
            "assessable_decision_count",
            "forced_move_count",
            "best_or_equivalent_count",
            "strictly_below_best_count",
            "not_assessable_count",
            "high_impact_decision_count",
            "key_decision_count",
            "turning_point_count",
            "pattern_count",
            "actionable_pattern_count",
            "decision_recommendation_count",
            "pattern_recommendation_count",
            "information_set_recommendation_count",
            "pimc_recommendation_count",
            "immediate_recommendation_count",
        ):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer.")
        for field_name, canonical in (
            (
                "assessment_status_counts",
                INFORMATION_SET_REPLAY_COACHING_ASSESSMENT_STATUSES,
            ),
            ("evidence_basis_counts", INFORMATION_SET_REPLAY_COACHING_EVIDENCE_BASES),
            ("impact_tier_counts", INFORMATION_SET_REPLAY_COACHING_IMPACT_TIERS),
            ("information_set_status_counts", _INFORMATION_SET_STATUS_VALUES),
            ("world_coverage_counts", WORLD_COVERAGE_VALUES),
            ("information_set_pimc_agreement_counts", _AGREEMENT_VALUES),
            ("information_set_immediate_agreement_counts", _AGREEMENT_VALUES),
        ):
            _validate_counts(
                getattr(self, field_name),
                canonical,
                self.decision_count,
                field_name,
            )
        statuses = dict(self.assessment_status_counts)
        if (
            self.assessable_decision_count + self.not_assessable_count
            != self.decision_count
            or self.forced_move_count != statuses["forced_move"]
            or self.best_or_equivalent_count != statuses["best_or_equivalent"]
            or self.strictly_below_best_count != statuses["strictly_below_best"]
            or self.not_assessable_count != statuses["not_assessable"]
        ):
            raise ValueError("Coverage assessment counts do not reconcile.")


@dataclass(frozen=True, slots=True, kw_only=True)
class InformationSetReplayCoachingScopeSummaryV1:
    scope: str
    scope_value: str
    decision_count: int
    assessable_decision_count: int
    forced_move_count: int
    best_or_equivalent_count: int
    strictly_below_best_count: int
    not_assessable_count: int
    high_impact_decision_count: int
    key_decision_count: int
    turning_point_count: int
    pattern_count: int
    actionable_pattern_count: int
    decision_recommendation_count: int
    pattern_recommendation_count: int
    decision_indices: tuple[int, ...]
    key_decision_indices: tuple[int, ...]
    turning_point_indices: tuple[int, ...]
    assessment_status_counts: tuple[tuple[str, int], ...]
    evidence_basis_counts: tuple[tuple[str, int], ...]
    impact_tier_counts: tuple[tuple[str, int], ...]

    def __post_init__(self) -> None:
        if self.scope not in REPLAY_COACHING_PATTERN_SCOPES:
            raise ValueError("scope is unsupported.")
        for field_name in (
            "decision_count",
            "assessable_decision_count",
            "forced_move_count",
            "best_or_equivalent_count",
            "strictly_below_best_count",
            "not_assessable_count",
            "high_impact_decision_count",
            "key_decision_count",
            "turning_point_count",
            "pattern_count",
            "actionable_pattern_count",
            "decision_recommendation_count",
            "pattern_recommendation_count",
        ):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer.")
        for field_name in (
            "decision_indices",
            "key_decision_indices",
            "turning_point_indices",
        ):
            values = getattr(self, field_name)
            if values != tuple(sorted(set(values))) or any(
                isinstance(value, bool) or not isinstance(value, int) or value <= 0
                for value in values
            ):
                raise ValueError(f"{field_name} must use unique chronological indices.")
        if len(self.decision_indices) != self.decision_count:
            raise ValueError("decision_indices do not reconcile.")
        if len(self.key_decision_indices) != self.key_decision_count:
            raise ValueError("key_decision_indices do not reconcile.")
        if not set(self.key_decision_indices).issubset(self.decision_indices):
            raise ValueError("Key Decision indices must be scope decision indices.")
        if not set(self.turning_point_indices).issubset(self.decision_indices):
            raise ValueError("Turning Point indices must be scope decision indices.")
        if self.turning_point_count < len(self.turning_point_indices):
            raise ValueError("Turning Point count cannot be below its unique decisions.")
        if self.high_impact_decision_count > self.decision_count:
            raise ValueError("High-impact decisions must be scope decisions.")
        for field_name, canonical in (
            (
                "assessment_status_counts",
                INFORMATION_SET_REPLAY_COACHING_ASSESSMENT_STATUSES,
            ),
            ("evidence_basis_counts", INFORMATION_SET_REPLAY_COACHING_EVIDENCE_BASES),
            ("impact_tier_counts", INFORMATION_SET_REPLAY_COACHING_IMPACT_TIERS),
        ):
            _validate_counts(
                getattr(self, field_name),
                canonical,
                self.decision_count,
                field_name,
            )
        statuses = dict(self.assessment_status_counts)
        if (
            self.assessable_decision_count
            != self.decision_count - statuses["not_assessable"]
            or self.forced_move_count != statuses["forced_move"]
            or self.best_or_equivalent_count != statuses["best_or_equivalent"]
            or self.strictly_below_best_count != statuses["strictly_below_best"]
            or self.not_assessable_count != statuses["not_assessable"]
        ):
            raise ValueError("Scope assessment counts do not reconcile.")


def _validate_source_review(
    record: HistoricalGameRecord,
    review: HistoricalInformationSetSearchReviewSummaryV1,
    assessments: tuple[InformationSetReplayCoachingDecisionAssessmentV1, ...],
) -> None:
    if not isinstance(review, HistoricalInformationSetSearchReviewSummaryV1):
        raise ValueError("review has the wrong type.")
    if (
        review.schema_version != HISTORICAL_INFORMATION_SET_SEARCH_REVIEW_VERSION
        or review.review_method != HISTORICAL_INFORMATION_SET_SEARCH_REVIEW_METHOD
        or review.information_policy
        != HISTORICAL_INFORMATION_SET_SEARCH_INFORMATION_POLICY
        or review.source_game_id != record.game_id
        or review.game_end_reason != record.game_end_reason
        or review.metrics.decision_count != len(review.decisions)
        or len(review.decisions) != len(assessments)
    ):
        raise ValueError("Retained Historical Information-set Review does not reconcile.")
    validate_replay_coaching_assessment_sequence(record, assessments)
    for decision, assessment in zip(review.decisions, assessments, strict=True):
        expected_evidence = (
            build_information_set_replay_coaching_decision_time_evidence_v1(
                decision
            )
        )
        if (
            assessment.decision_time_evidence != expected_evidence
            or assessment.actual_card != decision.actual_card
            or assessment.comparison != decision.comparison
        ):
            raise ValueError("Assessment does not reuse its exact retained review row.")


@dataclass(frozen=True, slots=True, kw_only=True)
class InformationSetReplayCoachingAnalysisV1:
    source_review: HistoricalInformationSetSearchReviewSummaryV1
    assessments: tuple[InformationSetReplayCoachingDecisionAssessmentV1, ...]
    prioritization: ReplayCoachingPrioritizationResult
    guidance: ReplayCoachingGuidanceResult
    historical_record: InitVar[HistoricalGameRecord]

    def __post_init__(self, historical_record: HistoricalGameRecord) -> None:
        if not isinstance(self.assessments, tuple):
            raise TypeError("assessments must be a tuple.")
        _validate_source_review(historical_record, self.source_review, self.assessments)
        expected_prioritization = build_replay_coaching_prioritization_result(
            historical_record,
            self.assessments,
        )
        expected_guidance = build_replay_coaching_guidance(
            historical_record,
            self.assessments,
            expected_prioritization,
        )
        if (
            self.prioritization != expected_prioritization
            or self.guidance != expected_guidance
        ):
            raise ValueError("Information-set Coaching artifacts do not reconcile.")


def build_information_set_replay_coaching_analysis_v1(
    historical_record: HistoricalGameRecord,
    source_review: HistoricalInformationSetSearchReviewSummaryV1,
) -> InformationSetReplayCoachingAnalysisV1:
    """Builds assessments and shared Coaching artifacts without rerunning analysis."""
    assessments = tuple(
        build_retained_information_set_replay_coaching_decision_assessment_v1(
            decision
        )
        for decision in source_review.decisions
    )
    prioritization = build_replay_coaching_prioritization_result(
        historical_record,
        assessments,
    )
    guidance = build_replay_coaching_guidance(
        historical_record,
        assessments,
        prioritization,
    )
    return InformationSetReplayCoachingAnalysisV1(
        source_review=source_review,
        assessments=assessments,
        prioritization=prioritization,
        guidance=guidance,
        historical_record=historical_record,
    )


def _build_coverage(
    analysis: InformationSetReplayCoachingAnalysisV1,
) -> InformationSetReplayCoachingCoverageV1:
    assessments = analysis.assessments
    statuses = _count_values(
        assessments,
        "assessment_status",
        INFORMATION_SET_REPLAY_COACHING_ASSESSMENT_STATUSES,
    )
    status_counts = dict(statuses)
    information_results = tuple(
        assessment.decision_time_evidence.information_set_pre_actual_analysis
        for assessment in assessments
    )
    return InformationSetReplayCoachingCoverageV1(
        decision_count=len(assessments),
        assessable_decision_count=(len(assessments) - status_counts["not_assessable"]),
        forced_move_count=status_counts["forced_move"],
        best_or_equivalent_count=status_counts["best_or_equivalent"],
        strictly_below_best_count=status_counts["strictly_below_best"],
        not_assessable_count=status_counts["not_assessable"],
        high_impact_decision_count=(analysis.prioritization.high_impact_decision_count),
        key_decision_count=len(analysis.prioritization.key_decisions),
        turning_point_count=len(analysis.prioritization.turning_points),
        pattern_count=analysis.guidance.pattern_count,
        actionable_pattern_count=analysis.guidance.actionable_pattern_count,
        decision_recommendation_count=(analysis.guidance.decision_recommendation_count),
        pattern_recommendation_count=(analysis.guidance.pattern_recommendation_count),
        information_set_recommendation_count=sum(
            item.information_set_result is not None
            and item.information_set_result.recommended_card is not None
            for item in information_results
        ),
        pimc_recommendation_count=sum(
            item.pimc_result is not None and item.pimc_result.recommended_card is not None
            for item in information_results
        ),
        immediate_recommendation_count=sum(
            item.immediate_recommended_card is not None for item in information_results
        ),
        assessment_status_counts=statuses,
        evidence_basis_counts=_count_values(
            assessments,
            "evidence_basis",
            INFORMATION_SET_REPLAY_COACHING_EVIDENCE_BASES,
        ),
        impact_tier_counts=_count_values(
            assessments,
            "impact_tier",
            INFORMATION_SET_REPLAY_COACHING_IMPACT_TIERS,
        ),
        information_set_status_counts=tuple(
            (
                status,
                sum(_information_set_status(item) == status for item in assessments),
            )
            for status in _INFORMATION_SET_STATUS_VALUES
        ),
        world_coverage_counts=tuple(
            (
                coverage,
                sum(_world_coverage(item) == coverage for item in assessments),
            )
            for coverage in WORLD_COVERAGE_VALUES
        ),
        information_set_pimc_agreement_counts=tuple(
            (
                value,
                sum(
                    _agreement(item, "information_set_pimc_same_card") == value
                    for item in assessments
                ),
            )
            for value in _AGREEMENT_VALUES
        ),
        information_set_immediate_agreement_counts=tuple(
            (
                value,
                sum(
                    _agreement(item, "information_set_immediate_same_card")
                    == value
                    for item in assessments
                ),
            )
            for value in _AGREEMENT_VALUES
        ),
    )


def _scope_value(
    assessment: InformationSetReplayCoachingDecisionAssessmentV1,
    scope: str,
) -> str:
    evidence = assessment.decision_time_evidence
    return {
        "player": evidence.acting_player_id,
        "role": evidence.local_side,
        "phase": evidence.game_phase,
        "contract": evidence.game_type,
    }[scope]


def _build_scope_summary(
    analysis: InformationSetReplayCoachingAnalysisV1,
    scope: str,
    scope_value: str,
) -> InformationSetReplayCoachingScopeSummaryV1:
    assessments = tuple(
        item
        for item in analysis.assessments
        if _scope_value(item, scope) == scope_value
    )
    decision_indices = tuple(
        item.decision_time_evidence.decision_index for item in assessments
    )
    key_decisions = tuple(
        item
        for item in analysis.prioritization.key_decisions
        if _scope_value(item.assessment, scope) == scope_value
    )
    turning_points = tuple(
        item
        for item in analysis.prioritization.turning_points
        if _scope_value(item.assessment, scope) == scope_value
    )
    patterns = tuple(
        item
        for item in analysis.guidance.patterns
        if item.scope == scope and item.scope_value == scope_value
    )
    decision_recommendations = tuple(
        item
        for item in analysis.guidance.decision_recommendations
        if _scope_value(item.key_decision.assessment, scope) == scope_value
    )
    pattern_recommendations = tuple(
        item
        for item in analysis.guidance.pattern_recommendations
        if item.pattern.scope == scope and item.pattern.scope_value == scope_value
    )
    high_indices = {
        item.assessment.decision_time_evidence.decision_index
        for item in analysis.prioritization.key_decisions
        if item.is_high_impact
    }
    high_indices.update(
        item.assessment.decision_time_evidence.decision_index
        for item in analysis.prioritization.turning_points
    )
    statuses = _count_values(
        assessments,
        "assessment_status",
        INFORMATION_SET_REPLAY_COACHING_ASSESSMENT_STATUSES,
    )
    status_counts = dict(statuses)
    return InformationSetReplayCoachingScopeSummaryV1(
        scope=scope,
        scope_value=scope_value,
        decision_count=len(assessments),
        assessable_decision_count=len(assessments) - status_counts["not_assessable"],
        forced_move_count=status_counts["forced_move"],
        best_or_equivalent_count=status_counts["best_or_equivalent"],
        strictly_below_best_count=status_counts["strictly_below_best"],
        not_assessable_count=status_counts["not_assessable"],
        high_impact_decision_count=sum(
            index in high_indices for index in decision_indices
        ),
        key_decision_count=len(key_decisions),
        turning_point_count=len(turning_points),
        pattern_count=len(patterns),
        actionable_pattern_count=sum(item.is_actionable for item in patterns),
        decision_recommendation_count=len(decision_recommendations),
        pattern_recommendation_count=len(pattern_recommendations),
        decision_indices=decision_indices,
        key_decision_indices=tuple(
            sorted(
                item.assessment.decision_time_evidence.decision_index
                for item in key_decisions
            )
        ),
        turning_point_indices=tuple(
            sorted(
                {
                    item.assessment.decision_time_evidence.decision_index
                    for item in turning_points
                }
            )
        ),
        assessment_status_counts=statuses,
        evidence_basis_counts=_count_values(
            assessments,
            "evidence_basis",
            INFORMATION_SET_REPLAY_COACHING_EVIDENCE_BASES,
        ),
        impact_tier_counts=_count_values(
            assessments,
            "impact_tier",
            INFORMATION_SET_REPLAY_COACHING_IMPACT_TIERS,
        ),
    )


def _build_scope_summaries(
    record: HistoricalGameRecord,
    analysis: InformationSetReplayCoachingAnalysisV1,
) -> tuple[
    tuple[InformationSetReplayCoachingScopeSummaryV1, ...],
    tuple[InformationSetReplayCoachingScopeSummaryV1, ...],
    tuple[InformationSetReplayCoachingScopeSummaryV1, ...],
    tuple[InformationSetReplayCoachingScopeSummaryV1, ...],
]:
    players_by_seat = {player.seat: player.player_id for player in record.players}
    values = {
        "player": tuple(players_by_seat[seat] for seat in HISTORICAL_SEATS),
        "role": ("declarer", "defenders"),
        "phase": ("opening", "middle", "endgame"),
        "contract": (record.declaration.game_type,),
    }
    groups = tuple(
        tuple(
            _build_scope_summary(analysis, scope, scope_value)
            for scope_value in values[scope]
        )
        for scope in REPLAY_COACHING_PATTERN_SCOPES
    )
    coverage = _build_coverage(analysis)
    for scope, summaries in zip(REPLAY_COACHING_PATTERN_SCOPES, groups, strict=True):
        for field_name in (
            "decision_count",
            "assessable_decision_count",
            "forced_move_count",
            "best_or_equivalent_count",
            "strictly_below_best_count",
            "not_assessable_count",
            "high_impact_decision_count",
            "key_decision_count",
            "turning_point_count",
            "decision_recommendation_count",
        ):
            if sum(getattr(item, field_name) for item in summaries) != getattr(
                coverage,
                field_name,
            ):
                raise ValueError(f"{scope} {field_name} totals do not reconcile.")
    return groups


def _build_report_limitations(
    assessments: tuple[InformationSetReplayCoachingDecisionAssessmentV1, ...],
) -> tuple[str, ...]:
    selected = {
        "outcome_context_not_decision_evidence",
        "single_recorded_game_only",
        "observed_card_not_ground_truth",
        "no_equilibrium_or_global_optimality_claim",
        "no_tactical_motif_inference",
        "no_causal_outcome_claim",
        "no_player_skill_rating",
    }
    if assessments:
        selected.update(
            {
                "bounded_three_trick_information_set_search",
                "fixed_opponent_policy_model",
            }
        )
    if any(item.evidence_basis != "none" for item in assessments):
        selected.add("controlled_player_selected_world_consistency")
    if any(
        item.evidence_basis == "information_set_sampled_compatible_worlds"
        for item in assessments
    ):
        selected.add("sampled_compatible_worlds")
    if any(item.evidence_basis == "none" for item in assessments):
        selected.add("search_unavailable")
    if any(item.assessment_status == "not_assessable" for item in assessments):
        selected.add("incomplete_assessment_coverage")
    return tuple(
        value
        for value in INFORMATION_SET_REPLAY_COACHING_LIMITATIONS
        if value in selected
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class InformationSetReplayCoachingReportV1:
    report_version: int
    report_method: str
    source_policy: str
    information_policy: str
    primary_evidence_policy: str
    assessment_policy: str
    prioritization_policy: str
    guidance_policy: str
    outcome_policy: str
    public_policy: str
    source_game_id: str
    source_review_method: str
    source_review_settings: Mapping[str, Any]
    game_context: ReplayCoachingGameContext
    assessments: tuple[InformationSetReplayCoachingDecisionAssessmentV1, ...]
    prioritization: ReplayCoachingPrioritizationResult
    guidance: ReplayCoachingGuidanceResult
    coverage: InformationSetReplayCoachingCoverageV1
    player_summaries: tuple[InformationSetReplayCoachingScopeSummaryV1, ...]
    role_summaries: tuple[InformationSetReplayCoachingScopeSummaryV1, ...]
    phase_summaries: tuple[InformationSetReplayCoachingScopeSummaryV1, ...]
    contract_summaries: tuple[InformationSetReplayCoachingScopeSummaryV1, ...]
    outcome_context: ReplayCoachingOutcomeContext
    limitations: tuple[str, ...]
    historical_record: InitVar[HistoricalGameRecord]
    coaching_analysis: InitVar[InformationSetReplayCoachingAnalysisV1]
    historical_game_summary: InitVar[Mapping[str, Any] | None] = None

    def __post_init__(
        self,
        historical_record: HistoricalGameRecord,
        coaching_analysis: InformationSetReplayCoachingAnalysisV1,
        historical_game_summary: Mapping[str, Any] | None,
    ) -> None:
        if (
            isinstance(self.report_version, bool)
            or not isinstance(self.report_version, int)
            or self.report_version != INFORMATION_SET_REPLAY_COACHING_REPORT_VERSION
            or self.report_method != INFORMATION_SET_REPLAY_COACHING_METHOD
            or self.source_policy != INFORMATION_SET_REPLAY_COACHING_SOURCE_POLICY
            or self.information_policy
            != INFORMATION_SET_REPLAY_COACHING_INFORMATION_POLICY
            or self.primary_evidence_policy
            != INFORMATION_SET_REPLAY_COACHING_PRIMARY_EVIDENCE_POLICY
            or self.assessment_policy
            != INFORMATION_SET_REPLAY_COACHING_ASSESSMENT_POLICY
            or self.prioritization_policy
            != INFORMATION_SET_REPLAY_COACHING_PRIORITIZATION_POLICY
            or self.guidance_policy != INFORMATION_SET_REPLAY_COACHING_GUIDANCE_POLICY
            or self.outcome_policy != INFORMATION_SET_REPLAY_COACHING_OUTCOME_POLICY
            or self.public_policy != INFORMATION_SET_REPLAY_COACHING_PUBLIC_POLICY
        ):
            raise ValueError("Information-set Replay Coaching report metadata is invalid.")
        _validate_source_review(
            historical_record,
            coaching_analysis.source_review,
            coaching_analysis.assessments,
        )
        expected_settings = (
            build_serializable_historical_information_set_search_review_settings_v1(
                coaching_analysis.source_review.settings
            )
        )
        if (
            self.source_game_id != historical_record.game_id
            or self.source_review_method
            != HISTORICAL_INFORMATION_SET_SEARCH_REVIEW_METHOD
            or _thaw_json_value(self.source_review_settings) != expected_settings
            or self.assessments is not coaching_analysis.assessments
            or self.prioritization is not coaching_analysis.prioritization
            or self.guidance is not coaching_analysis.guidance
        ):
            raise ValueError("Report must reuse the exact retained Coaching analysis.")
        expected_game_context = build_replay_coaching_game_context(
            historical_record,
            recorded_decision_count=len(self.assessments),
        )
        retained_summary = (
            build_historical_game_summary(historical_record)
            if historical_game_summary is None
            else historical_game_summary
        )
        expected_outcome_context = build_replay_coaching_outcome_context(
            historical_record,
            retained_summary,
        )
        expected_coverage = _build_coverage(coaching_analysis)
        expected_scopes = _build_scope_summaries(
            historical_record,
            coaching_analysis,
        )
        if (
            self.game_context != expected_game_context
            or self.outcome_context != expected_outcome_context
            or self.coverage != expected_coverage
            or (
                self.player_summaries,
                self.role_summaries,
                self.phase_summaries,
                self.contract_summaries,
            )
            != expected_scopes
            or self.limitations != _build_report_limitations(self.assessments)
        ):
            raise ValueError("Information-set Replay Coaching report does not reconcile.")
        object.__setattr__(
            self,
            "source_review_settings",
            _freeze_json_value(self.source_review_settings),
        )


def build_information_set_replay_coaching_report_v1(
    historical_record: HistoricalGameRecord,
    source_review: HistoricalInformationSetSearchReviewSummaryV1,
    historical_game_summary: Mapping[str, Any] | None = None,
) -> InformationSetReplayCoachingReportV1:
    """Composes the privacy-safe report from one retained review without reruns."""
    analysis = build_information_set_replay_coaching_analysis_v1(
        historical_record,
        source_review,
    )
    game_context = build_replay_coaching_game_context(
        historical_record,
        recorded_decision_count=len(analysis.assessments),
    )
    coverage = _build_coverage(analysis)
    player, role, phase, contract = _build_scope_summaries(
        historical_record,
        analysis,
    )
    retained_summary = (
        build_historical_game_summary(historical_record)
        if historical_game_summary is None
        else historical_game_summary
    )
    # Outcome is deliberately attached only after every Coaching artifact exists.
    outcome_context = build_replay_coaching_outcome_context(
        historical_record,
        retained_summary,
    )
    return InformationSetReplayCoachingReportV1(
        report_version=INFORMATION_SET_REPLAY_COACHING_REPORT_VERSION,
        report_method=INFORMATION_SET_REPLAY_COACHING_METHOD,
        source_policy=INFORMATION_SET_REPLAY_COACHING_SOURCE_POLICY,
        information_policy=INFORMATION_SET_REPLAY_COACHING_INFORMATION_POLICY,
        primary_evidence_policy=INFORMATION_SET_REPLAY_COACHING_PRIMARY_EVIDENCE_POLICY,
        assessment_policy=INFORMATION_SET_REPLAY_COACHING_ASSESSMENT_POLICY,
        prioritization_policy=INFORMATION_SET_REPLAY_COACHING_PRIORITIZATION_POLICY,
        guidance_policy=INFORMATION_SET_REPLAY_COACHING_GUIDANCE_POLICY,
        outcome_policy=INFORMATION_SET_REPLAY_COACHING_OUTCOME_POLICY,
        public_policy=INFORMATION_SET_REPLAY_COACHING_PUBLIC_POLICY,
        source_game_id=historical_record.game_id,
        source_review_method=HISTORICAL_INFORMATION_SET_SEARCH_REVIEW_METHOD,
        source_review_settings=(
            build_serializable_historical_information_set_search_review_settings_v1(
                source_review.settings
            )
        ),
        game_context=game_context,
        assessments=analysis.assessments,
        prioritization=analysis.prioritization,
        guidance=analysis.guidance,
        coverage=coverage,
        player_summaries=player,
        role_summaries=role,
        phase_summaries=phase,
        contract_summaries=contract,
        outcome_context=outcome_context,
        limitations=_build_report_limitations(analysis.assessments),
        historical_record=historical_record,
        coaching_analysis=analysis,
        historical_game_summary=retained_summary,
    )


def _serialize_counts(
    counts: tuple[tuple[str, int], ...],
    value_name: str,
) -> list[dict[str, str | int]]:
    return [{value_name: value, "count": count} for value, count in counts]


def _build_serializable_coverage(
    coverage: InformationSetReplayCoachingCoverageV1,
) -> dict[str, Any]:
    return {
        "decision_count": coverage.decision_count,
        "assessable_decision_count": coverage.assessable_decision_count,
        "forced_move_count": coverage.forced_move_count,
        "best_or_equivalent_count": coverage.best_or_equivalent_count,
        "strictly_below_best_count": coverage.strictly_below_best_count,
        "not_assessable_count": coverage.not_assessable_count,
        "high_impact_decision_count": coverage.high_impact_decision_count,
        "key_decision_count": coverage.key_decision_count,
        "turning_point_count": coverage.turning_point_count,
        "pattern_count": coverage.pattern_count,
        "actionable_pattern_count": coverage.actionable_pattern_count,
        "decision_recommendation_count": coverage.decision_recommendation_count,
        "pattern_recommendation_count": coverage.pattern_recommendation_count,
        "information_set_recommendation_count": (
            coverage.information_set_recommendation_count
        ),
        "pimc_recommendation_count": coverage.pimc_recommendation_count,
        "immediate_recommendation_count": coverage.immediate_recommendation_count,
        "assessment_status_counts": _serialize_counts(
            coverage.assessment_status_counts,
            "assessment_status",
        ),
        "evidence_basis_counts": _serialize_counts(
            coverage.evidence_basis_counts,
            "evidence_basis",
        ),
        "impact_tier_counts": _serialize_counts(
            coverage.impact_tier_counts,
            "impact_tier",
        ),
        "information_set_status_counts": _serialize_counts(
            coverage.information_set_status_counts,
            "information_set_status",
        ),
        "world_coverage_counts": _serialize_counts(
            coverage.world_coverage_counts,
            "world_coverage",
        ),
        "information_set_pimc_agreement_counts": _serialize_counts(
            coverage.information_set_pimc_agreement_counts,
            "agreement",
        ),
        "information_set_immediate_agreement_counts": _serialize_counts(
            coverage.information_set_immediate_agreement_counts,
            "agreement",
        ),
    }


def _build_serializable_scope_summary(
    summary: InformationSetReplayCoachingScopeSummaryV1,
) -> dict[str, Any]:
    return {
        "scope": summary.scope,
        "scope_value": summary.scope_value,
        "decision_count": summary.decision_count,
        "assessable_decision_count": summary.assessable_decision_count,
        "forced_move_count": summary.forced_move_count,
        "best_or_equivalent_count": summary.best_or_equivalent_count,
        "strictly_below_best_count": summary.strictly_below_best_count,
        "not_assessable_count": summary.not_assessable_count,
        "high_impact_decision_count": summary.high_impact_decision_count,
        "key_decision_count": summary.key_decision_count,
        "turning_point_count": summary.turning_point_count,
        "pattern_count": summary.pattern_count,
        "actionable_pattern_count": summary.actionable_pattern_count,
        "decision_recommendation_count": summary.decision_recommendation_count,
        "pattern_recommendation_count": summary.pattern_recommendation_count,
        "decision_indices": list(summary.decision_indices),
        "key_decision_indices": list(summary.key_decision_indices),
        "turning_point_indices": list(summary.turning_point_indices),
        "assessment_status_counts": _serialize_counts(
            summary.assessment_status_counts,
            "assessment_status",
        ),
        "evidence_basis_counts": _serialize_counts(
            summary.evidence_basis_counts,
            "evidence_basis",
        ),
        "impact_tier_counts": _serialize_counts(
            summary.impact_tier_counts,
            "impact_tier",
        ),
    }


def build_serializable_information_set_replay_coaching_report_v1(
    report: InformationSetReplayCoachingReportV1,
) -> dict[str, Any]:
    """Serializes only aggregate evidence and existing privacy-safe contexts."""
    if not isinstance(report, InformationSetReplayCoachingReportV1):
        raise ValueError("report has the wrong type.")
    result = {
        "report_version": report.report_version,
        "report_method": report.report_method,
        "source_policy": report.source_policy,
        "information_policy": report.information_policy,
        "primary_evidence_policy": report.primary_evidence_policy,
        "assessment_policy": report.assessment_policy,
        "prioritization_policy": report.prioritization_policy,
        "guidance_policy": report.guidance_policy,
        "outcome_policy": report.outcome_policy,
        "public_policy": report.public_policy,
        "source_game_id": report.source_game_id,
        "source_review_method": report.source_review_method,
        "source_review_settings": _thaw_json_value(report.source_review_settings),
        "game_context": build_serializable_replay_coaching_game_context(
            report.game_context
        ),
        "assessments": [
            build_serializable_information_set_replay_coaching_decision_assessment_v1(
                assessment
            )
            for assessment in report.assessments
        ],
        "prioritization": build_serializable_replay_coaching_prioritization_result(
            report.prioritization,
            assessment_serializer=(
                build_serializable_information_set_replay_coaching_decision_assessment_v1
            ),
        ),
        "guidance": build_serializable_replay_coaching_guidance_result(
            report.guidance,
            assessment_serializer=(
                build_serializable_information_set_replay_coaching_decision_assessment_v1
            ),
        ),
        "coverage": _build_serializable_coverage(report.coverage),
        "player_summaries": [
            _build_serializable_scope_summary(item) for item in report.player_summaries
        ],
        "role_summaries": [
            _build_serializable_scope_summary(item) for item in report.role_summaries
        ],
        "phase_summaries": [
            _build_serializable_scope_summary(item) for item in report.phase_summaries
        ],
        "contract_summaries": [
            _build_serializable_scope_summary(item) for item in report.contract_summaries
        ],
        "outcome_context": build_serializable_replay_coaching_outcome_context(
            report.outcome_context
        ),
        "limitations": list(report.limitations),
    }
    _validate_public_report(result)
    return result
