from __future__ import annotations

import errno
import json
import os
import stat
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from skatmind.errors import SkatMindInvariantError, SkatMindValidationError
from skatmind.session_persistence_codec import (
    build_session_persistence_document_v1,
    resume_session_document_v1,
)
from skatmind.session_persistence_contracts import (
    SESSION_PERSISTENCE_ENCODING,
    SessionPersistenceDocumentV1,
    SessionPersistenceWriteResultV1,
    SessionResumeResultV1,
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
            "expected_content_fingerprint must be null or one lowercase SHA-256 hexadecimal value."
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
            "Session persistence files must use UTF-8 without a BOM.",
            path="",
        )
    try:
        text = raw_bytes.decode(SESSION_PERSISTENCE_ENCODING, errors="strict")
    except UnicodeDecodeError as error:
        raise SkatMindValidationError(
            "Session persistence file is not valid UTF-8.",
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
            f"Session persistence file is not valid JSON: {error.msg}.",
            path="",
        ) from error
    if not isinstance(value, Mapping):
        raise SkatMindValidationError(
            "Session persistence document root must be a JSON object.",
            path="",
        )
    return value


def _read_regular_file_bytes(file_path: Path) -> bytes:
    with file_path.open("rb") as file:
        mode = os.fstat(file.fileno()).st_mode
        if not stat.S_ISREG(mode):
            raise OSError(
                errno.EINVAL,
                "Session persistence path must identify a regular file.",
                os.fspath(file_path),
            )
        return file.read()


def load_session_persistence_file_v1(
    file_path: str | os.PathLike[str],
) -> SessionResumeResultV1:
    """Loads and strictly resumes one private canonical Session file."""
    path = Path(file_path)
    raw_bytes = _read_regular_file_bytes(path)
    document = _decode_persistence_json(raw_bytes)
    return resume_session_document_v1(document)


def _sort_json_objects(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _sort_json_objects(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_sort_json_objects(item) for item in value]
    return value


def _canonical_file_document(
    document: SessionPersistenceDocumentV1,
) -> dict[str, Any]:
    value = document.to_dict()
    for checkpoint in value["decision_checkpoints"]:
        checkpoint["request"]["document"] = _sort_json_objects(checkpoint["request"]["document"])
    return value


def _build_session_persistence_file_bytes_v1(
    document: SessionPersistenceDocumentV1,
) -> bytes:
    try:
        text = json.dumps(
            _canonical_file_document(document),
            allow_nan=False,
            ensure_ascii=True,
            indent=2,
        )
    except (TypeError, ValueError) as error:
        raise SkatMindInvariantError(
            "Session persistence document cannot be serialized as finite JSON.",
            path="",
        ) from error
    return f"{text}\n".encode(SESSION_PERSISTENCE_ENCODING)


def _validate_requested_document(
    document: SessionPersistenceDocumentV1,
) -> SessionPersistenceDocumentV1:
    if type(document) is not SessionPersistenceDocumentV1:
        raise ValueError("document must be a SessionPersistenceDocumentV1.")
    try:
        resumed = resume_session_document_v1(document)
    except SkatMindValidationError as error:
        raise SkatMindInvariantError(
            "Internally supplied Session persistence document is inconsistent.",
            path=error.path,
        ) from error
    if resumed.document != document:
        raise SkatMindInvariantError(
            "Internally supplied Session persistence document is not canonical.",
            path="",
        )
    return build_session_persistence_document_v1(
        resumed.document.state,
        decision_checkpoints=resumed.document.decision_checkpoints,
    )


def _load_existing_target(
    file_path: Path,
) -> tuple[bool, SessionPersistenceDocumentV1 | None]:
    try:
        resumed = load_session_persistence_file_v1(file_path)
    except FileNotFoundError:
        return False, None
    return True, resumed.document


def _write_result(
    *,
    status: str,
    document: SessionPersistenceDocumentV1,
    expected_content_fingerprint: str | None,
    existing_content_fingerprint: str | None,
) -> SessionPersistenceWriteResultV1:
    return SessionPersistenceWriteResultV1(
        status=status,
        session_id=document.state.session_id,
        revision=document.state.revision,
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
            "Session persistence parent must be an existing directory.",
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


def save_session_persistence_file_v1(
    file_path: str | os.PathLike[str],
    document: SessionPersistenceDocumentV1,
    *,
    expected_content_fingerprint: str | None,
) -> SessionPersistenceWriteResultV1:
    """Optimistically saves one private Session through atomic replacement."""
    requested = _validate_requested_document(document)
    expected = _require_optional_fingerprint(expected_content_fingerprint)
    path = Path(file_path)

    target_exists, existing_document = _load_existing_target(path)
    existing = None if existing_document is None else existing_document.content_fingerprint
    if target_exists != (existing_document is not None):
        raise SkatMindInvariantError(
            "Existing Session persistence target observation is inconsistent.",
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
    persisted_bytes = _build_session_persistence_file_bytes_v1(requested)
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
            temporary_file.write(persisted_bytes)
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
