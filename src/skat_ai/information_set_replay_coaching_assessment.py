from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from skat_ai.bounded_search_result import AggregateSearchCandidateResult
from skat_ai.historical_information_set_search_review import (
    HistoricalInformationSetSearchDecisionReviewV1,
)
from skat_ai.information_set_replay_coaching_evidence import (
    InformationSetReplayCoachingDecisionTimeEvidenceV1,
    attach_retained_actual_card_to_information_set_replay_coaching_evidence_v1,
    build_information_set_replay_coaching_decision_time_evidence_v1,
    build_serializable_information_set_replay_coaching_decision_time_evidence_v1,
)
from skat_ai.information_set_search_comparison import (
    InformationSetSearchComparisonV1,
    attach_actual_card_to_information_set_search_comparison_v1,
    build_serializable_information_set_search_comparison_v1,
)
from skat_ai.replay_coaching_assessment import REPLAY_COACHING_ASSESSMENT_STATUSES

INFORMATION_SET_REPLAY_COACHING_ASSESSMENT_VERSION = 1
INFORMATION_SET_REPLAY_COACHING_ASSESSMENT_POLICY = (
    "complete_information_set_candidates_or_not_assessable"
)
INFORMATION_SET_REPLAY_COACHING_ASSESSMENT_STATUSES = (
    REPLAY_COACHING_ASSESSMENT_STATUSES
)
INFORMATION_SET_REPLAY_COACHING_EVIDENCE_BASES = (
    "information_set_single_exact_world",
    "information_set_all_compatible_worlds",
    "information_set_sampled_compatible_worlds",
    "none",
)
INFORMATION_SET_REPLAY_COACHING_IMPACT_TIERS = (
    "no_missed_impact",
    "contract_success",
    "settlement_score",
    "card_point_margin",
    "not_assessable",
)
INFORMATION_SET_REPLAY_COACHING_FACTORS = (
    "forced_move",
    "aggregate_equivalent_choice",
    "strictly_lower_contract_success",
    "strictly_lower_settlement_score",
    "strictly_lower_card_point_margin",
    "search_unavailable",
    "no_assessable_evidence",
    "null_margin_not_applicable",
)
INFORMATION_SET_REPLAY_COACHING_ASSESSMENT_LIMITATIONS = (
    "bounded_three_trick_information_set_search",
    "controlled_player_selected_world_consistency",
    "fixed_opponent_policy_model",
    "sampled_compatible_worlds",
    "search_unavailable",
    "observed_card_not_ground_truth",
    "incomplete_assessment_coverage",
    "no_equilibrium_or_global_optimality_claim",
)


def _ordered_subset(values: tuple[str, ...], canonical: tuple[str, ...]) -> bool:
    return values == tuple(value for value in canonical if value in values) and len(
        values
    ) == len(set(values))


def _candidate_metrics(
    candidate: AggregateSearchCandidateResult,
    game_type: str,
) -> tuple[float, float, float]:
    if (
        candidate.local_contract_success_rate is None
        or candidate.mean_local_side_game_score is None
    ):
        raise ValueError("Assessable Candidate aggregates must be complete.")
    margin = 0.0
    if game_type != "null":
        if candidate.mean_local_side_card_point_margin is None:
            raise ValueError("Suit and Grand Candidates require card-point margins.")
        margin = candidate.mean_local_side_card_point_margin
    return (
        candidate.local_contract_success_rate,
        candidate.mean_local_side_game_score,
        margin,
    )


def _complete_candidates(
    evidence: InformationSetReplayCoachingDecisionTimeEvidenceV1,
) -> tuple[AggregateSearchCandidateResult, ...] | None:
    result = evidence.information_set_pre_actual_analysis.information_set_result
    if result is None or result.status != "complete":
        return None
    cards = tuple(candidate.card for candidate in result.candidate_results)
    if len(cards) != len(evidence.legal_cards) or set(cards) != set(
        evidence.legal_cards
    ):
        return None
    if result.recommended_card is None or not result.candidate_results:
        return None
    return result.candidate_results


def _evidence_basis(
    evidence: InformationSetReplayCoachingDecisionTimeEvidenceV1,
) -> str:
    candidates = _complete_candidates(evidence)
    if candidates is None:
        return "none"
    result = evidence.information_set_pre_actual_analysis.information_set_result
    if result is None:
        return "none"
    if result.world_coverage == "sampled_compatible_worlds":
        return "information_set_sampled_compatible_worlds"
    # Information-set Search labels an exhaustive one-world result as all-compatible.
    if result.world_coverage == "single_exact_world" or (
        result.world_coverage == "all_compatible_worlds"
        and result.compatible_world_count == 1
    ):
        return "information_set_single_exact_world"
    if result.world_coverage == "all_compatible_worlds":
        return "information_set_all_compatible_worlds"
    return "none"


def _limitations(
    *,
    evidence_basis: str,
    assessment_status: str,
) -> tuple[str, ...]:
    selected = {
        "fixed_opponent_policy_model",
        "observed_card_not_ground_truth",
        "no_equilibrium_or_global_optimality_claim",
    }
    if evidence_basis != "none":
        selected.update(
            {
                "bounded_three_trick_information_set_search",
                "controlled_player_selected_world_consistency",
            }
        )
    else:
        selected.add("search_unavailable")
    if evidence_basis == "information_set_sampled_compatible_worlds":
        selected.add("sampled_compatible_worlds")
    if assessment_status == "not_assessable":
        selected.add("incomplete_assessment_coverage")
    return tuple(
        value
        for value in INFORMATION_SET_REPLAY_COACHING_ASSESSMENT_LIMITATIONS
        if value in selected
    )


def _derived_assessment_values(
    evidence: InformationSetReplayCoachingDecisionTimeEvidenceV1,
    actual_card: str,
) -> dict[str, Any]:
    basis = _evidence_basis(evidence)
    candidates = _complete_candidates(evidence) if basis != "none" else None
    factor_set: set[str] = set()
    if basis == "none":
        factor_set.add("search_unavailable")
    if evidence.game_type == "null":
        factor_set.add("null_margin_not_applicable")

    if len(evidence.legal_cards) == 1:
        status = "forced_move"
        impact = "no_missed_impact"
        factor_set.add("forced_move")
        if candidates is None:
            best_card = actual_card
            actual_rank = 1
            best_rank = 1
            better_count = 0
            aggregate_equivalent = None
            success_gap = None
            score_gap = None
            margin_gap = None
        else:
            candidate = candidates[0]
            best_card = candidate.card
            actual_rank = candidate.rank
            best_rank = candidate.rank
            better_count = 0
            aggregate_equivalent = True
            success_gap = 0.0
            score_gap = 0.0
            margin_gap = None if evidence.game_type == "null" else 0.0
    elif candidates is None:
        status = "not_assessable"
        impact = "not_assessable"
        best_card = None
        actual_rank = None
        best_rank = None
        better_count = None
        aggregate_equivalent = None
        success_gap = None
        score_gap = None
        margin_gap = None
        factor_set.add("no_assessable_evidence")
    else:
        by_card = {candidate.card: candidate for candidate in candidates}
        result = evidence.information_set_pre_actual_analysis.information_set_result
        if result is None or result.recommended_card is None:
            raise ValueError("Complete Candidate evidence requires a recommendation.")
        best = by_card[result.recommended_card]
        actual = by_card[actual_card]
        best_metrics = _candidate_metrics(best, evidence.game_type)
        actual_metrics = _candidate_metrics(actual, evidence.game_type)
        better_count = sum(
            _candidate_metrics(candidate, evidence.game_type) > actual_metrics
            for candidate in candidates
        )
        best_card = best.card
        actual_rank = actual.rank
        best_rank = best.rank
        aggregate_equivalent = actual_metrics == best_metrics
        success_gap = best_metrics[0] - actual_metrics[0]
        score_gap = best_metrics[1] - actual_metrics[1]
        margin_gap = (
            None
            if evidence.game_type == "null"
            else best_metrics[2] - actual_metrics[2]
        )
        if better_count == 0:
            status = "best_or_equivalent"
            impact = "no_missed_impact"
            if actual_card != best_card:
                factor_set.add("aggregate_equivalent_choice")
        else:
            status = "strictly_below_best"
            gaps = (
                ("contract_success", success_gap),
                ("settlement_score", score_gap),
                ("card_point_margin", margin_gap),
            )
            impact = next(
                (name for name, gap in gaps if gap is not None and gap > 0),
                "",
            )
            if not impact:
                raise ValueError(
                    "A below-best Information-set Candidate requires a positive gap."
                )
            factor_set.add(
                {
                    "contract_success": "strictly_lower_contract_success",
                    "settlement_score": "strictly_lower_settlement_score",
                    "card_point_margin": "strictly_lower_card_point_margin",
                }[impact]
            )
    return {
        "assessment_status": status,
        "evidence_basis": basis,
        "impact_tier": impact,
        "best_card": best_card,
        "actual_card_rank": actual_rank,
        "best_card_rank": best_rank,
        "strictly_better_card_count": better_count,
        "aggregate_equivalent": aggregate_equivalent,
        "contract_success_rate_gap": success_gap,
        "mean_local_side_game_score_gap": score_gap,
        "mean_local_side_card_point_margin_gap": margin_gap,
        "factors": tuple(
            value for value in INFORMATION_SET_REPLAY_COACHING_FACTORS if value in factor_set
        ),
        "limitations": _limitations(
            evidence_basis=basis,
            assessment_status=status,
        ),
    }


@dataclass(frozen=True, slots=True, kw_only=True)
class InformationSetReplayCoachingDecisionAssessmentV1:
    """Observed-Card assessment based only on complete Information-set Candidates."""

    information_set_replay_coaching_assessment_version: int
    decision_time_evidence: InformationSetReplayCoachingDecisionTimeEvidenceV1
    actual_card: str
    assessment_status: str
    evidence_basis: str
    impact_tier: str
    best_card: str | None
    actual_card_rank: int | None
    best_card_rank: int | None
    strictly_better_card_count: int | None
    aggregate_equivalent: bool | None
    contract_success_rate_gap: float | None
    mean_local_side_game_score_gap: float | None
    mean_local_side_card_point_margin_gap: float | None
    comparison: InformationSetSearchComparisonV1
    factors: tuple[str, ...]
    limitations: tuple[str, ...]

    @property
    def contract_version(self) -> int:
        return self.information_set_replay_coaching_assessment_version

    def __post_init__(self) -> None:
        version = self.information_set_replay_coaching_assessment_version
        if (
            isinstance(version, bool)
            or not isinstance(version, int)
            or version != INFORMATION_SET_REPLAY_COACHING_ASSESSMENT_VERSION
        ):
            raise ValueError("Unsupported information-set coaching assessment version.")
        if not isinstance(
            self.decision_time_evidence,
            InformationSetReplayCoachingDecisionTimeEvidenceV1,
        ):
            raise ValueError("decision_time_evidence has the wrong type.")
        if self.actual_card not in self.decision_time_evidence.legal_cards:
            raise ValueError("actual_card must be legal at decision time.")
        if (
            self.assessment_status
            not in INFORMATION_SET_REPLAY_COACHING_ASSESSMENT_STATUSES
        ):
            raise ValueError("assessment_status is unsupported.")
        if self.evidence_basis not in INFORMATION_SET_REPLAY_COACHING_EVIDENCE_BASES:
            raise ValueError("evidence_basis is unsupported.")
        if self.impact_tier not in INFORMATION_SET_REPLAY_COACHING_IMPACT_TIERS:
            raise ValueError("impact_tier is unsupported.")
        if not isinstance(self.comparison, InformationSetSearchComparisonV1):
            raise ValueError("comparison has the wrong type.")
        expected_comparison = (
            attach_actual_card_to_information_set_search_comparison_v1(
                self.decision_time_evidence.information_set_pre_actual_analysis,
                self.actual_card,
            )
        )
        if self.comparison != expected_comparison:
            raise ValueError("comparison must match the retained decision-time evidence.")
        if not isinstance(self.factors, tuple) or not _ordered_subset(
            self.factors,
            INFORMATION_SET_REPLAY_COACHING_FACTORS,
        ):
            raise ValueError("factors must use canonical order.")
        if not isinstance(self.limitations, tuple) or not _ordered_subset(
            self.limitations,
            INFORMATION_SET_REPLAY_COACHING_ASSESSMENT_LIMITATIONS,
        ):
            raise ValueError("limitations must use canonical order.")
        expected = _derived_assessment_values(
            self.decision_time_evidence,
            self.actual_card,
        )
        for field_name, value in expected.items():
            if getattr(self, field_name) != value:
                raise ValueError(
                    f"{field_name} does not match Information-set assessment semantics."
                )


def build_information_set_replay_coaching_decision_assessment_v1(
    *,
    decision_time_evidence: InformationSetReplayCoachingDecisionTimeEvidenceV1,
    actual_card: str,
    comparison: InformationSetSearchComparisonV1,
) -> InformationSetReplayCoachingDecisionAssessmentV1:
    """Attaches an observed Card with no PIMC or Immediate fallback."""
    if actual_card not in decision_time_evidence.legal_cards:
        raise ValueError("actual_card must be legal at decision time.")
    expected_comparison = attach_actual_card_to_information_set_search_comparison_v1(
        decision_time_evidence.information_set_pre_actual_analysis,
        actual_card,
    )
    if comparison != expected_comparison:
        raise ValueError("comparison must equal the retained actual-Card comparison.")
    values = _derived_assessment_values(decision_time_evidence, actual_card)
    return InformationSetReplayCoachingDecisionAssessmentV1(
        information_set_replay_coaching_assessment_version=(
            INFORMATION_SET_REPLAY_COACHING_ASSESSMENT_VERSION
        ),
        decision_time_evidence=decision_time_evidence,
        actual_card=actual_card,
        comparison=comparison,
        **values,
    )


def build_retained_information_set_replay_coaching_decision_assessment_v1(
    decision: HistoricalInformationSetSearchDecisionReviewV1,
) -> InformationSetReplayCoachingDecisionAssessmentV1:
    """Builds one assessment from a retained review row without any analysis rerun."""
    evidence = build_information_set_replay_coaching_decision_time_evidence_v1(
        decision
    )
    comparison = (
        attach_retained_actual_card_to_information_set_replay_coaching_evidence_v1(
            evidence,
            actual_card=decision.actual_card,
            retained_comparison=decision.comparison,
        )
    )
    return build_information_set_replay_coaching_decision_assessment_v1(
        decision_time_evidence=evidence,
        actual_card=decision.actual_card,
        comparison=comparison,
    )


def build_serializable_information_set_replay_coaching_decision_assessment_v1(
    assessment: InformationSetReplayCoachingDecisionAssessmentV1,
) -> dict[str, Any]:
    if not isinstance(
        assessment,
        InformationSetReplayCoachingDecisionAssessmentV1,
    ):
        raise ValueError("assessment has the wrong type.")
    return {
        "information_set_replay_coaching_assessment_version": (
            assessment.information_set_replay_coaching_assessment_version
        ),
        "decision_time_evidence": (
            build_serializable_information_set_replay_coaching_decision_time_evidence_v1(
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
        "contract_success_rate_gap": assessment.contract_success_rate_gap,
        "mean_local_side_game_score_gap": assessment.mean_local_side_game_score_gap,
        "mean_local_side_card_point_margin_gap": (
            assessment.mean_local_side_card_point_margin_gap
        ),
        "comparison": build_serializable_information_set_search_comparison_v1(
            assessment.comparison
        ),
        "factors": list(assessment.factors),
        "limitations": list(assessment.limitations),
    }
