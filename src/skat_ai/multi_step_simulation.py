import random
from typing import Any

from skat_ai.game_state import GameState
from skat_ai.rules import get_legal_cards
from skat_ai.simulation_step import simulate_and_advance_once


def choose_first_legal_card(
    state: GameState,
) -> str:
    """
    Chooses the first legal card from the current state.

    This is a simple placeholder policy for multi-step simulation.
    Smarter policies can be added later.
    """
    legal_cards = get_legal_cards(
        hand=state.hand,
        current_trick=state.current_trick,
        game_type=state.game_type,
    )

    if not legal_cards:
        raise ValueError("No legal cards available.")

    return legal_cards[0]


def simulate_multiple_steps(
    state: GameState,
    left_hand_size: int,
    right_hand_size: int,
    step_count: int,
    random_seed: int | None = None,
    use_basic_opponent_strategy: bool = True,
) -> dict[str, Any]:
    """
    Simulates multiple sequential trick steps.

    Current simplifications:
    - The candidate card is selected with a simple first-legal-card policy.
    - Each step assumes the player can act in the current state.
    - Opponent hands are resampled each step from unseen cards.
    """
    if step_count <= 0:
        raise ValueError("step_count must be a positive integer.")

    rng = random.Random(random_seed) if random_seed is not None else random

    current_state = state
    steps = []

    for step_index in range(step_count):
        if not current_state.hand:
            break

        candidate_card = choose_first_legal_card(current_state)

        step_result = simulate_and_advance_once(
            state=current_state,
            candidate_card=candidate_card,
            left_hand_size=left_hand_size,
            right_hand_size=right_hand_size,
            random_generator=rng,
            use_basic_opponent_strategy=use_basic_opponent_strategy,
        )

        steps.append(
            {
                "step_index": step_index,
                "candidate_card": candidate_card,
                "detailed_result": step_result["detailed_result"],
                "next_state": step_result["next_state"],
            }
        )

        current_state = step_result["next_state"]

    return {
        "initial_state": state,
        "final_state": current_state,
        "steps": steps,
    }