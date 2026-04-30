from dataclasses import dataclass, field
from typing import Any


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