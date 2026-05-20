from skat_ai.performance_rating import (
    build_performance_rating_summary,
    get_game_outcome_for_rating,
)


def test_get_game_outcome_for_rating_returns_incomplete() -> None:
    assert get_game_outcome_for_rating(
        {
            "is_complete": False,
            "is_loss": None,
        }
    ) == "incomplete"


def test_get_game_outcome_for_rating_returns_declarer_win() -> None:
    assert get_game_outcome_for_rating(
        {
            "is_complete": True,
            "is_loss": False,
        }
    ) == "declarer_win"


def test_get_game_outcome_for_rating_returns_declarer_loss() -> None:
    assert get_game_outcome_for_rating(
        {
            "is_complete": True,
            "is_loss": True,
        }
    ) == "declarer_loss"


def test_get_game_outcome_for_rating_returns_unknown() -> None:
    assert get_game_outcome_for_rating(
        {
            "is_complete": True,
            "is_loss": None,
        }
    ) == "unknown"


def test_build_performance_rating_summary_for_complete_settlement() -> None:
    summary = build_performance_rating_summary(
        final_settlement_summary={
            "is_complete": True,
            "is_loss": False,
            "settlement_score": 72,
        }
    )

    assert summary == {
        "is_implemented": False,
        "rating_system": None,
        "basis": "individual_game_settlement",
        "game_outcome": "declarer_win",
        "settlement_score": 72,
        "rating_score": None,
        "declarer_rating_points": None,
        "defender_rating_points": None,
        "unsupported_reason": "performance_rating_not_implemented",
        "notes": [
            "Performance rating is separate from individual game settlement.",
            "List, series, and tournament rating are not implemented yet.",
            "final_settlement_summary remains the source for single-game settlement.",
        ],
    }


def test_build_performance_rating_summary_for_incomplete_settlement() -> None:
    summary = build_performance_rating_summary(
        final_settlement_summary={
            "is_complete": False,
            "is_loss": None,
            "settlement_score": None,
        }
    )

    assert summary["is_implemented"] is False
    assert summary["game_outcome"] == "incomplete"
    assert summary["settlement_score"] is None
    assert summary["rating_score"] is None
    assert summary["unsupported_reason"] == "performance_rating_not_implemented"


def test_build_performance_rating_summary_accepts_placeholder_rating_system() -> None:
    summary = build_performance_rating_summary(
        final_settlement_summary={
            "is_complete": True,
            "is_loss": False,
            "settlement_score": 72,
        },
        rating_system="placeholder",
    )

    assert summary["rating_system"] == "placeholder"
    assert summary["game_outcome"] == "declarer_win"


def test_build_performance_rating_summary_rejects_unknown_rating_system() -> None:
    try:
        build_performance_rating_summary(
            final_settlement_summary={
                "is_complete": True,
                "is_loss": False,
                "settlement_score": 72,
            },
            rating_system="isko_list",
        )
    except ValueError as error:
        assert "Unknown performance rating system" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")