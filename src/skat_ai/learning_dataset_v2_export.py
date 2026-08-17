from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from skat_ai.learning_corpus_identity import (
    build_learning_corpus_canonical_json_bytes_v1,
)
from skat_ai.learning_dataset_v2_contracts import (
    LearningDatasetV2,
    _require_hash,
    _require_version,
    _validate_learning_dataset_v2,
)

LEARNING_DATASET_EXPORT_VERSION = 1
LEARNING_DATASET_DOCUMENT_KIND = "skat_ai_learning_dataset_v2"

_EXPORT_ID_DOMAIN = b"skat-ai\0learning_dataset_v2_export_v1\0"


def _build_export_id(dataset: LearningDatasetV2) -> str:
    material = {
        "learning_dataset_export_version": LEARNING_DATASET_EXPORT_VERSION,
        "document_kind": LEARNING_DATASET_DOCUMENT_KIND,
        "dataset_fingerprint": dataset.dataset_fingerprint,
        "learning_dataset": dataset.to_dict(),
    }
    return hashlib.sha256(
        _EXPORT_ID_DOMAIN + build_learning_corpus_canonical_json_bytes_v1(material)
    ).hexdigest()


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningDatasetExportV1:
    learning_dataset_export_version: int = LEARNING_DATASET_EXPORT_VERSION
    document_kind: str
    export_id: str
    dataset_fingerprint: str
    learning_dataset: LearningDatasetV2

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("LearningDatasetExportV1 must be constructed by its focused builder.")

    @classmethod
    def _from_validated(
        cls,
        *,
        export_id: str,
        dataset: LearningDatasetV2,
    ) -> LearningDatasetExportV1:
        value = object.__new__(cls)
        object.__setattr__(
            value,
            "learning_dataset_export_version",
            LEARNING_DATASET_EXPORT_VERSION,
        )
        object.__setattr__(value, "document_kind", LEARNING_DATASET_DOCUMENT_KIND)
        object.__setattr__(value, "export_id", export_id)
        object.__setattr__(value, "dataset_fingerprint", dataset.dataset_fingerprint)
        object.__setattr__(value, "learning_dataset", dataset)
        value._validate(verify_export_id=False, validate_dataset=False)
        return value

    def _validate(self, *, verify_export_id: bool, validate_dataset: bool) -> None:
        _require_version(
            self.learning_dataset_export_version,
            LEARNING_DATASET_EXPORT_VERSION,
            "learning_dataset_export_version",
        )
        if self.document_kind != LEARNING_DATASET_DOCUMENT_KIND:
            raise ValueError("document_kind must identify Learning Dataset version 2.")
        _require_hash(self.export_id, "export_id")
        _require_hash(self.dataset_fingerprint, "dataset_fingerprint")
        if validate_dataset:
            _validate_learning_dataset_v2(self.learning_dataset)
        if self.dataset_fingerprint != self.learning_dataset.dataset_fingerprint:
            raise ValueError("dataset_fingerprint must match the exact Learning Dataset.")
        if verify_export_id and self.export_id != _build_export_id(self.learning_dataset):
            raise ValueError("export_id must cover the exact export identity.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_dataset_export_version": self.learning_dataset_export_version,
            "document_kind": self.document_kind,
            "export_id": self.export_id,
            "dataset_fingerprint": self.dataset_fingerprint,
            "learning_dataset": self.learning_dataset.to_dict(),
        }


def build_learning_dataset_v2_export_v1(
    dataset: LearningDatasetV2,
) -> LearningDatasetExportV1:
    """Wraps one already-built Learning Dataset without rebuilding its sources."""
    _validate_learning_dataset_v2(dataset)
    return LearningDatasetExportV1._from_validated(
        export_id=_build_export_id(dataset),
        dataset=dataset,
    )


def serialize_learning_dataset_v2_export_v1(
    export: LearningDatasetExportV1,
) -> bytes:
    """Returns canonical private export bytes without accepting a path."""
    if type(export) is not LearningDatasetExportV1:
        raise ValueError("export must be an exact LearningDatasetExportV1.")
    export._validate(verify_export_id=False, validate_dataset=False)
    return (
        json.dumps(
            export.to_dict(),
            ensure_ascii=True,
            allow_nan=False,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")
