import pytest

from skat_ai.objective_utility import (
    calculate_expected_objective_utility,
    calculate_null_horizon_objective_utility,
    calculate_null_horizon_utility_from_states,
    calculate_null_trick_objective_utility,
)


def test_calculate_null_trick_objective_utility_for_local_declarer() -> None:
    assert calculate_null_trick_objective_utility("declarer", "defenders") == 1.0
    assert calculate_null_trick_objective_utility("declarer", "declarer") == 0.0


def test_calculate_null_trick_objective_utility_for_local_defender() -> None:
    assert calculate_null_trick_objective_utility("defender", "declarer") == 1.0
    assert calculate_null_trick_objective_utility("defender", "defenders") == 0.0


def test_calculate_null_trick_objective_utility_rejects_unknown_role() -> None:
    with pytest.raises(ValueError, match="player_role"):
        calculate_null_trick_objective_utility("unknown", "defenders")


def test_partner_and_local_defender_tricks_do_not_satisfy_null_defender_objective() -> None:
    assert calculate_null_trick_objective_utility("defender", "defenders") == 0.0
    assert calculate_null_horizon_objective_utility(
        player_role="defender",
        evaluated_completed_tricks=[
            {
                "cards": ["C7", "C8", "C9"],
                "winner_role": "defenders",
                "winner_player": "me",
            },
            {
                "cards": ["S7", "S8", "S9"],
                "winner_role": "defenders",
                "winner_player": "right",
            },
        ],
    ) == 0.0
    assert calculate_null_horizon_objective_utility(
        player_role="defender",
        evaluated_completed_tricks=[
            {
                "cards": ["C7", "C8", "C9"],
                "winner_role": "declarer",
                "winner_player": "left",
            }
        ],
    ) == 1.0


def test_calculate_null_horizon_utility_uses_all_evaluated_tricks() -> None:
    new_tricks = [
        {"cards": ["C7", "C8", "C9"], "winner_role": "defenders"},
        {"cards": ["S7", "S8", "S9"], "winner_role": "declarer"},
    ]

    assert calculate_null_horizon_objective_utility("declarer", new_tricks) == 0.0
    assert calculate_null_horizon_objective_utility("defender", new_tricks) == 1.0


def test_calculate_null_horizon_utility_excludes_pre_existing_tricks() -> None:
    initial_tricks = [
        {"cards": ["C7", "C8", "C9"], "winner_role": "declarer"},
    ]
    final_tricks = [
        *initial_tricks,
        {"cards": ["S7", "S8", "S9"], "winner_role": "defenders"},
    ]

    assert calculate_null_horizon_utility_from_states(
        player_role="declarer",
        initial_completed_tricks=initial_tricks,
        final_completed_tricks=final_tricks,
    ) == 1.0


def test_calculate_null_horizon_utility_uses_terminal_override() -> None:
    declarer_terminal_win = [
        {"cards": ["C7", "C8", "C9"], "winner_role": "defenders"}
        for _ in range(10)
    ]
    defender_terminal_win = [
        {"cards": ["C7", "C8", "C9"], "winner_role": "declarer"},
        *[
            {"cards": ["S7", "S8", "S9"], "winner_role": "defenders"}
            for _ in range(9)
        ],
    ]

    assert calculate_null_horizon_utility_from_states(
        player_role="declarer",
        initial_completed_tricks=[],
        final_completed_tricks=declarer_terminal_win,
    ) == 1.0
    assert calculate_null_horizon_utility_from_states(
        player_role="defender",
        initial_completed_tricks=[],
        final_completed_tricks=declarer_terminal_win,
    ) == 0.0
    assert calculate_null_horizon_utility_from_states(
        player_role="declarer",
        initial_completed_tricks=[],
        final_completed_tricks=defender_terminal_win,
    ) == 0.0
    assert calculate_null_horizon_utility_from_states(
        player_role="defender",
        initial_completed_tricks=[],
        final_completed_tricks=defender_terminal_win,
    ) == 1.0


def test_calculate_expected_objective_utility_keeps_suit_point_swing() -> None:
    value = {
        "win_rate": 0.0,
        "average_points_won": 9.0,
        "average_points_lost": 2.0,
    }

    assert calculate_expected_objective_utility("grand", "declarer", value) == 7.0


def test_calculate_expected_objective_utility_uses_null_utility() -> None:
    value = {
        "win_rate": 1.0,
        "average_points_won": 21.0,
        "average_points_lost": 0.0,
        "expected_objective_utility": 0.0,
    }

    assert calculate_expected_objective_utility("null", "declarer", value) == 0.0
