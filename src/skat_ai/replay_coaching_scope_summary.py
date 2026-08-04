from dataclasses import dataclass
from typing import Any

from skat_ai.bounded_search_result import BOUNDED_SEARCH_STATUSES, WORLD_COVERAGE_VALUES
from skat_ai.historical_game import HISTORICAL_SEATS, HistoricalGameRecord
from skat_ai.historical_search_review import HistoricalSearchReviewCoachingAnalysis
from skat_ai.replay_coaching_assessment import (
    REPLAY_COACHING_ASSESSMENT_STATUSES,
    REPLAY_COACHING_EVIDENCE_BASES,
    REPLAY_COACHING_IMPACT_TIERS,
    ReplayCoachingDecisionAssessment,
)
from skat_ai.replay_coaching_patterns import REPLAY_COACHING_PATTERN_SCOPES


def _decision_index(assessment: ReplayCoachingDecisionAssessment) -> int:
    return assessment.decision_time_evidence.decision_index


def _count_values(
    assessments: tuple[ReplayCoachingDecisionAssessment, ...],
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


def _serialize_counts(
    counts: tuple[tuple[str, int], ...],
    value_name: str,
) -> list[dict[str, str | int]]:
    return [{value_name: value, "count": count} for value, count in counts]


def _validate_counts(
    counts: tuple[tuple[str, int], ...],
    canonical_values: tuple[str, ...],
    field_name: str,
) -> None:
    if (
        not isinstance(counts, tuple)
        or tuple(value for value, _ in counts) != canonical_values
        or any(
            isinstance(count, bool) or not isinstance(count, int) or count < 0
            for _, count in counts
        )
    ):
        raise ValueError(f"{field_name} must use canonical non-negative counts.")


@dataclass(frozen=True)
class ReplayCoachingCoverageSummary:
    """Canonical report-wide assessment and evidence coverage."""

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
    search_recommendation_count: int
    immediate_available_count: int
    assessment_status_counts: tuple[tuple[str, int], ...]
    evidence_basis_counts: tuple[tuple[str, int], ...]
    impact_tier_counts: tuple[tuple[str, int], ...]
    search_status_counts: tuple[tuple[str, int], ...]
    world_coverage_counts: tuple[tuple[str, int], ...]

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
            "search_recommendation_count",
            "immediate_available_count",
        ):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer.")
        _validate_counts(
            self.assessment_status_counts,
            REPLAY_COACHING_ASSESSMENT_STATUSES,
            "assessment_status_counts",
        )
        _validate_counts(
            self.evidence_basis_counts,
            REPLAY_COACHING_EVIDENCE_BASES,
            "evidence_basis_counts",
        )
        _validate_counts(
            self.impact_tier_counts,
            REPLAY_COACHING_IMPACT_TIERS,
            "impact_tier_counts",
        )
        _validate_counts(
            self.search_status_counts,
            BOUNDED_SEARCH_STATUSES,
            "search_status_counts",
        )
        _validate_counts(
            self.world_coverage_counts,
            WORLD_COVERAGE_VALUES,
            "world_coverage_counts",
        )
        if any(
            sum(count for _, count in counts) != self.decision_count
            for counts in (
                self.assessment_status_counts,
                self.evidence_basis_counts,
                self.impact_tier_counts,
                self.search_status_counts,
                self.world_coverage_counts,
            )
        ):
            raise ValueError("Coverage count tuples must reconcile with decision_count.")
        if self.assessable_decision_count + self.not_assessable_count != self.decision_count:
            raise ValueError("Assessment coverage counts do not reconcile.")
        statuses = dict(self.assessment_status_counts)
        if (
            self.forced_move_count != statuses["forced_move"]
            or self.best_or_equivalent_count != statuses["best_or_equivalent"]
            or self.strictly_below_best_count != statuses["strictly_below_best"]
            or self.not_assessable_count != statuses["not_assessable"]
        ):
            raise ValueError("Assessment status fields do not reconcile with counts.")


@dataclass(frozen=True)
class ReplayCoachingScopeSummary:
    """One ungraded report summary for a player, role, phase, or contract."""

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
    decision_indices: tuple[int, ...]
    key_decision_indices: tuple[int, ...]
    turning_point_indices: tuple[int, ...]
    pattern_count: int
    actionable_pattern_count: int
    decision_recommendation_count: int
    pattern_recommendation_count: int
    assessment_status_counts: tuple[tuple[str, int], ...]
    evidence_basis_counts: tuple[tuple[str, int], ...]
    impact_tier_counts: tuple[tuple[str, int], ...]

    def __post_init__(self) -> None:
        if self.scope not in REPLAY_COACHING_PATTERN_SCOPES:
            raise ValueError("Unsupported Replay Coaching summary scope.")
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
            if (
                not isinstance(values, tuple)
                or values != tuple(sorted(set(values)))
                or any(
                    isinstance(value, bool) or not isinstance(value, int) or value <= 0
                    for value in values
                )
            ):
                raise ValueError(f"{field_name} must use unique chronological indices.")
        _validate_counts(
            self.assessment_status_counts,
            REPLAY_COACHING_ASSESSMENT_STATUSES,
            "assessment_status_counts",
        )
        _validate_counts(
            self.evidence_basis_counts,
            REPLAY_COACHING_EVIDENCE_BASES,
            "evidence_basis_counts",
        )
        _validate_counts(
            self.impact_tier_counts,
            REPLAY_COACHING_IMPACT_TIERS,
            "impact_tier_counts",
        )
        if len(self.decision_indices) != self.decision_count:
            raise ValueError("decision_indices must reconcile with decision_count.")
        if len(self.key_decision_indices) != self.key_decision_count:
            raise ValueError("key_decision_indices must reconcile with key_decision_count.")
        if not set(self.key_decision_indices).issubset(self.decision_indices):
            raise ValueError("Key Decision indices must be scope decision indices.")
        if not set(self.turning_point_indices).issubset(self.decision_indices):
            raise ValueError("Turning Point indices must be scope decision indices.")
        if self.turning_point_count < len(self.turning_point_indices):
            raise ValueError("Turning Point artifacts cannot have fewer unique decisions.")
        if self.high_impact_decision_count > self.decision_count:
            raise ValueError("High-impact decisions must be scope decisions.")
        if any(
            sum(count for _, count in counts) != self.decision_count
            for counts in (
                self.assessment_status_counts,
                self.evidence_basis_counts,
                self.impact_tier_counts,
            )
        ):
            raise ValueError("Scope count tuples must reconcile with decision_count.")
        statuses = dict(self.assessment_status_counts)
        if (
            self.assessable_decision_count
            != self.decision_count - statuses["not_assessable"]
            or self.forced_move_count != statuses["forced_move"]
            or self.best_or_equivalent_count != statuses["best_or_equivalent"]
            or self.strictly_below_best_count != statuses["strictly_below_best"]
            or self.not_assessable_count != statuses["not_assessable"]
        ):
            raise ValueError("Scope assessment status fields do not reconcile.")


def build_replay_coaching_coverage_summary(
    analysis: HistoricalSearchReviewCoachingAnalysis,
) -> ReplayCoachingCoverageSummary:
    assessments = analysis.assessments
    status_counts = _count_values(
        assessments, "assessment_status", REPLAY_COACHING_ASSESSMENT_STATUSES
    )
    evidence_counts = _count_values(
        assessments, "evidence_basis", REPLAY_COACHING_EVIDENCE_BASES
    )
    impact_counts = _count_values(
        assessments, "impact_tier", REPLAY_COACHING_IMPACT_TIERS
    )
    search_status_counts = tuple(
        (
            status,
            sum(
                assessment.decision_time_evidence.bounded_search_result.status == status
                for assessment in assessments
            ),
        )
        for status in BOUNDED_SEARCH_STATUSES
    )
    world_coverage_counts = tuple(
        (
            coverage,
            sum(
                assessment.decision_time_evidence.bounded_search_result.world_coverage
                == coverage
                for assessment in assessments
            ),
        )
        for coverage in WORLD_COVERAGE_VALUES
    )
    public = analysis.public_review_summary
    public_status = public.get("status_counts")
    public_coverage = public.get("coverage")
    public_decision_counts = public.get("decision_counts")
    status_mapping = dict(search_status_counts)
    coverage_mapping = dict(world_coverage_counts)
    search_recommendation_count = sum(
        assessment.decision_time_evidence.bounded_search_result.recommended_card
        is not None
        for assessment in assessments
    )
    if (
        not isinstance(public_status, dict) and not hasattr(public_status, "items")
    ) or dict(public_status) != status_mapping:
        raise ValueError("Report Search status counts do not match the public review.")
    expected_public_coverage = {
        "exact_coverage_decision_count": coverage_mapping["single_exact_world"]
        + coverage_mapping["all_compatible_worlds"],
        "sampled_coverage_decision_count": coverage_mapping[
            "sampled_compatible_worlds"
        ],
        "no_coverage_decision_count": coverage_mapping["none"],
    }
    if (
        not isinstance(public_coverage, dict) and not hasattr(public_coverage, "items")
    ) or dict(public_coverage) != expected_public_coverage:
        raise ValueError("Report world coverage does not match the public review.")
    if (
        not isinstance(public_decision_counts, dict)
        and not hasattr(public_decision_counts, "items")
    ) or (
        public_decision_counts.get("decision_count") != len(assessments)
        or public_decision_counts.get("search_recommendation_count")
        != search_recommendation_count
    ):
        raise ValueError("Report decision counts do not match the public review.")
    counts = dict(status_counts)
    guidance = analysis.guidance
    return ReplayCoachingCoverageSummary(
        decision_count=len(assessments),
        assessable_decision_count=analysis.prioritization.assessable_decision_count,
        forced_move_count=counts["forced_move"],
        best_or_equivalent_count=counts["best_or_equivalent"],
        strictly_below_best_count=counts["strictly_below_best"],
        not_assessable_count=counts["not_assessable"],
        high_impact_decision_count=analysis.prioritization.high_impact_decision_count,
        key_decision_count=len(analysis.prioritization.key_decisions),
        turning_point_count=len(analysis.prioritization.turning_points),
        pattern_count=guidance.pattern_count,
        actionable_pattern_count=guidance.actionable_pattern_count,
        decision_recommendation_count=guidance.decision_recommendation_count,
        pattern_recommendation_count=guidance.pattern_recommendation_count,
        search_recommendation_count=search_recommendation_count,
        immediate_available_count=sum(
            assessment.decision_time_evidence.immediate_evidence.is_available
            for assessment in assessments
        ),
        assessment_status_counts=status_counts,
        evidence_basis_counts=evidence_counts,
        impact_tier_counts=impact_counts,
        search_status_counts=search_status_counts,
        world_coverage_counts=world_coverage_counts,
    )


def _scope_value(scope: str, assessment: ReplayCoachingDecisionAssessment) -> str:
    evidence = assessment.decision_time_evidence
    return {
        "player": evidence.acting_player_id,
        "role": evidence.local_side,
        "phase": evidence.game_phase,
        "contract": evidence.game_type,
    }[scope]


def _build_scope_summary(
    analysis: HistoricalSearchReviewCoachingAnalysis,
    scope: str,
    scope_value: str,
) -> ReplayCoachingScopeSummary:
    assessments = tuple(
        assessment
        for assessment in analysis.assessments
        if _scope_value(scope, assessment) == scope_value
    )
    decision_indices = tuple(_decision_index(item) for item in assessments)
    key_indices = tuple(
        sorted(
            _decision_index(key.assessment)
            for key in analysis.prioritization.key_decisions
            if _scope_value(scope, key.assessment) == scope_value
        )
    )
    scoped_points = tuple(
        point
        for point in analysis.prioritization.turning_points
        if _scope_value(scope, point.assessment) == scope_value
    )
    turning_indices = tuple(
        sorted({_decision_index(point.assessment) for point in scoped_points})
    )
    high_indices = {
        _decision_index(key.assessment)
        for key in analysis.prioritization.key_decisions
        if key.is_high_impact
    }
    high_indices.update(
        _decision_index(point.assessment)
        for point in analysis.prioritization.turning_points
    )
    patterns = tuple(
        pattern
        for pattern in analysis.guidance.patterns
        if pattern.scope == scope and pattern.scope_value == scope_value
    )
    decision_recommendations = tuple(
        recommendation
        for recommendation in analysis.guidance.decision_recommendations
        if _scope_value(scope, recommendation.key_decision.assessment) == scope_value
    )
    pattern_recommendations = tuple(
        recommendation
        for recommendation in analysis.guidance.pattern_recommendations
        if recommendation.pattern.scope == scope
        and recommendation.pattern.scope_value == scope_value
    )
    status_counts = _count_values(
        assessments, "assessment_status", REPLAY_COACHING_ASSESSMENT_STATUSES
    )
    statuses = dict(status_counts)
    return ReplayCoachingScopeSummary(
        scope=scope,
        scope_value=scope_value,
        decision_count=len(assessments),
        assessable_decision_count=len(assessments) - statuses["not_assessable"],
        forced_move_count=statuses["forced_move"],
        best_or_equivalent_count=statuses["best_or_equivalent"],
        strictly_below_best_count=statuses["strictly_below_best"],
        not_assessable_count=statuses["not_assessable"],
        high_impact_decision_count=sum(index in high_indices for index in decision_indices),
        key_decision_count=len(key_indices),
        turning_point_count=len(scoped_points),
        decision_indices=decision_indices,
        key_decision_indices=key_indices,
        turning_point_indices=turning_indices,
        pattern_count=len(patterns),
        actionable_pattern_count=sum(pattern.is_actionable for pattern in patterns),
        decision_recommendation_count=len(decision_recommendations),
        pattern_recommendation_count=len(pattern_recommendations),
        assessment_status_counts=status_counts,
        evidence_basis_counts=_count_values(
            assessments, "evidence_basis", REPLAY_COACHING_EVIDENCE_BASES
        ),
        impact_tier_counts=_count_values(
            assessments, "impact_tier", REPLAY_COACHING_IMPACT_TIERS
        ),
    )


def build_replay_coaching_scope_summaries(
    record: HistoricalGameRecord,
    analysis: HistoricalSearchReviewCoachingAnalysis,
) -> tuple[
    tuple[ReplayCoachingScopeSummary, ...],
    tuple[ReplayCoachingScopeSummary, ...],
    tuple[ReplayCoachingScopeSummary, ...],
    tuple[ReplayCoachingScopeSummary, ...],
]:
    players_by_seat = {player.seat: player.player_id for player in record.players}
    values_by_scope = {
        "player": tuple(players_by_seat[seat] for seat in HISTORICAL_SEATS),
        "role": ("declarer", "defenders"),
        "phase": ("opening", "middle", "endgame"),
        "contract": (record.declaration.game_type,),
    }
    groups = tuple(
        tuple(
            _build_scope_summary(analysis, scope, scope_value)
            for scope_value in values_by_scope[scope]
        )
        for scope in REPLAY_COACHING_PATTERN_SCOPES
    )
    coverage = build_replay_coaching_coverage_summary(analysis)
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
        ):
            if sum(getattr(summary, field_name) for summary in summaries) != getattr(
                coverage, field_name
            ):
                raise ValueError(f"{scope} {field_name} totals do not reconcile.")
        if sum(summary.turning_point_count for summary in summaries) != (
            coverage.turning_point_count
        ):
            raise ValueError(f"{scope} Turning Point totals do not reconcile.")
        expected_pattern_count = sum(
            pattern.scope == scope for pattern in analysis.guidance.patterns
        )
        expected_pattern_recommendation_count = sum(
            recommendation.pattern.scope == scope
            for recommendation in analysis.guidance.pattern_recommendations
        )
        if sum(summary.pattern_count for summary in summaries) != expected_pattern_count:
            raise ValueError(f"{scope} pattern totals do not reconcile.")
        if sum(
            summary.pattern_recommendation_count for summary in summaries
        ) != expected_pattern_recommendation_count:
            raise ValueError(f"{scope} pattern recommendation totals do not reconcile.")
        if sum(
            summary.decision_recommendation_count for summary in summaries
        ) != coverage.decision_recommendation_count:
            raise ValueError(f"{scope} decision recommendation totals do not reconcile.")
    return groups


def build_serializable_replay_coaching_coverage_summary(
    summary: ReplayCoachingCoverageSummary,
) -> dict[str, Any]:
    return {
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
        "search_recommendation_count": summary.search_recommendation_count,
        "immediate_available_count": summary.immediate_available_count,
        "assessment_status_counts": _serialize_counts(
            summary.assessment_status_counts, "assessment_status"
        ),
        "evidence_basis_counts": _serialize_counts(
            summary.evidence_basis_counts, "evidence_basis"
        ),
        "impact_tier_counts": _serialize_counts(
            summary.impact_tier_counts, "impact_tier"
        ),
        "search_status_counts": _serialize_counts(
            summary.search_status_counts, "search_status"
        ),
        "world_coverage_counts": _serialize_counts(
            summary.world_coverage_counts, "world_coverage"
        ),
    }


def build_serializable_replay_coaching_scope_summary(
    summary: ReplayCoachingScopeSummary,
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
        "decision_indices": list(summary.decision_indices),
        "key_decision_indices": list(summary.key_decision_indices),
        "turning_point_indices": list(summary.turning_point_indices),
        "pattern_count": summary.pattern_count,
        "actionable_pattern_count": summary.actionable_pattern_count,
        "decision_recommendation_count": summary.decision_recommendation_count,
        "pattern_recommendation_count": summary.pattern_recommendation_count,
        "assessment_status_counts": _serialize_counts(
            summary.assessment_status_counts, "assessment_status"
        ),
        "evidence_basis_counts": _serialize_counts(
            summary.evidence_basis_counts, "evidence_basis"
        ),
        "impact_tier_counts": _serialize_counts(
            summary.impact_tier_counts, "impact_tier"
        ),
    }
