from skat_ai.card_selection import (
    choose_card_by_policy,
    choose_first_legal_card,
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