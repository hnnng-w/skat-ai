import random
from typing import Any

from skat_ai.game_state import GameState
from skat_ai.rules import get_card_points, get_legal_cards
from skat_ai.simulation import generate_random_opponent_hands


def choose_lowest_point_lead_card(hand: list[str]) -> str:
    """
    Chooses the lowest-point card from an opponent hand for leading a new trick.
    """
    if not hand:
        raise ValueError("Opponent hand is empty.")

    return min(hand, key=get_card_points)


def choose_lowest_point_legal_response_card(
    hand: list[str],
    current_trick: list[str],
    game_type: str,
) -> str:
    """
    Chooses the lowest-point legal response card from an opponent hand.
    """
    legal_cards = get_legal_cards(
        hand=hand,
        current_trick=current_trick,
        game_type=game_type,
    )

    if not legal_cards:
        raise ValueError("Opponent has no legal response cards.")

    return min(legal_cards, key=get_card_points)


def get_next_player_after_opponent_lead(leader: str) -> str:
    """
    Returns the next player after an opponent leads a trick.

    Seating model:
    me -> left -> right -> me
    """
    if leader == "left":
        return "right"

    if leader == "right":
        return "me"

    raise ValueError(f"Invalid opponent leader: {leader}")


def build_state_after_opponent_lead(
    state: GameState,
    lead_card: str,
    leader: str,
) -> GameState:
    """
    Builds a new GameState after an opponent leads a new trick.

    The old state is not mutated.
    """
    if leader not in ["left", "right"]:
        raise ValueError(f"Invalid opponent leader: {leader}")

    next_player = get_next_player_after_opponent_lead(leader)

    return GameState(
        game_type=state.game_type,
        player_role=state.player_role,
        hand=state.hand.copy(),
        current_trick=[lead_card],
        played_cards=state.played_cards.copy(),
        skat=state.skat.copy(),
        player_position=state.player_position,
        trick_leader=leader,
        completed_tricks=[completed_trick.copy() for completed_trick in state.completed_tricks],
        declarer_points=state.declarer_points,
        defender_points=state.defender_points,
        next_player=next_player,
    )


def build_state_after_opponent_second_hand_play(
    state: GameState,
    response_card: str,
    responder: str,
) -> GameState:
    """
    Builds a new GameState after an opponent plays second hand.

    This is currently intended for:
    left leads -> right responds -> me acts third
    """
    if responder not in ["left", "right"]:
        raise ValueError(f"Invalid opponent responder: {responder}")

    if len(state.current_trick) != 1:
        raise ValueError("Opponent second-hand play requires exactly one card in current_trick.")

    return GameState(
        game_type=state.game_type,
        player_role=state.player_role,
        hand=state.hand.copy(),
        current_trick=[*state.current_trick, response_card],
        played_cards=state.played_cards.copy(),
        skat=state.skat.copy(),
        player_position=state.player_position,
        trick_leader=state.trick_leader,
        completed_tricks=[completed_trick.copy() for completed_trick in state.completed_tricks],
        declarer_points=state.declarer_points,
        defender_points=state.defender_points,
        next_player="me",
    )


def simulate_opponent_lead_once(
    state: GameState,
    left_hand_size: int,
    right_hand_size: int,
    random_generator: random.Random | None = None,
) -> dict[str, str | GameState]:
    """
    Simulates one opponent lead when next_player is left or right.

    This starts a new trick with one opponent card.
    """
    if state.next_player not in ["left", "right"]:
        raise ValueError("Opponent lead requires next_player to be left or right.")

    rng = random_generator or random

    left_hand, right_hand = generate_random_opponent_hands(
        state=state,
        left_hand_size=left_hand_size,
        right_hand_size=right_hand_size,
        random_generator=rng,
    )

    if state.next_player == "left":
        leader_hand = left_hand
    else:
        leader_hand = right_hand

    lead_card = choose_lowest_point_lead_card(leader_hand)

    next_state = build_state_after_opponent_lead(
        state=state,
        lead_card=lead_card,
        leader=state.next_player,
    )

    return {
        "leader": state.next_player,
        "lead_card": lead_card,
        "next_state": next_state,
    }


def simulate_left_lead_and_right_response_once(
    state: GameState,
    left_hand_size: int,
    right_hand_size: int,
    random_generator: random.Random | None = None,
) -> dict[str, Any]:
    """
    Simulates the sequence:
    left leads -> right responds -> me acts third.

    This prepares a state where the player can act with two cards already
    in current_trick.
    """
    if state.next_player != "left":
        raise ValueError("Left lead sequence requires next_player to be left.")

    rng = random_generator or random

    left_hand, right_hand = generate_random_opponent_hands(
        state=state,
        left_hand_size=left_hand_size,
        right_hand_size=right_hand_size,
        random_generator=rng,
    )

    lead_card = choose_lowest_point_lead_card(left_hand)

    state_after_left_lead = build_state_after_opponent_lead(
        state=state,
        lead_card=lead_card,
        leader="left",
    )

    response_card = choose_lowest_point_legal_response_card(
        hand=right_hand,
        current_trick=state_after_left_lead.current_trick,
        game_type=state.game_type,
    )

    next_state = build_state_after_opponent_second_hand_play(
        state=state_after_left_lead,
        response_card=response_card,
        responder="right",
    )

    return {
        "leader": "left",
        "lead_card": lead_card,
        "responder": "right",
        "response_card": response_card,
        "next_state": next_state,
    }