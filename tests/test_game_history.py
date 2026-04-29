from skat_ai.game_history import (
    build_completed_trick_from_cards,
    build_completed_trick_from_state_and_candidate,
    build_score_summary,
    calculate_completed_trick_points_by_side,
    get_all_played_cards,
    get_completed_trick_cards,
    get_completed_trick_points,
    get_completed_trick_winner_role,
    get_played_cards_from_completed_tricks,
    get_winner_role_for_trick_winner,
)
from skat_ai.game_state import GameState


def test_get_completed_trick_cards() -> None:
    completed_trick = {
        "cards": ["CA", "C10", "CK"],
        "winner_role": "declarer",
    }

    assert get_completed_trick_cards(completed_trick) == ["CA", "C10", "CK"]


def test_get_completed_trick_winner_role() -> None:
    completed_trick = {
        "cards": ["CA", "C10", "CK"],
        "winner_role": "declarer",
    }

    assert get_completed_trick_winner_role(completed_trick) == "declarer"


def test_get_completed_trick_points() -> None:
    completed_trick = {
        "cards": ["CA", "C10", "CK"],
        "winner_role": "declarer",
    }

    assert get_completed_trick_points(completed_trick) == 25


def test_calculate_completed_trick_points_by_side() -> None:
    completed_tricks = [
        {
            "cards": ["CA", "C10", "CK"],
            "winner_role": "declarer",
        },
        {
            "cards": ["SA", "S10", "SK"],
            "winner_role": "defenders",
        },
    ]

    points = calculate_completed_trick_points_by_side(completed_tricks)

    assert points["declarer_points"] == 25
    assert points["defender_points"] == 25


def test_build_score_summary() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S9"],
        current_trick=[],
        completed_tricks=[
            {
                "cards": ["CA", "C10", "CK"],
                "winner_role": "declarer",
            }
        ],
        declarer_points=10,
        defender_points=5,
    )

    summary = build_score_summary(state)

    assert summary["explicit_declarer_points"] == 10
    assert summary["explicit_defender_points"] == 5
    assert summary["completed_trick_declarer_points"] == 25
    assert summary["completed_trick_defender_points"] == 0
    assert summary["total_declarer_points"] == 35
    assert summary["total_defender_points"] == 5


def test_get_played_cards_from_completed_tricks() -> None:
    completed_tricks = [
        {
            "cards": ["CA", "C10", "CK"],
            "winner_role": "declarer",
        },
        {
            "cards": ["SA", "S10", "SK"],
            "winner_role": "defenders",
        },
    ]

    played_cards = get_played_cards_from_completed_tricks(completed_tricks)

    assert played_cards == ["CA", "C10", "CK", "SA", "S10", "SK"]


def test_get_all_played_cards_combines_legacy_played_cards_and_completed_tricks() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["H7"],
        current_trick=[],
        played_cards=["D7"],
        completed_tricks=[
            {
                "cards": ["CA", "C10", "CK"],
                "winner_role": "declarer",
            }
        ],
    )

    played_cards = get_all_played_cards(state)

    assert played_cards == ["D7", "CA", "C10", "CK"]


def test_get_winner_role_for_trick_winner_when_declarer_wins_own_card() -> None:
    winner_role = get_winner_role_for_trick_winner(
        winner_index=1,
        player_index=1,
        player_role="declarer",
    )

    assert winner_role == "declarer"


def test_get_winner_role_for_trick_winner_when_declarer_loses() -> None:
    winner_role = get_winner_role_for_trick_winner(
        winner_index=0,
        player_index=1,
        player_role="declarer",
    )

    assert winner_role == "defenders"


def test_get_winner_role_for_trick_winner_when_defender_wins_own_card() -> None:
    winner_role = get_winner_role_for_trick_winner(
        winner_index=2,
        player_index=2,
        player_role="defender",
    )

    assert winner_role == "defenders"


def test_get_winner_role_for_trick_winner_when_defender_loses_to_declarer() -> None:
    winner_role = get_winner_role_for_trick_winner(
        winner_index=0,
        player_index=2,
        player_role="defender",
    )

    assert winner_role == "declarer"


def test_get_winner_role_for_trick_winner_rejects_unknown_player_role() -> None:
    try:
        get_winner_role_for_trick_winner(
            winner_index=0,
            player_index=0,
            player_role="unknown",
        )
    except ValueError as error:
        assert "Unsupported player role" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_build_completed_trick_from_cards_for_declarer_win() -> None:
    completed_trick = build_completed_trick_from_cards(
        cards=["S7", "SA", "S8"],
        game_type="grand",
        player_index=1,
        player_role="declarer",
    )

    assert completed_trick == {
        "cards": ["S7", "SA", "S8"],
        "winner_role": "declarer",
    }


def test_build_completed_trick_from_cards_for_declarer_loss() -> None:
    completed_trick = build_completed_trick_from_cards(
        cards=["S7", "S9", "SA"],
        game_type="grand",
        player_index=1,
        player_role="declarer",
    )

    assert completed_trick == {
        "cards": ["S7", "S9", "SA"],
        "winner_role": "defenders",
    }


def test_build_completed_trick_from_cards_requires_three_cards() -> None:
    try:
        build_completed_trick_from_cards(
            cards=["S7", "SA"],
            game_type="grand",
            player_index=1,
            player_role="declarer",
        )
    except ValueError as error:
        assert "exactly 3 cards" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_build_completed_trick_from_cards_requires_valid_player_index() -> None:
    try:
        build_completed_trick_from_cards(
            cards=["S7", "SA", "S8"],
            game_type="grand",
            player_index=3,
            player_role="declarer",
        )
    except ValueError as error:
        assert "player_index" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_build_completed_trick_from_state_and_candidate_second_position() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S9"],
        current_trick=["S7"],
    )

    completed_trick = build_completed_trick_from_state_and_candidate(
        state=state,
        completed_trick_cards=["S7", "SA", "S8"],
    )

    assert completed_trick == {
        "cards": ["S7", "SA", "S8"],
        "winner_role": "declarer",
    }


def test_build_completed_trick_from_state_and_candidate_third_position() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S9"],
        current_trick=["S7", "S8"],
    )

    completed_trick = build_completed_trick_from_state_and_candidate(
        state=state,
        completed_trick_cards=["S7", "S8", "SA"],
    )

    assert completed_trick == {
        "cards": ["S7", "S8", "SA"],
        "winner_role": "declarer",
    }