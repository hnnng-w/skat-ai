import time
from dataclasses import dataclass

from skat_ai.bounded_search_information import (
    SearchInformationView,
    assess_search_eligibility,
)
from skat_ai.bounded_search_result import (
    BOUNDED_SEARCH_ANALYSIS_METHOD,
    BOUNDED_SEARCH_SCHEMA_VERSION,
    AggregateSearchCandidateResult,
    BoundedSearchResult,
    ConsumedSearchBudget,
    RequestedSearchBudget,
    rank_search_candidate_results,
)
from skat_ai.compatible_search_world import (
    CompatibleSearchWorldSelection,
    build_compatible_search_world_space,
    select_compatible_search_worlds,
)
from skat_ai.perfect_information_minimax import (
    PERFECT_INFORMATION_MAX_REMAINING_TRICKS,
    _evaluate_exact_world_root_utilities,
    _SearchAborted,
    _SearchExecutionController,
)
from skat_ai.side_ownership import get_player_side
from skat_ai.terminal_utility import TERMINAL_UTILITY_VERSION, TerminalUtility

COMPATIBLE_WORLD_MINIMAX_METHOD = "compatible_world_minimax_v1"

_monotonic = time.monotonic


@dataclass
class _CandidateTotals:
    success_count: int = 0
    game_score: int = 0
    card_point_margin: int = 0


def _unavailable_result(
    *,
    information_view: SearchInformationView,
    requested_budget: RequestedSearchBudget,
    reason: str,
    compatible_world_count: int | None,
) -> BoundedSearchResult:
    return BoundedSearchResult(
        schema_version=BOUNDED_SEARCH_SCHEMA_VERSION,
        analysis_method=BOUNDED_SEARCH_ANALYSIS_METHOD,
        search_method=COMPATIBLE_WORLD_MINIMAX_METHOD,
        game_type=information_view.game_type,
        status="unavailable",
        stop_reason=reason,
        world_coverage="none",
        solution_claim="none",
        terminal_utility_version=TERMINAL_UTILITY_VERSION,
        requested_budget=requested_budget,
        consumed_budget=ConsumedSearchBudget(0, 0, 0, 0, 0, 0, 0),
        compatible_world_count=compatible_world_count,
        candidate_results=(),
        recommended_card=None,
        fallback_used=False,
        fallback_method=None,
    )


def _aggregate_candidates(
    *,
    legal_cards: tuple[str, ...],
    totals_by_card: dict[str, _CandidateTotals],
    completed_world_count: int,
    game_type: str,
    recommend: bool,
) -> tuple[AggregateSearchCandidateResult, ...]:
    candidates = []
    for card in legal_cards:
        totals = totals_by_card[card]
        candidates.append(
            AggregateSearchCandidateResult(
                card=card,
                rank=1,
                is_recommended=False,
                completed_world_count=completed_world_count,
                local_contract_success_count=totals.success_count,
                local_contract_success_rate=(
                    totals.success_count / completed_world_count if completed_world_count else None
                ),
                mean_local_side_game_score=(
                    totals.game_score / completed_world_count if completed_world_count else None
                ),
                mean_local_side_card_point_margin=(
                    None
                    if game_type == "null" or not completed_world_count
                    else totals.card_point_margin / completed_world_count
                ),
            )
        )
    return rank_search_candidate_results(
        tuple(candidates),
        game_type,
        recommend=recommend,
    )


def _add_complete_world(
    *,
    utilities: tuple[tuple[str, TerminalUtility], ...],
    legal_cards: tuple[str, ...],
    totals_by_card: dict[str, _CandidateTotals],
    game_type: str,
) -> None:
    utilities_by_card = dict(utilities)
    if set(utilities_by_card) != set(legal_cards) or len(utilities_by_card) != len(utilities):
        raise ValueError("Exact world utilities do not match the common legal root cards.")
    for card in legal_cards:
        utility = utilities_by_card[card]
        if utility.game_type != game_type:
            raise ValueError("Exact world utility game type does not match the selection.")
        totals = totals_by_card[card]
        totals.success_count += int(utility.local_contract_success)
        totals.game_score += utility.local_side_game_score
        if utility.local_side_card_point_margin is not None:
            totals.card_point_margin += utility.local_side_card_point_margin


def _build_available_result(
    *,
    information_view: SearchInformationView,
    requested_budget: RequestedSearchBudget,
    selection: CompatibleSearchWorldSelection,
    execution_controller: _SearchExecutionController,
    completed_world_count: int,
    stop_reason: str,
    totals_by_card: dict[str, _CandidateTotals],
) -> BoundedSearchResult:
    complete = stop_reason == "completed"
    status = (
        "complete" if complete else "timeout" if stop_reason == "wall_clock_timeout" else "partial"
    )
    claims = {
        "completed": "exact_per_selected_world",
        "node_budget_exhausted": "node_limited_partial",
        "depth_budget_exhausted": "depth_limited_per_selected_world",
        "wall_clock_timeout": "none",
    }
    recommend = complete or (completed_world_count >= requested_budget.minimum_comparable_worlds)
    candidates = _aggregate_candidates(
        legal_cards=selection.legal_root_cards,
        totals_by_card=totals_by_card,
        completed_world_count=completed_world_count,
        game_type=information_view.game_type,
        recommend=recommend,
    )
    return BoundedSearchResult(
        schema_version=BOUNDED_SEARCH_SCHEMA_VERSION,
        analysis_method=BOUNDED_SEARCH_ANALYSIS_METHOD,
        search_method=COMPATIBLE_WORLD_MINIMAX_METHOD,
        game_type=information_view.game_type,
        status=status,
        stop_reason=stop_reason,
        world_coverage=selection.world_coverage,
        solution_claim=claims[stop_reason],
        terminal_utility_version=TERMINAL_UTILITY_VERSION,
        requested_budget=requested_budget,
        consumed_budget=ConsumedSearchBudget(
            depth_reached=execution_controller.depth_reached,
            nodes_expanded=execution_controller.nodes_expanded,
            selected_world_count=selection.selected_world_count,
            completed_world_count=completed_world_count,
            sampled_world_count=selection.sampled_world_count,
            unique_sampled_world_count=selection.unique_sampled_world_count,
            wall_clock_elapsed_ms=execution_controller.elapsed_ms(),
        ),
        compatible_world_count=selection.compatible_world_count,
        candidate_results=candidates,
        recommended_card=candidates[0].card if recommend else None,
        fallback_used=False,
        fallback_method=None,
    )


def solve_compatible_world_minimax(
    *,
    information_view: SearchInformationView,
    requested_budget: RequestedSearchBudget,
    random_seed: int,
) -> BoundedSearchResult:
    """Solves one frozen compatible-world sequence over a common exact prefix."""
    if not isinstance(information_view, SearchInformationView):
        raise ValueError("information_view must be a SearchInformationView.")
    if not isinstance(requested_budget, RequestedSearchBudget):
        raise ValueError("requested_budget must be a RequestedSearchBudget.")
    if isinstance(random_seed, bool) or not isinstance(random_seed, int):
        raise ValueError("random_seed must be an integer and must not be a boolean.")

    eligibility = assess_search_eligibility(
        information_view,
        min(
            PERFECT_INFORMATION_MAX_REMAINING_TRICKS,
            requested_budget.max_remaining_tricks,
        ),
    )
    if not eligibility.eligible:
        if eligibility.unavailable_reason is None:
            raise ValueError("Ineligible search requires an unavailable reason.")
        return _unavailable_result(
            information_view=information_view,
            requested_budget=requested_budget,
            reason=eligibility.unavailable_reason,
            compatible_world_count=None,
        )

    world_space = build_compatible_search_world_space(information_view)
    selection = select_compatible_search_worlds(
        world_space=world_space,
        requested_budget=requested_budget,
        random_seed=random_seed,
    )
    if not selection.available:
        return _unavailable_result(
            information_view=information_view,
            requested_budget=requested_budget,
            reason="incompatible_world_space",
            compatible_world_count=0,
        )

    return solve_compatible_world_minimax_on_selection_v1(
        information_view=information_view,
        requested_budget=requested_budget,
        selection=selection,
    )


def solve_compatible_world_minimax_on_selection_v1(
    *,
    information_view: SearchInformationView,
    requested_budget: RequestedSearchBudget,
    selection: CompatibleSearchWorldSelection,
) -> BoundedSearchResult:
    """Solves exactly one retained compatible-world sequence without reselection."""
    if not isinstance(information_view, SearchInformationView):
        raise ValueError("information_view must be a SearchInformationView.")
    if not isinstance(requested_budget, RequestedSearchBudget):
        raise ValueError("requested_budget must be a RequestedSearchBudget.")
    if type(selection) is not CompatibleSearchWorldSelection:
        raise ValueError("selection must be a CompatibleSearchWorldSelection.")
    selection.__post_init__()
    if (
        selection.selected_world_count > requested_budget.max_selected_worlds
        or selection.sampled_world_count > requested_budget.max_sampled_worlds
    ):
        raise ValueError("The retained selection exceeds the requested PIMC budget.")
    if not selection.available:
        return _unavailable_result(
            information_view=information_view,
            requested_budget=requested_budget,
            reason="incompatible_world_space",
            compatible_world_count=selection.compatible_world_count,
        )

    expected_current_trick = tuple(
        (play.player, play.card) for play in information_view.current_trick
    )
    expected_hand_sizes = tuple(
        (item.player, item.card_count) for item in information_view.remaining_hand_sizes
    )
    for state in selection.exact_states:
        if (
            state.declaration != information_view.declaration
            or state.declarer_player != information_view.declarer_player
            or state.next_player != information_view.next_player
            or state.hand_for(information_view.perspective_player)
            != information_view.local_remaining_hand
            or tuple((play.player, play.card) for play in state.current_trick)
            != expected_current_trick
            or state.declarer_trick_points != information_view.declarer_points
            or state.defender_trick_points != information_view.defender_points
            or state.declarer_completed_tricks
            != information_view.declarer_trick_count
            or state.defender_completed_tricks
            != information_view.defender_trick_count
            or tuple(
                (player, len(state.hand_for(player)))
                for player in ("me", "left", "right")
            )
            != expected_hand_sizes
            or not set(information_view.known_skat_cards).issubset(
                state.out_of_play_cards
            )
        ):
            raise ValueError(
                "The retained selection does not belong to the information view."
            )

    local_side = get_player_side(
        information_view.perspective_player,
        information_view.declarer_player,
    )
    if local_side is None:
        raise ValueError("Compatible-world Minimax requires concrete side ownership.")
    execution_controller = _SearchExecutionController(
        requested_budget=requested_budget,
        started_at=_monotonic(),
        monotonic=_monotonic,
    )
    totals_by_card = {card: _CandidateTotals() for card in selection.legal_root_cards}
    completed_world_count = 0
    stop_reason = "completed"
    for state in selection.exact_states:
        try:
            utilities = _evaluate_exact_world_root_utilities(
                state=state,
                local_side=local_side,
                execution_controller=execution_controller,
            )
        except _SearchAborted as aborted:
            stop_reason = aborted.reason
            break
        _add_complete_world(
            utilities=utilities,
            legal_cards=selection.legal_root_cards,
            totals_by_card=totals_by_card,
            game_type=information_view.game_type,
        )
        completed_world_count += 1

    return _build_available_result(
        information_view=information_view,
        requested_budget=requested_budget,
        selection=selection,
        execution_controller=execution_controller,
        completed_world_count=completed_world_count,
        stop_reason=stop_reason,
        totals_by_card=totals_by_card,
    )
