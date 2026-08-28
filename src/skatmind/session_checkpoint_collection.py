from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from skatmind.session_contracts import SessionStateV1
from skatmind.session_decision_checkpoint import (
    SessionDecisionCheckpointV1,
    _build_replayed_session_decision_checkpoint_v1,
)
from skatmind.session_export_contracts import _canonicalize_diagnostics
from skatmind.session_persistence_contracts import _canonicalize_checkpoints
from skatmind.session_position_export import (
    SessionPositionExportOptionsV1,
    _export_replayed_session_position_analysis_request_v1,
)
from skatmind.session_transitions import replay_session_state_v1
from skatmind.session_validation import SessionValidationDiagnosticV1

SESSION_CHECKPOINT_COLLECTION_VERSION = 1
SESSION_CHECKPOINT_COLLECTION_POLICY = "exact_position_ready_revision_and_request"
SESSION_CHECKPOINT_COLLECTION_STATUSES = (
    "collected",
    "existing",
    "unavailable",
)


def _require_non_negative_integer(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer.")
    return value


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionCheckpointCollectionResultV1:
    """One immutable exact Checkpoint collection outcome."""

    session_checkpoint_collection_version: int = SESSION_CHECKPOINT_COLLECTION_VERSION
    status: str
    session_id: str
    source_revision: int
    checkpoint: SessionDecisionCheckpointV1 | None
    decision_checkpoints: tuple[SessionDecisionCheckpointV1, ...]
    diagnostics: tuple[SessionValidationDiagnosticV1, ...]

    def __post_init__(self) -> None:
        if (
            type(self.session_checkpoint_collection_version) is not int
            or self.session_checkpoint_collection_version
            != SESSION_CHECKPOINT_COLLECTION_VERSION
        ):
            raise ValueError(
                "session_checkpoint_collection_version must equal "
                f"{SESSION_CHECKPOINT_COLLECTION_VERSION}."
            )
        if self.status not in SESSION_CHECKPOINT_COLLECTION_STATUSES:
            raise ValueError(
                "status must be one of "
                f"{list(SESSION_CHECKPOINT_COLLECTION_STATUSES)}."
            )
        if (
            not isinstance(self.session_id, str)
            or not self.session_id
            or self.session_id != self.session_id.strip()
        ):
            raise ValueError("session_id must be a non-empty, non-padded string.")
        _require_non_negative_integer(self.source_revision, "source_revision")
        checkpoints = _canonicalize_checkpoints(
            self.decision_checkpoints,
            session_id=self.session_id,
        )
        diagnostics = _canonicalize_diagnostics(self.diagnostics)

        if self.status == "unavailable":
            if self.checkpoint is not None:
                raise ValueError("An unavailable collection must not contain a Checkpoint.")
            if not diagnostics or any(
                not diagnostic.blocks_position_export for diagnostic in diagnostics
            ):
                raise ValueError(
                    "An unavailable collection requires Position-export blockers."
                )
        else:
            if type(self.checkpoint) is not SessionDecisionCheckpointV1:
                raise ValueError(
                    "A collected or existing result requires one Decision Checkpoint."
                )
            if (
                self.checkpoint.session_id != self.session_id
                or self.checkpoint.source_revision != self.source_revision
            ):
                raise ValueError("checkpoint must match the collection source identity.")
            if checkpoints.count(self.checkpoint) != 1:
                raise ValueError(
                    "The returned Checkpoint must occur exactly once in decision_checkpoints."
                )
            if diagnostics:
                raise ValueError(
                    "A collected or existing result requires no diagnostics."
                )
        object.__setattr__(self, "decision_checkpoints", checkpoints)
        object.__setattr__(self, "diagnostics", diagnostics)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_checkpoint_collection_version": (
                self.session_checkpoint_collection_version
            ),
            "status": self.status,
            "session_id": self.session_id,
            "source_revision": self.source_revision,
            "checkpoint": (
                None if self.checkpoint is None else self.checkpoint.to_dict()
            ),
            "decision_checkpoints": [
                checkpoint.to_dict() for checkpoint in self.decision_checkpoints
            ],
            "diagnostics": [diagnostic.to_dict() for diagnostic in self.diagnostics],
        }


def collect_session_decision_checkpoint_v1(
    *,
    state: SessionStateV1,
    export_options: SessionPositionExportOptionsV1,
    decision_checkpoints: tuple[SessionDecisionCheckpointV1, ...],
) -> SessionCheckpointCollectionResultV1:
    """Collects or reuses one exact current Position-ready Checkpoint."""
    if type(state) is not SessionStateV1:
        raise ValueError("state must be a SessionStateV1.")
    if type(export_options) is not SessionPositionExportOptionsV1:
        raise ValueError("export_options must be a SessionPositionExportOptionsV1.")
    if type(decision_checkpoints) is not tuple:
        raise ValueError("decision_checkpoints must be a tuple.")
    checkpoints = _canonicalize_checkpoints(
        decision_checkpoints,
        session_id=state.session_id,
    )

    projection = replay_session_state_v1(state)
    position_export = _export_replayed_session_position_analysis_request_v1(
        state=state,
        projection=projection,
        options=export_options,
    )
    if position_export.status == "unavailable":
        return SessionCheckpointCollectionResultV1(
            status="unavailable",
            session_id=state.session_id,
            source_revision=state.revision,
            checkpoint=None,
            decision_checkpoints=checkpoints,
            diagnostics=position_export.diagnostics,
        )

    checkpoint = _build_replayed_session_decision_checkpoint_v1(
        state=state,
        projection=projection,
        position_export=position_export,
    )
    existing_checkpoint = next(
        (candidate for candidate in checkpoints if candidate == checkpoint),
        None,
    )
    if existing_checkpoint is not None:
        return SessionCheckpointCollectionResultV1(
            status="existing",
            session_id=state.session_id,
            source_revision=state.revision,
            checkpoint=existing_checkpoint,
            decision_checkpoints=checkpoints,
            diagnostics=(),
        )
    return SessionCheckpointCollectionResultV1(
        status="collected",
        session_id=state.session_id,
        source_revision=state.revision,
        checkpoint=checkpoint,
        decision_checkpoints=(*checkpoints, checkpoint),
        diagnostics=(),
    )
