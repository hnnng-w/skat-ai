from typing import Any

from skat_ai.deck import get_full_deck
from skat_ai.rules import GAME_TYPES

VALID_PLAYER_ROLES = ["declarer", "defender", "unknown"]
VALID_PLAYER_POSITIONS = ["forehand", "middlehand", "rearhand", "unknown"]
VALID_TRICK_LEADERS = ["me", "left", "right", "unknown"]
VALID_NEXT_PLAYERS = ["me", "left", "right", "unknown"]
VALID_COMPLETED_TRICK_WINNER_ROLES = ["declarer", "defenders"]


def validate_required_keys(data: dict[str, Any]) -> None:
    """
    Validates that all required input keys exist.
    """
    required_keys = [
        "game_type",
        "player_role",
        "hand",
        "current_trick",
        "left_hand_size",
        "right_hand_size",
        "sample_count",
    ]

    missing_keys = [key for key in required_keys if key not in data]

    if missing_keys:
        raise ValueError(f"Missing required input keys: {missing_keys}")


def validate_game_type(game_type: str) -> None:
    """
    Validates the game type.
    """
    if game_type not in GAME_TYPES:
        raise ValueError(f"Invalid game type: {game_type}")


def validate_player_role(player_role: str) -> None:
    """
    Validates the player role.
    """
    if player_role not in VALID_PLAYER_ROLES:
        raise ValueError(f"Invalid player role: {player_role}")


def validate_player_position(player_position: str) -> None:
    """
    Validates the player's table position.
    """
    if player_position not in VALID_PLAYER_POSITIONS:
        raise ValueError(f"Invalid player position: {player_position}")


def validate_trick_leader(trick_leader: str) -> None:
    """
    Validates who led the current trick.
    """
    if trick_leader not in VALID_TRICK_LEADERS:
        raise ValueError(f"Invalid trick leader: {trick_leader}")


def validate_cards(cards: list[str], field_name: str) -> None:
    """
    Validates that all cards in a list exist in the Skat deck.
    """
    full_deck = set(get_full_deck())

    invalid_cards = [card for card in cards if card not in full_deck]

    if invalid_cards:
        raise ValueError(f"Invalid cards in {field_name}: {invalid_cards}")


def validate_no_duplicate_cards(data: dict[str, Any]) -> None:
    """
    Validates that the same card is not listed in multiple known-card fields.
    """
    known_card_fields = [
        "hand",
        "current_trick",
        "played_cards",
        "skat",
    ]

    all_cards = []

    for field in known_card_fields:
        all_cards.extend(data.get(field, []))

    all_cards.extend(
        get_cards_from_completed_tricks_input(
            data.get("completed_tricks", []),
        )
    )

    duplicates = sorted({
        card for card in all_cards
        if all_cards.count(card) > 1
    })

    if duplicates:
        raise ValueError(f"Duplicate known cards found: {duplicates}")


def validate_current_trick(current_trick: list[str]) -> None:
    """
    Validates the current trick length.

    If the user is about to play, the current trick can contain:
    - 0 cards if the player leads
    - 1 card if the player plays second
    - 2 cards if the player plays third
    """
    if len(current_trick) > 2:
        raise ValueError("Current trick must contain at most 2 cards.")


def validate_trick_leader_matches_current_trick(
    trick_leader: str,
    current_trick: list[str],
) -> None:
    """
    Validates basic consistency between trick_leader and current_trick.

    Rules:
    - If current_trick is empty, the player is leading, so trick_leader may be "me" or "unknown".
    - If current_trick is not empty, another player has already led,
    so trick_leader should not be "me".
    """
    if len(current_trick) == 0 and trick_leader not in ["me", "unknown"]:
        raise ValueError("trick_leader must be 'me' or 'unknown' when current_trick is empty.")

    if len(current_trick) > 0 and trick_leader == "me":
        raise ValueError("trick_leader cannot be 'me' when current_trick is not empty.")


def validate_positive_integer(value: Any, field_name: str) -> None:
    """
    Validates that a value is a positive integer.
    """
    if not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer.")


def validate_optional_random_seed(value: Any) -> None:
    """
    Validates the optional random seed.
    """
    if value is not None and not isinstance(value, int):
        raise ValueError("random_seed must be an integer or null.")


def validate_boolean(value: Any, field_name: str) -> None:
    """
    Validates that a value is boolean.
    """
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be a boolean.")


def validate_position_input(data: dict[str, Any]) -> None:
    """
    Validates the complete JSON input for a position analysis.
    """
    validate_required_keys(data)

    validate_game_type(data["game_type"])
    validate_player_role(data["player_role"])
    validate_player_position(data.get("player_position", "unknown"))
    validate_trick_leader(data.get("trick_leader", "unknown"))

    hand = data["hand"]
    current_trick = data["current_trick"]
    played_cards = data.get("played_cards", [])
    skat = data.get("skat", [])
    completed_tricks = data.get("completed_tricks", [])

    validate_cards(hand, "hand")
    validate_cards(current_trick, "current_trick")
    validate_cards(played_cards, "played_cards")
    validate_cards(skat, "skat")
    validate_completed_tricks(completed_tricks)

    validate_no_duplicate_cards(data)
    validate_current_trick(current_trick)
    validate_trick_leader_matches_current_trick(
        trick_leader=data.get("trick_leader", "unknown"),
        current_trick=current_trick,
    )

    validate_positive_integer(data["left_hand_size"], "left_hand_size")
    validate_positive_integer(data["right_hand_size"], "right_hand_size")
    validate_positive_integer(data["sample_count"], "sample_count")

    validate_non_negative_integer(data.get("declarer_points", 0), "declarer_points")
    validate_non_negative_integer(data.get("defender_points", 0), "defender_points")
    validate_next_player(data.get("next_player", "unknown"))

    validate_optional_random_seed(data.get("random_seed"))
    validate_boolean(
        data.get("use_basic_opponent_strategy", True),
        "use_basic_opponent_strategy",
    )


def validate_next_player(next_player: str) -> None:
    """
    Validates who acts next.
    """
    if next_player not in VALID_NEXT_PLAYERS:
        raise ValueError(f"Invalid next player: {next_player}")


def validate_non_negative_integer(value: Any, field_name: str) -> None:
    """
    Validates that a value is a non-negative integer.
    """
    if not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer.")


def get_cards_from_completed_tricks_input(completed_tricks: list[dict[str, Any]]) -> list[str]:
    """
    Returns all cards from completed tricks in input data.
    """
    cards = []

    for completed_trick in completed_tricks:
        cards.extend(completed_trick.get("cards", []))

    return cards


def validate_completed_tricks(completed_tricks: list[dict[str, Any]]) -> None:
    """
    Validates completed trick entries.
    """
    full_deck = set(get_full_deck())

    for completed_trick in completed_tricks:
        if "cards" not in completed_trick:
            raise ValueError("Completed trick is missing required key: cards")

        if "winner_role" not in completed_trick:
            raise ValueError("Completed trick is missing required key: winner_role")

        cards = completed_trick["cards"]
        winner_role = completed_trick["winner_role"]

        if not isinstance(cards, list):
            raise ValueError("Completed trick cards must be a list.")

        if len(cards) != 3:
            raise ValueError("Completed trick must contain exactly 3 cards.")

        invalid_cards = [
            card for card in cards
            if card not in full_deck
        ]

        if invalid_cards:
            raise ValueError(f"Invalid cards in completed_tricks: {invalid_cards}")

        if winner_role not in VALID_COMPLETED_TRICK_WINNER_ROLES:
            raise ValueError(f"Invalid completed trick winner role: {winner_role}")