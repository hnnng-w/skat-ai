import time
from dataclasses import dataclass

from skat_ai.bounded_search_result import (
    BOUNDED_SEARCH_ANALYSIS_METHOD,
    BOUNDED_SEARCH_SCHEMA_VERSION,
    AggregateSearchCandidateResult,
    BoundedSearchResult,
    ConsumedSearchBudget,
    RequestedSearchBudget,
    rank_search_candidate_results,
)
from skat_ai.exact_search_state import (
    ExactSearchState,
    apply_exact_search_card,
    get_exact_search_legal_cards,
)
from skat_ai.exact_terminal_utility import build_exact_terminal_utility
from skat_ai.game_declaration import SUIT_GAME_TYPES
from skat_ai.game_value import build_game_value_summary
from skat_ai.overbid import build_overbid_summary
from skat_ai.side_ownership import VALID_CONCRETE_PLAYERS, get_player_side
from skat_ai.terminal_utility import (
    TERMINAL_UTILITY_VERSION,
    TerminalUtility,
    compare_terminal_utilities,
)

PERFECT_INFORMATION_MINIMAX_METHOD = "perfect_information_minimax_v1"
PERFECT_INFORMATION_MAX_REMAINING_TRICKS = 5

_monotonic = time.monotonic


class _SearchAborted(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


@dataclass
class _SearchContext:
    local_side: str
    requested_budget: RequestedSearchBudget
    started_at: float
    transposition_table: dict[ExactSearchState, TerminalUtility]
    nodes_expanded: int = 0
    depth_reached: int = 0

    def current_elapsed_ms(self) -> float:
        return max(0.0, (_monotonic() - self.started_at) * 1000)

    def elapsed_ms(self) -> int:
        return int(self.current_elapsed_ms())

    def begin_uncached_evaluation(self, depth: int) -> None:
        timeout = self.requested_budget.wall_clock_timeout_ms
        if timeout is not None and self.current_elapsed_ms() >= timeout:
            raise _SearchAborted("wall_clock_timeout")
        if self.nodes_expanded >= self.requested_budget.max_nodes:
            raise _SearchAborted("node_budget_exhausted")
        self.nodes_expanded += 1
        self.depth_reached = max(self.depth_reached, depth)


def _is_at_least(left: TerminalUtility, right: TerminalUtility) -> bool:
    return compare_terminal_utilities(left, right) >= 0


def _is_at_most(left: TerminalUtility, right: TerminalUtility) -> bool:
    return compare_terminal_utilities(left, right) <= 0


def _search(
    state: ExactSearchState,
    *,
    depth: int,
    alpha: TerminalUtility | None,
    beta: TerminalUtility | None,
    context: _SearchContext,
) -> TerminalUtility:
    cached = context.transposition_table.get(state)
    if cached is not None:
        context.depth_reached = max(context.depth_reached, depth)
        return cached

    context.begin_uncached_evaluation(depth)
    if state.is_terminal:
        utility = build_exact_terminal_utility(
            state=state,
            local_side=context.local_side,
        )
        context.transposition_table[state] = utility
        return utility
    if depth >= context.requested_budget.max_depth_plies:
        raise _SearchAborted("depth_budget_exhausted")

    original_alpha = alpha
    original_beta = beta
    actor_side = get_player_side(state.next_player, state.declarer_player)
    maximizing = actor_side == context.local_side
    best: TerminalUtility | None = None

    for card in get_exact_search_legal_cards(state):
        child = apply_exact_search_card(state, card).next_state
        utility = _search(
            child,
            depth=depth + 1,
            alpha=alpha,
            beta=beta,
            context=context,
        )
        if (
            best is None
            or (maximizing and compare_terminal_utilities(utility, best) > 0)
            or (not maximizing and compare_terminal_utilities(utility, best) < 0)
        ):
            best = utility

        if maximizing:
            if alpha is None or compare_terminal_utilities(best, alpha) > 0:
                alpha = best
            if beta is not None and _is_at_least(best, beta):
                break
        else:
            if beta is None or compare_terminal_utilities(best, beta) < 0:
                beta = best
            if alpha is not None and _is_at_most(best, alpha):
                break

    if best is None:
        raise ValueError("Non-terminal exact search state has no legal cards.")

    is_upper_bound = original_alpha is not None and _is_at_most(best, original_alpha)
    is_lower_bound = original_beta is not None and _is_at_least(best, original_beta)
    if not is_upper_bound and not is_lower_bound:
        context.transposition_table[state] = best
    return best


def _placeholder_candidates(
    legal_cards: tuple[str, ...],
    game_type: str,
) -> tuple[AggregateSearchCandidateResult, ...]:
    return rank_search_candidate_results(
        tuple(
            AggregateSearchCandidateResult(
                card=card,
                rank=1,
                is_recommended=False,
                completed_world_count=0,
                local_contract_success_count=0,
                local_contract_success_rate=None,
                mean_local_side_game_score=None,
                mean_local_side_card_point_margin=None,
            )
            for card in legal_cards
        ),
        game_type,
        recommend=False,
    )


def _unavailable_result(
    *,
    state: ExactSearchState,
    requested_budget: RequestedSearchBudget,
    reason: str,
) -> BoundedSearchResult:
    return BoundedSearchResult(
        schema_version=BOUNDED_SEARCH_SCHEMA_VERSION,
        analysis_method=BOUNDED_SEARCH_ANALYSIS_METHOD,
        search_method=PERFECT_INFORMATION_MINIMAX_METHOD,
        game_type=state.declaration.game_type,
        status="unavailable",
        stop_reason=reason,
        world_coverage="none",
        solution_claim="none",
        terminal_utility_version=TERMINAL_UTILITY_VERSION,
        requested_budget=requested_budget,
        consumed_budget=ConsumedSearchBudget(0, 0, 0, 0, 0, 0, 0),
        compatible_world_count=None,
        candidate_results=(),
        recommended_card=None,
        fallback_used=False,
        fallback_method=None,
    )


def _incomplete_result(
    *,
    state: ExactSearchState,
    requested_budget: RequestedSearchBudget,
    context: _SearchContext,
    legal_cards: tuple[str, ...],
    reason: str,
) -> BoundedSearchResult:
    status = "timeout" if reason == "wall_clock_timeout" else "partial"
    claims = {
        "wall_clock_timeout": "none",
        "node_budget_exhausted": "node_limited_partial",
        "depth_budget_exhausted": "depth_limited_per_selected_world",
    }
    return BoundedSearchResult(
        schema_version=BOUNDED_SEARCH_SCHEMA_VERSION,
        analysis_method=BOUNDED_SEARCH_ANALYSIS_METHOD,
        search_method=PERFECT_INFORMATION_MINIMAX_METHOD,
        game_type=state.declaration.game_type,
        status=status,
        stop_reason=reason,
        world_coverage="single_exact_world",
        solution_claim=claims[reason],
        terminal_utility_version=TERMINAL_UTILITY_VERSION,
        requested_budget=requested_budget,
        consumed_budget=ConsumedSearchBudget(
            depth_reached=context.depth_reached,
            nodes_expanded=context.nodes_expanded,
            selected_world_count=1,
            completed_world_count=0,
            sampled_world_count=0,
            unique_sampled_world_count=0,
            wall_clock_elapsed_ms=context.elapsed_ms(),
        ),
        compatible_world_count=1,
        candidate_results=_placeholder_candidates(legal_cards, state.declaration.game_type),
        recommended_card=None,
        fallback_used=False,
        fallback_method=None,
    )


def _has_supported_terminal_utility_inputs(state: ExactSearchState) -> bool:
    declaration = state.declaration
    if declaration.bid_value is None:
        return False
    if declaration.game_type != "null":
        return declaration.matadors is not None

    game_value = build_game_value_summary(declaration)
    overbid = build_overbid_summary(
        game_value_summary=game_value,
        bid_value=declaration.bid_value,
        game_end_reason="normal_completion",
    )
    return overbid["is_overbid"] is False


def solve_perfect_information_minimax(
    *,
    state: ExactSearchState,
    perspective_player: str,
    requested_budget: RequestedSearchBudget,
) -> BoundedSearchResult:
    """Solves one exact late Suit, Grand, or Null world with deterministic Minimax."""
    if not isinstance(state, ExactSearchState):
        raise ValueError("state must be a valid ExactSearchState.")
    if not isinstance(requested_budget, RequestedSearchBudget):
        raise ValueError("requested_budget must be a valid RequestedSearchBudget.")
    if perspective_player not in VALID_CONCRETE_PLAYERS:
        raise ValueError("perspective_player must be a concrete player.")

    game_type = state.declaration.game_type
    if game_type not in {*SUIT_GAME_TYPES, "grand", "null"}:
        return _unavailable_result(
            state=state,
            requested_budget=requested_budget,
            reason="unsupported_game_type",
        )
    if state.is_terminal:
        return _unavailable_result(
            state=state,
            requested_budget=requested_budget,
            reason="game_already_complete",
        )
    if perspective_player != state.next_player:
        return _unavailable_result(
            state=state,
            requested_budget=requested_budget,
            reason="local_player_not_to_act",
        )
    if not _has_supported_terminal_utility_inputs(state):
        return _unavailable_result(
            state=state,
            requested_budget=requested_budget,
            reason="missing_terminal_utility_inputs",
        )
    remaining_trick_limit = min(
        PERFECT_INFORMATION_MAX_REMAINING_TRICKS,
        requested_budget.max_remaining_tricks,
    )
    if state.remaining_tricks > remaining_trick_limit:
        return _unavailable_result(
            state=state,
            requested_budget=requested_budget,
            reason="remaining_trick_limit_exceeded",
        )
    legal_cards = get_exact_search_legal_cards(state)
    if not legal_cards:
        return _unavailable_result(
            state=state,
            requested_budget=requested_budget,
            reason="no_legal_cards",
        )

    local_side = get_player_side(perspective_player, state.declarer_player)
    if local_side is None:
        raise ValueError("Exact Minimax requires concrete side ownership.")
    context = _SearchContext(
        local_side=local_side,
        requested_budget=requested_budget,
        started_at=_monotonic(),
        transposition_table={},
    )
    try:
        context.begin_uncached_evaluation(depth=0)
        utilities = []
        for card in legal_cards:
            child = apply_exact_search_card(state, card).next_state
            utilities.append(
                (
                    card,
                    _search(
                        child,
                        depth=1,
                        alpha=None,
                        beta=None,
                        context=context,
                    ),
                )
            )
    except _SearchAborted as aborted:
        return _incomplete_result(
            state=state,
            requested_budget=requested_budget,
            context=context,
            legal_cards=legal_cards,
            reason=aborted.reason,
        )

    candidates = rank_search_candidate_results(
        tuple(
            AggregateSearchCandidateResult(
                card=card,
                rank=1,
                is_recommended=False,
                completed_world_count=1,
                local_contract_success_count=int(utility.local_contract_success),
                local_contract_success_rate=float(utility.local_contract_success),
                mean_local_side_game_score=float(utility.local_side_game_score),
                mean_local_side_card_point_margin=(
                    float(utility.local_side_card_point_margin)
                    if utility.local_side_card_point_margin is not None
                    else None
                ),
            )
            for card, utility in utilities
        ),
        game_type,
        recommend=True,
    )
    return BoundedSearchResult(
        schema_version=BOUNDED_SEARCH_SCHEMA_VERSION,
        analysis_method=BOUNDED_SEARCH_ANALYSIS_METHOD,
        search_method=PERFECT_INFORMATION_MINIMAX_METHOD,
        game_type=game_type,
        status="complete",
        stop_reason="completed",
        world_coverage="single_exact_world",
        solution_claim="exact_per_selected_world",
        terminal_utility_version=TERMINAL_UTILITY_VERSION,
        requested_budget=requested_budget,
        consumed_budget=ConsumedSearchBudget(
            depth_reached=context.depth_reached,
            nodes_expanded=context.nodes_expanded,
            selected_world_count=1,
            completed_world_count=1,
            sampled_world_count=0,
            unique_sampled_world_count=0,
            wall_clock_elapsed_ms=context.elapsed_ms(),
        ),
        compatible_world_count=1,
        candidate_results=candidates,
        recommended_card=candidates[0].card,
        fallback_used=False,
        fallback_method=None,
    )
