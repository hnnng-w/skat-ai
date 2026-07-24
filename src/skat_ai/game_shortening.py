from typing import Any

from skat_ai.declarer_card_exposure import (
    DeclarerCardExposure,
    build_declarer_card_exposure,
)
from skat_ai.declarer_concession import DeclarerConcession, build_declarer_concession
from skat_ai.defender_concession import DefenderConcession, build_defender_concession

type GameShortening = DeclarerConcession | DefenderConcession | DeclarerCardExposure


def build_game_shortening(value: Any) -> GameShortening:
    """Builds one supported version-1 structured game-shortening object."""
    if not isinstance(value, dict):
        raise ValueError("game_shortening must be an object.")

    kind = value.get("kind")
    if kind == "declarer_concession":
        return build_declarer_concession(value)
    if kind == "defender_concession":
        return build_defender_concession(value)
    if kind == "declarer_card_exposure":
        return build_declarer_card_exposure(value)

    raise ValueError(
        "game_shortening.kind must be 'declarer_concession', "
        "'defender_concession', or 'declarer_card_exposure' for schema_version 1."
    )


def get_game_shortening_from_input(
    data: dict[str, Any],
) -> GameShortening | None:
    """Returns the optional supported structured game shortening."""
    if "game_shortening" not in data:
        return None

    return build_game_shortening(data["game_shortening"])
