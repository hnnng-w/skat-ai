from typing import Any

from skat_ai.declarer_card_exposure_continuation import (
    DeclarerCardExposureContinuation,
    DeclarerCardExposureContinuationContext,
    build_declarer_card_exposure_continuation,
    resolve_declarer_card_exposure_continuation,
)
from skat_ai.declarer_card_exposure_continuation import (
    build_game_continuation_summary as build_declarer_card_exposure_continuation_summary,
)
from skat_ai.defender_open_play_continuation import (
    DefenderOpenPlayContinuation,
    DefenderOpenPlayContinuationContext,
    build_defender_open_play_continuation,
    build_defender_open_play_continuation_summary,
    resolve_defender_open_play_continuation,
)

type GameContinuation = DeclarerCardExposureContinuation | DefenderOpenPlayContinuation
type GameContinuationContext = (
    DeclarerCardExposureContinuationContext | DefenderOpenPlayContinuationContext
)


def build_game_continuation(value: Any) -> GameContinuation:
    """Dispatches one strict version-1 ongoing continuation by kind."""
    if not isinstance(value, dict):
        raise ValueError("game_continuation must be an object.")
    kind = value.get("kind")
    if kind == "declarer_card_exposure":
        return build_declarer_card_exposure_continuation(value)
    if kind == "defender_open_play":
        return build_defender_open_play_continuation(value)
    raise ValueError(
        "Unsupported game_continuation.kind; expected 'declarer_card_exposure' "
        "or 'defender_open_play'."
    )


def get_game_continuation_from_input(
    data: dict[str, Any],
) -> GameContinuation | None:
    """Returns the optional versioned ongoing-continuation union."""
    if "game_continuation" not in data:
        return None
    return build_game_continuation(data["game_continuation"])


def resolve_game_continuation(
    position: dict[str, Any],
    continuation: GameContinuation,
) -> GameContinuationContext:
    """Resolves one supported continuation without adjudicating the game."""
    if isinstance(continuation, DefenderOpenPlayContinuation):
        return resolve_defender_open_play_continuation(position, continuation)
    return resolve_declarer_card_exposure_continuation(position, continuation)


def build_game_continuation_summary(
    context: GameContinuationContext,
) -> dict[str, Any]:
    """Builds the stable summary for one continuation union member."""
    if isinstance(context, DefenderOpenPlayContinuationContext):
        return build_defender_open_play_continuation_summary(context)
    return build_declarer_card_exposure_continuation_summary(context)
