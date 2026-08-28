from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from skatmind.learning_dataset_v2_partition_contracts import (
    COMPONENT_BALANCED_UNSEEN_PLAYER_MATCH_GROUP_ALGORITHM,
    LEARNING_DATASET_PARTITIONS,
    LEARNING_DATASET_PLAYER_COMPONENT_VERSION,
    TEMPORAL_KNOWN_PLAYER_MATCH_GROUP_ALGORITHM,
    LearningDatasetKnownPlayerTemporalAuditV1,
    LearningDatasetMatchGroupV1,
    LearningDatasetMatchPartitionAssignmentV1,
    LearningDatasetPartitionWeightsV1,
    LearningDatasetPlayerComponentV1,
    LearningDatasetTemporalPartitionBoundaryV1,
    LearningDatasetUnseenPlayerComponentAuditV1,
)
from skatmind.learning_dataset_v2_partition_identity import (
    build_learning_dataset_player_component_id_v1,
    derive_learning_dataset_partition_seed_v1,
    derive_learning_dataset_partition_tie_break_key_v1,
)
from skatmind.rfc3339 import parse_rfc3339_datetime


@dataclass(frozen=True, slots=True)
class _PartitionAlgorithmResult:
    status: Literal["complete", "unavailable"]
    unavailable_reason: str | None
    assignments: tuple[LearningDatasetMatchPartitionAssignmentV1, ...]
    known_player_temporal_audit: LearningDatasetKnownPlayerTemporalAuditV1 | None
    unseen_player_component_audit: LearningDatasetUnseenPlayerComponentAuditV1 | None


@dataclass(frozen=True, slots=True)
class _TimeGroup:
    instant: datetime
    canonical_played_at: str
    match_groups: tuple[LearningDatasetMatchGroupV1, ...]
    player_ids: frozenset[str]
    record_count: int


@dataclass(frozen=True, slots=True)
class _TemporalCandidate:
    train_cut: int
    validation_cut: int
    objective: tuple[int, ...]
    stable_identity: str


@dataclass(frozen=True, slots=True)
class _AllocationOperation:
    kind: Literal["move", "swap"]
    component_ids: tuple[str, ...]
    target_partitions: tuple[str, ...]
    resulting_objective: tuple[int, ...]
    stable_identity: str


def build_learning_dataset_partition_balance_objective_v1(
    *,
    record_counts: tuple[int, int, int],
    match_counts: tuple[int, int, int],
    source_record_count: int,
    source_match_count: int,
    weights: LearningDatasetPartitionWeightsV1,
) -> tuple[int, ...]:
    """Builds the exact Record-primary, Match-secondary integer objective."""
    total_weight = weights.total_weight
    partition_weights = (weights.train, weights.validation, weights.test)

    def metrics(counts: tuple[int, int, int], source_count: int) -> tuple[int, ...]:
        deviations = tuple(
            abs(count * total_weight - source_count * weight)
            for count, weight in zip(counts, partition_weights, strict=True)
        )
        return (sum(deviations), max(deviations), *deviations)

    return (
        *metrics(record_counts, source_record_count),
        *metrics(match_counts, source_match_count),
    )


def _canonical_instant(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _counts_for_assignment(
    groups: tuple[LearningDatasetMatchGroupV1, ...],
    partition_by_snapshot: dict[str, str],
) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    records = []
    matches = []
    for partition in LEARNING_DATASET_PARTITIONS:
        selected = tuple(
            group
            for group in groups
            if partition_by_snapshot.get(group.match_snapshot_id) == partition
        )
        records.append(sum(group.record_count for group in selected))
        matches.append(len(selected))
    return (tuple(records), tuple(matches))  # type: ignore[return-value]


def _objective_for_assignment(
    groups: tuple[LearningDatasetMatchGroupV1, ...],
    partition_by_snapshot: dict[str, str],
    weights: LearningDatasetPartitionWeightsV1,
) -> tuple[int, ...]:
    record_counts, match_counts = _counts_for_assignment(groups, partition_by_snapshot)
    return build_learning_dataset_partition_balance_objective_v1(
        record_counts=record_counts,
        match_counts=match_counts,
        source_record_count=sum(group.record_count for group in groups),
        source_match_count=len(groups),
        weights=weights,
    )


def _build_time_groups(
    groups: tuple[LearningDatasetMatchGroupV1, ...],
) -> tuple[_TimeGroup, ...]:
    grouped: dict[datetime, list[LearningDatasetMatchGroupV1]] = {}
    for group in groups:
        if group.played_at is None:
            raise ValueError("Time groups require played_at on every active Match group.")
        instant = parse_rfc3339_datetime(
            group.played_at,
            f"Match Snapshot '{group.match_snapshot_id}' played_at",
        )
        grouped.setdefault(instant, []).append(group)
    return tuple(
        _TimeGroup(
            instant=instant,
            canonical_played_at=_canonical_instant(instant),
            match_groups=tuple(
                sorted(values, key=lambda item: (item.match_id, item.match_snapshot_id))
            ),
            player_ids=frozenset(player_id for item in values for player_id in item.player_ids),
            record_count=sum(item.record_count for item in values),
        )
        for instant, values in sorted(grouped.items())
    )


def _temporal_candidate_identity(
    time_groups: tuple[_TimeGroup, ...],
    train_cut: int,
    validation_cut: int,
) -> str:
    return json.dumps(
        {
            "algorithm": TEMPORAL_KNOWN_PLAYER_MATCH_GROUP_ALGORITHM,
            "train_end": time_groups[train_cut - 1].canonical_played_at,
            "validation_end": time_groups[validation_cut - 1].canonical_played_at,
        },
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _candidate_partition_mapping(
    time_groups: tuple[_TimeGroup, ...],
    train_cut: int,
    validation_cut: int,
) -> dict[str, str]:
    return {
        group.match_snapshot_id: partition
        for partition, selected_time_groups in (
            ("train", time_groups[:train_cut]),
            ("validation", time_groups[train_cut:validation_cut]),
            ("test", time_groups[validation_cut:]),
        )
        for time_group in selected_time_groups
        for group in time_group.match_groups
    }


def _build_known_player_audit(
    time_groups: tuple[_TimeGroup, ...],
    partition_by_snapshot: dict[str, str],
) -> LearningDatasetKnownPlayerTemporalAuditV1:
    groups_by_partition = {
        partition: tuple(
            group
            for time_group in time_groups
            for group in time_group.match_groups
            if partition_by_snapshot[group.match_snapshot_id] == partition
        )
        for partition in LEARNING_DATASET_PARTITIONS
    }
    instants_by_partition = {
        partition: tuple(
            time_group.instant
            for time_group in time_groups
            if any(
                partition_by_snapshot[group.match_snapshot_id] == partition
                for group in time_group.match_groups
            )
        )
        for partition in LEARNING_DATASET_PARTITIONS
    }
    players = {
        partition: {
            player_id for group in groups_by_partition[partition] for player_id in group.player_ids
        }
        for partition in LEARNING_DATASET_PARTITIONS
    }
    train_players = players["train"]
    validation_uncovered = players["validation"] - train_players
    test_uncovered = players["test"] - train_players
    boundaries = tuple(
        LearningDatasetTemporalPartitionBoundaryV1(
            partition=partition,
            minimum_played_at=_canonical_instant(min(instants_by_partition[partition])),
            maximum_played_at=_canonical_instant(max(instants_by_partition[partition])),
            time_group_count=len(instants_by_partition[partition]),
            match_snapshot_count=len(groups_by_partition[partition]),
            record_count=sum(group.record_count for group in groups_by_partition[partition]),
        )
        for partition in LEARNING_DATASET_PARTITIONS
    )
    return LearningDatasetKnownPlayerTemporalAuditV1(
        partition_boundaries=boundaries,
        train_match_snapshot_ids=tuple(
            sorted(item.match_snapshot_id for item in groups_by_partition["train"])
        ),
        validation_match_snapshot_ids=tuple(
            sorted(item.match_snapshot_id for item in groups_by_partition["validation"])
        ),
        test_match_snapshot_ids=tuple(
            sorted(item.match_snapshot_id for item in groups_by_partition["test"])
        ),
        train_player_ids=tuple(sorted(train_players)),
        validation_player_ids=tuple(sorted(players["validation"])),
        test_player_ids=tuple(sorted(players["test"])),
        validation_covered_player_ids=tuple(sorted(players["validation"] & train_players)),
        validation_uncovered_player_ids=tuple(sorted(validation_uncovered)),
        test_covered_player_ids=tuple(sorted(players["test"] & train_players)),
        test_uncovered_player_ids=tuple(sorted(test_uncovered)),
        all_played_at_present=True,
        time_group_count=len(time_groups),
        strict_partition_order=(
            max(instants_by_partition["train"]) < min(instants_by_partition["validation"])
            and max(instants_by_partition["validation"]) < min(instants_by_partition["test"])
        ),
        equal_timestamp_groups_preserved=True,
        validation_train_coverage_complete=not validation_uncovered,
        test_train_coverage_complete=not test_uncovered,
    )


def generate_temporal_known_player_match_group_assignments_v1(
    groups: tuple[LearningDatasetMatchGroupV1, ...],
    *,
    weights: LearningDatasetPartitionWeightsV1,
    base_random_seed: int,
    source_identity_fingerprint: str,
) -> _PartitionAlgorithmResult:
    """Generates strict chronological Known-player Match blocks."""
    if any(group.played_at is None for group in groups):
        return _PartitionAlgorithmResult("unavailable", "missing_match_played_at", (), None, None)
    time_groups = _build_time_groups(groups)
    if len(time_groups) < 3:
        return _PartitionAlgorithmResult("unavailable", "insufficient_time_groups", (), None, None)

    non_empty_candidates = []
    candidates = []
    for train_cut in range(1, len(time_groups) - 1):
        for validation_cut in range(train_cut + 1, len(time_groups)):
            partition_by_snapshot = _candidate_partition_mapping(
                time_groups,
                train_cut,
                validation_cut,
            )
            record_counts, match_counts = _counts_for_assignment(groups, partition_by_snapshot)
            if any(count == 0 for count in record_counts):
                continue
            objective = build_learning_dataset_partition_balance_objective_v1(
                record_counts=record_counts,
                match_counts=match_counts,
                source_record_count=sum(group.record_count for group in groups),
                source_match_count=len(groups),
                weights=weights,
            )
            stable_identity = _temporal_candidate_identity(
                time_groups,
                train_cut,
                validation_cut,
            )
            non_empty_candidates.append((objective, stable_identity))
            train_players = {
                player_id
                for group in groups
                if partition_by_snapshot[group.match_snapshot_id] == "train"
                for player_id in group.player_ids
            }
            later_players = {
                player_id
                for group in groups
                if partition_by_snapshot[group.match_snapshot_id] != "train"
                for player_id in group.player_ids
            }
            if not later_players <= train_players:
                continue
            candidates.append(
                _TemporalCandidate(
                    train_cut=train_cut,
                    validation_cut=validation_cut,
                    objective=objective,
                    stable_identity=stable_identity,
                )
            )
    if not non_empty_candidates:
        return _PartitionAlgorithmResult(
            "unavailable",
            "non_empty_record_partition_requirement_unsatisfied",
            (),
            None,
            None,
        )
    if not candidates:
        return _PartitionAlgorithmResult(
            "unavailable",
            "known_player_train_coverage_unsatisfied",
            (),
            None,
            None,
        )
    best_objective = min(item.objective for item in candidates)
    tied = tuple(item for item in candidates if item.objective == best_objective)
    if len(tied) == 1:
        selected = tied[0]
    else:
        partition_seed = derive_learning_dataset_partition_seed_v1(
            "known_player",
            base_random_seed,
            source_identity_fingerprint,
        )
        selected = min(
            tied,
            key=lambda item: (
                derive_learning_dataset_partition_tie_break_key_v1(
                    partition_seed,
                    item.stable_identity,
                ),
                item.stable_identity,
            ),
        )
    partition_by_snapshot = _candidate_partition_mapping(
        time_groups,
        selected.train_cut,
        selected.validation_cut,
    )
    assignments = tuple(
        LearningDatasetMatchPartitionAssignmentV1(
            match_snapshot_id=group.match_snapshot_id,
            partition=partition_by_snapshot[group.match_snapshot_id],
        )
        for group in groups
    )
    audit = _build_known_player_audit(time_groups, partition_by_snapshot)
    if not all(
        (
            audit.all_played_at_present,
            audit.strict_partition_order,
            audit.equal_timestamp_groups_preserved,
            audit.validation_train_coverage_complete,
            audit.test_train_coverage_complete,
        )
    ):
        raise RuntimeError("Known-player assignment did not satisfy its temporal audit.")
    return _PartitionAlgorithmResult("complete", None, assignments, audit, None)


def build_learning_dataset_player_components_v1(
    groups: tuple[LearningDatasetMatchGroupV1, ...],
) -> tuple[LearningDatasetPlayerComponentV1, ...]:
    """Builds transitive Match components through exact shared stable Player IDs."""
    parent = {group.match_snapshot_id: group.match_snapshot_id for group in groups}

    def find(snapshot_id: str) -> str:
        root = snapshot_id
        while parent[root] != root:
            root = parent[root]
        while parent[snapshot_id] != snapshot_id:
            next_id = parent[snapshot_id]
            parent[snapshot_id] = root
            snapshot_id = next_id
        return root

    def union(first: str, second: str) -> None:
        first_root = find(first)
        second_root = find(second)
        if first_root != second_root:
            lower, higher = sorted((first_root, second_root))
            parent[higher] = lower

    first_snapshot_by_player: dict[str, str] = {}
    for group in sorted(groups, key=lambda item: item.match_snapshot_id):
        for player_id in group.player_ids:
            first = first_snapshot_by_player.setdefault(player_id, group.match_snapshot_id)
            union(first, group.match_snapshot_id)

    grouped: dict[str, list[LearningDatasetMatchGroupV1]] = {}
    for group in groups:
        grouped.setdefault(find(group.match_snapshot_id), []).append(group)
    components = []
    for values in grouped.values():
        snapshot_ids = tuple(sorted(item.match_snapshot_id for item in values))
        player_ids = tuple(sorted({player_id for item in values for player_id in item.player_ids}))
        components.append(
            LearningDatasetPlayerComponentV1(
                learning_dataset_player_component_version=(
                    LEARNING_DATASET_PLAYER_COMPONENT_VERSION
                ),
                component_id=build_learning_dataset_player_component_id_v1(
                    match_snapshot_ids=snapshot_ids,
                    player_ids=player_ids,
                ),
                match_snapshot_ids=snapshot_ids,
                player_ids=player_ids,
                record_count=sum(item.record_count for item in values),
                skipped_decision_count=sum(item.skipped_decision_count for item in values),
                observed_decision_count=sum(item.observed_decision_count for item in values),
                match_snapshot_count=len(values),
            )
        )
    result = tuple(sorted(components, key=lambda item: item.component_id))
    if sum(item.match_snapshot_count for item in result) != len(groups):
        raise RuntimeError("Player-component construction lost an active Match group.")
    if any(
        set(result[first].player_ids) & set(result[second].player_ids)
        for first in range(len(result))
        for second in range(first + 1, len(result))
    ):
        raise RuntimeError("Player-component construction did not produce disjoint components.")
    return result


def _component_order(
    components: tuple[LearningDatasetPlayerComponentV1, ...],
    partition_seed: int,
) -> tuple[LearningDatasetPlayerComponentV1, ...]:
    return tuple(
        sorted(
            components,
            key=lambda item: (
                -item.record_count,
                -item.match_snapshot_count,
                -len(item.player_ids),
                derive_learning_dataset_partition_tie_break_key_v1(
                    partition_seed,
                    item.component_id,
                ),
                item.component_id,
            ),
        )
    )


def _component_assignment_mapping(
    components: tuple[LearningDatasetPlayerComponentV1, ...],
    allocation: dict[str, str],
) -> dict[str, str]:
    return {
        snapshot_id: allocation[component.component_id]
        for component in components
        if component.component_id in allocation
        for snapshot_id in component.match_snapshot_ids
    }


def _component_objective(
    groups: tuple[LearningDatasetMatchGroupV1, ...],
    components: tuple[LearningDatasetPlayerComponentV1, ...],
    allocation: dict[str, str],
    weights: LearningDatasetPartitionWeightsV1,
) -> tuple[int, ...]:
    return _objective_for_assignment(
        groups,
        _component_assignment_mapping(components, allocation),
        weights,
    )


def _initial_component_allocation(
    groups: tuple[LearningDatasetMatchGroupV1, ...],
    components: tuple[LearningDatasetPlayerComponentV1, ...],
    ordered_components: tuple[LearningDatasetPlayerComponentV1, ...],
    weights: LearningDatasetPartitionWeightsV1,
) -> dict[str, str]:
    allocation: dict[str, str] = {}
    for index, component in enumerate(ordered_components):
        eligible = (
            tuple(
                partition
                for partition in LEARNING_DATASET_PARTITIONS
                if partition not in allocation.values()
            )
            if index < 3
            else LEARNING_DATASET_PARTITIONS
        )
        candidates = []
        for partition in eligible:
            projected = {**allocation, component.component_id: partition}
            objective = _component_objective(
                groups,
                components,
                projected,
                weights,
            )
            candidates.append((objective, partition))
        best_objective = min(item[0] for item in candidates)
        tied = tuple(item for item in candidates if item[0] == best_objective)
        selected_partition = min(
            tied,
            key=lambda item: LEARNING_DATASET_PARTITIONS.index(item[1]),
        )[1]
        allocation[component.component_id] = selected_partition
    return allocation


def _operation_identity(
    kind: str,
    component_ids: tuple[str, ...],
    source_partitions: tuple[str, ...],
    target_partitions: tuple[str, ...],
) -> str:
    return json.dumps(
        {
            "algorithm": COMPONENT_BALANCED_UNSEEN_PLAYER_MATCH_GROUP_ALGORITHM,
            "phase": "local_improvement",
            "kind": kind,
            "component_ids": component_ids,
            "source_partitions": source_partitions,
            "target_partitions": target_partitions,
        },
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _strict_improvement_candidates(
    groups: tuple[LearningDatasetMatchGroupV1, ...],
    components: tuple[LearningDatasetPlayerComponentV1, ...],
    allocation: dict[str, str],
    weights: LearningDatasetPartitionWeightsV1,
) -> tuple[_AllocationOperation, ...]:
    current = _component_objective(groups, components, allocation, weights)
    candidates = []
    for component in components:
        source = allocation[component.component_id]
        for target in LEARNING_DATASET_PARTITIONS:
            if target == source:
                continue
            projected = {**allocation, component.component_id: target}
            mapping = _component_assignment_mapping(components, projected)
            record_counts, _match_counts = _counts_for_assignment(groups, mapping)
            if any(count == 0 for count in record_counts):
                continue
            objective = _component_objective(groups, components, projected, weights)
            if objective < current:
                candidates.append(
                    _AllocationOperation(
                        "move",
                        (component.component_id,),
                        (target,),
                        objective,
                        _operation_identity(
                            "move",
                            (component.component_id,),
                            (source,),
                            (target,),
                        ),
                    )
                )
    for first_index, first in enumerate(components):
        for second in components[first_index + 1 :]:
            first_partition = allocation[first.component_id]
            second_partition = allocation[second.component_id]
            if first_partition == second_partition:
                continue
            projected = {
                **allocation,
                first.component_id: second_partition,
                second.component_id: first_partition,
            }
            mapping = _component_assignment_mapping(components, projected)
            record_counts, _match_counts = _counts_for_assignment(groups, mapping)
            if any(count == 0 for count in record_counts):
                continue
            objective = _component_objective(groups, components, projected, weights)
            if objective < current:
                candidates.append(
                    _AllocationOperation(
                        "swap",
                        (first.component_id, second.component_id),
                        (second_partition, first_partition),
                        objective,
                        _operation_identity(
                            "swap",
                            (first.component_id, second.component_id),
                            (first_partition, second_partition),
                            (second_partition, first_partition),
                        ),
                    )
                )
    return tuple(candidates)


def _improve_component_allocation(
    groups: tuple[LearningDatasetMatchGroupV1, ...],
    components: tuple[LearningDatasetPlayerComponentV1, ...],
    allocation: dict[str, str],
    weights: LearningDatasetPartitionWeightsV1,
) -> dict[str, str]:
    result = dict(allocation)
    while True:
        candidates = _strict_improvement_candidates(groups, components, result, weights)
        if not candidates:
            return result
        best_objective = min(item.resulting_objective for item in candidates)
        tied = tuple(item for item in candidates if item.resulting_objective == best_objective)
        operation = (
            tied[0]
            if len(tied) == 1
            else min(
                tied,
                key=lambda item: item.stable_identity,
            )
        )
        for component_id, target in zip(
            operation.component_ids,
            operation.target_partitions,
            strict=True,
        ):
            result[component_id] = target


def _build_unseen_audit(
    groups: tuple[LearningDatasetMatchGroupV1, ...],
    components: tuple[LearningDatasetPlayerComponentV1, ...],
    allocation: dict[str, str],
    weights: LearningDatasetPartitionWeightsV1,
) -> LearningDatasetUnseenPlayerComponentAuditV1:
    components_by_partition = {
        partition: tuple(item for item in components if allocation[item.component_id] == partition)
        for partition in LEARNING_DATASET_PARTITIONS
    }
    players = {
        partition: {
            player_id
            for component in components_by_partition[partition]
            for player_id in component.player_ids
        }
        for partition in LEARNING_DATASET_PARTITIONS
    }
    candidates = _strict_improvement_candidates(groups, components, allocation, weights)
    mapping = _component_assignment_mapping(components, allocation)
    record_counts, _match_counts = _counts_for_assignment(groups, mapping)
    train_validation = players["train"] & players["validation"]
    train_test = players["train"] & players["test"]
    validation_test = players["validation"] & players["test"]
    return LearningDatasetUnseenPlayerComponentAuditV1(
        component_count=len(components),
        components=components,
        train_component_ids=tuple(
            sorted(item.component_id for item in components_by_partition["train"])
        ),
        validation_component_ids=tuple(
            sorted(item.component_id for item in components_by_partition["validation"])
        ),
        test_component_ids=tuple(
            sorted(item.component_id for item in components_by_partition["test"])
        ),
        train_player_ids=tuple(sorted(players["train"])),
        validation_player_ids=tuple(sorted(players["validation"])),
        test_player_ids=tuple(sorted(players["test"])),
        train_validation_overlap_player_ids=tuple(sorted(train_validation)),
        train_test_overlap_player_ids=tuple(sorted(train_test)),
        validation_test_overlap_player_ids=tuple(sorted(validation_test)),
        player_disjoint=not (train_validation or train_test or validation_test),
        components_indivisible=all(
            len({mapping[snapshot_id] for snapshot_id in item.match_snapshot_ids}) == 1
            for item in components
        ),
        all_partitions_have_records=all(count > 0 for count in record_counts),
        local_move_optimal=not any(item.kind == "move" for item in candidates),
        local_swap_optimal=not any(item.kind == "swap" for item in candidates),
    )


def generate_component_balanced_unseen_player_match_group_assignments_v1(
    groups: tuple[LearningDatasetMatchGroupV1, ...],
    *,
    weights: LearningDatasetPartitionWeightsV1,
    base_random_seed: int,
    source_identity_fingerprint: str,
) -> _PartitionAlgorithmResult:
    """Generates a deterministic locally optimized Player-disjoint split."""
    components = build_learning_dataset_player_components_v1(groups)
    if len(components) < 3:
        return _PartitionAlgorithmResult(
            "unavailable", "insufficient_player_components", (), None, None
        )
    if sum(item.record_count > 0 for item in components) < 3:
        return _PartitionAlgorithmResult(
            "unavailable", "component_distribution_infeasible", (), None, None
        )
    partition_seed = derive_learning_dataset_partition_seed_v1(
        "unseen_player",
        base_random_seed,
        source_identity_fingerprint,
    )
    ordered = _component_order(components, partition_seed)
    allocation = _initial_component_allocation(
        groups,
        components,
        ordered,
        weights,
    )
    allocation = _improve_component_allocation(
        groups,
        components,
        allocation,
        weights,
    )
    mapping = _component_assignment_mapping(components, allocation)
    assignments = tuple(
        LearningDatasetMatchPartitionAssignmentV1(
            match_snapshot_id=group.match_snapshot_id,
            partition=mapping[group.match_snapshot_id],
        )
        for group in groups
    )
    audit = _build_unseen_audit(groups, components, allocation, weights)
    if not all(
        (
            audit.player_disjoint,
            audit.components_indivisible,
            audit.all_partitions_have_records,
            audit.local_move_optimal,
            audit.local_swap_optimal,
        )
    ):
        raise RuntimeError("Unseen-player assignment did not satisfy its component audit.")
    return _PartitionAlgorithmResult("complete", None, assignments, None, audit)
