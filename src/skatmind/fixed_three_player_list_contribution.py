from dataclasses import dataclass
from typing import Any

from skatmind.performance_rating import (
    calculate_isko_list_performance_points,
    validate_stable_list_entry_identifier,
)


@dataclass(frozen=True)
class FixedThreePlayerListContribution:
    """One player's non-cumulative contribution at one list position."""

    player_id: str
    list_entry_count: int
    played_game_count: int
    passed_deal_count: int
    declarer_game_count: int
    defender_game_count: int
    own_games_won: int
    own_games_lost: int
    defender_games_won: int
    defender_games_lost: int
    other_players_lost_games: int
    player_game_points: int
    own_game_bonus_points: int
    opponent_loss_bonus_points: int
    total_performance_points: int


def build_fixed_three_player_list_contributions(
    *,
    player_ids: tuple[str, ...],
    entry_outcome: str,
    declarer_player_id: str | None,
    settlement_score: int | None,
) -> tuple[FixedThreePlayerListContribution, ...]:
    """Builds one canonical contribution per fixed table player."""
    if not isinstance(player_ids, tuple) or len(player_ids) != 3:
        raise ValueError("player_ids must contain exactly three players.")
    for index, player_id in enumerate(player_ids):
        validate_stable_list_entry_identifier(player_id, f"player_ids[{index}]")
    if len(set(player_ids)) != len(player_ids):
        raise ValueError("player_ids must identify three distinct players.")
    if entry_outcome not in {"declarer_win", "declarer_loss", "passed_deal"}:
        raise ValueError(f"Unsupported list entry outcome: {entry_outcome}.")
    if entry_outcome == "passed_deal":
        if declarer_player_id is not None or settlement_score is not None:
            raise ValueError("A passed deal cannot have a declarer or settlement score.")
    elif declarer_player_id not in player_ids:
        raise ValueError("A played game declarer must be one fixed list player.")
    elif isinstance(settlement_score, bool) or not isinstance(settlement_score, int):
        raise ValueError("A played game settlement score must be an integer.")
    elif entry_outcome == "declarer_win" and settlement_score <= 0:
        raise ValueError("A declarer win requires a positive settlement score.")
    elif entry_outcome == "declarer_loss" and settlement_score >= 0:
        raise ValueError("A declarer loss requires a negative settlement score.")

    contributions = []
    for player_id in player_ids:
        passed = entry_outcome == "passed_deal"
        declarer = not passed and player_id == declarer_player_id
        declarer_win = entry_outcome == "declarer_win"
        declarer_loss = entry_outcome == "declarer_loss"
        player_game_points = settlement_score if declarer else 0
        own_games_won = int(declarer and declarer_win)
        own_games_lost = int(declarer and declarer_loss)
        other_players_lost_games = int(not passed and not declarer and declarer_loss)
        points = calculate_isko_list_performance_points(
            player_game_points=player_game_points,
            own_games_won=own_games_won,
            own_games_lost=own_games_lost,
            other_players_lost_games=other_players_lost_games,
        )
        contributions.append(
            FixedThreePlayerListContribution(
                player_id=player_id,
                list_entry_count=1,
                played_game_count=int(not passed),
                passed_deal_count=int(passed),
                declarer_game_count=int(declarer),
                defender_game_count=int(not passed and not declarer),
                own_games_won=own_games_won,
                own_games_lost=own_games_lost,
                defender_games_won=other_players_lost_games,
                defender_games_lost=int(not passed and not declarer and declarer_win),
                other_players_lost_games=other_players_lost_games,
                player_game_points=player_game_points,
                own_game_bonus_points=points["own_game_bonus_points"],
                opponent_loss_bonus_points=points["opponent_loss_bonus_points"],
                total_performance_points=points["total_performance_points"],
            )
        )
    return tuple(contributions)


def build_serializable_fixed_three_player_list_contribution(
    contribution: FixedThreePlayerListContribution,
) -> dict[str, Any]:
    """Serializes one contribution in stable field order."""
    return {
        "player_id": contribution.player_id,
        "list_entry_count": contribution.list_entry_count,
        "played_game_count": contribution.played_game_count,
        "passed_deal_count": contribution.passed_deal_count,
        "declarer_game_count": contribution.declarer_game_count,
        "defender_game_count": contribution.defender_game_count,
        "own_games_won": contribution.own_games_won,
        "own_games_lost": contribution.own_games_lost,
        "defender_games_won": contribution.defender_games_won,
        "defender_games_lost": contribution.defender_games_lost,
        "other_players_lost_games": contribution.other_players_lost_games,
        "player_game_points": contribution.player_game_points,
        "own_game_bonus_points": contribution.own_game_bonus_points,
        "opponent_loss_bonus_points": contribution.opponent_loss_bonus_points,
        "total_performance_points": contribution.total_performance_points,
    }
