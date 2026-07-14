from skat_ai.overbid import (
    build_overbid_summary,
    calculate_required_overbid_game_value,
)


def test_build_overbid_summary_without_bid_value() -> None:
    summary = build_overbid_summary(
        game_value_summary={"game_value": 72},
        bid_value=None,
    )

    assert summary == {
        "bid_value": None,
        "game_value": 72,
        "is_overbid": None,
        "margin": None,
        "required_game_value": None,
        "status": "unknown_bid_value",
    }


def test_build_overbid_summary_without_game_value() -> None:
    summary = build_overbid_summary(
        game_value_summary={"game_value": None},
        bid_value=72,
    )

    assert summary == {
        "bid_value": 72,
        "game_value": None,
        "is_overbid": None,
        "margin": None,
        "required_game_value": None,
        "status": "unknown_game_value",
    }


def test_build_overbid_summary_when_not_overbid_equal_value() -> None:
    summary = build_overbid_summary(
        game_value_summary={
            "game_value": 72,
            "base_value": 24,
            "is_null_game": False,
        },
        bid_value=72,
    )

    assert summary == {
        "bid_value": 72,
        "game_value": 72,
        "is_overbid": False,
        "margin": 0,
        "required_game_value": 72,
        "status": "not_overbid",
    }


def test_build_overbid_summary_when_not_overbid_lower_bid() -> None:
    summary = build_overbid_summary(
        game_value_summary={"game_value": 72},
        bid_value=60,
    )

    assert summary == {
        "bid_value": 60,
        "game_value": 72,
        "is_overbid": False,
        "margin": 12,
        "required_game_value": 72,
        "status": "not_overbid",
    }


def test_build_overbid_summary_when_overbid() -> None:
    summary = build_overbid_summary(
        game_value_summary={
            "game_value": 48,
            "base_value": 24,
            "is_null_game": False,
        },
        bid_value=60,
    )

    assert summary == {
        "bid_value": 60,
        "game_value": 48,
        "is_overbid": True,
        "margin": -12,
        "required_game_value": 72,
        "status": "overbid",
    }

def test_calculate_required_overbid_game_value_exact_match() -> None:
    assert calculate_required_overbid_game_value(
        bid_value=72,
        base_value=24,
    ) == 72


def test_calculate_required_overbid_game_value_rounds_up() -> None:
    assert calculate_required_overbid_game_value(
        bid_value=60,
        base_value=24,
    ) == 72


def test_calculate_required_overbid_game_value_rejects_invalid_bid_value() -> None:
    try:
        calculate_required_overbid_game_value(
            bid_value=0,
            base_value=24,
        )
    except ValueError as error:
        assert "bid_value must be a positive integer" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_calculate_required_overbid_game_value_rejects_invalid_base_value() -> None:
    try:
        calculate_required_overbid_game_value(
            bid_value=60,
            base_value=0,
        )
    except ValueError as error:
        assert "base_value must be a positive integer" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")

def test_build_overbid_summary_rounds_required_value_up_for_overbid() -> None:
    summary = build_overbid_summary(
        game_value_summary={
            "game_value": 72,
            "base_value": 24,
            "is_null_game": False,
        },
        bid_value=73,
    )

    assert summary == {
        "bid_value": 73,
        "game_value": 72,
        "is_overbid": True,
        "margin": -1,
        "required_game_value": 96,
        "status": "overbid",
    }

def test_build_overbid_summary_for_null_overbid_has_no_required_game_value() -> None:
    summary = build_overbid_summary(
        game_value_summary={
            "game_value": 23,
            "base_value": None,
            "is_null_game": True,
        },
        bid_value=24,
    )

    assert summary == {
        "bid_value": 24,
        "game_value": 23,
        "is_overbid": True,
        "margin": -1,
        "required_game_value": None,
        "status": "overbid",
    }

def test_build_overbid_summary_for_null_not_overbid() -> None:
    summary = build_overbid_summary(
        game_value_summary={
            "game_value": 23,
            "base_value": None,
            "is_null_game": True,
        },
        bid_value=23,
    )

    assert summary == {
        "bid_value": 23,
        "game_value": 23,
        "is_overbid": False,
        "margin": 0,
        "required_game_value": 23,
        "status": "not_overbid",
    }


def test_impossible_null_overbid_uses_separate_replacement_value() -> None:
    replacement_summary = {
        "replacement_game_type": "clubs",
        "matadors": 1,
        "hand_game": False,
        "base_value": 12,
        "minimum_game_value": 24,
        "required_game_value": 36,
    }

    summary = build_overbid_summary(
        game_value_summary={
            "game_value": 23,
            "base_value": None,
            "is_null_game": True,
        },
        bid_value=25,
        game_end_reason="impossible_null_declaration",
        impossible_null_settlement=replacement_summary,
    )

    assert summary["game_value"] == 23
    assert summary["required_game_value"] == 36
    assert summary["impossible_null_settlement"] == replacement_summary


def test_impossible_null_overbid_keeps_missing_replacement_explicit() -> None:
    summary = build_overbid_summary(
        game_value_summary={
            "game_value": 23,
            "base_value": None,
            "is_null_game": True,
        },
        bid_value=24,
        game_end_reason="impossible_null_declaration",
    )

    assert summary["required_game_value"] is None
    assert summary["impossible_null_settlement"] is None
