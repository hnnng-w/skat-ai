import json
from dataclasses import replace
from pathlib import Path

import pytest

import skat_ai.application.execution as execution_module
from skat_ai.application import build_application_invocation, execute_application_invocation
from skat_ai.errors import SkatAIInvariantError
from skat_ai.field_provenance import (
    FieldProvenanceLedger,
    FieldProvenanceSourceReference,
)
from skat_ai.field_provenance_coverage import build_field_provenance_coverage_summary
from skat_ai.field_provenance_policy import InformationUseContext
from skat_ai.v1_information_provenance_enforcement import (
    validate_v1_retained_stage_linkage,
)
from skat_ai.v1_information_provenance_sources import (
    build_v1_information_provenance_sources,
)

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str) -> dict[str, object]:
    return json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "mutation",
    (
        {"perspective_player_id": "different-player"},
        {
            "available_from": "request_start",
            "available_from_decision_index": None,
        },
    ),
)
def test_pre_analysis_enforcement_rejects_changed_source_before_handler(
    monkeypatch,
    mutation: dict[str, object],
) -> None:
    invocation = build_application_invocation(
        _load("grand_second_position.json"),
        input_reference="fixture://position",
    )
    sources = build_v1_information_provenance_sources(invocation)
    request = next(item for item in sources.attachments if item.name == "v1_source/request")
    hand = next(entry for entry in request.ledger.entries if entry.field_path.startswith("/hand/"))
    forged_entry = replace(hand, **mutation)
    forged_ledger = FieldProvenanceLedger(
        status="complete",
        entries=tuple(
            forged_entry if entry is hand else entry for entry in request.ledger.entries
        ),
        exemptions=(),
        limitations=(),
    )
    forged_request = replace(
        request,
        ledger=forged_ledger,
        coverage_summary=build_field_provenance_coverage_summary(
            request.document,
            forged_ledger,
        ),
    )
    object.__setattr__(
        sources,
        "attachments",
        tuple(forged_request if item is request else item for item in sources.attachments),
    )
    called = 0
    original = execution_module._HANDLERS[invocation.request.workflow]

    def counted(*args, **kwargs):
        nonlocal called
        called += 1
        return original(*args, **kwargs)

    monkeypatch.setitem(execution_module._HANDLERS, invocation.request.workflow, counted)
    monkeypatch.setattr(
        execution_module,
        "build_v1_information_provenance_sources",
        lambda _invocation: sources,
    )
    with pytest.raises(SkatAIInvariantError, match="ledger changed"):
        execute_application_invocation(invocation)
    assert called == 0


def test_live_request_source_marks_local_hand_at_the_exact_decision_context() -> None:
    invocation = build_application_invocation(
        _load("grand_left_to_act_live.json"),
        input_reference="fixture://live",
    )
    sources = build_v1_information_provenance_sources(invocation)
    request = next(item for item in sources.attachments if item.name == "v1_source/request")
    hand_entries = tuple(
        entry for entry in request.ledger.entries if entry.field_path.startswith("/hand/")
    )

    assert hand_entries
    assert {entry.visibility for entry in hand_entries} == {"local_private"}
    assert {entry.available_from for entry in hand_entries} == {"current_decision"}
    assert {entry.perspective_player_id for entry in hand_entries} == {"me"}
    assert request.information_use_context == InformationUseContext(
        workflow="position_analysis",
        stage="decision_time",
        perspective_player_id="me",
        perspective_side="declarer",
        decision_index=0,
        event_index=0,
    )


def test_live_request_source_counts_completed_and_current_plays() -> None:
    invocation = build_application_invocation(
        _load("grand_midgame_profile_preset_live.json"),
        input_reference="fixture://midgame-live",
    )
    request = next(
        item
        for item in build_v1_information_provenance_sources(invocation).attachments
        if item.name == "v1_source/request"
    )
    hand_entries = tuple(
        entry for entry in request.ledger.entries if entry.field_path.startswith("/hand/")
    )

    assert hand_entries
    assert request.information_use_context.decision_index == 11
    assert {entry.available_from_decision_index for entry in hand_entries} == {11}


def test_historical_actual_cards_are_indexed_and_full_hands_are_post_game_only() -> None:
    invocation = build_application_invocation(
        _load("historical_grand_normal_completion.json"),
        input_reference="fixture://historical",
    )
    sources = build_v1_information_provenance_sources(invocation)
    request = next(item for item in sources.attachments if item.name == "v1_source/request")
    hand_entries = tuple(
        entry for entry in request.ledger.entries if "/initial_hand/" in entry.field_path
    )
    card_entries = tuple(
        entry
        for entry in request.ledger.entries
        if "/tricks/" in entry.field_path and entry.field_path.endswith("/card")
    )

    assert hand_entries
    assert {entry.visibility for entry in hand_entries} == {"post_game_only"}
    assert {entry.available_from for entry in hand_entries} == {"game_end"}
    assert [entry.available_from_decision_index for entry in card_entries] == list(
        range(1, 31)
    )
    assert {entry.origin for entry in card_entries} == {"caller_supplied"}


def test_retained_linkage_rejects_forged_reference_identity_and_path() -> None:
    invocation = build_application_invocation(
        _load("opponent_statistics.json"),
        input_reference="fixture://statistics",
    )
    execution = execute_application_invocation(invocation)
    assert execution.provenance is not None
    assert execution.information_provenance_enforcement is not None
    root = next(
        item
        for item in execution.provenance.attachments
        if item.name == "opponent_statistics_result"
    )
    original_entry = root.ledger.entries[0]

    for reference in (
        FieldProvenanceSourceReference(
            reference_type="request",
            reference_id="forged_request",
            field_path=None,
            visibility="public",
        ),
        FieldProvenanceSourceReference(
            reference_type="request",
            reference_id="opponent_statistics_input",
            field_path="/missing",
            visibility="public",
        ),
    ):
        forged_entry = replace(original_entry, source_references=(reference,))
        forged_ledger = FieldProvenanceLedger(
            status="complete",
            entries=tuple(
                forged_entry if entry is original_entry else entry
                for entry in root.ledger.entries
            ),
            exemptions=root.ledger.exemptions,
            limitations=root.ledger.limitations,
        )
        forged_root = replace(
            root,
            ledger=forged_ledger,
            coverage_summary=build_field_provenance_coverage_summary(
                root.document,
                forged_ledger,
            ),
        )
        forged_bundle = replace(
            execution.provenance,
            attachments=tuple(
                forged_root if item is root else item
                for item in execution.provenance.attachments
            ),
        )
        with pytest.raises(SkatAIInvariantError, match="source reference"):
            validate_v1_retained_stage_linkage(
                invocation,
                execution.information_provenance_enforcement.sources,
                forged_bundle,
            )


def test_all_retained_attachments_are_complete_and_linked_once() -> None:
    invocation = build_application_invocation(
        _load("training_dataset_variable_length.json"),
        input_reference="fixture://dataset",
    )
    execution = execute_application_invocation(invocation)
    checkpoint = execution.information_provenance_enforcement

    assert checkpoint is not None
    assert checkpoint.source_build_count == 1
    assert checkpoint.pre_analysis_enforcement_count == 1
    assert checkpoint.retained_stage_linkage_count == 1
    assert checkpoint.final_serialization_count == 1
    assert checkpoint.linked_attachment_names == tuple(
        item.name for item in execution.provenance.attachments
    )


@pytest.mark.parametrize(
    "example_name",
    (
        "grand_second_position.json",
        "historical_grand_declarer_concession.json",
        "training_dataset_variable_length.json",
        "training_dataset_preparation_unavailable.json",
        "opponent_statistics.json",
        "fixed_three_player_historical_list_all_passed.json",
        "fixed_three_player_historical_list_comparison.json",
    ),
)
def test_each_root_invocation_runs_each_lifecycle_stage_and_handler_once(
    example_name: str,
    monkeypatch,
) -> None:
    invocation = build_application_invocation(
        _load(example_name),
        input_reference=f"fixture://{example_name}",
    )
    counts = {"source": 0, "pre": 0, "handler": 0, "link": 0, "final": 0}

    def counted(name, operation):
        def run(*args, **kwargs):
            counts[name] += 1
            return operation(*args, **kwargs)

        return run

    monkeypatch.setattr(
        execution_module,
        "build_v1_information_provenance_sources",
        counted("source", execution_module.build_v1_information_provenance_sources),
    )
    monkeypatch.setattr(
        execution_module,
        "enforce_v1_information_provenance_before_analysis",
        counted("pre", execution_module.enforce_v1_information_provenance_before_analysis),
    )
    monkeypatch.setattr(
        execution_module,
        "validate_v1_retained_stage_linkage",
        counted("link", execution_module.validate_v1_retained_stage_linkage),
    )
    monkeypatch.setattr(
        execution_module,
        "reconcile_v1_information_provenance_serialization",
        counted(
            "final",
            execution_module.reconcile_v1_information_provenance_serialization,
        ),
    )
    monkeypatch.setitem(
        execution_module._HANDLERS,
        invocation.request.workflow,
        counted("handler", execution_module._HANDLERS[invocation.request.workflow]),
    )

    execute_application_invocation(invocation)

    assert counts == {"source": 1, "pre": 1, "handler": 1, "link": 1, "final": 1}
