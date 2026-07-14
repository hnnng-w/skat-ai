import pytest

from skat_ai.final_settlement import (
    build_final_settlement_summary,
    calculate_basic_settlement_score,
    get_missing_final_settlement_inputs,
    is_declarer_base_contract_winner,
    is_overbid_settlement_supported,
)
from skat_ai.game_declaration import GameDeclaration
from skat_ai.game_history import build_score_summary as build_state_score_summary
from skat_ai.game_result import build_game_result_summary_from_score_summary
from skat_ai.game_state import GameState
from skat_ai.game_value import build_game_value_summary
from skat_ai.simulation_step import simulate_and_advance_once


def build_score_summary(
    declarer_points: int,
    defender_points: int,
) -> dict[str, int]:
    return {
        "explicit_declarer_points": 0,
        "explicit_defender_points": 0,
        "completed_trick_declarer_points": declarer_points,
        "completed_trick_defender_points": defender_points,
        "total_declarer_points": declarer_points,
        "total_defender_points": defender_points,
    }


def build_completed_null_tricks(winner_roles: list[str]) -> list[dict[str, object]]:
    return [
        {
            "cards": ["C7", "C8", "C9"],
            "winner_role": winner_role,
        }
        for winner_role in winner_roles
    ]


def build_completed_schwarz_tricks(winner_roles: list[str]) -> list[dict[str, object]]:
    return [
        {
            "cards": ["C7", "C8", "C9"],
            "winner_role": winner_role,
        }
        for winner_role in winner_roles
    ]


def build_nine_declarer_tricks_before_final_clubs_trick() -> list[dict[str, object]]:
    return [
        {"cards": ["CJ", "CQ", "C9"], "winner_role": "declarer"},
        {"cards": ["SJ", "SA", "S10"], "winner_role": "declarer"},
        {"cards": ["SK", "SQ", "S9"], "winner_role": "declarer"},
        {"cards": ["S8", "S7", "HJ"], "winner_role": "declarer"},
        {"cards": ["HA", "H10", "HK"], "winner_role": "declarer"},
        {"cards": ["HQ", "H9", "H8"], "winner_role": "declarer"},
        {"cards": ["H7", "DJ", "DA"], "winner_role": "declarer"},
        {"cards": ["D10", "DK", "DQ"], "winner_role": "declarer"},
        {"cards": ["D9", "D8", "D7"], "winner_role": "declarer"},
    ]


def build_suit_game_value_summary(
    game_value: int = 72,
    schneider_announced: bool = False,
    schwarz_announced: bool = False,
) -> dict:
    return {
        "game_value": game_value,
        "base_value": 24,
        "is_null_game": False,
        "details": {
            "schneider_announced": schneider_announced,
            "schwarz_announced": schwarz_announced,
        },
    }


def build_complete_suit_result_summary(
    winner: str = "declarer",
    effective_schneider_status: str = "none",
    effective_schwarz_status: str = "none",
    game_end_reason: str = "normal_completion",
) -> dict:
    return {
        "is_complete": True,
        "winner": winner,
        "effective_schneider_status": effective_schneider_status,
        "effective_schwarz_status": effective_schwarz_status,
        "game_end_reason": game_end_reason,
    }


def build_completed_null_result_summary(
    winner_roles: list[str],
    declarer_points: int,
    defender_points: int,
) -> dict:
    return build_game_result_summary_from_score_summary(
        score_summary=build_score_summary(declarer_points, defender_points),
        game_type="null",
        completed_tricks=build_completed_null_tricks(winner_roles),
        game_end_reason="normal_completion",
    )


def build_null_game_value_summary() -> dict:
    return build_game_value_summary(GameDeclaration(game_type="null"))


def build_null_variant_game_value_summary(
    hand_game: bool,
    ouvert: bool,
) -> dict:
    return build_game_value_summary(
        GameDeclaration(
            game_type="null",
            hand_game=hand_game,
            ouvert=ouvert,
        )
    )


def test_get_missing_final_settlement_inputs_returns_none_when_complete() -> None:
    game_value_summary = {
        "game_value": 72,
    }
    game_result_summary = {
        "is_complete": True,
    }

    assert get_missing_final_settlement_inputs(
        game_value_summary=game_value_summary,
        game_result_summary=game_result_summary,
    ) == []


def test_get_missing_final_settlement_inputs_detects_incomplete_card_points() -> None:
    game_value_summary = {
        "game_value": 72,
    }
    game_result_summary = {
        "is_complete": False,
    }

    assert get_missing_final_settlement_inputs(
        game_value_summary=game_value_summary,
        game_result_summary=game_result_summary,
    ) == ["complete_card_points"]


def test_get_missing_final_settlement_inputs_detects_missing_game_value() -> None:
    game_value_summary = {
        "game_value": None,
    }
    game_result_summary = {
        "is_complete": True,
    }

    assert get_missing_final_settlement_inputs(
        game_value_summary=game_value_summary,
        game_result_summary=game_result_summary,
    ) == ["game_value"]


def test_get_missing_final_settlement_inputs_detects_multiple_missing_inputs() -> None:
    game_value_summary = {
        "game_value": None,
    }
    game_result_summary = {
        "is_complete": False,
    }

    assert get_missing_final_settlement_inputs(
        game_value_summary=game_value_summary,
        game_result_summary=game_result_summary,
    ) == ["complete_card_points", "game_value"]


def test_is_declarer_base_contract_winner_returns_none_when_incomplete() -> None:
    game_result_summary = {
        "is_complete": False,
        "winner": "undecided",
    }

    assert is_declarer_base_contract_winner(game_result_summary) is None


def test_is_declarer_base_contract_winner_returns_true() -> None:
    game_result_summary = {
        "is_complete": True,
        "winner": "declarer",
    }

    assert is_declarer_base_contract_winner(game_result_summary) is True


def test_is_declarer_base_contract_winner_returns_false() -> None:
    game_result_summary = {
        "is_complete": True,
        "winner": "defenders",
    }

    assert is_declarer_base_contract_winner(game_result_summary) is False


def test_is_declarer_base_contract_winner_returns_none_when_undecided() -> None:
    game_result_summary = {
        "is_complete": True,
        "winner": "undecided",
    }

    assert is_declarer_base_contract_winner(game_result_summary) is None


def test_calculate_basic_settlement_score_for_declarer_win() -> None:
    assert calculate_basic_settlement_score(
        game_value=72,
        declarer_won_by_card_points=True,
    ) == 72


def test_calculate_basic_settlement_score_for_declarer_loss() -> None:
    assert calculate_basic_settlement_score(
        game_value=72,
        declarer_won_by_card_points=False,
    ) == -144


def test_build_final_settlement_summary_incomplete() -> None:
    game_value_summary = {
        "game_value": None,
    }
    game_result_summary = {
        "is_complete": False,
        "winner": "undecided",
    }

    summary = build_final_settlement_summary(
        game_value_summary=game_value_summary,
        game_result_summary=game_result_summary,
    )

    assert summary["is_complete"] is False
    assert summary["missing_inputs"] == ["complete_card_points", "game_value"]
    assert summary["declarer_won_by_card_points"] is None
    assert summary["winner"] is None
    assert summary["game_value"] is None
    assert summary["effective_game_value"] is None
    assert summary["bid_value"] is None
    assert summary["settlement_score"] is None
    assert summary["is_loss"] is None
    assert summary["is_overbid"] is None
    assert summary["overbid_margin"] is None
    assert summary["overbid_status"] == "unknown"
    assert summary["overbid_required_game_value"] is None
    assert summary["notes"] == [
        "Settlement score uses simplified Skat logic.",
        "Lost declarer games are counted as -2 * effective_game_value.",
        (
            "Overbid settlement is supported for suit and grand games when "
            "required_game_value is available."
        ),
    ]


def test_build_final_settlement_summary_complete_declarer_win() -> None:
    game_value_summary = {
        "game_value": 72,
    }
    game_result_summary = {
        "is_complete": True,
        "winner": "declarer",
    }

    summary = build_final_settlement_summary(
        game_value_summary=game_value_summary,
        game_result_summary=game_result_summary,
    )

    assert summary["is_complete"] is True
    assert summary["missing_inputs"] == []
    assert summary["declarer_won_by_card_points"] is True
    assert summary["winner"] == "declarer"
    assert summary["game_value"] == 72
    assert summary["effective_game_value"] == 72
    assert summary["bid_value"] is None
    assert summary["settlement_score"] == 72
    assert summary["is_loss"] is False
    assert summary["is_overbid"] is None
    assert summary["overbid_margin"] is None
    assert summary["overbid_status"] == "unknown"
    assert summary["overbid_required_game_value"] is None


def test_final_trick_completion_counts_points_once_for_result_and_settlement() -> None:
    state = GameState(
        game_type="grand",
        player_role="declarer",
        declarer_player="me",
        hand=["CA"],
        current_trick=["C10", "CK"],
        trick_leader="left",
        completed_tricks=build_nine_declarer_tricks_before_final_clubs_trick(),
        next_player="me",
    )

    result = simulate_and_advance_once(
        state=state,
        candidate_card="CA",
        left_hand_size=0,
        right_hand_size=0,
    )
    final_state = result["next_state"]
    score_summary = build_state_score_summary(final_state)
    game_result_summary = build_game_result_summary_from_score_summary(
        score_summary=score_summary,
        game_type="grand",
        completed_tricks=final_state.completed_tricks,
        game_end_reason="normal_completion",
    )
    settlement_summary = build_final_settlement_summary(
        game_value_summary=build_suit_game_value_summary(),
        game_result_summary=game_result_summary,
        completed_tricks=final_state.completed_tricks,
    )

    assert len(final_state.completed_tricks) == 10
    assert final_state.declarer_points == 0
    assert score_summary["completed_trick_declarer_points"] == 120
    assert score_summary["total_declarer_points"] == 120
    assert score_summary["total_defender_points"] == 0
    assert game_result_summary["is_complete"] is True
    assert game_result_summary["winner"] == "declarer"
    assert game_result_summary["effective_schneider_status"] == (
        "declarer_made_schneider"
    )
    assert game_result_summary["effective_schwarz_status"] == "declarer_made_schwarz"
    assert settlement_summary["effective_game_value"] == 120
    assert settlement_summary["settlement_score"] == 120


def test_build_final_settlement_summary_complete_declarer_loss() -> None:
    game_value_summary = {
        "game_value": 72,
    }
    game_result_summary = {
        "is_complete": True,
        "winner": "defenders",
    }

    summary = build_final_settlement_summary(
        game_value_summary=game_value_summary,
        game_result_summary=game_result_summary,
    )

    assert summary["is_complete"] is True
    assert summary["missing_inputs"] == []
    assert summary["declarer_won_by_card_points"] is False
    assert summary["winner"] == "defenders"
    assert summary["game_value"] == 72
    assert summary["effective_game_value"] == 72
    assert summary["bid_value"] is None
    assert summary["settlement_score"] == -144
    assert summary["is_loss"] is True
    assert summary["is_overbid"] is None
    assert summary["overbid_margin"] is None
    assert summary["overbid_status"] == "unknown"
    assert summary["overbid_required_game_value"] is None


def test_build_final_settlement_summary_for_completed_null_win() -> None:
    summary = build_final_settlement_summary(
        game_value_summary=build_null_game_value_summary(),
        game_result_summary=build_completed_null_result_summary(
            winner_roles=["defenders"] * 10,
            declarer_points=0,
            defender_points=120,
        ),
    )

    assert summary["is_complete"] is True
    assert summary["missing_inputs"] == []
    assert summary["winner"] == "declarer"
    assert summary["declarer_won_by_card_points"] is True
    assert summary["game_value"] == 23
    assert summary["effective_game_value"] == 23
    assert summary["settlement_score"] == 23
    assert summary["is_loss"] is False


def test_build_final_settlement_summary_for_completed_null_zero_point_loss() -> None:
    summary = build_final_settlement_summary(
        game_value_summary=build_null_game_value_summary(),
        game_result_summary=build_completed_null_result_summary(
            winner_roles=["declarer", *["defenders"] * 9],
            declarer_points=0,
            defender_points=120,
        ),
    )

    assert summary["is_complete"] is True
    assert summary["winner"] == "defenders"
    assert summary["declarer_won_by_card_points"] is False
    assert summary["game_value"] == 23
    assert summary["effective_game_value"] == 23
    assert summary["settlement_score"] == -46
    assert summary["is_loss"] is True


def test_completed_null_losses_ignore_declarer_trick_card_points() -> None:
    zero_point_loss = build_final_settlement_summary(
        game_value_summary=build_null_game_value_summary(),
        game_result_summary=build_completed_null_result_summary(
            winner_roles=["declarer", *["defenders"] * 9],
            declarer_points=0,
            defender_points=120,
        ),
    )
    point_bearing_loss = build_final_settlement_summary(
        game_value_summary=build_null_game_value_summary(),
        game_result_summary=build_completed_null_result_summary(
            winner_roles=["declarer", *["defenders"] * 9],
            declarer_points=70,
            defender_points=50,
        ),
    )

    assert zero_point_loss["winner"] == "defenders"
    assert point_bearing_loss["winner"] == "defenders"
    assert zero_point_loss["is_loss"] is True
    assert point_bearing_loss["is_loss"] is True
    assert zero_point_loss["settlement_score"] == -46
    assert point_bearing_loss["settlement_score"] == -46


@pytest.mark.parametrize(
    ("hand_game", "ouvert", "expected_game_value"),
    [
        (False, False, 23),
        (True, False, 35),
        (False, True, 46),
        (True, True, 59),
    ],
)
def test_completed_null_variant_win_settlement_uses_fixed_game_value(
    hand_game: bool,
    ouvert: bool,
    expected_game_value: int,
) -> None:
    summary = build_final_settlement_summary(
        game_value_summary=build_null_variant_game_value_summary(
            hand_game=hand_game,
            ouvert=ouvert,
        ),
        game_result_summary=build_completed_null_result_summary(
            winner_roles=["defenders"] * 10,
            declarer_points=0,
            defender_points=120,
        ),
    )

    assert summary["is_complete"] is True
    assert summary["winner"] == "declarer"
    assert summary["game_value"] == expected_game_value
    assert summary["effective_game_value"] == expected_game_value
    assert summary["settlement_score"] == expected_game_value
    assert summary["is_loss"] is False


@pytest.mark.parametrize(
    ("hand_game", "ouvert", "expected_game_value"),
    [
        (False, False, 23),
        (True, False, 35),
        (False, True, 46),
        (True, True, 59),
    ],
)
def test_completed_null_variant_loss_settlement_uses_fixed_game_value(
    hand_game: bool,
    ouvert: bool,
    expected_game_value: int,
) -> None:
    summary = build_final_settlement_summary(
        game_value_summary=build_null_variant_game_value_summary(
            hand_game=hand_game,
            ouvert=ouvert,
        ),
        game_result_summary=build_completed_null_result_summary(
            winner_roles=["declarer", *["defenders"] * 9],
            declarer_points=0,
            defender_points=120,
        ),
    )

    assert summary["is_complete"] is True
    assert summary["winner"] == "defenders"
    assert summary["game_value"] == expected_game_value
    assert summary["effective_game_value"] == expected_game_value
    assert summary["settlement_score"] == -2 * expected_game_value
    assert summary["is_loss"] is True


def test_build_final_settlement_summary_applies_declarer_schneider_level() -> None:
    summary = build_final_settlement_summary(
        game_value_summary={
            "game_value": 72,
            "base_value": 24,
            "is_null_game": False,
        },
        game_result_summary={
            "is_complete": True,
            "winner": "declarer",
            "effective_schneider_status": "declarer_made_schneider",
        },
    )

    assert summary["game_value"] == 72
    assert summary["effective_game_value"] == 96
    assert summary["settlement_score"] == 96
    assert summary["is_loss"] is False


def test_build_final_settlement_summary_applies_defender_schneider_level() -> None:
    summary = build_final_settlement_summary(
        game_value_summary={
            "game_value": 72,
            "base_value": 24,
            "is_null_game": False,
        },
        game_result_summary={
            "is_complete": True,
            "winner": "defenders",
            "effective_schneider_status": "defenders_made_schneider",
        },
    )

    assert summary["game_value"] == 72
    assert summary["effective_game_value"] == 96
    assert summary["settlement_score"] == -192
    assert summary["is_loss"] is True


def test_build_final_settlement_summary_loses_failed_schneider_announcement() -> None:
    summary = build_final_settlement_summary(
        game_value_summary={
            "game_value": 96,
            "base_value": 24,
            "is_null_game": False,
            "details": {
                "schneider_announced": True,
            },
        },
        game_result_summary={
            "is_complete": True,
            "winner": "declarer",
            "effective_schneider_status": "none",
        },
    )

    assert summary["winner"] == "declarer"
    assert summary["declarer_won_by_card_points"] is True
    assert summary["game_value"] == 96
    assert summary["effective_game_value"] == 96
    assert summary["is_loss"] is True
    assert summary["settlement_score"] == -192


def test_build_final_settlement_summary_counts_successful_schneider_announcement() -> None:
    summary = build_final_settlement_summary(
        game_value_summary={
            "game_value": 96,
            "base_value": 24,
            "is_null_game": False,
            "details": {
                "schneider_announced": True,
            },
        },
        game_result_summary={
            "is_complete": True,
            "winner": "declarer",
            "effective_schneider_status": "declarer_made_schneider",
        },
    )

    assert summary["winner"] == "declarer"
    assert summary["game_value"] == 96
    assert summary["effective_game_value"] == 120
    assert summary["is_loss"] is False
    assert summary["settlement_score"] == 120


def test_failed_schneider_announcement_does_not_add_defender_schneider() -> None:
    summary = build_final_settlement_summary(
        game_value_summary={
            "game_value": 96,
            "base_value": 24,
            "is_null_game": False,
            "details": {
                "schneider_announced": True,
            },
        },
        game_result_summary={
            "is_complete": True,
            "winner": "defenders",
            "effective_schneider_status": "defenders_made_schneider",
        },
    )

    assert summary["winner"] == "defenders"
    assert summary["game_value"] == 96
    assert summary["effective_game_value"] == 96
    assert summary["is_loss"] is True
    assert summary["settlement_score"] == -192


def test_build_final_settlement_summary_applies_declarer_schwarz_level() -> None:
    summary = build_final_settlement_summary(
        game_value_summary=build_suit_game_value_summary(),
        game_result_summary=build_complete_suit_result_summary(
            winner="declarer",
            effective_schneider_status="declarer_made_schneider",
        ),
        completed_tricks=build_completed_schwarz_tricks(["declarer"] * 10),
    )

    assert summary["game_value"] == 72
    assert summary["effective_game_value"] == 120
    assert summary["settlement_score"] == 120
    assert summary["is_loss"] is False


def test_build_final_settlement_summary_applies_defender_schwarz_level() -> None:
    summary = build_final_settlement_summary(
        game_value_summary=build_suit_game_value_summary(),
        game_result_summary=build_complete_suit_result_summary(
            winner="defenders",
            effective_schneider_status="defenders_made_schneider",
        ),
        completed_tricks=build_completed_schwarz_tricks(["defenders"] * 10),
    )

    assert summary["game_value"] == 72
    assert summary["effective_game_value"] == 120
    assert summary["settlement_score"] == -240
    assert summary["is_loss"] is True


def test_mixed_trick_history_does_not_add_schwarz_level() -> None:
    summary = build_final_settlement_summary(
        game_value_summary=build_suit_game_value_summary(),
        game_result_summary=build_complete_suit_result_summary(
            winner="declarer",
            effective_schneider_status="declarer_made_schneider",
        ),
        completed_tricks=build_completed_schwarz_tricks(
            [*["declarer"] * 9, "defenders"]
        ),
    )

    assert summary["effective_game_value"] == 96
    assert summary["settlement_score"] == 96


def test_card_points_alone_do_not_add_schwarz_level() -> None:
    summary = build_final_settlement_summary(
        game_value_summary=build_suit_game_value_summary(),
        game_result_summary=build_complete_suit_result_summary(
            winner="declarer",
            effective_schneider_status="declarer_made_schneider",
            effective_schwarz_status="declarer_made_schwarz",
        ),
    )

    assert summary["effective_game_value"] == 96
    assert summary["settlement_score"] == 96


def test_zero_point_defender_trick_prevents_declarer_schwarz_level() -> None:
    completed_tricks = build_completed_schwarz_tricks(["declarer"] * 9)
    completed_tricks.append(
        {
            "cards": ["C7", "C8", "C9"],
            "winner_role": "defenders",
        }
    )

    summary = build_final_settlement_summary(
        game_value_summary=build_suit_game_value_summary(),
        game_result_summary=build_complete_suit_result_summary(
            winner="declarer",
            effective_schneider_status="declarer_made_schneider",
            effective_schwarz_status="declarer_made_schwarz",
        ),
        completed_tricks=completed_tricks,
    )

    assert summary["effective_game_value"] == 96
    assert summary["settlement_score"] == 96


def test_zero_point_declarer_trick_prevents_defender_schwarz_level() -> None:
    completed_tricks = build_completed_schwarz_tricks(["defenders"] * 9)
    completed_tricks.append(
        {
            "cards": ["C7", "C8", "C9"],
            "winner_role": "declarer",
        }
    )

    summary = build_final_settlement_summary(
        game_value_summary=build_suit_game_value_summary(),
        game_result_summary=build_complete_suit_result_summary(
            winner="defenders",
            effective_schneider_status="defenders_made_schneider",
            effective_schwarz_status="defenders_made_schwarz",
        ),
        completed_tricks=completed_tricks,
    )

    assert summary["effective_game_value"] == 96
    assert summary["settlement_score"] == -192


def test_successful_schwarz_announcement_counts_declared_and_achieved_levels_once() -> None:
    summary = build_final_settlement_summary(
        game_value_summary=build_suit_game_value_summary(
            game_value=96,
            schwarz_announced=True,
        ),
        game_result_summary=build_complete_suit_result_summary(
            winner="declarer",
            effective_schneider_status="declarer_made_schneider",
        ),
        completed_tricks=build_completed_schwarz_tricks(["declarer"] * 10),
    )

    assert summary["winner"] == "declarer"
    assert summary["declarer_won_by_card_points"] is True
    assert summary["game_value"] == 96
    assert summary["effective_game_value"] == 144
    assert summary["is_loss"] is False
    assert summary["settlement_score"] == 144


def test_failed_schwarz_announcement_loses_despite_card_point_win() -> None:
    summary = build_final_settlement_summary(
        game_value_summary=build_suit_game_value_summary(
            game_value=96,
            schwarz_announced=True,
        ),
        game_result_summary=build_complete_suit_result_summary(
            winner="declarer",
            effective_schneider_status="declarer_made_schneider",
        ),
        completed_tricks=build_completed_schwarz_tricks(
            [*["declarer"] * 9, "defenders"]
        ),
    )

    assert summary["winner"] == "declarer"
    assert summary["declarer_won_by_card_points"] is True
    assert summary["effective_game_value"] == 120
    assert summary["is_loss"] is True
    assert summary["settlement_score"] == -240


def test_zero_point_defender_trick_fails_schwarz_announcement() -> None:
    completed_tricks = build_completed_schwarz_tricks(["declarer"] * 9)
    completed_tricks.append(
        {
            "cards": ["C7", "C8", "C9"],
            "winner_role": "defenders",
        }
    )

    summary = build_final_settlement_summary(
        game_value_summary=build_suit_game_value_summary(
            game_value=96,
            schwarz_announced=True,
        ),
        game_result_summary=build_complete_suit_result_summary(
            winner="declarer",
            effective_schneider_status="declarer_made_schneider",
        ),
        completed_tricks=completed_tricks,
    )

    assert summary["is_loss"] is True
    assert summary["settlement_score"] == -240


def test_failed_schwarz_announcement_stays_loss_when_declarer_already_lost() -> None:
    summary = build_final_settlement_summary(
        game_value_summary=build_suit_game_value_summary(
            game_value=96,
            schwarz_announced=True,
        ),
        game_result_summary=build_complete_suit_result_summary(
            winner="defenders",
            effective_schneider_status="none",
        ),
        completed_tricks=build_completed_schwarz_tricks(
            ["declarer", *["defenders"] * 9]
        ),
    )

    assert summary["winner"] == "defenders"
    assert summary["is_loss"] is True
    assert summary["settlement_score"] == -192


def test_defender_schwarz_fails_declarer_schwarz_announcement() -> None:
    summary = build_final_settlement_summary(
        game_value_summary=build_suit_game_value_summary(
            game_value=96,
            schwarz_announced=True,
        ),
        game_result_summary=build_complete_suit_result_summary(
            winner="defenders",
            effective_schneider_status="defenders_made_schneider",
        ),
        completed_tricks=build_completed_schwarz_tricks(["defenders"] * 10),
    )

    assert summary["effective_game_value"] == 144
    assert summary["is_loss"] is True
    assert summary["settlement_score"] == -288


def test_successful_schwarz_announcement_with_overbid_uses_required_value() -> None:
    summary = build_final_settlement_summary(
        game_value_summary=build_suit_game_value_summary(
            game_value=96,
            schwarz_announced=True,
        ),
        game_result_summary=build_complete_suit_result_summary(
            winner="declarer",
            effective_schneider_status="declarer_made_schneider",
        ),
        overbid_summary={
            "bid_value": 100,
            "game_value": 96,
            "is_overbid": True,
            "margin": -4,
            "required_game_value": 120,
            "status": "overbid",
        },
        completed_tricks=build_completed_schwarz_tricks(["declarer"] * 10),
    )

    assert summary["effective_game_value"] == 120
    assert summary["is_loss"] is True
    assert summary["settlement_score"] == -240


def test_failed_schwarz_announcement_with_overbid_uses_required_value() -> None:
    summary = build_final_settlement_summary(
        game_value_summary=build_suit_game_value_summary(
            game_value=96,
            schwarz_announced=True,
        ),
        game_result_summary=build_complete_suit_result_summary(
            winner="declarer",
            effective_schneider_status="declarer_made_schneider",
        ),
        overbid_summary={
            "bid_value": 100,
            "game_value": 96,
            "is_overbid": True,
            "margin": -4,
            "required_game_value": 120,
            "status": "overbid",
        },
        completed_tricks=build_completed_schwarz_tricks(
            [*["declarer"] * 9, "defenders"]
        ),
    )

    assert summary["effective_game_value"] == 120
    assert summary["is_loss"] is True
    assert summary["settlement_score"] == -240


def test_achieved_schwarz_does_not_increase_overbid_required_value() -> None:
    summary = build_final_settlement_summary(
        game_value_summary=build_suit_game_value_summary(game_value=72),
        game_result_summary=build_complete_suit_result_summary(
            winner="declarer",
            effective_schneider_status="declarer_made_schneider",
        ),
        overbid_summary={
            "bid_value": 73,
            "game_value": 72,
            "is_overbid": True,
            "margin": -1,
            "required_game_value": 96,
            "status": "overbid",
        },
        completed_tricks=build_completed_schwarz_tricks(["declarer"] * 10),
    )

    assert summary["effective_game_value"] == 96
    assert summary["is_loss"] is True
    assert summary["settlement_score"] == -192


def test_incomplete_history_without_schwarz_announcement_keeps_ordinary_settlement() -> None:
    summary = build_final_settlement_summary(
        game_value_summary=build_suit_game_value_summary(game_value=72),
        game_result_summary=build_complete_suit_result_summary(
            winner="declarer",
            effective_schneider_status="declarer_made_schneider",
        ),
        completed_tricks=build_completed_schwarz_tricks(["declarer"] * 9),
    )

    assert summary["is_complete"] is True
    assert summary["effective_game_value"] == 96
    assert summary["settlement_score"] == 96


def test_unresolved_schwarz_announcement_keeps_settlement_incomplete() -> None:
    summary = build_final_settlement_summary(
        game_value_summary=build_suit_game_value_summary(
            game_value=96,
            schwarz_announced=True,
        ),
        game_result_summary=build_complete_suit_result_summary(
            winner="declarer",
            effective_schneider_status="declarer_made_schneider",
        ),
        completed_tricks=build_completed_schwarz_tricks(["declarer"] * 9),
    )

    assert summary["is_complete"] is False
    assert summary["missing_inputs"] == ["complete_trick_ownership"]
    assert summary["declarer_won_by_card_points"] is True
    assert summary["winner"] is None
    assert summary["effective_game_value"] is None
    assert summary["settlement_score"] is None
    assert summary["is_loss"] is None


def test_unresolved_schwarz_announcement_with_overbid_keeps_overbid_settlement() -> None:
    summary = build_final_settlement_summary(
        game_value_summary=build_suit_game_value_summary(
            game_value=96,
            schwarz_announced=True,
        ),
        game_result_summary=build_complete_suit_result_summary(
            winner="declarer",
            effective_schneider_status="declarer_made_schneider",
        ),
        overbid_summary={
            "bid_value": 100,
            "game_value": 96,
            "is_overbid": True,
            "margin": -4,
            "required_game_value": 120,
            "status": "overbid",
        },
        completed_tricks=build_completed_schwarz_tricks(["declarer"] * 9),
    )

    assert summary["is_complete"] is True
    assert summary["missing_inputs"] == []
    assert summary["effective_game_value"] == 120
    assert summary["is_loss"] is True
    assert summary["settlement_score"] == -240


def build_not_overbid_summary() -> dict:
    return {
        "bid_value": 72,
        "game_value": 72,
        "is_overbid": False,
        "margin": 0,
        "required_game_value": 72,
        "status": "not_overbid",
    }


def build_unknown_overbid_summary() -> dict:
    return {
        "bid_value": None,
        "game_value": None,
        "is_overbid": None,
        "margin": None,
        "required_game_value": None,
        "status": "unknown_bid_value",
    }

def test_build_final_settlement_summary_includes_not_overbid_status() -> None:
    summary = build_final_settlement_summary(
        game_value_summary={
            "game_value": 72,
        },
        game_result_summary={
            "is_complete": True,
            "winner": "declarer",
        },
        overbid_summary=build_not_overbid_summary(),
    )

    assert summary["is_complete"] is True
    assert summary["game_value"] == 72
    assert summary["effective_game_value"] == 72
    assert summary["overbid_required_game_value"] == 72
    assert summary["bid_value"] == 72
    assert summary["is_overbid"] is False
    assert summary["overbid_margin"] == 0
    assert summary["overbid_status"] == "not_overbid"

def test_build_final_settlement_summary_includes_overbid_status() -> None:
    summary = build_final_settlement_summary(
        game_value_summary={
            "game_value": 48,
        },
        game_result_summary={
            "is_complete": True,
            "winner": "declarer",
        },
        overbid_summary={
            "bid_value": 60,
            "game_value": 48,
            "is_overbid": True,
            "margin": -12,
            "required_game_value": 72,
            "status": "overbid",
        },
    )

    assert summary["is_complete"] is True
    assert summary["game_value"] == 48
    assert summary["bid_value"] == 60
    assert summary["is_overbid"] is True
    assert summary["overbid_margin"] == -12
    assert summary["overbid_status"] == "overbid"
    assert summary["effective_game_value"] == 72
    assert summary["overbid_required_game_value"] == 72

def test_build_final_settlement_summary_applies_overbid_loss_score() -> None:
    summary = build_final_settlement_summary(
        game_value_summary={
            "game_value": 48,
        },
        game_result_summary={
            "is_complete": True,
            "winner": "declarer",
        },
        overbid_summary={
            "bid_value": 60,
            "game_value": 48,
            "is_overbid": True,
            "margin": -12,
            "required_game_value": 72,
            "status": "overbid",
        },
    )

    assert summary["is_complete"] is True
    assert summary["declarer_won_by_card_points"] is True
    assert summary["winner"] == "declarer"
    assert summary["game_value"] == 48
    assert summary["effective_game_value"] == 72
    assert summary["bid_value"] == 60
    assert summary["is_overbid"] is True
    assert summary["is_loss"] is True
    assert summary["settlement_score"] == -144
    assert summary["overbid_required_game_value"] == 72


def test_overbid_required_value_takes_precedence_over_achieved_schneider() -> None:
    summary = build_final_settlement_summary(
        game_value_summary={
            "game_value": 48,
            "base_value": 24,
            "is_null_game": False,
        },
        game_result_summary={
            "is_complete": True,
            "winner": "declarer",
            "effective_schneider_status": "declarer_made_schneider",
        },
        overbid_summary={
            "bid_value": 73,
            "game_value": 48,
            "is_overbid": True,
            "margin": -25,
            "required_game_value": 96,
            "status": "overbid",
        },
    )

    assert summary["winner"] == "declarer"
    assert summary["effective_game_value"] == 96
    assert summary["settlement_score"] == -192
    assert summary["is_loss"] is True


def test_is_overbid_settlement_supported_for_not_overbid() -> None:
    assert is_overbid_settlement_supported(
        {
            "is_overbid": False,
            "required_game_value": None,
        }
    ) is True


def test_is_overbid_settlement_supported_for_overbid_with_required_value() -> None:
    assert is_overbid_settlement_supported(
        {
            "is_overbid": True,
            "required_game_value": 72,
        }
    ) is True


def test_is_overbid_settlement_supported_for_overbid_without_required_value() -> None:
    assert is_overbid_settlement_supported(
        {
            "is_overbid": True,
            "required_game_value": None,
        }
    ) is False

def test_get_missing_final_settlement_inputs_detects_unsupported_overbid() -> None:
    missing_inputs = get_missing_final_settlement_inputs(
        game_value_summary={
            "game_value": 23,
        },
        game_result_summary={
            "is_complete": True,
        },
        overbid_summary={
            "is_overbid": True,
            "required_game_value": None,
        },
    )

    assert missing_inputs == ["overbid_required_game_value"]

def test_build_final_settlement_summary_for_unsupported_null_overbid() -> None:
    summary = build_final_settlement_summary(
        game_value_summary={
            "game_value": 23,
        },
        game_result_summary={
            "is_complete": True,
            "winner": "declarer",
        },
        overbid_summary={
            "bid_value": 24,
            "game_value": 23,
            "is_overbid": True,
            "margin": -1,
            "required_game_value": None,
            "status": "overbid",
        },
    )

    assert summary["is_complete"] is False
    assert summary["missing_inputs"] == ["overbid_required_game_value"]
    assert summary["declarer_won_by_card_points"] is True
    assert summary["winner"] is None
    assert summary["game_value"] == 23
    assert summary["effective_game_value"] is None
    assert summary["bid_value"] == 24
    assert summary["settlement_score"] is None
    assert summary["is_loss"] is True
    assert summary["is_overbid"] is True
    assert summary["overbid_required_game_value"] is None


def test_impossible_null_settlement_is_incomplete_without_replacement() -> None:
    summary = build_final_settlement_summary(
        game_value_summary={"game_value": 23},
        game_result_summary={
            "is_complete": True,
            "winner": "defenders",
            "game_end_reason": "impossible_null_declaration",
        },
        overbid_summary={
            "bid_value": 24,
            "game_value": 23,
            "is_overbid": True,
            "margin": -1,
            "required_game_value": None,
            "status": "overbid",
        },
    )

    assert summary["is_complete"] is False
    assert summary["missing_inputs"] == ["impossible_null_settlement"]
    assert summary["winner"] == "defenders"
    assert summary["is_loss"] is True
    assert summary["settlement_score"] is None
    assert summary["declarer_won_by_card_points"] is None


def test_impossible_null_settlement_scores_doubled_immediate_loss() -> None:
    replacement_summary = {
        "replacement_game_type": "clubs",
        "matadors": 1,
        "hand_game": False,
        "base_value": 12,
        "minimum_game_value": 24,
        "required_game_value": 36,
    }
    summary = build_final_settlement_summary(
        game_value_summary={"game_value": 23},
        game_result_summary={
            "is_complete": True,
            "winner": "defenders",
            "game_end_reason": "impossible_null_declaration",
        },
        overbid_summary={
            "bid_value": 25,
            "game_value": 23,
            "is_overbid": True,
            "margin": -2,
            "required_game_value": 36,
            "status": "overbid",
        },
        completed_tricks=[],
        impossible_null_settlement=replacement_summary,
    )

    assert summary["is_complete"] is True
    assert summary["missing_inputs"] == []
    assert summary["effective_game_value"] == 36
    assert summary["settlement_score"] == -72
    assert summary["winner"] == "defenders"
    assert summary["declarer_won_by_card_points"] is None
    assert summary["impossible_null_settlement"] == replacement_summary
