from __future__ import annotations

import errno
import json
import os
import stat
import tempfile
from collections.abc import Mapping
from pathlib import Path

from skatmind.errors import SkatMindInvariantError, SkatMindValidationError
from skatmind.match_workspace_persistence_codec import (
    build_match_workspace_persistence_document_v1,
    resume_match_workspace_document_v1,
)
from skatmind.match_workspace_persistence_contracts import (
    MATCH_WORKSPACE_PERSISTENCE_ENCODING,
    MatchWorkspacePersistenceDocumentV1,
    MatchWorkspaceResumeResultV1,
    MatchWorkspaceWriteResultV1,
)

_UTF8_BOM = b"\xef\xbb\xbf"


def _require_optional_fingerprint(value: object) -> str | None:
    if value is None:
        return None
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(
            "expected_content_fingerprint must be null or one lowercase SHA-256 "
            "hexadecimal value."
        )
    return value


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise SkatMindValidationError(
                f"Duplicate JSON object key {key!r} is not allowed.",
                path="",
            )
        result[key] = value
    return result


def _reject_non_finite_constant(value: str) -> object:
    raise SkatMindValidationError(
        f"Non-finite JSON number {value!r} is not allowed.",
        path="",
    )


def _decode_persistence_json(raw_bytes: bytes) -> Mapping[str, object]:
    if raw_bytes.startswith(_UTF8_BOM):
        raise SkatMindValidationError(
            "Match Workspace persistence files must use UTF-8 without a BOM.",
            path="",
        )
    try:
        text = raw_bytes.decode(MATCH_WORKSPACE_PERSISTENCE_ENCODING, errors="strict")
    except UnicodeDecodeError as error:
        raise SkatMindValidationError(
            "Match Workspace persistence file is not valid UTF-8.",
            path="",
        ) from error
    try:
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_non_finite_constant,
        )
    except SkatMindValidationError:
        raise
    except json.JSONDecodeError as error:
        raise SkatMindValidationError(
            f"Match Workspace persistence file is not valid JSON: {error.msg}.",
            path="",
        ) from error
    if not isinstance(value, Mapping):
        raise SkatMindValidationError(
            "Match Workspace persistence document root must be a JSON object.",
            path="",
        )
    return value


def _read_regular_file_bytes(file_path: Path) -> bytes:
    with file_path.open("rb") as file:
        mode = os.fstat(file.fileno()).st_mode
        if not stat.S_ISREG(mode):
            raise OSError(
                errno.EINVAL,
                "Match Workspace persistence path must identify a regular file.",
                os.fspath(file_path),
            )
        return file.read()


def load_match_workspace_file_v1(
    file_path: str | os.PathLike[str],
) -> MatchWorkspaceResumeResultV1:
    """Loads and strictly resumes one private Match Workspace file."""
    path = Path(file_path)
    raw_bytes = _read_regular_file_bytes(path)
    document = _decode_persistence_json(raw_bytes)
    return resume_match_workspace_document_v1(document)


def _build_match_workspace_file_bytes_v1(
    document: MatchWorkspacePersistenceDocumentV1,
) -> bytes:
    try:
        text = json.dumps(
            document.to_dict(),
            allow_nan=False,
            ensure_ascii=True,
            indent=2,
        )
    except (TypeError, ValueError) as error:
        raise SkatMindInvariantError(
            "Match Workspace persistence document cannot be serialized as finite JSON.",
            path="",
        ) from error
    return f"{text}\n".encode(MATCH_WORKSPACE_PERSISTENCE_ENCODING)


def _validate_requested_document(
    document: MatchWorkspacePersistenceDocumentV1,
) -> MatchWorkspacePersistenceDocumentV1:
    if type(document) is not MatchWorkspacePersistenceDocumentV1:
        raise ValueError("document must be a MatchWorkspacePersistenceDocumentV1.")
    try:
        resumed = resume_match_workspace_document_v1(document.to_dict())
    except SkatMindValidationError as error:
        raise SkatMindInvariantError(
            "Internally supplied Match Workspace persistence document is inconsistent.",
            path=error.path,
        ) from error
    if resumed.document != document:
        raise SkatMindInvariantError(
            "Internally supplied Match Workspace persistence document is not canonical.",
            path="",
        )
    return build_match_workspace_persistence_document_v1(
        resumed.document.workspace
    )


def _load_existing_target(
    file_path: Path,
) -> tuple[bool, MatchWorkspacePersistenceDocumentV1 | None]:
    try:
        resumed = load_match_workspace_file_v1(file_path)
    except FileNotFoundError:
        return False, None
    return True, resumed.document


def _write_result(
    *,
    status: str,
    document: MatchWorkspacePersistenceDocumentV1,
    expected_content_fingerprint: str | None,
    existing_content_fingerprint: str | None,
) -> MatchWorkspaceWriteResultV1:
    return MatchWorkspaceWriteResultV1(
        status=status,
        match_id=document.workspace.match_definition.match_id,
        revision=document.workspace.revision,
        expected_content_fingerprint=expected_content_fingerprint,
        existing_content_fingerprint=existing_content_fingerprint,
        requested_content_fingerprint=document.content_fingerprint,
    )


def _require_existing_parent_directory(file_path: Path) -> Path:
    parent = file_path.parent
    mode = os.stat(parent).st_mode
    if not stat.S_ISDIR(mode):
        raise NotADirectoryError(
            errno.ENOTDIR,
            "Match Workspace persistence parent must be an existing directory.",
            os.fspath(parent),
        )
    return parent


def _best_effort_fsync_directory(directory: Path) -> None:
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    directory_fd: int | None = None
    try:
        directory_fd = os.open(directory, flags)
        os.fsync(directory_fd)
    except OSError:
        pass
    finally:
        if directory_fd is not None:
            try:
                os.close(directory_fd)
            except OSError:
                pass


def _pre_replace_existing_fingerprint(
    file_path: Path,
) -> tuple[bool, str | None]:
    exists, document = _load_existing_target(file_path)
    return exists, None if document is None else document.content_fingerprint


def _write_complete(temporary_file, persisted_bytes: bytes) -> None:
    offset = 0
    while offset < len(persisted_bytes):
        written = temporary_file.write(persisted_bytes[offset:])
        if type(written) is not int or written <= 0:
            raise OSError("Match Workspace persistence temporary write was incomplete.")
        offset += written


def save_match_workspace_file_v1(
    file_path: str | os.PathLike[str],
    document: MatchWorkspacePersistenceDocumentV1,
    *,
    expected_content_fingerprint: str | None,
) -> MatchWorkspaceWriteResultV1:
    """Optimistically saves one private Workspace through atomic replacement."""
    requested = _validate_requested_document(document)
    expected = _require_optional_fingerprint(expected_content_fingerprint)
    path = Path(file_path)

    target_exists, existing_document = _load_existing_target(path)
    existing = None if existing_document is None else existing_document.content_fingerprint
    if target_exists != (existing_document is not None):
        raise SkatMindInvariantError(
            "Existing Match Workspace persistence target observation is inconsistent.",
            path="",
        )
    if expected != existing:
        return _write_result(
            status="conflict",
            document=requested,
            expected_content_fingerprint=expected,
            existing_content_fingerprint=existing,
        )
    if target_exists and existing == requested.content_fingerprint:
        return _write_result(
            status="unchanged",
            document=requested,
            expected_content_fingerprint=expected,
            existing_content_fingerprint=existing,
        )

    parent = _require_existing_parent_directory(path)
    persisted_bytes = _build_match_workspace_file_bytes_v1(requested)
    file_descriptor: int | None = None
    temporary_path: Path | None = None
    try:
        file_descriptor, raw_temporary_path = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=parent,
        )
        temporary_path = Path(raw_temporary_path)
        with os.fdopen(file_descriptor, "wb") as temporary_file:
            file_descriptor = None
            _write_complete(temporary_file, persisted_bytes)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())

        current_exists, current = _pre_replace_existing_fingerprint(path)
        if current_exists != target_exists or current != expected:
            return _write_result(
                status="conflict",
                document=requested,
                expected_content_fingerprint=expected,
                existing_content_fingerprint=current,
            )

        os.replace(temporary_path, path)
        temporary_path = None
        _best_effort_fsync_directory(parent)
        return _write_result(
            status="saved",
            document=requested,
            expected_content_fingerprint=expected,
            existing_content_fingerprint=current,
        )
    finally:
        if file_descriptor is not None:
            os.close(file_descriptor)
        if temporary_path is not None:
            try:
                os.unlink(temporary_path)
            except FileNotFoundError:
                pass
