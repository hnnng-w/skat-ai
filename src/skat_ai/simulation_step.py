from __future__ import annotations

import random
from typing import TYPE_CHECKING, Any

from skat_ai.game_state import GameState
from skat_ai.hidden_card_inference import HiddenCardInferenceModel
from skat_ai.public_hand_constraint import PublicHandConstraint
from skat_ai.simulation import simulate_immediate_trick_once_detailed
from skat_ai.state_transition import advance_state_after_detailed_trick

if TYPE_CHECKING:
    from skat_ai.coherent_hidden_world import CoherentHiddenWorld


def simulate_and_advance_once(
    state: GameState,
    candidate_card: str,
    left_hand_size: int,
    right_hand_size: int,
    random_generator: random.Random | None = None,
    use_basic_opponent_strategy: bool = True,
    opponent_response_policy_by_player: dict[str, str] | None = None,
    public_hand_constraints: tuple[PublicHandConstraint, ...] = (),
    coherent_hidden_world: CoherentHiddenWorld | None = None,
    coherent_step_index: int = 0,
    hidden_card_inference_model: HiddenCardInferenceModel | None = None,
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
        opponent_response_policy_by_player=opponent_response_policy_by_player,
        public_hand_constraints=public_hand_constraints,
        coherent_hidden_world=coherent_hidden_world,
        coherent_step_index=coherent_step_index,
        hidden_card_inference_model=hidden_card_inference_model,
    )

    updated_hidden_world = detailed_result.pop("_coherent_hidden_world", None)
    opponent_plays = detailed_result.pop("_opponent_plays", ())

    next_state = advance_state_after_detailed_trick(
        state=state,
        candidate_card=candidate_card,
        detailed_result=detailed_result,
    )

    result = {
        "detailed_result": detailed_result,
        "next_state": next_state,
    }
    if updated_hidden_world is not None:
        result["coherent_hidden_world"] = updated_hidden_world
        result["opponent_plays"] = opponent_plays
    return result
