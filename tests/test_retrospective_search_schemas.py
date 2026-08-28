import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError
from referencing import Registry, Resource

from skatmind.bounded_search_evaluation import evaluate_bounded_search_dataset
from skatmind.bounded_search_result import (
    BOUNDED_SEARCH_ANALYSIS_METHOD,
    BOUNDED_SEARCH_SCHEMA_VERSION,
    AggregateSearchCandidateResult,
    BoundedSearchResult,
    ConsumedSearchBudget,
    rank_search_candidate_results,
)
from skatmind.historical_decision_snapshot import build_historical_decision_snapshots
from skatmind.historical_game import (
    build_historical_game_record,
    build_historical_game_summary,
)
from skatmind.historical_search_review import build_historical_search_review_summary
from skatmind.rules import get_legal_cards
from skatmind.terminal_utility import TERMINAL_UTILITY_VERSION
from skatmind.training_dataset import build_training_dataset_input

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_NAMES = (
    "bounded_search_result.schema.json",
    "bounded_search_post_game_review.schema.json",
    "historical_search_review.schema.json",
    "bounded_search_evaluation.schema.json",
)


def _load_schema(name: str) -> dict:
    with (ROOT / "schemas" / name).open("r", encoding="utf-8") as file:
        return json.load(file)


SCHEMAS = {name: _load_schema(name) for name in SCHEMA_NAMES}
REGISTRY = Registry().with_resources(
    [
        (schema["$id"], Resource.from_contents(schema))
        for schema in SCHEMAS.values()
    ]
)
FLAT_VALIDATOR = Draft202012Validator(
    SCHEMAS["bounded_search_post_game_review.schema.json"],
    registry=REGISTRY,
)
HISTORICAL_VALIDATOR = Draft202012Validator(
    SCHEMAS["historical_search_review.schema.json"],
    registry=REGISTRY,
)
EVALUATION_VALIDATOR = Draft202012Validator(
    SCHEMAS["bounded_search_evaluation.schema.json"],
    registry=REGISTRY,
)


def _fake_immediate(*, state, **_kwargs):
    legal_cards = get_legal_cards(state.hand, state.current_trick, state.game_type)
    recommended = legal_cards[-1]
    values = {
        card: {
            "win_rate": 1.0 if card == recommended else 0.0,
            "average_trick_points": 10.0 if card == recommended else 0.0,
            "average_points_won": 10.0 if card == recommended else 0.0,
            "average_points_lost": 0.0,
        }
        for card in legal_cards
    }
    return recommended, "deterministic schema test baseline", values


def _fake_search(*, information_view, requested_budget, random_seed):
    legal_cards = tuple(
        get_legal_cards(
            list(information_view.local_remaining_hand),
            [play.card for play in information_view.current_trick],
            information_view.game_type,
        )
    )
    candidates = tuple(
        AggregateSearchCandidateResult(
            card=card,
            rank=1,
            is_recommended=False,
            completed_world_count=1,
            local_contract_success_count=int(index == 0),
            local_contract_success_rate=float(index == 0),
            mean_local_side_game_score=float(len(legal_cards) - index),
            mean_local_side_card_point_margin=(
                None
                if information_view.game_type == "null"
                else float(len(legal_cards) - index)
            ),
        )
        for index, card in enumerate(legal_cards)
    )
    ranked = rank_search_candidate_results(
        candidates,
        information_view.game_type,
        recommend=True,
    )
    return BoundedSearchResult(
        schema_version=BOUNDED_SEARCH_SCHEMA_VERSION,
        analysis_method=BOUNDED_SEARCH_ANALYSIS_METHOD,
        search_method="compatible_world_minimax_v1",
        game_type=information_view.game_type,
        status="complete",
        stop_reason="completed",
        world_coverage="all_compatible_worlds",
        solution_claim="exact_per_selected_world",
        terminal_utility_version=TERMINAL_UTILITY_VERSION,
        requested_budget=requested_budget,
        consumed_budget=ConsumedSearchBudget(
            depth_reached=1,
            nodes_expanded=random_seed % 100 + 1,
            selected_world_count=1,
            completed_world_count=1,
            sampled_world_count=0,
            unique_sampled_world_count=0,
            wall_clock_elapsed_ms=2,
        ),
        compatible_world_count=1,
        candidate_results=ranked,
        recommended_card=ranked[0].card,
        fallback_used=False,
        fallback_method=None,
    )


@pytest.fixture(scope="module")
def representative_outputs() -> dict[str, dict]:
    from main import build_analysis_result

    flat_result = build_analysis_result(
        str(ROOT / "examples" / "grand_bounded_search_post_game_review.json")
    )["bounded_search_post_game_review_summary"]

    historical_data = json.loads(
        (ROOT / "examples" / "historical_grand_normal_completion.json").read_text(
            encoding="utf-8"
        )
    )
    record = build_historical_game_record(historical_data["historical_game_input"])
    snapshots = build_historical_decision_snapshots(build_historical_game_summary(record))
    dataset_data = json.loads(
        (ROOT / "examples" / "training_dataset_normal_play.json").read_text(
            encoding="utf-8"
        )
    )
    dataset = build_training_dataset_input(dataset_data["training_dataset_input"])

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        "skatmind.historical_search_review.solve_compatible_world_minimax",
        _fake_search,
    )
    monkeypatch.setattr(
        "skatmind.historical_search_review.recommend_card_by_expected_value",
        _fake_immediate,
    )
    try:
        historical_result = build_historical_search_review_summary(
            snapshots,
            record,
            base_search_seed=17,
            immediate_sample_count=1,
            immediate_base_random_seed=23,
        )
        evaluation_result = evaluate_bounded_search_dataset(
            dataset,
            base_search_seed=29,
            partitions=("validation",),
            max_decisions=2,
        )
    finally:
        monkeypatch.undo()

    return {
        "flat": flat_result,
        "historical": historical_result,
        "evaluation": evaluation_result,
    }


def test_retrospective_search_schemas_are_draft_2020_12_with_exact_ids() -> None:
    expected_ids = {
        "bounded_search_post_game_review.schema.json": (
            "https://example.local/skatmind/"
            "bounded_search_post_game_review.schema.json"
        ),
        "historical_search_review.schema.json": (
            "https://example.local/skatmind/historical_search_review.schema.json"
        ),
        "bounded_search_evaluation.schema.json": (
            "https://example.local/skatmind/bounded_search_evaluation.schema.json"
        ),
    }
    for name, expected_id in expected_ids.items():
        schema = SCHEMAS[name]
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["$id"] == expected_id
        Draft202012Validator.check_schema(schema)


def test_schemas_accept_representative_product_outputs(representative_outputs) -> None:
    FLAT_VALIDATOR.validate(representative_outputs["flat"])
    HISTORICAL_VALIDATOR.validate(representative_outputs["historical"])
    EVALUATION_VALIDATOR.validate(representative_outputs["evaluation"])


def test_schemas_recursively_reject_unknown_and_private_properties(
    representative_outputs,
) -> None:
    flat = copy.deepcopy(representative_outputs["flat"])
    flat["search_actual_card_comparison"]["actual_card_metrics"][
        "private_world_assignment"
    ] = {"C7": "left"}
    with pytest.raises(ValidationError):
        FLAT_VALIDATOR.validate(flat)

    historical = copy.deepcopy(representative_outputs["historical"])
    historical["decisions"][0]["immediate_baseline"]["analysis_report"][0][
        "hidden_opponent_hand"
    ] = ["C7"]
    with pytest.raises(ValidationError):
        HISTORICAL_VALIDATOR.validate(historical)

    historical = copy.deepcopy(representative_outputs["historical"])
    historical["decisions"][0]["bounded_search_result"]["private_skat"] = [
        "C7",
        "S7",
    ]
    with pytest.raises(ValidationError):
        HISTORICAL_VALIDATOR.validate(historical)

    evaluation = copy.deepcopy(representative_outputs["evaluation"])
    evaluation["records"][0]["private_source_payload"] = {"hands": []}
    with pytest.raises(ValidationError):
        EVALUATION_VALIDATOR.validate(evaluation)


@pytest.mark.parametrize(
    ("path", "invalid_value"),
    [
        (("search_vs_immediate_comparison", "search_aggregate_relation"), "better"),
        (("search_actual_card_comparison", "comparison_basis"), "all_worlds"),
        (("search_actual_card_comparison", "actual_card_rank"), 0),
        (
            (
                "search_actual_card_comparison",
                "actual_card_metrics",
                "local_contract_success_rate",
            ),
            1.01,
        ),
        (("search_actual_card_comparison", "completed_world_count"), -1),
    ],
)
def test_flat_schema_rejects_invalid_relation_basis_rank_rate_and_count(
    representative_outputs,
    path,
    invalid_value,
) -> None:
    result = copy.deepcopy(representative_outputs["flat"])
    target = result
    for segment in path[:-1]:
        target = target[segment]
    target[path[-1]] = invalid_value

    with pytest.raises(ValidationError):
        FLAT_VALIDATOR.validate(result)


def test_historical_schema_rejects_non_null_null_game_margins(
    representative_outputs,
) -> None:
    result = copy.deepcopy(representative_outputs["historical"])
    decision = result["decisions"][0]
    decision["game_type"] = "null"
    decision["bounded_search_result"]["game_type"] = "null"
    for candidate in decision["bounded_search_result"]["candidate_results"]:
        candidate["mean_local_side_card_point_margin"] = None
    actual_comparison = decision["search_actual_card_comparison"]
    actual_comparison["actual_card_metrics"][
        "mean_local_side_card_point_margin"
    ] = None
    actual_comparison["recommended_card_metrics"][
        "mean_local_side_card_point_margin"
    ] = None
    actual_comparison["mean_local_side_card_point_margin_gap"] = None
    decision["search_vs_immediate_comparison"][
        "search_mean_card_point_margin_advantage"
    ] = None
    HISTORICAL_VALIDATOR.validate(result)

    decision["search_vs_immediate_comparison"][
        "search_mean_card_point_margin_advantage"
    ] = 0.0
    with pytest.raises(ValidationError):
        HISTORICAL_VALIDATOR.validate(result)


def test_flat_schema_enforces_contract_specific_margin_semantics(
    representative_outputs,
) -> None:
    null_result = copy.deepcopy(representative_outputs["flat"])
    null_result["game_type"] = "null"
    actual = null_result["search_actual_card_comparison"]
    actual["actual_card_metrics"]["mean_local_side_card_point_margin"] = None
    actual["recommended_card_metrics"]["mean_local_side_card_point_margin"] = None
    actual["mean_local_side_card_point_margin_gap"] = None
    comparison = null_result["search_vs_immediate_comparison"]
    comparison["search_mean_card_point_margin_advantage"] = None
    FLAT_VALIDATOR.validate(null_result)

    comparison["search_mean_card_point_margin_advantage"] = 0.0
    with pytest.raises(ValidationError):
        FLAT_VALIDATOR.validate(null_result)

    suit_result = copy.deepcopy(representative_outputs["flat"])
    suit_result["search_actual_card_comparison"]["actual_card_metrics"][
        "mean_local_side_card_point_margin"
    ] = None
    with pytest.raises(ValidationError):
        FLAT_VALIDATOR.validate(suit_result)

    suit_result = copy.deepcopy(representative_outputs["flat"])
    suit_result["search_actual_card_comparison"][
        "mean_local_side_card_point_margin_gap"
    ] = None
    with pytest.raises(ValidationError):
        FLAT_VALIDATOR.validate(suit_result)


def test_schemas_reject_invalid_methods(representative_outputs) -> None:
    flat = copy.deepcopy(representative_outputs["flat"])
    flat["analysis_method"] = "bounded_search"
    with pytest.raises(ValidationError):
        FLAT_VALIDATOR.validate(flat)

    historical = copy.deepcopy(representative_outputs["historical"])
    historical["analysis_method"] = "immediate_expected_value"
    with pytest.raises(ValidationError):
        HISTORICAL_VALIDATOR.validate(historical)

    evaluation = copy.deepcopy(representative_outputs["evaluation"])
    evaluation["evaluation_method"] = "bounded_search_vs_immediate"
    with pytest.raises(ValidationError):
        EVALUATION_VALIDATOR.validate(evaluation)


def test_historical_schema_rejects_invalid_profile_metric_and_dynamic_count(
    representative_outputs,
) -> None:
    invalid_profile = copy.deepcopy(representative_outputs["historical"])
    invalid_profile["settings"]["search_budget_profile"] = "unbounded"
    with pytest.raises(ValidationError):
        HISTORICAL_VALIDATOR.validate(invalid_profile)

    invalid_rate = copy.deepcopy(representative_outputs["historical"])
    invalid_rate["search_vs_immediate_agreement"][
        "same_recommended_card_rate"
    ] = -0.1
    with pytest.raises(ValidationError):
        HISTORICAL_VALIDATOR.validate(invalid_rate)

    invalid_count = copy.deepcopy(representative_outputs["historical"])
    invalid_count["search_aggregate_quality"]["unavailable_reason_counts"] = {
        "no_completed_search_worlds": -1
    }
    with pytest.raises(ValidationError):
        HISTORICAL_VALIDATOR.validate(invalid_count)


def test_evaluation_schema_rejects_invalid_partition_cap_and_record_count(
    representative_outputs,
) -> None:
    invalid_partition = copy.deepcopy(representative_outputs["evaluation"])
    invalid_partition["selection"]["partitions"] = ["development"]
    with pytest.raises(ValidationError):
        EVALUATION_VALIDATOR.validate(invalid_partition)

    invalid_cap = copy.deepcopy(representative_outputs["evaluation"])
    invalid_cap["selection"]["max_decisions"] = 0
    with pytest.raises(ValidationError):
        EVALUATION_VALIDATOR.validate(invalid_cap)

    invalid_count = copy.deepcopy(representative_outputs["evaluation"])
    invalid_count["records"][0]["evaluated_decision_count"] = -1
    with pytest.raises(ValidationError):
        EVALUATION_VALIDATOR.validate(invalid_count)
