import random
from typing import Any

from skat_ai.game_state import GameState
from skat_ai.opponent_lead import (
    simulate_left_lead_and_right_response_once,
    simulate_opponent_lead_once,
)
from skat_ai.opponent_policy import get_opponent_policy_settings_for_player

SUPPORTED_NEXT_PLAYERS_FOR_PLAYER_ACTION = [
    "me",
    "unknown",
    "right",
    "left",
]


def can_prepare_player_action(
    next_player: str,
) -> bool:
    """
    Returns whether the engine can prepare a state where the player can act.

    Supported cases:
    - me: player can act immediately
    - unknown: legacy compatibility, assume player can act
    - right: right leads, then me acts second
    - left: left leads, right responds, then me acts third
    """
    return next_player in SUPPORTED_NEXT_PLAYERS_FOR_PLAYER_ACTION


def get_unsupported_next_player_reason(
    next_player: str,
) -> str:
    """
    Returns a readable reason for unsupported next_player values.
    """
    return f"Next player is {next_player}, not supported."


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
    - next_player == "me": return state unchanged
    - next_player == "unknown": return state unchanged for legacy compatibility
    - next_player == "right": simulate right lead, then me acts second
    - next_player == "left": simulate left lead and right response, then me acts third

    Returns:
    - prepared GameState
    - optional opponent sequence result
    """
    if current_state.next_player in ["me", "unknown"]:
        return current_state, None

    opponent_policy_settings = {
        "opponent_lead_policy": opponent_lead_policy,
        "opponent_response_policy": opponent_response_policy,
    }

    if current_state.next_player == "right":
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

    if current_state.next_player == "left":
        left_policy_settings = get_opponent_policy_settings_for_player(
            player="left",
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
            opponent_response_policy=opponent_response_policy,
        )

        return opponent_sequence_result["next_state"], opponent_sequence_result

    raise ValueError(get_unsupported_next_player_reason(current_state.next_player))

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