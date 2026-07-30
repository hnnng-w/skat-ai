import json
from collections.abc import Iterable, Mapping
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

import skat_ai.perfect_information_minimax as minimax_module
from skat_ai.bounded_search_result import (
    RequestedSearchBudget,
    build_serializable_bounded_search_result,
)
from skat_ai.deck import get_full_deck
from skat_ai.exact_search_state import (
    ExactSearchState,
    apply_exact_search_card,
    build_exact_search_state,
    get_exact_search_legal_cards,
)
from skat_ai.exact_terminal_utility import (
    build_exact_suit_or_grand_terminal_utility,
)
from skat_ai.game_declaration import GameDeclaration
from skat_ai.perfect_information_minimax import solve_perfect_information_minimax
from skat_ai.rules import get_trick_points
from skat_ai.side_ownership import get_player_side
from skat_ai.terminal_utility import TerminalUtility, compare_terminal_utilities

PROJECT_ROOT = Path(__file__).resolve().parents[1]
with (PROJECT_ROOT / "schemas" / "bounded_search_result.schema.json").open(
    "r", encoding="utf-8"
) as schema_file:
    BOUNDED_SEARCH_VALIDATOR = Draft202012Validator(json.load(schema_file))


def _budget(**overrides: int | None) -> RequestedSearchBudget:
    values = {
        "max_remaining_tricks": 5,
        "max_depth_plies": 15,
        "max_nodes": 100_000,
        "max_selected_worlds": 1,
        "max_sampled_worlds": 1,
        "minimum_comparable_worlds": 1,
        "wall_clock_timeout_ms": None,
    }
    values.update(overrides)
    return RequestedSearchBudget(**values)  # type: ignore[arg-type]


def _state(
    *,
    hands: Mapping[str, Iterable[str]],
    next_player: str,
    declaration: GameDeclaration | None = None,
    declarer_player: str = "me",
    current_trick: Iterable[tuple[str, str]] = (),
    declarer_points: int | None = None,
    declarer_tricks: int | None = None,
) -> ExactSearchState:
    copied_hands = {player: tuple(cards) for player, cards in hands.items()}
    copied_trick = tuple(current_trick)
    out_of_play_cards = ("D8", "D7")
    explicit = {
        *(card for cards in copied_hands.values() for card in cards),
        *(card for _, card in copied_trick),
        *out_of_play_cards,
    }
    completed_cards = [card for card in get_full_deck() if card not in explicit]
    completed_points = get_trick_points(completed_cards)
    remaining_tricks = (sum(len(cards) for cards in copied_hands.values()) + len(copied_trick)) // 3
    completed_trick_count = 10 - remaining_tricks
    if declarer_tricks is None:
        declarer_tricks = completed_trick_count // 2
    if declarer_points is None:
        declarer_points = completed_points // 2
    return build_exact_search_state(
        declaration=declaration or GameDeclaration("grand", matadors=1, bid_value=24),
        declarer_player=declarer_player,
        remaining_hands=copied_hands,
        current_trick=copied_trick,
        next_player=next_player,
        declarer_trick_points=declarer_points,
        defender_trick_points=completed_points - declarer_points,
        declarer_completed_tricks=declarer_tricks,
        defender_completed_tricks=completed_trick_count - declarer_tricks,
        out_of_play_cards=out_of_play_cards,
    )


def _oracle_value(
    state: ExactSearchState,
    local_side: str,
    evaluated_states: list[ExactSearchState] | None = None,
) -> TerminalUtility:
    if evaluated_states is not None:
        evaluated_states.append(state)
    if state.is_terminal:
        return build_exact_suit_or_grand_terminal_utility(
            state=state,
            local_side=local_side,
        )

    actor_side = get_player_side(state.next_player, state.declarer_player)
    maximizing = actor_side == local_side
    best = None
    for card in get_exact_search_legal_cards(state):
        utility = _oracle_value(
            apply_exact_search_card(state, card).next_state,
            local_side,
            evaluated_states,
        )
        if best is None:
            best = utility
            continue
        comparison = compare_terminal_utilities(utility, best)
        if (maximizing and comparison > 0) or (not maximizing and comparison < 0):
            best = utility
    assert best is not None
    return best


def _oracle_root_values(
    state: ExactSearchState,
    perspective_player: str,
) -> dict[str, TerminalUtility]:
    local_side = get_player_side(perspective_player, state.declarer_player)
    assert local_side is not None
    return {
        card: _oracle_value(apply_exact_search_card(state, card).next_state, local_side)
        for card in get_exact_search_legal_cards(state)
    }


def _assert_oracle_agreement(state: ExactSearchState, perspective_player: str) -> None:
    expected = _oracle_root_values(state, perspective_player)
    expected_card = next(iter(expected))
    for card, utility in expected.items():
        if compare_terminal_utilities(utility, expected[expected_card]) > 0:
            expected_card = card
    result = solve_perfect_information_minimax(
        state=state,
        perspective_player=perspective_player,
        requested_budget=_budget(),
    )

    assert result.status == "complete"
    assert result.solution_claim == "exact_per_selected_world"
    assert result.world_coverage == "single_exact_world"
    assert result.consumed_budget.completed_world_count == 1
    assert result.recommended_card == expected_card
    assert {candidate.card for candidate in result.candidate_results} == set(expected)
    for candidate in result.candidate_results:
        utility = expected[candidate.card]
        assert candidate.completed_world_count == 1
        assert candidate.local_contract_success_count == int(utility.local_contract_success)
        assert candidate.local_contract_success_rate == float(utility.local_contract_success)
        assert candidate.mean_local_side_game_score == float(utility.local_side_game_score)
        assert candidate.mean_local_side_card_point_margin == float(
            utility.local_side_card_point_margin
        )


@pytest.mark.parametrize("game_type", ["clubs", "spades", "hearts", "diamonds", "grand"])
def test_minimax_matches_oracle_for_all_suit_and_grand_contracts(
    game_type: str,
) -> None:
    state = _state(
        hands={"me": ["C7"], "left": ["S7"], "right": ["H7"]},
        next_player="me",
        declaration=GameDeclaration(game_type, matadors=1, bid_value=18),
        declarer_points=55,
        declarer_tricks=4,
    )

    _assert_oracle_agreement(state, "me")


@pytest.mark.parametrize(
    ("hands", "current_trick", "next_player"),
    [
        ({"me": ["C7"], "left": ["S7"], "right": ["H7"]}, (), "me"),
        ({"me": [], "left": ["S7"], "right": ["H7"]}, (("me", "C7"),), "left"),
        (
            {"me": [], "left": [], "right": ["H7"]},
            (("me", "C7"), ("left", "S7")),
            "right",
        ),
    ],
    ids=["lead", "second-seat", "third-seat"],
)
def test_minimax_matches_oracle_from_every_root_trick_seat(
    hands: Mapping[str, Iterable[str]],
    current_trick: tuple[tuple[str, str], ...],
    next_player: str,
) -> None:
    state = _state(
        hands=hands,
        current_trick=current_trick,
        next_player=next_player,
        declarer_points=55,
        declarer_tricks=4,
    )

    _assert_oracle_agreement(state, next_player)


@pytest.mark.parametrize(
    ("perspective_player", "declarer_player"),
    [("me", "me"), ("left", "me"), ("right", "me")],
    ids=["declarer", "left-defender", "right-defender"],
)
def test_minimax_orientation_and_cooperating_defenders_match_oracle(
    perspective_player: str,
    declarer_player: str,
) -> None:
    state = _state(
        hands={
            "me": ["CA", "H7"],
            "left": ["C10", "S7"],
            "right": ["C7", "SA"],
        },
        next_player=perspective_player,
        declarer_player=declarer_player,
        declarer_points=50,
        declarer_tricks=4,
    )

    _assert_oracle_agreement(state, perspective_player)


def test_minimax_matches_brute_force_oracle_for_curated_three_trick_world() -> None:
    state = _state(
        hands={
            "me": ["CA", "S10", "H7"],
            "left": ["C10", "SA", "H8"],
            "right": ["C7", "S7", "H9"],
        },
        next_player="me",
        declarer_points=40,
        declarer_tricks=3,
    )

    _assert_oracle_agreement(state, "me")


def test_alpha_beta_and_exact_transpositions_reduce_full_oracle_work() -> None:
    state = _state(
        hands={
            "me": ["CA", "S10", "H7"],
            "left": ["C10", "SA", "H8"],
            "right": ["C7", "S7", "H9"],
        },
        next_player="me",
        declarer_points=40,
        declarer_tricks=3,
    )
    evaluated_states: list[ExactSearchState] = []
    for card in get_exact_search_legal_cards(state):
        _oracle_value(
            apply_exact_search_card(state, card).next_state,
            "declarer",
            evaluated_states,
        )

    result = solve_perfect_information_minimax(
        state=state,
        perspective_player="me",
        requested_budget=_budget(),
    )

    assert result.status == "complete"
    assert result.consumed_budget.nodes_expanded < 1 + len(evaluated_states)


def test_minimax_uses_canonical_root_order_for_terminal_utility_ties() -> None:
    state = _state(
        hands={
            "me": ["C7", "S7"],
            "left": ["C8", "S8"],
            "right": ["C9", "S9"],
        },
        next_player="me",
        declarer_points=60,
        declarer_tricks=4,
    )

    result = solve_perfect_information_minimax(
        state=state,
        perspective_player="me",
        requested_budget=_budget(),
    )

    assert [candidate.card for candidate in result.candidate_results] == ["C7", "S7"]
    assert result.recommended_card == "C7"


def test_minimax_depth_boundary_is_exact_and_one_less_is_exhausted() -> None:
    state = _state(
        hands={
            "me": ["C7", "S7"],
            "left": ["C8", "S8"],
            "right": ["C9", "S9"],
        },
        next_player="me",
        declarer_points=60,
        declarer_tricks=4,
    )

    exact = solve_perfect_information_minimax(
        state=state,
        perspective_player="me",
        requested_budget=_budget(max_depth_plies=6),
    )
    exhausted = solve_perfect_information_minimax(
        state=state,
        perspective_player="me",
        requested_budget=_budget(max_depth_plies=5),
    )

    assert exact.status == "complete"
    assert exact.consumed_budget.depth_reached == 6
    assert exhausted.status == "partial"
    assert exhausted.stop_reason == "depth_budget_exhausted"
    assert exhausted.solution_claim == "depth_limited_per_selected_world"
    assert exhausted.consumed_budget.depth_reached == 5
    assert exhausted.consumed_budget.completed_world_count == 0


def test_minimax_root_partial_trick_cards_do_not_consume_future_depth() -> None:
    state = _state(
        hands={"me": [], "left": [], "right": ["H7"]},
        current_trick=(("me", "C7"), ("left", "S7")),
        next_player="right",
        declarer_points=55,
        declarer_tricks=4,
    )

    result = solve_perfect_information_minimax(
        state=state,
        perspective_player="right",
        requested_budget=_budget(max_depth_plies=1),
    )

    assert result.status == "complete"
    assert result.consumed_budget.depth_reached == 1


def test_minimax_node_count_and_exact_node_budget_boundary() -> None:
    state = _state(
        hands={"me": ["C7"], "left": ["S7"], "right": ["H7"]},
        next_player="me",
        declarer_points=55,
        declarer_tricks=4,
    )
    baseline = solve_perfect_information_minimax(
        state=state,
        perspective_player="me",
        requested_budget=_budget(),
    )
    nodes = baseline.consumed_budget.nodes_expanded

    exact = solve_perfect_information_minimax(
        state=state,
        perspective_player="me",
        requested_budget=_budget(max_nodes=nodes),
    )
    exhausted = solve_perfect_information_minimax(
        state=state,
        perspective_player="me",
        requested_budget=_budget(max_nodes=nodes - 1),
    )

    assert nodes == 4
    assert exact.status == "complete"
    assert exact.consumed_budget.nodes_expanded == nodes
    assert exhausted.status == "partial"
    assert exhausted.stop_reason == "node_budget_exhausted"
    assert exhausted.consumed_budget.nodes_expanded == nodes - 1


def test_minimax_discards_completed_root_values_after_later_node_abort() -> None:
    state = _state(
        hands={
            "me": ["C7", "S7"],
            "left": ["C8", "S8"],
            "right": ["C9", "S9"],
        },
        next_player="me",
        declarer_points=60,
        declarer_tricks=4,
    )
    complete = solve_perfect_information_minimax(
        state=state,
        perspective_player="me",
        requested_budget=_budget(),
    )

    partial = solve_perfect_information_minimax(
        state=state,
        perspective_player="me",
        requested_budget=_budget(
            max_nodes=complete.consumed_budget.nodes_expanded - 1,
        ),
    )

    assert partial.status == "partial"
    assert partial.stop_reason == "node_budget_exhausted"
    assert partial.recommended_card is None
    assert [candidate.card for candidate in partial.candidate_results] == ["C7", "S7"]
    assert all(candidate.completed_world_count == 0 for candidate in partial.candidate_results)
    assert all(
        candidate.mean_local_side_game_score is None for candidate in partial.candidate_results
    )


def test_minimax_does_not_reuse_aborted_work_across_solver_calls() -> None:
    state = _state(
        hands={
            "me": ["CA", "H7"],
            "left": ["C10", "S7"],
            "right": ["C7", "SA"],
        },
        next_player="me",
        declarer_points=50,
        declarer_tricks=4,
    )
    partial = solve_perfect_information_minimax(
        state=state,
        perspective_player="me",
        requested_budget=_budget(max_nodes=2),
    )
    first_complete = solve_perfect_information_minimax(
        state=state,
        perspective_player="me",
        requested_budget=_budget(),
    )
    second_complete = solve_perfect_information_minimax(
        state=state,
        perspective_player="me",
        requested_budget=_budget(),
    )

    assert partial.stop_reason == "node_budget_exhausted"
    assert first_complete.status == "complete"
    assert second_complete.status == "complete"
    assert first_complete.candidate_results == second_complete.candidate_results
    assert (
        first_complete.consumed_budget.nodes_expanded
        == second_complete.consumed_budget.nodes_expanded
    )


def test_minimax_fake_clock_timeout_is_deterministic_and_has_fair_placeholders(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _state(
        hands={
            "me": ["C7", "S7"],
            "left": ["C8", "S8"],
            "right": ["C9", "S9"],
        },
        next_player="me",
        declarer_points=60,
        declarer_tricks=4,
    )
    readings = iter((10.0, 10.011, 10.012))
    monkeypatch.setattr(minimax_module, "_monotonic", lambda: next(readings))

    result = solve_perfect_information_minimax(
        state=state,
        perspective_player="me",
        requested_budget=_budget(wall_clock_timeout_ms=10),
    )

    assert result.status == "timeout"
    assert result.stop_reason == "wall_clock_timeout"
    assert result.solution_claim == "none"
    assert result.consumed_budget.nodes_expanded == 0
    assert result.recommended_card is None
    assert [candidate.card for candidate in result.candidate_results] == ["C7", "S7"]
    assert [candidate.rank for candidate in result.candidate_results] == [1, 2]
    assert all(not candidate.is_recommended for candidate in result.candidate_results)
    assert all(candidate.completed_world_count == 0 for candidate in result.candidate_results)
    assert all(
        candidate.mean_local_side_game_score is None for candidate in result.candidate_results
    )


def test_minimax_null_is_explicitly_unavailable() -> None:
    state = _state(
        hands={"me": ["C7"], "left": ["S7"], "right": ["H7"]},
        next_player="me",
        declaration=GameDeclaration("null", bid_value=23),
        declarer_points=55,
        declarer_tricks=4,
    )

    result = solve_perfect_information_minimax(
        state=state,
        perspective_player="me",
        requested_budget=_budget(),
    )

    assert result.status == "unavailable"
    assert result.stop_reason == "unsupported_game_type"
    assert result.world_coverage == "none"
    assert result.candidate_results == ()


@pytest.mark.parametrize(
    ("state", "perspective_player", "budget", "reason"),
    [
        (
            _state(hands={"me": [], "left": [], "right": []}, next_player="me"),
            "me",
            _budget(),
            "game_already_complete",
        ),
        (
            _state(
                hands={"me": ["C7"], "left": ["S7"], "right": ["H7"]},
                next_player="left",
                declarer_points=55,
                declarer_tricks=4,
            ),
            "me",
            _budget(),
            "local_player_not_to_act",
        ),
        (
            _state(
                hands={"me": ["C7"], "left": ["S7"], "right": ["H7"]},
                next_player="me",
                declaration=GameDeclaration("clubs", bid_value=18),
                declarer_points=55,
                declarer_tricks=4,
            ),
            "me",
            _budget(),
            "missing_terminal_utility_inputs",
        ),
        (
            _state(
                hands={"me": ["C7"], "left": ["S7"], "right": ["H7"]},
                next_player="me",
                declaration=GameDeclaration("clubs", matadors=1),
                declarer_points=55,
                declarer_tricks=4,
            ),
            "me",
            _budget(),
            "missing_terminal_utility_inputs",
        ),
        (
            _state(
                hands={
                    "me": get_full_deck()[:6],
                    "left": get_full_deck()[6:12],
                    "right": get_full_deck()[12:18],
                },
                next_player="me",
            ),
            "me",
            _budget(),
            "remaining_trick_limit_exceeded",
        ),
    ],
)
def test_minimax_returns_privacy_empty_unavailable_results(
    state: ExactSearchState,
    perspective_player: str,
    budget: RequestedSearchBudget,
    reason: str,
) -> None:
    result = solve_perfect_information_minimax(
        state=state,
        perspective_player=perspective_player,
        requested_budget=budget,
    )

    assert result.status == "unavailable"
    assert result.stop_reason == reason
    assert result.compatible_world_count is None
    assert result.consumed_budget.selected_world_count == 0
    assert result.candidate_results == ()
    assert result.recommended_card is None
    assert result.fallback_used is False


def test_minimax_reports_no_legal_root_card_when_kernel_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _state(
        hands={"me": ["C7"], "left": ["S7"], "right": ["H7"]},
        next_player="me",
        declarer_points=55,
        declarer_tricks=4,
    )
    monkeypatch.setattr(minimax_module, "get_exact_search_legal_cards", lambda _: ())

    result = solve_perfect_information_minimax(
        state=state,
        perspective_player="me",
        requested_budget=_budget(),
    )

    assert result.status == "unavailable"
    assert result.stop_reason == "no_legal_cards"


def test_minimax_uses_lower_requested_remaining_trick_limit() -> None:
    state = _state(
        hands={
            "me": ["CA", "S10", "H7"],
            "left": ["C10", "SA", "H8"],
            "right": ["C7", "S7", "H9"],
        },
        next_player="me",
        declarer_points=40,
        declarer_tricks=3,
    )

    result = solve_perfect_information_minimax(
        state=state,
        perspective_player="me",
        requested_budget=_budget(max_remaining_tricks=2),
    )

    assert result.status == "unavailable"
    assert result.stop_reason == "remaining_trick_limit_exceeded"


def test_minimax_rejects_malformed_perspective() -> None:
    state = _state(
        hands={"me": ["C7"], "left": ["S7"], "right": ["H7"]},
        next_player="me",
        declarer_points=55,
        declarer_tricks=4,
    )

    with pytest.raises(ValueError, match="concrete player"):
        solve_perfect_information_minimax(
            state=state,
            perspective_player="unknown",
            requested_budget=_budget(),
        )


def test_minimax_serialization_is_aggregate_only_and_privacy_safe() -> None:
    state = _state(
        hands={
            "me": ["CA", "H7"],
            "left": ["C10", "S7"],
            "right": ["C7", "SA"],
        },
        next_player="left",
        declarer_points=50,
        declarer_tricks=4,
    )
    result = solve_perfect_information_minimax(
        state=state,
        perspective_player="left",
        requested_budget=_budget(),
    )

    serialized = build_serializable_bounded_search_result(result)

    assert serialized["search_method"] == "perfect_information_minimax_v1"
    assert serialized["compatible_world_count"] == 1
    text = repr(serialized)
    for private_field in (
        "hands",
        "left_hand",
        "right_hand",
        "out_of_play_cards",
        "world_assignment",
        "principal_variation",
    ):
        assert private_field not in text


def test_all_solver_result_statuses_validate_against_standalone_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    one_trick = _state(
        hands={"me": ["C7"], "left": ["S7"], "right": ["H7"]},
        next_player="me",
        declarer_points=55,
        declarer_tricks=4,
    )
    two_tricks = _state(
        hands={
            "me": ["C7", "S7"],
            "left": ["C8", "S8"],
            "right": ["C9", "S9"],
        },
        next_player="me",
        declarer_points=60,
        declarer_tricks=4,
    )
    null_state = _state(
        hands={"me": ["C7"], "left": ["S7"], "right": ["H7"]},
        next_player="me",
        declaration=GameDeclaration("null", bid_value=23),
        declarer_points=55,
        declarer_tricks=4,
    )
    results = [
        solve_perfect_information_minimax(
            state=one_trick,
            perspective_player="me",
            requested_budget=_budget(),
        ),
        solve_perfect_information_minimax(
            state=two_tricks,
            perspective_player="me",
            requested_budget=_budget(max_depth_plies=5),
        ),
        solve_perfect_information_minimax(
            state=null_state,
            perspective_player="me",
            requested_budget=_budget(),
        ),
    ]
    readings = iter((10.0, 10.011, 10.012))
    monkeypatch.setattr(minimax_module, "_monotonic", lambda: next(readings))
    results.append(
        solve_perfect_information_minimax(
            state=two_tricks,
            perspective_player="me",
            requested_budget=_budget(wall_clock_timeout_ms=10),
        )
    )

    assert {result.status for result in results} == {
        "complete",
        "partial",
        "timeout",
        "unavailable",
    }
    for result in results:
        BOUNDED_SEARCH_VALIDATOR.validate(build_serializable_bounded_search_result(result))
