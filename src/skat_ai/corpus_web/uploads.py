from __future__ import annotations

import json
import math
import os
import re
import tempfile
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from email.message import Message
from types import MappingProxyType

from .contracts import LEARNING_CORPUS_WEB_MAX_REQUEST_BYTES

_BOUNDARY_CHARACTERS = frozenset(
    "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'()+_,-./:=?"
)
_HEADER_NAME = re.compile(rb"^[!#$%&'*+.^_`|~0-9A-Za-z-]+$")
_UPLOAD_FILE_FIELDS = frozenset({"workspace_file", "report_source_file"})


def _reject_duplicate_json_keys(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
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


def decode_learning_corpus_uploaded_json_v1(
    raw_bytes: bytes,
) -> Mapping[str, object]:
    """Strictly decodes one uploaded finite UTF-8 JSON object without a BOM."""
    if type(raw_bytes) is not bytes:
        raise ValueError("Uploaded JSON must be immutable bytes.")
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


def _header_parameters(value: str, *, header_name: str) -> tuple[str, dict[str, str]]:
    message = Message()
    message[header_name] = value
    parameters = message.get_params(header=header_name, unquote=True)
    if not parameters:
        raise ValueError(f"Malformed {header_name} header.")
    primary = parameters[0][0].lower()
    result: dict[str, str] = {}
    for name, item in parameters[1:]:
        normalized = name.lower()
        if normalized in result or not isinstance(item, str):
            raise ValueError(f"Malformed {header_name} parameters.")
        result[normalized] = item
    return primary, result


def _multipart_boundary(content_type: str) -> bytes:
    primary, parameters = _header_parameters(
        content_type,
        header_name="content-type",
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
            value = raw_value.decode("latin-1").strip()
        except UnicodeDecodeError as error:
            raise ValueError("Multipart part headers must be ASCII.") from error
        if name in headers:
            raise ValueError("Multipart part headers must not repeat.")
        headers[name] = value
    unsupported = set(headers) - {"content-disposition", "content-type"}
    if unsupported:
        if "content-transfer-encoding" in unsupported:
            raise ValueError("Multipart transfer encodings are not supported.")
        raise ValueError("Multipart part contains unsupported headers.")
    return headers


@dataclass(frozen=True, slots=True, kw_only=True)
class LearningCorpusMultipartUploadV1:
    fields: Mapping[str, str]
    file_field: str
    file_content: bytes = field(repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.fields, Mapping) or any(
            not isinstance(name, str) or not isinstance(value, str)
            for name, value in self.fields.items()
        ):
            raise ValueError("Multipart fields must contain text values.")
        if self.file_field not in _UPLOAD_FILE_FIELDS:
            raise ValueError("Multipart upload has an unsupported file field.")
        if type(self.file_content) is not bytes:
            raise ValueError("Multipart file content must be immutable bytes.")
        object.__setattr__(self, "fields", MappingProxyType(dict(self.fields)))

    @contextmanager
    def temporary_file(self) -> Iterator[os.PathLike[str]]:
        """Writes exact bytes to one server-owned path and always removes it."""
        descriptor, raw_path = tempfile.mkstemp(
            prefix="skat-ai-corpus-upload-",
            suffix=".json",
        )
        try:
            with os.fdopen(descriptor, "wb") as target:
                target.write(self.file_content)
                target.flush()
                os.fsync(target.fileno())
            yield os.fspath(raw_path)
        finally:
            try:
                os.unlink(raw_path)
            except FileNotFoundError:
                pass


def parse_learning_corpus_multipart_upload_v1(
    body: bytes,
    *,
    content_type: str,
) -> LearningCorpusMultipartUploadV1:
    """Parses one strict multipart request with one file and unique text fields."""
    if type(body) is not bytes:
        raise ValueError("Multipart body must be immutable bytes.")
    if len(body) > LEARNING_CORPUS_WEB_MAX_REQUEST_BYTES:
        raise OverflowError("Request body is too large.")
    boundary = _multipart_boundary(content_type)
    sections = _multipart_sections(body, boundary)

    fields: dict[str, str] = {}
    file_field: str | None = None
    file_content: bytes | None = None
    for part in sections:
        if b"\r\n\r\n" not in part:
            raise ValueError("Multipart part header boundary is malformed.")
        raw_headers, content = part.split(b"\r\n\r\n", 1)
        headers = _part_headers(raw_headers)
        disposition = headers.get("content-disposition")
        if disposition is None:
            raise ValueError("Multipart parts require Content-Disposition.")
        primary, parameters = _header_parameters(
            disposition,
            header_name="content-disposition",
        )
        if primary != "form-data" or "name" not in parameters:
            raise ValueError("Multipart Content-Disposition is malformed.")
        if set(parameters) - {"name", "filename"}:
            raise ValueError("Multipart Content-Disposition has unsupported parameters.")
        name = parameters["name"]
        if not name or name != name.strip() or not name.isascii():
            raise ValueError("Multipart field names must be non-empty, unpadded ASCII.")
        part_content_type = headers.get("content-type")
        if part_content_type is not None:
            media_type = part_content_type.split(";", 1)[0].strip().lower()
            if media_type.startswith("multipart/"):
                raise ValueError("Nested multipart content is not supported.")

        is_file = "filename" in parameters or name in _UPLOAD_FILE_FIELDS
        if is_file:
            if name not in _UPLOAD_FILE_FIELDS:
                raise ValueError("Multipart upload has an unsupported file field.")
            if file_field is not None:
                raise ValueError("Exactly one uploaded file is allowed.")
            if part_content_type is not None and media_type != "application/json":
                raise ValueError("Uploaded files must use application/json.")
            file_field = name
            file_content = content
            continue

        if part_content_type is not None and media_type not in {
            "text/plain",
            "application/octet-stream",
        }:
            raise ValueError("Multipart text fields use an unsupported Content-Type.")
        if name in fields:
            raise ValueError(f"Duplicate multipart field {name!r} is not allowed.")
        if content.startswith(b"\xef\xbb\xbf"):
            raise ValueError("Multipart text fields must not contain a UTF-8 BOM.")
        try:
            fields[name] = content.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValueError("Multipart text fields must be valid UTF-8.") from error

    if file_field is None or file_content is None:
        raise ValueError("Exactly one uploaded file is required.")
    decode_learning_corpus_uploaded_json_v1(file_content)
    return LearningCorpusMultipartUploadV1(
        fields=fields,
        file_field=file_field,
        file_content=file_content,
    )


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
