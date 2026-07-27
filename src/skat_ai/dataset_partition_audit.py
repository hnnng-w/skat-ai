from dataclasses import dataclass
from typing import Any, Literal

from skat_ai.dataset_partition_policy import (
    CANONICAL_DATASET_PARTITIONS,
    DATASET_PARTITION_AUDIT_MODES,
    DatasetPartitionAuditMode,
    PlayerPartitionMembership,
    build_serializable_dataset_partition_policy,
    collect_player_partition_memberships,
)
from skat_ai.training_dataset import TrainingDatasetInput

DATASET_PARTITION_AUDIT_VERSION = 1

ComplianceStatus = Literal["compliant", "non_compliant", "not_evaluated"]


@dataclass(frozen=True)
class DatasetPartitionAudit:
    """One deterministic stable-player partition audit."""

    schema_version: int
    audit_version: int
    source_dataset: dict[str, Any]
    declared_partition_policy: dict[str, Any] | None
    effective_audit_mode: DatasetPartitionAuditMode
    compliance_status: ComplianceStatus
    partition_summary: dict[str, dict[str, Any]]
    player_summary: dict[str, int]
    overlap_summary: dict[str, dict[str, Any]]
    known_opponent_coverage: dict[str, dict[str, Any]]
    unseen_player_compliance: dict[str, Any]
    players: tuple[dict[str, Any], ...]


def resolve_dataset_partition_audit_mode(
    dataset: TrainingDatasetInput,
    requested_mode: str | None,
) -> DatasetPartitionAuditMode:
    """Resolves CLI audit mode without overriding a declared policy contract."""
    if requested_mode is not None and requested_mode not in DATASET_PARTITION_AUDIT_MODES:
        raise ValueError(
            f"Dataset partition audit mode must be one of {list(DATASET_PARTITION_AUDIT_MODES)}."
        )
    declared_mode = (
        dataset.partition_policy.mode if dataset.partition_policy is not None else None
    )
    if (
        requested_mode in ("known_opponent", "unseen_player")
        and declared_mode is not None
        and requested_mode != declared_mode
    ):
        raise ValueError(
            f"Requested dataset partition mode '{requested_mode}' contradicts declared "
            f"partition policy '{declared_mode}'."
        )
    if requested_mode is not None:
        return requested_mode
    if declared_mode is not None:
        return declared_mode
    return "report_only"


def _classification(membership: PlayerPartitionMembership) -> str:
    if len(membership.partitions) == 1:
        return "single_partition"
    if len(membership.partitions) == 2:
        return "pairwise_overlap"
    return "three_partition_overlap"


def _serialize_membership(membership: PlayerPartitionMembership) -> dict[str, Any]:
    return {
        "player_id": membership.player_id,
        "player_label": membership.player_label,
        "partitions": list(membership.partitions),
        "record_ids_by_partition": {
            partition: list(membership.record_ids_by_partition[partition])
            for partition in CANONICAL_DATASET_PARTITIONS
        },
        "historical_game_ids_by_partition": {
            partition: list(membership.game_ids_by_partition[partition])
            for partition in CANONICAL_DATASET_PARTITIONS
        },
        "game_count_by_partition": {
            partition: len(membership.game_ids_by_partition[partition])
            for partition in CANONICAL_DATASET_PARTITIONS
        },
        "first_appearance_index": membership.first_appearance_index,
        "classification": _classification(membership),
    }


def _build_partition_summary(
    dataset: TrainingDatasetInput,
    memberships: tuple[PlayerPartitionMembership, ...],
) -> dict[str, dict[str, Any]]:
    summary = {}
    for partition in CANONICAL_DATASET_PARTITIONS:
        records = [record for record in dataset.records if record.partition == partition]
        player_ids = [
            membership.player_id
            for membership in memberships
            if partition in membership.partitions
        ]
        summary[partition] = {
            "record_count": len(records),
            "game_count": len(records),
            "distinct_player_count": len(player_ids),
            "total_player_game_appearances": len(records) * 3,
            "player_ids": player_ids,
        }
    return summary


def _build_overlap_group(
    memberships: tuple[PlayerPartitionMembership, ...],
    required_partitions: tuple[str, ...],
) -> dict[str, Any]:
    selected = [
        membership
        for membership in memberships
        if all(partition in membership.partitions for partition in required_partitions)
    ]
    return {
        "player_count": len(selected),
        "player_ids": [membership.player_id for membership in selected],
        "player_memberships": [
            {
                "player_id": membership.player_id,
                "partitions": list(membership.partitions),
            }
            for membership in selected
        ],
    }


def _build_overlap_summary(
    memberships: tuple[PlayerPartitionMembership, ...],
) -> dict[str, dict[str, Any]]:
    return {
        "train_validation": _build_overlap_group(
            memberships, ("train", "validation")
        ),
        "train_test": _build_overlap_group(memberships, ("train", "test")),
        "validation_test": _build_overlap_group(
            memberships, ("validation", "test")
        ),
        "train_validation_test": _build_overlap_group(
            memberships, ("train", "validation", "test")
        ),
    }


def _build_coverage_relationship(
    dataset: TrainingDatasetInput,
    memberships: tuple[PlayerPartitionMembership, ...],
    source_partition: str,
    target_partition: str,
) -> dict[str, Any]:
    source_player_ids = [
        membership.player_id
        for membership in memberships
        if source_partition in membership.partitions
    ]
    target_player_ids = [
        membership.player_id
        for membership in memberships
        if target_partition in membership.partitions
    ]
    source_player_lookup = set(source_player_ids)
    shared_player_ids = [
        player_id for player_id in target_player_ids if player_id in source_player_lookup
    ]
    target_records = [
        record for record in dataset.records if record.partition == target_partition
    ]
    target_appearances_with_history = sum(
        player.player_id in source_player_lookup
        for record in target_records
        for player in record.historical_game.players
    )
    total_target_appearances = len(target_records) * 3
    return {
        "source_partition": source_partition,
        "target_partition": target_partition,
        "source_distinct_player_count": len(source_player_ids),
        "target_distinct_player_count": len(target_player_ids),
        "shared_player_count": len(shared_player_ids),
        "shared_player_ids": shared_player_ids,
        "target_player_count_with_source_history": len(shared_player_ids),
        "target_player_count_without_source_history": (
            len(target_player_ids) - len(shared_player_ids)
        ),
        "target_game_count_with_at_least_one_previously_seen_participant": sum(
            any(
                player.player_id in source_player_lookup
                for player in record.historical_game.players
            )
            for record in target_records
        ),
        "target_game_count_with_all_three_participants_previously_seen": sum(
            all(
                player.player_id in source_player_lookup
                for player in record.historical_game.players
            )
            for record in target_records
        ),
        "target_player_game_appearances_with_source_history": (
            target_appearances_with_history
        ),
        "target_player_game_appearances_without_source_history": (
            total_target_appearances - target_appearances_with_history
        ),
        "eligibility_basis": "partition_membership_only_not_temporal_eligibility",
    }


def _build_unseen_player_compliance(
    memberships: tuple[PlayerPartitionMembership, ...],
    overlap_summary: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    violations = [
        membership for membership in memberships if len(membership.partitions) > 1
    ]
    return {
        "player_disjoint": not violations,
        "violating_player_count": len(violations),
        "violating_player_ids": [membership.player_id for membership in violations],
        "violations": [
            {
                "player_id": membership.player_id,
                "partitions": list(membership.partitions),
            }
            for membership in violations
        ],
        "pairwise_violation_counts": {
            name: overlap_summary[name]["player_count"]
            for name in ("train_validation", "train_test", "validation_test")
        },
        "three_way_violation_count": overlap_summary["train_validation_test"][
            "player_count"
        ],
    }


def audit_training_dataset_partitions(
    dataset: TrainingDatasetInput,
    mode: DatasetPartitionAuditMode,
) -> DatasetPartitionAudit:
    """Audits exact stable-player overlap without replaying or sampling games."""
    if mode not in DATASET_PARTITION_AUDIT_MODES:
        raise ValueError(
            f"Dataset partition audit mode must be one of {list(DATASET_PARTITION_AUDIT_MODES)}."
        )
    memberships = collect_player_partition_memberships(dataset.records)
    partition_summary = _build_partition_summary(dataset, memberships)
    overlap_summary = _build_overlap_summary(memberships)
    unseen_compliance = _build_unseen_player_compliance(
        memberships, overlap_summary
    )
    if mode == "report_only":
        compliance_status: ComplianceStatus = "not_evaluated"
    elif mode == "known_opponent":
        compliance_status = "compliant"
    else:
        compliance_status = (
            "compliant" if unseen_compliance["player_disjoint"] else "non_compliant"
        )
    classifications = [_classification(membership) for membership in memberships]
    return DatasetPartitionAudit(
        schema_version=1,
        audit_version=DATASET_PARTITION_AUDIT_VERSION,
        source_dataset={
            "dataset_id": dataset.dataset_id,
            "dataset_version": dataset.dataset_version,
            "training_dataset_schema_version": dataset.schema_version,
            "feature_generation_version": dataset.feature_generation_version,
            "target": dataset.target,
            "total_record_count": len(dataset.records),
            "total_historical_game_count": len(dataset.records),
        },
        declared_partition_policy=(
            build_serializable_dataset_partition_policy(dataset.partition_policy)
            if dataset.partition_policy is not None
            else None
        ),
        effective_audit_mode=mode,
        compliance_status=compliance_status,
        partition_summary=partition_summary,
        player_summary={
            "total_distinct_player_count": len(memberships),
            "single_partition_player_count": classifications.count(
                "single_partition"
            ),
            "pairwise_overlap_player_count": classifications.count(
                "pairwise_overlap"
            ),
            "three_partition_overlap_player_count": classifications.count(
                "three_partition_overlap"
            ),
            "train_player_count": partition_summary["train"][
                "distinct_player_count"
            ],
            "validation_player_count": partition_summary["validation"][
                "distinct_player_count"
            ],
            "test_player_count": partition_summary["test"]["distinct_player_count"],
        },
        overlap_summary=overlap_summary,
        known_opponent_coverage={
            "train_to_validation": _build_coverage_relationship(
                dataset, memberships, "train", "validation"
            ),
            "train_to_test": _build_coverage_relationship(
                dataset, memberships, "train", "test"
            ),
            "validation_to_test": _build_coverage_relationship(
                dataset, memberships, "validation", "test"
            ),
        },
        unseen_player_compliance=unseen_compliance,
        players=tuple(_serialize_membership(membership) for membership in memberships),
    )


def build_serializable_dataset_partition_audit(
    audit: DatasetPartitionAudit,
) -> dict[str, Any]:
    """Builds the stable public representation of a partition audit."""
    return {
        "schema_version": audit.schema_version,
        "audit_version": audit.audit_version,
        "source_dataset": audit.source_dataset,
        "declared_partition_policy": audit.declared_partition_policy,
        "effective_audit_mode": audit.effective_audit_mode,
        "compliance_status": audit.compliance_status,
        "partition_summary": audit.partition_summary,
        "player_summary": audit.player_summary,
        "overlap_summary": audit.overlap_summary,
        "known_opponent_coverage": audit.known_opponent_coverage,
        "unseen_player_compliance": audit.unseen_player_compliance,
        "players": list(audit.players),
    }
