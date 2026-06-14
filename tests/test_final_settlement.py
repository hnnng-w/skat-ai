from skat_ai.final_settlement import (
    build_final_settlement_summary,
    calculate_basic_settlement_score,
    get_missing_final_settlement_inputs,
    is_declarer_base_contract_winner,
    is_overbid_settlement_supported,
)
from skat_ai.game_declaration import GameDeclaration
from skat_ai.game_result import build_game_result_summary_from_score_summary
from skat_ai.game_value import build_game_value_summary


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
