from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

import skatmind.api.v1.session as session_api
import skatmind.api.v1.session.files as session_files
from skatmind.cli import (
    session_application,
    session_checkpoints,
    session_context,
    session_parser,
    session_presentation,
)
from skatmind.cli.session_application import LegacyApplicationExecutor
from skatmind.cli.session_checkpoints import CheckpointCollector
from skatmind.cli.session_context import SessionContext
from skatmind.cli.session_transport import load_strict_json_object
from skatmind.errors import (
    CLI_EXIT_CODE_FAILURE,
    CLI_EXIT_CODE_SUCCESS,
    SkatMindInvariantError,
)
from skatmind.session_checkpoint_collection import (
    SessionCheckpointCollectionResultV1,
    collect_session_decision_checkpoint_v1,
)

if TYPE_CHECKING:
    from skatmind.cli.session_assistant import SessionAssistantServices


@dataclass(frozen=True, slots=True)
class SessionOperationServices:
    collect_checkpoint: CheckpointCollector
    execute_application: LegacyApplicationExecutor
    assistant_services: SessionAssistantServices | None = None


DEFAULT_SESSION_OPERATION_SERVICES = SessionOperationServices(
    collect_checkpoint=collect_session_decision_checkpoint_v1,
    execute_application=session_application.execute_legacy_application,
)


def run_new(
    args: argparse.Namespace,
    *,
    services: SessionOperationServices = DEFAULT_SESSION_OPERATION_SERVICES,
) -> int:
    del services
    created, context, saved = session_context.create_context(
        args.session,
        load_strict_json_object(args.input),
        include_provenance=args.include_provenance,
    )
    if saved.status == "conflict":
        session_presentation.print_save_conflict()
        return CLI_EXIT_CODE_FAILURE
    if args.output is not None:
        session_presentation.write_output(
            args.output,
            session_api.serialize_session_result(created),
        )
    if not args.quiet:
        print("Session creation status:", saved.status)
        session_presentation.print_session_summary(
            context.state,
            context.decision_checkpoints,
        )
        if args.output is not None:
            session_presentation.print_output_confirmation(args.output)
    return CLI_EXIT_CODE_SUCCESS


def run_show(
    args: argparse.Namespace,
    *,
    services: SessionOperationServices = DEFAULT_SESSION_OPERATION_SERVICES,
) -> int:
    del services
    context, loaded = session_context.load_context(args.session)
    if args.output is not None:
        session_presentation.write_output(
            args.output,
            session_files.serialize_session_file_result(loaded),
        )
    if not args.quiet:
        session_presentation.print_session_summary(
            context.state,
            context.decision_checkpoints,
        )
        if args.output is not None:
            session_presentation.print_output_confirmation(args.output)
    return CLI_EXIT_CODE_SUCCESS


def finish_mutation(
    args: argparse.Namespace,
    *,
    context: SessionContext,
    result: session_api.SessionApiResultV1,
    state_changed: bool,
    source_play_command: session_api.SessionCommandV1 | None,
    source_collection: SessionCheckpointCollectionResultV1 | None = None,
    services: SessionOperationServices = DEFAULT_SESSION_OPERATION_SERVICES,
) -> int:
    saved = None
    if state_changed:
        saved, _collections = session_checkpoints.persist_mutation_with(
            context,
            resulting_state=result.value.state,
            source_play_command=source_play_command,
            export_options=session_parser.position_export_options(args),
            source_collection=source_collection,
            collect_checkpoint=services.collect_checkpoint,
        )
        if saved.status == "conflict":
            session_presentation.print_save_conflict()
            return CLI_EXIT_CODE_FAILURE
    if args.output is not None:
        session_presentation.write_output(
            args.output,
            session_api.serialize_session_result(result),
        )
    if not args.quiet:
        print("Session operation:", result.operation)
        print("Operation status:", result.value.status)
        session_presentation.print_diagnostics(result.value.diagnostics)
        session_presentation.print_session_summary(
            context.state,
            context.decision_checkpoints,
        )
        if saved is not None:
            print("Persistence status:", saved.status)
        if args.output is not None:
            session_presentation.print_output_confirmation(args.output)
    return CLI_EXIT_CODE_SUCCESS


def run_apply(
    args: argparse.Namespace,
    *,
    services: SessionOperationServices = DEFAULT_SESSION_OPERATION_SERVICES,
) -> int:
    context, _loaded = session_context.load_context(args.session)
    command = session_api.parse_session_command(load_strict_json_object(args.input))
    source_collection = session_checkpoints.collect_source_play_checkpoint_with(
        context,
        command,
        session_parser.position_export_options(args),
        collect_checkpoint=services.collect_checkpoint,
    )
    result = session_api.apply_session_command(
        context.state,
        command,
        options=session_context.session_options(args.include_provenance),
    )
    return finish_mutation(
        args,
        context=context,
        result=result,
        state_changed=result.value.status == "applied",
        source_play_command=command,
        source_collection=source_collection,
        services=services,
    )


def run_undo(
    args: argparse.Namespace,
    *,
    services: SessionOperationServices = DEFAULT_SESSION_OPERATION_SERVICES,
) -> int:
    context, _loaded = session_context.load_context(args.session)
    result = session_api.rewind_session(
        context.state,
        expected_revision=context.state.revision,
        target_revision=args.target_revision,
        options=session_context.session_options(args.include_provenance),
    )
    return finish_mutation(
        args,
        context=context,
        result=result,
        state_changed=result.value.status == "applied",
        source_play_command=None,
        services=services,
    )


def run_correct(
    args: argparse.Namespace,
    *,
    services: SessionOperationServices = DEFAULT_SESSION_OPERATION_SERVICES,
) -> int:
    context, _loaded = session_context.load_context(args.session)
    correction = session_context.parse_correction_input(
        load_strict_json_object(args.input)
    )
    source_collection = (
        session_checkpoints.collect_correction_source_checkpoint_with(
            context,
            correction,
            session_parser.position_export_options(args),
            collect_checkpoint=services.collect_checkpoint,
        )
    )
    result = session_api.correct_session_command(
        context.state,
        correction,
        options=session_context.session_options(args.include_provenance),
    )
    return finish_mutation(
        args,
        context=context,
        result=result,
        state_changed=result.value.status in {"applied", "partial"},
        source_play_command=None,
        source_collection=source_collection,
        services=services,
    )


def run_checkpoint(
    args: argparse.Namespace,
    *,
    services: SessionOperationServices = DEFAULT_SESSION_OPERATION_SERVICES,
) -> int:
    context, _loaded = session_context.load_context(args.session)
    export_options = session_parser.position_export_options(args)
    collection = session_checkpoints.collect_current_checkpoint_with(
        state=context.state,
        export_options=export_options,
        decision_checkpoints=context.decision_checkpoints,
        collect_checkpoint=services.collect_checkpoint,
    )
    saved = None
    if collection.status == "collected":
        saved = session_context.save_context(
            context,
            state=context.state,
            decision_checkpoints=collection.decision_checkpoints,
        )
        if saved.status == "conflict":
            session_presentation.print_save_conflict()
            return CLI_EXIT_CODE_FAILURE
    if args.output is not None:
        if collection.checkpoint is None:
            output_result = session_api.export_session_position_request(
                context.state,
                export_options,
                options=session_context.session_options(args.include_provenance),
            )
        else:
            output_result = session_checkpoints.checkpoint_result(
                state=context.state,
                checkpoint=collection.checkpoint,
                include_provenance=args.include_provenance,
                export_options=export_options,
            )
        session_presentation.write_output(
            args.output,
            session_api.serialize_session_result(output_result),
        )
    if not args.quiet:
        print("Checkpoint status:", collection.status)
        if collection.checkpoint is not None:
            print("Checkpoint revision:", collection.checkpoint.source_revision)
            print("Decision index:", collection.checkpoint.decision_index)
        session_presentation.print_diagnostics(collection.diagnostics)
        if saved is not None:
            print("Persistence status:", saved.status)
        if args.output is not None:
            session_presentation.print_output_confirmation(args.output)
    return CLI_EXIT_CODE_SUCCESS


def run_export_position(
    args: argparse.Namespace,
    *,
    services: SessionOperationServices = DEFAULT_SESSION_OPERATION_SERVICES,
) -> int:
    context, _loaded = session_context.load_context(args.session)
    export_options = session_parser.position_export_options(args)
    exported = session_api.export_session_position_request(
        context.state,
        export_options,
        options=session_context.session_options(args.include_provenance),
    )
    collection = session_checkpoints.collect_current_checkpoint_with(
        state=context.state,
        export_options=export_options,
        decision_checkpoints=context.decision_checkpoints,
        collect_checkpoint=services.collect_checkpoint,
    )
    saved = None
    if exported.value.status == "available":
        if (
            collection.checkpoint is None
            or collection.checkpoint.request != exported.value.request
        ):
            raise SkatMindInvariantError(
                "Position export and collected Checkpoint disagree."
            )
        if collection.status == "collected":
            saved = session_context.save_context(
                context,
                state=context.state,
                decision_checkpoints=collection.decision_checkpoints,
            )
            if saved.status == "conflict":
                session_presentation.print_save_conflict()
                return CLI_EXIT_CODE_FAILURE
    session_presentation.write_output(
        args.output,
        session_api.serialize_session_result(exported),
    )
    if not args.quiet:
        print("Position export status:", exported.value.status)
        session_presentation.print_diagnostics(exported.value.diagnostics)
        if saved is not None:
            print("Checkpoint persistence status:", saved.status)
        session_presentation.print_output_confirmation(args.output)
    return CLI_EXIT_CODE_SUCCESS


def run_export_historical(
    args: argparse.Namespace,
    *,
    services: SessionOperationServices = DEFAULT_SESSION_OPERATION_SERVICES,
) -> int:
    del services
    context, _loaded = session_context.load_context(args.session)
    exported = session_api.export_session_historical_request(
        context.state,
        options=session_context.session_options(args.include_provenance),
    )
    session_presentation.write_output(
        args.output,
        session_api.serialize_session_result(exported),
    )
    if not args.quiet:
        print("Historical export status:", exported.value.status)
        session_presentation.print_diagnostics(exported.value.diagnostics)
        session_presentation.print_output_confirmation(args.output)
    return CLI_EXIT_CODE_SUCCESS


def run_analyze(
    args: argparse.Namespace,
    *,
    services: SessionOperationServices = DEFAULT_SESSION_OPERATION_SERVICES,
) -> int:
    context, _loaded = session_context.load_context(args.session)
    export_options = session_parser.position_export_options(args)
    if context.state.validation.position_export.status == "unavailable":
        unavailable = session_api.export_session_position_request(
            context.state,
            export_options,
            options=session_context.session_options(args.include_provenance),
        )
        session_presentation.write_output(
            args.output,
            session_api.serialize_session_result(unavailable),
        )
        if not args.quiet:
            print("Position analysis status: unavailable")
            session_presentation.print_diagnostics(unavailable.value.diagnostics)
            session_presentation.print_output_confirmation(args.output)
        return CLI_EXIT_CODE_SUCCESS

    collection, saved = session_checkpoints.collect_for_analysis_with(
        context,
        export_options,
        collect_checkpoint=services.collect_checkpoint,
    )
    if saved is not None and saved.status == "conflict":
        session_presentation.print_save_conflict()
        return CLI_EXIT_CODE_FAILURE
    if collection.checkpoint is None:
        raise SkatMindInvariantError(
            "A Position-ready Session did not produce a Decision Checkpoint."
        )

    result = session_application.execute_position_request_with_application(
        collection.checkpoint.request,
        input_reference=session_application.session_input_reference(context),
        include_provenance=args.include_provenance,
        execute_application=services.execute_application,
    )
    session_presentation.write_output(args.output, result)
    if not args.quiet:
        print(
            "Session checkpoint:",
            f"revision {collection.checkpoint.source_revision}, "
            f"decision {collection.checkpoint.decision_index}, {collection.status}",
        )
        session_presentation.print_analysis_result(
            session_presentation.privacy_safe_position_result(result)
        )
        session_presentation.print_output_confirmation(args.output)
        session_presentation.print_field_provenance_summary(result)
    return CLI_EXIT_CODE_SUCCESS


def run_review(
    args: argparse.Namespace,
    *,
    services: SessionOperationServices = DEFAULT_SESSION_OPERATION_SERVICES,
) -> int:
    context, _loaded = session_context.load_context(args.session)
    checkpoint = session_checkpoints.selected_checkpoint(
        context,
        args.checkpoint_index,
    )
    exported = session_api.export_session_checkpoint_review_request(
        state=context.state,
        checkpoint=checkpoint,
        options=session_context.session_options(args.include_provenance),
    )
    if exported.value.status != "available":
        session_presentation.write_output(
            args.output,
            session_api.serialize_session_result(exported),
        )
        if not args.quiet:
            print("Checkpoint review status:", exported.value.status)
            print("Observation status:", exported.value.observation.status)
            session_presentation.print_diagnostics(exported.value.diagnostics)
            session_presentation.print_output_confirmation(args.output)
        return CLI_EXIT_CODE_SUCCESS

    result = session_application.execute_position_request_with_application(
        exported.value.request,
        input_reference=session_application.session_input_reference(context),
        include_provenance=args.include_provenance,
        execute_application=services.execute_application,
    )
    session_presentation.write_output(args.output, result)
    if not args.quiet:
        print("Checkpoint review status: available")
        print("Checkpoint index:", args.checkpoint_index)
        print("Observed actual card:", exported.value.observation.actual_card)
        session_presentation.print_analysis_result(
            session_presentation.privacy_safe_position_result(result)
        )
        session_presentation.print_output_confirmation(args.output)
        session_presentation.print_field_provenance_summary(result)
    return CLI_EXIT_CODE_SUCCESS


def run_finalize(
    args: argparse.Namespace,
    *,
    services: SessionOperationServices = DEFAULT_SESSION_OPERATION_SERVICES,
) -> int:
    context, _loaded = session_context.load_context(args.session)
    exported = session_api.export_session_historical_request(
        context.state,
        options=session_context.session_options(args.include_provenance),
    )
    if exported.value.status != "available":
        session_presentation.write_output(
            args.output,
            session_api.serialize_session_result(exported),
        )
        if not args.quiet:
            print("Historical finalize status: unavailable")
            session_presentation.print_diagnostics(exported.value.diagnostics)
            session_presentation.print_output_confirmation(args.output)
        return CLI_EXIT_CODE_SUCCESS

    result = session_application.execute_historical_request_with_application(
        exported.value.request,
        input_reference=session_application.session_input_reference(context),
        include_provenance=args.include_provenance,
        options=session_application.historical_application_options(args),
        execute_application=services.execute_application,
    )
    session_presentation.write_output(args.output, result)
    if not args.quiet:
        session_presentation.print_historical_game_result(result)
        summary = result["historical_game_summary"]
        if args.historical_search_review:
            session_presentation.print_historical_search_review_result(
                summary["historical_search_review_summary"]
            )
        if args.historical_replay_coaching:
            session_presentation.print_historical_replay_coaching_result(
                summary["historical_replay_coaching_summary"]
            )
        session_presentation.print_output_confirmation(args.output)
        session_presentation.print_field_provenance_summary(result)
    return CLI_EXIT_CODE_SUCCESS


def run_assistant(
    args: argparse.Namespace,
    *,
    services: SessionOperationServices = DEFAULT_SESSION_OPERATION_SERVICES,
) -> int:
    from skatmind.cli.session_assistant import (
        run_session_assistant,
        session_assistant_services,
    )

    if services.assistant_services is None:
        return run_session_assistant(args.session)
    with session_assistant_services(services.assistant_services):
        return run_session_assistant(args.session)


SessionOperationHandler = Callable[..., int]

SESSION_OPERATION_HANDLERS: dict[str, SessionOperationHandler] = {
    "new": run_new,
    "show": run_show,
    "apply": run_apply,
    "undo": run_undo,
    "correct": run_correct,
    "checkpoint": run_checkpoint,
    "export-position": run_export_position,
    "export-historical": run_export_historical,
    "analyze": run_analyze,
    "review": run_review,
    "finalize": run_finalize,
    "assistant": run_assistant,
}


def dispatch_session_operation(
    args: argparse.Namespace,
    *,
    services: SessionOperationServices = DEFAULT_SESSION_OPERATION_SERVICES,
) -> int:
    return SESSION_OPERATION_HANDLERS[args.session_subcommand](
        args,
        services=services,
    )
