from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from skatmind.learning_corpus_identity import (
    build_learning_corpus_canonical_json_bytes_v1,
)
from skatmind.learning_corpus_tactical_motif_evidence import (
    LearningCorpusTacticalMotifEvidenceCollectionV1,
    _require_hash,
    _require_version,
    _validate_learning_corpus_tactical_motif_collection_v1,
)
from skatmind.learning_corpus_tactical_motif_summary import (
    LearningCorpusTacticalMotifCrossGameSummaryV1,
    _validate_learning_corpus_tactical_motif_cross_game_summary_v1,
)

LEARNING_CORPUS_TACTICAL_MOTIF_EVIDENCE_EXPORT_VERSION = 1
LEARNING_CORPUS_TACTICAL_MOTIF_SUMMARY_EXPORT_VERSION = 1

LEARNING_CORPUS_TACTICAL_MOTIF_EVIDENCE_DOCUMENT_KIND = (
    "skatmind_learning_corpus_tactical_motif_evidence"
)
LEARNING_CORPUS_TACTICAL_MOTIF_CROSS_GAME_SUMMARY_DOCUMENT_KIND = (
    "skatmind_learning_corpus_tactical_motif_cross_game_summary"
)

LEARNING_CORPUS_TACTICAL_MOTIF_EVIDENCE_EXPORT_ID_DOMAIN = (
    b"skatmind\0learning_corpus_tactical_motif_evidence_export_v1\0"
)
LEARNING_CORPUS_TACTICAL_MOTIF_SUMMARY_EXPORT_ID_DOMAIN = (
    b"skatmind\0learning_corpus_tactical_motif_summary_export_v1\0"
)


def _build_identifier(domain: bytes, value: object) -> str:
    return hashlib.sha256(domain + build_learning_corpus_canonical_json_bytes_v1(value)).hexdigest()


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningCorpusTacticalMotifEvidenceExportV1:
    learning_corpus_tactical_motif_evidence_export_version: int
    document_kind: str
    export_id: str
    collection_fingerprint: str
    tactical_motif_evidence: LearningCorpusTacticalMotifEvidenceCollectionV1

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("LearningCorpusTacticalMotifEvidenceExportV1 requires its focused builder.")

    @classmethod
    def _from_validated(
        cls,
        *,
        export_id: str,
        tactical_motif_evidence: LearningCorpusTacticalMotifEvidenceCollectionV1,
    ) -> LearningCorpusTacticalMotifEvidenceExportV1:
        value = object.__new__(cls)
        object.__setattr__(
            value,
            "learning_corpus_tactical_motif_evidence_export_version",
            LEARNING_CORPUS_TACTICAL_MOTIF_EVIDENCE_EXPORT_VERSION,
        )
        object.__setattr__(
            value,
            "document_kind",
            LEARNING_CORPUS_TACTICAL_MOTIF_EVIDENCE_DOCUMENT_KIND,
        )
        object.__setattr__(value, "export_id", export_id)
        object.__setattr__(
            value,
            "collection_fingerprint",
            tactical_motif_evidence.tactical_motif_collection_fingerprint,
        )
        object.__setattr__(
            value,
            "tactical_motif_evidence",
            tactical_motif_evidence,
        )
        value._validate(verify_export_id=False, validate_collection=False)
        return value

    def _validate(
        self,
        *,
        verify_export_id: bool,
        validate_collection: bool,
    ) -> None:
        _require_version(
            self.learning_corpus_tactical_motif_evidence_export_version,
            LEARNING_CORPUS_TACTICAL_MOTIF_EVIDENCE_EXPORT_VERSION,
            "learning_corpus_tactical_motif_evidence_export_version",
        )
        if self.document_kind != LEARNING_CORPUS_TACTICAL_MOTIF_EVIDENCE_DOCUMENT_KIND:
            raise ValueError("document_kind must identify Tactical Motif Evidence.")
        _require_hash(self.export_id, "export_id")
        _require_hash(self.collection_fingerprint, "collection_fingerprint")
        if validate_collection:
            _validate_learning_corpus_tactical_motif_collection_v1(self.tactical_motif_evidence)
        if self.collection_fingerprint != (
            self.tactical_motif_evidence.tactical_motif_collection_fingerprint
        ):
            raise ValueError("collection_fingerprint must match Tactical Evidence.")
        if verify_export_id and self.export_id != _build_evidence_export_id(
            self.tactical_motif_evidence
        ):
            raise ValueError("export_id must cover the exact Tactical Evidence export.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_corpus_tactical_motif_evidence_export_version": (
                self.learning_corpus_tactical_motif_evidence_export_version
            ),
            "document_kind": self.document_kind,
            "export_id": self.export_id,
            "collection_fingerprint": self.collection_fingerprint,
            "tactical_motif_evidence": self.tactical_motif_evidence.to_dict(),
        }


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningCorpusTacticalMotifCrossGameSummaryExportV1:
    learning_corpus_tactical_motif_summary_export_version: int
    document_kind: str
    export_id: str
    summary_fingerprint: str
    tactical_motif_cross_game_summary: LearningCorpusTacticalMotifCrossGameSummaryV1

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "LearningCorpusTacticalMotifCrossGameSummaryExportV1 requires its focused builder."
        )

    @classmethod
    def _from_validated(
        cls,
        *,
        export_id: str,
        tactical_motif_cross_game_summary: (LearningCorpusTacticalMotifCrossGameSummaryV1),
    ) -> LearningCorpusTacticalMotifCrossGameSummaryExportV1:
        value = object.__new__(cls)
        object.__setattr__(
            value,
            "learning_corpus_tactical_motif_summary_export_version",
            LEARNING_CORPUS_TACTICAL_MOTIF_SUMMARY_EXPORT_VERSION,
        )
        object.__setattr__(
            value,
            "document_kind",
            LEARNING_CORPUS_TACTICAL_MOTIF_CROSS_GAME_SUMMARY_DOCUMENT_KIND,
        )
        object.__setattr__(value, "export_id", export_id)
        object.__setattr__(
            value,
            "summary_fingerprint",
            tactical_motif_cross_game_summary.tactical_motif_cross_game_summary_fingerprint,
        )
        object.__setattr__(
            value,
            "tactical_motif_cross_game_summary",
            tactical_motif_cross_game_summary,
        )
        value._validate(verify_export_id=False, validate_summary=False)
        return value

    def _validate(
        self,
        *,
        verify_export_id: bool,
        validate_summary: bool,
    ) -> None:
        _require_version(
            self.learning_corpus_tactical_motif_summary_export_version,
            LEARNING_CORPUS_TACTICAL_MOTIF_SUMMARY_EXPORT_VERSION,
            "learning_corpus_tactical_motif_summary_export_version",
        )
        if self.document_kind != (LEARNING_CORPUS_TACTICAL_MOTIF_CROSS_GAME_SUMMARY_DOCUMENT_KIND):
            raise ValueError("document_kind must identify the Tactical Cross-game Summary.")
        _require_hash(self.export_id, "export_id")
        _require_hash(self.summary_fingerprint, "summary_fingerprint")
        if validate_summary:
            _validate_learning_corpus_tactical_motif_cross_game_summary_v1(
                self.tactical_motif_cross_game_summary
            )
        if self.summary_fingerprint != (
            self.tactical_motif_cross_game_summary.tactical_motif_cross_game_summary_fingerprint
        ):
            raise ValueError("summary_fingerprint must match the Tactical Summary.")
        if verify_export_id and self.export_id != _build_summary_export_id(
            self.tactical_motif_cross_game_summary
        ):
            raise ValueError("export_id must cover the exact Tactical Summary export.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_corpus_tactical_motif_summary_export_version": (
                self.learning_corpus_tactical_motif_summary_export_version
            ),
            "document_kind": self.document_kind,
            "export_id": self.export_id,
            "summary_fingerprint": self.summary_fingerprint,
            "tactical_motif_cross_game_summary": (self.tactical_motif_cross_game_summary.to_dict()),
        }


def _build_evidence_export_id(
    collection: LearningCorpusTacticalMotifEvidenceCollectionV1,
) -> str:
    return _build_identifier(
        LEARNING_CORPUS_TACTICAL_MOTIF_EVIDENCE_EXPORT_ID_DOMAIN,
        {
            "learning_corpus_tactical_motif_evidence_export_version": (
                LEARNING_CORPUS_TACTICAL_MOTIF_EVIDENCE_EXPORT_VERSION
            ),
            "document_kind": LEARNING_CORPUS_TACTICAL_MOTIF_EVIDENCE_DOCUMENT_KIND,
            "collection_fingerprint": (collection.tactical_motif_collection_fingerprint),
            "tactical_motif_evidence": collection.to_dict(),
        },
    )


def _build_summary_export_id(
    summary: LearningCorpusTacticalMotifCrossGameSummaryV1,
) -> str:
    return _build_identifier(
        LEARNING_CORPUS_TACTICAL_MOTIF_SUMMARY_EXPORT_ID_DOMAIN,
        {
            "learning_corpus_tactical_motif_summary_export_version": (
                LEARNING_CORPUS_TACTICAL_MOTIF_SUMMARY_EXPORT_VERSION
            ),
            "document_kind": (LEARNING_CORPUS_TACTICAL_MOTIF_CROSS_GAME_SUMMARY_DOCUMENT_KIND),
            "summary_fingerprint": (summary.tactical_motif_cross_game_summary_fingerprint),
            "tactical_motif_cross_game_summary": summary.to_dict(),
        },
    )


def build_learning_corpus_tactical_motif_evidence_export_v1(
    collection: LearningCorpusTacticalMotifEvidenceCollectionV1,
) -> LearningCorpusTacticalMotifEvidenceExportV1:
    _validate_learning_corpus_tactical_motif_collection_v1(collection)
    return LearningCorpusTacticalMotifEvidenceExportV1._from_validated(
        export_id=_build_evidence_export_id(collection),
        tactical_motif_evidence=collection,
    )


def build_learning_corpus_tactical_motif_cross_game_summary_export_v1(
    summary: LearningCorpusTacticalMotifCrossGameSummaryV1,
) -> LearningCorpusTacticalMotifCrossGameSummaryExportV1:
    _validate_learning_corpus_tactical_motif_cross_game_summary_v1(summary)
    return LearningCorpusTacticalMotifCrossGameSummaryExportV1._from_validated(
        export_id=_build_summary_export_id(summary),
        tactical_motif_cross_game_summary=summary,
    )


def serialize_learning_corpus_tactical_motif_evidence_export_v1(
    export: LearningCorpusTacticalMotifEvidenceExportV1,
) -> bytes:
    if type(export) is not LearningCorpusTacticalMotifEvidenceExportV1:
        raise ValueError("export must be an exact LearningCorpusTacticalMotifEvidenceExportV1.")
    export._validate(verify_export_id=True, validate_collection=True)
    return _serialize_document(export.to_dict())


def serialize_learning_corpus_tactical_motif_cross_game_summary_export_v1(
    export: LearningCorpusTacticalMotifCrossGameSummaryExportV1,
) -> bytes:
    if type(export) is not LearningCorpusTacticalMotifCrossGameSummaryExportV1:
        raise ValueError(
            "export must be an exact LearningCorpusTacticalMotifCrossGameSummaryExportV1."
        )
    export._validate(verify_export_id=True, validate_summary=True)
    return _serialize_document(export.to_dict())


def _serialize_document(value: dict[str, Any]) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            allow_nan=False,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")
