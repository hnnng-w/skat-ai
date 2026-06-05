import pytest

from skat_ai.post_game_review import (
    ACCEPTABLE_DECISION_QUALITY,
    MISTAKE_DECISION_QUALITY,
    NOT_AVAILABLE_DECISION_QUALITY,
    OPTIMAL_DECISION_QUALITY,
    SUBOPTIMAL_DECISION_QUALITY,
    build_post_game_review_summary,
    classify_decision_quality,
    get_recommended_report_row,
    get_report_row_for_card,
)


def build_analysis_report() -> list[dict[str, object]]:
    return [
        {
            "card": "SA",
            "win_rate": 0.75,
            "average_trick_points": 14.0,
            "average_points_won": 10.0,
            "average_points_lost": 4.0,
            "expected_point_swing": 6.0,
            "is_recommended": True,
        },
        {
            "card": "S10",
            "win_rate": 0.60,
            "average_trick_points": 12.0,
            "average_points_won": 8.0,
            "average_points_lost": 4.0,
            "expected_point_swing": 4.0,
            "is_recommended": False,
        },
        {
            "card": "S9",
            "win_rate": 0.10,
            "average_trick_points": 3.0,
            "average_points_won": 1.0,
            "average_points_lost": 5.0,
            "expected_point_swing": -4.0,
            "is_recommended": False,
        },
    ]


def test_classify_decision_quality_marks_zero_difference_as_optimal() -> None:
    assert classify_decision_quality(0.0) == OPTIMAL_DECISION_QUALITY


def test_classify_decision_quality_marks_negative_difference_as_optimal() -> None:
    assert classify_decision_quality(-1.0) == OPTIMAL_DECISION_QUALITY


def test_classify_decision_quality_marks_small_difference_as_acceptable() -> None:
    assert classify_decision_quality(2.0) == ACCEPTABLE_DECISION_QUALITY


def test_classify_decision_quality_marks_medium_difference_as_suboptimal() -> None:
    assert classify_decision_quality(6.0) == SUBOPTIMAL_DECISION_QUALITY


def test_classify_decision_quality_marks_large_difference_as_mistake() -> None:
    assert classify_decision_quality(6.01) == MISTAKE_DECISION_QUALITY


def test_get_recommended_report_row_returns_single_recommended_row() -> None:
    row = get_recommended_report_row(build_analysis_report())

    assert row["card"] == "SA"


def test_get_recommended_report_row_rejects_missing_recommended_row() -> None:
    report = build_analysis_report()
    for row in report:
        row["is_recommended"] = False

    with pytest.raises(
        ValueError,
        match="analysis_report must contain exactly one recommended row",
    ):
        get_recommended_report_row(report)


def test_get_recommended_report_row_rejects_multiple_recommended_rows() -> None:
    report = build_analysis_report()
    report[1]["is_recommended"] = True

    with pytest.raises(
        ValueError,
        match="analysis_report must contain exactly one recommended row",
    ):
        get_recommended_report_row(report)


def test_get_report_row_for_card_returns_matching_card_row() -> None:
    row = get_report_row_for_card(
        analysis_report=build_analysis_report(),
        card="S10",
    )

    assert row["expected_point_swing"] == 4.0


def test_get_report_row_for_card_rejects_missing_card() -> None:
    with pytest.raises(
        ValueError,
        match="actual_card_played must be present exactly once in analysis_report",
    ):
        get_report_row_for_card(
            analysis_report=build_analysis_report(),
            card="H7",
        )


def test_build_post_game_review_summary_returns_not_available_without_actual_card() -> None:
    summary = build_post_game_review_summary(
        actual_card_played=None,
        analysis_report=build_analysis_report(),
    )

    assert summary == {
        "is_available": False,
        "reason": "actual_card_played_not_provided",
        "actual_card_played": None,
        "recommended_card": "SA",
        "actual_expected_point_swing": None,
        "recommended_expected_point_swing": 6.0,
        "expected_point_swing_difference": None,
        "decision_quality": NOT_AVAILABLE_DECISION_QUALITY,
    }


def test_build_post_game_review_summary_marks_recommended_actual_card_as_optimal() -> None:
    summary = build_post_game_review_summary(
        actual_card_played="SA",
        analysis_report=build_analysis_report(),
    )

    assert summary["is_available"] is True
    assert summary["actual_card_played"] == "SA"
    assert summary["recommended_card"] == "SA"
    assert summary["actual_expected_point_swing"] == 6.0
    assert summary["recommended_expected_point_swing"] == 6.0
    assert summary["expected_point_swing_difference"] == 0.0
    assert summary["decision_quality"] == OPTIMAL_DECISION_QUALITY


def test_build_post_game_review_summary_calculates_expected_value_difference() -> None:
    summary = build_post_game_review_summary(
        actual_card_played="S10",
        analysis_report=build_analysis_report(),
    )

    assert summary["actual_expected_point_swing"] == 4.0
    assert summary["recommended_expected_point_swing"] == 6.0
    assert summary["expected_point_swing_difference"] == 2.0
    assert summary["decision_quality"] == ACCEPTABLE_DECISION_QUALITY


def test_build_post_game_review_summary_classifies_large_gap_as_mistake() -> None:
    summary = build_post_game_review_summary(
        actual_card_played="S9",
        analysis_report=build_analysis_report(),
    )

    assert summary["actual_expected_point_swing"] == -4.0
    assert summary["recommended_expected_point_swing"] == 6.0
    assert summary["expected_point_swing_difference"] == 10.0
    assert summary["decision_quality"] == MISTAKE_DECISION_QUALITY