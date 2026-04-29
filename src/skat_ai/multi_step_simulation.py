import random
from typing import Any

from skat_ai.card_selection import choose_card_by_policy
from skat_ai.game_state import GameState
from skat_ai.opponent_lead import simulate_opponent_lead_once
from skat_ai.simulation_step import simulate_and_advance_once


def should_continue_multi_step_simulation(
    current_state: GameState,
    step_index: int,
) -> bool:
    """
    Determines whether the multi-step simulation should continue.

    The first step is always allowed.
    Later player-action steps are allowed if the player is next to act.
    If right is next to act, the simulation can first simulate a right lead,
    because me acts directly after right in the current seating model.
    """
    if step_index == 0:
        return True

    return current_state.next_player in ["me", "right"]


def get_multi_step_stop_reason(
    current_state: GameState,
    step_index: int,
) -> str | None:
    """
    Returns a human-readable stop reason if simulation should stop.
    """
    if current_state.hand == []:
        return "Player has no cards left."

    if current_state.current_trick == [] and current_state.next_player == "left":
        return "Next player is left. Opponent second-hand simulation is not implemented yet."

    if step_index > 0 and current_state.next_player == "left":
        return "Next player is left. Opponent second-hand simulation is not implemented yet."

    if step_index > 0 and current_state.next_player not in ["me", "right", "unknown"]:
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

    raise ValueError(
        "Cannot prepare player action when "
        f"next_player is {current_state.next_player}."
    )

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

        prepared_state, opponent_lead_result = prepare_state_for_player_action(
            current_state=current_state,
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

        steps.append(
            {
                "step_index": step_index,
                "opponent_lead_result": opponent_lead_result,
                "candidate_card": candidate_card,
                "card_selection_policy": card_selection_policy,
                "detailed_result": step_result["detailed_result"],
                "next_state": step_result["next_state"],
            }
        )

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
        "steps": steps,
    }