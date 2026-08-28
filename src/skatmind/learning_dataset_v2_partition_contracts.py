from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

from skatmind.dataset_partition_policy import CANONICAL_DATASET_PARTITIONS
from skatmind.learning_corpus_player_catalog import LearningCorpusPlayerCatalogV1
from skatmind.learning_dataset_v2_contracts import LearningDatasetV2

LEARNING_DATASET_PARTITION_PREPARATION_VERSION = 1
LEARNING_DATASET_MATCH_GROUP_VERSION = 1
LEARNING_DATASET_PLAYER_COMPONENT_VERSION = 1
LEARNING_DATASET_PARTITION_PLAN_VERSION = 1
LEARNING_DATASET_PARTITION_AUDIT_VERSION = 1
LEARNING_DATASET_PARTITIONED_VIEW_VERSION = 1
LEARNING_DATASET_PARTITION_EXPORT_VERSION = 1

LEARNING_DATASET_PARTITIONS: Final[tuple[str, ...]] = CANONICAL_DATASET_PARTITIONS
LEARNING_DATASET_PARTITION_MODES: Final[tuple[str, ...]] = (
    "known_player",
    "unseen_player",
)
LEARNING_DATASET_PARTITION_ALGORITHMS: Final[tuple[str, ...]] = (
    "temporal_known_player_match_group_v1",
    "component_balanced_unseen_player_match_group_v1",
)
LEARNING_DATASET_PARTITION_PLAN_STATUSES: Final[tuple[str, ...]] = (
    "complete",
    "unavailable",
)
LEARNING_DATASET_PARTITION_AUDIT_STATUSES: Final[tuple[str, ...]] = (
    "compliant",
    "non_compliant",
)
LEARNING_DATASET_PARTITION_UNAVAILABLE_REASONS: Final[tuple[str, ...]] = (
    "dataset_has_no_records",
    "insufficient_match_groups",
    "non_empty_record_partition_requirement_unsatisfied",
    "missing_match_played_at",
    "insufficient_time_groups",
    "known_player_train_coverage_unsatisfied",
    "insufficient_player_components",
    "component_distribution_infeasible",
)

TEMPORAL_KNOWN_PLAYER_MATCH_GROUP_ALGORITHM = "temporal_known_player_match_group_v1"
COMPONENT_BALANCED_UNSEEN_PLAYER_MATCH_GROUP_ALGORITHM = (
    "component_balanced_unseen_player_match_group_v1"
)
LEARNING_DATASET_PARTITION_ALGORITHM_BY_MODE: Final[dict[str, str]] = {
    "known_player": TEMPORAL_KNOWN_PLAYER_MATCH_GROUP_ALGORITHM,
    "unseen_player": COMPONENT_BALANCED_UNSEEN_PLAYER_MATCH_GROUP_ALGORITHM,
}

LEARNING_DATASET_PARTITION_SOURCE_POLICY = "active_explicit_current_match_snapshots_only"
LEARNING_DATASET_PARTITION_UNIT_POLICY = "match_snapshot_is_indivisible"
LEARNING_DATASET_PARTITION_BALANCE_POLICY = "record_count_primary_match_snapshot_count_secondary"
LEARNING_DATASET_PARTITION_ZERO_RECORD_POLICY = (
    "zero_record_active_match_groups_remain_assignment_units"
)
LEARNING_DATASET_KNOWN_PLAYER_POLICY = "strict_temporal_blocks_with_complete_train_player_coverage"
LEARNING_DATASET_UNSEEN_PLAYER_POLICY = "player_connected_match_components_are_indivisible"
LEARNING_DATASET_EQUAL_TIME_POLICY = "equal_parsed_played_at_instants_remain_in_one_partition"
LEARNING_DATASET_SEED_POLICY = "caller_seed_breaks_exact_objective_ties_only"
LEARNING_DATASET_EVIDENCE_COHORT_POLICY = "decision_evidence_follows_match_snapshot_partition"
LEARNING_DATASET_STATISTICS_CONTEXT_POLICY = (
    "strictly_prior_context_may_be_shared_only_as_recorded_evidence"
)
LEARNING_DATASET_PARTITION_PLAN_POLICY = "complete_or_unavailable_without_fallback"
LEARNING_DATASET_PARTITIONED_VIEW_POLICY = "lossless_source_dataset_plus_partition_indexes"
LEARNING_DATASET_PARTITION_INFORMATION_POLICY = (
    "split_selection_uses_only_ids_times_players_and_counts"
)
LEARNING_DATASET_PARTITION_PRIVACY_POLICY = (
    "private_local_partition_metadata_over_private_learning_data"
)
LEARNING_DATASET_PARTITION_EXPORT_POLICY = "deterministic_path_free_json_document"


def _require_version(value: object, expected: int, field_name: str) -> None:
    if type(value) is not int or value != expected:
        raise ValueError(f"{field_name} must equal {expected}.")


def _require_hash(value: object, field_name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{field_name} must be a lowercase SHA-256 hexadecimal value.")
    return value


def _require_identifier(
    value: object,
    field_name: str,
    *,
    allow_none: bool = False,
) -> str | None:
    if value is None and allow_none:
        return None
    if not isinstance(value, str) or not value or value != value.strip():
        nullable = " or null" if allow_none else ""
        raise ValueError(f"{field_name} must be a non-empty, non-padded string{nullable}.")
    return value


def _require_count(value: object, field_name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer.")
    return value


def _require_positive_integer(value: object, field_name: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer.")
    return value


def _require_boolean(value: object, field_name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{field_name} must be a boolean.")
    return value


def _require_tuple(value: object, field_name: str) -> tuple[Any, ...]:
    if type(value) is not tuple:
        raise ValueError(f"{field_name} must be an immutable tuple.")
    return value


def _require_hash_tuple(
    value: object,
    field_name: str,
    *,
    unique: bool = True,
) -> tuple[str, ...]:
    values = _require_tuple(value, field_name)
    for item in values:
        _require_hash(item, field_name)
    if unique and len(values) != len(set(values)):
        raise ValueError(f"{field_name} must contain unique IDs.")
    return values


def _require_identifier_tuple(
    value: object,
    field_name: str,
    *,
    unique: bool = True,
) -> tuple[str, ...]:
    values = _require_tuple(value, field_name)
    for item in values:
        _require_identifier(item, field_name)
    if unique and len(values) != len(set(values)):
        raise ValueError(f"{field_name} must contain unique values.")
    return values


def _require_partition(value: object, field_name: str = "partition") -> str:
    if value not in LEARNING_DATASET_PARTITIONS:
        raise ValueError(f"{field_name} must be one of {list(LEARNING_DATASET_PARTITIONS)}.")
    return value


@dataclass(frozen=True, slots=True, kw_only=True)
class LearningDatasetPartitionWeightsV1:
    train: int
    validation: int
    test: int

    def __post_init__(self) -> None:
        for field_name in LEARNING_DATASET_PARTITIONS:
            _require_positive_integer(getattr(self, field_name), field_name)

    @property
    def total_weight(self) -> int:
        return self.train + self.validation + self.test

    def to_dict(self) -> dict[str, int]:
        return {
            "train": self.train,
            "validation": self.validation,
            "test": self.test,
        }


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningDatasetPartitionPreparationRequestV1:
    learning_dataset_partition_preparation_version: int
    request_fingerprint: str
    mode: str
    algorithm: str
    base_random_seed: int
    partition_weights: LearningDatasetPartitionWeightsV1
    learning_dataset: LearningDatasetV2
    player_catalog: LearningCorpusPlayerCatalogV1

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("LearningDatasetPartitionPreparationRequestV1 requires its builder.")

    @classmethod
    def _from_validated(cls, **values: Any) -> LearningDatasetPartitionPreparationRequestV1:
        value = object.__new__(cls)
        for field_name, field_value in values.items():
            object.__setattr__(value, field_name, field_value)
        value._validate()
        return value

    def _validate(self) -> None:
        _require_version(
            self.learning_dataset_partition_preparation_version,
            LEARNING_DATASET_PARTITION_PREPARATION_VERSION,
            "learning_dataset_partition_preparation_version",
        )
        _require_hash(self.request_fingerprint, "request_fingerprint")
        if self.mode not in LEARNING_DATASET_PARTITION_MODES:
            raise ValueError("mode must be one canonical Learning Dataset partition mode.")
        if self.algorithm != LEARNING_DATASET_PARTITION_ALGORITHM_BY_MODE[self.mode]:
            raise ValueError("algorithm must be derived exactly from mode.")
        if type(self.base_random_seed) is not int:
            raise ValueError("base_random_seed must be an integer and not a boolean.")
        if type(self.partition_weights) is not LearningDatasetPartitionWeightsV1:
            raise ValueError("partition_weights must be exact LearningDatasetPartitionWeightsV1.")
        if type(self.learning_dataset) is not LearningDatasetV2:
            raise ValueError("learning_dataset must be an exact LearningDatasetV2.")
        if type(self.player_catalog) is not LearningCorpusPlayerCatalogV1:
            raise ValueError("player_catalog must be an exact LearningCorpusPlayerCatalogV1.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_dataset_partition_preparation_version": (
                self.learning_dataset_partition_preparation_version
            ),
            "request_fingerprint": self.request_fingerprint,
            "mode": self.mode,
            "algorithm": self.algorithm,
            "base_random_seed": self.base_random_seed,
            "partition_weights": self.partition_weights.to_dict(),
            "learning_dataset": self.learning_dataset.to_dict(),
            "player_catalog": self.player_catalog.to_dict(),
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class LearningDatasetMatchGroupV1:
    learning_dataset_match_group_version: int
    match_group_id: str
    match_snapshot_id: str
    match_id: str
    played_at: str | None
    player_ids: tuple[str, ...]
    record_ids: tuple[str, ...]
    skipped_decision_ids: tuple[str, ...]
    record_count: int
    skipped_decision_count: int
    observed_decision_count: int
    strategy_teacher_evidence_count: int
    commentary_evidence_count: int
    response_evidence_count: int
    unjoined_commentary_evidence_count: int
    unjoined_response_evidence_count: int
    zero_record: bool

    def __post_init__(self) -> None:
        _require_version(
            self.learning_dataset_match_group_version,
            LEARNING_DATASET_MATCH_GROUP_VERSION,
            "learning_dataset_match_group_version",
        )
        _require_hash(self.match_group_id, "match_group_id")
        _require_hash(self.match_snapshot_id, "match_snapshot_id")
        _require_identifier(self.match_id, "match_id")
        _require_identifier(self.played_at, "played_at", allow_none=True)
        _require_identifier_tuple(self.player_ids, "player_ids")
        if len(self.player_ids) != 3 or self.player_ids != tuple(sorted(self.player_ids)):
            raise ValueError("player_ids must contain exactly three sorted stable IDs.")
        _require_hash_tuple(self.record_ids, "record_ids")
        _require_hash_tuple(self.skipped_decision_ids, "skipped_decision_ids")
        for field_name in (
            "record_count",
            "skipped_decision_count",
            "observed_decision_count",
            "strategy_teacher_evidence_count",
            "commentary_evidence_count",
            "response_evidence_count",
            "unjoined_commentary_evidence_count",
            "unjoined_response_evidence_count",
        ):
            _require_count(getattr(self, field_name), field_name)
        if self.record_count != len(self.record_ids):
            raise ValueError("record_count must reconcile exactly.")
        if self.skipped_decision_count != len(self.skipped_decision_ids):
            raise ValueError("skipped_decision_count must reconcile exactly.")
        if self.observed_decision_count != self.record_count + self.skipped_decision_count:
            raise ValueError("observed_decision_count must reconcile exactly.")
        if self.observed_decision_count == 0:
            raise ValueError("An active Match group requires at least one Decision.")
        _require_boolean(self.zero_record, "zero_record")
        if self.zero_record != (self.record_count == 0):
            raise ValueError("zero_record must match record_count exactly.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_dataset_match_group_version": self.learning_dataset_match_group_version,
            "match_group_id": self.match_group_id,
            "match_snapshot_id": self.match_snapshot_id,
            "match_id": self.match_id,
            "played_at": self.played_at,
            "player_ids": list(self.player_ids),
            "record_ids": list(self.record_ids),
            "skipped_decision_ids": list(self.skipped_decision_ids),
            "record_count": self.record_count,
            "skipped_decision_count": self.skipped_decision_count,
            "observed_decision_count": self.observed_decision_count,
            "strategy_teacher_evidence_count": self.strategy_teacher_evidence_count,
            "commentary_evidence_count": self.commentary_evidence_count,
            "response_evidence_count": self.response_evidence_count,
            "unjoined_commentary_evidence_count": (self.unjoined_commentary_evidence_count),
            "unjoined_response_evidence_count": self.unjoined_response_evidence_count,
            "zero_record": self.zero_record,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class LearningDatasetPlayerComponentV1:
    learning_dataset_player_component_version: int
    component_id: str
    match_snapshot_ids: tuple[str, ...]
    player_ids: tuple[str, ...]
    record_count: int
    skipped_decision_count: int
    observed_decision_count: int
    match_snapshot_count: int

    def __post_init__(self) -> None:
        _require_version(
            self.learning_dataset_player_component_version,
            LEARNING_DATASET_PLAYER_COMPONENT_VERSION,
            "learning_dataset_player_component_version",
        )
        _require_hash(self.component_id, "component_id")
        _require_hash_tuple(self.match_snapshot_ids, "match_snapshot_ids")
        _require_identifier_tuple(self.player_ids, "player_ids")
        if self.match_snapshot_ids != tuple(sorted(self.match_snapshot_ids)):
            raise ValueError("match_snapshot_ids must be sorted.")
        if self.player_ids != tuple(sorted(self.player_ids)):
            raise ValueError("player_ids must be sorted.")
        for field_name in (
            "record_count",
            "skipped_decision_count",
            "observed_decision_count",
            "match_snapshot_count",
        ):
            _require_count(getattr(self, field_name), field_name)
        if self.match_snapshot_count != len(self.match_snapshot_ids):
            raise ValueError("match_snapshot_count must reconcile exactly.")
        if self.observed_decision_count != self.record_count + self.skipped_decision_count:
            raise ValueError("observed_decision_count must reconcile exactly.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_dataset_player_component_version": (
                self.learning_dataset_player_component_version
            ),
            "component_id": self.component_id,
            "match_snapshot_ids": list(self.match_snapshot_ids),
            "player_ids": list(self.player_ids),
            "record_count": self.record_count,
            "skipped_decision_count": self.skipped_decision_count,
            "observed_decision_count": self.observed_decision_count,
            "match_snapshot_count": self.match_snapshot_count,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class LearningDatasetMatchPartitionAssignmentV1:
    match_snapshot_id: str
    partition: str

    def __post_init__(self) -> None:
        _require_hash(self.match_snapshot_id, "match_snapshot_id")
        _require_partition(self.partition)

    def to_dict(self) -> dict[str, str]:
        return {
            "match_snapshot_id": self.match_snapshot_id,
            "partition": self.partition,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class LearningDatasetPartitionSummaryV1:
    partition: str
    requested_weight: int
    match_snapshot_count: int
    record_count: int
    skipped_decision_count: int
    observed_decision_count: int
    strategy_teacher_evidence_count: int
    commentary_evidence_count: int
    response_evidence_count: int
    distinct_player_count: int
    player_ids: tuple[str, ...]
    target_record_count_numerator: int
    target_record_count_denominator: int
    record_count_deviation_numerator: int
    target_match_count_numerator: int
    target_match_count_denominator: int
    match_count_deviation_numerator: int

    def __post_init__(self) -> None:
        _require_partition(self.partition)
        _require_positive_integer(self.requested_weight, "requested_weight")
        for field_name in (
            "match_snapshot_count",
            "record_count",
            "skipped_decision_count",
            "observed_decision_count",
            "strategy_teacher_evidence_count",
            "commentary_evidence_count",
            "response_evidence_count",
            "distinct_player_count",
            "target_record_count_numerator",
            "target_match_count_numerator",
        ):
            _require_count(getattr(self, field_name), field_name)
        for field_name in (
            "target_record_count_denominator",
            "target_match_count_denominator",
        ):
            _require_positive_integer(getattr(self, field_name), field_name)
        for field_name in (
            "record_count_deviation_numerator",
            "match_count_deviation_numerator",
        ):
            if type(getattr(self, field_name)) is not int:
                raise ValueError(f"{field_name} must be an integer.")
        _require_identifier_tuple(self.player_ids, "player_ids")
        if self.player_ids != tuple(sorted(self.player_ids)):
            raise ValueError("player_ids must be sorted.")
        if self.distinct_player_count != len(self.player_ids):
            raise ValueError("distinct_player_count must reconcile exactly.")
        if self.observed_decision_count != self.record_count + self.skipped_decision_count:
            raise ValueError("observed_decision_count must reconcile exactly.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "partition": self.partition,
            "requested_weight": self.requested_weight,
            "match_snapshot_count": self.match_snapshot_count,
            "record_count": self.record_count,
            "skipped_decision_count": self.skipped_decision_count,
            "observed_decision_count": self.observed_decision_count,
            "strategy_teacher_evidence_count": self.strategy_teacher_evidence_count,
            "commentary_evidence_count": self.commentary_evidence_count,
            "response_evidence_count": self.response_evidence_count,
            "distinct_player_count": self.distinct_player_count,
            "player_ids": list(self.player_ids),
            "target_record_count_numerator": self.target_record_count_numerator,
            "target_record_count_denominator": self.target_record_count_denominator,
            "record_count_deviation_numerator": self.record_count_deviation_numerator,
            "target_match_count_numerator": self.target_match_count_numerator,
            "target_match_count_denominator": self.target_match_count_denominator,
            "match_count_deviation_numerator": self.match_count_deviation_numerator,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class LearningDatasetTemporalPartitionBoundaryV1:
    partition: str
    minimum_played_at: str
    maximum_played_at: str
    time_group_count: int
    match_snapshot_count: int
    record_count: int

    def __post_init__(self) -> None:
        _require_partition(self.partition)
        _require_identifier(self.minimum_played_at, "minimum_played_at")
        _require_identifier(self.maximum_played_at, "maximum_played_at")
        for field_name in ("time_group_count", "match_snapshot_count", "record_count"):
            _require_positive_integer(getattr(self, field_name), field_name)

    def to_dict(self) -> dict[str, Any]:
        return {
            "partition": self.partition,
            "minimum_played_at": self.minimum_played_at,
            "maximum_played_at": self.maximum_played_at,
            "time_group_count": self.time_group_count,
            "match_snapshot_count": self.match_snapshot_count,
            "record_count": self.record_count,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class LearningDatasetKnownPlayerTemporalAuditV1:
    partition_boundaries: tuple[LearningDatasetTemporalPartitionBoundaryV1, ...]
    train_match_snapshot_ids: tuple[str, ...]
    validation_match_snapshot_ids: tuple[str, ...]
    test_match_snapshot_ids: tuple[str, ...]
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

    def __post_init__(self) -> None:
        _require_tuple(self.partition_boundaries, "partition_boundaries")
        if any(
            type(item) is not LearningDatasetTemporalPartitionBoundaryV1
            for item in self.partition_boundaries
        ):
            raise ValueError("partition_boundaries must contain exact boundary values.")
        if tuple(item.partition for item in self.partition_boundaries) != (
            LEARNING_DATASET_PARTITIONS
        ):
            raise ValueError("partition_boundaries must use canonical partition order.")
        for field_name in (
            "train_match_snapshot_ids",
            "validation_match_snapshot_ids",
            "test_match_snapshot_ids",
        ):
            values = _require_hash_tuple(getattr(self, field_name), field_name)
            if values != tuple(sorted(values)):
                raise ValueError(f"{field_name} must be sorted.")
        for field_name in (
            "train_player_ids",
            "validation_player_ids",
            "test_player_ids",
            "validation_covered_player_ids",
            "validation_uncovered_player_ids",
            "test_covered_player_ids",
            "test_uncovered_player_ids",
        ):
            values = _require_identifier_tuple(getattr(self, field_name), field_name)
            if values != tuple(sorted(values)):
                raise ValueError(f"{field_name} must be sorted.")
        _require_positive_integer(self.time_group_count, "time_group_count")
        for field_name in (
            "all_played_at_present",
            "strict_partition_order",
            "equal_timestamp_groups_preserved",
            "validation_train_coverage_complete",
            "test_train_coverage_complete",
        ):
            _require_boolean(getattr(self, field_name), field_name)
        train = set(self.train_player_ids)
        validation = set(self.validation_player_ids)
        test = set(self.test_player_ids)
        if (
            set(self.validation_covered_player_ids) != validation & train
            or set(self.validation_uncovered_player_ids) != validation - train
        ):
            raise ValueError("Validation Player coverage fields must reconcile exactly.")
        if (
            set(self.test_covered_player_ids) != test & train
            or set(self.test_uncovered_player_ids) != test - train
        ):
            raise ValueError("Test Player coverage fields must reconcile exactly.")
        if self.validation_train_coverage_complete != (
            not self.validation_uncovered_player_ids
        ) or self.test_train_coverage_complete != (not self.test_uncovered_player_ids):
            raise ValueError("Player coverage booleans must reconcile exactly.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "partition_boundaries": [item.to_dict() for item in self.partition_boundaries],
            "train_match_snapshot_ids": list(self.train_match_snapshot_ids),
            "validation_match_snapshot_ids": list(self.validation_match_snapshot_ids),
            "test_match_snapshot_ids": list(self.test_match_snapshot_ids),
            "train_player_ids": list(self.train_player_ids),
            "validation_player_ids": list(self.validation_player_ids),
            "test_player_ids": list(self.test_player_ids),
            "validation_covered_player_ids": list(self.validation_covered_player_ids),
            "validation_uncovered_player_ids": list(self.validation_uncovered_player_ids),
            "test_covered_player_ids": list(self.test_covered_player_ids),
            "test_uncovered_player_ids": list(self.test_uncovered_player_ids),
            "all_played_at_present": self.all_played_at_present,
            "time_group_count": self.time_group_count,
            "strict_partition_order": self.strict_partition_order,
            "equal_timestamp_groups_preserved": self.equal_timestamp_groups_preserved,
            "validation_train_coverage_complete": (self.validation_train_coverage_complete),
            "test_train_coverage_complete": self.test_train_coverage_complete,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class LearningDatasetUnseenPlayerComponentAuditV1:
    component_count: int
    components: tuple[LearningDatasetPlayerComponentV1, ...]
    train_component_ids: tuple[str, ...]
    validation_component_ids: tuple[str, ...]
    test_component_ids: tuple[str, ...]
    train_player_ids: tuple[str, ...]
    validation_player_ids: tuple[str, ...]
    test_player_ids: tuple[str, ...]
    train_validation_overlap_player_ids: tuple[str, ...]
    train_test_overlap_player_ids: tuple[str, ...]
    validation_test_overlap_player_ids: tuple[str, ...]
    player_disjoint: bool
    components_indivisible: bool
    all_partitions_have_records: bool
    local_move_optimal: bool
    local_swap_optimal: bool

    def __post_init__(self) -> None:
        _require_count(self.component_count, "component_count")
        _require_tuple(self.components, "components")
        if any(type(item) is not LearningDatasetPlayerComponentV1 for item in self.components):
            raise ValueError("components must contain exact Player Component values.")
        if self.component_count != len(self.components):
            raise ValueError("component_count must reconcile exactly.")
        for field_name in (
            "train_component_ids",
            "validation_component_ids",
            "test_component_ids",
        ):
            _require_hash_tuple(getattr(self, field_name), field_name)
        for field_name in (
            "train_player_ids",
            "validation_player_ids",
            "test_player_ids",
            "train_validation_overlap_player_ids",
            "train_test_overlap_player_ids",
            "validation_test_overlap_player_ids",
        ):
            values = _require_identifier_tuple(getattr(self, field_name), field_name)
            if values != tuple(sorted(values)):
                raise ValueError(f"{field_name} must be sorted.")
        for field_name in (
            "player_disjoint",
            "components_indivisible",
            "all_partitions_have_records",
            "local_move_optimal",
            "local_swap_optimal",
        ):
            _require_boolean(getattr(self, field_name), field_name)
        component_ids = {item.component_id for item in self.components}
        assigned_component_ids = (
            *self.train_component_ids,
            *self.validation_component_ids,
            *self.test_component_ids,
        )
        if (
            len(assigned_component_ids) != len(set(assigned_component_ids))
            or set(assigned_component_ids) != component_ids
        ):
            raise ValueError("Component audit partitions must assign every component once.")
        train = set(self.train_player_ids)
        validation = set(self.validation_player_ids)
        test = set(self.test_player_ids)
        if set(self.train_validation_overlap_player_ids) != train & validation:
            raise ValueError("Train/Validation Player overlap must reconcile exactly.")
        if set(self.train_test_overlap_player_ids) != train & test:
            raise ValueError("Train/Test Player overlap must reconcile exactly.")
        if set(self.validation_test_overlap_player_ids) != validation & test:
            raise ValueError("Validation/Test Player overlap must reconcile exactly.")
        if self.player_disjoint != (
            not (
                self.train_validation_overlap_player_ids
                or self.train_test_overlap_player_ids
                or self.validation_test_overlap_player_ids
            )
        ):
            raise ValueError("player_disjoint must reconcile with exact overlaps.")
        components_by_id = {item.component_id: item for item in self.components}
        record_counts = tuple(
            sum(components_by_id[item_id].record_count for item_id in component_ids)
            for component_ids in (
                self.train_component_ids,
                self.validation_component_ids,
                self.test_component_ids,
            )
        )
        if self.all_partitions_have_records != all(count > 0 for count in record_counts):
            raise ValueError("all_partitions_have_records must reconcile exactly.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_count": self.component_count,
            "components": [item.to_dict() for item in self.components],
            "train_component_ids": list(self.train_component_ids),
            "validation_component_ids": list(self.validation_component_ids),
            "test_component_ids": list(self.test_component_ids),
            "train_player_ids": list(self.train_player_ids),
            "validation_player_ids": list(self.validation_player_ids),
            "test_player_ids": list(self.test_player_ids),
            "train_validation_overlap_player_ids": list(self.train_validation_overlap_player_ids),
            "train_test_overlap_player_ids": list(self.train_test_overlap_player_ids),
            "validation_test_overlap_player_ids": list(self.validation_test_overlap_player_ids),
            "player_disjoint": self.player_disjoint,
            "components_indivisible": self.components_indivisible,
            "all_partitions_have_records": self.all_partitions_have_records,
            "local_move_optimal": self.local_move_optimal,
            "local_swap_optimal": self.local_swap_optimal,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class LearningDatasetPartitionLeakageAuditV1:
    learning_dataset_partition_audit_version: int
    audit_fingerprint: str
    status: str
    mode: str
    source_dataset_fingerprint: str
    plan_fingerprint: str
    inactive_current_match_snapshot_ids: tuple[str, ...]
    assigned_match_snapshot_count: int
    assigned_match_snapshot_ids: tuple[str, ...]
    unassigned_active_match_snapshot_ids: tuple[str, ...]
    unknown_match_snapshot_assignment_ids: tuple[str, ...]
    duplicate_match_snapshot_assignment_ids: tuple[str, ...]
    match_snapshot_partition_overlap_ids: tuple[str, ...]
    match_id_partition_overlap_ids: tuple[str, ...]
    record_partition_overlap_ids: tuple[str, ...]
    skipped_decision_partition_overlap_ids: tuple[str, ...]
    strategy_teacher_partition_overlap_ids: tuple[str, ...]
    commentary_partition_overlap_ids: tuple[str, ...]
    response_partition_overlap_ids: tuple[str, ...]
    unjoined_commentary_partition_overlap_ids: tuple[str, ...]
    unjoined_response_partition_overlap_ids: tuple[str, ...]
    statistics_context_temporal_violation_record_ids: tuple[str, ...]
    shared_statistics_observation_ids: tuple[str, ...]
    match_group_closure_complete: bool
    record_closure_complete: bool
    skipped_decision_closure_complete: bool
    teacher_closure_complete: bool
    commentary_closure_complete: bool
    response_closure_complete: bool
    statistics_context_temporal_safety_complete: bool

    def __post_init__(self) -> None:
        _require_version(
            self.learning_dataset_partition_audit_version,
            LEARNING_DATASET_PARTITION_AUDIT_VERSION,
            "learning_dataset_partition_audit_version",
        )
        for field_name in (
            "audit_fingerprint",
            "source_dataset_fingerprint",
            "plan_fingerprint",
        ):
            _require_hash(getattr(self, field_name), field_name)
        if self.status not in LEARNING_DATASET_PARTITION_AUDIT_STATUSES:
            raise ValueError("status must be compliant or non_compliant.")
        if self.mode not in LEARNING_DATASET_PARTITION_MODES:
            raise ValueError("mode must be one canonical partition mode.")
        _require_count(self.assigned_match_snapshot_count, "assigned_match_snapshot_count")
        for field_name in (
            "inactive_current_match_snapshot_ids",
            "assigned_match_snapshot_ids",
            "unassigned_active_match_snapshot_ids",
            "unknown_match_snapshot_assignment_ids",
            "duplicate_match_snapshot_assignment_ids",
            "match_snapshot_partition_overlap_ids",
            "record_partition_overlap_ids",
            "skipped_decision_partition_overlap_ids",
            "strategy_teacher_partition_overlap_ids",
            "commentary_partition_overlap_ids",
            "response_partition_overlap_ids",
            "unjoined_commentary_partition_overlap_ids",
            "unjoined_response_partition_overlap_ids",
            "statistics_context_temporal_violation_record_ids",
            "shared_statistics_observation_ids",
        ):
            _require_hash_tuple(getattr(self, field_name), field_name)
        if (
            self.assigned_match_snapshot_count != len(self.assigned_match_snapshot_ids)
            or len(self.assigned_match_snapshot_ids)
            != len(set(self.assigned_match_snapshot_ids))
        ):
            raise ValueError("Assigned Match Snapshot IDs must reconcile exactly.")
        _require_identifier_tuple(
            self.match_id_partition_overlap_ids,
            "match_id_partition_overlap_ids",
        )
        for field_name in (
            "match_group_closure_complete",
            "record_closure_complete",
            "skipped_decision_closure_complete",
            "teacher_closure_complete",
            "commentary_closure_complete",
            "response_closure_complete",
            "statistics_context_temporal_safety_complete",
        ):
            _require_boolean(getattr(self, field_name), field_name)
        overlap_fields = (
            self.unassigned_active_match_snapshot_ids,
            self.unknown_match_snapshot_assignment_ids,
            self.duplicate_match_snapshot_assignment_ids,
            self.match_snapshot_partition_overlap_ids,
            self.match_id_partition_overlap_ids,
            self.record_partition_overlap_ids,
            self.skipped_decision_partition_overlap_ids,
            self.strategy_teacher_partition_overlap_ids,
            self.commentary_partition_overlap_ids,
            self.response_partition_overlap_ids,
            self.unjoined_commentary_partition_overlap_ids,
            self.unjoined_response_partition_overlap_ids,
            self.statistics_context_temporal_violation_record_ids,
        )
        closure_fields = (
            self.match_group_closure_complete,
            self.record_closure_complete,
            self.skipped_decision_closure_complete,
            self.teacher_closure_complete,
            self.commentary_closure_complete,
            self.response_closure_complete,
            self.statistics_context_temporal_safety_complete,
        )
        expected_compliant = (
            not any(overlap_fields)
            and all(closure_fields)
            and (self.mode != "unseen_player" or not self.shared_statistics_observation_ids)
        )
        if (self.status == "compliant") != expected_compliant:
            raise ValueError("Audit status must reconcile with every leakage dimension.")
        from skatmind.learning_dataset_v2_partition_identity import (
            build_learning_dataset_partition_audit_fingerprint_v1,
        )

        if self.audit_fingerprint != build_learning_dataset_partition_audit_fingerprint_v1(
            self
        ):
            raise ValueError("audit_fingerprint must cover the exact leakage Audit.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_dataset_partition_audit_version": (
                self.learning_dataset_partition_audit_version
            ),
            "audit_fingerprint": self.audit_fingerprint,
            "status": self.status,
            "mode": self.mode,
            "source_dataset_fingerprint": self.source_dataset_fingerprint,
            "plan_fingerprint": self.plan_fingerprint,
            "inactive_current_match_snapshot_ids": list(self.inactive_current_match_snapshot_ids),
            "assigned_match_snapshot_count": self.assigned_match_snapshot_count,
            "assigned_match_snapshot_ids": list(self.assigned_match_snapshot_ids),
            "unassigned_active_match_snapshot_ids": list(self.unassigned_active_match_snapshot_ids),
            "unknown_match_snapshot_assignment_ids": list(
                self.unknown_match_snapshot_assignment_ids
            ),
            "duplicate_match_snapshot_assignment_ids": list(
                self.duplicate_match_snapshot_assignment_ids
            ),
            "match_snapshot_partition_overlap_ids": list(self.match_snapshot_partition_overlap_ids),
            "match_id_partition_overlap_ids": list(self.match_id_partition_overlap_ids),
            "record_partition_overlap_ids": list(self.record_partition_overlap_ids),
            "skipped_decision_partition_overlap_ids": list(
                self.skipped_decision_partition_overlap_ids
            ),
            "strategy_teacher_partition_overlap_ids": list(
                self.strategy_teacher_partition_overlap_ids
            ),
            "commentary_partition_overlap_ids": list(self.commentary_partition_overlap_ids),
            "response_partition_overlap_ids": list(self.response_partition_overlap_ids),
            "unjoined_commentary_partition_overlap_ids": list(
                self.unjoined_commentary_partition_overlap_ids
            ),
            "unjoined_response_partition_overlap_ids": list(
                self.unjoined_response_partition_overlap_ids
            ),
            "statistics_context_temporal_violation_record_ids": list(
                self.statistics_context_temporal_violation_record_ids
            ),
            "shared_statistics_observation_ids": list(self.shared_statistics_observation_ids),
            "match_group_closure_complete": self.match_group_closure_complete,
            "record_closure_complete": self.record_closure_complete,
            "skipped_decision_closure_complete": self.skipped_decision_closure_complete,
            "teacher_closure_complete": self.teacher_closure_complete,
            "commentary_closure_complete": self.commentary_closure_complete,
            "response_closure_complete": self.response_closure_complete,
            "statistics_context_temporal_safety_complete": (
                self.statistics_context_temporal_safety_complete
            ),
        }


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningDatasetPartitionPlanV1:
    learning_dataset_partition_plan_version: int
    algorithm: str
    mode: str
    status: str
    unavailable_reason: str | None
    source_identity_fingerprint: str
    source_content_fingerprint: str
    request_fingerprint: str
    base_random_seed: int
    balance_basis: str
    secondary_balance_basis: str
    requested_partition_weights: LearningDatasetPartitionWeightsV1
    source_current_match_count: int
    source_active_match_group_count: int
    source_inactive_match_count: int
    source_record_count: int
    source_skipped_decision_count: int
    assignments: tuple[LearningDatasetMatchPartitionAssignmentV1, ...]
    partition_summaries: tuple[LearningDatasetPartitionSummaryV1, ...]
    known_player_temporal_audit: LearningDatasetKnownPlayerTemporalAuditV1 | None
    unseen_player_component_audit: LearningDatasetUnseenPlayerComponentAuditV1 | None
    leakage_audit: LearningDatasetPartitionLeakageAuditV1 | None
    plan_fingerprint: str

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("LearningDatasetPartitionPlanV1 requires its focused builder.")

    @classmethod
    def _from_validated(cls, **values: Any) -> LearningDatasetPartitionPlanV1:
        value = object.__new__(cls)
        for field_name, field_value in values.items():
            object.__setattr__(value, field_name, field_value)
        value._validate()
        return value

    def _validate(self) -> None:
        _require_version(
            self.learning_dataset_partition_plan_version,
            LEARNING_DATASET_PARTITION_PLAN_VERSION,
            "learning_dataset_partition_plan_version",
        )
        if self.mode not in LEARNING_DATASET_PARTITION_MODES:
            raise ValueError("mode must be one canonical partition mode.")
        if self.algorithm != LEARNING_DATASET_PARTITION_ALGORITHM_BY_MODE[self.mode]:
            raise ValueError("algorithm must match mode exactly.")
        if self.status not in LEARNING_DATASET_PARTITION_PLAN_STATUSES:
            raise ValueError("status must be complete or unavailable.")
        if self.unavailable_reason is not None and (
            self.unavailable_reason not in LEARNING_DATASET_PARTITION_UNAVAILABLE_REASONS
        ):
            raise ValueError("unavailable_reason must be one canonical reason or null.")
        for field_name in (
            "source_identity_fingerprint",
            "source_content_fingerprint",
            "request_fingerprint",
            "plan_fingerprint",
        ):
            _require_hash(getattr(self, field_name), field_name)
        if type(self.base_random_seed) is not int:
            raise ValueError("base_random_seed must be an integer and not a boolean.")
        if self.balance_basis != "record_count":
            raise ValueError("balance_basis must equal record_count.")
        if self.secondary_balance_basis != "match_snapshot_count":
            raise ValueError("secondary_balance_basis must equal match_snapshot_count.")
        if type(self.requested_partition_weights) is not LearningDatasetPartitionWeightsV1:
            raise ValueError("requested_partition_weights must use the exact contract.")
        for field_name in (
            "source_current_match_count",
            "source_active_match_group_count",
            "source_inactive_match_count",
            "source_record_count",
            "source_skipped_decision_count",
        ):
            _require_count(getattr(self, field_name), field_name)
        if self.source_current_match_count != (
            self.source_active_match_group_count + self.source_inactive_match_count
        ):
            raise ValueError("Current Match counts must reconcile exactly.")
        _require_tuple(self.assignments, "assignments")
        _require_tuple(self.partition_summaries, "partition_summaries")
        if any(
            type(item) is not LearningDatasetMatchPartitionAssignmentV1
            for item in self.assignments
        ):
            raise ValueError("assignments must contain exact Match partition assignments.")
        if any(
            type(item) is not LearningDatasetPartitionSummaryV1
            for item in self.partition_summaries
        ):
            raise ValueError("partition_summaries must contain exact partition summaries.")
        assignment_ids = tuple(item.match_snapshot_id for item in self.assignments)
        if len(assignment_ids) != len(set(assignment_ids)):
            raise ValueError("assignments must contain each active Match Snapshot exactly once.")
        from skatmind.learning_dataset_v2_partition_identity import (
            build_learning_dataset_partition_plan_fingerprint_v1,
        )

        if self.plan_fingerprint != build_learning_dataset_partition_plan_fingerprint_v1(self):
            raise ValueError("plan_fingerprint must cover the exact partition Plan.")
        if self.status == "unavailable":
            if self.unavailable_reason is None:
                raise ValueError("An unavailable Plan requires one exact reason.")
            if any(
                (
                    self.assignments,
                    self.partition_summaries,
                    self.known_player_temporal_audit,
                    self.unseen_player_component_audit,
                    self.leakage_audit,
                )
            ):
                raise ValueError("An unavailable Plan cannot contain assignments or audits.")
            return
        if self.unavailable_reason is not None:
            raise ValueError("A complete Plan cannot have an unavailable reason.")
        if len(self.assignments) != self.source_active_match_group_count:
            raise ValueError("Complete assignments must cover every active Match group.")
        if tuple(item.partition for item in self.partition_summaries) != (
            LEARNING_DATASET_PARTITIONS
        ):
            raise ValueError("Partition summaries must use canonical partition order.")
        weights = self.requested_partition_weights.to_dict()
        total_weight = self.requested_partition_weights.total_weight
        for summary in self.partition_summaries:
            expected_weight = weights[summary.partition]
            expected_match_count = sum(
                item.partition == summary.partition for item in self.assignments
            )
            if (
                summary.requested_weight != expected_weight
                or summary.match_snapshot_count != expected_match_count
                or summary.target_record_count_numerator
                != self.source_record_count * expected_weight
                or summary.target_record_count_denominator != total_weight
                or summary.record_count_deviation_numerator
                != summary.record_count * total_weight
                - summary.target_record_count_numerator
                or summary.target_match_count_numerator
                != self.source_active_match_group_count * expected_weight
                or summary.target_match_count_denominator != total_weight
                or summary.match_count_deviation_numerator
                != summary.match_snapshot_count * total_weight
                - summary.target_match_count_numerator
            ):
                raise ValueError("Partition summaries must reconcile with assignments and weights.")
        if (
            sum(item.match_snapshot_count for item in self.partition_summaries)
            != self.source_active_match_group_count
            or sum(item.record_count for item in self.partition_summaries)
            != self.source_record_count
            or sum(item.skipped_decision_count for item in self.partition_summaries)
            != self.source_skipped_decision_count
        ):
            raise ValueError("Partition summary counts must reconcile with source counts.")
        if self.mode == "known_player":
            if (
                self.known_player_temporal_audit is None
                or self.unseen_player_component_audit is not None
            ):
                raise ValueError("A complete Known-player Plan requires only its temporal audit.")
        elif (
            self.unseen_player_component_audit is None
            or self.known_player_temporal_audit is not None
        ):
            raise ValueError("A complete unseen-player Plan requires only its component audit.")
        if self.leakage_audit is None or self.leakage_audit.status != "compliant":
            raise ValueError("A complete Plan requires one compliant leakage audit.")
        if (
            self.leakage_audit.mode != self.mode
            or self.leakage_audit.assigned_match_snapshot_count
            != self.source_active_match_group_count
            or self.leakage_audit.assigned_match_snapshot_ids != assignment_ids
            or len(self.leakage_audit.inactive_current_match_snapshot_ids)
            != self.source_inactive_match_count
        ):
            raise ValueError("Leakage Audit must reconcile with the Plan source counts.")
        if self.leakage_audit.plan_fingerprint != self.plan_fingerprint:
            raise ValueError("Leakage Audit must reference the exact Plan fingerprint.")
        if self.mode == "known_player":
            assert self.known_player_temporal_audit is not None
            audit = self.known_player_temporal_audit
            if (
                not all(
                    (
                        audit.all_played_at_present,
                        audit.strict_partition_order,
                        audit.equal_timestamp_groups_preserved,
                        audit.validation_train_coverage_complete,
                        audit.test_train_coverage_complete,
                    )
                )
                or audit.validation_uncovered_player_ids
                or audit.test_uncovered_player_ids
            ):
                raise ValueError("A complete Known-player Plan requires a compliant audit.")
            snapshot_ids_by_partition = {
                "train": audit.train_match_snapshot_ids,
                "validation": audit.validation_match_snapshot_ids,
                "test": audit.test_match_snapshot_ids,
            }
            player_ids_by_partition = {
                "train": audit.train_player_ids,
                "validation": audit.validation_player_ids,
                "test": audit.test_player_ids,
            }
            boundaries_by_partition = {
                item.partition: item for item in audit.partition_boundaries
            }
            for summary in self.partition_summaries:
                assigned_ids = tuple(
                    sorted(
                        item.match_snapshot_id
                        for item in self.assignments
                        if item.partition == summary.partition
                    )
                )
                boundary = boundaries_by_partition[summary.partition]
                if (
                    assigned_ids != snapshot_ids_by_partition[summary.partition]
                    or summary.player_ids != player_ids_by_partition[summary.partition]
                    or summary.match_snapshot_count != boundary.match_snapshot_count
                    or summary.record_count != boundary.record_count
                ):
                    raise ValueError(
                        "Known-player assignments and summaries must match the temporal audit."
                    )
        else:
            assert self.unseen_player_component_audit is not None
            audit = self.unseen_player_component_audit
            if not all(
                (
                    audit.player_disjoint,
                    audit.components_indivisible,
                    audit.all_partitions_have_records,
                    audit.local_move_optimal,
                    audit.local_swap_optimal,
                )
            ):
                raise ValueError("A complete unseen-player Plan requires a compliant audit.")
            components_by_id = {item.component_id: item for item in audit.components}
            component_ids_by_partition = {
                "train": audit.train_component_ids,
                "validation": audit.validation_component_ids,
                "test": audit.test_component_ids,
            }
            player_ids_by_partition = {
                "train": audit.train_player_ids,
                "validation": audit.validation_player_ids,
                "test": audit.test_player_ids,
            }
            for summary in self.partition_summaries:
                components = tuple(
                    components_by_id[item_id]
                    for item_id in component_ids_by_partition[summary.partition]
                )
                expected_snapshot_ids = {
                    snapshot_id
                    for component in components
                    for snapshot_id in component.match_snapshot_ids
                }
                assigned_snapshot_ids = {
                    item.match_snapshot_id
                    for item in self.assignments
                    if item.partition == summary.partition
                }
                if (
                    assigned_snapshot_ids != expected_snapshot_ids
                    or summary.player_ids != player_ids_by_partition[summary.partition]
                    or summary.match_snapshot_count
                    != sum(item.match_snapshot_count for item in components)
                    or summary.record_count != sum(item.record_count for item in components)
                    or summary.skipped_decision_count
                    != sum(item.skipped_decision_count for item in components)
                ):
                    raise ValueError(
                        "Unseen-player assignments and summaries must match the component audit."
                    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_dataset_partition_plan_version": (
                self.learning_dataset_partition_plan_version
            ),
            "algorithm": self.algorithm,
            "mode": self.mode,
            "status": self.status,
            "unavailable_reason": self.unavailable_reason,
            "source_identity_fingerprint": self.source_identity_fingerprint,
            "source_content_fingerprint": self.source_content_fingerprint,
            "request_fingerprint": self.request_fingerprint,
            "base_random_seed": self.base_random_seed,
            "balance_basis": self.balance_basis,
            "secondary_balance_basis": self.secondary_balance_basis,
            "requested_partition_weights": self.requested_partition_weights.to_dict(),
            "source_current_match_count": self.source_current_match_count,
            "source_active_match_group_count": self.source_active_match_group_count,
            "source_inactive_match_count": self.source_inactive_match_count,
            "source_record_count": self.source_record_count,
            "source_skipped_decision_count": self.source_skipped_decision_count,
            "assignments": [item.to_dict() for item in self.assignments],
            "partition_summaries": [item.to_dict() for item in self.partition_summaries],
            "known_player_temporal_audit": (
                None
                if self.known_player_temporal_audit is None
                else self.known_player_temporal_audit.to_dict()
            ),
            "unseen_player_component_audit": (
                None
                if self.unseen_player_component_audit is None
                else self.unseen_player_component_audit.to_dict()
            ),
            "leakage_audit": (None if self.leakage_audit is None else self.leakage_audit.to_dict()),
            "plan_fingerprint": self.plan_fingerprint,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class LearningDatasetPartitionSliceV1:
    partition: str
    match_snapshot_ids: tuple[str, ...]
    record_ids: tuple[str, ...]
    skipped_decision_ids: tuple[str, ...]
    statistics_observation_ids: tuple[str, ...]
    strategy_teacher_evidence_ids: tuple[str, ...]
    commentary_evidence_ids: tuple[str, ...]
    response_evidence_ids: tuple[str, ...]
    unjoined_commentary_evidence_ids: tuple[str, ...]
    unjoined_response_evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_partition(self.partition)
        for field_name in (
            "match_snapshot_ids",
            "record_ids",
            "skipped_decision_ids",
            "statistics_observation_ids",
            "strategy_teacher_evidence_ids",
            "commentary_evidence_ids",
            "response_evidence_ids",
            "unjoined_commentary_evidence_ids",
            "unjoined_response_evidence_ids",
        ):
            _require_hash_tuple(getattr(self, field_name), field_name)

    def to_dict(self) -> dict[str, Any]:
        return {
            "partition": self.partition,
            "match_snapshot_ids": list(self.match_snapshot_ids),
            "record_ids": list(self.record_ids),
            "skipped_decision_ids": list(self.skipped_decision_ids),
            "statistics_observation_ids": list(self.statistics_observation_ids),
            "strategy_teacher_evidence_ids": list(self.strategy_teacher_evidence_ids),
            "commentary_evidence_ids": list(self.commentary_evidence_ids),
            "response_evidence_ids": list(self.response_evidence_ids),
            "unjoined_commentary_evidence_ids": list(self.unjoined_commentary_evidence_ids),
            "unjoined_response_evidence_ids": list(self.unjoined_response_evidence_ids),
        }


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningDatasetPartitionedViewV1:
    learning_dataset_partitioned_view_version: int
    partitioned_view_fingerprint: str
    source_dataset_fingerprint: str
    plan_fingerprint: str
    learning_dataset: LearningDatasetV2
    partitions: tuple[LearningDatasetPartitionSliceV1, ...]

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("LearningDatasetPartitionedViewV1 requires its focused builder.")

    @classmethod
    def _from_validated(cls, **values: Any) -> LearningDatasetPartitionedViewV1:
        value = object.__new__(cls)
        for field_name, field_value in values.items():
            object.__setattr__(value, field_name, field_value)
        value._validate()
        return value

    def _validate(self) -> None:
        _require_version(
            self.learning_dataset_partitioned_view_version,
            LEARNING_DATASET_PARTITIONED_VIEW_VERSION,
            "learning_dataset_partitioned_view_version",
        )
        for field_name in (
            "partitioned_view_fingerprint",
            "source_dataset_fingerprint",
            "plan_fingerprint",
        ):
            _require_hash(getattr(self, field_name), field_name)
        if type(self.learning_dataset) is not LearningDatasetV2:
            raise ValueError("learning_dataset must be the exact source Dataset.")
        if self.source_dataset_fingerprint != self.learning_dataset.dataset_fingerprint:
            raise ValueError("source_dataset_fingerprint must match the source Dataset.")
        _require_tuple(self.partitions, "partitions")
        if tuple(item.partition for item in self.partitions) != LEARNING_DATASET_PARTITIONS:
            raise ValueError("partitions must use canonical partition order.")
        if any(type(item) is not LearningDatasetPartitionSliceV1 for item in self.partitions):
            raise ValueError("partitions must contain exact partition slices.")
        dataset = self.learning_dataset
        active_snapshot_ids = tuple(
            snapshot_id
            for snapshot_id in dataset.current_match_snapshot_ids
            if any(
                record.source_context.match_snapshot_id == snapshot_id
                for record in dataset.records
            )
            or any(
                skipped.match_snapshot_id == snapshot_id
                for skipped in dataset.skipped_decisions
            )
        )
        sliced_snapshot_ids = tuple(
            snapshot_id for item in self.partitions for snapshot_id in item.match_snapshot_ids
        )
        if (
            len(sliced_snapshot_ids) != len(set(sliced_snapshot_ids))
            or set(sliced_snapshot_ids) != set(active_snapshot_ids)
        ):
            raise ValueError("Partition slices must cover each active Match Snapshot once.")
        for item in self.partitions:
            snapshot_set = set(item.match_snapshot_ids)
            if item.match_snapshot_ids != tuple(
                snapshot_id
                for snapshot_id in active_snapshot_ids
                if snapshot_id in snapshot_set
            ):
                raise ValueError("Partition Match Snapshot IDs must preserve source order.")
            records = tuple(
                record
                for record in dataset.records
                if record.source_context.match_snapshot_id in snapshot_set
            )
            skipped = tuple(
                value
                for value in dataset.skipped_decisions
                if value.match_snapshot_id in snapshot_set
            )
            statistics_ids = {
                observation_id
                for record in records
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
            unjoined_commentary_ids = {
                evidence_id
                for value in skipped
                for evidence_id in value.commentary_evidence_ids
                if evidence_id in dataset.unjoined_commentary_evidence_ids
            }
            unjoined_response_ids = {
                evidence_id
                for value in skipped
                for evidence_id in (
                    *value.outgoing_response_evidence_ids,
                    *value.incoming_response_evidence_ids,
                )
                if evidence_id in dataset.unjoined_response_evidence_ids
            }
            expected = {
                "record_ids": tuple(value.record_id for value in records),
                "skipped_decision_ids": tuple(
                    value.skipped_decision_id for value in skipped
                ),
                "statistics_observation_ids": tuple(
                    value.statistics_observation_id
                    for value in dataset.player_statistics_observations
                    if value.statistics_observation_id in statistics_ids
                ),
                "strategy_teacher_evidence_ids": tuple(
                    value.strategy_teacher_evidence_id
                    for value in dataset.strategy_teacher_evidences
                    if value.match_snapshot_id in snapshot_set
                ),
                "commentary_evidence_ids": tuple(
                    value.commentary_evidence_id
                    for value in dataset.commentary_evidences
                    if value.match_snapshot_id in snapshot_set
                ),
                "response_evidence_ids": tuple(
                    value.response_evidence_id
                    for value in dataset.response_evidences
                    if value.match_snapshot_id in snapshot_set
                ),
                "unjoined_commentary_evidence_ids": tuple(
                    value
                    for value in dataset.unjoined_commentary_evidence_ids
                    if value in unjoined_commentary_ids
                ),
                "unjoined_response_evidence_ids": tuple(
                    value
                    for value in dataset.unjoined_response_evidence_ids
                    if value in unjoined_response_ids
                ),
            }
            if any(getattr(item, name) != values for name, values in expected.items()):
                raise ValueError("Partition slices must losslessly index their source cohort.")
        from skatmind.learning_dataset_v2_partition_identity import (
            build_learning_dataset_partitioned_view_fingerprint_v1,
        )

        if self.partitioned_view_fingerprint != (
            build_learning_dataset_partitioned_view_fingerprint_v1(self)
        ):
            raise ValueError("partitioned_view_fingerprint must cover the exact view.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_dataset_partitioned_view_version": (
                self.learning_dataset_partitioned_view_version
            ),
            "partitioned_view_fingerprint": self.partitioned_view_fingerprint,
            "source_dataset_fingerprint": self.source_dataset_fingerprint,
            "plan_fingerprint": self.plan_fingerprint,
            "learning_dataset": self.learning_dataset.to_dict(),
            "partitions": [item.to_dict() for item in self.partitions],
        }


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningDatasetPartitionPreparationResultV1:
    learning_dataset_partition_preparation_version: int
    status: str
    unavailable_reason: str | None
    request_fingerprint: str
    plan: LearningDatasetPartitionPlanV1
    partitioned_view: LearningDatasetPartitionedViewV1 | None

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("LearningDatasetPartitionPreparationResultV1 requires its builder.")

    @classmethod
    def _from_validated(cls, **values: Any) -> LearningDatasetPartitionPreparationResultV1:
        value = object.__new__(cls)
        for field_name, field_value in values.items():
            object.__setattr__(value, field_name, field_value)
        value._validate()
        return value

    def _validate(self) -> None:
        _require_version(
            self.learning_dataset_partition_preparation_version,
            LEARNING_DATASET_PARTITION_PREPARATION_VERSION,
            "learning_dataset_partition_preparation_version",
        )
        if self.status not in LEARNING_DATASET_PARTITION_PLAN_STATUSES:
            raise ValueError("status must be complete or unavailable.")
        _require_hash(self.request_fingerprint, "request_fingerprint")
        if type(self.plan) is not LearningDatasetPartitionPlanV1:
            raise ValueError("plan must be an exact LearningDatasetPartitionPlanV1.")
        self.plan._validate()
        if self.status != self.plan.status or self.request_fingerprint != (
            self.plan.request_fingerprint
        ):
            raise ValueError("Preparation Result must reconcile with its exact Plan.")
        if self.status == "complete":
            if self.unavailable_reason is not None or self.partitioned_view is None:
                raise ValueError("A complete Result requires a view and no reason.")
            self.partitioned_view._validate()
            if self.partitioned_view.plan_fingerprint != self.plan.plan_fingerprint:
                raise ValueError("Partitioned View must reference the exact Plan.")
            dataset = self.partitioned_view.learning_dataset
            active_snapshot_ids = tuple(
                snapshot_id
                for snapshot_id in dataset.current_match_snapshot_ids
                if any(
                    record.source_context.match_snapshot_id == snapshot_id
                    for record in dataset.records
                )
                or any(
                    skipped.match_snapshot_id == snapshot_id
                    for skipped in dataset.skipped_decisions
                )
            )
            if tuple(
                item.match_snapshot_id for item in self.plan.assignments
            ) != active_snapshot_ids:
                raise ValueError("Plan assignments must preserve exact active source order.")
            if (
                self.plan.source_current_match_count != dataset.current_match_count
                or self.plan.source_record_count != dataset.record_count
                or self.plan.source_skipped_decision_count
                != dataset.skipped_decision_count
            ):
                raise ValueError("Plan source counts must match the partitioned Dataset.")
            assert self.plan.leakage_audit is not None
            if (
                self.plan.leakage_audit.source_dataset_fingerprint
                != dataset.dataset_fingerprint
                or self.plan.leakage_audit.inactive_current_match_snapshot_ids
                != tuple(
                    snapshot_id
                    for snapshot_id in dataset.current_match_snapshot_ids
                    if snapshot_id not in set(active_snapshot_ids)
                )
            ):
                raise ValueError("Leakage Audit must reference the exact source Dataset.")
            expected_slice_snapshot_ids = {
                partition: tuple(
                    item.match_snapshot_id
                    for item in self.plan.assignments
                    if item.partition == partition
                )
                for partition in LEARNING_DATASET_PARTITIONS
            }
            if any(
                item.match_snapshot_ids != expected_slice_snapshot_ids[item.partition]
                for item in self.partitioned_view.partitions
            ):
                raise ValueError("Partitioned View slices must match the exact Plan assignments.")
            summaries_by_partition = {
                item.partition: item for item in self.plan.partition_summaries
            }
            for partition, snapshot_ids in expected_slice_snapshot_ids.items():
                snapshot_set = set(snapshot_ids)
                records = tuple(
                    item
                    for item in dataset.records
                    if item.source_context.match_snapshot_id in snapshot_set
                )
                skipped = tuple(
                    item
                    for item in dataset.skipped_decisions
                    if item.match_snapshot_id in snapshot_set
                )
                summary = summaries_by_partition[partition]
                if (
                    summary.match_snapshot_count != len(snapshot_ids)
                    or summary.record_count != len(records)
                    or summary.skipped_decision_count != len(skipped)
                    or summary.observed_decision_count != len(records) + len(skipped)
                    or summary.strategy_teacher_evidence_count
                    != sum(
                        item.match_snapshot_id in snapshot_set
                        for item in dataset.strategy_teacher_evidences
                    )
                    or summary.commentary_evidence_count
                    != sum(
                        item.match_snapshot_id in snapshot_set
                        for item in dataset.commentary_evidences
                    )
                    or summary.response_evidence_count
                    != sum(
                        item.match_snapshot_id in snapshot_set
                        for item in dataset.response_evidences
                    )
                ):
                    raise ValueError(
                        "Partition summaries must reconcile with exact source cohorts."
                    )
        elif (
            self.unavailable_reason != self.plan.unavailable_reason
            or self.unavailable_reason is None
            or self.partitioned_view is not None
        ):
            raise ValueError("An unavailable Result requires its Plan reason and no view.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_dataset_partition_preparation_version": (
                self.learning_dataset_partition_preparation_version
            ),
            "status": self.status,
            "unavailable_reason": self.unavailable_reason,
            "request_fingerprint": self.request_fingerprint,
            "plan": self.plan.to_dict(),
            "partitioned_view": (
                None if self.partitioned_view is None else self.partitioned_view.to_dict()
            ),
        }
