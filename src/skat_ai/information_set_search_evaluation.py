from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from skat_ai.bounded_search_result import WORLD_COVERAGE_VALUES
from skat_ai.dataset_partition_policy import (
    CANONICAL_DATASET_PARTITIONS,
    DatasetPartitionPolicy,
    build_serializable_dataset_partition_policy,
)
from skat_ai.historical_decision_snapshot import (
    HistoricalDecisionSnapshotSummary,
    build_historical_decision_snapshots,
)
from skat_ai.historical_game import (
    HistoricalGameRecord,
    build_historical_game_summary,
)
from skat_ai.historical_information_set_search_review import (
    DECISION_PHASES,
    HISTORICAL_ROLES,
    HISTORICAL_SEATS,
    RECOMMENDATION_AGREEMENT_VALUES,
    HistoricalInformationSetSearchDecisionReviewV1,
    HistoricalInformationSetSearchMetricsV1,
    HistoricalInformationSetSearchPreActualBuilder,
    HistoricalInformationSetSearchReviewSettingsV1,
    build_historical_information_set_search_decision_review_v1,
    build_historical_information_set_search_metrics_v1,
    build_historical_information_set_search_pre_actual_analysis_v1,
    build_serializable_historical_information_set_search_decision_v1,
    build_serializable_historical_information_set_search_metrics_v1,
    build_serializable_historical_information_set_search_review_settings_v1,
)
from skat_ai.information_set_search_comparison import METHOD_NOT_AVAILABLE
from skat_ai.information_set_search_contracts import INFORMATION_SET_SEARCH_STATUSES
from skat_ai.rules import GAME_TYPES
from skat_ai.search_budget_profiles import EVALUATION_SEARCH_BUDGET_PROFILE
from skat_ai.simulation import DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT
from skat_ai.training_dataset import (
    TRAINING_DATASET_SCHEMA_VERSION,
    TRAINING_TARGET,
    TrainingDatasetInput,
)

INFORMATION_SET_SEARCH_EVALUATION_VERSION = 1
INFORMATION_SET_SEARCH_EVALUATION_METHOD = (
    "information_set_search_vs_same_selection_pimc_and_immediate_v1"
)
INFORMATION_SET_SEARCH_EVALUATION_POLICY = (
    "deterministic_dataset_prefix_without_training"
)
DEFAULT_INFORMATION_SET_SEARCH_EVALUATION_PARTITIONS = ("validation", "test")
DEFAULT_INFORMATION_SET_SEARCH_EVALUATION_PROFILE = EVALUATION_SEARCH_BUDGET_PROFILE
INFORMATION_SET_SEARCH_EVALUATION_IMMEDIATE_BASE_RANDOM_SEED = 0


HistoricalSummaryBuilder = Callable[[HistoricalGameRecord], dict[str, Any]]
HistoricalSnapshotBuilder = Callable[
    [dict[str, Any]], HistoricalDecisionSnapshotSummary
]


@dataclass(frozen=True, slots=True, kw_only=True)
class InformationSetSearchEvaluationSelectionV1:
    partitions: tuple[str, ...]
    max_decisions: int | None
    record_count: int
    available_decision_count: int
    evaluated_decision_count: int
    decision_cap_reached: bool

    def __post_init__(self) -> None:
        if not self.partitions or any(
            partition not in CANONICAL_DATASET_PARTITIONS
            for partition in self.partitions
        ):
            raise ValueError("Evaluation selection requires supported partitions.")
        _validate_max_decisions(self.max_decisions)
        for field_name in (
            "record_count",
            "available_decision_count",
            "evaluated_decision_count",
        ):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer.")
        if self.evaluated_decision_count > self.available_decision_count:
            raise ValueError("Evaluated decisions cannot exceed available decisions.")
        if not isinstance(self.decision_cap_reached, bool):
            raise ValueError("decision_cap_reached must be a boolean.")


@dataclass(frozen=True, slots=True, kw_only=True)
class InformationSetSearchEvaluationRecordV1:
    record_id: str
    partition: str
    source_game_id: str
    source_decision_count: int
    decisions: tuple[HistoricalInformationSetSearchDecisionReviewV1, ...]

    @property
    def evaluated_decision_count(self) -> int:
        return len(self.decisions)


@dataclass(frozen=True, slots=True, kw_only=True)
class InformationSetSearchEvaluationBreakdownRowV1:
    value: str
    metrics: HistoricalInformationSetSearchMetricsV1


@dataclass(frozen=True, slots=True, kw_only=True)
class InformationSetSearchEvaluationBreakdownV1:
    output_name: str
    field_name: str
    rows: tuple[InformationSetSearchEvaluationBreakdownRowV1, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class InformationSetSearchEvaluationSummaryV1:
    schema_version: int
    evaluation_method: str
    source_dataset_id: str
    source_dataset_version: str
    source_training_dataset_schema_version: int
    source_feature_generation_version: int
    source_target: str
    source_partition_policy: DatasetPartitionPolicy | None
    settings: HistoricalInformationSetSearchReviewSettingsV1
    selection: InformationSetSearchEvaluationSelectionV1
    zero_decision_record_count: int
    metrics: HistoricalInformationSetSearchMetricsV1
    breakdowns: tuple[InformationSetSearchEvaluationBreakdownV1, ...]
    records: tuple[InformationSetSearchEvaluationRecordV1, ...]

    def __post_init__(self) -> None:
        if (
            isinstance(self.schema_version, bool)
            or not isinstance(self.schema_version, int)
            or self.schema_version != INFORMATION_SET_SEARCH_EVALUATION_VERSION
        ):
            raise ValueError("Unsupported information-set Search evaluation version.")
        if self.evaluation_method != INFORMATION_SET_SEARCH_EVALUATION_METHOD:
            raise ValueError("Unsupported information-set Search evaluation method.")
        if self.source_training_dataset_schema_version != (
            TRAINING_DATASET_SCHEMA_VERSION
        ):
            raise ValueError("Evaluation requires Training Dataset version 1.")
        if self.source_target != TRAINING_TARGET:
            raise ValueError("Evaluation target must remain actual_card_played.")
        if self.selection.record_count != len(self.records):
            raise ValueError("Evaluation record count does not reconcile.")
        if self.selection.evaluated_decision_count != self.metrics.decision_count:
            raise ValueError("Evaluation decision count does not reconcile.")
        if sum(record.evaluated_decision_count for record in self.records) != (
            self.metrics.decision_count
        ):
            raise ValueError("Evaluation record decisions do not reconcile.")


def _canonicalize_partitions(partitions: Iterable[str]) -> tuple[str, ...]:
    if isinstance(partitions, (str, bytes)):
        raise ValueError("partitions must be a non-empty iterable of names.")
    try:
        requested = tuple(partitions)
    except TypeError as exc:
        raise ValueError("partitions must be a non-empty iterable of names.") from exc
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


def _evaluation_field(
    partition: str,
    decision: HistoricalInformationSetSearchDecisionReviewV1,
    field_name: str,
) -> str:
    if field_name == "partition":
        return partition
    if field_name == "status":
        return decision.information_set_status
    if field_name == "coverage":
        return decision.world_coverage
    if field_name == "agreement":
        return decision.recommendation_agreement
    attribute = {
        "role": "acting_role",
        "seat": "acting_seat",
        "phase": "decision_phase",
    }.get(field_name, field_name)
    value = getattr(decision, attribute)
    if not isinstance(value, str):
        raise ValueError("Evaluation breakdown fields must be strings.")
    return value


def _breakdown(
    rows: tuple[tuple[str, HistoricalInformationSetSearchDecisionReviewV1], ...],
    *,
    output_name: str,
    field_name: str,
    preferred_order: tuple[str, ...],
) -> InformationSetSearchEvaluationBreakdownV1:
    observed = tuple(
        _evaluation_field(partition, decision, field_name)
        for partition, decision in rows
    )
    extras = tuple(sorted(set(observed) - set(preferred_order)))
    values = tuple(
        value for value in (*preferred_order, *extras) if value in observed
    )
    return InformationSetSearchEvaluationBreakdownV1(
        output_name=output_name,
        field_name=field_name,
        rows=tuple(
            InformationSetSearchEvaluationBreakdownRowV1(
                value=value,
                metrics=build_historical_information_set_search_metrics_v1(
                    tuple(
                        decision
                        for partition, decision in rows
                        if _evaluation_field(partition, decision, field_name)
                        == value
                    )
                ),
            )
            for value in values
        ),
    )


def _build_breakdowns(
    rows: tuple[tuple[str, HistoricalInformationSetSearchDecisionReviewV1], ...],
) -> tuple[InformationSetSearchEvaluationBreakdownV1, ...]:
    return (
        _breakdown(
            rows,
            output_name="by_partition",
            field_name="partition",
            preferred_order=CANONICAL_DATASET_PARTITIONS,
        ),
        _breakdown(
            rows,
            output_name="by_contract",
            field_name="contract",
            preferred_order=tuple(GAME_TYPES),
        ),
        _breakdown(
            rows,
            output_name="by_role",
            field_name="role",
            preferred_order=HISTORICAL_ROLES,
        ),
        _breakdown(
            rows,
            output_name="by_seat",
            field_name="seat",
            preferred_order=HISTORICAL_SEATS,
        ),
        _breakdown(
            rows,
            output_name="by_phase",
            field_name="phase",
            preferred_order=DECISION_PHASES,
        ),
        _breakdown(
            rows,
            output_name="by_status",
            field_name="status",
            preferred_order=(*INFORMATION_SET_SEARCH_STATUSES, METHOD_NOT_AVAILABLE),
        ),
        _breakdown(
            rows,
            output_name="by_coverage",
            field_name="coverage",
            preferred_order=WORLD_COVERAGE_VALUES,
        ),
        _breakdown(
            rows,
            output_name="by_recommendation_agreement",
            field_name="agreement",
            preferred_order=RECOMMENDATION_AGREEMENT_VALUES,
        ),
    )


def build_information_set_search_evaluation_v1(
    dataset: TrainingDatasetInput,
    base_search_seed: int,
    *,
    pre_actual_analysis_builder: HistoricalInformationSetSearchPreActualBuilder = (
        build_historical_information_set_search_pre_actual_analysis_v1
    ),
    partitions: Iterable[str] = DEFAULT_INFORMATION_SET_SEARCH_EVALUATION_PARTITIONS,
    search_budget_profile: str = DEFAULT_INFORMATION_SET_SEARCH_EVALUATION_PROFILE,
    max_decisions: int | None = None,
    immediate_sample_count: int = DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT,
    immediate_base_random_seed: int = (
        INFORMATION_SET_SEARCH_EVALUATION_IMMEDIATE_BASE_RANDOM_SEED
    ),
    historical_summary_builder: HistoricalSummaryBuilder = (
        build_historical_game_summary
    ),
    snapshot_builder: HistoricalSnapshotBuilder = build_historical_decision_snapshots,
) -> InformationSetSearchEvaluationSummaryV1:
    """Evaluates a stable selected Dataset prefix without training or Samples."""
    if not isinstance(dataset, TrainingDatasetInput):
        raise ValueError("dataset must be a TrainingDatasetInput.")
    if dataset.schema_version != TRAINING_DATASET_SCHEMA_VERSION:
        raise ValueError("Evaluation requires Training Dataset version 1.")
    if dataset.target != TRAINING_TARGET:
        raise ValueError("Evaluation target must remain actual_card_played.")
    selected_partitions = _canonicalize_partitions(partitions)
    _validate_max_decisions(max_decisions)
    selected_records = tuple(
        record
        for record in dataset.records
        if record.partition in selected_partitions
    )
    if not selected_records:
        raise ValueError("No dataset records match the selected partitions.")
    settings = HistoricalInformationSetSearchReviewSettingsV1(
        base_search_seed=base_search_seed,
        search_budget_profile=search_budget_profile,
        immediate_sample_count=immediate_sample_count,
        immediate_base_random_seed=immediate_base_random_seed,
    )

    records: list[InformationSetSearchEvaluationRecordV1] = []
    decision_rows: list[
        tuple[str, HistoricalInformationSetSearchDecisionReviewV1]
    ] = []
    available_decision_count = 0
    for record in selected_records:
        historical_summary = historical_summary_builder(record.historical_game)
        snapshots = snapshot_builder(historical_summary)
        source_decision_count = snapshots.snapshot_count
        if source_decision_count != snapshots.cardinality.expected_snapshot_count:
            raise ValueError(
                f"Evaluation record '{record.record_id}' snapshot count does not reconcile."
            )
        available_decision_count += source_decision_count
        remaining_capacity = (
            source_decision_count
            if max_decisions is None
            else max(0, max_decisions - len(decision_rows))
        )
        selected_snapshots = snapshots.snapshots[:remaining_capacity]
        decisions = tuple(
            build_historical_information_set_search_decision_review_v1(
                snapshot,
                record.historical_game,
                settings,
                pre_actual_analysis_builder=pre_actual_analysis_builder,
                stable_game_identity=record.historical_game.game_id,
            )
            for snapshot in selected_snapshots
        )
        decision_rows.extend((record.partition, decision) for decision in decisions)
        records.append(
            InformationSetSearchEvaluationRecordV1(
                record_id=record.record_id,
                partition=record.partition,
                source_game_id=record.historical_game.game_id,
                source_decision_count=source_decision_count,
                decisions=decisions,
            )
        )

    immutable_rows = tuple(decision_rows)
    metrics = build_historical_information_set_search_metrics_v1(
        tuple(decision for _partition, decision in immutable_rows)
    )
    breakdowns = _build_breakdowns(immutable_rows)
    for breakdown in breakdowns:
        if sum(row.metrics.decision_count for row in breakdown.rows) != (
            metrics.decision_count
        ):
            raise ValueError(
                f"{breakdown.output_name} decision counts do not reconcile."
            )
    immutable_records = tuple(records)
    zero_decision_record_count = sum(
        record.source_decision_count == 0 for record in immutable_records
    )
    selection = InformationSetSearchEvaluationSelectionV1(
        partitions=selected_partitions,
        max_decisions=max_decisions,
        record_count=len(immutable_records),
        available_decision_count=available_decision_count,
        evaluated_decision_count=metrics.decision_count,
        decision_cap_reached=(
            max_decisions is not None
            and available_decision_count > metrics.decision_count
        ),
    )
    return InformationSetSearchEvaluationSummaryV1(
        schema_version=INFORMATION_SET_SEARCH_EVALUATION_VERSION,
        evaluation_method=INFORMATION_SET_SEARCH_EVALUATION_METHOD,
        source_dataset_id=dataset.dataset_id,
        source_dataset_version=dataset.dataset_version,
        source_training_dataset_schema_version=dataset.schema_version,
        source_feature_generation_version=dataset.feature_generation_version,
        source_target=dataset.target,
        source_partition_policy=dataset.partition_policy,
        settings=settings,
        selection=selection,
        zero_decision_record_count=zero_decision_record_count,
        metrics=metrics,
        breakdowns=breakdowns,
        records=immutable_records,
    )


def _serialize_source_dataset(
    summary: InformationSetSearchEvaluationSummaryV1,
) -> dict[str, Any]:
    result = {
        "dataset_id": summary.source_dataset_id,
        "dataset_version": summary.source_dataset_version,
        "training_dataset_schema_version": (
            summary.source_training_dataset_schema_version
        ),
        "feature_generation_version": summary.source_feature_generation_version,
        "target": summary.source_target,
    }
    if summary.source_partition_policy is not None:
        result["partition_policy"] = build_serializable_dataset_partition_policy(
            summary.source_partition_policy
        )
    return result


def build_serializable_information_set_search_evaluation_v1(
    summary: InformationSetSearchEvaluationSummaryV1,
) -> dict[str, Any]:
    if not isinstance(summary, InformationSetSearchEvaluationSummaryV1):
        raise ValueError("summary has the wrong type.")
    selection = summary.selection
    return {
        "schema_version": summary.schema_version,
        "evaluation_method": summary.evaluation_method,
        "source_dataset": _serialize_source_dataset(summary),
        "settings": (
            build_serializable_historical_information_set_search_review_settings_v1(
                summary.settings
            )
        ),
        "selection": {
            "partitions": list(selection.partitions),
            "max_decisions": selection.max_decisions,
            "record_count": selection.record_count,
            "available_decision_count": selection.available_decision_count,
            "evaluated_decision_count": selection.evaluated_decision_count,
            "decision_cap_reached": selection.decision_cap_reached,
        },
        "record_count": len(summary.records),
        "zero_decision_record_count": summary.zero_decision_record_count,
        "available_decision_count": selection.available_decision_count,
        **build_serializable_historical_information_set_search_metrics_v1(
            summary.metrics
        ),
        "breakdowns": {
            breakdown.output_name: [
                {
                    breakdown.field_name: row.value,
                    "metrics": (
                        build_serializable_historical_information_set_search_metrics_v1(
                            row.metrics
                        )
                    ),
                }
                for row in breakdown.rows
            ]
            for breakdown in summary.breakdowns
        },
        "records": [
            {
                "record_id": record.record_id,
                "partition": record.partition,
                "source_game_id": record.source_game_id,
                "source_decision_count": record.source_decision_count,
                "evaluated_decision_count": record.evaluated_decision_count,
                "decisions": [
                    build_serializable_historical_information_set_search_decision_v1(
                        decision
                    )
                    for decision in record.decisions
                ],
            }
            for record in summary.records
        ],
    }


def evaluate_information_set_search_dataset_v1(
    dataset: TrainingDatasetInput,
    base_search_seed: int,
    *,
    pre_actual_analysis_builder: HistoricalInformationSetSearchPreActualBuilder = (
        build_historical_information_set_search_pre_actual_analysis_v1
    ),
    partitions: Iterable[str] = DEFAULT_INFORMATION_SET_SEARCH_EVALUATION_PARTITIONS,
    search_budget_profile: str = DEFAULT_INFORMATION_SET_SEARCH_EVALUATION_PROFILE,
    max_decisions: int | None = None,
    immediate_sample_count: int = DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT,
    immediate_base_random_seed: int = (
        INFORMATION_SET_SEARCH_EVALUATION_IMMEDIATE_BASE_RANDOM_SEED
    ),
    historical_summary_builder: HistoricalSummaryBuilder = (
        build_historical_game_summary
    ),
    snapshot_builder: HistoricalSnapshotBuilder = build_historical_decision_snapshots,
) -> dict[str, Any]:
    """Application-friendly immutable-build plus fresh-serialization entry point."""
    summary = build_information_set_search_evaluation_v1(
        dataset,
        base_search_seed,
        pre_actual_analysis_builder=pre_actual_analysis_builder,
        partitions=partitions,
        search_budget_profile=search_budget_profile,
        max_decisions=max_decisions,
        immediate_sample_count=immediate_sample_count,
        immediate_base_random_seed=immediate_base_random_seed,
        historical_summary_builder=historical_summary_builder,
        snapshot_builder=snapshot_builder,
    )
    return build_serializable_information_set_search_evaluation_v1(summary)
