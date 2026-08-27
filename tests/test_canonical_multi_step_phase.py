from dataclasses import FrozenInstanceError

import pytest

from skat_ai.canonical_multi_step_phase import (
    CANONICAL_MULTI_STEP_PHASE_ACTIONS,
    CANONICAL_MULTI_STEP_PHASE_CLASSIFICATION_POLICY,
    CANONICAL_MULTI_STEP_PHASE_COMPATIBILITY_POLICY,
    CANONICAL_MULTI_STEP_PHASE_COMPLETION_POLICY,
    CANONICAL_MULTI_STEP_PHASE_CONTINUATION_POLICY,
    CANONICAL_MULTI_STEP_PHASE_COVERAGE_VERSION,
    CANONICAL_MULTI_STEP_PHASE_PROVENANCE_POLICY,
    CANONICAL_MULTI_STEP_PHASE_RANDOM_POLICY,
    CANONICAL_MULTI_STEP_PHASE_SEARCH_POLICY,
    CANONICAL_MULTI_STEP_PHASE_SOURCE_POLICY,
    CANONICAL_MULTI_STEP_PHASE_STEP_COUNT_POLICY,
    CANONICAL_MULTI_STEP_PHASE_TERMINATION_POLICY,
    CANONICAL_MULTI_STEP_PHASE_WORLD_POLICY,
    COMPLETE_CURRENT_TRICK_THEN_CONTINUE,
    LOCAL_ACTION,
    PREPARE_TO_LOCAL_ACTION,
    CanonicalMultiStepPhasePlanV1,
    build_canonical_multi_step_phase_plan_v1,
)
from skat_ai.turn_phase import TurnPhase


@pytest.mark.parametrize(
    (
        "trick_leader",
        "current_trick_length",
        "next_player",
        "phase_action",
        "completion_players",
    ),
    [
        ("me", 0, "me", LOCAL_ACTION, ()),
        (
            "me",
            1,
            "left",
            COMPLETE_CURRENT_TRICK_THEN_CONTINUE,
            ("left", "right"),
        ),
        (
            "me",
            2,
            "right",
            COMPLETE_CURRENT_TRICK_THEN_CONTINUE,
            ("right",),
        ),
        ("left", 0, "left", PREPARE_TO_LOCAL_ACTION, ()),
        ("left", 1, "right", PREPARE_TO_LOCAL_ACTION, ()),
        ("left", 2, "me", LOCAL_ACTION, ()),
        ("right", 0, "right", PREPARE_TO_LOCAL_ACTION, ()),
        ("right", 1, "me", LOCAL_ACTION, ()),
        (
            "right",
            2,
            "left",
            COMPLETE_CURRENT_TRICK_THEN_CONTINUE,
            ("left",),
        ),
    ],
)
def test_build_canonical_multi_step_phase_plan_covers_exact_table(
    trick_leader: str,
    current_trick_length: int,
    next_player: str,
    phase_action: str,
    completion_players: tuple[str, ...],
) -> None:
    plan = build_canonical_multi_step_phase_plan_v1(
        TurnPhase(trick_leader=trick_leader, next_player=next_player),
        current_trick_length,
    )

    assert plan is not None
    assert plan.to_dict() == {
        "canonical_multi_step_phase_coverage_version": 1,
        "trick_leader": trick_leader,
        "current_trick_length": current_trick_length,
        "next_player": next_player,
        "phase_action": phase_action,
        "local_card_already_played": (
            phase_action == COMPLETE_CURRENT_TRICK_THEN_CONTINUE
        ),
        "opponent_plays_required_to_complete_current_trick": len(
            completion_players
        ),
        "completion_players": list(completion_players),
    }


def test_canonical_multi_step_phase_contract_is_exact_and_stable() -> None:
    assert CANONICAL_MULTI_STEP_PHASE_COVERAGE_VERSION == 1
    assert CANONICAL_MULTI_STEP_PHASE_ACTIONS == (
        "local_action",
        "prepare_to_local_action",
        "complete_current_trick_then_continue",
    )
    assert CANONICAL_MULTI_STEP_PHASE_SOURCE_POLICY == (
        "normalized_concrete_turn_phase_only"
    )
    assert CANONICAL_MULTI_STEP_PHASE_CLASSIFICATION_POLICY == (
        "exact_leader_length_and_next_player_table"
    )
    assert CANONICAL_MULTI_STEP_PHASE_COMPLETION_POLICY == (
        "complete_existing_trick_without_replaying_local_card"
    )
    assert CANONICAL_MULTI_STEP_PHASE_CONTINUATION_POLICY == (
        "continue_from_completed_winner_to_next_local_decision"
    )
    assert CANONICAL_MULTI_STEP_PHASE_STEP_COUNT_POLICY == (
        "count_new_local_decisions_only"
    )
    assert CANONICAL_MULTI_STEP_PHASE_WORLD_POLICY == (
        "one_coherent_world_without_resampling_or_search_disclosure"
    )
    assert CANONICAL_MULTI_STEP_PHASE_RANDOM_POLICY == (
        "chronological_existing_opponent_action_stream"
    )
    assert CANONICAL_MULTI_STEP_PHASE_SEARCH_POLICY == (
        "search_only_at_new_local_decision_boundaries"
    )
    assert CANONICAL_MULTI_STEP_PHASE_TERMINATION_POLICY == (
        "existing_non_error_stop_without_synthetic_local_action"
    )
    assert CANONICAL_MULTI_STEP_PHASE_COMPATIBILITY_POLICY == (
        "preserve_supported_phase_outputs_and_public_shape"
    )
    assert CANONICAL_MULTI_STEP_PHASE_PROVENANCE_POLICY == (
        "retained_transition_evidence_without_workflow_rerun"
    )


def test_canonical_multi_step_phase_plan_is_immutable() -> None:
    plan = build_canonical_multi_step_phase_plan_v1(
        TurnPhase(trick_leader="me", next_player="left"),
        1,
    )

    assert plan is not None
    with pytest.raises(FrozenInstanceError):
        plan.next_player = "right"  # type: ignore[misc]


def test_canonical_multi_step_phase_builder_excludes_unresolved_phase() -> None:
    assert (
        build_canonical_multi_step_phase_plan_v1(
            TurnPhase(trick_leader="unknown", next_player="unknown"),
            0,
        )
        is None
    )


def test_canonical_multi_step_phase_plan_is_builder_controlled() -> None:
    with pytest.raises(
        ValueError,
        match="must be created by its builder",
    ):
        CanonicalMultiStepPhasePlanV1(
            canonical_multi_step_phase_coverage_version=1,
            trick_leader="me",
            current_trick_length=0,
            next_player="me",
            phase_action=LOCAL_ACTION,
            local_card_already_played=False,
            opponent_plays_required_to_complete_current_trick=0,
            completion_players=(),
        )


@pytest.mark.parametrize("invalid_value", [True, False, 0.0, "0"])
def test_canonical_multi_step_phase_builder_rejects_non_strict_length(
    invalid_value: object,
) -> None:
    with pytest.raises(ValueError, match="strict integer"):
        build_canonical_multi_step_phase_plan_v1(
            TurnPhase(trick_leader="me", next_player="me"),
            invalid_value,  # type: ignore[arg-type]
        )
