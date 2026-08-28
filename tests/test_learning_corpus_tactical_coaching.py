import json
from dataclasses import fields, replace
from types import SimpleNamespace

import pytest
from test_learning_corpus_human_evidence import _store
from test_learning_corpus_strategy_teacher import _changed_report, _snapshot, _source_bundle
from test_match_workspace_contracts import _complete_observed_game, _definition, _set_game

from skatmind.bounded_search_result import (
    BOUNDED_SEARCH_ANALYSIS_METHOD,
    BOUNDED_SEARCH_SCHEMA_VERSION,
    AggregateSearchCandidateResult,
    BoundedSearchResult,
    ConsumedSearchBudget,
    rank_search_candidate_results,
)
from skatmind.learning_corpus_player_catalog import (
    build_learning_corpus_player_catalog_v1,
)
from skatmind.learning_corpus_strategy_teacher import (
    build_learning_corpus_strategy_teacher_report_source_v1,
)
from skatmind.learning_corpus_strategy_teacher_builder import (
    build_learning_corpus_strategy_teacher_evidence_collection_v1,
)
from skatmind.learning_corpus_tactical_coaching_assessment import (
    _assessment_values,
    _immediate_assessment_values,
    _information_set_assessment_values,
    _semantic_assessments,
    build_learning_corpus_tactical_coaching_teacher_assessment_v1,
)
from skatmind.learning_corpus_tactical_coaching_contracts import (
    LEARNING_CORPUS_TACTICAL_COACHING_ACTIONABLE_POLICY,
    LEARNING_CORPUS_TACTICAL_COACHING_ACTUAL_CARD_POLICY,
    LEARNING_CORPUS_TACTICAL_COACHING_ASSESSMENT_SCOPES,
    LEARNING_CORPUS_TACTICAL_COACHING_CONSENSUS_POLICY,
    LEARNING_CORPUS_TACTICAL_COACHING_DATASET_POLICY,
    LEARNING_CORPUS_TACTICAL_COACHING_DECISION_STATUSES,
    LEARNING_CORPUS_TACTICAL_COACHING_DECISION_SUMMARY_ID_DOMAIN,
    LEARNING_CORPUS_TACTICAL_COACHING_DECISION_SUMMARY_VERSION,
    LEARNING_CORPUS_TACTICAL_COACHING_EVIDENCE_BASES,
    LEARNING_CORPUS_TACTICAL_COACHING_EVIDENCE_SEPARATION_POLICY,
    LEARNING_CORPUS_TACTICAL_COACHING_EXPORT_POLICY,
    LEARNING_CORPUS_TACTICAL_COACHING_FOCUS_AREA_ID_DOMAIN,
    LEARNING_CORPUS_TACTICAL_COACHING_FOCUS_AREA_VERSION,
    LEARNING_CORPUS_TACTICAL_COACHING_FOCUS_IMPACT_VALUES,
    LEARNING_CORPUS_TACTICAL_COACHING_GUIDANCE_CODES,
    LEARNING_CORPUS_TACTICAL_COACHING_GUIDANCE_POLICY,
    LEARNING_CORPUS_TACTICAL_COACHING_JOIN_POLICY,
    LEARNING_CORPUS_TACTICAL_COACHING_MAXIMUM_FOCUS_AREAS_PER_PLAYER,
    LEARNING_CORPUS_TACTICAL_COACHING_MINIMUM_DECISIONS,
    LEARNING_CORPUS_TACTICAL_COACHING_MINIMUM_GAMES,
    LEARNING_CORPUS_TACTICAL_COACHING_PLAYER_REPORT_ID_DOMAIN,
    LEARNING_CORPUS_TACTICAL_COACHING_PLAYER_REPORT_VERSION,
    LEARNING_CORPUS_TACTICAL_COACHING_PREPARATION_POLICY,
    LEARNING_CORPUS_TACTICAL_COACHING_PREPARED_ARTIFACTS_VERSION,
    LEARNING_CORPUS_TACTICAL_COACHING_PRIORITY_POLICY,
    LEARNING_CORPUS_TACTICAL_COACHING_PUBLIC_POLICY,
    LEARNING_CORPUS_TACTICAL_COACHING_RECURRENCE_POLICY,
    LEARNING_CORPUS_TACTICAL_COACHING_SEMANTIC_POLICY,
    LEARNING_CORPUS_TACTICAL_COACHING_SOURCE_POLICY,
    LEARNING_CORPUS_TACTICAL_COACHING_TEACHER_ASSESSMENT_ID_DOMAIN,
    LEARNING_CORPUS_TACTICAL_COACHING_TEACHER_ASSESSMENT_STATUSES,
    LEARNING_CORPUS_TACTICAL_COACHING_TEACHER_ASSESSMENT_VERSION,
    LEARNING_CORPUS_TACTICAL_COACHING_TEACHER_POLICY,
    LEARNING_CORPUS_TACTICAL_CROSS_GAME_COACHING_EXPORT_ID_DOMAIN,
    LEARNING_CORPUS_TACTICAL_CROSS_GAME_COACHING_EXPORT_VERSION,
    LEARNING_CORPUS_TACTICAL_CROSS_GAME_COACHING_LIMITATIONS,
    LEARNING_CORPUS_TACTICAL_CROSS_GAME_COACHING_METHOD,
    LEARNING_CORPUS_TACTICAL_CROSS_GAME_COACHING_REPORT_FINGERPRINT_DOMAIN,
    LEARNING_CORPUS_TACTICAL_CROSS_GAME_COACHING_REPORT_STATUSES,
    LEARNING_CORPUS_TACTICAL_CROSS_GAME_COACHING_REPORT_VERSION,
    LearningCorpusTacticalCoachingDecisionSummaryV1,
    LearningCorpusTacticalCoachingFocusAreaV1,
    LearningCorpusTacticalCoachingPlayerReportV1,
    LearningCorpusTacticalCoachingTeacherAssessmentV1,
    LearningCorpusTacticalCrossGameCoachingReportV1,
    _build_coaching_identifier_v1,
    _identity_material_v1,
)
from skatmind.learning_corpus_tactical_coaching_export import (
    LEARNING_CORPUS_TACTICAL_CROSS_GAME_COACHING_DOCUMENT_KIND,
    LearningCorpusTacticalCrossGameCoachingExportV1,
    build_learning_corpus_tactical_cross_game_coaching_export_v1,
    serialize_learning_corpus_tactical_cross_game_coaching_export_v1,
)
from skatmind.learning_corpus_tactical_cross_game_coaching import (
    _focus_priority,
    build_learning_corpus_tactical_cross_game_coaching_report_v1,
)
from skatmind.learning_corpus_tactical_motif_builder import (
    build_learning_corpus_tactical_motif_evidence_collection_v1,
)
from skatmind.learning_corpus_tactical_motif_evidence import (
    _build_learning_corpus_skipped_tactical_motif_decision_v1,
    _build_learning_corpus_tactical_motif_collection_v1,
)
from skatmind.learning_corpus_tactical_motif_summary import (
    build_learning_corpus_tactical_motif_cross_game_summary_v1,
)
from skatmind.match_workspace_contracts import create_match_workspace_v1
from skatmind.rules import get_legal_cards
from skatmind.tactical_motif_contracts import TACTICAL_MOTIF_FAMILIES, TACTICAL_MOTIF_TYPES
from skatmind.terminal_utility import TERMINAL_UTILITY_VERSION


def _coaching_sources(store, teacher_sources=()):
    player_catalog = build_learning_corpus_player_catalog_v1(store)
    teachers = build_learning_corpus_strategy_teacher_evidence_collection_v1(
        store,
        teacher_sources,
    )
    tactical = build_learning_corpus_tactical_motif_evidence_collection_v1(store)
    tactical_summary = build_learning_corpus_tactical_motif_cross_game_summary_v1(
        tactical,
        player_catalog,
    )
    return player_catalog, teachers, tactical, tactical_summary


def _report(store, teacher_sources=()):
    player_catalog, teachers, tactical, tactical_summary = _coaching_sources(
        store,
        teacher_sources,
    )
    return build_learning_corpus_tactical_cross_game_coaching_report_v1(
        player_catalog=player_catalog,
        strategy_teacher_collection=teachers,
        tactical_motif_collection=tactical,
        tactical_motif_cross_game_summary=tactical_summary,
    )


def _below_best_search_result(
    *,
    information_view,
    requested_budget,
    random_seed,
    expected_seed: int,
    below_best_cards: frozenset[str],
) -> BoundedSearchResult:
    assert random_seed == expected_seed
    legal_cards = get_legal_cards(
        list(information_view.local_remaining_hand),
        [play.card for play in information_view.current_trick],
        information_view.game_type,
    )
    candidates = rank_search_candidate_results(
        tuple(
            AggregateSearchCandidateResult(
                card=card,
                rank=1,
                is_recommended=False,
                completed_world_count=2,
                local_contract_success_count=0 if card in below_best_cards else 2,
                local_contract_success_rate=0.0 if card in below_best_cards else 1.0,
                mean_local_side_game_score=0.0 if card in below_best_cards else 24.0,
                mean_local_side_card_point_margin=(
                    0.0 if card in below_best_cards else 10.0
                ),
            )
            for card in legal_cards
        ),
        information_view.game_type,
        recommend=True,
    )
    return BoundedSearchResult(
        schema_version=BOUNDED_SEARCH_SCHEMA_VERSION,
        analysis_method=BOUNDED_SEARCH_ANALYSIS_METHOD,
        search_method="compatible_world_minimax_v1",
        game_type=information_view.game_type,
        status="complete",
        stop_reason="completed",
        world_coverage="sampled_compatible_worlds",
        solution_claim="exact_per_selected_world",
        terminal_utility_version=TERMINAL_UTILITY_VERSION,
        requested_budget=requested_budget,
        consumed_budget=ConsumedSearchBudget(
            depth_reached=1,
            nodes_expanded=2,
            selected_world_count=2,
            completed_world_count=2,
            sampled_world_count=2,
            unique_sampled_world_count=2,
            wall_clock_elapsed_ms=1,
        ),
        compatible_world_count=3,
        candidate_results=candidates,
        recommended_card=candidates[0].card,
        fallback_used=False,
        fallback_method=None,
    )


def _replace_tactical_evidence_with_skip(tactical, target):
    evidences = tuple(
        item
        for item in tactical.evidences
        if item.tactical_motif_evidence_id != target.tactical_motif_evidence_id
    )
    skipped = _build_learning_corpus_skipped_tactical_motif_decision_v1(
        match_snapshot_id=target.match_snapshot_id,
        workspace_revision=target.workspace_revision,
        game_reference_id=target.game_reference_id,
        decision_reference_id=target.decision_reference_id,
        match_id=target.match_id,
        match_position=target.match_position,
        game_id=target.game_id,
        decision_index=target.decision_index,
        trick_number=target.trick_number,
        play_index=target.play_index,
        acting_player_id=target.acting_player_id,
        acting_seat=target.acting_seat,
        acting_side=target.acting_side,
        game_type=target.game_type,
        reason="acting_hand_unavailable",
    )
    skipped_decisions = tuple(
        sorted(
            (*tactical.skipped_decisions, skipped),
            key=lambda item: (item.match_position, item.decision_index),
        )
    )
    motifs = tuple(motif for item in evidences for motif in item.observation.motifs)
    return _build_learning_corpus_tactical_motif_collection_v1(
        corpus_id=tactical.corpus_id,
        source_catalog_revision=tactical.source_catalog_revision,
        source_catalog_fingerprint=tactical.source_catalog_fingerprint,
        source_catalog_content_fingerprint=tactical.source_catalog_content_fingerprint,
        current_match_snapshot_ids=tactical.current_match_snapshot_ids,
        retained_match_snapshot_count=tactical.retained_match_snapshot_count,
        current_match_count=tactical.current_match_count,
        orphan_match_snapshot_count=tactical.orphan_match_snapshot_count,
        status="partial",
        observed_game_count=tactical.observed_game_count,
        observed_decision_count=tactical.observed_decision_count,
        evidence_count=len(evidences),
        skipped_decision_count=len(skipped_decisions),
        complete_observation_count=sum(
            item.observation.observation_status == "complete" for item in evidences
        ),
        partial_observation_count=sum(
            item.observation.observation_status == "partial" for item in evidences
        ),
        motif_occurrence_count=len(motifs),
        evidences=evidences,
        skipped_decisions=skipped_decisions,
        motif_counts=tuple(
            (motif_type, sum(item.motif_type == motif_type for item in motifs))
            for motif_type in TACTICAL_MOTIF_TYPES
        ),
        family_counts=tuple(
            (family, sum(item.motif_family == family for item in motifs))
            for family in TACTICAL_MOTIF_FAMILIES
        ),
    )


def _information_set_teacher_stub(
    *,
    coverage: str,
    compatible_world_count: int,
    search_status: str = "complete",
    game_type: str = "grand",
    aggregate_equivalent: bool = False,
):
    completed_world_count = 1 if compatible_world_count == 1 else 2
    margin = None if game_type == "null" else 10.0
    candidates = (
        {
            "card": "CA",
            "rank": 1,
            "completed_world_count": completed_world_count,
            "local_contract_success_rate": 1.0,
            "mean_local_side_game_score": 24.0,
            "mean_local_side_card_point_margin": margin,
        },
        {
            "card": "C8",
            "rank": 2,
            "completed_world_count": completed_world_count,
            "local_contract_success_rate": 1.0 if aggregate_equivalent else 0.0,
            "mean_local_side_game_score": 24.0 if aggregate_equivalent else 0.0,
            "mean_local_side_card_point_margin": (
                None if game_type == "null" else 10.0 if aggregate_equivalent else 0.0
            ),
        },
    )
    focused = SimpleNamespace(
        _validate=lambda: None,
        search_status=search_status,
        policy_claim="exact_selected_world_policy",
        policy_consistency="controlled_player_information_set_consistent",
        information_set_recommended_card="CA",
        world_coverage=coverage,
        consumed_budget={
            "selected_world_count": completed_world_count,
            "completed_world_count": completed_world_count,
        },
        information_set_search_result={
            "compatible_world_count": compatible_world_count,
            "candidate_results": candidates,
        },
        information_set_search_comparison={
            "comparison_status": "unavailable",
            "actual_card": "C8",
            "information_set_status": "complete",
            "information_set_recommended_card": "CA",
            "information_set_actual_same_card": False,
            "information_set_rank_of_actual_card": 2,
        },
    )
    return SimpleNamespace(
        information_set_search_evidence=focused,
        legal_cards=("CA", "C8"),
        actual_card_played="C8",
        post_game_review_summary={"is_available": False},
    )


def test_versions_vocabularies_policies_limitations_and_domains_are_exact() -> None:
    assert (
        LEARNING_CORPUS_TACTICAL_COACHING_TEACHER_ASSESSMENT_VERSION,
        LEARNING_CORPUS_TACTICAL_COACHING_DECISION_SUMMARY_VERSION,
        LEARNING_CORPUS_TACTICAL_COACHING_FOCUS_AREA_VERSION,
        LEARNING_CORPUS_TACTICAL_COACHING_PLAYER_REPORT_VERSION,
        LEARNING_CORPUS_TACTICAL_CROSS_GAME_COACHING_REPORT_VERSION,
        LEARNING_CORPUS_TACTICAL_CROSS_GAME_COACHING_EXPORT_VERSION,
        LEARNING_CORPUS_TACTICAL_COACHING_PREPARED_ARTIFACTS_VERSION,
    ) == (1,) * 7
    assert LEARNING_CORPUS_TACTICAL_CROSS_GAME_COACHING_METHOD == (
        "learning_corpus_tactical_cross_game_coaching_v1"
    )
    assert LEARNING_CORPUS_TACTICAL_COACHING_ASSESSMENT_SCOPES == (
        "complete_search",
        "completed_common_prefix",
        "immediate_only",
        "none",
    )
    assert LEARNING_CORPUS_TACTICAL_COACHING_EVIDENCE_BASES == (
        "bounded_search_single_exact_world",
        "bounded_search_all_compatible_worlds",
        "bounded_search_sampled_compatible_worlds",
        "bounded_search_completed_common_prefix",
        "information_set_single_exact_world",
        "information_set_all_compatible_worlds",
        "information_set_sampled_compatible_worlds",
        "immediate_expected_value",
        "none",
    )
    assert LEARNING_CORPUS_TACTICAL_COACHING_TEACHER_ASSESSMENT_STATUSES == (
        "forced_move",
        "best_or_equivalent",
        "strictly_below_best",
        "not_assessable",
    )
    assert LEARNING_CORPUS_TACTICAL_COACHING_DECISION_STATUSES == (
        "forced_move",
        "no_teacher",
        "not_assessable",
        "best_or_equivalent",
        "strictly_below_best",
        "mixed",
    )
    assert LEARNING_CORPUS_TACTICAL_CROSS_GAME_COACHING_REPORT_STATUSES == (
        "empty",
        "insufficient_evidence",
        "available",
    )
    assert LEARNING_CORPUS_TACTICAL_COACHING_FOCUS_IMPACT_VALUES == (
        "contract_success",
        "settlement_score",
        "card_point_margin",
        "mixed",
    )
    assert LEARNING_CORPUS_TACTICAL_COACHING_GUIDANCE_CODES == (
        "review_repeated_contract_success_gap",
        "review_repeated_settlement_score_gap",
        "review_repeated_card_point_margin_gap",
        "review_repeated_mixed_search_gap",
    )
    assert (
        LEARNING_CORPUS_TACTICAL_COACHING_MINIMUM_DECISIONS,
        LEARNING_CORPUS_TACTICAL_COACHING_MINIMUM_GAMES,
        LEARNING_CORPUS_TACTICAL_COACHING_MAXIMUM_FOCUS_AREAS_PER_PLAYER,
    ) == (2, 2, 5)
    assert (
        LEARNING_CORPUS_TACTICAL_COACHING_SOURCE_POLICY,
        LEARNING_CORPUS_TACTICAL_COACHING_JOIN_POLICY,
        LEARNING_CORPUS_TACTICAL_COACHING_TEACHER_POLICY,
        LEARNING_CORPUS_TACTICAL_COACHING_SEMANTIC_POLICY,
        LEARNING_CORPUS_TACTICAL_COACHING_ACTIONABLE_POLICY,
        LEARNING_CORPUS_TACTICAL_COACHING_CONSENSUS_POLICY,
        LEARNING_CORPUS_TACTICAL_COACHING_RECURRENCE_POLICY,
        LEARNING_CORPUS_TACTICAL_COACHING_PRIORITY_POLICY,
        LEARNING_CORPUS_TACTICAL_COACHING_GUIDANCE_POLICY,
        LEARNING_CORPUS_TACTICAL_COACHING_ACTUAL_CARD_POLICY,
        LEARNING_CORPUS_TACTICAL_COACHING_EVIDENCE_SEPARATION_POLICY,
        LEARNING_CORPUS_TACTICAL_COACHING_DATASET_POLICY,
        LEARNING_CORPUS_TACTICAL_COACHING_PREPARATION_POLICY,
        LEARNING_CORPUS_TACTICAL_COACHING_EXPORT_POLICY,
        LEARNING_CORPUS_TACTICAL_COACHING_PUBLIC_POLICY,
    ) == (
        "explicit_current_snapshot_tactical_and_strategy_sources",
        "exact_snapshot_scoped_decision_reference_join",
        "one_assessment_per_exact_teacher_report_without_preference",
        "semantic_duplicate_reports_do_not_multiply_decision_consensus",
        "complete_search_teacher_evidence_only_for_actionable_focus",
        "all_distinct_semantic_complete_search_teachers_must_agree",
        "repeated_below_best_decisions_across_at_least_two_games",
        "existing_objective_priority_without_teacher_preference",
        "fixed_template_review_guidance_without_trait_or_causal_claim",
        "observed_behavior_not_ground_truth",
        "human_strategy_and_tactical_evidence_remain_separate",
        "no_learning_dataset_v2_or_existing_summary_mutation",
        "process_local_explicit_generation_safe_preparation",
        "deterministic_path_free_private_json",
        "private_dashboard_counts_and_authenticated_download",
    )
    assert LEARNING_CORPUS_TACTICAL_CROSS_GAME_COACHING_LIMITATIONS[-1] == (
        "no_model_training_or_dataset_mutation"
    )
    assert (
        LEARNING_CORPUS_TACTICAL_COACHING_TEACHER_ASSESSMENT_ID_DOMAIN,
        LEARNING_CORPUS_TACTICAL_COACHING_DECISION_SUMMARY_ID_DOMAIN,
        LEARNING_CORPUS_TACTICAL_COACHING_FOCUS_AREA_ID_DOMAIN,
        LEARNING_CORPUS_TACTICAL_COACHING_PLAYER_REPORT_ID_DOMAIN,
        LEARNING_CORPUS_TACTICAL_CROSS_GAME_COACHING_REPORT_FINGERPRINT_DOMAIN,
        LEARNING_CORPUS_TACTICAL_CROSS_GAME_COACHING_EXPORT_ID_DOMAIN,
    ) == (
        b"skatmind\0learning_corpus_tactical_coaching_teacher_assessment_v1\0",
        b"skatmind\0learning_corpus_tactical_coaching_decision_summary_v1\0",
        b"skatmind\0learning_corpus_tactical_coaching_focus_area_v1\0",
        b"skatmind\0learning_corpus_tactical_coaching_player_report_v1\0",
        b"skatmind\0learning_corpus_tactical_cross_game_coaching_report_v1\0",
        b"skatmind\0learning_corpus_tactical_cross_game_coaching_export_v1\0",
    )
    assert fields(LearningCorpusTacticalCoachingTeacherAssessmentV1)[1].name == (
        "teacher_assessment_id"
    )
    assert fields(LearningCorpusTacticalCoachingDecisionSummaryV1)[1].name == (
        "decision_summary_id"
    )
    assert fields(LearningCorpusTacticalCoachingFocusAreaV1)[1].name == "focus_area_id"
    assert fields(LearningCorpusTacticalCoachingPlayerReportV1)[1].name == "player_report_id"
    assert fields(LearningCorpusTacticalCrossGameCoachingReportV1)[-1].name == "limitations"
    assert fields(LearningCorpusTacticalCrossGameCoachingExportV1)[1].name == "document_kind"


def test_empty_report_retains_every_zero_count_player_and_canonical_export() -> None:
    report = _report(_store())

    assert report.status == "empty"
    assert report.tactical_decision_count == 0
    assert report.teacher_assessments == ()
    assert report.decision_summaries == ()
    assert report.player_reports == ()
    assert report.focus_areas == ()
    assert report.limitations == LEARNING_CORPUS_TACTICAL_CROSS_GAME_COACHING_LIMITATIONS

    export = build_learning_corpus_tactical_cross_game_coaching_export_v1(report)
    content = serialize_learning_corpus_tactical_cross_game_coaching_export_v1(export)
    assert content == serialize_learning_corpus_tactical_cross_game_coaching_export_v1(export)
    assert content.endswith(b"\n") and not content.endswith(b"\n\n")
    document = json.loads(content)
    assert document["document_kind"] == (
        LEARNING_CORPUS_TACTICAL_CROSS_GAME_COACHING_DOCUMENT_KIND
    )
    assert "path" not in content.decode("ascii").lower()


def test_current_catalog_players_without_decisions_retain_zero_count_reports() -> None:
    snapshot = _snapshot(create_match_workspace_v1(_definition(match_id="match-zero-count")))

    report = _report(_store(snapshot, current=(snapshot,)))

    assert report.status == "empty"
    assert tuple(item.player_id for item in report.player_reports) == (
        "player-a",
        "player-b",
        "player-c",
    )
    assert all(item.tactical_decision_count == 0 for item in report.player_reports)
    assert all(item.retained_focus_area_count == 0 for item in report.player_reports)


def test_immediate_teacher_is_descriptive_and_never_focus_eligible() -> None:
    _workspace, _snapshot, _result, _source_report, source, store = _source_bundle(
        recommendation_method="immediate_expected_value",
        decision_index=1,
        match_id="match-tactical-coaching-immediate",
    )
    player_catalog, teachers, tactical, tactical_summary = _coaching_sources(
        store,
        (source,),
    )
    report = build_learning_corpus_tactical_cross_game_coaching_report_v1(
        player_catalog=player_catalog,
        strategy_teacher_collection=teachers,
        tactical_motif_collection=tactical,
        tactical_motif_cross_game_summary=tactical_summary,
    )

    assessment = report.teacher_assessments[0]
    assert assessment.assessment_scope == "immediate_only"
    assert assessment.evidence_basis == "immediate_expected_value"
    assert assessment.eligible_for_focus is False
    assert report.decision_summaries[0].decision_status in {
        "not_assessable",
        "no_teacher",
    }
    assert report.status == "insufficient_evidence"
    assert len(report.player_reports) == 3
    assert [item.player_id for item in report.player_reports] == [
        "player-a",
        "player-b",
        "player-c",
    ]


def test_complete_bounded_search_uses_exact_world_bases() -> None:
    for requested_method, decision_index, expected_basis in (
        ("bounded_search", 22, "bounded_search_sampled_compatible_worlds"),
        ("bounded_search", 24, "bounded_search_all_compatible_worlds"),
    ):
        _workspace, _snapshot, _result, _source_report, source, store = _source_bundle(
            recommendation_method=requested_method,
            decision_index=decision_index,
            match_id=f"match-tactical-coaching-{requested_method}",
            search_random_seed=7,
            search_budget_profile="interactive_v1",
        )
        player_catalog, teachers, tactical, tactical_summary = _coaching_sources(
            store,
            (source,),
        )
        report = build_learning_corpus_tactical_cross_game_coaching_report_v1(
            player_catalog=player_catalog,
            strategy_teacher_collection=teachers,
            tactical_motif_collection=tactical,
            tactical_motif_cross_game_summary=tactical_summary,
        )

        assessment = report.teacher_assessments[0]
        assert assessment.assessment_scope == "complete_search"
        assert assessment.evidence_basis == expected_basis
        assert assessment.assessment_status in {
            "forced_move",
            "best_or_equivalent",
            "strictly_below_best",
        }


@pytest.mark.parametrize(
    ("coverage", "compatible_world_count", "expected_basis"),
    (
        ("sampled_compatible_worlds", 3, "information_set_sampled_compatible_worlds"),
        ("all_compatible_worlds", 2, "information_set_all_compatible_worlds"),
        ("all_compatible_worlds", 1, "information_set_single_exact_world"),
    ),
)
def test_complete_information_set_search_uses_retained_rank_and_world_basis(
    coverage: str,
    compatible_world_count: int,
    expected_basis: str,
) -> None:
    teacher = _information_set_teacher_stub(
        coverage=coverage,
        compatible_world_count=compatible_world_count,
    )

    values = _information_set_assessment_values(teacher, game_type="grand")

    assert values["assessment_scope"] == "complete_search"
    assert values["evidence_basis"] == expected_basis
    assert values["assessment_status"] == "strictly_below_best"
    assert values["actual_card_rank"] == 2
    assert values["strictly_better_card_count"] == 1


def test_information_set_aggregate_equivalent_card_is_best_without_reranking() -> None:
    teacher = _information_set_teacher_stub(
        coverage="all_compatible_worlds",
        compatible_world_count=2,
        aggregate_equivalent=True,
    )

    values = _information_set_assessment_values(teacher, game_type="grand")

    assert values["assessment_status"] == "best_or_equivalent"
    assert values["actual_card_rank"] == 2
    assert values["best_card_rank"] == 1
    assert values["strictly_better_card_count"] == 0
    assert values["aggregate_equivalent"] is True


@pytest.mark.parametrize("search_status", ("partial", "timeout"))
def test_incomplete_information_set_search_is_not_assessable(search_status: str) -> None:
    teacher = _information_set_teacher_stub(
        coverage="sampled_compatible_worlds",
        compatible_world_count=3,
        search_status=search_status,
    )

    values = _information_set_assessment_values(teacher, game_type="grand")

    assert values["assessment_scope"] == "none"
    assert values["evidence_basis"] == "none"
    assert values["assessment_status"] == "not_assessable"


def test_information_set_null_assessment_omits_card_point_margin() -> None:
    teacher = _information_set_teacher_stub(
        coverage="all_compatible_worlds",
        compatible_world_count=2,
        game_type="null",
    )

    values = _information_set_assessment_values(teacher, game_type="null")

    assert values["assessment_status"] == "strictly_below_best"
    assert values["impact_tier"] == "contract_success"
    assert values["mean_local_side_card_point_margin_gap"] is None


def test_canonical_bounded_one_world_uses_single_exact_world_basis() -> None:
    _workspace, _snapshot, _result, _source_report, source, store = _source_bundle(
        recommendation_method="bounded_search",
        decision_index=30,
        match_id="match-tactical-coaching-bounded-single-world",
        search_random_seed=7,
        search_budget_profile="interactive_v1",
    )

    assessment = _report(store, (source,)).teacher_assessments[0]

    assert assessment.assessment_scope == "complete_search"
    assert assessment.evidence_basis == "bounded_search_single_exact_world"
    assert assessment.assessment_status == "forced_move"


def test_information_set_unavailable_is_not_assessable_without_fallback() -> None:
    _workspace, _snapshot, _result, _source_report, source, store = _source_bundle(
        recommendation_method="information_set_search",
        decision_index=1,
        match_id="match-tactical-coaching-information-set-unavailable",
        search_random_seed=7,
        search_budget_profile="interactive_v1",
    )

    report = _report(store, (source,))
    assessment = report.teacher_assessments[0]
    summary = next(item for item in report.decision_summaries if item.exact_teacher_count)
    assert assessment.assessment_scope == "none"
    assert assessment.assessment_status == "not_assessable"
    assert assessment.eligible_for_focus is False
    assert summary.decision_status == "not_assessable"
    assert summary.eligible_for_focus is False


def test_auto_follows_its_retained_effective_method() -> None:
    expected = (
        (1, "immediate_expected_value", "immediate_only"),
        (22, "compatible_world_minimax_v1", "complete_search"),
    )
    for decision_index, effective_method, scope in expected:
        _workspace, _snapshot, _result, _source_report, source, store = _source_bundle(
            recommendation_method="auto",
            decision_index=decision_index,
            match_id=f"match-tactical-coaching-auto-{decision_index}",
            search_random_seed=7,
            search_budget_profile="interactive_v1",
        )
        assessment = _report(store, (source,)).teacher_assessments[0]
        assert assessment.requested_method == "auto"
        assert assessment.effective_method == effective_method
        assert assessment.assessment_scope == scope


def test_auto_without_an_effective_recommendation_is_not_assessable() -> None:
    teacher = SimpleNamespace(
        recommendation_method_summary={"effective_method": "none"},
        post_game_review_summary={"is_available": False},
        actual_card_played="C8",
    )
    tactical = SimpleNamespace(
        game_type="grand",
        observation=SimpleNamespace(
            decision_time_facts=SimpleNamespace(legal_card_count=2),
        ),
    )

    values = _assessment_values(tactical, teacher)

    assert values["assessment_scope"] == "none"
    assert values["assessment_status"] == "not_assessable"


@pytest.mark.parametrize(
    ("better_card_count", "expected_status", "expected_impact"),
    (
        (0, "best_or_equivalent", "no_missed_impact"),
        (1, "strictly_below_best", "immediate_only"),
    ),
)
def test_immediate_assessment_remains_descriptive(
    better_card_count: int,
    expected_status: str,
    expected_impact: str,
) -> None:
    teacher = SimpleNamespace(
        actual_card_played="C8",
        legal_cards=("CA", "C8"),
        post_game_review_summary={
            "is_available": True,
            "actual_card_played": "C8",
            "recommended_card": "CA",
            "actual_card_rank": better_card_count + 1,
            "recommended_card_rank": 1,
            "better_card_count": better_card_count,
            "expected_point_swing_difference": float(better_card_count),
        },
    )

    values = _immediate_assessment_values(teacher)

    assert values["assessment_scope"] == "immediate_only"
    assert values["assessment_status"] == expected_status
    assert values["impact_tier"] == expected_impact


def test_elapsed_only_duplicate_reports_remain_exact_and_count_once_semantically() -> None:
    _workspace, snapshot, result, _source_report, source, store = _source_bundle(
        recommendation_method="bounded_search",
        decision_index=1,
        match_id="match-tactical-coaching-duplicates",
        search_random_seed=0,
        search_budget_profile="interactive_v1",
    )
    changed_document = result.result.to_dict()["document"]
    changed_document["bounded_search_result"]["consumed_budget"][
        "wall_clock_elapsed_ms"
    ] += 1
    duplicate = build_learning_corpus_strategy_teacher_report_source_v1(
        match_snapshot_id=snapshot.match_snapshot_id,
        report=_changed_report(result, result_document=changed_document),
    )

    report = _report(store, (source, duplicate))
    covered = next(item for item in report.decision_summaries if item.exact_teacher_count)
    assert covered.exact_teacher_count == 2
    assert covered.semantic_teacher_count == 1
    assert len(covered.teacher_assessment_ids) == 2
    assert len(set(covered.teacher_assessment_ids)) == 2
    assert len(covered.teacher_semantic_fingerprints) == 1


def test_direct_exact_assessment_builder_reconciles_join_fields() -> None:
    _workspace, _snapshot, _result, _source_report, source, store = _source_bundle(
        recommendation_method="immediate_expected_value",
        decision_index=2,
        match_id="match-tactical-coaching-direct",
    )
    _catalog, teachers, tactical, _summary = _coaching_sources(store, (source,))
    teacher = teachers.evidences[0]
    evidence = next(
        item
        for item in tactical.evidences
        if item.decision_reference_id == teacher.decision_reference_id
    )

    assessment = build_learning_corpus_tactical_coaching_teacher_assessment_v1(
        tactical_motif_evidence=evidence,
        strategy_teacher_evidence=teacher,
    )
    assert assessment.match_snapshot_id == evidence.match_snapshot_id
    assert assessment.game_reference_id == evidence.game_reference_id
    assert assessment.decision_reference_id == evidence.decision_reference_id
    assert assessment.acting_player_id == evidence.acting_player_id
    assert assessment.actual_card_played == evidence.actual_card_played


def test_direct_assessment_rejects_a_non_exact_join() -> None:
    first = _source_bundle(
        recommendation_method="immediate_expected_value",
        decision_index=1,
        match_id="match-tactical-coaching-join-first",
    )
    second = _source_bundle(
        recommendation_method="immediate_expected_value",
        decision_index=2,
        match_id="match-tactical-coaching-join-second",
    )
    _catalog, teachers, _tactical, _summary = _coaching_sources(first[5], (first[4],))
    _catalog, _teachers, tactical, _summary = _coaching_sources(second[5])

    with pytest.raises(ValueError, match="join on all exact facts"):
        build_learning_corpus_tactical_coaching_teacher_assessment_v1(
            tactical_motif_evidence=tactical.evidences[0],
            strategy_teacher_evidence=teachers.evidences[0],
        )


def test_no_teacher_and_skipped_tactical_teacher_coverage_are_explicit() -> None:
    _workspace, _snapshot, _result, _source_report, source, store = _source_bundle(
        recommendation_method="immediate_expected_value",
        decision_index=2,
        match_id="match-tactical-coaching-unjoined",
    )
    player_catalog, teachers, tactical, _summary = _coaching_sources(store, (source,))
    teacher = teachers.evidences[0]
    target = next(
        item
        for item in tactical.evidences
        if item.decision_reference_id == teacher.decision_reference_id
    )
    skipped_tactical = _replace_tactical_evidence_with_skip(tactical, target)
    skipped_summary = build_learning_corpus_tactical_motif_cross_game_summary_v1(
        skipped_tactical,
        player_catalog,
    )

    report = build_learning_corpus_tactical_cross_game_coaching_report_v1(
        player_catalog=player_catalog,
        strategy_teacher_collection=teachers,
        tactical_motif_collection=skipped_tactical,
        tactical_motif_cross_game_summary=skipped_summary,
    )
    assert report.joined_teacher_evidence_count == 0
    assert report.unjoined_teacher_evidence_count == 1
    assert report.unjoined_strategy_teacher_evidence_ids == (
        teacher.strategy_teacher_evidence_id,
    )
    assert all(
        item.decision_reference_id != teacher.decision_reference_id
        for item in report.decision_summaries
    )
    no_teacher = next(
        item
        for item in report.decision_summaries
        if item.decision_status == "no_teacher"
    )
    assert no_teacher.exact_teacher_count == 0


def test_bounded_completed_common_prefix_is_descriptive_only(monkeypatch) -> None:
    def partial_search(*, information_view, requested_budget, random_seed):
        complete = _below_best_search_result(
            information_view=information_view,
            requested_budget=requested_budget,
            random_seed=random_seed,
            expected_seed=9,
            below_best_cards=frozenset({"C8"}),
        )
        return replace(
            complete,
            status="partial",
            stop_reason="node_budget_exhausted",
            solution_claim="node_limited_partial",
            consumed_budget=replace(
                complete.consumed_budget,
                nodes_expanded=complete.requested_budget.max_nodes,
                selected_world_count=9,
                completed_world_count=8,
                sampled_world_count=9,
                unique_sampled_world_count=9,
            ),
            compatible_world_count=9,
            candidate_results=tuple(
                replace(
                    candidate,
                    completed_world_count=8,
                    local_contract_success_count=(
                        0 if candidate.local_contract_success_rate == 0.0 else 8
                    ),
                )
                for candidate in complete.candidate_results
            ),
        )

    monkeypatch.setattr(
        "skatmind.recommendation_workflow.solve_compatible_world_minimax",
        partial_search,
    )
    _workspace, _snapshot, _result, _source_report, source, store = _source_bundle(
        recommendation_method="bounded_search",
        decision_index=22,
        match_id="match-tactical-coaching-common-prefix",
        search_random_seed=9,
        search_budget_profile="interactive_v1",
    )

    assessment = _report(store, (source,)).teacher_assessments[0]
    assert assessment.assessment_scope == "completed_common_prefix"
    assert assessment.evidence_basis == "bounded_search_completed_common_prefix"
    assert assessment.eligible_for_focus is False


def test_repeated_below_best_decisions_across_games_build_bounded_focus(
    monkeypatch,
) -> None:
    def search(*, information_view, requested_budget, random_seed):
        return _below_best_search_result(
            information_view=information_view,
            requested_budget=requested_budget,
            random_seed=random_seed,
            expected_seed=9,
            below_best_cards=frozenset({"C8"}),
        )

    monkeypatch.setattr(
        "skatmind.recommendation_workflow.solve_compatible_world_minimax",
        search,
    )
    first = _source_bundle(
        recommendation_method="bounded_search",
        decision_index=22,
        match_id="match-tactical-focus-a",
        search_random_seed=9,
        search_budget_profile="interactive_v1",
    )
    second = _source_bundle(
        recommendation_method="bounded_search",
        decision_index=22,
        match_id="match-tactical-focus-b",
        search_random_seed=9,
        search_budget_profile="interactive_v1",
    )
    store = _store(
        first[1],
        second[1],
        current=(first[1], second[1]),
    )
    monkeypatch.setattr(
        "skatmind.recommendation_workflow.solve_compatible_world_minimax",
        lambda **_kwargs: pytest.fail("Coaching reran bounded Search"),
    )

    report = _report(store, (first[4], second[4]))

    assert report.status == "available"
    assert report.strictly_below_best_decision_count == 2
    assert report.focus_area_count == 2
    assert report.player_with_focus_count == 1
    player = next(item for item in report.player_reports if item.player_id == "player-a")
    assert player.eligible_focus_candidate_count == 2
    assert player.retained_focus_area_count == 2
    assert all(item.qualifying_decision_count == 2 for item in player.focus_areas)
    assert all(item.distinct_game_count == 2 for item in player.focus_areas)
    assert all(item.distinct_match_count == 2 for item in player.focus_areas)
    assert all(item.primary_impact_tier == "contract_success" for item in player.focus_areas)
    assert all(
        item.guidance_code == "review_repeated_contract_success_gap"
        for item in player.focus_areas
    )
    forbidden = (
        "mistake",
        "wrong",
        "weakness",
        "strength",
        "habit",
        "tendency",
        "signal",
        "communication",
        "caused",
        "optimal",
        "ground truth",
    )
    assert not any(
        word in item.guidance_text.lower()
        for item in player.focus_areas
        for word in forbidden
    )
    assert all(item.retained_focus_area_count == 0 for item in report.player_reports[1:])


def test_repeated_below_best_decisions_in_two_games_of_one_match_build_focus(
    monkeypatch,
) -> None:
    def search(*, information_view, requested_budget, random_seed):
        return _below_best_search_result(
            information_view=information_view,
            requested_budget=requested_budget,
            random_seed=random_seed,
            expected_seed=9,
            below_best_cards=frozenset({"C8"}),
        )

    monkeypatch.setattr(
        "skatmind.recommendation_workflow.solve_compatible_world_minimax",
        search,
    )
    definition = _definition(match_id="match-tactical-two-games")
    workspace = create_match_workspace_v1(definition)
    workspace = _set_game(
        workspace,
        _complete_observed_game(definition, match_position=3, game_id="coaching-game-3"),
    )
    workspace = _set_game(
        workspace,
        _complete_observed_game(definition, match_position=6, game_id="coaching-game-6"),
    )
    first = _source_bundle(
        recommendation_method="bounded_search",
        decision_index=22,
        match_position=3,
        search_random_seed=9,
        search_budget_profile="interactive_v1",
        workspace=workspace,
    )
    second = _source_bundle(
        recommendation_method="bounded_search",
        decision_index=22,
        match_position=6,
        search_random_seed=9,
        search_budget_profile="interactive_v1",
        workspace=workspace,
    )

    report = _report(first[5], (first[4], second[4]))
    player = next(item for item in report.player_reports if item.player_id == "player-a")

    assert report.status == "available"
    assert player.retained_focus_area_count == 2
    assert all(item.recurrence_scope == "multiple_games_one_match" for item in player.focus_areas)
    assert all(item.distinct_game_count == 2 for item in player.focus_areas)
    assert all(item.distinct_match_count == 1 for item in player.focus_areas)


def test_two_below_best_decisions_in_one_game_do_not_build_focus(monkeypatch) -> None:
    def search(*, information_view, requested_budget, random_seed):
        return _below_best_search_result(
            information_view=information_view,
            requested_budget=requested_budget,
            random_seed=random_seed,
            expected_seed=9,
            below_best_cards=frozenset({"C8", "C7"}),
        )

    monkeypatch.setattr(
        "skatmind.recommendation_workflow.solve_compatible_world_minimax",
        search,
    )
    first = _source_bundle(
        recommendation_method="bounded_search",
        decision_index=22,
        match_id="match-tactical-one-game",
        search_random_seed=9,
        search_budget_profile="interactive_v1",
    )
    second = _source_bundle(
        recommendation_method="bounded_search",
        decision_index=25,
        match_id="match-tactical-one-game",
        search_random_seed=9,
        search_budget_profile="interactive_v1",
    )
    assert first[1].match_snapshot_id == second[1].match_snapshot_id

    report = _report(first[5], (first[4], second[4]))
    covered = tuple(
        item for item in report.decision_summaries if item.decision_index in {22, 25}
    )
    assert {item.decision_status for item in covered} == {"strictly_below_best"}
    assert len({item.game_reference_id for item in covered}) == 1
    assert report.strictly_below_best_decision_count == 2
    assert report.status == "insufficient_evidence"
    assert report.focus_area_count == 0


def test_distinct_semantic_complete_search_disagreement_is_mixed(monkeypatch) -> None:
    first = _source_bundle(
        recommendation_method="bounded_search",
        decision_index=22,
        match_id="match-tactical-mixed-consensus",
        search_random_seed=9,
        search_budget_profile="interactive_v1",
    )

    def search(*, information_view, requested_budget, random_seed):
        return _below_best_search_result(
            information_view=information_view,
            requested_budget=requested_budget,
            random_seed=random_seed,
            expected_seed=9,
            below_best_cards=frozenset({"C8"}),
        )

    monkeypatch.setattr(
        "skatmind.recommendation_workflow.solve_compatible_world_minimax",
        search,
    )
    second = _source_bundle(
        recommendation_method="bounded_search",
        decision_index=22,
        match_id="match-tactical-mixed-consensus",
        search_random_seed=9,
        search_budget_profile="interactive_v1",
    )
    assert first[1].match_snapshot_id == second[1].match_snapshot_id

    report = _report(first[5], (first[4], second[4]))
    summary = next(item for item in report.decision_summaries if item.exact_teacher_count)
    assert summary.exact_teacher_count == 2
    assert summary.semantic_teacher_count == 2
    assert summary.decision_status == "mixed"
    assert summary.eligible_for_focus is False
    assert report.mixed_decision_count == 1
    assert report.focus_area_count == 0

    first_assessment, second_assessment = report.teacher_assessments
    conflicting_values = second_assessment.to_dict()
    conflicting_values["teacher_assessment_id"] = "0" * 64
    conflicting_values["teacher_semantic_fingerprint"] = (
        first_assessment.teacher_semantic_fingerprint
    )
    provisional = LearningCorpusTacticalCoachingTeacherAssessmentV1._from_validated(
        **conflicting_values
    )
    conflicting_values["teacher_assessment_id"] = _build_coaching_identifier_v1(
        LEARNING_CORPUS_TACTICAL_COACHING_TEACHER_ASSESSMENT_ID_DOMAIN,
        _identity_material_v1(provisional, "teacher_assessment_id"),
    )
    conflicting = LearningCorpusTacticalCoachingTeacherAssessmentV1._from_validated(
        **conflicting_values
    )
    with pytest.raises(ValueError, match="conflicting Assessments"):
        _semantic_assessments((first_assessment, conflicting))


def test_player_focus_areas_are_capped_at_five(monkeypatch) -> None:
    def search(*, information_view, requested_budget, random_seed):
        return _below_best_search_result(
            information_view=information_view,
            requested_budget=requested_budget,
            random_seed=random_seed,
            expected_seed=9,
            below_best_cards=frozenset({"H7", "DA"}),
        )

    monkeypatch.setattr(
        "skatmind.recommendation_workflow.solve_compatible_world_minimax",
        search,
    )
    bundles = tuple(
        _source_bundle(
            recommendation_method="bounded_search",
            decision_index=decision_index,
            match_id=match_id,
            search_random_seed=9,
            search_budget_profile="interactive_v1",
        )
        for match_id in ("match-tactical-cap-a", "match-tactical-cap-b")
        for decision_index in (12, 15)
    )
    assert bundles[0][1].match_snapshot_id == bundles[1][1].match_snapshot_id
    assert bundles[2][1].match_snapshot_id == bundles[3][1].match_snapshot_id
    store = _store(
        bundles[0][1],
        bundles[2][1],
        current=(bundles[0][1], bundles[2][1]),
    )

    report = _report(store, tuple(item[4] for item in bundles))
    player = next(item for item in report.player_reports if item.player_id == "player-c")
    assert player.eligible_focus_candidate_count == 6
    assert player.retained_focus_area_count == 5
    assert len(player.focus_areas) == (
        LEARNING_CORPUS_TACTICAL_COACHING_MAXIMUM_FOCUS_AREAS_PER_PLAYER
    )
    candidate_motifs = tuple(
        motif_type
        for motif_type in TACTICAL_MOTIF_TYPES
        if len(
            {
                summary.game_reference_id
                for summary in report.decision_summaries
                if summary.acting_player_id == player.player_id
                and summary.eligible_for_focus
                and motif_type in summary.motif_types
            }
        )
        >= LEARNING_CORPUS_TACTICAL_COACHING_MINIMUM_GAMES
    )
    assert len(candidate_motifs) == 6
    assert tuple(item.motif_type for item in player.focus_areas) == candidate_motifs[:5]


def test_focus_priority_is_objective_then_recurrence_then_canonical_motif() -> None:
    values = (
        SimpleNamespace(
            label="mixed",
            primary_impact_tier="mixed",
            distinct_match_count=3,
            distinct_game_count=3,
            qualifying_decision_count=3,
            motif_type=TACTICAL_MOTIF_TYPES[0],
        ),
        SimpleNamespace(
            label="settlement",
            primary_impact_tier="settlement_score",
            distinct_match_count=2,
            distinct_game_count=2,
            qualifying_decision_count=2,
            motif_type=TACTICAL_MOTIF_TYPES[0],
        ),
        SimpleNamespace(
            label="contract-less-recurrent",
            primary_impact_tier="contract_success",
            distinct_match_count=1,
            distinct_game_count=2,
            qualifying_decision_count=2,
            motif_type=TACTICAL_MOTIF_TYPES[0],
        ),
        SimpleNamespace(
            label="card-margin",
            primary_impact_tier="card_point_margin",
            distinct_match_count=3,
            distinct_game_count=3,
            qualifying_decision_count=3,
            motif_type=TACTICAL_MOTIF_TYPES[0],
        ),
        SimpleNamespace(
            label="contract-canonical-tie",
            primary_impact_tier="contract_success",
            distinct_match_count=2,
            distinct_game_count=2,
            qualifying_decision_count=2,
            motif_type=TACTICAL_MOTIF_TYPES[1],
        ),
        SimpleNamespace(
            label="contract-recurrent",
            primary_impact_tier="contract_success",
            distinct_match_count=2,
            distinct_game_count=2,
            qualifying_decision_count=2,
            motif_type=TACTICAL_MOTIF_TYPES[0],
        ),
    )

    ordered = tuple(item.label for item in sorted(values, key=_focus_priority))

    assert ordered == (
        "contract-recurrent",
        "contract-canonical-tie",
        "contract-less-recurrent",
        "settlement",
        "card-margin",
        "mixed",
    )
