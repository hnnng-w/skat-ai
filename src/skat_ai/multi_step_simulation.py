import random
from typing import Any

from skat_ai.card_selection import choose_card_by_policy
from skat_ai.game_state import GameState
from skat_ai.multi_step_summary import build_multi_step_summary
from skat_ai.opponent_sequence import (
    can_prepare_player_action,
    extract_opponent_sequence_cards,
    get_unsupported_next_player_reason,
    prepare_player_action_state,
)
from skat_ai.simulation_context import (
    SimulationContext,
    add_simulated_opponent_cards,
    add_simulation_event,
    apply_context_to_state_for_sampling,
    build_context_summary,
    validate_no_duplicate_simulated_opponent_cards,
)
from skat_ai.simulation_step import simulate_and_advance_once
from skat_ai.strategic_metadata import StrategicMetadata


def should_continue_multi_step_simulation(
    current_state: GameState,
    step_index: int,
) -> bool:
    """
    Determines whether the multi-step simulation should continue.

    The first step is always allowed for backward compatibility.
    Later steps continue only if the engine can prepare a state where
    the player can act.
    """
    if step_index == 0:
        return True

    return can_prepare_player_action(current_state.next_player)


def get_multi_step_stop_reason(
    current_state: GameState,
    step_index: int,
) -> str | None:
    """
    Returns a human-readable stop reason if simulation should stop.
    """
    if current_state.hand == []:
        return "Player has no cards left."

    if step_index > 0 and not can_prepare_player_action(current_state.next_player):
        return get_unsupported_next_player_reason(current_state.next_player)

    return None


def prepare_state_for_player_action(
    current_state: GameState,
    left_hand_size: int,
    right_hand_size: int,
    random_generator: random.Random,
    opponent_lead_policy: str = "lowest_point",
    opponent_response_policy: str = "lowest_point",
) -> tuple[GameState, dict[str, Any] | None]:
    """
    Prepares a state where the player can act.

    Kept as a compatibility wrapper around opponent_sequence.prepare_player_action_state.
    """
    return prepare_player_action_state(
        current_state=current_state,
        left_hand_size=left_hand_size,
        right_hand_size=right_hand_size,
        random_generator=random_generator,
        opponent_lead_policy=opponent_lead_policy,
        opponent_response_policy=opponent_response_policy,
    )

def extract_opponent_cards_from_step(
    step: dict[str, Any],
) -> list[str]:
    """
    Extracts simulated opponent cards from one multi-step result.

    Sources:
    - opponent sequence cards
    - opponent cards inside the completed trick, excluding the candidate card
    """
    opponent_cards = extract_opponent_sequence_cards(
        step.get("opponent_lead_result")
    )

    detailed_result = step["detailed_result"]
    trick = detailed_result["trick"]
    candidate_card = step["candidate_card"]

    for card in trick:
        if card != candidate_card and card not in opponent_cards:
            opponent_cards.append(card)

    return opponent_cards

def simulate_multiple_steps(
    state: GameState,
    left_hand_size: int,
    right_hand_size: int,
    step_count: int,
    random_seed: int | None = None,
    use_basic_opponent_strategy: bool = True,
    card_selection_policy: str = "first_legal",
    expected_value_sample_count: int = 100,
    strict_context: bool = False,
    strategic_metadata: StrategicMetadata | None = None,
    opponent_lead_policy: str = "lowest_point",
    opponent_response_policy: str = "lowest_point",
) -> dict[str, Any]:
    """
    Simulates multiple sequential player-action steps.

    Current simplifications:
    - The candidate card is selected with a configurable policy.
    - The first step assumes the player can act in the current state.
    - Later steps continue if next_player is "me".
    - If next_player is "right", right can lead first, because me acts next.
    - If next_player is "left", simulation stops for now.
    - Opponent hands are resampled each step from unseen cards.
    """
    if step_count <= 0:
        raise ValueError("step_count must be a positive integer.")

    rng = random.Random(random_seed) if random_seed is not None else random

    current_state = state
    steps = []
    stop_reason = None
    context = (
        SimulationContext(strategic_metadata=strategic_metadata)
        if strategic_metadata is not None
        else SimulationContext()
    )

    for step_index in range(step_count):
        stop_reason = get_multi_step_stop_reason(
            current_state=current_state,
            step_index=step_index,
        )

        if stop_reason is not None:
            break

        if not should_continue_multi_step_simulation(
            current_state=current_state,
            step_index=step_index,
        ):
            stop_reason = f"Next player is {current_state.next_player}, not supported."
            break

        sampling_state = apply_context_to_state_for_sampling(
            state=current_state,
            context=context,
        )

        prepared_state, opponent_lead_result = prepare_state_for_player_action(
            current_state=sampling_state,
            left_hand_size=left_hand_size,
            right_hand_size=right_hand_size,
            random_generator=rng,
            opponent_lead_policy=opponent_lead_policy,
            opponent_response_policy=opponent_response_policy,
        )

        candidate_card = choose_card_by_policy(
            state=prepared_state,
            policy=card_selection_policy,
            left_hand_size=left_hand_size,
            right_hand_size=right_hand_size,
            expected_value_sample_count=expected_value_sample_count,
            random_seed=rng.randint(0, 10**9) if random_seed is not None else None,
            use_basic_opponent_strategy=use_basic_opponent_strategy,
        )

        step_result = simulate_and_advance_once(
            state=prepared_state,
            candidate_card=candidate_card,
            left_hand_size=left_hand_size,
            right_hand_size=right_hand_size,
            random_generator=rng,
            use_basic_opponent_strategy=use_basic_opponent_strategy,
        )

        step = {
            "step_index": step_index,
            "opponent_lead_result": opponent_lead_result,
            "candidate_card": candidate_card,
            "card_selection_policy": card_selection_policy,
            "detailed_result": step_result["detailed_result"],
            "next_state": step_result["next_state"],
        }

        opponent_cards = extract_opponent_cards_from_step(step)

        context = add_simulated_opponent_cards(
            context=context,
            cards=opponent_cards,
        )

        context = add_simulation_event(
            context=context,
            event={
                "type": "player_action_step",
                "step_index": step_index,
                "candidate_card": candidate_card,
                "opponent_cards": opponent_cards,
            },
        )

        if strict_context:
            validate_no_duplicate_simulated_opponent_cards(context)

        steps.append(step)

        current_state = step_result["next_state"]

    if stop_reason is None and len(steps) == step_count:
        stop_reason = "Requested step count reached."

    result = {
        "initial_state": state,
        "final_state": current_state,
        "card_selection_policy": card_selection_policy,
        "requested_step_count": step_count,
        "steps_simulated": len(steps),
        "stop_reason": stop_reason,
        "strict_context": strict_context,
        "context": context,
        "context_summary": build_context_summary(context),
        "steps": steps,
    }

    result["summary"] = build_multi_step_summary(result)

    return result