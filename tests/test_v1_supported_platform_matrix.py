import copy
import json
import re
import tomllib
from pathlib import Path

import pytest

import skatmind
from scripts import validate_distribution_artifacts as distribution_validation
from scripts import validate_v1_supported_platform_matrix as matrix

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _valid_result() -> dict[str, object]:
    root_workflows = {
        workflow: {
            "artifact_names": [],
            "provenance": "complete",
            "status": "passed",
            "warning_count": 0,
        }
        for workflow in matrix.V1_ROOT_WORKFLOWS
    }
    cells = [
        {
            "dependency_lane": lane,
            "direct_dependency_versions": {
                "jsonschema": "4.23.0",
                "referencing": "0.31.0",
            },
            "installation_form": installation_form,
            "pip_check": "passed",
            "root_workflows": root_workflows,
            "semantic_digest": "0" * 64,
            "status": "passed",
            "surface_statuses": {
                surface: "passed" for surface in matrix.V1_SURFACE_FAMILIES
            },
        }
        for installation_form, lane in matrix.V1_MATRIX_CELLS
    ]
    return {
        "cells": cells,
        "direct_imports": ["jsonschema", "referencing"],
        "matrix_version": 1,
        "minimum_runtime_dependencies": list(matrix.V1_MINIMUM_RUNTIME_DEPENDENCIES),
        "platform": {
            "operating_system": "Windows 11",
            "operating_system_version": "10.0.26100",
            "platform_id": matrix.V1_SUPPORTED_PLATFORMS[0],
            "powershell_version": "5.1.26100.1",
            "python_implementation": "CPython",
            "python_version": "3.13.7",
        },
        "repository_mutation": "none",
        "result_state_evidence": {
            "normal_states": list(matrix.V1_NORMAL_RESULT_STATES),
            "timing_sensitive_timeout": "deterministic_repository_tests",
        },
        "runtime_dependencies": list(matrix.V1_RUNTIME_DEPENDENCIES),
        "semantic_parity": "passed",
        "status": "passed",
        "vocabularies": {
            "dependency_lanes": list(matrix.V1_DEPENDENCY_LANES),
            "installation_forms": list(matrix.V1_INSTALLATION_FORMS),
            "platforms": list(matrix.V1_SUPPORTED_PLATFORMS),
            "surface_families": list(matrix.V1_SURFACE_FAMILIES),
        },
    }


def test_matrix_constants_and_ordering_are_exact_and_private() -> None:
    assert matrix.V1_SUPPORTED_PLATFORM_MATRIX_VERSION == 1
    assert matrix.V1_SUPPORTED_PLATFORMS == (
        "windows_11_powershell_5_1_cpython_3_13",
        "ubuntu_github_actions_cpython_3_13",
    )
    assert matrix.V1_INSTALLATION_FORMS == ("source", "editable", "wheel", "sdist")
    assert matrix.V1_DEPENDENCY_LANES == ("resolved", "minimum_supported")
    assert matrix.V1_SURFACE_FAMILIES == (
        "package_metadata",
        "public_python_api",
        "installed_cli",
        "module_cli",
        "legacy_main",
        "session",
        "capture",
        "corpus",
        "package_resources",
        "provenance",
        "errors_and_exit_codes",
    )
    assert matrix.V1_MATRIX_CELLS == (
        ("source", "resolved"),
        ("editable", "resolved"),
        ("wheel", "resolved"),
        ("sdist", "resolved"),
        ("wheel", "minimum_supported"),
        ("sdist", "minimum_supported"),
    )
    assert skatmind.__all__ == ("api", "errors", "__version__")
    assert not any(name.startswith("V1_SUPPORTED_PLATFORM") for name in skatmind.__all__)


def test_runtime_dependency_declarations_are_exact() -> None:
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["dependencies"] == [
        "jsonschema>=4.23.0",
        "referencing>=0.31.0",
    ]
    assert matrix.declared_runtime_dependencies() == matrix.V1_RUNTIME_DEPENDENCIES
    assert distribution_validation.RUNTIME_DEPENDENCIES == matrix.V1_RUNTIME_DEPENDENCIES
    assert (
        distribution_validation.MINIMUM_RUNTIME_DEPENDENCIES
        == matrix.V1_MINIMUM_RUNTIME_DEPENDENCIES
    )


def test_direct_production_import_inventory_matches_package_metadata() -> None:
    inventory = matrix.validate_direct_import_inventory()

    assert set(inventory) == {"jsonschema", "referencing"}
    assert all(locations for locations in inventory.values())
    assert all(
        location.startswith("src/skatmind/")
        for locations in inventory.values()
        for location in locations
    )
    assert any("api/v1/schema_validation.py" in location for location in inventory["jsonschema"])
    assert any("api/v1/schema_validation.py" in location for location in inventory["referencing"])
    assert any(
        "api/v1/session/schema_validation.py" in location
        for location in inventory["referencing"]
    )


def test_resolved_editable_install_plan_and_pip_check_are_exact(tmp_path: Path) -> None:
    python = tmp_path / "python"
    source = tmp_path / "source"

    commands = distribution_validation._installation_commands(
        python,
        source,
        editable=True,
        minimum_dependencies=None,
    )

    assert commands == (
        (
            str(python),
            "-m",
            "pip",
            "install",
            "--no-input",
            "--editable",
            str(source),
        ),
        (str(python), "-m", "pip", "check"),
    )


@pytest.mark.parametrize("suffix", [".whl", ".tar.gz"])
def test_minimum_artifact_install_plan_uses_no_deps_and_exact_floors(
    tmp_path: Path,
    suffix: str,
) -> None:
    python = tmp_path / "python"
    artifact = tmp_path / f"skatmind{suffix}"

    commands = distribution_validation._installation_commands(
        python,
        artifact,
        editable=False,
        minimum_dependencies=matrix.V1_MINIMUM_RUNTIME_DEPENDENCIES,
    )

    assert commands == (
        (
            str(python),
            "-m",
            "pip",
            "install",
            "--no-input",
            "jsonschema==4.23.0",
            "referencing==0.31.0",
        ),
        (
            str(python),
            "-m",
            "pip",
            "install",
            "--no-input",
            "--no-deps",
            str(artifact),
        ),
        (str(python), "-m", "pip", "check"),
    )


def test_platform_detection_rejects_false_expected_platform(monkeypatch) -> None:
    monkeypatch.setattr(matrix.platform, "system", lambda: "Windows")
    monkeypatch.setattr(
        matrix,
        "_windows_platform_evidence",
        lambda: {
            "platform_id": matrix.V1_SUPPORTED_PLATFORMS[0],
            "operating_system": "Windows 11",
            "operating_system_version": "10.0.26100",
            "powershell_version": "5.1",
            "python_implementation": "CPython",
            "python_version": "3.13.7",
        },
    )

    assert matrix.detect_actual_platform()["platform_id"] == matrix.V1_SUPPORTED_PLATFORMS[0]
    with pytest.raises(matrix.V1SupportedPlatformMatrixError, match="does not match"):
        matrix.detect_actual_platform(matrix.V1_SUPPORTED_PLATFORMS[1])


def test_matrix_result_validation_and_json_are_deterministic() -> None:
    result = _valid_result()

    matrix.validate_matrix_result(result)
    first = matrix.serialize_matrix_result(result)
    second = matrix.serialize_matrix_result(copy.deepcopy(result))

    assert first == second
    assert first.endswith("\n")
    assert "NaN" not in first and "Infinity" not in first
    assert json.loads(first)["status"] == "passed"


def test_full_root_cli_smoke_reads_both_emitted_route_outputs() -> None:
    smoke = distribution_validation.SMOKE_PROGRAM

    assert 'for route_name in ("compatibility", "run"):' in smoke
    assert 'f"root-{invocation}-{route_name}-{workflow_name}.json"' in smoke
    assert 'f"root-{invocation}-{workflow_name}.json"' not in smoke


def test_matrix_cell_failure_diagnostic_is_bounded_actionable_and_sanitized(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    matrix_root = tmp_path / "matrix"
    private_document = '{"private":"' + ("x" * 8_000) + '"}'
    error = distribution_validation.DistributionValidationError(
        "Command failed with exit code 1: "
        f"{matrix_root / 'venv-source-resolved' / 'bin' / 'python'} -I "
        f"{matrix_root / 'consumer-source-resolved' / 'installed-smoke.py'} "
        "?token=private-token\n"
        "ACCESS_TOKEN=private-environment-token\n"
        f"stdout:\n{private_document}\n"
        "stderr:\nTraceback (most recent call last):\n"
        f'  File "{matrix_root / "consumer-source-resolved" / "installed-smoke.py"}", '
        "line 1, in <module>\n"
        "Cookie: skatmind_capture_token=private-cookie\n"
        "    raise AssertionError('app-distribution-token')\n"
        "AssertionError: app-distribution-token"
    )
    message = matrix._matrix_cell_failure_message(
        error,
        installation_form="source",
        dependency_lane="resolved",
        temporary_root=matrix_root,
    )
    monkeypatch.setattr(
        matrix,
        "validate_v1_supported_platform_matrix",
        lambda **_kwargs: (_ for _ in ()).throw(
            matrix.V1SupportedPlatformMatrixError(message)
        ),
    )

    assert matrix.main([]) == 1
    captured = capsys.readouterr()

    assert captured.out == ""
    assert "installation_form=source; dependency_lane=resolved" in captured.err
    assert "DistributionValidationError: Command failed with exit code 1:" in captured.err
    assert "<matrix-root>" in captured.err
    assert "installed-smoke.py" in captured.err
    assert "child stdout excerpt:" in captured.err
    assert "<structured child output redacted>" in captured.err
    assert "child stderr excerpt:" in captured.err
    assert "AssertionError: <redacted>" in captured.err
    assert str(matrix_root) not in captured.err
    assert "private-token" not in captured.err
    assert "private-environment-token" not in captured.err
    assert "private-cookie" not in captured.err
    assert "app-distribution-token" not in captured.err
    assert len(captured.err) < 9_000
    assert re.search(r"V1 supported-platform matrix validation failed:", captured.err)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("consumer_path", "not-retained"),
        ("access_token", "not-retained"),
        ("hostname", "not-retained"),
        ("started_timestamp", "not-retained"),
        ("elapsed_time", 1),
    ],
)
def test_matrix_result_rejects_secret_path_and_time_fields(key: str, value: object) -> None:
    result = _valid_result()
    result[key] = value

    with pytest.raises(matrix.V1SupportedPlatformMatrixError, match="forbidden"):
        matrix.validate_matrix_result(result)


def test_repository_snapshot_detects_content_addition_and_removal(tmp_path: Path) -> None:
    source = tmp_path / "source.py"
    source.write_text("value = 1\n", encoding="utf-8")
    first = matrix.repository_snapshot(tmp_path)
    source.write_text("value = 2\n", encoding="utf-8")
    second = matrix.repository_snapshot(tmp_path)
    generated = tmp_path / "dist" / "artifact.whl"
    generated.parent.mkdir()
    generated.write_bytes(b"artifact")
    third = matrix.repository_snapshot(tmp_path)
    generated.unlink()

    assert first != second
    assert second != third
    assert matrix.repository_snapshot(tmp_path) == second


def test_ci_preserves_check_job_and_adds_separate_matrix_job() -> None:
    workflow = (PROJECT_ROOT / ".github" / "workflows" / "check.yml").read_text(
        encoding="utf-8"
    )
    check_job, matrix_job = workflow.split("  v1-supported-platform-matrix:", 1)

    assert "  check:" in check_job
    assert "runs-on: ubuntu-latest" in check_job
    assert "python -m pytest" in check_job
    assert "scripts/validate_distribution_artifacts.py" in check_job
    assert "runs-on: ubuntu-latest" in matrix_job
    assert 'python-version: "3.13"' in matrix_job
    assert "scripts/validate_v1_supported_platform_matrix.py" in matrix_job
    assert "ubuntu_github_actions_cpython_3_13" in matrix_job
    assert "pytest" not in matrix_job
    assert "upload-artifact" not in matrix_job
    assert "publish" not in matrix_job.lower()
    assert "pull_request:" in workflow and "push:" in workflow


def test_issue_206_changes_no_package_api_schema_or_scenario_baseline() -> None:
    from scripts.validate_generated_outputs_schema import SCENARIOS
    from skatmind.api.v1 import PUBLIC_API_CONTRACT_VERSION, WorkflowV1

    schema_names = sorted((PROJECT_ROOT / "schemas").glob("*.schema.json"))
    packaged_schema_names = sorted(
        (PROJECT_ROOT / "src" / "skatmind" / "schema_resources").glob("*.schema.json")
    )
    session_examples = sorted((PROJECT_ROOT / "examples").glob("session_*.json"))
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["version"] == "0.17.0"
    assert pyproject["project"]["requires-python"] == ">=3.13"
    assert pyproject["project"]["license"] == "AGPL-3.0-only"
    assert pyproject["project"]["scripts"] == {"skatmind": "skatmind.cli:main"}
    assert PUBLIC_API_CONTRACT_VERSION == 1
    assert len(WorkflowV1) == 7
    assert len(schema_names) == len(packaged_schema_names) == 71
    assert len(session_examples) == 6
    assert len(SCENARIOS) == 98
    assert len(distribution_validation.CORPUS_RESOURCE_NAMES) == 3


def test_runner_contains_no_publication_operation() -> None:
    source = (PROJECT_ROOT / "scripts" / "validate_v1_supported_platform_matrix.py").read_text(
        encoding="utf-8"
    )

    for forbidden in ("twine", "pypi", "gh release", "git push", "upload-artifact"):
        assert forbidden not in source.lower()
