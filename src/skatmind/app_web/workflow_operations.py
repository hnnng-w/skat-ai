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
from .workflow_state import (
    FrontendWorkflowExecutionConflictError,
    StaleFrontendWorkflowRevisionError,
)


@dataclass(frozen=True, slots=True)
class FrontendWorkflowValidationError(ValueError):
    messages: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.messages or any(
            type(message) is not str or not message for message in self.messages
        ):
            raise ValueError("Frontend workflow validation messages must be non-empty text.")
        ValueError.__init__(self, "Frontend workflow validation failed.")


def _encoded_errors(errors: tuple[FormFieldErrorV1, ...]) -> tuple[str, ...]:
    return tuple(f"{error.field}::{error.message}" for error in errors)


def _safe_validation_error(error: Exception) -> tuple[str, ...]:
    if isinstance(error, SkatMindValidationError):
        field = error.path.lstrip("/").split("/", 1)[0] if error.path else "_form"
        message = error.message
        if len(message) <= 320 and "[" not in message and "{" not in message:
            return (f"{field or '_form'}::{message}",)
    return ("_form::The submitted information could not be validated.",)


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
        messages = _encoded_errors(error.errors)
        with context.lock:
            context.analyze_state = context.analyze_state.mutate(
                expected_revision=expected_revision,
                draft=error.draft,
                validation_messages=messages,
            )
        raise FrontendWorkflowValidationError(messages) from error

    with context.lock:
        if context.analyze_state.execution_source_revision is not None:
            raise FrontendWorkflowExecutionConflictError(
                "A frontend workflow execution is already in progress."
            )
        state = context.analyze_state.mutate(
            expected_revision=expected_revision,
            draft=draft,
        )
        state = state.begin(expected_revision=state.revision)
        context.analyze_state = state
        execution_revision = state.revision
    try:
        request, options = build_guided_position_execution_v1(draft)
    except PositionFormError as error:
        messages = _encoded_errors(error.errors)
        _retain_failed_execution(
            context,
            page="analyze",
            revision=execution_revision,
            messages=messages,
        )
        raise FrontendWorkflowValidationError(messages) from error
    except Exception:
        _retain_failed_execution(
            context,
            page="analyze",
            revision=execution_revision,
        )
        raise
    try:
        execution = execute_guided_frontend_analysis_v1(request, options=options)
    except SkatMindValidationError as error:
        messages = _safe_validation_error(error)
        _retain_failed_execution(
            context,
            page="analyze",
            revision=execution_revision,
            messages=messages,
        )
        raise FrontendWorkflowValidationError(messages) from error
    except Exception:
        _retain_failed_execution(
            context,
            page="analyze",
            revision=execution_revision,
        )
        raise
    _publish(
        context,
        page="analyze",
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
            raise FrontendWorkflowValidationError(
                ("_form::Import a valid Request before running it.",)
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
        messages = _safe_validation_error(error)
        _retain_failed_execution(
            context,
            page=page,
            revision=expected_revision,
            messages=messages,
        )
        raise FrontendWorkflowValidationError(messages) from error
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
            raise FrontendWorkflowValidationError(
                ("_form::Start the normal-completion editor first.",)
            )
        try:
            changed_draft = parser(draft, values)
        except HistoricalFormInputError as error:
            messages = _encoded_errors(error.errors)
            context.review_state = (
                state.mutate(
                    expected_revision=expected_revision,
                    draft=error.draft,
                    validation_messages=messages,
                )
                if error.draft is not None
                else state.reject(
                    expected_revision=expected_revision,
                    validation_messages=messages,
                )
            )
            raise FrontendWorkflowValidationError(messages) from error
        except ValueError as error:
            messages = _safe_validation_error(error)
            context.review_state = state.reject(
                expected_revision=expected_revision,
                validation_messages=messages,
            )
            raise FrontendWorkflowValidationError(messages) from error
        context.review_state = state.mutate(
            expected_revision=expected_revision,
            draft=changed_draft,
        )


def back_review_v1(context: AppWebContextV1, *, expected_revision: int) -> None:
    with context.lock:
        state = context.review_state
        state._require_expected_revision(expected_revision)
        if type(state.draft) is not HistoricalFormDraftV1:
            raise FrontendWorkflowValidationError(
                ("_form::Start the normal-completion editor first.",)
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
            raise FrontendWorkflowValidationError(
                ("_form::Start the normal-completion editor first.",)
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
            raise FrontendWorkflowValidationError(
                ("_form::Complete the guided normal-completion editor first.",)
            )
    with context.lock:
        state = context.review_state.begin(expected_revision=expected_revision)
        context.review_state = state
    try:
        request = build_historical_request_v1(draft)
        options = build_historical_execution_options_v1(draft)
    except (SkatMindValidationError, ValueError) as error:
        messages = _safe_validation_error(error)
        _retain_failed_execution(
            context,
            page="review",
            revision=expected_revision,
            messages=messages,
        )
        raise FrontendWorkflowValidationError(messages) from error
    except Exception:
        _retain_failed_execution(
            context,
            page="review",
            revision=expected_revision,
        )
        raise
    try:
        execution = execute_guided_frontend_review_v1(request, options=options)
    except SkatMindValidationError as error:
        messages = _safe_validation_error(error)
        _retain_failed_execution(
            context,
            page="review",
            revision=expected_revision,
            messages=messages,
        )
        raise FrontendWorkflowValidationError(messages) from error
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
            context.analyze_state = context.analyze_state.reset(
                expected_revision=expected_revision
            )
        else:
            context.review_state = context.review_state.reset(
                expected_revision=expected_revision
            )
