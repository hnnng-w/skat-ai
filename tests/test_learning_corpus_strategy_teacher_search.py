from dataclasses import replace

import pytest
from test_learning_corpus_strategy_teacher import (
    _changed_report,
    _source_bundle,
)

from skatmind.api.v1.contracts import ResultDocumentV1
from skatmind.application.execution import ApplicationWorkflowDependencies
from skatmind.application.position_workflow import PositionWorkflowDependencies
from skatmind.bounded_search_result import (
    BOUNDED_SEARCH_ANALYSIS_METHOD,
    BOUNDED_SEARCH_SCHEMA_VERSION,
    AggregateSearchCandidateResult,
    BoundedSearchResult,
    ConsumedSearchBudget,
    rank_search_candidate_results,
)
from skatmind.learning_corpus_strategy_teacher import (
    build_learning_corpus_strategy_teacher_report_source_v1,
)
from skatmind.learning_corpus_strategy_teacher_builder import (
    build_learning_corpus_strategy_teacher_evidence_collection_v1,
)
from skatmind.match_analysis_contracts import build_match_analysis_report_v1
from skatmind.match_decision_analysis import execute_match_decision_analysis_v1
from skatmind.rules import get_legal_cards
from skatmind.terminal_utility import TERMINAL_UTILITY_VERSION


@pytest.fixture(scope="module")
def search_unavailable_bundle():
    return _source_bundle(
        recommendation_method="bounded_search",
        search_random_seed=0,
        search_budget_profile="interactive_v1",
    )


def test_search_unavailable_preserves_exact_search_evidence(
    search_unavailable_bundle,
) -> None:
    _workspace, _snapshot, result, _report, source, store = (
        search_unavailable_bundle
    )
    collection = build_learning_corpus_strategy_teacher_evidence_collection_v1(
        store,
        (source,),
    )
    evidence = collection.evidences[0]
    document = result.result.to_dict()["document"]
    search = document["bounded_search_result"]
    assert evidence.status == "recommendation_unavailable"
    assert evidence.search_status == "unavailable"
    assert evidence.search_stop_reason == search["stop_reason"]
    assert evidence.world_coverage == search["world_coverage"]
    assert evidence.solution_claim == search["solution_claim"]
    assert evidence.requested_budget == search["requested_budget"]
    assert evidence.consumed_budget == search["consumed_budget"]
    assert evidence.search_candidate_results == tuple(search["candidate_results"])
    assert evidence.wall_clock_elapsed_ms == search["consumed_budget"][
        "wall_clock_elapsed_ms"
    ]
    assert evidence.immediate_candidate_results == ()
    assert evidence.bounded_search_post_game_review_summary == document[
        "bounded_search_post_game_review_summary"
    ]
    assert collection.bounded_search_requested_count == 1
    assert collection.search_attempted_count == 1
    assert collection.search_unavailable_count == 1


def test_complete_search_preserves_candidates_budgets_and_comparisons() -> None:
    _workspace, _snapshot, result, _report, source, store = _source_bundle(
        recommendation_method="bounded_search",
        decision_index=22,
        match_id="match-complete-search",
        search_random_seed=0,
        search_budget_profile="interactive_v1",
    )
    evidence = build_learning_corpus_strategy_teacher_evidence_collection_v1(
        store,
        (source,),
    ).evidences[0]
    document = result.result.to_dict()["document"]
    search = document["bounded_search_result"]
    assert evidence.status == "recommendation_available"
    assert evidence.search_status == "complete"
    assert evidence.search_candidate_results == tuple(search["candidate_results"])
    assert evidence.recommendation == document["recommendation"]
    assert evidence.bounded_search_post_game_review_summary == document[
        "bounded_search_post_game_review_summary"
    ]
    assert "worlds" not in evidence.to_dict()["bounded_search_result"]


def test_immediate_and_search_for_one_decision_remain_separate(
    search_unavailable_bundle,
) -> None:
    workspace, snapshot, _search_result, _report, search_source, store = (
        search_unavailable_bundle
    )
    immediate_result = execute_match_decision_analysis_v1(
        workspace,
        match_position=3,
        decision_index=1,
        options=replace(
            _search_result.options,
            recommendation_method="immediate_expected_value",
            search_random_seed=None,
            search_budget_profile="historical_review_v1",
        ),
    )
    immediate_source = build_learning_corpus_strategy_teacher_report_source_v1(
        match_snapshot_id=snapshot.match_snapshot_id,
        report=build_match_analysis_report_v1(immediate_result),
    )
    collection = build_learning_corpus_strategy_teacher_evidence_collection_v1(
        store,
        (search_source, immediate_source),
    )
    assert collection.source_report_count == collection.evidence_count == 2
    assert collection.distinct_decision_count == 1
    assert tuple(
        evidence.options.recommendation_method for evidence in collection.evidences
    ) == ("immediate_expected_value", "bounded_search")
    assert len(
        {evidence.strategy_teacher_evidence_id for evidence in collection.evidences}
    ) == 2


def test_auto_immediate_fallback_preserves_both_method_contexts() -> None:
    _workspace, _snapshot, result, _report, source, store = _source_bundle(
        recommendation_method="auto",
        match_id="match-auto-fallback",
        search_random_seed=0,
        search_budget_profile="interactive_v1",
    )
    evidence = build_learning_corpus_strategy_teacher_evidence_collection_v1(
        store,
        (source,),
    ).evidences[0]
    summary = result.result.to_dict()["document"]["recommendation_method_summary"]
    assert summary == {
        "requested_method": "auto",
        "effective_method": "immediate_expected_value",
        "search_attempted": True,
        "fallback_used": True,
        "fallback_method": "immediate_expected_value",
        "analysis_report_method": "immediate_expected_value",
    }
    assert evidence.recommendation_method_summary == summary
    assert evidence.search_status == "unavailable"
    assert evidence.immediate_candidate_results
    assert evidence.bounded_search_result is not None
    assert evidence.status == "recommendation_available"


def test_auto_search_success_preserves_effective_search() -> None:
    _workspace, _snapshot, result, _report, source, store = _source_bundle(
        recommendation_method="auto",
        decision_index=22,
        match_id="match-auto-search",
        search_random_seed=0,
        search_budget_profile="interactive_v1",
    )
    evidence = build_learning_corpus_strategy_teacher_evidence_collection_v1(
        store,
        (source,),
    ).evidences[0]
    summary = result.result.to_dict()["document"]["recommendation_method_summary"]
    assert summary["requested_method"] == "auto"
    assert summary["effective_method"] == "compatible_world_minimax_v1"
    assert summary["fallback_used"] is False
    assert evidence.search_status == "complete"
    assert evidence.immediate_candidate_results == ()
    assert evidence.status == "recommendation_available"


@pytest.mark.parametrize(
    ("status", "stop_reason", "solution_claim"),
    (
        ("partial", "node_budget_exhausted", "node_limited_partial"),
        (
            "partial",
            "depth_budget_exhausted",
            "depth_limited_per_selected_world",
        ),
        ("timeout", "wall_clock_timeout", "none"),
    ),
)
def test_partial_and_timeout_search_states_are_preserved(
    monkeypatch,
    status: str,
    stop_reason: str,
    solution_claim: str,
) -> None:
    def search(*, information_view, requested_budget, random_seed):
        assert random_seed == 5
        legal_cards = get_legal_cards(
            list(information_view.local_remaining_hand),
            [play.card for play in information_view.current_trick],
            information_view.game_type,
        )
        candidates = rank_search_candidate_results(
            tuple(
                    AggregateSearchCandidateResult(
                        card=card,
                        rank=1,
                        is_recommended=False,
                        completed_world_count=8,
                        local_contract_success_count=8,
                    local_contract_success_rate=1.0,
                    mean_local_side_game_score=24.0,
                    mean_local_side_card_point_margin=10.0,
                )
                for card in legal_cards
            ),
            information_view.game_type,
            recommend=True,
        )
        return BoundedSearchResult(
            schema_version=BOUNDED_SEARCH_SCHEMA_VERSION,
            analysis_method=BOUNDED_SEARCH_ANALYSIS_METHOD,
            search_method="compatible_world_minimax_v1",
            game_type=information_view.game_type,
            status=status,
            stop_reason=stop_reason,
            world_coverage="all_compatible_worlds",
            solution_claim=solution_claim,
            terminal_utility_version=TERMINAL_UTILITY_VERSION,
            requested_budget=requested_budget,
            consumed_budget=ConsumedSearchBudget(
                depth_reached=(
                    requested_budget.max_depth_plies
                    if stop_reason == "depth_budget_exhausted"
                    else 1
                ),
                nodes_expanded=(
                    requested_budget.max_nodes
                    if stop_reason == "node_budget_exhausted"
                    else 1
                ),
                selected_world_count=9,
                completed_world_count=8,
                sampled_world_count=0,
                unique_sampled_world_count=0,
                wall_clock_elapsed_ms=(
                    requested_budget.wall_clock_timeout_ms
                    if status == "timeout"
                    else 1
                ),
            ),
            compatible_world_count=9,
            candidate_results=candidates,
            recommended_card=candidates[0].card,
            fallback_used=False,
            fallback_method=None,
        )

    monkeypatch.setattr(
        "skatmind.recommendation_workflow.solve_compatible_world_minimax",
        search,
    )
    _workspace, _snapshot, _result, _report, source, store = _source_bundle(
        recommendation_method="bounded_search",
        decision_index=22,
        match_id=f"match-{status}-{stop_reason}",
        search_random_seed=5,
        search_budget_profile="interactive_v1",
    )
    evidence = build_learning_corpus_strategy_teacher_evidence_collection_v1(
        store,
        (source,),
    ).evidences[0]
    assert evidence.search_status == status
    assert evidence.search_stop_reason == stop_reason
    assert evidence.solution_claim == solution_claim
    assert evidence.search_candidate_results
    assert evidence.status == "recommendation_available"


def test_sampled_world_search_coverage_is_preserved(monkeypatch) -> None:
    def search(*, information_view, requested_budget, random_seed):
        assert random_seed == 7
        legal_cards = get_legal_cards(
            list(information_view.local_remaining_hand),
            [play.card for play in information_view.current_trick],
            information_view.game_type,
        )
        candidates = rank_search_candidate_results(
            tuple(
                AggregateSearchCandidateResult(
                    card=card,
                    rank=1,
                    is_recommended=False,
                    completed_world_count=2,
                    local_contract_success_count=2,
                    local_contract_success_rate=1.0,
                    mean_local_side_game_score=24.0,
                    mean_local_side_card_point_margin=10.0,
                )
                for card in legal_cards
            ),
            information_view.game_type,
            recommend=True,
        )
        return BoundedSearchResult(
            schema_version=BOUNDED_SEARCH_SCHEMA_VERSION,
            analysis_method=BOUNDED_SEARCH_ANALYSIS_METHOD,
            search_method="compatible_world_minimax_v1",
            game_type=information_view.game_type,
            status="complete",
            stop_reason="completed",
            world_coverage="sampled_compatible_worlds",
            solution_claim="exact_per_selected_world",
            terminal_utility_version=TERMINAL_UTILITY_VERSION,
            requested_budget=requested_budget,
            consumed_budget=ConsumedSearchBudget(1, 2, 2, 2, 2, 2, 1),
            compatible_world_count=3,
            candidate_results=candidates,
            recommended_card=candidates[0].card,
            fallback_used=False,
            fallback_method=None,
        )

    monkeypatch.setattr(
        "skatmind.recommendation_workflow.solve_compatible_world_minimax",
        search,
    )
    _workspace, _snapshot, _result, _report, source, store = _source_bundle(
        recommendation_method="bounded_search",
        decision_index=22,
        match_id="match-sampled-worlds",
        search_random_seed=7,
        search_budget_profile="interactive_v1",
    )
    evidence = build_learning_corpus_strategy_teacher_evidence_collection_v1(
        store,
        (source,),
    ).evidences[0]
    assert evidence.world_coverage == "sampled_compatible_worlds"
    assert evidence.bounded_search_result["compatible_world_count"] == 3
    assert evidence.consumed_budget["sampled_world_count"] == 2


def test_auto_no_recommendation_remains_valid_evidence() -> None:
    def no_recommendation(**_kwargs):
        return None, "No Immediate recommendation.", {}

    dependencies = ApplicationWorkflowDependencies(
        position=PositionWorkflowDependencies(
            immediate_recommender=no_recommendation,
        )
    )
    _workspace, _snapshot, result, _report, source, store = _source_bundle(
        recommendation_method="auto",
        match_id="match-auto-none",
        search_random_seed=0,
        search_budget_profile="interactive_v1",
        dependencies=dependencies,
    )
    evidence = build_learning_corpus_strategy_teacher_evidence_collection_v1(
        store,
        (source,),
    ).evidences[0]
    summary = result.result.to_dict()["document"]["recommendation_method_summary"]
    assert summary["effective_method"] == "none"
    assert summary["fallback_used"] is False
    assert evidence.status == "recommendation_unavailable"
    assert evidence.to_dict()["immediate_candidate_results"] == (
        result.result.to_dict()["document"]["analysis_report"]
    )


def test_wall_clock_only_change_keeps_semantic_fingerprint(
    search_unavailable_bundle,
) -> None:
    _workspace, snapshot, result, _report, source, store = (
        search_unavailable_bundle
    )
    changed_document = result.result.to_dict()["document"]
    consumed = changed_document["bounded_search_result"]["consumed_budget"]
    consumed["wall_clock_elapsed_ms"] += 1
    changed_report = _changed_report(result, result_document=changed_document)
    changed_source = build_learning_corpus_strategy_teacher_report_source_v1(
        match_snapshot_id=snapshot.match_snapshot_id,
        report=changed_report,
    )
    collection = build_learning_corpus_strategy_teacher_evidence_collection_v1(
        store,
        (source, changed_source),
    )
    first, second = collection.evidences
    assert first.source_report_fingerprint != second.source_report_fingerprint
    assert first.source_result_fingerprint != second.source_result_fingerprint
    assert first.teacher_semantic_fingerprint == second.teacher_semantic_fingerprint
    assert first.strategy_teacher_evidence_id != second.strategy_teacher_evidence_id
    assert first.wall_clock_elapsed_ms != second.wall_clock_elapsed_ms


def test_source_result_wrapper_remains_exact(search_unavailable_bundle) -> None:
    _workspace, snapshot, result, _report, _source, _store_value = (
        search_unavailable_bundle
    )
    document = result.result.to_dict()["document"]
    changed_result = ResultDocumentV1(
        workflow=result.result.workflow,
        document=document,
        warnings=("retained warning",),
    )
    changed_report = build_match_analysis_report_v1(
        replace(result, result=changed_result)
    )
    source = build_learning_corpus_strategy_teacher_report_source_v1(
        match_snapshot_id=snapshot.match_snapshot_id,
        report=changed_report,
    )
    assert source.source_result_fingerprint != (
        search_unavailable_bundle[4].source_result_fingerprint
    )
