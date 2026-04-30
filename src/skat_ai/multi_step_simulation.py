import random
from typing import Any

from skat_ai.card_selection import choose_card_by_policy
from skat_ai.game_state import GameState
from skat_ai.opponent_lead import (
    simulate_left_lead_and_right_response_once,
    simulate_opponent_lead_once,
)
from skat_ai.simulation_context import (
    SimulationContext,
    add_simulated_opponent_cards,
    add_simulation_event,
    apply_context_to_state_for_sampling,
    build_context_summary,
)
from skat_ai.simulation_step import simulate_and_advance_once


def should_continue_multi_step_simulation(
    current_state: GameState,
    step_index: int,
) -> bool:
    """
    Determines whether the multi-step simulation should continue.

    The first step is always allowed.
    Later player-action steps are allowed if the player is next to act.
    If right is next to act, right can lead because me acts second.
    If left is next to act, left can lead and right can respond because me acts third.
    """
    if step_index == 0:
        return True

    return current_state.next_player in ["me", "right", "left"]


def get_multi_step_stop_reason(
    current_state: GameState,
    step_index: int,
) -> str | None:
    """
    Returns a human-readable stop reason if simulation should stop.
    """
    if current_state.hand == []:
        return "Player has no cards left."

    if step_index > 0 and current_state.next_player not in ["me", "right", "left", "unknown"]:
        return f"Next player is {current_state.next_player}, not supported."

    return None


def prepare_state_for_player_action(
    current_state: GameState,
    left_hand_size: int,
    right_hand_size: int,
    random_generator: random.Random,
) -> tuple[GameState, dict[str, Any] | None]:
    """
    Prepares a state where the player can act.

    If current_state.next_player is "right", right leads a new trick and
    the returned next state has next_player set to "me".

    If current_state.next_player is "left", left leads and right responds,
    so the returned next state has two cards in current_trick and next_player
    set to "me".

    If current_state.next_player is already "me", the state is returned unchanged.

    If current_state.next_player is "unknown", the state is also returned unchanged.
    This keeps older inputs and tests compatible where next_player was not tracked yet.
    """
    if current_state.next_player in ["me", "unknown"]:
        return current_state, None

    if current_state.next_player == "right":
        opponent_lead_result = simulate_opponent_lead_once(
            state=current_state,
            left_hand_size=left_hand_size,
            right_hand_size=right_hand_size,
            random_generator=random_generator,
        )

        return opponent_lead_result["next_state"], opponent_lead_result

    if current_state.next_player == "left":
        opponent_lead_result = simulate_left_lead_and_right_response_once(
            state=current_state,
            left_hand_size=left_hand_size,
            right_hand_size=right_hand_size,
            random_generator=random_generator,
        )

        return opponent_lead_result["next_state"], opponent_lead_result

    raise ValueError(
        "Cannot prepare player action when "
        f"next_player is {current_state.next_player}."
    )

def extract_opponent_cards_from_step(
    step: dict[str, Any],
) -> list[str]:
    """
    Extracts simulated opponent cards from one multi-step result.

    Sources:
    - opponent lead card
    - opponent response card
    - opponent cards inside the completed trick, excluding the candidate card
    """
    opponent_cards = []

    opponent_lead_result = step.get("opponent_lead_result")
    if opponent_lead_result is not None:
        opponent_cards.append(opponent_lead_result["lead_card"])

        if opponent_lead_result.get("response_card") is not None:
            opponent_cards.append(opponent_lead_result["response_card"])

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
    context = SimulationContext()

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

        steps.append(step)

        current_state = step_result["next_state"]

    if stop_reason is None and len(steps) == step_count:
        stop_reason = "Requested step count reached."

    return {
        "initial_state": state,
        "final_state": current_state,
        "card_selection_policy": card_selection_policy,
        "requested_step_count": step_count,
        "steps_simulated": len(steps),
        "stop_reason": stop_reason,
        "context": context,
        "context_summary": build_context_summary(context),
        "steps": steps,
    }