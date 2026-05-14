from dataclasses import dataclass, field
from typing import Any

from skat_ai.game_state import GameState
from skat_ai.known_cards import (
    get_duplicate_cards,
    get_known_cards_from_state,
    get_unique_cards_preserving_order,
    validate_no_duplicate_known_cards,
)


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
    return get_unique_cards_preserving_order(context.simulated_opponent_cards)


def get_duplicate_simulated_opponent_cards(
    context: SimulationContext,
) -> list[str]:
    """
    Returns simulated opponent cards that appear more than once.
    """
    return get_duplicate_cards(context.simulated_opponent_cards)


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

def get_context_cards_safe_to_add_to_played_cards(
    state: GameState,
    context: SimulationContext,
) -> list[str]:
    """
    Returns simulated opponent cards that can safely be added to played_cards.

    Cards already known in the state are skipped.
    """
    known_cards = get_known_cards_from_state(state)
    safe_cards = []

    for card in get_unique_simulated_opponent_cards(context):
        if card not in known_cards and card not in safe_cards:
            safe_cards.append(card)

    return safe_cards

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
    validate_no_duplicate_known_cards(state)

    safe_context_cards = get_context_cards_safe_to_add_to_played_cards(
        state=state,
        context=context,
    )

    updated_played_cards = [
        *state.played_cards,
        *safe_context_cards,
    ]

    updated_state = GameState(
        game_type=state.game_type,
        player_role=state.player_role,
        hand=state.hand.copy(),
        current_trick=state.current_trick.copy(),
        played_cards=updated_played_cards,
        skat=state.skat.copy(),
        player_position=state.player_position,
        trick_leader=state.trick_leader,
        completed_tricks=[
            completed_trick.copy() 
            for completed_trick in state.completed_tricks
        ],
        declarer_points=state.declarer_points,
        defender_points=state.defender_points,
        next_player=state.next_player,
    )

    validate_no_duplicate_known_cards(updated_state)

    return updated_state

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