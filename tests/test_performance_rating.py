from skat_ai.performance_rating import (
    build_performance_rating_summary,
    calculate_isko_counterparty_rating_points,
    calculate_isko_declarer_rating_points,
    get_game_outcome_for_rating,
    get_performance_rating_unsupported_reason,
    is_performance_rating_partially_implemented,
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
        "is_partially_implemented": False,
        "rating_system": None,
        "table_player_count": 3,
        "basis": "individual_game_settlement",
        "game_outcome": "declarer_win",
        "settlement_score": 72,
        "rating_score": None,
        "declarer_rating_points": None,
        "counterparty_rating_points": None,
        "defender_rating_points": None,
        "unsupported_reason": "performance_rating_not_implemented",
        "notes": [
            "Performance rating is separate from individual game settlement.",
            "List, series, and tournament rating are not fully implemented yet.",
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

    assert summary == {
        "is_implemented": False,
        "is_partially_implemented": False,
        "rating_system": "placeholder",
        "basis": "individual_game_settlement",
        "game_outcome": "declarer_win",
        "settlement_score": 72,
        "rating_score": None,
        "declarer_rating_points": None,
        "defender_rating_points": None,
        "unsupported_reason": "performance_rating_not_implemented",
        "table_player_count": 3,
        "counterparty_rating_points": None,
        "notes": [
            "Performance rating is separate from individual game settlement.",
            "List, series, and tournament rating are not fully implemented yet.",
            "final_settlement_summary remains the source for single-game settlement.",
        ],
    }


def test_build_performance_rating_summary_accepts_isko_list_rating_system() -> None:
    summary = build_performance_rating_summary(
        final_settlement_summary={
            "is_complete": True,
            "is_loss": False,
            "settlement_score": 72,
        },
        rating_system="isko_list",
    )

    assert summary == {
        "is_implemented": False,
        "is_partially_implemented": True,
        "rating_system": "isko_list",
        "table_player_count": 3,
        "basis": "individual_game_settlement",
        "game_outcome": "declarer_win",
        "settlement_score": 72,
        "rating_score": None,
        "declarer_rating_points": 50,
        "counterparty_rating_points": 0,
        "defender_rating_points": 0,
        "unsupported_reason": "isko_list_rating_not_implemented",
        "notes": [
            "Performance rating is separate from individual game settlement.",
            "List, series, and tournament rating are not fully implemented yet.",
            "final_settlement_summary remains the source for single-game settlement.",
        ],
    }

def test_build_performance_rating_summary_for_isko_declarer_loss() -> None:
    summary = build_performance_rating_summary(
        final_settlement_summary={
            "is_complete": True,
            "is_loss": True,
            "settlement_score": -144,
        },
        rating_system="isko_list",
    )

    assert summary["is_implemented"] is False
    assert summary["is_partially_implemented"] is True
    assert summary["rating_system"] == "isko_list"
    assert summary["table_player_count"] == 3
    assert summary["game_outcome"] == "declarer_loss"
    assert summary["settlement_score"] == -144
    assert summary["rating_score"] is None
    assert summary["declarer_rating_points"] == -50
    assert summary["counterparty_rating_points"] == 40
    assert summary["defender_rating_points"] == 40
    assert summary["unsupported_reason"] == "isko_list_rating_not_implemented"

def test_build_performance_rating_summary_rejects_unknown_rating_system() -> None:
    try:
        build_performance_rating_summary(
            final_settlement_summary={
                "is_complete": True,
                "is_loss": False,
                "settlement_score": 72,
            },
            rating_system="unknown_system",
        )
    except ValueError as error:
        assert "Unknown performance rating system" in str(error)
        assert "unknown_system" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")

def test_get_performance_rating_unsupported_reason_for_default() -> None:
    assert get_performance_rating_unsupported_reason(None) == (
        "performance_rating_not_implemented"
    )


def test_get_performance_rating_unsupported_reason_for_placeholder() -> None:
    assert get_performance_rating_unsupported_reason("placeholder") == (
        "performance_rating_not_implemented"
    )


def test_get_performance_rating_unsupported_reason_for_isko_list() -> None:
    assert get_performance_rating_unsupported_reason("isko_list") == (
        "isko_list_rating_not_implemented"
    )

def test_calculate_isko_declarer_rating_points_for_declarer_win() -> None:
    assert calculate_isko_declarer_rating_points("declarer_win") == 50


def test_calculate_isko_declarer_rating_points_for_declarer_loss() -> None:
    assert calculate_isko_declarer_rating_points("declarer_loss") == -50


def test_calculate_isko_declarer_rating_points_for_incomplete_game() -> None:
    assert calculate_isko_declarer_rating_points("incomplete") is None


def test_calculate_isko_declarer_rating_points_for_unknown_outcome() -> None:
    assert calculate_isko_declarer_rating_points("unknown") is None

def test_is_performance_rating_partially_implemented_for_isko_list() -> None:
    assert is_performance_rating_partially_implemented("isko_list") is True


def test_is_performance_rating_partially_implemented_for_placeholder() -> None:
    assert is_performance_rating_partially_implemented("placeholder") is False


def test_is_performance_rating_partially_implemented_for_none() -> None:
    assert is_performance_rating_partially_implemented(None) is False

def test_calculate_isko_counterparty_rating_points_for_declarer_win() -> None:
    assert calculate_isko_counterparty_rating_points("declarer_win") == 0


def test_calculate_isko_counterparty_rating_points_for_declarer_loss() -> None:
    assert calculate_isko_counterparty_rating_points("declarer_loss") == 40


def test_calculate_isko_counterparty_rating_points_for_incomplete_game() -> None:
    assert calculate_isko_counterparty_rating_points("incomplete") is None


def test_calculate_isko_counterparty_rating_points_for_unknown_outcome() -> None:
    assert calculate_isko_counterparty_rating_points("unknown") is None