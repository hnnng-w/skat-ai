"""Training-dataset and evaluation result presentation."""

from typing import Any

from skat_ai.cli.presentation.common import print_information_set_search_metrics
from skat_ai.training_dataset_preparation import TrainingDatasetPreparationRequest
from skat_ai.training_dataset_preparation_workflow import (
    TrainingDatasetPreparationResult,
)


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
            f"{boundary.partition} {boundary.minimum_played_at} to {boundary.maximum_played_at}"
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
    print(f"Dataset identity: {request['dataset_id']}, version {request['dataset_version']}")
    print("Mode:", plan["mode"])
    print("Algorithm:", plan["algorithm"])
    print("Status:", plan["status"])
    if plan["status"] == "unavailable":
        print("Unavailable reason:", plan["unavailable_reason"])
    print(
        "Source Record and Sample Counts:",
        f"{plan['source_record_count']} records, {plan['source_sample_count']} samples",
    )
    print(
        "Requested weights:",
        f"train {weights['train']}, validation {weights['validation']}, test {weights['test']}",
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


def print_information_set_search_evaluation_result(
    result: dict[str, Any],
) -> None:
    """Prints only aggregate, information-safe evaluation metrics."""
    summary = result["information_set_search_evaluation_summary"]
    print("Information-set Search evaluation records:", summary["record_count"])
    print_information_set_search_metrics(summary)


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
