import ast
import builtins
import hashlib
import json
import tomllib
from dataclasses import FrozenInstanceError, fields
from pathlib import Path

import pytest
from test_learning_corpus_human_evidence import _store
from test_learning_corpus_strategy_teacher import _changed_report, _source_bundle

import skat_ai
import skat_ai.api.v1 as api_v1
import skat_ai.cli as cli
import skat_ai.learning_corpus_strategy_teacher_builder as builder_module
from scripts.validate_generated_outputs_schema import SCENARIOS
from skat_ai.api.v1.contracts import WorkflowV1
from skat_ai.learning_corpus_identity import (
    build_learning_corpus_canonical_json_bytes_v1,
)
from skat_ai.learning_corpus_strategy_teacher import (
    LearningCorpusStrategyTeacherEvidenceCollectionV1,
    build_learning_corpus_strategy_teacher_report_source_v1,
)
from skat_ai.learning_corpus_strategy_teacher_builder import (
    build_learning_corpus_strategy_teacher_evidence_collection_v1,
)
from skat_ai.learning_corpus_strategy_teacher_export import (
    LEARNING_CORPUS_STRATEGY_TEACHER_DOCUMENT_KIND,
    LEARNING_CORPUS_STRATEGY_TEACHER_EXPORT_POLICY,
    LEARNING_CORPUS_STRATEGY_TEACHER_EXPORT_VERSION,
    LearningCorpusStrategyTeacherEvidenceExportV1,
    build_learning_corpus_strategy_teacher_evidence_export_v1,
    serialize_learning_corpus_strategy_teacher_evidence_export_v1,
)
from skat_ai.training_dataset import (
    TRAINING_DATASET_SCHEMA_VERSION,
    TRAINING_FEATURE_GENERATION_VERSION,
    TRAINING_TARGET,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _hash(domain: bytes, value: object) -> str:
    return hashlib.sha256(
        domain + build_learning_corpus_canonical_json_bytes_v1(value)
    ).hexdigest()


@pytest.fixture(scope="module")
def collection():
    *_unused, source, store = _source_bundle(match_id="match-export")
    return build_learning_corpus_strategy_teacher_evidence_collection_v1(
        store,
        (source,),
    )


def test_export_contract_fields_and_identity_are_exact(collection) -> None:
    assert LEARNING_CORPUS_STRATEGY_TEACHER_EXPORT_VERSION == 1
    assert LEARNING_CORPUS_STRATEGY_TEACHER_DOCUMENT_KIND == (
        "skat_ai_learning_corpus_strategy_teacher_evidence"
    )
    assert (
        LEARNING_CORPUS_STRATEGY_TEACHER_EXPORT_POLICY
        == "deterministic_path_free_json_document"
    )
    assert tuple(
        field.name for field in fields(LearningCorpusStrategyTeacherEvidenceExportV1)
    ) == (
        "learning_corpus_strategy_teacher_export_version",
        "document_kind",
        "export_id",
        "collection_fingerprint",
        "strategy_teacher_evidence",
    )
    export = build_learning_corpus_strategy_teacher_evidence_export_v1(collection)
    assert export.strategy_teacher_evidence is collection
    assert export.collection_fingerprint == (
        collection.strategy_teacher_collection_fingerprint
    )
    assert export.export_id == _hash(
        b"skat-ai\0learning_corpus_strategy_teacher_export_v1\0",
        {
            "learning_corpus_strategy_teacher_export_version": 1,
            "document_kind": LEARNING_CORPUS_STRATEGY_TEACHER_DOCUMENT_KIND,
            "collection_fingerprint": (
                collection.strategy_teacher_collection_fingerprint
            ),
            "strategy_teacher_evidence": collection.to_dict(),
        },
    )


def test_empty_export_is_valid_and_deterministic() -> None:
    collection = build_learning_corpus_strategy_teacher_evidence_collection_v1(
        _store(),
        (),
    )
    first = build_learning_corpus_strategy_teacher_evidence_export_v1(collection)
    second = build_learning_corpus_strategy_teacher_evidence_export_v1(collection)
    assert first == second
    assert first.to_dict()["strategy_teacher_evidence"]["evidences"] == []


def test_export_is_frozen_slotted_builder_controlled_and_defensive(
    collection,
) -> None:
    export = build_learning_corpus_strategy_teacher_evidence_export_v1(collection)
    assert not hasattr(export, "__dict__")
    with pytest.raises(FrozenInstanceError):
        export.export_id = "0" * 64
    with pytest.raises(TypeError):
        LearningCorpusStrategyTeacherEvidenceExportV1()
    changed = export.to_dict()
    changed["strategy_teacher_evidence"]["evidences"][0][
        "strategic_summary"
    ] = "Changed"
    assert export.to_dict()["strategy_teacher_evidence"]["evidences"][0][
        "strategic_summary"
    ] != "Changed"


def test_export_builder_uses_existing_collection_without_rebuilding(
    collection,
    monkeypatch,
) -> None:
    def fail(*_args, **_kwargs):
        raise AssertionError("Export must not rebuild Strategy Teacher Evidence.")

    monkeypatch.setattr(
        builder_module,
        "build_learning_corpus_strategy_teacher_evidence_collection_v1",
        fail,
    )
    export = build_learning_corpus_strategy_teacher_evidence_export_v1(collection)
    assert export.strategy_teacher_evidence is collection
    with pytest.raises(TypeError):
        build_learning_corpus_strategy_teacher_evidence_export_v1(
            collection,
            "output.json",
        )


def test_canonical_serialization_is_ascii_utf8_two_space_lf_and_path_free(
    collection,
    monkeypatch,
) -> None:
    export = build_learning_corpus_strategy_teacher_evidence_export_v1(collection)
    expected = (
        json.dumps(
            export.to_dict(),
            ensure_ascii=True,
            allow_nan=False,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")
    monkeypatch.setattr(
        builtins,
        "open",
        lambda *_args, **_kwargs: pytest.fail("Serialization must perform no I/O."),
    )
    actual = serialize_learning_corpus_strategy_teacher_evidence_export_v1(export)
    assert actual == expected
    assert b"\r\n" not in actual
    assert actual.endswith(b"\n") and not actual.endswith(b"\n\n")
    with pytest.raises(TypeError):
        serialize_learning_corpus_strategy_teacher_evidence_export_v1(
            export,
            "output.json",
        )


def test_mapping_order_does_not_change_export_identity_or_bytes() -> None:
    _workspace, snapshot, result, _report, source, store = _source_bundle(
        match_id="match-mapping-order"
    )
    reordered_document = result.result.to_dict()["document"]
    reordered_document["settings"] = dict(
        reversed(tuple(reordered_document["settings"].items()))
    )
    reordered_source = build_learning_corpus_strategy_teacher_report_source_v1(
        match_snapshot_id=snapshot.match_snapshot_id,
        report=_changed_report(result, result_document=reordered_document),
    )
    first_collection = build_learning_corpus_strategy_teacher_evidence_collection_v1(
        store,
        (source,),
    )
    second_collection = build_learning_corpus_strategy_teacher_evidence_collection_v1(
        store,
        (reordered_source,),
    )
    first = build_learning_corpus_strategy_teacher_evidence_export_v1(
        first_collection
    )
    second = build_learning_corpus_strategy_teacher_evidence_export_v1(
        second_collection
    )
    assert first.export_id == second.export_id
    assert serialize_learning_corpus_strategy_teacher_evidence_export_v1(first) == (
        serialize_learning_corpus_strategy_teacher_evidence_export_v1(second)
    )


def test_forged_collection_fingerprint_is_rejected(collection) -> None:
    object.__setattr__(
        collection,
        "strategy_teacher_collection_fingerprint",
        "0" * 64,
    )
    with pytest.raises(ValueError, match="strategy_teacher_collection_fingerprint"):
        build_learning_corpus_strategy_teacher_evidence_export_v1(collection)


def test_strategy_teacher_modules_do_not_import_forbidden_boundaries() -> None:
    forbidden = (
        "pathlib",
        "skat_ai.capture_web",
        "skat_ai.cli",
        "skat_ai.learning_corpus_human_evidence",
        "skat_ai.learning_corpus_player_catalog",
        "skat_ai.match_historical_analysis",
        "skat_ai.replay_coaching",
        "skat_ai.training_dataset",
    )
    paths = tuple(
        PROJECT_ROOT.glob("src/skat_ai/learning_corpus_strategy_teacher*.py")
    )
    violations = []
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            modules = ()
            if isinstance(node, ast.Import):
                modules = tuple(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                modules = (node.module,)
            for module in modules:
                if module.startswith(forbidden):
                    violations.append((path.name, node.lineno, module))
    assert violations == []


def test_strategy_teacher_remains_private_and_baselines_are_unchanged() -> None:
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text())
    assert pyproject["project"]["version"] == "0.16.0"
    assert pyproject["project"]["requires-python"] == ">=3.13"
    assert pyproject["project"]["scripts"] == {"skat-ai": "skat_ai.cli:main"}
    assert TRAINING_DATASET_SCHEMA_VERSION == 1
    assert TRAINING_FEATURE_GENERATION_VERSION == 1
    assert TRAINING_TARGET == "actual_card_played"
    assert len(WorkflowV1) == 7
    assert len(SCENARIOS) == 88
    assert len(tuple((PROJECT_ROOT / "schemas").glob("*.schema.json"))) == 65
    assert len(
        tuple((PROJECT_ROOT / "src/skat_ai/schema_resources").glob("*.schema.json"))
    ) == 65
    assert len(tuple((PROJECT_ROOT / "examples").glob("session_*.json"))) == 6
    assert not tuple((PROJECT_ROOT / "schemas").glob("*strategy_teacher*.json"))
    for namespace in (skat_ai, api_v1, cli):
        assert not hasattr(
            namespace,
            "LearningCorpusStrategyTeacherEvidenceCollectionV1",
        )
        assert not hasattr(
            namespace,
            "build_learning_corpus_strategy_teacher_evidence_export_v1",
        )
    assert LearningCorpusStrategyTeacherEvidenceCollectionV1.__module__ == (
        "skat_ai.learning_corpus_strategy_teacher"
    )
