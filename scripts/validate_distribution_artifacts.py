from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import venv
import zipfile
from email import policy
from email.message import Message
from email.parser import BytesParser
from pathlib import Path, PurePosixPath

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_PACKAGE_DIRECTORY = PROJECT_ROOT / "src" / "skat_ai"
SCHEMA_DIRECTORY = PROJECT_ROOT / "schemas"
SMOKE_EXAMPLE = PROJECT_ROOT / "examples" / "opponent_statistics.json"
PACKAGE_NAME = "skat-ai"
PACKAGE_VERSION = "0.12.0"
SCHEMA_RESOURCE_PREFIX = "skat_ai/schema_resources/"


class DistributionValidationError(RuntimeError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise DistributionValidationError(message)


def _run(
    command: list[str],
    *,
    cwd: Path,
    environment: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        rendered_command = " ".join(command)
        raise DistributionValidationError(
            f"Command failed with exit code {completed.returncode}: {rendered_command}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed


def _sanitized_environment(*, disable_user_site: bool = True) -> dict[str, str]:
    environment = os.environ.copy()
    for name in tuple(environment):
        if name.upper() in {"PYTHONHOME", "PYTHONPATH", "VIRTUAL_ENV"}:
            del environment[name]
    if disable_user_site:
        environment["PYTHONNOUSERSITE"] = "1"
    else:
        environment.pop("PYTHONNOUSERSITE", None)
    environment["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    return environment


def _repository_artifact_snapshot() -> dict[str, tuple[int, int]]:
    roots = (
        PROJECT_ROOT / "build",
        PROJECT_ROOT / "dist",
        PROJECT_ROOT / "skat_ai.egg-info",
        PROJECT_ROOT / "src" / "skat_ai.egg-info",
    )
    snapshot: dict[str, tuple[int, int]] = {}
    for root in roots:
        if root.is_file():
            stat = root.stat()
            snapshot[str(root.relative_to(PROJECT_ROOT))] = (stat.st_size, stat.st_mtime_ns)
        elif root.is_dir():
            snapshot[str(root.relative_to(PROJECT_ROOT))] = (-1, root.stat().st_mtime_ns)
            for path in sorted(root.rglob("*")):
                if path.is_file():
                    stat = path.stat()
                    snapshot[str(path.relative_to(PROJECT_ROOT))] = (
                        stat.st_size,
                        stat.st_mtime_ns,
                    )
    return snapshot


def _copy_source_tree(destination: Path) -> None:
    ignored = shutil.ignore_patterns(
        ".git",
        ".venv",
        "venv",
        "env",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        "build",
        "dist",
        "*.egg-info",
        "*.pyc",
        "output",
        "outputs",
    )
    shutil.copytree(PROJECT_ROOT, destination, ignore=ignored)


def _expected_schema_bytes() -> dict[str, bytes]:
    return {path.name: path.read_bytes() for path in sorted(SCHEMA_DIRECTORY.glob("*.schema.json"))}


def _expected_module_names() -> set[str]:
    return {
        path.relative_to(PROJECT_ROOT / "src").as_posix()
        for path in SOURCE_PACKAGE_DIRECTORY.rglob("*.py")
    }


def _parse_metadata(content: bytes) -> Message:
    return BytesParser(policy=policy.default).parsebytes(content)


def _validate_metadata(metadata: Message, *, artifact_name: str) -> None:
    _require(metadata["Name"] == PACKAGE_NAME, f"{artifact_name} has the wrong Name metadata.")
    _require(
        metadata["Version"] == PACKAGE_VERSION,
        f"{artifact_name} has the wrong Version metadata.",
    )
    _require(
        metadata["Summary"] == "Local Skat analysis and simulation tool",
        f"{artifact_name} has the wrong Summary metadata.",
    )
    _require(
        metadata["Requires-Python"] == ">=3.13",
        f"{artifact_name} has the wrong Requires-Python metadata.",
    )
    _require(
        metadata["Description-Content-Type"] == "text/markdown",
        f"{artifact_name} does not identify README.md as Markdown.",
    )

    requirements = metadata.get_all("Requires-Dist", [])
    _require(
        any(requirement.startswith("jsonschema>=4.0.0") for requirement in requirements),
        f"{artifact_name} is missing the jsonschema runtime dependency.",
    )
    for dependency in ("build>=1.2.2", "pytest>=9.0.0", "ruff>=0.14.0"):
        _require(
            any(
                requirement.startswith(dependency) and 'extra == "dev"' in requirement
                for requirement in requirements
            ),
            f"{artifact_name} is missing the {dependency} development extra.",
        )
    _require(
        metadata.get_all("Provides-Extra", []) == ["dev"],
        f"{artifact_name} has unexpected optional extras.",
    )

    for header in (
        "Author",
        "Author-email",
        "Classifier",
        "Home-page",
        "License",
        "License-Expression",
        "License-File",
        "Project-URL",
    ):
        _require(
            not metadata.get_all(header, []),
            f"{artifact_name} unexpectedly contains {header} metadata.",
        )


def _validate_schema_payload(
    payload: dict[str, bytes],
    expected: dict[str, bytes],
    *,
    artifact_name: str,
) -> None:
    _require(
        set(payload) == set(expected),
        f"{artifact_name} schema filename set differs from the repository schemas.",
    )
    schema_ids: set[str] = set()
    for name in sorted(expected):
        content = payload[name]
        _require(content == expected[name], f"{artifact_name} schema {name!r} differs by bytes.")
        try:
            decoded = content.decode("utf-8")
        except UnicodeDecodeError as error:
            raise DistributionValidationError(
                f"{artifact_name} schema {name!r} is not valid UTF-8: {error}"
            ) from error
        try:
            schema = json.loads(decoded)
        except json.JSONDecodeError as error:
            raise DistributionValidationError(
                f"{artifact_name} schema {name!r} is not valid JSON: {error}"
            ) from error
        _require(isinstance(schema, dict), f"{artifact_name} schema {name!r} is not an object.")
        schema_id = schema.get("$id")
        _require(
            isinstance(schema_id, str) and bool(schema_id),
            f"{artifact_name} schema {name!r} has no non-empty $id.",
        )
        _require(
            schema_id not in schema_ids,
            f"{artifact_name} duplicates schema $id {schema_id!r}.",
        )
        schema_ids.add(schema_id)


def _validate_wheel_record(archive: zipfile.ZipFile, names: set[str], record_name: str) -> None:
    rows = csv.reader(io.StringIO(archive.read(record_name).decode("utf-8")))
    recorded_names: set[str] = set()
    for row in rows:
        _require(len(row) == 3, "Wheel RECORD contains a malformed row.")
        name, hash_value, size_value = row
        _require(name in names, f"Wheel RECORD names missing member {name!r}.")
        _require(name not in recorded_names, f"Wheel RECORD duplicates {name!r}.")
        recorded_names.add(name)
        content = archive.read(name)
        if name == record_name:
            _require(not hash_value and not size_value, "Wheel RECORD must not hash itself.")
            continue
        _require(bool(hash_value), f"Wheel RECORD omits the hash for {name!r}.")
        algorithm, encoded_digest = hash_value.split("=", 1)
        _require(algorithm == "sha256", f"Wheel RECORD uses {algorithm!r} for {name!r}.")
        digest = base64.urlsafe_b64encode(hashlib.sha256(content).digest()).rstrip(b"=").decode()
        _require(digest == encoded_digest, f"Wheel RECORD hash mismatch for {name!r}.")
        _require(int(size_value) == len(content), f"Wheel RECORD size mismatch for {name!r}.")
    _require(recorded_names == names, "Wheel RECORD does not list every archive member.")


def _inspect_wheel(
    wheel_path: Path,
    expected_schemas: dict[str, bytes],
    expected_modules: set[str],
) -> Message:
    with zipfile.ZipFile(wheel_path) as archive:
        names_list = archive.namelist()
        names = set(names_list)
        _require(len(names) == len(names_list), "Wheel contains duplicate member names.")
        _require(
            all("\\" not in name and not PurePosixPath(name).is_absolute() for name in names),
            "Wheel contains an unsafe member path.",
        )
        _require(
            all(".." not in PurePosixPath(name).parts for name in names),
            "Wheel contains a parent-directory member path.",
        )

        dist_info_directories = {name.split("/", 1)[0] for name in names if ".dist-info/" in name}
        _require(len(dist_info_directories) == 1, "Wheel must contain one .dist-info directory.")
        dist_info = next(iter(dist_info_directories))
        metadata_name = f"{dist_info}/METADATA"
        wheel_metadata_name = f"{dist_info}/WHEEL"
        record_name = f"{dist_info}/RECORD"
        for name in (metadata_name, wheel_metadata_name, record_name):
            _require(name in names, f"Wheel is missing {name!r}.")

        metadata = _parse_metadata(archive.read(metadata_name))
        _validate_metadata(metadata, artifact_name="Wheel")
        wheel_metadata = _parse_metadata(archive.read(wheel_metadata_name))
        _require(
            wheel_metadata["Root-Is-Purelib"] == "true",
            "Wheel is not marked as a pure-Python distribution.",
        )
        _validate_wheel_record(archive, names, record_name)

        wheel_modules = {
            name for name in names if name.startswith("skat_ai/") and name.endswith(".py")
        }
        _require(
            wheel_modules == expected_modules, "Wheel does not contain exactly all skat_ai modules."
        )
        _require("skat_ai/py.typed" in names, "Wheel is missing skat_ai/py.typed.")
        _require(archive.read("skat_ai/py.typed") == b"", "Wheel py.typed marker changed.")
        schema_payload = {
            name.removeprefix(SCHEMA_RESOURCE_PREFIX): archive.read(name)
            for name in names
            if name.startswith(SCHEMA_RESOURCE_PREFIX) and name.endswith(".schema.json")
        }
        _validate_schema_payload(schema_payload, expected_schemas, artifact_name="Wheel")

        forbidden_prefixes = ("tests/", "examples/", "outputs/", "generated_outputs/")
        _require(
            not any(name.startswith(forbidden_prefixes) for name in names),
            "Wheel contains repository-only test, example, or generated-output files.",
        )
        _require("main.py" not in names, "Wheel contains the repository Root main.py.")
        _require(
            not any(".data/scripts/" in name for name in names),
            "Wheel contains an installed script payload.",
        )
        entry_points_name = f"{dist_info}/entry_points.txt"
        if entry_points_name in names:
            entry_points = archive.read(entry_points_name).decode("utf-8")
            _require("console_scripts" not in entry_points, "Wheel declares a Console Script.")
            _require("gui_scripts" not in entry_points, "Wheel declares a GUI Script.")

        return metadata


def _safe_sdist_members(archive: tarfile.TarFile) -> tuple[str, dict[str, tarfile.TarInfo]]:
    members = archive.getmembers()
    names = [member.name for member in members]
    _require(len(names) == len(set(names)), "sdist contains duplicate member names.")
    for member in members:
        path = PurePosixPath(member.name)
        _require(
            not path.is_absolute() and "\\" not in member.name and ".." not in path.parts,
            f"sdist contains unsafe member path {member.name!r}.",
        )
        _require(
            member.isfile() or member.isdir(), f"sdist contains unsupported member {member.name!r}."
        )
    roots = {PurePosixPath(name).parts[0] for name in names if PurePosixPath(name).parts}
    _require(len(roots) == 1, "sdist must contain exactly one top-level directory.")
    return next(iter(roots)), {member.name: member for member in members}


def _tar_bytes(archive: tarfile.TarFile, member: tarfile.TarInfo) -> bytes:
    extracted = archive.extractfile(member)
    _require(extracted is not None, f"Could not read sdist member {member.name!r}.")
    return extracted.read()


def _inspect_sdist(
    sdist_path: Path,
    expected_schemas: dict[str, bytes],
    expected_modules: set[str],
) -> Message:
    with tarfile.open(sdist_path, "r:gz") as archive:
        root, members = _safe_sdist_members(archive)
        names = set(members)
        required_root_files = {
            f"{root}/PKG-INFO",
            f"{root}/README.md",
            f"{root}/pyproject.toml",
        }
        _require(required_root_files <= names, "sdist is missing required source metadata files.")
        metadata = _parse_metadata(_tar_bytes(archive, members[f"{root}/PKG-INFO"]))
        _validate_metadata(metadata, artifact_name="sdist")

        archived_pyproject = tomllib.loads(
            _tar_bytes(archive, members[f"{root}/pyproject.toml"]).decode("utf-8")
        )
        _require("scripts" not in archived_pyproject["project"], "sdist declares a Console Script.")
        _require("gui-scripts" not in archived_pyproject["project"], "sdist declares a GUI Script.")
        _require(
            archived_pyproject["build-system"]
            == {
                "requires": ["setuptools>=77.0.3"],
                "build-backend": "setuptools.build_meta",
            },
            "sdist build-system metadata differs from the repository contract.",
        )

        expected_sdist_modules = {f"{root}/src/{name}" for name in expected_modules}
        sdist_modules = {
            name
            for name in names
            if name.startswith(f"{root}/src/skat_ai/") and name.endswith(".py")
        }
        _require(
            sdist_modules == expected_sdist_modules,
            "sdist does not contain exactly all skat_ai source modules.",
        )
        marker_name = f"{root}/src/skat_ai/py.typed"
        _require(marker_name in names, "sdist is missing src/skat_ai/py.typed.")
        _require(_tar_bytes(archive, members[marker_name]) == b"", "sdist py.typed marker changed.")
        schema_prefix = f"{root}/src/{SCHEMA_RESOURCE_PREFIX}"
        schema_payload = {
            name.removeprefix(schema_prefix): _tar_bytes(archive, members[name])
            for name in names
            if name.startswith(schema_prefix) and name.endswith(".schema.json")
        }
        _validate_schema_payload(schema_payload, expected_schemas, artifact_name="sdist")
        _require(f"{root}/setup.py" not in names, "sdist contains setup.py.")
        return metadata


SMOKE_PROGRAM = r"""
import hashlib
import importlib.metadata
import importlib.resources
import importlib.util
import json
import os
import sys
import sysconfig
from pathlib import Path

import skat_ai
from skat_ai.api.v1 import ExecutionOptionsV1, execute_document, parse_request, serialize_result

cwd = Path.cwd().resolve()
repository_root = Path(os.environ["SKAT_AI_REPOSITORY_ROOT"]).resolve()
document = json.loads((cwd / "opponent_statistics.json").read_text(encoding="utf-8"))
expected_schema_root = cwd / "expected_schemas"
resource_root = importlib.resources.files("skat_ai.schema_resources")
resource_names = sorted(
    resource.name
    for resource in resource_root.iterdir()
    if resource.name.endswith(".schema.json") and resource.is_file()
)
expected_names = sorted(path.name for path in expected_schema_root.glob("*.schema.json"))
assert resource_names == expected_names

schema_ids = []
schema_digest = hashlib.sha256()
for name in resource_names:
    content = resource_root.joinpath(name).read_bytes()
    assert content == (expected_schema_root / name).read_bytes()
    schema = json.loads(content.decode("utf-8"))
    assert isinstance(schema, dict)
    assert isinstance(schema.get("$id"), str) and schema["$id"]
    schema_ids.append(schema["$id"])
    schema_digest.update(name.encode("utf-8"))
    schema_digest.update(b"\0")
    schema_digest.update(content)
assert len(schema_ids) == len(set(schema_ids))

request = parse_request(document)
execution = execute_document(
    document,
    options=ExecutionOptionsV1(validate_output=True),
    input_reference="distribution-smoke.json",
)
serialized = serialize_result(execution)
assert request.workflow.value == "opponent_statistics"
assert serialized["document"]["opponent_statistics_summary"]["record_count"] == 2
assert serialized["warnings"] == []
assert serialized["artifacts"] == []

distribution = importlib.metadata.distribution("skat-ai")
assert distribution.version == "0.12.0"
assert skat_ai.__version__ == "0.12.0"
assert not [
    entry
    for entry in distribution.entry_points
    if entry.group in {"console_scripts", "gui_scripts"}
]
marker = importlib.resources.files(skat_ai).joinpath("py.typed")
assert marker.is_file() and marker.read_bytes() == b""
assert Path(distribution.locate_file("skat_ai/py.typed")).is_file()
assert importlib.util.find_spec("skat_ai.__main__") is None
assert importlib.util.find_spec("main") is None

site_roots = {
    Path(path).resolve()
    for path in (sysconfig.get_path("purelib"), sysconfig.get_path("platlib"))
    if path
}
loaded_paths = []
for module_name, module in sorted(sys.modules.items()):
    if module_name != "skat_ai" and not module_name.startswith("skat_ai."):
        continue
    module_file = getattr(module, "__file__", None)
    if module_file is None:
        continue
    module_path = Path(module_file).resolve()
    assert any(module_path.is_relative_to(site_root) for site_root in site_roots)
    assert not module_path.is_relative_to(repository_root)
    loaded_paths.append(str(module_path))
for value in sys.path:
    if not value:
        continue
    path = Path(value).resolve()
    assert path != repository_root and not path.is_relative_to(repository_root)

print(json.dumps({
    "semantic": {
        "request": request.to_dict(),
        "execution": serialized,
    },
    "schema_names": resource_names,
    "schema_ids": schema_ids,
    "schema_digest": schema_digest.hexdigest(),
    "version": skat_ai.__version__,
    "installed_module_count": len(loaded_paths),
}, sort_keys=True))
"""


def _venv_python(environment_directory: Path) -> Path:
    if os.name == "nt":
        return environment_directory / "Scripts" / "python.exe"
    return environment_directory / "bin" / "python"


def _install_and_smoke(
    artifact: Path,
    *,
    label: str,
    temporary_root: Path,
    expected_schemas: dict[str, bytes],
) -> dict[str, object]:
    environment_directory = temporary_root / f"venv-{label}"
    venv.EnvBuilder(with_pip=True, clear=True).create(environment_directory)
    python = _venv_python(environment_directory)
    consumer_directory = temporary_root / f"consumer-{label}"
    consumer_directory.mkdir()
    expected_schema_directory = consumer_directory / "expected_schemas"
    expected_schema_directory.mkdir()
    for name, content in expected_schemas.items():
        (expected_schema_directory / name).write_bytes(content)
    document = json.loads(SMOKE_EXAMPLE.read_text(encoding="utf-8"))
    (consumer_directory / "opponent_statistics.json").write_text(
        json.dumps(document, separators=(",", ":")),
        encoding="utf-8",
    )

    environment = _sanitized_environment()
    _run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--no-input",
            str(artifact),
        ],
        cwd=consumer_directory,
        environment=environment,
    )
    smoke_environment = environment.copy()
    smoke_environment["SKAT_AI_REPOSITORY_ROOT"] = str(PROJECT_ROOT)
    completed = _run(
        [str(python), "-I", "-c", SMOKE_PROGRAM],
        cwd=consumer_directory,
        environment=smoke_environment,
    )
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise DistributionValidationError(
            f"{label} smoke test did not emit valid JSON: {completed.stdout!r}"
        ) from error
    _require(isinstance(result, dict), f"{label} smoke test emitted a non-object result.")
    return result


def validate_distribution_artifacts() -> None:
    before_snapshot = _repository_artifact_snapshot()
    expected_schemas = _expected_schema_bytes()
    expected_modules = _expected_module_names()
    _require(bool(expected_schemas), "No authoritative schemas were found.")

    with tempfile.TemporaryDirectory(prefix="skat-ai-distribution-") as temporary_name:
        temporary_root = Path(temporary_name).resolve()
        _require(
            not temporary_root.is_relative_to(PROJECT_ROOT),
            "Distribution validation temporary directory must be outside the repository.",
        )
        source_copy = temporary_root / "source"
        distribution_directory = temporary_root / "dist"
        _copy_source_tree(source_copy)
        distribution_directory.mkdir()
        _run(
            [
                sys.executable,
                "-m",
                "build",
                "--outdir",
                str(distribution_directory),
                str(source_copy),
            ],
            cwd=temporary_root,
            environment=_sanitized_environment(disable_user_site=False),
        )

        wheels = sorted(distribution_directory.glob("*.whl"))
        sdists = sorted(distribution_directory.glob("*.tar.gz"))
        _require(len(wheels) == 1, "Build must produce exactly one Wheel.")
        _require(len(sdists) == 1, "Build must produce exactly one sdist.")
        _require(
            set(distribution_directory.iterdir()) == {wheels[0], sdists[0]},
            "Build output contains unexpected artifacts.",
        )

        wheel_metadata = _inspect_wheel(wheels[0], expected_schemas, expected_modules)
        sdist_metadata = _inspect_sdist(sdists[0], expected_schemas, expected_modules)
        _require(
            wheel_metadata["Name"] == sdist_metadata["Name"]
            and wheel_metadata["Version"] == sdist_metadata["Version"],
            "Wheel and sdist core metadata differ.",
        )

        wheel_smoke = _install_and_smoke(
            wheels[0],
            label="wheel",
            temporary_root=temporary_root,
            expected_schemas=expected_schemas,
        )
        sdist_smoke = _install_and_smoke(
            sdists[0],
            label="sdist",
            temporary_root=temporary_root,
            expected_schemas=expected_schemas,
        )
        _require(
            wheel_smoke == sdist_smoke,
            "Wheel and sdist clean-install smoke results differ.",
        )

    _require(
        _repository_artifact_snapshot() == before_snapshot,
        "Distribution validation changed build artifacts inside the repository.",
    )


def main() -> int:
    try:
        validate_distribution_artifacts()
    except (DistributionValidationError, OSError, tarfile.TarError, zipfile.BadZipFile) as error:
        print(f"Distribution artifact validation failed: {error}", file=sys.stderr)
        return 1
    print("Wheel, sdist, and clean-install distribution validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
