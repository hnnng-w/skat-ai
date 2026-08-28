from __future__ import annotations

import json
from pathlib import Path

from skatmind.errors import SkatMindValidationError


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise SkatMindValidationError(
                f"Duplicate JSON object key {key!r} is not allowed.",
                path="",
            )
        result[key] = value
    return result


def _reject_non_finite_constant(value: str) -> object:
    raise SkatMindValidationError(
        f"Non-finite JSON number {value!r} is not allowed.",
        path="",
    )


def load_strict_json_object(file_path: str) -> dict[str, object]:
    path = Path(file_path)
    try:
        raw = path.read_bytes()
    except FileNotFoundError as error:
        raise FileNotFoundError(f"Input file not found: {file_path}") from error
    if raw.startswith(b"\xef\xbb\xbf"):
        raise SkatMindValidationError("Input JSON must use UTF-8 without a BOM.", path="")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise SkatMindValidationError("Input file is not valid UTF-8.", path="") from error
    try:
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_non_finite_constant,
        )
    except SkatMindValidationError:
        raise
    except json.JSONDecodeError as error:
        raise SkatMindValidationError(
            f"Input file is not valid JSON: {error.msg}.",
            path="",
        ) from error
    if not isinstance(value, dict):
        raise SkatMindValidationError("Input JSON root must be an object.", path="")
    return value
