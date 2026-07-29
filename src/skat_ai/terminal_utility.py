from dataclasses import dataclass

from skat_ai.rules import GAME_TYPES
from skat_ai.side_ownership import VALID_PLAYER_SIDES

TERMINAL_UTILITY_VERSION = 1


@dataclass(frozen=True)
class TerminalUtility:
    """Versioned terminal utility oriented toward the local side."""

    version: int
    game_type: str
    local_contract_success: bool
    local_side_game_score: int
    local_side_card_point_margin: int | None

    def __post_init__(self) -> None:
        if self.version != TERMINAL_UTILITY_VERSION:
            raise ValueError("Unsupported terminal utility version.")
        if self.game_type not in GAME_TYPES:
            raise ValueError(f"Invalid terminal utility game type: {self.game_type}")
        if not isinstance(self.local_contract_success, bool):
            raise ValueError("local_contract_success must be a boolean.")
        if isinstance(self.local_side_game_score, bool) or not isinstance(
            self.local_side_game_score, int
        ):
            raise ValueError("local_side_game_score must be an integer.")
        if self.game_type == "null":
            if self.local_side_card_point_margin is not None:
                raise ValueError("Null terminal utility has no card-point margin.")
        elif isinstance(self.local_side_card_point_margin, bool) or not isinstance(
            self.local_side_card_point_margin, int
        ):
            raise ValueError(
                "Suit and Grand terminal utility requires a card-point margin."
            )


def build_terminal_utility(
    *,
    game_type: str,
    local_side: str,
    winner: str,
    declarer_settlement_score: int,
    declarer_points: int,
    defender_points: int,
) -> TerminalUtility:
    """Orients existing terminal result and settlement values to the local side."""
    if local_side not in VALID_PLAYER_SIDES:
        raise ValueError(f"Invalid local side: {local_side}")
    if winner not in VALID_PLAYER_SIDES:
        raise ValueError(f"Invalid terminal winner: {winner}")
    if isinstance(declarer_settlement_score, bool) or not isinstance(
        declarer_settlement_score, int
    ):
        raise ValueError("declarer_settlement_score must be an integer.")
    for field_name, value in (
        ("declarer_points", declarer_points),
        ("defender_points", defender_points),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{field_name} must be a non-negative integer.")

    orientation = 1 if local_side == "declarer" else -1
    return TerminalUtility(
        version=TERMINAL_UTILITY_VERSION,
        game_type=game_type,
        local_contract_success=winner == local_side,
        local_side_game_score=orientation * declarer_settlement_score,
        local_side_card_point_margin=(
            None
            if game_type == "null"
            else orientation * (declarer_points - defender_points)
        ),
    )


def terminal_utility_comparison_key(
    utility: TerminalUtility,
) -> tuple[bool, int] | tuple[bool, int, int]:
    """Returns the version-1 lexicographic terminal comparison key."""
    if utility.game_type == "null":
        return utility.local_contract_success, utility.local_side_game_score
    margin = utility.local_side_card_point_margin
    if margin is None:  # Kept explicit for static type narrowing.
        raise ValueError("Suit and Grand terminal utility requires a margin.")
    return (
        utility.local_contract_success,
        utility.local_side_game_score,
        margin,
    )


def compare_terminal_utilities(
    left: TerminalUtility,
    right: TerminalUtility,
) -> int:
    """Returns -1, 0, or 1 using terminal utility version 1."""
    if left.game_type != right.game_type:
        raise ValueError("Terminal utilities must use the same game type.")
    left_key = terminal_utility_comparison_key(left)
    right_key = terminal_utility_comparison_key(right)
    return (left_key > right_key) - (left_key < right_key)
