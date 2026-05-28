from typing import Any

from skat_ai.deck import get_full_deck
from skat_ai.game_declaration import build_game_declaration_from_input
from skat_ai.game_history import validate_completed_trick_sequence
from skat_ai.opponent_policy import validate_opponent_card_policy
from skat_ai.opponent_policy_preset import validate_opponent_policy_preset
from skat_ai.performance_rating import validate_performance_rating_system
from skat_ai.rules import GAME_TYPES, get_card_points, get_trick_points
from skat_ai.strategic_metadata import (
    validate_analysis_mode,
    validate_analysis_mode_skat_visibility_combination,
    validate_game_end_reason,
    validate_skat_visibility,
)

VALID_PLAYER_ROLES = ["declarer", "defender", "unknown"]
VALID_PLAYER_POSITIONS = ["forehand", "middlehand", "rearhand", "unknown"]
VALID_TRICK_LEADERS = ["me", "left", "right", "unknown"]
VALID_NEXT_PLAYERS = ["me", "left", "right", "unknown"]
VALID_COMPLETED_TRICK_WINNER_ROLES = ["declarer", "defenders"]
VALID_TRICK_PLAYERS = ["me", "left", "right"]


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
    # Legacy field:
    # Keep for backward compatibility. Prefer completed_tricks for completed tricks.
    played_cards = data.get("played_cards", [])
    skat = data.get("skat", [])
    completed_tricks = data.get("completed_tricks", [])
    analysis_mode = data.get("analysis_mode", "live_decision")
    game_end_reason = data.get("game_end_reason", "not_ended")

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
    validate_optional_analysis_metadata(data)
    validate_optional_opponent_policies(data)
    validate_optional_profile_preset_settings(data)
    validate_optional_game_declaration(data)
    validate_performance_rating_system(data.get("performance_rating_system"))
    validate_completed_trick_sequence(
        completed_tricks=data.get("completed_tricks", []),
        current_trick=data.get("current_trick", []),
        trick_leader=data.get("trick_leader", "unknown"),
        player_role=data.get("player_role", "unknown"),
        game_type=data.get("game_type", "grand"),
    )
    validate_analysis_mode_skat_visibility_combination(
        analysis_mode=analysis_mode,
        skat_visibility=data.get("skat_visibility", "unknown"),
    )
    validate_live_decision_has_no_known_skat_cards(
        analysis_mode=analysis_mode,
        skat=data.get("skat", []),
    )
    validate_live_completed_trick_metadata(
        analysis_mode=analysis_mode,
        completed_tricks=data.get("completed_tricks", []),
    )
    validate_live_decision_has_no_game_end_reason(
        analysis_mode=analysis_mode,
        game_end_reason=game_end_reason,
    )

    validate_live_decision_is_not_complete_game(
        analysis_mode=analysis_mode,
        known_card_points=calculate_known_card_points_from_input(data),
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
        players = completed_trick.get("players")
        winner_player = completed_trick.get("winner_player")

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

        if players is not None:
            if not isinstance(players, list):
                raise ValueError("Completed trick players must be a list.")

            if len(players) != 3:
                raise ValueError("Completed trick players must contain exactly 3 players.")

            invalid_players = [
                player for player in players
                if player not in VALID_TRICK_PLAYERS
            ]

            if invalid_players:
                raise ValueError(f"Invalid completed trick players: {invalid_players}")

        if winner_player is not None and winner_player not in VALID_TRICK_PLAYERS:
            raise ValueError(f"Invalid completed trick winner player: {winner_player}")

def validate_optional_player_profile(
    profile: dict[str, Any] | None,
    field_name: str,
) -> None:
    """
    Validates an optional player profile input.
    """
    if profile is None:
        return

    if not isinstance(profile, dict):
        raise ValueError(f"{field_name} must be an object.")

    integer_fields = [
        "games_played",
        "solo_games_played",
        "defender_games_played",
    ]
    rate_fields = [
        "solo_rate",
        "solo_win_rate",
        "hand_game_rate",
        "suit_game_rate",
        "grand_rate",
        "null_game_rate",
        "defender_win_rate",
    ]

    for key in integer_fields:
        if key in profile and profile[key] is not None:
            value = profile[key]

            if not isinstance(value, int) or value < 0:
                raise ValueError(f"{field_name}.{key} must be a non-negative integer.")

    for key in rate_fields:
        if key in profile and profile[key] is not None:
            value = profile[key]

            if not isinstance(value, int | float) or value < 0 or value > 1:
                raise ValueError(f"{field_name}.{key} must be a number between 0 and 1.")


def validate_optional_analysis_metadata(data: dict[str, Any]) -> None:
    """
    Validates optional analysis metadata fields.
    """
    if "analysis_mode" in data:
        validate_analysis_mode(data["analysis_mode"])

    if "skat_visibility" in data:
        validate_skat_visibility(data["skat_visibility"])

    if "game_end_reason" in data:
        validate_game_end_reason(data["game_end_reason"])

    validate_optional_player_profile(
        profile=data.get("left_player_profile"),
        field_name="left_player_profile",
    )
    validate_optional_player_profile(
        profile=data.get("right_player_profile"),
        field_name="right_player_profile",
    )

def validate_optional_opponent_policies(data: dict[str, Any]) -> None:
    """
    Validates optional opponent policy fields.
    """
    if "opponent_policy_preset" in data:
        validate_opponent_policy_preset(data["opponent_policy_preset"])

    if "opponent_lead_policy" in data:
        validate_opponent_card_policy(data["opponent_lead_policy"])

    if "opponent_response_policy" in data:
        validate_opponent_card_policy(data["opponent_response_policy"])

def validate_optional_profile_preset_settings(data: dict[str, Any]) -> None:
    """
    Validates optional profile-preset settings.
    """
    if "use_profile_presets" in data:
        validate_boolean(data["use_profile_presets"], "use_profile_presets")

def validate_optional_game_declaration(data: dict[str, Any]) -> None:
    """
    Validates optional game declaration scoring fields.
    """
    build_game_declaration_from_input(data)

def validate_total_known_card_points(data: dict[str, Any]) -> None:
    explicit_declarer_points = data.get("declarer_points", 0)
    explicit_defender_points = data.get("defender_points", 0)

    completed_trick_points = 0
    for completed_trick in data.get("completed_tricks", []):
        completed_trick_points += sum(
            get_card_points(card) for card in completed_trick["cards"]
        )

    total_points = (
        explicit_declarer_points
        + explicit_defender_points
        + completed_trick_points
    )

    if total_points > 120:
        raise ValueError("Known card points cannot exceed 120.")

def validate_live_decision_has_no_known_skat_cards(
    analysis_mode: str,
    skat: list[str],
) -> None:
    """
    Validates that live decisions do not include known skat cards.
    """
    if analysis_mode == "live_decision" and skat:
        raise ValueError(
            "Known skat cards are not allowed for analysis_mode='live_decision'. "
            "Use analysis_mode='post_game_review' for post-game known skat cards."
        )

def validate_live_completed_trick_metadata(
    analysis_mode: str,
    completed_tricks: list[dict],
) -> None:
    """
    Validates that live decisions do not contain unverifiable
    post-game-style completed-trick metadata.
    """
    if analysis_mode != "live_decision":
        return

    for completed_trick in completed_tricks:
        has_players = "players" in completed_trick
        has_winner_player = "winner_player" in completed_trick
        has_winner_role = "winner_role" in completed_trick

        if has_winner_player and not has_players:
            raise ValueError(
                "winner_player in completed_tricks is only allowed for "
                "analysis_mode='live_decision' when players are provided."
            )

        if has_winner_role and not has_players:
            raise ValueError(
                "winner_role in completed_tricks is only allowed for "
                "analysis_mode='live_decision' when players are provided."
            )

def validate_live_decision_has_no_game_end_reason(
    analysis_mode: str,
    game_end_reason: str,
) -> None:
    """
    Validates that live decisions are not marked as ended games.
    """
    if analysis_mode == "live_decision" and game_end_reason != "not_ended":
        raise ValueError(
            "analysis_mode='live_decision' requires "
            "game_end_reason='not_ended'."
        )


def calculate_known_card_points_from_input(
    data: dict[str, Any],
) -> int:
    """
    Calculates known card points from explicit points and completed tricks.
    """
    explicit_points = data.get("declarer_points", 0) + data.get(
        "defender_points", 0
    )

    completed_trick_points = 0

    for completed_trick in data.get("completed_tricks", []):
        completed_trick_points += get_trick_points(completed_trick["cards"])

    return explicit_points + completed_trick_points


def validate_live_decision_is_not_complete_game(
    analysis_mode: str,
    known_card_points: int,
) -> None:
    """
    Validates that live decisions do not already represent a completed game.
    """
    if analysis_mode == "live_decision" and known_card_points == 120:
        raise ValueError(
            "analysis_mode='live_decision' cannot be used for a completed game "
            "with all 120 card points assigned."
        )