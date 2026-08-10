from __future__ import annotations

import argparse
import copy
import json
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import skat_ai.api.v1.session as session_api
import skat_ai.api.v1.session.files as session_files
from skat_ai.api.v1.session.execution import _result as _session_api_result
from skat_ai.api.v1.session.schema_validation import (
    validate_session_correction_document,
    validate_session_create_document,
)
from skat_ai.application.contracts import (
    ApplicationExecutionOptions,
    HistoricalGameApplicationOptions,
    PositionAnalysisApplicationOptions,
)
from skat_ai.cli.execution import (
    CLI_INVOCATION_STYLES,
    execute_legacy_application,
    print_analysis_result,
    print_field_provenance_summary,
    print_historical_game_result,
    print_historical_replay_coaching_result,
    print_historical_search_review_result,
)
from skat_ai.errors import (
    CLI_EXIT_CODE_FAILURE,
    CLI_EXIT_CODE_SUCCESS,
    CLI_EXIT_CODE_USAGE,
    SkatAICliUsageError,
    SkatAIError,
    SkatAIInvariantError,
    SkatAIValidationError,
)
from skat_ai.input_validation import MAX_SAMPLE_COUNT
from skat_ai.output_writer import write_analysis_result_to_json
from skat_ai.recommendation_workflow import (
    SEARCH_RECOMMENDATION_METHODS,
    VALID_RECOMMENDATION_METHODS,
    RecommendationMethodConfiguration,
    build_serializable_bounded_search_settings,
)
from skat_ai.search_budget_profiles import (
    HISTORICAL_REVIEW_SEARCH_BUDGET_PROFILE,
    INTERACTIVE_SEARCH_BUDGET_PROFILE,
    SEARCH_BUDGET_PROFILE_IDENTIFIERS,
    get_search_budget_profile,
)
from skat_ai.session_checkpoint_collection import (
    SessionCheckpointCollectionResultV1,
    collect_session_decision_checkpoint_v1,
)
from skat_ai.session_history import build_session_state_from_accepted_prefix_v1
from skat_ai.simulation import DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT

SESSION_CLI_CONTRACT_VERSION = 1
SESSION_CLI_COMMAND = "session"
SESSION_CLI_SUBCOMMANDS = (
    "new",
    "show",
    "apply",
    "undo",
    "correct",
    "checkpoint",
    "export-position",
    "export-historical",
    "analyze",
    "review",
    "finalize",
    "assistant",
)
SESSION_CLI_PERSISTENCE_POLICY = "load_operate_compare_and_swap_save"
SESSION_CLI_ANALYSIS_POLICY = "export_then_existing_application_once"
SESSION_CLI_AUTOMATIC_CHECKPOINT_POLICY = "collect_without_automatic_analysis"

_CREATE_INPUT_FIELDS = {
    "session_id",
    "capture_mode",
    "local_player_id",
    "players",
}
_PLAYER_FIELDS = {"player_id", "player_label", "seat"}
_CORRECTION_FIELDS = {
    "session_history_edit_version",
    "expected_revision",
    "target_revision",
    "replacement_command",
}


@dataclass(slots=True)
class _SessionContext:
    file_path: str
    document: session_api.SessionPersistenceDocumentV1

    @property
    def state(self) -> session_api.SessionStateV1:
        return self.document.state

    @property
    def decision_checkpoints(
        self,
    ) -> tuple[session_api.SessionDecisionCheckpointV1, ...]:
        return self.document.decision_checkpoints


def _invocation_command(invocation_style: str) -> str:
    commands = {
        "installed": "skat-ai",
        "module": "python -m skat_ai",
        "legacy": "python main.py",
    }
    try:
        return commands[invocation_style]
    except KeyError as error:
        raise ValueError(
            f"invocation_style must be one of {list(CLI_INVOCATION_STYLES)}."
        ) from error


def _positive_sample_count(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be an integer") from error
    if not 1 <= parsed <= MAX_SAMPLE_COUNT:
        raise argparse.ArgumentTypeError(
            f"must be from 1 through {MAX_SAMPLE_COUNT}"
        )
    return parsed


def _non_negative_integer(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be an integer") from error
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be non-negative")
    return parsed


def _add_common_options(
    parser: argparse.ArgumentParser,
    *,
    output_required: bool = False,
    include_provenance: bool = True,
) -> None:
    parser.add_argument(
        "--session",
        required=True,
        help="Read or write this explicit private Session JSON file.",
    )
    parser.add_argument(
        "--output",
        required=output_required,
        default=None,
        help="Write only the requested operation or Engine Result JSON here.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress successful human-readable output.",
    )
    if include_provenance:
        parser.add_argument(
            "--include-provenance",
            action="store_true",
            help="Include public-safe provenance in the requested JSON result.",
        )


def _add_position_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--samples",
        type=_positive_sample_count,
        default=DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT,
        help="Use this deterministic Position sample count.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="Use this deterministic Position random seed.",
    )
    parser.add_argument(
        "--opponent-strategy",
        choices=("basic", "random"),
        default="basic",
        help="Use the basic or random legacy opponent strategy.",
    )
    parser.add_argument(
        "--recommendation-method",
        choices=VALID_RECOMMENDATION_METHODS,
        default=None,
        help="Select an explicit Position recommendation method.",
    )
    parser.add_argument(
        "--search-budget-profile",
        choices=SEARCH_BUDGET_PROFILE_IDENTIFIERS,
        default=INTERACTIVE_SEARCH_BUDGET_PROFILE,
        help="Use this versioned bounded-Search budget when Search is requested.",
    )


def _add_historical_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--historical-decision-snapshots",
        action="store_true",
        help="Add information-safe Historical decision snapshots.",
    )
    parser.add_argument(
        "--historical-game-review",
        action="store_true",
        help="Run Immediate Historical decision review.",
    )
    parser.add_argument(
        "--historical-search-review",
        action="store_true",
        help="Run bounded-Search Historical decision review.",
    )
    parser.add_argument(
        "--historical-replay-coaching",
        action="store_true",
        help="Build the Historical Replay Coaching Report.",
    )
    parser.add_argument(
        "--search-seed",
        type=int,
        default=None,
        help="Use this explicit Historical Search base seed.",
    )
    parser.add_argument(
        "--search-budget-profile",
        choices=SEARCH_BUDGET_PROFILE_IDENTIFIERS,
        default=HISTORICAL_REVIEW_SEARCH_BUDGET_PROFILE,
        help="Use this versioned Historical Search budget.",
    )
    parser.add_argument(
        "--samples",
        type=_positive_sample_count,
        default=None,
        help="Use this Immediate Historical review sample count.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Use this Immediate Historical review base random seed.",
    )


def build_session_argument_parser(
    invocation_style: str = "installed",
) -> argparse.ArgumentParser:
    command = _invocation_command(invocation_style)
    parser = argparse.ArgumentParser(
        prog=f"{command} {SESSION_CLI_COMMAND}",
        description=(
            "Create, edit, inspect, export, analyze, and review one explicit "
            "private Skat Session file."
        ),
    )
    subparsers = parser.add_subparsers(
        dest="session_subcommand",
        required=True,
    )

    new = subparsers.add_parser("new", help="Create one new Session file.")
    _add_common_options(new)
    new.add_argument("--input", required=True, help="Read strict Session creation JSON.")

    show = subparsers.add_parser("show", help="Show privacy-safe Session status.")
    _add_common_options(show, include_provenance=False)

    apply = subparsers.add_parser("apply", help="Apply one strict Session Command.")
    _add_common_options(apply)
    apply.add_argument("--input", required=True, help="Read one Session Command JSON object.")
    _add_position_options(apply)

    undo = subparsers.add_parser("undo", help="Rewind to one strict-prefix revision.")
    _add_common_options(undo)
    undo.add_argument(
        "--target-revision",
        required=True,
        type=_non_negative_integer,
        help="Retain exactly this accepted revision prefix.",
    )
    _add_position_options(undo)

    correct = subparsers.add_parser("correct", help="Correct one accepted Command.")
    _add_common_options(correct)
    correct.add_argument(
        "--input",
        required=True,
        help="Read one strict Session Command Correction JSON object.",
    )
    _add_position_options(correct)

    checkpoint = subparsers.add_parser(
        "checkpoint",
        help="Collect or reuse the current exact Decision Checkpoint.",
    )
    _add_common_options(checkpoint)
    _add_position_options(checkpoint)

    export_position = subparsers.add_parser(
        "export-position",
        help="Export one information-safe Position Request without analysis.",
    )
    _add_common_options(export_position, output_required=True)
    _add_position_options(export_position)

    export_historical = subparsers.add_parser(
        "export-historical",
        help="Export one complete Historical Request without execution.",
    )
    _add_common_options(export_historical, output_required=True)

    analyze = subparsers.add_parser(
        "analyze",
        help="Analyze one Position-ready Session through the existing Application.",
    )
    _add_common_options(analyze, output_required=True)
    _add_position_options(analyze)

    review = subparsers.add_parser(
        "review",
        help="Review one observed frozen Decision Checkpoint.",
    )
    _add_common_options(review, output_required=True)
    review.add_argument(
        "--checkpoint-index",
        required=True,
        type=_non_negative_integer,
        help="Select one zero-based canonical Checkpoint index.",
    )

    finalize = subparsers.add_parser(
        "finalize",
        help="Execute one Historical-ready Session through the existing Application.",
    )
    _add_common_options(finalize, output_required=True)
    _add_historical_options(finalize)

    assistant = subparsers.add_parser(
        "assistant",
        help="Run the deterministic phase-aware interactive Session Assistant.",
    )
    assistant.add_argument(
        "--session",
        required=True,
        help="Read or write this explicit private Session JSON file.",
    )

    return parser


def parse_session_arguments(
    argv: list[str] | tuple[str, ...] | None = None,
    *,
    invocation_style: str = "installed",
) -> argparse.Namespace:
    return build_session_argument_parser(invocation_style).parse_args(argv)


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise SkatAIValidationError(
                f"Duplicate JSON object key {key!r} is not allowed.",
                path="",
            )
        result[key] = value
    return result


def _reject_non_finite_constant(value: str) -> object:
    raise SkatAIValidationError(
        f"Non-finite JSON number {value!r} is not allowed.",
        path="",
    )


def load_strict_json_object(file_path: str) -> dict[str, object]:
    path = Path(file_path)
    try:
        raw = path.read_bytes()
    except FileNotFoundError as error:
        raise FileNotFoundError(f"Input file not found: {file_path}") from error
    if raw.startswith(b"\xef\xbb\xbf"):
        raise SkatAIValidationError("Input JSON must use UTF-8 without a BOM.", path="")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise SkatAIValidationError("Input file is not valid UTF-8.", path="") from error
    try:
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_non_finite_constant,
        )
    except SkatAIValidationError:
        raise
    except json.JSONDecodeError as error:
        raise SkatAIValidationError(
            f"Input file is not valid JSON: {error.msg}.",
            path="",
        ) from error
    if not isinstance(value, dict):
        raise SkatAIValidationError("Input JSON root must be an object.", path="")
    return value


def _require_exact_fields(
    document: Mapping[str, object],
    expected: set[str],
    *,
    name: str,
) -> None:
    actual = set(document)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing:
        raise SkatAIValidationError(
            f"{name} is missing required fields: {missing}.",
            path="",
        )
    if unknown:
        raise SkatAIValidationError(
            f"{name} has unsupported fields: {unknown}.",
            path="",
        )


def _parse_create_input(
    document: Mapping[str, object],
) -> tuple[str, tuple[session_api.SessionPlayerV1, ...], str, str | None]:
    validate_session_create_document(document)
    _require_exact_fields(document, _CREATE_INPUT_FIELDS, name="Session creation input")
    raw_players = document["players"]
    if isinstance(raw_players, (str, bytes)) or not isinstance(raw_players, list):
        raise SkatAIValidationError("players must be an array.", path="/players")
    players: list[session_api.SessionPlayerV1] = []
    for index, raw_player in enumerate(raw_players):
        if not isinstance(raw_player, Mapping):
            raise SkatAIValidationError(
                "Each Session Player must be an object.",
                path=f"/players/{index}",
            )
        _require_exact_fields(raw_player, _PLAYER_FIELDS, name="Session Player")
        players.append(
            session_api.SessionPlayerV1(
                player_id=raw_player["player_id"],
                player_label=raw_player["player_label"],
                seat=raw_player["seat"],
            )
        )
    return (
        document["session_id"],
        tuple(players),
        document["capture_mode"],
        document["local_player_id"],
    )


def _parse_correction_input(
    document: Mapping[str, object],
) -> session_api.SessionCommandCorrectionV1:
    validate_session_correction_document(document)
    _require_exact_fields(
        document,
        _CORRECTION_FIELDS,
        name="Session Command Correction",
    )
    replacement = document["replacement_command"]
    if not isinstance(replacement, Mapping):
        raise SkatAIValidationError(
            "replacement_command must be an object.",
            path="/replacement_command",
        )
    return session_api.SessionCommandCorrectionV1(
        session_history_edit_version=document["session_history_edit_version"],
        expected_revision=document["expected_revision"],
        target_revision=document["target_revision"],
        replacement_command=session_api.parse_session_command(replacement),
    )


def _session_options(include_provenance: bool) -> session_api.SessionApiOptionsV1:
    return session_api.SessionApiOptionsV1(include_provenance=include_provenance)


def _position_export_options(
    args: argparse.Namespace,
) -> session_api.SessionPositionExportOptionsV1:
    bounded_search_settings = None
    if args.recommendation_method in SEARCH_RECOMMENDATION_METHODS:
        bounded_search_settings = build_serializable_bounded_search_settings(
            RecommendationMethodConfiguration(
                explicitly_supplied=True,
                requested_method=args.recommendation_method,
                search_random_seed=args.seed,
                requested_search_budget=get_search_budget_profile(
                    args.search_budget_profile
                ),
            )
        )
    return session_api.SessionPositionExportOptionsV1(
        sample_count=args.samples,
        random_seed=args.seed,
        use_basic_opponent_strategy=args.opponent_strategy == "basic",
        recommendation_method=args.recommendation_method,
        bounded_search_settings=bounded_search_settings,
    )


def _load_context(file_path: str) -> tuple[_SessionContext, session_files.SessionFileApiResultV1]:
    loaded = session_files.load_session_file(file_path)
    return (
        _SessionContext(file_path=file_path, document=loaded.value.document),
        loaded,
    )


def _save_context(
    context: _SessionContext,
    *,
    state: session_api.SessionStateV1,
    decision_checkpoints: tuple[session_api.SessionDecisionCheckpointV1, ...],
) -> session_files.SessionPersistenceWriteResultV1:
    expected_fingerprint = context.document.content_fingerprint
    persistence = session_api.build_session_persistence_document(
        state,
        decision_checkpoints=decision_checkpoints,
    ).value
    saved = session_files.save_session_file(
        context.file_path,
        persistence,
        expected_content_fingerprint=expected_fingerprint,
    ).value
    if saved.status != "conflict":
        context.document = persistence
    return saved


def _collect_current_checkpoint(
    *,
    state: session_api.SessionStateV1,
    export_options: session_api.SessionPositionExportOptionsV1,
    decision_checkpoints: tuple[session_api.SessionDecisionCheckpointV1, ...],
) -> SessionCheckpointCollectionResultV1:
    return collect_session_decision_checkpoint_v1(
        state=state,
        export_options=export_options,
        decision_checkpoints=decision_checkpoints,
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
        source_collection = _collect_current_checkpoint(
            state=source_state,
            export_options=export_options,
            decision_checkpoints=checkpoints,
        )
        checkpoints = source_collection.decision_checkpoints
        collections.append(source_collection)
    if resulting_state.validation.position_export.status == "available":
        resulting_collection = _collect_current_checkpoint(
            state=resulting_state,
            export_options=export_options,
            decision_checkpoints=checkpoints,
        )
        checkpoints = resulting_collection.decision_checkpoints
        collections.append(resulting_collection)
    return checkpoints, tuple(collections)


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
    checkpoints, collections = _collect_mutation_checkpoints(
        source_state=context.state,
        resulting_state=resulting_state,
        source_play_command=source_play_command,
        export_options=export_options,
        decision_checkpoints=context.decision_checkpoints,
        source_collection=source_collection,
    )
    saved = _save_context(
        context,
        state=resulting_state,
        decision_checkpoints=checkpoints,
    )
    return saved, collections


def _collect_source_play_checkpoint(
    context: _SessionContext,
    command: session_api.SessionCommandV1,
    export_options: session_api.SessionPositionExportOptionsV1,
) -> SessionCheckpointCollectionResultV1 | None:
    if (
        isinstance(command, session_api.RecordSessionPlayCommandV1)
        and command.player_id == context.state.local_player_id
        and context.state.validation.position_export.status == "available"
    ):
        return _collect_current_checkpoint(
            state=context.state,
            export_options=export_options,
            decision_checkpoints=context.decision_checkpoints,
        )
    return None


def _collect_correction_source_checkpoint(
    context: _SessionContext,
    correction: session_api.SessionCommandCorrectionV1,
    export_options: session_api.SessionPositionExportOptionsV1,
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
    return _collect_current_checkpoint(
        state=prefix,
        export_options=export_options,
        decision_checkpoints=context.decision_checkpoints,
    )


def _write_output(output_path: str, document: dict[str, Any]) -> None:
    write_analysis_result_to_json(output_path=output_path, result=document)


def _print_diagnostics(diagnostics: tuple[object, ...]) -> None:
    for diagnostic in diagnostics:
        print(f"Diagnostic {diagnostic.code}: {diagnostic.message}")


def _print_session_summary(
    state: session_api.SessionStateV1,
    checkpoints: tuple[session_api.SessionDecisionCheckpointV1, ...],
) -> None:
    print("Session summary")
    print("Session ID:", state.session_id)
    print("Revision:", state.revision)
    print("Capture mode:", state.capture_mode)
    print("Phase:", state.phase)
    print("Position readiness:", state.validation.position_export.status)
    print("Historical readiness:", state.validation.historical_export.status)
    print("Players:", ", ".join(f"{player.player_id} ({player.seat})" for player in state.players))
    print("Checkpoint count:", len(checkpoints))
    for index, checkpoint in enumerate(checkpoints):
        observation = session_api.observe_session_decision_checkpoint(
            state=state,
            checkpoint=checkpoint,
        ).value
        line = (
            f"Checkpoint {index}: revision {checkpoint.source_revision}, "
            f"decision {checkpoint.decision_index}, "
            f"lineage {observation.lineage.relationship}, "
            f"observation {observation.status}"
        )
        if observation.actual_card is not None:
            line += f", actual card {observation.actual_card}"
        print(line)


def _print_save_conflict() -> None:
    print(
        "Error: Session file changed since it was loaded; no changes were saved.",
        file=sys.stderr,
    )


def _print_output_confirmation(output_path: str) -> None:
    print("Output file written:", output_path)


def _privacy_safe_position_result(result: dict[str, Any]) -> dict[str, Any]:
    safe = copy.deepcopy(result)
    position = safe.get("position")
    if isinstance(position, dict):
        hand = position.get("hand")
        if isinstance(hand, list):
            position["hand"] = f"[{len(hand)} private cards]"
        skat = position.get("skat")
        if isinstance(skat, list):
            position["skat"] = f"[{len(skat)} private cards]"
    legal_cards = safe.get("legal_cards")
    if isinstance(legal_cards, list):
        safe["legal_cards"] = f"[{len(legal_cards)} private legal cards]"
    if isinstance(safe.get("analysis_report"), list):
        safe["analysis_report"] = []
    return safe


def _execute_position_request(
    request: object,
    *,
    input_reference: str,
    include_provenance: bool,
) -> dict[str, Any]:
    result, _artifacts = execute_legacy_application(
        request.to_dict()["document"],
        input_reference=input_reference,
        options=ApplicationExecutionOptions(
            position_analysis=PositionAnalysisApplicationOptions()
        ),
        include_provenance=include_provenance,
    )
    return result


def _session_input_reference(context: _SessionContext) -> str:
    return f"session:{context.state.session_id}:revision:{context.state.revision}"


def _historical_application_options(args: argparse.Namespace) -> ApplicationExecutionOptions:
    return ApplicationExecutionOptions(
        historical_game=HistoricalGameApplicationOptions(
            decision_snapshots=args.historical_decision_snapshots,
            immediate_review=args.historical_game_review,
            search_review=args.historical_search_review,
            replay_coaching=args.historical_replay_coaching,
            search_seed=args.search_seed,
            search_budget_profile=args.search_budget_profile,
            immediate_sample_count=args.samples,
            immediate_base_random_seed=args.seed,
        )
    )


def _execute_historical_request(
    request: object,
    *,
    input_reference: str,
    include_provenance: bool,
    options: ApplicationExecutionOptions,
) -> dict[str, Any]:
    result, _artifacts = execute_legacy_application(
        request.to_dict()["document"],
        input_reference=input_reference,
        options=options,
        include_provenance=include_provenance,
    )
    return result


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
    session_id, players, capture_mode, local_player_id = _parse_create_input(document)
    created = session_api.create_session(
        session_id=session_id,
        players=players,
        capture_mode=capture_mode,
        local_player_id=local_player_id,
        options=_session_options(include_provenance),
    )
    persistence = session_api.build_session_persistence_document(created.value).value
    saved = session_files.save_session_file(
        file_path,
        persistence,
        expected_content_fingerprint=None,
    ).value
    context = None
    if saved.status != "conflict":
        context = _SessionContext(file_path=file_path, document=persistence)
    return created, context, saved


def _run_new(args: argparse.Namespace) -> int:
    created, context, saved = _create_context(
        args.session,
        load_strict_json_object(args.input),
        include_provenance=args.include_provenance,
    )
    if saved.status == "conflict":
        _print_save_conflict()
        return CLI_EXIT_CODE_FAILURE
    if args.output is not None:
        _write_output(args.output, session_api.serialize_session_result(created))
    if not args.quiet:
        print("Session creation status:", saved.status)
        _print_session_summary(context.state, context.decision_checkpoints)
        if args.output is not None:
            _print_output_confirmation(args.output)
    return CLI_EXIT_CODE_SUCCESS


def _run_show(args: argparse.Namespace) -> int:
    context, loaded = _load_context(args.session)
    if args.output is not None:
        _write_output(
            args.output,
            session_files.serialize_session_file_result(loaded),
        )
    if not args.quiet:
        _print_session_summary(context.state, context.decision_checkpoints)
        if args.output is not None:
            _print_output_confirmation(args.output)
    return CLI_EXIT_CODE_SUCCESS


def _finish_mutation(
    args: argparse.Namespace,
    *,
    context: _SessionContext,
    result: session_api.SessionApiResultV1,
    state_changed: bool,
    source_play_command: session_api.SessionCommandV1 | None,
    source_collection: SessionCheckpointCollectionResultV1 | None = None,
) -> int:
    saved = None
    if state_changed:
        saved, _collections = _persist_mutation(
            context,
            resulting_state=result.value.state,
            source_play_command=source_play_command,
            export_options=_position_export_options(args),
            source_collection=source_collection,
        )
        if saved.status == "conflict":
            _print_save_conflict()
            return CLI_EXIT_CODE_FAILURE
    if args.output is not None:
        _write_output(args.output, session_api.serialize_session_result(result))
    if not args.quiet:
        print("Session operation:", result.operation)
        print("Operation status:", result.value.status)
        _print_diagnostics(result.value.diagnostics)
        _print_session_summary(context.state, context.decision_checkpoints)
        if saved is not None:
            print("Persistence status:", saved.status)
        if args.output is not None:
            _print_output_confirmation(args.output)
    return CLI_EXIT_CODE_SUCCESS


def _run_apply(args: argparse.Namespace) -> int:
    context, _loaded = _load_context(args.session)
    command = session_api.parse_session_command(load_strict_json_object(args.input))
    source_collection = _collect_source_play_checkpoint(
        context,
        command,
        _position_export_options(args),
    )
    result = session_api.apply_session_command(
        context.state,
        command,
        options=_session_options(args.include_provenance),
    )
    return _finish_mutation(
        args,
        context=context,
        result=result,
        state_changed=result.value.status == "applied",
        source_play_command=command,
        source_collection=source_collection,
    )


def _run_undo(args: argparse.Namespace) -> int:
    context, _loaded = _load_context(args.session)
    result = session_api.rewind_session(
        context.state,
        expected_revision=context.state.revision,
        target_revision=args.target_revision,
        options=_session_options(args.include_provenance),
    )
    return _finish_mutation(
        args,
        context=context,
        result=result,
        state_changed=result.value.status == "applied",
        source_play_command=None,
    )


def _run_correct(args: argparse.Namespace) -> int:
    context, _loaded = _load_context(args.session)
    correction = _parse_correction_input(load_strict_json_object(args.input))
    source_collection = _collect_correction_source_checkpoint(
        context,
        correction,
        _position_export_options(args),
    )
    result = session_api.correct_session_command(
        context.state,
        correction,
        options=_session_options(args.include_provenance),
    )
    return _finish_mutation(
        args,
        context=context,
        result=result,
        state_changed=result.value.status in {"applied", "partial"},
        source_play_command=None,
        source_collection=source_collection,
    )


def _checkpoint_result(
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
        options=_session_options(include_provenance),
        source_state=state,
        retained_inputs={
            "state": state,
            "position_export": position_export,
            "export_options": export_options,
        },
    )


def _run_checkpoint(args: argparse.Namespace) -> int:
    context, _loaded = _load_context(args.session)
    export_options = _position_export_options(args)
    collection = _collect_current_checkpoint(
        state=context.state,
        export_options=export_options,
        decision_checkpoints=context.decision_checkpoints,
    )
    saved = None
    if collection.status == "collected":
        saved = _save_context(
            context,
            state=context.state,
            decision_checkpoints=collection.decision_checkpoints,
        )
        if saved.status == "conflict":
            _print_save_conflict()
            return CLI_EXIT_CODE_FAILURE
    if args.output is not None:
        if collection.checkpoint is None:
            output_result = session_api.export_session_position_request(
                context.state,
                export_options,
                options=_session_options(args.include_provenance),
            )
        else:
            output_result = _checkpoint_result(
                state=context.state,
                checkpoint=collection.checkpoint,
                include_provenance=args.include_provenance,
                export_options=export_options,
            )
        _write_output(args.output, session_api.serialize_session_result(output_result))
    if not args.quiet:
        print("Checkpoint status:", collection.status)
        if collection.checkpoint is not None:
            print("Checkpoint revision:", collection.checkpoint.source_revision)
            print("Decision index:", collection.checkpoint.decision_index)
        _print_diagnostics(collection.diagnostics)
        if saved is not None:
            print("Persistence status:", saved.status)
        if args.output is not None:
            _print_output_confirmation(args.output)
    return CLI_EXIT_CODE_SUCCESS


def _run_export_position(args: argparse.Namespace) -> int:
    context, _loaded = _load_context(args.session)
    export_options = _position_export_options(args)
    exported = session_api.export_session_position_request(
        context.state,
        export_options,
        options=_session_options(args.include_provenance),
    )
    collection = _collect_current_checkpoint(
        state=context.state,
        export_options=export_options,
        decision_checkpoints=context.decision_checkpoints,
    )
    saved = None
    if exported.value.status == "available":
        if (
            collection.checkpoint is None
            or collection.checkpoint.request != exported.value.request
        ):
            raise SkatAIInvariantError(
                "Position export and collected Checkpoint disagree."
            )
        if collection.status == "collected":
            saved = _save_context(
                context,
                state=context.state,
                decision_checkpoints=collection.decision_checkpoints,
            )
            if saved.status == "conflict":
                _print_save_conflict()
                return CLI_EXIT_CODE_FAILURE
    _write_output(args.output, session_api.serialize_session_result(exported))
    if not args.quiet:
        print("Position export status:", exported.value.status)
        _print_diagnostics(exported.value.diagnostics)
        if saved is not None:
            print("Checkpoint persistence status:", saved.status)
        _print_output_confirmation(args.output)
    return CLI_EXIT_CODE_SUCCESS


def _run_export_historical(args: argparse.Namespace) -> int:
    context, _loaded = _load_context(args.session)
    exported = session_api.export_session_historical_request(
        context.state,
        options=_session_options(args.include_provenance),
    )
    _write_output(args.output, session_api.serialize_session_result(exported))
    if not args.quiet:
        print("Historical export status:", exported.value.status)
        _print_diagnostics(exported.value.diagnostics)
        _print_output_confirmation(args.output)
    return CLI_EXIT_CODE_SUCCESS


def _collect_for_analysis(
    context: _SessionContext,
    export_options: session_api.SessionPositionExportOptionsV1,
) -> tuple[
    SessionCheckpointCollectionResultV1,
    session_files.SessionPersistenceWriteResultV1 | None,
]:
    collection = _collect_current_checkpoint(
        state=context.state,
        export_options=export_options,
        decision_checkpoints=context.decision_checkpoints,
    )
    saved = None
    if collection.status == "collected":
        saved = _save_context(
            context,
            state=context.state,
            decision_checkpoints=collection.decision_checkpoints,
        )
    return collection, saved


def _run_analyze(args: argparse.Namespace) -> int:
    context, _loaded = _load_context(args.session)
    export_options = _position_export_options(args)
    if context.state.validation.position_export.status == "unavailable":
        unavailable = session_api.export_session_position_request(
            context.state,
            export_options,
            options=_session_options(args.include_provenance),
        )
        _write_output(args.output, session_api.serialize_session_result(unavailable))
        if not args.quiet:
            print("Position analysis status: unavailable")
            _print_diagnostics(unavailable.value.diagnostics)
            _print_output_confirmation(args.output)
        return CLI_EXIT_CODE_SUCCESS

    collection, saved = _collect_for_analysis(context, export_options)
    if saved is not None and saved.status == "conflict":
        _print_save_conflict()
        return CLI_EXIT_CODE_FAILURE
    if collection.checkpoint is None:
        raise SkatAIInvariantError(
            "A Position-ready Session did not produce a Decision Checkpoint."
        )

    result = _execute_position_request(
        collection.checkpoint.request,
        input_reference=_session_input_reference(context),
        include_provenance=args.include_provenance,
    )
    _write_output(args.output, result)
    if not args.quiet:
        print(
            "Session checkpoint:",
            f"revision {collection.checkpoint.source_revision}, "
            f"decision {collection.checkpoint.decision_index}, {collection.status}",
        )
        print_analysis_result(_privacy_safe_position_result(result))
        _print_output_confirmation(args.output)
        print_field_provenance_summary(result)
    return CLI_EXIT_CODE_SUCCESS


def _selected_checkpoint(
    context: _SessionContext,
    checkpoint_index: int,
) -> session_api.SessionDecisionCheckpointV1:
    if checkpoint_index >= len(context.decision_checkpoints):
        raise SkatAICliUsageError(
            "--checkpoint-index must identify an existing canonical Checkpoint."
        )
    return context.decision_checkpoints[checkpoint_index]


def _run_review(args: argparse.Namespace) -> int:
    context, _loaded = _load_context(args.session)
    checkpoint = _selected_checkpoint(context, args.checkpoint_index)
    exported = session_api.export_session_checkpoint_review_request(
        state=context.state,
        checkpoint=checkpoint,
        options=_session_options(args.include_provenance),
    )
    if exported.value.status != "available":
        _write_output(args.output, session_api.serialize_session_result(exported))
        if not args.quiet:
            print("Checkpoint review status:", exported.value.status)
            print("Observation status:", exported.value.observation.status)
            _print_diagnostics(exported.value.diagnostics)
            _print_output_confirmation(args.output)
        return CLI_EXIT_CODE_SUCCESS

    result = _execute_position_request(
        exported.value.request,
        input_reference=_session_input_reference(context),
        include_provenance=args.include_provenance,
    )
    _write_output(args.output, result)
    if not args.quiet:
        print("Checkpoint review status: available")
        print("Checkpoint index:", args.checkpoint_index)
        print("Observed actual card:", exported.value.observation.actual_card)
        print_analysis_result(_privacy_safe_position_result(result))
        _print_output_confirmation(args.output)
        print_field_provenance_summary(result)
    return CLI_EXIT_CODE_SUCCESS


def _run_finalize(args: argparse.Namespace) -> int:
    context, _loaded = _load_context(args.session)
    exported = session_api.export_session_historical_request(
        context.state,
        options=_session_options(args.include_provenance),
    )
    if exported.value.status != "available":
        _write_output(args.output, session_api.serialize_session_result(exported))
        if not args.quiet:
            print("Historical finalize status: unavailable")
            _print_diagnostics(exported.value.diagnostics)
            _print_output_confirmation(args.output)
        return CLI_EXIT_CODE_SUCCESS

    result = _execute_historical_request(
        exported.value.request,
        input_reference=_session_input_reference(context),
        include_provenance=args.include_provenance,
        options=_historical_application_options(args),
    )
    _write_output(args.output, result)
    if not args.quiet:
        print_historical_game_result(result)
        summary = result["historical_game_summary"]
        if args.historical_search_review:
            print_historical_search_review_result(
                summary["historical_search_review_summary"]
            )
        if args.historical_replay_coaching:
            print_historical_replay_coaching_result(
                summary["historical_replay_coaching_summary"]
            )
        _print_output_confirmation(args.output)
        print_field_provenance_summary(result)
    return CLI_EXIT_CODE_SUCCESS


def _run_assistant(args: argparse.Namespace) -> int:
    from skat_ai.cli.session_assistant import run_session_assistant

    return run_session_assistant(args.session)


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
