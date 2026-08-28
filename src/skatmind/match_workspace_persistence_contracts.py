from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Final

from skatmind.match_workspace_contracts import MatchWorkspaceV1, validate_match_workspace_v1
from skatmind.match_workspace_progress import MatchWorkspaceProgressV1

MATCH_WORKSPACE_PERSISTENCE_VERSION = 1
MATCH_WORKSPACE_DOCUMENT_KIND = "skatmind_match_workspace"
LEGACY_MATCH_WORKSPACE_DOCUMENT_KIND = "skat_ai_match_workspace"
MATCH_WORKSPACE_SUPPORTED_DOCUMENT_KINDS = (
    MATCH_WORKSPACE_DOCUMENT_KIND,
    LEGACY_MATCH_WORKSPACE_DOCUMENT_KIND,
)

MATCH_WORKSPACE_STATE_FINGERPRINT_POLICY = "sha256_canonical_match_workspace_v1"
MATCH_WORKSPACE_CONTENT_FINGERPRINT_POLICY = (
    "sha256_canonical_document_without_content_fingerprint"
)
MATCH_WORKSPACE_CONFLICT_POLICY = "expected_content_fingerprint_compare_and_swap"
MATCH_WORKSPACE_WRITE_POLICY = "same_directory_temp_file_atomic_replace"
MATCH_WORKSPACE_RESUME_POLICY = "strict_parse_fingerprint_validate_and_progress"

MATCH_WORKSPACE_PERSISTENCE_ENCODING = "utf-8"
MATCH_WORKSPACE_WRITE_STATUSES: Final[tuple[str, ...]] = (
    "saved",
    "unchanged",
    "conflict",
)


def _require_non_negative_integer(value: object, field_name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer.")
    return value


def _require_identifier(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{field_name} must be a non-empty, non-padded string.")
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
        raise ValueError(
            f"{field_name} must be a lowercase SHA-256 hexadecimal value{nullable}."
        )
    return value


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode(MATCH_WORKSPACE_PERSISTENCE_ENCODING)


@dataclass(frozen=True, slots=True, kw_only=True)
class MatchWorkspacePersistenceDocumentV1:
    """One immutable private Match Workspace persistence document."""

    match_workspace_persistence_version: int = MATCH_WORKSPACE_PERSISTENCE_VERSION
    document_kind: str = MATCH_WORKSPACE_DOCUMENT_KIND
    workspace_fingerprint: str
    content_fingerprint: str
    workspace: MatchWorkspaceV1

    def __post_init__(self) -> None:
        self._validate_structure(validate_workspace=True)
        from skatmind.match_workspace_persistence_codec import (
            _validate_match_workspace_persistence_document_fingerprints_v1,
        )

        _validate_match_workspace_persistence_document_fingerprints_v1(self)

    def _validate_structure(self, *, validate_workspace: bool) -> None:
        if (
            type(self.match_workspace_persistence_version) is not int
            or self.match_workspace_persistence_version
            != MATCH_WORKSPACE_PERSISTENCE_VERSION
        ):
            raise ValueError(
                "match_workspace_persistence_version must equal "
                f"{MATCH_WORKSPACE_PERSISTENCE_VERSION}."
            )
        if self.document_kind not in MATCH_WORKSPACE_SUPPORTED_DOCUMENT_KINDS:
            raise ValueError(
                "document_kind must be one supported Match Workspace persistence kind."
            )
        _require_fingerprint(self.workspace_fingerprint, "workspace_fingerprint")
        _require_fingerprint(self.content_fingerprint, "content_fingerprint")
        if type(self.workspace) is not MatchWorkspaceV1:
            raise ValueError("workspace must be a MatchWorkspaceV1.")
        if validate_workspace:
            validate_match_workspace_v1(self.workspace)

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_workspace_persistence_version": (
                self.match_workspace_persistence_version
            ),
            "document_kind": self.document_kind,
            "workspace_fingerprint": self.workspace_fingerprint,
            "content_fingerprint": self.content_fingerprint,
            "workspace": self.workspace.to_dict(),
        }


def _build_verified_match_workspace_persistence_document_v1(
    *,
    match_workspace_persistence_version: int = MATCH_WORKSPACE_PERSISTENCE_VERSION,
    document_kind: str = MATCH_WORKSPACE_DOCUMENT_KIND,
    workspace_fingerprint: str,
    content_fingerprint: str,
    workspace: MatchWorkspaceV1,
) -> MatchWorkspacePersistenceDocumentV1:
    document = object.__new__(MatchWorkspacePersistenceDocumentV1)
    object.__setattr__(
        document,
        "match_workspace_persistence_version",
        match_workspace_persistence_version,
    )
    object.__setattr__(document, "document_kind", document_kind)
    object.__setattr__(document, "workspace_fingerprint", workspace_fingerprint)
    object.__setattr__(document, "content_fingerprint", content_fingerprint)
    object.__setattr__(document, "workspace", workspace)
    document._validate_structure(validate_workspace=False)
    return document


@dataclass(frozen=True, slots=True, kw_only=True)
class MatchWorkspaceResumeResultV1:
    """One strict in-memory Resume result with freshly derived Progress."""

    match_workspace_persistence_version: int = MATCH_WORKSPACE_PERSISTENCE_VERSION
    document: MatchWorkspacePersistenceDocumentV1
    progress: MatchWorkspaceProgressV1

    def __post_init__(self) -> None:
        if (
            type(self.match_workspace_persistence_version) is not int
            or self.match_workspace_persistence_version
            != MATCH_WORKSPACE_PERSISTENCE_VERSION
        ):
            raise ValueError(
                "match_workspace_persistence_version must equal "
                f"{MATCH_WORKSPACE_PERSISTENCE_VERSION}."
            )
        if type(self.document) is not MatchWorkspacePersistenceDocumentV1:
            raise ValueError("document must be a MatchWorkspacePersistenceDocumentV1.")
        if type(self.progress) is not MatchWorkspaceProgressV1:
            raise ValueError("progress must be a MatchWorkspaceProgressV1.")
        if self.progress.revision != self.document.workspace.revision:
            raise ValueError("Progress revision must equal the Workspace revision.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_workspace_persistence_version": (
                self.match_workspace_persistence_version
            ),
            "document": self.document.to_dict(),
            "progress": self.progress.to_dict(),
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class MatchWorkspaceWriteResultV1:
    """One normal saved, unchanged, or optimistic-conflict outcome."""

    match_workspace_persistence_version: int = MATCH_WORKSPACE_PERSISTENCE_VERSION
    status: str
    match_id: str
    revision: int
    expected_content_fingerprint: str | None
    existing_content_fingerprint: str | None
    requested_content_fingerprint: str

    def __post_init__(self) -> None:
        if (
            type(self.match_workspace_persistence_version) is not int
            or self.match_workspace_persistence_version
            != MATCH_WORKSPACE_PERSISTENCE_VERSION
        ):
            raise ValueError(
                "match_workspace_persistence_version must equal "
                f"{MATCH_WORKSPACE_PERSISTENCE_VERSION}."
            )
        if self.status not in MATCH_WORKSPACE_WRITE_STATUSES:
            raise ValueError(
                f"status must be one of {list(MATCH_WORKSPACE_WRITE_STATUSES)}."
            )
        _require_identifier(self.match_id, "match_id")
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
                and self.requested_content_fingerprint
                == self.existing_content_fingerprint
            ):
                raise ValueError("Equal existing and requested content is unchanged.")
        elif self.status == "unchanged":
            if (
                self.expected_content_fingerprint is None
                or self.expected_content_fingerprint
                != self.existing_content_fingerprint
                or self.expected_content_fingerprint
                != self.requested_content_fingerprint
            ):
                raise ValueError(
                    "An unchanged Result requires three equal non-null fingerprints."
                )
        elif self.expected_content_fingerprint == self.existing_content_fingerprint:
            raise ValueError(
                "A conflict Result requires different expected and existing fingerprints."
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_workspace_persistence_version": (
                self.match_workspace_persistence_version
            ),
            "status": self.status,
            "match_id": self.match_id,
            "revision": self.revision,
            "expected_content_fingerprint": self.expected_content_fingerprint,
            "existing_content_fingerprint": self.existing_content_fingerprint,
            "requested_content_fingerprint": self.requested_content_fingerprint,
        }
