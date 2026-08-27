from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from skat_ai.api.v1.contracts import ResultDocumentV1, WorkflowV1
from skat_ai.application.contracts import (
    ApplicationArtifact,
    ApplicationExecutionResult,
    ApplicationInvocation,
    _freeze_json_object,
    _thaw_json_value,
)
from skat_ai.application.provenance import (
    ApplicationProvenanceAttachment,
    ApplicationProvenanceBundle,
)
from skat_ai.errors import SkatAIInvariantError, SkatAIValidationError
from skat_ai.field_provenance_coverage import build_field_provenance_coverage_summary
from skat_ai.v1_information_provenance_enforcement import (
    V1_INFORMATION_PROVENANCE_ENFORCEMENT_STAGES,
    V1_INFORMATION_PROVENANCE_ENFORCEMENT_VERSION,
    V1InformationProvenanceRetainedLinkage,
    validate_v1_information_provenance_enforcement_version,
)
from skat_ai.v1_information_provenance_sources import (
    V1InformationProvenanceSources,
    exact_v1_json_equal,
    validate_v1_information_provenance_sources,
)

V1_RESULT_ATTACHMENT_NAMES = MappingProxyType({
    "position_analysis": "position_result",
    "historical_game": "historical_game_result",
    "training_dataset": "training_dataset_result",
    "training_dataset_preparation": "dataset_preparation_result",
    "opponent_statistics": "opponent_statistics_result",
    "fixed_three_player_historical_list": "historical_list_result",
    "fixed_three_player_historical_list_comparison": (
        "historical_list_comparison_result"
    ),
})
V1_ARTIFACT_ATTACHMENTS = MappingProxyType({
    "opponent_statistics_input": (
        "training_dataset",
        "training_dataset/opponent_statistics_input",
    ),
})


def _invariant(message: str) -> SkatAIInvariantError:
    return SkatAIInvariantError(message)


def _select_exact_attachment(
    provenance: ApplicationProvenanceBundle,
    name: str,
) -> ApplicationProvenanceAttachment:
    matches = tuple(item for item in provenance.attachments if item.name == name)
    if len(matches) != 1:
        raise _invariant(
            f"Application provenance requires exactly one {name!r} attachment."
        )
    return matches[0]


def _validate_complete_attachment(
    attachment: ApplicationProvenanceAttachment,
    *,
    workflow: str,
    document: Mapping[str, object],
) -> None:
    if attachment.document_role != "result":
        raise _invariant(
            f"Application provenance attachment {attachment.name!r} must have result role."
        )
    if attachment.information_use_context.workflow != workflow:
        raise _invariant(
            f"Application provenance attachment {attachment.name!r} has the wrong workflow."
        )
    if not exact_v1_json_equal(attachment.document_to_dict(), document):
        raise _invariant(
            f"Application provenance attachment {attachment.name!r} does not match its document."
        )
    summary = build_field_provenance_coverage_summary(document, attachment.ledger)
    if (
        attachment.ledger.status != "complete"
        or not summary.all_paths_accounted_for
        or not summary.provenance_complete
        or summary.uncovered_paths
        or summary.orphaned_entry_paths
        or summary.orphaned_exemption_paths
        or summary.overlapping_paths
        or summary != attachment.coverage_summary
        or any(
            exemption.reason == "legacy_untracked"
            for exemption in attachment.ledger.exemptions
        )
    ):
        raise _invariant(
            f"Application provenance attachment {attachment.name!r} is not complete."
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class V1InformationProvenanceArtifactCheckpoint:
    """Exact immutable actual-artifact serialization checkpoint."""

    artifact_name: str
    attachment_name: str
    document: Mapping[str, object]

    def __post_init__(self) -> None:
        if not isinstance(self.artifact_name, str) or not self.artifact_name:
            raise SkatAIValidationError(
                "artifact_name must be a non-empty string.",
                path="artifact_name",
            )
        if not isinstance(self.attachment_name, str) or not self.attachment_name:
            raise SkatAIValidationError(
                "attachment_name must be a non-empty string.",
                path="attachment_name",
            )
        object.__setattr__(
            self,
            "document",
            _freeze_json_object(self.document, path="document"),
        )

    def document_to_dict(self) -> dict[str, Any]:
        return _thaw_json_value(self.document)


@dataclass(frozen=True, slots=True, kw_only=True)
class V1InformationProvenanceSerializationCheckpoint:
    """Internal proof that one Root execution crossed all four stages once."""

    workflow: WorkflowV1
    sources: V1InformationProvenanceSources
    provenance: ApplicationProvenanceBundle
    trusted_checkpoint_documents: tuple[
        tuple[str, Mapping[str, object]], ...
    ]
    linked_attachment_names: tuple[str, ...]
    result_attachment_name: str
    result_envelope: Mapping[str, object]
    result_document: Mapping[str, object]
    artifact_checkpoints: tuple[V1InformationProvenanceArtifactCheckpoint, ...]
    completed_stages: tuple[str, ...] = V1_INFORMATION_PROVENANCE_ENFORCEMENT_STAGES
    source_build_count: int = 1
    pre_analysis_enforcement_count: int = 1
    retained_stage_linkage_count: int = 1
    final_serialization_count: int = 1
    enforcement_version: int = V1_INFORMATION_PROVENANCE_ENFORCEMENT_VERSION

    def __post_init__(self) -> None:
        validate_v1_information_provenance_enforcement_version(
            self.enforcement_version
        )
        if not isinstance(self.workflow, WorkflowV1):
            raise SkatAIValidationError("workflow must be a WorkflowV1.", path="workflow")
        if not isinstance(self.sources, V1InformationProvenanceSources):
            raise SkatAIValidationError(
                "sources must be V1InformationProvenanceSources.",
                path="sources",
            )
        if self.sources.workflow is not self.workflow:
            raise SkatAIValidationError(
                "source workflow must match checkpoint workflow.",
                path="sources",
            )
        if not isinstance(self.provenance, ApplicationProvenanceBundle):
            raise SkatAIValidationError(
                "provenance must be an ApplicationProvenanceBundle.",
                path="provenance",
            )
        if self.provenance.workflow is not self.workflow:
            raise SkatAIValidationError(
                "provenance workflow must match checkpoint workflow.",
                path="provenance",
            )
        trusted_checkpoints = tuple(self.trusted_checkpoint_documents)
        trusted_names = tuple(name for name, _document in trusted_checkpoints)
        if len(trusted_names) != len(set(trusted_names)):
            raise SkatAIValidationError(
                "trusted checkpoint names must be unique.",
                path="trusted_checkpoint_documents",
            )
        names = tuple(self.linked_attachment_names)
        if any(not isinstance(name, str) or not name for name in names):
            raise SkatAIValidationError(
                "linked_attachment_names must contain non-empty strings.",
                path="linked_attachment_names",
            )
        if len(names) != len(set(names)):
            raise SkatAIValidationError(
                "linked_attachment_names must be unique.",
                path="linked_attachment_names",
            )
        if not isinstance(self.result_attachment_name, str) or not self.result_attachment_name:
            raise SkatAIValidationError(
                "result_attachment_name must be a non-empty string.",
                path="result_attachment_name",
            )
        checkpoints = tuple(self.artifact_checkpoints)
        if any(
            not isinstance(item, V1InformationProvenanceArtifactCheckpoint)
            for item in checkpoints
        ):
            raise SkatAIValidationError(
                "artifact_checkpoints contains an invalid value.",
                path="artifact_checkpoints",
            )
        artifact_names = tuple(item.artifact_name for item in checkpoints)
        if len(artifact_names) != len(set(artifact_names)):
            raise SkatAIValidationError(
                "artifact_checkpoints must have unique artifact names.",
                path="artifact_checkpoints",
            )
        if tuple(self.completed_stages) != V1_INFORMATION_PROVENANCE_ENFORCEMENT_STAGES:
            raise SkatAIValidationError(
                "completed_stages must equal the ordered v1 lifecycle.",
                path="completed_stages",
            )
        for name in (
            "source_build_count",
            "pre_analysis_enforcement_count",
            "retained_stage_linkage_count",
            "final_serialization_count",
        ):
            value = getattr(self, name)
            if type(value) is not int or value != 1:
                raise SkatAIValidationError(
                    f"{name} must equal 1.",
                    path=name,
                )
        object.__setattr__(self, "linked_attachment_names", names)
        object.__setattr__(
            self,
            "trusted_checkpoint_documents",
            tuple(
                (name, _freeze_json_object(document, path="checkpoint_document"))
                for name, document in trusted_checkpoints
            ),
        )
        object.__setattr__(
            self,
            "result_envelope",
            _freeze_json_object(self.result_envelope, path="result_envelope"),
        )
        object.__setattr__(
            self,
            "result_document",
            _freeze_json_object(self.result_document, path="result_document"),
        )
        object.__setattr__(self, "artifact_checkpoints", checkpoints)
        object.__setattr__(
            self,
            "completed_stages",
            V1_INFORMATION_PROVENANCE_ENFORCEMENT_STAGES,
        )

    @property
    def artifact_attachment_names(self) -> tuple[str, ...]:
        return tuple(item.attachment_name for item in self.artifact_checkpoints)

    def result_document_to_dict(self) -> dict[str, Any]:
        return _thaw_json_value(self.result_document)

    def result_envelope_to_dict(self) -> dict[str, Any]:
        return _thaw_json_value(self.result_envelope)


def _validate_result_and_artifacts(
    *,
    result: ResultDocumentV1,
    artifacts: tuple[ApplicationArtifact, ...],
    provenance: ApplicationProvenanceBundle,
) -> tuple[
    str,
    dict[str, object],
    tuple[V1InformationProvenanceArtifactCheckpoint, ...],
]:
    workflow = result.workflow.value
    expected_result_name = V1_RESULT_ATTACHMENT_NAMES.get(workflow)
    if expected_result_name is None:
        raise _invariant(f"No v1 Result provenance mapping exists for {workflow!r}.")
    document = result.to_dict()["document"]
    if not isinstance(document, dict):
        raise _invariant("Application Root Result must be a JSON object.")
    _validate_complete_attachment(
        _select_exact_attachment(provenance, expected_result_name),
        workflow=workflow,
        document=document,
    )

    artifacts_by_name = {artifact.name: artifact for artifact in artifacts}
    if len(artifacts_by_name) != len(artifacts):
        raise _invariant("Application execution contains duplicate artifacts.")
    unexpected = sorted(set(artifacts_by_name).difference(V1_ARTIFACT_ATTACHMENTS))
    if unexpected:
        raise _invariant(
            f"No v1 provenance mapping exists for artifacts {unexpected}."
        )
    mapped_attachment_names = {
        mapping[1] for mapping in V1_ARTIFACT_ATTACHMENTS.values()
    }
    retained_mapped_names = {
        attachment.name
        for attachment in provenance.attachments
        if attachment.name in mapped_attachment_names
    }
    expected_mapped_names = {
        V1_ARTIFACT_ATTACHMENTS[name][1] for name in artifacts_by_name
    }
    if retained_mapped_names != expected_mapped_names:
        raise _invariant(
            "Application artifact provenance attachments do not match actual artifacts."
        )

    checkpoints = []
    for artifact in artifacts:
        expected_workflow, attachment_name = V1_ARTIFACT_ATTACHMENTS[artifact.name]
        if workflow != expected_workflow:
            raise _invariant(
                f"Artifact {artifact.name!r} is not valid for workflow {workflow!r}."
            )
        artifact_document = artifact.to_dict()
        _validate_complete_attachment(
            _select_exact_attachment(provenance, attachment_name),
            workflow=workflow,
            document=artifact_document,
        )
        checkpoints.append(
            V1InformationProvenanceArtifactCheckpoint(
                artifact_name=artifact.name,
                attachment_name=attachment_name,
                document=artifact_document,
            )
        )
    return expected_result_name, document, tuple(checkpoints)


def reconcile_v1_information_provenance_serialization(
    *,
    invocation: ApplicationInvocation,
    sources: V1InformationProvenanceSources,
    linkage: V1InformationProvenanceRetainedLinkage,
    result: ResultDocumentV1,
    artifacts: tuple[ApplicationArtifact, ...],
    provenance: ApplicationProvenanceBundle,
) -> V1InformationProvenanceSerializationCheckpoint:
    """Reconciles exact current Result and actual artifacts before return."""
    validate_v1_information_provenance_sources(invocation, sources)
    if linkage.workflow is not invocation.request.workflow:
        raise _invariant("Retained provenance linkage has the wrong workflow.")
    if result.workflow is not invocation.request.workflow:
        raise _invariant("Application Result has the wrong workflow.")
    if provenance.workflow is not result.workflow:
        raise _invariant("Application provenance workflow does not match the Root Result.")
    current_names = tuple(item.name for item in provenance.attachments)
    if current_names != linkage.linked_attachment_names:
        raise _invariant("Retained provenance attachments changed after linkage.")
    result_name, result_document, artifact_checkpoints = _validate_result_and_artifacts(
        result=result,
        artifacts=artifacts,
        provenance=provenance,
    )
    return V1InformationProvenanceSerializationCheckpoint(
        workflow=result.workflow,
        sources=sources,
        provenance=provenance,
        trusted_checkpoint_documents=linkage.trusted_checkpoint_documents,
        linked_attachment_names=current_names,
        result_attachment_name=result_name,
        result_envelope=result.to_dict(),
        result_document=result_document,
        artifact_checkpoints=artifact_checkpoints,
    )


def validate_v1_information_provenance_serialization_checkpoint(
    execution: ApplicationExecutionResult,
) -> None:
    """Revalidates the immutable stable boundary without executing product work."""
    if not isinstance(execution, ApplicationExecutionResult):
        raise _invariant("V1 serialization requires an ApplicationExecutionResult.")
    checkpoint = execution.information_provenance_enforcement
    if checkpoint is None:
        raise _invariant("Application execution has no v1 provenance checkpoint.")
    if execution.provenance is None:
        raise _invariant("Application execution has no retained provenance bundle.")
    if checkpoint.workflow is not execution.result.workflow:
        raise _invariant("V1 provenance checkpoint has the wrong workflow.")
    if execution.provenance != checkpoint.provenance:
        raise _invariant("Retained provenance changed after final serialization.")
    result_name, result_document, artifact_checkpoints = _validate_result_and_artifacts(
        result=execution.result,
        artifacts=execution.artifacts,
        provenance=execution.provenance,
    )
    if result_name != checkpoint.result_attachment_name or not exact_v1_json_equal(
        result_document,
        checkpoint.result_document,
    ):
        raise _invariant("Application Root Result does not match its v1 checkpoint.")
    if not exact_v1_json_equal(
        execution.result.to_dict(),
        checkpoint.result_envelope,
    ):
        raise _invariant("Application Root Result envelope does not match its v1 checkpoint.")
    if tuple(item.name for item in execution.provenance.attachments) != (
        checkpoint.linked_attachment_names
    ):
        raise _invariant("Retained provenance attachments changed after final serialization.")
    if len(artifact_checkpoints) != len(checkpoint.artifact_checkpoints):
        raise _invariant("Application actual artifacts do not match the v1 checkpoint.")
    for current, retained in zip(
        artifact_checkpoints,
        checkpoint.artifact_checkpoints,
        strict=True,
    ):
        if (
            current.artifact_name != retained.artifact_name
            or current.attachment_name != retained.attachment_name
            or not exact_v1_json_equal(current.document, retained.document)
        ):
            raise _invariant("Application artifact does not match its v1 checkpoint.")
