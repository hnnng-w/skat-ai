import ast
from dataclasses import fields, replace
from pathlib import Path

import pytest
from test_information_set_search_state_and_preparation import _find_view, _request

import skatmind.information_set_search_executor as executor_module
import skatmind.information_set_search_preparation as preparation_module
from skatmind.errors import SkatMindInvariantError
from skatmind.exact_search_state import build_exact_search_state
from skatmind.information_set_search_contracts import (
    INFORMATION_SET_SEARCH_UNAVAILABLE_REASONS,
)
from skatmind.information_set_search_executor import (
    INFORMATION_SET_SEARCH_AGGREGATE_POLICY,
    INFORMATION_SET_SEARCH_BUDGET_POLICY,
    INFORMATION_SET_SEARCH_CONTINGENT_POLICY,
    INFORMATION_SET_SEARCH_CONTROL_ACTION_POLICY,
    INFORMATION_SET_SEARCH_EXECUTION_ALGORITHM,
    INFORMATION_SET_SEARCH_EXECUTOR_POLICY,
    INFORMATION_SET_SEARCH_EXECUTOR_VERSION,
    INFORMATION_SET_SEARCH_FRONTIER_POLICY,
    INFORMATION_SET_SEARCH_GROUPING_POLICY,
    INFORMATION_SET_SEARCH_MEMOIZATION_POLICY,
    INFORMATION_SET_SEARCH_PARTIAL_POLICY,
    INFORMATION_SET_SEARCH_ROOT_CANDIDATE_POLICY,
    INFORMATION_SET_SEARCH_TIE_POLICY,
    INFORMATION_SET_SEARCH_TIMEOUT_POLICY,
    INFORMATION_SET_SEARCH_WEIGHT_POLICY,
    execute_information_set_search_v1,
)
from skatmind.information_set_search_preparation import (
    InformationSetSearchPreparationV1,
    prepare_information_set_search_v1,
    validate_information_set_search_preparation_v1,
)
from skatmind.information_set_search_state import (
    InformationSetSearchObservationV1,
    InformationSetSearchWorldStateV1,
    build_information_set_search_observation_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _preparation(
    *,
    remaining_tricks: int = 2,
    hand_game: bool = False,
) -> InformationSetSearchPreparationV1:
    view, _ = _find_view(
        actor="me",
        remaining_tricks=remaining_tricks,
        hand_game=hand_game,
        public_players=() if hand_game else ("left", "right"),
    )
    return prepare_information_set_search_v1(_request(view, max_selected_worlds=1))


def _with_budget(
    preparation: InformationSetSearchPreparationV1,
    **changes: int | None,
) -> InformationSetSearchPreparationV1:
    request = replace(
        preparation.request,
        requested_budget=replace(
            preparation.request.requested_budget,
            **changes,
        ),
    )
    return prepare_information_set_search_v1(request)


def _forged_preparation(
    preparation: InformationSetSearchPreparationV1,
    **changes: object,
) -> InformationSetSearchPreparationV1:
    values = {item.name: getattr(preparation, item.name) for item in fields(preparation)}
    return InformationSetSearchPreparationV1._from_validated(**(values | changes))


def test_executor_metadata_is_exact_and_stable() -> None:
    assert INFORMATION_SET_SEARCH_EXECUTOR_VERSION == 1
    assert INFORMATION_SET_SEARCH_EXECUTION_ALGORITHM == (
        "selected_world_information_set_best_response_v1"
    )
    assert (
        INFORMATION_SET_SEARCH_EXECUTOR_POLICY,
        INFORMATION_SET_SEARCH_FRONTIER_POLICY,
        INFORMATION_SET_SEARCH_GROUPING_POLICY,
        INFORMATION_SET_SEARCH_CONTROL_ACTION_POLICY,
        INFORMATION_SET_SEARCH_ROOT_CANDIDATE_POLICY,
        INFORMATION_SET_SEARCH_CONTINGENT_POLICY,
        INFORMATION_SET_SEARCH_AGGREGATE_POLICY,
        INFORMATION_SET_SEARCH_WEIGHT_POLICY,
        INFORMATION_SET_SEARCH_TIE_POLICY,
        INFORMATION_SET_SEARCH_MEMOIZATION_POLICY,
        INFORMATION_SET_SEARCH_PARTIAL_POLICY,
        INFORMATION_SET_SEARCH_TIMEOUT_POLICY,
        INFORMATION_SET_SEARCH_BUDGET_POLICY,
    ) == (
        "exhaustive_selected_world_best_response",
        "fixed_players_advance_until_controlled_or_terminal",
        "first_selected_world_unresolved_information_set",
        "one_action_for_all_equal_controlled_observations",
        "evaluate_every_root_card_with_optimized_continuation",
        "retain_policy_table_across_counterfactual_root_branches",
        "existing_terminal_utility_lexicographic_selected_draw_aggregate",
        "selected_draws_equal_weight_with_duplicate_preservation",
        "first_canonical_best_card",
        "invocation_local_world_and_ordered_bundle_memoization",
        "fully_resolved_policy_fragment_without_candidates_or_recommendation",
        "no_policy_claim_candidates_or_recommendation",
        "deterministic_structural_limits_with_operational_wall_clock_cutoff",
    )
    assert not isinstance(INFORMATION_SET_SEARCH_EXECUTOR_VERSION, bool)


def test_complete_execution_evaluates_every_root_card_and_retains_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preparation = _preparation()
    assert preparation.root_information_set is not None
    terminal_calls = []
    original_terminal = executor_module.build_exact_terminal_utility

    def counted_terminal(**kwargs):
        terminal_calls.append(kwargs)
        return original_terminal(**kwargs)

    monkeypatch.setattr(
        executor_module,
        "build_exact_terminal_utility",
        counted_terminal,
    )
    original = preparation.to_dict()
    result = execute_information_set_search_v1(preparation)

    assert result.status == "complete"
    assert result.stop_reason == "completed"
    assert result.policy_claim == "exact_selected_world_policy"
    assert result.policy_consistency == ("controlled_player_information_set_consistent")
    assert {item.card for item in result.candidate_results} == set(preparation.root_legal_cards)
    assert result.recommended_card == result.candidate_results[0].card
    assert result.controlled_policy[0].information_set == (preparation.root_information_set)
    assert result.controlled_policy[0].selected_card == result.recommended_card
    assert result.controlled_policy[0].reached_world_count == 1
    assert result.controlled_policy[0].depth_plies == 0
    assert len(result.controlled_policy) == (result.consumed_budget.controlled_policy_decisions)
    assert len(result.controlled_policy) == (result.consumed_budget.information_sets_evaluated)
    assert result.consumed_budget.completed_world_count == 1
    assert result.consumed_budget.depth_reached == 6
    assert result.consumed_budget.fixed_policy_decisions > 0
    assert terminal_calls
    assert all(call["local_side"] == "declarer" for call in terminal_calls)
    assert preparation.to_dict() == original


def test_sampled_duplicate_draws_keep_weight_but_reuse_world_computation() -> None:
    view, _ = _find_view(actor="me", remaining_tricks=1, hand_game=True)
    duplicate_preparation = None
    for seed in range(100):
        request = replace(
            _request(view, max_selected_worlds=4, max_sampled_worlds=4),
            world_selection_seed=seed,
        )
        candidate = prepare_information_set_search_v1(request)
        selection = candidate.world_selection
        if (
            selection is not None
            and selection.sampled_world_count == 4
            and selection.unique_sampled_world_count < 4
        ):
            duplicate_preparation = candidate
            break
    assert duplicate_preparation is not None
    selection = duplicate_preparation.world_selection
    assert selection is not None

    observations = tuple(
        build_information_set_search_observation_v1(state)
        for state in duplicate_preparation.world_states
    )
    assert all(item == observations[0] for item in observations)
    result = execute_information_set_search_v1(duplicate_preparation)

    assert result.status == "complete"
    assert result.world_coverage == "sampled_compatible_worlds"
    assert result.consumed_budget.selected_world_count == 4
    assert result.consumed_budget.sampled_world_count == 4
    assert result.consumed_budget.unique_sampled_world_count == (
        selection.unique_sampled_world_count
    )
    assert all(item.completed_world_count == 4 for item in result.candidate_results)
    assert result.controlled_policy[0].reached_world_count == 4
    assert result.consumed_budget.state_nodes_evaluated < 4 * 4


@pytest.mark.parametrize("reason", INFORMATION_SET_SEARCH_UNAVAILABLE_REASONS)
def test_every_unavailable_reason_passes_through_without_execution(
    reason: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preparation = _preparation(remaining_tricks=1)
    unavailable = _forged_preparation(
        preparation,
        status="unavailable",
        unavailable_reason=reason,
        world_selection=None,
        world_states=(),
        root_information_set=None,
        root_legal_cards=(),
    )
    if reason == "incompatible_world_space":
        unavailable = _forged_preparation(
            unavailable,
            world_selection=replace(
                preparation.world_selection,
                available=False,
                unavailable_reason="incompatible_world_space",
                selection_method=None,
                world_coverage="none",
                compatible_world_count=0,
                selected_world_count=0,
                sampled_world_count=0,
                unique_sampled_world_count=0,
                legal_root_cards=(),
                exact_states=(),
            ),
        )

    monkeypatch.setattr(
        executor_module,
        "build_information_set_search_observation_v1",
        lambda _state: pytest.fail("unavailable execution built an Observation"),
    )
    monkeypatch.setattr(
        executor_module,
        "apply_information_set_search_card_v1",
        lambda *_args: pytest.fail("unavailable execution applied a transition"),
    )
    monkeypatch.setattr(
        executor_module,
        "build_exact_terminal_utility",
        lambda **_kwargs: pytest.fail("unavailable execution evaluated utility"),
    )
    result = execute_information_set_search_v1(unavailable)

    assert result.status == "unavailable"
    assert result.stop_reason == reason
    assert not any(result.consumed_budget.to_dict().values())
    assert result.candidate_results == result.controlled_policy == ()
    assert result.recommended_card is None


def test_preparation_validation_rejects_forgery_without_rebuilding_worlds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preparation = _preparation()
    assert preparation.root_information_set is not None
    assert preparation.world_selection is not None
    monkeypatch.setattr(
        preparation_module,
        "build_compatible_search_world_space",
        lambda _view: pytest.fail("validation rebuilt the Compatible-world space"),
    )
    monkeypatch.setattr(
        preparation_module,
        "select_compatible_search_worlds",
        lambda **_kwargs: pytest.fail("validation reselected Worlds"),
    )
    validate_information_set_search_preparation_v1(preparation)

    observation_values = {
        item.name: getattr(preparation.root_information_set, item.name)
        for item in fields(preparation.root_information_set)
    }
    boolean_version_observation = InformationSetSearchObservationV1._from_validated(
        **(observation_values | {"information_set_search_observation_version": True})
    )
    world_state_values = {
        item.name: getattr(preparation.world_states[0], item.name)
        for item in fields(preparation.world_states[0])
    }
    boolean_version_world = InformationSetSearchWorldStateV1._from_validated(
        **(world_state_values | {"information_set_search_world_state_version": True})
    )
    over_budget_selection = replace(
        preparation.world_selection,
        selection_method="uniform_iid_sampling",
        world_coverage="sampled_compatible_worlds",
        selected_world_count=2,
        sampled_world_count=2,
        unique_sampled_world_count=1,
        exact_states=(
            preparation.world_selection.exact_states[0],
            preparation.world_selection.exact_states[0],
        ),
    )

    for forged in (
        _forged_preparation(
            preparation,
            information_set_search_preparation_version=True,
        ),
        _forged_preparation(preparation, request=object()),
        _forged_preparation(preparation, world_states=()),
        _forged_preparation(preparation, root_information_set=None),
        _forged_preparation(preparation, root_legal_cards=()),
        _forged_preparation(
            preparation,
            root_information_set=boolean_version_observation,
        ),
        _forged_preparation(
            preparation,
            world_states=(boolean_version_world,),
        ),
        _forged_preparation(
            preparation,
            world_selection=over_budget_selection,
            world_states=(
                preparation.world_states[0],
                preparation.world_states[0],
            ),
        ),
    ):
        with pytest.raises(SkatMindInvariantError):
            validate_information_set_search_preparation_v1(forged)
    with pytest.raises(ValueError, match="preparation"):
        execute_information_set_search_v1(object())  # type: ignore[arg-type]


def test_preparation_validation_rejects_exact_public_ownership_forgery() -> None:
    preparation = _preparation()
    assert preparation.world_selection is not None
    source = preparation.world_selection.exact_states[0]
    swapped = build_exact_search_state(
        declaration=source.declaration,
        declarer_player=source.declarer_player,
        remaining_hands={
            "me": source.hand_for("me"),
            "left": source.hand_for("right"),
            "right": source.hand_for("left"),
        },
        current_trick=source.current_trick,
        next_player=source.next_player,
        declarer_trick_points=source.declarer_trick_points,
        defender_trick_points=source.defender_trick_points,
        declarer_completed_tricks=source.declarer_completed_tricks,
        defender_completed_tricks=source.defender_completed_tricks,
        out_of_play_cards=source.out_of_play_cards,
    )
    world_values = {
        item.name: getattr(preparation.world_states[0], item.name)
        for item in fields(preparation.world_states[0])
    }
    forged_world = InformationSetSearchWorldStateV1._from_validated(
        **(world_values | {"exact_state": swapped})
    )
    forged_selection = replace(
        preparation.world_selection,
        exact_states=(swapped,),
    )
    forged = _forged_preparation(
        preparation,
        world_selection=forged_selection,
        world_states=(forged_world,),
    )
    with pytest.raises(SkatMindInvariantError):
        validate_information_set_search_preparation_v1(forged)


@pytest.mark.parametrize(
    ("budget_changes", "reason", "expected_depth"),
    [
        ({"max_state_nodes": 1}, "state_node_budget_exhausted", 0),
        ({"max_information_sets": 1}, "information_set_budget_exhausted", 3),
        ({"max_depth_plies": 1}, "depth_budget_exhausted", 1),
    ],
)
def test_structural_limits_return_conservative_partial_results(
    budget_changes: dict[str, int],
    reason: str,
    expected_depth: int,
) -> None:
    preparation = _with_budget(_preparation(), **budget_changes)
    result = execute_information_set_search_v1(preparation)

    assert result.status == "partial"
    assert result.stop_reason == reason
    assert result.policy_claim == "common_policy_prefix"
    assert result.candidate_results == ()
    assert result.recommended_card is None
    assert result.consumed_budget.completed_world_count == 0
    assert result.consumed_budget.depth_reached == expected_depth
    assert len(result.controlled_policy) == (result.consumed_budget.controlled_policy_decisions)
    assert result.consumed_budget.controlled_policy_decisions <= (
        result.consumed_budget.information_sets_evaluated
    )
    if reason == "state_node_budget_exhausted":
        assert result.consumed_budget.state_nodes_evaluated == 1
    if reason == "information_set_budget_exhausted":
        assert result.consumed_budget.information_sets_evaluated == 1


def test_terminal_states_at_the_exact_depth_limit_complete() -> None:
    preparation = _with_budget(
        _preparation(remaining_tricks=1),
        max_depth_plies=3,
    )
    result = execute_information_set_search_v1(preparation)
    assert result.status == "complete"
    assert result.consumed_budget.depth_reached == 3


def test_timeout_precedes_structural_work_and_retains_only_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preparation = _with_budget(
        _preparation(),
        max_state_nodes=1,
        wall_clock_timeout_ms=1,
    )
    clock = iter((0.0, 0.002, 0.002))
    monkeypatch.setattr(executor_module, "_monotonic", lambda: next(clock))
    result = execute_information_set_search_v1(preparation)

    assert result.status == "timeout"
    assert result.stop_reason == "wall_clock_timeout"
    assert result.policy_claim == "none"
    assert result.policy_consistency == "not_assessed"
    assert result.consumed_budget.state_nodes_evaluated == 0
    assert result.consumed_budget.completed_world_count == 0
    assert result.candidate_results == result.controlled_policy == ()
    assert result.recommended_card is None


def test_equal_execution_is_deterministic_except_operational_elapsed_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preparation = _preparation()
    monkeypatch.setattr(executor_module, "_monotonic", lambda: 5.0)
    left = execute_information_set_search_v1(preparation)
    right = execute_information_set_search_v1(preparation)
    assert left == right
    assert left.to_dict() == right.to_dict()


def test_executor_has_no_public_routing_or_existing_minimax_dependency() -> None:
    path = PROJECT_ROOT / "src" / "skatmind" / "information_set_search_executor.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports = tuple(
        imported
        for node in ast.walk(tree)
        for imported in (
            (node.module or "",)
            if isinstance(node, ast.ImportFrom)
            else tuple(alias.name for alias in node.names)
            if isinstance(node, ast.Import)
            else ()
        )
    )
    assert not any(
        fragment in imported
        for fragment in (
            "api",
            "cli",
            "compatible_world_minimax",
            "perfect_information_minimax",
            "multi_step",
        )
        for imported in imports
    )
    calls = {
        node.func.id if isinstance(node.func, ast.Name) else node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, (ast.Name, ast.Attribute))
    }
    assert {
        "solve_compatible_world_minimax",
        "solve_perfect_information_minimax",
        "open",
        "urlopen",
    }.isdisjoint(calls)
    assert "build_exact_terminal_utility" in calls
    assert "apply_information_set_search_card_v1" in calls
