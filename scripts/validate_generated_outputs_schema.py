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

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = PROJECT_ROOT / "schemas" / "output.schema.json"
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
TRAINING_DATASET_OUTPUT_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "training_dataset_output.schema.json"
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


def check_unsupported_multi_step_phase(data: dict[str, Any]) -> list[str]:
    """
    Checks the valid but unsupported Multi-Step phase stop branch.
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

    if multi_step_result["stop_reason"] != "unsupported_turn_phase":
        errors.append("expected unsupported_turn_phase stop reason")

    if multi_step_result["steps_simulated"] != 0:
        errors.append("expected no simulated steps for unsupported phase")

    if multi_step_result["steps"] != []:
        errors.append("expected no candidate simulation steps")

    final_state = multi_step_result["final_state"]
    for field_name in ["hand", "current_trick", "trick_leader", "next_player"]:
        if final_state[field_name] != data["position"][field_name]:
            errors.append(f"expected final_state.{field_name} to be unchanged")

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
        branch="unsupported valid Multi-Step phase with no candidate step",
        cli_args=(
            "--multi-step",
            "1",
            "--card-policy",
            "highest_point",
            "--expected-value-samples",
            "20",
        ),
        check_output=check_unsupported_multi_step_phase,
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
)


def validate_generated_outputs() -> list[str]:
    """
    Generates selected example outputs and validates them against the output schema.
    """
    schema = load_json_file(SCHEMA_PATH)
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
    training_dataset_output_schema = load_json_file(TRAINING_DATASET_OUTPUT_SCHEMA_PATH)
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
                training_dataset_output_schema["$id"],
                Resource.from_contents(training_dataset_output_schema),
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
        ]
    )
    validator = Draft202012Validator(schema, registry=registry)
    opponent_statistics_input_validator = Draft202012Validator(opponent_statistics_input_schema)
    errors = []

    with tempfile.TemporaryDirectory() as temporary_directory:
        temporary_path = Path(temporary_directory)

        for scenario in SCENARIOS:
            output_path = temporary_path / f"{scenario.name}.output.json"

            generation_errors = run_analysis(
                scenario=scenario,
                output_path=output_path,
            )
            if generation_errors:
                return generation_errors

            data, validation_errors = validate_output_file(
                validator=validator,
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

            if scenario.check_output is not None:
                branch_errors = [
                    format_scenario_error(scenario=scenario, message=error)
                    for error in scenario.check_output(data)
                ]
                if branch_errors:
                    return branch_errors
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

    print(f"Generated {len(SCENARIOS)} outputs match schemas/output.schema.json.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
