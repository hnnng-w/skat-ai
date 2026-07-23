import random

from skat_ai.rules import (
    get_card_points,
    get_card_strength,
    get_effective_suit,
    get_legal_cards,
    is_trump,
)

VALID_OPPONENT_CARD_POLICIES = [
    "lowest_point",
    "highest_point",
    "random_legal",
    "basic_trick_play",
    "basic_defender_response",
    "basic_defender_lead",
]


def determine_current_trick_winner_index(
    cards: list[str],
    game_type: str,
) -> int:
    """
    Determines the current winner index for a partial or complete trick.
    """
    if not cards:
        raise ValueError("Cannot determine winner for an empty trick.")

    lead_effective_suit = get_effective_suit(cards[0], game_type)
    strengths = [
        get_card_strength(card, game_type, lead_effective_suit)
        for card in cards
    ]

    return strengths.index(max(strengths))


def validate_opponent_card_policy(policy: str) -> None:
    """
    Validates an opponent card-selection policy.
    """
    if policy not in VALID_OPPONENT_CARD_POLICIES:
        raise ValueError(f"Invalid opponent card policy: {policy}")


def choose_lowest_point_card(cards: list[str]) -> str:
    """
    Chooses the lowest-point card from a list of cards.
    """
    if not cards:
        raise ValueError("Cannot choose from an empty card list.")

    return _cards_with_extreme_points(cards, highest=False)[0]


def choose_highest_point_card(cards: list[str]) -> str:
    """
    Chooses the highest-point card from a list of cards.
    """
    if not cards:
        raise ValueError("Cannot choose from an empty card list.")

    return _cards_with_extreme_points(cards, highest=True)[0]


def _cards_with_extreme_points(cards: list[str], *, highest: bool) -> list[str]:
    if not cards:
        raise ValueError("Cannot choose from an empty card list.")
    point_value = (max if highest else min)(get_card_points(card) for card in cards)
    return [card for card in cards if get_card_points(card) == point_value]


def choose_random_card(
    cards: list[str],
    random_generator: random.Random | None = None,
) -> str:
    """
    Chooses a random card from a list of cards.
    """
    if not cards:
        raise ValueError("Cannot choose from an empty card list.")

    rng = random_generator or random

    return rng.choice(cards)


def get_winning_legal_cards(
    hand: list[str],
    current_trick: list[str],
    game_type: str,
    player_index: int,
) -> list[str]:
    """
    Returns legal cards that would currently win the trick.

    player_index is the index of the opponent card within the completed trick
    after the candidate card is added.
    """
    legal_cards = get_legal_cards(
        hand=hand,
        current_trick=current_trick,
        game_type=game_type,
    )

    winning_cards = []

    for card in legal_cards:
        trick = [*current_trick, card]
        winner_index = determine_current_trick_winner_index(
            cards=trick,
            game_type=game_type,
        )

        if winner_index == player_index:
            winning_cards.append(card)

    return winning_cards


def choose_basic_trick_play_card(
    hand: list[str],
    current_trick: list[str],
    game_type: str,
    player_index: int,
) -> str:
    """
    Chooses a basic opponent response card.

    If the opponent can currently win the trick, play the lowest-point winning card.
    Otherwise, play the lowest-point legal card.
    """
    legal_cards = get_legal_cards(
        hand=hand,
        current_trick=current_trick,
        game_type=game_type,
    )

    if not legal_cards:
        raise ValueError("Opponent has no legal cards.")

    winning_cards = get_winning_legal_cards(
        hand=hand,
        current_trick=current_trick,
        game_type=game_type,
        player_index=player_index,
    )

    return _get_basic_trick_play_preferred_cards(
        legal_cards=legal_cards,
        winning_cards=winning_cards,
    )[0]


def _get_basic_trick_play_preferred_cards(
    *,
    legal_cards: list[str],
    winning_cards: list[str],
) -> list[str]:
    return _cards_with_extreme_points(
        winning_cards if winning_cards else legal_cards,
        highest=False,
    )


def choose_basic_defender_response_card(
    hand: list[str],
    current_trick: list[str],
    game_type: str,
    player_index: int,
    partner_currently_winning: bool,
) -> str:
    """Chooses a basic cooperative defender response card."""
    legal_cards = get_legal_cards(
        hand=hand,
        current_trick=current_trick,
        game_type=game_type,
    )

    return _get_basic_defender_response_preferred_cards(
        hand=hand,
        current_trick=current_trick,
        game_type=game_type,
        player_index=player_index,
        partner_currently_winning=partner_currently_winning,
        legal_cards=legal_cards,
    )[0]


def _cards_with_weakest_trick_strength(
    cards: list[str],
    current_trick: list[str],
    game_type: str,
) -> list[str]:
    lead_effective_suit = get_effective_suit(current_trick[0], game_type)
    weakest_strength = min(
        get_card_strength(card, game_type, lead_effective_suit) for card in cards
    )
    return [
        card
        for card in cards
        if get_card_strength(card, game_type, lead_effective_suit) == weakest_strength
    ]


def _get_basic_defender_response_preferred_cards(
    *,
    hand: list[str],
    current_trick: list[str],
    game_type: str,
    player_index: int,
    partner_currently_winning: bool,
    legal_cards: list[str],
) -> list[str]:
    if partner_currently_winning:
        partner_safe_cards = get_partner_safe_legal_cards(
            hand=hand,
            current_trick=current_trick,
            game_type=game_type,
            partner_index=0,
        )

        if partner_safe_cards:
            return _cards_with_weakest_trick_strength(
                _cards_with_extreme_points(partner_safe_cards, highest=True),
                current_trick,
                game_type,
            )

        return _cards_with_weakest_trick_strength(
            _cards_with_extreme_points(legal_cards, highest=False),
            current_trick,
            game_type,
        )

    winning_cards = get_winning_legal_cards(
        hand=hand,
        current_trick=current_trick,
        game_type=game_type,
        player_index=player_index,
    )

    if winning_cards:
        losing_cards = get_losing_legal_cards(
            hand=hand,
            current_trick=current_trick,
            game_type=game_type,
            player_index=player_index,
        )

        if (
            len(current_trick) == 1
            and get_card_points(current_trick[0]) == 0
            and not is_trump(current_trick[0], game_type)
            and all(is_trump(card, game_type) for card in winning_cards)
            and losing_cards
        ):
            return _cards_with_extreme_points(losing_cards, highest=False)

        return _cards_with_weakest_trick_strength(
            _cards_with_extreme_points(winning_cards, highest=False),
            current_trick,
            game_type,
        )

    losing_cards = get_losing_legal_cards(
        hand=hand,
        current_trick=current_trick,
        game_type=game_type,
        player_index=player_index,
    )

    if losing_cards:
        return _cards_with_extreme_points(losing_cards, highest=False)

    return _get_basic_trick_play_preferred_cards(
        legal_cards=legal_cards,
        winning_cards=winning_cards,
    )


def choose_basic_defender_lead_card(
    hand: list[str],
    game_type: str,
) -> str:
    """Chooses a basic defender lead card."""
    return _get_basic_defender_lead_preferred_cards(hand, game_type)[0]


def _get_basic_defender_lead_preferred_cards(
    hand: list[str],
    game_type: str,
) -> list[str]:
    non_trump_cards = get_non_trump_cards(cards=hand, game_type=game_type)
    return _cards_with_extreme_points(
        non_trump_cards if non_trump_cards else hand,
        highest=False,
    )


def get_preferred_opponent_cards_by_policy(
    hand: list[str],
    current_trick: list[str],
    game_type: str,
    player_index: int,
    policy: str,
    partner_currently_winning: bool = False,
) -> list[str]:
    """Returns equally preferred deterministic policy cards in legal-hand order."""
    validate_opponent_card_policy(policy)
    if policy == "random_legal":
        raise ValueError("random_legal has no deterministic preferred-card set.")

    legal_cards = get_legal_cards(
        hand=hand,
        current_trick=current_trick,
        game_type=game_type,
    )
    if not legal_cards:
        raise ValueError("Opponent has no legal cards.")

    if not current_trick:
        if policy == "highest_point":
            return _cards_with_extreme_points(legal_cards, highest=True)
        if policy == "basic_defender_lead":
            return _get_basic_defender_lead_preferred_cards(legal_cards, game_type)
        return _cards_with_extreme_points(legal_cards, highest=False)

    if policy == "lowest_point":
        return _cards_with_extreme_points(legal_cards, highest=False)
    if policy == "highest_point":
        return _cards_with_extreme_points(legal_cards, highest=True)

    winning_cards = get_winning_legal_cards(
        hand=hand,
        current_trick=current_trick,
        game_type=game_type,
        player_index=player_index,
    )
    if policy == "basic_defender_response":
        return _get_basic_defender_response_preferred_cards(
            hand=hand,
            current_trick=current_trick,
            game_type=game_type,
            player_index=player_index,
            partner_currently_winning=partner_currently_winning,
            legal_cards=legal_cards,
        )
    return _get_basic_trick_play_preferred_cards(
        legal_cards=legal_cards,
        winning_cards=winning_cards,
    )


def choose_opponent_lead_card_by_policy(
    hand: list[str],
    policy: str = "lowest_point",
    random_generator: random.Random | None = None,
    game_type: str = "grand",
) -> str:
    """
    Chooses an opponent lead card by policy.

    For leading a trick, basic_trick_play currently behaves like lowest_point.
    """
    validate_opponent_card_policy(policy)

    if policy in ["lowest_point", "basic_trick_play", "basic_defender_response"]:
        return choose_lowest_point_card(hand)

    if policy == "basic_defender_lead":
        return choose_basic_defender_lead_card(
            hand=hand,
            game_type=game_type,
        )

    if policy == "highest_point":
        return choose_highest_point_card(hand)

    if policy == "random_legal":
        return choose_random_card(
            cards=hand,
            random_generator=random_generator,
        )

    raise ValueError(f"Invalid opponent card policy: {policy}")


def choose_opponent_response_card_by_policy(
    hand: list[str],
    current_trick: list[str],
    game_type: str,
    player_index: int,
    policy: str = "basic_trick_play",
    random_generator: random.Random | None = None,
    partner_currently_winning: bool = False,
) -> str:
    """
    Chooses an opponent response card by policy.
    """
    validate_opponent_card_policy(policy)

    legal_cards = get_legal_cards(
        hand=hand,
        current_trick=current_trick,
        game_type=game_type,
    )

    if not legal_cards:
        raise ValueError("Opponent has no legal cards.")

    if policy == "lowest_point":
        return choose_lowest_point_card(legal_cards)

    if policy == "highest_point":
        return choose_highest_point_card(legal_cards)

    if policy == "random_legal":
        return choose_random_card(
            cards=legal_cards,
            random_generator=random_generator,
        )

    if policy == "basic_trick_play":
        return choose_basic_trick_play_card(
            hand=hand,
            current_trick=current_trick,
            game_type=game_type,
            player_index=player_index,
        )
    
    if policy == "basic_defender_response":
        return choose_basic_defender_response_card(
            hand=hand,
            current_trick=current_trick,
            game_type=game_type,
            player_index=player_index,
            partner_currently_winning=partner_currently_winning,
        )
    
    if policy == "basic_defender_lead":
        return choose_basic_trick_play_card(
            hand=hand,
            current_trick=current_trick,
            game_type=game_type,
            player_index=player_index,
        )

    raise ValueError(f"Invalid opponent card policy: {policy}")

def get_opponent_policy_settings_for_player(
    player: str,
    opponent_policy_settings: dict[str, str],
    left_opponent_policy_settings: dict[str, str] | None = None,
    right_opponent_policy_settings: dict[str, str] | None = None,
) -> dict[str, str]:
    """
    Returns opponent policy settings for a specific opponent player.

    Falls back to global opponent policy settings when no specific settings
    are available.
    """
    if player == "left" and left_opponent_policy_settings is not None:
        return left_opponent_policy_settings

    if player == "right" and right_opponent_policy_settings is not None:
        return right_opponent_policy_settings

    return opponent_policy_settings


def get_partner_safe_legal_cards(
    hand: list[str],
    current_trick: list[str],
    game_type: str,
    partner_index: int,
) -> list[str]:
    """Returns legal cards that keep the defender's partner winning the trick."""
    legal_cards = get_legal_cards(
        hand=hand,
        current_trick=current_trick,
        game_type=game_type,
    )

    partner_safe_cards = []

    for card in legal_cards:
        trick = [*current_trick, card]
        winner_index = determine_current_trick_winner_index(
            cards=trick,
            game_type=game_type,
        )

        if winner_index == partner_index:
            partner_safe_cards.append(card)

    return partner_safe_cards


def get_losing_legal_cards(
    hand: list[str],
    current_trick: list[str],
    game_type: str,
    player_index: int,
) -> list[str]:
    """Returns legal cards that do not make the player win the current trick."""
    legal_cards = get_legal_cards(
        hand=hand,
        current_trick=current_trick,
        game_type=game_type,
    )

    losing_cards = []

    for card in legal_cards:
        trick = [*current_trick, card]
        winner_index = determine_current_trick_winner_index(
            cards=trick,
            game_type=game_type,
        )

        if winner_index != player_index:
            losing_cards.append(card)

    return losing_cards


def get_non_trump_cards(cards: list[str], game_type: str) -> list[str]:
    """Returns all cards that are not trump cards for the given game type."""
    return [card for card in cards if not is_trump(card, game_type)]
