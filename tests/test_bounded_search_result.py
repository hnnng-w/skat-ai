from dataclasses import FrozenInstanceError, replace

import pytest

from skat_ai.bounded_search_result import (
    BOUNDED_SEARCH_ANALYSIS_METHOD,
    BOUNDED_SEARCH_SCHEMA_VERSION,
    AggregateSearchCandidateResult,
    BoundedSearchResult,
    ConsumedSearchBudget,
    RequestedSearchBudget,
    build_serializable_bounded_search_result,
    rank_search_candidate_results,
)
from skat_ai.terminal_utility import TERMINAL_UTILITY_VERSION


def _requested(**overrides) -> RequestedSearchBudget:
    values = {
        "max_remaining_tricks": 3,
        "max_depth_plies": 9,
        "max_nodes": 1000,
        "max_selected_worlds": 5,
        "max_sampled_worlds": 5,
        "minimum_comparable_worlds": 2,
        "wall_clock_timeout_ms": 100,
    }
    values.update(overrides)
    return RequestedSearchBudget(**values)


def _consumed(**overrides) -> ConsumedSearchBudget:
    values = {
        "depth_reached": 6,
        "nodes_expanded": 100,
        "selected_world_count": 3,
        "completed_world_count": 3,
        "sampled_world_count": 3,
        "unique_sampled_world_count": 3,
        "wall_clock_elapsed_ms": 12,
    }
    values.update(overrides)
    return ConsumedSearchBudget(**values)


def _candidate(
    card: str,
    *,
    rank: int = 1,
    recommended: bool = False,
    completed: int = 3,
    successes: int = 2,
    score: float = 24.0,
    margin: float | None = 10.0,
) -> AggregateSearchCandidateResult:
    return AggregateSearchCandidateResult(
        card=card,
        rank=rank,
        is_recommended=recommended,
        completed_world_count=completed,
        local_contract_success_count=successes,
        local_contract_success_rate=(successes / completed if completed else None),
        mean_local_side_game_score=(score if completed else None),
        mean_local_side_card_point_margin=(margin if completed else None),
    )


def _ranked_candidates(
    *,
    game_type: str = "grand",
    completed: int = 3,
    recommend: bool = True,
):
    margin = None if game_type == "null" else 10.0
    return rank_search_candidate_results(
        (
            _candidate(
                "D7",
                completed=completed,
                successes=min(2, completed),
                score=20.0,
                margin=margin,
            ),
            _candidate(
                "CA",
                completed=completed,
                successes=min(2, completed),
                score=24.0,
                margin=margin,
            ),
        ),
        game_type,
        recommend=recommend,
    )


def _result(**overrides) -> BoundedSearchResult:
    values = {
        "schema_version": BOUNDED_SEARCH_SCHEMA_VERSION,
        "analysis_method": BOUNDED_SEARCH_ANALYSIS_METHOD,
        "search_method": "compatible_world_minimax_v1",
        "game_type": "grand",
        "status": "complete",
        "stop_reason": "completed",
        "world_coverage": "sampled_compatible_worlds",
        "solution_claim": "exact_per_selected_world",
        "terminal_utility_version": TERMINAL_UTILITY_VERSION,
        "requested_budget": _requested(),
        "consumed_budget": _consumed(),
        "compatible_world_count": 100,
        "candidate_results": _ranked_candidates(),
        "recommended_card": "CA",
        "fallback_used": False,
        "fallback_method": None,
    }
    values.update(overrides)
    return BoundedSearchResult(**values)


def test_requested_budget_is_frozen_and_validates_cross_field_limits() -> None:
    budget = _requested()

    with pytest.raises(FrozenInstanceError):
        budget.max_nodes = 2  # type: ignore[misc]
    with pytest.raises(ValueError, match="max_sampled_worlds"):
        _requested(max_selected_worlds=2, max_sampled_worlds=3)
    with pytest.raises(ValueError, match="minimum_comparable_worlds"):
        _requested(
            max_selected_worlds=2,
            max_sampled_worlds=2,
            minimum_comparable_worlds=3,
        )
    with pytest.raises(ValueError, match="wall_clock_timeout_ms"):
        _requested(wall_clock_timeout_ms=0)
    with pytest.raises(ValueError, match="max_nodes"):
        _requested(max_nodes=True)


@pytest.mark.parametrize(
    "overrides",
    [
        {"depth_reached": -1},
        {"completed_world_count": 4},
        {"sampled_world_count": 4},
        {"sampled_world_count": 2, "unique_sampled_world_count": 3},
        {"sampled_world_count": 1, "unique_sampled_world_count": 0},
    ],
)
def test_consumed_budget_validates_non_negative_counts_and_relationships(
    overrides: dict,
) -> None:
    with pytest.raises(ValueError):
        _consumed(**overrides)


def test_candidate_zero_coverage_requires_absent_aggregates() -> None:
    zero = _candidate("CA", completed=0, successes=0, margin=None)

    assert zero.local_contract_success_rate is None
    with pytest.raises(ValueError, match="must be absent"):
        replace(zero, mean_local_side_game_score=0.0)
    with pytest.raises(ValueError, match="cannot exceed"):
        _candidate("CA", completed=1, successes=2)
    with pytest.raises(ValueError, match="must match"):
        replace(_candidate("CA"), local_contract_success_rate=0.5)


def test_candidate_ties_use_canonical_root_card_order() -> None:
    tied = (
        _candidate("D7", score=24.0),
        _candidate("CA", score=24.0),
        _candidate("S7", score=24.0),
    )

    ranked = rank_search_candidate_results(tied, "grand", recommend=True)

    assert [candidate.card for candidate in ranked] == ["CA", "S7", "D7"]
    assert [candidate.rank for candidate in ranked] == [1, 2, 3]
    assert [candidate.is_recommended for candidate in ranked] == [True, False, False]


def test_complete_sampled_exact_selected_worlds_do_not_claim_all_world_exactness() -> None:
    result = _result()

    assert result.status == "complete"
    assert result.world_coverage == "sampled_compatible_worlds"
    assert result.solution_claim == "exact_per_selected_world"
    assert result.consumed_budget.completed_world_count == 3
    assert result.compatible_world_count == 100
    assert result.world_coverage != "all_compatible_worlds"


def test_sampled_coverage_reconciles_draw_and_unique_counts() -> None:
    with pytest.raises(ValueError, match="one sampled draw"):
        _result(
            consumed_budget=_consumed(
                sampled_world_count=2,
                unique_sampled_world_count=2,
            )
        )
    with pytest.raises(ValueError, match="cannot exceed compatible worlds"):
        _result(
            compatible_world_count=2,
            consumed_budget=_consumed(),
        )


@pytest.mark.parametrize(
    ("search_method", "coverage", "compatible_count", "consumed"),
    [
        (
            "perfect_information_minimax_v1",
            "single_exact_world",
            1,
            _consumed(
                selected_world_count=1,
                completed_world_count=1,
                sampled_world_count=0,
                unique_sampled_world_count=0,
            ),
        ),
        (
            "compatible_world_minimax_v1",
            "all_compatible_worlds",
            3,
            _consumed(sampled_world_count=0, unique_sampled_world_count=0),
        ),
    ],
)
def test_complete_exact_coverage_modes_are_distinct(
    search_method: str,
    coverage: str,
    compatible_count: int,
    consumed: ConsumedSearchBudget,
) -> None:
    completed = consumed.completed_world_count
    result = _result(
        search_method=search_method,
        world_coverage=coverage,
        compatible_world_count=compatible_count,
        consumed_budget=consumed,
        candidate_results=_ranked_candidates(completed=completed),
    )

    assert result.world_coverage == coverage


def test_available_search_methods_require_their_own_coverage_modes() -> None:
    with pytest.raises(ValueError, match="Perfect-information search"):
        _result(search_method="perfect_information_minimax_v1")

    exact_consumed = _consumed(
        selected_world_count=1,
        completed_world_count=1,
        sampled_world_count=0,
        unique_sampled_world_count=0,
    )
    with pytest.raises(ValueError, match="Compatible-world search"):
        _result(
            world_coverage="single_exact_world",
            compatible_world_count=1,
            consumed_budget=exact_consumed,
            candidate_results=_ranked_candidates(completed=1),
        )


def test_timeout_below_common_prefix_has_no_search_recommendation() -> None:
    result = _result(
        status="timeout",
        stop_reason="wall_clock_timeout",
        solution_claim="none",
        consumed_budget=_consumed(completed_world_count=1),
        candidate_results=_ranked_candidates(completed=1, recommend=False),
        recommended_card=None,
    )

    assert result.recommended_card is None
    assert not any(candidate.is_recommended for candidate in result.candidate_results)


def test_timeout_requires_none_claim_but_allows_an_exact_completed_prefix() -> None:
    result = _result(
        status="timeout",
        stop_reason="wall_clock_timeout",
        solution_claim="none",
        consumed_budget=_consumed(completed_world_count=2),
        candidate_results=_ranked_candidates(completed=2),
    )

    assert result.consumed_budget.completed_world_count == 2
    with pytest.raises(ValueError, match="no reproducible solution claim"):
        replace(result, solution_claim="node_limited_partial")


@pytest.mark.parametrize(
    ("status", "stop_reason", "solution_claim", "consumed", "completed"),
    [
        (
            "partial",
            "node_budget_exhausted",
            "node_limited_partial",
            _consumed(completed_world_count=2),
            2,
        ),
        (
            "partial",
            "depth_budget_exhausted",
            "depth_limited_per_selected_world",
            _consumed(completed_world_count=2),
            2,
        ),
        (
            "timeout",
            "wall_clock_timeout",
            "none",
            _consumed(completed_world_count=2),
            2,
        ),
    ],
)
def test_partial_and_timeout_status_invariants_allow_common_prefix_recommendation(
    status: str,
    stop_reason: str,
    solution_claim: str,
    consumed: ConsumedSearchBudget,
    completed: int,
) -> None:
    result = _result(
        status=status,
        stop_reason=stop_reason,
        solution_claim=solution_claim,
        consumed_budget=consumed,
        candidate_results=_ranked_candidates(completed=completed),
    )

    assert result.recommended_card == "CA"


def test_depth_limited_result_accepts_zero_completed_selected_worlds() -> None:
    result = _result(
        status="partial",
        stop_reason="depth_budget_exhausted",
        solution_claim="depth_limited_per_selected_world",
        consumed_budget=_consumed(completed_world_count=0),
        candidate_results=_ranked_candidates(completed=0, recommend=False),
        recommended_card=None,
    )

    assert result.consumed_budget.selected_world_count == 3
    assert result.consumed_budget.completed_world_count == 0
    assert all(
        candidate.local_contract_success_rate is None
        for candidate in result.candidate_results
    )

    with pytest.raises(ValueError, match="compatible-world coverage"):
        _result(
            status="partial",
            stop_reason="depth_budget_exhausted",
            solution_claim="depth_limited_per_selected_world",
            world_coverage="none",
            consumed_budget=_consumed(
                selected_world_count=0,
                completed_world_count=0,
                sampled_world_count=0,
                unique_sampled_world_count=0,
            ),
            compatible_world_count=None,
            candidate_results=_ranked_candidates(completed=0, recommend=False),
            recommended_card=None,
        )


def test_unavailable_status_has_no_worlds_candidates_or_recommendation() -> None:
    result = _result(
        status="unavailable",
        stop_reason="remaining_trick_limit_exceeded",
        world_coverage="none",
        solution_claim="none",
        consumed_budget=_consumed(
            depth_reached=0,
            nodes_expanded=0,
            selected_world_count=0,
            completed_world_count=0,
            sampled_world_count=0,
            unique_sampled_world_count=0,
        ),
        compatible_world_count=None,
        candidate_results=(),
        recommended_card=None,
    )

    assert result.status == "unavailable"


@pytest.mark.parametrize(
    ("status", "stop_reason"),
    [
        ("complete", "node_budget_exhausted"),
        ("partial", "wall_clock_timeout"),
        ("timeout", "completed"),
        ("unavailable", "completed"),
    ],
)
def test_status_rejects_inconsistent_stop_reason(status: str, stop_reason: str) -> None:
    with pytest.raises(ValueError, match="cannot use stop reason"):
        _result(status=status, stop_reason=stop_reason)


@pytest.mark.parametrize(
    ("stop_reason", "solution_claim"),
    [
        ("node_budget_exhausted", "depth_limited_per_selected_world"),
        ("depth_budget_exhausted", "node_limited_partial"),
    ],
)
def test_partial_stop_reason_requires_matching_solution_claim(
    stop_reason: str,
    solution_claim: str,
) -> None:
    with pytest.raises(ValueError, match="requires a .*limited claim"):
        _result(
            status="partial",
            stop_reason=stop_reason,
            solution_claim=solution_claim,
        )


def test_candidate_coverage_must_equal_for_every_candidate_and_consumed_budget() -> None:
    candidates = list(_ranked_candidates())
    candidates[1] = replace(
        candidates[1],
        completed_world_count=2,
        local_contract_success_count=1,
        local_contract_success_rate=0.5,
    )

    with pytest.raises(ValueError, match="same completed-world prefix"):
        _result(candidate_results=tuple(candidates))


def test_partial_recommendation_requires_minimum_comparable_common_prefix() -> None:
    with pytest.raises(ValueError, match="minimum common completed-world prefix"):
        _result(
            status="partial",
            stop_reason="node_budget_exhausted",
            solution_claim="node_limited_partial",
            consumed_budget=_consumed(completed_world_count=1),
            candidate_results=_ranked_candidates(completed=1),
        )


def test_recommendation_and_fallback_fields_are_consistent() -> None:
    with pytest.raises(ValueError, match="exactly one marked candidate"):
        _result(candidate_results=_ranked_candidates(recommend=False))
    with pytest.raises(ValueError, match="fallback_method must be null"):
        _result(fallback_method="immediate")

    fallback = _result(
        status="partial",
        stop_reason="node_budget_exhausted",
        solution_claim="node_limited_partial",
        consumed_budget=_consumed(completed_world_count=1),
        candidate_results=_ranked_candidates(completed=1, recommend=False),
        recommended_card=None,
        fallback_used=True,
        fallback_method="immediate_expected_value",
    )
    assert fallback.fallback_used is True


def test_null_candidates_reject_card_point_margin() -> None:
    with pytest.raises(ValueError, match="Null candidates"):
        _result(
            game_type="null",
            candidate_results=_ranked_candidates(game_type="grand"),
        )


def test_complete_null_result_serializes_deterministically_without_margin() -> None:
    candidates = _ranked_candidates(game_type="null")
    result = _result(
        game_type="null",
        candidate_results=candidates,
        recommended_card=candidates[0].card,
    )

    first = build_serializable_bounded_search_result(result)
    second = build_serializable_bounded_search_result(result)

    assert first == second
    assert first["game_type"] == "null"
    assert all(
        candidate["mean_local_side_card_point_margin"] is None
        for candidate in first["candidate_results"]
    )


def test_serialization_is_deterministic_and_contains_no_private_world_data() -> None:
    result = _result()

    first = build_serializable_bounded_search_result(result)
    second = build_serializable_bounded_search_result(result)

    assert first == second
    assert list(first) == [
        "schema_version",
        "analysis_method",
        "search_method",
        "game_type",
        "status",
        "stop_reason",
        "world_coverage",
        "solution_claim",
        "terminal_utility_version",
        "requested_budget",
        "consumed_budget",
        "compatible_world_count",
        "candidate_results",
        "recommended_card",
        "fallback_used",
        "fallback_method",
    ]
    serialized_text = repr(first)
    for forbidden in (
        "left_hand",
        "right_hand",
        "hypothetical_skat",
        "world_assignment",
        "world_fingerprint",
        "principal_variation",
        "future_historical",
    ):
        assert forbidden not in serialized_text
