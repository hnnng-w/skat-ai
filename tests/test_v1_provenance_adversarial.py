import json
from dataclasses import replace
from pathlib import Path

import pytest

import skat_ai.application.execution as application_execution_module
import skat_ai.application.position_workflow as position_workflow_module
import skat_ai.information_view as information_view_module
from skat_ai.api.v1 import WorkflowV1
from skat_ai.application import (
    ApplicationExecutionOptions,
    ApplicationExternalDocuments,
    HistoricalGameApplicationOptions,
    PositionAnalysisApplicationOptions,
    build_application_invocation,
    execute_application_invocation,
)
from skat_ai.errors import (
    SkatAIInformationPolicyError,
    SkatAIInvariantError,
    SkatAIValidationError,
)
from skat_ai.field_provenance import (
    FieldProvenanceEntry,
    FieldProvenanceExemption,
    FieldProvenanceLedger,
    FieldProvenanceSourceReference,
)
from skat_ai.field_provenance_coverage import (
    build_field_provenance_coverage_summary,
    validate_field_provenance_coverage,
)
from skat_ai.field_provenance_policy import (
    InformationUseContext,
    validate_field_provenance_entry_use,
)
from skat_ai.v1_information_provenance_enforcement import (
    validate_v1_information_provenance_enforcement_version,
    validate_v1_retained_stage_linkage,
)
from skat_ai.v1_information_provenance_sources import (
    build_v1_information_provenance_sources,
    canonical_v1_external_reference,
    exact_v1_json_equal,
    validate_v1_information_provenance_sources,
)

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str) -> dict[str, object]:
    return json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))


def _replace_attachment_entry(attachment, original, replacement):
    ledger = FieldProvenanceLedger(
        status="complete",
        entries=tuple(
            replacement if entry is original else entry
            for entry in attachment.ledger.entries
        ),
        exemptions=attachment.ledger.exemptions,
        limitations=attachment.ledger.limitations,
    )
    return replace(
        attachment,
        ledger=ledger,
        coverage_summary=build_field_provenance_coverage_summary(
            attachment.document,
            ledger,
        ),
    )


def _trusted_checkpoints(execution):
    enforcement = execution.information_provenance_enforcement
    return enforcement.trusted_checkpoint_documents


def _entry(**overrides) -> FieldProvenanceEntry:
    values = {
        "field_path": "/private",
        "coverage_kind": "field",
        "origin": "validated_copy",
        "visibility": "post_game_only",
        "available_from": "offline_review",
        "available_from_decision_index": None,
        "available_from_event_index": None,
        "derivation": "validated",
        "source_references": (),
        "dependency_paths": (),
        "subject_player_id": None,
        "perspective_player_id": None,
    }
    values.update(overrides)
    return FieldProvenanceEntry(**values)


@pytest.mark.parametrize("version", (True, False, 0, 2, "1", None))
def test_enforcement_version_rejects_boolean_and_non_one_values(version: object) -> None:
    with pytest.raises(SkatAIValidationError):
        validate_v1_information_provenance_enforcement_version(version)


@pytest.mark.parametrize(
    "entry",
    (
        _entry(),
        _entry(
            visibility="public",
            available_from="after_actual_play",
            available_from_decision_index=2,
            origin="retrospective_attachment",
            derivation="retrospective",
        ),
        _entry(
            visibility="engine_private",
            available_from="request_start",
            origin="validated_copy",
            derivation="validated",
        ),
    ),
)
def test_private_temporal_and_engine_values_are_denied_before_authorized_stage(
    entry: FieldProvenanceEntry,
) -> None:
    with pytest.raises(SkatAIInformationPolicyError, match="not available") as caught:
        validate_field_provenance_entry_use(
            entry,
            InformationUseContext(
                workflow="historical_game",
                stage="decision_time",
                perspective_player_id="player-a",
                perspective_side="declarer",
                decision_index=1,
                event_index=0,
            ),
        )
    assert "private" not in caught.value.message.lower()


def test_complete_coverage_rejects_uncovered_orphaned_overlapping_and_legacy() -> None:
    document = {"a": 1, "b": 2}
    entry = _entry(
        field_path="/a",
        visibility="public",
        available_from="request_start",
    )
    with pytest.raises(SkatAIValidationError, match="no provenance"):
        validate_field_provenance_coverage(
            document,
            FieldProvenanceLedger(
                status="complete",
                entries=(entry,),
                exemptions=(),
                limitations=(),
            ),
        )
    with pytest.raises(SkatAIValidationError, match="legacy_untracked"):
        FieldProvenanceLedger(
            status="complete",
            entries=(entry,),
            exemptions=(
                FieldProvenanceExemption(
                    field_path="/b",
                    coverage_kind="field",
                    reason="legacy_untracked",
                ),
            ),
            limitations=(),
        )


def test_dependency_missing_self_cycle_and_temporal_inversion_are_rejected() -> None:
    current = _entry(
        field_path="/current",
        visibility="public",
        available_from="request_start",
    )
    with pytest.raises(SkatAIValidationError, match="existing entry"):
        FieldProvenanceLedger(
            status="complete",
            entries=(replace(current, dependency_paths=("/missing",)),),
            exemptions=(),
            limitations=(),
        )
    with pytest.raises(SkatAIValidationError, match="itself"):
        replace(current, dependency_paths=("/current",))
    later = _entry(
        field_path="/later",
        visibility="public",
        available_from="game_end",
    )
    with pytest.raises(SkatAIValidationError, match="precede"):
        FieldProvenanceLedger(
            status="complete",
            entries=(replace(current, dependency_paths=("/later",)), later),
            exemptions=(),
            limitations=(),
        )


def test_mutated_source_binding_is_rejected_against_exact_invocation() -> None:
    invocation = build_application_invocation(
        _load("opponent_statistics.json"),
        input_reference="fixture://statistics",
    )
    sources = build_v1_information_provenance_sources(invocation)
    original = sources.bindings[0]
    forged = replace(
        sources,
        bindings=(
            replace(original, document={"forged": True}),
            *sources.bindings[1:],
        ),
    )

    with pytest.raises(SkatAIInvariantError, match="binding"):
        validate_v1_information_provenance_sources(invocation, forged)


def test_exact_source_equality_rejects_type_and_object_order_changes() -> None:
    assert exact_v1_json_equal({"a": 1, "b": False}, {"a": 1, "b": False})
    assert not exact_v1_json_equal({"a": True}, {"a": 1})
    assert not exact_v1_json_equal({"a": 1, "b": 2}, {"b": 2, "a": 1})


def test_padded_external_reference_uses_non_leaking_canonical_identity() -> None:
    canonical = canonical_v1_external_reference(" fixture://statistics ")

    assert canonical.startswith("external-reference-sha256:")
    assert "fixture" not in canonical
    assert canonical != canonical_v1_external_reference("fixture://statistics")


def test_mutated_source_timing_ledger_is_rejected_against_exact_invocation() -> None:
    invocation = build_application_invocation(
        _load("historical_grand_declarer_card_exposure_continuation.json"),
        input_reference="fixture://historical-event",
    )
    sources = build_v1_information_provenance_sources(invocation)
    request = next(item for item in sources.attachments if item.name == "v1_source/request")
    original = next(
        entry
        for entry in request.ledger.entries
        if "/game_events/0/" in entry.field_path
    )
    forged_entry = replace(
        original,
        available_from="request_start",
        available_from_event_index=None,
    )
    forged_request = _replace_attachment_entry(request, original, forged_entry)
    forged_sources = replace(
        sources,
        attachments=tuple(
            forged_request if item is request else item
            for item in sources.attachments
        ),
    )

    with pytest.raises(SkatAIInvariantError, match="ledger"):
        validate_v1_information_provenance_sources(invocation, forged_sources)


def test_cross_workflow_retained_reference_is_rejected() -> None:
    invocation = build_application_invocation(
        _load("opponent_statistics.json"),
        input_reference="fixture://statistics",
    )
    execution = execute_application_invocation(invocation)
    assert execution.provenance is not None
    root = next(
        item
        for item in execution.provenance.attachments
        if item.name == "opponent_statistics_result"
    )
    original = root.ledger.entries[0]
    forged_entry = replace(
        original,
        source_references=(
            FieldProvenanceSourceReference(
                reference_type="historical_game",
                reference_id="final_outcome_context",
                field_path=None,
                visibility="public",
            ),
        ),
    )
    forged_root = _replace_attachment_entry(root, original, forged_entry)
    forged_bundle = replace(
        execution.provenance,
        attachments=tuple(
            forged_root if item is root else item
            for item in execution.provenance.attachments
        ),
    )

    with pytest.raises(SkatAIInvariantError, match="not authorized"):
        validate_v1_retained_stage_linkage(
            invocation,
            execution.information_provenance_enforcement.sources,
            forged_bundle,
            trusted_checkpoint_documents=_trusted_checkpoints(execution),
        )


def test_retained_exact_source_timing_cannot_be_downgraded() -> None:
    invocation = build_application_invocation(
        _load("historical_grand_normal_completion.json"),
        input_reference="fixture://historical-timing",
    )
    execution = execute_application_invocation(invocation)
    assert execution.provenance is not None
    original_attachment, original_entry = next(
        (attachment, entry)
        for attachment in execution.provenance.attachments
        for entry in attachment.ledger.entries
        if entry.available_from == "after_actual_play"
        and any(
            reference.field_path is not None
            and "/tricks/" in reference.field_path
            and reference.field_path.endswith("/card")
            for reference in entry.source_references
        )
    )
    forged_entry = replace(
        original_entry,
        available_from="request_start",
        available_from_decision_index=None,
    )
    forged_attachment = _replace_attachment_entry(
        original_attachment,
        original_entry,
        forged_entry,
    )
    forged_bundle = replace(
        execution.provenance,
        attachments=tuple(
            forged_attachment if item is original_attachment else item
            for item in execution.provenance.attachments
        ),
    )

    with pytest.raises(SkatAIInvariantError, match="predates its exact source"):
        validate_v1_retained_stage_linkage(
            invocation,
            execution.information_provenance_enforcement.sources,
            forged_bundle,
            trusted_checkpoint_documents=_trusted_checkpoints(execution),
        )


def test_retained_cross_boundary_index_cannot_predate_its_source() -> None:
    invocation = build_application_invocation(
        _load("grand_midgame_profile_preset_live.json"),
        input_reference="fixture://live-cross-boundary",
    )
    execution = execute_application_invocation(invocation)
    assert execution.provenance is not None
    decision = next(
        item for item in execution.provenance.attachments if item.name == "flat_decision"
    )
    original = next(
        entry for entry in decision.ledger.entries if entry.field_path == "/game_state/hand"
    )
    forged_entry = replace(
        original,
        available_from="after_actual_play",
        available_from_decision_index=0,
    )
    forged_decision = replace(
        _replace_attachment_entry(decision, original, forged_entry),
        information_use_context=replace(
            decision.information_use_context,
            stage="after_actual_play",
        ),
    )
    forged_bundle = replace(
        execution.provenance,
        attachments=tuple(
            forged_decision if item is decision else item
            for item in execution.provenance.attachments
        ),
    )

    with pytest.raises(SkatAIInvariantError, match="exact-source Decision"):
        validate_v1_retained_stage_linkage(
            invocation,
            execution.information_provenance_enforcement.sources,
            forged_bundle,
            trusted_checkpoint_documents=_trusted_checkpoints(execution),
        )


def test_retained_exact_source_visibility_cannot_be_widened() -> None:
    invocation = build_application_invocation(
        _load("historical_grand_normal_completion.json"),
        input_reference="fixture://historical-visibility",
    )
    execution = execute_application_invocation(invocation)
    assert execution.provenance is not None
    root = next(
        item
        for item in execution.provenance.attachments
        if item.name == "historical_game_result"
    )
    original = next(
        entry
        for entry in root.ledger.entries
        if entry.visibility == "post_game_only"
        and any(
            reference.field_path is not None
            and "/initial_hand/" in reference.field_path
            for reference in entry.source_references
        )
    )
    forged_entry = replace(original, visibility="public")
    forged_root = _replace_attachment_entry(root, original, forged_entry)
    forged_bundle = replace(
        execution.provenance,
        attachments=tuple(
            forged_root if item is root else item
            for item in execution.provenance.attachments
        ),
    )

    with pytest.raises(SkatAIInvariantError, match="widens exact-source visibility"):
        validate_v1_retained_stage_linkage(
            invocation,
            execution.information_provenance_enforcement.sources,
            forged_bundle,
        )


def test_pathless_live_hand_is_reconciled_with_the_position_source() -> None:
    invocation = build_application_invocation(
        _load("grand_second_position.json"),
        input_reference="fixture://live-hand",
    )
    execution = execute_application_invocation(invocation)
    assert execution.provenance is not None
    decision = next(
        item for item in execution.provenance.attachments if item.name == "flat_decision"
    )
    forged_document = decision.document_to_dict()
    forged_document["game_state"]["hand"][0] = "C7"
    forged_decision = replace(decision, document=forged_document)
    forged_bundle = replace(
        execution.provenance,
        attachments=tuple(
            forged_decision if item is decision else item
            for item in execution.provenance.attachments
        ),
    )

    with pytest.raises(SkatAIInvariantError, match="exact source"):
        validate_v1_retained_stage_linkage(
            invocation,
            execution.information_provenance_enforcement.sources,
            forged_bundle,
        )


def test_pathless_direct_copy_is_reconciled_with_its_bound_source() -> None:
    invocation = build_application_invocation(
        _load("training_dataset_variable_length.json"),
        input_reference="fixture://dataset-pathless",
    )
    execution = execute_application_invocation(invocation)
    assert execution.provenance is not None
    input_attachment = next(
        item
        for item in execution.provenance.attachments
        if item.name == "training_dataset/input"
    )
    forged_document = input_attachment.document_to_dict()
    forged_document["dataset_id"] = "forged-dataset"
    forged_attachment = replace(input_attachment, document=forged_document)
    forged_bundle = replace(
        execution.provenance,
        attachments=tuple(
            forged_attachment if item is input_attachment else item
            for item in execution.provenance.attachments
        ),
    )

    with pytest.raises(SkatAIInvariantError, match="exact source"):
        validate_v1_retained_stage_linkage(
            invocation,
            execution.information_provenance_enforcement.sources,
            forged_bundle,
        )


def test_pathless_nested_external_record_is_reconciled_with_its_source() -> None:
    invocation = build_application_invocation(
        _load("training_dataset_variable_length.json"),
        input_reference="fixture://dataset-record-pathless",
    )
    execution = execute_application_invocation(invocation)
    assert execution.provenance is not None
    input_attachment = next(
        item
        for item in execution.provenance.attachments
        if item.name == "training_dataset/input"
    )
    forged_document = input_attachment.document_to_dict()
    forged_document["records"][0]["partition"] = "forged"
    forged_attachment = replace(input_attachment, document=forged_document)
    forged_bundle = replace(
        execution.provenance,
        attachments=tuple(
            forged_attachment if item is input_attachment else item
            for item in execution.provenance.attachments
        ),
    )

    with pytest.raises(SkatAIInvariantError, match="exact source"):
        validate_v1_retained_stage_linkage(
            invocation,
            execution.information_provenance_enforcement.sources,
            forged_bundle,
        )


def test_retained_exact_copy_requires_a_source_reference() -> None:
    invocation = build_application_invocation(
        _load("opponent_statistics.json"),
        input_reference="fixture://missing-reference",
    )
    execution = execute_application_invocation(invocation)
    assert execution.provenance is not None
    attachment = next(
        item
        for item in execution.provenance.attachments
        if item.name == "opponent_statistics/input"
    )
    original = next(entry for entry in attachment.ledger.entries if entry.source_references)
    forged_attachment = _replace_attachment_entry(
        attachment,
        original,
        replace(original, source_references=()),
    )
    forged_bundle = replace(
        execution.provenance,
        attachments=tuple(
            forged_attachment if item is attachment else item
            for item in execution.provenance.attachments
        ),
    )

    with pytest.raises(SkatAIInvariantError, match="no source reference"):
        validate_v1_retained_stage_linkage(
            invocation,
            execution.information_provenance_enforcement.sources,
            forged_bundle,
        )


def test_retained_exact_copy_rejects_an_unresolved_source_path() -> None:
    invocation = build_application_invocation(
        _load("opponent_statistics.json"),
        input_reference="fixture://missing-path",
    )
    execution = execute_application_invocation(invocation)
    assert execution.provenance is not None
    attachment = next(
        item
        for item in execution.provenance.attachments
        if item.name == "opponent_statistics/input"
    )
    original = next(entry for entry in attachment.ledger.entries if entry.source_references)
    forged_reference = replace(original.source_references[0], field_path="/missing")
    forged_attachment = _replace_attachment_entry(
        attachment,
        original,
        replace(original, source_references=(forged_reference,)),
    )
    forged_bundle = replace(
        execution.provenance,
        attachments=tuple(
            forged_attachment if item is attachment else item
            for item in execution.provenance.attachments
        ),
    )

    with pytest.raises(SkatAIInvariantError, match="path is missing"):
        validate_v1_retained_stage_linkage(
            invocation,
            execution.information_provenance_enforcement.sources,
            forged_bundle,
        )


def test_historical_replay_exact_copy_requires_its_explicit_source_path() -> None:
    invocation = build_application_invocation(
        _load("historical_grand_normal_completion.json"),
        input_reference="fixture://historical-replay-path",
    )
    execution = execute_application_invocation(invocation)
    assert execution.provenance is not None
    attachment = next(
        item
        for item in execution.provenance.attachments
        if item.name == "historical_game_result"
    )
    original = next(
        entry
        for entry in attachment.ledger.entries
        if entry.field_path
        == "/historical_game_summary/record/tricks/0/plays/0/card"
    )
    forged_references = tuple(
        replace(reference, field_path=None)
        if reference.reference_type == "historical_game"
        else reference
        for reference in original.source_references
    )
    forged_attachment = _replace_attachment_entry(
        attachment,
        original,
        replace(original, source_references=forged_references),
    )
    forged_bundle = replace(
        execution.provenance,
        attachments=tuple(
            forged_attachment if item is attachment else item
            for item in execution.provenance.attachments
        ),
    )

    with pytest.raises(SkatAIInvariantError, match="path is unresolved"):
        validate_v1_retained_stage_linkage(
            invocation,
            execution.information_provenance_enforcement.sources,
            forged_bundle,
        )


@pytest.mark.parametrize(
    "name",
    (
        "historical_grand_normal_completion.json",
        "training_dataset_normal_play.json",
    ),
)
def test_reconstructed_historical_replay_does_not_claim_a_pathless_exact_source(
    name: str,
) -> None:
    execution = execute_application_invocation(
        build_application_invocation(
            _load(name),
            input_reference=f"fixture://reconstructed-replay/{name}",
        )
    )
    assert execution.provenance is not None
    bound_types = {
        "external_record",
        "historical_event",
        "historical_game",
        "request",
        "retrospective_observation",
    }

    assert not [
        (attachment.name, entry.field_path, reference)
        for attachment in execution.provenance.attachments
        for entry in attachment.ledger.entries
        if entry.origin == "historical_replay"
        for reference in entry.source_references
        if reference.reference_type in bound_types and reference.field_path is None
    ]


def test_training_target_actual_card_is_reconciled_with_observed_play() -> None:
    invocation = build_application_invocation(
        _load("training_dataset_variable_length.json"),
        input_reference="fixture://target-card",
    )
    execution = execute_application_invocation(invocation)
    assert execution.provenance is not None
    attachment = next(
        item
        for item in execution.provenance.attachments
        if item.name == "training_dataset/sample/0/1/target"
    )
    forged_document = attachment.document_to_dict()
    forged_document["card"] = "C7"
    forged_attachment = replace(
        attachment,
        document=forged_document,
        coverage_summary=build_field_provenance_coverage_summary(
            forged_document,
            attachment.ledger,
        ),
    )
    forged_bundle = replace(
        execution.provenance,
        attachments=tuple(
            forged_attachment if item is attachment else item
            for item in execution.provenance.attachments
        ),
    )

    with pytest.raises(SkatAIInvariantError, match="exact source"):
        validate_v1_retained_stage_linkage(
            invocation,
            execution.information_provenance_enforcement.sources,
            forged_bundle,
        )


def test_top_level_matadors_remain_an_exact_retrospective_copy() -> None:
    invocation = build_application_invocation(
        _load("grand_post_game_mistake_actual_card.json"),
        input_reference="fixture://top-level-matadors",
    )
    execution = execute_application_invocation(invocation)
    assert execution.provenance is not None
    decision = next(
        item
        for item in execution.provenance.attachments
        if item.name == "flat_retrospective/input"
    )
    result_attachment = next(
        item
        for item in execution.provenance.attachments
        if item.name == "position_result"
    )
    matadors = next(
        entry
        for entry in decision.ledger.entries
        if entry.field_path == "/game_declaration/matadors"
    )
    private_position_entries = tuple(
        entry
        for entry in result_attachment.ledger.entries
        if entry.field_path.startswith(("/position/hand/", "/position/skat/"))
    )

    assert matadors.origin == "validated_copy"
    assert matadors.derivation == "validated"
    assert private_position_entries
    assert {entry.visibility for entry in private_position_entries} == {
        "post_game_only"
    }
    assert {entry.available_from for entry in private_position_entries} == {"game_end"}
    assert {
        entry.available_from_decision_index for entry in private_position_entries
    } == {None}


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        ({"perspective_player_id": "forged-player"}, "perspective"),
        ({"available_from_decision_index": 999}, "decision index"),
    ),
)
def test_retained_entry_cannot_self_authorize_aggregate_context(
    mutation: dict[str, object],
    message: str,
) -> None:
    invocation = build_application_invocation(
        _load("historical_grand_normal_completion.json"),
        input_reference="fixture://historical",
        options=ApplicationExecutionOptions(
            historical_game=HistoricalGameApplicationOptions(
                decision_snapshots=True,
            )
        ),
    )
    execution = execute_application_invocation(invocation)
    assert execution.provenance is not None
    summary = next(
        item
        for item in execution.provenance.attachments
        if item.name == "historical_snapshot_summary"
    )
    original = next(
        entry for entry in summary.ledger.entries if entry.visibility == "local_private"
    )
    forged_entry = replace(original, **mutation)
    forged_summary = _replace_attachment_entry(summary, original, forged_entry)
    forged_bundle = replace(
        execution.provenance,
        attachments=tuple(
            forged_summary if item is summary else item
            for item in execution.provenance.attachments
        ),
    )

    with pytest.raises(SkatAIInvariantError, match=message):
        validate_v1_retained_stage_linkage(
            invocation,
            execution.information_provenance_enforcement.sources,
            forged_bundle,
            trusted_checkpoint_documents=_trusted_checkpoints(execution),
        )

@pytest.mark.parametrize("nested", (False, True))
def test_application_handler_cannot_mutate_consumed_request(
    monkeypatch: pytest.MonkeyPatch,
    nested: bool,
) -> None:
    original = application_execution_module._HANDLERS[WorkflowV1.OPPONENT_STATISTICS]

    def mutating_handler(root, invocation, dependencies):
        if nested:
            root["opponent_statistics_input"]["records"].append({})
        else:
            root["forged"] = True
        return original(root, invocation, dependencies)

    monkeypatch.setitem(
        application_execution_module._HANDLERS,
        WorkflowV1.OPPONENT_STATISTICS,
        mutating_handler,
    )
    invocation = build_application_invocation(
        _load("opponent_statistics.json"),
        input_reference="fixture://guarded-request",
    )

    with pytest.raises((AttributeError, TypeError)):
        execute_application_invocation(invocation)


def test_live_hidden_skat_is_enforced_after_local_sanitization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document = _load("declarer_card_exposure_continuation.json")
    document["skat_visibility"] = "known_to_declarer"
    document["skat"] = ["CQ", "SQ"]
    original_sanitizer = information_view_module.build_local_analysis_input
    original_handler = application_execution_module._HANDLERS[
        WorkflowV1.POSITION_ANALYSIS
    ]
    handler_called = False

    def leaking_sanitizer(data):
        local_data = original_sanitizer(data)
        local_data["skat"] = list(data["skat"])
        return local_data

    def observed_handler(root, invocation, dependencies):
        nonlocal handler_called
        handler_called = True
        return original_handler(root, invocation, dependencies)

    monkeypatch.setattr(
        information_view_module,
        "build_local_analysis_input",
        leaking_sanitizer,
    )
    monkeypatch.setitem(
        application_execution_module._HANDLERS,
        WorkflowV1.POSITION_ANALYSIS,
        observed_handler,
    )
    invocation = build_application_invocation(
        document,
        input_reference="fixture://leaking-sanitizer",
    )

    with pytest.raises(SkatAIInvariantError, match="Local consumed Request"):
        execute_application_invocation(invocation)
    assert handler_called is False


def test_application_dependency_cannot_mutate_consumed_external_document(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_builder = position_workflow_module.build_opponent_statistics_from_document

    def mutating_builder(document):
        record = document["opponent_statistics_input"]["records"][0]
        dict.__setitem__(record, "games_played", 1)
        return original_builder(document)

    monkeypatch.setattr(
        position_workflow_module,
        "build_opponent_statistics_from_document",
        mutating_builder,
    )
    invocation = build_application_invocation(
        _load("grand_second_position.json"),
        input_reference="fixture://guarded-external-position",
        options=ApplicationExecutionOptions(
            position_analysis=PositionAnalysisApplicationOptions(
                sample_count_override=1,
                random_seed_override=42,
                use_profile_presets_override=True,
                left_opponent_player_id="opponent-123",
            )
        ),
        external_documents=ApplicationExternalDocuments(
            opponent_statistics_document=_load("opponent_statistics.json"),
            opponent_statistics_reference="fixture://guarded-external-statistics",
        ),
    )

    with pytest.raises(TypeError):
        execute_application_invocation(invocation)


def test_application_reconciles_base_class_request_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = application_execution_module._HANDLERS[WorkflowV1.OPPONENT_STATISTICS]

    def mutating_handler(root, invocation, dependencies):
        dict.__setitem__(root, "forged", True)
        return original(root, invocation, dependencies)

    monkeypatch.setitem(
        application_execution_module._HANDLERS,
        WorkflowV1.OPPONENT_STATISTICS,
        mutating_handler,
    )
    invocation = build_application_invocation(
        _load("opponent_statistics.json"),
        input_reference="fixture://reconciled-request",
    )

    with pytest.raises(TypeError):
        execute_application_invocation(invocation)


def test_input_reference_origin_cannot_self_disable_exact_reconciliation() -> None:
    invocation = build_application_invocation(
        _load("opponent_statistics.json"),
        input_reference="fixture://origin-relabel",
    )
    execution = execute_application_invocation(invocation)
    assert execution.provenance is not None
    attachment = next(
        item
        for item in execution.provenance.attachments
        if item.name == "opponent_statistics_result"
    )
    original = next(
        entry for entry in attachment.ledger.entries if entry.field_path == "/input_file"
    )
    forged_attachment = _replace_attachment_entry(
        attachment,
        original,
        replace(
            original,
            origin="rule_derived",
            derivation="deterministic_rule",
        ),
    )
    forged_bundle = replace(
        execution.provenance,
        attachments=tuple(
            forged_attachment if item is attachment else item
            for item in execution.provenance.attachments
        ),
    )

    with pytest.raises(SkatAIInvariantError, match="classification changed"):
        validate_v1_retained_stage_linkage(
            invocation,
            execution.information_provenance_enforcement.sources,
            forged_bundle,
        )


def test_bound_source_origin_cannot_self_disable_exact_reconciliation() -> None:
    invocation = build_application_invocation(
        _load("opponent_statistics.json"),
        input_reference="fixture://bound-origin-relabel",
    )
    execution = execute_application_invocation(invocation)
    assert execution.provenance is not None
    attachment = next(
        item
        for item in execution.provenance.attachments
        if item.name == "opponent_statistics/summary"
    )
    original = next(
        entry for entry in attachment.ledger.entries if entry.origin == "external_source"
    )
    forged_document = attachment.document_to_dict()
    forged_document["records"][0]["games_played"] += 1
    forged_attachment = replace(
        _replace_attachment_entry(
            attachment,
            original,
            replace(
                original,
                origin="rule_derived",
                derivation="deterministic_rule",
            ),
        ),
        document=forged_document,
    )
    forged_bundle = replace(
        execution.provenance,
        attachments=tuple(
            forged_attachment if item is attachment else item
            for item in execution.provenance.attachments
        ),
    )

    with pytest.raises(SkatAIInvariantError, match="resolvable exact source"):
        validate_v1_retained_stage_linkage(
            invocation,
            execution.information_provenance_enforcement.sources,
            forged_bundle,
        )


def test_rule_reference_cannot_disable_historical_exact_reconciliation() -> None:
    invocation = build_application_invocation(
        _load("historical_grand_normal_completion.json"),
        input_reference="fixture://historical-origin-relabel",
    )
    execution = execute_application_invocation(invocation)
    assert execution.provenance is not None
    attachment = next(
        item
        for item in execution.provenance.attachments
        if item.name == "historical_game_result"
    )
    path = "/historical_game_summary/record/tricks/0/plays/0/card"
    original = next(entry for entry in attachment.ledger.entries if entry.field_path == path)
    assert {reference.reference_type for reference in original.source_references} == {
        "historical_game",
        "rule_contract",
    }
    forged_document = attachment.document_to_dict()
    forged_document["historical_game_summary"]["record"]["tricks"][0]["plays"][0][
        "card"
    ] = "D8"
    forged_attachment = replace(
        _replace_attachment_entry(
            attachment,
            original,
            replace(
                original,
                origin="rule_derived",
                derivation="deterministic_rule",
            ),
        ),
        document=forged_document,
    )
    forged_bundle = replace(
        execution.provenance,
        attachments=tuple(
            forged_attachment if item is attachment else item
            for item in execution.provenance.attachments
        ),
    )

    with pytest.raises(SkatAIInvariantError, match="does not match its exact source"):
        validate_v1_retained_stage_linkage(
            invocation,
            execution.information_provenance_enforcement.sources,
            forged_bundle,
        )


def test_defaulted_position_value_must_match_canonical_defaults() -> None:
    invocation = build_application_invocation(
        _load("grand_second_position.json"),
        input_reference="fixture://canonical-default",
    )
    execution = execute_application_invocation(invocation)
    assert execution.provenance is not None
    attachment = next(
        item
        for item in execution.provenance.attachments
        if item.name == "position_result"
    )
    path = "/game_declaration/hand_game"
    entry = next(item for item in attachment.ledger.entries if item.field_path == path)
    assert entry.origin == "defaulted"
    forged_document = attachment.document_to_dict()
    forged_document["game_declaration"]["hand_game"] = True
    forged_attachment = replace(attachment, document=forged_document)
    forged_bundle = replace(
        execution.provenance,
        attachments=tuple(
            forged_attachment if item is attachment else item
            for item in execution.provenance.attachments
        ),
    )

    with pytest.raises(SkatAIInvariantError, match="does not match its exact source"):
        validate_v1_retained_stage_linkage(
            invocation,
            execution.information_provenance_enforcement.sources,
            forged_bundle,
        )


def test_historical_snapshot_cannot_change_from_retained_summary() -> None:
    invocation = build_application_invocation(
        _load("historical_grand_normal_completion.json"),
        input_reference="fixture://canonical-snapshot",
        options=ApplicationExecutionOptions(
            historical_game=HistoricalGameApplicationOptions(decision_snapshots=True)
        ),
    )
    execution = execute_application_invocation(invocation)
    assert execution.provenance is not None
    attachment = next(
        item
        for item in execution.provenance.attachments
        if item.name == "historical_game_result"
    )
    forged_document = attachment.document_to_dict()
    forged_document["historical_game_summary"]["decision_snapshot_summary"]["snapshots"][0][
        "visible_state"
    ]["own_hand"][0] = "D8"
    forged_attachment = replace(attachment, document=forged_document)
    forged_bundle = replace(
        execution.provenance,
        attachments=tuple(
            forged_attachment if item is attachment else item
            for item in execution.provenance.attachments
        ),
    )

    with pytest.raises(SkatAIInvariantError, match="retained Snapshot summary"):
        validate_v1_retained_stage_linkage(
            invocation,
            execution.information_provenance_enforcement.sources,
            forged_bundle,
            trusted_checkpoint_documents=_trusted_checkpoints(execution),
        )


def test_coordinated_historical_snapshot_copies_cannot_change_checkpoint() -> None:
    invocation = build_application_invocation(
        _load("historical_grand_normal_completion.json"),
        input_reference="fixture://snapshot-checkpoint",
        options=ApplicationExecutionOptions(
            historical_game=HistoricalGameApplicationOptions(decision_snapshots=True)
        ),
    )
    execution = execute_application_invocation(invocation)
    assert execution.provenance is not None
    replacements = {}
    for attachment in execution.provenance.attachments:
        document = attachment.document_to_dict()
        if attachment.name == "historical_game_result":
            document["historical_game_summary"]["decision_snapshot_summary"][
                "snapshots"
            ][0]["visible_state"]["own_hand"][0] = "D8"
        elif attachment.name == "historical_snapshot_summary":
            document["snapshots"][0]["visible_state"]["own_hand"][0] = "D8"
        elif attachment.name == "historical_decision/1/input":
            document["visible_state"]["own_hand"][0] = "D8"
        else:
            continue
        replacements[attachment.name] = replace(attachment, document=document)
    forged_bundle = replace(
        execution.provenance,
        attachments=tuple(
            replacements.get(attachment.name, attachment)
            for attachment in execution.provenance.attachments
        ),
    )

    with pytest.raises(SkatAIInvariantError, match="trusted Snapshot checkpoint"):
        validate_v1_retained_stage_linkage(
            invocation,
            execution.information_provenance_enforcement.sources,
            forged_bundle,
            trusted_checkpoint_documents=_trusted_checkpoints(execution),
        )


def test_training_summary_feature_is_bound_to_retained_feature() -> None:
    invocation = build_application_invocation(
        _load("training_dataset_normal_play.json"),
        input_reference="fixture://training-feature-aggregate",
    )
    execution = execute_application_invocation(invocation)
    assert execution.provenance is not None
    attachment = next(
        item
        for item in execution.provenance.attachments
        if item.name == "training_dataset/summary"
    )
    forged_document = attachment.document_to_dict()
    forged_document["records"][0]["samples"][0]["features"][
        "acting_position"
    ] = "forged-position"
    forged_attachment = replace(
        attachment,
        document=forged_document,
        coverage_summary=build_field_provenance_coverage_summary(
            forged_document,
            attachment.ledger,
        ),
    )
    forged_bundle = replace(
        execution.provenance,
        attachments=tuple(
            forged_attachment if item is attachment else item
            for item in execution.provenance.attachments
        ),
    )

    with pytest.raises(SkatAIInvariantError, match="exact aggregate"):
        validate_v1_retained_stage_linkage(
            invocation,
            execution.information_provenance_enforcement.sources,
            forged_bundle,
        )


def test_generated_source_aliases_do_not_reject_equal_user_identifiers() -> None:
    historical = _load("historical_grand_declarer_concession.json")
    historical["historical_game_input"]["game_id"] = "final_outcome_context"
    execute_application_invocation(
        build_application_invocation(
            historical,
            input_reference="fixture://alias-game-id",
        )
    )

    dataset = _load("training_dataset_normal_play.json")
    dataset["training_dataset_input"]["records"][0][
        "record_id"
    ] = "training_dataset_record/0"
    execute_application_invocation(
        build_application_invocation(
            dataset,
            input_reference="fixture://alias-record-id",
        )
    )

    cross_record = _load("training_dataset_normal_play.json")
    cross_record["training_dataset_input"]["records"][0][
        "record_id"
    ] = "training_dataset_record/1"
    execute_application_invocation(
        build_application_invocation(
            cross_record,
            input_reference="fixture://cross-record-alias",
        )
    )
