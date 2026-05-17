from skat_ai.final_settlement import (
    build_final_settlement_summary,
    get_missing_final_settlement_inputs,
    is_declarer_winner_by_card_points,
)


def test_get_missing_final_settlement_inputs_returns_none_when_complete() -> None:
    game_value_summary = {
        "game_value": 72,
    }
    game_result_summary = {
        "is_complete": True,
    }

    assert get_missing_final_settlement_inputs(
        game_value_summary=game_value_summary,
        game_result_summary=game_result_summary,
    ) == []


def test_get_missing_final_settlement_inputs_detects_incomplete_card_points() -> None:
    game_value_summary = {
        "game_value": 72,
    }
    game_result_summary = {
        "is_complete": False,
    }

    assert get_missing_final_settlement_inputs(
        game_value_summary=game_value_summary,
        game_result_summary=game_result_summary,
    ) == ["complete_card_points"]


def test_get_missing_final_settlement_inputs_detects_missing_game_value() -> None:
    game_value_summary = {
        "game_value": None,
    }
    game_result_summary = {
        "is_complete": True,
    }

    assert get_missing_final_settlement_inputs(
        game_value_summary=game_value_summary,
        game_result_summary=game_result_summary,
    ) == ["game_value"]


def test_get_missing_final_settlement_inputs_detects_multiple_missing_inputs() -> None:
    game_value_summary = {
        "game_value": None,
    }
    game_result_summary = {
        "is_complete": False,
    }

    assert get_missing_final_settlement_inputs(
        game_value_summary=game_value_summary,
        game_result_summary=game_result_summary,
    ) == ["complete_card_points", "game_value"]


def test_is_declarer_winner_by_card_points_returns_none_when_incomplete() -> None:
    game_result_summary = {
        "is_complete": False,
        "winner": "undecided",
    }

    assert is_declarer_winner_by_card_points(game_result_summary) is None


def test_is_declarer_winner_by_card_points_returns_true() -> None:
    game_result_summary = {
        "is_complete": True,
        "winner": "declarer",
    }

    assert is_declarer_winner_by_card_points(game_result_summary) is True


def test_is_declarer_winner_by_card_points_returns_false() -> None:
    game_result_summary = {
        "is_complete": True,
        "winner": "defenders",
    }

    assert is_declarer_winner_by_card_points(game_result_summary) is False


def test_build_final_settlement_summary_incomplete() -> None:
    game_value_summary = {
        "game_value": None,
    }
    game_result_summary = {
        "is_complete": False,
        "winner": "undecided",
    }

    summary = build_final_settlement_summary(
        game_value_summary=game_value_summary,
        game_result_summary=game_result_summary,
    )

    assert summary["is_complete"] is False
    assert summary["missing_inputs"] == ["complete_card_points", "game_value"]
    assert summary["declarer_won_by_card_points"] is None
    assert summary["winner"] is None
    assert summary["game_value"] is None
    assert summary["settlement_score"] is None
    assert summary["is_loss"] is None
    assert summary["is_overbid"] is None


def test_build_final_settlement_summary_complete_declarer_win() -> None:
    game_value_summary = {
        "game_value": 72,
    }
    game_result_summary = {
        "is_complete": True,
        "winner": "declarer",
    }

    summary = build_final_settlement_summary(
        game_value_summary=game_value_summary,
        game_result_summary=game_result_summary,
    )

    assert summary["is_complete"] is True
    assert summary["missing_inputs"] == []
    assert summary["declarer_won_by_card_points"] is True
    assert summary["winner"] == "declarer"
    assert summary["game_value"] == 72
    assert summary["settlement_score"] is None
    assert summary["is_loss"] is False
    assert summary["is_overbid"] is None


def test_build_final_settlement_summary_complete_declarer_loss() -> None:
    game_value_summary = {
        "game_value": 72,
    }
    game_result_summary = {
        "is_complete": True,
        "winner": "defenders",
    }

    summary = build_final_settlement_summary(
        game_value_summary=game_value_summary,
        game_result_summary=game_result_summary,
    )

    assert summary["is_complete"] is True
    assert summary["missing_inputs"] == []
    assert summary["declarer_won_by_card_points"] is False
    assert summary["winner"] == "defenders"
    assert summary["game_value"] == 72
    assert summary["settlement_score"] is None
    assert summary["is_loss"] is True
    assert summary["is_overbid"] is None