from collections.abc import Mapping

from skat_ai.api.v1.schema_validation import _validator_for
from skat_ai.errors import SkatAISchemaError

_SESSION_SCHEMA_NAME = "session.schema.json"
_SESSION_SCHEMA_ID = "https://example.local/skat-ai/session.schema.json"


def _validate_session_definition(document: object, definition: str) -> None:
    from referencing.exceptions import Unresolvable

    from skat_ai.api.v1.schema_validation import _error_sort_key, _json_pointer

    validator = _validator_for(_SESSION_SCHEMA_NAME).evolve(
        schema={"$ref": f"{_SESSION_SCHEMA_ID}#/$defs/{definition}"}
    )
    try:
        errors = sorted(validator.iter_errors(document), key=_error_sort_key)
    except Unresolvable as error:
        from skat_ai.errors import SkatAIResourceError

        raise SkatAIResourceError(
            f"Packaged Session schema resource is unavailable: {error}"
        ) from error
    if errors:
        error = errors[0]
        raise SkatAISchemaError(
            error.message,
            path=_json_pointer(error.absolute_path),
        )


def validate_session_command_document(document: object) -> None:
    _validate_session_definition(document, "session_command")


def validate_session_create_document(document: object) -> None:
    _validate_session_definition(document, "session_create_input")


def validate_session_correction_document(document: object) -> None:
    _validate_session_definition(document, "command_correction")


def validate_session_persistence_document(document: Mapping[str, object]) -> None:
    _validate_session_definition(document, "session_persistence_document")


def validate_session_result_document(document: object) -> None:
    _validate_session_definition(document, "session_api_result")
