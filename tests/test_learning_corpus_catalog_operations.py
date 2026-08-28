import pytest
from test_learning_corpus_catalog import _revision_snapshots
from test_learning_corpus_match_snapshot import (
    _same_revision_changed_workspaces,
    _snapshot_for_workspace,
)

import skatmind.learning_corpus_catalog_operations as operations_module
from skatmind.learning_corpus_catalog import (
    build_learning_corpus_catalog_v1,
    build_learning_corpus_current_match_selection_v1,
    build_learning_corpus_match_snapshot_catalog_entry_v1,
    create_empty_learning_corpus_catalog_v1,
)
from skatmind.learning_corpus_catalog_operations import (
    apply_learning_corpus_match_snapshot_import_v1,
    select_learning_corpus_current_match_snapshot_v1,
)


def _catalog(*snapshots, current, revision=4):
    return build_learning_corpus_catalog_v1(
        corpus_id="corpus-172",
        revision=revision,
        match_snapshots=tuple(
            build_learning_corpus_match_snapshot_catalog_entry_v1(snapshot)
            for snapshot in snapshots
        ),
        current_matches=tuple(
            build_learning_corpus_current_match_selection_v1(
                match_id=snapshot.match_id,
                match_snapshot_id=snapshot.match_snapshot_id,
            )
            for snapshot in current
        ),
    )


def _apply(catalog, snapshot, *, selection="keep_current", resolution="reject"):
    return apply_learning_corpus_match_snapshot_import_v1(
        catalog,
        snapshot,
        expected_revision=catalog.revision,
        selection_mode=selection,
        same_revision_resolution=resolution,
    )


def test_revision_conflict_precedes_classification_and_preserves_catalog(monkeypatch) -> None:
    snapshot = _revision_snapshots()[0]
    catalog = create_empty_learning_corpus_catalog_v1("corpus-172")

    def fail(*_args, **_kwargs):
        raise AssertionError("Snapshot semantics must not be evaluated.")

    monkeypatch.setattr(
        operations_module,
        "classify_learning_corpus_match_snapshot_v1",
        fail,
    )
    result = apply_learning_corpus_match_snapshot_import_v1(
        catalog,
        snapshot,
        expected_revision=1,
        selection_mode="select_imported",
        same_revision_resolution="retain",
    )
    assert result.status == "revision_conflict"
    assert result.relation is None
    assert result.catalog is catalog
    assert result.current_revision == 0


@pytest.mark.parametrize("selection_mode", ("select_imported", "keep_current"))
def test_new_match_adds_snapshot_and_only_selection(selection_mode) -> None:
    snapshot = _revision_snapshots()[0]
    source = create_empty_learning_corpus_catalog_v1("corpus-172")
    result = _apply(source, snapshot, selection=selection_mode)
    assert result.status == "applied"
    assert result.relation == "new_match"
    assert result.snapshot_added is result.selection_changed is True
    assert result.previous_current_snapshot_id is None
    assert result.current_snapshot_id == snapshot.match_snapshot_id
    assert result.catalog.revision == 1
    assert source.revision == 0 and source.match_snapshots == ()


def test_duplicate_keep_current_and_already_current_select_are_unchanged() -> None:
    revision_zero, revision_one, _ = _revision_snapshots()
    source = _catalog(revision_zero, revision_one, current=(revision_one,))
    keep = _apply(source, revision_zero, selection="keep_current")
    selected = _apply(source, revision_one, selection="select_imported")
    assert keep.status == selected.status == "unchanged"
    assert keep.relation == selected.relation == "duplicate_snapshot"
    assert keep.catalog is selected.catalog is source


def test_duplicate_noncurrent_select_changes_only_current_selection() -> None:
    revision_zero, revision_one, _ = _revision_snapshots()
    source = _catalog(revision_zero, revision_one, current=(revision_one,))
    result = _apply(source, revision_zero, selection="select_imported")
    assert result.status == "applied"
    assert result.snapshot_added is False
    assert result.selection_changed is True
    assert result.catalog.match_snapshots == source.match_snapshots
    assert result.current_snapshot_id == revision_zero.match_snapshot_id


@pytest.mark.parametrize(
    ("candidate_index", "current_index", "relation"),
    ((2, 1, "newer_revision"), (0, 1, "older_revision")),
)
@pytest.mark.parametrize("selection_mode", ("select_imported", "keep_current"))
def test_newer_and_older_revisions_are_retained_without_automatic_selection(
    candidate_index,
    current_index,
    relation,
    selection_mode,
) -> None:
    snapshots = _revision_snapshots()
    current = snapshots[current_index]
    candidate = snapshots[candidate_index]
    source = _catalog(current, current=(current,))
    result = _apply(source, candidate, selection=selection_mode)
    assert result.status == "applied"
    assert result.relation == relation
    assert result.snapshot_added is True
    expected_current = (
        candidate.match_snapshot_id
        if selection_mode == "select_imported"
        else current.match_snapshot_id
    )
    assert result.current_snapshot_id == expected_current
    assert result.catalog.revision == source.revision + 1


@pytest.mark.parametrize("selection_mode", ("select_imported", "keep_current"))
def test_same_revision_conflict_rejects_or_explicitly_retains(selection_mode) -> None:
    first_workspace, changed_workspace = _same_revision_changed_workspaces()
    _, first = _snapshot_for_workspace(first_workspace)
    _, changed = _snapshot_for_workspace(changed_workspace)
    source = _catalog(first, current=(first,))
    rejected = _apply(source, changed, selection=selection_mode, resolution="reject")
    assert rejected.status == "resolution_required"
    assert rejected.catalog is source
    retained = _apply(source, changed, selection=selection_mode, resolution="retain")
    assert retained.status == "applied"
    assert retained.snapshot_added is True
    assert len(retained.catalog.match_snapshots) == 2
    assert retained.current_snapshot_id == (
        changed.match_snapshot_id
        if selection_mode == "select_imported"
        else first.match_snapshot_id
    )


def test_import_classifies_exactly_once(monkeypatch) -> None:
    snapshot = _revision_snapshots()[0]
    catalog = create_empty_learning_corpus_catalog_v1("corpus-172")
    original = operations_module.classify_learning_corpus_match_snapshot_v1
    count = 0

    def counted(*args, **kwargs):
        nonlocal count
        count += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(
        operations_module,
        "classify_learning_corpus_match_snapshot_v1",
        counted,
    )
    _apply(catalog, snapshot)
    assert count == 1


def test_current_selection_change_unchanged_and_revision_conflict() -> None:
    revision_zero, revision_one, _ = _revision_snapshots()
    source = _catalog(revision_zero, revision_one, current=(revision_zero,))
    changed = select_learning_corpus_current_match_snapshot_v1(
        source,
        match_id=revision_one.match_id,
        match_snapshot_id=revision_one.match_snapshot_id,
        expected_revision=source.revision,
    )
    assert changed.status == "applied"
    assert changed.selection_changed is True and changed.snapshot_added is False
    assert changed.catalog.match_snapshots == source.match_snapshots
    assert changed.catalog.revision == source.revision + 1
    unchanged = select_learning_corpus_current_match_snapshot_v1(
        source,
        match_id=revision_zero.match_id,
        match_snapshot_id=revision_zero.match_snapshot_id,
        expected_revision=source.revision,
    )
    assert unchanged.status == "unchanged" and unchanged.catalog is source
    conflicted = select_learning_corpus_current_match_snapshot_v1(
        source,
        match_id="not-validated-under-conflict",
        match_snapshot_id="0" * 64,
        expected_revision=source.revision + 1,
    )
    assert conflicted.status == "revision_conflict"


def test_current_selection_rejects_unknown_and_foreign_targets() -> None:
    revision_zero = _revision_snapshots()[0]
    other_workspace = revision_zero.workspace
    from dataclasses import replace

    changed_definition = replace(
        other_workspace.match_definition,
        match_id="other-match",
    )
    from skatmind.match_workspace_contracts import create_match_workspace_v1

    _, other = _snapshot_for_workspace(create_match_workspace_v1(changed_definition))
    source = _catalog(revision_zero, other, current=(revision_zero, other))
    with pytest.raises(ValueError, match="represented"):
        select_learning_corpus_current_match_snapshot_v1(
            source,
            match_id="missing",
            match_snapshot_id=revision_zero.match_snapshot_id,
            expected_revision=source.revision,
        )
    with pytest.raises(ValueError, match="retained"):
        select_learning_corpus_current_match_snapshot_v1(
            source,
            match_id=revision_zero.match_id,
            match_snapshot_id="0" * 64,
            expected_revision=source.revision,
        )
    with pytest.raises(ValueError, match="belong"):
        select_learning_corpus_current_match_snapshot_v1(
            source,
            match_id=revision_zero.match_id,
            match_snapshot_id=other.match_snapshot_id,
            expected_revision=source.revision,
        )
