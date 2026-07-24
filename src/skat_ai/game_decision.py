from typing import Any

from skat_ai.final_settlement import is_schneider_announced, is_schwarz_announced
from skat_ai.game_result import (
    SCHNEIDER_POINT_THRESHOLD,
    get_card_point_winner,
    get_completed_trick_winner_roles,
)
from skat_ai.overbid import get_overbid_required_level

SCHNEIDER_SECURED_POINT_THRESHOLD = 90


def get_mandatory_level_source(
    game_value_summary: dict[str, Any],
    overbid_required_level: str | None,
) -> str | None:
    """Returns the source of a still-relevant mandatory higher level."""
    has_declared_announcement = (
        game_value_summary.get("is_null_game") is False
        and is_schneider_announced(game_value_summary)
    )
    has_overbid_requirement = overbid_required_level is not None

    if has_declared_announcement and has_overbid_requirement:
        return "declared_announcement_and_overbid_requirement"
    if has_declared_announcement:
        return "declared_announcement"
    if has_overbid_requirement:
        return "overbid_requirement"
    return None


def determine_decision_state_before_game_end(
    game_result_summary: dict[str, Any],
    game_value_summary: dict[str, Any],
    overbid_summary: dict[str, Any],
    completed_tricks: list[dict[str, Any]],
) -> str:
    """Determines whether the declared contract is already decided."""
    winner_roles = get_completed_trick_winner_roles(completed_tricks)
    if game_value_summary.get("is_null_game") is True:
        if "declarer" in winner_roles:
            return "defenders_already_won"
        return "undecided"

    declarer_points = game_result_summary["declarer_points"]
    defender_points = game_result_summary["defender_points"]
    overbid_required_level = get_overbid_required_level(
        game_value_summary,
        overbid_summary,
    )
    requires_schneider = (
        is_schneider_announced(game_value_summary)
        or overbid_required_level in {"schneider", "schwarz"}
    )
    requires_schwarz = (
        is_schwarz_announced(game_value_summary)
        or overbid_required_level == "schwarz"
    )

    if requires_schneider and defender_points > SCHNEIDER_POINT_THRESHOLD:
        return "defenders_already_won"
    if requires_schwarz and "defenders" in winner_roles:
        return "defenders_already_won"

    base_winner = get_card_point_winner(declarer_points, defender_points)
    if base_winner == "defenders":
        return "defenders_already_won"
    if base_winner != "declarer":
        return "undecided"

    if requires_schwarz:
        return "undecided"
    if requires_schneider and declarer_points < SCHNEIDER_SECURED_POINT_THRESHOLD:
        return "undecided"
    return "declarer_already_won"


def get_secured_achieved_schneider_status(
    decision_state: str,
    game_result_summary: dict[str, Any],
) -> str | None:
    """Returns Schneider only when observed points already secure it."""
    if (
        decision_state == "declarer_already_won"
        and game_result_summary["declarer_points"]
        >= SCHNEIDER_SECURED_POINT_THRESHOLD
    ):
        return "declarer_made_schneider"
    if (
        decision_state == "defenders_already_won"
        and game_result_summary["defender_points"]
        >= SCHNEIDER_SECURED_POINT_THRESHOLD
    ):
        return "defenders_made_schneider"
    return None
