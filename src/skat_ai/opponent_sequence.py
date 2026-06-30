import random
from typing import Any

from skat_ai.game_state import GameState
from skat_ai.opponent_lead import (
    simulate_left_lead_and_right_response_once,
    simulate_opponent_lead_once,
    simulate_right_response_to_left_lead_once,
)
from skat_ai.opponent_policy import get_opponent_policy_settings_for_player
from skat_ai.turn_phase import normalize_turn_phase

UNSUPPORTED_TURN_PHASE_STOP_REASON = "unsupported_turn_phase"
LEFT_LEAD_AND_RIGHT_RESPONSE_PHASE = "left_lead_and_right_response"
RIGHT_LEAD_PHASE = "right_lead"
RIGHT_RESPONSE_TO_LEFT_LEAD_PHASE = "right_response_to_left_lead"


def can_prepare_player_action(
    current_state: GameState,
) -> bool:
    """
    Returns whether the engine can prepare a state where the player can act.

    Supported cases:
    - local player already acts now
    - left leads an empty trick, then right responds
    - right leads an empty trick
    - left has led one card and right responds
    """
    return is_local_action_phase(current_state) or get_preparation_phase(
        current_state
    ) is not None


def get_unsupported_next_player_reason(
    next_player: str,
) -> str:
    """
    Returns a readable reason for unsupported next_player values.
    """
    return f"Next player is {next_player}, not supported."


def get_unsupported_turn_phase_reason() -> str:
    """Returns the stable stop reason for valid but unsupported turn phases."""
    return UNSUPPORTED_TURN_PHASE_STOP_REASON


def is_local_action_phase(current_state: GameState) -> bool:
    """Returns whether the normalized phase already has the local player next."""
    phase = normalize_turn_phase(
        trick_leader=current_state.trick_leader,
        next_player=current_state.next_player,
        current_trick_length=len(current_state.current_trick),
    )

    return phase.next_player == "me"


def get_preparation_phase(current_state: GameState) -> str | None:
    """Returns the supported opponent preparation phase for the state."""
    current_trick_length = len(current_state.current_trick)
    phase = normalize_turn_phase(
        trick_leader=current_state.trick_leader,
        next_player=current_state.next_player,
        current_trick_length=current_trick_length,
    )

    if (
        phase.trick_leader == "left"
        and current_trick_length == 0
        and phase.next_player == "left"
    ):
        return LEFT_LEAD_AND_RIGHT_RESPONSE_PHASE

    if (
        phase.trick_leader == "right"
        and current_trick_length == 0
        and phase.next_player == "right"
    ):
        return RIGHT_LEAD_PHASE

    if (
        phase.trick_leader == "left"
        and current_trick_length == 1
        and phase.next_player == "right"
    ):
        return RIGHT_RESPONSE_TO_LEFT_LEAD_PHASE

    return None


def prepare_player_action_state(
    current_state: GameState,
    left_hand_size: int,
    right_hand_size: int,
    random_generator: random.Random,
    opponent_lead_policy: str = "lowest_point",
    opponent_response_policy: str = "lowest_point",
    left_opponent_policy_settings: dict[str, str] | None = None,
    right_opponent_policy_settings: dict[str, str] | None = None,
) -> tuple[GameState, dict[str, Any] | None]:
    """
    Prepares a state where the player can act.

    Cases:
    - local player already acts now: return state unchanged
    - empty right lead: simulate right lead, then me acts second
    - empty left lead: simulate left lead and right response, then me acts third
    - one-card left lead: simulate only right's response, then me acts third

    Returns:
    - prepared GameState
    - optional opponent sequence result
    """
    if is_local_action_phase(current_state):
        return current_state, None

    opponent_policy_settings = {
        "opponent_lead_policy": opponent_lead_policy,
        "opponent_response_policy": opponent_response_policy,
    }

    preparation_phase = get_preparation_phase(current_state)

    if preparation_phase == RIGHT_LEAD_PHASE:
        right_policy_settings = get_opponent_policy_settings_for_player(
            player="right",
            opponent_policy_settings=opponent_policy_settings,
            left_opponent_policy_settings=left_opponent_policy_settings,
            right_opponent_policy_settings=right_opponent_policy_settings,
        )

        opponent_sequence_result = simulate_opponent_lead_once(
            state=current_state,
            left_hand_size=left_hand_size,
            right_hand_size=right_hand_size,
            random_generator=random_generator,
            opponent_lead_policy=right_policy_settings["opponent_lead_policy"],
        )

        return opponent_sequence_result["next_state"], opponent_sequence_result

    if preparation_phase == LEFT_LEAD_AND_RIGHT_RESPONSE_PHASE:
        left_policy_settings = get_opponent_policy_settings_for_player(
            player="left",
            opponent_policy_settings=opponent_policy_settings,
            left_opponent_policy_settings=left_opponent_policy_settings,
            right_opponent_policy_settings=right_opponent_policy_settings,
        )
        right_policy_settings = get_opponent_policy_settings_for_player(
            player="right",
            opponent_policy_settings=opponent_policy_settings,
            left_opponent_policy_settings=left_opponent_policy_settings,
            right_opponent_policy_settings=right_opponent_policy_settings,
        )

        opponent_sequence_result = simulate_left_lead_and_right_response_once(
            state=current_state,
            left_hand_size=left_hand_size,
            right_hand_size=right_hand_size,
            random_generator=random_generator,
            opponent_lead_policy=left_policy_settings["opponent_lead_policy"],
            opponent_response_policy=right_policy_settings["opponent_response_policy"],
        )

        return opponent_sequence_result["next_state"], opponent_sequence_result

    if preparation_phase == RIGHT_RESPONSE_TO_LEFT_LEAD_PHASE:
        right_policy_settings = get_opponent_policy_settings_for_player(
            player="right",
            opponent_policy_settings=opponent_policy_settings,
            left_opponent_policy_settings=left_opponent_policy_settings,
            right_opponent_policy_settings=right_opponent_policy_settings,
        )

        opponent_sequence_result = simulate_right_response_to_left_lead_once(
            state=current_state,
            left_hand_size=left_hand_size,
            right_hand_size=right_hand_size,
            random_generator=random_generator,
            opponent_response_policy=right_policy_settings["opponent_response_policy"],
        )

        return opponent_sequence_result["next_state"], opponent_sequence_result

    raise ValueError(get_unsupported_turn_phase_reason())

def build_serializable_opponent_sequence_result(
    opponent_sequence_result: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """
    Builds a JSON-serializable opponent sequence result.

    The internal result may contain a GameState under next_state.
    This function keeps only stable scalar fields.
    """
    if opponent_sequence_result is None:
        return None

    return {
        "leader": opponent_sequence_result.get("leader"),
        "lead_card": opponent_sequence_result.get("lead_card"),
        "responder": opponent_sequence_result.get("responder"),
        "response_card": opponent_sequence_result.get("response_card"),
    }


def extract_opponent_sequence_cards(
    opponent_sequence_result: dict[str, Any] | None,
) -> list[str]:
    """
    Extracts opponent cards from an opponent sequence result.
    """
    if opponent_sequence_result is None:
        return []

    cards = []

    lead_card = opponent_sequence_result.get("lead_card")
    response_card = opponent_sequence_result.get("response_card")

    if lead_card is not None:
        cards.append(lead_card)

    if response_card is not None:
        cards.append(response_card)

    return cards
