from typing import Any

from skat_ai.deck import get_full_deck
from skat_ai.game_declaration import build_game_declaration_from_input
from skat_ai.game_history import validate_completed_trick_sequence
from skat_ai.information_policy import validate_information_policy_from_input
from skat_ai.opponent_policy import validate_opponent_card_policy
from skat_ai.opponent_policy_preset import validate_opponent_policy_preset
from skat_ai.performance_rating import (
    build_list_game_contribution_from_analysis_result,
    validate_performance_rating_system,
)
from skat_ai.rules import GAME_TYPES, get_card_points, get_legal_cards
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
LIST_PERFORMANCE_REQUIRED_FIELDS = [
    "player_game_points",
    "own_games_won",
    "own_games_lost",
    "other_players_lost_games",
]
LIST_PERFORMANCE_COUNTER_FIELDS = [
    "own_games_won",
    "own_games_lost",
    "other_players_lost_games",
]
LIST_GAME_CONTRIBUTION_REQUIRED_FIELDS = [
    "player_role",
    "game_outcome",
    "settlement_score",
]
VALID_LIST_GAME_CONTRIBUTION_PLAYER_ROLES = ["declarer", "defender"]
VALID_LIST_GAME_CONTRIBUTION_OUTCOMES = ["declarer_win", "declarer_loss"]


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


def validate_actual_card_played(data: dict[str, Any]) -> None:
    """Validates the optional actual card played in post-game review mode."""
    actual_card_played = data.get("actual_card_played")

    if actual_card_played is None:
        return

    validate_cards([actual_card_played], "actual_card_played")

    analysis_mode = data.get("analysis_mode", "live_decision")
    if analysis_mode != "post_game_review":
        raise ValueError(
            "actual_card_played requires analysis_mode to be post_game_review."
        )

    hand = data["hand"]
    if actual_card_played not in hand:
        raise ValueError("actual_card_played must be contained in hand.")

    legal_cards = get_legal_cards(
        hand=hand,
        current_trick=data["current_trick"],
        game_type=data["game_type"],
    )

    if actual_card_played not in legal_cards:
        raise ValueError("actual_card_played must be legal in the current position.")


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
    validate_actual_card_played(data)

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
    validate_list_performance_input_modes(data)
    validate_optional_list_performance_input(data)
    validate_optional_list_game_contributions(data)
    validate_optional_list_analysis_results(data)
    validate_completed_trick_sequence(
        completed_tricks=data.get("completed_tricks", []),
        current_trick=data.get("current_trick", []),
        trick_leader=data.get("trick_leader", "unknown"),
        player_role=data.get("player_role", "unknown"),
        game_type=data.get("game_type", "grand"),
    )
    validate_analysis_mode_skat_visibility_combination(
        analysis_mode=data.get("analysis_mode", "live_decision"),
        skat_visibility=data.get("skat_visibility", "unknown"),
    )

    validate_information_policy_from_input(data)


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


def validate_strict_integer(value: Any, field_name: str) -> None:
    """
    Validates that a value is an integer and not a boolean.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer.")


def validate_list_performance_input_modes(data: dict[str, Any]) -> None:
    """
    Validates that only one list/series performance input mode is supplied.
    """
    supplied_modes = [
        field_name
        for field_name in [
            "list_performance_input",
            "list_game_contributions",
            "list_analysis_results",
        ]
        if field_name in data
    ]

    if len(supplied_modes) > 1:
        raise ValueError(
            "list_performance_input, list_game_contributions, and "
            "list_analysis_results are alternative input modes. Provide only one."
        )


def validate_optional_list_performance_input(data: dict[str, Any]) -> None:
    """
    Validates optional already aggregated list/series performance input.
    """
    if "list_performance_input" not in data:
        return

    list_performance_input = data["list_performance_input"]

    if not isinstance(list_performance_input, dict):
        raise ValueError("list_performance_input must be an object.")

    if data.get("performance_rating_system") != "isko_list":
        raise ValueError(
            "list_performance_input requires performance_rating_system to be isko_list."
        )

    missing_fields = [
        field_name
        for field_name in LIST_PERFORMANCE_REQUIRED_FIELDS
        if field_name not in list_performance_input
    ]
    if missing_fields:
        raise ValueError(
            "list_performance_input is missing required keys: "
            f"{missing_fields}"
        )

    for field_name in LIST_PERFORMANCE_REQUIRED_FIELDS:
        validate_strict_integer(
            list_performance_input[field_name],
            f"list_performance_input.{field_name}",
        )

    for field_name in LIST_PERFORMANCE_COUNTER_FIELDS:
        if list_performance_input[field_name] < 0:
            raise ValueError(
                f"list_performance_input.{field_name} must be non-negative."
            )


def validate_optional_list_game_contributions(data: dict[str, Any]) -> None:
    """
    Validates optional normalized list/series game contributions.
    """
    if "list_game_contributions" not in data:
        return

    list_game_contributions = data["list_game_contributions"]

    if not isinstance(list_game_contributions, list):
        raise ValueError("list_game_contributions must be an array.")

    if data.get("performance_rating_system") != "isko_list":
        raise ValueError(
            "list_game_contributions requires performance_rating_system to be "
            "isko_list."
        )

    for index, contribution in enumerate(list_game_contributions):
        validate_list_game_contribution(contribution, index)


def validate_list_game_contribution(contribution: Any, index: int) -> None:
    """
    Validates one normalized list/series game contribution.
    """
    field_prefix = f"list_game_contributions[{index}]"

    if not isinstance(contribution, dict):
        raise ValueError(f"{field_prefix} must be an object.")

    missing_fields = [
        field_name
        for field_name in LIST_GAME_CONTRIBUTION_REQUIRED_FIELDS
        if field_name not in contribution
    ]
    if missing_fields:
        raise ValueError(
            f"{field_prefix} is missing required keys: {missing_fields}"
        )

    additional_fields = sorted(
        set(contribution) - set(LIST_GAME_CONTRIBUTION_REQUIRED_FIELDS)
    )
    if additional_fields:
        raise ValueError(
            f"{field_prefix} has unsupported keys: {additional_fields}"
        )

    player_role = contribution["player_role"]
    if player_role not in VALID_LIST_GAME_CONTRIBUTION_PLAYER_ROLES:
        raise ValueError(f"Unsupported {field_prefix}.player_role: {player_role}.")

    game_outcome = contribution["game_outcome"]
    if game_outcome not in VALID_LIST_GAME_CONTRIBUTION_OUTCOMES:
        raise ValueError(
            f"Unsupported {field_prefix}.game_outcome: {game_outcome}."
        )

    settlement_score = contribution["settlement_score"]
    validate_strict_integer(settlement_score, f"{field_prefix}.settlement_score")

    if game_outcome == "declarer_win" and settlement_score <= 0:
        raise ValueError(
            f"{field_prefix} declarer_win requires a positive settlement_score."
        )

    if game_outcome == "declarer_loss" and settlement_score >= 0:
        raise ValueError(
            f"{field_prefix} declarer_loss requires a negative settlement_score."
        )


def validate_optional_list_analysis_results(data: dict[str, Any]) -> None:
    """
    Validates optional local analysis results for list/series performance input.
    """
    if "list_analysis_results" not in data:
        return

    list_analysis_results = data["list_analysis_results"]

    if not isinstance(list_analysis_results, list):
        raise ValueError("list_analysis_results must be an array.")

    if data.get("performance_rating_system") != "isko_list":
        raise ValueError(
            "list_analysis_results requires performance_rating_system to be "
            "isko_list."
        )

    for index, analysis_result in enumerate(list_analysis_results):
        try:
            build_list_game_contribution_from_analysis_result(analysis_result)
        except ValueError as error:
            raise ValueError(f"list_analysis_results[{index}]: {error}") from error


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

    if "left_opponent_lead_policy" in data:
        validate_opponent_card_policy(data["left_opponent_lead_policy"])

    if "left_opponent_response_policy" in data:
        validate_opponent_card_policy(data["left_opponent_response_policy"])

    if "right_opponent_lead_policy" in data:
        validate_opponent_card_policy(data["right_opponent_lead_policy"])

    if "right_opponent_response_policy" in data:
        validate_opponent_card_policy(data["right_opponent_response_policy"])

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
