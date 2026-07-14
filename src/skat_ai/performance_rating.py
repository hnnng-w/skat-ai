from typing import Any

SUPPORTED_PERFORMANCE_RATING_SYSTEMS = [
    "placeholder",
    "isko_list",
]
ISKO_DECLARER_WIN_POINTS = 50
ISKO_DECLARER_LOSS_POINTS = -50
ISKO_COUNTERPARTY_LOSS_BONUS_THREE_PLAYER_TABLE = 40
ISKO_FIXED_TABLE_PLAYER_COUNT = 3
LIST_ENTRY_METADATA_FIELDS = [
    "rated_player_id",
    "game_id",
]
LIST_STANDINGS_INPUT_REQUIRED_FIELDS = [
    "players",
    "games",
]
LIST_STANDINGS_INPUT_OPTIONAL_FIELDS = [
    "lot_order",
]
LIST_STANDINGS_PLAYER_REQUIRED_FIELDS = [
    "player_id",
]
LIST_STANDINGS_PLAYER_OPTIONAL_FIELDS = [
    "player_label",
]
LIST_STANDINGS_GAME_REQUIRED_FIELDS = [
    "declarer_player_id",
    "game_outcome",
    "settlement_score",
]
LIST_STANDINGS_GAME_OPTIONAL_FIELDS = [
    "game_id",
]
LIST_STANDINGS_BASIS = "fixed_three_player_game_results"


def validate_stable_list_entry_identifier(
    value: Any,
    field_path: str,
) -> None:
    """
    Validates one opaque stable identifier for list aggregation metadata.

    Identifiers are intentionally not normalized. Leading or trailing whitespace
    is rejected instead of being trimmed.
    """
    if not isinstance(value, str):
        raise ValueError(
            f"{field_path} must be a non-empty string without leading or "
            "trailing whitespace."
        )

    if value == "" or value.strip() == "":
        raise ValueError(
            f"{field_path} must be a non-empty string without leading or "
            "trailing whitespace."
        )

    if value != value.strip():
        raise ValueError(
            f"{field_path} must be a non-empty string without leading or "
            "trailing whitespace."
        )


def validate_list_entry_metadata(
    entries: list[Any],
    input_mode: str,
) -> None:
    """
    Validates optional stable metadata for per-game list aggregation entries.

    The validation is intentionally independent from scoring. It checks only
    supplied rated-player and game identifiers before aggregation ignores them.
    """
    if not isinstance(entries, list):
        raise ValueError(f"{input_mode} must be a list.")

    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue

        for field_name in LIST_ENTRY_METADATA_FIELDS:
            if field_name in entry:
                validate_stable_list_entry_identifier(
                    entry[field_name],
                    f"{input_mode}[{index}].{field_name}",
                )

    rated_player_indexes = [
        index
        for index, entry in enumerate(entries)
        if isinstance(entry, dict) and "rated_player_id" in entry
    ]

    if rated_player_indexes and len(rated_player_indexes) != len(entries):
        missing_indexes = [
            index
            for index, entry in enumerate(entries)
            if not isinstance(entry, dict) or "rated_player_id" not in entry
        ]
        raise ValueError(
            f"{input_mode}.rated_player_id must be supplied for every entry "
            "or omitted from every entry; "
            f"supplied indexes: {rated_player_indexes}; "
            f"missing indexes: {missing_indexes}."
        )

    if rated_player_indexes:
        first_index = rated_player_indexes[0]
        first_id = entries[first_index]["rated_player_id"]

        for index in rated_player_indexes[1:]:
            rated_player_id = entries[index]["rated_player_id"]
            if rated_player_id != first_id:
                raise ValueError(
                    f"{input_mode}.rated_player_id values conflict: "
                    f"index {first_index} has {first_id!r}, "
                    f"index {index} has {rated_player_id!r}."
                )

    game_id_first_index: dict[str, int] = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or "game_id" not in entry:
            continue

        game_id = entry["game_id"]
        if game_id in game_id_first_index:
            raise ValueError(
                f"Duplicate {input_mode}.game_id {game_id!r} at indexes "
                f"{game_id_first_index[game_id]} and {index}."
            )

        game_id_first_index[game_id] = index


def validate_stable_list_player_label(value: Any, field_path: str) -> None:
    """Validates an optional human-readable player label."""
    if not isinstance(value, str):
        raise ValueError(
            f"{field_path} must be a non-empty string without leading or "
            "trailing whitespace."
        )

    if value == "" or value.strip() == "":
        raise ValueError(
            f"{field_path} must be a non-empty string without leading or "
            "trailing whitespace."
        )

    if value != value.strip():
        raise ValueError(
            f"{field_path} must be a non-empty string without leading or "
            "trailing whitespace."
        )


def validate_list_standings_input(
    list_standings_input: Any,
    rating_system: str | None,
) -> None:
    """Validates fixed three-player list standings input."""
    validate_performance_rating_system(rating_system)

    if rating_system != "isko_list":
        raise ValueError(
            "list_standings_input requires performance_rating_system to be "
            "isko_list."
        )

    if not isinstance(list_standings_input, dict):
        raise ValueError("list_standings_input must be an object.")

    supported_fields = set(LIST_STANDINGS_INPUT_REQUIRED_FIELDS) | set(
        LIST_STANDINGS_INPUT_OPTIONAL_FIELDS
    )
    additional_fields = sorted(set(list_standings_input) - supported_fields)
    if additional_fields:
        raise ValueError(
            "list_standings_input has unsupported keys: "
            f"{additional_fields}."
        )

    missing_fields = [
        field_name
        for field_name in LIST_STANDINGS_INPUT_REQUIRED_FIELDS
        if field_name not in list_standings_input
    ]
    if missing_fields:
        raise ValueError(
            "list_standings_input is missing required keys: "
            f"{missing_fields}."
        )

    players = list_standings_input["players"]
    if not isinstance(players, list):
        raise ValueError("list_standings_input.players must be a list.")

    if len(players) != ISKO_FIXED_TABLE_PLAYER_COUNT:
        raise ValueError(
            "list_standings_input.players must contain exactly three players."
        )

    player_ids = []
    for index, player in enumerate(players):
        field_prefix = f"list_standings_input.players[{index}]"
        if not isinstance(player, dict):
            raise ValueError(f"{field_prefix} must be an object.")

        supported_player_fields = set(LIST_STANDINGS_PLAYER_REQUIRED_FIELDS) | set(
            LIST_STANDINGS_PLAYER_OPTIONAL_FIELDS
        )
        additional_player_fields = sorted(set(player) - supported_player_fields)
        if additional_player_fields:
            raise ValueError(
                f"{field_prefix} has unsupported keys: "
                f"{additional_player_fields}."
            )

        if "player_id" not in player:
            raise ValueError(f"{field_prefix} is missing required key: player_id.")

        validate_stable_list_entry_identifier(
            player["player_id"],
            f"{field_prefix}.player_id",
        )
        if "player_label" in player:
            validate_stable_list_player_label(
                player["player_label"],
                f"{field_prefix}.player_label",
            )

        player_ids.append(player["player_id"])

    duplicate_player_ids = sorted({
        player_id for player_id in player_ids if player_ids.count(player_id) > 1
    })
    if duplicate_player_ids:
        raise ValueError(
            "list_standings_input.players contains duplicate player_id values: "
            f"{duplicate_player_ids}."
        )

    if "lot_order" in list_standings_input:
        lot_order = list_standings_input["lot_order"]
        if not isinstance(lot_order, list):
            raise ValueError("list_standings_input.lot_order must be a list.")

        if len(lot_order) < 2 or len(lot_order) > 3:
            raise ValueError(
                "list_standings_input.lot_order must contain two or three "
                "player IDs."
            )

        for index, player_id in enumerate(lot_order):
            validate_stable_list_entry_identifier(
                player_id,
                f"list_standings_input.lot_order[{index}]",
            )

        duplicate_lot_player_ids = sorted({
            player_id for player_id in lot_order if lot_order.count(player_id) > 1
        })
        if duplicate_lot_player_ids:
            raise ValueError(
                "list_standings_input.lot_order contains duplicate player IDs: "
                f"{duplicate_lot_player_ids}."
            )

        unknown_lot_player_ids = sorted(set(lot_order) - set(player_ids))
        if unknown_lot_player_ids:
            raise ValueError(
                "list_standings_input.lot_order contains unknown player IDs: "
                f"{unknown_lot_player_ids}."
            )

    games = list_standings_input["games"]
    if not isinstance(games, list):
        raise ValueError("list_standings_input.games must be a list.")

    known_player_ids = set(player_ids)
    game_id_first_index: dict[str, int] = {}
    for index, game in enumerate(games):
        field_prefix = f"list_standings_input.games[{index}]"
        if not isinstance(game, dict):
            raise ValueError(f"{field_prefix} must be an object.")

        supported_game_fields = set(LIST_STANDINGS_GAME_REQUIRED_FIELDS) | set(
            LIST_STANDINGS_GAME_OPTIONAL_FIELDS
        )
        additional_game_fields = sorted(set(game) - supported_game_fields)
        if additional_game_fields:
            raise ValueError(
                f"{field_prefix} has unsupported keys: {additional_game_fields}."
            )

        missing_game_fields = [
            field_name
            for field_name in LIST_STANDINGS_GAME_REQUIRED_FIELDS
            if field_name not in game
        ]
        if missing_game_fields:
            raise ValueError(
                f"{field_prefix} is missing required keys: {missing_game_fields}."
            )

        if "game_id" in game:
            validate_stable_list_entry_identifier(
                game["game_id"],
                f"{field_prefix}.game_id",
            )
            game_id = game["game_id"]
            if game_id in game_id_first_index:
                raise ValueError(
                    "Duplicate list_standings_input.games.game_id "
                    f"{game_id!r} at indexes {game_id_first_index[game_id]} "
                    f"and {index}."
                )
            game_id_first_index[game_id] = index

        declarer_player_id = game["declarer_player_id"]
        validate_stable_list_entry_identifier(
            declarer_player_id,
            f"{field_prefix}.declarer_player_id",
        )
        if declarer_player_id not in known_player_ids:
            raise ValueError(
                f"{field_prefix}.declarer_player_id must reference one of "
                "list_standings_input.players."
            )

        game_outcome = game["game_outcome"]
        if game_outcome not in ["declarer_win", "declarer_loss"]:
            raise ValueError(f"Unsupported {field_prefix}.game_outcome: {game_outcome}.")

        settlement_score = game["settlement_score"]
        if isinstance(settlement_score, bool) or not isinstance(settlement_score, int):
            raise ValueError(f"{field_prefix}.settlement_score must be an integer.")

        if game_outcome == "declarer_win" and settlement_score <= 0:
            raise ValueError(
                f"{field_prefix} declarer_win requires a positive "
                "settlement_score."
            )

        if game_outcome == "declarer_loss" and settlement_score >= 0:
            raise ValueError(
                f"{field_prefix} declarer_loss requires a negative "
                "settlement_score."
            )

    # Cross-check the external lot result against the calculated official tie.
    calculate_isko_fixed_three_player_standings(list_standings_input)


def get_list_standings_ranking_key(row: dict[str, Any]) -> tuple[int, int, int]:
    """Returns the complete SkWO 6.3.1 standings comparison key."""
    return (
        -row["total_performance_points"],
        -row["own_games_won"],
        row["own_games_lost"],
    )


def get_list_standings_tie_group(
    standings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Returns the one unresolved official tie group, if present."""
    for index, row in enumerate(standings):
        ranking_key = get_list_standings_ranking_key(row)
        tie_group = [
            tied_row
            for tied_row in standings[index:]
            if get_list_standings_ranking_key(tied_row) == ranking_key
        ]
        if len(tie_group) > 1:
            return tie_group

    return []


def apply_list_standings_ranks_and_lot(
    standings: list[dict[str, Any]],
    lot_order: Any = None,
    lot_order_supplied: bool = False,
) -> None:
    """Assigns competition ranks and applies one validated external lot result."""
    for index, row in enumerate(standings):
        if (
            index > 0
            and get_list_standings_ranking_key(row)
            == get_list_standings_ranking_key(standings[index - 1])
        ):
            row["rank"] = standings[index - 1]["rank"]
        else:
            row["rank"] = index + 1

    tie_group = get_list_standings_tie_group(standings)
    if not lot_order_supplied:
        return

    if not isinstance(lot_order, list):
        raise ValueError("list_standings_input.lot_order must be a list.")

    if len(lot_order) < 2 or len(lot_order) > 3:
        raise ValueError(
            "list_standings_input.lot_order must contain two or three player IDs."
        )

    for index, player_id in enumerate(lot_order):
        validate_stable_list_entry_identifier(
            player_id,
            f"list_standings_input.lot_order[{index}]",
        )

    duplicate_player_ids = sorted({
        player_id for player_id in lot_order if lot_order.count(player_id) > 1
    })
    if duplicate_player_ids:
        raise ValueError(
            "list_standings_input.lot_order contains duplicate player IDs: "
            f"{duplicate_player_ids}."
        )

    standings_player_ids = {row["player_id"] for row in standings}
    unknown_player_ids = sorted(set(lot_order) - standings_player_ids)
    if unknown_player_ids:
        raise ValueError(
            "list_standings_input.lot_order contains unknown player IDs: "
            f"{unknown_player_ids}."
        )

    if not tie_group:
        raise ValueError(
            "list_standings_input.lot_order cannot be supplied when no "
            "unresolved tie exists."
        )

    tied_player_ids = {row["player_id"] for row in tie_group}
    supplied_player_ids = set(lot_order)
    missing_player_ids = sorted(tied_player_ids - supplied_player_ids)
    extra_player_ids = sorted(supplied_player_ids - tied_player_ids)
    if missing_player_ids or extra_player_ids:
        raise ValueError(
            "list_standings_input.lot_order must contain exactly the unresolved "
            f"tied players; missing: {missing_player_ids}; extra non-tied: "
            f"{extra_player_ids}."
        )

    tie_start = standings.index(tie_group[0])
    rows_by_player_id = {row["player_id"]: row for row in tie_group}
    standings[tie_start : tie_start + len(tie_group)] = [
        rows_by_player_id[player_id] for player_id in lot_order
    ]
    for offset, row in enumerate(
        standings[tie_start : tie_start + len(tie_group)],
        start=tie_start + 1,
    ):
        row["rank"] = offset


def calculate_isko_fixed_three_player_standings(
    list_standings_input: dict[str, Any],
    table_size: int = ISKO_FIXED_TABLE_PLAYER_COUNT,
) -> list[dict[str, Any]]:
    """Aggregates SkWO-governed standings for the fixed three-player model."""
    if table_size != ISKO_FIXED_TABLE_PLAYER_COUNT:
        raise ValueError(
            f"Unsupported ISkO list table size: {table_size}. "
            "Only three-player tables are supported."
        )

    players = list_standings_input["players"]
    games = list_standings_input["games"]
    game_count = len(games)
    rows_by_player_id = {}

    for index, player in enumerate(players):
        player_id = player["player_id"]
        rows_by_player_id[player_id] = {
            "rank": 0,
            "input_order": index + 1,
            "player_id": player_id,
            "player_label": player.get("player_label"),
            "games_played": game_count,
            "declarer_games": 0,
            "defender_games": 0,
            "own_games_won": 0,
            "own_games_lost": 0,
            "defender_games_won": 0,
            "defender_games_lost": 0,
            "other_players_lost_games": 0,
            "player_game_points": 0,
            "own_game_bonus_points": 0,
            "opponent_loss_bonus_points": 0,
            "total_performance_points": 0,
        }

    for game in games:
        declarer_player_id = game["declarer_player_id"]
        game_outcome = game["game_outcome"]
        settlement_score = game["settlement_score"]

        for player_id, row in rows_by_player_id.items():
            if player_id == declarer_player_id:
                row["declarer_games"] += 1
                row["player_game_points"] += settlement_score
                if game_outcome == "declarer_win":
                    row["own_games_won"] += 1
                else:
                    row["own_games_lost"] += 1
            elif game_outcome == "declarer_loss":
                row["defender_games_won"] += 1
                row["other_players_lost_games"] += 1
            else:
                row["defender_games_lost"] += 1

    for row in rows_by_player_id.values():
        row["defender_games"] = game_count - row["declarer_games"]
        performance_points = calculate_isko_list_performance_points(
            player_game_points=row["player_game_points"],
            own_games_won=row["own_games_won"],
            own_games_lost=row["own_games_lost"],
            other_players_lost_games=row["other_players_lost_games"],
            table_size=table_size,
        )
        row["own_game_bonus_points"] = performance_points["own_game_bonus_points"]
        row["opponent_loss_bonus_points"] = performance_points[
            "opponent_loss_bonus_points"
        ]
        row["total_performance_points"] = performance_points[
            "total_performance_points"
        ]

    standings = sorted(
        rows_by_player_id.values(),
        key=lambda row: (
            *get_list_standings_ranking_key(row),
            row["input_order"],
        ),
    )
    apply_list_standings_ranks_and_lot(
        standings,
        lot_order=list_standings_input.get("lot_order"),
        lot_order_supplied="lot_order" in list_standings_input,
    )

    return standings


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

    validate_list_entry_metadata(
        entries=analysis_results,
        input_mode="list_analysis_results",
    )

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
    validate_list_entry_metadata(
        entries=game_contributions,
        input_mode="list_game_contributions",
    )

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

        supported_fields = set(required_fields) | set(LIST_ENTRY_METADATA_FIELDS)
        additional_fields = sorted(set(contribution) - supported_fields)
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


def build_list_standings_summary(
    list_standings_input: dict[str, Any],
    rating_system: str | None,
) -> dict[str, Any]:
    """Builds fixed three-player list standings from explicit game results."""
    validate_list_standings_input(
        list_standings_input=list_standings_input,
        rating_system=rating_system,
    )
    standings = calculate_isko_fixed_three_player_standings(
        list_standings_input=list_standings_input,
    )
    tie_group = get_list_standings_tie_group(standings)
    applied_lot_order = list_standings_input.get("lot_order")
    ranking_status = "final"
    lot_required_player_ids = []
    if tie_group and applied_lot_order is None:
        ranking_status = "lot_required"
        lot_required_player_ids = [row["player_id"] for row in tie_group]

    return {
        "rating_system": rating_system,
        "basis": LIST_STANDINGS_BASIS,
        "table_size": ISKO_FIXED_TABLE_PLAYER_COUNT,
        "player_count": ISKO_FIXED_TABLE_PLAYER_COUNT,
        "game_count": len(list_standings_input["games"]),
        "ranking_status": ranking_status,
        "lot_required_player_ids": lot_required_player_ids,
        "applied_lot_order": applied_lot_order,
        "standings": standings,
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
