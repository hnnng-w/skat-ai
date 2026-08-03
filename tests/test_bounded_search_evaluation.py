import copy
import json
from pathlib import Path

import pytest
from test_historical_game import build_historical_input, rebuild_historical_suffix
from test_historical_search_review import (
    _collect_keys,
    _fake_immediate,
    _fake_search,
)

from skat_ai.bounded_search_evaluation import evaluate_bounded_search_dataset
from skat_ai.historical_search_review import derive_historical_search_decision_seed
from skat_ai.training_dataset import build_training_dataset_input

ROOT = Path(__file__).resolve().parents[1]


def _load_json(name: str):
    return json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))


def _evaluation_dataset():
    normal = _load_json("training_dataset_normal_play.json")[
        "training_dataset_input"
    ]
    validation = copy.deepcopy(normal["records"][1])
    shortened = _load_json("training_dataset_variable_length.json")[
        "training_dataset_input"
    ]
    zero = copy.deepcopy(shortened["records"][0])
    zero["record_id"] = "zero-test-record"
    zero["partition"] = "test"
    zero["historical_game"]["game_id"] = "zero-test-game"
    zero["historical_game"]["tricks"] = []
    zero["historical_game"]["game_end"]["declarer_hand_cards_remaining"] = 10
    zero["historical_game"]["game_end"]["defender_consent"] = {
        "status": "not_required",
        "consenting_defender_player_ids": [],
    }
    data = {
        "schema_version": 1,
        "dataset_id": "bounded-search-evaluation-test",
        "dataset_version": "1",
        "feature_generation_version": 1,
        "target": "actual_card_played",
        "records": [zero, validation],
    }
    return build_training_dataset_input(data)


def _shared_prefix_evaluation_dataset():
    variable = _load_json("training_dataset_variable_length.json")[
        "training_dataset_input"
    ]
    zero = copy.deepcopy(variable["records"][0])
    zero["record_id"] = "zero-prefix-record"
    zero["partition"] = "test"
    zero["provenance"]["source_record_id"] = "zero-prefix-source"
    zero["historical_game"]["game_id"] = "zero-prefix-game"
    zero["historical_game"]["tricks"] = []
    zero["historical_game"]["game_end"]["declarer_hand_cards_remaining"] = 10
    zero["historical_game"]["game_end"]["defender_consent"] = {
        "status": "not_required",
        "consenting_defender_player_ids": [],
    }

    template = copy.deepcopy(
        _load_json("training_dataset_normal_play.json")["training_dataset_input"][
            "records"
        ][1]
    )
    original_game = build_historical_input()
    original_game["game_id"] = "shared-prefix-original-game"
    changed_game = rebuild_historical_suffix(
        original_game, completed_prefix_tricks=5
    )
    changed_game["game_id"] = "shared-prefix-changed-game"

    original = copy.deepcopy(template)
    original["record_id"] = "shared-prefix-original-record"
    original["partition"] = "test"
    original["provenance"]["source_record_id"] = "shared-prefix-original-source"
    original["historical_game"] = original_game
    changed = copy.deepcopy(template)
    changed["record_id"] = "shared-prefix-changed-record"
    changed["partition"] = "test"
    changed["provenance"]["source_record_id"] = "shared-prefix-changed-source"
    changed["historical_game"] = changed_game
    return build_training_dataset_input(
        {
            "schema_version": 1,
            "dataset_id": "shared-prefix-search-evaluation",
            "dataset_version": "1",
            "feature_generation_version": 1,
            "target": "actual_card_played",
            "records": [zero, original, changed],
        }
    )


def _patch_fast_analyses(monkeypatch) -> None:
    monkeypatch.setattr(
        "skat_ai.historical_search_review.solve_compatible_world_minimax", _fake_search
    )
    monkeypatch.setattr(
        "skat_ai.historical_search_review.recommend_card_by_expected_value",
        _fake_immediate,
    )


def test_evaluation_canonicalizes_partitions_preserves_zero_records_and_caps_prefix(
    monkeypatch,
) -> None:
    _patch_fast_analyses(monkeypatch)
    result = evaluate_bounded_search_dataset(
        _evaluation_dataset(),
        base_search_seed=77,
        partitions=("test", "validation", "test"),
        max_decisions=3,
    )

    assert result["evaluation_method"] == "bounded_search_vs_immediate_v1"
    assert result["selection"]["partitions"] == ["validation", "test"]
    assert result["record_count"] == 2
    assert result["zero_decision_record_count"] == 1
    assert result["available_decision_count"] == 30
    assert result["decision_counts"]["decision_count"] == 3
    assert result["records"][0]["source_decision_count"] == 0
    assert result["records"][0]["decisions"] == []
    assert result["records"][1]["evaluated_decision_count"] == 3
    assert result["settings"]["immediate_base_random_seed"] == 0
    assert [
        row["immediate_baseline"]["effective_random_seed"]
        for row in result["records"][1]["decisions"]
    ] == [0, 1, 2]
    assert {"decision_seed", "derived_seed", "search_seed"}.isdisjoint(
        _collect_keys(result)
    )


def test_evaluation_preserves_shared_prefix_privacy_with_zero_decision_record(
    monkeypatch,
) -> None:
    def seed_independent_search(**kwargs):
        return _fake_search(**{**kwargs, "random_seed": 0})

    monkeypatch.setattr(
        "skat_ai.historical_search_review.solve_compatible_world_minimax",
        seed_independent_search,
    )
    monkeypatch.setattr(
        "skat_ai.historical_search_review.recommend_card_by_expected_value",
        _fake_immediate,
    )

    result = evaluate_bounded_search_dataset(
        _shared_prefix_evaluation_dataset(),
        base_search_seed=91,
        partitions=("test",),
        max_decisions=31,
    )

    assert result["record_count"] == 3
    assert result["zero_decision_record_count"] == 1
    assert result["records"][0]["source_decision_count"] == 0
    assert result["records"][0]["decisions"] == []
    original = result["records"][1]["decisions"][0]
    changed = result["records"][2]["decisions"][0]
    original_without_identity = {k: v for k, v in original.items() if k != "source_game_id"}
    changed_without_identity = {k: v for k, v in changed.items() if k != "source_game_id"}

    assert original_without_identity == changed_without_identity
    assert original["bounded_search_result"]["recommended_card"] == (
        changed["bounded_search_result"]["recommended_card"]
    )
    assert original["bounded_search_result"]["candidate_results"] == (
        changed["bounded_search_result"]["candidate_results"]
    )
    assert (
        original["bounded_search_result"]["status"],
        original["bounded_search_result"]["world_coverage"],
    ) == (
        changed["bounded_search_result"]["status"],
        changed["bounded_search_result"]["world_coverage"],
    )
    assert {"decision_seed", "derived_seed", "search_seed"}.isdisjoint(
        _collect_keys(result)
    )


def test_evaluation_quality_coverage_and_performance_arithmetic(monkeypatch) -> None:
    _patch_fast_analyses(monkeypatch)
    result = evaluate_bounded_search_dataset(
        _evaluation_dataset(), 11, max_decisions=4
    )

    quality = result["quality_gate"]
    assert quality["comparable_decision_count"] == 4
    assert quality["search_not_worse_count"] == 4
    assert quality["search_strictly_better_count"] + quality[
        "search_equivalent_count"
    ] == 4
    assert quality["quality_violation_count"] == 0
    assert quality["quality_gate_passed"] is True
    assert sum(result["status_counts"].values()) == 4
    assert sum(result["coverage"].values()) == 4
    node_values = [
        row["bounded_search_result"]["consumed_budget"]["nodes_expanded"]
        for row in result["records"][1]["decisions"]
    ]
    assert result["performance"]["nodes_expanded"]["total"] == sum(
        node_values
    )
    assert result["performance"]["nodes_expanded"]["p95"] == max(
        node_values
    )


def test_evaluation_seed_is_stable_under_dataset_record_reordering(monkeypatch) -> None:
    _patch_fast_analyses(monkeypatch)
    dataset = _evaluation_dataset()
    reversed_dataset = dataset.__class__(
        schema_version=dataset.schema_version,
        dataset_id=dataset.dataset_id,
        dataset_version=dataset.dataset_version,
        feature_generation_version=dataset.feature_generation_version,
        target=dataset.target,
        partition_policy=dataset.partition_policy,
        records=tuple(reversed(dataset.records)),
    )

    first = evaluate_bounded_search_dataset(dataset, 19, max_decisions=1)
    second = evaluate_bounded_search_dataset(reversed_dataset, 19, max_decisions=1)
    first_decision = next(row for row in first["records"] if row["decisions"])[
        "decisions"
    ][0]
    second_decision = next(row for row in second["records"] if row["decisions"])[
        "decisions"
    ][0]

    assert first_decision["source_game_id"] == second_decision["source_game_id"]
    assert first_decision["bounded_search_result"]["consumed_budget"] == (
        second_decision["bounded_search_result"]["consumed_budget"]
    )
    assert derive_historical_search_decision_seed(
        19, first_decision["source_game_id"], 1
    ) == derive_historical_search_decision_seed(
        19, second_decision["source_game_id"], 1
    )


@pytest.mark.parametrize(
    "partitions, error",
    [
        ((), "must not be empty"),
        (("development",), "Unsupported evaluation partitions"),
        (("train",), "No dataset records match"),
    ],
)
def test_evaluation_rejects_invalid_or_unmatched_partitions(
    partitions, error
) -> None:
    with pytest.raises(ValueError, match=error):
        evaluate_bounded_search_dataset(
            _evaluation_dataset(), 1, partitions=partitions, max_decisions=1
        )


@pytest.mark.parametrize("max_decisions", [0, -1, True, 1.5])
def test_evaluation_rejects_invalid_decision_caps(max_decisions) -> None:
    with pytest.raises(ValueError, match="max_decisions"):
        evaluate_bounded_search_dataset(
            _evaluation_dataset(), 1, max_decisions=max_decisions
        )
