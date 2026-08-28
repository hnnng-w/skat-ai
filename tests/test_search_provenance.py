from dataclasses import replace

import pytest

from skatmind.bounded_search_result import (
    BOUNDED_SEARCH_ANALYSIS_METHOD,
    BOUNDED_SEARCH_SCHEMA_VERSION,
    AggregateSearchCandidateResult,
    BoundedSearchResult,
    ConsumedSearchBudget,
    RequestedSearchBudget,
    rank_search_candidate_results,
)
from skatmind.field_provenance_coverage import validate_field_provenance_coverage
from skatmind.search_provenance import build_bounded_search_provenance_ledger
from skatmind.terminal_utility import TERMINAL_UTILITY_VERSION


def _budget(*, timeout: int | None = 100) -> RequestedSearchBudget:
    return RequestedSearchBudget(
        max_remaining_tricks=3,
        max_depth_plies=9,
        max_nodes=1000,
        max_selected_worlds=5,
        max_sampled_worlds=5,
        minimum_comparable_worlds=2,
        wall_clock_timeout_ms=timeout,
    )


def _candidates(completed: int, *, recommend: bool) -> tuple[AggregateSearchCandidateResult, ...]:
    candidates = tuple(
        AggregateSearchCandidateResult(
            card=card,
            rank=1,
            is_recommended=False,
            completed_world_count=completed,
            local_contract_success_count=(completed if card == "CA" else 0),
            local_contract_success_rate=(
                (1.0 if card == "CA" else 0.0) if completed else None
            ),
            mean_local_side_game_score=(24.0 if card == "CA" else 0.0) if completed else None,
            mean_local_side_card_point_margin=(10.0 if completed else None),
        )
        for card in ("CA", "D7")
    )
    return rank_search_candidate_results(candidates, "grand", recommend=recommend)


def _result(
    *,
    status: str = "complete",
    stop_reason: str = "completed",
    coverage: str = "sampled_compatible_worlds",
    completed: int = 3,
    selected: int = 3,
    recommend: bool = True,
) -> BoundedSearchResult:
    solution_claim = {
        "completed": "exact_per_selected_world",
        "node_budget_exhausted": "node_limited_partial",
        "wall_clock_timeout": "none",
    }[stop_reason]
    sampled = selected if coverage == "sampled_compatible_worlds" else 0
    return BoundedSearchResult(
        schema_version=BOUNDED_SEARCH_SCHEMA_VERSION,
        analysis_method=BOUNDED_SEARCH_ANALYSIS_METHOD,
        search_method="compatible_world_minimax_v1",
        game_type="grand",
        status=status,
        stop_reason=stop_reason,
        world_coverage=coverage,
        solution_claim=solution_claim,
        terminal_utility_version=TERMINAL_UTILITY_VERSION,
        requested_budget=_budget(),
        consumed_budget=ConsumedSearchBudget(
            depth_reached=3,
            nodes_expanded=20,
            selected_world_count=selected,
            completed_world_count=completed,
            sampled_world_count=sampled,
            unique_sampled_world_count=sampled,
            wall_clock_elapsed_ms=1,
        ),
        compatible_world_count=(100 if coverage == "sampled_compatible_worlds" else selected),
        candidate_results=_candidates(completed, recommend=recommend),
        recommended_card="CA" if recommend else None,
        fallback_used=False,
        fallback_method=None,
    )


def _unavailable() -> BoundedSearchResult:
    return BoundedSearchResult(
        schema_version=BOUNDED_SEARCH_SCHEMA_VERSION,
        analysis_method=BOUNDED_SEARCH_ANALYSIS_METHOD,
        search_method="compatible_world_minimax_v1",
        game_type="grand",
        status="unavailable",
        stop_reason="remaining_trick_limit_exceeded",
        world_coverage="none",
        solution_claim="none",
        terminal_utility_version=TERMINAL_UTILITY_VERSION,
        requested_budget=_budget(),
        consumed_budget=ConsumedSearchBudget(0, 0, 0, 0, 0, 0, 0),
        compatible_world_count=None,
        candidate_results=(),
        recommended_card=None,
        fallback_used=False,
        fallback_method=None,
    )


@pytest.mark.parametrize(
    "result",
    [
        _result(),
        _result(coverage="all_compatible_worlds"),
        _result(
            status="partial",
            stop_reason="node_budget_exhausted",
            completed=2,
            selected=3,
        ),
        _result(
            status="timeout",
            stop_reason="wall_clock_timeout",
            completed=2,
            selected=3,
        ),
        _unavailable(),
    ],
)
def test_search_provenance_is_complete_for_every_status(result: BoundedSearchResult) -> None:
    ledger = build_bounded_search_provenance_ledger(result)
    from skatmind.bounded_search_result import build_serializable_bounded_search_result

    coverage = validate_field_provenance_coverage(
        build_serializable_bounded_search_result(result),
        ledger,
    )
    assert ledger.status == "complete"
    assert coverage.provenance_complete is True


def test_search_aggregate_derivation_matches_world_coverage() -> None:
    sampled = build_bounded_search_provenance_ledger(_result())
    exact = build_bounded_search_provenance_ledger(
        _result(coverage="all_compatible_worlds")
    )

    sampled_metric = next(
        entry
        for entry in sampled.entries
        if entry.field_path == "/candidate_results/0/local_contract_success_rate"
    )
    exact_metric = next(
        entry
        for entry in exact.entries
        if entry.field_path == "/candidate_results/0/local_contract_success_rate"
    )
    recommendation = next(
        entry for entry in sampled.entries if entry.field_path == "/recommended_card"
    )
    assert (sampled_metric.origin, sampled_metric.derivation) == (
        "compatible_world_aggregate",
        "sampled_aggregate",
    )
    assert (exact_metric.origin, exact_metric.derivation) == (
        "compatible_world_aggregate",
        "exact_aggregate",
    )
    assert recommendation.origin == "search_derived"


def test_candidate_rank_dependencies_cover_all_tie_break_inputs() -> None:
    ledger = build_bounded_search_provenance_ledger(_result())
    rank = next(
        entry
        for entry in ledger.entries
        if entry.field_path == "/candidate_results/0/rank"
    )

    assert "/game_type" in rank.dependency_paths
    for index in range(2):
        for field_name in (
            "card",
            "local_contract_success_rate",
            "mean_local_side_game_score",
            "mean_local_side_card_point_margin",
        ):
            assert f"/candidate_results/{index}/{field_name}" in rank.dependency_paths


def test_zero_coverage_and_unavailable_do_not_claim_aggregate_provenance() -> None:
    zero = _result(
        status="partial",
        stop_reason="node_budget_exhausted",
        completed=0,
        selected=3,
        recommend=False,
    )
    ledger = build_bounded_search_provenance_ledger(zero)
    unavailable = build_bounded_search_provenance_ledger(_unavailable())

    assert all(
        entry.origin != "compatible_world_aggregate"
        for entry in ledger.entries
        if entry.field_path.startswith("/candidate_results/")
    )
    assert {entry.origin for entry in unavailable.entries} <= {
        "search_derived",
        "validated_copy",
    }


def test_search_provenance_contains_no_private_world_or_seed_identity() -> None:
    ledger = build_bounded_search_provenance_ledger(_result())
    serialized = repr(ledger)
    for forbidden in (
        "world_id",
        "left_hand",
        "right_hand",
        "hypothetical_skat",
        "exact_state",
        "child_seed",
        "principal_variation",
        "transposition",
    ):
        assert forbidden not in serialized

    changed_elapsed = replace(
        _result(),
        consumed_budget=replace(_result().consumed_budget, wall_clock_elapsed_ms=99),
    )
    assert build_bounded_search_provenance_ledger(changed_elapsed) == ledger


def test_search_provenance_retains_actual_simulated_decision_index() -> None:
    from skatmind.search_provenance import build_bounded_search_provenance_entries

    entries = build_bounded_search_provenance_entries(
        _result(),
        decision_index=3,
    )
    assert {entry.available_from_decision_index for entry in entries} == {3}
