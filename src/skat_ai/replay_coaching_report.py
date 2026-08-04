from collections.abc import Mapping
from dataclasses import InitVar, dataclass
from types import MappingProxyType
from typing import Any

from skat_ai.bounded_search_result import build_serializable_bounded_search_result
from skat_ai.historical_decision_snapshot import HistoricalDecisionSnapshotSummary
from skat_ai.historical_game import HistoricalGameRecord
from skat_ai.historical_search_review import (
    HISTORICAL_SEARCH_REVIEW_ANALYSIS_METHOD,
    HISTORICAL_SEARCH_REVIEW_INFORMATION_POLICY,
    HISTORICAL_SEARCH_REVIEW_SCHEMA_VERSION,
    HistoricalSearchReviewCoachingAnalysis,
    build_historical_search_review_coaching_analysis,
)
from skat_ai.replay_coaching_assessment import (
    ReplayCoachingDecisionAssessment,
    build_serializable_replay_coaching_decision_assessment,
)
from skat_ai.replay_coaching_evidence import REPLAY_COACHING_INFORMATION_POLICY
from skat_ai.replay_coaching_guidance import (
    ReplayCoachingGuidanceResult,
    build_serializable_replay_coaching_guidance_result,
)
from skat_ai.replay_coaching_prioritization import (
    ReplayCoachingPrioritizationResult,
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
from skat_ai.replay_coaching_scope_summary import (
    ReplayCoachingCoverageSummary,
    ReplayCoachingScopeSummary,
    build_replay_coaching_coverage_summary,
    build_replay_coaching_scope_summaries,
    build_serializable_replay_coaching_coverage_summary,
    build_serializable_replay_coaching_scope_summary,
)
from skat_ai.retrospective_search_comparison import (
    build_serializable_search_actual_card_comparison,
    build_serializable_search_vs_immediate_comparison,
)
from skat_ai.search_budget_profiles import HISTORICAL_REVIEW_SEARCH_BUDGET_PROFILE
from skat_ai.simulation import DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT

REPLAY_COACHING_REPORT_VERSION = 1
REPLAY_COACHING_REPORT_METHOD = "historical_replay_coaching_v1"
REPLAY_COACHING_OUTCOME_CONTEXT_POLICY = "final_context_after_coaching"
REPLAY_COACHING_REPORT_LIMITATIONS = (
    "outcome_context_not_decision_evidence",
    "single_recorded_game_only",
    "bounded_late_game_search",
    "determinization_strategy_fusion",
    "sampled_compatible_worlds",
    "completed_common_prefix",
    "immediate_expected_value_only",
    "search_unavailable",
    "observed_card_not_ground_truth",
    "incomplete_assessment_coverage",
    "no_tactical_motif_inference",
    "no_causal_outcome_claim",
    "no_player_skill_rating",
)


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


def _validate_source_review(
    record: HistoricalGameRecord,
    analysis: HistoricalSearchReviewCoachingAnalysis,
) -> None:
    if not isinstance(analysis, HistoricalSearchReviewCoachingAnalysis):
        raise ValueError("analysis must be HistoricalSearchReviewCoachingAnalysis.")
    validate_replay_coaching_assessment_sequence(record, analysis.assessments)
    public = analysis.public_review_summary
    if (
        public.get("schema_version") != HISTORICAL_SEARCH_REVIEW_SCHEMA_VERSION
        or public.get("analysis_method") != HISTORICAL_SEARCH_REVIEW_ANALYSIS_METHOD
        or public.get("information_policy")
        != HISTORICAL_SEARCH_REVIEW_INFORMATION_POLICY
        or public.get("source_game_id") != record.game_id
        or public.get("game_end_reason") != record.game_end_reason
    ):
        raise ValueError("Historical Search Review source metadata does not match.")
    settings = public.get("settings")
    if not isinstance(settings, Mapping) or tuple(settings) != (
        "base_search_seed",
        "search_budget_profile",
        "requested_budget",
        "immediate_sample_count",
        "immediate_base_random_seed",
    ):
        raise ValueError("Historical Search Review settings are not the public base settings.")
    decisions = public.get("decisions")
    if not isinstance(decisions, (list, tuple)) or len(decisions) != len(
        analysis.assessments
    ):
        raise ValueError("Historical Search Review decisions do not reconcile.")
    for decision, assessment in zip(decisions, analysis.assessments, strict=True):
        evidence = assessment.decision_time_evidence
        expected_identity = {
            "source_game_id": evidence.source_game_id,
            "decision_index": evidence.decision_index,
            "trick_number": evidence.trick_number,
            "play_index": evidence.play_index,
            "acting_player_id": evidence.acting_player_id,
            "acting_seat": evidence.acting_seat,
            "game_type": evidence.game_type,
            "local_side": evidence.local_side,
            "root_seat": evidence.root_seat,
            "actual_card": assessment.actual_card,
        }
        if not isinstance(decision, Mapping) or any(
            decision.get(field) != value for field, value in expected_identity.items()
        ):
            raise ValueError("Historical Search Review decision identity does not match.")
        if (
            _thaw_json_value(decision.get("bounded_search_result"))
            != build_serializable_bounded_search_result(
                evidence.bounded_search_result
            )
            or _thaw_json_value(decision.get("search_actual_card_comparison"))
            != build_serializable_search_actual_card_comparison(
                assessment.search_actual_card_comparison
            )
            or _thaw_json_value(decision.get("search_vs_immediate_comparison"))
            != build_serializable_search_vs_immediate_comparison(
                evidence.search_vs_immediate_comparison
            )
        ):
            raise ValueError(
                "Historical Search Review decision evidence does not match."
            )
        immediate = decision.get("immediate_baseline")
        immediate_evidence = evidence.immediate_evidence
        immediate_rows = (
            immediate.get("analysis_report")
            if isinstance(immediate, Mapping)
            else None
        )
        if (
            not isinstance(immediate, Mapping)
            or tuple(immediate.get("legal_cards", ())) != evidence.legal_cards
            or not isinstance(immediate.get("recommendation"), Mapping)
            or immediate["recommendation"].get("card")
            != immediate_evidence.recommended_card
            or not isinstance(immediate_rows, (list, tuple))
            or len(immediate_rows) != immediate_evidence.candidate_count
            or any(
                not isinstance(row, Mapping)
                or row.get("card") != candidate.card
                or row.get("is_recommended") != candidate.is_recommended
                or row.get("expected_point_swing")
                != candidate.expected_point_swing
                for row, candidate in zip(
                    immediate_rows,
                    immediate_evidence.candidates,
                    strict=True,
                )
            )
        ):
            raise ValueError(
                "Historical Search Review Immediate evidence does not match."
            )


def _build_report_limitations(
    analysis: HistoricalSearchReviewCoachingAnalysis,
) -> tuple[str, ...]:
    selected = {
        "outcome_context_not_decision_evidence",
        "single_recorded_game_only",
        "observed_card_not_ground_truth",
        "no_tactical_motif_inference",
        "no_causal_outcome_claim",
        "no_player_skill_rating",
    }
    selected.update(
        limitation
        for assessment in analysis.assessments
        for limitation in assessment.limitations
        if limitation in REPLAY_COACHING_REPORT_LIMITATIONS
    )
    selected.update(
        limitation
        for pattern in analysis.guidance.patterns
        for limitation in pattern.limitations
        if limitation in REPLAY_COACHING_REPORT_LIMITATIONS
    )
    if any(
        assessment.assessment_status == "not_assessable"
        for assessment in analysis.assessments
    ):
        selected.add("incomplete_assessment_coverage")
    return tuple(
        limitation
        for limitation in REPLAY_COACHING_REPORT_LIMITATIONS
        if limitation in selected
    )


@dataclass(frozen=True)
class ReplayCoachingReport:
    """Complete immutable internal Replay Coaching report for one game."""

    report_version: int
    report_method: str
    information_policy: str
    outcome_context_policy: str
    source_game_id: str
    source_review_method: str
    source_review_settings: Mapping[str, Any]
    game_context: ReplayCoachingGameContext
    outcome_context: ReplayCoachingOutcomeContext
    coverage_summary: ReplayCoachingCoverageSummary
    decision_assessments: tuple[ReplayCoachingDecisionAssessment, ...]
    prioritization: ReplayCoachingPrioritizationResult
    guidance: ReplayCoachingGuidanceResult
    player_summaries: tuple[ReplayCoachingScopeSummary, ...]
    role_summaries: tuple[ReplayCoachingScopeSummary, ...]
    phase_summaries: tuple[ReplayCoachingScopeSummary, ...]
    contract_summaries: tuple[ReplayCoachingScopeSummary, ...]
    limitations: tuple[str, ...]
    historical_record: InitVar[HistoricalGameRecord]
    coaching_analysis: InitVar[HistoricalSearchReviewCoachingAnalysis]

    def __post_init__(
        self,
        historical_record: HistoricalGameRecord,
        coaching_analysis: HistoricalSearchReviewCoachingAnalysis,
    ) -> None:
        if (
            self.report_version != REPLAY_COACHING_REPORT_VERSION
            or self.report_method != REPLAY_COACHING_REPORT_METHOD
            or self.information_policy != REPLAY_COACHING_INFORMATION_POLICY
            or self.outcome_context_policy != REPLAY_COACHING_OUTCOME_CONTEXT_POLICY
        ):
            raise ValueError("Replay Coaching report contract metadata is invalid.")
        _validate_source_review(historical_record, coaching_analysis)
        if (
            self.source_game_id != historical_record.game_id
            or self.source_review_method != HISTORICAL_SEARCH_REVIEW_ANALYSIS_METHOD
            or self.game_context.source_game_id != self.source_game_id
            or self.outcome_context.source_game_id != self.source_game_id
        ):
            raise ValueError("Replay Coaching report source metadata does not match.")
        if _thaw_json_value(self.source_review_settings) != _thaw_json_value(
            coaching_analysis.public_review_summary["settings"]
        ):
            raise ValueError("Report source settings must match the retained review.")
        if self.decision_assessments is not coaching_analysis.assessments:
            raise ValueError("Report assessments must reuse the exact source sequence.")
        if (
            self.prioritization is not coaching_analysis.prioritization
            or self.guidance is not coaching_analysis.guidance
        ):
            raise ValueError("Report must retain source prioritization and guidance.")
        expected_coverage = build_replay_coaching_coverage_summary(coaching_analysis)
        expected_scope_groups = build_replay_coaching_scope_summaries(
            historical_record, coaching_analysis
        )
        expected_game_context = build_replay_coaching_game_context(
            historical_record,
            recorded_decision_count=len(coaching_analysis.assessments),
        )
        expected_outcome_context = build_replay_coaching_outcome_context(
            historical_record
        )
        if (
            self.game_context != expected_game_context
            or self.outcome_context != expected_outcome_context
        ):
            raise ValueError("Report contexts must match the source historical game.")
        if self.coverage_summary != expected_coverage:
            raise ValueError("Report coverage does not match retained assessments.")
        expected_groups = (
            ("player", self.player_summaries, 3),
            ("role", self.role_summaries, 2),
            ("phase", self.phase_summaries, 3),
            ("contract", self.contract_summaries, 1),
        )
        for scope, summaries, count in expected_groups:
            if (
                not isinstance(summaries, tuple)
                or len(summaries) != count
                or any(summary.scope != scope for summary in summaries)
            ):
                raise ValueError(f"Report {scope} summaries are incomplete.")
        if (
            self.player_summaries,
            self.role_summaries,
            self.phase_summaries,
            self.contract_summaries,
        ) != expected_scope_groups:
            raise ValueError("Report scope summaries do not match retained assessments.")
        if self.limitations != _build_report_limitations(coaching_analysis):
            raise ValueError("Report limitations do not match retained evidence.")
        object.__setattr__(
            self, "source_review_settings", _freeze_json_value(self.source_review_settings)
        )
        object.__setattr__(self, "decision_assessments", tuple(self.decision_assessments))
        for field_name in (
            "player_summaries",
            "role_summaries",
            "phase_summaries",
            "contract_summaries",
            "limitations",
        ):
            object.__setattr__(self, field_name, tuple(getattr(self, field_name)))


@dataclass(frozen=True)
class HistoricalReplayCoachingAnalysis:
    """One-pass review artifacts plus the complete internal report."""

    public_review_summary: Mapping[str, Any]
    assessments: tuple[ReplayCoachingDecisionAssessment, ...]
    prioritization: ReplayCoachingPrioritizationResult
    guidance: ReplayCoachingGuidanceResult
    report: ReplayCoachingReport

    def __post_init__(self) -> None:
        if (
            self.report.decision_assessments != self.assessments
            or self.report.prioritization is not self.prioritization
            or self.report.guidance is not self.guidance
            or self.report.source_game_id
            != self.public_review_summary.get("source_game_id")
        ):
            raise ValueError("Historical Replay Coaching artifacts do not reconcile.")
        object.__setattr__(
            self, "public_review_summary", _freeze_json_value(self.public_review_summary)
        )
        object.__setattr__(self, "assessments", tuple(self.assessments))


def build_replay_coaching_report(
    historical_record: HistoricalGameRecord,
    coaching_analysis: HistoricalSearchReviewCoachingAnalysis,
) -> ReplayCoachingReport:
    """Composes a report after all decision coaching artifacts already exist."""
    _validate_source_review(historical_record, coaching_analysis)
    game_context = build_replay_coaching_game_context(
        historical_record,
        recorded_decision_count=len(coaching_analysis.assessments),
    )
    coverage = build_replay_coaching_coverage_summary(coaching_analysis)
    player, role, phase, contract = build_replay_coaching_scope_summaries(
        historical_record, coaching_analysis
    )
    limitations = _build_report_limitations(coaching_analysis)
    # Final outcome context is intentionally attached after all coaching derivation.
    outcome_context = build_replay_coaching_outcome_context(historical_record)
    return ReplayCoachingReport(
        report_version=REPLAY_COACHING_REPORT_VERSION,
        report_method=REPLAY_COACHING_REPORT_METHOD,
        information_policy=REPLAY_COACHING_INFORMATION_POLICY,
        outcome_context_policy=REPLAY_COACHING_OUTCOME_CONTEXT_POLICY,
        source_game_id=historical_record.game_id,
        source_review_method=HISTORICAL_SEARCH_REVIEW_ANALYSIS_METHOD,
        source_review_settings=coaching_analysis.public_review_summary["settings"],
        game_context=game_context,
        outcome_context=outcome_context,
        coverage_summary=coverage,
        decision_assessments=coaching_analysis.assessments,
        prioritization=coaching_analysis.prioritization,
        guidance=coaching_analysis.guidance,
        player_summaries=player,
        role_summaries=role,
        phase_summaries=phase,
        contract_summaries=contract,
        limitations=limitations,
        historical_record=historical_record,
        coaching_analysis=coaching_analysis,
    )


def build_historical_replay_coaching_analysis(
    snapshot_summary: HistoricalDecisionSnapshotSummary,
    historical_record: HistoricalGameRecord,
    base_search_seed: int,
    search_budget_profile: str = HISTORICAL_REVIEW_SEARCH_BUDGET_PROFILE,
    immediate_sample_count: int = DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT,
    immediate_base_random_seed: int | None = None,
) -> HistoricalReplayCoachingAnalysis:
    """Runs one existing review pass, then composes its complete internal report."""
    coaching = build_historical_search_review_coaching_analysis(
        snapshot_summary,
        historical_record,
        base_search_seed,
        search_budget_profile,
        immediate_sample_count,
        immediate_base_random_seed,
    )
    report = build_replay_coaching_report(historical_record, coaching)
    return HistoricalReplayCoachingAnalysis(
        public_review_summary=coaching.public_review_summary,
        assessments=coaching.assessments,
        prioritization=coaching.prioritization,
        guidance=coaching.guidance,
        report=report,
    )


def build_serializable_replay_coaching_report(
    report: ReplayCoachingReport,
) -> dict[str, Any]:
    """Serializes the internal report without private deal or Search-state data."""
    return {
        "report_version": report.report_version,
        "report_method": report.report_method,
        "information_policy": report.information_policy,
        "outcome_context_policy": report.outcome_context_policy,
        "source_game_id": report.source_game_id,
        "source_review_method": report.source_review_method,
        "source_review_settings": _thaw_json_value(report.source_review_settings),
        "game_context": build_serializable_replay_coaching_game_context(
            report.game_context
        ),
        "outcome_context": build_serializable_replay_coaching_outcome_context(
            report.outcome_context
        ),
        "coverage_summary": build_serializable_replay_coaching_coverage_summary(
            report.coverage_summary
        ),
        "decision_assessments": [
            build_serializable_replay_coaching_decision_assessment(assessment)
            for assessment in report.decision_assessments
        ],
        "prioritization": build_serializable_replay_coaching_prioritization_result(
            report.prioritization
        ),
        "guidance": build_serializable_replay_coaching_guidance_result(
            report.guidance
        ),
        "player_summaries": [
            build_serializable_replay_coaching_scope_summary(summary)
            for summary in report.player_summaries
        ],
        "role_summaries": [
            build_serializable_replay_coaching_scope_summary(summary)
            for summary in report.role_summaries
        ],
        "phase_summaries": [
            build_serializable_replay_coaching_scope_summary(summary)
            for summary in report.phase_summaries
        ],
        "contract_summaries": [
            build_serializable_replay_coaching_scope_summary(summary)
            for summary in report.contract_summaries
        ],
        "limitations": list(report.limitations),
    }
