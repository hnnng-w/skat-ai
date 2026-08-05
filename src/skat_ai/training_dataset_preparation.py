from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from skat_ai.dataset_partition_audit import (
    DatasetPartitionAudit,
    audit_training_dataset_partitions,
    build_serializable_dataset_partition_audit,
)
from skat_ai.dataset_partition_policy import (
    DATASET_PARTITION_POLICY_MODES,
    DATASET_PARTITION_POLICY_VERSION,
    DatasetPartitionPolicyMode,
)
from skat_ai.historical_decision_snapshot import build_historical_decision_snapshots
from skat_ai.historical_game import (
    HistoricalGameRecord,
    build_historical_game_record,
    build_historical_game_summary,
    build_serializable_historical_record,
)
from skat_ai.training_dataset import (
    TRAINING_DATASET_SCHEMA_VERSION,
    TRAINING_FEATURE_GENERATION_VERSION,
    TRAINING_TARGET,
    TrainingDatasetInput,
    TrainingProvenance,
    build_serializable_training_dataset_input,
    build_serializable_training_provenance,
    build_training_dataset_input,
    build_training_provenance,
    validate_unique_training_record_identities,
)

if TYPE_CHECKING:
    from skat_ai.dataset_partition_plan import CompleteDatasetPartitionPlan

TRAINING_DATASET_PREPARATION_VERSION = 1


@dataclass(frozen=True)
class UnpartitionedTrainingDatasetRecord:
    """One indivisible source record before partition assignment."""

    record_id: str
    provenance: TrainingProvenance
    historical_game: HistoricalGameRecord


@dataclass(frozen=True)
class DatasetPartitionWeights:
    """Explicit positive integer Record-count partition weights."""

    train: int
    validation: int
    test: int

    def __post_init__(self) -> None:
        for field_name, value in (
            ("train", self.train),
            ("validation", self.validation),
            ("test", self.test),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(
                    f"partition_weights.{field_name} must be a positive integer."
                )

    @property
    def total_weight(self) -> int:
        return self.train + self.validation + self.test

    @property
    def total(self) -> int:
        return self.total_weight


@dataclass(frozen=True)
class TrainingDatasetPreparationRequest:
    """One immutable internal request for deterministic split planning."""

    preparation_version: int
    dataset_id: str
    dataset_version: str
    feature_generation_version: int
    target: Literal["actual_card_played"]
    mode: DatasetPartitionPolicyMode
    base_random_seed: int
    partition_weights: DatasetPartitionWeights
    records: tuple[UnpartitionedTrainingDatasetRecord, ...]


@dataclass(frozen=True)
class DatasetPreparationSourceFact:
    """Split-safe facts for one source Record; sample count is diagnostic only."""

    source_index: int
    record_id: str
    historical_game_id: str
    source_identity: tuple[str, str, str] | None
    played_at: str | None
    player_ids: tuple[str, ...]
    sample_count: int
    zero_sample: bool


@dataclass(frozen=True)
class PreparedTrainingDataset:
    """A losslessly materialized version-1 dataset and its reused audit."""

    preparation_version: int
    plan: "CompleteDatasetPartitionPlan"
    training_dataset_input: TrainingDatasetInput
    partition_audit: DatasetPartitionAudit

    @property
    def training_dataset(self) -> TrainingDatasetInput:
        return self.training_dataset_input


def _require_object(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be an object.")
    return value


def _require_exact_fields(
    data: dict[str, Any],
    required_fields: set[str],
    field_name: str,
) -> None:
    missing_fields = sorted(required_fields - data.keys())
    if missing_fields:
        raise ValueError(f"{field_name} is missing required fields: {missing_fields}.")
    unexpected_fields = sorted(data.keys() - required_fields)
    if unexpected_fields:
        raise ValueError(f"{field_name} has unsupported fields: {unexpected_fields}.")


def _require_identifier(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{field_name} must be a non-empty, non-padded string.")
    return value


def _require_version(value: Any, expected: int, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value != expected:
        raise ValueError(f"{field_name} must currently equal {expected}.")
    return expected


def build_dataset_partition_weights(value: Any) -> DatasetPartitionWeights:
    """Builds all three explicit positive integer partition weights."""
    field_name = "training_dataset_preparation.partition_weights"
    data = _require_object(value, field_name)
    _require_exact_fields(data, {"train", "validation", "test"}, field_name)
    return DatasetPartitionWeights(
        train=data["train"],
        validation=data["validation"],
        test=data["test"],
    )


def _build_unpartitioned_record(
    value: Any,
    record_index: int,
) -> UnpartitionedTrainingDatasetRecord:
    record_name = f"training_dataset_preparation.records[{record_index}]"
    data = _require_object(value, record_name)
    _require_exact_fields(
        data,
        {"record_id", "provenance", "historical_game"},
        record_name,
    )
    record_id = _require_identifier(data["record_id"], f"{record_name}.record_id")
    historical_game_data = _require_object(
        data["historical_game"], f"{record_name}.historical_game"
    )
    return UnpartitionedTrainingDatasetRecord(
        record_id=record_id,
        provenance=build_training_provenance(data["provenance"], record_name),
        historical_game=build_historical_game_record(historical_game_data),
    )


def build_training_dataset_preparation_request(
    data: dict[str, Any],
) -> TrainingDatasetPreparationRequest:
    """Builds one strict, non-empty, unpartitioned preparation request."""
    field_name = "training_dataset_preparation"
    data = _require_object(data, field_name)
    _require_exact_fields(
        data,
        {
            "preparation_version",
            "dataset_id",
            "dataset_version",
            "feature_generation_version",
            "target",
            "mode",
            "base_random_seed",
            "partition_weights",
            "records",
        },
        field_name,
    )
    preparation_version = _require_version(
        data["preparation_version"],
        TRAINING_DATASET_PREPARATION_VERSION,
        f"{field_name}.preparation_version",
    )
    feature_generation_version = _require_version(
        data["feature_generation_version"],
        TRAINING_FEATURE_GENERATION_VERSION,
        f"{field_name}.feature_generation_version",
    )
    if data["target"] != TRAINING_TARGET:
        raise ValueError(
            f"{field_name}.target must currently equal '{TRAINING_TARGET}'."
        )
    mode = data["mode"]
    if mode not in DATASET_PARTITION_POLICY_MODES:
        raise ValueError(
            f"{field_name}.mode must be one of "
            f"{list(DATASET_PARTITION_POLICY_MODES)}."
        )
    base_random_seed = data["base_random_seed"]
    if isinstance(base_random_seed, bool) or not isinstance(base_random_seed, int):
        raise ValueError(
            f"{field_name}.base_random_seed must be an integer and must not be a boolean."
        )
    raw_records = data["records"]
    if not isinstance(raw_records, list) or not raw_records:
        raise ValueError(f"{field_name}.records must be a non-empty array.")
    records = tuple(
        _build_unpartitioned_record(raw_record, record_index)
        for record_index, raw_record in enumerate(raw_records)
    )
    validate_unique_training_record_identities(records)
    return TrainingDatasetPreparationRequest(
        preparation_version=preparation_version,
        dataset_id=_require_identifier(data["dataset_id"], f"{field_name}.dataset_id"),
        dataset_version=_require_identifier(
            data["dataset_version"], f"{field_name}.dataset_version"
        ),
        feature_generation_version=feature_generation_version,
        target=TRAINING_TARGET,
        mode=mode,
        base_random_seed=base_random_seed,
        partition_weights=build_dataset_partition_weights(
            data["partition_weights"]
        ),
        records=records,
    )


def build_dataset_preparation_source_facts(
    request: TrainingDatasetPreparationRequest,
) -> tuple[DatasetPreparationSourceFact, ...]:
    """Replays each Record once and counts snapshots without generating samples."""
    facts = []
    for source_index, record in enumerate(request.records):
        historical_summary = build_historical_game_summary(record.historical_game)
        snapshots = build_historical_decision_snapshots(historical_summary)
        sample_count = snapshots.snapshot_count
        if sample_count != snapshots.cardinality.expected_training_sample_count:
            raise ValueError(
                f"Preparation record '{record.record_id}' snapshot count does not "
                "match the validated play prefix."
            )
        provenance = record.provenance
        source_identity = (
            (
                provenance.source_type,
                provenance.source_name,
                provenance.source_record_id,
            )
            if provenance.source_record_id is not None
            else None
        )
        facts.append(
            DatasetPreparationSourceFact(
                source_index=source_index,
                record_id=record.record_id,
                historical_game_id=record.historical_game.game_id,
                source_identity=source_identity,
                played_at=record.historical_game.played_at,
                player_ids=tuple(
                    sorted(
                        player.player_id
                        for player in record.historical_game.players
                    )
                ),
                sample_count=sample_count,
                zero_sample=sample_count == 0,
            )
        )
    return tuple(facts)


def build_serializable_dataset_partition_weights(
    weights: DatasetPartitionWeights,
) -> dict[str, int]:
    return {
        "train": weights.train,
        "validation": weights.validation,
        "test": weights.test,
    }


def build_serializable_unpartitioned_training_record(
    record: UnpartitionedTrainingDatasetRecord,
) -> dict[str, Any]:
    return {
        "record_id": record.record_id,
        "provenance": build_serializable_training_provenance(record.provenance),
        "historical_game": build_serializable_historical_record(
            record.historical_game
        ),
    }


def build_serializable_training_dataset_preparation_request(
    request: TrainingDatasetPreparationRequest,
) -> dict[str, Any]:
    return {
        "preparation_version": request.preparation_version,
        "dataset_id": request.dataset_id,
        "dataset_version": request.dataset_version,
        "feature_generation_version": request.feature_generation_version,
        "target": request.target,
        "mode": request.mode,
        "base_random_seed": request.base_random_seed,
        "partition_weights": build_serializable_dataset_partition_weights(
            request.partition_weights
        ),
        "records": [
            build_serializable_unpartitioned_training_record(record)
            for record in request.records
        ],
    }


def build_serializable_dataset_preparation_source_fact(
    fact: DatasetPreparationSourceFact,
) -> dict[str, Any]:
    return {
        "source_index": fact.source_index,
        "record_id": fact.record_id,
        "historical_game_id": fact.historical_game_id,
        "source_identity": (
            {
                "source_type": fact.source_identity[0],
                "source_name": fact.source_identity[1],
                "source_record_id": fact.source_identity[2],
            }
            if fact.source_identity is not None
            else None
        ),
        "played_at": fact.played_at,
        "player_ids": list(fact.player_ids),
        "sample_count": fact.sample_count,
        "zero_sample": fact.zero_sample,
    }


def _build_materialized_training_dataset(
    request: TrainingDatasetPreparationRequest,
    assignments_by_record_id: dict[str, str],
) -> TrainingDatasetInput:
    return build_training_dataset_input(
        {
            "schema_version": TRAINING_DATASET_SCHEMA_VERSION,
            "dataset_id": request.dataset_id,
            "dataset_version": request.dataset_version,
            "feature_generation_version": request.feature_generation_version,
            "target": request.target,
            "partition_policy": {
                "policy_version": DATASET_PARTITION_POLICY_VERSION,
                "mode": request.mode,
            },
            "records": [
                {
                    **build_serializable_unpartitioned_training_record(record),
                    "partition": assignments_by_record_id[record.record_id],
                }
                for record in request.records
            ],
        }
    )


def materialize_prepared_training_dataset(
    request: TrainingDatasetPreparationRequest,
    plan: Any,
) -> PreparedTrainingDataset:
    """Adds only validated partitions and reuses version-1 dataset validation."""
    from skat_ai.dataset_partition_plan import (
        TEMPORAL_KNOWN_OPPONENT_ALGORITHM,
        validate_dataset_partition_plan,
    )

    validate_dataset_partition_plan(request, plan)
    if plan.status != "complete":
        raise ValueError("Only a complete dataset partition plan may be materialized.")
    assignments_by_record_id = {
        assignment.record_id: assignment.partition
        for assignment in plan.assignments
    }
    dataset = _build_materialized_training_dataset(
        request, assignments_by_record_id
    )
    if (
        dataset.dataset_id != request.dataset_id
        or dataset.dataset_version != request.dataset_version
        or dataset.feature_generation_version
        != request.feature_generation_version
        or dataset.target != request.target
    ):
        raise ValueError(
            "Materialized Training Dataset metadata does not match the request."
        )
    for source_record, materialized_record in zip(
        request.records,
        dataset.records,
        strict=True,
    ):
        if (
            materialized_record.record_id != source_record.record_id
            or materialized_record.provenance != source_record.provenance
            or materialized_record.historical_game != source_record.historical_game
        ):
            raise ValueError(
                f"Materialized record '{source_record.record_id}' does not "
                "losslessly preserve its source Record."
            )
    audit = audit_training_dataset_partitions(dataset, request.mode)
    serialized_plan_audit = build_serializable_dataset_partition_audit(
        plan.partition_audit
    )
    serialized_materialized_audit = build_serializable_dataset_partition_audit(
        audit
    )
    if (
        serialized_materialized_audit != serialized_plan_audit
        and plan.algorithm == TEMPORAL_KNOWN_OPPONENT_ALGORITHM
    ):
        serialized_materialized_audit = build_serializable_dataset_partition_audit(
            audit_training_dataset_partitions(
                dataset,
                request.mode,
                canonical_source_order=True,
            )
        )
    if serialized_materialized_audit != serialized_plan_audit:
        raise ValueError(
            "Materialized dataset partition audit does not match the validated plan."
        )
    return PreparedTrainingDataset(
        preparation_version=request.preparation_version,
        plan=plan,
        training_dataset_input=dataset,
        partition_audit=plan.partition_audit,
    )


def build_serializable_prepared_training_dataset(
    prepared: PreparedTrainingDataset,
) -> dict[str, Any]:
    """Serializes retained plan provenance and the existing materialized input."""
    from skat_ai.dataset_partition_plan import (
        build_serializable_dataset_partition_plan,
    )

    return {
        "preparation_version": prepared.preparation_version,
        "plan": build_serializable_dataset_partition_plan(prepared.plan),
        "training_dataset_input": build_serializable_training_dataset_input(
            prepared.training_dataset_input
        ),
        "partition_audit": build_serializable_dataset_partition_audit(
            prepared.partition_audit
        ),
    }
