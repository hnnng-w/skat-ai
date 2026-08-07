from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from skat_ai.api.v1.contracts import (
    WorkflowV1,
    _freeze_json_object,
    _thaw_json_value,
)
from skat_ai.errors import SkatAIValidationError

PUBLIC_FIELD_PROVENANCE_VERSION = 1
PUBLIC_FIELD_PROVENANCE_ROOT_FIELD = "field_provenance"
PUBLIC_FIELD_PROVENANCE_DOCUMENT_SCOPES = (
    "root_result_without_field_provenance",
    "artifact_document",
)
_PUBLIC_REDACTION_POLICY = "omit_engine_private_details"

_RESULT_ATTACHMENT_NAMES = MappingProxyType({
    WorkflowV1.POSITION_ANALYSIS: "position_result",
    WorkflowV1.HISTORICAL_GAME: "historical_game_result",
    WorkflowV1.TRAINING_DATASET: "training_dataset_result",
    WorkflowV1.TRAINING_DATASET_PREPARATION: "dataset_preparation_result",
    WorkflowV1.OPPONENT_STATISTICS: "opponent_statistics_result",
    WorkflowV1.FIXED_THREE_PLAYER_HISTORICAL_LIST: "historical_list_result",
    WorkflowV1.FIXED_THREE_PLAYER_HISTORICAL_LIST_COMPARISON: (
        "historical_list_comparison_result"
    ),
})
_ARTIFACT_ATTACHMENT_NAMES = MappingProxyType({
    "opponent_statistics_input": "training_dataset/opponent_statistics_input",
})
_LEDGER_FIELDS = {
    "provenance_version",
    "status",
    "entries",
    "exemptions",
    "limitations",
}
_COVERAGE_FIELDS = {
    "leaf_path_count",
    "provenanced_path_count",
    "exempted_path_count",
    "uncovered_paths",
    "orphaned_entry_paths",
    "orphaned_exemption_paths",
    "overlapping_paths",
    "all_paths_accounted_for",
    "provenance_complete",
}
_CONTEXT_FIELDS = {
    "workflow",
    "stage",
    "perspective_player_id",
    "perspective_side",
    "decision_index",
    "event_index",
}
_ENTRY_FIELDS = {
    "field_path",
    "coverage_kind",
    "origin",
    "visibility",
    "available_from",
    "available_from_decision_index",
    "available_from_event_index",
    "derivation",
    "source_references",
    "dependency_paths",
    "subject_player_id",
    "perspective_player_id",
}
_REFERENCE_FIELDS = {
    "reference_type",
    "reference_id",
    "field_path",
    "visibility",
}
_EXEMPTION_FIELDS = {"field_path", "coverage_kind", "reason"}
_COVERAGE_KINDS = {"field", "subtree"}
_ORIGINS = {
    "caller_supplied",
    "defaulted",
    "validated_copy",
    "public_game_event",
    "historical_replay",
    "external_source",
    "rule_derived",
    "structural_inference",
    "compatible_world_aggregate",
    "sampled_estimate",
    "heuristic_analysis",
    "simulation_derived",
    "search_derived",
    "retrospective_attachment",
    "historical_aggregation",
    "dataset_assignment",
}
_VISIBILITIES = {
    "public",
    "local_private",
    "declarer_private",
    "defender_private",
    "post_game_only",
}
_AVAILABILITY_BOUNDARIES = {
    "request_start",
    "current_decision",
    "after_public_event",
    "after_actual_play",
    "game_end",
    "offline_review",
}
_DERIVATIONS = {
    "direct",
    "validated",
    "deterministic_rule",
    "reconstruction",
    "exact_aggregate",
    "sampled_aggregate",
    "heuristic",
    "retrospective",
}
_REFERENCE_TYPES = {
    "request",
    "historical_game",
    "historical_event",
    "external_record",
    "rule_contract",
    "algorithm",
    "aggregate",
    "retrospective_observation",
    "dataset_plan",
}
_CONTEXT_STAGES = {
    "request_start",
    "decision_time",
    "after_actual_play",
    "game_end",
    "offline_review",
    "engine_internal",
}


def _validation_error(message: str, *, path: str) -> SkatAIValidationError:
    return SkatAIValidationError(message, path=path)


def _validate_identifier(value: object, *, path: str) -> None:
    if not isinstance(value, str) or not value or value != value.strip():
        raise _validation_error(
            f"{path} must be a non-empty, non-padded string.",
            path=path,
        )


def _require_exact_fields(
    value: Mapping[str, object],
    expected: set[str],
    *,
    path: str,
) -> None:
    if set(value) != expected:
        raise _validation_error(
            f"{path} must contain exactly {sorted(expected)}.",
            path=path,
        )


def _validate_json_pointer(value: object, *, path: str) -> None:
    if not isinstance(value, str) or (value and not value.startswith("/")):
        raise _validation_error(f"{path} must be an RFC 6901 JSON Pointer.", path=path)
    index = 0
    while index < len(value):
        if value[index] != "~":
            index += 1
            continue
        if index + 1 >= len(value) or value[index + 1] not in {"0", "1"}:
            raise _validation_error(
                f"{path} contains an invalid JSON Pointer escape.",
                path=path,
            )
        index += 2


def _validate_optional_identifier(value: object, *, path: str) -> None:
    if value is not None and (
        not isinstance(value, str) or not value or value != value.strip()
    ):
        raise _validation_error(
            f"{path} must be a non-empty, non-padded string or null.",
            path=path,
        )


def _validate_optional_index(value: object, *, path: str) -> None:
    if value is not None and (
        type(value) is not int or value < 0
    ):
        raise _validation_error(
            f"{path} must be a non-negative integer or null.",
            path=path,
        )


def _validate_public_ledger(ledger: Mapping[str, object]) -> None:
    _require_exact_fields(ledger, _LEDGER_FIELDS, path="ledger")
    if ledger["provenance_version"] != 1 or type(ledger["provenance_version"]) is not int:
        raise _validation_error("ledger provenance_version must equal 1.", path="ledger")
    if ledger["status"] != "complete":
        raise _validation_error("Public ledger status must be complete.", path="ledger.status")
    entries = ledger["entries"]
    exemptions = ledger["exemptions"]
    limitations = ledger["limitations"]
    if not isinstance(entries, tuple) or not isinstance(exemptions, tuple):
        raise _validation_error(
            "Public ledger entries and exemptions must be arrays.",
            path="ledger",
        )
    if not isinstance(limitations, tuple) or any(
        item != "private_dependencies_redacted" for item in limitations
    ):
        raise _validation_error(
            "Public ledger limitations may contain only private_dependencies_redacted.",
            path="ledger.limitations",
        )
    if len(limitations) != len(set(limitations)):
        raise _validation_error(
            "Public ledger limitations must be unique.",
            path="ledger.limitations",
        )
    entry_paths: set[object] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, Mapping):
            raise _validation_error("Public ledger entries must be objects.", path="ledger.entries")
        entry_path = f"ledger.entries.{index}"
        _require_exact_fields(entry, _ENTRY_FIELDS, path=entry_path)
        _validate_json_pointer(entry["field_path"], path=f"{entry_path}.field_path")
        if entry["coverage_kind"] not in _COVERAGE_KINDS:
            raise _validation_error("Invalid public coverage_kind.", path=entry_path)
        if entry["origin"] not in _ORIGINS:
            raise _validation_error("Invalid public origin.", path=entry_path)
        if entry["visibility"] not in _VISIBILITIES:
            raise _validation_error(
                "Invalid or engine-private public visibility.",
                path=f"{entry_path}.visibility",
            )
        if entry["available_from"] not in _AVAILABILITY_BOUNDARIES:
            raise _validation_error("Invalid public availability boundary.", path=entry_path)
        if entry["derivation"] not in _DERIVATIONS:
            raise _validation_error("Invalid public derivation.", path=entry_path)
        _validate_optional_index(
            entry["available_from_decision_index"],
            path=f"{entry_path}.available_from_decision_index",
        )
        _validate_optional_index(
            entry["available_from_event_index"],
            path=f"{entry_path}.available_from_event_index",
        )
        _validate_optional_identifier(
            entry["subject_player_id"],
            path=f"{entry_path}.subject_player_id",
        )
        _validate_optional_identifier(
            entry["perspective_player_id"],
            path=f"{entry_path}.perspective_player_id",
        )
        if (
            entry["visibility"] == "local_private"
            and entry["perspective_player_id"] is None
        ):
            raise _validation_error(
                "local_private visibility requires perspective_player_id.",
                path=f"{entry_path}.perspective_player_id",
            )
        entry_paths.add(entry["field_path"])
        references = entry["source_references"]
        dependencies = entry["dependency_paths"]
        if not isinstance(references, tuple) or not isinstance(dependencies, tuple):
            raise _validation_error(
                "Public entry references and dependencies must be arrays.",
                path=f"ledger.entries.{index}",
            )
        for reference_index, reference in enumerate(references):
            reference_path = f"{entry_path}.source_references.{reference_index}"
            if not isinstance(reference, Mapping):
                raise _validation_error(
                    "Public ledger references must be objects.",
                    path=reference_path,
                )
            _require_exact_fields(reference, _REFERENCE_FIELDS, path=reference_path)
            if reference["reference_type"] not in _REFERENCE_TYPES:
                raise _validation_error("Invalid public reference_type.", path=reference_path)
            _validate_identifier(
                reference["reference_id"],
                path=f"{reference_path}.reference_id",
            )
            if reference["field_path"] is not None:
                _validate_json_pointer(
                    reference["field_path"],
                    path=f"{reference_path}.field_path",
                )
            if reference["visibility"] not in _VISIBILITIES:
                raise _validation_error(
                    "Invalid or engine-private reference visibility.",
                    path=f"{reference_path}.visibility",
                )
        for dependency_index, dependency in enumerate(dependencies):
            _validate_json_pointer(
                dependency,
                path=f"{entry_path}.dependency_paths.{dependency_index}",
            )
    if len(entry_paths) != len(entries):
        raise _validation_error(
            "Public ledger entry paths must be unique.",
            path="ledger.entries",
        )
    if any(
        dependency not in entry_paths
        for entry in entries
        for dependency in entry["dependency_paths"]
    ):
        raise _validation_error(
            "Every public dependency must identify a retained entry.",
            path="ledger.entries",
        )
    exemption_paths = set()
    for index, exemption in enumerate(exemptions):
        exemption_path = f"ledger.exemptions.{index}"
        if not isinstance(exemption, Mapping):
            raise _validation_error(
                "Public ledger exemptions must be objects.",
                path=exemption_path,
            )
        _require_exact_fields(exemption, _EXEMPTION_FIELDS, path=exemption_path)
        _validate_json_pointer(
            exemption["field_path"],
            path=f"{exemption_path}.field_path",
        )
        if exemption["coverage_kind"] not in _COVERAGE_KINDS:
            raise _validation_error("Invalid public coverage_kind.", path=exemption_path)
        if exemption["reason"] not in {"schema_constant", "not_applicable"}:
            raise _validation_error(
                "Public ledger exemptions cannot contain legacy reasons.",
                path=f"{exemption_path}.reason",
            )
        exemption_paths.add(exemption["field_path"])
    if len(exemption_paths) != len(exemptions):
        raise _validation_error(
            "Public ledger exemption paths must be unique.",
            path="ledger.exemptions",
        )


def _validate_complete_coverage(summary: Mapping[str, object]) -> None:
    _require_exact_fields(summary, _COVERAGE_FIELDS, path="coverage_summary")
    for name in (
        "leaf_path_count",
        "provenanced_path_count",
        "exempted_path_count",
    ):
        if type(summary[name]) is not int or summary[name] < 0:
            raise _validation_error(
                f"coverage_summary {name} must be a non-negative integer.",
                path=f"coverage_summary.{name}",
            )
    for name in (
        "uncovered_paths",
        "orphaned_entry_paths",
        "orphaned_exemption_paths",
        "overlapping_paths",
    ):
        if summary[name] != ():
            raise _validation_error(
                f"Public coverage_summary {name} must be empty.",
                path=f"coverage_summary.{name}",
            )
    if summary["all_paths_accounted_for"] is not True:
        raise _validation_error(
            "Public coverage must account for every path.",
            path="coverage_summary.all_paths_accounted_for",
        )
    if summary["provenance_complete"] is not True:
        raise _validation_error(
            "Public coverage must be complete.",
            path="coverage_summary.provenance_complete",
        )
    if (
        summary["provenanced_path_count"] + summary["exempted_path_count"]
        != summary["leaf_path_count"]
    ):
        raise _validation_error(
            "Public coverage counts must reconcile with leaf_path_count.",
            path="coverage_summary.leaf_path_count",
        )


def _validate_information_use_context(context: Mapping[str, object]) -> None:
    _require_exact_fields(context, _CONTEXT_FIELDS, path="information_use_context")
    if context["workflow"] not in {workflow.value for workflow in WorkflowV1}:
        raise _validation_error(
            "Invalid information-use workflow.",
            path="information_use_context.workflow",
        )
    if context["stage"] not in _CONTEXT_STAGES:
        raise _validation_error(
            "Invalid information-use stage.",
            path="information_use_context.stage",
        )
    _validate_optional_identifier(
        context["perspective_player_id"],
        path="information_use_context.perspective_player_id",
    )
    if context["perspective_side"] not in {None, "declarer", "defenders"}:
        raise _validation_error(
            "Invalid information-use perspective_side.",
            path="information_use_context.perspective_side",
        )
    _validate_optional_index(
        context["decision_index"],
        path="information_use_context.decision_index",
    )
    _validate_optional_index(
        context["event_index"],
        path="information_use_context.event_index",
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class FieldProvenanceAttachmentV1:
    """One immutable public-safe field-provenance attachment."""

    attachment_name: str
    document_role: str
    document_scope: str
    ledger: Mapping[str, object]
    coverage_summary: Mapping[str, object]
    information_use_context: Mapping[str, object]

    def __post_init__(self) -> None:
        _validate_identifier(self.attachment_name, path="attachment_name")
        if self.document_role != "result":
            raise _validation_error(
                "document_role must be result.",
                path="document_role",
            )
        if self.document_scope not in PUBLIC_FIELD_PROVENANCE_DOCUMENT_SCOPES:
            raise _validation_error(
                "document_scope is not a public field-provenance scope.",
                path="document_scope",
            )
        ledger = _freeze_json_object(self.ledger, path="ledger")
        coverage = _freeze_json_object(
            self.coverage_summary,
            path="coverage_summary",
        )
        context = _freeze_json_object(
            self.information_use_context,
            path="information_use_context",
        )
        _validate_public_ledger(ledger)
        _validate_complete_coverage(coverage)
        _validate_information_use_context(context)
        object.__setattr__(self, "ledger", ledger)
        object.__setattr__(self, "coverage_summary", coverage)
        object.__setattr__(self, "information_use_context", context)

    def to_dict(self) -> dict[str, Any]:
        """Returns a fresh deterministic public attachment representation."""
        return {
            "attachment_name": self.attachment_name,
            "document_role": self.document_role,
            "document_scope": self.document_scope,
            "ledger": _thaw_json_value(self.ledger),
            "coverage_summary": _thaw_json_value(self.coverage_summary),
            "information_use_context": _thaw_json_value(
                self.information_use_context
            ),
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class FieldProvenanceArtifactV1:
    """One actual public artifact and its matching provenance attachment."""

    artifact_name: str
    attachment: FieldProvenanceAttachmentV1

    def __post_init__(self) -> None:
        if self.artifact_name not in _ARTIFACT_ATTACHMENT_NAMES:
            raise _validation_error(
                "artifact_name is not supported for public field provenance.",
                path="artifact_name",
            )
        if not isinstance(self.attachment, FieldProvenanceAttachmentV1):
            raise _validation_error(
                "attachment must be a FieldProvenanceAttachmentV1.",
                path="attachment",
            )
        if self.attachment.attachment_name != _ARTIFACT_ATTACHMENT_NAMES[self.artifact_name]:
            raise _validation_error(
                "Artifact attachment_name does not match artifact_name.",
                path="attachment.attachment_name",
            )
        if self.attachment.document_scope != "artifact_document":
            raise _validation_error(
                "Artifact provenance requires artifact_document scope.",
                path="attachment.document_scope",
            )

    def to_dict(self) -> dict[str, Any]:
        """Returns a fresh deterministic artifact-provenance representation."""
        return {
            "artifact_name": self.artifact_name,
            "attachment": self.attachment.to_dict(),
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class FieldProvenanceBundleV1:
    """One immutable public Root Result and actual-artifact provenance bundle."""

    workflow: WorkflowV1
    result: FieldProvenanceAttachmentV1
    artifacts: tuple[FieldProvenanceArtifactV1, ...] = ()
    provenance_version: int = PUBLIC_FIELD_PROVENANCE_VERSION
    redaction_policy: str = _PUBLIC_REDACTION_POLICY

    def __post_init__(self) -> None:
        if (
            type(self.provenance_version) is not int
            or self.provenance_version != PUBLIC_FIELD_PROVENANCE_VERSION
        ):
            raise _validation_error(
                f"provenance_version must equal {PUBLIC_FIELD_PROVENANCE_VERSION}.",
                path="provenance_version",
            )
        if not isinstance(self.workflow, WorkflowV1):
            raise _validation_error("workflow must be a WorkflowV1.", path="workflow")
        if self.redaction_policy != _PUBLIC_REDACTION_POLICY:
            raise _validation_error(
                "redaction_policy must omit engine-private details.",
                path="redaction_policy",
            )
        if not isinstance(self.result, FieldProvenanceAttachmentV1):
            raise _validation_error(
                "result must be a FieldProvenanceAttachmentV1.",
                path="result",
            )
        if self.result.attachment_name != _RESULT_ATTACHMENT_NAMES[self.workflow]:
            raise _validation_error(
                "Result attachment_name does not match workflow.",
                path="result.attachment_name",
            )
        if self.result.document_scope != "root_result_without_field_provenance":
            raise _validation_error(
                "Result provenance requires root_result_without_field_provenance scope.",
                path="result.document_scope",
            )
        artifacts = tuple(self.artifacts) if isinstance(self.artifacts, list) else self.artifacts
        if not isinstance(artifacts, tuple) or any(
            not isinstance(artifact, FieldProvenanceArtifactV1) for artifact in artifacts
        ):
            raise _validation_error(
                "artifacts must contain only FieldProvenanceArtifactV1 values.",
                path="artifacts",
            )
        names = tuple(artifact.artifact_name for artifact in artifacts)
        if len(names) != len(set(names)):
            raise _validation_error(
                "artifacts must not contain duplicate names.",
                path="artifacts",
            )
        if artifacts and self.workflow is not WorkflowV1.TRAINING_DATASET:
            raise _validation_error(
                "Public artifact provenance is supported only for training_dataset.",
                path="artifacts",
            )
        attachments = (self.result, *(artifact.attachment for artifact in artifacts))
        if any(
            attachment.information_use_context["workflow"] != self.workflow.value
            for attachment in attachments
        ):
            raise _validation_error(
                "Attachment information-use workflow must match bundle workflow.",
                path="workflow",
            )
        object.__setattr__(
            self,
            "artifacts",
            tuple(sorted(artifacts, key=lambda artifact: artifact.artifact_name)),
        )

    def to_dict(self) -> dict[str, Any]:
        """Returns a fresh deterministic public bundle representation."""
        return {
            "provenance_version": self.provenance_version,
            "workflow": self.workflow.value,
            "redaction_policy": self.redaction_policy,
            "result": self.result.to_dict(),
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
        }
