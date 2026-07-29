import hashlib
import random
from dataclasses import dataclass, field, replace
from typing import Any

from skat_ai.deck import get_full_deck
from skat_ai.game_state import GameState
from skat_ai.hidden_card_inference import (
    HiddenCardInferenceConstraints,
    HiddenCardInferenceModel,
    build_hidden_card_inference_model,
    get_public_effective_category,
)
from skat_ai.known_cards import (
    get_known_cards_from_state,
    validate_no_duplicate_known_cards,
)
from skat_ai.public_hand_constraint import PublicHandConstraint
from skat_ai.simulation import generate_sampled_hidden_state

COHERENT_PATH_MODE = "coherent_path"
HIDDEN_WORLD_SOURCE = "sampled_hidden_state"
_OPPONENT_PLAYERS = ("left", "right")


@dataclass(frozen=True)
class HiddenWorldProvenance:
    """Private construction facts used to validate one path world."""

    source: str
    sampled_at_step: int
    initial_left_hand_size: int
    initial_right_hand_size: int
    initial_left_hand: tuple[str, ...] = field(repr=False)
    initial_right_hand: tuple[str, ...] = field(repr=False)
    initial_hypothetical_skat: tuple[str, ...] = field(repr=False)
    public_constraint_sources: tuple[str, ...] = ()
    root_sample_count: int = 1

    @property
    def initial_hypothetical_skat_size(self) -> int:
        return len(self.initial_hypothetical_skat)


@dataclass(frozen=True)
class CoherentHiddenWorld:
    """One immutable hidden-card ownership assignment for a simulated path."""

    left_hand: tuple[str, ...]
    right_hand: tuple[str, ...]
    hypothetical_skat: tuple[str, ...]
    provenance: HiddenWorldProvenance | None = None
    ownership_transitions: tuple[tuple[str, str], ...] = field(
        default=(), repr=False
    )

    def __post_init__(self) -> None:
        for location_name in ("left_hand", "right_hand", "hypothetical_skat"):
            if not isinstance(getattr(self, location_name), tuple):
                raise TypeError(f"{location_name} must be a tuple.")
        if not isinstance(self.ownership_transitions, tuple):
            raise TypeError("ownership_transitions must be a tuple.")

        if self.provenance is None:
            object.__setattr__(
                self,
                "provenance",
                HiddenWorldProvenance(
                    source=HIDDEN_WORLD_SOURCE,
                    sampled_at_step=0,
                    initial_left_hand_size=len(self.left_hand),
                    initial_right_hand_size=len(self.right_hand),
                    initial_left_hand=self.left_hand,
                    initial_right_hand=self.right_hand,
                    initial_hypothetical_skat=self.hypothetical_skat,
                ),
            )
        validate_coherent_hidden_world(self)


def _canonical_card_set(cards: tuple[str, ...] | list[str], context: str) -> set[str]:
    full_deck = set(get_full_deck())
    invalid_cards = sorted(set(cards) - full_deck)
    if invalid_cards:
        raise ValueError(f"Invalid canonical cards in {context}: {invalid_cards}")
    if len(cards) != len(set(cards)):
        raise ValueError(f"Duplicate cards in {context}.")
    return set(cards)


def _raise_invariant_error(step_index: int, detail: str) -> None:
    raise ValueError(
        f"Hidden-world ownership invariant violated at step {step_index}: {detail}"
    )


def _validate_public_constraints(
    world: CoherentHiddenWorld,
    state: GameState,
    public_hand_constraints: tuple[PublicHandConstraint, ...],
    step_index: int,
) -> None:
    constraints_by_player: dict[str, PublicHandConstraint] = {}
    constrained_cards: set[str] = set()
    for constraint in public_hand_constraints:
        if constraint.player not in {"me", *_OPPONENT_PLAYERS}:
            _raise_invariant_error(
                step_index,
                f"unsupported public constraint player {constraint.player!r}.",
            )
        if constraint.player in constraints_by_player:
            _raise_invariant_error(
                step_index,
                f"duplicate public constraint for {constraint.player}.",
            )
        cards = _canonical_card_set(
            constraint.cards, f"public {constraint.player} hand constraint"
        )
        duplicate_assignments = constrained_cards.intersection(cards)
        if duplicate_assignments:
            _raise_invariant_error(
                step_index,
                "public constraints assign cards more than once: "
                f"{sorted(duplicate_assignments)}.",
            )
        constraints_by_player[constraint.player] = constraint
        constrained_cards.update(cards)

    expected_hands = {
        "me": set(state.hand),
        "left": set(world.left_hand),
        "right": set(world.right_hand),
    }
    for player, constraint in constraints_by_player.items():
        if set(constraint.cards) != expected_hands[player]:
            _raise_invariant_error(
                step_index,
                f"public {player} hand constraint does not match current ownership.",
            )


def _validate_root_public_constraints(
    state: GameState,
    left_hand_size: int,
    right_hand_size: int,
    public_hand_constraints: tuple[PublicHandConstraint, ...],
) -> None:
    constraints_by_player: dict[str, PublicHandConstraint] = {}
    constrained_cards: set[str] = set()
    known_cards = set(get_known_cards_from_state(state))
    for constraint in public_hand_constraints:
        if constraint.player not in {"me", *_OPPONENT_PLAYERS}:
            raise ValueError(
                f"Unsupported public hand constraint player: {constraint.player}"
            )
        if constraint.player in constraints_by_player:
            raise ValueError(
                f"Duplicate public hand constraint for {constraint.player}."
            )
        cards = _canonical_card_set(
            constraint.cards, f"public {constraint.player} hand constraint"
        )
        duplicate_assignments = constrained_cards.intersection(cards)
        if duplicate_assignments:
            raise ValueError(
                "Public hand constraints assign cards more than once: "
                f"{sorted(duplicate_assignments)}"
            )
        constraints_by_player[constraint.player] = constraint
        constrained_cards.update(cards)

    local_constraint = constraints_by_player.get("me")
    if local_constraint is not None and set(local_constraint.cards) != set(state.hand):
        raise ValueError("The local public hand constraint must exactly match state.hand.")
    for player, expected_size in (
        ("left", left_hand_size),
        ("right", right_hand_size),
    ):
        constraint = constraints_by_player.get(player)
        if constraint is None:
            continue
        if len(constraint.cards) != expected_size:
            raise ValueError(
                f"The exact public {player} hand has {len(constraint.cards)} cards, "
                f"but the required hand size is {expected_size}."
            )
        unavailable = sorted(set(constraint.cards).intersection(known_cards))
        if unavailable:
            raise ValueError(
                f"Public {player} hand cards overlap the known state: {unavailable}"
            )


def validate_coherent_hidden_world(
    world: CoherentHiddenWorld,
    *,
    state: GameState | None = None,
    left_hand_size: int | None = None,
    right_hand_size: int | None = None,
    public_hand_constraints: tuple[PublicHandConstraint, ...] = (),
    hidden_card_inference_constraints: HiddenCardInferenceConstraints | None = None,
    step_index: int = 0,
) -> None:
    """Validates card accounting and optional current public-state agreement."""
    provenance = world.provenance
    if provenance is None:
        _raise_invariant_error(step_index, "world provenance is missing.")
    if provenance.root_sample_count != 1:
        _raise_invariant_error(
            step_index,
            f"root sample count is {provenance.root_sample_count}, expected 1.",
        )
    if provenance.sampled_at_step != 0:
        _raise_invariant_error(
            step_index,
            f"root world was sampled at step {provenance.sampled_at_step}, expected 0.",
        )

    initial_left_cards = _canonical_card_set(
        provenance.initial_left_hand,
        "initial left hand provenance",
    )
    initial_right_cards = _canonical_card_set(
        provenance.initial_right_hand,
        "initial right hand provenance",
    )
    initial_skat_cards = _canonical_card_set(
        provenance.initial_hypothetical_skat,
        "initial hypothetical skat provenance",
    )
    if len(initial_left_cards) != provenance.initial_left_hand_size:
        _raise_invariant_error(step_index, "initial left ownership size is inconsistent.")
    if len(initial_right_cards) != provenance.initial_right_hand_size:
        _raise_invariant_error(step_index, "initial right ownership size is inconsistent.")
    if initial_left_cards.intersection(initial_right_cards, initial_skat_cards) or (
        initial_right_cards.intersection(initial_skat_cards)
    ):
        _raise_invariant_error(
            step_index,
            "initial ownership assigns cards to multiple locations.",
        )

    current_locations = (
        ("left hand", world.left_hand),
        ("right hand", world.right_hand),
        ("hypothetical skat", world.hypothetical_skat),
    )
    all_current_cards: set[str] = set()
    for location_name, cards in current_locations:
        location_cards = _canonical_card_set(cards, location_name)
        duplicates = all_current_cards.intersection(location_cards)
        if duplicates:
            _raise_invariant_error(
                step_index,
                f"cards occur in multiple current locations: {sorted(duplicates)}.",
            )
        all_current_cards.update(location_cards)

    if world.hypothetical_skat != provenance.initial_hypothetical_skat:
        _raise_invariant_error(step_index, "fixed hypothetical skat changed.")

    transitioned_cards: set[str] = set()
    left_transition_count = 0
    right_transition_count = 0
    for transition in world.ownership_transitions:
        if not isinstance(transition, tuple) or len(transition) != 2:
            _raise_invariant_error(step_index, "invalid ownership transition record.")
        player, card = transition
        if player not in _OPPONENT_PLAYERS:
            _raise_invariant_error(
                step_index, f"transition has unsupported owner {player!r}."
            )
        _canonical_card_set((card,), "ownership transition")
        if card in transitioned_cards or card in all_current_cards:
            _raise_invariant_error(
                step_index, f"transitioned card {card} is duplicated or still owned."
            )
        transitioned_cards.add(card)
        if player == "left":
            left_transition_count += 1
        else:
            right_transition_count += 1

    if len(world.left_hand) + left_transition_count != provenance.initial_left_hand_size:
        _raise_invariant_error(step_index, "left hand size does not reconcile.")
    if len(world.right_hand) + right_transition_count != provenance.initial_right_hand_size:
        _raise_invariant_error(step_index, "right hand size does not reconcile.")
    transitioned_left_cards = {
        card for player, card in world.ownership_transitions if player == "left"
    }
    transitioned_right_cards = {
        card for player, card in world.ownership_transitions if player == "right"
    }
    expected_left_hand = tuple(
        card
        for card in provenance.initial_left_hand
        if card not in transitioned_left_cards
    )
    expected_right_hand = tuple(
        card
        for card in provenance.initial_right_hand
        if card not in transitioned_right_cards
    )
    if world.left_hand != expected_left_hand:
        _raise_invariant_error(step_index, "left root ownership was not preserved.")
    if world.right_hand != expected_right_hand:
        _raise_invariant_error(step_index, "right root ownership was not preserved.")
    if left_hand_size is not None and len(world.left_hand) != left_hand_size:
        _raise_invariant_error(
            step_index,
            f"left hand has {len(world.left_hand)} cards, expected {left_hand_size}.",
        )
    if right_hand_size is not None and len(world.right_hand) != right_hand_size:
        _raise_invariant_error(
            step_index,
            f"right hand has {len(world.right_hand)} cards, expected {right_hand_size}.",
        )

    if state is not None:
        validate_no_duplicate_known_cards(state)
        known_cards = get_known_cards_from_state(state)
        _canonical_card_set(known_cards, "known game state")
        overlap = all_current_cards.intersection(known_cards)
        if overlap:
            _raise_invariant_error(
                step_index,
                f"remaining hidden cards are already known: {sorted(overlap)}.",
            )
        _validate_public_constraints(
            world, state, public_hand_constraints, step_index
        )
        if hidden_card_inference_constraints is not None:
            for player in _OPPONENT_PLAYERS:
                player_constraints = hidden_card_inference_constraints.for_player(player)
                hand = world.left_hand if player == "left" else world.right_hand
                for card in hand:
                    category = get_public_effective_category(card, state.game_type)
                    if category in player_constraints.forbidden_effective_categories:
                        _raise_invariant_error(
                            step_index,
                            f"{player} is confirmed void in {category}, but owns card "
                            f"{card} under evidence source "
                            f"{hidden_card_inference_constraints.provenance_status}.",
                        )
        missing_transition_cards = transitioned_cards.difference(known_cards)
        if missing_transition_cards:
            _raise_invariant_error(
                step_index,
                "transitioned cards are absent from the known state: "
                f"{sorted(missing_transition_cards)}.",
            )
        missing_cards = set(get_full_deck()).difference(all_current_cards, known_cards)
        if missing_cards:
            _raise_invariant_error(
                step_index,
                f"state and hidden world do not account for cards: {sorted(missing_cards)}.",
            )
    elif public_hand_constraints or hidden_card_inference_constraints is not None:
        raise ValueError("state is required when validating public ownership constraints.")


def reconcile_hidden_world_with_state(
    world: CoherentHiddenWorld,
    state: GameState,
    public_hand_constraints: tuple[PublicHandConstraint, ...] = (),
    hidden_card_inference_constraints: HiddenCardInferenceConstraints | None = None,
    *,
    step_index: int = 0,
) -> None:
    """Validates a current world against known state and exact public hands."""
    validate_coherent_hidden_world(
        world,
        state=state,
        public_hand_constraints=public_hand_constraints,
        hidden_card_inference_constraints=hidden_card_inference_constraints,
        step_index=step_index,
    )


def build_coherent_hidden_world(
    state: GameState,
    left_hand_size: int,
    right_hand_size: int,
    random_generator: random.Random | None = None,
    public_hand_constraints: tuple[PublicHandConstraint, ...] = (),
    hidden_card_inference_model: HiddenCardInferenceModel | None = None,
) -> CoherentHiddenWorld:
    """Samples and validates exactly one immutable root path world."""
    if left_hand_size < 0 or right_hand_size < 0:
        raise ValueError("Hidden-world hand sizes must not be negative.")
    validate_no_duplicate_known_cards(state)
    _canonical_card_set(get_known_cards_from_state(state), "known game state")
    _validate_root_public_constraints(
        state,
        left_hand_size,
        right_hand_size,
        public_hand_constraints,
    )

    inference_model = hidden_card_inference_model or build_hidden_card_inference_model(
        state,
        left_hand_size,
        right_hand_size,
        public_hand_constraints,
    )
    sample = generate_sampled_hidden_state(
        state=state,
        left_hand_size=left_hand_size,
        right_hand_size=right_hand_size,
        random_generator=random_generator,
        public_hand_constraints=public_hand_constraints,
        hidden_card_inference_model=inference_model,
    )
    world = CoherentHiddenWorld(
        left_hand=tuple(sample.left_hand),
        right_hand=tuple(sample.right_hand),
        hypothetical_skat=tuple(sample.hypothetical_skat),
        provenance=HiddenWorldProvenance(
            source=HIDDEN_WORLD_SOURCE,
            sampled_at_step=0,
            initial_left_hand_size=left_hand_size,
            initial_right_hand_size=right_hand_size,
            initial_left_hand=tuple(sample.left_hand),
            initial_right_hand=tuple(sample.right_hand),
            initial_hypothetical_skat=tuple(sample.hypothetical_skat),
            public_constraint_sources=tuple(
                sorted({constraint.source for constraint in public_hand_constraints})
            ),
        ),
    )
    validate_coherent_hidden_world(
        world,
        state=state,
        left_hand_size=left_hand_size,
        right_hand_size=right_hand_size,
        public_hand_constraints=public_hand_constraints,
        hidden_card_inference_constraints=(
            inference_model.constraints if inference_model is not None else None
        ),
    )
    return world


def copy_coherent_hidden_world(
    world: CoherentHiddenWorld,
) -> CoherentHiddenWorld:
    """Returns an equal immutable world object for one independent path."""
    return replace(world)


def get_hidden_world_card_owner(
    world: CoherentHiddenWorld,
    card: str,
) -> str | None:
    """Returns a card's current location, or its prior opponent owner."""
    if card in world.left_hand:
        return "left"
    if card in world.right_hand:
        return "right"
    if card in world.hypothetical_skat:
        return "hypothetical_skat"
    for player, transitioned_card in world.ownership_transitions:
        if transitioned_card == card:
            return f"played_by_{player}"
    return None


def remove_card_from_hidden_world(
    world: CoherentHiddenWorld,
    player: str,
    card: str,
    *,
    step_index: int = 0,
) -> CoherentHiddenWorld:
    """Returns a world after one card is played by its current owner."""
    if player not in _OPPONENT_PLAYERS:
        _raise_invariant_error(
            step_index,
            f"attempted owner {player!r} is unsupported; expected left or right.",
        )
    owner = get_hidden_world_card_owner(world, card)
    if owner != player:
        _raise_invariant_error(
            step_index,
            f"card {card} has owner {owner!r}, attempted owner {player!r}.",
        )

    hand_name = f"{player}_hand"
    hand = getattr(world, hand_name)
    updated_world = replace(
        world,
        **{
            hand_name: tuple(owned_card for owned_card in hand if owned_card != card),
            "ownership_transitions": (*world.ownership_transitions, (player, card)),
        },
    )
    validate_coherent_hidden_world(updated_world, step_index=step_index)
    return updated_world


def apply_hidden_world_plays(
    world: CoherentHiddenWorld,
    plays: tuple[tuple[str, str], ...],
    *,
    step_index: int = 0,
) -> CoherentHiddenWorld:
    """Applies one step's ordered opponent plays as immutable transitions."""
    updated_world = world
    for player, card in plays:
        updated_world = remove_card_from_hidden_world(
            updated_world,
            player,
            card,
            step_index=step_index,
        )
    return updated_world


def build_hidden_world_summary(world: CoherentHiddenWorld) -> dict[str, Any]:
    """Builds deterministic coherence metadata without serializing hidden cards."""
    validate_coherent_hidden_world(world)
    provenance = world.provenance
    if provenance is None:  # Kept explicit for static type narrowing.
        raise ValueError("Hidden-world provenance is missing.")
    transition_count = len(world.ownership_transitions)
    return {
        "mode": COHERENT_PATH_MODE,
        "initial_left_hand_size": provenance.initial_left_hand_size,
        "initial_right_hand_size": provenance.initial_right_hand_size,
        "initial_hypothetical_skat_size": (
            provenance.initial_hypothetical_skat_size
        ),
        "remaining_left_hand_size": len(world.left_hand),
        "remaining_right_hand_size": len(world.right_hand),
        "remaining_hypothetical_skat_size": len(world.hypothetical_skat),
        "root_sample_count": provenance.root_sample_count,
        "sampled_once": provenance.root_sample_count == 1,
        "resampled_after_path_start": False,
        "ownership_transition_count": transition_count,
        "opponent_cards_played": transition_count,
        "ownership_preserved": True,
        "hand_sizes_reconciled": True,
        "hypothetical_skat_fixed": True,
        "duplicate_card_detected": False,
        "ownership_violation_detected": False,
        "hidden_cards_emitted": False,
    }


def derive_simulation_child_seed(
    random_seed: int | None,
    stream_name: str,
    *,
    child_index: int = 0,
) -> int | None:
    """Derives a process-stable seed for one independent simulation stream."""
    if random_seed is None:
        return None
    if not stream_name:
        raise ValueError("stream_name must not be empty.")
    if child_index < 0:
        raise ValueError("child_index must not be negative.")
    material = f"skat-ai\0{random_seed}\0{stream_name}\0{child_index}".encode()
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")
