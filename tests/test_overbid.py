from skat_ai.overbid import build_overbid_summary


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
        "status": "unknown_game_value",
    }


def test_build_overbid_summary_when_not_overbid_equal_value() -> None:
    summary = build_overbid_summary(
        game_value_summary={"game_value": 72},
        bid_value=72,
    )

    assert summary == {
        "bid_value": 72,
        "game_value": 72,
        "is_overbid": False,
        "margin": 0,
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
        "status": "not_overbid",
    }


def test_build_overbid_summary_when_overbid() -> None:
    summary = build_overbid_summary(
        game_value_summary={"game_value": 48},
        bid_value=60,
    )

    assert summary == {
        "bid_value": 60,
        "game_value": 48,
        "is_overbid": True,
        "margin": -12,
        "status": "overbid",
    }