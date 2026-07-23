import argparse
import json
import subprocess
import sys
from pathlib import Path

import pytest

import main as main_module
from main import (
    apply_cli_overrides,
    apply_profile_preset_cli_overrides,
    build_analysis_result,
    print_multi_step_result,
    print_policy_comparison_result,
    run_json_historical_game_analysis,
    run_json_position_analysis,
    validate_cli_arguments,
)
from skat_ai.effective_opponent_policy import build_effective_opponent_policy_settings
from skat_ai.player_profile import PlayerProfile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MAIN_PATH = PROJECT_ROOT / "main.py"
VALID_INPUT_PATH = PROJECT_ROOT / "examples" / "grand_second_position.json"
HISTORICAL_INPUT_PATH = (
    PROJECT_ROOT / "examples" / "historical_grand_normal_completion.json"
)
TRAINING_DATASET_INPUT_PATH = (
    PROJECT_ROOT / "examples" / "training_dataset_normal_play.json"
)
OPPONENT_STATISTICS_INPUT_PATH = (
    PROJECT_ROOT / "examples" / "opponent_statistics.json"
)
HISTORICAL_OPPONENT_STATISTICS_INPUT_PATH = (
    PROJECT_ROOT / "examples" / "historical_opponent_statistics.json"
)
ROLLING_EVALUATION_INPUT_PATH = (
    PROJECT_ROOT / "examples" / "historical_opponent_policy_evaluation_dataset.json"
)
UNSUPPORTED_PHASE_INPUT_PATH = (
    PROJECT_ROOT
    / "tests"
    / "fixtures"
    / "generated_output_schema"
    / "grand_unsupported_multi_step_phase.json"
)
IMPOSSIBLE_NULL_INPUT_PATH = (
    PROJECT_ROOT / "examples" / "null_impossible_declaration_settlement.json"
)


def run_cli(*args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(MAIN_PATH), *(str(arg) for arg in args)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def assert_no_success_output(completed_process: subprocess.CompletedProcess[str]) -> None:
    assert "JSON position analysis" not in completed_process.stdout
    assert "Recommended card:" not in completed_process.stdout
    assert "Output file written:" not in completed_process.stdout


def test_cli_help_exits_zero_and_lists_important_options() -> None:
    completed_process = run_cli("--help")

    assert completed_process.returncode == 0
    assert completed_process.stderr == ""
    assert "usage:" in completed_process.stdout
    assert "Examples:" in completed_process.stdout

    for option in [
        "--input",
        "--output",
        "--quiet",
        "--samples",
        "--seed",
        "--expected-value-samples",
        "--multi-step",
        "--compare-policies",
        "--comparison-only",
        "--card-policy",
        "--opponent-strategy",
        "--opponent-policy-preset",
        "--opponent-lead-policy",
        "--opponent-response-policy",
        "--left-opponent-lead-policy",
        "--left-opponent-response-policy",
        "--right-opponent-lead-policy",
        "--right-opponent-response-policy",
        "--use-profile-presets",
        "--opponent-statistics-file",
        "--left-opponent-player-id",
        "--right-opponent-player-id",
        "--historical-decision-snapshots",
        "--historical-game-review",
        "--evaluate-opponent-policy-profiles",
        "--profile-source-partition",
        "--profile-evaluation-partition",
    ]:
        assert option in completed_process.stdout

    assert "Print only policy comparison details" in completed_process.stdout
    assert_no_success_output(completed_process)


def test_cli_default_input_success_exits_zero_and_prints_recommendation() -> None:
    completed_process = run_cli()

    assert completed_process.returncode == 0
    assert completed_process.stderr == ""
    assert "JSON position analysis" in completed_process.stdout
    assert "Input file: input_position.json" in completed_process.stdout
    assert "Legal cards: ['SA', 'S10', 'S9']" in completed_process.stdout
    assert "Recommended card: SA" in completed_process.stdout


def test_cli_success_exits_zero_and_writes_requested_output(tmp_path) -> None:
    output_path = tmp_path / "analysis.json"

    completed_process = run_cli(
        "--input",
        VALID_INPUT_PATH,
        "--samples",
        "1",
        "--seed",
        "42",
        "--output",
        output_path,
    )

    assert completed_process.returncode == 0
    assert "JSON position analysis" in completed_process.stdout
    assert "Recommended card:" in completed_process.stdout
    assert "Output file written:" in completed_process.stdout
    assert completed_process.stderr == ""
    assert output_path.exists()

    with output_path.open("r", encoding="utf-8") as file:
        result = json.load(file)

    assert result["input_file"] == str(VALID_INPUT_PATH)


def test_cli_quiet_output_writes_json_and_suppresses_success_stdout(tmp_path) -> None:
    output_path = tmp_path / "analysis.json"

    completed_process = run_cli(
        "--input",
        VALID_INPUT_PATH,
        "--samples",
        "1",
        "--seed",
        "42",
        "--output",
        output_path,
        "--quiet",
    )

    assert completed_process.returncode == 0
    assert completed_process.stdout == ""
    assert completed_process.stderr == ""
    assert output_path.exists()

    with output_path.open("r", encoding="utf-8") as file:
        result = json.load(file)

    assert result["input_file"] == str(VALID_INPUT_PATH)
    assert "recommendation" in result


def test_cli_quiet_without_output_suppresses_success_stdout() -> None:
    completed_process = run_cli(
        "--input",
        VALID_INPUT_PATH,
        "--samples",
        "1",
        "--seed",
        "42",
        "--quiet",
    )

    assert completed_process.returncode == 0
    assert completed_process.stdout == ""
    assert completed_process.stderr == ""


def test_cli_historical_game_prints_concise_summary() -> None:
    completed_process = run_cli("--input", HISTORICAL_INPUT_PATH)

    assert completed_process.returncode == 0
    assert completed_process.stderr == ""
    assert "Historical game summary" in completed_process.stdout
    assert "Game ID: historical-grand-001" in completed_process.stdout
    assert "Game type: grand" in completed_process.stdout
    assert "Settlement score:" in completed_process.stdout
    assert "Recommended card:" not in completed_process.stdout
    assert "Decision snapshots generated:" not in completed_process.stdout


def test_cli_historical_game_quiet_output_is_separate_branch(tmp_path) -> None:
    output_path = tmp_path / "historical-result.json"

    completed_process = run_cli(
        "--input",
        HISTORICAL_INPUT_PATH,
        "--output",
        output_path,
        "--quiet",
    )

    assert completed_process.returncode == 0
    assert completed_process.stdout == ""
    assert completed_process.stderr == ""
    with output_path.open("r", encoding="utf-8") as output_file:
        result = json.load(output_file)

    assert set(result) == {"input_file", "historical_game_summary"}
    assert result["historical_game_summary"]["status"] == "complete"
    assert "decision_snapshot_summary" not in result["historical_game_summary"]
    assert "position" not in result
    assert "recommendation" not in result


def test_cli_training_dataset_prints_identity_totals_and_partitions() -> None:
    completed_process = run_cli("--input", TRAINING_DATASET_INPUT_PATH)

    assert completed_process.returncode == 0
    assert completed_process.stderr == ""
    assert "Training dataset summary" in completed_process.stdout
    assert "Dataset ID: online-games-2026" in completed_process.stdout
    assert "Dataset version: 1" in completed_process.stdout
    assert "Records: 2" in completed_process.stdout
    assert "Samples: 60" in completed_process.stdout
    assert "Train partition: 1 records, 30 samples" in completed_process.stdout
    assert "Validation partition: 1 records, 30 samples" in completed_process.stdout
    assert "Test partition: 0 records, 0 samples" in completed_process.stdout
    assert "Recommended card:" not in completed_process.stdout


def test_cli_training_dataset_quiet_output_is_separate_branch(tmp_path) -> None:
    output_path = tmp_path / "training-dataset-result.json"
    completed_process = run_cli(
        "--input",
        TRAINING_DATASET_INPUT_PATH,
        "--output",
        output_path,
        "--quiet",
    )

    assert completed_process.returncode == 0
    assert completed_process.stdout == ""
    assert completed_process.stderr == ""
    with output_path.open("r", encoding="utf-8") as output_file:
        result = json.load(output_file)

    assert set(result) == {"input_file", "training_dataset_summary"}
    assert result["training_dataset_summary"]["sample_count"] == 60
    assert "position" not in result
    assert "historical_game_summary" not in result
    assert "recommendation" not in result


def test_cli_rolling_opponent_policy_evaluation_prints_concise_summary() -> None:
    completed_process = run_cli(
        "--input",
        ROLLING_EVALUATION_INPUT_PATH,
        "--evaluate-opponent-policy-profiles",
    )

    assert completed_process.returncode == 0
    assert completed_process.stderr == ""
    assert "Rolling opponent-policy evaluation: 1 target games, 30 decisions." in (
        completed_process.stdout
    )
    assert "Prior player history: 30 of 30 decisions." in completed_process.stdout
    assert "Actionable profile coverage: 0 of 30 decisions." in completed_process.stdout
    assert "No actionable profile predictions were available" in completed_process.stdout
    assert "Training dataset summary" not in completed_process.stdout
    assert "Recommended card:" not in completed_process.stdout


def test_cli_rolling_opponent_policy_evaluation_writes_quiet_separate_branch(
    tmp_path,
) -> None:
    output_path = tmp_path / "rolling-evaluation.json"
    completed_process = run_cli(
        "--input",
        ROLLING_EVALUATION_INPUT_PATH,
        "--evaluate-opponent-policy-profiles",
        "--profile-source-partition",
        "train",
        "--profile-source-partition",
        "train",
        "--profile-evaluation-partition",
        "validation",
        "--output",
        output_path,
        "--quiet",
    )

    assert completed_process.returncode == 0
    assert completed_process.stdout == ""
    assert completed_process.stderr == ""
    with output_path.open("r", encoding="utf-8") as output_file:
        result = json.load(output_file)
    assert set(result) == {
        "input_file",
        "rolling_opponent_policy_evaluation_summary",
    }
    summary = result["rolling_opponent_policy_evaluation_summary"]
    assert summary["selection"]["source_partitions"] == ["train"]
    assert summary["selection"]["evaluation_partitions"] == ["validation"]
    assert "training_dataset_summary" not in result
    assert "recommendation" not in str(result)


@pytest.mark.parametrize(
    ("input_path", "extra_args", "error_match"),
    [
        (
            ROLLING_EVALUATION_INPUT_PATH,
            ("--profile-source-partition", "train"),
            "require --evaluate-opponent-policy-profiles",
        ),
        (
            VALID_INPUT_PATH,
            ("--evaluate-opponent-policy-profiles",),
            "supported only for training_dataset_input",
        ),
        (
            ROLLING_EVALUATION_INPUT_PATH,
            (
                "--evaluate-opponent-policy-profiles",
                "--profile-source-partition",
                "train",
                "--profile-evaluation-partition",
                "train",
            ),
            "must be disjoint",
        ),
        (
            ROLLING_EVALUATION_INPUT_PATH,
            ("--evaluate-opponent-policy-profiles", "--samples", "5"),
            "do not accept position-analysis",
        ),
        (
            ROLLING_EVALUATION_INPUT_PATH,
            ("--evaluate-opponent-policy-profiles", "--aggregate-opponent-statistics"),
            "do not accept position-analysis",
        ),
        (
            ROLLING_EVALUATION_INPUT_PATH,
            ("--evaluate-opponent-policy-profiles", "--opponent-policy-preset", "random"),
            "do not accept position-analysis",
        ),
    ],
)
def test_cli_rejects_invalid_rolling_evaluation_modes(
    input_path: Path,
    extra_args: tuple[str, ...],
    error_match: str,
) -> None:
    completed_process = run_cli("--input", input_path, *extra_args)

    assert completed_process.returncode == 2
    assert error_match in completed_process.stderr
    assert_no_success_output(completed_process)


def test_cli_historical_opponent_statistics_prints_concise_summary() -> None:
    completed_process = run_cli(
        "--input",
        TRAINING_DATASET_INPUT_PATH,
        "--aggregate-opponent-statistics",
        "--opponent-statistics-partition",
        "validation",
        "--opponent-statistics-partition",
        "train",
        "--opponent-statistics-before",
        "2026-07-21T00:00:00Z",
    )

    assert completed_process.returncode == 0
    assert completed_process.stderr == ""
    assert "Historical opponent statistics: 2 games, 3 players." in (
        completed_process.stdout
    )
    assert "Included partitions: train, validation" in completed_process.stdout
    assert "player-b: 2 games, 100.00% declarer" in completed_process.stdout
    assert "Training dataset summary" not in completed_process.stdout
    assert "Recommended card:" not in completed_process.stdout


def test_cli_historical_opponent_statistics_quiet_output_and_export(tmp_path) -> None:
    output_path = tmp_path / "aggregation.json"
    export_path = tmp_path / "opponent-statistics.json"

    completed_process = run_cli(
        "--input",
        TRAINING_DATASET_INPUT_PATH,
        "--aggregate-opponent-statistics",
        "--opponent-statistics-partition",
        "train",
        "--opponent-statistics-partition",
        "validation",
        "--output",
        output_path,
        "--export-opponent-statistics",
        export_path,
        "--quiet",
    )

    assert completed_process.returncode == 0
    assert completed_process.stdout == ""
    assert completed_process.stderr == ""
    with output_path.open("r", encoding="utf-8") as output_file:
        result = json.load(output_file)
    with export_path.open("r", encoding="utf-8") as export_file:
        exported = json.load(export_file)
    assert set(result) == {
        "input_file",
        "historical_opponent_statistics_aggregation_summary",
    }
    assert "training_dataset_summary" not in result
    assert "samples" not in str(result)
    assert set(exported) == {"opponent_statistics_input"}
    assert [
        record["player_id"]
        for record in exported["opponent_statistics_input"]["records"]
    ] == ["player-a", "player-b", "player-c"]


def test_cli_historical_opponent_statistics_prints_export_confirmation(tmp_path) -> None:
    export_path = tmp_path / "opponent-statistics.json"

    completed_process = run_cli(
        "--input",
        TRAINING_DATASET_INPUT_PATH,
        "--aggregate-opponent-statistics",
        "--export-opponent-statistics",
        export_path,
    )

    assert completed_process.returncode == 0
    assert f"Exported opponent statistics to {export_path}." in (
        completed_process.stdout
    )
    assert export_path.exists()


@pytest.mark.parametrize(
    ("input_path", "extra_args", "error_match"),
    [
        (
            VALID_INPUT_PATH,
            ("--aggregate-opponent-statistics",),
            "supported only for training_dataset_input",
        ),
        (
            TRAINING_DATASET_INPUT_PATH,
            ("--opponent-statistics-partition", "train"),
            "require --aggregate-opponent-statistics",
        ),
        (
            TRAINING_DATASET_INPUT_PATH,
            ("--export-opponent-statistics", "export.json"),
            "require --aggregate-opponent-statistics",
        ),
        (
            TRAINING_DATASET_INPUT_PATH,
            ("--aggregate-opponent-statistics", "--samples", "5"),
            "do not accept position-analysis",
        ),
    ],
)
def test_cli_rejects_invalid_historical_aggregation_modes(
    input_path: Path,
    extra_args: tuple[str, ...],
    error_match: str,
) -> None:
    completed_process = run_cli("--input", input_path, *extra_args)

    assert completed_process.returncode == 2
    assert error_match in completed_process.stderr
    assert_no_success_output(completed_process)


def test_cli_rejects_aggregation_output_export_path_collision(tmp_path) -> None:
    shared_path = tmp_path / "shared.json"

    completed_process = run_cli(
        "--input",
        TRAINING_DATASET_INPUT_PATH,
        "--aggregate-opponent-statistics",
        "--output",
        shared_path,
        "--export-opponent-statistics",
        shared_path,
    )

    assert completed_process.returncode == 2
    assert "must use different paths" in completed_process.stderr


def test_cli_opponent_statistics_prints_percentage_summaries() -> None:
    completed_process = run_cli("--input", OPPONENT_STATISTICS_INPUT_PATH)

    assert completed_process.returncode == 0
    assert completed_process.stderr == ""
    assert "Opponent statistics summary" in completed_process.stdout
    assert "Records: 2" in completed_process.stdout
    assert "opponent-123 (Example Player): 600 games" in completed_process.stdout
    assert "declarer 31%" in completed_process.stdout
    assert "defender wins 64%" in completed_process.stdout
    assert "opponent-789 (Second Player): 842 games" in completed_process.stdout
    assert "declarer 42.5%" in completed_process.stdout
    assert "overall high, declarer medium, defender medium" in completed_process.stdout
    assert "classification cautious_defender" in completed_process.stdout
    assert "recommended preset cautious_defender; actionable yes" in completed_process.stdout
    assert "classification aggressive" in completed_process.stdout
    assert "recommended preset aggressive_points; actionable yes" in completed_process.stdout
    assert "Explanation:" in completed_process.stdout
    assert "Recommended card:" not in completed_process.stdout


def test_cli_opponent_statistics_quiet_output_is_separate_branch(tmp_path) -> None:
    output_path = tmp_path / "opponent-statistics-result.json"
    completed_process = run_cli(
        "--input",
        OPPONENT_STATISTICS_INPUT_PATH,
        "--output",
        output_path,
        "--quiet",
    )

    assert completed_process.returncode == 0
    assert completed_process.stdout == ""
    assert completed_process.stderr == ""
    with output_path.open("r", encoding="utf-8") as output_file:
        result = json.load(output_file)

    assert set(result) == {"input_file", "opponent_statistics_summary"}
    assert result["opponent_statistics_summary"]["record_count"] == 2
    assert "position" not in result
    assert "recommendation" not in result
    records = result["opponent_statistics_summary"]["records"]
    assert records[0]["normalized_profile_statistics"]["defender_rate"] == 0.69
    assert records[0]["profile_derivation"]["classification"] == "cautious_defender"
    assert records[1]["profile_derivation"]["classification"] == "aggressive"


def test_cli_historical_decision_snapshots_prints_count() -> None:
    completed_process = run_cli(
        "--input", HISTORICAL_INPUT_PATH, "--historical-decision-snapshots"
    )

    assert completed_process.returncode == 0
    assert completed_process.stderr == ""
    assert "Decision snapshots generated: 30" in completed_process.stdout
    assert "Recommended card:" not in completed_process.stdout


def test_cli_historical_decision_snapshots_quiet_output(tmp_path) -> None:
    output_path = tmp_path / "historical-snapshots.json"
    completed_process = run_cli(
        "--input",
        HISTORICAL_INPUT_PATH,
        "--historical-decision-snapshots",
        "--output",
        output_path,
        "--quiet",
    )

    assert completed_process.returncode == 0
    assert completed_process.stdout == ""
    assert completed_process.stderr == ""
    with output_path.open("r", encoding="utf-8") as output_file:
        result = json.load(output_file)
    snapshot_summary = result["historical_game_summary"][
        "decision_snapshot_summary"
    ]
    assert snapshot_summary["snapshot_count"] == 30
    assert len(snapshot_summary["snapshots"]) == 30


def test_cli_historical_game_review_prints_aggregate_summary() -> None:
    completed_process = run_cli(
        "--input",
        HISTORICAL_INPUT_PATH,
        "--historical-game-review",
        "--samples",
        "1",
        "--seed",
        "42",
    )

    assert completed_process.returncode == 0
    assert completed_process.stderr == ""
    assert "Historical game review" in completed_process.stdout
    assert "Total decisions: 30" in completed_process.stdout
    assert "Reviewed decisions: 30" in completed_process.stdout
    assert "Unavailable decisions: 0" in completed_process.stdout
    for quality in ["Optimal", "Acceptable", "Suboptimal", "Mistake", "Not Available"]:
        assert f"{quality} decisions:" in completed_process.stdout


def test_cli_historical_game_review_quiet_output_and_both_flags(tmp_path) -> None:
    output_path = tmp_path / "historical-review.json"
    completed_process = run_cli(
        "--input",
        HISTORICAL_INPUT_PATH,
        "--historical-game-review",
        "--historical-decision-snapshots",
        "--samples",
        "1",
        "--seed",
        "42",
        "--output",
        output_path,
        "--quiet",
    )

    assert completed_process.returncode == 0
    assert completed_process.stdout == ""
    assert completed_process.stderr == ""
    with output_path.open("r", encoding="utf-8") as output_file:
        result = json.load(output_file)
    summary = result["historical_game_summary"]
    assert summary["decision_snapshot_summary"]["snapshot_count"] == 30
    assert summary["historical_game_review_summary"]["decision_count"] == 30
    assert summary["historical_game_review_summary"]["settings"] == {
        "sample_count": 1,
        "base_random_seed": 42,
        "opponent_policy_mode": "default",
    }


def test_cli_historical_profile_review_prints_setup_summary_and_writes_output(
    tmp_path,
) -> None:
    output_path = tmp_path / "historical-profile-review.json"
    completed_process = run_cli(
        "--input",
        HISTORICAL_INPUT_PATH,
        "--historical-game-review",
        "--opponent-statistics-file",
        HISTORICAL_OPPONENT_STATISTICS_INPUT_PATH,
        "--use-profile-presets",
        "--samples",
        "1",
        "--seed",
        "42",
        "--output",
        output_path,
    )

    assert completed_process.returncode == 0
    assert completed_process.stderr == ""
    assert "Historical profile application: 2 of 3 participants matched." in (
        completed_process.stdout
    )
    assert "Temporal eligibility: all matched captures predate the game." in (
        completed_process.stdout
    )
    assert "Reviewed decisions with an applied external profile: 30 of 30." in (
        completed_process.stdout
    )
    with output_path.open("r", encoding="utf-8") as file:
        result = json.load(file)
    application = result["historical_opponent_profile_application_summary"]
    review = result["historical_game_summary"]["historical_game_review_summary"]
    assert application["temporal_rule"] == ("captured_at_strictly_before_played_at")
    assert application["matched_player_count"] == 2
    assert review["opponent_profile_application_counts"]["application_counts_by_player_id"] == {
        "player-a": 20,
        "player-c": 20,
    }


def test_cli_historical_profile_review_quiet_output_is_silent(tmp_path) -> None:
    output_path = tmp_path / "historical-profile-review.json"
    completed_process = run_cli(
        "--input",
        HISTORICAL_INPUT_PATH,
        "--historical-game-review",
        "--opponent-statistics-file",
        HISTORICAL_OPPONENT_STATISTICS_INPUT_PATH,
        "--use-profile-presets",
        "--samples",
        "1",
        "--seed",
        "42",
        "--output",
        output_path,
        "--quiet",
    )

    assert completed_process.returncode == 0
    assert completed_process.stdout == ""
    assert completed_process.stderr == ""


@pytest.mark.parametrize(
    ("extra_args", "expected_error"),
    [
        ((), "requires --historical-game-review"),
        (("--historical-game-review",), "requires effective --use-profile-presets"),
        (
            (
                "--historical-game-review",
                "--use-profile-presets",
                "--left-opponent-player-id",
                "player-a",
            ),
            "live-only",
        ),
    ],
)
def test_cli_rejects_invalid_historical_profile_mode_options(
    extra_args: tuple[str, ...],
    expected_error: str,
) -> None:
    completed_process = run_cli(
        "--input",
        HISTORICAL_INPUT_PATH,
        "--opponent-statistics-file",
        HISTORICAL_OPPONENT_STATISTICS_INPUT_PATH,
        *extra_args,
    )

    assert completed_process.returncode == 2
    assert expected_error in completed_process.stderr
    assert_no_success_output(completed_process)


def test_cli_rejects_historical_profiles_without_played_at(tmp_path) -> None:
    with HISTORICAL_INPUT_PATH.open("r", encoding="utf-8") as file:
        data = json.load(file)
    data["historical_game_input"].pop("played_at")
    input_path = tmp_path / "historical-without-played-at.json"
    input_path.write_text(json.dumps(data), encoding="utf-8")

    completed_process = run_cli(
        "--input",
        input_path,
        "--historical-game-review",
        "--opponent-statistics-file",
        HISTORICAL_OPPONENT_STATISTICS_INPUT_PATH,
        "--use-profile-presets",
    )

    assert completed_process.returncode == 1
    assert "played_at is required" in completed_process.stderr


def test_historical_review_and_snapshot_flags_generate_snapshots_once(
    monkeypatch,
) -> None:
    call_count = 0
    original_builder = main_module.build_historical_decision_snapshots

    def count_snapshot_builds(historical_summary):
        nonlocal call_count
        call_count += 1
        return original_builder(historical_summary)

    monkeypatch.setattr(
        main_module,
        "build_historical_decision_snapshots",
        count_snapshot_builds,
    )
    monkeypatch.setattr(
        main_module,
        "build_historical_game_review_summary",
        lambda **kwargs: {"decision_count": 30},
    )

    run_json_historical_game_analysis(
        file_path=str(HISTORICAL_INPUT_PATH),
        quiet=True,
        historical_decision_snapshots=True,
        historical_game_review=True,
        sample_count=1,
        base_random_seed=42,
    )

    assert call_count == 1


def test_cli_rejects_historical_game_review_for_position_input() -> None:
    completed_process = run_cli(
        "--input", VALID_INPUT_PATH, "--historical-game-review"
    )

    assert completed_process.returncode == 2
    assert "--historical-game-review requires historical-game input" in (
        completed_process.stderr
    )
    assert_no_success_output(completed_process)


def test_cli_rejects_historical_decision_snapshots_for_position_input() -> None:
    completed_process = run_cli(
        "--input", VALID_INPUT_PATH, "--historical-decision-snapshots"
    )

    assert completed_process.returncode == 2
    assert (
        "--historical-decision-snapshots requires historical-game input"
        in completed_process.stderr
    )
    assert_no_success_output(completed_process)


@pytest.mark.parametrize(
    "override_args",
    [
        ("--samples", "1"),
        ("--seed", "42"),
        ("--card-policy", "highest_point"),
        ("--opponent-policy-preset", "simple_lowest"),
        ("--multi-step", "1"),
        ("--multi-step", "1", "--compare-policies"),
        ("--historical-game-review", "--opponent-strategy", "random"),
        ("--historical-game-review", "--expected-value-samples", "1"),
        ("--historical-game-review", "--use-profile-presets"),
    ],
)
def test_cli_historical_game_rejects_position_specific_overrides(
    override_args: tuple[str, ...],
) -> None:
    completed_process = run_cli(
        "--input", HISTORICAL_INPUT_PATH, *override_args
    )

    assert completed_process.returncode == 2
    assert "Historical-game inputs do not accept" in completed_process.stderr
    assert "Historical game summary" not in completed_process.stdout


@pytest.mark.parametrize(
    "override_args",
    [
        ("--samples", "1"),
        ("--seed", "42"),
        ("--opponent-strategy", "random"),
        ("--historical-decision-snapshots",),
        ("--historical-game-review",),
        ("--multi-step", "1"),
        ("--card-policy", "highest_point"),
        ("--expected-value-samples", "1"),
        ("--strict-context",),
        ("--opponent-policy-preset", "simple_lowest"),
        ("--use-profile-presets",),
        ("--left-opponent-response-policy", "highest_point"),
        ("--right-opponent-lead-policy", "highest_point"),
    ],
)
def test_cli_training_dataset_rejects_analysis_and_review_options(
    override_args: tuple[str, ...],
) -> None:
    completed_process = run_cli(
        "--input", TRAINING_DATASET_INPUT_PATH, *override_args
    )

    assert completed_process.returncode == 2
    assert "Training-dataset inputs do not accept" in completed_process.stderr
    assert "Training dataset summary" not in completed_process.stdout


@pytest.mark.parametrize(
    "override_args",
    [
        ("--samples", "1"),
        ("--seed", "42"),
        ("--opponent-strategy", "random"),
        ("--historical-decision-snapshots",),
        ("--historical-game-review",),
        ("--multi-step", "1"),
        ("--card-policy", "highest_point"),
        ("--expected-value-samples", "1"),
        ("--strict-context",),
        ("--multi-step", "1", "--compare-policies"),
        ("--multi-step", "1", "--compare-policies", "--comparison-only"),
        ("--opponent-policy-preset", "simple_lowest"),
        ("--opponent-lead-policy", "highest_point"),
        ("--opponent-response-policy", "highest_point"),
        ("--use-profile-presets",),
        ("--left-opponent-lead-policy", "highest_point"),
        ("--right-opponent-response-policy", "highest_point"),
    ],
)
def test_cli_opponent_statistics_rejects_all_workflow_options(
    override_args: tuple[str, ...],
) -> None:
    completed_process = run_cli(
        "--input", OPPONENT_STATISTICS_INPUT_PATH, *override_args
    )

    assert completed_process.returncode == 2
    assert "Opponent-statistics inputs do not accept" in completed_process.stderr
    assert "Opponent statistics summary" not in completed_process.stdout


@pytest.mark.parametrize("sample_count", ["0", "-1"])
def test_cli_rejects_invalid_sample_count_before_analysis(
    tmp_path,
    sample_count: str,
) -> None:
    output_path = tmp_path / "result.json"

    completed_process = run_cli(
        "--input",
        VALID_INPUT_PATH,
        "--samples",
        sample_count,
        "--output",
        output_path,
    )

    assert completed_process.returncode == 2
    assert "CLI error: --samples must be a positive integer." in completed_process.stderr
    assert_no_success_output(completed_process)
    assert not output_path.exists()


def test_cli_rejects_invalid_expected_value_sample_count_before_analysis(
    tmp_path,
) -> None:
    output_path = tmp_path / "result.json"

    completed_process = run_cli(
        "--input",
        VALID_INPUT_PATH,
        "--expected-value-samples",
        "0",
        "--output",
        output_path,
    )

    assert completed_process.returncode == 2
    assert (
        "CLI error: --expected-value-samples must be a positive integer."
        in completed_process.stderr
    )
    assert_no_success_output(completed_process)
    assert not output_path.exists()


def test_cli_rejects_sample_count_above_maximum_before_analysis(tmp_path) -> None:
    output_path = tmp_path / "result.json"

    completed_process = run_cli(
        "--input",
        VALID_INPUT_PATH,
        "--samples",
        "100001",
        "--output",
        output_path,
    )

    assert completed_process.returncode == 2
    assert "CLI error: --samples must be at most 100000." in completed_process.stderr
    assert_no_success_output(completed_process)
    assert not output_path.exists()


def test_cli_rejects_expected_value_sample_count_above_maximum_before_analysis(
    tmp_path,
) -> None:
    output_path = tmp_path / "result.json"

    completed_process = run_cli(
        "--input",
        VALID_INPUT_PATH,
        "--expected-value-samples",
        "100001",
        "--output",
        output_path,
    )

    assert completed_process.returncode == 2
    assert (
        "CLI error: --expected-value-samples must be at most 100000."
        in completed_process.stderr
    )
    assert_no_success_output(completed_process)
    assert not output_path.exists()


def test_validate_cli_arguments_accepts_sample_count_maximum_boundary() -> None:
    validate_cli_arguments(
        argparse.Namespace(
            samples=100000,
            expected_value_samples=100000,
            multi_step=None,
            comparison_only=False,
            compare_policies=False,
        )
    )


def test_cli_rejects_invalid_multi_step_count_before_analysis(tmp_path) -> None:
    output_path = tmp_path / "result.json"

    completed_process = run_cli(
        "--input",
        VALID_INPUT_PATH,
        "--multi-step",
        "0",
        "--output",
        output_path,
    )

    assert completed_process.returncode == 2
    assert "CLI error: --multi-step must be a positive integer." in completed_process.stderr
    assert_no_success_output(completed_process)
    assert not output_path.exists()


def test_cli_rejects_comparison_only_without_compare_policies_before_analysis(
    tmp_path,
) -> None:
    output_path = tmp_path / "result.json"

    completed_process = run_cli(
        "--input",
        VALID_INPUT_PATH,
        "--comparison-only",
        "--output",
        output_path,
    )

    assert completed_process.returncode == 2
    assert "CLI error: --comparison-only requires --compare-policies." in (
        completed_process.stderr
    )
    assert_no_success_output(completed_process)
    assert not output_path.exists()


def test_cli_rejects_compare_policies_without_multi_step_before_analysis(
    tmp_path,
) -> None:
    output_path = tmp_path / "result.json"

    completed_process = run_cli(
        "--input",
        VALID_INPUT_PATH,
        "--compare-policies",
        "--output",
        output_path,
    )

    assert completed_process.returncode == 2
    assert "CLI error: --compare-policies requires --multi-step." in completed_process.stderr
    assert_no_success_output(completed_process)
    assert not output_path.exists()


def test_cli_rejects_comparison_only_compare_policies_without_multi_step_before_analysis(
    tmp_path,
) -> None:
    output_path = tmp_path / "result.json"

    completed_process = run_cli(
        "--input",
        VALID_INPUT_PATH,
        "--comparison-only",
        "--compare-policies",
        "--output",
        output_path,
    )

    assert completed_process.returncode == 2
    assert "CLI error: --compare-policies requires --multi-step." in completed_process.stderr
    assert_no_success_output(completed_process)
    assert not output_path.exists()


def test_cli_policy_comparison_prints_analysis_and_comparison_by_default() -> None:
    completed_process = run_cli(
        "--input",
        VALID_INPUT_PATH,
        "--samples",
        "20",
        "--seed",
        "42",
        "--multi-step",
        "1",
        "--expected-value-samples",
        "20",
        "--compare-policies",
    )

    assert completed_process.returncode == 0
    assert completed_process.stderr == ""
    assert "JSON position analysis" in completed_process.stdout
    assert "Recommended card:" in completed_process.stdout
    assert "Policy comparison" in completed_process.stdout


def test_cli_comparison_only_prints_only_policy_comparison() -> None:
    completed_process = run_cli(
        "--input",
        VALID_INPUT_PATH,
        "--samples",
        "20",
        "--seed",
        "42",
        "--multi-step",
        "1",
        "--expected-value-samples",
        "20",
        "--compare-policies",
        "--comparison-only",
    )

    assert completed_process.returncode == 0
    assert completed_process.stderr == ""
    assert "Policy comparison" in completed_process.stdout
    assert "Recommended policy:" in completed_process.stdout
    assert "JSON position analysis" not in completed_process.stdout
    assert "Recommended card:" not in completed_process.stdout
    assert "Multi-step simulation" not in completed_process.stdout
    assert "Multi-step score summary" not in completed_process.stdout


def test_cli_missing_input_exits_one_without_traceback_or_output(tmp_path) -> None:
    output_path = tmp_path / "result.json"

    completed_process = run_cli(
        "--input",
        tmp_path / "missing.json",
        "--output",
        output_path,
    )

    assert completed_process.returncode == 1
    assert "Error: Input file not found:" in completed_process.stderr
    assert "Traceback" not in completed_process.stderr
    assert_no_success_output(completed_process)
    assert not output_path.exists()


def test_cli_quiet_missing_input_still_prints_error_to_stderr(tmp_path) -> None:
    output_path = tmp_path / "result.json"

    completed_process = run_cli(
        "--input",
        tmp_path / "missing.json",
        "--output",
        output_path,
        "--quiet",
    )

    assert completed_process.returncode == 1
    assert completed_process.stdout == ""
    assert "Error: Input file not found:" in completed_process.stderr
    assert "Traceback" not in completed_process.stderr
    assert not output_path.exists()


def test_cli_malformed_json_exits_one_without_traceback_or_output(tmp_path) -> None:
    input_path = tmp_path / "malformed.json"
    output_path = tmp_path / "result.json"
    input_path.write_text("{not json", encoding="utf-8")

    completed_process = run_cli(
        "--input",
        input_path,
        "--output",
        output_path,
    )

    assert completed_process.returncode == 1
    assert "Error:" in completed_process.stderr
    assert "Expecting" in completed_process.stderr
    assert "Traceback" not in completed_process.stderr
    assert_no_success_output(completed_process)
    assert not output_path.exists()


def test_cli_invalid_position_input_exits_one_without_output(tmp_path) -> None:
    input_path = tmp_path / "invalid_position.json"
    output_path = tmp_path / "result.json"
    input_path.write_text(json.dumps({"game_type": "grand"}), encoding="utf-8")

    completed_process = run_cli(
        "--input",
        input_path,
        "--output",
        output_path,
    )

    assert completed_process.returncode == 1
    assert "Error: Missing required input keys:" in completed_process.stderr
    assert "Traceback" not in completed_process.stderr
    assert_no_success_output(completed_process)
    assert not output_path.exists()


def test_cli_invalid_runtime_shape_exits_one_without_output(tmp_path) -> None:
    input_path = tmp_path / "invalid_runtime_shape.json"
    output_path = tmp_path / "result.json"
    data = json.loads(VALID_INPUT_PATH.read_text(encoding="utf-8"))
    data["sample_count"] = 100_001
    input_path.write_text(json.dumps(data), encoding="utf-8")

    completed_process = run_cli(
        "--input",
        input_path,
        "--output",
        output_path,
    )

    assert completed_process.returncode == 1
    assert "Error: sample_count must be at most 100000." in completed_process.stderr
    assert "Traceback" not in completed_process.stderr
    assert_no_success_output(completed_process)
    assert not output_path.exists()


def test_cli_rejects_role_only_completed_trick_conflict(tmp_path) -> None:
    input_path = tmp_path / "wrong_role_only_completed_trick.json"
    output_path = tmp_path / "result.json"
    data = json.loads(VALID_INPUT_PATH.read_text(encoding="utf-8"))
    data["trick_leader"] = "left"
    data["next_player"] = "left"
    data["current_trick"] = []
    data["hand"] = ["C7", "C8", "C9"]
    data["left_hand_size"] = 3
    data["right_hand_size"] = 3
    data["completed_tricks"] = [
        {
            "cards": ["SA", "S7", "S8"],
            "players": ["left", "right", "me"],
            "winner_role": "declarer",
        }
    ]
    input_path.write_text(json.dumps(data), encoding="utf-8")

    completed_process = run_cli(
        "--input",
        input_path,
        "--output",
        output_path,
    )

    assert completed_process.returncode == 1
    assert "completed_tricks[0].winner_role" in completed_process.stderr
    assert "expected defenders, got declarer" in completed_process.stderr
    assert "Traceback" not in completed_process.stderr
    assert_no_success_output(completed_process)
    assert not output_path.exists()


def test_cli_output_write_failure_exits_one_before_success_output(tmp_path) -> None:
    completed_process = run_cli(
        "--input",
        VALID_INPUT_PATH,
        "--samples",
        "1",
        "--seed",
        "42",
        "--output",
        tmp_path,
    )

    assert completed_process.returncode == 1
    assert "Error:" in completed_process.stderr
    assert "Traceback" not in completed_process.stderr
    assert_no_success_output(completed_process)


def test_cli_quiet_output_write_failure_exits_one_without_success_output(
    tmp_path,
) -> None:
    completed_process = run_cli(
        "--input",
        VALID_INPUT_PATH,
        "--samples",
        "1",
        "--seed",
        "42",
        "--output",
        tmp_path,
        "--quiet",
    )

    assert completed_process.returncode == 1
    assert completed_process.stdout == ""
    assert "Error:" in completed_process.stderr
    assert "Traceback" not in completed_process.stderr


@pytest.mark.parametrize(
    ("args", "expected_error"),
    [
        (("--does-not-exist",), "unrecognized arguments"),
        (("--input",), "expected one argument"),
        (("--card-policy", "not_a_policy"), "invalid choice"),
    ],
)
def test_cli_preserves_argparse_exit_two_for_parser_errors(
    args: tuple[str, ...],
    expected_error: str,
) -> None:
    completed_process = run_cli(*args)

    assert completed_process.returncode == 2
    assert completed_process.stdout == ""
    assert "usage:" in completed_process.stderr
    assert expected_error in completed_process.stderr


def test_cli_unsupported_multi_step_phase_remains_success(tmp_path) -> None:
    output_path = tmp_path / "result.json"

    completed_process = run_cli(
        "--input",
        UNSUPPORTED_PHASE_INPUT_PATH,
        "--samples",
        "1",
        "--seed",
        "42",
        "--multi-step",
        "1",
        "--card-policy",
        "highest_point",
        "--output",
        output_path,
    )

    assert completed_process.returncode == 0
    assert "unsupported_turn_phase" in completed_process.stdout
    assert completed_process.stderr == ""
    assert output_path.exists()

    with output_path.open("r", encoding="utf-8") as file:
        result = json.load(file)

    assert result["multi_step_result"]["stop_reason"] == "unsupported_turn_phase"


def test_apply_cli_overrides_keeps_settings_when_no_overrides_are_given() -> None:
    settings = {
        "left_hand_size": 5,
        "right_hand_size": 5,
        "sample_count": 1000,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
    }

    updated_settings = apply_cli_overrides(
        settings=settings,
        sample_count=None,
        random_seed=None,
        opponent_strategy=None,
    )

    assert updated_settings == settings


def test_apply_cli_overrides_updates_sample_count() -> None:
    settings = {
        "left_hand_size": 5,
        "right_hand_size": 5,
        "sample_count": 1000,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
    }

    updated_settings = apply_cli_overrides(
        settings=settings,
        sample_count=500,
        random_seed=None,
        opponent_strategy=None,
    )

    assert updated_settings["sample_count"] == 500
    assert updated_settings["random_seed"] == 42


def test_apply_cli_overrides_updates_random_seed() -> None:
    settings = {
        "left_hand_size": 5,
        "right_hand_size": 5,
        "sample_count": 1000,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
    }

    updated_settings = apply_cli_overrides(
        settings=settings,
        sample_count=None,
        random_seed=123,
        opponent_strategy=None,
    )

    assert updated_settings["sample_count"] == 1000
    assert updated_settings["random_seed"] == 123


def test_apply_cli_overrides_updates_sample_count_and_random_seed() -> None:
    settings = {
        "left_hand_size": 5,
        "right_hand_size": 5,
        "sample_count": 1000,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
    }

    updated_settings = apply_cli_overrides(
        settings=settings,
        sample_count=500,
        random_seed=123,
        opponent_strategy=None,
    )

    assert updated_settings["sample_count"] == 500
    assert updated_settings["random_seed"] == 123


def test_apply_cli_overrides_does_not_mutate_original_settings() -> None:
    settings = {
        "left_hand_size": 5,
        "right_hand_size": 5,
        "sample_count": 1000,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
    }

    updated_settings = apply_cli_overrides(
        settings=settings,
        sample_count=500,
        random_seed=123,
        opponent_strategy=None,
    )

    assert settings["sample_count"] == 1000
    assert settings["random_seed"] == 42
    assert updated_settings["sample_count"] == 500
    assert updated_settings["random_seed"] == 123

def test_apply_cli_overrides_sets_basic_opponent_strategy() -> None:
    settings = {
        "left_hand_size": 5,
        "right_hand_size": 5,
        "sample_count": 1000,
        "random_seed": 42,
        "use_basic_opponent_strategy": False,
    }

    updated_settings = apply_cli_overrides(
        settings=settings,
        sample_count=None,
        random_seed=None,
        opponent_strategy="basic",
    )

    assert updated_settings["use_basic_opponent_strategy"] is True


def test_apply_cli_overrides_sets_random_opponent_strategy() -> None:
    settings = {
        "left_hand_size": 5,
        "right_hand_size": 5,
        "sample_count": 1000,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
    }

    updated_settings = apply_cli_overrides(
        settings=settings,
        sample_count=None,
        random_seed=None,
        opponent_strategy="random",
    )

    assert updated_settings["use_basic_opponent_strategy"] is False


def test_apply_cli_overrides_updates_all_cli_options() -> None:
    settings = {
        "left_hand_size": 5,
        "right_hand_size": 5,
        "sample_count": 1000,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
    }

    updated_settings = apply_cli_overrides(
        settings=settings,
        sample_count=500,
        random_seed=123,
        opponent_strategy="random",
    )

    assert updated_settings["sample_count"] == 500
    assert updated_settings["random_seed"] == 123
    assert updated_settings["use_basic_opponent_strategy"] is False

def test_build_analysis_result_returns_expected_top_level_keys() -> None:
    result = build_analysis_result(
        file_path="examples/grand_leading.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

    assert set(result.keys()) == {
        "input_file",
        "position",
        "settings",
        "analysis_metadata",
        "legal_cards",
        "analysis_report",
        "strategic_summary",
        "score_summary",
        "recommendation",
        "opponent_policy_settings",
        "left_opponent_policy_settings",
        "right_opponent_policy_settings",
        "profile_preset_settings",
        "game_declaration",
        "game_value_summary",
        "game_result_summary",
        "final_settlement_summary",
        "adjusted_game_result_summary",
        "overbid_summary",
        "performance_rating_summary",
        "information_policy_summary",
        "post_game_review_summary",
    }
    assert result["position"]["declarer_player"] == "me"
    assert "list_performance_summary" not in result


def test_build_analysis_result_omits_list_performance_summary_when_input_absent() -> None:
    result = build_analysis_result(
        file_path="examples/grand_leading.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

    assert "list_performance_summary" not in result


def test_build_analysis_result_contains_recommendation() -> None:
    result = build_analysis_result(
        file_path="examples/grand_leading.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

    assert "card" in result["recommendation"]
    assert "reason" in result["recommendation"]
    assert result["recommendation"]["card"] in result["legal_cards"]


def test_build_analysis_result_applies_cli_overrides() -> None:
    result = build_analysis_result(
        file_path="examples/grand_leading.json",
        sample_count_override=20,
        random_seed_override=123,
        opponent_strategy_override="random",
    )

    assert result["settings"]["sample_count"] == 20
    assert result["settings"]["random_seed"] == 123
    assert result["settings"]["use_basic_opponent_strategy"] is False

def test_build_analysis_result_includes_overbid_summary() -> None:
    result = build_analysis_result(
        file_path="examples/grand_second_position.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

    assert result["overbid_summary"] == {
        "bid_value": None,
        "game_value": 120,
        "is_overbid": None,
        "margin": None,
        "status": "unknown_bid_value",
        "required_game_value": None,
    }


def test_build_analysis_result_serializes_impossible_null_settlement() -> None:
    result = build_analysis_result(file_path=str(IMPOSSIBLE_NULL_INPUT_PATH))

    assert result["position"]["game_type"] == "null"
    assert result["game_declaration"]["ouvert"] is True
    assert result["game_declaration"]["matadors"] is None
    assert result["game_value_summary"]["game_value"] == 59
    assert result["overbid_summary"]["required_game_value"] == 60
    assert result["overbid_summary"]["impossible_null_settlement"][
        "hand_game"
    ] is True
    assert result["final_settlement_summary"]["winner"] == "defenders"
    assert result["final_settlement_summary"]["declarer_won_by_card_points"] is None
    assert result["final_settlement_summary"]["settlement_score"] == -120


def test_build_analysis_result_keeps_impossible_null_settlement_incomplete(
    tmp_path,
) -> None:
    data = json.loads(IMPOSSIBLE_NULL_INPUT_PATH.read_text(encoding="utf-8"))
    data.pop("impossible_null_settlement")
    input_path = tmp_path / "impossible_null_without_replacement.json"
    input_path.write_text(json.dumps(data), encoding="utf-8")

    result = build_analysis_result(file_path=str(input_path))

    assert result["adjusted_game_result_summary"]["winner"] == "defenders"
    assert result["overbid_summary"]["impossible_null_settlement"] is None
    assert result["final_settlement_summary"]["is_complete"] is False
    assert result["final_settlement_summary"]["missing_inputs"] == [
        "impossible_null_settlement"
    ]
    assert result["final_settlement_summary"]["settlement_score"] is None

def test_build_analysis_result_includes_performance_rating_summary() -> None:
    result = build_analysis_result(
        file_path="examples/grand_second_position.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

    assert result["performance_rating_summary"] == {
        "is_implemented": False,
        "implemented_scope": None,
        "unsupported_scope": "performance_rating_not_implemented",
        "rating_system": None,
        "basis": "individual_game_settlement",
        "game_outcome": "incomplete",
        "settlement_score": None,
        "rating_score": None,
        "declarer_rating_score": None,
        "declarer_rating_points": None,
        "defender_rating_points": None,
        "unsupported_reason": "performance_rating_not_implemented",
        "is_partially_implemented": False,
        "table_player_count": 3,
        "counterparty_rating_points": None,
        "notes": [
            "Performance rating is separate from individual game settlement.",
            "rating_score currently represents the declarer's rating score.",
            "List, series, and tournament rating are not fully implemented yet.",
            "final_settlement_summary remains the source for single-game settlement.",
        ],
    }


def build_list_performance_cli_input() -> dict[str, object]:
    return {
        "game_type": "grand",
        "player_role": "declarer",
        "player_position": "middlehand",
        "trick_leader": "right",
        "hand": ["SA", "S10", "S9", "H10", "D7"],
        "current_trick": ["S7"],
        "played_cards": [],
        "completed_tricks": [],
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "me",
        "skat": [],
        "left_hand_size": 5,
        "right_hand_size": 5,
        "sample_count": 1000,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
        "performance_rating_system": "isko_list",
    }


def test_build_analysis_result_includes_list_performance_summary(tmp_path) -> None:
    input_path = tmp_path / "list_performance_input.json"
    data = build_list_performance_cli_input()
    data["list_performance_input"] = {
        "player_game_points": 120,
        "own_games_won": 3,
        "own_games_lost": 1,
        "other_players_lost_games": 2,
    }
    input_path.write_text(json.dumps(data), encoding="utf-8")

    result = build_analysis_result(
        file_path=str(input_path),
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

    assert result["list_performance_summary"] == {
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
    }
    assert result["performance_rating_summary"]["basis"] == (
        "individual_game_settlement"
    )
    assert result["performance_rating_summary"]["game_outcome"] == "incomplete"
    assert result["performance_rating_summary"]["settlement_score"] is None
    assert result["performance_rating_summary"]["rating_score"] is None
    assert "list_standings_summary" not in result


def test_build_analysis_result_includes_contribution_list_performance_summary(
    tmp_path,
) -> None:
    input_path = tmp_path / "list_game_contributions.json"
    data = build_list_performance_cli_input()
    data["list_game_contributions"] = [
        {
            "player_role": "declarer",
            "game_outcome": "declarer_win",
            "settlement_score": 96,
        },
        {
            "player_role": "defender",
            "game_outcome": "declarer_loss",
            "settlement_score": -144,
        },
    ]
    input_path.write_text(json.dumps(data), encoding="utf-8")

    result = build_analysis_result(
        file_path=str(input_path),
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

    assert result["list_performance_summary"] == {
        "rating_system": "isko_list",
        "basis": "normalized_game_contributions",
        "table_size": 3,
        "player_game_points": 96,
        "own_games_won": 1,
        "own_games_lost": 0,
        "other_players_lost_games": 1,
        "own_game_bonus_points": 50,
        "opponent_loss_bonus_points": 40,
        "total_performance_points": 186,
    }
    assert result["performance_rating_summary"]["basis"] == (
        "individual_game_settlement"
    )
    assert result["performance_rating_summary"]["game_outcome"] == "incomplete"
    assert result["performance_rating_summary"]["settlement_score"] is None
    assert result["performance_rating_summary"]["rating_score"] is None
    assert "list_standings_summary" not in result


def test_build_analysis_result_includes_empty_contribution_list_performance_summary(
    tmp_path,
) -> None:
    input_path = tmp_path / "empty_list_game_contributions.json"
    data = build_list_performance_cli_input()
    data["list_game_contributions"] = []
    input_path.write_text(json.dumps(data), encoding="utf-8")

    result = build_analysis_result(
        file_path=str(input_path),
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

    assert result["list_performance_summary"] == {
        "rating_system": "isko_list",
        "basis": "normalized_game_contributions",
        "table_size": 3,
        "player_game_points": 0,
        "own_games_won": 0,
        "own_games_lost": 0,
        "other_players_lost_games": 0,
        "own_game_bonus_points": 0,
        "opponent_loss_bonus_points": 0,
        "total_performance_points": 0,
    }


def test_build_analysis_result_accepts_contribution_metadata(
    tmp_path,
) -> None:
    input_path = tmp_path / "list_game_contributions_with_metadata.json"
    data = build_list_performance_cli_input()
    data["list_game_contributions"] = [
        {
            "player_role": "declarer",
            "game_outcome": "declarer_win",
            "settlement_score": 96,
            "rated_player_id": "player-1",
            "game_id": "game-1",
        },
        {
            "player_role": "defender",
            "game_outcome": "declarer_loss",
            "settlement_score": -144,
            "rated_player_id": "player-1",
            "game_id": "game-2",
        },
    ]
    input_path.write_text(json.dumps(data), encoding="utf-8")

    result = build_analysis_result(
        file_path=str(input_path),
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

    assert result["list_performance_summary"] == {
        "rating_system": "isko_list",
        "basis": "normalized_game_contributions",
        "table_size": 3,
        "player_game_points": 96,
        "own_games_won": 1,
        "own_games_lost": 0,
        "other_players_lost_games": 1,
        "own_game_bonus_points": 50,
        "opponent_loss_bonus_points": 40,
        "total_performance_points": 186,
    }


def test_build_analysis_result_includes_analysis_result_list_performance_summary(
    tmp_path,
) -> None:
    input_path = tmp_path / "list_analysis_results.json"
    data = build_list_performance_cli_input()
    data["list_analysis_results"] = [
        {
            "position": {
                "player_role": "declarer",
            },
            "final_settlement_summary": {
                "is_complete": True,
                "is_loss": False,
                "settlement_score": 96,
            },
        },
        {
            "position": {
                "player_role": "defender",
            },
            "final_settlement_summary": {
                "is_complete": True,
                "is_loss": True,
                "settlement_score": -144,
            },
        },
    ]
    input_path.write_text(json.dumps(data), encoding="utf-8")

    result = build_analysis_result(
        file_path=str(input_path),
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

    assert result["list_performance_summary"] == {
        "rating_system": "isko_list",
        "basis": "local_analysis_results",
        "table_size": 3,
        "player_game_points": 96,
        "own_games_won": 1,
        "own_games_lost": 0,
        "other_players_lost_games": 1,
        "own_game_bonus_points": 50,
        "opponent_loss_bonus_points": 40,
        "total_performance_points": 186,
    }
    assert result["performance_rating_summary"]["basis"] == (
        "individual_game_settlement"
    )
    assert result["performance_rating_summary"]["game_outcome"] == "incomplete"
    assert "list_standings_summary" not in result


def test_build_analysis_result_includes_list_standings_summary(
    tmp_path,
) -> None:
    input_path = tmp_path / "list_standings_input.json"
    data = build_list_performance_cli_input()
    data["list_standings_input"] = {
        "players": [
            {"player_id": "alice", "player_label": "Alice"},
            {"player_id": "bob", "player_label": "Bob"},
            {"player_id": "carol", "player_label": "Carol"},
        ],
        "games": [
            {
                "game_id": "game-1",
                "declarer_player_id": "alice",
                "game_outcome": "declarer_win",
                "settlement_score": 96,
            },
            {
                "game_id": "game-2",
                "declarer_player_id": "bob",
                "game_outcome": "declarer_loss",
                "settlement_score": -72,
            },
        ],
    }
    input_path.write_text(json.dumps(data), encoding="utf-8")

    result = build_analysis_result(
        file_path=str(input_path),
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

    assert "list_performance_summary" not in result
    assert result["list_standings_summary"]["basis"] == (
        "fixed_three_player_game_results"
    )
    assert result["list_standings_summary"]["ranking_status"] == "final"
    assert result["list_standings_summary"]["lot_required_player_ids"] == []
    assert result["list_standings_summary"]["applied_lot_order"] is None
    assert result["list_standings_summary"]["standings"][0]["player_id"] == "alice"
    assert result["list_standings_summary"]["standings"][0][
        "total_performance_points"
    ] == 186


def test_build_analysis_result_accepts_analysis_result_metadata(
    tmp_path,
) -> None:
    input_path = tmp_path / "list_analysis_results_with_metadata.json"
    data = build_list_performance_cli_input()
    data["list_analysis_results"] = [
        {
            "rated_player_id": "player-1",
            "game_id": "game-1",
            "position": {
                "player_role": "declarer",
            },
            "final_settlement_summary": {
                "is_complete": True,
                "is_loss": False,
                "settlement_score": 96,
            },
        },
        {
            "rated_player_id": "player-1",
            "game_id": "game-2",
            "position": {
                "player_role": "defender",
            },
            "final_settlement_summary": {
                "is_complete": True,
                "is_loss": True,
                "settlement_score": -144,
            },
        },
    ]
    input_path.write_text(json.dumps(data), encoding="utf-8")

    result = build_analysis_result(
        file_path=str(input_path),
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

    assert result["list_performance_summary"] == {
        "rating_system": "isko_list",
        "basis": "local_analysis_results",
        "table_size": 3,
        "player_game_points": 96,
        "own_games_won": 1,
        "own_games_lost": 0,
        "other_players_lost_games": 1,
        "own_game_bonus_points": 50,
        "opponent_loss_bonus_points": 40,
        "total_performance_points": 186,
    }


def test_build_analysis_result_rejects_conflicting_analysis_result_player_metadata(
    tmp_path,
) -> None:
    input_path = tmp_path / "conflicting_list_analysis_results.json"
    data = build_list_performance_cli_input()
    data["list_analysis_results"] = [
        {
            "rated_player_id": "player-1",
            "position": {
                "player_role": "declarer",
            },
            "final_settlement_summary": {
                "is_complete": True,
                "is_loss": False,
                "settlement_score": 96,
            },
        },
        {
            "rated_player_id": "player-2",
            "position": {
                "player_role": "declarer",
            },
            "final_settlement_summary": {
                "is_complete": True,
                "is_loss": False,
                "settlement_score": 96,
            },
        },
    ]
    input_path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="rated_player_id values conflict"):
        build_analysis_result(
            file_path=str(input_path),
            sample_count_override=20,
            random_seed_override=42,
            opponent_strategy_override="basic",
        )


def test_build_analysis_result_rejects_duplicate_contribution_game_metadata(
    tmp_path,
) -> None:
    input_path = tmp_path / "duplicate_list_game_contributions.json"
    data = build_list_performance_cli_input()
    data["list_game_contributions"] = [
        {
            "player_role": "declarer",
            "game_outcome": "declarer_win",
            "settlement_score": 96,
            "game_id": "game-1",
        },
        {
            "player_role": "defender",
            "game_outcome": "declarer_loss",
            "settlement_score": -144,
            "game_id": "game-1",
        },
    ]
    input_path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="Duplicate list_game_contributions.game_id"):
        build_analysis_result(
            file_path=str(input_path),
            sample_count_override=20,
            random_seed_override=42,
            opponent_strategy_override="basic",
        )


def test_build_analysis_result_includes_empty_analysis_result_list_summary(
    tmp_path,
) -> None:
    input_path = tmp_path / "empty_list_analysis_results.json"
    data = build_list_performance_cli_input()
    data["list_analysis_results"] = []
    input_path.write_text(json.dumps(data), encoding="utf-8")

    result = build_analysis_result(
        file_path=str(input_path),
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

    assert result["list_performance_summary"] == {
        "rating_system": "isko_list",
        "basis": "local_analysis_results",
        "table_size": 3,
        "player_game_points": 0,
        "own_games_won": 0,
        "own_games_lost": 0,
        "other_players_lost_games": 0,
        "own_game_bonus_points": 0,
        "opponent_loss_bonus_points": 0,
        "total_performance_points": 0,
    }


def test_build_analysis_result_includes_only_skipped_analysis_result_list_summary(
    tmp_path,
) -> None:
    input_path = tmp_path / "skipped_list_analysis_results.json"
    data = build_list_performance_cli_input()
    data["list_analysis_results"] = [
        {
            "position": {
                "player_role": "declarer",
            },
            "final_settlement_summary": {
                "is_complete": False,
            },
        },
        {
            "position": {
                "player_role": "unknown",
            },
            "final_settlement_summary": {
                "is_complete": True,
                "is_loss": False,
                "settlement_score": 96,
            },
        },
    ]
    input_path.write_text(json.dumps(data), encoding="utf-8")

    result = build_analysis_result(
        file_path=str(input_path),
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

    assert result["list_performance_summary"] == {
        "rating_system": "isko_list",
        "basis": "local_analysis_results",
        "table_size": 3,
        "player_game_points": 0,
        "own_games_won": 0,
        "own_games_lost": 0,
        "other_players_lost_games": 0,
        "own_game_bonus_points": 0,
        "opponent_loss_bonus_points": 0,
        "total_performance_points": 0,
    }


def test_run_json_position_analysis_supports_multi_step() -> None:
    run_json_position_analysis(
        file_path="examples/grand_second_position.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
        output_path=None,
        multi_step_count=1,
        card_selection_policy="first_legal",
        expected_value_sample_count=20,
    )


def test_run_json_position_analysis_rejects_zero_multi_step_count() -> None:
    try:
        run_json_position_analysis(
            file_path="examples/grand_second_position.json",
            sample_count_override=20,
            random_seed_override=42,
            opponent_strategy_override="basic",
            output_path=None,
            multi_step_count=0,
            card_selection_policy="first_legal",
            expected_value_sample_count=20,
        )
    except ValueError as error:
        assert "multi_step_count" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_run_json_position_analysis_supports_highest_expected_value_multi_step() -> None:
    run_json_position_analysis(
        file_path="examples/grand_second_position.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
        output_path=None,
        multi_step_count=1,
        card_selection_policy="highest_expected_value",
        expected_value_sample_count=20,
    )


def test_print_multi_step_result_outputs_summary(capsys) -> None:
    from skat_ai.game_state import GameState

    result = {
        "card_selection_policy": "first_legal",
        "requested_step_count": 1,
        "steps_simulated": 1,
        "stop_reason": "Requested step count reached.",
        "context_summary": {
            "simulated_opponent_card_count": 2,
            "unique_simulated_opponent_card_count": 2,
            "duplicate_simulated_opponent_cards": [],
            "event_count": 1,
        },
        "steps": [
            {
                "step_index": 0,
                "opponent_lead_result": None,
                "candidate_card": "SA",
                "detailed_result": {
                    "trick": ["S7", "SA", "S8"],
                    "did_win": True,
                    "trick_points": 11,
                    "completed_trick": {
                        "cards": ["S7", "SA", "S8"],
                        "winner_role": "declarer",
                    },
                },
            }
        ],
        "final_state": GameState(
            game_type="grand",
            player_role="declarer",
            hand=["S10", "S9"],
            current_trick=[],
            completed_tricks=[
                {
                    "cards": ["S7", "SA", "S8"],
                    "winner_role": "declarer",
                }
            ],
            declarer_points=11,
            defender_points=0,
            next_player="me",
        ),
        "summary": {
            "requested_step_count": 1,
            "steps_simulated": 1,
            "stop_reason": "Requested step count reached.",
            "card_selection_policy": "first_legal",
            "strict_context": False,
            "score_summary": {
                "initial_declarer_points": 0,
                "initial_defender_points": 0,
                "final_declarer_points": 11,
                "final_defender_points": 0,
                "declarer_points_gained": 11,
                "defender_points_gained": 0,
                "final_point_swing": 11,
            },
            "context_summary": {
                "simulated_opponent_card_count": 2,
                "unique_simulated_opponent_card_count": 2,
                "duplicate_simulated_opponent_cards": [],
                "event_count": 1,
            },
        },
    }

    print_multi_step_result(result)

    captured = capsys.readouterr()

    assert "Multi-step simulation" in captured.out
    assert "Card selection policy: first_legal" in captured.out
    assert "Requested steps: 1" in captured.out
    assert "Steps simulated: 1" in captured.out
    assert "Stop reason: Requested step count reached." in captured.out
    assert "Context summary:" in captured.out
    assert "Context warning: none" in captured.out
    assert "Candidate card: SA" in captured.out
    assert "Final state" in captured.out
    assert "Multi-step score summary" in captured.out
    assert "Final point swing: 11" in captured.out


def test_print_multi_step_result_outputs_opponent_lead(capsys) -> None:
    from skat_ai.game_state import GameState

    result = {
        "card_selection_policy": "first_legal",
        "requested_step_count": 1,
        "steps_simulated": 1,
        "stop_reason": "Requested step count reached.",
        "steps": [
            {
                "step_index": 0,
                "opponent_lead_result": {
                    "leader": "right",
                    "lead_card": "D7",
                },
                "candidate_card": "DA",
                "detailed_result": {
                    "trick": ["D7", "DA", "D8"],
                    "did_win": True,
                    "trick_points": 11,
                    "completed_trick": {
                        "cards": ["D7", "DA", "D8"],
                        "players": ["right", "me", "left"],
                        "winner_role": "declarer",
                        "winner_player": "me",
                    },
                },
            }
        ],
        "final_state": GameState(
            game_type="grand",
            player_role="declarer",
            hand=["S10", "S9"],
            current_trick=[],
            completed_tricks=[
                {
                    "cards": ["D7", "DA", "D8"],
                    "players": ["right", "me", "left"],
                    "winner_role": "declarer",
                    "winner_player": "me",
                }
            ],
            declarer_points=11,
            defender_points=0,
            next_player="me",
        ),
        "summary": {
            "requested_step_count": 1,
            "steps_simulated": 1,
            "stop_reason": "Requested step count reached.",
            "card_selection_policy": "first_legal",
            "strict_context": False,
            "score_summary": {
                "initial_declarer_points": 0,
                "initial_defender_points": 0,
                "final_declarer_points": 11,
                "final_defender_points": 0,
                "declarer_points_gained": 11,
                "defender_points_gained": 0,
                "final_point_swing": 11,
            },
            "context_summary": {
                "simulated_opponent_card_count": 2,
                "unique_simulated_opponent_card_count": 2,
                "duplicate_simulated_opponent_cards": [],
                "event_count": 1,
            },
        },
    }

    print_multi_step_result(result)

    captured = capsys.readouterr()

    assert "Opponent lead player: right" in captured.out
    assert "Opponent lead card: D7" in captured.out
    assert "Candidate card: DA" in captured.out


def test_print_multi_step_result_outputs_opponent_response(capsys) -> None:
    from skat_ai.game_state import GameState

    result = {
        "card_selection_policy": "first_legal",
        "requested_step_count": 1,
        "steps_simulated": 1,
        "stop_reason": "Requested step count reached.",
        "steps": [
            {
                "step_index": 0,
                "opponent_lead_result": {
                    "leader": "left",
                    "lead_card": "D7",
                    "responder": "right",
                    "response_card": "D9",
                },
                "candidate_card": "DA",
                "detailed_result": {
                    "trick": ["D7", "D9", "DA"],
                    "did_win": True,
                    "trick_points": 11,
                    "completed_trick": {
                        "cards": ["D7", "D9", "DA"],
                        "players": ["left", "right", "me"],
                        "winner_role": "declarer",
                        "winner_player": "me",
                    },
                },
            }
        ],
        "final_state": GameState(
            game_type="grand",
            player_role="declarer",
            hand=["S10", "S9"],
            current_trick=[],
            completed_tricks=[
                {
                    "cards": ["D7", "D9", "DA"],
                    "players": ["left", "right", "me"],
                    "winner_role": "declarer",
                    "winner_player": "me",
                }
            ],
            declarer_points=11,
            defender_points=0,
            next_player="me",
        ),
        "summary": {
            "requested_step_count": 1,
            "steps_simulated": 1,
            "stop_reason": "Requested step count reached.",
            "card_selection_policy": "first_legal",
            "strict_context": False,
            "score_summary": {
                "initial_declarer_points": 0,
                "initial_defender_points": 0,
                "final_declarer_points": 11,
                "final_defender_points": 0,
                "declarer_points_gained": 11,
                "defender_points_gained": 0,
                "final_point_swing": 11,
            },
            "context_summary": {
                "simulated_opponent_card_count": 2,
                "unique_simulated_opponent_card_count": 2,
                "duplicate_simulated_opponent_cards": [],
                "event_count": 1,
            },
        },
    }

    print_multi_step_result(result)

    captured = capsys.readouterr()

    assert "Opponent lead player: left" in captured.out
    assert "Opponent lead card: D7" in captured.out
    assert "Opponent response player: right" in captured.out
    assert "Opponent response card: D9" in captured.out
    assert "Candidate card: DA" in captured.out

def test_print_multi_step_result_outputs_duplicate_context_warning(capsys) -> None:
    from skat_ai.game_state import GameState

    result = {
        "card_selection_policy": "first_legal",
        "requested_step_count": 1,
        "steps_simulated": 1,
        "stop_reason": "Requested step count reached.",
        "context_summary": {
            "simulated_opponent_card_count": 3,
            "unique_simulated_opponent_card_count": 2,
            "duplicate_simulated_opponent_cards": ["S7"],
            "event_count": 1,
        },
        "steps": [
            {
                "step_index": 0,
                "opponent_lead_result": None,
                "candidate_card": "SA",
                "detailed_result": {
                    "trick": ["S7", "SA", "S8"],
                    "did_win": True,
                    "trick_points": 11,
                    "completed_trick": {
                        "cards": ["S7", "SA", "S8"],
                        "winner_role": "declarer",
                    },
                },
            }
        ],
        "final_state": GameState(
            game_type="grand",
            player_role="declarer",
            hand=["S10", "S9"],
            current_trick=[],
            completed_tricks=[
                {
                    "cards": ["S7", "SA", "S8"],
                    "winner_role": "declarer",
                }
            ],
            declarer_points=11,
            defender_points=0,
            next_player="me",
        ),
        "summary": {
            "requested_step_count": 1,
            "steps_simulated": 1,
            "stop_reason": "Requested step count reached.",
            "card_selection_policy": "first_legal",
            "strict_context": False,
            "score_summary": {
                "initial_declarer_points": 0,
                "initial_defender_points": 0,
                "final_declarer_points": 11,
                "final_defender_points": 0,
                "declarer_points_gained": 11,
                "defender_points_gained": 0,
                "final_point_swing": 11,
            },
            "context_summary": {
                "simulated_opponent_card_count": 2,
                "unique_simulated_opponent_card_count": 2,
                "duplicate_simulated_opponent_cards": [],
                "event_count": 1,
            },
        },
    }

    print_multi_step_result(result)

    captured = capsys.readouterr()

    assert "Context summary:" in captured.out
    assert "Context warning: duplicate simulated opponent cards detected:" in captured.out
    assert "['S7']" in captured.out

def test_run_json_position_analysis_supports_strict_context() -> None:
    run_json_position_analysis(
        file_path="examples/grand_second_position.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
        output_path=None,
        multi_step_count=1,
        card_selection_policy="highest_expected_value",
        expected_value_sample_count=20,
        strict_context=True,
    )

def test_print_policy_comparison_result_outputs_summary(capsys) -> None:
    result = {
        "requested_step_count": 2,
        "random_seed": 42,
        "expected_value_sample_count": 20,
        "use_basic_opponent_strategy": True,
        "strict_context": False,
        "policies": ["lowest_point", "highest_point"],
        "policy_results": [
            {
                "policy": "lowest_point",
                "requested_step_count": 2,
                "steps_simulated": 1,
                "stop_reason": "Requested step count reached.",
                "strict_context": False,
                "declarer_points_gained": 4,
                "defender_points_gained": 10,
                "final_point_swing": -6,
                "local_point_swing": -6,
                "context_summary": {},
            },
            {
                "policy": "highest_point",
                "requested_step_count": 2,
                "steps_simulated": 1,
                "stop_reason": "Requested step count reached.",
                "strict_context": False,
                "declarer_points_gained": 14,
                "defender_points_gained": 2,
                "final_point_swing": 12,
                "local_point_swing": 12,
                "context_summary": {},
            },
        ],
        "recommended_policy": {
            "policy": "highest_point",
            "reason": "Best final point swing after tie-breakers.",
            "final_point_swing": 12,
            "local_point_swing": 12,
            "declarer_points_gained": 14,
            "defender_points_gained": 2,
            "steps_simulated": 1,
            "stop_reason": "Requested step count reached.",
        },
    }

    print_policy_comparison_result(result)

    captured = capsys.readouterr()

    assert "Policy comparison" in captured.out
    assert "lowest_point" in captured.out
    assert "highest_point" in captured.out
    assert "Recommended policy: highest_point" in captured.out
    assert "Recommendation reason: Best final point swing after tie-breakers." in captured.out
    assert "Recommended final point swing: 12" in captured.out
    assert "Recommended local point swing: 12" in captured.out

def test_run_json_position_analysis_supports_policy_comparison() -> None:
    run_json_position_analysis(
        file_path="examples/grand_second_position.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
        output_path=None,
        multi_step_count=1,
        card_selection_policy="highest_expected_value",
        expected_value_sample_count=20,
        strict_context=False,
        compare_policies=True,
    )


def test_run_json_position_analysis_writes_policy_comparison_to_output(tmp_path) -> None:
    import json

    output_path = tmp_path / "policy_comparison.json"

    run_json_position_analysis(
        file_path="examples/grand_second_position.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
        output_path=str(output_path),
        multi_step_count=1,
        card_selection_policy="highest_expected_value",
        expected_value_sample_count=20,
        strict_context=False,
        compare_policies=True,
    )

    with output_path.open("r", encoding="utf-8") as file:
        result = json.load(file)

    assert "policy_comparison_result" in result
    assert "policy_results" in result["policy_comparison_result"]
    assert "recommended_policy" in result["policy_comparison_result"]
    assert len(result["policy_comparison_result"]["policy_results"]) >= 1


def test_run_json_position_analysis_supports_comparison_only(capsys) -> None:
    run_json_position_analysis(
        file_path="examples/grand_second_position.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
        output_path=None,
        multi_step_count=1,
        card_selection_policy="highest_expected_value",
        expected_value_sample_count=20,
        strict_context=False,
        compare_policies=True,
        comparison_only=True,
    )

    captured = capsys.readouterr()

    assert "Policy comparison" in captured.out
    assert "Recommended policy:" in captured.out
    assert "JSON position analysis" not in captured.out
    assert "Recommended card:" not in captured.out
    assert "Multi-step simulation" not in captured.out
    assert "Multi-step score summary" not in captured.out

def test_run_json_position_analysis_rejects_comparison_only_without_compare_policies() -> None:
    try:
        run_json_position_analysis(
            file_path="examples/grand_second_position.json",
            sample_count_override=20,
            random_seed_override=42,
            opponent_strategy_override="basic",
            output_path=None,
            multi_step_count=1,
            card_selection_policy="highest_expected_value",
            expected_value_sample_count=20,
            strict_context=False,
            compare_policies=False,
            comparison_only=True,
        )
    except ValueError as error:
        assert "comparison_only requires compare_policies" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")

def test_build_analysis_result_includes_default_analysis_metadata() -> None:
    result = build_analysis_result(
        file_path="examples/grand_second_position.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

    assert result["analysis_metadata"]["strategic_metadata"] == {
        "analysis_mode": "live_decision",
        "skat_visibility": "unknown",
        "game_end_reason": "not_ended",
    }

def test_build_analysis_result_includes_information_policy_summary() -> None:
    result = build_analysis_result(
        file_path="examples/grand_second_position.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

    assert result["information_policy_summary"] == {
        "analysis_mode": "live_decision",
        "skat_visibility": "unknown",
        "game_end_reason": "not_ended",
        "live_information_enforced": True,
        "known_post_game_skat_allowed": False,
        "known_skat_cards_allowed": False,
        "ended_game_allowed": False,
        "unverifiable_completed_trick_winner_metadata_allowed": False,
    }
    

def test_build_analysis_result_reads_analysis_metadata() -> None:
    result = build_analysis_result(
        file_path="examples/grand_second_position_with_metadata.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

    assert result["analysis_metadata"]["strategic_metadata"] == {
        "analysis_mode": "post_game_review",
        "skat_visibility": "known_post_game",
        "game_end_reason": "not_ended",
    }
    assert result["analysis_metadata"]["left_player_profile"]["games_played"] == 1240
    assert result["analysis_metadata"]["right_player_profile"]["games_played"] == 520

def test_build_analysis_result_includes_opponent_policy_settings() -> None:
    result = build_analysis_result(
        file_path="examples/grand_second_position.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

    assert result["opponent_policy_settings"] == {
        "opponent_lead_policy": "lowest_point",
        "opponent_response_policy": "lowest_point",
    }


def test_apply_profile_preset_cli_overrides_defaults_to_unchanged() -> None:
    settings = {
        "use_profile_presets": False,
    }

    updated_settings = apply_profile_preset_cli_overrides(
        profile_preset_settings=settings,
        use_profile_presets=False,
    )

    assert updated_settings == {
        "use_profile_presets": False,
    }
    assert updated_settings is not settings


def test_apply_profile_preset_cli_overrides_enables_profile_presets() -> None:
    settings = {
        "use_profile_presets": False,
    }

    updated_settings = apply_profile_preset_cli_overrides(
        profile_preset_settings=settings,
        use_profile_presets=True,
    )

    assert updated_settings == {
        "use_profile_presets": True,
    }


def test_build_analysis_result_includes_profile_preset_settings() -> None:
    result = build_analysis_result(
        file_path="examples/grand_second_position.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

    assert result["profile_preset_settings"] == {
        "use_profile_presets": False,
    }

def test_build_analysis_result_applies_profile_presets_from_input() -> None:
    result = build_analysis_result(
        file_path="examples/grand_second_position_with_metadata.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

    if result["profile_preset_settings"]["use_profile_presets"]:
        assert result["opponent_policy_settings"]["opponent_lead_policy"] in [
            "lowest_point",
            "basic_defender_lead",
            "highest_point",
        ]

def test_build_analysis_result_includes_game_declaration() -> None:
    result = build_analysis_result(
        file_path="examples/grand_second_position.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

    assert result["game_declaration"] == {
        "game_type": "grand",
        "hand_game": False,
        "ouvert": False,
        "schneider_announced": False,
        "schwarz_announced": False,
        "matadors": 4,
        "bid_value": None,
    }

def test_build_analysis_result_includes_game_value_summary() -> None:
    result = build_analysis_result(
        file_path="examples/grand_second_position.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

    assert result["game_value_summary"] == {
        "game_type": "grand",
        "is_null_game": False,
        "base_value": 24,
        "game_level": 5,
        "game_value": 120,
        "details": {
            "matadors": 4,
            "matador_multiplier": 5,
            "hand_game": False,
            "schneider_announced": False,
            "schwarz_announced": False,
            "ouvert": False,
            "modifier_multiplier": 0,
            "is_complete": True,
        },
    }

def test_build_analysis_result_includes_game_result_summary() -> None:
    result = build_analysis_result(
        file_path="examples/grand_second_position.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

    assert result["game_result_summary"] == {
        "declarer_points": 0,
        "defender_points": 0,
        "points_remaining": 120,
        "is_complete": False,
        "winner": "undecided",
        "status": "in_progress",
        "raw_schneider_status": "declarer_made_schneider",
        "raw_schwarz_status": "declarer_made_schwarz",
        "effective_schneider_status": "pending",
        "effective_schwarz_status": "pending",
        "thresholds": {
            "declarer_win": 61,
            "defender_win": 60,
            "schneider": 30,
            "schwarz": 0,
            "total_card_points": 120,
        },
    }

def test_build_analysis_result_includes_final_settlement_summary() -> None:
    result = build_analysis_result(
        file_path="examples/grand_second_position.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

    assert result["final_settlement_summary"] == {
        "is_complete": False,
        "missing_inputs": ["complete_card_points"],
        "declarer_won_by_card_points": None,
        "winner": None,
        "game_value": 120,
        "bid_value": None,
        "settlement_score": None,
        "is_loss": None,
        "is_overbid": None,
        "overbid_margin": None,
        "overbid_status": "unknown_bid_value",
        "effective_game_value": None,
        "overbid_required_game_value": None,
        "notes": [
            "Settlement score uses simplified Skat logic.",
            "Lost declarer games are counted as -2 * effective_game_value.",
            "Overbid settlement is supported for suit and grand games when "
            "required_game_value is available."
        ],
    }

def test_build_analysis_result_includes_adjusted_game_result_summary() -> None:
    result = build_analysis_result(
        file_path="examples/grand_second_position.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

    assert result["adjusted_game_result_summary"] == {
        "declarer_points": 0,
        "defender_points": 0,
        "points_remaining": 120,
        "is_complete": False,
        "winner": "undecided",
        "status": "in_progress",
        "raw_schneider_status": "declarer_made_schneider",
        "raw_schwarz_status": "declarer_made_schwarz",
        "effective_schneider_status": "pending",
        "effective_schwarz_status": "pending",
        "thresholds": {
            "declarer_win": 61,
            "defender_win": 60,
            "schneider": 30,
            "schwarz": 0,
            "total_card_points": 120,
        },
        "game_end_reason": "not_ended",
        "remaining_points_recipient": None,
        "remaining_points_assigned": 0,
    }

def test_build_analysis_result_includes_left_right_opponent_policy_settings() -> None:
    result = build_analysis_result(
        file_path="examples/grand_second_position.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

    assert result["left_opponent_policy_settings"] == {
        "opponent_lead_policy": "lowest_point",
        "opponent_response_policy": "lowest_point",
    }
    assert result["right_opponent_policy_settings"] == {
        "opponent_lead_policy": "lowest_point",
        "opponent_response_policy": "lowest_point",
    }


def test_build_analysis_result_applies_left_right_policy_overrides() -> None:
    result = build_analysis_result(
        file_path="examples/grand_second_position.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
        left_opponent_lead_policy_override="highest_point",
        left_opponent_response_policy_override="basic_trick_play",
        right_opponent_lead_policy_override="lowest_point",
        right_opponent_response_policy_override="highest_point",
    )

    assert result["left_opponent_policy_settings"] == {
        "opponent_lead_policy": "highest_point",
        "opponent_response_policy": "basic_trick_play",
    }
    assert result["right_opponent_policy_settings"] == {
        "opponent_lead_policy": "lowest_point",
        "opponent_response_policy": "highest_point",
    }


def build_immediate_response_policy_input(
    policy_fields: dict[str, object] | None = None,
) -> dict[str, object]:
    data: dict[str, object] = {
        "game_type": "grand",
        "player_role": "declarer",
        "player_position": "forehand",
        "trick_leader": "me",
        "hand": ["S7"],
        "current_trick": [],
        "played_cards": [],
        "completed_tricks": [],
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "me",
        "skat": [],
        "left_hand_size": 2,
        "right_hand_size": 2,
        "sample_count": 1,
        "random_seed": 1,
        "use_basic_opponent_strategy": True,
        "analysis_mode": "live_decision",
        "skat_visibility": "unknown",
        "game_end_reason": "not_ended",
        "hand_game": False,
        "ouvert": False,
        "schneider_announced": False,
        "schwarz_announced": False,
        "matadors": 1,
    }

    if policy_fields is not None:
        data.update(policy_fields)

    return data


def build_immediate_response_policy_map_for_test(
    policy_fields: dict[str, object] | None = None,
    left_player_profile: PlayerProfile | None = None,
    right_player_profile: PlayerProfile | None = None,
    opponent_policy_preset_override: str | None = None,
    opponent_response_policy_override: str | None = None,
    use_profile_presets_override: bool = False,
    left_opponent_response_policy_override: str | None = None,
    right_opponent_response_policy_override: str | None = None,
) -> dict[str, str] | None:
    settings = build_effective_opponent_policy_settings(
        data=build_immediate_response_policy_input(policy_fields),
        left_player_profile=left_player_profile or PlayerProfile(),
        right_player_profile=right_player_profile or PlayerProfile(),
        opponent_policy_preset_override=opponent_policy_preset_override,
        opponent_response_policy_override=opponent_response_policy_override,
        use_profile_presets_override=use_profile_presets_override,
        left_opponent_response_policy_override=left_opponent_response_policy_override,
        right_opponent_response_policy_override=right_opponent_response_policy_override,
    )

    return settings.immediate_response_policy_by_player


def build_immediate_response_policy_result(
    tmp_path,
    monkeypatch,
    policy_fields: dict[str, object] | None = None,
    opponent_policy_preset_override: str | None = None,
    opponent_lead_policy_override: str | None = None,
    opponent_response_policy_override: str | None = None,
    use_profile_presets_override: bool = False,
    left_opponent_lead_policy_override: str | None = None,
    left_opponent_response_policy_override: str | None = None,
    right_opponent_lead_policy_override: str | None = None,
    right_opponent_response_policy_override: str | None = None,
) -> dict[str, object]:
    def fake_generate_random_opponent_hands(
        state,
        left_hand_size: int,
        right_hand_size: int,
        random_generator=None,
    ) -> tuple[list[str], list[str]]:
        _ = (state, left_hand_size, right_hand_size, random_generator)
        return ["S8", "S10"], ["S9", "SA"]

    monkeypatch.setattr(
        "skat_ai.simulation.generate_random_opponent_hands",
        fake_generate_random_opponent_hands,
    )
    input_path = tmp_path / "immediate_response_policy.json"
    input_path.write_text(
        json.dumps(build_immediate_response_policy_input(policy_fields)),
        encoding="utf-8",
    )

    return build_analysis_result(
        file_path=str(input_path),
        sample_count_override=1,
        random_seed_override=1,
        opponent_strategy_override="basic",
        opponent_policy_preset_override=opponent_policy_preset_override,
        opponent_lead_policy_override=opponent_lead_policy_override,
        opponent_response_policy_override=opponent_response_policy_override,
        use_profile_presets_override=use_profile_presets_override,
        left_opponent_lead_policy_override=left_opponent_lead_policy_override,
        left_opponent_response_policy_override=left_opponent_response_policy_override,
        right_opponent_lead_policy_override=right_opponent_lead_policy_override,
        right_opponent_response_policy_override=right_opponent_response_policy_override,
    )


def get_only_analysis_report_row(result: dict[str, object]) -> dict[str, object]:
    report = result["analysis_report"]

    assert isinstance(report, list)
    assert len(report) == 1

    row = report[0]
    assert isinstance(row, dict)

    return row


def build_aggressive_profile() -> PlayerProfile:
    return PlayerProfile(
        games_played=1000,
        solo_rate=0.38,
    )


def build_cautious_profile() -> PlayerProfile:
    return PlayerProfile(
        games_played=1000,
        solo_rate=0.25,
        grand_rate=0.15,
        hand_game_rate=0.03,
        defender_win_rate=0.55,
    )


def test_immediate_policy_map_defaults_to_none() -> None:
    policy_map = build_immediate_response_policy_map_for_test()

    assert policy_map is None


def test_immediate_policy_map_ignores_profiles_when_disabled() -> None:
    policy_map = build_immediate_response_policy_map_for_test(
        left_player_profile=build_cautious_profile(),
        right_player_profile=build_aggressive_profile(),
    )

    assert policy_map is None


def test_immediate_policy_map_ignores_false_profile_flag() -> None:
    policy_map = build_immediate_response_policy_map_for_test(
        policy_fields={
            "use_profile_presets": False,
        },
        left_player_profile=build_cautious_profile(),
        right_player_profile=build_aggressive_profile(),
    )

    assert policy_map is None


def test_immediate_policy_map_applies_global_json_policy() -> None:
    policy_map = build_immediate_response_policy_map_for_test(
        policy_fields={
            "opponent_response_policy": "highest_point",
        },
    )

    assert policy_map == {
        "left": "highest_point",
        "right": "highest_point",
    }


def test_immediate_policy_map_keeps_side_only_policy_sparse() -> None:
    policy_map = build_immediate_response_policy_map_for_test(
        policy_fields={
            "left_opponent_response_policy": "highest_point",
        },
    )

    assert policy_map == {
        "left": "highest_point",
    }


def test_immediate_policy_map_explicit_lowest_activates() -> None:
    policy_map = build_immediate_response_policy_map_for_test(
        policy_fields={
            "left_opponent_response_policy": "lowest_point",
        },
    )

    assert policy_map == {
        "left": "lowest_point",
    }


def test_immediate_policy_map_side_json_overrides_global_json() -> None:
    policy_map = build_immediate_response_policy_map_for_test(
        policy_fields={
            "opponent_response_policy": "highest_point",
            "right_opponent_response_policy": "lowest_point",
        },
    )

    assert policy_map == {
        "left": "highest_point",
        "right": "lowest_point",
    }


def test_immediate_policy_map_input_preset_activates_both_sides() -> None:
    policy_map = build_immediate_response_policy_map_for_test(
        policy_fields={
            "opponent_policy_preset": "cautious_defender",
        },
    )

    assert policy_map == {
        "left": "basic_defender_response",
        "right": "basic_defender_response",
    }


def test_immediate_policy_map_global_json_overrides_input_preset() -> None:
    policy_map = build_immediate_response_policy_map_for_test(
        policy_fields={
            "opponent_policy_preset": "cautious_defender",
            "opponent_response_policy": "highest_point",
        },
    )

    assert policy_map == {
        "left": "highest_point",
        "right": "highest_point",
    }


def test_immediate_policy_map_side_json_overrides_preset_and_global() -> None:
    policy_map = build_immediate_response_policy_map_for_test(
        policy_fields={
            "opponent_policy_preset": "aggressive_points",
            "opponent_response_policy": "basic_trick_play",
            "left_opponent_response_policy": "lowest_point",
        },
    )

    assert policy_map == {
        "left": "lowest_point",
        "right": "basic_trick_play",
    }


def test_immediate_policy_map_input_profile_presets_apply_by_side() -> None:
    policy_map = build_immediate_response_policy_map_for_test(
        policy_fields={
            "use_profile_presets": True,
        },
        left_player_profile=build_cautious_profile(),
        right_player_profile=build_aggressive_profile(),
    )

    assert policy_map == {
        "left": "basic_defender_response",
        "right": "highest_point",
    }


def test_immediate_policy_map_keeps_non_applicable_profile_side_absent() -> None:
    policy_map = build_immediate_response_policy_map_for_test(
        policy_fields={
            "use_profile_presets": True,
        },
        right_player_profile=build_aggressive_profile(),
    )

    assert policy_map == {
        "right": "highest_point",
    }


def test_immediate_policy_map_cli_profile_presets_apply_by_side() -> None:
    policy_map = build_immediate_response_policy_map_for_test(
        left_player_profile=build_cautious_profile(),
        right_player_profile=build_aggressive_profile(),
        use_profile_presets_override=True,
    )

    assert policy_map == {
        "left": "basic_defender_response",
        "right": "highest_point",
    }


def test_immediate_policy_map_side_json_overrides_profile_policy() -> None:
    policy_map = build_immediate_response_policy_map_for_test(
        policy_fields={
            "use_profile_presets": True,
            "left_opponent_response_policy": "lowest_point",
        },
        left_player_profile=build_cautious_profile(),
        right_player_profile=build_aggressive_profile(),
    )

    assert policy_map == {
        "left": "lowest_point",
        "right": "highest_point",
    }


def test_immediate_policy_map_cli_preset_overrides_input_side() -> None:
    policy_map = build_immediate_response_policy_map_for_test(
        policy_fields={
            "left_opponent_response_policy": "basic_trick_play",
        },
        opponent_policy_preset_override="aggressive_points",
    )

    assert policy_map == {
        "left": "highest_point",
        "right": "highest_point",
    }


def test_immediate_policy_map_cli_profile_overrides_cli_preset_side() -> None:
    policy_map = build_immediate_response_policy_map_for_test(
        right_player_profile=build_cautious_profile(),
        opponent_policy_preset_override="random",
        use_profile_presets_override=True,
    )

    assert policy_map == {
        "left": "random_legal",
        "right": "basic_defender_response",
    }


def test_immediate_policy_map_global_cli_response_overrides_profile() -> None:
    policy_map = build_immediate_response_policy_map_for_test(
        policy_fields={
            "use_profile_presets": True,
        },
        right_player_profile=build_aggressive_profile(),
        opponent_response_policy_override="lowest_point",
    )

    assert policy_map == {
        "left": "lowest_point",
        "right": "lowest_point",
    }


def test_immediate_policy_map_global_cli_response_overrides_input_side() -> None:
    policy_map = build_immediate_response_policy_map_for_test(
        policy_fields={
            "left_opponent_response_policy": "basic_trick_play",
        },
        opponent_response_policy_override="highest_point",
    )

    assert policy_map == {
        "left": "highest_point",
        "right": "highest_point",
    }


def test_immediate_policy_map_side_cli_response_is_final() -> None:
    policy_map = build_immediate_response_policy_map_for_test(
        opponent_response_policy_override="highest_point",
        left_opponent_response_policy_override="lowest_point",
    )

    assert policy_map == {
        "left": "lowest_point",
        "right": "highest_point",
    }


def test_immediate_policy_map_side_only_cli_response_is_sparse() -> None:
    policy_map = build_immediate_response_policy_map_for_test(
        right_opponent_response_policy_override="highest_point",
    )

    assert policy_map == {
        "right": "highest_point",
    }


def test_build_analysis_result_without_explicit_response_policy_keeps_legacy_immediate_result(
    tmp_path,
    monkeypatch,
) -> None:
    result = build_immediate_response_policy_result(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
    )
    row = get_only_analysis_report_row(result)

    assert row["card"] == "S7"
    assert row["average_trick_points"] == 0.0


def test_build_analysis_result_global_lead_only_cli_does_not_activate_immediate_response_policy(
    tmp_path,
    monkeypatch,
) -> None:
    result = build_immediate_response_policy_result(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        opponent_lead_policy_override="highest_point",
    )
    row = get_only_analysis_report_row(result)

    assert result["opponent_policy_settings"] == {
        "opponent_lead_policy": "highest_point",
        "opponent_response_policy": "lowest_point",
    }
    assert result["left_opponent_policy_settings"] == {
        "opponent_lead_policy": "highest_point",
        "opponent_response_policy": "lowest_point",
    }
    assert result["right_opponent_policy_settings"] == {
        "opponent_lead_policy": "highest_point",
        "opponent_response_policy": "lowest_point",
    }
    assert row["card"] == "S7"
    assert row["average_trick_points"] == 0.0


def test_build_analysis_result_input_side_lead_only_does_not_activate_immediate_response_policy(
    tmp_path,
    monkeypatch,
) -> None:
    result = build_immediate_response_policy_result(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        policy_fields={
            "left_opponent_lead_policy": "highest_point",
        },
    )
    row = get_only_analysis_report_row(result)

    assert result["left_opponent_policy_settings"] == {
        "opponent_lead_policy": "highest_point",
        "opponent_response_policy": "lowest_point",
    }
    assert result["right_opponent_policy_settings"] == {
        "opponent_lead_policy": "lowest_point",
        "opponent_response_policy": "lowest_point",
    }
    assert row["card"] == "S7"
    assert row["average_trick_points"] == 0.0


def test_build_analysis_result_applies_explicit_global_response_policy_to_both_sides(
    tmp_path,
    monkeypatch,
) -> None:
    result = build_immediate_response_policy_result(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        policy_fields={
            "opponent_response_policy": "highest_point",
        },
    )
    row = get_only_analysis_report_row(result)

    assert row["card"] == "S7"
    assert row["average_trick_points"] == 21.0


def test_build_analysis_result_right_response_policy_overrides_global_response_policy(
    tmp_path,
    monkeypatch,
) -> None:
    result = build_immediate_response_policy_result(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        policy_fields={
            "opponent_response_policy": "highest_point",
            "right_opponent_response_policy": "lowest_point",
        },
    )
    row = get_only_analysis_report_row(result)

    assert row["card"] == "S7"
    assert row["average_trick_points"] == 10.0


def test_build_analysis_result_left_response_policy_overrides_global_response_policy(
    tmp_path,
    monkeypatch,
) -> None:
    result = build_immediate_response_policy_result(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        policy_fields={
            "opponent_response_policy": "highest_point",
            "left_opponent_response_policy": "lowest_point",
        },
    )
    row = get_only_analysis_report_row(result)

    assert row["card"] == "S7"
    assert row["average_trick_points"] == 11.0


def test_build_analysis_result_applies_cli_response_policy_to_immediate_analysis(
    tmp_path,
    monkeypatch,
) -> None:
    result = build_immediate_response_policy_result(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        opponent_response_policy_override="highest_point",
    )
    row = get_only_analysis_report_row(result)

    assert row["card"] == "S7"
    assert row["average_trick_points"] == 21.0


def test_build_analysis_result_applies_cli_preset_to_immediate_analysis(
    tmp_path,
    monkeypatch,
) -> None:
    result = build_immediate_response_policy_result(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        opponent_policy_preset_override="aggressive_points",
    )
    row = get_only_analysis_report_row(result)

    assert row["card"] == "S7"
    assert row["average_trick_points"] == 21.0


def test_build_analysis_result_applies_profile_presets_to_immediate_analysis(
    tmp_path,
    monkeypatch,
) -> None:
    result = build_immediate_response_policy_result(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        policy_fields={
            "right_player_profile": {
                "games_played": 1000,
                "solo_rate": 0.38,
            },
        },
        use_profile_presets_override=True,
    )
    row = get_only_analysis_report_row(result)

    assert row["card"] == "S7"
    assert row["average_trick_points"] == 11.0


def test_build_analysis_result_side_cli_policy_uses_correct_immediate_responder(
    tmp_path,
    monkeypatch,
) -> None:
    from skat_ai.opponent_policy import choose_opponent_response_card_by_policy

    calls = []

    def fake_generate_random_opponent_hands(
        state,
        left_hand_size: int,
        right_hand_size: int,
        random_generator=None,
    ) -> tuple[list[str], list[str]]:
        _ = (state, left_hand_size, right_hand_size, random_generator)
        return ["S9", "SA"], ["S10", "H7"]

    def recording_choose_opponent_response_card_by_policy(
        hand,
        current_trick,
        game_type,
        player_index,
        policy="basic_trick_play",
        random_generator=None,
        partner_currently_winning=False,
    ):
        selected_card = choose_opponent_response_card_by_policy(
            hand=hand,
            current_trick=current_trick,
            game_type=game_type,
            player_index=player_index,
            policy=policy,
            random_generator=random_generator,
            partner_currently_winning=partner_currently_winning,
        )
        calls.append(
            {
                "hand": hand.copy(),
                "policy": policy,
                "selected_card": selected_card,
            }
        )
        return selected_card

    monkeypatch.setattr(
        "skat_ai.simulation.generate_random_opponent_hands",
        fake_generate_random_opponent_hands,
    )
    monkeypatch.setattr(
        "skat_ai.simulation.choose_opponent_response_card_by_policy",
        recording_choose_opponent_response_card_by_policy,
    )

    input_path = tmp_path / "immediate_left_responder_policy.json"
    input_path.write_text(
        json.dumps(
            {
                "game_type": "grand",
                "player_role": "declarer",
                "player_position": "middlehand",
                "trick_leader": "right",
                "hand": ["S8"],
                "current_trick": ["S7"],
                "played_cards": [],
                "completed_tricks": [],
                "declarer_points": 0,
                "defender_points": 0,
                "next_player": "me",
                "skat": [],
                "left_hand_size": 2,
                "right_hand_size": 2,
                "sample_count": 1,
                "random_seed": 1,
                "use_basic_opponent_strategy": True,
                "analysis_mode": "live_decision",
                "skat_visibility": "unknown",
                "game_end_reason": "not_ended",
                "hand_game": False,
                "ouvert": False,
                "schneider_announced": False,
                "schwarz_announced": False,
                "matadors": 1,
            }
        ),
        encoding="utf-8",
    )

    result = build_analysis_result(
        file_path=str(input_path),
        sample_count_override=1,
        random_seed_override=1,
        opponent_strategy_override="basic",
        left_opponent_response_policy_override="highest_point",
    )
    row = get_only_analysis_report_row(result)

    assert row["card"] == "S8"
    assert row["average_trick_points"] == 11.0
    assert calls
    assert all(call["hand"] == ["S9", "SA"] for call in calls)
    assert all(call["policy"] == "highest_point" for call in calls)
    assert all(call["selected_card"] == "SA" for call in calls)


def test_run_json_position_analysis_supports_left_right_policy_overrides() -> None:
    run_json_position_analysis(
        file_path="examples/grand_second_position.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
        output_path=None,
        multi_step_count=None,
        card_selection_policy="highest_expected_value",
        expected_value_sample_count=20,
        strict_context=False,
        compare_policies=False,
        comparison_only=False,
        left_opponent_lead_policy_override="highest_point",
        left_opponent_response_policy_override="basic_trick_play",
        right_opponent_lead_policy_override="lowest_point",
        right_opponent_response_policy_override="highest_point",
    )


def test_run_json_position_analysis_threads_left_right_policies_to_multi_step() -> None:
    run_json_position_analysis(
        file_path="examples/grand_second_position.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
        output_path=None,
        multi_step_count=1,
        card_selection_policy="highest_expected_value",
        expected_value_sample_count=20,
        strict_context=False,
        compare_policies=False,
        comparison_only=False,
        left_opponent_lead_policy_override="highest_point",
        left_opponent_response_policy_override="basic_trick_play",
        right_opponent_lead_policy_override="lowest_point",
        right_opponent_response_policy_override="highest_point",
    )


def test_run_json_position_analysis_writes_left_right_policy_settings_to_output(
    tmp_path,
) -> None:
    import json

    output_path = tmp_path / "result.json"

    run_json_position_analysis(
        file_path="examples/grand_second_position.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
        output_path=str(output_path),
        multi_step_count=1,
        card_selection_policy="highest_expected_value",
        expected_value_sample_count=20,
        strict_context=False,
        compare_policies=False,
        comparison_only=False,
        left_opponent_lead_policy_override="highest_point",
        left_opponent_response_policy_override="basic_trick_play",
        right_opponent_lead_policy_override="lowest_point",
        right_opponent_response_policy_override="highest_point",
    )

    with output_path.open("r", encoding="utf-8") as file:
        result = json.load(file)

    assert result["left_opponent_policy_settings"] == {
        "opponent_lead_policy": "highest_point",
        "opponent_response_policy": "basic_trick_play",
    }
    assert result["right_opponent_policy_settings"] == {
        "opponent_lead_policy": "lowest_point",
        "opponent_response_policy": "highest_point",
    }


def test_run_json_position_analysis_accepts_random_left_right_policy_overrides() -> None:
    run_json_position_analysis(
        file_path="examples/grand_second_position.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
        output_path=None,
        multi_step_count=1,
        card_selection_policy="highest_expected_value",
        expected_value_sample_count=20,
        strict_context=False,
        compare_policies=False,
        comparison_only=False,
        left_opponent_lead_policy_override="random_legal",
        left_opponent_response_policy_override="random_legal",
        right_opponent_lead_policy_override="random_legal",
        right_opponent_response_policy_override="random_legal",
    )


def test_run_json_position_analysis_writes_updated_policy_settings_to_output(
    tmp_path,
) -> None:
    output_path = tmp_path / "result.json"

    run_json_position_analysis(
        file_path="examples/grand_second_position.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
        output_path=str(output_path),
        multi_step_count=1,
        card_selection_policy="highest_expected_value",
        expected_value_sample_count=20,
        strict_context=False,
        compare_policies=False,
        comparison_only=False,
        opponent_lead_policy_override="highest_point",
        opponent_response_policy_override="basic_trick_play",
        left_opponent_lead_policy_override="lowest_point",
        left_opponent_response_policy_override="basic_defender_response",
        right_opponent_lead_policy_override="basic_defender_lead",
        right_opponent_response_policy_override="highest_point",
    )

    with output_path.open("r", encoding="utf-8") as file:
        result = json.load(file)

    assert result["opponent_policy_settings"] == {
        "opponent_lead_policy": "highest_point",
        "opponent_response_policy": "basic_trick_play",
    }
    assert result["left_opponent_policy_settings"] == {
        "opponent_lead_policy": "lowest_point",
        "opponent_response_policy": "basic_defender_response",
    }
    assert result["right_opponent_policy_settings"] == {
        "opponent_lead_policy": "basic_defender_lead",
        "opponent_response_policy": "highest_point",
    }
    assert result["multi_step_result"]["opponent_policy_settings"] == {
        "opponent_lead_policy": "highest_point",
        "opponent_response_policy": "basic_trick_play",
    }
    assert result["multi_step_result"]["left_opponent_policy_settings"] == {
        "opponent_lead_policy": "lowest_point",
        "opponent_response_policy": "basic_defender_response",
    }
    assert result["multi_step_result"]["right_opponent_policy_settings"] == {
        "opponent_lead_policy": "basic_defender_lead",
        "opponent_response_policy": "highest_point",
    }


def test_run_json_position_analysis_applies_profile_presets_to_left_right_output(
    tmp_path,
) -> None:
    output_path = tmp_path / "result.json"

    run_json_position_analysis(
        file_path="examples/grand_midgame_profile_preset_live.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
        output_path=str(output_path),
        multi_step_count=1,
        card_selection_policy="highest_point",
        expected_value_sample_count=20,
        strict_context=False,
        compare_policies=False,
        comparison_only=False,
    )

    with output_path.open("r", encoding="utf-8") as file:
        result = json.load(file)

    assert result["profile_preset_settings"] == {
        "use_profile_presets": True,
    }
    assert result["left_opponent_policy_settings"] == {
        "opponent_lead_policy": "basic_defender_lead",
        "opponent_response_policy": "basic_defender_response",
    }
    assert result["right_opponent_policy_settings"] == {
        "opponent_lead_policy": "highest_point",
        "opponent_response_policy": "highest_point",
    }
    assert result["multi_step_result"]["left_opponent_policy_settings"] == {
        "opponent_lead_policy": "basic_defender_lead",
        "opponent_response_policy": "basic_defender_response",
    }
    assert result["multi_step_result"]["right_opponent_policy_settings"] == {
        "opponent_lead_policy": "highest_point",
        "opponent_response_policy": "highest_point",
    }
    assert "opponent_profile_application_summary" not in result


def test_run_json_position_analysis_keeps_left_right_cli_overrides_final(
    tmp_path,
) -> None:
    output_path = tmp_path / "result.json"

    run_json_position_analysis(
        file_path="examples/grand_midgame_profile_preset_live.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
        output_path=str(output_path),
        multi_step_count=1,
        card_selection_policy="highest_point",
        expected_value_sample_count=20,
        strict_context=False,
        compare_policies=False,
        comparison_only=False,
        left_opponent_lead_policy_override="lowest_point",
        left_opponent_response_policy_override="lowest_point",
        right_opponent_lead_policy_override="basic_defender_lead",
        right_opponent_response_policy_override="basic_defender_response",
    )

    with output_path.open("r", encoding="utf-8") as file:
        result = json.load(file)

    assert result["left_opponent_policy_settings"] == {
        "opponent_lead_policy": "lowest_point",
        "opponent_response_policy": "lowest_point",
    }
    assert result["right_opponent_policy_settings"] == {
        "opponent_lead_policy": "basic_defender_lead",
        "opponent_response_policy": "basic_defender_response",
    }
    assert result["multi_step_result"]["left_opponent_policy_settings"] == {
        "opponent_lead_policy": "lowest_point",
        "opponent_response_policy": "lowest_point",
    }
    assert result["multi_step_result"]["right_opponent_policy_settings"] == {
        "opponent_lead_policy": "basic_defender_lead",
        "opponent_response_policy": "basic_defender_response",
    }


def build_policy_orchestration_input(
    policy_fields: dict[str, object] | None = None,
) -> dict[str, object]:
    data: dict[str, object] = {
        "game_type": "grand",
        "player_role": "declarer",
        "player_position": "middlehand",
        "trick_leader": "right",
        "hand": ["SA"],
        "current_trick": ["S7"],
        "played_cards": [],
        "completed_tricks": [],
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "me",
        "skat": [],
        "left_hand_size": 1,
        "right_hand_size": 1,
        "sample_count": 1,
        "random_seed": 1,
        "use_basic_opponent_strategy": True,
        "analysis_mode": "live_decision",
        "skat_visibility": "unknown",
        "game_end_reason": "not_ended",
        "hand_game": False,
        "ouvert": False,
        "schneider_announced": False,
        "schwarz_announced": False,
        "matadors": 1,
    }

    if policy_fields is not None:
        data.update(policy_fields)

    return data


def capture_multi_step_policy_orchestration(
    tmp_path,
    monkeypatch,
    policy_fields: dict[str, object] | None = None,
    opponent_policy_preset_override: str | None = None,
    opponent_lead_policy_override: str | None = None,
    opponent_response_policy_override: str | None = None,
    use_profile_presets_override: bool = False,
    left_opponent_lead_policy_override: str | None = None,
    left_opponent_response_policy_override: str | None = None,
    right_opponent_lead_policy_override: str | None = None,
    right_opponent_response_policy_override: str | None = None,
) -> dict[str, object]:
    captured: dict[str, object] = {}

    def fake_simulate_multiple_steps(**kwargs):
        captured.update(kwargs)
        state = kwargs["state"]

        return {
            "initial_state": state,
            "final_state": state,
            "card_selection_policy": kwargs["card_selection_policy"],
            "requested_step_count": kwargs["step_count"],
            "steps_simulated": 0,
            "stop_reason": "characterization fake",
            "strict_context": kwargs["strict_context"],
            "opponent_policy_settings": {
                "opponent_lead_policy": kwargs["opponent_lead_policy"],
                "opponent_response_policy": kwargs["opponent_response_policy"],
            },
            "left_opponent_policy_settings": kwargs["left_opponent_policy_settings"],
            "right_opponent_policy_settings": kwargs["right_opponent_policy_settings"],
            "context_summary": {
                "simulated_opponent_card_count": 0,
                "unique_simulated_opponent_card_count": 0,
                "duplicate_simulated_opponent_cards": [],
                "event_count": 0,
                "strategic_metadata": {
                    "analysis_mode": "live_decision",
                    "skat_visibility": "unknown",
                    "game_end_reason": "not_ended",
                },
            },
            "steps": [],
            "summary": {
                "requested_step_count": kwargs["step_count"],
                "steps_simulated": 0,
                "stop_reason": "characterization fake",
                "card_selection_policy": kwargs["card_selection_policy"],
                "strict_context": kwargs["strict_context"],
                "score_summary": {
                    "initial_declarer_points": 0,
                    "initial_defender_points": 0,
                    "final_declarer_points": 0,
                    "final_defender_points": 0,
                    "declarer_points_gained": 0,
                    "defender_points_gained": 0,
                    "final_point_swing": 0,
                },
                "context_summary": {},
            },
        }

    monkeypatch.setattr("main.simulate_multiple_steps", fake_simulate_multiple_steps)
    input_path = tmp_path / "policy_orchestration.json"
    input_path.write_text(
        json.dumps(build_policy_orchestration_input(policy_fields)),
        encoding="utf-8",
    )

    run_json_position_analysis(
        file_path=str(input_path),
        sample_count_override=1,
        random_seed_override=1,
        opponent_strategy_override="basic",
        output_path=None,
        multi_step_count=1,
        card_selection_policy="highest_point",
        expected_value_sample_count=1,
        strict_context=False,
        compare_policies=False,
        comparison_only=False,
        opponent_policy_preset_override=opponent_policy_preset_override,
        opponent_lead_policy_override=opponent_lead_policy_override,
        opponent_response_policy_override=opponent_response_policy_override,
        use_profile_presets_override=use_profile_presets_override,
        left_opponent_lead_policy_override=left_opponent_lead_policy_override,
        left_opponent_response_policy_override=left_opponent_response_policy_override,
        right_opponent_lead_policy_override=right_opponent_lead_policy_override,
        right_opponent_response_policy_override=right_opponent_response_policy_override,
    )

    return captured


def test_multi_step_global_cli_preset_cascades_to_side_settings(
    tmp_path,
    monkeypatch,
) -> None:
    captured = capture_multi_step_policy_orchestration(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        policy_fields={
            "left_opponent_lead_policy": "basic_defender_lead",
            "left_opponent_response_policy": "basic_defender_response",
            "right_opponent_lead_policy": "lowest_point",
            "right_opponent_response_policy": "basic_trick_play",
        },
        opponent_policy_preset_override="aggressive_points",
    )

    assert captured["opponent_lead_policy"] == "highest_point"
    assert captured["opponent_response_policy"] == "highest_point"
    assert captured["left_opponent_policy_settings"] == {
        "opponent_lead_policy": "highest_point",
        "opponent_response_policy": "highest_point",
    }
    assert captured["right_opponent_policy_settings"] == {
        "opponent_lead_policy": "highest_point",
        "opponent_response_policy": "highest_point",
    }
    assert captured["opponent_response_policy_by_player"] == {
        "left": "highest_point",
        "right": "highest_point",
    }


def test_multi_step_global_cli_policies_cascade_to_side_settings(
    tmp_path,
    monkeypatch,
) -> None:
    captured = capture_multi_step_policy_orchestration(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        policy_fields={
            "left_opponent_lead_policy": "basic_defender_lead",
            "left_opponent_response_policy": "basic_defender_response",
            "right_opponent_lead_policy": "lowest_point",
            "right_opponent_response_policy": "basic_trick_play",
        },
        opponent_lead_policy_override="highest_point",
        opponent_response_policy_override="highest_point",
    )

    assert captured["opponent_lead_policy"] == "highest_point"
    assert captured["opponent_response_policy"] == "highest_point"
    assert captured["left_opponent_policy_settings"] == {
        "opponent_lead_policy": "highest_point",
        "opponent_response_policy": "highest_point",
    }
    assert captured["right_opponent_policy_settings"] == {
        "opponent_lead_policy": "highest_point",
        "opponent_response_policy": "highest_point",
    }
    assert captured["opponent_response_policy_by_player"] == {
        "left": "highest_point",
        "right": "highest_point",
    }


def test_multi_step_explicit_input_side_settings_override_input_profiles(
    tmp_path,
    monkeypatch,
) -> None:
    captured = capture_multi_step_policy_orchestration(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        policy_fields={
            "use_profile_presets": True,
            "left_opponent_lead_policy": "lowest_point",
            "left_opponent_response_policy": "lowest_point",
            "left_player_profile": {
                "games_played": 1000,
                "solo_rate": 0.25,
                "grand_rate": 0.15,
                "hand_game_rate": 0.03,
                "defender_win_rate": 0.55,
            },
        },
    )

    assert captured["left_opponent_policy_settings"] == {
        "opponent_lead_policy": "lowest_point",
        "opponent_response_policy": "lowest_point",
    }
    assert captured["opponent_response_policy_by_player"] == {
        "left": "lowest_point",
    }


def test_multi_step_global_cli_response_overrides_cli_activated_profile_response(
    tmp_path,
    monkeypatch,
) -> None:
    captured = capture_multi_step_policy_orchestration(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        policy_fields={
            "right_player_profile": {
                "games_played": 1000,
                "solo_rate": 0.38,
            },
        },
        use_profile_presets_override=True,
        opponent_response_policy_override="lowest_point",
    )

    assert captured["opponent_response_policy"] == "lowest_point"
    assert captured["right_opponent_policy_settings"] == {
        "opponent_lead_policy": "highest_point",
        "opponent_response_policy": "lowest_point",
    }
    assert captured["opponent_response_policy_by_player"] == {
        "left": "lowest_point",
        "right": "lowest_point",
    }


def test_multi_step_side_cli_values_remain_final_after_profiles(
    tmp_path,
    monkeypatch,
) -> None:
    captured = capture_multi_step_policy_orchestration(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        policy_fields={
            "use_profile_presets": True,
            "left_player_profile": {
                "games_played": 1000,
                "solo_rate": 0.25,
                "grand_rate": 0.15,
                "hand_game_rate": 0.03,
                "defender_win_rate": 0.55,
            },
        },
        left_opponent_lead_policy_override="highest_point",
        left_opponent_response_policy_override="highest_point",
    )

    assert captured["left_opponent_policy_settings"] == {
        "opponent_lead_policy": "highest_point",
        "opponent_response_policy": "highest_point",
    }


@pytest.mark.parametrize(
    (
        "policy_fields",
        "cli_overrides",
        "expected_right_response_policy",
    ),
    [
        (
            {"opponent_response_policy": "highest_point"},
            {},
            "highest_point",
        ),
        (
            {"right_opponent_response_policy": "basic_defender_response"},
            {},
            "basic_defender_response",
        ),
        (
            {"opponent_policy_preset": "cautious_defender"},
            {},
            "basic_defender_response",
        ),
        (
            {
                "use_profile_presets": True,
                "right_player_profile": {
                    "games_played": 1000,
                    "solo_rate": 0.38,
                },
            },
            {},
            "highest_point",
        ),
        (
            {},
            {"opponent_policy_preset_override": "aggressive_points"},
            "highest_point",
        ),
        (
            {},
            {"opponent_response_policy_override": "highest_point"},
            "highest_point",
        ),
        (
            {"opponent_response_policy": "highest_point"},
            {"right_opponent_response_policy_override": "lowest_point"},
            "lowest_point",
        ),
    ],
)
def test_multi_step_orchestration_uses_same_effective_response_for_candidate_and_preparation(
    tmp_path,
    monkeypatch,
    policy_fields: dict[str, object],
    cli_overrides: dict[str, object],
    expected_right_response_policy: str,
) -> None:
    captured = capture_multi_step_policy_orchestration(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        policy_fields=policy_fields,
        **cli_overrides,
    )

    response_policy_by_player = captured["opponent_response_policy_by_player"]

    assert isinstance(response_policy_by_player, dict)
    assert response_policy_by_player["right"] == expected_right_response_policy
    assert captured["right_opponent_policy_settings"]["opponent_response_policy"] == (
        expected_right_response_policy
    )


def write_position_file(tmp_path, data: dict[str, object]) -> str:
    input_path = tmp_path / "position.json"
    input_path.write_text(json.dumps(data), encoding="utf-8")
    return str(input_path)


def build_turn_phase_position_input(
    trick_leader: str,
    current_trick: list[str],
    next_player: str,
) -> dict[str, object]:
    return {
        "game_type": "grand",
        "player_role": "declarer",
        "player_position": "forehand",
        "trick_leader": trick_leader,
        "hand": ["SA", "S10", "S9"],
        "current_trick": current_trick,
        "played_cards": [],
        "completed_tricks": [],
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": next_player,
        "skat": [],
        "left_hand_size": 5,
        "right_hand_size": 5,
        "sample_count": 5,
        "random_seed": 1,
        "use_basic_opponent_strategy": True,
    }


def assert_immediate_unavailable_for_opponent_turn(result: dict[str, object]) -> None:
    assert result["legal_cards"] == []
    assert result["analysis_report"] == []
    assert result["recommendation"] == {
        "card": None,
        "reason": "Immediate analysis is unavailable because the local player is not next.",
    }
    assert result["strategic_summary"] == (
        "Strategic summary: Immediate analysis is unavailable because the local player is not next."
    )


def test_build_analysis_result_keeps_immediate_available_when_local_player_is_next(
    tmp_path,
) -> None:
    data = build_turn_phase_position_input(
        trick_leader="right",
        current_trick=["S7"],
        next_player="me",
    )
    input_path = write_position_file(tmp_path, data)

    result = build_analysis_result(input_path)

    assert len(result["legal_cards"]) > 0
    assert len(result["analysis_report"]) > 0
    assert result["recommendation"]["card"] in result["legal_cards"]


def test_build_analysis_result_marks_left_turn_immediate_unavailable(
    tmp_path,
) -> None:
    data = build_turn_phase_position_input(
        trick_leader="left",
        current_trick=[],
        next_player="left",
    )
    input_path = write_position_file(tmp_path, data)

    result = build_analysis_result(input_path)

    assert result["position"]["next_player"] == "left"
    assert_immediate_unavailable_for_opponent_turn(result)


def test_build_analysis_result_marks_right_turn_immediate_unavailable(
    tmp_path,
) -> None:
    data = build_turn_phase_position_input(
        trick_leader="right",
        current_trick=[],
        next_player="right",
    )
    input_path = write_position_file(tmp_path, data)

    result = build_analysis_result(input_path)

    assert result["position"]["next_player"] == "right"
    assert_immediate_unavailable_for_opponent_turn(result)


def test_build_analysis_result_redacts_defender_known_to_declarer_skat(
    tmp_path,
) -> None:
    data = build_turn_phase_position_input(
        trick_leader="me",
        current_trick=[],
        next_player="me",
    )
    data["player_role"] = "defender"
    data["declarer_player"] = "left"
    data["analysis_mode"] = "live_decision"
    data["skat_visibility"] = "known_to_declarer"
    data["skat"] = ["C7", "D8"]
    data["left_hand_size"] = 3
    data["right_hand_size"] = 3
    input_path = write_position_file(tmp_path, data)

    result = build_analysis_result(input_path)

    assert result["position"]["skat"] == []
    assert result["analysis_metadata"]["strategic_metadata"]["skat_visibility"] == (
        "known_to_declarer"
    )


def test_build_analysis_result_defender_recommendation_ignores_private_skat_identities(
    tmp_path,
) -> None:
    base_data = build_turn_phase_position_input(
        trick_leader="me",
        current_trick=[],
        next_player="me",
    )
    base_data["player_role"] = "defender"
    base_data["declarer_player"] = "left"
    base_data["analysis_mode"] = "live_decision"
    base_data["skat_visibility"] = "known_to_declarer"
    base_data["left_hand_size"] = 3
    base_data["right_hand_size"] = 3
    base_data["sample_count"] = 5
    base_data["random_seed"] = 42
    first_input_path = write_position_file(
        tmp_path,
        {**base_data, "skat": ["C7", "D8"]},
    )
    second_path = tmp_path / "second_position.json"
    second_path.write_text(
        json.dumps({**base_data, "skat": ["H7", "D9"]}),
        encoding="utf-8",
    )

    first_result = build_analysis_result(first_input_path)
    second_result = build_analysis_result(str(second_path))

    assert first_result["position"] == second_result["position"]
    assert first_result["analysis_report"] == second_result["analysis_report"]
    assert first_result["recommendation"] == second_result["recommendation"]


def test_build_analysis_result_skips_immediate_simulation_for_opponent_turn(
    tmp_path,
    monkeypatch,
) -> None:
    def fail_recommend_card_by_expected_value(**_kwargs):
        raise AssertionError("Immediate recommendation should not run")

    def fail_build_card_analysis_report(**_kwargs):
        raise AssertionError("Immediate report should not run")

    monkeypatch.setattr(
        "main.recommend_card_by_expected_value",
        fail_recommend_card_by_expected_value,
    )
    monkeypatch.setattr(
        "main.build_card_analysis_report",
        fail_build_card_analysis_report,
    )
    data = build_turn_phase_position_input(
        trick_leader="left",
        current_trick=[],
        next_player="left",
    )
    input_path = write_position_file(tmp_path, data)

    result = build_analysis_result(input_path)

    assert_immediate_unavailable_for_opponent_turn(result)


def test_build_analysis_result_post_game_actual_card_is_unavailable_when_opponent_next(
    tmp_path,
) -> None:
    data = build_turn_phase_position_input(
        trick_leader="left",
        current_trick=[],
        next_player="left",
    )
    data["analysis_mode"] = "post_game_review"
    data["skat_visibility"] = "known_post_game"
    data["actual_card_played"] = "SA"
    input_path = write_position_file(tmp_path, data)

    result = build_analysis_result(input_path)
    summary = result["post_game_review_summary"]

    assert summary["is_available"] is False
    assert summary["reason"] == "immediate_analysis_unavailable"
    assert summary["actual_card_played"] == "SA"
    assert summary["recommended_card"] is None
    assert summary["candidate_count"] == 0


def test_build_analysis_result_marks_complete_game_immediate_unavailable(
    tmp_path,
) -> None:
    data = build_turn_phase_position_input(
        trick_leader="me",
        current_trick=[],
        next_player="me",
    )
    data["analysis_mode"] = "post_game_review"
    data["skat_visibility"] = "unknown"
    data["game_end_reason"] = "normal_completion"
    data["declarer_points"] = 120
    data["defender_points"] = 0
    input_path = write_position_file(tmp_path, data)

    result = build_analysis_result(input_path)

    assert result["legal_cards"] == []
    assert result["analysis_report"] == []
    assert result["recommendation"] == {
        "card": None,
        "reason": "Immediate analysis is unavailable because the game is complete.",
    }


def test_run_json_position_analysis_prints_no_local_recommendation_for_opponent_turn(
    tmp_path,
    capsys,
) -> None:
    data = build_turn_phase_position_input(
        trick_leader="left",
        current_trick=[],
        next_player="left",
    )
    input_path = write_position_file(tmp_path, data)

    run_json_position_analysis(
        file_path=input_path,
        output_path=None,
        multi_step_count=None,
    )

    captured = capsys.readouterr()

    assert "Next player: left" in captured.out
    assert "Legal cards: []" in captured.out
    assert "Recommended card: not available" in captured.out
    assert "Immediate analysis is unavailable because the local player is not next." in captured.out


def test_run_json_position_analysis_keeps_input_position_separate_from_prepared_state(
    tmp_path,
) -> None:
    data = build_turn_phase_position_input(
        trick_leader="left",
        current_trick=[],
        next_player="left",
    )
    input_path = write_position_file(tmp_path, data)
    output_path = tmp_path / "result.json"

    run_json_position_analysis(
        file_path=input_path,
        output_path=str(output_path),
        multi_step_count=1,
        card_selection_policy="highest_point",
    )

    with output_path.open("r", encoding="utf-8") as file:
        result = json.load(file)

    assert result["position"]["trick_leader"] == "left"
    assert result["position"]["current_trick"] == []
    assert result["position"]["next_player"] == "left"
    assert result["recommendation"]["card"] is None
    assert result["multi_step_result"]["steps_simulated"] == 1
    assert result["multi_step_result"]["steps"][0]["prepared_state"]["next_player"] == "me"
    assert len(
        result["multi_step_result"]["steps"][0]["prepared_state"]["current_trick"]
    ) == 2


def build_simple_nested_declaration_input(
    game_declaration: dict[str, object],
    top_level_declaration: dict[str, object] | None = None,
) -> dict[str, object]:
    data: dict[str, object] = {
        "game_type": "grand",
        "player_role": "declarer",
        "player_position": "forehand",
        "trick_leader": "me",
        "hand": ["D8"],
        "current_trick": [],
        "played_cards": [],
        "completed_tricks": [],
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "me",
        "skat": [],
        "left_hand_size": 1,
        "right_hand_size": 1,
        "sample_count": 1,
        "random_seed": 1,
        "use_basic_opponent_strategy": True,
        "game_declaration": game_declaration,
    }

    if top_level_declaration is not None:
        data.update(top_level_declaration)

    return data


def build_completed_null_defender_tricks() -> list[dict[str, object]]:
    return [
        {"cards": ["CA", "C10", "CK"], "winner_role": "defenders"},
        {"cards": ["CQ", "CJ", "C9"], "winner_role": "defenders"},
        {"cards": ["C8", "C7", "SA"], "winner_role": "defenders"},
        {"cards": ["S10", "SK", "SQ"], "winner_role": "defenders"},
        {"cards": ["SJ", "S9", "S8"], "winner_role": "defenders"},
        {"cards": ["S7", "HA", "H10"], "winner_role": "defenders"},
        {"cards": ["HK", "HQ", "HJ"], "winner_role": "defenders"},
        {"cards": ["H9", "H8", "H7"], "winner_role": "defenders"},
        {"cards": ["DA", "D10", "DK"], "winner_role": "defenders"},
        {"cards": ["DQ", "DJ", "D9"], "winner_role": "defenders"},
    ]


def build_completed_grand_tricks(winner_roles: list[str]) -> list[dict[str, object]]:
    cards_by_trick = [
        ["CA", "C10", "CK"],
        ["CQ", "CJ", "C9"],
        ["C8", "C7", "SA"],
        ["S10", "SK", "SQ"],
        ["SJ", "S9", "S8"],
        ["S7", "HA", "H10"],
        ["HK", "HQ", "HJ"],
        ["H9", "H8", "H7"],
        ["DA", "D10", "DK"],
        ["DQ", "DJ", "D9"],
    ]

    return [
        {
            "cards": cards,
            "winner_role": winner_role,
        }
        for cards, winner_role in zip(cards_by_trick, winner_roles, strict=True)
    ]


def build_completed_grand_schwarz_input(
    completed_tricks: list[dict[str, object]],
    schwarz_announced: bool = False,
) -> dict[str, object]:
    return {
        "game_type": "grand",
        "player_role": "declarer",
        "player_position": "forehand",
        "trick_leader": "me",
        "hand": ["D8", "D7"],
        "current_trick": [],
        "played_cards": [],
        "completed_tricks": completed_tricks,
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "me",
        "skat": [],
        "left_hand_size": 1,
        "right_hand_size": 1,
        "sample_count": 1,
        "random_seed": 1,
        "use_basic_opponent_strategy": True,
        "analysis_mode": "post_game_review",
        "skat_visibility": "unknown",
        "game_end_reason": "normal_completion",
        "hand_game": schwarz_announced,
        "ouvert": False,
        "schneider_announced": schwarz_announced,
        "schwarz_announced": schwarz_announced,
        "matadors": 2,
        "bid_value": 72,
        "performance_rating_system": "isko_list",
    }


def build_stub_analysis_report() -> list[dict[str, object]]:
    return [
        {
            "card": "D8",
            "win_rate": 0.0,
            "average_trick_points": 0.0,
            "average_points_won": 0.0,
            "average_points_lost": 0.0,
            "expected_point_swing": 0.0,
            "is_recommended": True,
        }
    ]


def test_build_analysis_result_uses_nested_declaration_for_game_value_and_overbid(
    tmp_path,
) -> None:
    data = build_simple_nested_declaration_input(
        {
            "hand_game": True,
            "matadors": 1,
            "bid_value": 80,
        }
    )
    input_path = write_position_file(tmp_path, data)

    result = build_analysis_result(input_path)

    assert result["game_declaration"]["hand_game"] is True
    assert result["game_declaration"]["matadors"] == 1
    assert result["game_declaration"]["bid_value"] == 80
    assert result["game_value_summary"]["game_level"] == 3
    assert result["game_value_summary"]["game_value"] == 72
    assert result["game_value_summary"]["details"]["hand_game"] is True
    assert result["game_value_summary"]["details"]["matadors"] == 1
    assert result["overbid_summary"] == {
        "bid_value": 80,
        "game_value": 72,
        "is_overbid": True,
        "margin": -8,
        "required_game_value": 96,
        "status": "overbid",
    }


def test_build_analysis_result_uses_nested_announcement_for_settlement(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "main.recommend_card_by_expected_value",
        lambda **_kwargs: ("D8", "Stubbed recommendation.", {}),
    )
    monkeypatch.setattr(
        "main.build_card_analysis_report",
        lambda **_kwargs: build_stub_analysis_report(),
    )
    data = build_completed_grand_schwarz_input(
        completed_tricks=build_completed_grand_tricks(
            [*["declarer"] * 9, "defenders"]
        ),
    )
    for field_name in [
        "hand_game",
        "ouvert",
        "schneider_announced",
        "schwarz_announced",
        "matadors",
        "bid_value",
    ]:
        data.pop(field_name, None)
    data["game_declaration"] = {
        "ouvert": False,
        "schwarz_announced": True,
        "matadors": 2,
        "bid_value": 72,
    }
    input_path = write_position_file(tmp_path, data)

    result = build_analysis_result(input_path)

    assert result["game_declaration"]["schwarz_announced"] is True
    assert result["game_value_summary"]["details"]["schwarz_announced"] is True
    assert result["game_declaration"]["hand_game"] is True
    assert result["game_declaration"]["schneider_announced"] is True
    assert result["game_value_summary"]["game_value"] == 144
    assert result["final_settlement_summary"]["is_loss"] is True
    assert result["final_settlement_summary"]["settlement_score"] == -336


def test_build_analysis_result_serializes_top_level_declaration_overrides(
    tmp_path,
) -> None:
    data = build_simple_nested_declaration_input(
        {
            "hand_game": True,
            "ouvert": True,
            "schneider_announced": True,
            "schwarz_announced": True,
            "matadors": 3,
            "bid_value": 48,
        },
        {
            "hand_game": False,
            "ouvert": False,
            "schneider_announced": False,
            "schwarz_announced": False,
            "matadors": 1,
            "bid_value": 72,
        },
    )
    input_path = write_position_file(tmp_path, data)

    result = build_analysis_result(input_path)

    assert result["game_declaration"] == {
        "game_type": "grand",
        "hand_game": False,
        "ouvert": False,
        "schneider_announced": False,
        "schwarz_announced": False,
        "matadors": 1,
        "bid_value": 72,
    }
    assert result["game_value_summary"]["game_value"] == 48
    assert result["overbid_summary"]["bid_value"] == 72


def build_post_game_position_input() -> dict[str, object]:
    return {
        "game_type": "spades",
        "player_role": "declarer",
        "player_position": "middlehand",
        "trick_leader": "right",
        "hand": ["C7", "SA", "S7"],
        "current_trick": ["CA"],
        "played_cards": [],
        "completed_tricks": [],
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "me",
        "skat": [],
        "left_hand_size": 10,
        "right_hand_size": 10,
        "sample_count": 10,
        "random_seed": 1,
        "use_basic_opponent_strategy": True,
        "analysis_mode": "post_game_review",
        "skat_visibility": "known_post_game",
    }


def test_build_analysis_result_includes_unavailable_post_game_review_summary(
    tmp_path,
) -> None:
    data = build_post_game_position_input()
    input_path = write_position_file(tmp_path, data)

    result = build_analysis_result(input_path)

    assert "post_game_review_summary" in result
    assert result["post_game_review_summary"]["is_available"] is False
    assert (
        result["post_game_review_summary"]["reason"]
        == "actual_card_played_not_provided"
    )
    assert result["post_game_review_summary"]["actual_card_played"] is None
    assert (
        result["post_game_review_summary"]["decision_quality"]
        == "not_available"
    )


def test_build_analysis_result_uses_completed_null_ownership(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "main.recommend_card_by_expected_value",
        lambda **_kwargs: ("D8", "Stubbed recommendation.", {}),
    )
    monkeypatch.setattr(
        "main.build_card_analysis_report",
        lambda **_kwargs: build_stub_analysis_report(),
    )
    data = {
        "game_type": "null",
        "player_role": "declarer",
        "player_position": "forehand",
        "trick_leader": "me",
        "hand": ["D8", "D7"],
        "current_trick": [],
        "played_cards": [],
        "completed_tricks": build_completed_null_defender_tricks(),
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "me",
        "skat": [],
        "left_hand_size": 1,
        "right_hand_size": 1,
        "sample_count": 1,
        "random_seed": 1,
        "use_basic_opponent_strategy": True,
        "analysis_mode": "post_game_review",
        "skat_visibility": "unknown",
        "game_end_reason": "normal_completion",
        "hand_game": False,
        "ouvert": False,
        "bid_value": 23,
        "performance_rating_system": "isko_list",
    }
    input_path = write_position_file(tmp_path, data)

    result = build_analysis_result(input_path)

    assert result["score_summary"]["total_declarer_points"] == 0
    assert result["score_summary"]["total_defender_points"] == 120

    assert result["game_result_summary"]["is_complete"] is True
    assert result["game_result_summary"]["winner"] == "declarer"
    assert result["adjusted_game_result_summary"]["is_complete"] is True
    assert result["adjusted_game_result_summary"]["winner"] == "declarer"
    assert result["adjusted_game_result_summary"]["game_end_reason"] == (
        "normal_completion"
    )

    assert result["final_settlement_summary"]["is_complete"] is True
    assert result["final_settlement_summary"]["winner"] == "declarer"
    assert result["final_settlement_summary"]["declarer_won_by_card_points"] is True
    assert result["final_settlement_summary"]["game_value"] == 23
    assert result["final_settlement_summary"]["effective_game_value"] == 23
    assert result["final_settlement_summary"]["settlement_score"] == 23
    assert result["final_settlement_summary"]["is_loss"] is False

    assert result["performance_rating_summary"]["game_outcome"] == "declarer_win"
    assert result["performance_rating_summary"]["settlement_score"] == 23
    assert result["performance_rating_summary"]["rating_score"] == 73


def test_build_analysis_result_uses_completed_trick_schwarz_settlement(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "main.recommend_card_by_expected_value",
        lambda **_kwargs: ("D8", "Stubbed recommendation.", {}),
    )
    monkeypatch.setattr(
        "main.build_card_analysis_report",
        lambda **_kwargs: build_stub_analysis_report(),
    )
    declarer_schwarz_input = build_completed_grand_schwarz_input(
        completed_tricks=build_completed_grand_tricks(["declarer"] * 10),
    )
    declarer_schwarz_path = write_position_file(tmp_path, declarer_schwarz_input)

    declarer_schwarz_result = build_analysis_result(declarer_schwarz_path)

    assert declarer_schwarz_result["game_result_summary"]["winner"] == "declarer"
    assert declarer_schwarz_result["final_settlement_summary"]["game_value"] == 72
    assert declarer_schwarz_result["final_settlement_summary"]["effective_game_value"] == 120
    assert declarer_schwarz_result["final_settlement_summary"]["settlement_score"] == 120
    assert declarer_schwarz_result["final_settlement_summary"]["is_loss"] is False
    assert declarer_schwarz_result["performance_rating_summary"]["game_outcome"] == (
        "declarer_win"
    )
    assert declarer_schwarz_result["performance_rating_summary"]["settlement_score"] == 120

    failed_announcement_input = build_completed_grand_schwarz_input(
        completed_tricks=build_completed_grand_tricks(
            [*["declarer"] * 9, "defenders"]
        ),
        schwarz_announced=True,
    )
    failed_announcement_path = write_position_file(tmp_path, failed_announcement_input)

    failed_announcement_result = build_analysis_result(failed_announcement_path)

    assert failed_announcement_result["game_result_summary"]["winner"] == "declarer"
    assert failed_announcement_result["game_value_summary"]["game_value"] == 144
    assert failed_announcement_result["final_settlement_summary"]["is_loss"] is True
    assert failed_announcement_result["final_settlement_summary"]["settlement_score"] == -336
    assert failed_announcement_result["performance_rating_summary"]["game_outcome"] == (
        "declarer_loss"
    )
    assert failed_announcement_result["performance_rating_summary"]["settlement_score"] == (
        -336
    )


def test_build_analysis_result_includes_available_post_game_review_summary(
    tmp_path,
) -> None:
    data = build_post_game_position_input()
    data["actual_card_played"] = "C7"
    input_path = write_position_file(tmp_path, data)

    result = build_analysis_result(input_path)
    summary = result["post_game_review_summary"]

    assert summary["is_available"] is True
    assert summary["reason"] == "actual_card_played_provided"
    assert summary["actual_card_played"] == "C7"
    assert summary["recommended_card"] is not None
    assert isinstance(summary["actual_expected_point_swing"], float)
    assert isinstance(summary["recommended_expected_point_swing"], float)
    assert isinstance(summary["expected_point_swing_difference"], float)
    assert summary["decision_quality"] in {
        "optimal",
        "acceptable",
        "suboptimal",
        "mistake",
    }


def test_build_analysis_result_uses_null_objective_for_recommendation_and_review(
    tmp_path,
) -> None:
    data = {
        "game_type": "null",
        "player_role": "declarer",
        "declarer_player": "me",
        "player_position": "rearhand",
        "trick_leader": "left",
        "hand": ["CA", "C7"],
        "current_trick": ["C10", "C9"],
        "played_cards": [],
        "completed_tricks": [],
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "me",
        "skat": [],
        "left_hand_size": 1,
        "right_hand_size": 1,
        "sample_count": 1,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
        "analysis_mode": "post_game_review",
        "skat_visibility": "unknown",
        "actual_card_played": "CA",
    }
    input_path = write_position_file(tmp_path, data)

    result = build_analysis_result(input_path)
    summary = result["post_game_review_summary"]

    assert result["recommendation"]["card"] == "C7"
    assert [row["card"] for row in result["analysis_report"]] == ["C7", "CA"]
    assert result["analysis_report"][0]["is_recommended"] is True
    assert result["analysis_report"][0]["expected_point_swing"] == -10.0
    assert result["analysis_report"][1]["expected_point_swing"] == 21.0
    assert summary["actual_card_played"] == "CA"
    assert summary["recommended_card"] == "C7"
    assert summary["expected_point_swing_difference"] == -31.0
    assert summary["decision_quality"] == "mistake"
    assert summary["decision_factors"] == [
        "lower_null_objective_than_recommendation",
        "large_null_objective_gap",
    ]
    assert "Null contract objective" in summary["decision_explanation"]


def test_run_json_position_analysis_prints_available_post_game_review_summary(
    capsys,
) -> None:
    run_json_position_analysis(
        file_path="examples/spades_post_game_actual_card_played.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
        output_path=None,
        multi_step_count=None,
        card_selection_policy="highest_expected_value",
        expected_value_sample_count=20,
        strict_context=False,
        compare_policies=False,
        comparison_only=False,
    )

    captured = capsys.readouterr()

    assert "Post-game review summary" in captured.out
    assert "Actual card played: C7" in captured.out
    assert "Recommended card: C7" in captured.out
    assert "Actual expected point swing:" in captured.out
    assert "Recommended expected point swing:" in captured.out
    assert "Missed expected point swing: 0.00" in captured.out
    assert "Decision quality: optimal" in captured.out
    assert "Decision factors: no_missed_expected_point_swing" in captured.out
    assert (
        "Decision explanation: The actual card matches the recommended card "
        "or has no missed expected point swing."
    ) in captured.out
    assert (
        "Review ranks: actual 1 of 1; recommended 1 of 1; better alternatives 0."
    ) in captured.out
    assert "Actual card is best-ranked by the review objective." in captured.out


def test_run_json_position_analysis_prints_unavailable_post_game_review_summary(
    capsys,
) -> None:
    run_json_position_analysis(
        file_path="examples/grand_leading.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
        output_path=None,
        multi_step_count=None,
        card_selection_policy="highest_expected_value",
        expected_value_sample_count=20,
        strict_context=False,
        compare_policies=False,
        comparison_only=False,
    )

    captured = capsys.readouterr()

    assert "Post-game review summary" in captured.out
    assert "Review status: not available" in captured.out
    assert "Actual card played: not available" in captured.out
    assert "Recommended card:" in captured.out
    assert "Unavailable reason: the actual card was not provided." in captured.out
    assert "Reason code: actual_card_played_not_provided" in captured.out
    assert "Decision factors: actual_card_played_not_provided" in captured.out
    assert (
        "Decision explanation: No post-game review decision quality is available "
        "because actual_card_played was not provided."
    ) in captured.out
    assert "Review ranks: actual not available; recommended" in captured.out
    assert "better alternatives not available." in captured.out
    assert "Better alternatives: not available." in captured.out


def test_run_json_position_analysis_prints_null_objective_aware_review_wording(
    tmp_path,
    capsys,
) -> None:
    data = {
        "game_type": "null",
        "player_role": "declarer",
        "declarer_player": "me",
        "player_position": "rearhand",
        "trick_leader": "left",
        "hand": ["CA", "C7"],
        "current_trick": ["C10", "C9"],
        "played_cards": [],
        "completed_tricks": [],
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "me",
        "skat": [],
        "left_hand_size": 1,
        "right_hand_size": 1,
        "sample_count": 1,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
        "analysis_mode": "post_game_review",
        "skat_visibility": "unknown",
        "actual_card_played": "CA",
    }
    input_path = write_position_file(tmp_path, data)

    run_json_position_analysis(
        file_path=input_path,
        sample_count_override=1,
        random_seed_override=42,
        opponent_strategy_override="basic",
        output_path=None,
        multi_step_count=None,
        card_selection_policy="highest_expected_value",
        expected_value_sample_count=1,
        strict_context=False,
        compare_policies=False,
        comparison_only=False,
    )

    captured = capsys.readouterr()

    assert "Post-game review summary" in captured.out
    assert "Actual card played: CA" in captured.out
    assert "Recommended card: C7" in captured.out
    assert "Objective basis: Null contract objective, not raw card points." in captured.out
    assert "Actual card-point swing (informational): 21.00" in captured.out
    assert "Recommended card-point swing (informational): -10.00" in captured.out
    assert "Missed Null objective gap: 23.00" in captured.out
    assert "Decision quality: mistake" in captured.out
    assert "Null contract objective" in captured.out
    assert (
        "Review ranks: actual 2 of 2; recommended 1 of 2; better alternatives 1."
    ) in captured.out
    assert "Actual card has 1 better alternative by the review objective." in captured.out
    assert "Expected point swing difference:" not in captured.out


def test_build_analysis_result_infers_missing_matadors_from_known_declarer_cards(
    tmp_path,
) -> None:
    data = {
        "game_type": "grand",
        "player_role": "declarer",
        "player_position": "middlehand",
        "trick_leader": "me",
        "hand": ["CJ", "SJ", "HJ", "D7"],
        "current_trick": [],
        "played_cards": [],
        "completed_tricks": [],
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "me",
        "skat": ["C7", "D8"],
        "left_hand_size": 10,
        "right_hand_size": 10,
        "sample_count": 10,
        "random_seed": 1,
        "use_basic_opponent_strategy": True,
        "analysis_mode": "post_game_review",
        "skat_visibility": "known_post_game",
        "game_declaration": {
            "hand_game": False,
            "ouvert": False,
            "schneider_announced": False,
            "schwarz_announced": False
        },
    }
    input_path = write_position_file(tmp_path, data)

    result = build_analysis_result(input_path)

    assert result["game_declaration"]["matadors"] == 3
    assert result["game_value_summary"]["details"]["matadors"] == 3
    assert result["game_value_summary"]["game_level"] == 4
    assert result["game_value_summary"]["game_value"] == 96


def test_build_analysis_result_uses_completed_trick_ownership_for_matadors(
    tmp_path,
) -> None:
    data = {
        "game_type": "grand",
        "player_role": "declarer",
        "player_position": "middlehand",
        "trick_leader": "me",
        "hand": ["CJ", "D7", "D8", "D9"],
        "current_trick": [],
        "played_cards": [],
        "completed_tricks": [
            {
                "cards": ["SJ", "H7", "HJ"],
                "players": ["me", "left", "right"],
                "winner_role": "declarer",
                "winner_player": "me",
            }
        ],
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "me",
        "skat": ["C7", "C8"],
        "left_hand_size": 9,
        "right_hand_size": 9,
        "sample_count": 10,
        "random_seed": 1,
        "use_basic_opponent_strategy": True,
        "analysis_mode": "post_game_review",
        "skat_visibility": "known_post_game",
        "game_declaration": {
            "hand_game": False,
            "ouvert": False,
            "schneider_announced": False,
            "schwarz_announced": False,
        },
    }
    input_path = write_position_file(tmp_path, data)

    result = build_analysis_result(input_path)

    assert result["game_declaration"]["matadors"] == 2
    assert result["game_value_summary"]["details"]["matadors"] == 2
    assert result["game_value_summary"]["details"]["matador_multiplier"] == 3
    assert result["game_value_summary"]["game_level"] == 3
    assert result["game_value_summary"]["game_value"] == 72
    assert result["game_value_summary"]["details"]["is_complete"] is True


def test_build_analysis_result_keeps_explicit_matadors_over_inference(
    tmp_path,
) -> None:
    data = {
        "game_type": "grand",
        "player_role": "declarer",
        "player_position": "middlehand",
        "trick_leader": "me",
        "hand": ["CJ", "SJ", "HJ", "D7"],
        "current_trick": [],
        "played_cards": [],
        "completed_tricks": [],
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "me",
        "skat": ["C7", "D8"],
        "left_hand_size": 10,
        "right_hand_size": 10,
        "sample_count": 10,
        "random_seed": 1,
        "use_basic_opponent_strategy": True,
        "analysis_mode": "post_game_review",
        "skat_visibility": "known_post_game",
        "game_declaration": {
            "hand_game": False,
            "ouvert": False,
            "schneider_announced": False,
            "schwarz_announced": False,
            "matadors": 1
        },
    }
    input_path = write_position_file(tmp_path, data)

    result = build_analysis_result(input_path)

    assert result["game_declaration"]["matadors"] == 1
    assert result["game_value_summary"]["details"]["matadors"] == 1
    assert result["game_value_summary"]["game_level"] == 2
    assert result["game_value_summary"]["game_value"] == 48


def test_build_analysis_result_uses_inferred_matadors_for_final_settlement(
    tmp_path,
) -> None:
    data = {
        "game_type": "grand",
        "player_role": "declarer",
        "player_position": "middlehand",
        "trick_leader": "me",
        "hand": ["CJ", "SJ", "HJ", "D7"],
        "current_trick": [],
        "played_cards": [],
        "completed_tricks": [
            {
                "cards": ["CA", "C10", "CK"],
                "winner_role": "declarer",
            },
            {
                "cards": ["SA", "S10", "SK"],
                "winner_role": "declarer",
            },
            {
                "cards": ["HA", "H10", "HK"],
                "winner_role": "defenders",
            },
            {
                "cards": ["DA", "D10", "DK"],
                "winner_role": "defenders",
            },
        ],
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "me",
        "skat": ["C7", "D8"],
        "left_hand_size": 6,
        "right_hand_size": 6,
        "sample_count": 10,
        "random_seed": 1,
        "use_basic_opponent_strategy": True,
        "analysis_mode": "post_game_review",
        "skat_visibility": "known_post_game",
        "game_end_reason": "defenders_conceded_remaining_tricks",
        "game_declaration": {
            "hand_game": False,
            "ouvert": False,
            "schneider_announced": False,
            "schwarz_announced": False,
        },
    }
    input_path = write_position_file(tmp_path, data)

    result = build_analysis_result(input_path)

    assert result["game_declaration"]["matadors"] == 3
    assert result["game_value_summary"]["details"]["matadors"] == 3
    assert result["game_value_summary"]["game_level"] == 4
    assert result["game_value_summary"]["game_value"] == 96

    assert result["adjusted_game_result_summary"]["is_complete"] is True
    assert result["adjusted_game_result_summary"]["winner"] == "declarer"

    assert result["final_settlement_summary"]["is_complete"] is True
    assert result["final_settlement_summary"]["winner"] == "declarer"
    assert result["final_settlement_summary"]["game_value"] == 96
    assert result["final_settlement_summary"]["settlement_score"] == 96


def test_cli_applies_two_external_profiles_and_prints_concise_side_lines(
    tmp_path,
) -> None:
    output_path = tmp_path / "external-profiles.json"
    completed_process = run_cli(
        "--input",
        VALID_INPUT_PATH,
        "--opponent-statistics-file",
        OPPONENT_STATISTICS_INPUT_PATH,
        "--left-opponent-player-id",
        "opponent-123",
        "--right-opponent-player-id",
        "opponent-789",
        "--use-profile-presets",
        "--samples",
        "5",
        "--seed",
        "42",
        "--output",
        output_path,
    )

    assert completed_process.returncode == 0
    assert completed_process.stderr == ""
    assert (
        "Left opponent opponent-123: cautious_defender, medium confidence, "
        "applied cautious_defender."
    ) in completed_process.stdout
    assert (
        "Right opponent opponent-789: aggressive, medium confidence, "
        "applied aggressive_points."
    ) in completed_process.stdout
    with output_path.open("r", encoding="utf-8") as output_file:
        result = json.load(output_file)
    summary = result["opponent_profile_application_summary"]
    assert summary["left"]["effective_lead_policy"] == (
        result["left_opponent_policy_settings"]["opponent_lead_policy"]
    )
    assert summary["left"]["effective_response_policy"] == (
        result["left_opponent_policy_settings"]["opponent_response_policy"]
    )
    assert summary["right"]["effective_lead_policy"] == (
        result["right_opponent_policy_settings"]["opponent_lead_policy"]
    )
    assert summary["right"]["effective_response_policy"] == (
        result["right_opponent_policy_settings"]["opponent_response_policy"]
    )
    assert "statistics" not in summary["left"]["external_profile"]
    assert summary["right"]["external_profile"]["notes"] == (
        "Percentages were copied from the public profile."
    )


def test_cli_external_profile_quiet_output_is_silent_and_preserves_side_isolation(
    tmp_path,
) -> None:
    output_path = tmp_path / "quiet-external-profiles.json"
    repeated_output_path = tmp_path / "quiet-external-profiles-repeated.json"
    args = (
        "--input",
        VALID_INPUT_PATH,
        "--opponent-statistics-file",
        OPPONENT_STATISTICS_INPUT_PATH,
        "--left-opponent-player-id",
        "opponent-123",
        "--right-opponent-player-id",
        "opponent-789",
        "--use-profile-presets",
        "--samples",
        "5",
        "--seed",
        "42",
        "--output",
    )
    completed_process = run_cli(
        *args,
        output_path,
        "--quiet",
    )
    repeated_process = run_cli(
        *args,
        repeated_output_path,
        "--quiet",
    )

    assert completed_process.returncode == 0
    assert repeated_process.returncode == 0
    assert completed_process.stdout == ""
    assert repeated_process.stdout == ""
    assert completed_process.stderr == ""
    with output_path.open("r", encoding="utf-8") as output_file:
        result = json.load(output_file)
    with repeated_output_path.open("r", encoding="utf-8") as output_file:
        repeated_result = json.load(output_file)
    assert repeated_result == result
    assert result["left_opponent_policy_settings"] == {
        "opponent_lead_policy": "basic_defender_lead",
        "opponent_response_policy": "basic_defender_response",
    }
    assert result["right_opponent_policy_settings"] == {
        "opponent_lead_policy": "highest_point",
        "opponent_response_policy": "highest_point",
    }


def test_external_profiles_match_equivalent_manual_immediate_and_multi_step_paths(
    tmp_path,
) -> None:
    statistics_input = main_module.load_opponent_statistics_from_json(
        str(OPPONENT_STATISTICS_INPUT_PATH)
    )
    statistics_summary = main_module.build_opponent_statistics_summary(statistics_input)
    with VALID_INPUT_PATH.open("r", encoding="utf-8") as file:
        manual_data = json.load(file)
    manual_data["analysis_mode"] = "live_decision"
    manual_data["use_profile_presets"] = True
    manual_data["left_player_profile"] = {
        key: value
        for key, value in statistics_summary["records"][0][
            "normalized_profile_statistics"
        ].items()
        if value is not None
    }
    manual_data["right_player_profile"] = {
        key: value
        for key, value in statistics_summary["records"][1][
            "normalized_profile_statistics"
        ].items()
        if value is not None
    }
    manual_path = tmp_path / "manual-profiles.json"
    manual_path.write_text(json.dumps(manual_data), encoding="utf-8")
    manual_output = tmp_path / "manual-output.json"
    external_output = tmp_path / "external-output.json"
    common_args = (
        "--samples",
        "5",
        "--seed",
        "42",
        "--multi-step",
        "1",
        "--compare-policies",
        "--expected-value-samples",
        "5",
        "--output",
    )

    manual_process = run_cli(
        "--input", manual_path, *common_args, manual_output, "--quiet"
    )
    external_process = run_cli(
        "--input",
        VALID_INPUT_PATH,
        *common_args,
        external_output,
        "--opponent-statistics-file",
        OPPONENT_STATISTICS_INPUT_PATH,
        "--left-opponent-player-id",
        "opponent-123",
        "--right-opponent-player-id",
        "opponent-789",
        "--use-profile-presets",
        "--quiet",
    )

    assert manual_process.returncode == 0
    assert external_process.returncode == 0
    with manual_output.open("r", encoding="utf-8") as file:
        manual_result = json.load(file)
    with external_output.open("r", encoding="utf-8") as file:
        external_result = json.load(file)
    for field_name in (
        "legal_cards",
        "analysis_report",
        "recommendation",
        "left_opponent_policy_settings",
        "right_opponent_policy_settings",
        "multi_step_result",
        "policy_comparison_result",
    ):
        assert external_result[field_name] == manual_result[field_name]


@pytest.mark.parametrize("derivation_kind", ["low_confidence", "neutral"])
def test_non_actionable_external_profiles_do_not_change_live_analysis(
    tmp_path,
    derivation_kind: str,
) -> None:
    with OPPONENT_STATISTICS_INPUT_PATH.open("r", encoding="utf-8") as file:
        statistics_data = json.load(file)
    record = statistics_data["opponent_statistics_input"]["records"][1]
    if derivation_kind == "low_confidence":
        record["games_played"] = 20
        expected_reason = "insufficient_confidence"
    else:
        record["statistics"].update(
            solo_games_played_percent=30,
            solo_hand_percent=0,
            suit_games_percent=100,
            grand_games_percent=0,
            null_games_percent=0,
            defender_games_played_percent=70,
            defender_games_won_percent=50,
        )
        expected_reason = "neutral_profile"
    statistics_path = tmp_path / f"{derivation_kind}.json"
    statistics_path.write_text(json.dumps(statistics_data), encoding="utf-8")
    baseline_output = tmp_path / f"{derivation_kind}-baseline.json"
    external_output = tmp_path / f"{derivation_kind}-external.json"
    baseline_process = run_cli(
        "--input",
        VALID_INPUT_PATH,
        "--use-profile-presets",
        "--samples",
        "5",
        "--seed",
        "42",
        "--multi-step",
        "1",
        "--expected-value-samples",
        "5",
        "--output",
        baseline_output,
        "--quiet",
    )
    external_process = run_cli(
        "--input",
        VALID_INPUT_PATH,
        "--opponent-statistics-file",
        statistics_path,
        "--right-opponent-player-id",
        "opponent-789",
        "--use-profile-presets",
        "--samples",
        "5",
        "--seed",
        "42",
        "--multi-step",
        "1",
        "--expected-value-samples",
        "5",
        "--output",
        external_output,
        "--quiet",
    )

    assert baseline_process.returncode == 0
    assert external_process.returncode == 0
    with baseline_output.open("r", encoding="utf-8") as file:
        baseline_result = json.load(file)
    with external_output.open("r", encoding="utf-8") as file:
        external_result = json.load(file)
    assert external_result["analysis_report"] == baseline_result["analysis_report"]
    assert external_result["recommendation"] == baseline_result["recommendation"]
    assert external_result["legal_cards"] == baseline_result["legal_cards"]
    assert external_result["multi_step_result"] == baseline_result["multi_step_result"]
    side = external_result["opponent_profile_application_summary"]["right"]
    assert side["application_status"] == "not_actionable"
    assert side["not_applied_reason"] == expected_reason
    assert side["applied_policy_preset"] is None


@pytest.mark.parametrize("manual_side", ["left", "right"])
def test_manual_profile_precedes_bound_external_profile_on_one_side(
    tmp_path,
    manual_side: str,
) -> None:
    with VALID_INPUT_PATH.open("r", encoding="utf-8") as file:
        position_data = json.load(file)
    position_data[f"{manual_side}_player_profile"] = (
        {
            "games_played": 600,
            "solo_rate": 0.42,
            "grand_rate": 0.34,
        }
        if manual_side == "left"
        else {
            "games_played": 600,
            "solo_rate": 0.2,
            "defender_rate": 0.8,
            "grand_rate": 0.1,
            "hand_game_rate": 0.03,
            "defender_win_rate": 0.56,
        }
    )
    position_path = tmp_path / f"manual-{manual_side}.json"
    position_path.write_text(json.dumps(position_data), encoding="utf-8")
    output_path = tmp_path / "manual-precedence.json"
    completed_process = run_cli(
        "--input",
        position_path,
        "--opponent-statistics-file",
        OPPONENT_STATISTICS_INPUT_PATH,
        "--left-opponent-player-id",
        "opponent-123",
        "--right-opponent-player-id",
        "opponent-789",
        "--use-profile-presets",
        "--samples",
        "2",
        "--output",
        output_path,
        "--quiet",
    )

    assert completed_process.returncode == 0
    with output_path.open("r", encoding="utf-8") as output_file:
        result = json.load(output_file)
    summary = result["opponent_profile_application_summary"]
    external_side = "right" if manual_side == "left" else "left"
    assert summary[manual_side]["binding_status"] == "matched"
    assert summary[manual_side]["effective_profile_source"] == "manual_profile"
    assert summary[manual_side]["application_status"] == "manual_profile_precedence"
    assert summary[external_side]["effective_profile_source"] == "external_statistics"
    assert summary[external_side]["application_status"] == "applied"
    expected_manual_policy = (
        {
            "opponent_lead_policy": "highest_point",
            "opponent_response_policy": "highest_point",
        }
        if manual_side == "left"
        else {
            "opponent_lead_policy": "basic_defender_lead",
            "opponent_response_policy": "basic_defender_response",
        }
    )
    assert result[f"{manual_side}_opponent_policy_settings"] == expected_manual_policy


def test_explicit_input_and_cli_policies_retain_existing_external_profile_precedence(
    tmp_path,
) -> None:
    with VALID_INPUT_PATH.open("r", encoding="utf-8") as file:
        position_data = json.load(file)
    position_data.update(
        use_profile_presets=True,
        left_opponent_lead_policy="lowest_point",
        left_opponent_response_policy="lowest_point",
    )
    position_path = tmp_path / "explicit-input.json"
    position_path.write_text(json.dumps(position_data), encoding="utf-8")
    input_output = tmp_path / "explicit-input-output.json"
    cli_output = tmp_path / "explicit-cli-output.json"
    input_process = run_cli(
        "--input",
        position_path,
        "--opponent-statistics-file",
        OPPONENT_STATISTICS_INPUT_PATH,
        "--left-opponent-player-id",
        "opponent-123",
        "--samples",
        "2",
        "--output",
        input_output,
        "--quiet",
    )
    cli_process = run_cli(
        "--input",
        VALID_INPUT_PATH,
        "--opponent-statistics-file",
        OPPONENT_STATISTICS_INPUT_PATH,
        "--left-opponent-player-id",
        "opponent-123",
        "--use-profile-presets",
        "--opponent-response-policy",
        "lowest_point",
        "--samples",
        "2",
        "--output",
        cli_output,
        "--quiet",
    )

    assert input_process.returncode == 0
    assert cli_process.returncode == 0
    with input_output.open("r", encoding="utf-8") as file:
        input_result = json.load(file)
    with cli_output.open("r", encoding="utf-8") as file:
        cli_result = json.load(file)
    assert input_result["opponent_profile_application_summary"]["left"][
        "application_status"
    ] == "explicit_policy_precedence"
    assert cli_result["opponent_profile_application_summary"]["left"][
        "application_status"
    ] == "explicit_policy_precedence"
    assert input_result["left_opponent_policy_settings"] == {
        "opponent_lead_policy": "lowest_point",
        "opponent_response_policy": "lowest_point",
    }
    assert cli_result["left_opponent_policy_settings"] == {
        "opponent_lead_policy": "basic_defender_lead",
        "opponent_response_policy": "lowest_point",
    }


def test_no_external_file_preserves_output_without_application_summary() -> None:
    result = build_analysis_result(
        file_path=str(VALID_INPUT_PATH),
        sample_count_override=2,
        random_seed_override=42,
    )

    assert "opponent_profile_application_summary" not in result


@pytest.mark.parametrize(
    ("args", "expected_error", "expected_returncode"),
    [
        (
            ("--opponent-statistics-file", OPPONENT_STATISTICS_INPUT_PATH),
            "requires --left-opponent-player-id",
            2,
        ),
        (
            ("--left-opponent-player-id", "opponent-123"),
            "require --opponent-statistics-file",
            2,
        ),
        (
            (
                "--opponent-statistics-file",
                OPPONENT_STATISTICS_INPUT_PATH,
                "--left-opponent-player-id",
                " opponent-123",
                "--use-profile-presets",
            ),
            "non-empty, non-padded",
            2,
        ),
        (
            (
                "--opponent-statistics-file",
                OPPONENT_STATISTICS_INPUT_PATH,
                "--left-opponent-player-id",
                "opponent-123",
                "--right-opponent-player-id",
                "opponent-123",
                "--use-profile-presets",
            ),
            "must be different",
            2,
        ),
        (
            (
                "--opponent-statistics-file",
                OPPONENT_STATISTICS_INPUT_PATH,
                "--left-opponent-player-id",
                "Opponent-123",
                "--use-profile-presets",
            ),
            "must match exactly one",
            1,
        ),
        (
            (
                "--opponent-statistics-file",
                OPPONENT_STATISTICS_INPUT_PATH,
                "--left-opponent-player-id",
                "opponent-123",
            ),
            "requires effective --use-profile-presets",
            2,
        ),
    ],
)
def test_cli_rejects_invalid_external_profile_option_combinations(
    args: tuple[object, ...],
    expected_error: str,
    expected_returncode: int,
) -> None:
    completed_process = run_cli("--input", VALID_INPUT_PATH, *args)

    assert completed_process.returncode == expected_returncode
    assert expected_error in completed_process.stderr
    assert_no_success_output(completed_process)


def test_cli_rejects_missing_wrong_workflow_and_invalid_statistics_companion(
    tmp_path,
) -> None:
    missing_process = run_cli(
        "--input",
        VALID_INPUT_PATH,
        "--opponent-statistics-file",
        tmp_path / "missing.json",
        "--left-opponent-player-id",
        "opponent-123",
        "--use-profile-presets",
    )
    wrong_workflow_process = run_cli(
        "--input",
        VALID_INPUT_PATH,
        "--opponent-statistics-file",
        VALID_INPUT_PATH,
        "--left-opponent-player-id",
        "opponent-123",
        "--use-profile-presets",
    )
    with OPPONENT_STATISTICS_INPUT_PATH.open("r", encoding="utf-8") as file:
        invalid_data = json.load(file)
    invalid_data["opponent_statistics_input"]["records"][0]["source"][
        "source_type"
    ] = "website"
    invalid_path = tmp_path / "invalid-statistics.json"
    invalid_path.write_text(json.dumps(invalid_data), encoding="utf-8")
    invalid_process = run_cli(
        "--input",
        VALID_INPUT_PATH,
        "--opponent-statistics-file",
        invalid_path,
        "--left-opponent-player-id",
        "opponent-123",
        "--use-profile-presets",
    )

    assert missing_process.returncode == 1
    assert "Input file not found" in missing_process.stderr
    assert wrong_workflow_process.returncode == 1
    assert "does not contain opponent_statistics_input" in wrong_workflow_process.stderr
    assert invalid_process.returncode == 1
    assert "source_type" in invalid_process.stderr


@pytest.mark.parametrize(
    "input_path",
    [
        HISTORICAL_INPUT_PATH,
        TRAINING_DATASET_INPUT_PATH,
        OPPONENT_STATISTICS_INPUT_PATH,
        PROJECT_ROOT / "examples" / "grand_second_position_with_metadata.json",
        PROJECT_ROOT / "examples" / "grand_list_performance_input.json",
        PROJECT_ROOT / "examples" / "grand_list_game_contributions.json",
        PROJECT_ROOT / "examples" / "grand_list_analysis_results.json",
        PROJECT_ROOT / "examples" / "grand_list_standings_input.json",
        IMPOSSIBLE_NULL_INPUT_PATH,
    ],
)
def test_cli_rejects_external_profiles_for_every_non_live_workflow(
    input_path: Path,
) -> None:
    completed_process = run_cli(
        "--input",
        input_path,
        "--opponent-statistics-file",
        OPPONENT_STATISTICS_INPUT_PATH,
        "--left-opponent-player-id",
        "opponent-123",
        "--use-profile-presets",
    )

    assert completed_process.returncode == 2
    assert "opponent-statistics-file" in completed_process.stderr
    assert_no_success_output(completed_process)
