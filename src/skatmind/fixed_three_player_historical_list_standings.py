from dataclasses import dataclass
from typing import Any

from skatmind.fixed_three_player_historical_list_totals import (
    FixedThreePlayerHistoricalListPlayerTotals,
)
from skatmind.fixed_three_player_list_rotation import (
    FIXED_THREE_PLAYER_LIST_TABLE_PLACES,
)
from skatmind.performance_rating import (
    apply_list_standings_ranks_and_lot,
    get_list_standings_ranking_key,
    get_list_standings_tie_group,
)


@dataclass(frozen=True)
class FixedThreePlayerHistoricalListStanding:
    """One immutable SkWO standings row backed by cumulative totals."""

    rank: int
    player_totals: FixedThreePlayerHistoricalListPlayerTotals


@dataclass(frozen=True)
class FixedThreePlayerHistoricalListStandingsResult:
    """One immutable pre-lot tie and optional external-lot result."""

    standings: tuple[FixedThreePlayerHistoricalListStanding, ...]
    tied_player_ids: tuple[str, ...]
    applied_lot_order: tuple[str, ...] | None


def build_fixed_three_player_historical_list_standings(
    player_totals: tuple[FixedThreePlayerHistoricalListPlayerTotals, ...],
    *,
    lot_order: Any = None,
) -> FixedThreePlayerHistoricalListStandingsResult:
    """Ranks canonical totals and applies only a supplied exact external lot."""
    if not isinstance(player_totals, tuple) or len(player_totals) != 3:
        raise ValueError("player_totals must contain exactly three players.")
    from skatmind.fixed_three_player_historical_list_aggregation import (
        validate_fixed_three_player_historical_list_player_totals,
    )

    for total in player_totals:
        validate_fixed_three_player_historical_list_player_totals(total)
    if tuple(total.table_place for total in player_totals) != (
        FIXED_THREE_PLAYER_LIST_TABLE_PLACES
    ):
        raise ValueError("player_totals must use canonical table-place order.")
    player_ids = tuple(total.player_id for total in player_totals)
    if len(set(player_ids)) != len(player_ids):
        raise ValueError("player_totals must identify three distinct players.")

    rows = [
        {
            "rank": 0,
            "input_order": input_order,
            "player_id": total.player_id,
            "total_performance_points": total.total_performance_points,
            "own_games_won": total.own_games_won,
            "own_games_lost": total.own_games_lost,
        }
        for input_order, total in enumerate(player_totals, start=1)
    ]
    rows.sort(
        key=lambda row: (
            *get_list_standings_ranking_key(row),
            row["input_order"],
        )
    )
    tied_player_ids = tuple(
        row["player_id"] for row in get_list_standings_tie_group(rows)
    )
    lot_order_supplied = lot_order is not None
    apply_list_standings_ranks_and_lot(
        rows,
        lot_order=lot_order,
        lot_order_supplied=lot_order_supplied,
    )

    totals_by_player_id = {total.player_id: total for total in player_totals}
    standings = tuple(
        FixedThreePlayerHistoricalListStanding(
            rank=row["rank"],
            player_totals=totals_by_player_id[row["player_id"]],
        )
        for row in rows
    )
    return FixedThreePlayerHistoricalListStandingsResult(
        standings=standings,
        tied_player_ids=tied_player_ids,
        applied_lot_order=tuple(lot_order) if lot_order_supplied else None,
    )


def build_serializable_fixed_three_player_historical_list_standing(
    standing: FixedThreePlayerHistoricalListStanding,
) -> dict[str, Any]:
    """Serializes one standings row without flattening or copying its metrics."""
    from skatmind.fixed_three_player_historical_list_aggregation import (
        build_serializable_fixed_three_player_historical_list_player_totals,
    )

    return {
        "rank": standing.rank,
        "player_totals": (
            build_serializable_fixed_three_player_historical_list_player_totals(
                standing.player_totals
            )
        ),
    }
