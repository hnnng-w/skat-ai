import inspect
import math
import random
from dataclasses import replace
from itertools import product

import pytest

from skat_ai.bounded_search_information import (
    SearchRemainingHandSize,
    build_live_search_information_view,
)
from skat_ai.bounded_search_result import RequestedSearchBudget
from skat_ai.compatible_search_world import (
    COMPATIBLE_SEARCH_WORLD_SELECTION_VERSION,
    CompatibleSearchWorldSelection,
    CompatibleSearchWorldSpace,
    build_compatible_search_world_space,
    build_exact_search_state_from_compatible_world,
    select_compatible_search_worlds,
)
from skat_ai.deck import get_full_deck
from skat_ai.exact_search_state import (
    apply_exact_search_card,
    build_exact_search_state,
    get_exact_search_legal_cards,
)
from skat_ai.game_declaration import GameDeclaration
from skat_ai.game_state import GameState
from skat_ai.hidden_card_inference import (
    EFFECTIVE_CATEGORY_ORDER,
    OWNER_ORDER,
    CompatibleAssignmentProblem,
    CompatibleHiddenWorld,
    count_compatible_hidden_worlds,
    enumerate_compatible_hidden_worlds,
    get_public_effective_category,
    sample_compatible_hidden_world,
    sample_compatible_hidden_worlds,
    validate_compatible_hidden_world,
)
from skat_ai.public_hand_constraint import (
    DEFENDER_OPEN_PLAY_CONTINUATION_SOURCE,
    PublicHandConstraint,
)
from skat_ai.turn_phase import CONCRETE_PLAYERS


def _declaration(game_type: str = "grand", *, hand_game: bool = False) -> GameDeclaration:
    return GameDeclaration(
        game_type,
        hand_game=hand_game,
        matadors=None if game_type == "null" else 1,
        bid_value=23 if game_type == "null" else 24,
    )


def _initial_hands() -> dict[str, tuple[str, ...]]:
    deck = tuple(get_full_deck())
    return {
        player: deck[index * 10 : (index + 1) * 10]
        for index, player in enumerate(CONCRETE_PLAYERS)
    }


def _view_after_plies(
    played_plies: int,
    *,
    game_type: str = "grand",
    known_skat_count: int = 0,
    hand_game: bool = False,
    public_players: tuple[str, ...] = (),
):
    deck = tuple(get_full_deck())
    declaration = _declaration(game_type, hand_game=hand_game)
    exact_state = build_exact_search_state(
        declaration=declaration,
        declarer_player="me",
        remaining_hands=_initial_hands(),
        current_trick=(),
        next_player="me",
        declarer_trick_points=0,
        defender_trick_points=0,
        declarer_completed_tricks=0,
        defender_completed_tricks=0,
        out_of_play_cards=deck[-2:],
    )
    completed = []
    for _ in range(played_plies):
        transition = apply_exact_search_card(
            exact_state,
            get_exact_search_legal_cards(exact_state)[0],
        )
        exact_state = transition.next_state
        if transition.completed_trick is not None:
            trick = transition.completed_trick
            completed.append(
                {
                    "cards": [play.card for play in trick.plays],
                    "players": [play.player for play in trick.plays],
                    "winner_player": trick.winner_player,
                    "winner_role": trick.winner_side,
                }
            )

    public_constraints = tuple(
        PublicHandConstraint(
            player=player,
            cards=exact_state.hand_for(player),
            source=DEFENDER_OPEN_PLAY_CONTINUATION_SOURCE,
        )
        for player in public_players
    )
    game_state = GameState(
        game_type=game_type,
        player_role="declarer",
        declarer_player="me",
        hand=list(exact_state.hand_for("me")),
        current_trick=[play.card for play in exact_state.current_trick],
        completed_tricks=completed,
        skat=list(deck[-2:][:known_skat_count]),
        trick_leader=(
            exact_state.current_trick[0].player
            if exact_state.current_trick
            else exact_state.next_player
        ),
        next_player=exact_state.next_player,
    )
    view = build_live_search_information_view(
        state=game_state,
        declaration=declaration,
        left_hand_size=len(exact_state.hand_for("left")),
        right_hand_size=len(exact_state.hand_for("right")),
        skat_visibility="known_to_declarer" if known_skat_count else "unknown",
        public_hand_constraints=public_constraints,
    )
    return view, exact_state


def _without_void_constraints(view):
    return replace(
        view,
        hidden_card_constraints=tuple(
            replace(constraint, forbidden_effective_categories=())
            for constraint in view.hidden_card_constraints
        ),
    )


def _budget(
    *,
    max_selected_worlds: int,
    max_sampled_worlds: int | None = None,
) -> RequestedSearchBudget:
    return RequestedSearchBudget(
        max_remaining_tricks=10,
        max_depth_plies=30,
        max_nodes=100_000,
        max_selected_worlds=max_selected_worlds,
        max_sampled_worlds=max_sampled_worlds or max_selected_worlds,
        minimum_comparable_worlds=1,
    )


def _small_problem(
    allowed: dict[str, tuple[str, ...]] | None = None,
) -> CompatibleAssignmentProblem:
    cards = ("CA", "SA", "HA")
    locations = allowed or {card: OWNER_ORDER for card in cards}
    return CompatibleAssignmentProblem(
        cards=cards,
        left_slots=1,
        right_slots=1,
        skat_slots=1,
        allowed_locations_by_card=tuple((card, locations[card]) for card in cards),
    )


def _brute_force_worlds(
    problem: CompatibleAssignmentProblem,
) -> tuple[CompatibleHiddenWorld, ...]:
    allowed = problem.allowed_locations()
    worlds = []
    for owners in product(OWNER_ORDER, repeat=len(problem.cards)):
        if any(
            owner not in allowed[card]
            for card, owner in zip(problem.cards, owners, strict=True)
        ):
            continue
        if owners.count("left") != problem.left_slots:
            continue
        if owners.count("right") != problem.right_slots:
            continue
        if owners.count("skat") != problem.skat_slots:
            continue
        worlds.append(
            CompatibleHiddenWorld(
                left_hand=tuple(
                    card
                    for card, owner in zip(problem.cards, owners, strict=True)
                    if owner == "left"
                ),
                right_hand=tuple(
                    card
                    for card, owner in zip(problem.cards, owners, strict=True)
                    if owner == "right"
                ),
                hypothetical_skat=tuple(
                    card
                    for card, owner in zip(problem.cards, owners, strict=True)
                    if owner == "skat"
                ),
            )
        )
    return tuple(worlds)


def test_world_space_without_void_evidence_counts_all_structural_assignments() -> None:
    view, _ = _view_after_plies(0)

    world_space = build_compatible_search_world_space(view)

    assert all(
        not constraint.forbidden_effective_categories
        for constraint in view.hidden_card_constraints
    )
    assert world_space.compatible_world_count == math.comb(22, 10) * math.comb(12, 10)
    assert world_space._assignment_problem.skat_slots == 2


@pytest.mark.parametrize("game_type", ["clubs", "grand", "null"])
def test_search_worlds_apply_existing_suit_grand_and_null_void_categories(
    game_type: str,
) -> None:
    view, exact_state = _view_after_plies(24, game_type=game_type)

    world_space = build_compatible_search_world_space(view)

    assert world_space.compatible_world_count > 0
    allowed = world_space._assignment_problem.allowed_locations()
    for player in ("left", "right"):
        forbidden = set(
            next(
                constraint
                for constraint in view.hidden_card_constraints
                if constraint.player == player
            ).forbidden_effective_categories
        )
        assert forbidden
        for card in world_space._assignment_problem.cards:
            if get_public_effective_category(card, game_type) in forbidden:
                assert player not in allowed[card]
        assert all(
            get_public_effective_category(card, game_type) not in forbidden
            for card in exact_state.hand_for(player)
        )


@pytest.mark.parametrize("public_players", [("left",), ("right",), ("left", "right")])
def test_exact_public_opponent_hands_are_fixed_to_their_owner(
    public_players: tuple[str, ...],
) -> None:
    view, exact_state = _view_after_plies(24, public_players=public_players)

    problem = build_compatible_search_world_space(view)._assignment_problem
    allowed = problem.allowed_locations()

    for player in public_players:
        exact_hand = set(exact_state.hand_for(player))
        assert all(allowed[card] == (player,) for card in exact_hand)
        assert all(
            player not in allowed[card]
            for card in problem.cards
            if card not in exact_hand
        )


@pytest.mark.parametrize("known_skat_count", [0, 1, 2])
def test_known_out_of_play_cards_reduce_only_skat_assignment_slots(
    known_skat_count: int,
) -> None:
    view, _ = _view_after_plies(0, known_skat_count=known_skat_count)

    world_space = build_compatible_search_world_space(view)

    unknown_count = 22 - known_skat_count
    expected = math.comb(unknown_count, 10) * math.comb(unknown_count - 10, 10)
    assert world_space._assignment_problem.skat_slots == 2 - known_skat_count
    assert world_space.compatible_world_count == expected


def test_hand_game_keeps_both_unknown_skat_cards_in_the_assignment_space() -> None:
    view, _ = _view_after_plies(0, hand_game=True)

    world_space = build_compatible_search_world_space(view)

    assert view.known_skat_cards == ()
    assert world_space._assignment_problem.skat_slots == 2
    assert world_space.compatible_world_count == math.comb(22, 10) * math.comb(12, 10)


@pytest.mark.parametrize(
    ("played_plies", "current_players"),
    [(24, ()), (4, ("right",)), (8, ("left", "right"))],
    ids=["lead", "second-seat", "third-seat"],
)
def test_lead_second_and_third_seat_prefixes_build_strict_world_spaces(
    played_plies: int,
    current_players: tuple[str, ...],
) -> None:
    view, _ = _view_after_plies(played_plies)

    world_space = build_compatible_search_world_space(view)

    assert tuple(play.player for play in view.current_trick) == current_players
    assert world_space.compatible_world_count > 0
    assert len(world_space._assignment_problem.cards) == (
        view.remaining_hand_size("left")
        + view.remaining_hand_size("right")
        + 2
    )


def test_assignment_cards_use_full_deck_order_and_reconcile_exact_slots() -> None:
    view, _ = _view_after_plies(8, known_skat_count=1)
    world_space = build_compatible_search_world_space(view)
    problem = world_space._assignment_problem
    excluded = {
        *view.local_remaining_hand,
        *(play.card for trick in view.completed_tricks for play in trick.plays),
        *(play.card for play in view.current_trick),
        *view.known_skat_cards,
    }

    assert problem.cards == tuple(card for card in get_full_deck() if card not in excluded)
    assert len(problem.cards) == problem.left_slots + problem.right_slots + problem.skat_slots


def test_world_space_rejects_slot_invalid_and_duplicate_cards() -> None:
    view, _ = _view_after_plies(24)
    wrong_sizes = replace(
        view,
        remaining_hand_sizes=(
            SearchRemainingHandSize("me", 2),
            SearchRemainingHandSize("left", 1),
            SearchRemainingHandSize("right", 2),
        ),
    )
    duplicate = replace(
        view,
        local_remaining_hand=(view.local_remaining_hand[0],) * 2,
    )

    with pytest.raises(ValueError, match="do not reconcile"):
        build_compatible_search_world_space(wrong_sizes)
    with pytest.raises(ValueError, match="duplicate known cards"):
        build_compatible_search_world_space(duplicate)
    with pytest.raises(ValueError, match="Invalid cards"):
        build_compatible_search_world_space(
            replace(view, local_remaining_hand=("XX", view.local_remaining_hand[1]))
        )


def test_world_space_rejects_conflicting_exact_ownership_and_public_size_mismatch() -> None:
    view, exact_state = _view_after_plies(24, public_players=("left", "right"))
    shared_card = exact_state.hand_for("left")[0]
    conflicting_constraints = tuple(
        replace(constraint, exact_cards=(shared_card,))
        if constraint.player in {"left", "right"}
        else constraint
        for constraint in view.hidden_card_constraints
    )
    conflicting_public = tuple(
        replace(constraint, cards=(shared_card,))
        for constraint in view.public_hand_constraints
    )

    with pytest.raises(ValueError, match="conflicting exact ownership"):
        build_compatible_search_world_space(
            replace(
                view,
                hidden_card_constraints=conflicting_constraints,
                public_hand_constraints=conflicting_public,
            )
        )

    left_constraint = next(
        constraint
        for constraint in view.hidden_card_constraints
        if constraint.player == "left"
    )
    short_left = left_constraint.exact_cards[:1]
    with pytest.raises(ValueError, match="required hand size"):
        build_compatible_search_world_space(
            replace(
                view,
                hidden_card_constraints=tuple(
                    replace(constraint, exact_cards=short_left)
                    if constraint.player == "left"
                    else constraint
                    for constraint in view.hidden_card_constraints
                ),
                public_hand_constraints=tuple(
                    replace(constraint, cards=short_left)
                    if constraint.player == "left"
                    else constraint
                    for constraint in view.public_hand_constraints
                ),
            )
        )


def test_world_space_rejects_non_public_exact_opponent_ownership() -> None:
    view, exact_state = _view_after_plies(24)
    injected = tuple(
        replace(constraint, exact_cards=exact_state.hand_for("left"))
        if constraint.player == "left"
        else constraint
        for constraint in view.hidden_card_constraints
    )

    with pytest.raises(ValueError, match="authorized public hand constraint"):
        build_compatible_search_world_space(
            replace(view, hidden_card_constraints=injected)
        )


@pytest.mark.parametrize(
    "problem",
    [
        _small_problem(),
        _small_problem(
            {
                "CA": ("left",),
                "SA": ("right", "skat"),
                "HA": ("right", "skat"),
            }
        ),
        _small_problem(
            {"CA": ("left",), "SA": ("left",), "HA": ("skat",)}
        ),
    ],
    ids=["unconstrained", "constrained", "zero-world"],
)
def test_dynamic_programming_count_and_enumeration_match_independent_oracle(
    problem: CompatibleAssignmentProblem,
) -> None:
    oracle = _brute_force_worlds(problem)

    assert count_compatible_hidden_worlds(problem) == len(oracle)
    assert enumerate_compatible_hidden_worlds(problem, max_worlds=10) == oracle


def test_canonical_enumeration_is_complete_unique_and_never_truncates() -> None:
    problem = _small_problem()

    worlds = enumerate_compatible_hidden_worlds(problem, max_worlds=6)

    assert len(worlds) == 6
    assert len(set(worlds)) == 6
    assert worlds == _brute_force_worlds(problem)
    with pytest.raises(ValueError, match="exceeds max_worlds.*not truncated"):
        enumerate_compatible_hidden_worlds(problem, max_worlds=5)
    with pytest.raises(ValueError, match="positive integer"):
        enumerate_compatible_hidden_worlds(problem, max_worlds=0)


def test_batch_sampling_matches_repeated_single_draws_and_preserves_duplicates() -> None:
    problem = _small_problem()
    batch_rng = random.Random(12)
    single_rng = random.Random(12)

    batch = sample_compatible_hidden_worlds(problem, 20, batch_rng)
    repeated = tuple(
        sample_compatible_hidden_world(problem, single_rng) for _ in range(20)
    )

    assert batch == repeated
    assert len(batch) == 20
    assert len(set(batch)) < len(batch)
    assert batch == sample_compatible_hidden_worlds(problem, 20, random.Random(12))
    assert batch != sample_compatible_hidden_worlds(problem, 20, random.Random(13))


def test_batch_sampling_preserves_the_existing_fixed_seed_draw_sequence() -> None:
    problem = _small_problem(
        {
            "CA": ("left", "skat"),
            "SA": ("left", "right", "skat"),
            "HA": ("right", "skat"),
        }
    )

    worlds = sample_compatible_hidden_worlds(problem, 8, random.Random(42))

    assert worlds == (
        CompatibleHiddenWorld(("SA",), ("HA",), ("CA",)),
        CompatibleHiddenWorld(("SA",), ("HA",), ("CA",)),
        CompatibleHiddenWorld(("CA",), ("SA",), ("HA",)),
        CompatibleHiddenWorld(("SA",), ("HA",), ("CA",)),
        CompatibleHiddenWorld(("CA",), ("SA",), ("HA",)),
        CompatibleHiddenWorld(("CA",), ("SA",), ("HA",)),
        CompatibleHiddenWorld(("SA",), ("HA",), ("CA",)),
        CompatibleHiddenWorld(("CA",), ("HA",), ("SA",)),
    )


def test_batch_sampling_rejects_invalid_counts_and_zero_worlds() -> None:
    zero_problem = _small_problem(
        {"CA": ("left",), "SA": ("left",), "HA": ("skat",)}
    )

    with pytest.raises(ValueError, match="positive integer"):
        sample_compatible_hidden_worlds(_small_problem(), 0, random.Random(1))
    with pytest.raises(ValueError, match="no compatible assignment"):
        sample_compatible_hidden_worlds(zero_problem, 1, random.Random(1))


def test_assignment_and_world_validation_report_invalid_cards_as_value_errors() -> None:
    invalid_problem = CompatibleAssignmentProblem(
        cards=("XX",),
        left_slots=0,
        right_slots=0,
        skat_slots=1,
        allowed_locations_by_card=(("XX", ("skat",)),),
    )
    with pytest.raises(ValueError, match="Invalid compatible assignment cards"):
        count_compatible_hidden_worlds(invalid_problem)

    with pytest.raises(ValueError, match="invalid card"):
        validate_compatible_hidden_world(
            _small_problem(),
            CompatibleHiddenWorld(("CA",), ("SA",), ("XX",)),
        )


def test_compatible_world_validator_rejects_slots_coverage_order_and_ownership() -> None:
    problem = _small_problem(
        {
            "CA": ("left",),
            "SA": ("right", "skat"),
            "HA": ("right", "skat"),
        }
    )
    valid = CompatibleHiddenWorld(("CA",), ("SA",), ("HA",))
    validate_compatible_hidden_world(problem, valid)

    invalid_worlds = (
        CompatibleHiddenWorld((), ("SA",), ("CA", "HA")),
        CompatibleHiddenWorld(("CA",), ("SA",), ("SA",)),
        CompatibleHiddenWorld(("SA",), ("CA",), ("HA",)),
    )
    for world in invalid_worlds:
        with pytest.raises(ValueError):
            validate_compatible_hidden_world(problem, world)
    with pytest.raises(TypeError, match="must be a tuple"):
        CompatibleHiddenWorld(["CA"], ("SA",), ("HA",))  # type: ignore[arg-type]


def test_exact_and_sampled_budget_selection_are_deterministic_and_common_rooted() -> None:
    exact_view, _ = _view_after_plies(24, public_players=("left", "right"))
    exact_space = build_compatible_search_world_space(exact_view)
    sampled_view, _ = _view_after_plies(24)
    sampled_space = build_compatible_search_world_space(_without_void_constraints(sampled_view))

    exact = select_compatible_search_worlds(
        world_space=exact_space,
        requested_budget=_budget(max_selected_worlds=1),
        random_seed=7,
    )
    sampled = select_compatible_search_worlds(
        world_space=sampled_space,
        requested_budget=_budget(max_selected_worlds=5),
        random_seed=7,
    )
    repeated = select_compatible_search_worlds(
        world_space=sampled_space,
        requested_budget=_budget(max_selected_worlds=5),
        random_seed=7,
    )
    different = select_compatible_search_worlds(
        world_space=sampled_space,
        requested_budget=_budget(max_selected_worlds=5),
        random_seed=8,
    )

    assert exact.selection_version == COMPATIBLE_SEARCH_WORLD_SELECTION_VERSION
    assert exact.selection_method == "exact_enumeration"
    assert exact.world_coverage == "all_compatible_worlds"
    assert exact.compatible_world_count == exact.selected_world_count == 1
    assert exact.sampled_world_count == exact.unique_sampled_world_count == 0
    assert sampled.selection_method == "uniform_iid_sampling"
    assert sampled.world_coverage == "sampled_compatible_worlds"
    assert sampled.selected_world_count == sampled.sampled_world_count == 5
    assert 0 < sampled.unique_sampled_world_count <= 5
    assert sampled.exact_states == repeated.exact_states
    assert sampled.exact_states != different.exact_states
    assert sampled.legal_root_cards == exact.legal_root_cards
    assert all(
        get_exact_search_legal_cards(state) == sampled.legal_root_cards
        for state in sampled.exact_states
    )
    duplicate_sample = next(
        selection
        for seed in range(100)
        if (
            selection := select_compatible_search_worlds(
                world_space=sampled_space,
                requested_budget=_budget(max_selected_worlds=5),
                random_seed=seed,
            )
        ).unique_sampled_world_count
        < selection.sampled_world_count
    )
    assert duplicate_sample.selected_world_count == 5
    assert duplicate_sample.sampled_world_count == 5
    assert duplicate_sample.unique_sampled_world_count < 5
    assert len(duplicate_sample.exact_states) == 5


def test_exact_enumeration_does_not_derive_or_consume_a_random_stream(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    view, _ = _view_after_plies(24, public_players=("left", "right"))
    world_space = build_compatible_search_world_space(view)
    monkeypatch.setattr(
        "skat_ai.compatible_search_world.derive_simulation_child_seed",
        lambda *_args, **_kwargs: pytest.fail("exact enumeration consumed randomness"),
    )

    selection = select_compatible_search_worlds(
        world_space=world_space,
        requested_budget=_budget(max_selected_worlds=1),
        random_seed=9,
    )

    assert selection.selection_method == "exact_enumeration"


def test_zero_world_selection_reports_only_incompatible_world_space() -> None:
    view, _ = _view_after_plies(24)
    impossible = replace(
        view,
        hidden_card_constraints=tuple(
            replace(
                constraint,
                forbidden_effective_categories=EFFECTIVE_CATEGORY_ORDER,
            )
            if constraint.player == "left"
            else constraint
            for constraint in view.hidden_card_constraints
        ),
    )
    world_space = build_compatible_search_world_space(impossible)

    selection = select_compatible_search_worlds(
        world_space=world_space,
        requested_budget=_budget(max_selected_worlds=2),
        random_seed=1,
    )

    assert world_space.compatible_world_count == 0
    assert selection.available is False
    assert selection.unavailable_reason == "incompatible_world_space"
    assert selection.world_coverage == "none"
    assert selection.selected_world_count == 0
    assert selection.exact_states == ()


def test_materialization_preserves_local_public_prefix_and_two_out_of_play_cards() -> None:
    view, source_state = _view_after_plies(
        24,
        known_skat_count=1,
        public_players=("left", "right"),
    )
    world_space = build_compatible_search_world_space(view)
    world = enumerate_compatible_hidden_worlds(
        world_space._assignment_problem,
        max_worlds=1,
    )[0]

    exact_state = build_exact_search_state_from_compatible_world(
        world_space=world_space,
        world=world,
    )
    completed_cards = {
        play.card for trick in view.completed_tricks for play in trick.plays
    }
    materialized_explicit = {
        *(card for hand in exact_state.hands for card in hand),
        *(play.card for play in exact_state.current_trick),
        *exact_state.out_of_play_cards,
    }

    assert exact_state.hand_for("me") == view.local_remaining_hand
    assert exact_state.hand_for("left") == source_state.hand_for("left")
    assert exact_state.hand_for("right") == source_state.hand_for("right")
    assert tuple(
        (play.player, play.card) for play in exact_state.current_trick
    ) == tuple((play.player, play.card) for play in view.current_trick)
    assert exact_state.declaration == view.declaration
    assert exact_state.declarer_player == view.declarer_player
    assert exact_state.next_player == view.next_player
    assert exact_state.declarer_trick_points == view.declarer_points
    assert exact_state.defender_trick_points == view.defender_points
    assert len(exact_state.out_of_play_cards) == 2
    assert set(view.known_skat_cards).issubset(exact_state.out_of_play_cards)
    assert completed_cards == set(get_full_deck()).difference(materialized_explicit)

    card_order = {card: index for index, card in enumerate(get_full_deck())}
    invalid_world = CompatibleHiddenWorld(
        left_hand=tuple(
            sorted((world.right_hand[0], world.left_hand[1]), key=card_order.__getitem__)
        ),
        right_hand=tuple(
            sorted((world.left_hand[0], world.right_hand[1]), key=card_order.__getitem__)
        ),
        hypothetical_skat=world.hypothetical_skat,
    )
    with pytest.raises(ValueError, match="not allowed"):
        build_exact_search_state_from_compatible_world(
            world_space=world_space,
            world=invalid_world,
        )


def test_selection_keeps_private_states_out_of_repr_and_accepts_no_coherent_root() -> None:
    view, _ = _view_after_plies(24, public_players=("left", "right"))
    world_space = build_compatible_search_world_space(view)
    selection = select_compatible_search_worlds(
        world_space=world_space,
        requested_budget=_budget(max_selected_worlds=1),
        random_seed=3,
    )

    assert "ExactSearchState" not in repr(selection)
    assert "_information_view" not in repr(world_space)
    assert "_assignment_problem" not in repr(world_space)
    assert "coherent_hidden_world" not in inspect.signature(
        build_compatible_search_world_space
    ).parameters
    assert "coherent_hidden_world" not in inspect.signature(
        select_compatible_search_worlds
    ).parameters
    with pytest.raises(TypeError, match="unexpected keyword"):
        build_compatible_search_world_space(  # type: ignore[call-arg]
            view,
            coherent_hidden_world=object(),
        )


def test_selection_value_rejects_malformed_private_state_and_root_invariants() -> None:
    view, _ = _view_after_plies(24, public_players=("left", "right"))
    valid = select_compatible_search_worlds(
        world_space=build_compatible_search_world_space(view),
        requested_budget=_budget(max_selected_worlds=1),
        random_seed=3,
    )

    with pytest.raises(ValueError, match="selection version"):
        replace(valid, selection_version=True)
    with pytest.raises(ValueError, match="available must be a boolean"):
        replace(valid, available=1)
    with pytest.raises(ValueError, match="ExactSearchState"):
        replace(valid, exact_states=(object(),))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="canonical deck order"):
        replace(valid, legal_root_cards=("XX",))
    with pytest.raises(ValueError, match="duplicate exact states"):
        CompatibleSearchWorldSelection(
            selection_version=COMPATIBLE_SEARCH_WORLD_SELECTION_VERSION,
            available=True,
            unavailable_reason=None,
            selection_method="exact_enumeration",
            world_coverage="all_compatible_worlds",
            compatible_world_count=2,
            selected_world_count=2,
            sampled_world_count=0,
            unique_sampled_world_count=0,
            legal_root_cards=valid.legal_root_cards,
            exact_states=(valid.exact_states[0], valid.exact_states[0]),
        )


@pytest.mark.parametrize("random_seed", [True, 1.5, "1"])
def test_search_selection_requires_an_explicit_non_boolean_integer_seed(
    random_seed: object,
) -> None:
    view, _ = _view_after_plies(24, public_players=("left", "right"))

    with pytest.raises(ValueError, match="must be an integer"):
        select_compatible_search_worlds(
            world_space=build_compatible_search_world_space(view),
            requested_budget=_budget(max_selected_worlds=1),
            random_seed=random_seed,  # type: ignore[arg-type]
        )


def test_world_space_requires_its_builder_and_search_information_view() -> None:
    with pytest.raises(TypeError, match="build_compatible_search_world_space"):
        CompatibleSearchWorldSpace()
    with pytest.raises(ValueError, match="SearchInformationView"):
        build_compatible_search_world_space(object())  # type: ignore[arg-type]
