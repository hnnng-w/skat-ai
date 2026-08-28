import builtins
from dataclasses import replace

import pytest
from test_match_workspace_contracts import (
    _annotated_observed_game,
    _complete_observed_game,
    _definition,
    _observed_game,
    _set_game,
)
from test_match_workspace_materialization import _all_passed_workspace
from test_match_workspace_persistence_codec import _rich_document

import skatmind.application.execution as application_execution
import skatmind.learning_corpus_match_snapshot as snapshot_module
import skatmind.training_dataset as training_dataset_module
from skatmind.capture_web.report_store import MatchAnalysisReportStoreV1
from skatmind.errors import SkatMindInvariantError
from skatmind.learning_corpus_match_snapshot import (
    build_learning_corpus_match_snapshot_v1,
    validate_learning_corpus_match_snapshot_v1,
)
from skatmind.learning_corpus_references import (
    build_learning_corpus_game_content_fingerprint_v1,
)
from skatmind.match_workspace_contracts import create_match_workspace_v1
from skatmind.match_workspace_operations import (
    mark_match_workspace_passed_deal_v1,
    set_match_workspace_observed_game_v1,
)
from skatmind.match_workspace_persistence import _build_match_workspace_file_bytes_v1
from skatmind.match_workspace_persistence_codec import (
    build_match_workspace_persistence_document_v1,
)


def _snapshot_for_workspace(workspace):
    document = build_match_workspace_persistence_document_v1(workspace)
    return document, build_learning_corpus_match_snapshot_v1(document)


def _annotated_workspace():
    definition = _definition()
    return _set_game(
        create_match_workspace_v1(definition),
        _annotated_observed_game(definition),
    )


def _same_revision_changed_workspaces():
    definition = _definition()
    source = create_match_workspace_v1(definition)
    first_game = _annotated_observed_game(definition)
    changed_commentary = replace(
        first_game.commentaries[0],
        text="Corrected exact source text.",
    )
    second_game = _observed_game(
        definition,
        match_position=3,
        game_id=first_game.game_id,
        declarer_player_id=first_game.declarer_player_id,
        declaration=first_game.declaration,
        plays=first_game.plays,
        commentaries=(changed_commentary,),
        response_links=first_game.response_links,
    )
    first = set_match_workspace_observed_game_v1(
        source,
        first_game,
        expected_revision=0,
    ).workspace
    second = set_match_workspace_observed_game_v1(
        source,
        second_game,
        expected_revision=0,
    ).workspace
    assert first.revision == second.revision == 1
    return first, second


def test_snapshot_requires_exact_document_strictly_resumes_and_retains_exact_source() -> None:
    workspace = _annotated_workspace()
    document, snapshot = _snapshot_for_workspace(workspace)
    assert snapshot.workspace is document.workspace
    assert snapshot.match_id == workspace.match_definition.match_id
    assert snapshot.workspace_revision == workspace.revision
    assert snapshot.source_workspace_fingerprint == document.workspace_fingerprint
    assert snapshot.source_content_fingerprint == document.content_fingerprint
    validate_learning_corpus_match_snapshot_v1(snapshot)
    with pytest.raises(ValueError, match="exact MatchWorkspacePersistenceDocumentV1"):
        build_learning_corpus_match_snapshot_v1(document.to_dict())


def test_inconsistent_internal_source_document_raises_invariant_error() -> None:
    document = build_match_workspace_persistence_document_v1(
        create_match_workspace_v1(_definition())
    )
    object.__setattr__(document, "content_fingerprint", "0" * 64)
    with pytest.raises(SkatMindInvariantError, match="inconsistent"):
        build_learning_corpus_match_snapshot_v1(document)


@pytest.mark.parametrize(
    ("workspace_factory", "expected"),
    (
        (
            lambda: create_match_workspace_v1(_definition()),
            (0, 0, 0, 0),
        ),
        (
            _annotated_workspace,
            (1, 2, 1, 1),
        ),
        (
            lambda: _set_game(
                create_match_workspace_v1(_definition()),
                _complete_observed_game(_definition()),
            ),
            (1, 30, 0, 0),
        ),
        (
            _all_passed_workspace,
            (0, 0, 0, 0),
        ),
    ),
)
def test_empty_partial_complete_and_all_passed_snapshot_cardinalities(
    workspace_factory,
    expected,
) -> None:
    _, snapshot = _snapshot_for_workspace(workspace_factory())
    assert len(snapshot.player_observations) == 3
    assert (
        len(snapshot.game_references),
        len(snapshot.decision_references),
        len(snapshot.commentary_references),
        len(snapshot.response_references),
    ) == expected


def test_snapshot_identity_is_deterministic_and_changed_source_content_is_distinct() -> None:
    first_workspace, changed_workspace = _same_revision_changed_workspaces()
    first_document, first = _snapshot_for_workspace(first_workspace)
    repeated = build_learning_corpus_match_snapshot_v1(first_document)
    _, changed = _snapshot_for_workspace(changed_workspace)
    assert repeated == first
    assert repeated.match_snapshot_id == first.match_snapshot_id
    assert changed.workspace_revision == first.workspace_revision
    assert changed.source_content_fingerprint != first.source_content_fingerprint
    assert changed.match_snapshot_id != first.match_snapshot_id
    assert changed.game_references[0].game_content_fingerprint != (
        first.game_references[0].game_content_fingerprint
    )
    assert changed.game_references[0].game_reference_id != (
        first.game_references[0].game_reference_id
    )
    assert changed.decision_references[0].decision_reference_id != (
        first.decision_references[0].decision_reference_id
    )
    assert changed.commentary_references[0].commentary_reference_id != (
        first.commentary_references[0].commentary_reference_id
    )
    assert changed.response_references[0].response_reference_id != (
        first.response_references[0].response_reference_id
    )


def test_player_observations_preserve_table_order_exact_ids_and_match_metadata() -> None:
    definition = _definition()
    _, snapshot = _snapshot_for_workspace(create_match_workspace_v1(definition))
    assert tuple(item.player_id for item in snapshot.player_observations) == (
        "player-a",
        "player-b",
        "player-c",
    )
    assert tuple(item.table_place for item in snapshot.player_observations) == (
        "place_1",
        "place_2",
        "place_3",
    )
    assert tuple(item.player_label for item in snapshot.player_observations) == tuple(
        participant.player_label for participant in definition.participants
    )
    assert all(
        item.game_platform == definition.game_platform
        for item in snapshot.player_observations
    )
    assert tuple(item.statistics_snapshot_id for item in snapshot.player_observations) == (
        None,
        None,
        None,
    )
    assert len({item.player_observation_id for item in snapshot.player_observations}) == 3


def test_player_observations_retain_exact_match_bound_statistics_snapshot_ids() -> None:
    document = _rich_document()
    snapshot = build_learning_corpus_match_snapshot_v1(document)
    expected = tuple(
        None
        if participant.statistics_snapshot is None
        else participant.statistics_snapshot.snapshot_id
        for participant in document.workspace.match_definition.participants
    )
    assert tuple(
        item.statistics_snapshot_id for item in snapshot.player_observations
    ) == expected


def test_game_decision_commentary_and_response_references_preserve_source_order() -> None:
    workspace = _annotated_workspace()
    _, snapshot = _snapshot_for_workspace(workspace)
    game = workspace.slots[2].observed_game
    assert game is not None
    game_reference = snapshot.game_references[0]
    assert game_reference.match_position == 3
    assert (game_reference.match_id, game_reference.game_id) == (
        game.match_id,
        game.game_id,
    )
    assert game_reference.game_content_fingerprint == (
        build_learning_corpus_game_content_fingerprint_v1(game)
    )
    assert tuple(item.decision_index for item in snapshot.decision_references) == tuple(
        item.decision_index for item in game.plays
    )
    assert tuple(item.acting_player_id for item in snapshot.decision_references) == tuple(
        item.player_id for item in game.plays
    )
    assert tuple(item.commentary_id for item in snapshot.commentary_references) == tuple(
        item.commentary_id for item in game.commentaries
    )
    assert tuple(item.link_id for item in snapshot.response_references) == tuple(
        item.link_id for item in game.response_links
    )
    assert game_reference.decision_reference_ids == tuple(
        item.decision_reference_id for item in snapshot.decision_references
    )
    assert game_reference.commentary_reference_ids == tuple(
        item.commentary_reference_id for item in snapshot.commentary_references
    )
    assert game_reference.response_reference_ids == tuple(
        item.response_reference_id for item in snapshot.response_references
    )
    assert snapshot.commentary_references[0].subject_decision_reference_id == (
        snapshot.decision_references[0].decision_reference_id
    )
    assert snapshot.response_references[0].commentary_reference_id == (
        snapshot.commentary_references[0].commentary_reference_id
    )
    assert snapshot.response_references[0].response_decision_reference_id == (
        snapshot.decision_references[1].decision_reference_id
    )


def test_empty_and_passed_slots_never_create_game_references() -> None:
    workspace = create_match_workspace_v1(_definition())
    workspace = mark_match_workspace_passed_deal_v1(
        workspace,
        match_position=1,
        game_timecode=None,
        expected_revision=0,
    ).workspace
    _, snapshot = _snapshot_for_workspace(workspace)
    assert snapshot.game_references == ()
    assert snapshot.decision_references == ()
    assert snapshot.commentary_references == ()
    assert snapshot.response_references == ()


def test_snapshot_validation_rejects_broken_closed_reference_reconciliation() -> None:
    _, snapshot = _snapshot_for_workspace(_annotated_workspace())
    object.__setattr__(snapshot, "response_references", ())
    with pytest.raises(SkatMindInvariantError, match="exact derivation"):
        validate_learning_corpus_match_snapshot_v1(snapshot)


def test_snapshot_has_no_path_or_import_time_and_preserves_original_commentary() -> None:
    workspace = _annotated_workspace()
    _, snapshot = _snapshot_for_workspace(workspace)
    serialized = snapshot.to_dict()

    def collect_keys(value):
        if isinstance(value, dict):
            return set(value) | set().union(*(collect_keys(item) for item in value.values()))
        if isinstance(value, list):
            return set().union(*(collect_keys(item) for item in value))
        return set()

    keys = collect_keys(serialized)
    assert not {"path", "file_path", "import_time", "imported_at"}.intersection(keys)
    source_text = workspace.slots[2].observed_game.commentaries[0].text
    assert serialized["workspace"]["slots"][2]["observed_game"]["commentaries"][0][
        "text"
    ] == source_text
    assert "text" not in serialized["commentary_references"][0]


def test_snapshot_build_performs_no_io_analysis_report_import_or_dataset_generation(
    monkeypatch,
) -> None:
    workspace = _annotated_workspace()
    document = build_match_workspace_persistence_document_v1(workspace)
    original_bytes = _build_match_workspace_file_bytes_v1(document)
    report_store = MatchAnalysisReportStoreV1()
    original_generation = report_store.generation

    def fail(*_args, **_kwargs):
        raise AssertionError("Forbidden execution boundary was called.")

    monkeypatch.setattr(builtins, "open", fail)
    monkeypatch.setattr(application_execution, "execute_application_invocation", fail)
    monkeypatch.setattr(training_dataset_module, "build_training_dataset_summary", fail)
    snapshot = build_learning_corpus_match_snapshot_v1(document)

    assert snapshot.workspace is workspace
    assert _build_match_workspace_file_bytes_v1(document) == original_bytes
    assert len(report_store) == 0
    assert report_store.generation == original_generation
    assert "MatchAnalysisReportV1" not in snapshot_module.__dict__
    assert "TrainingDatasetInput" not in snapshot_module.__dict__
    assert "Path" not in snapshot_module.__dict__


def test_snapshot_build_resumes_once_and_fingerprints_each_observed_game_once(
    monkeypatch,
) -> None:
    document = build_match_workspace_persistence_document_v1(_annotated_workspace())
    original_resume = snapshot_module.resume_match_workspace_document_v1
    original_game_fingerprint = (
        snapshot_module.build_learning_corpus_game_content_fingerprint_v1
    )
    counts = {"resume": 0, "game_fingerprint": 0}

    def counted_resume(value):
        counts["resume"] += 1
        return original_resume(value)

    def counted_game_fingerprint(value, *, _legacy_identity=False):
        counts["game_fingerprint"] += 1
        return original_game_fingerprint(value, _legacy_identity=_legacy_identity)

    monkeypatch.setattr(
        snapshot_module,
        "resume_match_workspace_document_v1",
        counted_resume,
    )
    monkeypatch.setattr(
        snapshot_module,
        "build_learning_corpus_game_content_fingerprint_v1",
        counted_game_fingerprint,
    )
    build_learning_corpus_match_snapshot_v1(document)
    assert counts == {"resume": 1, "game_fingerprint": 1}


def test_player_case_is_not_merged_or_normalized() -> None:
    definition = _definition()
    changed_participants = tuple(
        replace(
            participant,
            player_id=(
                "Player-A"
                if participant.player_id == "player-a"
                else participant.player_id
            ),
        )
        for participant in definition.participants
    )
    changed_definition = replace(
        definition,
        match_id="match-case-sensitive",
        participants=changed_participants,
        perspective_player_id="Player-A",
    )
    _, original = _snapshot_for_workspace(create_match_workspace_v1(definition))
    _, changed = _snapshot_for_workspace(create_match_workspace_v1(changed_definition))
    assert original.player_observations[0].player_id == "player-a"
    assert changed.player_observations[0].player_id == "Player-A"
    assert original.player_observations[0].player_observation_id != (
        changed.player_observations[0].player_observation_id
    )
