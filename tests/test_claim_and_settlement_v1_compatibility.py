import tomllib
from pathlib import Path

import skat_ai
import skat_ai.api.v1 as api_v1
from scripts.validate_generated_outputs_schema import SCENARIOS
from skat_ai.api.v1 import WorkflowV1

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SESSION_EXAMPLE_NAMES = {
    "session_command_record_play.json",
    "session_correction_record_play.json",
    "session_create_live.json",
    "session_create_retrospective.json",
    "session_live_persistence.json",
    "session_retrospective_persistence.json",
}


def test_issue_182_preserves_package_api_cli_and_artifact_baselines() -> None:
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = pyproject["project"]

    assert project["version"] == skat_ai.__version__ == "0.16.0"
    assert project["requires-python"] == ">=3.13"
    assert project["scripts"] == {"skat-ai": "skat_ai.cli:main"}
    assert api_v1.PUBLIC_API_CONTRACT_VERSION == 1
    assert len(WorkflowV1) == 7
    assert "PARTY_WIDE_ALL_REMAINING_TRICKS_CLAIM_V1" not in api_v1.__all__
    assert len(tuple((PROJECT_ROOT / "schemas").glob("*.schema.json"))) == 63
    assert len(
        tuple(
            (PROJECT_ROOT / "src" / "skat_ai" / "schema_resources").glob(
                "*.schema.json"
            )
        )
    ) == 63
    assert {
        path.name
        for path in (PROJECT_ROOT / "examples").glob("session_*.json")
    } == SESSION_EXAMPLE_NAMES
    assert len(SCENARIOS) == 85
