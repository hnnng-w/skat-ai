from skat_ai.game_history import build_completed_trick_from_state_and_candidate
from skat_ai.game_state import GameState
from skat_ai.rules import get_legal_cards
from skat_ai.simulation import (
    choose_basic_opponent_card,
    choose_random_legal_card,
    complete_trick_after_candidate_card,
    estimate_immediate_trick_value,
    estimate_immediate_trick_values_for_legal_cards,
    estimate_immediate_trick_win_rate,
    estimate_immediate_trick_win_rates_for_legal_cards,
    generate_multiple_random_opponent_hands,
    generate_random_opponent_hands,
    simulate_immediate_trick_once,
    simulate_immediate_trick_once_detailed,
    simulate_immediate_trick_once_with_points,
)


def test_generate_random_opponent_hands_returns_requested_sizes() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["CJ", "SA", "S9", "H10", "D7"],
        current_trick=[],
        played_cards=[],
        skat=[],
    )

    left_hand, right_hand = generate_random_opponent_hands(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
    )

    assert len(left_hand) == 5
    assert len(right_hand) == 5


def test_generate_random_opponent_hands_uses_only_unseen_cards() -> None:
    from skat_ai.card_tracking import get_unseen_cards

    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["CJ", "SA", "S9", "H10", "D7"],
        current_trick=[],
        played_cards=[],
        skat=[],
    )

    unseen_cards = get_unseen_cards(state)

    left_hand, right_hand = generate_random_opponent_hands(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
    )

    for card in left_hand + right_hand:
        assert card in unseen_cards


def test_generate_random_opponent_hands_has_no_duplicate_cards() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["CJ", "SA", "S9", "H10", "D7"],
        current_trick=[],
        played_cards=[],
        skat=[],
    )

    left_hand, right_hand = generate_random_opponent_hands(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
    )

    all_generated_cards = left_hand + right_hand

    assert len(all_generated_cards) == len(set(all_generated_cards))


def test_generate_random_opponent_hands_raises_error_when_too_many_cards_requested() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["CJ", "SA", "S9", "H10", "D7"],
        current_trick=[],
        played_cards=[],
        skat=[],
    )

    try:
        generate_random_opponent_hands(
            state=state,
            left_hand_size=20,
            right_hand_size=20,
        )
    except ValueError as error:
        assert "Not enough available cards for opponent sampling" in str(error)
        assert "required 40" in str(error)
        assert "available 27" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_generate_multiple_random_opponent_hands_returns_requested_sample_count() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["CJ", "SA", "S9", "H10", "D7"],
        current_trick=[],
        played_cards=[],
        skat=[],
    )

    samples = generate_multiple_random_opponent_hands(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        sample_count=3,
    )

    assert len(samples) == 3


def test_choose_random_legal_card_returns_card_from_hand() -> None:
    hand = ["SA", "S9"]
    current_trick = ["S10"]

    selected_card = choose_random_legal_card(
        hand=hand,
        current_trick=current_trick,
        game_type="grand",
    )

    assert selected_card in hand


def test_choose_random_legal_card_respects_legal_cards() -> None:
    hand = ["SA", "S9", "H10"]
    current_trick = ["S10"]

    selected_card = choose_random_legal_card(
        hand=hand,
        current_trick=current_trick,
        game_type="grand",
    )

    assert selected_card in ["SA", "S9"]


def test_simulate_immediate_trick_once_returns_boolean() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9", "H10", "D7"],
        current_trick=[],
        played_cards=[],
        skat=[],
    )

    result = simulate_immediate_trick_once(
        state=state,
        candidate_card="SA",
        left_hand_size=5,
        right_hand_size=5,
    )

    assert isinstance(result, bool)


def test_estimate_immediate_trick_win_rate_returns_value_between_zero_and_one() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9", "H10", "D7"],
        current_trick=[],
        played_cards=[],
        skat=[],
    )

    win_rate = estimate_immediate_trick_win_rate(
        state=state,
        candidate_card="SA",
        left_hand_size=5,
        right_hand_size=5,
        sample_count=100,
    )

    assert 0.0 <= win_rate <= 1.0


def test_estimate_immediate_trick_win_rate_raises_error_for_zero_samples() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9", "H10", "D7"],
        current_trick=[],
        played_cards=[],
        skat=[],
    )

    try:
        estimate_immediate_trick_win_rate(
            state=state,
            candidate_card="SA",
            left_hand_size=5,
            right_hand_size=5,
            sample_count=0,
        )
    except ValueError as error:
        assert "Sample count" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_estimate_immediate_trick_win_rates_for_legal_cards_returns_all_legal_cards() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9"],
        current_trick=[],
        played_cards=[],
        skat=[],
    )

    win_rates = estimate_immediate_trick_win_rates_for_legal_cards(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        sample_count=20,
    )

    assert set(win_rates.keys()) == {"SA", "S10", "S9"}

    for win_rate in win_rates.values():
        assert 0.0 <= win_rate <= 1.0


def test_generate_multiple_random_opponent_hands_is_reproducible_with_seed() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["CJ", "SA", "S9", "H10", "D7"],
        current_trick=[],
        played_cards=[],
        skat=[],
    )

    first_samples = generate_multiple_random_opponent_hands(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        sample_count=3,
        random_seed=42,
    )

    second_samples = generate_multiple_random_opponent_hands(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        sample_count=3,
        random_seed=42,
    )

    assert first_samples == second_samples


def test_estimate_immediate_trick_win_rate_is_reproducible_with_seed() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9", "H10", "D7"],
        current_trick=[],
        played_cards=[],
        skat=[],
    )

    first_win_rate = estimate_immediate_trick_win_rate(
        state=state,
        candidate_card="SA",
        left_hand_size=5,
        right_hand_size=5,
        sample_count=100,
        random_seed=42,
    )

    second_win_rate = estimate_immediate_trick_win_rate(
        state=state,
        candidate_card="SA",
        left_hand_size=5,
        right_hand_size=5,
        sample_count=100,
        random_seed=42,
    )

    assert first_win_rate == second_win_rate


def test_choose_basic_opponent_card_wins_with_lowest_point_winning_card() -> None:
    hand = ["SA", "S9", "H10"]
    current_trick = ["S10"]

    selected_card = choose_basic_opponent_card(
        hand=hand,
        current_trick=current_trick,
        game_type="grand",
    )

    assert selected_card == "SA"


def test_choose_basic_opponent_card_plays_lowest_points_when_cannot_win() -> None:
    hand = ["S9", "S7", "H10"]
    current_trick = ["SA"]

    selected_card = choose_basic_opponent_card(
        hand=hand,
        current_trick=current_trick,
        game_type="grand",
    )

    assert selected_card == "S9"


def test_choose_basic_opponent_card_respects_legal_cards() -> None:
    hand = ["SA", "S9", "H10"]
    current_trick = ["S10"]

    selected_card = choose_basic_opponent_card(
        hand=hand,
        current_trick=current_trick,
        game_type="grand",
    )

    assert selected_card in ["SA", "S9"]


def test_estimate_immediate_trick_win_rate_supports_basic_opponent_strategy_flag() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9", "H10", "D7"],
        current_trick=[],
        played_cards=[],
        skat=[],
    )

    win_rate = estimate_immediate_trick_win_rate(
        state=state,
        candidate_card="SA",
        left_hand_size=5,
        right_hand_size=5,
        sample_count=20,
        random_seed=42,
        use_basic_opponent_strategy=True,
    )

    assert 0.0 <= win_rate <= 1.0


def test_simulate_immediate_trick_once_with_points_returns_boolean_and_points() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9", "H10", "D7"],
        current_trick=[],
        played_cards=[],
        skat=[],
    )

    did_win, trick_points = simulate_immediate_trick_once_with_points(
        state=state,
        candidate_card="SA",
        left_hand_size=5,
        right_hand_size=5,
        random_generator=None,
        use_basic_opponent_strategy=True,
    )

    assert isinstance(did_win, bool)
    assert isinstance(trick_points, int)
    assert 0 <= trick_points <= 120


def test_estimate_immediate_trick_value_returns_expected_keys() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9", "H10", "D7"],
        current_trick=[],
        played_cards=[],
        skat=[],
    )

    value = estimate_immediate_trick_value(
        state=state,
        candidate_card="SA",
        left_hand_size=5,
        right_hand_size=5,
        sample_count=20,
        random_seed=42,
        use_basic_opponent_strategy=True,
    )

    assert set(value.keys()) == {
        "win_rate",
        "average_trick_points",
        "average_points_won",
        "average_points_lost",
    }


def test_estimate_immediate_trick_value_returns_values_in_valid_ranges() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9", "H10", "D7"],
        current_trick=[],
        played_cards=[],
        skat=[],
    )

    value = estimate_immediate_trick_value(
        state=state,
        candidate_card="SA",
        left_hand_size=5,
        right_hand_size=5,
        sample_count=20,
        random_seed=42,
        use_basic_opponent_strategy=True,
    )

    assert 0.0 <= value["win_rate"] <= 1.0
    assert 0.0 <= value["average_trick_points"] <= 120.0
    assert 0.0 <= value["average_points_won"] <= 120.0
    assert 0.0 <= value["average_points_lost"] <= 120.0


def test_estimate_immediate_trick_value_tracks_null_declarer_objective() -> None:
    state = GameState(
        game_type="null",
        player_role="declarer",
        declarer_player="me",
        hand=["CA", "C7"],
        current_trick=["C10", "C9"],
        trick_leader="left",
        next_player="me",
    )

    ace_value = estimate_immediate_trick_value(
        state=state,
        candidate_card="CA",
        left_hand_size=0,
        right_hand_size=0,
        sample_count=1,
        random_seed=42,
    )
    seven_value = estimate_immediate_trick_value(
        state=state,
        candidate_card="C7",
        left_hand_size=0,
        right_hand_size=0,
        sample_count=1,
        random_seed=42,
    )

    assert ace_value["expected_objective_utility"] == 0.0
    assert ace_value["average_points_won"] == 21.0
    assert seven_value["expected_objective_utility"] == 1.0
    assert seven_value["average_points_lost"] == 10.0


def test_estimate_immediate_trick_value_tracks_null_defender_objective() -> None:
    state = GameState(
        game_type="null",
        player_role="defender",
        declarer_player="left",
        hand=["CA", "C7"],
        current_trick=["C10", "C9"],
        trick_leader="left",
        next_player="me",
    )

    ace_value = estimate_immediate_trick_value(
        state=state,
        candidate_card="CA",
        left_hand_size=0,
        right_hand_size=0,
        sample_count=1,
        random_seed=42,
    )
    seven_value = estimate_immediate_trick_value(
        state=state,
        candidate_card="C7",
        left_hand_size=0,
        right_hand_size=0,
        sample_count=1,
        random_seed=42,
    )

    assert ace_value["expected_objective_utility"] == 0.0
    assert ace_value["average_points_won"] == 21.0
    assert seven_value["expected_objective_utility"] == 1.0
    assert seven_value["average_points_lost"] == 10.0


def test_estimate_immediate_trick_value_is_reproducible_with_seed() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9", "H10", "D7"],
        current_trick=[],
        played_cards=[],
        skat=[],
    )

    first_value = estimate_immediate_trick_value(
        state=state,
        candidate_card="SA",
        left_hand_size=5,
        right_hand_size=5,
        sample_count=50,
        random_seed=42,
        use_basic_opponent_strategy=True,
    )

    second_value = estimate_immediate_trick_value(
        state=state,
        candidate_card="SA",
        left_hand_size=5,
        right_hand_size=5,
        sample_count=50,
        random_seed=42,
        use_basic_opponent_strategy=True,
    )

    assert first_value == second_value


def test_estimate_immediate_trick_value_raises_error_for_zero_samples() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9", "H10", "D7"],
        current_trick=[],
        played_cards=[],
        skat=[],
    )

    try:
        estimate_immediate_trick_value(
            state=state,
            candidate_card="SA",
            left_hand_size=5,
            right_hand_size=5,
            sample_count=0,
            random_seed=42,
            use_basic_opponent_strategy=True,
        )
    except ValueError as error:
        assert "Sample count" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_estimate_immediate_trick_values_for_legal_cards_returns_all_legal_cards() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9"],
        current_trick=[],
        played_cards=[],
        skat=[],
    )

    values = estimate_immediate_trick_values_for_legal_cards(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        sample_count=20,
        random_seed=42,
        use_basic_opponent_strategy=True,
    )

    assert set(values.keys()) == {"SA", "S10", "S9"}

    for value in values.values():
        assert set(value.keys()) == {
            "win_rate",
            "average_trick_points",
            "average_points_won",
            "average_points_lost",
        }


def test_simulate_immediate_trick_once_supports_second_position() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9", "H10", "D7"],
        current_trick=["S7"],
        played_cards=[],
        skat=[],
    )

    result = simulate_immediate_trick_once(
        state=state,
        candidate_card="SA",
        left_hand_size=5,
        right_hand_size=5,
        random_generator=None,
        use_basic_opponent_strategy=True,
    )

    assert isinstance(result, bool)


def test_simulate_immediate_trick_once_supports_third_position() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9", "H10", "D7"],
        current_trick=["S7", "S8"],
        played_cards=[],
        skat=[],
    )

    result = simulate_immediate_trick_once(
        state=state,
        candidate_card="SA",
        left_hand_size=5,
        right_hand_size=5,
        random_generator=None,
        use_basic_opponent_strategy=True,
    )

    assert isinstance(result, bool)


def test_estimate_immediate_trick_value_supports_second_position() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9", "H10", "D7"],
        current_trick=["S7"],
        played_cards=[],
        skat=[],
    )

    value = estimate_immediate_trick_value(
        state=state,
        candidate_card="SA",
        left_hand_size=5,
        right_hand_size=5,
        sample_count=20,
        random_seed=42,
        use_basic_opponent_strategy=True,
    )

    assert 0.0 <= value["win_rate"] <= 1.0


def test_estimate_immediate_trick_value_supports_third_position() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9", "H10", "D7"],
        current_trick=["S7", "S8"],
        played_cards=[],
        skat=[],
    )

    value = estimate_immediate_trick_value(
        state=state,
        candidate_card="SA",
        left_hand_size=5,
        right_hand_size=5,
        sample_count=20,
        random_seed=42,
        use_basic_opponent_strategy=True,
    )

    assert 0.0 <= value["win_rate"] <= 1.0


def test_simulate_immediate_trick_once_detailed_returns_expected_keys() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9", "H10", "D7"],
        current_trick=["S7"],
        played_cards=[],
        skat=[],
    )

    result = simulate_immediate_trick_once_detailed(
        state=state,
        candidate_card="SA",
        left_hand_size=5,
        right_hand_size=5,
        random_generator=None,
        use_basic_opponent_strategy=True,
    )

    assert set(result.keys()) == {
        "trick",
        "did_win",
        "candidate_card_won",
        "local_side_won",
        "trick_points",
        "completed_trick",
    }


def test_detailed_result_counts_left_declarer_partner_win_as_local_win(monkeypatch) -> None:
    def fake_generate_random_opponent_hands(**_kwargs):
        return ["S8"], ["H7"]

    monkeypatch.setattr(
        "skat_ai.simulation.generate_random_opponent_hands",
        fake_generate_random_opponent_hands,
    )
    state = GameState(
        game_type="grand",
        player_role="defender",
        declarer_player="left",
        hand=["S7"],
        current_trick=["SA"],
        trick_leader="right",
    )

    result = simulate_immediate_trick_once_detailed(
        state=state,
        candidate_card="S7",
        left_hand_size=1,
        right_hand_size=1,
        use_basic_opponent_strategy=True,
    )

    assert result["trick"] == ["SA", "S7", "S8"]
    assert result["completed_trick"]["winner_player"] == "right"
    assert result["candidate_card_won"] is False
    assert result["local_side_won"] is True
    assert result["did_win"] is True


def test_detailed_result_counts_right_declarer_partner_win_as_local_win(monkeypatch) -> None:
    def fake_generate_random_opponent_hands(**_kwargs):
        return ["SA"], ["H7"]

    monkeypatch.setattr(
        "skat_ai.simulation.generate_random_opponent_hands",
        fake_generate_random_opponent_hands,
    )
    state = GameState(
        game_type="grand",
        player_role="defender",
        declarer_player="right",
        hand=["S8"],
        current_trick=["S7"],
        trick_leader="right",
    )

    result = simulate_immediate_trick_once_detailed(
        state=state,
        candidate_card="S8",
        left_hand_size=1,
        right_hand_size=1,
        use_basic_opponent_strategy=True,
    )

    assert result["trick"] == ["S7", "S8", "SA"]
    assert result["completed_trick"]["winner_player"] == "left"
    assert result["candidate_card_won"] is False
    assert result["local_side_won"] is True
    assert result["did_win"] is True


def test_detailed_result_counts_left_declarer_win_as_local_loss() -> None:
    state = GameState(
        game_type="grand",
        player_role="defender",
        declarer_player="left",
        hand=["S8"],
        current_trick=["SA", "S7"],
        trick_leader="left",
    )

    result = simulate_immediate_trick_once_detailed(
        state=state,
        candidate_card="S8",
        left_hand_size=0,
        right_hand_size=0,
        use_basic_opponent_strategy=True,
    )

    assert result["trick"] == ["SA", "S7", "S8"]
    assert result["completed_trick"]["winner_player"] == "left"
    assert result["candidate_card_won"] is False
    assert result["local_side_won"] is False
    assert result["did_win"] is False


def test_detailed_result_counts_right_declarer_win_as_local_loss(monkeypatch) -> None:
    def fake_generate_random_opponent_hands(**_kwargs):
        return ["S8"], ["H7"]

    monkeypatch.setattr(
        "skat_ai.simulation.generate_random_opponent_hands",
        fake_generate_random_opponent_hands,
    )
    state = GameState(
        game_type="grand",
        player_role="defender",
        declarer_player="right",
        hand=["S7"],
        current_trick=["SA"],
        trick_leader="right",
    )

    result = simulate_immediate_trick_once_detailed(
        state=state,
        candidate_card="S7",
        left_hand_size=1,
        right_hand_size=1,
        use_basic_opponent_strategy=True,
    )

    assert result["trick"] == ["SA", "S7", "S8"]
    assert result["completed_trick"]["winner_player"] == "right"
    assert result["candidate_card_won"] is False
    assert result["local_side_won"] is False
    assert result["did_win"] is False


def test_simulate_immediate_trick_once_detailed_returns_completed_three_card_trick() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9", "H10", "D7"],
        current_trick=["S7"],
        played_cards=[],
        skat=[],
    )

    result = simulate_immediate_trick_once_detailed(
        state=state,
        candidate_card="SA",
        left_hand_size=5,
        right_hand_size=5,
        random_generator=None,
        use_basic_opponent_strategy=True,
    )

    assert len(result["trick"]) == 3
    assert result["trick"][0] == "S7"
    assert result["trick"][1] == "SA"


def test_simulate_immediate_trick_once_detailed_returns_completed_trick_entry() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9", "H10", "D7"],
        current_trick=["S7"],
        played_cards=[],
        skat=[],
    )

    result = simulate_immediate_trick_once_detailed(
        state=state,
        candidate_card="SA",
        left_hand_size=5,
        right_hand_size=5,
        random_generator=None,
        use_basic_opponent_strategy=True,
    )

    completed_trick = result["completed_trick"]

    assert completed_trick["cards"] == result["trick"]
    assert completed_trick["winner_role"] in ["declarer", "defenders"]


def test_complete_trick_after_right_lead_uses_left_hand_for_third_card() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA"],
        current_trick=["S7"],
        trick_leader="right",
    )
    left_hand = ["S8", "H10"]
    right_hand = ["S9", "D10"]

    trick = complete_trick_after_candidate_card(
        state=state,
        candidate_card="SA",
        left_hand=left_hand,
        right_hand=right_hand,
        use_basic_opponent_strategy=True,
    )
    completed_trick = build_completed_trick_from_state_and_candidate(
        state=state,
        completed_trick_cards=trick,
    )

    assert trick == ["S7", "SA", "S8"]
    assert left_hand == ["H10"]
    assert right_hand == ["S9", "D10"]
    assert completed_trick["cards"] == ["S7", "SA", "S8"]
    assert completed_trick["players"] == ["right", "me", "left"]


def test_complete_trick_after_left_lead_local_third_keeps_opponent_hands() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA"],
        current_trick=["S7", "S8"],
        trick_leader="left",
    )
    left_hand = ["H10"]
    right_hand = ["S9"]

    trick = complete_trick_after_candidate_card(
        state=state,
        candidate_card="SA",
        left_hand=left_hand,
        right_hand=right_hand,
        use_basic_opponent_strategy=True,
    )
    completed_trick = build_completed_trick_from_state_and_candidate(
        state=state,
        completed_trick_cards=trick,
    )

    assert trick == ["S7", "S8", "SA"]
    assert left_hand == ["H10"]
    assert right_hand == ["S9"]
    assert completed_trick["players"] == ["left", "right", "me"]


def test_complete_trick_after_local_lead_uses_left_then_right_hands() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["S7"],
        current_trick=[],
        trick_leader="me",
    )
    left_hand = ["S8", "H10"]
    right_hand = ["S9", "D10"]

    trick = complete_trick_after_candidate_card(
        state=state,
        candidate_card="S7",
        left_hand=left_hand,
        right_hand=right_hand,
        use_basic_opponent_strategy=True,
    )
    completed_trick = build_completed_trick_from_state_and_candidate(
        state=state,
        completed_trick_cards=trick,
    )

    assert trick == ["S7", "S8", "S9"]
    assert left_hand == ["H10"]
    assert right_hand == ["D10"]
    assert completed_trick["players"] == ["me", "left", "right"]


def test_complete_trick_without_policy_keeps_legacy_basic_behavior() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["S7"],
        current_trick=[],
        trick_leader="me",
    )
    left_hand = ["S8", "S10"]
    right_hand = ["S9", "SA"]

    trick = complete_trick_after_candidate_card(
        state=state,
        candidate_card="S7",
        left_hand=left_hand,
        right_hand=right_hand,
        use_basic_opponent_strategy=True,
    )

    assert trick == ["S7", "S8", "S9"]
    assert left_hand == ["S10"]
    assert right_hand == ["SA"]


def test_complete_trick_without_policy_keeps_seeded_random_behavior() -> None:
    import random

    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["S7"],
        current_trick=[],
        trick_leader="me",
    )

    first_trick = complete_trick_after_candidate_card(
        state=state,
        candidate_card="S7",
        left_hand=["S8", "S10"],
        right_hand=["S9", "SA"],
        random_generator=random.Random(42),
        use_basic_opponent_strategy=False,
    )
    second_trick = complete_trick_after_candidate_card(
        state=state,
        candidate_card="S7",
        left_hand=["S8", "S10"],
        right_hand=["S9", "SA"],
        random_generator=random.Random(42),
        use_basic_opponent_strategy=False,
    )

    assert first_trick == second_trick


def test_explicit_lowest_response_policy_overrides_legacy_basic_play() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["H8"],
        current_trick=["S7"],
        trick_leader="right",
    )
    left_hand = ["H7", "CJ"]
    right_hand = ["S8"]

    trick = complete_trick_after_candidate_card(
        state=state,
        candidate_card="H8",
        left_hand=left_hand,
        right_hand=right_hand,
        use_basic_opponent_strategy=True,
        opponent_response_policy_by_player={
            "left": "lowest_point",
        },
    )

    assert trick == ["S7", "H8", "H7"]
    assert left_hand == ["CJ"]
    assert right_hand == ["S8"]


def test_explicit_response_policies_can_select_different_cards() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["S7"],
        current_trick=[],
        trick_leader="me",
    )
    lowest_left_hand = ["S8", "S10"]
    lowest_right_hand = ["S9", "SA"]
    highest_left_hand = ["S8", "S10"]
    highest_right_hand = ["S9", "SA"]

    lowest_trick = complete_trick_after_candidate_card(
        state=state,
        candidate_card="S7",
        left_hand=lowest_left_hand,
        right_hand=lowest_right_hand,
        use_basic_opponent_strategy=True,
        opponent_response_policy_by_player={
            "left": "lowest_point",
            "right": "lowest_point",
        },
    )
    highest_trick = complete_trick_after_candidate_card(
        state=state,
        candidate_card="S7",
        left_hand=highest_left_hand,
        right_hand=highest_right_hand,
        use_basic_opponent_strategy=True,
        opponent_response_policy_by_player={
            "left": "highest_point",
            "right": "highest_point",
        },
    )

    assert lowest_trick == ["S7", "S8", "S9"]
    assert highest_trick == ["S7", "S10", "SA"]
    assert lowest_trick != highest_trick
    assert lowest_trick[1] in get_legal_cards(
        hand=["S8", "S10"],
        current_trick=["S7"],
        game_type="grand",
    )
    assert highest_trick[2] in get_legal_cards(
        hand=["S9", "SA"],
        current_trick=["S7", "S10"],
        game_type="grand",
    )
    assert lowest_left_hand == ["S10"]
    assert lowest_right_hand == ["SA"]
    assert highest_left_hand == ["S8"]
    assert highest_right_hand == ["S9"]


def test_complete_trick_after_right_lead_uses_left_response_policy() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["S8"],
        current_trick=["S7"],
        trick_leader="right",
    )
    left_hand = ["S9", "SA"]
    right_hand = ["S10", "H7"]

    trick = complete_trick_after_candidate_card(
        state=state,
        candidate_card="S8",
        left_hand=left_hand,
        right_hand=right_hand,
        use_basic_opponent_strategy=True,
        opponent_response_policy_by_player={
            "left": "highest_point",
            "right": "lowest_point",
        },
    )
    completed_trick = build_completed_trick_from_state_and_candidate(
        state=state,
        completed_trick_cards=trick,
    )

    assert trick == ["S7", "S8", "SA"]
    assert left_hand == ["S9"]
    assert right_hand == ["S10", "H7"]
    assert completed_trick["players"] == ["right", "me", "left"]


def test_complete_trick_after_local_lead_uses_both_side_response_policies() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["S7"],
        current_trick=[],
        trick_leader="me",
    )
    left_hand = ["S8", "S10"]
    right_hand = ["S9", "SA"]

    trick = complete_trick_after_candidate_card(
        state=state,
        candidate_card="S7",
        left_hand=left_hand,
        right_hand=right_hand,
        use_basic_opponent_strategy=True,
        opponent_response_policy_by_player={
            "left": "lowest_point",
            "right": "highest_point",
        },
    )
    completed_trick = build_completed_trick_from_state_and_candidate(
        state=state,
        completed_trick_cards=trick,
    )

    assert trick == ["S7", "S8", "SA"]
    assert left_hand == ["S10"]
    assert right_hand == ["S9"]
    assert completed_trick["players"] == ["me", "left", "right"]


def test_unknown_one_card_leader_does_not_apply_side_response_policy() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["S8"],
        current_trick=["S7"],
        trick_leader="unknown",
    )
    left_hand = ["SA"]
    right_hand = ["S9", "S10"]

    trick = complete_trick_after_candidate_card(
        state=state,
        candidate_card="S8",
        left_hand=left_hand,
        right_hand=right_hand,
        use_basic_opponent_strategy=True,
        opponent_response_policy_by_player={
            "right": "highest_point",
        },
    )

    assert trick == ["S7", "S8", "S9"]
    assert left_hand == ["SA"]
    assert right_hand == ["S10"]


def test_simulate_immediate_trick_once_detailed_is_reproducible_with_seed() -> None:
    import random

    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9", "H10", "D7"],
        current_trick=["S7"],
        played_cards=[],
        skat=[],
    )

    first_result = simulate_immediate_trick_once_detailed(
        state=state,
        candidate_card="SA",
        left_hand_size=5,
        right_hand_size=5,
        random_generator=random.Random(42),
        use_basic_opponent_strategy=True,
    )

    second_result = simulate_immediate_trick_once_detailed(
        state=state,
        candidate_card="SA",
        left_hand_size=5,
        right_hand_size=5,
        random_generator=random.Random(42),
        use_basic_opponent_strategy=True,
    )

    assert first_result == second_result


def test_existing_boolean_simulation_uses_detailed_result_consistently() -> None:
    import random

    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9", "H10", "D7"],
        current_trick=["S7"],
        played_cards=[],
        skat=[],
    )

    detailed_result = simulate_immediate_trick_once_detailed(
        state=state,
        candidate_card="SA",
        left_hand_size=5,
        right_hand_size=5,
        random_generator=random.Random(42),
        use_basic_opponent_strategy=True,
    )

    boolean_result = simulate_immediate_trick_once(
        state=state,
        candidate_card="SA",
        left_hand_size=5,
        right_hand_size=5,
        random_generator=random.Random(42),
        use_basic_opponent_strategy=True,
    )

    assert boolean_result == detailed_result["did_win"]


def test_existing_points_simulation_uses_detailed_result_consistently() -> None:
    import random

    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9", "H10", "D7"],
        current_trick=["S7"],
        played_cards=[],
        skat=[],
    )

    detailed_result = simulate_immediate_trick_once_detailed(
        state=state,
        candidate_card="SA",
        left_hand_size=5,
        right_hand_size=5,
        random_generator=random.Random(42),
        use_basic_opponent_strategy=True,
    )

    did_win, trick_points = simulate_immediate_trick_once_with_points(
        state=state,
        candidate_card="SA",
        left_hand_size=5,
        right_hand_size=5,
        random_generator=random.Random(42),
        use_basic_opponent_strategy=True,
    )

    assert did_win == detailed_result["did_win"]
    assert trick_points == detailed_result["trick_points"]
