from __future__ import annotations

from dataclasses import FrozenInstanceError, fields

import pytest

from skatmind.api.v1 import (
    ExecutionOptionsV1,
    ExecutionResultV1,
    RequestDocumentV1,
    ResultDocumentV1,
    WorkflowV1,
)
from skatmind.app_web.guided_contracts import (
    ANALYZE_ACTION_ROUTE_PATHS,
    FRONTEND_JSON_TRANSFER_VERSION,
    FRONTEND_RESULT_PRESENTATION_VERSION,
    GUIDED_ACTION_ROUTE_PATHS,
    GUIDED_ANALYSIS_FRONTEND_POLICIES,
    GUIDED_ANALYSIS_FRONTEND_VERSION,
    GUIDED_DOWNLOAD_FILENAMES,
    GUIDED_DOWNLOAD_ROUTE_PATHS,
    GUIDED_HISTORICAL_REVIEW_FORM_VERSION,
    GUIDED_POSITION_FORM_VERSION,
    PROCESS_LOCAL_FRONTEND_WORKFLOW_STATE_VERSION,
    REVIEW_ACTION_ROUTE_PATHS,
    validate_guided_frontend_contract_v1,
)
from skatmind.app_web.workflow_state import (
    FrontendWorkflowExecutionConflictError,
    ProcessLocalFrontendWorkflowStateV1,
    _StaleFrontendWorkflowRevisionError,
)


def _execution_values() -> tuple[
    RequestDocumentV1,
    ExecutionOptionsV1,
    ExecutionResultV1,
]:
    request = RequestDocumentV1(
        workflow=WorkflowV1.POSITION_ANALYSIS,
        document={"position_analysis_input": {"analysis_mode": "live_decision"}},
    )
    options = ExecutionOptionsV1(validate_output=True)
    result = ExecutionResultV1(
        result=ResultDocumentV1(
            workflow=WorkflowV1.POSITION_ANALYSIS,
            document={"position": {"status": "complete"}},
        )
    )
    return request, options, result


def test_guided_private_versions_and_policies_are_exact() -> None:
    versions = (
        GUIDED_ANALYSIS_FRONTEND_VERSION,
        GUIDED_POSITION_FORM_VERSION,
        GUIDED_HISTORICAL_REVIEW_FORM_VERSION,
        FRONTEND_RESULT_PRESENTATION_VERSION,
        FRONTEND_JSON_TRANSFER_VERSION,
        PROCESS_LOCAL_FRONTEND_WORKFLOW_STATE_VERSION,
    )
    assert versions == (1, 1, 1, 1, 1, 1)
    assert all(type(version) is int for version in versions)
    assert GUIDED_ANALYSIS_FRONTEND_POLICIES == (
        "guided_forms_build_existing_root_documents",
        "one_explicit_application_execution_per_run",
        "normal_forms_reuse_existing_product_defaults",
        "advanced_settings_are_collapsed_and_explained",
        "strict_json_import_is_explicit_and_non_executing",
        "exact_json_download_uses_retained_values",
        "public_result_is_the_only_presentation_source",
        "normal_result_states_are_not_transport_errors",
        "process_local_state_without_implicit_persistence",
        "private_engine_state_never_enters_browser_state",
    )
    validate_guided_frontend_contract_v1()


@pytest.mark.parametrize(
    "name",
    (
        "guided_analysis_frontend_version",
        "guided_position_form_version",
        "guided_historical_review_form_version",
        "frontend_result_presentation_version",
        "frontend_json_transfer_version",
        "process_local_workflow_state_version",
    ),
)
@pytest.mark.parametrize("value", (True, 2, 1.0, "1"))
def test_guided_contract_validation_rejects_version_bool_and_drift(
    name: str,
    value: object,
) -> None:
    with pytest.raises(ValueError, match="strict integer 1"):
        validate_guided_frontend_contract_v1(**{name: value})


def test_guided_routes_and_download_filenames_are_exact_and_ordered() -> None:
    assert ANALYZE_ACTION_ROUTE_PATHS == (
        "/actions/analyze/run-guided",
        "/actions/analyze/import-json",
        "/actions/analyze/run-imported",
        "/actions/analyze/reset",
    )
    assert REVIEW_ACTION_ROUTE_PATHS == (
        "/actions/review/start",
        "/actions/review/update-players",
        "/actions/review/update-deal",
        "/actions/review/update-declaration",
        "/actions/review/update-discards",
        "/actions/review/append-play",
        "/actions/review/undo-play",
        "/actions/review/update-options",
        "/actions/review/back",
        "/actions/review/run-guided",
        "/actions/review/import-json",
        "/actions/review/run-imported",
        "/actions/review/reset",
    )
    assert GUIDED_ACTION_ROUTE_PATHS == ANALYZE_ACTION_ROUTE_PATHS + REVIEW_ACTION_ROUTE_PATHS
    assert GUIDED_DOWNLOAD_ROUTE_PATHS == (
        "/downloads/analyze/request.json",
        "/downloads/analyze/result.json",
        "/downloads/review/request.json",
        "/downloads/review/result.json",
    )
    assert GUIDED_DOWNLOAD_FILENAMES == (
        "skatmind-position-request.json",
        "skatmind-position-result.json",
        "skatmind-review-request.json",
        "skatmind-review-result.json",
    )

    with pytest.raises(ValueError, match="exact canonical ordered values"):
        validate_guided_frontend_contract_v1(
            policies=tuple(reversed(GUIDED_ANALYSIS_FRONTEND_POLICIES))
        )
    with pytest.raises(ValueError, match="exact canonical ordered values"):
        validate_guided_frontend_contract_v1(
            download_routes=GUIDED_DOWNLOAD_ROUTE_PATHS[:-1]
        )


def test_workflow_state_starts_at_revision_zero_and_is_immutable() -> None:
    state = ProcessLocalFrontendWorkflowStateV1()
    assert state.revision == 0
    assert state.draft is None
    assert state.imported_request is None
    assert state.execution_source_revision is None
    assert state.validation_messages == ()
    with pytest.raises(FrozenInstanceError):
        state.revision = 1  # type: ignore[misc]
    assert not hasattr(state, "__dict__")


def test_input_mutation_increments_once_and_invalidates_successful_result() -> None:
    request, options, result = _execution_values()
    draft = object()
    state = ProcessLocalFrontendWorkflowStateV1().mutate(
        expected_revision=0,
        draft=draft,
    )
    assert state.revision == 1
    assert state.draft is draft
    running = state.begin(expected_revision=1)
    assert running.revision == 1
    assert running.execution_source_revision == 1
    published = running.publish(
        expected_revision=1,
        execution_revision=1,
        request=request,
        options=options,
        result=result,
        request_json_bytes=b'{"request":true}\n',
        result_json_bytes=b'{"result":true}\n',
    )
    assert published.latest_successful_request is request
    assert published.latest_successful_options is options
    assert published.latest_successful_result is result
    assert published.revision == 2
    assert published.request_json_bytes == b'{"request":true}\n'
    assert published.result_json_bytes == b'{"result":true}\n'

    changed = published.mutate(
        expected_revision=2,
        draft={"safe": "entered value"},
        validation_messages=("One visible field needs correction.",),
    )
    assert changed.revision == 3
    assert changed.latest_successful_request is None
    assert changed.latest_successful_options is None
    assert changed.latest_successful_result is None
    assert changed.request_json_bytes is None
    assert changed.result_json_bytes is None
    assert changed.validation_messages == ("One visible field needs correction.",)


def test_import_and_reset_are_exact_exclusive_revisioned_mutations() -> None:
    request, _, _ = _execution_values()
    state = ProcessLocalFrontendWorkflowStateV1().mutate(
        expected_revision=0,
        imported_request=request,
    )
    assert state.revision == 1
    assert state.draft is None
    assert state.imported_request is request

    reset = state.reset(expected_revision=1)
    assert reset.revision == 2
    assert reset.draft is None
    assert reset.imported_request is None
    with pytest.raises(ValueError, match="mutually exclusive"):
        ProcessLocalFrontendWorkflowStateV1(draft=object(), imported_request=request)
    with pytest.raises(ValueError, match="exact RequestDocumentV1"):
        ProcessLocalFrontendWorkflowStateV1(imported_request=object())  # type: ignore[arg-type]


def test_strict_revisions_block_stale_mutation_duplicate_run_and_publication() -> None:
    request, options, result = _execution_values()
    state = ProcessLocalFrontendWorkflowStateV1().mutate(
        expected_revision=0,
        draft=object(),
    )
    with pytest.raises(_StaleFrontendWorkflowRevisionError):
        state.mutate(expected_revision=0, draft=object())
    with pytest.raises(_StaleFrontendWorkflowRevisionError):
        state.reset(expected_revision=True)

    running = state.begin(expected_revision=1)
    with pytest.raises(FrontendWorkflowExecutionConflictError, match="already in progress"):
        running.begin(expected_revision=1)
    changed = running.mutate(expected_revision=1, draft=object())
    assert changed.revision == 2
    assert changed.execution_source_revision is None
    with pytest.raises(_StaleFrontendWorkflowRevisionError, match="stale"):
        changed.publish(
            expected_revision=2,
            execution_revision=1,
            request=request,
            options=options,
            result=result,
            request_json_bytes=b"{}\n",
            result_json_bytes=b"{}\n",
        )
    with pytest.raises(_StaleFrontendWorkflowRevisionError, match="active execution"):
        changed.fail(expected_revision=2, execution_revision=1)


def test_failed_execution_retains_no_successful_values() -> None:
    state = (
        ProcessLocalFrontendWorkflowStateV1()
        .mutate(expected_revision=0, draft=object())
        .begin(expected_revision=1)
        .fail(
            expected_revision=1,
            execution_revision=1,
            validation_messages=("The execution did not complete.",),
        )
    )
    assert state.revision == 1
    assert state.execution_source_revision is None
    assert state.latest_successful_request is None
    assert state.latest_successful_options is None
    assert state.latest_successful_result is None
    assert state.request_json_bytes is None
    assert state.result_json_bytes is None
    assert state.validation_messages == ("The execution did not complete.",)


def test_workflow_state_has_no_path_timestamp_or_generated_identity_fields() -> None:
    field_names = tuple(field.name for field in fields(ProcessLocalFrontendWorkflowStateV1))
    assert "path" not in field_names
    assert "timestamp" not in field_names
    assert "id" not in field_names
    assert "identifier" not in field_names
    assert all("path" not in name and "timestamp" not in name for name in field_names)
