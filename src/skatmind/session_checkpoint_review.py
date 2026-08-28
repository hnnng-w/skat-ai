from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from skatmind.api.v1.contracts import RequestDocumentV1, WorkflowV1
from skatmind.errors import SkatMindInvariantError
from skatmind.input_loader import build_position_from_document
from skatmind.session_contracts import SessionStateV1
from skatmind.session_decision_checkpoint import SessionDecisionCheckpointV1
from skatmind.session_decision_observation import (
    SessionDecisionObservationV1,
    observe_session_decision_checkpoint_v1,
)
from skatmind.session_export_contracts import _canonicalize_diagnostics
from skatmind.session_validation import SessionValidationDiagnosticV1

SESSION_CHECKPOINT_REVIEW_EXPORT_VERSION = 1
SESSION_CHECKPOINT_REVIEW_EXPORT_POLICY = "frozen_request_plus_observed_card"
SESSION_CHECKPOINT_REVIEW_EXPORT_STATUSES = (
    "available",
    "unavailable",
    "diverged",
)


def _require_non_negative_integer(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer.")
    return value


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionCheckpointReviewExportV1:
    """One immutable post-game-review Request derived from a frozen Checkpoint."""

    session_checkpoint_review_export_version: int = (
        SESSION_CHECKPOINT_REVIEW_EXPORT_VERSION
    )
    status: str
    session_id: str
    checkpoint_revision: int
    observation_revision: int
    observation: SessionDecisionObservationV1
    request: RequestDocumentV1 | None
    diagnostics: tuple[SessionValidationDiagnosticV1, ...]

    def __post_init__(self) -> None:
        if (
            type(self.session_checkpoint_review_export_version) is not int
            or self.session_checkpoint_review_export_version
            != SESSION_CHECKPOINT_REVIEW_EXPORT_VERSION
        ):
            raise ValueError(
                "session_checkpoint_review_export_version must equal "
                f"{SESSION_CHECKPOINT_REVIEW_EXPORT_VERSION}."
            )
        if self.status not in SESSION_CHECKPOINT_REVIEW_EXPORT_STATUSES:
            raise ValueError(
                "status must be one of "
                f"{list(SESSION_CHECKPOINT_REVIEW_EXPORT_STATUSES)}."
            )
        if (
            not isinstance(self.session_id, str)
            or not self.session_id
            or self.session_id != self.session_id.strip()
        ):
            raise ValueError("session_id must be a non-empty, non-padded string.")
        _require_non_negative_integer(self.checkpoint_revision, "checkpoint_revision")
        _require_non_negative_integer(self.observation_revision, "observation_revision")
        if type(self.observation) is not SessionDecisionObservationV1:
            raise ValueError("observation must be a SessionDecisionObservationV1.")
        if (
            self.observation.session_id != self.session_id
            or self.observation.checkpoint_revision != self.checkpoint_revision
            or self.observation.state_revision != self.observation_revision
        ):
            raise ValueError("observation must match the review-export identity.")
        diagnostics = _canonicalize_diagnostics(self.diagnostics)

        if self.status == "available":
            if self.observation.status != "observed":
                raise ValueError("An available review export requires an observed decision.")
            if type(self.request) is not RequestDocumentV1:
                raise ValueError("An available review export requires one RequestDocumentV1.")
            if self.request.workflow is not WorkflowV1.POSITION_ANALYSIS:
                raise ValueError("A review export Request must target Position Analysis.")
            if (
                self.request.document.get("analysis_mode") != "post_game_review"
                or self.request.document.get("actual_card_played")
                != self.observation.actual_card
            ):
                raise ValueError(
                    "An available review Request must attach the observed Card in "
                    "post-game-review mode."
                )
            if diagnostics:
                raise ValueError("An available review export requires no diagnostics.")
        elif self.status == "diverged":
            if self.observation.status != "diverged" or self.request is not None:
                raise ValueError(
                    "A diverged review export requires a diverged observation and no Request."
                )
        elif (
            self.observation.status not in {"pending", "future", "ended_without_play"}
            or self.request is not None
        ):
            raise ValueError(
                "An unavailable review export requires a non-diverged unavailable "
                "observation and no Request."
            )
        object.__setattr__(self, "diagnostics", diagnostics)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_checkpoint_review_export_version": (
                self.session_checkpoint_review_export_version
            ),
            "status": self.status,
            "session_id": self.session_id,
            "checkpoint_revision": self.checkpoint_revision,
            "observation_revision": self.observation_revision,
            "observation": self.observation.to_dict(),
            "request": None if self.request is None else self.request.to_dict(),
            "diagnostics": [diagnostic.to_dict() for diagnostic in self.diagnostics],
        }


def export_session_checkpoint_review_request_v1(
    *,
    state: SessionStateV1,
    checkpoint: SessionDecisionCheckpointV1,
) -> SessionCheckpointReviewExportV1:
    """Attaches only the observed Card to one frozen Decision-time Request."""
    if type(state) is not SessionStateV1:
        raise ValueError("state must be a SessionStateV1.")
    if type(checkpoint) is not SessionDecisionCheckpointV1:
        raise ValueError("checkpoint must be a SessionDecisionCheckpointV1.")

    observation = observe_session_decision_checkpoint_v1(
        state=state,
        checkpoint=checkpoint,
    )
    common = {
        "session_id": state.session_id,
        "checkpoint_revision": checkpoint.source_revision,
        "observation_revision": observation.state_revision,
        "observation": observation,
        "diagnostics": (),
    }
    if observation.status == "diverged":
        return SessionCheckpointReviewExportV1(
            **common,
            status="diverged",
            request=None,
        )
    if observation.status != "observed":
        return SessionCheckpointReviewExportV1(
            **common,
            status="unavailable",
            request=None,
        )

    root = checkpoint.request.to_dict()["document"]
    root["analysis_mode"] = "post_game_review"
    root["actual_card_played"] = observation.actual_card
    try:
        validated_root = build_position_from_document(root)
        request = RequestDocumentV1(
            workflow=WorkflowV1.POSITION_ANALYSIS,
            document=validated_root,
        )
    except SkatMindInvariantError:
        raise
    except Exception as error:
        raise SkatMindInvariantError(
            "Frozen Checkpoint and observed Card could not produce a validated "
            "post-game-review Request.",
            path="/request/document",
        ) from error
    return SessionCheckpointReviewExportV1(
        **common,
        status="available",
        request=request,
    )
