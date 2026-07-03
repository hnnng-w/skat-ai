from typing import Any

from skat_ai.side_ownership import normalize_declarer_player


def is_skat_visible_to_local_player(
    player_role: str,
    declarer_player: str | None,
    skat_visibility: str,
) -> bool:
    """Returns whether supplied Skat identities are visible locally."""
    if skat_visibility == "known_post_game":
        return True

    if skat_visibility != "known_to_declarer":
        return False

    normalized_declarer_player = normalize_declarer_player(
        player_role=player_role,
        declarer_player=declarer_player,
    )

    return normalized_declarer_player == "me"


def build_local_analysis_input(
    data: dict[str, Any],
) -> dict[str, Any]:
    """Builds the local-information view used by analysis and output.

    The input may contain privileged Skat identities. For local defenders,
    `known_to_declarer` Skat cards are declarer-private and must not condition
    local recommendations or serialized local state.
    """
    local_data = data.copy()
    skat_visibility = data.get("skat_visibility", "unknown")

    if is_skat_visible_to_local_player(
        player_role=data["player_role"],
        declarer_player=data.get("declarer_player"),
        skat_visibility=skat_visibility,
    ):
        local_data["skat"] = list(data.get("skat", []))
    else:
        local_data["skat"] = []

    return local_data
