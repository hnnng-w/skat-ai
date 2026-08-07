from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from skat_ai.api.v1.contracts import WorkflowV1
from skat_ai.application.contracts import _freeze_json_object, _thaw_json_value
from skat_ai.errors import SkatAIValidationError
from skat_ai.field_provenance import FieldProvenanceLedger
from skat_ai.field_provenance_coverage import (
    FieldProvenanceCoverageSummary,
    build_field_provenance_coverage_summary,
)
from skat_ai.field_provenance_policy import InformationUseContext

APPLICATION_PROVENANCE_VERSION = 1
APPLICATION_PROVENANCE_DOCUMENT_ROLES = ("consumed_input", "result")


def _validation_error(message: str, *, path: str) -> SkatAIValidationError:
    return SkatAIValidationError(message, path=path)


def _validate_identifier(value: object, *, path: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise _validation_error(
            f"{path} must be a non-empty, non-padded string.",
            path=path,
        )
    return value


def _attachment_sort_key(
    attachment: ApplicationProvenanceAttachment,
) -> tuple[int, int, int, int, str]:
    name = attachment.name
    if name == "flat_decision":
        return (0, 0, 0, 0, name)
    if name.startswith("multi_step_decision/"):
        suffix = name.removeprefix("multi_step_decision/")
        if suffix.isascii() and suffix.isdecimal():
            return (1, int(suffix), 0, 0, name)
    if name.startswith("policy_comparison_decision/"):
        parts = name.split("/")
        if (
            len(parts) == 4
            and parts[1].isascii()
            and parts[1].isdecimal()
            and parts[3].isascii()
            and parts[3].isdecimal()
        ):
            return (2, int(parts[1]), int(parts[3]), 0, name)
    if name.startswith("flat_retrospective/"):
        stage = name.removeprefix("flat_retrospective/")
        stage_order = {"input": 0, "analysis": 1, "assessment": 2}
        if stage in stage_order:
            return (3, 0, stage_order[stage], 0, name)
    if name.startswith("historical_decision/"):
        parts = name.split("/")
        stage_order = {"input": 0, "analysis": 1, "assessment": 2}
        if (
            len(parts) == 3
            and parts[1].isascii()
            and parts[1].isdecimal()
            and int(parts[1]) > 0
            and parts[2] in stage_order
        ):
            return (4, int(parts[1]), stage_order[parts[2]], 0, name)
    aggregate_order = {
        "historical_snapshot_summary": 5,
        "historical_immediate_review_summary": 6,
        "historical_search_review_summary": 7,
        "replay_coaching/prioritization": 8,
        "replay_coaching/guidance": 9,
        "replay_coaching/report": 10,
    }
    if name in aggregate_order:
        return (aggregate_order[name], 0, 0, 0, name)
    if name == "position_result":
        return (11, 0, 0, 0, name)
    if name == "historical_game_result":
        return (12, 0, 0, 0, name)
    fixed_names = {
        "training_dataset/input": 13,
        "training_dataset/summary": 18,
        "training_dataset/partition_audit": 18,
        "training_dataset/rolling_evaluation": 18,
        "training_dataset/bounded_search_evaluation": 18,
        "training_dataset/opponent_statistics_aggregation": 18,
        "training_dataset/opponent_statistics_input": 19,
        "training_dataset_result": 20,
        "dataset_preparation/input": 21,
        "dataset_preparation/plan": 23,
        "dataset_preparation/materialized_dataset": 24,
        "dataset_preparation_result": 25,
        "opponent_statistics/input": 26,
        "opponent_statistics/summary": 29,
        "opponent_statistics_result": 30,
        "historical_list/input": 31,
        "historical_list/aggregation": 33,
        "historical_list_result": 34,
        "historical_list_comparison/input": 35,
        "historical_list_comparison_result": 38,
    }
    if name in fixed_names:
        return (fixed_names[name], 0, 0, 0, name)
    numeric_families = {
        "training_dataset/record": 14,
        "dataset_preparation/source": 22,
        "opponent_statistics/record": 27,
        "opponent_statistics/profile": 28,
        "historical_list/entry": 32,
        "historical_list_comparison/source": 36,
        "historical_list_comparison/pair": 37,
    }
    for prefix, order in numeric_families.items():
        parts = name.split("/")
        if (
            parts[:-1] == prefix.split("/")
            and parts[-1].isascii()
            and parts[-1].isdecimal()
        ):
            return (order, int(parts[-1]), 0, 0, name)
    staged_families = {
        "sample": (15, {"feature": 0, "target": 1}),
        "rolling": (16, {"prediction": 0, "actual": 1}),
        "search": (
            17,
            {
                "input": 0,
                "immediate": 1,
                "search": 2,
                "comparison": 3,
                "actual": 4,
                "retrospective": 5,
            },
        ),
    }
    parts = name.split("/")
    if len(parts) == 5 and parts[0] == "training_dataset":
        family = staged_families.get(parts[1])
        if (
            family is not None
            and parts[2].isascii()
            and parts[2].isdecimal()
            and parts[3].isascii()
            and parts[3].isdecimal()
            and parts[4] in family[1]
        ):
            return (
                family[0],
                int(parts[2]),
                int(parts[3]),
                family[1][parts[4]],
                name,
            )
    return (39, 0, 0, 0, name)


@dataclass(frozen=True, slots=True, kw_only=True)
class ApplicationProvenanceAttachment:
    """One immutable document and its matching field-provenance sidecar."""

    name: str
    document_role: str
    document: object
    ledger: FieldProvenanceLedger
    coverage_summary: FieldProvenanceCoverageSummary
    information_use_context: InformationUseContext

    def __post_init__(self) -> None:
        _validate_identifier(self.name, path="name")
        if self.document_role not in APPLICATION_PROVENANCE_DOCUMENT_ROLES:
            raise _validation_error(
                "document_role must be consumed_input or result.",
                path="document_role",
            )
        if not isinstance(self.ledger, FieldProvenanceLedger):
            raise _validation_error(
                "ledger must be a FieldProvenanceLedger.",
                path="ledger",
            )
        if not isinstance(self.coverage_summary, FieldProvenanceCoverageSummary):
            raise _validation_error(
                "coverage_summary must be a FieldProvenanceCoverageSummary.",
                path="coverage_summary",
            )
        if not isinstance(self.information_use_context, InformationUseContext):
            raise _validation_error(
                "information_use_context must be an InformationUseContext.",
                path="information_use_context",
            )
        frozen_document = _freeze_json_object(self.document, path="document")
        expected_summary = build_field_provenance_coverage_summary(
            frozen_document,
            self.ledger,
        )
        if expected_summary != self.coverage_summary:
            raise _validation_error(
                "coverage_summary does not match the attached document and ledger.",
                path="coverage_summary",
            )
        if self.ledger.status != "not_available" and (
            not expected_summary.all_paths_accounted_for
            or expected_summary.orphaned_entry_paths
            or expected_summary.orphaned_exemption_paths
        ):
            raise _validation_error(
                "The attached ledger does not account for the exact document.",
                path="coverage_summary",
            )
        if self.ledger.status == "complete" and not expected_summary.provenance_complete:
            raise _validation_error(
                "A complete attachment requires complete non-legacy provenance.",
                path="coverage_summary",
            )
        object.__setattr__(self, "document", frozen_document)

    def document_to_dict(self) -> dict[str, Any]:
        """Returns a fresh mutable copy of the attached JSON document."""
        return _thaw_json_value(self.document)


@dataclass(frozen=True, slots=True, kw_only=True)
class ApplicationProvenanceBundle:
    """Canonical immutable provenance attachments for one Application result."""

    workflow: WorkflowV1
    attachments: tuple[ApplicationProvenanceAttachment, ...]
    provenance_version: int = APPLICATION_PROVENANCE_VERSION

    def __post_init__(self) -> None:
        if (
            type(self.provenance_version) is not int
            or self.provenance_version != APPLICATION_PROVENANCE_VERSION
        ):
            raise _validation_error(
                f"provenance_version must equal {APPLICATION_PROVENANCE_VERSION}.",
                path="provenance_version",
            )
        if not isinstance(self.workflow, WorkflowV1):
            raise _validation_error("workflow must be a WorkflowV1.", path="workflow")
        attachments = (
            tuple(self.attachments)
            if isinstance(self.attachments, list)
            else self.attachments
        )
        if not isinstance(attachments, tuple) or any(
            not isinstance(item, ApplicationProvenanceAttachment)
            for item in attachments
        ):
            raise _validation_error(
                "attachments must contain only ApplicationProvenanceAttachment values.",
                path="attachments",
            )
        names = tuple(item.name for item in attachments)
        if len(names) != len(set(names)):
            raise _validation_error(
                "attachments must have unique names.",
                path="attachments",
            )
        object.__setattr__(
            self,
            "attachments",
            tuple(sorted(attachments, key=_attachment_sort_key)),
        )
