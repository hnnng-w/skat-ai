import json
from dataclasses import replace
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

import skat_ai.compatible_world_minimax as compatible_minimax_module
from skat_ai.bounded_search_information import (
    LIVE_LOCAL_VIEW_SOURCE,
    SearchCompletedTrick,
    SearchInformationView,
    SearchPublicPlay,
    SearchRemainingHandSize,
)
from skat_ai.bounded_search_result import (
    RequestedSearchBudget,
    build_serializable_bounded_search_result,
)
from skat_ai.compatible_search_world import (
    build_compatible_search_world_space,
    select_compatible_search_worlds,
)
from skat_ai.compatible_world_minimax import solve_compatible_world_minimax
from skat_ai.deck import get_full_deck
from skat_ai.exact_search_state import ExactSearchState, build_exact_search_state
from skat_ai.game_declaration import GameDeclaration
from skat_ai.hidden_card_inference import (
    EFFECTIVE_CATEGORY_ORDER,
    PlayerHiddenCardConstraints,
    get_public_effective_category,
)
from skat_ai.perfect_information_minimax import solve_perfect_information_minimax
from skat_ai.public_hand_constraint import (
    DEFENDER_OPEN_PLAY_CONTINUATION_SOURCE,
    PublicHandConstraint,
)
from skat_ai.rules import get_trick_points
from skat_ai.side_ownership import get_player_side
from skat_ai.turn_phase import CONCRETE_PLAYERS

PROJECT_ROOT = Path(__file__).resolve().parents[1]
with (PROJECT_ROOT / "schemas" / "bounded_search_result.schema.json").open(
    "r", encoding="utf-8"
) as schema_file:
    BOUNDED_SEARCH_VALIDATOR = Draft202012Validator(json.load(schema_file))


def _budget(**overrides: int | None) -> RequestedSearchBudget:
    values = {
        "max_remaining_tricks": 5,
        "max_depth_plies": 6,
        "max_nodes": 100_000,
        "max_selected_worlds": 10,
        "max_sampled_worlds": 5,
        "minimum_comparable_worlds": 1,
        "wall_clock_timeout_ms": None,
    }
    values.update(overrides)
    return RequestedSearchBudget(**values)  # type: ignore[arg-type]


def _declaration(game_type: str) -> GameDeclaration:
    return GameDeclaration(
        game_type,
        matadors=None if game_type == "null" else 1,
        bid_value=23 if game_type == "null" else 18,
    )


def _late_exact_state(
    *,
    game_type: str = "grand",
    declarer_player: str = "me",
    root_seat: str = "lead",
    declaration: GameDeclaration | None = None,
) -> ExactSearchState:
    declaration = declaration or _declaration(game_type)
    game_type = declaration.game_type
    seat_values = {
        "lead": (
            {"me": ("CA", "S7"), "left": ("C10", "H7"), "right": ("C7", "D7")},
            (),
        ),
        "second": (
            {"me": ("CA", "S7"), "left": ("C10", "H7"), "right": ("C7",)},
            (("right", "D7"),),
        ),
        "third": (
            {"me": ("CA", "S7"), "left": ("C10",), "right": ("C7",)},
            (("left", "H7"), ("right", "D7")),
        ),
    }
    hands, current_trick = seat_values[root_seat]
    out_of_play_cards = ("H8", "H9")
    explicit_cards = {
        *(card for hand in hands.values() for card in hand),
        *(card for _, card in current_trick),
        *out_of_play_cards,
    }
    completed_points = get_trick_points(
        [card for card in get_full_deck() if card not in explicit_cards]
    )
    if game_type == "null":
        declarer_points = 0
        declarer_tricks = 0
    else:
        declarer_points = completed_points // 2
        declarer_tricks = 4
    return build_exact_search_state(
        declaration=declaration,
        declarer_player=declarer_player,
        remaining_hands=hands,
        current_trick=current_trick,
        next_player="me",
        declarer_trick_points=declarer_points,
        defender_trick_points=completed_points - declarer_points,
        declarer_completed_tricks=declarer_tricks,
        defender_completed_tricks=8 - declarer_tricks,
        out_of_play_cards=out_of_play_cards,
    )


def _view_from_exact_state(
    state: ExactSearchState,
    *,
    public_players: tuple[str, ...] = (),
    known_skat_count: int = 0,
) -> SearchInformationView:
    explicit_cards = {
        *(card for hand in state.hands for card in hand),
        *(play.card for play in state.current_trick),
        *state.out_of_play_cards,
    }
    completed_cards = [card for card in get_full_deck() if card not in explicit_cards]
    completed_tricks = tuple(
        SearchCompletedTrick(
            plays=tuple(
                SearchPublicPlay(player=player, card=card)
                for player, card in zip(
                    CONCRETE_PLAYERS,
                    completed_cards[index : index + 3],
                    strict=True,
                )
            ),
            winner_player=state.declarer_player,
            winner_side="declarer",
            trick_points=get_trick_points(completed_cards[index : index + 3]),
        )
        for index in range(0, len(completed_cards), 3)
    )
    exact_by_player = {
        player: state.hand_for(player) if player in public_players else ()
        for player in CONCRETE_PLAYERS
    }
    exact_by_player["me"] = state.hand_for("me")
    forbidden_by_player = {player: () for player in CONCRETE_PLAYERS}
    if len(state.current_trick) == 2:
        led_category = get_public_effective_category(
            state.current_trick[0].card,
            state.declaration.game_type,
        )
        if (
            get_public_effective_category(
                state.current_trick[1].card,
                state.declaration.game_type,
            )
            != led_category
        ):
            forbidden_by_player[state.current_trick[1].player] = (led_category,)
    return SearchInformationView(
        source=LIVE_LOCAL_VIEW_SOURCE,
        perspective_player="me",
        declarer_player=state.declarer_player,
        local_side=get_player_side("me", state.declarer_player),
        declaration=state.declaration,
        game_type=state.declaration.game_type,
        local_remaining_hand=state.hand_for("me"),
        current_trick=tuple(
            SearchPublicPlay(play.player, play.card) for play in state.current_trick
        ),
        completed_tricks=completed_tricks,
        next_player="me",
        declarer_points=state.declarer_trick_points,
        defender_points=state.defender_trick_points,
        declarer_trick_count=state.declarer_completed_tricks,
        defender_trick_count=state.defender_completed_tricks,
        remaining_hand_sizes=tuple(
            SearchRemainingHandSize(player, len(state.hand_for(player)))
            for player in CONCRETE_PLAYERS
        ),
        known_skat_cards=state.out_of_play_cards[:known_skat_count],
        public_hand_constraints=tuple(
            PublicHandConstraint(
                player=player,
                cards=state.hand_for(player),
                source=DEFENDER_OPEN_PLAY_CONTINUATION_SOURCE,
            )
            for player in public_players
        ),
        hidden_card_constraints=tuple(
            PlayerHiddenCardConstraints(
                player=player,
                forbidden_effective_categories=forbidden_by_player[player],
                exact_cards=exact_by_player[player],
            )
            for player in CONCRETE_PLAYERS
        ),
    )


def _exhaustive_view(
    *,
    game_type: str = "grand",
    declarer_player: str = "me",
    root_seat: str = "lead",
) -> SearchInformationView:
    state = _late_exact_state(
        game_type=game_type,
        declarer_player=declarer_player,
        root_seat=root_seat,
    )
    public_player = "right" if declarer_player == "left" else "left"
    return _view_from_exact_state(
        state,
        public_players=(public_player,),
        known_skat_count=1,
    )


def _sampled_view(
    *,
    game_type: str = "grand",
    declarer_player: str = "me",
    root_seat: str = "lead",
) -> SearchInformationView:
    return _view_from_exact_state(
        _late_exact_state(
            game_type=game_type,
            declarer_player=declarer_player,
            root_seat=root_seat,
        )
    )


def _reference_aggregate(
    *,
    view: SearchInformationView,
    budget: RequestedSearchBudget,
    seed: int,
) -> tuple[object, list[dict[str, object]], int]:
    selection = select_compatible_search_worlds(
        world_space=build_compatible_search_world_space(view),
        requested_budget=budget,
        random_seed=seed,
    )
    totals = {
        card: {"successes": 0, "score": 0.0, "margin": 0.0} for card in selection.legal_root_cards
    }
    nodes = 0
    exact_budget = _budget(
        max_selected_worlds=1,
        max_sampled_worlds=1,
        minimum_comparable_worlds=1,
    )
    for state in selection.exact_states:
        exact_result = solve_perfect_information_minimax(
            state=state,
            perspective_player="me",
            requested_budget=exact_budget,
        )
        assert exact_result.status == "complete"
        nodes += exact_result.consumed_budget.nodes_expanded
        by_card = {candidate.card: candidate for candidate in exact_result.candidate_results}
        for card in selection.legal_root_cards:
            candidate = by_card[card]
            totals[card]["successes"] += candidate.local_contract_success_count
            totals[card]["score"] += candidate.mean_local_side_game_score
            if candidate.mean_local_side_card_point_margin is not None:
                totals[card]["margin"] += candidate.mean_local_side_card_point_margin

    count = selection.selected_world_count
    card_order = {card: index for index, card in enumerate(get_full_deck())}
    rows = [
        {
            "card": card,
            "successes": values["successes"],
            "rate": values["successes"] / count,
            "score": values["score"] / count,
            "margin": (None if view.game_type == "null" else values["margin"] / count),
        }
        for card, values in totals.items()
    ]
    rows.sort(
        key=lambda row: (
            -row["rate"],
            -row["score"],
            -(row["margin"] or 0.0),
            card_order[row["card"]],
        )
    )
    return selection, rows, nodes


def _assert_matches_reference(
    *,
    view: SearchInformationView,
    budget: RequestedSearchBudget,
    seed: int,
) -> None:
    selection, expected, expected_nodes = _reference_aggregate(
        view=view,
        budget=budget,
        seed=seed,
    )
    result = solve_compatible_world_minimax(
        information_view=view,
        requested_budget=budget,
        random_seed=seed,
    )

    assert result.status == "complete"
    assert result.search_method == "compatible_world_minimax_v1"
    assert result.world_coverage == selection.world_coverage
    assert result.compatible_world_count == selection.compatible_world_count
    assert result.consumed_budget.selected_world_count == selection.selected_world_count
    assert result.consumed_budget.sampled_world_count == selection.sampled_world_count
    assert result.consumed_budget.unique_sampled_world_count == selection.unique_sampled_world_count
    assert result.consumed_budget.completed_world_count == selection.selected_world_count
    assert result.consumed_budget.nodes_expanded == expected_nodes
    assert result.recommended_card == expected[0]["card"]
    for rank, (candidate, row) in enumerate(
        zip(result.candidate_results, expected, strict=True), start=1
    ):
        assert candidate.card == row["card"]
        assert candidate.rank == rank
        assert candidate.local_contract_success_count == row["successes"]
        assert candidate.local_contract_success_rate == row["rate"]
        assert candidate.mean_local_side_game_score == row["score"]
        assert candidate.mean_local_side_card_point_margin == row["margin"]


@pytest.mark.parametrize("game_type", ["clubs", "spades", "hearts", "diamonds", "grand", "null"])
@pytest.mark.parametrize("declarer_player", ["me", "left", "right"])
@pytest.mark.parametrize("root_seat", ["lead", "second", "third"])
def test_exhaustive_aggregate_matches_independent_exact_world_reference(
    game_type: str,
    declarer_player: str,
    root_seat: str,
) -> None:
    _assert_matches_reference(
        view=_exhaustive_view(
            game_type=game_type,
            declarer_player=declarer_player,
            root_seat=root_seat,
        ),
        budget=_budget(),
        seed=17,
    )


@pytest.mark.parametrize(
    ("game_type", "declarer_player"),
    [("clubs", "me"), ("grand", "left"), ("null", "right")],
)
def test_sampled_aggregate_matches_independent_exact_world_reference(
    game_type: str,
    declarer_player: str,
) -> None:
    _assert_matches_reference(
        view=_sampled_view(
            game_type=game_type,
            declarer_player=declarer_player,
        ),
        budget=_budget(max_selected_worlds=5, max_sampled_worlds=5),
        seed=31,
    )


def test_one_world_compatible_aggregate_equals_direct_exact_minimax() -> None:
    state = _late_exact_state(game_type="grand")
    view = _view_from_exact_state(
        state,
        public_players=("left", "right"),
        known_skat_count=2,
    )
    compatible = solve_compatible_world_minimax(
        information_view=view,
        requested_budget=_budget(),
        random_seed=2,
    )
    direct = solve_perfect_information_minimax(
        state=state,
        perspective_player="me",
        requested_budget=_budget(
            max_selected_worlds=1,
            max_sampled_worlds=1,
        ),
    )

    assert compatible.world_coverage == "all_compatible_worlds"
    assert compatible.compatible_world_count == 1
    assert compatible.candidate_results == direct.candidate_results
    assert compatible.recommended_card == direct.recommended_card
    assert compatible.consumed_budget.nodes_expanded == direct.consumed_budget.nodes_expanded


@pytest.mark.parametrize(
    "declaration",
    [
        GameDeclaration("null", bid_value=23),
        GameDeclaration("null", hand_game=True, bid_value=35),
        GameDeclaration("null", ouvert=True, bid_value=46),
        GameDeclaration("null", hand_game=True, ouvert=True, bid_value=59),
    ],
    ids=["null", "null-hand", "null-ouvert", "null-hand-ouvert"],
)
def test_one_world_compatible_aggregate_supports_all_null_variants(
    declaration: GameDeclaration,
) -> None:
    state = _late_exact_state(declaration=declaration)
    view = _view_from_exact_state(
        state,
        public_players=("left", "right"),
    )
    compatible = solve_compatible_world_minimax(
        information_view=view,
        requested_budget=_budget(),
        random_seed=2,
    )
    direct = solve_perfect_information_minimax(
        state=state,
        perspective_player="me",
        requested_budget=_budget(max_selected_worlds=1, max_sampled_worlds=1),
    )

    assert compatible.status == "complete"
    assert compatible.compatible_world_count == 1
    assert compatible.candidate_results == direct.candidate_results


def test_duplicate_sampled_draws_are_retained_and_weighted_repeatedly() -> None:
    view = _sampled_view(game_type="null")
    budget = _budget(max_selected_worlds=10, max_sampled_worlds=10)
    world_space = build_compatible_search_world_space(view)
    seed, selection = next(
        (seed, selection)
        for seed in range(100)
        if (
            selection := select_compatible_search_worlds(
                world_space=world_space,
                requested_budget=budget,
                random_seed=seed,
            )
        ).unique_sampled_world_count
        < selection.sampled_world_count
    )

    _assert_matches_reference(view=view, budget=budget, seed=seed)
    result = solve_compatible_world_minimax(
        information_view=view,
        requested_budget=budget,
        random_seed=seed,
    )
    assert result.consumed_budget.sampled_world_count == 10
    assert result.consumed_budget.unique_sampled_world_count < 10
    assert selection.selected_world_count == 10


def test_candidate_aggregation_aligns_reordered_world_values_by_card(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = compatible_minimax_module._evaluate_exact_world_root_utilities

    def reversed_values(**kwargs):
        return tuple(reversed(original(**kwargs)))

    monkeypatch.setattr(
        compatible_minimax_module,
        "_evaluate_exact_world_root_utilities",
        reversed_values,
    )

    _assert_matches_reference(
        view=_exhaustive_view(),
        budget=_budget(),
        seed=9,
    )


def test_global_nodes_equal_fresh_per_world_cost_and_stop_on_common_prefix() -> None:
    view = _exhaustive_view()
    budget = _budget()
    selection, _, complete_nodes = _reference_aggregate(
        view=view,
        budget=budget,
        seed=5,
    )
    first = solve_perfect_information_minimax(
        state=selection.exact_states[0],
        perspective_player="me",
        requested_budget=_budget(max_selected_worlds=1, max_sampled_worlds=1),
    ).consumed_budget.nodes_expanded
    second = solve_perfect_information_minimax(
        state=selection.exact_states[1],
        perspective_player="me",
        requested_budget=_budget(max_selected_worlds=1, max_sampled_worlds=1),
    ).consumed_budget.nodes_expanded

    complete = solve_compatible_world_minimax(
        information_view=view,
        requested_budget=budget,
        random_seed=5,
    )
    before_first_completion = solve_compatible_world_minimax(
        information_view=view,
        requested_budget=_budget(max_nodes=1),
        random_seed=5,
    )
    between_worlds = solve_compatible_world_minimax(
        information_view=view,
        requested_budget=_budget(max_nodes=first),
        random_seed=5,
    )
    inside_second = solve_compatible_world_minimax(
        information_view=view,
        requested_budget=_budget(max_nodes=first + 1),
        random_seed=5,
    )
    after_two = solve_compatible_world_minimax(
        information_view=view,
        requested_budget=_budget(max_nodes=first + second),
        random_seed=5,
    )

    assert complete.consumed_budget.nodes_expanded == complete_nodes
    assert before_first_completion.consumed_budget.completed_world_count == 0
    assert before_first_completion.consumed_budget.nodes_expanded == 1
    assert between_worlds.consumed_budget.completed_world_count == 1
    assert between_worlds.consumed_budget.nodes_expanded == first
    assert inside_second.consumed_budget.completed_world_count == 1
    assert inside_second.consumed_budget.nodes_expanded == first + 1
    assert after_two.consumed_budget.completed_world_count == 2
    assert all(
        result.status == "partial"
        and result.stop_reason == "node_budget_exhausted"
        and result.consumed_budget.selected_world_count == selection.selected_world_count
        for result in (
            before_first_completion,
            between_worlds,
            inside_second,
            after_two,
        )
    )


def test_partial_recommendation_threshold_below_at_and_above_minimum() -> None:
    view = _exhaustive_view()
    selection, _, _ = _reference_aggregate(view=view, budget=_budget(), seed=4)
    node_costs = [
        solve_perfect_information_minimax(
            state=state,
            perspective_player="me",
            requested_budget=_budget(max_selected_worlds=1, max_sampled_worlds=1),
        ).consumed_budget.nodes_expanded
        for state in selection.exact_states
    ]
    zero = solve_compatible_world_minimax(
        information_view=view,
        requested_budget=_budget(max_nodes=1, minimum_comparable_worlds=1),
        random_seed=4,
    )
    below = solve_compatible_world_minimax(
        information_view=view,
        requested_budget=_budget(
            max_nodes=node_costs[0],
            minimum_comparable_worlds=2,
        ),
        random_seed=4,
    )
    at = solve_compatible_world_minimax(
        information_view=view,
        requested_budget=_budget(
            max_nodes=node_costs[0],
            minimum_comparable_worlds=1,
        ),
        random_seed=4,
    )
    above = solve_compatible_world_minimax(
        information_view=view,
        requested_budget=_budget(
            max_nodes=sum(node_costs[:2]),
            minimum_comparable_worlds=1,
        ),
        random_seed=4,
    )

    assert zero.consumed_budget.completed_world_count == 0
    assert zero.recommended_card is None
    assert below.consumed_budget.completed_world_count == 1
    assert below.recommended_card is None
    assert at.consumed_budget.completed_world_count == 1
    assert at.recommended_card == at.candidate_results[0].card
    assert above.consumed_budget.completed_world_count == 2
    assert above.recommended_card == above.candidate_results[0].card
    assert all(not result.fallback_used for result in (zero, below, at, above))


def test_depth_exhaustion_discards_the_incomplete_world_without_fallback() -> None:
    result = solve_compatible_world_minimax(
        information_view=_exhaustive_view(),
        requested_budget=_budget(max_depth_plies=5),
        random_seed=6,
    )

    assert result.status == "partial"
    assert result.stop_reason == "depth_budget_exhausted"
    assert result.solution_claim == "depth_limited_per_selected_world"
    assert result.consumed_budget.depth_reached == 5
    assert result.consumed_budget.completed_world_count == 0
    assert result.recommended_card is None
    assert result.fallback_used is False
    assert all(candidate.completed_world_count == 0 for candidate in result.candidate_results)


def test_depth_exhaustion_retains_an_earlier_complete_prefix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = compatible_minimax_module._evaluate_exact_world_root_utilities
    attempted_worlds = 0

    def abort_second_world(**kwargs):
        nonlocal attempted_worlds
        attempted_worlds += 1
        if attempted_worlds == 2:
            raise compatible_minimax_module._SearchAborted(
                "depth_budget_exhausted"
            )
        return original(**kwargs)

    monkeypatch.setattr(
        compatible_minimax_module,
        "_evaluate_exact_world_root_utilities",
        abort_second_world,
    )
    result = solve_compatible_world_minimax(
        information_view=_exhaustive_view(),
        requested_budget=_budget(minimum_comparable_worlds=1),
        random_seed=6,
    )

    assert result.status == "partial"
    assert result.stop_reason == "depth_budget_exhausted"
    assert result.consumed_budget.completed_world_count == 1
    assert result.recommended_card == result.candidate_results[0].card
    assert all(candidate.completed_world_count == 1 for candidate in result.candidate_results)


def test_one_global_fake_clock_retains_a_positive_timeout_prefix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    view = _exhaustive_view()
    selection = select_compatible_search_worlds(
        world_space=build_compatible_search_world_space(view),
        requested_budget=_budget(),
        random_seed=8,
    )
    first_nodes = solve_perfect_information_minimax(
        state=selection.exact_states[0],
        perspective_player="me",
        requested_budget=_budget(max_selected_worlds=1, max_sampled_worlds=1),
    ).consumed_budget.nodes_expanded
    calls = 0

    def fake_clock() -> float:
        nonlocal calls
        calls += 1
        return 10.0 if calls <= first_nodes + 1 else 10.011

    monkeypatch.setattr(compatible_minimax_module, "_monotonic", fake_clock)
    result = solve_compatible_world_minimax(
        information_view=view,
        requested_budget=_budget(wall_clock_timeout_ms=10),
        random_seed=8,
    )

    assert result.status == "timeout"
    assert result.stop_reason == "wall_clock_timeout"
    assert result.solution_claim == "none"
    assert result.consumed_budget.completed_world_count == 1
    assert result.consumed_budget.nodes_expanded == first_nodes
    assert result.recommended_card == result.candidate_results[0].card
    assert all(candidate.completed_world_count == 1 for candidate in result.candidate_results)


def test_timeout_before_first_world_has_placeholders_and_no_recommendation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    readings = iter((10.0, 10.011, 10.012))
    monkeypatch.setattr(
        compatible_minimax_module,
        "_monotonic",
        lambda: next(readings),
    )

    result = solve_compatible_world_minimax(
        information_view=_exhaustive_view(),
        requested_budget=_budget(wall_clock_timeout_ms=10),
        random_seed=8,
    )

    assert result.status == "timeout"
    assert result.consumed_budget.nodes_expanded == 0
    assert result.consumed_budget.completed_world_count == 0
    assert result.recommended_card is None
    assert all(
        candidate.local_contract_success_rate is None for candidate in result.candidate_results
    )


def test_completed_selection_is_not_converted_by_a_final_timeout_reading(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    view = _view_from_exact_state(
        _late_exact_state(),
        public_players=("left", "right"),
        known_skat_count=2,
    )
    direct = solve_perfect_information_minimax(
        state=_late_exact_state(),
        perspective_player="me",
        requested_budget=_budget(max_selected_worlds=1, max_sampled_worlds=1),
    )
    calls = 0

    def fake_clock() -> float:
        nonlocal calls
        calls += 1
        return 10.0 if calls <= direct.consumed_budget.nodes_expanded + 1 else 10.100

    monkeypatch.setattr(compatible_minimax_module, "_monotonic", fake_clock)
    result = solve_compatible_world_minimax(
        information_view=view,
        requested_budget=_budget(wall_clock_timeout_ms=10),
        random_seed=1,
    )

    assert result.status == "complete"
    assert result.stop_reason == "completed"


@pytest.mark.parametrize(
    ("view", "reason"),
    [
        (
            replace(
                _exhaustive_view(),
                perspective_player="left",
                local_side="defenders",
            ),
            "unsupported_perspective",
        ),
        (replace(_exhaustive_view(), next_player="left"), "local_player_not_to_act"),
        (
            replace(
                _exhaustive_view(),
                declaration=GameDeclaration("grand", matadors=None, bid_value=18),
            ),
            "missing_terminal_utility_inputs",
        ),
    ],
)
def test_preflight_preserves_unavailable_precedence_without_selecting_worlds(
    view: SearchInformationView,
    reason: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        compatible_minimax_module,
        "build_compatible_search_world_space",
        lambda _view: pytest.fail("world construction ran before preflight"),
    )

    result = solve_compatible_world_minimax(
        information_view=view,
        requested_budget=_budget(),
        random_seed=3,
    )

    assert result.status == "unavailable"
    assert result.stop_reason == reason
    assert result.compatible_world_count is None
    assert result.world_coverage == "none"
    assert result.consumed_budget.selected_world_count == 0
    assert result.candidate_results == ()


def test_overbid_null_is_unavailable_before_world_construction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    view = replace(
        _exhaustive_view(game_type="null"),
        declaration=GameDeclaration("null", bid_value=24),
    )
    monkeypatch.setattr(
        compatible_minimax_module,
        "build_compatible_search_world_space",
        lambda _view: pytest.fail("overbid Null selected worlds"),
    )

    result = solve_compatible_world_minimax(
        information_view=view,
        requested_budget=_budget(),
        random_seed=3,
    )

    assert result.stop_reason == "missing_terminal_utility_inputs"
    assert result.compatible_world_count is None


def test_requested_remaining_trick_limit_is_applied_before_world_construction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        compatible_minimax_module,
        "build_compatible_search_world_space",
        lambda _view: pytest.fail("over-limit request selected worlds"),
    )

    result = solve_compatible_world_minimax(
        information_view=_exhaustive_view(),
        requested_budget=_budget(max_remaining_tricks=1),
        random_seed=3,
    )

    assert result.stop_reason == "remaining_trick_limit_exceeded"
    assert result.compatible_world_count is None


def test_zero_compatible_worlds_return_incompatible_world_space() -> None:
    view = _sampled_view()
    impossible = replace(
        view,
        hidden_card_constraints=tuple(
            replace(
                constraint,
                forbidden_effective_categories=EFFECTIVE_CATEGORY_ORDER,
            )
            if constraint.player in {"left", "right"}
            else constraint
            for constraint in view.hidden_card_constraints
        ),
    )

    result = solve_compatible_world_minimax(
        information_view=impossible,
        requested_budget=_budget(),
        random_seed=4,
    )

    assert result.status == "unavailable"
    assert result.stop_reason == "incompatible_world_space"
    assert result.compatible_world_count == 0
    assert result.world_coverage == "none"
    assert result.consumed_budget.selected_world_count == 0
    assert result.candidate_results == ()


@pytest.mark.parametrize("seed", [True, 1.5, "1"])
def test_entry_rejects_boolean_and_non_integer_seeds(seed: object) -> None:
    with pytest.raises(ValueError, match="must be an integer"):
        solve_compatible_world_minimax(
            information_view=_exhaustive_view(),
            requested_budget=_budget(),
            random_seed=seed,  # type: ignore[arg-type]
        )


def test_exact_enumeration_ignores_seed_and_structural_results_are_deterministic() -> None:
    view = _exhaustive_view()
    budget = _budget()
    first = solve_compatible_world_minimax(
        information_view=view,
        requested_budget=budget,
        random_seed=1,
    )
    second = solve_compatible_world_minimax(
        information_view=view,
        requested_budget=budget,
        random_seed=999,
    )

    assert first.world_coverage == second.world_coverage == "all_compatible_worlds"
    assert first.status == second.status
    assert first.stop_reason == second.stop_reason
    assert first.solution_claim == second.solution_claim
    assert first.candidate_results == second.candidate_results
    assert first.recommended_card == second.recommended_card
    assert first.consumed_budget.depth_reached == second.consumed_budget.depth_reached
    assert first.consumed_budget.nodes_expanded == second.consumed_budget.nodes_expanded


def test_result_serialization_is_schema_valid_and_aggregate_only() -> None:
    results = [
        solve_compatible_world_minimax(
            information_view=_exhaustive_view(),
            requested_budget=_budget(),
            random_seed=11,
        ),
        solve_compatible_world_minimax(
            information_view=_exhaustive_view(),
            requested_budget=_budget(max_nodes=1),
            random_seed=11,
        ),
    ]
    for result in results:
        serialized = build_serializable_bounded_search_result(result)
        BOUNDED_SEARCH_VALIDATOR.validate(serialized)
        text = repr(serialized)
        for private_name in (
            "hands",
            "out_of_play_cards",
            "hypothetical_skat",
            "exact_states",
            "fingerprint",
            "random_seed",
            "principal_variation",
            "transposition_table",
            "per_world",
        ):
            assert private_name not in text
