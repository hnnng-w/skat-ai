from dataclasses import FrozenInstanceError

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
from skatmind.retrospective_search_comparison import (
    NO_COMPLETED_SEARCH_WORLDS,
    SEARCH_CARD_NOT_AVAILABLE,
    build_search_actual_card_comparison,
    build_search_vs_immediate_comparison,
    build_serializable_search_actual_card_comparison,
    build_serializable_search_vs_immediate_comparison,
)
from skatmind.terminal_utility import TERMINAL_UTILITY_VERSION


def _candidate(
    card: str,
    *,
    completed: int = 4,
    successes: int = 2,
    score: float = 20.0,
    margin: float | None = 8.0,
) -> AggregateSearchCandidateResult:
    return AggregateSearchCandidateResult(
        card=card,
        rank=1,
        is_recommended=False,
        completed_world_count=completed,
        local_contract_success_count=successes,
        local_contract_success_rate=(successes / completed if completed else None),
        mean_local_side_game_score=(score if completed else None),
        mean_local_side_card_point_margin=(margin if completed else None),
    )


def _result(
    candidates: tuple[AggregateSearchCandidateResult, ...],
    *,
    game_type: str = "grand",
    completed: int = 4,
    status: str = "complete",
    coverage: str = "sampled_compatible_worlds",
    recommend: bool = True,
) -> BoundedSearchResult:
    selected = 4 if status == "complete" else 5
    sampled = selected if coverage == "sampled_compatible_worlds" else 0
    ranked = rank_search_candidate_results(candidates, game_type, recommend=recommend)
    return BoundedSearchResult(
        schema_version=BOUNDED_SEARCH_SCHEMA_VERSION,
        analysis_method=BOUNDED_SEARCH_ANALYSIS_METHOD,
        search_method="compatible_world_minimax_v1",
        game_type=game_type,
        status=status,
        stop_reason="completed" if status == "complete" else "node_budget_exhausted",
        world_coverage=coverage,
        solution_claim=(
            "exact_per_selected_world" if status == "complete" else "node_limited_partial"
        ),
        terminal_utility_version=TERMINAL_UTILITY_VERSION,
        requested_budget=RequestedSearchBudget(
            max_remaining_tricks=4,
            max_depth_plies=12,
            max_nodes=10_000,
            max_selected_worlds=8,
            max_sampled_worlds=8,
            minimum_comparable_worlds=2,
        ),
        consumed_budget=ConsumedSearchBudget(
            depth_reached=8,
            nodes_expanded=500,
            selected_world_count=selected,
            completed_world_count=completed,
            sampled_world_count=sampled,
            unique_sampled_world_count=sampled,
            wall_clock_elapsed_ms=10,
        ),
        compatible_world_count=(selected if coverage == "all_compatible_worlds" else 20),
        candidate_results=ranked,
        recommended_card=ranked[0].card if recommend else None,
        fallback_used=False,
        fallback_method=None,
    )


def _immediate_report(*cards: str) -> list[dict[str, object]]:
    return [
        {
            "card": card,
            "win_rate": 0.5,
            "average_points_won": float(len(cards) - index),
            "average_points_lost": 0.0,
            "expected_point_swing": float(len(cards) - index),
            "is_recommended": index == 0,
        }
        for index, card in enumerate(cards)
    ]


def test_actual_card_comparison_reports_strict_recommendation_minus_actual_gaps() -> None:
    result = _result(
        (
            _candidate("CA", successes=4, score=40.0, margin=20.0),
            _candidate("S7", successes=3, score=30.0, margin=12.0),
            _candidate("D7", successes=2, score=10.0, margin=2.0),
        ),
        coverage="all_compatible_worlds",
    )

    comparison = build_search_actual_card_comparison(result, "D7")

    assert comparison.is_available
    assert comparison.search_recommended_card == "CA"
    assert comparison.actual_card_rank == 3
    assert comparison.recommended_card_rank == 1
    assert comparison.actual_card_is_best_aggregate is False
    assert comparison.actual_card_is_aggregate_equivalent_to_recommendation is False
    assert comparison.strictly_better_card_count == 2
    assert comparison.comparison_basis == "all_compatible_worlds"
    assert comparison.contract_success_rate_gap == 0.5
    assert comparison.mean_local_side_game_score_gap == 30.0
    assert comparison.mean_local_side_card_point_margin_gap == 18.0
    assert comparison.actual_card_metrics is not None
    with pytest.raises(FrozenInstanceError):
        comparison.actual_card_rank = 1  # type: ignore[misc]


def test_canonical_order_tie_is_aggregate_equivalent_and_best() -> None:
    result = _result(
        (
            _candidate("S7", successes=3, score=25.0, margin=9.0),
            _candidate("CA", successes=3, score=25.0, margin=9.0),
        )
    )

    comparison = build_search_actual_card_comparison(result, "S7")

    assert result.candidate_results[0].card == "CA"
    assert comparison.actual_card_rank == 2
    assert comparison.actual_card_is_best_aggregate is True
    assert comparison.actual_card_is_aggregate_equivalent_to_recommendation is True
    assert comparison.strictly_better_card_count == 0


def test_null_comparison_omits_margin_metrics_and_gap() -> None:
    result = _result(
        (
            _candidate("CA", successes=4, score=23.0, margin=None),
            _candidate("S7", successes=2, score=-46.0, margin=None),
        ),
        game_type="null",
    )

    comparison = build_search_actual_card_comparison(result, "S7")
    serialized = build_serializable_search_actual_card_comparison(comparison)

    assert comparison.mean_local_side_card_point_margin_gap is None
    assert serialized["actual_card_metrics"]["mean_local_side_card_point_margin"] is None
    assert serialized["recommended_card_metrics"][
        "mean_local_side_card_point_margin"
    ] is None


def test_zero_completed_worlds_make_both_comparisons_unavailable() -> None:
    result = _result(
        (
            _candidate("CA", completed=0, successes=0, margin=None),
            _candidate("S7", completed=0, successes=0, margin=None),
        ),
        completed=0,
        status="partial",
        recommend=False,
    )

    actual = build_search_actual_card_comparison(result, "CA")
    immediate = build_search_vs_immediate_comparison(
        result,
        "S7",
        _immediate_report("S7", "CA"),
        "grand",
        "declarer",
    )

    assert actual.unavailable_reason == NO_COMPLETED_SEARCH_WORLDS
    assert actual.search_recommended_card is None
    assert actual.actual_card_metrics is None
    assert actual.recommended_card_metrics is None
    assert actual.contract_success_rate_gap is None
    assert immediate.unavailable_reason == NO_COMPLETED_SEARCH_WORLDS
    assert immediate.search_card is None
    assert immediate.search_aggregate_relation == "not_available"
    assert immediate.search_contract_success_rate_advantage is None
    assert set(build_serializable_search_actual_card_comparison(actual)) == {
        "is_available",
        "unavailable_reason",
        "actual_card",
        "search_recommended_card",
        "actual_card_rank",
        "recommended_card_rank",
        "actual_card_is_best_aggregate",
        "actual_card_is_aggregate_equivalent_to_recommendation",
        "strictly_better_card_count",
        "completed_world_count",
        "comparison_basis",
        "actual_card_metrics",
        "recommended_card_metrics",
        "contract_success_rate_gap",
        "mean_local_side_game_score_gap",
        "mean_local_side_card_point_margin_gap",
    }


def test_completed_aggregate_without_recommendation_is_not_comparable() -> None:
    result = _result(
        (
            _candidate(
                "CA", completed=1, successes=1, score=40.0, margin=20.0
            ),
            _candidate(
                "S7", completed=1, successes=0, score=30.0, margin=12.0
            ),
        ),
        completed=1,
        status="partial",
        recommend=False,
    )

    actual = build_search_actual_card_comparison(result, "CA")
    immediate = build_search_vs_immediate_comparison(
        result,
        "S7",
        _immediate_report("S7", "CA"),
        "grand",
        "declarer",
    )

    assert actual.is_available is False
    assert actual.unavailable_reason == SEARCH_CARD_NOT_AVAILABLE
    assert actual.search_recommended_card is None
    assert immediate.is_available is False
    assert immediate.unavailable_reason == SEARCH_CARD_NOT_AVAILABLE
    assert immediate.search_card is None


def test_search_vs_immediate_aligns_cards_and_uses_both_rankings() -> None:
    result = _result(
        (
            _candidate("CA", successes=4, score=35.0, margin=18.0),
            _candidate("S7", successes=3, score=30.0, margin=12.0),
        )
    )

    comparison = build_search_vs_immediate_comparison(
        result,
        "S7",
        _immediate_report("S7", "CA"),
        "grand",
        "declarer",
    )
    serialized = build_serializable_search_vs_immediate_comparison(comparison)

    assert comparison.is_available
    assert comparison.search_card == "CA"
    assert comparison.immediate_card == "S7"
    assert comparison.same_recommended_card is False
    assert comparison.search_rank_of_immediate_card == 2
    assert comparison.immediate_rank_of_search_card == 2
    assert comparison.search_aggregate_relation == "search_better"
    assert comparison.search_contract_success_rate_advantage == 0.25
    assert comparison.search_mean_game_score_advantage == 5.0
    assert comparison.search_mean_card_point_margin_advantage == 6.0
    assert set(serialized) == {
        "is_available",
        "unavailable_reason",
        "search_card",
        "immediate_card",
        "same_recommended_card",
        "search_rank_of_immediate_card",
        "immediate_rank_of_search_card",
        "search_aggregate_relation",
        "search_contract_success_rate_advantage",
        "search_mean_game_score_advantage",
        "search_mean_card_point_margin_advantage",
    }


def test_search_vs_immediate_never_emits_search_worse() -> None:
    result = _result(
        (
            _candidate("CA", successes=4, score=35.0, margin=18.0),
            _candidate("S7", successes=3, score=30.0, margin=12.0),
        )
    )
    object.__setattr__(
        result.candidate_results[0],
        "local_contract_success_rate",
        0.5,
    )

    with pytest.raises(ValueError, match="rank-1 candidate is worse"):
        build_search_vs_immediate_comparison(
            result,
            "S7",
            _immediate_report("S7", "CA"),
            "grand",
            "declarer",
        )
