from skat_ai.card_selection import (
    calculate_expected_point_swing,
    choose_card_by_policy,
    choose_first_legal_card,
    choose_highest_expected_value_card,
    choose_highest_point_card,
    choose_lowest_point_card,
    get_legal_cards_for_state,
)
from skat_ai.game_state import GameState


def test_get_legal_cards_for_state_returns_legal_cards() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["H10", "SA", "S9"],
        current_trick=["S7"],
    )

    legal_cards = get_legal_cards_for_state(state)

    assert legal_cards == ["SA", "S9"]


def test_choose_first_legal_card_returns_first_legal_card() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["H10", "SA", "S9"],
        current_trick=["S7"],
    )

    selected_card = choose_first_legal_card(state)

    assert selected_card == "SA"


def test_choose_lowest_point_card_returns_lowest_point_legal_card() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9"],
        current_trick=["S7"],
    )

    selected_card = choose_lowest_point_card(state)

    assert selected_card == "S9"


def test_choose_highest_point_card_returns_highest_point_legal_card() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9"],
        current_trick=["S7"],
    )

    selected_card = choose_highest_point_card(state)

    assert selected_card == "SA"


def test_choose_card_by_policy_supports_first_legal() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["H10", "SA", "S9"],
        current_trick=["S7"],
    )

    selected_card = choose_card_by_policy(
        state=state,
        policy="first_legal",
    )

    assert selected_card == "SA"


def test_choose_card_by_policy_supports_lowest_point() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9"],
        current_trick=["S7"],
    )

    selected_card = choose_card_by_policy(
        state=state,
        policy="lowest_point",
    )

    assert selected_card == "S9"


def test_choose_card_by_policy_supports_highest_point() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9"],
        current_trick=["S7"],
    )

    selected_card = choose_card_by_policy(
        state=state,
        policy="highest_point",
    )

    assert selected_card == "SA"


def test_choose_card_by_policy_rejects_invalid_policy() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9"],
        current_trick=["S7"],
    )

    try:
        choose_card_by_policy(
            state=state,
            policy="invalid_policy",
        )
    except ValueError as error:
        assert "Invalid card selection policy" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_choose_first_legal_card_rejects_empty_hand() -> None:
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


def test_calculate_expected_point_swing() -> None:
    value = {
        "win_rate": 0.5,
        "average_trick_points": 12.0,
        "average_points_won": 8.0,
        "average_points_lost": 3.0,
    }

    assert calculate_expected_point_swing(value) == 5.0


def test_choose_highest_expected_value_card_returns_legal_card() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9"],
        current_trick=["S7"],
    )

    selected_card = choose_highest_expected_value_card(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        sample_count=20,
        random_seed=42,
        use_basic_opponent_strategy=True,
    )

    assert selected_card in ["SA", "S10", "S9"]


def test_choose_highest_expected_value_card_uses_null_objective() -> None:
    state = GameState(
        game_type="null",
        player_role="declarer",
        declarer_player="me",
        hand=["CA", "C7"],
        current_trick=["C10", "C9"],
        trick_leader="left",
        next_player="me",
    )

    selected_card = choose_highest_expected_value_card(
        state=state,
        left_hand_size=0,
        right_hand_size=0,
        sample_count=1,
        random_seed=42,
    )

    assert selected_card == "C7"


def test_explicit_point_policies_remain_point_based_for_null() -> None:
    state = GameState(
        game_type="null",
        player_role="declarer",
        declarer_player="me",
        hand=["CA", "C7"],
        current_trick=["C10", "C9"],
        trick_leader="left",
        next_player="me",
    )

    assert choose_highest_point_card(state) == "CA"
    assert choose_lowest_point_card(state) == "C7"


def test_choose_highest_expected_value_card_is_reproducible_with_seed() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9"],
        current_trick=["S7"],
    )

    first_selected_card = choose_highest_expected_value_card(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        sample_count=20,
        random_seed=42,
        use_basic_opponent_strategy=True,
    )

    second_selected_card = choose_highest_expected_value_card(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        sample_count=20,
        random_seed=42,
        use_basic_opponent_strategy=True,
    )

    assert first_selected_card == second_selected_card


def test_choose_card_by_policy_supports_highest_expected_value() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9"],
        current_trick=["S7"],
    )

    selected_card = choose_card_by_policy(
        state=state,
        policy="highest_expected_value",
        left_hand_size=5,
        right_hand_size=5,
        expected_value_sample_count=20,
        random_seed=42,
        use_basic_opponent_strategy=True,
    )

    assert selected_card in ["SA", "S10", "S9"]


def test_choose_card_by_policy_requires_hand_sizes_for_highest_expected_value() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9"],
        current_trick=["S7"],
    )

    try:
        choose_card_by_policy(
            state=state,
            policy="highest_expected_value",
            expected_value_sample_count=20,
            random_seed=42,
            use_basic_opponent_strategy=True,
        )
    except ValueError as error:
        assert "left_hand_size and right_hand_size" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")
