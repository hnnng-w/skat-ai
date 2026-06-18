
import skat_ai.opponent_lead as opponent_lead_module
import skat_ai.simulation as simulation_module
from skat_ai.card_selection import choose_first_legal_card
from skat_ai.game_state import GameState
from skat_ai.multi_step_simulation import (
    extract_opponent_cards_from_step,
    get_multi_step_stop_reason,
    prepare_state_for_player_action,
    should_continue_multi_step_simulation,
    simulate_multiple_steps,
)
from skat_ai.strategic_metadata import StrategicMetadata


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
        "strict_context",
        "context",
        "context_summary",
        "summary",
        "steps",
        "opponent_policy_settings",
        "left_opponent_policy_settings",
        "right_opponent_policy_settings",
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


def test_should_continue_multi_step_allows_right_next_player() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA"],
        current_trick=[],
        next_player="right",
    )

    assert should_continue_multi_step_simulation(state, step_index=1) is True


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


def test_prepare_state_for_player_action_returns_state_when_next_player_is_me() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA"],
        current_trick=[],
        next_player="me",
    )

    prepared_state, opponent_lead_result = prepare_state_for_player_action(
        current_state=state,
        left_hand_size=5,
        right_hand_size=5,
        random_generator=__import__("random").Random(42),
    )

    assert prepared_state == state
    assert opponent_lead_result is None


def test_prepare_state_for_player_action_simulates_right_lead() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10"],
        current_trick=[],
        next_player="right",
    )

    prepared_state, opponent_lead_result = prepare_state_for_player_action(
        current_state=state,
        left_hand_size=5,
        right_hand_size=5,
        random_generator=__import__("random").Random(42),
    )

    assert opponent_lead_result is not None
    assert opponent_lead_result["leader"] == "right"
    assert prepared_state.trick_leader == "right"
    assert prepared_state.next_player == "me"
    assert len(prepared_state.current_trick) == 1


def test_simulate_multiple_steps_continues_after_right_lead() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9"],
        current_trick=[],
        next_player="right",
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

    assert result["steps_simulated"] == 1
    assert result["steps"][0]["opponent_lead_result"] is not None
    assert result["steps"][0]["opponent_lead_result"]["leader"] == "right"
    assert result["steps"][0]["candidate_card"] in ["SA", "S10", "S9"]


def test_simulate_multiple_steps_after_right_lead_completes_with_left_hand(
    monkeypatch,
) -> None:
    def fake_generate_random_opponent_hands(
        state: GameState,
        left_hand_size: int,
        right_hand_size: int,
        random_generator: object | None = None,
    ) -> tuple[list[str], list[str]]:
        _ = (left_hand_size, right_hand_size, random_generator)

        if not state.current_trick:
            return ["H10"], ["S7"]

        return ["S8", "H10"], ["S9", "D10"]

    monkeypatch.setattr(
        opponent_lead_module,
        "generate_random_opponent_hands",
        fake_generate_random_opponent_hands,
    )
    monkeypatch.setattr(
        simulation_module,
        "generate_random_opponent_hands",
        fake_generate_random_opponent_hands,
    )

    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA"],
        current_trick=[],
        next_player="right",
    )

    result = simulate_multiple_steps(
        state=state,
        left_hand_size=2,
        right_hand_size=2,
        step_count=1,
        random_seed=42,
        use_basic_opponent_strategy=True,
        card_selection_policy="highest_point",
    )
    step = result["steps"][0]

    assert step["opponent_lead_result"]["leader"] == "right"
    assert step["opponent_lead_result"]["lead_card"] == "S7"
    assert step["candidate_card"] == "SA"
    assert step["detailed_result"]["trick"] == ["S7", "SA", "S8"]
    assert step["detailed_result"]["completed_trick"]["players"] == [
        "right",
        "me",
        "left",
    ]
    assert result["context"].simulated_opponent_cards == ["S7", "S8"]


def test_multi_step_candidate_completion_consumes_configured_side_response_policy(
    monkeypatch,
) -> None:
    def fake_generate_random_opponent_hands(
        state: GameState,
        left_hand_size: int,
        right_hand_size: int,
        random_generator: object | None = None,
    ) -> tuple[list[str], list[str]]:
        _ = (left_hand_size, right_hand_size, random_generator)

        if not state.current_trick:
            return ["S9", "SA"], ["S7"]

        return ["S9", "SA"], ["D7"]

    monkeypatch.setattr(
        opponent_lead_module,
        "generate_random_opponent_hands",
        fake_generate_random_opponent_hands,
    )
    monkeypatch.setattr(
        simulation_module,
        "generate_random_opponent_hands",
        fake_generate_random_opponent_hands,
    )

    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["S8"],
        current_trick=[],
        next_player="right",
    )

    result = simulate_multiple_steps(
        state=state,
        left_hand_size=2,
        right_hand_size=1,
        step_count=1,
        random_seed=42,
        use_basic_opponent_strategy=True,
        card_selection_policy="highest_point",
        opponent_response_policy="highest_point",
        left_opponent_policy_settings={
            "opponent_lead_policy": "lowest_point",
            "opponent_response_policy": "highest_point",
        },
        right_opponent_policy_settings={
            "opponent_lead_policy": "lowest_point",
            "opponent_response_policy": "highest_point",
        },
        opponent_response_policy_by_player={
            "left": "highest_point",
            "right": "highest_point",
        },
    )

    step = result["steps"][0]

    assert step["opponent_lead_result"]["lead_card"] == "S7"
    assert step["candidate_card"] == "S8"
    assert step["detailed_result"]["trick"] == ["S7", "S8", "SA"]
    assert result["left_opponent_policy_settings"] == {
        "opponent_lead_policy": "lowest_point",
        "opponent_response_policy": "highest_point",
    }


def test_should_continue_multi_step_allows_left_next_player() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA"],
        current_trick=[],
        next_player="left",
    )

    assert should_continue_multi_step_simulation(state, step_index=1) is True


def test_get_multi_step_stop_reason_returns_none_when_left_is_next_player() -> None:
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

    assert reason is None


def test_simulate_multiple_steps_continues_after_left_lead_and_right_response() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9"],
        current_trick=[],
        next_player="left",
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

    assert result["steps_simulated"] == 1
    assert result["steps"][0]["opponent_lead_result"] is not None
    assert result["steps"][0]["opponent_lead_result"]["leader"] == "left"
    assert result["steps"][0]["opponent_lead_result"]["responder"] == "right"
    assert result["steps"][0]["candidate_card"] in ["SA", "S10", "S9"]


def test_multi_step_opponent_turn_preparation_executes_effective_right_response_policy(
    monkeypatch,
) -> None:
    def fake_generate_random_opponent_hands(
        state: GameState,
        left_hand_size: int,
        right_hand_size: int,
        random_generator: object | None = None,
    ) -> tuple[list[str], list[str]]:
        _ = (state, left_hand_size, right_hand_size, random_generator)
        return ["S7"], ["S9", "SA"]

    monkeypatch.setattr(
        opponent_lead_module,
        "generate_random_opponent_hands",
        fake_generate_random_opponent_hands,
    )

    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["S8"],
        current_trick=[],
        next_player="left",
    )

    result = simulate_multiple_steps(
        state=state,
        left_hand_size=1,
        right_hand_size=2,
        step_count=1,
        random_seed=42,
        use_basic_opponent_strategy=True,
        card_selection_policy="highest_point",
        left_opponent_policy_settings={
            "opponent_lead_policy": "lowest_point",
            "opponent_response_policy": "lowest_point",
        },
        right_opponent_policy_settings={
            "opponent_lead_policy": "lowest_point",
            "opponent_response_policy": "highest_point",
        },
    )

    opponent_lead_result = result["steps"][0]["opponent_lead_result"]

    assert opponent_lead_result["leader"] == "left"
    assert opponent_lead_result["lead_card"] == "S7"
    assert opponent_lead_result["responder"] == "right"
    assert opponent_lead_result["response_card"] == "SA"


def test_prepare_state_for_player_action_simulates_left_lead_and_right_response() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10"],
        current_trick=[],
        next_player="left",
    )

    prepared_state, opponent_lead_result = prepare_state_for_player_action(
        current_state=state,
        left_hand_size=5,
        right_hand_size=5,
        random_generator=__import__("random").Random(42),
    )

    assert opponent_lead_result is not None
    assert opponent_lead_result["leader"] == "left"
    assert opponent_lead_result["responder"] == "right"
    assert prepared_state.trick_leader == "left"
    assert prepared_state.next_player == "me"
    assert len(prepared_state.current_trick) == 2


def test_extract_opponent_cards_from_step_without_opponent_lead() -> None:
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
    }

    opponent_cards = extract_opponent_cards_from_step(step)

    assert opponent_cards == ["S7", "S8"]


def test_extract_opponent_cards_from_step_with_right_lead() -> None:
    step = {
        "step_index": 0,
        "opponent_lead_result": {
            "leader": "right",
            "lead_card": "D7",
        },
        "candidate_card": "DA",
        "card_selection_policy": "highest_point",
        "detailed_result": {
            "trick": ["D7", "DA", "D8"],
            "did_win": True,
            "trick_points": 11,
            "completed_trick": {
                "cards": ["D7", "DA", "D8"],
                "winner_role": "declarer",
            },
        },
    }

    opponent_cards = extract_opponent_cards_from_step(step)

    assert opponent_cards == ["D7", "D8"]


def test_extract_opponent_cards_from_step_with_left_lead_and_right_response() -> None:
    step = {
        "step_index": 0,
        "opponent_lead_result": {
            "leader": "left",
            "lead_card": "D7",
            "responder": "right",
            "response_card": "D9",
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
    }

    opponent_cards = extract_opponent_cards_from_step(step)

    assert opponent_cards == ["D7", "D9"]


def test_simulate_multiple_steps_returns_context_summary() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9"],
        current_trick=["S7"],
        next_player="me",
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

    assert "context_summary" in result
    assert result["context_summary"]["event_count"] == 1
    assert result["context_summary"]["simulated_opponent_card_count"] >= 1

def test_simulate_multiple_steps_context_tracks_opponent_cards() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9"],
        current_trick=["S7"],
        next_player="me",
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

    context = result["context"]

    assert len(context.simulated_opponent_cards) >= 1
    assert result["context_summary"]["simulated_opponent_card_count"] >= 1


def test_simulate_multiple_steps_applies_context_to_later_sampling() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9", "H10"],
        current_trick=[],
        trick_leader="me",
        next_player="me",
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

    context = result["context"]

    assert result["steps_simulated"] >= 1
    assert len(context.simulated_opponent_cards) >= 1

def test_simulate_multiple_steps_defaults_to_non_strict_context() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9"],
        current_trick=["S7"],
        next_player="me",
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

    assert result["strict_context"] is False


def test_simulate_multiple_steps_supports_strict_context() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9"],
        current_trick=["S7"],
        next_player="me",
    )

    result = simulate_multiple_steps(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        step_count=1,
        random_seed=42,
        use_basic_opponent_strategy=True,
        card_selection_policy="highest_point",
        strict_context=True,
    )

    assert result["strict_context"] is True

def test_simulate_multiple_steps_returns_summary() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9"],
        current_trick=["S7"],
        next_player="me",
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

    assert "summary" in result
    assert result["summary"]["steps_simulated"] == result["steps_simulated"]
    assert "score_summary" in result["summary"]
    assert "final_point_swing" in result["summary"]["score_summary"]

def test_simulate_multiple_steps_accepts_strategic_metadata() -> None:
    metadata = StrategicMetadata(
        analysis_mode="post_game_review",
        skat_visibility="known_post_game",
        game_end_reason="normal_completion",
    )
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9"],
        current_trick=["S7"],
        next_player="me",
    )

    result = simulate_multiple_steps(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        step_count=1,
        random_seed=42,
        use_basic_opponent_strategy=True,
        card_selection_policy="highest_point",
        strategic_metadata=metadata,
    )

    assert result["context"].strategic_metadata == metadata
    assert result["context_summary"]["strategic_metadata"] == {
        "analysis_mode": "post_game_review",
        "skat_visibility": "known_post_game",
        "game_end_reason": "normal_completion",
    }

def test_simulate_multiple_steps_accepts_opponent_policies() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9"],
        current_trick=[],
        next_player="left",
    )

    result = simulate_multiple_steps(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        step_count=1,
        random_seed=42,
        use_basic_opponent_strategy=True,
        card_selection_policy="highest_point",
        opponent_lead_policy="highest_point",
        opponent_response_policy="basic_trick_play",
    )

    assert result["steps_simulated"] == 1
    assert result["steps"][0]["opponent_lead_result"] is not None

def test_simulate_multiple_steps_returns_opponent_policy_settings() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9"],
        current_trick=[],
        next_player="left",
    )

    result = simulate_multiple_steps(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        step_count=1,
        random_seed=42,
        card_selection_policy="highest_point",
        opponent_lead_policy="highest_point",
        opponent_response_policy="basic_trick_play",
    )

    assert result["opponent_policy_settings"] == {
        "opponent_lead_policy": "highest_point",
        "opponent_response_policy": "basic_trick_play",
    }
