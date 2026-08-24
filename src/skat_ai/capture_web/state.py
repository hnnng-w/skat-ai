from __future__ import annotations

from typing import Any

from skat_ai.deck import get_full_deck
from skat_ai.game_declaration import VALID_DECLARATION_GAME_TYPES
from skat_ai.match_analysis_contracts import (
    MatchAnalysisReportV1,
    MatchDecisionAnalysisResultV1,
    MatchHistoricalAnalysisResultV1,
    MatchMaterializationReportV1,
)
from skat_ai.match_capture_position_view import build_match_capture_position_view_v1
from skat_ai.match_decision_review_preparation import (
    build_match_decision_review_preparation_v1,
)
from skat_ai.match_historical_information_set_analysis import (
    build_match_historical_information_set_report_view_v1,
)
from skat_ai.match_historical_materialization import (
    materialize_match_observed_game_historical_v1,
)
from skat_ai.match_historical_tactical_motif_analysis import (
    build_match_historical_tactical_motif_report_view_v1,
)
from skat_ai.match_information_set_search import (
    build_match_information_set_search_report_view_v1,
)
from skat_ai.match_player_statistics_preparation import (
    MatchPlayerStatisticsPreparationV1,
    build_match_player_statistics_preparation_v1,
)
from skat_ai.match_workspace_contracts import MatchWorkspaceV1
from skat_ai.match_workspace_progress import build_match_workspace_progress_v1
from skat_ai.match_workspace_rotation import build_match_workspace_position_fact_v1

from .contracts import MATCH_CAPTURE_WEB_PROTOCOL_VERSION
from .report_store import MatchAnalysisReportStoreV1
from .timecodes import format_media_timecode_v1

_ORDERED_DECK = tuple(get_full_deck())
_SUIT_NAMES = {"C": "Clubs", "S": "Spades", "H": "Hearts", "D": "Diamonds"}
_RANK_NAMES = {
    "A": "Ace",
    "10": "Ten",
    "K": "King",
    "Q": "Queen",
    "J": "Jack",
    "9": "Nine",
    "8": "Eight",
    "7": "Seven",
}


def _card_summary(card: str, selectable: set[str]) -> dict[str, Any]:
    return {
        "code": card,
        "label": f"{_SUIT_NAMES[card[0]]} {_RANK_NAMES[card[1:]]}",
        "selectable": card in selectable,
    }


def _participant_summary(participant, context) -> dict[str, Any]:
    snapshot = participant.statistics_snapshot
    record = None if snapshot is None else snapshot.statistics_record
    derivation = context.profile_derivation
    return {
        "player_id": participant.player_id,
        "player_label": participant.player_label,
        "platform_player_id": participant.platform_player_id,
        "table_place": participant.table_place,
        "statistics_snapshot": (None if snapshot is None else snapshot.to_dict()),
        "statistics_source": None
        if record is None
        else snapshot.to_dict()["statistics_record"]["source"],
        "statistics_games_played": None if record is None else record.games_played,
        "statistics_percentages": (
            None if record is None else snapshot.to_dict()["statistics_record"]["statistics"]
        ),
        "statistics_exact_counts": (
            None
            if record is None or record.exact_counts is None
            else snapshot.to_dict()["statistics_record"]["exact_counts"]
        ),
        "statistics_temporal_status": context.temporal_status,
        "statistics_eligible_for_match_analysis": (context.eligible_for_match_analysis),
        "normalized_profile": (
            None if context.normalized_profile is None else context.to_dict()["normalized_profile"]
        ),
        "profile_confidence": (
            None if derivation is None else context.to_dict()["profile_derivation"]["confidence"]
        ),
        "profile_classification": (None if derivation is None else derivation.classification),
        "profile_derivation_status": (None if derivation is None else derivation.derivation_status),
        "recommended_policy_preset": (
            None if derivation is None else derivation.recommended_policy_preset
        ),
        "actionable_policy_preset": (
            None if derivation is None else derivation.actionable_policy_preset
        ),
        "profile_explanations": ([] if derivation is None else list(derivation.explanations)),
    }


def _game_summary(game) -> dict[str, Any] | None:
    if game is None:
        return None
    declaration = game.declaration
    return {
        "game_id": game.game_id,
        "game_timecode": format_media_timecode_v1(game.game_timecode),
        "perspective_initial_hand": (
            None if game.perspective_initial_hand is None else list(game.perspective_initial_hand)
        ),
        "declarer_player_id": game.declarer_player_id,
        "declaration": (
            None
            if declaration is None
            else {
                "game_type": declaration.game_type,
                "hand_game": declaration.hand_game,
                "ouvert": declaration.ouvert,
                "schneider_announced": declaration.schneider_announced,
                "schwarz_announced": declaration.schwarz_announced,
                "matadors": declaration.matadors,
                "bid_value": declaration.bid_value,
            }
        ),
        "original_skat": None if game.original_skat is None else list(game.original_skat),
        "discarded_cards": (None if game.discarded_cards is None else list(game.discarded_cards)),
        "plays": [
            {
                **play.to_dict(),
                "decision_timecode_text": format_media_timecode_v1(play.decision_timecode)["start"],
                "trick_number": ((play.decision_index - 1) // 3) + 1,
            }
            for play in game.plays
        ],
        "commentaries": [
            {
                **commentary.to_dict(),
                "commentary_timecode_text": format_media_timecode_v1(
                    commentary.commentary_timecode
                )["start"],
            }
            for commentary in game.commentaries
        ],
        "response_links": [link.to_dict() for link in game.response_links],
    }


def _decision_preparation_summary(workspace: MatchWorkspaceV1, position: int) -> dict[str, Any]:
    game = workspace.slots[position - 1].observed_game
    if game is None:
        return {
            "status": "unavailable",
            "source_play_count": 0,
            "prepared_decision_count": 0,
            "skipped_decision_count": 0,
            "decisions": [],
        }
    preparation = build_match_decision_review_preparation_v1(
        workspace,
        match_position=position,
    )
    prepared = {item.decision_index for item in preparation.snapshots}
    skipped = {item.decision_index: item.reason for item in preparation.skipped_decisions}
    return {
        "status": preparation.status,
        "source_play_count": preparation.source_play_count,
        "prepared_decision_count": preparation.prepared_decision_count,
        "skipped_decision_count": preparation.skipped_decision_count,
        "decisions": [
            {
                "decision_index": play.decision_index,
                "acting_player_id": play.player_id,
                "actual_card": play.card,
                "state": "prepared" if play.decision_index in prepared else "skipped",
                "reason": skipped.get(play.decision_index),
            }
            for play in game.plays
        ],
    }


def _historical_materialization_summary(
    workspace: MatchWorkspaceV1,
    position: int,
) -> dict[str, Any]:
    result = materialize_match_observed_game_historical_v1(
        workspace,
        match_position=position,
    )
    return {
        "status": result.status,
        "available": result.status == "available",
        "game_id": result.game_id,
        "unavailable_reason": result.unavailable_reason,
    }


def _profile_side_summary(
    binding: dict[str, Any],
    application: dict[str, Any] | None,
    side: str,
    *,
    use_profile_presets: bool,
    policy_settings: dict[str, Any],
) -> dict[str, Any]:
    applied = None if application is None else application.get(side)
    profile_available = binding[f"{side}_profile_available"]
    if applied is None and profile_available and not use_profile_presets:
        application_status = "not_requested"
        not_applied_reason = "profile_presets_disabled"
    elif applied is None:
        application_status = "not_requested"
        not_applied_reason = "ineligible_or_absent"
    else:
        application_status = applied.get("application_status")
        not_applied_reason = applied.get("not_applied_reason")
    return {
        "relative_player": side,
        "opponent_player_id": binding[f"{side}_opponent_player_id"],
        "temporal_status": binding[f"{side}_temporal_status"],
        "profile_available": profile_available,
        "actionable_policy_preset": binding[f"{side}_actionable_policy_preset"],
        "application_status": application_status,
        "not_applied_reason": not_applied_reason,
        "applied_policy_preset": (
            None if applied is None else applied.get("applied_policy_preset")
        ),
        "effective_lead_policy": (
            policy_settings.get("opponent_lead_policy")
            if applied is None
            else applied.get("effective_lead_policy")
        ),
        "effective_response_policy": (
            policy_settings.get("opponent_response_policy")
            if applied is None
            else applied.get("effective_response_policy")
        ),
    }


def _curate_search_comparison(value: object) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    actual = value.get("search_actual_card_comparison")
    immediate = value.get("search_vs_immediate_comparison")
    return {
        "search_actual_card_comparison": (
            None
            if not isinstance(actual, dict)
            else {
                key: actual.get(key)
                for key in (
                    "is_available",
                    "unavailable_reason",
                    "actual_card",
                    "search_recommended_card",
                    "actual_card_rank",
                    "recommended_card_rank",
                    "actual_card_is_best_aggregate",
                    "actual_card_is_aggregate_equivalent_to_recommendation",
                    "strictly_better_card_count",
                    "completed_world_count",
                    "comparison_basis",
                    "contract_success_rate_gap",
                    "mean_local_side_game_score_gap",
                    "mean_local_side_card_point_margin_gap",
                )
            }
        ),
        "search_vs_immediate_comparison": (
            None
            if not isinstance(immediate, dict)
            else {
                key: immediate.get(key)
                for key in (
                    "is_available",
                    "unavailable_reason",
                    "search_card",
                    "immediate_card",
                    "same_recommended_card",
                    "search_rank_of_immediate_card",
                    "immediate_rank_of_search_card",
                    "search_aggregate_relation",
                    "search_contract_success_rate_advantage",
                    "search_mean_game_score_advantage",
                    "search_mean_card_point_margin_advantage",
                )
            }
        ),
    }


def _decision_report_details(value: MatchDecisionAnalysisResultV1) -> dict[str, Any]:
    details: dict[str, Any] = {
        "status": value.status,
        "match_position": value.match_position,
        "game_id": value.game_id,
        "decision_index": value.decision_index,
        "unavailable_reason": value.unavailable_reason,
        "skipped_reason": value.skipped_reason,
    }
    if value.result is None or value.request is None or value.profile_binding is None:
        return details
    document = value.result.to_dict()["document"]
    request = value.request.to_dict()["document"]
    method = document.get("recommendation_method_summary") or {
        "requested_method": value.options.recommendation_method,
        "effective_method": value.options.recommendation_method,
        "search_attempted": False,
        "fallback_used": False,
        "fallback_method": None,
    }
    curated_method = {
        key: method.get(key)
        for key in (
            "requested_method",
            "effective_method",
            "search_attempted",
            "fallback_used",
            "fallback_method",
        )
    }
    recommendation = document.get("recommendation")
    search = document.get("bounded_search_result")
    curated_search = None
    if isinstance(search, dict):
        consumed = search.get("consumed_budget", {})
        curated_search = {
            "status": search.get("status"),
            "stop_reason": search.get("stop_reason"),
            "world_coverage": search.get("world_coverage"),
            "solution_claim": search.get("solution_claim"),
            "selected_world_count": consumed.get("selected_world_count"),
            "completed_world_count": consumed.get("completed_world_count"),
            "fallback_used": search.get("fallback_used"),
            "fallback_method": search.get("fallback_method"),
            "recommended_card": search.get("recommended_card"),
            "candidate_results": [
                {
                    key: item.get(key)
                    for key in (
                        "rank",
                        "card",
                        "local_contract_success_rate",
                        "mean_local_side_game_score",
                        "mean_local_side_card_point_margin",
                    )
                }
                for item in search.get("candidate_results", [])
                if isinstance(item, dict)
            ],
        }
    binding = value.profile_binding.to_dict()
    application = document.get("opponent_profile_application_summary")
    review = document.get("post_game_review_summary")
    curated_review = (
        None
        if not isinstance(review, dict)
        else {
            key: review.get(key)
            for key in (
                "is_available",
                "reason",
                "decision_quality",
                "decision_explanation",
            )
        }
    )
    details.update(
        {
            "acting_player_id": binding["acting_player_id"],
            "actual_card": request.get("actual_card_played"),
            "recommendation_method": curated_method,
            "recommendation": (
                None
                if not isinstance(recommendation, dict)
                else {
                    "card": recommendation.get("card"),
                    "reason": recommendation.get("reason"),
                }
            ),
            "legal_cards": document.get("legal_cards", []),
            "strategic_summary": document.get("strategic_summary"),
            "post_game_review": curated_review,
            "search_post_game_review": _curate_search_comparison(
                document.get("bounded_search_post_game_review_summary")
            ),
            "immediate_candidate_values": [
                {
                    key: item.get(key)
                    for key in (
                        "card",
                        "expected_point_swing",
                        "win_rate",
                        "is_recommended",
                    )
                }
                for item in document.get("analysis_report", [])
                if isinstance(item, dict)
            ],
            "bounded_search": curated_search,
            "information_set_search": (build_match_information_set_search_report_view_v1(document)),
            "profiles": {
                side: _profile_side_summary(
                    binding,
                    application,
                    side,
                    use_profile_presets=value.options.use_profile_presets,
                    policy_settings=document.get(
                        f"{side}_opponent_policy_settings",
                        {},
                    ),
                )
                for side in ("left", "right")
            },
        }
    )
    return details


def _coaching_assessment_summary(value: object) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    evidence = value.get("decision_time_evidence")
    return {
        "decision_index": (
            None if not isinstance(evidence, dict) else evidence.get("decision_index")
        ),
        "acting_player_id": (
            None if not isinstance(evidence, dict) else evidence.get("acting_player_id")
        ),
        "actual_card": value.get("actual_card"),
        "assessment_status": value.get("assessment_status"),
        "evidence_basis": value.get("evidence_basis"),
        "impact_tier": value.get("impact_tier"),
        "best_card": value.get("best_card"),
        "actual_card_rank": value.get("actual_card_rank"),
        "strictly_better_card_count": value.get("strictly_better_card_count"),
        "factors": value.get("factors", []),
        "limitations": value.get("limitations", []),
    }


def _curate_coaching_summary(coaching: dict[str, Any]) -> dict[str, Any]:
    coverage = coaching.get("coverage_summary")
    prioritization = coaching.get("prioritization")
    guidance = coaching.get("guidance")
    outcome = coaching.get("outcome_context")
    key_decisions = (
        [] if not isinstance(prioritization, dict) else prioritization.get("key_decisions", [])
    )
    turning_points = (
        [] if not isinstance(prioritization, dict) else prioritization.get("turning_points", [])
    )
    decision_recommendations = (
        [] if not isinstance(guidance, dict) else guidance.get("decision_recommendations", [])
    )
    pattern_recommendations = (
        [] if not isinstance(guidance, dict) else guidance.get("pattern_recommendations", [])
    )
    return {
        "report_method": coaching.get("report_method"),
        "coverage_summary": (
            None
            if not isinstance(coverage, dict)
            else {
                key: coverage.get(key)
                for key in (
                    "assessable_decision_count",
                    "not_assessable_count",
                    "high_impact_decision_count",
                )
            }
        ),
        "prioritization": {
            "key_decisions": [
                {
                    "rank": item.get("rank"),
                    "selection_reason": item.get("selection_reason"),
                    "primary_gap": item.get("primary_gap"),
                    "is_high_impact": item.get("is_high_impact"),
                    "turning_point_types": item.get("turning_point_types", []),
                    "assessment": _coaching_assessment_summary(item.get("assessment")),
                }
                for item in key_decisions
                if isinstance(item, dict)
            ],
            "turning_points": [
                {
                    key: item.get(key)
                    for key in (
                        "turning_point_type",
                        "decision_index",
                        "is_high_impact",
                        "recorded_state_before",
                        "recorded_state_after",
                        "decided_side",
                        "factors",
                        "limitations",
                    )
                }
                | {"assessment": _coaching_assessment_summary(item.get("assessment"))}
                for item in turning_points
                if isinstance(item, dict)
            ],
        },
        "guidance": {
            "decision_recommendations": [
                {
                    key: item.get(key)
                    for key in (
                        "rank",
                        "recommendation_type",
                        "title",
                        "explanation",
                        "action",
                        "factors",
                        "limitations",
                    )
                }
                for item in decision_recommendations
                if isinstance(item, dict)
            ],
            "pattern_recommendations": [
                {
                    key: item.get(key)
                    for key in (
                        "rank",
                        "recommendation_type",
                        "title",
                        "explanation",
                        "action",
                        "decision_indices",
                        "factors",
                        "limitations",
                    )
                }
                for item in pattern_recommendations
                if isinstance(item, dict)
            ],
        },
        "outcome_context": (
            None
            if not isinstance(outcome, dict)
            else {
                "game_result_summary": {
                    "winner": (outcome.get("game_result_summary") or {}).get("winner")
                },
                "final_settlement_summary": {
                    "settlement_score": (outcome.get("final_settlement_summary") or {}).get(
                        "settlement_score"
                    )
                },
            }
        ),
        "limitations": coaching.get("limitations", []),
    }


def _selected_fields(value: object, fields: tuple[str, ...]) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {field_name: value.get(field_name) for field_name in fields}


def _curate_historical_search_summary(search: dict[str, Any]) -> dict[str, Any]:
    performance = search.get("performance")
    performance_summary = _selected_fields(
        performance,
        ("fallback_count",),
    )
    for name in ("nodes_expanded", "completed_world_count"):
        metrics = None if not isinstance(performance, dict) else performance.get(name)
        performance_summary[name] = _selected_fields(metrics, ("total",))
    return {
        "decision_counts": _selected_fields(
            search.get("decision_counts"),
            ("search_attempted_count", "search_recommendation_count"),
        ),
        "status_counts": _selected_fields(
            search.get("status_counts"),
            ("complete", "partial", "timeout", "unavailable"),
        ),
        "coverage": _selected_fields(
            search.get("coverage"),
            (
                "exact_coverage_decision_count",
                "sampled_coverage_decision_count",
                "no_coverage_decision_count",
            ),
        ),
        "search_vs_immediate_agreement": _selected_fields(
            search.get("search_vs_immediate_agreement"),
            ("same_recommended_card_rate",),
        ),
        "quality_gate": _selected_fields(
            search.get("quality_gate"),
            ("quality_gate_passed", "quality_violation_count"),
        ),
        "actual_card_agreement": _selected_fields(
            search.get("actual_card_agreement"),
            ("actual_top_1_rate",),
        ),
        "performance": performance_summary,
    }


def _historical_report_details(value: MatchHistoricalAnalysisResultV1) -> dict[str, Any]:
    details: dict[str, Any] = {
        "status": value.status,
        "match_position": value.match_position,
        "game_id": value.game_id,
        "unavailable_reason": value.unavailable_reason,
    }
    if value.result is None:
        return details
    document = value.result.to_dict()["document"]
    summary = document["historical_game_summary"]
    record = summary["record"]
    snapshots = summary.get("decision_snapshot_summary")
    review = summary.get("historical_game_review_summary")
    search = summary.get("historical_search_review_summary")
    coaching = summary.get("historical_replay_coaching_summary")
    information_set = build_match_historical_information_set_report_view_v1(summary)
    tactical_motif_review = build_match_historical_tactical_motif_report_view_v1(summary)
    declaration = record.get("declaration")
    game_result = summary.get("game_result_summary")
    game_value = summary.get("game_value_summary")
    overbid = summary.get("overbid_summary")
    settlement = summary.get("final_settlement_summary")
    details.update(
        {
            "declarer_player_id": record.get("declarer_player_id"),
            "declaration": (
                None
                if not isinstance(declaration, dict)
                else {
                    key: declaration.get(key)
                    for key in (
                        "game_type",
                        "hand_game",
                        "ouvert",
                        "bid_value",
                    )
                }
            ),
            "status": summary.get("status"),
            "winner": summary.get("winner"),
            "declarer_points": summary.get("declarer_points"),
            "defender_points": summary.get("defender_points"),
            "game_result": (
                None if not isinstance(game_result, dict) else {"winner": game_result.get("winner")}
            ),
            "game_value": (
                None
                if not isinstance(game_value, dict)
                else {"game_value": game_value.get("game_value")}
            ),
            "overbid": (
                None if not isinstance(overbid, dict) else {"status": overbid.get("status")}
            ),
            "settlement": (
                None
                if not isinstance(settlement, dict)
                else {
                    "settlement_score": settlement.get("settlement_score"),
                    "is_complete": settlement.get("is_complete"),
                }
            ),
            "decision_snapshots": (
                None
                if snapshots is None
                else {
                    "snapshot_count": snapshots.get("snapshot_count"),
                    "game_end_reason": snapshots.get("game_end_reason"),
                }
            ),
            "immediate_review": (
                None
                if review is None
                else {
                    "decision_count": review.get("decision_count"),
                    "reviewed_decision_count": review.get("reviewed_decision_count"),
                    "unavailable_decision_count": review.get("unavailable_decision_count"),
                    "quality_counts": _selected_fields(
                        review.get("quality_counts"),
                        ("optimal", "acceptable", "suboptimal", "mistake"),
                    ),
                }
            ),
            "search_review": (
                None if search is None else _curate_historical_search_summary(search)
            ),
            "replay_coaching": (None if coaching is None else _curate_coaching_summary(coaching)),
            "tactical_motif_review": tactical_motif_review,
            **information_set,
            "profile_application": (
                None
                if document.get("historical_opponent_profile_application_summary") is None
                else {
                    key: document["historical_opponent_profile_application_summary"].get(key)
                    for key in (
                        "game_id",
                        "temporal_rule",
                        "matched_player_count",
                        "unmatched_player_ids",
                    )
                }
                | {
                    "participant_matches": [
                        {
                            key: item.get(key)
                            for key in (
                                "player_id",
                                "match_status",
                                "temporal_status",
                                "derivation_status",
                                "actionable_policy_preset",
                            )
                        }
                        for item in document["historical_opponent_profile_application_summary"].get(
                            "participant_matches", []
                        )
                        if isinstance(item, dict)
                    ]
                }
            ),
        }
    )
    return details


def _materialization_report_details(value: MatchMaterializationReportV1) -> dict[str, Any]:
    materialization = value.materialization
    slots = materialization.slot_materializations
    historical_unavailable = [
        {
            "match_position": item.match_position,
            "reason": item.historical_materialization.unavailable_reason,
        }
        for item in slots
        if item.historical_materialization.status == "unavailable"
    ]
    list_value = materialization.historical_list_materialization.to_dict()
    aggregation = list_value["aggregation"]

    def curated_standings(items: object) -> list[dict[str, Any]]:
        if not isinstance(items, list):
            return []
        return [
            {
                "rank": item.get("rank"),
                "player_totals": _selected_fields(
                    item.get("player_totals"),
                    (
                        "player_id",
                        "total_performance_points",
                        "player_game_points",
                        "own_games_won",
                        "own_games_lost",
                    ),
                ),
            }
            for item in items
            if isinstance(item, dict)
        ]

    return {
        "status": materialization.status,
        "occupied_slot_count": sum(item.slot_kind != "empty" for item in slots),
        "empty_slot_count": sum(item.slot_kind == "empty" for item in slots),
        "observed_game_count": sum(item.slot_kind == "observed_game" for item in slots),
        "passed_deal_count": materialization.passed_deal_count,
        "prepared_decision_count": materialization.prepared_decision_count,
        "skipped_decision_count": materialization.skipped_decision_count,
        "historical_game_count": materialization.historical_game_count,
        "training_record_count": materialization.training_record_count,
        "commentary_count": materialization.commentary_count,
        "response_link_count": materialization.response_link_count,
        "historical_unavailable": historical_unavailable,
        "historical_list": {
            "status": list_value["status"],
            "unavailable_reason": list_value["unavailable_reason"],
            "unavailable_positions": list_value["unavailable_positions"],
            "ranking_status": None if aggregation is None else aggregation["ranking_status"],
            "lot_required_player_ids": (
                [] if aggregation is None else aggregation["lot_required_player_ids"]
            ),
            "applied_lot_order": (
                None if aggregation is None else aggregation["applied_lot_order"]
            ),
            "final_standings": (
                [] if aggregation is None else curated_standings(aggregation["final_standings"])
            ),
            "round_end_progression": (
                []
                if aggregation is None
                else [
                    {
                        "entry_fact": _selected_fields(
                            item.get("entry_fact"),
                            ("round_number", "entry_number"),
                        ),
                        "provisional_standings": curated_standings(
                            item.get("provisional_standings")
                        ),
                    }
                    for item in aggregation["progression"][2::3]
                    if isinstance(item, dict)
                ]
            ),
        },
    }


def build_match_analysis_report_summary_v1(
    report: MatchAnalysisReportV1,
    *,
    selected: bool = False,
) -> dict[str, Any]:
    value = report.value
    if type(value) is MatchMaterializationReportV1:
        status = value.materialization.status
    else:
        status = value.status
    return {
        "report_id": report.report_id,
        "report_kind": report.report_kind,
        "match_id": report.match_id,
        "workspace_revision": report.workspace_revision,
        "match_position": report.match_position,
        "decision_index": report.decision_index,
        "status": status,
        "selected": selected,
    }


def _selected_report_details(report: MatchAnalysisReportV1) -> dict[str, Any]:
    summary = build_match_analysis_report_summary_v1(report, selected=True)
    value = report.value
    if type(value) is MatchMaterializationReportV1:
        details = _materialization_report_details(value)
    elif type(value) is MatchDecisionAnalysisResultV1:
        details = _decision_report_details(value)
    else:
        details = _historical_report_details(value)
    return {**summary, "details": details}


def build_match_capture_web_state_v1(
    workspace: MatchWorkspaceV1 | None,
    *,
    workspace_filename: str,
    selected_position: int = 1,
    statistics_preparation: MatchPlayerStatisticsPreparationV1 | None = None,
    report_store: MatchAnalysisReportStoreV1 | None = None,
    selected_report_id: str | None = None,
) -> dict[str, Any]:
    """Builds deterministic private browser state without paths or fingerprints."""
    if type(selected_position) is not int or not 1 <= selected_position <= 36:
        raise ValueError("selected_position must be an integer from 1 through 36.")
    base: dict[str, Any] = {
        "match_capture_web_protocol_version": MATCH_CAPTURE_WEB_PROTOCOL_VERSION,
        "workspace_exists": workspace is not None,
        "workspace_filename": workspace_filename,
        "selected_position": selected_position,
        "reports": [],
        "selected_report_id": None,
        "selected_report": None,
        "materialization_report_id": None,
        "materialization_available": False,
        "materialization_report": None,
        "download_availability": {
            "report_result": False,
            "materialization": False,
            "historical_games": False,
            "training_sources": False,
            "historical_list_input": False,
            "historical_list_aggregation": False,
        },
    }
    if workspace is None:
        return {
            **base,
            "creation_defaults": {
                "game_platform": "EuroSkat",
                "source_kind": "youtube_video",
                "tournament_format_id": "euroskat_36_standard_v1",
                "perspective_player_id": "",
            },
        }

    definition = workspace.match_definition
    if statistics_preparation is None:
        statistics_preparation = build_match_player_statistics_preparation_v1(definition)
    elif (
        type(statistics_preparation) is not MatchPlayerStatisticsPreparationV1
        or statistics_preparation.match_id != definition.match_id
        or statistics_preparation.match_played_at != definition.played_at
        or tuple(context.player_id for context in statistics_preparation.participant_contexts)
        != tuple(participant.player_id for participant in definition.participants)
        or tuple(context.snapshot_id for context in statistics_preparation.participant_contexts)
        != tuple(
            None
            if participant.statistics_snapshot is None
            else participant.statistics_snapshot.snapshot_id
            for participant in definition.participants
        )
    ):
        raise ValueError("statistics_preparation must describe the supplied Match definition.")
    progress = build_match_workspace_progress_v1(workspace)
    selected_slot = workspace.slots[selected_position - 1]
    view = build_match_capture_position_view_v1(
        workspace,
        match_position=selected_position,
    )
    first_empty = progress.next_empty_position
    slot_summaries = []
    for slot in workspace.slots:
        fact = build_match_workspace_position_fact_v1(workspace, slot.match_position)
        game = slot.observed_game
        slot_summaries.append(
            {
                **fact.to_dict(),
                "game_state": build_match_capture_position_view_v1(
                    workspace,
                    match_position=slot.match_position,
                ).game_state,
                "commentary_count": 0 if game is None else len(game.commentaries),
                "first_empty": slot.match_position == first_empty,
                "selected": slot.match_position == selected_position,
            }
        )
    selectable = set(view.selectable_cards)
    current_reports = (
        ()
        if report_store is None
        else tuple(
            report
            for report in report_store.list()
            if report.match_id == definition.match_id
            and report.workspace_revision == workspace.revision
        )
    )
    selected_report = next(
        (report for report in current_reports if report.report_id == selected_report_id),
        None,
    )
    materialization_report = next(
        (report for report in reversed(current_reports) if report.report_kind == "materialization"),
        None,
    )
    materialization_available = materialization_report is not None
    list_available = (
        materialization_available
        and type(materialization_report.value) is MatchMaterializationReportV1
        and materialization_report.value.materialization.historical_list_materialization.status
        == "available"
    )
    return {
        **base,
        "match": {
            "match_id": definition.match_id,
            "title": definition.title,
            "game_platform": definition.game_platform,
            "external_match_id": definition.external_match_id,
            "played_at": definition.played_at,
            "tournament_format_id": definition.tournament_format.format_id,
        },
        "source": {
            "source_kind": definition.source.source_kind,
            "source_url": definition.source.source_url,
            "source_title": definition.source.source_title,
            "source_channel_name": definition.source.source_channel_name,
            "match_timecode": format_media_timecode_v1(definition.source.match_timecode),
        },
        "participants": [
            _participant_summary(participant, context)
            for participant, context in zip(
                definition.participants,
                statistics_preparation.participant_contexts,
                strict=True,
            )
        ],
        "player_statistics_preparation": statistics_preparation.to_dict(),
        "perspective_player_id": definition.perspective_player_id,
        "workspace_revision": workspace.revision,
        "progress": progress.to_dict(),
        "slots": slot_summaries,
        "selected_slot": selected_slot.to_dict(),
        "position_view": view.to_dict(),
        "game": _game_summary(selected_slot.observed_game),
        "decision_preparation": _decision_preparation_summary(
            workspace,
            selected_position,
        ),
        "historical_materialization": _historical_materialization_summary(
            workspace,
            selected_position,
        ),
        "reports": [
            build_match_analysis_report_summary_v1(
                report,
                selected=report is selected_report,
            )
            for report in current_reports
        ],
        "selected_report_id": (None if selected_report is None else selected_report.report_id),
        "selected_report": (
            None if selected_report is None else _selected_report_details(selected_report)
        ),
        "materialization_report_id": (
            None if materialization_report is None else materialization_report.report_id
        ),
        "materialization_available": materialization_available,
        "materialization_report": (
            None
            if materialization_report is None
            else build_match_analysis_report_summary_v1(materialization_report)
        ),
        "download_availability": {
            "report_result": (
                selected_report is not None
                and selected_report.report_kind != "materialization"
                and selected_report.value.status == "executed"
            ),
            "materialization": materialization_available,
            "historical_games": materialization_available,
            "training_sources": materialization_available,
            "historical_list_input": list_available,
            "historical_list_aggregation": list_available,
        },
        "declaration_options": list(VALID_DECLARATION_GAME_TYPES),
        "card_palette": [_card_summary(card, selectable) for card in _ORDERED_DECK],
    }
