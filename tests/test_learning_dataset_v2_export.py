import hashlib
import json
from dataclasses import fields

from test_learning_corpus_human_evidence import _rich_snapshot, _store
from test_learning_dataset_v2 import _dataset

from skatmind.learning_corpus_identity import (
    build_learning_corpus_canonical_json_bytes_v1,
)
from skatmind.learning_dataset_v2_export import (
    LEARNING_DATASET_DOCUMENT_KIND,
    LEARNING_DATASET_EXPORT_VERSION,
    LearningDatasetExportV1,
    build_learning_dataset_v2_export_v1,
    serialize_learning_dataset_v2_export_v1,
)


def test_export_contract_identity_and_canonical_bytes_are_exact() -> None:
    _, snapshot = _rich_snapshot()
    dataset = _dataset(_store(snapshot, current=(snapshot,)), dataset_id="dataset-export")
    export = build_learning_dataset_v2_export_v1(dataset)
    assert LEARNING_DATASET_EXPORT_VERSION == 1
    assert LEARNING_DATASET_DOCUMENT_KIND == "skatmind_learning_dataset_v2"
    assert tuple(field.name for field in fields(LearningDatasetExportV1)) == (
        "learning_dataset_export_version",
        "document_kind",
        "export_id",
        "dataset_fingerprint",
        "learning_dataset",
    )
    assert export.dataset_fingerprint == dataset.dataset_fingerprint
    assert export.learning_dataset is dataset
    identity_material = {
        "learning_dataset_export_version": 1,
        "document_kind": "skatmind_learning_dataset_v2",
        "dataset_fingerprint": dataset.dataset_fingerprint,
        "learning_dataset": dataset.to_dict(),
    }
    assert export.export_id == hashlib.sha256(
        b"skatmind\0learning_dataset_v2_export_v1\0"
        + build_learning_corpus_canonical_json_bytes_v1(identity_material)
    ).hexdigest()
    first = serialize_learning_dataset_v2_export_v1(export)
    second = serialize_learning_dataset_v2_export_v1(export)
    assert first == second
    assert first == (
        json.dumps(
            export.to_dict(),
            ensure_ascii=True,
            allow_nan=False,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")
    assert first.endswith(b"\n") and not first.endswith(b"\n\n")
    assert b"\r" not in first and not first.startswith(b"\xef\xbb\xbf")
    assert json.loads(first)["learning_dataset"]["commentary_evidences"][0][
        "text"
    ].startswith("Überlegt")


def test_export_builder_wraps_existing_dataset_without_path_or_rebuild() -> None:
    dataset = _dataset(_store(), dataset_id="dataset-empty-export")
    export = build_learning_dataset_v2_export_v1(dataset)
    assert export.learning_dataset is dataset
    assert not {"path", "filename", "exported_at"}.intersection(export.to_dict())
