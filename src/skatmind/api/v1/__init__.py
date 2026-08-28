from skatmind.api.v1.contracts import (
    DEFAULT_INPUT_REFERENCE_V1,
    EXECUTION_ARTIFACT_NAMES_V1,
    LEGACY_MAIN_COMPATIBILITY_TARGET,
    NORMAL_RESULT_STATES_V1,
    PUBLIC_API_COMPATIBILITY_POLICY,
    PUBLIC_API_CONTRACT_VERSION,
    PUBLIC_API_NAMESPACE,
    ApiVersionInfoV1,
    CompatibilityPolicyV1,
    ExecutionArtifactV1,
    ExecutionOptionsV1,
    ExecutionResultV1,
    RequestDocumentV1,
    ResultDocumentV1,
    WorkflowV1,
    get_api_version_info_v1,
)
from skatmind.api.v1.execution import (
    execute,
    execute_document,
    parse_request,
    serialize_result,
)
from skatmind.api.v1.provenance import (
    PUBLIC_FIELD_PROVENANCE_DOCUMENT_SCOPES,
    PUBLIC_FIELD_PROVENANCE_ROOT_FIELD,
    PUBLIC_FIELD_PROVENANCE_VERSION,
    FieldProvenanceArtifactV1,
    FieldProvenanceAttachmentV1,
    FieldProvenanceBundleV1,
)
from skatmind.errors import (
    CLI_EXIT_CODE_FAILURE,
    CLI_EXIT_CODE_SUCCESS,
    CLI_EXIT_CODE_USAGE,
    SkatMindCliUsageError,
    SkatMindDeprecationWarning,
    SkatMindError,
    SkatMindInformationPolicyError,
    SkatMindInvariantError,
    SkatMindResourceError,
    SkatMindSchemaError,
    SkatMindSerializationError,
    SkatMindValidationError,
    SkatMindWorkflowError,
)


def __getattr__(name: str):
    if name == "session":
        from importlib import import_module

        return import_module("skatmind.api.v1.session")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = (
    "PUBLIC_API_CONTRACT_VERSION",
    "PUBLIC_API_NAMESPACE",
    "PUBLIC_API_COMPATIBILITY_POLICY",
    "LEGACY_MAIN_COMPATIBILITY_TARGET",
    "NORMAL_RESULT_STATES_V1",
    "DEFAULT_INPUT_REFERENCE_V1",
    "EXECUTION_ARTIFACT_NAMES_V1",
    "WorkflowV1",
    "RequestDocumentV1",
    "ExecutionOptionsV1",
    "ResultDocumentV1",
    "ExecutionArtifactV1",
    "ExecutionResultV1",
    "CompatibilityPolicyV1",
    "ApiVersionInfoV1",
    "get_api_version_info_v1",
    "parse_request",
    "execute",
    "execute_document",
    "serialize_result",
    "PUBLIC_FIELD_PROVENANCE_VERSION",
    "PUBLIC_FIELD_PROVENANCE_ROOT_FIELD",
    "PUBLIC_FIELD_PROVENANCE_DOCUMENT_SCOPES",
    "FieldProvenanceAttachmentV1",
    "FieldProvenanceArtifactV1",
    "FieldProvenanceBundleV1",
    "CLI_EXIT_CODE_SUCCESS",
    "CLI_EXIT_CODE_FAILURE",
    "CLI_EXIT_CODE_USAGE",
    "SkatMindError",
    "SkatMindValidationError",
    "SkatMindWorkflowError",
    "SkatMindInformationPolicyError",
    "SkatMindSchemaError",
    "SkatMindSerializationError",
    "SkatMindResourceError",
    "SkatMindInvariantError",
    "SkatMindCliUsageError",
    "SkatMindDeprecationWarning",
    "session",
)
