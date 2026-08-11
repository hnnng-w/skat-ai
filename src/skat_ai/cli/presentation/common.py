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
