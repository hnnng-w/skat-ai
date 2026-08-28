from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from skatmind.fixed_three_player_historical_list_aggregation import (
    build_fixed_three_player_historical_list_aggregation,
    build_serializable_fixed_three_player_historical_list_aggregation,
)
from skatmind.fixed_three_player_historical_list_comparison import (
    build_fixed_three_player_historical_list_comparison,
)
from skatmind.fixed_three_player_historical_list_comparison_summary import (
    build_serializable_fixed_three_player_historical_list_comparison,
)
from skatmind.input_loader import (
    build_fixed_three_player_historical_list_comparison_request_from_document,
    build_fixed_three_player_historical_list_request_from_document,
    build_opponent_statistics_from_document,
    build_training_dataset_preparation_request_from_document,
)
from skatmind.opponent_statistics import build_opponent_statistics_summary
from skatmind.training_dataset_preparation_workflow import (
    build_serializable_training_dataset_preparation_result,
    build_training_dataset_preparation_result,
)


@dataclass(frozen=True, slots=True)
class SimpleWorkflowDependencies:
    """Legacy patch seams for simple Root workflow execution."""

    build_preparation_result: Callable[..., Any] = (
        build_training_dataset_preparation_result
    )
    serialize_preparation_result: Callable[..., Any] = (
        build_serializable_training_dataset_preparation_result
    )
    build_statistics_summary: Callable[..., Any] = build_opponent_statistics_summary
    build_list_aggregation: Callable[..., Any] = (
        build_fixed_three_player_historical_list_aggregation
    )
    build_list_comparison: Callable[..., Any] = (
        build_fixed_three_player_historical_list_comparison
    )


_DEFAULT_DEPENDENCIES = SimpleWorkflowDependencies()


def execute_training_dataset_preparation_workflow(
    root_document: dict[str, Any],
    *,
    input_reference: str,
    provenance_collector: Any = None,
    dependencies: SimpleWorkflowDependencies = _DEFAULT_DEPENDENCIES,
) -> dict[str, Any]:
    """Executes automatic Training Dataset Preparation without transport I/O."""
    request = build_training_dataset_preparation_request_from_document(
        root_document,
        validate_workflow=False,
    )
    preparation_result = dependencies.build_preparation_result(request)
    if provenance_collector is not None:
        provenance_collector.capture(request, preparation_result)
    return {
        "input_file": input_reference,
        "training_dataset_preparation_summary": (
            dependencies.serialize_preparation_result(
                request,
                preparation_result,
            )
        ),
    }


def execute_opponent_statistics_workflow(
    root_document: dict[str, Any],
    *,
    input_reference: str,
    provenance_collector: Any = None,
    dependencies: SimpleWorkflowDependencies = _DEFAULT_DEPENDENCIES,
) -> dict[str, Any]:
    """Normalizes one Opponent Statistics document without transport I/O."""
    statistics_input = build_opponent_statistics_from_document(
        root_document,
        validate_workflow=False,
    )
    if provenance_collector is not None:
        provenance_collector.capture_input(statistics_input)
    return {
        "input_file": input_reference,
        "opponent_statistics_summary": dependencies.build_statistics_summary(
            statistics_input
        ),
    }


def execute_fixed_three_player_historical_list_workflow(
    root_document: dict[str, Any],
    *,
    input_reference: str,
    provenance_collector: Any = None,
    dependencies: SimpleWorkflowDependencies = _DEFAULT_DEPENDENCIES,
) -> dict[str, Any]:
    """Aggregates one complete historical 36-position list."""
    request = build_fixed_three_player_historical_list_request_from_document(
        root_document,
        validate_workflow=False,
    )
    aggregation = dependencies.build_list_aggregation(
        request.historical_list,
        lot_order=None if request.lot_order is None else list(request.lot_order),
    )
    if provenance_collector is not None:
        provenance_collector.capture(request, aggregation)
    return {
        "input_file": input_reference,
        "fixed_three_player_historical_list_summary": (
            build_serializable_fixed_three_player_historical_list_aggregation(
                aggregation
            )
        ),
    }


def execute_fixed_three_player_historical_list_comparison_workflow(
    root_document: dict[str, Any],
    *,
    input_reference: str,
    provenance_collector: Any = None,
    dependencies: SimpleWorkflowDependencies = _DEFAULT_DEPENDENCIES,
) -> dict[str, Any]:
    """Aggregates each source once and compares it with the first source."""
    request = build_fixed_three_player_historical_list_comparison_request_from_document(
        root_document,
        validate_workflow=False,
    )
    if provenance_collector is not None:
        provenance_collector.capture_request(request)
    aggregations = tuple(
        dependencies.build_list_aggregation(
            source.historical_list,
            lot_order=None if source.lot_order is None else list(source.lot_order),
        )
        for source in request.lists
    )
    comparison = dependencies.build_list_comparison(aggregations)
    return {
        "input_file": input_reference,
        "fixed_three_player_historical_list_comparison_summary": (
            build_serializable_fixed_three_player_historical_list_comparison(
                comparison
            )
        ),
    }
