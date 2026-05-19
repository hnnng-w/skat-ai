from typing import Any

from skat_ai.game_declaration import (
    GameDeclaration,
    get_base_game_value,
)

NULL_GAME_VALUES = {
    (False, False): 23,
    (True, False): 35,
    (False, True): 46,
    (True, True): 59,
}


def is_null_game(
    declaration: GameDeclaration,
) -> bool:
    """
    Returns whether the declaration is a null game.
    """
    return declaration.game_type == "null"


def get_null_game_value(
    declaration: GameDeclaration,
) -> int:
    """
    Returns the fixed value for a null game variant.
    """
    if not is_null_game(declaration):
        raise ValueError("Only null games use null game values.")

    return NULL_GAME_VALUES[(declaration.hand_game, declaration.ouvert)]


def get_matador_multiplier(
    declaration: GameDeclaration,
) -> int | None:
    """
    Returns the multiplier contribution from matadors.

    If matadors are unknown, no reliable multiplier can be calculated.
    """
    if declaration.matadors is None:
        return None

    return declaration.matadors + 1


def get_modifier_multiplier(
    declaration: GameDeclaration,
) -> int:
    """
    Returns the multiplier contribution from scoring modifiers.
    """
    multiplier = 0

    if declaration.hand_game:
        multiplier += 1

    if declaration.schneider_announced:
        multiplier += 1

    if declaration.schwarz_announced:
        multiplier += 1

    if declaration.ouvert:
        multiplier += 1

    return multiplier


def calculate_suit_or_grand_game_level(
    declaration: GameDeclaration,
) -> int:
    """
    Calculates the game level for suit and grand games.

    Current model:
    - matadors contribute matadors + 1
    - hand, schneider announced, schwarz announced, ouvert each add 1
    """
    if is_null_game(declaration):
        raise ValueError("Null games do not use suit/grand game levels.")

    matador_multiplier = get_matador_multiplier(declaration)

    if matador_multiplier is None:
        raise ValueError("Cannot calculate game level without matadors.")

    return matador_multiplier + get_modifier_multiplier(declaration)

def calculate_game_value(
    declaration: GameDeclaration,
) -> int:
    """
    Calculates the declared game value.

    Null games use fixed values.
    Suit and grand games use base value * game level.
    """
    if is_null_game(declaration):
        return get_null_game_value(declaration)

    base_value = get_base_game_value(declaration.game_type)
    game_level = calculate_suit_or_grand_game_level(declaration)

    return base_value * game_level


def build_game_value_summary(
    declaration: GameDeclaration,
) -> dict[str, Any]:
    """
    Builds a JSON-serializable game value summary.
    """
    if is_null_game(declaration):
        return {
            "game_type": declaration.game_type,
            "is_null_game": True,
            "base_value": None,
            "game_level": None,
            "game_value": calculate_game_value(declaration),
            "details": {
                "hand_game": declaration.hand_game,
                "ouvert": declaration.ouvert,
            },
        }

    base_value = get_base_game_value(declaration.game_type)
    matador_multiplier = get_matador_multiplier(declaration)
    modifier_multiplier = get_modifier_multiplier(declaration)

    if matador_multiplier is None:
        game_level = None
        game_value = None
        is_complete = False
    else:
        game_level = matador_multiplier + modifier_multiplier
        game_value = base_value * game_level
        is_complete = True

    return {
        "game_type": declaration.game_type,
        "is_null_game": False,
        "base_value": base_value,
        "game_level": game_level,
        "game_value": game_value,
        "details": {
            "matadors": declaration.matadors,
            "matador_multiplier": matador_multiplier,
            "hand_game": declaration.hand_game,
            "schneider_announced": declaration.schneider_announced,
            "schwarz_announced": declaration.schwarz_announced,
            "ouvert": declaration.ouvert,
            "modifier_multiplier": modifier_multiplier,
            "is_complete": is_complete,
        },
    }