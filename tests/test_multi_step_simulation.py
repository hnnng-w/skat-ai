from skat_ai.card_selection import choose_first_legal_card
from skat_ai.game_state import GameState
from skat_ai.multi_step_simulation import simulate_multiple_steps


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
        "steps",
    }


def test_simulate_multiple_steps_runs_requested_number_of_steps_when_possible() -> None:
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
        step_count=2,
        random_seed=42,
        use_basic_opponent_strategy=True,
    )

    assert len(result["steps"]) == 2


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
        current_trick=["S7"],
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

    assert len(final_state.hand) == 3


def test_simulate_multiple_steps_appends_completed_tricks() -> None:
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
        step_count=2,
        random_seed=42,
        use_basic_opponent_strategy=True,
    )

    final_state = result["final_state"]

    assert len(final_state.completed_tricks) == 2


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