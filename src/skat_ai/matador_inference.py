from skat_ai.rules import get_trump_suit

SUIT_GAME_RANK_ORDER = ["A", "10", "K", "Q", "9", "8", "7"]
JACK_ORDER = ["CJ", "SJ", "HJ", "DJ"]
OWNERSHIP_OWNED = "owned"
OWNERSHIP_NOT_OWNED = "not_owned"
OWNERSHIP_UNKNOWN = "unknown"
VALID_COMPLETED_TRICK_PLAYER_ORDERS = [
    ["me", "left", "right"],
    ["left", "right", "me"],
    ["right", "me", "left"],
]
SUIT_TO_PREFIX = {
    "clubs": "C",
    "spades": "S",
    "hearts": "H",
    "diamonds": "D",
}


def get_trump_order_for_matadors(game_type: str) -> list[str]:
    """Returns the ordered trump sequence used for matador inference."""
    if game_type == "null":
        return []

    if game_type == "grand":
        return JACK_ORDER.copy()

    trump_suit = get_trump_suit(game_type)
    if trump_suit is None:
        raise ValueError(f"Unsupported game type for matador inference: {game_type}")

    suit_trumps = [f"{trump_suit}{rank}" for rank in SUIT_GAME_RANK_ORDER]

    return [*JACK_ORDER, *suit_trumps]


def infer_matadors_from_declarer_cards(
    game_type: str,
    declarer_cards: list[str],
) -> int | None:
    """Infers matador count from known declarer cards.

    Returns None for null games or when no declarer cards are available.
    """
    trump_order = get_trump_order_for_matadors(game_type)

    if not trump_order:
        return None

    if not declarer_cards:
        return None

    declarer_card_set = set(declarer_cards)
    has_top_trump = trump_order[0] in declarer_card_set
    matadors = 0

    for trump_card in trump_order:
        owns_card = trump_card in declarer_card_set

        if has_top_trump:
            if owns_card:
                matadors += 1
                continue
            break

        if not owns_card:
            matadors += 1
            continue

        break

    return matadors


def get_matador_ownership_state(
    card: str,
    declarer_owned_cards: set[str],
    non_declarer_owned_cards: set[str],
) -> str | None:
    """Returns the known declarer ownership state for one card."""
    if card in declarer_owned_cards and card in non_declarer_owned_cards:
        return None

    if card in declarer_owned_cards:
        return OWNERSHIP_OWNED

    if card in non_declarer_owned_cards:
        return OWNERSHIP_NOT_OWNED

    return OWNERSHIP_UNKNOWN


def infer_matadors_from_known_ownership(
    game_type: str,
    declarer_owned_cards: list[str],
    non_declarer_owned_cards: list[str],
) -> int | None:
    """Infers matadors only from deterministic declarer ownership facts."""
    trump_order = get_trump_order_for_matadors(game_type)

    if not trump_order:
        return None

    declarer_owned_card_set = set(declarer_owned_cards)
    non_declarer_owned_card_set = set(non_declarer_owned_cards)
    top_trump_state = get_matador_ownership_state(
        card=trump_order[0],
        declarer_owned_cards=declarer_owned_card_set,
        non_declarer_owned_cards=non_declarer_owned_card_set,
    )

    if top_trump_state is None or top_trump_state == OWNERSHIP_UNKNOWN:
        return None

    matadors = 0

    for trump_card in trump_order:
        ownership_state = get_matador_ownership_state(
            card=trump_card,
            declarer_owned_cards=declarer_owned_card_set,
            non_declarer_owned_cards=non_declarer_owned_card_set,
        )

        if ownership_state is None or ownership_state == OWNERSHIP_UNKNOWN:
            return None

        if ownership_state == top_trump_state:
            matadors += 1
            continue

        return matadors

    return matadors


def get_completed_trick_ownership_cards_for_local_declarer(
    completed_tricks: list[dict],
) -> tuple[list[str], list[str]]:
    """Returns completed-trick cards with deterministic local-declarer ownership."""
    declarer_owned_cards = []
    non_declarer_owned_cards = []

    for completed_trick in completed_tricks:
        cards = completed_trick.get("cards")
        players = completed_trick.get("players")

        if not isinstance(cards, list) or not isinstance(players, list):
            continue

        if len(cards) != 3 or len(players) != 3:
            continue

        if players not in VALID_COMPLETED_TRICK_PLAYER_ORDERS:
            continue

        for card, player in zip(cards, players, strict=True):
            if player == "me":
                declarer_owned_cards.append(card)
            else:
                non_declarer_owned_cards.append(card)

    return declarer_owned_cards, non_declarer_owned_cards


def infer_matadors_from_local_declarer_known_ownership(
    game_type: str,
    player_role: str,
    declarer_cards: list[str],
    completed_tricks: list[dict],
) -> int | None:
    """Infers matadors from safe local-declarer ownership facts."""
    if player_role != "declarer":
        return None

    (
        completed_trick_declarer_cards,
        completed_trick_non_declarer_cards,
    ) = get_completed_trick_ownership_cards_for_local_declarer(completed_tricks)

    return infer_matadors_from_known_ownership(
        game_type=game_type,
        declarer_owned_cards=[*declarer_cards, *completed_trick_declarer_cards],
        non_declarer_owned_cards=completed_trick_non_declarer_cards,
    )
