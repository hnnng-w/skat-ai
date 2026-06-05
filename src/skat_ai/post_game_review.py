from typing import Any

NOT_AVAILABLE_DECISION_QUALITY = "not_available"
OPTIMAL_DECISION_QUALITY = "optimal"
ACCEPTABLE_DECISION_QUALITY = "acceptable"
SUBOPTIMAL_DECISION_QUALITY = "suboptimal"
MISTAKE_DECISION_QUALITY = "mistake"


def classify_decision_quality(expected_point_swing_difference: float) -> str:
    """Classifies the decision quality based on missed expected point swing."""
    if expected_point_swing_difference <= 0.0:
        return OPTIMAL_DECISION_QUALITY

    if expected_point_swing_difference <= 2.0:
        return ACCEPTABLE_DECISION_QUALITY

    if expected_point_swing_difference <= 6.0:
        return SUBOPTIMAL_DECISION_QUALITY

    return MISTAKE_DECISION_QUALITY


def get_recommended_report_row(
    analysis_report: list[dict[str, Any]],
) -> dict[str, Any]:
    """Returns the single recommended row from the card analysis report."""
    recommended_rows = [
        row for row in analysis_report if row.get("is_recommended") is True
    ]

    if len(recommended_rows) != 1:
        raise ValueError("analysis_report must contain exactly one recommended row.")

    return recommended_rows[0]


def get_report_row_for_card(
    analysis_report: list[dict[str, Any]],
    card: str,
) -> dict[str, Any]:
    """Returns the report row for the given card."""
    matching_rows = [row for row in analysis_report if row.get("card") == card]

    if len(matching_rows) != 1:
        raise ValueError("actual_card_played must be present exactly once in analysis_report.")

    return matching_rows[0]


def build_post_game_review_summary(
    actual_card_played: str | None,
    analysis_report: list[dict[str, Any]],
) -> dict[str, Any]:
    """Builds a post-game review summary for the actual card played."""
    recommended_row = get_recommended_report_row(analysis_report)
    recommended_card = recommended_row["card"]
    recommended_expected_point_swing = recommended_row["expected_point_swing"]

    if actual_card_played is None:
        return {
            "is_available": False,
            "reason": "actual_card_played_not_provided",
            "actual_card_played": None,
            "recommended_card": recommended_card,
            "actual_expected_point_swing": None,
            "recommended_expected_point_swing": recommended_expected_point_swing,
            "expected_point_swing_difference": None,
            "decision_quality": NOT_AVAILABLE_DECISION_QUALITY,
        }

    actual_row = get_report_row_for_card(
        analysis_report=analysis_report,
        card=actual_card_played,
    )
    actual_expected_point_swing = actual_row["expected_point_swing"]
    expected_point_swing_difference = (
        recommended_expected_point_swing - actual_expected_point_swing
    )

    return {
        "is_available": True,
        "reason": "actual_card_played_provided",
        "actual_card_played": actual_card_played,
        "recommended_card": recommended_card,
        "actual_expected_point_swing": actual_expected_point_swing,
        "recommended_expected_point_swing": recommended_expected_point_swing,
        "expected_point_swing_difference": expected_point_swing_difference,
        "decision_quality": classify_decision_quality(
            expected_point_swing_difference
        ),
    }