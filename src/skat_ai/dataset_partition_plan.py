import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any, Literal

from skat_ai.dataset_partition_audit import (
    DatasetPartitionAudit,
    audit_training_dataset_partitions,
    build_serializable_dataset_partition_audit,
)
from skat_ai.dataset_partition_policy import CANONICAL_DATASET_PARTITIONS
from skat_ai.dataset_preparation_identity import (
    build_source_content_fingerprint,
    build_source_identity_fingerprint,
)
from skat_ai.rfc3339 import parse_rfc3339_datetime
from skat_ai.training_dataset import TrainingPartition
from skat_ai.training_dataset_preparation import (
    DatasetPartitionWeights,
    DatasetPreparationSourceFact,
    TrainingDatasetPreparationRequest,
    _build_materialized_training_dataset,
    build_dataset_preparation_source_facts,
    build_serializable_dataset_partition_weights,
)

DATASET_PARTITION_PLAN_VERSION = 1
DATASET_PARTITION_BALANCE_BASIS = "record_count"

TEMPORAL_KNOWN_OPPONENT_ALGORITHM = "temporal_known_opponent_v1"
COMPONENT_BALANCED_UNSEEN_PLAYER_ALGORITHM = (
    "component_balanced_unseen_player_v1"
)
DATASET_PARTITION_PLAN_ALGORITHMS = (
    TEMPORAL_KNOWN_OPPONENT_ALGORITHM,
    COMPONENT_BALANCED_UNSEEN_PLAYER_ALGORITHM,
)

DATASET_PARTITION_PLAN_STATUSES = ("complete", "unavailable")
DATASET_PARTITION_UNAVAILABLE_REASONS = (
    "missing_played_at",
    "insufficient_time_groups",
    "known_opponent_train_coverage_unsatisfied",
    "insufficient_player_components",
    "component_distribution_infeasible",
    "non_empty_partition_requirement_unsatisfied",
)

DatasetPartitionPlanStatus = Literal["complete", "unavailable"]
DatasetPartitionUnavailableReason = Literal[
    "missing_played_at",
    "insufficient_time_groups",
    "known_opponent_train_coverage_unsatisfied",
    "insufficient_player_components",
    "component_distribution_infeasible",
    "non_empty_partition_requirement_unsatisfied",
]

_ALGORITHM_MODES = {
    TEMPORAL_KNOWN_OPPONENT_ALGORITHM: "known_opponent",
    COMPONENT_BALANCED_UNSEEN_PLAYER_ALGORITHM: "unseen_player",
}
_UNAVAILABLE_REASON_MODES = {
    "missing_played_at": ("known_opponent",),
    "insufficient_time_groups": ("known_opponent",),
    "known_opponent_train_coverage_unsatisfied": ("known_opponent",),
    "insufficient_player_components": ("unseen_player",),
    "component_distribution_infeasible": ("unseen_player",),
    "non_empty_partition_requirement_unsatisfied": (
        "known_opponent",
        "unseen_player",
    ),
}


@dataclass(frozen=True)
class DatasetPartitionAssignment:
    """One whole-Record partition assignment."""

    record_id: str
    partition: TrainingPartition

    def __post_init__(self) -> None:
        if (
            not isinstance(self.record_id, str)
            or not self.record_id
            or self.record_id != self.record_id.strip()
        ):
            raise ValueError("record_id must be a non-empty, non-padded string.")
        if self.partition not in CANONICAL_DATASET_PARTITIONS:
            raise ValueError(
                "partition must be one of "
                f"{list(CANONICAL_DATASET_PARTITIONS)}."
            )


@dataclass(frozen=True)
class DatasetPartitionSummary:
    """Exact Record-count target arithmetic and diagnostic sample totals."""

    partition: TrainingPartition
    requested_weight: int
    record_count: int
    sample_count: int
    distinct_player_count: int
    player_ids: tuple[str, ...]
    target_record_count_numerator: int
    target_record_count_denominator: int
    record_count_deviation_numerator: int


@dataclass(frozen=True)
class DatasetTemporalPartitionBoundary:
    """Canonical UTC boundaries and time-group count for one partition."""

    partition: TrainingPartition
    minimum_played_at: str
    maximum_played_at: str
    time_group_count: int


@dataclass(frozen=True)
class KnownOpponentTemporalAudit:
    """Strict temporal blocks and Train player coverage for one complete plan."""

    partition_boundaries: tuple[DatasetTemporalPartitionBoundary, ...]
    train_player_ids: tuple[str, ...]
    validation_player_ids: tuple[str, ...]
    test_player_ids: tuple[str, ...]
    validation_covered_player_ids: tuple[str, ...]
    validation_uncovered_player_ids: tuple[str, ...]
    test_covered_player_ids: tuple[str, ...]
    test_uncovered_player_ids: tuple[str, ...]
    all_played_at_present: bool
    time_group_count: int
    strict_partition_order: bool
    equal_timestamp_groups_preserved: bool
    validation_train_coverage_complete: bool
    test_train_coverage_complete: bool


@dataclass(frozen=True)
class DatasetPartitionPlan:
    """One complete or explicitly unavailable deterministic split plan."""

    plan_version: int
    algorithm: str
    mode: str
    status: DatasetPartitionPlanStatus
    unavailable_reason: DatasetPartitionUnavailableReason | None
    source_identity_fingerprint: str
    source_content_fingerprint: str
    base_random_seed: int
    balance_basis: str
    requested_partition_weights: DatasetPartitionWeights
    source_record_count: int
    source_sample_count: int
    assignments: tuple[DatasetPartitionAssignment, ...]
    partition_summaries: tuple[DatasetPartitionSummary, ...]
    temporal_audit: KnownOpponentTemporalAudit | None
    partition_audit: DatasetPartitionAudit | None
    plan_fingerprint: str


@dataclass(frozen=True)
class CompleteDatasetPartitionPlan(DatasetPartitionPlan):
    """A fully assigned and validated partition plan."""


@dataclass(frozen=True)
class UnavailableDatasetPartitionPlan(DatasetPartitionPlan):
    """A deterministic declaration that no complete plan was supplied."""


def _validate_algorithm_mode(
    request: TrainingDatasetPreparationRequest,
    algorithm: str,
) -> None:
    if algorithm not in DATASET_PARTITION_PLAN_ALGORITHMS:
        raise ValueError(
            "algorithm must be one of "
            f"{list(DATASET_PARTITION_PLAN_ALGORITHMS)}."
        )
    expected_mode = _ALGORITHM_MODES[algorithm]
    if request.mode != expected_mode:
        raise ValueError(
            f"Algorithm '{algorithm}' requires mode '{expected_mode}', got "
            f"'{request.mode}'."
        )


def _normalize_assignments(
    request: TrainingDatasetPreparationRequest,
    assignments: tuple[DatasetPartitionAssignment, ...],
) -> tuple[DatasetPartitionAssignment, ...]:
    if not isinstance(assignments, tuple):
        raise ValueError("assignments must be an immutable tuple.")
    if any(
        not isinstance(assignment, DatasetPartitionAssignment)
        for assignment in assignments
    ):
        raise ValueError(
            "assignments must contain only DatasetPartitionAssignment values."
        )
    assignments_by_record_id: dict[str, DatasetPartitionAssignment] = {}
    for assignment in assignments:
        if assignment.record_id in assignments_by_record_id:
            raise ValueError(
                f"Duplicate assignment for record_id '{assignment.record_id}' is not allowed."
            )
        assignments_by_record_id[assignment.record_id] = assignment

    source_record_ids = {record.record_id for record in request.records}
    missing_record_ids = sorted(source_record_ids - assignments_by_record_id.keys())
    unknown_record_ids = sorted(assignments_by_record_id.keys() - source_record_ids)
    if missing_record_ids or unknown_record_ids:
        raise ValueError(
            "Complete assignments must cover every source Record exactly once. "
            f"Missing record IDs: {missing_record_ids}. Unknown record IDs: "
            f"{unknown_record_ids}."
        )
    return tuple(
        assignments_by_record_id[record.record_id]
        for record in request.records
    )


def _assignment_lookup(
    assignments: tuple[DatasetPartitionAssignment, ...],
) -> dict[str, str]:
    return {
        assignment.record_id: assignment.partition
        for assignment in assignments
    }


def _require_non_empty_partitions(
    assignments: tuple[DatasetPartitionAssignment, ...],
) -> None:
    assigned_partitions = {assignment.partition for assignment in assignments}
    empty_partitions = [
        partition
        for partition in CANONICAL_DATASET_PARTITIONS
        if partition not in assigned_partitions
    ]
    if empty_partitions:
        raise ValueError(
            "A complete partition plan requires all three partitions to be "
            f"non-empty. Empty partitions: {empty_partitions}."
        )


def _canonical_instant(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _freeze_json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {key: _freeze_json_value(item) for key, item in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json_value(item) for item in value)
    return value


def _freeze_partition_audit(
    audit: DatasetPartitionAudit,
) -> DatasetPartitionAudit:
    return DatasetPartitionAudit(
        schema_version=audit.schema_version,
        audit_version=audit.audit_version,
        source_dataset=_freeze_json_value(audit.source_dataset),
        declared_partition_policy=(
            _freeze_json_value(audit.declared_partition_policy)
            if audit.declared_partition_policy is not None
            else None
        ),
        effective_audit_mode=audit.effective_audit_mode,
        compliance_status=audit.compliance_status,
        partition_summary=_freeze_json_value(audit.partition_summary),
        player_summary=_freeze_json_value(audit.player_summary),
        overlap_summary=_freeze_json_value(audit.overlap_summary),
        known_opponent_coverage=_freeze_json_value(
            audit.known_opponent_coverage
        ),
        unseen_player_compliance=_freeze_json_value(
            audit.unseen_player_compliance
        ),
        players=tuple(_freeze_json_value(player) for player in audit.players),
    )


def _build_known_opponent_temporal_audit(
    facts: tuple[DatasetPreparationSourceFact, ...],
    assignments: tuple[DatasetPartitionAssignment, ...],
) -> KnownOpponentTemporalAudit:
    assignments_by_record_id = _assignment_lookup(assignments)
    partition_instants: dict[str, list[datetime]] = {
        partition: [] for partition in CANONICAL_DATASET_PARTITIONS
    }
    partition_player_ids: dict[str, set[str]] = {
        partition: set() for partition in CANONICAL_DATASET_PARTITIONS
    }
    instant_partitions: dict[datetime, set[str]] = {}
    for fact in facts:
        if fact.played_at is None:
            raise ValueError(
                "A complete known_opponent plan requires historical_game.played_at "
                f"for record_id '{fact.record_id}'."
            )
        instant = parse_rfc3339_datetime(
            fact.played_at,
            f"record_id '{fact.record_id}' historical_game.played_at",
        )
        partition = assignments_by_record_id[fact.record_id]
        partition_instants[partition].append(instant)
        partition_player_ids[partition].update(fact.player_ids)
        instant_partitions.setdefault(instant, set()).add(partition)

    split_instants = [
        instant
        for instant, partitions in instant_partitions.items()
        if len(partitions) > 1
    ]
    if split_instants:
        raise ValueError(
            "Equal historical_game.played_at time groups must not be split across "
            "partitions."
        )
    if not max(partition_instants["train"]) < min(
        partition_instants["validation"]
    ):
        raise ValueError(
            "A complete known_opponent plan requires max(train) < min(validation)."
        )
    if not max(partition_instants["validation"]) < min(
        partition_instants["test"]
    ):
        raise ValueError(
            "A complete known_opponent plan requires max(validation) < min(test)."
        )

    train_players = partition_player_ids["train"]
    validation_players = partition_player_ids["validation"]
    test_players = partition_player_ids["test"]
    validation_uncovered = validation_players - train_players
    test_uncovered = test_players - train_players
    if validation_uncovered or test_uncovered:
        raise ValueError(
            "A complete known_opponent plan requires every Validation and Test "
            "player in Train. Uncovered Validation player IDs: "
            f"{sorted(validation_uncovered)}. Uncovered Test player IDs: "
            f"{sorted(test_uncovered)}."
        )

    boundaries = tuple(
        DatasetTemporalPartitionBoundary(
            partition=partition,
            minimum_played_at=_canonical_instant(
                min(partition_instants[partition])
            ),
            maximum_played_at=_canonical_instant(
                max(partition_instants[partition])
            ),
            time_group_count=len(set(partition_instants[partition])),
        )
        for partition in CANONICAL_DATASET_PARTITIONS
    )
    return KnownOpponentTemporalAudit(
        partition_boundaries=boundaries,
        train_player_ids=tuple(sorted(train_players)),
        validation_player_ids=tuple(sorted(validation_players)),
        test_player_ids=tuple(sorted(test_players)),
        validation_covered_player_ids=tuple(sorted(validation_players & train_players)),
        validation_uncovered_player_ids=tuple(sorted(validation_uncovered)),
        test_covered_player_ids=tuple(sorted(test_players & train_players)),
        test_uncovered_player_ids=tuple(sorted(test_uncovered)),
        all_played_at_present=True,
        time_group_count=len(instant_partitions),
        strict_partition_order=True,
        equal_timestamp_groups_preserved=True,
        validation_train_coverage_complete=not validation_uncovered,
        test_train_coverage_complete=not test_uncovered,
    )


def _build_partition_summaries(
    request: TrainingDatasetPreparationRequest,
    facts: tuple[DatasetPreparationSourceFact, ...],
    assignments: tuple[DatasetPartitionAssignment, ...],
) -> tuple[DatasetPartitionSummary, ...]:
    assignments_by_record_id = _assignment_lookup(assignments)
    weight_by_partition = {
        "train": request.partition_weights.train,
        "validation": request.partition_weights.validation,
        "test": request.partition_weights.test,
    }
    total_weight = request.partition_weights.total_weight
    summaries = []
    for partition in CANONICAL_DATASET_PARTITIONS:
        selected = [
            fact
            for fact in facts
            if assignments_by_record_id[fact.record_id] == partition
        ]
        player_ids = sorted(
            {
                player_id
                for fact in selected
                for player_id in fact.player_ids
            }
        )
        record_count = len(selected)
        target_numerator = len(facts) * weight_by_partition[partition]
        summaries.append(
            DatasetPartitionSummary(
                partition=partition,
                requested_weight=weight_by_partition[partition],
                record_count=record_count,
                sample_count=sum(fact.sample_count for fact in selected),
                distinct_player_count=len(player_ids),
                player_ids=tuple(player_ids),
                target_record_count_numerator=target_numerator,
                target_record_count_denominator=total_weight,
                record_count_deviation_numerator=(
                    record_count * total_weight - target_numerator
                ),
            )
        )
    return tuple(summaries)


def _fingerprint_plan_values(
    *,
    plan_version: int,
    algorithm: str,
    mode: str,
    status: str,
    unavailable_reason: str | None,
    source_content_fingerprint: str,
    base_random_seed: int,
    weights: DatasetPartitionWeights,
    assignments: tuple[DatasetPartitionAssignment, ...],
) -> str:
    canonical_assignments = sorted(
        (
            {
                "record_id": assignment.record_id,
                "partition": assignment.partition,
            }
            for assignment in assignments
        ),
        key=lambda assignment: assignment["record_id"],
    )
    material = {
        "plan_version": plan_version,
        "algorithm": algorithm,
        "mode": mode,
        "status": status,
        "unavailable_reason": unavailable_reason,
        "source_content_fingerprint": source_content_fingerprint,
        "base_random_seed": base_random_seed,
        "requested_partition_weights": build_serializable_dataset_partition_weights(
            weights
        ),
        "assignments": canonical_assignments,
    }
    canonical_bytes = json.dumps(
        material,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical_bytes).hexdigest()


def build_dataset_partition_plan_fingerprint(
    plan: DatasetPartitionPlan,
) -> str:
    """Rebuilds the canonical order-independent SHA-256 plan fingerprint."""
    return _fingerprint_plan_values(
        plan_version=plan.plan_version,
        algorithm=plan.algorithm,
        mode=plan.mode,
        status=plan.status,
        unavailable_reason=plan.unavailable_reason,
        source_content_fingerprint=plan.source_content_fingerprint,
        base_random_seed=plan.base_random_seed,
        weights=plan.requested_partition_weights,
        assignments=plan.assignments,
    )


def _build_complete_plan(
    request: TrainingDatasetPreparationRequest,
    *,
    algorithm: str,
    assignments: tuple[DatasetPartitionAssignment, ...],
    source_facts: tuple[DatasetPreparationSourceFact, ...] | None = None,
    source_order_independent_audit: bool = False,
) -> CompleteDatasetPartitionPlan:
    _validate_algorithm_mode(request, algorithm)
    normalized_assignments = _normalize_assignments(request, assignments)
    _require_non_empty_partitions(normalized_assignments)
    facts = (
        source_facts
        if source_facts is not None
        else build_dataset_preparation_source_facts(request)
    )
    assignments_by_record_id = _assignment_lookup(normalized_assignments)
    dataset = _build_materialized_training_dataset(
        request,
        assignments_by_record_id,
    )
    partition_audit = (
        audit_training_dataset_partitions(
            dataset,
            request.mode,
            canonical_source_order=True,
        )
        if source_order_independent_audit
        else audit_training_dataset_partitions(dataset, request.mode)
    )
    if partition_audit.compliance_status != "compliant":
        raise ValueError(
            "A complete partition plan must pass the existing partition audit."
        )
    temporal_audit = (
        _build_known_opponent_temporal_audit(facts, normalized_assignments)
        if request.mode == "known_opponent"
        else None
    )
    source_content_fingerprint = build_source_content_fingerprint(request)
    plan_fingerprint = _fingerprint_plan_values(
        plan_version=DATASET_PARTITION_PLAN_VERSION,
        algorithm=algorithm,
        mode=request.mode,
        status="complete",
        unavailable_reason=None,
        source_content_fingerprint=source_content_fingerprint,
        base_random_seed=request.base_random_seed,
        weights=request.partition_weights,
        assignments=normalized_assignments,
    )
    return CompleteDatasetPartitionPlan(
        plan_version=DATASET_PARTITION_PLAN_VERSION,
        algorithm=algorithm,
        mode=request.mode,
        status="complete",
        unavailable_reason=None,
        source_identity_fingerprint=build_source_identity_fingerprint(request),
        source_content_fingerprint=source_content_fingerprint,
        base_random_seed=request.base_random_seed,
        balance_basis=DATASET_PARTITION_BALANCE_BASIS,
        requested_partition_weights=request.partition_weights,
        source_record_count=len(facts),
        source_sample_count=sum(fact.sample_count for fact in facts),
        assignments=normalized_assignments,
        partition_summaries=_build_partition_summaries(
            request, facts, normalized_assignments
        ),
        temporal_audit=temporal_audit,
        partition_audit=_freeze_partition_audit(partition_audit),
        plan_fingerprint=plan_fingerprint,
    )


def build_complete_dataset_partition_plan(
    request: TrainingDatasetPreparationRequest,
    *,
    algorithm: str,
    assignments: tuple[DatasetPartitionAssignment, ...],
) -> CompleteDatasetPartitionPlan:
    """Validates supplied assignments without choosing any assignment."""
    return _build_complete_plan(
        request,
        algorithm=algorithm,
        assignments=assignments,
    )


def _build_complete_dataset_partition_plan_from_source_facts(
    request: TrainingDatasetPreparationRequest,
    *,
    algorithm: str,
    assignments: tuple[DatasetPartitionAssignment, ...],
    source_facts: tuple[DatasetPreparationSourceFact, ...],
) -> CompleteDatasetPartitionPlan:
    """Builds one complete plan without replaying already-derived source facts."""
    return _build_complete_plan(
        request,
        algorithm=algorithm,
        assignments=assignments,
        source_facts=source_facts,
        source_order_independent_audit=True,
    )


def _build_unavailable_plan(
    request: TrainingDatasetPreparationRequest,
    *,
    algorithm: str,
    unavailable_reason: str,
    source_facts: tuple[DatasetPreparationSourceFact, ...] | None = None,
) -> UnavailableDatasetPartitionPlan:
    _validate_algorithm_mode(request, algorithm)
    if unavailable_reason not in DATASET_PARTITION_UNAVAILABLE_REASONS:
        raise ValueError(
            "unavailable_reason must be one of "
            f"{list(DATASET_PARTITION_UNAVAILABLE_REASONS)}."
        )
    if request.mode not in _UNAVAILABLE_REASON_MODES[unavailable_reason]:
        raise ValueError(
            f"Unavailable reason '{unavailable_reason}' is not valid for mode "
            f"'{request.mode}'."
        )
    facts = (
        source_facts
        if source_facts is not None
        else build_dataset_preparation_source_facts(request)
    )
    source_content_fingerprint = build_source_content_fingerprint(request)
    empty_assignments: tuple[DatasetPartitionAssignment, ...] = ()
    return UnavailableDatasetPartitionPlan(
        plan_version=DATASET_PARTITION_PLAN_VERSION,
        algorithm=algorithm,
        mode=request.mode,
        status="unavailable",
        unavailable_reason=unavailable_reason,
        source_identity_fingerprint=build_source_identity_fingerprint(request),
        source_content_fingerprint=source_content_fingerprint,
        base_random_seed=request.base_random_seed,
        balance_basis=DATASET_PARTITION_BALANCE_BASIS,
        requested_partition_weights=request.partition_weights,
        source_record_count=len(facts),
        source_sample_count=sum(fact.sample_count for fact in facts),
        assignments=empty_assignments,
        partition_summaries=(),
        temporal_audit=None,
        partition_audit=None,
        plan_fingerprint=_fingerprint_plan_values(
            plan_version=DATASET_PARTITION_PLAN_VERSION,
            algorithm=algorithm,
            mode=request.mode,
            status="unavailable",
            unavailable_reason=unavailable_reason,
            source_content_fingerprint=source_content_fingerprint,
            base_random_seed=request.base_random_seed,
            weights=request.partition_weights,
            assignments=empty_assignments,
        ),
    )


def build_unavailable_dataset_partition_plan(
    request: TrainingDatasetPreparationRequest,
    *,
    algorithm: str,
    unavailable_reason: str,
) -> UnavailableDatasetPartitionPlan:
    """Builds one reasoned all-or-nothing unavailable plan."""
    return _build_unavailable_plan(
        request,
        algorithm=algorithm,
        unavailable_reason=unavailable_reason,
    )


def _build_unavailable_dataset_partition_plan_from_source_facts(
    request: TrainingDatasetPreparationRequest,
    *,
    algorithm: str,
    unavailable_reason: str,
    source_facts: tuple[DatasetPreparationSourceFact, ...],
) -> UnavailableDatasetPartitionPlan:
    """Builds one unavailable plan without replaying already-derived source facts."""
    return _build_unavailable_plan(
        request,
        algorithm=algorithm,
        unavailable_reason=unavailable_reason,
        source_facts=source_facts,
    )


def validate_dataset_partition_plan(
    request: TrainingDatasetPreparationRequest,
    plan: DatasetPartitionPlan,
) -> None:
    """Strictly reconciles every supplied plan field with its source request."""
    if not isinstance(plan, DatasetPartitionPlan):
        raise ValueError("plan must be a DatasetPartitionPlan value.")
    if plan.status == "complete":
        if not isinstance(plan, CompleteDatasetPartitionPlan):
            raise ValueError("A complete plan must use CompleteDatasetPartitionPlan.")
        expected = _build_complete_plan(
            request,
            algorithm=plan.algorithm,
            assignments=plan.assignments,
        )
        if plan != expected and plan.algorithm == TEMPORAL_KNOWN_OPPONENT_ALGORITHM:
            expected = _build_complete_plan(
                request,
                algorithm=plan.algorithm,
                assignments=plan.assignments,
                source_order_independent_audit=True,
            )
    elif plan.status == "unavailable":
        if not isinstance(plan, UnavailableDatasetPartitionPlan):
            raise ValueError(
                "An unavailable plan must use UnavailableDatasetPartitionPlan."
            )
        if plan.unavailable_reason is None:
            raise ValueError("An unavailable plan requires unavailable_reason.")
        expected = _build_unavailable_plan(
            request,
            algorithm=plan.algorithm,
            unavailable_reason=plan.unavailable_reason,
        )
    else:
        raise ValueError(
            f"plan.status must be one of {list(DATASET_PARTITION_PLAN_STATUSES)}."
        )
    if plan != expected:
        raise ValueError(
            "Dataset partition plan fields do not match the request, assignments, "
            "audits, exact arithmetic, or plan fingerprint."
        )


def build_serializable_dataset_partition_assignment(
    assignment: DatasetPartitionAssignment,
) -> dict[str, str]:
    return {
        "record_id": assignment.record_id,
        "partition": assignment.partition,
    }


def build_serializable_dataset_partition_summary(
    summary: DatasetPartitionSummary,
) -> dict[str, Any]:
    return {
        "partition": summary.partition,
        "requested_weight": summary.requested_weight,
        "record_count": summary.record_count,
        "sample_count": summary.sample_count,
        "distinct_player_count": summary.distinct_player_count,
        "player_ids": list(summary.player_ids),
        "target_record_count_numerator": summary.target_record_count_numerator,
        "target_record_count_denominator": summary.target_record_count_denominator,
        "record_count_deviation_numerator": summary.record_count_deviation_numerator,
    }


def build_serializable_known_opponent_temporal_audit(
    audit: KnownOpponentTemporalAudit,
) -> dict[str, Any]:
    return {
        "partition_boundaries": [
            {
                "partition": boundary.partition,
                "minimum_played_at": boundary.minimum_played_at,
                "maximum_played_at": boundary.maximum_played_at,
                "time_group_count": boundary.time_group_count,
            }
            for boundary in audit.partition_boundaries
        ],
        "train_player_ids": list(audit.train_player_ids),
        "validation_player_ids": list(audit.validation_player_ids),
        "test_player_ids": list(audit.test_player_ids),
        "validation_covered_player_ids": list(
            audit.validation_covered_player_ids
        ),
        "validation_uncovered_player_ids": list(
            audit.validation_uncovered_player_ids
        ),
        "test_covered_player_ids": list(audit.test_covered_player_ids),
        "test_uncovered_player_ids": list(audit.test_uncovered_player_ids),
        "all_played_at_present": audit.all_played_at_present,
        "time_group_count": audit.time_group_count,
        "strict_partition_order": audit.strict_partition_order,
        "equal_timestamp_groups_preserved": (
            audit.equal_timestamp_groups_preserved
        ),
        "validation_train_coverage_complete": (
            audit.validation_train_coverage_complete
        ),
        "test_train_coverage_complete": audit.test_train_coverage_complete,
    }


def build_serializable_dataset_partition_plan(
    plan: DatasetPartitionPlan,
) -> dict[str, Any]:
    """Serializes plan proof without source Historical Game card data."""
    return {
        "plan_version": plan.plan_version,
        "algorithm": plan.algorithm,
        "mode": plan.mode,
        "status": plan.status,
        "unavailable_reason": plan.unavailable_reason,
        "source_identity_fingerprint": plan.source_identity_fingerprint,
        "source_content_fingerprint": plan.source_content_fingerprint,
        "base_random_seed": plan.base_random_seed,
        "balance_basis": plan.balance_basis,
        "requested_partition_weights": build_serializable_dataset_partition_weights(
            plan.requested_partition_weights
        ),
        "source_record_count": plan.source_record_count,
        "source_sample_count": plan.source_sample_count,
        "assignments": [
            build_serializable_dataset_partition_assignment(assignment)
            for assignment in plan.assignments
        ],
        "partition_summaries": [
            build_serializable_dataset_partition_summary(summary)
            for summary in plan.partition_summaries
        ],
        "temporal_audit": (
            build_serializable_known_opponent_temporal_audit(plan.temporal_audit)
            if plan.temporal_audit is not None
            else None
        ),
        "partition_audit": (
            build_serializable_dataset_partition_audit(plan.partition_audit)
            if plan.partition_audit is not None
            else None
        ),
        "plan_fingerprint": plan.plan_fingerprint,
    }
