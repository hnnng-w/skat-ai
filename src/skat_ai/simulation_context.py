from dataclasses import dataclass, field
from typing import Any

from skat_ai.game_state import GameState


@dataclass
class SimulationContext:
    """
    Stores information collected during one simulation run.

    This is a first step toward more consistent multi-step simulations.
    """
    simulated_opponent_cards: list[str] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)


def add_simulated_opponent_card(
    context: SimulationContext,
    card: str,
) -> SimulationContext:
    """
    Returns a new context with one simulated opponent card added.
    """
    updated_cards = context.simulated_opponent_cards.copy()
    updated_cards.append(card)

    return SimulationContext(
        simulated_opponent_cards=updated_cards,
        events=context.events.copy(),
    )


def add_simulated_opponent_cards(
    context: SimulationContext,
    cards: list[str],
) -> SimulationContext:
    """
    Returns a new context with multiple simulated opponent cards added.
    """
    updated_context = context

    for card in cards:
        updated_context = add_simulated_opponent_card(
            context=updated_context,
            card=card,
        )

    return updated_context


def add_simulation_event(
    context: SimulationContext,
    event: dict[str, Any],
) -> SimulationContext:
    """
    Returns a new context with one simulation event added.
    """
    updated_events = context.events.copy()
    updated_events.append(event.copy())

    return SimulationContext(
        simulated_opponent_cards=context.simulated_opponent_cards.copy(),
        events=updated_events,
    )


def get_unique_simulated_opponent_cards(
    context: SimulationContext,
) -> list[str]:
    """
    Returns unique simulated opponent cards while preserving order.
    """
    unique_cards = []

    for card in context.simulated_opponent_cards:
        if card not in unique_cards:
            unique_cards.append(card)

    return unique_cards


def get_duplicate_simulated_opponent_cards(
    context: SimulationContext,
) -> list[str]:
    """
    Returns simulated opponent cards that appear more than once.
    """
    duplicates = []

    for card in context.simulated_opponent_cards:
        if context.simulated_opponent_cards.count(card) > 1 and card not in duplicates:
            duplicates.append(card)

    return duplicates


def build_context_summary(
    context: SimulationContext,
) -> dict[str, Any]:
    """
    Builds a summary of the simulation context.
    """
    unique_cards = get_unique_simulated_opponent_cards(context)
    duplicates = get_duplicate_simulated_opponent_cards(context)

    return {
        "simulated_opponent_card_count": len(context.simulated_opponent_cards),
        "unique_simulated_opponent_card_count": len(unique_cards),
        "duplicate_simulated_opponent_cards": duplicates,
        "event_count": len(context.events),
    }

def apply_context_to_state_for_sampling(
    state: GameState,
    context: SimulationContext,
) -> GameState:
    """
    Returns a copy of the state where simulated opponent cards are treated
    as already played cards for future sampling.

    This prevents future opponent-hand sampling from drawing the same
    simulated opponent cards again.
    """
    known_simulated_cards = get_unique_simulated_opponent_cards(context)

    updated_played_cards = state.played_cards.copy()

    for card in known_simulated_cards:
        if (
            card not in updated_played_cards
            and card not in state.hand
            and card not in state.current_trick
            and card not in state.skat
        ):
            updated_played_cards.append(card)

    return GameState(
        game_type=state.game_type,
        player_role=state.player_role,
        hand=state.hand.copy(),
        current_trick=state.current_trick.copy(),
        played_cards=updated_played_cards,
        skat=state.skat.copy(),
        player_position=state.player_position,
        trick_leader=state.trick_leader,
        completed_tricks=[completed_trick.copy() for completed_trick in state.completed_tricks],
        declarer_points=state.declarer_points,
        defender_points=state.defender_points,
        next_player=state.next_player,
    )

def validate_no_duplicate_simulated_opponent_cards(
    context: SimulationContext,
) -> None:
    """
    Raises a ValueError if duplicate simulated opponent cards exist.
    """
    duplicates = get_duplicate_simulated_opponent_cards(context)

    if duplicates:
        raise ValueError(
            "Duplicate simulated opponent cards detected: "
            f"{duplicates}"
        )