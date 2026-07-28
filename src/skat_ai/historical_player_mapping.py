from dataclasses import dataclass
from typing import Any

HISTORICAL_SEATS = ("forehand", "middlehand", "rearhand")
FLAT_PLAYERS = ("me", "left", "right")


@dataclass(frozen=True)
class HistoricalPlayerMapping:
    """Deterministic circular mapping between stable and flat player identities."""

    stable_to_flat: tuple[tuple[str, str], ...]
    flat_to_stable: tuple[tuple[str, str], ...]

    def to_flat(self, player_id: str) -> str:
        return dict(self.stable_to_flat)[player_id]

    def to_stable(self, player: str) -> str:
        return dict(self.flat_to_stable)[player]


def build_historical_player_mapping(record: Any) -> HistoricalPlayerMapping:
    """Maps the declarer to me while preserving clockwise historical seat order."""
    seat_order = tuple(
        next(player.player_id for player in record.players if player.seat == seat)
        for seat in HISTORICAL_SEATS
    )
    declarer_index = seat_order.index(record.declarer_player_id)
    stable_order = tuple(
        seat_order[(declarer_index + offset) % len(seat_order)]
        for offset in range(len(seat_order))
    )
    stable_to_flat = tuple(zip(stable_order, FLAT_PLAYERS, strict=True))
    return HistoricalPlayerMapping(
        stable_to_flat=stable_to_flat,
        flat_to_stable=tuple(
            (flat_player, stable_id) for stable_id, flat_player in stable_to_flat
        ),
    )
