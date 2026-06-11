import random

from skat_ai.rules import get_card_points, get_legal_cards, is_trump

VALID_OPPONENT_CARD_POLICIES = [
    "lowest_point",
    "highest_point",
    "random_legal",
    "basic_trick_play",
    "basic_defender_response",
    "basic_defender_lead",
]

SUIT_BY_GAME_TYPE = {
    "clubs": "C",
    "spades": "S",
    "hearts": "H",
    "diamonds": "D",
}

JACK_TRUMP_ORDER = {
    "DJ": 0,
    "HJ": 1,
    "SJ": 2,
    "CJ": 3,
}

SUIT_GAME_RANK_ORDER = {
    "7": 0,
    "8": 1,
    "9": 2,
    "Q": 3,
    "K": 4,
    "10": 5,
    "A": 6,
}

NULL_GAME_RANK_ORDER = {
    "7": 0,
    "8": 1,
    "9": 2,
    "10": 3,
    "J": 4,
    "Q": 5,
    "K": 6,
    "A": 7,
}


def get_card_suit(card: str) -> str:
    """
    Returns the suit part of a compact card string.
    """
    return card[0]


def get_card_rank(card: str) -> str:
    """
    Returns the rank part of a compact card string.
    """
    return card[1:]


def is_trump_card(card: str, game_type: str) -> bool:
    """
    Returns whether a card is trump in the given game type.
    """
    if game_type == "null":
        return False

    if get_card_rank(card) == "J":
        return True

    if game_type == "grand":
        return False

    return get_card_suit(card) == SUIT_BY_GAME_TYPE.get(game_type)


def get_trick_order_value(card: str, game_type: str) -> int:
    """
    Returns an order value for comparing cards inside the same trick category.
    """
    if game_type == "null":
        return NULL_GAME_RANK_ORDER[get_card_rank(card)]

    if get_card_rank(card) == "J":
        return JACK_TRUMP_ORDER[card]

    return SUIT_GAME_RANK_ORDER[get_card_rank(card)]


def determine_current_trick_winner_index(
    cards: list[str],
    game_type: str,
) -> int:
    """
    Determines the current winner index for a partial or complete trick.
    """
    if not cards:
        raise ValueError("Cannot determine winner for an empty trick.")

    winning_index = 0
    winning_card = cards[0]
    lead_suit = get_card_suit(winning_card)
    lead_is_trump = is_trump_card(winning_card, game_type)

    for index, card in enumerate(cards[1:], start=1):
        card_is_trump = is_trump_card(card, game_type)
        winning_card_is_trump = is_trump_card(winning_card, game_type)

        if card_is_trump and not winning_card_is_trump:
            winning_index = index
            winning_card = card
            continue

        if not card_is_trump and winning_card_is_trump:
            continue

        if lead_is_trump:
            if not card_is_trump:
                continue
        elif get_card_suit(card) != lead_suit:
            continue

        if get_trick_order_value(card, game_type) > get_trick_order_value(
            winning_card,
            game_type,
        ):
            winning_index = index
            winning_card = card

    return winning_index


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

    return min(cards, key=get_card_points)


def choose_highest_point_card(cards: list[str]) -> str:
    """
    Chooses the highest-point card from a list of cards.
    """
    if not cards:
        raise ValueError("Cannot choose from an empty card list.")

    return max(cards, key=get_card_points)


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

    if winning_cards:
        return choose_lowest_point_card(winning_cards)

    return choose_lowest_point_card(legal_cards)


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

    if partner_currently_winning:
        partner_safe_cards = get_partner_safe_legal_cards(
            hand=hand,
            current_trick=current_trick,
            game_type=game_type,
            partner_index=0,
        )

        if partner_safe_cards:
            return choose_highest_point_card(partner_safe_cards)

        return choose_lowest_point_card(legal_cards)

    winning_cards = get_winning_legal_cards(
        hand=hand,
        current_trick=current_trick,
        game_type=game_type,
        player_index=player_index,
    )

    if winning_cards:
        return choose_basic_trick_play_card(
            hand=hand,
            current_trick=current_trick,
            game_type=game_type,
            player_index=player_index,
        )

    losing_cards = get_losing_legal_cards(
        hand=hand,
        current_trick=current_trick,
        game_type=game_type,
        player_index=player_index,
    )

    if losing_cards:
        return choose_lowest_point_card(losing_cards)

    return choose_basic_trick_play_card(
        hand=hand,
        current_trick=current_trick,
        game_type=game_type,
        player_index=player_index,
    )


def choose_basic_defender_lead_card(
    hand: list[str],
    game_type: str,
) -> str:
    """Chooses a basic defender lead card."""
    non_trump_cards = get_non_trump_cards(
        cards=hand,
        game_type=game_type,
    )

    if non_trump_cards:
        return choose_lowest_point_card(non_trump_cards)

    return choose_lowest_point_card(hand)


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
