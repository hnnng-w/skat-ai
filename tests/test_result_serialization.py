from skat_ai.game_state import GameState
from skat_ai.result_serialization import (
    build_serializable_game_state,
    build_serializable_multi_step_result,
    build_serializable_multi_step_step,
    build_serializable_policy_comparison_result,
)


def test_build_serializable_game_state() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10"],
        current_trick=["S7"],
        played_cards=["C7"],
        skat=["D7"],
        player_position="middlehand",
        trick_leader="left",
        completed_tricks=[
            {
                "cards": ["CA", "C10", "CK"],
                "winner_role": "defenders",
            }
        ],
        declarer_points=10,
        defender_points=25,
        next_player="me",
    )

    result = build_serializable_game_state(state)

    assert result == {
        "game_type": "grand",
        "player_role": "declarer",
        "hand": ["SA", "S10"],
        "current_trick": ["S7"],
        "played_cards": ["C7"],
        "skat": ["D7"],
        "player_position": "middlehand",
        "trick_leader": "left",
        "completed_tricks": [
            {
                "cards": ["CA", "C10", "CK"],
                "winner_role": "defenders",
            }
        ],
        "declarer_points": 10,
        "defender_points": 25,
        "next_player": "me",
    }


def test_build_serializable_multi_step_step_without_opponent_sequence() -> None:
    step = {
        "step_index": 0,
        "opponent_lead_result": None,
        "candidate_card": "SA",
        "card_selection_policy": "highest_point",
        "detailed_result": {
            "trick": ["S7", "SA", "S8"],
            "did_win": True,
            "trick_points": 11,
            "completed_trick": {
                "cards": ["S7", "SA", "S8"],
                "winner_role": "declarer",
            },
        },
        "next_state": GameState(
            game_type="grand",
            player_role="declarer",
            hand=["S10"],
            current_trick=[],
        ),
    }

    result = build_serializable_multi_step_step(step)

    assert result == {
        "step_index": 0,
        "opponent_lead_result": None,
        "candidate_card": "SA",
        "card_selection_policy": "highest_point",
        "detailed_result": {
            "trick": ["S7", "SA", "S8"],
            "did_win": True,
            "trick_points": 11,
            "completed_trick": {
                "cards": ["S7", "SA", "S8"],
                "winner_role": "declarer",
            },
        },
    }


def test_build_serializable_multi_step_step_with_opponent_sequence() -> None:
    step = {
        "step_index": 0,
        "opponent_lead_result": {
            "leader": "left",
            "lead_card": "D7",
            "responder": "right",
            "response_card": "D9",
            "next_state": GameState(
                game_type="grand",
                player_role="declarer",
                hand=["SA"],
                current_trick=["D7", "D9"],
            ),
        },
        "candidate_card": "DA",
        "card_selection_policy": "highest_point",
        "detailed_result": {
            "trick": ["D7", "D9", "DA"],
            "did_win": True,
            "trick_points": 11,
            "completed_trick": {
                "cards": ["D7", "D9", "DA"],
                "winner_role": "declarer",
            },
        },
        "next_state": GameState(
            game_type="grand",
            player_role="declarer",
            hand=[],
            current_trick=[],
        ),
    }

    result = build_serializable_multi_step_step(step)

    assert result["opponent_lead_result"] == {
        "leader": "left",
        "lead_card": "D7",
        "responder": "right",
        "response_card": "D9",
    }
    assert result["candidate_card"] == "DA"
    assert "next_state" not in result


def test_build_serializable_multi_step_result() -> None:
    final_state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["S10"],
        current_trick=[],
        declarer_points=11,
        defender_points=0,
        next_player="me",
    )
    result = {
        "card_selection_policy": "highest_point",
        "requested_step_count": 1,
        "steps_simulated": 1,
        "stop_reason": "Requested step count reached.",
        "strict_context": False,
        "summary": {
            "score_summary": {
                "final_point_swing": 11,
            }
        },
        "context_summary": {
            "simulated_opponent_card_count": 2,
            "unique_simulated_opponent_card_count": 2,
            "duplicate_simulated_opponent_cards": [],
            "event_count": 1,
        },
        "steps": [
            {
                "step_index": 0,
                "opponent_lead_result": None,
                "candidate_card": "SA",
                "card_selection_policy": "highest_point",
                "detailed_result": {
                    "trick": ["S7", "SA", "S8"],
                    "did_win": True,
                    "trick_points": 11,
                    "completed_trick": {
                        "cards": ["S7", "SA", "S8"],
                        "winner_role": "declarer",
                    },
                },
                "next_state": final_state,
            }
        ],
        "final_state": final_state,
    }

    serializable_result = build_serializable_multi_step_result(result)

    assert serializable_result["card_selection_policy"] == "highest_point"
    assert serializable_result["steps_simulated"] == 1
    assert serializable_result["summary"]["score_summary"]["final_point_swing"] == 11
    assert serializable_result["final_state"]["hand"] == ["S10"]
    assert "next_state" not in serializable_result["steps"][0]


def test_build_serializable_policy_comparison_result() -> None:
    result = {
        "requested_step_count": 2,
        "random_seed": 42,
        "expected_value_sample_count": 20,
        "use_basic_opponent_strategy": True,
        "strict_context": False,
        "policies": ["lowest_point", "highest_point"],
        "recommended_policy": {
            "policy": "highest_point",
            "reason": "Best final point swing after tie-breakers.",
            "final_point_swing": 12,
            "declarer_points_gained": 14,
            "defender_points_gained": 2,
            "steps_simulated": 1,
            "stop_reason": "Requested step count reached.",
        },
        "policy_results": [
            {
                "policy": "highest_point",
                "requested_step_count": 2,
                "steps_simulated": 1,
                "stop_reason": "Requested step count reached.",
                "strict_context": False,
                "declarer_points_gained": 14,
                "defender_points_gained": 2,
                "final_point_swing": 12,
                "context_summary": {
                    "simulated_opponent_card_count": 2,
                    "unique_simulated_opponent_card_count": 2,
                    "duplicate_simulated_opponent_cards": [],
                    "event_count": 1,
                },
            },
        ],
    }

    serializable_result = build_serializable_policy_comparison_result(result)

    assert serializable_result == result