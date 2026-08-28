from dataclasses import fields

import pytest
from test_learning_corpus_strategy_teacher import (
    _changed_report,
    _source_bundle,
)
from test_learning_dataset_v2 import _dataset
from test_learning_dataset_v2_cross_game_summary import _summary_sources

from skatmind.corpus_web.source_store import (
    LearningCorpusStrategyTeacherSourceStoreV1,
)
from skatmind.errors import SkatMindInvariantError
from skatmind.learning_corpus_information_set_strategy_teacher import (
    LEARNING_CORPUS_INFORMATION_SET_STRATEGY_TEACHER_EXTENSION_VERSION,
    LEARNING_CORPUS_INFORMATION_SET_TEACHER_AUTOMATION_POLICY,
    LEARNING_CORPUS_INFORMATION_SET_TEACHER_COMPARISON_POLICY,
    LEARNING_CORPUS_INFORMATION_SET_TEACHER_IDENTITY_POLICY,
    LEARNING_CORPUS_INFORMATION_SET_TEACHER_POLICY,
    LEARNING_CORPUS_INFORMATION_SET_TEACHER_PRIVACY_POLICY,
    LEARNING_CORPUS_INFORMATION_SET_TEACHER_RESULT_POLICY,
    LearningCorpusInformationSetStrategyTeacherEvidenceV1,
)
from skatmind.learning_corpus_strategy_teacher import (
    build_learning_corpus_strategy_teacher_report_source_v1,
)
from skatmind.learning_corpus_strategy_teacher_builder import (
    build_learning_corpus_strategy_teacher_evidence_collection_v1,
)


@pytest.fixture(scope="module")
def information_set_bundle():
    return _source_bundle(
        recommendation_method="information_set_search",
        decision_index=30,
        match_id="match-information-set-teacher",
        search_random_seed=7,
        search_budget_profile="interactive_v1",
    )


def test_information_set_teacher_version_policies_and_fields_are_exact() -> None:
    assert LEARNING_CORPUS_INFORMATION_SET_STRATEGY_TEACHER_EXTENSION_VERSION == 1
    assert LEARNING_CORPUS_INFORMATION_SET_TEACHER_POLICY == (
        "method_bound_information_set_evidence_not_ground_truth"
    )
    assert LEARNING_CORPUS_INFORMATION_SET_TEACHER_RESULT_POLICY == (
        "retain_safe_aggregate_result_without_controlled_policy_table"
    )
    assert LEARNING_CORPUS_INFORMATION_SET_TEACHER_COMPARISON_POLICY == (
        "same_selection_pimc_and_immediate_are_diagnostic_baselines"
    )
    assert LEARNING_CORPUS_INFORMATION_SET_TEACHER_IDENTITY_POLICY == (
        "exact_source_identity_and_wall_clock_normalized_semantic_identity"
    )
    assert LEARNING_CORPUS_INFORMATION_SET_TEACHER_PRIVACY_POLICY == (
        "minimized_private_evidence_without_worlds_observations_or_policy_table"
    )
    assert LEARNING_CORPUS_INFORMATION_SET_TEACHER_AUTOMATION_POLICY == (
        "explicit_report_transfer_without_automatic_capture"
    )
    assert tuple(
        field.name for field in fields(LearningCorpusInformationSetStrategyTeacherEvidenceV1)
    ) == (
        "learning_corpus_information_set_strategy_teacher_extension_version",
        "information_set_search_result",
        "information_set_search_comparison",
        "search_status",
        "search_stop_reason",
        "world_coverage",
        "policy_claim",
        "policy_consistency",
        "requested_budget",
        "consumed_budget",
        "candidate_results",
        "controlled_policy_decision_count",
        "information_sets_evaluated",
        "fixed_policy_settings",
        "information_set_recommended_card",
        "pimc_recommended_card",
        "immediate_recommended_card",
        "actual_card_played",
        "wall_clock_elapsed_ms",
    )
    with pytest.raises(TypeError, match="focused builder"):
        LearningCorpusInformationSetStrategyTeacherEvidenceV1()


def test_information_set_teacher_retains_safe_result_and_diagnostic_baselines(
    information_set_bundle,
) -> None:
    _workspace, _snapshot, result, _report, source, store = information_set_bundle
    collection = build_learning_corpus_strategy_teacher_evidence_collection_v1(
        store,
        (source,),
    )
    evidence = collection.evidences[0]
    focused = evidence.information_set_search_evidence
    assert focused is not None
    document = result.result.to_dict()["document"]
    search = document["information_set_search_result"]
    comparison = document["information_set_search_comparison"]
    focused_document = focused.to_dict()
    assert focused_document["information_set_search_result"] == search
    assert focused_document["information_set_search_comparison"] == comparison
    assert focused.search_status == search["status"] == "complete"
    assert focused.policy_claim == search["policy_claim"]
    assert focused.policy_consistency == search["policy_consistency"]
    assert (
        focused.information_sets_evaluated
        == search["consumed_budget"]["information_sets_evaluated"]
    )
    assert focused.controlled_policy_decision_count == search["controlled_policy_decision_count"]
    assert focused.pimc_recommended_card == comparison["pimc_recommended_card"]
    assert focused.immediate_recommended_card == comparison["immediate_recommended_card"]
    assert focused.actual_card_played == comparison["actual_card"]
    assert evidence.bounded_search_result is None
    assert evidence.bounded_search_post_game_review_summary is None
    assert evidence.solution_claim is None
    assert evidence.recommendation_method_summary["fallback_used"] is False
    assert evidence.search_status == focused.search_status
    assert evidence.policy_claim == focused.policy_claim
    assert evidence.policy_consistency == focused.policy_consistency
    assert evidence.information_sets_evaluated == focused.information_sets_evaluated
    assert evidence.controlled_policy_decision_count == (focused.controlled_policy_decision_count)
    assert collection.information_set_search_requested_count == 1
    assert collection.search_complete_count == 1

    serialized = focused_document
    forbidden = {
        "controlled_policy",
        "observations",
        "worlds",
        "world_states",
        "exact_states",
        "own_remaining_hand",
        "memoization",
        "bundle_memo",
        "profile_statistics_records",
        "commentaries",
        "responses",
    }

    def keys(value):
        if isinstance(value, dict):
            return set(value) | set().union(*(keys(item) for item in value.values()))
        if isinstance(value, list):
            return set().union(*(keys(item) for item in value))
        return set()

    assert not forbidden & keys(serialized)


def test_information_set_unavailable_is_retained_without_fallback() -> None:
    _workspace, _snapshot, _result, _report, source, store = _source_bundle(
        recommendation_method="information_set_search",
        decision_index=1,
        match_id="match-information-set-unavailable-teacher",
        search_random_seed=7,
        search_budget_profile="interactive_v1",
    )
    collection = build_learning_corpus_strategy_teacher_evidence_collection_v1(
        store,
        (source,),
    )
    evidence = collection.evidences[0]
    focused = evidence.information_set_search_evidence
    assert focused.search_status == "unavailable"
    assert focused.information_set_recommended_card is None
    assert focused.pimc_recommended_card is None
    assert focused.immediate_recommended_card is not None
    assert evidence.status == "recommendation_unavailable"
    assert evidence.recommendation_method_summary["fallback_used"] is False
    assert collection.search_unavailable_count == 1


def test_information_set_elapsed_only_change_preserves_semantic_identity(
    information_set_bundle,
) -> None:
    _workspace, snapshot, result, _report, source, store = information_set_bundle
    changed_document = result.result.to_dict()["document"]
    changed_document["information_set_search_result"]["consumed_budget"][
        "wall_clock_elapsed_ms"
    ] += 1
    changed_source = build_learning_corpus_strategy_teacher_report_source_v1(
        match_snapshot_id=snapshot.match_snapshot_id,
        report=_changed_report(result, result_document=changed_document),
    )
    collection = build_learning_corpus_strategy_teacher_evidence_collection_v1(
        store,
        (source, changed_source),
    )
    first, second = collection.evidences
    assert first.source_report_fingerprint != second.source_report_fingerprint
    assert first.source_result_fingerprint != second.source_result_fingerprint
    assert first.strategy_teacher_evidence_id != second.strategy_teacher_evidence_id
    assert first.teacher_semantic_fingerprint == second.teacher_semantic_fingerprint
    assert first.wall_clock_elapsed_ms != second.wall_clock_elapsed_ms


def test_information_set_teacher_rejects_changed_effective_fixed_policy(
    information_set_bundle,
) -> None:
    _workspace, snapshot, result, _report, _source, store = information_set_bundle
    changed_document = result.result.to_dict()["document"]
    changed_document["left_opponent_policy_settings"]["opponent_lead_policy"] = "highest_point"
    changed_document["information_set_search_result"]["fixed_policy_settings"][0]["lead_policy"] = (
        "highest_point"
    )
    changed_source = build_learning_corpus_strategy_teacher_report_source_v1(
        match_snapshot_id=snapshot.match_snapshot_id,
        report=_changed_report(result, result_document=changed_document),
    )

    with pytest.raises(SkatMindInvariantError, match="effective opponent Policy"):
        build_learning_corpus_strategy_teacher_evidence_collection_v1(
            store,
            (changed_source,),
        )


def test_information_set_method_sorts_after_existing_methods(
    information_set_bundle,
) -> None:
    workspace, snapshot, result, _report, information_source, store = information_set_bundle
    immediate_bundle = _source_bundle(
        recommendation_method="immediate_expected_value",
        decision_index=30,
        match_id=workspace.match_definition.match_id,
    )
    immediate_result = immediate_bundle[2]
    immediate_source = build_learning_corpus_strategy_teacher_report_source_v1(
        match_snapshot_id=snapshot.match_snapshot_id,
        report=_changed_report(immediate_result),
    )
    collection = build_learning_corpus_strategy_teacher_evidence_collection_v1(
        store,
        (information_source, immediate_source),
    )
    assert tuple(item.options.recommendation_method for item in collection.evidences) == (
        "immediate_expected_value",
        "information_set_search",
    )
    assert result.options.recommendation_method == "information_set_search"


def test_information_set_teacher_joins_dataset_and_cross_game_summary(
    information_set_bundle,
) -> None:
    _workspace, _snapshot, _result, _report, source, store = information_set_bundle
    without_teacher = _dataset(
        store,
        dataset_id="dataset-information-set-teacher",
    )
    with_teacher = _dataset(
        store,
        dataset_id="dataset-information-set-teacher",
        teacher_sources=(source,),
    )
    without_record = next(
        item for item in without_teacher.records if item.decision_state.decision_index == 30
    )
    with_record = next(
        item for item in with_teacher.records if item.decision_state.decision_index == 30
    )
    assert without_record.record_id == with_record.record_id
    assert without_record.record_content_fingerprint != (with_record.record_content_fingerprint)
    assert without_record.strategy_teacher_evidence_ids == ()
    assert len(with_record.strategy_teacher_evidence_ids) == 1
    assert len(with_teacher.strategy_teacher_evidences) == 1
    assert with_teacher.strategy_teacher_evidences[0].information_set_search_evidence

    _dataset_value, _catalog, _known, _unseen, summary = _summary_sources(
        store,
        dataset_id="dataset-information-set-summary",
        teacher_sources=(source,),
    )
    strategy = summary.strategy_summary
    assert [(item.category, item.count) for item in strategy.requested_method_counts] == [
        ("immediate_expected_value", 0),
        ("bounded_search", 0),
        ("auto", 0),
        ("information_set_search", 1),
    ]
    assert (
        "bounded_information_set_policy_search_v1",
        1,
    ) in [(item.category, item.count) for item in strategy.effective_method_counts]
    assert strategy.search_status_counts[1].category == "complete"
    assert strategy.search_status_counts[1].count == 1


def test_corpus_source_store_accepts_and_orders_information_set_source(
    information_set_bundle,
) -> None:
    workspace, snapshot, _result, _report, information_source, _store = information_set_bundle
    immediate_bundle = _source_bundle(
        recommendation_method="immediate_expected_value",
        decision_index=30,
        match_id=workspace.match_definition.match_id,
    )
    immediate_source = build_learning_corpus_strategy_teacher_report_source_v1(
        match_snapshot_id=snapshot.match_snapshot_id,
        report=immediate_bundle[3],
    )
    source_store = LearningCorpusStrategyTeacherSourceStoreV1()
    assert source_store.add(information_source) == "applied"
    assert source_store.add(immediate_source) == "applied"
    assert tuple(
        item.report.value.options.recommendation_method for item in source_store.sources
    ) == ("immediate_expected_value", "information_set_search")
