import argparse
import sys
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType
from typing import Any

from skat_ai import __version__
from skat_ai.analysis_report import (
    build_card_analysis_report,
    build_strategic_summary,
    format_card_analysis_report,
)
from skat_ai.application.contracts import (
    ApplicationExecutionOptions,
    ApplicationExternalDocuments,
    HistoricalGameApplicationOptions,
    PositionAnalysisApplicationOptions,
    TrainingDatasetApplicationOptions,
)
from skat_ai.application.execution import (
    ApplicationWorkflowDependencies,
    build_application_invocation,
    execute_application_invocation,
)
from skat_ai.application.historical_game_workflow import (
    HistoricalGameWorkflowDependencies,
)
from skat_ai.application.position_workflow import (
    PositionWorkflowDependencies,
    build_position_analysis_result,
)
from skat_ai.application.simple_workflows import SimpleWorkflowDependencies
from skat_ai.application.training_dataset_workflow import (
    TrainingDatasetWorkflowDependencies,
)
from skat_ai.bounded_search_evaluation import (
    DEFAULT_BOUNDED_SEARCH_EVALUATION_PARTITIONS,
    evaluate_bounded_search_dataset,
)
from skat_ai.card_selection import (
    SEARCH_AWARE_MULTI_STEP_POLICIES,
    VALID_MULTI_STEP_POLICIES,
)
from skat_ai.dataset_partition_audit import (
    audit_training_dataset_partitions,
    build_serializable_dataset_partition_audit,
    resolve_dataset_partition_audit_mode,
)
from skat_ai.effective_opponent_policy import (
    EffectiveOpponentPolicySettings,
    build_effective_opponent_policy_settings,
)
from skat_ai.errors import (
    CLI_EXIT_CODE_FAILURE,
    CLI_EXIT_CODE_SUCCESS,
    CLI_EXIT_CODE_USAGE,
    SkatAICliUsageError,
    SkatAIWorkflowError,
)
from skat_ai.fixed_three_player_historical_list_aggregation import (
    build_fixed_three_player_historical_list_aggregation,
)
from skat_ai.fixed_three_player_historical_list_comparison import (
    build_fixed_three_player_historical_list_comparison,
)
from skat_ai.historical_decision_snapshot import build_historical_decision_snapshots
from skat_ai.historical_game_review import build_historical_game_review_summary
from skat_ai.historical_opponent_statistics import (
    aggregate_historical_opponent_statistics,
    build_exportable_opponent_statistics_input,
    build_historical_opponent_statistics_aggregation_summary,
)
from skat_ai.historical_search_review import build_historical_search_review_summary
from skat_ai.input_loader import (
    get_input_workflow,
    load_json_object,
    load_opponent_statistics_from_json,
    load_position_from_json,
)
from skat_ai.input_validation import MAX_SAMPLE_COUNT
from skat_ai.multi_step_simulation import simulate_multiple_steps
from skat_ai.objective_utility import calculate_expected_objective_utility
from skat_ai.opponent_policy import VALID_OPPONENT_CARD_POLICIES
from skat_ai.opponent_profile_application import EffectiveLiveOpponentProfiles
from skat_ai.opponent_statistics import (
    build_opponent_statistics_summary,
    build_serializable_opponent_statistics_input,
)
from skat_ai.output_writer import write_analysis_result_to_json
from skat_ai.policy_comparison import compare_multi_step_policies
from skat_ai.recommendation_workflow import (
    SEARCH_RECOMMENDATION_METHODS,
    RecommendationMethodConfiguration,
)
from skat_ai.recommender import recommend_card_by_expected_value
from skat_ai.replay_coaching_report import (
    build_historical_replay_coaching_public_summaries,
)
from skat_ai.rolling_opponent_policy_evaluation import (
    DEFAULT_EVALUATION_PARTITIONS,
    DEFAULT_SOURCE_PARTITIONS,
    build_serializable_rolling_opponent_policy_evaluation,
    evaluate_rolling_opponent_policy_predictions,
)
from skat_ai.search_budget_profiles import (
    EVALUATION_SEARCH_BUDGET_PROFILE,
    HISTORICAL_REVIEW_SEARCH_BUDGET_PROFILE,
    SEARCH_BUDGET_PROFILE_IDENTIFIERS,
)
from skat_ai.simulation import DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT
from skat_ai.training_dataset import build_training_dataset_summary
from skat_ai.training_dataset_preparation import TrainingDatasetPreparationRequest
from skat_ai.training_dataset_preparation_workflow import (
    TrainingDatasetPreparationResult,
    build_serializable_training_dataset_preparation_result,
    build_training_dataset_preparation_result,
)

INSTALLED_CLI_CONTRACT_VERSION = 1
INSTALLED_CLI_COMMAND = "skat-ai"
MODULE_CLI_COMMAND = "python -m skat_ai"
LEGACY_CLI_COMMAND = "python main.py"
CLI_INVOCATION_STYLES = ("installed", "module", "legacy")

IMMEDIATE_UNAVAILABLE_LOCAL_NOT_NEXT_REASON = (
    "Immediate analysis is unavailable because the local player is not next."
)
IMMEDIATE_UNAVAILABLE_GAME_COMPLETE_REASON = (
    "Immediate analysis is unavailable because the game is complete."
)
POST_GAME_REVIEW_UNAVAILABLE_REASON_TEXT = {
    "actual_card_played_not_provided": "the actual card was not provided.",
    "immediate_analysis_unavailable": "immediate analysis is unavailable for this position.",
    "expected_point_swing_difference_not_available": (
        "the expected point swing difference is not available."
    ),
}

# These names remain module-level compatibility patch points through v1.0.0.
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
    "build_historical_opponent_statistics_aggregation_summary": (
        build_historical_opponent_statistics_aggregation_summary
    ),
    "build_historical_replay_coaching_public_summaries": (
        build_historical_replay_coaching_public_summaries
    ),
    "build_historical_search_review_summary": build_historical_search_review_summary,
    "build_opponent_statistics_summary": build_opponent_statistics_summary,
    "build_serializable_dataset_partition_audit": (
        build_serializable_dataset_partition_audit
    ),
    "build_serializable_opponent_statistics_input": (
        build_serializable_opponent_statistics_input
    ),
    "build_serializable_rolling_opponent_policy_evaluation": (
        build_serializable_rolling_opponent_policy_evaluation
    ),
    "build_serializable_training_dataset_preparation_result": (
        build_serializable_training_dataset_preparation_result
    ),
    "build_strategic_summary": build_strategic_summary,
    "build_training_dataset_preparation_result": (
        build_training_dataset_preparation_result
    ),
    "build_training_dataset_summary": build_training_dataset_summary,
    "compare_multi_step_policies": compare_multi_step_policies,
    "evaluate_bounded_search_dataset": evaluate_bounded_search_dataset,
    "evaluate_rolling_opponent_policy_predictions": (
        evaluate_rolling_opponent_policy_predictions
    ),
    "get_input_workflow": get_input_workflow,
    "load_opponent_statistics_from_json": load_opponent_statistics_from_json,
    "recommend_card_by_expected_value": recommend_card_by_expected_value,
    "resolve_dataset_partition_audit_mode": resolve_dataset_partition_audit_mode,
    "simulate_multiple_steps": simulate_multiple_steps,
}


CliUsageError = SkatAICliUsageError

_active_legacy_patch_namespace: ModuleType | None = None


@contextmanager
def legacy_patch_namespace(namespace: ModuleType):
    """Temporarily resolves established compatibility seams from Root main.py."""
    global _active_legacy_patch_namespace
    previous = _active_legacy_patch_namespace
    _active_legacy_patch_namespace = namespace
    try:
        yield
    finally:
        _active_legacy_patch_namespace = previous


def _legacy_patch_value(name: str):
    if _active_legacy_patch_namespace is not None:
        return getattr(_active_legacy_patch_namespace, name)
    return _DEFAULT_LEGACY_PATCH_VALUES.get(name, globals()[name])


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
            build_replay_coaching=dependency(
                "build_historical_replay_coaching_public_summaries"
            ),
        ),
        training_dataset=TrainingDatasetWorkflowDependencies(
            build_summary=dependency("build_training_dataset_summary"),
            resolve_partition_audit_mode=dependency("resolve_dataset_partition_audit_mode"),
            audit_partitions=dependency("audit_training_dataset_partitions"),
            serialize_partition_audit=dependency(
                "build_serializable_dataset_partition_audit"
            ),
            evaluate_rolling=dependency("evaluate_rolling_opponent_policy_predictions"),
            serialize_rolling=dependency(
                "build_serializable_rolling_opponent_policy_evaluation"
            ),
            evaluate_bounded_search=dependency("evaluate_bounded_search_dataset"),
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


def execute_legacy_application(
    root_document: dict[str, Any],
    *,
    input_reference: str,
    options: ApplicationExecutionOptions | None = None,
    external_documents: ApplicationExternalDocuments | None = None,
    include_provenance: bool = False,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """Executes one Root document and thaws its result and artifacts for transport."""
    invocation = build_application_invocation(
        root_document,
        input_reference=input_reference,
        options=options,
        external_documents=external_documents,
    )
    execution = execute_application_invocation(
        invocation,
        dependencies=build_legacy_application_dependencies(),
    )
    if include_provenance:
        from skat_ai.api.v1.schema_validation import validate_output_document
        from skat_ai.public_field_provenance import attach_public_field_provenance

        result, _public_provenance = attach_public_field_provenance(execution)
        validate_output_document(result)
    else:
        result = execution.result.to_dict()["document"]
    if not isinstance(result, dict):
        raise ValueError("Application result document must be an object.")
    artifacts = {artifact.name: artifact.to_dict() for artifact in execution.artifacts}
    return result, artifacts


def print_field_provenance_summary(result: dict[str, Any]) -> None:
    """Prints aggregate public provenance status without field-level detail."""
    bundle = result.get("field_provenance")
    if not isinstance(bundle, dict):
        return
    result_attachment = bundle["result"]
    coverage = result_attachment["coverage_summary"]
    attachments = [
        result_attachment,
        *[artifact["attachment"] for artifact in bundle["artifacts"]],
    ]
    redacted = any(
        "private_dependencies_redacted" in attachment["ledger"]["limitations"]
        for attachment in attachments
    )
    covered = coverage["provenanced_path_count"] + coverage["exempted_path_count"]
    print()
    print("Field Provenance")
    print("Version:", bundle["provenance_version"])
    print("Status:", result_attachment["ledger"]["status"])
    print("Result attachment:", result_attachment["attachment_name"])
    print("Covered leaves:", f"{covered}/{coverage['leaf_path_count']}")
    print("Private dependencies redacted:", "yes" if redacted else "no")
    print("Artifact attachment count:", len(bundle["artifacts"]))


def load_external_opponent_statistics_document(
    file_path: str,
) -> dict[str, Any]:
    """Loads one external statistics file through the established CLI seam."""
    statistics_input = _legacy_patch_value("load_opponent_statistics_from_json")(
        file_path
    )
    return _legacy_patch_value("build_serializable_opponent_statistics_input")(
        statistics_input
    )


def get_immediate_unavailable_reason(
    state_next_player: str,
    game_end_reason: str,
    has_game_shortening: bool = False,
) -> str | None:
    """Returns why Immediate Analysis is unavailable, if it is unavailable."""
    if game_end_reason != "not_ended" or has_game_shortening:
        return IMMEDIATE_UNAVAILABLE_GAME_COMPLETE_REASON

    if state_next_player != "me":
        return IMMEDIATE_UNAVAILABLE_LOCAL_NOT_NEXT_REASON

    return None


def build_unavailable_strategic_summary(reason: str) -> str:
    """Builds a readable strategic summary for unavailable Immediate Analysis."""
    return f"Strategic summary: {reason}"


def apply_cli_overrides(
    settings: dict[str, Any],
    sample_count: int | None,
    random_seed: int | None,
    opponent_strategy: str | None,
) -> dict[str, Any]:
    """
    Applies optional command-line overrides to simulation settings.
    """
    updated_settings = settings.copy()

    if sample_count is not None:
        updated_settings["sample_count"] = sample_count

    if random_seed is not None:
        updated_settings["random_seed"] = random_seed

    if opponent_strategy == "basic":
        updated_settings["use_basic_opponent_strategy"] = True

    if opponent_strategy == "random":
        updated_settings["use_basic_opponent_strategy"] = False

    return updated_settings


def apply_profile_preset_cli_overrides(
    profile_preset_settings: dict[str, bool],
    use_profile_presets: bool = False,
) -> dict[str, bool]:
    """
    Applies CLI overrides to profile-preset settings.
    """
    updated_settings = profile_preset_settings.copy()

    if use_profile_presets:
        updated_settings["use_profile_presets"] = True

    return updated_settings


def build_effective_opponent_policy_settings_for_analysis(
    data: dict[str, Any],
    analysis_metadata: Any,
    opponent_policy_preset_override: str | None = None,
    opponent_lead_policy_override: str | None = None,
    opponent_response_policy_override: str | None = None,
    use_profile_presets_override: bool = False,
    left_opponent_lead_policy_override: str | None = None,
    left_opponent_response_policy_override: str | None = None,
    right_opponent_lead_policy_override: str | None = None,
    right_opponent_response_policy_override: str | None = None,
    effective_live_profiles: EffectiveLiveOpponentProfiles | None = None,
) -> EffectiveOpponentPolicySettings:
    """
    Builds shared effective opponent policy settings for one analysis invocation.
    """
    return build_effective_opponent_policy_settings(
        data=data,
        left_player_profile=(
            effective_live_profiles.left
            if effective_live_profiles is not None
            else analysis_metadata.left_player_profile
        ),
        right_player_profile=(
            effective_live_profiles.right
            if effective_live_profiles is not None
            else analysis_metadata.right_player_profile
        ),
        opponent_policy_preset_override=opponent_policy_preset_override,
        opponent_lead_policy_override=opponent_lead_policy_override,
        opponent_response_policy_override=opponent_response_policy_override,
        use_profile_presets_override=use_profile_presets_override,
        left_opponent_lead_policy_override=left_opponent_lead_policy_override,
        left_opponent_response_policy_override=left_opponent_response_policy_override,
        right_opponent_lead_policy_override=right_opponent_lead_policy_override,
        right_opponent_response_policy_override=right_opponent_response_policy_override,
    )


def build_global_opponent_policy_settings(
    effective_settings: EffectiveOpponentPolicySettings,
) -> dict[str, str]:
    """Builds the existing global opponent-policy output shape."""
    return {
        "opponent_lead_policy": effective_settings.global_lead_policy,
        "opponent_response_policy": effective_settings.global_response_policy,
    }


def build_left_opponent_policy_settings(
    effective_settings: EffectiveOpponentPolicySettings,
) -> dict[str, str]:
    """Builds the existing left-opponent policy output shape."""
    return {
        "opponent_lead_policy": effective_settings.left_lead_policy,
        "opponent_response_policy": effective_settings.left_response_policy,
    }


def build_right_opponent_policy_settings(
    effective_settings: EffectiveOpponentPolicySettings,
) -> dict[str, str]:
    """Builds the existing right-opponent policy output shape."""
    return {
        "opponent_lead_policy": effective_settings.right_lead_policy,
        "opponent_response_policy": effective_settings.right_response_policy,
    }


def resolve_multi_step_card_selection_policy(
    explicit_policy: str | None,
    recommendation_configuration: RecommendationMethodConfiguration,
) -> str:
    """Resolves CLI policy omission and explicit Search-method precedence."""
    configured_search_method = (
        recommendation_configuration.requested_method
        if recommendation_configuration.requested_method in SEARCH_RECOMMENDATION_METHODS
        else None
    )
    if configured_search_method is not None:
        if explicit_policy is not None and explicit_policy != configured_search_method:
            raise ValueError(
                "Explicit --card-policy conflicts with the configured Search "
                f"recommendation method {configured_search_method}."
            )
        return configured_search_method
    if explicit_policy in SEARCH_AWARE_MULTI_STEP_POLICIES:
        raise ValueError(
            "A Search-aware --card-policy requires matching recommendation_method "
            "and bounded_search_settings."
        )
    return explicit_policy or "first_legal"


def build_analysis_result(
    file_path: str,
    sample_count_override: int | None = None,
    random_seed_override: int | None = None,
    opponent_strategy_override: str | None = None,
    left_opponent_lead_policy_override: str | None = None,
    left_opponent_response_policy_override: str | None = None,
    right_opponent_lead_policy_override: str | None = None,
    right_opponent_response_policy_override: str | None = None,
    opponent_policy_preset_override: str | None = None,
    opponent_lead_policy_override: str | None = None,
    opponent_response_policy_override: str | None = None,
    use_profile_presets_override: bool = False,
    effective_opponent_policy_settings: EffectiveOpponentPolicySettings | None = None,
    opponent_profile_application_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Builds the full analysis result as a structured dictionary.
    """
    data = load_position_from_json(file_path)
    return build_position_analysis_result(
        data,
        input_reference=file_path,
        options=PositionAnalysisApplicationOptions(
            sample_count_override=sample_count_override,
            random_seed_override=random_seed_override,
            opponent_strategy_override=opponent_strategy_override,
            left_opponent_lead_policy_override=(
                left_opponent_lead_policy_override
            ),
            left_opponent_response_policy_override=(
                left_opponent_response_policy_override
            ),
            right_opponent_lead_policy_override=(
                right_opponent_lead_policy_override
            ),
            right_opponent_response_policy_override=(
                right_opponent_response_policy_override
            ),
            opponent_policy_preset_override=opponent_policy_preset_override,
            opponent_lead_policy_override=opponent_lead_policy_override,
            opponent_response_policy_override=opponent_response_policy_override,
            use_profile_presets_override=use_profile_presets_override,
        ),
        effective_opponent_policy_settings=effective_opponent_policy_settings,
        opponent_profile_application_summary=opponent_profile_application_summary,
        dependencies=build_legacy_application_dependencies().position,
    )


def format_decision_factors(summary: dict[str, object]) -> str:
    """Formats post-game review decision factors for CLI output."""
    decision_factors = summary.get("decision_factors", [])

    if not isinstance(decision_factors, list):
        return str(decision_factors)

    return ", ".join(str(factor) for factor in decision_factors)


def format_optional_cli_value(value: object) -> str:
    """Formats optional values for human-readable CLI output."""
    if value is None:
        return "not available"

    return str(value)


def format_post_game_review_unavailable_reason(reason: object) -> str:
    """Formats stable post-game review reason codes for human-readable CLI output."""
    reason_text = str(reason)

    return POST_GAME_REVIEW_UNAVAILABLE_REASON_TEXT.get(
        reason_text,
        reason_text.replace("_", " "),
    )


def print_hidden_card_inference_summary(summary: dict[str, Any] | None) -> None:
    """Prints bounded public inference diagnostics without private assignments."""
    if summary is None:
        return
    print("Hidden-card inference: applied")
    void_descriptions = [
        f"{item['player']} is void in "
        f"{', '.join(item['forbidden_effective_categories']).title()}"
        for item in summary["confirmed_voids"]
    ]
    print("Confirmed evidence:", "; ".join(void_descriptions))
    print("Compatible hidden worlds:", summary["compatible_world_count"])
    estimates = summary["ownership_estimates"]
    if estimates:
        highest = max(
            estimates,
            key=lambda item: item["ownership_probability"][item["most_likely_owner"]],
        )
        probability = highest["ownership_probability"][highest["most_likely_owner"]]
        print(
            "Highest bounded estimate:",
            f"{highest['card']} -> {highest['most_likely_owner']} "
            f"({probability:.0%}, {highest['confidence']})",
        )


def is_null_review_result(result: dict[str, object]) -> bool:
    """Returns whether the CLI review output should use Null objective wording."""
    position = result.get("position")

    return isinstance(position, dict) and position.get("game_type") == "null"


def get_analysis_report_row_for_cli(
    result: dict[str, object],
    card: object,
) -> dict[str, object] | None:
    """Returns an analysis-report row for CLI-only presentation calculations."""
    analysis_report = result.get("analysis_report")

    if not isinstance(card, str) or not isinstance(analysis_report, list):
        return None

    for row in analysis_report:
        if isinstance(row, dict) and row.get("card") == card:
            return row

    return None


def calculate_missed_null_objective_gap_for_cli(
    result: dict[str, object],
    summary: dict[str, object],
) -> float | None:
    """Calculates the displayed Null objective gap without changing JSON output."""
    position = result.get("position")
    game_value_summary = result.get("game_value_summary")

    if not isinstance(position, dict) or not isinstance(game_value_summary, dict):
        return None

    actual_row = get_analysis_report_row_for_cli(
        result=result,
        card=summary.get("actual_card_played"),
    )
    recommended_row = get_analysis_report_row_for_cli(
        result=result,
        card=summary.get("recommended_card"),
    )

    if actual_row is None or recommended_row is None:
        return None

    try:
        actual_objective_utility = calculate_expected_objective_utility(
            game_type="null",
            player_role=str(position["player_role"]),
            value=actual_row,
        )
        recommended_objective_utility = calculate_expected_objective_utility(
            game_type="null",
            player_role=str(position["player_role"]),
            value=recommended_row,
        )
        game_value = float(game_value_summary["game_value"])
    except (KeyError, TypeError, ValueError):
        return None

    return max(
        0.0,
        (recommended_objective_utility - actual_objective_utility) * game_value,
    )


def print_post_game_review_rank_summary(summary: dict[str, object]) -> None:
    """Prints concise rank and better-alternative wording for review output."""
    candidate_count = format_optional_cli_value(summary.get("candidate_count"))
    actual_rank = format_optional_cli_value(summary.get("actual_card_rank"))
    recommended_rank = format_optional_cli_value(summary.get("recommended_card_rank"))
    actual_rank_text = actual_rank
    recommended_rank_text = recommended_rank

    if summary.get("actual_card_rank") is not None:
        actual_rank_text = f"{actual_rank} of {candidate_count}"

    if summary.get("recommended_card_rank") is not None:
        recommended_rank_text = f"{recommended_rank} of {candidate_count}"

    print(
        "Review ranks: "
        f"actual {actual_rank_text}; "
        f"recommended {recommended_rank_text}; "
        f"better alternatives {format_optional_cli_value(summary.get('better_card_count'))}."
    )

    better_card_count = summary.get("better_card_count")

    if better_card_count is None:
        print("Better alternatives: not available.")
        return

    if better_card_count == 0:
        print("Actual card is best-ranked by the review objective.")
        return

    suffix = "" if better_card_count == 1 else "s"
    print(
        f"Actual card has {better_card_count} better alternative{suffix} by the review objective."
    )


def print_post_game_review_value_summary(
    result: dict[str, object],
    summary: dict[str, object],
) -> None:
    """Prints point or objective-gap wording for post-game review output."""
    actual_expected_point_swing = float(summary["actual_expected_point_swing"])
    recommended_expected_point_swing = float(summary["recommended_expected_point_swing"])
    expected_point_swing_difference = float(summary["expected_point_swing_difference"])

    if is_null_review_result(result):
        missed_objective_gap = calculate_missed_null_objective_gap_for_cli(
            result=result,
            summary=summary,
        )
        missed_objective_gap_text = (
            format(missed_objective_gap, ".2f") if missed_objective_gap is not None else None
        )
        print("Objective basis: Null contract objective, not raw card points.")
        print(f"Actual card-point swing (informational): {actual_expected_point_swing:.2f}")
        print(
            f"Recommended card-point swing (informational): {recommended_expected_point_swing:.2f}"
        )
        print(f"Card-point swing difference (informational): {expected_point_swing_difference:.2f}")
        print(f"Missed Null objective gap: {format_optional_cli_value(missed_objective_gap_text)}")
        return

    print(f"Actual expected point swing: {actual_expected_point_swing:.2f}")
    print(f"Recommended expected point swing: {recommended_expected_point_swing:.2f}")
    print(f"Missed expected point swing: {max(0.0, expected_point_swing_difference):.2f}")


def print_post_game_review_summary(result: dict[str, object]) -> None:
    """Prints the post-game review summary for human-readable CLI output."""
    summary = result.get("post_game_review_summary")

    if not isinstance(summary, dict):
        return

    print()
    print("Post-game review summary")

    decision_factors = format_decision_factors(summary)
    decision_explanation = summary.get("decision_explanation", "")

    if summary.get("is_available") is not True:
        reason = summary.get("reason", "not_available")
        print("Review status: not available")
        print(f"Actual card played: {format_optional_cli_value(summary.get('actual_card_played'))}")
        print(f"Recommended card: {format_optional_cli_value(summary.get('recommended_card'))}")
        print(f"Unavailable reason: {format_post_game_review_unavailable_reason(reason)}")
        print(f"Reason code: {reason}")
        print(f"Decision factors: {decision_factors}")
        print(f"Decision explanation: {decision_explanation}")
        print_post_game_review_rank_summary(summary)
        return

    print(f"Actual card played: {summary['actual_card_played']}")
    print(f"Recommended card: {summary['recommended_card']}")
    print_post_game_review_value_summary(result=result, summary=summary)
    print(f"Decision quality: {summary['decision_quality']}")
    print(f"Decision factors: {decision_factors}")
    print(f"Decision explanation: {decision_explanation}")
    print_post_game_review_rank_summary(summary)


def print_analysis_result(result: dict[str, Any]) -> None:
    """
    Prints the analysis result in a readable text format.
    """
    position = result["position"]
    settings = result["settings"]
    score_summary = result["score_summary"]

    print("JSON position analysis")
    print("Input file:", result["input_file"])
    print("Game type:", position["game_type"])
    print("Player role:", position["player_role"])
    print("Player position:", position["player_position"])
    print("Declarer player:", position["declarer_player"])
    print("Trick leader:", position["trick_leader"])
    print("Hand:", position["hand"])
    print("Current trick:", position["current_trick"])
    print("Played cards:", position["played_cards"])
    print("Skat:", position["skat"])
    print("Completed tricks:", position["completed_tricks"])
    print("Declarer points:", position["declarer_points"])
    print("Defender points:", position["defender_points"])
    print("Next player:", position["next_player"])
    print("Legal cards:", result["legal_cards"])
    print("Left hand size:", settings["left_hand_size"])
    print("Right hand size:", settings["right_hand_size"])
    print("Sample count:", settings["sample_count"])
    print("Random seed:", settings["random_seed"])
    print("Use basic opponent strategy:", settings["use_basic_opponent_strategy"])

    method_summary = result.get("recommendation_method_summary")
    if isinstance(method_summary, dict):
        print("Requested recommendation method:", method_summary["requested_method"])
        print("Effective recommendation method:", method_summary["effective_method"])
        search_settings = settings.get("bounded_search_settings")
        if isinstance(search_settings, dict):
            print("Search random seed:", search_settings["random_seed"])
        search_result = result.get("bounded_search_result")
        if isinstance(search_result, dict):
            consumed = search_result["consumed_budget"]
            print("Search status:", search_result["status"])
            print("Search stop reason:", search_result["stop_reason"])
            print("Search coverage:", search_result["world_coverage"])
            print(
                "Search completed worlds:",
                f"{consumed['completed_world_count']} of {consumed['selected_world_count']}",
            )
        if method_summary["fallback_used"]:
            print("Fallback method:", method_summary["fallback_method"])

    declaration = result["game_declaration"]
    if declaration["ouvert"]:
        constraints = result["information_policy_summary"].get(
            "public_hand_constraints", []
        )
        declared_constraint = next(
            constraint
            for constraint in constraints
            if constraint["source"] == "declared_ouvert"
        )
        print("Declared Ouvert: yes")
        print("Public declarer:", declared_constraint["player"])
        print("Public declarer cards:", declared_constraint["card_count"])
        print("Ouvert-aware simulation: applied")

    print_opponent_profile_application_summary(result)

    print_hidden_card_inference_summary(result.get("hidden_card_inference_summary"))

    print()
    print("Score summary")
    print("Explicit declarer points:", score_summary["explicit_declarer_points"])
    print("Explicit defender points:", score_summary["explicit_defender_points"])
    print(
        "Completed-trick declarer points:",
        score_summary["completed_trick_declarer_points"],
    )
    print(
        "Completed-trick defender points:",
        score_summary["completed_trick_defender_points"],
    )
    print("Total declarer points:", score_summary["total_declarer_points"])
    print("Total defender points:", score_summary["total_defender_points"])

    print()
    print(format_card_analysis_report(result["analysis_report"]))

    print()
    print(result["strategic_summary"])

    print()
    print(
        "Recommended card:",
        format_optional_cli_value(result["recommendation"]["card"]),
    )
    print("Reason:", result["recommendation"]["reason"])

    print_game_shortening_summary(result)

    print_game_continuation_summary(result)

    print_post_game_review_summary(result)


def print_game_shortening_summary(result: dict[str, Any]) -> None:
    """Prints the supported structured game-shortening outcome."""
    summary = result.get("game_shortening_summary")
    if not isinstance(summary, dict):
        return
    if summary.get("kind") == "defender_concession":
        print_defender_concession_summary(result)
    elif summary.get("kind") == "declarer_card_exposure":
        print_declarer_card_exposure_summary(result)
    elif summary.get("kind") == "defender_open_play":
        print_defender_open_play_summary(result)
    elif summary.get("kind") == "open_card_throw":
        print_open_card_throw_summary(result)
    else:
        print_declarer_concession_summary(result)


def print_game_continuation_summary(result: dict[str, Any]) -> None:
    """Prints one supported ongoing continuation setup."""
    summary = result.get("game_continuation_summary")
    if not isinstance(summary, dict):
        return
    if summary.get("kind") == "defender_open_play":
        print_defender_open_play_continuation_summary(summary)
        return
    print()
    print("Declarer card exposure was not accepted unanimously.")
    continuing = summary["continuing_defenders"]
    if len(continuing) == 2:
        print("Both defenders requested continued play.")
    else:
        print(f"{continuing[0].title()} requested continued play.")
    print(
        f"The declarer's {summary['public_declarer_card_count']} remaining cards "
        "are public to all players."
    )
    print(
        f"Claimed level {summary['claimed_play_level'].title()} has no immediate settlement effect."
    )
    print("Analysis continues using the exposed declarer hand.")


def print_defender_open_play_continuation_summary(summary: dict[str, Any]) -> None:
    """Prints the non-adjudicating defender-open-play continuation state."""
    exposing_defender = summary["exposing_defender"]
    card_count = summary["public_exposing_defender_card_count"]
    print()
    print("Continued play was requested after defender open play.")
    if exposing_defender == "me":
        print(f"You took your {card_count} exposed cards back into the hand.")
        print("Your remaining hand is known to both opponents.")
    else:
        print(
            f"{exposing_defender.title()} took the {card_count} exposed cards back into the hand."
        )
        print("Those cards remain known to all players.")
    print("The original rest-trick claim is not adjudicated.")
    print("Analysis continues from the corrected legal position.")


def print_declarer_concession_summary(result: dict[str, Any]) -> None:
    """Prints the bounded structured declarer-concession outcome."""
    summary = result.get("game_shortening_summary")
    if not isinstance(summary, dict) or summary.get("kind") != "declarer_concession":
        return

    hand_count = summary["declarer_hand_cards_remaining"]
    consent = summary["defender_consent"]
    if summary["consent_required"]:
        consent_text = f"accepted by {consent['consenting_defender_count']} defender" + (
            "s" if consent["consenting_defender_count"] != 1 else ""
        )
    else:
        consent_text = "defender consent not required"

    settlement = result["final_settlement_summary"]
    print()
    print(f"Declarer concession: {hand_count} hand cards, {consent_text}.")
    print("Result: declarer lost; no remaining card points were assigned.")
    print(
        f"Settlement: {settlement['settlement_score']} using effective game value "
        f"{settlement['effective_game_value']}; no achieved Schneider or Schwarz "
        "level was added."
    )


def print_defender_concession_summary(result: dict[str, Any]) -> None:
    """Prints the bounded structured defender-concession outcome."""
    summary = result.get("game_shortening_summary")
    if not isinstance(summary, dict) or summary.get("kind") != "defender_concession":
        return

    settlement = result["final_settlement_summary"]
    decision_state = summary["decision_state_before_concession"]
    print()
    if decision_state == "defenders_already_won":
        print(
            f"Defender concession: {summary['conceding_player']} conceded after the "
            "game was already lost by the declarer."
        )
        print(
            "Result preserved: defenders won; the concession did not reverse the existing decision."
        )
    else:
        print(
            f"Defender concession: {summary['conceding_player']} conceded for the defending party."
        )
        print(f"Decision before concession: {decision_state}.")
        print(
            f"Result: {summary['adjudicated_winner']} won; no remaining card points were assigned."
        )
    print(
        f"Settlement: {settlement['settlement_score']} using effective game value "
        f"{settlement['effective_game_value']}."
    )


def print_declarer_card_exposure_summary(result: dict[str, Any]) -> None:
    """Prints the bounded accepted declarer-card-exposure outcome."""
    summary = result.get("game_shortening_summary")
    if not isinstance(summary, dict) or summary.get("kind") != ("declarer_card_exposure"):
        return

    settlement = result["final_settlement_summary"]
    print()
    if summary["exposure_form"] == "laid_open":
        print(f"Declarer card exposure: {summary['exposed_card_count']} cards laid open.")
    else:
        print(f"Declarer showed all remaining cards to {summary['shown_to_player']}.")
    print("Both defenders accepted the shortening.")
    print(f"Claimed level: {summary['claimed_play_level'].title()}.")
    if summary["decision_state_before_shortening"] == "defenders_already_won":
        print("The game was already lost before the card exposure.")
        print("Defender acceptance did not reverse the existing result.")
    else:
        print(
            f"Result: {summary['adjudicated_winner']} won; no remaining card points were assigned."
        )
    claim_text = ""
    basis = settlement["settlement_basis"]
    if basis["accepted_claimed_schwarz_applied"]:
        claim_text = " using a unanimously accepted Schwarz claim"
    elif basis["accepted_claimed_schneider_applied"]:
        claim_text = " using a unanimously accepted Schneider claim"
    print(f"Settlement: {settlement['settlement_score']}{claim_text}.")


def print_defender_open_play_summary(result: dict[str, Any]) -> None:
    """Prints one privacy-safe exact defender-open-play adjudication."""
    summary = result.get("game_shortening_summary")
    if not isinstance(summary, dict) or summary.get("kind") != "defender_open_play":
        return

    proof = summary["exact_proof"]
    settlement = result["final_settlement_summary"]
    print()
    print(
        f"Defender open play: {summary['exposing_defender']} exposed "
        f"{summary['exposed_card_count']} remaining cards."
    )
    if proof["status"] == "valid":
        print("Exact proof: valid across every legal declarer and partner response.")
        print("Rest tricks: defending party.")
    else:
        print("Exact proof: invalid; a legal counterplay can give the declarer a trick.")
        print("Rest tricks: declarer by rule.")
    decision_state = summary["decision_state_before_shortening"]
    if decision_state == "defenders_already_won":
        print("The declarer had already lost before the open play.")
        print("The later rest-trick adjudication did not reverse the existing result.")
    elif decision_state == "declarer_already_won":
        print("The declarer had already won before the open play.")
        print("The later rest-trick adjudication did not reverse the existing result.")
    else:
        result_text = "won" if summary["adjudicated_winner"] == "declarer" else "lost"
        print(f"Result: declarer {result_text}.")
    print(f"Settlement: {settlement['settlement_score']}.")


def print_open_card_throw_summary(result: dict[str, Any]) -> None:
    """Prints one privacy-safe ISkO 4.4.6 adjudication."""
    summary = result.get("game_shortening_summary")
    if not isinstance(summary, dict) or summary.get("kind") != "open_card_throw":
        return

    assignment = summary["rest_trick_assignment"]
    observed_tricks = summary["observed_trick_counts"]
    observed_points = summary["observed_points"]
    settlement = result["final_settlement_summary"]
    print()
    print(
        f"Open card throw: {summary['throwing_player']} threw "
        f"{summary['thrown_card_count']} remaining cards."
    )
    throwing_party_label = (
        "defending" if summary["throwing_party"] == "defenders" else "declarer"
    )
    print(
        f"The {throwing_party_label} party keeps its "
        f"{observed_tricks[summary['throwing_party']]} completed tricks and "
        f"{observed_points[summary['throwing_party']]} points."
    )
    print(
        f"All {assignment['remaining_trick_count']} unresolved tricks and "
        f"{assignment['assigned_card_points']} outstanding points go to the "
        f"{summary['opposing_party']} party."
    )
    decision_state = summary["decision_state_before_shortening"]
    if decision_state != "undecided":
        existing_winner = "declarer" if decision_state == "declarer_already_won" else "defenders"
        print(f"The game had already been won by the {existing_winner} party.")
        print("The later open throw did not reverse the existing result.")
    else:
        levels = []
        if summary["schneider_rule_level_applied"]:
            levels.append("Schneider")
        if summary["schwarz_rule_level_applied"]:
            levels.append("Schwarz")
        level_text = f" with {' and '.join(levels)}" if levels else ""
        print(f"Result: {summary['adjudicated_winner']} won{level_text}.")
    if summary["theoretical_schwarz_status"] == "excluded":
        basis = summary["theoretical_schwarz_assessment"]["exclusion_basis"]
        print(f"Schwarz was theoretically excluded under the jack-only assessment: {basis}.")
    else:
        print("Schwarz was not theoretically excluded under the jack-only assessment.")
    print(f"Settlement: {settlement['settlement_score']}.")


def print_opponent_profile_application_summary(result: dict[str, Any]) -> None:
    """Prints one concise line per requested external opponent binding."""
    summary = result.get("opponent_profile_application_summary")
    if not isinstance(summary, dict):
        return

    for relative_player in ("left", "right"):
        side = summary[relative_player]
        if side["binding_status"] != "matched":
            continue
        external_profile = side["external_profile"]
        classification = external_profile["classification"]
        confidence = external_profile["confidence_level"]
        status = side["application_status"]
        if status == "applied":
            decision = f"applied {side['applied_policy_preset']}"
        elif status == "manual_profile_precedence":
            decision = "not applied; manual profile takes precedence"
        elif status == "explicit_policy_precedence":
            decision = "not applied; explicit policy takes precedence"
        else:
            decision = "not applied"
        print(
            f"{relative_player.title()} opponent {side['bound_player_id']}: "
            f"{classification}, {confidence} confidence, {decision}."
        )


def _print_historical_continuation_event(event: dict[str, Any]) -> None:
    if event["kind"] == "defender_open_play_continuation":
        print("Non-terminal event: defender open-play continuation")
        print("Event after played cards:", event["after_play_count"])
        print("Exposing defender:", event["exposing_defender_player_id"])
        print("Returned public cards:", event["exposed_card_count"])
        print("Continued play requested: yes")
        print("Rest-trick claim adjudicated: no")
    else:
        print("Non-terminal event: declarer card-exposure continuation")
        print("Event after played cards:", event["after_play_count"])
        if event["exposure_form"] == "shown_to_defender":
            print(
                "Exposure: declarer showed "
                f"{event['public_declarer_card_count']} remaining cards to "
                f"{event['shown_to_defender_player_id']}"
            )
        else:
            print(
                "Exposure: declarer laid open "
                f"{event['public_declarer_card_count']} remaining cards"
            )
        continuing_ids = event["continuing_defender_player_ids"]
        if len(continuing_ids) == 2:
            print("Both defenders required continued play.")
        else:
            print("Continuing defender:", continuing_ids[0])
        print("Claimed play level:", event["claimed_play_level"].title())
        print("Claimed level applied immediately: no")
        print("The game continued with the declarer's cards open.")
    print("Actual plays after the event:", event["actual_plays_after_event"])


def print_historical_game_result(result: dict[str, Any]) -> None:
    """Prints a concise complete historical-game summary."""
    summary = result["historical_game_summary"]
    declaration = summary["record"]["declaration"]
    settlement = summary["final_settlement_summary"]

    game_end_summary = summary.get("historical_game_end_summary")
    game_events_summary = summary.get("historical_game_events_summary")
    if game_end_summary is not None:
        print(f"Historical game: {summary['game_id']}")
        end_kind = game_end_summary["kind"]
        if end_kind == "defender_concession":
            print("End reason: defender concession")
            print(
                "Conceding defender:",
                game_end_summary["conceding_defender_player_id"],
            )
            print("Joint liability: yes")
        elif end_kind == "declarer_concession":
            consent_ids = game_end_summary["defender_consent"][
                "consenting_defender_player_ids"
            ]
            consent_text = (
                "not required"
                if not consent_ids
                else f"granted by {', '.join(consent_ids)}"
            )
            print("End reason: declarer concession")
        elif end_kind == "defender_open_play":
            print("End reason: defender open play")
            print(
                "Exposing defender:",
                game_end_summary["exposing_defender_player_id"],
            )
            print(
                "Non-exposing defender:",
                game_end_summary["non_exposing_defender_player_id"],
            )
            print("Exposed defender cards:", game_end_summary["exposed_card_count"])
            print("Exact proof:", game_end_summary["exact_proof"]["status"])
            print("Rest tricks assigned to:", game_end_summary["rest_tricks_recipient"])
        elif end_kind == "open_card_throw":
            print("End reason: open card throw")
            print("Throwing player:", game_end_summary["throwing_player_id"])
            print("Throwing party:", game_end_summary["throwing_party"])
            print(
                "Joint liability:",
                "yes" if game_end_summary["joint_liability"] else "no",
            )
            print("Thrown cards:", game_end_summary["thrown_card_count"])
            print("Statement:", game_end_summary["statement_classification"])
            print("Rest tricks assigned to:", game_end_summary["rest_tricks_recipient"])
            print(
                "Theoretical Schwarz:",
                game_end_summary["theoretical_schwarz_status"],
            )
        else:
            print("End reason: accepted declarer card exposure")
            print("Exposure form:", game_end_summary["exposure_form"])
            shown_to_id = game_end_summary["shown_to_defender_player_id"]
            if shown_to_id is not None:
                print("Shown to defender:", shown_to_id)
            print("Exposed declarer cards:", game_end_summary["exposed_card_count"])
            print(
                "Accepted by defenders:",
                ", ".join(game_end_summary["accepting_defender_player_ids"]),
            )
            print("Claimed play level:", game_end_summary["claimed_play_level"])
        print("Played cards:", summary["play_prefix_summary"]["played_card_count"])
        if end_kind == "defender_concession":
            print(f"Result: {summary['winner']} won")
            if (
                game_end_summary["decision_state_before_concession"]
                == "defenders_already_won"
            ):
                print("The defending party had already won before the concession.")
                print("The later concession did not reverse the existing result.")
        elif end_kind == "declarer_concession":
            print(
                "Declarer cards remaining:",
                game_end_summary["declarer_hand_cards_remaining"],
            )
            print("Consent:", consent_text)
            print("Result: declarer lost")
        elif end_kind == "defender_open_play":
            print(
                "Decision before open play:",
                game_end_summary["decision_state_before_shortening"],
            )
            print(f"Result: {summary['winner']} won")
        elif end_kind == "open_card_throw":
            print(
                "Decision before throw:",
                game_end_summary["decision_state_before_shortening"],
            )
            print(f"Result: {summary['winner']} won")
        else:
            print("Decision before exposure:", game_end_summary["decision_state_before_shortening"])
            print(f"Result: {summary['winner']} won")
        print(
            "Unresolved points assigned:",
            "yes" if end_kind in {"defender_open_play", "open_card_throw"} else "no",
        )
        print("Settlement:", settlement["settlement_score"])
        if game_events_summary is not None:
            _print_historical_continuation_event(game_events_summary["events"][0])
    else:
        if game_events_summary is not None:
            event = game_events_summary["events"][0]
            print(f"Historical game: {summary['game_id']}")
            print("End reason: normal completion")
            _print_historical_continuation_event(event)
            print(f"Final result: {summary['winner']} won")
            print("Settlement:", settlement["settlement_score"])
        else:
            print("Historical game summary")
            print("Input file:", result["input_file"])
            print("Game ID:", summary["game_id"])
            print("Game type:", declaration["game_type"])
            print("Declarer:", summary["record"]["declarer_player_id"])
            print("Result winner:", summary["winner"])
            print("Declarer points:", summary["declarer_points"])
            print("Defender points:", summary["defender_points"])
            print("Game value:", summary["game_value_summary"]["game_value"])
            print("Overbid status:", summary["overbid_summary"]["status"])
            print("Settlement score:", settlement["settlement_score"])
    decision_snapshot_summary = summary.get("decision_snapshot_summary")
    if decision_snapshot_summary is not None:
        snapshot_count = decision_snapshot_summary["snapshot_count"]
        if game_end_summary is not None:
            print("Historical decision snapshots:", snapshot_count)
            if snapshot_count == 0:
                print("No card decisions occurred before the terminal event.")
        else:
            print("Decision snapshots generated:", snapshot_count)
        if game_events_summary is not None:
            event = game_events_summary["events"][0]
            print(
                (
                    "Public defender hand begins at decision:"
                    if event["kind"] == "defender_open_play_continuation"
                    else "Public declarer hand begins at decision:"
                ),
                event["first_affected_decision_index"],
            )
    review_summary = summary.get("historical_game_review_summary")
    if review_summary is not None:
        profile_summary = result.get("historical_opponent_profile_application_summary")
        if profile_summary is not None:
            participant_count = len(profile_summary["participant_matches"])
            matched_count = profile_summary["matched_player_count"]
            print(
                f"Historical profile application: {matched_count} of "
                f"{participant_count} participants matched."
            )
            print("Temporal eligibility: all matched captures predate the game.")
            application_counts = review_summary["opponent_profile_application_counts"]
            applied_decisions = sum(
                any(
                    application[side]["application_status"] == "applied"
                    for side in ("left", "right")
                )
                for application in (
                    decision["opponent_profile_application"]
                    for decision in review_summary["decisions"]
                )
            )
            print(
                "Reviewed decisions with an applied external profile: "
                f"{applied_decisions} of {application_counts['total_decisions']}."
            )
        print()
        if game_end_summary is not None:
            print(
                "Historical game review:",
                review_summary["decision_count"],
                "decisions",
            )
        else:
            print("Historical game review")
            print("Total decisions:", review_summary["decision_count"])
        print("Reviewed decisions:", review_summary["reviewed_decision_count"])
        print("Unavailable decisions:", review_summary["unavailable_decision_count"])
        inference_decision_count = sum(
            "hidden_card_inference_summary" in decision
            for decision in review_summary["decisions"]
        )
        if inference_decision_count:
            print(
                "Hidden-card inference applied at reviewed decisions:",
                inference_decision_count,
            )
        if game_end_summary is not None:
            print(
                "Terminal event:",
                game_end_summary["kind"].replace("_", " "),
            )
            print("The terminal event itself was not reviewed as a card decision.")
        for quality, count in review_summary["quality_counts"].items():
            print(f"{quality.replace('_', ' ').title()} decisions:", count)
        for decision in review_summary["decisions"]:
            decision_quality = decision["post_game_review_summary"]["decision_quality"]
            if decision_quality not in {"suboptimal", "mistake"}:
                continue
            print(
                f"Decision {decision['decision_index']} ({decision['acting_player_id']}): "
                f"{decision_quality}; actual {decision['actual_card_played']}, "
                f"recommended {decision['recommendation']['card']}."
            )


def _format_list_player_identity(player_id: str, player_label: str | None) -> str:
    return player_id if player_label is None else f"{player_id} ({player_label})"


def print_fixed_three_player_historical_list_result(result: dict[str, Any]) -> None:
    """Prints complete final facts and round-end progression for one list."""
    summary = result["fixed_three_player_historical_list_summary"]
    print("Fixed three-player historical list summary")
    print("List ID:", summary["list_id"])
    print(f"Positions: {summary['entry_count']}; rounds: {summary['round_count']}")
    print(
        "Entries:",
        f"{summary['played_game_count']} Played Games; "
        f"{summary['passed_deal_count']} Passed Deals",
    )
    print(
        "Declarer results:",
        f"{summary['declarer_win_count']} wins; "
        f"{summary['declarer_loss_count']} losses",
    )
    print("Ranking status:", summary["ranking_status"])
    if summary["ranking_status"] == "lot_required":
        print(
            "Unresolved tie; external lot required:",
            ", ".join(summary["lot_required_player_ids"]),
        )
    elif summary["applied_lot_order"] is not None:
        print("Applied external lot:", ", ".join(summary["applied_lot_order"]))
    else:
        print("External lot: not required")

    print("Final standings")
    for standing in summary["final_standings"]:
        totals = standing["player_totals"]
        print(
            f"Rank {standing['rank']}: "
            f"{_format_list_player_identity(totals['player_id'], totals['player_label'])}; "
            f"table place {totals['table_place']}; "
            f"total performance points {totals['total_performance_points']}; "
            f"game points {totals['player_game_points']}; "
            f"own-game bonus {totals['own_game_bonus_points']}; "
            f"opponent-loss bonus {totals['opponent_loss_bonus_points']}; "
            f"own wins {totals['own_games_won']}; own losses {totals['own_games_lost']}; "
            f"Played Games {totals['played_game_count']}; "
            f"Passed Deals {totals['passed_deal_count']}."
        )

    print("Round-end progression")
    for snapshot in summary["progression"][2::3]:
        standings_text = ", ".join(
            f"rank {standing['rank']} {standing['player_totals']['player_id']} "
            f"{standing['player_totals']['total_performance_points']}"
            for standing in snapshot["provisional_standings"]
        )
        print(
            f"Entry {snapshot['entry_fact']['entry_number']} "
            f"(round {snapshot['entry_fact']['round_number']}): {standings_text}."
        )


def _print_comparison_source_summary(summary: dict[str, Any]) -> None:
    print(
        f"Source list {summary['list_id']}: {summary['entry_count']} positions, "
        f"{summary['played_game_count']} Played Games, "
        f"{summary['passed_deal_count']} Passed Deals, "
        f"{summary['declarer_win_count']} declarer wins, "
        f"{summary['declarer_loss_count']} declarer losses; "
        f"ranking status {summary['ranking_status']}."
    )
    for standing in summary["final_standings"]:
        print(
            f"  Rank {standing['rank']}: "
            f"{_format_list_player_identity(standing['player_id'], standing['player_label'])}; "
            f"table place {standing['table_place']}; "
            f"total performance points {standing['total_performance_points']}; "
            f"own wins {standing['own_games_won']}; own losses {standing['own_games_lost']}."
        )


def print_fixed_three_player_historical_list_comparison_result(
    result: dict[str, Any],
) -> None:
    """Prints compact independent-list sources and comparison-minus-reference deltas."""
    summary = result["fixed_three_player_historical_list_comparison_summary"]
    print("Fixed three-player historical list comparison")
    print("Reference list:", summary["reference_list_id"])
    print("Source-list count:", summary["list_count"])
    print("Source summaries")
    for source in summary["source_lists"]:
        _print_comparison_source_summary(source)

    delta_labels = (
        ("list_entry_count", "list entries"),
        ("played_game_count", "Played Games"),
        ("passed_deal_count", "Passed Deals"),
        ("declarer_game_count", "declarer games"),
        ("defender_game_count", "defender games"),
        ("own_games_won", "own wins"),
        ("own_games_lost", "own losses"),
        ("defender_games_won", "defender wins"),
        ("defender_games_lost", "defender losses"),
        ("other_players_lost_games", "other-player losses"),
        ("player_game_points", "game points"),
        ("own_game_bonus_points", "own-game bonus"),
        ("opponent_loss_bonus_points", "opponent-loss bonus"),
        ("total_performance_points", "total performance points"),
    )
    for comparison in summary["comparisons"]:
        print(
            f"Comparison list {comparison['comparison_list_id']} against "
            f"{comparison['reference_list_id']}"
        )
        print(
            "List-count deltas (comparison - reference): "
            f"Played Games {comparison['played_game_count_delta']:+d}; "
            f"Passed Deals {comparison['passed_deal_count_delta']:+d}; "
            f"declarer wins {comparison['declarer_win_count_delta']:+d}; "
            f"declarer losses {comparison['declarer_loss_count_delta']:+d}."
        )
        for player in comparison["player_comparisons"]:
            identity = _format_list_player_identity(
                player["player_id"],
                player["player_label"],
            )
            print(
                f"Player {identity}: "
                f"reference table place {player['reference_table_place']}; "
                f"comparison table place {player['comparison_table_place']}."
            )
            print(
                "  Metric deltas (comparison - reference): "
                + "; ".join(
                    f"{label} {player['deltas'][field_name]:+d}"
                    for field_name, label in delta_labels
                )
                + "."
            )
            print("  Rank status:", player["rank_comparison_status"])
            if player["rank_comparison_status"] == "available":
                print(
                    f"  Reference rank {player['reference_rank']}; "
                    f"comparison rank {player['comparison_rank']}; "
                    f"rank-position change {player['rank_position_change']:+d}."
                )
            else:
                print("  Rank-position change: unavailable while a lot remains unresolved.")


def print_training_dataset_result(result: dict[str, Any]) -> None:
    """Prints a concise training-dataset conversion summary."""
    summary = result["training_dataset_summary"]
    print("Training dataset summary")
    print("Input file:", result["input_file"])
    print("Dataset ID:", summary["dataset_id"])
    print("Dataset version:", summary["dataset_version"])
    print("Records:", summary["record_count"])
    print("Samples:", summary["sample_count"])
    for partition in ("train", "validation", "test"):
        counts = summary["partition_counts"][partition]
        print(
            f"{partition.title()} partition:",
            f"{counts['record_count']} records, {counts['sample_count']} samples",
        )


def print_training_dataset_preparation_result(
    request: TrainingDatasetPreparationRequest,
    preparation_result: TrainingDatasetPreparationResult,
) -> None:
    """Prints concise card-free evidence for one automatic preparation result."""
    plan = preparation_result.plan
    weights = plan.requested_partition_weights
    print("Automatic Training Dataset Preparation")
    print(f"Dataset identity: {request.dataset_id}, version {request.dataset_version}")
    print("Mode:", plan.mode)
    print("Algorithm:", plan.algorithm)
    print("Status:", plan.status)
    if plan.status == "unavailable":
        print("Unavailable reason:", plan.unavailable_reason)
    print(
        "Source Record and Sample Counts:",
        f"{plan.source_record_count} records, {plan.source_sample_count} samples",
    )
    print(
        "Requested weights:",
        f"train {weights.train}, validation {weights.validation}, test {weights.test}",
    )
    print("Plan fingerprint:", plan.plan_fingerprint)
    if plan.status == "unavailable":
        print("Materialized Dataset: not created")
        return

    for summary in plan.partition_summaries:
        print(
            f"{summary.partition.title()} summary:",
            f"{summary.record_count} records, {summary.sample_count} samples, "
            f"{summary.distinct_player_count} players",
        )
    assert plan.partition_audit is not None
    audit = plan.partition_audit
    print("Audit evidence:", audit.compliance_status)
    if plan.mode == "known_opponent":
        assert plan.temporal_audit is not None
        boundaries = "; ".join(
            f"{boundary.partition} {boundary.minimum_played_at} to "
            f"{boundary.maximum_played_at}"
            for boundary in plan.temporal_audit.partition_boundaries
        )
        print("Temporal boundaries:", boundaries)
        print(
            "Train Player coverage:",
            f"{len(plan.temporal_audit.train_player_ids)} Train players; "
            f"Validation complete {plan.temporal_audit.validation_train_coverage_complete}; "
            f"Test complete {plan.temporal_audit.test_train_coverage_complete}",
        )
    else:
        compliance = audit.unseen_player_compliance
        overlaps = audit.overlap_summary
        print("Disjointness compliance:", compliance["player_disjoint"])
        print(
            "Overlap counts:",
            f"train-validation {overlaps['train_validation']['player_count']}, "
            f"train-test {overlaps['train_test']['player_count']}, "
            f"validation-test {overlaps['validation_test']['player_count']}",
        )
    print("Materialized Dataset status: created and reusable")


def print_training_dataset_preparation_application_result(
    root_document: dict[str, Any],
    result: dict[str, Any],
) -> None:
    """Prints the existing preparation wording from an Application result."""
    request = root_document["training_dataset_preparation_input"]
    summary = result["training_dataset_preparation_summary"]
    plan = summary["plan"]
    weights = plan["requested_partition_weights"]
    print("Automatic Training Dataset Preparation")
    print(
        f"Dataset identity: {request['dataset_id']}, "
        f"version {request['dataset_version']}"
    )
    print("Mode:", plan["mode"])
    print("Algorithm:", plan["algorithm"])
    print("Status:", plan["status"])
    if plan["status"] == "unavailable":
        print("Unavailable reason:", plan["unavailable_reason"])
    print(
        "Source Record and Sample Counts:",
        f"{plan['source_record_count']} records, "
        f"{plan['source_sample_count']} samples",
    )
    print(
        "Requested weights:",
        f"train {weights['train']}, validation {weights['validation']}, "
        f"test {weights['test']}",
    )
    print("Plan fingerprint:", plan["plan_fingerprint"])
    if plan["status"] == "unavailable":
        print("Materialized Dataset: not created")
        return
    for partition_summary in plan["partition_summaries"]:
        print(
            f"{partition_summary['partition'].title()} summary:",
            f"{partition_summary['record_count']} records, "
            f"{partition_summary['sample_count']} samples, "
            f"{partition_summary['distinct_player_count']} players",
        )
    audit = plan["partition_audit"]
    print("Audit evidence:", audit["compliance_status"])
    if plan["mode"] == "known_opponent":
        temporal_audit = plan["temporal_audit"]
        boundaries = "; ".join(
            f"{boundary['partition']} {boundary['minimum_played_at']} to "
            f"{boundary['maximum_played_at']}"
            for boundary in temporal_audit["partition_boundaries"]
        )
        print("Temporal boundaries:", boundaries)
        print(
            "Train Player coverage:",
            f"{len(temporal_audit['train_player_ids'])} Train players; "
            "Validation complete "
            f"{temporal_audit['validation_train_coverage_complete']}; "
            f"Test complete {temporal_audit['test_train_coverage_complete']}",
        )
    else:
        compliance = audit["unseen_player_compliance"]
        overlaps = audit["overlap_summary"]
        print("Disjointness compliance:", compliance["player_disjoint"])
        print(
            "Overlap counts:",
            f"train-validation {overlaps['train_validation']['player_count']}, "
            f"train-test {overlaps['train_test']['player_count']}, "
            "validation-test "
            f"{overlaps['validation_test']['player_count']}",
        )
    print("Materialized Dataset status: created and reusable")


def print_bounded_search_evaluation_result(result: dict[str, Any]) -> None:
    """Prints a concise bounded-Search dataset evaluation summary."""
    summary = result["bounded_search_evaluation_summary"]
    quality = summary["quality_gate"]
    counts = summary["decision_counts"]
    print(
        "Bounded Search evaluation: "
        f"{summary['record_count']} records, {counts['decision_count']} decisions."
    )
    print(
        "Search availability: "
        f"{counts['search_available_decision_count']} available, "
        f"{counts['search_unavailable_decision_count']} unavailable."
    )
    print(
        "Search not-worse gate: "
        f"{quality['search_not_worse_count']} of "
        f"{quality['comparable_decision_count']} comparable decisions; "
        f"violations {quality['quality_violation_count']}."
    )


def print_historical_search_review_result(summary: dict[str, Any]) -> None:
    """Prints a concise Historical Search Review summary."""
    quality = summary["quality_gate"]
    counts = summary["decision_counts"]
    print()
    print("Historical Search Review")
    print("Decisions attempted:", counts["search_attempted_count"])
    print("Search recommendations:", counts["search_recommendation_count"])
    print(
        "Search not-worse gate:",
        f"{quality['search_not_worse_count']} of "
        f"{quality['comparable_decision_count']} comparable decisions; "
        f"violations {quality['quality_violation_count']}.",
    )


def print_historical_replay_coaching_result(summary: dict[str, Any]) -> None:
    """Prints the concise public Replay Coaching view without private analysis state."""
    game = summary["game_context"]
    declaration = game["declaration"]
    coverage = summary["coverage_summary"]
    prioritization = summary["prioritization"]
    guidance = summary["guidance"]
    outcome = summary["outcome_context"]

    print()
    print("Historical Replay Coaching Report")
    print("Source game:", summary["source_game_id"])
    print("Method:", summary["report_method"])
    print(
        "Game type and declaration:",
        f"{game['game_type']}; Hand {str(declaration['hand_game']).lower()}; "
        f"Ouvert {str(declaration['ouvert']).lower()}; bid {declaration['bid_value']}.",
    )
    print("Game-end reason:", game["game_end_reason"].replace("_", " "))
    print(
        "Decision coverage:",
        f"{coverage['assessable_decision_count']} of {coverage['decision_count']} assessable; "
        f"{coverage['not_assessable_count']} not assessable.",
    )
    print("High-impact decisions:", coverage["high_impact_decision_count"])

    print("Key Decisions")
    if not prioritization["key_decisions"]:
        print("None.")
    for key_decision in prioritization["key_decisions"]:
        assessment = key_decision["assessment"]
        evidence = assessment["decision_time_evidence"]
        marker = "high impact" if key_decision["is_high_impact"] else "review focus"
        print(
            f"{key_decision['rank']}. Decision {evidence['decision_index']}; "
            f"actor {evidence['acting_player_id']}; trick {evidence['trick_number']}, "
            f"play {evidence['play_index']}; actual {assessment['actual_card']}; "
            f"best evaluated {assessment['best_card']}; impact "
            f"{assessment['impact_tier'].replace('_', ' ')}; evidence "
            f"{assessment['evidence_basis'].replace('_', ' ')}; {marker}."
        )

    print("Turning Points")
    if not prioritization["turning_points"]:
        print("None.")
    for turning_point in prioritization["turning_points"]:
        assessment = turning_point["assessment"]
        evidence = assessment["decision_time_evidence"]
        before = turning_point["recorded_state_before"]
        after = turning_point["recorded_state_after"]
        transition = (
            f"{before.replace('_', ' ')} -> {after.replace('_', ' ')}"
            if before is not None and after is not None
            else "counterfactual aggregate opportunity; no recorded transition"
        )
        print(
            f"{turning_point['turning_point_type'].replace('_', ' ')}; decision "
            f"{turning_point['decision_index']}; actor {evidence['acting_player_id']}; "
            f"{transition}; high impact."
        )

    print("Decision Recommendations")
    if not guidance["decision_recommendations"]:
        print("None.")
    for recommendation in guidance["decision_recommendations"]:
        print(f"{recommendation['rank']}. {recommendation['title']}")
        print("Action:", recommendation["action"])

    print("Pattern Recommendations")
    if not guidance["pattern_recommendations"]:
        print("None.")
    for recommendation in guidance["pattern_recommendations"]:
        print(f"{recommendation['rank']}. {recommendation['title']}")
        print("Action:", recommendation["action"])

    for label, field_name in (
        ("Player summaries", "player_summaries"),
        ("Role summaries", "role_summaries"),
        ("Phase summaries", "phase_summaries"),
        ("Contract summary", "contract_summaries"),
    ):
        rows = summary[field_name]
        compact = "; ".join(
            f"{row['scope_value']}: {row['decision_count']} decisions, "
            f"{row['key_decision_count']} key, {row['turning_point_count']} turning"
            for row in rows
        )
        print(f"{label}: {compact}.")

    print("Retrospective outcome context")
    print("Recorded end:", outcome["game_end_reason"].replace("_", " "))
    print("Recorded winner:", outcome["game_result_summary"]["winner"])
    print(
        "Recorded settlement score:",
        outcome["final_settlement_summary"]["settlement_score"],
    )
    print("This final outcome is retrospective context, not decision-time evidence.")
    print("Report limitations:", ", ".join(summary["limitations"]))


def print_dataset_partition_audit_result(result: dict[str, Any]) -> None:
    """Prints a concise stable-player partition-audit summary."""
    summary = result["dataset_partition_audit_summary"]
    source = summary["source_dataset"]
    players = summary["player_summary"]
    unseen = summary["unseen_player_compliance"]
    coverage = summary["known_opponent_coverage"]["train_to_validation"]
    print(
        "Dataset partition audit: "
        f"{source['total_historical_game_count']} games, "
        f"{players['total_distinct_player_count']} distinct players."
    )
    print("Partition mode:", f"{summary['effective_audit_mode']}.")
    print("Cross-partition players:", f"{unseen['violating_player_count']}.")
    print(
        "Train -> validation shared players: "
        f"{coverage['shared_player_count']} of "
        f"{coverage['target_distinct_player_count']} validation players."
    )
    if unseen["player_disjoint"]:
        print("Unseen-player compliance: passed.")
    else:
        print(
            "Unseen-player compliance: failed with "
            f"{unseen['violating_player_count']} overlapping players."
        )


def print_rolling_opponent_policy_evaluation_result(result: dict[str, Any]) -> None:
    """Prints a concise behavioral policy-evaluation summary."""
    summary = result["rolling_opponent_policy_evaluation_summary"]
    coverage = summary["coverage"]
    paired = summary["actionable_profile_paired_results"]
    print(
        "Rolling opponent-policy evaluation: "
        f"{coverage['target_game_count']} target games, "
        f"{coverage['target_decisions']} decisions."
    )
    print(
        "Prior player history: "
        f"{coverage['decisions_with_prior_player_history']} of "
        f"{coverage['target_decisions']} decisions."
    )
    print(
        "Actionable profile coverage: "
        f"{coverage['decisions_with_actionable_profile']} of "
        f"{coverage['target_decisions']} decisions."
    )
    zero_decision_game_count = sum(
        target_game["decision_count"] == 0 for target_game in summary["target_games"]
    )
    if zero_decision_game_count == 1:
        print("One target game contained no card decisions before its terminal event.")
    elif zero_decision_game_count:
        print(
            f"{zero_decision_game_count} target games contained no card decisions "
            "before their terminal events."
        )
    if paired["paired_decision_count"] == 0:
        print(
            "No actionable profile predictions were available; baseline and coverage "
            "results were still recorded."
        )
        return
    print(
        "Paired preferred-card match: profile "
        f"{paired['profile_preferred_card_match_rate']:.2f}%, baseline "
        f"{paired['baseline_preferred_card_match_rate']:.2f}%, delta "
        f"{paired['preferred_card_rate_delta_percentage_points']:+.2f} pp."
    )


def print_opponent_statistics_result(result: dict[str, Any]) -> None:
    """Prints one concise summary per external opponent-statistics record."""
    summary = result["opponent_statistics_summary"]
    print("Opponent statistics summary")
    print("Input file:", result["input_file"])
    print("Records:", summary["record_count"])
    for record in summary["records"]:
        statistics = record["statistics"]
        derivation = record["profile_derivation"]
        label = record.get("player_label")
        identity = record["player_id"] if label is None else f"{record['player_id']} ({label})"
        print(
            f"{identity}: {record['games_played']} games; "
            f"declarer {statistics['solo_games_played_percent']:g}%; "
            f"declarer wins {statistics['solo_games_won_percent']:g}%; "
            f"defender {statistics['defender_games_played_percent']:g}%; "
            f"defender wins {statistics['defender_games_won_percent']:g}%."
        )
        confidence = derivation["confidence"]
        actionable = derivation["actionable_policy_preset"] is not None
        print(
            "  Profile derivation: "
            f"overall {confidence['overall']['level']}, "
            f"declarer {confidence['declarer']['level']}, "
            f"defender {confidence['defender']['level']}; "
            f"classification {derivation['classification']}; "
            f"recommended preset {derivation['recommended_policy_preset']}; "
            f"actionable {'yes' if actionable else 'no'}."
        )
        print(f"  Explanation: {derivation['explanations'][-1]}")


def print_historical_opponent_statistics_result(result: dict[str, Any]) -> None:
    """Prints a concise historical aggregation summary."""
    summary = result["historical_opponent_statistics_aggregation_summary"]
    print(
        "Historical opponent statistics: "
        f"{summary['source_game_count']} games, {summary['player_count']} players."
    )
    print(
        "Included partitions:",
        ", ".join(summary["selection"]["included_partitions"]),
    )
    for record in summary["records"]:
        statistics = record["statistics"]
        confidence = record["profile_derivation"]["confidence"]["overall"]["level"]
        print(
            f"{record['player_id']}: {record['games_played']} games, "
            f"{statistics['solo_games_played_percent']:.2f}% declarer, "
            f"{statistics['defender_games_played_percent']:.2f}% defender, "
            f"{confidence} confidence."
        )


def print_multi_step_result(result: dict[str, Any]) -> None:
    """
    Prints a multi-step simulation result in a readable text format.
    """
    final_state = result["final_state"]
    steps = result["steps"]

    if "summary" in result:
        print_multi_step_score_summary(result["summary"])

    print()
    print("Multi-step simulation")
    print("Card selection policy:", result["card_selection_policy"])
    print("Requested steps:", result.get("requested_step_count", len(steps)))
    print("Steps simulated:", result.get("steps_simulated", len(steps)))
    print("Stop reason:", result.get("stop_reason", "unknown"))
    print_hidden_card_inference_summary(result.get("hidden_card_inference_summary"))
    if "opponent_policy_settings" in result:
        print(
            "Opponent lead policy:",
            result["opponent_policy_settings"]["opponent_lead_policy"],
        )
        print(
            "Opponent response policy:",
            result["opponent_policy_settings"]["opponent_response_policy"],
        )
    if "context_summary" in result:
        context_summary = result["context_summary"]
        duplicate_cards = context_summary["duplicate_simulated_opponent_cards"]

        print("Context summary:", context_summary)

        hidden_world_summary = context_summary.get("hidden_world")
        if hidden_world_summary is not None:
            print("Hidden-world mode:", hidden_world_summary["mode"])
            print("Hidden world sampled once:", hidden_world_summary["sampled_once"])
            print(
                "Hidden world resampled after path start:",
                hidden_world_summary["resampled_after_path_start"],
            )
            print(
                "Hidden-world ownership preserved:",
                hidden_world_summary["ownership_preserved"],
            )

        if duplicate_cards:
            print(
                "Context warning: duplicate simulated opponent cards detected:",
                duplicate_cards,
            )
        else:
            print("Context warning: none")

    for step in steps:
        detailed_result = step["detailed_result"]
        completed_trick = detailed_result["completed_trick"]
        opponent_lead_result = step.get("opponent_lead_result")

        print()
        print("Step:", step["step_index"])

        decision = step.get("recommendation_decision")
        if decision is not None:
            if isinstance(decision, dict):
                search = decision["bounded_search_result"]
                consumed = search["consumed_budget"]
                requested_method = decision["requested_method"]
                effective_method = decision["effective_method"]
                search_status = search["status"]
                search_stop_reason = search["stop_reason"]
                completed_world_count = consumed["completed_world_count"]
                selected_world_count = consumed["selected_world_count"]
                fallback_used = decision["fallback_used"]
                fallback_method = decision["fallback_method"]
                recommendation_card = decision["recommendation_card"]
            else:
                search = decision.bounded_search_result
                consumed = search.consumed_budget
                requested_method = decision.requested_method
                effective_method = decision.effective_method
                search_status = search.status
                search_stop_reason = search.stop_reason
                completed_world_count = consumed.completed_world_count
                selected_world_count = consumed.selected_world_count
                fallback_used = decision.fallback_used
                fallback_method = decision.fallback_method
                recommendation_card = decision.recommendation_card
            print("Requested recommendation method:", requested_method)
            print("Effective recommendation method:", effective_method)
            print("Search status:", search_status)
            print("Search stop reason:", search_stop_reason)
            print(
                "Search completed worlds:",
                f"{completed_world_count} of {selected_world_count}",
            )
            if fallback_used:
                print("Fallback method:", fallback_method)
                print("Fallback chosen card:", recommendation_card)
            else:
                print("Search chosen card:", recommendation_card)

        if opponent_lead_result is not None:
            print("Opponent lead player:", opponent_lead_result["leader"])
            print("Opponent lead card:", opponent_lead_result["lead_card"])

            if "responder" in opponent_lead_result:
                print("Opponent response player:", opponent_lead_result["responder"])
                print("Opponent response card:", opponent_lead_result["response_card"])

        print("Candidate card:", step["candidate_card"])
        print("Trick:", detailed_result["trick"])
        print("Did win:", detailed_result["did_win"])
        if "candidate_card_won" in detailed_result:
            print("Candidate card won:", detailed_result["candidate_card_won"])
        if "local_side_won" in detailed_result:
            print("Local side won:", detailed_result["local_side_won"])
        print("Trick points:", detailed_result["trick_points"])
        print("Winner role:", completed_trick["winner_role"])

    stopped_decision = result.get("stopped_recommendation_decision")
    if stopped_decision is not None:
        if isinstance(stopped_decision, dict):
            search = stopped_decision["bounded_search_result"]
            consumed = search["consumed_budget"]
            step_index = stopped_decision["step_index"]
            requested_method = stopped_decision["requested_method"]
            effective_method = stopped_decision["effective_method"]
            search_status = search["status"]
            search_stop_reason = search["stop_reason"]
            completed_world_count = consumed["completed_world_count"]
            selected_world_count = consumed["selected_world_count"]
        else:
            search = stopped_decision.bounded_search_result
            consumed = search.consumed_budget
            step_index = stopped_decision.step_index
            requested_method = stopped_decision.requested_method
            effective_method = stopped_decision.effective_method
            search_status = search.status
            search_stop_reason = search.stop_reason
            completed_world_count = consumed.completed_world_count
            selected_world_count = consumed.selected_world_count
        print()
        print("Stopped recommendation decision:", step_index)
        print("Requested recommendation method:", requested_method)
        print("Effective recommendation method:", effective_method)
        print("Search status:", search_status)
        print("Search stop reason:", search_stop_reason)
        print(
            "Search completed worlds:",
            f"{completed_world_count} of {selected_world_count}",
        )
        print("No local recommendation was available; no local card was executed.")

    print()
    print("Final state")
    if isinstance(final_state, dict):
        print("Remaining hand:", final_state["hand"])
        print("Completed tricks:", final_state["completed_tricks"])
        print("Declarer points:", final_state["declarer_points"])
        print("Defender points:", final_state["defender_points"])
        print("Next player:", final_state["next_player"])
    else:
        print("Remaining hand:", final_state.hand)
        print("Completed tricks:", final_state.completed_tricks)
        print("Declarer points:", final_state.declarer_points)
        print("Defender points:", final_state.defender_points)
        print("Next player:", final_state.next_player)


def print_policy_comparison_result(result: dict[str, Any]) -> None:
    """
    Prints a compact policy comparison result.
    """
    print()
    print("Policy comparison")
    print("Requested steps:", result["requested_step_count"])
    print("Random seed:", result["random_seed"])
    print("Expected-value samples:", result["expected_value_sample_count"])
    print("Use basic opponent strategy:", result["use_basic_opponent_strategy"])
    print("Strict context:", result["strict_context"])
    print("Opponent lead policy:", result.get("opponent_lead_policy", "lowest_point"))
    print(
        "Opponent response policy:",
        result.get("opponent_response_policy", "lowest_point"),
    )
    if "hidden_world" in result:
        hidden_world_summary = result["hidden_world"]
        print("Hidden-world mode:", hidden_world_summary["mode"])
        print("Policies shared one root world:", hidden_world_summary["shared_root_world"])
        print(
            "Policy paths use independent worlds:",
            hidden_world_summary["independent_path_worlds"],
        )
    print_hidden_card_inference_summary(result.get("hidden_card_inference_summary"))

    print()
    print(f"{'Policy':<24}{'Steps':>7}{'Decl. +':>10}{'Def. +':>10}{'Swing':>10}{'Local':>10}")
    print("-" * 71)

    for policy_result in result["policy_results"]:
        local_point_swing = policy_result.get(
            "local_point_swing",
            policy_result["final_point_swing"],
        )
        print(
            f"{policy_result['policy']:<24}"
            f"{policy_result['steps_simulated']:>7}"
            f"{policy_result['declarer_points_gained']:>10}"
            f"{policy_result['defender_points_gained']:>10}"
            f"{policy_result['final_point_swing']:>10}"
            f"{local_point_swing:>10}"
        )
        if "recommendation_summary" in policy_result:
            recommendation_summary = policy_result["recommendation_summary"]
            print(
                "  Search decisions: "
                f"{recommendation_summary['decisions_attempted']} attempted, "
                f"{recommendation_summary['decisions_executed']} executed, "
                f"{recommendation_summary['search_recommendations_used']} Search, "
                f"{recommendation_summary['immediate_fallbacks_used']} fallback, "
                f"{recommendation_summary['no_recommendation_count']} no recommendation"
            )
        if "eligible_for_recommendation" in policy_result:
            print(
                "  Eligible for recommendation:",
                policy_result["eligible_for_recommendation"],
            )
            if policy_result["ineligible_reason"] is not None:
                print("  Ineligible reason:", policy_result["ineligible_reason"])

    recommended_policy = result.get("recommended_policy")

    print()

    if recommended_policy is not None:
        print("Recommended policy:", recommended_policy["policy"])
        print("Recommendation reason:", recommended_policy["reason"])
        print("Recommended final point swing:", recommended_policy["final_point_swing"])
        print(
            "Recommended local point swing:",
            recommended_policy.get(
                "local_point_swing",
                recommended_policy["final_point_swing"],
            ),
        )
    else:
        print("Recommended policy: none")


def print_multi_step_score_summary(summary: dict[str, Any]) -> None:
    """
    Prints a compact multi-step score summary.
    """
    score_summary = summary["score_summary"]

    print()
    print("Multi-step score summary")
    print("Requested steps:", summary["requested_step_count"])
    print("Steps simulated:", summary["steps_simulated"])
    print("Stop reason:", summary["stop_reason"])
    print("Card selection policy:", summary["card_selection_policy"])
    print("Strict context:", summary["strict_context"])
    print("Initial declarer points:", score_summary["initial_declarer_points"])
    print("Initial defender points:", score_summary["initial_defender_points"])
    print("Final declarer points:", score_summary["final_declarer_points"])
    print("Final defender points:", score_summary["final_defender_points"])
    print("Declarer points gained:", score_summary["declarer_points_gained"])
    print("Defender points gained:", score_summary["defender_points_gained"])
    print("Final point swing:", score_summary["final_point_swing"])
    if "local_point_swing" in score_summary:
        print("Local point swing:", score_summary["local_point_swing"])


def run_json_position_analysis(
    file_path: str,
    sample_count_override: int | None = None,
    random_seed_override: int | None = None,
    opponent_strategy_override: str | None = None,
    left_opponent_lead_policy_override: str | None = None,
    left_opponent_response_policy_override: str | None = None,
    right_opponent_lead_policy_override: str | None = None,
    right_opponent_response_policy_override: str | None = None,
    output_path: str | None = None,
    multi_step_count: int | None = None,
    card_selection_policy: str | None = None,
    expected_value_sample_count: int = DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT,
    strict_context: bool = False,
    compare_policies: bool = False,
    comparison_only: bool = False,
    opponent_policy_preset_override: str | None = None,
    opponent_lead_policy_override: str | None = None,
    opponent_response_policy_override: str | None = None,
    use_profile_presets_override: bool = False,
    opponent_statistics_file: str | None = None,
    left_opponent_player_id: str | None = None,
    right_opponent_player_id: str | None = None,
    quiet: bool = False,
    include_provenance: bool = False,
) -> None:
    if comparison_only and not compare_policies:
        raise ValueError("comparison_only requires compare_policies to be enabled.")

    if multi_step_count is not None and multi_step_count <= 0:
        raise ValueError("multi_step_count must be a positive integer.")

    position_data = load_position_from_json(file_path)
    if "game_shortening" in position_data and (multi_step_count is not None or compare_policies):
        raise ValueError(
            "Structured game_shortening cannot be combined with multi-step simulation "
            "or policy comparison."
        )
    shortening_value = position_data.get("game_shortening")
    is_open_card_throw = (
        isinstance(shortening_value, dict)
        and shortening_value.get("kind") == "open_card_throw"
    )
    if is_open_card_throw and any(
        value is not None
        for value in [
            opponent_statistics_file,
            left_opponent_player_id,
            right_opponent_player_id,
        ]
    ):
        raise ValueError(
            "Open card throw cannot be combined with opponent-statistics or "
            "live profile-binding options."
        )
    validate_live_opponent_profile_options(
        position_data=position_data,
        opponent_statistics_file=opponent_statistics_file,
        left_opponent_player_id=left_opponent_player_id,
        right_opponent_player_id=right_opponent_player_id,
        use_profile_presets_override=use_profile_presets_override,
    )
    external_documents = None
    if opponent_statistics_file is not None:
        external_documents = ApplicationExternalDocuments(
            opponent_statistics_document=load_external_opponent_statistics_document(
                opponent_statistics_file
            ),
            opponent_statistics_reference=opponent_statistics_file,
        )
    result, _artifacts = execute_legacy_application(
        position_data,
        input_reference=file_path,
        options=ApplicationExecutionOptions(
            position_analysis=PositionAnalysisApplicationOptions(
                sample_count_override=sample_count_override,
                random_seed_override=random_seed_override,
                opponent_strategy_override=opponent_strategy_override,
                left_opponent_lead_policy_override=(
                    left_opponent_lead_policy_override
                ),
                left_opponent_response_policy_override=(
                    left_opponent_response_policy_override
                ),
                right_opponent_lead_policy_override=(
                    right_opponent_lead_policy_override
                ),
                right_opponent_response_policy_override=(
                    right_opponent_response_policy_override
                ),
                multi_step_count=multi_step_count,
                card_selection_policy=card_selection_policy,
                expected_value_sample_count=expected_value_sample_count,
                strict_context=strict_context,
                compare_policies=compare_policies,
                comparison_only=comparison_only,
                opponent_policy_preset_override=(
                    opponent_policy_preset_override
                ),
                opponent_lead_policy_override=opponent_lead_policy_override,
                opponent_response_policy_override=(
                    opponent_response_policy_override
                ),
                use_profile_presets_override=use_profile_presets_override,
                left_opponent_player_id=left_opponent_player_id,
                right_opponent_player_id=right_opponent_player_id,
            )
        ),
        external_documents=external_documents,
        include_provenance=include_provenance,
    )
    if output_path is not None:
        write_analysis_result_to_json(output_path=output_path, result=result)
    if quiet:
        return
    if not comparison_only:
        print_analysis_result(result)
    if multi_step_count is not None and not comparison_only:
        print_multi_step_result(result["multi_step_result"])
    if compare_policies:
        print_policy_comparison_result(result["policy_comparison_result"])
    if output_path is not None:
        print()
        print("Output file written:", output_path)
    print_field_provenance_summary(result)
    return


def run_json_historical_game_analysis(
    file_path: str,
    output_path: str | None = None,
    quiet: bool = False,
    historical_decision_snapshots: bool = False,
    historical_game_review: bool = False,
    historical_search_review: bool = False,
    historical_replay_coaching: bool = False,
    search_seed: int | None = None,
    search_budget_profile: str = HISTORICAL_REVIEW_SEARCH_BUDGET_PROFILE,
    sample_count: int | None = None,
    base_random_seed: int | None = None,
    opponent_statistics_file: str | None = None,
    opponent_policy_preset_override: str | None = None,
    opponent_lead_policy_override: str | None = None,
    opponent_response_policy_override: str | None = None,
    left_opponent_lead_policy_override: str | None = None,
    left_opponent_response_policy_override: str | None = None,
    right_opponent_lead_policy_override: str | None = None,
    right_opponent_response_policy_override: str | None = None,
    include_provenance: bool = False,
) -> None:
    """Runs the complete historical-game workflow."""
    root_document = load_json_object(file_path)
    external_documents = None
    if opponent_statistics_file is not None:
        external_documents = ApplicationExternalDocuments(
            opponent_statistics_document=load_external_opponent_statistics_document(
                opponent_statistics_file
            ),
            opponent_statistics_reference=opponent_statistics_file,
        )
    result, _artifacts = execute_legacy_application(
        root_document,
        input_reference=file_path,
        options=ApplicationExecutionOptions(
            historical_game=HistoricalGameApplicationOptions(
                decision_snapshots=historical_decision_snapshots,
                immediate_review=historical_game_review,
                search_review=historical_search_review,
                replay_coaching=historical_replay_coaching,
                search_seed=search_seed,
                search_budget_profile=search_budget_profile,
                immediate_sample_count=sample_count,
                immediate_base_random_seed=base_random_seed,
                opponent_policy_preset_override=(
                    opponent_policy_preset_override
                ),
                opponent_lead_policy_override=opponent_lead_policy_override,
                opponent_response_policy_override=(
                    opponent_response_policy_override
                ),
                left_opponent_lead_policy_override=(
                    left_opponent_lead_policy_override
                ),
                left_opponent_response_policy_override=(
                    left_opponent_response_policy_override
                ),
                right_opponent_lead_policy_override=(
                    right_opponent_lead_policy_override
                ),
                right_opponent_response_policy_override=(
                    right_opponent_response_policy_override
                ),
                use_profile_presets_override=(
                    opponent_statistics_file is not None
                ),
            )
        ),
        external_documents=external_documents,
        include_provenance=include_provenance,
    )
    if output_path is not None:
        write_analysis_result_to_json(output_path=output_path, result=result)
    if quiet:
        return
    print_historical_game_result(result)
    historical_game_summary = result["historical_game_summary"]
    if historical_search_review:
        print_historical_search_review_result(
            historical_game_summary["historical_search_review_summary"]
        )
    if historical_replay_coaching:
        print_historical_replay_coaching_result(
            historical_game_summary["historical_replay_coaching_summary"]
        )
    if output_path is not None:
        print()
        print("Output file written:", output_path)
    print_field_provenance_summary(result)
    return


def run_json_training_dataset_conversion(
    file_path: str,
    output_path: str | None = None,
    quiet: bool = False,
    include_provenance: bool = False,
) -> None:
    """Runs deterministic training-dataset validation and sample generation."""
    root_document = load_json_object(file_path)
    result, _artifacts = execute_legacy_application(
        root_document,
        input_reference=file_path,
        options=ApplicationExecutionOptions(
            training_dataset=TrainingDatasetApplicationOptions(operation="summary")
        ),
        include_provenance=include_provenance,
    )
    if output_path is not None:
        write_analysis_result_to_json(output_path=output_path, result=result)
    if quiet:
        return
    print_training_dataset_result(result)
    if output_path is not None:
        print()
        print("Output file written:", output_path)
    print_field_provenance_summary(result)
    return


def run_json_training_dataset_preparation(
    file_path: str,
    output_path: str | None = None,
    quiet: bool = False,
    include_provenance: bool = False,
) -> None:
    """Runs one mode-derived automatic Dataset preparation workflow."""
    root_document = load_json_object(file_path)
    result, _artifacts = execute_legacy_application(
        root_document,
        input_reference=file_path,
        include_provenance=include_provenance,
    )
    if output_path is not None:
        write_analysis_result_to_json(output_path=output_path, result=result)
    if quiet:
        return
    print_training_dataset_preparation_application_result(root_document, result)
    if output_path is not None:
        print()
        print("Output file written:", output_path)
    print_field_provenance_summary(result)
    return


def run_json_bounded_search_evaluation(
    file_path: str,
    *,
    search_seed: int,
    partitions: tuple[str, ...] = DEFAULT_BOUNDED_SEARCH_EVALUATION_PARTITIONS,
    search_budget_profile: str = EVALUATION_SEARCH_BUDGET_PROFILE,
    max_decisions: int | None = None,
    output_path: str | None = None,
    quiet: bool = False,
    include_provenance: bool = False,
) -> None:
    """Runs deterministic bounded-Search evaluation on selected dataset records."""
    root_document = load_json_object(file_path)
    result, _artifacts = execute_legacy_application(
        root_document,
        input_reference=file_path,
        options=ApplicationExecutionOptions(
            training_dataset=TrainingDatasetApplicationOptions(
                operation="bounded_search_evaluation",
                bounded_search_seed=search_seed,
                bounded_search_partitions=partitions,
                bounded_search_budget_profile=search_budget_profile,
                bounded_search_max_decisions=max_decisions,
            )
        ),
        include_provenance=include_provenance,
    )
    if output_path is not None:
        write_analysis_result_to_json(output_path=output_path, result=result)
    if quiet:
        return
    print_bounded_search_evaluation_result(result)
    if output_path is not None:
        print()
        print("Output file written:", output_path)
    print_field_provenance_summary(result)
    return


def run_json_dataset_partition_audit(
    file_path: str,
    requested_mode: str | None = None,
    output_path: str | None = None,
    quiet: bool = False,
    include_provenance: bool = False,
) -> None:
    """Audits training-dataset player overlap without generating samples."""
    root_document = load_json_object(file_path)
    try:
        result, _artifacts = execute_legacy_application(
            root_document,
            input_reference=file_path,
            options=ApplicationExecutionOptions(
                training_dataset=TrainingDatasetApplicationOptions(
                    operation="partition_audit",
                    partition_audit_mode=requested_mode,
                )
            ),
            include_provenance=include_provenance,
        )
    except (SkatAIWorkflowError, ValueError) as error:
        if not isinstance(error, SkatAIWorkflowError) and (
            "contradicts declared partition policy" not in str(error)
        ):
            raise
        raise CliUsageError(str(error)) from error
    if output_path is not None:
        write_analysis_result_to_json(output_path=output_path, result=result)
    if quiet:
        return
    print_dataset_partition_audit_result(result)
    if output_path is not None:
        print()
        print("Output file written:", output_path)
    print_field_provenance_summary(result)
    return


def run_json_rolling_opponent_policy_evaluation(
    file_path: str,
    source_partitions: tuple[str, ...] = DEFAULT_SOURCE_PARTITIONS,
    evaluation_partitions: tuple[str, ...] = DEFAULT_EVALUATION_PARTITIONS,
    output_path: str | None = None,
    quiet: bool = False,
    include_provenance: bool = False,
) -> None:
    """Runs rolling profile-derived behavioral policy evaluation."""
    root_document = load_json_object(file_path)
    result, _artifacts = execute_legacy_application(
        root_document,
        input_reference=file_path,
        options=ApplicationExecutionOptions(
            training_dataset=TrainingDatasetApplicationOptions(
                operation="rolling_opponent_policy_evaluation",
                rolling_source_partitions=source_partitions,
                rolling_evaluation_partitions=evaluation_partitions,
            )
        ),
        include_provenance=include_provenance,
    )
    if output_path is not None:
        write_analysis_result_to_json(output_path=output_path, result=result)
    if quiet:
        return
    print_rolling_opponent_policy_evaluation_result(result)
    if output_path is not None:
        print()
        print("Output file written:", output_path)
    print_field_provenance_summary(result)
    return


def run_json_historical_opponent_statistics_aggregation(
    file_path: str,
    included_partitions: tuple[str, ...] | None = None,
    before: str | None = None,
    output_path: str | None = None,
    export_path: str | None = None,
    quiet: bool = False,
    include_provenance: bool = False,
) -> None:
    """Aggregates historical statistics without generating training samples."""
    root_document = load_json_object(file_path)
    result, artifacts = execute_legacy_application(
        root_document,
        input_reference=file_path,
        options=ApplicationExecutionOptions(
            training_dataset=TrainingDatasetApplicationOptions(
                operation="historical_opponent_statistics_aggregation",
                aggregation_included_partitions=included_partitions,
                aggregation_before=before,
                export_opponent_statistics=export_path is not None,
            )
        ),
        include_provenance=include_provenance,
    )
    if output_path is not None:
        write_analysis_result_to_json(output_path=output_path, result=result)
    if export_path is not None:
        write_analysis_result_to_json(
            output_path=export_path,
            result=artifacts["opponent_statistics_input"],
        )
    if quiet:
        return
    print_historical_opponent_statistics_result(result)
    if output_path is not None:
        print()
        print("Output file written:", output_path)
    if export_path is not None:
        print("Exported opponent statistics to", f"{export_path}.")
    print_field_provenance_summary(result)
    return


def run_json_fixed_three_player_historical_list_analysis(
    file_path: str,
    output_path: str | None = None,
    quiet: bool = False,
    include_provenance: bool = False,
) -> None:
    """Runs one complete historical 36-position list aggregation."""
    root_document = load_json_object(file_path)
    result, _artifacts = execute_legacy_application(
        root_document,
        input_reference=file_path,
        include_provenance=include_provenance,
    )
    if output_path is not None:
        write_analysis_result_to_json(output_path=output_path, result=result)
    if quiet:
        return
    print_fixed_three_player_historical_list_result(result)
    if output_path is not None:
        print()
        print("Output file written:", output_path)
    print_field_provenance_summary(result)
    return


def run_json_fixed_three_player_historical_list_comparison(
    file_path: str,
    output_path: str | None = None,
    quiet: bool = False,
    include_provenance: bool = False,
) -> None:
    """Aggregates each ordered source once and compares it with the first source."""
    root_document = load_json_object(file_path)
    result, _artifacts = execute_legacy_application(
        root_document,
        input_reference=file_path,
        include_provenance=include_provenance,
    )
    if output_path is not None:
        write_analysis_result_to_json(output_path=output_path, result=result)
    if quiet:
        return
    print_fixed_three_player_historical_list_comparison_result(result)
    if output_path is not None:
        print()
        print("Output file written:", output_path)
    print_field_provenance_summary(result)
    return


def run_json_opponent_statistics_conversion(
    file_path: str,
    output_path: str | None = None,
    quiet: bool = False,
    include_provenance: bool = False,
) -> None:
    """Runs deterministic external opponent-statistics validation and normalization."""
    root_document = load_json_object(file_path)
    result, _artifacts = execute_legacy_application(
        root_document,
        input_reference=file_path,
        include_provenance=include_provenance,
    )
    if output_path is not None:
        write_analysis_result_to_json(output_path=output_path, result=result)
    if quiet:
        return
    print_opponent_statistics_result(result)
    if output_path is not None:
        print()
        print("Output file written:", output_path)
    print_field_provenance_summary(result)
    return


def _invocation_command(invocation_style: str) -> str:
    commands = {
        "installed": INSTALLED_CLI_COMMAND,
        "module": MODULE_CLI_COMMAND,
        "legacy": LEGACY_CLI_COMMAND,
    }
    try:
        return commands[invocation_style]
    except KeyError as error:
        raise ValueError(
            f"invocation_style must be one of {CLI_INVOCATION_STYLES}."
        ) from error


def _invocation_examples(invocation_style: str) -> str:
    command = _invocation_command(invocation_style)
    if invocation_style == "legacy":
        paths = {
            "position": "examples/grand_second_position.json",
            "historical": "examples/historical_grand_normal_completion.json",
            "list": "examples/fixed_three_player_historical_list_mixed.json",
            "comparison": "examples/fixed_three_player_historical_list_comparison.json",
            "dataset": "examples/training_dataset_normal_play.json",
            "preparation": "examples/training_dataset_preparation_known_opponent.json",
            "statistics": "examples/opponent_statistics.json",
        }
    else:
        paths = {
            "position": "position.json",
            "historical": "historical-game.json",
            "list": "historical-list.json",
            "comparison": "historical-list-comparison.json",
            "dataset": "training-dataset.json",
            "preparation": "training-dataset-preparation.json",
            "statistics": "opponent-statistics.json",
        }
    return (
        "Examples:\n"
        f"  {command}\n"
        f"  {command} --input {paths['position']}\n"
        f"  {command} --input {paths['position']} --multi-step 2\n"
        f"  {command} --input {paths['position']} --multi-step 1 --compare-policies\n"
        f"  {command} --input {paths['position']} --multi-step 1 "
        "--compare-policies --comparison-only\n"
        f"  {command} --input {paths['historical']}\n"
        f"  {command} --input {paths['list']}\n"
        f"  {command} --input {paths['comparison']}\n"
        f"  {command} --input {paths['dataset']}\n"
        f"  {command} --input {paths['preparation']}\n"
        f"  {command} --input {paths['statistics']}"
    )


def build_argument_parser(
    invocation_style: str = "installed",
) -> argparse.ArgumentParser:
    command = _invocation_command(invocation_style)
    parser = argparse.ArgumentParser(
        prog=command,
        description=(
            "Analyze a Skat position, replay a historical game, expose a complete "
            "historical 36-position list or independent-list comparison, prepare or "
            "convert a training dataset, or normalize opponent statistics from JSON."
        ),
        epilog=_invocation_examples(invocation_style),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"skat-ai {__version__}",
        help="Show the installed skat-ai Package version and exit.",
    )

    parser.add_argument(
        "--input",
        default="input_position.json",
        help=(
            "Read position-analysis, historical-game, historical-list, "
            "historical-list-comparison, training-dataset-preparation, training-dataset, "
            "or opponent-statistics input from this JSON file. "
            "Default: input_position.json."
        ),
    )

    parser.add_argument(
        "--samples",
        type=int,
        default=None,
        help="Override the JSON sample_count for Monte Carlo card analysis.",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Override the JSON random_seed for reproducible analysis.",
    )

    parser.add_argument(
        "--opponent-strategy",
        choices=["basic", "random"],
        default=None,
        help="Override legacy opponent strategy from the JSON input file.",
    )

    parser.add_argument(
        "--output",
        default=None,
        help="Write the structured analysis result JSON to this path.",
    )

    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress successful human-readable stdout output.",
    )

    parser.add_argument(
        "--include-provenance",
        action="store_true",
        help="Include a public-safe field-provenance sidecar in Root JSON output.",
    )

    parser.add_argument(
        "--audit-dataset-partitions",
        action="store_true",
        help="Audit exact stable-player membership and overlap across dataset partitions.",
    )
    parser.add_argument(
        "--dataset-partition-mode",
        choices=("report_only", "known_opponent", "unseen_player"),
        default=None,
        help="Evaluate the partition audit under this explicit policy mode.",
    )
    parser.add_argument(
        "--aggregate-opponent-statistics",
        action="store_true",
        help="Aggregate exact reusable opponent statistics from a training dataset.",
    )
    parser.add_argument(
        "--opponent-statistics-partition",
        action="append",
        choices=("train", "validation", "test"),
        default=None,
        help="Include this training-dataset partition; may be repeated.",
    )
    parser.add_argument(
        "--opponent-statistics-before",
        default=None,
        help="Include only games with played_at strictly before this RFC 3339 instant.",
    )
    parser.add_argument(
        "--export-opponent-statistics",
        default=None,
        help="Write a standalone reusable opponent_statistics_input JSON file.",
    )
    parser.add_argument(
        "--evaluate-opponent-policy-profiles",
        "--evaluate-rolling-opponent-policies",
        action="store_true",
        help="Evaluate rolling as-of profile policies against simple_lowest.",
    )
    parser.add_argument(
        "--profile-source-partition",
        action="append",
        choices=("train", "validation", "test"),
        default=None,
        help="Select a profile-history source partition; may be repeated.",
    )
    parser.add_argument(
        "--profile-evaluation-partition",
        action="append",
        choices=("train", "validation", "test"),
        default=None,
        help="Select a policy-evaluation target partition; may be repeated.",
    )

    parser.add_argument(
        "--historical-decision-snapshots",
        action="store_true",
        help=("Add one information-safe pre-play snapshot per supplied historical play."),
    )

    parser.add_argument(
        "--historical-game-review",
        action="store_true",
        help=("Evaluate every supplied historical card decision with decision-time information."),
    )
    parser.add_argument(
        "--historical-search-review",
        action="store_true",
        help="Evaluate every historical decision with bounded Search and Immediate.",
    )
    parser.add_argument(
        "--historical-replay-coaching",
        action="store_true",
        help="Build the complete Replay Coaching Report for a historical game.",
    )
    parser.add_argument(
        "--search-seed",
        type=int,
        default=None,
        help=(
            "Use this explicit base seed for Historical Search Review, Replay Coaching, "
            "or evaluation."
        ),
    )
    parser.add_argument(
        "--search-budget-profile",
        choices=SEARCH_BUDGET_PROFILE_IDENTIFIERS,
        default=None,
        help=(
            "Select a versioned Historical Search Review, Replay Coaching, or evaluation "
            "budget profile."
        ),
    )
    parser.add_argument(
        "--evaluate-bounded-search",
        action="store_true",
        help="Evaluate bounded Search against Immediate on a training dataset.",
    )
    parser.add_argument(
        "--search-evaluation-partition",
        action="append",
        choices=("train", "validation", "test"),
        default=None,
        help="Select a bounded-Search evaluation partition; may be repeated.",
    )
    parser.add_argument(
        "--search-evaluation-max-decisions",
        type=int,
        default=None,
        help="Evaluate only this deterministic prefix of selected decisions.",
    )

    parser.add_argument(
        "--multi-step",
        type=int,
        default=None,
        help="Run a phase-aware simulation for this many local decision steps.",
    )

    parser.add_argument(
        "--card-policy",
        choices=VALID_MULTI_STEP_POLICIES,
        default=None,
        help=(
            "Choose local cards during multi-step simulation. Search policies require "
            "matching JSON recommendation settings; otherwise the default is first_legal."
        ),
    )

    parser.add_argument(
        "--expected-value-samples",
        type=int,
        default=None,
        help=("Samples per candidate for the highest_expected_value card policy. Default: 100."),
    )

    parser.add_argument(
        "--strict-context",
        action="store_true",
        help=(
            "Fail multi-step simulation on duplicate cards, ownership drift, "
            "or hidden-world accounting violations."
        ),
    )

    parser.add_argument(
        "--compare-policies",
        action="store_true",
        help=(
            "Compare the four legacy local policies and append the configured Search "
            "method when present."
        ),
    )

    parser.add_argument(
        "--comparison-only",
        action="store_true",
        help="Print only policy comparison details; requires --compare-policies.",
    )

    parser.add_argument(
        "--opponent-lead-policy",
        choices=VALID_OPPONENT_CARD_POLICIES,
        default=None,
        help="Set both opponents' lead policy for multi-step simulation.",
    )

    parser.add_argument(
        "--opponent-response-policy",
        choices=VALID_OPPONENT_CARD_POLICIES,
        default=None,
        help=(
            "Set both opponents' response policy for immediate analysis and multi-step simulation."
        ),
    )

    parser.add_argument(
        "--opponent-policy-preset",
        choices=[
            "simple_lowest",
            "cautious_defender",
            "aggressive_points",
            "random",
        ],
        default=None,
        help=("Apply an opponent policy preset to immediate analysis and multi-step simulation."),
    )

    parser.add_argument(
        "--use-profile-presets",
        action="store_true",
        help=(
            "Use player profiles to derive opponent policy presets for immediate "
            "analysis and multi-step simulation."
        ),
    )

    parser.add_argument(
        "--opponent-statistics-file",
        default=None,
        help=(
            "Attach validated external opponent statistics to a live position or "
            "time-safe historical game review."
        ),
    )
    parser.add_argument(
        "--left-opponent-player-id",
        default=None,
        help="Bind this exact external player ID to the left opponent.",
    )
    parser.add_argument(
        "--right-opponent-player-id",
        default=None,
        help="Bind this exact external player ID to the right opponent.",
    )

    parser.add_argument(
        "--left-opponent-lead-policy",
        choices=VALID_OPPONENT_CARD_POLICIES,
        default=None,
        help="Override only left opponent's lead policy for multi-step simulation.",
    )
    parser.add_argument(
        "--left-opponent-response-policy",
        choices=VALID_OPPONENT_CARD_POLICIES,
        default=None,
        help=(
            "Override only left opponent's response policy for immediate analysis "
            "and multi-step simulation."
        ),
    )
    parser.add_argument(
        "--right-opponent-lead-policy",
        choices=VALID_OPPONENT_CARD_POLICIES,
        default=None,
        help="Override only right opponent's lead policy for multi-step simulation.",
    )
    parser.add_argument(
        "--right-opponent-response-policy",
        choices=VALID_OPPONENT_CARD_POLICIES,
        default=None,
        help=(
            "Override only right opponent's response policy for immediate analysis "
            "and multi-step simulation."
        ),
    )

    return parser


def parse_arguments(
    argv: list[str] | tuple[str, ...] | None = None,
    *,
    invocation_style: str = "installed",
) -> argparse.Namespace:
    return build_argument_parser(invocation_style).parse_args(argv)


def validate_cli_arguments(
    args: argparse.Namespace,
    workflow: str | None = None,
) -> None:
    """Validates semantic CLI-only argument combinations."""
    if args.samples is not None and args.samples <= 0:
        raise CliUsageError("--samples must be a positive integer.")

    if args.samples is not None and args.samples > MAX_SAMPLE_COUNT:
        raise CliUsageError(f"--samples must be at most {MAX_SAMPLE_COUNT}.")

    if args.expected_value_samples is not None and args.expected_value_samples <= 0:
        raise CliUsageError("--expected-value-samples must be a positive integer.")

    if args.expected_value_samples is not None and args.expected_value_samples > MAX_SAMPLE_COUNT:
        raise CliUsageError(f"--expected-value-samples must be at most {MAX_SAMPLE_COUNT}.")

    if args.multi_step is not None and args.multi_step <= 0:
        raise CliUsageError("--multi-step must be a positive integer.")

    aggregate_statistics = getattr(args, "aggregate_opponent_statistics", False)
    evaluate_profiles = getattr(args, "evaluate_opponent_policy_profiles", False)
    evaluate_search = getattr(args, "evaluate_bounded_search", False)
    audit_partitions = getattr(args, "audit_dataset_partitions", False)
    dataset_partition_mode = getattr(args, "dataset_partition_mode", None)
    if dataset_partition_mode is not None and not audit_partitions:
        raise CliUsageError("--dataset-partition-mode requires --audit-dataset-partitions.")
    if audit_partitions and workflow != "training_dataset":
        raise CliUsageError(
            "--audit-dataset-partitions is supported only for training_dataset_input."
        )
    evaluation_only_options = {
        "--profile-source-partition": getattr(args, "profile_source_partition", None) is not None,
        "--profile-evaluation-partition": getattr(args, "profile_evaluation_partition", None)
        is not None,
    }
    supplied_evaluation_options = [
        option for option, supplied in evaluation_only_options.items() if supplied
    ]
    if supplied_evaluation_options and not evaluate_profiles:
        raise CliUsageError(
            "Opponent-policy profile evaluation partition options require "
            "--evaluate-opponent-policy-profiles: "
            f"{', '.join(supplied_evaluation_options)}."
        )
    if evaluate_profiles and workflow != "training_dataset":
        raise CliUsageError(
            "--evaluate-opponent-policy-profiles is supported only for training_dataset_input."
        )
    search_evaluation_options = {
        "--search-evaluation-partition": getattr(
            args, "search_evaluation_partition", None
        )
        is not None,
        "--search-evaluation-max-decisions": getattr(
            args, "search_evaluation_max_decisions", None
        )
        is not None,
    }
    supplied_search_evaluation_options = [
        option for option, supplied in search_evaluation_options.items() if supplied
    ]
    if supplied_search_evaluation_options and not evaluate_search:
        raise CliUsageError(
            "Bounded-Search evaluation options require --evaluate-bounded-search: "
            f"{', '.join(supplied_search_evaluation_options)}."
        )
    if evaluate_search and workflow != "training_dataset":
        raise CliUsageError(
            "--evaluate-bounded-search is supported only for training_dataset_input."
        )
    historical_search = getattr(args, "historical_search_review", False)
    historical_coaching = getattr(args, "historical_replay_coaching", False)
    search_seed = getattr(args, "search_seed", None)
    search_budget_profile = getattr(args, "search_budget_profile", None)
    if (historical_search or historical_coaching or evaluate_search) and search_seed is None:
        raise CliUsageError(
            "Historical Search Review, Historical Replay Coaching, and bounded-Search "
            "evaluation require --search-seed."
        )
    if search_seed is not None and not (
        historical_search or historical_coaching or evaluate_search
    ):
        raise CliUsageError(
            "--search-seed requires --historical-search-review, "
            "--historical-replay-coaching, or --evaluate-bounded-search."
        )
    if search_budget_profile is not None and not (
        historical_search or historical_coaching or evaluate_search
    ):
        raise CliUsageError(
            "--search-budget-profile requires --historical-search-review or "
            "--historical-replay-coaching or --evaluate-bounded-search."
        )
    if (
        getattr(args, "search_evaluation_max_decisions", None) is not None
        and args.search_evaluation_max_decisions <= 0
    ):
        raise CliUsageError("--search-evaluation-max-decisions must be positive.")
    source_partitions = tuple(
        getattr(args, "profile_source_partition", None) or DEFAULT_SOURCE_PARTITIONS
    )
    evaluation_partitions = tuple(
        getattr(args, "profile_evaluation_partition", None) or DEFAULT_EVALUATION_PARTITIONS
    )
    overlap = sorted(set(source_partitions).intersection(evaluation_partitions))
    if evaluate_profiles and overlap:
        raise CliUsageError(
            f"Profile source and evaluation partitions must be disjoint; overlap: {overlap}."
        )
    aggregation_only_options = {
        "--opponent-statistics-partition": getattr(args, "opponent_statistics_partition", None)
        is not None,
        "--opponent-statistics-before": getattr(args, "opponent_statistics_before", None)
        is not None,
        "--export-opponent-statistics": getattr(args, "export_opponent_statistics", None)
        is not None,
    }
    supplied_aggregation_options = [
        option for option, supplied in aggregation_only_options.items() if supplied
    ]
    if supplied_aggregation_options and not aggregate_statistics:
        raise CliUsageError(
            "Historical opponent-statistics options require "
            "--aggregate-opponent-statistics: "
            f"{', '.join(supplied_aggregation_options)}."
        )
    if aggregate_statistics and workflow != "training_dataset":
        raise CliUsageError(
            "--aggregate-opponent-statistics is supported only for training_dataset_input."
        )
    if aggregate_statistics:
        paths = [
            ("--input", args.input),
            ("--output", args.output),
            (
                "--export-opponent-statistics",
                getattr(args, "export_opponent_statistics", None),
            ),
        ]
        resolved_paths = [
            (option, Path(path).resolve()) for option, path in paths if path is not None
        ]
        for index, (first_option, first_path) in enumerate(resolved_paths):
            for second_option, second_path in resolved_paths[index + 1 :]:
                if first_path == second_path:
                    raise CliUsageError(
                        f"{first_option} and {second_option} must use different paths."
                    )

    if args.comparison_only and not args.compare_policies:
        raise CliUsageError("--comparison-only requires --compare-policies.")

    if args.compare_policies and args.multi_step is None:
        raise CliUsageError("--compare-policies requires --multi-step.")

    opponent_statistics_file = getattr(args, "opponent_statistics_file", None)
    left_player_id = getattr(args, "left_opponent_player_id", None)
    right_player_id = getattr(args, "right_opponent_player_id", None)
    if opponent_statistics_file is None and (
        left_player_id is not None or right_player_id is not None
    ):
        raise CliUsageError(
            "--left-opponent-player-id and --right-opponent-player-id require "
            "--opponent-statistics-file."
        )
    if (
        opponent_statistics_file is not None
        and not getattr(args, "historical_game_review", False)
        and workflow != "historical_game"
        and (left_player_id is None and right_player_id is None)
    ):
        raise CliUsageError(
            "--opponent-statistics-file requires --left-opponent-player-id, "
            "--right-opponent-player-id, or both."
        )
    for option_name, player_id in (
        ("--left-opponent-player-id", left_player_id),
        ("--right-opponent-player-id", right_player_id),
    ):
        if player_id is not None and (not player_id or player_id != player_id.strip()):
            raise CliUsageError(f"{option_name} must be a non-empty, non-padded string.")
    if left_player_id is not None and left_player_id == right_player_id:
        raise CliUsageError(
            "--left-opponent-player-id and --right-opponent-player-id must be different."
        )


def validate_live_opponent_profile_options(
    position_data: dict[str, Any],
    opponent_statistics_file: str | None,
    left_opponent_player_id: str | None,
    right_opponent_player_id: str | None,
    use_profile_presets_override: bool,
) -> None:
    """Validates external-profile options for one live position invocation."""
    if opponent_statistics_file is None:
        if left_opponent_player_id is not None or right_opponent_player_id is not None:
            raise CliUsageError("Opponent player IDs require --opponent-statistics-file.")
        return
    if left_opponent_player_id is None and right_opponent_player_id is None:
        raise CliUsageError("--opponent-statistics-file requires at least one opponent player ID.")
    if position_data.get("analysis_mode", "live_decision") != "live_decision":
        raise CliUsageError(
            "--opponent-statistics-file is supported only for analysis_mode='live_decision'."
        )
    unsupported_fields = {
        "list_performance_input",
        "list_game_contributions",
        "list_analysis_results",
        "list_standings_input",
        "impossible_null_settlement",
    }.intersection(position_data)
    if unsupported_fields:
        raise CliUsageError(
            "--opponent-statistics-file is not supported for this non-live analysis "
            f"workflow: {', '.join(sorted(unsupported_fields))}."
        )
    if not (position_data.get("use_profile_presets") is True or use_profile_presets_override):
        raise CliUsageError(
            "--opponent-statistics-file requires effective --use-profile-presets opt-in."
        )


def validate_historical_game_cli_arguments(args: argparse.Namespace) -> None:
    """Rejects position-analysis and simulation overrides for historical games."""
    historical_profile_review = (
        args.historical_game_review and args.opponent_statistics_file is not None
    )
    if args.opponent_statistics_file is not None and not args.historical_game_review:
        raise CliUsageError(
            "--opponent-statistics-file requires --historical-game-review for "
            "historical-game input."
        )
    if historical_profile_review and (
        args.left_opponent_player_id is not None or args.right_opponent_player_id is not None
    ):
        raise CliUsageError(
            "--left-opponent-player-id and --right-opponent-player-id are live-only "
            "and are not accepted for historical review."
        )
    if historical_profile_review and not args.use_profile_presets:
        raise CliUsageError(
            "--opponent-statistics-file requires effective --use-profile-presets opt-in."
        )
    incompatible_options = {
        "--samples": args.samples is not None
        and not (
            args.historical_game_review
            or args.historical_search_review
            or args.historical_replay_coaching
        ),
        "--seed": args.seed is not None
        and not (
            args.historical_game_review
            or args.historical_search_review
            or args.historical_replay_coaching
        ),
        "--opponent-strategy": args.opponent_strategy is not None,
        "--multi-step": args.multi_step is not None,
        "--card-policy": args.card_policy is not None,
        "--expected-value-samples": args.expected_value_samples is not None,
        "--strict-context": args.strict_context,
        "--compare-policies": args.compare_policies,
        "--comparison-only": args.comparison_only,
        "--opponent-policy-preset": (
            args.opponent_policy_preset is not None and not historical_profile_review
        ),
        "--opponent-lead-policy": (
            args.opponent_lead_policy is not None and not historical_profile_review
        ),
        "--opponent-response-policy": (
            args.opponent_response_policy is not None and not historical_profile_review
        ),
        "--use-profile-presets": args.use_profile_presets and not historical_profile_review,
        "--left-opponent-lead-policy": (
            args.left_opponent_lead_policy is not None and not historical_profile_review
        ),
        "--left-opponent-response-policy": (
            args.left_opponent_response_policy is not None and not historical_profile_review
        ),
        "--right-opponent-lead-policy": (
            args.right_opponent_lead_policy is not None and not historical_profile_review
        ),
        "--right-opponent-response-policy": (
            args.right_opponent_response_policy is not None and not historical_profile_review
        ),
        "--opponent-statistics-file": False,
        "--left-opponent-player-id": args.left_opponent_player_id is not None,
        "--right-opponent-player-id": args.right_opponent_player_id is not None,
        "--aggregate-opponent-statistics": getattr(args, "aggregate_opponent_statistics", False),
        "--evaluate-bounded-search": getattr(args, "evaluate_bounded_search", False),
        "--search-evaluation-partition": getattr(
            args, "search_evaluation_partition", None
        )
        is not None,
        "--search-evaluation-max-decisions": getattr(
            args, "search_evaluation_max_decisions", None
        )
        is not None,
    }
    supplied_options = [
        option for option, was_supplied in incompatible_options.items() if was_supplied
    ]
    if supplied_options:
        raise CliUsageError(
            "Historical-game inputs do not accept position-analysis, recommendation, "
            "policy, comparison, or simulation options: "
            f"{', '.join(supplied_options)}."
        )


def validate_training_dataset_cli_arguments(args: argparse.Namespace) -> None:
    """Rejects all analysis, review, simulation, policy, and profile options."""
    incompatible_options = {
        "--samples": args.samples is not None,
        "--seed": args.seed is not None,
        "--opponent-strategy": args.opponent_strategy is not None,
        "--historical-decision-snapshots": args.historical_decision_snapshots,
        "--historical-game-review": args.historical_game_review,
        "--historical-search-review": args.historical_search_review,
        "--historical-replay-coaching": args.historical_replay_coaching,
        "--multi-step": args.multi_step is not None,
        "--card-policy": args.card_policy is not None,
        "--expected-value-samples": args.expected_value_samples is not None,
        "--strict-context": args.strict_context,
        "--compare-policies": args.compare_policies,
        "--comparison-only": args.comparison_only,
        "--opponent-policy-preset": args.opponent_policy_preset is not None,
        "--opponent-lead-policy": args.opponent_lead_policy is not None,
        "--opponent-response-policy": args.opponent_response_policy is not None,
        "--use-profile-presets": args.use_profile_presets,
        "--left-opponent-lead-policy": args.left_opponent_lead_policy is not None,
        "--left-opponent-response-policy": args.left_opponent_response_policy is not None,
        "--right-opponent-lead-policy": args.right_opponent_lead_policy is not None,
        "--right-opponent-response-policy": args.right_opponent_response_policy is not None,
        "--opponent-statistics-file": args.opponent_statistics_file is not None,
        "--left-opponent-player-id": args.left_opponent_player_id is not None,
        "--right-opponent-player-id": args.right_opponent_player_id is not None,
    }
    evaluation_mode = getattr(args, "evaluate_opponent_policy_profiles", False)
    search_evaluation_mode = getattr(args, "evaluate_bounded_search", False)
    audit_mode = getattr(args, "audit_dataset_partitions", False)
    if audit_mode:
        incompatible_options.update(
            {
                "--aggregate-opponent-statistics": getattr(
                    args, "aggregate_opponent_statistics", False
                ),
                "--opponent-statistics-partition": getattr(
                    args, "opponent_statistics_partition", None
                )
                is not None,
                "--opponent-statistics-before": getattr(args, "opponent_statistics_before", None)
                is not None,
                "--export-opponent-statistics": getattr(args, "export_opponent_statistics", None)
                is not None,
                "--evaluate-opponent-policy-profiles": evaluation_mode,
                "--evaluate-bounded-search": search_evaluation_mode,
            }
        )
    if evaluation_mode:
        incompatible_options.update(
            {
                "--aggregate-opponent-statistics": getattr(
                    args, "aggregate_opponent_statistics", False
                ),
                "--opponent-statistics-partition": getattr(
                    args, "opponent_statistics_partition", None
                )
                is not None,
                "--opponent-statistics-before": getattr(args, "opponent_statistics_before", None)
                is not None,
                "--export-opponent-statistics": getattr(args, "export_opponent_statistics", None)
                is not None,
            }
        )
    if search_evaluation_mode:
        incompatible_options.update(
            {
                "--audit-dataset-partitions": audit_mode,
                "--aggregate-opponent-statistics": getattr(
                    args, "aggregate_opponent_statistics", False
                ),
                "--evaluate-opponent-policy-profiles": evaluation_mode,
                "--opponent-statistics-partition": getattr(
                    args, "opponent_statistics_partition", None
                )
                is not None,
                "--opponent-statistics-before": getattr(
                    args, "opponent_statistics_before", None
                )
                is not None,
                "--export-opponent-statistics": getattr(
                    args, "export_opponent_statistics", None
                )
                is not None,
            }
        )
    supplied_options = [
        option for option, was_supplied in incompatible_options.items() if was_supplied
    ]
    if supplied_options:
        raise CliUsageError(
            "Training-dataset inputs do not accept position-analysis, historical-review, "
            "recommendation, policy, profile, comparison, or simulation options: "
            f"{', '.join(supplied_options)}."
        )


def validate_training_dataset_preparation_cli_arguments(
    args: argparse.Namespace,
) -> None:
    """Allows only transport and public-provenance options for preparation."""
    incompatible_options = {
        "--samples": args.samples is not None,
        "--seed": args.seed is not None,
        "--opponent-strategy": args.opponent_strategy is not None,
        "--audit-dataset-partitions": args.audit_dataset_partitions,
        "--dataset-partition-mode": args.dataset_partition_mode is not None,
        "--aggregate-opponent-statistics": args.aggregate_opponent_statistics,
        "--opponent-statistics-partition": args.opponent_statistics_partition is not None,
        "--opponent-statistics-before": args.opponent_statistics_before is not None,
        "--export-opponent-statistics": args.export_opponent_statistics is not None,
        "--evaluate-opponent-policy-profiles": args.evaluate_opponent_policy_profiles,
        "--profile-source-partition": args.profile_source_partition is not None,
        "--profile-evaluation-partition": args.profile_evaluation_partition is not None,
        "--historical-decision-snapshots": args.historical_decision_snapshots,
        "--historical-game-review": args.historical_game_review,
        "--historical-search-review": args.historical_search_review,
        "--historical-replay-coaching": args.historical_replay_coaching,
        "--search-seed": args.search_seed is not None,
        "--search-budget-profile": args.search_budget_profile is not None,
        "--evaluate-bounded-search": args.evaluate_bounded_search,
        "--search-evaluation-partition": args.search_evaluation_partition is not None,
        "--search-evaluation-max-decisions": args.search_evaluation_max_decisions is not None,
        "--multi-step": args.multi_step is not None,
        "--card-policy": args.card_policy is not None,
        "--expected-value-samples": args.expected_value_samples is not None,
        "--strict-context": args.strict_context,
        "--compare-policies": args.compare_policies,
        "--comparison-only": args.comparison_only,
        "--opponent-policy-preset": args.opponent_policy_preset is not None,
        "--opponent-lead-policy": args.opponent_lead_policy is not None,
        "--opponent-response-policy": args.opponent_response_policy is not None,
        "--use-profile-presets": args.use_profile_presets,
        "--opponent-statistics-file": args.opponent_statistics_file is not None,
        "--left-opponent-player-id": args.left_opponent_player_id is not None,
        "--right-opponent-player-id": args.right_opponent_player_id is not None,
        "--left-opponent-lead-policy": args.left_opponent_lead_policy is not None,
        "--left-opponent-response-policy": args.left_opponent_response_policy is not None,
        "--right-opponent-lead-policy": args.right_opponent_lead_policy is not None,
        "--right-opponent-response-policy": args.right_opponent_response_policy is not None,
    }
    supplied_options = [
        option for option, was_supplied in incompatible_options.items() if was_supplied
    ]
    if supplied_options:
        raise CliUsageError(
            "Training-dataset-preparation inputs accept only --input, --output, "
            "--quiet, and --include-provenance; unsupported options: "
            f"{', '.join(supplied_options)}."
        )


def validate_opponent_statistics_cli_arguments(args: argparse.Namespace) -> None:
    """Allows only transport and public-provenance options for statistics."""
    incompatible_options = {
        "--samples": args.samples is not None,
        "--seed": args.seed is not None,
        "--opponent-strategy": args.opponent_strategy is not None,
        "--historical-decision-snapshots": args.historical_decision_snapshots,
        "--historical-game-review": args.historical_game_review,
        "--historical-search-review": getattr(args, "historical_search_review", False),
        "--historical-replay-coaching": getattr(
            args, "historical_replay_coaching", False
        ),
        "--search-seed": getattr(args, "search_seed", None) is not None,
        "--search-budget-profile": getattr(args, "search_budget_profile", None)
        is not None,
        "--evaluate-bounded-search": getattr(args, "evaluate_bounded_search", False),
        "--search-evaluation-partition": getattr(
            args, "search_evaluation_partition", None
        )
        is not None,
        "--search-evaluation-max-decisions": getattr(
            args, "search_evaluation_max_decisions", None
        )
        is not None,
        "--multi-step": args.multi_step is not None,
        "--card-policy": args.card_policy is not None,
        "--expected-value-samples": args.expected_value_samples is not None,
        "--strict-context": args.strict_context,
        "--compare-policies": args.compare_policies,
        "--comparison-only": args.comparison_only,
        "--opponent-policy-preset": args.opponent_policy_preset is not None,
        "--opponent-lead-policy": args.opponent_lead_policy is not None,
        "--opponent-response-policy": args.opponent_response_policy is not None,
        "--use-profile-presets": args.use_profile_presets,
        "--left-opponent-lead-policy": args.left_opponent_lead_policy is not None,
        "--left-opponent-response-policy": args.left_opponent_response_policy is not None,
        "--right-opponent-lead-policy": args.right_opponent_lead_policy is not None,
        "--right-opponent-response-policy": args.right_opponent_response_policy is not None,
        "--opponent-statistics-file": args.opponent_statistics_file is not None,
        "--left-opponent-player-id": args.left_opponent_player_id is not None,
        "--right-opponent-player-id": args.right_opponent_player_id is not None,
        "--aggregate-opponent-statistics": getattr(args, "aggregate_opponent_statistics", False),
    }
    supplied_options = [
        option for option, was_supplied in incompatible_options.items() if was_supplied
    ]
    if supplied_options:
        raise CliUsageError(
            "Opponent-statistics inputs do not accept analysis, historical, training-"
            "dataset, list, recommendation, policy, profile, review, sample, seed, or "
            f"simulation options: {', '.join(supplied_options)}."
        )


def validate_fixed_three_player_historical_list_cli_arguments(
    args: argparse.Namespace,
) -> None:
    """Allows only transport and public-provenance options for list workflows."""
    incompatible_options = {
        "--samples": args.samples is not None,
        "--seed": args.seed is not None,
        "--opponent-strategy": args.opponent_strategy is not None,
        "--audit-dataset-partitions": args.audit_dataset_partitions,
        "--dataset-partition-mode": args.dataset_partition_mode is not None,
        "--aggregate-opponent-statistics": args.aggregate_opponent_statistics,
        "--opponent-statistics-partition": args.opponent_statistics_partition is not None,
        "--opponent-statistics-before": args.opponent_statistics_before is not None,
        "--export-opponent-statistics": args.export_opponent_statistics is not None,
        "--evaluate-opponent-policy-profiles": args.evaluate_opponent_policy_profiles,
        "--profile-source-partition": args.profile_source_partition is not None,
        "--profile-evaluation-partition": args.profile_evaluation_partition is not None,
        "--historical-decision-snapshots": args.historical_decision_snapshots,
        "--historical-game-review": args.historical_game_review,
        "--historical-search-review": args.historical_search_review,
        "--historical-replay-coaching": args.historical_replay_coaching,
        "--search-seed": args.search_seed is not None,
        "--search-budget-profile": args.search_budget_profile is not None,
        "--evaluate-bounded-search": args.evaluate_bounded_search,
        "--search-evaluation-partition": args.search_evaluation_partition is not None,
        "--search-evaluation-max-decisions": args.search_evaluation_max_decisions is not None,
        "--multi-step": args.multi_step is not None,
        "--card-policy": args.card_policy is not None,
        "--expected-value-samples": args.expected_value_samples is not None,
        "--strict-context": args.strict_context,
        "--compare-policies": args.compare_policies,
        "--comparison-only": args.comparison_only,
        "--opponent-policy-preset": args.opponent_policy_preset is not None,
        "--opponent-lead-policy": args.opponent_lead_policy is not None,
        "--opponent-response-policy": args.opponent_response_policy is not None,
        "--use-profile-presets": args.use_profile_presets,
        "--opponent-statistics-file": args.opponent_statistics_file is not None,
        "--left-opponent-player-id": args.left_opponent_player_id is not None,
        "--right-opponent-player-id": args.right_opponent_player_id is not None,
        "--left-opponent-lead-policy": args.left_opponent_lead_policy is not None,
        "--left-opponent-response-policy": args.left_opponent_response_policy is not None,
        "--right-opponent-lead-policy": args.right_opponent_lead_policy is not None,
        "--right-opponent-response-policy": args.right_opponent_response_policy is not None,
    }
    supplied_options = [
        option for option, was_supplied in incompatible_options.items() if was_supplied
    ]
    if supplied_options:
        raise CliUsageError(
            "Fixed-three-player historical-list inputs accept only --input, --output, "
            "--quiet, and --include-provenance; unsupported options: "
            f"{', '.join(supplied_options)}."
        )


def _run_cli(
    argv: list[str] | tuple[str, ...] | None,
    invocation_style: str,
) -> int:
    if _active_legacy_patch_namespace is not None and argv is None:
        args = _legacy_patch_value("parse_arguments")()
    else:
        args = parse_arguments(argv, invocation_style=invocation_style)

    try:
        input_data = _legacy_patch_value("load_json_object")(args.input)
        workflow = _legacy_patch_value("get_input_workflow")(input_data)
        if workflow == "training_dataset_preparation":
            _legacy_patch_value("validate_training_dataset_preparation_cli_arguments")(
                args
            )
        else:
            _legacy_patch_value("validate_cli_arguments")(args, workflow=workflow)
        if workflow == "fixed_three_player_historical_list_comparison":
            _legacy_patch_value(
                "validate_fixed_three_player_historical_list_cli_arguments"
            )(args)
            _legacy_patch_value(
                "run_json_fixed_three_player_historical_list_comparison"
            )(
                file_path=args.input,
                output_path=args.output,
                quiet=args.quiet,
                include_provenance=args.include_provenance,
            )
        elif workflow == "fixed_three_player_historical_list":
            _legacy_patch_value(
                "validate_fixed_three_player_historical_list_cli_arguments"
            )(args)
            _legacy_patch_value("run_json_fixed_three_player_historical_list_analysis")(
                file_path=args.input,
                output_path=args.output,
                quiet=args.quiet,
                include_provenance=args.include_provenance,
            )
        elif workflow == "opponent_statistics":
            _legacy_patch_value("validate_opponent_statistics_cli_arguments")(args)
            _legacy_patch_value("run_json_opponent_statistics_conversion")(
                file_path=args.input,
                output_path=args.output,
                quiet=args.quiet,
                include_provenance=args.include_provenance,
            )
        elif workflow == "training_dataset_preparation":
            _legacy_patch_value("run_json_training_dataset_preparation")(
                file_path=args.input,
                output_path=args.output,
                quiet=args.quiet,
                include_provenance=args.include_provenance,
            )
        elif workflow == "training_dataset":
            _legacy_patch_value("validate_training_dataset_cli_arguments")(args)
            if args.evaluate_bounded_search:
                _legacy_patch_value("run_json_bounded_search_evaluation")(
                    file_path=args.input,
                    search_seed=args.search_seed,
                    partitions=tuple(
                        args.search_evaluation_partition
                        or DEFAULT_BOUNDED_SEARCH_EVALUATION_PARTITIONS
                    ),
                    search_budget_profile=(
                        args.search_budget_profile
                        or EVALUATION_SEARCH_BUDGET_PROFILE
                    ),
                    max_decisions=args.search_evaluation_max_decisions,
                    output_path=args.output,
                    quiet=args.quiet,
                    include_provenance=args.include_provenance,
                )
            elif args.audit_dataset_partitions:
                _legacy_patch_value("run_json_dataset_partition_audit")(
                    file_path=args.input,
                    requested_mode=args.dataset_partition_mode,
                    output_path=args.output,
                    quiet=args.quiet,
                    include_provenance=args.include_provenance,
                )
            elif args.evaluate_opponent_policy_profiles:
                _legacy_patch_value("run_json_rolling_opponent_policy_evaluation")(
                    file_path=args.input,
                    source_partitions=tuple(
                        args.profile_source_partition or DEFAULT_SOURCE_PARTITIONS
                    ),
                    evaluation_partitions=tuple(
                        args.profile_evaluation_partition or DEFAULT_EVALUATION_PARTITIONS
                    ),
                    output_path=args.output,
                    quiet=args.quiet,
                    include_provenance=args.include_provenance,
                )
            elif args.aggregate_opponent_statistics:
                _legacy_patch_value(
                    "run_json_historical_opponent_statistics_aggregation"
                )(
                    file_path=args.input,
                    included_partitions=(
                        tuple(args.opponent_statistics_partition)
                        if args.opponent_statistics_partition is not None
                        else None
                    ),
                    before=args.opponent_statistics_before,
                    output_path=args.output,
                    export_path=args.export_opponent_statistics,
                    quiet=args.quiet,
                    include_provenance=args.include_provenance,
                )
            else:
                _legacy_patch_value("run_json_training_dataset_conversion")(
                    file_path=args.input,
                    output_path=args.output,
                    quiet=args.quiet,
                    include_provenance=args.include_provenance,
                )
        elif workflow == "historical_game":
            _legacy_patch_value("validate_historical_game_cli_arguments")(args)
            _legacy_patch_value("run_json_historical_game_analysis")(
                file_path=args.input,
                output_path=args.output,
                quiet=args.quiet,
                include_provenance=args.include_provenance,
                historical_decision_snapshots=args.historical_decision_snapshots,
                historical_game_review=args.historical_game_review,
                historical_search_review=args.historical_search_review,
                historical_replay_coaching=args.historical_replay_coaching,
                search_seed=args.search_seed,
                search_budget_profile=(
                    args.search_budget_profile
                    or HISTORICAL_REVIEW_SEARCH_BUDGET_PROFILE
                ),
                sample_count=args.samples,
                base_random_seed=args.seed,
                opponent_statistics_file=args.opponent_statistics_file,
                opponent_policy_preset_override=args.opponent_policy_preset,
                opponent_lead_policy_override=args.opponent_lead_policy,
                opponent_response_policy_override=args.opponent_response_policy,
                left_opponent_lead_policy_override=args.left_opponent_lead_policy,
                left_opponent_response_policy_override=(args.left_opponent_response_policy),
                right_opponent_lead_policy_override=args.right_opponent_lead_policy,
                right_opponent_response_policy_override=(args.right_opponent_response_policy),
            )
        else:
            if args.historical_decision_snapshots:
                raise CliUsageError(
                    "--historical-decision-snapshots requires historical-game input."
                )
            if args.historical_game_review:
                raise CliUsageError("--historical-game-review requires historical-game input.")
            if args.historical_search_review:
                raise CliUsageError(
                    "--historical-search-review requires historical-game input."
                )
            if args.historical_replay_coaching:
                raise CliUsageError(
                    "--historical-replay-coaching requires historical-game input."
                )
            _legacy_patch_value("run_json_position_analysis")(
                file_path=args.input,
                sample_count_override=args.samples,
                random_seed_override=args.seed,
                opponent_strategy_override=args.opponent_strategy,
                left_opponent_lead_policy_override=args.left_opponent_lead_policy,
                left_opponent_response_policy_override=args.left_opponent_response_policy,
                right_opponent_lead_policy_override=args.right_opponent_lead_policy,
                right_opponent_response_policy_override=args.right_opponent_response_policy,
                output_path=args.output,
                multi_step_count=args.multi_step,
                card_selection_policy=args.card_policy,
                expected_value_sample_count=(
                    args.expected_value_samples or DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT
                ),
                strict_context=args.strict_context,
                compare_policies=args.compare_policies,
                comparison_only=args.comparison_only,
                opponent_policy_preset_override=args.opponent_policy_preset,
                opponent_lead_policy_override=args.opponent_lead_policy,
                opponent_response_policy_override=args.opponent_response_policy,
                use_profile_presets_override=args.use_profile_presets,
                opponent_statistics_file=args.opponent_statistics_file,
                left_opponent_player_id=args.left_opponent_player_id,
                right_opponent_player_id=args.right_opponent_player_id,
                quiet=args.quiet,
                include_provenance=args.include_provenance,
            )
    except CliUsageError as error:
        print(f"CLI error: {error}", file=sys.stderr)
        return CLI_EXIT_CODE_USAGE
    except (ValueError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return CLI_EXIT_CODE_FAILURE

    return CLI_EXIT_CODE_SUCCESS


def run_cli(
    argv: list[str] | tuple[str, ...] | None = None,
    *,
    invocation_style: str = "installed",
    legacy_namespace: ModuleType | None = None,
) -> int:
    """Runs one argv-capable CLI invocation using the selected command identity."""
    _invocation_command(invocation_style)
    dispatch_argv = tuple(sys.argv[1:] if argv is None else argv)
    if dispatch_argv[:1] == ("session",):
        from skat_ai.cli.session import run_session_cli

        session_argv = dispatch_argv[1:]
        if legacy_namespace is None:
            return run_session_cli(session_argv, invocation_style=invocation_style)
        with legacy_patch_namespace(legacy_namespace):
            return run_session_cli(session_argv, invocation_style=invocation_style)
    if legacy_namespace is None:
        return _run_cli(argv, invocation_style)
    with legacy_patch_namespace(legacy_namespace):
        return _run_cli(argv, invocation_style)


def main() -> int:
    """Runs the installed ``skat-ai`` Console Script."""
    return run_cli(invocation_style="installed")
