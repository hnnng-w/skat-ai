from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any

from skatmind.errors import SkatMindInvariantError
from skatmind.tactical_motif_contracts import (
    HISTORICAL_TACTICAL_MOTIF_REVIEW_METHOD,
    HISTORICAL_TACTICAL_MOTIF_REVIEW_VERSION,
    MATCH_HISTORICAL_TACTICAL_MOTIF_INTEGRATION_VERSION,
    TACTICAL_MOTIF_INFORMATION_POLICY,
)

if TYPE_CHECKING:
    from skatmind.match_analysis_contracts import MatchHistoricalAnalysisOptionsV1


def reconcile_match_historical_tactical_motif_result_v1(
    historical_summary: Mapping[str, object],
    *,
    game_id: str,
    options: MatchHistoricalAnalysisOptionsV1,
) -> None:
    """Checks the requested tactical attachment without rebuilding evidence."""
    attachment_name = "historical_tactical_motif_review_summary"
    attachment = historical_summary.get(attachment_name)
    if not options.tactical_motif_review:
        if attachment is not None:
            raise SkatMindInvariantError(
                f"Match Historical Result unexpectedly contains {attachment_name}."
            )
        return
    if not isinstance(attachment, Mapping):
        raise SkatMindInvariantError(
            f"Match Historical Result omitted requested {attachment_name}."
        )
    if (
        attachment.get("historical_tactical_motif_review_version")
        != HISTORICAL_TACTICAL_MOTIF_REVIEW_VERSION
        or attachment.get("review_method")
        != HISTORICAL_TACTICAL_MOTIF_REVIEW_METHOD
        or attachment.get("information_policy")
        != TACTICAL_MOTIF_INFORMATION_POLICY
        or attachment.get("source_game_id") != game_id
    ):
        raise SkatMindInvariantError(
            "Match Historical Tactical Motif Result changed contract or Game identity."
        )


def _selected_rows(
    value: object,
    field_names: tuple[str, ...],
) -> list[dict[str, Any]]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return []
    return [
        {field_name: item.get(field_name) for field_name in field_names}
        for item in value
        if isinstance(item, Mapping)
    ]


def _curate_observations(value: object) -> list[dict[str, Any]]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return []
    observations = []
    for item in value:
        if not isinstance(item, Mapping):
            continue
        facts = item.get("decision_time_facts")
        motifs = item.get("motifs")
        observations.append(
            {
                "decision_index": (
                    facts.get("decision_index")
                    if isinstance(facts, Mapping)
                    else None
                ),
                "trick_number": (
                    facts.get("trick_number")
                    if isinstance(facts, Mapping)
                    else None
                ),
                "play_index": (
                    facts.get("play_index")
                    if isinstance(facts, Mapping)
                    else None
                ),
                "acting_player_id": (
                    facts.get("acting_player_id")
                    if isinstance(facts, Mapping)
                    else None
                ),
                "acting_side": (
                    facts.get("acting_side")
                    if isinstance(facts, Mapping)
                    else None
                ),
                "actual_card": item.get("actual_card"),
                "observation_status": item.get("observation_status"),
                "motifs": _selected_rows(
                    motifs,
                    ("motif_type", "motif_family", "evidence_time"),
                ),
            }
        )
    return observations


def build_match_historical_tactical_motif_report_view_v1(
    historical_summary: Mapping[str, object],
) -> dict[str, Any] | None:
    """Returns only tactical fields explicitly rendered by the local browser."""
    value = historical_summary.get("historical_tactical_motif_review_summary")
    if not isinstance(value, Mapping):
        return None
    return {
        "review_method": value.get("review_method"),
        "source_game_id": value.get("source_game_id"),
        "observation_count": value.get("observation_count"),
        "complete_observation_count": value.get("complete_observation_count"),
        "partial_observation_count": value.get("partial_observation_count"),
        "motif_occurrence_count": value.get("motif_occurrence_count"),
        "motif_counts": _selected_rows(
            value.get("motif_counts"),
            ("motif_type", "count"),
        ),
        "family_counts": _selected_rows(
            value.get("family_counts"),
            ("motif_family", "count"),
        ),
        "player_summaries": _selected_rows(
            value.get("player_summaries"),
            (
                "scope_value",
                "observation_count",
                "complete_observation_count",
                "partial_observation_count",
                "motif_occurrence_count",
            ),
        ),
        "observations": _curate_observations(value.get("observations")),
        "limitations": [
            limitation
            for limitation in value.get("limitations", ())
            if isinstance(limitation, str)
        ],
    }


__all__ = (
    "MATCH_HISTORICAL_TACTICAL_MOTIF_INTEGRATION_VERSION",
    "build_match_historical_tactical_motif_report_view_v1",
    "reconcile_match_historical_tactical_motif_result_v1",
)
