from __future__ import annotations

from dataclasses import dataclass, field

from skatmind.api.v1 import (
    ExecutionOptionsV1,
    ExecutionResultV1,
    RequestDocumentV1,
    execute,
    serialize_result,
)

from .json_transfer import (
    FrontendPageV1,
    build_frontend_request_json_bytes_v1,
    canonical_frontend_json_bytes_v1,
    validate_frontend_request_page_v1,
)

ANALYZE_INPUT_REFERENCE = "memory://skatmind/app/analyze"
REVIEW_INPUT_REFERENCE = "memory://skatmind/app/review"


@dataclass(frozen=True, slots=True, kw_only=True)
class GuidedFrontendExecutionV1:
    """Retained public values and precomputed downloads from one execution."""

    request: RequestDocumentV1 = field(repr=False)
    options: ExecutionOptionsV1 = field(repr=False)
    result: ExecutionResultV1 = field(repr=False)
    request_json_bytes: bytes = field(repr=False)
    result_json_bytes: bytes = field(repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.request, RequestDocumentV1):
            raise ValueError("request must be a RequestDocumentV1.")
        if not isinstance(self.options, ExecutionOptionsV1):
            raise ValueError("options must be an ExecutionOptionsV1.")
        if not isinstance(self.result, ExecutionResultV1):
            raise ValueError("result must be an ExecutionResultV1.")
        if self.result.result.workflow is not self.request.workflow:
            raise ValueError("Result workflow must match the request workflow.")
        if type(self.request_json_bytes) is not bytes:
            raise ValueError("request_json_bytes must be immutable bytes.")
        if type(self.result_json_bytes) is not bytes:
            raise ValueError("result_json_bytes must be immutable bytes.")


def execute_guided_frontend_request_v1(
    request: RequestDocumentV1,
    *,
    options: ExecutionOptionsV1,
    page: FrontendPageV1,
) -> GuidedFrontendExecutionV1:
    """Executes one already parsed request once through the public boundary."""

    validate_frontend_request_page_v1(request, page=page)
    if not isinstance(options, ExecutionOptionsV1):
        raise ValueError("options must be an ExecutionOptionsV1.")
    if options.validate_output is not True:
        raise ValueError("Frontend execution requires output validation.")

    request_json_bytes = build_frontend_request_json_bytes_v1(request)
    input_reference = ANALYZE_INPUT_REFERENCE if page == "analyze" else REVIEW_INPUT_REFERENCE
    result = execute(
        request,
        options=options,
        input_reference=input_reference,
    )
    serialized_result = serialize_result(result)
    result_json_bytes = canonical_frontend_json_bytes_v1(serialized_result)
    return GuidedFrontendExecutionV1(
        request=request,
        options=options,
        result=result,
        request_json_bytes=request_json_bytes,
        result_json_bytes=result_json_bytes,
    )


def execute_guided_frontend_analysis_v1(
    request: RequestDocumentV1,
    *,
    options: ExecutionOptionsV1,
) -> GuidedFrontendExecutionV1:
    return execute_guided_frontend_request_v1(
        request,
        options=options,
        page="analyze",
    )


def execute_guided_frontend_review_v1(
    request: RequestDocumentV1,
    *,
    options: ExecutionOptionsV1,
) -> GuidedFrontendExecutionV1:
    return execute_guided_frontend_request_v1(
        request,
        options=options,
        page="review",
    )
