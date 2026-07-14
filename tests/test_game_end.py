from skat_ai.game_end import (
    apply_remaining_points_assignment,
    get_remaining_points_recipient,
    validate_game_end_reason,
    validate_game_end_reason_for_points,
)


def build_incomplete_game_result_summary() -> dict:
    return {
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


def test_get_remaining_points_recipient_for_declarer_claim() -> None:
    assert get_remaining_points_recipient(
        "declarer_claimed_remaining_tricks"
    ) == "declarer"


def test_get_remaining_points_recipient_for_defenders_concession() -> None:
    assert get_remaining_points_recipient(
        "defenders_conceded_remaining_tricks"
    ) == "declarer"


def test_get_remaining_points_recipient_for_declarer_concession() -> None:
    assert get_remaining_points_recipient(
        "declarer_conceded_remaining_tricks"
    ) == "defenders"


def test_get_remaining_points_recipient_for_normal_completion() -> None:
    assert get_remaining_points_recipient("normal_completion") is None


def test_get_remaining_points_recipient_for_not_ended() -> None:
    assert get_remaining_points_recipient("not_ended") is None


def test_get_remaining_points_recipient_rejects_unknown_reason() -> None:
    try:
        get_remaining_points_recipient("unknown_reason")
    except ValueError as error:
        assert "Unknown game_end_reason" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_apply_remaining_points_assignment_for_declarer_claim() -> None:
    summary = apply_remaining_points_assignment(
        game_result_summary=build_incomplete_game_result_summary(),
        game_end_reason="declarer_claimed_remaining_tricks",
    )

    assert summary["declarer_points"] == 90
    assert summary["defender_points"] == 30
    assert summary["points_remaining"] == 0
    assert summary["is_complete"] is True
    assert summary["winner"] == "declarer"
    assert summary["status"] == "final_decided"
    assert summary["effective_schneider_status"] == "declarer_made_schneider"
    assert summary["game_end_reason"] == "declarer_claimed_remaining_tricks"
    assert summary["remaining_points_recipient"] == "declarer"
    assert summary["remaining_points_assigned"] == 29


def test_apply_remaining_points_assignment_for_defenders_concession() -> None:
    summary = apply_remaining_points_assignment(
        game_result_summary=build_incomplete_game_result_summary(),
        game_end_reason="defenders_conceded_remaining_tricks",
    )

    assert summary["declarer_points"] == 90
    assert summary["defender_points"] == 30
    assert summary["points_remaining"] == 0
    assert summary["is_complete"] is True
    assert summary["winner"] == "declarer"
    assert summary["remaining_points_recipient"] == "declarer"
    assert summary["remaining_points_assigned"] == 29


def build_declarer_behind_game_result_summary() -> dict:
    return {
        "declarer_points": 40,
        "defender_points": 50,
        "points_remaining": 30,
        "is_complete": False,
        "winner": "undecided",
        "status": "in_progress",
        "raw_schneider_status": "none",
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

def test_apply_remaining_points_assignment_for_declarer_concession() -> None:
    summary = apply_remaining_points_assignment(
        game_result_summary=build_declarer_behind_game_result_summary(),
        game_end_reason="declarer_conceded_remaining_tricks",
    )

    assert summary["declarer_points"] == 40
    assert summary["defender_points"] == 80
    assert summary["points_remaining"] == 0
    assert summary["is_complete"] is True
    assert summary["winner"] == "defenders"
    assert summary["status"] == "final_decided"
    assert summary["remaining_points_recipient"] == "defenders"
    assert summary["remaining_points_assigned"] == 30

def test_apply_remaining_points_assignment_for_not_ended_keeps_points() -> None:
    original_summary = build_incomplete_game_result_summary()

    summary = apply_remaining_points_assignment(
        game_result_summary=original_summary,
        game_end_reason="not_ended",
    )

    assert summary["declarer_points"] == 61
    assert summary["defender_points"] == 30
    assert summary["points_remaining"] == 29
    assert summary["is_complete"] is False
    assert summary["game_end_reason"] == "not_ended"
    assert summary["remaining_points_recipient"] is None
    assert summary["remaining_points_assigned"] == 0
    assert summary is not original_summary


def test_apply_remaining_points_assignment_accepts_complete_normal_result() -> None:
    original_summary = build_incomplete_game_result_summary()
    original_summary["is_complete"] = True
    original_summary["winner"] = "declarer"

    summary = apply_remaining_points_assignment(
        game_result_summary=original_summary,
        game_end_reason="normal_completion",
    )

    assert summary["points_remaining"] == 29
    assert summary["is_complete"] is True
    assert summary["winner"] == "declarer"
    assert summary["game_end_reason"] == "normal_completion"
    assert summary["remaining_points_recipient"] is None
    assert summary["remaining_points_assigned"] == 0


def test_impossible_null_is_immediate_loss_without_point_assignment() -> None:
    original_summary = build_incomplete_game_result_summary()
    original_summary.update(
        {
            "declarer_points": 0,
            "defender_points": 0,
            "points_remaining": 120,
            "winner": "undecided",
        }
    )

    summary = apply_remaining_points_assignment(
        game_result_summary=original_summary,
        game_end_reason="impossible_null_declaration",
    )

    assert summary["is_complete"] is True
    assert summary["winner"] == "defenders"
    assert summary["points_remaining"] == 120
    assert summary["remaining_points_assigned"] == 0
    assert summary["effective_schneider_status"] == "not_applicable"
    assert summary["effective_schwarz_status"] == "not_applicable"

def test_validate_game_end_reason_accepts_valid_reason() -> None:
    validate_game_end_reason("not_ended")
    validate_game_end_reason("normal_completion")
    validate_game_end_reason("declarer_claimed_remaining_tricks")
    validate_game_end_reason("declarer_conceded_remaining_tricks")
    validate_game_end_reason("defenders_conceded_remaining_tricks")
    validate_game_end_reason("impossible_null_declaration")


def test_validate_game_end_reason_rejects_unknown_reason() -> None:
    try:
        validate_game_end_reason("unknown_reason")
    except ValueError as error:
        assert "Unknown game_end_reason" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_game_end_reason_for_points_accepts_not_ended_with_remaining_points() -> None:
    validate_game_end_reason_for_points(
        game_end_reason="not_ended",
        points_remaining=10,
    )


def test_validate_game_end_reason_for_points_rejects_not_ended_without_remaining_points() -> None:
    try:
        validate_game_end_reason_for_points(
            game_end_reason="not_ended",
            points_remaining=0,
        )
    except ValueError as error:
        assert "not_ended requires remaining card points" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_game_end_reason_accepts_completed_normal_game() -> None:
    validate_game_end_reason_for_points(
        game_end_reason="normal_completion",
        points_remaining=0,
    )


def test_validate_game_end_reason_rejects_incomplete_normal_game() -> None:
    try:
        validate_game_end_reason_for_points(
            game_end_reason="normal_completion",
            points_remaining=10,
        )
    except ValueError as error:
        assert "normal_completion requires zero remaining card points" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_game_end_reason_for_points_accepts_claim_with_remaining_points() -> None:
    validate_game_end_reason_for_points(
        game_end_reason="declarer_claimed_remaining_tricks",
        points_remaining=10,
    )


def test_validate_game_end_reason_for_points_rejects_claim_without_remaining_points() -> None:
    try:
        validate_game_end_reason_for_points(
            game_end_reason="declarer_claimed_remaining_tricks",
            points_remaining=0,
        )
    except ValueError as error:
        assert "requires remaining card points" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_validate_game_end_reason_for_points_rejects_negative_points_remaining() -> None:
    try:
        validate_game_end_reason_for_points(
            game_end_reason="not_ended",
            points_remaining=-1,
        )
    except ValueError as error:
        assert "points_remaining cannot be negative" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")
    


def test_apply_remaining_points_assignment_rejects_invalid_game_end_points_combination() -> None:
    try:
        apply_remaining_points_assignment(
            game_result_summary={
                "declarer_points": 90,
                "defender_points": 30,
                "points_remaining": 0,
                "is_complete": True,
                "winner": "declarer",
                "status": "final_decided",
                "raw_schneider_status": "declarer_made_schneider",
                "raw_schwarz_status": "none",
                "effective_schneider_status": "declarer_made_schneider",
                "effective_schwarz_status": "none",
                "thresholds": {
                    "declarer_win": 61,
                    "defender_win": 60,
                    "schneider": 30,
                    "schwarz": 0,
                    "total_card_points": 120,
                },
            },
            game_end_reason="declarer_claimed_remaining_tricks",
        )
    except ValueError as error:
        assert "requires remaining card points" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")
