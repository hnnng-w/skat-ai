from __future__ import annotations

from skatmind.errors import SkatMindInvariantError
from skatmind.session_commands import SessionCommandV1, is_session_command_v1
from skatmind.session_contracts import (
    SESSION_CONTRACT_VERSION,
    SessionCommandRecordV1,
    SessionPlayerV1,
    SessionStateV1,
)
from skatmind.session_incremental_validation import (
    apply_session_command_to_projection_v1,
    build_session_validation_result_v1,
)
from skatmind.session_projection import (
    SessionProjectionV1,
    create_empty_session_projection_v1,
)
from skatmind.session_validation import (
    SessionTransitionResultV1,
    SessionValidationDiagnosticV1,
)

SESSION_TRANSITION_ENGINE_VERSION = 1
SESSION_REPLAY_POLICY = "full_accepted_log_before_apply"


def create_session_state_v1(
    *,
    session_id: str,
    players: tuple[SessionPlayerV1, ...] | list[SessionPlayerV1],
    capture_mode: str,
    local_player_id: str | None = None,
) -> SessionStateV1:
    """Creates one canonical revision-zero Session without generated facts."""
    projection = create_empty_session_projection_v1(
        session_id=session_id,
        players=players,
        capture_mode=capture_mode,
        local_player_id=local_player_id,
    )
    validation = build_session_validation_result_v1(projection, revision=0)
    return SessionStateV1(
        session_contract_version=SESSION_CONTRACT_VERSION,
        session_id=projection.session_id,
        initial_capture_mode=projection.initial_capture_mode,
        capture_mode=projection.capture_mode,
        revision=0,
        phase=projection.phase,
        players=projection.players,
        local_player_id=projection.local_player_id,
        command_log=(),
        validation=validation,
    )


def _raise_replay_invariant(
    message: str,
    *,
    path: str,
    cause: Exception | None = None,
) -> None:
    error = SkatMindInvariantError(message, path=path)
    if cause is None:
        raise error
    raise error from cause


def replay_session_state_v1(state: SessionStateV1) -> SessionProjectionV1:
    """Replays the full accepted Log and verifies every stored derived State value."""
    if type(state) is not SessionStateV1:
        raise ValueError("state must be a SessionStateV1.")
    try:
        projection = create_empty_session_projection_v1(
            session_id=state.session_id,
            players=state.players,
            capture_mode=state.initial_capture_mode,
            local_player_id=state.local_player_id,
        )
        if state.session_contract_version != SESSION_CONTRACT_VERSION:
            _raise_replay_invariant(
                "Session State has a forged contract version.",
                path="/session_contract_version",
            )
        if state.revision != len(state.command_log):
            _raise_replay_invariant(
                "Session State revision does not equal its accepted Log length.",
                path="/revision",
            )

        for record_index, record in enumerate(state.command_log):
            expected_revision = record_index + 1
            try:
                validated_record = SessionCommandRecordV1(
                    revision=record.revision,
                    command=record.command,
                )
            except (AttributeError, TypeError, ValueError) as error:
                _raise_replay_invariant(
                    "Session State contains a forged accepted Command record.",
                    path=f"/command_log/{record_index}",
                    cause=error,
                )
            if validated_record.revision != expected_revision:
                _raise_replay_invariant(
                    "Session State accepted revisions are not contiguous.",
                    path=f"/command_log/{record_index}/revision",
                )
            application = apply_session_command_to_projection_v1(
                projection,
                validated_record.command,
            )
            if application.projection is None:
                diagnostic = application.diagnostics[0]
                _raise_replay_invariant(
                    "Session State contains a semantically invalid accepted Command: "
                    f"{diagnostic.message}",
                    path=f"/command_log/{record_index}/command",
                )
            projection = application.projection

        validation = build_session_validation_result_v1(
            projection,
            revision=len(state.command_log),
        )
        expected_state = SessionStateV1(
            session_contract_version=SESSION_CONTRACT_VERSION,
            session_id=state.session_id,
            initial_capture_mode=state.initial_capture_mode,
            capture_mode=projection.capture_mode,
            revision=len(state.command_log),
            phase=projection.phase,
            players=projection.players,
            local_player_id=state.local_player_id,
            command_log=state.command_log,
            validation=validation,
        )
    except SkatMindInvariantError:
        raise
    except (AttributeError, TypeError, ValueError) as error:
        _raise_replay_invariant(
            "Session State cannot be reconstructed from its accepted Log.",
            path="",
            cause=error,
        )

    if state.revision != expected_state.revision:
        _raise_replay_invariant(
            "Session State has a forged revision.",
            path="/revision",
        )
    if state.capture_mode != expected_state.capture_mode:
        _raise_replay_invariant(
            "Session State Capture Mode conflicts with its accepted Log.",
            path="/capture_mode",
        )
    if state.phase != expected_state.phase:
        _raise_replay_invariant(
            "Session State phase conflicts with its accepted Log.",
            path="/phase",
        )
    if state.validation != expected_state.validation:
        _raise_replay_invariant(
            "Session State Validation conflicts with its accepted Log.",
            path="/validation",
        )
    if state != expected_state:
        _raise_replay_invariant(
            "Session State identity or accepted Log is not canonical.",
            path="",
        )
    return projection


def _revision_conflict_diagnostic(
    *,
    expected_revision: int,
    current_revision: int,
) -> SessionValidationDiagnosticV1:
    return SessionValidationDiagnosticV1(
        code="revision_conflict",
        path="/command/expected_revision",
        message=(
            f"Command expected revision {expected_revision}, but the Session is at "
            f"revision {current_revision}."
        ),
        severity="error",
        blocks_command=True,
        blocks_position_export=False,
        blocks_historical_export=False,
    )


def apply_session_command_v1(
    state: SessionStateV1,
    command: SessionCommandV1,
) -> SessionTransitionResultV1:
    """Atomically applies one Command after one full replay of the prior Log."""
    projection = replay_session_state_v1(state)
    if not is_session_command_v1(command):
        raise ValueError("command must be one SessionCommandV1 member.")

    previous_revision = state.revision
    if command.expected_revision != previous_revision:
        diagnostic = _revision_conflict_diagnostic(
            expected_revision=command.expected_revision,
            current_revision=previous_revision,
        )
        return SessionTransitionResultV1(
            status="revision_conflict",
            expected_revision=command.expected_revision,
            previous_revision=previous_revision,
            current_revision=previous_revision,
            command=command,
            state=state,
            diagnostics=(diagnostic,),
        )

    application = apply_session_command_to_projection_v1(projection, command)
    if application.projection is None:
        return SessionTransitionResultV1(
            status="rejected",
            expected_revision=command.expected_revision,
            previous_revision=previous_revision,
            current_revision=previous_revision,
            command=command,
            state=state,
            diagnostics=application.diagnostics,
        )

    current_revision = previous_revision + 1
    candidate_projection = application.projection
    validation = build_session_validation_result_v1(
        candidate_projection,
        revision=current_revision,
    )
    record = SessionCommandRecordV1(
        revision=current_revision,
        command=command,
    )
    candidate_state = SessionStateV1(
        session_contract_version=SESSION_CONTRACT_VERSION,
        session_id=state.session_id,
        initial_capture_mode=state.initial_capture_mode,
        capture_mode=candidate_projection.capture_mode,
        revision=current_revision,
        phase=candidate_projection.phase,
        players=state.players,
        local_player_id=state.local_player_id,
        command_log=(*state.command_log, record),
        validation=validation,
    )
    return SessionTransitionResultV1(
        status="applied",
        expected_revision=command.expected_revision,
        previous_revision=previous_revision,
        current_revision=current_revision,
        command=command,
        state=candidate_state,
        diagnostics=(),
    )
