from __future__ import annotations

import base64
import configparser
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
UNAVAILABLE_SMOKE_EXAMPLE = (
    PROJECT_ROOT / "examples" / "training_dataset_preparation_unavailable.json"
)
HISTORICAL_SESSION_SMOKE_EXAMPLE = (
    PROJECT_ROOT / "examples" / "historical_grand_declarer_concession.json"
)
HISTORICAL_MATCH_SMOKE_EXAMPLE = (
    PROJECT_ROOT / "examples" / "historical_grand_normal_completion.json"
)
HISTORICAL_CLAIM_SMOKE_EXAMPLE = PROJECT_ROOT / "examples" / "historical_party_wide_claim.json"
INFORMATION_SET_SEARCH_SMOKE_EXAMPLE = PROJECT_ROOT / "examples" / "information_set_search.json"
INFORMATION_SET_SEARCH_MULTI_STEP_SMOKE_EXAMPLE = (
    PROJECT_ROOT / "examples" / "information_set_search_multi_step.json"
)
INFORMATION_SET_SEARCH_POST_GAME_SMOKE_EXAMPLE = (
    PROJECT_ROOT
    / "tests"
    / "fixtures"
    / "generated_output_schema"
    / "information_set_search_post_game_comparison.json"
)
HISTORICAL_INFORMATION_SET_SEARCH_SMOKE_EXAMPLE = (
    PROJECT_ROOT / "examples" / "historical_grand_normal_completion.json"
)
HISTORICAL_INFORMATION_SET_REPLAY_COACHING_SMOKE_EXAMPLE = (
    PROJECT_ROOT / "examples" / "historical_information_set_replay_coaching.json"
)
HISTORICAL_TACTICAL_MOTIF_REVIEW_SMOKE_EXAMPLE = (
    PROJECT_ROOT / "examples" / "historical_tactical_motif_review.json"
)
INFORMATION_SET_SEARCH_EVALUATION_SMOKE_EXAMPLE = (
    PROJECT_ROOT / "examples" / "training_dataset_normal_play.json"
)
AUTO_SMOKE_EXAMPLE = PROJECT_ROOT / "examples" / "grand_auto_search_fallback.json"
BOUNDED_MULTI_STEP_SMOKE_EXAMPLE = (
    PROJECT_ROOT / "examples" / "grand_bounded_search_exhaustive.json"
)
DEFAULT_POLICY_COMPARISON_SMOKE_EXAMPLE = (
    PROJECT_ROOT / "examples" / "grand_second_position.json"
)
PACKAGE_NAME = "skat-ai"
PACKAGE_VERSION = "0.16.0"
EXPECTED_SCHEMA_RESOURCE_COUNT = 71
SCHEMA_RESOURCE_PREFIX = "skat_ai/schema_resources/"
CAPTURE_RESOURCE_PREFIX = "skat_ai/capture_web/"
CAPTURE_RESOURCE_NAMES = (
    "templates/page.html",
    "assets/capture.css",
    "assets/capture.js",
)
CORPUS_RESOURCE_PREFIX = "skat_ai/corpus_web/"
CORPUS_RESOURCE_NAMES = (
    "templates/page.html",
    "assets/corpus.css",
    "assets/corpus.js",
)
CONSOLE_SCRIPT_NAME = "skat-ai"
CONSOLE_SCRIPT_TARGET = "skat_ai.cli:main"


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


def _expected_capture_resource_bytes() -> dict[str, bytes]:
    capture_root = SOURCE_PACKAGE_DIRECTORY / "capture_web"
    return {name: capture_root.joinpath(name).read_bytes() for name in CAPTURE_RESOURCE_NAMES}


def _expected_corpus_resource_bytes() -> dict[str, bytes]:
    corpus_root = SOURCE_PACKAGE_DIRECTORY / "corpus_web"
    return {name: corpus_root.joinpath(name).read_bytes() for name in CORPUS_RESOURCE_NAMES}


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


def _parse_entry_points(content: str, *, artifact_name: str) -> dict[str, dict[str, str]]:
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    try:
        parser.read_string(content)
    except configparser.Error as error:
        raise DistributionValidationError(
            f"{artifact_name} entry-point metadata is invalid: {error}"
        ) from error
    return {section: dict(parser.items(section)) for section in parser.sections()}


def _validate_entry_points(content: str, *, artifact_name: str) -> None:
    _require(
        _parse_entry_points(content, artifact_name=artifact_name)
        == {"console_scripts": {CONSOLE_SCRIPT_NAME: CONSOLE_SCRIPT_TARGET}},
        f"{artifact_name} must declare exactly one skat-ai Console Script and no GUI Script.",
    )


def _inspect_wheel(
    wheel_path: Path,
    expected_schemas: dict[str, bytes],
    expected_modules: set[str],
    expected_capture_resources: dict[str, bytes],
    expected_corpus_resources: dict[str, bytes],
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
        capture_payload = {
            name.removeprefix(CAPTURE_RESOURCE_PREFIX): archive.read(name)
            for name in names
            if name.startswith(CAPTURE_RESOURCE_PREFIX) and not name.endswith(".py")
        }
        _require(
            capture_payload == expected_capture_resources,
            "Wheel Capture Web resources differ by filename or bytes.",
        )
        corpus_payload = {
            name.removeprefix(CORPUS_RESOURCE_PREFIX): archive.read(name)
            for name in names
            if name.startswith(CORPUS_RESOURCE_PREFIX) and not name.endswith(".py")
        }
        _require(
            corpus_payload == expected_corpus_resources,
            "Wheel Corpus Web resources differ by filename or bytes.",
        )

        forbidden_prefixes = ("tests/", "examples/", "outputs/", "generated_outputs/")
        _require(
            not any(name.startswith(forbidden_prefixes) for name in names),
            "Wheel contains repository-only test, example, or generated-output files.",
        )
        _require("main.py" not in names, "Wheel contains the repository Root main.py.")
        _require("skat_ai/__main__.py" in names, "Wheel is missing skat_ai/__main__.py.")
        _require(
            not any(".data/scripts/" in name for name in names),
            "Wheel contains an installed script payload.",
        )
        entry_points_name = f"{dist_info}/entry_points.txt"
        _require(entry_points_name in names, "Wheel is missing entry_points.txt.")
        _validate_entry_points(
            archive.read(entry_points_name).decode("utf-8"),
            artifact_name="Wheel",
        )

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
    expected_capture_resources: dict[str, bytes],
    expected_corpus_resources: dict[str, bytes],
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
        _require(
            archived_pyproject["project"].get("scripts")
            == {CONSOLE_SCRIPT_NAME: CONSOLE_SCRIPT_TARGET},
            "sdist does not declare the exact skat-ai Console Script.",
        )
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
        capture_prefix = f"{root}/src/{CAPTURE_RESOURCE_PREFIX}"
        capture_payload = {
            name.removeprefix(capture_prefix): _tar_bytes(archive, members[name])
            for name in names
            if name.startswith(capture_prefix)
            and not name.endswith(".py")
            and members[name].isfile()
        }
        _require(
            capture_payload == expected_capture_resources,
            "sdist Capture Web resources differ by filename or bytes.",
        )
        corpus_prefix = f"{root}/src/{CORPUS_RESOURCE_PREFIX}"
        corpus_payload = {
            name.removeprefix(corpus_prefix): _tar_bytes(archive, members[name])
            for name in names
            if name.startswith(corpus_prefix)
            and not name.endswith(".py")
            and members[name].isfile()
        }
        _require(
            corpus_payload == expected_corpus_resources,
            "sdist Corpus Web resources differ by filename or bytes.",
        )
        _require(f"{root}/setup.py" not in names, "sdist contains setup.py.")
        _require(f"{root}/main.py" not in names, "sdist contains the repository Root main.py.")
        _require(
            f"{root}/src/skat_ai/__main__.py" in names,
            "sdist is missing src/skat_ai/__main__.py.",
        )
        return metadata


SESSION_FIXTURE_PROGRAM = r"""
import json
from pathlib import Path

from skat_ai.api.v1 import session
import skat_ai.api.v1.session.files as session_files

cwd = Path.cwd()
fast_options = session.SessionApiOptionsV1(validate_output=False)
players = (
    session.SessionPlayerV1(
        player_id="player-a",
        player_label="Alice",
        seat="forehand",
    ),
    session.SessionPlayerV1(
        player_id="player-b",
        player_label="Bob",
        seat="middlehand",
    ),
    session.SessionPlayerV1(
        player_id="player-c",
        player_label="Carol",
        seat="rearhand",
    ),
)


def apply(state, kind, **values):
    result = session.apply_session_command(
        state,
        {
            "command_version": 1,
            "kind": kind,
            "expected_revision": state.revision,
            **values,
        },
        options=fast_options,
    )
    assert result.value.status == "applied", result.value.to_dict()
    return result.value.state


live_state = session.create_session(
    session_id="distribution-live",
    players=players,
    capture_mode="live",
    local_player_id="player-a",
    options=fast_options,
).value
live_hand = ("CA", "C10", "CK", "CQ", "CJ", "C9", "C8", "C7", "SA", "S10")
for card in live_hand:
    live_state = apply(
        live_state,
        "record_dealt_card",
        destination="player_hand",
        player_id="player-a",
        card=card,
    )
live_state = apply(live_state, "set_declarer", declarer_player_id="player-a")
live_state = apply(
    live_state,
    "set_declaration",
    declaration={
        "game_type": "grand",
        "hand_game": True,
        "ouvert": False,
        "schneider_announced": False,
        "schwarz_announced": False,
        "matadors": None,
        "bid_value": 24,
    },
)
position_options = session.SessionPositionExportOptionsV1(
    sample_count=1,
    random_seed=0,
    use_basic_opponent_strategy=True,
    recommendation_method=None,
    bounded_search_settings=None,
)
position_export = session.export_session_position_request(
    live_state,
    position_options,
    options=fast_options,
)
assert position_export.value.status == "available"
actual_card = position_export.value.request.to_dict()["document"]["hand"][0]
(cwd / "ready-play.json").write_text(
    json.dumps(
        {
            "command_version": 1,
            "kind": "record_play",
            "expected_revision": live_state.revision,
            "player_id": "player-a",
            "card": actual_card,
        },
        separators=(",", ":"),
    ),
    encoding="utf-8",
)
live_document = session.build_session_persistence_document(
    live_state,
    options=fast_options,
).value
live_saved = session_files.save_session_file(
    cwd / "ready-live.json",
    live_document,
    expected_content_fingerprint=None,
)
assert live_saved.value.status == "saved"
live_loaded = session_files.load_session_file(cwd / "ready-live.json")
assert live_loaded.value.document == live_document

historical = json.loads(
    (cwd / "historical-session.json").read_text(encoding="utf-8")
)["historical_game_input"]
historical_players = tuple(
    session.SessionPlayerV1(
        player_id=player["player_id"],
        player_label=player.get("player_label"),
        seat=player["seat"],
    )
    for player in historical["players"]
)
historical_state = session.create_session(
    session_id="distribution-retrospective",
    players=historical_players,
    capture_mode="retrospective",
    options=fast_options,
).value
historical_state = apply(
    historical_state,
    "set_game_metadata",
    game_id=historical["game_id"],
    played_at=historical["played_at"],
)
for player in historical["players"]:
    for card in reversed(player["initial_hand"]):
        historical_state = apply(
            historical_state,
            "record_dealt_card",
            destination="player_hand",
            player_id=player["player_id"],
            card=card,
        )
for card in reversed(historical["skat"]):
    historical_state = apply(
        historical_state,
        "record_dealt_card",
        destination="skat",
        player_id=None,
        card=card,
    )
historical_state = apply(
    historical_state,
    "set_declarer",
    declarer_player_id=historical["declarer_player_id"],
)
declaration = historical["declaration"]
historical_state = apply(
    historical_state,
    "set_declaration",
    declaration={
        "game_type": declaration["game_type"],
        "hand_game": declaration.get("hand_game", False),
        "ouvert": declaration.get("ouvert", False),
        "schneider_announced": declaration.get("schneider_announced", False),
        "schwarz_announced": declaration.get("schwarz_announced", False),
        "matadors": declaration.get("matadors"),
        "bid_value": declaration.get("bid_value"),
    },
)
for card in historical["discarded_cards"]:
    historical_state = apply(historical_state, "record_discard", card=card)
for trick in historical["tricks"]:
    for play in trick["plays"]:
        historical_state = apply(
            historical_state,
            "record_play",
            player_id=play["player_id"],
            card=play["card"],
        )
historical_state = apply(
    historical_state,
    "set_game_end",
    game_end_reason=historical["game_end_reason"],
    game_end=historical["game_end"],
)
assert historical_state.validation.historical_export.status == "available"
historical_document = session.build_session_persistence_document(
    historical_state,
    options=fast_options,
).value
historical_saved = session_files.save_session_file(
    cwd / "ready-historical.json",
    historical_document,
    expected_content_fingerprint=None,
)
assert historical_saved.value.status == "saved"
assert session_files.load_session_file(
    cwd / "ready-historical.json"
).value.document == historical_document
"""


SMOKE_PROGRAM = r"""
import hashlib
import http.client
import importlib.metadata
import importlib.resources
import importlib.util
import json
import os
import sys
import sysconfig
import threading
from pathlib import Path
from urllib.parse import urlencode

import skat_ai
from skat_ai.api.v1 import (
    ExecutionOptionsV1,
    WorkflowV1,
    execute_document,
    parse_request,
    serialize_result,
)
from skat_ai.api.v1 import session
import skat_ai.api.v1.session.files as session_files
from skat_ai.api.v1.session.files.contracts import (
    SessionFileApiOptionsV1 as ContractSessionFileApiOptionsV1,
    SessionFileApiResultV1 as ContractSessionFileApiResultV1,
    SessionFileApiVersionInfoV1 as ContractSessionFileApiVersionInfoV1,
)
from skat_ai.api.v1.session.files.execution import (
    load_session_file as execution_load_session_file,
    save_session_file as execution_save_session_file,
    serialize_session_file_result as execution_serialize_session_file_result,
)
from skat_ai.cli.session_assistant import run_session_assistant
from skat_ai.capture_web.analysis import execute_match_capture_web_analysis_v1
from skat_ai.capture_web.context import MatchCaptureWebContextV1
from skat_ai.capture_web.server import start_match_capture_web_server_v1
from skat_ai.corpus_web.context import LearningCorpusWebContextV1
from skat_ai.corpus_web.server import start_learning_corpus_web_server_v1
from skat_ai.game_declaration import GameDeclaration
from skat_ai.match_analysis_contracts import (
    MatchDecisionAnalysisOptionsV1,
    MatchHistoricalAnalysisOptionsV1,
    build_match_analysis_report_v1,
)
from skat_ai.match_analysis_exports import (
    build_match_historical_game_collection_export_v1,
    build_match_materialization_summary_export_v1,
    build_match_report_result_export_v1,
)
from skat_ai.match_analysis_report_source_codec import (
    resume_match_analysis_report_source_export_v1,
)
from skat_ai.match_capture_contracts import MatchCaptureDefinitionV1
from skat_ai.match_decision_analysis import execute_match_decision_analysis_v1
from skat_ai.match_decision_review_preparation import (
    build_match_decision_review_preparation_v1,
)
from skat_ai.match_historical_analysis import execute_match_historical_analysis_v1
from skat_ai.match_player_snapshot import (
    MatchParticipantV1,
    MatchPlayerStatisticsSnapshotV1,
)
from skat_ai.match_source_metadata import MatchSourceMetadataV1
from skat_ai.match_tournament_format import get_match_tournament_format_v1
from skat_ai.match_workspace_persistence import load_match_workspace_file_v1
from skat_ai.match_workspace_contracts import create_match_workspace_v1
from skat_ai.match_workspace_operations import set_match_workspace_observed_game_v1
from skat_ai.observed_game_contracts import build_observed_game_record_v1
from skat_ai.observed_game_trace import ObservedPlayV1
from skat_ai.opponent_statistics import build_opponent_statistics_input
from skat_ai.session_persistence_contracts import (
    SessionPersistenceWriteResultV1 as InternalSessionPersistenceWriteResultV1,
    SessionResumeResultV1 as InternalSessionResumeResultV1,
)

cwd = Path.cwd().resolve()
repository_root = Path(os.environ["SKAT_AI_REPOSITORY_ROOT"]).resolve()
document = json.loads((cwd / "opponent_statistics.json").read_text(encoding="utf-8"))
information_set_search_document = json.loads(
    (cwd / "information-set-search.json").read_text(encoding="utf-8")
)
information_set_multi_step_document = json.loads(
    (cwd / "information-set-search-multi-step.json").read_text(encoding="utf-8")
)
information_set_replay_coaching_document = json.loads(
    (cwd / "historical-information-set-replay-coaching.json").read_text(
        encoding="utf-8"
    )
)
tactical_motif_document = json.loads(
    (cwd / "historical-tactical-motif-review.json").read_text(encoding="utf-8")
)
expected_schema_root = cwd / "expected_schemas"
resource_root = importlib.resources.files("skat_ai.schema_resources")
resource_names = sorted(
    resource.name
    for resource in resource_root.iterdir()
    if resource.name.endswith(".schema.json") and resource.is_file()
)
expected_names = sorted(path.name for path in expected_schema_root.glob("*.schema.json"))
assert resource_names == expected_names
assert len(resource_names) == 71
assert len(WorkflowV1) == 7

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

capture_resource_root = importlib.resources.files("skat_ai.capture_web")
capture_resource_names = (
    "templates/page.html",
    "assets/capture.css",
    "assets/capture.js",
)
capture_digest = hashlib.sha256()
for name in capture_resource_names:
    content = capture_resource_root.joinpath(name).read_bytes()
    assert content
    assert b"https://" not in content and b"http://" not in content
    capture_digest.update(name.encode("utf-8"))
    capture_digest.update(b"\0")
    capture_digest.update(content)

corpus_resource_root = importlib.resources.files("skat_ai.corpus_web")
corpus_resource_names = (
    "templates/page.html",
    "assets/corpus.css",
    "assets/corpus.js",
)
corpus_digest = hashlib.sha256()
for name in corpus_resource_names:
    content = corpus_resource_root.joinpath(name).read_bytes()
    assert content
    assert b"https://" not in content and b"http://" not in content
    assert b"eval(" not in content
    corpus_digest.update(name.encode("utf-8"))
    corpus_digest.update(b"\0")
    corpus_digest.update(content)

capture_path = cwd / "capture-workspace.json"
capture_context = MatchCaptureWebContextV1.open(capture_path)
capture_server = start_match_capture_web_server_v1(
    capture_context,
    port=0,
    token="distribution-token",
)
capture_thread = threading.Thread(target=capture_server.serve_forever, daemon=True)
capture_thread.start()


def capture_request(method, path, *, headers=None, body=None):
    connection = http.client.HTTPConnection("127.0.0.1", capture_server.port)
    connection.request(method, path, headers=headers or {}, body=body)
    response = connection.getresponse()
    content = response.read()
    returned_headers = dict(response.getheaders())
    connection.close()
    return response.status, returned_headers, content


try:
    host = f"127.0.0.1:{capture_server.port}"
    status, headers, content = capture_request(
        "GET",
        "/?token=distribution-token",
        headers={"Host": host},
    )
    assert status == 303 and content == b""
    cookie = headers["Set-Cookie"].split(";", 1)[0]
    get_headers = {"Host": host, "Cookie": cookie}
    post_headers = {
        **get_headers,
        "Origin": f"http://{host}",
        "Content-Type": "application/json",
    }
    status, _, content = capture_request("GET", "/", headers=get_headers)
    assert status == 200 and b"Create capture-workspace.json" in content

    create_values = {
        "match_id": "distribution-match",
        "title": "Distribution Match",
        "game_platform": "EuroSkat",
        "external_match_id": "",
        "played_at": "2026-08-01T18:00:00Z",
        "source_kind": "manual_observation",
        "source_url": "",
        "source_title": "Manual capture",
        "source_channel_name": "",
        "match_timecode_start": "",
        "match_timecode_end": "",
        "player_1_id": "player-a",
        "player_1_label": "Alice",
        "player_1_platform_id": "",
        "player_2_id": "player-b",
        "player_2_label": "Bob",
        "player_2_platform_id": "",
        "player_3_id": "player-c",
        "player_3_label": "Carol",
        "player_3_platform_id": "",
        "perspective_player_id": "player-a",
    }
    status, _, content = capture_request(
        "POST",
        "/api/v1/create",
        headers=post_headers,
        body=json.dumps(create_values).encode("utf-8"),
    )
    assert status == 200 and json.loads(content)["status"] == "applied"
    revision = capture_context.workspace.revision

    def capture_operation(operation, **values):
        nonlocal_values = {
            "operation": operation,
            "match_position": 1,
            "expected_revision": capture_context.workspace.revision,
            **values,
        }
        status, _, content = capture_request(
            "POST",
            "/api/v1/operation",
            headers=post_headers,
            body=json.dumps(nonlocal_values).encode("utf-8"),
        )
        assert status == 200, content
        result = json.loads(content)
        assert result["status"] == "applied", result
        return result

    capture_operation(
        "set_player_statistics_snapshot",
        player_id="player-a",
        snapshot_id="",
        observed_at="2026-07-20T10:00:00Z",
        source_type="manual_entry",
        source_name="Distribution smoke profile",
        source_player_id="",
        notes="",
        games_played=127,
        solo_games_played_percent=31,
        solo_games_won_percent=58,
        solo_hand_percent=12,
        suit_games_percent=61,
        grand_games_percent=29,
        null_games_percent=10,
        defender_games_played_percent=69,
        defender_games_won_percent=64,
    )
    assert capture_context.workspace.match_definition.participants[
        0
    ].statistics_snapshot.snapshot_id == (
        f"distribution-match-player-a-statistics-r{revision + 1}"
    )
    capture_operation(
        "clear_player_statistics_snapshot",
        player_id="player-a",
        confirm_clear_snapshot=True,
    )
    assert capture_context.workspace.match_definition.participants[
        0
    ].statistics_snapshot is None
    capture_operation(
        "start_game",
        game_id="",
        game_timecode_start="",
        game_timecode_end="",
    )
    capture_operation(
        "set_declaration",
        declarer_player_id="player-b",
        game_type="grand",
        hand_game=False,
        ouvert=False,
        schneider_announced=False,
        schwarz_announced=False,
        matadors=None,
        bid_value=24,
    )
    capture_operation("append_plays", cards="CA", decision_timecode="")
    capture_loaded = load_match_workspace_file_v1(capture_path)
    capture_game = capture_loaded.document.workspace.slots[0].observed_game
    assert capture_game is not None
    assert capture_game.declaration.game_type == "grand"
    assert capture_game.plays[0].decision_index == 1
    assert capture_game.plays[0].player_id == "player-b"
    assert capture_game.plays[0].card == "CA"
    assert capture_loaded.document.workspace.revision == revision + 5

    historical_input = json.loads(
        (cwd / "match-analysis-historical.json").read_text(encoding="utf-8")
    )["historical_game_input"]
    statistics_records = build_opponent_statistics_input(
        {
            "schema_version": 1,
            "records": [
                {
                    "player_id": player["player_id"],
                    "source": {
                        "source_type": "manual_entry",
                        "source_name": "Distribution Match profile",
                        "captured_at": "2026-07-20T10:00:00Z",
                    },
                    "games_played": 1000,
                    "statistics": {
                        "solo_games_played_percent": 42,
                        "solo_games_won_percent": 61,
                        "solo_hand_percent": 12,
                        "suit_games_percent": 55,
                        "grand_games_percent": 35,
                        "null_games_percent": 10,
                        "defender_games_played_percent": 58,
                        "defender_games_won_percent": 65,
                    },
                }
                for player in historical_input["players"]
            ],
        }
    ).records
    analysis_definition = MatchCaptureDefinitionV1(
        match_id="distribution-analysis-match",
        title="Distribution Analysis Match",
        game_platform="EuroSkat",
        external_match_id=None,
        played_at=historical_input["played_at"],
        tournament_format=get_match_tournament_format_v1(
            "euroskat_36_standard_v1"
        ),
        source=MatchSourceMetadataV1(
            source_kind="manual_observation",
            source_url=None,
            source_title="Distribution analysis fixture",
            source_channel_name=None,
            match_timecode=None,
        ),
        participants=tuple(
            MatchParticipantV1(
                player_id=player["player_id"],
                player_label=player.get("player_label"),
                platform_player_id=None,
                table_place=f"place_{index}",
                statistics_snapshot=(
                    None
                    if index == 1
                    else MatchPlayerStatisticsSnapshotV1(
                        snapshot_id=f"distribution-{player['player_id']}-snapshot",
                        observed_at="2026-07-20T10:00:00Z",
                        statistics_record=statistics_record,
                    )
                ),
            )
            for index, (player, statistics_record) in enumerate(
                zip(
                    historical_input["players"],
                    statistics_records,
                    strict=True,
                ),
                start=1,
            )
        ),
        perspective_player_id="player-a",
    )
    historical_declaration = historical_input["declaration"]
    declaration = GameDeclaration(
        game_type=historical_declaration["game_type"],
        hand_game=historical_declaration.get("hand_game", False),
        ouvert=historical_declaration.get("ouvert", False),
        schneider_announced=historical_declaration.get(
            "schneider_announced", False
        ),
        schwarz_announced=historical_declaration.get("schwarz_announced", False),
        matadors=historical_declaration.get("matadors"),
        bid_value=historical_declaration.get("bid_value"),
    )
    observed_plays = tuple(
        ObservedPlayV1(
            decision_index=decision_index,
            player_id=play["player_id"],
            card=play["card"],
            decision_timecode=None,
        )
        for decision_index, play in enumerate(
            (
                play
                for trick in historical_input["tricks"]
                for play in trick["plays"]
            ),
            start=1,
        )
    )
    perspective_hand = next(
        player["initial_hand"]
        for player in historical_input["players"]
        if player["player_id"] == analysis_definition.perspective_player_id
    )

    def analysis_workspace(play_count):
        observed_game = build_observed_game_record_v1(
            analysis_definition,
            game_id=historical_input["game_id"],
            match_position=3,
            game_timecode=None,
            seat_order_player_ids=tuple(
                player["player_id"] for player in historical_input["players"]
            ),
            perspective_initial_hand=tuple(perspective_hand),
            declarer_player_id=historical_input["declarer_player_id"],
            declaration=declaration,
            original_skat=tuple(historical_input["skat"]),
            discarded_cards=tuple(historical_input["discarded_cards"]),
            plays=observed_plays[:play_count],
            commentaries=(),
            response_links=(),
        )
        workspace = create_match_workspace_v1(analysis_definition)
        changed = set_match_workspace_observed_game_v1(
            workspace,
            observed_game,
            expected_revision=workspace.revision,
        )
        assert changed.status == "applied"
        return changed.workspace

    partial_workspace = analysis_workspace(6)
    partial_preparation = build_match_decision_review_preparation_v1(
        partial_workspace,
        match_position=3,
    )
    assert partial_preparation.status == "partial"
    assert partial_preparation.source_play_count == 6
    immediate_analysis = execute_match_decision_analysis_v1(
        partial_workspace,
        match_position=3,
        decision_index=1,
        options=MatchDecisionAnalysisOptionsV1(
            immediate_sample_count=1,
            immediate_random_seed=0,
            use_profile_presets=True,
        ),
    )
    assert immediate_analysis.status == "executed"
    immediate_document = immediate_analysis.result.to_dict()["document"]
    assert immediate_document["recommendation_method_summary"]["requested_method"] == (
        "immediate_expected_value"
    )
    profile_summary = immediate_document["opponent_profile_application_summary"]
    assert {
        profile_summary["left"]["bound_player_id"],
        profile_summary["right"]["bound_player_id"],
    } == {"player-b", "player-c"}
    assert profile_summary["left"]["application_status"] == "applied"
    assert profile_summary["right"]["application_status"] == "applied"

    complete_workspace = analysis_workspace(30)
    search_analysis = execute_match_decision_analysis_v1(
        complete_workspace,
        match_position=3,
        decision_index=22,
        options=MatchDecisionAnalysisOptionsV1(
            recommendation_method="bounded_search",
            immediate_sample_count=1,
            immediate_random_seed=0,
            search_random_seed=0,
            search_budget_profile="interactive_v1",
            use_profile_presets=True,
        ),
    )
    assert search_analysis.status == "executed"
    search_document = search_analysis.result.to_dict()["document"]
    search_result = search_document["bounded_search_result"]
    assert search_result["requested_budget"]["wall_clock_timeout_ms"] == 1000
    assert search_result["requested_budget"]["max_nodes"] == 500000
    assert search_result["status"] in {"complete", "partial", "timeout"}

    historical_analysis = execute_match_historical_analysis_v1(
        complete_workspace,
        match_position=3,
        options=MatchHistoricalAnalysisOptionsV1(
            decision_snapshots=False,
            tactical_motif_review=True,
            immediate_review=True,
            search_review=False,
            replay_coaching=False,
            immediate_sample_count=1,
            immediate_random_seed=0,
            use_profile_presets=True,
        ),
    )
    assert historical_analysis.status == "executed"
    historical_document = historical_analysis.result.to_dict()["document"]
    historical_review = historical_document["historical_game_summary"][
        "historical_game_review_summary"
    ]
    assert historical_review["decision_count"] == 30
    assert historical_review["reviewed_decision_count"] == 30
    historical_tactical = historical_document["historical_game_summary"][
        "historical_tactical_motif_review_summary"
    ]
    assert historical_tactical["observation_count"] == 30
    assert historical_tactical["complete_observation_count"] == 30

    information_set_coaching_analysis = execute_match_historical_analysis_v1(
        complete_workspace,
        match_position=3,
        options=MatchHistoricalAnalysisOptionsV1(
            decision_snapshots=False,
            immediate_review=False,
            search_review=False,
            replay_coaching=False,
            information_set_search_review=False,
            information_set_replay_coaching=True,
            immediate_sample_count=1,
            immediate_random_seed=47,
            search_random_seed=83,
            search_budget_profile="interactive_v1",
            use_profile_presets=True,
        ),
    )
    assert information_set_coaching_analysis.status == "executed"
    information_set_coaching_summary = (
        information_set_coaching_analysis.result.to_dict()["document"][
            "historical_game_summary"
        ]
    )
    information_set_coaching_report = information_set_coaching_summary[
        "historical_information_set_replay_coaching_summary"
    ]
    assert information_set_coaching_report["coverage"]["decision_count"] == 30
    assert "historical_information_set_search_review_summary" not in (
        information_set_coaching_summary
    )

    assert capture_context.save_candidate(complete_workspace) == "saved"
    corpus_workspace_bytes = capture_path.read_bytes()
    materialization_response = execute_match_capture_web_analysis_v1(
        capture_context,
        {
            "operation": "prepare_materialization",
            "match_position": 3,
            "expected_revision": complete_workspace.revision,
        },
    )
    assert materialization_response.status == "applied"
    materialization_report = capture_context.report_store.list()[-1]
    materialization = materialization_report.value.materialization
    assert materialization.historical_game_count == 1
    assert materialization.training_record_count == 1

    search_report = build_match_analysis_report_v1(search_analysis)
    historical_report = build_match_analysis_report_v1(historical_analysis)
    capture_context.report_store.add(search_report)
    capture_context.report_store.add(historical_report)

    status, _, content = capture_request(
        "GET",
        "/position/3",
        headers=get_headers,
    )
    assert status == 200
    for control in (
        b"Match materialization",
        b"Prepare Match summary",
        b"Observed Game Decisions",
        b"Analyze selected Decision",
        b"Historical Game Analysis",
        b"Analyze strict Historical Game",
        b"Tactical Motif Review",
    ):
        assert control in content

    root_path = f"/api/v1/reports/{search_report.report_id}.json"
    status, _, _ = capture_request(
        "GET",
        root_path,
        headers={"Host": host},
    )
    assert status == 403
    status, headers, content = capture_request(
        "GET",
        root_path,
        headers=get_headers,
    )
    expected_root_export = build_match_report_result_export_v1(search_report)
    assert status == 200
    assert headers["Content-Disposition"] == (
        f'attachment; filename="{expected_root_export.filename}"'
    )
    assert content == expected_root_export.to_bytes()
    assert json.loads(content) == search_document

    strategy_source_path = (
        f"/api/v1/reports/{search_report.report_id}/strategy-source.json"
    )
    status, strategy_source_headers, strategy_source_content = capture_request(
        "GET",
        strategy_source_path,
        headers=get_headers,
    )
    assert status == 200
    assert strategy_source_headers["Content-Disposition"].endswith(
        'strategy-source.json"'
    )
    strategy_source_document = json.loads(strategy_source_content)
    assert resume_match_analysis_report_source_export_v1(
        strategy_source_document
    ).report == search_report

    materialization_path = "/api/v1/exports/materialization.json"
    status, _, content = capture_request(
        "GET",
        materialization_path,
        headers=get_headers,
    )
    expected_materialization_export = build_match_materialization_summary_export_v1(
        materialization_report.value
    )
    assert status == 200
    assert content == expected_materialization_export.to_bytes()

    historical_collection_path = "/api/v1/exports/historical-games.json"
    status, _, _ = capture_request(
        "GET",
        historical_collection_path,
        headers={"Host": host},
    )
    assert status == 403
    status, headers, content = capture_request(
        "GET",
        historical_collection_path,
        headers=get_headers,
    )
    expected_historical_collection = (
        build_match_historical_game_collection_export_v1(materialization)
    )
    assert status == 200
    assert headers["Content-Disposition"] == (
        f'attachment; filename="{expected_historical_collection.filename}"'
    )
    assert content == expected_historical_collection.to_bytes()
    assert json.loads(content)["available_game_count"] == 1

    invalidation = capture_operation(
        "truncate_plays",
        match_position=3,
        target_play_count=29,
    )
    assert invalidation["status"] == "applied"
    assert capture_context.report_store.list() == ()
    status, _, _ = capture_request("GET", root_path, headers=get_headers)
    assert status == 404
    status, _, _ = capture_request(
        "GET",
        historical_collection_path,
        headers=get_headers,
    )
    assert status == 404
finally:
    capture_server.shutdown()
    capture_server.server_close()
    capture_thread.join(timeout=5)

corpus_root = cwd / "distribution-corpus"
corpus_context = LearningCorpusWebContextV1.open(corpus_root)
assert corpus_context.store is None
corpus_server = start_learning_corpus_web_server_v1(
    corpus_context,
    port=0,
    token="distribution-corpus-token",
)
corpus_thread = threading.Thread(target=corpus_server.serve_forever, daemon=True)
corpus_thread.start()


def corpus_request(method, path, *, headers=None, body=None):
    connection = http.client.HTTPConnection("127.0.0.1", corpus_server.port)
    connection.request(method, path, headers=headers or {}, body=body)
    response = connection.getresponse()
    content = response.read()
    returned_headers = dict(response.getheaders())
    connection.close()
    return response.status, returned_headers, content


def corpus_multipart(fields, file_field, content):
    boundary = "distribution-corpus-boundary"
    parts = [
        (
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"'
            f"\r\n\r\n{value}\r\n"
        ).encode("utf-8")
        for name, value in fields.items()
    ]
    parts.append(
        (
            f'--{boundary}\r\nContent-Disposition: form-data; name="{file_field}"; '
            'filename="ignored-caller-name.json"\r\n'
            "Content-Type: application/json\r\n\r\n"
        ).encode("utf-8")
        + content
        + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode("ascii"))
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


try:
    corpus_host = f"127.0.0.1:{corpus_server.port}"
    status, headers, content = corpus_request(
        "GET",
        "/?token=distribution-corpus-token",
        headers={"Host": corpus_host},
    )
    assert status == 303 and content == b""
    corpus_cookie = headers["Set-Cookie"].split(";", 1)[0]
    corpus_get_headers = {"Host": corpus_host, "Cookie": corpus_cookie}
    corpus_post_headers = {
        **corpus_get_headers,
        "Origin": f"http://{corpus_host}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    status, _, content = corpus_request("GET", "/", headers=corpus_get_headers)
    assert status == 200 and b"Initialize the Learning Corpus" in content
    initialization_body = urlencode({
        "operation": "initialize_corpus",
        "corpus_id": "distribution-corpus",
    }).encode("utf-8")
    status, _, content = corpus_request(
        "POST",
        "/api/v1/operations",
        headers=corpus_post_headers,
        body=initialization_body,
    )
    assert status == 200 and b"Learning Corpus initialized" in content

    workspace_body, workspace_content_type = corpus_multipart(
        {
            "operation": "import_match_workspace",
            "selection_mode": "select_imported",
            "same_revision_resolution": "reject",
            "expected_catalog_revision": 0,
        },
        "workspace_file",
        corpus_workspace_bytes,
    )
    status, _, content = corpus_request(
        "POST",
        "/api/v1/operations",
        headers={
            **corpus_get_headers,
            "Origin": f"http://{corpus_host}",
            "Content-Type": workspace_content_type,
        },
        body=workspace_body,
    )
    assert status == 200 and b"Match Workspace imported" in content
    assert corpus_context.store is not None
    current_selection = corpus_context.store.document.catalog.current_matches[0]

    unchanged_selection_body = urlencode({
        "operation": "select_current_snapshot",
        "match_id": current_selection.match_id,
        "match_snapshot_id": current_selection.match_snapshot_id,
        "expected_catalog_revision": 1,
    }).encode("utf-8")
    status, _, content = corpus_request(
        "POST",
        "/api/v1/operations",
        headers=corpus_post_headers,
        body=unchanged_selection_body,
    )
    assert status == 200 and b"no Corpus change" in content

    preparation_values = {
        "operation": "prepare_learning_artifacts",
        "dataset_id": "distribution-learning-dataset-v2",
        "known_player_seed": 0,
        "unseen_player_seed": 0,
        "train_weight": 70,
        "validation_weight": 15,
        "test_weight": 15,
    }
    status, _, content = corpus_request(
        "POST",
        "/api/v1/operations",
        headers=corpus_post_headers,
        body=urlencode(preparation_values).encode("utf-8"),
    )
    assert status == 200 and b"Learning artifacts prepared" in content
    assert corpus_context.prepared_artifacts is not None
    assert corpus_context.prepared_artifacts.strategy_teacher_evidence.evidence_count == 0
    assert corpus_context.prepared_artifacts.known_player_partition_result.status == (
        "unavailable"
    )
    assert corpus_context.prepared_artifacts.unseen_player_partition_result.status == (
        "unavailable"
    )

    report_body, report_content_type = corpus_multipart(
        {
            "operation": "import_strategy_teacher_report",
            "match_snapshot_id": current_selection.match_snapshot_id,
        },
        "report_source_file",
        strategy_source_content,
    )
    status, _, content = corpus_request(
        "POST",
        "/api/v1/operations",
        headers={
            **corpus_get_headers,
            "Origin": f"http://{corpus_host}",
            "Content-Type": report_content_type,
        },
        body=report_body,
    )
    assert status == 200 and b"Report source added" in content
    assert corpus_context.prepared_artifacts is None
    assert len(corpus_context.strategy_source_store.sources) == 1

    status, _, content = corpus_request(
        "POST",
        "/api/v1/operations",
        headers=corpus_post_headers,
        body=urlencode(preparation_values).encode("utf-8"),
    )
    assert status == 200 and b"Learning artifacts prepared" in content
    prepared = corpus_context.prepared_artifacts
    assert prepared is not None
    assert prepared.strategy_teacher_evidence.evidence_count == 1

    corpus_download_routes = (
        "/downloads/player-catalog.json",
        "/downloads/human-evidence.json",
        "/downloads/strategy-teacher-evidence.json",
        "/downloads/learning-dataset-v2.json",
        "/downloads/known-player-partitions.json",
        "/downloads/unseen-player-partitions.json",
        "/downloads/cross-game-summary.json",
    )
    files_before_download = sorted(path.relative_to(corpus_root) for path in corpus_root.rglob("*"))
    for route in corpus_download_routes:
        status, download_headers, content = corpus_request(
            "GET",
            route,
            headers=corpus_get_headers,
        )
        assert status == 200 and content.endswith(b"\n") and b"\r" not in content
        assert download_headers["Content-Disposition"].startswith(
            'attachment; filename="'
        )
        assert isinstance(json.loads(content), dict)
    assert sorted(path.relative_to(corpus_root) for path in corpus_root.rglob("*")) == (
        files_before_download
    )

    source_binding_id = corpus_context.strategy_source_store.source_binding_ids[0]
    remove_body = urlencode({
        "operation": "remove_strategy_teacher_report",
        "source_binding_id": source_binding_id,
    }).encode("utf-8")
    status, _, content = corpus_request(
        "POST",
        "/api/v1/operations",
        headers=corpus_post_headers,
        body=remove_body,
    )
    assert status == 200 and b"source removed" in content
    assert corpus_context.prepared_artifacts is None
    for route in corpus_download_routes:
        status, _, _ = corpus_request("GET", route, headers=corpus_get_headers)
        assert status == 404
finally:
    corpus_server.shutdown()
    corpus_server.server_close()
    corpus_thread.join(timeout=5)

assert corpus_context.strategy_source_store.sources == ()
assert corpus_context.prepared_artifacts is None

assert session.files is session_files
assert session_files.__all__ == (
    "PUBLIC_SESSION_FILE_API_VERSION",
    "PUBLIC_SESSION_FILE_API_NAMESPACE",
    "PUBLIC_SESSION_FILE_API_COMPATIBILITY_POLICY",
    "SESSION_FILE_API_OPERATIONS",
    "SessionFileApiVersionInfoV1",
    "SessionFileApiOptionsV1",
    "SessionFileApiResultV1",
    "SessionPersistenceWriteResultV1",
    "get_session_file_api_version_info_v1",
    "save_session_file",
    "load_session_file",
    "serialize_session_file_result",
)
assert session_files.SessionFileApiOptionsV1 is ContractSessionFileApiOptionsV1
assert session_files.SessionFileApiResultV1 is ContractSessionFileApiResultV1
assert session_files.SessionFileApiVersionInfoV1 is ContractSessionFileApiVersionInfoV1
assert session_files.SessionPersistenceWriteResultV1 is InternalSessionPersistenceWriteResultV1
assert session_files.save_session_file is execution_save_session_file
assert session_files.load_session_file is execution_load_session_file
assert session_files.serialize_session_file_result is execution_serialize_session_file_result
file_api_info = session_files.get_session_file_api_version_info_v1()
assert type(file_api_info) is ContractSessionFileApiVersionInfoV1
assert file_api_info.public_session_file_api_version == 1
assert file_api_info.operations == ("save", "load")

api_loaded = session_files.load_session_file(cwd / "ready-live.json")
assert type(api_loaded) is ContractSessionFileApiResultV1
assert type(api_loaded.value) is InternalSessionResumeResultV1
api_unchanged = session_files.save_session_file(
    cwd / "ready-live.json",
    api_loaded.value.document,
    expected_content_fingerprint=api_loaded.value.document.content_fingerprint,
)
assert type(api_unchanged.value) is InternalSessionPersistenceWriteResultV1
assert api_unchanged.value.status == "unchanged"
assert "path" not in session_files.serialize_session_file_result(api_loaded)

session_players = (
    session.SessionPlayerV1(player_id="p1", player_label="Player 1", seat="forehand"),
    session.SessionPlayerV1(player_id="p2", player_label="Player 2", seat="middlehand"),
    session.SessionPlayerV1(player_id="p3", player_label="Player 3", seat="rearhand"),
)
created_session = session.create_session(
    session_id="distribution-smoke",
    players=session_players,
    capture_mode="retrospective",
    options=session.SessionApiOptionsV1(include_provenance=True),
)
assert created_session.field_provenance is not None
applied_session = session.apply_session_command(
    created_session.value,
    {
        "command_version": 1,
        "kind": "set_game_metadata",
        "expected_revision": 0,
        "game_id": "distribution-smoke-game",
        "played_at": None,
    },
)
position_export = session.export_session_position_request(
    applied_session.value.state,
    session.SessionPositionExportOptionsV1(
        sample_count=1,
        random_seed=0,
        use_basic_opponent_strategy=False,
        recommendation_method=None,
        bounded_search_settings=None,
    ),
)
assert position_export.value.status == "unavailable"
persistence = session.build_session_persistence_document(applied_session.value.state)
resumed_session = session.resume_session_document(persistence.value.to_dict())
assert resumed_session.value.document == persistence.value
assert session.serialize_session_result(created_session)["operation"] == "create"

session_new = json.loads((cwd / "session-new.json").read_text(encoding="utf-8"))
session_apply = json.loads((cwd / "session-apply.json").read_text(encoding="utf-8"))
installed_session_show = json.loads(
    (cwd / "installed-session-show.json").read_text(encoding="utf-8")
)
module_session_show = json.loads(
    (cwd / "module-session-show.json").read_text(encoding="utf-8")
)
assert session_new["operation"] == "create"
assert session_new["value"]["revision"] == 0
assert session_apply["operation"] == "apply_command"
assert session_apply["value"]["status"] == "applied"
assert installed_session_show == module_session_show
assert installed_session_show["operation"] == "load"
assert installed_session_show["value"]["document"]["state"]["revision"] == 1

installed_session_analysis = json.loads(
    (cwd / "installed-session-analysis.json").read_text(encoding="utf-8")
)
module_session_analysis = json.loads(
    (cwd / "module-session-analysis.json").read_text(encoding="utf-8")
)
assert installed_session_analysis == module_session_analysis
assert "recommendation" in installed_session_analysis
ready_play = json.loads((cwd / "ready-play.json").read_text(encoding="utf-8"))
ready_loaded = session_files.load_session_file(cwd / "ready-live.json")
assert len(ready_loaded.value.document.decision_checkpoints) == 1
ready_checkpoint = ready_loaded.value.document.decision_checkpoints[0]
observation = session.observe_session_decision_checkpoint(
    state=ready_loaded.value.document.state,
    checkpoint=ready_checkpoint,
)
assert observation.value.status == "observed"
assert observation.value.actual_card == ready_play["card"]
review_export = session.export_session_checkpoint_review_request(
    state=ready_loaded.value.document.state,
    checkpoint=ready_checkpoint,
)
assert review_export.value.status == "available"
assert review_export.value.observation.actual_card == ready_play["card"]
session_review = json.loads(
    (cwd / "session-review.json").read_text(encoding="utf-8")
)
assert "post_game_review_summary" in session_review
session_finalize = json.loads(
    (cwd / "session-finalize.json").read_text(encoding="utf-8")
)
assert "historical_game_summary" in session_finalize

assistant_responses = iter(
    (
        "assistant-distribution",
        "live",
        "player-a",
        "player-a",
        "Local",
        "player-b",
        "",
        "player-c",
        "",
        "quit",
    )
)
assistant_output = []


def assistant_input(_prompt):
    return next(assistant_responses)


assistant_path = cwd / "assistant-session.json"
assert run_session_assistant(
    str(assistant_path),
    input_fn=assistant_input,
    output_fn=assistant_output.append,
) == 0
assert "Session creation status: saved" in assistant_output
assert assistant_output[-1] == "Assistant closed."
assistant_loaded = session_files.load_session_file(assistant_path)
assert assistant_loaded.value.document.state.session_id == "assistant-distribution"

request = parse_request(document)
default_execution = execute_document(
    document,
    options=ExecutionOptionsV1(validate_output=True),
    input_reference="opponent_statistics.json",
)
default_serialized = serialize_result(default_execution)
assert default_execution.field_provenance is None
assert "field_provenance" not in default_serialized["document"]
execution = execute_document(
    document,
    options=ExecutionOptionsV1(validate_output=True, include_provenance=True),
    input_reference="opponent_statistics.json",
)
serialized = serialize_result(execution)
assert request.workflow.value == "opponent_statistics"
assert serialized["document"]["opponent_statistics_summary"]["record_count"] == 2
assert serialized["warnings"] == []
assert serialized["artifacts"] == []
assert execution.field_provenance is not None
assert serialized["document"]["field_provenance"] == execution.field_provenance.to_dict()
assert execution.field_provenance.workflow.value == "opponent_statistics"
assert execution.field_provenance.result.attachment_name == "opponent_statistics_result"
assert execution.field_provenance.result.ledger["status"] == "complete"
assert execution.field_provenance.result.coverage_summary["provenance_complete"] is True
assert execution.field_provenance.artifacts == ()
information_set_request = parse_request(information_set_search_document)
information_set_execution = execute_document(
    information_set_search_document,
    options=ExecutionOptionsV1(validate_output=True, include_provenance=True),
    input_reference="information-set-search.json",
)
information_set_serialized = serialize_result(information_set_execution)
information_set_document = information_set_serialized["document"]
information_set_result = information_set_document["information_set_search_result"]
assert information_set_request.workflow.value == "position_analysis"
assert information_set_result["status"] == "complete"
assert information_set_result["search_method"] == (
    "bounded_information_set_policy_search_v1"
)
assert information_set_document["bounded_search_result"] is None
assert information_set_execution.field_provenance is not None
assert information_set_execution.field_provenance.result.ledger["status"] == "complete"
information_set_multi_step_execution = execute_document(
    information_set_multi_step_document,
    options=ExecutionOptionsV1(
        validate_output=True,
        include_provenance=True,
        workflow_options={"multi_step_count": 1, "compare_policies": True},
    ),
    input_reference="information-set-search-multi-step.json",
)
information_set_multi_step_result = information_set_multi_step_execution.result.document
assert information_set_multi_step_result["multi_step_result"]["summary"][
    "requested_method"
] == "information_set_search"
assert information_set_multi_step_result["policy_comparison_result"]["policies"][-1] == (
    "information_set_search"
)
assert information_set_multi_step_execution.field_provenance is not None
assert information_set_multi_step_execution.field_provenance.result.coverage_summary[
    "provenance_complete"
] is True
information_set_coaching_request = parse_request(
    information_set_replay_coaching_document
)
information_set_coaching_execution = execute_document(
    information_set_replay_coaching_document,
    options=ExecutionOptionsV1(
        validate_output=True,
        include_provenance=True,
        workflow_options={
            "historical_tactical_motif_review": True,
            "information_set_search_review": True,
            "information_set_replay_coaching": True,
            "search_seed": 83,
            "search_budget_profile": "interactive_v1",
            "immediate_sample_count": 1,
            "immediate_base_random_seed": 47,
        },
    ),
    input_reference="historical-information-set-replay-coaching.json",
)
information_set_coaching_document = (
    information_set_coaching_execution.result.to_dict()["document"]
)
information_set_coaching_summary = information_set_coaching_document[
    "historical_game_summary"
]
information_set_coaching_report = information_set_coaching_summary[
    "historical_information_set_replay_coaching_summary"
]
assert information_set_coaching_request.workflow.value == "historical_game"
assert "historical_information_set_search_review_summary" in (
    information_set_coaching_summary
)
assert information_set_coaching_report["report_method"] == (
    "historical_information_set_replay_coaching_v1"
)
assert information_set_coaching_report["coverage"]["decision_count"] == 30
assert information_set_coaching_summary[
    "historical_tactical_motif_review_summary"
]["observation_count"] == 30
assert information_set_coaching_execution.field_provenance is not None
assert information_set_coaching_execution.field_provenance.result.coverage_summary[
    "provenance_complete"
] is True


def collect_property_names(value):
    if isinstance(value, dict):
        return set(value).union(
            *(collect_property_names(child) for child in value.values())
        )
    if isinstance(value, list):
        return set().union(*(collect_property_names(child) for child in value))
    return set()


assert not {
    "controlled_policy",
    "policy_table",
    "observation",
    "own_hand",
    "exact_state",
    "world_identity",
    "memoization",
}.intersection(collect_property_names(information_set_result))
assert not {
    "controlled_policy",
    "policy_table",
    "observation",
    "own_hand",
    "exact_state",
    "world_identity",
    "memoization",
}.intersection(collect_property_names(information_set_coaching_report))
tactical_execution = execute_document(
    tactical_motif_document,
    options=ExecutionOptionsV1(
        validate_output=True,
        include_provenance=True,
        workflow_options={"historical_tactical_motif_review": True},
    ),
    input_reference="historical-tactical-motif-review.json",
)
tactical_summary = tactical_execution.result.document["historical_game_summary"]
tactical_report = tactical_summary["historical_tactical_motif_review_summary"]
assert tactical_report["observation_count"] == 30
assert tactical_report["complete_observation_count"] == 30
assert tactical_execution.field_provenance is not None
assert tactical_execution.field_provenance.result.coverage_summary[
    "provenance_complete"
] is True
bounded_coaching_with_tactical = execute_document(
    tactical_motif_document,
    options=ExecutionOptionsV1(
        validate_output=True,
        workflow_options={
            "historical_tactical_motif_review": True,
            "replay_coaching": True,
            "search_seed": 71,
            "search_budget_profile": "interactive_v1",
            "immediate_sample_count": 1,
            "immediate_base_random_seed": 43,
        },
    ),
    input_reference="historical-tactical-motif-review.json",
).result.document["historical_game_summary"]
assert "historical_tactical_motif_review_summary" in bounded_coaching_with_tactical
assert "historical_replay_coaching_summary" in bounded_coaching_with_tactical
claim_document = json.loads((cwd / "historical-claim.json").read_text(encoding="utf-8"))
claim_request = parse_request(claim_document)
claim_execution = execute_document(
    claim_document,
    options=ExecutionOptionsV1(validate_output=True, include_provenance=True),
    input_reference="historical-claim.json",
)
claim_serialized = serialize_result(claim_execution)
claim_summary = claim_serialized["document"]["historical_game_summary"]
assert claim_request.workflow.value == "historical_game"
assert claim_summary["status"] == "complete"
assert claim_summary["historical_game_end_summary"]["exact_proof"]["status"] == "valid"
assert claim_summary["final_settlement_summary"]["is_complete"] is True
assert claim_execution.field_provenance is not None
assert claim_execution.field_provenance.result.ledger["status"] == "complete"
assert claim_execution.field_provenance.result.coverage_summary["provenance_complete"] is True
claim_tactical_execution = execute_document(
    claim_document,
    options=ExecutionOptionsV1(
        validate_output=True,
        workflow_options={"historical_tactical_motif_review": True},
    ),
    input_reference="historical-claim.json",
)
claim_tactical_report = claim_tactical_execution.result.document[
    "historical_game_summary"
]["historical_tactical_motif_review_summary"]
assert claim_tactical_report["observation_count"] == 15
claim_coaching_execution = execute_document(
    claim_document,
    options=ExecutionOptionsV1(
        validate_output=True,
        workflow_options={
            "information_set_replay_coaching": True,
            "search_seed": 97,
            "search_budget_profile": "interactive_v1",
            "immediate_sample_count": 1,
            "immediate_base_random_seed": 53,
        },
    ),
    input_reference="historical-claim.json",
)
claim_coaching_summary = claim_coaching_execution.result.document[
    "historical_game_summary"
]
claim_coaching_report = claim_coaching_summary[
    "historical_information_set_replay_coaching_summary"
]
assert claim_coaching_report["game_context"]["game_end_reason"] == (
    "party_wide_all_remaining_tricks_claim"
)
assert claim_coaching_report["outcome_context"]["final_settlement_summary"][
    "is_complete"
] is True
installed_claim = json.loads((cwd / "installed-claim.json").read_text(encoding="utf-8"))
module_claim = json.loads((cwd / "module-claim.json").read_text(encoding="utf-8"))
legacy_claim = json.loads((cwd / "legacy-claim.json").read_text(encoding="utf-8"))
assert installed_claim == module_claim == legacy_claim == claim_serialized["document"]
installed_information_set = json.loads(
    (cwd / "installed-information-set-search.json").read_text(encoding="utf-8")
)
module_information_set = json.loads(
    (cwd / "module-information-set-search.json").read_text(encoding="utf-8")
)
legacy_information_set = json.loads(
    (cwd / "legacy-information-set-search.json").read_text(encoding="utf-8")
)


def without_wall_clock_elapsed(value):
    if isinstance(value, dict):
        return {
            key: (0 if key == "wall_clock_elapsed_ms" else without_wall_clock_elapsed(item))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [without_wall_clock_elapsed(item) for item in value]
    return value


assert (
    without_wall_clock_elapsed(installed_information_set)
    == without_wall_clock_elapsed(module_information_set)
    == without_wall_clock_elapsed(legacy_information_set)
    == without_wall_clock_elapsed(information_set_document)
)
installed_cli_document = json.loads((cwd / "installed-cli-result.json").read_text(encoding="utf-8"))
module_cli_document = json.loads((cwd / "module-cli-result.json").read_text(encoding="utf-8"))
assert installed_cli_document == module_cli_document == serialized["document"]
installed_cli_default = json.loads(
    (cwd / "installed-cli-default.json").read_text(encoding="utf-8")
)
module_cli_default = json.loads(
    (cwd / "module-cli-default.json").read_text(encoding="utf-8")
)
assert installed_cli_default == module_cli_default == default_serialized["document"]
assert "field_provenance" not in installed_cli_default
stripped_cli_document = dict(installed_cli_document)
stripped_cli_document.pop("field_provenance")
assert stripped_cli_document == installed_cli_default
unavailable_document = json.loads((cwd / "unavailable-result.json").read_text(encoding="utf-8"))
assert (
    unavailable_document["training_dataset_preparation_summary"]["plan"]["status"]
    == "unavailable"
)
assert unavailable_document["field_provenance"]["workflow"] == (
    "training_dataset_preparation"
)
assert unavailable_document["field_provenance"]["result"]["ledger"]["status"] == (
    "complete"
)

distribution = importlib.metadata.distribution("skat-ai")
assert distribution.version == "0.16.0"
assert skat_ai.__version__ == "0.16.0"
entry_points = [
    (entry.group, entry.name, entry.value)
    for entry in distribution.entry_points
    if entry.group in {"console_scripts", "gui_scripts"}
]
assert entry_points == [("console_scripts", "skat-ai", "skat_ai.cli:main")]
marker = importlib.resources.files(skat_ai).joinpath("py.typed")
assert marker.is_file() and marker.read_bytes() == b""
assert Path(distribution.locate_file("skat_ai/py.typed")).is_file()
assert importlib.util.find_spec("skat_ai.__main__") is not None
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
        "cli_document": installed_cli_document,
        "default_cli_document": installed_cli_default,
        "unavailable_document": unavailable_document,
        "information_set_search_document": information_set_document,
        "information_set_replay_coaching": {
            "decision_count": information_set_coaching_report["coverage"][
                "decision_count"
            ],
            "combined_review_present": True,
            "claim_end_reason": claim_coaching_report["game_context"][
                "game_end_reason"
            ],
        },
        "session": {
            "new": session_new,
            "apply": session_apply,
            "show": installed_session_show,
            "analysis": installed_session_analysis,
            "observation": session.serialize_session_result(observation),
            "review": session_review,
            "finalize": session_finalize,
        },
        "match_analysis": {
            "partial_preparation_status": partial_preparation.status,
            "partial_immediate_status": immediate_analysis.status,
            "profile_application_statuses": [
                profile_summary["left"]["application_status"],
                profile_summary["right"]["application_status"],
            ],
            "bounded_search_executed": search_analysis.status == "executed",
            "bounded_search_timeout_ms": search_result["requested_budget"][
                "wall_clock_timeout_ms"
            ],
            "historical_review_decision_count": historical_review[
                "decision_count"
            ],
            "materialized_historical_game_count": (
                materialization.historical_game_count
            ),
            "authenticated_root_download_exact": True,
            "authenticated_historical_collection_count": 1,
            "applied_mutation_invalidated_reports": True,
        },
        "learning_corpus": {
            "initialized": True,
            "workspace_imported": True,
            "explicit_current_selection_unchanged": True,
            "strategy_source_transfer_exact": True,
            "empty_strategy_preparation": True,
            "strategy_evidence_count": prepared.strategy_teacher_evidence.evidence_count,
            "known_player_partition_status": prepared.known_player_partition_result.status,
            "unseen_player_partition_status": prepared.unseen_player_partition_result.status,
            "download_count": len(corpus_download_routes),
            "source_removal_invalidated_downloads": True,
        },
    },
    "schema_names": resource_names,
    "schema_ids": schema_ids,
    "schema_digest": schema_digest.hexdigest(),
    "capture_resource_names": capture_resource_names,
    "capture_resource_digest": capture_digest.hexdigest(),
    "corpus_resource_names": corpus_resource_names,
    "corpus_resource_digest": corpus_digest.hexdigest(),
    "version": skat_ai.__version__,
    "installed_module_count": len(loaded_paths),
}, sort_keys=True))
"""


def _venv_python(environment_directory: Path) -> Path:
    if os.name == "nt":
        return environment_directory / "Scripts" / "python.exe"
    return environment_directory / "bin" / "python"


def _venv_console_script(environment_directory: Path) -> Path:
    if os.name == "nt":
        return environment_directory / "Scripts" / "skat-ai.exe"
    return environment_directory / "bin" / "skat-ai"


def _run_cli_check(
    command: list[str],
    *,
    cwd: Path,
    environment: dict[str, str],
    expected_returncode: int,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    _require(
        completed.returncode == expected_returncode,
        f"CLI command returned {completed.returncode}, expected {expected_returncode}: "
        f"{' '.join(command)}\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}",
    )
    return completed


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
    console_script = _venv_console_script(environment_directory)
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
    unavailable_document = json.loads(UNAVAILABLE_SMOKE_EXAMPLE.read_text(encoding="utf-8"))
    (consumer_directory / "unavailable.json").write_text(
        json.dumps(unavailable_document, separators=(",", ":")),
        encoding="utf-8",
    )
    historical_session_document = json.loads(
        HISTORICAL_SESSION_SMOKE_EXAMPLE.read_text(encoding="utf-8")
    )
    (consumer_directory / "historical-session.json").write_text(
        json.dumps(historical_session_document, separators=(",", ":")),
        encoding="utf-8",
    )
    historical_match_document = json.loads(
        HISTORICAL_MATCH_SMOKE_EXAMPLE.read_text(encoding="utf-8")
    )
    (consumer_directory / "match-analysis-historical.json").write_text(
        json.dumps(historical_match_document, separators=(",", ":")),
        encoding="utf-8",
    )
    historical_claim_document = json.loads(
        HISTORICAL_CLAIM_SMOKE_EXAMPLE.read_text(encoding="utf-8")
    )
    (consumer_directory / "historical-claim.json").write_text(
        json.dumps(historical_claim_document, separators=(",", ":")),
        encoding="utf-8",
    )
    information_set_search_document = json.loads(
        INFORMATION_SET_SEARCH_SMOKE_EXAMPLE.read_text(encoding="utf-8")
    )
    (consumer_directory / "information-set-search.json").write_text(
        json.dumps(information_set_search_document, separators=(",", ":")),
        encoding="utf-8",
    )
    information_set_multi_step_document = json.loads(
        INFORMATION_SET_SEARCH_MULTI_STEP_SMOKE_EXAMPLE.read_text(encoding="utf-8")
    )
    (consumer_directory / "information-set-search-multi-step.json").write_text(
        json.dumps(information_set_multi_step_document, separators=(",", ":")),
        encoding="utf-8",
    )
    for source, destination in (
        (
            INFORMATION_SET_SEARCH_POST_GAME_SMOKE_EXAMPLE,
            "information-set-search-post-game.json",
        ),
        (
            HISTORICAL_INFORMATION_SET_SEARCH_SMOKE_EXAMPLE,
            "historical-information-set-search.json",
        ),
        (
            HISTORICAL_INFORMATION_SET_REPLAY_COACHING_SMOKE_EXAMPLE,
            "historical-information-set-replay-coaching.json",
        ),
        (
            HISTORICAL_TACTICAL_MOTIF_REVIEW_SMOKE_EXAMPLE,
            "historical-tactical-motif-review.json",
        ),
        (
            INFORMATION_SET_SEARCH_EVALUATION_SMOKE_EXAMPLE,
            "information-set-search-evaluation.json",
        ),
        (AUTO_SMOKE_EXAMPLE, "auto-search.json"),
        (BOUNDED_MULTI_STEP_SMOKE_EXAMPLE, "bounded-multi-step.json"),
        (DEFAULT_POLICY_COMPARISON_SMOKE_EXAMPLE, "default-policy-comparison.json"),
    ):
        source_document = json.loads(source.read_text(encoding="utf-8"))
        (consumer_directory / destination).write_text(
            json.dumps(source_document, separators=(",", ":")),
            encoding="utf-8",
        )
    (consumer_directory / "session-create.json").write_text(
        json.dumps(
            {
                "session_id": "distribution-cli",
                "capture_mode": "live",
                "local_player_id": "player-a",
                "players": [
                    {
                        "player_id": "player-a",
                        "player_label": "Alice",
                        "seat": "forehand",
                    },
                    {
                        "player_id": "player-b",
                        "player_label": "Bob",
                        "seat": "middlehand",
                    },
                    {
                        "player_id": "player-c",
                        "player_label": "Carol",
                        "seat": "rearhand",
                    },
                ],
            },
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )
    (consumer_directory / "session-command.json").write_text(
        json.dumps(
            {
                "command_version": 1,
                "kind": "set_game_metadata",
                "expected_revision": 0,
                "game_id": "distribution-cli-game",
                "played_at": None,
            },
            separators=(",", ":"),
        ),
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
    _require(console_script.is_file(), f"{label} did not install the skat-ai command.")

    installed_prefix = [str(console_script)]
    module_prefix = [str(python), "-m", "skat_ai"]

    _run(
        [str(python), "-I", "-c", SESSION_FIXTURE_PROGRAM],
        cwd=consumer_directory,
        environment=environment,
    )

    for prefix, command_name in (
        (installed_prefix, "skat-ai"),
        (module_prefix, "python -m skat_ai"),
    ):
        help_result = _run_cli_check(
            [*prefix, "--help"],
            cwd=consumer_directory,
            environment=environment,
            expected_returncode=0,
        )
        _require(not help_result.stderr, f"{label} {command_name} --help wrote stderr.")
        _require(
            f"usage: {command_name}" in help_result.stdout,
            f"{label} {command_name} --help used the wrong command identity.",
        )
        _require(
            "examples/" not in help_result.stdout,
            f"{label} {command_name} --help implies repository examples are installed.",
        )
        session_help_result = _run_cli_check(
            [*prefix, "session", "--help"],
            cwd=consumer_directory,
            environment=environment,
            expected_returncode=0,
        )
        _require(
            not session_help_result.stderr,
            f"{label} {command_name} session --help wrote stderr.",
        )
        _require(
            f"usage: {command_name} session" in session_help_result.stdout,
            f"{label} {command_name} session --help used the wrong command identity.",
        )
        capture_help_result = _run_cli_check(
            [*prefix, "capture", "--help"],
            cwd=consumer_directory,
            environment=environment,
            expected_returncode=0,
        )
        _require(
            not capture_help_result.stderr,
            f"{label} {command_name} capture --help wrote stderr.",
        )
        _require(
            f"usage: {command_name} capture" in capture_help_result.stdout,
            f"{label} {command_name} capture --help used the wrong command identity.",
        )
        for option in ("--workspace PATH", "--port INTEGER", "--no-open"):
            _require(
                option in capture_help_result.stdout,
                f"{label} {command_name} capture --help omits {option!r}.",
            )
        for forbidden_option in ("--host", "--force", "--daemon"):
            _require(
                forbidden_option not in capture_help_result.stdout,
                f"{label} {command_name} capture --help exposes {forbidden_option!r}.",
            )
        corpus_help_result = _run_cli_check(
            [*prefix, "corpus", "--help"],
            cwd=consumer_directory,
            environment=environment,
            expected_returncode=0,
        )
        _require(
            not corpus_help_result.stderr,
            f"{label} {command_name} corpus --help wrote stderr.",
        )
        _require(
            f"usage: {command_name} corpus" in corpus_help_result.stdout,
            f"{label} {command_name} corpus --help used the wrong command identity.",
        )
        for option in ("--corpus PATH", "--port INTEGER", "--no-open"):
            _require(
                option in corpus_help_result.stdout,
                f"{label} {command_name} corpus --help omits {option!r}.",
            )
        for forbidden_option in ("--host", "--force", "--daemon", "--workspace"):
            _require(
                forbidden_option not in corpus_help_result.stdout,
                f"{label} {command_name} corpus --help exposes {forbidden_option!r}.",
            )
        for subcommand in (
            "new",
            "show",
            "apply",
            "analyze",
            "review",
            "finalize",
            "assistant",
        ):
            _require(
                subcommand in session_help_result.stdout,
                f"{label} {command_name} session --help omits {subcommand!r}.",
            )
        version_result = _run_cli_check(
            [*prefix, "--version"],
            cwd=consumer_directory,
            environment=environment,
            expected_returncode=0,
        )
        _require(
            version_result.stdout == "skat-ai 0.16.0\n" and not version_result.stderr,
            f"{label} {command_name} --version output changed.",
        )

    legacy_directory = temporary_root / f"legacy-{label}"
    legacy_directory.mkdir()
    legacy_main = legacy_directory / "main.py"
    shutil.copy2(PROJECT_ROOT / "main.py", legacy_main)
    legacy_corpus_help = _run_cli_check(
        [str(python), str(legacy_main), "corpus", "--help"],
        cwd=legacy_directory,
        environment=environment,
        expected_returncode=0,
    )
    _require(
        not legacy_corpus_help.stderr
        and "usage: python main.py corpus" in legacy_corpus_help.stdout,
        f"{label} Legacy corpus --help used the wrong command identity.",
    )
    for option in ("--corpus PATH", "--port INTEGER", "--no-open"):
        _require(
            option in legacy_corpus_help.stdout,
            f"{label} Legacy corpus --help omits {option!r}.",
        )

    for prefix, default_output_name, provenance_output_name in (
        (
            installed_prefix,
            "installed-cli-default.json",
            "installed-cli-result.json",
        ),
        (
            module_prefix,
            "module-cli-default.json",
            "module-cli-result.json",
        ),
    ):
        default_completed = _run_cli_check(
            [
                *prefix,
                "--input",
                "opponent_statistics.json",
                "--output",
                default_output_name,
                "--quiet",
            ],
            cwd=consumer_directory,
            environment=environment,
            expected_returncode=0,
        )
        provenance_completed = _run_cli_check(
            [
                *prefix,
                "--input",
                "opponent_statistics.json",
                "--output",
                provenance_output_name,
                "--include-provenance",
                "--quiet",
            ],
            cwd=consumer_directory,
            environment=environment,
            expected_returncode=0,
        )
        _require(
            not default_completed.stdout
            and not default_completed.stderr
            and not provenance_completed.stdout
            and not provenance_completed.stderr,
            f"{label} quiet CLI workflow produced output.",
        )

    quiet_session_commands = (
        (
            [
                *installed_prefix,
                "session",
                "new",
                "--session",
                "cli-session.json",
                "--input",
                "session-create.json",
                "--output",
                "session-new.json",
                "--quiet",
            ],
            "installed Session new",
        ),
        (
            [
                *module_prefix,
                "session",
                "apply",
                "--session",
                "cli-session.json",
                "--input",
                "session-command.json",
                "--output",
                "session-apply.json",
                "--quiet",
            ],
            "module Session apply",
        ),
        (
            [
                *installed_prefix,
                "session",
                "show",
                "--session",
                "cli-session.json",
                "--output",
                "installed-session-show.json",
                "--quiet",
            ],
            "installed Session show",
        ),
        (
            [
                *module_prefix,
                "session",
                "show",
                "--session",
                "cli-session.json",
                "--output",
                "module-session-show.json",
                "--quiet",
            ],
            "module Session show",
        ),
        (
            [
                *installed_prefix,
                "session",
                "analyze",
                "--session",
                "ready-live.json",
                "--output",
                "installed-session-analysis.json",
                "--samples",
                "1",
                "--seed",
                "0",
                "--quiet",
            ],
            "installed Session analyze",
        ),
        (
            [
                *module_prefix,
                "session",
                "analyze",
                "--session",
                "ready-live.json",
                "--output",
                "module-session-analysis.json",
                "--samples",
                "1",
                "--seed",
                "0",
                "--quiet",
            ],
            "module Session analyze",
        ),
        (
            [
                *installed_prefix,
                "session",
                "apply",
                "--session",
                "ready-live.json",
                "--input",
                "ready-play.json",
                "--output",
                "session-play.json",
                "--samples",
                "1",
                "--seed",
                "0",
                "--quiet",
            ],
            "installed observed-card Session apply",
        ),
        (
            [
                *module_prefix,
                "session",
                "review",
                "--session",
                "ready-live.json",
                "--checkpoint-index",
                "0",
                "--output",
                "session-review.json",
                "--quiet",
            ],
            "module Session review",
        ),
        (
            [
                *installed_prefix,
                "session",
                "finalize",
                "--session",
                "ready-historical.json",
                "--output",
                "session-finalize.json",
                "--quiet",
            ],
            "installed Session finalize",
        ),
    )
    for command, description in quiet_session_commands:
        session_completed = _run_cli_check(
            command,
            cwd=consumer_directory,
            environment=environment,
            expected_returncode=0,
        )
        _require(
            not session_completed.stdout and not session_completed.stderr,
            f"{label} {description} was not a quiet success.",
        )

    unavailable_result = _run_cli_check(
        [
            *installed_prefix,
            "--input",
            "unavailable.json",
            "--output",
            "unavailable-result.json",
            "--include-provenance",
            "--quiet",
        ],
        cwd=consumer_directory,
        environment=environment,
        expected_returncode=0,
    )
    _require(
        not unavailable_result.stdout and not unavailable_result.stderr,
        f"{label} unavailable Result was not a quiet success.",
    )
    for prefix, output_name, command_name in (
        (installed_prefix, "installed-claim.json", "installed"),
        (module_prefix, "module-claim.json", "module"),
        ([str(python), str(legacy_main)], "legacy-claim.json", "Legacy"),
    ):
        claim_result = _run_cli_check(
            [
                *prefix,
                "--input",
                "historical-claim.json",
                "--output",
                output_name,
                "--include-provenance",
                "--quiet",
            ],
            cwd=consumer_directory,
            environment=environment,
            expected_returncode=0,
        )
        _require(
            not claim_result.stdout and not claim_result.stderr,
            f"{label} {command_name} Historical Claim was not a quiet success.",
        )
    for prefix, output_name, command_name in (
        (installed_prefix, "installed-information-set-search.json", "installed"),
        (module_prefix, "module-information-set-search.json", "module"),
        (
            [str(python), str(legacy_main)],
            "legacy-information-set-search.json",
            "Legacy",
        ),
    ):
        information_set_result = _run_cli_check(
            [
                *prefix,
                "--input",
                "information-set-search.json",
                "--output",
                output_name,
                "--include-provenance",
                "--quiet",
            ],
            cwd=consumer_directory,
            environment=environment,
            expected_returncode=0,
        )
        _require(
            not information_set_result.stdout and not information_set_result.stderr,
            f"{label} {command_name} information-set Search was not a quiet success.",
        )
        information_set_document = json.loads(
            (consumer_directory / output_name).read_text(encoding="utf-8")
        )
        _require(
            "information_set_search_result" in information_set_document
            and "field_provenance" in information_set_document,
            f"{label} {command_name} information-set Search omitted its safe Result or provenance.",
        )

    for prefix, command_name in (
        (installed_prefix, "installed"),
        (module_prefix, "module"),
        ([str(python), str(legacy_main)], "Legacy"),
    ):
        for output_stem, extra_args in (
            (
                "information-set-multi-step",
                ("--multi-step", "1", "--include-provenance"),
            ),
            (
                "information-set-policy-comparison",
                (
                    "--multi-step",
                    "1",
                    "--compare-policies",
                    "--include-provenance",
                ),
            ),
        ):
            output_name = f"{command_name.lower()}-{output_stem}.json"
            simulation_result = _run_cli_check(
                [
                    *prefix,
                    "--input",
                    "information-set-search-multi-step.json",
                    "--output",
                    output_name,
                    *extra_args,
                    "--quiet",
                ],
                cwd=consumer_directory,
                environment=environment,
                expected_returncode=0,
            )
            _require(
                not simulation_result.stdout and not simulation_result.stderr,
                f"{label} {command_name} {output_stem} was not a quiet success.",
            )
            simulation_document = json.loads(
                (consumer_directory / output_name).read_text(encoding="utf-8")
            )
            multi_step = simulation_document.get("multi_step_result")
            valid = isinstance(multi_step, dict) and (
                multi_step.get("card_selection_policy") == "information_set_search"
            )
            if output_stem == "information-set-policy-comparison":
                comparison = simulation_document.get("policy_comparison_result")
                valid = valid and isinstance(comparison, dict) and (
                    comparison.get("policies", [])[-1:] == ["information_set_search"]
                )
            _require(
                valid and "field_provenance" in simulation_document,
                f"{label} {command_name} {output_stem} omitted its safe Result or provenance.",
            )

    for input_name, output_name, extra_args, expected_policy in (
        (
            "bounded-multi-step.json",
            "unchanged-bounded-multi-step.json",
            ("--multi-step", "1"),
            "bounded_search",
        ),
        (
            "auto-search.json",
            "unchanged-auto-multi-step.json",
            ("--multi-step", "1"),
            "auto",
        ),
        (
            "default-policy-comparison.json",
            "unchanged-default-policy-comparison.json",
            ("--multi-step", "1", "--compare-policies"),
            "first_legal",
        ),
    ):
        compatibility_result = _run_cli_check(
            [
                *installed_prefix,
                "--input",
                input_name,
                "--output",
                output_name,
                *extra_args,
                "--quiet",
            ],
            cwd=consumer_directory,
            environment=environment,
            expected_returncode=0,
        )
        _require(
            not compatibility_result.stdout and not compatibility_result.stderr,
            f"{label} unchanged {expected_policy} simulation was not a quiet success.",
        )
        compatibility_document = json.loads(
            (consumer_directory / output_name).read_text(encoding="utf-8")
        )
        _require(
            compatibility_document["multi_step_result"]["card_selection_policy"]
            == expected_policy,
            f"{label} unchanged {expected_policy} simulation changed policy routing.",
        )

    information_set_workflow_smokes = (
        (
            "information-set-search-post-game.json",
            "information-set-search-post-game",
            (),
        ),
        (
            "historical-information-set-search.json",
            "historical-information-set-search",
            (
                "--historical-information-set-search-review",
                "--search-seed",
                "83",
                "--search-budget-profile",
                "interactive_v1",
                "--samples",
                "1",
                "--seed",
                "47",
            ),
        ),
        (
            "historical-information-set-replay-coaching.json",
            "historical-information-set-replay-coaching",
            (
                "--historical-information-set-replay-coaching",
                "--search-seed",
                "83",
                "--search-budget-profile",
                "interactive_v1",
                "--samples",
                "1",
                "--seed",
                "47",
                "--include-provenance",
            ),
        ),
        (
            "historical-tactical-motif-review.json",
            "historical-tactical-motif-review",
            (
                "--historical-tactical-motif-review",
                "--include-provenance",
            ),
        ),
        (
            "information-set-search-evaluation.json",
            "information-set-search-evaluation",
            (
                "--information-set-search-evaluation",
                "--search-seed",
                "89",
                "--search-evaluation-max-decisions",
                "1",
            ),
        ),
        ("auto-search.json", "unchanged-auto", ()),
    )
    for prefix, command_name in (
        (installed_prefix, "installed"),
        (module_prefix, "module"),
        ([str(python), str(legacy_main)], "Legacy"),
    ):
        for input_name, output_stem, workflow_args in information_set_workflow_smokes:
            output_name = f"{command_name.lower()}-{output_stem}.json"
            workflow_result = _run_cli_check(
                [
                    *prefix,
                    "--input",
                    input_name,
                    "--output",
                    output_name,
                    *workflow_args,
                    "--quiet",
                ],
                cwd=consumer_directory,
                environment=environment,
                expected_returncode=0,
            )
            _require(
                not workflow_result.stdout and not workflow_result.stderr,
                f"{label} {command_name} {output_stem} was not a quiet success.",
            )
            workflow_document = json.loads(
                (consumer_directory / output_name).read_text(encoding="utf-8")
            )
            if output_stem == "information-set-search-post-game":
                valid = "information_set_search_comparison" in workflow_document
            elif output_stem == "historical-information-set-search":
                historical_summary = workflow_document.get("historical_game_summary")
                valid = isinstance(historical_summary, dict) and (
                    "historical_information_set_search_review_summary"
                    in historical_summary
                )
            elif output_stem == "historical-information-set-replay-coaching":
                historical_summary = workflow_document.get("historical_game_summary")
                valid = isinstance(historical_summary, dict) and (
                    "historical_information_set_replay_coaching_summary"
                    in historical_summary
                    and "historical_information_set_search_review_summary"
                    not in historical_summary
                    and "field_provenance" in workflow_document
                )
            elif output_stem == "historical-tactical-motif-review":
                historical_summary = workflow_document.get("historical_game_summary")
                valid = isinstance(historical_summary, dict) and (
                    historical_summary.get(
                        "historical_tactical_motif_review_summary", {}
                    ).get("observation_count")
                    == 30
                    and "field_provenance" in workflow_document
                )
            elif output_stem == "information-set-search-evaluation":
                valid = "information_set_search_evaluation_summary" in workflow_document
            else:
                method_summary = workflow_document.get("recommendation_method_summary")
                valid = isinstance(method_summary, dict) and (
                    method_summary.get("requested_method") == "auto"
                )
            _require(
                valid,
                f"{label} {command_name} {output_stem} omitted its expected Result.",
            )
    unknown_result = _run_cli_check(
        [*installed_prefix, "--not-an-option"],
        cwd=consumer_directory,
        environment=environment,
        expected_returncode=2,
    )
    _require(
        not unknown_result.stdout
        and "usage: skat-ai" in unknown_result.stderr
        and "unrecognized arguments" in unknown_result.stderr,
        f"{label} unknown-option usage behavior changed.",
    )
    missing_result = _run_cli_check(
        [*module_prefix, "--input", "missing.json"],
        cwd=consumer_directory,
        environment=environment,
        expected_returncode=1,
    )
    _require(
        not missing_result.stdout and "Error: Input file not found:" in missing_result.stderr,
        f"{label} missing-input failure behavior changed.",
    )

    smoke_environment = environment.copy()
    smoke_environment["SKAT_AI_REPOSITORY_ROOT"] = str(PROJECT_ROOT)
    smoke_program_path = consumer_directory / "installed-smoke.py"
    smoke_program_path.write_text(SMOKE_PROGRAM, encoding="utf-8")
    completed = _run(
        [str(python), "-I", str(smoke_program_path)],
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
    expected_capture_resources = _expected_capture_resource_bytes()
    expected_corpus_resources = _expected_corpus_resource_bytes()
    _require(
        len(expected_schemas) == EXPECTED_SCHEMA_RESOURCE_COUNT,
        f"Expected {EXPECTED_SCHEMA_RESOURCE_COUNT} authoritative schemas, "
        f"found {len(expected_schemas)}.",
    )

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

        wheel_metadata = _inspect_wheel(
            wheels[0],
            expected_schemas,
            expected_modules,
            expected_capture_resources,
            expected_corpus_resources,
        )
        sdist_metadata = _inspect_sdist(
            sdists[0],
            expected_schemas,
            expected_modules,
            expected_capture_resources,
            expected_corpus_resources,
        )
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
