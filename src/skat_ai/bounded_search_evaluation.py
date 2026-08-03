from collections.abc import Iterable
from typing import Any

from skat_ai.dataset_partition_policy import (
    CANONICAL_DATASET_PARTITIONS,
    build_serializable_dataset_partition_policy,
)
from skat_ai.historical_decision_snapshot import build_historical_decision_snapshots
from skat_ai.historical_game import build_historical_game_summary
from skat_ai.historical_search_review import (
    HistoricalSearchReviewSettings,
    _with_breakdown_fields,
    build_historical_search_decision_review,
    build_historical_search_review_breakdowns,
    build_historical_search_review_metrics,
    build_serializable_historical_search_review_settings,
)
from skat_ai.search_budget_profiles import EVALUATION_SEARCH_BUDGET_PROFILE
from skat_ai.simulation import DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT
from skat_ai.training_dataset import TrainingDatasetInput

BOUNDED_SEARCH_EVALUATION_SCHEMA_VERSION = 1
BOUNDED_SEARCH_EVALUATION_METHOD = "bounded_search_vs_immediate_v1"
DEFAULT_BOUNDED_SEARCH_EVALUATION_PARTITIONS = ("validation", "test")
DEFAULT_BOUNDED_SEARCH_EVALUATION_PROFILE = EVALUATION_SEARCH_BUDGET_PROFILE
EVALUATION_IMMEDIATE_BASE_RANDOM_SEED = 0


def _canonicalize_partitions(partitions: Iterable[str]) -> tuple[str, ...]:
    if isinstance(partitions, (str, bytes)):
        raise ValueError("partitions must be a non-empty iterable of partition names.")
    try:
        requested = tuple(partitions)
    except TypeError as exc:
        raise ValueError(
            "partitions must be a non-empty iterable of partition names."
        ) from exc
    if not requested:
        raise ValueError("partitions must not be empty.")
    unsupported = sorted(
        {
            partition
            for partition in requested
            if partition not in CANONICAL_DATASET_PARTITIONS
        }
    )
    if unsupported:
        raise ValueError(f"Unsupported evaluation partitions: {unsupported}.")
    return tuple(
        partition
        for partition in CANONICAL_DATASET_PARTITIONS
        if partition in requested
    )


def _validate_max_decisions(max_decisions: int | None) -> None:
    if max_decisions is not None and (
        isinstance(max_decisions, bool)
        or not isinstance(max_decisions, int)
        or max_decisions <= 0
    ):
        raise ValueError("max_decisions must be a positive integer or null.")


def _source_dataset(dataset: TrainingDatasetInput) -> dict[str, Any]:
    result = {
        "dataset_id": dataset.dataset_id,
        "dataset_version": dataset.dataset_version,
        "training_dataset_schema_version": dataset.schema_version,
        "feature_generation_version": dataset.feature_generation_version,
        "target": dataset.target,
    }
    if dataset.partition_policy is not None:
        result["partition_policy"] = build_serializable_dataset_partition_policy(
            dataset.partition_policy
        )
    return result


def evaluate_bounded_search_dataset(
    dataset: TrainingDatasetInput,
    base_search_seed: int,
    partitions: Iterable[str] = DEFAULT_BOUNDED_SEARCH_EVALUATION_PARTITIONS,
    search_budget_profile: str = DEFAULT_BOUNDED_SEARCH_EVALUATION_PROFILE,
    max_decisions: int | None = None,
) -> dict[str, Any]:
    """Evaluates a deterministic selected dataset prefix against Immediate."""
    if not isinstance(dataset, TrainingDatasetInput):
        raise ValueError("dataset must be a TrainingDatasetInput.")
    selected_partitions = _canonicalize_partitions(partitions)
    _validate_max_decisions(max_decisions)
    selected_records = [
        record for record in dataset.records if record.partition in selected_partitions
    ]
    if not selected_records:
        raise ValueError("No dataset records match the selected evaluation partitions.")
    settings = HistoricalSearchReviewSettings(
        base_search_seed=base_search_seed,
        search_budget_profile=search_budget_profile,
        immediate_sample_count=DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT,
        immediate_base_random_seed=EVALUATION_IMMEDIATE_BASE_RANDOM_SEED,
    )

    records = []
    all_decisions: list[dict[str, Any]] = []
    available_decision_count = 0
    for record in selected_records:
        historical_summary = build_historical_game_summary(record.historical_game)
        snapshot_summary = build_historical_decision_snapshots(historical_summary)
        source_decision_count = snapshot_summary.snapshot_count
        if source_decision_count != snapshot_summary.cardinality.expected_snapshot_count:
            raise ValueError(
                f"Evaluation record '{record.record_id}' snapshot count does not reconcile."
            )
        available_decision_count += source_decision_count
        remaining_capacity = (
            source_decision_count
            if max_decisions is None
            else max(0, max_decisions - len(all_decisions))
        )
        selected_snapshots = snapshot_summary.snapshots[:remaining_capacity]
        decisions = [
            build_historical_search_decision_review(
                snapshot,
                record.historical_game,
                settings,
                stable_game_identity=record.historical_game.game_id,
            )
            for snapshot in selected_snapshots
        ]
        all_decisions.extend(
            {**decision, "partition": record.partition} for decision in decisions
        )
        records.append(
            {
                "record_id": record.record_id,
                "partition": record.partition,
                "source_game_id": record.historical_game.game_id,
                "source_decision_count": source_decision_count,
                "evaluated_decision_count": len(decisions),
                "decisions": decisions,
            }
        )

    aggregate_decisions = [_with_breakdown_fields(row) for row in all_decisions]
    metrics = build_historical_search_review_metrics(aggregate_decisions)
    breakdowns = build_historical_search_review_breakdowns(aggregate_decisions)
    breakdowns = {
        "by_partition": [
            {
                "partition": partition,
                "metrics": build_historical_search_review_metrics(
                    [
                        row
                        for row in aggregate_decisions
                        if row["partition"] == partition
                    ]
                ),
            }
            for partition in CANONICAL_DATASET_PARTITIONS
            if any(row["partition"] == partition for row in aggregate_decisions)
        ],
        **breakdowns,
    }
    zero_decision_record_count = sum(
        record["source_decision_count"] == 0 for record in records
    )
    if sum(record["evaluated_decision_count"] for record in records) != len(
        all_decisions
    ):
        raise ValueError("Evaluation record decision totals do not reconcile.")
    if sum(record["source_decision_count"] for record in records) != (
        available_decision_count
    ):
        raise ValueError("Evaluation available decision totals do not reconcile.")
    for breakdown_name, rows in breakdowns.items():
        if sum(
            row["metrics"]["decision_counts"]["decision_count"] for row in rows
        ) != len(all_decisions):
            raise ValueError(f"{breakdown_name} decision counts do not reconcile.")

    serialized_settings = build_serializable_historical_search_review_settings(
        settings
    )
    return {
        "schema_version": BOUNDED_SEARCH_EVALUATION_SCHEMA_VERSION,
        "evaluation_method": BOUNDED_SEARCH_EVALUATION_METHOD,
        "source_dataset": _source_dataset(dataset),
        "settings": serialized_settings,
        "selection": {
            "partitions": list(selected_partitions),
            "max_decisions": max_decisions,
            "record_count": len(records),
            "available_decision_count": available_decision_count,
            "evaluated_decision_count": len(all_decisions),
            "decision_cap_reached": (
                max_decisions is not None
                and available_decision_count > len(all_decisions)
            ),
        },
        "record_count": len(records),
        "zero_decision_record_count": zero_decision_record_count,
        "available_decision_count": available_decision_count,
        **metrics,
        "breakdowns": breakdowns,
        "records": records,
    }
