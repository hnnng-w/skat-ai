import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from skat_ai.api.v1 import ExecutionOptionsV1, execute_document

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = PROJECT_ROOT / "schemas" / "field_provenance.schema.json"
EXAMPLE_PATH = PROJECT_ROOT / "examples" / "opponent_statistics.json"


def _schema() -> dict[str, object]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _bundle() -> dict[str, object]:
    source = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
    execution = execute_document(
        source,
        options=ExecutionOptionsV1(
            validate_output=False,
            include_provenance=True,
        ),
    )
    assert execution.field_provenance is not None
    return execution.field_provenance.to_dict()


def _assert_invalid(document: dict[str, object]) -> None:
    assert list(Draft202012Validator(_schema()).iter_errors(document))


def test_standalone_public_field_provenance_schema_is_meta_valid_and_strict() -> None:
    schema = _schema()
    Draft202012Validator.check_schema(schema)
    assert schema["$id"] == (
        "https://example.local/skat-ai/field_provenance.schema.json"
    )
    bundle = _bundle()
    assert list(Draft202012Validator(schema).iter_errors(bundle)) == []

    unknown = copy.deepcopy(bundle)
    unknown["unknown"] = True
    _assert_invalid(unknown)
    attached_document = copy.deepcopy(bundle)
    attached_document["result"]["document"] = {"private": True}
    _assert_invalid(attached_document)


@pytest.mark.parametrize(
    ("path", "value"),
    (
        (("result", "ledger", "status"), "partial_legacy"),
        (
            ("result", "ledger", "limitations"),
            ["legacy_untracked_fields"],
        ),
        (
            ("result", "ledger", "exemptions"),
            [
                {
                    "field_path": "/legacy",
                    "coverage_kind": "field",
                    "reason": "legacy_untracked",
                }
            ],
        ),
        (
            ("result", "coverage_summary", "uncovered_paths"),
            ["/uncovered"],
        ),
        (
            ("result", "coverage_summary", "orphaned_entry_paths"),
            ["/orphaned"],
        ),
        (
            ("result", "coverage_summary", "orphaned_exemption_paths"),
            ["/orphaned"],
        ),
        (
            ("result", "coverage_summary", "overlapping_paths"),
            ["/overlap"],
        ),
        (
            ("result", "coverage_summary", "all_paths_accounted_for"),
            False,
        ),
        (
            ("result", "coverage_summary", "provenance_complete"),
            False,
        ),
        (("result", "document_scope"), "artifact_document"),
        (("result", "document_role"), "consumed_input"),
    ),
)
def test_standalone_schema_forbids_legacy_incomplete_and_wrong_scope_values(
    path: tuple[str, ...],
    value: object,
) -> None:
    bundle = _bundle()
    target = bundle
    for token in path[:-1]:
        target = target[token]
    target[path[-1]] = value
    _assert_invalid(bundle)


def test_standalone_schema_forbids_engine_private_entries_and_references() -> None:
    entry_private = _bundle()
    entry_private["result"]["ledger"]["entries"][0]["visibility"] = (
        "engine_private"
    )
    _assert_invalid(entry_private)

    reference_private = _bundle()
    entry = next(
        item
        for item in reference_private["result"]["ledger"]["entries"]
        if item["source_references"]
    )
    entry["source_references"][0]["visibility"] = "engine_private"
    _assert_invalid(reference_private)


def test_standalone_schema_constrains_bundle_result_and_context_workflow() -> None:
    wrong_result = _bundle()
    wrong_result["result"]["attachment_name"] = "position_result"
    _assert_invalid(wrong_result)

    wrong_context = _bundle()
    wrong_context["result"]["information_use_context"]["workflow"] = (
        "position_analysis"
    )
    _assert_invalid(wrong_context)

    unexpected_artifact = _bundle()
    unexpected_artifact["artifacts"] = [
        {
            "artifact_name": "opponent_statistics_input",
            "attachment": copy.deepcopy(unexpected_artifact["result"]),
        }
    ]
    _assert_invalid(unexpected_artifact)
