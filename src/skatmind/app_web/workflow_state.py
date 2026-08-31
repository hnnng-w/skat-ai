from __future__ import annotations

from dataclasses import dataclass, replace

from skatmind.api.v1 import ExecutionOptionsV1, ExecutionResultV1, RequestDocumentV1


class StaleFrontendWorkflowRevisionError(RuntimeError):
    """A process-local frontend transition targeted an obsolete revision."""


class FrontendWorkflowExecutionConflictError(RuntimeError):
    """A second execution targeted a workflow that is already running."""


_StaleFrontendWorkflowRevisionError = StaleFrontendWorkflowRevisionError


_NOT_SUPPLIED = object()


def _require_revision(value: object, name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a non-negative integer.")
    return value


def _require_messages(value: object) -> tuple[str, ...]:
    if type(value) is not tuple:
        raise ValueError("validation_messages must be an immutable tuple.")
    if any(type(message) is not str or not message for message in value):
        raise ValueError("validation_messages must contain only non-empty text.")
    return value


def _require_download_bytes(value: object, name: str) -> bytes:
    if type(value) is not bytes or not value:
        raise ValueError(f"{name} must be non-empty exact bytes.")
    return value


@dataclass(frozen=True, slots=True, kw_only=True)
class ProcessLocalFrontendWorkflowStateV1:
    """Immutable private state for one guided process-local workflow area."""

    revision: int = 0
    draft: object | None = None
    imported_request: RequestDocumentV1 | None = None
    latest_successful_request: RequestDocumentV1 | None = None
    latest_successful_options: ExecutionOptionsV1 | None = None
    latest_successful_result: ExecutionResultV1 | None = None
    request_json_bytes: bytes | None = None
    result_json_bytes: bytes | None = None
    validation_messages: tuple[str, ...] = ()
    execution_source_revision: int | None = None

    def __post_init__(self) -> None:
        revision = _require_revision(self.revision, "revision")
        if self.draft is not None and self.imported_request is not None:
            raise ValueError("draft and imported_request are mutually exclusive.")
        if (
            self.imported_request is not None
            and type(self.imported_request) is not RequestDocumentV1
        ):
            raise ValueError("imported_request must be an exact RequestDocumentV1 or None.")

        successful_values = (
            self.latest_successful_request,
            self.latest_successful_options,
            self.latest_successful_result,
            self.result_json_bytes,
        )
        if any(value is not None for value in successful_values) and not all(
            value is not None for value in successful_values
        ):
            raise ValueError("Successful execution values and bytes must be retained together.")
        if self.latest_successful_request is not None:
            if type(self.latest_successful_request) is not RequestDocumentV1:
                raise ValueError(
                    "latest_successful_request must be an exact RequestDocumentV1 or None."
                )
            if type(self.latest_successful_options) is not ExecutionOptionsV1:
                raise ValueError(
                    "latest_successful_options must be an exact ExecutionOptionsV1 or None."
                )
            if type(self.latest_successful_result) is not ExecutionResultV1:
                raise ValueError(
                    "latest_successful_result must be an exact ExecutionResultV1 or None."
                )
            _require_download_bytes(self.request_json_bytes, "request_json_bytes")
            _require_download_bytes(self.result_json_bytes, "result_json_bytes")
            if (
                self.latest_successful_request.workflow
                is not self.latest_successful_result.result.workflow
            ):
                raise ValueError("Successful Request and Result workflows must match.")
        elif self.request_json_bytes is not None:
            _require_download_bytes(self.request_json_bytes, "request_json_bytes")
            if self.imported_request is None:
                raise ValueError(
                    "Request download bytes without a Result require an imported Request."
                )

        _require_messages(self.validation_messages)
        if self.execution_source_revision is not None:
            source_revision = _require_revision(
                self.execution_source_revision,
                "execution_source_revision",
            )
            if source_revision > revision:
                raise ValueError("execution_source_revision must not exceed revision.")
            if (
                source_revision == revision
                and self.draft is None
                and self.imported_request is None
            ):
                raise ValueError("Current execution requires a draft or imported Request.")

    def _require_expected_revision(self, expected_revision: object) -> int:
        if type(expected_revision) is not int or expected_revision != self.revision:
            raise StaleFrontendWorkflowRevisionError(
                "The frontend workflow revision is stale."
            )
        return expected_revision

    def mutate(
        self,
        *,
        expected_revision: object,
        draft: object = _NOT_SUPPLIED,
        imported_request: object = _NOT_SUPPLIED,
        request_json_bytes: bytes | None = None,
        validation_messages: tuple[str, ...] = (),
    ) -> ProcessLocalFrontendWorkflowStateV1:
        """Accepts one draft or import mutation and invalidates retained output."""

        self._require_expected_revision(expected_revision)
        if (draft is _NOT_SUPPLIED) == (imported_request is _NOT_SUPPLIED):
            raise ValueError("Supply exactly one of draft or imported_request.")
        if draft is not _NOT_SUPPLIED:
            if draft is None:
                raise ValueError("draft must not be None; use reset instead.")
            next_draft = draft
            next_imported_request = None
            next_request_bytes = None
        else:
            if type(imported_request) is not RequestDocumentV1:
                raise ValueError("imported_request must be an exact RequestDocumentV1.")
            next_draft = None
            next_imported_request = imported_request
            next_request_bytes = request_json_bytes
            if next_request_bytes is not None:
                _require_download_bytes(next_request_bytes, "request_json_bytes")
        messages = _require_messages(validation_messages)
        return replace(
            self,
            revision=self.revision + 1,
            draft=next_draft,
            imported_request=next_imported_request,
            latest_successful_request=None,
            latest_successful_options=None,
            latest_successful_result=None,
            request_json_bytes=next_request_bytes,
            result_json_bytes=None,
            validation_messages=messages,
            execution_source_revision=None,
        )

    def reject(
        self,
        *,
        expected_revision: object,
        validation_messages: tuple[str, ...],
    ) -> ProcessLocalFrontendWorkflowStateV1:
        """Retains safe input after validation failure and invalidates output."""

        self._require_expected_revision(expected_revision)
        return replace(
            self,
            revision=self.revision + 1,
            latest_successful_request=None,
            latest_successful_options=None,
            latest_successful_result=None,
            request_json_bytes=(
                self.request_json_bytes if self.imported_request is not None else None
            ),
            result_json_bytes=None,
            validation_messages=_require_messages(validation_messages),
            execution_source_revision=None,
        )

    def reset(self, *, expected_revision: object) -> ProcessLocalFrontendWorkflowStateV1:
        """Clears current input and retained output as one accepted revision."""

        self._require_expected_revision(expected_revision)
        return replace(
            self,
            revision=self.revision + 1,
            draft=None,
            imported_request=None,
            latest_successful_request=None,
            latest_successful_options=None,
            latest_successful_result=None,
            request_json_bytes=None,
            result_json_bytes=None,
            validation_messages=(),
            execution_source_revision=None,
        )

    def begin(self, *, expected_revision: object) -> ProcessLocalFrontendWorkflowStateV1:
        """Marks one execution at the current revision without advancing it."""

        self._require_expected_revision(expected_revision)
        if self.execution_source_revision is not None:
            raise FrontendWorkflowExecutionConflictError(
                "A frontend workflow execution is already in progress."
            )
        if self.draft is None and self.imported_request is None:
            raise ValueError("Execution requires a current draft or imported Request.")
        return replace(
            self,
            latest_successful_request=None,
            latest_successful_options=None,
            latest_successful_result=None,
            request_json_bytes=(
                self.request_json_bytes if self.imported_request is not None else None
            ),
            result_json_bytes=None,
            validation_messages=(),
            execution_source_revision=self.revision,
        )

    def publish(
        self,
        *,
        expected_revision: object,
        execution_revision: object,
        request: object,
        options: object,
        result: object,
        request_json_bytes: object,
        result_json_bytes: object,
    ) -> ProcessLocalFrontendWorkflowStateV1:
        """Publishes exact retained values only for the still-current execution."""

        self._require_expected_revision(expected_revision)
        if (
            type(execution_revision) is not int
            or execution_revision != self.execution_source_revision
            or execution_revision != self.revision
        ):
            raise StaleFrontendWorkflowRevisionError(
                "The completed frontend workflow execution is stale."
            )
        if type(request) is not RequestDocumentV1:
            raise ValueError("request must be an exact RequestDocumentV1.")
        if type(options) is not ExecutionOptionsV1:
            raise ValueError("options must be an exact ExecutionOptionsV1.")
        if type(result) is not ExecutionResultV1:
            raise ValueError("result must be an exact ExecutionResultV1.")
        request_bytes = _require_download_bytes(request_json_bytes, "request_json_bytes")
        result_bytes = _require_download_bytes(result_json_bytes, "result_json_bytes")
        return replace(
            self,
            revision=self.revision + 1,
            latest_successful_request=request,
            latest_successful_options=options,
            latest_successful_result=result,
            request_json_bytes=request_bytes,
            result_json_bytes=result_bytes,
            validation_messages=(),
            execution_source_revision=None,
        )

    def fail(
        self,
        *,
        expected_revision: object,
        execution_revision: object,
        validation_messages: tuple[str, ...] = (),
    ) -> ProcessLocalFrontendWorkflowStateV1:
        """Finishes one failed execution without creating a successful Result."""

        self._require_expected_revision(expected_revision)
        if (
            type(execution_revision) is not int
            or execution_revision != self.execution_source_revision
        ):
            raise StaleFrontendWorkflowRevisionError(
                "The failed frontend workflow execution does not match the active execution."
            )
        return replace(
            self,
            validation_messages=_require_messages(validation_messages),
            execution_source_revision=None,
        )
