from dataclasses import dataclass

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
    hand: bool = False
    ouvert: bool = False
    schneider_announced: bool = False
    schwarz_announced: bool = False
    matadors: int | None = None


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

    if declaration.game_type == "null":
        if declaration.schneider_announced:
            raise ValueError("Null games cannot have schneider announced.")

        if declaration.schwarz_announced:
            raise ValueError("Null games cannot have schwarz announced.")

        if declaration.matadors is not None:
            raise ValueError("Null games cannot have matadors.")


def build_game_declaration_from_input(
    data: dict,
) -> GameDeclaration:
    """
    Builds a game declaration from input data.

    Defaults to the existing game_type field.
    """
    declaration = GameDeclaration(
        game_type=data["game_type"],
        hand=data.get("hand_game", False),
        ouvert=data.get("ouvert", False),
        schneider_announced=data.get("schneider_announced", False),
        schwarz_announced=data.get("schwarz_announced", False),
        matadors=data.get("matadors"),
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
        "hand_game": declaration.hand,
        "ouvert": declaration.ouvert,
        "schneider_announced": declaration.schneider_announced,
        "schwarz_announced": declaration.schwarz_announced,
        "matadors": declaration.matadors,
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