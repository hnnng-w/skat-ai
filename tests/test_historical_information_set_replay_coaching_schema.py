import copy
import json
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from skatmind.api.v1 import ExecutionOptionsV1, execute_document

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMAS_DIR = PROJECT_ROOT / "schemas"
SCHEMA_NAME = "historical_information_set_replay_coaching.schema.json"


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


def _build_zero_decision_output() -> dict:
    return execute_document(
        _zero_decision_historical_root(),
        options=ExecutionOptionsV1(
            validate_output=False,
            workflow_options={
                "information_set_replay_coaching": True,
                "search_seed": 17,
                "immediate_sample_count": 1,
            },
        ),
    ).result.to_dict()["document"]


def test_information_set_replay_coaching_schema_metadata_is_stable() -> None:
    schema = SCHEMAS[SCHEMA_NAME]

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"] == (
        "https://example.local/skatmind/"
        "historical_information_set_replay_coaching.schema.json"
    )
    assert schema["additionalProperties"] is False


def test_zero_decision_report_matches_standalone_and_root_schemas() -> None:
    output = _build_zero_decision_output()
    summary = output["historical_game_summary"]
    report = summary["historical_information_set_replay_coaching_summary"]

    assert list(_validator(SCHEMA_NAME).iter_errors(report)) == []
    assert list(_validator("output.schema.json").iter_errors(output)) == []
    assert report["assessments"] == []
    assert report["coverage"]["decision_count"] == 0
    assert "historical_information_set_search_review_summary" not in summary


def test_information_set_replay_coaching_schema_rejects_unknown_nested_field() -> None:
    output = _build_zero_decision_output()
    report = copy.deepcopy(
        output["historical_game_summary"][
            "historical_information_set_replay_coaching_summary"
        ]
    )
    report["coverage"]["private_policy_table"] = {}

    assert list(_validator(SCHEMA_NAME).iter_errors(report))
