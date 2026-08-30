import base64
import csv
import hashlib
import importlib.metadata
import io
import os
import subprocess
import sys
import tarfile
import tomllib
import zipfile
from email import policy
from email.message import Message
from email.parser import BytesParser
from pathlib import Path, PurePosixPath

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LICENSE_EXPRESSION = "AGPL-3.0-only"
LICENSE_FILES = ("LICENSE", "COPYRIGHT")
LICENSE_SHA256 = "d8a6cc31abc16b6748c7a21f21611f5a1ec33f67d22ca23d7da1c19b95496bee"
COPYRIGHT_BYTES = b"Copyright (C) 2026 Henning Wiese\n"


def _parse_metadata(content: bytes) -> Message:
    return BytesParser(policy=policy.default).parsebytes(content)


def _assert_license_metadata(metadata: Message) -> None:
    metadata_version = tuple(int(part) for part in metadata["Metadata-Version"].split("."))
    assert metadata_version >= (2, 4)
    assert metadata.get_all("License-Expression", []) == [LICENSE_EXPRESSION]
    assert metadata.get_all("License-File", []) == list(LICENSE_FILES)
    assert metadata.get_all("License", []) == []
    assert metadata.get_all("Classifier", []) == []
    assert "AGPL-3.0-or-later" not in metadata.as_string()


@pytest.fixture(scope="module")
def focused_license_artifacts(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    temporary_root = tmp_path_factory.mktemp("v1-package-license")
    metadata = (
        "Metadata-Version: 2.4\n"
        "Name: skatmind\n"
        "Version: 0.17.0\n"
        f"License-Expression: {LICENSE_EXPRESSION}\n"
        f"License-File: {LICENSE_FILES[0]}\n"
        f"License-File: {LICENSE_FILES[1]}\n"
        "\n"
    ).encode()
    legal_files = {name: (PROJECT_ROOT / name).read_bytes() for name in LICENSE_FILES}

    wheel = temporary_root / "skatmind-0.17.0-py3-none-any.whl"
    dist_info = "skatmind-0.17.0.dist-info"
    wheel_members = {
        f"{dist_info}/METADATA": metadata,
        f"{dist_info}/WHEEL": (
            b"Wheel-Version: 1.0\nGenerator: license-test\n"
            b"Root-Is-Purelib: true\nTag: py3-none-any\n\n"
        ),
        **{f"{dist_info}/licenses/{name}": content for name, content in legal_files.items()},
    }
    record_buffer = io.StringIO(newline="")
    record_writer = csv.writer(record_buffer, lineterminator="\n")
    for name, content in wheel_members.items():
        digest = base64.urlsafe_b64encode(hashlib.sha256(content).digest()).rstrip(b"=").decode()
        record_writer.writerow((name, f"sha256={digest}", len(content)))
    record_name = f"{dist_info}/RECORD"
    record_writer.writerow((record_name, "", ""))
    wheel_members[record_name] = record_buffer.getvalue().encode()
    with zipfile.ZipFile(wheel, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in wheel_members.items():
            archive.writestr(name, content)

    sdist = temporary_root / "skatmind-0.17.0.tar.gz"
    sdist_root = "skatmind-0.17.0"
    sdist_members = {
        f"{sdist_root}/PKG-INFO": metadata,
        **{f"{sdist_root}/{name}": content for name, content in legal_files.items()},
    }
    with tarfile.open(sdist, "w:gz") as archive:
        for name, content in sdist_members.items():
            member = tarfile.TarInfo(name)
            member.size = len(content)
            archive.addfile(member, io.BytesIO(content))

    return wheel, sdist


def test_repository_legal_files_are_exact_canonical_bytes() -> None:
    license_content = (PROJECT_ROOT / "LICENSE").read_bytes()
    copyright_content = (PROJECT_ROOT / "COPYRIGHT").read_bytes()

    assert hashlib.sha256(license_content).hexdigest() == LICENSE_SHA256
    assert copyright_content == COPYRIGHT_BYTES
    for content in (license_content, copyright_content):
        assert not content.startswith(b"\xef\xbb\xbf")
        assert b"\r" not in content
        assert content.endswith(b"\n")
        assert not content.endswith(b"\n\n")
        content.decode("utf-8")


def test_pep_639_source_metadata_preserves_the_package_baseline() -> None:
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = pyproject["project"]

    assert project["license"] == LICENSE_EXPRESSION
    assert isinstance(project["license"], str)
    assert project["license-files"] == list(LICENSE_FILES)
    assert "AGPL-3.0-or-later" not in project.values()
    assert "classifiers" not in project
    assert "authors" not in project
    assert "urls" not in project
    assert pyproject["build-system"] == {
        "requires": ["setuptools>=77.0.3"],
        "build-backend": "setuptools.build_meta",
    }
    assert project["dependencies"] == [
        "jsonschema>=4.23.0",
        "referencing>=0.31.0",
    ]
    assert project["optional-dependencies"]["dev"] == [
        "build>=1.2.2",
        "pytest>=9.0.0",
        "ruff>=0.14.0",
    ]
    assert pyproject["tool"]["setuptools"]["package-data"] == {
        "skatmind": ["py.typed"],
        "skatmind.schema_resources": ["*.schema.json"],
        "skatmind.capture_web": ["templates/*.html", "assets/*.css", "assets/*.js"],
        "skatmind.corpus_web": ["templates/*.html", "assets/*.css", "assets/*.js"],
        "skatmind.app_web": ["templates/*.html", "assets/*.css", "assets/*.js"],
    }
    assert project["scripts"] == {"skatmind": "skatmind.cli:main"}


def test_wheel_has_exact_pep_639_metadata_files_and_record(
    focused_license_artifacts: tuple[Path, Path],
) -> None:
    wheel, _sdist = focused_license_artifacts
    expected_content = {name: (PROJECT_ROOT / name).read_bytes() for name in LICENSE_FILES}
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        dist_info = next(name.split("/", 1)[0] for name in names if ".dist-info/" in name)
        _assert_license_metadata(_parse_metadata(archive.read(f"{dist_info}/METADATA")))

        expected_paths = {f"{dist_info}/licenses/{name}" for name in LICENSE_FILES}
        actual_paths = {
            name
            for name in names
            if name.startswith(f"{dist_info}/licenses/") and not name.endswith("/")
        }
        assert actual_paths == expected_paths
        for name, content in expected_content.items():
            assert archive.read(f"{dist_info}/licenses/{name}") == content
            assert [path for path in names if PurePosixPath(path).name == name] == [
                f"{dist_info}/licenses/{name}"
            ]

        record_name = f"{dist_info}/RECORD"
        record = {
            row[0]: row[1:] for row in csv.reader(io.StringIO(archive.read(record_name).decode()))
        }
        for path in expected_paths:
            content = archive.read(path)
            digest = (
                base64.urlsafe_b64encode(hashlib.sha256(content).digest()).rstrip(b"=").decode()
            )
            assert record[path] == [f"sha256={digest}", str(len(content))]


def test_sdist_has_exact_pep_639_metadata_and_root_files(
    focused_license_artifacts: tuple[Path, Path],
) -> None:
    _wheel, sdist = focused_license_artifacts
    with tarfile.open(sdist, "r:gz") as archive:
        members = {member.name: member for member in archive.getmembers()}
        root = next(iter({PurePosixPath(name).parts[0] for name in members}))
        pkg_info = archive.extractfile(members[f"{root}/PKG-INFO"])
        assert pkg_info is not None
        _assert_license_metadata(_parse_metadata(pkg_info.read()))
        for name in LICENSE_FILES:
            path = f"{root}/{name}"
            extracted = archive.extractfile(members[path])
            assert extracted is not None
            assert extracted.read() == (PROJECT_ROOT / name).read_bytes()
            assert [item for item in members if PurePosixPath(item).name == name] == [path]


def test_target_install_has_exact_metadata_and_legal_files(
    focused_license_artifacts: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    wheel, _sdist = focused_license_artifacts
    target = tmp_path / "installed"
    environment = os.environ.copy()
    environment["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    environment["PIP_NO_INDEX"] = "1"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-index",
            "--no-deps",
            "--target",
            str(target),
            str(wheel),
        ],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
    distributions = [
        distribution
        for distribution in importlib.metadata.distributions(path=[str(target)])
        if distribution.metadata["Name"] == "skatmind"
    ]
    assert len(distributions) == 1
    distribution = distributions[0]
    _assert_license_metadata(distribution.metadata)

    license_entries = {}
    for entry in distribution.files or ():
        path = PurePosixPath(str(entry).replace("\\", "/"))
        if (
            len(path.parts) == 3
            and path.parts[0].endswith(".dist-info")
            and path.parts[1] == "licenses"
        ):
            license_entries[path.parts[2]] = entry
    assert set(license_entries) == set(LICENSE_FILES)
    for name, entry in license_entries.items():
        assert (
            Path(distribution.locate_file(entry)).read_bytes() == (PROJECT_ROOT / name).read_bytes()
        )


def test_documented_dependency_and_bundled_asset_audit_is_complete() -> None:
    documentation = (PROJECT_ROOT / "docs" / "v1_package_license.md").read_text(encoding="utf-8")
    for expected in (
        "setuptools>=77.0.3",
        "jsonschema>=4.23.0",
        "referencing>=0.31.0",
        "build>=1.2.2",
        "pytest>=9.0.0",
        "ruff>=0.14.0",
        "Python source",
        "JSON Schemas",
        "Capture HTML/CSS/JavaScript",
        "Corpus HTML/CSS/JavaScript",
        "Application-shell HTML/CSS",
        "benchmark fixtures",
        "examples",
        "documentation assets",
        "AGPL-3.0-only",
        "minimum-supported",
        "B-05",
    ):
        assert expected in documentation
