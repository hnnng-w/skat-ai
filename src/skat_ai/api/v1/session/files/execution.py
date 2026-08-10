from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

from skat_ai.api.v1.session.files.contracts import (
    SessionFileApiOptionsV1,
    SessionFileApiResultV1,
)
from skat_ai.api.v1.session.files.schema_validation import (
    validate_session_file_result_document,
)
from skat_ai.errors import SkatAIError, SkatAISerializationError, SkatAIValidationError
from skat_ai.session_persistence import (
    load_session_persistence_file_v1,
    save_session_persistence_file_v1,
)
from skat_ai.session_persistence_contracts import SessionPersistenceDocumentV1

_DEFAULT_OPTIONS = SessionFileApiOptionsV1()


def _at_public_boundary[T](operation: Callable[[], T]) -> T:
    try:
        return operation()
    except SkatAIError:
        raise
    except (TypeError, ValueError) as error:
        raise SkatAIValidationError(str(error)) from error


def _require_options(options: object) -> SessionFileApiOptionsV1:
    if type(options) is not SessionFileApiOptionsV1:
        raise SkatAIValidationError(
            "options must be a SessionFileApiOptionsV1.",
            path="options",
        )
    return options


def _result(
    *,
    operation: str,
    value: object,
    options: SessionFileApiOptionsV1,
) -> SessionFileApiResultV1:
    result = SessionFileApiResultV1(operation=operation, value=value)
    if options.validate_output:
        validate_session_file_result_document(result.to_dict())
    return result


def save_session_file(
    file_path: str | os.PathLike[str],
    document: SessionPersistenceDocumentV1,
    *,
    expected_content_fingerprint: str | None,
    options: SessionFileApiOptionsV1 = _DEFAULT_OPTIONS,
) -> SessionFileApiResultV1:
    """Saves one Session file through the existing optimistic persistence boundary."""

    def operation() -> SessionFileApiResultV1:
        validated_options = _require_options(options)
        value = save_session_persistence_file_v1(
            file_path,
            document,
            expected_content_fingerprint=expected_content_fingerprint,
        )
        return _result(
            operation="save",
            value=value,
            options=validated_options,
        )

    return _at_public_boundary(operation)


def load_session_file(
    file_path: str | os.PathLike[str],
    *,
    options: SessionFileApiOptionsV1 = _DEFAULT_OPTIONS,
) -> SessionFileApiResultV1:
    """Loads and strictly resumes one Session file."""

    def operation() -> SessionFileApiResultV1:
        validated_options = _require_options(options)
        value = load_session_persistence_file_v1(file_path)
        return _result(
            operation="load",
            value=value,
            options=validated_options,
        )

    return _at_public_boundary(operation)


def serialize_session_file_result(
    result: SessionFileApiResultV1,
) -> dict[str, object]:
    """Returns one fresh mutable Session file Result representation."""
    if type(result) is not SessionFileApiResultV1:
        raise SkatAISerializationError(
            "result must be a SessionFileApiResultV1.",
            path="result",
        )
    serialized: dict[str, Any] = result.to_dict()
    return serialized
