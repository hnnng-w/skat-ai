import json
from dataclasses import fields
from unittest.mock import patch

from test_session_decision_checkpoint import _checkpoint
from test_session_decision_observation import (
    _diverged_state,
    _ended_without_play,
    _observed,
)

import skatmind.api.v1.session as session
import skatmind.api.v1.session.contracts as session_contracts
import skatmind.api.v1.session.execution as session_execution
import skatmind.session_checkpoint_review as checkpoint_review
import skatmind.session_decision_observation as decision_observation
import skatmind.session_provenance as session_provenance
from skatmind.field_provenance_coverage import enumerate_json_leaf_paths
from skatmind.session_history import build_session_state_from_accepted_prefix_v1

FIRST_52_SESSION_EXPORTS = (
    "PUBLIC_SESSION_API_VERSION",
    "PUBLIC_SESSION_API_NAMESPACE",
    "PUBLIC_SESSION_API_COMPATIBILITY_POLICY",
    "SESSION_API_OPERATIONS",
    "SESSION_FIELD_PROVENANCE_VERSION",
    "SESSION_FIELD_PROVENANCE_DOCUMENT_SCOPE",
    "SessionApiVersionInfoV1",
    "SessionApiOptionsV1",
    "SessionApiResultV1",
    "SessionProvenanceContextV1",
    "SessionFieldProvenanceAttachmentV1",
    "SessionFieldProvenanceBundleV1",
    "get_session_api_version_info_v1",
    "SessionPlayerV1",
    "SessionStateV1",
    "SessionCommandRecordV1",
    "SessionCommandV1",
    "SetSessionGameMetadataCommandV1",
    "RecordSessionDealtCardCommandV1",
    "SetSessionDeclarerCommandV1",
    "SetSessionDeclarationCommandV1",
    "RecordSessionDiscardCommandV1",
    "RecordSessionPlayCommandV1",
    "SetSessionGameEventCommandV1",
    "SetSessionGameEndCommandV1",
    "PromoteSessionToRetrospectiveCommandV1",
    "SetSessionPublicHandCommandV1",
    "SessionValidationDiagnosticV1",
    "SessionExportReadinessV1",
    "SessionValidationResultV1",
    "SessionTransitionResultV1",
    "SessionPositionExportOptionsV1",
    "SessionRequestExportV1",
    "SessionDecisionCheckpointV1",
    "SessionUndoResultV1",
    "SessionCommandCorrectionV1",
    "SessionCorrectionResultV1",
    "SessionCheckpointLineageV1",
    "SessionPersistenceDocumentV1",
    "SessionResumeResultV1",
    "parse_session_command",
    "create_session",
    "apply_session_command",
    "rewind_session",
    "correct_session_command",
    "export_session_position_request",
    "export_session_historical_request",
    "build_session_decision_checkpoint",
    "classify_session_decision_checkpoint",
    "build_session_persistence_document",
    "resume_session_document",
    "serialize_session_result",
)

ISSUE_157_SESSION_EXPORTS = (
    "SESSION_DECISION_OBSERVATION_VERSION",
    "SESSION_CHECKPOINT_REVIEW_EXPORT_VERSION",
    "SessionDecisionObservationV1",
    "SessionCheckpointReviewExportV1",
    "observe_session_decision_checkpoint",
    "export_session_checkpoint_review_request",
)

FIRST_10_SESSION_OPERATIONS = (
    "create",
    "apply_command",
    "rewind",
    "correct",
    "export_position",
    "export_historical",
    "build_checkpoint",
    "classify_checkpoint",
    "build_persistence_document",
    "resume_persistence_document",
)

ISSUE_157_SESSION_OPERATIONS = (
    "observe_checkpoint",
    "export_checkpoint_review",
)

NO_OUTPUT_VALIDATION = session.SessionApiOptionsV1(validate_output=False)
WITH_PROVENANCE = session.SessionApiOptionsV1(
    include_provenance=True,
)


def _status_cases():
    pending_state, _, pending_checkpoint = _checkpoint()
    _, observed_state, observed_checkpoint = _observed()
    future_state = build_session_state_from_accepted_prefix_v1(
        pending_state,
        target_revision=pending_state.revision - 1,
    )
    ended_state, ended_checkpoint = _ended_without_play()
    return (
        ("pending", "unavailable", pending_state, pending_checkpoint),
        ("observed", "available", observed_state, observed_checkpoint),
        ("future", "unavailable", future_state, pending_checkpoint),
        (
            "diverged",
            "diverged",
            _diverged_state(pending_state),
            pending_checkpoint,
        ),
        ("ended_without_play", "unavailable", ended_state, ended_checkpoint),
    )


def _assert_complete_provenance(result: session.SessionApiResultV1) -> None:
    bundle = result.field_provenance
    assert bundle is not None
    assert bundle.operation == result.operation
    assert bundle.result.session_context["operation"] == result.operation
    assert bundle.result.coverage_summary["provenance_complete"] is True
    assert bundle.result.coverage_summary["uncovered_paths"] == ()
    assert bundle.result.coverage_summary["orphaned_entry_paths"] == ()
    assert bundle.result.coverage_summary["orphaned_exemption_paths"] == ()
    assert bundle.result.coverage_summary["overlapping_paths"] == ()
    assert bundle.result.ledger["status"] == "complete"
    assert bundle.result.ledger["exemptions"] == ()

    value_paths = set(enumerate_json_leaf_paths(result.value.to_dict()))
    entry_paths = {entry["field_path"] for entry in bundle.result.ledger["entries"]}
    assert entry_paths == value_paths
    assert bundle.result.coverage_summary["leaf_path_count"] == len(value_paths)
    assert bundle.result.coverage_summary["provenanced_path_count"] == len(value_paths)
    assert all(
        reference["visibility"] != "engine_private"
        for entry in bundle.result.ledger["entries"]
        for reference in entry["source_references"]
    )


def _entries_by_path(result: session.SessionApiResultV1) -> dict[str, object]:
    assert result.field_provenance is not None
    return {
        entry["field_path"]: entry for entry in result.field_provenance.result.ledger["entries"]
    }


def test_issue157_exports_preserve_the_first_52_and_append_in_exact_order() -> None:
    assert session.__all__[:52] == FIRST_52_SESSION_EXPORTS
    assert session.__all__[52:58] == ISSUE_157_SESSION_EXPORTS
    assert len(set(session.__all__)) == len(session.__all__)

    assert session.SESSION_API_OPERATIONS == (
        *FIRST_10_SESSION_OPERATIONS,
        *ISSUE_157_SESSION_OPERATIONS,
    )


def test_issue157_version_info_fields_are_appended_and_exact() -> None:
    info = session.get_session_api_version_info_v1()
    old_fields = (
        "api_contract_version",
        "public_session_api_version",
        "namespace",
        "compatibility_policy",
        "operations",
        "session_contract_version",
        "session_command_version",
        "transition_engine_version",
        "projection_version",
        "request_export_version",
        "decision_checkpoint_version",
        "history_edit_version",
        "checkpoint_lineage_version",
        "persistence_version",
    )
    new_fields = (
        "decision_observation_version",
        "checkpoint_review_export_version",
    )

    assert tuple(field.name for field in fields(type(info))) == (
        *old_fields,
        *new_fields,
    )
    assert tuple(info.to_dict()) == (*old_fields, *new_fields)
    assert info.operations == (*FIRST_10_SESSION_OPERATIONS, *ISSUE_157_SESSION_OPERATIONS)
    assert info.decision_observation_version == 1
    assert info.checkpoint_review_export_version == 1
    assert info.to_dict()["decision_observation_version"] == 1
    assert info.to_dict()["checkpoint_review_export_version"] == 1


def test_issue157_reexports_preserve_exact_type_and_function_identity() -> None:
    assert session.SessionDecisionObservationV1 is decision_observation.SessionDecisionObservationV1
    assert (
        session.SessionCheckpointReviewExportV1 is checkpoint_review.SessionCheckpointReviewExportV1
    )
    assert session.SessionApiVersionInfoV1 is session_contracts.SessionApiVersionInfoV1
    assert (
        session.observe_session_decision_checkpoint
        is session_execution.observe_session_decision_checkpoint
    )
    assert (
        session.export_session_checkpoint_review_request
        is session_execution.export_session_checkpoint_review_request
    )
    assert (
        session_execution.observe_session_decision_checkpoint_v1
        is decision_observation.observe_session_decision_checkpoint_v1
    )
    assert (
        session_execution.export_session_checkpoint_review_request_v1
        is checkpoint_review.export_session_checkpoint_review_request_v1
    )
    assert (
        session.SESSION_DECISION_OBSERVATION_VERSION
        == decision_observation.SESSION_DECISION_OBSERVATION_VERSION
        == 1
    )
    assert (
        session.SESSION_CHECKPOINT_REVIEW_EXPORT_VERSION
        == checkpoint_review.SESSION_CHECKPOINT_REVIEW_EXPORT_VERSION
        == 1
    )


def test_public_issue157_wrappers_cover_all_statuses_and_omit_provenance_by_default() -> None:
    def unexpected_provenance(**_kwargs):
        raise AssertionError("default path built provenance")

    with patch.object(
        session_provenance,
        "build_session_field_provenance_bundle_v1",
        unexpected_provenance,
    ):
        for expected_observation, expected_export, state, checkpoint in _status_cases():
            observed = session.observe_session_decision_checkpoint(
                state=state,
                checkpoint=checkpoint,
            )
            assert observed.operation == "observe_checkpoint"
            assert type(observed.value) is session.SessionDecisionObservationV1
            assert observed.value.status == expected_observation
            assert observed.field_provenance is None
            observed_document = session.serialize_session_result(observed)
            assert observed_document == observed.to_dict()
            assert "field_provenance" not in observed_document
            json.dumps(observed_document)

            exported = session.export_session_checkpoint_review_request(
                state=state,
                checkpoint=checkpoint,
            )
            assert exported.operation == "export_checkpoint_review"
            assert type(exported.value) is session.SessionCheckpointReviewExportV1
            assert exported.value.status == expected_export
            assert exported.value.observation.status == expected_observation
            assert exported.field_provenance is None
            exported_document = session.serialize_session_result(exported)
            assert exported_document == exported.to_dict()
            assert "field_provenance" not in exported_document
            json.dumps(exported_document)


def test_issue157_result_serialization_returns_fresh_mutable_documents() -> None:
    _, observed_state, checkpoint = _observed()
    observed = session.observe_session_decision_checkpoint(
        state=observed_state,
        checkpoint=checkpoint,
        options=NO_OUTPUT_VALIDATION,
    )
    exported = session.export_session_checkpoint_review_request(
        state=observed_state,
        checkpoint=checkpoint,
        options=NO_OUTPUT_VALIDATION,
    )

    observed_document = session.serialize_session_result(observed)
    observed_document["value"]["actual_card"] = "SA"
    assert observed.value.actual_card == "CA"

    exported_document = session.serialize_session_result(exported)
    exported_document["value"]["request"]["document"]["hand"].clear()
    assert exported.value.request.document["hand"]


def test_issue157_wrappers_delegate_once_and_provenance_does_not_rerun_operations() -> None:
    _, observed_state, checkpoint = _observed()
    cases = (
        (
            "observe_session_decision_checkpoint_v1",
            lambda options: session.observe_session_decision_checkpoint(
                state=observed_state,
                checkpoint=checkpoint,
                options=options,
            ),
        ),
        (
            "export_session_checkpoint_review_request_v1",
            lambda options: session.export_session_checkpoint_review_request(
                state=observed_state,
                checkpoint=checkpoint,
                options=options,
            ),
        ),
    )

    for internal_name, invoke in cases:
        internal_operation = getattr(session_execution, internal_name)
        for options in (NO_OUTPUT_VALIDATION, WITH_PROVENANCE):
            with patch.object(
                session_execution,
                internal_name,
                wraps=internal_operation,
            ) as operation_spy:
                result = invoke(options)
            assert operation_spy.call_count == 1, (internal_name, options)
            if options.include_provenance:
                _assert_complete_provenance(result)


def test_issue157_provenance_is_complete_for_every_public_status() -> None:
    for expected_observation, expected_export, state, checkpoint in _status_cases():
        observed = session.observe_session_decision_checkpoint(
            state=state,
            checkpoint=checkpoint,
            options=WITH_PROVENANCE,
        )
        exported = session.export_session_checkpoint_review_request(
            state=state,
            checkpoint=checkpoint,
            options=WITH_PROVENANCE,
        )
        assert observed.value.status == expected_observation
        assert exported.value.status == expected_export
        _assert_complete_provenance(observed)
        _assert_complete_provenance(exported)


def test_actual_card_fields_have_retrospective_after_play_provenance() -> None:
    _, observed_state, checkpoint = _observed()
    observed = session.observe_session_decision_checkpoint(
        state=observed_state,
        checkpoint=checkpoint,
        options=WITH_PROVENANCE,
    )
    exported = session.export_session_checkpoint_review_request(
        state=observed_state,
        checkpoint=checkpoint,
        options=WITH_PROVENANCE,
    )
    observed_entries = _entries_by_path(observed)
    exported_entries = _entries_by_path(exported)

    actual_value_paths = (
        (observed, observed_entries, "/actual_card"),
        (observed, observed_entries, "/observed_play_revision"),
        (exported, exported_entries, "/observation/actual_card"),
        (exported, exported_entries, "/observation/observed_play_revision"),
        (exported, exported_entries, "/request/document/actual_card_played"),
    )
    for result, entries, field_path in actual_value_paths:
        entry = entries[field_path]
        assert entry["origin"] == "retrospective_attachment", (
            result.operation,
            field_path,
        )
        assert entry["derivation"] == "retrospective"
        assert entry["visibility"] == "public"
        assert entry["available_from"] == "after_actual_play"
        assert entry["available_from_decision_index"] == checkpoint.decision_index
        assert entry["available_from_event_index"] is None
        assert {reference["reference_type"] for reference in entry["source_references"]} == {
            "retrospective_observation"
        }
        assert entry["source_references"][0]["reference_id"].endswith(
            f":accepted-play:{observed.value.observed_play_revision}"
        )

    assert observed.value.actual_card == "CA"
    assert exported.value.observation.actual_card == "CA"
    assert exported.value.request.document["actual_card_played"] == "CA"


def test_review_provenance_preserves_frozen_request_decision_time_boundary() -> None:
    _, observed_state, checkpoint = _observed()
    result = session.export_session_checkpoint_review_request(
        state=observed_state,
        checkpoint=checkpoint,
        options=WITH_PROVENANCE,
    )
    assert result.value.status == "available"
    entries = _entries_by_path(result)

    later_paths = {
        "/request/document/actual_card_played",
        "/request/document/analysis_mode",
    }
    frozen_request_entries = [
        entry
        for path, entry in entries.items()
        if path.startswith("/request/") and path not in later_paths
    ]
    assert frozen_request_entries
    assert {entry["available_from"] for entry in frozen_request_entries} == {"current_decision"}
    assert {entry["available_from_decision_index"] for entry in frozen_request_entries} == {
        checkpoint.decision_index
    }

    hand_entries = [
        entry for path, entry in entries.items() if path.startswith("/request/document/hand/")
    ]
    assert hand_entries
    assert {entry["visibility"] for entry in hand_entries} == {"local_private"}
    assert {entry["perspective_player_id"] for entry in hand_entries} == {
        checkpoint.acting_player_id
    }

    assert entries["/request/document/actual_card_played"]["available_from"] == (
        "after_actual_play"
    )
    analysis_mode = entries["/request/document/analysis_mode"]
    assert analysis_mode["origin"] == "rule_derived"
    assert analysis_mode["available_from"] == "offline_review"
