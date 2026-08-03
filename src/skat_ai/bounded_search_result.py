import math
from dataclasses import dataclass, replace
from typing import Any

from skat_ai.bounded_search_information import SEARCH_UNAVAILABLE_REASONS
from skat_ai.deck import get_full_deck
from skat_ai.rules import GAME_TYPES
from skat_ai.terminal_utility import TERMINAL_UTILITY_VERSION

BOUNDED_SEARCH_SCHEMA_VERSION = 1
BOUNDED_SEARCH_ANALYSIS_METHOD = "bounded_search"
BOUNDED_SEARCH_METHODS = (
    "perfect_information_minimax_v1",
    "compatible_world_minimax_v1",
)
BOUNDED_SEARCH_STATUSES = ("complete", "partial", "timeout", "unavailable")
BOUNDED_SEARCH_STOP_REASONS = (
    "completed",
    "node_budget_exhausted",
    "depth_budget_exhausted",
    "wall_clock_timeout",
    *SEARCH_UNAVAILABLE_REASONS,
)
WORLD_COVERAGE_VALUES = (
    "none",
    "single_exact_world",
    "all_compatible_worlds",
    "sampled_compatible_worlds",
)
SOLUTION_CLAIM_VALUES = (
    "none",
    "exact_per_selected_world",
    "depth_limited_per_selected_world",
    "node_limited_partial",
)


def _validate_positive_integer(value: int, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer.")


def _validate_non_negative_integer(value: int, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer.")


@dataclass(frozen=True)
class RequestedSearchBudget:
    """Deterministic structural limits plus an optional wall-clock cutoff."""

    max_remaining_tricks: int
    max_depth_plies: int
    max_nodes: int
    max_selected_worlds: int
    max_sampled_worlds: int
    minimum_comparable_worlds: int
    wall_clock_timeout_ms: int | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "max_remaining_tricks",
            "max_depth_plies",
            "max_nodes",
            "max_selected_worlds",
            "max_sampled_worlds",
            "minimum_comparable_worlds",
        ):
            _validate_positive_integer(getattr(self, field_name), field_name)
        if self.wall_clock_timeout_ms is not None:
            _validate_positive_integer(
                self.wall_clock_timeout_ms,
                "wall_clock_timeout_ms",
            )
        if self.max_sampled_worlds > self.max_selected_worlds:
            raise ValueError("max_sampled_worlds cannot exceed max_selected_worlds.")
        if self.minimum_comparable_worlds > self.max_selected_worlds:
            raise ValueError(
                "minimum_comparable_worlds cannot exceed max_selected_worlds."
            )


@dataclass(frozen=True)
class ConsumedSearchBudget:
    """Consumed structural work and diagnostic wall-clock time."""

    depth_reached: int
    nodes_expanded: int
    selected_world_count: int
    completed_world_count: int
    sampled_world_count: int
    unique_sampled_world_count: int
    wall_clock_elapsed_ms: int

    def __post_init__(self) -> None:
        for field_name in (
            "depth_reached",
            "nodes_expanded",
            "selected_world_count",
            "completed_world_count",
            "sampled_world_count",
            "unique_sampled_world_count",
            "wall_clock_elapsed_ms",
        ):
            _validate_non_negative_integer(getattr(self, field_name), field_name)
        if self.completed_world_count > self.selected_world_count:
            raise ValueError(
                "completed_world_count cannot exceed selected_world_count."
            )
        if self.sampled_world_count > self.selected_world_count:
            raise ValueError("sampled_world_count cannot exceed selected_world_count.")
        if self.unique_sampled_world_count > self.sampled_world_count:
            raise ValueError(
                "unique_sampled_world_count cannot exceed sampled_world_count."
            )
        if self.sampled_world_count > 0 and self.unique_sampled_world_count == 0:
            raise ValueError("Sampled worlds require at least one unique sampled world.")


@dataclass(frozen=True)
class AggregateSearchCandidateResult:
    """Privacy-safe candidate aggregate over one common completed-world prefix."""

    card: str
    rank: int
    is_recommended: bool
    completed_world_count: int
    local_contract_success_count: int
    local_contract_success_rate: float | None
    mean_local_side_game_score: float | None
    mean_local_side_card_point_margin: float | None

    def __post_init__(self) -> None:
        if self.card not in get_full_deck():
            raise ValueError(f"Invalid candidate card: {self.card}")
        _validate_positive_integer(self.rank, "rank")
        if not isinstance(self.is_recommended, bool):
            raise ValueError("is_recommended must be a boolean.")
        _validate_non_negative_integer(
            self.completed_world_count,
            "completed_world_count",
        )
        _validate_non_negative_integer(
            self.local_contract_success_count,
            "local_contract_success_count",
        )
        if self.local_contract_success_count > self.completed_world_count:
            raise ValueError(
                "local_contract_success_count cannot exceed completed_world_count."
            )
        aggregate_values = (
            self.local_contract_success_rate,
            self.mean_local_side_game_score,
            self.mean_local_side_card_point_margin,
        )
        if self.completed_world_count == 0:
            if any(value is not None for value in aggregate_values):
                raise ValueError(
                    "Candidate rates and means must be absent with zero completed worlds."
                )
            return
        if self.local_contract_success_rate is None:
            raise ValueError("A completed candidate requires a success rate.")
        if self.mean_local_side_game_score is None:
            raise ValueError("A completed candidate requires a mean game score.")
        for field_name, value in (
            ("local_contract_success_rate", self.local_contract_success_rate),
            ("mean_local_side_game_score", self.mean_local_side_game_score),
            (
                "mean_local_side_card_point_margin",
                self.mean_local_side_card_point_margin,
            ),
        ):
            if value is not None and (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
            ):
                raise ValueError(f"{field_name} must be a finite number or null.")
        expected_rate = self.local_contract_success_count / self.completed_world_count
        if not math.isclose(
            self.local_contract_success_rate,
            expected_rate,
            rel_tol=1e-12,
            abs_tol=1e-12,
        ):
            raise ValueError(
                "local_contract_success_rate must match its count and denominator."
            )


def _candidate_sort_key(
    candidate: AggregateSearchCandidateResult,
    game_type: str,
) -> tuple[float, float, float, int]:
    card_order = {card: index for index, card in enumerate(get_full_deck())}
    return (
        -(candidate.local_contract_success_rate or 0.0),
        -(candidate.mean_local_side_game_score or 0.0),
        -(
            candidate.mean_local_side_card_point_margin or 0.0
            if game_type != "null"
            else 0.0
        ),
        card_order[candidate.card],
    )


def rank_search_candidate_results(
    candidates: tuple[AggregateSearchCandidateResult, ...],
    game_type: str,
    *,
    recommend: bool,
) -> tuple[AggregateSearchCandidateResult, ...]:
    """Ranks aggregate candidates with canonical card order as the final tie-break."""
    if game_type not in GAME_TYPES:
        raise ValueError(f"Invalid candidate ranking game type: {game_type}")
    ordered = sorted(tuple(candidates), key=lambda item: _candidate_sort_key(item, game_type))
    return tuple(
        replace(
            candidate,
            rank=index,
            is_recommended=recommend and index == 1,
        )
        for index, candidate in enumerate(ordered, start=1)
    )


@dataclass(frozen=True)
class BoundedSearchResult:
    """Version-1 aggregate result for a future bounded search implementation."""

    schema_version: int
    analysis_method: str
    search_method: str
    game_type: str
    status: str
    stop_reason: str
    world_coverage: str
    solution_claim: str
    terminal_utility_version: int
    requested_budget: RequestedSearchBudget
    consumed_budget: ConsumedSearchBudget
    compatible_world_count: int | None
    candidate_results: tuple[AggregateSearchCandidateResult, ...]
    recommended_card: str | None
    fallback_used: bool
    fallback_method: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.candidate_results, tuple):
            raise TypeError("candidate_results must be a tuple.")
        if self.schema_version != BOUNDED_SEARCH_SCHEMA_VERSION:
            raise ValueError("Unsupported bounded-search schema version.")
        if self.analysis_method != BOUNDED_SEARCH_ANALYSIS_METHOD:
            raise ValueError("analysis_method must be bounded_search.")
        if self.search_method not in BOUNDED_SEARCH_METHODS:
            raise ValueError(f"Invalid bounded-search method: {self.search_method}")
        if self.game_type not in GAME_TYPES:
            raise ValueError(f"Invalid bounded-search game type: {self.game_type}")
        if self.status not in BOUNDED_SEARCH_STATUSES:
            raise ValueError(f"Invalid bounded-search status: {self.status}")
        if self.stop_reason not in BOUNDED_SEARCH_STOP_REASONS:
            raise ValueError(f"Invalid bounded-search stop reason: {self.stop_reason}")
        if self.world_coverage not in WORLD_COVERAGE_VALUES:
            raise ValueError(f"Invalid world coverage: {self.world_coverage}")
        if self.solution_claim not in SOLUTION_CLAIM_VALUES:
            raise ValueError(f"Invalid solution claim: {self.solution_claim}")
        if self.terminal_utility_version != TERMINAL_UTILITY_VERSION:
            raise ValueError("Unsupported terminal utility version.")
        if self.compatible_world_count is not None:
            _validate_non_negative_integer(
                self.compatible_world_count,
                "compatible_world_count",
            )
        self._validate_status()
        self._validate_budget_consumption()
        self._validate_coverage()
        self._validate_candidates()
        self._validate_recommendation_and_fallback()

    def _validate_status(self) -> None:
        expected_reasons = {
            "complete": {"completed"},
            "partial": {"node_budget_exhausted", "depth_budget_exhausted"},
            "timeout": {"wall_clock_timeout"},
            "unavailable": set(SEARCH_UNAVAILABLE_REASONS),
        }
        if self.stop_reason not in expected_reasons[self.status]:
            raise ValueError(
                f"Status {self.status!r} cannot use stop reason {self.stop_reason!r}."
            )
        if self.status == "unavailable":
            if self.world_coverage != "none" or self.solution_claim != "none":
                raise ValueError("Unavailable search results have no coverage or claim.")
            if self.candidate_results:
                raise ValueError("Unavailable search results cannot contain candidates.")
        elif not self.candidate_results:
            raise ValueError("Available search results require candidate aggregates.")
        if self.status == "complete" and self.solution_claim != "exact_per_selected_world":
            raise ValueError("Complete search results require exact selected-world solutions.")
        if (
            self.status == "partial"
            and self.stop_reason == "node_budget_exhausted"
            and self.solution_claim != "node_limited_partial"
        ):
            raise ValueError("Node-budget exhaustion requires a node-limited claim.")
        if (
            self.status == "partial"
            and self.stop_reason == "depth_budget_exhausted"
            and self.solution_claim != "depth_limited_per_selected_world"
        ):
            raise ValueError("Depth-budget exhaustion requires a depth-limited claim.")
        if self.status == "timeout" and self.requested_budget.wall_clock_timeout_ms is None:
            raise ValueError("Timeout status requires a requested wall-clock cutoff.")
        if self.status == "timeout" and self.solution_claim != "none":
            raise ValueError("Timeout results require no reproducible solution claim.")

    def _validate_budget_consumption(self) -> None:
        consumed = self.consumed_budget
        requested = self.requested_budget
        if consumed.depth_reached > requested.max_depth_plies:
            raise ValueError("Consumed depth exceeds the requested depth budget.")
        if consumed.nodes_expanded > requested.max_nodes:
            raise ValueError("Consumed nodes exceed the requested node budget.")
        if consumed.selected_world_count > requested.max_selected_worlds:
            raise ValueError("Selected worlds exceed the requested world budget.")
        if consumed.sampled_world_count > requested.max_sampled_worlds:
            raise ValueError("Sampled worlds exceed the requested sampling budget.")

    def _validate_coverage(self) -> None:
        consumed = self.consumed_budget
        if self.world_coverage == "none":
            if any(
                (
                    consumed.selected_world_count,
                    consumed.completed_world_count,
                    consumed.sampled_world_count,
                    consumed.unique_sampled_world_count,
                )
            ):
                raise ValueError("World coverage none cannot consume world counts.")
        elif self.world_coverage == "single_exact_world":
            if self.compatible_world_count != 1 or consumed.selected_world_count != 1:
                raise ValueError("Single exact coverage requires one compatible world.")
            if consumed.sampled_world_count != 0:
                raise ValueError("Single exact coverage is not sampled coverage.")
        elif self.world_coverage == "all_compatible_worlds":
            if (
                self.compatible_world_count is None
                or self.compatible_world_count <= 0
                or consumed.selected_world_count != self.compatible_world_count
            ):
                raise ValueError(
                    "All-compatible coverage must select every compatible world."
                )
            if consumed.sampled_world_count != 0:
                raise ValueError("All-compatible coverage is not sampled coverage.")
        elif (
            consumed.selected_world_count == 0
            or consumed.sampled_world_count == 0
            or self.compatible_world_count is None
            or self.compatible_world_count <= 0
        ):
            raise ValueError("Sampled coverage requires selected sampled worlds.")
        elif consumed.selected_world_count != consumed.sampled_world_count:
            raise ValueError("Every selected sampled world must be one sampled draw.")
        elif consumed.unique_sampled_world_count > self.compatible_world_count:
            raise ValueError("Unique sampled worlds cannot exceed compatible worlds.")
        if (
            self.world_coverage != "sampled_compatible_worlds"
            and self.compatible_world_count is not None
            and consumed.selected_world_count > self.compatible_world_count
        ):
            raise ValueError("Selected worlds cannot exceed compatible worlds.")
        if (
            self.search_method == "perfect_information_minimax_v1"
            and self.status != "unavailable"
            and self.world_coverage != "single_exact_world"
        ):
            raise ValueError(
                "Perfect-information search requires single exact world coverage."
            )
        if (
            self.search_method == "compatible_world_minimax_v1"
            and self.status != "unavailable"
            and self.world_coverage not in {"all_compatible_worlds", "sampled_compatible_worlds"}
        ):
            raise ValueError("Compatible-world search requires compatible-world coverage.")

        if (
            self.solution_claim == "none"
            and self.status != "timeout"
            and consumed.completed_world_count != 0
        ):
            raise ValueError("A result with completed worlds requires a solution claim.")
        if self.solution_claim == "exact_per_selected_world" and (
            consumed.completed_world_count != consumed.selected_world_count
            or consumed.completed_world_count == 0
        ):
            raise ValueError(
                "Exact-per-selected-world requires every selected world to complete."
            )
        if self.solution_claim == "depth_limited_per_selected_world":
            if consumed.selected_world_count == 0:
                raise ValueError("Depth-limited-per-selected-world requires a selected world.")
            if consumed.completed_world_count >= consumed.selected_world_count:
                raise ValueError(
                    "Depth-limited-per-selected-world requires an incomplete selected prefix."
                )
        if self.solution_claim == "node_limited_partial" and self.status != "partial":
            raise ValueError("Node-limited partial claims require partial status.")
        if self.status in {"partial", "timeout"} and (
            consumed.selected_world_count == 0
            or consumed.completed_world_count >= consumed.selected_world_count
        ):
            raise ValueError("Incomplete search results require a strict completed-world prefix.")

    def _validate_candidates(self) -> None:
        candidates = self.candidate_results
        cards = [candidate.card for candidate in candidates]
        if len(cards) != len(set(cards)):
            raise ValueError("Candidate cards must be unique.")
        if [candidate.rank for candidate in candidates] != list(
            range(1, len(candidates) + 1)
        ):
            raise ValueError("Candidate ranks must be contiguous and ordered.")
        expected_order = sorted(
            candidates,
            key=lambda item: _candidate_sort_key(item, self.game_type),
        )
        if list(candidates) != expected_order:
            raise ValueError("Candidate order does not match deterministic ranking.")
        completed_counts = {candidate.completed_world_count for candidate in candidates}
        if len(completed_counts) > 1:
            raise ValueError("Every candidate must use the same completed-world prefix.")
        if completed_counts and completed_counts != {
            self.consumed_budget.completed_world_count
        }:
            raise ValueError(
                "Candidate coverage must match the consumed completed-world count."
            )
        for candidate in candidates:
            if self.game_type == "null":
                if candidate.mean_local_side_card_point_margin is not None:
                    raise ValueError("Null candidates cannot have a card-point margin.")
            elif (
                candidate.completed_world_count > 0
                and candidate.mean_local_side_card_point_margin is None
            ):
                raise ValueError(
                    "Suit and Grand candidates require a mean card-point margin."
                )

    def _validate_recommendation_and_fallback(self) -> None:
        recommended = [
            candidate for candidate in self.candidate_results if candidate.is_recommended
        ]
        if self.recommended_card is None:
            if recommended:
                raise ValueError(
                    "No candidate may be marked recommended without recommended_card."
                )
        else:
            if len(recommended) != 1 or recommended[0].card != self.recommended_card:
                raise ValueError(
                    "recommended_card must identify exactly one marked candidate."
                )
            if recommended[0].rank != 1:
                raise ValueError("The deterministic rank-1 candidate must be recommended.")
            if self.status in {"partial", "timeout"} and (
                self.consumed_budget.completed_world_count
                < self.requested_budget.minimum_comparable_worlds
            ):
                raise ValueError(
                    "Partial and timeout recommendations require the minimum "
                    "common completed-world prefix."
                )
            if self.status == "unavailable":
                raise ValueError("Unavailable search results cannot recommend a card.")

        if not isinstance(self.fallback_used, bool):
            raise ValueError("fallback_used must be a boolean.")
        if self.fallback_used:
            if not isinstance(self.fallback_method, str) or not self.fallback_method:
                raise ValueError("A used fallback requires a fallback_method.")
            if self.recommended_card is not None:
                raise ValueError("Search and fallback recommendations are mutually exclusive.")
        elif self.fallback_method is not None:
            raise ValueError("fallback_method must be null when fallback_used is false.")


def _serialize_requested_budget(budget: RequestedSearchBudget) -> dict[str, Any]:
    return {
        "max_remaining_tricks": budget.max_remaining_tricks,
        "max_depth_plies": budget.max_depth_plies,
        "max_nodes": budget.max_nodes,
        "max_selected_worlds": budget.max_selected_worlds,
        "max_sampled_worlds": budget.max_sampled_worlds,
        "minimum_comparable_worlds": budget.minimum_comparable_worlds,
        "wall_clock_timeout_ms": budget.wall_clock_timeout_ms,
    }


def _serialize_consumed_budget(budget: ConsumedSearchBudget) -> dict[str, int]:
    return {
        "depth_reached": budget.depth_reached,
        "nodes_expanded": budget.nodes_expanded,
        "selected_world_count": budget.selected_world_count,
        "completed_world_count": budget.completed_world_count,
        "sampled_world_count": budget.sampled_world_count,
        "unique_sampled_world_count": budget.unique_sampled_world_count,
        "wall_clock_elapsed_ms": budget.wall_clock_elapsed_ms,
    }


def build_serializable_bounded_search_result(
    result: BoundedSearchResult,
) -> dict[str, Any]:
    """Builds deterministic aggregate output without world-specific data."""
    return {
        "schema_version": result.schema_version,
        "analysis_method": result.analysis_method,
        "search_method": result.search_method,
        "game_type": result.game_type,
        "status": result.status,
        "stop_reason": result.stop_reason,
        "world_coverage": result.world_coverage,
        "solution_claim": result.solution_claim,
        "terminal_utility_version": result.terminal_utility_version,
        "requested_budget": _serialize_requested_budget(result.requested_budget),
        "consumed_budget": _serialize_consumed_budget(result.consumed_budget),
        "compatible_world_count": result.compatible_world_count,
        "candidate_results": [
            {
                "card": candidate.card,
                "rank": candidate.rank,
                "is_recommended": candidate.is_recommended,
                "completed_world_count": candidate.completed_world_count,
                "local_contract_success_count": (
                    candidate.local_contract_success_count
                ),
                "local_contract_success_rate": (
                    candidate.local_contract_success_rate
                ),
                "mean_local_side_game_score": (
                    candidate.mean_local_side_game_score
                ),
                "mean_local_side_card_point_margin": (
                    candidate.mean_local_side_card_point_margin
                ),
            }
            for candidate in result.candidate_results
        ],
        "recommended_card": result.recommended_card,
        "fallback_used": result.fallback_used,
        "fallback_method": result.fallback_method,
    }
