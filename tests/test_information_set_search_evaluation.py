import copy
import json
from pathlib import Path

import pytest

from skatmind.historical_information_set_search_review import (
    derive_historical_information_set_search_decision_seed,
)
from skatmind.information_set_search_comparison import (
    build_information_set_search_comparison_pre_actual_analysis_v1,
)
from skatmind.information_set_search_evaluation import (
    DEFAULT_INFORMATION_SET_SEARCH_EVALUATION_PARTITIONS,
    INFORMATION_SET_SEARCH_EVALUATION_METHOD,
    INFORMATION_SET_SEARCH_EVALUATION_POLICY,
    build_information_set_search_evaluation_v1,
    evaluate_information_set_search_dataset_v1,
)
from skatmind.training_dataset import build_training_dataset_input

ROOT = Path(__file__).resolve().parents[1]


def _load_json(name: str):
    return json.loads((ROOT / "examples" / name).read_text("utf-8"))


def _evaluation_dataset():
    normal = _load_json("training_dataset_normal_play.json")[
        "training_dataset_input"
    ]
    validation = copy.deepcopy(normal["records"][1])
    variable = _load_json("training_dataset_variable_length.json")[
        "training_dataset_input"
    ]
    zero = copy.deepcopy(variable["records"][0])
    zero["record_id"] = "zero-test-record"
    zero["partition"] = "test"
    zero["historical_game"]["game_id"] = "zero-test-game"
    zero["historical_game"]["tricks"] = []
    zero["historical_game"]["game_end"]["declarer_hand_cards_remaining"] = 10
    zero["historical_game"]["game_end"]["defender_consent"] = {
        "status": "not_required",
        "consenting_defender_player_ids": [],
    }
    return build_training_dataset_input(
        {
            "schema_version": 1,
            "dataset_id": "information-set-evaluation-test",
            "dataset_version": "1",
            "feature_generation_version": 1,
            "target": "actual_card_played",
            "records": [zero, validation],
        }
    )


def _capturing_builder(observed_inputs: list):
    def build(decision_input):
        observed_inputs.append(decision_input)
        assert not hasattr(decision_input, "actual_card")
        return build_information_set_search_comparison_pre_actual_analysis_v1(
            information_set_result=None,
            pimc_result=None,
            immediate_recommended_card=decision_input.visible_state.legal_cards[0],
            same_selected_world_sequence=False,
        )

    return build


def test_defaults_preserve_record_order_zero_records_cap_and_decision_seeds() -> None:
    dataset = _evaluation_dataset()
    observed_inputs = []

    summary = build_information_set_search_evaluation_v1(
        dataset,
        77,
        pre_actual_analysis_builder=_capturing_builder(observed_inputs),
        max_decisions=3,
        immediate_sample_count=1,
    )

    assert DEFAULT_INFORMATION_SET_SEARCH_EVALUATION_PARTITIONS == (
        "validation",
        "test",
    )
    assert summary.evaluation_method == INFORMATION_SET_SEARCH_EVALUATION_METHOD
    assert summary.selection.partitions == ("validation", "test")
    assert [record.record_id for record in summary.records] == [
        "zero-test-record",
        dataset.records[1].record_id,
    ]
    assert summary.records[0].source_decision_count == 0
    assert summary.records[0].decisions == ()
    assert summary.zero_decision_record_count == 1
    assert summary.selection.available_decision_count == 30
    assert summary.selection.evaluated_decision_count == 3
    assert summary.selection.decision_cap_reached is True
    assert len(observed_inputs) == 3
    game_id = dataset.records[1].historical_game.game_id
    assert [item.search_seed for item in observed_inputs] == [
        derive_historical_information_set_search_decision_seed(77, game_id, index)
        for index in (1, 2, 3)
    ]
    assert [item.immediate_random_seed for item in observed_inputs] == [0, 1, 2]


def test_explicit_partition_with_only_zero_record_is_preserved() -> None:
    result = evaluate_information_set_search_dataset_v1(
        _evaluation_dataset(),
        9,
        pre_actual_analysis_builder=_capturing_builder([]),
        partitions=("test", "test"),
        max_decisions=2,
        immediate_sample_count=1,
    )

    assert result["selection"]["partitions"] == ["test"]
    assert result["record_count"] == 1
    assert result["zero_decision_record_count"] == 1
    assert result["decision_count"] == 0
    assert result["records"][0]["decisions"] == []
    assert result["source_dataset"]["target"] == "actual_card_played"
    assert "samples" not in result


def test_breakdowns_cover_partition_contract_role_seat_phase_status_and_agreement() -> None:
    observed_inputs = []
    result = evaluate_information_set_search_dataset_v1(
        _evaluation_dataset(),
        13,
        pre_actual_analysis_builder=_capturing_builder(observed_inputs),
        max_decisions=4,
        immediate_sample_count=1,
    )

    assert result["evaluation_method"] == (
        "information_set_search_vs_same_selection_pimc_and_immediate_v1"
    )
    assert INFORMATION_SET_SEARCH_EVALUATION_POLICY == (
        "deterministic_dataset_prefix_without_training"
    )
    assert tuple(result["breakdowns"]) == (
        "by_partition",
        "by_contract",
        "by_role",
        "by_seat",
        "by_phase",
        "by_status",
        "by_coverage",
        "by_recommendation_agreement",
    )
    assert all(
        sum(row["metrics"]["decision_count"] for row in rows) == 4
        for rows in result["breakdowns"].values()
    )
    assert result["status_counts"] == {"not_available": 4}
    assert result["coverage_counts"] == {"none": 4}
    assert result["source_dataset"]["target"] == "actual_card_played"
    assert all("label" not in record for record in result["records"])


@pytest.mark.parametrize(
    "partitions,max_decisions,error",
    [
        ((), 1, "must not be empty"),
        (("development",), 1, "Unsupported evaluation partitions"),
        (("train",), 1, "No dataset records match"),
        (("test",), True, "max_decisions"),
    ],
)
def test_evaluation_validates_partitions_and_global_cap(
    partitions,
    max_decisions,
    error,
) -> None:
    with pytest.raises(ValueError, match=error):
        build_information_set_search_evaluation_v1(
            _evaluation_dataset(),
            1,
            pre_actual_analysis_builder=_capturing_builder([]),
            partitions=partitions,
            max_decisions=max_decisions,
            immediate_sample_count=1,
        )
