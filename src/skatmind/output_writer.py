import json
from pathlib import Path
from typing import Any


def write_analysis_result_to_json(
    output_path: str,
    result: dict[str, Any],
) -> None:
    """
    Writes an analysis result to a JSON file.
    """
    path = Path(output_path)

    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(result, file, indent=2)
        file.write("\n")