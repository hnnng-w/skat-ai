import random

from skat_ai.game_state import GameState
from skat_ai.opponent_lead import (
    build_state_after_opponent_lead,
    build_state_after_opponent_second_hand_play,
    choose_lowest_point_lead_card,
    choose_lowest_point_legal_response_card,
    get_next_player_after_opponent_lead,
    simulate_left_lead_and_right_response_once,
    simulate_opponent_lead_once,
)


def test_choose_lowest_point_lead_card_returns_lowest_point_card() -> None:
    hand = ["SA", "S10", "S9"]

    selected_card = choose_lowest_point_lead_card(hand)

    assert selected_card == "S9"


def test_choose_lowest_point_lead_card_rejects_empty_hand() -> None:
    try:
        choose_lowest_point_lead_card([])
    except ValueError as error:
        assert "Opponent hand is empty" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_choose_lowest_point_legal_response_card_respects_follow_suit() -> None:
    hand = ["SA", "S9", "H10"]

    selected_card = choose_lowest_point_legal_response_card(
        hand=hand,
        current_trick=["S7"],
        game_type="grand",
    )

    assert selected_card == "S9"


def test_choose_lowest_point_legal_response_card_rejects_empty_legal_cards() -> None:
    try:
        choose_lowest_point_legal_response_card(
            hand=[],
            current_trick=["S7"],
            game_type="grand",
        )
    except ValueError as error:
        assert "Opponent has no legal response cards" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_get_next_player_after_left_lead() -> None:
    assert get_next_player_after_opponent_lead("left") == "right"


def test_get_next_player_after_right_lead() -> None:
    assert get_next_player_after_opponent_lead("right") == "me"


def test_get_next_player_after_opponent_lead_rejects_invalid_leader() -> None:
    try:
        get_next_player_after_opponent_lead("me")
    except ValueError as error:
        assert "Invalid opponent leader" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_build_state_after_left_opponent_lead() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10"],
        current_trick=[],
        next_player="left",
    )

    next_state = build_state_after_opponent_lead(
        state=state,
        lead_card="D7",
        leader="left",
    )

    assert next_state.current_trick == ["D7"]
    assert next_state.trick_leader == "left"
    assert next_state.next_player == "right"
    assert next_state.hand == ["SA", "S10"]


def test_build_state_after_right_opponent_lead() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10"],
        current_trick=[],
        next_player="right",
    )

    next_state = build_state_after_opponent_lead(
        state=state,
        lead_card="D7",
        leader="right",
    )

    assert next_state.current_trick == ["D7"]
    assert next_state.trick_leader == "right"
    assert next_state.next_player == "me"


def test_build_state_after_opponent_lead_preserves_declarer_player() -> None:
    state = GameState(
        game_type="grand",
        player_role="defender",
        declarer_player="right",
        hand=["SA", "S10"],
        current_trick=[],
        next_player="left",
    )

    next_state = build_state_after_opponent_lead(
        state=state,
        lead_card="D7",
        leader="left",
    )

    assert next_state.declarer_player == "right"


def test_build_state_after_opponent_second_hand_play() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10"],
        current_trick=["D7"],
        trick_leader="left",
        next_player="right",
    )

    next_state = build_state_after_opponent_second_hand_play(
        state=state,
        response_card="D9",
        responder="right",
    )

    assert next_state.current_trick == ["D7", "D9"]
    assert next_state.trick_leader == "left"
    assert next_state.next_player == "me"


def test_build_state_after_opponent_second_hand_play_preserves_declarer_player() -> None:
    state = GameState(
        game_type="grand",
        player_role="defender",
        declarer_player="left",
        hand=["SA", "S10"],
        current_trick=["D7"],
        trick_leader="left",
        next_player="right",
    )

    next_state = build_state_after_opponent_second_hand_play(
        state=state,
        response_card="D9",
        responder="right",
    )

    assert next_state.declarer_player == "left"


def test_build_state_after_opponent_second_hand_play_rejects_invalid_responder() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10"],
        current_trick=["D7"],
        trick_leader="left",
        next_player="right",
    )

    try:
        build_state_after_opponent_second_hand_play(
            state=state,
            response_card="D9",
            responder="me",
        )
    except ValueError as error:
        assert "Invalid opponent responder" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_build_state_after_opponent_second_hand_play_requires_one_current_card() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10"],
        current_trick=[],
        trick_leader="left",
        next_player="right",
    )

    try:
        build_state_after_opponent_second_hand_play(
            state=state,
            response_card="D9",
            responder="right",
        )
    except ValueError as error:
        assert "exactly one card" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_build_state_after_opponent_lead_does_not_mutate_original_state() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10"],
        current_trick=[],
        next_player="left",
    )

    next_state = build_state_after_opponent_lead(
        state=state,
        lead_card="D7",
        leader="left",
    )

    assert state.current_trick == []
    assert state.next_player == "left"
    assert next_state.current_trick == ["D7"]
    assert next_state.next_player == "right"


def test_simulate_opponent_lead_once_requires_opponent_next_player() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10"],
        current_trick=[],
        next_player="me",
    )

    try:
        simulate_opponent_lead_once(
            state=state,
            left_hand_size=5,
            right_hand_size=5,
            random_generator=random.Random(42),
        )
    except ValueError as error:
        assert "next_player to be left or right" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_simulate_opponent_lead_once_for_left_returns_expected_keys() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10"],
        current_trick=[],
        next_player="left",
    )

    result = simulate_opponent_lead_once(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        random_generator=random.Random(42),
    )

    assert set(result.keys()) == {
        "leader",
        "lead_card",
        "next_state",
    }


def test_simulate_opponent_lead_once_for_left_starts_new_trick() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10"],
        current_trick=[],
        next_player="left",
    )

    result = simulate_opponent_lead_once(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        random_generator=random.Random(42),
    )

    next_state = result["next_state"]

    assert result["leader"] == "left"
    assert isinstance(result["lead_card"], str)
    assert isinstance(next_state, GameState)
    assert next_state.current_trick == [result["lead_card"]]
    assert next_state.trick_leader == "left"
    assert next_state.next_player == "right"


def test_simulate_opponent_lead_once_for_right_starts_new_trick() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10"],
        current_trick=[],
        next_player="right",
    )

    result = simulate_opponent_lead_once(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        random_generator=random.Random(42),
    )

    next_state = result["next_state"]

    assert result["leader"] == "right"
    assert isinstance(result["lead_card"], str)
    assert isinstance(next_state, GameState)
    assert next_state.current_trick == [result["lead_card"]]
    assert next_state.trick_leader == "right"
    assert next_state.next_player == "me"


def test_simulate_left_lead_and_right_response_once_returns_expected_keys() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10"],
        current_trick=[],
        next_player="left",
    )

    result = simulate_left_lead_and_right_response_once(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        random_generator=random.Random(42),
    )

    assert set(result.keys()) == {
        "leader",
        "lead_card",
        "responder",
        "response_card",
        "next_state",
    }


def test_simulate_left_lead_and_right_response_once_prepares_player_action() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10"],
        current_trick=[],
        next_player="left",
    )

    result = simulate_left_lead_and_right_response_once(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        random_generator=random.Random(42),
    )

    next_state = result["next_state"]

    assert result["leader"] == "left"
    assert result["responder"] == "right"
    assert isinstance(result["lead_card"], str)
    assert isinstance(result["response_card"], str)
    assert len(next_state.current_trick) == 2
    assert next_state.trick_leader == "left"
    assert next_state.next_player == "me"


def test_simulate_left_lead_and_right_response_once_requires_left_next_player() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10"],
        current_trick=[],
        next_player="right",
    )

    try:
        simulate_left_lead_and_right_response_once(
            state=state,
            left_hand_size=5,
            right_hand_size=5,
            random_generator=random.Random(42),
        )
    except ValueError as error:
        assert "next_player to be left" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_simulate_opponent_lead_once_is_reproducible_with_seed() -> None:
    first_state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10"],
        current_trick=[],
        next_player="left",
    )

    second_state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10"],
        current_trick=[],
        next_player="left",
    )

    first_result = simulate_opponent_lead_once(
        state=first_state,
        left_hand_size=5,
        right_hand_size=5,
        random_generator=random.Random(42),
    )

    second_result = simulate_opponent_lead_once(
        state=second_state,
        left_hand_size=5,
        right_hand_size=5,
        random_generator=random.Random(42),
    )

    assert first_result == second_result

def test_simulate_opponent_lead_once_supports_highest_point_policy() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10"],
        current_trick=[],
        next_player="right",
    )

    result = simulate_opponent_lead_once(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        random_generator=random.Random(42),
        opponent_lead_policy="highest_point",
    )

    assert result["leader"] == "right"
    assert isinstance(result["lead_card"], str)


def test_simulate_left_lead_and_right_response_once_supports_response_policy() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10"],
        current_trick=[],
        next_player="left",
    )

    result = simulate_left_lead_and_right_response_once(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        random_generator=random.Random(42),
        opponent_lead_policy="lowest_point",
        opponent_response_policy="basic_trick_play",
    )

    assert result["leader"] == "left"
    assert result["responder"] == "right"
    assert isinstance(result["lead_card"], str)
    assert isinstance(result["response_card"], str)

def test_simulate_left_lead_and_right_response_once_supports_basic_defender_response(
) -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10"],
        current_trick=[],
        next_player="left",
    )

    result = simulate_left_lead_and_right_response_once(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        random_generator=random.Random(42),
        opponent_lead_policy="lowest_point",
        opponent_response_policy="basic_defender_response",
    )

    assert result["leader"] == "left"
    assert result["responder"] == "right"
    assert isinstance(result["lead_card"], str)
    assert isinstance(result["response_card"], str)

def test_simulate_opponent_lead_once_supports_basic_defender_lead_policy() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10"],
        current_trick=[],
        next_player="right",
    )

    result = simulate_opponent_lead_once(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        random_generator=random.Random(42),
        opponent_lead_policy="basic_defender_lead",
    )

    assert result["leader"] == "right"
    assert isinstance(result["lead_card"], str)
