import copy
import json
import subprocess
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from test_input_schema import INPUT_VALIDATOR
from test_output_schema import OUTPUT_VALIDATOR

import main as main_module
from scripts.validate_generated_outputs_schema import SCENARIOS
from skat_ai.fixed_three_player_historical_list_request import (
    build_fixed_three_player_historical_list_analysis_request,
    build_fixed_three_player_historical_list_comparison_request,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMAS_DIR = PROJECT_ROOT / "schemas"
MIXED_PATH = PROJECT_ROOT / "examples" / "fixed_three_player_historical_list_mixed.json"
ALL_PASSED_PATH = (
    PROJECT_ROOT / "examples" / "fixed_three_player_historical_list_all_passed.json"
)
COMPARISON_PATH = (
    PROJECT_ROOT / "examples" / "fixed_three_player_historical_list_comparison.json"
)

UNSUPPORTED_LIST_CLI_ARGUMENTS = (
    ("--samples", "1"),
    ("--seed", "1"),
    ("--opponent-strategy", "basic"),
    ("--audit-dataset-partitions",),
    ("--dataset-partition-mode", "report_only"),
    ("--aggregate-opponent-statistics",),
    ("--opponent-statistics-partition", "train"),
    ("--opponent-statistics-before", "2026-07-25T00:00:00Z"),
    ("--export-opponent-statistics", "unused.json"),
    ("--evaluate-opponent-policy-profiles",),
    ("--evaluate-rolling-opponent-policies",),
    ("--profile-source-partition", "train"),
    ("--profile-evaluation-partition", "validation"),
    ("--historical-decision-snapshots",),
    ("--historical-game-review",),
    ("--historical-search-review",),
    ("--historical-replay-coaching",),
    ("--search-seed", "1"),
    ("--search-budget-profile", "interactive_v1"),
    ("--evaluate-bounded-search",),
    ("--search-evaluation-partition", "test"),
    ("--search-evaluation-max-decisions", "1"),
    ("--multi-step", "1"),
    ("--card-policy", "first_legal"),
    ("--expected-value-samples", "1"),
    ("--strict-context",),
    ("--compare-policies",),
    ("--comparison-only",),
    ("--opponent-lead-policy", "lowest_point"),
    ("--opponent-response-policy", "lowest_point"),
    ("--opponent-policy-preset", "simple_lowest"),
    ("--use-profile-presets",),
    ("--opponent-statistics-file", "unused.json"),
    ("--left-opponent-player-id", "left-player"),
    ("--right-opponent-player-id", "right-player"),
    ("--left-opponent-lead-policy", "lowest_point"),
    ("--left-opponent-response-policy", "lowest_point"),
    ("--right-opponent-lead-policy", "lowest_point"),
    ("--right-opponent-response-policy", "lowest_point"),
)

SCHEMA_NAMES = (
    "fixed_three_player_historical_list.schema.json",
    "fixed_three_player_historical_list_input.schema.json",
    "fixed_three_player_historical_list_comparison_input.schema.json",
    "fixed_three_player_historical_list_aggregation.schema.json",
    "fixed_three_player_historical_list_comparison.schema.json",
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


SCHEMAS = {
    name: load_json(SCHEMAS_DIR / name)
    for name in (
        *SCHEMA_NAMES,
        "historical_game.schema.json",
        "historical_game_end.schema.json",
        "historical_game_event.schema.json",
        "historical_declarer_concession.schema.json",
        "historical_defender_concession.schema.json",
        "historical_declarer_card_exposure.schema.json",
        "historical_defender_open_play.schema.json",
        "historical_open_card_throw.schema.json",
        "historical_party_wide_claim.schema.json",
        "historical_defender_open_play_continuation_event.schema.json",
        "historical_declarer_card_exposure_continuation_event.schema.json",
    )
}
SCHEMA_REGISTRY = Registry().with_resources(
    [
        (schema["$id"], Resource.from_contents(schema))
        for schema in SCHEMAS.values()
    ]
)


def validator(name: str) -> Draft202012Validator:
    return Draft202012Validator(
        SCHEMAS[name],
        registry=SCHEMA_REGISTRY,
        format_checker=FormatChecker(),
    )


def run_cli(*args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "main.py"), *(str(arg) for arg in args)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def build_output(input_path: Path, output_path: Path) -> dict[str, Any]:
    data = load_json(input_path)
    if "fixed_three_player_historical_list_input" in data:
        main_module.run_json_fixed_three_player_historical_list_analysis(
            str(input_path),
            output_path=str(output_path),
            quiet=True,
        )
    else:
        main_module.run_json_fixed_three_player_historical_list_comparison(
            str(input_path),
            output_path=str(output_path),
            quiet=True,
        )
    return load_json(output_path)


def collect_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value).union(*(collect_keys(child) for child in value.values()))
    if isinstance(value, list):
        return set().union(*(collect_keys(child) for child in value))
    return set()


def test_all_five_public_list_schemas_are_strict_draft_2020_12() -> None:
    for name in SCHEMA_NAMES:
        schema = SCHEMAS[name]
        Draft202012Validator.check_schema(schema)
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["$id"] == f"https://example.local/skat-ai/{name}"
        assert schema["additionalProperties"] is False


def test_input_schemas_accept_all_three_public_examples() -> None:
    for path in (MIXED_PATH, ALL_PASSED_PATH, COMPARISON_PATH):
        assert list(INPUT_VALIDATOR.iter_errors(load_json(path))) == []


def test_source_schema_enforces_cardinality_and_strict_entry_union() -> None:
    request = load_json(MIXED_PATH)["fixed_three_player_historical_list_input"]
    historical_list = request["historical_list"]
    list_validator = validator("fixed_three_player_historical_list.schema.json")

    assert list(list_validator.iter_errors(historical_list)) == []
    for field_name in ("players", "entries"):
        invalid = copy.deepcopy(historical_list)
        invalid[field_name].pop()
        assert list(list_validator.iter_errors(invalid))

    passed_with_played_field = copy.deepcopy(historical_list)
    passed_with_played_field["entries"][1]["historical_game"] = {}
    assert list(list_validator.iter_errors(passed_with_played_field))

    played_with_passed_field = copy.deepcopy(historical_list)
    played_with_passed_field["entries"][0]["played_at"] = None
    assert list(list_validator.iter_errors(played_with_passed_field))

    recursive_unknown = copy.deepcopy(historical_list)
    recursive_unknown["entries"][0]["historical_game"]["unknown"] = True
    assert list(list_validator.iter_errors(recursive_unknown))

    explicit_null_label = copy.deepcopy(historical_list)
    explicit_null_label["players"][2]["player_label"] = None
    assert list(list_validator.iter_errors(explicit_null_label)) == []
    wrapped_request = copy.deepcopy(
        load_json(MIXED_PATH)["fixed_three_player_historical_list_input"]
    )
    wrapped_request["historical_list"] = explicit_null_label
    request = build_fixed_three_player_historical_list_analysis_request(wrapped_request)
    assert request.historical_list.players[2].player_label is None


def test_request_schemas_require_explicit_nullable_lots_and_two_sources() -> None:
    mixed_request = load_json(MIXED_PATH)["fixed_three_player_historical_list_input"]
    request_validator = validator(
        "fixed_three_player_historical_list_input.schema.json"
    )
    assert list(request_validator.iter_errors(mixed_request)) == []

    missing_lot = copy.deepcopy(mixed_request)
    missing_lot.pop("lot_order")
    assert list(request_validator.iter_errors(missing_lot))

    nullable_lot = copy.deepcopy(mixed_request)
    nullable_lot["lot_order"] = None
    assert list(request_validator.iter_errors(nullable_lot)) == []

    comparison = load_json(COMPARISON_PATH)[
        "fixed_three_player_historical_list_comparison_input"
    ]
    comparison_validator = validator(
        "fixed_three_player_historical_list_comparison_input.schema.json"
    )
    assert list(comparison_validator.iter_errors(comparison)) == []
    comparison["lists"].pop()
    assert list(comparison_validator.iter_errors(comparison))


def test_public_requests_are_frozen_and_defensively_copy_arrays() -> None:
    raw_request = load_json(MIXED_PATH)["fixed_three_player_historical_list_input"]
    request = build_fixed_three_player_historical_list_analysis_request(raw_request)
    raw_request["lot_order"].append("player-b")
    raw_request["historical_list"]["entries"].clear()

    assert request.lot_order == ("player-a", "player-c")
    assert len(request.historical_list.entries) == 36
    with pytest.raises(FrozenInstanceError):
        request.schema_version = 2

    raw_comparison = load_json(COMPARISON_PATH)[
        "fixed_three_player_historical_list_comparison_input"
    ]
    comparison = build_fixed_three_player_historical_list_comparison_request(
        raw_comparison
    )
    raw_comparison["lists"].clear()

    assert len(comparison.lists) == 2
    with pytest.raises(FrozenInstanceError):
        comparison.lists = ()


def test_single_execution_emits_complete_schema_valid_root(tmp_path: Path) -> None:
    output_path = tmp_path / "list.json"
    data = build_output(MIXED_PATH, output_path)

    assert set(data) == {"input_file", "fixed_three_player_historical_list_summary"}
    summary = data["fixed_three_player_historical_list_summary"]
    assert len(summary["progression"]) == 36
    assert len(summary["player_totals"]) == 3
    assert len(summary["final_standings"]) == 3
    assert list(OUTPUT_VALIDATOR.iter_errors(data)) == []
    assert list(
        validator("fixed_three_player_historical_list_aggregation.schema.json").iter_errors(
            summary
        )
    ) == []


def test_comparison_aggregates_each_source_once_and_compares_once(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    aggregation_calls = 0
    comparison_calls = 0
    real_aggregate = main_module.build_fixed_three_player_historical_list_aggregation
    real_compare = main_module.build_fixed_three_player_historical_list_comparison

    def counted_aggregate(*args: Any, **kwargs: Any):
        nonlocal aggregation_calls
        aggregation_calls += 1
        return real_aggregate(*args, **kwargs)

    def counted_compare(*args: Any, **kwargs: Any):
        nonlocal comparison_calls
        comparison_calls += 1
        return real_compare(*args, **kwargs)

    monkeypatch.setattr(
        main_module,
        "build_fixed_three_player_historical_list_aggregation",
        counted_aggregate,
    )
    monkeypatch.setattr(
        main_module,
        "build_fixed_three_player_historical_list_comparison",
        counted_compare,
    )
    data = build_output(COMPARISON_PATH, tmp_path / "comparison.json")

    assert aggregation_calls == 2
    assert comparison_calls == 1
    assert set(data) == {
        "input_file",
        "fixed_three_player_historical_list_comparison_summary",
    }
    assert list(OUTPUT_VALIDATOR.iter_errors(data)) == []


def test_output_schemas_reject_recursive_unknown_fields(tmp_path: Path) -> None:
    aggregation = build_output(MIXED_PATH, tmp_path / "list.json")[
        "fixed_three_player_historical_list_summary"
    ]
    aggregation["progression"][0]["entry_fact"]["unknown"] = True
    assert list(
        validator("fixed_three_player_historical_list_aggregation.schema.json").iter_errors(
            aggregation
        )
    )

    comparison = build_output(COMPARISON_PATH, tmp_path / "comparison.json")[
        "fixed_three_player_historical_list_comparison_summary"
    ]
    comparison["source_lists"][0]["progression"] = []
    assert list(
        validator("fixed_three_player_historical_list_comparison.schema.json").iter_errors(
            comparison
        )
    )


def test_root_schemas_use_external_list_schema_references() -> None:
    input_schema = load_json(SCHEMAS_DIR / "input.schema.json")
    output_schema = load_json(SCHEMAS_DIR / "output.schema.json")

    assert input_schema["properties"]["fixed_three_player_historical_list_input"][
        "$ref"
    ].endswith("fixed_three_player_historical_list_input.schema.json")
    assert input_schema["properties"][
        "fixed_three_player_historical_list_comparison_input"
    ]["$ref"].endswith("fixed_three_player_historical_list_comparison_input.schema.json")
    assert output_schema["properties"]["fixed_three_player_historical_list_summary"][
        "$ref"
    ].endswith("fixed_three_player_historical_list_aggregation.schema.json")
    assert output_schema["properties"][
        "fixed_three_player_historical_list_comparison_summary"
    ]["$ref"].endswith("fixed_three_player_historical_list_comparison.schema.json")


def test_public_outputs_exclude_private_source_and_search_state(tmp_path: Path) -> None:
    forbidden = {
        "historical_game",
        "record",
        "hand",
        "initial_hand",
        "skat",
        "discarded_cards",
        "tricks",
        "plays",
        "ownership",
        "search_state",
        "proof_state",
    }
    aggregation = build_output(MIXED_PATH, tmp_path / "list.json")
    comparison = build_output(COMPARISON_PATH, tmp_path / "comparison.json")

    assert collect_keys(aggregation).isdisjoint(forbidden)
    assert collect_keys(comparison).isdisjoint(forbidden)
    assert "progression" not in comparison[
        "fixed_three_player_historical_list_comparison_summary"
    ]
    assert "entry_fact" not in collect_keys(comparison)


def test_single_list_cli_prints_twelve_round_ends_and_lot_wording() -> None:
    mixed = run_cli("--input", MIXED_PATH)
    all_passed = run_cli("--input", ALL_PASSED_PATH)

    assert mixed.returncode == 0
    assert mixed.stderr == ""
    assert "Fixed three-player historical list summary" in mixed.stdout
    assert "Applied external lot: player-a, player-c" in mixed.stdout
    assert sum(line.startswith("Entry ") for line in mixed.stdout.splitlines()) == 12
    for entry_number in range(3, 37, 3):
        assert f"Entry {entry_number} (round {entry_number // 3}):" in mixed.stdout

    assert all_passed.returncode == 0
    assert "Ranking status: lot_required" in all_passed.stdout
    assert "Unresolved tie; external lot required: player-a, player-b, player-c" in (
        all_passed.stdout
    )


def test_comparison_cli_prints_deltas_places_and_rank_status_without_claims() -> None:
    completed = run_cli("--input", COMPARISON_PATH)

    assert completed.returncode == 0
    assert completed.stderr == ""
    for expected in (
        "Fixed three-player historical list comparison",
        "Reference list: comparison-reference-001",
        "Source-list count: 2",
        "Played Games +1; Passed Deals -1",
        "reference table place place_1; comparison table place place_2",
        "Rank status: available",
        "rank-position change +1",
    ):
        assert expected in completed.stdout
    lower_output = completed.stdout.lower()
    for prohibited in (
        "better player",
        "skill",
        "series winner",
        "winner analysis",
        "recommended list",
        "official cross-list ranking",
    ):
        assert prohibited not in lower_output


@pytest.mark.parametrize("input_path", [MIXED_PATH, COMPARISON_PATH])
def test_public_list_cli_quiet_mode_and_output_files(
    input_path: Path,
    tmp_path: Path,
) -> None:
    output_path = tmp_path / f"{input_path.stem}.output.json"
    completed = run_cli(
        "--input",
        input_path,
        "--output",
        output_path,
        "--quiet",
    )

    assert completed.returncode == 0
    assert completed.stdout == ""
    assert completed.stderr == ""
    assert output_path.exists()
    assert list(OUTPUT_VALIDATOR.iter_errors(load_json(output_path))) == []


@pytest.mark.parametrize("input_path", [MIXED_PATH, COMPARISON_PATH])
@pytest.mark.parametrize(
    "option_args",
    UNSUPPORTED_LIST_CLI_ARGUMENTS,
    ids=[arguments[0] for arguments in UNSUPPORTED_LIST_CLI_ARGUMENTS],
)
def test_public_list_cli_rejects_each_non_file_option(
    input_path: Path,
    option_args: tuple[str, ...],
) -> None:
    completed = run_cli("--input", input_path, *option_args)

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert "CLI error:" in completed.stderr


def test_generated_output_matrix_appends_exactly_three_list_scenarios() -> None:
    assert len(SCENARIOS) == 88
    assert tuple(scenario.name for scenario in SCENARIOS[64:67]) == (
        "fixed_three_player_historical_list_mixed",
        "fixed_three_player_historical_list_all_passed",
        "fixed_three_player_historical_list_comparison",
    )
