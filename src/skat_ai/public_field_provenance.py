from __future__ import annotations

from collections.abc import Mapping

from skat_ai.api.v1.provenance import (
    PUBLIC_FIELD_PROVENANCE_ROOT_FIELD,
    FieldProvenanceArtifactV1,
    FieldProvenanceAttachmentV1,
    FieldProvenanceBundleV1,
)
from skat_ai.application.contracts import ApplicationExecutionResult
from skat_ai.application.provenance import (
    ApplicationProvenanceAttachment,
    ApplicationProvenanceBundle,
)
from skat_ai.errors import SkatAIInvariantError
from skat_ai.field_provenance import (
    build_public_serializable_field_provenance_ledger,
)
from skat_ai.field_provenance_coverage import (
    build_field_provenance_coverage_summary,
    build_serializable_field_provenance_coverage_summary,
)
from skat_ai.field_provenance_policy import (
    build_serializable_information_use_context,
    redact_field_provenance_ledger_for_public_output,
)
from skat_ai.v1_information_provenance_serialization import (
    V1_ARTIFACT_ATTACHMENTS,
    V1_RESULT_ATTACHMENT_NAMES,
    validate_v1_information_provenance_serialization_checkpoint,
)

_RESULT_ATTACHMENT_NAMES = V1_RESULT_ATTACHMENT_NAMES
_ARTIFACT_ATTACHMENTS = V1_ARTIFACT_ATTACHMENTS


def _invariant(message: str) -> SkatAIInvariantError:
    return SkatAIInvariantError(message)


def _select_exact_attachment(
    provenance: ApplicationProvenanceBundle,
    name: str,
) -> ApplicationProvenanceAttachment:
    matches = tuple(
        attachment for attachment in provenance.attachments if attachment.name == name
    )
    if len(matches) != 1:
        raise _invariant(
            f"Application provenance requires exactly one {name!r} attachment."
        )
    return matches[0]


def _build_public_attachment(
    attachment: ApplicationProvenanceAttachment,
    *,
    document: Mapping[str, object] | dict[str, object],
    document_scope: str,
    workflow: str,
) -> FieldProvenanceAttachmentV1:
    if attachment.document_role != "result":
        raise _invariant(
            f"Application provenance attachment {attachment.name!r} must have result role."
        )
    if attachment.document_to_dict() != document:
        raise _invariant(
            f"Application provenance attachment {attachment.name!r} does not match its document."
        )
    if attachment.information_use_context.workflow != workflow:
        raise _invariant(
            f"Application provenance attachment {attachment.name!r} has the wrong workflow."
        )

    redacted = redact_field_provenance_ledger_for_public_output(attachment.ledger)
    summary = build_field_provenance_coverage_summary(document, redacted)
    if (
        redacted.status != "complete"
        or not summary.all_paths_accounted_for
        or not summary.provenance_complete
        or summary.uncovered_paths
        or summary.orphaned_entry_paths
        or summary.orphaned_exemption_paths
        or summary.overlapping_paths
    ):
        raise _invariant(
            f"Public provenance attachment {attachment.name!r} is not complete for its document."
        )
    if any(
        exemption.reason == "legacy_untracked" for exemption in redacted.exemptions
    ) or any(
        limitation in {"legacy_untracked_fields", "provenance_not_available"}
        for limitation in redacted.limitations
    ):
        raise _invariant(
            f"Public provenance attachment {attachment.name!r} contains legacy detail."
        )

    try:
        return FieldProvenanceAttachmentV1(
            attachment_name=attachment.name,
            document_role=attachment.document_role,
            document_scope=document_scope,
            ledger=build_public_serializable_field_provenance_ledger(redacted),
            coverage_summary=build_serializable_field_provenance_coverage_summary(
                summary
            ),
            information_use_context=build_serializable_information_use_context(
                attachment.information_use_context
            ),
        )
    except (TypeError, ValueError) as error:
        raise _invariant(
            f"Application provenance attachment {attachment.name!r} is not public-safe."
        ) from error


def build_public_field_provenance_bundle(
    execution: ApplicationExecutionResult,
) -> FieldProvenanceBundleV1:
    """Builds the bounded public bundle from one retained Application execution."""
    if not isinstance(execution, ApplicationExecutionResult):
        raise _invariant("Public provenance requires an ApplicationExecutionResult.")
    validate_v1_information_provenance_serialization_checkpoint(execution)
    provenance = execution.provenance
    if provenance is None:
        raise _invariant("Application execution has no retained provenance bundle.")
    if provenance.workflow is not execution.result.workflow:
        raise _invariant("Application provenance workflow does not match the Root Result.")

    workflow = execution.result.workflow.value
    expected_result_name = _RESULT_ATTACHMENT_NAMES.get(workflow)
    if expected_result_name is None:
        raise _invariant(f"No public Result provenance mapping exists for {workflow!r}.")
    result_document = execution.result.to_dict()["document"]
    if not isinstance(result_document, dict):
        raise _invariant("Application Root Result must be a JSON object.")
    if PUBLIC_FIELD_PROVENANCE_ROOT_FIELD in result_document:
        raise _invariant("Application Root Result already contains field_provenance.")
    result_attachment = _build_public_attachment(
        _select_exact_attachment(provenance, expected_result_name),
        document=result_document,
        document_scope="root_result_without_field_provenance",
        workflow=workflow,
    )

    artifacts_by_name = {artifact.name: artifact for artifact in execution.artifacts}
    if len(artifacts_by_name) != len(execution.artifacts):
        raise _invariant("Application execution contains duplicate artifacts.")
    unexpected_artifacts = sorted(set(artifacts_by_name).difference(_ARTIFACT_ATTACHMENTS))
    if unexpected_artifacts:
        raise _invariant(
            f"No public provenance mapping exists for artifacts {unexpected_artifacts}."
        )
    mapped_attachment_names = {
        mapping[1] for mapping in _ARTIFACT_ATTACHMENTS.values()
    }
    retained_mapped_names = {
        attachment.name
        for attachment in provenance.attachments
        if attachment.name in mapped_attachment_names
    }
    expected_mapped_names = {
        _ARTIFACT_ATTACHMENTS[name][1] for name in artifacts_by_name
    }
    if retained_mapped_names != expected_mapped_names:
        raise _invariant(
            "Application artifact provenance attachments do not match actual artifacts."
        )

    public_artifacts = []
    for artifact_name, artifact in artifacts_by_name.items():
        expected_workflow, attachment_name = _ARTIFACT_ATTACHMENTS[artifact_name]
        if workflow != expected_workflow:
            raise _invariant(
                f"Artifact {artifact_name!r} is not valid for workflow {workflow!r}."
            )
        artifact_document = artifact.to_dict()
        public_artifacts.append(
            FieldProvenanceArtifactV1(
                artifact_name=artifact_name,
                attachment=_build_public_attachment(
                    _select_exact_attachment(provenance, attachment_name),
                    document=artifact_document,
                    document_scope="artifact_document",
                    workflow=workflow,
                ),
            )
        )

    try:
        return FieldProvenanceBundleV1(
            workflow=execution.result.workflow,
            result=result_attachment,
            artifacts=tuple(public_artifacts),
        )
    except (TypeError, ValueError) as error:
        raise _invariant("Application provenance cannot form a public bundle.") from error


def attach_public_field_provenance(
    execution: ApplicationExecutionResult,
) -> tuple[dict[str, object], FieldProvenanceBundleV1]:
    """Adds one public sidecar to a fresh Root Result document copy."""
    bundle = build_public_field_provenance_bundle(execution)
    document = execution.result.to_dict()["document"]
    if not isinstance(document, dict):
        raise _invariant("Application Root Result must be a JSON object.")
    document[PUBLIC_FIELD_PROVENANCE_ROOT_FIELD] = bundle.to_dict()
    return document, bundle
