import pytest

from skat_ai.final_settlement import build_final_settlement_summary
from skat_ai.game_declaration import GameDeclaration
from skat_ai.game_result import build_game_result_summary_from_score_summary
from skat_ai.game_value import build_game_value_summary
from skat_ai.performance_rating import (
    build_list_game_contribution_from_analysis_result,
    build_list_performance_summary,
    build_list_performance_summary_from_analysis_results,
    build_list_performance_summary_from_game_contributions,
    build_performance_rating_summary,
    calculate_isko_counterparty_rating_points,
    calculate_isko_declarer_rating_points,
    calculate_isko_declarer_rating_score,
    calculate_isko_list_performance_points,
    calculate_isko_list_performance_points_from_analysis_results,
    calculate_isko_list_performance_points_from_game_contributions,
    get_game_outcome_for_rating,
    get_performance_rating_implemented_scope,
    get_performance_rating_unsupported_reason,
    get_performance_rating_unsupported_scope,
    is_performance_rating_partially_implemented,
)


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


def build_completed_null_final_settlement(
    winner_roles: list[str],
    declarer_points: int,
    defender_points: int,
) -> dict:
    game_result_summary = build_game_result_summary_from_score_summary(
        score_summary=build_score_summary(declarer_points, defender_points),
        game_type="null",
        completed_tricks=build_completed_null_tricks(winner_roles),
        game_end_reason="normal_completion",
    )

    return build_final_settlement_summary(
        game_value_summary=build_game_value_summary(GameDeclaration(game_type="null")),
        game_result_summary=game_result_summary,
    )


def build_contribution_analysis_result(
    player_role="declarer",
    is_complete=True,
    is_loss=False,
    settlement_score=72,
    winner="declarer",
    declarer_won_by_card_points=True,
    rating_score=122,
):
    return {
        "position": {
            "player_role": player_role,
        },
        "final_settlement_summary": {
            "is_complete": is_complete,
            "is_loss": is_loss,
            "settlement_score": settlement_score,
            "winner": winner,
            "declarer_won_by_card_points": declarer_won_by_card_points,
        },
        "performance_rating_summary": {
            "rating_score": rating_score,
        },
    }


def build_valid_game_contribution(
    player_role="declarer",
    game_outcome="declarer_win",
    settlement_score=72,
    rated_player_id=None,
    game_id=None,
):
    contribution = {
        "player_role": player_role,
        "game_outcome": game_outcome,
        "settlement_score": settlement_score,
    }

    if rated_player_id is not None:
        contribution["rated_player_id"] = rated_player_id

    if game_id is not None:
        contribution["game_id"] = game_id

    return contribution


def with_list_metadata(
    entry: dict,
    rated_player_id=None,
    game_id=None,
) -> dict:
    updated_entry = dict(entry)

    if rated_player_id is not None:
        updated_entry["rated_player_id"] = rated_player_id

    if game_id is not None:
        updated_entry["game_id"] = game_id

    return updated_entry


@pytest.mark.parametrize(
    ("player_role", "is_loss", "settlement_score", "expected_contribution"),
    [
        (
            "declarer",
            False,
            72,
            {
                "player_role": "declarer",
                "game_outcome": "declarer_win",
                "settlement_score": 72,
            },
        ),
        (
            "declarer",
            True,
            -144,
            {
                "player_role": "declarer",
                "game_outcome": "declarer_loss",
                "settlement_score": -144,
            },
        ),
        (
            "defender",
            False,
            72,
            {
                "player_role": "defender",
                "game_outcome": "declarer_win",
                "settlement_score": 72,
            },
        ),
        (
            "defender",
            True,
            -144,
            {
                "player_role": "defender",
                "game_outcome": "declarer_loss",
                "settlement_score": -144,
            },
        ),
    ],
)
def test_build_list_game_contribution_from_analysis_result_maps_completed_games(
    player_role,
    is_loss,
    settlement_score,
    expected_contribution,
) -> None:
    result = build_contribution_analysis_result(
        player_role=player_role,
        is_loss=is_loss,
        settlement_score=settlement_score,
    )

    assert build_list_game_contribution_from_analysis_result(result) == (
        expected_contribution
    )


def test_build_list_game_contribution_from_analysis_result_uses_settlement_loss() -> None:
    result = build_contribution_analysis_result(
        is_loss=True,
        settlement_score=-144,
        winner="declarer",
        declarer_won_by_card_points=True,
    )

    assert build_list_game_contribution_from_analysis_result(result) == {
        "player_role": "declarer",
        "game_outcome": "declarer_loss",
        "settlement_score": -144,
    }


def test_analysis_result_contribution_handles_failed_announcement() -> None:
    result = build_contribution_analysis_result(
        is_loss=True,
        settlement_score=-192,
        winner="declarer",
        declarer_won_by_card_points=True,
    )

    assert build_list_game_contribution_from_analysis_result(result) == {
        "player_role": "declarer",
        "game_outcome": "declarer_loss",
        "settlement_score": -192,
    }


def test_build_list_game_contribution_from_analysis_result_ignores_rating_score() -> None:
    result = build_contribution_analysis_result(
        settlement_score=72,
        rating_score=122,
    )

    contribution = build_list_game_contribution_from_analysis_result(result)

    assert contribution is not None
    assert contribution["settlement_score"] == 72


def test_analysis_result_contribution_returns_none_when_incomplete() -> None:
    result = build_contribution_analysis_result(
        is_complete=False,
        is_loss=None,
        settlement_score=None,
        winner=None,
        declarer_won_by_card_points=None,
    )

    assert build_list_game_contribution_from_analysis_result(result) is None


def test_analysis_result_contribution_returns_none_for_unknown_role() -> None:
    result = build_contribution_analysis_result(player_role="unknown")

    assert build_list_game_contribution_from_analysis_result(result) is None


@pytest.mark.parametrize("analysis_result", [None, [], "result", True, 1])
def test_build_list_game_contribution_from_analysis_result_rejects_non_object_result(
    analysis_result,
) -> None:
    with pytest.raises(ValueError, match="analysis_result must be an object"):
        build_list_game_contribution_from_analysis_result(analysis_result)


@pytest.mark.parametrize(
    "analysis_result",
    [
        {},
        {"position": None},
        {"position": "position"},
        {"position": []},
    ],
)
def test_build_list_game_contribution_from_analysis_result_rejects_invalid_position(
    analysis_result,
) -> None:
    with pytest.raises(ValueError, match="analysis_result.position must be an object"):
        build_list_game_contribution_from_analysis_result(analysis_result)


def test_build_list_game_contribution_from_analysis_result_rejects_missing_role() -> None:
    result = build_contribution_analysis_result()
    del result["position"]["player_role"]

    with pytest.raises(ValueError, match="position.player_role is required"):
        build_list_game_contribution_from_analysis_result(result)


def test_build_list_game_contribution_from_analysis_result_rejects_invalid_role() -> None:
    result = build_contribution_analysis_result(player_role="attacker")

    with pytest.raises(
        ValueError,
        match="Unsupported analysis_result.position.player_role",
    ):
        build_list_game_contribution_from_analysis_result(result)


@pytest.mark.parametrize(
    "final_settlement_summary",
    [None, "summary", []],
)
def test_build_list_game_contribution_from_analysis_result_rejects_invalid_settlement(
    final_settlement_summary,
) -> None:
    result = build_contribution_analysis_result()
    result["final_settlement_summary"] = final_settlement_summary

    with pytest.raises(
        ValueError,
        match="analysis_result.final_settlement_summary must be an object",
    ):
        build_list_game_contribution_from_analysis_result(result)


def test_analysis_result_contribution_rejects_missing_settlement() -> None:
    result = build_contribution_analysis_result()
    del result["final_settlement_summary"]

    with pytest.raises(
        ValueError,
        match="analysis_result.final_settlement_summary must be an object",
    ):
        build_list_game_contribution_from_analysis_result(result)


def test_analysis_result_contribution_rejects_missing_is_complete() -> None:
    result = build_contribution_analysis_result()
    del result["final_settlement_summary"]["is_complete"]

    with pytest.raises(ValueError, match="is_complete is required"):
        build_list_game_contribution_from_analysis_result(result)


@pytest.mark.parametrize("is_complete", [None, "true", 1, 0])
def test_build_list_game_contribution_from_analysis_result_rejects_invalid_is_complete(
    is_complete,
) -> None:
    result = build_contribution_analysis_result(is_complete=is_complete)

    with pytest.raises(ValueError, match="is_complete must be a boolean"):
        build_list_game_contribution_from_analysis_result(result)


def test_analysis_result_contribution_rejects_missing_is_loss() -> None:
    result = build_contribution_analysis_result()
    del result["final_settlement_summary"]["is_loss"]

    with pytest.raises(ValueError, match="is_loss is required"):
        build_list_game_contribution_from_analysis_result(result)


@pytest.mark.parametrize("is_loss", [None, "false", 1, 0])
def test_build_list_game_contribution_from_analysis_result_rejects_invalid_is_loss(
    is_loss,
) -> None:
    result = build_contribution_analysis_result(is_loss=is_loss)

    with pytest.raises(ValueError, match="is_loss must be a boolean"):
        build_list_game_contribution_from_analysis_result(result)


def test_build_list_game_contribution_from_analysis_result_rejects_missing_score() -> None:
    result = build_contribution_analysis_result()
    del result["final_settlement_summary"]["settlement_score"]

    with pytest.raises(ValueError, match="settlement_score is required"):
        build_list_game_contribution_from_analysis_result(result)


@pytest.mark.parametrize("settlement_score", [None, "72", 72.0, True, False])
def test_build_list_game_contribution_from_analysis_result_rejects_invalid_score(
    settlement_score,
) -> None:
    result = build_contribution_analysis_result(settlement_score=settlement_score)

    with pytest.raises(ValueError, match="settlement_score must be an integer"):
        build_list_game_contribution_from_analysis_result(result)


@pytest.mark.parametrize(
    ("is_loss", "settlement_score", "expected_error"),
    [
        (False, 0, "positive settlement_score"),
        (False, -72, "positive settlement_score"),
        (True, 0, "negative settlement_score"),
        (True, 72, "negative settlement_score"),
    ],
)
def test_build_list_game_contribution_from_analysis_result_rejects_inconsistent_signs(
    is_loss,
    settlement_score,
    expected_error,
) -> None:
    result = build_contribution_analysis_result(
        is_loss=is_loss,
        settlement_score=settlement_score,
    )

    with pytest.raises(ValueError, match=expected_error):
        build_list_game_contribution_from_analysis_result(result)


def test_calculate_isko_list_performance_points_from_analysis_results_mixed_results() -> None:
    result = calculate_isko_list_performance_points_from_analysis_results(
        analysis_results=[
            build_contribution_analysis_result(
                player_role="declarer",
                is_loss=False,
                settlement_score=72,
            ),
            build_contribution_analysis_result(
                player_role="declarer",
                is_loss=True,
                settlement_score=-96,
            ),
            build_contribution_analysis_result(
                player_role="defender",
                is_loss=True,
                settlement_score=-48,
            ),
            build_contribution_analysis_result(
                player_role="defender",
                is_loss=False,
                settlement_score=48,
            ),
        ]
    )

    assert result == {
        "player_game_points": -24,
        "own_games_won": 1,
        "own_games_lost": 1,
        "other_players_lost_games": 1,
        "own_game_bonus_points": 0,
        "opponent_loss_bonus_points": 40,
        "total_performance_points": 16,
        "table_size": 3,
    }


def test_calculate_isko_list_performance_points_from_analysis_results_skips_none_results() -> None:
    result = calculate_isko_list_performance_points_from_analysis_results(
        analysis_results=[
            build_contribution_analysis_result(
                is_complete=False,
                is_loss=None,
                settlement_score=None,
                winner=None,
                declarer_won_by_card_points=None,
            ),
            build_contribution_analysis_result(player_role="unknown"),
            build_contribution_analysis_result(
                player_role="defender",
                is_loss=True,
                settlement_score=-72,
            ),
        ]
    )

    assert result == {
        "player_game_points": 0,
        "own_games_won": 0,
        "own_games_lost": 0,
        "other_players_lost_games": 1,
        "own_game_bonus_points": 0,
        "opponent_loss_bonus_points": 40,
        "total_performance_points": 40,
        "table_size": 3,
    }


def test_calculate_isko_list_performance_points_from_empty_analysis_results() -> None:
    result = calculate_isko_list_performance_points_from_analysis_results(
        analysis_results=[]
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


def test_calculate_isko_list_performance_points_from_only_skipped_results() -> None:
    result = calculate_isko_list_performance_points_from_analysis_results(
        analysis_results=[
            build_contribution_analysis_result(
                is_complete=False,
                is_loss=None,
                settlement_score=None,
                winner=None,
                declarer_won_by_card_points=None,
            ),
            build_contribution_analysis_result(player_role="unknown"),
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


@pytest.mark.parametrize("analysis_results", [None, {}, (), "results", True, 1])
def test_calculate_isko_list_performance_points_from_analysis_results_rejects_non_list(
    analysis_results,
) -> None:
    with pytest.raises(ValueError, match="analysis_results must be a list"):
        calculate_isko_list_performance_points_from_analysis_results(
            analysis_results=analysis_results
        )


@pytest.mark.parametrize("analysis_result", [None, [], "result", True, 1])
def test_calculate_isko_list_performance_points_from_analysis_results_rejects_entries(
    analysis_result,
) -> None:
    with pytest.raises(ValueError, match="analysis_result must be an object"):
        calculate_isko_list_performance_points_from_analysis_results(
            analysis_results=[analysis_result]
        )


def test_calculate_isko_list_performance_points_from_analysis_results_rejects_malformed() -> None:
    analysis_result = build_contribution_analysis_result()
    del analysis_result["final_settlement_summary"]["settlement_score"]

    with pytest.raises(ValueError, match="settlement_score is required"):
        calculate_isko_list_performance_points_from_analysis_results(
            analysis_results=[analysis_result]
        )


def test_calculate_isko_list_performance_points_from_analysis_results_rejects_table_size() -> None:
    with pytest.raises(ValueError, match="Unsupported ISkO list table size"):
        calculate_isko_list_performance_points_from_analysis_results(
            analysis_results=[],
            table_size=4,
        )


def test_analysis_result_aggregation_direct_call_rejects_conflicting_player_ids() -> None:
    with pytest.raises(
        ValueError,
        match=r"list_analysis_results\.rated_player_id values conflict: .*0.*1",
    ):
        calculate_isko_list_performance_points_from_analysis_results(
            analysis_results=[
                with_list_metadata(
                    build_contribution_analysis_result(),
                    rated_player_id="player-a",
                ),
                with_list_metadata(
                    build_contribution_analysis_result(),
                    rated_player_id="Player-A",
                ),
            ]
        )


def test_analysis_result_aggregation_direct_call_rejects_duplicate_game_ids() -> None:
    with pytest.raises(
        ValueError,
        match=r"Duplicate list_analysis_results\.game_id 'game-1' at indexes 0 and 1",
    ):
        calculate_isko_list_performance_points_from_analysis_results(
            analysis_results=[
                with_list_metadata(
                    build_contribution_analysis_result(settlement_score=72),
                    game_id="game-1",
                ),
                with_list_metadata(
                    build_contribution_analysis_result(settlement_score=96),
                    game_id="game-1",
                ),
            ]
        )


def test_analysis_result_aggregation_metadata_does_not_change_scoring() -> None:
    analysis_results_without_metadata = [
        build_contribution_analysis_result(
            player_role="declarer",
            is_loss=False,
            settlement_score=96,
        ),
        build_contribution_analysis_result(
            player_role="defender",
            is_loss=True,
            settlement_score=-144,
        ),
    ]
    analysis_results_with_metadata = [
        with_list_metadata(
            analysis_results_without_metadata[0],
            rated_player_id="player-1",
            game_id="game-1",
        ),
        with_list_metadata(
            analysis_results_without_metadata[1],
            rated_player_id="player-1",
            game_id="game-2",
        ),
    ]

    assert calculate_isko_list_performance_points_from_analysis_results(
        analysis_results_with_metadata
    ) == calculate_isko_list_performance_points_from_analysis_results(
        analysis_results_without_metadata
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


def test_performance_rating_uses_completed_null_win_settlement() -> None:
    final_settlement_summary = build_completed_null_final_settlement(
        winner_roles=["defenders"] * 10,
        declarer_points=0,
        defender_points=120,
    )

    summary = build_performance_rating_summary(
        final_settlement_summary=final_settlement_summary,
        rating_system="isko_list",
    )

    assert final_settlement_summary["settlement_score"] == 23
    assert summary["game_outcome"] == "declarer_win"
    assert summary["settlement_score"] == 23
    assert summary["rating_score"] == 73


def test_performance_rating_uses_completed_null_loss_settlement() -> None:
    final_settlement_summary = build_completed_null_final_settlement(
        winner_roles=["declarer", *["defenders"] * 9],
        declarer_points=0,
        defender_points=120,
    )

    summary = build_performance_rating_summary(
        final_settlement_summary=final_settlement_summary,
        rating_system="isko_list",
    )

    assert final_settlement_summary["settlement_score"] == -46
    assert summary["game_outcome"] == "declarer_loss"
    assert summary["settlement_score"] == -46
    assert summary["rating_score"] == -96

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


def test_calculate_isko_list_performance_points_from_contributions_rejects_non_objects() -> None:
    for contribution in [None, "game", 1, True]:
        try:
            calculate_isko_list_performance_points_from_game_contributions(
                game_contributions=[contribution]
            )
        except ValueError as error:
            assert "game contribution must be an object" in str(error)
        else:
            raise AssertionError("Expected ValueError was not raised.")


def test_calculate_isko_list_performance_points_from_contributions_rejects_extra_fields() -> None:
    try:
        calculate_isko_list_performance_points_from_game_contributions(
            game_contributions=[
                {
                    "player_role": "declarer",
                    "game_outcome": "declarer_win",
                    "settlement_score": 72,
                    "table_size": 3,
                },
            ]
        )
    except ValueError as error:
        assert "unsupported fields" in str(error)
        assert "table_size" in str(error)
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


def test_game_contribution_aggregation_direct_call_rejects_conflicting_player_ids() -> None:
    with pytest.raises(
        ValueError,
        match=r"list_game_contributions\.rated_player_id values conflict: .*0.*1",
    ):
        calculate_isko_list_performance_points_from_game_contributions(
            game_contributions=[
                build_valid_game_contribution(rated_player_id="player-a"),
                build_valid_game_contribution(rated_player_id="Player-A"),
            ]
        )


def test_game_contribution_aggregation_direct_call_rejects_duplicate_game_ids() -> None:
    with pytest.raises(
        ValueError,
        match=r"Duplicate list_game_contributions\.game_id 'game-1' at indexes 0 and 1",
    ):
        calculate_isko_list_performance_points_from_game_contributions(
            game_contributions=[
                build_valid_game_contribution(settlement_score=72, game_id="game-1"),
                build_valid_game_contribution(settlement_score=96, game_id="game-1"),
            ]
        )


def test_game_contribution_metadata_does_not_change_scoring() -> None:
    contributions_without_metadata = [
        build_valid_game_contribution(
            player_role="declarer",
            game_outcome="declarer_win",
            settlement_score=96,
        ),
        build_valid_game_contribution(
            player_role="defender",
            game_outcome="declarer_loss",
            settlement_score=-144,
        ),
    ]
    contributions_with_metadata = [
        with_list_metadata(
            contributions_without_metadata[0],
            rated_player_id="player-1",
            game_id="game-1",
        ),
        with_list_metadata(
            contributions_without_metadata[1],
            rated_player_id="player-1",
            game_id="game-2",
        ),
    ]

    assert calculate_isko_list_performance_points_from_game_contributions(
        contributions_with_metadata
    ) == calculate_isko_list_performance_points_from_game_contributions(
        contributions_without_metadata
    )


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


def test_build_list_performance_summary_from_mixed_contributions() -> None:
    summary = build_list_performance_summary_from_game_contributions(
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
        ],
        rating_system="isko_list",
    )

    assert summary == {
        "rating_system": "isko_list",
        "basis": "normalized_game_contributions",
        "table_size": 3,
        "player_game_points": 120,
        "own_games_won": 3,
        "own_games_lost": 1,
        "other_players_lost_games": 2,
        "own_game_bonus_points": 100,
        "opponent_loss_bonus_points": 80,
        "total_performance_points": 300,
    }


def test_build_list_performance_summary_from_empty_contributions() -> None:
    summary = build_list_performance_summary_from_game_contributions(
        game_contributions=[],
        rating_system="isko_list",
    )

    assert summary == {
        "rating_system": "isko_list",
        "basis": "normalized_game_contributions",
        "table_size": 3,
        "player_game_points": 0,
        "own_games_won": 0,
        "own_games_lost": 0,
        "other_players_lost_games": 0,
        "own_game_bonus_points": 0,
        "opponent_loss_bonus_points": 0,
        "total_performance_points": 0,
    }


def test_build_list_performance_summary_from_analysis_results() -> None:
    summary = build_list_performance_summary_from_analysis_results(
        analysis_results=[
            build_contribution_analysis_result(
                player_role="declarer",
                is_loss=False,
                settlement_score=96,
            ),
            build_contribution_analysis_result(
                player_role="defender",
                is_loss=True,
                settlement_score=-144,
            ),
        ],
        rating_system="isko_list",
    )

    assert summary == {
        "rating_system": "isko_list",
        "basis": "local_analysis_results",
        "table_size": 3,
        "player_game_points": 96,
        "own_games_won": 1,
        "own_games_lost": 0,
        "other_players_lost_games": 1,
        "own_game_bonus_points": 50,
        "opponent_loss_bonus_points": 40,
        "total_performance_points": 186,
    }


def test_build_list_performance_summary_from_empty_analysis_results() -> None:
    summary = build_list_performance_summary_from_analysis_results(
        analysis_results=[],
        rating_system="isko_list",
    )

    assert summary == {
        "rating_system": "isko_list",
        "basis": "local_analysis_results",
        "table_size": 3,
        "player_game_points": 0,
        "own_games_won": 0,
        "own_games_lost": 0,
        "other_players_lost_games": 0,
        "own_game_bonus_points": 0,
        "opponent_loss_bonus_points": 0,
        "total_performance_points": 0,
    }


def test_build_list_performance_summary_from_analysis_results_skips_none_results() -> None:
    summary = build_list_performance_summary_from_analysis_results(
        analysis_results=[
            build_contribution_analysis_result(
                is_complete=False,
                is_loss=None,
                settlement_score=None,
                winner=None,
                declarer_won_by_card_points=None,
            ),
            build_contribution_analysis_result(player_role="unknown"),
            build_contribution_analysis_result(
                player_role="defender",
                is_loss=True,
                settlement_score=-72,
            ),
        ],
        rating_system="isko_list",
    )

    assert summary == {
        "rating_system": "isko_list",
        "basis": "local_analysis_results",
        "table_size": 3,
        "player_game_points": 0,
        "own_games_won": 0,
        "own_games_lost": 0,
        "other_players_lost_games": 1,
        "own_game_bonus_points": 0,
        "opponent_loss_bonus_points": 40,
        "total_performance_points": 40,
    }


def test_build_list_performance_summary_from_analysis_results_rejects_malformed() -> None:
    analysis_result = build_contribution_analysis_result()
    del analysis_result["final_settlement_summary"]["settlement_score"]

    with pytest.raises(ValueError, match="settlement_score is required"):
        build_list_performance_summary_from_analysis_results(
            analysis_results=[analysis_result],
            rating_system="isko_list",
        )


def test_build_list_performance_summary_from_analysis_results_rejects_rating_system() -> None:
    for rating_system in [None, "placeholder"]:
        with pytest.raises(
            ValueError,
            match="requires performance_rating_system to be isko_list",
        ):
            build_list_performance_summary_from_analysis_results(
                analysis_results=[],
                rating_system=rating_system,
            )


def test_build_list_performance_summary_from_contributions_rejects_rating_system() -> None:
    for rating_system in [None, "placeholder"]:
        try:
            build_list_performance_summary_from_game_contributions(
                game_contributions=[],
                rating_system=rating_system,
            )
        except ValueError as error:
            assert "requires performance_rating_system to be isko_list" in str(error)
        else:
            raise AssertionError("Expected ValueError was not raised.")


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
