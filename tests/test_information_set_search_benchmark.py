from __future__ import annotations

import ast
import copy
import hashlib
import json
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

import scripts.benchmark_information_set_search as benchmark
import skatmind
import skatmind.api.v1 as api_v1
from scripts.validate_generated_outputs_schema import SCENARIOS
from skatmind.api.v1 import WorkflowV1
from skatmind.bounded_search_information import (
    LIVE_LOCAL_VIEW_SOURCE,
    get_remaining_search_trick_count,
)
from skatmind.information_set_search_contracts import (
    INFORMATION_SET_SEARCH_BUDGET_VERSION,
    INFORMATION_SET_SEARCH_OBSERVATION_VERSION,
    INFORMATION_SET_SEARCH_POLICY_SETTINGS_VERSION,
    INFORMATION_SET_SEARCH_PREPARATION_VERSION,
    INFORMATION_SET_SEARCH_REQUEST_VERSION,
    INFORMATION_SET_SEARCH_RESULT_VERSION,
    INFORMATION_SET_SEARCH_WORLD_STATE_VERSION,
)
from skatmind.search_budget_profiles import SEARCH_BUDGET_PROFILE_IDENTIFIERS
from skatmind.settlement_normative_matrix import (
    SETTLEMENT_NORMATIVE_MATRIX_VERSION,
    get_normative_settlement_cases,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORPUS_PATH = (
    PROJECT_ROOT / "benchmarks" / "information_set_search_late_game_v1.json"
)
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "benchmark_information_set_search.py"
OLD_CORPUS_PATH = PROJECT_ROOT / "benchmarks" / "bounded_search_late_game_v1.json"
OLD_SCRIPT_PATH = PROJECT_ROOT / "scripts" / "benchmark_bounded_search.py"
CHANGELOG_PATH = PROJECT_ROOT / "CHANGELOG.md"


def _corpus() -> dict:
    return benchmark._load_corpus(CORPUS_PATH)


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _all_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value).union(*(_all_keys(item) for item in value.values()))
    if isinstance(value, list):
        return set().union(*(_all_keys(item) for item in value))
    return set()


@pytest.fixture(scope="module")
def repeated_functional_results() -> dict[str, dict]:
    results = {}
    for case in _corpus()["cases"]:
        context = benchmark._build_case_context(case)
        first, _first_timings = benchmark._execute_case(case, context)
        second, _second_timings = benchmark._execute_case(case, context)
        assert first == second
        results[case["name"]] = first
    return results


def test_benchmark_metadata_versions_identity_and_policies_are_exact() -> None:
    assert benchmark.INFORMATION_SET_SEARCH_BENCHMARK_CORPUS_SCHEMA_VERSION == 1
    assert benchmark.INFORMATION_SET_SEARCH_BENCHMARK_OUTPUT_VERSION == 1
    assert not isinstance(
        benchmark.INFORMATION_SET_SEARCH_BENCHMARK_CORPUS_SCHEMA_VERSION,
        bool,
    )
    assert not isinstance(benchmark.INFORMATION_SET_SEARCH_BENCHMARK_OUTPUT_VERSION, bool)
    assert benchmark.INFORMATION_SET_SEARCH_BENCHMARK_NAME == (
        "information_set_search_selected_world_performance_v1"
    )
    assert benchmark.INFORMATION_SET_SEARCH_BENCHMARK_CORPUS_NAME == (
        "information_set_search_late_game_v1"
    )
    assert benchmark.INFORMATION_SET_SEARCH_BENCHMARK_POLICIES == {
        "functional": "frozen_functional_and_structural_signature",
        "baseline": "same_selection_pimc_and_independent_immediate_diagnostic_only",
        "weight": "sampled_duplicate_draw_weight_is_preserved",
        "timing": "local_wall_clock_reference_without_cross_machine_gate",
        "privacy": "synthetic_fixture_without_public_or_user_data",
        "compatibility": "no_routing_profile_or_public_contract_change",
    }
    assert (
        INFORMATION_SET_SEARCH_WORLD_STATE_VERSION,
        INFORMATION_SET_SEARCH_OBSERVATION_VERSION,
        INFORMATION_SET_SEARCH_POLICY_SETTINGS_VERSION,
        INFORMATION_SET_SEARCH_BUDGET_VERSION,
        INFORMATION_SET_SEARCH_REQUEST_VERSION,
        INFORMATION_SET_SEARCH_PREPARATION_VERSION,
        INFORMATION_SET_SEARCH_RESULT_VERSION,
    ) == (1, 1, 1, 1, 1, 1, 1)


def test_strict_loader_accepts_the_canonical_finite_corpus() -> None:
    corpus = _corpus()

    assert set(corpus) == {"schema_version", "corpus_name", "cases"}
    assert corpus["schema_version"] == 1
    assert corpus["corpus_name"] == "information_set_search_late_game_v1"
    json.dumps(corpus, allow_nan=False)


def test_strict_loader_rejects_invalid_json_encodings_and_numbers(tmp_path: Path) -> None:
    raw = CORPUS_PATH.read_bytes()
    invalid_documents = {
        "bom.json": b"\xef\xbb\xbf" + raw,
        "malformed.json": b"{",
        "duplicate-key.json": raw.replace(
            b'"schema_version": 1,',
            b'"schema_version": 1, "schema_version": 1,',
            1,
        ),
        "nan.json": raw.replace(b'"schema_version": 1', b'"schema_version": NaN', 1),
        "infinity.json": raw.replace(
            b'"schema_version": 1',
            b'"schema_version": 1e9999',
            1,
        ),
        "non-object.json": b"[]",
    }
    for name, content in invalid_documents.items():
        path = tmp_path / name
        path.write_bytes(content)
        with pytest.raises(ValueError):
            benchmark._load_corpus(path)


def test_strict_loader_rejects_unknown_missing_and_invalid_fields(tmp_path: Path) -> None:
    canonical = _corpus()
    invalid_documents = []

    unknown_root = copy.deepcopy(canonical)
    unknown_root["unknown"] = None
    invalid_documents.append(unknown_root)
    missing_root = copy.deepcopy(canonical)
    del missing_root["corpus_name"]
    invalid_documents.append(missing_root)
    boolean_version = copy.deepcopy(canonical)
    boolean_version["schema_version"] = True
    invalid_documents.append(boolean_version)
    wrong_version = copy.deepcopy(canonical)
    wrong_version["schema_version"] = 2
    invalid_documents.append(wrong_version)
    empty_name = copy.deepcopy(canonical)
    empty_name["corpus_name"] = ""
    invalid_documents.append(empty_name)
    empty_cases = copy.deepcopy(canonical)
    empty_cases["cases"] = []
    invalid_documents.append(empty_cases)
    duplicate_name = copy.deepcopy(canonical)
    duplicate_name["cases"][1]["name"] = duplicate_name["cases"][0]["name"]
    invalid_documents.append(duplicate_name)
    unknown_case_field = copy.deepcopy(canonical)
    unknown_case_field["cases"][0]["unknown"] = None
    invalid_documents.append(unknown_case_field)
    unknown_profile = copy.deepcopy(canonical)
    unknown_profile["cases"][0]["profile_name"] = "unknown"
    invalid_documents.append(unknown_profile)
    incorrect_matadors = copy.deepcopy(canonical)
    incorrect_matadors["cases"][0]["declaration"]["matadors"] = 1
    invalid_documents.append(incorrect_matadors)
    invalid_policy = copy.deepcopy(canonical)
    invalid_policy["cases"][0]["fixed_player_policies"][0]["lead_policy"] = "unknown"
    invalid_documents.append(invalid_policy)
    random_policy = copy.deepcopy(canonical)
    random_policy["cases"][0]["fixed_player_policies"][0][
        "lead_policy"
    ] = "random_legal"
    invalid_documents.append(random_policy)
    malformed_expected = copy.deepcopy(canonical)
    del malformed_expected["cases"][0]["expected_information_set_signature"][
        "state_nodes_evaluated"
    ]
    invalid_documents.append(malformed_expected)
    illegal_replay = copy.deepcopy(canonical)
    illegal_replay["cases"][0]["fixture"]["replayed_cards"][:2] = ["CA", "C10"]
    invalid_documents.append(illegal_replay)
    impossible_structural_counts = copy.deepcopy(canonical)
    impossible_structural_counts["cases"][0]["expected_information_set_signature"][
        "information_sets_evaluated"
    ] = 2_000
    invalid_documents.append(impossible_structural_counts)
    candidate_denominator_mismatch = copy.deepcopy(canonical)
    candidate_denominator_mismatch["cases"][0]["expected_information_set_signature"][
        "candidate_results"
    ][0]["completed_world_count"] = 63
    invalid_documents.append(candidate_denominator_mismatch)
    invalid_strategy_card = copy.deepcopy(canonical)
    invalid_strategy_card["cases"][6]["expected_strategy_fusion_diagnostic"][
        "information_set_common_root_card"
    ] = None
    invalid_documents.append(invalid_strategy_card)
    mismatched_strategy_count = copy.deepcopy(canonical)
    mismatched_strategy_count["cases"][6]["expected_strategy_fusion_diagnostic"][
        "selected_world_count"
    ] = 31
    invalid_documents.append(mismatched_strategy_count)
    invalid_multiplicity = copy.deepcopy(canonical)
    invalid_multiplicity["cases"][7]["expected_sampled_duplicate_diagnostic"][
        "multiplicity_histogram"
    ][0]["multiplicity"] = "1"
    invalid_documents.append(invalid_multiplicity)
    mismatched_duplicate_count = copy.deepcopy(canonical)
    mismatched_duplicate_count["cases"][7]["expected_sampled_duplicate_diagnostic"][
        "sampled_world_count"
    ] = 31
    invalid_documents.append(mismatched_duplicate_count)
    mismatched_comparison = copy.deepcopy(canonical)
    mismatched_comparison["cases"][0]["expected_descriptive_comparison"][
        "information_set_pimc_same_card"
    ] = False
    invalid_documents.append(mismatched_comparison)
    mismatched_candidate_set = copy.deepcopy(canonical)
    mismatched_candidate_set["cases"][0]["expected_immediate_signature"][
        "candidate_order"
    ][0] = "HA"
    invalid_documents.append(mismatched_candidate_set)

    for index, document in enumerate(invalid_documents):
        path = tmp_path / f"invalid-{index}.json"
        _write_json(path, document)
        with pytest.raises(ValueError):
            benchmark._load_corpus(path)


def test_exact_case_order_and_complete_contract_turn_coverage() -> None:
    cases = _corpus()["cases"]
    assert tuple(case["name"] for case in cases) == (
        "clubs_declarer_lead_sampled_three_tricks",
        "grand_defender_second_seat_exhaustive_two_tricks",
        "null_defender_third_seat_exhaustive_one_trick",
        "null_hand_declarer_lead_exhaustive_two_tricks",
        "null_ouvert_defender_second_seat_sampled_two_tricks",
        "null_hand_ouvert_declarer_third_seat_exhaustive_one_trick",
        "clubs_strategy_fusion_sampled_two_tricks",
        "grand_sampled_duplicate_weight_two_tricks",
    )

    contract_variants = set()
    current_trick_sizes = set()
    remaining_tricks = set()
    for case in cases:
        declaration = case["declaration"]
        if declaration["game_type"] != "null":
            contract_variants.add(
                "Suit" if declaration["game_type"] == "clubs" else "Grand"
            )
        elif declaration["hand_game"] and declaration["ouvert"]:
            contract_variants.add("Null Hand Ouvert")
        elif declaration["hand_game"]:
            contract_variants.add("Null Hand")
        elif declaration["ouvert"]:
            contract_variants.add("Null Ouvert")
        else:
            contract_variants.add("Null")
        context = benchmark._build_case_context(case)
        current_trick_sizes.add(len(context.information_view.current_trick))
        remaining_tricks.add(get_remaining_search_trick_count(context.information_view))

    assert contract_variants == {
        "Suit",
        "Grand",
        "Null",
        "Null Hand",
        "Null Ouvert",
        "Null Hand Ouvert",
    }
    assert {case["actor"]["player_role"] for case in cases} == {
        "declarer",
        "defender",
    }
    assert {case["actor"]["turn_phase"] for case in cases} == {
        "lead",
        "second_seat",
        "third_seat",
    }
    assert current_trick_sizes == {0, 1, 2}
    assert remaining_tricks == {1, 2, 3}
    assert {case["profile_name"] for case in cases} == set(
        SEARCH_BUDGET_PROFILE_IDENTIFIERS
    )
    assert {
        case["expected_information_set_signature"]["world_coverage"]
        for case in cases
    } == {"all_compatible_worlds", "sampled_compatible_worlds"}


def test_named_sampled_ouvert_case_truthfully_freezes_exhaustive_selection() -> None:
    case = next(
        case
        for case in _corpus()["cases"]
        if case["name"] == "null_ouvert_defender_second_seat_sampled_two_tricks"
    )
    signature = case["expected_information_set_signature"]

    assert case["profile_name"] == "interactive_v1"
    assert signature["compatible_world_count"] == 3
    assert signature["world_coverage"] == "all_compatible_worlds"
    assert signature["selected_world_count"] == 3
    assert signature["sampled_world_count"] == 0


def test_synthetic_fixtures_build_only_safe_live_information_views() -> None:
    for case in _corpus()["cases"]:
        context = benchmark._build_case_context(case)
        view = context.information_view
        public_players = {
            constraint.player for constraint in context.public_hand_constraints
        }
        assert view.source == LIVE_LOCAL_VIEW_SOURCE
        assert view.perspective_player == view.next_player == "me"
        assert view.local_remaining_hand == tuple(context.immediate_state.hand)
        assert all(
            not constraint.exact_cards
            or constraint.player == "me"
            or constraint.player in public_players
            for constraint in view.hidden_card_constraints
        )
        assert not hasattr(context.immediate_state, "left_hand")
        assert not hasattr(context.immediate_state, "right_hand")


def test_every_case_matches_all_frozen_functional_and_structural_signatures(
    repeated_functional_results: dict[str, dict],
) -> None:
    for case in _corpus()["cases"]:
        assert repeated_functional_results[case["name"]] == (
            benchmark._expected_functional_bundle(case)
        )
        information = repeated_functional_results[case["name"]][
            "information_set_signature"
        ]
        assert information["status"] == "complete"
        assert all(
            candidate["completed_world_count"] == information["completed_world_count"]
            for candidate in information["candidate_results"]
        )
        assert information["recommended_card"] == information["candidate_results"][0][
            "card"
        ]


def test_baselines_and_descriptive_comparisons_are_frozen_diagnostics_only(
    repeated_functional_results: dict[str, dict],
) -> None:
    comparison_values = set()
    for result in repeated_functional_results.values():
        information = result["information_set_signature"]
        pimc = result["same_selection_pimc_signature"]
        immediate = result["immediate_signature"]
        comparison = result["descriptive_comparison"]
        comparison_values.add(comparison["information_set_pimc_same_card"])
        assert pimc["status"] == "complete"
        assert information["selected_world_count"] == pimc["selected_world_count"]
        assert information["sampled_world_count"] == pimc["sampled_world_count"]
        assert immediate["recommended_card"] in immediate["candidate_order"]
        assert comparison["information_set_pimc_same_card"] == (
            information["recommended_card"] == pimc["recommended_card"]
        )
        assert comparison["information_set_immediate_same_card"] == (
            information["recommended_card"] == immediate["recommended_card"]
        )
        assert "fallback" not in comparison
        assert "accuracy" not in comparison
        assert "correctness" not in comparison
    assert comparison_values == {False, True}


def test_strategy_fusion_case_is_aggregate_only_and_uses_one_common_action(
    repeated_functional_results: dict[str, dict],
) -> None:
    result = repeated_functional_results[
        "clubs_strategy_fusion_sampled_two_tricks"
    ]
    diagnostic = result["strategy_fusion_diagnostic"]

    assert diagnostic == {
        "equal_controlled_root_observation": True,
        "selected_world_count": 32,
        "unique_exact_worlds_evaluated": 30,
        "distinct_world_preferred_card_count": 2,
        "world_preferred_card_counts": [
            {"card": "DA", "count": 30},
            {"card": "DQ", "count": 2},
        ],
        "information_set_common_root_card": "DA",
        "information_set_root_decision_count": 1,
        "information_set_root_reached_world_count": 32,
    }
    assert {
        "world_id",
        "world_index",
        "exact_state",
        "hand",
        "hands",
        "observation",
        "controlled_policy",
    }.isdisjoint(_all_keys(diagnostic))


def test_sampled_duplicate_case_preserves_repeated_draw_weight(
    repeated_functional_results: dict[str, dict],
) -> None:
    result = repeated_functional_results[
        "grand_sampled_duplicate_weight_two_tricks"
    ]
    information = result["information_set_signature"]
    diagnostic = result["sampled_duplicate_diagnostic"]

    assert information["sampled_world_count"] == 32
    assert information["unique_sampled_world_count"] == 28
    assert diagnostic["duplicate_draw_count"] == 4
    assert diagnostic["maximum_draw_multiplicity"] == 2
    assert diagnostic["multiplicity_histogram"] == [
        {"multiplicity": 1, "world_count": 24},
        {"multiplicity": 2, "world_count": 4},
    ]
    assert diagnostic["candidate_completed_world_counts"] == [
        {"card": "DK", "count": 32},
        {"card": "D9", "count": 32},
    ]
    assert diagnostic["root_reached_world_count"] == 32
    assert diagnostic["selected_draw_weight_preserved"] is True


def test_runner_selected_case_output_shape_and_no_file_output(tmp_path: Path) -> None:
    before = set(tmp_path.iterdir())
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--corpus",
            str(CORPUS_PATH),
            "--warmup-runs",
            "0",
            "--runs",
            "2",
            "--case",
            "null_defender_third_seat_exhaustive_one_trick",
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.endswith("\n")
    output = json.loads(completed.stdout)
    assert set(output) == {
        "schema_version",
        "benchmark_name",
        "corpus",
        "policies",
        "profile_names",
        "warmup_run_count",
        "measured_run_count",
        "environment",
        "cases",
        "aggregate",
    }
    assert output["schema_version"] == 1
    assert output["benchmark_name"] == (
        "information_set_search_selected_world_performance_v1"
    )
    assert output["corpus"]["name"] == "information_set_search_late_game_v1"
    assert output["corpus"]["path"] == CORPUS_PATH.name
    assert output["policies"] == benchmark.INFORMATION_SET_SEARCH_BENCHMARK_POLICIES
    assert output["profile_names"] == ["interactive_v1"]
    assert output["warmup_run_count"] == 0
    assert output["measured_run_count"] == 2
    assert set(output["environment"]) == {
        "platform",
        "system",
        "release",
        "machine",
        "processor",
        "python_version",
        "python_implementation",
        "python_executable",
    }
    assert output["environment"]["python_executable"] == Path(sys.executable).name
    assert not Path(output["corpus"]["path"]).is_absolute()
    assert not Path(output["environment"]["python_executable"]).is_absolute()
    assert output["aggregate"]["measured_execution_count"] == 2
    assert len(output["cases"]) == 1
    assert len(output["cases"][0]["runs"]) == 2
    assert set(output["cases"][0]["timing_ms"]) == {
        "preparation",
        "information_set_execution",
        "information_set_total",
        "same_selection_pimc",
        "immediate",
    }
    assert set(output["cases"][0]["structural_work"]) == set(
        benchmark._STRUCTURAL_FIELDS
    )
    assert all(
        summary["deterministic_within_each_case"] is True
        for summary in output["aggregate"]["structural_work"].values()
    )
    assert set(tmp_path.iterdir()) == before


def test_runner_rejects_invalid_arguments_and_unknown_case() -> None:
    with pytest.raises(ValueError, match="warmup_run_count"):
        benchmark.run_benchmark(warmup_run_count=-1, measured_run_count=2)
    with pytest.raises(ValueError, match="measured_run_count"):
        benchmark.run_benchmark(warmup_run_count=0, measured_run_count=1)
    with pytest.raises(ValueError, match="Unknown Information-set benchmark case"):
        benchmark.run_benchmark(
            warmup_run_count=0,
            measured_run_count=2,
            case_name="unknown",
        )
    assert benchmark.DEFAULT_CORPUS_PATH == CORPUS_PATH


def test_runner_stage_summaries_use_patchable_performance_clock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    milliseconds = 1_000_000
    clock_values = iter(
        (
            0,
            1 * milliseconds,
            1 * milliseconds,
            3 * milliseconds,
            3 * milliseconds,
            6 * milliseconds,
            6 * milliseconds,
            10 * milliseconds,
            10 * milliseconds,
            12 * milliseconds,
            12 * milliseconds,
            16 * milliseconds,
            16 * milliseconds,
            22 * milliseconds,
            22 * milliseconds,
            30 * milliseconds,
        )
    )
    monkeypatch.setattr(benchmark, "_performance_clock_ns", lambda: next(clock_values))

    output = benchmark.run_benchmark(
        warmup_run_count=0,
        measured_run_count=2,
        case_name="null_defender_third_seat_exhaustive_one_trick",
    )
    timing = output["cases"][0]["timing_ms"]

    assert timing == {
        "preparation": {"minimum": 1.0, "median": 1.5, "mean": 1.5, "maximum": 2.0},
        "information_set_execution": {
            "minimum": 2.0,
            "median": 3.0,
            "mean": 3.0,
            "maximum": 4.0,
        },
        "information_set_total": {
            "minimum": 3.0,
            "median": 4.5,
            "mean": 4.5,
            "maximum": 6.0,
        },
        "same_selection_pimc": {
            "minimum": 3.0,
            "median": 4.5,
            "mean": 4.5,
            "maximum": 6.0,
        },
        "immediate": {"minimum": 4.0, "median": 6.0, "mean": 6.0, "maximum": 8.0},
    }
    assert output["cases"][0]["local_timing_ratios"] == {
        "information_set_execution_to_pimc_median_ratio": 0.667,
        "information_set_total_to_immediate_median_ratio": 0.75,
    }


def test_runner_freezes_operational_timeouts_without_changing_profiles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import skatmind.compatible_world_minimax as compatible_world_minimax
    import skatmind.information_set_search_executor as information_set_search_executor
    import skatmind.perfect_information_minimax as perfect_information_minimax
    from skatmind.search_budget_profiles import get_information_set_search_budget_profile

    def unexpected_operational_clock() -> float:
        raise AssertionError("Benchmark execution used a production timeout clock.")

    for module in (
        compatible_world_minimax,
        information_set_search_executor,
        perfect_information_minimax,
    ):
        monkeypatch.setattr(module, "_monotonic", unexpected_operational_clock)

    case = next(
        case
        for case in _corpus()["cases"]
        if case["name"] == "clubs_strategy_fusion_sampled_two_tricks"
    )
    profile = get_information_set_search_budget_profile(case["profile_name"])
    result, _timings = benchmark._execute_case(
        case,
        benchmark._build_case_context(case),
    )

    assert profile.wall_clock_timeout_ms == 1_000
    assert result["information_set_signature"]["status"] == "complete"


def test_runner_has_no_latency_threshold_percentile_or_sleep() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    calls = {
        node.func.id if isinstance(node.func, ast.Name) else node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, (ast.Name, ast.Attribute))
    }

    assert "sleep" not in calls
    assert "p95" not in source.lower()
    assert "p99" not in source.lower()
    assert "percentile" not in source.lower()
    assert "latency_threshold" not in source.lower()


def test_existing_pimc_benchmark_corpus_and_renamed_runner_entry_are_exact() -> None:
    assert hashlib.sha256(OLD_CORPUS_PATH.read_bytes()).hexdigest().upper() == (
        "7A76152CDC2BA36BD4BBB1FDD29CEBA30D760A97D410EA9B4E61122ABD2D700D"
    )
    assert hashlib.sha256(OLD_SCRIPT_PATH.read_bytes()).hexdigest().upper() == (
        "3E1FB236AAE0C37BD8F057A501DCC2C5DCC2C414DA2C83823C1A029418E3501E"
    )
    old_source = OLD_SCRIPT_PATH.read_text(encoding="utf-8")
    assert "from skatmind.search_budget_profiles import" in old_source
    assert '"bounded_search_compatible_world_performance_v1"' in old_source
    assert 'parser.add_argument("--corpus"' in old_source
    assert 'parser.add_argument("--warmup-runs"' in old_source
    assert 'parser.add_argument("--runs"' in old_source
    assert 'parser.add_argument("--case"' not in old_source


def test_benchmark_privacy_import_and_packaging_boundaries_are_private() -> None:
    tree = ast.parse(SCRIPT_PATH.read_text(encoding="utf-8"))
    imports = tuple(
        imported
        for node in ast.walk(tree)
        for imported in (
            (node.module or "",)
            if isinstance(node, ast.ImportFrom)
            else tuple(alias.name for alias in node.names)
            if isinstance(node, ast.Import)
            else ()
        )
    )
    forbidden_fragments = (
        "skatmind.api",
        "skatmind.cli",
        "skatmind.match",
        "skatmind.capture",
        "skatmind.corpus",
    )
    assert not any(
        fragment in imported for fragment in forbidden_fragments for imported in imports
    )
    assert {"requests", "socket", "urllib"}.isdisjoint(
        imported.split(".", maxsplit=1)[0] for imported in imports
    )

    output = benchmark.run_benchmark(
        warmup_run_count=0,
        measured_run_count=2,
        case_name="clubs_strategy_fusion_sampled_two_tricks",
    )
    assert {
        "controlled_policy",
        "information_set",
        "observation",
        "exact_state",
        "exact_states",
        "world_state",
        "world_states",
        "world_id",
        "world_index",
        "hands",
        "left_hand",
        "right_hand",
    }.isdisjoint(_all_keys(output))

    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    package_data = pyproject["tool"]["setuptools"]["package-data"]
    assert not any(
        "benchmark" in pattern
        for patterns in package_data.values()
        for pattern in patterns
    )
    assert pyproject["project"]["scripts"] == {"skatmind": "skatmind.cli:main"}


def test_package_public_artifact_and_changelog_baselines_are_unchanged() -> None:
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = pyproject["project"]

    assert project["version"] == skatmind.__version__ == "0.17.0"
    assert project["requires-python"] == ">=3.13"
    assert project["scripts"] == {"skatmind": "skatmind.cli:main"}
    assert api_v1.PUBLIC_API_CONTRACT_VERSION == 1
    assert len(WorkflowV1) == 7
    assert not any("BENCHMARK" in name for name in api_v1.__all__)
    assert SETTLEMENT_NORMATIVE_MATRIX_VERSION == 3
    assert len(get_normative_settlement_cases()) == 61
    assert len(tuple((PROJECT_ROOT / "schemas").glob("*.schema.json"))) == 71
    assert (
        len(
            tuple(
                (PROJECT_ROOT / "src" / "skatmind" / "schema_resources").glob(
                    "*.schema.json"
                )
            )
        )
        == 71
    )
    assert len(tuple((PROJECT_ROOT / "examples").glob("session_*.json"))) == 6
    assert len(SCENARIOS) == 98
    assert hashlib.sha256(CHANGELOG_PATH.read_bytes()).hexdigest().upper() == (
        "A0C06B51FC41D7C7C1BE8F60684EA5E378E9D759748F24FAF3AA205172C1D178"
    )
