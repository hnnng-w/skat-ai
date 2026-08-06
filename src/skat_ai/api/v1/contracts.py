import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any

from skat_ai.errors import SkatAIValidationError

PUBLIC_API_CONTRACT_VERSION = 1
PUBLIC_API_NAMESPACE = "skat_ai.api.v1"
PUBLIC_API_COMPATIBILITY_POLICY = "additive_until_v1_0"
LEGACY_MAIN_COMPATIBILITY_TARGET = "v1.0.0"

NORMAL_RESULT_STATES_V1 = (
    "complete",
    "partial",
    "timeout",
    "unavailable",
    "final",
    "lot_required",
    "not_assessable",
)


class WorkflowV1(StrEnum):
    """Stable version-1 Root workflow identifiers."""

    POSITION_ANALYSIS = "position_analysis"
    HISTORICAL_GAME = "historical_game"
    TRAINING_DATASET = "training_dataset"
    TRAINING_DATASET_PREPARATION = "training_dataset_preparation"
    OPPONENT_STATISTICS = "opponent_statistics"
    FIXED_THREE_PLAYER_HISTORICAL_LIST = "fixed_three_player_historical_list"
    FIXED_THREE_PLAYER_HISTORICAL_LIST_COMPARISON = "fixed_three_player_historical_list_comparison"


def _freeze_json_value(value: object, *, path: str) -> object:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise SkatAIValidationError(
                "JSON numbers must be finite.",
                path=path,
            )
        return value
    if isinstance(value, Mapping):
        frozen: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise SkatAIValidationError(
                    "JSON object keys must be strings.",
                    path=path,
                )
            frozen[key] = _freeze_json_value(item, path=f"{path}.{key}")
        return MappingProxyType(frozen)
    if isinstance(value, (list, tuple)):
        return tuple(
            _freeze_json_value(item, path=f"{path}[{index}]") for index, item in enumerate(value)
        )
    raise SkatAIValidationError(
        "document values must be JSON-compatible objects, arrays, or scalar values.",
        path=path,
    )


def _freeze_json_object(document: object) -> Mapping[str, object]:
    if not isinstance(document, Mapping):
        raise SkatAIValidationError(
            "document root must be an object.",
            path="document",
        )
    frozen = _freeze_json_value(document, path="document")
    if not isinstance(frozen, Mapping):
        raise SkatAIValidationError(
            "document root must be an object.",
            path="document",
        )
    return frozen


def _thaw_json_value(value: object) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_json_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json_value(item) for item in value]
    return value


def _validate_api_contract_version(value: object) -> None:
    if type(value) is not int or value != PUBLIC_API_CONTRACT_VERSION:
        raise SkatAIValidationError(
            f"api_contract_version must equal {PUBLIC_API_CONTRACT_VERSION}.",
            path="api_contract_version",
        )


def _validate_workflow(value: object) -> None:
    if not isinstance(value, WorkflowV1):
        raise SkatAIValidationError(
            "workflow must be a WorkflowV1 value.",
            path="workflow",
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class RequestDocumentV1:
    """Immutable version-1 request JSON document."""

    api_contract_version: int = PUBLIC_API_CONTRACT_VERSION
    workflow: WorkflowV1
    document: Mapping[str, object]

    def __post_init__(self) -> None:
        _validate_api_contract_version(self.api_contract_version)
        _validate_workflow(self.workflow)
        object.__setattr__(self, "document", _freeze_json_object(self.document))

    def to_dict(self) -> dict[str, Any]:
        """Returns a fresh mutable JSON-compatible request representation."""
        return {
            "api_contract_version": self.api_contract_version,
            "workflow": self.workflow.value,
            "document": _thaw_json_value(self.document),
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionOptionsV1:
    """Version-1 placeholder for future workflow execution options."""

    validate_output: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.validate_output, bool):
            raise SkatAIValidationError(
                "validate_output must be a boolean.",
                path="validate_output",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ResultDocumentV1:
    """Immutable version-1 result JSON document."""

    api_contract_version: int = PUBLIC_API_CONTRACT_VERSION
    workflow: WorkflowV1
    document: Mapping[str, object]
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _validate_api_contract_version(self.api_contract_version)
        _validate_workflow(self.workflow)
        object.__setattr__(self, "document", _freeze_json_object(self.document))
        if isinstance(self.warnings, str) or not isinstance(self.warnings, (list, tuple)):
            raise SkatAIValidationError(
                "warnings must be an ordered array of non-empty strings.",
                path="warnings",
            )
        warnings = tuple(self.warnings)
        if any(not isinstance(warning, str) or not warning for warning in warnings):
            raise SkatAIValidationError(
                "warnings must contain only non-empty strings.",
                path="warnings",
            )
        object.__setattr__(self, "warnings", warnings)

    def to_dict(self) -> dict[str, Any]:
        """Returns a fresh mutable JSON-compatible result representation."""
        return {
            "api_contract_version": self.api_contract_version,
            "workflow": self.workflow.value,
            "document": _thaw_json_value(self.document),
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class CompatibilityPolicyV1:
    """Machine-readable additive compatibility policy for the version-1 API."""

    policy_id: str = PUBLIC_API_COMPATIBILITY_POLICY
    public_namespace: str = PUBLIC_API_NAMESPACE
    public_name_removal_before_v1_allowed: bool = False
    public_name_renaming_before_v1_allowed: bool = False
    additive_public_exports_allowed: bool = True
    direct_internal_imports_stable: bool = False
    legacy_main_supported_through: str = LEGACY_MAIN_COMPATIBILITY_TARGET
    package_version_independent: bool = True
    schema_versions_independent: bool = True
    deprecation_warning_name: str = "SkatAIDeprecationWarning"

    def __post_init__(self) -> None:
        expected = self.to_dict()
        required = {
            "policy_id": PUBLIC_API_COMPATIBILITY_POLICY,
            "public_namespace": PUBLIC_API_NAMESPACE,
            "public_name_removal_before_v1_allowed": False,
            "public_name_renaming_before_v1_allowed": False,
            "additive_public_exports_allowed": True,
            "direct_internal_imports_stable": False,
            "legacy_main_supported_through": LEGACY_MAIN_COMPATIBILITY_TARGET,
            "package_version_independent": True,
            "schema_versions_independent": True,
            "deprecation_warning_name": "SkatAIDeprecationWarning",
        }
        for name, required_value in required.items():
            value = expected[name]
            if type(value) is not type(required_value) or value != required_value:
                raise SkatAIValidationError(
                    f"{name} must equal {required_value!r}.",
                    path=name,
                )

    def to_dict(self) -> dict[str, str | bool]:
        """Returns the deterministic compatibility-policy representation."""
        return {
            "policy_id": self.policy_id,
            "public_namespace": self.public_namespace,
            "public_name_removal_before_v1_allowed": (self.public_name_removal_before_v1_allowed),
            "public_name_renaming_before_v1_allowed": (self.public_name_renaming_before_v1_allowed),
            "additive_public_exports_allowed": self.additive_public_exports_allowed,
            "direct_internal_imports_stable": self.direct_internal_imports_stable,
            "legacy_main_supported_through": self.legacy_main_supported_through,
            "package_version_independent": self.package_version_independent,
            "schema_versions_independent": self.schema_versions_independent,
            "deprecation_warning_name": self.deprecation_warning_name,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class ApiVersionInfoV1:
    """Immutable metadata describing the complete version-1 public contract."""

    api_contract_version: int = PUBLIC_API_CONTRACT_VERSION
    namespace: str = PUBLIC_API_NAMESPACE
    supported_workflows: tuple[WorkflowV1, ...] = tuple(WorkflowV1)
    normal_result_states: tuple[str, ...] = NORMAL_RESULT_STATES_V1
    compatibility_policy: CompatibilityPolicyV1 = field(default_factory=CompatibilityPolicyV1)

    def __post_init__(self) -> None:
        _validate_api_contract_version(self.api_contract_version)
        if self.namespace != PUBLIC_API_NAMESPACE:
            raise SkatAIValidationError(
                f"namespace must equal {PUBLIC_API_NAMESPACE!r}.",
                path="namespace",
            )
        if self.supported_workflows != tuple(WorkflowV1):
            raise SkatAIValidationError(
                "supported_workflows must contain the canonical WorkflowV1 values.",
                path="supported_workflows",
            )
        if self.normal_result_states != NORMAL_RESULT_STATES_V1:
            raise SkatAIValidationError(
                "normal_result_states must contain the canonical version-1 states.",
                path="normal_result_states",
            )
        if self.compatibility_policy != CompatibilityPolicyV1():
            raise SkatAIValidationError(
                "compatibility_policy must equal CompatibilityPolicyV1().",
                path="compatibility_policy",
            )

    def to_dict(self) -> dict[str, Any]:
        """Returns the deterministic API-version information representation."""
        return {
            "api_contract_version": self.api_contract_version,
            "namespace": self.namespace,
            "supported_workflows": [workflow.value for workflow in self.supported_workflows],
            "normal_result_states": list(self.normal_result_states),
            "compatibility_policy": self.compatibility_policy.to_dict(),
        }


def get_api_version_info_v1() -> ApiVersionInfoV1:
    """Returns immutable version-1 API metadata without external resource access."""
    return ApiVersionInfoV1()
