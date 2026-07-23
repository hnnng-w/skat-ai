from dataclasses import dataclass
from typing import Any, Literal

from skat_ai.dataset_partition_policy import (
    DatasetPartitionPolicy,
    build_dataset_partition_policy,
    build_serializable_dataset_partition_policy,
    format_unseen_player_policy_violation,
    get_cross_partition_player_memberships,
)
from skat_ai.historical_decision_snapshot import (
    HistoricalDecisionSnapshot,
    build_historical_decision_snapshots,
)
from skat_ai.historical_game import (
    HistoricalGameRecord,
    build_historical_game_record,
    build_historical_game_summary,
    build_serializable_historical_record,
)
from skat_ai.rfc3339 import parse_rfc3339_datetime
from skat_ai.training_feature_view import build_training_feature_view

TRAINING_DATASET_SCHEMA_VERSION = 1
TRAINING_FEATURE_GENERATION_VERSION = 1
TRAINING_TARGET = "actual_card_played"
TRAINING_PARTITIONS = ("train", "validation", "test")
TRAINING_SOURCE_TYPES = (
    "online_platform",
    "manual_entry",
    "imported_file",
    "synthetic",
    "other",
)
SAMPLES_PER_TRAINING_RECORD = 30

TrainingPartition = Literal["train", "validation", "test"]
TrainingSourceType = Literal[
    "online_platform",
    "manual_entry",
    "imported_file",
    "synthetic",
    "other",
]


@dataclass(frozen=True)
class TrainingProvenance:
    """Stable source metadata that remains outside model-facing features."""

    source_type: TrainingSourceType
    source_name: str
    source_record_id: str | None
    collected_at: str | None
    notes: str | None


@dataclass(frozen=True)
class TrainingDatasetRecord:
    """One partitioned historical game and its source provenance."""

    record_id: str
    partition: TrainingPartition
    provenance: TrainingProvenance
    historical_game: HistoricalGameRecord


@dataclass(frozen=True)
class TrainingDatasetInput:
    """One validated version-1 training or evaluation dataset input."""

    schema_version: int
    dataset_id: str
    dataset_version: str
    feature_generation_version: int
    target: Literal["actual_card_played"]
    partition_policy: DatasetPartitionPolicy | None
    records: tuple[TrainingDatasetRecord, ...]


def _require_object(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be an object.")
    return value


def _require_exact_fields(
    data: dict[str, Any],
    required_fields: set[str],
    optional_fields: set[str],
    field_name: str,
) -> None:
    missing_fields = sorted(required_fields - data.keys())
    if missing_fields:
        raise ValueError(f"{field_name} is missing required fields: {missing_fields}.")
    unexpected_fields = sorted(data.keys() - required_fields - optional_fields)
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


def _build_provenance(value: Any, record_name: str) -> TrainingProvenance:
    field_name = f"{record_name}.provenance"
    data = _require_object(value, field_name)
    _require_exact_fields(
        data,
        required_fields={"source_type", "source_name"},
        optional_fields={"source_record_id", "collected_at", "notes"},
        field_name=field_name,
    )
    source_type = data["source_type"]
    if source_type not in TRAINING_SOURCE_TYPES:
        raise ValueError(
            f"{field_name}.source_type must be one of {list(TRAINING_SOURCE_TYPES)}."
        )
    source_name = _require_identifier(data["source_name"], f"{field_name}.source_name")
    source_record_id = data.get("source_record_id")
    if source_record_id is not None:
        source_record_id = _require_identifier(
            source_record_id, f"{field_name}.source_record_id"
        )
    collected_at = data.get("collected_at")
    if collected_at is not None:
        collected_at = _require_identifier(collected_at, f"{field_name}.collected_at")
        parse_rfc3339_datetime(collected_at, f"{field_name}.collected_at")
    notes = data.get("notes")
    if notes is not None:
        notes = _require_identifier(notes, f"{field_name}.notes")
    return TrainingProvenance(
        source_type=source_type,
        source_name=source_name,
        source_record_id=source_record_id,
        collected_at=collected_at,
        notes=notes,
    )


def _build_training_record(value: Any, record_index: int) -> TrainingDatasetRecord:
    record_name = f"training_dataset_input.records[{record_index}]"
    data = _require_object(value, record_name)
    _require_exact_fields(
        data,
        required_fields={"record_id", "partition", "provenance", "historical_game"},
        optional_fields=set(),
        field_name=record_name,
    )
    record_id = _require_identifier(data["record_id"], f"{record_name}.record_id")
    partition = data["partition"]
    if partition not in TRAINING_PARTITIONS:
        raise ValueError(
            f"{record_name}.partition must be one of {list(TRAINING_PARTITIONS)}."
        )
    provenance = _build_provenance(data["provenance"], record_name)
    historical_game_data = _require_object(
        data["historical_game"], f"{record_name}.historical_game"
    )
    return TrainingDatasetRecord(
        record_id=record_id,
        partition=partition,
        provenance=provenance,
        historical_game=build_historical_game_record(historical_game_data),
    )


def _validate_unique_record_identities(
    records: tuple[TrainingDatasetRecord, ...],
) -> None:
    record_partitions: dict[str, str] = {}
    game_partitions: dict[str, str] = {}
    source_partitions: dict[tuple[str, str, str], str] = {}
    for record in records:
        if record.record_id in record_partitions:
            raise ValueError(
                f"Duplicate training record_id '{record.record_id}' is not allowed."
            )
        record_partitions[record.record_id] = record.partition

        game_id = record.historical_game.game_id
        if game_id in game_partitions:
            previous_partition = game_partitions[game_id]
            if previous_partition != record.partition:
                raise ValueError(
                    f"Historical game_id '{game_id}' appears in both "
                    f"'{previous_partition}' and '{record.partition}' partitions."
                )
            raise ValueError(f"Duplicate historical game_id '{game_id}' is not allowed.")
        game_partitions[game_id] = record.partition

        provenance = record.provenance
        if provenance.source_record_id is None:
            continue
        source_identity = (
            provenance.source_type,
            provenance.source_name,
            provenance.source_record_id,
        )
        if source_identity in source_partitions:
            previous_partition = source_partitions[source_identity]
            if previous_partition != record.partition:
                raise ValueError(
                    f"Source record {source_identity!r} appears in both "
                    f"'{previous_partition}' and '{record.partition}' partitions."
                )
            raise ValueError(f"Duplicate source record {source_identity!r} is not allowed.")
        source_partitions[source_identity] = record.partition


def build_training_dataset_input(data: dict[str, Any]) -> TrainingDatasetInput:
    """Builds and validates one versioned training-dataset input object."""
    _require_exact_fields(
        data,
        required_fields={
            "schema_version",
            "dataset_id",
            "dataset_version",
            "feature_generation_version",
            "target",
            "records",
        },
        optional_fields={"partition_policy"},
        field_name="training_dataset_input",
    )
    schema_version = _require_version(
        data["schema_version"],
        TRAINING_DATASET_SCHEMA_VERSION,
        "training_dataset_input.schema_version",
    )
    dataset_id = _require_identifier(
        data["dataset_id"], "training_dataset_input.dataset_id"
    )
    dataset_version = _require_identifier(
        data["dataset_version"], "training_dataset_input.dataset_version"
    )
    feature_generation_version = _require_version(
        data["feature_generation_version"],
        TRAINING_FEATURE_GENERATION_VERSION,
        "training_dataset_input.feature_generation_version",
    )
    if data["target"] != TRAINING_TARGET:
        raise ValueError(
            f"training_dataset_input.target must currently equal '{TRAINING_TARGET}'."
        )
    raw_records = data["records"]
    if not isinstance(raw_records, list) or not raw_records:
        raise ValueError("training_dataset_input.records must be a non-empty array.")
    records = tuple(
        _build_training_record(raw_record, record_index)
        for record_index, raw_record in enumerate(raw_records)
    )
    _validate_unique_record_identities(records)
    partition_policy = (
        build_dataset_partition_policy(data["partition_policy"])
        if "partition_policy" in data
        else None
    )
    if partition_policy is not None and partition_policy.mode == "unseen_player":
        violations = get_cross_partition_player_memberships(records)
        if violations:
            raise ValueError(format_unseen_player_policy_violation(violations))
    return TrainingDatasetInput(
        schema_version=schema_version,
        dataset_id=dataset_id,
        dataset_version=dataset_version,
        feature_generation_version=feature_generation_version,
        target=TRAINING_TARGET,
        partition_policy=partition_policy,
        records=records,
    )


def build_serializable_training_provenance(
    provenance: TrainingProvenance,
) -> dict[str, str]:
    """Preserves supplied provenance fields in canonical input order."""
    result = {
        "source_type": provenance.source_type,
        "source_name": provenance.source_name,
    }
    if provenance.source_record_id is not None:
        result["source_record_id"] = provenance.source_record_id
    if provenance.collected_at is not None:
        result["collected_at"] = provenance.collected_at
    if provenance.notes is not None:
        result["notes"] = provenance.notes
    return result


def build_serializable_training_dataset_input(
    dataset: TrainingDatasetInput,
) -> dict[str, Any]:
    """Builds the canonical training-dataset input representation."""
    result = {
        "schema_version": dataset.schema_version,
        "dataset_id": dataset.dataset_id,
        "dataset_version": dataset.dataset_version,
        "feature_generation_version": dataset.feature_generation_version,
        "target": dataset.target,
    }
    if dataset.partition_policy is not None:
        result["partition_policy"] = build_serializable_dataset_partition_policy(
            dataset.partition_policy
        )
    result["records"] = [
        {
            "record_id": record.record_id,
            "partition": record.partition,
            "provenance": build_serializable_training_provenance(record.provenance),
            "historical_game": build_serializable_historical_record(
                record.historical_game
            ),
        }
        for record in dataset.records
    ]
    return result


def _build_sample(
    dataset: TrainingDatasetInput,
    record: TrainingDatasetRecord,
    snapshot: HistoricalDecisionSnapshot,
) -> dict[str, Any]:
    actual_card = snapshot.actual_card_played
    if actual_card not in snapshot.visible_state.own_hand:
        raise ValueError(
            f"Training sample '{record.record_id}:{snapshot.decision_index}' label "
            "card is not in the pre-play own hand."
        )
    if actual_card not in snapshot.visible_state.legal_cards:
        raise ValueError(
            f"Training sample '{record.record_id}:{snapshot.decision_index}' label "
            "card is not legal."
        )
    if actual_card in {play.card for play in snapshot.visible_state.current_trick}:
        raise ValueError(
            f"Training sample '{record.record_id}:{snapshot.decision_index}' label "
            "card already appears in the current trick."
        )
    result = {
        "sample_id": f"{record.record_id}:{snapshot.decision_index}",
        "metadata": {
            "dataset_id": dataset.dataset_id,
            "dataset_version": dataset.dataset_version,
            "record_id": record.record_id,
            "source_game_id": snapshot.source_game_id,
            "partition": record.partition,
            "decision_index": snapshot.decision_index,
            "trick_number": snapshot.trick_number,
            "play_index": snapshot.play_index,
            "acting_player_id": snapshot.acting_player_id,
            "acting_seat": snapshot.acting_seat,
            "acting_side": snapshot.acting_side,
            "provenance": build_serializable_training_provenance(record.provenance),
        },
        "features": build_training_feature_view(snapshot),
        "label": {
            "target": TRAINING_TARGET,
            "card": actual_card,
        },
    }
    if snapshot.source_played_at is not None:
        result["metadata"]["source_played_at"] = snapshot.source_played_at
    return result


def build_training_dataset_summary(
    dataset: TrainingDatasetInput,
) -> dict[str, Any]:
    """Replays records once and builds deterministic information-safe samples."""
    serialized_records = []
    partition_counts = {
        partition: {"record_count": 0, "sample_count": 0}
        for partition in TRAINING_PARTITIONS
    }
    sample_ids: set[str] = set()
    for record in dataset.records:
        historical_summary = build_historical_game_summary(record.historical_game)
        snapshots = build_historical_decision_snapshots(historical_summary)
        if snapshots.snapshot_count != SAMPLES_PER_TRAINING_RECORD:
            raise ValueError(
                f"Training record '{record.record_id}' must produce exactly "
                f"{SAMPLES_PER_TRAINING_RECORD} samples."
            )
        samples = [
            _build_sample(dataset, record, snapshot)
            for snapshot in snapshots.snapshots
        ]
        record_sample_ids = [sample["sample_id"] for sample in samples]
        if len(record_sample_ids) != len(set(record_sample_ids)):
            raise ValueError(
                f"Training record '{record.record_id}' produced duplicate sample IDs."
            )
        if sample_ids.intersection(record_sample_ids):
            raise ValueError("Training dataset produced duplicate sample IDs.")
        sample_ids.update(record_sample_ids)
        serialized_records.append(
            {
                "record_id": record.record_id,
                "partition": record.partition,
                "provenance": build_serializable_training_provenance(record.provenance),
                "source_game_id": record.historical_game.game_id,
                "historical_game": build_serializable_historical_record(
                    record.historical_game
                ),
                "sample_count": len(samples),
                "samples": samples,
            }
        )
        if record.historical_game.played_at is not None:
            serialized_records[-1]["source_played_at"] = record.historical_game.played_at
        partition_counts[record.partition]["record_count"] += 1
        partition_counts[record.partition]["sample_count"] += len(samples)

    record_count = len(serialized_records)
    sample_count = sum(record["sample_count"] for record in serialized_records)
    if record_count != sum(
        counts["record_count"] for counts in partition_counts.values()
    ):
        raise ValueError("Training dataset partition record counts do not reconcile.")
    if sample_count != sum(
        counts["sample_count"] for counts in partition_counts.values()
    ):
        raise ValueError("Training dataset partition sample counts do not reconcile.")
    if sample_count != record_count * SAMPLES_PER_TRAINING_RECORD:
        raise ValueError("Training dataset total sample count does not reconcile.")

    result = {
        "schema_version": dataset.schema_version,
        "dataset_id": dataset.dataset_id,
        "dataset_version": dataset.dataset_version,
        "feature_generation_version": dataset.feature_generation_version,
        "target": dataset.target,
        "record_count": record_count,
        "sample_count": sample_count,
        "partition_counts": partition_counts,
        "records": serialized_records,
    }
    if dataset.partition_policy is not None:
        result["partition_policy"] = build_serializable_dataset_partition_policy(
            dataset.partition_policy
        )
    return result
