import inspect
import json
import subprocess
import sys
from pathlib import Path

import pytest

import main as legacy_main
from skat_ai.api.v1 import ExecutionOptionsV1, execute_document
from skat_ai.application import (
    ApplicationExecutionOptions,
    HistoricalGameApplicationOptions,
    PositionAnalysisApplicationOptions,
    TrainingDatasetApplicationOptions,
    build_application_invocation,
    execute_application_invocation,
)
from skat_ai.cli import execution as cli

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = PROJECT_ROOT / "examples"

WORKFLOW_CASES = (
    (
        "grand_second_position.json",
        ("--samples", "1", "--seed", "42"),
        {"sample_count_override": 1, "random_seed_override": 42},
        "position_analysis",
    ),
    (
        "historical_grand_normal_completion.json",
        (),
        {},
        "historical_game",
    ),
    (
        "training_dataset_normal_play.json",
        (),
        {},
        "training_dataset",
    ),
    (
        "training_dataset_preparation_unavailable.json",
        (),
        {},
        "training_dataset_preparation",
    ),
    (
        "opponent_statistics.json",
        (),
        {},
        "opponent_statistics",
    ),
    (
        "fixed_three_player_historical_list_mixed.json",
        (),
        {},
        "fixed_three_player_historical_list",
    ),
    (
        "fixed_three_player_historical_list_comparison.json",
        (),
        {},
        "fixed_three_player_historical_list_comparison",
    ),
)

EXPECTED_OPTION_STRINGS = (
    ("-h", "--help"),
    ("--version",),
    ("--input",),
    ("--samples",),
    ("--seed",),
    ("--opponent-strategy",),
    ("--output",),
    ("--quiet",),
    ("--include-provenance",),
    ("--audit-dataset-partitions",),
    ("--dataset-partition-mode",),
    ("--aggregate-opponent-statistics",),
    ("--opponent-statistics-partition",),
    ("--opponent-statistics-before",),
    ("--export-opponent-statistics",),
    ("--evaluate-opponent-policy-profiles", "--evaluate-rolling-opponent-policies"),
    ("--profile-source-partition",),
    ("--profile-evaluation-partition",),
    ("--historical-decision-snapshots",),
    ("--historical-game-review",),
    ("--historical-search-review",),
    ("--historical-replay-coaching",),
    ("--search-seed",),
    ("--search-budget-profile",),
    ("--evaluate-bounded-search",),
    ("--search-evaluation-partition",),
    ("--search-evaluation-max-decisions",),
    ("--multi-step",),
    ("--card-policy",),
    ("--expected-value-samples",),
    ("--strict-context",),
    ("--compare-policies",),
    ("--comparison-only",),
    ("--opponent-lead-policy",),
    ("--opponent-response-policy",),
    ("--opponent-policy-preset",),
    ("--use-profile-presets",),
    ("--opponent-statistics-file",),
    ("--left-opponent-player-id",),
    ("--right-opponent-player-id",),
    ("--left-opponent-lead-policy",),
    ("--left-opponent-response-policy",),
    ("--right-opponent-lead-policy",),
    ("--right-opponent-response-policy",),
)

LEGACY_NAMES = (
    "main",
    "parse_arguments",
    "build_analysis_result",
    "run_json_position_analysis",
    "run_json_historical_game_analysis",
    "run_json_training_dataset_conversion",
    "run_json_training_dataset_preparation",
    "run_json_bounded_search_evaluation",
    "run_json_dataset_partition_audit",
    "run_json_rolling_opponent_policy_evaluation",
    "run_json_historical_opponent_statistics_aggregation",
    "run_json_fixed_three_player_historical_list_analysis",
    "run_json_fixed_three_player_historical_list_comparison",
    "run_json_opponent_statistics_conversion",
    "validate_cli_arguments",
    "validate_live_opponent_profile_options",
    "validate_historical_game_cli_arguments",
    "validate_training_dataset_cli_arguments",
    "validate_training_dataset_preparation_cli_arguments",
    "validate_opponent_statistics_cli_arguments",
    "validate_fixed_three_player_historical_list_cli_arguments",
    "print_analysis_result",
    "print_historical_game_result",
    "print_training_dataset_result",
    "print_opponent_statistics_result",
    "print_multi_step_result",
    "print_policy_comparison_result",
)


def _load_example(name: str) -> dict[str, object]:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def _run_subprocess(prefix: list[str], args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [*prefix, *args],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _run_installed_subprocess(args: list[str]) -> subprocess.CompletedProcess[str]:
    command = "from skat_ai.cli import main; raise SystemExit(main())"
    return _run_subprocess([sys.executable, "-c", command], args)


def _application_options(
    workflow: str,
    workflow_options: dict[str, object],
) -> ApplicationExecutionOptions:
    if workflow == "position_analysis":
        return ApplicationExecutionOptions(
            position_analysis=PositionAnalysisApplicationOptions(**workflow_options)
        )
    if workflow == "historical_game":
        return ApplicationExecutionOptions(
            historical_game=HistoricalGameApplicationOptions(**workflow_options)
        )
    if workflow == "training_dataset":
        return ApplicationExecutionOptions(
            training_dataset=TrainingDatasetApplicationOptions(**workflow_options)
        )
    return ApplicationExecutionOptions()


def _action_contract(parser) -> tuple[tuple[object, ...], ...]:
    return tuple(
        (
            tuple(action.option_strings),
            action.dest,
            action.nargs,
            action.const,
            action.default,
            getattr(action.type, "__name__", None),
            tuple(action.choices) if action.choices is not None else None,
            action.required,
            type(action).__name__,
        )
        for action in parser._actions
    )


def test_installed_cli_contract_constants_are_exact_and_internal() -> None:
    assert cli.INSTALLED_CLI_CONTRACT_VERSION == 1
    assert cli.INSTALLED_CLI_COMMAND == "skat-ai"
    assert cli.MODULE_CLI_COMMAND == "python -m skat_ai"
    assert cli.LEGACY_CLI_COMMAND == "python main.py"
    assert cli.CLI_INVOCATION_STYLES == ("installed", "module", "legacy")

    import skat_ai.api.v1 as api_v1

    assert "INSTALLED_CLI_CONTRACT_VERSION" not in api_v1.__all__
    assert "INSTALLED_CLI_COMMAND" not in api_v1.__all__
    assert "MODULE_CLI_COMMAND" not in api_v1.__all__
    assert "LEGACY_CLI_COMMAND" not in api_v1.__all__


def test_parser_action_contract_is_exactly_equal_for_all_invocation_styles() -> None:
    contracts = {
        style: _action_contract(cli.build_argument_parser(style))
        for style in cli.CLI_INVOCATION_STYLES
    }

    assert contracts["installed"] == contracts["module"] == contracts["legacy"]
    assert tuple(action[0] for action in contracts["installed"]) == EXPECTED_OPTION_STRINGS
    assert tuple(action[1] for action in contracts["installed"]) == (
        "help",
        "version",
        "input",
        "samples",
        "seed",
        "opponent_strategy",
        "output",
        "quiet",
        "include_provenance",
        "audit_dataset_partitions",
        "dataset_partition_mode",
        "aggregate_opponent_statistics",
        "opponent_statistics_partition",
        "opponent_statistics_before",
        "export_opponent_statistics",
        "evaluate_opponent_policy_profiles",
        "profile_source_partition",
        "profile_evaluation_partition",
        "historical_decision_snapshots",
        "historical_game_review",
        "historical_search_review",
        "historical_replay_coaching",
        "search_seed",
        "search_budget_profile",
        "evaluate_bounded_search",
        "search_evaluation_partition",
        "search_evaluation_max_decisions",
        "multi_step",
        "card_policy",
        "expected_value_samples",
        "strict_context",
        "compare_policies",
        "comparison_only",
        "opponent_lead_policy",
        "opponent_response_policy",
        "opponent_policy_preset",
        "use_profile_presets",
        "opponent_statistics_file",
        "left_opponent_player_id",
        "right_opponent_player_id",
        "left_opponent_lead_policy",
        "left_opponent_response_policy",
        "right_opponent_lead_policy",
        "right_opponent_response_policy",
    )


def test_help_is_invocation_specific_without_changing_options() -> None:
    installed = cli.build_argument_parser("installed").format_help()
    module = cli.build_argument_parser("module").format_help()
    legacy = cli.build_argument_parser("legacy").format_help()

    assert installed.startswith("usage: skat-ai")
    assert module.startswith("usage: python -m skat_ai")
    assert legacy.startswith("usage: python main.py")
    assert "skat-ai --input position.json" in installed
    assert "python -m skat_ai --input position.json" in module
    assert "examples/grand_second_position.json" not in installed
    assert "examples/grand_second_position.json" not in module
    assert "python main.py --input examples/grand_second_position.json" in legacy
    for option in (
        "--version",
        "--input",
        "--output",
        "--quiet",
        "--include-provenance",
        "--multi-step",
    ):
        assert option in installed and option in module and option in legacy


@pytest.mark.parametrize("style", cli.CLI_INVOCATION_STYLES)
def test_help_and_version_exit_without_loading_or_execution(
    style: str,
    monkeypatch,
    capsys,
) -> None:
    def unexpected_call(*_args, **_kwargs):
        raise AssertionError("Help or version attempted input, schema, or workflow access.")

    monkeypatch.setattr(cli, "load_json_object", unexpected_call)
    monkeypatch.setattr(cli, "get_input_workflow", unexpected_call)
    with pytest.raises(SystemExit) as help_exit:
        cli.run_cli(["--help"], invocation_style=style)
    help_output = capsys.readouterr()
    assert help_exit.value.code == 0
    assert help_output.err == ""

    with pytest.raises(SystemExit) as version_exit:
        cli.run_cli(["--version"], invocation_style=style)
    version_output = capsys.readouterr()
    assert version_exit.value.code == 0
    assert version_output.out == "skat-ai 0.12.0\n"
    assert version_output.err == ""


def test_module_entry_point_and_package_cli_do_not_import_root_main() -> None:
    command = (
        "import json, sys\n"
        "import skat_ai.cli\n"
        "print(json.dumps({'root_loaded': 'main' in sys.modules, "
        "'callable': callable(skat_ai.cli.main)}))\n"
    )
    imported = _run_subprocess([sys.executable, "-c", command], [])
    module_version = _run_subprocess([sys.executable, "-m", "skat_ai"], ["--version"])

    assert imported.returncode == 0
    assert json.loads(imported.stdout) == {"root_loaded": False, "callable": True}
    assert module_version.returncode == 0
    assert module_version.stdout == "skat-ai 0.12.0\n"
    assert module_version.stderr == ""


@pytest.mark.parametrize(
    ("example_name", "cli_options", "workflow_options", "workflow"),
    WORKFLOW_CASES,
)
def test_all_seven_cli_forms_match_application_and_public_api(
    example_name: str,
    cli_options: tuple[str, ...],
    workflow_options: dict[str, object],
    workflow: str,
    tmp_path: Path,
    capsys,
) -> None:
    input_path = EXAMPLES / example_name
    installed_output = tmp_path / "installed.json"
    module_output = tmp_path / "module.json"
    legacy_output = tmp_path / "legacy.json"
    common = ["--input", str(input_path), *cli_options, "--quiet"]

    assert cli.run_cli(
        [*common, "--output", str(installed_output)],
        invocation_style="installed",
    ) == 0
    assert capsys.readouterr().out == ""
    module = _run_subprocess(
        [sys.executable, "-m", "skat_ai"],
        [*common, "--output", str(module_output)],
    )
    legacy = _run_subprocess(
        [sys.executable, str(PROJECT_ROOT / "main.py")],
        [*common, "--output", str(legacy_output)],
    )
    assert module.returncode == legacy.returncode == 0
    assert module.stdout == module.stderr == legacy.stdout == legacy.stderr == ""

    installed_document = json.loads(installed_output.read_text(encoding="utf-8"))
    module_document = json.loads(module_output.read_text(encoding="utf-8"))
    legacy_document = json.loads(legacy_output.read_text(encoding="utf-8"))
    source = _load_example(example_name)
    public_document = execute_document(
        source,
        options=ExecutionOptionsV1(workflow_options=workflow_options),
        input_reference=str(input_path),
    ).result.to_dict()["document"]
    application_document = execute_application_invocation(
        build_application_invocation(
            source,
            input_reference=str(input_path),
            options=_application_options(workflow, workflow_options),
        )
    ).result.to_dict()["document"]

    assert installed_document == module_document == legacy_document
    assert installed_document == application_document == public_document
    if workflow == "training_dataset_preparation":
        assert installed_document["training_dataset_preparation_summary"]["plan"][
            "status"
        ] == "unavailable"


@pytest.mark.parametrize(
    ("example_name", "cli_options", "workflow_options", "workflow"),
    WORKFLOW_CASES,
)
def test_all_seven_provenance_outputs_match_public_installed_module_and_legacy(
    example_name: str,
    cli_options: tuple[str, ...],
    workflow_options: dict[str, object],
    workflow: str,
    tmp_path: Path,
    capsys,
) -> None:
    input_path = EXAMPLES / example_name
    paths = {
        "installed": tmp_path / "installed-provenance.json",
        "module": tmp_path / "module-provenance.json",
        "legacy": tmp_path / "legacy-provenance.json",
    }
    common = [
        "--input",
        str(input_path),
        *cli_options,
        "--include-provenance",
        "--quiet",
        "--output",
    ]

    assert cli.run_cli([*common, str(paths["installed"])]) == 0
    assert capsys.readouterr().out == ""
    module = _run_subprocess(
        [sys.executable, "-m", "skat_ai"],
        [*common, str(paths["module"])],
    )
    legacy = _run_subprocess(
        [sys.executable, str(PROJECT_ROOT / "main.py")],
        [*common, str(paths["legacy"])],
    )
    assert module.returncode == legacy.returncode == 0
    assert module.stdout == module.stderr == legacy.stdout == legacy.stderr == ""

    documents = [json.loads(path.read_text(encoding="utf-8")) for path in paths.values()]
    public = execute_document(
        _load_example(example_name),
        options=ExecutionOptionsV1(
            include_provenance=True,
            workflow_options=workflow_options,
        ),
        input_reference=str(input_path),
    )
    public_document = public.result.to_dict()["document"]

    assert documents[0] == documents[1] == documents[2] == public_document
    assert public.field_provenance is not None
    assert documents[0]["field_provenance"] == public.field_provenance.to_dict()
    assert documents[0]["field_provenance"]["workflow"] == workflow


def test_provenance_summary_is_concise_and_quiet_retains_json(
    tmp_path: Path,
    capsys,
) -> None:
    input_path = EXAMPLES / "opponent_statistics.json"
    output_path = tmp_path / "summary.json"
    args = [
        "--input",
        str(input_path),
        "--output",
        str(output_path),
        "--include-provenance",
    ]

    assert cli.run_cli(args) == 0
    output = capsys.readouterr()
    document = json.loads(output_path.read_text(encoding="utf-8"))
    coverage = document["field_provenance"]["result"]["coverage_summary"]
    covered = coverage["provenanced_path_count"] + coverage["exempted_path_count"]
    expected_section = (
        "Field Provenance\n"
        "Version: 1\n"
        "Status: complete\n"
        "Result attachment: opponent_statistics_result\n"
        f"Covered leaves: {covered}/{coverage['leaf_path_count']}\n"
        "Private dependencies redacted: no\n"
        "Artifact attachment count: 0\n"
    )
    assert output.err == ""
    assert output.out.endswith(expected_section)
    emitted_section = "Field Provenance\n" + output.out.rsplit(
        "Field Provenance\n", maxsplit=1
    )[1]
    assert emitted_section == expected_section
    for forbidden in ("field_path", "reference_id", "player_id", "cards"):
        assert forbidden not in emitted_section

    module = _run_subprocess([sys.executable, "-m", "skat_ai"], args)
    legacy = _run_subprocess(
        [sys.executable, str(PROJECT_ROOT / "main.py")],
        args,
    )
    assert module.returncode == legacy.returncode == 0
    assert module.stdout == legacy.stdout == output.out
    assert module.stderr == legacy.stderr == ""

    quiet_path = tmp_path / "quiet-summary.json"
    assert cli.run_cli([*args, "--output", str(quiet_path), "--quiet"]) == 0
    quiet = capsys.readouterr()
    assert quiet.out == quiet.err == ""
    assert "field_provenance" in json.loads(quiet_path.read_text(encoding="utf-8"))


def test_cli_rejects_output_only_field_provenance_in_root_input(
    tmp_path: Path,
    capsys,
) -> None:
    source = _load_example("grand_second_position.json")
    source["field_provenance"] = {"forged": True}
    input_path = tmp_path / "forged-input.json"
    input_path.write_text(json.dumps(source), encoding="utf-8")

    assert cli.run_cli(["--input", str(input_path), "--quiet"]) == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert "field_provenance is an output-only Root field" in output.err


def test_provenance_artifact_sidecar_preserves_export_document(
    tmp_path: Path,
    capsys,
) -> None:
    input_path = EXAMPLES / "training_dataset_variable_length.json"
    output_path = tmp_path / "aggregation.json"
    export_path = tmp_path / "statistics.json"
    args = [
        "--input",
        str(input_path),
        "--aggregate-opponent-statistics",
        "--export-opponent-statistics",
        str(export_path),
        "--output",
        str(output_path),
        "--include-provenance",
        "--quiet",
    ]

    assert cli.run_cli(args) == 0
    assert capsys.readouterr().out == ""
    result = json.loads(output_path.read_text(encoding="utf-8"))
    exported = json.loads(export_path.read_text(encoding="utf-8"))
    artifacts = result["field_provenance"]["artifacts"]

    assert len(artifacts) == 1
    assert artifacts[0]["artifact_name"] == "opponent_statistics_input"
    assert artifacts[0]["attachment"]["document_scope"] == "artifact_document"
    assert set(exported) == {"opponent_statistics_input"}
    assert "field_provenance" not in exported


def test_human_readable_output_and_confirmation_match_module_and_legacy(
    tmp_path: Path,
    capsys,
) -> None:
    input_path = EXAMPLES / "opponent_statistics.json"
    output_path = tmp_path / "result.json"
    args = ["--input", str(input_path), "--output", str(output_path)]

    assert cli.run_cli(args, invocation_style="installed") == 0
    installed = capsys.readouterr()
    module = _run_subprocess([sys.executable, "-m", "skat_ai"], args)
    legacy = _run_subprocess([sys.executable, str(PROJECT_ROOT / "main.py")], args)

    assert installed.err == module.stderr == legacy.stderr == ""
    assert installed.out == module.stdout == legacy.stdout
    assert "Opponent statistics summary" in installed.out
    assert f"Output file written: {output_path}" in installed.out


@pytest.mark.parametrize(
    ("example_name", "cli_options", "workflow_options", "workflow"),
    [
        (
            "grand_second_position.json",
            (
                "--samples",
                "1",
                "--seed",
                "42",
                "--multi-step",
                "1",
                "--card-policy",
                "highest_point",
                "--expected-value-samples",
                "1",
                "--compare-policies",
            ),
            {
                "sample_count_override": 1,
                "random_seed_override": 42,
                "multi_step_count": 1,
                "card_selection_policy": "highest_point",
                "expected_value_sample_count": 1,
                "compare_policies": True,
            },
            "position_analysis",
        ),
        (
            "historical_grand_normal_completion.json",
            ("--historical-decision-snapshots",),
            {"decision_snapshots": True},
            "historical_game",
        ),
        (
            "training_dataset_partition_audit.json",
            ("--audit-dataset-partitions", "--dataset-partition-mode", "report_only"),
            {"operation": "partition_audit", "partition_audit_mode": "report_only"},
            "training_dataset",
        ),
        (
            "grand_bounded_search_exhaustive.json",
            (),
            {},
            "position_analysis",
        ),
        (
            "grand_auto_search_fallback.json",
            (),
            {},
            "position_analysis",
        ),
        (
            "historical_grand_defender_concession.json",
            (
                "--historical-decision-snapshots",
                "--historical-game-review",
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
            ),
            {
                "decision_snapshots": True,
                "immediate_review": True,
                "search_review": True,
                "replay_coaching": True,
                "search_seed": 71,
                "search_budget_profile": "interactive_v1",
                "immediate_sample_count": 1,
                "immediate_base_random_seed": 42,
            },
            "historical_game",
        ),
        (
            "historical_opponent_policy_evaluation_dataset.json",
            ("--evaluate-opponent-policy-profiles",),
            {"operation": "rolling_opponent_policy_evaluation"},
            "training_dataset",
        ),
        (
            "training_dataset_normal_play.json",
            (
                "--evaluate-bounded-search",
                "--search-seed",
                "71",
                "--search-evaluation-max-decisions",
                "1",
            ),
            {
                "operation": "bounded_search_evaluation",
                "bounded_search_seed": 71,
                "bounded_search_max_decisions": 1,
            },
            "training_dataset",
        ),
        (
            "fixed_three_player_historical_list_all_passed.json",
            (),
            {},
            "fixed_three_player_historical_list",
        ),
    ],
)
def test_representative_submodes_match_all_execution_boundaries(
    example_name: str,
    cli_options: tuple[str, ...],
    workflow_options: dict[str, object],
    workflow: str,
    tmp_path: Path,
    capsys,
) -> None:
    input_path = EXAMPLES / example_name
    paths = {
        "installed": tmp_path / "installed-submode.json",
        "module": tmp_path / "module-submode.json",
        "legacy": tmp_path / "legacy-submode.json",
    }
    common = ["--input", str(input_path), *cli_options, "--quiet", "--output"]

    assert cli.run_cli([*common, str(paths["installed"])]) == 0
    assert capsys.readouterr().out == ""
    module = _run_subprocess(
        [sys.executable, "-m", "skat_ai"],
        [*common, str(paths["module"])],
    )
    legacy = _run_subprocess(
        [sys.executable, str(PROJECT_ROOT / "main.py")],
        [*common, str(paths["legacy"])],
    )
    assert module.returncode == legacy.returncode == 0

    source = _load_example(example_name)
    public = execute_document(
        source,
        options=ExecutionOptionsV1(workflow_options=workflow_options),
        input_reference=str(input_path),
    ).result.to_dict()["document"]
    application = execute_application_invocation(
        build_application_invocation(
            source,
            input_reference=str(input_path),
            options=_application_options(workflow, workflow_options),
        )
    ).result.to_dict()["document"]
    documents = [json.loads(path.read_text(encoding="utf-8")) for path in paths.values()]
    assert documents[0] == documents[1] == documents[2] == public == application
    if example_name == "grand_auto_search_fallback.json":
        assert documents[0]["bounded_search_result"]["status"] == "partial"
    if example_name == "fixed_three_player_historical_list_all_passed.json":
        assert documents[0]["fixed_three_player_historical_list_summary"][
            "ranking_status"
        ] == "lot_required"


def test_auxiliary_export_matches_all_boundaries(tmp_path: Path, capsys) -> None:
    input_path = EXAMPLES / "training_dataset_normal_play.json"
    installed_output = tmp_path / "installed.json"
    installed_export = tmp_path / "installed-export.json"
    module_output = tmp_path / "module.json"
    module_export = tmp_path / "module-export.json"
    legacy_output = tmp_path / "legacy.json"
    legacy_export = tmp_path / "legacy-export.json"

    def args(output: Path, export: Path) -> list[str]:
        return [
            "--input",
            str(input_path),
            "--aggregate-opponent-statistics",
            "--output",
            str(output),
            "--export-opponent-statistics",
            str(export),
            "--quiet",
        ]

    assert cli.run_cli(args(installed_output, installed_export)) == 0
    assert capsys.readouterr().out == ""
    module = _run_subprocess(
        [sys.executable, "-m", "skat_ai"],
        args(module_output, module_export),
    )
    legacy = _run_subprocess(
        [sys.executable, str(PROJECT_ROOT / "main.py")],
        args(legacy_output, legacy_export),
    )
    assert module.returncode == legacy.returncode == 0

    public = execute_document(
        _load_example("training_dataset_normal_play.json"),
        options=ExecutionOptionsV1(
            workflow_options={
                "operation": "historical_opponent_statistics_aggregation",
                "export_opponent_statistics": True,
            }
        ),
        input_reference=str(input_path),
    )
    application = execute_application_invocation(
        build_application_invocation(
            _load_example("training_dataset_normal_play.json"),
            input_reference=str(input_path),
            options=ApplicationExecutionOptions(
                training_dataset=TrainingDatasetApplicationOptions(
                    operation="historical_opponent_statistics_aggregation",
                    export_opponent_statistics=True,
                )
            ),
        )
    )
    cli_outputs = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in (installed_output, module_output, legacy_output)
    ]
    cli_exports = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in (installed_export, module_export, legacy_export)
    ]
    assert cli_outputs[0] == cli_outputs[1] == cli_outputs[2]
    assert cli_outputs[0] == public.result.to_dict()["document"]
    assert cli_outputs[0] == application.result.to_dict()["document"]
    assert cli_exports[0] == cli_exports[1] == cli_exports[2]
    assert cli_exports[0] == public.artifacts[0].to_dict()["document"]
    assert cli_exports[0] == application.artifacts[0].to_dict()


def test_usage_expected_failure_and_unexpected_option_exit_codes(
    tmp_path: Path,
    capsys,
) -> None:
    position = EXAMPLES / "grand_second_position.json"
    usage_code = cli.run_cli(
        ["--input", str(position), "--comparison-only"],
        invocation_style="installed",
    )
    usage = capsys.readouterr()
    assert usage_code == 2
    assert usage.out == ""
    assert usage.err == "CLI error: --comparison-only requires --compare-policies.\n"

    failure_code = cli.run_cli(
        ["--input", str(tmp_path / "missing.json")],
        invocation_style="installed",
    )
    failure = capsys.readouterr()
    assert failure_code == 1
    assert failure.out == ""
    assert failure.err.startswith("Error: Input file not found:")

    unknown = _run_subprocess([sys.executable, "-m", "skat_ai"], ["--provenance"])
    assert unknown.returncode == 2
    assert unknown.stdout == ""
    assert "unrecognized arguments: --provenance" in unknown.stderr


@pytest.mark.parametrize(
    "runner",
    [
        _run_installed_subprocess,
        lambda args: _run_subprocess([sys.executable, "-m", "skat_ai"], args),
        lambda args: _run_subprocess(
            [sys.executable, str(PROJECT_ROOT / "main.py")], args
        ),
    ],
    ids=("installed", "module", "legacy"),
)
def test_all_command_forms_preserve_usage_and_resource_failures(
    runner,
    tmp_path: Path,
) -> None:
    position = EXAMPLES / "grand_second_position.json"
    semantic = runner(["--input", str(position), "--comparison-only"])
    unknown = runner(["--not-an-option"])
    missing = runner(["--input", str(tmp_path / "missing.json")])

    assert semantic.returncode == 2
    assert semantic.stdout == ""
    assert semantic.stderr == "CLI error: --comparison-only requires --compare-policies.\n"
    assert unknown.returncode == 2
    assert unknown.stdout == ""
    assert "unrecognized arguments: --not-an-option" in unknown.stderr
    assert missing.returncode == 1
    assert missing.stdout == ""
    assert missing.stderr.startswith("Error: Input file not found:")
    for result in (semantic, unknown, missing):
        assert "Traceback" not in result.stderr


def test_legacy_root_names_signatures_and_patch_points_remain_active(
    monkeypatch,
    tmp_path: Path,
) -> None:
    for name in LEGACY_NAMES:
        assert callable(getattr(legacy_main, name))
    assert len(inspect.signature(legacy_main.main).parameters) == 0
    assert len(inspect.signature(legacy_main.parse_arguments).parameters) == 0
    assert len(inspect.signature(cli.main).parameters) == 0
    for name in LEGACY_NAMES[2:14]:
        assert inspect.signature(getattr(legacy_main, name)) == inspect.signature(
            getattr(cli, name)
        )
    assert legacy_main.CliUsageError is cli.CliUsageError
    assert tuple(function.__name__ for function in legacy_main._LEGACY_PATCH_POINT_FUNCTIONS) == (
        "aggregate_historical_opponent_statistics",
        "build_opponent_statistics_summary",
        "build_training_dataset_summary",
        "evaluate_rolling_opponent_policy_predictions",
        "load_opponent_statistics_from_json",
    )

    expected = {
        "dataset_id": "legacy-patch",
        "dataset_version": "1",
        "record_count": 0,
        "sample_count": 0,
        "partition_counts": {},
    }
    monkeypatch.setattr(legacy_main, "build_training_dataset_summary", lambda _value: expected)
    output_path = tmp_path / "patched.json"
    legacy_main.run_json_training_dataset_conversion(
        file_path=str(EXAMPLES / "training_dataset_normal_play.json"),
        output_path=str(output_path),
        quiet=True,
    )
    assert json.loads(output_path.read_text(encoding="utf-8"))[
        "training_dataset_summary"
    ] == expected
