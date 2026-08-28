from dataclasses import dataclass
from typing import Any

from skatmind.fixed_three_player_list_rotation import (
    FIXED_THREE_PLAYER_LIST_TABLE_PLACES,
)
from skatmind.opponent_statistics import (
    OPPONENT_STATISTICS_SCHEMA_VERSION,
    OpponentStatisticsInput,
    OpponentStatisticsRecord,
    build_opponent_statistics_input,
    build_serializable_opponent_statistics_input,
)
from skatmind.performance_rating import (
    validate_stable_list_entry_identifier,
    validate_stable_list_player_label,
)
from skatmind.rfc3339 import parse_rfc3339_datetime

MATCH_PLAYER_STATISTICS_SNAPSHOT_VERSION = 1

_RELATIVE_PLAYER_IDS = frozenset({"me", "left", "right"})


def _validate_match_player_id(value: object, field_name: str) -> None:
    validate_stable_list_entry_identifier(value, field_name)
    if value in _RELATIVE_PLAYER_IDS:
        raise ValueError(f"{field_name} must be a stable, non-relative Player ID.")


def _serialize_statistics_record(record: OpponentStatisticsRecord) -> dict[str, Any]:
    document = build_serializable_opponent_statistics_input(
        OpponentStatisticsInput(
            schema_version=OPPONENT_STATISTICS_SCHEMA_VERSION,
            records=(record,),
        )
    )
    return document["opponent_statistics_input"]["records"][0]


def _copy_statistics_record(record: object) -> OpponentStatisticsRecord:
    if not isinstance(record, OpponentStatisticsRecord):
        raise ValueError("statistics_record must be an OpponentStatisticsRecord.")
    return build_opponent_statistics_input(
        {
            "schema_version": OPPONENT_STATISTICS_SCHEMA_VERSION,
            "records": [_serialize_statistics_record(record)],
        }
    ).records[0]


@dataclass(frozen=True, slots=True, kw_only=True)
class MatchPlayerStatisticsSnapshotV1:
    """One immutable observation of an existing Player statistics record."""

    match_player_statistics_snapshot_version: int = (
        MATCH_PLAYER_STATISTICS_SNAPSHOT_VERSION
    )
    snapshot_id: str
    observed_at: str
    statistics_record: OpponentStatisticsRecord

    def __post_init__(self) -> None:
        if (
            type(self.match_player_statistics_snapshot_version) is not int
            or self.match_player_statistics_snapshot_version
            != MATCH_PLAYER_STATISTICS_SNAPSHOT_VERSION
        ):
            raise ValueError(
                "match_player_statistics_snapshot_version must equal "
                f"{MATCH_PLAYER_STATISTICS_SNAPSHOT_VERSION}."
            )
        validate_stable_list_entry_identifier(self.snapshot_id, "snapshot_id")
        validate_stable_list_entry_identifier(self.observed_at, "observed_at")
        observed_instant = parse_rfc3339_datetime(self.observed_at, "observed_at")
        statistics_record = _copy_statistics_record(self.statistics_record)
        captured_instant = parse_rfc3339_datetime(
            statistics_record.source.captured_at,
            "statistics_record.source.captured_at",
        )
        if observed_instant != captured_instant:
            raise ValueError(
                "observed_at and statistics_record.source.captured_at must represent "
                "the same instant."
            )
        object.__setattr__(self, "statistics_record", statistics_record)

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_player_statistics_snapshot_version": (
                self.match_player_statistics_snapshot_version
            ),
            "snapshot_id": self.snapshot_id,
            "observed_at": self.observed_at,
            "statistics_record": _serialize_statistics_record(self.statistics_record),
        }


def _copy_statistics_snapshot(
    value: MatchPlayerStatisticsSnapshotV1 | None,
) -> MatchPlayerStatisticsSnapshotV1 | None:
    if value is None:
        return None
    if not isinstance(value, MatchPlayerStatisticsSnapshotV1):
        raise ValueError(
            "statistics_snapshot must be null or MatchPlayerStatisticsSnapshotV1."
        )
    return MatchPlayerStatisticsSnapshotV1(
        match_player_statistics_snapshot_version=(
            value.match_player_statistics_snapshot_version
        ),
        snapshot_id=value.snapshot_id,
        observed_at=value.observed_at,
        statistics_record=value.statistics_record,
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class MatchParticipantV1:
    """One stable Match Player at one fixed table place."""

    player_id: str
    player_label: str | None
    platform_player_id: str | None
    table_place: str
    statistics_snapshot: MatchPlayerStatisticsSnapshotV1 | None

    def __post_init__(self) -> None:
        _validate_match_player_id(self.player_id, "player_id")
        if self.player_label is not None:
            validate_stable_list_player_label(self.player_label, "player_label")
        if self.platform_player_id is not None:
            validate_stable_list_entry_identifier(
                self.platform_player_id,
                "platform_player_id",
            )
        if self.table_place not in FIXED_THREE_PLAYER_LIST_TABLE_PLACES:
            raise ValueError(
                "table_place must be one of "
                f"{list(FIXED_THREE_PLAYER_LIST_TABLE_PLACES)}."
            )

        snapshot = _copy_statistics_snapshot(self.statistics_snapshot)
        if snapshot is not None:
            record = snapshot.statistics_record
            if record.player_id != self.player_id:
                raise ValueError(
                    "statistics_snapshot Player identity must equal participant player_id."
                )
            if (
                self.player_label is not None
                and record.player_label is not None
                and self.player_label != record.player_label
            ):
                raise ValueError(
                    "Participant and statistics snapshot contain conflicting non-null "
                    "Player labels."
                )
        object.__setattr__(self, "statistics_snapshot", snapshot)

    def to_dict(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "player_label": self.player_label,
            "platform_player_id": self.platform_player_id,
            "table_place": self.table_place,
            "statistics_snapshot": (
                None
                if self.statistics_snapshot is None
                else self.statistics_snapshot.to_dict()
            ),
        }


def copy_match_participant_v1(value: MatchParticipantV1) -> MatchParticipantV1:
    """Returns a validated defensive copy of one immutable Match participant."""
    if not isinstance(value, MatchParticipantV1):
        raise ValueError("participants must contain only MatchParticipantV1 values.")
    return MatchParticipantV1(
        player_id=value.player_id,
        player_label=value.player_label,
        platform_player_id=value.platform_player_id,
        table_place=value.table_place,
        statistics_snapshot=value.statistics_snapshot,
    )
