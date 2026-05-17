from skat_ai.game_result import (
    build_game_result_summary_from_points,
    build_game_result_summary_from_score_summary,
    get_card_point_result_status,
    get_card_point_winner,
    get_points_remaining,
    is_card_point_result_complete,
)


def test_get_points_remaining() -> None:
    assert get_points_remaining(61, 30) == 29


def test_get_points_remaining_rejects_too_many_points() -> None:
    try:
        get_points_remaining(80, 50)
    except ValueError as error:
        assert "exceed total card points" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_is_card_point_result_complete() -> None:
    assert is_card_point_result_complete(61, 59) is True
    assert is_card_point_result_complete(61, 30) is False


def test_get_card_point_winner_declarer() -> None:
    assert get_card_point_winner(61, 20) == "declarer"


def test_get_card_point_winner_defenders() -> None:
    assert get_card_point_winner(30, 60) == "defenders"


def test_get_card_point_winner_undecided() -> None:
    assert get_card_point_winner(40, 40) == "undecided"


def test_get_card_point_result_status_final_decided() -> None:
    assert get_card_point_result_status(61, 59) == "final_decided"


def test_get_card_point_result_status_currently_decided() -> None:
    assert get_card_point_result_status(61, 20) == "currently_decided"


def test_get_card_point_result_status_final_decided_at_60_60() -> None:
    assert get_card_point_result_status(60, 60) == "final_decided"


def test_get_card_point_result_status_in_progress() -> None:
    assert get_card_point_result_status(40, 40) == "in_progress"


def test_build_game_result_summary_from_points() -> None:
    summary = build_game_result_summary_from_points(
        declarer_points=61,
        defender_points=30,
    )

    assert summary == {
        "declarer_points": 61,
        "defender_points": 30,
        "points_remaining": 29,
        "is_complete": False,
        "winner": "declarer",
        "status": "currently_decided",
        "thresholds": {
            "declarer_win": 61,
            "defender_win": 60,
            "total_card_points": 120,
        },
    }


def test_build_game_result_summary_from_score_summary() -> None:
    score_summary = {
        "explicit_declarer_points": 0,
        "explicit_defender_points": 0,
        "completed_trick_declarer_points": 61,
        "completed_trick_defender_points": 30,
        "total_declarer_points": 61,
        "total_defender_points": 30,
    }

    summary = build_game_result_summary_from_score_summary(score_summary)

    assert summary["winner"] == "declarer"
    assert summary["status"] == "currently_decided"