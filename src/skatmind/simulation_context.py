from dataclasses import dataclass, field
from typing import Any

from skatmind.coherent_hidden_world import (
    CoherentHiddenWorld,
    build_hidden_world_summary,
    reconcile_hidden_world_with_state,
)
from skatmind.game_state import GameState
from skatmind.known_cards import (
    get_duplicate_cards,
    get_known_cards_from_state,
    get_unique_cards_preserving_order,
    validate_no_duplicate_known_cards,
)
from skatmind.public_hand_constraint import (
    PublicHandConstraint,
    build_serializable_public_hand_constraints,
)
from skatmind.strategic_metadata import (
    StrategicMetadata,
    build_default_strategic_metadata,
)


@dataclass
class SimulationContext:
    """
    Stores information collected during one simulation run.

    This is a first step toward more consistent multi-step simulations.
    """
    simulated_opponent_cards: list[str] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    strategic_metadata: StrategicMetadata = field(
        default_factory=build_default_strategic_metadata
    )
    public_hand_constraints: tuple[PublicHandConstraint, ...] = ()
    hidden_world: CoherentHiddenWorld | None = field(default=None, repr=False)
    root_hidden_world: CoherentHiddenWorld | None = field(default=None, repr=False)
    simulated_opponent_card_ownership: list[tuple[str, str]] = field(
        default_factory=list,
        repr=False,
    )


def _copy_context(
    context: SimulationContext,
    *,
    simulated_opponent_cards: list[str] | None = None,
    events: list[dict[str, Any]] | None = None,
    public_hand_constraints: tuple[PublicHandConstraint, ...] | None = None,
    hidden_world: CoherentHiddenWorld | None = None,
    replace_hidden_world: bool = False,
    simulated_opponent_card_ownership: list[tuple[str, str]] | None = None,
) -> SimulationContext:
    return SimulationContext(
        simulated_opponent_cards=(
            context.simulated_opponent_cards.copy()
            if simulated_opponent_cards is None
            else simulated_opponent_cards
        ),
        events=context.events.copy() if events is None else events,
        strategic_metadata=context.strategic_metadata,
        public_hand_constraints=(
            context.public_hand_constraints
            if public_hand_constraints is None
            else public_hand_constraints
        ),
        hidden_world=(
            hidden_world if replace_hidden_world else context.hidden_world
        ),
        root_hidden_world=context.root_hidden_world,
        simulated_opponent_card_ownership=(
            context.simulated_opponent_card_ownership.copy()
            if simulated_opponent_card_ownership is None
            else simulated_opponent_card_ownership
        ),
    )


def add_simulated_opponent_card(
    context: SimulationContext,
    card: str,
) -> SimulationContext:
    """
    Returns a new context with one simulated opponent card added.
    """
    updated_cards = context.simulated_opponent_cards.copy()
    updated_cards.append(card)

    return _copy_context(
        context,
        simulated_opponent_cards=updated_cards,
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


def add_simulated_opponent_plays(
    context: SimulationContext,
    plays: tuple[tuple[str, str], ...],
) -> SimulationContext:
    """Records ordered opponent plays with stable ownership evidence."""
    cards = [card for _, card in plays]
    ownership = [*context.simulated_opponent_card_ownership, *plays]
    return _copy_context(
        context,
        simulated_opponent_cards=[*context.simulated_opponent_cards, *cards],
        simulated_opponent_card_ownership=ownership,
    )


def add_simulation_event(
    context: SimulationContext,
    event: dict[str, Any],
) -> SimulationContext:
    """
    Returns a new context with one simulation event added.
    """
    updated_events = context.events.copy()
    updated_events.append(event.copy())

    return _copy_context(
        context,
        events=updated_events,
    )


def update_public_hand_constraints(
    context: SimulationContext,
    constraints: tuple[PublicHandConstraint, ...],
) -> SimulationContext:
    """Returns a context with the current public hands replaced."""
    return _copy_context(
        context,
        public_hand_constraints=constraints,
    )


def update_hidden_world(
    context: SimulationContext,
    hidden_world: CoherentHiddenWorld,
) -> SimulationContext:
    """Returns a context with the current private execution world replaced."""
    return _copy_context(
        context,
        hidden_world=hidden_world,
        replace_hidden_world=True,
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

    summary = {
        "simulated_opponent_card_count": len(context.simulated_opponent_cards),
        "unique_simulated_opponent_card_count": len(unique_cards),
        "duplicate_simulated_opponent_cards": duplicates,
        "event_count": len(context.events),
        "strategic_metadata": {
            "analysis_mode": context.strategic_metadata.analysis_mode,
            "skat_visibility": context.strategic_metadata.skat_visibility,
            "game_end_reason": context.strategic_metadata.game_end_reason,
        },
    }
    if context.public_hand_constraints:
        summary["public_hand_constraints"] = build_serializable_public_hand_constraints(
            context.public_hand_constraints
        )
    if context.hidden_world is not None:
        summary["hidden_world"] = build_hidden_world_summary(context.hidden_world)
    return summary

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
        declarer_player=state.declarer_player,
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


def validate_simulation_context(
    context: SimulationContext,
    state: GameState,
    *,
    step_index: int,
) -> None:
    """Strictly reconciles path evidence, public state, and private ownership."""
    validate_no_duplicate_simulated_opponent_cards(context)
    if context.hidden_world is None:
        raise ValueError(
            f"Hidden-world ownership invariant violated at step {step_index}: "
            "coherent path world is missing."
        )
    if context.root_hidden_world is None:
        raise ValueError(
            f"Hidden-world ownership invariant violated at step {step_index}: "
            "root path world is missing."
        )
    if context.root_hidden_world.ownership_transitions:
        raise ValueError(
            f"Hidden-world ownership invariant violated at step {step_index}: "
            "root path world already contains transitions."
        )
    if context.hidden_world.provenance != context.root_hidden_world.provenance:
        raise ValueError(
            f"Hidden-world ownership invariant violated at step {step_index}: "
            "current world does not retain the sampled root ownership."
        )
    evidence_cards = [
        card for _, card in context.simulated_opponent_card_ownership
    ]
    if evidence_cards != context.simulated_opponent_cards:
        raise ValueError(
            f"Hidden-world ownership invariant violated at step {step_index}: "
            "owner-aware play evidence does not match simulated opponent cards."
        )
    if tuple(context.simulated_opponent_card_ownership) != (
        context.hidden_world.ownership_transitions
    ):
        raise ValueError(
            f"Hidden-world ownership invariant violated at step {step_index}: "
            "world transitions do not match path ownership evidence."
        )
    reconcile_hidden_world_with_state(
        context.hidden_world,
        state,
        context.public_hand_constraints,
        step_index=step_index,
    )
