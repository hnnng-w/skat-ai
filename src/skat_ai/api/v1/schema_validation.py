import json
from collections.abc import Iterable
from functools import lru_cache
from pathlib import Path
from typing import Any

from skat_ai.errors import (
    SkatAIInvariantError,
    SkatAIResourceError,
    SkatAISchemaError,
)

_INPUT_SCHEMA_NAME = "input.schema.json"
_OUTPUT_SCHEMA_NAME = "output.schema.json"


def _schema_directory() -> Path:
    return Path(__file__).parents[4] / "schemas"


def _read_schema(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as schema_file:
            schema = json.load(schema_file)
    except OSError as error:
        raise SkatAIResourceError(str(error)) from error
    except json.JSONDecodeError as error:
        raise SkatAIInvariantError(
            f"Repository schema {path.name!r} is not valid JSON: {error}."
        ) from error
    except UnicodeDecodeError as error:
        raise SkatAIInvariantError(
            f"Repository schema {path.name!r} is not valid UTF-8: {error}."
        ) from error
    if not isinstance(schema, dict):
        raise SkatAIInvariantError(
            f"Repository schema {path.name!r} must contain a JSON object."
        )
    return schema


def _reject_schema_retrieval(uri: str):
    from referencing.exceptions import NoSuchResource

    raise NoSuchResource(ref=uri)


@lru_cache(maxsize=2)
def _validator_for(schema_name: str):
    from jsonschema import Draft202012Validator, FormatChecker
    from jsonschema.exceptions import SchemaError
    from referencing import Registry, Resource
    from referencing.exceptions import CannotDetermineSpecification
    from referencing.jsonschema import UnknownDialect

    schema_directory = _schema_directory()
    root_path = schema_directory / schema_name
    schemas: list[tuple[Path, dict[str, Any]]] = []
    try:
        schema_paths = sorted(schema_directory.glob("*.schema.json"))
    except OSError as error:
        raise SkatAIResourceError(str(error)) from error
    if root_path not in schema_paths:
        _read_schema(root_path)
    for path in schema_paths:
        schemas.append((path, _read_schema(path)))

    resources = []
    schema_ids: set[str] = set()
    root_schema: dict[str, Any] | None = None
    for path, schema in schemas:
        try:
            Draft202012Validator.check_schema(schema)
        except SchemaError as error:
            raise SkatAIInvariantError(
                f"Repository schema {path.name!r} is invalid: {error.message}"
            ) from error
        schema_id = schema.get("$id")
        if not isinstance(schema_id, str) or not schema_id:
            raise SkatAIInvariantError(
                f"Repository schema {path.name!r} requires a non-empty $id."
            )
        if schema_id in schema_ids:
            raise SkatAIInvariantError(
                f"Repository schema $id {schema_id!r} is duplicated."
            )
        schema_ids.add(schema_id)
        try:
            resources.append((schema_id, Resource.from_contents(schema)))
        except (CannotDetermineSpecification, UnknownDialect) as error:
            raise SkatAIInvariantError(
                f"Repository schema {path.name!r} has no supported specification."
            ) from error
        if path == root_path:
            root_schema = schema

    if root_schema is None:
        raise SkatAIResourceError(f"Schema resource not found: {root_path}")
    registry = Registry(retrieve=_reject_schema_retrieval).with_resources(resources)
    format_checker = FormatChecker() if schema_name == _INPUT_SCHEMA_NAME else None
    return Draft202012Validator(
        root_schema,
        registry=registry,
        format_checker=format_checker,
    )


def _sortable_path(path: Iterable[object]) -> tuple[tuple[int, int | str], ...]:
    return tuple(
        (0, token) if type(token) is int else (1, str(token))
        for token in path
    )


def _error_sort_key(error) -> tuple[object, ...]:
    return (
        _sortable_path(error.absolute_path),
        _sortable_path(error.absolute_schema_path),
        error.message,
    )


def _json_pointer(path: Iterable[object]) -> str:
    tokens = (
        str(token).replace("~", "~0").replace("/", "~1")
        for token in path
    )
    return "".join(f"/{token}" for token in tokens)


def _validate_document(document: object, *, schema_name: str) -> None:
    from referencing.exceptions import Unresolvable

    validator = _validator_for(schema_name)
    try:
        errors = sorted(validator.iter_errors(document), key=_error_sort_key)
    except Unresolvable as error:
        raise SkatAIResourceError(
            f"Repository schema resource is unavailable: {error}"
        ) from error
    if errors:
        error = errors[0]
        raise SkatAISchemaError(
            error.message,
            path=_json_pointer(error.absolute_path),
        )


def validate_input_document(document: object) -> None:
    _validate_document(document, schema_name=_INPUT_SCHEMA_NAME)


def validate_output_document(document: object) -> None:
    _validate_document(document, schema_name=_OUTPUT_SCHEMA_NAME)
