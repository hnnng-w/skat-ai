import copy
import json
import pickle
from dataclasses import fields, replace
from inspect import signature
from pathlib import Path

import pytest

from skatmind.api.v1 import ExecutionOptionsV1, WorkflowV1
from skatmind.application import (
    ApplicationExecutionOptions,
    PositionAnalysisApplicationOptions,
    build_application_invocation,
)
from skatmind.field_provenance import FIELD_PROVENANCE_VERSION
from skatmind.field_provenance_coverage import enumerate_json_leaf_paths
from skatmind.v1_information_provenance_enforcement import (
    V1_INFORMATION_PROVENANCE_ADVERSARIAL_POLICY,
    V1_INFORMATION_PROVENANCE_COMPATIBILITY_POLICY,
    V1_INFORMATION_PROVENANCE_ENFORCEMENT_STAGES,
    V1_INFORMATION_PROVENANCE_ENFORCEMENT_VERSION,
    V1_INFORMATION_PROVENANCE_EXECUTION_POLICY,
    V1_INFORMATION_PROVENANCE_LINKAGE_POLICY,
    V1_INFORMATION_PROVENANCE_LOADING_POLICY,
    V1_INFORMATION_PROVENANCE_PUBLIC_POLICY,
    V1_INFORMATION_PROVENANCE_SERIALIZATION_POLICY,
    V1_INFORMATION_PROVENANCE_USE_POLICY,
)
from skatmind.v1_information_provenance_sources import (
    V1InformationProvenanceSourceMetadata,
    build_v1_information_provenance_sources,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"

WORKFLOW_CASES = (
    ("grand_second_position.json", WorkflowV1.POSITION_ANALYSIS),
    ("historical_grand_declarer_concession.json", WorkflowV1.HISTORICAL_GAME),
    ("training_dataset_variable_length.json", WorkflowV1.TRAINING_DATASET),
    (
        "training_dataset_preparation_unavailable.json",
        WorkflowV1.TRAINING_DATASET_PREPARATION,
    ),
    ("opponent_statistics.json", WorkflowV1.OPPONENT_STATISTICS),
    (
        "fixed_three_player_historical_list_all_passed.json",
        WorkflowV1.FIXED_THREE_PLAYER_HISTORICAL_LIST,
    ),
    (
        "fixed_three_player_historical_list_comparison.json",
        WorkflowV1.FIXED_THREE_PLAYER_HISTORICAL_LIST_COMPARISON,
    ),
)


def _load(name: str) -> dict[str, object]:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def test_historical_actual_cards_use_one_based_decision_timing() -> None:
    invocation = build_application_invocation(
        _load("historical_grand_normal_completion.json"),
        input_reference="fixture://historical-timing",
    )
    sources = build_v1_information_provenance_sources(invocation)
    request = next(item for item in sources.attachments if item.name == "v1_source/request")
    first_card = next(
        entry
        for entry in request.ledger.entries
        if entry.field_path == "/historical_game_input/tricks/0/plays/0/card"
    )

    assert first_card.available_from_decision_index == 1


def test_live_defender_cannot_consume_declarer_known_skat_source() -> None:
    document = _load("declarer_card_exposure_continuation.json")
    document["skat_visibility"] = "known_to_declarer"
    document["skat"] = ["CQ", "SQ"]
    sources = build_v1_information_provenance_sources(
        build_application_invocation(
            document,
            input_reference="fixture://declarer-private-skat",
        )
    )
    request = next(item for item in sources.attachments if item.name == "v1_source/request")
    skat_entries = tuple(
        entry for entry in request.ledger.entries if entry.field_path.startswith("/skat/")
    )

    assert skat_entries
    assert {entry.visibility for entry in skat_entries} == {"post_game_only"}
    assert {entry.available_from for entry in skat_entries} == {"game_end"}


def _attachment(sources, name: str):
    return next(item for item in sources.attachments if item.name == name)


def test_v1_information_provenance_contract_constants_are_exact() -> None:
    assert V1_INFORMATION_PROVENANCE_ENFORCEMENT_VERSION == 1
    assert V1_INFORMATION_PROVENANCE_ENFORCEMENT_STAGES == (
        "loaded_request",
        "validated_consumed_input",
        "retained_stage_linkage",
        "final_serialization",
    )
    assert V1_INFORMATION_PROVENANCE_LOADING_POLICY == (
        "exact_verified_request_options_and_external_documents"
    )
    assert V1_INFORMATION_PROVENANCE_USE_POLICY == (
        "validate_information_use_context_before_downstream_use"
    )
    assert V1_INFORMATION_PROVENANCE_LINKAGE_POLICY == (
        "retained_values_link_to_authorized_loaded_or_retained_sources"
    )
    assert V1_INFORMATION_PROVENANCE_EXECUTION_POLICY == (
        "retained_stage_values_without_workflow_rerun"
    )
    assert V1_INFORMATION_PROVENANCE_SERIALIZATION_POLICY == (
        "exact_result_and_actual_artifact_reconciliation_before_return"
    )
    assert V1_INFORMATION_PROVENANCE_ADVERSARIAL_POLICY == (
        "reject_mutation_coverage_dependency_temporal_and_private_leakage"
    )
    assert V1_INFORMATION_PROVENANCE_PUBLIC_POLICY == (
        "preserve_existing_redacted_result_and_actual_artifact_boundary"
    )
    assert V1_INFORMATION_PROVENANCE_COMPATIBILITY_POLICY == (
        "no_public_field_version_schema_default_or_output_change"
    )
    assert FIELD_PROVENANCE_VERSION == 1
    with pytest.raises(ValueError):
        V1InformationProvenanceSourceMetadata(enforcement_version=True)


@pytest.mark.parametrize(("example_name", "workflow"), WORKFLOW_CASES)
def test_all_seven_verified_requests_have_one_complete_exact_source(
    example_name: str,
    workflow: WorkflowV1,
) -> None:
    document = _load(example_name)
    invocation = build_application_invocation(
        document,
        input_reference=f"fixture://{example_name}",
    )
    sources = build_v1_information_provenance_sources(invocation)
    request = _attachment(sources, "v1_source/request")
    options = _attachment(sources, "v1_source/application_options")

    assert sources.workflow is workflow
    assert request.document_role == "consumed_input"
    assert request.document_to_dict() == document
    assert request.ledger.status == "complete"
    assert request.ledger.exemptions == ()
    assert request.coverage_summary.provenance_complete is True
    assert tuple(entry.field_path for entry in request.ledger.entries) == tuple(
        sorted(enumerate_json_leaf_paths(document))
    )
    assert all(entry.origin == "caller_supplied" for entry in request.ledger.entries)
    assert options.document_role == "consumed_input"
    assert options.coverage_summary.provenance_complete is True
    assert all(
        item.name != "v1_source/external_opponent_statistics"
        for item in sources.attachments
    )


def test_effective_options_distinguish_explicit_defaults_from_omission() -> None:
    document = _load("grand_second_position.json")
    omitted = build_application_invocation(
        document,
        input_reference="fixture://omitted",
    )
    explicit = build_application_invocation(
        document,
        input_reference="fixture://explicit",
        options=ApplicationExecutionOptions(
            position_analysis=PositionAnalysisApplicationOptions(strict_context=False)
        ),
    )
    omitted_attachment = _attachment(
        build_v1_information_provenance_sources(omitted),
        "v1_source/application_options",
    )
    explicit_attachment = _attachment(
        build_v1_information_provenance_sources(explicit),
        "v1_source/application_options",
    )
    path = "/workflow_options/strict_context"

    assert omitted_attachment.document["workflow_options"]["strict_context"] is False
    assert explicit_attachment.document["workflow_options"]["strict_context"] is False
    assert next(
        entry.origin for entry in omitted_attachment.ledger.entries if entry.field_path == path
    ) == "defaulted"
    assert next(
        entry.origin for entry in explicit_attachment.ledger.entries if entry.field_path == path
    ) == "caller_supplied"
    assert next(
        entry.origin
        for entry in explicit_attachment.ledger.entries
        if entry.field_path == "/workflow_options/compare_policies"
    ) == "defaulted"
    assert next(
        entry.origin
        for entry in explicit_attachment.ledger.entries
        if entry.field_path == "/workflow_options/sample_count_override"
    ) == "defaulted"
    assert ExecutionOptionsV1()._provenance_supplied_option_names == ()
    assert ExecutionOptionsV1(
        validate_output=True
    )._provenance_supplied_option_names == ("validate_output",)


def test_option_source_distinguishes_an_explicit_empty_public_options_object() -> None:
    document = _load("grand_second_position.json")
    omitted = build_application_invocation(
        document,
        input_reference="fixture://omitted-options",
    )
    explicit = replace(
        omitted,
        provenance_source_metadata=V1InformationProvenanceSourceMetadata(
            application_options_supplied=True,
            supplied_execution_option_names=("workflow_options",),
        ),
    )

    omitted_document = _attachment(
        build_v1_information_provenance_sources(omitted),
        "v1_source/application_options",
    ).document_to_dict()
    explicit_document = _attachment(
        build_v1_information_provenance_sources(explicit),
        "v1_source/application_options",
    ).document_to_dict()

    assert omitted_document["application_options_supplied"] is False
    assert omitted_document["supplied_execution_option_names"] == []
    assert explicit_document["application_options_supplied"] is True
    assert explicit_document["supplied_execution_option_names"] == [
        "workflow_options"
    ]


def test_explicit_empty_internal_options_are_distinct_from_cli_omission() -> None:
    document = _load("grand_second_position.json")
    options = ApplicationExecutionOptions(
        position_analysis=PositionAnalysisApplicationOptions()
    )
    explicit = build_application_invocation(
        document,
        input_reference="fixture://explicit-empty",
        options=options,
    )
    cli_omitted = build_application_invocation(
        document,
        input_reference="fixture://cli-omitted",
        options=options,
        supplied_workflow_option_names=(),
    )

    assert explicit.provenance_source_metadata.application_options_supplied is True
    assert explicit.provenance_source_metadata.supplied_execution_option_names == (
        "workflow_options",
    )
    assert explicit.provenance_source_metadata.supplied_workflow_option_names == ()
    assert cli_omitted.provenance_source_metadata.application_options_supplied is False
    assert cli_omitted.provenance_source_metadata.supplied_execution_option_names == ()


def test_public_execution_option_presence_survives_copy_and_pickle() -> None:
    options = ExecutionOptionsV1(
        validate_output=True,
        workflow_options={"strict_context": False},
    )

    for restored in (
        copy.copy(options),
        copy.deepcopy(options),
        pickle.loads(pickle.dumps(options)),
    ):
        assert restored == options
        assert restored.to_dict() == options.to_dict()
        assert restored._provenance_supplied_option_names == (
            "validate_output",
            "workflow_options",
        )

    replaced = replace(options)
    assert replaced == options
    assert replaced.to_dict() == options.to_dict()
    assert replaced._provenance_supplied_option_names == (
        "validate_output",
        "workflow_options",
    )
    replaced_workflow_options = replace(
        options,
        workflow_options={"strict_context": True},
    )
    assert replaced_workflow_options._provenance_supplied_option_names == (
        "validate_output",
        "workflow_options",
    )
    assert replaced_workflow_options.workflow_options == {"strict_context": True}


def test_public_execution_option_constructor_signature_remains_stable() -> None:
    parameters = signature(ExecutionOptionsV1).parameters

    assert tuple(parameters) == (
        "validate_output",
        "include_provenance",
        "workflow_options",
        "opponent_statistics_document",
        "opponent_statistics_reference",
    )
    assert parameters["validate_output"].annotation == "bool"
    assert parameters["workflow_options"].annotation == "Mapping[str, object]"
    with pytest.raises(TypeError):
        ExecutionOptionsV1(_replace_state=None)  # type: ignore[call-arg]


def test_internal_workflow_option_presence_survives_replace_and_pickle() -> None:
    options = PositionAnalysisApplicationOptions(strict_context=False)

    for restored in (
        copy.copy(options),
        copy.deepcopy(options),
        pickle.loads(pickle.dumps(options)),
        replace(options),
    ):
        assert restored == options
        assert restored._provenance_supplied_option_names == ("strict_context",)

    changed = replace(options, compare_policies=True)
    assert changed._provenance_supplied_option_names == (
        "strict_context",
        "compare_policies",
    )


def test_historical_events_are_available_only_after_their_public_event() -> None:
    invocation = build_application_invocation(
        _load("historical_grand_declarer_card_exposure_continuation.json"),
        input_reference="fixture://historical-event",
    )
    request = _attachment(
        build_v1_information_provenance_sources(invocation),
        "v1_source/request",
    )
    event_entries = tuple(
        entry
        for entry in request.ledger.entries
        if "/game_events/0/" in entry.field_path
    )

    assert event_entries
    assert {entry.available_from for entry in event_entries} == {"after_public_event"}
    assert {entry.available_from_event_index for entry in event_entries} == {0}


def test_retrospective_position_private_cards_are_post_game_only() -> None:
    invocation = build_application_invocation(
        _load("defender_open_play.json"),
        input_reference="fixture://defender-open-play",
    )
    request = _attachment(
        build_v1_information_provenance_sources(invocation),
        "v1_source/request",
    )
    private_entries = tuple(
        entry
        for entry in request.ledger.entries
        if entry.field_path.startswith((
            "/hand/",
            "/skat/",
            "/game_shortening/remaining_hands/",
        ))
    )

    assert private_entries
    assert {entry.visibility for entry in private_entries} == {"post_game_only"}
    assert {entry.available_from for entry in private_entries} == {"game_end"}


def test_injected_external_document_has_one_exact_private_source() -> None:
    position = _load("grand_midgame_profile_preset_live.json")
    statistics = _load("opponent_statistics.json")
    from skatmind.application import ApplicationExternalDocuments

    invocation = build_application_invocation(
        position,
        input_reference="fixture://position",
        options=ApplicationExecutionOptions(
            position_analysis=PositionAnalysisApplicationOptions(
                use_profile_presets_override=True,
                left_opponent_player_id="left-player",
            )
        ),
        external_documents=ApplicationExternalDocuments(
            opponent_statistics_document=statistics,
            opponent_statistics_reference="fixture://statistics",
        ),
    )
    sources = build_v1_information_provenance_sources(invocation)
    external = _attachment(sources, "v1_source/external_opponent_statistics")

    assert external.document_to_dict() == statistics
    assert external.document_role == "consumed_input"
    assert external.coverage_summary.provenance_complete is True
    assert all(entry.origin == "external_source" for entry in external.ledger.entries)
    assert all(entry.visibility == "engine_private" for entry in external.ledger.entries)
    assert tuple(field.name for field in fields(type(sources))) == (
        "workflow",
        "attachments",
        "bindings",
        "source_build_count",
    )
