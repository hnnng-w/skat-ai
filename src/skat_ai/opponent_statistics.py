import math
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from skat_ai.player_profile import PlayerProfile

OPPONENT_STATISTICS_SCHEMA_VERSION = 1
PERCENTAGE_SUM_TOLERANCE_POINTS = 2.0
OPPONENT_STATISTICS_SOURCE_TYPES = ("online_platform", "manual_entry")

OpponentStatisticsSourceType = Literal["online_platform", "manual_entry"]

_RFC_3339_DATE_TIME = re.compile(
    r"^\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[Zz]|[+-]\d{2}:\d{2})$"
)
_STATISTIC_FIELDS = (
    "solo_games_played_percent",
    "solo_games_won_percent",
    "solo_hand_percent",
    "suit_games_percent",
    "grand_games_percent",
    "null_games_percent",
    "defender_games_played_percent",
    "defender_games_won_percent",
)
_DECLARER_DEPENDENT_FIELDS = (
    "solo_games_won_percent",
    "solo_hand_percent",
    "suit_games_percent",
    "grand_games_percent",
    "null_games_percent",
)


@dataclass(frozen=True)
class OpponentStatisticsSource:
    """Required provenance for one external statistics capture."""

    source_type: OpponentStatisticsSourceType
    source_name: str
    source_player_id: str | None
    captured_at: str
    notes: str | None


@dataclass(frozen=True)
class OpponentPercentageStatistics:
    """Original source values expressed in percentage points."""

    solo_games_played_percent: float
    solo_games_won_percent: float
    solo_hand_percent: float
    suit_games_percent: float
    grand_games_percent: float
    null_games_percent: float
    defender_games_played_percent: float
    defender_games_won_percent: float


@dataclass(frozen=True)
class OpponentStatisticsRecord:
    """One validated external opponent-statistics record."""

    player_id: str
    player_label: str | None
    source: OpponentStatisticsSource
    games_played: int
    statistics: OpponentPercentageStatistics


@dataclass(frozen=True)
class OpponentStatisticsInput:
    """One validated version-1 opponent-statistics input."""

    schema_version: int
    records: tuple[OpponentStatisticsRecord, ...]


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


def _require_non_padded_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{field_name} must be a non-empty, non-padded string.")
    return value


def _validate_rfc3339_date_time(value: str, field_name: str) -> None:
    if not _RFC_3339_DATE_TIME.fullmatch(value):
        raise ValueError(
            f"{field_name} must be a valid RFC 3339 date-time with a time-zone offset."
        )
    try:
        normalized_value = value.replace("t", "T").replace("z", "+00:00").replace("Z", "+00:00")
        if normalized_value[17:19] == "60":
            normalized_value = f"{normalized_value[:17]}59{normalized_value[19:]}"
        datetime.fromisoformat(normalized_value)
    except ValueError as error:
        raise ValueError(
            f"{field_name} must be a valid RFC 3339 date-time with a time-zone offset."
        ) from error


def _require_percentage(value: Any, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be a number from 0 through 100.")
    if not math.isfinite(value) or value < 0 or value > 100:
        raise ValueError(f"{field_name} must be a finite number from 0 through 100.")
    return value


def _validate_percentage_sum(value: float, field_name: str) -> None:
    lower_bound = 100.0 - PERCENTAGE_SUM_TOLERANCE_POINTS
    upper_bound = 100.0 + PERCENTAGE_SUM_TOLERANCE_POINTS
    if value < lower_bound or value > upper_bound:
        raise ValueError(
            f"{field_name} must total from {lower_bound:.0f} through {upper_bound:.0f} "
            "percentage points."
        )


def _build_source(value: Any, record_name: str) -> OpponentStatisticsSource:
    field_name = f"{record_name}.source"
    data = _require_object(value, field_name)
    _require_exact_fields(
        data,
        required_fields={"source_type", "source_name", "captured_at"},
        optional_fields={"source_player_id", "notes"},
        field_name=field_name,
    )
    source_type = data["source_type"]
    if source_type not in OPPONENT_STATISTICS_SOURCE_TYPES:
        raise ValueError(
            f"{field_name}.source_type must be one of {list(OPPONENT_STATISTICS_SOURCE_TYPES)}."
        )
    source_name = _require_non_padded_string(data["source_name"], f"{field_name}.source_name")
    source_player_id = None
    if "source_player_id" in data:
        source_player_id = _require_non_padded_string(
            data["source_player_id"], f"{field_name}.source_player_id"
        )
    captured_at = _require_non_padded_string(data["captured_at"], f"{field_name}.captured_at")
    _validate_rfc3339_date_time(captured_at, f"{field_name}.captured_at")
    notes = None
    if "notes" in data:
        notes = _require_non_padded_string(data["notes"], f"{field_name}.notes")
    return OpponentStatisticsSource(
        source_type=source_type,
        source_name=source_name,
        source_player_id=source_player_id,
        captured_at=captured_at,
        notes=notes,
    )


def _build_statistics(value: Any, record_name: str) -> OpponentPercentageStatistics:
    field_name = f"{record_name}.statistics"
    data = _require_object(value, field_name)
    _require_exact_fields(
        data,
        required_fields=set(_STATISTIC_FIELDS),
        optional_fields=set(),
        field_name=field_name,
    )
    values = {
        statistic_name: _require_percentage(data[statistic_name], f"{field_name}.{statistic_name}")
        for statistic_name in _STATISTIC_FIELDS
    }
    solo_rate = values["solo_games_played_percent"]
    defender_rate = values["defender_games_played_percent"]
    _validate_percentage_sum(
        solo_rate + defender_rate,
        f"{field_name} solo and defender game percentages",
    )
    if solo_rate == 0:
        nonzero_fields = [
            statistic_name
            for statistic_name in _DECLARER_DEPENDENT_FIELDS
            if values[statistic_name] != 0
        ]
        if nonzero_fields:
            raise ValueError(
                f"{field_name} declarer-dependent percentages must be 0 when "
                "solo_games_played_percent is 0."
            )
    else:
        _validate_percentage_sum(
            values["suit_games_percent"]
            + values["grand_games_percent"]
            + values["null_games_percent"],
            f"{field_name} contract-distribution percentages",
        )
    if defender_rate == 0 and values["defender_games_won_percent"] != 0:
        raise ValueError(
            f"{field_name}.defender_games_won_percent must be 0 when "
            "defender_games_played_percent is 0."
        )
    return OpponentPercentageStatistics(**values)


def _build_record(value: Any, record_index: int) -> OpponentStatisticsRecord:
    record_name = f"opponent_statistics_input.records[{record_index}]"
    data = _require_object(value, record_name)
    _require_exact_fields(
        data,
        required_fields={"player_id", "source", "games_played", "statistics"},
        optional_fields={"player_label"},
        field_name=record_name,
    )
    player_id = _require_non_padded_string(data["player_id"], f"{record_name}.player_id")
    player_label = None
    if "player_label" in data:
        player_label = _require_non_padded_string(
            data["player_label"], f"{record_name}.player_label"
        )
    games_played = data["games_played"]
    if isinstance(games_played, bool) or not isinstance(games_played, int) or games_played < 1:
        raise ValueError(f"{record_name}.games_played must be an integer of at least 1.")
    return OpponentStatisticsRecord(
        player_id=player_id,
        player_label=player_label,
        source=_build_source(data["source"], record_name),
        games_played=games_played,
        statistics=_build_statistics(data["statistics"], record_name),
    )


def build_opponent_statistics_input(data: dict[str, Any]) -> OpponentStatisticsInput:
    """Builds and validates one versioned opponent-statistics input."""
    _require_exact_fields(
        data,
        required_fields={"schema_version", "records"},
        optional_fields=set(),
        field_name="opponent_statistics_input",
    )
    schema_version = data["schema_version"]
    if (
        isinstance(schema_version, bool)
        or not isinstance(schema_version, int)
        or schema_version != OPPONENT_STATISTICS_SCHEMA_VERSION
    ):
        raise ValueError(
            "opponent_statistics_input.schema_version must currently equal "
            f"{OPPONENT_STATISTICS_SCHEMA_VERSION}."
        )
    raw_records = data["records"]
    if not isinstance(raw_records, list):
        raise ValueError("opponent_statistics_input.records must be an array.")
    records = tuple(
        _build_record(raw_record, record_index)
        for record_index, raw_record in enumerate(raw_records)
    )
    seen_player_ids: set[str] = set()
    for record in records:
        if record.player_id in seen_player_ids:
            raise ValueError(
                f"Duplicate opponent-statistics player_id '{record.player_id}' is not allowed."
            )
        seen_player_ids.add(record.player_id)
    return OpponentStatisticsInput(schema_version=schema_version, records=records)


def build_player_profile_from_opponent_statistics(
    record: OpponentStatisticsRecord,
) -> PlayerProfile:
    """Converts percentage points to existing normalized profile-rate semantics."""
    statistics = record.statistics
    return PlayerProfile(
        games_played=record.games_played,
        solo_games_played=None,
        defender_games_played=None,
        solo_rate=statistics.solo_games_played_percent / 100,
        solo_win_rate=statistics.solo_games_won_percent / 100,
        hand_game_rate=statistics.solo_hand_percent / 100,
        suit_game_rate=statistics.suit_games_percent / 100,
        grand_rate=statistics.grand_games_percent / 100,
        null_game_rate=statistics.null_games_percent / 100,
        defender_win_rate=statistics.defender_games_won_percent / 100,
    )


def _build_serializable_source(source: OpponentStatisticsSource) -> dict[str, str]:
    result = {
        "source_type": source.source_type,
        "source_name": source.source_name,
    }
    if source.source_player_id is not None:
        result["source_player_id"] = source.source_player_id
    result["captured_at"] = source.captured_at
    if source.notes is not None:
        result["notes"] = source.notes
    return result


def _build_serializable_statistics(
    statistics: OpponentPercentageStatistics,
) -> dict[str, float]:
    return {
        statistic_name: getattr(statistics, statistic_name) for statistic_name in _STATISTIC_FIELDS
    }


def _build_serializable_profile(profile: PlayerProfile) -> dict[str, int | float | None]:
    return {
        "games_played": profile.games_played,
        "solo_games_played": profile.solo_games_played,
        "defender_games_played": profile.defender_games_played,
        "solo_rate": profile.solo_rate,
        "solo_win_rate": profile.solo_win_rate,
        "hand_game_rate": profile.hand_game_rate,
        "suit_game_rate": profile.suit_game_rate,
        "grand_rate": profile.grand_rate,
        "null_game_rate": profile.null_game_rate,
        "defender_win_rate": profile.defender_win_rate,
    }


def build_opponent_statistics_summary(
    statistics_input: OpponentStatisticsInput,
) -> dict[str, Any]:
    """Builds deterministic canonical output while preserving input record order."""
    records = []
    for record in statistics_input.records:
        serialized_record = {
            "player_id": record.player_id,
        }
        if record.player_label is not None:
            serialized_record["player_label"] = record.player_label
        serialized_record.update(
            {
                "source": _build_serializable_source(record.source),
                "games_played": record.games_played,
                "statistics": _build_serializable_statistics(record.statistics),
                "normalized_profile_statistics": _build_serializable_profile(
                    build_player_profile_from_opponent_statistics(record)
                ),
                "validation_metadata": {
                    "percentage_sum_tolerance_points": PERCENTAGE_SUM_TOLERANCE_POINTS,
                },
            }
        )
        records.append(serialized_record)
    return {
        "schema_version": statistics_input.schema_version,
        "record_count": len(records),
        "records": records,
    }
