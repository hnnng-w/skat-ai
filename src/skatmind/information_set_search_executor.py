from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field

from skatmind.bounded_search_result import (
    AggregateSearchCandidateResult,
    rank_search_candidate_results,
)
from skatmind.errors import SkatMindInvariantError
from skatmind.exact_terminal_utility import build_exact_terminal_utility
from skatmind.information_set_search_contracts import (
    BOUNDED_INFORMATION_SET_POLICY_SEARCH_METHOD,
    INFORMATION_SET_SEARCH_ANALYSIS_METHOD,
    INFORMATION_SET_SEARCH_RESULT_VERSION,
    InformationSetControlledPolicyDecisionV1,
    InformationSetSearchBudgetV1,
    InformationSetSearchConsumedBudgetV1,
    InformationSetSearchPolicySettingsV1,
    InformationSetSearchResultV1,
    build_unavailable_information_set_search_result_v1,
)
from skatmind.information_set_search_policy import (
    select_information_set_fixed_policy_card_v1,
)
from skatmind.information_set_search_preparation import (
    InformationSetSearchPreparationV1,
    validate_information_set_search_preparation_v1,
)
from skatmind.information_set_search_state import (
    InformationSetSearchObservationV1,
    InformationSetSearchWorldStateV1,
    apply_information_set_search_card_v1,
    build_information_set_search_observation_v1,
)
from skatmind.terminal_utility import TERMINAL_UTILITY_VERSION, TerminalUtility

INFORMATION_SET_SEARCH_EXECUTOR_VERSION = 1
INFORMATION_SET_SEARCH_EXECUTION_ALGORITHM = "selected_world_information_set_best_response_v1"

INFORMATION_SET_SEARCH_EXECUTOR_POLICY = "exhaustive_selected_world_best_response"
INFORMATION_SET_SEARCH_FRONTIER_POLICY = "fixed_players_advance_until_controlled_or_terminal"
INFORMATION_SET_SEARCH_GROUPING_POLICY = "first_selected_world_unresolved_information_set"
INFORMATION_SET_SEARCH_CONTROL_ACTION_POLICY = "one_action_for_all_equal_controlled_observations"
INFORMATION_SET_SEARCH_ROOT_CANDIDATE_POLICY = (
    "evaluate_every_root_card_with_optimized_continuation"
)
INFORMATION_SET_SEARCH_CONTINGENT_POLICY = "retain_policy_table_across_counterfactual_root_branches"
INFORMATION_SET_SEARCH_AGGREGATE_POLICY = (
    "existing_terminal_utility_lexicographic_selected_draw_aggregate"
)
INFORMATION_SET_SEARCH_WEIGHT_POLICY = "selected_draws_equal_weight_with_duplicate_preservation"
INFORMATION_SET_SEARCH_TIE_POLICY = "first_canonical_best_card"
INFORMATION_SET_SEARCH_MEMOIZATION_POLICY = "invocation_local_world_and_ordered_bundle_memoization"
INFORMATION_SET_SEARCH_PARTIAL_POLICY = (
    "fully_resolved_policy_fragment_without_candidates_or_recommendation"
)
INFORMATION_SET_SEARCH_TIMEOUT_POLICY = "no_policy_claim_candidates_or_recommendation"
INFORMATION_SET_SEARCH_BUDGET_POLICY = (
    "deterministic_structural_limits_with_operational_wall_clock_cutoff"
)

_monotonic = time.monotonic


class _SearchAborted(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


@dataclass(slots=True)
class _WorldEvaluation:
    depth_plies: int
    terminal_utility: TerminalUtility | None = None
    observation: InformationSetSearchObservationV1 | None = None
    fixed_card: str | None = None
    fixed_successor: InformationSetSearchWorldStateV1 | None = None


@dataclass(frozen=True, slots=True)
class _BundleSolution:
    terminal_utilities: tuple[TerminalUtility, ...]
    controlled_policy_suffix: tuple[InformationSetControlledPolicyDecisionV1, ...]


def _merge_policy_suffixes(
    *suffixes: tuple[InformationSetControlledPolicyDecisionV1, ...],
) -> tuple[InformationSetControlledPolicyDecisionV1, ...]:
    merged: list[InformationSetControlledPolicyDecisionV1] = []
    selected: dict[InformationSetSearchObservationV1, str] = {}
    for suffix in suffixes:
        for decision in suffix:
            prior = selected.get(decision.information_set)
            if prior is not None:
                if prior != decision.selected_card:
                    raise SkatMindInvariantError(
                        "Equal controlled Information Sets produced conflicting Cards."
                    )
                continue
            selected[decision.information_set] = decision.selected_card
            merged.append(decision)
    return tuple(merged)


def _aggregate_utility_key(
    utilities: tuple[TerminalUtility, ...],
    game_type: str,
) -> tuple[int, int] | tuple[int, int, int]:
    success_count = sum(int(item.local_contract_success) for item in utilities)
    game_score_sum = sum(item.local_side_game_score for item in utilities)
    if game_type == "null":
        return success_count, game_score_sum
    margins = tuple(item.local_side_card_point_margin for item in utilities)
    if any(item is None for item in margins):
        raise SkatMindInvariantError("Suit and Grand utility aggregation requires margins.")
    return success_count, game_score_sum, sum(item for item in margins if item is not None)


@dataclass(slots=True)
class _ExecutionController:
    requested_budget: InformationSetSearchBudgetV1
    local_side: str
    policy_settings: InformationSetSearchPolicySettingsV1
    root_public_play_count: int
    started_at: float
    monotonic: Callable[[], float]
    depth_reached: int = 0
    state_nodes_evaluated: int = 0
    information_sets_evaluated: int = 0
    controlled_policy_decisions: int = 0
    fixed_policy_decisions: int = 0
    world_cache: dict[InformationSetSearchWorldStateV1, _WorldEvaluation] = field(
        default_factory=dict
    )
    bundle_memo: dict[tuple[InformationSetSearchWorldStateV1, ...], _BundleSolution] = field(
        default_factory=dict
    )
    started_information_sets: dict[InformationSetSearchObservationV1, int] = field(
        default_factory=dict
    )
    resolved_decisions: dict[
        InformationSetSearchObservationV1, InformationSetControlledPolicyDecisionV1
    ] = field(default_factory=dict)

    def current_elapsed_ms(self) -> float:
        return max(0.0, (self.monotonic() - self.started_at) * 1000)

    def elapsed_ms(self) -> int:
        return int(self.current_elapsed_ms())

    def _check_timeout(self) -> None:
        timeout = self.requested_budget.wall_clock_timeout_ms
        if timeout is not None and self.current_elapsed_ms() >= timeout:
            raise _SearchAborted("wall_clock_timeout")

    def _depth(self, state: InformationSetSearchWorldStateV1) -> int:
        public_play_count = 3 * len(state.public_completed_tricks) + len(
            state.exact_state.current_trick
        )
        depth = public_play_count - self.root_public_play_count
        if depth < 0:
            raise SkatMindInvariantError("A World State predates the prepared Search root.")
        return depth

    def evaluate_world_state(
        self,
        state: InformationSetSearchWorldStateV1,
    ) -> _WorldEvaluation:
        cached = self.world_cache.get(state)
        if cached is not None:
            return cached
        self._check_timeout()
        if self.state_nodes_evaluated >= self.requested_budget.max_state_nodes:
            raise _SearchAborted("state_node_budget_exhausted")
        self.state_nodes_evaluated += 1
        depth = self._depth(state)
        self.depth_reached = max(self.depth_reached, depth)
        if state.exact_state.is_terminal:
            evaluation = _WorldEvaluation(
                depth_plies=depth,
                terminal_utility=build_exact_terminal_utility(
                    state=state.exact_state,
                    local_side=self.local_side,
                ),
            )
            self.world_cache[state] = evaluation
            return evaluation
        if depth >= self.requested_budget.max_depth_plies:
            raise _SearchAborted("depth_budget_exhausted")
        evaluation = _WorldEvaluation(
            depth_plies=depth,
            observation=build_information_set_search_observation_v1(state),
        )
        self.world_cache[state] = evaluation
        return evaluation

    def begin_information_set(
        self,
        information_set: InformationSetSearchObservationV1,
    ) -> None:
        if information_set in self.started_information_sets:
            return
        self._check_timeout()
        if self.information_sets_evaluated >= (self.requested_budget.max_information_sets):
            raise _SearchAborted("information_set_budget_exhausted")
        self.started_information_sets[information_set] = len(self.started_information_sets)
        self.information_sets_evaluated += 1

    def resolve_decision(
        self,
        decision: InformationSetControlledPolicyDecisionV1,
    ) -> None:
        if decision.information_set not in self.started_information_sets:
            raise SkatMindInvariantError(
                "A controlled Decision was resolved before its Information Set started."
            )
        retained = self.resolved_decisions.get(decision.information_set)
        if retained is not None:
            if retained != decision:
                raise SkatMindInvariantError(
                    "Equal controlled Information Sets produced conflicting Decisions."
                )
            return
        self.resolved_decisions[decision.information_set] = decision
        self.controlled_policy_decisions += 1

    def retained_policy(self) -> tuple[InformationSetControlledPolicyDecisionV1, ...]:
        return tuple(
            self.resolved_decisions[information_set]
            for information_set in self.started_information_sets
            if information_set in self.resolved_decisions
        )


def _advance_fixed_players(
    state: InformationSetSearchWorldStateV1,
    controller: _ExecutionController,
) -> InformationSetSearchWorldStateV1:
    current = state
    while True:
        evaluation = controller.evaluate_world_state(current)
        if evaluation.terminal_utility is not None:
            return current
        observation = evaluation.observation
        if observation is None:
            raise SkatMindInvariantError("A non-terminal World lacks an actor Observation.")
        if observation.actor_player == "me":
            return current
        if evaluation.fixed_successor is None:
            card = select_information_set_fixed_policy_card_v1(
                observation=observation,
                policy_settings=controller.policy_settings,
            )
            evaluation.fixed_card = card
            evaluation.fixed_successor = apply_information_set_search_card_v1(
                current,
                card,
            )
            controller.fixed_policy_decisions += 1
        current = evaluation.fixed_successor


def _apply_controlled_card(
    states: tuple[InformationSetSearchWorldStateV1, ...],
    grouped_indexes: tuple[int, ...],
    card: str,
) -> tuple[InformationSetSearchWorldStateV1, ...]:
    grouped = set(grouped_indexes)
    return tuple(
        apply_information_set_search_card_v1(state, card) if index in grouped else state
        for index, state in enumerate(states)
    )


def _solve_bundle(
    states: tuple[InformationSetSearchWorldStateV1, ...],
    controller: _ExecutionController,
) -> _BundleSolution:
    cached = controller.bundle_memo.get(states)
    if cached is not None:
        return cached

    frontier = tuple(_advance_fixed_players(state, controller) for state in states)
    if frontier != states:
        cached_frontier = controller.bundle_memo.get(frontier)
        solution = cached_frontier or _solve_bundle(frontier, controller)
        controller.bundle_memo[states] = solution
        return solution

    evaluations = tuple(controller.evaluate_world_state(state) for state in frontier)
    if all(item.terminal_utility is not None for item in evaluations):
        solution = _BundleSolution(
            terminal_utilities=tuple(
                item.terminal_utility for item in evaluations if item.terminal_utility is not None
            ),
            controlled_policy_suffix=(),
        )
        if len(solution.terminal_utilities) != len(frontier):
            raise SkatMindInvariantError("A terminal World bundle lost selected-draw weight.")
        controller.bundle_memo[states] = solution
        return solution

    first_index = next(
        index for index, evaluation in enumerate(evaluations) if evaluation.terminal_utility is None
    )
    information_set = evaluations[first_index].observation
    if information_set is None or information_set.actor_player != "me":
        raise SkatMindInvariantError("The controlled frontier does not belong to me.")
    grouped_indexes = tuple(
        index
        for index, evaluation in enumerate(evaluations)
        if evaluation.observation == information_set
    )

    retained = controller.resolved_decisions.get(information_set)
    if retained is not None:
        if retained.reached_world_count != len(grouped_indexes):
            raise SkatMindInvariantError(
                "A repeated controlled Information Set changed its reached World count."
            )
        child = _solve_bundle(
            _apply_controlled_card(frontier, grouped_indexes, retained.selected_card),
            controller,
        )
        solution = _BundleSolution(
            terminal_utilities=child.terminal_utilities,
            controlled_policy_suffix=_merge_policy_suffixes(
                (retained,), child.controlled_policy_suffix
            ),
        )
        controller.bundle_memo[states] = solution
        return solution
    if information_set in controller.started_information_sets:
        raise SkatMindInvariantError(
            "A controlled Information Set recurred before its Decision resolved."
        )
    controller.begin_information_set(information_set)

    solutions_by_card: list[tuple[str, _BundleSolution]] = []
    best_card: str | None = None
    best_solution: _BundleSolution | None = None
    best_key: tuple[int, int] | tuple[int, int, int] | None = None
    for card in information_set.legal_cards:
        child = _solve_bundle(
            _apply_controlled_card(frontier, grouped_indexes, card),
            controller,
        )
        solutions_by_card.append((card, child))
        key = _aggregate_utility_key(child.terminal_utilities, information_set.game_type)
        if best_key is None or key > best_key:
            best_card = card
            best_solution = child
            best_key = key
    if best_card is None or best_solution is None:
        raise SkatMindInvariantError("A controlled Information Set produced no legal outcome.")

    decision = InformationSetControlledPolicyDecisionV1(
        information_set=information_set,
        selected_card=best_card,
        reached_world_count=len(grouped_indexes),
        depth_plies=evaluations[first_index].depth_plies,
    )
    controller.resolve_decision(decision)
    solution = _BundleSolution(
        terminal_utilities=best_solution.terminal_utilities,
        controlled_policy_suffix=_merge_policy_suffixes(
            (decision,),
            *(child.controlled_policy_suffix for _, child in solutions_by_card),
        ),
    )
    controller.bundle_memo[states] = solution
    return solution


def _build_candidates(
    *,
    solutions_by_card: tuple[tuple[str, _BundleSolution], ...],
    selected_world_count: int,
    game_type: str,
) -> tuple[AggregateSearchCandidateResult, ...]:
    candidates = []
    for card, solution in solutions_by_card:
        utilities = solution.terminal_utilities
        if len(utilities) != selected_world_count:
            raise SkatMindInvariantError("A root Candidate lost selected-draw weight.")
        success_count = sum(int(item.local_contract_success) for item in utilities)
        game_score_sum = sum(item.local_side_game_score for item in utilities)
        margin_sum = sum(item.local_side_card_point_margin or 0 for item in utilities)
        candidates.append(
            AggregateSearchCandidateResult(
                card=card,
                rank=1,
                is_recommended=False,
                completed_world_count=selected_world_count,
                local_contract_success_count=success_count,
                local_contract_success_rate=success_count / selected_world_count,
                mean_local_side_game_score=game_score_sum / selected_world_count,
                mean_local_side_card_point_margin=(
                    None if game_type == "null" else margin_sum / selected_world_count
                ),
            )
        )
    return rank_search_candidate_results(
        tuple(candidates),
        game_type,
        recommend=True,
    )


def _consumed_budget(
    *,
    controller: _ExecutionController,
    preparation: InformationSetSearchPreparationV1,
    complete: bool,
) -> InformationSetSearchConsumedBudgetV1:
    selection = preparation.world_selection
    if selection is None:
        raise SkatMindInvariantError("Available execution lost its World selection.")
    return InformationSetSearchConsumedBudgetV1(
        depth_reached=controller.depth_reached,
        state_nodes_evaluated=controller.state_nodes_evaluated,
        information_sets_evaluated=controller.information_sets_evaluated,
        controlled_policy_decisions=controller.controlled_policy_decisions,
        fixed_policy_decisions=controller.fixed_policy_decisions,
        selected_world_count=selection.selected_world_count,
        completed_world_count=selection.selected_world_count if complete else 0,
        sampled_world_count=selection.sampled_world_count,
        unique_sampled_world_count=selection.unique_sampled_world_count,
        wall_clock_elapsed_ms=controller.elapsed_ms(),
    )


def _build_incomplete_result(
    *,
    preparation: InformationSetSearchPreparationV1,
    controller: _ExecutionController,
    reason: str,
) -> InformationSetSearchResultV1:
    selection = preparation.world_selection
    if selection is None:
        raise SkatMindInvariantError("Available execution lost its World selection.")
    timeout = reason == "wall_clock_timeout"
    try:
        return InformationSetSearchResultV1(
            information_set_search_result_version=INFORMATION_SET_SEARCH_RESULT_VERSION,
            analysis_method=INFORMATION_SET_SEARCH_ANALYSIS_METHOD,
            search_method=BOUNDED_INFORMATION_SET_POLICY_SEARCH_METHOD,
            game_type=preparation.request.information_view.game_type,
            status="timeout" if timeout else "partial",
            stop_reason=reason,
            world_coverage=selection.world_coverage,
            policy_claim="none" if timeout else "common_policy_prefix",
            policy_consistency=(
                "not_assessed" if timeout else "controlled_player_information_set_consistent"
            ),
            terminal_utility_version=TERMINAL_UTILITY_VERSION,
            requested_budget=preparation.request.requested_budget,
            consumed_budget=_consumed_budget(
                controller=controller,
                preparation=preparation,
                complete=False,
            ),
            compatible_world_count=selection.compatible_world_count,
            candidate_results=(),
            recommended_card=None,
            controlled_policy=() if timeout else controller.retained_policy(),
            fixed_policy_settings=preparation.request.policy_settings,
        )
    except ValueError as error:
        raise SkatMindInvariantError(
            "Information-set Search produced an inconsistent incomplete Result."
        ) from error


def execute_information_set_search_v1(
    preparation: InformationSetSearchPreparationV1,
) -> InformationSetSearchResultV1:
    """Executes one bounded selected-world information-set best response."""
    if type(preparation) is not InformationSetSearchPreparationV1:
        raise ValueError("preparation must be an InformationSetSearchPreparationV1.")
    validate_information_set_search_preparation_v1(preparation)
    if preparation.status == "unavailable":
        compatible_world_count = (
            preparation.world_selection.compatible_world_count
            if preparation.world_selection is not None
            else None
        )
        return build_unavailable_information_set_search_result_v1(
            request=preparation.request,
            unavailable_reason=preparation.unavailable_reason,
            compatible_world_count=compatible_world_count,
        )

    selection = preparation.world_selection
    root_information_set = preparation.root_information_set
    local_side = preparation.request.information_view.local_side
    if selection is None or root_information_set is None or local_side is None:
        raise SkatMindInvariantError("Available execution lacks required root facts.")
    root_public_play_count = 3 * len(preparation.request.information_view.completed_tricks) + len(
        preparation.request.information_view.current_trick
    )
    controller = _ExecutionController(
        requested_budget=preparation.request.requested_budget,
        local_side=local_side,
        policy_settings=preparation.request.policy_settings,
        root_public_play_count=root_public_play_count,
        started_at=_monotonic(),
        monotonic=_monotonic,
    )

    try:
        root_evaluations = tuple(
            controller.evaluate_world_state(state) for state in preparation.world_states
        )
        if any(item.observation != root_information_set for item in root_evaluations):
            raise SkatMindInvariantError("Prepared root Information Sets changed at execution.")
        controller.begin_information_set(root_information_set)

        root_solutions: list[tuple[str, _BundleSolution]] = []
        best_card: str | None = None
        best_key: tuple[int, int] | tuple[int, int, int] | None = None
        for card in preparation.root_legal_cards:
            solution = _solve_bundle(
                tuple(
                    apply_information_set_search_card_v1(state, card)
                    for state in preparation.world_states
                ),
                controller,
            )
            root_solutions.append((card, solution))
            key = _aggregate_utility_key(
                solution.terminal_utilities,
                preparation.request.information_view.game_type,
            )
            if best_key is None or key > best_key:
                best_card = card
                best_key = key
        if best_card is None:
            raise SkatMindInvariantError("Root execution produced no Candidate.")

        root_decision = InformationSetControlledPolicyDecisionV1(
            information_set=root_information_set,
            selected_card=best_card,
            reached_world_count=selection.selected_world_count,
            depth_plies=0,
        )
        controller.resolve_decision(root_decision)
    except _SearchAborted as aborted:
        return _build_incomplete_result(
            preparation=preparation,
            controller=controller,
            reason=aborted.reason,
        )

    candidates = _build_candidates(
        solutions_by_card=tuple(root_solutions),
        selected_world_count=selection.selected_world_count,
        game_type=preparation.request.information_view.game_type,
    )
    if candidates[0].card != best_card:
        raise SkatMindInvariantError(
            "Root aggregate objective and existing Candidate ranking disagree."
        )
    try:
        return InformationSetSearchResultV1(
            information_set_search_result_version=INFORMATION_SET_SEARCH_RESULT_VERSION,
            analysis_method=INFORMATION_SET_SEARCH_ANALYSIS_METHOD,
            search_method=BOUNDED_INFORMATION_SET_POLICY_SEARCH_METHOD,
            game_type=preparation.request.information_view.game_type,
            status="complete",
            stop_reason="completed",
            world_coverage=selection.world_coverage,
            policy_claim="exact_selected_world_policy",
            policy_consistency="controlled_player_information_set_consistent",
            terminal_utility_version=TERMINAL_UTILITY_VERSION,
            requested_budget=preparation.request.requested_budget,
            consumed_budget=_consumed_budget(
                controller=controller,
                preparation=preparation,
                complete=True,
            ),
            compatible_world_count=selection.compatible_world_count,
            candidate_results=candidates,
            recommended_card=candidates[0].card,
            controlled_policy=controller.retained_policy(),
            fixed_policy_settings=preparation.request.policy_settings,
        )
    except ValueError as error:
        raise SkatMindInvariantError(
            "Information-set Search produced an inconsistent complete Result."
        ) from error
