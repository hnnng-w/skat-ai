from dataclasses import FrozenInstanceError

import pytest
from test_information_set_search_state_and_preparation import _find_view, _request

from skat_ai.bounded_search_result import (
    BOUNDED_SEARCH_ANALYSIS_METHOD,
    BOUNDED_SEARCH_SCHEMA_VERSION,
    AggregateSearchCandidateResult,
    BoundedSearchResult,
    ConsumedSearchBudget,
    RequestedSearchBudget,
    rank_search_candidate_results,
)
from skat_ai.historical_information_set_search_review import (
    HISTORICAL_INFORMATION_SET_SEARCH_REVIEW_METHOD,
    HISTORICAL_INFORMATION_SET_SEARCH_REVIEW_VERSION,
    INFORMATION_SET_SEARCH_HISTORICAL_POLICY,
    INFORMATION_SET_SEARCH_PROFILE_POLICY,
)
from skat_ai.information_set_search_comparison import (
    INFORMATION_SET_SEARCH_ACTUAL_CARD_POLICY,
    INFORMATION_SET_SEARCH_BASELINE_POLICY,
    INFORMATION_SET_SEARCH_COMPARISON_METHOD,
    INFORMATION_SET_SEARCH_COMPARISON_POLICY,
    INFORMATION_SET_SEARCH_COMPARISON_VERSION,
    INFORMATION_SET_SEARCH_PROVENANCE_POLICY,
    INFORMATION_SET_SEARCH_STRATEGY_FUSION_MITIGATION_SCOPE,
    attach_actual_card_to_information_set_search_comparison_v1,
    build_information_set_search_comparison_pre_actual_analysis_v1,
    build_serializable_information_set_search_comparison_v1,
)
from skat_ai.information_set_search_contracts import (
    build_unavailable_information_set_search_result_v1,
)
from skat_ai.information_set_search_evaluation import (
    INFORMATION_SET_SEARCH_EVALUATION_METHOD,
    INFORMATION_SET_SEARCH_EVALUATION_POLICY,
    INFORMATION_SET_SEARCH_EVALUATION_VERSION,
)
from skat_ai.information_set_search_executor import (
    execute_information_set_search_v1,
)
from skat_ai.information_set_search_preparation import (
    prepare_information_set_search_v1,
)
from skat_ai.information_set_search_public import (
    build_public_information_set_search_result_v1,
)
from skat_ai.terminal_utility import TERMINAL_UTILITY_VERSION


@pytest.fixture(scope="module")
def complete_information_result():
    view, _state = _find_view(
        actor="me",
        remaining_tricks=2,
        current_trick_size=0,
        public_players=("left", "right"),
    )
    preparation = prepare_information_set_search_v1(
        _request(view, max_selected_worlds=1, max_sampled_worlds=1)
    )
    result = execute_information_set_search_v1(preparation)
    assert result.status == "complete"
    assert len(result.candidate_results) >= 2
    return result, preparation


def _pimc_result(information_result, recommended_card: str) -> BoundedSearchResult:
    completed = information_result.consumed_budget.selected_world_count
    candidates = tuple(
        AggregateSearchCandidateResult(
            card=candidate.card,
            rank=1,
            is_recommended=False,
            completed_world_count=completed,
            local_contract_success_count=(
                completed if candidate.card == recommended_card else 0
            ),
            local_contract_success_rate=(
                1.0 if candidate.card == recommended_card else 0.0
            ),
            mean_local_side_game_score=(
                40.0 if candidate.card == recommended_card else 10.0
            ),
            mean_local_side_card_point_margin=(
                20.0 if candidate.card == recommended_card else 2.0
            ),
        )
        for candidate in information_result.candidate_results
    )
    ranked = rank_search_candidate_results(candidates, "grand", recommend=True)
    requested = RequestedSearchBudget(
        max_remaining_tricks=3,
        max_depth_plies=9,
        max_nodes=20_000,
        max_selected_worlds=1,
        max_sampled_worlds=1,
        minimum_comparable_worlds=1,
    )
    return BoundedSearchResult(
        schema_version=BOUNDED_SEARCH_SCHEMA_VERSION,
        analysis_method=BOUNDED_SEARCH_ANALYSIS_METHOD,
        search_method="compatible_world_minimax_v1",
        game_type="grand",
        status="complete",
        stop_reason="completed",
        world_coverage="all_compatible_worlds",
        solution_claim="exact_per_selected_world",
        terminal_utility_version=TERMINAL_UTILITY_VERSION,
        requested_budget=requested,
        consumed_budget=ConsumedSearchBudget(
            depth_reached=6,
            nodes_expanded=20,
            selected_world_count=completed,
            completed_world_count=completed,
            sampled_world_count=0,
            unique_sampled_world_count=0,
            wall_clock_elapsed_ms=1,
        ),
        compatible_world_count=completed,
        candidate_results=ranked,
        recommended_card=ranked[0].card,
        fallback_used=False,
        fallback_method=None,
    )


def _collect_keys(value) -> set[str]:
    if isinstance(value, dict):
        return set(value).union(*(_collect_keys(item) for item in value.values()))
    if isinstance(value, list):
        return set().union(*(_collect_keys(item) for item in value))
    return set()


def test_versions_methods_and_issue_policies_are_exact() -> None:
    assert (
        INFORMATION_SET_SEARCH_COMPARISON_VERSION,
        HISTORICAL_INFORMATION_SET_SEARCH_REVIEW_VERSION,
        INFORMATION_SET_SEARCH_EVALUATION_VERSION,
    ) == (1, 1, 1)
    assert not any(
        isinstance(value, bool)
        for value in (
            INFORMATION_SET_SEARCH_COMPARISON_VERSION,
            HISTORICAL_INFORMATION_SET_SEARCH_REVIEW_VERSION,
            INFORMATION_SET_SEARCH_EVALUATION_VERSION,
        )
    )
    assert INFORMATION_SET_SEARCH_COMPARISON_METHOD == (
        "information_set_vs_same_selection_pimc_and_immediate_v1"
    )
    assert HISTORICAL_INFORMATION_SET_SEARCH_REVIEW_METHOD == (
        "information_set_search_with_same_selection_pimc_and_immediate_v1"
    )
    assert INFORMATION_SET_SEARCH_EVALUATION_METHOD == (
        "information_set_search_vs_same_selection_pimc_and_immediate_v1"
    )
    assert (
        INFORMATION_SET_SEARCH_BASELINE_POLICY,
        INFORMATION_SET_SEARCH_ACTUAL_CARD_POLICY,
        INFORMATION_SET_SEARCH_COMPARISON_POLICY,
        INFORMATION_SET_SEARCH_HISTORICAL_POLICY,
        INFORMATION_SET_SEARCH_EVALUATION_POLICY,
        INFORMATION_SET_SEARCH_PROFILE_POLICY,
        INFORMATION_SET_SEARCH_PROVENANCE_POLICY,
    ) == (
        "same_selected_world_pimc_plus_independent_immediate",
        "attach_actual_card_only_after_decision_time_analysis",
        "descriptive_method_comparison_without_accuracy_or_truth_claim",
        "one_pre_actual_execution_per_observed_decision",
        "deterministic_dataset_prefix_without_training",
        "existing_profile_identifier_to_information_set_budget",
        "retained_stage_values_without_execution_rerun",
    )


def test_agreement_and_actual_attachment_are_separate_and_immutable(
    complete_information_result,
) -> None:
    information_result, _preparation = complete_information_result
    card = information_result.recommended_card
    assert card is not None
    pimc = _pimc_result(information_result, card)
    pre_actual = build_information_set_search_comparison_pre_actual_analysis_v1(
        information_set_result=information_result,
        pimc_result=pimc,
        immediate_recommended_card=card,
        same_selected_world_sequence=True,
    )

    assert not hasattr(pre_actual, "actual_card")
    comparison = attach_actual_card_to_information_set_search_comparison_v1(
        pre_actual, card
    )

    assert comparison.comparison_status == "available"
    assert comparison.information_set_pimc_same_card is True
    assert comparison.information_set_immediate_same_card is True
    assert comparison.pimc_immediate_same_card is True
    assert comparison.information_set_actual_same_card is True
    assert comparison.pimc_actual_same_card is True
    assert comparison.immediate_actual_same_card is True
    assert comparison.information_set_rank_of_pimc_card == 1
    assert comparison.pimc_rank_of_information_set_card == 1
    assert comparison.information_set_rank_of_actual_card == 1
    assert comparison.pimc_rank_of_actual_card == 1
    assert comparison.strategy_fusion_mitigation_scope == (
        INFORMATION_SET_SEARCH_STRATEGY_FUSION_MITIGATION_SCOPE
    )
    with pytest.raises(FrozenInstanceError):
        comparison.actual_card = "CA"  # type: ignore[misc]


def test_disagreement_uses_retained_ranks_and_same_denominator_deltas(
    complete_information_result,
) -> None:
    information_result, _preparation = complete_information_result
    information_card = information_result.recommended_card
    assert information_card is not None
    pimc_card = next(
        candidate.card
        for candidate in information_result.candidate_results
        if candidate.card != information_card
    )
    pimc = _pimc_result(information_result, pimc_card)
    pre_actual = build_information_set_search_comparison_pre_actual_analysis_v1(
        information_set_result=information_result,
        pimc_result=pimc,
        immediate_recommended_card=pimc_card,
        same_selected_world_sequence=True,
    )

    comparison = attach_actual_card_to_information_set_search_comparison_v1(
        pre_actual, pimc_card
    )

    assert comparison.information_set_pimc_same_card is False
    assert comparison.information_set_immediate_same_card is False
    assert comparison.pimc_immediate_same_card is True
    assert comparison.information_set_actual_same_card is False
    assert comparison.pimc_actual_same_card is True
    assert comparison.immediate_actual_same_card is True
    assert comparison.information_set_rank_of_pimc_card == next(
        candidate.rank
        for candidate in information_result.candidate_results
        if candidate.card == pimc_card
    )
    assert comparison.pimc_rank_of_information_set_card == next(
        candidate.rank
        for candidate in pimc.candidate_results
        if candidate.card == information_card
    )
    assert comparison.information_set_rank_of_actual_card == (
        comparison.information_set_rank_of_pimc_card
    )
    assert comparison.pimc_rank_of_actual_card == 1
    assert (
        comparison.information_set_minus_pimc_at_information_set_card
        is not None
    )
    assert comparison.information_set_minus_pimc_at_pimc_card is not None

    serialized = build_serializable_information_set_search_comparison_v1(
        comparison
    )
    keys = _collect_keys(serialized)
    assert not any("accuracy" in key or "truth" in key for key in keys)
    assert serialized["information_set_minus_pimc_at_pimc_card"][
        "completed_world_count"
    ] == comparison.selected_world_count


def test_missing_and_incomplete_methods_are_explicitly_unavailable(
    complete_information_result,
) -> None:
    information_result, preparation = complete_information_result
    unavailable_information = build_unavailable_information_set_search_result_v1(
        request=preparation.request,
        unavailable_reason="remaining_trick_limit_exceeded",
    )
    incomplete = build_information_set_search_comparison_pre_actual_analysis_v1(
        information_set_result=unavailable_information,
        pimc_result=None,
        immediate_recommended_card=None,
        same_selected_world_sequence=False,
    )
    incomplete_comparison = (
        attach_actual_card_to_information_set_search_comparison_v1(
            incomplete, information_result.recommended_card
        )
    )
    missing_pimc = build_information_set_search_comparison_pre_actual_analysis_v1(
        information_set_result=information_result,
        pimc_result=None,
        immediate_recommended_card=information_result.recommended_card,
        same_selected_world_sequence=False,
    )
    missing_comparison = attach_actual_card_to_information_set_search_comparison_v1(
        missing_pimc, information_result.recommended_card
    )

    assert incomplete_comparison.comparison_status == "unavailable"
    assert incomplete_comparison.unavailable_reason == (
        "information_set_result_not_complete"
    )
    assert incomplete_comparison.information_set_status == "unavailable"
    assert incomplete_comparison.pimc_status == "not_available"
    assert incomplete_comparison.information_set_pimc_same_card is None
    assert missing_comparison.unavailable_reason == "pimc_result_not_available"
    assert missing_comparison.pimc_recommended_card is None


def test_safe_result_serialization_omits_private_policy_and_is_fresh(
    complete_information_result,
) -> None:
    information_result, _preparation = complete_information_result

    first = build_public_information_set_search_result_v1(information_result)
    second = build_public_information_set_search_result_v1(information_result)

    assert first == second
    assert first is not second
    assert "controlled_policy" not in first
    assert "controlled_policy_decision_count" in first
    keys = _collect_keys(first)
    assert "information_set" not in keys
    assert "own_hand" not in keys
    assert "exact_state" not in keys
    assert "selected_world" not in keys
