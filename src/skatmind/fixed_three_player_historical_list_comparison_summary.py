from dataclasses import dataclass
from typing import Any

from skatmind.fixed_three_player_historical_list_aggregation import (
    FixedThreePlayerHistoricalListPlayerTotals,
    build_serializable_fixed_three_player_historical_list_player_totals,
)


@dataclass(frozen=True)
class FixedThreePlayerHistoricalListComparisonCompactStanding:
    """One privacy-safe final standing retained in a source summary."""

    rank: int
    player_id: str
    player_label: str | None
    table_place: str
    total_performance_points: int
    own_games_won: int
    own_games_lost: int


@dataclass(frozen=True)
class FixedThreePlayerHistoricalListComparisonSourceSummary:
    """Compact privacy-safe facts for one independently completed source list."""

    comparison_version: int
    basis: str
    list_id: str
    source_list_schema_version: int
    entry_count: int
    round_count: int
    played_game_count: int
    passed_deal_count: int
    declarer_win_count: int
    declarer_loss_count: int
    ranking_status: str
    tied_player_ids: tuple[str, ...]
    lot_required_player_ids: tuple[str, ...]
    applied_lot_order: tuple[str, ...] | None
    final_standings: tuple[FixedThreePlayerHistoricalListComparisonCompactStanding, ...]


@dataclass(frozen=True)
class FixedThreePlayerHistoricalListPlayerTotalsDelta:
    """Comparison-minus-reference deltas for every numeric player-total field."""

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


@dataclass(frozen=True)
class FixedThreePlayerHistoricalListPlayerComparison:
    """One stable player aligned between a reference and comparison list."""

    comparison_version: int
    player_id: str
    player_label: str | None
    reference_table_place: str
    comparison_table_place: str
    reference_totals: FixedThreePlayerHistoricalListPlayerTotals
    comparison_totals: FixedThreePlayerHistoricalListPlayerTotals
    deltas: FixedThreePlayerHistoricalListPlayerTotalsDelta
    rank_comparison_status: str
    reference_rank: int | None
    comparison_rank: int | None
    rank_position_change: int | None


@dataclass(frozen=True)
class FixedThreePlayerHistoricalListPairwiseComparison:
    """One independent comparison against the first supplied source list."""

    comparison_version: int
    reference_list_id: str
    comparison_list_id: str
    reference_summary: FixedThreePlayerHistoricalListComparisonSourceSummary
    comparison_summary: FixedThreePlayerHistoricalListComparisonSourceSummary
    played_game_count_delta: int
    passed_deal_count_delta: int
    declarer_win_count_delta: int
    declarer_loss_count_delta: int
    final_rank_comparison_available: bool
    player_comparisons: tuple[FixedThreePlayerHistoricalListPlayerComparison, ...]


@dataclass(frozen=True)
class FixedThreePlayerHistoricalListComparisonResult:
    """Ordered independent completed-list comparisons with one fixed reference."""

    comparison_version: int
    basis: str
    reference_list_id: str
    list_count: int
    player_ids: tuple[str, ...]
    source_lists: tuple[FixedThreePlayerHistoricalListComparisonSourceSummary, ...]
    comparisons: tuple[FixedThreePlayerHistoricalListPairwiseComparison, ...]


def build_serializable_fixed_three_player_historical_list_comparison_compact_standing(
    standing: FixedThreePlayerHistoricalListComparisonCompactStanding,
) -> dict[str, Any]:
    """Serializes one compact final standing in stable field order."""
    return {
        "rank": standing.rank,
        "player_id": standing.player_id,
        "player_label": standing.player_label,
        "table_place": standing.table_place,
        "total_performance_points": standing.total_performance_points,
        "own_games_won": standing.own_games_won,
        "own_games_lost": standing.own_games_lost,
    }


def build_serializable_fixed_three_player_historical_list_comparison_source_summary(
    summary: FixedThreePlayerHistoricalListComparisonSourceSummary,
) -> dict[str, Any]:
    """Serializes one compact source-list summary without retained Entry Facts."""
    return {
        "comparison_version": summary.comparison_version,
        "basis": summary.basis,
        "list_id": summary.list_id,
        "source_list_schema_version": summary.source_list_schema_version,
        "entry_count": summary.entry_count,
        "round_count": summary.round_count,
        "played_game_count": summary.played_game_count,
        "passed_deal_count": summary.passed_deal_count,
        "declarer_win_count": summary.declarer_win_count,
        "declarer_loss_count": summary.declarer_loss_count,
        "ranking_status": summary.ranking_status,
        "tied_player_ids": list(summary.tied_player_ids),
        "lot_required_player_ids": list(summary.lot_required_player_ids),
        "applied_lot_order": (
            None if summary.applied_lot_order is None else list(summary.applied_lot_order)
        ),
        "final_standings": [
            build_serializable_fixed_three_player_historical_list_comparison_compact_standing(
                standing
            )
            for standing in summary.final_standings
        ],
    }


def build_serializable_fixed_three_player_historical_list_player_totals_delta(
    delta: FixedThreePlayerHistoricalListPlayerTotalsDelta,
) -> dict[str, int]:
    """Serializes every numeric player-total delta in source-field order."""
    return {
        "list_entry_count": delta.list_entry_count,
        "played_game_count": delta.played_game_count,
        "passed_deal_count": delta.passed_deal_count,
        "declarer_game_count": delta.declarer_game_count,
        "defender_game_count": delta.defender_game_count,
        "own_games_won": delta.own_games_won,
        "own_games_lost": delta.own_games_lost,
        "defender_games_won": delta.defender_games_won,
        "defender_games_lost": delta.defender_games_lost,
        "other_players_lost_games": delta.other_players_lost_games,
        "player_game_points": delta.player_game_points,
        "own_game_bonus_points": delta.own_game_bonus_points,
        "opponent_loss_bonus_points": delta.opponent_loss_bonus_points,
        "total_performance_points": delta.total_performance_points,
    }


def build_serializable_fixed_three_player_historical_list_player_comparison(
    comparison: FixedThreePlayerHistoricalListPlayerComparison,
) -> dict[str, Any]:
    """Serializes one player comparison with explicit nullable rank fields."""
    return {
        "comparison_version": comparison.comparison_version,
        "player_id": comparison.player_id,
        "player_label": comparison.player_label,
        "reference_table_place": comparison.reference_table_place,
        "comparison_table_place": comparison.comparison_table_place,
        "reference_totals": (
            build_serializable_fixed_three_player_historical_list_player_totals(
                comparison.reference_totals
            )
        ),
        "comparison_totals": (
            build_serializable_fixed_three_player_historical_list_player_totals(
                comparison.comparison_totals
            )
        ),
        "deltas": build_serializable_fixed_three_player_historical_list_player_totals_delta(
            comparison.deltas
        ),
        "rank_comparison_status": comparison.rank_comparison_status,
        "reference_rank": comparison.reference_rank,
        "comparison_rank": comparison.comparison_rank,
        "rank_position_change": comparison.rank_position_change,
    }


def build_serializable_fixed_three_player_historical_list_pairwise_comparison(
    comparison: FixedThreePlayerHistoricalListPairwiseComparison,
) -> dict[str, Any]:
    """Serializes one ordered comparison against the fixed reference."""
    return {
        "comparison_version": comparison.comparison_version,
        "reference_list_id": comparison.reference_list_id,
        "comparison_list_id": comparison.comparison_list_id,
        "reference_summary": (
            build_serializable_fixed_three_player_historical_list_comparison_source_summary(
                comparison.reference_summary
            )
        ),
        "comparison_summary": (
            build_serializable_fixed_three_player_historical_list_comparison_source_summary(
                comparison.comparison_summary
            )
        ),
        "played_game_count_delta": comparison.played_game_count_delta,
        "passed_deal_count_delta": comparison.passed_deal_count_delta,
        "declarer_win_count_delta": comparison.declarer_win_count_delta,
        "declarer_loss_count_delta": comparison.declarer_loss_count_delta,
        "final_rank_comparison_available": comparison.final_rank_comparison_available,
        "player_comparisons": [
            build_serializable_fixed_three_player_historical_list_player_comparison(player)
            for player in comparison.player_comparisons
        ],
    }


def build_serializable_fixed_three_player_historical_list_comparison(
    result: FixedThreePlayerHistoricalListComparisonResult,
) -> dict[str, Any]:
    """Serializes the ordered comparison result without source-private detail."""
    return {
        "comparison_version": result.comparison_version,
        "basis": result.basis,
        "reference_list_id": result.reference_list_id,
        "list_count": result.list_count,
        "player_ids": list(result.player_ids),
        "source_lists": [
            build_serializable_fixed_three_player_historical_list_comparison_source_summary(summary)
            for summary in result.source_lists
        ],
        "comparisons": [
            build_serializable_fixed_three_player_historical_list_pairwise_comparison(comparison)
            for comparison in result.comparisons
        ],
    }
