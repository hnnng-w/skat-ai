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

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = PROJECT_ROOT / "schemas" / "output.schema.json"
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
    return (
        f"{scenario.name} ({scenario.branch}; input: {scenario.input_path}): "
        f"{message}"
    )


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
        "--samples",
        DEFAULT_SAMPLE_COUNT,
        "--seed",
        DEFAULT_RANDOM_SEED,
        *scenario.cli_args,
    ]

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

    if multi_step_result["left_opponent_policy_settings"] != (
        data["left_opponent_policy_settings"]
    ):
        errors.append("expected multi-step left opponent settings to match top level")

    if multi_step_result["right_opponent_policy_settings"] != (
        data["right_opponent_policy_settings"]
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

    if (
        information_policy["unverifiable_completed_trick_winner_metadata_allowed"]
        is not False
    ):
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
        input_path=(
            PROJECT_ROOT / "examples" / "spades_post_game_actual_card_played.json"
        ),
        branch="actual-card post-game review and nested Suit declaration output",
        check_output=check_post_game_available_nested_suit,
    ),
    Scenario(
        name="post_game_null_objective_review",
        input_path=(
            PROJECT_ROOT / "examples" / "null_post_game_objective_actual_card.json"
        ),
        branch="actual-card post-game review using the Null contract objective",
        check_output=check_post_game_null_objective_review,
    ),
    Scenario(
        name="post_game_defender_perspective_review",
        input_path=(
            PROJECT_ROOT / "examples" / "spades_post_game_defender_actual_card.json"
        ),
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
        input_path=(
            PROJECT_ROOT / "examples" / "grand_left_right_opponent_policies.json"
        ),
        branch="distinct left/right opponent policy settings",
        check_output=check_side_specific_opponent_policies,
    ),
    Scenario(
        name="side_specific_opponent_policy_multi_step",
        input_path=(
            PROJECT_ROOT / "examples" / "grand_left_right_opponent_policies.json"
        ),
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
        name="overbid_settlement",
        input_path=(
            PROJECT_ROOT
            / "examples"
            / "grand_overbid_declarer_card_points_win.json"
        ),
        branch="supported Suit/Grand overbid settlement",
        check_output=check_overbid_settlement,
    ),
    Scenario(
        name="list_performance_summary",
        input_path=PROJECT_ROOT / "examples" / "grand_list_performance_input.json",
        branch="optional list performance summary",
        check_output=check_list_performance,
    ),
    Scenario(
        name="list_game_contributions_summary",
        input_path=(
            PROJECT_ROOT / "examples" / "grand_list_game_contributions.json"
        ),
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
        input_path=(
            PROJECT_ROOT
            / "examples"
            / "grand_late_game_history_heavy_live.json"
        ),
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
)


def validate_generated_outputs() -> list[str]:
    """
    Generates selected example outputs and validates them against the output schema.
    """
    schema = load_json_file(SCHEMA_PATH)
    validator = Draft202012Validator(schema)
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
        f"Generated {len(SCENARIOS)} outputs match schemas/output.schema.json."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
