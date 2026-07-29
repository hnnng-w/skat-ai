import random

import pytest

from skat_ai.game_state import GameState
from skat_ai.hidden_card_inference import (
    CompatibleAssignmentProblem,
    build_hidden_card_inference_constraints,
    build_hidden_card_inference_model,
    build_hidden_card_inference_summary,
    calculate_hidden_card_ownership_marginals,
    classify_hidden_card_confidence,
    count_compatible_assignments,
    count_compatible_hidden_worlds,
    derive_failed_to_follow_evidence,
    sample_compatible_hidden_world,
)
from skat_ai.multi_step_simulation import simulate_multiple_steps
from skat_ai.policy_comparison import compare_multi_step_policies
from skat_ai.public_hand_constraint import PublicHandConstraint
from skat_ai.simulation import (
    estimate_immediate_trick_values_for_legal_cards,
    generate_sampled_hidden_state,
)


def _completed_trick(
    cards: list[str],
    players: list[str] | None = None,
) -> dict:
    trick = {"cards": cards, "winner_role": "defenders"}
    if players is not None:
        trick["players"] = players
    return trick


@pytest.mark.parametrize(
    ("game_type", "lead_card", "response_card", "expected_category"),
    [
        ("clubs", "S7", "H7", "spades"),
        ("clubs", "CJ", "S7", "trump"),
        ("clubs", "S7", "CJ", "spades"),
        ("grand", "C7", "H7", "clubs"),
        ("grand", "CJ", "C7", "trump"),
        ("null", "C7", "H7", "clubs"),
    ],
)
def test_failure_to_follow_uses_existing_effective_categories(
    game_type: str,
    lead_card: str,
    response_card: str,
    expected_category: str,
) -> None:
    state = GameState(
        game_type=game_type,
        player_role="declarer",
        hand=[],
        current_trick=[],
        completed_tricks=[
            _completed_trick(
                [lead_card, response_card, "D8"],
                ["left", "right", "me"],
            )
        ],
    )

    evidence = derive_failed_to_follow_evidence(state)

    assert any(
        item.player == "right" and item.effective_category == expected_category
        for item in evidence
    )


def test_following_and_leading_create_no_void_evidence() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=[],
        current_trick=[],
        completed_tricks=[
            _completed_trick(["C7", "CA", "C10"], ["left", "right", "me"])
        ],
    )

    assert derive_failed_to_follow_evidence(state) == ()


def test_duplicate_void_evidence_is_deduplicated_at_earliest_source() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=[],
        current_trick=[],
        completed_tricks=[
            _completed_trick(["C7", "H7", "D7"], ["left", "right", "me"]),
            _completed_trick(["C8", "H8", "D8"], ["left", "right", "me"]),
        ],
    )

    evidence = derive_failed_to_follow_evidence(state)
    right_clubs = [
        item
        for item in evidence
        if item.player == "right" and item.effective_category == "clubs"
    ]

    assert len(right_clubs) == 1
    assert right_clubs[0].source_trick_number == 1
    assert right_clubs[0].source_play_index == 2


def test_current_trick_evidence_is_immediate_and_requires_concrete_leader() -> None:
    concrete = GameState(
        game_type="null",
        player_role="declarer",
        hand=["S7"],
        current_trick=["C7", "H7"],
        trick_leader="left",
    )
    ambiguous = GameState(
        game_type="null",
        player_role="declarer",
        hand=["S7"],
        current_trick=["C7", "H7"],
        trick_leader="unknown",
    )

    evidence = derive_failed_to_follow_evidence(concrete)

    assert [(item.player, item.effective_category) for item in evidence] == [
        ("right", "clubs")
    ]
    assert evidence[0].source == "current_trick"
    assert derive_failed_to_follow_evidence(ambiguous) == ()


def test_legacy_card_only_history_is_not_guessed() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["S7"],
        current_trick=[],
        played_cards=["C7", "H7", "D7"],
        completed_tricks=[_completed_trick(["S8", "H8", "D8"])],
    )

    constraints = build_hidden_card_inference_constraints(state)

    assert constraints.confirmed_void_evidence == ()
    assert constraints.provenance_status == "not_available_missing_play_provenance"


def test_void_evidence_rejects_conflicting_exact_public_hand() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["S7"],
        current_trick=["C7", "H7"],
        trick_leader="left",
    )
    public_right = PublicHandConstraint(player="right", cards=("CA",))

    with pytest.raises(ValueError, match="right.*void in clubs.*CA"):
        build_hidden_card_inference_constraints(state, (public_right,))


def test_void_evidence_rejects_later_public_ownership() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["S7"],
        current_trick=[],
        completed_tricks=[
            _completed_trick(["C7", "H7", "D7"], ["left", "right", "me"]),
            _completed_trick(["CA", "S8", "H8"], ["right", "me", "left"]),
        ],
    )

    with pytest.raises(ValueError, match="right.*void in clubs.*CA"):
        build_hidden_card_inference_constraints(state)


def test_exact_dynamic_programming_counts_controlled_assignments() -> None:
    cards = ("CA", "SA", "HA")
    all_locations = {card: ("left", "right", "skat") for card in cards}

    assert count_compatible_assignments(cards, 1, 1, all_locations) == 6
    assert count_compatible_assignments(
        cards,
        1,
        1,
        {"CA": ("left",), "SA": ("right",), "HA": ("skat",)},
    ) == 1
    assert count_compatible_assignments(
        cards,
        1,
        1,
        {"CA": ("left",), "SA": ("left",), "HA": ("skat",)},
    ) == 0


def test_exact_marginals_cover_three_locations_and_deterministic_tie() -> None:
    cards = ("CA", "SA", "HA")
    problem = CompatibleAssignmentProblem(
        cards=cards,
        left_slots=1,
        right_slots=1,
        skat_slots=1,
        allowed_locations_by_card=tuple(
            (card, ("left", "right", "skat")) for card in cards
        ),
    )

    marginals = calculate_hidden_card_ownership_marginals(problem)

    assert count_compatible_hidden_worlds(problem) == 6
    assert [item.card for item in marginals] == list(cards)
    assert marginals[0].owner_assignment_counts == (
        ("left", 2),
        ("right", 2),
        ("skat", 2),
    )


@pytest.mark.parametrize(
    ("probability", "owner_count", "expected"),
    [
        (1.0, 1, "confirmed"),
        (0.85, 2, "high"),
        (0.849, 2, "medium"),
        (0.65, 2, "medium"),
        (0.649, 2, "low"),
    ],
)
def test_confidence_has_exact_bounded_semantics(
    probability: float,
    owner_count: int,
    expected: str,
) -> None:
    assert classify_hidden_card_confidence(probability, owner_count) == expected


def test_uniform_sampler_is_fixed_seed_deterministic_and_respects_slots() -> None:
    cards = ("CA", "SA", "HA")
    problem = CompatibleAssignmentProblem(
        cards=cards,
        left_slots=1,
        right_slots=1,
        skat_slots=1,
        allowed_locations_by_card=(
            ("CA", ("left", "skat")),
            ("SA", ("left", "right", "skat")),
            ("HA", ("right", "skat")),
        ),
    )

    first = [sample_compatible_hidden_world(problem, random.Random(seed)) for seed in range(10)]
    second = [sample_compatible_hidden_world(problem, random.Random(seed)) for seed in range(10)]

    assert first == second
    for world in first:
        assert len(world.left_hand) == 1
        assert len(world.right_hand) == 1
        assert len(world.hypothetical_skat) == 1
        assert set(world.left_hand + world.right_hand + world.hypothetical_skat) == set(
            cards
        )
        assert "CA" not in world.right_hand
        assert "HA" not in world.left_hand


def _physical_grand_state_with_right_clubs_void() -> GameState:
    return GameState(
        game_type="grand",
        player_role="declarer",
        hand=["CJ", "SJ", "HJ", "DJ", "SA", "S10", "HA", "H10", "DA"],
        current_trick=[],
        completed_tricks=[
            _completed_trick(["C7", "H7", "CA"], ["left", "right", "me"])
        ],
        trick_leader="me",
    )


def test_model_count_marginals_sampling_and_summary_are_exact_and_private() -> None:
    state = _physical_grand_state_with_right_clubs_void()
    model = build_hidden_card_inference_model(state, 9, 9)

    assert model is not None
    assert model.compatible_world_count > 0
    assert model.assignment_problem.skat_slots == 2
    assert model.compatible_world_count == count_compatible_hidden_worlds(
        model.assignment_problem
    )

    samples = [
        generate_sampled_hidden_state(
            state,
            9,
            9,
            random.Random(seed),
            hidden_card_inference_model=model,
        )
        for seed in range(20)
    ]
    assert all(
        not any(card.startswith("C") for card in sample.right_hand)
        for sample in samples
    )

    summary = build_hidden_card_inference_summary(model)
    assert summary is not None
    assert summary["compatible_world_count"] == model.compatible_world_count
    assert summary["confirmed_voids"] == [
        {"player": "right", "forbidden_effective_categories": ["clubs"]}
    ]
    assert summary["confidence_is_calibrated"] is False
    assert summary["behavioral_inference_applied"] is False
    assert summary["future_information_used"] is False
    assert summary["actual_hidden_hands_emitted"] is False
    assert all(not value for value in summary["privacy_flags"].values())
    serialized = repr(summary).lower()
    assert "left_hand" not in serialized
    assert "right_hand" not in serialized
    assert "dynamic_programming" in serialized
    for estimate in summary["ownership_estimates"]:
        assert sum(estimate["ownership_probability"].values()) == pytest.approx(1.0)


def test_immediate_candidates_receive_one_common_compatible_world_sequence(
    monkeypatch,
) -> None:
    state = _physical_grand_state_with_right_clubs_void()
    observed_samples = []

    def capture_common_samples(**kwargs):
        observed_samples.append(kwargs["sampled_hidden_states"])
        return {
            "win_rate": 0.5,
            "average_trick_points": 1.0,
            "average_points_won": 0.5,
            "average_points_lost": 0.5,
        }

    monkeypatch.setattr(
        "skat_ai.simulation.estimate_immediate_trick_value",
        capture_common_samples,
    )

    values = estimate_immediate_trick_values_for_legal_cards(
        state,
        9,
        9,
        sample_count=5,
        random_seed=42,
    )

    assert set(values) == set(state.hand)
    assert len(observed_samples) == len(state.hand)
    assert all(samples is observed_samples[0] for samples in observed_samples)
    assert len(observed_samples[0]) == 5
    assert all(
        not any(card.startswith("C") for card in sample.right_hand)
        for sample in observed_samples[0]
    )


def test_multi_step_and_policy_comparison_share_compatible_root_evidence() -> None:
    state = _physical_grand_state_with_right_clubs_void()

    multi_step = simulate_multiple_steps(
        state,
        9,
        9,
        step_count=2,
        random_seed=42,
        card_selection_policy="first_legal",
    )
    comparison = compare_multi_step_policies(
        state,
        9,
        9,
        step_count=1,
        policies=["first_legal", "lowest_point"],
        random_seed=42,
    )

    root_summary = build_hidden_card_inference_summary(
        build_hidden_card_inference_model(state, 9, 9)
    )
    assert multi_step["hidden_card_inference_summary"] == root_summary
    assert comparison["hidden_card_inference_summary"] == root_summary
    assert comparison["hidden_world"]["shared_root_world"] is True
    assert comparison["hidden_world"]["root_sample_count"] == 1
    assert all(
        step["coherence_summary"]["ownership_violation_detected"] is False
        for step in multi_step["steps"]
    )


def test_no_confirmed_void_preserves_optional_inference_path() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["CA"],
        current_trick=[],
        played_cards=["C7", "H7", "D7"],
    )

    assert build_hidden_card_inference_model(state, 1, 1) is None
    assert build_hidden_card_inference_summary(None) is None


def test_cli_summary_prints_only_bounded_public_diagnostics(capsys) -> None:
    from main import print_hidden_card_inference_summary

    model = build_hidden_card_inference_model(
        _physical_grand_state_with_right_clubs_void(),
        9,
        9,
    )
    print_hidden_card_inference_summary(build_hidden_card_inference_summary(model))

    output = capsys.readouterr().out
    assert "Hidden-card inference: applied" in output
    assert "right is void in Clubs" in output
    assert "Compatible hidden worlds: 275275" in output
    assert "Highest bounded estimate:" in output
    assert "left_hand" not in output
    assert "right_hand" not in output
