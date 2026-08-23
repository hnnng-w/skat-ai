from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any

from skat_ai.application.contracts import HistoricalGameApplicationOptions
from skat_ai.errors import SkatAIInvariantError

if TYPE_CHECKING:
    from skat_ai.match_analysis_contracts import MatchHistoricalAnalysisOptionsV1


MATCH_HISTORICAL_INFORMATION_SET_COACHING_INTEGRATION_VERSION = 1

MATCH_HISTORICAL_INFORMATION_SET_COACHING_POLICY = (
    "one_historical_application_with_shared_information_set_review"
)
MATCH_HISTORICAL_INFORMATION_SET_MODE_POLICY = (
    "separate_from_existing_pimc_replay_coaching"
)


def uses_match_historical_information_set_family_v1(
    options: MatchHistoricalAnalysisOptionsV1,
) -> bool:
    return (
        options.information_set_search_review
        or options.information_set_replay_coaching
    )


def build_match_historical_application_options_v1(
    options: MatchHistoricalAnalysisOptionsV1,
    *,
    inject_statistics: bool,
) -> HistoricalGameApplicationOptions:
    """Maps private Match controls to one existing Historical invocation."""
    has_review = (
        options.immediate_review
        or options.search_review
        or options.information_set_search_review
        or options.replay_coaching
        or options.information_set_replay_coaching
    )
    return HistoricalGameApplicationOptions(
        decision_snapshots=options.decision_snapshots,
        immediate_review=options.immediate_review,
        search_review=options.search_review,
        information_set_search_review=options.information_set_search_review,
        information_set_replay_coaching=(
            options.information_set_replay_coaching
        ),
        replay_coaching=options.replay_coaching,
        search_seed=options.search_random_seed,
        search_budget_profile=options.search_budget_profile,
        immediate_sample_count=(
            options.immediate_sample_count if has_review else None
        ),
        immediate_base_random_seed=(
            options.immediate_random_seed if has_review else None
        ),
        use_profile_presets_override=(
            options.use_profile_presets if inject_statistics else False
        ),
    )


def reconcile_match_historical_information_set_result_v1(
    historical_summary: Mapping[str, object],
    *,
    game_id: str,
    options: MatchHistoricalAnalysisOptionsV1,
) -> None:
    """Checks requested public attachments without recomputing any analysis."""
    expected = {
        "historical_information_set_search_review_summary": (
            options.information_set_search_review
        ),
        "historical_information_set_replay_coaching_summary": (
            options.information_set_replay_coaching
        ),
    }
    for attachment_name, requested in expected.items():
        attachment = historical_summary.get(attachment_name)
        if not requested:
            if attachment is not None:
                raise SkatAIInvariantError(
                    f"Match Historical Result unexpectedly contains {attachment_name}."
                )
            continue
        if not isinstance(attachment, Mapping):
            raise SkatAIInvariantError(
                f"Match Historical Result omitted requested {attachment_name}."
            )
        if attachment.get("source_game_id") != game_id:
            raise SkatAIInvariantError(
                f"Match Historical {attachment_name} changed Game identity."
            )


def _selected_fields(
    value: object,
    field_names: tuple[str, ...],
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    return {field_name: value.get(field_name) for field_name in field_names}


def _selected_rows(
    value: object,
    field_names: tuple[str, ...],
) -> list[dict[str, Any]]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return []
    return [
        _selected_fields(item, field_names)
        for item in value
        if isinstance(item, Mapping)
    ]


def _curate_information_set_review(
    value: object,
) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    agreement_fields = (
        "comparable_decision_count",
        "same_card_count",
        "different_card_count",
    )
    return {
        "review_method": value.get("review_method"),
        "source_game_id": value.get("source_game_id"),
        "decision_count": value.get("decision_count"),
        "status_counts": _selected_fields(
            value.get("status_counts"),
            ("complete", "partial", "timeout", "unavailable", "not_available"),
        ),
        "coverage_counts": _selected_fields(
            value.get("coverage_counts"),
            (
                "none",
                "single_exact_world",
                "all_compatible_worlds",
                "sampled_compatible_worlds",
            ),
        ),
        "selected_world_count_total": value.get("selected_world_count_total"),
        "sampled_world_count_total": value.get("sampled_world_count_total"),
        "comparison_available_count": value.get("comparison_available_count"),
        "comparison_unavailable_count": value.get("comparison_unavailable_count"),
        "information_set_recommendation_count": value.get(
            "information_set_recommendation_count"
        ),
        "information_set_pimc_agreement": _selected_fields(
            value.get("information_set_pimc_agreement"), agreement_fields
        ),
        "information_set_immediate_agreement": _selected_fields(
            value.get("information_set_immediate_agreement"), agreement_fields
        ),
        "information_set_actual_agreement": _selected_fields(
            value.get("information_set_actual_agreement"), agreement_fields
        ),
    }


def _curate_assessment(value: object) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    evidence = value.get("decision_time_evidence")
    return {
        "decision_index": (
            evidence.get("decision_index") if isinstance(evidence, Mapping) else None
        ),
        "acting_player_id": (
            evidence.get("acting_player_id") if isinstance(evidence, Mapping) else None
        ),
        "actual_card": value.get("actual_card"),
        "assessment_status": value.get("assessment_status"),
        "evidence_basis": value.get("evidence_basis"),
        "impact_tier": value.get("impact_tier"),
        "best_card": value.get("best_card"),
        "actual_card_rank": value.get("actual_card_rank"),
        "strictly_better_card_count": value.get("strictly_better_card_count"),
        "factors": list(value.get("factors", [])),
        "limitations": list(value.get("limitations", [])),
    }


def _curate_information_set_coaching(
    value: object,
) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    coverage = value.get("coverage")
    prioritization = value.get("prioritization")
    guidance = value.get("guidance")
    outcome = value.get("outcome_context")
    key_decisions = (
        prioritization.get("key_decisions", [])
        if isinstance(prioritization, Mapping)
        else []
    )
    turning_points = (
        prioritization.get("turning_points", [])
        if isinstance(prioritization, Mapping)
        else []
    )
    decision_recommendations = (
        guidance.get("decision_recommendations", [])
        if isinstance(guidance, Mapping)
        else []
    )
    pattern_recommendations = (
        guidance.get("pattern_recommendations", [])
        if isinstance(guidance, Mapping)
        else []
    )
    curated_coverage = _selected_fields(
        coverage,
        (
            "decision_count",
            "assessable_decision_count",
            "forced_move_count",
            "best_or_equivalent_count",
            "strictly_below_best_count",
            "not_assessable_count",
            "high_impact_decision_count",
            "key_decision_count",
            "turning_point_count",
            "pattern_count",
            "actionable_pattern_count",
            "decision_recommendation_count",
            "pattern_recommendation_count",
            "information_set_recommendation_count",
            "pimc_recommendation_count",
            "immediate_recommendation_count",
        ),
    )
    if isinstance(coverage, Mapping):
        curated_coverage.update(
            {
                "assessment_status_counts": _selected_rows(
                    coverage.get("assessment_status_counts"),
                    ("assessment_status", "count"),
                ),
                "evidence_basis_counts": _selected_rows(
                    coverage.get("evidence_basis_counts"),
                    ("evidence_basis", "count"),
                ),
                "information_set_status_counts": _selected_rows(
                    coverage.get("information_set_status_counts"),
                    ("information_set_status", "count"),
                ),
                "world_coverage_counts": _selected_rows(
                    coverage.get("world_coverage_counts"),
                    ("world_coverage", "count"),
                ),
                "information_set_pimc_agreement_counts": _selected_rows(
                    coverage.get("information_set_pimc_agreement_counts"),
                    ("agreement", "count"),
                ),
                "information_set_immediate_agreement_counts": _selected_rows(
                    coverage.get("information_set_immediate_agreement_counts"),
                    ("agreement", "count"),
                ),
            }
        )
    return {
        "report_method": value.get("report_method"),
        "source_game_id": value.get("source_game_id"),
        "coverage": curated_coverage,
        "prioritization": {
            "key_decisions": [
                {
                    "rank": item.get("rank"),
                    "selection_reason": item.get("selection_reason"),
                    "primary_gap": item.get("primary_gap"),
                    "is_high_impact": item.get("is_high_impact"),
                    "turning_point_types": list(item.get("turning_point_types", [])),
                    "assessment": _curate_assessment(item.get("assessment")),
                }
                for item in key_decisions
                if isinstance(item, Mapping)
            ],
            "turning_points": [
                _selected_fields(
                    item,
                    (
                        "turning_point_type",
                        "decision_index",
                        "is_high_impact",
                        "recorded_state_before",
                        "recorded_state_after",
                        "decided_side",
                        "factors",
                        "limitations",
                    ),
                )
                | {"assessment": _curate_assessment(item.get("assessment"))}
                for item in turning_points
                if isinstance(item, Mapping)
            ],
        },
        "guidance": {
            "decision_recommendations": [
                _selected_fields(
                    item,
                    (
                        "rank",
                        "recommendation_type",
                        "title",
                        "explanation",
                        "action",
                        "factors",
                        "limitations",
                    ),
                )
                for item in decision_recommendations
                if isinstance(item, Mapping)
            ],
            "pattern_recommendations": [
                _selected_fields(
                    item,
                    (
                        "rank",
                        "recommendation_type",
                        "title",
                        "explanation",
                        "action",
                        "decision_indices",
                        "factors",
                        "limitations",
                    ),
                )
                for item in pattern_recommendations
                if isinstance(item, Mapping)
            ],
        },
        "outcome_context": (
            None
            if not isinstance(outcome, Mapping)
            else {
                "game_result_summary": {
                    "winner": (
                        outcome.get("game_result_summary", {}).get("winner")
                        if isinstance(outcome.get("game_result_summary"), Mapping)
                        else None
                    )
                },
                "final_settlement_summary": {
                    "settlement_score": (
                        outcome.get("final_settlement_summary", {}).get(
                            "settlement_score"
                        )
                        if isinstance(
                            outcome.get("final_settlement_summary"), Mapping
                        )
                        else None
                    )
                },
            }
        ),
        "limitations": list(value.get("limitations", [])),
    }


def build_match_historical_information_set_report_view_v1(
    historical_summary: Mapping[str, object],
) -> dict[str, Any]:
    """Returns only bounded public aggregates used by local rendering."""
    return {
        "information_set_search_review": _curate_information_set_review(
            historical_summary.get(
                "historical_information_set_search_review_summary"
            )
        ),
        "information_set_replay_coaching": _curate_information_set_coaching(
            historical_summary.get(
                "historical_information_set_replay_coaching_summary"
            )
        ),
    }
