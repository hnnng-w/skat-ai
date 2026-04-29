import random
from typing import Any

from skat_ai.game_state import GameState
from skat_ai.simulation import simulate_immediate_trick_once_detailed
from skat_ai.state_transition import advance_state_after_detailed_trick


def simulate_and_advance_once(
    state: GameState,
    candidate_card: str,
    left_hand_size: int,
    right_hand_size: int,
    random_generator: random.Random | None = None,
    use_basic_opponent_strategy: bool = True,
) -> dict[str, Any]:
    """
    Simulates one immediate trick and advances the game state.

    Returns:
    - detailed_result: detailed immediate trick simulation result
    - next_state: GameState after applying the completed trick
    """
    detailed_result = simulate_immediate_trick_once_detailed(
        state=state,
        candidate_card=candidate_card,
        left_hand_size=left_hand_size,
        right_hand_size=right_hand_size,
        random_generator=random_generator,
        use_basic_opponent_strategy=use_basic_opponent_strategy,
    )

    next_state = advance_state_after_detailed_trick(
        state=state,
        candidate_card=candidate_card,
        detailed_result=detailed_result,
    )

    return {
        "detailed_result": detailed_result,
        "next_state": next_state,
    }