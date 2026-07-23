from dataclasses import dataclass
from typing import Any

from skat_ai.historical_game import HistoricalGameRecord
from skat_ai.opponent_statistics import (
    OpponentStatisticsInput,
    build_opponent_statistics_summary,
)
from skat_ai.player_profile import PlayerProfile, build_player_profile_from_dict
from skat_ai.rfc3339 import parse_rfc3339_datetime

HISTORICAL_TEMPORAL_RULE = "captured_at_strictly_before_played_at"


@dataclass(frozen=True)
class HistoricalMatchedOpponentProfile:
    """One time-safe external profile matched to a stable historical player."""

    player_id: str
    player_label: str | None
    source: dict[str, str]
    profile: PlayerProfile
    derivation: dict[str, Any]


@dataclass(frozen=True)
class HistoricalOpponentProfileBindings:
    """Validated participant matches and their top-level application summary."""

    profiles_by_player_id: dict[str, HistoricalMatchedOpponentProfile]
    application_summary: dict[str, Any]


def _build_matched_profile(record: dict[str, Any]) -> HistoricalMatchedOpponentProfile:
    source = record.get("source")
    profile_data = record.get("normalized_profile_statistics")
    derivation = record.get("profile_derivation")
    if (
        not isinstance(source, dict)
        or not isinstance(profile_data, dict)
        or not isinstance(derivation, dict)
    ):
        raise ValueError("Opponent-statistics summary is missing normalized profile data.")
    return HistoricalMatchedOpponentProfile(
        player_id=record["player_id"],
        player_label=record.get("player_label"),
        source=source.copy(),
        profile=build_player_profile_from_dict(profile_data),
        derivation=derivation.copy(),
    )


def _build_participant_summary(
    player_id: str,
    player_label: str | None,
    profile: HistoricalMatchedOpponentProfile | None,
) -> dict[str, Any]:
    if profile is None:
        return {
            "player_id": player_id,
            "player_label": player_label,
            "match_status": "unmatched",
            "captured_at": None,
            "temporal_status": "not_applicable",
            "source": None,
            "profile_derivation_version": None,
            "classification": None,
            "derivation_status": None,
            "recommended_policy_preset": None,
            "actionable_policy_preset": None,
        }

    derivation = profile.derivation
    return {
        "player_id": player_id,
        "player_label": player_label,
        "match_status": "matched",
        "captured_at": profile.source["captured_at"],
        "temporal_status": "eligible",
        "source": profile.source.copy(),
        "profile_derivation_version": derivation["profile_derivation_version"],
        "classification": derivation["classification"],
        "derivation_status": derivation["derivation_status"],
        "recommended_policy_preset": derivation["recommended_policy_preset"],
        "actionable_policy_preset": derivation["actionable_policy_preset"],
    }


def resolve_historical_opponent_profile_bindings(
    historical_game: HistoricalGameRecord,
    opponent_statistics: OpponentStatisticsInput,
    statistics_input_file: str,
) -> HistoricalOpponentProfileBindings:
    """Matches exact participant IDs and enforces strict pre-game capture ordering."""
    if historical_game.played_at is None:
        raise ValueError(
            f"Historical game '{historical_game.game_id}' played_at is required when "
            "--opponent-statistics-file is used for historical review."
        )

    played_at_instant = parse_rfc3339_datetime(
        historical_game.played_at,
        f"Historical game '{historical_game.game_id}' played_at",
    )
    participant_ids = {player.player_id for player in historical_game.players}
    statistics_summary = build_opponent_statistics_summary(opponent_statistics)
    matched_records = {
        record["player_id"]: record
        for record in statistics_summary["records"]
        if record["player_id"] in participant_ids
    }
    if not matched_records:
        raise ValueError(
            f"No opponent-statistics records in '{statistics_input_file}' match the "
            f"participants in historical game '{historical_game.game_id}'."
        )

    profiles_by_player_id = {}
    for player_id, record in matched_records.items():
        profile = _build_matched_profile(record)
        captured_at = profile.source["captured_at"]
        captured_at_instant = parse_rfc3339_datetime(
            captured_at,
            f"Opponent-statistics player '{player_id}' source.captured_at",
        )
        if captured_at_instant >= played_at_instant:
            raise ValueError(
                f"Opponent-statistics player '{player_id}' captured_at '{captured_at}' "
                f"must be strictly before historical game played_at "
                f"'{historical_game.played_at}'."
            )
        profiles_by_player_id[player_id] = profile

    participant_matches = [
        _build_participant_summary(
            player.player_id,
            player.player_label,
            profiles_by_player_id.get(player.player_id),
        )
        for player in historical_game.players
    ]
    unmatched_player_ids = [
        player.player_id
        for player in historical_game.players
        if player.player_id not in profiles_by_player_id
    ]
    application_summary = {
        "enabled": True,
        "statistics_input_file": statistics_input_file,
        "game_id": historical_game.game_id,
        "played_at": historical_game.played_at,
        "temporal_rule": HISTORICAL_TEMPORAL_RULE,
        "participant_matches": participant_matches,
        "matched_player_count": len(profiles_by_player_id),
        "unmatched_player_ids": unmatched_player_ids,
    }
    return HistoricalOpponentProfileBindings(
        profiles_by_player_id=profiles_by_player_id,
        application_summary=application_summary,
    )
