import pytest
from test_match_decision_analysis import _complete_workspace

from skat_ai.application.execution import (
    execute_application_invocation as real_execute_application_invocation,
)
from skat_ai.match_analysis_contracts import MatchDecisionAnalysisOptionsV1
from skat_ai.match_decision_analysis import (
    build_match_decision_position_request_v1,
    execute_match_decision_analysis_v1,
)
from skat_ai.match_information_set_search import (
    MATCH_INFORMATION_SET_SEARCH_BROWSER_POLICY,
    MATCH_INFORMATION_SET_SEARCH_COMPARISON_POLICY,
    MATCH_INFORMATION_SET_SEARCH_EXECUTION_POLICY,
    MATCH_INFORMATION_SET_SEARCH_INTEGRATION_VERSION,
    MATCH_INFORMATION_SET_SEARCH_PROFILE_POLICY,
    MATCH_INFORMATION_SET_SEARCH_REPORT_POLICY,
    MATCH_INFORMATION_SET_SEARCH_SETTINGS_POLICY,
    MATCH_INFORMATION_SET_SEARCH_SOURCE_POLICY,
    build_match_information_set_search_report_view_v1,
)


def _options(profile: str = "interactive_v1") -> MatchDecisionAnalysisOptionsV1:
    return MatchDecisionAnalysisOptionsV1(
        recommendation_method="information_set_search",
        immediate_sample_count=1,
        immediate_random_seed=3,
        search_random_seed=7,
        search_budget_profile=profile,
    )


def test_match_information_set_search_contract_constants_are_exact() -> None:
    assert MATCH_INFORMATION_SET_SEARCH_INTEGRATION_VERSION == 1
    assert MATCH_INFORMATION_SET_SEARCH_SOURCE_POLICY == (
        "prepared_match_decision_through_existing_position_application"
    )
    assert MATCH_INFORMATION_SET_SEARCH_SETTINGS_POLICY == (
        "existing_match_profile_to_information_set_budget"
    )
    assert MATCH_INFORMATION_SET_SEARCH_EXECUTION_POLICY == (
        "strict_information_set_search_once_without_fallback"
    )
    assert MATCH_INFORMATION_SET_SEARCH_COMPARISON_POLICY == (
        "same_selection_pimc_plus_independent_immediate_before_actual_card"
    )
    assert MATCH_INFORMATION_SET_SEARCH_PROFILE_POLICY == (
        "existing_effective_profile_policies_without_search_weighting"
    )
    assert MATCH_INFORMATION_SET_SEARCH_REPORT_POLICY == (
        "exact_revision_scoped_decision_report_with_safe_aggregate_result"
    )
    assert MATCH_INFORMATION_SET_SEARCH_BROWSER_POLICY == (
        "explicit_user_execution_and_safe_diagnostics_only"
    )


@pytest.mark.parametrize(
    ("profile", "expected"),
    (
        (
            "interactive_v1",
            {
                "random_seed": 7,
                "max_remaining_tricks": 3,
                "max_depth_plies": 9,
                "max_state_nodes": 500_000,
                "max_information_sets": 500_000,
                "max_selected_worlds": 64,
                "max_sampled_worlds": 32,
                "minimum_comparable_worlds": 8,
                "wall_clock_timeout_ms": 1_000,
            },
        ),
        (
            "historical_review_v1",
            {
                "random_seed": 7,
                "max_remaining_tricks": 3,
                "max_depth_plies": 9,
                "max_state_nodes": 2_000_000,
                "max_information_sets": 2_000_000,
                "max_selected_worlds": 128,
                "max_sampled_worlds": 64,
                "minimum_comparable_worlds": 16,
                "wall_clock_timeout_ms": 5_000,
            },
        ),
    ),
)
def test_match_request_maps_existing_profiles_to_information_set_settings(
    profile: str,
    expected: dict[str, int],
) -> None:
    prepared = build_match_decision_position_request_v1(
        _complete_workspace(),
        match_position=3,
        decision_index=30,
        options=_options(profile),
    )
    root = prepared.request.to_dict()["document"]
    assert root["recommendation_method"] == "information_set_search"
    assert root["information_set_search_settings"] == expected
    assert "bounded_search_settings" not in root
    assert root["actual_card_played"] is not None
    assert "commentaries" not in root
    assert "response_links" not in root


def test_match_information_set_search_executes_application_once(monkeypatch) -> None:
    import skat_ai.match_decision_analysis as analysis_module

    calls = 0
    validations = 0

    def counted(invocation, **kwargs):
        nonlocal calls
        calls += 1
        return real_execute_application_invocation(invocation, **kwargs)

    def counted_validation(document):
        nonlocal validations
        validations += 1
        from skat_ai.api.v1.schema_validation import validate_output_document

        validate_output_document(document)

    monkeypatch.setattr(analysis_module, "execute_application_invocation", counted)
    monkeypatch.setattr(analysis_module, "validate_output_document", counted_validation)
    result = execute_match_decision_analysis_v1(
        _complete_workspace(),
        match_position=3,
        decision_index=30,
        options=_options(),
    )

    assert calls == validations == 1
    assert result.status == "executed"
    document = result.result.to_dict()["document"]
    search = document["information_set_search_result"]
    comparison = document["information_set_search_comparison"]
    assert search["status"] == "complete"
    assert document["bounded_search_result"] is None
    assert document["recommendation_method_summary"] == {
        "requested_method": "information_set_search",
        "effective_method": "bounded_information_set_policy_search_v1",
        "search_attempted": True,
        "fallback_used": False,
        "fallback_method": None,
        "analysis_report_method": "none",
    }
    assert comparison["actual_card"] == result.request.document["actual_card_played"]

    view = build_match_information_set_search_report_view_v1(document)
    assert view == {
        "status": search["status"],
        "stop_reason": search["stop_reason"],
        "world_coverage": search["world_coverage"],
        "policy_claim": search["policy_claim"],
        "policy_consistency": search["policy_consistency"],
        "compatible_world_count": search["compatible_world_count"],
        "selected_world_count": search["consumed_budget"]["selected_world_count"],
        "completed_world_count": search["consumed_budget"]["completed_world_count"],
        "information_sets_evaluated": search["consumed_budget"]["information_sets_evaluated"],
        "controlled_policy_decision_count": search["controlled_policy_decision_count"],
        "fixed_policy_decision_count": search["consumed_budget"]["fixed_policy_decisions"],
        "information_set_recommended_card": comparison["information_set_recommended_card"],
        "pimc_recommended_card": comparison["pimc_recommended_card"],
        "immediate_recommended_card": comparison["immediate_recommended_card"],
        "actual_card": comparison["actual_card"],
        "information_set_pimc_same_card": comparison["information_set_pimc_same_card"],
        "information_set_immediate_same_card": comparison["information_set_immediate_same_card"],
        "information_set_actual_same_card": comparison["information_set_actual_same_card"],
    }
    assert not {
        "controlled_policy",
        "observations",
        "worlds",
        "exact_states",
        "candidate_results",
        "fixed_policy_settings",
        "wall_clock_elapsed_ms",
    } & set(view)


def test_match_information_set_unavailability_remains_executed_without_fallback() -> None:
    result = execute_match_decision_analysis_v1(
        _complete_workspace(),
        match_position=3,
        decision_index=1,
        options=_options(),
    )
    assert result.status == "executed"
    document = result.result.to_dict()["document"]
    assert document["information_set_search_result"]["status"] == "unavailable"
    assert document["information_set_search_comparison"]["comparison_status"] == "unavailable"
    assert document["recommendation_method_summary"]["fallback_used"] is False
    assert document["recommendation"]["card"] is None
