from dataclasses import dataclass
from typing import Any

from skat_ai.fixed_three_player_historical_list import (
    FixedThreePlayerHistoricalListEntryFact,
    build_serializable_fixed_three_player_historical_list_entry_fact,
)
from skat_ai.fixed_three_player_historical_list_standings import (
    FixedThreePlayerHistoricalListStanding,
    build_serializable_fixed_three_player_historical_list_standing,
)
from skat_ai.fixed_three_player_historical_list_totals import (
    FixedThreePlayerHistoricalListPlayerTotals,
)


@dataclass(frozen=True)
class FixedThreePlayerHistoricalListProgressionSnapshot:
    """Cumulative immutable totals and provisional standings after one entry."""

    aggregation_version: int
    list_id: str
    entry_fact: FixedThreePlayerHistoricalListEntryFact
    cumulative_player_totals: tuple[
        FixedThreePlayerHistoricalListPlayerTotals, ...
    ]
    provisional_standings: tuple[FixedThreePlayerHistoricalListStanding, ...]
    tied_player_ids: tuple[str, ...]


def build_serializable_fixed_three_player_historical_list_progression_snapshot(
    snapshot: FixedThreePlayerHistoricalListProgressionSnapshot,
) -> dict[str, Any]:
    """Serializes one privacy-safe cumulative position snapshot."""
    from skat_ai.fixed_three_player_historical_list_aggregation import (
        build_serializable_fixed_three_player_historical_list_player_totals,
    )

    return {
        "aggregation_version": snapshot.aggregation_version,
        "list_id": snapshot.list_id,
        "entry_fact": build_serializable_fixed_three_player_historical_list_entry_fact(
            snapshot.entry_fact
        ),
        "cumulative_player_totals": [
            build_serializable_fixed_three_player_historical_list_player_totals(total)
            for total in snapshot.cumulative_player_totals
        ],
        "provisional_standings": [
            build_serializable_fixed_three_player_historical_list_standing(standing)
            for standing in snapshot.provisional_standings
        ],
        "tied_player_ids": list(snapshot.tied_player_ids),
    }
