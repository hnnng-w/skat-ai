from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import pytest

import main as legacy_main
import skatmind.api.v1 as public_api
import skatmind.cli.execution as cli
import skatmind.cli.run as run_cli_module
from skatmind.cli.onboarding_contracts import (
    ADVANCED_COMMAND_FAMILIES,
    ADVANCED_ROOT_AUTOMATION_CLI_VERSION,
    CLI_ONBOARDING_CONTRACT_VERSION,
    CLI_ONBOARDING_POLICIES,
    PRODUCT_TOP_LEVEL_AREAS,
    PRODUCT_TOP_LEVEL_HELP_VERSION,
    RUN_HELP_GROUPS,
)
from skatmind.cli.root_compatibility import _has_active_legacy_patch_namespace
from skatmind.cli.root_parser import build_argument_parser, parse_arguments
from skatmind.cli.top_level_parser import (
    TOP_LEVEL_DISPATCH_APP,
    TOP_LEVEL_DISPATCH_CAPTURE,
    TOP_LEVEL_DISPATCH_CORPUS,
    TOP_LEVEL_DISPATCH_HELP,
    TOP_LEVEL_DISPATCH_ROOT_COMPATIBILITY,
    TOP_LEVEL_DISPATCH_RUN,
    TOP_LEVEL_DISPATCH_SESSION,
    TOP_LEVEL_DISPATCH_UNKNOWN_COMMAND,
    TOP_LEVEL_DISPATCH_VERSION,
    build_top_level_argument_parser,
    classify_top_level_argv,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _action_contract(action: argparse.Action) -> tuple[object, ...]:
    return (
        tuple(action.option_strings),
        action.dest,
        action.nargs,
        action.const,
        action.default,
        getattr(action.type, "__name__", None),
        tuple(action.choices) if action.choices is not None else None,
        type(action).__name__,
    )


def _run_subprocess(prefix: list[str], argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [*prefix, *argv],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_private_onboarding_contract_versions_and_policies_are_exact() -> None:
    assert CLI_ONBOARDING_CONTRACT_VERSION == 1
    assert ADVANCED_ROOT_AUTOMATION_CLI_VERSION == 1
    assert PRODUCT_TOP_LEVEL_HELP_VERSION == 1
    assert CLI_ONBOARDING_POLICIES == (
        "bare_skatmind_remains_primary_frontend",
        "top_level_help_is_product_oriented",
        "run_is_canonical_root_json_automation",
        "direct_root_options_remain_package_1_x_compatible",
        "run_and_compatibility_share_one_root_implementation",
        "advanced_command_families_remain_explicit",
        "help_and_version_execute_no_product_work",
        "advanced_options_are_grouped_by_user_purpose",
        "task_examples_explain_goal_input_and_output",
        "existing_cli_results_errors_and_exit_codes_remain_stable",
    )
    for name in (
        "CLI_ONBOARDING_CONTRACT_VERSION",
        "ADVANCED_ROOT_AUTOMATION_CLI_VERSION",
        "PRODUCT_TOP_LEVEL_HELP_VERSION",
        "CLI_ONBOARDING_POLICIES",
    ):
        assert name not in public_api.__all__
        assert not hasattr(public_api, name)


@pytest.mark.parametrize(
    ("argv", "expected"),
    (
        ((), TOP_LEVEL_DISPATCH_APP),
        (("app",), TOP_LEVEL_DISPATCH_APP),
        (("run",), TOP_LEVEL_DISPATCH_RUN),
        (("session",), TOP_LEVEL_DISPATCH_SESSION),
        (("capture",), TOP_LEVEL_DISPATCH_CAPTURE),
        (("corpus",), TOP_LEVEL_DISPATCH_CORPUS),
        (("-h",), TOP_LEVEL_DISPATCH_HELP),
        (("--help",), TOP_LEVEL_DISPATCH_HELP),
        (("--version",), TOP_LEVEL_DISPATCH_VERSION),
        (("--input", "request.json"), TOP_LEVEL_DISPATCH_ROOT_COMPATIBILITY),
        (("--not-an-option",), TOP_LEVEL_DISPATCH_ROOT_COMPATIBILITY),
        (("unknown",), TOP_LEVEL_DISPATCH_UNKNOWN_COMMAND),
    ),
)
def test_top_level_dispatch_classification_is_exact(
    argv: tuple[str, ...],
    expected: str,
) -> None:
    assert classify_top_level_argv(argv) == expected


def test_top_level_help_is_concise_ordered_product_discovery() -> None:
    parser = build_top_level_argument_parser()
    help_text = parser.format_help()
    headings = (
        "Product introduction",
        "Start here",
        "What the local application includes",
        "Advanced commands",
        "Common options",
        "More help",
    )
    assert [help_text.index(heading) for heading in headings] == sorted(
        help_text.index(heading) for heading in headings
    )
    assert PRODUCT_TOP_LEVEL_AREAS == (
        "Analyze a position",
        "Review a completed game",
        "Sessions",
        "Match capture",
        "Learning & cross-game insights",
        "About SkatMind",
    )
    assert [help_text.index(area) for area in PRODUCT_TOP_LEVEL_AREAS] == sorted(
        help_text.index(area) for area in PRODUCT_TOP_LEVEL_AREAS
    )
    assert ADVANCED_COMMAND_FAMILIES == ("app", "run", "session", "capture", "corpus")
    command_lines = [
        next(line for line in help_text.splitlines() if line.startswith(f"  {command}"))
        for command in ADVANCED_COMMAND_FAMILIES
    ]
    assert [help_text.index(line) for line in command_lines] == sorted(
        help_text.index(line) for line in command_lines
    )
    assert "complete private local browser application" in help_text
    assert "version, license, local operation, and managed-storage information" in help_text


def test_top_level_parser_exposes_only_help_and_version_options() -> None:
    parser = build_top_level_argument_parser()
    assert tuple(tuple(action.option_strings) for action in parser._actions) == (
        ("-h", "--help"),
        ("--version",),
    )
    help_text = parser.format_help()
    for root_option in (
        "--input",
        "--output",
        "--quiet",
        "--samples",
        "--seed",
        "--multi-step",
        "--compare-policies",
        "--search-budget-profile",
        "--include-provenance",
    ):
        assert root_option not in help_text


@pytest.mark.parametrize(
    ("style", "expected_program"),
    (
        ("installed", "skatmind run"),
        ("module", "python -m skatmind run"),
        ("legacy", "python main.py run"),
    ),
)
def test_run_parser_uses_exact_invocation_program(style: str, expected_program: str) -> None:
    assert build_argument_parser(style, parser_mode="run").prog == expected_program


def test_run_and_compatibility_parser_actions_are_structurally_equal() -> None:
    compatibility = build_argument_parser()
    run = build_argument_parser(parser_mode="run")
    compatibility_actions = {
        tuple(action.option_strings): action for action in compatibility._actions
    }
    run_actions = {tuple(action.option_strings): action for action in run._actions}
    assert set(run_actions) == set(compatibility_actions)
    for option_strings, compatibility_action in compatibility_actions.items():
        run_action = run_actions[option_strings]
        assert _action_contract(run_action) == _action_contract(compatibility_action)
        assert run_action.required is (option_strings == ("--input",))
        assert compatibility_action.required is False


def test_run_help_groups_cover_every_root_action_exactly_once() -> None:
    parser = build_argument_parser(parser_mode="run")
    nonempty_groups = tuple(group for group in parser._action_groups if group._group_actions)
    assert tuple(group.title for group in nonempty_groups) == RUN_HELP_GROUPS
    grouped_actions = tuple(action for group in nonempty_groups for action in group._group_actions)
    assert len(grouped_actions) == len(parser._actions)
    assert set(map(id, grouped_actions)) == set(map(id, parser._actions))


def test_run_requires_explicit_input_while_compatibility_retains_default(capsys) -> None:
    assert parse_arguments([]).input == "input_position.json"
    with pytest.raises(SystemExit) as raised:
        parse_arguments([], parser_mode="run")
    assert raised.value.code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "the following arguments are required: --input" in captured.err

    with pytest.raises(SystemExit) as help_exit:
        cli.run_cli(["run", "--help"])
    assert help_exit.value.code == 0
    assert capsys.readouterr().err == ""
    with pytest.raises(SystemExit) as version_exit:
        cli.run_cli(["run", "--version"])
    assert version_exit.value.code == 0
    assert capsys.readouterr().out == "SkatMind 0.17.0\n"


def test_run_parser_preserves_supplied_option_tracking() -> None:
    argv = [
        "--input",
        "request.json",
        "--strict-context",
        "--expected-value-samples=1000",
        "--evaluate-rolling-opponent-policies",
    ]
    compatibility = parse_arguments(argv)
    run = parse_arguments(argv, parser_mode="run")
    assert vars(run) == vars(compatibility)
    assert run._supplied_cli_options == frozenset(
        {
            "--input",
            "--strict-context",
            "--expected-value-samples",
            "--evaluate-rolling-opponent-policies",
        }
    )


def test_run_help_explains_advanced_concepts_without_quality_claims() -> None:
    help_text = " ".join(build_argument_parser(parser_mode="run").format_help().split())
    expected = (
        "automation, portability, and reproducibility",
        "normal frontend use does not require JSON",
        "More samples may increase runtime",
        "not calibrated probability",
        "A seed makes randomized work reproducible",
        "Fixed simulation behavior for opponents, not learned prediction or hidden truth",
        "bounded work limit for Search",
        "not a quality, completeness, or optimality guarantee",
        "Field-origin and information-timing evidence",
        "not Confidence, correctness, or proof",
        "suppresses successful terminal presentation, but not errors",
        "requested output",
        "auxiliary Artifact files",
    )
    for text in expected:
        assert text in help_text


def test_run_help_has_six_ordered_task_examples_with_goal_input_result_and_output() -> None:
    installed = build_argument_parser(parser_mode="run").format_help()
    topics = (
        "Analyze an exported Position request",
        "Review a completed Historical Game",
        "Run Multi-Step Policy Comparison",
        "Prepare a Training Dataset",
        "Audit Dataset partitions",
        "Aggregate reusable Opponent Statistics",
    )
    assert [installed.index(topic) for topic in topics] == sorted(
        installed.index(topic) for topic in topics
    )
    for label in ("Goal:", "Input:", "Command:", "Result:", "Output file:"):
        assert installed.count(label) == 6
    assert installed.count("Command: skatmind run --input") == 6
    assert "examples/" not in installed

    module = build_argument_parser("module", parser_mode="run").format_help()
    assert module.count("Command: python -m skatmind run --input") == 6
    assert "examples/" not in module

    legacy = build_argument_parser("legacy", parser_mode="run").format_help()
    assert legacy.count("Command: python main.py run --input") == 6
    assert "examples/grand_second_position.json" in legacy


@pytest.mark.parametrize("style", ("installed", "module", "legacy"))
def test_run_dispatch_removes_only_leading_token_and_uses_shared_root(
    style: str,
    monkeypatch,
) -> None:
    calls: list[tuple[object, ...]] = []

    def run_root(argv, invocation_style, *, parser_mode):
        calls.append(
            (
                tuple(argv),
                invocation_style,
                parser_mode,
                _has_active_legacy_patch_namespace(),
            )
        )
        return 23

    monkeypatch.setattr(run_cli_module, "_run_cli", run_root)
    namespace = legacy_main if style == "legacy" else None
    assert (
        cli.run_cli(
            ["run", "--input", "request.json", "--quiet"],
            invocation_style=style,
            legacy_namespace=namespace,
        )
        == 23
    )
    assert calls == [
        (
            ("--input", "request.json", "--quiet"),
            style,
            "run",
            style == "legacy",
        )
    ]


def test_direct_root_compatibility_retains_original_argv_and_mode(monkeypatch) -> None:
    calls = []

    def run_root(argv, style):
        calls.append((argv, style))
        return 29

    monkeypatch.setattr(cli, "_run_cli", run_root)
    argv = ["--input", "request.json", "--quiet"]
    assert cli.run_cli(argv, invocation_style="module") == 29
    assert calls == [(argv, "module")]


@pytest.mark.parametrize(
    ("prefix", "identity"),
    (
        (
            [sys.executable, "-c", "from skatmind.cli import main; raise SystemExit(main())"],
            "skatmind",
        ),
        ([sys.executable, "-m", "skatmind"], "python -m skatmind"),
        ([sys.executable, "main.py"], "python main.py"),
    ),
    ids=("installed", "module", "legacy"),
)
def test_top_level_help_version_run_help_and_unknown_command_across_forms(
    prefix: list[str],
    identity: str,
) -> None:
    top_help = _run_subprocess(prefix, ["--help"])
    run_help = _run_subprocess(prefix, ["run", "--help"])
    version = _run_subprocess(prefix, ["--version"])
    missing_run_input = _run_subprocess(prefix, ["run"])
    unknown = _run_subprocess(prefix, ["not-a-command"])
    unknown_option = _run_subprocess(prefix, ["--not-an-option"])

    assert top_help.returncode == run_help.returncode == version.returncode == 0
    assert top_help.stderr == run_help.stderr == version.stderr == ""
    assert f"usage: {identity} [-h] [--version] [COMMAND]" in top_help.stdout
    assert f"usage: {identity} run" in run_help.stdout
    assert version.stdout == "SkatMind 0.17.0\n"
    assert missing_run_input.returncode == 2
    assert missing_run_input.stdout == ""
    assert f"usage: {identity} run" in missing_run_input.stderr
    assert "the following arguments are required: --input" in missing_run_input.stderr
    assert unknown.returncode == 2
    assert unknown.stdout == ""
    assert f"usage: {identity} [-h] [--version] [COMMAND]" in unknown.stderr
    assert "unknown command 'not-a-command'" in unknown.stderr
    assert f"Run '{identity} --help'" in unknown.stderr
    assert "Traceback" not in unknown.stderr
    assert unknown_option.returncode == 2
    assert unknown_option.stdout == ""
    assert f"usage: {identity}" in unknown_option.stderr
    assert "unrecognized arguments: --not-an-option" in unknown_option.stderr


@pytest.mark.parametrize("argument", ("--help", "--version"))
def test_top_level_help_and_version_have_lightweight_import_boundary(argument: str) -> None:
    probe = """
import sys
from skatmind.cli.entrypoint import run_cli

try:
    result = run_cli([sys.argv[1]])
except SystemExit as error:
    result = error.code
assert result == 0
blocked = (
    "skatmind.app_web",
    "skatmind.application",
    "skatmind.capture_web",
    "skatmind.cli.app",
    "skatmind.cli.capture",
    "skatmind.cli.corpus",
    "skatmind.cli.execution",
    "skatmind.cli.root_parser",
    "skatmind.cli.session",
    "skatmind.corpus_web",
    "skatmind.input_loader",
    "skatmind.learning_corpus",
    "skatmind.match_",
    "skatmind.schema_resources",
    "skatmind.search",
    "skatmind.session",
)
loaded = sorted(
    name for name in sys.modules
    if any(name == prefix or name.startswith(prefix) for prefix in blocked)
)
assert loaded == [], loaded
"""
    completed = subprocess.run(
        [sys.executable, "-c", probe, argument],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
