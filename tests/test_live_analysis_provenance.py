import json
from dataclasses import replace
from pathlib import Path

import pytest

import skat_ai.api.v1 as api_v1
import skat_ai.application.position_workflow as position_workflow_module
import skat_ai.live_analysis_provenance as live_provenance_module
from skat_ai.api.v1 import WorkflowV1
from skat_ai.application import (
    ApplicationExecutionOptions,
    ApplicationExternalDocuments,
    PositionAnalysisApplicationOptions,
    build_application_invocation,
    execute_application_invocation,
)
from skat_ai.application.execution import ApplicationWorkflowDependencies
from skat_ai.application.position_workflow import (
    PositionWorkflowDependencies,
)
from skat_ai.application.provenance import ApplicationProvenanceAttachment
from skat_ai.deck import get_full_deck
from skat_ai.errors import SkatAIInformationPolicyError
from skat_ai.field_provenance import (
    FieldProvenanceEntry,
    FieldProvenanceLedger,
    build_serializable_field_provenance_ledger,
)
from skat_ai.field_provenance_coverage import validate_field_provenance_coverage
from skat_ai.field_provenance_policy import (
    InformationUseContext,
    redact_field_provenance_ledger_for_public_output,
)
from skat_ai.game_declaration import GameDeclaration
from skat_ai.game_state import GameState
from skat_ai.live_analysis_provenance import (
    build_live_decision_provenance_attachment,
    build_live_position_result_provenance_attachment,
)
from skat_ai.public_hand_constraint import PublicHandConstraint
from skat_ai.recommender import recommend_card_by_expected_value
from skat_ai.simulation_provenance import build_safe_selection_settings
from skat_ai.strategic_metadata import StrategicMetadata

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = PROJECT_ROOT / "examples"


def _load(name: str) -> dict[str, object]:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def _execute(
    document: dict[str, object],
    *,
    options: PositionAnalysisApplicationOptions | None = None,
    external_documents: ApplicationExternalDocuments | None = None,
):
    return execute_application_invocation(
        build_application_invocation(
            document,
            input_reference="memory://live-position",
            options=ApplicationExecutionOptions(
                position_analysis=(
                    options
                    or PositionAnalysisApplicationOptions(
                        sample_count_override=1,
                        random_seed_override=42,
                    )
                )
            ),
            external_documents=external_documents,
        )
    )


def _flat(execution):
    assert execution.provenance is not None
    return execution.provenance.attachments[0]


def test_live_application_attaches_complete_decision_and_result_ledgers() -> None:
    execution = _execute(_load("grand_second_position.json"))
    assert execution.provenance is not None
    flat, result = execution.provenance.attachments

    assert flat.name == "flat_decision"
    assert flat.document_role == "consumed_input"
    assert flat.ledger.status == "complete"
    assert flat.coverage_summary.provenance_complete is True
    assert result.name == "position_result"
    assert result.document_role == "result"
    assert result.ledger.status == "complete"
    assert result.ledger.exemptions == ()
    assert result.ledger.limitations == ()
    assert result.coverage_summary.provenance_complete is True
    assert result.coverage_summary.all_paths_accounted_for is True
    assert result.coverage_summary.uncovered_paths == ()
    assert result.document_to_dict() == execution.result.to_dict()["document"]

    recommendation = next(
        item
        for item in result.ledger.entries
        if item.field_path == "/recommendation/card"
    )
    hand = result.document["position"]["hand"]
    assert {
        path
        for path in recommendation.dependency_paths
        if path.startswith("/position/hand/")
    } == {f"/position/hand/{index}" for index in range(len(hand))}
    assert {
        path
        for path in recommendation.dependency_paths
        if path.startswith("/legal_cards/")
    } == {
        f"/legal_cards/{index}"
        for index in range(len(result.document["legal_cards"]))
    }

    exempted = {item.field_path for item in result.ledger.exemptions}
    for critical in (
        "/position",
        "/settings",
        "/analysis_metadata",
        "/information_policy_summary",
        "/game_declaration",
        "/legal_cards",
        "/analysis_report",
        "/strategic_summary",
        "/recommendation",
    ):
        assert critical not in exempted


def test_decision_document_contains_only_allowlisted_information_and_no_seed() -> None:
    attachment = _flat(_execute(_load("grand_second_position.json")))
    document = attachment.document_to_dict()
    serialized = json.dumps(document, sort_keys=True)

    assert set(document) == {
        "game_state",
        "opponent_hand_sizes",
        "public_hand_constraints",
        "strategic_metadata",
        "game_declaration",
        "selection",
    }
    assert document["selection"]["method"] == "immediate_expected_value"
    assert "random_seed" not in serialized
    for forbidden in (
        "left_hand",
        "right_hand",
        "hypothetical_skat",
        "coherent",
        "ownership_transitions",
        "actual_card_played",
        "final_settlement",
        "principal_variation",
    ):
        assert forbidden not in serialized

    hand_entry = next(
        item for item in attachment.ledger.entries if item.field_path == "/game_state/hand"
    )
    assert (hand_entry.origin, hand_entry.visibility) == (
        "validated_copy",
        "local_private",
    )
    assert hand_entry.perspective_player_id == "me"
    assert attachment.information_use_context.stage == "decision_time"


def test_local_defender_decision_redacts_declarer_known_skat_deterministically() -> None:
    document = _load("declarer_card_exposure_continuation.json")
    document["skat_visibility"] = "known_to_declarer"
    first = {**document, "skat": ["CQ", "SQ"]}
    second = {**document, "skat": ["HQ", "DQ"]}

    first_attachment = _flat(_execute(first))
    second_attachment = _flat(_execute(second))

    assert first_attachment.document["game_state"]["skat"] == ()
    assert first_attachment.document == second_attachment.document
    assert first_attachment.ledger == second_attachment.ledger
    assert first_attachment.coverage_summary == second_attachment.coverage_summary
    assert any(
        item.field_path == "/game_state/skat" and item.reason == "not_applicable"
        for item in first_attachment.ledger.exemptions
    )


def test_decision_builder_rejects_unauthorized_skat_and_public_hand_sources() -> None:
    state = GameState(
        game_type="grand",
        player_role="defender",
        declarer_player="left",
        hand=["CA"],
        current_trick=["C7", "C8"],
        skat=["SQ", "HQ"],
        trick_leader="left",
        next_player="me",
    )
    common = {
        "name": "flat_decision",
        "state": state,
        "left_hand_size": 0,
        "right_hand_size": 0,
        "strategic_metadata": StrategicMetadata(skat_visibility="known_to_declarer"),
        "game_declaration": GameDeclaration("grand", matadors=1, bid_value=24),
        "decision_index": 0,
        "selection_method": "immediate_expected_value",
        "selection_settings": build_safe_selection_settings(
            sample_count=1,
            use_basic_opponent_strategy=True,
            opponent_response_policy_by_player={},
            requested_search_budget=None,
        ),
        "simulation_scope": False,
    }
    with pytest.raises(SkatAIInformationPolicyError) as skat_error:
        build_live_decision_provenance_attachment(
            public_hand_constraints=(),
            **common,
        )
    assert skat_error.value.path == "/game_state/skat"
    assert "SQ" not in str(skat_error.value)

    state.skat = []
    with pytest.raises(SkatAIInformationPolicyError) as constraint_error:
        build_live_decision_provenance_attachment(
            public_hand_constraints=(
                PublicHandConstraint(
                    player="right",
                    cards=(),
                    source="accepted_defender_open_play_proof",
                ),
            ),
            **common,
        )
    assert constraint_error.value.path == "/public_hand_constraints"
    assert "accepted_defender_open_play_proof" not in str(constraint_error.value)


@pytest.mark.parametrize(
    ("example_name", "player", "source"),
    [
        (
            "declarer_card_exposure_continuation.json",
            "left",
            "declarer_card_exposure_continuation",
        ),
        (
            "defender_open_play_continuation.json",
            "left",
            "defender_open_play_continuation",
        ),
    ],
)
def test_only_authorized_continuation_public_hands_enter_decision_documents(
    example_name: str,
    player: str,
    source: str,
) -> None:
    constraints = _flat(_execute(_load(example_name))).document[
        "public_hand_constraints"
    ]
    assert len(constraints) == 1
    assert constraints[0]["player"] == player
    assert constraints[0]["source"] == source


def test_hidden_card_inference_is_structural_and_result_safe() -> None:
    execution = _execute(_load("grand_hidden_card_inference.json"))
    assert execution.provenance is not None
    result_attachment = execution.provenance.attachments[-1]
    hidden_entries = [
        item
        for item in result_attachment.ledger.entries
        if item.field_path.startswith("/hidden_card_inference_summary")
    ]
    assert hidden_entries
    assert {item.origin for item in hidden_entries} == {"structural_inference"}
    assert (
        execution.result.document["hidden_card_inference_summary"]["provenance_status"]
        == "available"
    )

    known_skat_execution = _execute(_load("grand_declarer_known_to_declarer_live.json"))
    assert known_skat_execution.provenance is not None
    known_skat_ledger = known_skat_execution.provenance.attachments[-1].ledger
    known_skat_recommendation = next(
        item
        for item in known_skat_ledger.entries
        if item.field_path == "/recommendation/card"
    )
    assert {
        "/position/skat/0",
        "/position/skat/1",
        "/position/trick_leader",
    } <= set(known_skat_recommendation.dependency_paths)


def test_declared_ouvert_adds_only_the_authorized_public_declarer_hand() -> None:
    deck = get_full_deck()
    document = {
        "game_type": "grand",
        "player_role": "defender",
        "declarer_player": "left",
        "player_position": "forehand",
        "trick_leader": "me",
        "hand": deck[:10],
        "current_trick": [],
        "played_cards": [],
        "completed_tricks": [],
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": "me",
        "skat": [],
        "left_hand_size": 10,
        "right_hand_size": 10,
        "sample_count": 1,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
        "analysis_mode": "live_decision",
        "skat_visibility": "unknown",
        "game_end_reason": "not_ended",
        "hand_game": True,
        "ouvert": True,
        "schneider_announced": True,
        "schwarz_announced": True,
        "matadors": 1,
        "bid_value": 18,
        "public_declarer_cards": deck[10:20],
    }
    attachment = _flat(_execute(document))

    assert attachment.document["public_hand_constraints"] == (
        {
            "player": "left",
            "source": "declared_ouvert",
            "visibility_scope": "all_players",
            "card_count": 10,
            "cards": tuple(deck[10:20]),
        },
    )


def test_auto_fallback_is_immediate_derived_with_search_evidence_dependency() -> None:
    execution = _execute(_load("grand_auto_search_fallback.json"))
    assert execution.provenance is not None
    ledger = execution.provenance.attachments[-1].ledger
    recommendation = next(
        item for item in ledger.entries if item.field_path == "/recommendation/card"
    )

    assert recommendation.origin == "heuristic_analysis"
    assert "/bounded_search_result/status" in recommendation.dependency_paths
    assert execution.result.document["recommendation_method_summary"]["fallback_used"] is True


def test_strict_unavailable_search_remains_search_derived() -> None:
    document = _load("defender_open_play_continuation.json")
    document.update(
        recommendation_method="bounded_search",
        bounded_search_settings={
            "random_seed": 113,
            "max_remaining_tricks": 1,
            "max_depth_plies": 3,
            "max_nodes": 100,
            "max_selected_worlds": 2,
            "max_sampled_worlds": 2,
            "minimum_comparable_worlds": 1,
            "wall_clock_timeout_ms": None,
        },
    )
    execution = _execute(document)
    assert execution.provenance is not None
    recommendation = next(
        item
        for item in execution.provenance.attachments[-1].ledger.entries
        if item.field_path == "/recommendation/card"
    )

    assert execution.result.document["bounded_search_result"]["status"] == "unavailable"
    assert recommendation.origin == "search_derived"
    assert all(
        reference.reference_id != "immediate_expected_value"
        for reference in recommendation.source_references
    )

    orphan = replace(
        next(
            item
            for item in execution.provenance.attachments[-1].ledger.entries
            if item.field_path == "/bounded_search_result/status"
        ),
        field_path="/bounded_search_result/missing",
    )
    with pytest.raises(ValueError, match="absent from the Position Result"):
        build_live_position_result_provenance_attachment(
            execution.result.document,
            search_entries_by_path={orphan.field_path: orphan},
        )


def test_auto_without_search_or_immediate_recommendation_retains_both_evidence() -> None:
    document = _load("defender_open_play_continuation.json")
    document.update(
        hand=["D8", "D7"],
        current_trick=["DQ"],
        next_player="left",
        trick_leader="me",
        recommendation_method="auto",
        bounded_search_settings={
            "random_seed": 113,
            "max_remaining_tricks": 1,
            "max_depth_plies": 3,
            "max_nodes": 100,
            "max_selected_worlds": 2,
            "max_sampled_worlds": 2,
            "minimum_comparable_worlds": 1,
            "wall_clock_timeout_ms": None,
        },
    )
    execution = _execute(document)
    assert execution.provenance is not None
    recommendation = next(
        item
        for item in execution.provenance.attachments[-1].ledger.entries
        if item.field_path == "/recommendation/reason"
    )

    assert execution.result.document["recommendation_method_summary"][
        "effective_method"
    ] == "none"
    assert recommendation.origin == "heuristic_analysis"
    assert "/bounded_search_result/status" in recommendation.dependency_paths
    assert {item.reference_id for item in recommendation.source_references} == {
        "immediate_expected_value"
    }


def test_strict_search_recommendation_is_search_derived_without_fallback() -> None:
    execution = _execute(_load("grand_bounded_search_exhaustive.json"))
    assert execution.provenance is not None
    ledger = execution.provenance.attachments[-1].ledger
    recommendation = next(
        item for item in ledger.entries if item.field_path == "/recommendation/card"
    )

    assert recommendation.origin == "search_derived"
    assert execution.result.document["recommendation_method_summary"]["fallback_used"] is False
    assert execution.result.document["analysis_report"] == ()
    reason = next(
        item
        for item in ledger.entries
        if item.field_path == "/recommendation/reason"
    )
    assert {
        "/bounded_search_result/status",
        "/bounded_search_result/stop_reason",
        "/bounded_search_result/world_coverage",
        "/bounded_search_result/consumed_budget/selected_world_count",
        "/bounded_search_result/consumed_budget/completed_world_count",
        "/bounded_search_result/recommended_card",
    } <= set(reason.dependency_paths)
    assert any(
        path.endswith("/local_contract_success_rate")
        for path in reason.dependency_paths
    )


def test_explicit_immediate_routing_is_rule_derived_without_search_claims() -> None:
    document = _load("grand_second_position.json")
    document["recommendation_method"] = "immediate_expected_value"
    execution = _execute(document)
    assert execution.provenance is not None
    ledger = execution.provenance.attachments[-1].ledger
    routing_entries = [
        item
        for item in ledger.entries
        if item.field_path.startswith("/recommendation_method_summary/")
        or item.field_path == "/bounded_search_result"
    ]

    assert routing_entries
    assert {item.origin for item in routing_entries} == {"rule_derived"}
    assert all(
        reference.reference_id != "compatible_world_minimax_v1"
        for item in routing_entries
        for reference in item.source_references
    )


def test_auto_search_selection_is_search_derived_without_immediate_analysis() -> None:
    document = _load("grand_bounded_search_exhaustive.json")
    document["recommendation_method"] = "auto"
    execution = _execute(document)
    assert execution.provenance is not None
    ledger = execution.provenance.attachments[-1].ledger
    recommendation = next(
        item for item in ledger.entries if item.field_path == "/recommendation/card"
    )

    assert recommendation.origin == "search_derived"
    assert execution.result.document["recommendation_method_summary"] == {
        "requested_method": "auto",
        "effective_method": "compatible_world_minimax_v1",
        "search_attempted": True,
        "fallback_used": False,
        "fallback_method": None,
        "analysis_report_method": "none",
    }


def test_multi_step_and_policy_comparison_names_are_canonical() -> None:
    options = PositionAnalysisApplicationOptions(
        sample_count_override=1,
        random_seed_override=42,
        multi_step_count=1,
        card_selection_policy="highest_point",
        expected_value_sample_count=1,
        compare_policies=True,
    )
    execution = _execute(_load("grand_second_position.json"), options=options)
    assert execution.provenance is not None

    assert [item.name for item in execution.provenance.attachments] == [
        "flat_decision",
        "multi_step_decision/0",
        "policy_comparison_decision/0/first_legal/0",
        "policy_comparison_decision/1/lowest_point/0",
        "policy_comparison_decision/2/highest_point/0",
        "policy_comparison_decision/3/highest_expected_value/0",
        "position_result",
    ]
    assert all(
        item.coverage_summary.provenance_complete
        for item in execution.provenance.attachments[:-1]
    )
    private_result_entries = [
        item
        for item in execution.provenance.attachments[-1].ledger.entries
        if any(
            marker in item.field_path
            for marker in (
                "/prepared_state/hand",
                "/prepared_state/skat",
                "/final_state/hand",
                "/final_state/skat",
            )
        )
    ]
    assert private_result_entries
    assert {item.visibility for item in private_result_entries} == {"local_private"}


def test_external_profile_reference_is_engine_private_and_publicly_redactable(
    monkeypatch,
) -> None:
    reference = "private-profile-reference-sentinel"
    construction_counts = {"input": 0, "summary": 0}
    real_input_builder = position_workflow_module.build_opponent_statistics_from_document
    real_summary_builder = position_workflow_module.build_opponent_statistics_summary

    def counted_input_builder(document):
        construction_counts["input"] += 1
        return real_input_builder(document)

    def counted_summary_builder(statistics_input):
        construction_counts["summary"] += 1
        return real_summary_builder(statistics_input)

    monkeypatch.setattr(
        position_workflow_module,
        "build_opponent_statistics_from_document",
        counted_input_builder,
    )
    monkeypatch.setattr(
        position_workflow_module,
        "build_opponent_statistics_summary",
        counted_summary_builder,
    )
    execution = _execute(
        _load("grand_second_position.json"),
        options=PositionAnalysisApplicationOptions(
            sample_count_override=1,
            random_seed_override=42,
            use_profile_presets_override=True,
            left_opponent_player_id="opponent-123",
        ),
        external_documents=ApplicationExternalDocuments(
            opponent_statistics_document=_load("opponent_statistics.json"),
            opponent_statistics_reference=reference,
        ),
    )
    assert execution.provenance is not None
    ledger = execution.provenance.attachments[-1].ledger
    assert reference in repr(ledger)
    policy_entry = next(
        item
        for item in ledger.entries
        if item.field_path == "/left_opponent_policy_settings/opponent_lead_policy"
    )
    assert any(
        dependency.startswith("/opponent_profile_application_summary/")
        for dependency in policy_entry.dependency_paths
    )

    redacted = redact_field_provenance_ledger_for_public_output(ledger)
    serialized = json.dumps(
        build_serializable_field_provenance_ledger(redacted),
        sort_keys=True,
    )
    assert reference not in serialized
    assert "private_dependencies_redacted" in serialized
    assert construction_counts == {"input": 1, "summary": 1}


def test_post_game_defender_open_play_proof_creates_only_safe_retrospective_bundle() -> None:
    execution = _execute(_load("defender_open_play.json"))
    assert execution.provenance is not None
    assert [attachment.name for attachment in execution.provenance.attachments] == [
        "flat_retrospective/input",
        "flat_retrospective/analysis",
        "position_result",
    ]
    serialized = json.dumps(
        [attachment.document_to_dict() for attachment in execution.provenance.attachments],
        sort_keys=True,
    )
    assert "accepted_defender_open_play_proof" not in serialized
    assert "private_evidence_redacted" in serialized
    assert "proof_internals" not in serialized


def test_context_use_is_enforced_before_analysis_and_simulation(monkeypatch) -> None:
    document = {"blocked": True}
    ledger = FieldProvenanceLedger(
        status="complete",
        entries=(
            FieldProvenanceEntry(
                field_path="/blocked",
                coverage_kind="field",
                origin="validated_copy",
                visibility="local_private",
                available_from="current_decision",
                available_from_decision_index=0,
                available_from_event_index=None,
                derivation="validated",
                source_references=(),
                dependency_paths=(),
                subject_player_id=None,
                perspective_player_id="other-player",
            ),
        ),
        exemptions=(),
        limitations=(),
    )
    coverage = validate_field_provenance_coverage(document, ledger)
    denied = ApplicationProvenanceAttachment(
        name="flat_decision",
        document_role="consumed_input",
        document=document,
        ledger=ledger,
        coverage_summary=coverage,
        information_use_context=InformationUseContext(
            workflow="position_analysis",
            stage="decision_time",
            perspective_player_id="me",
            perspective_side="declarer",
            decision_index=0,
            event_index=None,
        ),
    )
    monkeypatch.setattr(
        live_provenance_module,
        "build_live_decision_provenance_attachment",
        lambda **_kwargs: denied,
    )
    call_counts = {"immediate": 0, "multi_step": 0, "comparison": 0}

    def unexpected_recommender(**_kwargs):
        call_counts["immediate"] += 1
        raise AssertionError("Immediate analysis executed before context validation.")

    def unexpected_multi_step(**_kwargs):
        call_counts["multi_step"] += 1
        raise AssertionError("Multi-Step executed before context validation.")

    def unexpected_comparison(**_kwargs):
        call_counts["comparison"] += 1
        raise AssertionError("Policy Comparison executed before context validation.")

    invocation = build_application_invocation(
        _load("grand_second_position.json"),
        input_reference="denied-context",
        options=ApplicationExecutionOptions(
            position_analysis=PositionAnalysisApplicationOptions(
                sample_count_override=1,
                random_seed_override=42,
                multi_step_count=1,
                compare_policies=True,
            )
        ),
    )
    with pytest.raises(SkatAIInformationPolicyError, match="not available"):
        execute_application_invocation(
            invocation,
            dependencies=ApplicationWorkflowDependencies(
                position=PositionWorkflowDependencies(
                    immediate_recommender=unexpected_recommender,
                    multi_step_simulator=unexpected_multi_step,
                    policy_comparator=unexpected_comparison,
                )
            ),
        )
    assert call_counts == {"immediate": 0, "multi_step": 0, "comparison": 0}


def test_normal_flat_provenance_preserves_immediate_and_inference_call_counts(
    monkeypatch,
) -> None:
    counts = {"immediate": 0, "inference": 0}
    real_inference_builder = position_workflow_module.build_hidden_card_inference_model

    def counted_recommender(**kwargs):
        counts["immediate"] += 1
        return recommend_card_by_expected_value(**kwargs)

    def counted_inference_builder(*args, **kwargs):
        counts["inference"] += 1
        return real_inference_builder(*args, **kwargs)

    monkeypatch.setattr(
        position_workflow_module,
        "build_hidden_card_inference_model",
        counted_inference_builder,
    )
    invocation = build_application_invocation(
        _load("grand_second_position.json"),
        input_reference="counted-live-analysis",
        options=ApplicationExecutionOptions(
            position_analysis=PositionAnalysisApplicationOptions(
                sample_count_override=1,
                random_seed_override=42,
            )
        ),
    )
    execution = execute_application_invocation(
        invocation,
        dependencies=ApplicationWorkflowDependencies(
            position=PositionWorkflowDependencies(
                immediate_recommender=counted_recommender
            )
        ),
    )

    assert execution.provenance is not None
    assert counts == {"immediate": 1, "inference": 1}


def test_public_api_intentionally_omits_internal_application_provenance() -> None:
    document = _load("grand_second_position.json")
    public_result = api_v1.execute_document(
        document,
        options=api_v1.ExecutionOptionsV1(
            workflow_options={
                "sample_count_override": 1,
                "random_seed_override": 42,
            }
        ),
    )
    serialized = api_v1.serialize_result(public_result)

    assert not hasattr(public_result, "provenance")
    assert "provenance" not in serialized
    assert "provenance" not in serialized["document"]
    assert public_result.result.workflow is WorkflowV1.POSITION_ANALYSIS
