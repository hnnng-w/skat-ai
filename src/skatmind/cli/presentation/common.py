"""Shared Root CLI presentation helpers."""

from typing import Any

POST_GAME_REVIEW_UNAVAILABLE_REASON_TEXT = {
    "actual_card_played_not_provided": "the actual card was not provided.",
    "immediate_analysis_unavailable": "immediate analysis is unavailable for this position.",
    "expected_point_swing_difference_not_available": (
        "the expected point swing difference is not available."
    ),
}


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
        f"{item['player']} is void in {', '.join(item['forbidden_effective_categories']).title()}"
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


def print_information_set_search_metrics(summary: dict[str, Any]) -> None:
    """Prints aggregate Information-set Search evidence without private state."""
    statuses = summary["status_counts"]
    unavailable_count = statuses.get("unavailable", 0) + statuses.get("not_available", 0)
    print("Evaluated decisions:", summary["decision_count"])
    print(
        "Statuses: "
        f"complete {statuses.get('complete', 0)}, "
        f"partial {statuses.get('partial', 0)}, "
        f"timeout {statuses.get('timeout', 0)}, "
        f"unavailable {unavailable_count}."
    )

    pimc = summary["information_set_pimc_agreement"]
    immediate = summary["information_set_immediate_agreement"]
    print(
        "Recommendation agreement: "
        f"same-selection Search {pimc['same_card_count']} same / "
        f"{pimc['different_card_count']} different / "
        f"{pimc['comparable_decision_count']} comparable; "
        f"Immediate {immediate['same_card_count']} same / "
        f"{immediate['different_card_count']} different / "
        f"{immediate['comparable_decision_count']} comparable."
    )

    information_set_actual = summary["information_set_actual_agreement"]
    pimc_actual = summary["pimc_actual_agreement"]
    immediate_actual = summary["immediate_actual_agreement"]
    print(
        "Actual-card agreement: "
        f"Information-set Search {information_set_actual['same_card_count']} same / "
        f"{information_set_actual['different_card_count']} different / "
        f"{information_set_actual['comparable_decision_count']} comparable; "
        f"same-selection Search {pimc_actual['same_card_count']} same / "
        f"{pimc_actual['different_card_count']} different / "
        f"{pimc_actual['comparable_decision_count']} comparable; "
        f"Immediate {immediate_actual['same_card_count']} same / "
        f"{immediate_actual['different_card_count']} different / "
        f"{immediate_actual['comparable_decision_count']} comparable."
    )

    coverage = summary["coverage_counts"]
    print(
        "Selected-world coverage: "
        f"none {coverage.get('none', 0)}, "
        f"single exact {coverage.get('single_exact_world', 0)}, "
        f"all compatible {coverage.get('all_compatible_worlds', 0)}, "
        f"sampled compatible {coverage.get('sampled_compatible_worlds', 0)}; "
        f"{summary['selected_world_count_total']} selected; "
        f"{summary['sampled_world_count_total']} sampled draws."
    )
