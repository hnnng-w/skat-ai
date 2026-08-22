import ast
import hashlib
import inspect
import json
from dataclasses import FrozenInstanceError, fields

import pytest
from test_historical_game import build_historical_input
from test_learning_corpus_human_evidence import _rich_snapshot, _store
from test_learning_corpus_strategy_teacher import _changed_report, _source_bundle
from test_learning_dataset_v2 import _complete_rich_store, _dataset, _sources
from test_learning_dataset_v2_partition_preparation import (
    _disjoint_snapshot,
    _known_bundle,
)
from test_match_workspace_contracts import _definition, _observed_game, _set_game
from test_observed_game_contracts import (
    declaration_from_historical,
    observed_plays_from_historical,
)

import skat_ai.learning_dataset_v2_summary_builder as summary_builder_module
import skat_ai.learning_dataset_v2_summary_contracts as summary_contracts_module
import skat_ai.learning_dataset_v2_summary_export as summary_export_module
from skat_ai import __version__
from skat_ai.api.v1.contracts import PUBLIC_API_CONTRACT_VERSION
from skat_ai.learning_corpus_human_evidence import (
    LEARNING_CORPUS_COMMENTATOR_IDENTITY_KINDS,
)
from skat_ai.learning_corpus_identity import (
    LEARNING_CORPUS_IDENTITY_VERSION,
    build_learning_corpus_canonical_json_bytes_v1,
)
from skat_ai.learning_corpus_match_snapshot import (
    build_learning_corpus_match_snapshot_v1,
)
from skat_ai.learning_corpus_player_catalog import (
    build_learning_corpus_player_catalog_v1,
)
from skat_ai.learning_corpus_strategy_teacher import (
    LEARNING_CORPUS_STRATEGY_TEACHER_SEARCH_STATUSES,
    LearningCorpusStrategyTeacherEvidenceCollectionV1,
    _build_collection_fingerprint_v1,
    _build_strategy_teacher_evidence_v1,
    _strategy_teacher_counts_v1,
    build_learning_corpus_strategy_teacher_report_source_v1,
)
from skat_ai.learning_corpus_strategy_teacher_builder import _collection_material
from skat_ai.learning_dataset_v2_builder import build_learning_dataset_v2
from skat_ai.learning_dataset_v2_contracts import LEARNING_DATASET_VERSION
from skat_ai.learning_dataset_v2_partition_contracts import (
    LEARNING_DATASET_PARTITION_MODES,
    LEARNING_DATASET_PARTITION_PREPARATION_VERSION,
    LearningDatasetPartitionWeightsV1,
)
from skat_ai.learning_dataset_v2_partition_preparation import (
    build_learning_dataset_partition_preparation_request_v1,
    prepare_learning_dataset_v2_partitions_v1,
)
from skat_ai.learning_dataset_v2_summary_builder import (
    build_learning_dataset_v2_cross_game_summary_v1,
)
from skat_ai.learning_dataset_v2_summary_contracts import (
    _COMMUNICATION_SUMMARY_FINGERPRINT_DOMAIN,
    _COVERAGE_ID_DOMAIN,
    _CROSS_GAME_SUMMARY_FINGERPRINT_DOMAIN,
    _MATCH_SUMMARY_ID_DOMAIN,
    _PARTITION_READINESS_ID_DOMAIN,
    _PLAYER_SUMMARY_ID_DOMAIN,
    _READINESS_SUMMARY_FINGERPRINT_DOMAIN,
    _STRATEGY_SUMMARY_FINGERPRINT_DOMAIN,
    _SUMMARY_COUNT_ID_DOMAIN,
    LEARNING_DATASET_COMMUNICATION_SUMMARY_VERSION,
    LEARNING_DATASET_CROSS_GAME_SUMMARY_VERSION,
    LEARNING_DATASET_MATCH_SUMMARY_VERSION,
    LEARNING_DATASET_PARTITION_READINESS_VERSION,
    LEARNING_DATASET_PLAYER_SUMMARY_VERSION,
    LEARNING_DATASET_READINESS_SUMMARY_VERSION,
    LEARNING_DATASET_STRATEGY_SUMMARY_VERSION,
    LEARNING_DATASET_SUMMARY_BEHAVIOR_POLICY,
    LEARNING_DATASET_SUMMARY_COMMUNICATION_POLICY,
    LEARNING_DATASET_SUMMARY_COVERAGE_FAMILIES,
    LEARNING_DATASET_SUMMARY_COVERAGE_STATUSES,
    LEARNING_DATASET_SUMMARY_CURRENT_SOURCE_POLICY,
    LEARNING_DATASET_SUMMARY_EXPORT_POLICY,
    LEARNING_DATASET_SUMMARY_EXPORT_VERSION,
    LEARNING_DATASET_SUMMARY_PARTITION_POLICY,
    LEARNING_DATASET_SUMMARY_PLAYER_POLICY,
    LEARNING_DATASET_SUMMARY_PRIMITIVE_VERSION,
    LEARNING_DATASET_SUMMARY_PRIVACY_POLICY,
    LEARNING_DATASET_SUMMARY_RATIO_POLICY,
    LEARNING_DATASET_SUMMARY_READINESS_POLICY,
    LEARNING_DATASET_SUMMARY_SOURCE_POLICY,
    LEARNING_DATASET_SUMMARY_STRATEGY_POLICY,
    LEARNING_DATASET_SUMMARY_TEXT_POLICY,
    LearningDatasetCommunicationSummaryV1,
    LearningDatasetCrossGameSummaryV1,
    LearningDatasetMatchSummaryV1,
    LearningDatasetPartitionReadinessV1,
    LearningDatasetPlayerSummaryV1,
    LearningDatasetReadinessSummaryV1,
    LearningDatasetStrategySummaryV1,
    LearningDatasetSummaryCategoricalCountV1,
    LearningDatasetSummaryCoverageV1,
    LearningDatasetSummaryIntegerCountV1,
    build_learning_dataset_summary_coverage_v1,
)
from skat_ai.learning_dataset_v2_summary_export import (
    _SUMMARY_EXPORT_ID_DOMAIN,
    LEARNING_DATASET_SUMMARY_DOCUMENT_KIND,
    LearningDatasetCrossGameSummaryExportV1,
    build_learning_dataset_v2_cross_game_summary_export_v1,
    serialize_learning_dataset_v2_cross_game_summary_export_v1,
)
from skat_ai.match_workspace_contracts import create_match_workspace_v1
from skat_ai.match_workspace_persistence_codec import (
    build_match_workspace_persistence_document_v1,
)
from skat_ai.recommendation_workflow import FLAT_RECOMMENDATION_METHODS
from skat_ai.training_dataset import TRAINING_DATASET_SCHEMA_VERSION, TRAINING_TARGET


def _hash(domain: bytes, value: object) -> str:
    return hashlib.sha256(domain + build_learning_corpus_canonical_json_bytes_v1(value)).hexdigest()


def _partition_results(dataset, catalog, *, seed=17):
    weights = LearningDatasetPartitionWeightsV1(train=1, validation=1, test=1)
    results = []
    for mode in LEARNING_DATASET_PARTITION_MODES:
        request = build_learning_dataset_partition_preparation_request_v1(
            dataset,
            catalog,
            mode=mode,
            base_random_seed=seed,
            partition_weights=weights,
        )
        results.append(prepare_learning_dataset_v2_partitions_v1(request))
    return tuple(results)


def _summary_sources(store, *, dataset_id="dataset-summary", teacher_sources=()):
    catalog, human_evidence, teachers = _sources(
        store,
        teacher_sources=teacher_sources,
    )
    dataset = build_learning_dataset_v2(
        store,
        catalog,
        human_evidence,
        teachers,
        dataset_id=dataset_id,
    )
    known, unseen = _partition_results(dataset, catalog)
    summary = build_learning_dataset_v2_cross_game_summary_v1(
        dataset,
        catalog,
        known_player_partition_result=known,
        unseen_player_partition_result=unseen,
    )
    return dataset, catalog, known, unseen, summary


@pytest.fixture(scope="module")
def complete_summary_bundle():
    return _summary_sources(
        _complete_rich_store(),
        dataset_id="dataset-summary-complete",
    )


@pytest.fixture(scope="module")
def strategy_summary_bundle():
    _workspace, snapshot, result, _report, search_source, store = _source_bundle(
        recommendation_method="bounded_search",
        search_random_seed=0,
        search_budget_profile="interactive_v1",
    )
    changed_document = result.result.to_dict()["document"]
    changed_document["bounded_search_result"]["consumed_budget"]["wall_clock_elapsed_ms"] += 1
    semantic_duplicate = build_learning_corpus_strategy_teacher_report_source_v1(
        match_snapshot_id=snapshot.match_snapshot_id,
        report=_changed_report(result, result_document=changed_document),
    )
    _, immediate_snapshot, _, _, immediate_source, _ = _source_bundle()
    _, auto_snapshot, _, _, auto_source, _ = _source_bundle(
        recommendation_method="auto",
        search_random_seed=0,
        search_budget_profile="interactive_v1",
    )
    assert (
        immediate_snapshot.match_snapshot_id
        == auto_snapshot.match_snapshot_id
        == snapshot.match_snapshot_id
    )
    return _summary_sources(
        store,
        dataset_id="dataset-summary-strategy",
        teacher_sources=(
            immediate_source,
            search_source,
            semantic_duplicate,
            auto_source,
        ),
    )


def test_versions_vocabularies_policies_document_kind_and_domains_are_exact() -> None:
    assert (
        LEARNING_DATASET_SUMMARY_PRIMITIVE_VERSION,
        LEARNING_DATASET_MATCH_SUMMARY_VERSION,
        LEARNING_DATASET_PLAYER_SUMMARY_VERSION,
        LEARNING_DATASET_COMMUNICATION_SUMMARY_VERSION,
        LEARNING_DATASET_STRATEGY_SUMMARY_VERSION,
        LEARNING_DATASET_PARTITION_READINESS_VERSION,
        LEARNING_DATASET_READINESS_SUMMARY_VERSION,
        LEARNING_DATASET_CROSS_GAME_SUMMARY_VERSION,
        LEARNING_DATASET_SUMMARY_EXPORT_VERSION,
    ) == (1,) * 9
    assert LEARNING_DATASET_SUMMARY_COVERAGE_STATUSES == (
        "absent",
        "partial",
        "complete",
    )
    assert LEARNING_DATASET_SUMMARY_COVERAGE_FAMILIES == (
        "decision_state",
        "observed_behavior",
        "player_context",
        "strategy_teacher",
        "human_commentary",
        "linked_response",
    )
    assert (
        LEARNING_DATASET_SUMMARY_SOURCE_POLICY,
        LEARNING_DATASET_SUMMARY_CURRENT_SOURCE_POLICY,
        LEARNING_DATASET_SUMMARY_BEHAVIOR_POLICY,
        LEARNING_DATASET_SUMMARY_COMMUNICATION_POLICY,
        LEARNING_DATASET_SUMMARY_STRATEGY_POLICY,
        LEARNING_DATASET_SUMMARY_READINESS_POLICY,
        LEARNING_DATASET_SUMMARY_PLAYER_POLICY,
        LEARNING_DATASET_SUMMARY_PARTITION_POLICY,
        LEARNING_DATASET_SUMMARY_RATIO_POLICY,
        LEARNING_DATASET_SUMMARY_TEXT_POLICY,
        LEARNING_DATASET_SUMMARY_PRIVACY_POLICY,
        LEARNING_DATASET_SUMMARY_EXPORT_POLICY,
    ) == (
        "exact_dataset_player_catalog_and_partition_results",
        "explicit_current_match_snapshots_only",
        "descriptive_observed_behavior_without_skill_or_quality_claim",
        "count_exact_human_and_response_evidence_without_interpretation",
        "aggregate_method_bound_teacher_status_without_preference_or_truth_claim",
        "coverage_and_partition_availability_not_model_readiness",
        "stable_player_descriptive_history_without_rating_or_ranking",
        "report_supplied_partition_results_without_regeneration",
        "exact_counts_without_floating_point_percentages",
        "human_text_never_used_for_grouping_or_output",
        "private_local_minimized_aggregate_metadata",
        "deterministic_path_free_json_document",
    )
    assert LEARNING_DATASET_SUMMARY_DOCUMENT_KIND == (
        "skat_ai_learning_dataset_v2_cross_game_summary"
    )
    assert (
        _SUMMARY_COUNT_ID_DOMAIN,
        _COVERAGE_ID_DOMAIN,
        _MATCH_SUMMARY_ID_DOMAIN,
        _PLAYER_SUMMARY_ID_DOMAIN,
        _COMMUNICATION_SUMMARY_FINGERPRINT_DOMAIN,
        _STRATEGY_SUMMARY_FINGERPRINT_DOMAIN,
        _PARTITION_READINESS_ID_DOMAIN,
        _READINESS_SUMMARY_FINGERPRINT_DOMAIN,
        _CROSS_GAME_SUMMARY_FINGERPRINT_DOMAIN,
        _SUMMARY_EXPORT_ID_DOMAIN,
    ) == tuple(
        f"skat-ai\0{name}\0".encode()
        for name in (
            "learning_dataset_v2_summary_count_v1",
            "learning_dataset_v2_summary_coverage_v1",
            "learning_dataset_v2_match_summary_v1",
            "learning_dataset_v2_player_summary_v1",
            "learning_dataset_v2_communication_summary_v1",
            "learning_dataset_v2_strategy_summary_v1",
            "learning_dataset_v2_partition_readiness_v1",
            "learning_dataset_v2_readiness_summary_v1",
            "learning_dataset_v2_cross_game_summary_v1",
            "learning_dataset_v2_summary_export_v1",
        )
    )
    assert LEARNING_DATASET_VERSION == 2
    assert LEARNING_DATASET_PARTITION_PREPARATION_VERSION == 1
    assert LEARNING_CORPUS_IDENTITY_VERSION == 1
    assert TRAINING_DATASET_SCHEMA_VERSION == 1
    assert TRAINING_TARGET == "actual_card_played"
    assert PUBLIC_API_CONTRACT_VERSION == 1
    assert __version__ == "0.16.0"


def test_summary_contract_field_sets_are_exact() -> None:
    assert tuple(item.name for item in fields(LearningDatasetSummaryCategoricalCountV1)) == (
        "learning_dataset_summary_primitive_version",
        "category",
        "count",
    )
    assert tuple(item.name for item in fields(LearningDatasetSummaryIntegerCountV1)) == (
        "learning_dataset_summary_primitive_version",
        "value",
        "count",
    )
    assert tuple(item.name for item in fields(LearningDatasetSummaryCoverageV1)) == (
        "learning_dataset_summary_primitive_version",
        "coverage_id",
        "family",
        "status",
        "covered_count",
        "total_count",
        "uncovered_count",
    )
    assert tuple(item.name for item in fields(LearningDatasetMatchSummaryV1))[0:2] == (
        "learning_dataset_match_summary_version",
        "match_summary_id",
    )
    assert tuple(item.name for item in fields(LearningDatasetPlayerSummaryV1))[0:3] == (
        "learning_dataset_player_summary_version",
        "player_summary_id",
        "player_id",
    )
    assert tuple(item.name for item in fields(LearningDatasetCommunicationSummaryV1))[0:2] == (
        "learning_dataset_communication_summary_version",
        "communication_summary_fingerprint",
    )
    assert tuple(item.name for item in fields(LearningDatasetStrategySummaryV1))[0:2] == (
        "learning_dataset_strategy_summary_version",
        "strategy_summary_fingerprint",
    )
    assert tuple(item.name for item in fields(LearningDatasetPartitionReadinessV1))[0:3] == (
        "learning_dataset_partition_readiness_version",
        "partition_readiness_id",
        "mode",
    )
    assert tuple(item.name for item in fields(LearningDatasetReadinessSummaryV1))[0:2] == (
        "learning_dataset_readiness_summary_version",
        "readiness_summary_fingerprint",
    )
    assert tuple(item.name for item in fields(LearningDatasetCrossGameSummaryV1))[0:2] == (
        "learning_dataset_cross_game_summary_version",
        "cross_game_summary_fingerprint",
    )
    assert tuple(item.name for item in fields(LearningDatasetCrossGameSummaryExportV1)) == (
        "learning_dataset_summary_export_version",
        "document_kind",
        "export_id",
        "summary_fingerprint",
        "cross_game_summary",
    )


def test_summary_primitives_reject_invalid_values_and_cover_exact_semantics() -> None:
    categorical = LearningDatasetSummaryCategoricalCountV1(category="grand", count=2)
    integer = LearningDatasetSummaryIntegerCountV1(value=3, count=4)
    assert categorical.to_dict()["category"] == "grand"
    assert integer.to_dict()["value"] == 3
    with pytest.raises(ValueError, match="non-negative"):
        LearningDatasetSummaryCategoricalCountV1(category="grand", count=-1)
    with pytest.raises(ValueError, match="non-negative"):
        LearningDatasetSummaryIntegerCountV1(value=3, count=True)
    with pytest.raises(ValueError, match="non-padded"):
        LearningDatasetSummaryCategoricalCountV1(category=" grand", count=1)
    with pytest.raises(ValueError, match="integer"):
        LearningDatasetSummaryIntegerCountV1(value=True, count=1)

    absent = build_learning_dataset_summary_coverage_v1(
        family="decision_state",
        covered_count=0,
        total_count=0,
    )
    partial = build_learning_dataset_summary_coverage_v1(
        family="decision_state",
        covered_count=2,
        total_count=6,
    )
    complete = build_learning_dataset_summary_coverage_v1(
        family="observed_behavior",
        covered_count=2,
        total_count=2,
    )
    assert (absent.status, partial.status, complete.status) == (
        "absent",
        "partial",
        "complete",
    )
    assert (partial.covered_count, partial.uncovered_count, partial.total_count) == (
        2,
        4,
        6,
    )
    material = partial.to_dict()
    del material["coverage_id"]
    assert partial.coverage_id == _hash(_COVERAGE_ID_DOMAIN, material)
    with pytest.raises(ValueError, match="cannot exceed"):
        build_learning_dataset_summary_coverage_v1(
            family="decision_state",
            covered_count=2,
            total_count=1,
        )
    with pytest.raises(FrozenInstanceError):
        categorical.count = 3


def test_empty_summary_and_export_are_valid_deterministic_and_count_only() -> None:
    dataset, catalog, known, unseen, summary = _summary_sources(
        _store(),
        dataset_id="dataset-summary-empty",
    )
    assert dataset.status == summary.dataset_status == "empty"
    assert catalog.player_count == summary.player_count == 0
    assert summary.match_summaries == ()
    assert summary.player_summaries == ()
    assert summary.communication_summary.commentary_count == 0
    assert summary.strategy_summary.evidence_count == 0
    assert summary.readiness_summary.decision_state_coverage.status == "absent"
    assert tuple(item.status for item in summary.readiness_summary.partition_readiness) == (
        "unavailable",
        "unavailable",
    )
    assert known.unavailable_reason == unseen.unavailable_reason == "dataset_has_no_records"
    repeated = build_learning_dataset_v2_cross_game_summary_v1(
        dataset,
        catalog,
        known_player_partition_result=known,
        unseen_player_partition_result=unseen,
    )
    assert repeated == summary
    export = build_learning_dataset_v2_cross_game_summary_export_v1(summary)
    assert export.cross_game_summary is summary
    assert serialize_learning_dataset_v2_cross_game_summary_export_v1(export) == (
        serialize_learning_dataset_v2_cross_game_summary_export_v1(export)
    )


def test_zero_decision_observed_game_is_global_but_not_match_decision_represented() -> None:
    definition = _definition(match_id="match-summary-zero-decision")
    workspace = _set_game(
        create_match_workspace_v1(definition),
        _observed_game(definition),
    )
    snapshot = build_learning_corpus_match_snapshot_v1(
        build_match_workspace_persistence_document_v1(workspace)
    )
    dataset, _catalog, _known, _unseen, summary = _summary_sources(
        _store(snapshot, current=(snapshot,)),
        dataset_id="dataset-summary-zero-decision",
    )

    assert dataset.status == "empty"
    assert (dataset.observed_game_count, dataset.observed_decision_count) == (1, 0)
    assert summary.observed_game_count == 1
    assert len(summary.match_summaries) == 1
    # Match summaries count only Game References represented by a Decision.
    assert summary.match_summaries[0].observed_game_count == 0


def test_complete_match_behavior_context_and_readiness_counts(
    complete_summary_bundle,
) -> None:
    dataset, catalog, _known, _unseen, summary = complete_summary_bundle
    assert summary.dataset_fingerprint == dataset.dataset_fingerprint
    assert summary.player_catalog_fingerprint == catalog.player_catalog_fingerprint
    assert summary.dataset_status == "complete"
    assert (summary.observed_game_count, summary.record_count, summary.skipped_decision_count) == (
        1,
        30,
        0,
    )
    assert len(summary.match_summaries) == 1
    match = summary.match_summaries[0]
    assert len(match.player_ids) == 3
    assert match.perspective_player_id in match.player_ids
    assert (match.observed_game_count, match.record_count, match.skipped_decision_count) == (
        1,
        30,
        0,
    )
    assert match.record_coverage.status == "complete"
    assert (match.forced_choice_record_count, match.choice_record_count) == (4, 26)
    assert (
        match.player_context_available_count,
        match.player_context_unavailable_count,
    ) == (30, 60)
    assert match.records_by_game_type[4].to_dict() == {
        "learning_dataset_summary_primitive_version": 1,
        "category": "grand",
        "count": 30,
    }
    assert [item.value for item in match.records_by_trick_number] == list(range(1, 11))
    assert [item.value for item in match.records_by_play_index] == [1, 2, 3]
    readiness = summary.readiness_summary
    assert readiness.decision_state_coverage.status == "complete"
    assert tuple(item.family for item in readiness.evidence_family_coverages) == (
        "observed_behavior",
        "player_context",
        "strategy_teacher",
        "human_commentary",
        "linked_response",
    )
    assert tuple(item.status for item in readiness.evidence_family_coverages[:2]) == (
        "complete",
        "complete",
    )
    assert (
        readiness.player_context_total_count,
        readiness.player_context_available_count,
        readiness.player_context_unavailable_count,
        readiness.selected_statistics_context_count,
    ) == (90, 30, 60, 30)
    assert [(item.category, item.count) for item in readiness.skipped_reason_counts] == [
        ("acting_hand_unavailable", 0),
        ("required_public_hand_unavailable", 0),
    ]
    assert [
        (item.category, item.count) for item in readiness.player_context_unavailable_reason_counts
    ] == [("no_statistics_history", 60)]


@pytest.mark.parametrize(
    ("match_position", "rename"),
    (
        (1, {"player-a": "player-b", "player-b": "player-c", "player-c": "player-a"}),
        (2, {"player-a": "player-c", "player-b": "player-a", "player-c": "player-b"}),
    ),
)
def test_match_reconciliation_accepts_rotating_seat_order(match_position, rename) -> None:
    historical = build_historical_input()
    for player in historical["players"]:
        player["player_id"] = rename[player["player_id"]]
    historical["declarer_player_id"] = rename[historical["declarer_player_id"]]
    for trick in historical["tricks"]:
        trick["leader_player_id"] = rename[trick["leader_player_id"]]
        for play in trick["plays"]:
            play["player_id"] = rename[play["player_id"]]

    definition = _definition(match_id=f"match-summary-position-{match_position}")
    perspective_hand = next(
        player["initial_hand"]
        for player in historical["players"]
        if player["player_id"] == definition.perspective_player_id
    )
    game = _observed_game(
        definition,
        match_position=match_position,
        perspective_initial_hand=perspective_hand,
        declarer_player_id=historical["declarer_player_id"],
        declaration=declaration_from_historical(historical),
        original_skat=historical["skat"],
        discarded_cards=historical["discarded_cards"],
        plays=observed_plays_from_historical(historical),
    )
    workspace = _set_game(create_match_workspace_v1(definition), game)
    snapshot = build_learning_corpus_match_snapshot_v1(
        build_match_workspace_persistence_document_v1(workspace)
    )
    _dataset_value, _catalog, _known, _unseen, summary = _summary_sources(
        _store(snapshot, current=(snapshot,)),
        dataset_id=f"dataset-summary-position-{match_position}",
    )

    assert summary.match_summaries[0].record_count == 30


def test_player_summaries_are_stable_descriptive_and_card_canonical(
    complete_summary_bundle,
) -> None:
    _dataset_value, catalog, _known, _unseen, summary = complete_summary_bundle
    assert [item.player_id for item in summary.player_summaries] == sorted(
        item.player_id for item in summary.player_summaries
    )
    assert len(summary.player_summaries) == 3
    assert sum(item.record_count for item in summary.player_summaries) == 30
    cards = [
        count.category for player in summary.player_summaries for count in player.actual_card_counts
    ]
    deck_order = {
        card: index
        for index, card in enumerate(
            (
                "CA",
                "C10",
                "CK",
                "CQ",
                "CJ",
                "C9",
                "C8",
                "C7",
                "SA",
                "S10",
                "SK",
                "SQ",
                "SJ",
                "S9",
                "S8",
                "S7",
                "HA",
                "H10",
                "HK",
                "HQ",
                "HJ",
                "H9",
                "H8",
                "H7",
                "DA",
                "D10",
                "DK",
                "DQ",
                "DJ",
                "D9",
                "D8",
                "D7",
            )
        )
    }
    for player in summary.player_summaries:
        assert [deck_order[item.category] for item in player.actual_card_counts] == sorted(
            deck_order[item.category] for item in player.actual_card_counts
        )
        assert sum(item.count for item in player.actual_card_counts) == player.record_count
        catalog_entry = next(item for item in catalog.players if item.player_id == player.player_id)
        assert player.observed_labels == catalog_entry.observed_labels
        assert player.match_ids == catalog_entry.match_ids
        assert player.statistics_observation_count == catalog_entry.statistics_observation_count
        assert player.player_context_reference_count == 30
        assert player.same_trick_response_count + player.later_trick_response_count == (
            player.outgoing_response_count
        )
    assert cards
    forbidden = {"rating", "ranking", "rank", "score", "grade", "quality", "average"}
    assert not forbidden.intersection(summary.player_summaries[0].to_dict())


def test_communication_summary_uses_structure_without_text_or_names(
    complete_summary_bundle,
) -> None:
    _dataset_value, _catalog, _known, _unseen, summary = complete_summary_bundle
    communication = summary.communication_summary
    assert (
        communication.commentary_count,
        communication.commented_decision_count,
        communication.response_count,
    ) == (3, 3, 3)
    assert [
        (item.category, item.count) for item in communication.commentator_identity_kind_counts
    ] == [
        ("match_player", 1),
        ("external", 1),
        ("match_player_and_external", 1),
    ]
    assert (
        tuple(item.category for item in communication.commentator_identity_kind_counts)
        == LEARNING_CORPUS_COMMENTATOR_IDENTITY_KINDS
    )
    assert (
        communication.commentaries_with_response_count,
        communication.commentaries_without_response_count,
    ) == (2, 1)
    assert (
        communication.same_trick_response_count,
        communication.later_trick_response_count,
    ) == (1, 2)
    assert [item.value for item in communication.decision_offset_counts] == [1, 3]
    assert sum(item.count for item in communication.subject_response_role_pair_counts) == 3
    assert sum(item.count for item in communication.subject_response_seat_pair_counts) == 3
    serialized = json.dumps(communication.to_dict()).lower()
    for forbidden in (
        "überlegt",
        "video analyst",
        "source audio",
        "sentiment",
        "intent",
        "causal",
        "quality",
    ):
        assert forbidden not in serialized


def test_partial_summary_reports_skipped_and_unjoined_evidence() -> None:
    _, snapshot = _rich_snapshot()
    dataset, _catalog, _known, _unseen, summary = _summary_sources(
        _store(snapshot, current=(snapshot,)),
        dataset_id="dataset-summary-partial",
    )
    assert summary.dataset_status == "partial"
    assert (summary.record_count, summary.skipped_decision_count) == (2, 4)
    assert summary.match_summaries[0].record_coverage.status == "partial"
    assert summary.communication_summary.commentary_count == 1
    assert summary.communication_summary.response_count == 0
    assert (
        summary.communication_summary.unjoined_commentary_evidence_count,
        summary.communication_summary.unjoined_response_evidence_count,
    ) == (2, 3)
    assert summary.readiness_summary.unjoined_commentary_evidence_count == (
        dataset.unjoined_commentary_evidence_count
    )
    assert [
        (item.category, item.count) for item in summary.readiness_summary.skipped_reason_counts
    ] == [
        ("acting_hand_unavailable", 4),
        ("required_public_hand_unavailable", 0),
    ]


def test_strategy_summary_retains_methods_statuses_semantic_duplicates_and_equality(
    strategy_summary_bundle,
) -> None:
    dataset, _catalog, _known, _unseen, summary = strategy_summary_bundle
    strategy = summary.strategy_summary
    assert strategy.evidence_count == dataset.strategy_teacher_evidence_count == 4
    assert strategy.distinct_decision_count == 1
    assert strategy.multi_teacher_decision_count == 1
    assert strategy.maximum_teacher_count_per_decision == 4
    assert strategy.semantic_fingerprint_count == 3
    assert strategy.semantic_duplicate_group_count == 1
    assert [item.category for item in strategy.requested_method_counts] == list(
        FLAT_RECOMMENDATION_METHODS
    )
    assert [item.category for item in strategy.search_status_counts] == list(
        LEARNING_CORPUS_STRATEGY_TEACHER_SEARCH_STATUSES
    )
    assert sum(item.count for item in strategy.effective_method_counts) == 4
    assert (
        strategy.actual_card_match_evidence_count
        + strategy.actual_card_difference_evidence_count
        + strategy.actual_card_comparison_unavailable_count
        == 4
    )
    assert strategy.actual_card_comparison_unavailable_count == (
        strategy.recommendation_unavailable_count
    )
    player = next(
        item
        for item in summary.player_summaries
        if item.player_id == dataset.strategy_teacher_evidences[0].acting_player_id
    )
    assert player.strategy_teacher_evidence_count == 4
    assert player.teacher_distinct_decision_count == 1
    assert player.teacher_actual_card_match_count == (strategy.actual_card_match_evidence_count)
    serialized = strategy.to_dict()
    for forbidden in (
        "accuracy",
        "precision",
        "average",
        "winner",
        "consensus",
        "candidate_results",
        "requested_budget",
    ):
        assert forbidden not in serialized


def test_text_change_changes_source_identity_but_not_descriptive_counts() -> None:
    _, first_snapshot = _rich_snapshot(first_text="First exact text.")
    _, second_snapshot = _rich_snapshot(first_text="Adversarial text: rating winner intent.")
    first = _summary_sources(
        _store(first_snapshot, current=(first_snapshot,)),
        dataset_id="dataset-summary-text",
    )
    second = _summary_sources(
        _store(second_snapshot, current=(second_snapshot,)),
        dataset_id="dataset-summary-text",
    )
    first_dataset, *_, first_summary = first
    second_dataset, *_, second_summary = second
    assert first_dataset.dataset_fingerprint != second_dataset.dataset_fingerprint
    assert first_summary.cross_game_summary_fingerprint != (
        second_summary.cross_game_summary_fingerprint
    )
    assert first_summary.communication_summary.to_dict() == (
        second_summary.communication_summary.to_dict()
    )
    first_behavior = first_summary.match_summaries[0].to_dict()
    second_behavior = second_summary.match_summaries[0].to_dict()
    behavior_fields = (
        "record_count",
        "skipped_decision_count",
        "records_by_game_type",
        "records_by_acting_side",
        "records_by_acting_seat",
        "records_by_trick_number",
        "records_by_play_index",
        "forced_choice_record_count",
        "choice_record_count",
    )
    assert {field: first_behavior[field] for field in behavior_fields} == {
        field: second_behavior[field] for field in behavior_fields
    }


def test_teacher_candidate_metric_changes_only_source_bound_summary_identity() -> None:
    _workspace, snapshot, result, _report, source, store = _source_bundle()
    changed_document = result.result.to_dict()["document"]
    changed_document["analysis_report"][0]["win_rate"] = 0.125
    changed_source = build_learning_corpus_strategy_teacher_report_source_v1(
        match_snapshot_id=snapshot.match_snapshot_id,
        report=_changed_report(result, result_document=changed_document),
    )
    first_dataset, *_first_sources, first_summary = _summary_sources(
        store,
        dataset_id="dataset-summary-candidate-metric",
        teacher_sources=(source,),
    )
    changed_dataset, *_changed_sources, changed_summary = _summary_sources(
        store,
        dataset_id="dataset-summary-candidate-metric",
        teacher_sources=(changed_source,),
    )

    assert first_dataset.dataset_fingerprint != changed_dataset.dataset_fingerprint
    assert (
        first_dataset.strategy_teacher_evidences[0].teacher_semantic_fingerprint
        != changed_dataset.strategy_teacher_evidences[0].teacher_semantic_fingerprint
    )
    assert first_summary.cross_game_summary_fingerprint != (
        changed_summary.cross_game_summary_fingerprint
    )
    assert first_summary.match_summaries == changed_summary.match_summaries
    assert first_summary.player_summaries == changed_summary.player_summaries
    assert first_summary.communication_summary == changed_summary.communication_summary
    for field_name in (
        "requested_method_counts",
        "effective_method_counts",
        "search_status_counts",
    ):
        assert getattr(first_summary.strategy_summary, field_name) == getattr(
            changed_summary.strategy_summary,
            field_name,
        )


def test_unavailable_teacher_with_retained_card_uses_card_comparison_semantics() -> None:
    _workspace, _snapshot, _result, _report, source, store = _source_bundle()
    catalog, human_evidence, teachers = _sources(
        store,
        teacher_sources=(source,),
    )
    teacher = teachers.evidences[0]
    teacher_values = {
        item.name: getattr(teacher, item.name)
        for item in fields(teacher)
        if item.name
        not in {
            "learning_corpus_strategy_teacher_evidence_version",
            "strategy_teacher_evidence_id",
            "teacher_semantic_fingerprint",
        }
    }
    teacher_values["status"] = "recommendation_unavailable"
    method_summary = dict(teacher_values["recommendation_method_summary"])
    method_summary["effective_method"] = "none"
    teacher_values["recommendation_method_summary"] = method_summary
    changed_teacher = _build_strategy_teacher_evidence_v1(**teacher_values)
    collection_values = {
        item.name: getattr(teachers, item.name)
        for item in fields(teachers)
        if item.name
        not in {
            "learning_corpus_strategy_teacher_collection_version",
            "strategy_teacher_collection_fingerprint",
        }
    }
    collection_values.update(_strategy_teacher_counts_v1((changed_teacher,)))
    collection_values["evidences"] = (changed_teacher,)
    changed_teachers = LearningCorpusStrategyTeacherEvidenceCollectionV1._from_validated(
        strategy_teacher_collection_fingerprint=_build_collection_fingerprint_v1(
            _collection_material(collection_values)
        ),
        **collection_values,
    )
    dataset = build_learning_dataset_v2(
        store,
        catalog,
        human_evidence,
        changed_teachers,
        dataset_id="dataset-summary-unavailable-retained-card",
    )
    known, unseen = _partition_results(dataset, catalog)
    summary = build_learning_dataset_v2_cross_game_summary_v1(
        dataset,
        catalog,
        known_player_partition_result=known,
        unseen_player_partition_result=unseen,
    )

    retained_teacher = dataset.strategy_teacher_evidences[0]
    assert retained_teacher.status == "recommendation_unavailable"
    assert retained_teacher.recommendation["card"] is not None
    strategy = summary.strategy_summary
    assert (strategy.recommendation_available_count, strategy.recommendation_unavailable_count) == (
        0,
        1,
    )
    assert (
        strategy.actual_card_match_evidence_count + strategy.actual_card_difference_evidence_count
    ) == 1
    assert strategy.actual_card_comparison_unavailable_count == 0


def test_complete_known_and_unseen_partition_readiness_preserves_supplied_facts() -> None:
    known_request, known_dataset, known_catalog = _known_bundle()
    known_result = prepare_learning_dataset_v2_partitions_v1(known_request)
    unseen_request = build_learning_dataset_partition_preparation_request_v1(
        known_dataset,
        known_catalog,
        mode="unseen_player",
        base_random_seed=17,
        partition_weights=known_request.partition_weights,
    )
    unseen_unavailable = prepare_learning_dataset_v2_partitions_v1(unseen_request)
    known_summary = build_learning_dataset_v2_cross_game_summary_v1(
        known_dataset,
        known_catalog,
        known_player_partition_result=known_result,
        unseen_player_partition_result=unseen_unavailable,
    )
    known = known_summary.readiness_summary.partition_readiness[0]
    assert known.status == "complete"
    assert known.algorithm == known_result.plan.algorithm
    assert known.request_fingerprint == known_result.request_fingerprint
    assert known.plan_fingerprint == known_result.plan.plan_fingerprint
    assert known.partition_summaries == known_result.plan.partition_summaries
    assert known.leakage_audit_status == "compliant"
    assert known.all_partitions_have_records is True
    assert known.mode_constraints_satisfied is True
    assert known.known_player_time_group_count == 3
    assert known.known_player_validation_train_coverage_complete is True
    assert known.known_player_test_train_coverage_complete is True
    assert known.unseen_player_component_count is None

    snapshots = tuple(_disjoint_snapshot(index) for index in range(1, 4))
    store = _store(*snapshots, current=snapshots)
    dataset = _dataset(store, dataset_id="dataset-summary-unseen")
    catalog = build_learning_corpus_player_catalog_v1(store)
    weights = LearningDatasetPartitionWeightsV1(train=1, validation=1, test=1)
    results = {}
    for mode in LEARNING_DATASET_PARTITION_MODES:
        results[mode] = prepare_learning_dataset_v2_partitions_v1(
            build_learning_dataset_partition_preparation_request_v1(
                dataset,
                catalog,
                mode=mode,
                base_random_seed=23,
                partition_weights=weights,
            )
        )
    unseen_summary = build_learning_dataset_v2_cross_game_summary_v1(
        dataset,
        catalog,
        known_player_partition_result=results["known_player"],
        unseen_player_partition_result=results["unseen_player"],
    )
    unseen = unseen_summary.readiness_summary.partition_readiness[1]
    assert unseen.status == "complete"
    assert unseen.partition_summaries == results["unseen_player"].plan.partition_summaries
    assert unseen.unseen_player_component_count == 3
    assert unseen.unseen_player_player_disjoint is True
    assert unseen.unseen_player_local_move_optimal is True
    assert unseen.unseen_player_local_swap_optimal is True
    assert unseen.known_player_time_group_count is None
    readiness_document = unseen.to_dict()
    assert "assignments" not in readiness_document
    assert "learning_dataset" not in readiness_document


def test_source_modes_fingerprints_and_catalog_identity_are_reconciled() -> None:
    dataset, catalog, known, unseen, _summary = _summary_sources(
        _store(),
        dataset_id="dataset-summary-reconcile",
    )
    with pytest.raises(ValueError, match="known_player"):
        build_learning_dataset_v2_cross_game_summary_v1(
            dataset,
            catalog,
            known_player_partition_result=unseen,
            unseen_player_partition_result=known,
        )
    original = known.request_fingerprint
    object.__setattr__(known, "request_fingerprint", "0" * 64)
    try:
        with pytest.raises(ValueError, match="request fingerprint"):
            build_learning_dataset_v2_cross_game_summary_v1(
                dataset,
                catalog,
                known_player_partition_result=known,
                unseen_player_partition_result=unseen,
            )
    finally:
        object.__setattr__(known, "request_fingerprint", original)
    original_catalog = catalog.player_catalog_fingerprint
    object.__setattr__(catalog, "player_catalog_fingerprint", "0" * 64)
    try:
        with pytest.raises(ValueError, match="fingerprint"):
            build_learning_dataset_v2_cross_game_summary_v1(
                dataset,
                catalog,
                known_player_partition_result=known,
                unseen_player_partition_result=unseen,
            )
    finally:
        object.__setattr__(catalog, "player_catalog_fingerprint", original_catalog)


def test_foreign_dataset_result_and_stale_catalog_are_rejected() -> None:
    store = _store()
    catalog, human_evidence, teachers = _sources(store)
    first_dataset = build_learning_dataset_v2(
        store,
        catalog,
        human_evidence,
        teachers,
        dataset_id="dataset-summary-foreign-first",
    )
    foreign_dataset = build_learning_dataset_v2(
        store,
        catalog,
        human_evidence,
        teachers,
        dataset_id="dataset-summary-foreign-second",
    )
    known, unseen = _partition_results(first_dataset, catalog)
    with pytest.raises(ValueError, match="request fingerprint"):
        build_learning_dataset_v2_cross_game_summary_v1(
            foreign_dataset,
            catalog,
            known_player_partition_result=known,
            unseen_player_partition_result=unseen,
        )

    _, first_snapshot = _rich_snapshot(first_text="First Catalog source.")
    _, stale_snapshot = _rich_snapshot(first_text="Stale Catalog source.")
    current_store = _store(first_snapshot, current=(first_snapshot,))
    current_catalog, human_evidence, teachers = _sources(current_store)
    current_dataset = build_learning_dataset_v2(
        current_store,
        current_catalog,
        human_evidence,
        teachers,
        dataset_id="dataset-summary-stale-catalog",
    )
    known, unseen = _partition_results(current_dataset, current_catalog)
    stale_catalog = build_learning_corpus_player_catalog_v1(
        _store(stale_snapshot, current=(stale_snapshot,))
    )
    with pytest.raises(ValueError, match="source identities"):
        build_learning_dataset_v2_cross_game_summary_v1(
            current_dataset,
            stale_catalog,
            known_player_partition_result=known,
            unseen_player_partition_result=unseen,
        )


def test_complete_partition_view_must_retain_same_dataset_instance() -> None:
    known_request, dataset, catalog = _known_bundle()
    known = prepare_learning_dataset_v2_partitions_v1(known_request)
    assert known.status == "complete"
    unseen = prepare_learning_dataset_v2_partitions_v1(
        build_learning_dataset_partition_preparation_request_v1(
            dataset,
            catalog,
            mode="unseen_player",
            base_random_seed=known_request.base_random_seed,
            partition_weights=known_request.partition_weights,
        )
    )
    duplicate_dataset = object.__new__(type(dataset))
    for contract_field in fields(dataset):
        object.__setattr__(
            duplicate_dataset,
            contract_field.name,
            getattr(dataset, contract_field.name),
        )
    assert duplicate_dataset == dataset and duplicate_dataset is not dataset

    with pytest.raises(ValueError, match="exact source Dataset"):
        build_learning_dataset_v2_cross_game_summary_v1(
            duplicate_dataset,
            catalog,
            known_player_partition_result=known,
            unseen_player_partition_result=unseen,
        )


def test_builder_validates_sources_once_rebuilds_two_requests_and_generates_no_plan(
    monkeypatch,
) -> None:
    store = _store()
    catalog, human_evidence, teachers = _sources(store)
    dataset = build_learning_dataset_v2(
        store,
        catalog,
        human_evidence,
        teachers,
        dataset_id="dataset-summary-counts",
    )
    known, unseen = _partition_results(dataset, catalog)
    calls = {
        "dataset_validation": 0,
        "catalog_validation": 0,
        "request_rebuild": 0,
        "plan_generation": 0,
    }

    for name, key in (
        ("_validate_learning_dataset_v2", "dataset_validation"),
        ("_validate_learning_corpus_player_catalog_v1", "catalog_validation"),
        (
            "_build_learning_dataset_partition_preparation_request_from_validated_sources_v1",
            "request_rebuild",
        ),
    ):
        original = getattr(summary_builder_module, name)

        def counted(*args, _key=key, _original=original, **kwargs):
            calls[_key] += 1
            return _original(*args, **kwargs)

        monkeypatch.setattr(summary_builder_module, name, counted)

    import skat_ai.learning_dataset_v2_partition_preparation as partition_module

    original_generator = partition_module.generate_learning_dataset_partition_plan_v1

    def counted_generator(*args, **kwargs):
        calls["plan_generation"] += 1
        return original_generator(*args, **kwargs)

    monkeypatch.setattr(
        partition_module,
        "generate_learning_dataset_partition_plan_v1",
        counted_generator,
    )
    build_learning_dataset_v2_cross_game_summary_v1(
        dataset,
        catalog,
        known_player_partition_result=known,
        unseen_player_partition_result=unseen,
    )
    assert calls == {
        "dataset_validation": 1,
        "catalog_validation": 1,
        "request_rebuild": 2,
        "plan_generation": 0,
    }


def test_builder_traverses_each_exact_summary_source_collection_once(
    monkeypatch,
) -> None:
    known_request, dataset, catalog = _known_bundle()
    known = prepare_learning_dataset_v2_partitions_v1(known_request)
    unseen = prepare_learning_dataset_v2_partitions_v1(
        build_learning_dataset_partition_preparation_request_v1(
            dataset,
            catalog,
            mode="unseen_player",
            base_random_seed=known_request.base_random_seed,
            partition_weights=known_request.partition_weights,
        )
    )
    assert known.status == "complete"
    traversed = []
    original = summary_builder_module._traverse_source_once

    def counted(values):
        traversed.append(values)
        return original(values)

    monkeypatch.setattr(summary_builder_module, "_traverse_source_once", counted)
    monkeypatch.setattr(
        type(known),
        "_validate",
        lambda _self: pytest.fail("Summary build must not revalidate source-backed Results."),
    )
    build_learning_dataset_v2_cross_game_summary_v1(
        dataset,
        catalog,
        known_player_partition_result=known,
        unseen_player_partition_result=unseen,
    )

    expected = (
        catalog.players,
        dataset.records,
        dataset.skipped_decisions,
        dataset.strategy_teacher_evidences,
        dataset.commentary_evidences,
        dataset.response_evidences,
    )
    assert len(traversed) == len(expected)
    assert all(
        actual is expected_value for actual, expected_value in zip(traversed, expected, strict=True)
    )


def test_match_reconciliation_rejects_seat_permutation_and_foreign_skipped_actor() -> None:
    dataset, catalog, _known, _unseen, _summary = _summary_sources(
        _complete_rich_store(),
        dataset_id="dataset-summary-match-reconciliation",
    )
    source = dataset.records[0].source_context
    original_forehand = source.forehand_player_id
    original_middlehand = source.middlehand_player_id
    object.__setattr__(source, "forehand_player_id", original_middlehand)
    object.__setattr__(source, "middlehand_player_id", original_forehand)
    try:
        with pytest.raises(ValueError, match="Match facts"):
            summary_builder_module._build_indexes(dataset, catalog)
    finally:
        object.__setattr__(source, "forehand_player_id", original_forehand)
        object.__setattr__(source, "middlehand_player_id", original_middlehand)

    _, snapshot = _rich_snapshot()
    partial_dataset, partial_catalog, *_ = _summary_sources(
        _store(snapshot, current=(snapshot,)),
        dataset_id="dataset-summary-skipped-reconciliation",
    )
    skipped = partial_dataset.skipped_decisions[0]
    original_actor = skipped.acting_player_id
    object.__setattr__(skipped, "acting_player_id", "foreign-player")
    try:
        with pytest.raises(ValueError, match="Skipped Decision"):
            summary_builder_module._build_indexes(partial_dataset, partial_catalog)
    finally:
        object.__setattr__(skipped, "acting_player_id", original_actor)


def test_summary_and_export_identities_serialization_and_privacy_are_exact(
    complete_summary_bundle,
) -> None:
    _dataset_value, _catalog, _known, _unseen, summary = complete_summary_bundle
    summary_material = summary.to_dict()
    del summary_material["cross_game_summary_fingerprint"]
    assert summary.cross_game_summary_fingerprint == _hash(
        _CROSS_GAME_SUMMARY_FINGERPRINT_DOMAIN,
        summary_material,
    )
    export = build_learning_dataset_v2_cross_game_summary_export_v1(summary)
    identity_material = {
        "learning_dataset_summary_export_version": 1,
        "document_kind": LEARNING_DATASET_SUMMARY_DOCUMENT_KIND,
        "summary_fingerprint": summary.cross_game_summary_fingerprint,
        "cross_game_summary": summary.to_dict(),
    }
    assert export.export_id == _hash(_SUMMARY_EXPORT_ID_DOMAIN, identity_material)
    encoded = serialize_learning_dataset_v2_cross_game_summary_export_v1(export)
    assert encoded == (
        json.dumps(export.to_dict(), ensure_ascii=True, allow_nan=False, indent=2) + "\n"
    ).encode("utf-8")
    assert encoded.endswith(b"\n") and not encoded.endswith(b"\n\n")
    assert b"\r" not in encoded and not encoded.startswith(b"\xef\xbb\xbf")
    assert export.to_dict() is not export.to_dict()
    assert inspect.signature(
        serialize_learning_dataset_v2_cross_game_summary_export_v1
    ).parameters.keys() == {"export"}
    document = export.to_dict()
    serialized = json.dumps(document).lower()
    forbidden = (
        "own_hand",
        "known_skat_cards",
        "discarded_cards",
        "commentator_name",
        '"text"',
        "source_url",
        "statistics_record",
        "candidate_results",
        "search_world",
        "model_ready",
        "production_ready",
        "player_rating",
        "ranking",
        "quality_score",
    )
    for value in forbidden:
        assert value not in serialized
    assert "learning_dataset" not in document["cross_game_summary"]
    assert "player_catalog" not in document["cross_game_summary"]
    assert "assignments" not in serialized
    assert "partitioned_view" not in serialized


def test_summary_modules_keep_private_transport_and_execution_import_boundaries() -> None:
    forbidden_prefixes = (
        "skat_ai.api",
        "skat_ai.capture_web",
        "skat_ai.cli",
        "skat_ai.application",
        "skat_ai.match_decision_analysis",
        "skat_ai.match_historical_analysis",
        "skat_ai.replay_coaching",
    )
    for module in (
        summary_contracts_module,
        summary_builder_module,
        summary_export_module,
    ):
        tree = ast.parse(inspect.getsource(module))
        imported_modules = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imported_modules.append(node.module)
        assert not any(
            imported == prefix or imported.startswith(f"{prefix}.")
            for imported in imported_modules
            for prefix in forbidden_prefixes
        )
