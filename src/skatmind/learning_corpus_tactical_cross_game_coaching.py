from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from skatmind.learning_corpus_player_catalog import (
    LearningCorpusPlayerCatalogEntryV1,
    LearningCorpusPlayerCatalogV1,
    _validate_learning_corpus_player_catalog_v1,
)
from skatmind.learning_corpus_strategy_teacher import (
    LearningCorpusStrategyTeacherEvidenceCollectionV1,
    _validate_learning_corpus_strategy_teacher_collection_v1,
)
from skatmind.learning_corpus_tactical_coaching_assessment import (
    _build_learning_corpus_tactical_coaching_decision_summary_v1,
    _build_learning_corpus_tactical_coaching_teacher_assessment_v1,
    _semantic_assessments,
    _tactical_teacher_join_key_v1,
)
from skatmind.learning_corpus_tactical_coaching_contracts import (
    LEARNING_CORPUS_TACTICAL_COACHING_FOCUS_AREA_ID_DOMAIN,
    LEARNING_CORPUS_TACTICAL_COACHING_FOCUS_AREA_VERSION,
    LEARNING_CORPUS_TACTICAL_COACHING_FOCUS_IMPACT_VALUES,
    LEARNING_CORPUS_TACTICAL_COACHING_GUIDANCE_CODES,
    LEARNING_CORPUS_TACTICAL_COACHING_GUIDANCE_TEXT_BY_CODE,
    LEARNING_CORPUS_TACTICAL_COACHING_MAXIMUM_FOCUS_AREAS_PER_PLAYER,
    LEARNING_CORPUS_TACTICAL_COACHING_MINIMUM_DECISIONS,
    LEARNING_CORPUS_TACTICAL_COACHING_MINIMUM_GAMES,
    LEARNING_CORPUS_TACTICAL_COACHING_PLAYER_REPORT_ID_DOMAIN,
    LEARNING_CORPUS_TACTICAL_COACHING_PLAYER_REPORT_VERSION,
    LEARNING_CORPUS_TACTICAL_CROSS_GAME_COACHING_LIMITATIONS,
    LEARNING_CORPUS_TACTICAL_CROSS_GAME_COACHING_METHOD,
    LEARNING_CORPUS_TACTICAL_CROSS_GAME_COACHING_REPORT_FINGERPRINT_DOMAIN,
    LEARNING_CORPUS_TACTICAL_CROSS_GAME_COACHING_REPORT_VERSION,
    LearningCorpusTacticalCoachingDecisionSummaryV1,
    LearningCorpusTacticalCoachingFocusAreaV1,
    LearningCorpusTacticalCoachingPlayerReportV1,
    LearningCorpusTacticalCoachingTeacherAssessmentV1,
    LearningCorpusTacticalCrossGameCoachingReportV1,
    _build_coaching_identifier_v1,
    _identity_material_v1,
)
from skatmind.learning_corpus_tactical_motif_evidence import (
    LEARNING_CORPUS_TACTICAL_MOTIF_CONTRACTS,
    LEARNING_CORPUS_TACTICAL_MOTIF_PHASES,
    LEARNING_CORPUS_TACTICAL_MOTIF_ROLES,
    LEARNING_CORPUS_TACTICAL_MOTIF_SEATS,
    LearningCorpusTacticalMotifEvidenceCollectionV1,
    LearningCorpusTacticalMotifEvidenceV1,
    _validate_learning_corpus_tactical_motif_collection_v1,
)
from skatmind.learning_corpus_tactical_motif_summary import (
    LearningCorpusTacticalMotifCrossGameSummaryV1,
    _validate_learning_corpus_tactical_motif_cross_game_summary_v1,
)
from skatmind.recommendation_workflow import FLAT_RECOMMENDATION_METHODS
from skatmind.tactical_motif_contracts import (
    TACTICAL_MOTIF_FAMILY_BY_TYPE,
    TACTICAL_MOTIF_TYPES,
)


def _phase(trick_number: int) -> str:
    if 1 <= trick_number <= 3:
        return "opening"
    if 4 <= trick_number <= 7:
        return "middle"
    if 8 <= trick_number <= 10:
        return "endgame"
    raise ValueError("Tactical Coaching requires Tricks 1 through 10.")


def _ordered_unique(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def _canonical_counts(
    canonical: tuple[str, ...],
    values: Iterable[str],
) -> tuple[tuple[str, int], ...]:
    retained = tuple(values)
    return tuple((category, retained.count(category)) for category in canonical)


def _source_identity(value: object) -> tuple[object, ...]:
    return (
        value.corpus_id,
        value.source_catalog_revision,
        value.source_catalog_fingerprint,
        value.source_catalog_content_fingerprint,
        value.current_match_snapshot_ids,
        value.retained_match_snapshot_count,
        value.current_match_count,
        value.orphan_match_snapshot_count,
    )


def _build_focus_area(
    *,
    player_id: str,
    motif_type: str,
    summaries: tuple[LearningCorpusTacticalCoachingDecisionSummaryV1, ...],
    tactical_by_id: dict[str, LearningCorpusTacticalMotifEvidenceV1],
    assessments_by_id: dict[str, LearningCorpusTacticalCoachingTeacherAssessmentV1],
) -> LearningCorpusTacticalCoachingFocusAreaV1:
    impacts = tuple(item.consensus_impact_tier for item in summaries)
    primary_impact = impacts[0] if len(set(impacts)) == 1 else "mixed"
    impact_index = LEARNING_CORPUS_TACTICAL_COACHING_FOCUS_IMPACT_VALUES.index(
        primary_impact
    )
    guidance_code = LEARNING_CORPUS_TACTICAL_COACHING_GUIDANCE_CODES[impact_index]
    game_reference_ids = _ordered_unique(item.game_reference_id for item in summaries)
    match_ids = _ordered_unique(item.match_id for item in summaries)
    recurrence_scope = (
        "multiple_matches"
        if len(match_ids) >= 2
        else "multiple_games_one_match"
        if len(game_reference_ids) >= 2
        else "single_game_only"
    )
    requested_methods: list[str] = []
    roles: list[str] = []
    seats: list[str] = []
    phases: list[str] = []
    contracts: list[str] = []
    for summary in summaries:
        tactical = tactical_by_id[summary.tactical_motif_evidence_id]
        semantic = _semantic_assessments(
            tuple(assessments_by_id[item] for item in summary.teacher_assessment_ids)
        )
        requested_methods.extend(
            dict.fromkeys(
                item.requested_method
                for item in semantic
                if item.assessment_scope == "complete_search"
            )
        )
        roles.append(tactical.acting_side)
        seats.append(tactical.acting_seat)
        phases.append(_phase(tactical.trick_number))
        contracts.append(tactical.game_type)
    values: dict[str, Any] = {
        "learning_corpus_tactical_coaching_focus_area_version": (
            LEARNING_CORPUS_TACTICAL_COACHING_FOCUS_AREA_VERSION
        ),
        "focus_area_id": "0" * 64,
        "player_id": player_id,
        "motif_type": motif_type,
        "motif_family": TACTICAL_MOTIF_FAMILY_BY_TYPE[motif_type],
        "recurrence_scope": recurrence_scope,
        "primary_impact_tier": primary_impact,
        "guidance_code": guidance_code,
        "guidance_text": LEARNING_CORPUS_TACTICAL_COACHING_GUIDANCE_TEXT_BY_CODE[
            guidance_code
        ],
        "qualifying_decision_count": len(summaries),
        "distinct_game_count": len(game_reference_ids),
        "distinct_match_count": len(match_ids),
        "contract_success_decision_count": impacts.count("contract_success"),
        "settlement_score_decision_count": impacts.count("settlement_score"),
        "card_point_margin_decision_count": impacts.count("card_point_margin"),
        "mixed_impact_decision_count": impacts.count("mixed"),
        "decision_summary_ids": tuple(item.decision_summary_id for item in summaries),
        "tactical_motif_evidence_ids": tuple(
            item.tactical_motif_evidence_id for item in summaries
        ),
        "game_reference_ids": game_reference_ids,
        "match_ids": match_ids,
        "requested_method_counts": _canonical_counts(
            tuple(FLAT_RECOMMENDATION_METHODS),
            requested_methods,
        ),
        "role_counts": _canonical_counts(LEARNING_CORPUS_TACTICAL_MOTIF_ROLES, roles),
        "seat_counts": _canonical_counts(LEARNING_CORPUS_TACTICAL_MOTIF_SEATS, seats),
        "phase_counts": _canonical_counts(LEARNING_CORPUS_TACTICAL_MOTIF_PHASES, phases),
        "contract_counts": _canonical_counts(
            LEARNING_CORPUS_TACTICAL_MOTIF_CONTRACTS,
            contracts,
        ),
    }
    provisional = LearningCorpusTacticalCoachingFocusAreaV1._from_validated(**values)
    values["focus_area_id"] = _build_coaching_identifier_v1(
        LEARNING_CORPUS_TACTICAL_COACHING_FOCUS_AREA_ID_DOMAIN,
        _identity_material_v1(provisional, "focus_area_id"),
    )
    result = LearningCorpusTacticalCoachingFocusAreaV1._from_validated(**values)
    result._validate(verify_identity=True)
    return result


def _focus_priority(
    focus: LearningCorpusTacticalCoachingFocusAreaV1,
) -> tuple[int, int, int, int, int]:
    return (
        LEARNING_CORPUS_TACTICAL_COACHING_FOCUS_IMPACT_VALUES.index(
            focus.primary_impact_tier
        ),
        -focus.distinct_match_count,
        -focus.distinct_game_count,
        -focus.qualifying_decision_count,
        TACTICAL_MOTIF_TYPES.index(focus.motif_type),
    )


def _build_player_report(
    *,
    catalog_entry: LearningCorpusPlayerCatalogEntryV1,
    summaries: tuple[LearningCorpusTacticalCoachingDecisionSummaryV1, ...],
    tactical_by_id: dict[str, LearningCorpusTacticalMotifEvidenceV1],
    assessments_by_id: dict[str, LearningCorpusTacticalCoachingTeacherAssessmentV1],
) -> LearningCorpusTacticalCoachingPlayerReportV1:
    candidates: list[LearningCorpusTacticalCoachingFocusAreaV1] = []
    for motif_type in TACTICAL_MOTIF_TYPES:
        qualifying = tuple(
            item
            for item in summaries
            if item.eligible_for_focus and motif_type in item.motif_types
        )
        if (
            len(qualifying) >= LEARNING_CORPUS_TACTICAL_COACHING_MINIMUM_DECISIONS
            and len({item.game_reference_id for item in qualifying})
            >= LEARNING_CORPUS_TACTICAL_COACHING_MINIMUM_GAMES
        ):
            candidates.append(
                _build_focus_area(
                    player_id=catalog_entry.player_id,
                    motif_type=motif_type,
                    summaries=qualifying,
                    tactical_by_id=tactical_by_id,
                    assessments_by_id=assessments_by_id,
                )
            )
    candidates.sort(key=_focus_priority)
    focus_areas = tuple(
        candidates[:LEARNING_CORPUS_TACTICAL_COACHING_MAXIMUM_FOCUS_AREAS_PER_PLAYER]
    )
    values: dict[str, Any] = {
        "learning_corpus_tactical_coaching_player_report_version": (
            LEARNING_CORPUS_TACTICAL_COACHING_PLAYER_REPORT_VERSION
        ),
        "player_report_id": "0" * 64,
        "player_id": catalog_entry.player_id,
        "observed_labels": catalog_entry.observed_labels,
        "match_ids": catalog_entry.match_ids,
        "current_match_snapshot_ids": catalog_entry.current_match_snapshot_ids,
        "tactical_decision_count": len(summaries),
        "teacher_covered_decision_count": sum(
            item.exact_teacher_count > 0 for item in summaries
        ),
        "exact_teacher_assessment_count": sum(item.exact_teacher_count for item in summaries),
        "semantic_teacher_group_count": sum(item.semantic_teacher_count for item in summaries),
        "forced_move_count": sum(item.decision_status == "forced_move" for item in summaries),
        "no_teacher_count": sum(item.decision_status == "no_teacher" for item in summaries),
        "not_assessable_count": sum(
            item.decision_status == "not_assessable" for item in summaries
        ),
        "best_or_equivalent_count": sum(
            item.decision_status == "best_or_equivalent" for item in summaries
        ),
        "strictly_below_best_count": sum(
            item.decision_status == "strictly_below_best" for item in summaries
        ),
        "mixed_count": sum(item.decision_status == "mixed" for item in summaries),
        "eligible_focus_candidate_count": len(candidates),
        "retained_focus_area_count": len(focus_areas),
        "focus_areas": focus_areas,
    }
    provisional = LearningCorpusTacticalCoachingPlayerReportV1._from_validated(**values)
    values["player_report_id"] = _build_coaching_identifier_v1(
        LEARNING_CORPUS_TACTICAL_COACHING_PLAYER_REPORT_ID_DOMAIN,
        _identity_material_v1(provisional, "player_report_id"),
    )
    result = LearningCorpusTacticalCoachingPlayerReportV1._from_validated(**values)
    result._validate(verify_identity=True)
    return result


def build_learning_corpus_tactical_cross_game_coaching_report_v1(
    *,
    player_catalog: LearningCorpusPlayerCatalogV1,
    strategy_teacher_collection: LearningCorpusStrategyTeacherEvidenceCollectionV1,
    tactical_motif_collection: LearningCorpusTacticalMotifEvidenceCollectionV1,
    tactical_motif_cross_game_summary: LearningCorpusTacticalMotifCrossGameSummaryV1,
) -> LearningCorpusTacticalCrossGameCoachingReportV1:
    """Builds exact method-bound Coaching without executing any analysis workflow."""
    _validate_learning_corpus_player_catalog_v1(player_catalog)
    _validate_learning_corpus_strategy_teacher_collection_v1(strategy_teacher_collection)
    _validate_learning_corpus_tactical_motif_collection_v1(tactical_motif_collection)
    _validate_learning_corpus_tactical_motif_cross_game_summary_v1(
        tactical_motif_cross_game_summary
    )
    source_identity = _source_identity(player_catalog)
    if _source_identity(strategy_teacher_collection) != source_identity or _source_identity(
        tactical_motif_collection
    ) != source_identity:
        raise ValueError("Coaching sources must use one exact Current-Snapshot identity.")
    summary = tactical_motif_cross_game_summary
    if (
        (
            summary.corpus_id,
            summary.source_catalog_revision,
            summary.source_catalog_fingerprint,
            summary.source_catalog_content_fingerprint,
            summary.current_match_snapshot_ids,
        )
        != source_identity[:5]
        or summary.player_catalog_fingerprint != player_catalog.player_catalog_fingerprint
        or summary.tactical_motif_collection_fingerprint
        != tactical_motif_collection.tactical_motif_collection_fingerprint
        or summary.evidence_count != tactical_motif_collection.evidence_count
        or summary.skipped_decision_count != tactical_motif_collection.skipped_decision_count
    ):
        raise ValueError("Tactical Summary must reconcile with exact Coaching sources.")

    tactical_by_key = {
        _tactical_teacher_join_key_v1(item): item for item in tactical_motif_collection.evidences
    }
    tactical_by_reference = {
        item.decision_reference_id: item for item in tactical_motif_collection.evidences
    }
    if len(tactical_by_key) != len(tactical_motif_collection.evidences):
        raise ValueError("Tactical Coaching join keys must be unique.")
    assessments: list[LearningCorpusTacticalCoachingTeacherAssessmentV1] = []
    unjoined_ids: list[str] = []
    assessments_by_tactical: dict[
        str, list[LearningCorpusTacticalCoachingTeacherAssessmentV1]
    ] = {item.tactical_motif_evidence_id: [] for item in tactical_motif_collection.evidences}
    for teacher in strategy_teacher_collection.evidences:
        tactical = tactical_by_key.get(_tactical_teacher_join_key_v1(teacher))
        if tactical is None:
            same_reference = tactical_by_reference.get(teacher.decision_reference_id)
            if same_reference is not None:
                raise ValueError(
                    "A shared Decision Reference cannot contradict exact Coaching join facts."
                )
            unjoined_ids.append(teacher.strategy_teacher_evidence_id)
            continue
        assessment = _build_learning_corpus_tactical_coaching_teacher_assessment_v1(
            tactical_motif_evidence=tactical,
            strategy_teacher_evidence=teacher,
        )
        assessments.append(assessment)
        assessments_by_tactical[tactical.tactical_motif_evidence_id].append(assessment)

    decision_summaries = tuple(
        _build_learning_corpus_tactical_coaching_decision_summary_v1(
            tactical_motif_evidence=tactical,
            teacher_assessments=tuple(
                assessments_by_tactical[tactical.tactical_motif_evidence_id]
            ),
        )
        for tactical in tactical_motif_collection.evidences
    )
    summaries_by_player: dict[
        str, list[LearningCorpusTacticalCoachingDecisionSummaryV1]
    ] = {item.player_id: [] for item in player_catalog.players}
    for item in decision_summaries:
        if item.acting_player_id not in summaries_by_player:
            raise ValueError("Every Tactical Coaching Player must resolve through the Catalog.")
        summaries_by_player[item.acting_player_id].append(item)
    tactical_by_id = {
        item.tactical_motif_evidence_id: item for item in tactical_motif_collection.evidences
    }
    assessments_by_id = {item.teacher_assessment_id: item for item in assessments}
    player_reports = tuple(
        _build_player_report(
            catalog_entry=entry,
            summaries=tuple(summaries_by_player[entry.player_id]),
            tactical_by_id=tactical_by_id,
            assessments_by_id=assessments_by_id,
        )
        for entry in player_catalog.players
    )
    focus_areas = tuple(focus for player in player_reports for focus in player.focus_areas)
    status = (
        "empty"
        if not decision_summaries
        else "available"
        if focus_areas
        else "insufficient_evidence"
    )
    values: dict[str, Any] = {
        "learning_corpus_tactical_cross_game_coaching_report_version": (
            LEARNING_CORPUS_TACTICAL_CROSS_GAME_COACHING_REPORT_VERSION
        ),
        "tactical_cross_game_coaching_report_fingerprint": "0" * 64,
        "report_method": LEARNING_CORPUS_TACTICAL_CROSS_GAME_COACHING_METHOD,
        "status": status,
        "corpus_id": player_catalog.corpus_id,
        "source_catalog_revision": player_catalog.source_catalog_revision,
        "source_catalog_fingerprint": player_catalog.source_catalog_fingerprint,
        "source_catalog_content_fingerprint": (
            player_catalog.source_catalog_content_fingerprint
        ),
        "current_match_snapshot_ids": player_catalog.current_match_snapshot_ids,
        "player_catalog_fingerprint": player_catalog.player_catalog_fingerprint,
        "strategy_teacher_collection_fingerprint": (
            strategy_teacher_collection.strategy_teacher_collection_fingerprint
        ),
        "tactical_motif_collection_fingerprint": (
            tactical_motif_collection.tactical_motif_collection_fingerprint
        ),
        "tactical_motif_cross_game_summary_fingerprint": (
            summary.tactical_motif_cross_game_summary_fingerprint
        ),
        "tactical_decision_count": len(decision_summaries),
        "tactical_skipped_decision_count": tactical_motif_collection.skipped_decision_count,
        "exact_teacher_evidence_count": strategy_teacher_collection.evidence_count,
        "joined_teacher_evidence_count": len(assessments),
        "unjoined_teacher_evidence_count": len(unjoined_ids),
        "semantic_teacher_group_count": sum(
            item.semantic_teacher_count for item in decision_summaries
        ),
        "teacher_assessment_count": len(assessments),
        "decision_summary_count": len(decision_summaries),
        "teacher_covered_decision_count": sum(
            item.exact_teacher_count > 0 for item in decision_summaries
        ),
        "complete_search_assessable_decision_count": sum(
            item.decision_status
            in {"best_or_equivalent", "strictly_below_best", "mixed"}
            for item in decision_summaries
        ),
        "strictly_below_best_decision_count": sum(
            item.decision_status == "strictly_below_best" for item in decision_summaries
        ),
        "mixed_decision_count": sum(
            item.decision_status == "mixed" for item in decision_summaries
        ),
        "focus_area_count": len(focus_areas),
        "player_with_focus_count": sum(
            item.retained_focus_area_count > 0 for item in player_reports
        ),
        "teacher_assessments": tuple(assessments),
        "decision_summaries": decision_summaries,
        "unjoined_strategy_teacher_evidence_ids": tuple(unjoined_ids),
        "player_reports": player_reports,
        "focus_areas": focus_areas,
        "limitations": LEARNING_CORPUS_TACTICAL_CROSS_GAME_COACHING_LIMITATIONS,
    }
    provisional = LearningCorpusTacticalCrossGameCoachingReportV1._from_validated(**values)
    values["tactical_cross_game_coaching_report_fingerprint"] = (
        _build_coaching_identifier_v1(
            LEARNING_CORPUS_TACTICAL_CROSS_GAME_COACHING_REPORT_FINGERPRINT_DOMAIN,
            _identity_material_v1(
                provisional,
                "tactical_cross_game_coaching_report_fingerprint",
            ),
        )
    )
    result = LearningCorpusTacticalCrossGameCoachingReportV1._from_validated(**values)
    result._validate(verify_fingerprint=True)
    return result
