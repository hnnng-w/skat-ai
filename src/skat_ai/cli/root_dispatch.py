"""Workflow selection and option dispatch for the Root CLI."""

import sys

from skat_ai.bounded_search_evaluation import (
    DEFAULT_BOUNDED_SEARCH_EVALUATION_PARTITIONS,
)
from skat_ai.cli.root_compatibility import (
    CliUsageError,
    _facade_value,
    _has_active_legacy_patch_namespace,
    _legacy_patch_value,
)
from skat_ai.cli.root_parser import parse_arguments
from skat_ai.errors import (
    CLI_EXIT_CODE_FAILURE,
    CLI_EXIT_CODE_SUCCESS,
    CLI_EXIT_CODE_USAGE,
)
from skat_ai.information_set_search_evaluation import (
    DEFAULT_INFORMATION_SET_SEARCH_EVALUATION_PARTITIONS,
    DEFAULT_INFORMATION_SET_SEARCH_EVALUATION_PROFILE,
)
from skat_ai.rolling_opponent_policy_evaluation import (
    DEFAULT_EVALUATION_PARTITIONS,
    DEFAULT_SOURCE_PARTITIONS,
)
from skat_ai.search_budget_profiles import (
    EVALUATION_SEARCH_BUDGET_PROFILE,
    HISTORICAL_REVIEW_SEARCH_BUDGET_PROFILE,
)
from skat_ai.simulation import DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT


def _run_cli(
    argv: list[str] | tuple[str, ...] | None,
    invocation_style: str,
) -> int:
    if _has_active_legacy_patch_namespace() and argv is None:
        args = _legacy_patch_value("parse_arguments")()
    else:
        args = _facade_value("parse_arguments", parse_arguments)(
            argv, invocation_style=invocation_style
        )

    try:
        input_data = _legacy_patch_value("load_json_object")(args.input)
        workflow = _legacy_patch_value("get_input_workflow")(input_data)
        if workflow == "training_dataset_preparation":
            _legacy_patch_value("validate_training_dataset_preparation_cli_arguments")(args)
        else:
            _legacy_patch_value("validate_cli_arguments")(args, workflow=workflow)
        if workflow == "fixed_three_player_historical_list_comparison":
            _legacy_patch_value("validate_fixed_three_player_historical_list_cli_arguments")(args)
            _legacy_patch_value("run_json_fixed_three_player_historical_list_comparison")(
                file_path=args.input,
                output_path=args.output,
                quiet=args.quiet,
                include_provenance=args.include_provenance,
            )
        elif workflow == "fixed_three_player_historical_list":
            _legacy_patch_value("validate_fixed_three_player_historical_list_cli_arguments")(args)
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
            if args.information_set_search_evaluation:
                _legacy_patch_value("run_json_information_set_search_evaluation")(
                    file_path=args.input,
                    search_seed=args.search_seed,
                    partitions=tuple(
                        args.search_evaluation_partition
                        or DEFAULT_INFORMATION_SET_SEARCH_EVALUATION_PARTITIONS
                    ),
                    search_budget_profile=(
                        args.search_budget_profile
                        or DEFAULT_INFORMATION_SET_SEARCH_EVALUATION_PROFILE
                    ),
                    max_decisions=args.search_evaluation_max_decisions,
                    output_path=args.output,
                    quiet=args.quiet,
                    include_provenance=args.include_provenance,
                )
            elif args.evaluate_bounded_search:
                _legacy_patch_value("run_json_bounded_search_evaluation")(
                    file_path=args.input,
                    search_seed=args.search_seed,
                    partitions=tuple(
                        args.search_evaluation_partition
                        or DEFAULT_BOUNDED_SEARCH_EVALUATION_PARTITIONS
                    ),
                    search_budget_profile=(
                        args.search_budget_profile or EVALUATION_SEARCH_BUDGET_PROFILE
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
                _legacy_patch_value("run_json_historical_opponent_statistics_aggregation")(
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
                historical_information_set_search_review=(
                    args.historical_information_set_search_review
                ),
                historical_replay_coaching=args.historical_replay_coaching,
                search_seed=args.search_seed,
                search_budget_profile=(
                    args.search_budget_profile or HISTORICAL_REVIEW_SEARCH_BUDGET_PROFILE
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
                raise CliUsageError("--historical-search-review requires historical-game input.")
            if args.historical_information_set_search_review:
                raise CliUsageError(
                    "--historical-information-set-search-review requires historical-game input."
                )
            if args.historical_replay_coaching:
                raise CliUsageError("--historical-replay-coaching requires historical-game input.")
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
