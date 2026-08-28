import copy
import json
from dataclasses import FrozenInstanceError, fields, replace
from pathlib import Path

import pytest

import skatmind.api.v1.provenance as public_contract_module
import skatmind.public_field_provenance as public_builder_module
from skatmind.api.v1 import (
    PUBLIC_FIELD_PROVENANCE_DOCUMENT_SCOPES,
    PUBLIC_FIELD_PROVENANCE_ROOT_FIELD,
    PUBLIC_FIELD_PROVENANCE_VERSION,
    ExecutionOptionsV1,
    FieldProvenanceArtifactV1,
    FieldProvenanceAttachmentV1,
    FieldProvenanceBundleV1,
    WorkflowV1,
    execute_document,
)
from skatmind.application import (
    ApplicationExecutionOptions,
    TrainingDatasetApplicationOptions,
    build_application_invocation,
    execute_application_invocation,
)
from skatmind.errors import SkatMindInvariantError, SkatMindValidationError
from skatmind.field_provenance import (
    FieldProvenanceLedger,
    FieldProvenanceSourceReference,
)
from skatmind.field_provenance_coverage import (
    build_field_provenance_coverage_summary,
)
from skatmind.public_field_provenance import build_public_field_provenance_bundle

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = PROJECT_ROOT / "examples"

WORKFLOW_CASES = (
    ("grand_second_position.json", WorkflowV1.POSITION_ANALYSIS, "position_result"),
    (
        "historical_grand_declarer_concession.json",
        WorkflowV1.HISTORICAL_GAME,
        "historical_game_result",
    ),
    (
        "training_dataset_variable_length.json",
        WorkflowV1.TRAINING_DATASET,
        "training_dataset_result",
    ),
    (
        "training_dataset_preparation_unavailable.json",
        WorkflowV1.TRAINING_DATASET_PREPARATION,
        "dataset_preparation_result",
    ),
    (
        "opponent_statistics.json",
        WorkflowV1.OPPONENT_STATISTICS,
        "opponent_statistics_result",
    ),
    (
        "fixed_three_player_historical_list_all_passed.json",
        WorkflowV1.FIXED_THREE_PLAYER_HISTORICAL_LIST,
        "historical_list_result",
    ),
    (
        "fixed_three_player_historical_list_comparison.json",
        WorkflowV1.FIXED_THREE_PLAYER_HISTORICAL_LIST_COMPARISON,
        "historical_list_comparison_result",
    ),
)


def _load(name: str) -> dict[str, object]:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def _execute_application(
    name: str,
    *,
    training_options: TrainingDatasetApplicationOptions | None = None,
):
    options = (
        ApplicationExecutionOptions(training_dataset=training_options)
        if training_options is not None
        else None
    )
    return execute_application_invocation(
        build_application_invocation(
            _load(name),
            input_reference=f"fixture://{name}",
            options=options,
        )
    )


def test_public_provenance_constants_and_contract_fields_are_exact() -> None:
    assert PUBLIC_FIELD_PROVENANCE_VERSION == 1
    assert PUBLIC_FIELD_PROVENANCE_ROOT_FIELD == "field_provenance"
    assert PUBLIC_FIELD_PROVENANCE_DOCUMENT_SCOPES == (
        "root_result_without_field_provenance",
        "artifact_document",
    )
    assert tuple(field.name for field in fields(FieldProvenanceAttachmentV1)) == (
        "attachment_name",
        "document_role",
        "document_scope",
        "ledger",
        "coverage_summary",
        "information_use_context",
    )
    assert tuple(field.name for field in fields(FieldProvenanceArtifactV1)) == (
        "artifact_name",
        "attachment",
    )
    assert tuple(field.name for field in fields(FieldProvenanceBundleV1)) == (
        "workflow",
        "result",
        "artifacts",
        "provenance_version",
        "redaction_policy",
    )


def test_public_contracts_are_recursive_defensive_immutable_and_deterministic() -> None:
    application = _execute_application("opponent_statistics.json")
    bundle = build_public_field_provenance_bundle(application)
    first = bundle.to_dict()
    second = bundle.to_dict()

    first["result"]["ledger"]["entries"].clear()
    first["artifacts"].append({"changed": True})

    assert second == bundle.to_dict()
    assert bundle.result.ledger["entries"]
    assert not hasattr(bundle.result, "document")
    with pytest.raises(TypeError):
        bundle.result.ledger["status"] = "partial_legacy"
    with pytest.raises(TypeError):
        bundle.result.ledger["entries"][0]["field_path"] = "/changed"
    with pytest.raises(FrozenInstanceError):
        bundle.workflow = WorkflowV1.POSITION_ANALYSIS


def test_public_attachment_rejects_malformed_nested_values_with_stable_errors() -> None:
    application = _execute_application("opponent_statistics.json")
    valid = build_public_field_provenance_bundle(application).result.to_dict()
    invalid_documents = []

    missing_entry_field = copy.deepcopy(valid)
    del missing_entry_field["ledger"]["entries"][0]["origin"]
    invalid_documents.append(missing_entry_field)
    unknown_entry_field = copy.deepcopy(valid)
    unknown_entry_field["ledger"]["entries"][0]["private"] = True
    invalid_documents.append(unknown_entry_field)
    unknown_visibility = copy.deepcopy(valid)
    unknown_visibility["ledger"]["entries"][0]["visibility"] = "secret"
    invalid_documents.append(unknown_visibility)
    invalid_context = copy.deepcopy(valid)
    invalid_context["information_use_context"]["stage"] = "future"
    invalid_documents.append(invalid_context)
    negative_count = copy.deepcopy(valid)
    negative_count["coverage_summary"]["leaf_path_count"] = -1
    invalid_documents.append(negative_count)
    boolean_count = copy.deepcopy(valid)
    boolean_count["coverage_summary"]["leaf_path_count"] = True
    invalid_documents.append(boolean_count)
    mismatched_count = copy.deepcopy(valid)
    mismatched_count["coverage_summary"]["leaf_path_count"] += 1
    invalid_documents.append(mismatched_count)
    invalid_pointer = copy.deepcopy(valid)
    invalid_pointer["ledger"]["entries"][0]["field_path"] = ["not", "a", "pointer"]
    invalid_documents.append(invalid_pointer)

    for document in invalid_documents:
        with pytest.raises(SkatMindValidationError):
            FieldProvenanceAttachmentV1(**document)


def test_public_result_reconciles_typed_artifact_provenance_with_actual_artifacts() -> None:
    execution = execute_document(
        _load("training_dataset_variable_length.json"),
        options=ExecutionOptionsV1(
            include_provenance=True,
            workflow_options={
                "operation": "historical_opponent_statistics_aggregation",
                "export_opponent_statistics": True,
            },
        ),
    )
    assert execution.field_provenance is not None
    assert len(execution.artifacts) == len(execution.field_provenance.artifacts) == 1

    with pytest.raises(SkatMindValidationError, match="actual execution artifacts"):
        replace(execution, artifacts=())


def test_explicit_public_mapping_tables_are_immutable() -> None:
    with pytest.raises(TypeError):
        public_contract_module._RESULT_ATTACHMENT_NAMES[
            WorkflowV1.POSITION_ANALYSIS
        ] = "changed"
    with pytest.raises(TypeError):
        public_builder_module._RESULT_ATTACHMENT_NAMES[
            "position_analysis"
        ] = "changed"
    with pytest.raises(TypeError):
        public_builder_module._ARTIFACT_ATTACHMENTS[
            "opponent_statistics_input"
        ] = ("training_dataset", "changed")


@pytest.mark.parametrize(
    ("example_name", "workflow", "attachment_name"),
    WORKFLOW_CASES,
)
def test_all_seven_result_attachment_mappings_are_explicit_and_complete(
    example_name: str,
    workflow: WorkflowV1,
    attachment_name: str,
) -> None:
    application = _execute_application(example_name)
    bundle = build_public_field_provenance_bundle(application)
    serialized = bundle.to_dict()

    assert bundle.workflow is workflow
    assert bundle.result.attachment_name == attachment_name
    assert bundle.result.document_role == "result"
    assert bundle.result.document_scope == "root_result_without_field_provenance"
    assert bundle.result.ledger["status"] == "complete"
    assert bundle.result.coverage_summary["all_paths_accounted_for"] is True
    assert bundle.result.coverage_summary["provenance_complete"] is True
    assert bundle.result.coverage_summary["uncovered_paths"] == ()
    assert serialized["result"]["coverage_summary"]["uncovered_paths"] == []
    assert serialized["result"]["information_use_context"]["workflow"] == workflow.value
    assert bundle.artifacts == ()


def test_actual_artifact_has_exact_separate_mapping_and_document_scope() -> None:
    application = _execute_application(
        "training_dataset_variable_length.json",
        training_options=TrainingDatasetApplicationOptions(
            operation="historical_opponent_statistics_aggregation",
            export_opponent_statistics=True,
        ),
    )
    bundle = build_public_field_provenance_bundle(application)

    assert len(application.artifacts) == len(bundle.artifacts) == 1
    public_artifact = bundle.artifacts[0]
    assert public_artifact.artifact_name == "opponent_statistics_input"
    assert public_artifact.attachment.attachment_name == (
        "training_dataset/opponent_statistics_input"
    )
    assert public_artifact.attachment.document_scope == "artifact_document"
    assert public_artifact.attachment.coverage_summary["provenance_complete"] is True
    assert "field_provenance" not in application.artifacts[0].to_dict()


def test_public_builder_redacts_private_references_without_mutating_internal_ledger() -> None:
    application = _execute_application("defender_open_play.json")
    assert application.provenance is not None
    internal = next(
        attachment
        for attachment in application.provenance.attachments
        if attachment.name == "position_result"
    )
    original = internal.ledger
    assert "defender_open_play_exact_proof_v1" in repr(original)

    bundle = build_public_field_provenance_bundle(application)
    serialized = json.dumps(bundle.to_dict(), sort_keys=True).lower()

    assert internal.ledger is original
    assert "defender_open_play_exact_proof_v1" not in serialized
    assert "private_dependencies_redacted" in serialized
    assert bundle.result.coverage_summary["provenance_complete"] is True


@pytest.mark.parametrize(
    "private_marker",
    (
        "engine-private-entry-marker",
        "engine-private-reference-marker",
        "engine-private-dependency-marker",
        "engine-private-world-identity-marker",
        "engine-private-ownership-marker",
        "engine-private-proof-state-marker",
        "engine-private-private-hand-marker",
        "engine-private-seed-marker",
        "engine-private-tie-key-marker",
        "engine-private-component-identity-marker",
        "engine-private-cache-marker",
        "engine-private-branch-marker",
        "engine-private-principal-variation-marker",
    ),
)
def test_adversarial_engine_private_categories_are_not_exposed(
    private_marker: str,
) -> None:
    application = _execute_application("opponent_statistics.json")
    assert application.provenance is not None
    internal = next(
        attachment
        for attachment in application.provenance.attachments
        if attachment.name == "opponent_statistics_result"
    )
    entries = list(internal.ledger.entries)
    private_reference = FieldProvenanceSourceReference(
        reference_type="algorithm",
        reference_id=private_marker,
        field_path=None,
        visibility="engine_private",
    )
    entries[0] = replace(
        entries[0],
        source_references=(*entries[0].source_references, private_reference),
    )
    ledger = FieldProvenanceLedger(
        status="complete",
        entries=tuple(entries),
        exemptions=internal.ledger.exemptions,
        limitations=internal.ledger.limitations,
    )
    forged_attachment = replace(
        internal,
        ledger=ledger,
        coverage_summary=build_field_provenance_coverage_summary(
            internal.document,
            ledger,
        ),
    )
    attachments = tuple(
        forged_attachment if attachment is internal else attachment
        for attachment in application.provenance.attachments
    )
    object.__setattr__(application.provenance, "attachments", attachments)

    serialized = json.dumps(
        build_public_field_provenance_bundle(application).to_dict(),
        sort_keys=True,
    )
    assert private_marker not in serialized


@pytest.mark.parametrize(
    ("mutation", "match"),
    (
        ("missing_result", "exactly one"),
        ("duplicate_result", "exactly one"),
        ("wrong_role", "result role"),
        ("wrong_document", "does not match"),
        ("unexpected_artifact_attachment", "do not match actual artifacts"),
    ),
)
def test_public_builder_rejects_impossible_result_and_artifact_mismatches(
    mutation: str,
    match: str,
) -> None:
    application = _execute_application("opponent_statistics.json")
    assert application.provenance is not None
    root = next(
        attachment
        for attachment in application.provenance.attachments
        if attachment.name == "opponent_statistics_result"
    )
    attachments = list(application.provenance.attachments)
    if mutation == "missing_result":
        attachments.remove(root)
    elif mutation == "duplicate_result":
        attachments.append(root)
    elif mutation == "wrong_role":
        object.__setattr__(root, "document_role", "consumed_input")
    elif mutation == "wrong_document":
        object.__setattr__(root, "document", {"wrong": True})
    else:
        artifact_source = _execute_application(
            "training_dataset_variable_length.json",
            training_options=TrainingDatasetApplicationOptions(
                operation="historical_opponent_statistics_aggregation",
                export_opponent_statistics=True,
            ),
        )
        assert artifact_source.provenance is not None
        artifact_attachment = next(
            attachment
            for attachment in artifact_source.provenance.attachments
            if attachment.name == "training_dataset/opponent_statistics_input"
        )
        attachments.append(artifact_attachment)
    object.__setattr__(application.provenance, "attachments", tuple(attachments))

    with pytest.raises(SkatMindInvariantError, match=match):
        build_public_field_provenance_bundle(application)


def test_public_builder_rejects_redaction_that_would_make_coverage_incomplete() -> None:
    application = _execute_application("opponent_statistics.json")
    assert application.provenance is not None
    root = next(
        attachment
        for attachment in application.provenance.attachments
        if attachment.name == "opponent_statistics_result"
    )
    entries = list(root.ledger.entries)
    entries[0] = replace(entries[0], visibility="engine_private")
    ledger = FieldProvenanceLedger(
        status="complete",
        entries=tuple(entries),
        exemptions=root.ledger.exemptions,
        limitations=root.ledger.limitations,
    )
    forged = copy.copy(root)
    object.__setattr__(forged, "ledger", ledger)
    object.__setattr__(
        forged,
        "coverage_summary",
        build_field_provenance_coverage_summary(root.document, ledger),
    )
    object.__setattr__(
        application.provenance,
        "attachments",
        tuple(
            forged if attachment is root else attachment
            for attachment in application.provenance.attachments
        ),
    )

    with pytest.raises(SkatMindInvariantError, match="not complete"):
        build_public_field_provenance_bundle(application)


def test_public_api_default_omits_and_opt_in_adds_equal_typed_provenance() -> None:
    source = _load("opponent_statistics.json")
    default = execute_document(source)
    opted_in = execute_document(
        source,
        options=ExecutionOptionsV1(include_provenance=True),
    )

    assert default.field_provenance is None
    assert "field_provenance" not in default.result.document
    assert opted_in.field_provenance is not None
    assert opted_in.result.to_dict()["document"]["field_provenance"] == (
        opted_in.field_provenance.to_dict()
    )
    stripped = opted_in.result.to_dict()["document"]
    stripped.pop("field_provenance")
    assert stripped == default.result.to_dict()["document"]
