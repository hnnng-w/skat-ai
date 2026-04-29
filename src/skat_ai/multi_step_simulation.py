import random
from typing import Any

from skat_ai.card_selection import choose_card_by_policy
from skat_ai.game_state import GameState
from skat_ai.simulation_step import simulate_and_advance_once


def simulate_multiple_steps(
    state: GameState,
    left_hand_size: int,
    right_hand_size: int,
    step_count: int,
    random_seed: int | None = None,
    use_basic_opponent_strategy: bool = True,
    card_selection_policy: str = "first_legal",
    expected_value_sample_count: int = 100,
) -> dict[str, Any]:
    """
    Simulates multiple sequential trick steps.

    Current simplifications:
    - The candidate card is selected with a configurable policy.
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

        card_selection_seed = rng.randint(0, 10**9) if random_seed is not None else None

        candidate_card = choose_card_by_policy(
            state=current_state,
            policy=card_selection_policy,
            left_hand_size=left_hand_size,
            right_hand_size=right_hand_size,
            expected_value_sample_count=expected_value_sample_count,
            random_seed=card_selection_seed,
            use_basic_opponent_strategy=use_basic_opponent_strategy,
        )

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
                "card_selection_policy": card_selection_policy,
                "detailed_result": step_result["detailed_result"],
                "next_state": step_result["next_state"],
            }
        )

        current_state = step_result["next_state"]

    return {
        "initial_state": state,
        "final_state": current_state,
        "card_selection_policy": card_selection_policy,
        "steps": steps,
    }