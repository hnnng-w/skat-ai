from dataclasses import dataclass
from typing import Any

from skatmind.post_game_review import NOT_AVAILABLE_DECISION_QUALITY
from skatmind.replay_coaching_evidence import (
    REPLAY_COACHING_CONTRACT_VERSION,
    DecisionTimeReplayCoachingEvidence,
    build_serializable_decision_time_replay_coaching_evidence,
)
from skatmind.retrospective_search_comparison import (
    SearchActualCardComparison,
    build_search_actual_card_comparison,
    build_serializable_search_actual_card_comparison,
)

REPLAY_COACHING_ASSESSMENT_STATUSES = (
    "forced_move",
    "best_or_equivalent",
    "strictly_below_best",
    "not_assessable",
)
REPLAY_COACHING_EVIDENCE_BASES = (
    "all_compatible_worlds",
    "sampled_compatible_worlds",
    "completed_common_prefix",
    "immediate_expected_value",
    "none",
)
REPLAY_COACHING_IMPACT_TIERS = (
    "no_missed_impact",
    "contract_success",
    "settlement_score",
    "card_point_margin",
    "immediate_only",
    "not_assessable",
)
REPLAY_COACHING_FACTORS = (
    "forced_move",
    "aggregate_equivalent_choice",
    "strictly_lower_contract_success",
    "strictly_lower_settlement_score",
    "strictly_lower_card_point_margin",
    "immediate_only_best_or_equivalent",
    "immediate_only_better_alternative",
    "search_unavailable",
    "no_assessable_evidence",
    "null_margin_not_applicable",
)
REPLAY_COACHING_LIMITATIONS = (
    "bounded_late_game_search",
    "determinization_strategy_fusion",
    "sampled_compatible_worlds",
    "completed_common_prefix",
    "immediate_expected_value_only",
    "search_unavailable",
    "observed_card_not_ground_truth",
    "no_assessable_evidence",
)
IMMEDIATE_BASELINE_QUALITIES = (
    "not_available",
    "optimal",
    "acceptable",
    "suboptimal",
    "mistake",
)


def _ordered_subset(values: tuple[str, ...], canonical: tuple[str, ...], name: str) -> None:
    if len(values) != len(set(values)) or any(value not in canonical for value in values):
        raise ValueError(f"{name} must contain unique supported values.")
    expected = tuple(value for value in canonical if value in values)
    if values != expected:
        raise ValueError(f"{name} must use deterministic canonical order.")


def _candidate_by_card(evidence: DecisionTimeReplayCoachingEvidence, card: str):
    return next(
        (
            candidate
            for candidate in evidence.immediate_evidence.candidates
            if candidate.card == card
        ),
        None,
    )


def _expected_basis(
    evidence: DecisionTimeReplayCoachingEvidence,
    search_comparison: SearchActualCardComparison,
) -> str:
    if search_comparison.is_available:
        if search_comparison.comparison_basis not in REPLAY_COACHING_EVIDENCE_BASES[:3]:
            raise ValueError("Available Search comparison requires a supported evidence basis.")
        search_result = evidence.bounded_search_result
        expected_search_basis = (
            "all_compatible_worlds"
            if search_result.status == "complete"
            and search_result.world_coverage == "all_compatible_worlds"
            else "sampled_compatible_worlds"
            if search_result.status == "complete"
            and search_result.world_coverage == "sampled_compatible_worlds"
            else "completed_common_prefix"
        )
        if search_comparison.comparison_basis != expected_search_basis:
            raise ValueError("Search comparison basis does not match the Search result.")
        return str(search_comparison.comparison_basis)
    if evidence.immediate_evidence.is_available:
        return "immediate_expected_value"
    return "none"


def _build_limitations(evidence_basis: str) -> tuple[str, ...]:
    selected = {"observed_card_not_ground_truth"}
    if evidence_basis in REPLAY_COACHING_EVIDENCE_BASES[:3]:
        selected.update({"bounded_late_game_search", "determinization_strategy_fusion"})
        if evidence_basis == "sampled_compatible_worlds":
            selected.add("sampled_compatible_worlds")
        elif evidence_basis == "completed_common_prefix":
            selected.add("completed_common_prefix")
    elif evidence_basis == "immediate_expected_value":
        selected.update({"immediate_expected_value_only", "search_unavailable"})
    else:
        selected.update({"search_unavailable", "no_assessable_evidence"})
    return tuple(value for value in REPLAY_COACHING_LIMITATIONS if value in selected)


@dataclass(frozen=True)
class ReplayCoachingDecisionAssessment:
    """Version-1 retrospective attachment for one observed legal card."""

    contract_version: int
    decision_time_evidence: DecisionTimeReplayCoachingEvidence
    actual_card: str
    assessment_status: str
    evidence_basis: str
    impact_tier: str
    best_card: str | None
    actual_card_rank: int | None
    best_card_rank: int | None
    strictly_better_card_count: int | None
    aggregate_equivalent: bool | None
    search_actual_card_comparison: SearchActualCardComparison
    immediate_baseline_quality: str
    immediate_expected_point_swing_gap: float | None
    factors: tuple[str, ...]
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.contract_version != REPLAY_COACHING_CONTRACT_VERSION:
            raise ValueError("Unsupported replay-coaching assessment contract version.")
        if not isinstance(self.decision_time_evidence, DecisionTimeReplayCoachingEvidence):
            raise ValueError("decision_time_evidence has the wrong type.")
        if self.actual_card not in self.decision_time_evidence.legal_cards:
            raise ValueError("actual_card must be legal at decision time.")
        if self.assessment_status not in REPLAY_COACHING_ASSESSMENT_STATUSES:
            raise ValueError(f"Invalid assessment_status: {self.assessment_status}")
        if self.evidence_basis not in REPLAY_COACHING_EVIDENCE_BASES:
            raise ValueError(f"Invalid evidence_basis: {self.evidence_basis}")
        if self.impact_tier not in REPLAY_COACHING_IMPACT_TIERS:
            raise ValueError(f"Invalid impact_tier: {self.impact_tier}")
        if not isinstance(self.search_actual_card_comparison, SearchActualCardComparison):
            raise ValueError("search_actual_card_comparison has the wrong type.")
        if self.search_actual_card_comparison.actual_card != self.actual_card:
            raise ValueError("Search actual-card comparison must match actual_card.")
        expected_search_comparison = build_search_actual_card_comparison(
            self.decision_time_evidence.bounded_search_result,
            self.actual_card,
        )
        if self.search_actual_card_comparison != expected_search_comparison:
            raise ValueError(
                "Search actual-card comparison must match the bounded Search result."
            )
        expected_basis = _expected_basis(
            self.decision_time_evidence, self.search_actual_card_comparison
        )
        if self.evidence_basis != expected_basis:
            raise ValueError("evidence_basis does not match available evidence priority.")
        if self.immediate_baseline_quality not in IMMEDIATE_BASELINE_QUALITIES:
            raise ValueError("Invalid immediate_baseline_quality.")
        if not isinstance(self.factors, tuple) or not isinstance(self.limitations, tuple):
            raise TypeError("factors and limitations must be tuples.")
        _ordered_subset(self.factors, REPLAY_COACHING_FACTORS, "factors")
        _ordered_subset(self.limitations, REPLAY_COACHING_LIMITATIONS, "limitations")
        if self.limitations != _build_limitations(self.evidence_basis):
            raise ValueError("limitations do not match the evidence basis.")
        self._validate_classification()

    def _validate_classification(self) -> None:
        legal_count = len(self.decision_time_evidence.legal_cards)
        expected_factor_set: set[str] = set()
        if self.evidence_basis in {"immediate_expected_value", "none"}:
            expected_factor_set.add("search_unavailable")
        if self.decision_time_evidence.game_type == "null":
            expected_factor_set.add("null_margin_not_applicable")
        if self.assessment_status == "forced_move":
            if legal_count != 1 or self.impact_tier != "no_missed_impact":
                raise ValueError(
                    "forced_move requires exactly one legal card and no missed impact."
                )
            if self.factors[0:1] != ("forced_move",):
                raise ValueError("forced_move requires the forced_move factor.")
            expected_factor_set.add("forced_move")
        elif legal_count == 1:
            raise ValueError("A one-card decision must be classified as forced_move.")

        if (
            self.assessment_status == "best_or_equivalent"
            and self.impact_tier != "no_missed_impact"
        ):
            raise ValueError("best_or_equivalent requires no_missed_impact.")
        if self.assessment_status == "strictly_below_best" and self.impact_tier not in {
            "contract_success",
            "settlement_score",
            "card_point_margin",
            "immediate_only",
        }:
            raise ValueError("strictly_below_best requires a supported positive impact.")
        if self.assessment_status == "not_assessable":
            if (
                self.evidence_basis != "none"
                or self.impact_tier != "not_assessable"
                or any(
                    value is not None
                    for value in (
                        self.best_card,
                        self.actual_card_rank,
                        self.best_card_rank,
                        self.strictly_better_card_count,
                        self.aggregate_equivalent,
                        self.immediate_expected_point_swing_gap,
                    )
                )
                or self.immediate_baseline_quality != NOT_AVAILABLE_DECISION_QUALITY
                or "no_assessable_evidence" not in self.factors
            ):
                raise ValueError("not_assessable fields are inconsistent.")
            expected_factor_set.add("no_assessable_evidence")
            expected_factors = tuple(
                value for value in REPLAY_COACHING_FACTORS if value in expected_factor_set
            )
            if self.factors != expected_factors:
                raise ValueError("factors do not match the assessment classification.")
            return
        if self.best_card not in self.decision_time_evidence.legal_cards:
            raise ValueError("Assessable decisions require a legal best_card.")
        for field_name, value in (
            ("actual_card_rank", self.actual_card_rank),
            ("best_card_rank", self.best_card_rank),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{field_name} must be a positive integer.")
        if (
            isinstance(self.strictly_better_card_count, bool)
            or not isinstance(self.strictly_better_card_count, int)
            or self.strictly_better_card_count < 0
        ):
            raise ValueError("strictly_better_card_count must be non-negative.")
        if (
            self.decision_time_evidence.game_type == "null"
            and self.impact_tier == "card_point_margin"
        ):
            raise ValueError("Null assessments cannot use card-point-margin impact.")
        if self.evidence_basis in REPLAY_COACHING_EVIDENCE_BASES[:3]:
            comparison = self.search_actual_card_comparison
            if (
                self.best_card != comparison.search_recommended_card
                or self.actual_card_rank != comparison.actual_card_rank
                or self.best_card_rank != comparison.recommended_card_rank
                or self.strictly_better_card_count != comparison.strictly_better_card_count
                or self.aggregate_equivalent
                != comparison.actual_card_is_aggregate_equivalent_to_recommendation
            ):
                raise ValueError("Search assessment fields must align with its comparison.")
            better_count = comparison.strictly_better_card_count
            if legal_count > 1 and better_count == 0:
                if (
                    self.assessment_status != "best_or_equivalent"
                    or self.impact_tier != "no_missed_impact"
                    or self.aggregate_equivalent is not True
                ):
                    raise ValueError("Search-equivalent classification is inconsistent.")
                if self.actual_card != self.best_card:
                    expected_factor_set.add("aggregate_equivalent_choice")
            elif legal_count > 1:
                if self.assessment_status != "strictly_below_best":
                    raise ValueError("A Search gap requires strictly_below_best.")
                gaps = (
                    ("contract_success", comparison.contract_success_rate_gap),
                    ("settlement_score", comparison.mean_local_side_game_score_gap),
                    ("card_point_margin", comparison.mean_local_side_card_point_margin_gap),
                )
                expected_impact = next(
                    (name for name, gap in gaps if gap is not None and gap > 0),
                    None,
                )
                if expected_impact is None or self.impact_tier != expected_impact:
                    raise ValueError("Search impact does not match the first positive gap.")
                expected_factor_set.add(
                    {
                        "contract_success": "strictly_lower_contract_success",
                        "settlement_score": "strictly_lower_settlement_score",
                        "card_point_margin": "strictly_lower_card_point_margin",
                    }[expected_impact]
                )
        elif self.aggregate_equivalent is not None:
            raise ValueError("aggregate_equivalent is available only from Search evidence.")
        if self.evidence_basis == "immediate_expected_value":
            immediate = self.decision_time_evidence.immediate_evidence
            actual = _candidate_by_card(self.decision_time_evidence, self.actual_card)
            best = _candidate_by_card(
                self.decision_time_evidence, str(immediate.recommended_card)
            )
            if actual is None or best is None:
                raise ValueError("Immediate assessment cards are missing.")
            expected_better_count = sum(
                candidate.objective_utility > actual.objective_utility
                for candidate in immediate.candidates
            )
            expected_gap = best.expected_point_swing - actual.expected_point_swing
            if (
                self.best_card != best.card
                or self.actual_card_rank != actual.rank
                or self.best_card_rank != best.rank
                or self.strictly_better_card_count != expected_better_count
                or self.immediate_expected_point_swing_gap != expected_gap
            ):
                raise ValueError("Immediate assessment fields do not align with evidence.")
            if legal_count > 1 and expected_better_count == 0:
                if (
                    self.assessment_status != "best_or_equivalent"
                    or self.impact_tier != "no_missed_impact"
                ):
                    raise ValueError("Immediate best-equivalent classification is inconsistent.")
                expected_factor_set.add("immediate_only_best_or_equivalent")
            elif legal_count > 1:
                if (
                    self.assessment_status != "strictly_below_best"
                    or self.impact_tier != "immediate_only"
                ):
                    raise ValueError("Immediate alternative classification is inconsistent.")
                expected_factor_set.add("immediate_only_better_alternative")
        immediate = self.decision_time_evidence.immediate_evidence
        if immediate.is_available:
            immediate_actual = _candidate_by_card(
                self.decision_time_evidence, self.actual_card
            )
            immediate_best = _candidate_by_card(
                self.decision_time_evidence, str(immediate.recommended_card)
            )
            if immediate_actual is None or immediate_best is None:
                raise ValueError("Immediate baseline cards are missing.")
            expected_immediate_gap = (
                immediate_best.expected_point_swing
                - immediate_actual.expected_point_swing
            )
            if self.immediate_expected_point_swing_gap != expected_immediate_gap:
                raise ValueError("Immediate expected-point-swing gap is inconsistent.")
        elif (
            self.immediate_baseline_quality != NOT_AVAILABLE_DECISION_QUALITY
            or self.immediate_expected_point_swing_gap is not None
        ):
            raise ValueError(
                "Unavailable Immediate evidence requires unavailable baseline fields."
            )
        expected_factors = tuple(
            value for value in REPLAY_COACHING_FACTORS if value in expected_factor_set
        )
        if self.factors != expected_factors:
            raise ValueError("factors do not match the assessment classification.")


def build_replay_coaching_decision_assessment(
    *,
    decision_time_evidence: DecisionTimeReplayCoachingEvidence,
    actual_card: str,
    search_actual_card_comparison: SearchActualCardComparison,
    immediate_baseline_quality: str,
) -> ReplayCoachingDecisionAssessment:
    """Attaches one observed card without rerunning Search or Immediate analysis."""
    if actual_card not in decision_time_evidence.legal_cards:
        raise ValueError("actual_card must be legal at decision time.")
    evidence_basis = _expected_basis(
        decision_time_evidence, search_actual_card_comparison
    )
    immediate = decision_time_evidence.immediate_evidence
    immediate_actual = _candidate_by_card(decision_time_evidence, actual_card)
    immediate_best = (
        _candidate_by_card(decision_time_evidence, immediate.recommended_card)
        if immediate.recommended_card is not None
        else None
    )
    immediate_gap = (
        immediate_best.expected_point_swing - immediate_actual.expected_point_swing
        if immediate_best is not None and immediate_actual is not None
        else None
    )

    factor_set: set[str] = set()
    if evidence_basis in {"immediate_expected_value", "none"}:
        factor_set.add("search_unavailable")
    if decision_time_evidence.game_type == "null":
        factor_set.add("null_margin_not_applicable")

    if len(decision_time_evidence.legal_cards) == 1:
        status = "forced_move"
        impact = "no_missed_impact"
        factor_set.add("forced_move")
        if search_actual_card_comparison.is_available:
            best_card = search_actual_card_comparison.search_recommended_card
            actual_rank = search_actual_card_comparison.actual_card_rank
            best_rank = search_actual_card_comparison.recommended_card_rank
            better_count = search_actual_card_comparison.strictly_better_card_count
            aggregate_equivalent = (
                search_actual_card_comparison.actual_card_is_aggregate_equivalent_to_recommendation
            )
        elif immediate_actual is not None and immediate_best is not None:
            best_card = immediate_best.card
            actual_rank = immediate_actual.rank
            best_rank = immediate_best.rank
            better_count = 0
            aggregate_equivalent = None
        else:
            best_card = actual_card
            actual_rank = 1
            best_rank = 1
            better_count = 0
            aggregate_equivalent = None
    elif search_actual_card_comparison.is_available:
        comparison = search_actual_card_comparison
        best_card = comparison.search_recommended_card
        actual_rank = comparison.actual_card_rank
        best_rank = comparison.recommended_card_rank
        better_count = comparison.strictly_better_card_count
        aggregate_equivalent = comparison.actual_card_is_aggregate_equivalent_to_recommendation
        if better_count == 0:
            status = "best_or_equivalent"
            impact = "no_missed_impact"
            if actual_card != best_card:
                factor_set.add("aggregate_equivalent_choice")
        else:
            status = "strictly_below_best"
            gaps = (
                ("contract_success", comparison.contract_success_rate_gap),
                ("settlement_score", comparison.mean_local_side_game_score_gap),
                ("card_point_margin", comparison.mean_local_side_card_point_margin_gap),
            )
            impact = next((name for name, gap in gaps if gap is not None and gap > 0), "")
            if not impact:
                raise ValueError(
                    "A strictly-below-best Search assessment requires a positive supported gap."
                )
            factor_set.add(
                {
                    "contract_success": "strictly_lower_contract_success",
                    "settlement_score": "strictly_lower_settlement_score",
                    "card_point_margin": "strictly_lower_card_point_margin",
                }[impact]
            )
    elif immediate.is_available:
        if immediate_actual is None or immediate_best is None:
            raise ValueError("Immediate evidence does not contain the actual or best card.")
        better_count = sum(
            candidate.objective_utility > immediate_actual.objective_utility
            for candidate in immediate.candidates
        )
        best_card = immediate_best.card
        actual_rank = immediate_actual.rank
        best_rank = immediate_best.rank
        aggregate_equivalent = None
        if better_count == 0:
            status = "best_or_equivalent"
            impact = "no_missed_impact"
            factor_set.add("immediate_only_best_or_equivalent")
        else:
            status = "strictly_below_best"
            impact = "immediate_only"
            factor_set.add("immediate_only_better_alternative")
    else:
        status = "not_assessable"
        impact = "not_assessable"
        best_card = None
        actual_rank = None
        best_rank = None
        better_count = None
        aggregate_equivalent = None
        immediate_gap = None
        factor_set.add("no_assessable_evidence")

    factors = tuple(value for value in REPLAY_COACHING_FACTORS if value in factor_set)
    return ReplayCoachingDecisionAssessment(
        contract_version=REPLAY_COACHING_CONTRACT_VERSION,
        decision_time_evidence=decision_time_evidence,
        actual_card=actual_card,
        assessment_status=status,
        evidence_basis=evidence_basis,
        impact_tier=impact,
        best_card=best_card,
        actual_card_rank=actual_rank,
        best_card_rank=best_rank,
        strictly_better_card_count=better_count,
        aggregate_equivalent=aggregate_equivalent,
        search_actual_card_comparison=search_actual_card_comparison,
        immediate_baseline_quality=immediate_baseline_quality,
        immediate_expected_point_swing_gap=immediate_gap,
        factors=factors,
        limitations=_build_limitations(evidence_basis),
    )


def build_serializable_replay_coaching_decision_assessment(
    assessment: ReplayCoachingDecisionAssessment,
) -> dict[str, Any]:
    """Serializes retrospective comparison fields without final outcome context."""
    return {
        "contract_version": assessment.contract_version,
        "decision_time_evidence": (
            build_serializable_decision_time_replay_coaching_evidence(
                assessment.decision_time_evidence
            )
        ),
        "actual_card": assessment.actual_card,
        "assessment_status": assessment.assessment_status,
        "evidence_basis": assessment.evidence_basis,
        "impact_tier": assessment.impact_tier,
        "best_card": assessment.best_card,
        "actual_card_rank": assessment.actual_card_rank,
        "best_card_rank": assessment.best_card_rank,
        "strictly_better_card_count": assessment.strictly_better_card_count,
        "aggregate_equivalent": assessment.aggregate_equivalent,
        "search_actual_card_comparison": (
            build_serializable_search_actual_card_comparison(
                assessment.search_actual_card_comparison
            )
        ),
        "immediate_baseline_quality": assessment.immediate_baseline_quality,
        "immediate_expected_point_swing_gap": (
            assessment.immediate_expected_point_swing_gap
        ),
        "factors": list(assessment.factors),
        "limitations": list(assessment.limitations),
    }
