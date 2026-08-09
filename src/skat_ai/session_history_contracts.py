from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from skat_ai.session_commands import (
    SessionCommandV1,
    is_session_command_v1,
    serialize_session_command_v1,
)
from skat_ai.session_contracts import SessionCommandRecordV1, SessionStateV1
from skat_ai.session_validation import (
    SESSION_DIAGNOSTIC_SEVERITIES,
    SessionValidationDiagnosticV1,
)

SESSION_HISTORY_EDIT_VERSION = 1

SESSION_UNDO_POLICY = "immutable_strict_prefix_rewind"
SESSION_CORRECTION_POLICY = "replace_one_command_then_replay_suffix"
SESSION_CORRECTION_SUFFIX_POLICY = "stop_before_first_rejected_command"
SESSION_HISTORY_STATE_POLICY = "accepted_log_length_per_immutable_state"
SESSION_BRANCHING_POLICY = "unsupported"
SESSION_REDO_POLICY = "caller_retained_suffix_only"

SESSION_UNDO_STATUSES = (
    "applied",
    "unchanged",
    "rejected",
    "revision_conflict",
)
SESSION_CORRECTION_STATUSES = (
    "applied",
    "unchanged",
    "partial",
    "rejected",
    "revision_conflict",
)

SESSION_CHECKPOINT_LINEAGE_VERSION = 1
SESSION_CHECKPOINT_RELATIONSHIPS = (
    "current",
    "ancestor",
    "future",
    "diverged",
)

_SEVERITY_ORDER = {
    severity: index for index, severity in enumerate(SESSION_DIAGNOSTIC_SEVERITIES)
}


def _require_identifier(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{field_name} must be a non-empty, non-padded string.")
    return value


def _require_non_negative_integer(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer.")
    return value


def _require_positive_integer(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer.")
    return value


def _require_ordered_values(value: object, field_name: str) -> tuple[object, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        raise ValueError(f"{field_name} must be an ordered array.")
    return tuple(value)


def _canonicalize_records(
    value: object,
    field_name: str,
) -> tuple[SessionCommandRecordV1, ...]:
    records = _require_ordered_values(value, field_name)
    if any(type(record) is not SessionCommandRecordV1 for record in records):
        raise ValueError(
            f"{field_name} must contain only SessionCommandRecordV1 values."
        )
    return records


def _canonicalize_diagnostics(
    value: object,
) -> tuple[SessionValidationDiagnosticV1, ...]:
    diagnostics = _require_ordered_values(value, "diagnostics")
    if any(
        type(diagnostic) is not SessionValidationDiagnosticV1
        for diagnostic in diagnostics
    ):
        raise ValueError(
            "diagnostics must contain only SessionValidationDiagnosticV1 values."
        )
    if len(diagnostics) != len(set(diagnostics)):
        raise ValueError("Duplicate Session history diagnostics are not allowed.")
    return tuple(
        sorted(
            diagnostics,
            key=lambda diagnostic: (
                _SEVERITY_ORDER[diagnostic.severity],
                diagnostic.path,
                diagnostic.code,
                diagnostic.message,
            ),
        )
    )


def _require_contiguous_revisions(
    records: tuple[SessionCommandRecordV1, ...],
    *,
    first_revision: int,
    field_name: str,
) -> None:
    if tuple(record.revision for record in records) != tuple(
        range(first_revision, first_revision + len(records))
    ):
        raise ValueError(f"{field_name} revisions must be contiguous and exact.")


def _require_conflict_diagnostic(
    diagnostics: tuple[SessionValidationDiagnosticV1, ...],
) -> None:
    if (
        len(diagnostics) != 1
        or diagnostics[0].code != "revision_conflict"
        or not diagnostics[0].blocks_command
    ):
        raise ValueError(
            "A revision conflict requires exactly one blocking revision_conflict "
            "diagnostic."
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionUndoResultV1:
    """One immutable strict-prefix Session rewind outcome."""

    session_history_edit_version: int = SESSION_HISTORY_EDIT_VERSION
    status: str
    session_id: str
    expected_revision: int
    source_revision: int
    target_revision: int
    current_revision: int
    state: SessionStateV1
    removed_records: tuple[SessionCommandRecordV1, ...]
    diagnostics: tuple[SessionValidationDiagnosticV1, ...]

    def __post_init__(self) -> None:
        if (
            type(self.session_history_edit_version) is not int
            or self.session_history_edit_version != SESSION_HISTORY_EDIT_VERSION
        ):
            raise ValueError(
                "session_history_edit_version must equal "
                f"{SESSION_HISTORY_EDIT_VERSION}."
            )
        if self.status not in SESSION_UNDO_STATUSES:
            raise ValueError(f"status must be one of {list(SESSION_UNDO_STATUSES)}.")
        _require_identifier(self.session_id, "session_id")
        _require_non_negative_integer(self.expected_revision, "expected_revision")
        _require_non_negative_integer(self.source_revision, "source_revision")
        _require_non_negative_integer(self.target_revision, "target_revision")
        _require_non_negative_integer(self.current_revision, "current_revision")
        if type(self.state) is not SessionStateV1:
            raise ValueError("state must be a SessionStateV1.")
        if self.state.session_id != self.session_id:
            raise ValueError("state Session ID must equal session_id.")
        if self.state.revision != self.current_revision:
            raise ValueError("state revision must equal current_revision.")
        removed_records = _canonicalize_records(
            self.removed_records,
            "removed_records",
        )
        diagnostics = _canonicalize_diagnostics(self.diagnostics)

        if self.status == "applied":
            if self.expected_revision != self.source_revision:
                raise ValueError("An applied Undo requires the expected source revision.")
            if not 0 <= self.target_revision < self.source_revision:
                raise ValueError("An applied Undo requires an earlier target revision.")
            if self.current_revision != self.target_revision:
                raise ValueError("An applied Undo current revision must equal its target.")
            if len(removed_records) != self.source_revision - self.target_revision:
                raise ValueError("An applied Undo requires the complete removed suffix.")
            _require_contiguous_revisions(
                removed_records,
                first_revision=self.target_revision + 1,
                field_name="removed_records",
            )
            if diagnostics:
                raise ValueError("An applied Undo requires no diagnostics.")
        elif self.status == "unchanged":
            if self.expected_revision != self.source_revision:
                raise ValueError("An unchanged Undo requires the expected source revision.")
            if self.target_revision != self.source_revision:
                raise ValueError("An unchanged Undo targets the source revision.")
            if self.current_revision != self.source_revision:
                raise ValueError("An unchanged Undo preserves the source revision.")
            if removed_records or diagnostics:
                raise ValueError("An unchanged Undo has no removed records or diagnostics.")
        elif self.status == "rejected":
            if self.expected_revision != self.source_revision:
                raise ValueError("A rejected Undo requires the expected source revision.")
            if self.target_revision <= self.source_revision:
                raise ValueError("A rejected Undo target must exceed the source revision.")
            if self.current_revision != self.source_revision:
                raise ValueError("A rejected Undo preserves the source revision.")
            if removed_records:
                raise ValueError("A rejected Undo has no removed records.")
            if not any(
                diagnostic.code == "history_revision_violation"
                and diagnostic.path == "/target_revision"
                and diagnostic.blocks_command
                for diagnostic in diagnostics
            ):
                raise ValueError(
                    "A rejected Undo requires a blocking history_revision_violation "
                    "diagnostic at /target_revision."
                )
        else:
            if self.expected_revision == self.source_revision:
                raise ValueError("An Undo revision conflict requires a mismatched revision.")
            if self.current_revision != self.source_revision:
                raise ValueError("An Undo revision conflict preserves the source revision.")
            if removed_records:
                raise ValueError("An Undo revision conflict has no removed records.")
            _require_conflict_diagnostic(diagnostics)

        object.__setattr__(self, "removed_records", removed_records)
        object.__setattr__(self, "diagnostics", diagnostics)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_history_edit_version": self.session_history_edit_version,
            "status": self.status,
            "session_id": self.session_id,
            "expected_revision": self.expected_revision,
            "source_revision": self.source_revision,
            "target_revision": self.target_revision,
            "current_revision": self.current_revision,
            "state": self.state.to_dict(),
            "removed_records": [record.to_dict() for record in self.removed_records],
            "diagnostics": [diagnostic.to_dict() for diagnostic in self.diagnostics],
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionCommandCorrectionV1:
    """One immutable request to replace exactly one accepted Session Command."""

    session_history_edit_version: int = SESSION_HISTORY_EDIT_VERSION
    expected_revision: int
    target_revision: int
    replacement_command: SessionCommandV1

    def __post_init__(self) -> None:
        if (
            type(self.session_history_edit_version) is not int
            or self.session_history_edit_version != SESSION_HISTORY_EDIT_VERSION
        ):
            raise ValueError(
                "session_history_edit_version must equal "
                f"{SESSION_HISTORY_EDIT_VERSION}."
            )
        _require_non_negative_integer(self.expected_revision, "expected_revision")
        _require_positive_integer(self.target_revision, "target_revision")
        if self.target_revision > self.expected_revision:
            raise ValueError("target_revision must not exceed expected_revision.")
        if not is_session_command_v1(self.replacement_command):
            raise ValueError("replacement_command must be one exact SessionCommandV1.")
        if self.replacement_command.expected_revision != self.target_revision - 1:
            raise ValueError(
                "replacement_command.expected_revision must equal target_revision - 1."
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_history_edit_version": self.session_history_edit_version,
            "expected_revision": self.expected_revision,
            "target_revision": self.target_revision,
            "replacement_command": serialize_session_command_v1(
                self.replacement_command
            ),
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionCorrectionResultV1:
    """One immutable one-command correction and suffix-replay outcome."""

    session_history_edit_version: int = SESSION_HISTORY_EDIT_VERSION
    status: str
    session_id: str
    expected_revision: int
    source_revision: int
    target_revision: int
    current_revision: int
    replacement_command: SessionCommandV1
    state: SessionStateV1
    original_record: SessionCommandRecordV1 | None
    replayed_suffix_records: tuple[SessionCommandRecordV1, ...]
    discarded_suffix_records: tuple[SessionCommandRecordV1, ...]
    failed_original_revision: int | None
    diagnostics: tuple[SessionValidationDiagnosticV1, ...]

    def __post_init__(self) -> None:
        if (
            type(self.session_history_edit_version) is not int
            or self.session_history_edit_version != SESSION_HISTORY_EDIT_VERSION
        ):
            raise ValueError(
                "session_history_edit_version must equal "
                f"{SESSION_HISTORY_EDIT_VERSION}."
            )
        if self.status not in SESSION_CORRECTION_STATUSES:
            raise ValueError(
                f"status must be one of {list(SESSION_CORRECTION_STATUSES)}."
            )
        _require_identifier(self.session_id, "session_id")
        _require_non_negative_integer(self.expected_revision, "expected_revision")
        _require_non_negative_integer(self.source_revision, "source_revision")
        _require_positive_integer(self.target_revision, "target_revision")
        _require_non_negative_integer(self.current_revision, "current_revision")
        if self.target_revision > self.expected_revision:
            raise ValueError("target_revision must not exceed expected_revision.")
        if not is_session_command_v1(self.replacement_command):
            raise ValueError("replacement_command must be one exact SessionCommandV1.")
        if self.replacement_command.expected_revision != self.target_revision - 1:
            raise ValueError(
                "replacement_command.expected_revision must equal target_revision - 1."
            )
        if type(self.state) is not SessionStateV1:
            raise ValueError("state must be a SessionStateV1.")
        if self.state.session_id != self.session_id:
            raise ValueError("state Session ID must equal session_id.")
        if self.state.revision != self.current_revision:
            raise ValueError("state revision must equal current_revision.")
        if (
            self.original_record is not None
            and type(self.original_record) is not SessionCommandRecordV1
        ):
            raise ValueError("original_record must be a SessionCommandRecordV1 or null.")
        replayed = _canonicalize_records(
            self.replayed_suffix_records,
            "replayed_suffix_records",
        )
        discarded = _canonicalize_records(
            self.discarded_suffix_records,
            "discarded_suffix_records",
        )
        if self.failed_original_revision is not None:
            _require_positive_integer(
                self.failed_original_revision,
                "failed_original_revision",
            )
        diagnostics = _canonicalize_diagnostics(self.diagnostics)

        if self.status == "revision_conflict":
            if self.expected_revision == self.source_revision:
                raise ValueError(
                    "A Correction revision conflict requires a mismatched revision."
                )
            if self.current_revision != self.source_revision:
                raise ValueError(
                    "A Correction revision conflict preserves the source revision."
                )
            if self.original_record is not None or replayed or discarded:
                raise ValueError(
                    "A Correction revision conflict has no source-record reports."
                )
            if self.failed_original_revision is not None:
                raise ValueError(
                    "A Correction revision conflict has no failed original revision."
                )
            _require_conflict_diagnostic(diagnostics)
        else:
            if self.expected_revision != self.source_revision:
                raise ValueError(
                    "A non-conflict Correction requires the expected source revision."
                )
            if self.target_revision > self.source_revision:
                raise ValueError("A non-conflict Correction target must exist in the source.")
            if (
                self.original_record is None
                or self.original_record.revision != self.target_revision
            ):
                raise ValueError(
                    "A non-conflict Correction requires the exact target original_record."
                )

            if self.status == "unchanged":
                if self.current_revision != self.source_revision:
                    raise ValueError("An unchanged Correction preserves the revision.")
                if self.original_record.command != self.replacement_command:
                    raise ValueError(
                        "An unchanged Correction replacement must equal the original Command."
                    )
                if replayed or discarded or self.failed_original_revision is not None:
                    raise ValueError(
                        "An unchanged Correction has no suffix or failed revision."
                    )
                if diagnostics:
                    raise ValueError("An unchanged Correction has no diagnostics.")
                if self.state.command_log[self.target_revision - 1] != self.original_record:
                    raise ValueError("An unchanged Correction must retain the original record.")
            elif self.status == "rejected":
                if self.current_revision != self.source_revision:
                    raise ValueError("A rejected Correction preserves the revision.")
                if self.original_record.command == self.replacement_command:
                    raise ValueError("A rejected Correction cannot be an exact no-op.")
                if replayed or discarded:
                    raise ValueError("A rejected Correction evaluates no suffix records.")
                if self.failed_original_revision != self.target_revision:
                    raise ValueError(
                        "A rejected Correction fails at its target revision."
                    )
                if not diagnostics or any(
                    not diagnostic.blocks_command for diagnostic in diagnostics
                ):
                    raise ValueError(
                        "A rejected Correction requires only blocking diagnostics."
                    )
                if self.state.command_log[self.target_revision - 1] != self.original_record:
                    raise ValueError("A rejected Correction must retain the original record.")
            elif self.status == "applied":
                if self.current_revision != self.source_revision:
                    raise ValueError(
                        "An applied Correction preserves the complete source length."
                    )
                if self.original_record.command == self.replacement_command:
                    raise ValueError("An applied Correction cannot be an exact no-op.")
                if (
                    self.state.command_log[self.target_revision - 1].command
                    != self.replacement_command
                ):
                    raise ValueError(
                        "An applied Correction State must contain the replacement at target."
                    )
                if len(replayed) != self.source_revision - self.target_revision:
                    raise ValueError(
                        "An applied Correction must report the complete replayed suffix."
                    )
                _require_contiguous_revisions(
                    replayed,
                    first_revision=self.target_revision + 1,
                    field_name="replayed_suffix_records",
                )
                if self.state.command_log[self.target_revision :] != replayed:
                    raise ValueError(
                        "An applied Correction must retain every replayed suffix record."
                    )
                if discarded or self.failed_original_revision is not None or diagnostics:
                    raise ValueError(
                        "An applied Correction has no discarded suffix, failure, or diagnostics."
                    )
            else:
                if not self.target_revision <= self.current_revision < self.source_revision:
                    raise ValueError(
                        "A partial Correction ends between its target and source revision."
                    )
                if self.original_record.command == self.replacement_command:
                    raise ValueError("A partial Correction cannot be an exact no-op.")
                if (
                    self.state.command_log[self.target_revision - 1].command
                    != self.replacement_command
                ):
                    raise ValueError(
                        "A partial Correction State must contain the replacement at target."
                    )
                if len(replayed) != self.current_revision - self.target_revision:
                    raise ValueError(
                        "A partial Correction replay report must reach current_revision."
                    )
                _require_contiguous_revisions(
                    replayed,
                    first_revision=self.target_revision + 1,
                    field_name="replayed_suffix_records",
                )
                if self.state.command_log[self.target_revision :] != replayed:
                    raise ValueError(
                        "A partial Correction State must retain its replayed suffix."
                    )
                if len(discarded) != self.source_revision - self.current_revision:
                    raise ValueError(
                        "A partial Correction must report the complete discarded suffix."
                    )
                _require_contiguous_revisions(
                    discarded,
                    first_revision=self.current_revision + 1,
                    field_name="discarded_suffix_records",
                )
                if self.failed_original_revision != self.current_revision + 1:
                    raise ValueError(
                        "A partial Correction fails at the first discarded revision."
                    )
                if not diagnostics or any(
                    not diagnostic.blocks_command for diagnostic in diagnostics
                ):
                    raise ValueError(
                        "A partial Correction requires only first-rejection blockers."
                    )

        object.__setattr__(self, "replayed_suffix_records", replayed)
        object.__setattr__(self, "discarded_suffix_records", discarded)
        object.__setattr__(self, "diagnostics", diagnostics)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_history_edit_version": self.session_history_edit_version,
            "status": self.status,
            "session_id": self.session_id,
            "expected_revision": self.expected_revision,
            "source_revision": self.source_revision,
            "target_revision": self.target_revision,
            "current_revision": self.current_revision,
            "replacement_command": serialize_session_command_v1(
                self.replacement_command
            ),
            "state": self.state.to_dict(),
            "original_record": (
                None if self.original_record is None else self.original_record.to_dict()
            ),
            "replayed_suffix_records": [
                record.to_dict() for record in self.replayed_suffix_records
            ],
            "discarded_suffix_records": [
                record.to_dict() for record in self.discarded_suffix_records
            ],
            "failed_original_revision": self.failed_original_revision,
            "diagnostics": [diagnostic.to_dict() for diagnostic in self.diagnostics],
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionCheckpointLineageV1:
    """One derived relationship between a State and frozen Decision Checkpoint."""

    session_checkpoint_lineage_version: int = SESSION_CHECKPOINT_LINEAGE_VERSION
    relationship: str
    session_id: str
    checkpoint_revision: int
    state_revision: int

    def __post_init__(self) -> None:
        if (
            type(self.session_checkpoint_lineage_version) is not int
            or self.session_checkpoint_lineage_version
            != SESSION_CHECKPOINT_LINEAGE_VERSION
        ):
            raise ValueError(
                "session_checkpoint_lineage_version must equal "
                f"{SESSION_CHECKPOINT_LINEAGE_VERSION}."
            )
        if self.relationship not in SESSION_CHECKPOINT_RELATIONSHIPS:
            raise ValueError(
                "relationship must be one of "
                f"{list(SESSION_CHECKPOINT_RELATIONSHIPS)}."
            )
        _require_identifier(self.session_id, "session_id")
        _require_non_negative_integer(self.checkpoint_revision, "checkpoint_revision")
        _require_non_negative_integer(self.state_revision, "state_revision")

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_checkpoint_lineage_version": (
                self.session_checkpoint_lineage_version
            ),
            "relationship": self.relationship,
            "session_id": self.session_id,
            "checkpoint_revision": self.checkpoint_revision,
            "state_revision": self.state_revision,
        }
