import copy
import json
from dataclasses import replace
from pathlib import Path

import pytest

from skat_ai.api.v1 import ExecutionOptionsV1, execute_document
from skat_ai.application import (
    ApplicationExecutionOptions,
    TrainingDatasetApplicationOptions,
    build_application_invocation,
    execute_application_invocation,
)
from skat_ai.errors import SkatAIInvariantError
from skat_ai.v1_information_provenance_serialization import (
    V1_RESULT_ATTACHMENT_NAMES,
    validate_v1_information_provenance_serialization_checkpoint,
)

ROOT = Path(__file__).resolve().parents[1]

WORKFLOW_CASES = (
    ("grand_second_position.json", "position_result"),
    ("historical_grand_declarer_concession.json", "historical_game_result"),
    ("training_dataset_variable_length.json", "training_dataset_result"),
    ("training_dataset_preparation_unavailable.json", "dataset_preparation_result"),
    ("opponent_statistics.json", "opponent_statistics_result"),
    ("fixed_three_player_historical_list_all_passed.json", "historical_list_result"),
    (
        "fixed_three_player_historical_list_comparison.json",
        "historical_list_comparison_result",
    ),
)


def _load(name: str) -> dict[str, object]:
    return json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize(("example_name", "attachment_name"), WORKFLOW_CASES)
def test_all_seven_results_are_reconciled_before_application_return(
    example_name: str,
    attachment_name: str,
) -> None:
    execution = execute_application_invocation(
        build_application_invocation(
            _load(example_name),
            input_reference=f"fixture://{example_name}",
        )
    )
    checkpoint = execution.information_provenance_enforcement

    assert checkpoint is not None
    assert checkpoint.result_attachment_name == attachment_name
    assert checkpoint.completed_stages[-1] == "final_serialization"
    assert V1_RESULT_ATTACHMENT_NAMES[execution.result.workflow.value] == attachment_name
    validate_v1_information_provenance_serialization_checkpoint(execution)


def test_result_reconciliation_rejects_value_and_key_order_mutation() -> None:
    execution = execute_application_invocation(
        build_application_invocation(
            _load("opponent_statistics.json"),
            input_reference="fixture://statistics",
        )
    )
    document = execution.result.to_dict()["document"]
    changed = dict(document)
    changed["input_file"] = "changed"
    reordered = dict(reversed(tuple(document.items())))

    for mutation in (changed, reordered):
        forged = copy.copy(execution)
        forged_result = copy.copy(execution.result)
        object.__setattr__(forged_result, "document", mutation)
        object.__setattr__(forged, "result", forged_result)
        with pytest.raises(SkatAIInvariantError, match="does not match"):
            validate_v1_information_provenance_serialization_checkpoint(forged)


def test_result_reconciliation_rejects_envelope_warning_mutation() -> None:
    execution = execute_application_invocation(
        build_application_invocation(
            _load("opponent_statistics.json"),
            input_reference="fixture://statistics-envelope",
        )
    )
    checkpoint = execution.information_provenance_enforcement
    assert checkpoint is not None
    assert checkpoint.result_envelope_to_dict() == execution.result.to_dict()

    forged = copy.copy(execution)
    forged_result = copy.copy(execution.result)
    object.__setattr__(forged_result, "warnings", ("forged warning",))
    object.__setattr__(forged, "result", forged_result)

    with pytest.raises(SkatAIInvariantError, match="envelope"):
        validate_v1_information_provenance_serialization_checkpoint(forged)


def test_result_reconciliation_rejects_provenance_bundle_mutation() -> None:
    execution = execute_application_invocation(
        build_application_invocation(
            _load("opponent_statistics.json"),
            input_reference="fixture://statistics-provenance",
        )
    )
    assert execution.provenance is not None
    forged = copy.copy(execution)
    object.__setattr__(
        forged,
        "provenance",
        replace(
            execution.provenance,
            attachments=execution.provenance.attachments[:-1],
        ),
    )

    with pytest.raises(SkatAIInvariantError, match="provenance"):
        validate_v1_information_provenance_serialization_checkpoint(forged)


def test_actual_artifact_reconciliation_is_exact_and_absence_is_enforced() -> None:
    invocation = build_application_invocation(
        _load("training_dataset_variable_length.json"),
        input_reference="fixture://dataset",
        options=ApplicationExecutionOptions(
            training_dataset=TrainingDatasetApplicationOptions(
                operation="historical_opponent_statistics_aggregation",
                export_opponent_statistics=True,
            )
        ),
    )
    execution = execute_application_invocation(invocation)
    assert tuple(item.name for item in execution.artifacts) == (
        "opponent_statistics_input",
    )
    validate_v1_information_provenance_serialization_checkpoint(execution)

    missing = replace(execution, artifacts=())
    with pytest.raises(SkatAIInvariantError, match="actual artifacts"):
        validate_v1_information_provenance_serialization_checkpoint(missing)

    forged = copy.copy(execution)
    artifact = copy.copy(execution.artifacts[0])
    object.__setattr__(artifact, "document", {"changed": True})
    object.__setattr__(forged, "artifacts", (artifact,))
    with pytest.raises(SkatAIInvariantError, match="does not match"):
        validate_v1_information_provenance_serialization_checkpoint(forged)


def test_public_omission_and_opt_in_results_remain_equal_after_stripping_sidecar() -> None:
    source = _load("opponent_statistics.json")
    omitted = execute_document(source)
    included = execute_document(
        source,
        options=ExecutionOptionsV1(include_provenance=True),
    )

    omitted_document = omitted.result.to_dict()["document"]
    included_document = included.result.to_dict()["document"]
    included_document.pop("field_provenance")
    assert included_document == omitted_document


def test_equal_execution_has_equal_internal_enforcement_checkpoint() -> None:
    source = _load("opponent_statistics.json")
    first = execute_application_invocation(
        build_application_invocation(source, input_reference="fixture://same")
    )
    second = execute_application_invocation(
        build_application_invocation(source, input_reference="fixture://same")
    )
    assert first.information_provenance_enforcement == (
        second.information_provenance_enforcement
    )
