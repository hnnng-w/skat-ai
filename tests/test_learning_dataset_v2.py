import hashlib
from dataclasses import FrozenInstanceError, fields

import pytest
from test_historical_game import build_historical_input
from test_learning_corpus_human_evidence import _rich_snapshot, _store
from test_learning_corpus_player_catalog_and_statistics import (
    _match_snapshot,
    _statistics_snapshot,
    _three_players,
)
from test_learning_corpus_strategy_teacher import _source_bundle
from test_match_workspace_contracts import _definition, _observed_game, _set_game
from test_observed_game_contracts import (
    declaration_from_historical,
    observed_plays_from_historical,
)

import skatmind.learning_dataset_v2_builder as dataset_builder_module
from skatmind.learning_corpus_human_evidence_builder import (
    build_learning_corpus_human_evidence_collection_v1,
)
from skatmind.learning_corpus_identity import (
    build_learning_corpus_canonical_json_bytes_v1,
)
from skatmind.learning_corpus_match_snapshot import (
    build_learning_corpus_match_snapshot_v1,
)
from skatmind.learning_corpus_persistence_contracts import (
    LearningCorpusStoreResumeResultV1,
)
from skatmind.learning_corpus_player_catalog import (
    build_learning_corpus_player_catalog_v1,
)
from skatmind.learning_corpus_strategy_teacher_builder import (
    build_learning_corpus_strategy_teacher_evidence_collection_v1,
)
from skatmind.learning_dataset_v2_builder import build_learning_dataset_v2
from skatmind.learning_dataset_v2_contracts import (
    LEARNING_DATASET_DECISION_STATE_POLICY,
    LEARNING_DATASET_DECISION_STATE_VERSION,
    LEARNING_DATASET_DERIVED_TAG_POLICY,
    LEARNING_DATASET_EVIDENCE_FAMILIES,
    LEARNING_DATASET_EVIDENCE_SEPARATION_POLICY,
    LEARNING_DATASET_EXPORT_POLICY,
    LEARNING_DATASET_HUMAN_TEXT_POLICY,
    LEARNING_DATASET_OBSERVED_BEHAVIOR_POLICY,
    LEARNING_DATASET_OBSERVED_BEHAVIOR_VERSION,
    LEARNING_DATASET_PARTITION_POLICY,
    LEARNING_DATASET_PLAYER_CONTEXT_POLICY,
    LEARNING_DATASET_PLAYER_CONTEXT_VERSION,
    LEARNING_DATASET_PRIVACY_POLICY,
    LEARNING_DATASET_RECORD_VERSION,
    LEARNING_DATASET_RELATIVE_PLAYERS,
    LEARNING_DATASET_SKIPPED_DECISION_VERSION,
    LEARNING_DATASET_SOURCE_CONTEXT_VERSION,
    LEARNING_DATASET_SOURCE_POLICY,
    LEARNING_DATASET_STATUSES,
    LEARNING_DATASET_STRATEGY_TEACHER_POLICY,
    LEARNING_DATASET_TASK_POLICY,
    LEARNING_DATASET_UNAVAILABLE_CONTEXT_POLICY,
    LEARNING_DATASET_VERSION,
    LearningDatasetDecisionStateV1,
    LearningDatasetObservedBehaviorV1,
    LearningDatasetPlayerContextV1,
    LearningDatasetRecordV1,
    LearningDatasetSkippedDecisionV1,
    LearningDatasetSourceContextV1,
    LearningDatasetV2,
)
from skatmind.match_workspace_contracts import create_match_workspace_v1
from skatmind.match_workspace_operations import mark_match_workspace_passed_deal_v1
from skatmind.match_workspace_persistence_codec import (
    build_match_workspace_persistence_document_v1,
)


def _hash(domain: bytes, value: object) -> str:
    return hashlib.sha256(
        domain + build_learning_corpus_canonical_json_bytes_v1(value)
    ).hexdigest()


def _sources(store, *, teacher_sources=()):
    return (
        build_learning_corpus_player_catalog_v1(store),
        build_learning_corpus_human_evidence_collection_v1(store),
        build_learning_corpus_strategy_teacher_evidence_collection_v1(
            store,
            teacher_sources,
        ),
    )


def _dataset(store, *, dataset_id="dataset-176", teacher_sources=()):
    player_catalog, human_evidence, teachers = _sources(
        store,
        teacher_sources=teacher_sources,
    )
    return build_learning_dataset_v2(
        store,
        player_catalog,
        human_evidence,
        teachers,
        dataset_id=dataset_id,
    )


def _complete_rich_store():
    _, partial_snapshot = _rich_snapshot()
    source_workspace = partial_snapshot.workspace
    source_game = source_workspace.slots[2].observed_game
    assert source_game is not None
    historical = build_historical_input(game_type="grand", hand_game=False)
    game = _observed_game(
        source_workspace.match_definition,
        match_position=3,
        game_id=source_game.game_id,
        game_timecode=source_game.game_timecode,
        perspective_initial_hand=source_game.perspective_initial_hand,
        declarer_player_id=source_game.declarer_player_id,
        declaration=source_game.declaration,
        original_skat=source_game.original_skat,
        discarded_cards=source_game.discarded_cards,
        plays=observed_plays_from_historical(historical),
        commentaries=source_game.commentaries,
        response_links=source_game.response_links,
    )
    workspace = _set_game(
        create_match_workspace_v1(source_workspace.match_definition),
        game,
    )
    snapshot = build_learning_corpus_match_snapshot_v1(
        build_match_workspace_persistence_document_v1(workspace)
    )
    return _store(snapshot, current=(snapshot,))


def _unavailable_store():
    _, source_snapshot = _rich_snapshot()
    source_workspace = source_snapshot.workspace
    source_game = source_workspace.slots[2].observed_game
    assert source_game is not None
    game = _observed_game(
        source_workspace.match_definition,
        match_position=3,
        game_id="game-unavailable",
        game_timecode=source_game.game_timecode,
        perspective_initial_hand=None,
        declarer_player_id=source_game.declarer_player_id,
        declaration=source_game.declaration,
        original_skat=source_game.original_skat,
        discarded_cards=source_game.discarded_cards,
        plays=source_game.plays[:1],
    )
    workspace = _set_game(
        create_match_workspace_v1(source_workspace.match_definition),
        game,
    )
    snapshot = build_learning_corpus_match_snapshot_v1(
        build_match_workspace_persistence_document_v1(workspace)
    )
    return _store(snapshot, current=(snapshot,))


def _rich_store_with_played_at(played_at):
    _, source_snapshot = _rich_snapshot()
    source_workspace = source_snapshot.workspace
    source_game = source_workspace.slots[2].observed_game
    assert source_game is not None
    definition = _definition(
        match_id="match-played-at",
        played_at=played_at,
        title=source_workspace.match_definition.title,
        external_match_id=source_workspace.match_definition.external_match_id,
        participants=source_workspace.match_definition.participants,
    )
    game = _observed_game(
        definition,
        match_position=3,
        game_id=source_game.game_id,
        game_timecode=source_game.game_timecode,
        perspective_initial_hand=source_game.perspective_initial_hand,
        declarer_player_id=source_game.declarer_player_id,
        declaration=source_game.declaration,
        original_skat=source_game.original_skat,
        discarded_cards=source_game.discarded_cards,
        plays=source_game.plays,
        commentaries=source_game.commentaries,
        response_links=source_game.response_links,
    )
    workspace = _set_game(create_match_workspace_v1(definition), game)
    snapshot = build_learning_corpus_match_snapshot_v1(
        build_match_workspace_persistence_document_v1(workspace)
    )
    return _store(snapshot, current=(snapshot,))


def _rich_snapshot_for_definition(definition):
    _, source_snapshot = _rich_snapshot()
    source_game = source_snapshot.workspace.slots[2].observed_game
    assert source_game is not None
    game = _observed_game(
        definition,
        match_position=3,
        game_id=f"game-{definition.match_id}",
        game_timecode=source_game.game_timecode,
        perspective_initial_hand=source_game.perspective_initial_hand,
        declarer_player_id=source_game.declarer_player_id,
        declaration=source_game.declaration,
        original_skat=source_game.original_skat,
        discarded_cards=source_game.discarded_cards,
        plays=source_game.plays,
        commentaries=source_game.commentaries,
        response_links=source_game.response_links,
    )
    workspace = _set_game(create_match_workspace_v1(definition), game)
    return build_learning_corpus_match_snapshot_v1(
        build_match_workspace_persistence_document_v1(workspace)
    )


@pytest.fixture(scope="module")
def rich_dataset_bundle():
    _, snapshot = _rich_snapshot()
    store = _store(snapshot, current=(snapshot,))
    player_catalog, human_evidence, teachers = _sources(store)
    dataset = build_learning_dataset_v2(
        store,
        player_catalog,
        human_evidence,
        teachers,
        dataset_id="dataset-rich",
    )
    return dataset, store, player_catalog, human_evidence, teachers


@pytest.fixture(scope="module")
def teacher_dataset_bundle():
    _workspace, snapshot_value, _result, _report, source, store = _source_bundle()
    _auto_workspace, auto_snapshot, _auto_result, _auto_report, auto_source, _ = (
        _source_bundle(recommendation_method="auto", search_random_seed=0)
    )
    assert auto_snapshot.match_snapshot_id == snapshot_value.match_snapshot_id
    player_catalog = build_learning_corpus_player_catalog_v1(store)
    human_evidence = build_learning_corpus_human_evidence_collection_v1(store)
    empty_teachers = build_learning_corpus_strategy_teacher_evidence_collection_v1(
        store,
        (),
    )
    teachers = build_learning_corpus_strategy_teacher_evidence_collection_v1(
        store,
        (source,),
    )
    without_teacher = build_learning_dataset_v2(
        store,
        player_catalog,
        human_evidence,
        empty_teachers,
        dataset_id="dataset-without-teacher",
    )
    with_teacher = build_learning_dataset_v2(
        store,
        player_catalog,
        human_evidence,
        teachers,
        dataset_id="dataset-with-teacher",
    )
    multiple_teachers = build_learning_corpus_strategy_teacher_evidence_collection_v1(
        store,
        (source, auto_source),
    )
    with_multiple_teachers = build_learning_dataset_v2(
        store,
        player_catalog,
        human_evidence,
        multiple_teachers,
        dataset_id="dataset-with-multiple-teachers",
    )
    return without_teacher, with_teacher, teachers, with_multiple_teachers


def test_versions_tuples_policies_and_fields_are_exact() -> None:
    assert (
        LEARNING_DATASET_VERSION,
        LEARNING_DATASET_SOURCE_CONTEXT_VERSION,
        LEARNING_DATASET_DECISION_STATE_VERSION,
        LEARNING_DATASET_OBSERVED_BEHAVIOR_VERSION,
        LEARNING_DATASET_PLAYER_CONTEXT_VERSION,
        LEARNING_DATASET_RECORD_VERSION,
        LEARNING_DATASET_SKIPPED_DECISION_VERSION,
    ) == (2, 1, 1, 1, 1, 1, 1)
    assert LEARNING_DATASET_STATUSES == (
        "empty",
        "unavailable",
        "partial",
        "complete",
    )
    assert LEARNING_DATASET_EVIDENCE_FAMILIES == (
        "observed_behavior",
        "player_context",
        "strategy_teacher",
        "human_commentary",
        "linked_response",
    )
    assert LEARNING_DATASET_RELATIVE_PLAYERS == ("me", "left", "right")
    assert (
        LEARNING_DATASET_SOURCE_POLICY,
        LEARNING_DATASET_DECISION_STATE_POLICY,
        LEARNING_DATASET_OBSERVED_BEHAVIOR_POLICY,
        LEARNING_DATASET_EVIDENCE_SEPARATION_POLICY,
        LEARNING_DATASET_HUMAN_TEXT_POLICY,
        LEARNING_DATASET_STRATEGY_TEACHER_POLICY,
        LEARNING_DATASET_PLAYER_CONTEXT_POLICY,
        LEARNING_DATASET_UNAVAILABLE_CONTEXT_POLICY,
        LEARNING_DATASET_PARTITION_POLICY,
        LEARNING_DATASET_TASK_POLICY,
        LEARNING_DATASET_DERIVED_TAG_POLICY,
        LEARNING_DATASET_PRIVACY_POLICY,
        LEARNING_DATASET_EXPORT_POLICY,
    ) == (
        "explicit_current_match_snapshots_only",
        "before_actual_play_information_safe_state",
        "actual_card_is_observed_behavior_not_universal_target",
        "behavior_strategy_and_communication_remain_separate",
        "preserve_exact_human_evidence_without_interpretation",
        "retain_all_method_bound_teacher_evidence_without_preference",
        "latest_unambiguous_strictly_prior_statistics_without_profile_derivation",
        "preserve_selection_status_reason_and_source_observation_ids",
        "unpartitioned_match_snapshot_grouping_reserved_for_later_preparation",
        "task_neutral_no_default_target_or_label",
        "no_derived_communication_tags_in_version_2",
        "private_local_unredacted_learning_evidence",
        "deterministic_path_free_json_document",
    )
    assert tuple(field.name for field in fields(LearningDatasetSourceContextV1)) == (
        "learning_dataset_source_context_version",
        "source_context_fingerprint",
        "match_snapshot_id",
        "game_reference_id",
        "match_id",
        "workspace_revision",
        "match_position",
        "game_id",
        "match_title",
        "external_match_id",
        "played_at",
        "game_platform",
        "source_kind",
        "source_url",
        "source_title",
        "source_channel_name",
        "match_timecode",
        "game_timecode",
        "decision_timecode",
        "perspective_player_id",
        "forehand_player_id",
        "middlehand_player_id",
        "rearhand_player_id",
        "declarer_player_id",
    )
    assert tuple(field.name for field in fields(LearningDatasetDecisionStateV1)) == (
        "learning_dataset_decision_state_version",
        "decision_state_fingerprint",
        "decision_reference_id",
        "source_game_id",
        "source_played_at",
        "decision_index",
        "trick_number",
        "play_index",
        "acting_player_id",
        "acting_seat",
        "acting_side",
        "information_cutoff",
        "relative_player_map",
        "visible_state",
    )
    assert tuple(field.name for field in fields(LearningDatasetObservedBehaviorV1)) == (
        "learning_dataset_observed_behavior_version",
        "observed_behavior_fingerprint",
        "decision_reference_id",
        "actual_card_played",
    )
    assert tuple(field.name for field in fields(LearningDatasetPlayerContextV1)) == (
        "learning_dataset_player_context_version",
        "relative_player",
        "player_id",
        "selection_mode",
        "selection_status",
        "unavailable_reason",
        "target_played_at",
        "candidate_observation_ids",
        "selected_statistics_observation_id",
        "equivalent_observation_ids",
        "ambiguous_observation_ids",
    )
    assert tuple(field.name for field in fields(LearningDatasetRecordV1)) == (
        "learning_dataset_record_version",
        "record_id",
        "record_content_fingerprint",
        "source_context",
        "decision_state",
        "observed_behavior",
        "player_contexts",
        "evidence_families_present",
        "strategy_teacher_evidence_ids",
        "commentary_evidence_ids",
        "outgoing_response_evidence_ids",
        "incoming_response_evidence_ids",
    )
    assert tuple(field.name for field in fields(LearningDatasetSkippedDecisionV1)) == (
        "learning_dataset_skipped_decision_version",
        "skipped_decision_id",
        "match_snapshot_id",
        "game_reference_id",
        "decision_reference_id",
        "match_id",
        "match_position",
        "game_id",
        "decision_index",
        "acting_player_id",
        "reason",
        "commentary_evidence_ids",
        "outgoing_response_evidence_ids",
        "incoming_response_evidence_ids",
    )
    assert tuple(field.name for field in fields(LearningDatasetV2)) == (
        "learning_dataset_version",
        "dataset_id",
        "dataset_fingerprint",
        "status",
        "corpus_id",
        "source_catalog_revision",
        "source_catalog_fingerprint",
        "source_catalog_content_fingerprint",
        "current_match_snapshot_ids",
        "player_catalog_fingerprint",
        "human_evidence_collection_fingerprint",
        "strategy_teacher_collection_fingerprint",
        "retained_match_snapshot_count",
        "current_match_count",
        "orphan_match_snapshot_count",
        "observed_game_count",
        "observed_decision_count",
        "record_count",
        "skipped_decision_count",
        "selected_statistics_context_count",
        "statistics_observation_count",
        "strategy_teacher_evidence_count",
        "commentary_evidence_count",
        "response_evidence_count",
        "records_with_strategy_teacher_count",
        "records_with_commentary_count",
        "records_with_outgoing_response_count",
        "records_with_incoming_response_count",
        "unjoined_commentary_evidence_count",
        "unjoined_response_evidence_count",
        "records",
        "skipped_decisions",
        "player_statistics_observations",
        "strategy_teacher_evidences",
        "commentary_evidences",
        "response_evidences",
        "unjoined_commentary_evidence_ids",
        "unjoined_response_evidence_ids",
    )


def test_empty_store_builds_one_valid_empty_task_neutral_dataset() -> None:
    dataset = _dataset(_store())
    assert dataset.status == "empty"
    assert dataset.observed_game_count == dataset.observed_decision_count == 0
    assert dataset.records == dataset.skipped_decisions == ()
    assert dataset.record_count == dataset.skipped_decision_count == 0
    assert dataset.player_statistics_observations == ()
    assert dataset.strategy_teacher_evidences == ()
    assert dataset.commentary_evidences == dataset.response_evidences == ()


def test_current_empty_slots_and_passed_deals_are_valid_empty_datasets() -> None:
    definition = _definition(match_id="match-empty-slots")
    empty_workspace = create_match_workspace_v1(definition)
    empty_snapshot = build_learning_corpus_match_snapshot_v1(
        build_match_workspace_persistence_document_v1(empty_workspace)
    )
    empty = _dataset(
        _store(empty_snapshot, current=(empty_snapshot,)),
        dataset_id="dataset-empty-slots",
    )
    assert empty.status == "empty"
    assert empty.current_match_count == 1
    assert empty.observed_game_count == 0

    passed_workspace = mark_match_workspace_passed_deal_v1(
        empty_workspace,
        match_position=1,
        game_timecode=None,
        expected_revision=0,
    ).workspace
    passed_snapshot = build_learning_corpus_match_snapshot_v1(
        build_match_workspace_persistence_document_v1(passed_workspace)
    )
    passed = _dataset(
        _store(passed_snapshot, current=(passed_snapshot,)),
        dataset_id="dataset-passed-only",
    )
    assert passed.status == "empty"
    assert passed.observed_game_count == passed.observed_decision_count == 0


def test_unavailable_and_complete_statuses_follow_safe_state_coverage() -> None:
    unavailable = _dataset(_unavailable_store(), dataset_id="dataset-unavailable")
    assert unavailable.status == "unavailable"
    assert unavailable.observed_decision_count == 1
    assert unavailable.records == ()
    assert unavailable.skipped_decision_count == 1
    assert unavailable.skipped_decisions[0].reason == "acting_hand_unavailable"

    complete = _dataset(_complete_rich_store(), dataset_id="dataset-complete")
    assert complete.status == "complete"
    assert complete.observed_decision_count == complete.record_count == 30
    assert complete.skipped_decisions == ()


def test_required_public_hand_unavailable_is_retained() -> None:
    definition = _definition(match_id="match-ouvert-unavailable")
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
    dataset = _dataset(
        _store(snapshot, current=(snapshot,)),
        dataset_id="dataset-ouvert-unavailable",
    )
    assert dataset.status == "unavailable"
    assert dataset.skipped_decisions[0].reason == (
        "required_public_hand_unavailable"
    )


def test_missing_match_time_preserves_unavailable_player_context() -> None:
    dataset = _dataset(
        _rich_store_with_played_at(None),
        dataset_id="dataset-missing-match-time",
    )
    assert dataset.records
    assert all(
        context.target_played_at is None
        and context.selection_status == "unavailable"
        and context.unavailable_reason == "target_time_unavailable"
        for record in dataset.records
        for context in record.player_contexts
    )


@pytest.mark.parametrize(
    ("second_games_played", "expected_status", "expected_reason"),
    (
        (127, "available", None),
        (128, "unavailable", "ambiguous_latest_instant"),
    ),
)
def test_dataset_preserves_equivalent_or_ambiguous_latest_statistics(
    second_games_played,
    expected_status,
    expected_reason,
) -> None:
    first_statistics = _statistics_snapshot(
        "player-a",
        "statistics-equivalent-a",
    )
    second_statistics = _statistics_snapshot(
        "player-a",
        "statistics-equivalent-b",
        games_played=second_games_played,
    )
    first_history = _match_snapshot(
        "match-statistics-a",
        participants=_three_players(player_a_statistics=first_statistics),
    )
    second_history = _match_snapshot(
        "match-statistics-b",
        participants=_three_players(player_a_statistics=second_statistics),
    )
    target_definition = _definition(
        match_id="match-statistics-target",
        played_at="2026-08-09T18:00:00Z",
        participants=_three_players(),
    )
    target = _rich_snapshot_for_definition(target_definition)
    store = _store(
        first_history,
        second_history,
        target,
        current=(first_history, second_history, target),
    )
    dataset = _dataset(store, dataset_id=f"dataset-statistics-{second_games_played}")
    target_record = next(
        item
        for item in dataset.records
        if item.source_context.match_snapshot_id == target.match_snapshot_id
        and item.decision_state.acting_player_id == "player-a"
    )
    context = target_record.player_contexts[0]
    assert context.selection_status == expected_status
    assert context.unavailable_reason == expected_reason
    assert len(context.candidate_observation_ids) == 2
    if expected_status == "available":
        assert len(context.equivalent_observation_ids) == 2
        assert context.selected_statistics_observation_id == min(
            context.equivalent_observation_ids
        )
        assert context.ambiguous_observation_ids == ()
    else:
        assert context.equivalent_observation_ids == ()
        assert len(context.ambiguous_observation_ids) == 2
    assert tuple(
        (
            item.player_id,
            item.captured_at,
            item.statistics_observation_id,
        )
        for item in dataset.player_statistics_observations
    ) == tuple(
        sorted(
            (
                item.player_id,
                item.captured_at,
                item.statistics_observation_id,
            )
            for item in dataset.player_statistics_observations
        )
    )


def test_offset_equivalent_capture_is_not_strictly_prior() -> None:
    statistics = _statistics_snapshot(
        "player-a",
        "statistics-equal-target",
    )
    history = _match_snapshot(
        "match-statistics-equality",
        participants=_three_players(player_a_statistics=statistics),
    )
    target = _rich_snapshot_for_definition(
        _definition(
            match_id="match-statistics-equal-target",
            played_at="2026-07-23T12:00:00+02:00",
            participants=_three_players(),
        )
    )
    dataset = _dataset(
        _store(history, target, current=(history, target)),
        dataset_id="dataset-equal-target",
    )
    record = next(
        item
        for item in dataset.records
        if item.source_context.match_snapshot_id == target.match_snapshot_id
        and item.decision_state.acting_player_id == "player-a"
    )
    context = record.player_contexts[0]
    assert context.selection_status == "unavailable"
    assert context.unavailable_reason == "no_prior_snapshot"
    assert context.candidate_observation_ids == ()


def test_partial_dataset_separates_state_behavior_and_evidence(
    rich_dataset_bundle,
) -> None:
    dataset, _, _, _, _ = rich_dataset_bundle
    assert dataset.status == "partial"
    assert dataset.observed_game_count == 1
    assert dataset.observed_decision_count == 6
    assert dataset.record_count == 2
    assert dataset.skipped_decision_count == 4
    assert tuple(item.decision_state.decision_index for item in dataset.records) == (1, 6)
    assert tuple(item.decision_index for item in dataset.skipped_decisions) == (2, 3, 4, 5)
    first = dataset.records[0]
    state = first.decision_state.to_dict()
    assert "actual_card_played" not in state
    assert "actual_card_played" not in state["visible_state"]
    assert first.observed_behavior.actual_card_played in state["visible_state"]["own_hand"]
    assert first.observed_behavior.actual_card_played in state["visible_state"]["legal_cards"]
    assert first.observed_behavior.actual_card_played not in {
        item["card"] for item in state["visible_state"]["current_trick"]
    }
    assert tuple(item.relative_player for item in first.player_contexts) == (
        LEARNING_DATASET_RELATIVE_PLAYERS
    )
    assert tuple(item.player_id for item in first.player_contexts) == tuple(
        first.decision_state.relative_player_map[key]
        for key in LEARNING_DATASET_RELATIVE_PLAYERS
    )
    assert all(item.selection_mode == "latest_unambiguous" for item in first.player_contexts)
    assert {item.selection_status for item in first.player_contexts} == {
        "available",
        "unavailable",
    }
    assert first.evidence_families_present == (
        "observed_behavior",
        "player_context",
        "human_commentary",
    )
    with pytest.raises(FrozenInstanceError):
        dataset.status = "complete"


def test_source_context_retains_exact_metadata_and_decision_timecode(
    rich_dataset_bundle,
) -> None:
    dataset, store, _, _, _ = rich_dataset_bundle
    snapshot = store.match_snapshots[0]
    game = snapshot.workspace.slots[2].observed_game
    assert game is not None
    context = dataset.records[0].source_context
    definition = snapshot.workspace.match_definition
    assert context.match_snapshot_id == snapshot.match_snapshot_id
    assert context.workspace_revision == snapshot.workspace_revision
    assert context.match_position == game.match_position
    assert context.match_title == definition.title
    assert context.external_match_id == definition.external_match_id
    assert context.played_at == definition.played_at
    assert context.source_url == definition.source.source_url
    assert context.match_timecode == definition.source.match_timecode
    assert context.game_timecode == game.game_timecode
    assert context.decision_timecode == game.plays[0].decision_timecode
    assert context.perspective_player_id == game.perspective_player_id
    assert {
        context.forehand_player_id,
        context.middlehand_player_id,
        context.rearhand_player_id,
    } == {item.player_id for item in game.players}


def test_commentary_and_response_joins_preserve_direction_and_unjoined_coverage(
) -> None:
    store = _complete_rich_store()
    player_catalog, human_evidence, teachers = _sources(store)
    dataset = build_learning_dataset_v2(
        store,
        player_catalog,
        human_evidence,
        teachers,
        dataset_id="dataset-complete-human",
    )
    records_by_index = {item.decision_state.decision_index: item for item in dataset.records}
    first = records_by_index[1]
    commentary_by_id = {
        item.commentary_evidence_id: item for item in human_evidence.commentaries
    }
    response_by_id = {item.response_evidence_id: item for item in human_evidence.responses}
    assert len(first.commentary_evidence_ids) == 1
    assert commentary_by_id[first.commentary_evidence_ids[0]].text.startswith("Überlegt")
    assert len(first.outgoing_response_evidence_ids) == 2
    for response_id in first.outgoing_response_evidence_ids:
        response = response_by_id[response_id]
        assert records_by_index[response.response_decision_index].incoming_response_evidence_ids
    external_response = next(
        item for item in human_evidence.responses if item.subject_decision_index == 2
    )
    assert external_response.response_evidence_id in (
        records_by_index[2].outgoing_response_evidence_ids
    )
    assert external_response.response_evidence_id in (
        records_by_index[5].incoming_response_evidence_ids
    )
    assert tuple(item.response_evidence_id for item in dataset.response_evidences) == tuple(
        item.response_evidence_id for item in human_evidence.responses
    )
    assert dataset.unjoined_commentary_evidence_ids == ()
    assert dataset.unjoined_response_evidence_ids == ()


def test_skipped_human_evidence_is_reported_unjoined(rich_dataset_bundle) -> None:
    dataset = rich_dataset_bundle[0]
    assert len(dataset.unjoined_commentary_evidence_ids) == 2
    assert len(dataset.unjoined_response_evidence_ids) == 3
    skipped_by_index = {item.decision_index: item for item in dataset.skipped_decisions}
    assert skipped_by_index[2].commentary_evidence_ids
    assert skipped_by_index[2].incoming_response_evidence_ids
    assert skipped_by_index[2].outgoing_response_evidence_ids
    assert skipped_by_index[3].commentary_evidence_ids
    assert skipped_by_index[4].incoming_response_evidence_ids
    assert skipped_by_index[5].incoming_response_evidence_ids


def test_teacher_enrichment_preserves_record_id_and_changes_content(
    teacher_dataset_bundle,
) -> None:
    without_teacher, with_teacher, teachers, _multiple = teacher_dataset_bundle
    assert with_teacher.strategy_teacher_evidences == teachers.evidences
    assert with_teacher.strategy_teacher_evidence_count == 1
    teacher = teachers.evidences[0]
    before = next(
        item
        for item in without_teacher.records
        if item.decision_state.decision_reference_id == teacher.decision_reference_id
    )
    after = next(
        item
        for item in with_teacher.records
        if item.decision_state.decision_reference_id == teacher.decision_reference_id
    )
    assert before.record_id == after.record_id
    assert before.record_content_fingerprint != after.record_content_fingerprint
    assert after.strategy_teacher_evidence_ids == (teacher.strategy_teacher_evidence_id,)
    assert "strategy_teacher" in after.evidence_families_present


def test_multiple_teachers_for_one_decision_preserve_source_order(
    teacher_dataset_bundle,
) -> None:
    _without, _single, _teachers, dataset = teacher_dataset_bundle
    assert dataset.strategy_teacher_evidence_count == 2
    decision_ids = {
        item.decision_reference_id for item in dataset.strategy_teacher_evidences
    }
    assert len(decision_ids) == 1
    record = next(
        item
        for item in dataset.records
        if item.decision_state.decision_reference_id in decision_ids
    )
    assert record.strategy_teacher_evidence_ids == tuple(
        item.strategy_teacher_evidence_id
        for item in dataset.strategy_teacher_evidences
    )


def test_statistics_selection_is_cached_per_player_and_target(monkeypatch) -> None:
    store = _complete_rich_store()
    player_catalog, human_evidence, teachers = _sources(store)
    original = (
        dataset_builder_module._select_learning_corpus_player_statistics_as_of_validated_v1
    )
    calls = []

    def counted(*args, **kwargs):
        calls.append((kwargs["player_id"], kwargs["target_played_at"]))
        return original(*args, **kwargs)

    monkeypatch.setattr(
        dataset_builder_module,
        "_select_learning_corpus_player_statistics_as_of_validated_v1",
        counted,
    )
    dataset = build_learning_dataset_v2(
        store,
        player_catalog,
        human_evidence,
        teachers,
        dataset_id="dataset-cached-statistics",
    )
    assert dataset.record_count == 30
    assert len(calls) == len(set(calls)) == 3


def test_sources_workspace_reconstruction_and_state_seam_execute_once(monkeypatch) -> None:
    _, snapshot = _rich_snapshot()
    store = _store(snapshot, current=(snapshot,))
    player_catalog, human_evidence, teachers = _sources(store)
    names = (
        "_validate_learning_corpus_player_catalog_v1",
        "_validate_learning_corpus_human_evidence_collection_v1",
        "_validate_learning_corpus_strategy_teacher_collection_v1",
        "_validate_match_workspace_with_traces_v1",
        "build_match_observed_game_reconstruction_v1",
        "_build_match_decision_states_from_reconstruction_v1",
    )
    calls = {name: 0 for name in names}
    for name in names:
        original = getattr(dataset_builder_module, name)

        def counted(*args, _name=name, _original=original, **kwargs):
            calls[_name] += 1
            return _original(*args, **kwargs)

        monkeypatch.setattr(dataset_builder_module, name, counted)
    build_learning_dataset_v2(
        store,
        player_catalog,
        human_evidence,
        teachers,
        dataset_id="dataset-execution-counts",
    )
    assert calls == dict.fromkeys(names, 1)


def test_only_explicit_current_snapshot_contributes() -> None:
    _, first = _rich_snapshot("match-current", first_text="First current text.")
    _, second = _rich_snapshot("match-current", first_text="Second retained text.")
    store = _store(
        first,
        second,
        current=(first,),
        orphans=("a" * 64,),
    )
    dataset = _dataset(store, dataset_id="dataset-current-only")
    assert dataset.current_match_snapshot_ids == (first.match_snapshot_id,)
    assert dataset.orphan_match_snapshot_count == 1
    assert {item.source_context.match_snapshot_id for item in dataset.records} == {
        first.match_snapshot_id
    }
    assert dataset.commentary_evidences[0].text == "First current text."
    changed = _dataset(
        _store(
            first,
            second,
            current=(second,),
            revision=2,
            orphans=("a" * 64,),
        ),
        dataset_id="dataset-current-only",
    )
    assert changed.current_match_snapshot_ids == (second.match_snapshot_id,)
    assert changed.commentary_evidences[0].text == "Second retained text."
    assert changed.dataset_fingerprint != dataset.dataset_fingerprint


def test_multiple_matches_use_canonical_match_and_decision_order() -> None:
    _, match_b = _rich_snapshot("match-b")
    _, match_a = _rich_snapshot("match-a")
    dataset = _dataset(
        _store(match_b, match_a, current=(match_b, match_a)),
        dataset_id="dataset-multiple-matches",
    )
    keys = tuple(
        (
            item.source_context.match_id,
            item.source_context.match_position,
            item.decision_state.decision_index,
            item.record_id,
        )
        for item in dataset.records
    )
    assert keys == tuple(sorted(keys))
    assert dataset.current_match_snapshot_ids == (
        match_a.match_snapshot_id,
        match_b.match_snapshot_id,
    )


def test_dataset_counts_and_normalized_pools_reconcile(rich_dataset_bundle) -> None:
    dataset = rich_dataset_bundle[0]
    assert dataset.record_count == len(dataset.records)
    assert dataset.skipped_decision_count == len(dataset.skipped_decisions)
    assert dataset.statistics_observation_count == len(
        dataset.player_statistics_observations
    )
    assert dataset.strategy_teacher_evidence_count == len(
        dataset.strategy_teacher_evidences
    )
    assert dataset.commentary_evidence_count == len(dataset.commentary_evidences)
    assert dataset.response_evidence_count == len(dataset.response_evidences)
    assert dataset.records_with_commentary_count == sum(
        bool(item.commentary_evidence_ids) for item in dataset.records
    )
    assert dataset.records_with_outgoing_response_count == sum(
        bool(item.outgoing_response_evidence_ids) for item in dataset.records
    )
    assert dataset.records_with_incoming_response_count == sum(
        bool(item.incoming_response_evidence_ids) for item in dataset.records
    )
    referenced_statistics = {
        observation_id
        for record in dataset.records
        for context in record.player_contexts
        for observation_id in (
            *context.candidate_observation_ids,
            *context.equivalent_observation_ids,
            *context.ambiguous_observation_ids,
            *(
                (context.selected_statistics_observation_id,)
                if context.selected_statistics_observation_id is not None
                else ()
            ),
        )
    }
    assert referenced_statistics == {
        item.statistics_observation_id for item in dataset.player_statistics_observations
    }


def test_record_validation_rejects_source_seat_mismatch(rich_dataset_bundle) -> None:
    record = rich_dataset_bundle[0].records[0]
    context = record.source_context
    original_forehand = context.forehand_player_id
    original_middlehand = context.middlehand_player_id
    object.__setattr__(context, "forehand_player_id", original_middlehand)
    object.__setattr__(context, "middlehand_player_id", original_forehand)
    try:
        with pytest.raises(ValueError, match="acting seat"):
            record._validate(verify_identities=False)
    finally:
        object.__setattr__(context, "forehand_player_id", original_forehand)
        object.__setattr__(context, "middlehand_player_id", original_middlehand)


def test_dataset_validation_rejects_cross_player_statistics_reference(
    rich_dataset_bundle,
) -> None:
    dataset = rich_dataset_bundle[0]
    record = dataset.records[0]
    me, left, _right = record.player_contexts
    assert me.candidate_observation_ids
    original_candidates = left.candidate_observation_ids
    object.__setattr__(left, "candidate_observation_ids", me.candidate_observation_ids)
    try:
        with pytest.raises(ValueError, match="same Player"):
            dataset._validate(verify_fingerprint=False, validate_nested=False)
    finally:
        object.__setattr__(left, "candidate_observation_ids", original_candidates)


def test_player_context_rejects_unavailable_explicit_override_reason(
    rich_dataset_bundle,
) -> None:
    context = next(
        item
        for item in rich_dataset_bundle[0].records[0].player_contexts
        if item.selection_status == "unavailable"
    )
    original = context.unavailable_reason
    object.__setattr__(context, "unavailable_reason", "explicit_observation_not_found")
    try:
        with pytest.raises(ValueError, match="invalid reason"):
            context._validate()
    finally:
        object.__setattr__(context, "unavailable_reason", original)


def test_dataset_validation_binds_commentary_and_response_to_exact_records() -> None:
    dataset = _dataset(_complete_rich_store(), dataset_id="dataset-binding-validation")
    records_by_index = {item.decision_state.decision_index: item for item in dataset.records}
    first = records_by_index[1]
    second = records_by_index[2]
    first_commentary = first.commentary_evidence_ids
    second_commentary = second.commentary_evidence_ids
    object.__setattr__(first, "commentary_evidence_ids", second_commentary)
    object.__setattr__(second, "commentary_evidence_ids", first_commentary)
    try:
        with pytest.raises(ValueError, match="Commentary Evidence must reconcile"):
            dataset._validate(verify_fingerprint=False, validate_nested=False)
    finally:
        object.__setattr__(first, "commentary_evidence_ids", first_commentary)
        object.__setattr__(second, "commentary_evidence_ids", second_commentary)

    first_outgoing = first.outgoing_response_evidence_ids
    second_outgoing = second.outgoing_response_evidence_ids
    object.__setattr__(first, "outgoing_response_evidence_ids", second_outgoing)
    object.__setattr__(second, "outgoing_response_evidence_ids", first_outgoing)
    try:
        with pytest.raises(ValueError, match="Response Evidence must reconcile"):
            dataset._validate(verify_fingerprint=False, validate_nested=False)
    finally:
        object.__setattr__(first, "outgoing_response_evidence_ids", first_outgoing)
        object.__setattr__(second, "outgoing_response_evidence_ids", second_outgoing)


def test_dataset_validation_requires_complete_skipped_evidence_attachment(
    rich_dataset_bundle,
) -> None:
    dataset = rich_dataset_bundle[0]
    skipped = next(item for item in dataset.skipped_decisions if item.commentary_evidence_ids)
    original = skipped.commentary_evidence_ids
    object.__setattr__(skipped, "commentary_evidence_ids", ())
    try:
        with pytest.raises(ValueError, match="Every unjoined Commentary"):
            dataset._validate(verify_fingerprint=False, validate_nested=False)
    finally:
        object.__setattr__(skipped, "commentary_evidence_ids", original)


def test_dataset_validation_binds_teacher_to_its_decision(
    teacher_dataset_bundle,
) -> None:
    _without_teacher, dataset, teachers, _multiple = teacher_dataset_bundle
    teacher = teachers.evidences[0]
    correct = next(
        item
        for item in dataset.records
        if item.decision_state.decision_reference_id == teacher.decision_reference_id
    )
    wrong = next(item for item in dataset.records if item is not correct)
    correct_ids = correct.strategy_teacher_evidence_ids
    wrong_ids = wrong.strategy_teacher_evidence_ids
    object.__setattr__(correct, "strategy_teacher_evidence_ids", ())
    object.__setattr__(wrong, "strategy_teacher_evidence_ids", correct_ids)
    try:
        with pytest.raises(ValueError, match="Strategy Teacher Evidence must reconcile"):
            dataset._validate(verify_fingerprint=False, validate_nested=False)
    finally:
        object.__setattr__(correct, "strategy_teacher_evidence_ids", correct_ids)
        object.__setattr__(wrong, "strategy_teacher_evidence_ids", wrong_ids)


def test_record_and_dataset_identities_use_exact_domains(rich_dataset_bundle) -> None:
    dataset, _, _, _, _ = rich_dataset_bundle
    first = dataset.records[0]
    source_material = first.source_context.to_dict()
    del source_material["source_context_fingerprint"]
    assert first.source_context.source_context_fingerprint == _hash(
        b"skatmind\0learning_dataset_v2_source_context_v1\0",
        source_material,
    )
    state_material = first.decision_state.to_dict()
    del state_material["decision_state_fingerprint"]
    assert first.decision_state.decision_state_fingerprint == _hash(
        b"skatmind\0learning_dataset_v2_decision_state_v1\0",
        state_material,
    )
    behavior_material = first.observed_behavior.to_dict()
    del behavior_material["observed_behavior_fingerprint"]
    assert first.observed_behavior.observed_behavior_fingerprint == _hash(
        b"skatmind\0learning_dataset_v2_observed_behavior_v1\0",
        behavior_material,
    )
    record_material = {
        "learning_dataset_record_version": 1,
        "match_snapshot_id": first.source_context.match_snapshot_id,
        "decision_reference_id": first.decision_state.decision_reference_id,
    }
    assert first.record_id == _hash(
        b"skatmind\0learning_dataset_v2_record_v1\0",
        record_material,
    )
    record_content = first.to_dict()
    del record_content["record_content_fingerprint"]
    assert first.record_content_fingerprint == _hash(
        b"skatmind\0learning_dataset_v2_record_content_v1\0",
        record_content,
    )
    skipped = dataset.skipped_decisions[0]
    skipped_material = skipped.to_dict()
    del skipped_material["skipped_decision_id"]
    assert skipped.skipped_decision_id == _hash(
        b"skatmind\0learning_dataset_v2_skipped_decision_v1\0",
        skipped_material,
    )
    dataset_content = dataset.to_dict()
    del dataset_content["dataset_fingerprint"]
    assert dataset.dataset_fingerprint == _hash(
        b"skatmind\0learning_dataset_v2_collection_v2\0",
        dataset_content,
    )
    changed_id = build_learning_dataset_v2(
        rich_dataset_bundle[1],
        rich_dataset_bundle[2],
        rich_dataset_bundle[3],
        rich_dataset_bundle[4],
        dataset_id="dataset-rich-changed",
    )
    assert changed_id.dataset_fingerprint != dataset.dataset_fingerprint
    assert tuple(item.record_id for item in changed_id.records) == tuple(
        item.record_id for item in dataset.records
    )


def test_serialization_is_fresh_and_task_neutral(rich_dataset_bundle) -> None:
    dataset = rich_dataset_bundle[0]
    first = dataset.to_dict()
    second = dataset.to_dict()
    first["records"][0]["decision_state"]["visible_state"]["own_hand"].clear()
    assert second == dataset.to_dict()
    assert not {"partition", "target", "label", "reward"}.intersection(
        dataset.to_dict()
    )
    assert not {"partition", "target", "label", "reward"}.intersection(
        dataset.records[0].to_dict()
    )
    assert "profile" not in dataset.records[0].decision_state.to_dict()["visible_state"]


def test_source_identity_mismatch_is_rejected(rich_dataset_bundle) -> None:
    _, store, player_catalog, human_evidence, teachers = rich_dataset_bundle
    foreign = _store()
    with pytest.raises(ValueError, match="exact Corpus Store source identity"):
        build_learning_dataset_v2(
            foreign,
            player_catalog,
            human_evidence,
            teachers,
            dataset_id="foreign",
        )


def test_store_is_strictly_validated_before_source_mismatch(
    rich_dataset_bundle,
    monkeypatch,
) -> None:
    _, _, player_catalog, human_evidence, teachers = rich_dataset_bundle
    foreign = _store()
    calls = 0
    original = LearningCorpusStoreResumeResultV1._validate_structure

    def counted(self, *, validate_snapshots):
        nonlocal calls
        calls += 1
        return original(self, validate_snapshots=validate_snapshots)

    monkeypatch.setattr(
        LearningCorpusStoreResumeResultV1,
        "_validate_structure",
        counted,
    )
    with pytest.raises(ValueError, match="exact Corpus Store source identity"):
        build_learning_dataset_v2(
            foreign,
            player_catalog,
            human_evidence,
            teachers,
            dataset_id="foreign-validation-order",
        )
    assert calls == 1


@pytest.mark.parametrize("foreign_source_index", (0, 1, 2))
def test_each_stale_derived_source_is_rejected(foreign_source_index) -> None:
    _, snapshot = _rich_snapshot("match-stale-source")
    current_store = _store(snapshot, current=(snapshot,), revision=1)
    stale_store = _store(snapshot, current=(snapshot,), revision=2)
    current_sources = list(_sources(current_store))
    stale_sources = _sources(stale_store)
    current_sources[foreign_source_index] = stale_sources[foreign_source_index]
    with pytest.raises(ValueError, match="exact Corpus Store source identity"):
        build_learning_dataset_v2(
            current_store,
            *current_sources,
            dataset_id=f"dataset-stale-{foreign_source_index}",
        )
