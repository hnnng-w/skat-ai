from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from skat_ai.api.v1.contracts import RequestDocumentV1, ResultDocumentV1
from skat_ai.bounded_search_evaluation import DEFAULT_BOUNDED_SEARCH_EVALUATION_PARTITIONS
from skat_ai.errors import SkatAIValidationError
from skat_ai.rolling_opponent_policy_evaluation import (
    DEFAULT_EVALUATION_PARTITIONS,
    DEFAULT_SOURCE_PARTITIONS,
)
from skat_ai.search_budget_profiles import (
    EVALUATION_SEARCH_BUDGET_PROFILE,
    HISTORICAL_REVIEW_SEARCH_BUDGET_PROFILE,
)
from skat_ai.simulation import DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT

if TYPE_CHECKING:
    from skat_ai.application.provenance import ApplicationProvenanceBundle

APPLICATION_ORCHESTRATION_VERSION = 1
APPLICATION_INPUT_REFERENCE_POLICY = "caller_supplied"

TRAINING_DATASET_APPLICATION_OPERATIONS = (
    "summary",
    "partition_audit",
    "rolling_opponent_policy_evaluation",
    "bounded_search_evaluation",
    "historical_opponent_statistics_aggregation",
)
APPLICATION_ARTIFACT_NAMES = ("opponent_statistics_input",)


def _validation_error(message: str, path: str) -> SkatAIValidationError:
    return SkatAIValidationError(message, path=path)


def _freeze_json_value(value: object, *, path: str) -> object:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise _validation_error("JSON numbers must be finite.", path)
        return value
    if isinstance(value, Mapping):
        frozen: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise _validation_error("JSON object keys must be strings.", path)
            frozen[key] = _freeze_json_value(item, path=f"{path}.{key}")
        return MappingProxyType(frozen)
    if isinstance(value, (list, tuple)):
        return tuple(
            _freeze_json_value(item, path=f"{path}[{index}]")
            for index, item in enumerate(value)
        )
    raise _validation_error(
        "value must contain only JSON-compatible objects, arrays, and scalar values.",
        path,
    )


def _freeze_json_object(value: object, *, path: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise _validation_error("must be an object.", path)
    frozen = _freeze_json_value(value, path=path)
    if not isinstance(frozen, Mapping):
        raise _validation_error("must be an object.", path)
    return frozen


def _thaw_json_value(value: object) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_json_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json_value(item) for item in value]
    return value


def _validate_optional_int(value: object, *, path: str) -> None:
    if value is not None and type(value) is not int:
        raise _validation_error("must be an integer or None.", path)


def _validate_optional_string(value: object, *, path: str) -> None:
    if value is not None and not isinstance(value, str):
        raise _validation_error("must be a string or None.", path)


def _validate_boolean(value: object, *, path: str) -> None:
    if not isinstance(value, bool):
        raise _validation_error("must be a boolean.", path)


def _freeze_string_sequence(
    value: object,
    *,
    path: str,
    allow_none: bool = False,
) -> tuple[str, ...] | None:
    if value is None and allow_none:
        return None
    if isinstance(value, str) or not isinstance(value, (list, tuple)):
        suffix = " or None" if allow_none else ""
        raise _validation_error(f"must be an ordered string sequence{suffix}.", path)
    items = tuple(value)
    if any(not isinstance(item, str) or not item for item in items):
        raise _validation_error("must contain only non-empty strings.", path)
    return items


@dataclass(frozen=True, slots=True, kw_only=True)
class PositionAnalysisApplicationOptions:
    """Non-transport options for one Position Analysis invocation."""

    sample_count_override: int | None = None
    random_seed_override: int | None = None
    opponent_strategy_override: str | None = None
    opponent_policy_preset_override: str | None = None
    opponent_lead_policy_override: str | None = None
    opponent_response_policy_override: str | None = None
    use_profile_presets_override: bool = False
    left_opponent_lead_policy_override: str | None = None
    left_opponent_response_policy_override: str | None = None
    right_opponent_lead_policy_override: str | None = None
    right_opponent_response_policy_override: str | None = None
    multi_step_count: int | None = None
    card_selection_policy: str | None = None
    expected_value_sample_count: int = DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT
    strict_context: bool = False
    compare_policies: bool = False
    comparison_only: bool = False
    left_opponent_player_id: str | None = None
    right_opponent_player_id: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "sample_count_override",
            "random_seed_override",
            "multi_step_count",
            "expected_value_sample_count",
        ):
            value = getattr(self, name)
            if name == "expected_value_sample_count":
                if type(value) is not int:
                    raise _validation_error("must be an integer.", name)
            else:
                _validate_optional_int(value, path=name)
        for name in (
            "opponent_strategy_override",
            "opponent_policy_preset_override",
            "opponent_lead_policy_override",
            "opponent_response_policy_override",
            "left_opponent_lead_policy_override",
            "left_opponent_response_policy_override",
            "right_opponent_lead_policy_override",
            "right_opponent_response_policy_override",
            "card_selection_policy",
            "left_opponent_player_id",
            "right_opponent_player_id",
        ):
            _validate_optional_string(getattr(self, name), path=name)
        for name in (
            "use_profile_presets_override",
            "strict_context",
            "compare_policies",
            "comparison_only",
        ):
            _validate_boolean(getattr(self, name), path=name)


@dataclass(frozen=True, slots=True, kw_only=True)
class HistoricalGameApplicationOptions:
    """Non-transport options for one Historical Game invocation."""

    decision_snapshots: bool = False
    immediate_review: bool = False
    search_review: bool = False
    replay_coaching: bool = False
    search_seed: int | None = None
    search_budget_profile: str = HISTORICAL_REVIEW_SEARCH_BUDGET_PROFILE
    immediate_sample_count: int | None = None
    immediate_base_random_seed: int | None = None
    opponent_policy_preset_override: str | None = None
    opponent_lead_policy_override: str | None = None
    opponent_response_policy_override: str | None = None
    left_opponent_lead_policy_override: str | None = None
    left_opponent_response_policy_override: str | None = None
    right_opponent_lead_policy_override: str | None = None
    right_opponent_response_policy_override: str | None = None
    use_profile_presets_override: bool = False

    def __post_init__(self) -> None:
        for name in (
            "decision_snapshots",
            "immediate_review",
            "search_review",
            "replay_coaching",
            "use_profile_presets_override",
        ):
            _validate_boolean(getattr(self, name), path=name)
        for name in (
            "search_seed",
            "immediate_sample_count",
            "immediate_base_random_seed",
        ):
            _validate_optional_int(getattr(self, name), path=name)
        if not isinstance(self.search_budget_profile, str) or not self.search_budget_profile:
            raise _validation_error("must be a non-empty string.", "search_budget_profile")
        for name in (
            "opponent_policy_preset_override",
            "opponent_lead_policy_override",
            "opponent_response_policy_override",
            "left_opponent_lead_policy_override",
            "left_opponent_response_policy_override",
            "right_opponent_lead_policy_override",
            "right_opponent_response_policy_override",
        ):
            _validate_optional_string(getattr(self, name), path=name)


@dataclass(frozen=True, slots=True, kw_only=True)
class TrainingDatasetApplicationOptions:
    """Exactly one selected Training Dataset operation and its settings."""

    operation: str = "summary"
    partition_audit_mode: str | None = None
    rolling_source_partitions: tuple[str, ...] = DEFAULT_SOURCE_PARTITIONS
    rolling_evaluation_partitions: tuple[str, ...] = DEFAULT_EVALUATION_PARTITIONS
    bounded_search_seed: int | None = None
    bounded_search_partitions: tuple[str, ...] = DEFAULT_BOUNDED_SEARCH_EVALUATION_PARTITIONS
    bounded_search_budget_profile: str = EVALUATION_SEARCH_BUDGET_PROFILE
    bounded_search_max_decisions: int | None = None
    aggregation_included_partitions: tuple[str, ...] | None = None
    aggregation_before: str | None = None
    export_opponent_statistics: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.operation, str):
            raise _validation_error("must be a string.", "operation")
        _validate_optional_string(self.partition_audit_mode, path="partition_audit_mode")
        _validate_optional_int(self.bounded_search_seed, path="bounded_search_seed")
        _validate_optional_int(
            self.bounded_search_max_decisions,
            path="bounded_search_max_decisions",
        )
        _validate_optional_string(self.aggregation_before, path="aggregation_before")
        _validate_boolean(
            self.export_opponent_statistics,
            path="export_opponent_statistics",
        )
        if (
            not isinstance(self.bounded_search_budget_profile, str)
            or not self.bounded_search_budget_profile
        ):
            raise _validation_error(
                "must be a non-empty string.",
                "bounded_search_budget_profile",
            )
        for name in (
            "rolling_source_partitions",
            "rolling_evaluation_partitions",
            "bounded_search_partitions",
        ):
            object.__setattr__(
                self,
                name,
                _freeze_string_sequence(getattr(self, name), path=name),
            )
        object.__setattr__(
            self,
            "aggregation_included_partitions",
            _freeze_string_sequence(
                self.aggregation_included_partitions,
                path="aggregation_included_partitions",
                allow_none=True,
            ),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ApplicationExecutionOptions:
    """Workflow-specific non-transport options for one invocation."""

    position_analysis: PositionAnalysisApplicationOptions | None = None
    historical_game: HistoricalGameApplicationOptions | None = None
    training_dataset: TrainingDatasetApplicationOptions | None = None

    def __post_init__(self) -> None:
        expected_types = {
            "position_analysis": PositionAnalysisApplicationOptions,
            "historical_game": HistoricalGameApplicationOptions,
            "training_dataset": TrainingDatasetApplicationOptions,
        }
        for name, expected_type in expected_types.items():
            value = getattr(self, name)
            if value is not None and not isinstance(value, expected_type):
                raise _validation_error(
                    f"must be a {expected_type.__name__} or None.",
                    name,
                )


@dataclass(frozen=True, slots=True, kw_only=True)
class ApplicationExternalDocuments:
    """Optional injected documents that Application execution may consume."""

    opponent_statistics_document: Mapping[str, object] | None = None
    opponent_statistics_reference: str | None = None

    def __post_init__(self) -> None:
        has_document = self.opponent_statistics_document is not None
        has_reference = self.opponent_statistics_reference is not None
        if has_document != has_reference:
            raise _validation_error(
                "opponent_statistics_document and opponent_statistics_reference "
                "must be supplied together.",
                "external_documents",
            )
        if has_reference and (
            not isinstance(self.opponent_statistics_reference, str)
            or not self.opponent_statistics_reference
        ):
            raise _validation_error(
                "must be a non-empty string.",
                "opponent_statistics_reference",
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

    def opponent_statistics_to_dict(self) -> dict[str, Any] | None:
        """Returns a fresh mutable copy of the injected Root document."""
        if self.opponent_statistics_document is None:
            return None
        return _thaw_json_value(self.opponent_statistics_document)


@dataclass(frozen=True, slots=True, kw_only=True)
class ApplicationInvocation:
    """One immutable in-memory Application execution request."""

    orchestration_version: int = APPLICATION_ORCHESTRATION_VERSION
    request: RequestDocumentV1
    input_reference: str
    options: ApplicationExecutionOptions
    external_documents: ApplicationExternalDocuments = field(
        default_factory=ApplicationExternalDocuments
    )

    def __post_init__(self) -> None:
        if (
            type(self.orchestration_version) is not int
            or self.orchestration_version != APPLICATION_ORCHESTRATION_VERSION
        ):
            raise _validation_error(
                f"must equal {APPLICATION_ORCHESTRATION_VERSION}.",
                "orchestration_version",
            )
        if not isinstance(self.request, RequestDocumentV1):
            raise _validation_error("must be a RequestDocumentV1.", "request")
        if not isinstance(self.input_reference, str) or not self.input_reference:
            raise _validation_error("must be a non-empty string.", "input_reference")
        if not isinstance(self.options, ApplicationExecutionOptions):
            raise _validation_error(
                "must be an ApplicationExecutionOptions.",
                "options",
            )
        if not isinstance(self.external_documents, ApplicationExternalDocuments):
            raise _validation_error(
                "must be an ApplicationExternalDocuments.",
                "external_documents",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ApplicationArtifact:
    """One immutable out-of-band JSON artifact without a transport path."""

    name: str
    document: Mapping[str, object]

    def __post_init__(self) -> None:
        if self.name not in APPLICATION_ARTIFACT_NAMES:
            raise _validation_error(
                f"must be one of {APPLICATION_ARTIFACT_NAMES}.",
                "name",
            )
        object.__setattr__(
            self,
            "document",
            _freeze_json_object(self.document, path="document"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Returns a fresh mutable artifact document."""
        return _thaw_json_value(self.document)


@dataclass(frozen=True, slots=True, kw_only=True)
class ApplicationExecutionResult:
    """One immutable Application result and its auxiliary artifacts."""

    orchestration_version: int = APPLICATION_ORCHESTRATION_VERSION
    result: ResultDocumentV1
    artifacts: tuple[ApplicationArtifact, ...] = ()
    provenance: ApplicationProvenanceBundle | None = None

    def __post_init__(self) -> None:
        if (
            type(self.orchestration_version) is not int
            or self.orchestration_version != APPLICATION_ORCHESTRATION_VERSION
        ):
            raise _validation_error(
                f"must equal {APPLICATION_ORCHESTRATION_VERSION}.",
                "orchestration_version",
            )
        if not isinstance(self.result, ResultDocumentV1):
            raise _validation_error("must be a ResultDocumentV1.", "result")
        if isinstance(self.artifacts, list):
            object.__setattr__(self, "artifacts", tuple(self.artifacts))
        elif not isinstance(self.artifacts, tuple):
            raise _validation_error("must be an ordered artifact sequence.", "artifacts")
        if any(not isinstance(artifact, ApplicationArtifact) for artifact in self.artifacts):
            raise _validation_error(
                "must contain only ApplicationArtifact values.",
                "artifacts",
            )
        names = tuple(artifact.name for artifact in self.artifacts)
        if len(names) != len(set(names)):
            raise _validation_error("must not contain duplicate artifact names.", "artifacts")
        if self.provenance is not None:
            from skat_ai.application.provenance import ApplicationProvenanceBundle

            if not isinstance(self.provenance, ApplicationProvenanceBundle):
                raise _validation_error(
                    "must be an ApplicationProvenanceBundle or None.",
                    "provenance",
                )
            if self.provenance.workflow is not self.result.workflow:
                raise _validation_error(
                    "workflow must match the Application Result workflow.",
                    "provenance",
                )
