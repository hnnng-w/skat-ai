from typing import Any

from skat_ai.game_history import validate_completed_trick_rule_winner
from skat_ai.rules import get_trick_points


def is_live_information_enforced(
    analysis_mode: str,
) -> bool:
    """
    Returns whether live-information restrictions are enforced.
    """
    return analysis_mode == "live_decision"


def build_information_policy_summary(
    analysis_mode: str,
    skat_visibility: str,
    game_end_reason: str,
) -> dict[str, Any]:
    """
    Builds a JSON-serializable information policy summary.
    """
    live_information_enforced = is_live_information_enforced(analysis_mode)
    known_skat_cards_allowed = (
        not live_information_enforced
        or skat_visibility == "known_to_declarer"
    )

    return {
        "analysis_mode": analysis_mode,
        "skat_visibility": skat_visibility,
        "game_end_reason": game_end_reason,
        "live_information_enforced": live_information_enforced,
        "known_post_game_skat_allowed": not live_information_enforced,
        "known_skat_cards_allowed": known_skat_cards_allowed,
        "ended_game_allowed": not live_information_enforced,
        "unverifiable_completed_trick_winner_metadata_allowed": (
            not live_information_enforced
        ),
    }


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


def validate_live_decision_has_no_known_skat_cards(
    analysis_mode: str,
    skat_visibility: str,
    skat: list[str],
) -> None:
    """
    Validates that live decisions do not include known skat cards.
    """
    if (
        analysis_mode == "live_decision"
        and skat
        and skat_visibility != "known_to_declarer"
    ):
        raise ValueError(
            "Known skat cards are not allowed for analysis_mode='live_decision'. "
            "Use skat_visibility='known_to_declarer' only when the concrete "
            "declarer legitimately knows the Skat."
        )


def validate_skat_card_count_for_visibility(
    skat_visibility: str,
    skat: list[str],
) -> None:
    """Validates concrete Skat-card counts for the visibility state."""
    if skat_visibility == "unknown" and skat:
        raise ValueError("skat_visibility='unknown' requires skat to be empty.")

    if (
        skat_visibility in ["known_to_declarer", "known_post_game"]
        and len(skat) not in [0, 2]
    ):
        raise ValueError(
            f"skat_visibility='{skat_visibility}' requires either zero or two "
            "concrete Skat cards."
        )


def validate_live_completed_trick_metadata(
    analysis_mode: str,
    completed_tricks: list[dict[str, Any]],
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


def validate_live_completed_trick_winner_role_verifiability(
    data: dict[str, Any],
) -> None:
    """
    Validates that live completed-trick winner_role values are derivable.
    """
    if data.get("analysis_mode", "live_decision") != "live_decision":
        return

    for trick_index, completed_trick in enumerate(data.get("completed_tricks", [])):
        validate_completed_trick_rule_winner(
            completed_trick=completed_trick,
            game_type=data.get("game_type", "grand"),
            player_role=data.get("player_role", "unknown"),
            declarer_player=data.get("declarer_player", "unknown"),
            trick_index=trick_index,
            require_verifiable_winner_role=True,
        )


def validate_ended_game_requires_post_game_review(
    analysis_mode: str,
    game_end_reason: str,
) -> None:
    """
    Validates that ended games are analyzed as post-game reviews.
    """
    if game_end_reason != "not_ended" and analysis_mode != "post_game_review":
        raise ValueError(
            "game_end_reason values other than 'not_ended' require "
            "analysis_mode='post_game_review'."
        )


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


def validate_information_policy_from_input(
    data: dict[str, Any],
) -> None:
    """
    Validates live-vs-post-game information policy rules for raw input data.
    """
    analysis_mode = data.get("analysis_mode", "live_decision")
    game_end_reason = data.get("game_end_reason", "not_ended")

    validate_live_decision_has_no_known_skat_cards(
        analysis_mode=analysis_mode,
        skat_visibility=data.get("skat_visibility", "unknown"),
        skat=data.get("skat", []),
    )
    validate_skat_card_count_for_visibility(
        skat_visibility=data.get("skat_visibility", "unknown"),
        skat=data.get("skat", []),
    )
    validate_live_completed_trick_metadata(
        analysis_mode=analysis_mode,
        completed_tricks=data.get("completed_tricks", []),
    )
    validate_live_completed_trick_winner_role_verifiability(data)
    validate_ended_game_requires_post_game_review(
        analysis_mode=analysis_mode,
        game_end_reason=game_end_reason,
    )
    validate_live_decision_is_not_complete_game(
        analysis_mode=analysis_mode,
        known_card_points=calculate_known_card_points_from_input(data),
    )
