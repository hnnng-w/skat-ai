import argparse
import ast
import importlib
import inspect
import subprocess
import sys
from pathlib import Path

import pytest

import main as legacy_main
import skatmind.cli as cli_package
import skatmind.cli.execution as root_cli
import skatmind.cli.session as session_cli
from skatmind.cli.root_option_context import (
    current_supplied_workflow_option_names,
    invoke_with_supplied_root_cli_options,
)
from skatmind.errors import SkatMindValidationError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src" / "skatmind"


def _action_contract(parser: argparse.ArgumentParser) -> tuple[tuple[object, ...], ...]:
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


HELP_ACTION = (
    ("-h", "--help"),
    "help",
    0,
    None,
    argparse.SUPPRESS,
    None,
    None,
    False,
    "_HelpAction",
)
COMMON_ACTIONS = (
    (("--session",), "session", None, None, None, None, None, True, "_StoreAction"),
    (("--output",), "output", None, None, None, None, None, False, "_StoreAction"),
    (("--quiet",), "quiet", 0, True, False, None, None, False, "_StoreTrueAction"),
    (
        ("--include-provenance",),
        "include_provenance",
        0,
        True,
        False,
        None,
        None,
        False,
        "_StoreTrueAction",
    ),
)
POSITION_ACTIONS = (
    (
        ("--samples",),
        "samples",
        None,
        None,
        100,
        "_positive_sample_count",
        None,
        False,
        "_StoreAction",
    ),
    (("--seed",), "seed", None, None, 0, "int", None, False, "_StoreAction"),
    (
        ("--opponent-strategy",),
        "opponent_strategy",
        None,
        None,
        "basic",
        None,
        ("basic", "random"),
        False,
        "_StoreAction",
    ),
    (
        ("--recommendation-method",),
        "recommendation_method",
        None,
        None,
        None,
        None,
        ("immediate_expected_value", "bounded_search", "auto"),
        False,
        "_StoreAction",
    ),
    (
        ("--search-budget-profile",),
        "search_budget_profile",
        None,
        None,
        "interactive_v1",
        None,
        ("interactive_v1", "historical_review_v1", "evaluation_v1"),
        False,
        "_StoreAction",
    ),
)
HISTORICAL_ACTIONS = (
    (
        ("--historical-decision-snapshots",),
        "historical_decision_snapshots",
        0,
        True,
        False,
        None,
        None,
        False,
        "_StoreTrueAction",
    ),
    (
        ("--historical-game-review",),
        "historical_game_review",
        0,
        True,
        False,
        None,
        None,
        False,
        "_StoreTrueAction",
    ),
    (
        ("--historical-search-review",),
        "historical_search_review",
        0,
        True,
        False,
        None,
        None,
        False,
        "_StoreTrueAction",
    ),
    (
        ("--historical-replay-coaching",),
        "historical_replay_coaching",
        0,
        True,
        False,
        None,
        None,
        False,
        "_StoreTrueAction",
    ),
    (("--search-seed",), "search_seed", None, None, None, "int", None, False, "_StoreAction"),
    (
        ("--search-budget-profile",),
        "search_budget_profile",
        None,
        None,
        "historical_review_v1",
        None,
        ("interactive_v1", "historical_review_v1", "evaluation_v1"),
        False,
        "_StoreAction",
    ),
    (
        ("--samples",),
        "samples",
        None,
        None,
        None,
        "_positive_sample_count",
        None,
        False,
        "_StoreAction",
    ),
    (("--seed",), "seed", None, None, None, "int", None, False, "_StoreAction"),
)


def _required_output(actions: tuple[tuple[object, ...], ...]) -> tuple[tuple[object, ...], ...]:
    return tuple(
        (*action[:7], True, action[8]) if action[1] == "output" else action for action in actions
    )


def test_root_parser_identity_description_examples_and_formatter_are_exact() -> None:
    description = (
        "Analyze a Skat position, replay a historical game, expose a complete "
        "historical 36-position list or independent-list comparison, prepare or "
        "convert a training dataset, or normalize opponent statistics from JSON."
    )
    commands = {
        "installed": "skatmind",
        "module": "python -m skatmind",
        "legacy": "python main.py",
    }
    for style, command in commands.items():
        parser = root_cli.build_argument_parser(style)
        assert parser.prog == command
        assert parser.description == description
        assert parser.formatter_class is argparse.RawDescriptionHelpFormatter
        assert parser.epilog == root_cli._invocation_examples(style)
    assert "skatmind --input position.json" in root_cli._invocation_examples("installed")
    assert "python -m skatmind --input position.json" in root_cli._invocation_examples("module")
    assert (
        "python main.py --input examples/grand_second_position.json"
        in root_cli._invocation_examples("legacy")
    )


def test_session_parser_subcommand_action_contracts_are_exact() -> None:
    parser = session_cli.build_session_argument_parser()
    subparsers = parser._subparsers._group_actions[0].choices
    input_action = (
        ("--input",),
        "input",
        None,
        None,
        None,
        None,
        None,
        True,
        "_StoreAction",
    )
    target_revision = (
        ("--target-revision",),
        "target_revision",
        None,
        None,
        None,
        "_non_negative_integer",
        None,
        True,
        "_StoreAction",
    )
    checkpoint_index = (
        ("--checkpoint-index",),
        "checkpoint_index",
        None,
        None,
        None,
        "_non_negative_integer",
        None,
        True,
        "_StoreAction",
    )
    no_provenance = COMMON_ACTIONS[:3]
    expected = {
        "new": (HELP_ACTION, *COMMON_ACTIONS, input_action),
        "show": (HELP_ACTION, *no_provenance),
        "apply": (HELP_ACTION, *COMMON_ACTIONS, input_action, *POSITION_ACTIONS),
        "undo": (HELP_ACTION, *COMMON_ACTIONS, target_revision, *POSITION_ACTIONS),
        "correct": (HELP_ACTION, *COMMON_ACTIONS, input_action, *POSITION_ACTIONS),
        "checkpoint": (HELP_ACTION, *COMMON_ACTIONS, *POSITION_ACTIONS),
        "export-position": (
            HELP_ACTION,
            *_required_output(COMMON_ACTIONS),
            *POSITION_ACTIONS,
        ),
        "export-historical": (HELP_ACTION, *_required_output(COMMON_ACTIONS)),
        "analyze": (
            HELP_ACTION,
            *_required_output(COMMON_ACTIONS),
            *POSITION_ACTIONS,
        ),
        "review": (
            HELP_ACTION,
            *_required_output(COMMON_ACTIONS),
            checkpoint_index,
        ),
        "finalize": (
            HELP_ACTION,
            *_required_output(COMMON_ACTIONS),
            *HISTORICAL_ACTIONS,
        ),
        "assistant": (HELP_ACTION, COMMON_ACTIONS[0]),
    }
    assert tuple(subparsers) == tuple(expected)
    for name, expected_contract in expected.items():
        assert _action_contract(subparsers[name]) == expected_contract, name


def test_session_parser_program_names_and_description_are_exact() -> None:
    programs = {
        "installed": "skatmind session",
        "module": "python -m skatmind session",
        "legacy": "python main.py session",
    }
    for style, program in programs.items():
        parser = session_cli.build_session_argument_parser(style)
        assert parser.prog == program
        assert parser.description == (
            "Create, edit, inspect, export, analyze, and review one explicit "
            "private Skat Session file."
        )


def test_legacy_default_patch_values_and_resolution_are_exact(monkeypatch) -> None:
    expected_names = (
        "aggregate_historical_opponent_statistics",
        "audit_training_dataset_partitions",
        "build_card_analysis_report",
        "build_exportable_opponent_statistics_input",
        "build_fixed_three_player_historical_list_aggregation",
        "build_fixed_three_player_historical_list_comparison",
        "build_historical_decision_snapshots",
        "build_historical_game_review_summary",
        "build_historical_information_set_search_review_summary_v1",
        "build_historical_information_set_search_review_v1",
        "build_historical_opponent_statistics_aggregation_summary",
        "build_historical_replay_coaching_public_summaries",
        "build_historical_search_review_summary",
        "build_opponent_statistics_summary",
        "build_serializable_dataset_partition_audit",
        "build_serializable_historical_information_set_search_review_v1",
        "build_serializable_opponent_statistics_input",
        "build_serializable_rolling_opponent_policy_evaluation",
        "build_serializable_training_dataset_preparation_result",
        "build_strategic_summary",
        "build_training_dataset_preparation_result",
        "build_training_dataset_summary",
        "compare_multi_step_policies",
        "evaluate_bounded_search_dataset",
        "evaluate_information_set_search_dataset_v1",
        "evaluate_rolling_opponent_policy_predictions",
        "get_input_workflow",
        "load_opponent_statistics_from_json",
        "recommend_card_by_expected_value",
        "resolve_dataset_partition_audit_mode",
        "simulate_multiple_steps",
    )
    assert tuple(root_cli._DEFAULT_LEGACY_PATCH_VALUES) == expected_names
    for name in expected_names:
        assert root_cli._DEFAULT_LEGACY_PATCH_VALUES[name] is getattr(root_cli, name)

    original = root_cli.build_training_dataset_summary

    def patched(_dataset):
        return {"patched": True}

    monkeypatch.setattr(legacy_main, "build_training_dataset_summary", patched)
    dependencies = root_cli.build_legacy_application_dependencies()
    assert dependencies.training_dataset.build_summary is original
    with root_cli.legacy_patch_namespace(legacy_main):
        assert root_cli._active_legacy_patch_namespace is legacy_main
        dependencies = root_cli.build_legacy_application_dependencies()
        assert dependencies.training_dataset.build_summary is patched
    assert root_cli._active_legacy_patch_namespace is None
    dependencies = root_cli.build_legacy_application_dependencies()
    assert dependencies.training_dataset.build_summary is original


def test_root_and_legacy_compatibility_callable_signatures_are_preserved() -> None:
    delegated_names = (
        "build_legacy_application_dependencies",
        "execute_legacy_application",
        "load_external_opponent_statistics_document",
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
    )
    for name in delegated_names:
        assert inspect.signature(getattr(legacy_main, name)) == inspect.signature(
            getattr(root_cli, name)
        )

    assert str(inspect.signature(root_cli.build_argument_parser)) == (
        "(invocation_style: str = 'installed', *, parser_mode: str = "
        "'compatibility') -> argparse.ArgumentParser"
    )
    assert str(inspect.signature(root_cli.parse_arguments)) == (
        "(argv: list[str] | tuple[str, ...] | None = None, *, "
        "invocation_style: str = 'installed', parser_mode: str = "
        "'compatibility') -> argparse.Namespace"
    )
    assert str(inspect.signature(root_cli.run_cli)) == (
        "(argv: list[str] | tuple[str, ...] | None = None, *, "
        "invocation_style: str = 'installed', legacy_namespace: "
        "module | None = None) -> int"
    )
    assert str(inspect.signature(root_cli.main)) == "() -> int"
    assert str(inspect.signature(legacy_main.parse_arguments)) == "() -> argparse.Namespace"
    assert str(inspect.signature(legacy_main.main)) == "() -> int"


def test_session_facade_callable_signatures_are_preserved() -> None:
    assert str(inspect.signature(session_cli.build_session_argument_parser)) == (
        "(invocation_style: 'str' = 'installed') -> 'argparse.ArgumentParser'"
    )
    assert str(inspect.signature(session_cli.parse_session_arguments)) == (
        "(argv: 'list[str] | tuple[str, ...] | None' = None, *, "
        "invocation_style: 'str' = 'installed') -> 'argparse.Namespace'"
    )
    assert str(inspect.signature(session_cli.load_strict_json_object)) == (
        "(file_path: 'str') -> 'dict[str, object]'"
    )
    assert str(inspect.signature(session_cli.run_session_cli)) == (
        "(argv: 'list[str] | tuple[str, ...] | None' = None, *, "
        "invocation_style: 'str' = 'installed') -> 'int'"
    )


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (b"\xef\xbb\xbf{}", "Input JSON must use UTF-8 without a BOM."),
        (b"\xff", "Input file is not valid UTF-8."),
        (b'{"value": NaN}', "Non-finite JSON number 'NaN' is not allowed."),
        (
            b'{"outer": {"value": 1, "value": 2}}',
            "Duplicate JSON object key 'value' is not allowed.",
        ),
        (b"[]", "Input JSON root must be an object."),
        (b"{", "Input file is not valid JSON: Expecting property name enclosed in double quotes."),
    ],
)
def test_strict_session_json_errors_are_exact(
    tmp_path: Path,
    content: bytes,
    message: str,
) -> None:
    input_path = tmp_path / "input.json"
    input_path.write_bytes(content)
    with pytest.raises(SkatMindValidationError) as raised:
        session_cli.load_strict_json_object(str(input_path))
    assert str(raised.value) == message
    assert raised.value.path == ""


def test_strict_session_json_missing_file_error_is_exact(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    with pytest.raises(FileNotFoundError) as raised:
        session_cli.load_strict_json_object(str(missing))
    assert str(raised.value) == f"Input file not found: {missing}"


def test_cli_package_export_is_exact() -> None:
    assert cli_package.__all__ == ("main",)
    assert cli_package.main is root_cli.main


def test_root_and_session_compatibility_facade_names_are_retained() -> None:
    root_names = (
        "CliUsageError",
        "build_argument_parser",
        "parse_arguments",
        "validate_cli_arguments",
        "validate_live_opponent_profile_options",
        "validate_historical_game_cli_arguments",
        "validate_training_dataset_cli_arguments",
        "validate_training_dataset_preparation_cli_arguments",
        "validate_opponent_statistics_cli_arguments",
        "validate_fixed_three_player_historical_list_cli_arguments",
        "build_legacy_application_dependencies",
        "execute_legacy_application",
        "load_external_opponent_statistics_document",
        "legacy_patch_namespace",
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
        "print_analysis_result",
        "print_field_provenance_summary",
        "print_historical_game_result",
        "print_historical_search_review_result",
        "print_historical_replay_coaching_result",
        "print_training_dataset_result",
        "print_training_dataset_preparation_result",
        "print_bounded_search_evaluation_result",
        "print_dataset_partition_audit_result",
        "print_rolling_opponent_policy_evaluation_result",
        "print_opponent_statistics_result",
        "print_historical_opponent_statistics_result",
        "print_fixed_three_player_historical_list_result",
        "print_fixed_three_player_historical_list_comparison_result",
        "print_multi_step_result",
        "print_policy_comparison_result",
        "run_cli",
        "main",
    )
    session_names = (
        "build_session_argument_parser",
        "parse_session_arguments",
        "load_strict_json_object",
        "run_session_cli",
        "collect_session_decision_checkpoint_v1",
        "execute_legacy_application",
        "_SessionContext",
        "_load_context",
        "_create_context",
        "_position_export_options",
        "_collect_source_play_checkpoint",
        "_collect_correction_source_checkpoint",
        "_persist_mutation",
        "_collect_for_analysis",
        "_execute_position_request",
        "_execute_historical_request",
        "_session_input_reference",
    )
    assert all(hasattr(root_cli, name) for name in root_names)
    assert all(hasattr(session_cli, name) for name in session_names)


def test_application_public_api_match_and_observed_game_do_not_import_cli() -> None:
    paths = [
        *sorted((SOURCE_ROOT / "application").rglob("*.py")),
        *sorted((SOURCE_ROOT / "api").rglob("*.py")),
        *sorted(SOURCE_ROOT.glob("match_*.py")),
        *sorted(SOURCE_ROOT.glob("observed_game_*.py")),
    ]
    violations = []
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported = tuple(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported = (node.module or "",)
            else:
                continue
            for module_name in imported:
                if module_name == "main" or module_name.startswith("skatmind.cli"):
                    violations.append((path.relative_to(PROJECT_ROOT), node.lineno, module_name))
    assert violations == []


def test_capture_web_layering_and_execution_boundaries() -> None:
    capture_root = SOURCE_ROOT / "capture_web"
    capture_paths = sorted(capture_root.glob("*.py"))
    imported = {}
    for path in capture_paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imported[path.name] = tuple(
            node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
        )
    assert "skatmind.match_capture_application" in imported["operations.py"]
    assert all(
        not any(
            module == forbidden or module.startswith(f"{forbidden}.")
            for module in modules
            for forbidden in (
                "skatmind.application",
                "skatmind.api",
                "skatmind.session",
                "skatmind.search",
                "skatmind.bounded_search",
                "skatmind.replay_coaching",
            )
        )
        for modules in imported.values()
    )
    lower_paths = [
        *sorted((SOURCE_ROOT / "application").rglob("*.py")),
        *sorted((SOURCE_ROOT / "api").rglob("*.py")),
        *sorted(SOURCE_ROOT.glob("match_*.py")),
        *sorted(SOURCE_ROOT.glob("observed_game_*.py")),
    ]
    for path in lower_paths:
        assert "skatmind.capture_web" not in path.read_text(encoding="utf-8")


def test_corpus_web_layering_and_execution_boundaries() -> None:
    corpus_root = SOURCE_ROOT / "corpus_web"
    corpus_paths = sorted(corpus_root.glob("*.py"))
    forbidden = (
        "skatmind.application",
        "skatmind.api",
        "skatmind.match_decision_analysis",
        "skatmind.match_historical_analysis",
        "skatmind.search",
        "skatmind.bounded_search",
        "skatmind.replay_coaching",
        "skatmind.cli",
    )
    violations = []
    for path in corpus_paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported = tuple(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported = (node.module or "",)
            else:
                continue
            for module_name in imported:
                if any(
                    module_name == blocked or module_name.startswith(f"{blocked}.")
                    for blocked in forbidden
                ):
                    violations.append((path.relative_to(PROJECT_ROOT), node.lineno, module_name))
    assert violations == []

    lower_paths = [
        *sorted(SOURCE_ROOT.glob("learning_corpus_*.py")),
        *sorted(SOURCE_ROOT.glob("learning_dataset_v2*.py")),
        *sorted(SOURCE_ROOT.glob("match_*.py")),
        *sorted((SOURCE_ROOT / "application").rglob("*.py")),
        *sorted((SOURCE_ROOT / "api").rglob("*.py")),
    ]
    for path in lower_paths:
        assert "skatmind.corpus_web" not in path.read_text(encoding="utf-8")

    capture_text = "".join(
        path.read_text(encoding="utf-8")
        for path in sorted((SOURCE_ROOT / "capture_web").glob("*.py"))
    )
    assert "skatmind.corpus_web" not in capture_text


def test_app_web_layering_and_startup_execution_boundaries() -> None:
    app_root = SOURCE_ROOT / "app_web"
    public_api_adapters = {
        "execution.py",
        "historical_form.py",
        "json_transfer.py",
        "managed_item_discovery.py",
        "position_form.py",
        "result_presentation.py",
        "session_form_translation.py",
        "session_frontend.py",
        "workflow_state.py",
    }
    forbidden = (
        "skatmind.application",
        "skatmind.api",
        "skatmind.session",
        "skatmind.match_capture",
        "skatmind.learning_corpus",
        "skatmind.search",
        "skatmind.bounded_search",
        "skatmind.replay_coaching",
        "skatmind.cli",
    )
    violations = []
    for path in sorted(app_root.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported = tuple(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported = (node.module or "",)
            else:
                continue
            for module_name in imported:
                if path.name in public_api_adapters and (
                    module_name == "skatmind.api.v1" or module_name.startswith("skatmind.api.v1.")
                ):
                    continue
                if any(
                    module_name == blocked or module_name.startswith(f"{blocked}.")
                    for blocked in forbidden
                ):
                    violations.append((path.relative_to(PROJECT_ROOT), node.lineno, module_name))
    assert violations == []


def test_tactical_coaching_core_is_private_transport_and_io_free() -> None:
    paths = [
        *sorted(SOURCE_ROOT.glob("learning_corpus_tactical_coaching_*.py")),
        SOURCE_ROOT / "learning_corpus_tactical_cross_game_coaching.py",
    ]
    forbidden = (
        "http",
        "pathlib",
        "socket",
        "urllib",
        "skatmind.api",
        "skatmind.capture_web",
        "skatmind.cli",
        "skatmind.corpus_web",
    )
    violations = []
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported = tuple(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported = (node.module or "",)
            else:
                continue
            for module_name in imported:
                if any(
                    module_name == blocked or module_name.startswith(f"{blocked}.")
                    for blocked in forbidden
                ):
                    violations.append((path.relative_to(PROJECT_ROOT), node.lineno, module_name))
    assert violations == []


def test_root_presentation_modules_are_transport_and_execution_free() -> None:
    presentation_root = SOURCE_ROOT / "cli" / "presentation"
    forbidden_modules = {
        "skatmind.application",
        "skatmind.api",
        "skatmind.input_loader",
        "skatmind.output_writer",
    }
    violations = []
    for path in sorted(presentation_root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported = tuple(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported = (node.module or "",)
            else:
                continue
            for module_name in imported:
                if any(
                    module_name == forbidden or module_name.startswith(f"{forbidden}.")
                    for forbidden in forbidden_modules
                ):
                    violations.append((path.relative_to(PROJECT_ROOT), node.lineno, module_name))
    assert violations == []


def test_session_assistant_uses_focused_services_not_session_facade() -> None:
    path = SOURCE_ROOT / "cli" / "session_assistant.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported_modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported_modules.append(node.module or "")
            if node.module == "skatmind.cli":
                assert all(alias.name != "session" for alias in node.names)
    assert "skatmind.cli.session" not in imported_modules


def test_focused_cli_modules_do_not_import_compatibility_facades() -> None:
    paths = [
        *sorted((SOURCE_ROOT / "cli").glob("root_*.py")),
        *sorted((SOURCE_ROOT / "cli").glob("session_*.py")),
        *sorted((SOURCE_ROOT / "cli").glob("capture*.py")),
        *sorted((SOURCE_ROOT / "cli").glob("corpus*.py")),
        *sorted((SOURCE_ROOT / "cli" / "presentation").glob("*.py")),
    ]
    violations = []
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported = tuple(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported = (node.module or "",)
                if node.module == "skatmind.cli":
                    imported += tuple(f"skatmind.cli.{alias.name}" for alias in node.names)
            else:
                continue
            for module_name in imported:
                if module_name in {
                    "skatmind.cli.execution",
                    "skatmind.cli.session",
                }:
                    violations.append((path.relative_to(PROJECT_ROOT), node.lineno, module_name))
    assert violations == []


def test_session_assistant_subcommand_retains_facade_service_seams(monkeypatch) -> None:
    import skatmind.cli.session_assistant as assistant_module

    sentinel = object()
    monkeypatch.setattr(session_cli, "_persist_mutation", sentinel)

    def run_assistant(_session_path):
        services = assistant_module._active_session_assistant_services
        assert services is not None
        assert services.persist_mutation is sentinel
        return 23

    monkeypatch.setattr(assistant_module, "run_session_assistant", run_assistant)
    assert session_cli.run_session_cli(["assistant", "--session", "private-session.json"]) == 23
    assert assistant_module._active_session_assistant_services is None


def test_ordinary_session_services_do_not_import_assistant() -> None:
    command = (
        "import sys; "
        "import skatmind.cli.session as session_cli; "
        "assert 'skatmind.cli.session_assistant' not in sys.modules; "
        "session_cli._operation_services(); "
        "assert 'skatmind.cli.session_assistant' not in sys.modules"
    )
    completed = subprocess.run(
        [sys.executable, "-c", command],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


@pytest.mark.parametrize(
    ("workflow", "runner_name"),
    [
        ("position_analysis", "run_json_position_analysis"),
        ("historical_game", "run_json_historical_game_analysis"),
        ("training_dataset", "run_json_training_dataset_conversion"),
        ("training_dataset_preparation", "run_json_training_dataset_preparation"),
        ("opponent_statistics", "run_json_opponent_statistics_conversion"),
        (
            "fixed_three_player_historical_list",
            "run_json_fixed_three_player_historical_list_analysis",
        ),
        (
            "fixed_three_player_historical_list_comparison",
            "run_json_fixed_three_player_historical_list_comparison",
        ),
    ],
)
@pytest.mark.parametrize("canonical_run", (False, True), ids=("compatibility", "run"))
def test_root_dispatch_loads_detects_and_selects_once(
    workflow: str,
    runner_name: str,
    canonical_run: bool,
    monkeypatch,
) -> None:
    calls = {"load": 0, "detect": 0, "run": 0}

    def load(_path):
        calls["load"] += 1
        return {}

    def detect(_document):
        calls["detect"] += 1
        return workflow

    def run(**_kwargs):
        calls["run"] += 1

    monkeypatch.setattr(legacy_main, "load_json_object", load)
    monkeypatch.setattr(legacy_main, "get_input_workflow", detect)
    monkeypatch.setattr(legacy_main, "validate_cli_arguments", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        legacy_main,
        "validate_training_dataset_preparation_cli_arguments",
        lambda _args: None,
    )
    monkeypatch.setattr(
        legacy_main,
        "validate_training_dataset_cli_arguments",
        lambda _args: None,
    )
    monkeypatch.setattr(
        legacy_main,
        "validate_historical_game_cli_arguments",
        lambda _args: None,
    )
    monkeypatch.setattr(
        legacy_main,
        "validate_opponent_statistics_cli_arguments",
        lambda _args: None,
    )
    monkeypatch.setattr(
        legacy_main,
        "validate_fixed_three_player_historical_list_cli_arguments",
        lambda _args: None,
    )
    monkeypatch.setattr(legacy_main, runner_name, run)

    assert (
        root_cli.run_cli(
            [*(["run"] if canonical_run else []), "--input", "input.json"],
            invocation_style="legacy",
            legacy_namespace=legacy_main,
        )
        == 0
    )
    assert calls == {"load": 1, "detect": 1, "run": 1}


@pytest.mark.parametrize(
    ("runner_name", "uses_position_loader"),
    [
        ("run_json_position_analysis", True),
        ("run_json_historical_game_analysis", False),
        ("run_json_training_dataset_conversion", False),
        ("run_json_training_dataset_preparation", False),
        ("run_json_opponent_statistics_conversion", False),
        ("run_json_fixed_three_player_historical_list_analysis", False),
        ("run_json_fixed_three_player_historical_list_comparison", False),
    ],
)
def test_each_root_transport_executes_application_once(
    runner_name: str,
    uses_position_loader: bool,
    monkeypatch,
) -> None:
    calls = {"load": 0, "execute": 0}

    def load(_path):
        calls["load"] += 1
        return {}

    def execute(*_args, **_kwargs):
        calls["execute"] += 1
        return {}, {}

    monkeypatch.setattr(root_cli, "load_json_object", load)
    if uses_position_loader:
        monkeypatch.setattr(root_cli, "load_position_from_json", load)
    monkeypatch.setattr(root_cli, "execute_legacy_application", execute)
    monkeypatch.setattr(
        root_cli,
        "validate_live_opponent_profile_options",
        lambda **_kwargs: None,
    )
    getattr(root_cli, runner_name)(file_path="input.json", quiet=True)
    assert calls == {"load": 1, "execute": 1}


def test_position_cli_preserves_omitted_and_explicit_default_option_presence(
    monkeypatch,
) -> None:
    captured: list[tuple[str, ...]] = []

    monkeypatch.setattr(root_cli, "load_json_object", lambda _path: {})
    monkeypatch.setattr(root_cli, "load_position_from_json", lambda _path: {})
    monkeypatch.setattr(
        root_cli,
        "validate_live_opponent_profile_options",
        lambda **_kwargs: None,
    )

    def execute(*_args, **kwargs):
        assert "supplied_workflow_option_names" not in kwargs
        captured.append(current_supplied_workflow_option_names())
        return {}, {}

    monkeypatch.setattr(root_cli, "execute_legacy_application", execute)

    invoke_with_supplied_root_cli_options(
        root_cli.run_json_position_analysis,
        (),
        file_path="input.json",
        quiet=True,
    )
    invoke_with_supplied_root_cli_options(
        root_cli.run_json_position_analysis,
        ("--strict-context",),
        file_path="input.json",
        quiet=True,
        strict_context=False,
    )

    assert captured == [(), ("strict_context",)]


@pytest.mark.parametrize(
    ("runner_name", "runner_kwargs", "supplied_cli_options", "expected_names"),
    (
        (
            "run_json_bounded_search_evaluation",
            {"search_seed": 17},
            (
                "--evaluate-bounded-search",
                "--search-seed",
                "--search-budget-profile",
            ),
            ("operation", "bounded_search_seed", "bounded_search_budget_profile"),
        ),
        (
            "run_json_information_set_search_evaluation",
            {"search_seed": 19},
            (
                "--information-set-search-evaluation",
                "--search-seed",
                "--search-evaluation-max-decisions",
            ),
            (
                "operation",
                "information_set_search_seed",
                "information_set_search_max_decisions",
            ),
        ),
        (
            "run_json_dataset_partition_audit",
            {"requested_mode": "known_opponent"},
            ("--audit-dataset-partitions", "--dataset-partition-mode"),
            ("operation", "partition_audit_mode"),
        ),
        (
            "run_json_rolling_opponent_policy_evaluation",
            {},
            (
                "--evaluate-opponent-policy-profiles",
                "--profile-source-partition",
            ),
            ("operation", "rolling_source_partitions"),
        ),
        (
            "run_json_rolling_opponent_policy_evaluation",
            {},
            ("--evaluate-rolling-opponent-policies",),
            ("operation",),
        ),
        (
            "run_json_historical_opponent_statistics_aggregation",
            {"before": "2026-01-01T00:00:00Z"},
            (
                "--aggregate-opponent-statistics",
                "--opponent-statistics-before",
            ),
            ("operation", "aggregation_before"),
        ),
    ),
)
def test_training_dataset_cli_preserves_exact_option_presence(
    monkeypatch,
    runner_name: str,
    runner_kwargs: dict[str, object],
    supplied_cli_options: tuple[str, ...],
    expected_names: tuple[str, ...],
) -> None:
    captured: list[tuple[str, ...]] = []
    monkeypatch.setattr(root_cli, "load_json_object", lambda _path: {})

    def execute(*_args, **kwargs):
        assert "supplied_workflow_option_names" not in kwargs
        captured.append(current_supplied_workflow_option_names())
        return {}, {}

    monkeypatch.setattr(root_cli, "execute_legacy_application", execute)
    invoke_with_supplied_root_cli_options(
        getattr(root_cli, runner_name),
        supplied_cli_options,
        file_path="input.json",
        quiet=True,
        **runner_kwargs,
    )

    assert captured == [expected_names]


def test_root_parser_retains_exact_supplied_cli_option_names() -> None:
    args = root_cli.parse_arguments(
        [
            "--input",
            "input.json",
            "--strict-context",
            "--expected-value-samples=1000",
        ]
    )

    assert args._supplied_cli_options == frozenset(
        {
            "--input",
            "--strict-context",
            "--expected-value-samples",
        }
    )


@pytest.mark.parametrize(
    "module_order",
    [
        ("skatmind.cli.execution", "skatmind.cli.session", "skatmind.cli.session_assistant"),
        ("skatmind.cli.session_assistant", "skatmind.cli.session", "skatmind.cli.execution"),
        ("skatmind.cli.session", "skatmind.cli.execution", "skatmind.cli.session_assistant"),
    ],
)
def test_cli_modules_import_without_circular_imports(module_order: tuple[str, ...]) -> None:
    command = "; ".join(
        ["import importlib", *(f"importlib.import_module({name!r})" for name in module_order)]
    )
    completed = subprocess.run(
        [sys.executable, "-c", command],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_capture_modules_import_without_circular_imports() -> None:
    command = "; ".join(
        [
            "import importlib",
            "importlib.import_module('skatmind.cli.capture')",
            "importlib.import_module('skatmind.capture_web.server')",
            "importlib.import_module('skatmind.cli.execution')",
        ]
    )
    completed = subprocess.run(
        [sys.executable, "-c", command],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_characterized_modules_are_importable_by_exact_name() -> None:
    for name in (
        "skatmind.cli.execution",
        "skatmind.cli.session",
        "skatmind.cli.session_assistant",
        "main",
    ):
        assert importlib.import_module(name) is sys.modules[name]
