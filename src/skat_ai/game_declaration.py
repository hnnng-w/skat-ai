from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from skat_ai.matador_inference import (
    infer_matadors_from_concrete_declarer_known_ownership,
    infer_matadors_from_declarer_cards,
)

VALID_DECLARATION_GAME_TYPES = [
    "clubs",
    "spades",
    "hearts",
    "diamonds",
    "grand",
    "null",
]

SUIT_GAME_BASE_VALUES = {
    "clubs": 12,
    "spades": 11,
    "hearts": 10,
    "diamonds": 9,
    "grand": 24,
}
BOOLEAN_DECLARATION_FIELDS = [
    "hand_game",
    "ouvert",
    "schneider_announced",
    "schwarz_announced",
]


@dataclass(frozen=True)
class GameDeclaration:
    """
    Describes the declared game and scoring modifiers.

    This is prepared for full Skat game-value scoring.
    It does not replace GameState.game_type yet.
    """
    game_type: str
    hand_game: bool = False
    ouvert: bool = False
    schneider_announced: bool = False
    schwarz_announced: bool = False
    matadors: int | None = None
    bid_value: int | None = None


def validate_declaration_game_type(game_type: str) -> None:
    """
    Validates a declared game type.
    """
    if game_type not in VALID_DECLARATION_GAME_TYPES:
        raise ValueError(f"Invalid declaration game type: {game_type}")


def validate_matadors(matadors: int | None) -> None:
    """
    Validates optional matador count.
    """
    if matadors is None:
        return

    if isinstance(matadors, bool) or not isinstance(matadors, int) or matadors < 0:
        raise ValueError("matadors must be a non-negative integer or null.")


def validate_declaration_boolean(value: Any, field_name: str) -> None:
    """Validates one declaration boolean field."""
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be a boolean.")


def validate_bid_value(bid_value: int | None) -> None:
    """Validates optional bid value."""
    if bid_value is None:
        return

    if isinstance(bid_value, bool) or not isinstance(bid_value, int) or bid_value <= 0:
        raise ValueError("bid_value must be a positive integer when provided.")


def validate_game_declaration(declaration: GameDeclaration) -> None:
    """
    Validates a game declaration.
    """
    validate_declaration_game_type(declaration.game_type)
    for field_name in BOOLEAN_DECLARATION_FIELDS:
        validate_declaration_boolean(
            getattr(declaration, field_name),
            field_name,
        )
    validate_matadors(declaration.matadors)
    validate_bid_value(declaration.bid_value)

    if declaration.game_type == "null":
        if declaration.schneider_announced:
            raise ValueError("Null games cannot have schneider announced.")

        if declaration.schwarz_announced:
            raise ValueError("Null games cannot have schwarz announced.")

        if declaration.matadors is not None:
            raise ValueError("Null games cannot have matadors.")


def infer_missing_matadors_from_input(data: dict[str, Any]) -> int | None:
    """Infers missing matadors from deterministic declarer ownership facts."""
    player_role = data.get("player_role", "unknown")

    hand = data.get("hand", [])
    skat = data.get("skat", [])

    if not isinstance(hand, list):
        hand = []

    if not isinstance(skat, list):
        skat = []

    declarer_cards = [*hand, *skat] if player_role == "declarer" else []
    completed_tricks = data.get("completed_tricks", [])

    if not isinstance(completed_tricks, list):
        completed_tricks = []

    inferred_from_ownership = infer_matadors_from_concrete_declarer_known_ownership(
        game_type=data["game_type"],
        declarer_player=data.get("declarer_player"),
        declarer_cards=declarer_cards,
        completed_tricks=completed_tricks,
    )

    if inferred_from_ownership is not None:
        return inferred_from_ownership

    if player_role != "declarer":
        return None

    return infer_matadors_from_declarer_cards(
        game_type=data["game_type"],
        declarer_cards=declarer_cards,
    )


def get_nested_game_declaration_data(
    data: dict[str, Any],
) -> Mapping[str, Any]:
    """Returns optional nested declaration metadata after type validation."""
    game_declaration_data = data.get("game_declaration")

    if game_declaration_data is None:
        return {}

    if not isinstance(game_declaration_data, Mapping):
        raise ValueError("game_declaration must be an object.")

    return game_declaration_data


def resolve_boolean_declaration_value(
    data: dict[str, Any],
    nested_data: Mapping[str, Any],
    field_name: str,
) -> bool:
    """Resolves one declaration boolean with top-level-over-nested precedence."""
    if field_name in data:
        value = data[field_name]
        validate_declaration_boolean(value, field_name)
        return value

    if field_name in nested_data:
        value = nested_data[field_name]
        validate_declaration_boolean(value, f"game_declaration.{field_name}")
        return value

    return False


def resolve_nullable_declaration_value(
    data: dict[str, Any],
    nested_data: Mapping[str, Any],
    field_name: str,
) -> Any:
    """Resolves a nullable numeric declaration field without truthiness checks."""
    if field_name in data and data[field_name] is not None:
        return data[field_name]

    if field_name in nested_data and nested_data[field_name] is not None:
        return nested_data[field_name]

    return None


def resolve_effective_declaration_values(
    data: dict[str, Any],
) -> dict[str, Any]:
    """Resolves effective declaration inputs from top-level and nested fields."""
    nested_data = get_nested_game_declaration_data(data)
    matadors = resolve_nullable_declaration_value(
        data=data,
        nested_data=nested_data,
        field_name="matadors",
    )

    if matadors is None:
        matadors = infer_missing_matadors_from_input(data)

    return {
        "game_type": data["game_type"],
        "hand_game": resolve_boolean_declaration_value(
            data=data,
            nested_data=nested_data,
            field_name="hand_game",
        ),
        "ouvert": resolve_boolean_declaration_value(
            data=data,
            nested_data=nested_data,
            field_name="ouvert",
        ),
        "schneider_announced": resolve_boolean_declaration_value(
            data=data,
            nested_data=nested_data,
            field_name="schneider_announced",
        ),
        "schwarz_announced": resolve_boolean_declaration_value(
            data=data,
            nested_data=nested_data,
            field_name="schwarz_announced",
        ),
        "matadors": matadors,
        "bid_value": resolve_nullable_declaration_value(
            data=data,
            nested_data=nested_data,
            field_name="bid_value",
        ),
    }


def build_game_declaration_from_input(
    data: dict[str, Any],
) -> GameDeclaration:
    """
    Builds and validates a game declaration from input data.
    """
    declaration = GameDeclaration(**resolve_effective_declaration_values(data))

    validate_game_declaration(declaration)

    return declaration


def build_serializable_game_declaration(
    declaration: GameDeclaration,
) -> dict[str, str | bool | int | None]:
    """
    Builds a JSON-serializable game declaration.
    """
    return {
        "game_type": declaration.game_type,
        "hand_game": declaration.hand_game,
        "ouvert": declaration.ouvert,
        "schneider_announced": declaration.schneider_announced,
        "schwarz_announced": declaration.schwarz_announced,
        "matadors": declaration.matadors,
        "bid_value": declaration.bid_value,
    }


def get_base_game_value(
    game_type: str,
) -> int:
    """
    Returns the base game value for non-null games.
    """
    validate_declaration_game_type(game_type)

    if game_type == "null":
        raise ValueError("Null games do not use suit/grand base values.")

    return SUIT_GAME_BASE_VALUES[game_type]
