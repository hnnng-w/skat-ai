from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal

from skatmind.api.v1 import RequestDocumentV1, WorkflowV1, parse_request, serialize_result
from skatmind.api.v1.contracts import ExecutionResultV1
from skatmind.errors import SkatMindWorkflowError

FRONTEND_JSON_TRANSFER_VERSION = 1
FRONTEND_JSON_MAX_FILE_BYTES = 1_048_576

FrontendPageV1 = Literal["analyze", "review"]

_BOUNDARY_CHARACTERS = frozenset(
    "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'()+_,-./:=?"
)
_TOKEN_CHARACTERS = frozenset(
    "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!#$%&'*+-.^_`|~"
)
_PRIMARY_CHARACTERS = _TOKEN_CHARACTERS | {"/"}
_HEADER_NAME = re.compile(rb"^[!#$%&'*+.^_`|~0-9A-Za-z-]+$")
_PAGES = frozenset({"analyze", "review"})


@dataclass(frozen=True, slots=True, kw_only=True)
class ImportedRequestSummaryV1:
    """Browser-safe facts about one imported Root request."""

    workflow: WorkflowV1
    analysis_mode: str | None
    game_end_reason: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.workflow, WorkflowV1):
            raise ValueError("Imported summary workflow must be a WorkflowV1 value.")
        for name in ("analysis_mode", "game_end_reason"):
            value = getattr(self, name)
            if value is not None and type(value) is not str:
                raise ValueError(f"Imported summary {name} must be text or None.")

    def to_dict(self) -> dict[str, str | None]:
        return {
            "workflow": self.workflow.value,
            "analysis_mode": self.analysis_mode,
            "game_end_reason": self.game_end_reason,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class FrontendJsonImportV1:
    """One in-memory imported request without caller file metadata."""

    revision: str
    request: RequestDocumentV1 = field(repr=False)
    summary: ImportedRequestSummaryV1
    request_json_bytes: bytes = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.revision) is not str or not self.revision:
            raise ValueError("Multipart revision must be non-empty text.")
        if not isinstance(self.request, RequestDocumentV1):
            raise ValueError("Imported request must be a RequestDocumentV1.")
        if not isinstance(self.summary, ImportedRequestSummaryV1):
            raise ValueError("Imported summary must be an ImportedRequestSummaryV1.")
        if self.summary.workflow is not self.request.workflow:
            raise ValueError("Imported summary workflow must match the request workflow.")
        if type(self.request_json_bytes) is not bytes:
            raise ValueError("Imported request JSON must be immutable bytes.")


def _reject_duplicate_json_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"Duplicate JSON object key {key!r} is not allowed.")
        value[key] = item
    return value


def _reject_non_finite_json_constant(value: str) -> object:
    raise ValueError(f"Non-finite JSON number {value!r} is not allowed.")


def _finite_json_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError(f"Non-finite JSON number {value!r} is not allowed.")
    return parsed


def decode_frontend_json_object_v1(raw_bytes: bytes) -> dict[str, object]:
    """Decodes one bounded finite UTF-8 JSON object without a BOM."""

    if type(raw_bytes) is not bytes:
        raise ValueError("Uploaded JSON must be immutable bytes.")
    if len(raw_bytes) > FRONTEND_JSON_MAX_FILE_BYTES:
        raise OverflowError("Uploaded JSON file is too large.")
    if raw_bytes.startswith(b"\xef\xbb\xbf"):
        raise ValueError("Uploaded JSON must not contain a UTF-8 BOM.")
    try:
        decoded = raw_bytes.decode("utf-8")
        value = json.loads(
            decoded,
            object_pairs_hook=_reject_duplicate_json_keys,
            parse_constant=_reject_non_finite_json_constant,
            parse_float=_finite_json_float,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("Uploaded file must contain valid UTF-8 JSON.") from error
    if not isinstance(value, dict):
        raise ValueError("Uploaded JSON root must be an object.")
    return value


def canonical_frontend_json_bytes_v1(value: object) -> bytes:
    """Serializes deterministic finite pretty JSON with one trailing LF."""

    return (
        json.dumps(
            value,
            ensure_ascii=True,
            allow_nan=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def build_frontend_request_json_bytes_v1(request: RequestDocumentV1) -> bytes:
    if not isinstance(request, RequestDocumentV1):
        raise ValueError("request must be a RequestDocumentV1.")
    return canonical_frontend_json_bytes_v1(request.to_dict()["document"])


def build_frontend_result_json_bytes_v1(result: ExecutionResultV1) -> bytes:
    if not isinstance(result, ExecutionResultV1):
        raise ValueError("result must be an ExecutionResultV1.")
    return canonical_frontend_json_bytes_v1(serialize_result(result))


def _parse_parameterized_header(
    value: str,
    *,
    header_name: str,
) -> tuple[str, dict[str, str]]:
    if not value or "\r" in value or "\n" in value:
        raise ValueError(f"Malformed {header_name} header.")
    length = len(value)
    cursor = 0
    while cursor < length and value[cursor] in " \t":
        cursor += 1
    start = cursor
    while cursor < length and value[cursor] in _PRIMARY_CHARACTERS:
        cursor += 1
    if cursor == start:
        raise ValueError(f"Malformed {header_name} header.")
    primary = value[start:cursor].lower()
    parameters: dict[str, str] = {}

    while True:
        while cursor < length and value[cursor] in " \t":
            cursor += 1
        if cursor == length:
            return primary, parameters
        if value[cursor] != ";":
            raise ValueError(f"Malformed {header_name} parameters.")
        cursor += 1
        while cursor < length and value[cursor] in " \t":
            cursor += 1
        name_start = cursor
        while cursor < length and value[cursor] in _TOKEN_CHARACTERS:
            cursor += 1
        if cursor == name_start:
            raise ValueError(f"Malformed {header_name} parameters.")
        name = value[name_start:cursor].lower()
        while cursor < length and value[cursor] in " \t":
            cursor += 1
        if cursor == length or value[cursor] != "=":
            raise ValueError(f"Malformed {header_name} parameters.")
        cursor += 1
        while cursor < length and value[cursor] in " \t":
            cursor += 1
        if cursor == length:
            raise ValueError(f"Malformed {header_name} parameters.")

        if value[cursor] == '"':
            cursor += 1
            characters: list[str] = []
            while cursor < length and value[cursor] != '"':
                character = value[cursor]
                if character == "\\":
                    cursor += 1
                    if cursor == length:
                        raise ValueError(f"Malformed {header_name} parameters.")
                    character = value[cursor]
                if ord(character) < 32 or ord(character) == 127:
                    raise ValueError(f"Malformed {header_name} parameters.")
                characters.append(character)
                cursor += 1
            if cursor == length:
                raise ValueError(f"Malformed {header_name} parameters.")
            cursor += 1
            item = "".join(characters)
        else:
            item_start = cursor
            while cursor < length and value[cursor] in _TOKEN_CHARACTERS:
                cursor += 1
            if cursor == item_start:
                raise ValueError(f"Malformed {header_name} parameters.")
            item = value[item_start:cursor]

        if name in parameters:
            raise ValueError(f"Malformed {header_name} parameters.")
        parameters[name] = item


def _multipart_boundary(content_type: str) -> bytes:
    if type(content_type) is not str:
        raise ValueError("Content-Type must be text.")
    primary, parameters = _parse_parameterized_header(
        content_type,
        header_name="Content-Type",
    )
    if primary != "multipart/form-data" or set(parameters) != {"boundary"}:
        raise ValueError("Content-Type must be strict multipart/form-data.")
    boundary = parameters["boundary"]
    if (
        not 1 <= len(boundary) <= 70
        or boundary[-1] == " "
        or any(character not in _BOUNDARY_CHARACTERS for character in boundary)
    ):
        raise ValueError("Multipart boundary is malformed.")
    try:
        return boundary.encode("ascii")
    except UnicodeEncodeError as error:
        raise ValueError("Multipart boundary must be ASCII.") from error


def _part_headers(raw_headers: bytes) -> dict[str, str]:
    headers: dict[str, str] = {}
    for line in raw_headers.split(b"\r\n"):
        if not line or line[:1] in b" \t" or b":" not in line:
            raise ValueError("Multipart part headers are malformed.")
        raw_name, raw_value = line.split(b":", 1)
        if not _HEADER_NAME.fullmatch(raw_name):
            raise ValueError("Multipart part header name is malformed.")
        try:
            name = raw_name.decode("ascii").lower()
            value = raw_value.decode("latin-1").strip(" \t")
        except UnicodeDecodeError as error:
            raise ValueError("Multipart part header name must be ASCII.") from error
        if not value or any(
            (ord(character) < 32 and character != "\t") or ord(character) == 127
            for character in value
        ):
            raise ValueError("Multipart part headers are malformed.")
        if name in headers:
            raise ValueError("Multipart part headers must not repeat.")
        headers[name] = value
    unsupported = set(headers) - {"content-disposition", "content-type"}
    if "content-transfer-encoding" in unsupported:
        raise ValueError("Multipart transfer encodings are not supported.")
    if unsupported:
        raise ValueError("Multipart part contains unsupported headers.")
    return headers


def _multipart_sections(body: bytes, boundary: bytes) -> tuple[bytes, ...]:
    opening = b"--" + boundary + b"\r\n"
    marker = b"\r\n--" + boundary
    if not body.startswith(opening):
        raise ValueError("Multipart boundary framing is malformed.")
    sections: list[bytes] = []
    cursor = len(opening)
    while True:
        boundary_index = body.find(marker, cursor)
        while boundary_index >= 0:
            suffix = body[boundary_index + len(marker) :]
            if suffix.startswith(b"\r\n") or suffix.startswith(b"--\r\n"):
                break
            boundary_index = body.find(marker, boundary_index + len(marker))
        if boundary_index < 0:
            raise ValueError("Multipart closing boundary is missing.")
        sections.append(body[cursor:boundary_index])
        suffix_start = boundary_index + len(marker)
        if body.startswith(b"--\r\n", suffix_start):
            if suffix_start + 4 != len(body):
                raise ValueError("Multipart closing boundary is malformed.")
            if not sections or any(not section for section in sections):
                raise ValueError("Multipart parts must not be empty.")
            return tuple(sections)
        cursor = suffix_start + 2


def _part_identity(headers: dict[str, str]) -> tuple[str, bool]:
    disposition = headers.get("content-disposition")
    if disposition is None:
        raise ValueError("Multipart parts require Content-Disposition.")
    primary, parameters = _parse_parameterized_header(
        disposition,
        header_name="Content-Disposition",
    )
    if primary != "form-data" or "name" not in parameters:
        raise ValueError("Multipart Content-Disposition is malformed.")
    if set(parameters) - {"name", "filename"}:
        raise ValueError("Multipart Content-Disposition has unsupported parameters.")
    name = parameters["name"]
    if not name or name != name.strip() or not name.isascii():
        raise ValueError("Multipart field names must be non-empty, unpadded ASCII.")
    return name, "filename" in parameters or name == "request_file"


def _validate_part_content_type(headers: dict[str, str], *, is_file: bool) -> None:
    content_type = headers.get("content-type")
    if content_type is None:
        return
    primary, parameters = _parse_parameterized_header(
        content_type,
        header_name="Content-Type",
    )
    if primary.startswith("multipart/"):
        raise ValueError("Nested multipart content is not supported.")
    if is_file:
        if primary != "application/json" or parameters:
            raise ValueError("Uploaded files must use application/json.")
        return
    if primary != "text/plain" or (
        parameters and parameters != {"charset": "utf-8"}
    ):
        raise ValueError("Multipart revision uses an unsupported Content-Type.")


def _decode_revision(content: bytes) -> str:
    if content.startswith(b"\xef\xbb\xbf"):
        raise ValueError("Multipart revision must not contain a UTF-8 BOM.")
    try:
        revision = content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("Multipart revision must be valid UTF-8.") from error
    if not revision:
        raise ValueError("Multipart revision must be non-empty text.")
    return revision


def validate_frontend_request_page_v1(
    request: RequestDocumentV1,
    *,
    page: FrontendPageV1,
) -> None:
    """Enforces the exact imported/executed workflow accepted by one page."""

    if not isinstance(request, RequestDocumentV1):
        raise ValueError("request must be a RequestDocumentV1.")
    if type(page) is not str or page not in _PAGES:
        raise ValueError("page must be 'analyze' or 'review'.")
    if page == "analyze":
        if request.workflow is not WorkflowV1.POSITION_ANALYSIS:
            raise SkatMindWorkflowError(
                f"Workflow {request.workflow.value!r} is not supported on the Analyze page."
            )
        return
    if request.workflow is WorkflowV1.HISTORICAL_GAME:
        return
    if request.workflow is WorkflowV1.POSITION_ANALYSIS:
        if request.document.get("analysis_mode") == "post_game_review":
            return
        raise SkatMindWorkflowError(
            "Position Analysis requests on the Review page require exact "
            "analysis_mode='post_game_review'."
        )
    raise SkatMindWorkflowError(
        f"Workflow {request.workflow.value!r} is not supported on the Review page."
    )


def summarize_frontend_request_v1(request: RequestDocumentV1) -> ImportedRequestSummaryV1:
    if not isinstance(request, RequestDocumentV1):
        raise ValueError("request must be a RequestDocumentV1.")
    analysis_mode = request.document.get("analysis_mode")
    game_end_reason: object = request.document.get("game_end_reason")
    if request.workflow is WorkflowV1.HISTORICAL_GAME:
        historical = request.document.get("historical_game_input")
        if isinstance(historical, Mapping):
            game_end_reason = historical.get("game_end_reason")
    return ImportedRequestSummaryV1(
        workflow=request.workflow,
        analysis_mode=analysis_mode if type(analysis_mode) is str else None,
        game_end_reason=(game_end_reason if type(game_end_reason) is str else None),
    )


def parse_frontend_json_import_v1(
    body: bytes,
    *,
    content_type: str,
    page: FrontendPageV1,
) -> FrontendJsonImportV1:
    """Parses, publicly validates, and immutably retains one JSON upload."""

    if type(body) is not bytes:
        raise ValueError("Multipart body must be immutable bytes.")
    boundary = _multipart_boundary(content_type)
    sections = _multipart_sections(body, boundary)
    revision: str | None = None
    file_content: bytes | None = None

    for part in sections:
        if b"\r\n\r\n" not in part:
            raise ValueError("Multipart part header boundary is malformed.")
        raw_headers, content = part.split(b"\r\n\r\n", 1)
        headers = _part_headers(raw_headers)
        name, is_file = _part_identity(headers)
        _validate_part_content_type(headers, is_file=is_file)

        if is_file:
            if name != "request_file":
                raise ValueError("Multipart upload has an unsupported file field.")
            if file_content is not None:
                raise ValueError("Exactly one uploaded request file is allowed.")
            if len(content) > FRONTEND_JSON_MAX_FILE_BYTES:
                raise OverflowError("Uploaded JSON file is too large.")
            file_content = content
            continue

        if name != "revision":
            raise ValueError("Multipart upload has an unsupported text field.")
        if revision is not None:
            raise ValueError("Multipart revision must appear exactly once.")
        revision = _decode_revision(content)

    if revision is None:
        raise ValueError("Multipart revision must appear exactly once.")
    if file_content is None:
        raise ValueError("Exactly one uploaded request file is required.")

    document = decode_frontend_json_object_v1(file_content)
    request = parse_request(document)
    validate_frontend_request_page_v1(request, page=page)
    return FrontendJsonImportV1(
        revision=revision,
        request=request,
        summary=summarize_frontend_request_v1(request),
        request_json_bytes=build_frontend_request_json_bytes_v1(request),
    )
