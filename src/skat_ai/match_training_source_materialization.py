from dataclasses import dataclass
from typing import Any

from skat_ai.match_historical_materialization import (
    MATCH_HISTORICAL_MATERIALIZATION_UNAVAILABLE_REASONS,
    MATCH_MATERIALIZATION_ARTIFACT_STATUSES,
    MatchHistoricalGameMaterializationV1,
)
from skat_ai.training_dataset import (
    build_training_provenance,
    validate_unique_training_record_identities,
)
from skat_ai.training_dataset_preparation import (
    UnpartitionedTrainingDatasetRecord,
    build_serializable_unpartitioned_training_record,
)

MATCH_TRAINING_SOURCE_COLLECTION_VERSION = 1
MATCH_TRAINING_SOURCE_POLICY = "existing_unpartitioned_record_from_materialized_historical_game"


@dataclass(frozen=True, slots=True, kw_only=True)
class MatchTrainingSourceRecordMaterializationV1:
    """One unpartitioned Training source Record or mirrored unavailability."""

    status: str
    match_position: int
    record_id: str
    unavailable_reason: str | None
    record: UnpartitionedTrainingDatasetRecord | None

    def __post_init__(self) -> None:
        if self.status not in MATCH_MATERIALIZATION_ARTIFACT_STATUSES:
            raise ValueError(
                f"status must be one of {list(MATCH_MATERIALIZATION_ARTIFACT_STATUSES)}."
            )
        if type(self.match_position) is not int or not 1 <= self.match_position <= 36:
            raise ValueError("match_position must be an integer from 1 through 36.")
        if self.status == "available":
            if (
                self.unavailable_reason is not None
                or type(self.record) is not UnpartitionedTrainingDatasetRecord
                or self.record.record_id != self.record_id
            ):
                raise ValueError("Available Training materialization requires one Record.")
        elif (
            self.record is not None
            or self.unavailable_reason not in MATCH_HISTORICAL_MATERIALIZATION_UNAVAILABLE_REASONS
        ):
            raise ValueError("Unavailable Training materialization requires one mirrored reason.")
        expected_record_id = self.record_id.rsplit("-", maxsplit=1)[-1]
        if expected_record_id != f"{self.match_position:02d}":
            raise ValueError("record_id must end with the zero-padded Match position.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "match_position": self.match_position,
            "record_id": self.record_id,
            "unavailable_reason": self.unavailable_reason,
            "record": (
                None
                if self.record is None
                else build_serializable_unpartitioned_training_record(self.record)
            ),
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class MatchTrainingSourceCollectionV1:
    """Available unpartitioned source Records in Match-position order."""

    match_training_source_collection_version: int = MATCH_TRAINING_SOURCE_COLLECTION_VERSION
    match_id: str
    available_record_count: int
    unavailable_record_count: int
    records: tuple[UnpartitionedTrainingDatasetRecord, ...]
    unavailable_positions: tuple[int, ...]

    def __post_init__(self) -> None:
        if (
            type(self.match_training_source_collection_version) is not int
            or self.match_training_source_collection_version
            != MATCH_TRAINING_SOURCE_COLLECTION_VERSION
        ):
            raise ValueError(
                "match_training_source_collection_version must equal "
                f"{MATCH_TRAINING_SOURCE_COLLECTION_VERSION}."
            )
        for field_name in ("available_record_count", "unavailable_record_count"):
            value = getattr(self, field_name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer.")
        if not isinstance(self.records, (list, tuple)) or any(
            type(record) is not UnpartitionedTrainingDatasetRecord for record in self.records
        ):
            raise ValueError("records must contain unpartitioned Training Records.")
        if not isinstance(self.unavailable_positions, (list, tuple)):
            raise ValueError("unavailable_positions must be an ordered array.")
        object.__setattr__(self, "records", tuple(self.records))
        object.__setattr__(self, "unavailable_positions", tuple(self.unavailable_positions))
        if self.available_record_count != len(self.records):
            raise ValueError("available_record_count must equal records length.")
        if self.unavailable_record_count != len(self.unavailable_positions):
            raise ValueError("unavailable_record_count must equal unavailable_positions length.")
        if self.available_record_count + self.unavailable_record_count != 36:
            raise ValueError("Available and unavailable positions must total 36.")
        if tuple(sorted(self.unavailable_positions)) != self.unavailable_positions:
            raise ValueError("unavailable_positions must use Match-position order.")
        if len(set(self.unavailable_positions)) != len(self.unavailable_positions) or any(
            type(position) is not int or not 1 <= position <= 36
            for position in self.unavailable_positions
        ):
            raise ValueError("unavailable_positions must contain unique positions 1 through 36.")
        available_positions = tuple(
            position for position in range(1, 37) if position not in self.unavailable_positions
        )
        expected_record_ids = tuple(
            f"{self.match_id}-record-{position:02d}" for position in available_positions
        )
        if tuple(record.record_id for record in self.records) != expected_record_ids:
            raise ValueError("records must use exact Match IDs in available Match-position order.")
        validate_unique_training_record_identities(self.records)

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_training_source_collection_version": (
                self.match_training_source_collection_version
            ),
            "match_id": self.match_id,
            "available_record_count": self.available_record_count,
            "unavailable_record_count": self.unavailable_record_count,
            "records": [
                build_serializable_unpartitioned_training_record(record) for record in self.records
            ],
            "unavailable_positions": list(self.unavailable_positions),
        }


def materialize_match_training_source_record_v1(
    historical: MatchHistoricalGameMaterializationV1,
    *,
    source_title: str,
) -> MatchTrainingSourceRecordMaterializationV1:
    """Builds one validated unpartitioned Record from strict Historical evidence."""
    record_id = f"{historical.match_id}-record-{historical.match_position:02d}"
    if historical.historical_game is None:
        return MatchTrainingSourceRecordMaterializationV1(
            status="unavailable",
            match_position=historical.match_position,
            record_id=record_id,
            unavailable_reason=historical.unavailable_reason,
            record=None,
        )
    provenance = build_training_provenance(
        {
            "source_type": "manual_entry",
            "source_name": source_title,
            "source_record_id": historical.historical_game.game_id,
            "collected_at": None,
            "notes": None,
        },
        f"Match position {historical.match_position} Training source",
    )
    record = UnpartitionedTrainingDatasetRecord(
        record_id=record_id,
        provenance=provenance,
        historical_game=historical.historical_game,
    )
    validate_unique_training_record_identities((record,))
    return MatchTrainingSourceRecordMaterializationV1(
        status="available",
        match_position=historical.match_position,
        record_id=record_id,
        unavailable_reason=None,
        record=record,
    )


def build_match_training_source_collection_v1(
    *,
    match_id: str,
    materializations: tuple[MatchTrainingSourceRecordMaterializationV1, ...],
) -> MatchTrainingSourceCollectionV1:
    """Collects only available Records while retaining unavailable positions."""
    if tuple(item.match_position for item in materializations) != tuple(range(1, 37)):
        raise ValueError("materializations must contain exact Match positions 1 through 36.")
    if any(
        item.record_id != f"{match_id}-record-{item.match_position:02d}"
        for item in materializations
    ):
        raise ValueError("materializations must use exact collection Record IDs.")
    records = tuple(item.record for item in materializations if item.record is not None)
    unavailable_positions = tuple(
        item.match_position for item in materializations if item.record is None
    )
    return MatchTrainingSourceCollectionV1(
        match_id=match_id,
        available_record_count=len(records),
        unavailable_record_count=len(unavailable_positions),
        records=records,
        unavailable_positions=unavailable_positions,
    )
