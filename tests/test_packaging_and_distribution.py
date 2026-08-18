import importlib.metadata
import importlib.resources
import json
import tomllib
from pathlib import Path

import skat_ai
import skat_ai._version as version_module
from scripts import sync_packaged_schemas

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIRECTORY = PROJECT_ROOT / "schemas"
PACKAGED_SCHEMA_DIRECTORY = PROJECT_ROOT / "src" / "skat_ai" / "schema_resources"
CAPTURE_RESOURCE_DIRECTORY = PROJECT_ROOT / "src" / "skat_ai" / "capture_web"
CORPUS_RESOURCE_DIRECTORY = PROJECT_ROOT / "src" / "skat_ai" / "corpus_web"


def test_build_metadata_package_discovery_and_package_data_are_explicit() -> None:
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["build-system"] == {
        "requires": ["setuptools>=77.0.3"],
        "build-backend": "setuptools.build_meta",
    }
    assert pyproject["project"]["name"] == "skat-ai"
    assert pyproject["project"]["version"] == "0.15.0"
    assert pyproject["project"]["requires-python"] == ">=3.13"
    assert pyproject["project"]["readme"] == "README.md"
    assert pyproject["project"]["dependencies"] == ["jsonschema>=4.0.0"]
    assert pyproject["project"]["scripts"] == {"skat-ai": "skat_ai.cli:main"}
    assert pyproject["project"]["optional-dependencies"]["dev"] == [
        "build>=1.2.2",
        "pytest>=9.0.0",
        "ruff>=0.14.0",
    ]
    assert pyproject["tool"]["setuptools"]["packages"]["find"] == {
        "where": ["src"],
        "include": ["skat_ai*"],
    }
    assert pyproject["tool"]["setuptools"]["package-data"] == {
        "skat_ai": ["py.typed"],
        "skat_ai.schema_resources": ["*.schema.json"],
        "skat_ai.capture_web": [
            "templates/*.html",
            "assets/*.css",
            "assets/*.js",
        ],
        "skat_ai.corpus_web": [
            "templates/*.html",
            "assets/*.css",
            "assets/*.js",
        ],
    }
    for forbidden in (
        "authors",
        "classifiers",
        "gui-scripts",
        "license",
        "urls",
    ):
        assert forbidden not in pyproject["project"]
    assert not (PROJECT_ROOT / "setup.py").exists()
    assert not (PROJECT_ROOT / "setup.cfg").exists()


def test_packaged_schema_mirror_has_exact_filename_byte_and_id_parity() -> None:
    from scripts.validate_distribution_artifacts import (
        EXPECTED_SCHEMA_RESOURCE_COUNT,
    )

    authoritative = {
        path.name: path.read_bytes() for path in sorted(SCHEMA_DIRECTORY.glob("*.schema.json"))
    }
    packaged = {
        path.name: path.read_bytes()
        for path in sorted(PACKAGED_SCHEMA_DIRECTORY.glob("*.schema.json"))
    }

    assert EXPECTED_SCHEMA_RESOURCE_COUNT == 63
    assert len(authoritative) == EXPECTED_SCHEMA_RESOURCE_COUNT
    assert packaged == authoritative
    schema_ids = []
    for name, content in packaged.items():
        schema = json.loads(content.decode("utf-8"))
        assert isinstance(schema, dict)
        assert schema["$id"] == f"https://example.local/skat-ai/{name}"
        schema_ids.append(schema["$id"])
    assert len(schema_ids) == len(set(schema_ids))


def test_schema_resource_package_and_typing_marker_are_available() -> None:
    resources = importlib.resources.files("skat_ai.schema_resources")
    resource_names = sorted(
        resource.name
        for resource in resources.iterdir()
        if resource.name.endswith(".schema.json") and resource.is_file()
    )

    assert resource_names == sorted(path.name for path in SCHEMA_DIRECTORY.glob("*.schema.json"))
    assert (PROJECT_ROOT / "src" / "skat_ai" / "py.typed").read_bytes() == b""
    marker = importlib.resources.files(skat_ai).joinpath("py.typed")
    assert marker.is_file()
    assert marker.read_bytes() == b""


def test_capture_web_resources_are_local_package_data() -> None:
    resources = importlib.resources.files("skat_ai.capture_web")
    expected = {
        "templates/page.html",
        "assets/capture.css",
        "assets/capture.js",
    }
    for name in expected:
        resource = resources.joinpath(name)
        source = CAPTURE_RESOURCE_DIRECTORY.joinpath(name)
        assert resource.is_file()
        assert resource.read_bytes() == source.read_bytes()
    combined = b"".join(
        CAPTURE_RESOURCE_DIRECTORY.joinpath(name).read_bytes() for name in sorted(expected)
    )
    assert b"https://" not in combined
    assert b"http://" not in combined
    assert b"eval(" not in combined


def test_corpus_web_resources_are_local_package_data() -> None:
    resources = importlib.resources.files("skat_ai.corpus_web")
    expected = {
        "templates/page.html",
        "assets/corpus.css",
        "assets/corpus.js",
    }
    for name in expected:
        resource = resources.joinpath(name)
        source = CORPUS_RESOURCE_DIRECTORY.joinpath(name)
        assert resource.is_file()
        assert resource.read_bytes() == source.read_bytes()
    combined = b"".join(
        CORPUS_RESOURCE_DIRECTORY.joinpath(name).read_bytes() for name in sorted(expected)
    )
    assert b"https://" not in combined
    assert b"http://" not in combined
    assert b"eval(" not in combined


def test_match_player_statistics_modules_are_package_discovered() -> None:
    import skat_ai.match_player_statistics_context as context_module
    import skat_ai.match_player_statistics_preparation as preparation_module
    import skat_ai.match_player_statistics_updates as updates_module

    assert context_module.MATCH_PLAYER_STATISTICS_CONTEXT_VERSION == 1
    assert preparation_module.MATCH_PLAYER_STATISTICS_PREPARATION_VERSION == 1
    assert updates_module.MATCH_PLAYER_STATISTICS_UPDATE_VERSION == 1


def test_schema_sync_check_is_deterministic_and_does_not_modify_files(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source = tmp_path / "source"
    packaged = tmp_path / "packaged"
    source.mkdir()
    packaged.mkdir()
    (source / "a.schema.json").write_bytes(b'{"$id":"a"}\n')
    (source / "b.schema.json").write_bytes(b'{"$id":"b"}\n')
    (packaged / "a.schema.json").write_bytes(b'{"$id":"changed"}\n')
    (packaged / "c.schema.json").write_bytes(b'{"$id":"c"}\n')
    before = {path.name: path.read_bytes() for path in packaged.glob("*.schema.json")}
    monkeypatch.setattr(sync_packaged_schemas, "AUTHORITATIVE_SCHEMA_DIRECTORY", source)
    monkeypatch.setattr(sync_packaged_schemas, "PACKAGED_SCHEMA_DIRECTORY", packaged)

    assert sync_packaged_schemas.schema_parity_errors(source, packaged) == (
        "Missing packaged schema: b.schema.json",
        "Unexpected packaged schema: c.schema.json",
        "Packaged schema differs: a.schema.json",
    )
    assert sync_packaged_schemas.main(["--check"]) == 1
    assert {path.name: path.read_bytes() for path in packaged.glob("*.schema.json")} == before

    assert sync_packaged_schemas.main([]) == 0
    assert sync_packaged_schemas.schema_parity_errors(source, packaged) == ()
    assert (packaged / "a.schema.json").read_bytes() == b'{"$id":"a"}\n'
    assert (packaged / "b.schema.json").read_bytes() == b'{"$id":"b"}\n'
    assert not (packaged / "c.schema.json").exists()


def test_package_version_uses_distribution_metadata() -> None:
    assert importlib.metadata.version("skat-ai") == "0.15.0"
    assert skat_ai.__version__ == "0.15.0"


def test_source_only_version_fallback_reads_no_repository_file(monkeypatch) -> None:
    def metadata_missing(_distribution_name: str) -> str:
        raise importlib.metadata.PackageNotFoundError("skat-ai")

    def unexpected_open(*_args, **_kwargs):
        raise AssertionError("Version fallback attempted a repository-file read.")

    monkeypatch.setattr(version_module.metadata, "version", metadata_missing)
    monkeypatch.setattr(Path, "open", unexpected_open)

    assert version_module._get_version() == "0+unknown"


def test_distribution_gate_is_centralized_in_local_check_and_ci() -> None:
    local_check = (PROJECT_ROOT / "scripts" / "check.ps1").read_text(encoding="utf-8")
    ci_check = (PROJECT_ROOT / ".github" / "workflows" / "check.yml").read_text(encoding="utf-8")

    for content in (local_check, ci_check):
        assert content.count("scripts/sync_packaged_schemas.py --check") == 1
        assert content.count("scripts/validate_distribution_artifacts.py") == 1
