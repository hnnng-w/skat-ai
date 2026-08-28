from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from skatmind.session_contracts import SessionStateV1
from skatmind.session_decision_checkpoint import SessionDecisionCheckpointV1
from skatmind.session_history_contracts import SessionCheckpointLineageV1

SESSION_PERSISTENCE_VERSION = 1
SESSION_PERSISTENCE_DOCUMENT_KIND = "skatmind_session"
LEGACY_SESSION_PERSISTENCE_DOCUMENT_KIND = "skat_ai_session"
SESSION_PERSISTENCE_SUPPORTED_DOCUMENT_KINDS = (
    SESSION_PERSISTENCE_DOCUMENT_KIND,
    LEGACY_SESSION_PERSISTENCE_DOCUMENT_KIND,
)

SESSION_PERSISTENCE_STATE_POLICY = "authoritative_accepted_log_state"
SESSION_PERSISTENCE_CHECKPOINT_POLICY = "caller_supplied_frozen_checkpoints"
SESSION_PERSISTENCE_STATE_FINGERPRINT_POLICY = "sha256_canonical_session_state_v1"
SESSION_PERSISTENCE_CONTENT_FINGERPRINT_POLICY = (
    "sha256_canonical_document_without_content_fingerprint"
)
SESSION_PERSISTENCE_CONFLICT_POLICY = "expected_content_fingerprint_compare_and_swap"
SESSION_PERSISTENCE_WRITE_POLICY = "same_directory_temp_file_atomic_replace"
SESSION_PERSISTENCE_RESUME_POLICY = "strict_parse_fingerprint_replay_and_lineage"
SESSION_PERSISTENCE_ENCODING = "utf-8"

SESSION_PERSISTENCE_WRITE_STATUSES = (
    "saved",
    "unchanged",
    "conflict",
)


def _require_identifier(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{field_name} must be a non-empty, non-padded string.")
    return value


def _require_non_negative_integer(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer.")
    return value


def _require_fingerprint(
    value: object,
    field_name: str,
    *,
    allow_none: bool = False,
) -> str | None:
    if value is None and allow_none:
        return None
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        nullable = " or null" if allow_none else ""
        raise ValueError(f"{field_name} must be a lowercase SHA-256 hexadecimal value{nullable}.")
    return value


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode(SESSION_PERSISTENCE_ENCODING)


def _checkpoint_bytes(checkpoint: SessionDecisionCheckpointV1) -> bytes:
    return _canonical_json_bytes(checkpoint.to_dict())


def _checkpoint_sort_key(
    checkpoint: SessionDecisionCheckpointV1,
) -> tuple[int, int, int, int, bytes, bytes]:
    return (
        checkpoint.source_revision,
        checkpoint.decision_index,
        checkpoint.trick_number,
        checkpoint.play_index,
        _canonical_json_bytes(checkpoint.request.to_dict()),
        _checkpoint_bytes(checkpoint),
    )


def _canonicalize_checkpoints(
    value: object,
    *,
    session_id: str,
) -> tuple[SessionDecisionCheckpointV1, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        raise ValueError("decision_checkpoints must be an ordered array.")
    checkpoints = tuple(value)
    if any(type(checkpoint) is not SessionDecisionCheckpointV1 for checkpoint in checkpoints):
        raise ValueError(
            "decision_checkpoints must contain only SessionDecisionCheckpointV1 values."
        )
    if any(checkpoint.session_id != session_id for checkpoint in checkpoints):
        raise ValueError("Every Decision Checkpoint must match the Session State ID.")
    checkpoint_bytes = tuple(_checkpoint_bytes(checkpoint) for checkpoint in checkpoints)
    if len(checkpoint_bytes) != len(set(checkpoint_bytes)):
        raise ValueError("Exact duplicate Decision Checkpoints are not allowed.")
    return tuple(sorted(checkpoints, key=_checkpoint_sort_key))


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionPersistenceDocumentV1:
    """One immutable private Session persistence document."""

    session_persistence_version: int = SESSION_PERSISTENCE_VERSION
    document_kind: str = SESSION_PERSISTENCE_DOCUMENT_KIND
    state_fingerprint: str
    content_fingerprint: str
    state: SessionStateV1
    decision_checkpoints: tuple[SessionDecisionCheckpointV1, ...]

    def __post_init__(self) -> None:
        self._validate_structure()
        from skatmind.session_persistence_codec import (
            _validate_session_persistence_document_fingerprints_v1,
        )

        _validate_session_persistence_document_fingerprints_v1(self)

    def _validate_structure(self) -> None:
        if (
            type(self.session_persistence_version) is not int
            or self.session_persistence_version != SESSION_PERSISTENCE_VERSION
        ):
            raise ValueError(
                f"session_persistence_version must equal {SESSION_PERSISTENCE_VERSION}."
            )
        if self.document_kind not in SESSION_PERSISTENCE_SUPPORTED_DOCUMENT_KINDS:
            raise ValueError(
                "document_kind must be one supported Session persistence kind."
            )
        _require_fingerprint(self.state_fingerprint, "state_fingerprint")
        _require_fingerprint(self.content_fingerprint, "content_fingerprint")
        if type(self.state) is not SessionStateV1:
            raise ValueError("state must be a SessionStateV1.")
        checkpoints = _canonicalize_checkpoints(
            self.decision_checkpoints,
            session_id=self.state.session_id,
        )
        object.__setattr__(self, "decision_checkpoints", checkpoints)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_persistence_version": self.session_persistence_version,
            "document_kind": self.document_kind,
            "state_fingerprint": self.state_fingerprint,
            "content_fingerprint": self.content_fingerprint,
            "state": self.state.to_dict(),
            "decision_checkpoints": [
                checkpoint.to_dict() for checkpoint in self.decision_checkpoints
            ],
        }


def _build_verified_session_persistence_document_v1(
    *,
    session_persistence_version: int = SESSION_PERSISTENCE_VERSION,
    document_kind: str = SESSION_PERSISTENCE_DOCUMENT_KIND,
    state_fingerprint: str,
    content_fingerprint: str,
    state: SessionStateV1,
    decision_checkpoints: tuple[SessionDecisionCheckpointV1, ...],
) -> SessionPersistenceDocumentV1:
    document = object.__new__(SessionPersistenceDocumentV1)
    object.__setattr__(
        document,
        "session_persistence_version",
        session_persistence_version,
    )
    object.__setattr__(document, "document_kind", document_kind)
    object.__setattr__(document, "state_fingerprint", state_fingerprint)
    object.__setattr__(document, "content_fingerprint", content_fingerprint)
    object.__setattr__(document, "state", state)
    object.__setattr__(document, "decision_checkpoints", decision_checkpoints)
    document._validate_structure()
    return document


def _canonicalize_lineage(
    value: object,
    *,
    document: SessionPersistenceDocumentV1,
) -> tuple[SessionCheckpointLineageV1, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        raise ValueError("checkpoint_lineage must be an ordered array.")
    lineage = tuple(value)
    if len(lineage) != len(document.decision_checkpoints):
        raise ValueError(
            "checkpoint_lineage must correspond one-for-one with Decision Checkpoints."
        )
    if any(type(item) is not SessionCheckpointLineageV1 for item in lineage):
        raise ValueError("checkpoint_lineage must contain only SessionCheckpointLineageV1 values.")
    for checkpoint, item in zip(document.decision_checkpoints, lineage, strict=True):
        if item.session_id != document.state.session_id:
            raise ValueError("Checkpoint Lineage Session IDs must match the document.")
        if item.checkpoint_revision != checkpoint.source_revision:
            raise ValueError("Checkpoint Lineage revisions must match Decision Checkpoint order.")
        if item.state_revision != document.state.revision:
            raise ValueError("Checkpoint Lineage State revisions must match the document.")
        if item.relationship == "current" and checkpoint.source_revision != item.state_revision:
            raise ValueError("A current Checkpoint must equal the State revision.")
        if item.relationship == "ancestor" and checkpoint.source_revision >= item.state_revision:
            raise ValueError("An ancestor Checkpoint must precede the State revision.")
        if item.relationship == "future" and checkpoint.source_revision <= item.state_revision:
            raise ValueError("A future Checkpoint must follow the State revision.")
        if item.relationship == "diverged" and checkpoint.source_revision > item.state_revision:
            raise ValueError("A diverged Checkpoint cannot follow the State revision.")
    return lineage


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionResumeResultV1:
    """One strict in-memory Session Resume result with derived Checkpoint Lineage."""

    session_persistence_version: int = SESSION_PERSISTENCE_VERSION
    document: SessionPersistenceDocumentV1
    checkpoint_lineage: tuple[SessionCheckpointLineageV1, ...]

    def __post_init__(self) -> None:
        if (
            type(self.session_persistence_version) is not int
            or self.session_persistence_version != SESSION_PERSISTENCE_VERSION
        ):
            raise ValueError(
                f"session_persistence_version must equal {SESSION_PERSISTENCE_VERSION}."
            )
        if type(self.document) is not SessionPersistenceDocumentV1:
            raise ValueError("document must be a SessionPersistenceDocumentV1.")
        lineage = _canonicalize_lineage(
            self.checkpoint_lineage,
            document=self.document,
        )
        object.__setattr__(self, "checkpoint_lineage", lineage)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_persistence_version": self.session_persistence_version,
            "document": self.document.to_dict(),
            "checkpoint_lineage": [item.to_dict() for item in self.checkpoint_lineage],
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionPersistenceWriteResultV1:
    """One normal saved, unchanged, or optimistic-conflict outcome."""

    session_persistence_version: int = SESSION_PERSISTENCE_VERSION
    status: str
    session_id: str
    revision: int
    expected_content_fingerprint: str | None
    existing_content_fingerprint: str | None
    requested_content_fingerprint: str

    def __post_init__(self) -> None:
        if (
            type(self.session_persistence_version) is not int
            or self.session_persistence_version != SESSION_PERSISTENCE_VERSION
        ):
            raise ValueError(
                f"session_persistence_version must equal {SESSION_PERSISTENCE_VERSION}."
            )
        if self.status not in SESSION_PERSISTENCE_WRITE_STATUSES:
            raise ValueError(f"status must be one of {list(SESSION_PERSISTENCE_WRITE_STATUSES)}.")
        _require_identifier(self.session_id, "session_id")
        _require_non_negative_integer(self.revision, "revision")
        _require_fingerprint(
            self.expected_content_fingerprint,
            "expected_content_fingerprint",
            allow_none=True,
        )
        _require_fingerprint(
            self.existing_content_fingerprint,
            "existing_content_fingerprint",
            allow_none=True,
        )
        _require_fingerprint(
            self.requested_content_fingerprint,
            "requested_content_fingerprint",
        )

        if self.status == "saved":
            if self.expected_content_fingerprint != self.existing_content_fingerprint:
                raise ValueError("A saved Result requires the expected existing fingerprint.")
            if (
                self.existing_content_fingerprint is not None
                and self.requested_content_fingerprint == self.existing_content_fingerprint
            ):
                raise ValueError("Equal existing and requested content is unchanged.")
        elif self.status == "unchanged":
            if (
                self.expected_content_fingerprint is None
                or self.expected_content_fingerprint != self.existing_content_fingerprint
                or self.expected_content_fingerprint != self.requested_content_fingerprint
            ):
                raise ValueError("An unchanged Result requires three equal non-null fingerprints.")
        elif self.expected_content_fingerprint == self.existing_content_fingerprint:
            raise ValueError(
                "A conflict Result requires different expected and existing fingerprints."
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_persistence_version": self.session_persistence_version,
            "status": self.status,
            "session_id": self.session_id,
            "revision": self.revision,
            "expected_content_fingerprint": self.expected_content_fingerprint,
            "existing_content_fingerprint": self.existing_content_fingerprint,
            "requested_content_fingerprint": self.requested_content_fingerprint,
        }
