from __future__ import annotations

from collections.abc import Callable

import skat_ai.api.v1.session as session_api
import skat_ai.api.v1.session.files as session_files
from skat_ai.api.v1.session.execution import _result as _session_api_result
from skat_ai.cli.session_context import SessionContext, save_context, session_options
from skat_ai.errors import SkatAICliUsageError
from skat_ai.session_checkpoint_collection import (
    SessionCheckpointCollectionResultV1,
    collect_session_decision_checkpoint_v1,
)
from skat_ai.session_history import build_session_state_from_accepted_prefix_v1

CheckpointCollector = Callable[..., SessionCheckpointCollectionResultV1]


def collect_current_checkpoint_with(
    *,
    state: session_api.SessionStateV1,
    export_options: session_api.SessionPositionExportOptionsV1,
    decision_checkpoints: tuple[session_api.SessionDecisionCheckpointV1, ...],
    collect_checkpoint: CheckpointCollector,
) -> SessionCheckpointCollectionResultV1:
    return collect_checkpoint(
        state=state,
        export_options=export_options,
        decision_checkpoints=decision_checkpoints,
    )


def collect_current_checkpoint(
    *,
    state: session_api.SessionStateV1,
    export_options: session_api.SessionPositionExportOptionsV1,
    decision_checkpoints: tuple[session_api.SessionDecisionCheckpointV1, ...],
) -> SessionCheckpointCollectionResultV1:
    return collect_current_checkpoint_with(
        state=state,
        export_options=export_options,
        decision_checkpoints=decision_checkpoints,
        collect_checkpoint=collect_session_decision_checkpoint_v1,
    )


def collect_mutation_checkpoints_with(
    *,
    source_state: session_api.SessionStateV1,
    resulting_state: session_api.SessionStateV1,
    source_play_command: session_api.SessionCommandV1 | None,
    export_options: session_api.SessionPositionExportOptionsV1,
    decision_checkpoints: tuple[session_api.SessionDecisionCheckpointV1, ...],
    collect_checkpoint: CheckpointCollector,
    source_collection: SessionCheckpointCollectionResultV1 | None = None,
) -> tuple[
    tuple[session_api.SessionDecisionCheckpointV1, ...],
    tuple[SessionCheckpointCollectionResultV1, ...],
]:
    checkpoints = (
        decision_checkpoints
        if source_collection is None
        else source_collection.decision_checkpoints
    )
    collections: list[SessionCheckpointCollectionResultV1] = (
        [] if source_collection is None else [source_collection]
    )
    if (
        source_collection is None
        and isinstance(source_play_command, session_api.RecordSessionPlayCommandV1)
        and source_play_command.player_id == source_state.local_player_id
        and source_state.validation.position_export.status == "available"
    ):
        source_collection = collect_current_checkpoint_with(
            state=source_state,
            export_options=export_options,
            decision_checkpoints=checkpoints,
            collect_checkpoint=collect_checkpoint,
        )
        checkpoints = source_collection.decision_checkpoints
        collections.append(source_collection)
    if resulting_state.validation.position_export.status == "available":
        resulting_collection = collect_current_checkpoint_with(
            state=resulting_state,
            export_options=export_options,
            decision_checkpoints=checkpoints,
            collect_checkpoint=collect_checkpoint,
        )
        checkpoints = resulting_collection.decision_checkpoints
        collections.append(resulting_collection)
    return checkpoints, tuple(collections)


def collect_mutation_checkpoints(
    *,
    source_state: session_api.SessionStateV1,
    resulting_state: session_api.SessionStateV1,
    source_play_command: session_api.SessionCommandV1 | None,
    export_options: session_api.SessionPositionExportOptionsV1,
    decision_checkpoints: tuple[session_api.SessionDecisionCheckpointV1, ...],
    source_collection: SessionCheckpointCollectionResultV1 | None = None,
) -> tuple[
    tuple[session_api.SessionDecisionCheckpointV1, ...],
    tuple[SessionCheckpointCollectionResultV1, ...],
]:
    return collect_mutation_checkpoints_with(
        source_state=source_state,
        resulting_state=resulting_state,
        source_play_command=source_play_command,
        export_options=export_options,
        decision_checkpoints=decision_checkpoints,
        source_collection=source_collection,
        collect_checkpoint=collect_session_decision_checkpoint_v1,
    )


def persist_mutation_with(
    context: SessionContext,
    *,
    resulting_state: session_api.SessionStateV1,
    source_play_command: session_api.SessionCommandV1 | None,
    export_options: session_api.SessionPositionExportOptionsV1,
    collect_checkpoint: CheckpointCollector,
    source_collection: SessionCheckpointCollectionResultV1 | None = None,
) -> tuple[
    session_files.SessionPersistenceWriteResultV1,
    tuple[SessionCheckpointCollectionResultV1, ...],
]:
    checkpoints, collections = collect_mutation_checkpoints_with(
        source_state=context.state,
        resulting_state=resulting_state,
        source_play_command=source_play_command,
        export_options=export_options,
        decision_checkpoints=context.decision_checkpoints,
        source_collection=source_collection,
        collect_checkpoint=collect_checkpoint,
    )
    saved = save_context(
        context,
        state=resulting_state,
        decision_checkpoints=checkpoints,
    )
    return saved, collections


def persist_mutation(
    context: SessionContext,
    *,
    resulting_state: session_api.SessionStateV1,
    source_play_command: session_api.SessionCommandV1 | None,
    export_options: session_api.SessionPositionExportOptionsV1,
    source_collection: SessionCheckpointCollectionResultV1 | None = None,
) -> tuple[
    session_files.SessionPersistenceWriteResultV1,
    tuple[SessionCheckpointCollectionResultV1, ...],
]:
    return persist_mutation_with(
        context,
        resulting_state=resulting_state,
        source_play_command=source_play_command,
        export_options=export_options,
        source_collection=source_collection,
        collect_checkpoint=collect_session_decision_checkpoint_v1,
    )


def collect_source_play_checkpoint_with(
    context: SessionContext,
    command: session_api.SessionCommandV1,
    export_options: session_api.SessionPositionExportOptionsV1,
    *,
    collect_checkpoint: CheckpointCollector,
) -> SessionCheckpointCollectionResultV1 | None:
    if (
        isinstance(command, session_api.RecordSessionPlayCommandV1)
        and command.player_id == context.state.local_player_id
        and context.state.validation.position_export.status == "available"
    ):
        return collect_current_checkpoint_with(
            state=context.state,
            export_options=export_options,
            decision_checkpoints=context.decision_checkpoints,
            collect_checkpoint=collect_checkpoint,
        )
    return None


def collect_source_play_checkpoint(
    context: SessionContext,
    command: session_api.SessionCommandV1,
    export_options: session_api.SessionPositionExportOptionsV1,
) -> SessionCheckpointCollectionResultV1 | None:
    return collect_source_play_checkpoint_with(
        context,
        command,
        export_options,
        collect_checkpoint=collect_session_decision_checkpoint_v1,
    )


def collect_correction_source_checkpoint_with(
    context: SessionContext,
    correction: session_api.SessionCommandCorrectionV1,
    export_options: session_api.SessionPositionExportOptionsV1,
    *,
    collect_checkpoint: CheckpointCollector,
) -> SessionCheckpointCollectionResultV1 | None:
    if (
        correction.expected_revision != context.state.revision
        or correction.target_revision > context.state.revision
        or not isinstance(
            correction.replacement_command,
            session_api.RecordSessionPlayCommandV1,
        )
    ):
        return None
    prefix = build_session_state_from_accepted_prefix_v1(
        context.state,
        target_revision=correction.target_revision - 1,
    )
    if (
        correction.replacement_command.player_id != prefix.local_player_id
        or prefix.validation.position_export.status != "available"
    ):
        return None
    return collect_current_checkpoint_with(
        state=prefix,
        export_options=export_options,
        decision_checkpoints=context.decision_checkpoints,
        collect_checkpoint=collect_checkpoint,
    )


def collect_correction_source_checkpoint(
    context: SessionContext,
    correction: session_api.SessionCommandCorrectionV1,
    export_options: session_api.SessionPositionExportOptionsV1,
) -> SessionCheckpointCollectionResultV1 | None:
    return collect_correction_source_checkpoint_with(
        context,
        correction,
        export_options,
        collect_checkpoint=collect_session_decision_checkpoint_v1,
    )


def collect_for_analysis_with(
    context: SessionContext,
    export_options: session_api.SessionPositionExportOptionsV1,
    *,
    collect_checkpoint: CheckpointCollector,
) -> tuple[
    SessionCheckpointCollectionResultV1,
    session_files.SessionPersistenceWriteResultV1 | None,
]:
    collection = collect_current_checkpoint_with(
        state=context.state,
        export_options=export_options,
        decision_checkpoints=context.decision_checkpoints,
        collect_checkpoint=collect_checkpoint,
    )
    saved = None
    if collection.status == "collected":
        saved = save_context(
            context,
            state=context.state,
            decision_checkpoints=collection.decision_checkpoints,
        )
    return collection, saved


def collect_for_analysis(
    context: SessionContext,
    export_options: session_api.SessionPositionExportOptionsV1,
) -> tuple[
    SessionCheckpointCollectionResultV1,
    session_files.SessionPersistenceWriteResultV1 | None,
]:
    return collect_for_analysis_with(
        context,
        export_options,
        collect_checkpoint=collect_session_decision_checkpoint_v1,
    )


def checkpoint_result(
    *,
    state: session_api.SessionStateV1,
    checkpoint: session_api.SessionDecisionCheckpointV1,
    include_provenance: bool,
    export_options: session_api.SessionPositionExportOptionsV1,
) -> session_api.SessionApiResultV1:
    position_export = session_api.SessionRequestExportV1(
        session_id=state.session_id,
        source_revision=state.revision,
        target="position_analysis",
        status="available",
        request=checkpoint.request,
        diagnostics=(),
    )
    return _session_api_result(
        operation="build_checkpoint",
        value=checkpoint,
        options=session_options(include_provenance),
        source_state=state,
        retained_inputs={
            "state": state,
            "position_export": position_export,
            "export_options": export_options,
        },
    )


def selected_checkpoint(
    context: SessionContext,
    checkpoint_index: int,
) -> session_api.SessionDecisionCheckpointV1:
    if checkpoint_index >= len(context.decision_checkpoints):
        raise SkatAICliUsageError(
            "--checkpoint-index must identify an existing canonical Checkpoint."
        )
    return context.decision_checkpoints[checkpoint_index]


_collect_current_checkpoint = collect_current_checkpoint
_collect_mutation_checkpoints = collect_mutation_checkpoints
_persist_mutation = persist_mutation
_collect_source_play_checkpoint = collect_source_play_checkpoint
_collect_correction_source_checkpoint = collect_correction_source_checkpoint
_collect_for_analysis = collect_for_analysis
_checkpoint_result = checkpoint_result
_selected_checkpoint = selected_checkpoint
