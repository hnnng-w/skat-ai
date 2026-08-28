from dataclasses import dataclass
from typing import Any

FIXED_THREE_PLAYER_LIST_TABLE_PLACES = (
    "place_1",
    "place_2",
    "place_3",
)


@dataclass(frozen=True)
class FixedThreePlayerListSeatAssignment:
    """Stable players assigned to the rotating historical seats for one entry."""

    dealer_player_id: str
    forehand_player_id: str
    middlehand_player_id: str
    rearhand_player_id: str


def build_fixed_three_player_list_seat_assignment(
    entry_number: int,
    player_id_by_place: dict[str, str],
) -> FixedThreePlayerListSeatAssignment:
    """Derives dealer and play seats for one fixed-three-player list position."""
    if isinstance(entry_number, bool) or not isinstance(entry_number, int):
        raise ValueError("entry_number must be an integer.")
    if not 1 <= entry_number <= 36:
        raise ValueError("entry_number must be between 1 and 36.")
    if tuple(player_id_by_place) != FIXED_THREE_PLAYER_LIST_TABLE_PLACES:
        raise ValueError("player_id_by_place must use canonical table-place order.")
    player_ids = tuple(player_id_by_place.values())
    if any(
        not isinstance(player_id, str)
        or not player_id
        or player_id != player_id.strip()
        for player_id in player_ids
    ):
        raise ValueError("player_id_by_place values must be stable player IDs.")
    if len(set(player_ids)) != len(player_ids):
        raise ValueError("player_id_by_place values must identify three distinct players.")

    dealer_index = (entry_number - 1) % len(FIXED_THREE_PLAYER_LIST_TABLE_PLACES)
    dealer_place = FIXED_THREE_PLAYER_LIST_TABLE_PLACES[dealer_index]
    forehand_place = FIXED_THREE_PLAYER_LIST_TABLE_PLACES[(dealer_index + 1) % 3]
    middlehand_place = FIXED_THREE_PLAYER_LIST_TABLE_PLACES[(dealer_index + 2) % 3]
    dealer_player_id = player_id_by_place[dealer_place]
    return FixedThreePlayerListSeatAssignment(
        dealer_player_id=dealer_player_id,
        forehand_player_id=player_id_by_place[forehand_place],
        middlehand_player_id=player_id_by_place[middlehand_place],
        rearhand_player_id=dealer_player_id,
    )


def build_serializable_fixed_three_player_list_seat_assignment(
    assignment: FixedThreePlayerListSeatAssignment,
) -> dict[str, Any]:
    """Serializes one seat assignment in canonical dealer and seat order."""
    return {
        "dealer_player_id": assignment.dealer_player_id,
        "forehand_player_id": assignment.forehand_player_id,
        "middlehand_player_id": assignment.middlehand_player_id,
        "rearhand_player_id": assignment.rearhand_player_id,
    }
