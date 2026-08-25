import json
from dataclasses import fields

import pytest
from test_historical_game import build_historical_input
from test_learning_corpus_human_evidence import _rich_snapshot, _store
from test_learning_dataset_v2 import _complete_rich_store, _unavailable_store
from test_match_workspace_contracts import (
    _complete_observed_game,
    _definition,
    _observed_game,
    _set_game,
)
from test_observed_game_contracts import (
    declaration_from_historical,
    observed_plays_from_historical,
)

import skat_ai.learning_corpus_tactical_motif_builder as tactical_builder_module
from skat_ai.learning_corpus_match_snapshot import (
    build_learning_corpus_match_snapshot_v1,
)
from skat_ai.learning_corpus_player_catalog import (
    build_learning_corpus_player_catalog_v1,
)
from skat_ai.learning_corpus_tactical_motif_builder import (
    build_learning_corpus_tactical_motif_evidence_collection_v1,
)
from skat_ai.learning_corpus_tactical_motif_evidence import (
    LEARNING_CORPUS_TACTICAL_MOTIF_COLLECTION_FINGERPRINT_DOMAIN,
    LEARNING_CORPUS_TACTICAL_MOTIF_COLLECTION_STATUSES,
    LEARNING_CORPUS_TACTICAL_MOTIF_COLLECTION_VERSION,
    LEARNING_CORPUS_TACTICAL_MOTIF_COVERAGE_POLICY,
    LEARNING_CORPUS_TACTICAL_MOTIF_DATASET_POLICY,
    LEARNING_CORPUS_TACTICAL_MOTIF_DECISION_POLICY,
    LEARNING_CORPUS_TACTICAL_MOTIF_EVIDENCE_ID_DOMAIN,
    LEARNING_CORPUS_TACTICAL_MOTIF_EVIDENCE_SEPARATION_POLICY,
    LEARNING_CORPUS_TACTICAL_MOTIF_EVIDENCE_VERSION,
    LEARNING_CORPUS_TACTICAL_MOTIF_EXPORT_POLICY,
    LEARNING_CORPUS_TACTICAL_MOTIF_IDENTITY_POLICY,
    LEARNING_CORPUS_TACTICAL_MOTIF_OBSERVATION_POLICY,
    LEARNING_CORPUS_TACTICAL_MOTIF_PREPARATION_POLICY,
    LEARNING_CORPUS_TACTICAL_MOTIF_PUBLIC_POLICY,
    LEARNING_CORPUS_TACTICAL_MOTIF_RECURRENCE_POLICY,
    LEARNING_CORPUS_TACTICAL_MOTIF_SKIPPED_DECISION_ID_DOMAIN,
    LEARNING_CORPUS_TACTICAL_MOTIF_SKIPPED_DECISION_VERSION,
    LEARNING_CORPUS_TACTICAL_MOTIF_SOURCE_POLICY,
    LEARNING_CORPUS_TACTICAL_MOTIF_SUMMARY_POLICY,
    LearningCorpusSkippedTacticalMotifDecisionV1,
    LearningCorpusTacticalMotifEvidenceCollectionV1,
    LearningCorpusTacticalMotifEvidenceV1,
)
from skat_ai.learning_corpus_tactical_motif_export import (
    LEARNING_CORPUS_TACTICAL_MOTIF_CROSS_GAME_SUMMARY_DOCUMENT_KIND,
    LEARNING_CORPUS_TACTICAL_MOTIF_EVIDENCE_DOCUMENT_KIND,
    LEARNING_CORPUS_TACTICAL_MOTIF_EVIDENCE_EXPORT_ID_DOMAIN,
    LEARNING_CORPUS_TACTICAL_MOTIF_EVIDENCE_EXPORT_VERSION,
    LEARNING_CORPUS_TACTICAL_MOTIF_SUMMARY_EXPORT_ID_DOMAIN,
    LEARNING_CORPUS_TACTICAL_MOTIF_SUMMARY_EXPORT_VERSION,
    build_learning_corpus_tactical_motif_cross_game_summary_export_v1,
    build_learning_corpus_tactical_motif_evidence_export_v1,
    serialize_learning_corpus_tactical_motif_cross_game_summary_export_v1,
    serialize_learning_corpus_tactical_motif_evidence_export_v1,
)
from skat_ai.learning_corpus_tactical_motif_summary import (
    LEARNING_CORPUS_TACTICAL_MOTIF_CROSS_GAME_LIMITATIONS,
    LEARNING_CORPUS_TACTICAL_MOTIF_CROSS_GAME_SUMMARY_FINGERPRINT_DOMAIN,
    LEARNING_CORPUS_TACTICAL_MOTIF_CROSS_GAME_SUMMARY_VERSION,
    LEARNING_CORPUS_TACTICAL_MOTIF_PLAYER_SUMMARY_ID_DOMAIN,
    LEARNING_CORPUS_TACTICAL_MOTIF_PLAYER_SUMMARY_VERSION,
    LEARNING_CORPUS_TACTICAL_MOTIF_RECURRENCE_ID_DOMAIN,
    LEARNING_CORPUS_TACTICAL_MOTIF_RECURRENCE_SCOPES,
    LEARNING_CORPUS_TACTICAL_MOTIF_RECURRENCE_VERSION,
    LEARNING_CORPUS_TACTICAL_MOTIF_SCOPE_SUMMARY_ID_DOMAIN,
    LEARNING_CORPUS_TACTICAL_MOTIF_SCOPE_SUMMARY_VERSION,
    LearningCorpusTacticalMotifCrossGameSummaryV1,
    LearningCorpusTacticalMotifPlayerSummaryV1,
    LearningCorpusTacticalMotifRecurrenceV1,
    LearningCorpusTacticalMotifScopeSummaryV1,
    build_learning_corpus_tactical_motif_cross_game_summary_v1,
)
from skat_ai.match_workspace_contracts import create_match_workspace_v1
from skat_ai.match_workspace_persistence_codec import (
    build_match_workspace_persistence_document_v1,
)
from skat_ai.tactical_motif_contracts import (
    TACTICAL_MOTIF_FAMILIES,
    TACTICAL_MOTIF_TYPES,
)


def _collection_and_summary(store):
    collection = build_learning_corpus_tactical_motif_evidence_collection_v1(store)
    summary = build_learning_corpus_tactical_motif_cross_game_summary_v1(
        collection,
        build_learning_corpus_player_catalog_v1(store),
    )
    return collection, summary


def test_versions_statuses_policies_domains_and_contract_fields_are_exact() -> None:
    assert (
        LEARNING_CORPUS_TACTICAL_MOTIF_EVIDENCE_VERSION,
        LEARNING_CORPUS_TACTICAL_MOTIF_SKIPPED_DECISION_VERSION,
        LEARNING_CORPUS_TACTICAL_MOTIF_COLLECTION_VERSION,
        LEARNING_CORPUS_TACTICAL_MOTIF_SCOPE_SUMMARY_VERSION,
        LEARNING_CORPUS_TACTICAL_MOTIF_PLAYER_SUMMARY_VERSION,
        LEARNING_CORPUS_TACTICAL_MOTIF_RECURRENCE_VERSION,
        LEARNING_CORPUS_TACTICAL_MOTIF_CROSS_GAME_SUMMARY_VERSION,
        LEARNING_CORPUS_TACTICAL_MOTIF_EVIDENCE_EXPORT_VERSION,
        LEARNING_CORPUS_TACTICAL_MOTIF_SUMMARY_EXPORT_VERSION,
    ) == (1,) * 9
    assert LEARNING_CORPUS_TACTICAL_MOTIF_COLLECTION_STATUSES == (
        "empty",
        "partial",
        "complete",
    )
    assert LEARNING_CORPUS_TACTICAL_MOTIF_RECURRENCE_SCOPES == (
        "single_game_only",
        "multiple_games_one_match",
        "multiple_matches",
    )
    assert (
        LEARNING_CORPUS_TACTICAL_MOTIF_SOURCE_POLICY,
        LEARNING_CORPUS_TACTICAL_MOTIF_DECISION_POLICY,
        LEARNING_CORPUS_TACTICAL_MOTIF_OBSERVATION_POLICY,
        LEARNING_CORPUS_TACTICAL_MOTIF_IDENTITY_POLICY,
        LEARNING_CORPUS_TACTICAL_MOTIF_COVERAGE_POLICY,
        LEARNING_CORPUS_TACTICAL_MOTIF_RECURRENCE_POLICY,
        LEARNING_CORPUS_TACTICAL_MOTIF_SUMMARY_POLICY,
        LEARNING_CORPUS_TACTICAL_MOTIF_EVIDENCE_SEPARATION_POLICY,
        LEARNING_CORPUS_TACTICAL_MOTIF_DATASET_POLICY,
        LEARNING_CORPUS_TACTICAL_MOTIF_PREPARATION_POLICY,
        LEARNING_CORPUS_TACTICAL_MOTIF_EXPORT_POLICY,
        LEARNING_CORPUS_TACTICAL_MOTIF_PUBLIC_POLICY,
    ) == (
        "explicit_current_match_snapshots_only",
        "safe_reconstructed_decision_or_explicit_skip",
        "reuse_exact_tactical_detector_without_search_or_coaching",
        "exact_snapshot_game_and_decision_reference_identity",
        "every_observed_decision_is_evidence_or_skipped",
        "distinct_game_and_match_counts_without_trait_inference",
        "exact_counts_without_rates_quality_or_significance",
        "tactical_human_and_strategy_evidence_remain_separate",
        "no_learning_dataset_v2_contract_or_record_mutation",
        "process_local_explicit_generation_safe_preparation",
        "deterministic_path_free_private_json",
        "private_corpus_downloads_without_public_schema_or_api",
    )
    assert (
        LEARNING_CORPUS_TACTICAL_MOTIF_EVIDENCE_ID_DOMAIN,
        LEARNING_CORPUS_TACTICAL_MOTIF_SKIPPED_DECISION_ID_DOMAIN,
        LEARNING_CORPUS_TACTICAL_MOTIF_COLLECTION_FINGERPRINT_DOMAIN,
        LEARNING_CORPUS_TACTICAL_MOTIF_SCOPE_SUMMARY_ID_DOMAIN,
        LEARNING_CORPUS_TACTICAL_MOTIF_PLAYER_SUMMARY_ID_DOMAIN,
        LEARNING_CORPUS_TACTICAL_MOTIF_RECURRENCE_ID_DOMAIN,
        LEARNING_CORPUS_TACTICAL_MOTIF_CROSS_GAME_SUMMARY_FINGERPRINT_DOMAIN,
        LEARNING_CORPUS_TACTICAL_MOTIF_EVIDENCE_EXPORT_ID_DOMAIN,
        LEARNING_CORPUS_TACTICAL_MOTIF_SUMMARY_EXPORT_ID_DOMAIN,
    ) == (
        b"skat-ai\0learning_corpus_tactical_motif_evidence_v1\0",
        b"skat-ai\0learning_corpus_tactical_motif_skipped_decision_v1\0",
        b"skat-ai\0learning_corpus_tactical_motif_collection_v1\0",
        b"skat-ai\0learning_corpus_tactical_motif_scope_summary_v1\0",
        b"skat-ai\0learning_corpus_tactical_motif_player_summary_v1\0",
        b"skat-ai\0learning_corpus_tactical_motif_recurrence_v1\0",
        b"skat-ai\0learning_corpus_tactical_motif_cross_game_summary_v1\0",
        b"skat-ai\0learning_corpus_tactical_motif_evidence_export_v1\0",
        b"skat-ai\0learning_corpus_tactical_motif_summary_export_v1\0",
    )
    with pytest.raises(TypeError, match="focused builder"):
        LearningCorpusTacticalMotifEvidenceV1()
    with pytest.raises(TypeError, match="focused builder"):
        LearningCorpusSkippedTacticalMotifDecisionV1()
    assert fields(LearningCorpusTacticalMotifEvidenceCollectionV1)[-4].name == (
        "evidences"
    )
    assert fields(LearningCorpusTacticalMotifScopeSummaryV1)[2].name == "scope"
    assert fields(LearningCorpusTacticalMotifPlayerSummaryV1)[2].name == "player_id"
    assert fields(LearningCorpusTacticalMotifRecurrenceV1)[2].name == "player_id"
    assert fields(LearningCorpusTacticalMotifCrossGameSummaryV1)[-1].name == (
        "limitations"
    )


def test_complete_current_snapshot_builds_one_exact_evidence_per_play() -> None:
    store = _complete_rich_store()
    collection = build_learning_corpus_tactical_motif_evidence_collection_v1(store)

    assert collection.status == "complete"
    assert collection.observed_game_count == 1
    assert collection.observed_decision_count == 30
    assert collection.evidence_count == 30
    assert collection.skipped_decision_count == 0
    assert collection.complete_observation_count == 30
    assert collection.partial_observation_count == 0
    assert [item.decision_index for item in collection.evidences] == list(range(1, 31))
    assert all(
        item.actual_card_played == item.observation.actual_card
        for item in collection.evidences
    )
    assert [item[0] for item in collection.motif_counts] == list(
        TACTICAL_MOTIF_TYPES
    )
    assert [item[0] for item in collection.family_counts] == list(
        TACTICAL_MOTIF_FAMILIES
    )
    assert collection == build_learning_corpus_tactical_motif_evidence_collection_v1(
        store
    )


def test_partial_source_preserves_safe_evidence_and_explicit_skips() -> None:
    _, snapshot = _rich_snapshot()
    collection = build_learning_corpus_tactical_motif_evidence_collection_v1(
        _store(snapshot, current=(snapshot,))
    )

    assert collection.status == "partial"
    assert collection.observed_decision_count == 6
    assert collection.evidence_count == 2
    assert collection.skipped_decision_count == 4
    assert {
        item.reason for item in collection.skipped_decisions
    } == {"acting_hand_unavailable"}
    assert not any(
        "actual_card" in item.to_dict() for item in collection.skipped_decisions
    )
    assert {
        item.decision_reference_id for item in collection.evidences
    }.isdisjoint(
        item.decision_reference_id for item in collection.skipped_decisions
    )


def test_required_public_hand_unavailable_is_an_explicit_skip() -> None:
    definition = _definition(match_id="match-tactical-ouvert-unavailable")
    historical = build_historical_input(game_type="null", hand_game=True)
    declaration = type(declaration_from_historical(historical))(
        game_type="null",
        hand_game=True,
        ouvert=True,
        bid_value=59,
    )
    perspective_hand = next(
        item["initial_hand"]
        for item in historical["players"]
        if item["player_id"] == definition.perspective_player_id
    )
    game = _observed_game(
        definition,
        match_position=3,
        perspective_initial_hand=perspective_hand,
        declarer_player_id=historical["declarer_player_id"],
        declaration=declaration,
        original_skat=historical["skat"],
        discarded_cards=(),
        plays=observed_plays_from_historical(historical, count=1),
    )
    workspace = _set_game(create_match_workspace_v1(definition), game)
    snapshot = build_learning_corpus_match_snapshot_v1(
        build_match_workspace_persistence_document_v1(workspace)
    )

    collection = build_learning_corpus_tactical_motif_evidence_collection_v1(
        _store(snapshot, current=(snapshot,))
    )

    assert collection.status == "partial"
    assert collection.evidence_count == 0
    assert collection.skipped_decision_count == 1
    assert collection.skipped_decisions[0].reason == (
        "required_public_hand_unavailable"
    )


def test_incomplete_final_trick_preserves_safe_partial_observation() -> None:
    _, source_snapshot = _rich_snapshot("match-incomplete-trick")
    source_game = source_snapshot.workspace.slots[2].observed_game
    assert source_game is not None
    truncated_game = _observed_game(
        source_snapshot.workspace.match_definition,
        match_position=3,
        game_id=source_game.game_id,
        game_timecode=source_game.game_timecode,
        perspective_initial_hand=source_game.perspective_initial_hand,
        declarer_player_id=source_game.declarer_player_id,
        declaration=source_game.declaration,
        original_skat=source_game.original_skat,
        discarded_cards=source_game.discarded_cards,
        plays=source_game.plays[:1],
        commentaries=(),
        response_links=(),
    )
    workspace = _set_game(
        create_match_workspace_v1(source_snapshot.workspace.match_definition),
        truncated_game,
    )
    snapshot = build_learning_corpus_match_snapshot_v1(
        build_match_workspace_persistence_document_v1(workspace)
    )

    collection = build_learning_corpus_tactical_motif_evidence_collection_v1(
        _store(snapshot, current=(snapshot,))
    )

    assert collection.status == "complete"
    assert collection.partial_observation_count == 1
    partial = next(
        item
        for item in collection.evidences
        if item.observation.observation_status == "partial"
    )
    assert partial.decision_index == 1
    assert partial.observation.completed_trick_winner_player_id is None
    assert all(
        motif.evidence_time == "after_actual_play"
        for motif in partial.observation.motifs
    )


def test_builder_reuses_each_current_source_stage_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _complete_rich_store()
    function_names = (
        "resolve_learning_corpus_current_match_snapshots_v1",
        "_validate_match_workspace_with_traces_v1",
        "build_match_observed_game_reconstruction_v1",
        "_build_match_decision_states_from_reconstruction_v1",
    )
    counts = {name: 0 for name in function_names}
    for name in function_names:
        original = getattr(tactical_builder_module, name)

        def counted(*args, _name=name, _original=original, **kwargs):
            counts[_name] += 1
            return _original(*args, **kwargs)

        monkeypatch.setattr(tactical_builder_module, name, counted)

    build_learning_corpus_tactical_motif_evidence_collection_v1(store)

    assert counts == {name: 1 for name in function_names}


def test_all_unsafe_and_empty_sources_use_exact_status_semantics() -> None:
    unavailable = build_learning_corpus_tactical_motif_evidence_collection_v1(
        _unavailable_store()
    )
    empty = build_learning_corpus_tactical_motif_evidence_collection_v1(_store())

    assert unavailable.status == "partial"
    assert unavailable.evidence_count == 0
    assert unavailable.skipped_decision_count == unavailable.observed_decision_count
    assert empty.status == "empty"
    assert empty.observed_game_count == 0
    assert empty.observed_decision_count == 0
    assert empty.evidences == ()
    assert empty.skipped_decisions == ()


def test_only_current_snapshots_contribute_and_source_counts_are_retained() -> None:
    _, retained = _rich_snapshot("match-current", first_text="Earlier text.")
    _, current = _rich_snapshot("match-current", first_text="Current text.")
    store = _store(
        retained,
        current,
        current=(current,),
        revision=2,
        orphans=("a" * 64,),
    )

    collection = build_learning_corpus_tactical_motif_evidence_collection_v1(store)

    assert collection.current_match_snapshot_ids == (current.match_snapshot_id,)
    assert collection.retained_match_snapshot_count == 2
    assert collection.current_match_count == 1
    assert collection.orphan_match_snapshot_count == 1
    assert {item.match_id for item in collection.evidences} == {"match-current"}
    assert {item.match_id for item in collection.skipped_decisions} == {
        "match-current"
    }


def test_cross_game_summary_reconciles_global_player_scope_and_recurrence_counts() -> None:
    collection, summary = _collection_and_summary(_complete_rich_store())

    assert summary.collection_status == "complete"
    assert summary.observed_decision_count == collection.observed_decision_count
    assert summary.evidence_count == collection.evidence_count
    assert summary.motif_counts == collection.motif_counts
    assert summary.family_counts == collection.family_counts
    assert len(summary.player_summaries) == 3
    assert [item.player_id for item in summary.player_summaries] == [
        "player-a",
        "player-b",
        "player-c",
    ]
    assert sum(item.decision_count for item in summary.role_summaries) == 30
    assert [item.scope_value for item in summary.seat_summaries] == [
        "forehand",
        "middlehand",
        "rearhand",
    ]
    assert [item.scope_value for item in summary.phase_summaries] == [
        "opening",
        "middle",
        "endgame",
    ]
    assert [item.scope_value for item in summary.contract_summaries] == [
        "clubs",
        "spades",
        "hearts",
        "diamonds",
        "grand",
        "null",
    ]
    assert all(item.occurrence_count > 0 for item in summary.recurrences)
    assert all(
        item.recurrence_scope == "single_game_only" for item in summary.recurrences
    )
    assert summary.limitations == LEARNING_CORPUS_TACTICAL_MOTIF_CROSS_GAME_LIMITATIONS
    assert not any(
        key in summary.to_dict()
        for key in ("quality", "recommendation", "rating", "significance")
    )


def test_recurrence_across_current_matches_is_factual_multiple_matches() -> None:
    snapshots = []
    for match_id in ("match-recurrence-a", "match-recurrence-b"):
        definition = _definition(match_id=match_id)
        workspace = _set_game(
            create_match_workspace_v1(definition),
            _complete_observed_game(
                definition,
                match_position=3,
                game_id="shared-source-game-id",
            ),
        )
        snapshots.append(
            build_learning_corpus_match_snapshot_v1(
                build_match_workspace_persistence_document_v1(workspace)
            )
        )
    first, second = snapshots
    _, summary = _collection_and_summary(
        _store(first, second, current=(first, second), revision=2)
    )

    repeated = [
        item
        for item in summary.recurrences
        if item.recurrence_scope == "multiple_matches"
    ]
    assert repeated
    assert all(item.match_count == 2 for item in repeated)
    assert all(item.game_count == 2 for item in repeated)
    assert all(len(item.game_reference_ids) == 2 for item in repeated)
    assert all(item.game_ids == ("shared-source-game-id",) for item in repeated)


def test_recurrence_across_games_in_one_match_uses_distinct_game_references() -> None:
    definition = _definition(match_id="match-multiple-games")
    workspace = create_match_workspace_v1(definition)
    workspace = _set_game(
        workspace,
        _complete_observed_game(definition, match_position=3, game_id="game-first"),
    )
    workspace = _set_game(
        workspace,
        _complete_observed_game(definition, match_position=6, game_id="game-second"),
    )
    snapshot = build_learning_corpus_match_snapshot_v1(
        build_match_workspace_persistence_document_v1(workspace)
    )
    _, summary = _collection_and_summary(_store(snapshot, current=(snapshot,)))

    repeated = [
        item
        for item in summary.recurrences
        if item.recurrence_scope == "multiple_games_one_match"
    ]
    assert repeated
    assert all(item.match_count == 1 for item in repeated)
    assert all(item.game_count == 2 for item in repeated)
    assert all(len(item.game_reference_ids) == 2 for item in repeated)


def test_empty_cross_game_summary_retains_players_and_canonical_zero_scopes() -> None:
    collection, summary = _collection_and_summary(_store())

    assert collection.status == "empty"
    assert summary.player_summaries == ()
    assert summary.recurrences == ()
    assert len(summary.role_summaries) == 2
    assert len(summary.seat_summaries) == 3
    assert len(summary.phase_summaries) == 3
    assert len(summary.contract_summaries) == 6
    assert all(count == 0 for _, count in summary.motif_counts)
    assert all(item.decision_count == 0 for item in summary.contract_summaries)


def test_player_summaries_retain_zero_valued_canonical_scopes() -> None:
    _, snapshot = _rich_snapshot()
    _, summary = _collection_and_summary(_store(snapshot, current=(snapshot,)))

    for player in summary.player_summaries:
        assert len(player.role_summaries) == 2
        assert len(player.seat_summaries) == 3
        assert len(player.phase_summaries) == 3
        assert len(player.contract_summaries) == 6
        assert any(item.decision_count == 0 for item in player.role_summaries)
        assert any(item.decision_count == 0 for item in player.seat_summaries)
        assert any(item.decision_count == 0 for item in player.phase_summaries)
        assert any(item.decision_count == 0 for item in player.contract_summaries)


def test_private_exports_are_path_free_canonical_and_deterministic() -> None:
    collection, summary = _collection_and_summary(_complete_rich_store())
    evidence_export = build_learning_corpus_tactical_motif_evidence_export_v1(
        collection
    )
    summary_export = (
        build_learning_corpus_tactical_motif_cross_game_summary_export_v1(summary)
    )
    evidence_bytes = serialize_learning_corpus_tactical_motif_evidence_export_v1(
        evidence_export
    )
    summary_bytes = (
        serialize_learning_corpus_tactical_motif_cross_game_summary_export_v1(
            summary_export
        )
    )

    assert evidence_export.document_kind == (
        LEARNING_CORPUS_TACTICAL_MOTIF_EVIDENCE_DOCUMENT_KIND
    )
    assert summary_export.document_kind == (
        LEARNING_CORPUS_TACTICAL_MOTIF_CROSS_GAME_SUMMARY_DOCUMENT_KIND
    )
    assert evidence_bytes.endswith(b"\n") and not evidence_bytes.endswith(b"\n\n")
    assert summary_bytes.endswith(b"\n") and not summary_bytes.endswith(b"\n\n")
    assert json.loads(evidence_bytes)["export_id"] == evidence_export.export_id
    assert json.loads(summary_bytes)["export_id"] == summary_export.export_id
    assert b"path" not in evidence_bytes.lower()
    assert b"path" not in summary_bytes.lower()
    assert evidence_bytes == serialize_learning_corpus_tactical_motif_evidence_export_v1(
        evidence_export
    )
    assert summary_bytes == (
        serialize_learning_corpus_tactical_motif_cross_game_summary_export_v1(
            summary_export
        )
    )
