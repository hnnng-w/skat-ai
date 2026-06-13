from typing import Any

SUPPORTED_PERFORMANCE_RATING_SYSTEMS = [
    "placeholder",
    "isko_list",
]
ISKO_DECLARER_WIN_POINTS = 50
ISKO_DECLARER_LOSS_POINTS = -50
ISKO_COUNTERPARTY_LOSS_BONUS_THREE_PLAYER_TABLE = 40
ISKO_FIXED_TABLE_PLAYER_COUNT = 3


def calculate_isko_list_performance_points(
    player_game_points: int,
    own_games_won: int,
    own_games_lost: int,
    other_players_lost_games: int,
    table_size: int = ISKO_FIXED_TABLE_PLAYER_COUNT,
) -> dict[str, int]:
    """
    Calculates ISkO-style list performance points for one player.

    Inputs are already aggregated list or series totals. This is separate from
    single-game final settlement and does not inspect final_settlement_summary.
    """
    if table_size != ISKO_FIXED_TABLE_PLAYER_COUNT:
        raise ValueError(
            f"Unsupported ISkO list table size: {table_size}. "
            "Only three-player tables are supported."
        )

    game_counters = {
        "own_games_won": own_games_won,
        "own_games_lost": own_games_lost,
        "other_players_lost_games": other_players_lost_games,
    }
    for field_name, value in game_counters.items():
        if value < 0:
            raise ValueError(f"{field_name} must be non-negative.")

    own_game_bonus_points = (
        own_games_won * ISKO_DECLARER_WIN_POINTS
        + own_games_lost * ISKO_DECLARER_LOSS_POINTS
    )
    opponent_loss_bonus_points = (
        other_players_lost_games
        * ISKO_COUNTERPARTY_LOSS_BONUS_THREE_PLAYER_TABLE
    )
    total_performance_points = (
        player_game_points
        + own_game_bonus_points
        + opponent_loss_bonus_points
    )

    return {
        "player_game_points": player_game_points,
        "own_game_bonus_points": own_game_bonus_points,
        "opponent_loss_bonus_points": opponent_loss_bonus_points,
        "total_performance_points": total_performance_points,
        "table_size": table_size,
    }


def build_list_game_contribution_from_analysis_result(
    analysis_result: dict[str, Any],
) -> dict[str, Any] | None:
    """
    Builds one normalized list-game contribution for the local player.

    The analysis result is expected to represent the selected player as local
    "me". The returned contribution is still declarer-centric because list
    aggregation needs the declarer's settlement score and outcome.
    """
    if not isinstance(analysis_result, dict):
        raise ValueError("analysis_result must be an object.")

    position = analysis_result.get("position")
    if not isinstance(position, dict):
        raise ValueError("analysis_result.position must be an object.")

    if "player_role" not in position:
        raise ValueError("analysis_result.position.player_role is required.")

    player_role = position["player_role"]
    if player_role not in ["declarer", "defender", "unknown"]:
        raise ValueError(f"Unsupported analysis_result.position.player_role: {player_role}.")

    final_settlement_summary = analysis_result.get("final_settlement_summary")
    if not isinstance(final_settlement_summary, dict):
        raise ValueError("analysis_result.final_settlement_summary must be an object.")

    if "is_complete" not in final_settlement_summary:
        raise ValueError(
            "analysis_result.final_settlement_summary.is_complete is required."
        )

    is_complete = final_settlement_summary["is_complete"]
    if not isinstance(is_complete, bool):
        raise ValueError(
            "analysis_result.final_settlement_summary.is_complete must be a boolean."
        )

    if not is_complete:
        return None

    if "is_loss" not in final_settlement_summary:
        raise ValueError(
            "analysis_result.final_settlement_summary.is_loss is required for "
            "completed settlements."
        )

    is_loss = final_settlement_summary["is_loss"]
    if not isinstance(is_loss, bool):
        raise ValueError(
            "analysis_result.final_settlement_summary.is_loss must be a boolean "
            "for completed settlements."
        )

    if "settlement_score" not in final_settlement_summary:
        raise ValueError(
            "analysis_result.final_settlement_summary.settlement_score is required "
            "for completed settlements."
        )

    settlement_score = final_settlement_summary["settlement_score"]
    if isinstance(settlement_score, bool) or not isinstance(settlement_score, int):
        raise ValueError(
            "analysis_result.final_settlement_summary.settlement_score must be an "
            "integer for completed settlements."
        )

    if is_loss:
        game_outcome = "declarer_loss"
        if settlement_score >= 0:
            raise ValueError(
                "declarer_loss contribution requires a negative settlement_score."
            )
    else:
        game_outcome = "declarer_win"
        if settlement_score <= 0:
            raise ValueError(
                "declarer_win contribution requires a positive settlement_score."
            )

    if player_role == "unknown":
        return None

    return {
        "player_role": player_role,
        "game_outcome": game_outcome,
        "settlement_score": settlement_score,
    }


def calculate_isko_list_performance_points_from_analysis_results(
    analysis_results: list[dict[str, Any]],
    table_size: int = ISKO_FIXED_TABLE_PLAYER_COUNT,
) -> dict[str, int]:
    """
    Aggregates already-built analysis results for one local list player.

    The caller must provide results from one consistently represented local
    "me" player. Incomplete games and unknown local player roles are skipped.
    """
    if not isinstance(analysis_results, list):
        raise ValueError("analysis_results must be a list.")

    game_contributions = []
    for analysis_result in analysis_results:
        contribution = build_list_game_contribution_from_analysis_result(
            analysis_result
        )
        if contribution is not None:
            game_contributions.append(contribution)

    return calculate_isko_list_performance_points_from_game_contributions(
        game_contributions=game_contributions,
        table_size=table_size,
    )


def calculate_isko_list_performance_points_from_game_contributions(
    game_contributions: list[dict[str, Any]],
    table_size: int = ISKO_FIXED_TABLE_PLAYER_COUNT,
) -> dict[str, int]:
    """
    Aggregates normalized single-game contributions for one list player.

    The caller must provide games from one consistently represented player
    perspective. Each settlement_score is the declarer's single-game settlement
    score, not a pre-bonused performance rating score.
    """
    if table_size != ISKO_FIXED_TABLE_PLAYER_COUNT:
        raise ValueError(
            f"Unsupported ISkO list table size: {table_size}. "
            "Only three-player tables are supported."
        )

    player_game_points = 0
    own_games_won = 0
    own_games_lost = 0
    other_players_lost_games = 0

    required_fields = ["player_role", "game_outcome", "settlement_score"]

    for contribution in game_contributions:
        if not isinstance(contribution, dict):
            raise ValueError("game contribution must be an object.")

        for field_name in required_fields:
            if field_name not in contribution:
                raise ValueError(
                    "game contribution is missing required field: "
                    f"{field_name}."
                )

        additional_fields = sorted(set(contribution) - set(required_fields))
        if additional_fields:
            raise ValueError(
                "game contribution has unsupported fields: "
                f"{additional_fields}."
            )

        player_role = contribution["player_role"]
        if player_role not in ["declarer", "defender"]:
            raise ValueError(
                f"Unsupported contribution player_role: {player_role}."
            )

        game_outcome = contribution["game_outcome"]
        if game_outcome not in ["declarer_win", "declarer_loss"]:
            raise ValueError(
                f"Unsupported contribution game_outcome: {game_outcome}."
            )

        settlement_score = contribution["settlement_score"]
        if isinstance(settlement_score, bool) or not isinstance(settlement_score, int):
            raise ValueError("contribution settlement_score must be an integer.")

        if game_outcome == "declarer_win" and settlement_score <= 0:
            raise ValueError(
                "declarer_win contribution requires a positive settlement_score."
            )

        if game_outcome == "declarer_loss" and settlement_score >= 0:
            raise ValueError(
                "declarer_loss contribution requires a negative settlement_score."
            )

        if player_role == "declarer":
            player_game_points += settlement_score

            if game_outcome == "declarer_win":
                own_games_won += 1
            else:
                own_games_lost += 1

        elif game_outcome == "declarer_loss":
            other_players_lost_games += 1

    performance_points = calculate_isko_list_performance_points(
        player_game_points=player_game_points,
        own_games_won=own_games_won,
        own_games_lost=own_games_lost,
        other_players_lost_games=other_players_lost_games,
        table_size=table_size,
    )

    return {
        "player_game_points": performance_points["player_game_points"],
        "own_games_won": own_games_won,
        "own_games_lost": own_games_lost,
        "other_players_lost_games": other_players_lost_games,
        "own_game_bonus_points": performance_points["own_game_bonus_points"],
        "opponent_loss_bonus_points": performance_points[
            "opponent_loss_bonus_points"
        ],
        "total_performance_points": performance_points[
            "total_performance_points"
        ],
        "table_size": performance_points["table_size"],
    }


def build_list_performance_summary(
    list_performance_input: dict[str, int],
    rating_system: str | None,
) -> dict[str, Any]:
    """
    Builds a list/series performance summary from already aggregated totals.

    This does not aggregate raw games and stays independent from single-game
    settlement.
    """
    validate_performance_rating_system(rating_system)

    if rating_system != "isko_list":
        raise ValueError(
            "list_performance_input requires performance_rating_system to be isko_list."
        )

    performance_points = calculate_isko_list_performance_points(
        player_game_points=list_performance_input["player_game_points"],
        own_games_won=list_performance_input["own_games_won"],
        own_games_lost=list_performance_input["own_games_lost"],
        other_players_lost_games=list_performance_input["other_players_lost_games"],
    )

    return {
        "rating_system": rating_system,
        "basis": "aggregated_list_or_series_totals",
        "table_size": performance_points["table_size"],
        "player_game_points": performance_points["player_game_points"],
        "own_games_won": list_performance_input["own_games_won"],
        "own_games_lost": list_performance_input["own_games_lost"],
        "other_players_lost_games": list_performance_input[
            "other_players_lost_games"
        ],
        "own_game_bonus_points": performance_points["own_game_bonus_points"],
        "opponent_loss_bonus_points": performance_points[
            "opponent_loss_bonus_points"
        ],
        "total_performance_points": performance_points[
            "total_performance_points"
        ],
    }


def build_list_performance_summary_from_game_contributions(
    game_contributions: list[dict[str, Any]],
    rating_system: str | None,
) -> dict[str, Any]:
    """
    Builds a list/series performance summary from normalized game contributions.

    This stays independent from the currently analyzed game's settlement.
    """
    validate_performance_rating_system(rating_system)

    if rating_system != "isko_list":
        raise ValueError(
            "list_game_contributions requires performance_rating_system to be "
            "isko_list."
        )

    performance_points = calculate_isko_list_performance_points_from_game_contributions(
        game_contributions=game_contributions,
    )

    return {
        "rating_system": rating_system,
        "basis": "normalized_game_contributions",
        "table_size": performance_points["table_size"],
        "player_game_points": performance_points["player_game_points"],
        "own_games_won": performance_points["own_games_won"],
        "own_games_lost": performance_points["own_games_lost"],
        "other_players_lost_games": performance_points["other_players_lost_games"],
        "own_game_bonus_points": performance_points["own_game_bonus_points"],
        "opponent_loss_bonus_points": performance_points[
            "opponent_loss_bonus_points"
        ],
        "total_performance_points": performance_points[
            "total_performance_points"
        ],
    }


def build_list_performance_summary_from_analysis_results(
    analysis_results: list[dict[str, Any]],
    rating_system: str | None,
) -> dict[str, Any]:
    """
    Builds a list/series performance summary from local analysis results.

    The analysis results must represent the same rated player as local "me".
    """
    validate_performance_rating_system(rating_system)

    if rating_system != "isko_list":
        raise ValueError(
            "list_analysis_results requires performance_rating_system to be "
            "isko_list."
        )

    performance_points = calculate_isko_list_performance_points_from_analysis_results(
        analysis_results=analysis_results,
    )

    return {
        "rating_system": rating_system,
        "basis": "local_analysis_results",
        "table_size": performance_points["table_size"],
        "player_game_points": performance_points["player_game_points"],
        "own_games_won": performance_points["own_games_won"],
        "own_games_lost": performance_points["own_games_lost"],
        "other_players_lost_games": performance_points["other_players_lost_games"],
        "own_game_bonus_points": performance_points["own_game_bonus_points"],
        "opponent_loss_bonus_points": performance_points[
            "opponent_loss_bonus_points"
        ],
        "total_performance_points": performance_points[
            "total_performance_points"
        ],
    }


def get_game_outcome_for_rating(
    final_settlement_summary: dict[str, Any],
) -> str:
    """
    Returns the settlement outcome used as basis for later performance rating.

    This does not calculate list or tournament points yet.
    """
    if not final_settlement_summary["is_complete"]:
        return "incomplete"

    if final_settlement_summary["is_loss"] is True:
        return "declarer_loss"

    if final_settlement_summary["is_loss"] is False:
        return "declarer_win"

    return "unknown"

def calculate_isko_declarer_rating_points(
    game_outcome: str,
) -> int | None:
    """
    Calculates basic ISkO-style declarer rating points.

    This only covers the declarer's basic win/loss rating points.
    Defender and tournament/list-specific additions are added later.
    """
    if game_outcome == "declarer_win":
        return ISKO_DECLARER_WIN_POINTS

    if game_outcome == "declarer_loss":
        return ISKO_DECLARER_LOSS_POINTS

    return None

def is_performance_rating_partially_implemented(
    rating_system: str | None,
) -> bool:
    """
    Returns whether the selected rating system has partial implementation.
    """
    return rating_system == "isko_list"

def get_performance_rating_implemented_scope(
    rating_system: str | None,
) -> str | None:
    """
    Returns the scope that is currently implemented for the selected rating system.
    """
    if rating_system == "isko_list":
        return "declarer_single_game_rating"

    return None


def get_performance_rating_unsupported_scope(
    rating_system: str | None,
) -> str:
    """
    Returns the scope that is not implemented yet for the selected rating system.
    """
    if rating_system == "isko_list":
        return "full_list_series_tournament_rating"

    return "performance_rating_not_implemented"

def get_performance_rating_unsupported_reason(
    rating_system: str | None,
) -> str:
    """
    Returns why performance rating is not implemented yet.
    """
    if rating_system == "isko_list":
        return "full_list_series_tournament_rating_not_implemented"

    return "performance_rating_not_implemented"


def build_performance_rating_summary(
    final_settlement_summary: dict[str, Any],
    rating_system: str | None = None,
) -> dict[str, Any]:
    """
    Builds a performance rating scaffold.

    Performance rating is intentionally separated from individual game settlement.
    It will later cover list, series, and tournament scoring.
    """
    validate_performance_rating_system(rating_system)

    game_outcome = get_game_outcome_for_rating(final_settlement_summary)

    declarer_rating_points = None
    counterparty_rating_points = None
    declarer_rating_score = None

    if rating_system == "isko_list":
        declarer_rating_points = calculate_isko_declarer_rating_points(
            game_outcome
        )
        counterparty_rating_points = calculate_isko_counterparty_rating_points(
            game_outcome
        )
        declarer_rating_score = calculate_isko_declarer_rating_score(
            settlement_score=final_settlement_summary["settlement_score"],
            declarer_rating_points=declarer_rating_points,
        )

    return {
        "is_implemented": False,
        "is_partially_implemented": is_performance_rating_partially_implemented(
            rating_system
        ),
        "implemented_scope": get_performance_rating_implemented_scope(
            rating_system
        ),
        "unsupported_scope": get_performance_rating_unsupported_scope(
            rating_system
        ),
        "rating_system": rating_system,
        "table_player_count": ISKO_FIXED_TABLE_PLAYER_COUNT,
        "basis": "individual_game_settlement",
        "game_outcome": game_outcome,
        "settlement_score": final_settlement_summary["settlement_score"],
        "rating_score": declarer_rating_score,
        "declarer_rating_score": declarer_rating_score,
        "declarer_rating_points": declarer_rating_points,
        "counterparty_rating_points": counterparty_rating_points,
        "defender_rating_points": counterparty_rating_points,
        "unsupported_reason": get_performance_rating_unsupported_reason(
            rating_system
        ),
        "notes": [
            "Performance rating is separate from individual game settlement.",
            "rating_score currently represents the declarer's rating score.",
            "List, series, and tournament rating are not fully implemented yet.",
            "final_settlement_summary remains the source for single-game settlement.",
        ],
    }

def validate_performance_rating_system(
    rating_system: str | None,
) -> None:
    """
    Validates the optional performance rating system.
    """
    if rating_system is None:
        return

    if rating_system not in SUPPORTED_PERFORMANCE_RATING_SYSTEMS:
        raise ValueError(f"Unknown performance rating system: {rating_system}")

def calculate_isko_counterparty_rating_points(
    game_outcome: str,
) -> int | None:
    """
    Calculates ISkO-style counterparty rating points per counterparty member.

    This project assumes a fixed three-player table.
    """
    if game_outcome == "declarer_win":
        return 0

    if game_outcome == "declarer_loss":
        return ISKO_COUNTERPARTY_LOSS_BONUS_THREE_PLAYER_TABLE

    return None

def calculate_isko_declarer_rating_score(
    settlement_score: int | None,
    declarer_rating_points: int | None,
) -> int | None:
    """
    Calculates the declarer's partial ISkO-style rating score.

    This combines the individual game settlement score with the declarer's
    win/loss rating points.
    """
    if settlement_score is None or declarer_rating_points is None:
        return None

    return settlement_score + declarer_rating_points
