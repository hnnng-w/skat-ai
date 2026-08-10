from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Mapping
from pathlib import Path

import skat_ai.api.v1.session as session_api
from skat_ai.application.contracts import (
    ApplicationExecutionOptions,
    HistoricalGameApplicationOptions,
)
from skat_ai.cli import session as session_cli
from skat_ai.errors import CLI_EXIT_CODE_FAILURE, CLI_EXIT_CODE_SUCCESS, SkatAIError
from skat_ai.session_commands import SESSION_COMMAND_ALLOWED_PHASES

InputFunction = Callable[[str], str]
OutputFunction = Callable[[str], None]

_ACTION_ORDER = (
    "metadata",
    "dealt-card",
    "skat",
    "declarer",
    "declaration",
    "discard",
    "play",
    "public-hand",
    "event",
    "end",
    "promote",
    "undo",
    "correct",
    "checkpoint",
    "analyze",
    "review",
    "finalize",
    "quit",
)

_ACTION_COMMAND_KIND = {
    "metadata": "set_game_metadata",
    "dealt-card": "record_dealt_card",
    "skat": "record_dealt_card",
    "declarer": "set_declarer",
    "declaration": "set_declaration",
    "discard": "record_discard",
    "play": "record_play",
    "public-hand": "set_public_hand",
    "event": "set_game_event",
    "end": "set_game_end",
    "promote": "promote_to_retrospective",
}


def _emit(output_fn: OutputFunction, *values: object) -> None:
    output_fn(" ".join(str(value) for value in values))


def _strict_json_object(text: str, *, name: str) -> dict[str, object]:
    def reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"{name} contains duplicate key {key!r}.")
            result[key] = value
        return result

    def reject_constant(value: str) -> object:
        raise ValueError(f"{name} contains non-finite number {value!r}.")

    try:
        value = json.loads(
            text,
            object_pairs_hook=reject_duplicates,
            parse_constant=reject_constant,
        )
    except json.JSONDecodeError as error:
        raise ValueError(f"{name} is not valid JSON: {error.msg}.") from error
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a JSON object.")
    return value


def _strict_json_array(text: str, *, name: str) -> list[object]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError(f"{name} is not valid JSON: {error.msg}.") from error
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a JSON array.")
    return value


def _prompt_creation(input_fn: InputFunction) -> dict[str, object]:
    session_id = input_fn("Session ID: ")
    capture_mode = input_fn("Capture mode (live/retrospective): ")
    local_player_id = input_fn(
        "Local player ID (required for live; blank for retrospective): "
    )
    players = []
    for seat in ("forehand", "middlehand", "rearhand"):
        player_id = input_fn(f"{seat.title()} player ID: ")
        player_label = input_fn(f"{seat.title()} player label (optional): ")
        players.append(
            {
                "player_id": player_id,
                "player_label": player_label or None,
                "seat": seat,
            }
        )
    return {
        "session_id": session_id,
        "capture_mode": capture_mode,
        "local_player_id": local_player_id or None,
        "players": players,
    }


def _available_actions(context: session_cli._SessionContext) -> tuple[str, ...]:
    state = context.state
    available = []
    for action in _ACTION_ORDER:
        command_kind = _ACTION_COMMAND_KIND.get(action)
        if command_kind is not None:
            if state.phase not in SESSION_COMMAND_ALLOWED_PHASES[command_kind]:
                continue
            if action == "promote" and state.capture_mode != "live":
                continue
        elif action in {"undo", "correct"} and state.revision == 0:
            continue
        elif action in {"checkpoint", "analyze"} and (
            state.validation.position_export.status != "available"
        ):
            continue
        elif action == "review" and not context.decision_checkpoints:
            continue
        elif action == "finalize" and (
            state.validation.historical_export.status != "available"
        ):
            continue
        available.append(action)
    return tuple(available)


def _show_status(
    context: session_cli._SessionContext,
    output_fn: OutputFunction,
) -> None:
    state = context.state
    _emit(
        output_fn,
        f"Session {state.session_id}: revision {state.revision},",
        f"phase {state.phase}, mode {state.capture_mode}.",
    )
    _emit(
        output_fn,
        f"Position {state.validation.position_export.status};",
        f"Historical {state.validation.historical_export.status};",
        f"Checkpoints {len(context.decision_checkpoints)}.",
    )
    for index, checkpoint in enumerate(context.decision_checkpoints):
        observation = session_api.observe_session_decision_checkpoint(
            state=state,
            checkpoint=checkpoint,
        ).value
        text = (
            f"Checkpoint {index}: revision {checkpoint.source_revision}, "
            f"decision {checkpoint.decision_index}, {observation.lineage.relationship}, "
            f"{observation.status}"
        )
        if observation.actual_card is not None:
            text += f", actual card {observation.actual_card}"
        _emit(output_fn, text + ".")


def _build_command_document(
    action: str,
    *,
    revision: int,
    input_fn: InputFunction,
) -> dict[str, object]:
    header: dict[str, object] = {
        "command_version": 1,
        "kind": _ACTION_COMMAND_KIND[action],
        "expected_revision": revision,
    }
    if action == "metadata":
        return {
            **header,
            "game_id": input_fn("Game ID (optional): ") or None,
            "played_at": input_fn("Played-at RFC 3339 instant (optional): ") or None,
        }
    if action == "dealt-card":
        return {
            **header,
            "destination": "player_hand",
            "player_id": input_fn("Player ID: "),
            "card": input_fn("Card: "),
        }
    if action == "skat":
        return {
            **header,
            "destination": "skat",
            "player_id": None,
            "card": input_fn("Skat card: "),
        }
    if action == "declarer":
        return {
            **header,
            "declarer_player_id": input_fn("Declarer player ID: "),
        }
    if action == "declaration":
        return {
            **header,
            "declaration": _strict_json_object(
                input_fn("Declaration JSON object: "),
                name="Declaration",
            ),
        }
    if action == "discard":
        return {**header, "card": input_fn("Discard card: ")}
    if action == "play":
        return {
            **header,
            "player_id": input_fn("Acting player ID: "),
            "card": input_fn("Played card: "),
        }
    if action == "public-hand":
        return {
            **header,
            "source": "declared_ouvert",
            "player_id": input_fn("Public-hand player ID: "),
            "cards": _strict_json_array(
                input_fn("Public cards JSON array: "),
                name="Public cards",
            ),
        }
    if action == "event":
        return {
            **header,
            "event": _strict_json_object(
                input_fn("Continuation event JSON object: "),
                name="Continuation event",
            ),
        }
    if action == "end":
        end = _strict_json_object(
            input_fn(
                "Game end JSON object with game_end_reason and game_end: "
            ),
            name="Game end",
        )
        if set(end) != {"game_end_reason", "game_end"}:
            raise ValueError(
                "Game end JSON must contain exactly game_end_reason and game_end."
            )
        return {
            **header,
            "game_end_reason": end["game_end_reason"],
            "game_end": end["game_end"],
        }
    if action == "promote":
        return header
    raise ValueError(f"Unsupported command action {action!r}.")


def _default_position_args() -> argparse.Namespace:
    return argparse.Namespace(
        samples=session_cli.DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT,
        seed=0,
        opponent_strategy="basic",
        recommendation_method=None,
        search_budget_profile=session_cli.INTERACTIVE_SEARCH_BUDGET_PROFILE,
    )


def _apply_command(
    context: session_cli._SessionContext,
    document: Mapping[str, object],
    *,
    output_fn: OutputFunction,
) -> bool:
    command = session_api.parse_session_command(document)
    export_options = session_cli._position_export_options(_default_position_args())
    source_collection = session_cli._collect_source_play_checkpoint(
        context,
        command,
        export_options,
    )
    result = session_api.apply_session_command(context.state, command)
    _emit(output_fn, "Apply status:", result.value.status)
    for diagnostic in result.value.diagnostics:
        _emit(output_fn, f"Diagnostic {diagnostic.code}: {diagnostic.message}")
    if result.value.status != "applied":
        return True
    saved, _collections = session_cli._persist_mutation(
        context,
        resulting_state=result.value.state,
        source_play_command=command,
        export_options=export_options,
        source_collection=source_collection,
    )
    _emit(output_fn, "Persistence status:", saved.status)
    return saved.status != "conflict"


def _undo(
    context: session_cli._SessionContext,
    *,
    input_fn: InputFunction,
    output_fn: OutputFunction,
) -> bool:
    target_text = input_fn("Target revision: ")
    try:
        target_revision = int(target_text)
    except ValueError as error:
        raise ValueError("Target revision must be an integer.") from error
    result = session_api.rewind_session(
        context.state,
        expected_revision=context.state.revision,
        target_revision=target_revision,
    )
    _emit(output_fn, "Undo status:", result.value.status)
    if result.value.status != "applied":
        return True
    saved, _collections = session_cli._persist_mutation(
        context,
        resulting_state=result.value.state,
        source_play_command=None,
        export_options=session_cli._position_export_options(
            _default_position_args()
        ),
    )
    _emit(output_fn, "Persistence status:", saved.status)
    return saved.status != "conflict"


def _correct(
    context: session_cli._SessionContext,
    *,
    input_fn: InputFunction,
    output_fn: OutputFunction,
) -> bool:
    document = _strict_json_object(
        input_fn("Session Command Correction JSON object: "),
        name="Session Command Correction",
    )
    correction = session_cli._parse_correction_input(document)
    export_options = session_cli._position_export_options(_default_position_args())
    source_collection = session_cli._collect_correction_source_checkpoint(
        context,
        correction,
        export_options,
    )
    result = session_api.correct_session_command(context.state, correction)
    _emit(output_fn, "Correction status:", result.value.status)
    _emit(
        output_fn,
        "Replayed suffix records:",
        len(result.value.replayed_suffix_records),
    )
    _emit(
        output_fn,
        "Discarded suffix records:",
        len(result.value.discarded_suffix_records),
    )
    if result.value.status not in {"applied", "partial"}:
        return True
    saved, _collections = session_cli._persist_mutation(
        context,
        resulting_state=result.value.state,
        source_play_command=None,
        export_options=export_options,
        source_collection=source_collection,
    )
    _emit(output_fn, "Persistence status:", saved.status)
    return saved.status != "conflict"


def _checkpoint_or_analyze(
    context: session_cli._SessionContext,
    *,
    analyze: bool,
    output_fn: OutputFunction,
) -> bool:
    export_options = session_cli._position_export_options(_default_position_args())
    collection, saved = session_cli._collect_for_analysis(context, export_options)
    if saved is not None:
        _emit(output_fn, "Persistence status:", saved.status)
        if saved.status == "conflict":
            return False
    _emit(output_fn, "Checkpoint status:", collection.status)
    if not analyze or collection.checkpoint is None:
        return True
    result = session_cli._execute_position_request(
        collection.checkpoint.request,
        input_reference=session_cli._session_input_reference(context),
        include_provenance=False,
    )
    recommendation = result.get("recommendation", {})
    _emit(output_fn, "Position analysis completed.")
    if isinstance(recommendation, dict):
        _emit(output_fn, "Recommended card:", recommendation.get("card"))
    return True


def _review(
    context: session_cli._SessionContext,
    *,
    input_fn: InputFunction,
    output_fn: OutputFunction,
) -> None:
    index_text = input_fn("Checkpoint index: ")
    try:
        index = int(index_text)
    except ValueError as error:
        raise ValueError("Checkpoint index must be an integer.") from error
    if not 0 <= index < len(context.decision_checkpoints):
        raise ValueError("Checkpoint index does not exist.")
    checkpoint = context.decision_checkpoints[index]
    exported = session_api.export_session_checkpoint_review_request(
        state=context.state,
        checkpoint=checkpoint,
    )
    _emit(output_fn, "Checkpoint review status:", exported.value.status)
    _emit(output_fn, "Observation status:", exported.value.observation.status)
    if exported.value.observation.actual_card is not None:
        _emit(
            output_fn,
            "Observed actual card:",
            exported.value.observation.actual_card,
        )
    if exported.value.status != "available":
        return
    result = session_cli._execute_position_request(
        exported.value.request,
        input_reference=session_cli._session_input_reference(context),
        include_provenance=False,
    )
    summary = result.get("post_game_review_summary", {})
    if isinstance(summary, dict):
        _emit(output_fn, "Decision quality:", summary.get("decision_quality"))


def _finalize(
    context: session_cli._SessionContext,
    *,
    output_fn: OutputFunction,
) -> None:
    exported = session_api.export_session_historical_request(context.state)
    _emit(output_fn, "Historical export status:", exported.value.status)
    if exported.value.status != "available":
        return
    result = session_cli._execute_historical_request(
        exported.value.request,
        input_reference=session_cli._session_input_reference(context),
        include_provenance=False,
        options=ApplicationExecutionOptions(
            historical_game=HistoricalGameApplicationOptions()
        ),
    )
    summary = result.get("historical_game_summary", {})
    _emit(output_fn, "Historical finalize completed.")
    if isinstance(summary, dict):
        _emit(output_fn, "Winner:", summary.get("winner"))


def run_session_assistant(
    session_path: str,
    *,
    input_fn: InputFunction = input,
    output_fn: OutputFunction = print,
) -> int:
    """Runs one deterministic interactive Session loop with injectable I/O."""
    try:
        if Path(session_path).exists():
            context, _loaded = session_cli._load_context(session_path)
            _emit(output_fn, "Session resumed.")
        else:
            _emit(output_fn, "Session file does not exist; enter explicit creation values.")
            created, context, saved = session_cli._create_context(
                session_path,
                _prompt_creation(input_fn),
                include_provenance=False,
            )
            del created
            _emit(output_fn, "Session creation status:", saved.status)
            if saved.status == "conflict" or context is None:
                return CLI_EXIT_CODE_FAILURE

        while True:
            _show_status(context, output_fn)
            available = _available_actions(context)
            _emit(output_fn, "Available actions:", ", ".join(available))
            action = input_fn("Action: ").strip().lower()
            if action == "quit":
                _emit(output_fn, "Assistant closed.")
                return CLI_EXIT_CODE_SUCCESS
            if action not in available:
                _emit(output_fn, f"Action {action!r} is unavailable in this phase.")
                continue

            try:
                if action in _ACTION_COMMAND_KIND:
                    if not _apply_command(
                        context,
                        _build_command_document(
                            action,
                            revision=context.state.revision,
                            input_fn=input_fn,
                        ),
                        output_fn=output_fn,
                    ):
                        return CLI_EXIT_CODE_FAILURE
                elif action == "undo":
                    if not _undo(context, input_fn=input_fn, output_fn=output_fn):
                        return CLI_EXIT_CODE_FAILURE
                elif action == "correct":
                    if not _correct(context, input_fn=input_fn, output_fn=output_fn):
                        return CLI_EXIT_CODE_FAILURE
                elif action == "checkpoint":
                    if not _checkpoint_or_analyze(
                        context,
                        analyze=False,
                        output_fn=output_fn,
                    ):
                        return CLI_EXIT_CODE_FAILURE
                elif action == "analyze":
                    if not _checkpoint_or_analyze(
                        context,
                        analyze=True,
                        output_fn=output_fn,
                    ):
                        return CLI_EXIT_CODE_FAILURE
                elif action == "review":
                    _review(context, input_fn=input_fn, output_fn=output_fn)
                elif action == "finalize":
                    _finalize(context, output_fn=output_fn)
            except (SkatAIError, TypeError, ValueError, OSError) as error:
                _emit(output_fn, f"Error: {error}")
    except EOFError:
        _emit(output_fn, "Assistant closed at end of input.")
        return CLI_EXIT_CODE_SUCCESS
    except (SkatAIError, TypeError, ValueError, OSError) as error:
        _emit(output_fn, f"Error: {error}")
        return CLI_EXIT_CODE_FAILURE
