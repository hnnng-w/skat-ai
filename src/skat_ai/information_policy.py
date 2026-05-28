from typing import Any


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

    return {
        "analysis_mode": analysis_mode,
        "skat_visibility": skat_visibility,
        "game_end_reason": game_end_reason,
        "live_information_enforced": live_information_enforced,
        "known_post_game_skat_allowed": not live_information_enforced,
        "known_skat_cards_allowed": not live_information_enforced,
        "ended_game_allowed": not live_information_enforced,
        "unverifiable_completed_trick_winner_metadata_allowed": (
            not live_information_enforced
        ),
    }