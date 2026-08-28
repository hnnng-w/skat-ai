from dataclasses import dataclass


@dataclass(frozen=True)
class FixedThreePlayerHistoricalListPlayerTotals:
    """One player's immutable cumulative totals in a historical list."""

    player_id: str
    player_label: str | None
    table_place: str
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
