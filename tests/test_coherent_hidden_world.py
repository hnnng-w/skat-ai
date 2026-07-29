import random
from dataclasses import FrozenInstanceError

import pytest

from skat_ai.card_tracking import get_unseen_cards
from skat_ai.coherent_hidden_world import (
    CoherentHiddenWorld,
    HiddenWorldProvenance,
    apply_hidden_world_plays,
    build_coherent_hidden_world,
    build_hidden_world_summary,
    derive_simulation_child_seed,
    reconcile_hidden_world_with_state,
    remove_card_from_hidden_world,
)
from skat_ai.game_state import GameState
from skat_ai.multi_step_simulation import simulate_multiple_steps
from skat_ai.opponent_lead import (
    simulate_left_lead_and_right_response_once,
    simulate_opponent_lead_once,
    simulate_right_response_to_left_lead_once,
)
from skat_ai.opponent_sequence import prepare_player_action_state
from skat_ai.policy_comparison import compare_multi_step_policies
from skat_ai.public_hand_constraint import PublicHandConstraint
from skat_ai.simulation import simulate_immediate_trick_once_detailed
from skat_ai.simulation_context import SimulationContext, validate_simulation_context


def _state() -> GameState:
    return GameState(
        game_type="grand",
        player_role="declarer",
        hand=["CJ", "SA", "H10"],
        current_trick=["D7"],
        played_cards=["C7"],
        skat=[],
    )


def _world_from_hands(
    state: GameState,
    left_hand: tuple[str, ...],
    right_hand: tuple[str, ...],
) -> CoherentHiddenWorld:
    assigned = {*left_hand, *right_hand}
    return CoherentHiddenWorld(
        left_hand=left_hand,
        right_hand=right_hand,
        hypothetical_skat=tuple(
            card for card in get_unseen_cards(state) if card not in assigned
        ),
    )


def test_builder_samples_one_deterministic_tuple_backed_root_world(monkeypatch) -> None:
    calls = 0

    from skat_ai.simulation import generate_sampled_hidden_state as real_sampler

    def counting_sampler(**kwargs):
        nonlocal calls
        calls += 1
        return real_sampler(**kwargs)

    monkeypatch.setattr(
        "skat_ai.coherent_hidden_world.generate_sampled_hidden_state",
        counting_sampler,
    )
    state = _state()
    original_state = state.__dict__.copy()

    first = build_coherent_hidden_world(state, 4, 4, random.Random(42))
    second = build_coherent_hidden_world(state, 4, 4, random.Random(42))

    assert calls == 2
    assert first == second
    assert isinstance(first.left_hand, tuple)
    assert isinstance(first.right_hand, tuple)
    assert isinstance(first.hypothetical_skat, tuple)
    assert state.__dict__ == original_state
    assert first.provenance is not None
    assert first.provenance.root_sample_count == 1


def test_root_world_assigns_every_unseen_card_exactly_once() -> None:
    from skat_ai.card_tracking import get_unseen_cards

    state = _state()
    world = build_coherent_hidden_world(state, 4, 5, random.Random(7))
    assigned = world.left_hand + world.right_hand + world.hypothetical_skat

    assert len(world.left_hand) == 4
    assert len(world.right_hand) == 5
    assert sorted(assigned) == sorted(get_unseen_cards(state))
    assert len(assigned) == len(set(assigned))


def test_different_seed_can_build_a_different_valid_world() -> None:
    first = build_coherent_hidden_world(_state(), 4, 4, random.Random(1))
    second = build_coherent_hidden_world(_state(), 4, 4, random.Random(2))

    assert first != second
    assert set(first.left_hand + first.right_hand + first.hypothetical_skat) == set(
        second.left_hand + second.right_hand + second.hypothetical_skat
    )


def test_builder_preserves_exact_local_and_opponent_public_constraints() -> None:
    state = _state()
    left_cards = ("CA", "C10", "CK", "CQ")
    constraints = (
        PublicHandConstraint(player="me", cards=tuple(state.hand)),
        PublicHandConstraint(player="left", cards=left_cards),
    )

    world = build_coherent_hidden_world(
        state,
        4,
        4,
        random.Random(9),
        constraints,
    )

    assert set(world.left_hand) == set(left_cards)
    assert set(world.right_hand).isdisjoint(left_cards)
    assert set(world.hypothetical_skat).isdisjoint(left_cards)
    reconcile_hidden_world_with_state(world, state, constraints)


def test_builder_rejects_invalid_public_constraints_before_sampling(
    monkeypatch,
) -> None:
    def fail_if_sampled(**_kwargs):
        raise AssertionError("sampler must not run")

    monkeypatch.setattr(
        "skat_ai.coherent_hidden_world.generate_sampled_hidden_state",
        fail_if_sampled,
    )
    invalid_constraint = PublicHandConstraint(player="left", cards=("X1",))

    with pytest.raises(ValueError, match="Invalid canonical cards"):
        build_coherent_hidden_world(
            _state(),
            1,
            1,
            random.Random(3),
            (invalid_constraint,),
        )


@pytest.mark.parametrize(
    ("state", "left_size", "right_size", "message"),
    [
        (
            GameState(
                game_type="grand",
                player_role="declarer",
                hand=["SA", "SA"],
                current_trick=[],
            ),
            1,
            1,
            "Duplicate known cards",
        ),
        (_state(), -1, 1, "must not be negative"),
        (_state(), 20, 20, "Not enough available cards"),
    ],
)
def test_builder_rejects_invalid_root_states(
    state: GameState,
    left_size: int,
    right_size: int,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        build_coherent_hidden_world(state, left_size, right_size, random.Random(1))


def test_world_rejects_invalid_cards_and_cross_location_duplicates() -> None:
    with pytest.raises(ValueError, match="Invalid canonical cards"):
        CoherentHiddenWorld(("X1",), (), ())
    with pytest.raises(ValueError, match="multiple current locations"):
        CoherentHiddenWorld(("SA",), ("SA",), ())


def test_world_and_transition_history_are_frozen() -> None:
    world = CoherentHiddenWorld(("SA",), ("H7",), ("D7",))

    with pytest.raises(FrozenInstanceError):
        world.left_hand = ()  # type: ignore[misc]
    with pytest.raises(TypeError, match="left_hand must be a tuple"):
        CoherentHiddenWorld(["SA"], (), ())  # type: ignore[arg-type]


def test_remove_card_is_immutable_and_preserves_other_owners_and_skat() -> None:
    world = CoherentHiddenWorld(("SA", "S10"), ("H7",), ("D7",))

    updated = remove_card_from_hidden_world(world, "left", "SA", step_index=3)

    assert world.left_hand == ("SA", "S10")
    assert updated.left_hand == ("S10",)
    assert updated.right_hand is world.right_hand
    assert updated.hypothetical_skat is world.hypothetical_skat
    assert updated.ownership_transitions == (("left", "SA"),)


@pytest.mark.parametrize(
    ("player", "card", "owner"),
    [
        ("left", "H7", "right"),
        ("right", "SA", "left"),
        ("left", "D7", "hypothetical_skat"),
        ("me", "SA", "unsupported"),
    ],
)
def test_remove_rejects_wrong_owner_with_step_and_invariant(
    player: str,
    card: str,
    owner: str,
) -> None:
    world = CoherentHiddenWorld(("SA",), ("H7",), ("D7",))

    with pytest.raises(ValueError) as error:
        remove_card_from_hidden_world(world, player, card, step_index=6)

    assert "ownership invariant" in str(error.value)
    assert "step 6" in str(error.value)
    assert owner in str(error.value)


def test_apply_plays_removes_each_owner_card_once_and_rejects_replay() -> None:
    world = CoherentHiddenWorld(("SA", "S10"), ("H7", "H8"), ("D7",))

    updated = apply_hidden_world_plays(
        world,
        (("left", "SA"), ("right", "H7")),
        step_index=2,
    )

    assert updated.left_hand == ("S10",)
    assert updated.right_hand == ("H8",)
    assert updated.hypothetical_skat == ("D7",)
    with pytest.raises(ValueError, match="step 3.*played_by_left"):
        remove_card_from_hidden_world(updated, "left", "SA", step_index=3)


def test_reconciliation_detects_known_overlap_and_public_owner_mismatch() -> None:
    world = CoherentHiddenWorld(("SA",), ("H7",), ("D7",))
    overlapping_state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA"],
        current_trick=[],
    )
    clean_state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["CJ"],
        current_trick=[],
    )

    with pytest.raises(ValueError, match="step 4.*already known"):
        reconcile_hidden_world_with_state(world, overlapping_state, step_index=4)
    with pytest.raises(ValueError, match="public left.*does not match"):
        reconcile_hidden_world_with_state(
            world,
            clean_state,
            (PublicHandConstraint(player="left", cards=("H7",)),),
            step_index=5,
        )


def test_reconciliation_requires_transitioned_cards_in_known_state() -> None:
    state = _state()
    world = build_coherent_hidden_world(state, 2, 2, random.Random(11))
    played_card = world.left_hand[0]
    updated = remove_card_from_hidden_world(world, "left", played_card, step_index=1)

    with pytest.raises(ValueError, match="transitioned cards are absent"):
        reconcile_hidden_world_with_state(updated, state, step_index=1)

    state.played_cards.append(played_card)
    reconcile_hidden_world_with_state(updated, state, step_index=1)


def test_fixed_skat_and_root_sample_count_are_validated() -> None:
    provenance = HiddenWorldProvenance(
        source="sampled_hidden_state",
        sampled_at_step=0,
        initial_left_hand_size=1,
        initial_right_hand_size=1,
        initial_left_hand=("SA",),
        initial_right_hand=("H7",),
        initial_hypothetical_skat=("D7",),
    )
    with pytest.raises(ValueError, match="fixed hypothetical skat changed"):
        CoherentHiddenWorld(("SA",), ("H7",), ("D8",), provenance)

    invalid_count = HiddenWorldProvenance(
        source="sampled_hidden_state",
        sampled_at_step=0,
        initial_left_hand_size=1,
        initial_right_hand_size=1,
        initial_left_hand=("SA",),
        initial_right_hand=("H7",),
        initial_hypothetical_skat=("D7",),
        root_sample_count=2,
    )
    with pytest.raises(ValueError, match="root sample count is 2"):
        CoherentHiddenWorld(("SA",), ("H7",), ("D7",), invalid_count)


def test_validation_rejects_root_owner_switch_with_equal_hand_sizes() -> None:
    root = CoherentHiddenWorld(("SA",), ("H7",), ("D7",))

    with pytest.raises(ValueError, match="left root ownership was not preserved"):
        CoherentHiddenWorld(
            left_hand=("H7",),
            right_hand=("SA",),
            hypothetical_skat=("D7",),
            provenance=root.provenance,
        )

    ordered_root = CoherentHiddenWorld(("SA", "S10"), ("H7",), ("D7",))
    with pytest.raises(ValueError, match="left root ownership was not preserved"):
        CoherentHiddenWorld(
            left_hand=("S10", "SA"),
            right_hand=("H7",),
            hypothetical_skat=("D7",),
            provenance=ordered_root.provenance,
        )


def test_summary_contains_only_privacy_safe_counts_and_invariants() -> None:
    world = apply_hidden_world_plays(
        CoherentHiddenWorld(("SA", "S10"), ("H7",), ("D7",)),
        (("left", "SA"),),
    )

    summary = build_hidden_world_summary(world)

    assert summary == {
        "mode": "coherent_path",
        "initial_left_hand_size": 2,
        "initial_right_hand_size": 1,
        "initial_hypothetical_skat_size": 1,
        "remaining_left_hand_size": 1,
        "remaining_right_hand_size": 1,
        "remaining_hypothetical_skat_size": 1,
        "root_sample_count": 1,
        "sampled_once": True,
        "resampled_after_path_start": False,
        "ownership_transition_count": 1,
        "opponent_cards_played": 1,
        "ownership_preserved": True,
        "hand_sizes_reconciled": True,
        "hypothetical_skat_fixed": True,
        "duplicate_card_detected": False,
        "ownership_violation_detected": False,
        "hidden_cards_emitted": False,
    }
    assert not any(card in repr(summary) for card in ("SA", "S10", "H7", "D7"))


def test_child_seed_is_stable_and_separates_streams() -> None:
    root_seed = derive_simulation_child_seed(42, "root_world")

    assert root_seed == derive_simulation_child_seed(42, "root_world")
    assert root_seed != derive_simulation_child_seed(42, "opponent_actions")
    assert root_seed != derive_simulation_child_seed(42, "root_world", child_index=1)
    assert derive_simulation_child_seed(None, "root_world") is None
    assert isinstance(root_seed, int)


def test_exact_world_immediate_completion_bypasses_sampling_and_returns_transition(
    monkeypatch,
) -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA"],
        current_trick=["S7"],
        trick_leader="right",
        next_player="me",
    )
    world = _world_from_hands(state, ("S8", "H10"), ("D7",))

    monkeypatch.setattr(
        "skat_ai.simulation.generate_random_opponent_hands",
        lambda **_kwargs: pytest.fail("exact-world execution must not sample"),
    )
    result = simulate_immediate_trick_once_detailed(
        state=state,
        candidate_card="SA",
        left_hand_size=2,
        right_hand_size=1,
        coherent_hidden_world=world,
        coherent_step_index=4,
    )

    assert result["trick"] == ["S7", "SA", "S8"]
    assert result["_opponent_plays"] == (("left", "S8"),)
    assert result["_coherent_hidden_world"].left_hand == ("H10",)
    assert result["_coherent_hidden_world"].right_hand == world.right_hand
    assert result["_coherent_hidden_world"].hypothetical_skat == world.hypothetical_skat


def test_exact_world_opponent_preparation_bypasses_sampling_and_removes_owner_card(
    monkeypatch,
) -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA"],
        current_trick=[],
        trick_leader="right",
        next_player="right",
    )
    world = _world_from_hands(state, ("H10",), ("S7", "D10"))

    monkeypatch.setattr(
        "skat_ai.opponent_lead.generate_random_opponent_hands",
        lambda **_kwargs: pytest.fail("exact-world preparation must not sample"),
    )
    result = simulate_opponent_lead_once(
        state=state,
        left_hand_size=1,
        right_hand_size=2,
        coherent_hidden_world=world,
        coherent_step_index=2,
    )

    assert result["lead_card"] == "S7"
    assert result["_opponent_plays"] == (("right", "S7"),)
    assert result["_coherent_hidden_world"].right_hand == ("D10",)


def test_exact_world_covers_all_supported_preparation_paths_without_sampling(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "skat_ai.opponent_lead.generate_random_opponent_hands",
        lambda **_kwargs: pytest.fail("exact-world preparation must not sample"),
    )
    left_lead_state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA"],
        current_trick=[],
        trick_leader="left",
        next_player="left",
    )
    left_lead_world = _world_from_hands(
        left_lead_state,
        ("D7", "DA"),
        ("D8", "D10"),
    )
    sequence = simulate_left_lead_and_right_response_once(
        state=left_lead_state,
        left_hand_size=2,
        right_hand_size=2,
        coherent_hidden_world=left_lead_world,
    )

    assert sequence["_opponent_plays"] == (("left", "D7"), ("right", "D8"))
    assert sequence["_coherent_hidden_world"].left_hand == ("DA",)
    assert sequence["_coherent_hidden_world"].right_hand == ("D10",)

    response_state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA"],
        current_trick=["D7"],
        trick_leader="left",
        next_player="right",
    )
    response_world = _world_from_hands(response_state, ("C7",), ("D8", "DA"))
    response = simulate_right_response_to_left_lead_once(
        state=response_state,
        left_hand_size=1,
        right_hand_size=2,
        coherent_hidden_world=response_world,
    )

    assert response["_opponent_plays"] == (("right", "D8"),)
    assert response["_coherent_hidden_world"].right_hand == ("DA",)

    local_state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA"],
        current_trick=[],
        trick_leader="me",
        next_player="me",
    )
    local_world = _world_from_hands(local_state, ("D7",), ("D8",))
    prepared_state, preparation = prepare_player_action_state(
        current_state=local_state,
        left_hand_size=1,
        right_hand_size=1,
        random_generator=random.Random(1),
        coherent_hidden_world=local_world,
    )

    assert prepared_state is local_state
    assert preparation is None


def test_exact_world_rejects_contradictory_hand_sizes() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA"],
        current_trick=[],
        trick_leader="right",
        next_player="right",
    )
    world = _world_from_hands(state, ("D7",), ("D8",))

    with pytest.raises(ValueError, match="right hand has 1 cards, expected 2"):
        simulate_opponent_lead_once(
            state=state,
            left_hand_size=1,
            right_hand_size=2,
            coherent_hidden_world=world,
            coherent_step_index=7,
        )

    local_state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA"],
        current_trick=[],
        trick_leader="me",
        next_player="me",
    )
    local_world = _world_from_hands(local_state, ("D7",), ("D8",))
    with pytest.raises(ValueError, match="step 8.*left hand has 1 cards, expected 2"):
        prepare_player_action_state(
            current_state=local_state,
            left_hand_size=2,
            right_hand_size=1,
            random_generator=random.Random(1),
            coherent_hidden_world=local_world,
            coherent_step_index=8,
        )


def test_multi_step_builds_one_root_and_reconciles_complete_path(monkeypatch) -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        declarer_player="me",
        hand=["SA", "H10"],
        current_trick=[],
        trick_leader="me",
        next_player="me",
    )
    calls = 0
    from skat_ai.multi_step_simulation import (
        build_coherent_hidden_world as real_builder,
    )

    def counting_builder(**kwargs):
        nonlocal calls
        calls += 1
        return real_builder(**kwargs)

    monkeypatch.setattr(
        "skat_ai.multi_step_simulation.build_coherent_hidden_world",
        counting_builder,
    )
    result = simulate_multiple_steps(
        state=state,
        left_hand_size=2,
        right_hand_size=2,
        step_count=2,
        random_seed=17,
        strict_context=True,
        card_selection_policy="highest_point",
    )

    summary = result["context_summary"]["hidden_world"]
    assert calls == 1
    assert result["steps_simulated"] == 2
    assert summary["root_sample_count"] == 1
    assert summary["resampled_after_path_start"] is False
    assert summary["ownership_transition_count"] == 4
    assert summary["remaining_left_hand_size"] == 0
    assert summary["remaining_right_hand_size"] == 0
    assert summary["remaining_hypothetical_skat_size"] == summary[
        "initial_hypothetical_skat_size"
    ]


def test_highest_expected_value_receives_only_public_counterfactual_inputs(
    monkeypatch,
) -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        declarer_player="me",
        hand=["SA"],
        current_trick=[],
        trick_leader="me",
        next_player="me",
    )
    world = _world_from_hands(state, ("S7",), ("S8",))
    calls = []

    def fake_estimator(**kwargs):
        calls.append(kwargs)
        return {
            "SA": {
                "win_rate": 1.0,
                "average_trick_points": 11.0,
                "average_points_won": 11.0,
                "average_points_lost": 0.0,
            }
        }

    monkeypatch.setattr(
        "skat_ai.card_selection.estimate_immediate_trick_values_for_legal_cards",
        fake_estimator,
    )
    result = simulate_multiple_steps(
        state=state,
        left_hand_size=1,
        right_hand_size=1,
        step_count=1,
        random_seed=23,
        card_selection_policy="highest_expected_value",
        expected_value_sample_count=7,
        initial_hidden_world=world,
    )

    assert result["steps"][0]["candidate_card"] == "SA"
    assert len(calls) == 1
    assert calls[0]["sample_count"] == 7
    assert "coherent_hidden_world" not in calls[0]
    assert not set(world.hypothetical_skat).intersection(
        calls[0]["state"].hand
        + calls[0]["state"].current_trick
        + calls[0]["state"].played_cards
    )


def test_root_and_path_actions_are_stable_across_evaluation_and_diagnostics() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        declarer_player="me",
        hand=["SA", "H10"],
        current_trick=[],
        trick_leader="me",
        next_player="me",
    )
    low_samples = simulate_multiple_steps(
        state=state,
        left_hand_size=2,
        right_hand_size=2,
        step_count=1,
        random_seed=37,
        card_selection_policy="highest_expected_value",
        expected_value_sample_count=1,
        strict_context=False,
    )
    high_samples = simulate_multiple_steps(
        state=state,
        left_hand_size=2,
        right_hand_size=2,
        step_count=1,
        random_seed=37,
        card_selection_policy="highest_expected_value",
        expected_value_sample_count=5,
        strict_context=True,
    )

    def reconstruct_root(result, player: str) -> set[str]:
        world = result["context"].hidden_world
        assert world is not None
        current_hand = set(getattr(world, f"{player}_hand"))
        played = {
            card
            for owner, card in world.ownership_transitions
            if owner == player
        }
        return current_hand | played

    assert reconstruct_root(low_samples, "left") == reconstruct_root(
        high_samples, "left"
    )
    assert reconstruct_root(low_samples, "right") == reconstruct_root(
        high_samples, "right"
    )
    assert (
        low_samples["context"].hidden_world.hypothetical_skat
        == high_samples["context"].hidden_world.hypothetical_skat
    )

    non_strict = simulate_multiple_steps(
        state=state,
        left_hand_size=2,
        right_hand_size=2,
        step_count=1,
        random_seed=41,
        card_selection_policy="highest_point",
        strict_context=False,
    )
    strict = simulate_multiple_steps(
        state=state,
        left_hand_size=2,
        right_hand_size=2,
        step_count=1,
        random_seed=41,
        card_selection_policy="highest_point",
        strict_context=True,
    )
    assert non_strict["steps"] == strict["steps"]
    assert non_strict["final_state"] == strict["final_state"]


def test_policy_comparison_passes_equal_distinct_root_copies(monkeypatch) -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA"],
        current_trick=["S7", "S8"],
        trick_leader="left",
        next_player="me",
    )
    received_worlds = []

    def fake_simulate_multiple_steps(**kwargs):
        received_worlds.append(kwargs["initial_hidden_world"])
        return {
            "final_state": kwargs["state"],
            "summary": {
                "requested_step_count": kwargs["step_count"],
                "steps_simulated": 1,
                "stop_reason": "Requested step count reached.",
                "strict_context": kwargs["strict_context"],
                "score_summary": {
                    "declarer_points_gained": 0,
                    "defender_points_gained": 0,
                    "final_point_swing": 0,
                    "local_point_swing": 0,
                },
                "context_summary": {},
            },
        }

    monkeypatch.setattr(
        "skat_ai.policy_comparison.simulate_multiple_steps",
        fake_simulate_multiple_steps,
    )
    result = compare_multi_step_policies(
        state=state,
        left_hand_size=0,
        right_hand_size=0,
        step_count=1,
        policies=["first_legal", "highest_point"],
        random_seed=29,
    )

    assert received_worlds[0] == received_worlds[1]
    assert received_worlds[0] is not received_worlds[1]
    assert received_worlds[0].ownership_transitions == ()
    assert result["hidden_world"] == {
        "mode": "coherent_path",
        "shared_root_world": True,
        "root_sample_count": 1,
        "policy_path_count": 2,
        "independent_path_worlds": True,
        "hidden_cards_emitted": False,
    }


def test_strict_context_rejects_tampered_owner_evidence() -> None:
    state = _state()
    world = build_coherent_hidden_world(state, 1, 1, random.Random(31))
    card = world.left_hand[0]
    transitioned = remove_card_from_hidden_world(world, "left", card, step_index=5)
    state.played_cards.append(card)
    context = SimulationContext(
        simulated_opponent_cards=[card],
        simulated_opponent_card_ownership=[("right", card)],
        hidden_world=transitioned,
        root_hidden_world=world,
    )

    with pytest.raises(ValueError, match="step 5.*ownership evidence"):
        validate_simulation_context(context, state, step_index=5)


def test_strict_context_rejects_replacement_root_world() -> None:
    state = _state()
    original = build_coherent_hidden_world(state, 2, 2, random.Random(1))
    replacement = build_coherent_hidden_world(state, 2, 2, random.Random(2))
    assert replacement != original
    context = SimulationContext(
        hidden_world=replacement,
        root_hidden_world=original,
    )

    with pytest.raises(ValueError, match="step 6.*sampled root ownership"):
        validate_simulation_context(context, state, step_index=6)
