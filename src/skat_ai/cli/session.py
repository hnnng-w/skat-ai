from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Mapping
from typing import Any

import skat_ai.api.v1.session as session_api
import skat_ai.api.v1.session.files as session_files
from skat_ai import errors as skat_errors
from skat_ai.application import contracts as application_contracts
from skat_ai.cli import (
    session_application,
    session_checkpoints,
    session_context,
    session_operations,
    session_parser,
    session_presentation,
    session_transport,
)
from skat_ai.cli.session_context import SessionContext as _SessionContext
from skat_ai.errors import (
    CLI_EXIT_CODE_FAILURE,
    CLI_EXIT_CODE_USAGE,
    SkatAICliUsageError,
    SkatAIError,
)
from skat_ai.session_checkpoint_collection import (
    SessionCheckpointCollectionResultV1,
    collect_session_decision_checkpoint_v1,
)

ApplicationExecutionOptions = application_contracts.ApplicationExecutionOptions
HistoricalGameApplicationOptions = application_contracts.HistoricalGameApplicationOptions
PositionAnalysisApplicationOptions = application_contracts.PositionAnalysisApplicationOptions

CLI_INVOCATION_STYLES = session_parser.CLI_INVOCATION_STYLES
HISTORICAL_REVIEW_SEARCH_BUDGET_PROFILE = (
    session_parser.HISTORICAL_REVIEW_SEARCH_BUDGET_PROFILE
)
INTERACTIVE_SEARCH_BUDGET_PROFILE = session_parser.INTERACTIVE_SEARCH_BUDGET_PROFILE
MAX_SAMPLE_COUNT = session_parser.MAX_SAMPLE_COUNT
SEARCH_BUDGET_PROFILE_IDENTIFIERS = session_parser.SEARCH_BUDGET_PROFILE_IDENTIFIERS
SEARCH_RECOMMENDATION_METHODS = session_parser.SEARCH_RECOMMENDATION_METHODS
SESSION_CLI_ANALYSIS_POLICY = session_parser.SESSION_CLI_ANALYSIS_POLICY
SESSION_CLI_AUTOMATIC_CHECKPOINT_POLICY = (
    session_parser.SESSION_CLI_AUTOMATIC_CHECKPOINT_POLICY
)
SESSION_CLI_COMMAND = session_parser.SESSION_CLI_COMMAND
SESSION_CLI_CONTRACT_VERSION = session_parser.SESSION_CLI_CONTRACT_VERSION
SESSION_CLI_PERSISTENCE_POLICY = session_parser.SESSION_CLI_PERSISTENCE_POLICY
SESSION_CLI_SUBCOMMANDS = session_parser.SESSION_CLI_SUBCOMMANDS
VALID_RECOMMENDATION_METHODS = session_parser.VALID_RECOMMENDATION_METHODS
DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT = (
    session_parser.DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT
)
RecommendationMethodConfiguration = session_parser.RecommendationMethodConfiguration
build_serializable_bounded_search_settings = (
    session_parser.build_serializable_bounded_search_settings
)
get_search_budget_profile = session_parser.get_search_budget_profile

build_session_argument_parser = session_parser.build_session_argument_parser
parse_session_arguments = session_parser.parse_session_arguments
load_strict_json_object = session_transport.load_strict_json_object

_add_common_options = session_parser._add_common_options
_add_historical_options = session_parser._add_historical_options
_add_position_options = session_parser._add_position_options
_invocation_command = session_parser._invocation_command
_non_negative_integer = session_parser._non_negative_integer
_positive_sample_count = session_parser._positive_sample_count
_reject_duplicate_keys = session_transport._reject_duplicate_keys
_reject_non_finite_constant = session_transport._reject_non_finite_constant

_print_diagnostics = session_presentation.print_diagnostics
_print_output_confirmation = session_presentation.print_output_confirmation
_print_save_conflict = session_presentation.print_save_conflict
_print_session_summary = session_presentation.print_session_summary
_privacy_safe_position_result = session_presentation.privacy_safe_position_result
_write_output = session_presentation.write_output

execute_legacy_application = session_application.execute_legacy_application
print_analysis_result = session_presentation.print_analysis_result
print_field_provenance_summary = session_presentation.print_field_provenance_summary
print_historical_game_result = session_presentation.print_historical_game_result
print_historical_replay_coaching_result = (
    session_presentation.print_historical_replay_coaching_result
)
print_historical_search_review_result = (
    session_presentation.print_historical_search_review_result
)

CLI_EXIT_CODE_SUCCESS = skat_errors.CLI_EXIT_CODE_SUCCESS
SkatAIInvariantError = skat_errors.SkatAIInvariantError
SkatAIValidationError = skat_errors.SkatAIValidationError

_CREATE_INPUT_FIELDS = session_context._CREATE_INPUT_FIELDS
_PLAYER_FIELDS = session_context._PLAYER_FIELDS
_CORRECTION_FIELDS = session_context._CORRECTION_FIELDS


def _require_exact_fields(
    document: Mapping[str, object],
    expected: set[str],
    *,
    name: str,
) -> None:
    session_context.require_exact_fields(document, expected, name=name)


def _parse_create_input(
    document: Mapping[str, object],
) -> tuple[str, tuple[session_api.SessionPlayerV1, ...], str, str | None]:
    return session_context.parse_create_input(document)


def _parse_correction_input(
    document: Mapping[str, object],
) -> session_api.SessionCommandCorrectionV1:
    return session_context.parse_correction_input(document)


def _session_options(include_provenance: bool) -> session_api.SessionApiOptionsV1:
    return session_context.session_options(include_provenance)


def _position_export_options(
    args: argparse.Namespace,
) -> session_api.SessionPositionExportOptionsV1:
    return session_parser.position_export_options(args)


def _load_context(
    file_path: str,
) -> tuple[_SessionContext, session_files.SessionFileApiResultV1]:
    return session_context.load_context(file_path)


def _save_context(
    context: _SessionContext,
    *,
    state: session_api.SessionStateV1,
    decision_checkpoints: tuple[session_api.SessionDecisionCheckpointV1, ...],
) -> session_files.SessionPersistenceWriteResultV1:
    return session_context.save_context(
        context,
        state=state,
        decision_checkpoints=decision_checkpoints,
    )


def _create_context(
    file_path: str,
    document: Mapping[str, object],
    *,
    include_provenance: bool,
) -> tuple[
    session_api.SessionApiResultV1,
    _SessionContext | None,
    session_files.SessionPersistenceWriteResultV1,
]:
    return session_context.create_context(
        file_path,
        document,
        include_provenance=include_provenance,
    )


def _collect_current_checkpoint(
    *,
    state: session_api.SessionStateV1,
    export_options: session_api.SessionPositionExportOptionsV1,
    decision_checkpoints: tuple[session_api.SessionDecisionCheckpointV1, ...],
) -> SessionCheckpointCollectionResultV1:
    return session_checkpoints.collect_current_checkpoint_with(
        state=state,
        export_options=export_options,
        decision_checkpoints=decision_checkpoints,
        collect_checkpoint=collect_session_decision_checkpoint_v1,
    )


def _collect_mutation_checkpoints(
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
    return session_checkpoints.collect_mutation_checkpoints_with(
        source_state=source_state,
        resulting_state=resulting_state,
        source_play_command=source_play_command,
        export_options=export_options,
        decision_checkpoints=decision_checkpoints,
        source_collection=source_collection,
        collect_checkpoint=collect_session_decision_checkpoint_v1,
    )


def _persist_mutation(
    context: _SessionContext,
    *,
    resulting_state: session_api.SessionStateV1,
    source_play_command: session_api.SessionCommandV1 | None,
    export_options: session_api.SessionPositionExportOptionsV1,
    source_collection: SessionCheckpointCollectionResultV1 | None = None,
) -> tuple[
    session_files.SessionPersistenceWriteResultV1,
    tuple[SessionCheckpointCollectionResultV1, ...],
]:
    return session_checkpoints.persist_mutation_with(
        context,
        resulting_state=resulting_state,
        source_play_command=source_play_command,
        export_options=export_options,
        source_collection=source_collection,
        collect_checkpoint=collect_session_decision_checkpoint_v1,
    )


def _collect_source_play_checkpoint(
    context: _SessionContext,
    command: session_api.SessionCommandV1,
    export_options: session_api.SessionPositionExportOptionsV1,
) -> SessionCheckpointCollectionResultV1 | None:
    return session_checkpoints.collect_source_play_checkpoint_with(
        context,
        command,
        export_options,
        collect_checkpoint=collect_session_decision_checkpoint_v1,
    )


def _collect_correction_source_checkpoint(
    context: _SessionContext,
    correction: session_api.SessionCommandCorrectionV1,
    export_options: session_api.SessionPositionExportOptionsV1,
) -> SessionCheckpointCollectionResultV1 | None:
    return session_checkpoints.collect_correction_source_checkpoint_with(
        context,
        correction,
        export_options,
        collect_checkpoint=collect_session_decision_checkpoint_v1,
    )


def _collect_for_analysis(
    context: _SessionContext,
    export_options: session_api.SessionPositionExportOptionsV1,
) -> tuple[
    SessionCheckpointCollectionResultV1,
    session_files.SessionPersistenceWriteResultV1 | None,
]:
    return session_checkpoints.collect_for_analysis_with(
        context,
        export_options,
        collect_checkpoint=collect_session_decision_checkpoint_v1,
    )


def _checkpoint_result(
    *,
    state: session_api.SessionStateV1,
    checkpoint: session_api.SessionDecisionCheckpointV1,
    include_provenance: bool,
    export_options: session_api.SessionPositionExportOptionsV1,
) -> session_api.SessionApiResultV1:
    return session_checkpoints.checkpoint_result(
        state=state,
        checkpoint=checkpoint,
        include_provenance=include_provenance,
        export_options=export_options,
    )


def _selected_checkpoint(
    context: _SessionContext,
    checkpoint_index: int,
) -> session_api.SessionDecisionCheckpointV1:
    return session_checkpoints.selected_checkpoint(context, checkpoint_index)


def _execute_position_request(
    request: object,
    *,
    input_reference: str,
    include_provenance: bool,
) -> dict[str, Any]:
    return session_application.execute_position_request_with_application(
        request,
        input_reference=input_reference,
        include_provenance=include_provenance,
        execute_application=execute_legacy_application,
    )


def _session_input_reference(context: _SessionContext) -> str:
    return session_application.session_input_reference(context)


def _historical_application_options(
    args: argparse.Namespace,
) -> ApplicationExecutionOptions:
    return session_application.historical_application_options(args)


def _execute_historical_request(
    request: object,
    *,
    input_reference: str,
    include_provenance: bool,
    options: ApplicationExecutionOptions,
) -> dict[str, Any]:
    return session_application.execute_historical_request_with_application(
        request,
        input_reference=input_reference,
        include_provenance=include_provenance,
        options=options,
        execute_application=execute_legacy_application,
    )


def _operation_services() -> session_operations.SessionOperationServices:
    return session_operations.SessionOperationServices(
        collect_checkpoint=collect_session_decision_checkpoint_v1,
        execute_application=execute_legacy_application,
    )


def _assistant_operation_services() -> session_operations.SessionOperationServices:
    from skat_ai.cli.session_assistant import SessionAssistantServices

    return session_operations.SessionOperationServices(
        collect_checkpoint=collect_session_decision_checkpoint_v1,
        execute_application=execute_legacy_application,
        assistant_services=SessionAssistantServices(
            load_context=_load_context,
            create_context=_create_context,
            position_export_options=_position_export_options,
            parse_correction_input=_parse_correction_input,
            collect_source_play_checkpoint=_collect_source_play_checkpoint,
            persist_mutation=_persist_mutation,
            collect_correction_source_checkpoint=(
                _collect_correction_source_checkpoint
            ),
            collect_for_analysis=_collect_for_analysis,
            execute_position_request=_execute_position_request,
            execute_historical_request=_execute_historical_request,
            session_input_reference=_session_input_reference,
        ),
    )


def _run_new(args: argparse.Namespace) -> int:
    return session_operations.run_new(args, services=_operation_services())


def _run_show(args: argparse.Namespace) -> int:
    return session_operations.run_show(args, services=_operation_services())


def _finish_mutation(
    args: argparse.Namespace,
    *,
    context: _SessionContext,
    result: session_api.SessionApiResultV1,
    state_changed: bool,
    source_play_command: session_api.SessionCommandV1 | None,
    source_collection: SessionCheckpointCollectionResultV1 | None = None,
) -> int:
    return session_operations.finish_mutation(
        args,
        context=context,
        result=result,
        state_changed=state_changed,
        source_play_command=source_play_command,
        source_collection=source_collection,
        services=_operation_services(),
    )


def _run_apply(args: argparse.Namespace) -> int:
    return session_operations.run_apply(args, services=_operation_services())


def _run_undo(args: argparse.Namespace) -> int:
    return session_operations.run_undo(args, services=_operation_services())


def _run_correct(args: argparse.Namespace) -> int:
    return session_operations.run_correct(args, services=_operation_services())


def _run_checkpoint(args: argparse.Namespace) -> int:
    return session_operations.run_checkpoint(args, services=_operation_services())


def _run_export_position(args: argparse.Namespace) -> int:
    return session_operations.run_export_position(
        args,
        services=_operation_services(),
    )


def _run_export_historical(args: argparse.Namespace) -> int:
    return session_operations.run_export_historical(
        args,
        services=_operation_services(),
    )


def _run_analyze(args: argparse.Namespace) -> int:
    return session_operations.run_analyze(args, services=_operation_services())


def _run_review(args: argparse.Namespace) -> int:
    return session_operations.run_review(args, services=_operation_services())


def _run_finalize(args: argparse.Namespace) -> int:
    return session_operations.run_finalize(args, services=_operation_services())


def _run_assistant(args: argparse.Namespace) -> int:
    return session_operations.run_assistant(
        args,
        services=_assistant_operation_services(),
    )


_SESSION_HANDLERS: dict[str, Callable[[argparse.Namespace], int]] = {
    "new": _run_new,
    "show": _run_show,
    "apply": _run_apply,
    "undo": _run_undo,
    "correct": _run_correct,
    "checkpoint": _run_checkpoint,
    "export-position": _run_export_position,
    "export-historical": _run_export_historical,
    "analyze": _run_analyze,
    "review": _run_review,
    "finalize": _run_finalize,
    "assistant": _run_assistant,
}


def run_session_cli(
    argv: list[str] | tuple[str, ...] | None = None,
    *,
    invocation_style: str = "installed",
) -> int:
    args = parse_session_arguments(argv, invocation_style=invocation_style)
    try:
        return _SESSION_HANDLERS[args.session_subcommand](args)
    except SkatAICliUsageError as error:
        print(f"CLI error: {error}", file=sys.stderr)
        return CLI_EXIT_CODE_USAGE
    except (SkatAIError, TypeError, ValueError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return CLI_EXIT_CODE_FAILURE
