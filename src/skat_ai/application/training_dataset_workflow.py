from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from skat_ai.application.contracts import (
    ApplicationArtifact,
    TrainingDatasetApplicationOptions,
)
from skat_ai.bounded_search_evaluation import evaluate_bounded_search_dataset
from skat_ai.dataset_partition_audit import (
    audit_training_dataset_partitions,
    build_serializable_dataset_partition_audit,
    resolve_dataset_partition_audit_mode,
)
from skat_ai.historical_opponent_statistics import (
    aggregate_historical_opponent_statistics,
    build_exportable_opponent_statistics_input,
    build_historical_opponent_statistics_aggregation_summary,
)
from skat_ai.input_loader import build_training_dataset_from_document
from skat_ai.opponent_statistics import build_serializable_opponent_statistics_input
from skat_ai.rolling_opponent_policy_evaluation import (
    build_serializable_rolling_opponent_policy_evaluation,
    evaluate_rolling_opponent_policy_predictions,
)
from skat_ai.training_dataset import build_training_dataset_summary


@dataclass(frozen=True, slots=True)
class TrainingDatasetWorkflowDependencies:
    """Legacy patch seams for Training Dataset orchestration."""

    build_summary: Callable[..., Any] = build_training_dataset_summary
    resolve_partition_audit_mode: Callable[..., Any] = (
        resolve_dataset_partition_audit_mode
    )
    audit_partitions: Callable[..., Any] = audit_training_dataset_partitions
    serialize_partition_audit: Callable[..., Any] = (
        build_serializable_dataset_partition_audit
    )
    evaluate_rolling: Callable[..., Any] = (
        evaluate_rolling_opponent_policy_predictions
    )
    serialize_rolling: Callable[..., Any] = (
        build_serializable_rolling_opponent_policy_evaluation
    )
    evaluate_bounded_search: Callable[..., Any] = evaluate_bounded_search_dataset
    aggregate_statistics: Callable[..., Any] = (
        aggregate_historical_opponent_statistics
    )
    build_aggregation_summary: Callable[..., Any] = (
        build_historical_opponent_statistics_aggregation_summary
    )
    build_export_input: Callable[..., Any] = build_exportable_opponent_statistics_input
    serialize_export_input: Callable[..., Any] = (
        build_serializable_opponent_statistics_input
    )


_DEFAULT_DEPENDENCIES = TrainingDatasetWorkflowDependencies()


def execute_training_dataset_workflow(
    root_document: dict[str, Any],
    *,
    input_reference: str,
    options: TrainingDatasetApplicationOptions,
    provenance_collector: Any = None,
    dependencies: TrainingDatasetWorkflowDependencies = _DEFAULT_DEPENDENCIES,
) -> tuple[dict[str, Any], tuple[ApplicationArtifact, ...]]:
    """Builds one Dataset and executes exactly one selected operation."""
    dataset = build_training_dataset_from_document(
        root_document,
        validate_workflow=False,
    )
    if provenance_collector is not None:
        provenance_collector.capture_dataset(dataset)
    artifacts: tuple[ApplicationArtifact, ...] = ()

    if options.operation == "summary":
        result = {
            "input_file": input_reference,
            "training_dataset_summary": dependencies.build_summary(dataset),
        }
    elif options.operation == "partition_audit":
        effective_mode = dependencies.resolve_partition_audit_mode(
            dataset,
            options.partition_audit_mode,
        )
        audit = dependencies.audit_partitions(dataset, effective_mode)
        result = {
            "input_file": input_reference,
            "dataset_partition_audit_summary": (
                dependencies.serialize_partition_audit(audit)
            ),
        }
    elif options.operation == "rolling_opponent_policy_evaluation":
        evaluation = dependencies.evaluate_rolling(
            dataset,
            source_partitions=options.rolling_source_partitions,
            evaluation_partitions=options.rolling_evaluation_partitions,
        )
        result = {
            "input_file": input_reference,
            "rolling_opponent_policy_evaluation_summary": (
                dependencies.serialize_rolling(evaluation)
            ),
        }
    elif options.operation == "bounded_search_evaluation":
        result = {
            "input_file": input_reference,
            "bounded_search_evaluation_summary": dependencies.evaluate_bounded_search(
                dataset,
                base_search_seed=options.bounded_search_seed,
                partitions=options.bounded_search_partitions,
                search_budget_profile=options.bounded_search_budget_profile,
                max_decisions=options.bounded_search_max_decisions,
            ),
        }
    else:
        aggregation = dependencies.aggregate_statistics(
            dataset,
            included_partitions=options.aggregation_included_partitions,
            before=options.aggregation_before,
        )
        result = {
            "input_file": input_reference,
            "historical_opponent_statistics_aggregation_summary": (
                dependencies.build_aggregation_summary(aggregation)
            ),
        }
        if options.export_opponent_statistics:
            export_input = dependencies.build_export_input(aggregation)
            artifacts = (
                ApplicationArtifact(
                    name="opponent_statistics_input",
                    document=dependencies.serialize_export_input(export_input),
                ),
            )

    return result, artifacts
