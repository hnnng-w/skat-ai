import hashlib
from dataclasses import FrozenInstanceError, fields, replace

import pytest
from test_learning_corpus_human_evidence import _store
from test_match_decision_analysis import _complete_workspace
from test_match_player_statistics_context import (
    _actionable_snapshot,
    _capture_with_snapshots,
)
from test_match_workspace_contracts import _definition

from skat_ai.api.v1.contracts import RequestDocumentV1, ResultDocumentV1
from skat_ai.learning_corpus_identity import (
    build_learning_corpus_canonical_json_bytes_v1,
)
from skat_ai.learning_corpus_match_snapshot import (
    build_learning_corpus_match_snapshot_v1,
)
from skat_ai.learning_corpus_strategy_teacher import (
    LEARNING_CORPUS_STRATEGY_TEACHER_ACTUAL_CARD_POLICY,
    LEARNING_CORPUS_STRATEGY_TEACHER_CLAIM_POLICY,
    LEARNING_CORPUS_STRATEGY_TEACHER_COLLECTION_VERSION,
    LEARNING_CORPUS_STRATEGY_TEACHER_DATASET_POLICY,
    LEARNING_CORPUS_STRATEGY_TEACHER_EVIDENCE_VERSION,
    LEARNING_CORPUS_STRATEGY_TEACHER_EXECUTION_POLICY,
    LEARNING_CORPUS_STRATEGY_TEACHER_EXPORT_POLICY,
    LEARNING_CORPUS_STRATEGY_TEACHER_METHOD_POLICY,
    LEARNING_CORPUS_STRATEGY_TEACHER_MULTIPLE_REPORT_POLICY,
    LEARNING_CORPUS_STRATEGY_TEACHER_PRIVACY_POLICY,
    LEARNING_CORPUS_STRATEGY_TEACHER_PROFILE_POLICY,
    LEARNING_CORPUS_STRATEGY_TEACHER_RECONCILIATION_POLICY,
    LEARNING_CORPUS_STRATEGY_TEACHER_REPORT_POLICY,
    LEARNING_CORPUS_STRATEGY_TEACHER_SEARCH_STATUSES,
    LEARNING_CORPUS_STRATEGY_TEACHER_SEMANTIC_ID_POLICY,
    LEARNING_CORPUS_STRATEGY_TEACHER_SOURCE_POLICY,
    LEARNING_CORPUS_STRATEGY_TEACHER_SOURCE_REPORT_KINDS,
    LEARNING_CORPUS_STRATEGY_TEACHER_SOURCE_VERSION,
    LEARNING_CORPUS_STRATEGY_TEACHER_STATUSES,
    LearningCorpusStrategyTeacherEvidenceCollectionV1,
    LearningCorpusStrategyTeacherEvidenceV1,
    build_learning_corpus_strategy_teacher_report_fingerprint_v1,
    build_learning_corpus_strategy_teacher_report_source_v1,
    build_learning_corpus_strategy_teacher_request_fingerprint_v1,
    build_learning_corpus_strategy_teacher_result_fingerprint_v1,
)
from skat_ai.learning_corpus_strategy_teacher_builder import (
    build_learning_corpus_strategy_teacher_evidence_collection_v1,
)
from skat_ai.match_analysis_contracts import (
    MatchDecisionAnalysisOptionsV1,
    MatchHistoricalAnalysisOptionsV1,
    build_match_analysis_report_v1,
    prepare_match_materialization_report_v1,
)
from skat_ai.match_decision_analysis import execute_match_decision_analysis_v1
from skat_ai.match_historical_analysis import execute_match_historical_analysis_v1
from skat_ai.match_workspace_persistence_codec import (
    build_match_workspace_persistence_document_v1,
)


def _hash(domain: bytes, value: object) -> str:
    return hashlib.sha256(
        domain + build_learning_corpus_canonical_json_bytes_v1(value)
    ).hexdigest()


def _snapshot(workspace):
    return build_learning_corpus_match_snapshot_v1(
        build_match_workspace_persistence_document_v1(workspace)
    )


def _source_bundle(
    *,
    recommendation_method="immediate_expected_value",
    decision_index=1,
    match_id="match-teacher",
    match_position=3,
    search_random_seed=None,
    search_budget_profile="historical_review_v1",
    use_profile_presets=True,
    dependencies=None,
    workspace=None,
):
    workspace = workspace or _complete_workspace(definition=_definition(match_id=match_id))
    snapshot = _snapshot(workspace)
    options = MatchDecisionAnalysisOptionsV1(
        recommendation_method=recommendation_method,
        immediate_sample_count=1,
        search_random_seed=search_random_seed,
        search_budget_profile=search_budget_profile,
        use_profile_presets=use_profile_presets,
    )
    result = execute_match_decision_analysis_v1(
        workspace,
        match_position=match_position,
        decision_index=decision_index,
        options=options,
        dependencies=dependencies,
    )
    report = build_match_analysis_report_v1(result)
    source = build_learning_corpus_strategy_teacher_report_source_v1(
        match_snapshot_id=snapshot.match_snapshot_id,
        report=report,
    )
    store = _store(snapshot, current=(snapshot,))
    return workspace, snapshot, result, report, source, store


@pytest.fixture(scope="module")
def immediate_bundle():
    return _source_bundle()


def test_versions_tuples_and_policies_are_exact() -> None:
    assert LEARNING_CORPUS_STRATEGY_TEACHER_SOURCE_VERSION == 1
    assert LEARNING_CORPUS_STRATEGY_TEACHER_EVIDENCE_VERSION == 1
    assert LEARNING_CORPUS_STRATEGY_TEACHER_COLLECTION_VERSION == 1
    assert LEARNING_CORPUS_STRATEGY_TEACHER_SOURCE_REPORT_KINDS == (
        "decision_analysis",
    )
    assert LEARNING_CORPUS_STRATEGY_TEACHER_STATUSES == (
        "recommendation_available",
        "recommendation_unavailable",
    )
    assert LEARNING_CORPUS_STRATEGY_TEACHER_SEARCH_STATUSES == (
        "not_attempted",
        "complete",
        "partial",
        "timeout",
        "unavailable",
    )
    assert (
        LEARNING_CORPUS_STRATEGY_TEACHER_SOURCE_POLICY
        == "explicit_current_match_snapshot_bound_decision_reports"
    )
    assert (
        LEARNING_CORPUS_STRATEGY_TEACHER_REPORT_POLICY
        == "exact_executed_decision_analysis_reports_only"
    )
    assert (
        LEARNING_CORPUS_STRATEGY_TEACHER_RECONCILIATION_POLICY
        == "rebuild_request_without_analysis_execution"
    )
    assert (
        LEARNING_CORPUS_STRATEGY_TEACHER_CLAIM_POLICY
        == "method_bound_evidence_not_ground_truth"
    )
    assert (
        LEARNING_CORPUS_STRATEGY_TEACHER_ACTUAL_CARD_POLICY
        == "retrospective_observed_behavior_not_optimal_label"
    )
    assert (
        LEARNING_CORPUS_STRATEGY_TEACHER_METHOD_POLICY
        == "preserve_existing_method_budget_status_and_candidate_semantics"
    )
    assert (
        LEARNING_CORPUS_STRATEGY_TEACHER_MULTIPLE_REPORT_POLICY
        == "retain_distinct_reports_without_preferred_teacher"
    )
    assert (
        LEARNING_CORPUS_STRATEGY_TEACHER_SEMANTIC_ID_POLICY
        == "exclude_wall_clock_elapsed_time_only"
    )
    assert (
        LEARNING_CORPUS_STRATEGY_TEACHER_PROFILE_POLICY
        == "retain_existing_binding_and_application_context_without_rederivation"
    )
    assert (
        LEARNING_CORPUS_STRATEGY_TEACHER_EXECUTION_POLICY
        == "no_analysis_execution_or_rerun"
    )
    assert (
        LEARNING_CORPUS_STRATEGY_TEACHER_PRIVACY_POLICY
        == "private_local_minimized_unredacted_strategy_evidence"
    )
    assert (
        LEARNING_CORPUS_STRATEGY_TEACHER_EXPORT_POLICY
        == "deterministic_path_free_json_document"
    )
    assert (
        LEARNING_CORPUS_STRATEGY_TEACHER_DATASET_POLICY
        == "no_training_dataset_version_1_influence"
    )


def test_report_source_fields_and_fingerprints_are_exact(immediate_bundle) -> None:
    _workspace, snapshot, result, report, source, _store_value = immediate_bundle
    assert tuple(field.name for field in fields(source)) == (
        "learning_corpus_strategy_teacher_source_version",
        "source_binding_id",
        "match_snapshot_id",
        "source_report_id",
        "source_report_fingerprint",
        "source_request_fingerprint",
        "source_result_fingerprint",
        "report",
    )
    assert source.source_report_id == report.report_id
    assert source.source_report_fingerprint == _hash(
        b"skat-ai\0learning_corpus_strategy_teacher_report_v1\0",
        report.to_dict(),
    )
    assert source.source_request_fingerprint == _hash(
        b"skat-ai\0learning_corpus_strategy_teacher_request_v1\0",
        result.request.to_dict(),
    )
    assert source.source_result_fingerprint == _hash(
        b"skat-ai\0learning_corpus_strategy_teacher_result_v1\0",
        result.result.to_dict(),
    )
    binding_material = {
        "learning_corpus_strategy_teacher_source_version": 1,
        "match_snapshot_id": snapshot.match_snapshot_id,
        "source_report_id": source.source_report_id,
        "source_report_fingerprint": source.source_report_fingerprint,
        "source_request_fingerprint": source.source_request_fingerprint,
        "source_result_fingerprint": source.source_result_fingerprint,
    }
    assert source.source_binding_id == _hash(
        b"skat-ai\0learning_corpus_strategy_teacher_source_binding_v1\0",
        binding_material,
    )
    assert build_learning_corpus_strategy_teacher_report_fingerprint_v1(report) == (
        source.source_report_fingerprint
    )
    assert build_learning_corpus_strategy_teacher_request_fingerprint_v1(
        result.request
    ) == source.source_request_fingerprint
    assert build_learning_corpus_strategy_teacher_result_fingerprint_v1(
        result.result
    ) == source.source_result_fingerprint
    changed = source.to_dict()
    changed["report"]["value"]["options"]["immediate_random_seed"] = 99
    assert source.to_dict()["report"]["value"]["options"][
        "immediate_random_seed"
    ] == 0


def test_source_is_frozen_slotted_and_rejects_non_decision_reports(
    immediate_bundle,
) -> None:
    workspace, snapshot, _result, _report, source, _store_value = immediate_bundle
    assert not hasattr(source, "__dict__")
    with pytest.raises(FrozenInstanceError):
        source.source_binding_id = "0" * 64
    materialization = build_match_analysis_report_v1(
        prepare_match_materialization_report_v1(workspace)
    )
    with pytest.raises(ValueError, match="decision_analysis"):
        build_learning_corpus_strategy_teacher_report_source_v1(
            match_snapshot_id=snapshot.match_snapshot_id,
            report=materialization,
        )
    from skat_ai.match_workspace_contracts import create_match_workspace_v1

    historical = execute_match_historical_analysis_v1(
        create_match_workspace_v1(_definition(match_id="match-historical")),
        match_position=1,
        options=MatchHistoricalAnalysisOptionsV1(immediate_sample_count=1),
    )
    with pytest.raises(ValueError, match="decision_analysis"):
        build_learning_corpus_strategy_teacher_report_source_v1(
            match_snapshot_id=snapshot.match_snapshot_id,
            report=build_match_analysis_report_v1(historical),
        )
    with pytest.raises(ValueError, match="exact MatchAnalysisReportV1"):
        build_learning_corpus_strategy_teacher_report_source_v1(
            match_snapshot_id=snapshot.match_snapshot_id,
            report=object(),
        )


def test_source_rejects_unavailable_decision_report() -> None:
    from skat_ai.match_workspace_contracts import create_match_workspace_v1

    workspace = create_match_workspace_v1(_definition(match_id="match-unavailable"))
    result = execute_match_decision_analysis_v1(
        workspace,
        match_position=1,
        decision_index=1,
        options=MatchDecisionAnalysisOptionsV1(immediate_sample_count=1),
    )
    with pytest.raises(ValueError, match="executed Decision Report"):
        build_learning_corpus_strategy_teacher_report_source_v1(
            match_snapshot_id="0" * 64,
            report=build_match_analysis_report_v1(result),
        )


def test_immediate_collection_preserves_exact_minimized_evidence(
    immediate_bundle,
) -> None:
    _workspace, snapshot, result, _report, source, store = immediate_bundle
    collection = build_learning_corpus_strategy_teacher_evidence_collection_v1(
        store,
        (source,),
    )
    evidence = collection.evidences[0]
    document = result.result.to_dict()["document"]
    play = snapshot.workspace.slots[2].observed_game.plays[0]
    assert evidence.match_snapshot_id == snapshot.match_snapshot_id
    assert evidence.actual_card_played == play.card
    assert evidence.acting_player_id == play.player_id
    assert evidence.options is result.options
    assert evidence.profile_binding is result.profile_binding
    assert evidence.status == "recommendation_available"
    assert evidence.search_status == "not_attempted"
    assert evidence.immediate_candidate_results == tuple(document["analysis_report"])
    assert evidence.recommendation == document["recommendation"]
    assert evidence.strategic_summary == document["strategic_summary"]
    assert evidence.to_dict()["post_game_review_summary"] == document[
        "post_game_review_summary"
    ]
    assert evidence.bounded_search_result is None
    assert evidence.bounded_search_post_game_review_summary is None
    assert evidence.search_stop_reason is None
    assert evidence.requested_budget is None
    assert evidence.consumed_budget is None
    assert evidence.search_candidate_results == ()
    assert evidence.wall_clock_elapsed_ms is None
    assert collection.source_report_count == collection.evidence_count == 1
    assert collection.distinct_decision_count == 1
    assert collection.recommendation_available_count == 1
    assert collection.immediate_requested_count == 1
    assert collection.search_not_attempted_count == 1
    assert collection.search_attempted_count == 0
    serialized = evidence.to_dict()
    forbidden_keys = {
        "hand",
        "skat",
        "discarded_cards",
        "commentaries",
        "response_links",
        "compatible_worlds",
    }
    assert forbidden_keys.isdisjoint(serialized)
    serialized["legal_cards"].append("C7")
    assert evidence.to_dict()["legal_cards"] == document["legal_cards"]


def test_evidence_and_collection_are_builder_controlled() -> None:
    with pytest.raises(TypeError):
        LearningCorpusStrategyTeacherEvidenceV1()
    with pytest.raises(TypeError):
        LearningCorpusStrategyTeacherEvidenceCollectionV1()
    with pytest.raises(ValueError, match="sources must be an immutable tuple"):
        build_learning_corpus_strategy_teacher_evidence_collection_v1(
            _store(),
            [],
        )


def test_empty_collection_is_valid_and_deterministic() -> None:
    first = build_learning_corpus_strategy_teacher_evidence_collection_v1(
        _store(),
        (),
    )
    second = build_learning_corpus_strategy_teacher_evidence_collection_v1(
        _store(),
        (),
    )
    assert first == second
    assert first.source_report_count == first.evidence_count == 0
    assert first.distinct_decision_count == 0
    assert first.current_match_snapshot_ids == first.evidences == ()


def test_non_current_same_revision_snapshot_binding_is_rejected() -> None:
    old_workspace = _complete_workspace(
        definition=_definition(match_id="match-current", title="Old title")
    )
    current_workspace = _complete_workspace(
        definition=_definition(match_id="match-current", title="Current title")
    )
    old_snapshot = _snapshot(old_workspace)
    current_snapshot = _snapshot(current_workspace)
    result = execute_match_decision_analysis_v1(
        old_workspace,
        match_position=3,
        decision_index=1,
        options=MatchDecisionAnalysisOptionsV1(immediate_sample_count=1),
    )
    source = build_learning_corpus_strategy_teacher_report_source_v1(
        match_snapshot_id=old_snapshot.match_snapshot_id,
        report=build_match_analysis_report_v1(result),
    )
    store = _store(
        old_snapshot,
        current_snapshot,
        current=(current_snapshot,),
    )
    with pytest.raises(ValueError, match="explicit Current Match Snapshot"):
        build_learning_corpus_strategy_teacher_evidence_collection_v1(
            store,
            (source,),
        )
    current_result = execute_match_decision_analysis_v1(
        current_workspace,
        match_position=3,
        decision_index=1,
        options=MatchDecisionAnalysisOptionsV1(immediate_sample_count=1),
    )
    current_source = build_learning_corpus_strategy_teacher_report_source_v1(
        match_snapshot_id=current_snapshot.match_snapshot_id,
        report=build_match_analysis_report_v1(current_result),
    )
    current_collection = (
        build_learning_corpus_strategy_teacher_evidence_collection_v1(
            store,
            (current_source,),
        )
    )
    assert current_collection.evidences[0].match_snapshot_id == (
        current_snapshot.match_snapshot_id
    )


def test_orphan_and_wrong_logical_match_bindings_are_rejected(
    immediate_bundle,
) -> None:
    _workspace, snapshot, _result, report, _source, _store_value = immediate_bundle
    orphan_id = "f" * 64
    orphan_source = build_learning_corpus_strategy_teacher_report_source_v1(
        match_snapshot_id=orphan_id,
        report=report,
    )
    orphan_store = _store(
        snapshot,
        current=(snapshot,),
        orphans=(orphan_id,),
    )
    with pytest.raises(ValueError, match="explicit Current Match Snapshot"):
        build_learning_corpus_strategy_teacher_evidence_collection_v1(
            orphan_store,
            (orphan_source,),
        )

    _other_workspace, other_snapshot, *_rest = _source_bundle(
        match_id="match-other-binding"
    )
    wrong_source = build_learning_corpus_strategy_teacher_report_source_v1(
        match_snapshot_id=other_snapshot.match_snapshot_id,
        report=report,
    )
    combined_store = _store(
        snapshot,
        other_snapshot,
        current=(snapshot, other_snapshot),
    )
    with pytest.raises(ValueError, match="explicit Current Match Snapshot"):
        build_learning_corpus_strategy_teacher_evidence_collection_v1(
            combined_store,
            (wrong_source,),
        )


def _changed_report(result, *, request_document=None, result_document=None):
    request = result.request
    root_result = result.result
    if request_document is not None:
        request = RequestDocumentV1(
            workflow=request.workflow,
            document=request_document,
        )
    if result_document is not None:
        root_result = ResultDocumentV1(
            workflow=root_result.workflow,
            document=result_document,
            warnings=root_result.warnings,
        )
    return build_match_analysis_report_v1(
        replace(result, request=request, result=root_result)
    )


def test_changed_request_is_rejected_as_an_invariant(immediate_bundle) -> None:
    from skat_ai.errors import SkatAIInvariantError

    _workspace, snapshot, result, _report, _source, store = immediate_bundle
    request_document = result.request.to_dict()["document"]
    request_document["random_seed"] = 99
    source = build_learning_corpus_strategy_teacher_report_source_v1(
        match_snapshot_id=snapshot.match_snapshot_id,
        report=_changed_report(result, request_document=request_document),
    )
    with pytest.raises(SkatAIInvariantError, match="rebuilt Request differs"):
        build_learning_corpus_strategy_teacher_evidence_collection_v1(
            store,
            (source,),
        )


@pytest.mark.parametrize("change", ("input_reference", "actual_card"))
def test_source_contract_rejects_changed_result_identity(
    immediate_bundle,
    change: str,
) -> None:
    _workspace, snapshot, result, _report, _source, _store_value = immediate_bundle
    result_document = result.result.to_dict()["document"]
    if change == "input_reference":
        result_document["input_file"] = "changed-reference"
        message = "source identity"
    else:
        result_document["post_game_review_summary"]["actual_card_played"] = (
            result_document["legal_cards"][-1]
        )
        message = "retrospective actual Card"
    with pytest.raises(ValueError, match=message):
        build_learning_corpus_strategy_teacher_report_source_v1(
            match_snapshot_id=snapshot.match_snapshot_id,
            report=_changed_report(result, result_document=result_document),
        )


def test_builder_rejects_malformed_result_through_output_validation(
    immediate_bundle,
) -> None:
    from skat_ai.errors import SkatAISchemaError

    _workspace, snapshot, result, _report, _source, store = immediate_bundle
    result_document = result.result.to_dict()["document"]
    del result_document["legal_cards"]
    source = build_learning_corpus_strategy_teacher_report_source_v1(
        match_snapshot_id=snapshot.match_snapshot_id,
        report=_changed_report(result, result_document=result_document),
    )
    with pytest.raises(SkatAISchemaError) as caught:
        build_learning_corpus_strategy_teacher_evidence_collection_v1(
            store,
            (source,),
        )
    assert caught.value.path == ""


def test_builder_rejects_unexpected_nested_private_evidence(
    immediate_bundle,
) -> None:
    from skat_ai.errors import SkatAIInvariantError

    _workspace, snapshot, result, _report, _source, store = immediate_bundle
    result_document = result.result.to_dict()["document"]
    result_document["analysis_report"][0]["compatible_worlds"] = [
        {"left_hand": ["C7"], "right_hand": ["S7"]}
    ]
    source = build_learning_corpus_strategy_teacher_report_source_v1(
        match_snapshot_id=snapshot.match_snapshot_id,
        report=_changed_report(result, result_document=result_document),
    )
    with pytest.raises(SkatAIInvariantError, match=r"analysis_report\[0\] fields"):
        build_learning_corpus_strategy_teacher_evidence_collection_v1(
            store,
            (source,),
        )


@pytest.mark.parametrize(
    "mutate",
    (
        lambda document: document["settings"].__setitem__(
            "left_hand_size",
            {"compatible_worlds": []},
        ),
        lambda document: document["analysis_metadata"][
            "left_player_profile"
        ].__setitem__("games_played", {"private_hand": ["C7"]}),
        lambda document: document["analysis_metadata"][
            "strategic_metadata"
        ].__setitem__("analysis_mode", {"original_skat": ["C7", "S7"]}),
    ),
)
def test_builder_rejects_private_values_under_allowed_fields(
    immediate_bundle,
    mutate,
) -> None:
    from skat_ai.errors import SkatAIInvariantError

    _workspace, snapshot, result, _report, _source, store = immediate_bundle
    result_document = result.result.to_dict()["document"]
    mutate(result_document)
    source = build_learning_corpus_strategy_teacher_report_source_v1(
        match_snapshot_id=snapshot.match_snapshot_id,
        report=_changed_report(result, result_document=result_document),
    )
    with pytest.raises(SkatAIInvariantError):
        build_learning_corpus_strategy_teacher_evidence_collection_v1(
            store,
            (source,),
        )


def test_source_strictly_rebuilds_nested_versioned_contracts() -> None:
    _workspace, snapshot, result, report, _source, _store_value = _source_bundle(
        match_id="match-strict-nested"
    )
    object.__setattr__(result.options, "match_decision_analysis_options_version", 2)
    with pytest.raises(ValueError, match="must equal 1"):
        build_learning_corpus_strategy_teacher_report_source_v1(
            match_snapshot_id=snapshot.match_snapshot_id,
            report=report,
        )


def test_changed_candidate_metric_changes_semantic_identity(immediate_bundle) -> None:
    _workspace, snapshot, result, _report, source, store = immediate_bundle
    changed_document = result.result.to_dict()["document"]
    changed_document["analysis_report"][0]["average_trick_points"] += 0.5
    changed_source = build_learning_corpus_strategy_teacher_report_source_v1(
        match_snapshot_id=snapshot.match_snapshot_id,
        report=_changed_report(result, result_document=changed_document),
    )
    collection = build_learning_corpus_strategy_teacher_evidence_collection_v1(
        store,
        (source, changed_source),
    )
    first, second = collection.evidences
    assert first.teacher_semantic_fingerprint != second.teacher_semantic_fingerprint
    assert first.strategy_teacher_evidence_id != second.strategy_teacher_evidence_id


def test_collection_orders_multiple_matches_and_decisions_canonically() -> None:
    first_workspace, first_snapshot, *_first_rest = _source_bundle(
        match_id="match-b-order"
    )
    second_workspace, second_snapshot, *_second_rest = _source_bundle(
        match_id="match-a-order"
    )
    options = MatchDecisionAnalysisOptionsV1(immediate_sample_count=1)
    first_sources = []
    for decision_index in (2, 1):
        result = execute_match_decision_analysis_v1(
            first_workspace,
            match_position=3,
            decision_index=decision_index,
            options=options,
        )
        first_sources.append(
            build_learning_corpus_strategy_teacher_report_source_v1(
                match_snapshot_id=first_snapshot.match_snapshot_id,
                report=build_match_analysis_report_v1(result),
            )
        )
    second_result = execute_match_decision_analysis_v1(
        second_workspace,
        match_position=3,
        decision_index=1,
        options=options,
    )
    second_source = build_learning_corpus_strategy_teacher_report_source_v1(
        match_snapshot_id=second_snapshot.match_snapshot_id,
        report=build_match_analysis_report_v1(second_result),
    )
    store = _store(
        first_snapshot,
        second_snapshot,
        current=(first_snapshot, second_snapshot),
    )
    collection = build_learning_corpus_strategy_teacher_evidence_collection_v1(
        store,
        (first_sources[0], second_source, first_sources[1]),
    )
    assert tuple(
        (evidence.match_id, evidence.decision_index)
        for evidence in collection.evidences
    ) == (
        ("match-a-order", 1),
        ("match-b-order", 1),
        ("match-b-order", 2),
    )
    assert collection.current_match_count == 2
    assert collection.source_report_count == collection.evidence_count == 3
    assert collection.distinct_decision_count == 3
    assert collection.immediate_requested_count == 3
    assert collection.search_not_attempted_count == 3


def test_duplicate_source_binding_is_rejected(immediate_bundle) -> None:
    _workspace, _snapshot_value, _result, _report, source, store = immediate_bundle
    with pytest.raises(ValueError, match="source-binding IDs must be unique"):
        build_learning_corpus_strategy_teacher_evidence_collection_v1(
            store,
            (source, source),
        )


@pytest.fixture(scope="module")
def profile_bundle():
    definition = _capture_with_snapshots(
        snapshots=(
            _actionable_snapshot("player-a", "snapshot-a"),
            _actionable_snapshot("player-b", "snapshot-b"),
            _actionable_snapshot("player-c", "snapshot-c"),
        )
    )
    workspace = _complete_workspace(definition=definition)
    snapshot = _snapshot(workspace)
    store = _store(snapshot, current=(snapshot,))
    results = tuple(
        execute_match_decision_analysis_v1(
            workspace,
            match_position=3,
            decision_index=1,
            options=MatchDecisionAnalysisOptionsV1(
                immediate_sample_count=1,
                use_profile_presets=enabled,
            ),
        )
        for enabled in (True, False)
    )
    sources = tuple(
        build_learning_corpus_strategy_teacher_report_source_v1(
            match_snapshot_id=snapshot.match_snapshot_id,
            report=build_match_analysis_report_v1(result),
        )
        for result in results
    )
    return snapshot, results, sources, store


def test_profile_and_policy_context_is_preserved_without_rederivation(
    profile_bundle,
) -> None:
    _snapshot_value, results, sources, store = profile_bundle
    collection = build_learning_corpus_strategy_teacher_evidence_collection_v1(
        store,
        sources,
    )
    by_enabled = {
        evidence.options.use_profile_presets: evidence
        for evidence in collection.evidences
    }
    enabled = by_enabled[True]
    disabled = by_enabled[False]
    enabled_document = results[0].result.to_dict()["document"]
    disabled_document = results[1].result.to_dict()["document"]
    assert enabled.profile_binding is results[0].profile_binding
    assert enabled.to_dict()["opponent_profile_application_summary"] == (
        enabled_document["opponent_profile_application_summary"]
    )
    assert disabled.opponent_profile_application_summary is None
    assert disabled.to_dict()["left_opponent_policy_settings"] == (
        disabled_document["left_opponent_policy_settings"]
    )
    assert disabled.to_dict()["right_opponent_policy_settings"] == (
        disabled_document["right_opponent_policy_settings"]
    )
    assert collection.profile_presets_enabled_count == 1
    assert collection.profile_application_summary_count == 1


def test_changed_profile_summary_is_rejected(profile_bundle) -> None:
    from skat_ai.errors import SkatAIInvariantError

    snapshot, results, _sources, store = profile_bundle
    result = results[0]
    result_document = result.result.to_dict()["document"]
    result_document["opponent_profile_application_summary"]["left"][
        "bound_player_id"
    ] = "player-c"
    source = build_learning_corpus_strategy_teacher_report_source_v1(
        match_snapshot_id=snapshot.match_snapshot_id,
        report=_changed_report(result, result_document=result_document),
    )
    with pytest.raises(SkatAIInvariantError, match="stable opponent identity"):
        build_learning_corpus_strategy_teacher_evidence_collection_v1(
            store,
            (source,),
        )


def test_collection_rebuilds_and_validates_once_without_execution(
    immediate_bundle,
    monkeypatch,
) -> None:
    import skat_ai.application.execution as application_execution
    import skat_ai.learning_corpus_strategy_teacher_builder as builder_module
    import skat_ai.match_decision_analysis as match_decision_analysis

    _workspace, _snapshot_value, _result, _report, source, store = immediate_bundle
    calls = {"request": 0, "result": 0}
    real_request = builder_module.build_match_decision_position_request_v1
    real_validation = builder_module.validate_output_document

    def counted_request(*args, **kwargs):
        calls["request"] += 1
        return real_request(*args, **kwargs)

    def counted_validation(*args, **kwargs):
        calls["result"] += 1
        return real_validation(*args, **kwargs)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("Strategy Teacher collection must not execute analysis.")

    monkeypatch.setattr(
        builder_module,
        "build_match_decision_position_request_v1",
        counted_request,
    )
    monkeypatch.setattr(
        builder_module,
        "validate_output_document",
        counted_validation,
    )
    monkeypatch.setattr(
        application_execution,
        "_execute_match_decision_application_invocation",
        forbidden,
    )
    monkeypatch.setattr(
        match_decision_analysis,
        "execute_application_invocation",
        forbidden,
    )
    collection = build_learning_corpus_strategy_teacher_evidence_collection_v1(
        store,
        (source,),
    )
    assert collection.evidence_count == 1
    assert calls == {"request": 1, "result": 1}
