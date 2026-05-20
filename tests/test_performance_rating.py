from skat_ai.performance_rating import build_performance_rating_summary


def test_build_performance_rating_summary_for_complete_settlement() -> None:
    summary = build_performance_rating_summary(
        final_settlement_summary={
            "settlement_score": 72,
        }
    )

    assert summary == {
        "is_implemented": False,
        "basis": "individual_game_settlement",
        "settlement_score": 72,
        "rating_score": None,
        "rating_system": None,
        "notes": [
            "Performance rating is separate from individual game settlement.",
            "List, series, and tournament rating are not implemented yet.",
            "final_settlement_summary remains the source for single-game settlement.",
        ],
    }


def test_build_performance_rating_summary_for_incomplete_settlement() -> None:
    summary = build_performance_rating_summary(
        final_settlement_summary={
            "settlement_score": None,
        }
    )

    assert summary["is_implemented"] is False
    assert summary["settlement_score"] is None
    assert summary["rating_score"] is None