import json
import tomllib
from pathlib import Path

import pytest
from test_learning_corpus_match_snapshot import (
    _annotated_workspace,
    _same_revision_changed_workspaces,
    _snapshot_for_workspace,
)
from test_match_workspace_contracts import _definition

import skat_ai
import skat_ai.api.v1 as api_v1
from scripts.validate_generated_outputs_schema import SCENARIOS
from skat_ai.api.v1.contracts import WorkflowV1
from skat_ai.learning_corpus_catalog import (
    build_learning_corpus_catalog_v1,
    build_learning_corpus_current_match_selection_v1,
    build_learning_corpus_match_snapshot_catalog_entry_v1,
    classify_learning_corpus_match_snapshot_v1,
    create_empty_learning_corpus_catalog_v1,
)
from skat_ai.match_workspace_contracts import create_match_workspace_v1
from skat_ai.match_workspace_operations import mark_match_workspace_passed_deal_v1
from skat_ai.training_dataset import (
    TRAINING_DATASET_SCHEMA_VERSION,
    TRAINING_FEATURE_GENERATION_VERSION,
    TRAINING_TARGET,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _entry(snapshot):
    return build_learning_corpus_match_snapshot_catalog_entry_v1(snapshot)


def _selection(snapshot):
    return build_learning_corpus_current_match_selection_v1(
        match_id=snapshot.match_id,
        match_snapshot_id=snapshot.match_snapshot_id,
    )


def _catalog(*snapshots, current):
    return build_learning_corpus_catalog_v1(
        corpus_id="corpus-171",
        revision=4,
        match_snapshots=tuple(_entry(snapshot) for snapshot in snapshots),
        current_matches=tuple(_selection(snapshot) for snapshot in current),
    )


def _revision_snapshots():
    definition = _definition()
    revision_zero_workspace = create_match_workspace_v1(definition)
    revision_one_workspace = mark_match_workspace_passed_deal_v1(
        revision_zero_workspace,
        match_position=1,
        game_timecode=None,
        expected_revision=0,
    ).workspace
    revision_two_workspace = mark_match_workspace_passed_deal_v1(
        revision_one_workspace,
        match_position=2,
        game_timecode=None,
        expected_revision=1,
    ).workspace
    return tuple(
        _snapshot_for_workspace(workspace)[1]
        for workspace in (
            revision_zero_workspace,
            revision_one_workspace,
            revision_two_workspace,
        )
    )


def test_catalog_entry_summarizes_snapshot_without_embedding_workspace() -> None:
    _, snapshot = _snapshot_for_workspace(_annotated_workspace())
    entry = _entry(snapshot)
    assert entry.match_snapshot_id == snapshot.match_snapshot_id
    assert entry.match_id == snapshot.match_id
    assert entry.workspace_revision == snapshot.workspace_revision
    assert entry.source_workspace_fingerprint == snapshot.source_workspace_fingerprint
    assert entry.source_content_fingerprint == snapshot.source_content_fingerprint
    assert entry.player_ids == ("player-a", "player-b", "player-c")
    assert (
        entry.observed_game_count,
        entry.passed_deal_count,
        entry.empty_slot_count,
    ) == (1, 0, 35)
    assert (
        entry.decision_count,
        entry.commentary_count,
        entry.response_link_count,
    ) == (2, 1, 1)
    serialized = entry.to_dict()
    assert "workspace" not in serialized
    assert "path" not in serialized
    assert "report" not in serialized
    assert "dataset" not in serialized


def test_empty_catalog_is_revision_zero_and_has_no_automatic_selection() -> None:
    catalog = create_empty_learning_corpus_catalog_v1("corpus-171")
    assert catalog.corpus_id == "corpus-171"
    assert catalog.revision == 0
    assert catalog.match_snapshots == ()
    assert catalog.current_matches == ()
    assert catalog.to_dict() == {
        "learning_corpus_catalog_version": 1,
        "corpus_id": "corpus-171",
        "revision": 0,
        "match_snapshots": [],
        "current_matches": [],
    }
    with pytest.raises(ValueError, match="non-negative"):
        build_learning_corpus_catalog_v1(
            corpus_id="corpus-171",
            revision=-1,
            match_snapshots=(),
            current_matches=(),
        )


def test_catalog_canonicalizes_multiple_matches_revisions_and_selections() -> None:
    revision_zero, revision_one, _ = _revision_snapshots()
    other_definition = _definition(match_id="match-other")
    _, other = _snapshot_for_workspace(create_match_workspace_v1(other_definition))
    catalog = build_learning_corpus_catalog_v1(
        corpus_id="corpus-171",
        revision=9,
        match_snapshots=(_entry(other), _entry(revision_one), _entry(revision_zero)),
        current_matches=(_selection(other), _selection(revision_zero)),
    )
    assert tuple(
        (item.match_id, item.workspace_revision) for item in catalog.match_snapshots
    ) == (
        (revision_zero.match_id, 0),
        (revision_zero.match_id, 1),
        (other.match_id, 0),
    )
    assert tuple(item.match_id for item in catalog.current_matches) == (
        revision_zero.match_id,
        other.match_id,
    )
    assert catalog.current_matches[0].match_snapshot_id == revision_zero.match_snapshot_id


def test_catalog_requires_unique_identity_and_exactly_one_valid_selection_per_match() -> None:
    revision_zero, revision_one, _ = _revision_snapshots()
    entry_zero = _entry(revision_zero)
    entry_one = _entry(revision_one)
    with pytest.raises(ValueError, match="Snapshot IDs must be unique"):
        build_learning_corpus_catalog_v1(
            corpus_id="corpus-171",
            revision=1,
            match_snapshots=(entry_zero, entry_zero),
            current_matches=(_selection(revision_zero),),
        )
    with pytest.raises(ValueError, match="exactly one current selection"):
        build_learning_corpus_catalog_v1(
            corpus_id="corpus-171",
            revision=1,
            match_snapshots=(entry_zero, entry_one),
            current_matches=(),
        )
    wrong_match_selection = build_learning_corpus_current_match_selection_v1(
        match_id="wrong-match",
        match_snapshot_id=revision_zero.match_snapshot_id,
    )
    with pytest.raises(ValueError, match="represented Match"):
        build_learning_corpus_catalog_v1(
            corpus_id="corpus-171",
            revision=1,
            match_snapshots=(entry_zero,),
            current_matches=(wrong_match_selection,),
        )


def test_catalog_validation_rejects_forged_contract_versions() -> None:
    _, snapshot = _snapshot_for_workspace(create_match_workspace_v1(_definition()))
    entry = _entry(snapshot)
    selection = _selection(snapshot)
    object.__setattr__(entry, "learning_corpus_catalog_version", 2)
    with pytest.raises(ValueError, match="learning_corpus_catalog_version"):
        build_learning_corpus_catalog_v1(
            corpus_id="corpus-171",
            revision=1,
            match_snapshots=(entry,),
            current_matches=(selection,),
        )

    entry = _entry(snapshot)
    object.__setattr__(selection, "learning_corpus_catalog_version", 2)
    with pytest.raises(ValueError, match="learning_corpus_catalog_version"):
        build_learning_corpus_catalog_v1(
            corpus_id="corpus-171",
            revision=1,
            match_snapshots=(entry,),
            current_matches=(selection,),
        )

    selection = _selection(snapshot)
    catalog = build_learning_corpus_catalog_v1(
        corpus_id="corpus-171",
        revision=1,
        match_snapshots=(entry,),
        current_matches=(selection,),
    )
    object.__setattr__(catalog, "learning_corpus_catalog_version", 2)
    with pytest.raises(ValueError, match="learning_corpus_catalog_version"):
        classify_learning_corpus_match_snapshot_v1(catalog, snapshot)

    catalog = _catalog(snapshot, current=(snapshot,))
    classification = classify_learning_corpus_match_snapshot_v1(catalog, snapshot)
    object.__setattr__(
        classification,
        "learning_corpus_snapshot_classification_version",
        2,
    )
    with pytest.raises(
        ValueError,
        match="learning_corpus_snapshot_classification_version",
    ):
        classification._validate()


def test_same_revision_distinct_content_entries_are_retained_with_explicit_current() -> None:
    first_workspace, changed_workspace = _same_revision_changed_workspaces()
    _, first = _snapshot_for_workspace(first_workspace)
    _, changed = _snapshot_for_workspace(changed_workspace)
    catalog = _catalog(first, changed, current=(first,))
    assert len(catalog.match_snapshots) == 2
    assert tuple(item.workspace_revision for item in catalog.match_snapshots) == (1, 1)
    assert catalog.current_matches[0].match_snapshot_id == first.match_snapshot_id


def test_classification_precedence_covers_new_duplicate_conflict_newer_and_older() -> None:
    revision_zero, revision_one, revision_two = _revision_snapshots()
    catalog = _catalog(revision_zero, revision_one, current=(revision_one,))

    duplicate = classify_learning_corpus_match_snapshot_v1(catalog, revision_zero)
    assert duplicate.relation == "duplicate_snapshot"
    assert duplicate.current_snapshot_id == revision_one.match_snapshot_id
    assert duplicate.same_match_snapshot_ids == (
        revision_zero.match_snapshot_id,
        revision_one.match_snapshot_id,
    )
    assert duplicate.same_revision_snapshot_ids == (revision_zero.match_snapshot_id,)

    newer = classify_learning_corpus_match_snapshot_v1(catalog, revision_two)
    assert newer.relation == "newer_revision"
    assert newer.current_workspace_revision == 1

    catalog_with_newer_current = _catalog(
        revision_zero,
        revision_one,
        revision_two,
        current=(revision_two,),
    )
    older = classify_learning_corpus_match_snapshot_v1(
        catalog_with_newer_current,
        revision_one,
    )
    assert older.relation == "duplicate_snapshot"
    new_older_workspace = mark_match_workspace_passed_deal_v1(
        create_match_workspace_v1(_definition()),
        match_position=3,
        game_timecode=None,
        expected_revision=0,
    ).workspace
    _, new_older = _snapshot_for_workspace(new_older_workspace)
    older = classify_learning_corpus_match_snapshot_v1(
        catalog_with_newer_current,
        new_older,
    )
    assert older.relation == "same_revision_content_conflict"

    new_match_definition = _definition(match_id="new-logical-match")
    _, new_match = _snapshot_for_workspace(
        create_match_workspace_v1(new_match_definition)
    )
    classified_new = classify_learning_corpus_match_snapshot_v1(catalog, new_match)
    assert classified_new.relation == "new_match"
    assert classified_new.current_snapshot_id is None
    assert classified_new.same_match_snapshot_ids == ()


def test_classification_reports_older_for_unseen_revision_below_current() -> None:
    revision_zero, revision_one, revision_two = _revision_snapshots()
    catalog = _catalog(revision_two, current=(revision_two,))
    older = classify_learning_corpus_match_snapshot_v1(catalog, revision_one)
    assert older.relation == "older_revision"
    assert older.current_workspace_revision == 2
    assert older.same_revision_snapshot_ids == ()
    assert revision_zero.workspace_revision == 0


def test_same_revision_conflict_precedes_newer_or_older_comparison() -> None:
    first_workspace, changed_workspace = _same_revision_changed_workspaces()
    _, first = _snapshot_for_workspace(first_workspace)
    _, changed = _snapshot_for_workspace(changed_workspace)
    catalog = _catalog(first, current=(first,))
    classification = classify_learning_corpus_match_snapshot_v1(catalog, changed)
    assert classification.relation == "same_revision_content_conflict"
    assert classification.same_revision_snapshot_ids == (first.match_snapshot_id,)


def test_catalog_and_snapshot_are_private_internal_compatibility_additions_only() -> None:
    assert not hasattr(skat_ai, "LearningCorpusCatalogV1")
    assert not hasattr(api_v1, "LearningCorpusCatalogV1")
    assert len(WorkflowV1) == 7
    assert TRAINING_DATASET_SCHEMA_VERSION == 1
    assert TRAINING_FEATURE_GENERATION_VERSION == 1
    assert TRAINING_TARGET == "actual_card_played"
    assert len(SCENARIOS) == 94

    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["project"]["version"] == "0.16.0"
    assert pyproject["project"]["scripts"] == {"skat-ai": "skat_ai.cli:main"}
    assert len(tuple((PROJECT_ROOT / "schemas").glob("*.schema.json"))) == 69
    assert len(tuple((PROJECT_ROOT / "src/skat_ai/schema_resources").glob("*.schema.json"))) == 69
    session_examples = {
        path.name
        for path in (PROJECT_ROOT / "examples").glob("session_*.json")
    }
    assert session_examples == {
        "session_create_live.json",
        "session_create_retrospective.json",
        "session_command_record_play.json",
        "session_correction_record_play.json",
        "session_live_persistence.json",
        "session_retrospective_persistence.json",
    }
    assert not tuple((PROJECT_ROOT / "schemas").glob("*learning_corpus*.schema.json"))
    assert not tuple((PROJECT_ROOT / "examples").glob("*learning_corpus*.json"))
    assert json.loads((PROJECT_ROOT / "schemas/input.schema.json").read_text())["$id"]
