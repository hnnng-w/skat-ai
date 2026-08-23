from __future__ import annotations

import math
from typing import Any


def is_information_set_replay_coaching_assessment(assessment: Any) -> bool:
    from skat_ai.information_set_replay_coaching_assessment import (
        InformationSetReplayCoachingDecisionAssessmentV1,
    )

    return isinstance(assessment, InformationSetReplayCoachingDecisionAssessmentV1)


def validate_supported_replay_coaching_assessment(assessment: Any) -> None:
    from skat_ai.replay_coaching_assessment import ReplayCoachingDecisionAssessment

    if not isinstance(assessment, ReplayCoachingDecisionAssessment) and not (
        is_information_set_replay_coaching_assessment(assessment)
    ):
        raise ValueError("assessment must be a supported Replay Coaching assessment.")


def get_replay_coaching_assessment_version(assessment: Any) -> int:
    validate_supported_replay_coaching_assessment(assessment)
    if is_information_set_replay_coaching_assessment(assessment):
        return assessment.information_set_replay_coaching_assessment_version
    return assessment.contract_version


def get_replay_coaching_evidence_basis_order(assessment: Any) -> tuple[str, ...]:
    validate_supported_replay_coaching_assessment(assessment)
    if is_information_set_replay_coaching_assessment(assessment):
        from skat_ai.information_set_replay_coaching_assessment import (
            INFORMATION_SET_REPLAY_COACHING_EVIDENCE_BASES,
        )

        return INFORMATION_SET_REPLAY_COACHING_EVIDENCE_BASES
    from skat_ai.replay_coaching_assessment import REPLAY_COACHING_EVIDENCE_BASES

    return REPLAY_COACHING_EVIDENCE_BASES


def get_replay_coaching_impact_tier_order(assessment: Any) -> tuple[str, ...]:
    validate_supported_replay_coaching_assessment(assessment)
    if is_information_set_replay_coaching_assessment(assessment):
        from skat_ai.information_set_replay_coaching_assessment import (
            INFORMATION_SET_REPLAY_COACHING_IMPACT_TIERS,
        )

        return INFORMATION_SET_REPLAY_COACHING_IMPACT_TIERS
    from skat_ai.replay_coaching_assessment import REPLAY_COACHING_IMPACT_TIERS

    return REPLAY_COACHING_IMPACT_TIERS


def get_replay_coaching_primary_gap_value(assessment: Any) -> float:
    validate_supported_replay_coaching_assessment(assessment)
    if assessment.assessment_status != "strictly_below_best":
        raise ValueError("A Key Decision primary gap requires strictly_below_best.")
    if is_information_set_replay_coaching_assessment(assessment):
        gap = {
            "contract_success": assessment.contract_success_rate_gap,
            "settlement_score": assessment.mean_local_side_game_score_gap,
            "card_point_margin": assessment.mean_local_side_card_point_margin_gap,
        }.get(assessment.impact_tier)
    elif assessment.impact_tier == "immediate_only":
        immediate = assessment.decision_time_evidence.immediate_evidence
        best = next(
            candidate
            for candidate in immediate.candidates
            if candidate.card == immediate.recommended_card
        )
        actual = next(
            candidate
            for candidate in immediate.candidates
            if candidate.card == assessment.actual_card
        )
        gap = best.objective_utility - actual.objective_utility
    else:
        comparison = assessment.search_actual_card_comparison
        gap = {
            "contract_success": comparison.contract_success_rate_gap,
            "settlement_score": comparison.mean_local_side_game_score_gap,
            "card_point_margin": comparison.mean_local_side_card_point_margin_gap,
        }.get(assessment.impact_tier)
    if (
        isinstance(gap, bool)
        or not isinstance(gap, (int, float))
        or not math.isfinite(gap)
        or gap <= 0
    ):
        raise ValueError("A Key Decision primary gap must be finite and positive.")
    return float(gap)


def has_replay_coaching_primary_search_evidence(assessment: Any) -> bool:
    bases = get_replay_coaching_evidence_basis_order(assessment)
    return assessment.evidence_basis in bases[:3]


def has_replay_coaching_search_immediate_divergence(assessment: Any) -> bool:
    validate_supported_replay_coaching_assessment(assessment)
    if is_information_set_replay_coaching_assessment(assessment):
        value = assessment.comparison.information_set_immediate_same_card
        return value is False
    comparison = assessment.decision_time_evidence.search_vs_immediate_comparison
    return comparison.is_available and comparison.same_recommended_card is False


def is_replay_coaching_divergence_actionable(assessment: Any) -> bool:
    validate_supported_replay_coaching_assessment(assessment)
    return not is_information_set_replay_coaching_assessment(assessment)
