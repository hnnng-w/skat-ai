from __future__ import annotations

import errno
import json
import os
import stat
import tempfile
from collections.abc import Mapping
from pathlib import Path

from skat_ai.errors import SkatAIInvariantError, SkatAIValidationError
from skat_ai.learning_corpus_catalog import (
    _build_learning_corpus_match_snapshot_catalog_entry_from_validated_v1,
    create_empty_learning_corpus_catalog_v1,
)
from skat_ai.learning_corpus_match_snapshot import (
    LearningCorpusMatchSnapshotV1,
    validate_learning_corpus_match_snapshot_v1,
)
from skat_ai.learning_corpus_persistence_codec import (
    _build_learning_corpus_catalog_file_bytes_v1,
    _build_learning_corpus_match_snapshot_object_file_bytes_v1,
    build_learning_corpus_catalog_persistence_document_v1,
    resume_learning_corpus_catalog_document_v1,
    resume_learning_corpus_match_snapshot_object_v1,
)
from skat_ai.learning_corpus_persistence_contracts import (
    LEARNING_CORPUS_CATALOG_FILENAME,
    LEARNING_CORPUS_MATCH_SNAPSHOT_OBJECT_DIRECTORY,
    LEARNING_CORPUS_OBJECT_FILE_SUFFIX,
    LEARNING_CORPUS_OBJECTS_DIRECTORY,
    LEARNING_CORPUS_PERSISTENCE_ENCODING,
    LearningCorpusCatalogPersistenceDocumentV1,
    LearningCorpusCatalogWriteResultV1,
    LearningCorpusStoreResumeResultV1,
    _build_verified_learning_corpus_store_resume_result_v1,
)

_UTF8_BOM = b"\xef\xbb\xbf"


def _require_fingerprint(value: object, field_name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{field_name} must be a lowercase SHA-256 hexadecimal value.")
    return value


def _require_optional_fingerprint(value: object) -> str | None:
    if value is None:
        return None
    return _require_fingerprint(value, "expected_content_fingerprint")


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise SkatAIValidationError(
                f"Duplicate JSON object key {key!r} is not allowed.",
                path="",
            )
        result[key] = value
    return result


def _reject_non_finite_constant(value: str) -> object:
    raise SkatAIValidationError(
        f"Non-finite JSON number {value!r} is not allowed.",
        path="",
    )


def _decode_learning_corpus_json(
    raw_bytes: bytes,
    *,
    description: str,
) -> Mapping[str, object]:
    if raw_bytes.startswith(_UTF8_BOM):
        raise SkatAIValidationError(
            f"{description} must use UTF-8 without a BOM.",
            path="",
        )
    try:
        text = raw_bytes.decode(LEARNING_CORPUS_PERSISTENCE_ENCODING, errors="strict")
    except UnicodeDecodeError as error:
        raise SkatAIValidationError(
            f"{description} is not valid UTF-8.",
            path="",
        ) from error
    try:
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_non_finite_constant,
        )
    except SkatAIValidationError:
        raise
    except json.JSONDecodeError as error:
        raise SkatAIValidationError(
            f"{description} is not valid JSON: {error.msg}.",
            path="",
        ) from error
    if not isinstance(value, Mapping):
        raise SkatAIValidationError(
            f"{description} root must be a JSON object.",
            path="",
        )
    return value


def _read_regular_file_bytes(file_path: Path, *, description: str) -> bytes:
    with file_path.open("rb") as file:
        mode = os.fstat(file.fileno()).st_mode
        if not stat.S_ISREG(mode):
            raise OSError(
                errno.EINVAL,
                f"{description} must identify a regular file.",
                os.fspath(file_path),
            )
        return file.read()


def _require_directory(directory: Path, *, description: str) -> Path:
    mode = os.stat(directory).st_mode
    if not stat.S_ISDIR(mode):
        raise NotADirectoryError(
            errno.ENOTDIR,
            f"{description} must be an existing directory.",
            os.fspath(directory),
        )
    return directory


def _catalog_path(root_path: Path) -> Path:
    return root_path / LEARNING_CORPUS_CATALOG_FILENAME


def _match_snapshot_object_directory(root_path: Path) -> Path:
    return (
        root_path
        / LEARNING_CORPUS_OBJECTS_DIRECTORY
        / LEARNING_CORPUS_MATCH_SNAPSHOT_OBJECT_DIRECTORY
    )


def _match_snapshot_object_path(root_path: Path, match_snapshot_id: str) -> Path:
    return _match_snapshot_object_directory(root_path) / (
        f"{match_snapshot_id}{LEARNING_CORPUS_OBJECT_FILE_SUFFIX}"
    )


def _load_learning_corpus_catalog_file(
    file_path: Path,
) -> LearningCorpusCatalogPersistenceDocumentV1:
    raw_bytes = _read_regular_file_bytes(
        file_path,
        description="Learning Corpus Catalog path",
    )
    document = _decode_learning_corpus_json(
        raw_bytes,
        description="Learning Corpus Catalog file",
    )
    return resume_learning_corpus_catalog_document_v1(document)


def load_learning_corpus_match_snapshot_object_file_v1(
    root_path: str | os.PathLike[str],
    match_snapshot_id: str,
) -> LearningCorpusMatchSnapshotV1:
    """Loads one object only from its fixed content-addressed Corpus path."""
    snapshot_id = _require_fingerprint(match_snapshot_id, "match_snapshot_id")
    root = Path(root_path)
    file_path = _match_snapshot_object_path(root, snapshot_id)
    raw_bytes = _read_regular_file_bytes(
        file_path,
        description="Learning Corpus Match Snapshot object path",
    )
    document = _decode_learning_corpus_json(
        raw_bytes,
        description="Learning Corpus Match Snapshot object file",
    )
    snapshot = resume_learning_corpus_match_snapshot_object_v1(document)
    if snapshot.match_snapshot_id != snapshot_id:
        raise SkatAIValidationError(
            "Match Snapshot object filename does not match its Snapshot ID.",
            path="/match_snapshot_id",
        )
    return snapshot


def _is_canonical_match_snapshot_filename(name: str) -> bool:
    if not name.endswith(LEARNING_CORPUS_OBJECT_FILE_SUFFIX):
        return False
    snapshot_id = name[: -len(LEARNING_CORPUS_OBJECT_FILE_SUFFIX)]
    return (
        len(snapshot_id) == 64
        and all(character in "0123456789abcdef" for character in snapshot_id)
    )


def _reconcile_catalog_entry(
    snapshot: LearningCorpusMatchSnapshotV1,
    *,
    expected_entry,
) -> None:
    try:
        actual_entry = (
            _build_learning_corpus_match_snapshot_catalog_entry_from_validated_v1(
                snapshot
            )
        )
    except SkatAIInvariantError:
        raise
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        raise SkatAIInvariantError(
            "Strictly resumed Match Snapshot could not be summarized.",
            path="",
        ) from error
    if actual_entry != expected_entry:
        raise SkatAIValidationError(
            "Catalog entry does not reconcile with its Match Snapshot object.",
            path="/catalog/match_snapshots",
        )


def load_learning_corpus_directory_v1(
    root_path: str | os.PathLike[str],
) -> LearningCorpusStoreResumeResultV1:
    """Strictly resumes the authoritative Catalog, objects, and valid orphans."""
    root = _require_directory(
        Path(root_path),
        description="Learning Corpus root",
    )
    document = _load_learning_corpus_catalog_file(_catalog_path(root))
    objects_directory = _require_directory(
        root / LEARNING_CORPUS_OBJECTS_DIRECTORY,
        description="Learning Corpus objects path",
    )
    object_directory = _require_directory(
        objects_directory / LEARNING_CORPUS_MATCH_SNAPSHOT_OBJECT_DIRECTORY,
        description="Learning Corpus Match Snapshot object path",
    )

    snapshots: list[LearningCorpusMatchSnapshotV1] = []
    referenced_ids: set[str] = set()
    for entry in document.catalog.match_snapshots:
        if entry.match_snapshot_id in referenced_ids:
            raise SkatAIInvariantError(
                "Validated Catalog contains a duplicate Match Snapshot ID.",
                path="/catalog/match_snapshots",
            )
        referenced_ids.add(entry.match_snapshot_id)
        snapshot = load_learning_corpus_match_snapshot_object_file_v1(
            root,
            entry.match_snapshot_id,
        )
        _reconcile_catalog_entry(snapshot, expected_entry=entry)
        snapshots.append(snapshot)

    with os.scandir(object_directory) as scanned:
        object_names = tuple(entry.name for entry in scanned)
    object_ids = sorted(
        name[: -len(LEARNING_CORPUS_OBJECT_FILE_SUFFIX)]
        for name in object_names
        if _is_canonical_match_snapshot_filename(name)
    )
    orphan_ids: list[str] = []
    for snapshot_id in object_ids:
        if snapshot_id in referenced_ids:
            continue
        load_learning_corpus_match_snapshot_object_file_v1(root, snapshot_id)
        orphan_ids.append(snapshot_id)

    return _build_verified_learning_corpus_store_resume_result_v1(
        document=document,
        match_snapshots=tuple(snapshots),
        orphan_match_snapshot_ids=tuple(orphan_ids),
    )


def _validate_requested_catalog_document(
    document: LearningCorpusCatalogPersistenceDocumentV1,
) -> LearningCorpusCatalogPersistenceDocumentV1:
    if type(document) is not LearningCorpusCatalogPersistenceDocumentV1:
        raise ValueError(
            "document must be a LearningCorpusCatalogPersistenceDocumentV1."
        )
    try:
        resumed = resume_learning_corpus_catalog_document_v1(document.to_dict())
    except SkatAIValidationError as error:
        raise SkatAIInvariantError(
            "Internally supplied Learning Corpus Catalog document is inconsistent.",
            path=error.path,
        ) from error
    if resumed != document:
        raise SkatAIInvariantError(
            "Internally supplied Learning Corpus Catalog document is not canonical.",
            path="",
        )
    return resumed


def _load_existing_catalog_target(
    file_path: Path,
) -> tuple[bool, LearningCorpusCatalogPersistenceDocumentV1 | None]:
    try:
        document = _load_learning_corpus_catalog_file(file_path)
    except FileNotFoundError:
        return False, None
    return True, document


def _catalog_write_result(
    *,
    status: str,
    document: LearningCorpusCatalogPersistenceDocumentV1,
    expected_content_fingerprint: str | None,
    existing_content_fingerprint: str | None,
) -> LearningCorpusCatalogWriteResultV1:
    return LearningCorpusCatalogWriteResultV1(
        status=status,
        corpus_id=document.catalog.corpus_id,
        revision=document.catalog.revision,
        expected_content_fingerprint=expected_content_fingerprint,
        existing_content_fingerprint=existing_content_fingerprint,
        requested_content_fingerprint=document.content_fingerprint,
    )


def _write_complete(temporary_file, persisted_bytes: bytes) -> None:
    offset = 0
    while offset < len(persisted_bytes):
        written = temporary_file.write(persisted_bytes[offset:])
        if type(written) is not int or written <= 0:
            raise OSError("Learning Corpus temporary write was incomplete.")
        offset += written


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


def _pre_replace_existing_fingerprint(file_path: Path) -> tuple[bool, str | None]:
    exists, document = _load_existing_catalog_target(file_path)
    return exists, None if document is None else document.content_fingerprint


def save_learning_corpus_catalog_v1(
    root_path: str | os.PathLike[str],
    document: LearningCorpusCatalogPersistenceDocumentV1,
    *,
    expected_content_fingerprint: str | None,
) -> LearningCorpusCatalogWriteResultV1:
    """Optimistically saves only catalog.json through atomic replacement."""
    requested = _validate_requested_catalog_document(document)
    expected = _require_optional_fingerprint(expected_content_fingerprint)
    root = _require_directory(
        Path(root_path),
        description="Learning Corpus root",
    )
    path = _catalog_path(root)
    target_exists, existing_document = _load_existing_catalog_target(path)
    existing = None if existing_document is None else existing_document.content_fingerprint
    if target_exists != (existing_document is not None):
        raise SkatAIInvariantError(
            "Existing Learning Corpus Catalog target observation is inconsistent.",
            path="",
        )
    if expected != existing:
        return _catalog_write_result(
            status="conflict",
            document=requested,
            expected_content_fingerprint=expected,
            existing_content_fingerprint=existing,
        )
    if target_exists and existing == requested.content_fingerprint:
        return _catalog_write_result(
            status="unchanged",
            document=requested,
            expected_content_fingerprint=expected,
            existing_content_fingerprint=existing,
        )

    persisted_bytes = _build_learning_corpus_catalog_file_bytes_v1(requested)
    file_descriptor: int | None = None
    temporary_path: Path | None = None
    try:
        file_descriptor, raw_temporary_path = tempfile.mkstemp(
            prefix=f".{LEARNING_CORPUS_CATALOG_FILENAME}.",
            suffix=".tmp",
            dir=root,
        )
        temporary_path = Path(raw_temporary_path)
        with os.fdopen(file_descriptor, "wb") as temporary_file:
            file_descriptor = None
            _write_complete(temporary_file, persisted_bytes)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())

        current_exists, current = _pre_replace_existing_fingerprint(path)
        if current_exists != target_exists or current != expected:
            return _catalog_write_result(
                status="conflict",
                document=requested,
                expected_content_fingerprint=expected,
                existing_content_fingerprint=current,
            )

        os.replace(temporary_path, path)
        temporary_path = None
        _best_effort_fsync_directory(root)
        return _catalog_write_result(
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


def _validate_requested_snapshot(
    snapshot: LearningCorpusMatchSnapshotV1,
) -> LearningCorpusMatchSnapshotV1:
    if type(snapshot) is not LearningCorpusMatchSnapshotV1:
        raise ValueError("snapshot must be an exact LearningCorpusMatchSnapshotV1.")
    try:
        validate_learning_corpus_match_snapshot_v1(snapshot)
    except SkatAIInvariantError:
        raise
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        raise SkatAIInvariantError(
            "Internally supplied Learning Corpus Match Snapshot is inconsistent.",
            path="",
        ) from error
    return snapshot


def _require_equal_existing_snapshot(
    root_path: Path,
    requested: LearningCorpusMatchSnapshotV1,
) -> None:
    existing = load_learning_corpus_match_snapshot_object_file_v1(
        root_path,
        requested.match_snapshot_id,
    )
    if existing != requested:
        raise SkatAIValidationError(
            "Existing content-addressed Match Snapshot object differs from the request.",
            path="",
        )


def publish_learning_corpus_match_snapshot_object_v1(
    root_path: str | os.PathLike[str],
    snapshot: LearningCorpusMatchSnapshotV1,
) -> str:
    """Publishes one complete immutable object without clobbering a winner."""
    requested = _validate_requested_snapshot(snapshot)
    root = _require_directory(
        Path(root_path),
        description="Learning Corpus root",
    )
    object_directory = _require_directory(
        _match_snapshot_object_directory(root),
        description="Learning Corpus Match Snapshot object path",
    )
    target_path = _match_snapshot_object_path(root, requested.match_snapshot_id)
    try:
        _require_equal_existing_snapshot(root, requested)
    except FileNotFoundError:
        pass
    else:
        return "unchanged"

    persisted_bytes = _build_learning_corpus_match_snapshot_object_file_bytes_v1(
        requested
    )
    file_descriptor: int | None = None
    temporary_path: Path | None = None
    try:
        file_descriptor, raw_temporary_path = tempfile.mkstemp(
            prefix=f".{requested.match_snapshot_id}.",
            suffix=".tmp",
            dir=object_directory,
        )
        temporary_path = Path(raw_temporary_path)
        with os.fdopen(file_descriptor, "wb") as temporary_file:
            file_descriptor = None
            _write_complete(temporary_file, persisted_bytes)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        try:
            os.link(temporary_path, target_path)
        except FileExistsError:
            _require_equal_existing_snapshot(root, requested)
            return "unchanged"
        os.unlink(temporary_path)
        temporary_path = None
        _best_effort_fsync_directory(object_directory)
        return "saved"
    finally:
        if file_descriptor is not None:
            os.close(file_descriptor)
        if temporary_path is not None:
            try:
                os.unlink(temporary_path)
            except FileNotFoundError:
                pass


def _remove_owned_catalog_if_equal(
    file_path: Path,
    expected_bytes: bytes,
) -> None:
    try:
        current_bytes = _read_regular_file_bytes(
            file_path,
            description="Learning Corpus Catalog path",
        )
        if current_bytes == expected_bytes:
            os.unlink(file_path)
    except OSError:
        pass


def initialize_learning_corpus_directory_v1(
    root_path: str | os.PathLike[str],
    *,
    corpus_id: str,
) -> LearningCorpusStoreResumeResultV1:
    """Initializes only the fixed empty version-1 Corpus directory layout."""
    root = Path(root_path)
    _require_directory(root.parent, description="Learning Corpus parent")
    root_created = False
    created_directories: list[Path] = []
    catalog_document: LearningCorpusCatalogPersistenceDocumentV1 | None = None
    catalog_saved = False
    try:
        try:
            _require_directory(root, description="Learning Corpus root")
        except FileNotFoundError:
            os.mkdir(root)
            root_created = True
        else:
            with os.scandir(root) as scanned:
                if next(scanned, None) is not None:
                    raise OSError(
                        errno.ENOTEMPTY,
                        "Learning Corpus root must be empty before initialization.",
                        os.fspath(root),
                    )

        objects_directory = root / LEARNING_CORPUS_OBJECTS_DIRECTORY
        os.mkdir(objects_directory)
        created_directories.append(objects_directory)
        object_directory = (
            objects_directory / LEARNING_CORPUS_MATCH_SNAPSHOT_OBJECT_DIRECTORY
        )
        os.mkdir(object_directory)
        created_directories.append(object_directory)

        catalog = create_empty_learning_corpus_catalog_v1(corpus_id)
        catalog_document = build_learning_corpus_catalog_persistence_document_v1(
            catalog
        )
        write_result = save_learning_corpus_catalog_v1(
            root,
            catalog_document,
            expected_content_fingerprint=None,
        )
        if write_result.status != "saved":
            raise FileExistsError(
                errno.EEXIST,
                "Learning Corpus Catalog was concurrently created.",
                os.fspath(_catalog_path(root)),
            )
        catalog_saved = True
        return load_learning_corpus_directory_v1(root)
    except Exception:
        if catalog_saved and catalog_document is not None:
            _remove_owned_catalog_if_equal(
                _catalog_path(root),
                _build_learning_corpus_catalog_file_bytes_v1(catalog_document),
            )
        for directory in reversed(created_directories):
            try:
                os.rmdir(directory)
            except OSError:
                pass
        if root_created:
            try:
                os.rmdir(root)
            except OSError:
                pass
        raise
