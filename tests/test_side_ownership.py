from skat_ai.side_ownership import (
    did_local_side_win,
    get_defender_partner,
    get_player_side,
    get_winner_role,
    normalize_declarer_player,
)


def test_normalize_declarer_player_for_local_declarer() -> None:
    assert normalize_declarer_player("declarer", None) == "me"
    assert normalize_declarer_player("declarer", "me") == "me"


def test_normalize_declarer_player_rejects_unresolved_local_declarer() -> None:
    try:
        normalize_declarer_player("declarer", "unknown")
    except ValueError as error:
        assert "requires declarer_player to be 'me'" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_normalize_declarer_player_for_local_defender() -> None:
    assert normalize_declarer_player("defender", "left") == "left"
    assert normalize_declarer_player("defender", "right") == "right"


def test_normalize_declarer_player_rejects_unresolved_local_defender() -> None:
    try:
        normalize_declarer_player("defender", None)
    except ValueError as error:
        assert "requires declarer_player to be 'left' or 'right'" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_normalize_declarer_player_for_unknown_role() -> None:
    assert normalize_declarer_player("unknown", None) == "unknown"
    assert normalize_declarer_player("unknown", "unknown") == "unknown"


def test_normalize_declarer_player_rejects_concrete_unknown_role() -> None:
    try:
        normalize_declarer_player("unknown", "left")
    except ValueError as error:
        assert "requires declarer_player to be missing or 'unknown'" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_get_player_side_for_local_declarer() -> None:
    assert get_player_side("me", "me") == "declarer"
    assert get_player_side("left", "me") == "defenders"
    assert get_player_side("right", "me") == "defenders"


def test_get_player_side_for_declarer_left() -> None:
    assert get_player_side("left", "left") == "declarer"
    assert get_player_side("me", "left") == "defenders"
    assert get_player_side("right", "left") == "defenders"


def test_get_player_side_for_declarer_right() -> None:
    assert get_player_side("right", "right") == "declarer"
    assert get_player_side("me", "right") == "defenders"
    assert get_player_side("left", "right") == "defenders"


def test_get_defender_partner() -> None:
    assert get_defender_partner("left") == "right"
    assert get_defender_partner("right") == "left"
    assert get_defender_partner("me") is None
    assert get_defender_partner("unknown") is None


def test_get_winner_role() -> None:
    assert get_winner_role("right", "left") == "defenders"
    assert get_winner_role("left", "right") == "defenders"
    assert get_winner_role("right", "right") == "declarer"


def test_did_local_side_win() -> None:
    assert did_local_side_win("right", "defender", "left") is True
    assert did_local_side_win("left", "defender", "left") is False
    assert did_local_side_win("me", "declarer", "me") is True


def test_unresolved_direct_call_returns_none() -> None:
    assert get_player_side("left", "unknown") is None
    assert get_winner_role("left", "unknown") is None
    assert did_local_side_win("left", "defender", "unknown") is None
