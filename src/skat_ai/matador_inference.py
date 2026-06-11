from skat_ai.rules import get_trump_suit

SUIT_GAME_RANK_ORDER = ["A", "10", "K", "Q", "9", "8", "7"]
JACK_ORDER = ["CJ", "SJ", "HJ", "DJ"]
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