SUITS = ["C", "S", "H", "D"]
RANKS = ["A", "10", "K", "Q", "J", "9", "8", "7"]


def get_full_deck() -> list[str]:
    """
    Returns the full 32-card Skat deck.
    """
    return [f"{suit}{rank}" for suit in SUITS for rank in RANKS]
