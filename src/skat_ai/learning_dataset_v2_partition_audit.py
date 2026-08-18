from __future__ import annotations

from collections import Counter

from skat_ai.learning_dataset_v2_partition_contracts import (
    LEARNING_DATASET_PARTITION_AUDIT_VERSION,
    LearningDatasetMatchGroupV1,
    LearningDatasetMatchPartitionAssignmentV1,
    LearningDatasetPartitionLeakageAuditV1,
    LearningDatasetPartitionPreparationRequestV1,
)
from skat_ai.learning_dataset_v2_partition_identity import (
    build_learning_dataset_partition_audit_fingerprint_v1,
)
from skat_ai.rfc3339 import parse_rfc3339_datetime


def _ordered_selected(
    source_ids: tuple[str, ...],
    selected: set[str],
) -> tuple[str, ...]:
    return tuple(item for item in source_ids if item in selected)


def _partitions_for_snapshot(
    assignments: tuple[LearningDatasetMatchPartitionAssignmentV1, ...],
) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for assignment in assignments:
        result.setdefault(assignment.match_snapshot_id, []).append(assignment.partition)
    return result


def audit_learning_dataset_v2_partitions_v1(
    request: LearningDatasetPartitionPreparationRequestV1,
    active_match_groups: tuple[LearningDatasetMatchGroupV1, ...],
    inactive_current_match_snapshot_ids: tuple[str, ...],
    assignments: tuple[LearningDatasetMatchPartitionAssignmentV1, ...],
    *,
    plan_fingerprint: str,
) -> LearningDatasetPartitionLeakageAuditV1:
    """Audits Match, evidence, and time-safe Statistics closure without mutation."""
    dataset = request.learning_dataset
    active_snapshot_ids = tuple(item.match_snapshot_id for item in active_match_groups)
    active_snapshot_set = set(active_snapshot_ids)
    current_snapshot_set = set(dataset.current_match_snapshot_ids)
    assignment_counts = Counter(item.match_snapshot_id for item in assignments)
    partitions_by_snapshot = _partitions_for_snapshot(assignments)
    assigned_active = {
        snapshot_id for snapshot_id in active_snapshot_ids if assignment_counts[snapshot_id] > 0
    }
    unassigned = active_snapshot_set - assigned_active
    unknown = set(assignment_counts) - active_snapshot_set
    duplicates = {snapshot_id for snapshot_id, count in assignment_counts.items() if count > 1}
    snapshot_overlaps = {
        snapshot_id
        for snapshot_id, partitions in partitions_by_snapshot.items()
        if len(set(partitions)) > 1
    }

    groups_by_snapshot = {item.match_snapshot_id: item for item in active_match_groups}
    match_id_partitions: dict[str, set[str]] = {}
    for snapshot_id, group in groups_by_snapshot.items():
        for partition in partitions_by_snapshot.get(snapshot_id, ()):
            match_id_partitions.setdefault(group.match_id, set()).add(partition)
    match_id_overlaps = {
        match_id for match_id, partitions in match_id_partitions.items() if len(partitions) > 1
    }

    record_ids = tuple(item.record_id for item in dataset.records)
    skipped_ids = tuple(item.skipped_decision_id for item in dataset.skipped_decisions)
    teacher_ids = tuple(
        item.strategy_teacher_evidence_id for item in dataset.strategy_teacher_evidences
    )
    commentary_ids = tuple(item.commentary_evidence_id for item in dataset.commentary_evidences)
    response_ids = tuple(item.response_evidence_id for item in dataset.response_evidences)

    record_partitions = {
        record.record_id: partitions_by_snapshot.get(
            record.source_context.match_snapshot_id,
            [],
        )
        for record in dataset.records
    }
    skipped_partitions = {
        skipped.skipped_decision_id: partitions_by_snapshot.get(
            skipped.match_snapshot_id,
            [],
        )
        for skipped in dataset.skipped_decisions
    }

    def overlap_ids(values: dict[str, list[str]]) -> set[str]:
        return {item_id for item_id, partitions in values.items() if len(set(partitions)) > 1}

    record_overlaps = overlap_ids(record_partitions)
    skipped_overlaps = overlap_ids(skipped_partitions)

    teacher_partitions: dict[str, list[str]] = {item_id: [] for item_id in teacher_ids}
    commentary_partitions: dict[str, list[str]] = {item_id: [] for item_id in commentary_ids}
    response_partitions: dict[str, list[str]] = {item_id: [] for item_id in response_ids}
    for record in dataset.records:
        partitions = record_partitions[record.record_id]
        for item_id in record.strategy_teacher_evidence_ids:
            teacher_partitions.setdefault(item_id, []).extend(partitions)
        for item_id in record.commentary_evidence_ids:
            commentary_partitions.setdefault(item_id, []).extend(partitions)
        for item_id in {
            *record.outgoing_response_evidence_ids,
            *record.incoming_response_evidence_ids,
        }:
            response_partitions.setdefault(item_id, []).extend(partitions)

    unjoined_commentary_partitions: dict[str, list[str]] = {
        item_id: [] for item_id in dataset.unjoined_commentary_evidence_ids
    }
    unjoined_response_partitions: dict[str, list[str]] = {
        item_id: [] for item_id in dataset.unjoined_response_evidence_ids
    }
    for skipped in dataset.skipped_decisions:
        partitions = skipped_partitions[skipped.skipped_decision_id]
        for item_id in skipped.commentary_evidence_ids:
            if item_id in unjoined_commentary_partitions:
                unjoined_commentary_partitions[item_id].extend(partitions)
        for item_id in {
            *skipped.outgoing_response_evidence_ids,
            *skipped.incoming_response_evidence_ids,
        }:
            if item_id in unjoined_response_partitions:
                unjoined_response_partitions[item_id].extend(partitions)

    teacher_overlaps = overlap_ids(teacher_partitions)
    commentary_overlaps = overlap_ids(commentary_partitions)
    response_overlaps = overlap_ids(response_partitions)
    unjoined_commentary_overlaps = overlap_ids(unjoined_commentary_partitions)
    unjoined_response_overlaps = overlap_ids(unjoined_response_partitions)

    observations_by_id = {
        item.statistics_observation_id: item for item in dataset.player_statistics_observations
    }
    observation_partitions: dict[str, set[str]] = {item_id: set() for item_id in observations_by_id}
    temporal_violation_record_ids: set[str] = set()
    for record in dataset.records:
        record_partition_set = set(record_partitions[record.record_id])
        for context in record.player_contexts:
            referenced = {
                *context.candidate_observation_ids,
                *context.equivalent_observation_ids,
                *context.ambiguous_observation_ids,
                *(
                    (context.selected_statistics_observation_id,)
                    if context.selected_statistics_observation_id is not None
                    else ()
                ),
            }
            if referenced and context.target_played_at is None:
                temporal_violation_record_ids.add(record.record_id)
                continue
            target = (
                None
                if context.target_played_at is None
                else parse_rfc3339_datetime(
                    context.target_played_at,
                    "Player Context target_played_at",
                )
            )
            for observation_id in referenced:
                observation = observations_by_id.get(observation_id)
                if observation is None or observation.player_id != context.player_id:
                    temporal_violation_record_ids.add(record.record_id)
                    continue
                observation_partitions[observation_id].update(record_partition_set)
                captured = parse_rfc3339_datetime(
                    observation.captured_at,
                    "Statistics Observation captured_at",
                )
                if target is None or not captured < target:
                    temporal_violation_record_ids.add(record.record_id)

    shared_statistics = {
        item_id for item_id, partitions in observation_partitions.items() if len(partitions) > 1
    }
    match_closure = not any(
        (
            unassigned,
            unknown,
            duplicates,
            snapshot_overlaps,
            match_id_overlaps,
            set(inactive_current_match_snapshot_ids) & set(assignment_counts),
            current_snapshot_set != active_snapshot_set | set(inactive_current_match_snapshot_ids),
        )
    )
    record_closure = (
        set(record_partitions) == set(record_ids)
        and all(len(values) == 1 for values in record_partitions.values())
        and not record_overlaps
    )
    skipped_closure = (
        set(skipped_partitions) == set(skipped_ids)
        and all(len(values) == 1 for values in skipped_partitions.values())
        and not skipped_overlaps
    )
    teacher_closure = (
        set(teacher_partitions) == set(teacher_ids)
        and all(len(set(values)) == 1 for values in teacher_partitions.values())
        and not teacher_overlaps
    )
    commentary_closure = (
        set(commentary_partitions) == set(commentary_ids)
        and all(len(set(values)) == 1 for values in commentary_partitions.values())
        and not commentary_overlaps
        and all(len(set(values)) == 1 for values in unjoined_commentary_partitions.values())
        and not unjoined_commentary_overlaps
    )
    response_closure = (
        set(response_partitions) == set(response_ids)
        and all(len(set(values)) == 1 for values in response_partitions.values())
        and not response_overlaps
        and all(len(set(values)) == 1 for values in unjoined_response_partitions.values())
        and not unjoined_response_overlaps
    )
    statistics_safe = not temporal_violation_record_ids
    compliant = all(
        (
            match_closure,
            record_closure,
            skipped_closure,
            teacher_closure,
            commentary_closure,
            response_closure,
            statistics_safe,
            request.mode != "unseen_player" or not shared_statistics,
        )
    )
    values = {
        "learning_dataset_partition_audit_version": (LEARNING_DATASET_PARTITION_AUDIT_VERSION),
        "audit_fingerprint": "0" * 64,
        "status": "compliant" if compliant else "non_compliant",
        "mode": request.mode,
        "source_dataset_fingerprint": dataset.dataset_fingerprint,
        "plan_fingerprint": plan_fingerprint,
        "inactive_current_match_snapshot_ids": inactive_current_match_snapshot_ids,
        "assigned_match_snapshot_count": len(assigned_active),
        "assigned_match_snapshot_ids": _ordered_selected(
            active_snapshot_ids,
            assigned_active,
        ),
        "unassigned_active_match_snapshot_ids": _ordered_selected(
            active_snapshot_ids,
            unassigned,
        ),
        "unknown_match_snapshot_assignment_ids": tuple(sorted(unknown)),
        "duplicate_match_snapshot_assignment_ids": tuple(sorted(duplicates)),
        "match_snapshot_partition_overlap_ids": tuple(sorted(snapshot_overlaps)),
        "match_id_partition_overlap_ids": tuple(sorted(match_id_overlaps)),
        "record_partition_overlap_ids": _ordered_selected(record_ids, record_overlaps),
        "skipped_decision_partition_overlap_ids": _ordered_selected(
            skipped_ids,
            skipped_overlaps,
        ),
        "strategy_teacher_partition_overlap_ids": _ordered_selected(
            teacher_ids,
            teacher_overlaps,
        ),
        "commentary_partition_overlap_ids": _ordered_selected(
            commentary_ids,
            commentary_overlaps,
        ),
        "response_partition_overlap_ids": _ordered_selected(
            response_ids,
            response_overlaps,
        ),
        "unjoined_commentary_partition_overlap_ids": _ordered_selected(
            dataset.unjoined_commentary_evidence_ids,
            unjoined_commentary_overlaps,
        ),
        "unjoined_response_partition_overlap_ids": _ordered_selected(
            dataset.unjoined_response_evidence_ids,
            unjoined_response_overlaps,
        ),
        "statistics_context_temporal_violation_record_ids": _ordered_selected(
            record_ids,
            temporal_violation_record_ids,
        ),
        "shared_statistics_observation_ids": tuple(
            item.statistics_observation_id
            for item in dataset.player_statistics_observations
            if item.statistics_observation_id in shared_statistics
        ),
        "match_group_closure_complete": match_closure,
        "record_closure_complete": record_closure,
        "skipped_decision_closure_complete": skipped_closure,
        "teacher_closure_complete": teacher_closure,
        "commentary_closure_complete": commentary_closure,
        "response_closure_complete": response_closure,
        "statistics_context_temporal_safety_complete": statistics_safe,
    }
    fingerprint = build_learning_dataset_partition_audit_fingerprint_v1(values)
    return LearningDatasetPartitionLeakageAuditV1(**{**values, "audit_fingerprint": fingerprint})
