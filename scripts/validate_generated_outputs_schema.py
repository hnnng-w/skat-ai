from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

import skatmind.api.v1.session as session_api
import skatmind.api.v1.session.files as session_files
from skatmind.cli.session import run_session_cli
from skatmind.field_provenance import parse_json_pointer, resolve_json_pointer
from skatmind.field_provenance_coverage import enumerate_json_leaf_paths

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = PROJECT_ROOT / "schemas" / "output.schema.json"
INPUT_SCHEMA_PATH = PROJECT_ROOT / "schemas" / "input.schema.json"
SESSION_SCHEMA_PATH = PROJECT_ROOT / "schemas" / "session.schema.json"
HISTORICAL_DECISION_SNAPSHOT_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "historical_decision_snapshot.schema.json"
)
HISTORICAL_GAME_REVIEW_SCHEMA_PATH = PROJECT_ROOT / "schemas" / "historical_game_review.schema.json"
HISTORICAL_GAME_SCHEMA_PATH = PROJECT_ROOT / "schemas" / "historical_game.schema.json"
HISTORICAL_GAME_END_SCHEMA_PATH = PROJECT_ROOT / "schemas" / "historical_game_end.schema.json"
HISTORICAL_GAME_EVENT_SCHEMA_PATH = PROJECT_ROOT / "schemas" / "historical_game_event.schema.json"
HISTORICAL_DEFENDER_OPEN_PLAY_CONTINUATION_EVENT_SCHEMA_PATH = (
    PROJECT_ROOT
    / "schemas"
    / "historical_defender_open_play_continuation_event.schema.json"
)
HISTORICAL_DECLARER_CARD_EXPOSURE_CONTINUATION_EVENT_SCHEMA_PATH = (
    PROJECT_ROOT
    / "schemas"
    / "historical_declarer_card_exposure_continuation_event.schema.json"
)
HISTORICAL_DECLARER_CARD_EXPOSURE_CONTINUATION_EVENT_OUTPUT_SCHEMA_PATH = (
    PROJECT_ROOT
    / "schemas"
    / "historical_declarer_card_exposure_continuation_event_output.schema.json"
)
HISTORICAL_GAME_EVENTS_OUTPUT_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "historical_game_events_output.schema.json"
)
HISTORICAL_DECLARER_CONCESSION_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "historical_declarer_concession.schema.json"
)
HISTORICAL_DECLARER_CONCESSION_OUTPUT_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "historical_declarer_concession_output.schema.json"
)
HISTORICAL_DEFENDER_CONCESSION_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "historical_defender_concession.schema.json"
)
HISTORICAL_DEFENDER_CONCESSION_OUTPUT_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "historical_defender_concession_output.schema.json"
)
HISTORICAL_DECLARER_CARD_EXPOSURE_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "historical_declarer_card_exposure.schema.json"
)
HISTORICAL_DECLARER_CARD_EXPOSURE_OUTPUT_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "historical_declarer_card_exposure_output.schema.json"
)
HISTORICAL_DEFENDER_OPEN_PLAY_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "historical_defender_open_play.schema.json"
)
HISTORICAL_DEFENDER_OPEN_PLAY_OUTPUT_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "historical_defender_open_play_output.schema.json"
)
HISTORICAL_OPEN_CARD_THROW_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "historical_open_card_throw.schema.json"
)
HISTORICAL_OPEN_CARD_THROW_OUTPUT_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "historical_open_card_throw_output.schema.json"
)
HISTORICAL_PARTY_WIDE_CLAIM_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "historical_party_wide_claim.schema.json"
)
HISTORICAL_PARTY_WIDE_CLAIM_OUTPUT_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "historical_party_wide_claim_output.schema.json"
)
TRAINING_DATASET_OUTPUT_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "training_dataset_output.schema.json"
)
TRAINING_DATASET_SCHEMA_PATH = PROJECT_ROOT / "schemas" / "training_dataset.schema.json"
DATASET_PARTITION_PLAN_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "dataset_partition_plan.schema.json"
)
TRAINING_DATASET_PREPARATION_OUTPUT_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "training_dataset_preparation_output.schema.json"
)
OPPONENT_STATISTICS_OUTPUT_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "opponent_statistics_output.schema.json"
)
OPPONENT_STATISTICS_INPUT_SCHEMA_PATH = PROJECT_ROOT / "schemas" / "opponent_statistics.schema.json"
HISTORICAL_OPPONENT_STATISTICS_AGGREGATION_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "historical_opponent_statistics_aggregation.schema.json"
)
OPPONENT_PROFILE_DERIVATION_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "opponent_profile_derivation.schema.json"
)
OPPONENT_PROFILE_APPLICATION_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "opponent_profile_application.schema.json"
)
HISTORICAL_OPPONENT_PROFILE_APPLICATION_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "historical_opponent_profile_application.schema.json"
)
ROLLING_OPPONENT_POLICY_EVALUATION_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "rolling_opponent_policy_evaluation.schema.json"
)
DATASET_PARTITION_POLICY_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "dataset_partition_policy.schema.json"
)
DATASET_PARTITION_AUDIT_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "dataset_partition_audit.schema.json"
)
DECLARER_CONCESSION_OUTPUT_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "declarer_concession_output.schema.json"
)
DEFENDER_CONCESSION_OUTPUT_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "defender_concession_output.schema.json"
)
DECLARER_CARD_EXPOSURE_OUTPUT_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "declarer_card_exposure_output.schema.json"
)
DEFENDER_OPEN_PLAY_OUTPUT_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "defender_open_play_output.schema.json"
)
OPEN_CARD_THROW_OUTPUT_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "open_card_throw_output.schema.json"
)
THEORETICAL_LEVEL_ASSESSMENT_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "theoretical_level_assessment.schema.json"
)
EXACT_REST_TRICK_PROOF_SCHEMA_PATH = PROJECT_ROOT / "schemas" / "exact_rest_trick_proof.schema.json"
DECLARER_CARD_EXPOSURE_CONTINUATION_OUTPUT_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "declarer_card_exposure_continuation_output.schema.json"
)
DEFENDER_OPEN_PLAY_CONTINUATION_OUTPUT_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "defender_open_play_continuation_output.schema.json"
)
PUBLIC_HAND_CONSTRAINT_SCHEMA_PATH = PROJECT_ROOT / "schemas" / "public_hand_constraint.schema.json"
HIDDEN_CARD_INFERENCE_SUMMARY_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "hidden_card_inference_summary.schema.json"
)
BOUNDED_SEARCH_RESULT_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "bounded_search_result.schema.json"
)
BOUNDED_SEARCH_POST_GAME_REVIEW_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "bounded_search_post_game_review.schema.json"
)
HISTORICAL_SEARCH_REVIEW_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "historical_search_review.schema.json"
)
HISTORICAL_REPLAY_COACHING_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "historical_replay_coaching.schema.json"
)
BOUNDED_SEARCH_EVALUATION_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "bounded_search_evaluation.schema.json"
)
INFORMATION_SET_SEARCH_RESULT_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "information_set_search_result.schema.json"
)
INFORMATION_SET_SEARCH_COMPARISON_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "information_set_search_comparison.schema.json"
)
HISTORICAL_INFORMATION_SET_SEARCH_REVIEW_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "historical_information_set_search_review.schema.json"
)
HISTORICAL_INFORMATION_SET_REPLAY_COACHING_SCHEMA_PATH = (
    PROJECT_ROOT
    / "schemas"
    / "historical_information_set_replay_coaching.schema.json"
)
HISTORICAL_TACTICAL_MOTIF_REVIEW_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "historical_tactical_motif_review.schema.json"
)
INFORMATION_SET_SEARCH_EVALUATION_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "information_set_search_evaluation.schema.json"
)
FIXED_THREE_PLAYER_HISTORICAL_LIST_AGGREGATION_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "fixed_three_player_historical_list_aggregation.schema.json"
)
FIXED_THREE_PLAYER_HISTORICAL_LIST_COMPARISON_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "fixed_three_player_historical_list_comparison.schema.json"
)
FIELD_PROVENANCE_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "field_provenance.schema.json"
)
DEFAULT_SAMPLE_COUNT = "20"
DEFAULT_RANDOM_SEED = "42"


CheckFunction = Callable[[dict[str, Any]], list[str]]


@dataclass(frozen=True)
class Scenario:
    """
    Defines one deterministic generated-output validation scenario.
    """

    name: str
    input_path: Path
    branch: str
    cli_args: tuple[str, ...] = ()
    check_output: CheckFunction | None = None
    expect_quiet_stdout: bool = False
    include_position_overrides: bool = True
    export_opponent_statistics: bool = False
    include_provenance: bool = False
    session_orchestration: str | None = None
    session_output_definition: str | None = None


_SESSION_PLAYERS = (
    session_api.SessionPlayerV1(
        player_id="player-a",
        player_label="Alice",
        seat="forehand",
    ),
    session_api.SessionPlayerV1(
        player_id="player-b",
        player_label="Bob",
        seat="middlehand",
    ),
    session_api.SessionPlayerV1(
        player_id="player-c",
        player_label="Carol",
        seat="rearhand",
    ),
)
_SESSION_HANDS = {
    "player-a": ("CA", "C10", "CK", "CQ", "CJ", "C9", "C8", "C7", "SA", "S10"),
    "player-b": ("SK", "SQ", "SJ", "S9", "S8", "S7", "HA", "H10", "HK", "HQ"),
    "player-c": ("HJ", "H9", "H8", "H7", "DA", "D10", "DK", "DQ", "DJ", "D9"),
}
_SESSION_POSITION_OPTIONS = session_api.SessionPositionExportOptionsV1(
    sample_count=1,
    random_seed=157,
    use_basic_opponent_strategy=True,
    recommendation_method=None,
    bounded_search_settings=None,
)


def _apply_session_document(
    state: session_api.SessionStateV1,
    document: dict[str, object],
) -> session_api.SessionStateV1:
    command = session_api.parse_session_command(document)
    result = session_api.apply_session_command(state, command).value
    if result.status != "applied":
        raise RuntimeError(
            f"Session fixture Command {document['kind']!r} was not applied: "
            f"{result.to_dict()}"
        )
    return result.state


def build_live_example_persistence_document() -> session_api.SessionPersistenceDocumentV1:
    """Builds the canonical Position-ready Live Session example."""
    state = session_api.create_session(
        session_id="session-live-example",
        players=_SESSION_PLAYERS,
        capture_mode="live",
        local_player_id="player-a",
    ).value
    state = _apply_session_document(
        state,
        {
            "command_version": 1,
            "kind": "set_game_metadata",
            "expected_revision": state.revision,
            "game_id": "session-live-example-game",
            "played_at": "2026-08-10T18:00:00Z",
        },
    )
    for card in _SESSION_HANDS["player-a"]:
        state = _apply_session_document(
            state,
            {
                "command_version": 1,
                "kind": "record_dealt_card",
                "expected_revision": state.revision,
                "destination": "player_hand",
                "player_id": "player-a",
                "card": card,
            },
        )
    state = _apply_session_document(
        state,
        {
            "command_version": 1,
            "kind": "set_declarer",
            "expected_revision": state.revision,
            "declarer_player_id": "player-a",
        },
    )
    state = _apply_session_document(
        state,
        {
            "command_version": 1,
            "kind": "set_declaration",
            "expected_revision": state.revision,
            "declaration": {
                "game_type": "grand",
                "hand_game": True,
                "ouvert": False,
                "schneider_announced": False,
                "schwarz_announced": False,
                "matadors": None,
                "bid_value": 24,
            },
        },
    )
    position_export = session_api.export_session_position_request(
        state,
        _SESSION_POSITION_OPTIONS,
    ).value
    checkpoint = session_api.build_session_decision_checkpoint(
        state=state,
        position_export=position_export,
    ).value
    return session_api.build_session_persistence_document(
        state,
        decision_checkpoints=(checkpoint,),
    ).value


def build_retrospective_example_persistence_document(
) -> session_api.SessionPersistenceDocumentV1:
    """Builds the canonical zero-decision Retrospective Session example."""
    state = session_api.create_session(
        session_id="session-retrospective-example",
        players=_SESSION_PLAYERS,
        capture_mode="retrospective",
        local_player_id=None,
    ).value
    state = _apply_session_document(
        state,
        {
            "command_version": 1,
            "kind": "set_game_metadata",
            "expected_revision": state.revision,
            "game_id": "session-retrospective-example-game",
            "played_at": "2026-08-09T18:00:00Z",
        },
    )
    for player in _SESSION_PLAYERS:
        for card in reversed(_SESSION_HANDS[player.player_id]):
            state = _apply_session_document(
                state,
                {
                    "command_version": 1,
                    "kind": "record_dealt_card",
                    "expected_revision": state.revision,
                    "destination": "player_hand",
                    "player_id": player.player_id,
                    "card": card,
                },
            )
    for card in reversed(("D8", "D7")):
        state = _apply_session_document(
            state,
            {
                "command_version": 1,
                "kind": "record_dealt_card",
                "expected_revision": state.revision,
                "destination": "skat",
                "player_id": None,
                "card": card,
            },
        )
    state = _apply_session_document(
        state,
        {
            "command_version": 1,
            "kind": "set_declarer",
            "expected_revision": state.revision,
            "declarer_player_id": "player-b",
        },
    )
    state = _apply_session_document(
        state,
        {
            "command_version": 1,
            "kind": "set_declaration",
            "expected_revision": state.revision,
            "declaration": {
                "game_type": "grand",
                "hand_game": False,
                "ouvert": False,
                "schneider_announced": False,
                "schwarz_announced": False,
                "matadors": None,
                "bid_value": 18,
            },
        },
    )
    for card in ("SK", "SQ"):
        state = _apply_session_document(
            state,
            {
                "command_version": 1,
                "kind": "record_discard",
                "expected_revision": state.revision,
                "card": card,
            },
        )
    state = _apply_session_document(
        state,
        {
            "command_version": 1,
            "kind": "set_game_end",
            "expected_revision": state.revision,
            "game_end_reason": "declarer_concession",
            "game_end": {
                "schema_version": 1,
                "kind": "declarer_concession",
                "declarer_hand_cards_remaining": 10,
                "defender_consent": {
                    "status": "not_required",
                    "consenting_defender_player_ids": [],
                },
            },
        },
    )
    return session_api.build_session_persistence_document(state).value


def load_json_file(file_path: Path) -> dict[str, Any]:
    """
    Loads a JSON file.
    """
    with file_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def format_scenario_error(scenario: Scenario, message: str) -> str:
    """
    Formats a scenario-specific validation or generation error.
    """
    return f"{scenario.name} ({scenario.branch}; input: {scenario.input_path}): {message}"


def format_validation_error(
    scenario: Scenario,
    file_path: Path,
    error,
) -> str:
    """
    Formats a JSON schema validation error.
    """
    location = ".".join(str(part) for part in error.absolute_path)

    if not location:
        location = "<root>"

    return format_scenario_error(
        scenario=scenario,
        message=f"{file_path}: {location}: {error.message}",
    )


def format_process_output(completed_process: subprocess.CompletedProcess[str]) -> str:
    """
    Formats captured CLI output for failure diagnostics.
    """
    output_parts = []

    if completed_process.stdout.strip():
        output_parts.append(f"stdout:\n{completed_process.stdout.strip()}")

    if completed_process.stderr.strip():
        output_parts.append(f"stderr:\n{completed_process.stderr.strip()}")

    if not output_parts:
        return "no CLI output"

    return "\n".join(output_parts)


def run_analysis(
    scenario: Scenario,
    output_path: Path,
) -> list[str]:
    """
    Runs the CLI analysis for one scenario input.
    """
    if output_path.exists():
        return [
            format_scenario_error(
                scenario=scenario,
                message=f"temporary output path already exists: {output_path}",
            )
        ]

    command = [
        sys.executable,
        str(PROJECT_ROOT / "main.py"),
        "--input",
        str(scenario.input_path),
        "--output",
        str(output_path),
    ]
    if scenario.include_position_overrides:
        command.extend(["--samples", DEFAULT_SAMPLE_COUNT, "--seed", DEFAULT_RANDOM_SEED])
    if scenario.export_opponent_statistics:
        command.extend(
            [
                "--export-opponent-statistics",
                str(output_path.with_suffix(".export.json")),
            ]
        )
    if scenario.include_provenance:
        command.append("--include-provenance")
    command.extend(scenario.cli_args)

    completed_process = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )

    if completed_process.returncode != 0:
        return [
            format_scenario_error(
                scenario=scenario,
                message=(
                    "CLI generation failed with exit code "
                    f"{completed_process.returncode}.\n"
                    f"{format_process_output(completed_process)}"
                ),
            )
        ]

    if not output_path.exists():
        return [
            format_scenario_error(
                scenario=scenario,
                message=(
                    "CLI generation completed without creating the expected "
                    f"output file: {output_path}.\n"
                    f"{format_process_output(completed_process)}"
                ),
            )
        ]

    if scenario.expect_quiet_stdout and completed_process.stdout != "":
        return [
            format_scenario_error(
                scenario=scenario,
                message=(
                    "expected quiet workflow to suppress successful stdout.\n"
                    f"{format_process_output(completed_process)}"
                ),
            )
        ]
    if scenario.expect_quiet_stdout and completed_process.stderr != "":
        return [
            format_scenario_error(
                scenario=scenario,
                message=(
                    "expected quiet workflow to suppress successful stderr.\n"
                    f"{format_process_output(completed_process)}"
                ),
            )
        ]

    return []


def validate_output_file(
    validator: Draft202012Validator,
    scenario: Scenario,
    output_path: Path,
) -> tuple[dict[str, Any] | None, list[str]]:
    """
    Validates one generated output file against the output schema.
    """
    try:
        data = load_json_file(output_path)
    except json.JSONDecodeError as error:
        return None, [
            format_scenario_error(
                scenario=scenario,
                message=f"generated malformed JSON in {output_path}: {error}",
            )
        ]

    return data, [
        format_validation_error(
            scenario=scenario,
            file_path=output_path,
            error=error,
        )
        for error in sorted(
            validator.iter_errors(data),
            key=lambda validation_error: list(validation_error.absolute_path),
        )
    ]


_PROVENANCE_RESULT_ATTACHMENTS = {
    "position_analysis": "position_result",
    "historical_game": "historical_game_result",
    "training_dataset": "training_dataset_result",
    "training_dataset_preparation": "dataset_preparation_result",
    "opponent_statistics": "opponent_statistics_result",
    "fixed_three_player_historical_list": "historical_list_result",
    "fixed_three_player_historical_list_comparison": (
        "historical_list_comparison_result"
    ),
}


def _output_workflow(data: dict[str, Any]) -> str:
    if "historical_game_summary" in data:
        return "historical_game"
    if "training_dataset_preparation_summary" in data:
        return "training_dataset_preparation"
    if "opponent_statistics_summary" in data:
        return "opponent_statistics"
    if "fixed_three_player_historical_list_summary" in data:
        return "fixed_three_player_historical_list"
    if "fixed_three_player_historical_list_comparison_summary" in data:
        return "fixed_three_player_historical_list_comparison"
    if any(
        name in data
        for name in (
            "training_dataset_summary",
            "historical_opponent_statistics_aggregation_summary",
            "rolling_opponent_policy_evaluation_summary",
            "dataset_partition_audit_summary",
            "bounded_search_evaluation_summary",
            "information_set_search_evaluation_summary",
        )
    ):
        return "training_dataset"
    return "position_analysis"


def _is_at_or_below(path: str, ancestor: str) -> bool:
    path_tokens = parse_json_pointer(path)
    ancestor_tokens = parse_json_pointer(ancestor)
    return path_tokens[: len(ancestor_tokens)] == ancestor_tokens


def _covered_leaf_paths(
    document: dict[str, Any],
    leaf_paths: tuple[str, ...],
    declaration: dict[str, Any],
) -> tuple[str, ...] | None:
    path = declaration["field_path"]
    try:
        resolve_json_pointer(document, path)
    except ValueError:
        return None
    if declaration["coverage_kind"] == "field":
        return (path,) if path in leaf_paths else None
    covered = tuple(leaf for leaf in leaf_paths if _is_at_or_below(leaf, path))
    return covered or None


def _check_public_attachment_semantics(
    attachment: dict[str, Any],
    *,
    document: dict[str, Any],
    workflow: str,
    attachment_name: str,
    document_scope: str,
) -> list[str]:
    errors = []
    if attachment["attachment_name"] != attachment_name:
        errors.append(f"expected Result attachment {attachment_name}")
    if attachment["document_role"] != "result":
        errors.append("expected only result-role public provenance")
    if attachment["document_scope"] != document_scope:
        errors.append(f"expected public document scope {document_scope}")
    if attachment["information_use_context"]["workflow"] != workflow:
        errors.append("expected attachment context workflow to match Root workflow")

    ledger = attachment["ledger"]
    if ledger["status"] != "complete":
        errors.append("expected complete public provenance ledger")
    if any(
        limitation != "private_dependencies_redacted"
        for limitation in ledger["limitations"]
    ):
        errors.append("public provenance contains a non-redaction limitation")
    if any(
        exemption["reason"] == "legacy_untracked"
        for exemption in ledger["exemptions"]
    ):
        errors.append("public provenance contains a legacy exemption")
    if any(
        entry["visibility"] == "engine_private"
        or any(
            reference["visibility"] == "engine_private"
            for reference in entry["source_references"]
        )
        for entry in ledger["entries"]
    ):
        errors.append("public provenance contains engine-private detail")
    entry_paths = {entry["field_path"] for entry in ledger["entries"]}
    if any(
        dependency not in entry_paths
        for entry in ledger["entries"]
        for dependency in entry["dependency_paths"]
    ):
        errors.append("public provenance contains an unresolved dependency")

    leaf_paths = enumerate_json_leaf_paths(document)
    coverage_count = {path: 0 for path in leaf_paths}
    provenanced_paths: set[str] = set()
    exempted_paths: set[str] = set()
    orphaned_entries = []
    orphaned_exemptions = []
    declarations = [
        *(
            (entry, provenanced_paths, orphaned_entries)
            for entry in ledger["entries"]
        ),
        *(
            (exemption, exempted_paths, orphaned_exemptions)
            for exemption in ledger["exemptions"]
        ),
    ]
    for declaration, covered_paths, orphaned in declarations:
        covered = _covered_leaf_paths(document, leaf_paths, declaration)
        if covered is None:
            orphaned.append(declaration["field_path"])
            continue
        for path in covered:
            coverage_count[path] += 1
            covered_paths.add(path)
    uncovered = sorted(path for path, count in coverage_count.items() if count == 0)
    overlapping = sorted(path for path, count in coverage_count.items() if count > 1)
    expected_summary = {
        "leaf_path_count": len(leaf_paths),
        "provenanced_path_count": len(provenanced_paths),
        "exempted_path_count": len(exempted_paths),
        "uncovered_paths": uncovered,
        "orphaned_entry_paths": sorted(orphaned_entries),
        "orphaned_exemption_paths": sorted(orphaned_exemptions),
        "overlapping_paths": overlapping,
        "all_paths_accounted_for": not uncovered and not overlapping,
        "provenance_complete": (
            not uncovered
            and not overlapping
            and not orphaned_entries
            and not orphaned_exemptions
        ),
    }
    if attachment["coverage_summary"] != expected_summary:
        errors.append("public Coverage Summary does not match the exact document")
    if not expected_summary["provenance_complete"]:
        errors.append("public provenance does not completely cover the exact document")
    return errors


def check_public_field_provenance(
    data: dict[str, Any],
    scenario: Scenario,
    artifact_document: dict[str, Any] | None,
) -> list[str]:
    bundle = data.get("field_provenance")
    if not scenario.include_provenance:
        return [] if bundle is None else ["unexpected field_provenance in default output"]
    if not isinstance(bundle, dict):
        return ["expected field_provenance for provenance-enabled output"]
    workflow = _output_workflow(data)
    errors = []
    if bundle["workflow"] != workflow:
        errors.append("public provenance workflow does not match output branch")
    if bundle["provenance_version"] != 1:
        errors.append("expected public field provenance version 1")
    if bundle["redaction_policy"] != "omit_engine_private_details":
        errors.append("expected public engine-private redaction policy")
    root_document = dict(data)
    root_document.pop("field_provenance")
    errors.extend(
        _check_public_attachment_semantics(
            bundle["result"],
            document=root_document,
            workflow=workflow,
            attachment_name=_PROVENANCE_RESULT_ATTACHMENTS[workflow],
            document_scope="root_result_without_field_provenance",
        )
    )
    if scenario.name == "field_provenance_position_analysis" and (
        "private_dependencies_redacted"
        not in bundle["result"]["ledger"]["limitations"]
    ):
        errors.append("expected the Position provenance scenario to exercise redaction")
    expected_artifact_count = 1 if artifact_document is not None else 0
    if len(bundle["artifacts"]) != expected_artifact_count:
        errors.append("public artifact provenance does not match actual artifacts")
    if artifact_document is not None and len(bundle["artifacts"]) == 1:
        artifact = bundle["artifacts"][0]
        if artifact["artifact_name"] != "opponent_statistics_input":
            errors.append("unexpected public artifact provenance name")
        errors.extend(
            _check_public_attachment_semantics(
                artifact["attachment"],
                document=artifact_document,
                workflow=workflow,
                attachment_name="training_dataset/opponent_statistics_input",
                document_scope="artifact_document",
            )
        )
    serialized = json.dumps(bundle, sort_keys=True).lower()
    for forbidden in (
        "defender_open_play_exact_proof_v1",
        "historical_remaining_card_reconstruction_v1",
        "principal_variation",
        "exact_search_state",
        "private_seed",
        "private_hand",
    ):
        if forbidden in serialized:
            errors.append(f"public provenance exposed private detail {forbidden}")
    return errors


def check_normal_local_live(data: dict[str, Any]) -> list[str]:
    """
    Checks the baseline local Immediate Analysis branch.
    """
    errors = []

    if not data["legal_cards"]:
        errors.append("expected non-empty legal_cards")

    if not data["analysis_report"]:
        errors.append("expected populated analysis_report")

    if data["recommendation"]["card"] is None:
        errors.append("expected recommendation.card to be populated")

    return errors


def check_opponent_turn_left_multi_step(data: dict[str, Any]) -> list[str]:
    """
    Checks opponent-turn Immediate unavailable plus left-lead preparation.
    """
    errors = []
    recommendation = data["recommendation"]
    multi_step_result = data.get("multi_step_result")

    if data["position"]["next_player"] != "left":
        errors.append("expected top-level position.next_player to remain left")

    if data["legal_cards"] != []:
        errors.append("expected opponent-turn legal_cards to be []")

    if data["analysis_report"] != []:
        errors.append("expected opponent-turn analysis_report to be []")

    if recommendation["card"] is not None:
        errors.append("expected opponent-turn recommendation.card to be null")

    if "local player is not next" not in recommendation["reason"]:
        errors.append("expected local-player-not-next recommendation reason")

    if data["post_game_review_summary"]["reason"] != "immediate_analysis_unavailable":
        errors.append("expected immediate_analysis_unavailable post-game reason")

    if not isinstance(multi_step_result, dict):
        errors.append("expected populated multi_step_result")
        return errors

    if multi_step_result["steps_simulated"] != 1:
        errors.append("expected exactly one simulated multi-step step")

    step = multi_step_result["steps"][0]
    opponent_result = step["opponent_lead_result"]

    if opponent_result["leader"] != "left":
        errors.append("expected left opponent lead preparation")

    if opponent_result["responder"] != "right":
        errors.append("expected right opponent response preparation")

    if step["prepared_state"]["next_player"] != "me":
        errors.append("expected prepared_state.next_player to be me")

    if len(step["prepared_state"]["current_trick"]) != 2:
        errors.append("expected prepared_state.current_trick to contain two cards")

    score_summary = multi_step_result["summary"]["score_summary"]
    for field_name in ["final_point_swing", "local_point_swing"]:
        if field_name not in score_summary:
            errors.append(f"expected multi-step score field {field_name}")

    detailed_result = step["detailed_result"]
    for field_name in ["candidate_card_won", "local_side_won"]:
        if field_name not in detailed_result:
            errors.append(f"expected detailed result field {field_name}")

    return errors


def check_local_live_multi_step(data: dict[str, Any]) -> list[str]:
    """
    Checks documented local two-step Multi-Step JSON output.
    """
    errors = []
    multi_step_result = data.get("multi_step_result")

    if data["position"]["next_player"] != "me":
        errors.append("expected top-level position.next_player to remain me")

    if data["recommendation"]["card"] is None:
        errors.append("expected live recommendation.card to be populated")

    if not isinstance(multi_step_result, dict):
        errors.append("expected populated multi_step_result")
        return errors

    if multi_step_result["requested_step_count"] != 2:
        errors.append("expected requested two-step simulation")

    if multi_step_result["steps_simulated"] != 2:
        errors.append("expected two simulated multi-step steps")

    if len(multi_step_result["steps"]) != 2:
        errors.append("expected two serialized multi-step steps")

    score_summary = multi_step_result["summary"]["score_summary"]
    for field_name in ["final_point_swing", "local_point_swing"]:
        if field_name not in score_summary:
            errors.append(f"expected multi-step score field {field_name}")

    return errors


def check_completed_game_immediate_unavailable(data: dict[str, Any]) -> list[str]:
    """
    Checks completed-game Immediate Analysis unavailable output.
    """
    errors = []

    if data["legal_cards"] != []:
        errors.append("expected completed-game legal_cards to be []")

    if data["analysis_report"] != []:
        errors.append("expected completed-game analysis_report to be []")

    if data["recommendation"]["card"] is not None:
        errors.append("expected completed-game recommendation.card to be null")

    if "game is complete" not in data["recommendation"]["reason"]:
        errors.append("expected game-complete recommendation reason")

    if data["final_settlement_summary"]["is_complete"] is not True:
        errors.append("expected completed-game final settlement")

    if data["performance_rating_summary"]["game_outcome"] != "declarer_win":
        errors.append("expected declarer_win performance outcome")

    return errors


def check_post_game_available_nested_suit(data: dict[str, Any]) -> list[str]:
    """
    Checks actual-card post-game review and nested Suit declaration output.
    """
    errors = []
    summary = data["post_game_review_summary"]

    if summary["is_available"] is not True:
        errors.append("expected available post-game review")

    if summary["reason"] != "actual_card_played_provided":
        errors.append("expected actual_card_played_provided reason")

    for field_name in [
        "actual_expected_point_swing",
        "recommended_expected_point_swing",
        "expected_point_swing_difference",
        "actual_card_rank",
        "recommended_card_rank",
        "better_card_count",
    ]:
        if summary[field_name] is None:
            errors.append(f"expected populated post-game field {field_name}")

    if data["game_declaration"]["game_type"] != "spades":
        errors.append("expected effective nested declaration game_type spades")

    if data["game_value_summary"]["game_value"] != 22:
        errors.append("expected nested Suit game value 22")

    if data["overbid_summary"]["status"] != "unknown_bid_value":
        errors.append("expected nested declaration overbid status unknown_bid_value")

    if data["final_settlement_summary"]["game_value"] != 22:
        errors.append("expected final settlement to receive nested game value")

    if data["performance_rating_summary"]["game_outcome"] != "incomplete":
        errors.append("expected incomplete performance outcome")

    return errors


def check_post_game_null_objective_review(data: dict[str, Any]) -> list[str]:
    """Checks actual-card post-game review using the Null objective."""
    errors = []
    summary = data["post_game_review_summary"]

    if data["position"]["game_type"] != "null":
        errors.append("expected Null post-game review")

    if summary["is_available"] is not True:
        errors.append("expected available Null post-game review")

    if summary["actual_card_played"] != "C8":
        errors.append("expected actual Null card C8")

    if summary["recommended_card"] != "C7":
        errors.append("expected recommended Null card C7")

    if summary["decision_quality"] != "optimal":
        errors.append("expected Null objective tie to be optimal")

    if summary["decision_factors"] != ["no_missed_null_objective"]:
        errors.append("expected no_missed_null_objective factor")

    if summary["better_card_count"] != 0:
        errors.append("expected no better Null-objective alternatives")

    if "Null contract-objective utility" not in summary["decision_explanation"]:
        errors.append("expected Null objective explanation")

    return errors


def check_post_game_defender_perspective_review(data: dict[str, Any]) -> list[str]:
    """Checks actual-card post-game review from a local defender perspective."""
    errors = []
    summary = data["post_game_review_summary"]

    if data["position"]["player_role"] != "defender":
        errors.append("expected local defender position")

    if data["position"]["declarer_player"] != "left":
        errors.append("expected concrete left declarer")

    if summary["is_available"] is not True:
        errors.append("expected available defender post-game review")

    if summary["actual_card_played"] != "CK":
        errors.append("expected actual defender card CK")

    if summary["recommended_card"] != "C7":
        errors.append("expected recommended defender card C7")

    if summary["decision_quality"] != "suboptimal":
        errors.append("expected suboptimal defender decision quality")

    if summary["decision_factors"] != [
        "lower_expected_point_swing_than_recommendation",
        "medium_expected_point_swing_gap",
    ]:
        errors.append("expected medium point-swing gap factors")

    if summary["better_card_count"] != 1:
        errors.append("expected one better defender alternative")

    return errors


def check_multi_step_partial_trick(data: dict[str, Any]) -> list[str]:
    """
    Checks right-response preparation after an existing left lead.
    """
    errors = []
    multi_step_result = data.get("multi_step_result")

    if data["position"]["current_trick"] != ["D7"]:
        errors.append("expected original one-card current_trick to be preserved")

    if data["position"]["next_player"] != "right":
        errors.append("expected top-level position.next_player to remain right")

    if not isinstance(multi_step_result, dict):
        errors.append("expected populated multi_step_result")
        return errors

    step = multi_step_result["steps"][0]
    opponent_result = step["opponent_lead_result"]
    prepared_state = step["prepared_state"]

    if opponent_result["lead_card"] != "D7":
        errors.append("expected opponent preparation to preserve original lead card")

    if opponent_result["responder"] != "right":
        errors.append("expected right response preparation")

    if prepared_state["current_trick"][0] != "D7":
        errors.append("expected prepared_state to preserve original lead card")

    if len(prepared_state["current_trick"]) != 2:
        errors.append("expected prepared_state.current_trick to contain two cards")

    if prepared_state["next_player"] != "me":
        errors.append("expected prepared_state.next_player to be me")

    return errors


def check_canonical_multi_step_completion_phase(data: dict[str, Any]) -> list[str]:
    """
    Checks canonical completion before the next local Multi-Step Decision.
    """
    errors = []
    post_game_summary = data["post_game_review_summary"]
    recommendation = data["recommendation"]
    multi_step_result = data.get("multi_step_result")

    if data["position"]["next_player"] != "left":
        errors.append("expected top-level position.next_player to remain left")

    if data["legal_cards"] != []:
        errors.append("expected opponent-turn legal_cards to be []")

    if data["analysis_report"] != []:
        errors.append("expected opponent-turn analysis_report to be []")

    if recommendation["card"] is not None:
        errors.append("expected opponent-turn recommendation.card to be null")

    if post_game_summary["is_available"] is not False:
        errors.append("expected post-game review to be unavailable")

    if post_game_summary["reason"] != "immediate_analysis_unavailable":
        errors.append("expected immediate_analysis_unavailable post-game reason")

    if post_game_summary["actual_card_played"] != "SA":
        errors.append("expected actual card to be retained in unavailable review")

    if not isinstance(multi_step_result, dict):
        errors.append("expected populated multi_step_result")
        return errors

    if multi_step_result["stop_reason"] != "Requested step count reached.":
        errors.append("expected requested-step-count stop after canonical completion")

    if multi_step_result["steps_simulated"] != 1:
        errors.append("expected one local step after canonical completion")

    if len(multi_step_result["steps"]) != 1:
        errors.append("expected one candidate simulation step")
        return errors

    step = multi_step_result["steps"][0]
    if step["step_index"] != 0:
        errors.append("expected first new local Decision to use step index zero")
    if step["prepared_state"]["hand"] != data["position"]["hand"]:
        errors.append("expected initial completion to preserve the local hand")
    if step["prepared_state"]["completed_tricks"][0]["cards"][0] != "S7":
        errors.append("expected completed Trick to preserve the existing local Card")

    return errors


def check_policy_comparison(data: dict[str, Any]) -> list[str]:
    """
    Checks generated policy-comparison output.
    """
    errors = []
    comparison_result = data.get("policy_comparison_result")

    if not isinstance(comparison_result, dict):
        errors.append("expected populated policy_comparison_result")
        return errors

    if not comparison_result["policy_results"]:
        errors.append("expected non-empty policy_results")

    if "recommended_policy" not in comparison_result:
        errors.append("expected recommended_policy")

    policy_result = comparison_result["policy_results"][0]
    for field_name in ["final_point_swing", "local_point_swing", "context_summary"]:
        if field_name not in policy_result:
            errors.append(f"expected policy result field {field_name}")

    return errors


def check_coherent_hidden_world_policy_comparison(
    data: dict[str, Any],
) -> list[str]:
    """Checks privacy-safe coherent-world evidence across compared paths."""
    errors = []
    comparison = data.get("policy_comparison_result")
    if not isinstance(comparison, dict):
        return ["expected populated policy_comparison_result"]

    shared = comparison.get("hidden_world", {})
    if shared.get("mode") != "coherent_path":
        errors.append("expected coherent_path comparison mode")
    if shared.get("shared_root_world") is not True:
        errors.append("expected all policies to share one root world")
    if shared.get("root_sample_count") != 1:
        errors.append("expected exactly one comparison root sample")
    if shared.get("independent_path_worlds") is not True:
        errors.append("expected independent policy path worlds")

    policy_results = comparison.get("policy_results", [])
    if len(policy_results) != 4:
        errors.append("expected all four local policies")
    for policy_result in policy_results:
        world = policy_result.get("context_summary", {}).get("hidden_world", {})
        if world.get("mode") != "coherent_path":
            errors.append("expected coherent_path mode for every policy")
        if world.get("root_sample_count") != 1:
            errors.append("expected one root sample per policy path")
        if world.get("resampled_after_path_start") is not False:
            errors.append("expected no path resampling")
        if world.get("ownership_preserved") is not True:
            errors.append("expected preserved ownership")
        if world.get("duplicate_card_detected") is not False:
            errors.append("expected no duplicate-card violation")
        if world.get("ownership_violation_detected") is not False:
            errors.append("expected no ownership violation")
        if world.get("hidden_cards_emitted") is not False:
            errors.append("expected no hidden cards to be emitted")
        initial_total = world.get("initial_left_hand_size", 0) + world.get(
            "initial_right_hand_size", 0
        )
        remaining_total = world.get("remaining_left_hand_size", 0) + world.get(
            "remaining_right_hand_size", 0
        )
        if initial_total - remaining_total != world.get("opponent_cards_played"):
            errors.append("expected opponent transition counts to reconcile")
        if world.get("remaining_hypothetical_skat_size") != world.get(
            "initial_hypothetical_skat_size"
        ):
            errors.append("expected fixed hypothetical skat count")

    forbidden_keys = {
        "left_hand",
        "right_hand",
        "hypothetical_skat",
        "initial_hypothetical_skat",
        "coherent_hidden_world",
        "hidden_world_digest",
    }

    def find_forbidden(value: Any) -> bool:
        if isinstance(value, dict):
            return bool(forbidden_keys.intersection(value)) or any(
                find_forbidden(child) for child in value.values()
            )
        if isinstance(value, list):
            return any(find_forbidden(child) for child in value)
        return False

    if find_forbidden(comparison):
        errors.append("expected no private hidden-world card fields")
    return errors


def check_comparison_only(data: dict[str, Any]) -> list[str]:
    """
    Checks comparison-only workflow output still contains JSON result branches.
    """
    errors = check_policy_comparison(data)

    if not isinstance(data.get("multi_step_result"), dict):
        errors.append("expected comparison-only output to retain multi_step_result")

    return errors


def check_side_specific_opponent_policies(data: dict[str, Any]) -> list[str]:
    """
    Checks distinct left/right opponent policy output.
    """
    errors = []

    if data["left_opponent_policy_settings"] != {
        "opponent_lead_policy": "highest_point",
        "opponent_response_policy": "basic_trick_play",
    }:
        errors.append("expected distinct left opponent policy settings")

    if data["right_opponent_policy_settings"] != {
        "opponent_lead_policy": "basic_defender_lead",
        "opponent_response_policy": "basic_defender_response",
    }:
        errors.append("expected distinct right opponent policy settings")

    return errors


def check_side_specific_opponent_policy_multi_step(
    data: dict[str, Any],
) -> list[str]:
    """
    Checks side-specific opponent lead policies in Multi-Step output.
    """
    errors = check_side_specific_opponent_policies(data)
    multi_step_result = data.get("multi_step_result")

    if not isinstance(multi_step_result, dict):
        errors.append("expected populated multi_step_result")
        return errors

    if multi_step_result["requested_step_count"] != 2:
        errors.append("expected requested two-step simulation")

    if (
        multi_step_result["left_opponent_policy_settings"]
        != (data["left_opponent_policy_settings"])
    ):
        errors.append("expected multi-step left opponent settings to match top level")

    if (
        multi_step_result["right_opponent_policy_settings"]
        != (data["right_opponent_policy_settings"])
    ):
        errors.append("expected multi-step right opponent settings to match top level")

    return errors


def check_claim_remaining_tricks(data: dict[str, Any]) -> list[str]:
    """
    Checks claim/concession settlement output structure with one representative claim.
    """
    errors = []
    adjusted_result = data["adjusted_game_result_summary"]

    if adjusted_result["game_end_reason"] != "declarer_claimed_remaining_tricks":
        errors.append("expected declarer_claimed_remaining_tricks adjustment")

    if adjusted_result["remaining_points_recipient"] != "declarer":
        errors.append("expected remaining points assigned to declarer")

    if data["final_settlement_summary"]["is_complete"] is not True:
        errors.append("expected complete claim settlement")

    return errors


def check_structured_declarer_concession(data: dict[str, Any]) -> list[str]:
    """Checks adjudication without assignment or achieved-level inference."""
    errors = []
    raw_result = data["game_result_summary"]
    adjusted_result = data["adjusted_game_result_summary"]
    summary = data.get("game_shortening_summary")
    settlement = data["final_settlement_summary"]

    if not isinstance(summary, dict):
        return ["expected game_shortening_summary"]
    if raw_result["points_remaining"] != 120:
        errors.append("expected all 120 zero-point-trick points to remain unplayed")
    if adjusted_result["points_remaining"] != raw_result["points_remaining"]:
        errors.append("expected adjusted result to preserve unplayed points")
    if adjusted_result["winner"] != "defenders":
        errors.append("expected adjudicated defender winner")
    if adjusted_result["remaining_points_recipient"] is not None:
        errors.append("expected no remaining points recipient")
    if adjusted_result["remaining_points_assigned"] != 0:
        errors.append("expected zero assigned remaining points")
    if summary.get("rule_sections") != ["4.4.1"]:
        errors.append("expected deterministic ISkO 4.4.1 rule section")
    if summary.get("hand_card_count_reconciliation") != "confirmed":
        errors.append("expected confirmed declarer hand-card count")
    if settlement.get("settlement_score") != -144:
        errors.append("expected simple doubled Grand loss of -144")
    if settlement.get("settlement_basis") != {
        "game_end_kind": "declarer_concession",
        "outcome_source": "adjudicated",
        "forced_winner": "defenders",
        "achieved_schneider_applied": False,
        "achieved_schwarz_applied": False,
        "overbid_required_value_applied": False,
    }:
        errors.append("expected bounded declarer-concession settlement basis")

    return errors


def check_structured_defender_concession(data: dict[str, Any]) -> list[str]:
    """Checks joint-liability adjudication without remaining-point assignment."""
    errors = []
    raw_result = data["game_result_summary"]
    adjusted_result = data["adjusted_game_result_summary"]
    summary = data.get("game_shortening_summary")
    settlement = data["final_settlement_summary"]

    if not isinstance(summary, dict):
        return ["expected game_shortening_summary"]
    if adjusted_result["declarer_points"] != raw_result["declarer_points"]:
        errors.append("expected observed declarer points to remain unchanged")
    if adjusted_result["defender_points"] != raw_result["defender_points"]:
        errors.append("expected observed defender points to remain unchanged")
    if adjusted_result["points_remaining"] != raw_result["points_remaining"]:
        errors.append("expected unplayed points to remain unassigned")
    if adjusted_result["winner"] != "declarer":
        errors.append("expected undecided game adjudicated for declarer")
    if adjusted_result["remaining_points_recipient"] is not None:
        errors.append("expected no remaining points recipient")
    if adjusted_result["remaining_points_assigned"] != 0:
        errors.append("expected zero assigned remaining points")
    if summary.get("rule_sections") != ["4.4.3", "4.1.4"]:
        errors.append("expected deterministic ISkO 4.4.3 and 4.1.4 sections")
    if summary.get("conceding_player") != "left":
        errors.append("expected concrete left conceding player")
    if summary.get("joint_liability") is not True:
        errors.append("expected joint defender liability")
    if settlement.get("settlement_score") != 72:
        errors.append("expected simple Grand win of 72")
    if settlement.get("settlement_basis") != {
        "game_end_kind": "defender_concession",
        "outcome_source": "adjudicated",
        "winner_basis": "defender_concession",
        "decision_state_before_game_end": "undecided",
        "mandatory_level_awarded": False,
        "mandatory_level_source": None,
        "achieved_schneider_applied": False,
        "achieved_schwarz_applied": False,
        "overbid_required_value_applied": False,
    }:
        errors.append("expected bounded defender-concession settlement basis")

    return errors


def check_declarer_card_exposure(data: dict[str, Any]) -> list[str]:
    """Checks accepted exposure, claimed-level settlement, and no assignment."""
    errors = []
    raw_result = data["game_result_summary"]
    adjusted_result = data["adjusted_game_result_summary"]
    summary = data.get("game_shortening_summary")
    settlement = data["final_settlement_summary"]

    if not isinstance(summary, dict):
        return ["expected game_shortening_summary"]
    for field_name in ("declarer_points", "defender_points", "points_remaining"):
        if adjusted_result[field_name] != raw_result[field_name]:
            errors.append(f"expected preserved {field_name}")
    if adjusted_result["winner"] != "declarer":
        errors.append("expected accepted exposure to adjudicate the declarer win")
    if adjusted_result["remaining_points_recipient"] is not None:
        errors.append("expected no remaining points recipient")
    if adjusted_result["remaining_points_assigned"] != 0:
        errors.append("expected zero assigned remaining points")
    if summary.get("rule_sections") != ["4.4.4"]:
        errors.append("expected deterministic ISkO 4.4.4 section")
    if summary.get("card_reconciliation") != "confirmed":
        errors.append("expected confirmed complete exposed-card reconciliation")
    if summary.get("accepting_defenders") != ["left", "right"]:
        errors.append("expected deterministic concrete defender order")
    if settlement.get("settlement_score") != 96:
        errors.append("expected accepted Schneider Grand settlement of 96")
    basis = settlement.get("settlement_basis")
    if not isinstance(basis, dict):
        errors.append("expected declarer-card-exposure settlement basis")
    else:
        if basis.get("accepted_claimed_schneider_applied") is not True:
            errors.append("expected accepted Schneider claim to be applied")
        if basis.get("achieved_schneider_applied") is not False:
            errors.append("expected accepted Schneider not labeled as achieved")
        if basis.get("overbid_required_value_applied") is not False:
            errors.append("expected no overbid-required value")
    return errors


def check_defender_open_play(data: dict[str, Any]) -> list[str]:
    """Checks exact proof, rule assignment, privacy, and settlement."""
    errors = []
    adjusted_result = data["adjusted_game_result_summary"]
    summary = data.get("game_shortening_summary")
    settlement = data["final_settlement_summary"]
    if not isinstance(summary, dict):
        return ["expected defender-open-play game_shortening_summary"]
    proof = summary.get("exact_proof", {})
    if summary.get("rule_sections") != ["4.4.5"]:
        errors.append("expected deterministic ISkO 4.4.5 rule section")
    if summary.get("exposing_defender") != "me":
        errors.append("expected concrete exposing defender")
    if summary.get("non_exposing_defender") != "right":
        errors.append("expected deterministic non-exposing defender")
    if proof.get("status") != "valid" or proof.get("proof_complete") is not True:
        errors.append("expected complete valid exact proof")
    if proof.get("quantifier_policy") != {
        "exposing_defender": "exists_legal_strategy",
        "declarer": "all_legal_plays",
        "non_exposing_defender": "all_legal_plays",
    }:
        errors.append("expected exact defender-open-play quantifier policy")
    if proof.get("evaluated_state_count") != 18:
        errors.append("expected deterministic evaluated-state count")
    if proof.get("memoized_state_count") != 18:
        errors.append("expected deterministic memoized-state count")
    assignment = summary.get("rest_trick_assignment")
    if assignment != {
        "source": "defender_open_play_adjudication",
        "recipient": "defenders",
        "remaining_trick_count": 2,
        "assigned_card_count": 6,
        "assigned_card_points": 12,
    }:
        errors.append("expected exact defender-side rest-trick assignment")
    if adjusted_result.get("defender_points") != 65:
        errors.append("expected assigned final defender points")
    if adjusted_result.get("declarer_points") != 55:
        errors.append("expected preserved observed declarer points")
    if settlement.get("settlement_score") != -144:
        errors.append("expected simple doubled Grand loss")
    serialized = json.dumps(data)
    if "remaining_hands" in serialized:
        errors.append("private exact remaining hands must not be emitted")
    for hidden_card in ("D7", "D8", "D9", "H8"):
        if f'"{hidden_card}"' in serialized:
            errors.append(f"hidden proof card {hidden_card} must not be emitted")
    return errors


def check_open_card_throw(data: dict[str, Any]) -> list[str]:
    """Checks ISkO 4.4.6 assignment, level state, privacy, and settlement."""
    errors = []
    adjusted = data["adjusted_game_result_summary"]
    summary = data.get("game_shortening_summary")
    settlement = data["final_settlement_summary"]
    if not isinstance(summary, dict):
        return ["expected open-card-throw game_shortening_summary"]
    if summary.get("rule_sections") != ["4.4.6"]:
        errors.append("expected deterministic ISkO 4.4.6 rule section")
    if summary.get("throwing_player") != "left":
        errors.append("expected concrete left throwing player")
    if summary.get("throwing_party") != "defenders":
        errors.append("expected defending throwing party")
    if summary.get("opposing_party") != "declarer":
        errors.append("expected declarer opposing party")
    if summary.get("joint_liability") is not True:
        errors.append("expected joint defender liability")
    if summary.get("thrown_cards") != ["C10", "S10"]:
        errors.append("expected canonical public thrown hand")
    if summary.get("card_reconciliation") != "not_verifiable":
        errors.append("expected bounded opponent-hand reconciliation")
    if summary.get("statement_classification") != "attempted_level_limitation":
        errors.append("expected restrictive-statement provenance")
    if summary.get("decision_state_before_shortening") != "undecided":
        errors.append("expected undecided pre-throw state")
    if summary.get("rest_trick_assignment") != {
        "source": "open_card_throw",
        "recipient": "declarer",
        "remaining_trick_count": 2,
        "assigned_card_count": 6,
        "assigned_card_points": 63,
    }:
        errors.append("expected complete declarer-side unresolved assignment")
    if adjusted.get("final_points") != {"declarer": 120, "defenders": 0}:
        errors.append("expected final 120-point reconciliation")
    if adjusted.get("final_trick_counts") != {"declarer": 10, "defenders": 0}:
        errors.append("expected final ten-trick reconciliation")
    if adjusted.get("winner") != "declarer":
        errors.append("expected defender throw adjudicated for declarer")
    if adjusted.get("open_throw_schneider_applied") is not True:
        errors.append("expected open-throw Schneider rule level")
    if adjusted.get("open_throw_schwarz_applied") is not True:
        errors.append("expected open-throw Schwarz rule level")
    if adjusted.get("achieved_schneider_applied") is not False:
        errors.append("expected Schneider not labeled as achieved during play")
    if adjusted.get("achieved_schwarz_applied") is not False:
        errors.append("expected Schwarz not labeled as achieved during play")
    if summary.get("theoretical_schwarz_status") != "not_excluded":
        errors.append("expected deterministic non-excluded jack-only assessment")
    if settlement.get("settlement_score") != 168:
        errors.append("expected Grand Schneider and Schwarz settlement")
    if data.get("position", {}).get("hand") != []:
        errors.append("non-throwing complete local hand must be redacted")
    serialized = json.dumps(data)
    for unsupported in ("remaining_hands", "exact_proof", "proof_complete"):
        if unsupported in serialized:
            errors.append(f"open-card-throw output must not contain {unsupported}")
    return errors


def check_declarer_card_exposure_continuation(
    data: dict[str, Any],
) -> list[str]:
    """Checks exact public-hand analysis without game-end adjudication."""
    errors = []
    summary = data.get("game_continuation_summary")
    information = data.get("information_policy_summary", {})
    adjusted_result = data["adjusted_game_result_summary"]
    settlement = data["final_settlement_summary"]
    if not isinstance(summary, dict):
        return ["expected game_continuation_summary"]
    if summary.get("continuing_defenders") != ["me"]:
        errors.append("expected local defender to request continuation")
    if summary.get("accepting_defenders") != ["right"]:
        errors.append("expected right defender acceptance provenance")
    if summary.get("public_declarer_cards") != ["C10", "SK", "SJ", "S7", "HK", "DK"]:
        errors.append("expected canonical exact public declarer hand")
    if summary.get("game_end_applied") is not False:
        errors.append("expected no game end from continuation")
    if summary.get("settlement_applied") is not False:
        errors.append("expected no settlement from continuation")
    constraints = information.get("public_hand_constraints")
    if not isinstance(constraints, list) or len(constraints) != 1:
        errors.append("expected one public declarer-hand constraint")
    elif constraints[0].get("player") != "left":
        errors.append("expected public constraint for left declarer")
    if adjusted_result.get("is_complete") is not False:
        errors.append("expected continued game to remain incomplete")
    if adjusted_result.get("game_end_reason") != "not_ended":
        errors.append("expected neutral game-end reason")
    if settlement.get("is_complete") is not False:
        errors.append("expected incomplete final settlement")
    if not data.get("analysis_report"):
        errors.append("expected available Immediate Analysis")
    return errors


def check_defender_open_play_continuation(
    data: dict[str, Any],
) -> list[str]:
    """Checks returned public cards without proof, adjudication, or settlement."""
    errors = []
    summary = data.get("game_continuation_summary")
    information = data.get("information_policy_summary", {})
    adjusted_result = data["adjusted_game_result_summary"]
    settlement = data["final_settlement_summary"]
    if not isinstance(summary, dict):
        return ["expected defender-open-play game_continuation_summary"]
    if summary.get("exposing_defender") != "left":
        errors.append("expected left exposing defender")
    if summary.get("non_exposing_defender") != "right":
        errors.append("expected right non-exposing defender")
    if summary.get("public_exposing_defender_cards") != ["C7", "H8", "D9"]:
        errors.append("expected canonical exact public exposing-defender hand")
    if summary.get("cards_returned_to_hand") is not True:
        errors.append("expected exposed cards returned to hand")
    if summary.get("hand_physically_open") is not False:
        errors.append("expected returned hand not physically open")
    if summary.get("rest_trick_claim_status") != ("not_adjudicated_due_to_continued_play"):
        errors.append("expected original rest-trick claim not adjudicated")
    for field in ("exact_proof_applied", "game_end_applied", "settlement_applied"):
        if summary.get(field) is not False:
            errors.append(f"expected {field} false")
    constraints = information.get("public_hand_constraints")
    if not isinstance(constraints, list) or len(constraints) != 1:
        errors.append("expected one public exposing-defender constraint")
    elif constraints[0].get("source") != "defender_open_play_continuation":
        errors.append("expected defender-open-play continuation constraint source")
    if adjusted_result.get("is_complete") is not False:
        errors.append("expected continued game to remain incomplete")
    if adjusted_result.get("winner") != "undecided":
        errors.append("expected no decided winner from continued play")
    if settlement.get("is_complete") is not False:
        errors.append("expected incomplete final settlement")
    if not data.get("analysis_report"):
        errors.append("expected available Immediate Analysis")
    serialized = json.dumps(data)
    for forbidden in ('"exact_proof":', '"rest_trick_assignment":', '"settlement_basis":'):
        if forbidden in serialized:
            errors.append(f"unexpected {forbidden} in continuation output")
    return errors


def check_overbid_settlement(data: dict[str, Any]) -> list[str]:
    """
    Checks the supported Suit/Grand overbid settlement branch.
    """
    errors = []

    if data["overbid_summary"]["status"] != "overbid":
        errors.append("expected overbid status")

    if data["final_settlement_summary"]["is_overbid"] is not True:
        errors.append("expected final settlement is_overbid true")

    if data["final_settlement_summary"]["is_loss"] is not True:
        errors.append("expected overbid settlement loss")

    if data["performance_rating_summary"]["game_outcome"] != "declarer_loss":
        errors.append("expected overbid declarer_loss performance outcome")

    return errors


def check_impossible_null_settlement(data: dict[str, Any]) -> list[str]:
    """Checks the complete impossible Null replacement settlement branch."""
    errors = []
    replacement = data["overbid_summary"].get("impossible_null_settlement")

    if data["game_declaration"]["game_type"] != "null":
        errors.append("expected original Null declaration")

    if data["game_value_summary"]["game_value"] != 59:
        errors.append("expected original Null ouvert Hand value 59")

    if not isinstance(replacement, dict):
        errors.append("expected impossible Null replacement summary")
        return errors

    if replacement.get("hand_game") is not True:
        errors.append("expected replacement Hand status")

    if "ouvert" in replacement:
        errors.append("expected Null ouvert not to transfer")

    settlement = data["final_settlement_summary"]
    if settlement["settlement_score"] != -120:
        errors.append("expected doubled impossible Null loss score -120")

    if settlement["declarer_won_by_card_points"] is not None:
        errors.append("expected no card-point winner for immediate loss")

    return errors


def check_list_performance_summary(
    data: dict[str, Any],
    expected_summary: dict[str, Any],
) -> list[str]:
    """
    Checks optional list performance summary output.
    """
    errors = []
    list_summary = data.get("list_performance_summary")

    if not isinstance(list_summary, dict):
        errors.append("expected populated list_performance_summary")
        return errors

    if list_summary != expected_summary:
        errors.append(f"unexpected list_performance_summary: {list_summary}")

    if "list_standings_summary" in data:
        errors.append("expected single-player list mode not to emit standings")

    return errors


def check_list_performance(data: dict[str, Any]) -> list[str]:
    """Checks already aggregated list performance summary output."""
    return check_list_performance_summary(
        data=data,
        expected_summary={
            "rating_system": "isko_list",
            "basis": "aggregated_list_or_series_totals",
            "table_size": 3,
            "player_game_points": 120,
            "own_games_won": 3,
            "own_games_lost": 1,
            "other_players_lost_games": 2,
            "own_game_bonus_points": 100,
            "opponent_loss_bonus_points": 80,
            "total_performance_points": 300,
        },
    )


def check_list_game_contributions(data: dict[str, Any]) -> list[str]:
    """Checks normalized game-contribution list performance output."""
    return check_list_performance_summary(
        data=data,
        expected_summary={
            "rating_system": "isko_list",
            "basis": "normalized_game_contributions",
            "table_size": 3,
            "player_game_points": 24,
            "own_games_won": 1,
            "own_games_lost": 1,
            "other_players_lost_games": 1,
            "own_game_bonus_points": 0,
            "opponent_loss_bonus_points": 40,
            "total_performance_points": 64,
        },
    )


def check_list_analysis_results(data: dict[str, Any]) -> list[str]:
    """Checks local analysis-result list performance output."""
    return check_list_performance_summary(
        data=data,
        expected_summary={
            "rating_system": "isko_list",
            "basis": "local_analysis_results",
            "table_size": 3,
            "player_game_points": 24,
            "own_games_won": 1,
            "own_games_lost": 1,
            "other_players_lost_games": 1,
            "own_game_bonus_points": 0,
            "opponent_loss_bonus_points": 40,
            "total_performance_points": 64,
        },
    )


def check_list_standings(data: dict[str, Any]) -> list[str]:
    """Checks optional fixed three-player list standings output."""
    errors = []
    standings_summary = data.get("list_standings_summary")

    if not isinstance(standings_summary, dict):
        errors.append("expected populated list_standings_summary")
        return errors

    if standings_summary["basis"] != "fixed_three_player_game_results":
        errors.append("expected fixed three-player standings basis")

    if standings_summary["ranking_status"] != "final":
        errors.append("expected final fixed three-player standings")

    if standings_summary["lot_required_player_ids"] != []:
        errors.append("expected no unresolved standings lot")

    if standings_summary["applied_lot_order"] is not None:
        errors.append("expected no applied standings lot")

    standings = standings_summary["standings"]
    if len(standings) != 3:
        errors.append("expected exactly three standings rows")
        return errors

    expected_rows = [
        ("alice", 1, 186),
        ("carol", 2, 138),
        ("bob", 3, -122),
    ]
    actual_rows = [
        (
            row["player_id"],
            row["rank"],
            row["total_performance_points"],
        )
        for row in standings
    ]
    if actual_rows != expected_rows:
        errors.append(f"unexpected standings rows: {actual_rows}")

    if "list_performance_summary" in data:
        errors.append("expected standings mode not to emit list_performance_summary")

    return errors


def check_late_game_history_heavy_live(data: dict[str, Any]) -> list[str]:
    """
    Checks a late-game live input with zero opponent hand sizes and rich history.
    """
    errors = []

    if data["settings"]["left_hand_size"] != 0:
        errors.append("expected left_hand_size to be zero")

    if data["settings"]["right_hand_size"] != 0:
        errors.append("expected right_hand_size to be zero")

    if data["position"]["current_trick"] != ["D8", "D9"]:
        errors.append("expected preserved two-card late-game current_trick")

    if len(data["position"]["completed_tricks"]) != 9:
        errors.append("expected nine completed history tricks")

    if data["legal_cards"] != ["D7"]:
        errors.append("expected final local card to be the only legal card")

    if data["recommendation"]["card"] != "D7":
        errors.append("expected final local card recommendation")

    if data["game_declaration"]["matadors"] != 2:
        errors.append("expected matadors inferred from completed-trick ownership")

    if data["game_value_summary"]["game_value"] != 72:
        errors.append("expected inferred grand game value 72")

    information_policy = data["information_policy_summary"]
    if information_policy["live_information_enforced"] is not True:
        errors.append("expected live information policy enforcement")

    if information_policy["unverifiable_completed_trick_winner_metadata_allowed"] is not False:
        errors.append("expected strict live completed-trick winner metadata")

    return errors


def check_defender_known_to_declarer_local_view(data: dict[str, Any]) -> list[str]:
    """
    Checks generated local-view output for declarer-private Skat cards.
    """
    errors = []

    if data["position"]["skat"] != []:
        errors.append("expected local defender position.skat to be redacted")

    strategic_metadata = data["analysis_metadata"]["strategic_metadata"]
    if strategic_metadata["skat_visibility"] != "known_to_declarer":
        errors.append("expected known_to_declarer strategic metadata")

    information_policy = data["information_policy_summary"]
    if information_policy["skat_visibility"] != "known_to_declarer":
        errors.append("expected known_to_declarer information policy summary")

    if information_policy["known_skat_cards_allowed"] is not True:
        errors.append("expected known Skat cards to be allowed for known_to_declarer")

    multi_step_result = data.get("multi_step_result")
    if not isinstance(multi_step_result, dict):
        errors.append("expected populated multi_step_result")
        return errors

    context_metadata = multi_step_result["context_summary"]["strategic_metadata"]
    if context_metadata["skat_visibility"] != "known_to_declarer":
        errors.append("expected known_to_declarer multi-step strategic metadata")

    if multi_step_result["final_state"]["skat"] != []:
        errors.append("expected local defender final_state.skat to be redacted")

    return errors


def check_historical_game_normal_completion(data: dict[str, Any]) -> list[str]:
    """Checks the complete normal-play historical-game output branch."""
    errors = []
    if set(data) != {"input_file", "historical_game_summary"}:
        errors.append("expected only the historical-game top-level output branch")
        return errors

    summary = data["historical_game_summary"]
    if summary["game_id"] != "historical-grand-001":
        errors.append("expected preserved historical game ID")
    if summary["status"] != "complete":
        errors.append("expected complete historical game status")
    if len(summary["derived_tricks"]) != 10:
        errors.append("expected ten derived historical tricks")
    if summary["declarer_points"] + summary["defender_points"] != 120:
        errors.append("expected final historical card points to total 120")
    if summary["record"]["declaration"]["matadors"] is None:
        errors.append("expected deterministic historical matador inference")
    if summary["final_settlement_summary"]["is_complete"] is not True:
        errors.append("expected complete historical final settlement")
    return errors


def check_historical_declarer_concession(data: dict[str, Any]) -> list[str]:
    """Checks exact-prefix historical concession adjudication and privacy."""
    errors = []
    if set(data) != {"input_file", "historical_game_summary"}:
        return ["expected only the historical-game top-level output branch"]
    summary = data["historical_game_summary"]
    if summary["record"]["game_end_reason"] != "declarer_concession":
        errors.append("expected historical declarer-concession record")
    if summary["play_prefix_summary"] != {
        "played_card_count": 14,
        "completed_trick_count": 4,
        "current_trick_card_count": 2,
        "remaining_hand_sizes": {"player-a": 5, "player-b": 5, "player-c": 6},
        "next_player_id": "player-c",
    }:
        errors.append("expected exact historical play-prefix summary")
    points = summary["point_accounting"]
    if (
        points["observed_declarer_points"]
        + points["observed_defender_points"]
        + points["total_unresolved_points"]
        != 120
    ):
        errors.append("expected observed and unresolved points to total 120")
    if summary["winner"] != "defenders":
        errors.append("expected adjudicated defender winner")
    if summary["final_settlement_summary"]["settlement_score"] != -96:
        errors.append("expected doubled declared Grand loss of -96")
    if "remaining_hands" in json.dumps(summary):
        errors.append("exact remaining hand cards must remain private")
    return errors


def check_historical_defender_concession(data: dict[str, Any]) -> list[str]:
    """Checks stable-ID joint-liability adjudication and prefix privacy."""
    if set(data) != {"input_file", "historical_game_summary"}:
        return ["expected only the historical-game top-level output branch"]
    summary = data["historical_game_summary"]
    end = summary["historical_game_end_summary"]
    points = summary["point_accounting"]
    errors = []
    if summary["record"]["game_end_reason"] != "defender_concession":
        errors.append("expected historical defender-concession record")
    if (
        end["conceding_defender_player_id"] != "player-a"
        or end["non_conceding_defender_player_id"] != "player-c"
        or end["liable_party"] != "defenders"
        or end["joint_liability"] is not True
    ):
        errors.append("expected stable defenders and joint defending-party liability")
    if summary["play_prefix_summary"]["played_card_count"] != 14:
        errors.append("expected exactly 14 actual prefix plays")
    if (
        points["observed_declarer_points"]
        + points["observed_defender_points"]
        + points["total_unresolved_points"]
        != 120
    ):
        errors.append("expected observed and unresolved points to total 120")
    if summary["winner"] != "declarer":
        errors.append("expected undecided defender concession to award declarer win")
    if summary["final_settlement_summary"]["settlement_score"] != 48:
        errors.append("expected simple declared Grand settlement of 48")
    serialized = json.dumps(summary)
    if "remaining_hands" in serialized:
        errors.append("exact remaining hand cards must remain private")
    return errors


def check_historical_declarer_card_exposure(data: dict[str, Any]) -> list[str]:
    """Checks exact accepted exposure adjudication and defender-hand privacy."""
    if set(data) != {"input_file", "historical_game_summary"}:
        return ["expected only the historical-game top-level output branch"]
    summary = data["historical_game_summary"]
    end = summary["historical_game_end_summary"]
    errors = []
    if summary["record"]["game_end_reason"] != "declarer_card_exposure":
        errors.append("expected historical declarer-card-exposure record")
    if summary["play_prefix_summary"]["played_card_count"] != 14:
        errors.append("expected exactly 14 actual prefix plays")
    if end["card_reconciliation"] != "confirmed":
        errors.append("expected exact exposed-card reconciliation")
    if end["accepting_defender_player_ids"] != ["player-a", "player-c"]:
        errors.append("expected canonical stable defender acceptance order")
    if summary["winner"] != "declarer":
        errors.append("expected accepted exposure to award the undecided game")
    if summary["final_settlement_summary"]["settlement_score"] != 72:
        errors.append("expected accepted Schneider Grand settlement of 72")
    serialized = json.dumps(summary)
    if "remaining_hands" in serialized:
        errors.append("defender remaining hands must remain private")
    return errors


def check_historical_defender_open_play(data: dict[str, Any]) -> list[str]:
    """Checks exact stable-ID open-play adjudication and proof privacy."""
    if set(data) != {"input_file", "historical_game_summary"}:
        return ["expected only the historical-game top-level output branch"]
    summary = data["historical_game_summary"]
    end = summary["historical_game_end_summary"]
    errors = []
    if summary["record"]["game_end_reason"] != "defender_open_play":
        errors.append("expected historical defender-open-play record")
    if summary["play_prefix_summary"]["played_card_count"] != 24:
        errors.append("expected exactly 24 actual prefix plays")
    if end["exposing_defender_player_id"] != "player-a":
        errors.append("expected stable exposing-defender identity")
    if end["exact_proof"]["status"] != "valid":
        errors.append("expected valid exact rest-trick proof")
    if end["exact_proof"]["evaluated_state_count"] != 32:
        errors.append("expected deterministic 32-state proof")
    if summary["point_accounting"]["assigned_defender_points"] != 13:
        errors.append("expected all 13 unresolved points assigned to defenders")
    if summary["final_settlement_summary"]["settlement_score"] != -144:
        errors.append("expected final Grand settlement of -144")
    serialized = json.dumps(summary)
    if any(identity in serialized for identity in ('"me"', '"left"', '"right"')):
        errors.append("historical proof output must use only stable player IDs")
    line = end["exact_proof"]["successful_line"]
    if any(
        move["card"] is not None
        for move in line
        if move["player_id"] != end["exposing_defender_player_id"]
    ):
        errors.append("private proof cards must be redacted")
    return errors


def check_historical_open_card_throw(data: dict[str, Any]) -> list[str]:
    """Checks stable-ID open-throw assignment, settlement, and privacy."""
    if set(data) != {"input_file", "historical_game_summary"}:
        return ["expected only the historical-game top-level output branch"]
    summary = data["historical_game_summary"]
    end = summary["historical_game_end_summary"]
    points = summary["point_accounting"]
    errors = []
    if summary["record"]["game_end_reason"] != "open_card_throw":
        errors.append("expected historical open-card-throw record")
    if summary["play_prefix_summary"]["played_card_count"] != 24:
        errors.append("expected exactly 24 actual prefix plays")
    if end["throwing_player_id"] != "player-a":
        errors.append("expected stable throwing-player identity")
    if end["thrown_cards"] != ["C7", "S10"]:
        errors.append("expected canonical exact thrown hand")
    if end["card_reconciliation"] != "confirmed":
        errors.append("expected confirmed exact hand reconciliation")
    if end["throwing_party"] != "defenders" or end["joint_liability"] is not True:
        errors.append("expected joint defending-party liability")
    if end["rest_tricks_recipient"] != "declarer":
        errors.append("expected unresolved tricks assigned to the opposing declarer")
    if points["assigned_declarer_points"] != 13:
        errors.append("expected all 13 unresolved points assigned to the declarer")
    if points["final_declarer_points"] + points["final_defender_points"] != 120:
        errors.append("expected final rule-assigned points to total 120")
    if sum(end["final_trick_counts"].values()) != 10:
        errors.append("expected completed and assigned tricks to total ten")
    serialized = json.dumps(summary)
    if "remaining_hands" in serialized or "exact_proof" in serialized:
        errors.append("private hands and exact future-play proof must not be emitted")
    if any(identity in serialized for identity in ('"me"', '"left"', '"right"')):
        errors.append("historical output must use only stable player IDs")
    return errors


def check_historical_party_wide_claim(data: dict[str, Any]) -> list[str]:
    """Checks exact Historical Claim proof, adjudication, and privacy."""
    if set(data) != {"input_file", "historical_game_summary"}:
        return ["expected only the historical-game top-level output branch"]
    summary = data["historical_game_summary"]
    end = summary["historical_game_end_summary"]
    proof = end["exact_proof"]
    adjudication = end["adjudication"]
    points = summary["point_accounting"]
    errors = []
    if summary["record"]["game_end_reason"] != (
        "party_wide_all_remaining_tricks_claim"
    ):
        errors.append("expected Historical party-wide Claim record")
    if proof["status"] != "valid" or proof["claim_satisfied"] is not True:
        errors.append("expected one complete valid exact Claim proof")
    if proof["representative_line_scope"] != (
        "diagnostic_decisive_branch_only"
    ):
        errors.append("expected diagnostic representative-line scope")
    if proof["assignment"]["recipient_party"] != end["claiming_party"]:
        errors.append("expected exact assignment to the claiming party")
    if adjudication["remaining_points_recipient"] != end["claiming_party"]:
        errors.append("expected adjudicated remaining points for the claiming party")
    if points["final_declarer_points"] + points["final_defender_points"] != 120:
        errors.append("expected final Claim points to total 120")
    if adjudication["final_declarer_tricks"] + adjudication["final_defender_tricks"] != 10:
        errors.append("expected final Claim Trick ownership to total ten")
    current = summary.get("incomplete_current_trick", {}).get("plays", [])
    current_cards = {play["card"] for play in current}
    line_cards = {move["card"] for move in proof["representative_line"]}
    if current_cards.intersection(line_cards):
        errors.append("current-Trick Cards must not repeat in the representative line")
    serialized_end = json.dumps(end)
    for private_field in (
        "remaining_hands",
        "exact_state",
        "memo_table",
        "universal_branch_certificate",
    ):
        if private_field in serialized_end:
            errors.append(f"Claim output must not expose {private_field}")
    events = summary.get("historical_game_events_summary")
    if events is not None and events["events"][0]["final_game_end_reason"] != (
        "party_wide_all_remaining_tricks_claim"
    ):
        errors.append("expected continuation to delegate to the final Claim")
    return errors


def check_historical_decision_snapshots(data: dict[str, Any]) -> list[str]:
    """Checks deterministic information-safe historical snapshot output."""
    errors = check_historical_game_normal_completion(data)
    snapshot_summary = data["historical_game_summary"].get("decision_snapshot_summary")
    if not isinstance(snapshot_summary, dict):
        errors.append("expected historical decision snapshot summary")
        return errors
    if snapshot_summary["information_policy"] != "decision_time":
        errors.append("expected decision-time information policy")
    if snapshot_summary["snapshot_count"] != 30:
        errors.append("expected exactly 30 historical decision snapshots")
    if [snapshot["decision_index"] for snapshot in snapshot_summary["snapshots"]] != list(
        range(1, 31)
    ):
        errors.append("expected ordered decision indices 1 through 30")
    return errors


def check_historical_defender_open_play_continuation_snapshots(
    data: dict[str, Any],
) -> list[str]:
    """Checks the timed public-hand transition and later known-card removal."""
    errors = []
    summary = data.get("historical_game_summary")
    if not isinstance(summary, dict):
        return ["expected historical game summary"]
    if summary["record"]["game_end_reason"] != "normal_completion":
        errors.append("expected continuation record to end by normal completion")
    events = summary.get("historical_game_events_summary", {}).get("events", [])
    if len(events) != 1:
        errors.append("expected exactly one historical continuation event")
        return errors
    event = events[0]
    if event["after_play_count"] != 12 or event["first_affected_decision_index"] != 13:
        errors.append("expected event boundary after play 12")
    if any(
        event[field]
        for field in ("exact_proof_applied", "game_end_applied", "settlement_applied")
    ):
        errors.append("continuation event must not apply proof, game end, or settlement")
    snapshots = summary.get("decision_snapshot_summary", {}).get("snapshots", [])
    if len(snapshots) != 30:
        errors.append("expected exactly 30 continued-play snapshots")
        return errors
    if snapshots[11]["visible_state"]["public_exposed_cards"]:
        errors.append("last pre-event snapshot must not expose the defender hand")
    first_public = snapshots[12]["visible_state"]["public_exposed_cards"]
    if first_public != [
        {
            "player_id": "player-a",
            "cards": ["CQ", "CJ", "C9", "C8", "C7", "S10"],
        }
    ]:
        errors.append("first post-event snapshot must contain the exact exposed hand")
    later_public = snapshots[13]["visible_state"]["public_exposed_cards"]
    if later_public != [
        {
            "player_id": "player-a",
            "cards": ["CJ", "C9", "C8", "C7", "S10"],
        }
    ]:
        errors.append("later snapshot must remove the exposing defender's played card")
    return errors


def check_historical_declarer_card_exposure_continuation_snapshots(
    data: dict[str, Any],
) -> list[str]:
    """Checks the timed public declarer-hand transition and card removal."""
    errors = []
    summary = data.get("historical_game_summary")
    if not isinstance(summary, dict):
        return ["expected historical game summary"]
    if summary["record"]["game_end_reason"] != "normal_completion":
        errors.append("expected continuation record to end by normal completion")
    events = summary.get("historical_game_events_summary", {}).get("events", [])
    if len(events) != 1:
        errors.append("expected exactly one historical continuation event")
        return errors
    event = events[0]
    if event["after_play_count"] != 12 or event["first_affected_decision_index"] != 13:
        errors.append("expected event boundary after play 12")
    if event["claimed_play_level_status"] != (
        "continuation_required_no_immediate_settlement_effect"
    ):
        errors.append("claimed level must remain non-settling provenance")
    if any(
        event[field]
        for field in ("exact_proof_applied", "game_end_applied", "settlement_applied")
    ):
        errors.append("continuation event must not apply proof, game end, or settlement")
    snapshots = summary.get("decision_snapshot_summary", {}).get("snapshots", [])
    if len(snapshots) != 30:
        errors.append("expected exactly 30 continued-play snapshots")
        return errors
    if snapshots[11]["visible_state"]["public_exposed_cards"]:
        errors.append("last pre-event snapshot must not expose the declarer hand")
    first_public = snapshots[12]["visible_state"]["public_exposed_cards"]
    if first_public != [
        {
            "player_id": "player-b",
            "cards": ["HA", "H10", "HK", "HQ", "D8", "D7"],
        }
    ]:
        errors.append("first post-event snapshot must contain the exact declarer hand")
    later_public = snapshots[14]["visible_state"]["public_exposed_cards"]
    if later_public != [
        {
            "player_id": "player-b",
            "cards": ["H10", "HK", "HQ", "D8", "D7"],
        }
    ]:
        errors.append("later snapshot must remove the declarer's played card")
    return errors


def check_historical_continuation_terminal_chain(data: dict[str, Any]) -> list[str]:
    """Checks separated continuation and terminal summaries at both chain boundaries."""
    errors = []
    summary = data.get("historical_game_summary")
    if not isinstance(summary, dict):
        return ["expected historical game summary"]
    events = summary.get("historical_game_events_summary", {}).get("events", [])
    end = summary.get("historical_game_end_summary")
    if len(events) != 1 or not isinstance(end, dict):
        return ["expected both continuation and terminal summaries"]
    event = events[0]
    if event["final_game_end_reason"] != end["kind"]:
        errors.append("expected continuation summary to name the terminal reason")
    if event["final_outcome_source"] != "subsequent_terminal_shortening":
        errors.append("expected subsequent terminal shortening outcome source")
    if any(
        event[field]
        for field in ("exact_proof_applied", "game_end_applied", "settlement_applied")
    ):
        errors.append("continuation must remain non-adjudicating")
    snapshots = summary.get("decision_snapshot_summary", {}).get("snapshots", [])
    if len(snapshots) != 14:
        errors.append("expected one snapshot for each of 14 actual card plays")
        return errors
    if event["kind"] == "defender_open_play_continuation":
        if event["after_play_count"] != 12 or event["actual_plays_after_event"] != 2:
            errors.append("expected two plays after the defender continuation")
        if snapshots[11]["visible_state"]["public_exposed_cards"]:
            errors.append("pre-continuation snapshot must not expose the defender hand")
        if snapshots[12]["visible_state"]["public_exposed_cards"] != [
            {
                "player_id": "player-a",
                "cards": ["CQ", "CJ", "C9", "C8", "C7", "S10"],
            }
        ]:
            errors.append("first post-continuation snapshot must expose the exact hand")
        if snapshots[13]["visible_state"]["public_exposed_cards"] != [
            {
                "player_id": "player-a",
                "cards": ["CJ", "C9", "C8", "C7", "S10"],
            }
        ]:
            errors.append("public defender hand must shrink after its actual play")
    else:
        if event["after_play_count"] != 14 or event["actual_plays_after_event"] != 0:
            errors.append("expected immediate terminal action at the exposure boundary")
        if any(
            snapshot["visible_state"]["public_exposed_cards"] for snapshot in snapshots
        ):
            errors.append("same-boundary terminal action must add no card-play snapshot")
    return errors


def check_historical_game_review(data: dict[str, Any]) -> list[str]:
    """Checks the deterministic complete historical decision review."""
    errors = check_historical_game_normal_completion(data)
    review = data["historical_game_summary"].get("historical_game_review_summary")
    if not isinstance(review, dict):
        errors.append("expected historical game review summary")
        return errors
    if review["decision_count"] != 30 or len(review["decisions"]) != 30:
        errors.append("expected exactly 30 historical review decisions")
    if review["reviewed_decision_count"] != 30:
        errors.append("expected all non-ouvert historical decisions to be reviewed")
    if review["unavailable_decision_count"] != 0:
        errors.append("expected no unavailable non-ouvert historical decisions")
    if review["settings"] != {
        "sample_count": 20,
        "base_random_seed": 42,
        "opponent_policy_mode": "default",
    }:
        errors.append("expected deterministic historical review settings")
    if [decision["effective_random_seed"] for decision in review["decisions"]] != list(
        range(42, 72)
    ):
        errors.append("expected historical decision seeds 42 through 71")
    if len(review["player_summaries"]) != 3 or any(
        player["decision_count"] != 10 for player in review["player_summaries"]
    ):
        errors.append("expected three ten-decision player summaries")
    if any(
        decision["actual_card_played"] not in decision["legal_cards"]
        or decision["recommendation"]["card"] is None
        or sum(row["card"] == decision["actual_card_played"] for row in decision["analysis_report"])
        != 1
        for decision in review["decisions"]
    ):
        errors.append("expected legal actual cards and complete candidate reviews")
    if sum(review["quality_counts"].values()) != 30:
        errors.append("expected historical review quality counts to reconcile")
    if any(len(decision["legal_cards"]) != 1 for decision in review["decisions"][-3:]):
        errors.append("expected final one-card decisions to remain reviewable")
    return errors


def check_historical_grand_ouvert_review(data: dict[str, Any]) -> list[str]:
    """Checks declared-Ouvert ownership and normal historical review."""
    if set(data) != {"input_file", "historical_game_summary"}:
        return ["expected only the historical-game top-level output branch"]
    summary = data["historical_game_summary"]
    review = summary.get("historical_game_review_summary")
    errors = []
    declaration = summary["record"]["declaration"]
    if summary["game_id"] != "historical-grand-ouvert-review-001":
        errors.append("expected preserved historical Grand Ouvert game ID")
    if summary["status"] != "complete" or len(summary["derived_tricks"]) != 10:
        errors.append("expected complete ten-trick historical Grand Ouvert game")
    if declaration != {
        "game_type": "grand",
        "hand_game": True,
        "ouvert": True,
        "schneider_announced": True,
        "schwarz_announced": True,
        "matadors": 1,
        "bid_value": 18,
    }:
        errors.append("expected canonical Grand Ouvert declaration with one matador")
    if summary["game_value_summary"]["game_value"] != 144:
        errors.append("expected unchanged Grand Ouvert game value of 144")
    if summary["final_settlement_summary"]["settlement_score"] != -288:
        errors.append("expected unchanged doubled Grand Ouvert loss of -288")
    if not isinstance(review, dict):
        errors.append("expected historical Grand Ouvert review summary")
        return errors
    if review["settings"] != {
        "sample_count": 20,
        "base_random_seed": 42,
        "opponent_policy_mode": "default",
    }:
        errors.append("expected deterministic Grand Ouvert review settings")
    if (
        review["decision_count"] != 30
        or review["reviewed_decision_count"] != 30
        or review["unavailable_decision_count"] != 0
        or len(review["decisions"]) != 30
    ):
        errors.append("expected all 30 Grand Ouvert decisions to be reviewed")
    if review["quality_counts"]["not_available"] != 0:
        errors.append("expected no Ouvert-only unavailable decisions")
    if [decision["effective_random_seed"] for decision in review["decisions"]] != list(
        range(42, 72)
    ):
        errors.append("expected Grand Ouvert decision seeds 42 through 71")
    if any(
        decision["status"] != "reviewed"
        or decision["unavailable_reason"] is not None
        or decision["recommendation"]["card"] is None
        or decision["actual_card_played"] not in decision["legal_cards"]
        or not decision.get("public_hand_constraints")
        or decision["public_hand_constraints"][0]["source"] != "declared_ouvert"
        for decision in review["decisions"]
    ):
        errors.append("expected reviewed decisions with declared-Ouvert constraints")
    first_public = review["decisions"][0].get("public_hand_constraints")
    if first_public != [
        {
            "player": "left",
            "source": "declared_ouvert",
            "visibility_scope": "all_players",
            "card_count": 10,
            "cards": ["SK", "SQ", "SJ", "S9", "S8", "S7", "HA", "H10", "HK", "HQ"],
        }
    ]:
        errors.append("expected exact initial public declarer hand in review context")
    first_decision = review["decisions"][0]
    if (
        first_decision["recommendation"]["card"] != "SA"
        or first_decision["post_game_review_summary"]["decision_quality"] != "mistake"
    ):
        errors.append("expected stable first Ouvert recommendation and decision quality")
    if len(review["player_summaries"]) != 3 or any(
        player["reviewed_decision_count"] != 10
        or player["unavailable_decision_count"] != 0
        for player in review["player_summaries"]
    ):
        errors.append("expected three reconciled ten-decision player summaries")
    return errors


def check_historical_opponent_profile_review(data: dict[str, Any]) -> list[str]:
    """Checks time-safe stable-ID profile application across historical decisions."""
    base_output = {
        key: value
        for key, value in data.items()
        if key != "historical_opponent_profile_application_summary"
    }
    errors = check_historical_game_normal_completion(base_output)
    application = data.get("historical_opponent_profile_application_summary")
    if not isinstance(application, dict):
        errors.append("expected historical opponent profile application summary")
        return errors
    if application["temporal_rule"] != "captured_at_strictly_before_played_at":
        errors.append("expected strict historical profile temporal rule")
    if application["matched_player_count"] != 2:
        errors.append("expected two exact historical participant matches")
    if application["unmatched_player_ids"] != ["player-b"]:
        errors.append("expected unmatched player-b coverage")

    review = data["historical_game_summary"]["historical_game_review_summary"]
    if review["settings"]["opponent_policy_mode"] != "external_profiles":
        errors.append("expected external historical opponent policy mode")
    counts = review.get("opponent_profile_application_counts")
    if not isinstance(counts, dict):
        errors.append("expected historical profile application counts")
        return errors
    if counts["application_counts_by_player_id"] != {
        "player-a": 20,
        "player-c": 20,
    }:
        errors.append("expected stable-player historical application counts")
    if any(
        decision["opponent_profile_application"]["acting_player_id"] != decision["acting_player_id"]
        or decision["acting_player_id"]
        in {
            decision["opponent_profile_application"]["left_opponent_player_id"],
            decision["opponent_profile_application"]["right_opponent_player_id"],
        }
        for decision in review["decisions"]
    ):
        errors.append("expected safe per-decision relative opponent identities")
    return errors


def check_training_dataset_normal_play(data: dict[str, Any]) -> list[str]:
    """Checks deterministic training dataset conversion and reconciliation."""
    errors = []
    if set(data) != {"input_file", "training_dataset_summary"}:
        errors.append("expected only the training-dataset top-level output branch")
        return errors
    summary = data["training_dataset_summary"]
    if summary["dataset_id"] != "online-games-2026" or summary["dataset_version"] != "1":
        errors.append("expected preserved training dataset identity and version")
    if summary["record_count"] != 2 or summary["sample_count"] != 60:
        errors.append("expected two training records and exactly 60 samples")
    if summary["partition_counts"] != {
        "train": {"record_count": 1, "sample_count": 30},
        "validation": {"record_count": 1, "sample_count": 30},
        "test": {"record_count": 0, "sample_count": 0},
    }:
        errors.append("expected reconciled train, validation, and test counts")
    record = summary["records"][0]
    if record["record_id"] != "record-001" or record["sample_count"] != 30:
        errors.append("expected preserved record identity and sample count")
    if record["source_game_id"] != "historical-grand-001":
        errors.append("expected preserved source game identity")
    samples = record["samples"]
    if [sample["sample_id"] for sample in samples] != [
        f"record-001:{index}" for index in range(1, 31)
    ]:
        errors.append("expected stable ordered training sample IDs")
    if any(
        sample["label"]["target"] != "actual_card_played"
        or sample["label"]["card"] not in sample["features"]["own_hand"]
        or sample["label"]["card"] not in sample["features"]["legal_cards"]
        for sample in samples
    ):
        errors.append("expected legal actual-card labels for every sample")
    forbidden_features = {
        "dataset_id",
        "record_id",
        "source_game_id",
        "player_id",
        "acting_player_id",
        "recommendation",
        "decision_quality",
        "final_settlement_summary",
    }

    def collect_keys(value: object) -> set[str]:
        if isinstance(value, dict):
            return set(value).union(*(collect_keys(item) for item in value.values()))
        if isinstance(value, list):
            return set().union(*(collect_keys(item) for item in value), set())
        return set()

    if any(forbidden_features.intersection(collect_keys(sample["features"])) for sample in samples):
        errors.append("expected identity-free, review-free training features")
    return errors


def check_training_dataset_variable_length(data: dict[str, Any]) -> list[str]:
    """Checks variable decision cardinality without terminal-event feature leakage."""
    errors = []
    if set(data) != {"input_file", "training_dataset_summary"}:
        return ["expected only the training-dataset top-level output branch"]
    summary = data["training_dataset_summary"]
    if summary["record_count"] != 1 or summary["sample_count"] != 14:
        errors.append("expected one shortened record and exactly 14 samples")
    if summary["partition_counts"] != {
        "train": {"record_count": 1, "sample_count": 14},
        "validation": {"record_count": 0, "sample_count": 0},
        "test": {"record_count": 0, "sample_count": 0},
    }:
        errors.append("expected variable partition sample reconciliation")
    record = summary["records"][0]
    if (
        record["historical_game"]["game_end_reason"] != "declarer_concession"
        or record["sample_count"] != 14
    ):
        errors.append("expected preserved concession provenance and 14 record samples")
    samples = record["samples"]
    if [sample["sample_id"] for sample in samples] != [
        f"concession-record-001:{index}" for index in range(1, 15)
    ]:
        errors.append("expected consecutive variable-length sample IDs")
    if any(
        sample["label"]["target"] != "actual_card_played"
        or sample["label"]["card"] not in sample["features"]["own_hand"]
        or sample["label"]["card"] not in sample["features"]["legal_cards"]
        for sample in samples
    ):
        errors.append("expected legal actual-card labels for shortened samples")
    forbidden = {
        "game_end",
        "game_end_reason",
        "defender_consent",
        "game_result_summary",
        "final_settlement_summary",
        "unresolved_points",
    }

    def collect_keys(value: object) -> set[str]:
        if isinstance(value, dict):
            return set(value).union(*(collect_keys(item) for item in value.values()))
        if isinstance(value, list):
            return set().union(*(collect_keys(item) for item in value), set())
        return set()

    if any(forbidden.intersection(collect_keys(sample["features"])) for sample in samples):
        errors.append("expected terminal-event-free variable-length training features")
    return errors


def check_historical_opponent_statistics(data: dict[str, Any]) -> list[str]:
    """Checks exact aggregation without training samples or policy application."""
    errors = []
    if set(data) != {
        "input_file",
        "historical_opponent_statistics_aggregation_summary",
    }:
        return ["expected only the historical aggregation output branch"]
    summary = data["historical_opponent_statistics_aggregation_summary"]
    if summary["source_record_count"] != 2 or summary["source_game_count"] != 2:
        errors.append("expected exactly two included historical games")
    if summary["player_count"] != 3:
        errors.append("expected exactly three aggregated stable players")
    if summary["selection"] != {
        "included_partitions": ["train", "validation"],
        "before": "2026-07-21T00:00:00Z",
        "excluded_record_counts_by_partition": {
            "train": 0,
            "validation": 0,
            "test": 0,
        },
        "excluded_record_count_by_temporal_cutoff": 0,
    }:
        errors.append("expected canonical explicit partition and strict-cutoff selection")
    if [record["player_id"] for record in summary["records"]] != [
        "player-a",
        "player-b",
        "player-c",
    ]:
        errors.append("expected first-appearance stable player order")
    declarer = summary["records"][1]
    if declarer["exact_counts"] != {
        "solo_games_played": 2,
        "solo_games_won": 1,
        "solo_hand_games": 0,
        "suit_games": 0,
        "grand_games": 2,
        "null_games": 0,
        "defender_games_played": 0,
        "defender_games_won": 0,
    }:
        errors.append("expected exact declarer role, result, and contract counts")
    if declarer["profile_derivation"]["confidence"]["declarer"]["evidence_kind"] != "exact":
        errors.append("expected exact declarer profile evidence")
    first_defender = summary["records"][0]
    if first_defender["exact_counts"]["defender_games_won"] != 1:
        errors.append("expected both defenders to receive the defender-side win")
    if first_defender["source"]["captured_at"] != "2026-07-20T19:00:00+02:00":
        errors.append("expected captured_at to equal the latest included player game")
    if "samples" in str(summary):
        errors.append("expected aggregation output without training samples")
    if "recommendation" in str(summary) or "policy_application" in str(summary):
        errors.append("expected aggregation without policy application or recommendations")
    return errors


def check_rolling_opponent_policy_evaluation(data: dict[str, Any]) -> list[str]:
    """Checks rolling selection, baseline coverage, and low-confidence behavior."""
    if set(data) != {"input_file", "rolling_opponent_policy_evaluation_summary"}:
        return ["expected only the rolling opponent-policy evaluation branch"]
    summary = data["rolling_opponent_policy_evaluation_summary"]
    errors = []
    if summary["selection"] != {
        "evaluation_mode": "known_opponent",
        "source_partitions": ["train"],
        "evaluation_partitions": ["validation", "test"],
        "temporal_rule": "source_played_at_strictly_before_target_played_at",
        "selected_partition_player_overlap": {
            "source_distinct_player_count": 3,
            "evaluation_distinct_player_count": 3,
            "shared_player_count": 3,
            "shared_player_ids": ["player-a", "player-b", "player-c"],
            "eligibility_basis": "partition_membership_only_not_temporal_eligibility",
        },
        "source_record_count": 1,
        "target_record_count": 1,
        "target_game_count": 1,
        "target_decision_count": 30,
    }:
        errors.append("expected default disjoint partitions and strict rolling selection")
    coverage = summary["coverage"]
    if (
        coverage["target_decisions"] != 30
        or coverage["decisions_with_insufficient_confidence"] != 30
    ):
        errors.append("expected 30 low-confidence target decisions")
    baseline = summary["baseline_results"]
    if baseline["baseline_policy_preset"] != "simple_lowest" or baseline["decision_count"] != 30:
        errors.append("expected immutable simple_lowest baseline on all decisions")
    paired = summary["actionable_profile_paired_results"]
    if (
        paired["paired_decision_count"] != 0
        or paired["profile_preferred_card_match_rate"] is not None
    ):
        errors.append("expected valid null paired rates without actionable profiles")
    target = summary["target_games"][0]
    if target["as_of_source_game_count"] != 1:
        errors.append("expected exactly one strictly earlier source game")
    if target["participant_ids"] != ["player-b", "player-c", "player-a"]:
        errors.append("expected stable identities in changed target seats")
    if len(target["decisions"]) != 30 or any(
        decision["profile_prediction"] is not None
        or decision["baseline_prediction"]["predicted_card"]
        not in decision["baseline_prediction"]["preferred_cards"]
        for decision in target["decisions"]
    ):
        errors.append("expected 30 baseline-only policy-equivalent predictions")
    if "recommendation" in str(summary) or "expected_point" in str(summary):
        errors.append("expected behavioral evaluation without recommendation or simulation")
    return errors


def check_shortened_rolling_opponent_policy_evaluation(
    data: dict[str, Any],
) -> list[str]:
    """Checks mixed sources and one variable-cardinality concession target."""
    if set(data) != {"input_file", "rolling_opponent_policy_evaluation_summary"}:
        return ["expected only the shortened rolling evaluation branch"]
    summary = data["rolling_opponent_policy_evaluation_summary"]
    selection = summary["selection"]
    coverage = summary["coverage"]
    baseline = summary["baseline_results"]
    paired = summary["actionable_profile_paired_results"]
    errors = []
    if (
        selection["source_record_count"] != 2
        or selection["target_record_count"] != 1
        or selection["target_game_count"] != 1
        or selection["target_decision_count"] != 14
    ):
        errors.append("expected two mixed sources and one 14-decision target")
    overlap = selection["selected_partition_player_overlap"]
    if overlap["shared_player_ids"] != ["player-a", "player-b", "player-c"]:
        errors.append("expected all stable target participants in source membership")
    if (
        coverage["target_game_count"] != 1
        or coverage["target_player_game_count"] != 3
        or coverage["distinct_target_player_count"] != 3
        or coverage["target_decisions"] != 14
        or coverage["decisions_with_insufficient_confidence"] != 14
    ):
        errors.append("expected participant-based coverage over 14 actual decisions")
    if baseline["baseline_policy_preset"] != "simple_lowest" or baseline[
        "decision_count"
    ] != 14:
        errors.append("expected the unchanged baseline on all actual decisions")
    if (
        paired["paired_decision_count"] != 0
        or paired["profile_preferred_card_match_rate"] is not None
    ):
        errors.append("expected nullable paired rates for low-confidence profiles")
    target = summary["target_games"][0]
    decisions = target["decisions"]
    if (
        target["as_of_source_game_count"] != 2
        or target["decision_count"] != 14
        or len(decisions) != 14
        or [decision["decision_index"] for decision in decisions] != list(range(1, 15))
    ):
        errors.append("expected two as-of games and 14 consecutive target decisions")
    if target["baseline_results"]["decision_count"] != 14:
        errors.append("expected per-target baseline reconciliation")
    if not all(
        profile["source_game_count"] == 2 for profile in target["player_as_of_profiles"]
    ):
        errors.append("expected both source games in every recurring-player profile")
    if (
        sum(game["decision_count"] for game in summary["target_games"])
        != selection["target_decision_count"]
        or selection["target_decision_count"] != coverage["target_decisions"]
        or coverage["target_decisions"] != baseline["decision_count"]
    ):
        errors.append("expected actual target decision totals to reconcile")
    decision_fields = {field_name for decision in decisions for field_name in decision}
    if decision_fields.intersection(
        {
            "game_end_reason",
            "concession_status",
            "defender_consent",
            "winner",
            "final_settlement_summary",
            "unresolved_points",
            "remaining_cards",
        }
    ):
        errors.append("expected terminal-event and hidden-result isolation")
    return errors


def check_dataset_partition_audit(data: dict[str, Any]) -> list[str]:
    """Checks deterministic membership, overlap, coverage, and output isolation."""
    if set(data) != {"input_file", "dataset_partition_audit_summary"}:
        return ["expected only the dataset partition audit output branch"]
    summary = data["dataset_partition_audit_summary"]
    errors = []
    if summary["declared_partition_policy"] is not None:
        errors.append("expected the audit example to leave partition intent unspecified")
    if summary["effective_audit_mode"] != "known_opponent":
        errors.append("expected explicit known_opponent audit mode")
    if summary["compliance_status"] != "compliant":
        errors.append("expected structurally valid known-opponent compliance")
    if summary["source_dataset"]["total_historical_game_count"] != 3:
        errors.append("expected exactly three historical games")
    if summary["partition_summary"]["train"]["record_count"] != 1:
        errors.append("expected one train record")
    if summary["partition_summary"]["validation"]["record_count"] != 1:
        errors.append("expected one validation record")
    if summary["partition_summary"]["test"]["record_count"] != 1:
        errors.append("expected one test record")
    if summary["overlap_summary"]["train_validation_test"]["player_ids"] != [
        "player-a",
        "player-b",
        "player-c",
    ]:
        errors.append("expected all three stable players in the three-way overlap")
    if summary["known_opponent_coverage"]["train_to_validation"]["shared_player_count"] != 3:
        errors.append("expected complete train-to-validation player coverage")
    if (
        summary["known_opponent_coverage"]["train_to_validation"][
            "target_game_count_with_all_three_participants_previously_seen"
        ]
        != 1
    ):
        errors.append("expected one target game with all participants in train")
    if summary["unseen_player_compliance"]["violating_player_count"] != 3:
        errors.append("expected three deterministic unseen-player violations")
    if len(summary["players"]) != 3:
        errors.append("expected complete three-player membership output")
    forbidden = ("samples", "recommendation", "simulation", "model")
    if any(value in str(summary) for value in forbidden):
        errors.append("expected audit output without samples or analysis products")
    return errors


def check_opponent_statistics(data: dict[str, Any]) -> list[str]:
    """Checks deterministic external-statistics normalization and derivation."""
    errors = []
    if set(data) != {"input_file", "opponent_statistics_summary"}:
        errors.append("expected only the opponent-statistics top-level output branch")
        return errors
    summary = data["opponent_statistics_summary"]
    if summary["schema_version"] != 1 or summary["record_count"] != 2:
        errors.append("expected version 1 output with two records")
    if [record["player_id"] for record in summary["records"]] != [
        "opponent-123",
        "opponent-789",
    ]:
        errors.append("expected preserved opponent input order and identity")
    first_record = summary["records"][0]
    if first_record["source"] != {
        "source_type": "online_platform",
        "source_name": "Example platform",
        "source_player_id": "platform-user-456",
        "captured_at": "2026-07-23T12:00:00+02:00",
    }:
        errors.append("expected unchanged source provenance")
    if first_record["statistics"]["solo_games_played_percent"] != 31:
        errors.append("expected unchanged percentage-point statistics")
    profile = first_record["normalized_profile_statistics"]
    if (
        profile["solo_rate"] != 0.31
        or profile["defender_rate"] != 0.69
        or profile["defender_win_rate"] != 0.64
    ):
        errors.append("expected normalized PlayerProfile rates")
    if profile["solo_games_played"] is not None:
        errors.append("expected no invented declarer game count")
    if profile["defender_games_played"] is not None:
        errors.append("expected no invented defender game count")
    if first_record["validation_metadata"] != {"percentage_sum_tolerance_points": 2.0}:
        errors.append("expected fixed percentage-sum tolerance metadata")
    derivation = first_record["profile_derivation"]
    if derivation["profile_derivation_version"] != 1:
        errors.append("expected profile derivation version 1")
    if derivation["classification"] != "cautious_defender":
        errors.append("expected a distinct actionable cautious-defender profile")
    if derivation["actionable_policy_preset"] != "cautious_defender":
        errors.append("expected an actionable cautious_defender preset")
    second_derivation = summary["records"][1]["profile_derivation"]
    if second_derivation["classification"] != "aggressive":
        errors.append("expected a distinct actionable aggressive profile")
    if second_derivation["actionable_policy_preset"] != "aggressive_points":
        errors.append("expected an actionable aggressive_points preset")
    forbidden_keys = {"recommendation", "simulation"}
    if forbidden_keys.intersection(first_record):
        errors.append("expected no recommendation or simulation output")
    return errors


def check_live_external_opponent_profiles(data: dict[str, Any]) -> list[str]:
    """Checks exact two-sided live external-profile application."""
    errors = []
    summary = data.get("opponent_profile_application_summary")
    if not isinstance(summary, dict):
        return ["expected opponent_profile_application_summary"]
    if summary["left"]["bound_player_id"] != "opponent-123":
        errors.append("expected exact left external player binding")
    if summary["right"]["bound_player_id"] != "opponent-789":
        errors.append("expected exact right external player binding")
    if summary["left"]["applied_policy_preset"] != "cautious_defender":
        errors.append("expected applied left cautious_defender preset")
    if summary["right"]["applied_policy_preset"] != "aggressive_points":
        errors.append("expected applied right aggressive_points preset")
    if data["left_opponent_policy_settings"] != {
        "opponent_lead_policy": summary["left"]["effective_lead_policy"],
        "opponent_response_policy": summary["left"]["effective_response_policy"],
    }:
        errors.append("expected reconciled left effective policies")
    if data["right_opponent_policy_settings"] != {
        "opponent_lead_policy": summary["right"]["effective_lead_policy"],
        "opponent_response_policy": summary["right"]["effective_response_policy"],
    }:
        errors.append("expected reconciled right effective policies")
    if "statistics" in summary["left"]["external_profile"]:
        errors.append("expected no copied source statistics")
    return errors


def check_hidden_card_inference(data: dict[str, Any]) -> list[str]:
    """Checks exact evidence-constrained counting, sampling, and privacy."""
    errors = []
    summary = data.get("hidden_card_inference_summary")
    multi_step = data.get("multi_step_result")
    if not isinstance(summary, dict):
        return ["expected top-level hidden_card_inference_summary"]
    if not isinstance(multi_step, dict):
        return ["expected evidence-constrained multi_step_result"]
    if summary.get("compatible_world_count") != 275275:
        errors.append("expected exactly 275275 compatible root worlds")
    if summary.get("confirmed_voids") != [
        {"player": "right", "forbidden_effective_categories": ["clubs"]}
    ]:
        errors.append("expected confirmed right-player Clubs void evidence")
    estimates = summary.get("ownership_estimates", [])
    if not any(
        estimate["ownership_probability"]["right"] == 0.0
        for estimate in estimates
    ):
        errors.append("expected at least one impossible right-owner marginal")
    if not any(estimate["confidence"] != "confirmed" for estimate in estimates):
        errors.append("expected at least one bounded non-confirmed estimate")
    if summary.get("confidence_is_calibrated") is not False:
        errors.append("expected explicitly non-calibrated confidence")
    if multi_step.get("hidden_card_inference_summary") != summary:
        errors.append("expected Multi-Step to use the equivalent root evidence model")
    if multi_step["context_summary"]["hidden_world"]["ownership_violation_detected"]:
        errors.append("expected compatible coherent root ownership")
    if not any(
        step.get("hidden_card_inference_summary", {}).get(
            "confirmed_void_evidence_count", 0
        )
        > summary["confirmed_void_evidence_count"]
        for step in multi_step["steps"]
    ):
        errors.append("expected later simulated public evidence progression")

    forbidden_keys = {
        "left_hand",
        "right_hand",
        "sampled_hypothetical_skat",
        "coherent_root_ownership",
        "dynamic_programming_table",
        "actual_historical_hidden_hands",
    }

    def collect_keys(value: Any) -> set[str]:
        if isinstance(value, dict):
            return set(value).union(
                *(collect_keys(item) for item in value.values()),
            )
        if isinstance(value, list):
            return set().union(*(collect_keys(item) for item in value))
        return set()

    emitted_forbidden_keys = collect_keys(data).intersection(forbidden_keys)
    if emitted_forbidden_keys:
        errors.append(
            f"expected no private hidden ownership keys, got {sorted(emitted_forbidden_keys)}"
        )
    if any(summary["privacy_flags"].values()):
        errors.append("expected every hidden-card inference privacy flag to be false")
    return errors


def check_complete_bounded_search(data: dict[str, Any]) -> list[str]:
    errors = []
    summary = data.get("recommendation_method_summary")
    search = data.get("bounded_search_result")
    if summary != {
        "requested_method": "bounded_search",
        "effective_method": "compatible_world_minimax_v1",
        "search_attempted": True,
        "fallback_used": False,
        "fallback_method": None,
        "analysis_report_method": "none",
    }:
        errors.append("expected strict bounded-Search method summary")
    if not isinstance(search, dict):
        return [*errors, "expected bounded_search_result"]
    if search["status"] != "complete" or search["world_coverage"] != "all_compatible_worlds":
        errors.append("expected complete exhaustive bounded Search")
    if search["consumed_budget"]["selected_world_count"] != 1:
        errors.append("expected one selected exhaustive world")
    if search["consumed_budget"]["completed_world_count"] != 1:
        errors.append("expected one completed exhaustive world")
    if data["recommendation"]["card"] != search["recommended_card"]:
        errors.append("expected top-level Search recommendation consistency")
    if data["analysis_report"] != []:
        errors.append("expected no Immediate report for effective Search")
    if data["settings"]["bounded_search_settings"]["random_seed"] != 113:
        errors.append("expected independent explicit Search seed")
    if "child_seed" in repr(data) or "exact_states" in repr(data):
        errors.append("expected no derived seed or private Search state")
    return errors


def check_auto_search_fallback(data: dict[str, Any]) -> list[str]:
    errors = []
    summary = data.get("recommendation_method_summary")
    search = data.get("bounded_search_result")
    if summary != {
        "requested_method": "auto",
        "effective_method": "immediate_expected_value",
        "search_attempted": True,
        "fallback_used": True,
        "fallback_method": "immediate_expected_value",
        "analysis_report_method": "immediate_expected_value",
    }:
        errors.append("expected auto Immediate-fallback method summary")
    if not isinstance(search, dict):
        return [*errors, "expected auto bounded_search_result"]
    if search["status"] != "partial" or search["stop_reason"] != "node_budget_exhausted":
        errors.append("expected node-limited Search fallback trigger")
    if search["recommended_card"] is not None:
        errors.append("expected Search result to retain no recommendation")
    if not search["fallback_used"] or search["fallback_method"] != "immediate_expected_value":
        errors.append("expected Search fallback marker")
    if data["recommendation"]["card"] is None:
        errors.append("expected top-level Immediate fallback card")
    if not data["analysis_report"] or not data["analysis_report"][0]["is_recommended"]:
        errors.append("expected unchanged Immediate fallback report")
    return errors


def check_search_aware_multi_step(data: dict[str, Any]) -> list[str]:
    errors = []
    result = data.get("multi_step_result")
    if not isinstance(result, dict):
        return ["expected Search-aware multi_step_result"]
    if result["card_selection_policy"] != "bounded_search":
        errors.append("expected bounded_search Multi-Step policy")
    if result["steps_simulated"] != 1 or len(result["steps"]) != 1:
        errors.append("expected one executed Search-aware decision")
        return errors
    step = result["steps"][0]
    decision = step.get("recommendation_decision")
    if not isinstance(decision, dict):
        return [*errors, "expected recommendation_decision"]
    if decision["recommendation_card"] != step["candidate_card"]:
        errors.append("expected decision and executed card to match")
    if decision["bounded_search_result"]["recommended_card"] != step["candidate_card"]:
        errors.append("expected nested Search and executed card to match")
    expected_summary = {
        "requested_method": "bounded_search",
        "decisions_attempted": 1,
        "decisions_executed": 1,
        "search_recommendations_used": 1,
        "immediate_fallbacks_used": 0,
        "no_recommendation_count": 0,
    }
    for key, value in expected_summary.items():
        if result["summary"].get(key) != value:
            errors.append(f"expected Multi-Step Search summary {key}={value}")
    if "child_seed" in repr(result) or "exact_states" in repr(result):
        errors.append("expected no child seed or private Search states")
    return errors


def check_search_inclusive_policy_comparison(data: dict[str, Any]) -> list[str]:
    errors = check_search_aware_multi_step(data)
    comparison = data.get("policy_comparison_result")
    if not isinstance(comparison, dict):
        return [*errors, "expected Search-inclusive policy_comparison_result"]
    expected_policies = [
        "first_legal",
        "lowest_point",
        "highest_point",
        "highest_expected_value",
        "bounded_search",
    ]
    if comparison["policies"] != expected_policies:
        errors.append("expected four legacy policies followed by bounded_search")
    rows = [
        row
        for row in comparison["policy_results"]
        if row["policy"] == "bounded_search"
    ]
    if len(rows) != 1:
        return [*errors, "expected exactly one bounded_search policy row"]
    search_row = rows[0]
    if not search_row["eligible_for_recommendation"]:
        errors.append("expected completed Search policy to remain eligible")
    if search_row["ineligible_reason"] is not None:
        errors.append("expected no ineligibility reason for completed Search")
    if search_row["recommendation_summary"]["search_recommendations_used"] != 1:
        errors.append("expected one Search recommendation in comparison summary")
    diagnostics = search_row["search_decision_diagnostics"]
    if len(diagnostics) != 1 or diagnostics[0]["recommendation_card"] != "D7":
        errors.append("expected one compact Search decision diagnostic")
    return errors


def check_bounded_search_post_game_review(data: dict[str, Any]) -> list[str]:
    summary = data.get("bounded_search_post_game_review_summary")
    if not isinstance(summary, dict):
        return ["expected bounded_search_post_game_review_summary"]
    errors = []
    actual = summary["search_actual_card_comparison"]
    comparison = summary["search_vs_immediate_comparison"]
    if not actual["is_available"] or actual["actual_card"] != "D7":
        errors.append("expected available Search actual-card comparison for D7")
    if not comparison["is_available"] or comparison["search_aggregate_relation"] not in {
        "search_better",
        "aggregate_equivalent",
    }:
        errors.append("expected available Search-versus-Immediate comparison")
    if not data["post_game_review_summary"]["is_available"]:
        errors.append("expected unchanged Immediate post-game review to remain available")
    return errors


def check_historical_search_review(data: dict[str, Any]) -> list[str]:
    review = data["historical_game_summary"].get("historical_search_review_summary")
    if not isinstance(review, dict):
        return ["expected historical_search_review_summary"]
    errors = []
    counts = review["decision_counts"]
    if counts["decision_count"] != 30 or counts["search_attempted_count"] != 30:
        errors.append("expected all 30 historical decisions to attempt Search")
    if counts["search_available_decision_count"] == 0:
        errors.append("expected at least one late eligible Search decision")
    if counts["search_unavailable_decision_count"] == 0:
        errors.append("expected early out-of-profile Search decisions")
    if review["quality_gate"]["quality_violation_count"] != 0:
        errors.append("expected no Search-not-worse quality violations")
    if any("random_seed" in decision["bounded_search_result"] for decision in review["decisions"]):
        errors.append("derived Search seeds must not be serialized")
    return errors


def _collect_property_names(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value).union(
            *(_collect_property_names(item) for item in value.values())
        )
    if isinstance(value, list):
        return set().union(*(_collect_property_names(item) for item in value))
    return set()


def check_historical_replay_coaching(data: dict[str, Any]) -> list[str]:
    summary = data["historical_game_summary"].get(
        "historical_replay_coaching_summary"
    )
    if not isinstance(summary, dict):
        return ["expected historical_replay_coaching_summary"]
    errors = []
    coverage = summary["coverage_summary"]
    prioritization = summary["prioritization"]
    guidance = summary["guidance"]
    if summary["report_version"] != 1:
        errors.append("expected Replay Coaching report version 1")
    if summary["report_method"] != "historical_replay_coaching_v1":
        errors.append("expected historical_replay_coaching_v1 method")
    if summary["information_policy"] != (
        "decision_time_then_retrospective_attachment"
    ):
        errors.append("expected decision-time then retrospective information policy")
    if summary["outcome_context_policy"] != "final_context_after_coaching":
        errors.append("expected final outcome context after coaching")
    if coverage["decision_count"] != len(summary["decision_assessments"]):
        errors.append("expected decision coverage to match assessments")
    if coverage["key_decision_count"] != len(prioritization["key_decisions"]):
        errors.append("expected Key Decision coverage to reconcile")
    if coverage["turning_point_count"] != len(prioritization["turning_points"]):
        errors.append("expected Turning Point coverage to reconcile")
    if coverage["pattern_count"] != len(guidance["patterns"]):
        errors.append("expected pattern coverage to reconcile")
    if coverage["decision_recommendation_count"] != len(
        guidance["decision_recommendations"]
    ):
        errors.append("expected decision recommendations to reconcile")
    if coverage["pattern_recommendation_count"] != len(
        guidance["pattern_recommendations"]
    ):
        errors.append("expected pattern recommendations to reconcile")
    if tuple(
        len(summary[field])
        for field in (
            "player_summaries",
            "role_summaries",
            "phase_summaries",
            "contract_summaries",
        )
    ) != (3, 2, 3, 1):
        errors.append("expected complete player, role, phase, and contract summaries")
    if summary["outcome_context"]["source_game_id"] != summary["source_game_id"]:
        errors.append("expected retrospective outcome source identity")
    if any(
        "random_seed" in row["decision_time_evidence"]["bounded_search_result"]
        for row in summary["decision_assessments"]
    ):
        errors.append("derived Search seeds must not be serialized")
    prohibited_properties = {
        "initial_hand",
        "initial_hands",
        "final_hidden_hands",
        "skat",
        "discarded_cards",
        "remaining_hands",
        "private_remaining_hands",
        "selected_worlds",
        "ownership_assignments",
        "exact_search_states",
        "derived_child_seed",
        "caches",
        "branches",
        "principal_variations",
        "proof_internals",
        "ratings",
        "grades",
        "rankings",
    }
    leaked = sorted(prohibited_properties.intersection(_collect_property_names(summary)))
    if leaked:
        errors.append(f"Replay Coaching report exposed private properties: {leaked}")
    serialized = json.dumps(summary).lower()
    for prohibited_claim in (
        "caused the final outcome",
        "certain counterfactual victory",
        "player weakness",
        "permanent trait",
        "statistical significance",
        "perfect play",
        "optimal hidden-information play",
    ):
        if prohibited_claim in serialized:
            errors.append(f"unexpected coaching claim: {prohibited_claim}")
    return errors


def check_historical_grand_replay_coaching(data: dict[str, Any]) -> list[str]:
    errors = check_historical_replay_coaching(data)
    historical = data["historical_game_summary"]
    summary = historical["historical_replay_coaching_summary"]
    if "historical_search_review_summary" not in historical:
        errors.append("expected shared public Historical Search Review summary")
    if not summary["prioritization"]["key_decisions"]:
        errors.append("expected at least one Key Decision")
    if not summary["prioritization"]["turning_points"]:
        errors.append("expected at least one Turning Point")
    if not summary["guidance"]["decision_recommendations"]:
        errors.append("expected at least one decision recommendation")
    if not summary["guidance"]["patterns"]:
        errors.append("expected one-game patterns")
    return errors


def check_historical_null_replay_coaching(data: dict[str, Any]) -> list[str]:
    errors = check_historical_replay_coaching(data)
    historical = data["historical_game_summary"]
    summary = historical["historical_replay_coaching_summary"]
    if "historical_search_review_summary" in historical:
        errors.append("Coaching-only workflow must not emit Historical Search Review")
    if summary["game_context"]["game_type"] != "null":
        errors.append("expected Null Replay Coaching context")
    recommendations = [
        *summary["guidance"]["decision_recommendations"],
        *summary["guidance"]["pattern_recommendations"],
    ]
    if any("card-point margin" in item["action"] for item in recommendations):
        errors.append("Null must not receive card-point-margin recommendation wording")
    if any(
        item["recommendation_type"] == "prefer_higher_card_point_margin"
        for item in summary["guidance"]["decision_recommendations"]
    ):
        errors.append("Null must not receive a margin recommendation")
    return errors


def check_historical_shortened_replay_coaching(data: dict[str, Any]) -> list[str]:
    errors = check_historical_replay_coaching(data)
    historical = data["historical_game_summary"]
    summary = historical["historical_replay_coaching_summary"]
    if historical["decision_snapshot_summary"]["snapshot_count"] != 14:
        errors.append("expected 14 shortened-game decision snapshots")
    if summary["coverage_summary"]["decision_count"] != 14:
        errors.append("expected 14 shortened-game coaching decisions")
    outcome = summary["outcome_context"]
    if outcome["game_end_reason"] != "declarer_concession":
        errors.append("expected retrospective declarer-concession context")
    events = outcome.get("historical_game_events_summary", {}).get("events", [])
    if len(events) != 1 or events[0].get("kind") != (
        "defender_open_play_continuation"
    ):
        errors.append("expected redacted continuation context before shortening")
    return errors


def check_bounded_search_evaluation(data: dict[str, Any]) -> list[str]:
    summary = data.get("bounded_search_evaluation_summary")
    if not isinstance(summary, dict):
        return ["expected bounded_search_evaluation_summary"]
    errors = []
    if summary["selection"]["partitions"] != ["validation", "test"]:
        errors.append("expected default validation/test evaluation partitions")
    if summary["decision_counts"]["decision_count"] != 1:
        errors.append("expected deterministic one-decision evaluation prefix")
    if summary["quality_gate"]["quality_violation_count"] != 0:
        errors.append("expected no Search-not-worse quality violations")
    if summary["record_count"] != 1:
        errors.append("expected one selected validation record")
    return errors


_INFORMATION_SET_PRIVATE_FIELDS = {
    "controlled_policy",
    "policy_table",
    "observation",
    "observations",
    "actor_observation",
    "hand",
    "own_hand",
    "state",
    "exact_state",
    "world_id",
    "world_identity",
    "world_state",
    "selected_worlds",
    "memoization",
    "memoization_cache",
}


def _check_information_set_public_surface(value: Any) -> list[str]:
    leaked = sorted(
        _INFORMATION_SET_PRIVATE_FIELDS.intersection(_collect_property_names(value))
    )
    return (
        [f"information-set Search output exposed private fields: {leaked}"]
        if leaked
        else []
    )


def check_information_set_search_live_complete(data: dict[str, Any]) -> list[str]:
    search = data.get("information_set_search_result")
    if not isinstance(search, dict):
        return ["expected information_set_search_result"]
    errors = _check_information_set_public_surface(search)
    if data.get("bounded_search_result") is not None:
        errors.append("expected bounded_search_result to remain null")
    if "information_set_search_comparison" in data:
        errors.append("live Search must not emit a retrospective comparison")
    if search["status"] != "complete" or search["stop_reason"] != "completed":
        errors.append("expected complete information-set Search")
    if search["world_coverage"] != "all_compatible_worlds":
        errors.append("expected exhaustive compatible-world coverage")
    if search["recommended_card"] != data["recommendation"]["card"]:
        errors.append("expected top-level and information-set recommendations to match")
    if data["recommendation_method_summary"] != {
        "requested_method": "information_set_search",
        "effective_method": "bounded_information_set_policy_search_v1",
        "search_attempted": True,
        "fallback_used": False,
        "fallback_method": None,
        "analysis_report_method": "none",
    }:
        errors.append("expected strict information-set Search method summary")
    return errors


def check_information_set_search_post_game_comparison(
    data: dict[str, Any],
) -> list[str]:
    errors = check_information_set_search_live_complete(data)
    if "live Search must not emit a retrospective comparison" in errors:
        errors.remove("live Search must not emit a retrospective comparison")
    comparison = data.get("information_set_search_comparison")
    if not isinstance(comparison, dict):
        return [*errors, "expected information_set_search_comparison"]
    errors.extend(_check_information_set_public_surface(comparison))
    if comparison["comparison_status"] != "available":
        errors.append("expected available same-selection comparison")
    if comparison["same_selected_world_sequence"] is not True:
        errors.append("expected one shared selected-world sequence")
    if comparison["actual_card"] != "D7":
        errors.append("expected retrospective actual Card D7")
    if comparison["information_set_pimc_same_card"] is not True:
        errors.append("expected information-set and PIMC recommendation agreement")
    return errors


def check_historical_information_set_search_review(data: dict[str, Any]) -> list[str]:
    review = data["historical_game_summary"].get(
        "historical_information_set_search_review_summary"
    )
    if not isinstance(review, dict):
        return ["expected historical_information_set_search_review_summary"]
    errors = _check_information_set_public_surface(review)
    if review["decision_count"] != 30 or len(review["decisions"]) != 30:
        errors.append("expected all 30 historical decisions")
    if sum(review["status_counts"].values()) != review["decision_count"]:
        errors.append("expected exact information-set status reconciliation")
    if sum(review["coverage_counts"].values()) != review["decision_count"]:
        errors.append("expected exact information-set coverage reconciliation")
    if not review["comparison_available_count"]:
        errors.append("expected at least one available late-game comparison")
    if not review["comparison_unavailable_count"]:
        errors.append("expected unavailable early-game comparisons")
    return errors


def check_historical_information_set_replay_coaching(
    data: dict[str, Any],
) -> list[str]:
    historical = data.get("historical_game_summary")
    if not isinstance(historical, dict):
        return ["expected historical_game_summary"]
    report = historical.get(
        "historical_information_set_replay_coaching_summary"
    )
    if not isinstance(report, dict):
        return ["expected historical_information_set_replay_coaching_summary"]
    errors = _check_information_set_public_surface(report)
    coverage = report["coverage"]
    prioritization = report["prioritization"]
    guidance = report["guidance"]
    if report["report_method"] != (
        "historical_information_set_replay_coaching_v1"
    ):
        errors.append("expected historical Information-set Replay Coaching method")
    if report["source_review_method"] != (
        "information_set_search_with_same_selection_pimc_and_immediate_v1"
    ):
        errors.append("expected retained Historical Information-set Review method")
    if coverage["decision_count"] != len(report["assessments"]):
        errors.append("expected Information-set Coaching decision coverage")
    if coverage["key_decision_count"] != len(prioritization["key_decisions"]):
        errors.append("expected Information-set Coaching Key Decision coverage")
    if coverage["turning_point_count"] != len(prioritization["turning_points"]):
        errors.append("expected Information-set Coaching Turning Point coverage")
    if coverage["pattern_count"] != len(guidance["patterns"]):
        errors.append("expected Information-set Coaching pattern coverage")
    if tuple(
        len(report[field])
        for field in (
            "player_summaries",
            "role_summaries",
            "phase_summaries",
            "contract_summaries",
        )
    ) != (3, 2, 3, 1):
        errors.append("expected complete Information-set Coaching scope summaries")
    if "historical_information_set_search_review_summary" in historical:
        errors.append("Coaching-only workflow must not emit the retained Review")
    if report["outcome_context"]["source_game_id"] != report["source_game_id"]:
        errors.append("expected Information-set Coaching outcome source identity")
    return errors


def check_historical_party_wide_claim_information_set_replay_coaching(
    data: dict[str, Any],
) -> list[str]:
    errors = check_historical_information_set_replay_coaching(data)
    report = data["historical_game_summary"].get(
        "historical_information_set_replay_coaching_summary"
    )
    if not isinstance(report, dict):
        return errors
    if report["game_context"]["game_end_reason"] != (
        "party_wide_all_remaining_tricks_claim"
    ):
        errors.append("expected party-wide Claim Coaching context")
    outcome = report["outcome_context"]
    if outcome["historical_game_end_summary"]["kind"] != (
        "party_wide_all_remaining_tricks_claim"
    ):
        errors.append("expected party-wide Claim Coaching outcome")
    if outcome["final_settlement_summary"]["is_complete"] is not True:
        errors.append("expected complete Claim settlement in Coaching outcome")
    return errors


def check_historical_tactical_motif_review(data: dict[str, Any]) -> list[str]:
    historical = data.get("historical_game_summary")
    if not isinstance(historical, dict):
        return ["expected historical_game_summary"]
    report = historical.get("historical_tactical_motif_review_summary")
    if not isinstance(report, dict):
        return ["expected historical_tactical_motif_review_summary"]
    errors = []
    if report["review_method"] != "historical_tactical_motif_review_v1":
        errors.append("expected Historical Tactical Motif Review method")
    if report["source_game_id"] != historical["game_id"]:
        errors.append("expected Historical Tactical Motif source identity")
    if report["observation_count"] != len(report["observations"]):
        errors.append("expected exact tactical observation coverage")
    if (
        report["complete_observation_count"] + report["partial_observation_count"]
        != report["observation_count"]
    ):
        errors.append("expected exact tactical observation status reconciliation")
    if sum(item["count"] for item in report["motif_counts"]) != report["motif_occurrence_count"]:
        errors.append("expected exact tactical motif-count reconciliation")
    if sum(item["count"] for item in report["family_counts"]) != report["motif_occurrence_count"]:
        errors.append("expected exact tactical family-count reconciliation")
    if tuple(
        len(report[field])
        for field in (
            "player_summaries",
            "role_summaries",
            "phase_summaries",
            "contract_summaries",
        )
    ) != (3, 2, 3, 1):
        errors.append("expected complete Tactical Motif scope summaries")
    if "decision_snapshot_summary" in historical:
        errors.append("Tactical-only workflow must not emit retained Snapshots")
    return errors


def check_historical_tactical_motif_defender_partnership(
    data: dict[str, Any],
) -> list[str]:
    errors = check_historical_tactical_motif_review(data)
    report = data["historical_game_summary"].get("historical_tactical_motif_review_summary")
    if not isinstance(report, dict):
        return errors
    partnership_count = next(
        item["count"]
        for item in report["family_counts"]
        if item["motif_family"] == "defender_partnership"
    )
    if partnership_count <= 0:
        errors.append("expected deterministic Defender-partnership motifs")
    if report["observation_count"] != 30:
        errors.append("expected all 30 normal-completion observations")
    return errors


def check_historical_party_wide_claim_tactical_motif_review(
    data: dict[str, Any],
) -> list[str]:
    errors = check_historical_tactical_motif_review(data)
    historical = data["historical_game_summary"]
    report = historical.get("historical_tactical_motif_review_summary")
    if not isinstance(report, dict):
        return errors
    if report["observation_count"] != 15:
        errors.append("expected all 15 pre-Claim observations")
    if historical["historical_game_end_summary"]["kind"] != (
        "party_wide_all_remaining_tricks_claim"
    ):
        errors.append("expected party-wide Claim Tactical Motif context")
    return errors


def check_information_set_search_evaluation(data: dict[str, Any]) -> list[str]:
    summary = data.get("information_set_search_evaluation_summary")
    if not isinstance(summary, dict):
        return ["expected information_set_search_evaluation_summary"]
    errors = _check_information_set_public_surface(summary)
    if summary["selection"]["partitions"] != ["validation", "test"]:
        errors.append("expected default validation/test evaluation partitions")
    if summary["decision_count"] != 1:
        errors.append("expected deterministic one-decision evaluation prefix")
    if summary["record_count"] != 1 or len(summary["records"]) != 1:
        errors.append("expected one selected Dataset record")
    if sum(summary["status_counts"].values()) != summary["decision_count"]:
        errors.append("expected exact evaluation status reconciliation")
    return errors


def check_information_set_search_multi_step(data: dict[str, Any]) -> list[str]:
    errors = check_information_set_search_live_complete(data)
    multi_step = data.get("multi_step_result")
    if not isinstance(multi_step, dict):
        return [*errors, "expected information-set Search multi_step_result"]
    summary = multi_step.get("summary")
    expected_summary = {
        "requested_method": "information_set_search",
        "decisions_attempted": 1,
        "decisions_executed": 1,
        "search_recommendations_used": 1,
        "immediate_fallbacks_used": 0,
        "no_recommendation_count": 0,
    }
    if not isinstance(summary, dict) or any(
        summary.get(key) != value for key, value in expected_summary.items()
    ):
        errors.append("expected exact information-set Multi-Step recommendation counts")
    if multi_step.get("card_selection_policy") != "information_set_search":
        errors.append("expected information_set_search Multi-Step policy")
    steps = multi_step.get("steps")
    if not isinstance(steps, list) or len(steps) != 1:
        return [*errors, "expected one Information-set Multi-Step step"]
    step = steps[0]
    decision = step.get("recommendation_decision")
    if not isinstance(decision, dict):
        return [*errors, "expected one Information-set Multi-Step Decision"]
    errors.extend(_check_information_set_public_surface(decision))
    nested = decision.get("information_set_search_result")
    if not isinstance(nested, dict):
        errors.append("expected nested safe information-set Search Result")
    else:
        errors.extend(_check_information_set_public_surface(nested))
    if "bounded_search_result" in decision:
        errors.append("Information-set Multi-Step Decision exposed bounded Search")
    if (
        decision.get("recommendation_card") != "D7"
        or step.get("candidate_card") != "D7"
    ):
        errors.append("expected D7 recommendation and execution equality")
    if decision.get("fallback_used") is not False:
        errors.append("Information-set Multi-Step Decision must not use fallback")
    if "world_selection_seed" in _collect_property_names(decision):
        errors.append("Information-set Multi-Step Decision exposed its child seed")
    return errors


def check_information_set_search_policy_comparison(
    data: dict[str, Any],
) -> list[str]:
    errors = check_information_set_search_multi_step(data)
    comparison = data.get("policy_comparison_result")
    if not isinstance(comparison, dict):
        return [*errors, "expected information-set Search policy comparison"]
    errors.extend(_check_information_set_public_surface(comparison))
    expected_policies = [
        "first_legal",
        "lowest_point",
        "highest_point",
        "highest_expected_value",
        "information_set_search",
    ]
    if comparison.get("policies") != expected_policies:
        errors.append("expected Information-set Search exactly once and last")
    rows = comparison.get("policy_results")
    if not isinstance(rows, list):
        return [*errors, "expected Policy Comparison rows"]
    search_rows = [row for row in rows if row.get("policy") == "information_set_search"]
    if len(search_rows) != 1:
        return [*errors, "expected exactly one Information-set Search row"]
    row = search_rows[0]
    if row.get("eligible_for_recommendation") is not True:
        errors.append("expected eligible Information-set Search comparison row")
    if row.get("ineligible_reason") is not None:
        errors.append("expected no Information-set Search ineligible reason")
    diagnostics = row.get("search_decision_diagnostics")
    if not isinstance(diagnostics, list) or len(diagnostics) != 1:
        return [*errors, "expected one compact Information-set diagnostic"]
    expected_fields = {
        "step_index",
        "requested_method",
        "effective_method",
        "search_method",
        "search_status",
        "search_stop_reason",
        "world_coverage",
        "policy_claim",
        "policy_consistency",
        "selected_world_count",
        "completed_world_count",
        "information_sets_evaluated",
        "controlled_policy_decision_count",
        "fixed_policy_decision_count",
        "recommendation_card",
        "fallback_used",
    }
    if set(diagnostics[0]) != expected_fields:
        errors.append("expected exact compact Information-set diagnostic fields")
    if diagnostics[0].get("fallback_used") is not False:
        errors.append("Information-set comparison diagnostic must not use fallback")
    return errors


def _find_forbidden_list_output_key(value: Any) -> str | None:
    forbidden_keys = {
        "historical_game",
        "record",
        "hand",
        "initial_hand",
        "skat",
        "discarded_cards",
        "tricks",
        "plays",
        "remaining_hands",
        "ownership",
        "search_state",
        "proof_state",
    }
    if isinstance(value, dict):
        for key, child in value.items():
            if key in forbidden_keys:
                return key
            found = _find_forbidden_list_output_key(child)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_forbidden_list_output_key(child)
            if found is not None:
                return found
    return None


def check_fixed_three_player_historical_list_mixed(data: dict[str, Any]) -> list[str]:
    summary = data.get("fixed_three_player_historical_list_summary")
    if not isinstance(summary, dict):
        return ["expected fixed_three_player_historical_list_summary"]
    errors = []
    if set(data) != {"input_file", "fixed_three_player_historical_list_summary"}:
        errors.append("expected isolated historical-list root output")
    if (summary["entry_count"], summary["round_count"]) != (36, 12):
        errors.append("expected 36 positions and twelve rounds")
    if (summary["played_game_count"], summary["passed_deal_count"]) != (1, 35):
        errors.append("expected one Played Game and 35 Passed Deals")
    if len(summary["progression"]) != 36 or len(summary["final_standings"]) != 3:
        errors.append("expected complete progression and final standings")
    if summary["applied_lot_order"] != ["player-a", "player-c"]:
        errors.append("expected the supplied external lot")
    forbidden = _find_forbidden_list_output_key(summary)
    if forbidden is not None:
        errors.append(f"unexpected private list-output key: {forbidden}")
    return errors


def check_fixed_three_player_historical_list_all_passed(
    data: dict[str, Any],
) -> list[str]:
    errors = check_fixed_three_player_historical_list_mixed(data)
    summary = data["fixed_three_player_historical_list_summary"]
    errors = [
        error
        for error in errors
        if error
        not in {
            "expected one Played Game and 35 Passed Deals",
            "expected the supplied external lot",
        }
    ]
    if (summary["played_game_count"], summary["passed_deal_count"]) != (0, 36):
        errors.append("expected all 36 positions to be Passed Deals")
    if summary["ranking_status"] != "lot_required":
        errors.append("expected unresolved all-player tie")
    if summary["lot_required_player_ids"] != ["player-a", "player-b", "player-c"]:
        errors.append("expected all three players in the required lot")
    return errors


def check_fixed_three_player_historical_list_comparison(
    data: dict[str, Any],
) -> list[str]:
    summary = data.get("fixed_three_player_historical_list_comparison_summary")
    if not isinstance(summary, dict):
        return ["expected fixed_three_player_historical_list_comparison_summary"]
    errors = []
    if set(data) != {
        "input_file",
        "fixed_three_player_historical_list_comparison_summary",
    }:
        errors.append("expected isolated historical-list comparison root output")
    if summary["list_count"] != 2 or len(summary["source_lists"]) != 2:
        errors.append("expected two ordered source lists")
    if summary["reference_list_id"] != "comparison-reference-001":
        errors.append("expected the first source as reference")
    pairwise = summary["comparisons"][0]
    if (pairwise["played_game_count_delta"], pairwise["passed_deal_count_delta"]) != (
        1,
        -1,
    ):
        errors.append("expected Played Game and Passed Deal count deltas")
    expected_delta_fields = {
        "list_entry_count",
        "played_game_count",
        "passed_deal_count",
        "declarer_game_count",
        "defender_game_count",
        "own_games_won",
        "own_games_lost",
        "defender_games_won",
        "defender_games_lost",
        "other_players_lost_games",
        "player_game_points",
        "own_game_bonus_points",
        "opponent_loss_bonus_points",
        "total_performance_points",
    }
    for player in pairwise["player_comparisons"]:
        if set(player["deltas"]) != expected_delta_fields:
            errors.append("expected all 14 player-total delta fields")
        if player["rank_comparison_status"] != "available":
            errors.append("expected resolved rank comparison")
    if "progression" in json.dumps(summary) or "entry_fact" in json.dumps(summary):
        errors.append("compact comparison must not expose progression or Entry Facts")
    forbidden = _find_forbidden_list_output_key(summary)
    if forbidden is not None:
        errors.append(f"unexpected private comparison-output key: {forbidden}")
    return errors


def _check_training_dataset_preparation(
    result: dict[str, Any],
    *,
    mode: str,
    algorithm: str,
    status: str,
) -> list[str]:
    errors = []
    if set(result) != {"input_file", "training_dataset_preparation_summary"}:
        errors.append("expected isolated training_dataset_preparation_summary output")
        return errors
    summary = result["training_dataset_preparation_summary"]
    if set(summary) != {
        "preparation_version",
        "plan",
        "training_dataset_input",
        "partition_audit",
    }:
        errors.append("expected exact four-field preparation result")
        return errors
    plan = summary["plan"]
    if (plan["mode"], plan["algorithm"], plan["status"]) != (
        mode,
        algorithm,
        status,
    ):
        errors.append("expected mode-compatible preparation Plan")
    if len(plan["plan_fingerprint"]) != 64:
        errors.append("expected SHA-256 Plan fingerprint")
    forbidden_plan_terms = (
        '"historical_game"',
        '"initial_hand"',
        '"components"',
        '"candidates"',
        '"derived_seed"',
        '"tie_key"',
    )
    serialized_plan = json.dumps(plan)
    if any(term in serialized_plan for term in forbidden_plan_terms):
        errors.append("Plan crossed the card-free or private-information boundary")
    if status == "complete":
        if summary["training_dataset_input"] is None or summary["partition_audit"] is None:
            errors.append("complete preparation must materialize Dataset and audit")
        if len(plan["assignments"]) != plan["source_record_count"]:
            errors.append("complete preparation must assign every source Record")
        if [row["partition"] for row in plan["partition_summaries"]] != [
            "train",
            "validation",
            "test",
        ]:
            errors.append("complete preparation summaries must use canonical order")
        if mode == "known_opponent" and plan["temporal_audit"] is None:
            errors.append("complete Known-opponent preparation requires temporal audit")
        if mode == "unseen_player" and plan["temporal_audit"] is not None:
            errors.append("complete unseen-player preparation must omit temporal audit")
    else:
        if summary["training_dataset_input"] is not None or summary["partition_audit"] is not None:
            errors.append("unavailable preparation must not materialize Dataset or audit")
        if plan["assignments"] or plan["partition_summaries"]:
            errors.append("unavailable preparation must not expose partial Plan data")
    return errors


def check_training_dataset_preparation_known_opponent(
    result: dict[str, Any],
) -> list[str]:
    return _check_training_dataset_preparation(
        result,
        mode="known_opponent",
        algorithm="temporal_known_opponent_v1",
        status="complete",
    )


def check_training_dataset_preparation_unseen_player(
    result: dict[str, Any],
) -> list[str]:
    return _check_training_dataset_preparation(
        result,
        mode="unseen_player",
        algorithm="component_balanced_unseen_player_v1",
        status="complete",
    )


def check_training_dataset_preparation_unavailable(
    result: dict[str, Any],
) -> list[str]:
    errors = _check_training_dataset_preparation(
        result,
        mode="known_opponent",
        algorithm="temporal_known_opponent_v1",
        status="unavailable",
    )
    plan = result["training_dataset_preparation_summary"]["plan"]
    if plan["unavailable_reason"] != "missing_played_at":
        errors.append("expected stable missing_played_at unavailable reason")
    return errors


def _write_generated_document(file_path: Path, document: dict[str, Any]) -> None:
    file_path.write_text(
        json.dumps(document, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _session_players_from_create(
    document: dict[str, Any],
) -> tuple[session_api.SessionPlayerV1, ...]:
    return tuple(
        session_api.SessionPlayerV1(
            player_id=player["player_id"],
            player_label=player["player_label"],
            seat=player["seat"],
        )
        for player in document["players"]
    )


def _load_example_persistence(
    file_name: str,
) -> session_api.SessionPersistenceDocumentV1:
    source = load_json_file(PROJECT_ROOT / "examples" / file_name)
    return session_api.resume_session_document(source).value.document


def _save_scenario_session(
    scenario: Scenario,
    file_path: Path,
    document: session_api.SessionPersistenceDocumentV1,
) -> list[str]:
    saved = session_files.save_session_file(
        file_path,
        document,
        expected_content_fingerprint=None,
    ).value
    if saved.status == "saved":
        return []
    return [
        format_scenario_error(
            scenario,
            f"expected initial Session persistence status saved, got {saved.status}",
        )
    ]


def _run_session_command(
    scenario: Scenario,
    arguments: list[str],
) -> list[str]:
    exit_code = run_session_cli(arguments)
    if exit_code == 0:
        return []
    return [
        format_scenario_error(
            scenario,
            f"Session CLI generation failed with exit code {exit_code}",
        )
    ]


def _forbidden_position_keys(value: object) -> set[str]:
    forbidden = {
        "command_log",
        "content_fingerprint",
        "decision_checkpoints",
        "initial_hand",
        "opponent_hand",
        "state_fingerprint",
    }
    found: set[str] = set()
    if isinstance(value, dict):
        found.update(forbidden.intersection(value))
        for child in value.values():
            found.update(_forbidden_position_keys(child))
    elif isinstance(value, list):
        for child in value:
            found.update(_forbidden_position_keys(child))
    return found


def _check_live_fixture(
    scenario: Scenario,
    document: session_api.SessionPersistenceDocumentV1,
) -> list[str]:
    expected = build_live_example_persistence_document()
    errors = []
    if document != expected:
        errors.append("Live persistence example differs from canonical API construction")
    if document.state.revision != 13 or document.state.phase != "play":
        errors.append("expected Position-ready Live revision 13")
    if len(document.decision_checkpoints) != 1:
        errors.append("expected one frozen Live Decision Checkpoint")
    resumed = session_api.resume_session_document(document.to_dict()).value
    if [lineage.relationship for lineage in resumed.checkpoint_lineage] != ["current"]:
        errors.append("expected current lineage for the frozen Live Checkpoint")
    return [format_scenario_error(scenario, error) for error in errors]


def _generate_session_live_create(
    scenario: Scenario,
    output_path: Path,
    _temporary_path: Path,
) -> list[str]:
    create_document = load_json_file(scenario.input_path)
    result = session_api.create_session(
        session_id=create_document["session_id"],
        players=_session_players_from_create(create_document),
        capture_mode=create_document["capture_mode"],
        local_player_id=create_document["local_player_id"],
        options=session_api.SessionApiOptionsV1(include_provenance=True),
    )
    _write_generated_document(
        output_path,
        session_api.serialize_session_result(result),
    )
    errors = []
    if result.value.revision != 0 or result.value.phase != "setup":
        errors.append("expected deterministic revision-zero Session creation")
    if result.value.validation.position_export.status != "unavailable":
        errors.append("expected normal unavailable Position status at creation")
    if result.value.validation.historical_export.status != "unavailable":
        errors.append("expected normal unavailable Historical status at creation")
    if result.field_provenance is None:
        errors.append("expected Session provenance on creation")
    return [format_scenario_error(scenario, error) for error in errors]


def _generate_session_live_apply_and_resume(
    scenario: Scenario,
    output_path: Path,
    temporary_path: Path,
) -> list[str]:
    source = _load_example_persistence("session_live_persistence.json")
    errors = _check_live_fixture(scenario, source)
    session_path = temporary_path / f"{scenario.name}.session.json"
    errors.extend(_save_scenario_session(scenario, session_path, source))
    if errors:
        return errors
    errors.extend(
        _run_session_command(
            scenario,
            [
                "apply",
                "--session",
                str(session_path),
                "--input",
                str(scenario.input_path),
                "--output",
                str(output_path),
                "--samples",
                "1",
                "--seed",
                "157",
                "--include-provenance",
                "--quiet",
            ],
        )
    )
    if errors:
        return errors
    resumed = session_files.load_session_file(session_path).value
    state = resumed.document.state
    checkpoint = resumed.document.decision_checkpoints[0]
    observation = session_api.observe_session_decision_checkpoint(
        state=state,
        checkpoint=checkpoint,
        options=session_api.SessionApiOptionsV1(include_provenance=True),
    )
    output = load_json_file(output_path)
    checks = []
    if output.get("operation") != "apply_command" or output.get("value", {}).get(
        "status"
    ) != "applied":
        checks.append("expected one applied public Session Command Result")
    if "field_provenance" not in output:
        checks.append("expected Session provenance on the apply Result")
    if state.revision != 14 or state.command_log[-1].command.card != "CA":
        checks.append("expected accepted CA at revision 14 after strict Resume")
    if resumed.document.decision_checkpoints != source.decision_checkpoints:
        checks.append("automatic collection did not deduplicate the exact Checkpoint")
    if [item.relationship for item in resumed.checkpoint_lineage] != ["ancestor"]:
        checks.append("expected ancestor lineage after the observed Play")
    if (
        observation.value.status != "observed"
        or observation.value.actual_card != "CA"
        or observation.value.observed_play_revision != 14
    ):
        checks.append("expected observed CA at accepted revision 14")
    if observation.field_provenance is None:
        checks.append("expected complete observation provenance")
    return [format_scenario_error(scenario, error) for error in checks]


def _generate_session_live_analyze_with_checkpoint(
    scenario: Scenario,
    output_path: Path,
    temporary_path: Path,
) -> list[str]:
    source = _load_example_persistence("session_live_persistence.json")
    session_path = temporary_path / f"{scenario.name}.session.json"
    errors = _check_live_fixture(scenario, source)
    errors.extend(_save_scenario_session(scenario, session_path, source))
    if errors:
        return errors
    before = session_path.read_bytes()
    errors.extend(
        _run_session_command(
            scenario,
            [
                "analyze",
                "--session",
                str(session_path),
                "--output",
                str(output_path),
                "--samples",
                "1",
                "--seed",
                "157",
                "--include-provenance",
                "--quiet",
            ],
        )
    )
    if errors:
        return errors
    output = load_json_file(output_path)
    resumed = session_files.load_session_file(session_path).value
    checks = []
    if session_path.read_bytes() != before:
        checks.append("analysis rewrote an already deduplicated Checkpoint file")
    if resumed.document.decision_checkpoints != source.decision_checkpoints:
        checks.append("analysis changed the exact frozen Checkpoint")
    if "field_provenance" not in output:
        checks.append("expected Root Result provenance on Session-triggered analysis")
    if output.get("position", {}).get("hand") != list(_SESSION_HANDS["player-a"]):
        checks.append("analysis did not use the frozen Decision-time local hand")
    leaked = _forbidden_position_keys(output)
    if leaked:
        checks.append(f"Position Result leaked private Session fields: {sorted(leaked)}")
    return [format_scenario_error(scenario, error) for error in checks]


def _generate_session_live_observed_card_review(
    scenario: Scenario,
    output_path: Path,
    temporary_path: Path,
) -> list[str]:
    source = _load_example_persistence("session_live_persistence.json")
    checkpoint = source.decision_checkpoints[0]
    session_path = temporary_path / f"{scenario.name}.session.json"
    errors = _save_scenario_session(scenario, session_path, source)
    if errors:
        return errors
    errors.extend(
        _run_session_command(
            scenario,
            [
                "apply",
                "--session",
                str(session_path),
                "--input",
                str(scenario.input_path),
                "--samples",
                "1",
                "--seed",
                "157",
                "--quiet",
            ],
        )
    )
    if errors:
        return errors
    resumed = session_files.load_session_file(session_path).value
    observation = session_api.observe_session_decision_checkpoint(
        state=resumed.document.state,
        checkpoint=resumed.document.decision_checkpoints[0],
    ).value
    review_export = session_api.export_session_checkpoint_review_request(
        state=resumed.document.state,
        checkpoint=resumed.document.decision_checkpoints[0],
        options=session_api.SessionApiOptionsV1(include_provenance=True),
    )
    frozen = checkpoint.request.to_dict()["document"]
    expected_review = dict(frozen)
    expected_review["analysis_mode"] = "post_game_review"
    expected_review["actual_card_played"] = "CA"
    before_review = session_path.read_bytes()
    errors.extend(
        _run_session_command(
            scenario,
            [
                "review",
                "--session",
                str(session_path),
                "--checkpoint-index",
                "0",
                "--output",
                str(output_path),
                "--quiet",
            ],
        )
    )
    if errors:
        return errors
    output = load_json_file(output_path)
    checks = []
    if (
        observation.status != "observed"
        or observation.actual_card != "CA"
        or observation.observed_play_revision != 14
    ):
        checks.append("review did not derive the exact observed CA revision")
    if review_export.value.request.to_dict()["document"] != expected_review:
        checks.append("review Request was not the frozen Request plus only observed CA")
    if review_export.field_provenance is None:
        checks.append("expected Session provenance on review Request export")
    if source.decision_checkpoints[0] != checkpoint:
        checks.append("review mutated the frozen Checkpoint")
    if session_path.read_bytes() != before_review:
        checks.append("review modified the persisted Session")
    if output.get("post_game_review_summary", {}).get("actual_card_played") != "CA":
        checks.append("Engine review Result did not retain observed CA")
    if output.get("position", {}).get("hand") != frozen["hand"]:
        checks.append("Engine review did not retain the frozen Decision-time hand")
    leaked = _forbidden_position_keys(output)
    if leaked:
        checks.append(f"review Result leaked private Session fields: {sorted(leaked)}")
    return [format_scenario_error(scenario, error) for error in checks]


def _build_live_correction_source(
) -> session_api.SessionPersistenceDocumentV1:
    source = build_live_example_persistence_document()
    state = source.state
    for player_id, card in (
        ("player-a", "CA"),
        ("player-b", "SJ"),
        ("player-c", "HJ"),
        ("player-b", "S9"),
        ("player-c", "H9"),
        ("player-a", "SA"),
    ):
        state = _apply_session_document(
            state,
            {
                "command_version": 1,
                "kind": "record_play",
                "expected_revision": state.revision,
                "player_id": player_id,
                "card": card,
            },
        )
    return session_api.build_session_persistence_document(
        state,
        decision_checkpoints=source.decision_checkpoints,
    ).value


def _generate_session_undo_and_partial_correction(
    scenario: Scenario,
    output_path: Path,
    temporary_path: Path,
) -> list[str]:
    source = _build_live_correction_source()
    undo_path = temporary_path / f"{scenario.name}.undo.session.json"
    correction_path = temporary_path / f"{scenario.name}.correct.session.json"
    errors = _save_scenario_session(scenario, undo_path, source)
    errors.extend(_save_scenario_session(scenario, correction_path, source))
    if errors:
        return errors
    undo_output = temporary_path / f"{scenario.name}.undo.output.json"
    errors.extend(
        _run_session_command(
            scenario,
            [
                "undo",
                "--session",
                str(undo_path),
                "--target-revision",
                "18",
                "--output",
                str(undo_output),
                "--samples",
                "1",
                "--seed",
                "157",
                "--quiet",
            ],
        )
    )
    errors.extend(
        _run_session_command(
            scenario,
            [
                "correct",
                "--session",
                str(correction_path),
                "--input",
                str(scenario.input_path),
                "--output",
                str(output_path),
                "--samples",
                "1",
                "--seed",
                "157",
                "--quiet",
            ],
        )
    )
    if errors:
        return errors
    undo = load_json_file(undo_output)
    correction = load_json_file(output_path)
    resumed_undo = session_files.load_session_file(undo_path).value
    resumed_correction = session_files.load_session_file(correction_path).value
    checks = []
    if undo.get("operation") != "rewind" or undo.get("value", {}).get("status") != "applied":
        checks.append("expected an applied strict-prefix Undo")
    if resumed_undo.document.state.revision != 18:
        checks.append("Undo did not persist the exact target revision")
    value = correction.get("value", {})
    if correction.get("operation") != "correct" or value.get("status") != "partial":
        checks.append("expected a normal partial Correction Result")
    if value.get("failed_original_revision") != 19:
        checks.append("expected suffix replay to first fail at original revision 19")
    if len(value.get("replayed_suffix_records", [])) != 4 or len(
        value.get("discarded_suffix_records", [])
    ) != 1:
        checks.append("partial Correction suffix accounting is not exact")
    if resumed_correction.document.state.revision != 18:
        checks.append("partial Correction did not persist its valid partial State")
    relationships = [
        item.relationship for item in resumed_correction.checkpoint_lineage
    ]
    if relationships != ["ancestor", "current"]:
        checks.append("partial Correction Checkpoint lineage is not ancestor/current")
    if len(resumed_correction.document.decision_checkpoints) != 2:
        checks.append("partial Correction did not retain and collect exact Checkpoints")
    return [format_scenario_error(scenario, error) for error in checks]


def _generate_session_persistence_conflict(
    scenario: Scenario,
    output_path: Path,
    temporary_path: Path,
) -> list[str]:
    source = _load_example_persistence("session_live_persistence.json")
    advanced_state = _apply_session_document(
        source.state,
        load_json_file(PROJECT_ROOT / "examples" / "session_command_record_play.json"),
    )
    advanced = session_api.build_session_persistence_document(
        advanced_state,
        decision_checkpoints=source.decision_checkpoints,
    ).value
    session_path = temporary_path / f"{scenario.name}.session.json"
    errors = _save_scenario_session(scenario, session_path, advanced)
    if errors:
        return errors
    before = session_path.read_bytes()
    conflict = session_files.save_session_file(
        session_path,
        source,
        expected_content_fingerprint=source.content_fingerprint,
    )
    _write_generated_document(
        output_path,
        session_files.serialize_session_file_result(conflict),
    )
    resumed = session_files.load_session_file(session_path).value
    checks = []
    if conflict.value.status != "conflict":
        checks.append("expected a normal optimistic persistence conflict")
    if conflict.value.existing_content_fingerprint != advanced.content_fingerprint:
        checks.append("conflict did not report the exact existing fingerprint")
    if conflict.value.requested_content_fingerprint != source.content_fingerprint:
        checks.append("conflict did not report the exact requested fingerprint")
    if session_path.read_bytes() != before or resumed.document != advanced:
        checks.append("persistence conflict replaced the target Session")
    return [format_scenario_error(scenario, error) for error in checks]


def _check_retrospective_fixture(
    scenario: Scenario,
    document: session_api.SessionPersistenceDocumentV1,
) -> list[str]:
    expected = build_retrospective_example_persistence_document()
    errors = []
    if document != expected:
        errors.append("Retrospective persistence example differs from API construction")
    if document.state.revision != 38 or document.state.phase != "ended":
        errors.append("expected ended zero-decision Retrospective revision 38")
    if document.decision_checkpoints:
        errors.append("Retrospective example unexpectedly retained a Decision Checkpoint")
    resumed = session_api.resume_session_document(document.to_dict()).value
    if resumed.checkpoint_lineage:
        errors.append("Retrospective example unexpectedly derived Checkpoint lineage")
    return [format_scenario_error(scenario, error) for error in errors]


def _generate_session_retrospective_export(
    scenario: Scenario,
    output_path: Path,
    temporary_path: Path,
) -> list[str]:
    source = _load_example_persistence("session_retrospective_persistence.json")
    errors = _check_retrospective_fixture(scenario, source)
    session_path = temporary_path / f"{scenario.name}.session.json"
    errors.extend(_save_scenario_session(scenario, session_path, source))
    if errors:
        return errors
    before = session_path.read_bytes()
    errors.extend(
        _run_session_command(
            scenario,
            [
                "export-historical",
                "--session",
                str(session_path),
                "--output",
                str(output_path),
                "--include-provenance",
                "--quiet",
            ],
        )
    )
    if errors:
        return errors
    output = load_json_file(output_path)
    request = output.get("value", {}).get("request", {})
    historical = request.get("document", {}).get("historical_game_input", {})
    checks = []
    if output.get("operation") != "export_historical" or output.get("value", {}).get(
        "status"
    ) != "available":
        checks.append("expected an available Historical Session export")
    if historical.get("game_id") != "session-retrospective-example-game":
        checks.append("Historical export did not retain the canonical game identity")
    if historical.get("tricks") != []:
        checks.append("expected an exact zero-decision Historical export")
    if "field_provenance" not in output:
        checks.append("expected Session provenance on Historical export")
    if session_path.read_bytes() != before:
        checks.append("Historical export modified the Session file")
    return [format_scenario_error(scenario, error) for error in checks]


def _generate_session_retrospective_finalize(
    scenario: Scenario,
    output_path: Path,
    temporary_path: Path,
) -> list[str]:
    source = _load_example_persistence("session_retrospective_persistence.json")
    session_path = temporary_path / f"{scenario.name}.session.json"
    errors = _check_retrospective_fixture(scenario, source)
    errors.extend(_save_scenario_session(scenario, session_path, source))
    if errors:
        return errors
    before = session_path.read_bytes()
    errors.extend(
        _run_session_command(
            scenario,
            [
                "finalize",
                "--session",
                str(session_path),
                "--output",
                str(output_path),
                "--include-provenance",
                "--quiet",
            ],
        )
    )
    if errors:
        return errors
    output = load_json_file(output_path)
    summary = output.get("historical_game_summary", {})
    checks = []
    if summary.get("game_id") != "session-retrospective-example-game":
        checks.append("finalize did not execute the exported Historical game")
    if summary.get("play_prefix_summary", {}).get("played_card_count") != 0:
        checks.append("expected deterministic zero-decision Historical execution")
    if "field_provenance" not in output:
        checks.append("expected Root Result provenance on Historical finalize")
    if session_path.read_bytes() != before:
        checks.append("Historical finalize modified the Session file")
    return [format_scenario_error(scenario, error) for error in checks]


_SESSION_SCENARIO_GENERATORS = {
    "live_create": _generate_session_live_create,
    "live_apply_and_resume": _generate_session_live_apply_and_resume,
    "live_analyze_with_checkpoint": _generate_session_live_analyze_with_checkpoint,
    "live_observed_card_review": _generate_session_live_observed_card_review,
    "undo_and_partial_correction": _generate_session_undo_and_partial_correction,
    "persistence_conflict": _generate_session_persistence_conflict,
    "retrospective_export": _generate_session_retrospective_export,
    "retrospective_finalize": _generate_session_retrospective_finalize,
}


def run_session_scenario(
    scenario: Scenario,
    output_path: Path,
    temporary_path: Path,
) -> list[str]:
    """Runs one appended deterministic Session orchestration."""
    if scenario.session_orchestration is None:
        return [format_scenario_error(scenario, "missing Session orchestration")]
    return _SESSION_SCENARIO_GENERATORS[scenario.session_orchestration](
        scenario,
        output_path,
        temporary_path,
    )


SCENARIOS = (
    Scenario(
        name="normal_local_live",
        input_path=PROJECT_ROOT / "examples" / "grand_second_position.json",
        branch="baseline local live Immediate Analysis",
        check_output=check_normal_local_live,
    ),
    Scenario(
        name="quiet_json_output",
        input_path=PROJECT_ROOT / "examples" / "grand_second_position.json",
        branch="quiet automation-friendly JSON output workflow",
        cli_args=("--quiet",),
        check_output=check_normal_local_live,
        expect_quiet_stdout=True,
    ),
    Scenario(
        name="complete_bounded_search",
        input_path=PROJECT_ROOT / "examples" / "grand_bounded_search_exhaustive.json",
        branch="complete small exhaustive live bounded Search recommendation",
        check_output=check_complete_bounded_search,
    ),
    Scenario(
        name="auto_bounded_search_fallback",
        input_path=PROJECT_ROOT / "examples" / "grand_auto_search_fallback.json",
        branch="node-limited bounded Search with explicit Immediate fallback",
        check_output=check_auto_search_fallback,
    ),
    Scenario(
        name="bounded_search_post_game_review",
        input_path=(
            PROJECT_ROOT / "examples" / "grand_bounded_search_post_game_review.json"
        ),
        branch="flat post-game Search actual-card and Immediate comparison",
        check_output=check_bounded_search_post_game_review,
    ),
    Scenario(
        name="search_aware_multi_step",
        input_path=PROJECT_ROOT / "examples" / "grand_bounded_search_exhaustive.json",
        branch="one executed bounded-Search Multi-Step decision",
        cli_args=("--multi-step", "1"),
        check_output=check_search_aware_multi_step,
    ),
    Scenario(
        name="search_inclusive_policy_comparison",
        input_path=PROJECT_ROOT / "examples" / "grand_bounded_search_exhaustive.json",
        branch="four legacy policies plus one bounded-Search comparison path",
        cli_args=("--multi-step", "1", "--compare-policies"),
        check_output=check_search_inclusive_policy_comparison,
    ),
    Scenario(
        name="local_live_multi_step_two_steps",
        input_path=PROJECT_ROOT / "examples" / "grand_second_position.json",
        branch="documented local live two-step Multi-Step JSON output",
        cli_args=(
            "--multi-step",
            "2",
            "--expected-value-samples",
            "20",
        ),
        check_output=check_local_live_multi_step,
    ),
    Scenario(
        name="opponent_turn_left_multi_step_preparation",
        input_path=PROJECT_ROOT / "examples" / "grand_left_to_act_live.json",
        branch=(
            "opponent-turn Immediate unavailable plus left-lead/right-response "
            "Multi-Step preparation"
        ),
        cli_args=(
            "--multi-step",
            "1",
            "--card-policy",
            "highest_point",
            "--expected-value-samples",
            "20",
        ),
        check_output=check_opponent_turn_left_multi_step,
    ),
    Scenario(
        name="completed_game_immediate_unavailable",
        input_path=PROJECT_ROOT / "examples" / "grand_complete_declarer_win.json",
        branch="completed-game Immediate unavailable with settlement and rating",
        check_output=check_completed_game_immediate_unavailable,
    ),
    Scenario(
        name="post_game_available_nested_suit_declaration",
        input_path=(PROJECT_ROOT / "examples" / "spades_post_game_actual_card_played.json"),
        branch="actual-card post-game review and nested Suit declaration output",
        check_output=check_post_game_available_nested_suit,
    ),
    Scenario(
        name="post_game_null_objective_review",
        input_path=(PROJECT_ROOT / "examples" / "null_post_game_objective_actual_card.json"),
        branch="actual-card post-game review using the Null contract objective",
        check_output=check_post_game_null_objective_review,
    ),
    Scenario(
        name="post_game_defender_perspective_review",
        input_path=(PROJECT_ROOT / "examples" / "spades_post_game_defender_actual_card.json"),
        branch="actual-card post-game review from a local defender perspective",
        check_output=check_post_game_defender_perspective_review,
    ),
    Scenario(
        name="multi_step_partial_trick_right_response",
        input_path=(
            PROJECT_ROOT
            / "tests"
            / "fixtures"
            / "generated_output_schema"
            / "grand_left_led_right_to_respond_live.json"
        ),
        branch="Multi-Step existing left lead with right response preparation",
        cli_args=(
            "--multi-step",
            "1",
            "--card-policy",
            "highest_point",
            "--expected-value-samples",
            "20",
        ),
        check_output=check_multi_step_partial_trick,
    ),
    Scenario(
        name="multi_step_unsupported_phase",
        input_path=(
            PROJECT_ROOT
            / "tests"
            / "fixtures"
            / "generated_output_schema"
            / "grand_unsupported_multi_step_phase.json"
        ),
        branch="canonical current-Trick completion before one local Decision",
        cli_args=(
            "--multi-step",
            "1",
            "--card-policy",
            "highest_point",
            "--expected-value-samples",
            "20",
        ),
        check_output=check_canonical_multi_step_completion_phase,
    ),
    Scenario(
        name="policy_comparison",
        input_path=PROJECT_ROOT / "examples" / "grand_second_position.json",
        branch="policy-comparison result with per-policy rows and recommendation",
        cli_args=(
            "--multi-step",
            "1",
            "--card-policy",
            "highest_expected_value",
            "--expected-value-samples",
            "20",
            "--compare-policies",
        ),
        check_output=check_policy_comparison,
    ),
    Scenario(
        name="coherent_hidden_world_policy_comparison",
        input_path=PROJECT_ROOT / "examples" / "grand_coherent_hidden_world.json",
        branch="three-step Policy Comparison with one coherent shared root world",
        cli_args=(
            "--multi-step",
            "3",
            "--card-policy",
            "highest_expected_value",
            "--expected-value-samples",
            "20",
            "--compare-policies",
        ),
        check_output=check_coherent_hidden_world_policy_comparison,
    ),
    Scenario(
        name="grand_hidden_card_inference",
        input_path=PROJECT_ROOT / "examples" / "grand_hidden_card_inference.json",
        branch="evidence-constrained hidden-card inference with coherent Multi-Step root",
        cli_args=(
            "--multi-step",
            "2",
            "--expected-value-samples",
            "20",
        ),
        check_output=check_hidden_card_inference,
    ),
    Scenario(
        name="comparison_only_policy_comparison",
        input_path=PROJECT_ROOT / "examples" / "grand_second_position.json",
        branch="comparison-only policy-comparison CLI workflow",
        cli_args=(
            "--multi-step",
            "1",
            "--card-policy",
            "highest_expected_value",
            "--expected-value-samples",
            "20",
            "--compare-policies",
            "--comparison-only",
        ),
        check_output=check_comparison_only,
    ),
    Scenario(
        name="side_specific_opponent_policies",
        input_path=(PROJECT_ROOT / "examples" / "grand_left_right_opponent_policies.json"),
        branch="distinct left/right opponent policy settings",
        check_output=check_side_specific_opponent_policies,
    ),
    Scenario(
        name="side_specific_opponent_policy_multi_step",
        input_path=(PROJECT_ROOT / "examples" / "grand_left_right_opponent_policies.json"),
        branch="side-specific opponent lead policies in Multi-Step output",
        cli_args=(
            "--multi-step",
            "2",
            "--left-opponent-lead-policy",
            "highest_point",
            "--right-opponent-lead-policy",
            "basic_defender_lead",
            "--expected-value-samples",
            "20",
        ),
        check_output=check_side_specific_opponent_policy_multi_step,
    ),
    Scenario(
        name="claim_remaining_tricks_settlement",
        input_path=PROJECT_ROOT / "examples" / "grand_claimed_remaining_tricks.json",
        branch="claim/concession settlement structure",
        check_output=check_claim_remaining_tricks,
    ),
    Scenario(
        name="structured_declarer_concession",
        input_path=PROJECT_ROOT / "examples" / "declarer_concession.json",
        branch="structured declarer-concession adjudication",
        cli_args=("--quiet",),
        check_output=check_structured_declarer_concession,
        expect_quiet_stdout=True,
    ),
    Scenario(
        name="structured_defender_concession",
        input_path=PROJECT_ROOT / "examples" / "defender_concession.json",
        branch="structured defender-concession adjudication",
        cli_args=("--quiet",),
        check_output=check_structured_defender_concession,
        expect_quiet_stdout=True,
    ),
    Scenario(
        name="accepted_declarer_card_exposure",
        input_path=PROJECT_ROOT / "examples" / "declarer_card_exposure.json",
        branch="unanimously accepted declarer-card-exposure adjudication",
        cli_args=("--quiet",),
        check_output=check_declarer_card_exposure,
        expect_quiet_stdout=True,
    ),
    Scenario(
        name="defender_open_play",
        input_path=PROJECT_ROOT / "examples" / "defender_open_play.json",
        branch="bounded exact defender open-play adjudication",
        cli_args=("--quiet",),
        check_output=check_defender_open_play,
        expect_quiet_stdout=True,
    ),
    Scenario(
        name="open_card_throw",
        input_path=PROJECT_ROOT / "examples" / "open_card_throw.json",
        branch="structured open-card-throw rule adjudication",
        cli_args=("--quiet",),
        check_output=check_open_card_throw,
        expect_quiet_stdout=True,
    ),
    Scenario(
        name="declarer_card_exposure_continuation",
        input_path=(PROJECT_ROOT / "examples" / "declarer_card_exposure_continuation.json"),
        branch="continued play with exposed declarer cards",
        cli_args=("--quiet",),
        check_output=check_declarer_card_exposure_continuation,
        expect_quiet_stdout=True,
    ),
    Scenario(
        name="defender_open_play_continuation",
        input_path=PROJECT_ROOT / "examples" / "defender_open_play_continuation.json",
        branch="continued play with returned public exposing-defender cards",
        cli_args=("--quiet",),
        check_output=check_defender_open_play_continuation,
        expect_quiet_stdout=True,
    ),
    Scenario(
        name="overbid_settlement",
        input_path=(PROJECT_ROOT / "examples" / "grand_overbid_declarer_card_points_win.json"),
        branch="supported Suit/Grand overbid settlement",
        check_output=check_overbid_settlement,
    ),
    Scenario(
        name="impossible_null_settlement",
        input_path=(PROJECT_ROOT / "examples" / "null_impossible_declaration_settlement.json"),
        branch="complete impossible Null replacement settlement",
        check_output=check_impossible_null_settlement,
    ),
    Scenario(
        name="list_performance_summary",
        input_path=PROJECT_ROOT / "examples" / "grand_list_performance_input.json",
        branch="optional list performance summary",
        check_output=check_list_performance,
    ),
    Scenario(
        name="list_game_contributions_summary",
        input_path=(PROJECT_ROOT / "examples" / "grand_list_game_contributions.json"),
        branch="optional normalized game-contribution list performance summary",
        check_output=check_list_game_contributions,
    ),
    Scenario(
        name="list_analysis_results_summary",
        input_path=PROJECT_ROOT / "examples" / "grand_list_analysis_results.json",
        branch="optional local analysis-result list performance summary",
        check_output=check_list_analysis_results,
    ),
    Scenario(
        name="list_standings_summary",
        input_path=PROJECT_ROOT / "examples" / "grand_list_standings_input.json",
        branch="optional fixed three-player list standings summary",
        check_output=check_list_standings,
    ),
    Scenario(
        name="late_game_history_heavy_live",
        input_path=(PROJECT_ROOT / "examples" / "grand_late_game_history_heavy_live.json"),
        branch="late-game live public input with zero hand sizes and rich history",
        check_output=check_late_game_history_heavy_live,
    ),
    Scenario(
        name="defender_known_to_declarer_local_view",
        input_path=(
            PROJECT_ROOT
            / "tests"
            / "fixtures"
            / "generated_output_schema"
            / "grand_defender_known_to_declarer_live.json"
        ),
        branch="local defender live output with declarer-private Skat redaction",
        cli_args=(
            "--multi-step",
            "1",
            "--card-policy",
            "highest_point",
            "--expected-value-samples",
            "20",
        ),
        check_output=check_defender_known_to_declarer_local_view,
    ),
    Scenario(
        name="historical_grand_normal_completion",
        input_path=(PROJECT_ROOT / "examples" / "historical_grand_normal_completion.json"),
        branch="complete normal-play historical game with derived settlement",
        cli_args=("--quiet",),
        check_output=check_historical_game_normal_completion,
        expect_quiet_stdout=True,
        include_position_overrides=False,
    ),
    Scenario(
        name="historical_grand_declarer_concession",
        input_path=(PROJECT_ROOT / "examples" / "historical_grand_declarer_concession.json"),
        branch="exact-prefix historical declarer-concession adjudication",
        cli_args=("--quiet",),
        check_output=check_historical_declarer_concession,
        expect_quiet_stdout=True,
        include_position_overrides=False,
    ),
    Scenario(
        name="historical_grand_defender_concession",
        input_path=(PROJECT_ROOT / "examples" / "historical_grand_defender_concession.json"),
        branch="exact-prefix historical defender-concession adjudication",
        cli_args=("--quiet",),
        check_output=check_historical_defender_concession,
        expect_quiet_stdout=True,
        include_position_overrides=False,
    ),
    Scenario(
        name="historical_grand_declarer_card_exposure",
        input_path=(
            PROJECT_ROOT / "examples" / "historical_grand_declarer_card_exposure.json"
        ),
        branch="exact-prefix unanimously accepted historical declarer-card exposure",
        cli_args=("--quiet",),
        check_output=check_historical_declarer_card_exposure,
        expect_quiet_stdout=True,
        include_position_overrides=False,
    ),
    Scenario(
        name="historical_grand_defender_open_play",
        input_path=(
            PROJECT_ROOT / "examples" / "historical_grand_defender_open_play.json"
        ),
        branch="bounded exact historical defender-open-play adjudication",
        cli_args=("--quiet",),
        check_output=check_historical_defender_open_play,
        expect_quiet_stdout=True,
        include_position_overrides=False,
    ),
    Scenario(
        name="historical_grand_open_card_throw",
        input_path=(PROJECT_ROOT / "examples" / "historical_grand_open_card_throw.json"),
        branch="exact-prefix historical open-card-throw rule assignment",
        cli_args=("--quiet",),
        check_output=check_historical_open_card_throw,
        expect_quiet_stdout=True,
        include_position_overrides=False,
    ),
    Scenario(
        name="historical_grand_decision_snapshots",
        input_path=(PROJECT_ROOT / "examples" / "historical_grand_normal_completion.json"),
        branch="information-safe snapshots for all 30 historical decisions",
        cli_args=("--historical-decision-snapshots", "--quiet"),
        check_output=check_historical_decision_snapshots,
        expect_quiet_stdout=True,
        include_position_overrides=False,
    ),
    Scenario(
        name="historical_grand_defender_open_play_continuation_snapshots",
        input_path=(
            PROJECT_ROOT
            / "examples"
            / "historical_grand_defender_open_play_continuation.json"
        ),
        branch="timed historical defender-open-play public-hand transition",
        cli_args=("--historical-decision-snapshots", "--quiet"),
        check_output=check_historical_defender_open_play_continuation_snapshots,
        expect_quiet_stdout=True,
        include_position_overrides=False,
    ),
    Scenario(
        name="historical_grand_declarer_card_exposure_continuation_snapshots",
        input_path=(
            PROJECT_ROOT
            / "examples"
            / "historical_grand_declarer_card_exposure_continuation.json"
        ),
        branch="timed historical public declarer-hand transition",
        cli_args=("--historical-decision-snapshots", "--quiet"),
        check_output=check_historical_declarer_card_exposure_continuation_snapshots,
        expect_quiet_stdout=True,
        include_position_overrides=False,
    ),
    Scenario(
        name="historical_defender_continuation_then_declarer_concession",
        input_path=(
            PROJECT_ROOT
            / "examples"
            / "historical_grand_defender_open_play_continuation_declarer_concession.json"
        ),
        branch="defender continuation followed by terminal declarer concession",
        cli_args=("--historical-decision-snapshots", "--quiet"),
        check_output=check_historical_continuation_terminal_chain,
        expect_quiet_stdout=True,
        include_position_overrides=False,
    ),
    Scenario(
        name="historical_declarer_continuation_then_defender_concession",
        input_path=(
            PROJECT_ROOT
            / "examples"
            / "historical_grand_declarer_card_exposure_continuation_defender_concession.json"
        ),
        branch="declarer continuation followed immediately by defender concession",
        cli_args=("--historical-decision-snapshots", "--quiet"),
        check_output=check_historical_continuation_terminal_chain,
        expect_quiet_stdout=True,
        include_position_overrides=False,
    ),
    Scenario(
        name="historical_grand_game_review",
        input_path=(PROJECT_ROOT / "examples" / "historical_grand_normal_completion.json"),
        branch="seeded complete review of all 30 historical decisions",
        cli_args=(
            "--historical-game-review",
            "--samples",
            "20",
            "--seed",
            "42",
            "--quiet",
        ),
        check_output=check_historical_game_review,
        expect_quiet_stdout=True,
        include_position_overrides=False,
    ),
    Scenario(
        name="historical_grand_search_review",
        input_path=(PROJECT_ROOT / "examples" / "historical_grand_normal_completion.json"),
        branch="Historical Search Review with eligible and unavailable decisions",
        cli_args=(
            "--historical-search-review",
            "--search-seed",
            "71",
            "--search-budget-profile",
            "interactive_v1",
            "--samples",
            "1",
            "--seed",
            "42",
            "--quiet",
        ),
        check_output=check_historical_search_review,
        expect_quiet_stdout=True,
        include_position_overrides=False,
    ),
    Scenario(
        name="historical_grand_ouvert_review",
        input_path=(PROJECT_ROOT / "examples" / "historical_grand_ouvert_review.json"),
        branch="declared-Ouvert historical review with exact public declarer hand",
        cli_args=(
            "--historical-game-review",
            "--samples",
            "20",
            "--seed",
            "42",
            "--quiet",
        ),
        check_output=check_historical_grand_ouvert_review,
        expect_quiet_stdout=True,
        include_position_overrides=False,
    ),
    Scenario(
        name="historical_grand_opponent_profile_review",
        input_path=(PROJECT_ROOT / "examples" / "historical_grand_normal_completion.json"),
        branch="time-safe external profiles applied by stable historical identity",
        cli_args=(
            "--historical-game-review",
            "--opponent-statistics-file",
            str(PROJECT_ROOT / "examples" / "historical_opponent_statistics.json"),
            "--use-profile-presets",
            "--samples",
            "20",
            "--seed",
            "42",
            "--quiet",
        ),
        check_output=check_historical_opponent_profile_review,
        expect_quiet_stdout=True,
        include_position_overrides=False,
    ),
    Scenario(
        name="training_dataset_normal_play",
        input_path=PROJECT_ROOT / "examples" / "training_dataset_normal_play.json",
        branch="versioned normal-play training dataset with 30 decision samples",
        cli_args=("--quiet",),
        check_output=check_training_dataset_normal_play,
        expect_quiet_stdout=True,
        include_position_overrides=False,
    ),
    Scenario(
        name="bounded_search_dataset_evaluation",
        input_path=PROJECT_ROOT / "examples" / "training_dataset_normal_play.json",
        branch="bounded Search versus Immediate dataset evaluation",
        cli_args=(
            "--evaluate-bounded-search",
            "--search-seed",
            "71",
            "--search-evaluation-max-decisions",
            "1",
            "--quiet",
        ),
        check_output=check_bounded_search_evaluation,
        expect_quiet_stdout=True,
        include_position_overrides=False,
    ),
    Scenario(
        name="training_dataset_variable_length",
        input_path=PROJECT_ROOT / "examples" / "training_dataset_variable_length.json",
        branch="variable-length concession training data with 14 decision samples",
        cli_args=("--quiet",),
        check_output=check_training_dataset_variable_length,
        expect_quiet_stdout=True,
        include_position_overrides=False,
    ),
    Scenario(
        name="historical_opponent_statistics_aggregation",
        input_path=PROJECT_ROOT / "examples" / "training_dataset_normal_play.json",
        branch="exact reusable historical aggregation and standalone export",
        cli_args=(
            "--aggregate-opponent-statistics",
            "--opponent-statistics-partition",
            "validation",
            "--opponent-statistics-partition",
            "train",
            "--opponent-statistics-before",
            "2026-07-21T00:00:00Z",
            "--quiet",
        ),
        check_output=check_historical_opponent_statistics,
        expect_quiet_stdout=True,
        include_position_overrides=False,
        export_opponent_statistics=True,
    ),
    Scenario(
        name="rolling_opponent_policy_evaluation",
        input_path=(
            PROJECT_ROOT / "examples" / "historical_opponent_policy_evaluation_dataset.json"
        ),
        branch="rolling as-of profile-derived behavioral policy evaluation",
        cli_args=("--evaluate-opponent-policy-profiles", "--quiet"),
        check_output=check_rolling_opponent_policy_evaluation,
        expect_quiet_stdout=True,
        include_position_overrides=False,
    ),
    Scenario(
        name="rolling_shortened_opponent_policy_evaluation",
        input_path=(
            PROJECT_ROOT
            / "examples"
            / "training_dataset_shortened_opponent_workflows.json"
        ),
        branch="rolling evaluation with concession source and variable target decisions",
        cli_args=("--evaluate-rolling-opponent-policies", "--quiet"),
        check_output=check_shortened_rolling_opponent_policy_evaluation,
        expect_quiet_stdout=True,
        include_position_overrides=False,
    ),
    Scenario(
        name="dataset_partition_audit",
        input_path=(PROJECT_ROOT / "examples" / "training_dataset_partition_audit.json"),
        branch="exact stable-player dataset partition overlap audit",
        cli_args=(
            "--audit-dataset-partitions",
            "--dataset-partition-mode",
            "known_opponent",
            "--quiet",
        ),
        check_output=check_dataset_partition_audit,
        expect_quiet_stdout=True,
        include_position_overrides=False,
    ),
    Scenario(
        name="opponent_statistics",
        input_path=PROJECT_ROOT / "examples" / "opponent_statistics.json",
        branch="versioned external statistics with explainable profile derivation",
        cli_args=("--quiet",),
        check_output=check_opponent_statistics,
        expect_quiet_stdout=True,
        include_position_overrides=False,
    ),
    Scenario(
        name="live_external_opponent_profiles",
        input_path=PROJECT_ROOT / "examples" / "grand_second_position.json",
        branch="two exact external player bindings applied to live side policies",
        cli_args=(
            "--opponent-statistics-file",
            str(PROJECT_ROOT / "examples" / "opponent_statistics.json"),
            "--left-opponent-player-id",
            "opponent-123",
            "--right-opponent-player-id",
            "opponent-789",
            "--use-profile-presets",
            "--quiet",
        ),
        check_output=check_live_external_opponent_profiles,
        expect_quiet_stdout=True,
    ),
    Scenario(
        name="historical_grand_replay_coaching",
        input_path=PROJECT_ROOT / "examples" / "historical_grand_normal_completion.json",
        branch="public Grand Replay Coaching with shared Historical Search Review",
        cli_args=(
            "--historical-search-review",
            "--historical-replay-coaching",
            "--search-seed",
            "71",
            "--search-budget-profile",
            "interactive_v1",
            "--samples",
            "1",
            "--seed",
            "42",
            "--quiet",
        ),
        check_output=check_historical_grand_replay_coaching,
        expect_quiet_stdout=True,
        include_position_overrides=False,
    ),
    Scenario(
        name="historical_null_replay_coaching",
        input_path=PROJECT_ROOT / "examples" / "historical_null_replay_coaching.json",
        branch="public Null Replay Coaching with no margin recommendation",
        cli_args=(
            "--historical-replay-coaching",
            "--search-seed",
            "73",
            "--search-budget-profile",
            "interactive_v1",
            "--samples",
            "1",
            "--seed",
            "43",
            "--quiet",
        ),
        check_output=check_historical_null_replay_coaching,
        expect_quiet_stdout=True,
        include_position_overrides=False,
    ),
    Scenario(
        name="historical_shortened_replay_coaching",
        input_path=(
            PROJECT_ROOT
            / "examples"
            / "historical_grand_defender_open_play_continuation_declarer_concession.json"
        ),
        branch="public Replay Coaching after continuation and terminal shortening",
        cli_args=(
            "--historical-decision-snapshots",
            "--historical-replay-coaching",
            "--search-seed",
            "79",
            "--search-budget-profile",
            "interactive_v1",
            "--samples",
            "1",
            "--seed",
            "44",
            "--quiet",
        ),
        check_output=check_historical_shortened_replay_coaching,
        expect_quiet_stdout=True,
        include_position_overrides=False,
    ),
    Scenario(
        name="fixed_three_player_historical_list_mixed",
        input_path=(
            PROJECT_ROOT / "examples" / "fixed_three_player_historical_list_mixed.json"
        ),
        branch="complete historical 36-position list with an applied external lot",
        cli_args=("--quiet",),
        check_output=check_fixed_three_player_historical_list_mixed,
        expect_quiet_stdout=True,
        include_position_overrides=False,
    ),
    Scenario(
        name="fixed_three_player_historical_list_all_passed",
        input_path=(
            PROJECT_ROOT
            / "examples"
            / "fixed_three_player_historical_list_all_passed.json"
        ),
        branch="all-Passed-Deal historical list with an unresolved three-player tie",
        cli_args=("--quiet",),
        check_output=check_fixed_three_player_historical_list_all_passed,
        expect_quiet_stdout=True,
        include_position_overrides=False,
    ),
    Scenario(
        name="fixed_three_player_historical_list_comparison",
        input_path=(
            PROJECT_ROOT
            / "examples"
            / "fixed_three_player_historical_list_comparison.json"
        ),
        branch="compact comparison of two independent completed historical lists",
        cli_args=("--quiet",),
        check_output=check_fixed_three_player_historical_list_comparison,
        expect_quiet_stdout=True,
        include_position_overrides=False,
    ),
    Scenario(
        name="training_dataset_preparation_known_opponent",
        input_path=(
            PROJECT_ROOT / "examples" / "training_dataset_preparation_known_opponent.json"
        ),
        branch="complete temporal Known-opponent automatic Dataset preparation",
        cli_args=("--quiet",),
        check_output=check_training_dataset_preparation_known_opponent,
        expect_quiet_stdout=True,
        include_position_overrides=False,
    ),
    Scenario(
        name="training_dataset_preparation_unseen_player",
        input_path=(
            PROJECT_ROOT / "examples" / "training_dataset_preparation_unseen_player.json"
        ),
        branch="complete player-disjoint unseen-player automatic Dataset preparation",
        cli_args=("--quiet",),
        check_output=check_training_dataset_preparation_unseen_player,
        expect_quiet_stdout=True,
        include_position_overrides=False,
    ),
    Scenario(
        name="training_dataset_preparation_unavailable",
        input_path=(
            PROJECT_ROOT / "examples" / "training_dataset_preparation_unavailable.json"
        ),
        branch="valid unavailable automatic Dataset preparation",
        cli_args=("--quiet",),
        check_output=check_training_dataset_preparation_unavailable,
        expect_quiet_stdout=True,
        include_position_overrides=False,
    ),
    Scenario(
        name="field_provenance_position_analysis",
        input_path=PROJECT_ROOT / "examples" / "defender_open_play.json",
        branch="public field provenance for Position Analysis",
        cli_args=("--quiet",),
        check_output=check_defender_open_play,
        expect_quiet_stdout=True,
        include_provenance=True,
    ),
    Scenario(
        name="field_provenance_historical_game",
        input_path=PROJECT_ROOT / "examples" / "historical_grand_declarer_concession.json",
        branch="public field provenance for Historical Game",
        cli_args=("--quiet",),
        check_output=check_historical_declarer_concession,
        expect_quiet_stdout=True,
        include_position_overrides=False,
        include_provenance=True,
    ),
    Scenario(
        name="field_provenance_training_dataset",
        input_path=PROJECT_ROOT / "examples" / "training_dataset_variable_length.json",
        branch="public Result and actual Artifact field provenance for Training Dataset",
        cli_args=("--aggregate-opponent-statistics", "--quiet"),
        expect_quiet_stdout=True,
        include_position_overrides=False,
        export_opponent_statistics=True,
        include_provenance=True,
    ),
    Scenario(
        name="field_provenance_training_dataset_preparation",
        input_path=(
            PROJECT_ROOT / "examples" / "training_dataset_preparation_unavailable.json"
        ),
        branch="public field provenance for a valid unavailable Dataset Preparation Result",
        cli_args=("--quiet",),
        check_output=check_training_dataset_preparation_unavailable,
        expect_quiet_stdout=True,
        include_position_overrides=False,
        include_provenance=True,
    ),
    Scenario(
        name="field_provenance_opponent_statistics",
        input_path=PROJECT_ROOT / "examples" / "opponent_statistics.json",
        branch="public field provenance for Opponent Statistics",
        cli_args=("--quiet",),
        check_output=check_opponent_statistics,
        expect_quiet_stdout=True,
        include_position_overrides=False,
        include_provenance=True,
    ),
    Scenario(
        name="field_provenance_fixed_three_player_historical_list",
        input_path=(
            PROJECT_ROOT / "examples" / "fixed_three_player_historical_list_all_passed.json"
        ),
        branch="public field provenance for a fixed-three-player Historical List",
        cli_args=("--quiet",),
        check_output=check_fixed_three_player_historical_list_all_passed,
        expect_quiet_stdout=True,
        include_position_overrides=False,
        include_provenance=True,
    ),
    Scenario(
        name="field_provenance_fixed_three_player_historical_list_comparison",
        input_path=(
            PROJECT_ROOT / "examples" / "fixed_three_player_historical_list_comparison.json"
        ),
        branch="public field provenance for Historical List Comparison",
        cli_args=("--quiet",),
        check_output=check_fixed_three_player_historical_list_comparison,
        expect_quiet_stdout=True,
        include_position_overrides=False,
        include_provenance=True,
    ),
    Scenario(
        name="session_live_create",
        input_path=PROJECT_ROOT / "examples" / "session_create_live.json",
        branch="public Live Session creation with normal unavailable readiness",
        include_provenance=True,
        session_orchestration="live_create",
        session_output_definition="session_api_result",
    ),
    Scenario(
        name="session_live_apply_and_resume",
        input_path=PROJECT_ROOT / "examples" / "session_command_record_play.json",
        branch="accepted local Play with automatic Checkpoint deduplication and strict Resume",
        include_provenance=True,
        session_orchestration="live_apply_and_resume",
        session_output_definition="session_api_result",
    ),
    Scenario(
        name="session_live_analyze_with_checkpoint",
        input_path=PROJECT_ROOT / "examples" / "session_live_persistence.json",
        branch="Session-triggered Position Analysis with an exact existing Checkpoint",
        include_provenance=True,
        session_orchestration="live_analyze_with_checkpoint",
    ),
    Scenario(
        name="session_live_observed_card_review",
        input_path=PROJECT_ROOT / "examples" / "session_command_record_play.json",
        branch="observed-card Checkpoint review isolated to the frozen Position Request",
        session_orchestration="live_observed_card_review",
    ),
    Scenario(
        name="session_undo_and_partial_correction",
        input_path=PROJECT_ROOT / "examples" / "session_correction_record_play.json",
        branch="strict-prefix Undo and first-rejection partial Session Correction",
        session_orchestration="undo_and_partial_correction",
        session_output_definition="session_api_result",
    ),
    Scenario(
        name="session_persistence_conflict",
        input_path=PROJECT_ROOT / "examples" / "session_live_persistence.json",
        branch="optimistic Session persistence conflict without target replacement",
        session_orchestration="persistence_conflict",
        session_output_definition="session_file_api_result",
    ),
    Scenario(
        name="session_retrospective_export",
        input_path=(
            PROJECT_ROOT / "examples" / "session_retrospective_persistence.json"
        ),
        branch="canonical zero-decision Retrospective Historical Request export",
        include_provenance=True,
        session_orchestration="retrospective_export",
        session_output_definition="session_api_result",
    ),
    Scenario(
        name="session_retrospective_finalize",
        input_path=(
            PROJECT_ROOT / "examples" / "session_retrospective_persistence.json"
        ),
        branch="Session-triggered zero-decision Historical execution",
        include_provenance=True,
        session_orchestration="retrospective_finalize",
    ),
    Scenario(
        name="historical_party_wide_claim_declarer_suit",
        input_path=PROJECT_ROOT / "examples" / "historical_party_wide_claim.json",
        branch="valid declarer Suit party-wide Claim with exact adjudication",
        cli_args=("--quiet",),
        check_output=check_historical_party_wide_claim,
        expect_quiet_stdout=True,
        include_position_overrides=False,
        include_provenance=True,
    ),
    Scenario(
        name="historical_party_wide_claim_defenders_null_incomplete_trick",
        input_path=(
            PROJECT_ROOT
            / "tests"
            / "fixtures"
            / "generated_output_schema"
            / "historical_party_wide_claim_defenders_null_incomplete_trick.json"
        ),
        branch="valid defender Null Claim during an incomplete final Trick",
        cli_args=("--quiet",),
        check_output=check_historical_party_wide_claim,
        expect_quiet_stdout=True,
        include_position_overrides=False,
    ),
    Scenario(
        name="historical_continuation_then_party_wide_claim",
        input_path=(
            PROJECT_ROOT
            / "tests"
            / "fixtures"
            / "generated_output_schema"
            / "historical_continuation_then_party_wide_claim.json"
        ),
        branch="one defender-open-play continuation before a valid final Claim",
        cli_args=("--quiet",),
        check_output=check_historical_party_wide_claim,
        expect_quiet_stdout=True,
        include_position_overrides=False,
    ),
    Scenario(
        name="information_set_search_live_complete",
        input_path=PROJECT_ROOT / "examples" / "information_set_search.json",
        branch="complete information-set Search with safe public aggregate output",
        cli_args=("--quiet",),
        check_output=check_information_set_search_live_complete,
        expect_quiet_stdout=True,
        include_provenance=True,
    ),
    Scenario(
        name="information_set_search_post_game_comparison",
        input_path=(
            PROJECT_ROOT
            / "tests"
            / "fixtures"
            / "generated_output_schema"
            / "information_set_search_post_game_comparison.json"
        ),
        branch="retrospective same-selection PIMC and Immediate comparison",
        cli_args=("--quiet",),
        check_output=check_information_set_search_post_game_comparison,
        expect_quiet_stdout=True,
    ),
    Scenario(
        name="historical_information_set_search_review",
        input_path=PROJECT_ROOT / "examples" / "historical_grand_normal_completion.json",
        branch="decision-time historical information-set Search review",
        cli_args=(
            "--historical-information-set-search-review",
            "--search-seed",
            "83",
            "--search-budget-profile",
            "interactive_v1",
            "--samples",
            "1",
            "--seed",
            "47",
            "--quiet",
        ),
        check_output=check_historical_information_set_search_review,
        expect_quiet_stdout=True,
        include_position_overrides=False,
    ),
    Scenario(
        name="training_dataset_information_set_search_evaluation",
        input_path=PROJECT_ROOT / "examples" / "training_dataset_normal_play.json",
        branch="information-set Search Dataset evaluation without training",
        cli_args=(
            "--information-set-search-evaluation",
            "--search-seed",
            "89",
            "--search-evaluation-max-decisions",
            "1",
            "--quiet",
        ),
        check_output=check_information_set_search_evaluation,
        expect_quiet_stdout=True,
        include_position_overrides=False,
    ),
    Scenario(
        name="information_set_search_multi_step",
        input_path=(
            PROJECT_ROOT / "examples" / "information_set_search_multi_step.json"
        ),
        branch="fresh strict information-set Search in one Multi-Step decision",
        cli_args=("--multi-step", "1", "--quiet"),
        check_output=check_information_set_search_multi_step,
        expect_quiet_stdout=True,
        include_provenance=True,
    ),
    Scenario(
        name="information_set_search_policy_comparison",
        input_path=(
            PROJECT_ROOT / "examples" / "information_set_search_multi_step.json"
        ),
        branch="Information-set Search appended last to coherent Policy Comparison",
        cli_args=("--multi-step", "1", "--compare-policies", "--quiet"),
        check_output=check_information_set_search_policy_comparison,
        expect_quiet_stdout=True,
    ),
    Scenario(
        name="historical_information_set_replay_coaching",
        input_path=(
            PROJECT_ROOT
            / "examples"
            / "historical_information_set_replay_coaching.json"
        ),
        branch="privacy-safe Historical Information-set Replay Coaching",
        cli_args=(
            "--historical-information-set-replay-coaching",
            "--search-seed",
            "83",
            "--search-budget-profile",
            "interactive_v1",
            "--samples",
            "1",
            "--seed",
            "47",
            "--quiet",
        ),
        check_output=check_historical_information_set_replay_coaching,
        expect_quiet_stdout=True,
        include_position_overrides=False,
        include_provenance=True,
    ),
    Scenario(
        name="historical_party_wide_claim_information_set_replay_coaching",
        input_path=PROJECT_ROOT / "examples" / "historical_party_wide_claim.json",
        branch="party-wide Claim Historical Information-set Replay Coaching",
        cli_args=(
            "--historical-information-set-replay-coaching",
            "--search-seed",
            "97",
            "--search-budget-profile",
            "interactive_v1",
            "--samples",
            "1",
            "--seed",
            "53",
            "--quiet",
        ),
        check_output=(
            check_historical_party_wide_claim_information_set_replay_coaching
        ),
        expect_quiet_stdout=True,
        include_position_overrides=False,
    ),
    Scenario(
        name="historical_tactical_motif_review_defender_partnership",
        input_path=(PROJECT_ROOT / "examples" / "historical_tactical_motif_review.json"),
        branch="deterministic Historical Defender-partnership tactical motifs",
        cli_args=("--historical-tactical-motif-review", "--quiet"),
        check_output=check_historical_tactical_motif_defender_partnership,
        expect_quiet_stdout=True,
        include_position_overrides=False,
        include_provenance=True,
    ),
    Scenario(
        name="historical_party_wide_claim_tactical_motif_review",
        input_path=PROJECT_ROOT / "examples" / "historical_party_wide_claim.json",
        branch="party-wide Claim Historical Tactical Motif Review",
        cli_args=("--historical-tactical-motif-review", "--quiet"),
        check_output=check_historical_party_wide_claim_tactical_motif_review,
        expect_quiet_stdout=True,
        include_position_overrides=False,
    ),
)


def validate_generated_outputs() -> list[str]:
    """
    Generates selected example outputs and validates them against the output schema.
    """
    schema = load_json_file(SCHEMA_PATH)
    input_schema = load_json_file(INPUT_SCHEMA_PATH)
    session_schema = load_json_file(SESSION_SCHEMA_PATH)
    historical_decision_snapshot_schema = load_json_file(HISTORICAL_DECISION_SNAPSHOT_SCHEMA_PATH)
    historical_game_review_schema = load_json_file(HISTORICAL_GAME_REVIEW_SCHEMA_PATH)
    historical_game_schema = load_json_file(HISTORICAL_GAME_SCHEMA_PATH)
    historical_game_end_schema = load_json_file(HISTORICAL_GAME_END_SCHEMA_PATH)
    historical_game_event_schema = load_json_file(HISTORICAL_GAME_EVENT_SCHEMA_PATH)
    historical_continuation_event_schema = load_json_file(
        HISTORICAL_DEFENDER_OPEN_PLAY_CONTINUATION_EVENT_SCHEMA_PATH
    )
    historical_declarer_continuation_event_schema = load_json_file(
        HISTORICAL_DECLARER_CARD_EXPOSURE_CONTINUATION_EVENT_SCHEMA_PATH
    )
    historical_declarer_continuation_event_output_schema = load_json_file(
        HISTORICAL_DECLARER_CARD_EXPOSURE_CONTINUATION_EVENT_OUTPUT_SCHEMA_PATH
    )
    historical_game_events_output_schema = load_json_file(
        HISTORICAL_GAME_EVENTS_OUTPUT_SCHEMA_PATH
    )
    historical_declarer_concession_schema = load_json_file(
        HISTORICAL_DECLARER_CONCESSION_SCHEMA_PATH
    )
    historical_declarer_concession_output_schema = load_json_file(
        HISTORICAL_DECLARER_CONCESSION_OUTPUT_SCHEMA_PATH
    )
    historical_defender_concession_schema = load_json_file(
        HISTORICAL_DEFENDER_CONCESSION_SCHEMA_PATH
    )
    historical_defender_concession_output_schema = load_json_file(
        HISTORICAL_DEFENDER_CONCESSION_OUTPUT_SCHEMA_PATH
    )
    historical_declarer_card_exposure_schema = load_json_file(
        HISTORICAL_DECLARER_CARD_EXPOSURE_SCHEMA_PATH
    )
    historical_declarer_card_exposure_output_schema = load_json_file(
        HISTORICAL_DECLARER_CARD_EXPOSURE_OUTPUT_SCHEMA_PATH
    )
    historical_defender_open_play_schema = load_json_file(
        HISTORICAL_DEFENDER_OPEN_PLAY_SCHEMA_PATH
    )
    historical_defender_open_play_output_schema = load_json_file(
        HISTORICAL_DEFENDER_OPEN_PLAY_OUTPUT_SCHEMA_PATH
    )
    historical_open_card_throw_schema = load_json_file(
        HISTORICAL_OPEN_CARD_THROW_SCHEMA_PATH
    )
    historical_open_card_throw_output_schema = load_json_file(
        HISTORICAL_OPEN_CARD_THROW_OUTPUT_SCHEMA_PATH
    )
    historical_party_wide_claim_schema = load_json_file(
        HISTORICAL_PARTY_WIDE_CLAIM_SCHEMA_PATH
    )
    historical_party_wide_claim_output_schema = load_json_file(
        HISTORICAL_PARTY_WIDE_CLAIM_OUTPUT_SCHEMA_PATH
    )
    training_dataset_output_schema = load_json_file(TRAINING_DATASET_OUTPUT_SCHEMA_PATH)
    training_dataset_schema = load_json_file(TRAINING_DATASET_SCHEMA_PATH)
    dataset_partition_plan_schema = load_json_file(DATASET_PARTITION_PLAN_SCHEMA_PATH)
    training_dataset_preparation_output_schema = load_json_file(
        TRAINING_DATASET_PREPARATION_OUTPUT_SCHEMA_PATH
    )
    opponent_statistics_output_schema = load_json_file(OPPONENT_STATISTICS_OUTPUT_SCHEMA_PATH)
    opponent_statistics_input_schema = load_json_file(OPPONENT_STATISTICS_INPUT_SCHEMA_PATH)
    historical_opponent_statistics_aggregation_schema = load_json_file(
        HISTORICAL_OPPONENT_STATISTICS_AGGREGATION_SCHEMA_PATH
    )
    opponent_profile_derivation_schema = load_json_file(OPPONENT_PROFILE_DERIVATION_SCHEMA_PATH)
    opponent_profile_application_schema = load_json_file(OPPONENT_PROFILE_APPLICATION_SCHEMA_PATH)
    historical_opponent_profile_application_schema = load_json_file(
        HISTORICAL_OPPONENT_PROFILE_APPLICATION_SCHEMA_PATH
    )
    rolling_opponent_policy_evaluation_schema = load_json_file(
        ROLLING_OPPONENT_POLICY_EVALUATION_SCHEMA_PATH
    )
    dataset_partition_policy_schema = load_json_file(DATASET_PARTITION_POLICY_SCHEMA_PATH)
    dataset_partition_audit_schema = load_json_file(DATASET_PARTITION_AUDIT_SCHEMA_PATH)
    declarer_concession_output_schema = load_json_file(DECLARER_CONCESSION_OUTPUT_SCHEMA_PATH)
    defender_concession_output_schema = load_json_file(DEFENDER_CONCESSION_OUTPUT_SCHEMA_PATH)
    declarer_card_exposure_output_schema = load_json_file(DECLARER_CARD_EXPOSURE_OUTPUT_SCHEMA_PATH)
    defender_open_play_output_schema = load_json_file(DEFENDER_OPEN_PLAY_OUTPUT_SCHEMA_PATH)
    open_card_throw_output_schema = load_json_file(OPEN_CARD_THROW_OUTPUT_SCHEMA_PATH)
    theoretical_level_assessment_schema = load_json_file(
        THEORETICAL_LEVEL_ASSESSMENT_SCHEMA_PATH
    )
    exact_rest_trick_proof_schema = load_json_file(EXACT_REST_TRICK_PROOF_SCHEMA_PATH)
    declarer_card_exposure_continuation_output_schema = load_json_file(
        DECLARER_CARD_EXPOSURE_CONTINUATION_OUTPUT_SCHEMA_PATH
    )
    defender_open_play_continuation_output_schema = load_json_file(
        DEFENDER_OPEN_PLAY_CONTINUATION_OUTPUT_SCHEMA_PATH
    )
    public_hand_constraint_schema = load_json_file(PUBLIC_HAND_CONSTRAINT_SCHEMA_PATH)
    hidden_card_inference_summary_schema = load_json_file(
        HIDDEN_CARD_INFERENCE_SUMMARY_SCHEMA_PATH
    )
    bounded_search_result_schema = load_json_file(BOUNDED_SEARCH_RESULT_SCHEMA_PATH)
    bounded_search_post_game_review_schema = load_json_file(
        BOUNDED_SEARCH_POST_GAME_REVIEW_SCHEMA_PATH
    )
    historical_search_review_schema = load_json_file(
        HISTORICAL_SEARCH_REVIEW_SCHEMA_PATH
    )
    historical_replay_coaching_schema = load_json_file(
        HISTORICAL_REPLAY_COACHING_SCHEMA_PATH
    )
    bounded_search_evaluation_schema = load_json_file(
        BOUNDED_SEARCH_EVALUATION_SCHEMA_PATH
    )
    information_set_search_result_schema = load_json_file(
        INFORMATION_SET_SEARCH_RESULT_SCHEMA_PATH
    )
    information_set_search_comparison_schema = load_json_file(
        INFORMATION_SET_SEARCH_COMPARISON_SCHEMA_PATH
    )
    historical_information_set_search_review_schema = load_json_file(
        HISTORICAL_INFORMATION_SET_SEARCH_REVIEW_SCHEMA_PATH
    )
    historical_information_set_replay_coaching_schema = load_json_file(
        HISTORICAL_INFORMATION_SET_REPLAY_COACHING_SCHEMA_PATH
    )
    historical_tactical_motif_review_schema = load_json_file(
        HISTORICAL_TACTICAL_MOTIF_REVIEW_SCHEMA_PATH
    )
    information_set_search_evaluation_schema = load_json_file(
        INFORMATION_SET_SEARCH_EVALUATION_SCHEMA_PATH
    )
    historical_list_aggregation_schema = load_json_file(
        FIXED_THREE_PLAYER_HISTORICAL_LIST_AGGREGATION_SCHEMA_PATH
    )
    historical_list_comparison_schema = load_json_file(
        FIXED_THREE_PLAYER_HISTORICAL_LIST_COMPARISON_SCHEMA_PATH
    )
    field_provenance_schema = load_json_file(FIELD_PROVENANCE_SCHEMA_PATH)
    registry = Registry().with_resources(
        [
            (
                historical_decision_snapshot_schema["$id"],
                Resource.from_contents(historical_decision_snapshot_schema),
            ),
            (
                historical_game_review_schema["$id"],
                Resource.from_contents(historical_game_review_schema),
            ),
            (
                historical_game_schema["$id"],
                Resource.from_contents(historical_game_schema),
            ),
            (
                historical_game_end_schema["$id"],
                Resource.from_contents(historical_game_end_schema),
            ),
            (
                historical_game_event_schema["$id"],
                Resource.from_contents(historical_game_event_schema),
            ),
            (
                historical_continuation_event_schema["$id"],
                Resource.from_contents(historical_continuation_event_schema),
            ),
            (
                historical_declarer_continuation_event_schema["$id"],
                Resource.from_contents(historical_declarer_continuation_event_schema),
            ),
            (
                historical_declarer_continuation_event_output_schema["$id"],
                Resource.from_contents(
                    historical_declarer_continuation_event_output_schema
                ),
            ),
            (
                historical_game_events_output_schema["$id"],
                Resource.from_contents(historical_game_events_output_schema),
            ),
            (
                historical_declarer_concession_schema["$id"],
                Resource.from_contents(historical_declarer_concession_schema),
            ),
            (
                historical_declarer_concession_output_schema["$id"],
                Resource.from_contents(historical_declarer_concession_output_schema),
            ),
            (
                historical_defender_concession_schema["$id"],
                Resource.from_contents(historical_defender_concession_schema),
            ),
            (
                historical_defender_concession_output_schema["$id"],
                Resource.from_contents(historical_defender_concession_output_schema),
            ),
            (
                historical_declarer_card_exposure_schema["$id"],
                Resource.from_contents(historical_declarer_card_exposure_schema),
            ),
            (
                historical_declarer_card_exposure_output_schema["$id"],
                Resource.from_contents(historical_declarer_card_exposure_output_schema),
            ),
            (
                historical_defender_open_play_schema["$id"],
                Resource.from_contents(historical_defender_open_play_schema),
            ),
            (
                historical_defender_open_play_output_schema["$id"],
                Resource.from_contents(historical_defender_open_play_output_schema),
            ),
            (
                historical_open_card_throw_schema["$id"],
                Resource.from_contents(historical_open_card_throw_schema),
            ),
            (
                historical_open_card_throw_output_schema["$id"],
                Resource.from_contents(historical_open_card_throw_output_schema),
            ),
            (
                historical_party_wide_claim_schema["$id"],
                Resource.from_contents(historical_party_wide_claim_schema),
            ),
            (
                historical_party_wide_claim_output_schema["$id"],
                Resource.from_contents(historical_party_wide_claim_output_schema),
            ),
            (
                training_dataset_output_schema["$id"],
                Resource.from_contents(training_dataset_output_schema),
            ),
            (
                training_dataset_schema["$id"],
                Resource.from_contents(training_dataset_schema),
            ),
            (
                dataset_partition_plan_schema["$id"],
                Resource.from_contents(dataset_partition_plan_schema),
            ),
            (
                training_dataset_preparation_output_schema["$id"],
                Resource.from_contents(training_dataset_preparation_output_schema),
            ),
            (
                opponent_statistics_output_schema["$id"],
                Resource.from_contents(opponent_statistics_output_schema),
            ),
            (
                historical_opponent_statistics_aggregation_schema["$id"],
                Resource.from_contents(historical_opponent_statistics_aggregation_schema),
            ),
            (
                opponent_profile_derivation_schema["$id"],
                Resource.from_contents(opponent_profile_derivation_schema),
            ),
            (
                opponent_profile_application_schema["$id"],
                Resource.from_contents(opponent_profile_application_schema),
            ),
            (
                historical_opponent_profile_application_schema["$id"],
                Resource.from_contents(historical_opponent_profile_application_schema),
            ),
            (
                rolling_opponent_policy_evaluation_schema["$id"],
                Resource.from_contents(rolling_opponent_policy_evaluation_schema),
            ),
            (
                dataset_partition_policy_schema["$id"],
                Resource.from_contents(dataset_partition_policy_schema),
            ),
            (
                dataset_partition_audit_schema["$id"],
                Resource.from_contents(dataset_partition_audit_schema),
            ),
            (
                declarer_concession_output_schema["$id"],
                Resource.from_contents(declarer_concession_output_schema),
            ),
            (
                defender_concession_output_schema["$id"],
                Resource.from_contents(defender_concession_output_schema),
            ),
            (
                declarer_card_exposure_output_schema["$id"],
                Resource.from_contents(declarer_card_exposure_output_schema),
            ),
            (
                defender_open_play_output_schema["$id"],
                Resource.from_contents(defender_open_play_output_schema),
            ),
            (
                open_card_throw_output_schema["$id"],
                Resource.from_contents(open_card_throw_output_schema),
            ),
            (
                theoretical_level_assessment_schema["$id"],
                Resource.from_contents(theoretical_level_assessment_schema),
            ),
            (
                exact_rest_trick_proof_schema["$id"],
                Resource.from_contents(exact_rest_trick_proof_schema),
            ),
            (
                declarer_card_exposure_continuation_output_schema["$id"],
                Resource.from_contents(declarer_card_exposure_continuation_output_schema),
            ),
            (
                defender_open_play_continuation_output_schema["$id"],
                Resource.from_contents(defender_open_play_continuation_output_schema),
            ),
            (
                public_hand_constraint_schema["$id"],
                Resource.from_contents(public_hand_constraint_schema),
            ),
            (
                hidden_card_inference_summary_schema["$id"],
                Resource.from_contents(hidden_card_inference_summary_schema),
            ),
            (
                bounded_search_result_schema["$id"],
                Resource.from_contents(bounded_search_result_schema),
            ),
            (
                bounded_search_post_game_review_schema["$id"],
                Resource.from_contents(bounded_search_post_game_review_schema),
            ),
            (
                historical_search_review_schema["$id"],
                Resource.from_contents(historical_search_review_schema),
            ),
            (
                historical_replay_coaching_schema["$id"],
                Resource.from_contents(historical_replay_coaching_schema),
            ),
            (
                bounded_search_evaluation_schema["$id"],
                Resource.from_contents(bounded_search_evaluation_schema),
            ),
            (
                information_set_search_result_schema["$id"],
                Resource.from_contents(information_set_search_result_schema),
            ),
            (
                information_set_search_comparison_schema["$id"],
                Resource.from_contents(information_set_search_comparison_schema),
            ),
            (
                historical_information_set_search_review_schema["$id"],
                Resource.from_contents(
                    historical_information_set_search_review_schema
                ),
            ),
            (
                historical_information_set_replay_coaching_schema["$id"],
                Resource.from_contents(
                    historical_information_set_replay_coaching_schema
                ),
            ),
            (
                historical_tactical_motif_review_schema["$id"],
                Resource.from_contents(historical_tactical_motif_review_schema),
            ),
            (
                information_set_search_evaluation_schema["$id"],
                Resource.from_contents(information_set_search_evaluation_schema),
            ),
            (
                historical_list_aggregation_schema["$id"],
                Resource.from_contents(historical_list_aggregation_schema),
            ),
            (
                historical_list_comparison_schema["$id"],
                Resource.from_contents(historical_list_comparison_schema),
            ),
            (
                field_provenance_schema["$id"],
                Resource.from_contents(field_provenance_schema),
            ),
            (input_schema["$id"], Resource.from_contents(input_schema)),
            (session_schema["$id"], Resource.from_contents(session_schema)),
        ]
    )
    validator = Draft202012Validator(schema, registry=registry)
    session_validators = {
        definition: Draft202012Validator(
            {"$ref": f"{session_schema['$id']}#/$defs/{definition}"},
            registry=registry,
        )
        for definition in ("session_api_result", "session_file_api_result")
    }
    training_dataset_input_validator = Draft202012Validator(
        training_dataset_schema,
        registry=registry,
    )
    opponent_statistics_input_validator = Draft202012Validator(opponent_statistics_input_schema)
    errors = []

    with tempfile.TemporaryDirectory() as temporary_directory:
        temporary_path = Path(temporary_directory)

        for scenario_index, scenario in enumerate(SCENARIOS):
            output_path = temporary_path / f"{scenario.name}.output.json"

            if scenario.session_orchestration is None:
                generation_errors = run_analysis(
                    scenario=scenario,
                    output_path=output_path,
                )
            else:
                generation_errors = run_session_scenario(
                    scenario=scenario,
                    output_path=output_path,
                    temporary_path=temporary_path,
                )
            if generation_errors:
                return generation_errors

            if scenario.session_orchestration is not None:
                regeneration_path = temporary_path / "regenerated"
                regeneration_path.mkdir(exist_ok=True)
                regenerated_output_path = regeneration_path / output_path.name
                regeneration_errors = run_session_scenario(
                    scenario=scenario,
                    output_path=regenerated_output_path,
                    temporary_path=regeneration_path,
                )
                if regeneration_errors:
                    return regeneration_errors
                if regenerated_output_path.read_bytes() != output_path.read_bytes():
                    return [
                        format_scenario_error(
                            scenario,
                            "Session output bytes changed across deterministic regeneration",
                        )
                    ]

            data, validation_errors = validate_output_file(
                validator=(
                    validator
                    if scenario.session_output_definition is None
                    else session_validators[scenario.session_output_definition]
                ),
                scenario=scenario,
                output_path=output_path,
            )
            if validation_errors:
                return validation_errors

            if data is None:
                return [
                    format_scenario_error(
                        scenario=scenario,
                        message="generated output could not be parsed",
                    )
                ]
            if scenario_index < 77 and (
                "public_session_api_version" in data
                or "public_session_file_api_version" in data
            ):
                return [
                    format_scenario_error(
                        scenario,
                        "a previous generated output unexpectedly became Session output",
                    )
                ]

            branch_data = dict(data)
            branch_data.pop("field_provenance", None)
            if scenario.check_output is not None:
                branch_errors = [
                    format_scenario_error(scenario=scenario, message=error)
                    for error in scenario.check_output(branch_data)
                ]
                if branch_errors:
                    return branch_errors
            if scenario.session_output_definition is not None:
                if scenario.check_output is not None:
                    return [
                        format_scenario_error(
                            scenario,
                            "Session output must not use an Engine branch checker",
                        )
                    ]
                unexpected_engine_fields = sorted(
                    {"analysis_report", "historical_game_summary", "recommendation"}
                    & set(data)
                )
                if unexpected_engine_fields:
                    return [
                        format_scenario_error(
                            scenario,
                            "Session-only orchestration unexpectedly executed analysis: "
                            f"{unexpected_engine_fields}",
                        )
                    ]
                continue
            preparation_summary = data.get("training_dataset_preparation_summary")
            if (
                preparation_summary is not None
                and preparation_summary["training_dataset_input"] is not None
            ):
                nested_errors = list(
                    training_dataset_input_validator.iter_errors(
                        preparation_summary["training_dataset_input"]
                    )
                )
                if nested_errors:
                    return [
                        format_validation_error(
                            scenario,
                            output_path,
                            nested_errors[0],
                        )
                    ]
            export_data = None
            if scenario.export_opponent_statistics:
                export_path = output_path.with_suffix(".export.json")
                if not export_path.exists():
                    return [
                        format_scenario_error(
                            scenario,
                            "standalone opponent-statistics export was not created",
                        )
                    ]
                export_data = load_json_file(export_path)
                if set(export_data) != {"opponent_statistics_input"}:
                    return [
                        format_scenario_error(
                            scenario,
                            "export is not a standalone opponent_statistics_input",
                        )
                    ]
                export_errors = list(
                    opponent_statistics_input_validator.iter_errors(
                        export_data["opponent_statistics_input"]
                    )
                )
                if export_errors:
                    return [
                        format_validation_error(
                            scenario,
                            export_path,
                            export_errors[0],
                        )
                    ]
            provenance_errors = [
                format_scenario_error(scenario=scenario, message=error)
                for error in check_public_field_provenance(
                    data,
                    scenario,
                    export_data,
                )
            ]
            if provenance_errors:
                return provenance_errors

    return errors


def main() -> int:
    """
    Runs generated-output schema validation.
    """
    errors = validate_generated_outputs()

    if errors:
        print("Generated output JSON schema validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(
        f"Generated {len(SCENARIOS)} outputs match the Engine and Session schemas."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
