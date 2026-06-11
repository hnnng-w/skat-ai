from dataclasses import dataclass
from typing import Any

from skat_ai.matador_inference import infer_matadors_from_declarer_cards

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

    if not isinstance(matadors, int) or matadors < 0:
        raise ValueError("matadors must be a non-negative integer or null.")


def validate_game_declaration(declaration: GameDeclaration) -> None:
    """
    Validates a game declaration.
    """
    validate_declaration_game_type(declaration.game_type)
    validate_matadors(declaration.matadors)

    if declaration.bid_value is not None:
        if not isinstance(declaration.bid_value, int) or declaration.bid_value <= 0:
            raise ValueError("bid_value must be a positive integer when provided.")

    if declaration.game_type == "null":
        if declaration.schneider_announced:
            raise ValueError("Null games cannot have schneider announced.")

        if declaration.schwarz_announced:
            raise ValueError("Null games cannot have schwarz announced.")

        if declaration.matadors is not None:
            raise ValueError("Null games cannot have matadors.")


def infer_missing_matadors_from_input(data: dict[str, Any]) -> int | None:
    """Infers missing matadors from currently known declarer cards."""
    game_declaration_data = data.get("game_declaration", {})

    if not isinstance(game_declaration_data, dict):
        game_declaration_data = {}

    if game_declaration_data.get("matadors") is not None:
        return game_declaration_data["matadors"]

    if data.get("matadors") is not None:
        return data["matadors"]

    hand = data.get("hand", [])
    skat = data.get("skat", [])

    if not isinstance(hand, list):
        hand = []

    if not isinstance(skat, list):
        skat = []

    declarer_cards = [*hand, *skat]

    return infer_matadors_from_declarer_cards(
        game_type=data["game_type"],
        declarer_cards=declarer_cards,
    )


def build_game_declaration_from_input(
    data: dict[str, Any],
) -> GameDeclaration:
    """
    Builds and validates a game declaration from input data.
    """
    declaration = GameDeclaration(
        game_type=data["game_type"],
        hand_game=data.get("hand_game", False),
        ouvert=data.get("ouvert", False),
        schneider_announced=data.get("schneider_announced", False),
        schwarz_announced=data.get("schwarz_announced", False),
        matadors=infer_missing_matadors_from_input(data),
        bid_value=data.get("bid_value"),
    )

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