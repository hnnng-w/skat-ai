from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from skat_ai.api.v1.session.contracts import (
    SessionApiOptionsV1,
    SessionApiResultV1,
)
from skat_ai.api.v1.session.schema_validation import (
    validate_session_command_document,
    validate_session_persistence_document,
    validate_session_result_document,
)
from skat_ai.errors import (
    SkatAIError,
    SkatAIResourceError,
    SkatAISerializationError,
    SkatAIValidationError,
)
from skat_ai.session_checkpoint_review import (
    export_session_checkpoint_review_request_v1,
)
from skat_ai.session_commands import SessionCommandV1, is_session_command_v1
from skat_ai.session_contracts import SessionPlayerV1, SessionStateV1
from skat_ai.session_decision_checkpoint import (
    SessionDecisionCheckpointV1,
    build_session_decision_checkpoint_v1,
)
from skat_ai.session_decision_observation import (
    observe_session_decision_checkpoint_v1,
)
from skat_ai.session_export_contracts import SessionRequestExportV1
from skat_ai.session_historical_export import (
    export_session_historical_game_request_v1,
)
from skat_ai.session_history import (
    classify_session_decision_checkpoint_v1,
    correct_session_command_v1,
    rewind_session_state_v1,
)
from skat_ai.session_history_contracts import SessionCommandCorrectionV1
from skat_ai.session_persistence_codec import (
    _build_command,
    build_session_persistence_document_v1,
    resume_session_document_v1,
)
from skat_ai.session_position_export import (
    SessionPositionExportOptionsV1,
    export_session_position_analysis_request_v1,
)
from skat_ai.session_transitions import (
    apply_session_command_v1,
    create_session_state_v1,
)

_DEFAULT_OPTIONS = SessionApiOptionsV1()


def _at_public_boundary[T](operation: Callable[[], T]) -> T:
    try:
        return operation()
    except SkatAIError:
        raise
    except OSError as error:
        raise SkatAIResourceError(str(error)) from error
    except (TypeError, ValueError) as error:
        raise SkatAIValidationError(str(error)) from error


def _require_options(options: object) -> SessionApiOptionsV1:
    if type(options) is not SessionApiOptionsV1:
        raise SkatAIValidationError(
            "options must be a SessionApiOptionsV1.",
            path="options",
        )
    return options


def _result(
    *,
    operation: str,
    value: object,
    options: SessionApiOptionsV1,
    source_state: SessionStateV1 | None,
    retained_inputs: Mapping[str, object],
) -> SessionApiResultV1:
    provenance = None
    if options.include_provenance:
        from skat_ai.session_provenance import build_session_field_provenance_bundle_v1

        provenance = build_session_field_provenance_bundle_v1(
            operation=operation,
            value=value,
            source_state=source_state,
            retained_inputs=retained_inputs,
        )
    result = SessionApiResultV1(
        operation=operation,
        value=value,
        field_provenance=provenance,
    )
    if options.validate_output:
        validate_session_result_document(result.to_dict())
    return result


def _parse_session_command(document: Mapping[str, object]) -> SessionCommandV1:
    if not isinstance(document, Mapping):
        raise SkatAIValidationError(
            "Session Command document must be an object.",
            path="",
        )
    mutable_document = dict(document)
    validate_session_command_document(mutable_document)
    return _build_command(mutable_document, path="")


def parse_session_command(document: Mapping[str, object]) -> SessionCommandV1:
    """Validates and reconstructs one immutable Session Command."""
    return _at_public_boundary(lambda: _parse_session_command(document))


def create_session(
    *,
    session_id: str,
    players: tuple[SessionPlayerV1, ...],
    capture_mode: str,
    local_player_id: str | None = None,
    options: SessionApiOptionsV1 = _DEFAULT_OPTIONS,
) -> SessionApiResultV1:
    def operation() -> SessionApiResultV1:
        validated_options = _require_options(options)
        value = create_session_state_v1(
            session_id=session_id,
            players=players,
            capture_mode=capture_mode,
            local_player_id=local_player_id,
        )
        return _result(
            operation="create",
            value=value,
            options=validated_options,
            source_state=None,
            retained_inputs={
                "session_id": session_id,
                "players": players,
                "capture_mode": capture_mode,
                "local_player_id": local_player_id,
            },
        )

    return _at_public_boundary(operation)


def apply_session_command(
    state: SessionStateV1,
    command: SessionCommandV1 | Mapping[str, object],
    *,
    options: SessionApiOptionsV1 = _DEFAULT_OPTIONS,
) -> SessionApiResultV1:
    def operation() -> SessionApiResultV1:
        validated_options = _require_options(options)
        typed_command = (
            command
            if is_session_command_v1(command)
            else _parse_session_command(command)
        )
        value = apply_session_command_v1(state, typed_command)
        return _result(
            operation="apply_command",
            value=value,
            options=validated_options,
            source_state=state,
            retained_inputs={"state": state, "command": typed_command},
        )

    return _at_public_boundary(operation)


def rewind_session(
    state: SessionStateV1,
    *,
    expected_revision: int,
    target_revision: int,
    options: SessionApiOptionsV1 = _DEFAULT_OPTIONS,
) -> SessionApiResultV1:
    def operation() -> SessionApiResultV1:
        validated_options = _require_options(options)
        value = rewind_session_state_v1(
            state,
            expected_revision=expected_revision,
            target_revision=target_revision,
        )
        return _result(
            operation="rewind",
            value=value,
            options=validated_options,
            source_state=state,
            retained_inputs={
                "state": state,
                "expected_revision": expected_revision,
                "target_revision": target_revision,
            },
        )

    return _at_public_boundary(operation)


def correct_session_command(
    state: SessionStateV1,
    correction: SessionCommandCorrectionV1,
    *,
    options: SessionApiOptionsV1 = _DEFAULT_OPTIONS,
) -> SessionApiResultV1:
    def operation() -> SessionApiResultV1:
        validated_options = _require_options(options)
        value = correct_session_command_v1(state, correction)
        return _result(
            operation="correct",
            value=value,
            options=validated_options,
            source_state=state,
            retained_inputs={"state": state, "correction": correction},
        )

    return _at_public_boundary(operation)


def export_session_position_request(
    state: SessionStateV1,
    export_options: SessionPositionExportOptionsV1,
    *,
    options: SessionApiOptionsV1 = _DEFAULT_OPTIONS,
) -> SessionApiResultV1:
    def operation() -> SessionApiResultV1:
        validated_options = _require_options(options)
        value = export_session_position_analysis_request_v1(state, export_options)
        return _result(
            operation="export_position",
            value=value,
            options=validated_options,
            source_state=state,
            retained_inputs={"state": state, "export_options": export_options},
        )

    return _at_public_boundary(operation)


def export_session_historical_request(
    state: SessionStateV1,
    *,
    options: SessionApiOptionsV1 = _DEFAULT_OPTIONS,
) -> SessionApiResultV1:
    def operation() -> SessionApiResultV1:
        validated_options = _require_options(options)
        value = export_session_historical_game_request_v1(state)
        return _result(
            operation="export_historical",
            value=value,
            options=validated_options,
            source_state=state,
            retained_inputs={"state": state},
        )

    return _at_public_boundary(operation)


def build_session_decision_checkpoint(
    *,
    state: SessionStateV1,
    position_export: SessionRequestExportV1,
    options: SessionApiOptionsV1 = _DEFAULT_OPTIONS,
) -> SessionApiResultV1:
    def operation() -> SessionApiResultV1:
        validated_options = _require_options(options)
        value = build_session_decision_checkpoint_v1(
            state=state,
            position_export=position_export,
        )
        return _result(
            operation="build_checkpoint",
            value=value,
            options=validated_options,
            source_state=state,
            retained_inputs={
                "state": state,
                "position_export": position_export,
            },
        )

    return _at_public_boundary(operation)


def classify_session_decision_checkpoint(
    *,
    state: SessionStateV1,
    checkpoint: SessionDecisionCheckpointV1,
    options: SessionApiOptionsV1 = _DEFAULT_OPTIONS,
) -> SessionApiResultV1:
    def operation() -> SessionApiResultV1:
        validated_options = _require_options(options)
        value = classify_session_decision_checkpoint_v1(state, checkpoint)
        return _result(
            operation="classify_checkpoint",
            value=value,
            options=validated_options,
            source_state=state,
            retained_inputs={"state": state, "checkpoint": checkpoint},
        )

    return _at_public_boundary(operation)


def build_session_persistence_document(
    state: SessionStateV1,
    *,
    decision_checkpoints: tuple[SessionDecisionCheckpointV1, ...] = (),
    options: SessionApiOptionsV1 = _DEFAULT_OPTIONS,
) -> SessionApiResultV1:
    def operation() -> SessionApiResultV1:
        validated_options = _require_options(options)
        value = build_session_persistence_document_v1(
            state,
            decision_checkpoints=decision_checkpoints,
        )
        return _result(
            operation="build_persistence_document",
            value=value,
            options=validated_options,
            source_state=state,
            retained_inputs={
                "state": state,
                "decision_checkpoints": decision_checkpoints,
            },
        )

    return _at_public_boundary(operation)


def resume_session_document(
    document: Mapping[str, object],
    *,
    options: SessionApiOptionsV1 = _DEFAULT_OPTIONS,
) -> SessionApiResultV1:
    def operation() -> SessionApiResultV1:
        validated_options = _require_options(options)
        if not isinstance(document, Mapping):
            raise SkatAIValidationError(
                "Session persistence document must be an object.",
                path="",
            )
        mutable_document = dict(document)
        validate_session_persistence_document(mutable_document)
        value = resume_session_document_v1(mutable_document)
        return _result(
            operation="resume_persistence_document",
            value=value,
            options=validated_options,
            source_state=value.document.state,
            retained_inputs={"document": mutable_document},
        )

    return _at_public_boundary(operation)


def observe_session_decision_checkpoint(
    *,
    state: SessionStateV1,
    checkpoint: SessionDecisionCheckpointV1,
    options: SessionApiOptionsV1 = _DEFAULT_OPTIONS,
) -> SessionApiResultV1:
    """Observes one frozen decision from accepted Session history."""

    def operation() -> SessionApiResultV1:
        validated_options = _require_options(options)
        value = observe_session_decision_checkpoint_v1(
            state=state,
            checkpoint=checkpoint,
        )
        return _result(
            operation="observe_checkpoint",
            value=value,
            options=validated_options,
            source_state=state,
            retained_inputs={"state": state, "checkpoint": checkpoint},
        )

    return _at_public_boundary(operation)


def export_session_checkpoint_review_request(
    *,
    state: SessionStateV1,
    checkpoint: SessionDecisionCheckpointV1,
    options: SessionApiOptionsV1 = _DEFAULT_OPTIONS,
) -> SessionApiResultV1:
    """Exports one review Request from a frozen decision and observed Card."""

    def operation() -> SessionApiResultV1:
        validated_options = _require_options(options)
        value = export_session_checkpoint_review_request_v1(
            state=state,
            checkpoint=checkpoint,
        )
        return _result(
            operation="export_checkpoint_review",
            value=value,
            options=validated_options,
            source_state=state,
            retained_inputs={"state": state, "checkpoint": checkpoint},
        )

    return _at_public_boundary(operation)


def serialize_session_result(result: SessionApiResultV1) -> dict[str, object]:
    """Returns one fresh mutable Session Result representation."""
    if type(result) is not SessionApiResultV1:
        raise SkatAISerializationError(
            "result must be a SessionApiResultV1.",
            path="result",
        )
    serialized: dict[str, Any] = result.to_dict()
    return serialized
