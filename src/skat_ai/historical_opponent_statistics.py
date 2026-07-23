from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from skat_ai.game_declaration import SUIT_GAME_TYPES
from skat_ai.historical_game import build_historical_game_summary
from skat_ai.opponent_statistics import (
    OPPONENT_STATISTICS_SCHEMA_VERSION,
    HistoricalAggregationProvenance,
    OpponentExactCounts,
    OpponentPercentageStatistics,
    OpponentStatisticsInput,
    OpponentStatisticsRecord,
    OpponentStatisticsSource,
    build_opponent_statistics_summary,
)
from skat_ai.rfc3339 import parse_rfc3339_datetime
from skat_ai.training_dataset import TRAINING_PARTITIONS, TrainingDatasetInput

HISTORICAL_OPPONENT_STATISTICS_AGGREGATION_VERSION = 1


@dataclass(frozen=True)
class HistoricalOpponentStatisticsPlayerRecord:
    """One player's exact aggregate and ordered source-game provenance."""

    statistics_record: OpponentStatisticsRecord
    source_record_ids: tuple[str, ...]
    source_game_ids: tuple[str, ...]
    included_partitions: tuple[str, ...]
    first_played_at: str
    last_played_at: str


@dataclass(frozen=True)
class HistoricalOpponentStatisticsAggregation:
    """One deterministic, time-bounded historical statistics aggregation."""

    aggregation_version: int
    source_dataset: dict[str, Any]
    included_partitions: tuple[str, ...]
    before: str | None
    excluded_record_counts_by_partition: dict[str, int]
    excluded_record_count_by_temporal_cutoff: int
    source_record_count: int
    source_game_count: int
    first_played_at: str
    last_played_at: str
    records: tuple[HistoricalOpponentStatisticsPlayerRecord, ...]


@dataclass
class _PlayerAccumulator:
    player_id: str
    player_label: str | None
    games_played: int = 0
    solo_games_played: int = 0
    solo_games_won: int = 0
    solo_hand_games: int = 0
    suit_games: int = 0
    grand_games: int = 0
    null_games: int = 0
    defender_games_played: int = 0
    defender_games_won: int = 0
    source_record_ids: list[str] = field(default_factory=list)
    source_game_ids: list[str] = field(default_factory=list)
    partitions: set[str] = field(default_factory=set)
    first_played_at: str | None = None
    first_played_at_instant: datetime | None = None
    last_played_at: str | None = None
    last_played_at_instant: datetime | None = None


def _canonicalize_partitions(
    included_partitions: tuple[str, ...] | None,
    dataset: TrainingDatasetInput,
) -> tuple[str, ...]:
    if included_partitions is None:
        return TRAINING_PARTITIONS
    if not included_partitions:
        raise ValueError("At least one opponent-statistics partition must be selected.")
    unsupported = sorted(set(included_partitions) - set(TRAINING_PARTITIONS))
    if unsupported:
        raise ValueError(f"Unsupported opponent-statistics partitions: {unsupported}.")
    selected = tuple(
        partition for partition in TRAINING_PARTITIONS if partition in included_partitions
    )
    populated = {record.partition for record in dataset.records}
    empty = [partition for partition in selected if partition not in populated]
    if empty:
        raise ValueError(
            "Selected opponent-statistics partitions contain no source records: "
            f"{empty}."
        )
    return selected


def _percentage(numerator: int, denominator: int) -> float:
    return numerator / denominator * 100 if denominator else 0.0


def _build_exact_counts(accumulator: _PlayerAccumulator) -> OpponentExactCounts:
    counts = OpponentExactCounts(
        solo_games_played=accumulator.solo_games_played,
        solo_games_won=accumulator.solo_games_won,
        solo_hand_games=accumulator.solo_hand_games,
        suit_games=accumulator.suit_games,
        grand_games=accumulator.grand_games,
        null_games=accumulator.null_games,
        defender_games_played=accumulator.defender_games_played,
        defender_games_won=accumulator.defender_games_won,
    )
    if counts.solo_games_played + counts.defender_games_played != accumulator.games_played:
        raise ValueError("Aggregated role counts do not reconcile with games_played.")
    if counts.solo_games_won > counts.solo_games_played:
        raise ValueError("Aggregated solo wins exceed solo games played.")
    if counts.solo_hand_games > counts.solo_games_played:
        raise ValueError("Aggregated Hand games exceed solo games played.")
    if counts.suit_games + counts.grand_games + counts.null_games != counts.solo_games_played:
        raise ValueError("Aggregated contract counts do not reconcile with solo games.")
    if counts.defender_games_won > counts.defender_games_played:
        raise ValueError("Aggregated defender wins exceed defender games played.")
    return counts


def _build_percentages(
    games_played: int,
    counts: OpponentExactCounts,
) -> OpponentPercentageStatistics:
    return OpponentPercentageStatistics(
        solo_games_played_percent=_percentage(
            counts.solo_games_played, games_played
        ),
        solo_games_won_percent=_percentage(
            counts.solo_games_won, counts.solo_games_played
        ),
        solo_hand_percent=_percentage(
            counts.solo_hand_games, counts.solo_games_played
        ),
        suit_games_percent=_percentage(counts.suit_games, counts.solo_games_played),
        grand_games_percent=_percentage(counts.grand_games, counts.solo_games_played),
        null_games_percent=_percentage(counts.null_games, counts.solo_games_played),
        defender_games_played_percent=_percentage(
            counts.defender_games_played, games_played
        ),
        defender_games_won_percent=_percentage(
            counts.defender_games_won, counts.defender_games_played
        ),
    )


def _update_player_source(
    accumulator: _PlayerAccumulator,
    record_id: str,
    game_id: str,
    partition: str,
    played_at: str,
    played_at_instant: datetime,
) -> None:
    accumulator.source_record_ids.append(record_id)
    accumulator.source_game_ids.append(game_id)
    accumulator.partitions.add(partition)
    if (
        accumulator.first_played_at_instant is None
        or played_at_instant < accumulator.first_played_at_instant
    ):
        accumulator.first_played_at = played_at
        accumulator.first_played_at_instant = played_at_instant
    if (
        accumulator.last_played_at_instant is None
        or played_at_instant > accumulator.last_played_at_instant
    ):
        accumulator.last_played_at = played_at
        accumulator.last_played_at_instant = played_at_instant


def aggregate_historical_opponent_statistics(
    dataset: TrainingDatasetInput,
    included_partitions: tuple[str, ...] | None = None,
    before: str | None = None,
) -> HistoricalOpponentStatisticsAggregation:
    """Aggregates exact reusable player statistics from selected historical games."""
    selected_partitions = _canonicalize_partitions(included_partitions, dataset)
    before_instant = (
        parse_rfc3339_datetime(before, "opponent-statistics-before")
        if before is not None
        else None
    )
    partition_selected_records = [
        record for record in dataset.records if record.partition in selected_partitions
    ]
    selected_with_instants = []
    for record in partition_selected_records:
        played_at = record.historical_game.played_at
        if played_at is None:
            raise ValueError(
                f"Historical game '{record.historical_game.game_id}' played_at is "
                "required for reusable opponent-statistics aggregation."
            )
        selected_with_instants.append(
            (
                record,
                parse_rfc3339_datetime(
                    played_at,
                    f"Historical game '{record.historical_game.game_id}' played_at",
                ),
            )
        )
    included_records = [
        item
        for item in selected_with_instants
        if before_instant is None or item[1] < before_instant
    ]
    if not included_records:
        raise ValueError("Opponent-statistics selection leaves no historical games.")

    accumulators: dict[str, _PlayerAccumulator] = {}
    for record, played_at_instant in included_records:
        game = record.historical_game
        played_at = game.played_at
        if played_at is None:
            raise AssertionError("Selected historical game lost its validated played_at.")
        summary = build_historical_game_summary(game)
        settlement = summary["final_settlement_summary"]
        if settlement["is_loss"] is True:
            winner = "defenders"
        elif settlement["is_loss"] is False:
            winner = "declarer"
        else:
            raise ValueError(
                f"Historical game '{game.game_id}' final settlement has no decided winner."
            )

        for player in game.players:
            accumulator = accumulators.get(player.player_id)
            if accumulator is None:
                accumulator = _PlayerAccumulator(player.player_id, player.player_label)
                accumulators[player.player_id] = accumulator
            elif (
                player.player_label is not None
                and accumulator.player_label is not None
                and player.player_label != accumulator.player_label
            ):
                raise ValueError(
                    f"Conflicting non-null player labels for player_id "
                    f"'{player.player_id}'."
                )
            elif accumulator.player_label is None and player.player_label is not None:
                accumulator.player_label = player.player_label

            accumulator.games_played += 1
            if player.player_id == game.declarer_player_id:
                accumulator.solo_games_played += 1
                if winner == "declarer":
                    accumulator.solo_games_won += 1
                if game.declaration.hand_game:
                    accumulator.solo_hand_games += 1
                if game.declaration.game_type in SUIT_GAME_TYPES:
                    accumulator.suit_games += 1
                elif game.declaration.game_type == "grand":
                    accumulator.grand_games += 1
                elif game.declaration.game_type == "null":
                    accumulator.null_games += 1
                else:
                    raise ValueError(
                        f"Historical game '{game.game_id}' has an unsupported contract."
                    )
            else:
                accumulator.defender_games_played += 1
                if winner == "defenders":
                    accumulator.defender_games_won += 1
            _update_player_source(
                accumulator,
                record.record_id,
                game.game_id,
                record.partition,
                played_at,
                played_at_instant,
            )

    player_records = []
    for accumulator in accumulators.values():
        if accumulator.first_played_at is None or accumulator.last_played_at is None:
            raise AssertionError("Aggregated player is missing source timestamps.")
        counts = _build_exact_counts(accumulator)
        player_partitions = tuple(
            partition
            for partition in TRAINING_PARTITIONS
            if partition in accumulator.partitions
        )
        provenance = HistoricalAggregationProvenance(
            aggregation_version=HISTORICAL_OPPONENT_STATISTICS_AGGREGATION_VERSION,
            dataset_id=dataset.dataset_id,
            dataset_version=dataset.dataset_version,
            included_partitions=player_partitions,
            source_record_ids=tuple(accumulator.source_record_ids),
            source_game_ids=tuple(accumulator.source_game_ids),
            first_played_at=accumulator.first_played_at,
            last_played_at=accumulator.last_played_at,
        )
        statistics_record = OpponentStatisticsRecord(
            player_id=accumulator.player_id,
            player_label=accumulator.player_label,
            source=OpponentStatisticsSource(
                source_type="historical_games",
                source_name=dataset.dataset_id,
                source_player_id=accumulator.player_id,
                captured_at=accumulator.last_played_at,
                notes=None,
                historical_aggregation=provenance,
            ),
            games_played=accumulator.games_played,
            statistics=_build_percentages(accumulator.games_played, counts),
            exact_counts=counts,
        )
        player_records.append(
            HistoricalOpponentStatisticsPlayerRecord(
                statistics_record=statistics_record,
                source_record_ids=tuple(accumulator.source_record_ids),
                source_game_ids=tuple(accumulator.source_game_ids),
                included_partitions=player_partitions,
                first_played_at=accumulator.first_played_at,
                last_played_at=accumulator.last_played_at,
            )
        )

    first_record = min(included_records, key=lambda item: item[1])[0]
    last_record = max(included_records, key=lambda item: item[1])[0]
    excluded_by_partition = {
        partition: sum(
            record.partition == partition and partition not in selected_partitions
            for record in dataset.records
        )
        for partition in TRAINING_PARTITIONS
    }
    return HistoricalOpponentStatisticsAggregation(
        aggregation_version=HISTORICAL_OPPONENT_STATISTICS_AGGREGATION_VERSION,
        source_dataset={
            "dataset_id": dataset.dataset_id,
            "dataset_version": dataset.dataset_version,
            "training_dataset_schema_version": dataset.schema_version,
            "feature_generation_version": dataset.feature_generation_version,
            "target": dataset.target,
        },
        included_partitions=selected_partitions,
        before=before,
        excluded_record_counts_by_partition=excluded_by_partition,
        excluded_record_count_by_temporal_cutoff=(
            len(partition_selected_records) - len(included_records)
        ),
        source_record_count=len(included_records),
        source_game_count=len(included_records),
        first_played_at=first_record.historical_game.played_at or "",
        last_played_at=last_record.historical_game.played_at or "",
        records=tuple(player_records),
    )


def build_exportable_opponent_statistics_input(
    aggregation: HistoricalOpponentStatisticsAggregation,
) -> OpponentStatisticsInput:
    """Builds a standalone reusable statistics input without applying any policy."""
    return OpponentStatisticsInput(
        schema_version=OPPONENT_STATISTICS_SCHEMA_VERSION,
        records=tuple(record.statistics_record for record in aggregation.records),
    )


def build_historical_opponent_statistics_aggregation_summary(
    aggregation: HistoricalOpponentStatisticsAggregation,
) -> dict[str, Any]:
    """Serializes one aggregation with exact profiles and bounded provenance."""
    statistics_summary = build_opponent_statistics_summary(
        build_exportable_opponent_statistics_input(aggregation)
    )
    records = statistics_summary["records"]
    return {
        "schema_version": 1,
        "aggregation_version": aggregation.aggregation_version,
        "source_dataset": aggregation.source_dataset.copy(),
        "selection": {
            "included_partitions": list(aggregation.included_partitions),
            "before": aggregation.before,
            "excluded_record_counts_by_partition": (
                aggregation.excluded_record_counts_by_partition.copy()
            ),
            "excluded_record_count_by_temporal_cutoff": (
                aggregation.excluded_record_count_by_temporal_cutoff
            ),
        },
        "source_record_count": aggregation.source_record_count,
        "source_game_count": aggregation.source_game_count,
        "player_count": len(records),
        "first_played_at": aggregation.first_played_at,
        "last_played_at": aggregation.last_played_at,
        "records": records,
    }
