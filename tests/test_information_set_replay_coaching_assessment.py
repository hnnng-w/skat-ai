from dataclasses import FrozenInstanceError, replace

import pytest
from test_information_set_replay_coaching_evidence import (
    _base_request_and_result,
    _decision,
    _information_result,
    _partial_or_timeout_result,
)

from skat_ai.information_set_replay_coaching_assessment import (
    INFORMATION_SET_REPLAY_COACHING_ASSESSMENT_LIMITATIONS,
    INFORMATION_SET_REPLAY_COACHING_ASSESSMENT_POLICY,
    INFORMATION_SET_REPLAY_COACHING_ASSESSMENT_STATUSES,
    INFORMATION_SET_REPLAY_COACHING_ASSESSMENT_VERSION,
    INFORMATION_SET_REPLAY_COACHING_EVIDENCE_BASES,
    INFORMATION_SET_REPLAY_COACHING_FACTORS,
    INFORMATION_SET_REPLAY_COACHING_IMPACT_TIERS,
    build_retained_information_set_replay_coaching_decision_assessment_v1,
    build_serializable_information_set_replay_coaching_decision_assessment_v1,
)
from skat_ai.information_set_search_comparison import (
    attach_actual_card_to_information_set_search_comparison_v1,
    build_information_set_search_comparison_pre_actual_analysis_v1,
)
from skat_ai.information_set_search_contracts import (
    build_unavailable_information_set_search_result_v1,
)
from skat_ai.replay_coaching_key_decisions import (
    build_replay_coaching_key_decisions,
)


def test_assessment_constants_vocabularies_and_limitations_are_exact() -> None:
    assert INFORMATION_SET_REPLAY_COACHING_ASSESSMENT_VERSION == 1
    assert INFORMATION_SET_REPLAY_COACHING_ASSESSMENT_POLICY == (
        "complete_information_set_candidates_or_not_assessable"
    )
    assert INFORMATION_SET_REPLAY_COACHING_ASSESSMENT_STATUSES == (
        "forced_move",
        "best_or_equivalent",
        "strictly_below_best",
        "not_assessable",
    )
    assert INFORMATION_SET_REPLAY_COACHING_EVIDENCE_BASES == (
        "information_set_single_exact_world",
        "information_set_all_compatible_worlds",
        "information_set_sampled_compatible_worlds",
        "none",
    )
    assert INFORMATION_SET_REPLAY_COACHING_IMPACT_TIERS == (
        "no_missed_impact",
        "contract_success",
        "settlement_score",
        "card_point_margin",
        "not_assessable",
    )
    assert "immediate_only" not in INFORMATION_SET_REPLAY_COACHING_IMPACT_TIERS
    assert INFORMATION_SET_REPLAY_COACHING_FACTORS == (
        "forced_move",
        "aggregate_equivalent_choice",
        "strictly_lower_contract_success",
        "strictly_lower_settlement_score",
        "strictly_lower_card_point_margin",
        "search_unavailable",
        "no_assessable_evidence",
        "null_margin_not_applicable",
    )
    assert INFORMATION_SET_REPLAY_COACHING_ASSESSMENT_LIMITATIONS[-1] == (
        "no_equilibrium_or_global_optimality_claim"
    )


@pytest.mark.parametrize(
    ("impact", "expected_factor"),
    [
        ("contract_success", "strictly_lower_contract_success"),
        ("settlement_score", "strictly_lower_settlement_score"),
        ("card_point_margin", "strictly_lower_card_point_margin"),
    ],
)
def test_complete_candidates_use_first_objective_gap_without_fallback(
    impact: str,
    expected_factor: str,
) -> None:
    decision = _decision(_information_result(impact))
    assessment = (
        build_retained_information_set_replay_coaching_decision_assessment_v1(
            decision
        )
    )

    assert assessment.assessment_status == "strictly_below_best"
    assert assessment.impact_tier == impact
    assert assessment.factors == (expected_factor,)
    assert assessment.best_card == decision.information_set_result.recommended_card
    assert assessment.strictly_better_card_count
    assert "immediate_only" not in assessment.factors


def test_single_world_best_and_aggregate_equivalent_mapping_are_exact() -> None:
    best_result = _information_result(coverage="single_exact_world")
    best_card = best_result.recommended_card
    assert best_card is not None
    best = build_retained_information_set_replay_coaching_decision_assessment_v1(
        _decision(best_result, actual_card=best_card)
    )
    equivalent_result = _information_result("aggregate_equivalent")
    equivalent_card = next(
        candidate.card
        for candidate in equivalent_result.candidate_results
        if candidate.card != equivalent_result.recommended_card
    )
    equivalent = (
        build_retained_information_set_replay_coaching_decision_assessment_v1(
            _decision(equivalent_result, actual_card=equivalent_card)
        )
    )

    assert best.evidence_basis == "information_set_single_exact_world"
    assert best.assessment_status == "best_or_equivalent"
    assert equivalent.assessment_status == "best_or_equivalent"
    assert equivalent.aggregate_equivalent is True
    assert equivalent.factors == ("aggregate_equivalent_choice",)


def test_sampled_evidence_is_primary_and_receives_sampled_limitation() -> None:
    assessment = build_retained_information_set_replay_coaching_decision_assessment_v1(
        _decision(_information_result(coverage="sampled_compatible_worlds"))
    )

    assert assessment.evidence_basis == (
        "information_set_sampled_compatible_worlds"
    )
    assert "sampled_compatible_worlds" in assessment.limitations
    assert "no_equilibrium_or_global_optimality_claim" in assessment.limitations


@pytest.mark.parametrize("status", ["partial", "timeout"])
def test_incomplete_results_are_not_assessable_despite_diagnostic_baselines(
    status: str,
) -> None:
    result = _partial_or_timeout_result(status)
    decision = _decision(
        result,
        legal_cards=("CA", "S7"),
        actual_card="S7",
        immediate_recommended_card="CA",
    )
    assessment = (
        build_retained_information_set_replay_coaching_decision_assessment_v1(
            decision
        )
    )

    assert assessment.assessment_status == "not_assessable"
    assert assessment.evidence_basis == "none"
    assert assessment.impact_tier == "not_assessable"
    assert assessment.best_card is None
    assert assessment.factors == (
        "search_unavailable",
        "no_assessable_evidence",
    )


def test_unavailable_and_missing_candidate_coverage_have_no_fallback() -> None:
    request, complete = _base_request_and_result()
    unavailable = build_unavailable_information_set_search_result_v1(
        request=request,
        unavailable_reason="remaining_trick_limit_exceeded",
    )
    unavailable_assessment = (
        build_retained_information_set_replay_coaching_decision_assessment_v1(
            _decision(
                unavailable,
                legal_cards=("CA", "S7"),
                actual_card="S7",
                immediate_recommended_card="CA",
            )
        )
    )
    full_cards = tuple(candidate.card for candidate in complete.candidate_results)
    complete_result = _information_result()
    missing = replace(
        complete_result,
        candidate_results=complete_result.candidate_results[:-1],
    )
    missing_assessment = (
        build_retained_information_set_replay_coaching_decision_assessment_v1(
            _decision(
                missing,
                legal_cards=full_cards,
                actual_card=full_cards[-1],
            )
        )
    )

    assert unavailable_assessment.assessment_status == "not_assessable"
    assert missing_assessment.assessment_status == "not_assessable"
    assert unavailable_assessment.best_card is None
    assert missing_assessment.best_card is None


def test_forced_move_is_factual_without_complete_search() -> None:
    result = _partial_or_timeout_result("timeout")
    decision = _decision(
        result,
        legal_cards=("CA",),
        actual_card="CA",
        immediate_recommended_card="CA",
    )
    assessment = (
        build_retained_information_set_replay_coaching_decision_assessment_v1(
            decision
        )
    )

    assert assessment.assessment_status == "forced_move"
    assert assessment.evidence_basis == "none"
    assert assessment.impact_tier == "no_missed_impact"
    assert assessment.best_card == "CA"
    assert assessment.strictly_better_card_count == 0
    assert assessment.factors == ("forced_move", "search_unavailable")


def test_null_unavailable_assessment_never_uses_margin_or_immediate_fallback() -> None:
    source = _decision(
        _partial_or_timeout_result("timeout"),
        legal_cards=("CA", "S7"),
        actual_card="S7",
        immediate_recommended_card="CA",
    )
    public_result = dict(source.information_set_public_result or {})
    public_result["game_type"] = "null"
    pre_actual = build_information_set_search_comparison_pre_actual_analysis_v1(
        information_set_result=None,
        information_set_public_result=public_result,
        pimc_result=None,
        immediate_recommended_card="CA",
        same_selected_world_sequence=False,
    )
    comparison = attach_actual_card_to_information_set_search_comparison_v1(
        pre_actual,
        "S7",
    )
    decision = replace(
        source,
        contract="null",
        information_set_result=None,
        information_set_public_result=public_result,
        pimc_result=None,
        comparison=comparison,
    )
    assessment = build_retained_information_set_replay_coaching_decision_assessment_v1(
        decision
    )

    assert assessment.decision_time_evidence.game_type == "null"
    assert assessment.mean_local_side_card_point_margin_gap is None
    assert assessment.impact_tier == "not_assessable"
    assert "null_margin_not_applicable" in assessment.factors


def test_information_set_assessment_reuses_shared_key_ranking_and_serializes_safely() -> None:
    assessment = build_retained_information_set_replay_coaching_decision_assessment_v1(
        _decision(_information_result("contract_success"))
    )
    key = build_replay_coaching_key_decisions(
        (assessment,),
        {assessment.decision_time_evidence.decision_index: ()},
    )[0]
    serialized = build_serializable_information_set_replay_coaching_decision_assessment_v1(
        assessment
    )

    assert key.selection_reason == "contract_success_gap"
    assert key.primary_gap == assessment.contract_success_rate_gap
    assert "actual_card" not in serialized["decision_time_evidence"]
    safe_result = serialized["decision_time_evidence"][
        "information_set_pre_actual_analysis"
    ]["information_set_search_result"]
    assert "controlled_policy" not in safe_result
    assert "controlled_policy_decision_count" in safe_result
    with pytest.raises(FrozenInstanceError):
        assessment.impact_tier = "settlement_score"  # type: ignore[misc]
