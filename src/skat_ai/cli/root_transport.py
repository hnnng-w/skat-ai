"""Root CLI JSON loading, Application execution, output, and presentation transport."""

from typing import Any

from skat_ai.application.contracts import (
    ApplicationExecutionOptions,
    ApplicationExternalDocuments,
    HistoricalGameApplicationOptions,
    PositionAnalysisApplicationOptions,
    TrainingDatasetApplicationOptions,
)
from skat_ai.bounded_search_evaluation import (
    DEFAULT_BOUNDED_SEARCH_EVALUATION_PARTITIONS,
)
from skat_ai.cli.presentation.dataset import (
    print_bounded_search_evaluation_result,
    print_dataset_partition_audit_result,
    print_information_set_search_evaluation_result,
    print_rolling_opponent_policy_evaluation_result,
    print_training_dataset_preparation_application_result,
    print_training_dataset_result,
)
from skat_ai.cli.presentation.historical import (
    print_historical_game_result,
    print_historical_information_set_replay_coaching_result,
    print_historical_information_set_search_review_result,
    print_historical_replay_coaching_result,
    print_historical_search_review_result,
)
from skat_ai.cli.presentation.historical_lists import (
    print_fixed_three_player_historical_list_comparison_result,
    print_fixed_three_player_historical_list_result,
)
from skat_ai.cli.presentation.opponent_statistics import (
    print_historical_opponent_statistics_result,
    print_opponent_statistics_result,
)
from skat_ai.cli.presentation.position import print_analysis_result
from skat_ai.cli.presentation.provenance import print_field_provenance_summary
from skat_ai.cli.presentation.simulation import (
    print_multi_step_result,
    print_policy_comparison_result,
)
from skat_ai.cli.root_application import (
    execute_legacy_application,
    load_external_opponent_statistics_document,
)
from skat_ai.cli.root_compatibility import CliUsageError, _facade_value
from skat_ai.cli.root_validation import validate_live_opponent_profile_options
from skat_ai.errors import SkatAIWorkflowError
from skat_ai.information_set_search_evaluation import (
    DEFAULT_INFORMATION_SET_SEARCH_EVALUATION_PARTITIONS,
    DEFAULT_INFORMATION_SET_SEARCH_EVALUATION_PROFILE,
)
from skat_ai.input_loader import load_json_object, load_position_from_json
from skat_ai.output_writer import write_analysis_result_to_json
from skat_ai.rolling_opponent_policy_evaluation import (
    DEFAULT_EVALUATION_PARTITIONS,
    DEFAULT_SOURCE_PARTITIONS,
)
from skat_ai.search_budget_profiles import (
    EVALUATION_SEARCH_BUDGET_PROFILE,
    HISTORICAL_REVIEW_SEARCH_BUDGET_PROFILE,
)
from skat_ai.simulation import DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT


def _dependency(name: str, default: Any) -> Any:
    return _facade_value(name, default)


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

    position_data = _dependency("load_position_from_json", load_position_from_json)(file_path)
    if "game_shortening" in position_data and (multi_step_count is not None or compare_policies):
        raise ValueError(
            "Structured game_shortening cannot be combined with multi-step simulation "
            "or policy comparison."
        )
    shortening_value = position_data.get("game_shortening")
    is_open_card_throw = (
        isinstance(shortening_value, dict) and shortening_value.get("kind") == "open_card_throw"
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
    _dependency(
        "validate_live_opponent_profile_options",
        validate_live_opponent_profile_options,
    )(
        position_data=position_data,
        opponent_statistics_file=opponent_statistics_file,
        left_opponent_player_id=left_opponent_player_id,
        right_opponent_player_id=right_opponent_player_id,
        use_profile_presets_override=use_profile_presets_override,
    )
    external_documents = None
    if opponent_statistics_file is not None:
        external_documents = ApplicationExternalDocuments(
            opponent_statistics_document=_dependency(
                "load_external_opponent_statistics_document",
                load_external_opponent_statistics_document,
            )(opponent_statistics_file),
            opponent_statistics_reference=opponent_statistics_file,
        )
    result, _artifacts = _dependency("execute_legacy_application", execute_legacy_application)(
        position_data,
        input_reference=file_path,
        options=ApplicationExecutionOptions(
            position_analysis=PositionAnalysisApplicationOptions(
                sample_count_override=sample_count_override,
                random_seed_override=random_seed_override,
                opponent_strategy_override=opponent_strategy_override,
                left_opponent_lead_policy_override=(left_opponent_lead_policy_override),
                left_opponent_response_policy_override=(left_opponent_response_policy_override),
                right_opponent_lead_policy_override=(right_opponent_lead_policy_override),
                right_opponent_response_policy_override=(right_opponent_response_policy_override),
                multi_step_count=multi_step_count,
                card_selection_policy=card_selection_policy,
                expected_value_sample_count=expected_value_sample_count,
                strict_context=strict_context,
                compare_policies=compare_policies,
                comparison_only=comparison_only,
                opponent_policy_preset_override=(opponent_policy_preset_override),
                opponent_lead_policy_override=opponent_lead_policy_override,
                opponent_response_policy_override=(opponent_response_policy_override),
                use_profile_presets_override=use_profile_presets_override,
                left_opponent_player_id=left_opponent_player_id,
                right_opponent_player_id=right_opponent_player_id,
            )
        ),
        external_documents=external_documents,
        include_provenance=include_provenance,
    )
    if output_path is not None:
        _dependency("write_analysis_result_to_json", write_analysis_result_to_json)(
            output_path=output_path, result=result
        )
    if quiet:
        return
    if not comparison_only:
        _dependency("print_analysis_result", print_analysis_result)(result)
    if multi_step_count is not None and not comparison_only:
        _dependency("print_multi_step_result", print_multi_step_result)(result["multi_step_result"])
    if compare_policies:
        _dependency("print_policy_comparison_result", print_policy_comparison_result)(
            result["policy_comparison_result"]
        )
    if output_path is not None:
        print()
        print("Output file written:", output_path)
    _dependency("print_field_provenance_summary", print_field_provenance_summary)(result)
    return


def run_json_historical_game_analysis(
    file_path: str,
    output_path: str | None = None,
    quiet: bool = False,
    historical_decision_snapshots: bool = False,
    historical_game_review: bool = False,
    historical_search_review: bool = False,
    historical_information_set_search_review: bool = False,
    historical_information_set_replay_coaching: bool = False,
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
    root_document = _dependency("load_json_object", load_json_object)(file_path)
    external_documents = None
    if opponent_statistics_file is not None:
        external_documents = ApplicationExternalDocuments(
            opponent_statistics_document=_dependency(
                "load_external_opponent_statistics_document",
                load_external_opponent_statistics_document,
            )(opponent_statistics_file),
            opponent_statistics_reference=opponent_statistics_file,
        )
    result, _artifacts = _dependency("execute_legacy_application", execute_legacy_application)(
        root_document,
        input_reference=file_path,
        options=ApplicationExecutionOptions(
            historical_game=HistoricalGameApplicationOptions(
                decision_snapshots=historical_decision_snapshots,
                immediate_review=historical_game_review,
                search_review=historical_search_review,
                information_set_search_review=(historical_information_set_search_review),
                information_set_replay_coaching=(
                    historical_information_set_replay_coaching
                ),
                replay_coaching=historical_replay_coaching,
                search_seed=search_seed,
                search_budget_profile=search_budget_profile,
                immediate_sample_count=sample_count,
                immediate_base_random_seed=base_random_seed,
                opponent_policy_preset_override=(opponent_policy_preset_override),
                opponent_lead_policy_override=opponent_lead_policy_override,
                opponent_response_policy_override=(opponent_response_policy_override),
                left_opponent_lead_policy_override=(left_opponent_lead_policy_override),
                left_opponent_response_policy_override=(left_opponent_response_policy_override),
                right_opponent_lead_policy_override=(right_opponent_lead_policy_override),
                right_opponent_response_policy_override=(right_opponent_response_policy_override),
                use_profile_presets_override=(opponent_statistics_file is not None),
            )
        ),
        external_documents=external_documents,
        include_provenance=include_provenance,
    )
    if output_path is not None:
        _dependency("write_analysis_result_to_json", write_analysis_result_to_json)(
            output_path=output_path, result=result
        )
    if quiet:
        return
    _dependency("print_historical_game_result", print_historical_game_result)(result)
    historical_game_summary = result["historical_game_summary"]
    if historical_search_review:
        _dependency(
            "print_historical_search_review_result",
            print_historical_search_review_result,
        )(historical_game_summary["historical_search_review_summary"])
    if historical_information_set_search_review:
        _dependency(
            "print_historical_information_set_search_review_result",
            print_historical_information_set_search_review_result,
        )(historical_game_summary["historical_information_set_search_review_summary"])
    if historical_information_set_replay_coaching:
        _dependency(
            "print_historical_information_set_replay_coaching_result",
            print_historical_information_set_replay_coaching_result,
        )(
            historical_game_summary[
                "historical_information_set_replay_coaching_summary"
            ]
        )
    if historical_replay_coaching:
        _dependency(
            "print_historical_replay_coaching_result",
            print_historical_replay_coaching_result,
        )(historical_game_summary["historical_replay_coaching_summary"])
    if output_path is not None:
        print()
        print("Output file written:", output_path)
    _dependency("print_field_provenance_summary", print_field_provenance_summary)(result)
    return


def run_json_training_dataset_conversion(
    file_path: str,
    output_path: str | None = None,
    quiet: bool = False,
    include_provenance: bool = False,
) -> None:
    """Runs deterministic training-dataset validation and sample generation."""
    root_document = _dependency("load_json_object", load_json_object)(file_path)
    result, _artifacts = _dependency("execute_legacy_application", execute_legacy_application)(
        root_document,
        input_reference=file_path,
        options=ApplicationExecutionOptions(
            training_dataset=TrainingDatasetApplicationOptions(operation="summary")
        ),
        include_provenance=include_provenance,
    )
    if output_path is not None:
        _dependency("write_analysis_result_to_json", write_analysis_result_to_json)(
            output_path=output_path, result=result
        )
    if quiet:
        return
    _dependency("print_training_dataset_result", print_training_dataset_result)(result)
    if output_path is not None:
        print()
        print("Output file written:", output_path)
    _dependency("print_field_provenance_summary", print_field_provenance_summary)(result)
    return


def run_json_training_dataset_preparation(
    file_path: str,
    output_path: str | None = None,
    quiet: bool = False,
    include_provenance: bool = False,
) -> None:
    """Runs one mode-derived automatic Dataset preparation workflow."""
    root_document = _dependency("load_json_object", load_json_object)(file_path)
    result, _artifacts = _dependency("execute_legacy_application", execute_legacy_application)(
        root_document,
        input_reference=file_path,
        include_provenance=include_provenance,
    )
    if output_path is not None:
        _dependency("write_analysis_result_to_json", write_analysis_result_to_json)(
            output_path=output_path, result=result
        )
    if quiet:
        return
    _dependency(
        "print_training_dataset_preparation_application_result",
        print_training_dataset_preparation_application_result,
    )(root_document, result)
    if output_path is not None:
        print()
        print("Output file written:", output_path)
    _dependency("print_field_provenance_summary", print_field_provenance_summary)(result)
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
    root_document = _dependency("load_json_object", load_json_object)(file_path)
    result, _artifacts = _dependency("execute_legacy_application", execute_legacy_application)(
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
        _dependency("write_analysis_result_to_json", write_analysis_result_to_json)(
            output_path=output_path, result=result
        )
    if quiet:
        return
    _dependency(
        "print_bounded_search_evaluation_result",
        print_bounded_search_evaluation_result,
    )(result)
    if output_path is not None:
        print()
        print("Output file written:", output_path)
    _dependency("print_field_provenance_summary", print_field_provenance_summary)(result)
    return


def run_json_information_set_search_evaluation(
    file_path: str,
    *,
    search_seed: int,
    partitions: tuple[str, ...] = (DEFAULT_INFORMATION_SET_SEARCH_EVALUATION_PARTITIONS),
    search_budget_profile: str = (DEFAULT_INFORMATION_SET_SEARCH_EVALUATION_PROFILE),
    max_decisions: int | None = None,
    output_path: str | None = None,
    quiet: bool = False,
    include_provenance: bool = False,
) -> None:
    """Runs Information-set Search evaluation on selected dataset records."""
    root_document = _dependency("load_json_object", load_json_object)(file_path)
    result, _artifacts = _dependency("execute_legacy_application", execute_legacy_application)(
        root_document,
        input_reference=file_path,
        options=ApplicationExecutionOptions(
            training_dataset=TrainingDatasetApplicationOptions(
                operation="information_set_search_evaluation",
                information_set_search_seed=search_seed,
                information_set_search_partitions=partitions,
                information_set_search_budget_profile=search_budget_profile,
                information_set_search_max_decisions=max_decisions,
            )
        ),
        include_provenance=include_provenance,
    )
    if output_path is not None:
        _dependency("write_analysis_result_to_json", write_analysis_result_to_json)(
            output_path=output_path, result=result
        )
    if quiet:
        return
    _dependency(
        "print_information_set_search_evaluation_result",
        print_information_set_search_evaluation_result,
    )(result)
    if output_path is not None:
        print()
        print("Output file written:", output_path)
    _dependency("print_field_provenance_summary", print_field_provenance_summary)(result)
    return


def run_json_dataset_partition_audit(
    file_path: str,
    requested_mode: str | None = None,
    output_path: str | None = None,
    quiet: bool = False,
    include_provenance: bool = False,
) -> None:
    """Audits training-dataset player overlap without generating samples."""
    root_document = _dependency("load_json_object", load_json_object)(file_path)
    try:
        result, _artifacts = _dependency("execute_legacy_application", execute_legacy_application)(
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
        _dependency("write_analysis_result_to_json", write_analysis_result_to_json)(
            output_path=output_path, result=result
        )
    if quiet:
        return
    _dependency("print_dataset_partition_audit_result", print_dataset_partition_audit_result)(
        result
    )
    if output_path is not None:
        print()
        print("Output file written:", output_path)
    _dependency("print_field_provenance_summary", print_field_provenance_summary)(result)
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
    root_document = _dependency("load_json_object", load_json_object)(file_path)
    result, _artifacts = _dependency("execute_legacy_application", execute_legacy_application)(
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
        _dependency("write_analysis_result_to_json", write_analysis_result_to_json)(
            output_path=output_path, result=result
        )
    if quiet:
        return
    _dependency(
        "print_rolling_opponent_policy_evaluation_result",
        print_rolling_opponent_policy_evaluation_result,
    )(result)
    if output_path is not None:
        print()
        print("Output file written:", output_path)
    _dependency("print_field_provenance_summary", print_field_provenance_summary)(result)
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
    root_document = _dependency("load_json_object", load_json_object)(file_path)
    result, artifacts = _dependency("execute_legacy_application", execute_legacy_application)(
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
        _dependency("write_analysis_result_to_json", write_analysis_result_to_json)(
            output_path=output_path, result=result
        )
    if export_path is not None:
        _dependency("write_analysis_result_to_json", write_analysis_result_to_json)(
            output_path=export_path,
            result=artifacts["opponent_statistics_input"],
        )
    if quiet:
        return
    _dependency(
        "print_historical_opponent_statistics_result",
        print_historical_opponent_statistics_result,
    )(result)
    if output_path is not None:
        print()
        print("Output file written:", output_path)
    if export_path is not None:
        print("Exported opponent statistics to", f"{export_path}.")
    _dependency("print_field_provenance_summary", print_field_provenance_summary)(result)
    return


def run_json_fixed_three_player_historical_list_analysis(
    file_path: str,
    output_path: str | None = None,
    quiet: bool = False,
    include_provenance: bool = False,
) -> None:
    """Runs one complete historical 36-position list aggregation."""
    root_document = _dependency("load_json_object", load_json_object)(file_path)
    result, _artifacts = _dependency("execute_legacy_application", execute_legacy_application)(
        root_document,
        input_reference=file_path,
        include_provenance=include_provenance,
    )
    if output_path is not None:
        _dependency("write_analysis_result_to_json", write_analysis_result_to_json)(
            output_path=output_path, result=result
        )
    if quiet:
        return
    _dependency(
        "print_fixed_three_player_historical_list_result",
        print_fixed_three_player_historical_list_result,
    )(result)
    if output_path is not None:
        print()
        print("Output file written:", output_path)
    _dependency("print_field_provenance_summary", print_field_provenance_summary)(result)
    return


def run_json_fixed_three_player_historical_list_comparison(
    file_path: str,
    output_path: str | None = None,
    quiet: bool = False,
    include_provenance: bool = False,
) -> None:
    """Aggregates each ordered source once and compares it with the first source."""
    root_document = _dependency("load_json_object", load_json_object)(file_path)
    result, _artifacts = _dependency("execute_legacy_application", execute_legacy_application)(
        root_document,
        input_reference=file_path,
        include_provenance=include_provenance,
    )
    if output_path is not None:
        _dependency("write_analysis_result_to_json", write_analysis_result_to_json)(
            output_path=output_path, result=result
        )
    if quiet:
        return
    _dependency(
        "print_fixed_three_player_historical_list_comparison_result",
        print_fixed_three_player_historical_list_comparison_result,
    )(result)
    if output_path is not None:
        print()
        print("Output file written:", output_path)
    _dependency("print_field_provenance_summary", print_field_provenance_summary)(result)
    return


def run_json_opponent_statistics_conversion(
    file_path: str,
    output_path: str | None = None,
    quiet: bool = False,
    include_provenance: bool = False,
) -> None:
    """Runs deterministic external opponent-statistics validation and normalization."""
    root_document = _dependency("load_json_object", load_json_object)(file_path)
    result, _artifacts = _dependency("execute_legacy_application", execute_legacy_application)(
        root_document,
        input_reference=file_path,
        include_provenance=include_provenance,
    )
    if output_path is not None:
        _dependency("write_analysis_result_to_json", write_analysis_result_to_json)(
            output_path=output_path, result=result
        )
    if quiet:
        return
    _dependency("print_opponent_statistics_result", print_opponent_statistics_result)(result)
    if output_path is not None:
        print()
        print("Output file written:", output_path)
    _dependency("print_field_provenance_summary", print_field_provenance_summary)(result)
    return
