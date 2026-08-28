import json
import os

import pytest
from test_learning_corpus_match_snapshot import _annotated_workspace, _snapshot_for_workspace

import skatmind.learning_corpus_persistence as persistence_module
from skatmind.errors import SkatMindValidationError
from skatmind.learning_corpus_catalog import (
    LearningCorpusMatchSnapshotCatalogEntryV1,
    build_learning_corpus_catalog_v1,
    build_learning_corpus_current_match_selection_v1,
)
from skatmind.learning_corpus_catalog_operations import (
    apply_learning_corpus_match_snapshot_import_v1,
)
from skatmind.learning_corpus_persistence import (
    initialize_learning_corpus_directory_v1,
    load_learning_corpus_directory_v1,
    load_learning_corpus_match_snapshot_object_file_v1,
    publish_learning_corpus_match_snapshot_object_v1,
    save_learning_corpus_catalog_v1,
)
from skatmind.learning_corpus_persistence_codec import (
    _build_learning_corpus_match_snapshot_object_file_bytes_v1,
    build_learning_corpus_catalog_persistence_document_v1,
)


def _initialize(tmp_path, name="corpus"):
    root = tmp_path / name
    store = initialize_learning_corpus_directory_v1(root, corpus_id="corpus-172")
    return root, store


def _snapshot():
    return _snapshot_for_workspace(_annotated_workspace())[1]


def _catalog_with_snapshot(store, snapshot):
    change = apply_learning_corpus_match_snapshot_import_v1(
        store.document.catalog,
        snapshot,
        expected_revision=store.document.catalog.revision,
        selection_mode="select_imported",
        same_revision_resolution="retain",
    )
    assert change.status == "applied"
    return build_learning_corpus_catalog_persistence_document_v1(change.catalog)


def test_initialization_creates_only_fixed_layout_and_empty_revision_zero_catalog(
    tmp_path,
) -> None:
    root, store = _initialize(tmp_path)
    assert {path.name for path in root.iterdir()} == {"objects", "catalog.json"}
    assert tuple((root / "objects").iterdir()) == (
        root / "objects" / "match_workspace_snapshot",
    )
    assert tuple((root / "objects" / "match_workspace_snapshot").iterdir()) == ()
    assert store.document.catalog.corpus_id == "corpus-172"
    assert store.document.catalog.revision == 0
    assert store.match_snapshots == store.orphan_match_snapshot_ids == ()
    raw = (root / "catalog.json").read_bytes()
    assert b"\r" not in raw and raw.endswith(b"\n")
    assert json.loads(raw) == store.document.to_dict()


def test_initialization_accepts_existing_empty_root_and_rejects_invalid_roots(tmp_path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    assert initialize_learning_corpus_directory_v1(
        empty,
        corpus_id="caller-supplied",
    ).document.catalog.corpus_id == "caller-supplied"
    nonempty = tmp_path / "nonempty"
    nonempty.mkdir()
    (nonempty / "caller.txt").write_text("keep")
    with pytest.raises(OSError):
        initialize_learning_corpus_directory_v1(nonempty, corpus_id="corpus-172")
    assert (nonempty / "caller.txt").read_text() == "keep"
    with pytest.raises(FileNotFoundError):
        initialize_learning_corpus_directory_v1(
            tmp_path / "missing" / "corpus",
            corpus_id="corpus-172",
        )


def test_initialization_failure_cleans_only_paths_created_by_attempt(
    tmp_path,
    monkeypatch,
) -> None:
    root = tmp_path / "failed"

    def fail(*_args, **_kwargs):
        raise OSError("injected Catalog save failure")

    monkeypatch.setattr(persistence_module, "save_learning_corpus_catalog_v1", fail)
    with pytest.raises(OSError, match="injected"):
        initialize_learning_corpus_directory_v1(root, corpus_id="corpus-172")
    assert not root.exists()


def test_store_resume_requires_and_reconciles_each_catalog_object(tmp_path) -> None:
    root, source = _initialize(tmp_path)
    snapshot = _snapshot()
    document = _catalog_with_snapshot(source, snapshot)
    publish_learning_corpus_match_snapshot_object_v1(root, snapshot)
    save_learning_corpus_catalog_v1(
        root,
        document,
        expected_content_fingerprint=source.document.content_fingerprint,
    )
    resumed = load_learning_corpus_directory_v1(root)
    assert resumed.document == document
    assert resumed.match_snapshots == (snapshot,)
    assert resumed.orphan_match_snapshot_ids == ()
    assert "path" not in resumed.to_dict()


def test_store_resume_rejects_valid_catalog_entry_that_disagrees_with_object(
    tmp_path,
) -> None:
    root, source = _initialize(tmp_path)
    snapshot = _snapshot()
    actual = _catalog_with_snapshot(source, snapshot).catalog.match_snapshots[0]
    mismatched = LearningCorpusMatchSnapshotCatalogEntryV1._from_validated(
        match_snapshot_id=actual.match_snapshot_id,
        match_id=actual.match_id,
        workspace_revision=actual.workspace_revision,
        source_workspace_fingerprint=actual.source_workspace_fingerprint,
        source_content_fingerprint=actual.source_content_fingerprint,
        played_at=actual.played_at,
        source_kind=actual.source_kind,
        source_title=actual.source_title,
        game_platform=actual.game_platform,
        perspective_player_id=actual.perspective_player_id,
        player_ids=actual.player_ids,
        observed_game_count=0,
        passed_deal_count=0,
        empty_slot_count=36,
        decision_count=0,
        commentary_count=0,
        response_link_count=0,
    )
    catalog = build_learning_corpus_catalog_v1(
        corpus_id=source.document.catalog.corpus_id,
        revision=1,
        match_snapshots=(mismatched,),
        current_matches=(
            build_learning_corpus_current_match_selection_v1(
                match_id=snapshot.match_id,
                match_snapshot_id=snapshot.match_snapshot_id,
            ),
        ),
    )
    document = build_learning_corpus_catalog_persistence_document_v1(catalog)
    publish_learning_corpus_match_snapshot_object_v1(root, snapshot)
    save_learning_corpus_catalog_v1(
        root,
        document,
        expected_content_fingerprint=source.document.content_fingerprint,
    )
    with pytest.raises(SkatMindValidationError, match="reconcile"):
        load_learning_corpus_directory_v1(root)


def test_store_resume_rejects_missing_and_malformed_referenced_object(tmp_path) -> None:
    root, source = _initialize(tmp_path)
    snapshot = _snapshot()
    document = _catalog_with_snapshot(source, snapshot)
    save_learning_corpus_catalog_v1(
        root,
        document,
        expected_content_fingerprint=source.document.content_fingerprint,
    )
    with pytest.raises(FileNotFoundError):
        load_learning_corpus_directory_v1(root)
    object_path = (
        root
        / "objects"
        / "match_workspace_snapshot"
        / f"{snapshot.match_snapshot_id}.json"
    )
    object_path.write_bytes(b"{}\n")
    with pytest.raises(SkatMindValidationError):
        load_learning_corpus_directory_v1(root)


def test_valid_unreferenced_objects_are_sorted_reported_and_never_changed(tmp_path) -> None:
    root, _ = _initialize(tmp_path)
    first = _snapshot()
    from test_learning_corpus_catalog import _revision_snapshots

    second = _revision_snapshots()[0]
    for snapshot in (first, second):
        assert publish_learning_corpus_match_snapshot_object_v1(root, snapshot) == "saved"
    before = {
        path.name: path.read_bytes()
        for path in (root / "objects" / "match_workspace_snapshot").iterdir()
    }
    resumed = load_learning_corpus_directory_v1(root)
    assert resumed.match_snapshots == ()
    assert resumed.orphan_match_snapshot_ids == tuple(
        sorted((first.match_snapshot_id, second.match_snapshot_id))
    )
    after = {
        path.name: path.read_bytes()
        for path in (root / "objects" / "match_workspace_snapshot").iterdir()
    }
    assert after == before


def test_hidden_temporary_and_unrelated_files_are_ignored_but_invalid_object_is_not(
    tmp_path,
) -> None:
    root, _ = _initialize(tmp_path)
    object_directory = root / "objects" / "match_workspace_snapshot"
    (object_directory / ".owned.tmp").write_bytes(b"invalid")
    (object_directory / "notes.txt").write_bytes(b"invalid")
    assert load_learning_corpus_directory_v1(root).orphan_match_snapshot_ids == ()
    (object_directory / f"{'0' * 64}.json").write_bytes(b"{}")
    with pytest.raises(SkatMindValidationError):
        load_learning_corpus_directory_v1(root)


def test_snapshot_filename_id_mismatch_is_rejected(tmp_path) -> None:
    root, _ = _initialize(tmp_path)
    snapshot = _snapshot()
    wrong_id = "0" * 64
    if wrong_id == snapshot.match_snapshot_id:
        wrong_id = "1" * 64
    object_path = (
        root / "objects" / "match_workspace_snapshot" / f"{wrong_id}.json"
    )
    object_path.write_bytes(
        _build_learning_corpus_match_snapshot_object_file_bytes_v1(snapshot)
    )
    with pytest.raises(SkatMindValidationError, match="filename"):
        load_learning_corpus_directory_v1(root)


@pytest.mark.parametrize(
    "raw",
    (
        b"\xff",
        b"\xef\xbb\xbf{}",
        b"{",
        b'{"duplicate": 1, "duplicate": 2}',
        b'{"value": NaN}',
        b'{"value": -Infinity}',
        b"[]",
    ),
)
def test_match_snapshot_object_load_rejects_strict_json_failures(tmp_path, raw) -> None:
    root, _ = _initialize(tmp_path)
    object_path = (
        root / "objects" / "match_workspace_snapshot" / f"{'0' * 64}.json"
    )
    object_path.write_bytes(raw)
    with pytest.raises(SkatMindValidationError):
        load_learning_corpus_match_snapshot_object_file_v1(root, "0" * 64)


def test_object_publication_is_immutable_canonical_and_idempotent(tmp_path) -> None:
    root, _ = _initialize(tmp_path)
    snapshot = _snapshot()
    assert publish_learning_corpus_match_snapshot_object_v1(root, snapshot) == "saved"
    object_path = (
        root
        / "objects"
        / "match_workspace_snapshot"
        / f"{snapshot.match_snapshot_id}.json"
    )
    before = object_path.read_bytes()
    assert publish_learning_corpus_match_snapshot_object_v1(root, snapshot) == "unchanged"
    assert object_path.read_bytes() == before
    assert load_learning_corpus_match_snapshot_object_file_v1(
        root,
        snapshot.match_snapshot_id,
    ) == snapshot
    assert b"\r" not in before and before.endswith(b"\n")


def test_no_clobber_equal_race_returns_unchanged(tmp_path, monkeypatch) -> None:
    root, _ = _initialize(tmp_path)
    snapshot = _snapshot()
    original_link = persistence_module.os.link

    def publish_first(source, target):
        original_link(source, target)
        raise FileExistsError()

    monkeypatch.setattr(persistence_module.os, "link", publish_first)
    assert publish_learning_corpus_match_snapshot_object_v1(root, snapshot) == "unchanged"
    assert load_learning_corpus_match_snapshot_object_file_v1(
        root,
        snapshot.match_snapshot_id,
    ) == snapshot
    assert not tuple(
        path
        for path in (root / "objects" / "match_workspace_snapshot").iterdir()
        if path.name.startswith(".")
    )


def test_no_clobber_conflicting_race_is_not_overwritten(tmp_path, monkeypatch) -> None:
    root, _ = _initialize(tmp_path)
    snapshot = _snapshot()

    def publish_invalid(_source, target):
        with open(target, "xb") as file:
            file.write(b"{}\n")
        raise FileExistsError()

    monkeypatch.setattr(persistence_module.os, "link", publish_invalid)
    with pytest.raises(SkatMindValidationError):
        publish_learning_corpus_match_snapshot_object_v1(root, snapshot)
    target = (
        root
        / "objects"
        / "match_workspace_snapshot"
        / f"{snapshot.match_snapshot_id}.json"
    )
    assert target.read_bytes() == b"{}\n"


@pytest.mark.parametrize("failure_stage", ("write", "fsync", "link"))
def test_object_publication_failures_leave_no_partial_target_or_owned_temp(
    tmp_path,
    monkeypatch,
    failure_stage,
) -> None:
    root, _ = _initialize(tmp_path)
    snapshot = _snapshot()
    object_directory = root / "objects" / "match_workspace_snapshot"
    if failure_stage == "write":
        monkeypatch.setattr(
            persistence_module,
            "_write_complete",
            lambda *_args: (_ for _ in ()).throw(OSError("injected write failure")),
        )
    elif failure_stage == "fsync":
        monkeypatch.setattr(
            persistence_module.os,
            "fsync",
            lambda *_args: (_ for _ in ()).throw(OSError("injected fsync failure")),
        )
    else:
        monkeypatch.setattr(
            persistence_module.os,
            "link",
            lambda *_args: (_ for _ in ()).throw(OSError("injected link failure")),
        )
    with pytest.raises(OSError, match="injected"):
        publish_learning_corpus_match_snapshot_object_v1(root, snapshot)
    assert tuple(object_directory.iterdir()) == ()


def test_catalog_save_supports_saved_unchanged_conflict_and_atomic_failure(
    tmp_path,
    monkeypatch,
) -> None:
    root, source = _initialize(tmp_path)
    changed_catalog = build_learning_corpus_catalog_v1(
        corpus_id=source.document.catalog.corpus_id,
        revision=1,
        match_snapshots=(),
        current_matches=(),
    )
    changed = build_learning_corpus_catalog_persistence_document_v1(changed_catalog)
    unchanged = save_learning_corpus_catalog_v1(
        root,
        source.document,
        expected_content_fingerprint=source.document.content_fingerprint,
    )
    stale = save_learning_corpus_catalog_v1(
        root,
        changed,
        expected_content_fingerprint="0" * 64,
    )
    assert unchanged.status == "unchanged"
    assert stale.status == "conflict"
    before = (root / "catalog.json").read_bytes()

    def fail(_source, _target):
        raise OSError("injected replace failure")

    monkeypatch.setattr(persistence_module.os, "replace", fail)
    with pytest.raises(OSError, match="injected"):
        save_learning_corpus_catalog_v1(
            root,
            changed,
            expected_content_fingerprint=source.document.content_fingerprint,
        )
    assert (root / "catalog.json").read_bytes() == before
    assert not tuple(path for path in root.iterdir() if path.name.startswith("."))


def test_catalog_target_revalidation_conflict_preserves_existing_bytes(
    tmp_path,
    monkeypatch,
) -> None:
    root, source = _initialize(tmp_path)
    changed = build_learning_corpus_catalog_persistence_document_v1(
        build_learning_corpus_catalog_v1(
            corpus_id=source.document.catalog.corpus_id,
            revision=1,
            match_snapshots=(),
            current_matches=(),
        )
    )
    before = (root / "catalog.json").read_bytes()
    monkeypatch.setattr(
        persistence_module,
        "_pre_replace_existing_fingerprint",
        lambda _path: (False, None),
    )
    result = save_learning_corpus_catalog_v1(
        root,
        changed,
        expected_content_fingerprint=source.document.content_fingerprint,
    )
    assert result.status == "conflict"
    assert (root / "catalog.json").read_bytes() == before
    assert not tuple(path for path in root.iterdir() if path.name.startswith("."))


@pytest.mark.parametrize("failure_stage", ("write", "fsync"))
def test_catalog_write_failures_preserve_target_and_clean_owned_temp(
    tmp_path,
    monkeypatch,
    failure_stage,
) -> None:
    root, source = _initialize(tmp_path)
    changed = build_learning_corpus_catalog_persistence_document_v1(
        build_learning_corpus_catalog_v1(
            corpus_id=source.document.catalog.corpus_id,
            revision=1,
            match_snapshots=(),
            current_matches=(),
        )
    )
    before = (root / "catalog.json").read_bytes()
    if failure_stage == "write":
        monkeypatch.setattr(
            persistence_module,
            "_write_complete",
            lambda *_args: (_ for _ in ()).throw(OSError("injected write failure")),
        )
    else:
        monkeypatch.setattr(
            persistence_module.os,
            "fsync",
            lambda *_args: (_ for _ in ()).throw(OSError("injected fsync failure")),
        )
    with pytest.raises(OSError, match="injected"):
        save_learning_corpus_catalog_v1(
            root,
            changed,
            expected_content_fingerprint=source.document.content_fingerprint,
        )
    assert (root / "catalog.json").read_bytes() == before
    assert not tuple(path for path in root.iterdir() if path.name.startswith("."))


def test_invalid_existing_catalog_is_never_overwritten(tmp_path) -> None:
    root, source = _initialize(tmp_path)
    catalog_path = root / "catalog.json"
    catalog_path.write_bytes(b'{"invalid": true}\n')
    before = catalog_path.read_bytes()
    with pytest.raises(SkatMindValidationError):
        save_learning_corpus_catalog_v1(
            root,
            source.document,
            expected_content_fingerprint=None,
        )
    assert catalog_path.read_bytes() == before


@pytest.mark.parametrize(
    "raw",
    (
        b"\xff",
        b"\xef\xbb\xbf{}",
        b"{",
        b'{"duplicate": 1, "duplicate": 2}',
        b'{"value": NaN}',
        b'{"value": Infinity}',
        b"[]",
    ),
)
def test_catalog_load_rejects_strict_json_failures(tmp_path, raw) -> None:
    root, _ = _initialize(tmp_path)
    (root / "catalog.json").write_bytes(raw)
    with pytest.raises(SkatMindValidationError):
        load_learning_corpus_directory_v1(root)


def test_store_load_preserves_filesystem_failures(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        load_learning_corpus_directory_v1(tmp_path / "missing")
    root_file = tmp_path / "file"
    root_file.write_text("not a directory")
    with pytest.raises(NotADirectoryError):
        load_learning_corpus_directory_v1(root_file)
    root, _ = _initialize(tmp_path, "missing-objects")
    os.rmdir(root / "objects" / "match_workspace_snapshot")
    with pytest.raises(FileNotFoundError):
        load_learning_corpus_directory_v1(root)
    root, _ = _initialize(tmp_path, "catalog-directory")
    os.unlink(root / "catalog.json")
    os.mkdir(root / "catalog.json")
    with pytest.raises(OSError):
        load_learning_corpus_directory_v1(root)
    root, _ = _initialize(tmp_path, "missing-catalog")
    os.unlink(root / "catalog.json")
    with pytest.raises(FileNotFoundError):
        load_learning_corpus_directory_v1(root)
