"""Semantic option validation for Root CLI workflows."""

import argparse
from pathlib import Path
from typing import Any

from skat_ai.errors import SkatAICliUsageError
from skat_ai.input_validation import MAX_SAMPLE_COUNT
from skat_ai.rolling_opponent_policy_evaluation import (
    DEFAULT_EVALUATION_PARTITIONS,
    DEFAULT_SOURCE_PARTITIONS,
)

CliUsageError = SkatAICliUsageError


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
