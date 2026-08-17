from dataclasses import replace

import pytest
from test_learning_corpus_catalog import _revision_snapshots
from test_learning_corpus_match_snapshot import (
    _same_revision_changed_workspaces,
)

import skat_ai.learning_corpus_import as import_module
from skat_ai.learning_corpus_catalog import build_learning_corpus_catalog_v1
from skat_ai.learning_corpus_import import (
    import_match_workspace_file_into_learning_corpus_v1,
    set_learning_corpus_current_match_snapshot_file_v1,
)
from skat_ai.learning_corpus_persistence import (
    initialize_learning_corpus_directory_v1,
    save_learning_corpus_catalog_v1,
)
from skat_ai.learning_corpus_persistence_codec import (
    build_learning_corpus_catalog_persistence_document_v1,
)
from skat_ai.match_workspace_persistence import save_match_workspace_file_v1
from skat_ai.match_workspace_persistence_codec import (
    build_match_workspace_persistence_document_v1,
)


def _initialize(tmp_path, name="corpus"):
    root = tmp_path / name
    store = initialize_learning_corpus_directory_v1(root, corpus_id=f"{name}-id")
    return root, store


def _write_workspace(tmp_path, workspace, name="workspace.json"):
    path = tmp_path / name
    document = build_match_workspace_persistence_document_v1(workspace)
    result = save_match_workspace_file_v1(
        path,
        document,
        expected_content_fingerprint=None,
    )
    assert result.status == "saved"
    return path, document


def _import(root, store, workspace_path, *, selection="select_imported", resolution="reject"):
    return import_match_workspace_file_into_learning_corpus_v1(
        root,
        workspace_path,
        expected_catalog_revision=store.document.catalog.revision,
        expected_catalog_content_fingerprint=store.document.content_fingerprint,
        selection_mode=selection,
        same_revision_resolution=resolution,
    )


def test_strict_workspace_file_import_adds_object_and_catalog_without_mutating_source(
    tmp_path,
) -> None:
    root, store = _initialize(tmp_path)
    workspace = _revision_snapshots()[0].workspace
    workspace_path, _ = _write_workspace(tmp_path, workspace)
    source_bytes = workspace_path.read_bytes()
    result = _import(root, store, workspace_path)
    assert result.status == "applied"
    assert result.classification.relation == "new_match"
    assert result.catalog_change.snapshot_added is True
    assert result.object_write_status == "saved"
    assert result.catalog_write_status == "saved"
    assert result.store.document.catalog.revision == 1
    assert len(result.store.match_snapshots) == 1
    assert workspace_path.read_bytes() == source_bytes
    serialized = result.to_dict()
    assert "path" not in serialized
    assert "imported_at" not in serialized


def test_duplicate_import_is_unchanged_and_writes_nothing(tmp_path, monkeypatch) -> None:
    root, store = _initialize(tmp_path)
    workspace_path, _ = _write_workspace(
        tmp_path,
        _revision_snapshots()[0].workspace,
    )
    first = _import(root, store, workspace_path)

    def fail(*_args, **_kwargs):
        raise AssertionError("Duplicate import must not write.")

    monkeypatch.setattr(
        import_module,
        "publish_learning_corpus_match_snapshot_object_v1",
        fail,
    )
    monkeypatch.setattr(import_module, "save_learning_corpus_catalog_v1", fail)
    duplicate = _import(root, first.store, workspace_path, selection="keep_current")
    assert duplicate.status == "unchanged"
    assert duplicate.classification.relation == "duplicate_snapshot"
    assert duplicate.object_write_status == "not_required"
    assert duplicate.catalog_write_status == "not_required"


@pytest.mark.parametrize(
    ("first_index", "second_index", "relation"),
    ((0, 2, "newer_revision"), (2, 1, "older_revision")),
)
@pytest.mark.parametrize("selection_mode", ("select_imported", "keep_current"))
def test_newer_and_older_workspace_file_import_retains_explicit_selection(
    tmp_path,
    first_index,
    second_index,
    relation,
    selection_mode,
) -> None:
    root, store = _initialize(tmp_path, f"corpus-{first_index}-{selection_mode}")
    snapshots = _revision_snapshots()
    first_path, _ = _write_workspace(
        tmp_path,
        snapshots[first_index].workspace,
        f"first-{first_index}-{selection_mode}.json",
    )
    first = _import(root, store, first_path)
    second_path, _ = _write_workspace(
        tmp_path,
        snapshots[second_index].workspace,
        f"second-{second_index}-{selection_mode}.json",
    )
    second = _import(root, first.store, second_path, selection=selection_mode)
    assert second.status == "applied"
    assert second.classification.relation == relation
    assert len(second.store.match_snapshots) == 2
    expected_current = (
        snapshots[second_index].match_snapshot_id
        if selection_mode == "select_imported"
        else snapshots[first_index].match_snapshot_id
    )
    assert second.store.document.catalog.current_matches[0].match_snapshot_id == (
        expected_current
    )


def test_same_revision_workspace_conflict_requires_reject_or_explicit_retain(
    tmp_path,
) -> None:
    root, store = _initialize(tmp_path)
    first_workspace, changed_workspace = _same_revision_changed_workspaces()
    first_path, _ = _write_workspace(tmp_path, first_workspace, "first.json")
    first = _import(root, store, first_path)
    changed_path, _ = _write_workspace(tmp_path, changed_workspace, "changed.json")
    rejected = _import(root, first.store, changed_path, resolution="reject")
    assert rejected.status == "resolution_required"
    assert rejected.object_write_status == "not_required"
    assert rejected.store == first.store
    retained = _import(
        root,
        first.store,
        changed_path,
        selection="keep_current",
        resolution="retain",
    )
    assert retained.status == "applied"
    assert retained.classification.relation == "same_revision_content_conflict"
    assert len(retained.store.match_snapshots) == 2
    assert retained.store.document.catalog.current_matches[0].match_snapshot_id == (
        first.store.match_snapshots[0].match_snapshot_id
    )


def test_stale_revision_and_fingerprint_precede_workspace_file_read(
    tmp_path,
    monkeypatch,
) -> None:
    root, store = _initialize(tmp_path)

    def fail(*_args, **_kwargs):
        raise AssertionError("Stale import must not read the Workspace source.")

    monkeypatch.setattr(import_module, "load_match_workspace_file_v1", fail)
    revision_conflict = import_match_workspace_file_into_learning_corpus_v1(
        root,
        tmp_path / "missing.json",
        expected_catalog_revision=1,
        expected_catalog_content_fingerprint="0" * 64,
        selection_mode="select_imported",
        same_revision_resolution="reject",
    )
    assert revision_conflict.status == "revision_conflict"
    assert revision_conflict.classification is None
    fingerprint_conflict = import_match_workspace_file_into_learning_corpus_v1(
        root,
        tmp_path / "missing.json",
        expected_catalog_revision=0,
        expected_catalog_content_fingerprint="0" * 64,
        selection_mode="select_imported",
        same_revision_resolution="reject",
    )
    assert fingerprint_conflict.status == "persistence_conflict"
    assert fingerprint_conflict.catalog_change is None
    assert fingerprint_conflict.store == store


def test_new_import_executes_each_bounded_stage_once(tmp_path, monkeypatch) -> None:
    root, store = _initialize(tmp_path)
    workspace_path, _ = _write_workspace(
        tmp_path,
        _revision_snapshots()[0].workspace,
    )
    names = (
        "load_learning_corpus_directory_v1",
        "load_match_workspace_file_v1",
        "build_learning_corpus_match_snapshot_v1",
        "classify_learning_corpus_match_snapshot_v1",
        "publish_learning_corpus_match_snapshot_object_v1",
        "build_learning_corpus_catalog_persistence_document_v1",
        "save_learning_corpus_catalog_v1",
    )
    counts = {name: 0 for name in names}
    for name in names:
        original = getattr(import_module, name)

        def counted(*args, _name=name, _original=original, **kwargs):
            counts[_name] += 1
            return _original(*args, **kwargs)

        monkeypatch.setattr(import_module, name, counted)
    result = _import(root, store, workspace_path)
    assert result.status == "applied"
    assert counts == {
        "load_learning_corpus_directory_v1": 2,
        "load_match_workspace_file_v1": 1,
        "build_learning_corpus_match_snapshot_v1": 1,
        "classify_learning_corpus_match_snapshot_v1": 1,
        "publish_learning_corpus_match_snapshot_object_v1": 1,
        "build_learning_corpus_catalog_persistence_document_v1": 1,
        "save_learning_corpus_catalog_v1": 1,
    }


def test_object_before_catalog_conflict_leaves_orphan_and_repeated_import_reuses_it(
    tmp_path,
    monkeypatch,
) -> None:
    root, store = _initialize(tmp_path)
    workspace_path, _ = _write_workspace(
        tmp_path,
        _revision_snapshots()[0].workspace,
    )
    external_catalog = build_learning_corpus_catalog_v1(
        corpus_id=store.document.catalog.corpus_id,
        revision=1,
        match_snapshots=(),
        current_matches=(),
    )
    external_document = build_learning_corpus_catalog_persistence_document_v1(
        external_catalog
    )
    original_save = save_learning_corpus_catalog_v1
    calls = 0

    def conflict_after_external_save(root_path, document, *, expected_content_fingerprint):
        nonlocal calls
        calls += 1
        external = original_save(
            root_path,
            external_document,
            expected_content_fingerprint=expected_content_fingerprint,
        )
        assert external.status == "saved"
        return original_save(
            root_path,
            document,
            expected_content_fingerprint=expected_content_fingerprint,
        )

    monkeypatch.setattr(
        import_module,
        "save_learning_corpus_catalog_v1",
        conflict_after_external_save,
    )
    conflicted = _import(root, store, workspace_path)
    assert calls == 1
    assert conflicted.status == "persistence_conflict"
    assert conflicted.object_write_status == "saved"
    assert conflicted.catalog_write_status == "conflict"
    assert conflicted.store.document == external_document
    snapshot_id = conflicted.catalog_change.match_snapshot_id
    assert conflicted.store.orphan_match_snapshot_ids == (snapshot_id,)

    monkeypatch.setattr(import_module, "save_learning_corpus_catalog_v1", original_save)
    repeated = _import(root, conflicted.store, workspace_path)
    assert repeated.status == "applied"
    assert repeated.object_write_status == "unchanged"
    assert repeated.store.orphan_match_snapshot_ids == ()
    assert repeated.store.document.catalog.match_snapshots[0].match_snapshot_id == (
        snapshot_id
    )


def test_successful_import_returns_a_valid_concurrent_successor_as_final_store(
    tmp_path,
    monkeypatch,
) -> None:
    root, store = _initialize(tmp_path)
    workspace_path, _ = _write_workspace(
        tmp_path,
        _revision_snapshots()[0].workspace,
    )
    original_save = save_learning_corpus_catalog_v1
    successor_documents = []

    def save_then_successor(root_path, document, *, expected_content_fingerprint):
        saved = original_save(
            root_path,
            document,
            expected_content_fingerprint=expected_content_fingerprint,
        )
        assert saved.status == "saved"
        successor = build_learning_corpus_catalog_persistence_document_v1(
            build_learning_corpus_catalog_v1(
                corpus_id=document.catalog.corpus_id,
                revision=document.catalog.revision + 1,
                match_snapshots=document.catalog.match_snapshots,
                current_matches=document.catalog.current_matches,
            )
        )
        successor_saved = original_save(
            root_path,
            successor,
            expected_content_fingerprint=document.content_fingerprint,
        )
        assert successor_saved.status == "saved"
        successor_documents.append(successor)
        return saved

    monkeypatch.setattr(
        import_module,
        "save_learning_corpus_catalog_v1",
        save_then_successor,
    )
    result = _import(root, store, workspace_path)
    assert result.status == "applied"
    assert result.catalog_write_status == "saved"
    assert result.store.document == successor_documents[0]
    assert result.store.document.catalog.revision == result.catalog_change.current_revision + 1


def test_persisted_current_selection_change_writes_only_catalog(tmp_path) -> None:
    root, store = _initialize(tmp_path)
    revision_zero, revision_one, _ = _revision_snapshots()
    first_path, _ = _write_workspace(tmp_path, revision_zero.workspace, "zero.json")
    first = _import(root, store, first_path)
    second_path, _ = _write_workspace(tmp_path, revision_one.workspace, "one.json")
    second = _import(root, first.store, second_path, selection="keep_current")
    object_directory = root / "objects" / "match_workspace_snapshot"
    object_bytes = {path.name: path.read_bytes() for path in object_directory.iterdir()}
    changed = set_learning_corpus_current_match_snapshot_file_v1(
        root,
        match_id=revision_one.match_id,
        match_snapshot_id=revision_one.match_snapshot_id,
        expected_catalog_revision=second.store.document.catalog.revision,
        expected_catalog_content_fingerprint=second.store.document.content_fingerprint,
    )
    assert changed.status == "applied"
    assert changed.catalog_write_status == "saved"
    assert changed.store.document.catalog.current_matches[0].match_snapshot_id == (
        revision_one.match_snapshot_id
    )
    assert {path.name: path.read_bytes() for path in object_directory.iterdir()} == (
        object_bytes
    )
    unchanged = set_learning_corpus_current_match_snapshot_file_v1(
        root,
        match_id=revision_one.match_id,
        match_snapshot_id=revision_one.match_snapshot_id,
        expected_catalog_revision=changed.store.document.catalog.revision,
        expected_catalog_content_fingerprint=changed.store.document.content_fingerprint,
    )
    assert unchanged.status == "unchanged"
    assert unchanged.catalog_write_status == "not_required"


def test_persisted_selection_revision_and_fingerprint_conflicts_write_nothing(
    tmp_path,
) -> None:
    root, store = _initialize(tmp_path)
    snapshot = _revision_snapshots()[0]
    workspace_path, _ = _write_workspace(tmp_path, snapshot.workspace)
    imported = _import(root, store, workspace_path)
    before = (root / "catalog.json").read_bytes()
    revision_conflict = set_learning_corpus_current_match_snapshot_file_v1(
        root,
        match_id=snapshot.match_id,
        match_snapshot_id=snapshot.match_snapshot_id,
        expected_catalog_revision=99,
        expected_catalog_content_fingerprint="0" * 64,
    )
    fingerprint_conflict = set_learning_corpus_current_match_snapshot_file_v1(
        root,
        match_id=snapshot.match_id,
        match_snapshot_id=snapshot.match_snapshot_id,
        expected_catalog_revision=imported.store.document.catalog.revision,
        expected_catalog_content_fingerprint="0" * 64,
    )
    assert revision_conflict.status == "revision_conflict"
    assert fingerprint_conflict.status == "persistence_conflict"
    assert (root / "catalog.json").read_bytes() == before


def test_persisted_selection_catalog_save_conflict_retains_external_catalog(
    tmp_path,
    monkeypatch,
) -> None:
    root, store = _initialize(tmp_path)
    revision_zero, revision_one, _ = _revision_snapshots()
    first_path, _ = _write_workspace(tmp_path, revision_zero.workspace, "zero.json")
    first = _import(root, store, first_path)
    second_path, _ = _write_workspace(tmp_path, revision_one.workspace, "one.json")
    second = _import(root, first.store, second_path, selection="keep_current")
    external_catalog = build_learning_corpus_catalog_v1(
        corpus_id=second.store.document.catalog.corpus_id,
        revision=second.store.document.catalog.revision + 1,
        match_snapshots=second.store.document.catalog.match_snapshots,
        current_matches=second.store.document.catalog.current_matches,
    )
    external_document = build_learning_corpus_catalog_persistence_document_v1(
        external_catalog
    )
    original_save = save_learning_corpus_catalog_v1

    def conflict_after_external_save(root_path, document, *, expected_content_fingerprint):
        external = original_save(
            root_path,
            external_document,
            expected_content_fingerprint=expected_content_fingerprint,
        )
        assert external.status == "saved"
        return original_save(
            root_path,
            document,
            expected_content_fingerprint=expected_content_fingerprint,
        )

    monkeypatch.setattr(
        import_module,
        "save_learning_corpus_catalog_v1",
        conflict_after_external_save,
    )
    result = set_learning_corpus_current_match_snapshot_file_v1(
        root,
        match_id=revision_one.match_id,
        match_snapshot_id=revision_one.match_snapshot_id,
        expected_catalog_revision=second.store.document.catalog.revision,
        expected_catalog_content_fingerprint=second.store.document.content_fingerprint,
    )
    assert result.status == "persistence_conflict"
    assert result.catalog_change.status == "applied"
    assert result.catalog_write_status == "conflict"
    assert result.store.document == external_document
    assert result.store.document.catalog.current_matches[0].match_snapshot_id == (
        revision_zero.match_snapshot_id
    )


def test_import_retains_complete_private_workspace_only_in_object(tmp_path) -> None:
    root, store = _initialize(tmp_path)
    first_workspace, _ = _same_revision_changed_workspaces()
    workspace_path, _ = _write_workspace(tmp_path, first_workspace)
    _import(root, store, workspace_path)
    catalog_text = (root / "catalog.json").read_text()
    object_text = next(
        (root / "objects" / "match_workspace_snapshot").iterdir()
    ).read_text()
    commentary = first_workspace.slots[2].observed_game.commentaries[0].text
    assert commentary not in catalog_text
    assert commentary in object_text
    assert str(workspace_path) not in catalog_text
    assert str(workspace_path) not in object_text


def test_import_rejects_strict_workspace_file_content(tmp_path) -> None:
    root, store = _initialize(tmp_path)
    invalid = tmp_path / "invalid.json"
    invalid.write_bytes(b"{}\n")
    with pytest.raises(ValueError):
        _import(root, store, invalid)


def test_selection_target_validation_occurs_only_after_fingerprint_precedence(
    tmp_path,
) -> None:
    root, store = _initialize(tmp_path)
    result = set_learning_corpus_current_match_snapshot_file_v1(
        root,
        match_id="unknown",
        match_snapshot_id="0" * 64,
        expected_catalog_revision=0,
        expected_catalog_content_fingerprint="0" * 64,
    )
    assert result.status == "persistence_conflict"


def test_workspace_path_and_catalog_root_are_transport_only(tmp_path) -> None:
    root, store = _initialize(tmp_path)
    snapshot = _revision_snapshots()[0]
    changed_definition = replace(snapshot.workspace.match_definition, title="Private title")
    from skat_ai.match_workspace_contracts import create_match_workspace_v1

    workspace_path, _ = _write_workspace(
        tmp_path,
        create_match_workspace_v1(changed_definition),
    )
    result = _import(root, store, workspace_path)
    serialized = str(result.to_dict())
    assert str(root) not in serialized
    assert str(workspace_path) not in serialized
    assert "Private title" in serialized


def test_import_modules_have_no_analysis_dataset_cli_or_browser_dependency() -> None:
    forbidden = {
        "ApplicationInvocationV1",
        "build_training_dataset_summary",
        "MatchCaptureWebContextV1",
        "main",
    }
    for module in (
        import_module,
        __import__("skat_ai.learning_corpus_persistence", fromlist=["*"]),
    ):
        assert forbidden.isdisjoint(module.__dict__)


def test_existing_workspace_and_session_persistence_bytes_remain_unchanged(tmp_path) -> None:
    from test_match_workspace_persistence_codec import _rich_document
    from test_session_persistence import _documents as _session_documents

    from skat_ai.match_workspace_persistence import _build_match_workspace_file_bytes_v1
    from skat_ai.session_persistence import _build_session_persistence_file_bytes_v1

    workspace_document = _rich_document()
    session_document = _session_documents()[0]
    workspace_bytes = _build_match_workspace_file_bytes_v1(workspace_document)
    session_bytes = _build_session_persistence_file_bytes_v1(session_document)
    root, store = _initialize(tmp_path)
    workspace_path, _ = _write_workspace(
        tmp_path,
        workspace_document.workspace,
        "unchanged-workspace.json",
    )
    result = _import(root, store, workspace_path)
    assert result.status == "applied"
    assert _build_match_workspace_file_bytes_v1(workspace_document) == workspace_bytes
    assert _build_session_persistence_file_bytes_v1(session_document) == session_bytes
