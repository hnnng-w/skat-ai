import random

from skat_ai.game_state import GameState
from skat_ai.opponent_sequence import (
    build_serializable_opponent_sequence_result,
    can_prepare_player_action,
    extract_opponent_sequence_cards,
    get_unsupported_next_player_reason,
    get_unsupported_turn_phase_reason,
    prepare_player_action_state,
)


def test_can_prepare_player_action_supports_local_action_phases() -> None:
    assert can_prepare_player_action(
        GameState(
            game_type="grand",
            player_role="declarer",
            hand=["SA"],
            current_trick=[],
            trick_leader="me",
            next_player="me",
        )
    ) is True
    assert can_prepare_player_action(
        GameState(
            game_type="grand",
            player_role="declarer",
            hand=["SA"],
            current_trick=["S7"],
            trick_leader="right",
            next_player="me",
        )
    ) is True
    assert can_prepare_player_action(
        GameState(
            game_type="grand",
            player_role="declarer",
            hand=["SA"],
            current_trick=["S7", "S8"],
            trick_leader="left",
            next_player="me",
        )
    ) is True


def test_can_prepare_player_action_supports_opponent_preparation_phases() -> None:
    assert can_prepare_player_action(
        GameState(
            game_type="grand",
            player_role="declarer",
            hand=["SA"],
            current_trick=[],
            trick_leader="left",
            next_player="left",
        )
    ) is True
    assert can_prepare_player_action(
        GameState(
            game_type="grand",
            player_role="declarer",
            hand=["SA"],
            current_trick=[],
            trick_leader="right",
            next_player="right",
        )
    ) is True
    assert can_prepare_player_action(
        GameState(
            game_type="grand",
            player_role="declarer",
            hand=["SA"],
            current_trick=["S7"],
            trick_leader="left",
            next_player="right",
        )
    ) is True


def test_can_prepare_player_action_rejects_unsupported_valid_phases() -> None:
    unsupported_states = [
        GameState(
            game_type="grand",
            player_role="declarer",
            hand=["SA"],
            current_trick=["S7"],
            trick_leader="me",
            next_player="left",
        ),
        GameState(
            game_type="grand",
            player_role="declarer",
            hand=["SA"],
            current_trick=["S7", "S8"],
            trick_leader="me",
            next_player="right",
        ),
        GameState(
            game_type="grand",
            player_role="declarer",
            hand=["SA"],
            current_trick=["S7", "S8"],
            trick_leader="right",
            next_player="left",
        ),
    ]

    for state in unsupported_states:
        assert can_prepare_player_action(state) is False


def test_get_unsupported_next_player_reason() -> None:
    reason = get_unsupported_next_player_reason("dealer")

    assert reason == "Next player is dealer, not supported."


def test_prepare_player_action_state_returns_state_when_next_player_is_me() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA"],
        current_trick=[],
        next_player="me",
    )

    prepared_state, opponent_sequence_result = prepare_player_action_state(
        current_state=state,
        left_hand_size=5,
        right_hand_size=5,
        random_generator=random.Random(42),
    )

    assert prepared_state == state
    assert opponent_sequence_result is None


def test_prepare_player_action_state_rejects_unknown_phase() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA"],
        current_trick=[],
        next_player="unknown",
    )

    try:
        prepare_player_action_state(
            current_state=state,
            left_hand_size=5,
            right_hand_size=5,
            random_generator=random.Random(42),
        )
    except ValueError as error:
        assert str(error) == get_unsupported_turn_phase_reason()
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_prepare_player_action_state_simulates_right_lead() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10"],
        current_trick=[],
        trick_leader="right",
        next_player="right",
    )

    prepared_state, opponent_sequence_result = prepare_player_action_state(
        current_state=state,
        left_hand_size=5,
        right_hand_size=5,
        random_generator=random.Random(42),
    )

    assert opponent_sequence_result is not None
    assert opponent_sequence_result["leader"] == "right"
    assert prepared_state.trick_leader == "right"
    assert prepared_state.next_player == "me"
    assert len(prepared_state.current_trick) == 1


def test_prepare_player_action_state_simulates_left_lead_and_right_response() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10"],
        current_trick=[],
        trick_leader="left",
        next_player="left",
    )

    prepared_state, opponent_sequence_result = prepare_player_action_state(
        current_state=state,
        left_hand_size=5,
        right_hand_size=5,
        random_generator=random.Random(42),
    )

    assert opponent_sequence_result is not None
    assert opponent_sequence_result["leader"] == "left"
    assert opponent_sequence_result["responder"] == "right"
    assert prepared_state.trick_leader == "left"
    assert prepared_state.next_player == "me"
    assert len(prepared_state.current_trick) == 2


def test_prepare_player_action_state_does_not_overwrite_non_empty_trick() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10"],
        current_trick=["D7"],
        trick_leader="me",
        next_player="left",
    )

    try:
        prepare_player_action_state(
            current_state=state,
            left_hand_size=5,
            right_hand_size=5,
            random_generator=random.Random(42),
        )
    except ValueError as error:
        assert str(error) == get_unsupported_turn_phase_reason()
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_prepare_player_action_state_rejects_unsupported_next_player() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA"],
        current_trick=[],
        next_player="dealer",
    )

    try:
        prepare_player_action_state(
            current_state=state,
            left_hand_size=5,
            right_hand_size=5,
            random_generator=random.Random(42),
        )
    except ValueError as error:
        assert "Invalid next_player" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_build_serializable_opponent_sequence_result_returns_none() -> None:
    result = build_serializable_opponent_sequence_result(None)

    assert result is None


def test_build_serializable_opponent_sequence_result_for_right_lead() -> None:
    result = build_serializable_opponent_sequence_result(
        {
            "leader": "right",
            "lead_card": "D7",
            "next_state": "ignored",
        }
    )

    assert result == {
        "leader": "right",
        "lead_card": "D7",
        "responder": None,
        "response_card": None,
    }


def test_build_serializable_opponent_sequence_result_for_left_lead_and_response() -> None:
    result = build_serializable_opponent_sequence_result(
        {
            "leader": "left",
            "lead_card": "D7",
            "responder": "right",
            "response_card": "D9",
            "next_state": "ignored",
        }
    )

    assert result == {
        "leader": "left",
        "lead_card": "D7",
        "responder": "right",
        "response_card": "D9",
    }


def test_extract_opponent_sequence_cards_returns_empty_list_without_sequence() -> None:
    cards = extract_opponent_sequence_cards(None)

    assert cards == []


def test_extract_opponent_sequence_cards_for_right_lead() -> None:
    cards = extract_opponent_sequence_cards(
        {
            "leader": "right",
            "lead_card": "D7",
        }
    )

    assert cards == ["D7"]


def test_extract_opponent_sequence_cards_for_left_lead_and_response() -> None:
    cards = extract_opponent_sequence_cards(
        {
            "leader": "left",
            "lead_card": "D7",
            "responder": "right",
            "response_card": "D9",
        }
    )

    assert cards == ["D7", "D9"]

def test_prepare_player_action_state_supports_opponent_policies() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10"],
        current_trick=[],
        next_player="left",
    )

    prepared_state, opponent_sequence_result = prepare_player_action_state(
        current_state=state,
        left_hand_size=5,
        right_hand_size=5,
        random_generator=random.Random(42),
        opponent_lead_policy="highest_point",
        opponent_response_policy="basic_trick_play",
    )

    assert opponent_sequence_result is not None
    assert opponent_sequence_result["leader"] == "left"
    assert opponent_sequence_result["responder"] == "right"
    assert prepared_state.next_player == "me"

def test_prepare_player_action_state_uses_right_lead_policy() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["S7", "S8", "S9"],
        current_trick=[],
        completed_tricks=[],
        declarer_points=0,
        defender_points=0,
        next_player="right",
    )

    _, opponent_sequence_result = prepare_player_action_state(
        current_state=state,
        left_hand_size=3,
        right_hand_size=3,
        random_generator=random.Random(42),
        opponent_lead_policy="lowest_point",
        opponent_response_policy="lowest_point",
        right_opponent_policy_settings={
            "opponent_lead_policy": "highest_point",
            "opponent_response_policy": "lowest_point",
        },
    )

    assert opponent_sequence_result is not None
    assert opponent_sequence_result["leader"] == "right"
    assert opponent_sequence_result["lead_card"] is not None

def test_prepare_player_action_state_uses_right_response_policy() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["H7", "H8", "H9"],
        current_trick=[],
        completed_tricks=[],
        declarer_points=0,
        defender_points=0,
        next_player="left",
    )

    _, opponent_sequence_result = prepare_player_action_state(
        current_state=state,
        left_hand_size=3,
        right_hand_size=3,
        random_generator=random.Random(42),
        opponent_lead_policy="lowest_point",
        opponent_response_policy="lowest_point",
        left_opponent_policy_settings={
            "opponent_lead_policy": "lowest_point",
            "opponent_response_policy": "lowest_point",
        },
        right_opponent_policy_settings={
            "opponent_lead_policy": "lowest_point",
            "opponent_response_policy": "highest_point",
        },
    )

    assert opponent_sequence_result is not None
    assert opponent_sequence_result["leader"] == "left"
    assert opponent_sequence_result["responder"] == "right"
    assert opponent_sequence_result["response_card"] is not None
