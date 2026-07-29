import random
from dataclasses import dataclass
from typing import Any

from skat_ai.card_tracking import get_unseen_cards
from skat_ai.game_history import (
    build_completed_trick_from_state_and_candidate,
    get_compatible_declarer_player,
    get_players_for_trick_leader,
)
from skat_ai.game_state import GameState
from skat_ai.objective_utility import calculate_null_trick_objective_utility
from skat_ai.opponent_policy import choose_opponent_response_card_by_policy
from skat_ai.public_hand_constraint import DECLARED_OUVERT_SOURCE, PublicHandConstraint
from skat_ai.rules import (
    get_card_points,
    get_card_strength,
    get_effective_suit,
    get_legal_cards,
    get_trick_points,
    get_trick_winner,
)
from skat_ai.sampling_validation import validate_enough_cards_for_opponent_sampling
from skat_ai.side_ownership import (
    did_local_side_win,
    did_local_side_win_for_winner_role,
    normalize_declarer_player,
)

DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT = 100


@dataclass(frozen=True)
class SampledHiddenState:
    left_hand: list[str]
    right_hand: list[str]
    hypothetical_skat: list[str]


def generate_sampled_hidden_state(
    state: GameState,
    left_hand_size: int,
    right_hand_size: int,
    random_generator: random.Random | None = None,
    public_hand_constraints: tuple[PublicHandConstraint, ...] = (),
) -> SampledHiddenState:
    """Generates one coherent local-perspective hidden-card sample."""
    validate_enough_cards_for_opponent_sampling(
        state=state,
        left_hand_size=left_hand_size,
        right_hand_size=right_hand_size,
    )

    rng = random_generator or random
    unseen_cards = get_unseen_cards(state)
    required_card_count = left_hand_size + right_hand_size

    if required_card_count > len(unseen_cards):
        raise ValueError("Requested more opponent cards than unseen cards available.")

    if not public_hand_constraints:
        shuffled_cards = unseen_cards.copy()
        rng.shuffle(shuffled_cards)
        return SampledHiddenState(
            left_hand=shuffled_cards[:left_hand_size],
            right_hand=shuffled_cards[left_hand_size:required_card_count],
            hypothetical_skat=shuffled_cards[required_card_count:],
        )

    constraints_by_player: dict[str, PublicHandConstraint] = {}
    constrained_cards: set[str] = set()
    for constraint in public_hand_constraints:
        if constraint.player in constraints_by_player:
            raise ValueError(f"Duplicate public hand constraint for {constraint.player}.")
        constraints_by_player[constraint.player] = constraint
        if len(set(constraint.cards)) != len(constraint.cards):
            raise ValueError("Public hand constraints must contain unique cards.")
        duplicates = constrained_cards.intersection(constraint.cards)
        if duplicates:
            raise ValueError(
                f"Public hand constraints assign cards more than once: {sorted(duplicates)}"
            )
        constrained_cards.update(constraint.cards)

    local_constraint = constraints_by_player.get("me")
    if local_constraint is not None and set(local_constraint.cards) != set(state.hand):
        raise ValueError("The local public hand constraint must exactly match state.hand.")

    for player, hand_size in (("left", left_hand_size), ("right", right_hand_size)):
        constraint = constraints_by_player.get(player)
        if constraint is None:
            continue
        if len(constraint.cards) != hand_size:
            raise ValueError(
                f"The exact public {player} hand has {len(constraint.cards)} cards, "
                f"but the required hand size is {hand_size}."
            )
        unavailable = sorted(set(constraint.cards) - set(unseen_cards))
        if unavailable:
            raise ValueError(
                f"Public {player} hand cards are unavailable for sampling: {unavailable}"
            )

    opponent_constrained_cards = {
        card
        for player, constraint in constraints_by_player.items()
        if player in {"left", "right"}
        for card in constraint.cards
    }
    shuffled_cards = [
        card for card in unseen_cards if card not in opponent_constrained_cards
    ]
    rng.shuffle(shuffled_cards)
    offset = 0
    left_constraint = constraints_by_player.get("left")
    if left_constraint is None:
        left_hand = shuffled_cards[offset : offset + left_hand_size]
        offset += left_hand_size
    else:
        left_hand = list(left_constraint.cards)
    right_constraint = constraints_by_player.get("right")
    if right_constraint is None:
        right_hand = shuffled_cards[offset : offset + right_hand_size]
        offset += right_hand_size
    else:
        right_hand = list(right_constraint.cards)
    hypothetical_skat = shuffled_cards[offset:]

    return SampledHiddenState(
        left_hand=left_hand,
        right_hand=right_hand,
        hypothetical_skat=hypothetical_skat,
    )


def generate_random_opponent_hands(
    state: GameState,
    left_hand_size: int,
    right_hand_size: int,
    random_generator: random.Random | None = None,
    public_hand_constraints: tuple[PublicHandConstraint, ...] = (),
) -> tuple[list[str], list[str]]:
    """
    Generates random opponent hands from unseen cards.
    """
    sample = generate_sampled_hidden_state(
        state=state,
        left_hand_size=left_hand_size,
        right_hand_size=right_hand_size,
        random_generator=random_generator,
        public_hand_constraints=public_hand_constraints,
    )

    return sample.left_hand, sample.right_hand


def generate_multiple_random_opponent_hands(
    state: GameState,
    left_hand_size: int,
    right_hand_size: int,
    sample_count: int,
    random_seed: int | None = None,
    public_hand_constraints: tuple[PublicHandConstraint, ...] = (),
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
            public_hand_constraints=public_hand_constraints,
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
    opponent_response_policy_by_player: dict[str, str] | None = None,
) -> list[str]:
    """
    Completes the current trick after the player plays candidate_card.

    Assumptions:
    - If current_trick has 0 cards, the player leads and both opponents play.
    - If current_trick has 1 card, the player plays second and one opponent plays after.
    - If current_trick has 2 cards, the player plays third and the trick is complete.
    """
    rng = random_generator or random

    def choose_and_remove_opponent_card(
        hand: list[str],
        current_trick: list[str],
        player: str | None,
    ) -> str:
        if (
            player is not None
            and opponent_response_policy_by_player is not None
            and player in opponent_response_policy_by_player
        ):
            selected_card = choose_opponent_response_card_by_policy(
                hand=hand,
                current_trick=current_trick,
                game_type=state.game_type,
                player_index=len(current_trick),
                policy=opponent_response_policy_by_player[player],
                random_generator=rng,
            )
        elif use_basic_opponent_strategy:
            selected_card = choose_basic_opponent_card(
                hand=hand,
                current_trick=current_trick,
                game_type=state.game_type,
            )
        else:
            selected_card = choose_random_legal_card(
                hand=hand,
                current_trick=current_trick,
                game_type=state.game_type,
                random_generator=rng,
            )

        hand.remove(selected_card)
        return selected_card

    trick = state.current_trick.copy()
    trick.append(candidate_card)

    if len(trick) == 1:
        left_card = choose_and_remove_opponent_card(
            hand=left_hand,
            current_trick=trick,
            player="left",
        )

        trick.append(left_card)

        right_card = choose_and_remove_opponent_card(
            hand=right_hand,
            current_trick=trick,
            player="right",
        )

        trick.append(right_card)

    elif len(trick) == 2:
        third_hand = right_hand
        third_player = None

        if state.trick_leader != "unknown":
            trick_players = get_players_for_trick_leader(state.trick_leader)

            if trick_players[1] == "me":
                third_player = trick_players[2]

                if third_player == "left":
                    third_hand = left_hand
                elif third_player == "right":
                    third_hand = right_hand
                else:
                    raise ValueError(f"Invalid third opponent player: {third_player}")

        # Legacy one-card states without a usable leader keep the old fallback.
        third_card = choose_and_remove_opponent_card(
            hand=third_hand,
            current_trick=trick,
            player=third_player,
        )

        trick.append(third_card)

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
    opponent_response_policy_by_player: dict[str, str] | None = None,
    public_hand_constraints: tuple[PublicHandConstraint, ...] = (),
) -> bool:
    """
    Simulates the current trick once after the player plays candidate_card.

    Returns True if the local player's side wins the completed trick.
    """
    result = simulate_immediate_trick_once_detailed(
        state=state,
        candidate_card=candidate_card,
        left_hand_size=left_hand_size,
        right_hand_size=right_hand_size,
        random_generator=random_generator,
        use_basic_opponent_strategy=use_basic_opponent_strategy,
        opponent_response_policy_by_player=opponent_response_policy_by_player,
        public_hand_constraints=public_hand_constraints,
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
    opponent_response_policy_by_player: dict[str, str] | None = None,
    public_hand_constraints: tuple[PublicHandConstraint, ...] = (),
) -> float:
    """
    Estimates how often the local player's side wins the current trick.
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
            opponent_response_policy_by_player=opponent_response_policy_by_player,
            public_hand_constraints=public_hand_constraints,
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
    opponent_response_policy_by_player: dict[str, str] | None = None,
    public_hand_constraints: tuple[PublicHandConstraint, ...] = (),
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
    use_common_seed = any(
        constraint.source == DECLARED_OUVERT_SOURCE
        for constraint in public_hand_constraints
    )

    return {
        card: estimate_immediate_trick_win_rate(
            state=state,
            candidate_card=card,
            left_hand_size=left_hand_size,
            right_hand_size=right_hand_size,
            sample_count=sample_count,
            random_seed=(
                random_seed
                if use_common_seed
                else rng.randint(0, 10**9) if rng is not None else None
            ),
            use_basic_opponent_strategy=use_basic_opponent_strategy,
            opponent_response_policy_by_player=opponent_response_policy_by_player,
            public_hand_constraints=public_hand_constraints,
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
    opponent_response_policy_by_player: dict[str, str] | None = None,
    public_hand_constraints: tuple[PublicHandConstraint, ...] = (),
) -> tuple[bool, int]:
    """
    Simulates the current trick once and returns whether the local player's
    side wins plus the point value of the completed trick.
    """
    result = simulate_immediate_trick_once_detailed(
        state=state,
        candidate_card=candidate_card,
        left_hand_size=left_hand_size,
        right_hand_size=right_hand_size,
        random_generator=random_generator,
        use_basic_opponent_strategy=use_basic_opponent_strategy,
        opponent_response_policy_by_player=opponent_response_policy_by_player,
        public_hand_constraints=public_hand_constraints,
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
    opponent_response_policy_by_player: dict[str, str] | None = None,
    public_hand_constraints: tuple[PublicHandConstraint, ...] = (),
) -> dict[str, float]:
    """
    Estimates immediate trick value for one candidate card.

    Returned metrics:
    - win_rate: how often the local player's side wins the trick
    - average_trick_points: average total points in the trick
    - average_points_won: average points won by the local player's side
    - average_points_lost: average points lost to the other side
    """
    if sample_count <= 0:
        raise ValueError("Sample count must be greater than zero.")

    rng = random.Random(random_seed) if random_seed is not None else random

    wins = 0
    total_trick_points = 0
    total_points_won = 0
    total_points_lost = 0
    total_objective_utility = 0.0

    for _ in range(sample_count):
        detailed_result = simulate_immediate_trick_once_detailed(
            state=state,
            candidate_card=candidate_card,
            left_hand_size=left_hand_size,
            right_hand_size=right_hand_size,
            random_generator=rng,
            use_basic_opponent_strategy=use_basic_opponent_strategy,
            opponent_response_policy_by_player=opponent_response_policy_by_player,
            public_hand_constraints=public_hand_constraints,
        )
        did_win = bool(detailed_result["did_win"])
        trick_points = int(detailed_result["trick_points"])

        total_trick_points += trick_points

        if did_win:
            wins += 1
            total_points_won += trick_points
        else:
            total_points_lost += trick_points

        if state.game_type == "null":
            total_objective_utility += calculate_null_trick_objective_utility(
                player_role=state.player_role,
                winner_role=str(detailed_result["completed_trick"]["winner_role"]),
            )

    value = {
        "win_rate": wins / sample_count,
        "average_trick_points": total_trick_points / sample_count,
        "average_points_won": total_points_won / sample_count,
        "average_points_lost": total_points_lost / sample_count,
    }

    if state.game_type == "null":
        value["expected_objective_utility"] = total_objective_utility / sample_count

    return value


def estimate_immediate_trick_values_for_legal_cards(
    state: GameState,
    left_hand_size: int,
    right_hand_size: int,
    sample_count: int,
    random_seed: int | None = None,
    use_basic_opponent_strategy: bool = True,
    opponent_response_policy_by_player: dict[str, str] | None = None,
    public_hand_constraints: tuple[PublicHandConstraint, ...] = (),
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
    use_common_seed = any(
        constraint.source == DECLARED_OUVERT_SOURCE
        for constraint in public_hand_constraints
    )

    return {
        card: estimate_immediate_trick_value(
            state=state,
            candidate_card=card,
            left_hand_size=left_hand_size,
            right_hand_size=right_hand_size,
            sample_count=sample_count,
            random_seed=(
                random_seed
                if use_common_seed
                else rng.randint(0, 10**9) if rng is not None else None
            ),
            use_basic_opponent_strategy=use_basic_opponent_strategy,
            opponent_response_policy_by_player=opponent_response_policy_by_player,
            public_hand_constraints=public_hand_constraints,
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
    opponent_response_policy_by_player: dict[str, str] | None = None,
    public_hand_constraints: tuple[PublicHandConstraint, ...] = (),
) -> dict[str, Any]:
    """
    Simulates the current trick once and returns detailed information.

    Returned fields:
    - trick: the completed three-card trick
    - did_win: whether the local player's side won the trick
    - candidate_card_won: whether the candidate card won the trick
    - local_side_won: whether the local player's side won the trick
    - trick_points: total points in the trick
    - completed_trick: completed trick entry with cards and winner_role
    """
    rng = random_generator or random

    validate_candidate_card_for_current_trick(state, candidate_card)

    sampling_kwargs: dict[str, Any] = {}
    if public_hand_constraints:
        sampling_kwargs["public_hand_constraints"] = public_hand_constraints
    left_hand, right_hand = generate_random_opponent_hands(
        state=state,
        left_hand_size=left_hand_size,
        right_hand_size=right_hand_size,
        random_generator=rng,
        **sampling_kwargs,
    )

    trick = complete_trick_after_candidate_card(
        state=state,
        candidate_card=candidate_card,
        left_hand=left_hand,
        right_hand=right_hand,
        random_generator=rng,
        use_basic_opponent_strategy=use_basic_opponent_strategy,
        opponent_response_policy_by_player=opponent_response_policy_by_player,
    )

    winner_index = get_trick_winner(
        trick=trick,
        game_type=state.game_type,
    )

    candidate_index = len(state.current_trick)
    candidate_card_won = winner_index == candidate_index
    trick_points = get_trick_points(trick)

    completed_trick = build_completed_trick_from_state_and_candidate(
        state=state,
        completed_trick_cards=trick,
    )

    normalized_declarer_player = normalize_declarer_player(
        player_role=state.player_role,
        declarer_player=get_compatible_declarer_player(
            player_role=state.player_role,
            declarer_player=state.declarer_player,
        ),
    )
    if completed_trick["winner_player"] == "unknown":
        local_side_won = did_local_side_win_for_winner_role(
            winner_role=completed_trick["winner_role"],
            player_role=state.player_role,
        )
    else:
        local_side_won = did_local_side_win(
            winner_player=completed_trick["winner_player"],
            player_role=state.player_role,
            declarer_player=normalized_declarer_player,
        )

    return {
        "trick": trick,
        "did_win": local_side_won,
        "candidate_card_won": candidate_card_won,
        "local_side_won": local_side_won,
        "trick_points": trick_points,
        "completed_trick": completed_trick,
    }
