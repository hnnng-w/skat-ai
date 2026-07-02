from skat_ai.game_history import get_all_played_cards
from skat_ai.game_state import GameState
from skat_ai.objective_utility import (
    calculate_expected_objective_utility,
    choose_best_card_by_expected_objective,
)
from skat_ai.rules import (
    SUIT_GAME_RANK_STRENGTH,
    get_card_points,
    get_card_strength,
    get_effective_suit,
    get_legal_cards,
    get_rank,
    get_suit,
    is_trump,
)
from skat_ai.simulation import (
    estimate_immediate_trick_values_for_legal_cards,
    estimate_immediate_trick_win_rates_for_legal_cards,
)


def get_higher_cards_in_same_suit(card: str, state: GameState) -> list[str]:
    """
    Returns all higher non-trump cards in the same printed suit.
    """
    if is_trump(card, state.game_type):
        return []

    card_suit = get_suit(card)
    card_rank = get_rank(card)
    card_strength = SUIT_GAME_RANK_STRENGTH[card_rank]

    suit_cards = [
        f"{card_suit}A",
        f"{card_suit}10",
        f"{card_suit}K",
        f"{card_suit}Q",
        f"{card_suit}9",
        f"{card_suit}8",
        f"{card_suit}7",
    ]

    return [
        possible_card
        for possible_card in suit_cards
        if SUIT_GAME_RANK_STRENGTH[get_rank(possible_card)] > card_strength
    ]


def classify_higher_cards(card: str, state: GameState) -> dict[str, list[str]]:
    """
    Classifies higher cards in the same suit.

    Categories:
    - played: higher cards that have already been played
    - in_hand: higher cards currently held by the player
    - unknown: higher cards that are neither played nor in the player's hand
    """
    higher_cards = get_higher_cards_in_same_suit(card, state)
    played_cards = get_all_played_cards(state)

    played = [
        higher_card for higher_card in higher_cards
        if higher_card in played_cards
    ]

    in_hand = [
        higher_card for higher_card in higher_cards
        if higher_card in state.hand
    ]

    unknown = [
        higher_card for higher_card in higher_cards
        if higher_card not in played_cards and higher_card not in state.hand
    ]

    return {
        "played": played,
        "in_hand": in_hand,
        "unknown": unknown,
    }


def is_highest_remaining_card_in_suit(card: str, state: GameState) -> bool:
    """
    Checks whether the given card has no unknown higher non-trump card in its suit.
    """
    if is_trump(card, state.game_type):
        return False

    classification = classify_higher_cards(card, state)

    return len(classification["unknown"]) == 0


def score_leading_card(card: str, state: GameState) -> int:
    """
    Scores a card when leading the trick.

    Higher score means the bot prefers this card.

    Current simple scoring:
    - Reward cards with no unknown higher card in the same suit.
    - Reward point value only if the card is safe.
    - Penalize trump cards slightly when leading.
    - Unsafe cards do not receive a point-value bonus.
    """
    score = 0

    if is_highest_remaining_card_in_suit(card, state):
        score += 100
        score += get_card_points(card)

    if is_trump(card, state.game_type):
        score -= 20

    return score


def choose_leading_card(state: GameState, legal_cards: list[str]) -> tuple[str, str]:
    """
    Chooses a card when the player is leading the trick.

    Basic leading strategy:
    - Score every legal card.
    - If at least one card has a positive score, play the card with the highest score.
    - If no card has a positive score, play the lowest-point legal card.
    """
    scored_cards = [(card, score_leading_card(card, state)) for card in legal_cards]

    best_card, best_score = max(scored_cards, key=lambda item: item[1])

    if best_score > 0:
        reason = (
            "You are leading the trick. The bot selected the legal card with the "
            f"highest leading score: {best_score}."
        )
        return best_card, reason

    recommended_card = min(legal_cards, key=get_card_points)
    reason = (
        "You are leading the trick and no safe high card was found, "
        "so the bot plays the lowest-point legal card."
    )
    return recommended_card, reason


def recommend_card_for_state(state: GameState) -> tuple[str, str]:
    """
    Recommends one legal card for the current game state.

    Basic strategy:
    - If leading the trick, use leading-card scoring.
    - If a legal card can currently win the trick, play the lowest-point winning card.
    - Otherwise, play the lowest-point legal card.
    """
    legal_cards = get_legal_cards(
        hand=state.hand,
        current_trick=state.current_trick,
        game_type=state.game_type,
    )

    if not legal_cards:
        raise ValueError("The hand must contain at least one legal card.")

    if not state.current_trick:
        return choose_leading_card(state, legal_cards)

    lead_effective_suit = get_effective_suit(state.current_trick[0], state.game_type)

    current_best_strength = max(
        get_card_strength(card, state.game_type, lead_effective_suit)
        for card in state.current_trick
    )

    winning_cards = [
        card
        for card in legal_cards
        if get_card_strength(card, state.game_type, lead_effective_suit) > current_best_strength
    ]

    if winning_cards:
        recommended_card = min(winning_cards, key=get_card_points)
        reason = "This card can currently win the trick while spending as few points as possible."
        return recommended_card, reason

    recommended_card = min(legal_cards, key=get_card_points)
    reason = (
        "No legal card can currently win the trick, so the bot plays the lowest-point legal card."
    )
    return recommended_card, reason


def recommend_card(hand: list[str], current_trick: list[str], game_type: str) -> tuple[str, str]:
    """
    Backward-compatible wrapper for earlier tests and demos.
    """
    state = GameState(
        game_type=game_type,
        player_role="unknown",
        hand=hand,
        current_trick=current_trick,
    )

    return recommend_card_for_state(state)


def recommend_card_by_simulation(
    state: GameState,
    left_hand_size: int,
    right_hand_size: int,
    sample_count: int,
    random_seed: int | None = None,
    use_basic_opponent_strategy: bool = True,
    opponent_response_policy_by_player: dict[str, str] | None = None,
) -> tuple[str, str, dict[str, float]]:
    """
    Recommends a card based on immediate trick win-rate simulation.

    Returns:
    - recommended card
    - reason
    - win rates for all legal cards
    """

    win_rates = estimate_immediate_trick_win_rates_for_legal_cards(
        state=state,
        left_hand_size=left_hand_size,
        right_hand_size=right_hand_size,
        sample_count=sample_count,
        random_seed=random_seed,
        use_basic_opponent_strategy=use_basic_opponent_strategy,
        opponent_response_policy_by_player=opponent_response_policy_by_player,
    )

    if not win_rates:
        raise ValueError("No legal cards available for simulation-based recommendation.")

    recommended_card = max(
        win_rates,
        key=lambda card: win_rates[card],
    )

    recommended_rate = win_rates[recommended_card]

    reason = (
        f"This card has the highest estimated immediate trick win rate: {recommended_rate:.3f}."
    )

    return recommended_card, reason, win_rates


def recommend_card_by_expected_value(
    state: GameState,
    left_hand_size: int,
    right_hand_size: int,
    sample_count: int,
    random_seed: int | None = None,
    use_basic_opponent_strategy: bool = True,
    opponent_response_policy_by_player: dict[str, str] | None = None,
) -> tuple[str, str, dict[str, dict[str, float]]]:
    """
    Recommends a card based on immediate expected point swing.

    Expected point swing:
    average_points_won - average_points_lost

    Returns:
    - recommended card
    - reason
    - value metrics for all legal cards
    """

    values = estimate_immediate_trick_values_for_legal_cards(
        state=state,
        left_hand_size=left_hand_size,
        right_hand_size=right_hand_size,
        sample_count=sample_count,
        random_seed=random_seed,
        use_basic_opponent_strategy=use_basic_opponent_strategy,
        opponent_response_policy_by_player=opponent_response_policy_by_player,
    )

    if not values:
        raise ValueError("No legal cards available for expected-value recommendation.")

    recommended_card = choose_best_card_by_expected_objective(
        values=values,
        game_type=state.game_type,
        player_role=state.player_role,
    )

    recommended_utility = calculate_expected_objective_utility(
        game_type=state.game_type,
        player_role=state.player_role,
        value=values[recommended_card],
    )

    if state.game_type == "null":
        reason = (
            "This card has the highest estimated Null contract-objective utility: "
            f"{recommended_utility:.3f}."
        )
        return recommended_card, reason, values

    recommended_swing = recommended_utility

    reason = (
        "This card has the highest estimated immediate expected point swing: "
        f"{recommended_swing:.2f}."
    )

    return recommended_card, reason, values
