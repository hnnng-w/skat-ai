import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

from skat_ai.bounded_search_result import (
    AggregateSearchCandidateResult,
    BoundedSearchResult,
    ConsumedSearchBudget,
    RequestedSearchBudget,
    build_serializable_bounded_search_result,
    rank_search_candidate_results,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = PROJECT_ROOT / "schemas" / "bounded_search_result.schema.json"
with SCHEMA_PATH.open("r", encoding="utf-8") as file:
    SCHEMA = json.load(file)
VALIDATOR = Draft202012Validator(SCHEMA)


def _budget() -> RequestedSearchBudget:
    return RequestedSearchBudget(3, 9, 1000, 3, 3, 2, 100)


def _consumed(
    selected: int = 3,
    completed: int = 3,
    sampled: int = 3,
) -> ConsumedSearchBudget:
    return ConsumedSearchBudget(6, 100, selected, completed, sampled, sampled, 12)


def _candidates(completed: int = 3, recommend: bool = True):
    rows = (
        AggregateSearchCandidateResult(
            "CA", 1, False, completed, min(2, completed),
            min(2, completed) / completed if completed else None,
            24.0 if completed else None,
            10.0 if completed else None,
        ),
        AggregateSearchCandidateResult(
            "D7", 1, False, completed, min(1, completed),
            min(1, completed) / completed if completed else None,
            18.0 if completed else None,
            5.0 if completed else None,
        ),
    )
    return rank_search_candidate_results(rows, "grand", recommend=recommend)


def _fixture(status: str) -> dict:
    common = {
        "schema_version": 1,
        "analysis_method": "bounded_search",
        "search_method": "compatible_world_minimax_v1",
        "game_type": "grand",
        "terminal_utility_version": 1,
        "requested_budget": _budget(),
        "fallback_used": False,
        "fallback_method": None,
    }
    if status == "complete":
        result = BoundedSearchResult(
            **common,
            status="complete",
            stop_reason="completed",
            world_coverage="sampled_compatible_worlds",
            solution_claim="exact_per_selected_world",
            consumed_budget=_consumed(),
            compatible_world_count=100,
            candidate_results=_candidates(),
            recommended_card="CA",
        )
    elif status == "partial":
        result = BoundedSearchResult(
            **common,
            status="partial",
            stop_reason="node_budget_exhausted",
            world_coverage="sampled_compatible_worlds",
            solution_claim="node_limited_partial",
            consumed_budget=_consumed(completed=2),
            compatible_world_count=100,
            candidate_results=_candidates(2),
            recommended_card="CA",
        )
    elif status == "timeout":
        result = BoundedSearchResult(
            **common,
            status="timeout",
            stop_reason="wall_clock_timeout",
            world_coverage="sampled_compatible_worlds",
            solution_claim="node_limited_partial",
            consumed_budget=_consumed(completed=2),
            compatible_world_count=100,
            candidate_results=_candidates(2),
            recommended_card="CA",
        )
    else:
        result = BoundedSearchResult(
            **common,
            status="unavailable",
            stop_reason="unsupported_turn_phase",
            world_coverage="none",
            solution_claim="none",
            consumed_budget=ConsumedSearchBudget(0, 0, 0, 0, 0, 0, 0),
            compatible_world_count=None,
            candidate_results=(),
            recommended_card=None,
        )
    return build_serializable_bounded_search_result(result)


@pytest.mark.parametrize("status", ["complete", "partial", "timeout", "unavailable"])
def test_standalone_schema_accepts_each_valid_status(status: str) -> None:
    VALIDATOR.validate(_fixture(status))


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("status",), "finished"),
        (("stop_reason",), "cancelled"),
        (("world_coverage",), "exact"),
        (("solution_claim",), "optimal"),
        (("search_method",), "minimax"),
    ],
)
def test_standalone_schema_rejects_invalid_enums(
    path: tuple[str, ...],
    value: str,
) -> None:
    fixture = _fixture("complete")
    fixture[path[0]] = value

    with pytest.raises(ValidationError):
        VALIDATOR.validate(fixture)


@pytest.mark.parametrize(
    ("status", "stop_reason"),
    [
        ("complete", "node_budget_exhausted"),
        ("partial", "wall_clock_timeout"),
        ("timeout", "completed"),
        ("unavailable", "completed"),
    ],
)
def test_standalone_schema_rejects_invalid_status_combinations(
    status: str,
    stop_reason: str,
) -> None:
    fixture = _fixture(status)
    fixture["stop_reason"] = stop_reason

    with pytest.raises(ValidationError):
        VALIDATOR.validate(fixture)


@pytest.mark.parametrize(
    ("stop_reason", "solution_claim"),
    [
        ("node_budget_exhausted", "depth_limited_per_selected_world"),
        ("depth_budget_exhausted", "node_limited_partial"),
    ],
)
def test_schema_rejects_partial_stop_and_claim_mismatch(
    stop_reason: str,
    solution_claim: str,
) -> None:
    fixture = _fixture("partial")
    fixture["stop_reason"] = stop_reason
    fixture["solution_claim"] = solution_claim

    with pytest.raises(ValidationError):
        VALIDATOR.validate(fixture)


@pytest.mark.parametrize(
    ("location", "property_name", "value"),
    [
        ((), "actual_opponent_hands", {"left": ["CA"]}),
        ((), "sampled_world_assignment", {"CA": "left"}),
        (("requested_budget",), "private_skat", ["CA", "SA"]),
        (("consumed_budget",), "world_fingerprint", "secret"),
        (("candidate_results", 0), "principal_variation", ["CA"]),
    ],
)
def test_standalone_schema_recursively_rejects_unknown_and_private_world_properties(
    location: tuple[str | int, ...],
    property_name: str,
    value: object,
) -> None:
    fixture = copy.deepcopy(_fixture("complete"))
    target = fixture
    for segment in location:
        target = target[segment]
    target[property_name] = value

    with pytest.raises(ValidationError):
        VALIDATOR.validate(fixture)


def test_schema_rejects_zero_world_aggregates_and_null_card_margin() -> None:
    zero_world = _fixture("complete")
    zero_world["candidate_results"][0]["completed_world_count"] = 0
    with pytest.raises(ValidationError):
        VALIDATOR.validate(zero_world)

    null_fixture = _fixture("complete")
    null_fixture["game_type"] = "null"
    with pytest.raises(ValidationError):
        VALIDATOR.validate(null_fixture)


def test_schema_rejects_timeout_without_cutoff_and_missing_suit_margin() -> None:
    timeout = _fixture("timeout")
    timeout["requested_budget"]["wall_clock_timeout_ms"] = None
    with pytest.raises(ValidationError):
        VALIDATOR.validate(timeout)

    missing_margin = _fixture("complete")
    missing_margin["candidate_results"][0][
        "mean_local_side_card_point_margin"
    ] = None
    with pytest.raises(ValidationError):
        VALIDATOR.validate(missing_margin)


def test_schema_rejects_depth_claim_without_completed_or_unique_sampled_world() -> None:
    depth_limited = _fixture("partial")
    depth_limited["stop_reason"] = "depth_budget_exhausted"
    depth_limited["solution_claim"] = "depth_limited_per_selected_world"
    depth_limited["consumed_budget"]["completed_world_count"] = 0
    with pytest.raises(ValidationError):
        VALIDATOR.validate(depth_limited)

    no_unique_sample = _fixture("complete")
    no_unique_sample["consumed_budget"]["unique_sampled_world_count"] = 0
    with pytest.raises(ValidationError):
        VALIDATOR.validate(no_unique_sample)


def test_schema_rejects_recommendation_marker_inconsistency() -> None:
    missing_marker = _fixture("complete")
    for candidate in missing_marker["candidate_results"]:
        candidate["is_recommended"] = False
    with pytest.raises(ValidationError):
        VALIDATOR.validate(missing_marker)

    marker_without_card = _fixture("complete")
    marker_without_card["recommended_card"] = None
    with pytest.raises(ValidationError):
        VALIDATOR.validate(marker_without_card)
