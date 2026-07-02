from skat_ai.game_history import build_score_summary
from skat_ai.game_state import GameState
from skat_ai.simulation import simulate_immediate_trick_once_detailed
from skat_ai.state_transition import (
    advance_state_after_detailed_trick,
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


def test_determine_next_player_when_only_defender_side_wins_is_unknown() -> None:
    completed_trick = {
        "cards": ["S7", "SA", "S8"],
        "winner_role": "defenders",
    }

    next_player = determine_next_player_from_completed_trick(
        completed_trick=completed_trick,
        player_role="defender",
    )

    assert next_player == "unknown"


def test_determine_next_player_when_declarer_role_has_concrete_declarer() -> None:
    completed_trick = {
        "cards": ["S7", "SA", "S8"],
        "winner_role": "declarer",
    }

    next_player = determine_next_player_from_completed_trick(
        completed_trick=completed_trick,
        player_role="defender",
        declarer_player="right",
    )

    assert next_player == "right"


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


def test_advance_state_after_detailed_trick_preserves_explicit_points() -> None:
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

    assert next_state.declarer_points == 10
    assert next_state.defender_points == 5


def test_advance_state_after_detailed_trick_counts_new_declarer_trick_once() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        declarer_player="me",
        hand=["CA"],
        current_trick=["C10", "CK"],
        trick_leader="left",
        next_player="me",
    )
    detailed_result = simulate_immediate_trick_once_detailed(
        state=state,
        candidate_card="CA",
        left_hand_size=0,
        right_hand_size=0,
    )

    next_state = advance_state_after_detailed_trick(
        state=state,
        candidate_card="CA",
        detailed_result=detailed_result,
    )
    score_summary = build_score_summary(next_state)

    assert detailed_result["trick_points"] == 25
    assert next_state.declarer_points == 0
    assert next_state.defender_points == 0
    assert next_state.completed_tricks == [
        {
            "cards": ["C10", "CK", "CA"],
            "players": ["left", "right", "me"],
            "winner_role": "declarer",
            "winner_player": "me",
        }
    ]
    assert score_summary["explicit_declarer_points"] == 0
    assert score_summary["completed_trick_declarer_points"] == 25
    assert score_summary["total_declarer_points"] == 25


def test_advance_state_after_detailed_trick_preserves_existing_explicit_points() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        declarer_player="me",
        hand=["CA"],
        current_trick=["C10", "CK"],
        trick_leader="left",
        declarer_points=20,
        defender_points=10,
        next_player="me",
    )
    detailed_result = simulate_immediate_trick_once_detailed(
        state=state,
        candidate_card="CA",
        left_hand_size=0,
        right_hand_size=0,
    )

    next_state = advance_state_after_detailed_trick(
        state=state,
        candidate_card="CA",
        detailed_result=detailed_result,
    )
    score_summary = build_score_summary(next_state)

    assert next_state.declarer_points == 20
    assert next_state.defender_points == 10
    assert len(next_state.completed_tricks) == 1
    assert score_summary["explicit_declarer_points"] == 20
    assert score_summary["explicit_defender_points"] == 10
    assert score_summary["completed_trick_declarer_points"] == 25
    assert score_summary["total_declarer_points"] == 45
    assert score_summary["total_defender_points"] == 10


def test_advance_state_after_detailed_trick_counts_existing_completed_tricks_once() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        declarer_player="me",
        hand=["CA"],
        current_trick=["C10", "CK"],
        trick_leader="left",
        completed_tricks=[
            {
                "cards": ["SA", "S10", "SK"],
                "winner_role": "declarer",
            }
        ],
        declarer_points=20,
        defender_points=10,
        next_player="me",
    )
    detailed_result = simulate_immediate_trick_once_detailed(
        state=state,
        candidate_card="CA",
        left_hand_size=0,
        right_hand_size=0,
    )

    next_state = advance_state_after_detailed_trick(
        state=state,
        candidate_card="CA",
        detailed_result=detailed_result,
    )
    score_summary = build_score_summary(next_state)

    assert next_state.declarer_points == 20
    assert next_state.defender_points == 10
    assert len(next_state.completed_tricks) == 2
    assert score_summary["explicit_declarer_points"] == 20
    assert score_summary["completed_trick_declarer_points"] == 50
    assert score_summary["total_declarer_points"] == 70
    assert score_summary["total_defender_points"] == 10


def test_advance_state_after_detailed_trick_counts_new_defender_trick_once() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        declarer_player="me",
        hand=["C7"],
        current_trick=["CA", "C10"],
        trick_leader="left",
        defender_points=6,
        next_player="me",
    )
    detailed_result = simulate_immediate_trick_once_detailed(
        state=state,
        candidate_card="C7",
        left_hand_size=0,
        right_hand_size=0,
    )

    next_state = advance_state_after_detailed_trick(
        state=state,
        candidate_card="C7",
        detailed_result=detailed_result,
    )
    score_summary = build_score_summary(next_state)

    assert detailed_result["trick_points"] == 21
    assert next_state.defender_points == 6
    assert next_state.completed_tricks[-1]["winner_role"] == "defenders"
    assert score_summary["explicit_defender_points"] == 6
    assert score_summary["completed_trick_defender_points"] == 21
    assert score_summary["total_defender_points"] == 27


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


def test_advance_state_after_detailed_trick_preserves_declarer_player() -> None:
    state = GameState(
        game_type="grand",
        player_role="defender",
        declarer_player="left",
        hand=["SA", "S10", "S9"],
        current_trick=["S7"],
    )

    detailed_result = {
        "trick": ["S7", "SA", "S8"],
        "did_win": True,
        "trick_points": 11,
        "completed_trick": {
            "cards": ["S7", "SA", "S8"],
            "winner_role": "defenders",
            "winner_player": "me",
        },
    }

    next_state = advance_state_after_detailed_trick(
        state=state,
        candidate_card="SA",
        detailed_result=detailed_result,
    )

    assert next_state.declarer_player == "left"


def test_determine_next_player_uses_winner_player_when_available() -> None:
    completed_trick = {
        "cards": ["S7", "S9", "SJ"],
        "players": ["left", "me", "right"],
        "winner_role": "defenders",
        "winner_player": "right",
    }

    next_player = determine_next_player_from_completed_trick(
        completed_trick=completed_trick,
        player_role="declarer",
    )

    assert next_player == "right"
