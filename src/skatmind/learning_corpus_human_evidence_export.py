from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from skatmind.learning_corpus_human_evidence import (
    LearningCorpusHumanEvidenceCollectionV1,
    _require_hash,
    _require_version,
    _validate_learning_corpus_human_evidence_collection_v1,
)
from skatmind.learning_corpus_identity import (
    build_learning_corpus_canonical_json_bytes_v1,
)

LEARNING_CORPUS_HUMAN_EVIDENCE_EXPORT_VERSION = 1
LEARNING_CORPUS_HUMAN_EVIDENCE_DOCUMENT_KIND = "skatmind_learning_corpus_human_evidence"
LEARNING_CORPUS_HUMAN_EVIDENCE_EXPORT_POLICY = "deterministic_path_free_json_document"

_HUMAN_EVIDENCE_EXPORT_ID_DOMAIN = b"skatmind\0learning_corpus_human_evidence_export_v1\0"


def _build_export_id(human_evidence: LearningCorpusHumanEvidenceCollectionV1) -> str:
    if type(human_evidence) is not LearningCorpusHumanEvidenceCollectionV1:
        raise ValueError("human_evidence must be an exact LearningCorpusHumanEvidenceCollectionV1.")
    material = {
        "learning_corpus_human_evidence_export_version": (
            LEARNING_CORPUS_HUMAN_EVIDENCE_EXPORT_VERSION
        ),
        "document_kind": LEARNING_CORPUS_HUMAN_EVIDENCE_DOCUMENT_KIND,
        "collection_fingerprint": (human_evidence.human_evidence_collection_fingerprint),
        "human_evidence": human_evidence.to_dict(),
    }
    return hashlib.sha256(
        _HUMAN_EVIDENCE_EXPORT_ID_DOMAIN + build_learning_corpus_canonical_json_bytes_v1(material)
    ).hexdigest()


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningCorpusHumanEvidenceExportV1:
    """One private in-memory canonical Human Evidence export document."""

    learning_corpus_human_evidence_export_version: int = (
        LEARNING_CORPUS_HUMAN_EVIDENCE_EXPORT_VERSION
    )
    document_kind: str
    export_id: str
    collection_fingerprint: str
    human_evidence: LearningCorpusHumanEvidenceCollectionV1

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "LearningCorpusHumanEvidenceExportV1 must be constructed by its focused builder."
        )

    @classmethod
    def _from_validated(
        cls,
        *,
        export_id: str,
        human_evidence: LearningCorpusHumanEvidenceCollectionV1,
    ) -> LearningCorpusHumanEvidenceExportV1:
        value = object.__new__(cls)
        object.__setattr__(
            value,
            "learning_corpus_human_evidence_export_version",
            LEARNING_CORPUS_HUMAN_EVIDENCE_EXPORT_VERSION,
        )
        object.__setattr__(
            value,
            "document_kind",
            LEARNING_CORPUS_HUMAN_EVIDENCE_DOCUMENT_KIND,
        )
        object.__setattr__(value, "export_id", export_id)
        object.__setattr__(
            value,
            "collection_fingerprint",
            human_evidence.human_evidence_collection_fingerprint,
        )
        object.__setattr__(value, "human_evidence", human_evidence)
        value._validate(verify_export_id=False, validate_collection=False)
        return value

    def _validate(
        self,
        *,
        verify_export_id: bool,
        validate_collection: bool,
    ) -> None:
        _require_version(
            self.learning_corpus_human_evidence_export_version,
            LEARNING_CORPUS_HUMAN_EVIDENCE_EXPORT_VERSION,
            "learning_corpus_human_evidence_export_version",
        )
        if self.document_kind != LEARNING_CORPUS_HUMAN_EVIDENCE_DOCUMENT_KIND:
            raise ValueError("document_kind must identify Human Evidence.")
        _require_hash(self.export_id, "export_id")
        _require_hash(self.collection_fingerprint, "collection_fingerprint")
        if validate_collection:
            _validate_learning_corpus_human_evidence_collection_v1(self.human_evidence)
        if self.collection_fingerprint != self.human_evidence.human_evidence_collection_fingerprint:
            raise ValueError("collection_fingerprint must match Human Evidence.")
        if verify_export_id and self.export_id != _build_export_id(self.human_evidence):
            raise ValueError("export_id must cover the exact export identity.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_corpus_human_evidence_export_version": (
                self.learning_corpus_human_evidence_export_version
            ),
            "document_kind": self.document_kind,
            "export_id": self.export_id,
            "collection_fingerprint": self.collection_fingerprint,
            "human_evidence": self.human_evidence.to_dict(),
        }


def build_learning_corpus_human_evidence_export_v1(
    human_evidence: LearningCorpusHumanEvidenceCollectionV1,
) -> LearningCorpusHumanEvidenceExportV1:
    """Wraps one already built collection without rebuilding its source."""
    _validate_learning_corpus_human_evidence_collection_v1(human_evidence)
    return LearningCorpusHumanEvidenceExportV1._from_validated(
        export_id=_build_export_id(human_evidence),
        human_evidence=human_evidence,
    )


def serialize_learning_corpus_human_evidence_export_v1(
    export: LearningCorpusHumanEvidenceExportV1,
) -> bytes:
    """Returns canonical private export bytes without accepting a path."""
    if type(export) is not LearningCorpusHumanEvidenceExportV1:
        raise ValueError("export must be an exact LearningCorpusHumanEvidenceExportV1.")
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
