from skat_ai.game_result import (
    build_game_result_summary_from_points,
    build_game_result_summary_from_score_summary,
    get_card_point_result_status,
    get_card_point_winner,
    get_completed_trick_schwarz_status,
    get_effective_schneider_status,
    get_effective_schwarz_status,
    get_points_remaining,
    get_schneider_status,
    get_schwarz_status,
    is_card_point_result_complete,
)


def build_score_summary(
    declarer_points: int,
    defender_points: int,
) -> dict[str, int]:
    return {
        "explicit_declarer_points": 0,
        "explicit_defender_points": 0,
        "completed_trick_declarer_points": declarer_points,
        "completed_trick_defender_points": defender_points,
        "total_declarer_points": declarer_points,
        "total_defender_points": defender_points,
    }


def build_completed_null_tricks(winner_roles: list[str]) -> list[dict[str, object]]:
    return [
        {
            "cards": ["C7", "C8", "C9"],
            "winner_role": winner_role,
        }
        for winner_role in winner_roles
    ]


def build_completed_schwarz_tricks(winner_roles: list[str]) -> list[dict[str, object]]:
    return [
        {
            "cards": ["C7", "C8", "C9"],
            "winner_role": winner_role,
        }
        for winner_role in winner_roles
    ]


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
        "raw_schneider_status": "declarer_made_schneider",
        "raw_schwarz_status": "none",
        "effective_schneider_status": "pending",
        "effective_schwarz_status": "pending",
        "thresholds": {
            "declarer_win": 61,
            "defender_win": 60,
            "schneider": 30,
            "schwarz": 0,
            "total_card_points": 120,
        },
    }


def test_build_game_result_summary_from_score_summary() -> None:
    score_summary = build_score_summary(61, 30)

    summary = build_game_result_summary_from_score_summary(score_summary)

    assert summary["winner"] == "declarer"
    assert summary["status"] == "currently_decided"


def test_completed_null_zero_declarer_tricks_is_declarer_win() -> None:
    summary = build_game_result_summary_from_score_summary(
        score_summary=build_score_summary(0, 120),
        game_type="null",
        completed_tricks=build_completed_null_tricks(["defenders"] * 10),
        game_end_reason="normal_completion",
    )

    assert summary["is_complete"] is True
    assert summary["winner"] == "declarer"
    assert summary["status"] == "final_decided"


def test_completed_null_zero_point_declarer_trick_is_declarer_loss() -> None:
    completed_tricks = build_completed_null_tricks(
        ["declarer", *["defenders"] * 9]
    )
    completed_tricks[0]["cards"] = ["C7", "C8", "C9"]

    summary = build_game_result_summary_from_score_summary(
        score_summary=build_score_summary(0, 120),
        game_type="null",
        completed_tricks=completed_tricks,
        game_end_reason="normal_completion",
    )

    assert summary["declarer_points"] == 0
    assert summary["is_complete"] is True
    assert summary["winner"] == "defenders"


def test_completed_null_point_bearing_declarer_trick_is_declarer_loss() -> None:
    completed_tricks = build_completed_null_tricks(
        ["declarer", *["defenders"] * 9]
    )
    completed_tricks[0]["cards"] = ["CA", "C10", "CK"]

    summary = build_game_result_summary_from_score_summary(
        score_summary=build_score_summary(70, 50),
        game_type="null",
        completed_tricks=completed_tricks,
        game_end_reason="normal_completion",
    )

    assert summary["declarer_points"] == 70
    assert summary["is_complete"] is True
    assert summary["winner"] == "defenders"


def test_incomplete_null_history_does_not_fall_back_to_card_points() -> None:
    summary = build_game_result_summary_from_score_summary(
        score_summary=build_score_summary(0, 120),
        game_type="null",
        completed_tricks=build_completed_null_tricks(["defenders"] * 9),
        game_end_reason="normal_completion",
    )

    assert summary["is_complete"] is False
    assert summary["winner"] == "undecided"
    assert summary["status"] == "in_progress"


def test_completed_null_rejects_missing_winner_role() -> None:
    completed_tricks = build_completed_null_tricks(["defenders"] * 10)
    del completed_tricks[0]["winner_role"]

    try:
        build_game_result_summary_from_score_summary(
            score_summary=build_score_summary(0, 120),
            game_type="null",
            completed_tricks=completed_tricks,
            game_end_reason="normal_completion",
        )
    except ValueError as error:
        assert "winner_role is required" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_completed_null_rejects_non_object_completed_trick() -> None:
    completed_tricks = build_completed_null_tricks(["defenders"] * 10)
    completed_tricks[0] = "not-an-object"

    try:
        build_game_result_summary_from_score_summary(
            score_summary=build_score_summary(0, 120),
            game_type="null",
            completed_tricks=completed_tricks,
            game_end_reason="normal_completion",
        )
    except ValueError as error:
        assert "must be an object" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_completed_null_rejects_unknown_winner_role() -> None:
    completed_tricks = build_completed_null_tricks(["defenders"] * 10)
    completed_tricks[0]["winner_role"] = "unknown"

    try:
        build_game_result_summary_from_score_summary(
            score_summary=build_score_summary(0, 120),
            game_type="null",
            completed_tricks=completed_tricks,
            game_end_reason="normal_completion",
        )
    except ValueError as error:
        assert "Invalid completed Null trick winner_role" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_suit_and_grand_results_stay_card_point_based() -> None:
    grand_summary = build_game_result_summary_from_score_summary(
        score_summary=build_score_summary(61, 59),
        game_type="grand",
        completed_tricks=[],
        game_end_reason="normal_completion",
    )
    suit_summary = build_game_result_summary_from_score_summary(
        score_summary=build_score_summary(50, 70),
        game_type="spades",
        completed_tricks=[],
        game_end_reason="normal_completion",
    )

    assert grand_summary["is_complete"] is True
    assert grand_summary["winner"] == "declarer"
    assert suit_summary["is_complete"] is True
    assert suit_summary["winner"] == "defenders"

def test_get_schneider_status_declarer_made_schneider() -> None:
    assert get_schneider_status(90, 30) == "declarer_made_schneider"


def test_get_schneider_status_defenders_made_schneider() -> None:
    assert get_schneider_status(30, 90) == "defenders_made_schneider"


def test_get_schneider_status_none() -> None:
    assert get_schneider_status(70, 50) == "none"


def test_get_schwarz_status_declarer_made_schwarz() -> None:
    assert get_schwarz_status(120, 0) == "declarer_made_schwarz"


def test_get_schwarz_status_defenders_made_schwarz() -> None:
    assert get_schwarz_status(0, 120) == "defenders_made_schwarz"


def test_get_schwarz_status_none() -> None:
    assert get_schwarz_status(70, 50) == "none"

def test_get_effective_schneider_status_pending_when_incomplete() -> None:
    assert get_effective_schneider_status(0, 0) == "pending"


def test_get_effective_schneider_status_when_complete() -> None:
    assert get_effective_schneider_status(90, 30) == "declarer_made_schneider"


def test_get_effective_schneider_status_none_when_complete() -> None:
    assert get_effective_schneider_status(70, 50) == "none"


def test_get_effective_schwarz_status_pending_when_incomplete() -> None:
    assert get_effective_schwarz_status(0, 0) == "pending"


def test_get_effective_schwarz_status_when_complete() -> None:
    assert get_effective_schwarz_status(120, 0) == "declarer_made_schwarz"


def test_get_effective_schwarz_status_none_when_complete() -> None:
    assert get_effective_schwarz_status(70, 50) == "none"


def test_completed_trick_schwarz_status_declarer() -> None:
    assert get_completed_trick_schwarz_status(
        build_completed_schwarz_tricks(["declarer"] * 10)
    ) == "declarer"


def test_completed_trick_schwarz_status_defenders() -> None:
    assert get_completed_trick_schwarz_status(
        build_completed_schwarz_tricks(["defenders"] * 10)
    ) == "defenders"


def test_completed_trick_schwarz_status_none_for_mixed_ownership() -> None:
    assert get_completed_trick_schwarz_status(
        build_completed_schwarz_tricks(["declarer", *["defenders"] * 9])
    ) == "none"


def test_completed_trick_schwarz_status_zero_point_trick_prevents_schwarz() -> None:
    completed_tricks = build_completed_schwarz_tricks(["declarer"] * 9)
    completed_tricks.append(
        {
            "cards": ["C7", "C8", "C9"],
            "winner_role": "defenders",
        }
    )

    assert get_completed_trick_schwarz_status(completed_tricks) == "none"


def test_completed_trick_schwarz_status_unresolved_for_incomplete_history() -> None:
    assert get_completed_trick_schwarz_status(
        build_completed_schwarz_tricks(["declarer"] * 9)
    ) == "unresolved"


def test_completed_trick_schwarz_status_rejects_overlong_history() -> None:
    try:
        get_completed_trick_schwarz_status(
            build_completed_schwarz_tricks(["declarer"] * 11)
        )
    except ValueError as error:
        assert "exactly ten completed tricks" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_completed_trick_schwarz_status_rejects_missing_winner_role() -> None:
    completed_tricks = build_completed_schwarz_tricks(["declarer"] * 10)
    del completed_tricks[0]["winner_role"]

    try:
        get_completed_trick_schwarz_status(completed_tricks)
    except ValueError as error:
        assert "winner_role is required" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_completed_trick_schwarz_status_rejects_invalid_winner_role() -> None:
    completed_tricks = build_completed_schwarz_tricks(["declarer"] * 10)
    completed_tricks[0]["winner_role"] = "unknown"

    try:
        get_completed_trick_schwarz_status(completed_tricks)
    except ValueError as error:
        assert "Invalid completed Schwarz trick winner_role" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_completed_trick_schwarz_status_rejects_non_object_entry() -> None:
    completed_tricks = build_completed_schwarz_tricks(["declarer"] * 10)
    completed_tricks[0] = "not-an-object"

    try:
        get_completed_trick_schwarz_status(completed_tricks)
    except ValueError as error:
        assert "must be an object" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_build_game_result_summary_from_points_complete_schneider() -> None:
    summary = build_game_result_summary_from_points(
        declarer_points=90,
        defender_points=30,
    )

    assert summary["is_complete"] is True
    assert summary["raw_schneider_status"] == "declarer_made_schneider"
    assert summary["effective_schneider_status"] == "declarer_made_schneider"
    assert summary["effective_schwarz_status"] == "none"
