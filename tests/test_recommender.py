from skat_ai.game_state import GameState
from skat_ai.recommender import (
    classify_higher_cards,
    is_highest_remaining_card_in_suit,
    recommend_card,
    recommend_card_by_expected_value,
    recommend_card_by_simulation,
    recommend_card_for_state,
    score_leading_card,
)


def test_recommend_card_wins_with_lowest_point_winning_card() -> None:
    hand = ["CJ", "SA", "S9", "H10", "D7"]
    current_trick = ["S10"]

    recommended_card, reason = recommend_card(hand, current_trick, "grand")

    assert recommended_card == "SA"
    assert "win" in reason.lower()


def test_recommend_card_discards_lowest_points_when_cannot_win() -> None:
    hand = ["S9", "S7", "H10", "D7"]
    current_trick = ["SA"]

    recommended_card, reason = recommend_card(hand, current_trick, "grand")

    assert recommended_card == "S9"
    assert "lowest-point" in reason.lower()


def test_recommend_card_prefers_highest_remaining_suit_card_when_leading() -> None:
    hand = ["CJ", "SA", "S9", "H10", "D7"]
    current_trick = []

    recommended_card, reason = recommend_card(hand, current_trick, "grand")

    assert recommended_card == "SA"
    assert "highest leading score" in reason.lower()


def test_recommend_card_plays_lowest_points_when_leading_without_strong_ace() -> None:
    hand = ["CJ", "S9", "H10", "D7"]
    current_trick = []

    recommended_card, reason = recommend_card(hand, current_trick, "grand")

    assert recommended_card == "S9"
    assert "lowest-point" in reason.lower()


def test_ten_is_highest_remaining_when_ace_was_played() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["S10", "S9", "H10"],
        current_trick=[],
        played_cards=["SA"],
    )

    assert is_highest_remaining_card_in_suit("S10", state) is True


def test_ten_is_not_highest_remaining_when_ace_was_not_played() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["S10", "S9", "H10"],
        current_trick=[],
        played_cards=[],
    )

    assert is_highest_remaining_card_in_suit("S10", state) is False


def test_recommend_card_leads_ten_when_ace_was_played() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["S10", "S9", "H10"],
        current_trick=[],
        played_cards=["SA"],
    )

    recommended_card, reason = recommend_card_for_state(state)

    assert recommended_card == "S10"
    assert "highest leading score" in reason.lower()


def test_recommend_card_does_not_lead_ten_when_ace_was_not_played() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["S10", "S9", "H10"],
        current_trick=[],
        played_cards=[],
    )

    recommended_card, reason = recommend_card_for_state(state)

    assert recommended_card != "S10"


def test_classify_higher_cards_detects_higher_card_in_own_hand() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9"],
        current_trick=[],
        played_cards=[],
    )

    classification = classify_higher_cards("S10", state)

    assert classification["played"] == []
    assert classification["in_hand"] == ["SA"]
    assert classification["unknown"] == []


def test_classify_higher_cards_detects_unknown_higher_card() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["S10", "S9"],
        current_trick=[],
        played_cards=[],
    )

    classification = classify_higher_cards("S10", state)

    assert classification["played"] == []
    assert classification["in_hand"] == []
    assert classification["unknown"] == ["SA"]


def test_ten_is_highest_remaining_when_ace_is_in_own_hand() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9"],
        current_trick=[],
        played_cards=[],
    )

    assert is_highest_remaining_card_in_suit("S10", state) is True


def test_king_is_not_highest_remaining_when_ten_is_unknown() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SK", "S9"],
        current_trick=[],
        played_cards=["SA"],
    )

    assert is_highest_remaining_card_in_suit("SK", state) is False


def test_king_is_highest_remaining_when_ace_and_ten_are_safe() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["S10", "SK", "S9"],
        current_trick=[],
        played_cards=["SA"],
    )

    assert is_highest_remaining_card_in_suit("SK", state) is True


def test_score_leading_card_rewards_safe_high_card() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S9"],
        current_trick=[],
        played_cards=[],
    )

    assert score_leading_card("SA", state) == 111


def test_score_leading_card_penalizes_trump_when_leading() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["CJ", "S9"],
        current_trick=[],
        played_cards=[],
    )

    assert score_leading_card("CJ", state) == -20


def test_score_leading_card_rewards_ten_when_ace_is_safe() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["S10", "S9"],
        current_trick=[],
        played_cards=["SA"],
    )

    assert score_leading_card("S10", state) == 110


def test_recommend_card_by_simulation_returns_legal_card() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9"],
        current_trick=[],
        played_cards=[],
        skat=[],
    )

    recommended_card, reason, win_rates = recommend_card_by_simulation(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        sample_count=20,
        random_seed=42,
    )

    assert recommended_card in ["SA", "S10", "S9"]
    assert recommended_card in win_rates
    assert "highest estimated immediate trick win rate" in reason.lower()


def test_recommend_card_by_simulation_is_reproducible_with_seed() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9", "H10", "D7"],
        current_trick=[],
        played_cards=[],
        skat=[],
    )

    first_result = recommend_card_by_simulation(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        sample_count=100,
        random_seed=42,
    )

    second_result = recommend_card_by_simulation(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        sample_count=100,
        random_seed=42,
    )

    assert first_result == second_result


def test_recommend_card_by_simulation_supports_basic_opponent_strategy_flag() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9"],
        current_trick=[],
        played_cards=[],
        skat=[],
    )

    recommended_card, reason, win_rates = recommend_card_by_simulation(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        sample_count=20,
        random_seed=42,
        use_basic_opponent_strategy=True,
    )

    assert recommended_card in ["SA", "S10", "S9"]
    assert recommended_card in win_rates
    assert "highest estimated immediate trick win rate" in reason.lower()


def test_recommend_card_by_expected_value_returns_legal_card() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9"],
        current_trick=[],
        played_cards=[],
        skat=[],
    )

    recommended_card, reason, values = recommend_card_by_expected_value(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        sample_count=20,
        random_seed=42,
        use_basic_opponent_strategy=True,
    )

    assert recommended_card in ["SA", "S10", "S9"]
    assert recommended_card in values
    assert "highest estimated immediate expected point swing" in reason.lower()


def test_recommend_card_by_expected_value_is_reproducible_with_seed() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9"],
        current_trick=[],
        played_cards=[],
        skat=[],
    )

    first_result = recommend_card_by_expected_value(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        sample_count=20,
        random_seed=42,
        use_basic_opponent_strategy=True,
    )

    second_result = recommend_card_by_expected_value(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        sample_count=20,
        random_seed=42,
        use_basic_opponent_strategy=True,
    )

    assert first_result == second_result


def test_recommend_card_by_expected_value_supports_second_position() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9", "H10", "D7"],
        current_trick=["S7"],
        played_cards=[],
        skat=[],
    )

    recommended_card, reason, values = recommend_card_by_expected_value(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        sample_count=20,
        random_seed=42,
        use_basic_opponent_strategy=True,
    )

    assert recommended_card in ["SA", "S10", "S9"]
    assert recommended_card in values
    assert "expected point swing" in reason.lower()


def test_recommend_card_by_expected_value_supports_third_position() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9", "H10", "D7"],
        current_trick=["S7", "S8"],
        played_cards=[],
        skat=[],
    )

    recommended_card, reason, values = recommend_card_by_expected_value(
        state=state,
        left_hand_size=5,
        right_hand_size=5,
        sample_count=20,
        random_seed=42,
        use_basic_opponent_strategy=True,
    )

    assert recommended_card in ["SA", "S10", "S9"]
    assert recommended_card in values
    assert "expected point swing" in reason.lower()
