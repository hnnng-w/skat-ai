import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from skat_ai.api.v1 import ExecutionOptionsV1, execute_document
from skat_ai.application.contracts import PositionAnalysisApplicationOptions
from skat_ai.application.position_workflow import build_position_analysis_result

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMAS_DIR = PROJECT_ROOT / "schemas"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


SCHEMAS = {
    path.name: _load(path) for path in sorted(SCHEMAS_DIR.glob("*.schema.json"))
}
REGISTRY = Registry().with_resources(
    (schema["$id"], Resource.from_contents(schema)) for schema in SCHEMAS.values()
)


def _validator(name: str) -> Draft202012Validator:
    return Draft202012Validator(SCHEMAS[name], registry=REGISTRY)


def _assert_valid(name: str, document: dict) -> None:
    assert list(_validator(name).iter_errors(document)) == []


def _build_position(example_name: str) -> dict:
    root = _load(PROJECT_ROOT / "examples" / example_name)
    settings = _load(PROJECT_ROOT / "examples" / "information_set_search.json")[
        "information_set_search_settings"
    ]
    root["recommendation_method"] = "information_set_search"
    root.pop("bounded_search_settings", None)
    root["information_set_search_settings"] = settings
    return build_position_analysis_result(
        root,
        input_reference=f"memory://{example_name}",
        options=PositionAnalysisApplicationOptions(),
    )


def _zero_decision_historical_root() -> dict:
    dataset = _load(PROJECT_ROOT / "examples" / "training_dataset_variable_length.json")
    historical = copy.deepcopy(
        dataset["training_dataset_input"]["records"][0]["historical_game"]
    )
    historical["tricks"] = []
    historical["game_end"]["declarer_hand_cards_remaining"] = 10
    historical["game_end"]["defender_consent"] = {
        "status": "not_required",
        "consenting_defender_player_ids": [],
    }
    return {"historical_game_input": historical}


def test_live_information_set_search_result_matches_standalone_and_root_schemas() -> None:
    output = _build_position("information_set_search.json")

    _assert_valid(
        "information_set_search_result.schema.json",
        output["information_set_search_result"],
    )
    _assert_valid("output.schema.json", output)
    assert output["bounded_search_result"] is None


@pytest.mark.parametrize(
    "private_field",
    [
        "policy_table",
        "observation",
        "own_hand",
        "exact_state",
        "world_identity",
        "memoization",
    ],
)
def test_information_set_search_result_schema_rejects_private_fields(
    private_field: str,
) -> None:
    result = copy.deepcopy(
        _build_position("information_set_search.json")["information_set_search_result"]
    )
    result[private_field] = {}

    assert list(_validator("information_set_search_result.schema.json").iter_errors(result))


def test_post_game_comparison_matches_standalone_and_root_schemas() -> None:
    output = _build_position("grand_bounded_search_post_game_review.json")

    _assert_valid(
        "information_set_search_comparison.schema.json",
        output["information_set_search_comparison"],
    )
    _assert_valid("output.schema.json", output)
    assert output["information_set_search_comparison"]["comparison_status"] == "available"

    private = copy.deepcopy(output["information_set_search_comparison"])
    private["selected_worlds"] = [{"own_hand": ["D7"]}]
    assert list(
        _validator("information_set_search_comparison.schema.json").iter_errors(private)
    )


def test_zero_decision_historical_review_matches_standalone_and_root_schemas() -> None:
    output = execute_document(
        _zero_decision_historical_root(),
        options=ExecutionOptionsV1(
            validate_output=False,
            workflow_options={
                "information_set_search_review": True,
                "search_seed": 67,
                "immediate_sample_count": 1,
            },
        ),
    ).result.to_dict()["document"]
    review = output["historical_game_summary"][
        "historical_information_set_search_review_summary"
    ]

    _assert_valid("historical_information_set_search_review.schema.json", review)
    _assert_valid("output.schema.json", output)
    assert review["decision_count"] == 0


def test_zero_decision_evaluation_matches_standalone_and_root_schemas() -> None:
    dataset = _load(PROJECT_ROOT / "examples" / "training_dataset_variable_length.json")
    record = copy.deepcopy(dataset["training_dataset_input"]["records"][0])
    record["partition"] = "test"
    record["historical_game"] = _zero_decision_historical_root()["historical_game_input"]
    dataset["training_dataset_input"]["records"] = [record]
    output = execute_document(
        dataset,
        options=ExecutionOptionsV1(
            validate_output=False,
            workflow_options={
                "operation": "information_set_search_evaluation",
                "information_set_search_seed": 71,
                "information_set_search_partitions": ["test"],
                "information_set_search_max_decisions": 1,
            },
        ),
    ).result.to_dict()["document"]
    evaluation = output["information_set_search_evaluation_summary"]

    _assert_valid("information_set_search_evaluation.schema.json", evaluation)
    _assert_valid("output.schema.json", output)
    assert evaluation["record_count"] == 1
    assert evaluation["decision_count"] == 0
