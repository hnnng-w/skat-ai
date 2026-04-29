from skat_ai.card_selection import choose_first_legal_card
from skat_ai.game_state import GameState
from skat_ai.multi_step_simulation import (
    get_multi_step_stop_reason,
    should_continue_multi_step_simulation,
    simulate_multiple_steps,
)


def test_choose_first_legal_card_returns_first_legal_card_when_leading() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9"],
        current_trick=[],
    )

    selected_card = choose_first_legal_card(state)

    assert selected_card == "SA"


def test_choose_first_legal_card_respects_follow_suit() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["H10", "SA", "S9"],
        current_trick=["S7"],
    )

    selected_card = choose_first_legal_card(state)

    assert selected_card == "SA"


def test_choose_first_legal_card_raises_error_without_legal_cards() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=[],
        current_trick=[],
    )

    try:
        choose_first_legal_card(state)
    except ValueError as error:
        assert "No legal cards" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_simulate_multiple_steps_returns_expected_keys() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9", "H10", "D7"],
        current_trick=["S7"],
    )

    result = simulate_multiple_steps(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        step_count=1,
        random_seed=42,
        use_basic_opponent_strategy=True,
    )

    assert set(result.keys()) == {
        "initial_state",
        "final_state",
        "card_selection_policy",
        "requested_step_count",
        "steps_simulated",
        "stop_reason",
        "steps",
    }


def test_simulate_multiple_steps_runs_requested_number_of_steps_when_possible() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9", "H10", "D7"],
        current_trick=[],
        trick_leader="me",
    )

    result = simulate_multiple_steps(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        step_count=2,
        random_seed=42,
        use_basic_opponent_strategy=True,
        card_selection_policy="highest_point",
    )

    assert len(result["steps"]) <= 2
    assert result["requested_step_count"] == 2
    assert result["steps_simulated"] == len(result["steps"])


def test_simulate_multiple_steps_stops_when_hand_is_empty() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA"],
        current_trick=["S7"],
    )

    result = simulate_multiple_steps(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        step_count=3,
        random_seed=42,
        use_basic_opponent_strategy=True,
    )

    assert len(result["steps"]) == 1


def test_simulate_multiple_steps_reduces_hand_size() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9", "H10", "D7"],
        current_trick=[],
        trick_leader="me",
    )

    result = simulate_multiple_steps(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        step_count=2,
        random_seed=42,
        use_basic_opponent_strategy=True,
        card_selection_policy="highest_point",
    )

    final_state = result["final_state"]

    assert len(final_state.hand) == len(state.hand) - result["steps_simulated"]


def test_simulate_multiple_steps_appends_completed_tricks() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9", "H10", "D7"],
        current_trick=[],
        trick_leader="me",
    )

    result = simulate_multiple_steps(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        step_count=2,
        random_seed=42,
        use_basic_opponent_strategy=True,
        card_selection_policy="highest_point",
    )

    final_state = result["final_state"]

    assert len(final_state.completed_tricks) == result["steps_simulated"]


def test_simulate_multiple_steps_does_not_mutate_initial_state() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9", "H10", "D7"],
        current_trick=["S7"],
        completed_tricks=[],
    )

    result = simulate_multiple_steps(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        step_count=2,
        random_seed=42,
        use_basic_opponent_strategy=True,
    )

    final_state = result["final_state"]

    assert state.hand == ["SA", "S10", "S9", "H10", "D7"]
    assert state.current_trick == ["S7"]
    assert state.completed_tricks == []
    assert final_state is not state


def test_simulate_multiple_steps_is_reproducible_with_seed() -> None:
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

    first_result = simulate_multiple_steps(
        state=first_state,
        left_hand_size=5,
        right_hand_size=5,
        step_count=2,
        random_seed=42,
        use_basic_opponent_strategy=True,
    )

    second_result = simulate_multiple_steps(
        state=second_state,
        left_hand_size=5,
        right_hand_size=5,
        step_count=2,
        random_seed=42,
        use_basic_opponent_strategy=True,
    )

    assert first_result == second_result


def test_simulate_multiple_steps_rejects_zero_steps() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA"],
        current_trick=["S7"],
    )

    try:
        simulate_multiple_steps(
            state=state,
            left_hand_size=5,
            right_hand_size=5,
            step_count=0,
            random_seed=42,
            use_basic_opponent_strategy=True,
        )
    except ValueError as error:
        assert "step_count" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_simulate_multiple_steps_uses_default_card_selection_policy() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9", "H10", "D7"],
        current_trick=["S7"],
    )

    result = simulate_multiple_steps(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        step_count=1,
        random_seed=42,
        use_basic_opponent_strategy=True,
    )

    assert result["card_selection_policy"] == "first_legal"
    assert result["steps"][0]["card_selection_policy"] == "first_legal"


def test_simulate_multiple_steps_supports_lowest_point_policy() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9", "H10", "D7"],
        current_trick=["S7"],
    )

    result = simulate_multiple_steps(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        step_count=1,
        random_seed=42,
        use_basic_opponent_strategy=True,
        card_selection_policy="lowest_point",
    )

    assert result["card_selection_policy"] == "lowest_point"
    assert result["steps"][0]["candidate_card"] == "S9"


def test_simulate_multiple_steps_supports_highest_point_policy() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9", "H10", "D7"],
        current_trick=["S7"],
    )

    result = simulate_multiple_steps(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        step_count=1,
        random_seed=42,
        use_basic_opponent_strategy=True,
        card_selection_policy="highest_point",
    )

    assert result["card_selection_policy"] == "highest_point"
    assert result["steps"][0]["candidate_card"] == "SA"


def test_simulate_multiple_steps_rejects_invalid_card_selection_policy() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9", "H10", "D7"],
        current_trick=["S7"],
    )

    try:
        simulate_multiple_steps(
            state=state,
            left_hand_size=5,
            right_hand_size=5,
            step_count=1,
            random_seed=42,
            use_basic_opponent_strategy=True,
            card_selection_policy="invalid_policy",
        )
    except ValueError as error:
        assert "Invalid card selection policy" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_simulate_multiple_steps_supports_highest_expected_value_policy() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9", "H10", "D7"],
        current_trick=["S7"],
    )

    result = simulate_multiple_steps(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        step_count=1,
        random_seed=42,
        use_basic_opponent_strategy=True,
        card_selection_policy="highest_expected_value",
        expected_value_sample_count=20,
    )

    assert result["card_selection_policy"] == "highest_expected_value"
    assert result["steps"][0]["card_selection_policy"] == "highest_expected_value"
    assert result["steps"][0]["candidate_card"] in ["SA", "S10", "S9"]


def test_simulate_multiple_steps_highest_expected_value_is_reproducible_with_seed() -> None:
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

    first_result = simulate_multiple_steps(
        state=first_state,
        left_hand_size=5,
        right_hand_size=5,
        step_count=1,
        random_seed=42,
        use_basic_opponent_strategy=True,
        card_selection_policy="highest_expected_value",
        expected_value_sample_count=20,
    )

    second_result = simulate_multiple_steps(
        state=second_state,
        left_hand_size=5,
        right_hand_size=5,
        step_count=1,
        random_seed=42,
        use_basic_opponent_strategy=True,
        card_selection_policy="highest_expected_value",
        expected_value_sample_count=20,
    )

    assert first_result == second_result


def test_should_continue_multi_step_simulation_allows_first_step() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA"],
        current_trick=["S7"],
        next_player="left",
    )

    assert should_continue_multi_step_simulation(state, step_index=0) is True


def test_should_continue_multi_step_simulation_allows_later_step_when_next_player_is_me() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA"],
        current_trick=[],
        next_player="me",
    )

    assert should_continue_multi_step_simulation(state, step_index=1) is True


def test_should_continue_multi_step_stops_when_next_player_is_not_me() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA"],
        current_trick=[],
        next_player="left",
    )

    assert should_continue_multi_step_simulation(state, step_index=1) is False


def test_get_multi_step_stop_reason_when_hand_is_empty() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=[],
        current_trick=[],
        next_player="me",
    )

    reason = get_multi_step_stop_reason(
        current_state=state,
        step_index=1,
    )

    assert reason == "Player has no cards left."


def test_get_multi_step_stop_reason_when_next_player_is_not_me() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA"],
        current_trick=[],
        next_player="left",
    )

    reason = get_multi_step_stop_reason(
        current_state=state,
        step_index=1,
    )

    assert reason == "Next player is left, not me."


def test_simulate_multiple_steps_stops_when_next_player_is_not_me_after_first_step() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["S9", "D7"],
        current_trick=["S7"],
        trick_leader="left",
    )

    result = simulate_multiple_steps(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        step_count=3,
        random_seed=42,
        use_basic_opponent_strategy=True,
        card_selection_policy="lowest_point",
    )

    assert result["steps_simulated"] <= 3

    if result["final_state"].next_player != "me":
        assert (
            "not me" in result["stop_reason"]
            or result["stop_reason"] == "Requested step count reached."
        )