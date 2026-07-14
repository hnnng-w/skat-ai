from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = PROJECT_ROOT / "schemas" / "input.schema.json"
HISTORICAL_SCHEMA_PATH = PROJECT_ROOT / "schemas" / "historical_game.schema.json"
ROOT_INPUT_PATH = PROJECT_ROOT / "input_position.json"
EXAMPLES_DIR = PROJECT_ROOT / "examples"


def load_json_file(file_path: Path) -> dict:
    """
    Loads a JSON file.
    """
    with file_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def get_example_files() -> list[Path]:
    """
    Returns all example JSON files.
    """
    return sorted(EXAMPLES_DIR.glob("*.json"))


def get_schema_input_files() -> list[Path]:
    """
    Returns all input files covered by input schema validation.
    """
    return [ROOT_INPUT_PATH, *get_example_files()]


def format_validation_error(file_path: Path, error) -> str:
    """
    Formats a JSON schema validation error.
    """
    location = ".".join(str(part) for part in error.absolute_path)

    if not location:
        location = "<root>"

    return f"{file_path}: {location}: {error.message}"


def validate_example_files() -> list[str]:
    """
    Validates all example JSON files against the input JSON schema.
    """
    schema = load_json_file(SCHEMA_PATH)
    historical_schema = load_json_file(HISTORICAL_SCHEMA_PATH)
    registry = Registry().with_resource(
        historical_schema["$id"], Resource.from_contents(historical_schema)
    )
    validator = Draft202012Validator(schema, registry=registry)

    errors = []

    for example_file in get_schema_input_files():
        data = load_json_file(example_file)

        for error in sorted(
            validator.iter_errors(data),
            key=lambda validation_error: list(validation_error.absolute_path),
        ):
            errors.append(format_validation_error(example_file, error))

    return errors


def main() -> int:
    """
    Runs example schema validation.
    """
    errors = validate_example_files()

    if errors:
        print("JSON schema validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("All root input and example JSON files match schemas/input.schema.json.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
