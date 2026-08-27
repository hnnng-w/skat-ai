from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import InitVar, dataclass, field
from enum import StrEnum
from inspect import signature
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from skat_ai.errors import SkatAIValidationError

if TYPE_CHECKING:
    from skat_ai.api.v1.provenance import FieldProvenanceBundleV1

PUBLIC_API_CONTRACT_VERSION = 1
PUBLIC_API_NAMESPACE = "skat_ai.api.v1"
PUBLIC_API_COMPATIBILITY_POLICY = "additive_until_v1_0"
LEGACY_MAIN_COMPATIBILITY_TARGET = "v1.0.0"
DEFAULT_INPUT_REFERENCE_V1 = "memory://skat-ai/request"
EXECUTION_ARTIFACT_NAMES_V1 = ("opponent_statistics_input",)

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


def _freeze_json_object(
    document: object,
    *,
    path: str = "document",
) -> Mapping[str, object]:
    if not isinstance(document, Mapping):
        message = (
            "document root must be an object."
            if path == "document"
            else f"{path} must be an object."
        )
        raise SkatAIValidationError(
            message,
            path=path,
        )
    frozen = _freeze_json_value(document, path=path)
    if not isinstance(frozen, Mapping):
        message = (
            "document root must be an object."
            if path == "document"
            else f"{path} must be an object."
        )
        raise SkatAIValidationError(
            message,
            path=path,
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


class _ExecutionOptionsV1Presence:
    __slots__ = ("_supplied_execution_option_names",)


_OPTION_NOT_SUPPLIED = object()
_EXECUTION_OPTIONS_REPLACE_TOKEN = object()


@dataclass(frozen=True, slots=True)
class _ExecutionOptionsV1ReplaceState:
    supplied_names: tuple[str, ...]
    values: tuple[object, ...]
    token: object

    def __post_init__(self) -> None:
        if self.token is not _EXECUTION_OPTIONS_REPLACE_TOKEN:
            raise TypeError("invalid private ExecutionOptionsV1 state")


class _ExecutionOptionsV1ReplaceStateDescriptor:
    def __get__(
        self,
        instance: ExecutionOptionsV1 | None,
        owner: type[ExecutionOptionsV1] | None = None,
    ) -> object:
        if instance is None:
            return self
        return _ExecutionOptionsV1ReplaceState(
            supplied_names=instance._supplied_execution_option_names,
            values=(
                instance.validate_output,
                instance.include_provenance,
                instance.workflow_options,
                instance.opponent_statistics_document,
                instance.opponent_statistics_reference,
            ),
            token=_EXECUTION_OPTIONS_REPLACE_TOKEN,
        )


_EXECUTION_OPTIONS_REPLACE_STATE = _ExecutionOptionsV1ReplaceStateDescriptor()


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class ExecutionOptionsV1(_ExecutionOptionsV1Presence):
    """Public non-transport options for one version-1 execution."""

    validate_output: bool = True
    include_provenance: bool = False
    workflow_options: Mapping[str, object] = field(default_factory=dict)
    opponent_statistics_document: Mapping[str, object] | None = None
    opponent_statistics_reference: str | None = None
    _replace_state: InitVar[object] = _EXECUTION_OPTIONS_REPLACE_STATE

    def __init__(
        self,
        *,
        validate_output: bool = _OPTION_NOT_SUPPLIED,  # type: ignore[assignment]
        include_provenance: bool = _OPTION_NOT_SUPPLIED,  # type: ignore[assignment]
        workflow_options: Mapping[str, object] = _OPTION_NOT_SUPPLIED,  # type: ignore[assignment]
        opponent_statistics_document: Mapping[str, object] | None = _OPTION_NOT_SUPPLIED,  # type: ignore[assignment]
        opponent_statistics_reference: str | None = _OPTION_NOT_SUPPLIED,  # type: ignore[assignment]
        _replace_state: object = _EXECUTION_OPTIONS_REPLACE_STATE,
    ) -> None:
        object.__setattr__(
            self,
            "validate_output",
            True if validate_output is _OPTION_NOT_SUPPLIED else validate_output,
        )
        object.__setattr__(
            self,
            "include_provenance",
            False if include_provenance is _OPTION_NOT_SUPPLIED else include_provenance,
        )
        object.__setattr__(
            self,
            "workflow_options",
            {} if workflow_options is _OPTION_NOT_SUPPLIED else workflow_options,
        )
        object.__setattr__(
            self,
            "opponent_statistics_document",
            (
                None
                if opponent_statistics_document is _OPTION_NOT_SUPPLIED
                else opponent_statistics_document
            ),
        )
        object.__setattr__(
            self,
            "opponent_statistics_reference",
            (
                None
                if opponent_statistics_reference is _OPTION_NOT_SUPPLIED
                else opponent_statistics_reference
            ),
        )
        self.__post_init__()
        if _replace_state is _EXECUTION_OPTIONS_REPLACE_STATE:
            supplied = tuple(
                name
                for name, value in (
                    ("validate_output", validate_output),
                    ("include_provenance", include_provenance),
                    ("workflow_options", workflow_options),
                    ("opponent_statistics_document", opponent_statistics_document),
                    ("opponent_statistics_reference", opponent_statistics_reference),
                )
                if value is not _OPTION_NOT_SUPPLIED
            )
        elif isinstance(_replace_state, _ExecutionOptionsV1ReplaceState):
            supplied_values = set(_replace_state.supplied_names)
            for name, current, previous in zip(
                (
                    "validate_output",
                    "include_provenance",
                    "workflow_options",
                    "opponent_statistics_document",
                    "opponent_statistics_reference",
                ),
                (
                    self.validate_output,
                    self.include_provenance,
                    self.workflow_options,
                    self.opponent_statistics_document,
                    self.opponent_statistics_reference,
                ),
                _replace_state.values,
                strict=True,
            ):
                if current != previous:
                    supplied_values.add(name)
            supplied = tuple(
                name
                for name in (
                    "validate_output",
                    "include_provenance",
                    "workflow_options",
                    "opponent_statistics_document",
                    "opponent_statistics_reference",
                )
                if name in supplied_values
            )
        else:
            raise TypeError("invalid private ExecutionOptionsV1 state")
        object.__setattr__(self, "_supplied_execution_option_names", supplied)

    def __post_init__(self) -> None:
        if not isinstance(self.validate_output, bool):
            raise SkatAIValidationError(
                "validate_output must be a boolean.",
                path="validate_output",
            )
        if not isinstance(self.include_provenance, bool):
            raise SkatAIValidationError(
                "include_provenance must be a boolean.",
                path="include_provenance",
            )
        object.__setattr__(
            self,
            "workflow_options",
            _freeze_json_object(self.workflow_options, path="workflow_options"),
        )
        has_document = self.opponent_statistics_document is not None
        has_reference = self.opponent_statistics_reference is not None
        if has_document != has_reference:
            raise SkatAIValidationError(
                "opponent_statistics_document and opponent_statistics_reference "
                "must be supplied together.",
                path="opponent_statistics_document",
            )
        if has_reference and (
            not isinstance(self.opponent_statistics_reference, str)
            or not self.opponent_statistics_reference
        ):
            raise SkatAIValidationError(
                "opponent_statistics_reference must be a non-empty string.",
                path="opponent_statistics_reference",
            )
        if has_document:
            object.__setattr__(
                self,
                "opponent_statistics_document",
                _freeze_json_object(
                    self.opponent_statistics_document,
                    path="opponent_statistics_document",
                ),
            )

    def to_dict(self) -> dict[str, Any]:
        """Returns a fresh deterministic execution-option representation."""
        return {
            "validate_output": self.validate_output,
            "include_provenance": self.include_provenance,
            "workflow_options": _thaw_json_value(self.workflow_options),
            "opponent_statistics_document": (
                None
                if self.opponent_statistics_document is None
                else _thaw_json_value(self.opponent_statistics_document)
            ),
            "opponent_statistics_reference": self.opponent_statistics_reference,
        }

    @property
    def _provenance_supplied_option_names(self) -> tuple[str, ...]:
        return self._supplied_execution_option_names

    def __copy__(self) -> ExecutionOptionsV1:
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> ExecutionOptionsV1:
        memo[id(self)] = self
        return self

    def __reduce__(self) -> tuple[object, tuple[object, ...]]:
        return (
            _restore_execution_options_v1,
            (
                self.to_dict(),
                self._supplied_execution_option_names,
            ),
        )


def _restore_execution_options_v1(
    values: Mapping[str, object],
    supplied_names: tuple[str, ...],
) -> ExecutionOptionsV1:
    restored = ExecutionOptionsV1(**values)
    object.__setattr__(restored, "_supplied_execution_option_names", supplied_names)
    return restored


@dataclass(frozen=True, slots=True, kw_only=True)
class _ExecutionOptionsV1PublicSignature:
    validate_output: bool = True
    include_provenance: bool = False
    workflow_options: Mapping[str, object] = field(default_factory=dict)
    opponent_statistics_document: Mapping[str, object] | None = None
    opponent_statistics_reference: str | None = None


_execution_options_public_init_signature = signature(
    _ExecutionOptionsV1PublicSignature.__init__
)
ExecutionOptionsV1.__signature__ = (  # type: ignore[attr-defined]
    _execution_options_public_init_signature.replace(
        parameters=tuple(
            _execution_options_public_init_signature.parameters.values()
        )[1:]
    )
)
ExecutionOptionsV1.__init__.__signature__ = (  # type: ignore[attr-defined]
    _execution_options_public_init_signature
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
class ExecutionArtifactV1:
    """One immutable public auxiliary execution artifact."""

    name: str
    document: Mapping[str, object]

    def __post_init__(self) -> None:
        if self.name not in EXECUTION_ARTIFACT_NAMES_V1:
            raise SkatAIValidationError(
                f"name must be one of {EXECUTION_ARTIFACT_NAMES_V1}.",
                path="name",
            )
        object.__setattr__(self, "document", _freeze_json_object(self.document))

    def to_dict(self) -> dict[str, Any]:
        """Returns a fresh deterministic artifact representation."""
        return {
            "name": self.name,
            "document": _thaw_json_value(self.document),
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionResultV1:
    """One immutable public execution result and its auxiliary artifacts."""

    api_contract_version: int = PUBLIC_API_CONTRACT_VERSION
    result: ResultDocumentV1
    artifacts: tuple[ExecutionArtifactV1, ...] = ()
    field_provenance: FieldProvenanceBundleV1 | None = None

    def __post_init__(self) -> None:
        _validate_api_contract_version(self.api_contract_version)
        if not isinstance(self.result, ResultDocumentV1):
            raise SkatAIValidationError(
                "result must be a ResultDocumentV1.",
                path="result",
            )
        if isinstance(self.artifacts, list):
            object.__setattr__(self, "artifacts", tuple(self.artifacts))
        elif not isinstance(self.artifacts, tuple):
            raise SkatAIValidationError(
                "artifacts must be an ordered artifact sequence.",
                path="artifacts",
            )
        if any(not isinstance(artifact, ExecutionArtifactV1) for artifact in self.artifacts):
            raise SkatAIValidationError(
                "artifacts must contain only ExecutionArtifactV1 values.",
                path="artifacts",
            )
        names = tuple(artifact.name for artifact in self.artifacts)
        if len(names) != len(set(names)):
            raise SkatAIValidationError(
                "artifacts must not contain duplicate names.",
                path="artifacts",
            )
        from skat_ai.api.v1.provenance import (
            PUBLIC_FIELD_PROVENANCE_ROOT_FIELD,
            FieldProvenanceBundleV1,
        )

        has_serialized_sidecar = (
            PUBLIC_FIELD_PROVENANCE_ROOT_FIELD in self.result.document
        )
        serialized_sidecar = self.result.document.get(PUBLIC_FIELD_PROVENANCE_ROOT_FIELD)
        if self.field_provenance is None:
            if has_serialized_sidecar:
                raise SkatAIValidationError(
                    "Result document field_provenance requires typed field_provenance.",
                    path="field_provenance",
                )
        elif not isinstance(self.field_provenance, FieldProvenanceBundleV1):
            raise SkatAIValidationError(
                "field_provenance must be a FieldProvenanceBundleV1 or None.",
                path="field_provenance",
            )
        elif self.field_provenance.workflow is not self.result.workflow:
            raise SkatAIValidationError(
                "field_provenance workflow must match the Result workflow.",
                path="field_provenance.workflow",
            )
        elif tuple(artifact.name for artifact in self.artifacts) != tuple(
            artifact.artifact_name for artifact in self.field_provenance.artifacts
        ):
            raise SkatAIValidationError(
                "field_provenance artifacts must match actual execution artifacts.",
                path="field_provenance.artifacts",
            )
        elif serialized_sidecar != _freeze_json_object(
            self.field_provenance.to_dict(),
            path="field_provenance",
        ):
            raise SkatAIValidationError(
                "Typed and serialized field_provenance must be equal.",
                path="field_provenance",
            )

    def to_dict(self) -> dict[str, Any]:
        """Returns a fresh mutable flattened public execution envelope."""
        result = self.result.to_dict()
        return {
            "api_contract_version": self.api_contract_version,
            "workflow": result["workflow"],
            "document": result["document"],
            "warnings": result["warnings"],
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
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
