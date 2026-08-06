from __future__ import annotations

import argparse
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
AUTHORITATIVE_SCHEMA_DIRECTORY = PROJECT_ROOT / "schemas"
PACKAGED_SCHEMA_DIRECTORY = PROJECT_ROOT / "src" / "skat_ai" / "schema_resources"


def _schema_files(directory: Path) -> dict[str, Path]:
    return {
        path.name: path
        for path in sorted(directory.glob("*.schema.json"), key=lambda path: path.name)
        if path.is_file()
    }


def schema_parity_errors(source_directory: Path, packaged_directory: Path) -> tuple[str, ...]:
    source_files = _schema_files(source_directory)
    packaged_files = _schema_files(packaged_directory)
    errors: list[str] = []

    for name in sorted(source_files.keys() - packaged_files.keys()):
        errors.append(f"Missing packaged schema: {name}")
    for name in sorted(packaged_files.keys() - source_files.keys()):
        errors.append(f"Unexpected packaged schema: {name}")
    for name in sorted(source_files.keys() & packaged_files.keys()):
        if source_files[name].read_bytes() != packaged_files[name].read_bytes():
            errors.append(f"Packaged schema differs: {name}")

    return tuple(errors)


def sync_schema_directories(source_directory: Path, packaged_directory: Path) -> None:
    source_files = _schema_files(source_directory)
    packaged_files = _schema_files(packaged_directory)
    packaged_directory.mkdir(parents=True, exist_ok=True)

    for name in sorted(packaged_files.keys() - source_files.keys()):
        packaged_files[name].unlink()
    for name, source_path in source_files.items():
        shutil.copyfile(source_path, packaged_directory / name)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Synchronize packaged JSON Schemas with the authoritative repository schemas."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check exact filename and byte parity without modifying files.",
    )
    arguments = parser.parse_args(argv)

    if arguments.check:
        errors = schema_parity_errors(
            AUTHORITATIVE_SCHEMA_DIRECTORY,
            PACKAGED_SCHEMA_DIRECTORY,
        )
        if errors:
            print("Packaged schema parity check failed:")
            for error in errors:
                print(f"- {error}")
            return 1
        print("Packaged schemas match the authoritative repository schemas.")
        return 0

    sync_schema_directories(
        AUTHORITATIVE_SCHEMA_DIRECTORY,
        PACKAGED_SCHEMA_DIRECTORY,
    )
    print("Packaged schemas synchronized from the authoritative repository schemas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
