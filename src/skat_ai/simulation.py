import random
from typing import Any

from skat_ai.card_tracking import get_unseen_cards
from skat_ai.game_history import build_completed_trick_from_state_and_candidate
from skat_ai.game_state import GameState
from skat_ai.rules import (
    get_card_points,
    get_card_strength,
    get_effective_suit,
    get_legal_cards,
    get_trick_points,
    get_trick_winner,
)


def generate_random_opponent_hands(
    state: GameState,
    left_hand_size: int,
    right_hand_size: int,
    random_generator: random.Random | None = None,
) -> tuple[list[str], list[str]]:
    """
    Generates one random possible card distribution for the two opponents.

    The function uses only cards that are currently unseen from the player's perspective.
    """
    rng = random_generator or random

    unseen_cards = get_unseen_cards(state)
    required_card_count = left_hand_size + right_hand_size

    if required_card_count > len(unseen_cards):
        raise ValueError("Requested more opponent cards than unseen cards available.")

    shuffled_cards = unseen_cards.copy()
    rng.shuffle(shuffled_cards)

    left_hand = shuffled_cards[:left_hand_size]
    right_hand = shuffled_cards[left_hand_size:required_card_count]

    return left_hand, right_hand


def generate_multiple_random_opponent_hands(
    state: GameState,
    left_hand_size: int,
    right_hand_size: int,
    sample_count: int,
    random_seed: int | None = None,
) -> list[tuple[list[str], list[str]]]:
    """
    Generates multiple random possible card distributions for the two opponents.
    """
    if sample_count <= 0:
        raise ValueError("Sample count must be greater than zero.")

    rng = random.Random(random_seed) if random_seed is not None else random

    return [
        generate_random_opponent_hands(
            state=state,
            left_hand_size=left_hand_size,
            right_hand_size=right_hand_size,
            random_generator=rng,
        )
        for _ in range(sample_count)
    ]


def choose_random_legal_card(
    hand: list[str],
    current_trick: list[str],
    game_type: str,
    random_generator: random.Random | None = None,
) -> str:
    """
    Chooses one random legal card from a hand.

    This function is kept for comparison tests and future experiments.
    """
    rng = random_generator or random

    legal_cards = get_legal_cards(
        hand=hand,
        current_trick=current_trick,
        game_type=game_type,
    )

    if not legal_cards:
        raise ValueError("No legal cards available.")

    return rng.choice(legal_cards)


def choose_basic_opponent_card(
    hand: list[str],
    current_trick: list[str],
    game_type: str,
) -> str:
    """
    Chooses a legal opponent card using a simple deterministic heuristic.

    Basic opponent strategy:
    - If the opponent can currently win the trick, play the lowest-point winning card.
    - Otherwise, play the lowest-point legal card.
    """
    legal_cards = get_legal_cards(
        hand=hand,
        current_trick=current_trick,
        game_type=game_type,
    )

    if not legal_cards:
        raise ValueError("No legal cards available.")

    if not current_trick:
        return min(legal_cards, key=get_card_points)

    lead_effective_suit = get_effective_suit(current_trick[0], game_type)

    current_best_strength = max(
        get_card_strength(card, game_type, lead_effective_suit) for card in current_trick
    )

    winning_cards = [
        card
        for card in legal_cards
        if get_card_strength(card, game_type, lead_effective_suit) > current_best_strength
    ]

    if winning_cards:
        return min(winning_cards, key=get_card_points)

    return min(legal_cards, key=get_card_points)


def validate_candidate_card_for_current_trick(state: GameState, candidate_card: str) -> None:
    """
    Validates that the candidate card can legally be played in the current state.
    """
    if candidate_card not in state.hand:
        raise ValueError("Candidate card must be in the player's hand.")

    legal_cards = get_legal_cards(
        hand=state.hand,
        current_trick=state.current_trick,
        game_type=state.game_type,
    )

    if candidate_card not in legal_cards:
        raise ValueError("Candidate card must be legal in the current trick.")

    if len(state.current_trick) > 2:
        raise ValueError("Current trick must contain at most 2 cards.")


def complete_trick_after_candidate_card(
    state: GameState,
    candidate_card: str,
    left_hand: list[str],
    right_hand: list[str],
    random_generator: random.Random | None = None,
    use_basic_opponent_strategy: bool = True,
) -> list[str]:
    """
    Completes the current trick after the player plays candidate_card.

    Assumptions:
    - If current_trick has 0 cards, the player leads and both opponents play.
    - If current_trick has 1 card, the player plays second and one opponent plays after.
    - If current_trick has 2 cards, the player plays third and the trick is complete.
    """
    rng = random_generator or random

    trick = state.current_trick.copy()
    trick.append(candidate_card)

    if len(trick) == 1:
        if use_basic_opponent_strategy:
            left_card = choose_basic_opponent_card(
                hand=left_hand,
                current_trick=trick,
                game_type=state.game_type,
            )
        else:
            left_card = choose_random_legal_card(
                hand=left_hand,
                current_trick=trick,
                game_type=state.game_type,
                random_generator=rng,
            )

        trick.append(left_card)

        if use_basic_opponent_strategy:
            right_card = choose_basic_opponent_card(
                hand=right_hand,
                current_trick=trick,
                game_type=state.game_type,
            )
        else:
            right_card = choose_random_legal_card(
                hand=right_hand,
                current_trick=trick,
                game_type=state.game_type,
                random_generator=rng,
            )

        trick.append(right_card)

    elif len(trick) == 2:
        if use_basic_opponent_strategy:
            right_card = choose_basic_opponent_card(
                hand=right_hand,
                current_trick=trick,
                game_type=state.game_type,
            )
        else:
            right_card = choose_random_legal_card(
                hand=right_hand,
                current_trick=trick,
                game_type=state.game_type,
                random_generator=rng,
            )

        trick.append(right_card)

    elif len(trick) == 3:
        return trick

    else:
        raise ValueError("Completed trick must contain exactly 3 cards.")

    return trick


def simulate_immediate_trick_once(
    state: GameState,
    candidate_card: str,
    left_hand_size: int,
    right_hand_size: int,
    random_generator: random.Random | None = None,
    use_basic_opponent_strategy: bool = True,
) -> bool:
    """
    Simulates the current trick once after the player plays candidate_card.

    Returns True if candidate_card wins the completed trick.
    """
    result = simulate_immediate_trick_once_detailed(
        state=state,
        candidate_card=candidate_card,
        left_hand_size=left_hand_size,
        right_hand_size=right_hand_size,
        random_generator=random_generator,
        use_basic_opponent_strategy=use_basic_opponent_strategy,
    )

    return bool(result["did_win"])


def estimate_immediate_trick_win_rate(
    state: GameState,
    candidate_card: str,
    left_hand_size: int,
    right_hand_size: int,
    sample_count: int,
    random_seed: int | None = None,
    use_basic_opponent_strategy: bool = True,
) -> float:
    """
    Estimates how often candidate_card wins the current trick.
    """
    if sample_count <= 0:
        raise ValueError("Sample count must be greater than zero.")

    rng = random.Random(random_seed) if random_seed is not None else random

    wins = 0

    for _ in range(sample_count):
        did_win = simulate_immediate_trick_once(
            state=state,
            candidate_card=candidate_card,
            left_hand_size=left_hand_size,
            right_hand_size=right_hand_size,
            random_generator=rng,
            use_basic_opponent_strategy=use_basic_opponent_strategy,
        )

        if did_win:
            wins += 1

    return wins / sample_count


def estimate_immediate_trick_win_rates_for_legal_cards(
    state: GameState,
    left_hand_size: int,
    right_hand_size: int,
    sample_count: int,
    random_seed: int | None = None,
    use_basic_opponent_strategy: bool = True,
) -> dict[str, float]:
    """
    Estimates immediate trick win rates for all legal cards in the current state.
    """
    legal_cards = get_legal_cards(
        hand=state.hand,
        current_trick=state.current_trick,
        game_type=state.game_type,
    )

    rng = random.Random(random_seed) if random_seed is not None else None

    return {
        card: estimate_immediate_trick_win_rate(
            state=state,
            candidate_card=card,
            left_hand_size=left_hand_size,
            right_hand_size=right_hand_size,
            sample_count=sample_count,
            random_seed=rng.randint(0, 10**9) if rng is not None else None,
            use_basic_opponent_strategy=use_basic_opponent_strategy,
        )
        for card in legal_cards
    }


def simulate_immediate_trick_once_with_points(
    state: GameState,
    candidate_card: str,
    left_hand_size: int,
    right_hand_size: int,
    random_generator: random.Random | None = None,
    use_basic_opponent_strategy: bool = True,
) -> tuple[bool, int]:
    """
    Simulates the current trick once and returns whether candidate_card wins
    plus the point value of the completed trick.
    """
    result = simulate_immediate_trick_once_detailed(
        state=state,
        candidate_card=candidate_card,
        left_hand_size=left_hand_size,
        right_hand_size=right_hand_size,
        random_generator=random_generator,
        use_basic_opponent_strategy=use_basic_opponent_strategy,
    )

    return bool(result["did_win"]), int(result["trick_points"])


def estimate_immediate_trick_value(
    state: GameState,
    candidate_card: str,
    left_hand_size: int,
    right_hand_size: int,
    sample_count: int,
    random_seed: int | None = None,
    use_basic_opponent_strategy: bool = True,
) -> dict[str, float]:
    """
    Estimates immediate trick value for one candidate card.

    Returned metrics:
    - win_rate: how often candidate_card wins the trick
    - average_trick_points: average total points in the trick
    - average_points_won: average points won by the player
    - average_points_lost: average points lost to opponents
    """
    if sample_count <= 0:
        raise ValueError("Sample count must be greater than zero.")

    rng = random.Random(random_seed) if random_seed is not None else random

    wins = 0
    total_trick_points = 0
    total_points_won = 0
    total_points_lost = 0

    for _ in range(sample_count):
        did_win, trick_points = simulate_immediate_trick_once_with_points(
            state=state,
            candidate_card=candidate_card,
            left_hand_size=left_hand_size,
            right_hand_size=right_hand_size,
            random_generator=rng,
            use_basic_opponent_strategy=use_basic_opponent_strategy,
        )

        total_trick_points += trick_points

        if did_win:
            wins += 1
            total_points_won += trick_points
        else:
            total_points_lost += trick_points

    return {
        "win_rate": wins / sample_count,
        "average_trick_points": total_trick_points / sample_count,
        "average_points_won": total_points_won / sample_count,
        "average_points_lost": total_points_lost / sample_count,
    }


def estimate_immediate_trick_values_for_legal_cards(
    state: GameState,
    left_hand_size: int,
    right_hand_size: int,
    sample_count: int,
    random_seed: int | None = None,
    use_basic_opponent_strategy: bool = True,
) -> dict[str, dict[str, float]]:
    """
    Estimates immediate trick value metrics for all legal cards in the current state.
    """
    legal_cards = get_legal_cards(
        hand=state.hand,
        current_trick=state.current_trick,
        game_type=state.game_type,
    )

    rng = random.Random(random_seed) if random_seed is not None else None

    return {
        card: estimate_immediate_trick_value(
            state=state,
            candidate_card=card,
            left_hand_size=left_hand_size,
            right_hand_size=right_hand_size,
            sample_count=sample_count,
            random_seed=rng.randint(0, 10**9) if rng is not None else None,
            use_basic_opponent_strategy=use_basic_opponent_strategy,
        )
        for card in legal_cards
    }


def simulate_immediate_trick_once_detailed(
    state: GameState,
    candidate_card: str,
    left_hand_size: int,
    right_hand_size: int,
    random_generator: random.Random | None = None,
    use_basic_opponent_strategy: bool = True,
) -> dict[str, Any]:
    """
    Simulates the current trick once and returns detailed information.

    Returned fields:
    - trick: the completed three-card trick
    - did_win: whether the candidate card won the trick
    - trick_points: total points in the trick
    - completed_trick: completed trick entry with cards and winner_role
    """
    rng = random_generator or random

    validate_candidate_card_for_current_trick(state, candidate_card)

    left_hand, right_hand = generate_random_opponent_hands(
        state=state,
        left_hand_size=left_hand_size,
        right_hand_size=right_hand_size,
        random_generator=rng,
    )

    trick = complete_trick_after_candidate_card(
        state=state,
        candidate_card=candidate_card,
        left_hand=left_hand,
        right_hand=right_hand,
        random_generator=rng,
        use_basic_opponent_strategy=use_basic_opponent_strategy,
    )

    winner_index = get_trick_winner(
        trick=trick,
        game_type=state.game_type,
    )

    candidate_index = len(state.current_trick)
    did_win = winner_index == candidate_index
    trick_points = get_trick_points(trick)

    completed_trick = build_completed_trick_from_state_and_candidate(
        state=state,
        completed_trick_cards=trick,
    )

    return {
        "trick": trick,
        "did_win": did_win,
        "trick_points": trick_points,
        "completed_trick": completed_trick,
    }