from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any

from skat_ai.game_declaration import (
    SUIT_GAME_TYPES,
    GameDeclaration,
    get_base_game_value,
    validate_matadors,
)
from skat_ai.overbid import calculate_required_overbid_game_value

REPLACEMENT_GAME_TYPES = [*SUIT_GAME_TYPES, "grand"]
REPLACEMENT_SELECTION_FIELDS = {"replacement_game_type", "matadors"}


@dataclass(frozen=True)
class ImpossibleNullSettlementSelection:
    """Externally selected Suit or Grand replacement used only for settlement."""

    replacement_game_type: str
    matadors: int

    def __post_init__(self) -> None:
        if self.replacement_game_type not in REPLACEMENT_GAME_TYPES:
            raise ValueError(
                "impossible_null_settlement.replacement_game_type must be one of "
                f"{REPLACEMENT_GAME_TYPES}."
            )

        try:
            validate_matadors(self.matadors, self.replacement_game_type)
        except ValueError as error:
            raise ValueError(
                f"impossible_null_settlement.{error}"
            ) from error


@dataclass(frozen=True)
class ImpossibleNullSettlementSummary:
    """Calculated scoring summary for one impossible Null replacement selection."""

    replacement_game_type: str
    matadors: int
    hand_game: bool
    base_value: int
    minimum_game_value: int
    required_game_value: int


def build_impossible_null_settlement_selection_from_input(
    data: dict[str, Any],
) -> ImpossibleNullSettlementSelection | None:
    """Builds the optional external replacement selection from public input."""
    if "impossible_null_settlement" not in data:
        return None

    raw_selection = data["impossible_null_settlement"]
    if not isinstance(raw_selection, Mapping):
        raise ValueError("impossible_null_settlement must be an object.")

    missing_fields = sorted(REPLACEMENT_SELECTION_FIELDS - set(raw_selection))
    if missing_fields:
        raise ValueError(
            "impossible_null_settlement is missing required keys: "
            f"{missing_fields}"
        )

    additional_fields = sorted(set(raw_selection) - REPLACEMENT_SELECTION_FIELDS)
    if additional_fields:
        raise ValueError(
            "impossible_null_settlement has unsupported keys: "
            f"{additional_fields}"
        )

    return ImpossibleNullSettlementSelection(
        replacement_game_type=raw_selection["replacement_game_type"],
        matadors=raw_selection["matadors"],
    )


def build_impossible_null_settlement_summary(
    selection: ImpossibleNullSettlementSelection,
    original_declaration: GameDeclaration,
) -> ImpossibleNullSettlementSummary:
    """Calculates the replacement value while preserving the original Null declaration."""
    if original_declaration.game_type != "null":
        raise ValueError("Impossible Null settlement requires a Null declaration.")

    if original_declaration.bid_value is None:
        raise ValueError("Impossible Null settlement requires bid_value.")

    base_value = get_base_game_value(selection.replacement_game_type)
    minimum_multiplier = (
        selection.matadors + 1 + int(original_declaration.hand_game)
    )
    minimum_game_value = base_value * minimum_multiplier
    rounded_bid_value = calculate_required_overbid_game_value(
        bid_value=original_declaration.bid_value,
        base_value=base_value,
    )

    return ImpossibleNullSettlementSummary(
        replacement_game_type=selection.replacement_game_type,
        matadors=selection.matadors,
        hand_game=original_declaration.hand_game,
        base_value=base_value,
        minimum_game_value=minimum_game_value,
        required_game_value=max(minimum_game_value, rounded_bid_value),
    )


def build_serializable_impossible_null_settlement_summary(
    summary: ImpossibleNullSettlementSummary | None,
) -> dict[str, str | bool | int] | None:
    """Builds the nullable JSON representation of a replacement summary."""
    if summary is None:
        return None

    return asdict(summary)
