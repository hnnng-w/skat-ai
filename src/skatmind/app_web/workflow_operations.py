from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from skatmind.errors import SkatMindValidationError

from .context import AppWebContextV1
from .execution import (
    ExecutionOptionsV1,
    GuidedFrontendExecutionV1,
    RequestDocumentV1,
    execute_guided_frontend_analysis_v1,
    execute_guided_frontend_review_v1,
)
from .form_parsing import FormFieldErrorV1
from .form_registry import resolve_frontend_form_v1
from .guided_contracts import (
    ANALYZE_RUN_GUIDED_ACTION_ROUTE_PATH,
    ANALYZE_RUN_IMPORTED_ACTION_ROUTE_PATH,
    REVIEW_APPEND_PLAY_ACTION_ROUTE_PATH,
    REVIEW_RUN_GUIDED_ACTION_ROUTE_PATH,
    REVIEW_RUN_IMPORTED_ACTION_ROUTE_PATH,
    REVIEW_UPDATE_DEAL_ACTION_ROUTE_PATH,
    REVIEW_UPDATE_DECLARATION_ACTION_ROUTE_PATH,
    REVIEW_UPDATE_DISCARDS_ACTION_ROUTE_PATH,
    REVIEW_UPDATE_OPTIONS_ACTION_ROUTE_PATH,
    REVIEW_UPDATE_PLAYERS_ACTION_ROUTE_PATH,
)
from .historical_form import (
    HistoricalFormDraftV1,
    build_historical_execution_options_v1,
    build_historical_request_v1,
    create_historical_form_draft_v1,
    go_back_historical_form_v1,
    undo_historical_play_v1,
)
from .historical_form_parsing import (
    HistoricalFormInputError,
    parse_historical_deal_form_v1,
    parse_historical_declaration_form_v1,
    parse_historical_discards_form_v1,
    parse_historical_options_form_v1,
    parse_historical_play_form_v1,
    parse_historical_players_form_v1,
)
from .json_transfer import FrontendJsonImportV1
from .position_form import (
    PositionFormError,
    build_guided_position_execution_v1,
    parse_position_form_v1,
)
from .validation_contracts import FrontendValidationIssueV1
from .validation_mapping import map_form_field_errors_v1, map_frontend_exception_v1
from .workflow_state import StaleFrontendWorkflowRevisionError


@dataclass(frozen=True, slots=True)
class FrontendWorkflowValidationError(ValueError):
    issues: tuple[FrontendValidationIssueV1, ...]

    def __post_init__(self) -> None:
        if not self.issues or any(
            type(issue) is not FrontendValidationIssueV1 for issue in self.issues
        ):
            raise ValueError("Frontend workflow validation issues must be structured.")
        ValueError.__init__(self, "Frontend workflow validation failed.")


def _structured_errors(
    route: str,
    errors: tuple[FormFieldErrorV1, ...],
) -> tuple[FrontendValidationIssueV1, ...]:
    return map_form_field_errors_v1(errors, resolve_frontend_form_v1(route))


def _safe_validation_error(
    error: Exception,
    *,
    route: str,
) -> tuple[FrontendValidationIssueV1, ...]:
    definition = resolve_frontend_form_v1(route)
    if isinstance(error, SkatMindValidationError):
        field = error.path.lstrip("/").split("/", 1)[0] if error.path else "_form"
        return map_form_field_errors_v1(
            (FormFieldErrorV1(field or "_form", error.message),),
            definition,
        )
    return map_frontend_exception_v1(error, definition, status=400)


def _publish(
    context: AppWebContextV1,
    *,
    page: str,
    revision: int,
    execution: GuidedFrontendExecutionV1,
) -> None:
    with context.lock:
        state = context.analyze_state if page == "analyze" else context.review_state
        published = state.publish(
            expected_revision=revision,
            execution_revision=revision,
            request=execution.request,
            options=execution.options,
            result=execution.result,
            request_json_bytes=execution.request_json_bytes,
            result_json_bytes=execution.result_json_bytes,
        )
        if page == "analyze":
            context.analyze_state = published
        else:
            context.review_state = published


def _publish_candidate(
    context: AppWebContextV1,
    *,
    draft: object,
    revision: int,
    execution: GuidedFrontendExecutionV1,
) -> None:
    with context.lock:
        context.analyze_state = context.analyze_state.publish_candidate(
            expected_revision=revision,
            execution_revision=revision,
            draft=draft,
            request=execution.request,
            options=execution.options,
            result=execution.result,
            request_json_bytes=execution.request_json_bytes,
            result_json_bytes=execution.result_json_bytes,
        )


def _retain_failed_execution(
    context: AppWebContextV1,
    *,
    page: str,
    revision: int,
    messages: tuple[str, ...] = (),
) -> None:
    with context.lock:
        state = context.analyze_state if page == "analyze" else context.review_state
        if state.revision != revision or state.execution_source_revision != revision:
            raise StaleFrontendWorkflowRevisionError(
                "The completed frontend workflow execution is stale."
            )
        failed = state.fail(
            expected_revision=revision,
            execution_revision=revision,
            validation_messages=messages,
        )
        if page == "analyze":
            context.analyze_state = failed
        else:
            context.review_state = failed


def run_guided_analyze_v1(
    context: AppWebContextV1,
    *,
    expected_revision: int,
    values: Mapping[str, list[str] | tuple[str, ...]],
) -> None:
    try:
        draft = parse_position_form_v1(values)
    except PositionFormError as error:
        issues = _structured_errors(ANALYZE_RUN_GUIDED_ACTION_ROUTE_PATH, error.errors)
        raise FrontendWorkflowValidationError(issues) from error

    try:
        request, options = build_guided_position_execution_v1(draft)
    except PositionFormError as error:
        issues = _structured_errors(ANALYZE_RUN_GUIDED_ACTION_ROUTE_PATH, error.errors)
        raise FrontendWorkflowValidationError(issues) from error

    with context.lock:
        state = context.analyze_state.begin_candidate(
            expected_revision=expected_revision,
        )
        context.analyze_state = state
        execution_revision = state.revision
    try:
        execution = execute_guided_frontend_analysis_v1(request, options=options)
    except SkatMindValidationError as error:
        issues = _safe_validation_error(
            error,
            route=ANALYZE_RUN_GUIDED_ACTION_ROUTE_PATH,
        )
        _retain_failed_execution(
            context,
            page="analyze",
            revision=execution_revision,
        )
        raise FrontendWorkflowValidationError(issues) from error
    except Exception:
        _retain_failed_execution(
            context,
            page="analyze",
            revision=execution_revision,
        )
        raise
    _publish_candidate(
        context,
        draft=draft,
        revision=execution_revision,
        execution=execution,
    )


def store_frontend_import_v1(
    context: AppWebContextV1,
    *,
    page: str,
    expected_revision: int,
    imported: FrontendJsonImportV1,
) -> None:
    with context.lock:
        state = context.analyze_state if page == "analyze" else context.review_state
        changed = state.mutate(
            expected_revision=expected_revision,
            imported_request=imported.request,
            request_json_bytes=imported.request_json_bytes,
        )
        if page == "analyze":
            context.analyze_state = changed
        else:
            context.review_state = changed


def reject_frontend_mutation_v1(
    context: AppWebContextV1,
    *,
    page: str,
    expected_revision: int,
    messages: tuple[str, ...],
) -> None:
    with context.lock:
        state = context.analyze_state if page == "analyze" else context.review_state
        changed = state.reject(
            expected_revision=expected_revision,
            validation_messages=messages,
        )
        if page == "analyze":
            context.analyze_state = changed
        else:
            context.review_state = changed


def run_imported_request_v1(
    context: AppWebContextV1,
    *,
    page: str,
    expected_revision: int,
) -> None:
    with context.lock:
        state = context.analyze_state if page == "analyze" else context.review_state
        state._require_expected_revision(expected_revision)
        request = state.imported_request
        if type(request) is not RequestDocumentV1:
            definition = resolve_frontend_form_v1(
                ANALYZE_RUN_IMPORTED_ACTION_ROUTE_PATH
                if page == "analyze"
                else REVIEW_RUN_IMPORTED_ACTION_ROUTE_PATH
            )
            raise FrontendWorkflowValidationError(
                map_frontend_exception_v1(
                    ValueError("A valid imported Request is required."),
                    definition,
                    status=400,
                )
            )
        options = ExecutionOptionsV1(validate_output=True)
        state = state.begin(expected_revision=expected_revision)
        if page == "analyze":
            context.analyze_state = state
        else:
            context.review_state = state
    try:
        execution = (
            execute_guided_frontend_analysis_v1(request, options=options)
            if page == "analyze"
            else execute_guided_frontend_review_v1(request, options=options)
        )
    except SkatMindValidationError as error:
        route = (
            ANALYZE_RUN_IMPORTED_ACTION_ROUTE_PATH
            if page == "analyze"
            else REVIEW_RUN_IMPORTED_ACTION_ROUTE_PATH
        )
        issues = _safe_validation_error(error, route=route)
        _retain_failed_execution(
            context,
            page=page,
            revision=expected_revision,
        )
        raise FrontendWorkflowValidationError(issues) from error
    except Exception:
        _retain_failed_execution(
            context,
            page=page,
            revision=expected_revision,
        )
        raise
    _publish(
        context,
        page=page,
        revision=expected_revision,
        execution=execution,
    )


def start_review_v1(context: AppWebContextV1, *, expected_revision: int) -> None:
    with context.lock:
        context.review_state = context.review_state.mutate(
            expected_revision=expected_revision,
            draft=create_historical_form_draft_v1(),
        )


_REVIEW_FORM_OPERATIONS = {
    "players": parse_historical_players_form_v1,
    "deal": parse_historical_deal_form_v1,
    "declaration": parse_historical_declaration_form_v1,
    "discards": parse_historical_discards_form_v1,
    "play": parse_historical_play_form_v1,
    "options": parse_historical_options_form_v1,
}


def update_review_v1(
    context: AppWebContextV1,
    *,
    expected_revision: int,
    operation: str,
    values: Mapping[str, list[str] | tuple[str, ...]],
) -> None:
    parser = _REVIEW_FORM_OPERATIONS.get(operation)
    if parser is None:
        raise ValueError("Unknown guided Review operation.")
    with context.lock:
        state = context.review_state
        state._require_expected_revision(expected_revision)
        draft = state.draft
        if type(draft) is not HistoricalFormDraftV1:
            definition = resolve_frontend_form_v1(REVIEW_UPDATE_PLAYERS_ACTION_ROUTE_PATH)
            raise FrontendWorkflowValidationError(
                map_frontend_exception_v1(
                    ValueError("The normal-completion editor is required."),
                    definition,
                    status=400,
                )
            )
        try:
            changed_draft = parser(draft, values)
        except HistoricalFormInputError as error:
            route = {
                "players": REVIEW_UPDATE_PLAYERS_ACTION_ROUTE_PATH,
                "deal": REVIEW_UPDATE_DEAL_ACTION_ROUTE_PATH,
                "declaration": REVIEW_UPDATE_DECLARATION_ACTION_ROUTE_PATH,
                "discards": REVIEW_UPDATE_DISCARDS_ACTION_ROUTE_PATH,
                "play": REVIEW_APPEND_PLAY_ACTION_ROUTE_PATH,
                "options": REVIEW_UPDATE_OPTIONS_ACTION_ROUTE_PATH,
            }[operation]
            issues = _structured_errors(route, error.errors)
            raise FrontendWorkflowValidationError(issues) from error
        except ValueError as error:
            route = {
                "players": REVIEW_UPDATE_PLAYERS_ACTION_ROUTE_PATH,
                "deal": REVIEW_UPDATE_DEAL_ACTION_ROUTE_PATH,
                "declaration": REVIEW_UPDATE_DECLARATION_ACTION_ROUTE_PATH,
                "discards": REVIEW_UPDATE_DISCARDS_ACTION_ROUTE_PATH,
                "play": REVIEW_APPEND_PLAY_ACTION_ROUTE_PATH,
                "options": REVIEW_UPDATE_OPTIONS_ACTION_ROUTE_PATH,
            }[operation]
            definition = resolve_frontend_form_v1(route)
            raise FrontendWorkflowValidationError(
                map_frontend_exception_v1(error, definition, status=400)
            ) from error
        context.review_state = state.mutate(
            expected_revision=expected_revision,
            draft=changed_draft,
        )


def back_review_v1(context: AppWebContextV1, *, expected_revision: int) -> None:
    with context.lock:
        state = context.review_state
        state._require_expected_revision(expected_revision)
        if type(state.draft) is not HistoricalFormDraftV1:
            definition = resolve_frontend_form_v1(REVIEW_UPDATE_PLAYERS_ACTION_ROUTE_PATH)
            raise FrontendWorkflowValidationError(
                map_frontend_exception_v1(
                    ValueError("The normal-completion editor is required."),
                    definition,
                    status=400,
                )
            )
        changed = go_back_historical_form_v1(state.draft)
        context.review_state = state.mutate(
            expected_revision=expected_revision,
            draft=changed,
        )


def undo_review_play_v1(context: AppWebContextV1, *, expected_revision: int) -> None:
    with context.lock:
        state = context.review_state
        state._require_expected_revision(expected_revision)
        if type(state.draft) is not HistoricalFormDraftV1:
            definition = resolve_frontend_form_v1(REVIEW_APPEND_PLAY_ACTION_ROUTE_PATH)
            raise FrontendWorkflowValidationError(
                map_frontend_exception_v1(
                    ValueError("The normal-completion editor is required."),
                    definition,
                    status=400,
                )
            )
        changed = undo_historical_play_v1(state.draft)
        context.review_state = state.mutate(
            expected_revision=expected_revision,
            draft=changed,
        )


def run_guided_review_v1(
    context: AppWebContextV1,
    *,
    expected_revision: int,
) -> None:
    with context.lock:
        state = context.review_state
        state._require_expected_revision(expected_revision)
        draft = state.draft
        if type(draft) is not HistoricalFormDraftV1:
            definition = resolve_frontend_form_v1(REVIEW_RUN_GUIDED_ACTION_ROUTE_PATH)
            raise FrontendWorkflowValidationError(
                map_frontend_exception_v1(
                    ValueError("A completed guided editor is required."),
                    definition,
                    status=400,
                )
            )
    try:
        request = build_historical_request_v1(draft)
        options = build_historical_execution_options_v1(draft)
    except (SkatMindValidationError, ValueError) as error:
        issues = _safe_validation_error(
            error,
            route=REVIEW_RUN_GUIDED_ACTION_ROUTE_PATH,
        )
        raise FrontendWorkflowValidationError(issues) from error
    with context.lock:
        state = context.review_state.begin(expected_revision=expected_revision)
        context.review_state = state
    try:
        execution = execute_guided_frontend_review_v1(request, options=options)
    except SkatMindValidationError as error:
        issues = _safe_validation_error(
            error,
            route=REVIEW_RUN_GUIDED_ACTION_ROUTE_PATH,
        )
        _retain_failed_execution(
            context,
            page="review",
            revision=expected_revision,
        )
        raise FrontendWorkflowValidationError(issues) from error
    except Exception:
        _retain_failed_execution(
            context,
            page="review",
            revision=expected_revision,
        )
        raise
    _publish(
        context,
        page="review",
        revision=expected_revision,
        execution=execution,
    )


def reset_workflow_v1(
    context: AppWebContextV1,
    *,
    page: str,
    expected_revision: int,
) -> None:
    with context.lock:
        if page == "analyze":
            context.analyze_state = context.analyze_state.reset(expected_revision=expected_revision)
        else:
            context.review_state = context.review_state.reset(expected_revision=expected_revision)
