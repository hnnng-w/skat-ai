from __future__ import annotations

from typing import Any

from skatmind.errors import SkatMindInvariantError
from skatmind.session_contracts import (
    SESSION_CONTRACT_VERSION,
    SessionCommandRecordV1,
    SessionStateV1,
)
from skatmind.session_decision_checkpoint import (
    SessionDecisionCheckpointV1,
    _build_replayed_session_decision_checkpoint_v1,
    _options_from_request,
)
from skatmind.session_history_contracts import (
    SessionCheckpointLineageV1,
    SessionCommandCorrectionV1,
    SessionCorrectionResultV1,
    SessionUndoResultV1,
)
from skatmind.session_incremental_validation import (
    apply_session_command_to_projection_v1,
    build_session_validation_result_v1,
)
from skatmind.session_position_export import (
    _export_replayed_session_position_analysis_request_v1,
)
from skatmind.session_projection import (
    SessionProjectionV1,
    create_empty_session_projection_v1,
)
from skatmind.session_transitions import replay_session_state_v1
from skatmind.session_validation import SessionValidationDiagnosticV1


def _require_non_negative_integer(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer.")
    return value


def _raise_history_invariant(
    message: str,
    *,
    path: str,
    cause: Exception | None = None,
) -> None:
    error = SkatMindInvariantError(message, path=path)
    if cause is None:
        raise error
    raise error from cause


def _revision_conflict_diagnostic(
    *,
    expected_revision: int,
    source_revision: int,
) -> SessionValidationDiagnosticV1:
    return SessionValidationDiagnosticV1(
        code="revision_conflict",
        path="/expected_revision",
        message=(
            f"History edit expected revision {expected_revision}, but the Session is "
            f"at revision {source_revision}."
        ),
        severity="error",
        blocks_command=True,
        blocks_position_export=False,
        blocks_historical_export=False,
    )


def _history_revision_diagnostic(
    *,
    target_revision: int,
    source_revision: int,
) -> SessionValidationDiagnosticV1:
    return SessionValidationDiagnosticV1(
        code="history_revision_violation",
        path="/target_revision",
        message=(
            f"Undo target revision {target_revision} exceeds Session revision "
            f"{source_revision}."
        ),
        severity="error",
        blocks_command=True,
        blocks_position_export=False,
        blocks_historical_export=False,
    )


def _build_state_from_projection_v1(
    *,
    source_state: SessionStateV1,
    projection: SessionProjectionV1,
    command_log: tuple[SessionCommandRecordV1, ...],
) -> SessionStateV1:
    revision = len(command_log)
    validation = build_session_validation_result_v1(
        projection,
        revision=revision,
    )
    return SessionStateV1(
        session_contract_version=SESSION_CONTRACT_VERSION,
        session_id=source_state.session_id,
        initial_capture_mode=source_state.initial_capture_mode,
        capture_mode=projection.capture_mode,
        revision=revision,
        phase=projection.phase,
        players=source_state.players,
        local_player_id=source_state.local_player_id,
        command_log=command_log,
        validation=validation,
    )


def _reconstruct_session_prefix_v1(
    state: SessionStateV1,
    *,
    target_revision: int,
) -> tuple[SessionStateV1, SessionProjectionV1]:
    if type(state) is not SessionStateV1:
        raise ValueError("state must be a SessionStateV1.")
    _require_non_negative_integer(target_revision, "target_revision")
    if target_revision > state.revision:
        raise ValueError("target_revision must not exceed the source State revision.")

    try:
        projection = create_empty_session_projection_v1(
            session_id=state.session_id,
            players=state.players,
            capture_mode=state.initial_capture_mode,
            local_player_id=state.local_player_id,
        )
        command_log = state.command_log[:target_revision]
        for record_index, record in enumerate(command_log):
            expected_revision = record_index + 1
            try:
                validated_record = SessionCommandRecordV1(
                    revision=record.revision,
                    command=record.command,
                )
            except (AttributeError, TypeError, ValueError) as error:
                _raise_history_invariant(
                    "Session prefix contains a forged accepted Command record.",
                    path=f"/command_log/{record_index}",
                    cause=error,
                )
            if validated_record.revision != expected_revision:
                _raise_history_invariant(
                    "Session prefix accepted revisions are not contiguous.",
                    path=f"/command_log/{record_index}/revision",
                )
            application = apply_session_command_to_projection_v1(
                projection,
                validated_record.command,
            )
            if application.projection is None:
                diagnostic = application.diagnostics[0]
                _raise_history_invariant(
                    "Session prefix contains a semantically invalid accepted Command: "
                    f"{diagnostic.message}",
                    path=f"/command_log/{record_index}/command",
                )
            projection = application.projection
        prefix_state = _build_state_from_projection_v1(
            source_state=state,
            projection=projection,
            command_log=command_log,
        )
    except SkatMindInvariantError:
        raise
    except (AttributeError, TypeError, ValueError) as error:
        _raise_history_invariant(
            "Session State prefix cannot be reconstructed from its accepted Log.",
            path="",
            cause=error,
        )
    return prefix_state, projection


def build_session_state_from_accepted_prefix_v1(
    state: SessionStateV1,
    *,
    target_revision: int,
) -> SessionStateV1:
    """Reconstructs a caller-replay-validated accepted Session prefix."""
    prefix_state, _ = _reconstruct_session_prefix_v1(
        state,
        target_revision=target_revision,
    )
    return prefix_state


def _build_undo_result(**values: Any) -> SessionUndoResultV1:
    try:
        return SessionUndoResultV1(**values)
    except (AttributeError, TypeError, ValueError) as error:
        _raise_history_invariant(
            "Undo Result assembly violated the Session history contract.",
            path="",
            cause=error,
        )


def rewind_session_state_v1(
    state: SessionStateV1,
    *,
    expected_revision: int,
    target_revision: int,
) -> SessionUndoResultV1:
    """Rewinds one immutable Session to an accepted strict prefix."""
    if type(state) is not SessionStateV1:
        raise ValueError("state must be a SessionStateV1.")
    _require_non_negative_integer(expected_revision, "expected_revision")
    _require_non_negative_integer(target_revision, "target_revision")
    replay_session_state_v1(state)

    source_revision = state.revision
    common = {
        "session_id": state.session_id,
        "expected_revision": expected_revision,
        "source_revision": source_revision,
        "target_revision": target_revision,
    }
    if expected_revision != source_revision:
        return _build_undo_result(
            **common,
            status="revision_conflict",
            current_revision=source_revision,
            state=state,
            removed_records=(),
            diagnostics=(
                _revision_conflict_diagnostic(
                    expected_revision=expected_revision,
                    source_revision=source_revision,
                ),
            ),
        )
    if target_revision > source_revision:
        return _build_undo_result(
            **common,
            status="rejected",
            current_revision=source_revision,
            state=state,
            removed_records=(),
            diagnostics=(
                _history_revision_diagnostic(
                    target_revision=target_revision,
                    source_revision=source_revision,
                ),
            ),
        )
    if target_revision == source_revision:
        return _build_undo_result(
            **common,
            status="unchanged",
            current_revision=source_revision,
            state=state,
            removed_records=(),
            diagnostics=(),
        )

    prefix_state, _ = _reconstruct_session_prefix_v1(
        state,
        target_revision=target_revision,
    )
    return _build_undo_result(
        **common,
        status="applied",
        current_revision=target_revision,
        state=prefix_state,
        removed_records=state.command_log[target_revision:],
        diagnostics=(),
    )


def _build_correction_result(**values: Any) -> SessionCorrectionResultV1:
    try:
        return SessionCorrectionResultV1(**values)
    except (AttributeError, TypeError, ValueError) as error:
        _raise_history_invariant(
            "Correction Result assembly violated the Session history contract.",
            path="",
            cause=error,
        )


def _validated_original_suffix_record(
    record: SessionCommandRecordV1,
    *,
    expected_revision: int,
) -> SessionCommandRecordV1:
    try:
        validated_record = SessionCommandRecordV1(
            revision=record.revision,
            command=record.command,
        )
    except (AttributeError, TypeError, ValueError) as error:
        _raise_history_invariant(
            "Correction source suffix contains a forged accepted Command record.",
            path=f"/command_log/{expected_revision - 1}",
            cause=error,
        )
    if validated_record.revision != expected_revision:
        _raise_history_invariant(
            "Correction source suffix revisions are not contiguous.",
            path=f"/command_log/{expected_revision - 1}/revision",
        )
    return validated_record


def correct_session_command_v1(
    state: SessionStateV1,
    correction: SessionCommandCorrectionV1,
) -> SessionCorrectionResultV1:
    """Replaces one accepted Command and linearly replays the original suffix."""
    if type(state) is not SessionStateV1:
        raise ValueError("state must be a SessionStateV1.")
    if type(correction) is not SessionCommandCorrectionV1:
        raise ValueError("correction must be a SessionCommandCorrectionV1.")
    replay_session_state_v1(state)

    source_revision = state.revision
    common = {
        "session_id": state.session_id,
        "expected_revision": correction.expected_revision,
        "source_revision": source_revision,
        "target_revision": correction.target_revision,
        "replacement_command": correction.replacement_command,
    }
    if correction.expected_revision != source_revision:
        return _build_correction_result(
            **common,
            status="revision_conflict",
            current_revision=source_revision,
            state=state,
            original_record=None,
            replayed_suffix_records=(),
            discarded_suffix_records=(),
            failed_original_revision=None,
            diagnostics=(
                _revision_conflict_diagnostic(
                    expected_revision=correction.expected_revision,
                    source_revision=source_revision,
                ),
            ),
        )

    target_index = correction.target_revision - 1
    try:
        original_record = state.command_log[target_index]
    except IndexError as error:
        _raise_history_invariant(
            "Correction target has no accepted source record.",
            path=f"/command_log/{target_index}",
            cause=error,
        )
    if original_record.revision != correction.target_revision:
        _raise_history_invariant(
            "Correction target source record has an impossible revision.",
            path=f"/command_log/{target_index}/revision",
        )
    if original_record.command == correction.replacement_command:
        return _build_correction_result(
            **common,
            status="unchanged",
            current_revision=source_revision,
            state=state,
            original_record=original_record,
            replayed_suffix_records=(),
            discarded_suffix_records=(),
            failed_original_revision=None,
            diagnostics=(),
        )

    prefix_state, projection = _reconstruct_session_prefix_v1(
        state,
        target_revision=target_index,
    )
    replacement_application = apply_session_command_to_projection_v1(
        projection,
        correction.replacement_command,
    )
    if replacement_application.projection is None:
        return _build_correction_result(
            **common,
            status="rejected",
            current_revision=source_revision,
            state=state,
            original_record=original_record,
            replayed_suffix_records=(),
            discarded_suffix_records=(),
            failed_original_revision=correction.target_revision,
            diagnostics=replacement_application.diagnostics,
        )

    try:
        replacement_record = SessionCommandRecordV1(
            revision=correction.target_revision,
            command=correction.replacement_command,
        )
    except (TypeError, ValueError) as error:
        _raise_history_invariant(
            "Accepted replacement cannot form its canonical Command record.",
            path=f"/command_log/{target_index}",
            cause=error,
        )
    projection = replacement_application.projection
    accepted_records = [*prefix_state.command_log, replacement_record]
    replayed_records: list[SessionCommandRecordV1] = []
    discarded_records: tuple[SessionCommandRecordV1, ...] = ()
    failed_revision: int | None = None
    diagnostics: tuple[SessionValidationDiagnosticV1, ...] = ()

    for source_index in range(correction.target_revision, source_revision):
        source_record = state.command_log[source_index]
        validated_record = _validated_original_suffix_record(
            source_record,
            expected_revision=source_index + 1,
        )
        application = apply_session_command_to_projection_v1(
            projection,
            validated_record.command,
        )
        if application.projection is None:
            failed_revision = validated_record.revision
            discarded_records = state.command_log[source_index:]
            diagnostics = application.diagnostics
            break
        projection = application.projection
        accepted_records.append(source_record)
        replayed_records.append(source_record)

    try:
        corrected_state = _build_state_from_projection_v1(
            source_state=state,
            projection=projection,
            command_log=tuple(accepted_records),
        )
    except SkatMindInvariantError:
        raise
    except (AttributeError, TypeError, ValueError) as error:
        _raise_history_invariant(
            "Corrected Session State cannot be assembled canonically.",
            path="",
            cause=error,
        )

    status = "partial" if discarded_records else "applied"
    return _build_correction_result(
        **common,
        status=status,
        current_revision=corrected_state.revision,
        state=corrected_state,
        original_record=original_record,
        replayed_suffix_records=tuple(replayed_records),
        discarded_suffix_records=discarded_records,
        failed_original_revision=failed_revision,
        diagnostics=diagnostics,
    )


def _validate_checkpoint_contract(
    checkpoint: SessionDecisionCheckpointV1,
) -> SessionDecisionCheckpointV1:
    try:
        validated = SessionDecisionCheckpointV1(
            session_decision_checkpoint_version=(
                checkpoint.session_decision_checkpoint_version
            ),
            session_id=checkpoint.session_id,
            source_revision=checkpoint.source_revision,
            source_capture_mode=checkpoint.source_capture_mode,
            decision_index=checkpoint.decision_index,
            trick_number=checkpoint.trick_number,
            play_index=checkpoint.play_index,
            acting_player_id=checkpoint.acting_player_id,
            acting_seat=checkpoint.acting_seat,
            information_cutoff=checkpoint.information_cutoff,
            relative_player_map=checkpoint.relative_player_map,
            request=checkpoint.request,
        )
    except (AttributeError, TypeError, ValueError) as error:
        _raise_history_invariant(
            "Decision Checkpoint violates its immutable contract.",
            path="/checkpoint",
            cause=error,
        )
    if validated != checkpoint:
        _raise_history_invariant(
            "Decision Checkpoint is not canonical.",
            path="/checkpoint",
        )
    return validated


def _build_lineage_result(**values: Any) -> SessionCheckpointLineageV1:
    try:
        return SessionCheckpointLineageV1(**values)
    except (AttributeError, TypeError, ValueError) as error:
        _raise_history_invariant(
            "Checkpoint Lineage assembly violated the Session history contract.",
            path="",
            cause=error,
        )


def classify_session_decision_checkpoint_v1(
    state: SessionStateV1,
    checkpoint: SessionDecisionCheckpointV1,
) -> SessionCheckpointLineageV1:
    """Classifies one frozen Checkpoint against the State's accepted history."""
    if type(state) is not SessionStateV1:
        raise ValueError("state must be a SessionStateV1.")
    if type(checkpoint) is not SessionDecisionCheckpointV1:
        raise ValueError("checkpoint must be a SessionDecisionCheckpointV1.")
    validated_checkpoint = _validate_checkpoint_contract(checkpoint)
    if state.session_id != validated_checkpoint.session_id:
        raise ValueError("checkpoint Session ID must match the Session State.")

    source_projection = replay_session_state_v1(state)
    common = {
        "session_id": state.session_id,
        "checkpoint_revision": validated_checkpoint.source_revision,
        "state_revision": state.revision,
    }
    if state.revision < validated_checkpoint.source_revision:
        return _build_lineage_result(**common, relationship="future")

    if state.revision == validated_checkpoint.source_revision:
        prefix_state = state
        prefix_projection = source_projection
    else:
        prefix_state, prefix_projection = _reconstruct_session_prefix_v1(
            state,
            target_revision=validated_checkpoint.source_revision,
        )
    try:
        options = _options_from_request(validated_checkpoint.request)
        expected_export = _export_replayed_session_position_analysis_request_v1(
            state=prefix_state,
            projection=prefix_projection,
            options=options,
        )
    except SkatMindInvariantError:
        raise
    except Exception as error:
        _raise_history_invariant(
            "Checkpoint lineage cannot reconstruct the expected Position Request.",
            path="/checkpoint/request",
            cause=error,
        )
    if expected_export.status == "unavailable":
        return _build_lineage_result(**common, relationship="diverged")

    try:
        expected_checkpoint = _build_replayed_session_decision_checkpoint_v1(
            state=prefix_state,
            projection=prefix_projection,
            position_export=expected_export,
        )
    except SkatMindInvariantError:
        raise
    except Exception as error:
        _raise_history_invariant(
            "Checkpoint lineage cannot reconstruct the expected Checkpoint.",
            path="/checkpoint",
            cause=error,
        )
    if expected_checkpoint != validated_checkpoint:
        return _build_lineage_result(**common, relationship="diverged")
    relationship = (
        "current"
        if state.revision == validated_checkpoint.source_revision
        else "ancestor"
    )
    return _build_lineage_result(**common, relationship=relationship)
