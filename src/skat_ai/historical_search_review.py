import hashlib
import math
from collections.abc import Mapping
from dataclasses import InitVar, dataclass
from types import MappingProxyType
from typing import Any

from skat_ai.analysis_report import build_card_analysis_report_from_values
from skat_ai.bounded_search_information import (
    build_historical_search_information_view,
    get_remaining_search_trick_count,
)
from skat_ai.bounded_search_result import (
    BOUNDED_SEARCH_STATUSES,
    WORLD_COVERAGE_VALUES,
    RequestedSearchBudget,
    build_serializable_bounded_search_result,
)
from skat_ai.compatible_world_minimax import solve_compatible_world_minimax
from skat_ai.game_value import get_null_game_value
from skat_ai.historical_decision_snapshot import (
    HistoricalDecisionSnapshot,
    HistoricalDecisionSnapshotSummary,
)
from skat_ai.historical_game import HistoricalGameRecord
from skat_ai.historical_snapshot_adapter import (
    HistoricalSnapshotPosition,
    build_position_from_historical_snapshot,
)
from skat_ai.input_validation import MAX_SAMPLE_COUNT, validate_positive_integer_maximum
from skat_ai.post_game_review import build_post_game_review_summary
from skat_ai.recommender import recommend_card_by_expected_value
from skat_ai.replay_coaching_assessment import (
    ReplayCoachingDecisionAssessment,
    build_replay_coaching_decision_assessment,
)
from skat_ai.replay_coaching_evidence import (
    DecisionTimeReplayCoachingEvidence,
    build_decision_time_replay_coaching_evidence,
    build_immediate_replay_coaching_evidence,
)
from skat_ai.replay_coaching_guidance import (
    ReplayCoachingGuidanceResult,
    build_replay_coaching_guidance,
)
from skat_ai.replay_coaching_prioritization import (
    ReplayCoachingPrioritizationResult,
    build_replay_coaching_prioritization_result,
    validate_replay_coaching_assessment_sequence,
)
from skat_ai.retrospective_search_comparison import (
    SearchActualCardComparison,
    build_search_actual_card_comparison,
    build_search_vs_immediate_comparison,
    build_serializable_search_actual_card_comparison,
    build_serializable_search_vs_immediate_comparison,
)
from skat_ai.rules import GAME_TYPES
from skat_ai.search_budget_profiles import (
    HISTORICAL_REVIEW_SEARCH_BUDGET_PROFILE,
    get_search_budget_profile,
)
from skat_ai.simulation import DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT

HISTORICAL_SEARCH_REVIEW_SCHEMA_VERSION = 1
HISTORICAL_SEARCH_REVIEW_ANALYSIS_METHOD = (
    "bounded_search_with_immediate_baseline"
)
HISTORICAL_SEARCH_REVIEW_INFORMATION_POLICY = "decision_time"
HISTORICAL_SEARCH_DECISION_SEED_DOMAIN = "historical_bounded_search_decision_v1"

ROOT_SEATS = ("lead", "second", "third")
LOCAL_SIDES = ("declarer", "defenders")


def _validate_integer_seed(value: int, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer and must not be a boolean.")


def derive_historical_search_decision_seed(
    base_search_seed: int,
    stable_game_identity: str,
    decision_index: int,
) -> int:
    """Derives a process-stable Search seed from stable decision identity only."""
    _validate_integer_seed(base_search_seed, "base_search_seed")
    if (
        not isinstance(stable_game_identity, str)
        or not stable_game_identity
        or stable_game_identity != stable_game_identity.strip()
    ):
        raise ValueError("stable_game_identity must be a non-empty, non-padded string.")
    if (
        isinstance(decision_index, bool)
        or not isinstance(decision_index, int)
        or decision_index <= 0
    ):
        raise ValueError("decision_index must be a positive integer.")
    material = (
        f"skat-ai\0{base_search_seed}\0{HISTORICAL_SEARCH_DECISION_SEED_DOMAIN}"
        f"\0{stable_game_identity}\0{decision_index}"
    ).encode()
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")


@dataclass(frozen=True)
class HistoricalSearchReviewSettings:
    """Versioned Search and independent Immediate settings for one review."""

    base_search_seed: int
    search_budget_profile: str = HISTORICAL_REVIEW_SEARCH_BUDGET_PROFILE
    immediate_sample_count: int = DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT
    immediate_base_random_seed: int | None = None

    def __post_init__(self) -> None:
        _validate_integer_seed(self.base_search_seed, "base_search_seed")
        if not isinstance(self.search_budget_profile, str) or not self.search_budget_profile:
            raise ValueError("search_budget_profile must be a non-empty string.")
        get_search_budget_profile(self.search_budget_profile)
        validate_positive_integer_maximum(
            self.immediate_sample_count,
            "immediate_sample_count",
            MAX_SAMPLE_COUNT,
        )
        if self.immediate_base_random_seed is not None:
            _validate_integer_seed(
                self.immediate_base_random_seed,
                "immediate_base_random_seed",
            )


@dataclass(frozen=True)
class HistoricalSearchDecisionPreActualAnalysis:
    """One Search and Immediate run completed before observed-card attachment."""

    position: HistoricalSnapshotPosition
    remaining_tricks: int
    effective_immediate_seed: int | None
    immediate_card: str
    immediate_reason: str
    immediate_report: tuple[Mapping[str, Any], ...]
    decision_time_evidence: DecisionTimeReplayCoachingEvidence


@dataclass(frozen=True)
class HistoricalSearchDecisionRetrospectiveAttachment:
    """The existing Search comparison plus its internal coaching assessment."""

    search_actual_card_comparison: SearchActualCardComparison
    coaching_assessment: ReplayCoachingDecisionAssessment


def _freeze_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType(
            {key: _freeze_json_value(item) for key, item in value.items()}
        )
    if isinstance(value, list):
        return tuple(_freeze_json_value(item) for item in value)
    return value


def _thaw_json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_json_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json_value(item) for item in value]
    return value


@dataclass(frozen=True)
class HistoricalSearchDecisionInternalResult:
    """One immutable public decision row and its retained assessment."""

    public_review: Mapping[str, Any]
    assessment: ReplayCoachingDecisionAssessment

    def __post_init__(self) -> None:
        if not isinstance(self.public_review, Mapping):
            raise ValueError("public_review must be a mapping.")
        if not isinstance(self.assessment, ReplayCoachingDecisionAssessment):
            raise ValueError("assessment must be ReplayCoachingDecisionAssessment.")
        object.__setattr__(
            self,
            "public_review",
            _freeze_json_value(dict(self.public_review)),
        )


@dataclass(frozen=True)
class HistoricalSearchReviewInternalResult:
    """The unchanged public summary plus chronological coaching assessments."""

    public_review_summary: Mapping[str, Any]
    assessments: tuple[ReplayCoachingDecisionAssessment, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.public_review_summary, Mapping):
            raise ValueError("public_review_summary must be a mapping.")
        if not isinstance(self.assessments, tuple) or any(
            not isinstance(assessment, ReplayCoachingDecisionAssessment)
            for assessment in self.assessments
        ):
            raise ValueError("assessments must contain coaching assessments.")
        decisions = self.public_review_summary.get("decisions")
        if not isinstance(decisions, (list, tuple)) or len(decisions) != len(
            self.assessments
        ):
            raise ValueError("Public decisions and coaching assessments must reconcile.")
        object.__setattr__(
            self,
            "public_review_summary",
            _freeze_json_value(dict(self.public_review_summary)),
        )
        object.__setattr__(self, "assessments", tuple(self.assessments))


@dataclass(frozen=True)
class HistoricalSearchReviewCoachingAnalysis:
    """One retained Search Review, prioritization, and internal guidance result."""

    public_review_summary: Mapping[str, Any]
    assessments: tuple[ReplayCoachingDecisionAssessment, ...]
    prioritization: ReplayCoachingPrioritizationResult
    guidance: ReplayCoachingGuidanceResult
    historical_record: InitVar[HistoricalGameRecord]

    def __post_init__(self, historical_record: HistoricalGameRecord) -> None:
        if not isinstance(self.public_review_summary, Mapping):
            raise ValueError("public_review_summary must be a mapping.")
        validate_replay_coaching_assessment_sequence(
            historical_record, self.assessments
        )
        if not isinstance(self.prioritization, ReplayCoachingPrioritizationResult):
            raise ValueError("prioritization has the wrong type.")
        if not isinstance(self.guidance, ReplayCoachingGuidanceResult):
            raise ValueError("guidance has the wrong type.")
        expected_prioritization = build_replay_coaching_prioritization_result(
            historical_record, self.assessments
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
            raise ValueError("Historical Search Review coaching artifacts do not reconcile.")
        decisions = self.public_review_summary.get("decisions")
        if (
            self.public_review_summary.get("source_game_id")
            != historical_record.game_id
            or not isinstance(decisions, (list, tuple))
            or len(decisions) != len(self.assessments)
        ):
            raise ValueError("Public review summary does not match coaching artifacts.")
        for decision, assessment in zip(decisions, self.assessments, strict=True):
            evidence = assessment.decision_time_evidence
            if (
                not isinstance(decision, Mapping)
                or decision.get("decision_index") != evidence.decision_index
                or decision.get("actual_card") != assessment.actual_card
                or decision.get("acting_player_id") != evidence.acting_player_id
            ):
                raise ValueError(
                    "Public review decisions do not match coaching assessments."
                )
        object.__setattr__(
            self,
            "public_review_summary",
            _freeze_json_value(dict(self.public_review_summary)),
        )
        object.__setattr__(self, "assessments", tuple(self.assessments))


def _serialize_requested_budget(budget: RequestedSearchBudget) -> dict[str, Any]:
    return {
        "max_remaining_tricks": budget.max_remaining_tricks,
        "max_depth_plies": budget.max_depth_plies,
        "max_nodes": budget.max_nodes,
        "max_selected_worlds": budget.max_selected_worlds,
        "max_sampled_worlds": budget.max_sampled_worlds,
        "minimum_comparable_worlds": budget.minimum_comparable_worlds,
        "wall_clock_timeout_ms": budget.wall_clock_timeout_ms,
    }


def build_serializable_historical_search_review_settings(
    settings: HistoricalSearchReviewSettings,
) -> dict[str, Any]:
    budget = get_search_budget_profile(settings.search_budget_profile)
    return {
        "base_search_seed": settings.base_search_seed,
        "search_budget_profile": settings.search_budget_profile,
        "requested_budget": _serialize_requested_budget(budget),
        "immediate_sample_count": settings.immediate_sample_count,
        "immediate_base_random_seed": settings.immediate_base_random_seed,
    }


def _decision_identity(snapshot: HistoricalDecisionSnapshot) -> dict[str, Any]:
    result = {
        "source_game_id": snapshot.source_game_id,
        "decision_index": snapshot.decision_index,
        "trick_number": snapshot.trick_number,
        "play_index": snapshot.play_index,
        "acting_player_id": snapshot.acting_player_id,
        "acting_seat": snapshot.acting_seat,
        "acting_side": snapshot.acting_side,
    }
    if snapshot.source_played_at is not None:
        result["source_played_at"] = snapshot.source_played_at
    return result


def build_historical_search_decision_pre_actual_analysis(
    snapshot: HistoricalDecisionSnapshot,
    historical_record: HistoricalGameRecord,
    settings: HistoricalSearchReviewSettings,
    *,
    stable_game_identity: str | None = None,
) -> HistoricalSearchDecisionPreActualAnalysis:
    """Runs Search and Immediate once without reading the observed card."""
    if not isinstance(settings, HistoricalSearchReviewSettings):
        raise ValueError("settings must be HistoricalSearchReviewSettings.")
    if snapshot.play_index not in (1, 2, 3):
        raise ValueError("Historical play_index must identify lead, second, or third.")
    stable_identity = stable_game_identity or historical_record.game_id
    position = build_position_from_historical_snapshot(snapshot, historical_record)
    information_view = build_historical_search_information_view(position)
    budget = get_search_budget_profile(settings.search_budget_profile)
    search_seed = derive_historical_search_decision_seed(
        settings.base_search_seed,
        stable_identity,
        snapshot.decision_index,
    )
    search_result = solve_compatible_world_minimax(
        information_view=information_view,
        requested_budget=budget,
        random_seed=search_seed,
    )

    effective_immediate_seed = (
        None
        if settings.immediate_base_random_seed is None
        else settings.immediate_base_random_seed + snapshot.decision_index - 1
    )
    immediate_card, immediate_reason, immediate_values = (
        recommend_card_by_expected_value(
            state=position.state,
            left_hand_size=position.left_hand_size,
            right_hand_size=position.right_hand_size,
            sample_count=settings.immediate_sample_count,
            random_seed=effective_immediate_seed,
            public_hand_constraints=position.public_hand_constraints,
        )
    )
    immediate_report = build_card_analysis_report_from_values(
        state=position.state,
        values=immediate_values,
    )
    recommended_rows = [
        row for row in immediate_report if row["is_recommended"] is True
    ]
    if len(recommended_rows) != 1 or recommended_rows[0]["card"] != immediate_card:
        raise ValueError("Immediate recommendation and analysis report are inconsistent.")

    search_vs_immediate_comparison = build_search_vs_immediate_comparison(
        search_result,
        immediate_card,
        immediate_report,
        position.state.game_type,
        position.state.player_role,
    )
    immediate_evidence = build_immediate_replay_coaching_evidence(
        legal_cards=position.legal_cards,
        analysis_report=immediate_report,
        recommended_card=immediate_card,
        unavailable_reason=None,
        game_type=position.state.game_type,
        player_role=position.state.player_role,
        objective_values=immediate_values,
    )
    decision_time_evidence = build_decision_time_replay_coaching_evidence(
        source_game_id=snapshot.source_game_id,
        decision_index=snapshot.decision_index,
        trick_number=snapshot.trick_number,
        play_index=snapshot.play_index,
        acting_player_id=snapshot.acting_player_id,
        acting_seat=snapshot.acting_seat,
        local_side=information_view.local_side,
        game_type=information_view.game_type,
        legal_cards=position.legal_cards,
        immediate_evidence=immediate_evidence,
        bounded_search_result=search_result,
        search_vs_immediate_comparison=search_vs_immediate_comparison,
    )
    return HistoricalSearchDecisionPreActualAnalysis(
        position=position,
        remaining_tricks=get_remaining_search_trick_count(information_view),
        effective_immediate_seed=effective_immediate_seed,
        immediate_card=immediate_card,
        immediate_reason=immediate_reason,
        immediate_report=tuple(MappingProxyType(dict(row)) for row in immediate_report),
        decision_time_evidence=decision_time_evidence,
    )


def attach_historical_search_decision_retrospective_assessment(
    snapshot: HistoricalDecisionSnapshot,
    analysis: HistoricalSearchDecisionPreActualAnalysis,
) -> HistoricalSearchDecisionRetrospectiveAttachment:
    """Attaches the observed card to completed decision-time analyses."""
    if snapshot.source_game_id != analysis.decision_time_evidence.source_game_id:
        raise ValueError("Historical retrospective attachment game IDs do not match.")
    if snapshot.decision_index != analysis.decision_time_evidence.decision_index:
        raise ValueError("Historical retrospective attachment decisions do not match.")

    actual_card = snapshot.actual_card_played
    actual_comparison = build_search_actual_card_comparison(
        analysis.decision_time_evidence.bounded_search_result,
        actual_card,
    )
    immediate_report = [dict(row) for row in analysis.immediate_report]
    game_value = (
        get_null_game_value(analysis.position.game_declaration)
        if analysis.position.state.game_type == "null"
        else None
    )
    immediate_review = build_post_game_review_summary(
        actual_card_played=actual_card,
        analysis_report=immediate_report,
        game_type=analysis.position.state.game_type,
        player_role=analysis.position.state.player_role,
        game_value=game_value,
    )
    coaching_assessment = build_replay_coaching_decision_assessment(
        decision_time_evidence=analysis.decision_time_evidence,
        actual_card=actual_card,
        search_actual_card_comparison=actual_comparison,
        immediate_baseline_quality=immediate_review["decision_quality"],
    )
    return HistoricalSearchDecisionRetrospectiveAttachment(
        search_actual_card_comparison=actual_comparison,
        coaching_assessment=coaching_assessment,
    )


def build_historical_search_decision_internal_result(
    snapshot: HistoricalDecisionSnapshot,
    historical_record: HistoricalGameRecord,
    settings: HistoricalSearchReviewSettings,
    *,
    stable_game_identity: str | None = None,
) -> HistoricalSearchDecisionInternalResult:
    """Builds one public review row and retains its existing assessment."""
    analysis = build_historical_search_decision_pre_actual_analysis(
        snapshot,
        historical_record,
        settings,
        stable_game_identity=stable_game_identity,
    )
    attachment = attach_historical_search_decision_retrospective_assessment(
        snapshot,
        analysis,
    )
    evidence = analysis.decision_time_evidence
    public_review = {
        **_decision_identity(snapshot),
        "game_type": evidence.game_type,
        "local_side": evidence.local_side,
        "root_seat": ROOT_SEATS[snapshot.play_index - 1],
        "remaining_tricks": analysis.remaining_tricks,
        "actual_card": snapshot.actual_card_played,
        "immediate_baseline": {
            "effective_random_seed": analysis.effective_immediate_seed,
            "legal_cards": list(analysis.position.legal_cards),
            "recommendation": {
                "card": analysis.immediate_card,
                "reason": analysis.immediate_reason,
            },
            "analysis_report": [dict(row) for row in analysis.immediate_report],
        },
        "bounded_search_result": build_serializable_bounded_search_result(
            evidence.bounded_search_result
        ),
        "search_actual_card_comparison": (
            build_serializable_search_actual_card_comparison(
                attachment.search_actual_card_comparison
            )
        ),
        "search_vs_immediate_comparison": (
            build_serializable_search_vs_immediate_comparison(
                evidence.search_vs_immediate_comparison
            )
        ),
    }
    return HistoricalSearchDecisionInternalResult(
        public_review=_freeze_json_value(public_review),
        assessment=attachment.coaching_assessment,
    )


def build_historical_search_decision_review(
    snapshot: HistoricalDecisionSnapshot,
    historical_record: HistoricalGameRecord,
    settings: HistoricalSearchReviewSettings,
    *,
    stable_game_identity: str | None = None,
) -> dict[str, Any]:
    """Builds the unchanged public review row."""
    result = build_historical_search_decision_internal_result(
        snapshot,
        historical_record,
        settings,
        stable_game_identity=stable_game_identity,
    )
    return _thaw_json_value(result.public_review)


def _nearest_rank(values: list[int], percentile: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[math.ceil(percentile * len(ordered)) - 1]


def _performance_metric(values: list[int]) -> dict[str, int | float | None]:
    return {
        "total": sum(values),
        "mean": sum(values) / len(values) if values else None,
        "p50": _nearest_rank(values, 0.50),
        "p95": _nearest_rank(values, 0.95),
        "max": max(values) if values else None,
    }


def _count_search_comparisons(
    decisions: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    comparisons = [
        decision["search_vs_immediate_comparison"] for decision in decisions
    ]
    comparable = [comparison for comparison in comparisons if comparison["is_available"]]
    same_count = sum(comparison["same_recommended_card"] is True for comparison in comparable)
    agreement = {
        "comparable_decision_count": len(comparable),
        "same_recommended_card_count": same_count,
        "different_recommended_card_count": len(comparable) - same_count,
        "same_recommended_card_rate": (
            same_count / len(comparable) if comparable else None
        ),
    }
    better_count = sum(
        comparison["search_aggregate_relation"] == "search_better"
        for comparison in comparable
    )
    equivalent_count = sum(
        comparison["search_aggregate_relation"] == "aggregate_equivalent"
        for comparison in comparable
    )
    not_worse_count = better_count + equivalent_count
    quality_gate = {
        "comparable_decision_count": len(comparable),
        "search_not_worse_count": not_worse_count,
        "search_strictly_better_count": better_count,
        "search_equivalent_count": equivalent_count,
        "quality_violation_count": len(comparable) - not_worse_count,
        "quality_gate_passed": len(comparable) == not_worse_count,
    }
    unavailable_reasons = {
        reason: sum(
            not comparison["is_available"]
            and comparison["unavailable_reason"] == reason
            for comparison in comparisons
        )
        for reason in dict.fromkeys(
            comparison["unavailable_reason"]
            for comparison in comparisons
            if comparison["unavailable_reason"] is not None
        )
    }
    quality_counts = {
        "search_better": better_count,
        "aggregate_equivalent": equivalent_count,
        "not_available": len(comparisons) - len(comparable),
        "unavailable_reason_counts": unavailable_reasons,
    }
    return agreement, quality_gate, quality_counts


def build_historical_search_review_metrics(
    decisions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Builds reconciled aggregate metrics shared by review and evaluation."""
    status_counts = {
        status: sum(
            decision["bounded_search_result"]["status"] == status
            for decision in decisions
        )
        for status in BOUNDED_SEARCH_STATUSES
    }
    coverage_counts = {
        "exact_coverage_decision_count": sum(
            decision["bounded_search_result"]["world_coverage"]
            in {"single_exact_world", "all_compatible_worlds"}
            for decision in decisions
        ),
        "sampled_coverage_decision_count": sum(
            decision["bounded_search_result"]["world_coverage"]
            == "sampled_compatible_worlds"
            for decision in decisions
        ),
        "no_coverage_decision_count": sum(
            decision["bounded_search_result"]["world_coverage"] == "none"
            for decision in decisions
        ),
    }
    agreement, quality_gate, aggregate_quality_counts = (
        _count_search_comparisons(decisions)
    )
    actual_comparisons = [
        decision["search_actual_card_comparison"] for decision in decisions
    ]
    comparable_actual = [
        comparison for comparison in actual_comparisons if comparison["is_available"]
    ]
    top_1_count = sum(
        comparison["strictly_better_card_count"] == 0
        for comparison in comparable_actual
    )
    top_3_count = sum(
        comparison["strictly_better_card_count"] <= 2
        for comparison in comparable_actual
    )
    actual_ranks = {
        "comparable_decision_count": len(comparable_actual),
        "actual_top_1_count": top_1_count,
        "actual_top_1_rate": (
            top_1_count / len(comparable_actual) if comparable_actual else None
        ),
        "actual_top_3_count": top_3_count,
        "actual_top_3_rate": (
            top_3_count / len(comparable_actual) if comparable_actual else None
        ),
    }
    consumed = [
        decision["bounded_search_result"]["consumed_budget"]
        for decision in decisions
    ]
    performance = {
        field_name: _performance_metric([row[field_name] for row in consumed])
        for field_name in (
            "nodes_expanded",
            "selected_world_count",
            "completed_world_count",
            "sampled_world_count",
            "depth_reached",
            "wall_clock_elapsed_ms",
        )
    }
    performance["fallback_count"] = sum(
        decision["bounded_search_result"]["fallback_used"]
        for decision in decisions
    )
    available_count = len(decisions) - status_counts["unavailable"]
    recommendation_count = sum(
        decision["bounded_search_result"]["recommended_card"] is not None
        for decision in decisions
    )
    decision_counts = {
        "decision_count": len(decisions),
        "search_attempted_count": len(decisions),
        "search_available_decision_count": available_count,
        "search_unavailable_decision_count": status_counts["unavailable"],
        "search_recommendation_count": recommendation_count,
        "no_search_recommendation_count": len(decisions) - recommendation_count,
    }
    metrics = {
        "decision_counts": decision_counts,
        "status_counts": status_counts,
        "coverage": coverage_counts,
        "search_vs_immediate_agreement": agreement,
        "quality_gate": quality_gate,
        "actual_card_agreement": actual_ranks,
        "search_aggregate_quality": aggregate_quality_counts,
        "performance": performance,
    }
    if sum(status_counts.values()) != len(decisions):
        raise ValueError("Search status counts do not reconcile.")
    if sum(coverage_counts.values()) != len(decisions):
        raise ValueError("Search coverage counts do not reconcile.")
    if available_count + status_counts["unavailable"] != len(decisions):
        raise ValueError("Search availability counts do not reconcile.")
    if (
        recommendation_count + decision_counts["no_search_recommendation_count"]
        != len(decisions)
    ):
        raise ValueError("Search recommendation counts do not reconcile.")
    if (
        quality_gate["search_not_worse_count"]
        + quality_gate["quality_violation_count"]
        != quality_gate["comparable_decision_count"]
    ):
        raise ValueError("Search quality-gate counts do not reconcile.")
    if (
        aggregate_quality_counts["search_better"]
        + aggregate_quality_counts["aggregate_equivalent"]
        + aggregate_quality_counts["not_available"]
        != len(decisions)
    ):
        raise ValueError("Aggregate Search quality counts do not reconcile.")
    return metrics


def _breakdown_rows(
    decisions: list[dict[str, Any]],
    field_name: str,
    ordered_values: tuple[Any, ...] | None = None,
) -> list[dict[str, Any]]:
    values = (
        [value for value in ordered_values if any(row[field_name] == value for row in decisions)]
        if ordered_values is not None
        else sorted({row[field_name] for row in decisions})
    )
    return [
        {
            field_name: value,
            "metrics": build_historical_search_review_metrics(
                [row for row in decisions if row[field_name] == value]
            ),
        }
        for value in values
    ]


def build_historical_search_review_breakdowns(
    decisions: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    return {
        "by_game_type": _breakdown_rows(decisions, "game_type", tuple(GAME_TYPES)),
        "by_local_side": _breakdown_rows(decisions, "local_side", LOCAL_SIDES),
        "by_root_seat": _breakdown_rows(decisions, "root_seat", ROOT_SEATS),
        "by_remaining_tricks": _breakdown_rows(decisions, "remaining_tricks"),
        "by_status": _breakdown_rows(decisions, "search_status", BOUNDED_SEARCH_STATUSES),
        "by_coverage": _breakdown_rows(
            decisions,
            "search_coverage",
            WORLD_COVERAGE_VALUES,
        ),
    }


def _with_breakdown_fields(decision: dict[str, Any]) -> dict[str, Any]:
    return {
        **decision,
        "search_status": decision["bounded_search_result"]["status"],
        "search_coverage": decision["bounded_search_result"]["world_coverage"],
    }


def build_historical_search_review_internal_result(
    snapshot_summary: HistoricalDecisionSnapshotSummary,
    historical_record: HistoricalGameRecord,
    base_search_seed: int,
    search_budget_profile: str = HISTORICAL_REVIEW_SEARCH_BUDGET_PROFILE,
    immediate_sample_count: int = DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT,
    immediate_base_random_seed: int | None = None,
) -> HistoricalSearchReviewInternalResult:
    """Evaluates one review while retaining chronological assessments."""
    cardinality = snapshot_summary.cardinality
    if historical_record.game_end_reason != cardinality.game_end_reason:
        raise ValueError("Historical Search review end reasons do not match.")
    if (
        snapshot_summary.snapshot_count
        != cardinality.expected_review_decision_count
        or len(snapshot_summary.snapshots)
        != cardinality.expected_review_decision_count
    ):
        raise ValueError(
            "Historical Search review snapshot count does not match the validated prefix."
        )
    settings = HistoricalSearchReviewSettings(
        base_search_seed=base_search_seed,
        search_budget_profile=search_budget_profile,
        immediate_sample_count=immediate_sample_count,
        immediate_base_random_seed=immediate_base_random_seed,
    )
    decision_results = [
        build_historical_search_decision_internal_result(
            snapshot,
            historical_record,
            settings,
            stable_game_identity=historical_record.game_id,
        )
        for snapshot in snapshot_summary.snapshots
    ]
    decisions = [
        _thaw_json_value(result.public_review) for result in decision_results
    ]
    aggregate_decisions = [_with_breakdown_fields(decision) for decision in decisions]
    metrics = build_historical_search_review_metrics(aggregate_decisions)
    breakdowns = build_historical_search_review_breakdowns(aggregate_decisions)
    for breakdown_name, rows in breakdowns.items():
        if sum(
            row["metrics"]["decision_counts"]["decision_count"] for row in rows
        ) != len(decisions):
            raise ValueError(f"{breakdown_name} decision counts do not reconcile.")
    public_summary = {
        "schema_version": HISTORICAL_SEARCH_REVIEW_SCHEMA_VERSION,
        "analysis_method": HISTORICAL_SEARCH_REVIEW_ANALYSIS_METHOD,
        "information_policy": HISTORICAL_SEARCH_REVIEW_INFORMATION_POLICY,
        "source_game_id": historical_record.game_id,
        "game_end_reason": historical_record.game_end_reason,
        "settings": build_serializable_historical_search_review_settings(settings),
        **metrics,
        "breakdowns": breakdowns,
        "decisions": decisions,
    }
    return HistoricalSearchReviewInternalResult(
        public_review_summary=_freeze_json_value(public_summary),
        assessments=tuple(result.assessment for result in decision_results),
    )


def build_historical_search_review_summary(
    snapshot_summary: HistoricalDecisionSnapshotSummary,
    historical_record: HistoricalGameRecord,
    base_search_seed: int,
    search_budget_profile: str = HISTORICAL_REVIEW_SEARCH_BUDGET_PROFILE,
    immediate_sample_count: int = DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT,
    immediate_base_random_seed: int | None = None,
) -> dict[str, Any]:
    """Evaluates every decision and returns the unchanged public summary."""
    result = build_historical_search_review_internal_result(
        snapshot_summary,
        historical_record,
        base_search_seed,
        search_budget_profile,
        immediate_sample_count,
        immediate_base_random_seed,
    )
    return _thaw_json_value(result.public_review_summary)


def build_historical_search_review_coaching_analysis(
    snapshot_summary: HistoricalDecisionSnapshotSummary,
    historical_record: HistoricalGameRecord,
    base_search_seed: int,
    search_budget_profile: str = HISTORICAL_REVIEW_SEARCH_BUDGET_PROFILE,
    immediate_sample_count: int = DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT,
    immediate_base_random_seed: int | None = None,
) -> HistoricalSearchReviewCoachingAnalysis:
    """Retains internal coaching artifacts from exactly one Search Review pass."""
    review = build_historical_search_review_internal_result(
        snapshot_summary,
        historical_record,
        base_search_seed,
        search_budget_profile,
        immediate_sample_count,
        immediate_base_random_seed,
    )
    prioritization = build_replay_coaching_prioritization_result(
        historical_record, review.assessments
    )
    guidance = build_replay_coaching_guidance(
        historical_record,
        review.assessments,
        prioritization,
    )
    return HistoricalSearchReviewCoachingAnalysis(
        public_review_summary=review.public_review_summary,
        assessments=review.assessments,
        prioritization=prioritization,
        guidance=guidance,
        historical_record=historical_record,
    )
