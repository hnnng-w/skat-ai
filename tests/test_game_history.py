from skat_ai.game_history import (
    build_score_summary,
    calculate_completed_trick_points_by_side,
    get_completed_trick_cards,
    get_completed_trick_points,
    get_completed_trick_winner_role,
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