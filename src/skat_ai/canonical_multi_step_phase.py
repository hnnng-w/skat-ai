from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from skat_ai.turn_phase import TurnPhase, is_concrete_player

CANONICAL_MULTI_STEP_PHASE_COVERAGE_VERSION = 1

LOCAL_ACTION = "local_action"
PREPARE_TO_LOCAL_ACTION = "prepare_to_local_action"
COMPLETE_CURRENT_TRICK_THEN_CONTINUE = "complete_current_trick_then_continue"
CANONICAL_MULTI_STEP_PHASE_ACTIONS = (
    LOCAL_ACTION,
    PREPARE_TO_LOCAL_ACTION,
    COMPLETE_CURRENT_TRICK_THEN_CONTINUE,
)

CANONICAL_MULTI_STEP_PHASE_SOURCE_POLICY = "normalized_concrete_turn_phase_only"
CANONICAL_MULTI_STEP_PHASE_CLASSIFICATION_POLICY = (
    "exact_leader_length_and_next_player_table"
)
CANONICAL_MULTI_STEP_PHASE_COMPLETION_POLICY = (
    "complete_existing_trick_without_replaying_local_card"
)
CANONICAL_MULTI_STEP_PHASE_CONTINUATION_POLICY = (
    "continue_from_completed_winner_to_next_local_decision"
)
CANONICAL_MULTI_STEP_PHASE_STEP_COUNT_POLICY = "count_new_local_decisions_only"
CANONICAL_MULTI_STEP_PHASE_WORLD_POLICY = (
    "one_coherent_world_without_resampling_or_search_disclosure"
)
CANONICAL_MULTI_STEP_PHASE_RANDOM_POLICY = (
    "chronological_existing_opponent_action_stream"
)
CANONICAL_MULTI_STEP_PHASE_SEARCH_POLICY = (
    "search_only_at_new_local_decision_boundaries"
)
CANONICAL_MULTI_STEP_PHASE_TERMINATION_POLICY = (
    "existing_non_error_stop_without_synthetic_local_action"
)
CANONICAL_MULTI_STEP_PHASE_COMPATIBILITY_POLICY = (
    "preserve_supported_phase_outputs_and_public_shape"
)
CANONICAL_MULTI_STEP_PHASE_PROVENANCE_POLICY = (
    "retained_transition_evidence_without_workflow_rerun"
)

_PLAN_CONSTRUCTION_TOKEN = object()
_PHASE_ROWS = {
    ("me", 0, "me"): (LOCAL_ACTION, ()),
    ("me", 1, "left"): (
        COMPLETE_CURRENT_TRICK_THEN_CONTINUE,
        ("left", "right"),
    ),
    ("me", 2, "right"): (COMPLETE_CURRENT_TRICK_THEN_CONTINUE, ("right",)),
    ("left", 0, "left"): (PREPARE_TO_LOCAL_ACTION, ()),
    ("left", 1, "right"): (PREPARE_TO_LOCAL_ACTION, ()),
    ("left", 2, "me"): (LOCAL_ACTION, ()),
    ("right", 0, "right"): (PREPARE_TO_LOCAL_ACTION, ()),
    ("right", 1, "me"): (LOCAL_ACTION, ()),
    ("right", 2, "left"): (COMPLETE_CURRENT_TRICK_THEN_CONTINUE, ("left",)),
}


@dataclass(frozen=True, slots=True, init=False)
class CanonicalMultiStepPhasePlanV1:
    """One validated internal action for a concrete canonical turn phase."""

    canonical_multi_step_phase_coverage_version: int
    trick_leader: str
    current_trick_length: int
    next_player: str
    phase_action: str
    local_card_already_played: bool
    opponent_plays_required_to_complete_current_trick: int
    completion_players: tuple[str, ...]

    def __init__(
        self,
        *,
        canonical_multi_step_phase_coverage_version: int,
        trick_leader: str,
        current_trick_length: int,
        next_player: str,
        phase_action: str,
        local_card_already_played: bool,
        opponent_plays_required_to_complete_current_trick: int,
        completion_players: tuple[str, ...],
        _construction_token: object | None = None,
    ) -> None:
        if _construction_token is not _PLAN_CONSTRUCTION_TOKEN:
            raise ValueError(
                "CanonicalMultiStepPhasePlanV1 must be created by its builder."
            )
        values = {
            "canonical_multi_step_phase_coverage_version": (
                canonical_multi_step_phase_coverage_version
            ),
            "trick_leader": trick_leader,
            "current_trick_length": current_trick_length,
            "next_player": next_player,
            "phase_action": phase_action,
            "local_card_already_played": local_card_already_played,
            "opponent_plays_required_to_complete_current_trick": (
                opponent_plays_required_to_complete_current_trick
            ),
            "completion_players": completion_players,
        }
        for field_name, value in values.items():
            object.__setattr__(self, field_name, value)
        validate_canonical_multi_step_phase_plan_v1(self)

    def to_dict(self) -> dict[str, Any]:
        """Builds a defensive representation for internal tests and diagnostics."""
        return {
            "canonical_multi_step_phase_coverage_version": (
                self.canonical_multi_step_phase_coverage_version
            ),
            "trick_leader": self.trick_leader,
            "current_trick_length": self.current_trick_length,
            "next_player": self.next_player,
            "phase_action": self.phase_action,
            "local_card_already_played": self.local_card_already_played,
            "opponent_plays_required_to_complete_current_trick": (
                self.opponent_plays_required_to_complete_current_trick
            ),
            "completion_players": list(self.completion_players),
        }


def validate_canonical_multi_step_phase_plan_v1(
    plan: CanonicalMultiStepPhasePlanV1,
) -> None:
    """Validates one builder-controlled canonical phase plan."""
    version = plan.canonical_multi_step_phase_coverage_version
    if isinstance(version, bool) or not isinstance(version, int) or version != 1:
        raise ValueError("Unsupported canonical Multi-Step phase coverage version.")
    if (
        isinstance(plan.current_trick_length, bool)
        or not isinstance(plan.current_trick_length, int)
        or plan.current_trick_length not in (0, 1, 2)
    ):
        raise ValueError("current_trick_length must be a strict integer from 0 to 2.")
    if not isinstance(plan.completion_players, tuple):
        raise TypeError("completion_players must be a tuple.")

    key = (plan.trick_leader, plan.current_trick_length, plan.next_player)
    expected = _PHASE_ROWS.get(key)
    if expected is None:
        raise ValueError("Phase plan does not identify a canonical concrete phase.")
    expected_action, expected_completion_players = expected
    if plan.phase_action != expected_action:
        raise ValueError("Phase plan action does not match the canonical phase table.")
    if plan.phase_action not in CANONICAL_MULTI_STEP_PHASE_ACTIONS:
        raise ValueError("Phase plan action is not canonical.")
    if plan.completion_players != expected_completion_players:
        raise ValueError("Phase plan completion players do not match the phase table.")
    if plan.local_card_already_played is not (
        expected_action == COMPLETE_CURRENT_TRICK_THEN_CONTINUE
    ):
        raise ValueError("Phase plan local-card status does not match the phase table.")
    required_plays = plan.opponent_plays_required_to_complete_current_trick
    if (
        isinstance(required_plays, bool)
        or not isinstance(required_plays, int)
        or required_plays != len(expected_completion_players)
    ):
        raise ValueError("Phase plan opponent completion count is invalid.")


def build_canonical_multi_step_phase_plan_v1(
    phase: TurnPhase,
    current_trick_length: int,
) -> CanonicalMultiStepPhasePlanV1 | None:
    """Classifies one normalized concrete phase; unresolved phases return None."""
    if not isinstance(phase, TurnPhase):
        raise TypeError("phase must be a normalized TurnPhase.")
    if isinstance(current_trick_length, bool) or not isinstance(
        current_trick_length, int
    ):
        raise ValueError("current_trick_length must be a strict integer.")
    if not is_concrete_player(phase.trick_leader) or not is_concrete_player(
        phase.next_player
    ):
        return None

    key = (phase.trick_leader, current_trick_length, phase.next_player)
    row = _PHASE_ROWS.get(key)
    if row is None:
        raise ValueError("Normalized concrete turn phase is not canonical.")
    phase_action, completion_players = row
    return CanonicalMultiStepPhasePlanV1(
        canonical_multi_step_phase_coverage_version=(
            CANONICAL_MULTI_STEP_PHASE_COVERAGE_VERSION
        ),
        trick_leader=phase.trick_leader,
        current_trick_length=current_trick_length,
        next_player=phase.next_player,
        phase_action=phase_action,
        local_card_already_played=(
            phase_action == COMPLETE_CURRENT_TRICK_THEN_CONTINUE
        ),
        opponent_plays_required_to_complete_current_trick=len(completion_players),
        completion_players=completion_players,
        _construction_token=_PLAN_CONSTRUCTION_TOKEN,
    )
