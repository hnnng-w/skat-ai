from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
from pathlib import Path

from .frontend_profile_codec import (
    build_frontend_profile_bytes_v1,
    resume_local_frontend_profile_v1,
)
from .frontend_profile_contracts import (
    FRONTEND_PROFILE_FILENAME,
    FRONTEND_PROFILE_MAX_FILE_BYTES,
    FrontendProfileLoadResultV1,
    FrontendProfileWriteResultV1,
    LocalFrontendProfileV1,
)

_UTF8_BOM = b"\xef\xbb\xbf"
_INVALID_ENTRY_DIGEST_DOMAIN = b"skatmind\0frontend_profile_invalid_entry_v1\0"


class _InvalidFrontendProfileEntryError(ValueError):
    def __init__(self, digest: str) -> None:
        super().__init__("Frontend profile entry is not safely readable.")
        self.digest = digest


def frontend_profile_path_v1(managed_data_root: Path) -> Path:
    if not isinstance(managed_data_root, Path):
        raise ValueError("managed_data_root must be a Path.")
    return managed_data_root / FRONTEND_PROFILE_FILENAME


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Frontend profile must not contain duplicate keys.")
        result[key] = value
    return result


def _reject_non_finite(value: str) -> object:
    raise ValueError(f"Non-finite JSON number {value!r} is not allowed.")


def _entry_identity(metadata: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        stat.S_IFMT(metadata.st_mode),
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_size,
        metadata.st_mtime_ns,
    )


def _invalid_entry_digest(metadata: os.stat_result) -> str:
    observation = ":".join(str(value) for value in _entry_identity(metadata)).encode("ascii")
    return hashlib.sha256(_INVALID_ENTRY_DIGEST_DOMAIN + observation).hexdigest()


def _read_direct_regular_file(path: Path) -> bytes:
    initial = os.lstat(path)
    if not stat.S_ISREG(initial.st_mode) or initial.st_size > FRONTEND_PROFILE_MAX_FILE_BYTES:
        raise _InvalidFrontendProfileEntryError(_invalid_entry_digest(initial))
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        current = os.lstat(path)
        if (
            not stat.S_ISREG(opened.st_mode)
            or not stat.S_ISREG(current.st_mode)
            or _entry_identity(initial) != _entry_identity(opened)
            or _entry_identity(opened) != _entry_identity(current)
        ):
            raise _InvalidFrontendProfileEntryError(_invalid_entry_digest(current))
        with os.fdopen(descriptor, "rb") as source:
            descriptor = -1
            raw = source.read(FRONTEND_PROFILE_MAX_FILE_BYTES + 1)
        final = os.lstat(path)
        if (
            not stat.S_ISREG(final.st_mode)
            or _entry_identity(opened) != _entry_identity(final)
        ):
            raise _InvalidFrontendProfileEntryError(_invalid_entry_digest(final))
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if len(raw) > FRONTEND_PROFILE_MAX_FILE_BYTES:
        raise _InvalidFrontendProfileEntryError(_invalid_entry_digest(final))
    return raw


def _invalid(digest: str) -> FrontendProfileLoadResultV1:
    return FrontendProfileLoadResultV1(
        status="invalid",
        invalid_raw_digest=digest,
    )


def load_frontend_profile_file_v1(managed_data_root: Path) -> FrontendProfileLoadResultV1:
    path = frontend_profile_path_v1(managed_data_root)
    try:
        raw = _read_direct_regular_file(path)
    except FileNotFoundError:
        return FrontendProfileLoadResultV1(status="absent")
    except _InvalidFrontendProfileEntryError as exc:
        return _invalid(exc.digest)
    except OSError:
        try:
            return _invalid(_invalid_entry_digest(os.lstat(path)))
        except FileNotFoundError:
            return FrontendProfileLoadResultV1(status="absent")
    try:
        if raw.startswith(_UTF8_BOM):
            raise ValueError("Frontend profile must use UTF-8 without a BOM.")
        text = raw.decode("utf-8", errors="strict")
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_non_finite,
        )
        if type(value) is not dict:
            raise ValueError("Frontend profile root must be an object.")
        document = resume_local_frontend_profile_v1(value)
        if build_frontend_profile_bytes_v1(document) != raw:
            raise ValueError("Frontend profile bytes are not canonical.")
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError):
        return _invalid(hashlib.sha256(raw).hexdigest())
    return FrontendProfileLoadResultV1(status="available", document=document)


def _matches_expected(
    load: FrontendProfileLoadResultV1,
    *,
    expected_fingerprint: str | None,
    expected_invalid_raw_digest: str | None,
) -> bool:
    if expected_fingerprint is not None:
        return (
            load.status == "available"
            and load.document is not None
            and load.document.content_fingerprint == expected_fingerprint
            and expected_invalid_raw_digest is None
        )
    if expected_invalid_raw_digest is not None:
        return (
            load.status == "invalid"
            and load.invalid_raw_digest == expected_invalid_raw_digest
        )
    return load.status == "absent"


def _validate_expected_state(
    *,
    expected_fingerprint: str | None,
    expected_invalid_raw_digest: str | None,
) -> None:
    if expected_fingerprint is not None and expected_invalid_raw_digest is not None:
        raise ValueError("Expected profile state must identify exactly one state.")
    for value, name in (
        (expected_fingerprint, "expected_fingerprint"),
        (expected_invalid_raw_digest, "expected_invalid_raw_digest"),
    ):
        if value is not None and (
            type(value) is not str
            or len(value) != 64
            or any(character not in "0123456789abcdef" for character in value)
        ):
            raise ValueError(f"{name} must be one lowercase SHA-256 value.")


def _validate_revision_transition(
    load: FrontendProfileLoadResultV1,
    document: LocalFrontendProfileV1,
) -> None:
    if load.status == "available":
        assert load.document is not None
        expected_revision = load.document.revision + 1
    else:
        expected_revision = 0
    if document.revision != expected_revision:
        raise ValueError("Frontend profile revision must advance exactly once.")


def _write_complete(target, content: bytes) -> None:
    offset = 0
    while offset < len(content):
        written = target.write(content[offset:])
        if type(written) is not int or written <= 0:
            raise OSError("Frontend profile temporary write was incomplete.")
        offset += written


def _best_effort_fsync_directory(directory: Path) -> None:
    descriptor: int | None = None
    try:
        flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
        descriptor = os.open(directory, flags)
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass


def save_frontend_profile_file_v1(
    managed_data_root: Path,
    document: LocalFrontendProfileV1,
    *,
    expected_fingerprint: str | None,
    expected_invalid_raw_digest: str | None = None,
) -> FrontendProfileWriteResultV1:
    _validate_expected_state(
        expected_fingerprint=expected_fingerprint,
        expected_invalid_raw_digest=expected_invalid_raw_digest,
    )
    path = frontend_profile_path_v1(managed_data_root)
    requested_bytes = build_frontend_profile_bytes_v1(document)
    first = load_frontend_profile_file_v1(managed_data_root)
    if not _matches_expected(
        first,
        expected_fingerprint=expected_fingerprint,
        expected_invalid_raw_digest=expected_invalid_raw_digest,
    ):
        return FrontendProfileWriteResultV1(status="conflict", document=document)
    if (
        first.status == "available"
        and first.document is not None
        and first.document.content_fingerprint == document.content_fingerprint
    ):
        return FrontendProfileWriteResultV1(status="unchanged", document=document)
    _validate_revision_transition(first, document)
    parent_metadata = os.stat(managed_data_root)
    if not stat.S_ISDIR(parent_metadata.st_mode):
        raise NotADirectoryError("Managed data root must be an existing directory.")
    descriptor: int | None = None
    temporary_path: Path | None = None
    try:
        descriptor, raw_temporary_path = tempfile.mkstemp(
            prefix=f".{FRONTEND_PROFILE_FILENAME}.",
            suffix=".tmp",
            dir=managed_data_root,
        )
        temporary_path = Path(raw_temporary_path)
        with os.fdopen(descriptor, "wb") as temporary:
            descriptor = None
            _write_complete(temporary, requested_bytes)
            temporary.flush()
            os.fsync(temporary.fileno())
        second = load_frontend_profile_file_v1(managed_data_root)
        if not _matches_expected(
            second,
            expected_fingerprint=expected_fingerprint,
            expected_invalid_raw_digest=expected_invalid_raw_digest,
        ):
            return FrontendProfileWriteResultV1(status="conflict", document=document)
        removed_empty_directory = False
        if second.status == "invalid":
            target_metadata = os.lstat(path)
            if (
                not stat.S_ISREG(target_metadata.st_mode)
                and _invalid_entry_digest(target_metadata) != second.invalid_raw_digest
            ):
                return FrontendProfileWriteResultV1(status="conflict", document=document)
            if stat.S_ISDIR(target_metadata.st_mode):
                os.rmdir(path)
                removed_empty_directory = True
        try:
            os.replace(temporary_path, path)
        except OSError:
            if removed_empty_directory:
                try:
                    os.mkdir(path)
                except FileExistsError:
                    pass
            raise
        temporary_path = None
        _best_effort_fsync_directory(managed_data_root)
        return FrontendProfileWriteResultV1(status="saved", document=document)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if temporary_path is not None:
            try:
                os.unlink(temporary_path)
            except FileNotFoundError:
                pass
