import math
from dataclasses import dataclass
from typing import Any, Literal

from skat_ai.opponent_profile_derivation import (
    OpponentProfileDerivation,
    derive_opponent_profile,
)
from skat_ai.player_profile import PlayerProfile
from skat_ai.rfc3339 import parse_rfc3339_datetime

OPPONENT_STATISTICS_SCHEMA_VERSION = 1
PERCENTAGE_SUM_TOLERANCE_POINTS = 2.0
OPPONENT_STATISTICS_SOURCE_TYPES = (
    "online_platform",
    "manual_entry",
    "historical_games",
)

OpponentStatisticsSourceType = Literal[
    "online_platform",
    "manual_entry",
    "historical_games",
]

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
_EXACT_COUNT_FIELDS = (
    "solo_games_played",
    "solo_games_won",
    "solo_hand_games",
    "suit_games",
    "grand_games",
    "null_games",
    "defender_games_played",
    "defender_games_won",
)


@dataclass(frozen=True)
class HistoricalAggregationProvenance:
    """Bounded source-game provenance for one historically aggregated player."""

    aggregation_version: int
    dataset_id: str
    dataset_version: str
    included_partitions: tuple[str, ...]
    source_record_ids: tuple[str, ...]
    source_game_ids: tuple[str, ...]
    first_played_at: str
    last_played_at: str


@dataclass(frozen=True)
class OpponentStatisticsSource:
    """Required provenance for one external or historical statistics capture."""

    source_type: OpponentStatisticsSourceType
    source_name: str
    source_player_id: str | None
    captured_at: str
    notes: str | None
    historical_aggregation: HistoricalAggregationProvenance | None


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
class OpponentExactCounts:
    """Exact role, result, Hand, and contract counts when supplied by a source."""

    solo_games_played: int
    solo_games_won: int
    solo_hand_games: int
    suit_games: int
    grand_games: int
    null_games: int
    defender_games_played: int
    defender_games_won: int


@dataclass(frozen=True)
class OpponentStatisticsRecord:
    """One validated external or historically aggregated statistics record."""

    player_id: str
    player_label: str | None
    source: OpponentStatisticsSource
    games_played: int
    statistics: OpponentPercentageStatistics
    exact_counts: OpponentExactCounts | None


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


def _build_historical_aggregation(
    value: Any,
    field_name: str,
    captured_at: str,
) -> HistoricalAggregationProvenance:
    data = _require_object(value, field_name)
    _require_exact_fields(
        data,
        required_fields={
            "aggregation_version",
            "dataset_id",
            "dataset_version",
            "included_partitions",
            "source_record_ids",
            "source_game_ids",
            "first_played_at",
            "last_played_at",
        },
        optional_fields=set(),
        field_name=field_name,
    )
    if data["aggregation_version"] != 1 or isinstance(
        data["aggregation_version"], bool
    ):
        raise ValueError(f"{field_name}.aggregation_version must currently equal 1.")
    dataset_id = _require_non_padded_string(
        data["dataset_id"], f"{field_name}.dataset_id"
    )
    dataset_version = _require_non_padded_string(
        data["dataset_version"], f"{field_name}.dataset_version"
    )
    raw_partitions = data["included_partitions"]
    canonical_partitions = ("train", "validation", "test")
    if (
        not isinstance(raw_partitions, list)
        or not raw_partitions
        or any(partition not in canonical_partitions for partition in raw_partitions)
        or len(raw_partitions) != len(set(raw_partitions))
        or raw_partitions
        != [partition for partition in canonical_partitions if partition in raw_partitions]
    ):
        raise ValueError(
            f"{field_name}.included_partitions must be a non-empty, unique array in "
            "canonical train, validation, test order."
        )

    def build_identifiers(raw_value: Any, nested_field: str) -> tuple[str, ...]:
        if not isinstance(raw_value, list) or not raw_value:
            raise ValueError(f"{nested_field} must be a non-empty array.")
        identifiers = tuple(
            _require_non_padded_string(item, f"{nested_field}[{index}]")
            for index, item in enumerate(raw_value)
        )
        if len(identifiers) != len(set(identifiers)):
            raise ValueError(f"{nested_field} must not contain duplicates.")
        return identifiers

    source_record_ids = build_identifiers(
        data["source_record_ids"], f"{field_name}.source_record_ids"
    )
    source_game_ids = build_identifiers(
        data["source_game_ids"], f"{field_name}.source_game_ids"
    )
    if len(source_record_ids) != len(source_game_ids):
        raise ValueError(
            f"{field_name}.source_record_ids and source_game_ids must have equal lengths."
        )
    first_played_at = _require_non_padded_string(
        data["first_played_at"], f"{field_name}.first_played_at"
    )
    last_played_at = _require_non_padded_string(
        data["last_played_at"], f"{field_name}.last_played_at"
    )
    first_instant = parse_rfc3339_datetime(
        first_played_at, f"{field_name}.first_played_at"
    )
    last_instant = parse_rfc3339_datetime(
        last_played_at, f"{field_name}.last_played_at"
    )
    if first_instant > last_instant:
        raise ValueError(f"{field_name}.first_played_at must not be after last_played_at.")
    captured_instant = parse_rfc3339_datetime(captured_at, f"{field_name} source.captured_at")
    if captured_instant != last_instant:
        raise ValueError(
            f"{field_name} requires source.captured_at to represent the same instant "
            "as last_played_at."
        )
    return HistoricalAggregationProvenance(
        aggregation_version=1,
        dataset_id=dataset_id,
        dataset_version=dataset_version,
        included_partitions=tuple(raw_partitions),
        source_record_ids=source_record_ids,
        source_game_ids=source_game_ids,
        first_played_at=first_played_at,
        last_played_at=last_played_at,
    )


def _build_source(value: Any, record_name: str) -> OpponentStatisticsSource:
    field_name = f"{record_name}.source"
    data = _require_object(value, field_name)
    _require_exact_fields(
        data,
        required_fields={"source_type", "source_name", "captured_at"},
        optional_fields={"source_player_id", "notes", "historical_aggregation"},
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
    parse_rfc3339_datetime(captured_at, f"{field_name}.captured_at")
    notes = None
    if "notes" in data:
        notes = _require_non_padded_string(data["notes"], f"{field_name}.notes")
    historical_aggregation = None
    if source_type == "historical_games":
        if "historical_aggregation" not in data:
            raise ValueError(
                f"{field_name}.historical_aggregation is required for historical_games."
            )
        historical_aggregation = _build_historical_aggregation(
            data["historical_aggregation"],
            f"{field_name}.historical_aggregation",
            captured_at,
        )
    elif "historical_aggregation" in data:
        raise ValueError(
            f"{field_name}.historical_aggregation is supported only for historical_games."
        )
    return OpponentStatisticsSource(
        source_type=source_type,
        source_name=source_name,
        source_player_id=source_player_id,
        captured_at=captured_at,
        notes=notes,
        historical_aggregation=historical_aggregation,
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


def _percentage(numerator: int, denominator: int) -> float:
    return numerator / denominator * 100 if denominator else 0.0


def _build_exact_counts(
    value: Any,
    record_name: str,
    games_played: int,
    statistics: OpponentPercentageStatistics,
) -> OpponentExactCounts:
    field_name = f"{record_name}.exact_counts"
    data = _require_object(value, field_name)
    _require_exact_fields(
        data,
        required_fields=set(_EXACT_COUNT_FIELDS),
        optional_fields=set(),
        field_name=field_name,
    )
    values: dict[str, int] = {}
    for count_name in _EXACT_COUNT_FIELDS:
        count = data[count_name]
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError(f"{field_name}.{count_name} must be a non-negative integer.")
        values[count_name] = count
    exact_counts = OpponentExactCounts(**values)
    if exact_counts.solo_games_played + exact_counts.defender_games_played != games_played:
        raise ValueError(
            f"{field_name} solo and defender games must sum to games_played."
        )
    if exact_counts.solo_games_won > exact_counts.solo_games_played:
        raise ValueError(f"{field_name}.solo_games_won must not exceed solo_games_played.")
    if exact_counts.solo_hand_games > exact_counts.solo_games_played:
        raise ValueError(f"{field_name}.solo_hand_games must not exceed solo_games_played.")
    if (
        exact_counts.suit_games + exact_counts.grand_games + exact_counts.null_games
        != exact_counts.solo_games_played
    ):
        raise ValueError(
            f"{field_name} suit, Grand, and Null games must sum to solo_games_played."
        )
    if exact_counts.defender_games_won > exact_counts.defender_games_played:
        raise ValueError(
            f"{field_name}.defender_games_won must not exceed defender_games_played."
        )
    expected_percentages = {
        "solo_games_played_percent": _percentage(
            exact_counts.solo_games_played, games_played
        ),
        "solo_games_won_percent": _percentage(
            exact_counts.solo_games_won, exact_counts.solo_games_played
        ),
        "solo_hand_percent": _percentage(
            exact_counts.solo_hand_games, exact_counts.solo_games_played
        ),
        "suit_games_percent": _percentage(
            exact_counts.suit_games, exact_counts.solo_games_played
        ),
        "grand_games_percent": _percentage(
            exact_counts.grand_games, exact_counts.solo_games_played
        ),
        "null_games_percent": _percentage(
            exact_counts.null_games, exact_counts.solo_games_played
        ),
        "defender_games_played_percent": _percentage(
            exact_counts.defender_games_played, games_played
        ),
        "defender_games_won_percent": _percentage(
            exact_counts.defender_games_won, exact_counts.defender_games_played
        ),
    }
    for statistic_name, expected in expected_percentages.items():
        supplied = getattr(statistics, statistic_name)
        difference = abs(supplied - expected)
        if difference > PERCENTAGE_SUM_TOLERANCE_POINTS and not math.isclose(
            difference,
            PERCENTAGE_SUM_TOLERANCE_POINTS,
            abs_tol=1e-12,
        ):
            raise ValueError(
                f"{field_name} contradicts statistics.{statistic_name} beyond the "
                f"{PERCENTAGE_SUM_TOLERANCE_POINTS:g}-percentage-point tolerance."
            )
    return exact_counts


def _build_record(value: Any, record_index: int) -> OpponentStatisticsRecord:
    record_name = f"opponent_statistics_input.records[{record_index}]"
    data = _require_object(value, record_name)
    _require_exact_fields(
        data,
        required_fields={"player_id", "source", "games_played", "statistics"},
        optional_fields={"player_label", "exact_counts"},
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
    source = _build_source(data["source"], record_name)
    if source.source_type == "historical_games" and source.source_player_id != player_id:
        raise ValueError(
            f"{record_name}.source.source_player_id must equal player_id for "
            "historical_games."
        )
    statistics = _build_statistics(data["statistics"], record_name)
    exact_counts = (
        _build_exact_counts(data["exact_counts"], record_name, games_played, statistics)
        if "exact_counts" in data
        else None
    )
    return OpponentStatisticsRecord(
        player_id=player_id,
        player_label=player_label,
        source=source,
        games_played=games_played,
        statistics=statistics,
        exact_counts=exact_counts,
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
    exact_counts = record.exact_counts
    if exact_counts is not None:
        solo_rate = exact_counts.solo_games_played / record.games_played
        defender_rate = exact_counts.defender_games_played / record.games_played
        solo_win_rate = (
            exact_counts.solo_games_won / exact_counts.solo_games_played
            if exact_counts.solo_games_played
            else 0.0
        )
        hand_game_rate = (
            exact_counts.solo_hand_games / exact_counts.solo_games_played
            if exact_counts.solo_games_played
            else 0.0
        )
        suit_game_rate = (
            exact_counts.suit_games / exact_counts.solo_games_played
            if exact_counts.solo_games_played
            else 0.0
        )
        grand_rate = (
            exact_counts.grand_games / exact_counts.solo_games_played
            if exact_counts.solo_games_played
            else 0.0
        )
        null_game_rate = (
            exact_counts.null_games / exact_counts.solo_games_played
            if exact_counts.solo_games_played
            else 0.0
        )
        defender_win_rate = (
            exact_counts.defender_games_won / exact_counts.defender_games_played
            if exact_counts.defender_games_played
            else 0.0
        )
    else:
        solo_rate = statistics.solo_games_played_percent / 100
        defender_rate = statistics.defender_games_played_percent / 100
        solo_win_rate = statistics.solo_games_won_percent / 100
        hand_game_rate = statistics.solo_hand_percent / 100
        suit_game_rate = statistics.suit_games_percent / 100
        grand_rate = statistics.grand_games_percent / 100
        null_game_rate = statistics.null_games_percent / 100
        defender_win_rate = statistics.defender_games_won_percent / 100
    return PlayerProfile(
        games_played=record.games_played,
        solo_games_played=(
            exact_counts.solo_games_played if exact_counts is not None else None
        ),
        defender_games_played=(
            exact_counts.defender_games_played if exact_counts is not None else None
        ),
        solo_rate=solo_rate,
        defender_rate=defender_rate,
        solo_win_rate=solo_win_rate,
        hand_game_rate=hand_game_rate,
        suit_game_rate=suit_game_rate,
        grand_rate=grand_rate,
        null_game_rate=null_game_rate,
        defender_win_rate=defender_win_rate,
    )


def _build_serializable_historical_aggregation(
    provenance: HistoricalAggregationProvenance,
) -> dict[str, Any]:
    return {
        "aggregation_version": provenance.aggregation_version,
        "dataset_id": provenance.dataset_id,
        "dataset_version": provenance.dataset_version,
        "included_partitions": list(provenance.included_partitions),
        "source_record_ids": list(provenance.source_record_ids),
        "source_game_ids": list(provenance.source_game_ids),
        "first_played_at": provenance.first_played_at,
        "last_played_at": provenance.last_played_at,
    }


def _build_serializable_source(source: OpponentStatisticsSource) -> dict[str, Any]:
    result: dict[str, Any] = {
        "source_type": source.source_type,
        "source_name": source.source_name,
    }
    if source.source_player_id is not None:
        result["source_player_id"] = source.source_player_id
    result["captured_at"] = source.captured_at
    if source.notes is not None:
        result["notes"] = source.notes
    if source.historical_aggregation is not None:
        result["historical_aggregation"] = _build_serializable_historical_aggregation(
            source.historical_aggregation
        )
    return result


def _build_serializable_statistics(
    statistics: OpponentPercentageStatistics,
) -> dict[str, float]:
    return {
        statistic_name: getattr(statistics, statistic_name) for statistic_name in _STATISTIC_FIELDS
    }


def _build_serializable_exact_counts(
    exact_counts: OpponentExactCounts,
) -> dict[str, int]:
    return {
        count_name: getattr(exact_counts, count_name)
        for count_name in _EXACT_COUNT_FIELDS
    }


def _build_serializable_profile(profile: PlayerProfile) -> dict[str, int | float | None]:
    return {
        "games_played": profile.games_played,
        "solo_games_played": profile.solo_games_played,
        "defender_games_played": profile.defender_games_played,
        "solo_rate": profile.solo_rate,
        "defender_rate": profile.defender_rate,
        "solo_win_rate": profile.solo_win_rate,
        "hand_game_rate": profile.hand_game_rate,
        "suit_game_rate": profile.suit_game_rate,
        "grand_rate": profile.grand_rate,
        "null_game_rate": profile.null_game_rate,
        "defender_win_rate": profile.defender_win_rate,
    }


def _build_serializable_derivation(
    derivation: OpponentProfileDerivation,
) -> dict[str, Any]:
    return {
        "profile_derivation_version": derivation.profile_derivation_version,
        "confidence": {
            scope: {
                "level": result.level,
                "evidence_count": result.evidence_count,
                "evidence_kind": result.evidence_kind,
            }
            for scope, result in derivation.confidence.items()
        },
        "signals": [
            {
                "code": signal.code,
                "source_field": signal.source_field,
                "observed_value": signal.observed_value,
                "comparison_operator": signal.comparison_operator,
                "threshold": signal.threshold,
                "confidence_scope": signal.confidence_scope,
                "confidence_level": signal.confidence_level,
                "value_threshold_matched": signal.value_threshold_matched,
                "actionable": signal.actionable,
                "reason_code": signal.reason_code,
            }
            for signal in derivation.signals
        ],
        "classification": derivation.classification,
        "recommended_policy_preset": derivation.recommended_policy_preset,
        "actionable_policy_preset": derivation.actionable_policy_preset,
        "derivation_status": derivation.derivation_status,
        "decisive_signal_codes": list(derivation.decisive_signal_codes),
        "explanations": list(derivation.explanations),
    }


def build_opponent_statistics_summary(
    statistics_input: OpponentStatisticsInput,
) -> dict[str, Any]:
    """Builds deterministic canonical output while preserving input record order."""
    records = []
    for record in statistics_input.records:
        profile = build_player_profile_from_opponent_statistics(record)
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
                "normalized_profile_statistics": _build_serializable_profile(profile),
                "profile_derivation": _build_serializable_derivation(
                    derive_opponent_profile(profile)
                ),
                "validation_metadata": {
                    "percentage_sum_tolerance_points": PERCENTAGE_SUM_TOLERANCE_POINTS,
                },
            }
        )
        if record.exact_counts is not None:
            serialized_record["exact_counts"] = _build_serializable_exact_counts(
                record.exact_counts
            )
        records.append(serialized_record)
    return {
        "schema_version": statistics_input.schema_version,
        "record_count": len(records),
        "records": records,
    }


def build_serializable_opponent_statistics_input(
    statistics_input: OpponentStatisticsInput,
) -> dict[str, Any]:
    """Builds one canonical standalone opponent-statistics input object."""
    records = []
    for record in statistics_input.records:
        serialized_record: dict[str, Any] = {"player_id": record.player_id}
        if record.player_label is not None:
            serialized_record["player_label"] = record.player_label
        serialized_record.update(
            {
                "source": _build_serializable_source(record.source),
                "games_played": record.games_played,
                "statistics": _build_serializable_statistics(record.statistics),
            }
        )
        if record.exact_counts is not None:
            serialized_record["exact_counts"] = _build_serializable_exact_counts(
                record.exact_counts
            )
        records.append(serialized_record)
    return {
        "opponent_statistics_input": {
            "schema_version": statistics_input.schema_version,
            "records": records,
        }
    }
