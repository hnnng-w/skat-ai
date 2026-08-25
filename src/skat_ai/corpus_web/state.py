from __future__ import annotations

from typing import Any

from skat_ai.match_analysis_contracts import MatchDecisionAnalysisResultV1

from .context import LearningCorpusWebContextV1
from .contracts import LEARNING_CORPUS_WEB_VERSION


def _prepared_state(context: LearningCorpusWebContextV1) -> dict[str, Any] | None:
    prepared = context.prepared_artifacts
    tactical = context.tactical_prepared_artifacts
    coaching = context.tactical_coaching_prepared_artifacts
    if prepared is None or tactical is None or coaching is None:
        return None
    dataset = prepared.learning_dataset
    summary = prepared.cross_game_summary
    readiness = {
        item.mode: {
            "status": item.status,
            "unavailable_reason": item.unavailable_reason,
        }
        for item in summary.readiness_summary.partition_readiness
    }
    player_conflicts = {player.player_id: 0 for player in prepared.player_catalog.players}
    for conflict in prepared.player_catalog.platform_alias_conflicts:
        for player_id in conflict.player_ids:
            player_conflicts[player_id] += 1
    return {
        "dataset_id": prepared.dataset_id,
        "dataset_status": dataset.status,
        "observed_decision_count": dataset.observed_decision_count,
        "record_count": dataset.record_count,
        "skipped_decision_count": dataset.skipped_decision_count,
        "strategy_teacher_evidence_count": dataset.strategy_teacher_evidence_count,
        "commentary_evidence_count": dataset.commentary_evidence_count,
        "response_evidence_count": dataset.response_evidence_count,
        "known_player": readiness["known_player"],
        "unseen_player": readiness["unseen_player"],
        "cross_game_match_count": len(summary.match_summaries),
        "cross_game_player_count": summary.player_count,
        "tactical_collection_status": tactical.tactical_motif_collection.status,
        "tactical_evidence_count": tactical.tactical_motif_collection.evidence_count,
        "tactical_skipped_decision_count": (
            tactical.tactical_motif_collection.skipped_decision_count
        ),
        "tactical_motif_occurrence_count": (
            tactical.tactical_motif_collection.motif_occurrence_count
        ),
        "tactical_cross_game_player_count": len(
            tactical.tactical_motif_cross_game_summary.player_summaries
        ),
        "tactical_cross_game_recurrence_count": len(
            tactical.tactical_motif_cross_game_summary.recurrences
        ),
        "tactical_coaching_status": coaching.tactical_cross_game_coaching_report.status,
        "tactical_coaching_decision_count": (
            coaching.tactical_cross_game_coaching_report.decision_summary_count
        ),
        "tactical_coaching_teacher_assessment_count": (
            coaching.tactical_cross_game_coaching_report.teacher_assessment_count
        ),
        "tactical_coaching_focus_area_count": (
            coaching.tactical_cross_game_coaching_report.focus_area_count
        ),
        "tactical_coaching_player_with_focus_count": (
            coaching.tactical_cross_game_coaching_report.player_with_focus_count
        ),
        "players": [
            {
                "player_id": player.player_id,
                "observed_labels": list(player.observed_labels),
                "match_count": player.match_count,
                "alias_conflict_count": player_conflicts[player.player_id],
                "statistics_observation_count": player.statistics_observation_count,
            }
            for player in prepared.player_catalog.players
        ],
        "player_count": prepared.player_catalog.player_count,
        "platform_alias_conflict_count": len(prepared.player_catalog.platform_alias_conflicts),
    }


def build_learning_corpus_web_state_v1(
    context: LearningCorpusWebContextV1,
) -> dict[str, Any]:
    """Builds one minimized path-free dashboard projection."""
    if type(context) is not LearningCorpusWebContextV1:
        raise ValueError("context must be an exact LearningCorpusWebContextV1.")
    with context.lock:
        store = context.store
        if store is None:
            return {
                "learning_corpus_web_version": LEARNING_CORPUS_WEB_VERSION,
                "initialized": False,
                "corpus": None,
                "matches": [],
                "current_match_snapshots": [],
                "strategy_sources": [],
                "prepared": None,
            }

        catalog = store.document.catalog
        current_by_match = {
            selection.match_id: selection.match_snapshot_id for selection in catalog.current_matches
        }
        entries_by_match: dict[str, list[Any]] = {}
        for entry in catalog.match_snapshots:
            entries_by_match.setdefault(entry.match_id, []).append(entry)
        matches = []
        for match_id, entries in entries_by_match.items():
            current_id = current_by_match.get(match_id)
            current_entry = next(
                (entry for entry in entries if entry.match_snapshot_id == current_id),
                None,
            )
            matches.append(
                {
                    "match_id": match_id,
                    "current_match_snapshot_id": current_id,
                    "current_workspace_revision": (
                        None if current_entry is None else current_entry.workspace_revision
                    ),
                    "observed_game_count": (
                        0 if current_entry is None else current_entry.observed_game_count
                    ),
                    "decision_count": 0 if current_entry is None else current_entry.decision_count,
                    "commentary_count": (
                        0 if current_entry is None else current_entry.commentary_count
                    ),
                    "response_count": (
                        0 if current_entry is None else current_entry.response_link_count
                    ),
                    "snapshots": [
                        {
                            "match_snapshot_id": entry.match_snapshot_id,
                            "workspace_revision": entry.workspace_revision,
                            "current": entry.match_snapshot_id == current_id,
                            "observed_game_count": entry.observed_game_count,
                            "decision_count": entry.decision_count,
                            "commentary_count": entry.commentary_count,
                            "response_count": entry.response_link_count,
                        }
                        for entry in entries
                    ],
                }
            )

        strategy_sources = []
        for source, binding_status in context.strategy_source_store.classified_sources(store):
            value = source.report.value
            if type(value) is not MatchDecisionAnalysisResultV1:
                raise RuntimeError("Strategy source store contains a non-Decision report.")
            strategy_sources.append(
                {
                    "source_binding_id": source.source_binding_id,
                    "source_report_id": source.source_report_id,
                    "match_snapshot_id": source.match_snapshot_id,
                    "match_id": value.match_id,
                    "match_position": value.match_position,
                    "decision_index": value.decision_index,
                    "recommendation_method": value.options.recommendation_method,
                    "binding_status": binding_status,
                }
            )

        return {
            "learning_corpus_web_version": LEARNING_CORPUS_WEB_VERSION,
            "initialized": True,
            "corpus": {
                "corpus_id": catalog.corpus_id,
                "catalog_revision": catalog.revision,
                "logical_match_count": len(entries_by_match),
                "retained_match_snapshot_count": len(catalog.match_snapshots),
                "current_match_snapshot_count": len(catalog.current_matches),
                "orphan_match_snapshot_count": len(store.orphan_match_snapshot_ids),
            },
            "matches": matches,
            "current_match_snapshots": [
                {
                    "match_id": selection.match_id,
                    "match_snapshot_id": selection.match_snapshot_id,
                }
                for selection in catalog.current_matches
            ],
            "strategy_sources": strategy_sources,
            "prepared": _prepared_state(context),
        }
