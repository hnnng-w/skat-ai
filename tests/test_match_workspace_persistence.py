import json
import os

import pytest
from test_match_workspace_contracts import _definition

import skat_ai.match_workspace_persistence as persistence_module
from skat_ai.errors import SkatAIValidationError
from skat_ai.match_workspace_contracts import create_match_workspace_v1
from skat_ai.match_workspace_operations import mark_match_workspace_passed_deal_v1
from skat_ai.match_workspace_persistence import (
    load_match_workspace_file_v1,
    save_match_workspace_file_v1,
)
from skat_ai.match_workspace_persistence_codec import (
    build_match_workspace_persistence_document_v1,
)


def _documents():
    source_workspace = create_match_workspace_v1(_definition())
    first_workspace = mark_match_workspace_passed_deal_v1(
        source_workspace,
        match_position=1,
        game_timecode=None,
        expected_revision=0,
    ).workspace
    second_workspace = mark_match_workspace_passed_deal_v1(
        source_workspace,
        match_position=2,
        game_timecode=None,
        expected_revision=0,
    ).workspace
    return (
        build_match_workspace_persistence_document_v1(first_workspace),
        build_match_workspace_persistence_document_v1(second_workspace),
    )


def test_new_file_save_load_and_canonical_bytes_are_exact(tmp_path) -> None:
    document, _ = _documents()
    file_path = tmp_path / "match-workspace.json"
    result = save_match_workspace_file_v1(
        file_path,
        document,
        expected_content_fingerprint=None,
    )
    raw = file_path.read_bytes()
    assert result.status == "saved"
    assert result.existing_content_fingerprint is None
    assert result.requested_content_fingerprint == document.content_fingerprint
    assert result.match_id == document.workspace.match_definition.match_id
    assert result.revision == document.workspace.revision
    assert not raw.startswith(b"\xef\xbb\xbf")
    assert b"\r" not in raw
    assert raw.endswith(b"\n") and not raw.endswith(b"\n\n")
    assert raw.startswith(b'{\n  "match_workspace_persistence_version": 1,\n')
    assert json.loads(raw.decode("utf-8")) == document.to_dict()
    resumed = load_match_workspace_file_v1(file_path)
    assert resumed.document == document
    assert resumed.progress.passed_deal_count == 1
    assert "path" not in resumed.to_dict()


def test_equal_documents_produce_byte_identical_files(tmp_path) -> None:
    document, _ = _documents()
    first_path = tmp_path / "first.json"
    second_path = tmp_path / "second.json"
    save_match_workspace_file_v1(
        first_path,
        document,
        expected_content_fingerprint=None,
    )
    resumed_document = load_match_workspace_file_v1(first_path).document
    save_match_workspace_file_v1(
        second_path,
        resumed_document,
        expected_content_fingerprint=None,
    )
    assert first_path.read_bytes() == second_path.read_bytes()


def test_load_identity_is_independent_of_whitespace_and_object_key_order(tmp_path) -> None:
    document, _ = _documents()
    file_path = tmp_path / "compact.json"
    compact = json.dumps(
        document.to_dict(),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    file_path.write_bytes(compact)
    resumed = load_match_workspace_file_v1(file_path)
    assert resumed.document == document
    assert resumed.document.content_fingerprint == document.content_fingerprint


def test_missing_and_existing_file_save_conflict_matrix(tmp_path) -> None:
    source, replacement = _documents()
    file_path = tmp_path / "workspace.json"
    missing_stale = save_match_workspace_file_v1(
        file_path,
        source,
        expected_content_fingerprint="1" * 64,
    )
    assert missing_stale.status == "conflict"
    assert not file_path.exists()
    created = save_match_workspace_file_v1(
        file_path,
        source,
        expected_content_fingerprint=None,
    )
    before = file_path.read_bytes()
    absent_expectation = save_match_workspace_file_v1(
        file_path,
        replacement,
        expected_content_fingerprint=None,
    )
    wrong_expectation = save_match_workspace_file_v1(
        file_path,
        replacement,
        expected_content_fingerprint="2" * 64,
    )
    unchanged = save_match_workspace_file_v1(
        file_path,
        source,
        expected_content_fingerprint=source.content_fingerprint,
    )
    assert created.status == "saved"
    assert absent_expectation.status == wrong_expectation.status == "conflict"
    assert unchanged.status == "unchanged"
    assert file_path.read_bytes() == before


def test_same_revision_stale_fingerprint_conflicts_and_current_identity_saves(tmp_path) -> None:
    source, replacement = _documents()
    file_path = tmp_path / "workspace.json"
    save_match_workspace_file_v1(
        file_path,
        source,
        expected_content_fingerprint=None,
    )
    changed = save_match_workspace_file_v1(
        file_path,
        replacement,
        expected_content_fingerprint=source.content_fingerprint,
    )
    stale = save_match_workspace_file_v1(
        file_path,
        source,
        expected_content_fingerprint=source.content_fingerprint,
    )
    current = save_match_workspace_file_v1(
        file_path,
        source,
        expected_content_fingerprint=replacement.content_fingerprint,
    )
    assert source.workspace.revision == replacement.workspace.revision
    assert changed.status == "saved"
    assert stale.status == "conflict"
    assert stale.existing_content_fingerprint == replacement.content_fingerprint
    assert current.status == "saved"
    assert load_match_workspace_file_v1(file_path).document == source


@pytest.mark.parametrize(
    "raw",
    (
        b"\xff",
        b"\xef\xbb\xbf{}",
        b"{",
        b'{"duplicate": 1, "duplicate": 2}',
        b'{"value": NaN}',
        b'{"value": Infinity}',
        b'{"value": -Infinity}',
        b"[]",
    ),
)
def test_file_load_rejects_utf8_bom_json_duplicates_nonfinite_and_root(
    tmp_path,
    raw: bytes,
) -> None:
    file_path = tmp_path / "invalid.json"
    file_path.write_bytes(raw)
    with pytest.raises(SkatAIValidationError):
        load_match_workspace_file_v1(file_path)


def test_file_load_rejects_duplicate_nested_keys(tmp_path) -> None:
    document, _ = _documents()
    raw = persistence_module._build_match_workspace_file_bytes_v1(document)
    raw = raw.replace(
        b'"workspace": {',
        b'"workspace": {"revision": 999,',
        1,
    )
    file_path = tmp_path / "duplicate-nested.json"
    file_path.write_bytes(raw)
    with pytest.raises(SkatAIValidationError, match="Duplicate"):
        load_match_workspace_file_v1(file_path)


def test_file_load_preserves_filesystem_exceptions(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        load_match_workspace_file_v1(tmp_path / "missing.json")
    with pytest.raises(OSError):
        load_match_workspace_file_v1(tmp_path)


def test_invalid_existing_target_is_never_overwritten(tmp_path) -> None:
    document, _ = _documents()
    file_path = tmp_path / "workspace.json"
    invalid = b'{"not": "a Workspace"}\n'
    file_path.write_bytes(invalid)
    with pytest.raises(SkatAIValidationError):
        save_match_workspace_file_v1(
            file_path,
            document,
            expected_content_fingerprint=None,
        )
    assert file_path.read_bytes() == invalid


def test_actual_write_requires_existing_parent_and_creates_no_directory(tmp_path) -> None:
    document, _ = _documents()
    parent = tmp_path / "missing"
    with pytest.raises(FileNotFoundError):
        save_match_workspace_file_v1(
            parent / "workspace.json",
            document,
            expected_content_fingerprint=None,
        )
    assert not parent.exists()


def test_atomic_replace_failure_preserves_old_target_and_cleans_temp(
    tmp_path,
    monkeypatch,
) -> None:
    source, replacement = _documents()
    file_path = tmp_path / "workspace.json"
    save_match_workspace_file_v1(
        file_path,
        source,
        expected_content_fingerprint=None,
    )
    before = file_path.read_bytes()

    def failed_replace(_source, _target):
        raise OSError("injected replace failure")

    monkeypatch.setattr(persistence_module.os, "replace", failed_replace)
    with pytest.raises(OSError, match="injected"):
        save_match_workspace_file_v1(
            file_path,
            replacement,
            expected_content_fingerprint=source.content_fingerprint,
        )
    assert file_path.read_bytes() == before
    assert tuple(tmp_path.iterdir()) == (file_path,)


def test_file_fsync_failure_preserves_old_target_and_cleans_temp(
    tmp_path,
    monkeypatch,
) -> None:
    source, replacement = _documents()
    file_path = tmp_path / "workspace.json"
    save_match_workspace_file_v1(
        file_path,
        source,
        expected_content_fingerprint=None,
    )
    before = file_path.read_bytes()

    def failed_fsync(_file_descriptor):
        raise OSError("injected fsync failure")

    monkeypatch.setattr(persistence_module.os, "fsync", failed_fsync)
    with pytest.raises(OSError, match="injected"):
        save_match_workspace_file_v1(
            file_path,
            replacement,
            expected_content_fingerprint=source.content_fingerprint,
        )
    assert file_path.read_bytes() == before
    assert tuple(tmp_path.iterdir()) == (file_path,)


@pytest.mark.parametrize("failure_stage", ("write", "flush"))
def test_write_and_flush_failures_preserve_old_target_and_clean_temp(
    tmp_path,
    monkeypatch,
    failure_stage: str,
) -> None:
    source, replacement = _documents()
    file_path = tmp_path / "workspace.json"
    save_match_workspace_file_v1(
        file_path,
        source,
        expected_content_fingerprint=None,
    )
    before = file_path.read_bytes()
    original_fdopen = persistence_module.os.fdopen

    class FailingFile:
        def __init__(self, file_descriptor: int) -> None:
            self._file = original_fdopen(file_descriptor, "wb")

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            self._file.close()

        def write(self, value: bytes):
            if failure_stage == "write":
                raise OSError("injected write failure")
            return self._file.write(value)

        def flush(self):
            if failure_stage == "flush":
                raise OSError("injected flush failure")
            return self._file.flush()

        def fileno(self):
            return self._file.fileno()

    monkeypatch.setattr(
        persistence_module.os,
        "fdopen",
        lambda file_descriptor, _mode: FailingFile(file_descriptor),
    )
    with pytest.raises(OSError, match=failure_stage):
        save_match_workspace_file_v1(
            file_path,
            replacement,
            expected_content_fingerprint=source.content_fingerprint,
        )
    assert file_path.read_bytes() == before
    assert tuple(tmp_path.iterdir()) == (file_path,)


def test_short_writes_are_completed_before_flush(tmp_path, monkeypatch) -> None:
    document, _ = _documents()
    file_path = tmp_path / "workspace.json"
    original_fdopen = persistence_module.os.fdopen
    write_count = 0

    class ShortWritingFile:
        def __init__(self, file_descriptor: int) -> None:
            self._file = original_fdopen(file_descriptor, "wb")

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            self._file.close()

        def write(self, value: bytes):
            nonlocal write_count
            write_count += 1
            return self._file.write(value[: max(1, len(value) // 2)])

        def flush(self):
            return self._file.flush()

        def fileno(self):
            return self._file.fileno()

    monkeypatch.setattr(
        persistence_module.os,
        "fdopen",
        lambda file_descriptor, _mode: ShortWritingFile(file_descriptor),
    )
    result = save_match_workspace_file_v1(
        file_path,
        document,
        expected_content_fingerprint=None,
    )
    assert result.status == "saved"
    assert write_count > 1
    assert load_match_workspace_file_v1(file_path).document == document


def test_new_file_replace_failure_leaves_target_absent_and_cleans_temp(
    tmp_path,
    monkeypatch,
) -> None:
    document, _ = _documents()
    file_path = tmp_path / "workspace.json"

    def failed_replace(_source, _target):
        raise OSError("injected new-file replace failure")

    monkeypatch.setattr(persistence_module.os, "replace", failed_replace)
    with pytest.raises(OSError, match="new-file"):
        save_match_workspace_file_v1(
            file_path,
            document,
            expected_content_fingerprint=None,
        )
    assert not file_path.exists()
    assert tuple(tmp_path.iterdir()) == ()


def test_pre_replace_change_returns_conflict_and_cleans_owned_temp(
    tmp_path,
    monkeypatch,
) -> None:
    source, replacement = _documents()
    file_path = tmp_path / "workspace.json"
    save_match_workspace_file_v1(
        file_path,
        source,
        expected_content_fingerprint=None,
    )
    before = file_path.read_bytes()
    monkeypatch.setattr(
        persistence_module,
        "_pre_replace_existing_fingerprint",
        lambda _path: (False, None),
    )
    result = save_match_workspace_file_v1(
        file_path,
        replacement,
        expected_content_fingerprint=source.content_fingerprint,
    )
    assert result.status == "conflict"
    assert result.existing_content_fingerprint is None
    assert file_path.read_bytes() == before
    assert tuple(tmp_path.iterdir()) == (file_path,)


def test_temporary_file_is_same_directory_and_unrelated_temp_is_ignored(
    tmp_path,
    monkeypatch,
) -> None:
    document, _ = _documents()
    file_path = tmp_path / "workspace.json"
    unrelated = tmp_path / ".workspace.json.stale.tmp"
    unrelated.write_bytes(b"not a Workspace")
    observed_directories = []
    original_mkstemp = persistence_module.tempfile.mkstemp

    def recorded_mkstemp(*args, **kwargs):
        observed_directories.append(os.fspath(kwargs["dir"]))
        return original_mkstemp(*args, **kwargs)

    monkeypatch.setattr(persistence_module.tempfile, "mkstemp", recorded_mkstemp)
    result = save_match_workspace_file_v1(
        file_path,
        document,
        expected_content_fingerprint=None,
    )
    assert result.status == "saved"
    assert observed_directories == [os.fspath(tmp_path)]
    assert unrelated.read_bytes() == b"not a Workspace"


def test_directory_fsync_failure_is_best_effort_after_success(
    tmp_path,
    monkeypatch,
) -> None:
    document, _ = _documents()
    file_path = tmp_path / "workspace.json"
    original_fsync = persistence_module.os.fsync
    count = 0

    def directory_failure(file_descriptor):
        nonlocal count
        count += 1
        if count > 1:
            raise OSError("directory fsync unavailable")
        return original_fsync(file_descriptor)

    monkeypatch.setattr(persistence_module.os, "fsync", directory_failure)
    result = save_match_workspace_file_v1(
        file_path,
        document,
        expected_content_fingerprint=None,
    )
    assert result.status == "saved"
    assert load_match_workspace_file_v1(file_path).document == document


def test_save_rejects_invalid_expected_fingerprint_and_document_type(tmp_path) -> None:
    document, _ = _documents()
    with pytest.raises(ValueError, match="expected_content_fingerprint"):
        save_match_workspace_file_v1(
            tmp_path / "workspace.json",
            document,
            expected_content_fingerprint="INVALID",
        )
    with pytest.raises(ValueError, match="MatchWorkspacePersistenceDocumentV1"):
        save_match_workspace_file_v1(
            tmp_path / "workspace.json",
            document.to_dict(),
            expected_content_fingerprint=None,
        )
