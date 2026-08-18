import inspect
import json
import tomllib
from dataclasses import FrozenInstanceError, fields, replace
from pathlib import Path

import pytest
from test_learning_corpus_human_evidence import _rich_snapshot, _store
from test_learning_corpus_player_catalog_and_statistics import _match_snapshot, _participant
from test_learning_corpus_strategy_teacher import _source_bundle
from test_learning_dataset_v2 import _dataset, _rich_snapshot_for_definition
from test_match_workspace_contracts import _definition, _observed_game, _set_game

import skat_ai
import skat_ai.api.v1 as api_v1
import skat_ai.cli as cli
import skat_ai.learning_dataset_v2_partition_preparation as preparation_module
from scripts.validate_generated_outputs_schema import SCENARIOS
from skat_ai.api.v1 import WorkflowV1
from skat_ai.dataset_partition_policy import CANONICAL_DATASET_PARTITIONS
from skat_ai.learning_corpus_match_snapshot import (
    build_learning_corpus_match_snapshot_v1,
)
from skat_ai.learning_corpus_player_catalog import (
    build_learning_corpus_player_catalog_v1,
)
from skat_ai.learning_dataset_v2_contracts import LEARNING_DATASET_VERSION
from skat_ai.learning_dataset_v2_partition_algorithms import (
    build_learning_dataset_partition_balance_objective_v1,
    build_learning_dataset_player_components_v1,
    generate_component_balanced_unseen_player_match_group_assignments_v1,
    generate_temporal_known_player_match_group_assignments_v1,
)
from skat_ai.learning_dataset_v2_partition_audit import (
    audit_learning_dataset_v2_partitions_v1,
)
from skat_ai.learning_dataset_v2_partition_contracts import (
    COMPONENT_BALANCED_UNSEEN_PLAYER_MATCH_GROUP_ALGORITHM,
    LEARNING_DATASET_EQUAL_TIME_POLICY,
    LEARNING_DATASET_EVIDENCE_COHORT_POLICY,
    LEARNING_DATASET_KNOWN_PLAYER_POLICY,
    LEARNING_DATASET_MATCH_GROUP_VERSION,
    LEARNING_DATASET_PARTITION_ALGORITHMS,
    LEARNING_DATASET_PARTITION_AUDIT_STATUSES,
    LEARNING_DATASET_PARTITION_AUDIT_VERSION,
    LEARNING_DATASET_PARTITION_BALANCE_POLICY,
    LEARNING_DATASET_PARTITION_EXPORT_POLICY,
    LEARNING_DATASET_PARTITION_EXPORT_VERSION,
    LEARNING_DATASET_PARTITION_INFORMATION_POLICY,
    LEARNING_DATASET_PARTITION_MODES,
    LEARNING_DATASET_PARTITION_PLAN_POLICY,
    LEARNING_DATASET_PARTITION_PLAN_STATUSES,
    LEARNING_DATASET_PARTITION_PLAN_VERSION,
    LEARNING_DATASET_PARTITION_PREPARATION_VERSION,
    LEARNING_DATASET_PARTITION_PRIVACY_POLICY,
    LEARNING_DATASET_PARTITION_SOURCE_POLICY,
    LEARNING_DATASET_PARTITION_UNAVAILABLE_REASONS,
    LEARNING_DATASET_PARTITION_UNIT_POLICY,
    LEARNING_DATASET_PARTITION_ZERO_RECORD_POLICY,
    LEARNING_DATASET_PARTITIONED_VIEW_POLICY,
    LEARNING_DATASET_PARTITIONED_VIEW_VERSION,
    LEARNING_DATASET_PARTITIONS,
    LEARNING_DATASET_PLAYER_COMPONENT_VERSION,
    LEARNING_DATASET_SEED_POLICY,
    LEARNING_DATASET_STATISTICS_CONTEXT_POLICY,
    LEARNING_DATASET_UNSEEN_PLAYER_POLICY,
    TEMPORAL_KNOWN_PLAYER_MATCH_GROUP_ALGORITHM,
    LearningDatasetMatchGroupV1,
    LearningDatasetMatchPartitionAssignmentV1,
    LearningDatasetPartitionWeightsV1,
)
from skat_ai.learning_dataset_v2_partition_export import (
    LEARNING_DATASET_PARTITION_DOCUMENT_KIND,
    build_learning_dataset_partition_preparation_export_v1,
    serialize_learning_dataset_partition_preparation_export_v1,
)
from skat_ai.learning_dataset_v2_partition_identity import (
    LEARNING_DATASET_KNOWN_PLAYER_SEED_DOMAIN,
    LEARNING_DATASET_UNSEEN_PLAYER_SEED_DOMAIN,
    build_learning_dataset_match_group_id_v1,
    build_learning_dataset_partition_plan_fingerprint_v1,
    build_learning_dataset_partition_source_content_fingerprint_v1,
    build_learning_dataset_partition_source_identity_fingerprint_v1,
    build_learning_dataset_partitioned_view_fingerprint_v1,
    derive_learning_dataset_partition_seed_v1,
    derive_learning_dataset_partition_tie_break_key_v1,
)
from skat_ai.learning_dataset_v2_partition_preparation import (
    build_learning_dataset_partition_preparation_request_v1,
    derive_learning_dataset_match_groups_v1,
    generate_learning_dataset_partition_plan_v1,
    prepare_learning_dataset_v2_partitions_v1,
)
from skat_ai.match_workspace_contracts import create_match_workspace_v1
from skat_ai.match_workspace_persistence_codec import (
    build_match_workspace_persistence_document_v1,
)
from skat_ai.training_dataset import (
    TRAINING_DATASET_SCHEMA_VERSION,
    TRAINING_FEATURE_GENERATION_VERSION,
    TRAINING_TARGET,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _known_bundle(*, include_inactive=False, mode="known_player", seed=17):
    _, source = _rich_snapshot()
    participants = source.workspace.match_definition.participants
    snapshots = tuple(
        _rich_snapshot_for_definition(
            _definition(
                match_id=f"partition-match-{index}",
                played_at=f"2026-08-0{index}T10:00:00Z",
                participants=participants,
            )
        )
        for index in range(1, 4)
    )
    if include_inactive:
        snapshots = (
            *snapshots,
            _match_snapshot(
                "partition-match-inactive",
                played_at="2026-08-04T10:00:00Z",
                participants=participants,
            ),
        )
    store = _store(*snapshots, current=snapshots)
    dataset = _dataset(store, dataset_id="dataset-177")
    catalog = build_learning_corpus_player_catalog_v1(store)
    request = build_learning_dataset_partition_preparation_request_v1(
        dataset,
        catalog,
        mode=mode,
        base_random_seed=seed,
        partition_weights=LearningDatasetPartitionWeightsV1(
            train=1,
            validation=1,
            test=1,
        ),
    )
    return request, dataset, catalog


def _disjoint_snapshot(index: int):
    _, source = _rich_snapshot()
    source_game = source.workspace.slots[2].observed_game
    assert source_game is not None
    old_ids = tuple(item.player_id for item in source.workspace.match_definition.participants)
    new_ids = tuple(f"component-{index}-player-{item}" for item in "abc")
    replacements = dict(zip(old_ids, new_ids, strict=True))
    participants = tuple(
        _participant(
            player_id,
            table_place,
            label=None,
            platform_player_id=None,
        )
        for player_id, table_place in zip(
            new_ids,
            ("place_1", "place_2", "place_3"),
            strict=True,
        )
    )
    definition = _definition(
        match_id=f"unseen-match-{index}",
        played_at=f"2026-09-0{index}T10:00:00Z",
        participants=participants,
        perspective_player_id=replacements[source.workspace.match_definition.perspective_player_id],
    )
    game = _observed_game(
        definition,
        match_position=3,
        game_id=f"unseen-game-{index}",
        game_timecode=source_game.game_timecode,
        perspective_initial_hand=source_game.perspective_initial_hand,
        declarer_player_id=replacements[source_game.declarer_player_id],
        declaration=source_game.declaration,
        original_skat=source_game.original_skat,
        discarded_cards=source_game.discarded_cards,
        plays=tuple(
            replace(play, player_id=replacements[play.player_id]) for play in source_game.plays
        ),
    )
    workspace = _set_game(create_match_workspace_v1(definition), game)
    return build_learning_corpus_match_snapshot_v1(
        build_match_workspace_persistence_document_v1(workspace)
    )


def _skipped_only_snapshot(index: int):
    _, source = _rich_snapshot()
    source_game = source.workspace.slots[2].observed_game
    assert source_game is not None
    definition = _definition(
        match_id=f"skipped-only-match-{index}",
        played_at=f"2026-08-0{index}T10:00:00Z",
        participants=source.workspace.match_definition.participants,
    )
    game = _observed_game(
        definition,
        match_position=3,
        game_id=f"skipped-only-game-{index}",
        game_timecode=source_game.game_timecode,
        perspective_initial_hand=None,
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


def _hash_id(prefix: str, index: int) -> str:
    import hashlib

    return hashlib.sha256(f"{prefix}-{index}".encode()).hexdigest()


def _group(
    index: int,
    players: tuple[str, str, str],
    *,
    record_count: int = 1,
    skipped_count: int = 0,
    played_at: str | None = None,
) -> LearningDatasetMatchGroupV1:
    snapshot_id = _hash_id("snapshot", index)
    record_ids = tuple(_hash_id(f"record-{index}", item) for item in range(record_count))
    skipped_ids = tuple(_hash_id(f"skipped-{index}", item) for item in range(skipped_count))
    match_id = f"match-{index}"
    player_ids = tuple(sorted(players))
    played_at = played_at or f"2026-01-{index:02d}T00:00:00Z"
    return LearningDatasetMatchGroupV1(
        learning_dataset_match_group_version=LEARNING_DATASET_MATCH_GROUP_VERSION,
        match_group_id=build_learning_dataset_match_group_id_v1(
            match_snapshot_id=snapshot_id,
            match_id=match_id,
            played_at=played_at,
            player_ids=player_ids,
            record_ids=record_ids,
            skipped_decision_ids=skipped_ids,
        ),
        match_snapshot_id=snapshot_id,
        match_id=match_id,
        played_at=played_at,
        player_ids=player_ids,
        record_ids=record_ids,
        skipped_decision_ids=skipped_ids,
        record_count=record_count,
        skipped_decision_count=skipped_count,
        observed_decision_count=record_count + skipped_count,
        strategy_teacher_evidence_count=index,
        commentary_evidence_count=index + 1,
        response_evidence_count=index + 2,
        unjoined_commentary_evidence_count=skipped_count,
        unjoined_response_evidence_count=skipped_count,
        zero_record=record_count == 0,
    )


def test_versions_modes_algorithms_reasons_policies_and_domains_are_exact() -> None:
    assert (
        LEARNING_DATASET_PARTITION_PREPARATION_VERSION,
        LEARNING_DATASET_MATCH_GROUP_VERSION,
        LEARNING_DATASET_PLAYER_COMPONENT_VERSION,
        LEARNING_DATASET_PARTITION_PLAN_VERSION,
        LEARNING_DATASET_PARTITION_AUDIT_VERSION,
        LEARNING_DATASET_PARTITIONED_VIEW_VERSION,
        LEARNING_DATASET_PARTITION_EXPORT_VERSION,
    ) == (1, 1, 1, 1, 1, 1, 1)
    assert (
        LEARNING_DATASET_PARTITIONS
        == CANONICAL_DATASET_PARTITIONS
        == (
            "train",
            "validation",
            "test",
        )
    )
    assert LEARNING_DATASET_PARTITION_MODES == ("known_player", "unseen_player")
    assert LEARNING_DATASET_PARTITION_ALGORITHMS == (
        "temporal_known_player_match_group_v1",
        "component_balanced_unseen_player_match_group_v1",
    )
    assert LEARNING_DATASET_PARTITION_PLAN_STATUSES == ("complete", "unavailable")
    assert LEARNING_DATASET_PARTITION_AUDIT_STATUSES == (
        "compliant",
        "non_compliant",
    )
    assert LEARNING_DATASET_PARTITION_UNAVAILABLE_REASONS == (
        "dataset_has_no_records",
        "insufficient_match_groups",
        "non_empty_record_partition_requirement_unsatisfied",
        "missing_match_played_at",
        "insufficient_time_groups",
        "known_player_train_coverage_unsatisfied",
        "insufficient_player_components",
        "component_distribution_infeasible",
    )
    assert (
        LEARNING_DATASET_PARTITION_SOURCE_POLICY,
        LEARNING_DATASET_PARTITION_UNIT_POLICY,
        LEARNING_DATASET_PARTITION_BALANCE_POLICY,
        LEARNING_DATASET_PARTITION_ZERO_RECORD_POLICY,
        LEARNING_DATASET_KNOWN_PLAYER_POLICY,
        LEARNING_DATASET_UNSEEN_PLAYER_POLICY,
        LEARNING_DATASET_EQUAL_TIME_POLICY,
        LEARNING_DATASET_SEED_POLICY,
        LEARNING_DATASET_EVIDENCE_COHORT_POLICY,
        LEARNING_DATASET_STATISTICS_CONTEXT_POLICY,
        LEARNING_DATASET_PARTITION_PLAN_POLICY,
        LEARNING_DATASET_PARTITIONED_VIEW_POLICY,
        LEARNING_DATASET_PARTITION_INFORMATION_POLICY,
        LEARNING_DATASET_PARTITION_PRIVACY_POLICY,
        LEARNING_DATASET_PARTITION_EXPORT_POLICY,
    ) == (
        "active_explicit_current_match_snapshots_only",
        "match_snapshot_is_indivisible",
        "record_count_primary_match_snapshot_count_secondary",
        "zero_record_active_match_groups_remain_assignment_units",
        "strict_temporal_blocks_with_complete_train_player_coverage",
        "player_connected_match_components_are_indivisible",
        "equal_parsed_played_at_instants_remain_in_one_partition",
        "caller_seed_breaks_exact_objective_ties_only",
        "decision_evidence_follows_match_snapshot_partition",
        "strictly_prior_context_may_be_shared_only_as_recorded_evidence",
        "complete_or_unavailable_without_fallback",
        "lossless_source_dataset_plus_partition_indexes",
        "split_selection_uses_only_ids_times_players_and_counts",
        "private_local_partition_metadata_over_private_learning_data",
        "deterministic_path_free_json_document",
    )
    assert LEARNING_DATASET_KNOWN_PLAYER_SEED_DOMAIN == (
        "learning_dataset_v2_known_player_split_v1"
    )
    assert LEARNING_DATASET_UNSEEN_PLAYER_SEED_DOMAIN == (
        "learning_dataset_v2_unseen_player_split_v1"
    )
    assert LEARNING_DATASET_PARTITION_DOCUMENT_KIND == (
        "skat_ai_learning_dataset_v2_partition_preparation"
    )


def test_weights_are_exact_immutable_positive_integers() -> None:
    weights = LearningDatasetPartitionWeightsV1(train=3, validation=2, test=1)
    assert weights.total_weight == 6
    assert weights.to_dict() == {"train": 3, "validation": 2, "test": 1}
    with pytest.raises(FrozenInstanceError):
        weights.train = 4  # type: ignore[misc]
    for value in (True, 0, -1, 1.0):
        with pytest.raises(ValueError, match="positive integer"):
            LearningDatasetPartitionWeightsV1(
                train=value,  # type: ignore[arg-type]
                validation=1,
                test=1,
            )


def test_exact_ten_term_balance_objective_is_record_then_match() -> None:
    weights = LearningDatasetPartitionWeightsV1(train=3, validation=2, test=1)
    objective = build_learning_dataset_partition_balance_objective_v1(
        record_counts=(5, 2, 2),
        match_counts=(3, 4, 1),
        source_record_count=9,
        source_match_count=8,
        weights=weights,
    )
    assert objective == (12, 6, 3, 6, 3, 16, 8, 6, 8, 2)


def test_known_player_algorithm_groups_equal_instants_and_audits_chronology() -> None:
    groups = (
        _group(1, ("A", "B", "C")),
        _group(2, ("A", "B", "C"), played_at="2026-01-02T00:00:00Z"),
        _group(3, ("A", "B", "C"), played_at="2026-01-02T01:00:00+01:00"),
        _group(4, ("A", "B", "C")),
    )
    result = generate_temporal_known_player_match_group_assignments_v1(
        groups,
        weights=LearningDatasetPartitionWeightsV1(train=1, validation=2, test=1),
        base_random_seed=7,
        source_identity_fingerprint="a" * 64,
    )
    assert result.status == "complete"
    assert tuple(item.partition for item in result.assignments) == (
        "train",
        "validation",
        "validation",
        "test",
    )
    audit = result.known_player_temporal_audit
    assert audit is not None
    assert audit.time_group_count == 3
    assert audit.strict_partition_order is True
    assert audit.equal_timestamp_groups_preserved is True
    assert audit.validation_train_coverage_complete is True
    assert audit.test_train_coverage_complete is True
    assert audit.partition_boundaries[1].minimum_played_at == "2026-01-02T00:00:00Z"


def test_known_player_unavailable_reason_precedence_is_exact() -> None:
    missing = (
        _group(1, ("A", "B", "C")),
        _group(2, ("A", "B", "C"), played_at=None),
        _group(3, ("A", "B", "C")),
    )
    object.__setattr__(missing[1], "played_at", None)
    result = generate_temporal_known_player_match_group_assignments_v1(
        missing,
        weights=LearningDatasetPartitionWeightsV1(train=1, validation=1, test=1),
        base_random_seed=1,
        source_identity_fingerprint="b" * 64,
    )
    assert result.unavailable_reason == "missing_match_played_at"

    uncovered = tuple(
        _group(index, (f"A{index}", f"B{index}", f"C{index}")) for index in range(1, 4)
    )
    result = generate_temporal_known_player_match_group_assignments_v1(
        uncovered,
        weights=LearningDatasetPartitionWeightsV1(train=1, validation=1, test=1),
        base_random_seed=1,
        source_identity_fingerprint="c" * 64,
    )
    assert result.unavailable_reason == "known_player_train_coverage_unsatisfied"


def test_player_components_are_transitive_and_keep_skipped_only_groups() -> None:
    groups = (
        _group(1, ("A", "B", "C")),
        _group(2, ("C", "D", "E"), record_count=0, skipped_count=1),
        _group(3, ("E", "F", "G")),
        _group(4, ("H", "I", "J")),
    )
    components = build_learning_dataset_player_components_v1(groups)
    connected = next(item for item in components if item.match_snapshot_count == 3)
    assert connected.record_count == 2
    assert connected.skipped_decision_count == 1
    assert connected.observed_decision_count == 3
    assert connected.player_ids == tuple("ABCDEFG")
    assert len(connected.component_id) == 64


def test_unseen_player_algorithm_is_disjoint_indivisible_and_locally_optimal() -> None:
    groups = (
        _group(1, ("A", "B", "C"), record_count=3),
        _group(2, ("D", "E", "F"), record_count=2),
        _group(3, ("G", "H", "I")),
        _group(4, ("J", "K", "L")),
        _group(5, ("M", "N", "O"), record_count=0, skipped_count=1),
    )
    result = generate_component_balanced_unseen_player_match_group_assignments_v1(
        groups,
        weights=LearningDatasetPartitionWeightsV1(train=3, validation=2, test=1),
        base_random_seed=11,
        source_identity_fingerprint="d" * 64,
    )
    assert result.status == "complete"
    audit = result.unseen_player_component_audit
    assert audit is not None
    assert audit.player_disjoint is True
    assert audit.components_indivisible is True
    assert audit.all_partitions_have_records is True
    assert audit.local_move_optimal is True
    assert audit.local_swap_optimal is True
    assert set(item.partition for item in result.assignments) == {
        "train",
        "validation",
        "test",
    }


def test_unseen_swaps_preserve_positive_records_and_seed_does_not_change_objective() -> None:
    zero_groups = tuple(
        _group(
            index + 1,
            (f"A{index}", f"B{index}", f"C{index}"),
            record_count=record_count,
            skipped_count=int(record_count == 0),
        )
        for index, record_count in enumerate((0, 1, 1, 1))
    )
    zero_result = generate_component_balanced_unseen_player_match_group_assignments_v1(
        zero_groups,
        weights=LearningDatasetPartitionWeightsV1(train=1, validation=1, test=3),
        base_random_seed=0,
        source_identity_fingerprint="1" * 64,
    )
    assert zero_result.status == "complete"
    assert zero_result.unseen_player_component_audit is not None
    assert zero_result.unseen_player_component_audit.all_partitions_have_records is True

    groups = tuple(
        _group(
            index + 10,
            (f"D{index}", f"E{index}", f"F{index}"),
            record_count=record_count,
        )
        for index, record_count in enumerate((2, 4, 5, 5))
    )
    weights = LearningDatasetPartitionWeightsV1(train=3, validation=2, test=3)
    objectives = []
    for seed in (0, 1, 99):
        result = generate_component_balanced_unseen_player_match_group_assignments_v1(
            groups,
            weights=weights,
            base_random_seed=seed,
            source_identity_fingerprint="2" * 64,
        )
        mapping = {item.match_snapshot_id: item.partition for item in result.assignments}
        record_counts = tuple(
            sum(
                group.record_count
                for group in groups
                if mapping[group.match_snapshot_id] == partition
            )
            for partition in LEARNING_DATASET_PARTITIONS
        )
        match_counts = tuple(
            sum(mapping[group.match_snapshot_id] == partition for group in groups)
            for partition in LEARNING_DATASET_PARTITIONS
        )
        objectives.append(
            build_learning_dataset_partition_balance_objective_v1(
                record_counts=record_counts,
                match_counts=match_counts,
                source_record_count=16,
                source_match_count=4,
                weights=weights,
            )
        )
    assert len(set(objectives)) == 1


def test_complete_unseen_preparation_uses_real_disjoint_current_snapshots() -> None:
    snapshots = tuple(_disjoint_snapshot(index) for index in range(1, 4))
    store = _store(*snapshots, current=snapshots)
    dataset = _dataset(store, dataset_id="dataset-unseen-177")
    catalog = build_learning_corpus_player_catalog_v1(store)
    request = build_learning_dataset_partition_preparation_request_v1(
        dataset,
        catalog,
        mode="unseen_player",
        base_random_seed=23,
        partition_weights=LearningDatasetPartitionWeightsV1(
            train=1,
            validation=1,
            test=1,
        ),
    )
    result = prepare_learning_dataset_v2_partitions_v1(request)
    assert result.status == "complete"
    assert result.plan.algorithm == (COMPONENT_BALANCED_UNSEEN_PLAYER_MATCH_GROUP_ALGORITHM)
    assert result.plan.unseen_player_component_audit is not None
    assert result.plan.unseen_player_component_audit.player_disjoint is True
    assert result.plan.leakage_audit is not None
    assert result.plan.leakage_audit.status == "compliant"
    assert result.plan.leakage_audit.shared_statistics_observation_ids == ()
    assert result.partitioned_view is not None
    assert (
        sum(len(item.record_ids) for item in result.partitioned_view.partitions)
        == dataset.record_count
    )


def test_complete_known_preparation_keeps_skipped_only_group_and_unjoined_evidence() -> None:
    _, source = _rich_snapshot()
    participants = source.workspace.match_definition.participants
    snapshots = (
        _rich_snapshot_for_definition(
            _definition(
                match_id="skipped-cohort-match-1",
                played_at="2026-08-01T10:00:00Z",
                participants=participants,
            )
        ),
        _skipped_only_snapshot(2),
        _rich_snapshot_for_definition(
            _definition(
                match_id="skipped-cohort-match-3",
                played_at="2026-08-03T10:00:00Z",
                participants=participants,
            )
        ),
        _rich_snapshot_for_definition(
            _definition(
                match_id="skipped-cohort-match-4",
                played_at="2026-08-04T10:00:00Z",
                participants=participants,
            )
        ),
    )
    store = _store(*snapshots, current=snapshots)
    dataset = _dataset(store, dataset_id="dataset-skipped-only-cohort")
    catalog = build_learning_corpus_player_catalog_v1(store)
    request = build_learning_dataset_partition_preparation_request_v1(
        dataset,
        catalog,
        mode="known_player",
        base_random_seed=4,
        partition_weights=LearningDatasetPartitionWeightsV1(
            train=1,
            validation=1,
            test=1,
        ),
    )
    result = prepare_learning_dataset_v2_partitions_v1(request)
    assert result.status == "complete"
    assert result.partitioned_view is not None
    skipped_snapshot_id = snapshots[1].match_snapshot_id
    skipped_group = next(
        item
        for item in derive_learning_dataset_match_groups_v1(dataset, catalog)[0]
        if item.match_snapshot_id == skipped_snapshot_id
    )
    assert skipped_group.zero_record is True
    assignment = next(
        item for item in result.plan.assignments if item.match_snapshot_id == skipped_snapshot_id
    )
    partition_slice = next(
        item
        for item in result.partitioned_view.partitions
        if item.partition == assignment.partition
    )
    assert set(skipped_group.skipped_decision_ids) <= set(partition_slice.skipped_decision_ids)
    skipped_ids = set(skipped_group.skipped_decision_ids)
    expected_commentary_ids = {
        evidence_id
        for item in dataset.skipped_decisions
        if item.skipped_decision_id in skipped_ids
        for evidence_id in item.commentary_evidence_ids
        if evidence_id in dataset.unjoined_commentary_evidence_ids
    }
    expected_response_ids = {
        evidence_id
        for item in dataset.skipped_decisions
        if item.skipped_decision_id in skipped_ids
        for evidence_id in (
            *item.outgoing_response_evidence_ids,
            *item.incoming_response_evidence_ids,
        )
        if evidence_id in dataset.unjoined_response_evidence_ids
    }
    assert expected_commentary_ids
    assert expected_response_ids
    assert expected_commentary_ids <= set(
        partition_slice.unjoined_commentary_evidence_ids
    )
    assert expected_response_ids <= set(
        partition_slice.unjoined_response_evidence_ids
    )


def test_seed_and_tie_keys_are_stable_and_mode_separated() -> None:
    known = derive_learning_dataset_partition_seed_v1("known_player", 19, "e" * 64)
    unseen = derive_learning_dataset_partition_seed_v1("unseen_player", 19, "e" * 64)
    assert known != unseen
    assert known == derive_learning_dataset_partition_seed_v1("known_player", 19, "e" * 64)
    assert derive_learning_dataset_partition_tie_break_key_v1(known, "candidate") == (
        derive_learning_dataset_partition_tie_break_key_v1(known, "candidate")
    )


def test_request_reconciliation_groups_inactive_match_and_complete_known_plan() -> None:
    request, dataset, _catalog = _known_bundle(include_inactive=True)
    groups, inactive = derive_learning_dataset_match_groups_v1(
        request.learning_dataset,
        request.player_catalog,
    )
    assert len(groups) == 3
    assert len(inactive) == 1
    assert sum(item.record_count for item in groups) == dataset.record_count
    assert sum(item.skipped_decision_count for item in groups) == (dataset.skipped_decision_count)
    assert all(len(item.player_ids) == 3 for item in groups)
    plan = generate_learning_dataset_partition_plan_v1(request)
    assert plan.status == "complete"
    assert plan.algorithm == TEMPORAL_KNOWN_PLAYER_MATCH_GROUP_ALGORITHM
    assert plan.source_active_match_group_count == 3
    assert plan.source_inactive_match_count == 1
    assert plan.assignments == tuple(
        LearningDatasetMatchPartitionAssignmentV1(
            match_snapshot_id=group.match_snapshot_id,
            partition=partition,
        )
        for group, partition in zip(
            groups,
            LEARNING_DATASET_PARTITIONS,
            strict=True,
        )
    )
    assert plan.leakage_audit is not None
    assert plan.leakage_audit.status == "compliant"
    assert plan.leakage_audit.shared_statistics_observation_ids
    assert all(
        (
            plan.leakage_audit.match_group_closure_complete,
            plan.leakage_audit.record_closure_complete,
            plan.leakage_audit.skipped_decision_closure_complete,
            plan.leakage_audit.teacher_closure_complete,
            plan.leakage_audit.commentary_closure_complete,
            plan.leakage_audit.response_closure_complete,
            plan.leakage_audit.statistics_context_temporal_safety_complete,
        )
    )
    assert plan.leakage_audit.inactive_current_match_snapshot_ids == inactive
    assert plan.plan_fingerprint == build_learning_dataset_partition_plan_fingerprint_v1(plan)


def test_source_identity_ignores_teacher_enrichment_but_content_does_not() -> None:
    _workspace, _snapshot, _result, _report, source, store = _source_bundle()
    catalog = build_learning_corpus_player_catalog_v1(store)
    without = _dataset(store, dataset_id="dataset-evidence", teacher_sources=())
    with_teacher = _dataset(
        store,
        dataset_id="dataset-evidence",
        teacher_sources=(source,),
    )
    assert tuple(item.record_id for item in without.records) == tuple(
        item.record_id for item in with_teacher.records
    )
    identities = []
    contents = []
    for dataset in (without, with_teacher):
        groups, inactive = derive_learning_dataset_match_groups_v1(dataset, catalog)
        identities.append(
            build_learning_dataset_partition_source_identity_fingerprint_v1(
                mode="known_player",
                dataset=dataset,
                active_match_groups=groups,
                inactive_current_match_snapshot_ids=inactive,
            )
        )
        contents.append(
            build_learning_dataset_partition_source_content_fingerprint_v1(
                mode="known_player",
                dataset=dataset,
                player_catalog=catalog,
                active_match_groups=groups,
                inactive_current_match_snapshot_ids=inactive,
            )
        )
    assert identities[0] == identities[1]
    assert contents[0] != contents[1]


def test_common_unavailable_plans_have_no_assignments_summaries_audits_or_view() -> None:
    _, snapshot = _rich_snapshot()
    store = _store(snapshot, current=(snapshot,))
    dataset = _dataset(store)
    catalog = build_learning_corpus_player_catalog_v1(store)
    request = build_learning_dataset_partition_preparation_request_v1(
        dataset,
        catalog,
        mode="known_player",
        base_random_seed=7,
        partition_weights=LearningDatasetPartitionWeightsV1(
            train=1,
            validation=1,
            test=1,
        ),
    )
    result = prepare_learning_dataset_v2_partitions_v1(request)
    assert result.status == "unavailable"
    assert result.unavailable_reason == "insufficient_match_groups"
    assert result.plan.assignments == ()
    assert result.plan.partition_summaries == ()
    assert result.plan.known_player_temporal_audit is None
    assert result.plan.unseen_player_component_audit is None
    assert result.plan.leakage_audit is None
    assert result.partitioned_view is None

    empty_store = _store()
    empty_dataset = _dataset(empty_store, dataset_id="dataset-empty-177")
    empty_catalog = build_learning_corpus_player_catalog_v1(empty_store)
    empty_request = build_learning_dataset_partition_preparation_request_v1(
        empty_dataset,
        empty_catalog,
        mode="unseen_player",
        base_random_seed=7,
        partition_weights=request.partition_weights,
    )
    empty_result = prepare_learning_dataset_v2_partitions_v1(empty_request)
    assert empty_result.unavailable_reason == "dataset_has_no_records"


def test_general_audit_detects_duplicate_unknown_and_unseen_statistics_sharing() -> None:
    known_request, _dataset_value, _catalog = _known_bundle(mode="known_player")
    groups, inactive = derive_learning_dataset_match_groups_v1(
        known_request.learning_dataset,
        known_request.player_catalog,
    )
    valid = tuple(
        LearningDatasetMatchPartitionAssignmentV1(
            match_snapshot_id=group.match_snapshot_id,
            partition=partition,
        )
        for group, partition in zip(groups, LEARNING_DATASET_PARTITIONS, strict=True)
    )
    malformed = (
        *valid,
        LearningDatasetMatchPartitionAssignmentV1(
            match_snapshot_id=groups[0].match_snapshot_id,
            partition="test",
        ),
        LearningDatasetMatchPartitionAssignmentV1(
            match_snapshot_id="f" * 64,
            partition="train",
        ),
    )
    audit = audit_learning_dataset_v2_partitions_v1(
        known_request,
        groups,
        inactive,
        malformed,
        plan_fingerprint="0" * 64,
    )
    assert audit.status == "non_compliant"
    assert audit.duplicate_match_snapshot_assignment_ids == (groups[0].match_snapshot_id,)
    assert audit.unknown_match_snapshot_assignment_ids == ("f" * 64,)
    assert audit.match_snapshot_partition_overlap_ids == (groups[0].match_snapshot_id,)

    unseen_request = build_learning_dataset_partition_preparation_request_v1(
        known_request.learning_dataset,
        known_request.player_catalog,
        mode="unseen_player",
        base_random_seed=7,
        partition_weights=known_request.partition_weights,
    )
    unseen_audit = audit_learning_dataset_v2_partitions_v1(
        unseen_request,
        groups,
        inactive,
        valid,
        plan_fingerprint="0" * 64,
    )
    assert unseen_audit.shared_statistics_observation_ids
    assert unseen_audit.status == "non_compliant"


def test_partition_summaries_view_and_export_are_lossless_and_canonical() -> None:
    request, dataset, _catalog = _known_bundle(include_inactive=True)
    result = prepare_learning_dataset_v2_partitions_v1(request)
    assert result.status == "complete"
    assert result.partitioned_view is not None
    assert result.partitioned_view.learning_dataset is dataset
    assert result.partitioned_view.source_dataset_fingerprint == dataset.dataset_fingerprint
    assert tuple(item.partition for item in result.partitioned_view.partitions) == (
        LEARNING_DATASET_PARTITIONS
    )
    assert sum(len(item.record_ids) for item in result.partitioned_view.partitions) == (
        dataset.record_count
    )
    assert (
        sum(len(item.skipped_decision_ids) for item in result.partitioned_view.partitions)
        == dataset.skipped_decision_count
    )
    assert {
        item_id
        for partition in result.partitioned_view.partitions
        for item_id in partition.commentary_evidence_ids
    } == {item.commentary_evidence_id for item in dataset.commentary_evidences}
    assert {
        item_id
        for partition in result.partitioned_view.partitions
        for item_id in partition.response_evidence_ids
    } == {item.response_evidence_id for item in dataset.response_evidences}
    assert {
        item_id
        for partition in result.partitioned_view.partitions
        for item_id in partition.unjoined_commentary_evidence_ids
    } == set(dataset.unjoined_commentary_evidence_ids)
    assert {
        item_id
        for partition in result.partitioned_view.partitions
        for item_id in partition.unjoined_response_evidence_ids
    } == set(dataset.unjoined_response_evidence_ids)
    assert {
        item_id
        for partition in result.partitioned_view.partitions
        for item_id in partition.statistics_observation_ids
    } == {item.statistics_observation_id for item in dataset.player_statistics_observations}
    assert all("partition" not in record.to_dict() for record in dataset.records)
    summaries = result.plan.partition_summaries
    assert tuple(item.requested_weight for item in summaries) == (1, 1, 1)
    assert tuple(item.match_snapshot_count for item in summaries) == (1, 1, 1)
    assert tuple(item.target_match_count_numerator for item in summaries) == (3, 3, 3)
    assert tuple(item.match_count_deviation_numerator for item in summaries) == (0, 0, 0)

    export = build_learning_dataset_partition_preparation_export_v1(result)
    first = serialize_learning_dataset_partition_preparation_export_v1(export)
    second = serialize_learning_dataset_partition_preparation_export_v1(export)
    assert (
        first
        == second
        == (
            json.dumps(
                export.to_dict(),
                ensure_ascii=True,
                allow_nan=False,
                indent=2,
            )
            + "\n"
        ).encode()
    )
    assert first.endswith(b"\n") and not first.endswith(b"\n\n")
    assert b"\r" not in first
    assert export.request_fingerprint == request.request_fingerprint
    assert export.plan_fingerprint == result.plan.plan_fingerprint
    assert not {"path", "filename", "exported_at"}.intersection(export.to_dict())
    assert (
        "path"
        not in inspect.signature(
            serialize_learning_dataset_partition_preparation_export_v1
        ).parameters
    )

    _, one_snapshot = _rich_snapshot()
    one_store = _store(one_snapshot, current=(one_snapshot,))
    unavailable_dataset = _dataset(one_store, dataset_id="dataset-export-unavailable")
    unavailable_catalog = build_learning_corpus_player_catalog_v1(one_store)
    unavailable_request = build_learning_dataset_partition_preparation_request_v1(
        unavailable_dataset,
        unavailable_catalog,
        mode="known_player",
        base_random_seed=1,
        partition_weights=request.partition_weights,
    )
    unavailable_result = prepare_learning_dataset_v2_partitions_v1(unavailable_request)
    unavailable_export = build_learning_dataset_partition_preparation_export_v1(unavailable_result)
    assert (
        json.loads(serialize_learning_dataset_partition_preparation_export_v1(unavailable_export))[
            "preparation_result"
        ]["status"]
        == "unavailable"
    )


def test_audit_and_plan_contracts_reject_false_compliance_facts() -> None:
    request, _dataset_value, _catalog = _known_bundle()
    plan = generate_learning_dataset_partition_plan_v1(request)
    assert plan.leakage_audit is not None
    with pytest.raises(ValueError, match="Audit status"):
        replace(plan.leakage_audit, record_closure_complete=False)

    assert plan.known_player_temporal_audit is not None
    false_temporal = replace(
        plan.known_player_temporal_audit,
        strict_partition_order=False,
    )
    plan_values = {field.name: getattr(plan, field.name) for field in fields(plan)}
    plan_values["known_player_temporal_audit"] = false_temporal
    with pytest.raises(ValueError, match="plan_fingerprint"):
        type(plan)._from_validated(**plan_values)


def test_complete_plan_rejects_duplicate_assignments_with_recomputed_fingerprint() -> None:
    request, _dataset_value, _catalog = _known_bundle()
    plan = generate_learning_dataset_partition_plan_v1(request)
    assert plan.leakage_audit is not None
    malformed_assignments = (
        plan.assignments[0],
        plan.assignments[0],
        plan.assignments[2],
    )
    serialized = plan.to_dict()
    serialized["assignments"] = [item.to_dict() for item in malformed_assignments]
    fingerprint = build_learning_dataset_partition_plan_fingerprint_v1(serialized)
    plan_values = {field.name: getattr(plan, field.name) for field in fields(plan)}
    plan_values.update(
        assignments=malformed_assignments,
        leakage_audit=replace(plan.leakage_audit, plan_fingerprint=fingerprint),
        plan_fingerprint=fingerprint,
    )

    with pytest.raises(ValueError, match="each active Match Snapshot exactly once"):
        type(plan)._from_validated(**plan_values)


def test_complete_plan_rejects_partition_swap_with_stale_temporal_audit() -> None:
    request, _dataset_value, _catalog = _known_bundle()
    plan = generate_learning_dataset_partition_plan_v1(request)
    assert plan.leakage_audit is not None
    swapped_assignments = tuple(
        replace(
            item,
            partition={"train": "test", "validation": "validation", "test": "train"}[
                item.partition
            ],
        )
        for item in plan.assignments
    )
    serialized = plan.to_dict()
    serialized["assignments"] = [item.to_dict() for item in swapped_assignments]
    fingerprint = build_learning_dataset_partition_plan_fingerprint_v1(serialized)
    plan_values = {field.name: getattr(plan, field.name) for field in fields(plan)}
    plan_values.update(
        assignments=swapped_assignments,
        leakage_audit=replace(plan.leakage_audit, plan_fingerprint=fingerprint),
        plan_fingerprint=fingerprint,
    )

    with pytest.raises(ValueError, match="match the temporal audit"):
        type(plan)._from_validated(**plan_values)


def test_partitioned_view_rejects_omitted_source_indexes_with_recomputed_fingerprint() -> None:
    request, _dataset_value, _catalog = _known_bundle()
    result = prepare_learning_dataset_v2_partitions_v1(request)
    assert result.partitioned_view is not None
    view = result.partitioned_view
    malformed_slices = (
        replace(view.partitions[0], record_ids=()),
        *view.partitions[1:],
    )
    serialized = view.to_dict()
    serialized["partitions"] = [item.to_dict() for item in malformed_slices]
    fingerprint = build_learning_dataset_partitioned_view_fingerprint_v1(serialized)
    view_values = {field.name: getattr(view, field.name) for field in fields(view)}
    view_values.update(
        partitioned_view_fingerprint=fingerprint,
        partitions=malformed_slices,
    )

    with pytest.raises(ValueError, match="losslessly index"):
        type(view)._from_validated(**view_values)


def test_complete_result_rejects_source_inaccurate_partition_summary() -> None:
    request, _dataset_value, _catalog = _known_bundle()
    result = prepare_learning_dataset_v2_partitions_v1(request)
    assert result.partitioned_view is not None
    plan = result.plan
    assert plan.leakage_audit is not None
    malformed_summaries = (
        replace(
            plan.partition_summaries[0],
            commentary_evidence_count=(
                plan.partition_summaries[0].commentary_evidence_count + 1
            ),
        ),
        *plan.partition_summaries[1:],
    )
    serialized_plan = plan.to_dict()
    serialized_plan["partition_summaries"] = [
        item.to_dict() for item in malformed_summaries
    ]
    plan_fingerprint = build_learning_dataset_partition_plan_fingerprint_v1(serialized_plan)
    plan_values = {field.name: getattr(plan, field.name) for field in fields(plan)}
    plan_values.update(
        partition_summaries=malformed_summaries,
        leakage_audit=replace(plan.leakage_audit, plan_fingerprint=plan_fingerprint),
        plan_fingerprint=plan_fingerprint,
    )
    malformed_plan = type(plan)._from_validated(**plan_values)

    view = result.partitioned_view
    serialized_view = view.to_dict()
    serialized_view["plan_fingerprint"] = plan_fingerprint
    view_fingerprint = build_learning_dataset_partitioned_view_fingerprint_v1(serialized_view)
    view_values = {field.name: getattr(view, field.name) for field in fields(view)}
    view_values.update(
        plan_fingerprint=plan_fingerprint,
        partitioned_view_fingerprint=view_fingerprint,
    )
    malformed_view = type(view)._from_validated(**view_values)
    result_values = {field.name: getattr(result, field.name) for field in fields(result)}
    result_values.update(plan=malformed_plan, partitioned_view=malformed_view)

    with pytest.raises(ValueError, match="exact source cohorts"):
        type(result)._from_validated(**result_values)


def test_generation_executes_one_group_derivation_algorithm_audit_and_plan_hash(
    monkeypatch,
) -> None:
    request, _dataset_value, _catalog = _known_bundle()
    names = (
        "derive_learning_dataset_match_groups_v1",
        "generate_temporal_known_player_match_group_assignments_v1",
        "audit_learning_dataset_v2_partitions_v1",
        "build_learning_dataset_partition_plan_fingerprint_v1",
    )
    calls = dict.fromkeys(names, 0)
    for name in names:
        original = getattr(preparation_module, name)

        def counted(*args, _name=name, _original=original, **kwargs):
            calls[_name] += 1
            return _original(*args, **kwargs)

        monkeypatch.setattr(preparation_module, name, counted)
    plan = preparation_module.generate_learning_dataset_partition_plan_v1(request)
    assert plan.status == "complete"
    assert calls == dict.fromkeys(names, 1)


def test_private_architecture_and_compatibility_baselines_remain_unchanged() -> None:
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text())
    assert pyproject["project"]["version"] == "0.16.0"
    assert pyproject["project"]["requires-python"] == ">=3.13"
    assert pyproject["project"]["scripts"] == {"skat-ai": "skat_ai.cli:main"}
    assert LEARNING_DATASET_VERSION == 2
    assert TRAINING_DATASET_SCHEMA_VERSION == 1
    assert TRAINING_FEATURE_GENERATION_VERSION == 1
    assert TRAINING_TARGET == "actual_card_played"
    assert len(WorkflowV1) == 7
    assert len(SCENARIOS) == 85
    assert len(tuple((PROJECT_ROOT / "schemas").glob("*.schema.json"))) == 63
    assert len(tuple((PROJECT_ROOT / "src/skat_ai/schema_resources").glob("*.schema.json"))) == 63
    assert len(tuple((PROJECT_ROOT / "examples").glob("session_*.json"))) == 6
    for namespace in (skat_ai, api_v1, cli):
        assert not hasattr(namespace, "LearningDatasetPartitionPlanV1")
        assert not hasattr(namespace, "prepare_learning_dataset_v2_partitions_v1")
    assert all(
        COMPONENT_BALANCED_UNSEEN_PLAYER_MATCH_GROUP_ALGORITHM
        not in path.read_text(encoding="utf-8")
        for path in (
            PROJECT_ROOT / "src/skat_ai/training_dataset_preparation.py",
            PROJECT_ROOT / "src/skat_ai/dataset_partition_plan.py",
        )
    )
