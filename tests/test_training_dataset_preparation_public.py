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
from test_fixed_three_player_historical_list_public import (
    UNSUPPORTED_LIST_CLI_ARGUMENTS,
)
from test_input_schema import INPUT_VALIDATOR
from test_output_schema import OUTPUT_VALIDATOR

import skat_ai.training_dataset_preparation_workflow as workflow_module
from skat_ai.dataset_partition_plan import (
    COMPONENT_BALANCED_UNSEEN_PLAYER_ALGORITHM,
    TEMPORAL_KNOWN_OPPONENT_ALGORITHM,
    build_unavailable_dataset_partition_plan,
)
from skat_ai.input_loader import (
    get_input_workflow,
    load_training_dataset_preparation_request_from_json,
)
from skat_ai.training_dataset import (
    build_serializable_training_dataset_input,
    build_training_dataset_input,
)
from skat_ai.training_dataset_preparation import (
    build_serializable_training_dataset_preparation_request,
)
from skat_ai.training_dataset_preparation_workflow import (
    TrainingDatasetPreparationResult,
    build_serializable_training_dataset_preparation_result,
    build_training_dataset_preparation_result,
    validate_training_dataset_preparation_result,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMAS_DIR = PROJECT_ROOT / "schemas"
KNOWN_PATH = (
    PROJECT_ROOT / "examples" / "training_dataset_preparation_known_opponent.json"
)
UNSEEN_PATH = (
    PROJECT_ROOT / "examples" / "training_dataset_preparation_unseen_player.json"
)
UNAVAILABLE_PATH = (
    PROJECT_ROOT / "examples" / "training_dataset_preparation_unavailable.json"
)
PREPARATION_EXAMPLE_PATHS = (KNOWN_PATH, UNSEEN_PATH, UNAVAILABLE_PATH)

SCHEMA_NAMES = (
    "training_dataset_preparation.schema.json",
    "dataset_partition_plan.schema.json",
    "training_dataset_preparation_output.schema.json",
)
SCHEMAS = {
    name: json.loads((SCHEMAS_DIR / name).read_text(encoding="utf-8"))
    for name in (
        *SCHEMA_NAMES,
        "training_dataset.schema.json",
        "dataset_partition_policy.schema.json",
        "dataset_partition_audit.schema.json",
        "historical_game.schema.json",
        "historical_game_end.schema.json",
        "historical_game_event.schema.json",
        "historical_declarer_concession.schema.json",
        "historical_defender_concession.schema.json",
        "historical_declarer_card_exposure.schema.json",
        "historical_defender_open_play.schema.json",
        "historical_open_card_throw.schema.json",
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


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_cli(*args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "main.py"), *(str(arg) for arg in args)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def build_public_output(path: Path) -> tuple[Any, Any, dict[str, Any]]:
    request = load_training_dataset_preparation_request_from_json(str(path))
    result = build_training_dataset_preparation_result(request)
    output = {
        "input_file": str(path),
        "training_dataset_preparation_summary": (
            build_serializable_training_dataset_preparation_result(request, result)
        ),
    }
    return request, result, output


def test_public_request_loading_is_exclusive_ordered_and_immutable() -> None:
    request = load_training_dataset_preparation_request_from_json(str(KNOWN_PATH))
    serialized = build_serializable_training_dataset_preparation_request(request)

    assert get_input_workflow(load_json(KNOWN_PATH)) == "training_dataset_preparation"
    assert [record.record_id for record in request.records] == [
        "known-zero-001",
        "known-zero-002",
        "known-zero-003",
    ]
    assert all(not hasattr(record, "partition") for record in request.records)
    with pytest.raises(FrozenInstanceError):
        request.dataset_id = "changed"  # type: ignore[misc]
    serialized["records"][0]["record_id"] = "changed"
    assert request.records[0].record_id == "known-zero-001"

    with pytest.raises(ValueError, match="cannot be combined"):
        get_input_workflow(
            {
                "training_dataset_preparation_input": {},
                "historical_game_input": {},
            }
        )


@pytest.mark.parametrize(
    ("path", "mode", "expected_algorithm"),
    [
        (KNOWN_PATH, "known_opponent", TEMPORAL_KNOWN_OPPONENT_ALGORITHM),
        (UNSEEN_PATH, "unseen_player", COMPONENT_BALANCED_UNSEEN_PLAYER_ALGORITHM),
    ],
)
def test_dispatch_calls_one_generator_and_materializes_complete_plan_once(
    monkeypatch,
    path: Path,
    mode: str,
    expected_algorithm: str,
) -> None:
    request = load_training_dataset_preparation_request_from_json(str(path))
    calls = {"known": 0, "unseen": 0, "materialize": 0}
    real_known = workflow_module.generate_temporal_known_opponent_dataset_partition_plan
    real_unseen = (
        workflow_module.generate_component_balanced_unseen_player_dataset_partition_plan
    )
    real_materialize = workflow_module.materialize_prepared_training_dataset

    def known(value):
        calls["known"] += 1
        return real_known(value)

    def unseen(value):
        calls["unseen"] += 1
        return real_unseen(value)

    def materialize(value, plan):
        calls["materialize"] += 1
        return real_materialize(value, plan)

    monkeypatch.setattr(
        workflow_module,
        "generate_temporal_known_opponent_dataset_partition_plan",
        known,
    )
    monkeypatch.setattr(
        workflow_module,
        "generate_component_balanced_unseen_player_dataset_partition_plan",
        unseen,
    )
    monkeypatch.setattr(
        workflow_module,
        "materialize_prepared_training_dataset",
        materialize,
    )

    result = build_training_dataset_preparation_result(request)

    assert calls == {
        "known": int(mode == "known_opponent"),
        "unseen": int(mode == "unseen_player"),
        "materialize": 1,
    }
    assert result.plan.algorithm == expected_algorithm
    assert result.plan.status == "complete"


def test_unavailable_plan_never_materializes_and_is_a_successful_result(
    monkeypatch,
) -> None:
    request = load_training_dataset_preparation_request_from_json(str(UNAVAILABLE_PATH))

    def unexpected_materialization(*args, **kwargs):
        raise AssertionError("Unavailable preparation attempted materialization.")

    monkeypatch.setattr(
        workflow_module,
        "materialize_prepared_training_dataset",
        unexpected_materialization,
    )
    result = build_training_dataset_preparation_result(request)
    serialized = build_serializable_training_dataset_preparation_result(request, result)

    assert result.plan.status == "unavailable"
    assert result.plan.unavailable_reason == "missing_played_at"
    assert serialized["training_dataset_input"] is None
    assert serialized["partition_audit"] is None


@pytest.mark.parametrize(
    ("path", "algorithm", "reason"),
    [
        (KNOWN_PATH, TEMPORAL_KNOWN_OPPONENT_ALGORITHM, "missing_played_at"),
        (KNOWN_PATH, TEMPORAL_KNOWN_OPPONENT_ALGORITHM, "insufficient_time_groups"),
        (
            KNOWN_PATH,
            TEMPORAL_KNOWN_OPPONENT_ALGORITHM,
            "known_opponent_train_coverage_unsatisfied",
        ),
        (
            KNOWN_PATH,
            TEMPORAL_KNOWN_OPPONENT_ALGORITHM,
            "non_empty_partition_requirement_unsatisfied",
        ),
        (
            UNSEEN_PATH,
            COMPONENT_BALANCED_UNSEEN_PLAYER_ALGORITHM,
            "insufficient_player_components",
        ),
        (
            UNSEEN_PATH,
            COMPONENT_BALANCED_UNSEEN_PLAYER_ALGORITHM,
            "component_distribution_infeasible",
        ),
        (
            UNSEEN_PATH,
            COMPONENT_BALANCED_UNSEEN_PLAYER_ALGORITHM,
            "non_empty_partition_requirement_unsatisfied",
        ),
    ],
)
def test_all_stable_unavailable_reasons_serialize_without_partial_data(
    path: Path,
    algorithm: str,
    reason: str,
) -> None:
    request = load_training_dataset_preparation_request_from_json(str(path))
    plan = build_unavailable_dataset_partition_plan(
        request,
        algorithm=algorithm,
        unavailable_reason=reason,
    )
    result = TrainingDatasetPreparationResult(1, plan, None, None)

    validate_training_dataset_preparation_result(request, result)
    serialized = build_serializable_training_dataset_preparation_result(request, result)

    assert serialized["plan"]["unavailable_reason"] == reason
    assert serialized["plan"]["assignments"] == []
    assert serialized["plan"]["partition_summaries"] == []
    assert serialized["training_dataset_input"] is None
    assert serialized["partition_audit"] is None


@pytest.mark.parametrize("path", [KNOWN_PATH, UNSEEN_PATH])
def test_complete_materialization_preserves_records_and_adds_only_partition(
    path: Path,
) -> None:
    request, result, output = build_public_output(path)
    summary = output["training_dataset_preparation_summary"]
    dataset_data = summary["training_dataset_input"]
    assert dataset_data is not None
    rebuilt = build_training_dataset_input(dataset_data)

    assert rebuilt == result.training_dataset_input
    assert [record.record_id for record in rebuilt.records] == [
        record.record_id for record in request.records
    ]
    assert all(len(record.historical_game.tricks) == 0 for record in rebuilt.records)
    source_records = build_serializable_training_dataset_preparation_request(request)[
        "records"
    ]
    for source_record, materialized_record in zip(
        source_records,
        dataset_data["records"],
        strict=True,
    ):
        assert {key: value for key, value in materialized_record.items() if key != "partition"} == (
            source_record
        )
    assert build_serializable_training_dataset_input(rebuilt) == dataset_data
    assert "CA" in json.dumps(dataset_data)


def test_all_three_standalone_schemas_and_root_schemas_validate_public_examples() -> None:
    preparation_validator = validator("training_dataset_preparation.schema.json")
    plan_validator = validator("dataset_partition_plan.schema.json")
    output_validator = validator("training_dataset_preparation_output.schema.json")

    for path in PREPARATION_EXAMPLE_PATHS:
        input_data = load_json(path)
        request, _result, output = build_public_output(path)
        summary = output["training_dataset_preparation_summary"]

        assert list(INPUT_VALIDATOR.iter_errors(input_data)) == []
        assert list(
            preparation_validator.iter_errors(
                input_data["training_dataset_preparation_input"]
            )
        ) == []
        assert list(plan_validator.iter_errors(summary["plan"])) == []
        assert list(output_validator.iter_errors(summary)) == []
        assert list(OUTPUT_VALIDATOR.iter_errors(output)) == []
        validate_training_dataset_preparation_result(
            request,
            build_training_dataset_preparation_result(request),
        )


def test_schemas_reject_partition_unknown_fields_and_inconsistent_variants() -> None:
    request_data = load_json(KNOWN_PATH)["training_dataset_preparation_input"]
    invalid_request = copy.deepcopy(request_data)
    invalid_request["records"][0]["partition"] = "train"
    assert list(
        validator("training_dataset_preparation.schema.json").iter_errors(
            invalid_request
        )
    )

    _request, _result, output = build_public_output(KNOWN_PATH)
    summary = output["training_dataset_preparation_summary"]
    invalid_plan = copy.deepcopy(summary["plan"])
    invalid_plan["algorithm"] = COMPONENT_BALANCED_UNSEEN_PLAYER_ALGORITHM
    assert list(
        validator("dataset_partition_plan.schema.json").iter_errors(invalid_plan)
    )
    invalid_output = copy.deepcopy(summary)
    invalid_output["training_dataset_input"] = None
    assert list(
        validator("training_dataset_preparation_output.schema.json").iter_errors(
            invalid_output
        )
    )


@pytest.mark.parametrize("path", [KNOWN_PATH, UNSEEN_PATH])
def test_complete_cli_output_is_concise_and_plan_boundary_is_card_free(
    path: Path,
) -> None:
    completed = run_cli("--input", path)

    assert completed.returncode == 0
    assert completed.stderr == ""
    for text in (
        "Automatic Training Dataset Preparation",
        "Dataset identity:",
        "Algorithm:",
        "Status: complete",
        "Source Record and Sample Counts:",
        "Requested weights:",
        "Plan fingerprint:",
        "Train summary:",
        "Validation summary:",
        "Test summary:",
        "Audit evidence: compliant",
        "Materialized Dataset status: created and reusable",
    ):
        assert text in completed.stdout
    assert "record_id" not in completed.stdout
    assert "initial_hand" not in completed.stdout
    assert "CA" not in completed.stdout


def test_unavailable_cli_output_is_successful_without_partial_wording() -> None:
    completed = run_cli("--input", UNAVAILABLE_PATH)

    assert completed.returncode == 0
    assert completed.stderr == ""
    assert "Status: unavailable" in completed.stdout
    assert "Unavailable reason: missing_played_at" in completed.stdout
    assert "Materialized Dataset: not created" in completed.stdout
    assert "Train summary:" not in completed.stdout
    assert "Audit evidence:" not in completed.stdout
    assert "partial" not in completed.stdout.lower()
    assert "fallback" not in completed.stdout.lower()


def test_quiet_output_file_contains_reusable_nested_dataset(tmp_path: Path) -> None:
    output_path = tmp_path / "prepared.json"
    completed = run_cli(
        "--input",
        KNOWN_PATH,
        "--output",
        output_path,
        "--quiet",
    )

    assert completed.returncode == 0
    assert completed.stdout == ""
    assert completed.stderr == ""
    output = load_json(output_path)
    assert list(OUTPUT_VALIDATOR.iter_errors(output)) == []
    nested = output["training_dataset_preparation_summary"][
        "training_dataset_input"
    ]
    assert build_training_dataset_input(nested).dataset_id == (
        "automatic-known-opponent-example"
    )
    assert "CA" in json.dumps(nested)


@pytest.mark.parametrize(
    "option_args",
    UNSUPPORTED_LIST_CLI_ARGUMENTS,
    ids=[arguments[0] for arguments in UNSUPPORTED_LIST_CLI_ARGUMENTS],
)
def test_preparation_cli_rejects_every_non_file_option(
    option_args: tuple[str, ...],
) -> None:
    completed = run_cli("--input", KNOWN_PATH, *option_args)

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert "Training-dataset-preparation inputs accept only" in completed.stderr


def test_generated_output_matrix_appends_three_preparation_scenarios() -> None:
    from scripts.validate_generated_outputs_schema import SCENARIOS

    assert len(SCENARIOS) == 70
    assert tuple(scenario.name for scenario in SCENARIOS[-3:]) == (
        "training_dataset_preparation_known_opponent",
        "training_dataset_preparation_unseen_player",
        "training_dataset_preparation_unavailable",
    )
