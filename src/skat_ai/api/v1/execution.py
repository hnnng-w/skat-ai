from collections.abc import Callable, Mapping
from typing import Any

from skat_ai.api.v1.contracts import (
    DEFAULT_INPUT_REFERENCE_V1,
    PUBLIC_API_CONTRACT_VERSION,
    ExecutionArtifactV1,
    ExecutionOptionsV1,
    ExecutionResultV1,
    RequestDocumentV1,
    ResultDocumentV1,
    WorkflowV1,
)
from skat_ai.api.v1.schema_validation import (
    validate_input_document,
    validate_output_document,
)
from skat_ai.errors import (
    SkatAIError,
    SkatAIResourceError,
    SkatAISchemaError,
    SkatAISerializationError,
    SkatAIValidationError,
    SkatAIWorkflowError,
)

_POSITION_OPTION_NAMES = (
    "sample_count_override",
    "random_seed_override",
    "opponent_strategy_override",
    "opponent_policy_preset_override",
    "opponent_lead_policy_override",
    "opponent_response_policy_override",
    "use_profile_presets_override",
    "left_opponent_lead_policy_override",
    "left_opponent_response_policy_override",
    "right_opponent_lead_policy_override",
    "right_opponent_response_policy_override",
    "multi_step_count",
    "card_selection_policy",
    "expected_value_sample_count",
    "strict_context",
    "compare_policies",
    "comparison_only",
    "left_opponent_player_id",
    "right_opponent_player_id",
)
_HISTORICAL_OPTION_NAMES = (
    "decision_snapshots",
    "immediate_review",
    "search_review",
    "replay_coaching",
    "search_seed",
    "search_budget_profile",
    "immediate_sample_count",
    "immediate_base_random_seed",
    "opponent_policy_preset_override",
    "opponent_lead_policy_override",
    "opponent_response_policy_override",
    "left_opponent_lead_policy_override",
    "left_opponent_response_policy_override",
    "right_opponent_lead_policy_override",
    "right_opponent_response_policy_override",
    "use_profile_presets_override",
)
_TRAINING_DATASET_OPTION_NAMES = (
    "operation",
    "partition_audit_mode",
    "rolling_source_partitions",
    "rolling_evaluation_partitions",
    "bounded_search_seed",
    "bounded_search_partitions",
    "bounded_search_budget_profile",
    "bounded_search_max_decisions",
    "aggregation_included_partitions",
    "aggregation_before",
    "export_opponent_statistics",
)
_TRAINING_DATASET_OPERATION_OPTION_NAMES = {
    "summary": {"operation"},
    "partition_audit": {"operation", "partition_audit_mode"},
    "rolling_opponent_policy_evaluation": {
        "operation",
        "rolling_source_partitions",
        "rolling_evaluation_partitions",
    },
    "bounded_search_evaluation": {
        "operation",
        "bounded_search_seed",
        "bounded_search_partitions",
        "bounded_search_budget_profile",
        "bounded_search_max_decisions",
    },
    "historical_opponent_statistics_aggregation": {
        "operation",
        "aggregation_included_partitions",
        "aggregation_before",
        "export_opponent_statistics",
    },
}

def _at_public_boundary[T](operation: Callable[[], T]) -> T:
    try:
        return operation()
    except SkatAIError:
        raise
    except OSError as error:
        raise SkatAIResourceError(str(error)) from error
    except ValueError as error:
        raise SkatAIValidationError(str(error)) from error


def _detect_workflow(document: Mapping[str, object]) -> WorkflowV1:
    from skat_ai.input_loader import get_input_workflow

    workflow_name = get_input_workflow(dict(document))
    try:
        return WorkflowV1(workflow_name)
    except ValueError as error:
        raise SkatAIWorkflowError(
            f"Unsupported Root workflow: {workflow_name!r}."
        ) from error


def _parse_request(document: object) -> RequestDocumentV1:
    if isinstance(document, Mapping) and "field_provenance" in document:
        raise SkatAISchemaError(
            "field_provenance is an output-only Root field.",
            path="/field_provenance",
        )
    validate_input_document(document)
    if not isinstance(document, Mapping):
        raise SkatAISchemaError("Root document must be an object.", path="")
    workflow = _detect_workflow(document)
    return RequestDocumentV1(workflow=workflow, document=document)


def parse_request(document: object) -> RequestDocumentV1:
    """Validates and immutably wraps one Root input document without execution."""
    return _at_public_boundary(lambda: _parse_request(document))


def _request_document(request: RequestDocumentV1) -> dict[str, Any]:
    request_data = request.to_dict()["document"]
    if not isinstance(request_data, dict):
        raise SkatAIValidationError("request document must be an object.")
    return request_data


def _verify_request(request: object) -> RequestDocumentV1:
    if not isinstance(request, RequestDocumentV1):
        raise SkatAIValidationError("request must be a RequestDocumentV1.")
    if (
        type(request.api_contract_version) is not int
        or request.api_contract_version != PUBLIC_API_CONTRACT_VERSION
    ):
        raise SkatAIValidationError(
            f"api_contract_version must equal {PUBLIC_API_CONTRACT_VERSION}.",
            path="api_contract_version",
        )
    document = _request_document(request)
    validate_input_document(document)
    detected_workflow = _detect_workflow(document)
    if detected_workflow is not request.workflow:
        raise SkatAIWorkflowError(
            "Request wrapper workflow does not match the Root document workflow.",
            path="workflow",
        )
    return RequestDocumentV1(
        api_contract_version=request.api_contract_version,
        workflow=request.workflow,
        document=document,
    )


def _option_values(
    workflow: WorkflowV1,
    workflow_options: Mapping[str, object],
    allowed_names: tuple[str, ...],
) -> dict[str, object]:
    unknown = sorted(set(workflow_options).difference(allowed_names))
    if unknown:
        raise SkatAIWorkflowError(
            f"workflow_options contains fields unsupported by {workflow.value}: {unknown}.",
            path="workflow_options",
        )
    return dict(workflow_options)


def _translate_workflow_options(
    workflow: WorkflowV1,
    workflow_options: Mapping[str, object],
):
    from skat_ai.application import (
        ApplicationExecutionOptions,
        HistoricalGameApplicationOptions,
        PositionAnalysisApplicationOptions,
        TrainingDatasetApplicationOptions,
    )

    if workflow is WorkflowV1.POSITION_ANALYSIS:
        values = _option_values(workflow, workflow_options, _POSITION_OPTION_NAMES)
        return ApplicationExecutionOptions(
            position_analysis=PositionAnalysisApplicationOptions(**values)
        )
    if workflow is WorkflowV1.HISTORICAL_GAME:
        values = _option_values(workflow, workflow_options, _HISTORICAL_OPTION_NAMES)
        return ApplicationExecutionOptions(
            historical_game=HistoricalGameApplicationOptions(**values)
        )
    if workflow is WorkflowV1.TRAINING_DATASET:
        values = _option_values(
            workflow,
            workflow_options,
            _TRAINING_DATASET_OPTION_NAMES,
        )
        operation = values.get("operation", "summary")
        operation_names = (
            _TRAINING_DATASET_OPERATION_OPTION_NAMES.get(operation)
            if isinstance(operation, str)
            else None
        )
        if operation_names is not None:
            incompatible = sorted(set(values).difference(operation_names))
            if incompatible:
                raise SkatAIWorkflowError(
                    f"Training Dataset operation {operation!r} does not accept "
                    f"workflow_options fields: {incompatible}.",
                    path="workflow_options",
                )
        return ApplicationExecutionOptions(
            training_dataset=TrainingDatasetApplicationOptions(**values)
        )
    if workflow_options:
        raise SkatAIWorkflowError(
            f"{workflow.value} requires an empty workflow_options object.",
            path="workflow_options",
        )
    return ApplicationExecutionOptions()


def _validated_external_documents(options: ExecutionOptionsV1):
    from skat_ai.application import ApplicationExternalDocuments

    external_document = options.to_dict()["opponent_statistics_document"]
    if external_document is None:
        return ApplicationExternalDocuments()
    validate_input_document(external_document)
    if not isinstance(external_document, Mapping):
        raise SkatAISchemaError(
            "Opponent Statistics Root document must be an object.",
            path="",
        )
    workflow = _detect_workflow(external_document)
    if workflow is not WorkflowV1.OPPONENT_STATISTICS:
        raise SkatAIWorkflowError(
            "opponent_statistics_document must select the opponent_statistics workflow.",
            path="opponent_statistics_document",
        )
    return ApplicationExternalDocuments(
        opponent_statistics_document=external_document,
        opponent_statistics_reference=options.opponent_statistics_reference,
    )


def _execute_verified_request(
    request: RequestDocumentV1,
    *,
    options: ExecutionOptionsV1 | None,
    input_reference: str,
) -> ExecutionResultV1:
    from skat_ai.application import (
        ApplicationInvocation,
        execute_application_invocation,
    )

    if options is None:
        execution_options = ExecutionOptionsV1()
    elif isinstance(options, ExecutionOptionsV1):
        execution_options = options
    else:
        raise SkatAIValidationError("options must be an ExecutionOptionsV1 or None.")
    if not isinstance(execution_options.workflow_options, Mapping):
        raise SkatAIValidationError("workflow_options must be an object.")
    application_options = _translate_workflow_options(
        request.workflow,
        execution_options.workflow_options,
    )
    external_documents = _validated_external_documents(execution_options)
    invocation = ApplicationInvocation(
        request=request,
        input_reference=input_reference,
        options=application_options,
        external_documents=external_documents,
    )
    application_result = execute_application_invocation(invocation)
    artifacts = tuple(
        ExecutionArtifactV1(name=artifact.name, document=artifact.to_dict())
        for artifact in application_result.artifacts
    )
    public_provenance = None
    result = application_result.result
    if execution_options.include_provenance:
        from skat_ai.public_field_provenance import attach_public_field_provenance

        enriched_document, public_provenance = attach_public_field_provenance(
            application_result
        )
        result = ResultDocumentV1(
            workflow=application_result.result.workflow,
            document=enriched_document,
            warnings=application_result.result.warnings,
        )
    execution_result = ExecutionResultV1(
        result=result,
        artifacts=artifacts,
        field_provenance=public_provenance,
    )
    if execution_options.validate_output:
        serialized = execution_result.to_dict()
        validate_output_document(serialized["document"])
        for artifact in serialized["artifacts"]:
            validate_input_document(artifact["document"])
    return execution_result


def execute(
    request: RequestDocumentV1,
    *,
    options: ExecutionOptionsV1 | None = None,
    input_reference: str = DEFAULT_INPUT_REFERENCE_V1,
) -> ExecutionResultV1:
    """Executes one verified immutable request through the Application layer."""
    return _at_public_boundary(
        lambda: _execute_verified_request(
            _verify_request(request),
            options=options,
            input_reference=input_reference,
        )
    )


def execute_document(
    document: object,
    *,
    options: ExecutionOptionsV1 | None = None,
    input_reference: str = DEFAULT_INPUT_REFERENCE_V1,
) -> ExecutionResultV1:
    """Parses and executes one Root document without duplicate request checks."""
    return _at_public_boundary(
        lambda: _execute_verified_request(
            _parse_request(document),
            options=options,
            input_reference=input_reference,
        )
    )


def serialize_result(result: ExecutionResultV1) -> dict[str, object]:
    """Returns one fresh mutable flattened public execution envelope."""
    if not isinstance(result, ExecutionResultV1):
        raise SkatAISerializationError("result must be an ExecutionResultV1.")
    return result.to_dict()
