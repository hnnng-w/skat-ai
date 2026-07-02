from skat_ai.game_state import GameState
from skat_ai.multi_step_summary import (
    build_multi_step_score_summary,
    build_multi_step_summary,
)


def test_build_multi_step_score_summary() -> None:
    initial_state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA"],
        current_trick=[],
        declarer_points=10,
        defender_points=5,
    )
    final_state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=[],
        current_trick=[],
        completed_tricks=[
            {
                "cards": ["SA", "S10", "SK"],
                "winner_role": "declarer",
            },
            {
                "cards": ["CA", "CQ", "C7"],
                "winner_role": "defenders",
            },
        ],
        declarer_points=10,
        defender_points=5,
    )

    summary = build_multi_step_score_summary(
        initial_state=initial_state,
        final_state=final_state,
    )

    assert summary == {
        "initial_declarer_points": 10,
        "initial_defender_points": 5,
        "final_declarer_points": 35,
        "final_defender_points": 19,
        "declarer_points_gained": 25,
        "defender_points_gained": 14,
        "final_point_swing": 11,
        "local_point_swing": 11,
    }


def test_build_multi_step_score_summary_uses_defender_local_point_swing() -> None:
    initial_state = GameState(
        game_type="grand",
        player_role="defender",
        declarer_player="left",
        hand=["SA"],
        current_trick=[],
        declarer_points=10,
        defender_points=5,
    )
    final_state = GameState(
        game_type="grand",
        player_role="defender",
        declarer_player="left",
        hand=[],
        current_trick=[],
        completed_tricks=[
            {
                "cards": ["SA", "S10", "SK"],
                "winner_role": "declarer",
            },
            {
                "cards": ["CA", "CQ", "C7"],
                "winner_role": "defenders",
            },
        ],
        declarer_points=10,
        defender_points=5,
    )

    summary = build_multi_step_score_summary(
        initial_state=initial_state,
        final_state=final_state,
    )

    assert summary["declarer_points_gained"] == 25
    assert summary["defender_points_gained"] == 14
    assert summary["final_point_swing"] == 11
    assert summary["local_point_swing"] == -11


def test_build_multi_step_summary() -> None:
    initial_state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA"],
        current_trick=[],
        declarer_points=0,
        defender_points=0,
    )
    final_state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=[],
        current_trick=[],
        completed_tricks=[
            {
                "cards": ["SA", "S7", "S8"],
                "winner_role": "declarer",
            },
            {
                "cards": ["CK", "C7", "C8"],
                "winner_role": "defenders",
            },
        ],
    )
    multi_step_result = {
        "initial_state": initial_state,
        "final_state": final_state,
        "requested_step_count": 2,
        "steps_simulated": 1,
        "stop_reason": "Requested step count reached.",
        "card_selection_policy": "highest_point",
        "strict_context": True,
        "context_summary": {
            "simulated_opponent_card_count": 2,
            "unique_simulated_opponent_card_count": 2,
            "duplicate_simulated_opponent_cards": [],
            "event_count": 1,
        },
    }

    summary = build_multi_step_summary(multi_step_result)

    assert summary["requested_step_count"] == 2
    assert summary["steps_simulated"] == 1
    assert summary["stop_reason"] == "Requested step count reached."
    assert summary["card_selection_policy"] == "highest_point"
    assert summary["strict_context"] is True
    assert summary["score_summary"]["final_point_swing"] == 7
    assert summary["score_summary"]["local_point_swing"] == 7
    assert summary["context_summary"]["event_count"] == 1
