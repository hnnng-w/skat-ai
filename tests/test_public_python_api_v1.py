import builtins
import json
from dataclasses import FrozenInstanceError, fields
from pathlib import Path

import pytest
from jsonschema import FormatChecker

import main as main_module
import skat_ai.api.v1.execution as facade_module
import skat_ai.api.v1.schema_validation as schema_validation_module
import skat_ai.application as application_module
from skat_ai.api.v1 import (
    DEFAULT_INPUT_REFERENCE_V1,
    EXECUTION_ARTIFACT_NAMES_V1,
    ExecutionArtifactV1,
    ExecutionOptionsV1,
    ExecutionResultV1,
    RequestDocumentV1,
    ResultDocumentV1,
    WorkflowV1,
    execute,
    execute_document,
    parse_request,
    serialize_result,
)
from skat_ai.application import (
    ApplicationArtifact,
    ApplicationExecutionResult,
    HistoricalGameApplicationOptions,
    PositionAnalysisApplicationOptions,
    TrainingDatasetApplicationOptions,
    build_application_invocation,
    execute_application_invocation,
    validate_application_invocation,
)
from skat_ai.errors import (
    SkatAIError,
    SkatAIInvariantError,
    SkatAIResourceError,
    SkatAISchemaError,
    SkatAISerializationError,
    SkatAIValidationError,
    SkatAIWorkflowError,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = PROJECT_ROOT / "examples"


def load_example(name: str) -> dict[str, object]:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


WORKFLOW_EXAMPLES = (
    (
        "grand_second_position.json",
        WorkflowV1.POSITION_ANALYSIS,
        "position",
        {"sample_count_override": 1, "random_seed_override": 42},
    ),
    (
        "historical_grand_normal_completion.json",
        WorkflowV1.HISTORICAL_GAME,
        "historical_game_summary",
        {},
    ),
    (
        "training_dataset_normal_play.json",
        WorkflowV1.TRAINING_DATASET,
        "training_dataset_summary",
        {},
    ),
    (
        "training_dataset_preparation_unavailable.json",
        WorkflowV1.TRAINING_DATASET_PREPARATION,
        "training_dataset_preparation_summary",
        {},
    ),
    (
        "opponent_statistics.json",
        WorkflowV1.OPPONENT_STATISTICS,
        "opponent_statistics_summary",
        {},
    ),
    (
        "fixed_three_player_historical_list_mixed.json",
        WorkflowV1.FIXED_THREE_PLAYER_HISTORICAL_LIST,
        "fixed_three_player_historical_list_summary",
        {},
    ),
    (
        "fixed_three_player_historical_list_comparison.json",
        WorkflowV1.FIXED_THREE_PLAYER_HISTORICAL_LIST_COMPARISON,
        "fixed_three_player_historical_list_comparison_summary",
        {},
    ),
)


def test_execution_options_are_recursive_defensive_immutable_and_deterministic() -> None:
    workflow_options = {"rolling_source_partitions": ["train"]}
    statistics = load_example("opponent_statistics.json")
    options = ExecutionOptionsV1(
        validate_output=False,
        workflow_options=workflow_options,
        opponent_statistics_document=statistics,
        opponent_statistics_reference="descriptive:statistics",
    )
    workflow_options["rolling_source_partitions"].append("test")
    statistics["opponent_statistics_input"]["records"].clear()

    assert options.workflow_options["rolling_source_partitions"] == ("train",)
    assert len(options.opponent_statistics_document["opponent_statistics_input"]["records"]) == 2
    assert options.to_dict() == {
        "validate_output": False,
        "workflow_options": {"rolling_source_partitions": ["train"]},
        "opponent_statistics_document": load_example("opponent_statistics.json"),
        "opponent_statistics_reference": "descriptive:statistics",
    }
    with pytest.raises(TypeError):
        options.workflow_options["new"] = True
    with pytest.raises(FrozenInstanceError):
        options.validate_output = True
    with pytest.raises(SkatAIValidationError, match="supplied together"):
        ExecutionOptionsV1(opponent_statistics_document=load_example("opponent_statistics.json"))
    with pytest.raises(SkatAIValidationError, match="supplied together"):
        ExecutionOptionsV1(opponent_statistics_reference="statistics")
    with pytest.raises(TypeError):
        ExecutionOptionsV1(output_path="result.json")
    with pytest.raises(TypeError):
        ExecutionOptionsV1(provenance=True)


def test_public_execution_contracts_are_frozen_defensive_and_flattened() -> None:
    artifact_source = {"opponent_statistics_input": {"records": []}}
    artifact = ExecutionArtifactV1(
        name="opponent_statistics_input",
        document=artifact_source,
    )
    result = ExecutionResultV1(
        result=ResultDocumentV1(
            workflow=WorkflowV1.TRAINING_DATASET,
            document={"input_file": "memory", "summary": {"status": "complete"}},
            warnings=("bounded",),
        ),
        artifacts=[artifact],
    )
    artifact_source["opponent_statistics_input"]["records"].append({"changed": True})

    assert EXECUTION_ARTIFACT_NAMES_V1 == ("opponent_statistics_input",)
    assert result.artifacts == (artifact,)
    assert result.to_dict() == {
        "api_contract_version": 1,
        "workflow": "training_dataset",
        "document": {"input_file": "memory", "summary": {"status": "complete"}},
        "warnings": ["bounded"],
        "artifacts": [
            {
                "name": "opponent_statistics_input",
                "document": {"opponent_statistics_input": {"records": []}},
            }
        ],
    }
    with pytest.raises(SkatAIValidationError, match="one of"):
        ExecutionArtifactV1(name="unknown", document={})
    with pytest.raises(SkatAIValidationError, match="duplicate"):
        ExecutionResultV1(result=result.result, artifacts=(artifact, artifact))


@pytest.mark.parametrize(
    ("example_name", "workflow", "_result_key", "_workflow_options"),
    WORKFLOW_EXAMPLES,
)
def test_parse_request_detects_all_seven_root_workflows(
    example_name: str,
    workflow: WorkflowV1,
    _result_key: str,
    _workflow_options: dict[str, object],
) -> None:
    source = load_example(example_name)
    request = parse_request(source)
    source.clear()

    assert request.workflow is workflow
    assert request.api_contract_version == 1
    assert request.document


def test_parse_request_reports_deterministic_rfc6901_schema_path() -> None:
    invalid = load_example("grand_second_position.json")
    invalid["sample_count"] = 0

    paths = []
    for _ in range(2):
        with pytest.raises(SkatAISchemaError) as caught:
            parse_request(invalid)
        paths.append(caught.value.path)

    assert paths == ["/sample_count", "/sample_count"]


def test_packaged_validators_retain_input_format_checker_only() -> None:
    schema_validation_module._validator_for.cache_clear()
    input_validator = schema_validation_module._validator_for("input.schema.json")
    output_validator = schema_validation_module._validator_for("output.schema.json")

    assert isinstance(input_validator.format_checker, FormatChecker)
    assert output_validator.format_checker is None


def test_execute_revalidates_direct_requests_and_rejects_forged_workflow() -> None:
    request = RequestDocumentV1(
        workflow=WorkflowV1.HISTORICAL_GAME,
        document=load_example("grand_second_position.json"),
    )

    with pytest.raises(SkatAIWorkflowError, match="does not match"):
        execute(request)

    valid = parse_request(load_example("grand_second_position.json"))
    object.__setattr__(valid, "api_contract_version", 2)
    with pytest.raises(SkatAIValidationError, match="api_contract_version"):
        execute(valid)


def test_execute_refreezes_a_forged_request_document() -> None:
    request = parse_request(load_example("grand_second_position.json"))
    forged = request.to_dict()["document"]
    forged["caller_metadata"] = object()
    object.__setattr__(request, "document", forged)

    with pytest.raises(SkatAIValidationError, match="JSON-compatible"):
        execute(request)


@pytest.mark.parametrize(
    ("example_name", "workflow", "result_key", "workflow_options"),
    WORKFLOW_EXAMPLES,
)
def test_all_seven_public_executions_match_application_results(
    example_name: str,
    workflow: WorkflowV1,
    result_key: str,
    workflow_options: dict[str, object],
) -> None:
    document = load_example(example_name)
    reference = f"opaque:{example_name}"
    public = execute_document(
        document,
        options=ExecutionOptionsV1(workflow_options=workflow_options),
        input_reference=reference,
    )
    application = execute_application_invocation(
        build_application_invocation(
            document,
            input_reference=reference,
            options=facade_module._translate_workflow_options(workflow, workflow_options),
        )
    )

    assert public.result == application.result
    assert public.artifacts == ()
    assert public.result.document["input_file"] == reference
    assert result_key in public.result.document


def test_position_search_multi_step_and_policy_comparison_execute() -> None:
    result = execute_document(
        load_example("grand_bounded_search_exhaustive.json"),
        options=ExecutionOptionsV1(
            workflow_options={
                "multi_step_count": 1,
                "compare_policies": True,
                "expected_value_sample_count": 1,
            }
        ),
    ).result.document

    assert result["bounded_search_result"]["status"] == "complete"
    assert result["multi_step_result"]["steps_simulated"] == 1
    assert result["policy_comparison_result"]["policy_results"]


def test_all_historical_submodes_and_replay_coaching_execute_together() -> None:
    result = execute_document(
        load_example("historical_grand_normal_completion.json"),
        options=ExecutionOptionsV1(
            workflow_options={
                "decision_snapshots": True,
                "immediate_review": True,
                "search_review": True,
                "replay_coaching": True,
                "search_seed": 71,
                "search_budget_profile": "interactive_v1",
                "immediate_sample_count": 1,
                "immediate_base_random_seed": 42,
            }
        ),
    ).result.document["historical_game_summary"]

    assert result["decision_snapshot_summary"]["snapshot_count"] == 30
    assert result["historical_game_review_summary"]["decision_count"] == 30
    assert result["historical_search_review_summary"]["decision_counts"]["decision_count"] == 30
    assert result["historical_replay_coaching_summary"]["report_method"] == (
        "historical_replay_coaching_v1"
    )


@pytest.mark.parametrize(
    ("example_name", "workflow_options", "result_key"),
    [
        ("training_dataset_normal_play.json", {}, "training_dataset_summary"),
        (
            "training_dataset_partition_audit.json",
            {"operation": "partition_audit", "partition_audit_mode": "report_only"},
            "dataset_partition_audit_summary",
        ),
        (
            "historical_opponent_policy_evaluation_dataset.json",
            {"operation": "rolling_opponent_policy_evaluation"},
            "rolling_opponent_policy_evaluation_summary",
        ),
        (
            "training_dataset_normal_play.json",
            {
                "operation": "bounded_search_evaluation",
                "bounded_search_seed": 71,
                "bounded_search_max_decisions": 1,
            },
            "bounded_search_evaluation_summary",
        ),
        (
            "training_dataset_normal_play.json",
            {"operation": "historical_opponent_statistics_aggregation"},
            "historical_opponent_statistics_aggregation_summary",
        ),
    ],
)
def test_all_five_training_dataset_operations_execute(
    example_name: str,
    workflow_options: dict[str, object],
    result_key: str,
) -> None:
    document = execute_document(
        load_example(example_name),
        options=ExecutionOptionsV1(workflow_options=workflow_options),
    ).result.document

    assert set(document) == {"input_file", result_key}


def test_dataset_preparation_complete_and_unavailable_are_normal_results() -> None:
    complete = execute_document(
        load_example("training_dataset_preparation_known_opponent.json")
    ).result.document["training_dataset_preparation_summary"]
    unavailable = execute_document(
        load_example("training_dataset_preparation_unavailable.json")
    ).result.document["training_dataset_preparation_summary"]

    assert complete["plan"]["status"] == "complete"
    assert complete["training_dataset_input"] is not None
    assert unavailable["plan"]["status"] == "unavailable"
    assert unavailable["training_dataset_input"] is None


def test_historical_list_final_lot_required_and_comparison_execute() -> None:
    final = execute_document(
        load_example("fixed_three_player_historical_list_mixed.json")
    ).result.document["fixed_three_player_historical_list_summary"]
    lot_required = execute_document(
        load_example("fixed_three_player_historical_list_all_passed.json")
    ).result.document["fixed_three_player_historical_list_summary"]
    comparison = execute_document(
        load_example("fixed_three_player_historical_list_comparison.json")
    ).result.document["fixed_three_player_historical_list_comparison_summary"]

    assert final["ranking_status"] == "final"
    assert lot_required["ranking_status"] == "lot_required"
    assert len(comparison["comparisons"]) == 1


def test_external_opponent_statistics_are_validated_injected_and_not_executed() -> None:
    result = execute_document(
        load_example("grand_second_position.json"),
        options=ExecutionOptionsV1(
            workflow_options={
                "sample_count_override": 1,
                "random_seed_override": 42,
                "use_profile_presets_override": True,
                "left_opponent_player_id": "opponent-123",
            },
            opponent_statistics_document=load_example("opponent_statistics.json"),
            opponent_statistics_reference="descriptive:opponents",
        ),
    ).result.document

    assert result["opponent_profile_application_summary"]["statistics_input_file"] == (
        "descriptive:opponents"
    )
    with pytest.raises(SkatAIWorkflowError, match="opponent_statistics workflow"):
        execute_document(
            load_example("grand_second_position.json"),
            options=ExecutionOptionsV1(
                opponent_statistics_document=load_example("grand_second_position.json"),
                opponent_statistics_reference="wrong-workflow",
            ),
        )


def test_historical_external_opponent_statistics_preserve_reference() -> None:
    result = execute_document(
        load_example("historical_grand_normal_completion.json"),
        options=ExecutionOptionsV1(
            workflow_options={
                "immediate_review": True,
                "immediate_sample_count": 1,
                "immediate_base_random_seed": 42,
                "use_profile_presets_override": True,
            },
            opponent_statistics_document=load_example(
                "historical_opponent_statistics.json"
            ),
            opponent_statistics_reference="descriptive:historical-opponents",
        ),
    ).result.document

    application = result["historical_opponent_profile_application_summary"]
    assert application["statistics_input_file"] == "descriptive:historical-opponents"


def test_public_artifact_is_separate_schema_valid_and_deterministic() -> None:
    result = execute_document(
        load_example("training_dataset_normal_play.json"),
        options=ExecutionOptionsV1(
            workflow_options={
                "operation": "historical_opponent_statistics_aggregation",
                "export_opponent_statistics": True,
            }
        ),
    )
    serialized = serialize_result(result)

    assert "opponent_statistics_input" not in serialized["document"]
    assert [artifact["name"] for artifact in serialized["artifacts"]] == [
        "opponent_statistics_input"
    ]
    assert set(serialized["artifacts"][0]["document"]) == {
        "opponent_statistics_input"
    }


def test_workflow_option_allowlists_exactly_match_application_contract_fields() -> None:
    assert facade_module._POSITION_OPTION_NAMES == tuple(
        field.name for field in fields(PositionAnalysisApplicationOptions)
    )
    assert facade_module._HISTORICAL_OPTION_NAMES == tuple(
        field.name for field in fields(HistoricalGameApplicationOptions)
    )
    assert facade_module._TRAINING_DATASET_OPTION_NAMES == tuple(
        field.name for field in fields(TrainingDatasetApplicationOptions)
    )


@pytest.mark.parametrize("field_name", ["output_path", "quiet", "provenance"])
def test_unknown_transport_and_provenance_workflow_options_are_rejected(
    field_name: str,
) -> None:
    with pytest.raises(SkatAIWorkflowError, match="unsupported"):
        execute_document(
            load_example("grand_second_position.json"),
            options=ExecutionOptionsV1(workflow_options={field_name: True}),
        )


def test_fields_from_another_workflow_and_simple_workflow_options_are_rejected() -> None:
    with pytest.raises(SkatAIWorkflowError, match="unsupported"):
        execute_document(
            load_example("historical_grand_normal_completion.json"),
            options=ExecutionOptionsV1(workflow_options={"multi_step_count": 1}),
        )
    with pytest.raises(SkatAIWorkflowError, match="empty"):
        execute_document(
            load_example("opponent_statistics.json"),
            options=ExecutionOptionsV1(workflow_options={"operation": "summary"}),
        )


def test_application_semantic_option_validation_is_always_reused() -> None:
    with pytest.raises(SkatAIWorkflowError, match="requires multi_step_count"):
        execute_document(
            load_example("grand_second_position.json"),
            options=ExecutionOptionsV1(workflow_options={"compare_policies": True}),
        )
    with pytest.raises(SkatAIWorkflowError, match="requires bounded_search_seed"):
        execute_document(
            load_example("training_dataset_normal_play.json"),
            options=ExecutionOptionsV1(
                workflow_options={"operation": "bounded_search_evaluation"}
            ),
        )
    with pytest.raises(SkatAIWorkflowError, match="does not accept"):
        execute_document(
            load_example("training_dataset_normal_play.json"),
            options=ExecutionOptionsV1(
                workflow_options={
                    "operation": "summary",
                    "bounded_search_partitions": ["validation", "test"],
                }
            ),
        )


def _malformed_application_result(invocation) -> ApplicationExecutionResult:
    validate_application_invocation(invocation)
    return ApplicationExecutionResult(
        result=ResultDocumentV1(
            workflow=invocation.request.workflow,
            document={"input_file": invocation.input_reference},
        )
    )


def test_output_validation_can_be_disabled_but_input_and_semantics_cannot(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        application_module,
        "execute_application_invocation",
        _malformed_application_result,
    )
    request = parse_request(load_example("grand_second_position.json"))

    with pytest.raises(SkatAISchemaError):
        execute(request)
    result = execute(request, options=ExecutionOptionsV1(validate_output=False))
    assert result.result.document == {"input_file": DEFAULT_INPUT_REFERENCE_V1}

    invalid = load_example("grand_second_position.json")
    invalid["sample_count"] = 0
    with pytest.raises(SkatAISchemaError):
        execute_document(invalid, options=ExecutionOptionsV1(validate_output=False))


def test_auxiliary_artifact_validation_can_be_disabled(monkeypatch) -> None:
    def fake_execute(invocation) -> ApplicationExecutionResult:
        validate_application_invocation(invocation)
        return ApplicationExecutionResult(
            result=ResultDocumentV1(
                workflow=invocation.request.workflow,
                document={"input_file": invocation.input_reference},
            ),
            artifacts=(
                ApplicationArtifact(
                    name="opponent_statistics_input",
                    document={"invalid": True},
                ),
            ),
        )

    monkeypatch.setattr(application_module, "execute_application_invocation", fake_execute)
    monkeypatch.setattr(facade_module, "validate_output_document", lambda _document: None)

    with pytest.raises(SkatAISchemaError):
        execute_document(load_example("training_dataset_normal_play.json"))
    result = execute_document(
        load_example("training_dataset_normal_play.json"),
        options=ExecutionOptionsV1(validate_output=False),
    )
    assert result.artifacts[0].document == {"invalid": True}


def test_execute_document_validates_and_detects_once_and_matches_explicit_path(
    monkeypatch,
) -> None:
    document = load_example("grand_second_position.json")
    counts = {"schema": 0, "workflow": 0, "application": 0}
    real_schema = facade_module.validate_input_document
    real_detect = facade_module._detect_workflow
    real_execute = application_module.execute_application_invocation

    def counted_schema(value):
        counts["schema"] += 1
        return real_schema(value)

    def counted_detect(value):
        counts["workflow"] += 1
        return real_detect(value)

    def counted_execute(invocation):
        counts["application"] += 1
        return real_execute(invocation)

    monkeypatch.setattr(facade_module, "validate_input_document", counted_schema)
    monkeypatch.setattr(facade_module, "_detect_workflow", counted_detect)
    monkeypatch.setattr(application_module, "execute_application_invocation", counted_execute)
    options = ExecutionOptionsV1(
        workflow_options={"sample_count_override": 1, "random_seed_override": 42}
    )
    convenient = execute_document(document, options=options, input_reference="same")

    assert counts == {"schema": 1, "workflow": 1, "application": 1}
    monkeypatch.setattr(facade_module, "validate_input_document", real_schema)
    monkeypatch.setattr(facade_module, "_detect_workflow", real_detect)
    monkeypatch.setattr(application_module, "execute_application_invocation", real_execute)
    explicit = execute(
        parse_request(document),
        options=options,
        input_reference="same",
    )
    assert convenient == explicit


def test_serialization_is_fresh_deterministic_and_type_checked() -> None:
    result = execute_document(
        load_example("opponent_statistics.json"),
        input_reference="serialize-reference",
    )
    first = serialize_result(result)
    second = serialize_result(result)
    first["document"]["input_file"] = "changed"

    assert second["document"]["input_file"] == "serialize-reference"
    assert list(second) == [
        "api_contract_version",
        "workflow",
        "document",
        "warnings",
        "artifacts",
    ]
    with pytest.raises(SkatAISerializationError):
        serialize_result(result.result)


@pytest.mark.parametrize(
    ("raw_error", "public_error"),
    [
        (ValueError("domain value"), SkatAIValidationError),
        (OSError("resource"), SkatAIResourceError),
    ],
)
def test_raw_boundary_errors_are_translated_with_message_and_cause(
    monkeypatch,
    raw_error: Exception,
    public_error: type[SkatAIError],
) -> None:
    def fail(_invocation):
        raise raw_error

    monkeypatch.setattr(application_module, "execute_application_invocation", fail)
    with pytest.raises(public_error) as caught:
        execute_document(load_example("opponent_statistics.json"))

    assert str(caught.value) == str(raw_error)
    assert caught.value.path is None
    assert caught.value.__cause__ is raw_error


def test_existing_public_errors_are_preserved_and_unexpected_errors_escape(
    monkeypatch,
) -> None:
    marker = SkatAIWorkflowError("preserve me")

    def fail_public(_invocation):
        raise marker

    monkeypatch.setattr(application_module, "execute_application_invocation", fail_public)
    with pytest.raises(SkatAIWorkflowError) as caught:
        execute_document(load_example("opponent_statistics.json"))
    assert caught.value is marker

    unexpected = RuntimeError("unexpected")

    def fail_unexpected(_invocation):
        raise unexpected

    monkeypatch.setattr(application_module, "execute_application_invocation", fail_unexpected)
    with pytest.raises(RuntimeError) as caught:
        execute_document(load_example("opponent_statistics.json"))
    assert caught.value is unexpected


@pytest.mark.parametrize(
    "state",
    ("complete", "partial", "timeout", "unavailable", "final", "lot_required", "not_assessable"),
)
def test_every_normal_result_state_passes_through_execution(
    monkeypatch,
    state: str,
) -> None:
    def fake_execute(invocation) -> ApplicationExecutionResult:
        validate_application_invocation(invocation)
        return ApplicationExecutionResult(
            result=ResultDocumentV1(
                workflow=invocation.request.workflow,
                document={"input_file": invocation.input_reference, "status": state},
            )
        )

    monkeypatch.setattr(application_module, "execute_application_invocation", fake_execute)
    result = execute_document(
        load_example("opponent_statistics.json"),
        options=ExecutionOptionsV1(validate_output=False),
    )
    assert result.result.document["status"] == state


def test_schema_resources_are_lazy_cwd_and_repository_schema_independent(
    monkeypatch,
    tmp_path: Path,
) -> None:
    schema_validation_module._validator_for.cache_clear()
    authoritative_schema_directory = PROJECT_ROOT / "schemas"
    real_open = Path.open

    def reject_authoritative_schema_read(path, *args, **kwargs):
        if Path(path).resolve().is_relative_to(authoritative_schema_directory):
            raise AssertionError("Runtime validation read the authoritative schema directory.")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", reject_authoritative_schema_read)
    monkeypatch.chdir(tmp_path)
    result = execute_document(load_example("opponent_statistics.json"))

    assert result.result.workflow is WorkflowV1.OPPONENT_STATISTICS


def test_missing_invalid_and_unresolvable_packaged_schemas_use_stable_errors(
    monkeypatch,
    tmp_path: Path,
) -> None:
    missing = tmp_path / "missing"
    monkeypatch.setattr(schema_validation_module, "_schema_resource_root", lambda: missing)
    schema_validation_module._validator_for.cache_clear()
    with pytest.raises(SkatAIResourceError):
        parse_request(load_example("opponent_statistics.json"))

    invalid = tmp_path / "invalid"
    invalid.mkdir()
    (invalid / "input.schema.json").write_text(
        json.dumps(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "$id": "https://example.local/invalid/input.schema.json",
                "type": 7,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(schema_validation_module, "_schema_resource_root", lambda: invalid)
    schema_validation_module._validator_for.cache_clear()
    with pytest.raises(SkatAIInvariantError):
        parse_request(load_example("opponent_statistics.json"))

    unresolved = tmp_path / "unresolved"
    unresolved.mkdir()
    (unresolved / "input.schema.json").write_text(
        json.dumps(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "$id": "https://example.local/unresolved/input.schema.json",
                "$ref": "https://network-resolution-is-forbidden.invalid/schema.json",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(schema_validation_module, "_schema_resource_root", lambda: unresolved)
    schema_validation_module._validator_for.cache_clear()
    with pytest.raises(SkatAIResourceError, match="unavailable"):
        parse_request(load_example("opponent_statistics.json"))
    schema_validation_module._validator_for.cache_clear()


@pytest.mark.parametrize(
    ("content", "additional_content", "match"),
    [
        (b"{", None, "not valid JSON"),
        (b"\xff", None, "not valid UTF-8"),
        (b"[]", None, "JSON object"),
        (
            b'{"$schema":"https://json-schema.org/draft/2020-12/schema"}',
            None,
            "non-empty \\$id",
        ),
        (
            b'{"$schema":"https://json-schema.org/draft/2020-12/schema",'
            b'"$id":"https://example.local/duplicate"}',
            b'{"$schema":"https://json-schema.org/draft/2020-12/schema",'
            b'"$id":"https://example.local/duplicate"}',
            "duplicated",
        ),
    ],
)
def test_malformed_packaged_schema_resources_are_invariant_errors(
    monkeypatch,
    tmp_path: Path,
    content: bytes,
    additional_content: bytes | None,
    match: str,
) -> None:
    resource_root = tmp_path / "resources"
    resource_root.mkdir()
    (resource_root / "input.schema.json").write_bytes(content)
    if additional_content is not None:
        (resource_root / "other.schema.json").write_bytes(additional_content)
    monkeypatch.setattr(
        schema_validation_module,
        "_schema_resource_root",
        lambda: resource_root,
    )
    schema_validation_module._validator_for.cache_clear()

    with pytest.raises(SkatAIInvariantError, match=match):
        parse_request(load_example("opponent_statistics.json"))

    schema_validation_module._validator_for.cache_clear()


def test_facade_performs_no_transport_io_or_printing_after_lazy_schema_load(
    monkeypatch,
) -> None:
    document = load_example("opponent_statistics.json")
    execute_document(document)

    def unexpected_call(*_args, **_kwargs):
        raise AssertionError("Facade attempted transport I/O or printing.")

    monkeypatch.setattr(Path, "open", unexpected_call)
    monkeypatch.setattr(builtins, "print", unexpected_call)
    result = execute_document(document)

    assert result.result.workflow is WorkflowV1.OPPONENT_STATISTICS


def test_legacy_cli_parity_and_public_exports_do_not_import_main(tmp_path: Path) -> None:
    input_path = EXAMPLES / "grand_second_position.json"
    output_path = tmp_path / "legacy.json"
    public = execute_document(
        load_example("grand_second_position.json"),
        options=ExecutionOptionsV1(
            workflow_options={"sample_count_override": 1, "random_seed_override": 42}
        ),
        input_reference=str(input_path),
    )
    main_module.run_json_position_analysis(
        file_path=str(input_path),
        sample_count_override=1,
        random_seed_override=42,
        output_path=str(output_path),
        quiet=True,
    )

    assert public.result.to_dict()["document"] == json.loads(
        output_path.read_text(encoding="utf-8")
    )
