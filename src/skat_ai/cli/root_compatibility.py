"""Legacy Root-module compatibility and Application dependency seams."""

import sys
from contextlib import contextmanager
from types import ModuleType
from typing import Any

from skat_ai.analysis_report import build_card_analysis_report, build_strategic_summary
from skat_ai.application.execution import ApplicationWorkflowDependencies
from skat_ai.application.historical_game_workflow import (
    HistoricalGameWorkflowDependencies,
)
from skat_ai.application.position_workflow import PositionWorkflowDependencies
from skat_ai.application.simple_workflows import SimpleWorkflowDependencies
from skat_ai.application.training_dataset_workflow import (
    TrainingDatasetWorkflowDependencies,
)
from skat_ai.bounded_search_evaluation import evaluate_bounded_search_dataset
from skat_ai.dataset_partition_audit import (
    audit_training_dataset_partitions,
    build_serializable_dataset_partition_audit,
    resolve_dataset_partition_audit_mode,
)
from skat_ai.errors import SkatAICliUsageError
from skat_ai.fixed_three_player_historical_list_aggregation import (
    build_fixed_three_player_historical_list_aggregation,
)
from skat_ai.fixed_three_player_historical_list_comparison import (
    build_fixed_three_player_historical_list_comparison,
)
from skat_ai.historical_decision_snapshot import build_historical_decision_snapshots
from skat_ai.historical_game_review import build_historical_game_review_summary
from skat_ai.historical_information_set_search_review import (
    build_historical_information_set_search_review_summary_v1,
)
from skat_ai.historical_opponent_statistics import (
    aggregate_historical_opponent_statistics,
    build_exportable_opponent_statistics_input,
    build_historical_opponent_statistics_aggregation_summary,
)
from skat_ai.historical_search_review import build_historical_search_review_summary
from skat_ai.information_set_search_evaluation import (
    evaluate_information_set_search_dataset_v1,
)
from skat_ai.input_loader import get_input_workflow, load_opponent_statistics_from_json
from skat_ai.multi_step_simulation import simulate_multiple_steps
from skat_ai.opponent_statistics import (
    build_opponent_statistics_summary,
    build_serializable_opponent_statistics_input,
)
from skat_ai.policy_comparison import compare_multi_step_policies
from skat_ai.recommender import recommend_card_by_expected_value
from skat_ai.replay_coaching_report import (
    build_historical_replay_coaching_public_summaries,
)
from skat_ai.rolling_opponent_policy_evaluation import (
    build_serializable_rolling_opponent_policy_evaluation,
    evaluate_rolling_opponent_policy_predictions,
)
from skat_ai.training_dataset import build_training_dataset_summary
from skat_ai.training_dataset_preparation_workflow import (
    build_serializable_training_dataset_preparation_result,
    build_training_dataset_preparation_result,
)

CliUsageError = SkatAICliUsageError


def build_unavailable_strategic_summary(reason: str) -> str:
    """Builds a readable strategic summary for unavailable Immediate Analysis."""
    return f"Strategic summary: {reason}"


# These ordered identities are compatibility patch points through v1.0.0.
_LEGACY_PATCH_POINT_FUNCTIONS = (
    aggregate_historical_opponent_statistics,
    build_opponent_statistics_summary,
    build_training_dataset_summary,
    evaluate_rolling_opponent_policy_predictions,
    load_opponent_statistics_from_json,
)

_DEFAULT_LEGACY_PATCH_VALUES = {
    "aggregate_historical_opponent_statistics": aggregate_historical_opponent_statistics,
    "audit_training_dataset_partitions": audit_training_dataset_partitions,
    "build_card_analysis_report": build_card_analysis_report,
    "build_exportable_opponent_statistics_input": build_exportable_opponent_statistics_input,
    "build_fixed_three_player_historical_list_aggregation": (
        build_fixed_three_player_historical_list_aggregation
    ),
    "build_fixed_three_player_historical_list_comparison": (
        build_fixed_three_player_historical_list_comparison
    ),
    "build_historical_decision_snapshots": build_historical_decision_snapshots,
    "build_historical_game_review_summary": build_historical_game_review_summary,
    "build_historical_information_set_search_review_summary_v1": (
        build_historical_information_set_search_review_summary_v1
    ),
    "build_historical_opponent_statistics_aggregation_summary": (
        build_historical_opponent_statistics_aggregation_summary
    ),
    "build_historical_replay_coaching_public_summaries": (
        build_historical_replay_coaching_public_summaries
    ),
    "build_historical_search_review_summary": build_historical_search_review_summary,
    "build_opponent_statistics_summary": build_opponent_statistics_summary,
    "build_serializable_dataset_partition_audit": (build_serializable_dataset_partition_audit),
    "build_serializable_opponent_statistics_input": (build_serializable_opponent_statistics_input),
    "build_serializable_rolling_opponent_policy_evaluation": (
        build_serializable_rolling_opponent_policy_evaluation
    ),
    "build_serializable_training_dataset_preparation_result": (
        build_serializable_training_dataset_preparation_result
    ),
    "build_strategic_summary": build_strategic_summary,
    "build_training_dataset_preparation_result": (build_training_dataset_preparation_result),
    "build_training_dataset_summary": build_training_dataset_summary,
    "compare_multi_step_policies": compare_multi_step_policies,
    "evaluate_bounded_search_dataset": evaluate_bounded_search_dataset,
    "evaluate_information_set_search_dataset_v1": (evaluate_information_set_search_dataset_v1),
    "evaluate_rolling_opponent_policy_predictions": (evaluate_rolling_opponent_policy_predictions),
    "get_input_workflow": get_input_workflow,
    "load_opponent_statistics_from_json": load_opponent_statistics_from_json,
    "recommend_card_by_expected_value": recommend_card_by_expected_value,
    "resolve_dataset_partition_audit_mode": resolve_dataset_partition_audit_mode,
    "simulate_multiple_steps": simulate_multiple_steps,
}

_active_legacy_patch_namespace: ModuleType | None = None


@contextmanager
def legacy_patch_namespace(namespace: ModuleType):
    """Temporarily resolves established compatibility seams from Root main.py."""
    global _active_legacy_patch_namespace
    previous = _active_legacy_patch_namespace
    facade = sys.modules.get("skat_ai.cli.execution")
    previous_facade = (
        getattr(facade, "_active_legacy_patch_namespace", None) if facade is not None else None
    )
    _active_legacy_patch_namespace = namespace
    if facade is not None:
        facade._active_legacy_patch_namespace = namespace
    try:
        yield
    finally:
        _active_legacy_patch_namespace = previous
        if facade is not None:
            facade._active_legacy_patch_namespace = previous_facade


def _has_active_legacy_patch_namespace() -> bool:
    return _active_legacy_patch_namespace is not None


def _facade_value(name: str, default: Any = None) -> Any:
    facade = sys.modules.get("skat_ai.cli.execution")
    if facade is not None and hasattr(facade, name):
        return getattr(facade, name)
    if default is not None:
        return default
    return globals()[name]


def _legacy_patch_value(name: str):
    if _active_legacy_patch_namespace is not None:
        return getattr(_active_legacy_patch_namespace, name)
    if name in _DEFAULT_LEGACY_PATCH_VALUES:
        return _DEFAULT_LEGACY_PATCH_VALUES[name]
    return _facade_value(name)


def build_legacy_application_dependencies() -> ApplicationWorkflowDependencies:
    """Preserves established Root-module monkeypatch seams for CLI adapters."""
    dependency = _legacy_patch_value
    return ApplicationWorkflowDependencies(
        position=PositionWorkflowDependencies(
            immediate_recommender=dependency("recommend_card_by_expected_value"),
            report_builder=dependency("build_card_analysis_report"),
            strategic_summary_builder=dependency("build_strategic_summary"),
            unavailable_summary_builder=dependency("build_unavailable_strategic_summary"),
            multi_step_simulator=dependency("simulate_multiple_steps"),
            policy_comparator=dependency("compare_multi_step_policies"),
        ),
        historical_game=HistoricalGameWorkflowDependencies(
            build_snapshots=dependency("build_historical_decision_snapshots"),
            build_immediate_review=dependency("build_historical_game_review_summary"),
            build_search_review=dependency("build_historical_search_review_summary"),
            build_information_set_search_review=dependency(
                "build_historical_information_set_search_review_summary_v1"
            ),
            build_replay_coaching=dependency("build_historical_replay_coaching_public_summaries"),
        ),
        training_dataset=TrainingDatasetWorkflowDependencies(
            build_summary=dependency("build_training_dataset_summary"),
            resolve_partition_audit_mode=dependency("resolve_dataset_partition_audit_mode"),
            audit_partitions=dependency("audit_training_dataset_partitions"),
            serialize_partition_audit=dependency("build_serializable_dataset_partition_audit"),
            evaluate_rolling=dependency("evaluate_rolling_opponent_policy_predictions"),
            serialize_rolling=dependency("build_serializable_rolling_opponent_policy_evaluation"),
            evaluate_bounded_search=dependency("evaluate_bounded_search_dataset"),
            evaluate_information_set_search=dependency(
                "evaluate_information_set_search_dataset_v1"
            ),
            aggregate_statistics=dependency("aggregate_historical_opponent_statistics"),
            build_aggregation_summary=(
                dependency("build_historical_opponent_statistics_aggregation_summary")
            ),
            build_export_input=dependency("build_exportable_opponent_statistics_input"),
            serialize_export_input=dependency("build_serializable_opponent_statistics_input"),
        ),
        simple=SimpleWorkflowDependencies(
            build_preparation_result=dependency("build_training_dataset_preparation_result"),
            serialize_preparation_result=(
                dependency("build_serializable_training_dataset_preparation_result")
            ),
            build_statistics_summary=dependency("build_opponent_statistics_summary"),
            build_list_aggregation=(
                dependency("build_fixed_three_player_historical_list_aggregation")
            ),
            build_list_comparison=(
                dependency("build_fixed_three_player_historical_list_comparison")
            ),
        ),
    )
