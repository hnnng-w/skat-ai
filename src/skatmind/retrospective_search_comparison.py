from dataclasses import dataclass
from typing import Any

from skatmind.bounded_search_result import (
    AggregateSearchCandidateResult,
    BoundedSearchResult,
)
from skatmind.post_game_review import build_card_rank_lookup

NO_COMPLETED_SEARCH_WORLDS = "no_completed_search_worlds"
ACTUAL_CARD_NOT_PROVIDED = "actual_card_not_provided"
ACTUAL_CARD_NOT_IN_SEARCH_CANDIDATES = "actual_card_not_in_search_candidates"
SEARCH_CARD_NOT_AVAILABLE = "search_card_not_available"
IMMEDIATE_CARD_NOT_PROVIDED = "immediate_card_not_provided"
IMMEDIATE_ANALYSIS_REPORT_NOT_AVAILABLE = "immediate_analysis_report_not_available"
IMMEDIATE_CARD_NOT_IN_SEARCH_CANDIDATES = "immediate_card_not_in_search_candidates"
SEARCH_CARD_NOT_IN_IMMEDIATE_ANALYSIS_REPORT = (
    "search_card_not_in_immediate_analysis_report"
)
IMMEDIATE_CARD_NOT_IN_IMMEDIATE_ANALYSIS_REPORT = (
    "immediate_card_not_in_immediate_analysis_report"
)


@dataclass(frozen=True)
class SearchAggregateMetrics:
    local_contract_success_count: int
    local_contract_success_rate: float
    mean_local_side_game_score: float
    mean_local_side_card_point_margin: float | None


@dataclass(frozen=True)
class SearchActualCardComparison:
    is_available: bool
    unavailable_reason: str | None
    actual_card: str | None
    search_recommended_card: str | None
    actual_card_rank: int | None
    recommended_card_rank: int | None
    actual_card_is_best_aggregate: bool | None
    actual_card_is_aggregate_equivalent_to_recommendation: bool | None
    strictly_better_card_count: int | None
    completed_world_count: int
    comparison_basis: str | None
    actual_card_metrics: SearchAggregateMetrics | None
    recommended_card_metrics: SearchAggregateMetrics | None
    contract_success_rate_gap: float | None
    mean_local_side_game_score_gap: float | None
    mean_local_side_card_point_margin_gap: float | None


@dataclass(frozen=True)
class SearchVsImmediateComparison:
    is_available: bool
    unavailable_reason: str | None
    search_card: str | None
    immediate_card: str | None
    same_recommended_card: bool | None
    search_rank_of_immediate_card: int | None
    immediate_rank_of_search_card: int | None
    search_aggregate_relation: str
    search_contract_success_rate_advantage: float | None
    search_mean_game_score_advantage: float | None
    search_mean_card_point_margin_advantage: float | None


def _metrics(candidate: AggregateSearchCandidateResult) -> SearchAggregateMetrics:
    if (
        candidate.local_contract_success_rate is None
        or candidate.mean_local_side_game_score is None
    ):
        raise ValueError("Completed Search candidates require aggregate metrics.")
    return SearchAggregateMetrics(
        local_contract_success_count=candidate.local_contract_success_count,
        local_contract_success_rate=candidate.local_contract_success_rate,
        mean_local_side_game_score=candidate.mean_local_side_game_score,
        mean_local_side_card_point_margin=(
            candidate.mean_local_side_card_point_margin
        ),
    )


def _metric_tuple(
    candidate: AggregateSearchCandidateResult,
    game_type: str,
) -> tuple[float, ...]:
    metrics = _metrics(candidate)
    values = (
        metrics.local_contract_success_rate,
        metrics.mean_local_side_game_score,
    )
    if game_type == "null":
        return values
    if metrics.mean_local_side_card_point_margin is None:
        raise ValueError("Suit and Grand Search candidates require a margin.")
    return (*values, metrics.mean_local_side_card_point_margin)


def _comparison_basis(result: BoundedSearchResult) -> str:
    if result.status == "complete":
        if result.world_coverage == "all_compatible_worlds":
            return "all_compatible_worlds"
        if result.world_coverage == "sampled_compatible_worlds":
            return "sampled_compatible_worlds"
    return "completed_common_prefix"


def _candidate_by_card(
    result: BoundedSearchResult,
) -> dict[str, AggregateSearchCandidateResult]:
    return {candidate.card: candidate for candidate in result.candidate_results}


def _unavailable_actual_card_comparison(
    *,
    reason: str,
    actual_card: str | None,
    completed_world_count: int,
    search_card: str | None,
    comparison_basis: str | None,
) -> SearchActualCardComparison:
    return SearchActualCardComparison(
        is_available=False,
        unavailable_reason=reason,
        actual_card=actual_card,
        search_recommended_card=search_card,
        actual_card_rank=None,
        recommended_card_rank=None,
        actual_card_is_best_aggregate=None,
        actual_card_is_aggregate_equivalent_to_recommendation=None,
        strictly_better_card_count=None,
        completed_world_count=completed_world_count,
        comparison_basis=comparison_basis,
        actual_card_metrics=None,
        recommended_card_metrics=None,
        contract_success_rate_gap=None,
        mean_local_side_game_score_gap=None,
        mean_local_side_card_point_margin_gap=None,
    )


def build_search_actual_card_comparison(
    search_result: BoundedSearchResult,
    actual_card: str | None,
) -> SearchActualCardComparison:
    """Compares an observed card with Search's common-prefix aggregates."""
    if not isinstance(search_result, BoundedSearchResult):
        raise ValueError("search_result must be a BoundedSearchResult.")

    completed_world_count = search_result.consumed_budget.completed_world_count
    search_card = search_result.recommended_card
    if completed_world_count == 0:
        return _unavailable_actual_card_comparison(
            reason=NO_COMPLETED_SEARCH_WORLDS,
            actual_card=actual_card,
            completed_world_count=0,
            search_card=search_card,
            comparison_basis=None,
        )

    comparison_basis = _comparison_basis(search_result)
    if search_card is None:
        return _unavailable_actual_card_comparison(
            reason=SEARCH_CARD_NOT_AVAILABLE,
            actual_card=actual_card,
            completed_world_count=completed_world_count,
            search_card=None,
            comparison_basis=comparison_basis,
        )

    search_candidate = _candidate_by_card(search_result)[search_card]
    if actual_card is None:
        return _unavailable_actual_card_comparison(
            reason=ACTUAL_CARD_NOT_PROVIDED,
            actual_card=None,
            completed_world_count=completed_world_count,
            search_card=search_candidate.card,
            comparison_basis=comparison_basis,
        )

    candidates_by_card = _candidate_by_card(search_result)
    actual_candidate = candidates_by_card.get(actual_card)
    if actual_candidate is None:
        return _unavailable_actual_card_comparison(
            reason=ACTUAL_CARD_NOT_IN_SEARCH_CANDIDATES,
            actual_card=actual_card,
            completed_world_count=completed_world_count,
            search_card=search_candidate.card,
            comparison_basis=comparison_basis,
        )

    search_metrics = _metrics(search_candidate)
    actual_metrics = _metrics(actual_candidate)
    search_metric_tuple = _metric_tuple(search_candidate, search_result.game_type)
    actual_metric_tuple = _metric_tuple(actual_candidate, search_result.game_type)
    strictly_better_card_count = sum(
        _metric_tuple(candidate, search_result.game_type) > actual_metric_tuple
        for candidate in search_result.candidate_results
    )
    margin_gap = None
    if search_result.game_type != "null":
        if (
            search_metrics.mean_local_side_card_point_margin is None
            or actual_metrics.mean_local_side_card_point_margin is None
        ):
            raise ValueError("Suit and Grand Search comparisons require margins.")
        margin_gap = (
            search_metrics.mean_local_side_card_point_margin
            - actual_metrics.mean_local_side_card_point_margin
        )

    return SearchActualCardComparison(
        is_available=True,
        unavailable_reason=None,
        actual_card=actual_card,
        search_recommended_card=search_candidate.card,
        actual_card_rank=actual_candidate.rank,
        recommended_card_rank=search_candidate.rank,
        actual_card_is_best_aggregate=strictly_better_card_count == 0,
        actual_card_is_aggregate_equivalent_to_recommendation=(
            actual_metric_tuple == search_metric_tuple
        ),
        strictly_better_card_count=strictly_better_card_count,
        completed_world_count=completed_world_count,
        comparison_basis=comparison_basis,
        actual_card_metrics=actual_metrics,
        recommended_card_metrics=search_metrics,
        contract_success_rate_gap=(
            search_metrics.local_contract_success_rate
            - actual_metrics.local_contract_success_rate
        ),
        mean_local_side_game_score_gap=(
            search_metrics.mean_local_side_game_score
            - actual_metrics.mean_local_side_game_score
        ),
        mean_local_side_card_point_margin_gap=margin_gap,
    )


def _unavailable_search_vs_immediate_comparison(
    *,
    reason: str,
    search_card: str | None,
    immediate_card: str | None,
) -> SearchVsImmediateComparison:
    return SearchVsImmediateComparison(
        is_available=False,
        unavailable_reason=reason,
        search_card=search_card,
        immediate_card=immediate_card,
        same_recommended_card=None,
        search_rank_of_immediate_card=None,
        immediate_rank_of_search_card=None,
        search_aggregate_relation="not_available",
        search_contract_success_rate_advantage=None,
        search_mean_game_score_advantage=None,
        search_mean_card_point_margin_advantage=None,
    )


def build_search_vs_immediate_comparison(
    search_result: BoundedSearchResult,
    immediate_card: str | None,
    immediate_analysis_report: list[dict[str, Any]] | None,
    game_type: str,
    player_role: str,
) -> SearchVsImmediateComparison:
    """Evaluates Search and Immediate cards on the same Search aggregate."""
    if not isinstance(search_result, BoundedSearchResult):
        raise ValueError("search_result must be a BoundedSearchResult.")
    if game_type != search_result.game_type:
        raise ValueError("game_type must match the bounded Search result.")
    search_card = search_result.recommended_card
    if search_result.consumed_budget.completed_world_count == 0:
        return _unavailable_search_vs_immediate_comparison(
            reason=NO_COMPLETED_SEARCH_WORLDS,
            search_card=search_card,
            immediate_card=immediate_card,
        )
    if search_card is None:
        return _unavailable_search_vs_immediate_comparison(
            reason=SEARCH_CARD_NOT_AVAILABLE,
            search_card=None,
            immediate_card=immediate_card,
        )

    search_candidate = _candidate_by_card(search_result)[search_card]
    if immediate_card is None:
        return _unavailable_search_vs_immediate_comparison(
            reason=IMMEDIATE_CARD_NOT_PROVIDED,
            search_card=search_candidate.card,
            immediate_card=None,
        )
    if not immediate_analysis_report:
        return _unavailable_search_vs_immediate_comparison(
            reason=IMMEDIATE_ANALYSIS_REPORT_NOT_AVAILABLE,
            search_card=search_candidate.card,
            immediate_card=immediate_card,
        )

    candidates_by_card = _candidate_by_card(search_result)
    immediate_candidate = candidates_by_card.get(immediate_card)
    if immediate_candidate is None:
        return _unavailable_search_vs_immediate_comparison(
            reason=IMMEDIATE_CARD_NOT_IN_SEARCH_CANDIDATES,
            search_card=search_candidate.card,
            immediate_card=immediate_card,
        )

    immediate_rank_lookup = build_card_rank_lookup(
        analysis_report=immediate_analysis_report,
        game_type=game_type,
        player_role=player_role,
    )
    if search_candidate.card not in immediate_rank_lookup:
        return _unavailable_search_vs_immediate_comparison(
            reason=SEARCH_CARD_NOT_IN_IMMEDIATE_ANALYSIS_REPORT,
            search_card=search_candidate.card,
            immediate_card=immediate_card,
        )
    if immediate_card not in immediate_rank_lookup:
        return _unavailable_search_vs_immediate_comparison(
            reason=IMMEDIATE_CARD_NOT_IN_IMMEDIATE_ANALYSIS_REPORT,
            search_card=search_candidate.card,
            immediate_card=immediate_card,
        )

    search_metric_tuple = _metric_tuple(search_candidate, game_type)
    immediate_metric_tuple = _metric_tuple(immediate_candidate, game_type)
    if search_metric_tuple < immediate_metric_tuple:
        raise ValueError(
            "Search rank-1 candidate is worse than the aligned Immediate candidate."
        )
    relation = (
        "aggregate_equivalent"
        if search_metric_tuple == immediate_metric_tuple
        else "search_better"
    )
    search_metrics = _metrics(search_candidate)
    immediate_metrics = _metrics(immediate_candidate)
    margin_advantage = None
    if game_type != "null":
        if (
            search_metrics.mean_local_side_card_point_margin is None
            or immediate_metrics.mean_local_side_card_point_margin is None
        ):
            raise ValueError("Suit and Grand Search comparisons require margins.")
        margin_advantage = (
            search_metrics.mean_local_side_card_point_margin
            - immediate_metrics.mean_local_side_card_point_margin
        )

    return SearchVsImmediateComparison(
        is_available=True,
        unavailable_reason=None,
        search_card=search_candidate.card,
        immediate_card=immediate_card,
        same_recommended_card=search_candidate.card == immediate_card,
        search_rank_of_immediate_card=immediate_candidate.rank,
        immediate_rank_of_search_card=immediate_rank_lookup[search_candidate.card],
        search_aggregate_relation=relation,
        search_contract_success_rate_advantage=(
            search_metrics.local_contract_success_rate
            - immediate_metrics.local_contract_success_rate
        ),
        search_mean_game_score_advantage=(
            search_metrics.mean_local_side_game_score
            - immediate_metrics.mean_local_side_game_score
        ),
        search_mean_card_point_margin_advantage=margin_advantage,
    )


def build_serializable_search_aggregate_metrics(
    metrics: SearchAggregateMetrics,
) -> dict[str, int | float | None]:
    return {
        "local_contract_success_count": metrics.local_contract_success_count,
        "local_contract_success_rate": metrics.local_contract_success_rate,
        "mean_local_side_game_score": metrics.mean_local_side_game_score,
        "mean_local_side_card_point_margin": (
            metrics.mean_local_side_card_point_margin
        ),
    }


def build_serializable_search_actual_card_comparison(
    comparison: SearchActualCardComparison,
) -> dict[str, Any]:
    return {
        "is_available": comparison.is_available,
        "unavailable_reason": comparison.unavailable_reason,
        "actual_card": comparison.actual_card,
        "search_recommended_card": comparison.search_recommended_card,
        "actual_card_rank": comparison.actual_card_rank,
        "recommended_card_rank": comparison.recommended_card_rank,
        "actual_card_is_best_aggregate": comparison.actual_card_is_best_aggregate,
        "actual_card_is_aggregate_equivalent_to_recommendation": (
            comparison.actual_card_is_aggregate_equivalent_to_recommendation
        ),
        "strictly_better_card_count": comparison.strictly_better_card_count,
        "completed_world_count": comparison.completed_world_count,
        "comparison_basis": comparison.comparison_basis,
        "actual_card_metrics": (
            build_serializable_search_aggregate_metrics(comparison.actual_card_metrics)
            if comparison.actual_card_metrics is not None
            else None
        ),
        "recommended_card_metrics": (
            build_serializable_search_aggregate_metrics(
                comparison.recommended_card_metrics
            )
            if comparison.recommended_card_metrics is not None
            else None
        ),
        "contract_success_rate_gap": comparison.contract_success_rate_gap,
        "mean_local_side_game_score_gap": comparison.mean_local_side_game_score_gap,
        "mean_local_side_card_point_margin_gap": (
            comparison.mean_local_side_card_point_margin_gap
        ),
    }


def build_serializable_search_vs_immediate_comparison(
    comparison: SearchVsImmediateComparison,
) -> dict[str, Any]:
    return {
        "is_available": comparison.is_available,
        "unavailable_reason": comparison.unavailable_reason,
        "search_card": comparison.search_card,
        "immediate_card": comparison.immediate_card,
        "same_recommended_card": comparison.same_recommended_card,
        "search_rank_of_immediate_card": comparison.search_rank_of_immediate_card,
        "immediate_rank_of_search_card": comparison.immediate_rank_of_search_card,
        "search_aggregate_relation": comparison.search_aggregate_relation,
        "search_contract_success_rate_advantage": (
            comparison.search_contract_success_rate_advantage
        ),
        "search_mean_game_score_advantage": (
            comparison.search_mean_game_score_advantage
        ),
        "search_mean_card_point_margin_advantage": (
            comparison.search_mean_card_point_margin_advantage
        ),
    }
