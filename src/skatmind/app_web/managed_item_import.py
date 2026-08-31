from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from .json_transfer import (
    _multipart_boundary,
    _multipart_sections,
    _part_headers,
    _part_identity,
    _validate_part_content_type,
)
from .managed_item_contracts import MANAGED_ITEM_MAX_IMPORT_BYTES


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON object key {key!r} is not allowed.")
        result[key] = value
    return result


def _reject_non_finite_constant(value: str) -> object:
    raise ValueError(f"Non-finite JSON number {value!r} is not allowed.")


def _finite_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError(f"Non-finite JSON number {value!r} is not allowed.")
    return parsed


def decode_managed_item_json_object_v1(raw_bytes: bytes) -> dict[str, object]:
    if type(raw_bytes) is not bytes:
        raise ValueError("Uploaded JSON must be immutable bytes.")
    if len(raw_bytes) > MANAGED_ITEM_MAX_IMPORT_BYTES:
        raise OverflowError("Uploaded JSON file is too large.")
    if raw_bytes.startswith(b"\xef\xbb\xbf"):
        raise ValueError("Uploaded JSON must not contain a UTF-8 BOM.")
    try:
        value = json.loads(
            raw_bytes.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_non_finite_constant,
            parse_float=_finite_float,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("Uploaded file must contain valid UTF-8 JSON.") from error
    if not isinstance(value, dict):
        raise ValueError("Uploaded JSON root must be an object.")
    return value


@dataclass(frozen=True, slots=True, kw_only=True)
class ManagedItemJsonUploadV1:
    fields: Mapping[str, str]
    file_field: str
    file_content: bytes = field(repr=False)
    document: Mapping[str, object] = field(repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.fields, Mapping) or any(
            type(name) is not str or type(value) is not str
            for name, value in self.fields.items()
        ):
            raise ValueError("fields must contain text names and values.")
        if type(self.file_field) is not str or not self.file_field:
            raise ValueError("file_field must be non-empty text.")
        if type(self.file_content) is not bytes:
            raise ValueError("file_content must be immutable bytes.")
        if not isinstance(self.document, Mapping):
            raise ValueError("document must be a JSON object.")
        object.__setattr__(self, "fields", MappingProxyType(dict(self.fields)))
        object.__setattr__(self, "document", MappingProxyType(dict(self.document)))


def parse_managed_item_json_upload_v1(
    body: bytes,
    *,
    content_type: str,
    expected_file_field: str,
    expected_text_fields: frozenset[str] = frozenset(),
) -> ManagedItemJsonUploadV1:
    """Parses one strict in-memory upload while ignoring caller filename authority."""

    if type(body) is not bytes:
        raise ValueError("Multipart body must be immutable bytes.")
    boundary = _multipart_boundary(content_type)
    sections = _multipart_sections(body, boundary)
    fields: dict[str, str] = {}
    file_content: bytes | None = None
    for part in sections:
        if b"\r\n\r\n" not in part:
            raise ValueError("Multipart part header boundary is malformed.")
        raw_headers, content = part.split(b"\r\n\r\n", 1)
        headers = _part_headers(raw_headers)
        name, is_file = _part_identity(headers)
        _validate_part_content_type(headers, is_file=is_file)
        if is_file:
            if name != expected_file_field or file_content is not None:
                raise ValueError("Exactly one supported uploaded file is required.")
            if len(content) > MANAGED_ITEM_MAX_IMPORT_BYTES:
                raise OverflowError("Uploaded JSON file is too large.")
            file_content = content
            continue
        if name not in expected_text_fields or name in fields:
            raise ValueError("Multipart upload has an unsupported or duplicate text field.")
        if content.startswith(b"\xef\xbb\xbf"):
            raise ValueError("Multipart text fields must not contain a UTF-8 BOM.")
        try:
            fields[name] = content.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValueError("Multipart text fields must be valid UTF-8.") from error
    if file_content is None:
        raise ValueError("Exactly one uploaded file is required.")
    if set(fields) != set(expected_text_fields):
        raise ValueError("Multipart upload is missing required text fields.")
    return ManagedItemJsonUploadV1(
        fields=fields,
        file_field=expected_file_field,
        file_content=file_content,
        document=decode_managed_item_json_object_v1(file_content),
    )
