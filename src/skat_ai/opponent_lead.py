import random

from skat_ai.game_state import GameState
from skat_ai.rules import get_card_points
from skat_ai.simulation import generate_random_opponent_hands


def choose_lowest_point_lead_card(hand: list[str]) -> str:
    """
    Chooses the lowest-point card from an opponent hand for leading a new trick.
    """
    if not hand:
        raise ValueError("Opponent hand is empty.")

    return min(hand, key=get_card_points)


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