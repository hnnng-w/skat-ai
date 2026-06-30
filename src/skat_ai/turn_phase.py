from dataclasses import dataclass
from typing import Any

CONCRETE_PLAYERS = ["me", "left", "right"]
UNKNOWN_PLAYER = "unknown"
VALID_TURN_PLAYERS = [*CONCRETE_PLAYERS, UNKNOWN_PLAYER]
VALID_CURRENT_TRICK_LENGTHS = [0, 1, 2]


@dataclass(frozen=True)
class TurnPhase:
    trick_leader: str
    next_player: str


def is_concrete_player(player: str | None) -> bool:
    """Returns whether the player is one of the fixed table seats."""
    return player in CONCRETE_PLAYERS


def validate_current_trick_length(current_trick_length: int) -> None:
    """Validates a supported in-progress trick length."""
    if current_trick_length not in VALID_CURRENT_TRICK_LENGTHS:
        raise ValueError("current_trick length must be 0, 1, or 2.")


def normalize_turn_player(player: str | None, field_name: str) -> str:
    """Normalizes a missing turn player to unknown and validates known values."""
    if player is None:
        return UNKNOWN_PLAYER

    if player not in VALID_TURN_PLAYERS:
        raise ValueError(f"Invalid {field_name}: {player}")

    return player


def derive_next_player(trick_leader: str, current_trick_length: int) -> str:
    """Derives the canonical next player from a concrete trick leader."""
    validate_current_trick_length(current_trick_length)

    if trick_leader not in CONCRETE_PLAYERS:
        raise ValueError(f"Cannot derive next_player from trick_leader: {trick_leader}")

    leader_index = CONCRETE_PLAYERS.index(trick_leader)
    next_index = (leader_index + current_trick_length) % len(CONCRETE_PLAYERS)

    return CONCRETE_PLAYERS[next_index]


def derive_trick_leader(next_player: str, current_trick_length: int) -> str:
    """Derives the canonical trick leader from a concrete next player."""
    validate_current_trick_length(current_trick_length)

    if next_player not in CONCRETE_PLAYERS:
        raise ValueError(f"Cannot derive trick_leader from next_player: {next_player}")

    next_index = CONCRETE_PLAYERS.index(next_player)
    leader_index = (next_index - current_trick_length) % len(CONCRETE_PLAYERS)

    return CONCRETE_PLAYERS[leader_index]


def get_last_concrete_completed_trick_winner(
    completed_tricks: list[dict[str, Any]] | None,
) -> str | None:
    """Returns the last concrete winner_player, without side-level inference."""
    if not completed_tricks:
        return None

    winner_player = completed_tricks[-1].get("winner_player")

    if is_concrete_player(winner_player):
        return winner_player

    return None


def normalize_turn_phase(
    trick_leader: str | None,
    next_player: str | None,
    current_trick_length: int,
    required_trick_leader: str | None = None,
) -> TurnPhase:
    """Normalizes and validates one fixed-table turn phase.

    Missing or unknown counterpart fields are derived only when exactly one
    concrete value determines the canonical phase.
    """
    validate_current_trick_length(current_trick_length)

    normalized_leader = normalize_turn_player(trick_leader, "trick_leader")
    normalized_next = normalize_turn_player(next_player, "next_player")
    normalized_required_leader = normalize_turn_player(
        required_trick_leader,
        "required_trick_leader",
    )

    if is_concrete_player(normalized_required_leader):
        if (
            is_concrete_player(normalized_leader)
            and normalized_leader != normalized_required_leader
        ):
            raise ValueError(
                "trick_leader is inconsistent with completed_tricks: "
                f"expected {normalized_required_leader}, got {normalized_leader}."
            )

        normalized_leader = normalized_required_leader

    has_concrete_leader = is_concrete_player(normalized_leader)
    has_concrete_next = is_concrete_player(normalized_next)

    if not has_concrete_leader and not has_concrete_next:
        if current_trick_length > 0:
            raise ValueError(
                "Cannot determine turn phase for non-empty current_trick without "
                "trick_leader or next_player."
            )

        return TurnPhase(
            trick_leader=UNKNOWN_PLAYER,
            next_player=UNKNOWN_PLAYER,
        )

    if has_concrete_leader and not has_concrete_next:
        normalized_next = derive_next_player(
            trick_leader=normalized_leader,
            current_trick_length=current_trick_length,
        )
    elif has_concrete_next and not has_concrete_leader:
        normalized_leader = derive_trick_leader(
            next_player=normalized_next,
            current_trick_length=current_trick_length,
        )
    else:
        expected_next = derive_next_player(
            trick_leader=normalized_leader,
            current_trick_length=current_trick_length,
        )

        if normalized_next != expected_next:
            raise ValueError(
                "turn phase is inconsistent: "
                f"trick_leader={normalized_leader!r} with "
                f"current_trick length {current_trick_length} requires "
                f"next_player={expected_next!r}, got {normalized_next!r}."
            )

    return TurnPhase(
        trick_leader=normalized_leader,
        next_player=normalized_next,
    )


def normalize_turn_phase_for_position(
    trick_leader: str | None,
    next_player: str | None,
    current_trick: list[str],
    completed_tricks: list[dict[str, Any]] | None = None,
) -> TurnPhase:
    """Normalizes turn phase fields for an input position."""
    return normalize_turn_phase(
        trick_leader=trick_leader,
        next_player=next_player,
        current_trick_length=len(current_trick),
        required_trick_leader=get_last_concrete_completed_trick_winner(
            completed_tricks
        ),
    )


def validate_turn_phase(
    trick_leader: str | None,
    next_player: str | None,
    current_trick_length: int,
    required_trick_leader: str | None = None,
) -> None:
    """Validates one fixed-table turn phase."""
    normalize_turn_phase(
        trick_leader=trick_leader,
        next_player=next_player,
        current_trick_length=current_trick_length,
        required_trick_leader=required_trick_leader,
    )
