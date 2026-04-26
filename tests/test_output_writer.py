import json

from skat_ai.output_writer import write_analysis_result_to_json


def test_write_analysis_result_to_json_creates_file(tmp_path) -> None:
    output_path = tmp_path / "analysis_result.json"
    result = {
        "recommendation": {
            "card": "SA",
            "reason": "Test reason.",
        }
    }

    write_analysis_result_to_json(
        output_path=str(output_path),
        result=result,
    )

    assert output_path.exists()


def test_write_analysis_result_to_json_writes_valid_json(tmp_path) -> None:
    output_path = tmp_path / "analysis_result.json"
    result = {
        "recommendation": {
            "card": "SA",
            "reason": "Test reason.",
        }
    }

    write_analysis_result_to_json(
        output_path=str(output_path),
        result=result,
    )

    with output_path.open("r", encoding="utf-8") as file:
        loaded_result = json.load(file)

    assert loaded_result == result


def test_write_analysis_result_to_json_creates_parent_directory(tmp_path) -> None:
    output_path = tmp_path / "nested" / "analysis_result.json"
    result = {
        "recommendation": {
            "card": "SA",
            "reason": "Test reason.",
        }
    }

    write_analysis_result_to_json(
        output_path=str(output_path),
        result=result,
    )

    assert output_path.exists()
    assert output_path.parent.exists()