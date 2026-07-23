from dataclasses import dataclass
from typing import Any

from skat_ai.opponent_statistics import OpponentStatisticsInput, build_opponent_statistics_summary
from skat_ai.player_profile import PlayerProfile, build_player_profile_from_dict


@dataclass(frozen=True)
class BoundExternalOpponentProfile:
    """One validated external statistics record bound to an opponent side."""

    player_id: str
    player_label: str | None
    source: dict[str, str]
    profile: PlayerProfile
    derivation: dict[str, Any]


@dataclass(frozen=True)
class LiveOpponentProfileBindings:
    """Independent optional external profile bindings for a live position."""

    left: BoundExternalOpponentProfile | None
    right: BoundExternalOpponentProfile | None


def _validate_requested_player_id(player_id: str | None, option_name: str) -> None:
    if player_id is not None and (not player_id or player_id != player_id.strip()):
        raise ValueError(f"{option_name} must be a non-empty, non-padded string.")


def _resolve_binding(
    records: list[dict[str, Any]],
    player_id: str | None,
    option_name: str,
) -> BoundExternalOpponentProfile | None:
    if player_id is None:
        return None

    matches = [record for record in records if record.get("player_id") == player_id]
    if len(matches) != 1:
        raise ValueError(
            f"{option_name} '{player_id}' must match exactly one opponent-statistics record."
        )

    record = matches[0]
    source = record.get("source")
    profile_data = record.get("normalized_profile_statistics")
    derivation = record.get("profile_derivation")
    if not isinstance(source, dict) or not isinstance(profile_data, dict) or not isinstance(
        derivation, dict
    ):
        raise ValueError("Opponent-statistics summary is missing normalized profile data.")

    return BoundExternalOpponentProfile(
        player_id=player_id,
        player_label=record.get("player_label"),
        source=source.copy(),
        profile=build_player_profile_from_dict(profile_data),
        derivation=derivation.copy(),
    )


def resolve_live_opponent_profile_bindings(
    opponent_statistics_summary: dict[str, Any] | OpponentStatisticsInput,
    left_player_id: str | None = None,
    right_player_id: str | None = None,
) -> LiveOpponentProfileBindings:
    """Resolves exact case-sensitive external player IDs for left and right."""
    _validate_requested_player_id(left_player_id, "--left-opponent-player-id")
    _validate_requested_player_id(right_player_id, "--right-opponent-player-id")
    if left_player_id is not None and left_player_id == right_player_id:
        raise ValueError(
            "--left-opponent-player-id and --right-opponent-player-id must be different."
        )

    summary = (
        build_opponent_statistics_summary(opponent_statistics_summary)
        if isinstance(opponent_statistics_summary, OpponentStatisticsInput)
        else opponent_statistics_summary
    )
    records = summary.get("records")
    if not isinstance(records, list):
        raise ValueError("Opponent-statistics summary records must be an array.")

    return LiveOpponentProfileBindings(
        left=_resolve_binding(
            records,
            left_player_id,
            "--left-opponent-player-id",
        ),
        right=_resolve_binding(
            records,
            right_player_id,
            "--right-opponent-player-id",
        ),
    )
