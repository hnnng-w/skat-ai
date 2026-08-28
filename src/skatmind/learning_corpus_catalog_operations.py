from __future__ import annotations

from skatmind.learning_corpus_catalog import (
    LearningCorpusCatalogV1,
    LearningCorpusMatchSnapshotClassificationV1,
    _build_learning_corpus_match_snapshot_catalog_entry_from_validated_v1,
    _validate_learning_corpus_catalog_v1,
    build_learning_corpus_catalog_v1,
    build_learning_corpus_current_match_selection_v1,
    classify_learning_corpus_match_snapshot_v1,
)
from skatmind.learning_corpus_match_snapshot import LearningCorpusMatchSnapshotV1
from skatmind.learning_corpus_persistence_contracts import (
    LEARNING_CORPUS_IMPORT_SELECTION_MODES,
    LEARNING_CORPUS_SAME_REVISION_RESOLUTIONS,
    LearningCorpusCatalogChangeResultV1,
)


def _require_non_negative_integer(value: object, field_name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer.")
    return value


def _require_identifier(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{field_name} must be a non-empty, non-padded string.")
    return value


def _require_hash(value: object, field_name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{field_name} must be a lowercase SHA-256 hexadecimal value.")
    return value


def _require_catalog(catalog: object) -> LearningCorpusCatalogV1:
    if type(catalog) is not LearningCorpusCatalogV1:
        raise ValueError("catalog must be an exact LearningCorpusCatalogV1.")
    _validate_learning_corpus_catalog_v1(catalog)
    return catalog


def _require_snapshot_type(snapshot: object) -> LearningCorpusMatchSnapshotV1:
    if type(snapshot) is not LearningCorpusMatchSnapshotV1:
        raise ValueError("snapshot must be an exact LearningCorpusMatchSnapshotV1.")
    return snapshot


def _require_import_options(selection_mode: object, same_revision_resolution: object) -> None:
    if selection_mode not in LEARNING_CORPUS_IMPORT_SELECTION_MODES:
        raise ValueError(
            f"selection_mode must be one of {list(LEARNING_CORPUS_IMPORT_SELECTION_MODES)}."
        )
    if same_revision_resolution not in LEARNING_CORPUS_SAME_REVISION_RESOLUTIONS:
        raise ValueError(
            "same_revision_resolution must be one of "
            f"{list(LEARNING_CORPUS_SAME_REVISION_RESOLUTIONS)}."
        )


def _change_result(
    *,
    operation: str,
    status: str,
    relation: str | None,
    selection_mode: str | None,
    same_revision_resolution: str | None,
    match_id: str | None,
    match_snapshot_id: str | None,
    expected_revision: int,
    source_catalog: LearningCorpusCatalogV1,
    catalog: LearningCorpusCatalogV1,
    snapshot_added: bool,
    selection_changed: bool,
    previous_current_snapshot_id: str | None,
    current_snapshot_id: str | None,
) -> LearningCorpusCatalogChangeResultV1:
    return LearningCorpusCatalogChangeResultV1(
        operation=operation,
        status=status,
        relation=relation,
        selection_mode=selection_mode,
        same_revision_resolution=same_revision_resolution,
        match_id=match_id,
        match_snapshot_id=match_snapshot_id,
        expected_revision=expected_revision,
        source_revision=source_catalog.revision,
        current_revision=catalog.revision,
        snapshot_added=snapshot_added,
        selection_changed=selection_changed,
        previous_current_snapshot_id=previous_current_snapshot_id,
        current_snapshot_id=current_snapshot_id,
        catalog=catalog,
    )


def _build_learning_corpus_import_revision_conflict_v1(
    catalog: LearningCorpusCatalogV1,
    *,
    expected_revision: int,
    selection_mode: str,
    same_revision_resolution: str,
    match_id: str | None = None,
    match_snapshot_id: str | None = None,
) -> LearningCorpusCatalogChangeResultV1:
    return _change_result(
        operation="import_match_snapshot",
        status="revision_conflict",
        relation=None,
        selection_mode=selection_mode,
        same_revision_resolution=same_revision_resolution,
        match_id=match_id,
        match_snapshot_id=match_snapshot_id,
        expected_revision=expected_revision,
        source_catalog=catalog,
        catalog=catalog,
        snapshot_added=False,
        selection_changed=False,
        previous_current_snapshot_id=None,
        current_snapshot_id=None,
    )


def _replace_current_selection(
    catalog: LearningCorpusCatalogV1,
    *,
    match_id: str,
    match_snapshot_id: str,
):
    replacement = build_learning_corpus_current_match_selection_v1(
        match_id=match_id,
        match_snapshot_id=match_snapshot_id,
    )
    return tuple(
        replacement if selection.match_id == match_id else selection
        for selection in catalog.current_matches
    )


def _apply_learning_corpus_match_snapshot_import_v1(
    catalog: LearningCorpusCatalogV1,
    snapshot: LearningCorpusMatchSnapshotV1,
    *,
    expected_revision: int,
    selection_mode: str,
    same_revision_resolution: str,
    classification: LearningCorpusMatchSnapshotClassificationV1,
) -> LearningCorpusCatalogChangeResultV1:
    if type(classification) is not LearningCorpusMatchSnapshotClassificationV1:
        raise ValueError(
            "classification must be an exact LearningCorpusMatchSnapshotClassificationV1."
        )
    if (
        classification.match_id != snapshot.match_id
        or classification.candidate_snapshot_id != snapshot.match_snapshot_id
        or classification.candidate_workspace_revision != snapshot.workspace_revision
    ):
        raise ValueError("classification must describe the exact candidate Snapshot.")

    relation = classification.relation
    previous_current = classification.current_snapshot_id
    if relation == "same_revision_content_conflict" and same_revision_resolution == "reject":
        return _change_result(
            operation="import_match_snapshot",
            status="resolution_required",
            relation=relation,
            selection_mode=selection_mode,
            same_revision_resolution=same_revision_resolution,
            match_id=snapshot.match_id,
            match_snapshot_id=snapshot.match_snapshot_id,
            expected_revision=expected_revision,
            source_catalog=catalog,
            catalog=catalog,
            snapshot_added=False,
            selection_changed=False,
            previous_current_snapshot_id=previous_current,
            current_snapshot_id=previous_current,
        )

    snapshot_added = relation != "duplicate_snapshot"
    if relation == "new_match":
        selection_changed = True
        current_snapshot_id = snapshot.match_snapshot_id
        selections = (
            *catalog.current_matches,
            build_learning_corpus_current_match_selection_v1(
                match_id=snapshot.match_id,
                match_snapshot_id=snapshot.match_snapshot_id,
            ),
        )
    elif selection_mode == "select_imported":
        selection_changed = previous_current != snapshot.match_snapshot_id
        current_snapshot_id = snapshot.match_snapshot_id
        selections = (
            _replace_current_selection(
                catalog,
                match_id=snapshot.match_id,
                match_snapshot_id=snapshot.match_snapshot_id,
            )
            if selection_changed
            else catalog.current_matches
        )
    else:
        selection_changed = False
        current_snapshot_id = previous_current
        selections = catalog.current_matches

    if not snapshot_added and not selection_changed:
        return _change_result(
            operation="import_match_snapshot",
            status="unchanged",
            relation=relation,
            selection_mode=selection_mode,
            same_revision_resolution=same_revision_resolution,
            match_id=snapshot.match_id,
            match_snapshot_id=snapshot.match_snapshot_id,
            expected_revision=expected_revision,
            source_catalog=catalog,
            catalog=catalog,
            snapshot_added=False,
            selection_changed=False,
            previous_current_snapshot_id=previous_current,
            current_snapshot_id=current_snapshot_id,
        )

    entries = catalog.match_snapshots
    if snapshot_added:
        entries = (
            *entries,
            _build_learning_corpus_match_snapshot_catalog_entry_from_validated_v1(
                snapshot
            ),
        )
    changed_catalog = build_learning_corpus_catalog_v1(
        corpus_id=catalog.corpus_id,
        revision=catalog.revision + 1,
        match_snapshots=entries,
        current_matches=selections,
    )
    return _change_result(
        operation="import_match_snapshot",
        status="applied",
        relation=relation,
        selection_mode=selection_mode,
        same_revision_resolution=same_revision_resolution,
        match_id=snapshot.match_id,
        match_snapshot_id=snapshot.match_snapshot_id,
        expected_revision=expected_revision,
        source_catalog=catalog,
        catalog=changed_catalog,
        snapshot_added=snapshot_added,
        selection_changed=selection_changed,
        previous_current_snapshot_id=previous_current,
        current_snapshot_id=current_snapshot_id,
    )


def apply_learning_corpus_match_snapshot_import_v1(
    catalog: LearningCorpusCatalogV1,
    snapshot: LearningCorpusMatchSnapshotV1,
    *,
    expected_revision: int,
    selection_mode: str,
    same_revision_resolution: str,
) -> LearningCorpusCatalogChangeResultV1:
    """Purely applies one explicit Snapshot import to one immutable Catalog."""
    source = _require_catalog(catalog)
    candidate = _require_snapshot_type(snapshot)
    expected = _require_non_negative_integer(expected_revision, "expected_revision")
    _require_import_options(selection_mode, same_revision_resolution)
    if expected != source.revision:
        return _build_learning_corpus_import_revision_conflict_v1(
            source,
            expected_revision=expected,
            selection_mode=selection_mode,
            same_revision_resolution=same_revision_resolution,
            match_id=candidate.match_id,
            match_snapshot_id=candidate.match_snapshot_id,
        )
    classification = classify_learning_corpus_match_snapshot_v1(source, candidate)
    return _apply_learning_corpus_match_snapshot_import_v1(
        source,
        candidate,
        expected_revision=expected,
        selection_mode=selection_mode,
        same_revision_resolution=same_revision_resolution,
        classification=classification,
    )


def select_learning_corpus_current_match_snapshot_v1(
    catalog: LearningCorpusCatalogV1,
    *,
    match_id: str,
    match_snapshot_id: str,
    expected_revision: int,
) -> LearningCorpusCatalogChangeResultV1:
    """Purely selects one existing Snapshot without applying an automatic rule."""
    source = _require_catalog(catalog)
    requested_match_id = _require_identifier(match_id, "match_id")
    requested_snapshot_id = _require_hash(match_snapshot_id, "match_snapshot_id")
    expected = _require_non_negative_integer(expected_revision, "expected_revision")
    if expected != source.revision:
        return _change_result(
            operation="select_current_snapshot",
            status="revision_conflict",
            relation=None,
            selection_mode=None,
            same_revision_resolution=None,
            match_id=requested_match_id,
            match_snapshot_id=requested_snapshot_id,
            expected_revision=expected,
            source_catalog=source,
            catalog=source,
            snapshot_added=False,
            selection_changed=False,
            previous_current_snapshot_id=None,
            current_snapshot_id=None,
        )

    selection = next(
        (item for item in source.current_matches if item.match_id == requested_match_id),
        None,
    )
    if selection is None:
        raise ValueError("match_id must identify one represented logical Match.")
    entry = next(
        (
            item
            for item in source.match_snapshots
            if item.match_snapshot_id == requested_snapshot_id
        ),
        None,
    )
    if entry is None:
        raise ValueError("match_snapshot_id must identify one retained Catalog entry.")
    if entry.match_id != requested_match_id:
        raise ValueError("match_snapshot_id must belong to the supplied logical Match.")

    previous_current = selection.match_snapshot_id
    if previous_current == requested_snapshot_id:
        return _change_result(
            operation="select_current_snapshot",
            status="unchanged",
            relation=None,
            selection_mode=None,
            same_revision_resolution=None,
            match_id=requested_match_id,
            match_snapshot_id=requested_snapshot_id,
            expected_revision=expected,
            source_catalog=source,
            catalog=source,
            snapshot_added=False,
            selection_changed=False,
            previous_current_snapshot_id=previous_current,
            current_snapshot_id=previous_current,
        )

    changed_catalog = build_learning_corpus_catalog_v1(
        corpus_id=source.corpus_id,
        revision=source.revision + 1,
        match_snapshots=source.match_snapshots,
        current_matches=_replace_current_selection(
            source,
            match_id=requested_match_id,
            match_snapshot_id=requested_snapshot_id,
        ),
    )
    return _change_result(
        operation="select_current_snapshot",
        status="applied",
        relation=None,
        selection_mode=None,
        same_revision_resolution=None,
        match_id=requested_match_id,
        match_snapshot_id=requested_snapshot_id,
        expected_revision=expected,
        source_catalog=source,
        catalog=changed_catalog,
        snapshot_added=False,
        selection_changed=True,
        previous_current_snapshot_id=previous_current,
        current_snapshot_id=requested_snapshot_id,
    )
