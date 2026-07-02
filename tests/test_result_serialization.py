from skat_ai.game_history import build_score_summary
from skat_ai.game_state import GameState
from skat_ai.input_loader import build_game_state_from_input
from skat_ai.input_validation import validate_position_input
from skat_ai.result_serialization import (
    build_serializable_game_state,
    build_serializable_multi_step_result,
    build_serializable_multi_step_step,
    build_serializable_policy_comparison_result,
)
from skat_ai.simulation_step import simulate_and_advance_once


def test_build_serializable_game_state() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10"],
        current_trick=["S7"],
        played_cards=["C7"],
        skat=["D7"],
        player_position="middlehand",
        declarer_player="me",
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
        "declarer_player": "me",
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
        "prepared_state": GameState(
            game_type="grand",
            player_role="declarer",
            hand=["SA"],
            current_trick=["S7"],
            trick_leader="right",
            next_player="me",
        ),
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
        "prepared_state": {
            "game_type": "grand",
            "player_role": "declarer",
            "hand": ["SA"],
            "current_trick": ["S7"],
            "played_cards": [],
            "skat": [],
            "player_position": "unknown",
            "declarer_player": "unknown",
            "trick_leader": "right",
            "completed_tricks": [],
            "declarer_points": 0,
            "defender_points": 0,
            "next_player": "me",
        },
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
        "prepared_state": GameState(
            game_type="grand",
            player_role="declarer",
            hand=["SA"],
            current_trick=["D7", "D9"],
            trick_leader="left",
            next_player="me",
        ),
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
                "prepared_state": GameState(
                    game_type="grand",
                    player_role="declarer",
                    hand=["SA"],
                    current_trick=["S7"],
                    trick_leader="right",
                    next_player="me",
                ),
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
        "opponent_policy_settings": {
            "opponent_lead_policy": "highest_point",
            "opponent_response_policy": "basic_trick_play",
        },
        "left_opponent_policy_settings": {
            "opponent_lead_policy": "lowest_point",
            "opponent_response_policy": "lowest_point",
        },
        "right_opponent_policy_settings": {
            "opponent_lead_policy": "highest_point",
            "opponent_response_policy": "basic_defender_response",
        },
    }

    serializable_result = build_serializable_multi_step_result(result)

    assert serializable_result["card_selection_policy"] == "highest_point"
    assert serializable_result["steps_simulated"] == 1
    assert serializable_result["summary"]["score_summary"]["final_point_swing"] == 11
    assert serializable_result["final_state"]["hand"] == ["S10"]
    assert "next_state" not in serializable_result["steps"][0]
    assert serializable_result["steps"][0]["prepared_state"]["next_player"] == "me"
    assert serializable_result["opponent_policy_settings"] == {
        "opponent_lead_policy": "highest_point",
        "opponent_response_policy": "basic_trick_play",
    }
    assert serializable_result["left_opponent_policy_settings"] == {
        "opponent_lead_policy": "lowest_point",
        "opponent_response_policy": "lowest_point",
    }
    assert serializable_result["right_opponent_policy_settings"] == {
        "opponent_lead_policy": "highest_point",
        "opponent_response_policy": "basic_defender_response",
    }


def test_serialized_advanced_state_round_trips_without_inflated_points() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        declarer_player="me",
        hand=["CA"],
        current_trick=["C10", "CK"],
        trick_leader="left",
        next_player="me",
    )
    result = simulate_and_advance_once(
        state=state,
        candidate_card="CA",
        left_hand_size=0,
        right_hand_size=0,
    )
    final_state = result["next_state"]
    original_score_summary = build_score_summary(final_state)

    reconstructed_input = {
        **build_serializable_game_state(final_state),
        "left_hand_size": 1,
        "right_hand_size": 1,
        "sample_count": 1,
        "use_basic_opponent_strategy": True,
    }

    validate_position_input(reconstructed_input)
    rebuilt_state = build_game_state_from_input(reconstructed_input)
    rebuilt_score_summary = build_score_summary(rebuilt_state)

    assert original_score_summary["total_declarer_points"] == 25
    assert original_score_summary["explicit_declarer_points"] == 0
    assert rebuilt_score_summary == original_score_summary
    assert rebuilt_score_summary["total_declarer_points"] != 50


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
            "local_point_swing": 12,
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
                "local_point_swing": 12,
                "context_summary": {
                    "simulated_opponent_card_count": 2,
                    "unique_simulated_opponent_card_count": 2,
                    "duplicate_simulated_opponent_cards": [],
                    "event_count": 1,
                },
            },
        ],
        "opponent_lead_policy": "highest_point",
        "opponent_response_policy": "basic_trick_play",
    }

    serializable_result = build_serializable_policy_comparison_result(result)

    assert serializable_result == result
