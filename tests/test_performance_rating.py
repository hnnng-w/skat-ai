from skat_ai.performance_rating import (
    build_list_performance_summary,
    build_performance_rating_summary,
    calculate_isko_counterparty_rating_points,
    calculate_isko_declarer_rating_points,
    calculate_isko_declarer_rating_score,
    calculate_isko_list_performance_points,
    calculate_isko_list_performance_points_from_game_contributions,
    get_game_outcome_for_rating,
    get_performance_rating_implemented_scope,
    get_performance_rating_unsupported_reason,
    get_performance_rating_unsupported_scope,
    is_performance_rating_partially_implemented,
)


def test_get_game_outcome_for_rating_returns_incomplete() -> None:
    assert get_game_outcome_for_rating(
        {
            "is_complete": False,
            "is_loss": None,
        }
    ) == "incomplete"


def test_get_game_outcome_for_rating_returns_declarer_win() -> None:
    assert get_game_outcome_for_rating(
        {
            "is_complete": True,
            "is_loss": False,
        }
    ) == "declarer_win"


def test_get_game_outcome_for_rating_returns_declarer_loss() -> None:
    assert get_game_outcome_for_rating(
        {
            "is_complete": True,
            "is_loss": True,
        }
    ) == "declarer_loss"


def test_get_game_outcome_for_rating_returns_unknown() -> None:
    assert get_game_outcome_for_rating(
        {
            "is_complete": True,
            "is_loss": None,
        }
    ) == "unknown"


def test_build_performance_rating_summary_for_complete_settlement() -> None:
    summary = build_performance_rating_summary(
        final_settlement_summary={
            "is_complete": True,
            "is_loss": False,
            "settlement_score": 72,
        }
    )

    assert summary == {
        "is_implemented": False,
        "is_partially_implemented": False,
        "implemented_scope": None,
        "unsupported_scope": "performance_rating_not_implemented",
        "rating_system": None,
        "table_player_count": 3,
        "basis": "individual_game_settlement",
        "game_outcome": "declarer_win",
        "settlement_score": 72,
        "rating_score": None,
        "declarer_rating_score": None,
        "declarer_rating_points": None,
        "counterparty_rating_points": None,
        "defender_rating_points": None,
        "unsupported_reason": "performance_rating_not_implemented",
        "notes": [
            "Performance rating is separate from individual game settlement.",
            "rating_score currently represents the declarer's rating score.",
            "List, series, and tournament rating are not fully implemented yet.",
            "final_settlement_summary remains the source for single-game settlement.",
        ],
    }


def test_build_performance_rating_summary_for_incomplete_settlement() -> None:
    summary = build_performance_rating_summary(
        final_settlement_summary={
            "is_complete": False,
            "is_loss": None,
            "settlement_score": None,
        }
    )

    assert summary["is_implemented"] is False
    assert summary["game_outcome"] == "incomplete"
    assert summary["settlement_score"] is None
    assert summary["rating_score"] is None
    assert summary["unsupported_reason"] == "performance_rating_not_implemented"


def test_build_performance_rating_summary_accepts_placeholder_rating_system() -> None:
    summary = build_performance_rating_summary(
        final_settlement_summary={
            "is_complete": True,
            "is_loss": False,
            "settlement_score": 72,
        },
        rating_system="placeholder",
    )

    assert summary == {
        "is_implemented": False,
        "is_partially_implemented": False,
        "implemented_scope": None,
        "unsupported_scope": "performance_rating_not_implemented",
        "rating_system": "placeholder",
        "table_player_count": 3,
        "basis": "individual_game_settlement",
        "game_outcome": "declarer_win",
        "settlement_score": 72,
        "rating_score": None,
        "declarer_rating_score": None,
        "declarer_rating_points": None,
        "counterparty_rating_points": None,
        "defender_rating_points": None,
        "unsupported_reason": "performance_rating_not_implemented",
        "notes": [
            "Performance rating is separate from individual game settlement.",
            "rating_score currently represents the declarer's rating score.",
            "List, series, and tournament rating are not fully implemented yet.",
            "final_settlement_summary remains the source for single-game settlement.",
        ],
    }


def test_build_performance_rating_summary_accepts_isko_list_rating_system() -> None:
    summary = build_performance_rating_summary(
        final_settlement_summary={
            "is_complete": True,
            "is_loss": False,
            "settlement_score": 72,
        },
        rating_system="isko_list",
    )

    assert summary == {
        "is_implemented": False,
        "is_partially_implemented": True,
        "implemented_scope": "declarer_single_game_rating",
        "unsupported_scope": "full_list_series_tournament_rating",
        "rating_system": "isko_list",
        "table_player_count": 3,
        "basis": "individual_game_settlement",
        "game_outcome": "declarer_win",
        "settlement_score": 72,
        "rating_score": 122,
        "declarer_rating_score": 122,
        "declarer_rating_points": 50,
        "counterparty_rating_points": 0,
        "defender_rating_points": 0,
        "unsupported_reason": "full_list_series_tournament_rating_not_implemented",
        "notes": [
            "Performance rating is separate from individual game settlement.",
            "rating_score currently represents the declarer's rating score.",
            "List, series, and tournament rating are not fully implemented yet.",
            "final_settlement_summary remains the source for single-game settlement.",
        ],
    }

def test_build_performance_rating_summary_for_isko_declarer_loss() -> None:
    summary = build_performance_rating_summary(
        final_settlement_summary={
            "is_complete": True,
            "is_loss": True,
            "settlement_score": -144,
        },
        rating_system="isko_list",
    )

    assert summary == {
        "is_implemented": False,
        "is_partially_implemented": True,
        "implemented_scope": "declarer_single_game_rating",
        "unsupported_scope": "full_list_series_tournament_rating",
        "rating_system": "isko_list",
        "table_player_count": 3,
        "basis": "individual_game_settlement",
        "game_outcome": "declarer_loss",
        "settlement_score": -144,
        "rating_score": -194,
        "declarer_rating_score": -194,
        "declarer_rating_points": -50,
        "counterparty_rating_points": 40,
        "defender_rating_points": 40,
        "unsupported_reason": "full_list_series_tournament_rating_not_implemented",
        "notes": [
            "Performance rating is separate from individual game settlement.",
            "rating_score currently represents the declarer's rating score.",
            "List, series, and tournament rating are not fully implemented yet.",
            "final_settlement_summary remains the source for single-game settlement.",
        ],
    }

def test_build_performance_rating_summary_rejects_unknown_rating_system() -> None:
    try:
        build_performance_rating_summary(
            final_settlement_summary={
                "is_complete": True,
                "is_loss": False,
                "settlement_score": 72,
            },
            rating_system="unknown_system",
        )
    except ValueError as error:
        assert "Unknown performance rating system" in str(error)
        assert "unknown_system" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")

def test_get_performance_rating_unsupported_reason_for_default() -> None:
    assert get_performance_rating_unsupported_reason(None) == (
        "performance_rating_not_implemented"
    )


def test_get_performance_rating_unsupported_reason_for_placeholder() -> None:
    assert get_performance_rating_unsupported_reason("placeholder") == (
        "performance_rating_not_implemented"
    )


def test_get_performance_rating_unsupported_reason_for_isko_list() -> None:
    assert get_performance_rating_unsupported_reason("isko_list") == (
        "full_list_series_tournament_rating_not_implemented"
    )

def test_calculate_isko_declarer_rating_points_for_declarer_win() -> None:
    assert calculate_isko_declarer_rating_points("declarer_win") == 50


def test_calculate_isko_declarer_rating_points_for_declarer_loss() -> None:
    assert calculate_isko_declarer_rating_points("declarer_loss") == -50


def test_calculate_isko_declarer_rating_points_for_incomplete_game() -> None:
    assert calculate_isko_declarer_rating_points("incomplete") is None


def test_calculate_isko_declarer_rating_points_for_unknown_outcome() -> None:
    assert calculate_isko_declarer_rating_points("unknown") is None

def test_is_performance_rating_partially_implemented_for_isko_list() -> None:
    assert is_performance_rating_partially_implemented("isko_list") is True


def test_is_performance_rating_partially_implemented_for_placeholder() -> None:
    assert is_performance_rating_partially_implemented("placeholder") is False


def test_is_performance_rating_partially_implemented_for_none() -> None:
    assert is_performance_rating_partially_implemented(None) is False

def test_calculate_isko_counterparty_rating_points_for_declarer_win() -> None:
    assert calculate_isko_counterparty_rating_points("declarer_win") == 0


def test_calculate_isko_counterparty_rating_points_for_declarer_loss() -> None:
    assert calculate_isko_counterparty_rating_points("declarer_loss") == 40


def test_calculate_isko_counterparty_rating_points_for_incomplete_game() -> None:
    assert calculate_isko_counterparty_rating_points("incomplete") is None


def test_calculate_isko_counterparty_rating_points_for_unknown_outcome() -> None:
    assert calculate_isko_counterparty_rating_points("unknown") is None


def test_calculate_isko_declarer_rating_score_for_win() -> None:
    assert calculate_isko_declarer_rating_score(
        settlement_score=72,
        declarer_rating_points=50,
    ) == 122


def test_calculate_isko_declarer_rating_score_for_loss() -> None:
    assert calculate_isko_declarer_rating_score(
        settlement_score=-144,
        declarer_rating_points=-50,
    ) == -194


def test_calculate_isko_declarer_rating_score_without_settlement_score() -> None:
    assert calculate_isko_declarer_rating_score(
        settlement_score=None,
        declarer_rating_points=50,
    ) is None


def test_calculate_isko_declarer_rating_score_without_declarer_points() -> None:
    assert calculate_isko_declarer_rating_score(
        settlement_score=72,
        declarer_rating_points=None,
    ) is None

def test_build_performance_rating_summary_rating_score_aliases_declarer_score() -> None:
    summary = build_performance_rating_summary(
        final_settlement_summary={
            "is_complete": True,
            "is_loss": False,
            "settlement_score": 72,
        },
        rating_system="isko_list",
    )

    assert summary["rating_score"] == 122
    assert summary["declarer_rating_score"] == 122
    assert summary["rating_score"] == summary["declarer_rating_score"]

def test_get_performance_rating_implemented_scope_for_isko_list() -> None:
    assert get_performance_rating_implemented_scope("isko_list") == (
        "declarer_single_game_rating"
    )


def test_get_performance_rating_implemented_scope_for_placeholder() -> None:
    assert get_performance_rating_implemented_scope("placeholder") is None


def test_get_performance_rating_implemented_scope_for_none() -> None:
    assert get_performance_rating_implemented_scope(None) is None


def test_get_performance_rating_unsupported_scope_for_isko_list() -> None:
    assert get_performance_rating_unsupported_scope("isko_list") == (
        "full_list_series_tournament_rating"
    )


def test_get_performance_rating_unsupported_scope_for_placeholder() -> None:
    assert get_performance_rating_unsupported_scope("placeholder") == (
        "performance_rating_not_implemented"
    )


def test_get_performance_rating_unsupported_scope_for_none() -> None:
    assert get_performance_rating_unsupported_scope(None) == (
        "performance_rating_not_implemented"
    )


def test_calculate_isko_list_performance_points_for_mixed_positive_totals() -> None:
    result = calculate_isko_list_performance_points(
        player_game_points=120,
        own_games_won=3,
        own_games_lost=1,
        other_players_lost_games=2,
    )

    assert result == {
        "player_game_points": 120,
        "own_game_bonus_points": 100,
        "opponent_loss_bonus_points": 80,
        "total_performance_points": 300,
        "table_size": 3,
    }


def test_calculate_isko_list_performance_points_from_mixed_contributions() -> None:
    result = calculate_isko_list_performance_points_from_game_contributions(
        game_contributions=[
            {
                "player_role": "declarer",
                "game_outcome": "declarer_win",
                "settlement_score": 72,
            },
            {
                "player_role": "declarer",
                "game_outcome": "declarer_win",
                "settlement_score": 48,
            },
            {
                "player_role": "declarer",
                "game_outcome": "declarer_win",
                "settlement_score": 96,
            },
            {
                "player_role": "declarer",
                "game_outcome": "declarer_loss",
                "settlement_score": -96,
            },
            {
                "player_role": "defender",
                "game_outcome": "declarer_loss",
                "settlement_score": -72,
            },
            {
                "player_role": "defender",
                "game_outcome": "declarer_loss",
                "settlement_score": -48,
            },
            {
                "player_role": "defender",
                "game_outcome": "declarer_win",
                "settlement_score": 48,
            },
        ]
    )

    assert result == {
        "player_game_points": 120,
        "own_games_won": 3,
        "own_games_lost": 1,
        "other_players_lost_games": 2,
        "own_game_bonus_points": 100,
        "opponent_loss_bonus_points": 80,
        "total_performance_points": 300,
        "table_size": 3,
    }


def test_calculate_isko_list_performance_points_from_declarer_win() -> None:
    result = calculate_isko_list_performance_points_from_game_contributions(
        game_contributions=[
            {
                "player_role": "declarer",
                "game_outcome": "declarer_win",
                "settlement_score": 72,
            },
        ]
    )

    assert result["player_game_points"] == 72
    assert result["own_games_won"] == 1
    assert result["own_games_lost"] == 0
    assert result["other_players_lost_games"] == 0
    assert result["total_performance_points"] == 122


def test_calculate_isko_list_performance_points_from_declarer_loss() -> None:
    result = calculate_isko_list_performance_points_from_game_contributions(
        game_contributions=[
            {
                "player_role": "declarer",
                "game_outcome": "declarer_loss",
                "settlement_score": -144,
            },
        ]
    )

    assert result["player_game_points"] == -144
    assert result["own_games_won"] == 0
    assert result["own_games_lost"] == 1
    assert result["other_players_lost_games"] == 0
    assert result["total_performance_points"] == -194


def test_calculate_isko_list_performance_points_from_defender_declarer_loss() -> None:
    result = calculate_isko_list_performance_points_from_game_contributions(
        game_contributions=[
            {
                "player_role": "defender",
                "game_outcome": "declarer_loss",
                "settlement_score": -144,
            },
        ]
    )

    assert result["player_game_points"] == 0
    assert result["own_games_won"] == 0
    assert result["own_games_lost"] == 0
    assert result["other_players_lost_games"] == 1
    assert result["total_performance_points"] == 40


def test_calculate_isko_list_performance_points_from_defender_declarer_win() -> None:
    result = calculate_isko_list_performance_points_from_game_contributions(
        game_contributions=[
            {
                "player_role": "defender",
                "game_outcome": "declarer_win",
                "settlement_score": 72,
            },
        ]
    )

    assert result == {
        "player_game_points": 0,
        "own_games_won": 0,
        "own_games_lost": 0,
        "other_players_lost_games": 0,
        "own_game_bonus_points": 0,
        "opponent_loss_bonus_points": 0,
        "total_performance_points": 0,
        "table_size": 3,
    }


def test_calculate_isko_list_performance_points_from_empty_contributions() -> None:
    result = calculate_isko_list_performance_points_from_game_contributions(
        game_contributions=[]
    )

    assert result == {
        "player_game_points": 0,
        "own_games_won": 0,
        "own_games_lost": 0,
        "other_players_lost_games": 0,
        "own_game_bonus_points": 0,
        "opponent_loss_bonus_points": 0,
        "total_performance_points": 0,
        "table_size": 3,
    }


def test_calculate_isko_list_performance_points_from_contributions_rejects_role() -> None:
    try:
        calculate_isko_list_performance_points_from_game_contributions(
            game_contributions=[
                {
                    "player_role": "unknown",
                    "game_outcome": "declarer_win",
                    "settlement_score": 72,
                },
            ]
        )
    except ValueError as error:
        assert "Unsupported contribution player_role" in str(error)
        assert "unknown" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_calculate_isko_list_performance_points_from_contributions_rejects_outcome() -> None:
    for game_outcome in ["incomplete", "unknown", "defender_win"]:
        try:
            calculate_isko_list_performance_points_from_game_contributions(
                game_contributions=[
                    {
                        "player_role": "declarer",
                        "game_outcome": game_outcome,
                        "settlement_score": 72,
                    },
                ]
            )
        except ValueError as error:
            assert "Unsupported contribution game_outcome" in str(error)
            assert game_outcome in str(error)
        else:
            raise AssertionError("Expected ValueError was not raised.")


def test_calculate_isko_list_performance_points_from_contributions_rejects_missing_fields() -> None:
    for field_name in ["player_role", "game_outcome", "settlement_score"]:
        contribution = {
            "player_role": "declarer",
            "game_outcome": "declarer_win",
            "settlement_score": 72,
        }
        del contribution[field_name]

        try:
            calculate_isko_list_performance_points_from_game_contributions(
                game_contributions=[contribution]
            )
        except ValueError as error:
            assert "missing required field" in str(error)
            assert field_name in str(error)
        else:
            raise AssertionError("Expected ValueError was not raised.")


def test_calculate_isko_list_contributions_reject_non_integer_scores() -> None:
    for settlement_score in [None, "72", 72.0, True, False]:
        try:
            calculate_isko_list_performance_points_from_game_contributions(
                game_contributions=[
                    {
                        "player_role": "declarer",
                        "game_outcome": "declarer_win",
                        "settlement_score": settlement_score,
                    },
                ]
            )
        except ValueError as error:
            assert "settlement_score must be an integer" in str(error)
        else:
            raise AssertionError("Expected ValueError was not raised.")


def test_calculate_isko_list_performance_points_from_contributions_rejects_score_signs() -> None:
    cases = [
        {
            "player_role": "declarer",
            "game_outcome": "declarer_win",
            "settlement_score": 0,
            "expected_error": "positive settlement_score",
        },
        {
            "player_role": "declarer",
            "game_outcome": "declarer_win",
            "settlement_score": -72,
            "expected_error": "positive settlement_score",
        },
        {
            "player_role": "defender",
            "game_outcome": "declarer_win",
            "settlement_score": -72,
            "expected_error": "positive settlement_score",
        },
        {
            "player_role": "declarer",
            "game_outcome": "declarer_loss",
            "settlement_score": 0,
            "expected_error": "negative settlement_score",
        },
        {
            "player_role": "declarer",
            "game_outcome": "declarer_loss",
            "settlement_score": 72,
            "expected_error": "negative settlement_score",
        },
        {
            "player_role": "defender",
            "game_outcome": "declarer_loss",
            "settlement_score": 72,
            "expected_error": "negative settlement_score",
        },
    ]

    for case in cases:
        try:
            calculate_isko_list_performance_points_from_game_contributions(
                game_contributions=[
                    {
                        "player_role": case["player_role"],
                        "game_outcome": case["game_outcome"],
                        "settlement_score": case["settlement_score"],
                    },
                ]
            )
        except ValueError as error:
            assert case["expected_error"] in str(error)
        else:
            raise AssertionError("Expected ValueError was not raised.")


def test_calculate_isko_list_performance_points_from_contributions_rejects_table_size() -> None:
    try:
        calculate_isko_list_performance_points_from_game_contributions(
            game_contributions=[],
            table_size=4,
        )
    except ValueError as error:
        assert "Unsupported ISkO list table size" in str(error)
        assert "three-player" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_build_list_performance_summary_for_aggregated_totals() -> None:
    summary = build_list_performance_summary(
        list_performance_input={
            "player_game_points": 120,
            "own_games_won": 3,
            "own_games_lost": 1,
            "other_players_lost_games": 2,
        },
        rating_system="isko_list",
    )

    assert summary == {
        "rating_system": "isko_list",
        "basis": "aggregated_list_or_series_totals",
        "table_size": 3,
        "player_game_points": 120,
        "own_games_won": 3,
        "own_games_lost": 1,
        "other_players_lost_games": 2,
        "own_game_bonus_points": 100,
        "opponent_loss_bonus_points": 80,
        "total_performance_points": 300,
    }


def test_build_list_performance_summary_rejects_missing_rating_system() -> None:
    try:
        build_list_performance_summary(
            list_performance_input={
                "player_game_points": 120,
                "own_games_won": 3,
                "own_games_lost": 1,
                "other_players_lost_games": 2,
            },
            rating_system=None,
        )
    except ValueError as error:
        assert "requires performance_rating_system to be isko_list" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_calculate_isko_list_performance_points_allows_negative_game_points() -> None:
    result = calculate_isko_list_performance_points(
        player_game_points=-80,
        own_games_won=1,
        own_games_lost=0,
        other_players_lost_games=0,
    )

    assert result == {
        "player_game_points": -80,
        "own_game_bonus_points": 50,
        "opponent_loss_bonus_points": 0,
        "total_performance_points": -30,
        "table_size": 3,
    }


def test_calculate_isko_list_performance_points_counts_own_game_losses() -> None:
    result = calculate_isko_list_performance_points(
        player_game_points=0,
        own_games_won=0,
        own_games_lost=2,
        other_players_lost_games=0,
    )

    assert result["own_game_bonus_points"] == -100
    assert result["total_performance_points"] == -100


def test_calculate_isko_list_performance_points_counts_opponent_losses() -> None:
    result = calculate_isko_list_performance_points(
        player_game_points=0,
        own_games_won=0,
        own_games_lost=0,
        other_players_lost_games=3,
    )

    assert result["opponent_loss_bonus_points"] == 120
    assert result["total_performance_points"] == 120


def test_calculate_isko_list_performance_points_defaults_to_three_players() -> None:
    result = calculate_isko_list_performance_points(
        player_game_points=0,
        own_games_won=0,
        own_games_lost=0,
        other_players_lost_games=0,
    )

    assert result["table_size"] == 3


def test_calculate_isko_list_performance_points_accepts_explicit_three_players() -> None:
    result = calculate_isko_list_performance_points(
        player_game_points=0,
        own_games_won=0,
        own_games_lost=0,
        other_players_lost_games=0,
        table_size=3,
    )

    assert result["table_size"] == 3


def test_calculate_isko_list_performance_points_rejects_non_three_player_table() -> None:
    try:
        calculate_isko_list_performance_points(
            player_game_points=0,
            own_games_won=0,
            own_games_lost=0,
            other_players_lost_games=0,
            table_size=4,
        )
    except ValueError as error:
        assert "Unsupported ISkO list table size" in str(error)
        assert "three-player" in str(error)
    else:
        raise AssertionError("Expected ValueError was not raised.")


def test_calculate_isko_list_performance_points_rejects_negative_counters() -> None:
    cases = [
        {
            "own_games_won": -1,
            "own_games_lost": 0,
            "other_players_lost_games": 0,
            "expected_error": "own_games_won must be non-negative.",
        },
        {
            "own_games_won": 0,
            "own_games_lost": -1,
            "other_players_lost_games": 0,
            "expected_error": "own_games_lost must be non-negative.",
        },
        {
            "own_games_won": 0,
            "own_games_lost": 0,
            "other_players_lost_games": -1,
            "expected_error": "other_players_lost_games must be non-negative.",
        },
    ]

    for case in cases:
        try:
            calculate_isko_list_performance_points(
                player_game_points=0,
                own_games_won=case["own_games_won"],
                own_games_lost=case["own_games_lost"],
                other_players_lost_games=case["other_players_lost_games"],
            )
        except ValueError as error:
            assert str(error) == case["expected_error"]
        else:
            raise AssertionError("Expected ValueError was not raised.")
