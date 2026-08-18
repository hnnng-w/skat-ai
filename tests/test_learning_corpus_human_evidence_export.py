import builtins
import hashlib
import json
import tomllib
from dataclasses import FrozenInstanceError, fields
from pathlib import Path

import pytest
from test_learning_corpus_human_evidence import _rich_collection, _store

import skat_ai
import skat_ai.api.v1 as api_v1
import skat_ai.cli as cli
import skat_ai.learning_corpus_human_evidence_builder as builder_module
import skat_ai.learning_corpus_human_evidence_export as export_module
from scripts.validate_generated_outputs_schema import SCENARIOS
from skat_ai.api.v1.contracts import WorkflowV1
from skat_ai.learning_corpus_human_evidence import (
    LearningCorpusHumanEvidenceCollectionV1,
)
from skat_ai.learning_corpus_human_evidence_builder import (
    build_learning_corpus_human_evidence_collection_v1,
)
from skat_ai.learning_corpus_human_evidence_export import (
    LEARNING_CORPUS_HUMAN_EVIDENCE_DOCUMENT_KIND,
    LEARNING_CORPUS_HUMAN_EVIDENCE_EXPORT_POLICY,
    LEARNING_CORPUS_HUMAN_EVIDENCE_EXPORT_VERSION,
    LearningCorpusHumanEvidenceExportV1,
    build_learning_corpus_human_evidence_export_v1,
    serialize_learning_corpus_human_evidence_export_v1,
)
from skat_ai.learning_corpus_identity import (
    build_learning_corpus_canonical_json_bytes_v1,
)
from skat_ai.training_dataset import (
    TRAINING_DATASET_SCHEMA_VERSION,
    TRAINING_FEATURE_GENERATION_VERSION,
    TRAINING_TARGET,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _hash(domain: bytes, value: object) -> str:
    return hashlib.sha256(domain + build_learning_corpus_canonical_json_bytes_v1(value)).hexdigest()


def test_export_version_document_kind_and_fields_are_exact() -> None:
    assert LEARNING_CORPUS_HUMAN_EVIDENCE_EXPORT_VERSION == 1
    assert LEARNING_CORPUS_HUMAN_EVIDENCE_DOCUMENT_KIND == (
        "skat_ai_learning_corpus_human_evidence"
    )
    assert LEARNING_CORPUS_HUMAN_EVIDENCE_EXPORT_POLICY == ("deterministic_path_free_json_document")
    assert tuple(field.name for field in fields(LearningCorpusHumanEvidenceExportV1)) == (
        "learning_corpus_human_evidence_export_version",
        "document_kind",
        "export_id",
        "collection_fingerprint",
        "human_evidence",
    )


def test_empty_collection_export_is_valid_deterministic_and_identity_scoped() -> None:
    collection = build_learning_corpus_human_evidence_collection_v1(_store())
    first = build_learning_corpus_human_evidence_export_v1(collection)
    second = build_learning_corpus_human_evidence_export_v1(collection)
    assert first == second
    assert first.human_evidence is collection
    assert first.collection_fingerprint == (collection.human_evidence_collection_fingerprint)
    assert first.export_id == _hash(
        b"skat-ai\0learning_corpus_human_evidence_export_v1\0",
        {
            "learning_corpus_human_evidence_export_version": 1,
            "document_kind": "skat_ai_learning_corpus_human_evidence",
            "collection_fingerprint": (collection.human_evidence_collection_fingerprint),
            "human_evidence": collection.to_dict(),
        },
    )
    assert first.to_dict()["human_evidence"]["games"] == []


def test_export_builder_uses_already_built_collection_without_rebuilding(
    monkeypatch,
) -> None:
    collection, _ = _rich_collection()

    def fail(*_args, **_kwargs):
        raise AssertionError("Export builder must not rebuild Human Evidence.")

    monkeypatch.setattr(
        builder_module,
        "build_learning_corpus_human_evidence_collection_v1",
        fail,
    )
    export = build_learning_corpus_human_evidence_export_v1(collection)
    assert export.human_evidence is collection
    with pytest.raises(TypeError):
        build_learning_corpus_human_evidence_export_v1(collection, "output.json")


def test_export_id_is_computed_once_by_export_builder(monkeypatch) -> None:
    collection, _ = _rich_collection()
    calls = 0
    original = export_module._build_export_id

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(export_module, "_build_export_id", counted)
    build_learning_corpus_human_evidence_export_v1(collection)
    assert calls == 1


def test_export_builder_validates_collection_once(monkeypatch) -> None:
    collection, _ = _rich_collection()
    calls = 0
    original = export_module._validate_learning_corpus_human_evidence_collection_v1

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(
        export_module,
        "_validate_learning_corpus_human_evidence_collection_v1",
        counted,
    )
    build_learning_corpus_human_evidence_export_v1(collection)
    assert calls == 1


def test_canonical_serialization_is_utf8_ascii_finite_two_space_lf_and_defensive() -> None:
    collection, _ = _rich_collection()
    export = build_learning_corpus_human_evidence_export_v1(collection)
    expected = (
        json.dumps(
            export.to_dict(),
            ensure_ascii=True,
            allow_nan=False,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")
    actual = serialize_learning_corpus_human_evidence_export_v1(export)
    assert actual == expected
    assert b"\r\n" not in actual
    assert actual.endswith(b"\n") and not actual.endswith(b"\n\n")
    assert b"\\u00dcberlegt" in actual
    assert json.loads(actual)["human_evidence"] == collection.to_dict()
    changed = export.to_dict()
    changed["human_evidence"]["commentaries"][0]["text"] = "Changed"
    assert export.to_dict()["human_evidence"]["commentaries"][0]["text"] != ("Changed")


def test_serialization_performs_one_json_serialization_without_identity_rebuild(
    monkeypatch,
) -> None:
    collection, _ = _rich_collection()
    export = build_learning_corpus_human_evidence_export_v1(collection)
    calls = 0
    original_dumps = export_module.json.dumps

    def counted_dumps(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original_dumps(*args, **kwargs)

    def fail(*_args, **_kwargs):
        raise AssertionError("Serialization must not rebuild an identity.")

    monkeypatch.setattr(export_module.json, "dumps", counted_dumps)
    monkeypatch.setattr(export_module, "_build_export_id", fail)
    monkeypatch.setattr(
        export_module,
        "_validate_learning_corpus_human_evidence_collection_v1",
        fail,
    )
    assert serialize_learning_corpus_human_evidence_export_v1(export).startswith(b"{")
    assert calls == 1


def test_serialization_performs_no_file_io_and_accepts_no_path(monkeypatch) -> None:
    collection, _ = _rich_collection()
    export = build_learning_corpus_human_evidence_export_v1(collection)
    monkeypatch.setattr(
        builtins,
        "open",
        lambda *_args, **_kwargs: pytest.fail("Serialization must perform no file I/O."),
    )
    assert serialize_learning_corpus_human_evidence_export_v1(export).startswith(b"{")
    with pytest.raises(TypeError):
        serialize_learning_corpus_human_evidence_export_v1(export, "output.json")


def test_export_rejects_a_forged_collection_fingerprint() -> None:
    collection, _ = _rich_collection()
    object.__setattr__(
        collection,
        "human_evidence_collection_fingerprint",
        "0" * 64,
    )
    with pytest.raises(ValueError, match="human_evidence_collection_fingerprint"):
        build_learning_corpus_human_evidence_export_v1(collection)


@pytest.mark.parametrize(
    ("child_kind", "field_name", "message"),
    (
        ("commentary", "game_reference_id", "parent Game"),
        ("response", "commentary_evidence_id", "Game and Commentary parents"),
    ),
)
def test_export_rejects_orphaned_child_references(
    child_kind: str,
    field_name: str,
    message: str,
) -> None:
    collection, _ = _rich_collection()
    child = collection.commentaries[0] if child_kind == "commentary" else collection.responses[0]
    object.__setattr__(child, field_name, "0" * 64)
    with pytest.raises(ValueError, match=message):
        build_learning_corpus_human_evidence_export_v1(collection)


def test_export_remains_private_and_compatibility_baselines_are_unchanged() -> None:
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text())
    assert pyproject["project"]["version"] == "0.16.0"
    assert pyproject["project"]["requires-python"] == ">=3.13"
    assert pyproject["project"]["scripts"] == {"skat-ai": "skat_ai.cli:main"}
    assert TRAINING_DATASET_SCHEMA_VERSION == 1
    assert TRAINING_FEATURE_GENERATION_VERSION == 1
    assert TRAINING_TARGET == "actual_card_played"
    assert len(WorkflowV1) == 7
    assert len(SCENARIOS) == 85
    assert len(tuple((PROJECT_ROOT / "schemas").glob("*.schema.json"))) == 63
    assert len(tuple((PROJECT_ROOT / "src/skat_ai/schema_resources").glob("*.schema.json"))) == 63
    assert len(tuple((PROJECT_ROOT / "examples").glob("session_*.json"))) == 6
    assert not tuple((PROJECT_ROOT / "schemas").glob("*human_evidence*.schema.json"))
    for namespace in (skat_ai, api_v1, cli):
        assert not hasattr(namespace, "LearningCorpusHumanEvidenceCollectionV1")
        assert not hasattr(
            namespace,
            "build_learning_corpus_human_evidence_export_v1",
        )


def test_export_value_is_frozen_slotted_and_builder_controlled() -> None:
    collection, _ = _rich_collection()
    export = build_learning_corpus_human_evidence_export_v1(collection)
    assert not hasattr(export, "__dict__")
    with pytest.raises(FrozenInstanceError):
        export.export_id = "0" * 64
    with pytest.raises(TypeError):
        LearningCorpusHumanEvidenceExportV1()
    with pytest.raises(ValueError, match="exact LearningCorpusHumanEvidenceCollectionV1"):
        build_learning_corpus_human_evidence_export_v1(object())
    with pytest.raises(ValueError, match="exact LearningCorpusHumanEvidenceExportV1"):
        serialize_learning_corpus_human_evidence_export_v1(object())


def test_human_evidence_type_is_not_added_to_public_annotations() -> None:
    assert "LearningCorpusHumanEvidenceCollectionV1" not in getattr(
        skat_ai,
        "__annotations__",
        {},
    )
    assert "LearningCorpusHumanEvidenceCollectionV1" not in getattr(
        api_v1,
        "__annotations__",
        {},
    )
    assert LearningCorpusHumanEvidenceCollectionV1.__module__ == (
        "skat_ai.learning_corpus_human_evidence"
    )
