from skat_ai.game_state import GameState
from skat_ai.state_transition import (
    advance_state_after_detailed_trick,
    apply_completed_trick_to_points,
    determine_next_player_from_completed_trick,
    remove_card_from_hand,
)


def test_remove_card_from_hand_removes_one_card() -> None:
    hand = ["SA", "S10", "S9"]

    updated_hand = remove_card_from_hand(hand, "S10")

    assert updated_hand == ["SA", "S9"]


def test_remove_card_from_hand_does_not_mutate_original_hand() -> None:
    hand = ["SA", "S10", "S9"]

    updated_hand = remove_card_from_hand(hand, "S10")

    assert hand == ["SA", "S10", "S9"]
    assert updated_hand == ["SA", "S9"]


def test_remove_card_from_hand_rejects_missing_card() -> None:
    try:
        remove_card_from_hand(["SA", "S9"], "S10")
    except ValueError as error:
        assert "Card must be in hand" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_determine_next_player_when_declarer_wins() -> None:
    completed_trick = {
        "cards": ["S7", "SA", "S8"],
        "winner_role": "declarer",
    }

    next_player = determine_next_player_from_completed_trick(
        completed_trick=completed_trick,
        player_role="declarer",
    )

    assert next_player == "me"


def test_determine_next_player_when_declarer_loses() -> None:
    completed_trick = {
        "cards": ["S7", "S9", "SA"],
        "winner_role": "defenders",
    }

    next_player = determine_next_player_from_completed_trick(
        completed_trick=completed_trick,
        player_role="declarer",
    )

    assert next_player == "unknown"


def test_determine_next_player_when_defender_side_wins() -> None:
    completed_trick = {
        "cards": ["S7", "SA", "S8"],
        "winner_role": "defenders",
    }

    next_player = determine_next_player_from_completed_trick(
        completed_trick=completed_trick,
        player_role="defender",
    )

    assert next_player == "me"


def test_apply_completed_trick_to_points_adds_points_to_declarer() -> None:
    completed_trick = {
        "cards": ["CA", "C10", "CK"],
        "winner_role": "declarer",
    }

    declarer_points, defender_points = apply_completed_trick_to_points(
        declarer_points=10,
        defender_points=5,
        completed_trick=completed_trick,
    )

    assert declarer_points == 35
    assert defender_points == 5


def test_apply_completed_trick_to_points_adds_points_to_defenders() -> None:
    completed_trick = {
        "cards": ["CA", "C10", "CK"],
        "winner_role": "defenders",
    }

    declarer_points, defender_points = apply_completed_trick_to_points(
        declarer_points=10,
        defender_points=5,
        completed_trick=completed_trick,
    )

    assert declarer_points == 10
    assert defender_points == 30


def test_advance_state_after_detailed_trick_removes_candidate_card() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9"],
        current_trick=["S7"],
    )

    detailed_result = {
        "trick": ["S7", "SA", "S8"],
        "did_win": True,
        "trick_points": 11,
        "completed_trick": {
            "cards": ["S7", "SA", "S8"],
            "winner_role": "declarer",
        },
    }

    next_state = advance_state_after_detailed_trick(
        state=state,
        candidate_card="SA",
        detailed_result=detailed_result,
    )

    assert next_state.hand == ["S10", "S9"]


def test_advance_state_after_detailed_trick_clears_current_trick() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9"],
        current_trick=["S7"],
    )

    detailed_result = {
        "trick": ["S7", "SA", "S8"],
        "did_win": True,
        "trick_points": 11,
        "completed_trick": {
            "cards": ["S7", "SA", "S8"],
            "winner_role": "declarer",
        },
    }

    next_state = advance_state_after_detailed_trick(
        state=state,
        candidate_card="SA",
        detailed_result=detailed_result,
    )

    assert next_state.current_trick == []


def test_advance_state_after_detailed_trick_appends_completed_trick() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9"],
        current_trick=["S7"],
        completed_tricks=[
            {
                "cards": ["CA", "C10", "CK"],
                "winner_role": "defenders",
            }
        ],
    )

    detailed_result = {
        "trick": ["S7", "SA", "S8"],
        "did_win": True,
        "trick_points": 11,
        "completed_trick": {
            "cards": ["S7", "SA", "S8"],
            "winner_role": "declarer",
        },
    }

    next_state = advance_state_after_detailed_trick(
        state=state,
        candidate_card="SA",
        detailed_result=detailed_result,
    )

    assert next_state.completed_tricks == [
        {
            "cards": ["CA", "C10", "CK"],
            "winner_role": "defenders",
        },
        {
            "cards": ["S7", "SA", "S8"],
            "winner_role": "declarer",
        },
    ]


def test_advance_state_after_detailed_trick_updates_points() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9"],
        current_trick=["S7"],
        declarer_points=10,
        defender_points=5,
    )

    detailed_result = {
        "trick": ["S7", "SA", "S8"],
        "did_win": True,
        "trick_points": 11,
        "completed_trick": {
            "cards": ["S7", "SA", "S8"],
            "winner_role": "declarer",
        },
    }

    next_state = advance_state_after_detailed_trick(
        state=state,
        candidate_card="SA",
        detailed_result=detailed_result,
    )

    assert next_state.declarer_points == 21
    assert next_state.defender_points == 5


def test_advance_state_after_detailed_trick_sets_next_player() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9"],
        current_trick=["S7"],
    )

    detailed_result = {
        "trick": ["S7", "SA", "S8"],
        "did_win": True,
        "trick_points": 11,
        "completed_trick": {
            "cards": ["S7", "SA", "S8"],
            "winner_role": "declarer",
        },
    }

    next_state = advance_state_after_detailed_trick(
        state=state,
        candidate_card="SA",
        detailed_result=detailed_result,
    )

    assert next_state.next_player == "me"
    assert next_state.trick_leader == "me"


def test_advance_state_after_detailed_trick_does_not_mutate_original_state() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        hand=["SA", "S10", "S9"],
        current_trick=["S7"],
        completed_tricks=[],
        declarer_points=0,
        defender_points=0,
    )

    detailed_result = {
        "trick": ["S7", "SA", "S8"],
        "did_win": True,
        "trick_points": 11,
        "completed_trick": {
            "cards": ["S7", "SA", "S8"],
            "winner_role": "declarer",
        },
    }

    next_state = advance_state_after_detailed_trick(
        state=state,
        candidate_card="SA",
        detailed_result=detailed_result,
    )

    assert state.hand == ["SA", "S10", "S9"]
    assert state.current_trick == ["S7"]
    assert state.completed_tricks == []
    assert state.declarer_points == 0
    assert state.defender_points == 0

    assert next_state.hand == ["S10", "S9"]
    assert next_state.current_trick == []
    assert next_state.completed_tricks == [
        {
            "cards": ["S7", "SA", "S8"],
            "winner_role": "declarer",
        }
    ]