from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from skatmind.learning_corpus_identity import (
    build_learning_corpus_canonical_json_bytes_v1,
)
from skatmind.learning_corpus_strategy_teacher import (
    LearningCorpusStrategyTeacherEvidenceCollectionV1,
    _require_hash,
    _require_version,
    _validate_learning_corpus_strategy_teacher_collection_v1,
)

LEARNING_CORPUS_STRATEGY_TEACHER_EXPORT_VERSION = 1
LEARNING_CORPUS_STRATEGY_TEACHER_DOCUMENT_KIND = (
    "skatmind_learning_corpus_strategy_teacher_evidence"
)
LEARNING_CORPUS_STRATEGY_TEACHER_EXPORT_POLICY = (
    "deterministic_path_free_json_document"
)

_STRATEGY_TEACHER_EXPORT_ID_DOMAIN = (
    b"skatmind\0learning_corpus_strategy_teacher_export_v1\0"
)


def _build_export_id(
    collection: LearningCorpusStrategyTeacherEvidenceCollectionV1,
) -> str:
    if type(collection) is not LearningCorpusStrategyTeacherEvidenceCollectionV1:
        raise ValueError(
            "collection must be an exact "
            "LearningCorpusStrategyTeacherEvidenceCollectionV1."
        )
    material = {
        "learning_corpus_strategy_teacher_export_version": (
            LEARNING_CORPUS_STRATEGY_TEACHER_EXPORT_VERSION
        ),
        "document_kind": LEARNING_CORPUS_STRATEGY_TEACHER_DOCUMENT_KIND,
        "collection_fingerprint": (
            collection.strategy_teacher_collection_fingerprint
        ),
        "strategy_teacher_evidence": collection.to_dict(),
    }
    return hashlib.sha256(
        _STRATEGY_TEACHER_EXPORT_ID_DOMAIN
        + build_learning_corpus_canonical_json_bytes_v1(material)
    ).hexdigest()


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningCorpusStrategyTeacherEvidenceExportV1:
    """One private in-memory canonical Strategy Teacher Evidence export."""

    learning_corpus_strategy_teacher_export_version: int = (
        LEARNING_CORPUS_STRATEGY_TEACHER_EXPORT_VERSION
    )
    document_kind: str
    export_id: str
    collection_fingerprint: str
    strategy_teacher_evidence: LearningCorpusStrategyTeacherEvidenceCollectionV1

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "LearningCorpusStrategyTeacherEvidenceExportV1 must be constructed "
            "by its focused builder."
        )

    @classmethod
    def _from_validated(
        cls,
        *,
        export_id: str,
        collection: LearningCorpusStrategyTeacherEvidenceCollectionV1,
    ) -> LearningCorpusStrategyTeacherEvidenceExportV1:
        value = object.__new__(cls)
        object.__setattr__(
            value,
            "learning_corpus_strategy_teacher_export_version",
            LEARNING_CORPUS_STRATEGY_TEACHER_EXPORT_VERSION,
        )
        object.__setattr__(
            value,
            "document_kind",
            LEARNING_CORPUS_STRATEGY_TEACHER_DOCUMENT_KIND,
        )
        object.__setattr__(value, "export_id", export_id)
        object.__setattr__(
            value,
            "collection_fingerprint",
            collection.strategy_teacher_collection_fingerprint,
        )
        object.__setattr__(value, "strategy_teacher_evidence", collection)
        value._validate(verify_export_id=False, validate_collection=False)
        return value

    def _validate(
        self,
        *,
        verify_export_id: bool,
        validate_collection: bool,
    ) -> None:
        _require_version(
            self.learning_corpus_strategy_teacher_export_version,
            LEARNING_CORPUS_STRATEGY_TEACHER_EXPORT_VERSION,
            "learning_corpus_strategy_teacher_export_version",
        )
        if self.document_kind != LEARNING_CORPUS_STRATEGY_TEACHER_DOCUMENT_KIND:
            raise ValueError("document_kind must identify Strategy Teacher Evidence.")
        _require_hash(self.export_id, "export_id")
        _require_hash(self.collection_fingerprint, "collection_fingerprint")
        if validate_collection:
            _validate_learning_corpus_strategy_teacher_collection_v1(
                self.strategy_teacher_evidence
            )
        if self.collection_fingerprint != (
            self.strategy_teacher_evidence.strategy_teacher_collection_fingerprint
        ):
            raise ValueError(
                "collection_fingerprint must match Strategy Teacher Evidence."
            )
        if verify_export_id and self.export_id != _build_export_id(
            self.strategy_teacher_evidence
        ):
            raise ValueError("export_id must cover the exact export identity.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_corpus_strategy_teacher_export_version": (
                self.learning_corpus_strategy_teacher_export_version
            ),
            "document_kind": self.document_kind,
            "export_id": self.export_id,
            "collection_fingerprint": self.collection_fingerprint,
            "strategy_teacher_evidence": self.strategy_teacher_evidence.to_dict(),
        }


def build_learning_corpus_strategy_teacher_evidence_export_v1(
    collection: LearningCorpusStrategyTeacherEvidenceCollectionV1,
) -> LearningCorpusStrategyTeacherEvidenceExportV1:
    """Wraps one already-built collection without rebuilding its sources."""
    _validate_learning_corpus_strategy_teacher_collection_v1(collection)
    return LearningCorpusStrategyTeacherEvidenceExportV1._from_validated(
        export_id=_build_export_id(collection),
        collection=collection,
    )


def serialize_learning_corpus_strategy_teacher_evidence_export_v1(
    export: LearningCorpusStrategyTeacherEvidenceExportV1,
) -> bytes:
    """Returns canonical private export bytes without accepting a path."""
    if type(export) is not LearningCorpusStrategyTeacherEvidenceExportV1:
        raise ValueError(
            "export must be an exact "
            "LearningCorpusStrategyTeacherEvidenceExportV1."
        )
    export._validate(verify_export_id=False, validate_collection=False)
    return (
        json.dumps(
            export.to_dict(),
            ensure_ascii=True,
            allow_nan=False,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")
