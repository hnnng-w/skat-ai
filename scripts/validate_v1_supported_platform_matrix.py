from __future__ import annotations

import argparse
import ast
import hashlib
import importlib
import json
import math
import os
import platform
import re
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

try:
    distribution_validation = importlib.import_module(
        "scripts.validate_distribution_artifacts"
    )
except ModuleNotFoundError:
    distribution_validation = importlib.import_module(
        "validate_distribution_artifacts"
    )

PROJECT_ROOT = Path(__file__).resolve().parents[1]
V1_SUPPORTED_PLATFORM_MATRIX_VERSION = 1
V1_SUPPORTED_PLATFORMS = (
    "windows_11_powershell_5_1_cpython_3_13",
    "ubuntu_github_actions_cpython_3_13",
)
V1_INSTALLATION_FORMS = (
    "source",
    "editable",
    "wheel",
    "sdist",
)
V1_DEPENDENCY_LANES = (
    "resolved",
    "minimum_supported",
)
V1_SURFACE_FAMILIES = (
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
V1_RUNTIME_DEPENDENCIES = (
    "jsonschema>=4.23.0",
    "referencing>=0.31.0",
)
V1_MINIMUM_RUNTIME_DEPENDENCIES = (
    "jsonschema==4.23.0",
    "referencing==0.31.0",
)
V1_RUNTIME_DISTRIBUTION_IMPORT_ROOTS = {
    "jsonschema": ("jsonschema",),
    "referencing": ("referencing",),
}
V1_MATRIX_CELLS = (
    ("source", "resolved"),
    ("editable", "resolved"),
    ("wheel", "resolved"),
    ("sdist", "resolved"),
    ("wheel", "minimum_supported"),
    ("sdist", "minimum_supported"),
)
V1_ROOT_WORKFLOWS = (
    "position_analysis",
    "historical_game",
    "training_dataset",
    "training_dataset_preparation",
    "opponent_statistics",
    "fixed_three_player_historical_list",
    "fixed_three_player_historical_list_comparison",
)
V1_NORMAL_RESULT_STATES = (
    "complete",
    "partial",
    "timeout",
    "unavailable",
    "final",
    "lot_required",
    "not_assessable",
)
_FORBIDDEN_EVIDENCE_KEY_FRAGMENTS = (
    "elapsed",
    "hostname",
    "path",
    "timestamp",
    "token",
    "username",
)
_SNAPSHOT_EXCLUDED_DIRECTORY_NAMES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "env",
    "venv",
}
_MAX_DIAGNOSTIC_EXCERPT_CHARS = 4_000


class V1SupportedPlatformMatrixError(RuntimeError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise V1SupportedPlatformMatrixError(message)


def _sanitize_diagnostic_text(value: str, *, temporary_root: Path) -> str:
    replacements = (
        (str(temporary_root), "<matrix-root>"),
        (str(PROJECT_ROOT), "<repository>"),
        (str(Path(sys.base_prefix).resolve()), "<python>"),
        (str(Path.home().resolve()), "<home>"),
    )
    sanitized = value
    for private, placeholder in sorted(replacements, key=lambda item: -len(item[0])):
        sanitized = sanitized.replace(private, placeholder)
    sanitized = re.sub(r"(?i)(token=)[^&\s'\"]+", r"\1<redacted>", sanitized)
    sanitized = re.sub(
        r"(?i)(skatmind_(?:app|capture|corpus)_token=)[^;\s'\"]+",
        r"\1<redacted>",
        sanitized,
    )
    sanitized = re.sub(
        r"(?im)^(\s*(?:set-)?cookie\s*:\s*).*$",
        r"\1<redacted>",
        sanitized,
    )
    sanitized = re.sub(
        r"(?i)(\b[A-Za-z0-9_.-]*(?:token|cookie)\b\s*[:=]\s*)"
        r"(?:'[^']*'|\"[^\"]*\"|[^\s,;]+)",
        r"\1<redacted>",
        sanitized,
    )
    for retained_token in (
        "app-distribution-token",
        "distribution-corpus-token",
        "distribution-token",
    ):
        sanitized = sanitized.replace(retained_token, "<redacted>")
    return sanitized


def _bounded_diagnostic_excerpt(value: str) -> str:
    content = value.strip()
    if not content:
        return "<empty>"
    if content.startswith(("{", "[")):
        return "<structured child output redacted>"
    if len(content) <= _MAX_DIAGNOSTIC_EXCERPT_CHARS:
        return content
    half = _MAX_DIAGNOSTIC_EXCERPT_CHARS // 2
    return (
        content[:half]
        + "\n... <bounded diagnostic excerpt truncated> ...\n"
        + content[-half:]
    )


def _bounded_failure_details(
    error: Exception,
    *,
    temporary_root: Path,
) -> str:
    diagnostic = _sanitize_diagnostic_text(str(error), temporary_root=temporary_root)
    summary, stdout_marker, child_output = diagnostic.partition("\nstdout:\n")
    child_stdout, stderr_marker, child_stderr = child_output.partition("\nstderr:\n")
    if not stdout_marker or not stderr_marker:
        child_stdout = ""
        child_stderr = diagnostic[len(summary) :]
    return (
        f"{type(error).__name__}: {_bounded_diagnostic_excerpt(summary)}\n"
        "child stdout excerpt:\n"
        f"{_bounded_diagnostic_excerpt(child_stdout)}\n"
        "child stderr excerpt:\n"
        f"{_bounded_diagnostic_excerpt(child_stderr)}"
    )


def _matrix_cell_failure_message(
    error: Exception,
    *,
    installation_form: str,
    dependency_lane: str,
    temporary_root: Path,
) -> str:
    return (
        "Matrix cell failed: "
        f"installation_form={installation_form}; dependency_lane={dependency_lane}\n"
        + _bounded_failure_details(error, temporary_root=temporary_root)
    )


def _distribution_name(requirement: str) -> str:
    match = re.match(r"[A-Za-z0-9_.-]+", requirement)
    _require(match is not None, "Runtime dependency declaration has no distribution name.")
    return re.sub(r"[-_.]+", "-", match.group(0)).lower()


def declared_runtime_dependencies(project_root: Path = PROJECT_ROOT) -> tuple[str, ...]:
    pyproject = tomllib.loads(
        project_root.joinpath("pyproject.toml").read_text(encoding="utf-8")
    )
    dependencies = pyproject["project"].get("dependencies")
    _require(isinstance(dependencies, list), "project.dependencies must be an array.")
    _require(
        all(isinstance(item, str) for item in dependencies),
        "Every runtime dependency declaration must be a string.",
    )
    return tuple(dependencies)


def _literal_dynamic_imports(tree: ast.AST) -> tuple[tuple[str, int], ...]:
    aliases = {
        alias.asname or alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module == "importlib"
        for alias in node.names
        if alias.name == "import_module"
    }
    imports: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        function = node.func
        is_import = (
            isinstance(function, ast.Name)
            and function.id in {"__import__", *aliases}
        ) or (
            isinstance(function, ast.Attribute)
            and isinstance(function.value, ast.Name)
            and function.value.id == "importlib"
            and function.attr == "import_module"
        )
        if not is_import:
            continue
        target = node.args[0]
        _require(
            isinstance(target, ast.Constant) and isinstance(target.value, str),
            "Production dynamic imports must use a literal module name.",
        )
        imports.append((target.value, node.lineno))
    return tuple(imports)


def production_import_inventory(
    project_root: Path = PROJECT_ROOT,
) -> dict[str, tuple[str, ...]]:
    source_root = project_root / "src" / "skatmind"
    production_files = [*sorted(source_root.rglob("*.py")), project_root / "main.py"]
    inventory: dict[str, list[str]] = {}
    stdlib_roots = {*sys.stdlib_module_names, "__future__"}
    for source_file in production_files:
        tree = ast.parse(source_file.read_text(encoding="utf-8"), filename=str(source_file))
        imported_modules: list[tuple[str, int]] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.extend((alias.name, node.lineno) for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imported_modules.append((node.module, node.lineno))
        imported_modules.extend(_literal_dynamic_imports(tree))
        for module_name, line_number in imported_modules:
            root = module_name.split(".", 1)[0]
            if root == "skatmind" or root in stdlib_roots:
                continue
            location = f"{source_file.relative_to(project_root).as_posix()}:{line_number}"
            inventory.setdefault(root, []).append(location)
    return {
        root: tuple(sorted(set(locations)))
        for root, locations in sorted(inventory.items())
    }


def validate_direct_import_inventory(
    project_root: Path = PROJECT_ROOT,
) -> dict[str, tuple[str, ...]]:
    declarations = declared_runtime_dependencies(project_root)
    _require(
        declarations == V1_RUNTIME_DEPENDENCIES,
        "Runtime dependency declarations differ from the v1 contract.",
    )
    declared_names = tuple(_distribution_name(item) for item in declarations)
    _require(
        declared_names == tuple(V1_RUNTIME_DISTRIBUTION_IMPORT_ROOTS),
        "Runtime dependency declarations and import-root mapping differ.",
    )
    inventory = production_import_inventory(project_root)
    expected_roots = {
        root
        for roots in V1_RUNTIME_DISTRIBUTION_IMPORT_ROOTS.values()
        for root in roots
    }
    _require(
        set(inventory) == expected_roots,
        "Production third-party imports and Package metadata are not reconciled.",
    )
    return inventory


def repository_snapshot(project_root: Path = PROJECT_ROOT) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for path in sorted(project_root.rglob("*")):
        relative = path.relative_to(project_root)
        if any(part in _SNAPSHOT_EXCLUDED_DIRECTORY_NAMES for part in relative.parts):
            continue
        if path.is_file():
            snapshot[relative.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return snapshot


def _python_evidence() -> dict[str, str]:
    implementation = platform.python_implementation()
    version = platform.python_version()
    _require(implementation == "CPython", "The v1 matrix requires CPython.")
    _require(sys.version_info[:2] == (3, 13), "The v1 matrix requires CPython 3.13.")
    return {"python_implementation": implementation, "python_version": version}


def _windows_platform_evidence() -> dict[str, str]:
    operating_system_version = platform.version()
    version_parts = operating_system_version.split(".")
    _require(
        len(version_parts) >= 3 and version_parts[2].isdigit(),
        "Windows version does not contain a numeric build.",
    )
    _require(int(version_parts[2]) >= 22000, "The Windows v1 lane requires Windows 11.")
    completed = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-Command",
            "$PSVersionTable.PSVersion.ToString()",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    _require(completed.returncode == 0, "Windows PowerShell version detection failed.")
    powershell_version = completed.stdout.strip()
    _require(
        powershell_version == "5.1" or powershell_version.startswith("5.1."),
        "The Windows v1 lane requires Windows PowerShell 5.1.",
    )
    return {
        "platform_id": V1_SUPPORTED_PLATFORMS[0],
        "operating_system": "Windows 11",
        "operating_system_version": operating_system_version,
        "powershell_version": powershell_version,
        **_python_evidence(),
    }


def _ubuntu_platform_evidence() -> dict[str, str]:
    release_values: dict[str, str] = {}
    for line in Path("/etc/os-release").read_text(encoding="utf-8").splitlines():
        if "=" not in line:
            continue
        name, value = line.split("=", 1)
        release_values[name] = value.strip().strip('"')
    _require(release_values.get("ID") == "ubuntu", "The Linux v1 lane requires Ubuntu.")
    _require(
        os.environ.get("GITHUB_ACTIONS") == "true",
        "The Ubuntu v1 lane requires the GitHub Actions runner.",
    )
    return {
        "platform_id": V1_SUPPORTED_PLATFORMS[1],
        "operating_system": "Ubuntu",
        "operating_system_version": release_values.get("VERSION_ID", "unknown"),
        **_python_evidence(),
    }


def detect_actual_platform(expected_platform: str | None = None) -> dict[str, str]:
    system = platform.system()
    if system == "Windows":
        evidence = _windows_platform_evidence()
    elif system == "Linux":
        evidence = _ubuntu_platform_evidence()
    else:
        raise V1SupportedPlatformMatrixError(
            "The current operating system is not in the v1 supported-platform matrix."
        )
    if expected_platform is not None:
        _require(
            expected_platform in V1_SUPPORTED_PLATFORMS,
            "The expected platform identifier is not in the v1 contract.",
        )
        _require(
            evidence["platform_id"] == expected_platform,
            "The expected platform identifier does not match the actual platform.",
        )
    return evidence


def normalize_semantic_output(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: (
                0
                if key == "wall_clock_elapsed_ms"
                else normalize_semantic_output(child)
            )
            for key, child in value.items()
            if key != "environment"
        }
    if isinstance(value, list):
        return [normalize_semantic_output(child) for child in value]
    return value


def _semantic_digest(smoke: dict[str, object]) -> str:
    normalized = normalize_semantic_output(smoke)
    content = json.dumps(
        normalized,
        ensure_ascii=True,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def _cell_result(
    installation_form: str,
    dependency_lane: str,
    smoke: dict[str, object],
) -> dict[str, object]:
    environment = smoke.get("environment")
    _require(isinstance(environment, dict), "Installation smoke omitted environment evidence.")
    direct_versions = environment.get("direct_dependency_versions")
    _require(isinstance(direct_versions, dict), "Installation smoke omitted dependency versions.")
    semantic = smoke.get("semantic")
    _require(isinstance(semantic, dict), "Installation smoke omitted semantic evidence.")
    workflows = semantic.get("root_workflows")
    _require(isinstance(workflows, dict), "Installation smoke omitted Root workflow evidence.")
    root_evidence: dict[str, object] = {}
    for workflow in V1_ROOT_WORKFLOWS:
        workflow_result = workflows.get(workflow)
        _require(isinstance(workflow_result, dict), f"Root workflow {workflow} was not executed.")
        default = workflow_result.get("default")
        provenance = workflow_result.get("provenance")
        _require(
            isinstance(default, dict) and isinstance(provenance, dict),
            "Root evidence changed.",
        )
        default_document = default.get("document")
        provenance_document = provenance.get("document")
        _require(
            isinstance(default_document, dict) and isinstance(provenance_document, dict),
            "Root result documents changed.",
        )
        _require("field_provenance" not in default_document, "Default provenance was not omitted.")
        _require("field_provenance" in provenance_document, "Enabled provenance was omitted.")
        artifacts = provenance.get("artifacts")
        warnings = provenance.get("warnings")
        _require(
            isinstance(artifacts, list) and isinstance(warnings, list),
            "Root envelope changed.",
        )
        root_evidence[workflow] = {
            "artifact_names": [artifact["name"] for artifact in artifacts],
            "provenance": "complete",
            "status": "passed",
            "warning_count": len(warnings),
        }
    return {
        "dependency_lane": dependency_lane,
        "direct_dependency_versions": direct_versions,
        "installation_form": installation_form,
        "pip_check": environment.get("pip_check"),
        "root_workflows": root_evidence,
        "semantic_digest": _semantic_digest(smoke),
        "status": "passed",
        "surface_statuses": {surface: "passed" for surface in V1_SURFACE_FAMILIES},
    }


def _contains_non_finite(value: object) -> bool:
    if isinstance(value, float):
        return not math.isfinite(value)
    if isinstance(value, dict):
        return any(_contains_non_finite(child) for child in value.values())
    if isinstance(value, list):
        return any(_contains_non_finite(child) for child in value)
    return False


def forbidden_evidence_fields(value: object, *, location: str = "") -> tuple[str, ...]:
    violations: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            normalized_key = key.lower()
            if any(fragment in normalized_key for fragment in _FORBIDDEN_EVIDENCE_KEY_FRAGMENTS):
                violations.append(f"{location}/{key}")
            violations.extend(forbidden_evidence_fields(child, location=f"{location}/{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            violations.extend(forbidden_evidence_fields(child, location=f"{location}/{index}"))
    elif isinstance(value, str):
        lowered = value.lower()
        if "distribution-token" in lowered or "corpus-token" in lowered:
            violations.append(location)
        if str(PROJECT_ROOT).lower() in lowered:
            violations.append(location)
    return tuple(violations)


def validate_matrix_result(result: dict[str, object]) -> None:
    _require(result.get("matrix_version") == 1, "Matrix version changed.")
    _require(result.get("status") == "passed", "Matrix did not pass.")
    vocabularies = result.get("vocabularies")
    _require(isinstance(vocabularies, dict), "Matrix vocabularies are missing.")
    _require(vocabularies.get("platforms") == list(V1_SUPPORTED_PLATFORMS), "Platforms changed.")
    _require(
        vocabularies.get("installation_forms") == list(V1_INSTALLATION_FORMS),
        "Installation forms changed.",
    )
    _require(
        vocabularies.get("dependency_lanes") == list(V1_DEPENDENCY_LANES),
        "Dependency lanes changed.",
    )
    _require(
        vocabularies.get("surface_families") == list(V1_SURFACE_FAMILIES),
        "Surface families changed.",
    )
    cells = result.get("cells")
    _require(isinstance(cells, list), "Matrix cells are missing.")
    actual_cells = tuple(
        (cell.get("installation_form"), cell.get("dependency_lane"))
        for cell in cells
        if isinstance(cell, dict)
    )
    _require(actual_cells == V1_MATRIX_CELLS, "Matrix cell ordering changed.")
    _require(all(cell.get("status") == "passed" for cell in cells), "A matrix cell failed.")
    for cell in cells:
        _require(cell.get("pip_check") == "passed", "A matrix pip check failed.")
        versions = cell.get("direct_dependency_versions")
        _require(
            isinstance(versions, dict) and set(versions) == {"jsonschema", "referencing"},
            "A matrix cell omitted direct dependency versions.",
        )
        surfaces = cell.get("surface_statuses")
        _require(
            surfaces == {surface: "passed" for surface in V1_SURFACE_FAMILIES},
            "A matrix cell omitted a surface family.",
        )
        workflows = cell.get("root_workflows")
        _require(
            isinstance(workflows, dict)
            and set(workflows) == set(V1_ROOT_WORKFLOWS)
            and len(workflows) == len(V1_ROOT_WORKFLOWS),
            "A matrix cell omitted a Root workflow.",
        )
        _require(
            all(
                isinstance(workflow, dict)
                and workflow.get("status") == "passed"
                and workflow.get("provenance") == "complete"
                for workflow in workflows.values()
            ),
            "A matrix Root workflow did not pass.",
        )
        digest = cell.get("semantic_digest")
        _require(
            isinstance(digest, str)
            and len(digest) == 64
            and all(character in "0123456789abcdef" for character in digest),
            "A matrix semantic digest is invalid.",
        )
    _require(
        result.get("runtime_dependencies") == list(V1_RUNTIME_DEPENDENCIES),
        "Matrix runtime dependencies changed.",
    )
    _require(
        result.get("minimum_runtime_dependencies")
        == list(V1_MINIMUM_RUNTIME_DEPENDENCIES),
        "Matrix minimum runtime dependencies changed.",
    )
    _require(result.get("direct_imports") == ["jsonschema", "referencing"], "Imports changed.")
    _require(result.get("semantic_parity") == "passed", "Semantic parity failed.")
    _require(result.get("repository_mutation") == "none", "Repository mutation was detected.")
    _require(not _contains_non_finite(result), "Matrix evidence contains a non-finite number.")
    _require(not forbidden_evidence_fields(result), "Matrix evidence contains a forbidden field.")
    json.dumps(result, ensure_ascii=True, allow_nan=False, sort_keys=True)


def serialize_matrix_result(result: dict[str, object]) -> str:
    validate_matrix_result(result)
    return json.dumps(
        result,
        ensure_ascii=True,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ) + "\n"


def validate_v1_supported_platform_matrix(
    *,
    expected_platform: str | None = None,
) -> dict[str, object]:
    before_snapshot = repository_snapshot()
    platform_evidence = detect_actual_platform(expected_platform)
    import_inventory = validate_direct_import_inventory()
    cells: list[dict[str, object]] = []
    normalized_smokes: list[object] = []
    with tempfile.TemporaryDirectory(prefix="skatmind-v1-matrix-") as temporary_name:
        temporary_root = Path(temporary_name).resolve()
        _require(
            not temporary_root.is_relative_to(PROJECT_ROOT),
            "Matrix temporary work must remain outside the repository.",
        )
        try:
            source_copy, wheel, sdist, expected_schemas = (
                distribution_validation._build_and_inspect_distribution_artifacts(
                    temporary_root
                )
            )
        except distribution_validation.DistributionValidationError as error:
            raise V1SupportedPlatformMatrixError(
                "Matrix distribution build failed.\n"
                + _bounded_failure_details(error, temporary_root=temporary_root)
            ) from error
        targets = {
            "source": source_copy,
            "editable": source_copy,
            "wheel": wheel,
            "sdist": sdist,
        }
        for installation_form, dependency_lane in V1_MATRIX_CELLS:
            minimum_dependencies = (
                V1_MINIMUM_RUNTIME_DEPENDENCIES
                if dependency_lane == "minimum_supported"
                else None
            )
            try:
                smoke = distribution_validation._install_and_smoke(
                    targets[installation_form],
                    label=f"{installation_form}-{dependency_lane}",
                    temporary_root=temporary_root,
                    expected_schemas=expected_schemas,
                    installation_form=installation_form,
                    editable=installation_form == "editable",
                    minimum_dependencies=minimum_dependencies,
                    external_source_root=(
                        source_copy if installation_form == "editable" else None
                    ),
                    full_root_cli_matrix=dependency_lane == "resolved",
                )
            except distribution_validation.DistributionValidationError as error:
                raise V1SupportedPlatformMatrixError(
                    _matrix_cell_failure_message(
                        error,
                        installation_form=installation_form,
                        dependency_lane=dependency_lane,
                        temporary_root=temporary_root,
                    )
                ) from error
            normalized_smokes.append(normalize_semantic_output(smoke))
            cells.append(_cell_result(installation_form, dependency_lane, smoke))
    _require(
        all(smoke == normalized_smokes[0] for smoke in normalized_smokes[1:]),
        "Semantic outputs differ across installation forms or dependency lanes.",
    )
    _require(
        repository_snapshot() == before_snapshot,
        "The supported-platform matrix changed repository files.",
    )
    result: dict[str, object] = {
        "cells": cells,
        "direct_imports": sorted(import_inventory),
        "matrix_version": V1_SUPPORTED_PLATFORM_MATRIX_VERSION,
        "minimum_runtime_dependencies": list(V1_MINIMUM_RUNTIME_DEPENDENCIES),
        "platform": platform_evidence,
        "repository_mutation": "none",
        "result_state_evidence": {
            "normal_states": list(V1_NORMAL_RESULT_STATES),
            "timing_sensitive_timeout": "deterministic_repository_tests",
        },
        "runtime_dependencies": list(V1_RUNTIME_DEPENDENCIES),
        "semantic_parity": "passed",
        "status": "passed",
        "vocabularies": {
            "dependency_lanes": list(V1_DEPENDENCY_LANES),
            "installation_forms": list(V1_INSTALLATION_FORMS),
            "platforms": list(V1_SUPPORTED_PLATFORMS),
            "surface_families": list(V1_SURFACE_FAMILIES),
        },
    }
    validate_matrix_result(result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate the SkatMind v1 installation and supported-platform matrix."
    )
    parser.add_argument("--expected-platform", choices=V1_SUPPORTED_PLATFORMS)
    arguments = parser.parse_args(argv)
    try:
        result = validate_v1_supported_platform_matrix(
            expected_platform=arguments.expected_platform
        )
        sys.stdout.write(serialize_matrix_result(result))
    except (
        V1SupportedPlatformMatrixError,
        distribution_validation.DistributionValidationError,
        OSError,
    ) as error:
        print(f"V1 supported-platform matrix validation failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
