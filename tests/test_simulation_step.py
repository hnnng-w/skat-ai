import random

from skat_ai.game_state import GameState
from skat_ai.simulation_step import simulate_and_advance_once


def test_simulate_and_advance_once_returns_expected_keys() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9", "H10", "D7"],
        current_trick=["S7"],
    )

    result = simulate_and_advance_once(
        state=state,
        candidate_card="SA",
        left_hand_size=5,
        right_hand_size=5,
        random_generator=random.Random(42),
        use_basic_opponent_strategy=True,
    )

    assert set(result.keys()) == {
        "detailed_result",
        "next_state",
    }


def test_simulate_and_advance_once_returns_detailed_result() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9", "H10", "D7"],
        current_trick=["S7"],
    )

    result = simulate_and_advance_once(
        state=state,
        candidate_card="SA",
        left_hand_size=5,
        right_hand_size=5,
        random_generator=random.Random(42),
        use_basic_opponent_strategy=True,
    )

    detailed_result = result["detailed_result"]

    assert set(detailed_result.keys()) == {
        "trick",
        "did_win",
        "trick_points",
        "completed_trick",
    }


def test_simulate_and_advance_once_returns_next_state() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9", "H10", "D7"],
        current_trick=["S7"],
    )

    result = simulate_and_advance_once(
        state=state,
        candidate_card="SA",
        left_hand_size=5,
        right_hand_size=5,
        random_generator=random.Random(42),
        use_basic_opponent_strategy=True,
    )

    next_state = result["next_state"]

    assert isinstance(next_state, GameState)


def test_simulate_and_advance_once_removes_candidate_card_from_next_state() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9", "H10", "D7"],
        current_trick=["S7"],
    )

    result = simulate_and_advance_once(
        state=state,
        candidate_card="SA",
        left_hand_size=5,
        right_hand_size=5,
        random_generator=random.Random(42),
        use_basic_opponent_strategy=True,
    )

    next_state = result["next_state"]

    assert "SA" not in next_state.hand
    assert next_state.hand == ["S10", "S9", "H10", "D7"]


def test_simulate_and_advance_once_clears_current_trick_in_next_state() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9", "H10", "D7"],
        current_trick=["S7"],
    )

    result = simulate_and_advance_once(
        state=state,
        candidate_card="SA",
        left_hand_size=5,
        right_hand_size=5,
        random_generator=random.Random(42),
        use_basic_opponent_strategy=True,
    )

    next_state = result["next_state"]

    assert next_state.current_trick == []


def test_simulate_and_advance_once_appends_completed_trick() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9", "H10", "D7"],
        current_trick=["S7"],
    )

    result = simulate_and_advance_once(
        state=state,
        candidate_card="SA",
        left_hand_size=5,
        right_hand_size=5,
        random_generator=random.Random(42),
        use_basic_opponent_strategy=True,
    )

    detailed_result = result["detailed_result"]
    next_state = result["next_state"]

    assert next_state.completed_tricks == [
        detailed_result["completed_trick"],
    ]


def test_simulate_and_advance_once_updates_points() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9", "H10", "D7"],
        current_trick=["S7"],
        declarer_points=0,
        defender_points=0,
    )

    result = simulate_and_advance_once(
        state=state,
        candidate_card="SA",
        left_hand_size=5,
        right_hand_size=5,
        random_generator=random.Random(42),
        use_basic_opponent_strategy=True,
    )

    detailed_result = result["detailed_result"]
    next_state = result["next_state"]

    if detailed_result["completed_trick"]["winner_role"] == "declarer":
        assert next_state.declarer_points == detailed_result["trick_points"]
        assert next_state.defender_points == 0
    else:
        assert next_state.declarer_points == 0
        assert next_state.defender_points == detailed_result["trick_points"]


def test_simulate_and_advance_once_does_not_mutate_original_state() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9", "H10", "D7"],
        current_trick=["S7"],
        completed_tricks=[],
        declarer_points=0,
        defender_points=0,
    )

    result = simulate_and_advance_once(
        state=state,
        candidate_card="SA",
        left_hand_size=5,
        right_hand_size=5,
        random_generator=random.Random(42),
        use_basic_opponent_strategy=True,
    )

    next_state = result["next_state"]

    assert state.hand == ["SA", "S10", "S9", "H10", "D7"]
    assert state.current_trick == ["S7"]
    assert state.completed_tricks == []
    assert state.declarer_points == 0
    assert state.defender_points == 0

    assert next_state.hand != state.hand
    assert next_state.current_trick == []
    assert len(next_state.completed_tricks) == 1


def test_simulate_and_advance_once_is_reproducible_with_seed() -> None:
    first_state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9", "H10", "D7"],
        current_trick=["S7"],
    )

    second_state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9", "H10", "D7"],
        current_trick=["S7"],
    )

    first_result = simulate_and_advance_once(
        state=first_state,
        candidate_card="SA",
        left_hand_size=5,
        right_hand_size=5,
        random_generator=random.Random(42),
        use_basic_opponent_strategy=True,
    )

    second_result = simulate_and_advance_once(
        state=second_state,
        candidate_card="SA",
        left_hand_size=5,
        right_hand_size=5,
        random_generator=random.Random(42),
        use_basic_opponent_strategy=True,
    )

    assert first_result == second_result