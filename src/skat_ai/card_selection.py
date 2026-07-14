from skat_ai.game_state import GameState
from skat_ai.objective_utility import (
    calculate_expected_point_swing as calculate_value_expected_point_swing,
)
from skat_ai.objective_utility import (
    choose_best_card_by_expected_objective,
)
from skat_ai.rules import get_card_points, get_legal_cards
from skat_ai.simulation import (
    DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT,
    estimate_immediate_trick_values_for_legal_cards,
)

VALID_CARD_SELECTION_POLICIES = [
    "first_legal",
    "lowest_point",
    "highest_point",
    "highest_expected_value",
]


def get_legal_cards_for_state(state: GameState) -> list[str]:
    """
    Returns all legal cards for the current state.
    """
    return get_legal_cards(
        hand=state.hand,
        current_trick=state.current_trick,
        game_type=state.game_type,
    )


def choose_first_legal_card(state: GameState) -> str:
    """
    Chooses the first legal card from the current state.
    """
    legal_cards = get_legal_cards_for_state(state)

    if not legal_cards:
        raise ValueError("No legal cards available.")

    return legal_cards[0]


def choose_lowest_point_card(state: GameState) -> str:
    """
    Chooses the legal card with the lowest point value.
    """
    legal_cards = get_legal_cards_for_state(state)

    if not legal_cards:
        raise ValueError("No legal cards available.")

    return min(legal_cards, key=get_card_points)


def choose_highest_point_card(state: GameState) -> str:
    """
    Chooses the legal card with the highest point value.
    """
    legal_cards = get_legal_cards_for_state(state)

    if not legal_cards:
        raise ValueError("No legal cards available.")

    return max(legal_cards, key=get_card_points)


def calculate_expected_point_swing(value: dict[str, float]) -> float:
    """
    Calculates expected point swing for one simulated card value.
    """
    return calculate_value_expected_point_swing(value)


def choose_highest_expected_value_card(
    state: GameState,
    left_hand_size: int,
    right_hand_size: int,
    sample_count: int,
    random_seed: int | None = None,
    use_basic_opponent_strategy: bool = True,
    opponent_response_policy_by_player: dict[str, str] | None = None,
) -> str:
    """
    Chooses the legal card with the highest estimated immediate expected point swing.
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
        raise ValueError("No legal cards available.")

    return choose_best_card_by_expected_objective(
        values=values,
        game_type=state.game_type,
        player_role=state.player_role,
    )


def choose_card_by_policy(
    state: GameState,
    policy: str,
    left_hand_size: int | None = None,
    right_hand_size: int | None = None,
    expected_value_sample_count: int = DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT,
    random_seed: int | None = None,
    use_basic_opponent_strategy: bool = True,
    opponent_response_policy_by_player: dict[str, str] | None = None,
) -> str:
    """
    Chooses a card using the given card-selection policy.
    """
    if policy == "first_legal":
        return choose_first_legal_card(state)

    if policy == "lowest_point":
        return choose_lowest_point_card(state)

    if policy == "highest_point":
        return choose_highest_point_card(state)

    if policy == "highest_expected_value":
        if left_hand_size is None or right_hand_size is None:
            raise ValueError(
                "left_hand_size and right_hand_size are required for highest_expected_value."
            )

        return choose_highest_expected_value_card(
            state=state,
            left_hand_size=left_hand_size,
            right_hand_size=right_hand_size,
            sample_count=expected_value_sample_count,
            random_seed=random_seed,
            use_basic_opponent_strategy=use_basic_opponent_strategy,
            opponent_response_policy_by_player=opponent_response_policy_by_player,
        )

    raise ValueError(f"Invalid card selection policy: {policy}")
