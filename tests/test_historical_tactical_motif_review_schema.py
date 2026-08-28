import copy
import json
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from skatmind.api.v1 import ExecutionOptionsV1, execute_document

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMAS_DIR = PROJECT_ROOT / "schemas"
SCHEMA_NAME = "historical_tactical_motif_review.schema.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


SCHEMAS = {path.name: _load(path) for path in sorted(SCHEMAS_DIR.glob("*.schema.json"))}
REGISTRY = Registry().with_resources(
    (schema["$id"], Resource.from_contents(schema)) for schema in SCHEMAS.values()
)


def _validator(name: str) -> Draft202012Validator:
    return Draft202012Validator(SCHEMAS[name], registry=REGISTRY)


def _build_output() -> dict:
    historical = _load(PROJECT_ROOT / "examples" / "historical_grand_normal_completion.json")
    return execute_document(
        historical,
        options=ExecutionOptionsV1(
            validate_output=False,
            workflow_options={"historical_tactical_motif_review": True},
        ),
    ).result.to_dict()["document"]


def test_historical_tactical_motif_schema_metadata_is_stable() -> None:
    schema = SCHEMAS[SCHEMA_NAME]

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"] == (
        "https://example.local/skatmind/historical_tactical_motif_review.schema.json"
    )
    assert schema["additionalProperties"] is False


def test_historical_tactical_motif_report_matches_standalone_and_root_schemas() -> None:
    output = _build_output()
    report = output["historical_game_summary"]["historical_tactical_motif_review_summary"]

    assert list(_validator(SCHEMA_NAME).iter_errors(report)) == []
    assert list(_validator("output.schema.json").iter_errors(output)) == []
    assert report["observation_count"] == 30
    assert report["complete_observation_count"] == 30
    assert report["partial_observation_count"] == 0


def test_historical_tactical_motif_schema_rejects_unknown_nested_field() -> None:
    report = copy.deepcopy(
        _build_output()["historical_game_summary"]["historical_tactical_motif_review_summary"]
    )
    report["observations"][0]["decision_time_facts"]["private_legal_cards"] = ["CA"]

    assert list(_validator(SCHEMA_NAME).iter_errors(report))


def test_historical_tactical_motif_schema_reconciles_motifs_and_status() -> None:
    report = _build_output()["historical_game_summary"][
        "historical_tactical_motif_review_summary"
    ]
    observation = next(item for item in report["observations"] if item["motifs"])

    wrong_family = copy.deepcopy(report)
    target = next(item for item in wrong_family["observations"] if item["motifs"])
    target["motifs"][0]["motif_family"] = "trick_outcome"
    assert list(_validator(SCHEMA_NAME).iter_errors(wrong_family))

    wrong_time = copy.deepcopy(report)
    target = next(item for item in wrong_time["observations"] if item["motifs"])
    target["motifs"][0]["evidence_time"] = "after_trick_completion"
    assert list(_validator(SCHEMA_NAME).iter_errors(wrong_time))

    duplicate = copy.deepcopy(report)
    target = next(item for item in duplicate["observations"] if item["motifs"])
    target["motifs"].append(copy.deepcopy(target["motifs"][0]))
    assert list(_validator(SCHEMA_NAME).iter_errors(duplicate))

    partial_with_outcome = copy.deepcopy(report)
    target_index = report["observations"].index(observation)
    partial_with_outcome["observations"][target_index]["observation_status"] = "partial"
    assert list(_validator(SCHEMA_NAME).iter_errors(partial_with_outcome))
