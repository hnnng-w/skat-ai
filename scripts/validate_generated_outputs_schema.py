from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = PROJECT_ROOT / "schemas" / "output.schema.json"

EXAMPLE_INPUTS = [
    PROJECT_ROOT / "examples" / "grand_second_position.json",
    PROJECT_ROOT / "examples" / "grand_complete_declarer_win.json",
    PROJECT_ROOT / "examples" / "grand_complete_declarer_loss.json",
    PROJECT_ROOT / "examples" / "grand_list_performance_input.json",
    PROJECT_ROOT / "examples" / "grand_overbid_declarer_card_points_win.json",
]


def load_json_file(file_path: Path) -> dict[str, Any]:
    """
    Loads a JSON file.
    """
    with file_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def format_validation_error(file_path: Path, error) -> str:
    """
    Formats a JSON schema validation error.
    """
    location = ".".join(str(part) for part in error.absolute_path)

    if not location:
        location = "<root>"

    return f"{file_path}: {location}: {error.message}"


def run_analysis(input_path: Path, output_path: Path) -> None:
    """
    Runs the CLI analysis for one example input.
    """
    command = [
        sys.executable,
        str(PROJECT_ROOT / "main.py"),
        "--input",
        str(input_path),
        "--output",
        str(output_path),
        "--samples",
        "20",
        "--seed",
        "42",
    ]

    subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


def validate_output_file(
    validator: Draft202012Validator,
    output_path: Path,
) -> list[str]:
    """
    Validates one generated output file against the output schema.
    """
    data = load_json_file(output_path)

    return [
        format_validation_error(output_path, error)
        for error in sorted(
            validator.iter_errors(data),
            key=lambda validation_error: list(validation_error.absolute_path),
        )
    ]


def validate_generated_outputs() -> list[str]:
    """
    Generates selected example outputs and validates them against the output schema.
    """
    schema = load_json_file(SCHEMA_PATH)
    validator = Draft202012Validator(schema)
    errors = []

    with tempfile.TemporaryDirectory() as temporary_directory:
        temporary_path = Path(temporary_directory)

        for input_path in EXAMPLE_INPUTS:
            output_path = temporary_path / f"{input_path.stem}.output.json"

            run_analysis(
                input_path=input_path,
                output_path=output_path,
            )

            errors.extend(
                validate_output_file(
                    validator=validator,
                    output_path=output_path,
                )
            )

    return errors


def main() -> int:
    """
    Runs generated-output schema validation.
    """
    errors = validate_generated_outputs()

    if errors:
        print("Generated output JSON schema validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Generated outputs match schemas/output.schema.json.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
