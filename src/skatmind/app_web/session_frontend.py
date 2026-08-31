from __future__ import annotations

import os
import threading
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

import skatmind.api.v1.session as session_api
import skatmind.api.v1.session.files as session_files
from skatmind.api.v1 import ExecutionOptionsV1
from skatmind.errors import SkatMindInvariantError
from skatmind.session_checkpoint_collection import (
    collect_session_decision_checkpoint_v1,
)
from skatmind.session_persistence import _build_session_persistence_file_bytes_v1
from skatmind.simulation import DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT

from .execution import (
    GuidedFrontendExecutionV1,
    execute_guided_frontend_analysis_v1,
    execute_guided_frontend_review_v1,
)
from .managed_item_contracts import DiscoveredManagedItemV1
from .managed_item_storage import (
    build_managed_item_storage_path_v1,
    validate_managed_direct_child_path_v1,
)


def default_session_position_export_options_v1(
) -> session_api.SessionPositionExportOptionsV1:
    return session_api.SessionPositionExportOptionsV1(
        sample_count=DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT,
        random_seed=0,
        use_basic_opponent_strategy=True,
        recommendation_method=None,
        bounded_search_settings=None,
    )


def build_guided_session_players_v1(
    values: Mapping[str, str],
) -> tuple[session_api.SessionPlayerV1, ...]:
    return tuple(
        session_api.SessionPlayerV1(
            player_id=values[f"player_{index}_id"],
            player_label=values[f"player_{index}_label"] or None,
            seat=seat,
        )
        for index, seat in enumerate(
            ("forehand", "middlehand", "rearhand"),
            start=1,
        )
    )


def get_guided_session_import_product_id_v1(
    document: Mapping[str, object],
) -> str:
    return session_api.resume_session_document(document).value.document.state.session_id


def default_guided_session_execution_options_v1() -> ExecutionOptionsV1:
    return ExecutionOptionsV1()


@dataclass(frozen=True, slots=True, kw_only=True)
class GuidedSessionOperationResultV1:
    status: str
    message: str
    diagnostics: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.status not in {
            "created",
            "imported",
            "opened",
            "reloaded",
            "applied",
            "partial",
            "unchanged",
            "rejected",
            "conflict",
            "unavailable",
            "executed",
            "stale",
        }:
            raise ValueError("status must identify one guided Session outcome.")
        if type(self.message) is not str or not self.message:
            raise ValueError("message must be non-empty text.")
        if type(self.diagnostics) is not tuple or any(
            type(item) is not str or not item for item in self.diagnostics
        ):
            raise ValueError("diagnostics must contain non-empty text.")


@dataclass(slots=True, kw_only=True)
class GuidedSessionContextV1:
    """One active managed Session and its revision-scoped process-local Result."""

    category_root: Path = field(repr=False)
    path: Path = field(repr=False)
    handle: str
    document: session_api.SessionPersistenceDocumentV1 = field(repr=False)
    generation: int = 1
    last_operation: GuidedSessionOperationResultV1 | None = None
    execution: GuidedFrontendExecutionV1 | None = field(default=None, repr=False)
    lock: threading.RLock = field(default_factory=threading.RLock, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.category_root, Path) or not isinstance(self.path, Path):
            raise ValueError("Managed Session paths must be private Paths.")
        if self.path.parent != self.category_root:
            raise ValueError("Managed Session must be one direct category child.")
        if type(self.handle) is not str or len(self.handle) != 64:
            raise ValueError("handle must be one opaque managed handle.")
        if type(self.document) is not session_api.SessionPersistenceDocumentV1:
            raise ValueError("document must be a SessionPersistenceDocumentV1.")
        if type(self.generation) is not int or self.generation < 1:
            raise ValueError("generation must be a positive integer.")

    @property
    def state(self) -> session_api.SessionStateV1:
        return self.document.state

    @property
    def decision_checkpoints(
        self,
    ) -> tuple[session_api.SessionDecisionCheckpointV1, ...]:
        return self.document.decision_checkpoints


def _diagnostic_messages(value: object) -> tuple[str, ...]:
    diagnostics = getattr(value, "diagnostics", ())
    return tuple(
        f"{diagnostic.code}: {diagnostic.message}" for diagnostic in diagnostics
    )


def _create_context(
    *,
    category_root: Path,
    path: Path,
    handle: str,
    document: session_api.SessionPersistenceDocumentV1,
    status: str,
    message: str,
) -> GuidedSessionContextV1:
    return GuidedSessionContextV1(
        category_root=category_root,
        path=path,
        handle=handle,
        document=document,
        last_operation=GuidedSessionOperationResultV1(
            status=status,
            message=message,
        ),
    )


def create_guided_session_v1(
    category_root: Path,
    *,
    handle: str,
    session_id: str,
    players: tuple[session_api.SessionPlayerV1, ...],
    capture_mode: str,
    local_player_id: str | None,
) -> GuidedSessionContextV1:
    created = session_api.create_session(
        session_id=session_id,
        players=players,
        capture_mode=capture_mode,
        local_player_id=local_player_id,
    )
    document = session_api.build_session_persistence_document(created.value).value
    path = build_managed_item_storage_path_v1(
        category_root,
        family="sessions",
        product_id=session_id,
    )
    if os.path.lexists(path):
        raise FileExistsError("A managed Session already uses this Product identity.")
    saved = session_files.save_session_file(
        path,
        document,
        expected_content_fingerprint=None,
    ).value
    if saved.status != "saved":
        raise SkatMindInvariantError("New managed Session was not saved exactly once.")
    return _create_context(
        category_root=category_root,
        path=path,
        handle=handle,
        document=document,
        status="created",
        message="The Session was created and opened.",
    )


def import_guided_session_v1(
    category_root: Path,
    *,
    handle: str,
    document: dict[str, object],
) -> GuidedSessionContextV1:
    resumed = session_api.resume_session_document(document).value
    persistence = resumed.document
    path = build_managed_item_storage_path_v1(
        category_root,
        family="sessions",
        product_id=persistence.state.session_id,
    )
    if os.path.lexists(path):
        raise FileExistsError("A managed Session already uses this Product identity.")
    saved = session_files.save_session_file(
        path,
        persistence,
        expected_content_fingerprint=None,
    ).value
    if saved.status != "saved":
        raise SkatMindInvariantError("Imported managed Session was not saved exactly once.")
    return _create_context(
        category_root=category_root,
        path=path,
        handle=handle,
        document=persistence,
        status="imported",
        message="The Session was validated, imported, and opened.",
    )


def open_guided_session_v1(
    category_root: Path,
    entry: DiscoveredManagedItemV1,
) -> GuidedSessionContextV1:
    if entry.summary.family != "sessions" or entry.summary.status != "available":
        raise ValueError("Only one available discovered Session can be opened.")
    validate_managed_direct_child_path_v1(
        category_root,
        entry.path,
        expected_kind="file",
    )
    loaded = session_files.load_session_file(entry.path).value.document
    if loaded.state.session_id != entry.summary.semantic_product_id:
        raise ValueError("Managed Session identity changed after discovery.")
    return _create_context(
        category_root=category_root,
        path=entry.path,
        handle=entry.summary.handle,
        document=loaded,
        status="opened",
        message="The Session was opened.",
    )


def reload_guided_session_v1(context: GuidedSessionContextV1) -> GuidedSessionOperationResultV1:
    with context.lock:
        validate_managed_direct_child_path_v1(
            context.category_root,
            context.path,
            expected_kind="file",
        )
        loaded = session_files.load_session_file(context.path).value.document
        if loaded.state.session_id != context.state.session_id:
            raise ValueError("Managed Session identity changed on disk.")
        context.document = loaded
        context.generation += 1
        context.execution = None
        context.last_operation = GuidedSessionOperationResultV1(
            status="reloaded",
            message="The Session was reloaded; process-local Results were discarded.",
        )
        return context.last_operation


def _collect_current_checkpoint(
    *,
    state: session_api.SessionStateV1,
    checkpoints: tuple[session_api.SessionDecisionCheckpointV1, ...],
    export_options: session_api.SessionPositionExportOptionsV1,
) -> tuple[session_api.SessionDecisionCheckpointV1, ...]:
    return collect_session_decision_checkpoint_v1(
        state=state,
        export_options=export_options,
        decision_checkpoints=checkpoints,
    ).decision_checkpoints


def _persist_session_mutation(
    context: GuidedSessionContextV1,
    *,
    state: session_api.SessionStateV1,
    checkpoints: tuple[session_api.SessionDecisionCheckpointV1, ...],
    result_status: str,
    diagnostics: tuple[str, ...],
) -> GuidedSessionOperationResultV1:
    validate_managed_direct_child_path_v1(
        context.category_root,
        context.path,
        expected_kind="file",
    )
    persistence = session_api.build_session_persistence_document(
        state,
        decision_checkpoints=checkpoints,
    ).value
    saved = session_files.save_session_file(
        context.path,
        persistence,
        expected_content_fingerprint=context.document.content_fingerprint,
    ).value
    if saved.status == "conflict":
        operation = GuidedSessionOperationResultV1(
            status="conflict",
            message="The Session changed on disk. Reload before retrying this edit.",
        )
    else:
        context.document = persistence
        context.generation += 1
        context.execution = None
        operation = GuidedSessionOperationResultV1(
            status=result_status,
            message="The Session edit was persisted.",
            diagnostics=diagnostics,
        )
    context.last_operation = operation
    return operation


def apply_guided_session_command_v1(
    context: GuidedSessionContextV1,
    command: session_api.SessionCommandV1,
    *,
    export_options: session_api.SessionPositionExportOptionsV1 | None = None,
) -> GuidedSessionOperationResultV1:
    options = export_options or default_session_position_export_options_v1()
    with context.lock:
        checkpoints = _collect_current_checkpoint(
            state=context.state,
            checkpoints=context.decision_checkpoints,
            export_options=options,
        )
        result = session_api.apply_session_command(context.state, command)
        diagnostics = _diagnostic_messages(result.value)
        if result.value.status != "applied":
            operation = GuidedSessionOperationResultV1(
                status="rejected",
                message="The Session Command was rejected without changing the Session.",
                diagnostics=diagnostics,
            )
            context.last_operation = operation
            return operation
        checkpoints = _collect_current_checkpoint(
            state=result.value.state,
            checkpoints=checkpoints,
            export_options=options,
        )
        return _persist_session_mutation(
            context,
            state=result.value.state,
            checkpoints=checkpoints,
            result_status="applied",
            diagnostics=diagnostics,
        )


def apply_guided_session_edit_v1(
    context: GuidedSessionContextV1,
    edit: session_api.SessionCommandV1 | session_api.SessionCommandCorrectionV1,
) -> GuidedSessionOperationResultV1:
    if type(edit) is session_api.SessionCommandCorrectionV1:
        return correct_guided_session_command_v1(context, edit)
    return apply_guided_session_command_v1(context, edit)


def rewind_guided_session_v1(
    context: GuidedSessionContextV1,
    *,
    target_revision: int,
    export_options: session_api.SessionPositionExportOptionsV1 | None = None,
) -> GuidedSessionOperationResultV1:
    options = export_options or default_session_position_export_options_v1()
    with context.lock:
        result = session_api.rewind_session(
            context.state,
            expected_revision=context.state.revision,
            target_revision=target_revision,
        )
        diagnostics = _diagnostic_messages(result.value)
        if result.value.status not in {"applied", "unchanged"}:
            operation = GuidedSessionOperationResultV1(
                status="rejected",
                message="The Session rewind was rejected without changing the Session.",
                diagnostics=diagnostics,
            )
            context.last_operation = operation
            return operation
        if result.value.status == "unchanged":
            operation = GuidedSessionOperationResultV1(
                status="unchanged",
                message="The Session already has the requested revision.",
            )
            context.last_operation = operation
            return operation
        checkpoints = _collect_current_checkpoint(
            state=result.value.state,
            checkpoints=context.decision_checkpoints,
            export_options=options,
        )
        return _persist_session_mutation(
            context,
            state=result.value.state,
            checkpoints=checkpoints,
            result_status="applied",
            diagnostics=diagnostics,
        )


def correct_guided_session_command_v1(
    context: GuidedSessionContextV1,
    correction: session_api.SessionCommandCorrectionV1,
    *,
    export_options: session_api.SessionPositionExportOptionsV1 | None = None,
) -> GuidedSessionOperationResultV1:
    options = export_options or default_session_position_export_options_v1()
    with context.lock:
        checkpoints = context.decision_checkpoints
        source = session_api.rewind_session(
            context.state,
            expected_revision=context.state.revision,
            target_revision=correction.target_revision - 1,
        )
        if source.value.status in {"applied", "unchanged"}:
            checkpoints = _collect_current_checkpoint(
                state=source.value.state,
                checkpoints=checkpoints,
                export_options=options,
            )
        result = session_api.correct_session_command(context.state, correction)
        diagnostics = _diagnostic_messages(result.value)
        if result.value.status not in {"applied", "partial", "unchanged"}:
            operation = GuidedSessionOperationResultV1(
                status="rejected",
                message="The Session correction was rejected without changing the Session.",
                diagnostics=diagnostics,
            )
            context.last_operation = operation
            return operation
        if result.value.status == "unchanged":
            operation = GuidedSessionOperationResultV1(
                status="unchanged",
                message="The replacement Command is already retained.",
            )
            context.last_operation = operation
            return operation
        checkpoints = _collect_current_checkpoint(
            state=result.value.state,
            checkpoints=checkpoints,
            export_options=options,
        )
        return _persist_session_mutation(
            context,
            state=result.value.state,
            checkpoints=checkpoints,
            result_status=result.value.status,
            diagnostics=diagnostics,
        )


def execute_guided_session_position_v1(
    context: GuidedSessionContextV1,
    *,
    export_options: session_api.SessionPositionExportOptionsV1,
    execution_options: ExecutionOptionsV1,
) -> GuidedSessionOperationResultV1:
    with context.lock:
        exported = session_api.export_session_position_request(
            context.state,
            export_options,
        )
        if exported.value.status != "available":
            operation = GuidedSessionOperationResultV1(
                status="unavailable",
                message="This Session is not ready for Position analysis.",
                diagnostics=_diagnostic_messages(exported.value),
            )
            context.last_operation = operation
            return operation
        checkpoints = _collect_current_checkpoint(
            state=context.state,
            checkpoints=context.decision_checkpoints,
            export_options=export_options,
        )
        if checkpoints != context.decision_checkpoints:
            persisted = _persist_session_mutation(
                context,
                state=context.state,
                checkpoints=checkpoints,
                result_status="applied",
                diagnostics=(),
            )
            if persisted.status == "conflict":
                return persisted
        source_generation = context.generation
        source_fingerprint = context.document.content_fingerprint
        request = exported.value.request
    execution = execute_guided_frontend_analysis_v1(
        request,
        options=execution_options,
    )
    with context.lock:
        if (
            context.generation != source_generation
            or context.document.content_fingerprint != source_fingerprint
        ):
            operation = GuidedSessionOperationResultV1(
                status="stale",
                message="The Session changed while analysis ran; the stale Result was discarded.",
            )
        else:
            context.execution = execution
            operation = GuidedSessionOperationResultV1(
                status="executed",
                message="Position analysis completed for the current Session revision.",
            )
        context.last_operation = operation
        return operation


def execute_guided_session_historical_v1(
    context: GuidedSessionContextV1,
    *,
    execution_options: ExecutionOptionsV1,
) -> GuidedSessionOperationResultV1:
    with context.lock:
        exported = session_api.export_session_historical_request(context.state)
        if exported.value.status != "available":
            operation = GuidedSessionOperationResultV1(
                status="unavailable",
                message="This Session is not ready for completed-game Review.",
                diagnostics=_diagnostic_messages(exported.value),
            )
            context.last_operation = operation
            return operation
        source_generation = context.generation
        source_fingerprint = context.document.content_fingerprint
        request = exported.value.request
    execution = execute_guided_frontend_review_v1(
        request,
        options=execution_options,
    )
    with context.lock:
        if (
            context.generation != source_generation
            or context.document.content_fingerprint != source_fingerprint
        ):
            operation = GuidedSessionOperationResultV1(
                status="stale",
                message="The Session changed while Review ran; the stale Result was discarded.",
            )
        else:
            context.execution = execution
            operation = GuidedSessionOperationResultV1(
                status="executed",
                message="Completed-game Review finished for the current Session revision.",
            )
        context.last_operation = operation
        return operation


def build_guided_session_persistence_download_v1(
    context: GuidedSessionContextV1,
) -> bytes:
    with context.lock:
        return _build_session_persistence_file_bytes_v1(context.document)
