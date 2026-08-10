from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from skat_ai.deck import get_full_deck
from skat_ai.errors import SkatAIInvariantError
from skat_ai.session_commands import (
    RecordSessionPlayCommandV1,
    SetSessionGameEndCommandV1,
)
from skat_ai.session_contracts import SessionStateV1
from skat_ai.session_decision_checkpoint import SessionDecisionCheckpointV1
from skat_ai.session_history import classify_session_decision_checkpoint_v1
from skat_ai.session_history_contracts import SessionCheckpointLineageV1

SESSION_DECISION_OBSERVATION_VERSION = 1
SESSION_DECISION_OBSERVATION_POLICY = "first_observed_local_play_after_checkpoint"
SESSION_DECISION_OBSERVATION_STATUSES = (
    "observed",
    "pending",
    "future",
    "diverged",
    "ended_without_play",
)
SESSION_DECISION_OBSERVATION_REASON_CODES = (
    "local_play_not_recorded",
    "state_before_checkpoint",
    "checkpoint_diverged",
    "game_ended_before_local_play",
)

_STATUS_REASON_CODES = {
    "observed": (),
    "pending": ("local_play_not_recorded",),
    "future": ("state_before_checkpoint",),
    "diverged": ("checkpoint_diverged",),
    "ended_without_play": ("game_ended_before_local_play",),
}


def _require_non_negative_integer(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer.")
    return value


def _require_positive_integer(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer.")
    return value


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionDecisionObservationV1:
    """One immutable actual-card observation derived from accepted Session history."""

    session_decision_observation_version: int = SESSION_DECISION_OBSERVATION_VERSION
    status: str
    session_id: str
    checkpoint_revision: int
    state_revision: int
    decision_index: int
    lineage: SessionCheckpointLineageV1
    observed_play_revision: int | None
    actual_card: str | None
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if (
            type(self.session_decision_observation_version) is not int
            or self.session_decision_observation_version
            != SESSION_DECISION_OBSERVATION_VERSION
        ):
            raise ValueError(
                "session_decision_observation_version must equal "
                f"{SESSION_DECISION_OBSERVATION_VERSION}."
            )
        if self.status not in SESSION_DECISION_OBSERVATION_STATUSES:
            raise ValueError(
                "status must be one of "
                f"{list(SESSION_DECISION_OBSERVATION_STATUSES)}."
            )
        if (
            not isinstance(self.session_id, str)
            or not self.session_id
            or self.session_id != self.session_id.strip()
        ):
            raise ValueError("session_id must be a non-empty, non-padded string.")
        _require_non_negative_integer(self.checkpoint_revision, "checkpoint_revision")
        _require_non_negative_integer(self.state_revision, "state_revision")
        _require_positive_integer(self.decision_index, "decision_index")
        if self.decision_index > 30:
            raise ValueError("decision_index must not exceed 30.")
        if type(self.lineage) is not SessionCheckpointLineageV1:
            raise ValueError("lineage must be a SessionCheckpointLineageV1.")
        if (
            self.lineage.session_id != self.session_id
            or self.lineage.checkpoint_revision != self.checkpoint_revision
            or self.lineage.state_revision != self.state_revision
        ):
            raise ValueError("lineage must identify the observed Session revisions.")
        if isinstance(self.reason_codes, (str, bytes)) or not isinstance(
            self.reason_codes, (list, tuple)
        ):
            raise ValueError("reason_codes must be an ordered array.")
        reason_codes = tuple(self.reason_codes)
        if reason_codes != _STATUS_REASON_CODES[self.status]:
            raise ValueError("reason_codes must match the observation status.")

        relationship = self.lineage.relationship
        if self.status == "observed":
            if relationship != "ancestor":
                raise ValueError("An observed decision requires ancestor lineage.")
            _require_positive_integer(
                self.observed_play_revision,
                "observed_play_revision",
            )
            if not self.checkpoint_revision < self.observed_play_revision <= self.state_revision:
                raise ValueError(
                    "observed_play_revision must follow the Checkpoint and not exceed "
                    "the State revision."
                )
            if not isinstance(self.actual_card, str) or self.actual_card not in get_full_deck():
                raise ValueError("actual_card must be one valid Skat card.")
        else:
            if self.observed_play_revision is not None or self.actual_card is not None:
                raise ValueError(
                    "A non-observed decision must not contain a Play revision or Card."
                )
            expected_relationships = {
                "pending": {"current", "ancestor"},
                "future": {"future"},
                "diverged": {"diverged"},
                "ended_without_play": {"ancestor"},
            }[self.status]
            if relationship not in expected_relationships:
                raise ValueError("Observation status does not match Checkpoint lineage.")

        if relationship == "current" and self.checkpoint_revision != self.state_revision:
            raise ValueError("Current lineage requires equal Checkpoint and State revisions.")
        if relationship == "ancestor" and self.checkpoint_revision >= self.state_revision:
            raise ValueError("Ancestor lineage requires an earlier Checkpoint revision.")
        if relationship == "future" and self.checkpoint_revision <= self.state_revision:
            raise ValueError("Future lineage requires a later Checkpoint revision.")
        if relationship == "diverged" and self.checkpoint_revision > self.state_revision:
            raise ValueError("Diverged lineage cannot follow the State revision.")
        object.__setattr__(self, "reason_codes", reason_codes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_decision_observation_version": (
                self.session_decision_observation_version
            ),
            "status": self.status,
            "session_id": self.session_id,
            "checkpoint_revision": self.checkpoint_revision,
            "state_revision": self.state_revision,
            "decision_index": self.decision_index,
            "lineage": self.lineage.to_dict(),
            "observed_play_revision": self.observed_play_revision,
            "actual_card": self.actual_card,
            "reason_codes": list(self.reason_codes),
        }


def _build_observation(
    *,
    state: SessionStateV1,
    checkpoint: SessionDecisionCheckpointV1,
    lineage: SessionCheckpointLineageV1,
    status: str,
    observed_play_revision: int | None = None,
    actual_card: str | None = None,
) -> SessionDecisionObservationV1:
    return SessionDecisionObservationV1(
        status=status,
        session_id=state.session_id,
        checkpoint_revision=checkpoint.source_revision,
        state_revision=state.revision,
        decision_index=checkpoint.decision_index,
        lineage=lineage,
        observed_play_revision=observed_play_revision,
        actual_card=actual_card,
        reason_codes=_STATUS_REASON_CODES[status],
    )


def observe_session_decision_checkpoint_v1(
    *,
    state: SessionStateV1,
    checkpoint: SessionDecisionCheckpointV1,
) -> SessionDecisionObservationV1:
    """Derives the first accepted local Play after one immutable Checkpoint."""
    if type(state) is not SessionStateV1:
        raise ValueError("state must be a SessionStateV1.")
    if type(checkpoint) is not SessionDecisionCheckpointV1:
        raise ValueError("checkpoint must be a SessionDecisionCheckpointV1.")

    lineage = classify_session_decision_checkpoint_v1(state, checkpoint)
    if lineage.relationship == "future":
        return _build_observation(
            state=state,
            checkpoint=checkpoint,
            lineage=lineage,
            status="future",
        )
    if lineage.relationship == "diverged":
        return _build_observation(
            state=state,
            checkpoint=checkpoint,
            lineage=lineage,
            status="diverged",
        )

    for record in state.command_log[checkpoint.source_revision :]:
        command = record.command
        if isinstance(command, SetSessionGameEndCommandV1):
            return _build_observation(
                state=state,
                checkpoint=checkpoint,
                lineage=lineage,
                status="ended_without_play",
            )
        if not isinstance(command, RecordSessionPlayCommandV1):
            continue
        if command.player_id != checkpoint.acting_player_id:
            raise SkatAIInvariantError(
                "Accepted Play order disagrees with the frozen local decision.",
                path=f"/command_log/{record.revision - 1}/command/player_id",
            )
        return _build_observation(
            state=state,
            checkpoint=checkpoint,
            lineage=lineage,
            status="observed",
            observed_play_revision=record.revision,
            actual_card=command.card,
        )

    return _build_observation(
        state=state,
        checkpoint=checkpoint,
        lineage=lineage,
        status="pending",
    )
