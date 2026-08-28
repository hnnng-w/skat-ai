from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from skatmind.api.v1.contracts import PUBLIC_API_CONTRACT_VERSION
from skatmind.errors import SkatMindValidationError
from skatmind.session_checkpoint_review import (
    SESSION_CHECKPOINT_REVIEW_EXPORT_VERSION,
    SessionCheckpointReviewExportV1,
)
from skatmind.session_commands import SESSION_COMMAND_VERSION
from skatmind.session_contracts import SESSION_CONTRACT_VERSION, SessionStateV1
from skatmind.session_decision_checkpoint import (
    SESSION_DECISION_CHECKPOINT_VERSION,
    SessionDecisionCheckpointV1,
)
from skatmind.session_decision_observation import (
    SESSION_DECISION_OBSERVATION_VERSION,
    SessionDecisionObservationV1,
)
from skatmind.session_export_contracts import (
    SESSION_REQUEST_EXPORT_VERSION,
    SessionRequestExportV1,
)
from skatmind.session_history_contracts import (
    SESSION_CHECKPOINT_LINEAGE_VERSION,
    SESSION_HISTORY_EDIT_VERSION,
    SessionCheckpointLineageV1,
    SessionCorrectionResultV1,
    SessionUndoResultV1,
)
from skatmind.session_persistence_contracts import (
    SESSION_PERSISTENCE_VERSION,
    SessionPersistenceDocumentV1,
    SessionResumeResultV1,
)
from skatmind.session_projection import SESSION_PROJECTION_VERSION
from skatmind.session_transitions import SESSION_TRANSITION_ENGINE_VERSION
from skatmind.session_validation import SessionTransitionResultV1

if TYPE_CHECKING:
    from skatmind.api.v1.session.provenance import SessionFieldProvenanceBundleV1

PUBLIC_SESSION_API_VERSION = 1
PUBLIC_SESSION_API_NAMESPACE = "skatmind.api.v1.session"
PUBLIC_SESSION_API_COMPATIBILITY_POLICY = "additive_until_v1_0"

SESSION_API_OPERATIONS = (
    "create",
    "apply_command",
    "rewind",
    "correct",
    "export_position",
    "export_historical",
    "build_checkpoint",
    "classify_checkpoint",
    "build_persistence_document",
    "resume_persistence_document",
    "observe_checkpoint",
    "export_checkpoint_review",
)


def _validation_error(message: str, *, path: str) -> SkatMindValidationError:
    return SkatMindValidationError(message, path=path)


def _validate_version(value: object, expected: int, *, path: str) -> None:
    if type(value) is not int or value != expected:
        raise _validation_error(f"{path} must equal {expected}.", path=path)


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionApiVersionInfoV1:
    """Stable version information for the public in-memory Session API."""

    api_contract_version: int = PUBLIC_API_CONTRACT_VERSION
    public_session_api_version: int = PUBLIC_SESSION_API_VERSION
    namespace: str = PUBLIC_SESSION_API_NAMESPACE
    compatibility_policy: str = PUBLIC_SESSION_API_COMPATIBILITY_POLICY
    operations: tuple[str, ...] = SESSION_API_OPERATIONS
    session_contract_version: int = SESSION_CONTRACT_VERSION
    session_command_version: int = SESSION_COMMAND_VERSION
    transition_engine_version: int = SESSION_TRANSITION_ENGINE_VERSION
    projection_version: int = SESSION_PROJECTION_VERSION
    request_export_version: int = SESSION_REQUEST_EXPORT_VERSION
    decision_checkpoint_version: int = SESSION_DECISION_CHECKPOINT_VERSION
    history_edit_version: int = SESSION_HISTORY_EDIT_VERSION
    checkpoint_lineage_version: int = SESSION_CHECKPOINT_LINEAGE_VERSION
    persistence_version: int = SESSION_PERSISTENCE_VERSION
    decision_observation_version: int = SESSION_DECISION_OBSERVATION_VERSION
    checkpoint_review_export_version: int = SESSION_CHECKPOINT_REVIEW_EXPORT_VERSION

    def __post_init__(self) -> None:
        _validate_version(
            self.api_contract_version,
            PUBLIC_API_CONTRACT_VERSION,
            path="api_contract_version",
        )
        _validate_version(
            self.public_session_api_version,
            PUBLIC_SESSION_API_VERSION,
            path="public_session_api_version",
        )
        if self.namespace != PUBLIC_SESSION_API_NAMESPACE:
            raise _validation_error(
                f"namespace must equal {PUBLIC_SESSION_API_NAMESPACE!r}.",
                path="namespace",
            )
        if self.compatibility_policy != PUBLIC_SESSION_API_COMPATIBILITY_POLICY:
            raise _validation_error(
                "compatibility_policy must equal the public Session API policy.",
                path="compatibility_policy",
            )
        if self.operations != SESSION_API_OPERATIONS:
            raise _validation_error(
                "operations must equal the canonical Session API operation order.",
                path="operations",
            )
        for path, value, expected in (
            ("session_contract_version", self.session_contract_version, SESSION_CONTRACT_VERSION),
            ("session_command_version", self.session_command_version, SESSION_COMMAND_VERSION),
            (
                "transition_engine_version",
                self.transition_engine_version,
                SESSION_TRANSITION_ENGINE_VERSION,
            ),
            ("projection_version", self.projection_version, SESSION_PROJECTION_VERSION),
            (
                "request_export_version",
                self.request_export_version,
                SESSION_REQUEST_EXPORT_VERSION,
            ),
            (
                "decision_checkpoint_version",
                self.decision_checkpoint_version,
                SESSION_DECISION_CHECKPOINT_VERSION,
            ),
            ("history_edit_version", self.history_edit_version, SESSION_HISTORY_EDIT_VERSION),
            (
                "checkpoint_lineage_version",
                self.checkpoint_lineage_version,
                SESSION_CHECKPOINT_LINEAGE_VERSION,
            ),
            ("persistence_version", self.persistence_version, SESSION_PERSISTENCE_VERSION),
            (
                "decision_observation_version",
                self.decision_observation_version,
                SESSION_DECISION_OBSERVATION_VERSION,
            ),
            (
                "checkpoint_review_export_version",
                self.checkpoint_review_export_version,
                SESSION_CHECKPOINT_REVIEW_EXPORT_VERSION,
            ),
        ):
            _validate_version(value, expected, path=path)

    def to_dict(self) -> dict[str, Any]:
        return {
            "api_contract_version": self.api_contract_version,
            "public_session_api_version": self.public_session_api_version,
            "namespace": self.namespace,
            "compatibility_policy": self.compatibility_policy,
            "operations": list(self.operations),
            "session_contract_version": self.session_contract_version,
            "session_command_version": self.session_command_version,
            "transition_engine_version": self.transition_engine_version,
            "projection_version": self.projection_version,
            "request_export_version": self.request_export_version,
            "decision_checkpoint_version": self.decision_checkpoint_version,
            "history_edit_version": self.history_edit_version,
            "checkpoint_lineage_version": self.checkpoint_lineage_version,
            "persistence_version": self.persistence_version,
            "decision_observation_version": self.decision_observation_version,
            "checkpoint_review_export_version": self.checkpoint_review_export_version,
        }


def get_session_api_version_info_v1() -> SessionApiVersionInfoV1:
    """Returns deterministic public Session API compatibility information."""
    return SessionApiVersionInfoV1()


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionApiOptionsV1:
    """Non-transport controls for one public Session API operation."""

    validate_output: bool = True
    include_provenance: bool = False

    def __post_init__(self) -> None:
        if type(self.validate_output) is not bool:
            raise _validation_error(
                "validate_output must be a boolean.",
                path="validate_output",
            )
        if type(self.include_provenance) is not bool:
            raise _validation_error(
                "include_provenance must be a boolean.",
                path="include_provenance",
            )

    def to_dict(self) -> dict[str, bool]:
        return {
            "validate_output": self.validate_output,
            "include_provenance": self.include_provenance,
        }


_OPERATION_VALUE_TYPES = {
    "create": SessionStateV1,
    "apply_command": SessionTransitionResultV1,
    "rewind": SessionUndoResultV1,
    "correct": SessionCorrectionResultV1,
    "export_position": SessionRequestExportV1,
    "export_historical": SessionRequestExportV1,
    "build_checkpoint": SessionDecisionCheckpointV1,
    "classify_checkpoint": SessionCheckpointLineageV1,
    "build_persistence_document": SessionPersistenceDocumentV1,
    "resume_persistence_document": SessionResumeResultV1,
    "observe_checkpoint": SessionDecisionObservationV1,
    "export_checkpoint_review": SessionCheckpointReviewExportV1,
}


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionApiResultV1:
    """One immutable result from the stable in-memory Session API."""

    api_contract_version: int = PUBLIC_API_CONTRACT_VERSION
    public_session_api_version: int = PUBLIC_SESSION_API_VERSION
    operation: str
    value: object
    field_provenance: SessionFieldProvenanceBundleV1 | None = None

    def __post_init__(self) -> None:
        _validate_version(
            self.api_contract_version,
            PUBLIC_API_CONTRACT_VERSION,
            path="api_contract_version",
        )
        _validate_version(
            self.public_session_api_version,
            PUBLIC_SESSION_API_VERSION,
            path="public_session_api_version",
        )
        if self.operation not in SESSION_API_OPERATIONS:
            raise _validation_error(
                "operation must be one canonical Session API operation.",
                path="operation",
            )
        expected_type = _OPERATION_VALUE_TYPES[self.operation]
        if type(self.value) is not expected_type:
            raise _validation_error(
                f"value must be a {expected_type.__name__} for {self.operation!r}.",
                path="value",
            )
        expected_target = {
            "export_position": "position_analysis",
            "export_historical": "historical_game",
        }.get(self.operation)
        if expected_target is not None and self.value.target != expected_target:
            raise _validation_error(
                f"value target must equal {expected_target!r} for {self.operation!r}.",
                path="value.target",
            )
        if self.field_provenance is not None:
            from skatmind.api.v1.session.provenance import (
                SessionFieldProvenanceBundleV1,
            )

            if type(self.field_provenance) is not SessionFieldProvenanceBundleV1:
                raise _validation_error(
                    "field_provenance must be a SessionFieldProvenanceBundleV1 or null.",
                    path="field_provenance",
                )
            if self.field_provenance.operation != self.operation:
                raise _validation_error(
                    "field_provenance operation must match the Session API operation.",
                    path="field_provenance.operation",
                )
            from skatmind.api.v1.session.provenance import (
                validate_session_provenance_for_value_v1,
            )

            validate_session_provenance_for_value_v1(
                self.field_provenance,
                self.value,
            )

    def to_dict(self) -> dict[str, Any]:
        value = self.value.to_dict()
        result = {
            "api_contract_version": self.api_contract_version,
            "public_session_api_version": self.public_session_api_version,
            "operation": self.operation,
            "value": value,
        }
        if self.field_provenance is not None:
            result["field_provenance"] = self.field_provenance.to_dict()
        return result
