CARD_POINTS = {
    "A": 11,
    "10": 10,
    "K": 4,
    "Q": 3,
    "J": 2,
    "9": 0,
    "8": 0,
    "7": 0,
}

SUIT_NAMES = {
    "C": "Clubs",
    "S": "Spades",
    "H": "Hearts",
    "D": "Diamonds",
}

RANK_NAMES = {
    "A": "Ace",
    "10": "Ten",
    "K": "King",
    "Q": "Queen",
    "J": "Jack",
    "9": "Nine",
    "8": "Eight",
    "7": "Seven",
}

GAME_TYPES = ["clubs", "spades", "hearts", "diamonds", "grand", "null"]

JACK_STRENGTH = {
    "CJ": 4,
    "SJ": 3,
    "HJ": 2,
    "DJ": 1,
}

SUIT_GAME_RANK_STRENGTH = {
    "A": 7,
    "10": 6,
    "K": 5,
    "Q": 4,
    "9": 3,
    "8": 2,
    "7": 1,
}

NULL_RANK_STRENGTH = {
    "A": 8,
    "K": 7,
    "Q": 6,
    "J": 5,
    "10": 4,
    "9": 3,
    "8": 2,
    "7": 1,
}


def get_suit(card: str) -> str:
    return card[0]


def get_rank(card: str) -> str:
    return card[1:]


def get_card_name(card: str) -> str:
    suit = get_suit(card)
    rank = get_rank(card)

    return f"{RANK_NAMES[rank]} of {SUIT_NAMES[suit]}"


def get_card_points(card: str) -> int:
    rank = get_rank(card)
    return CARD_POINTS[rank]


def is_jack(card: str) -> bool:
    return get_rank(card) == "J"


def get_trump_suit(game_type: str) -> str | None:
    if game_type == "clubs":
        return "C"
    if game_type == "spades":
        return "S"
    if game_type == "hearts":
        return "H"
    if game_type == "diamonds":
        return "D"
    if game_type in ["grand", "null"]:
        return None

    raise ValueError(f"Unknown game type: {game_type}")


def is_trump(card: str, game_type: str) -> bool:
    if game_type == "null":
        return False

    if game_type == "grand":
        return is_jack(card)

    trump_suit = get_trump_suit(game_type)

    return is_jack(card) or get_suit(card) == trump_suit


def get_effective_suit(card: str, game_type: str) -> str:
    """
    Returns the suit that must be followed.

    In suit games and grand:
    - Jacks are trump.
    - In suit games, cards of the trump suit are also trump.

    In null games:
    - There is no trump.
    - Jacks belong to their printed suit.
    """
    if is_trump(card, game_type):
        return "TRUMP"

    return get_suit(card)


def get_legal_cards(hand: list[str], current_trick: list[str], game_type: str) -> list[str]:
    """
    Returns all cards that can legally be played.

    If the player leads the trick, every card in hand is legal.
    Otherwise, the player must follow the effective suit of the first card
    if possible. If not possible, every card is legal.
    """
    if not current_trick:
        return hand

    lead_card = current_trick[0]
    required_suit = get_effective_suit(lead_card, game_type)

    matching_cards = [card for card in hand if get_effective_suit(card, game_type) == required_suit]

    if matching_cards:
        return matching_cards

    return hand


def get_card_strength(card: str, game_type: str, lead_effective_suit: str) -> int:
    """
    Returns an internal comparable strength value for a card within a trick.

    Higher values mean stronger cards for trick-winning comparison.
    These values are not Skat card points and must not be used for scoring.

    Cards that cannot win the trick because they do not follow the required
    effective suit receive 0.

    The numeric ranges are intentionally separated:
    - Jacks/trumps receive high internal values.
    - Suit-following non-trump cards receive lower internal values.
    - Off-suit cards receive 0.
    """
    if game_type == "null":
        if get_effective_suit(card, game_type) != lead_effective_suit:
            return 0

        return NULL_RANK_STRENGTH[get_rank(card)]

    if is_trump(card, game_type):
        if is_jack(card):
            return 100 + JACK_STRENGTH[card]

        return 50 + SUIT_GAME_RANK_STRENGTH[get_rank(card)]

    if lead_effective_suit == "TRUMP":
        return 0

    if get_effective_suit(card, game_type) != lead_effective_suit:
        return 0

    return SUIT_GAME_RANK_STRENGTH[get_rank(card)]


def get_trick_winner(trick: list[str], game_type: str) -> int:
    """
    Returns the index of the winning card in the trick.

    Example:
    trick = ["S10", "SA", "S7"]
    result = 1 because "SA" wins.
    """
    if len(trick) != 3:
        raise ValueError("A completed trick must contain exactly 3 cards.")

    lead_effective_suit = get_effective_suit(trick[0], game_type)

    strengths = [get_card_strength(card, game_type, lead_effective_suit) for card in trick]

    return strengths.index(max(strengths))


def get_trick_points(trick: list[str]) -> int:
    return sum(get_card_points(card) for card in trick)
