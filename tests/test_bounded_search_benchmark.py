from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.benchmark_bounded_search import _build_information_view
from skat_ai.bounded_search_information import LIVE_LOCAL_VIEW_SOURCE
from skat_ai.search_budget_profiles import SEARCH_BUDGET_PROFILE_IDENTIFIERS

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORPUS_PATH = PROJECT_ROOT / "benchmarks" / "bounded_search_late_game_v1.json"
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "benchmark_bounded_search.py"


def _load_corpus() -> dict:
    with CORPUS_PATH.open(encoding="utf-8") as file:
        return json.load(file)


def test_benchmark_corpus_has_supported_declarations_and_named_profiles() -> None:
    corpus = _load_corpus()

    assert corpus["schema_version"] == 1
    assert corpus["corpus_name"] == "bounded_search_late_game_v1"
    assert {case["declaration"]["game_type"] for case in corpus["cases"]} == {
        "clubs",
        "grand",
        "null",
    }
    assert {case["profile_name"] for case in corpus["cases"]} == set(
        SEARCH_BUDGET_PROFILE_IDENTIFIERS
    )
    assert len({case["name"] for case in corpus["cases"]}) == len(corpus["cases"])

    for case in corpus["cases"]:
        declaration = case["declaration"]
        information_view = _build_information_view(case)
        assert set(declaration) == {
            "game_type",
            "hand_game",
            "ouvert",
            "schneider_announced",
            "schwarz_announced",
            "matadors",
            "bid_value",
        }
        assert all(
            isinstance(declaration[field], bool)
            for field in (
                "hand_game",
                "ouvert",
                "schneider_announced",
                "schwarz_announced",
            )
        )
        assert (declaration["matadors"] is None) == (declaration["game_type"] == "null")
        assert information_view.source == LIVE_LOCAL_VIEW_SOURCE
        assert all(
            not constraint.forbidden_effective_categories
            for constraint in information_view.hidden_card_constraints
        )


def test_benchmark_script_is_runnable_and_reports_deterministic_results() -> None:
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
        ],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )

    assert completed.returncode == 0, completed.stderr
    output = json.loads(completed.stdout)
    assert output["schema_version"] == 1
    assert output["benchmark_name"] == "bounded_search_compatible_world_performance_v1"
    assert output["corpus"]["name"] == "bounded_search_late_game_v1"
    assert output["profile_names"] == list(SEARCH_BUDGET_PROFILE_IDENTIFIERS)
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
    assert output["aggregate"]["measured_execution_count"] == 6
    assert output["aggregate"]["timing_ms"]["total"] >= 0
    assert output["aggregate"]["nodes_expanded"]["total"] > 0

    expected_by_name = {case["name"]: case["expected_result"] for case in _load_corpus()["cases"]}
    coverages = set()
    for case in output["cases"]:
        expected = expected_by_name[case["case_name"]]
        functional = case["functional_result"]
        coverages.add(functional["world_coverage"])
        assert functional == expected
        assert case["deterministic_across_measured_runs"] is True
        assert case["nodes_expanded"]["deterministic"] is True
        assert len(case["runs"]) == 2
        assert {run["nodes_expanded"] for run in case["runs"]} == {expected["nodes_expanded"]}
        assert all(run["elapsed_ms"] >= 0 for run in case["runs"])

    assert coverages == {"all_compatible_worlds", "sampled_compatible_worlds"}
