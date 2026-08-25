from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import cast

from skat_ai.learning_corpus_strategy_teacher import (
    LearningCorpusStrategyTeacherEvidenceV1,
)
from skat_ai.learning_corpus_tactical_coaching_contracts import (
    LEARNING_CORPUS_TACTICAL_COACHING_ASSESSMENT_SCOPES,
    LEARNING_CORPUS_TACTICAL_COACHING_DECISION_SUMMARY_ID_DOMAIN,
    LEARNING_CORPUS_TACTICAL_COACHING_DECISION_SUMMARY_VERSION,
    LEARNING_CORPUS_TACTICAL_COACHING_IMPACT_TIERS,
    LEARNING_CORPUS_TACTICAL_COACHING_TEACHER_ASSESSMENT_ID_DOMAIN,
    LEARNING_CORPUS_TACTICAL_COACHING_TEACHER_ASSESSMENT_STATUSES,
    LEARNING_CORPUS_TACTICAL_COACHING_TEACHER_ASSESSMENT_VERSION,
    LearningCorpusTacticalCoachingDecisionSummaryV1,
    LearningCorpusTacticalCoachingTeacherAssessmentV1,
    _build_coaching_identifier_v1,
    _identity_material_v1,
)
from skat_ai.learning_corpus_tactical_motif_evidence import (
    LearningCorpusTacticalMotifEvidenceV1,
)
from skat_ai.tactical_motif_contracts import TACTICAL_MOTIF_TYPES

_COMPLETE_BOUNDED_EVIDENCE_BASIS = {
    "single_exact_world": "bounded_search_single_exact_world",
    "all_compatible_worlds": "bounded_search_all_compatible_worlds",
    "sampled_compatible_worlds": "bounded_search_sampled_compatible_worlds",
}


def _require_mapping(value: object, field_name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be a retained JSON object.")
    return value


def _require_sequence(value: object, field_name: str) -> Sequence[object]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError(f"{field_name} must be a retained JSON array.")
    return value


def _integer(value: object, field_name: str, *, positive: bool = False) -> int:
    if type(value) is not int or value < (1 if positive else 0):
        qualifier = "positive" if positive else "non-negative"
        raise ValueError(f"{field_name} must be a {qualifier} integer.")
    return value


def _number(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be a finite number.")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{field_name} must be finite.")
    return result


def _optional_number(value: object, field_name: str) -> float | None:
    return None if value is None else _number(value, field_name)


def _tactical_teacher_join_key_v1(
    value: LearningCorpusTacticalMotifEvidenceV1 | LearningCorpusStrategyTeacherEvidenceV1,
) -> tuple[str, str, str, str, str]:
    return (
        value.match_snapshot_id,
        value.game_reference_id,
        value.decision_reference_id,
        value.acting_player_id,
        value.actual_card_played,
    )


def _immediate_gap(teacher: LearningCorpusStrategyTeacherEvidenceV1) -> float | None:
    review = teacher.post_game_review_summary
    if review.get("is_available") is not True:
        return None
    if review.get("actual_card_played") != teacher.actual_card_played:
        raise ValueError("Immediate review actual Card must match the Teacher source.")
    return _optional_number(
        review.get("expected_point_swing_difference"),
        "expected_point_swing_difference",
    )


def _not_assessable_values(
    teacher: LearningCorpusStrategyTeacherEvidenceV1,
) -> dict[str, object]:
    return {
        "assessment_scope": "none",
        "evidence_basis": "none",
        "assessment_status": "not_assessable",
        "impact_tier": "not_assessable",
        "best_card": None,
        "actual_card_rank": None,
        "best_card_rank": None,
        "strictly_better_card_count": None,
        "aggregate_equivalent": None,
        "contract_success_rate_gap": None,
        "mean_local_side_game_score_gap": None,
        "mean_local_side_card_point_margin_gap": None,
        "immediate_expected_point_swing_gap": _immediate_gap(teacher),
    }


def _impact_tier(
    *,
    success_gap: float | None,
    score_gap: float | None,
    margin_gap: float | None,
) -> str | None:
    return next(
        (
            tier
            for tier, gap in (
                ("contract_success", success_gap),
                ("settlement_score", score_gap),
                ("card_point_margin", margin_gap),
            )
            if gap is not None and gap > 0
        ),
        None,
    )


def _immediate_assessment_values(
    teacher: LearningCorpusStrategyTeacherEvidenceV1,
) -> dict[str, object]:
    review = teacher.post_game_review_summary
    if review.get("is_available") is not True:
        return _not_assessable_values(teacher)
    if review.get("actual_card_played") != teacher.actual_card_played:
        raise ValueError("Immediate review actual Card must match the Teacher source.")
    best_card = review.get("recommended_card")
    if not isinstance(best_card, str) or best_card not in teacher.legal_cards:
        return _not_assessable_values(teacher)
    try:
        actual_rank = _integer(review.get("actual_card_rank"), "actual_card_rank", positive=True)
        best_rank = _integer(
            review.get("recommended_card_rank"),
            "recommended_card_rank",
            positive=True,
        )
        better_count = _integer(review.get("better_card_count"), "better_card_count")
        immediate_gap = _number(
            review.get("expected_point_swing_difference"),
            "expected_point_swing_difference",
        )
    except ValueError:
        return _not_assessable_values(teacher)
    return {
        "assessment_scope": "immediate_only",
        "evidence_basis": "immediate_expected_value",
        "assessment_status": (
            "best_or_equivalent" if better_count == 0 else "strictly_below_best"
        ),
        "impact_tier": "no_missed_impact" if better_count == 0 else "immediate_only",
        "best_card": best_card,
        "actual_card_rank": actual_rank,
        "best_card_rank": best_rank,
        "strictly_better_card_count": better_count,
        "aggregate_equivalent": None,
        "contract_success_rate_gap": None,
        "mean_local_side_game_score_gap": None,
        "mean_local_side_card_point_margin_gap": None,
        "immediate_expected_point_swing_gap": immediate_gap,
    }


def _complete_candidate_cards(
    teacher: LearningCorpusStrategyTeacherEvidenceV1,
    candidates: Sequence[object],
) -> bool:
    cards = []
    for item in candidates:
        if not isinstance(item, Mapping) or not isinstance(item.get("card"), str):
            return False
        cards.append(cast(str, item["card"]))
    return len(cards) == len(teacher.legal_cards) and len(cards) == len(set(cards)) and set(
        cards
    ) == set(teacher.legal_cards)


def _bounded_search_assessment_values(
    teacher: LearningCorpusStrategyTeacherEvidenceV1,
) -> dict[str, object]:
    search = teacher.bounded_search_result
    review = teacher.bounded_search_post_game_review_summary
    if search is None or review is None:
        return _not_assessable_values(teacher)
    if search.get("game_type") != teacher.information_policy_summary.get("game_type") and (
        teacher.information_policy_summary.get("game_type") is not None
    ):
        raise ValueError("Bounded Search contract must match retained Teacher information.")
    candidates = _require_sequence(search.get("candidate_results"), "candidate_results")
    comparison = review.get("search_actual_card_comparison")
    if (
        not isinstance(comparison, Mapping)
        or comparison.get("is_available") is not True
        or comparison.get("actual_card") != teacher.actual_card_played
        or not _complete_candidate_cards(teacher, candidates)
    ):
        return _not_assessable_values(teacher)

    status = search.get("status")
    world_coverage = search.get("world_coverage")
    if (
        status == "complete"
        and search.get("solution_claim") == "exact_per_selected_world"
        and world_coverage in _COMPLETE_BOUNDED_EVIDENCE_BASIS
    ):
        scope = "complete_search"
        basis = (
            "bounded_search_single_exact_world"
            if world_coverage == "all_compatible_worlds"
            and search.get("compatible_world_count") == 1
            else _COMPLETE_BOUNDED_EVIDENCE_BASIS[cast(str, world_coverage)]
        )
    elif status in {"partial", "timeout"} and comparison.get("comparison_basis") == (
        "completed_common_prefix"
    ):
        scope = "completed_common_prefix"
        basis = "bounded_search_completed_common_prefix"
    else:
        return _not_assessable_values(teacher)

    best_card = comparison.get("search_recommended_card")
    aggregate_equivalent = comparison.get(
        "actual_card_is_aggregate_equivalent_to_recommendation"
    )
    if (
        not isinstance(best_card, str)
        or best_card not in teacher.legal_cards
        or type(aggregate_equivalent) is not bool
    ):
        return _not_assessable_values(teacher)
    try:
        actual_rank = _integer(
            comparison.get("actual_card_rank"),
            "actual_card_rank",
            positive=True,
        )
        best_rank = _integer(
            comparison.get("recommended_card_rank"),
            "recommended_card_rank",
            positive=True,
        )
        better_count = _integer(
            comparison.get("strictly_better_card_count"),
            "strictly_better_card_count",
        )
        success_gap = _optional_number(
            comparison.get("contract_success_rate_gap"),
            "contract_success_rate_gap",
        )
        score_gap = _optional_number(
            comparison.get("mean_local_side_game_score_gap"),
            "mean_local_side_game_score_gap",
        )
        margin_gap = _optional_number(
            comparison.get("mean_local_side_card_point_margin_gap"),
            "mean_local_side_card_point_margin_gap",
        )
    except ValueError:
        return _not_assessable_values(teacher)
    if search.get("game_type") == "null" and margin_gap is not None:
        raise ValueError("Null bounded Search cannot retain card-point-margin impact.")
    impact = (
        "no_missed_impact"
        if better_count == 0
        else _impact_tier(
            success_gap=success_gap,
            score_gap=score_gap,
            margin_gap=margin_gap,
        )
    )
    if impact is None:
        return _not_assessable_values(teacher)
    return {
        "assessment_scope": scope,
        "evidence_basis": basis,
        "assessment_status": (
            "best_or_equivalent" if better_count == 0 else "strictly_below_best"
        ),
        "impact_tier": impact,
        "best_card": best_card,
        "actual_card_rank": actual_rank,
        "best_card_rank": best_rank,
        "strictly_better_card_count": better_count,
        "aggregate_equivalent": aggregate_equivalent,
        "contract_success_rate_gap": success_gap,
        "mean_local_side_game_score_gap": score_gap,
        "mean_local_side_card_point_margin_gap": margin_gap,
        "immediate_expected_point_swing_gap": _immediate_gap(teacher),
    }


def _candidate_metrics(
    candidate: Mapping[str, object],
    *,
    game_type: str,
) -> tuple[float, ...]:
    values = (
        _number(candidate.get("local_contract_success_rate"), "local_contract_success_rate"),
        _number(candidate.get("mean_local_side_game_score"), "mean_local_side_game_score"),
    )
    if game_type == "null":
        if candidate.get("mean_local_side_card_point_margin") is not None:
            raise ValueError("Null Candidates cannot retain card-point margins.")
        return values
    return (
        *values,
        _number(
            candidate.get("mean_local_side_card_point_margin"),
            "mean_local_side_card_point_margin",
        ),
    )


def _information_set_assessment_values(
    teacher: LearningCorpusStrategyTeacherEvidenceV1,
    *,
    game_type: str,
) -> dict[str, object]:
    focused = teacher.information_set_search_evidence
    if focused is None:
        return _not_assessable_values(teacher)
    focused._validate()
    result = focused.information_set_search_result
    comparison = focused.information_set_search_comparison
    if (
        focused.search_status != "complete"
        or focused.policy_claim != "exact_selected_world_policy"
        or focused.policy_consistency != "controlled_player_information_set_consistent"
        or focused.information_set_recommended_card is None
    ):
        return _not_assessable_values(teacher)
    candidates = _require_sequence(result.get("candidate_results"), "candidate_results")
    if not _complete_candidate_cards(teacher, candidates):
        return _not_assessable_values(teacher)
    selected_world_count = _integer(
        focused.consumed_budget.get("selected_world_count"),
        "selected_world_count",
        positive=True,
    )
    completed_world_count = _integer(
        focused.consumed_budget.get("completed_world_count"),
        "completed_world_count",
        positive=True,
    )
    if selected_world_count != completed_world_count:
        return _not_assessable_values(teacher)
    compatible_world_count = _integer(
        result.get("compatible_world_count"),
        "compatible_world_count",
        positive=True,
    )
    if focused.world_coverage == "sampled_compatible_worlds":
        basis = "information_set_sampled_compatible_worlds"
    elif focused.world_coverage == "all_compatible_worlds" and compatible_world_count == 1:
        basis = "information_set_single_exact_world"
    elif focused.world_coverage == "single_exact_world":
        basis = "information_set_single_exact_world"
    elif focused.world_coverage == "all_compatible_worlds":
        basis = "information_set_all_compatible_worlds"
    else:
        return _not_assessable_values(teacher)

    by_card: dict[str, Mapping[str, object]] = {}
    try:
        for item in candidates:
            candidate = _require_mapping(item, "candidate_result")
            card = candidate.get("card")
            if not isinstance(card, str):
                return _not_assessable_values(teacher)
            if _integer(candidate.get("completed_world_count"), "completed_world_count") != (
                selected_world_count
            ):
                return _not_assessable_values(teacher)
            by_card[card] = candidate
        best = by_card[focused.information_set_recommended_card]
        actual = by_card[teacher.actual_card_played]
        best_metrics = _candidate_metrics(best, game_type=game_type)
        actual_metrics = _candidate_metrics(actual, game_type=game_type)
        actual_rank = _integer(actual.get("rank"), "actual_card_rank", positive=True)
        best_rank = _integer(best.get("rank"), "best_card_rank", positive=True)
        better_count = sum(
            _candidate_metrics(candidate, game_type=game_type) > actual_metrics
            for candidate in by_card.values()
        )
    except (KeyError, ValueError):
        return _not_assessable_values(teacher)
    if (
        comparison.get("actual_card") != teacher.actual_card_played
        or comparison.get("information_set_status") != "complete"
        or comparison.get("information_set_recommended_card")
        != focused.information_set_recommended_card
        or comparison.get("information_set_actual_same_card")
        != (teacher.actual_card_played == focused.information_set_recommended_card)
        or comparison.get("information_set_rank_of_actual_card") != actual_rank
    ):
        return _not_assessable_values(teacher)
    success_gap = best_metrics[0] - actual_metrics[0]
    score_gap = best_metrics[1] - actual_metrics[1]
    margin_gap = None if game_type == "null" else best_metrics[2] - actual_metrics[2]
    impact = (
        "no_missed_impact"
        if better_count == 0
        else _impact_tier(
            success_gap=success_gap,
            score_gap=score_gap,
            margin_gap=margin_gap,
        )
    )
    if impact is None:
        return _not_assessable_values(teacher)
    return {
        "assessment_scope": "complete_search",
        "evidence_basis": basis,
        "assessment_status": (
            "best_or_equivalent" if better_count == 0 else "strictly_below_best"
        ),
        "impact_tier": impact,
        "best_card": focused.information_set_recommended_card,
        "actual_card_rank": actual_rank,
        "best_card_rank": best_rank,
        "strictly_better_card_count": better_count,
        "aggregate_equivalent": actual_metrics == best_metrics,
        "contract_success_rate_gap": success_gap,
        "mean_local_side_game_score_gap": score_gap,
        "mean_local_side_card_point_margin_gap": margin_gap,
        "immediate_expected_point_swing_gap": _immediate_gap(teacher),
    }


def _assessment_values(
    tactical: LearningCorpusTacticalMotifEvidenceV1,
    teacher: LearningCorpusStrategyTeacherEvidenceV1,
) -> dict[str, object]:
    effective_method = teacher.recommendation_method_summary.get("effective_method")
    if effective_method == "immediate_expected_value":
        values = _immediate_assessment_values(teacher)
    elif effective_method == "compatible_world_minimax_v1":
        values = _bounded_search_assessment_values(teacher)
    elif effective_method == "bounded_information_set_policy_search_v1":
        values = _information_set_assessment_values(teacher, game_type=tactical.game_type)
    elif effective_method == "none":
        values = _not_assessable_values(teacher)
    else:
        raise ValueError("Strategy Teacher effective method must be canonical.")

    if tactical.observation.decision_time_facts.legal_card_count == 1:
        values.update(
            {
                "assessment_status": "forced_move",
                "impact_tier": "no_missed_impact",
                "best_card": teacher.actual_card_played,
                "actual_card_rank": 1,
                "best_card_rank": 1,
                "strictly_better_card_count": 0,
                "aggregate_equivalent": (
                    True if values["assessment_scope"] == "complete_search" else None
                ),
            }
        )
    values["eligible_for_focus"] = (
        values["assessment_scope"] == "complete_search"
        and values["assessment_status"] == "strictly_below_best"
    )
    return values


def _build_learning_corpus_tactical_coaching_teacher_assessment_v1(
    *,
    tactical_motif_evidence: LearningCorpusTacticalMotifEvidenceV1,
    strategy_teacher_evidence: LearningCorpusStrategyTeacherEvidenceV1,
) -> LearningCorpusTacticalCoachingTeacherAssessmentV1:
    tactical = tactical_motif_evidence
    teacher = strategy_teacher_evidence
    if _tactical_teacher_join_key_v1(tactical) != _tactical_teacher_join_key_v1(teacher):
        raise ValueError("Tactical and Strategy Teacher Evidence must join on all exact facts.")
    if (
        tactical.match_id,
        tactical.workspace_revision,
        tactical.match_position,
        tactical.game_id,
        tactical.decision_index,
    ) != (
        teacher.match_id,
        teacher.workspace_revision,
        teacher.match_position,
        teacher.game_id,
        teacher.decision_index,
    ):
        raise ValueError("Joined Tactical and Strategy Teacher source identities must reconcile.")
    legal_cards = tuple(teacher.legal_cards)
    if (
        any(not isinstance(card, str) for card in legal_cards)
        or len(legal_cards) != len(set(legal_cards))
        or len(legal_cards) != tactical.observation.decision_time_facts.legal_card_count
    ):
        raise ValueError("Joined Tactical and Strategy Teacher legal-card Counts must reconcile.")
    requested_method = teacher.recommendation_method_summary.get("requested_method")
    effective_method = teacher.recommendation_method_summary.get("effective_method")
    if not isinstance(requested_method, str) or not isinstance(effective_method, str):
        raise ValueError("Strategy Teacher method summary must be complete.")
    values = {
        "learning_corpus_tactical_coaching_teacher_assessment_version": (
            LEARNING_CORPUS_TACTICAL_COACHING_TEACHER_ASSESSMENT_VERSION
        ),
        "teacher_assessment_id": "0" * 64,
        "tactical_motif_evidence_id": tactical.tactical_motif_evidence_id,
        "strategy_teacher_evidence_id": teacher.strategy_teacher_evidence_id,
        "teacher_semantic_fingerprint": teacher.teacher_semantic_fingerprint,
        "match_snapshot_id": tactical.match_snapshot_id,
        "game_reference_id": tactical.game_reference_id,
        "decision_reference_id": tactical.decision_reference_id,
        "match_id": tactical.match_id,
        "game_id": tactical.game_id,
        "decision_index": tactical.decision_index,
        "acting_player_id": tactical.acting_player_id,
        "actual_card_played": tactical.actual_card_played,
        "requested_method": requested_method,
        "effective_method": effective_method,
        **_assessment_values(tactical, teacher),
    }
    provisional = LearningCorpusTacticalCoachingTeacherAssessmentV1._from_validated(**values)
    values["teacher_assessment_id"] = _build_coaching_identifier_v1(
        LEARNING_CORPUS_TACTICAL_COACHING_TEACHER_ASSESSMENT_ID_DOMAIN,
        _identity_material_v1(provisional, "teacher_assessment_id"),
    )
    result = LearningCorpusTacticalCoachingTeacherAssessmentV1._from_validated(**values)
    result._validate(verify_identity=True)
    return result


def build_learning_corpus_tactical_coaching_teacher_assessment_v1(
    *,
    tactical_motif_evidence: LearningCorpusTacticalMotifEvidenceV1,
    strategy_teacher_evidence: LearningCorpusStrategyTeacherEvidenceV1,
) -> LearningCorpusTacticalCoachingTeacherAssessmentV1:
    if type(tactical_motif_evidence) is not LearningCorpusTacticalMotifEvidenceV1:
        raise ValueError("tactical_motif_evidence must be exact Tactical Evidence.")
    if type(strategy_teacher_evidence) is not LearningCorpusStrategyTeacherEvidenceV1:
        raise ValueError("strategy_teacher_evidence must be exact Strategy Teacher Evidence.")
    tactical_motif_evidence._validate(verify_identity=True)
    strategy_teacher_evidence._validate(verify_identities=True)
    return _build_learning_corpus_tactical_coaching_teacher_assessment_v1(
        tactical_motif_evidence=tactical_motif_evidence,
        strategy_teacher_evidence=strategy_teacher_evidence,
    )


def _semantic_assessment_material(
    assessment: LearningCorpusTacticalCoachingTeacherAssessmentV1,
) -> dict[str, object]:
    return {
        key: value
        for key, value in assessment.to_dict().items()
        if key not in {"teacher_assessment_id", "strategy_teacher_evidence_id"}
    }


def _semantic_assessments(
    assessments: tuple[LearningCorpusTacticalCoachingTeacherAssessmentV1, ...],
) -> tuple[LearningCorpusTacticalCoachingTeacherAssessmentV1, ...]:
    by_fingerprint: dict[str, LearningCorpusTacticalCoachingTeacherAssessmentV1] = {}
    for assessment in assessments:
        existing = by_fingerprint.get(assessment.teacher_semantic_fingerprint)
        if existing is None:
            by_fingerprint[assessment.teacher_semantic_fingerprint] = assessment
        elif _semantic_assessment_material(existing) != _semantic_assessment_material(assessment):
            raise ValueError("One semantic Teacher fingerprint produced conflicting Assessments.")
    return tuple(by_fingerprint.values())


def _build_learning_corpus_tactical_coaching_decision_summary_v1(
    *,
    tactical_motif_evidence: LearningCorpusTacticalMotifEvidenceV1,
    teacher_assessments: tuple[LearningCorpusTacticalCoachingTeacherAssessmentV1, ...],
) -> LearningCorpusTacticalCoachingDecisionSummaryV1:
    tactical = tactical_motif_evidence
    if any(
        assessment.tactical_motif_evidence_id != tactical.tactical_motif_evidence_id
        for assessment in teacher_assessments
    ):
        raise ValueError("Decision Teacher Assessments must use the exact Tactical Evidence.")
    semantic = _semantic_assessments(teacher_assessments)
    complete = tuple(item for item in semantic if item.assessment_scope == "complete_search")
    legal_count = tactical.observation.decision_time_facts.legal_card_count
    if legal_count == 1:
        decision_status = "forced_move"
    elif not teacher_assessments:
        decision_status = "no_teacher"
    elif not complete:
        decision_status = "not_assessable"
    elif all(item.assessment_status == "best_or_equivalent" for item in complete):
        decision_status = "best_or_equivalent"
    elif all(item.assessment_status == "strictly_below_best" for item in complete):
        decision_status = "strictly_below_best"
    else:
        decision_status = "mixed"
    if decision_status in {"forced_move", "best_or_equivalent"}:
        consensus_impact = "no_missed_impact"
    elif decision_status == "strictly_below_best":
        impacts = {item.impact_tier for item in complete}
        consensus_impact = next(iter(impacts)) if len(impacts) == 1 else "mixed"
    elif decision_status == "mixed":
        consensus_impact = "mixed"
    else:
        consensus_impact = "not_assessable"
    scope_counts = {
        scope: sum(item.assessment_scope == scope for item in semantic)
        for scope in LEARNING_CORPUS_TACTICAL_COACHING_ASSESSMENT_SCOPES
    }
    values = {
        "learning_corpus_tactical_coaching_decision_summary_version": (
            LEARNING_CORPUS_TACTICAL_COACHING_DECISION_SUMMARY_VERSION
        ),
        "decision_summary_id": "0" * 64,
        "tactical_motif_evidence_id": tactical.tactical_motif_evidence_id,
        "match_snapshot_id": tactical.match_snapshot_id,
        "game_reference_id": tactical.game_reference_id,
        "decision_reference_id": tactical.decision_reference_id,
        "match_id": tactical.match_id,
        "game_id": tactical.game_id,
        "decision_index": tactical.decision_index,
        "acting_player_id": tactical.acting_player_id,
        "actual_card_played": tactical.actual_card_played,
        "motif_types": tuple(
            motif_type
            for motif_type in TACTICAL_MOTIF_TYPES
            if any(item.motif_type == motif_type for item in tactical.observation.motifs)
        ),
        "teacher_assessment_ids": tuple(
            item.teacher_assessment_id for item in teacher_assessments
        ),
        "teacher_semantic_fingerprints": tuple(
            item.teacher_semantic_fingerprint for item in semantic
        ),
        "exact_teacher_count": len(teacher_assessments),
        "semantic_teacher_count": len(semantic),
        "complete_search_semantic_teacher_count": scope_counts["complete_search"],
        "completed_common_prefix_semantic_teacher_count": scope_counts[
            "completed_common_prefix"
        ],
        "immediate_only_semantic_teacher_count": scope_counts["immediate_only"],
        "not_assessable_semantic_teacher_count": scope_counts["none"],
        "assessment_status_counts": tuple(
            (
                status,
                sum(item.assessment_status == status for item in semantic),
            )
            for status in LEARNING_CORPUS_TACTICAL_COACHING_TEACHER_ASSESSMENT_STATUSES
        ),
        "impact_tier_counts": tuple(
            (tier, sum(item.impact_tier == tier for item in semantic))
            for tier in LEARNING_CORPUS_TACTICAL_COACHING_IMPACT_TIERS
        ),
        "decision_status": decision_status,
        "consensus_impact_tier": consensus_impact,
        "eligible_for_focus": decision_status == "strictly_below_best",
    }
    provisional = LearningCorpusTacticalCoachingDecisionSummaryV1._from_validated(**values)
    values["decision_summary_id"] = _build_coaching_identifier_v1(
        LEARNING_CORPUS_TACTICAL_COACHING_DECISION_SUMMARY_ID_DOMAIN,
        _identity_material_v1(provisional, "decision_summary_id"),
    )
    result = LearningCorpusTacticalCoachingDecisionSummaryV1._from_validated(**values)
    result._validate(verify_identity=True)
    return result


def build_learning_corpus_tactical_coaching_decision_summary_v1(
    *,
    tactical_motif_evidence: LearningCorpusTacticalMotifEvidenceV1,
    teacher_assessments: tuple[LearningCorpusTacticalCoachingTeacherAssessmentV1, ...],
) -> LearningCorpusTacticalCoachingDecisionSummaryV1:
    if type(tactical_motif_evidence) is not LearningCorpusTacticalMotifEvidenceV1:
        raise ValueError("tactical_motif_evidence must be exact Tactical Evidence.")
    tactical_motif_evidence._validate(verify_identity=True)
    if type(teacher_assessments) is not tuple or any(
        type(item) is not LearningCorpusTacticalCoachingTeacherAssessmentV1
        for item in teacher_assessments
    ):
        raise ValueError("teacher_assessments must contain exact immutable Assessments.")
    for item in teacher_assessments:
        item._validate(verify_identity=True)
    return _build_learning_corpus_tactical_coaching_decision_summary_v1(
        tactical_motif_evidence=tactical_motif_evidence,
        teacher_assessments=teacher_assessments,
    )
