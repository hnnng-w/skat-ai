from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from skatmind.api.v1.contracts import _freeze_json_object, _thaw_json_value
from skatmind.api.v1.provenance import (
    _validate_complete_coverage,
    _validate_identifier,
    _validate_public_ledger,
)
from skatmind.api.v1.session.contracts import SESSION_API_OPERATIONS
from skatmind.errors import SkatMindValidationError
from skatmind.field_provenance import parse_json_pointer, resolve_json_pointer
from skatmind.field_provenance_coverage import enumerate_json_leaf_paths
from skatmind.session_contracts import SESSION_CAPTURE_MODES, SESSION_PHASES

SESSION_FIELD_PROVENANCE_VERSION = 1
SESSION_FIELD_PROVENANCE_DOCUMENT_SCOPE = "session_operation_value"
SESSION_FIELD_PROVENANCE_REDACTION_POLICY = "omit_engine_private_details"


def _validation_error(message: str, *, path: str) -> SkatMindValidationError:
    return SkatMindValidationError(message, path=path)


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionProvenanceContextV1:
    """Public-safe context for one Session operation value."""

    operation: str
    session_id: str
    revision: int
    capture_mode: str
    phase: str

    def __post_init__(self) -> None:
        if self.operation not in SESSION_API_OPERATIONS:
            raise _validation_error(
                "operation must be one canonical Session API operation.",
                path="operation",
            )
        _validate_identifier(self.session_id, path="session_id")
        if type(self.revision) is not int or self.revision < 0:
            raise _validation_error(
                "revision must be a non-negative integer.",
                path="revision",
            )
        if self.capture_mode not in SESSION_CAPTURE_MODES:
            raise _validation_error(
                "capture_mode must be a valid Session Capture Mode.",
                path="capture_mode",
            )
        if self.phase not in SESSION_PHASES:
            raise _validation_error(
                "phase must be a valid Session phase.",
                path="phase",
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "operation": self.operation,
            "session_id": self.session_id,
            "revision": self.revision,
            "capture_mode": self.capture_mode,
            "phase": self.phase,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionFieldProvenanceAttachmentV1:
    """One complete public-safe provenance attachment for a Session value."""

    attachment_name: str
    document_role: str
    document_scope: str
    ledger: Mapping[str, object]
    coverage_summary: Mapping[str, object]
    session_context: Mapping[str, object]

    def __post_init__(self) -> None:
        if self.attachment_name != "session_operation_result":
            raise _validation_error(
                "attachment_name must equal 'session_operation_result'.",
                path="attachment_name",
            )
        if self.document_role != "result":
            raise _validation_error(
                "document_role must equal 'result'.",
                path="document_role",
            )
        if self.document_scope != SESSION_FIELD_PROVENANCE_DOCUMENT_SCOPE:
            raise _validation_error(
                "document_scope must equal the Session operation value scope.",
                path="document_scope",
            )
        ledger = _freeze_json_object(self.ledger, path="ledger")
        coverage = _freeze_json_object(
            self.coverage_summary,
            path="coverage_summary",
        )
        context = _freeze_json_object(self.session_context, path="session_context")
        _validate_public_ledger(ledger)
        _validate_complete_coverage(coverage)
        try:
            typed_context = SessionProvenanceContextV1(**dict(context))
        except (TypeError, ValueError) as error:
            raise _validation_error(
                "session_context must be one valid Session provenance context.",
                path="session_context",
            ) from error
        if typed_context.to_dict() != dict(context):
            raise _validation_error(
                "session_context must use its canonical representation.",
                path="session_context",
            )
        object.__setattr__(self, "ledger", ledger)
        object.__setattr__(self, "coverage_summary", coverage)
        object.__setattr__(self, "session_context", context)

    def to_dict(self) -> dict[str, Any]:
        return {
            "attachment_name": self.attachment_name,
            "document_role": self.document_role,
            "document_scope": self.document_scope,
            "ledger": _thaw_json_value(self.ledger),
            "coverage_summary": _thaw_json_value(self.coverage_summary),
            "session_context": _thaw_json_value(self.session_context),
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionFieldProvenanceBundleV1:
    """One immutable public Session value provenance bundle."""

    session_field_provenance_version: int = SESSION_FIELD_PROVENANCE_VERSION
    operation: str
    redaction_policy: str = SESSION_FIELD_PROVENANCE_REDACTION_POLICY
    result: SessionFieldProvenanceAttachmentV1

    def __post_init__(self) -> None:
        if (
            type(self.session_field_provenance_version) is not int
            or self.session_field_provenance_version
            != SESSION_FIELD_PROVENANCE_VERSION
        ):
            raise _validation_error(
                f"session_field_provenance_version must equal {SESSION_FIELD_PROVENANCE_VERSION}.",
                path="session_field_provenance_version",
            )
        if self.operation not in SESSION_API_OPERATIONS:
            raise _validation_error(
                "operation must be one canonical Session API operation.",
                path="operation",
            )
        if self.redaction_policy != SESSION_FIELD_PROVENANCE_REDACTION_POLICY:
            raise _validation_error(
                "redaction_policy must omit engine-private details.",
                path="redaction_policy",
            )
        if type(self.result) is not SessionFieldProvenanceAttachmentV1:
            raise _validation_error(
                "result must be a SessionFieldProvenanceAttachmentV1.",
                path="result",
            )
        if self.result.session_context["operation"] != self.operation:
            raise _validation_error(
                "result Session context operation must match the bundle operation.",
                path="result.session_context.operation",
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_field_provenance_version": self.session_field_provenance_version,
            "operation": self.operation,
            "redaction_policy": self.redaction_policy,
            "result": self.result.to_dict(),
        }


def validate_session_provenance_for_value_v1(
    bundle: SessionFieldProvenanceBundleV1,
    value: object,
) -> None:
    """Reconciles one public sidecar with the exact typed operation value."""
    document = value.to_dict()
    if not isinstance(document, Mapping):
        raise _validation_error(
            "Session operation value must serialize to an object.",
            path="value",
        )
    expected_coverage = _recompute_public_coverage(document, bundle.result.ledger)
    actual_coverage = _thaw_json_value(bundle.result.coverage_summary)
    if actual_coverage != expected_coverage:
        raise _validation_error(
            "field_provenance coverage does not match the Session operation value.",
            path="field_provenance.result.coverage_summary",
        )
    _validate_context_for_value(bundle.result.session_context, value)


def _covered_leaf_paths(
    document: Mapping[str, object],
    leaf_paths: tuple[str, ...],
    *,
    field_path: str,
    coverage_kind: str,
) -> tuple[str, ...] | None:
    try:
        resolve_json_pointer(document, field_path)
    except SkatMindValidationError:
        return None
    if coverage_kind == "field":
        return (field_path,) if field_path in leaf_paths else None
    ancestor = parse_json_pointer(field_path)
    covered = tuple(
        leaf_path
        for leaf_path in leaf_paths
        if parse_json_pointer(leaf_path)[: len(ancestor)] == ancestor
    )
    return covered or None


def _recompute_public_coverage(
    document: Mapping[str, object],
    ledger: Mapping[str, object],
) -> dict[str, object]:
    leaf_paths = enumerate_json_leaf_paths(document)
    coverage_count = {path: 0 for path in leaf_paths}
    provenanced_paths: set[str] = set()
    exempted_paths: set[str] = set()
    orphaned_entries: list[str] = []
    orphaned_exemptions: list[str] = []
    for declaration, covered_paths, orphaned_paths in (
        (ledger["entries"], provenanced_paths, orphaned_entries),
        (ledger["exemptions"], exempted_paths, orphaned_exemptions),
    ):
        for item in declaration:
            covered = _covered_leaf_paths(
                document,
                leaf_paths,
                field_path=item["field_path"],
                coverage_kind=item["coverage_kind"],
            )
            if covered is None:
                orphaned_paths.append(item["field_path"])
                continue
            for path in covered:
                coverage_count[path] += 1
                covered_paths.add(path)
    uncovered = tuple(sorted(path for path, count in coverage_count.items() if count == 0))
    overlapping = tuple(sorted(path for path, count in coverage_count.items() if count > 1))
    orphaned_entry_paths = tuple(sorted(orphaned_entries))
    orphaned_exemption_paths = tuple(sorted(orphaned_exemptions))
    complete = not (
        uncovered
        or overlapping
        or orphaned_entry_paths
        or orphaned_exemption_paths
    )
    return {
        "leaf_path_count": len(leaf_paths),
        "provenanced_path_count": len(provenanced_paths),
        "exempted_path_count": len(exempted_paths),
        "uncovered_paths": list(uncovered),
        "orphaned_entry_paths": list(orphaned_entry_paths),
        "orphaned_exemption_paths": list(orphaned_exemption_paths),
        "overlapping_paths": list(overlapping),
        "all_paths_accounted_for": not uncovered and not overlapping,
        "provenance_complete": complete and ledger["status"] == "complete",
    }


def _validate_context_for_value(
    context: Mapping[str, object],
    value: object,
) -> None:
    from skatmind.session_checkpoint_review import SessionCheckpointReviewExportV1
    from skatmind.session_contracts import SessionStateV1
    from skatmind.session_decision_checkpoint import SessionDecisionCheckpointV1
    from skatmind.session_decision_observation import SessionDecisionObservationV1
    from skatmind.session_export_contracts import SessionRequestExportV1
    from skatmind.session_history_contracts import (
        SessionCheckpointLineageV1,
        SessionCorrectionResultV1,
        SessionUndoResultV1,
    )
    from skatmind.session_persistence_contracts import (
        SessionPersistenceDocumentV1,
        SessionResumeResultV1,
    )
    from skatmind.session_validation import SessionTransitionResultV1

    state = None
    expected_session_id: str
    expected_revision: int
    expected_capture_mode: str | None = None
    if type(value) is SessionStateV1:
        state = value
    elif type(value) in {
        SessionTransitionResultV1,
        SessionUndoResultV1,
        SessionCorrectionResultV1,
    }:
        state = value.state
    elif type(value) is SessionPersistenceDocumentV1:
        state = value.state
    elif type(value) is SessionResumeResultV1:
        state = value.document.state
    if state is not None:
        expected_session_id = state.session_id
        expected_revision = state.revision
        expected_capture_mode = state.capture_mode
        expected_phase = state.phase
    elif type(value) is SessionRequestExportV1:
        expected_session_id = value.session_id
        expected_revision = value.source_revision
        expected_phase = None
    elif type(value) is SessionDecisionCheckpointV1:
        expected_session_id = value.session_id
        expected_revision = value.source_revision
        expected_capture_mode = value.source_capture_mode
        expected_phase = None
    elif type(value) is SessionCheckpointLineageV1:
        expected_session_id = value.session_id
        expected_revision = value.state_revision
        expected_phase = None
    elif type(value) is SessionDecisionObservationV1:
        expected_session_id = value.session_id
        expected_revision = value.state_revision
        expected_phase = None
    elif type(value) is SessionCheckpointReviewExportV1:
        expected_session_id = value.session_id
        expected_revision = value.observation_revision
        expected_phase = None
    else:
        raise _validation_error(
            "Unsupported Session operation value for provenance context.",
            path="value",
        )
    if (
        context["session_id"] != expected_session_id
        or context["revision"] != expected_revision
        or (
            expected_capture_mode is not None
            and context["capture_mode"] != expected_capture_mode
        )
        or (expected_phase is not None and context["phase"] != expected_phase)
    ):
        raise _validation_error(
            "field_provenance context does not match the Session operation value.",
            path="field_provenance.result.session_context",
        )
