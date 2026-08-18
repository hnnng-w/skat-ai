from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from skat_ai.learning_corpus_identity import (
    build_learning_corpus_canonical_json_bytes_v1,
)
from skat_ai.learning_dataset_v2_summary_contracts import (
    LEARNING_DATASET_SUMMARY_EXPORT_VERSION,
    LearningDatasetCrossGameSummaryV1,
    _require_hash,
    _require_version,
    _validate_learning_dataset_cross_game_summary_v1,
)

LEARNING_DATASET_SUMMARY_DOCUMENT_KIND = "skat_ai_learning_dataset_v2_cross_game_summary"

_SUMMARY_EXPORT_ID_DOMAIN = b"skat-ai\0learning_dataset_v2_summary_export_v1\0"


def _build_export_id(summary: LearningDatasetCrossGameSummaryV1) -> str:
    material = {
        "learning_dataset_summary_export_version": LEARNING_DATASET_SUMMARY_EXPORT_VERSION,
        "document_kind": LEARNING_DATASET_SUMMARY_DOCUMENT_KIND,
        "summary_fingerprint": summary.cross_game_summary_fingerprint,
        "cross_game_summary": summary.to_dict(),
    }
    return hashlib.sha256(
        _SUMMARY_EXPORT_ID_DOMAIN + build_learning_corpus_canonical_json_bytes_v1(material)
    ).hexdigest()


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningDatasetCrossGameSummaryExportV1:
    learning_dataset_summary_export_version: int
    document_kind: str
    export_id: str
    summary_fingerprint: str
    cross_game_summary: LearningDatasetCrossGameSummaryV1

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("LearningDatasetCrossGameSummaryExportV1 requires its focused builder.")

    @classmethod
    def _from_validated(
        cls,
        **values: Any,
    ) -> LearningDatasetCrossGameSummaryExportV1:
        value = object.__new__(cls)
        for field_name, field_value in values.items():
            object.__setattr__(value, field_name, field_value)
        value._validate(verify_identity=False, validate_summary=False)
        return value

    def _validate(self, *, verify_identity: bool, validate_summary: bool) -> None:
        _require_version(
            self.learning_dataset_summary_export_version,
            LEARNING_DATASET_SUMMARY_EXPORT_VERSION,
            "learning_dataset_summary_export_version",
        )
        if self.document_kind != LEARNING_DATASET_SUMMARY_DOCUMENT_KIND:
            raise ValueError("document_kind must identify the cross-game Summary export.")
        _require_hash(self.export_id, "export_id")
        _require_hash(self.summary_fingerprint, "summary_fingerprint")
        if type(self.cross_game_summary) is not LearningDatasetCrossGameSummaryV1:
            raise ValueError("cross_game_summary must use the exact internal contract.")
        if validate_summary:
            _validate_learning_dataset_cross_game_summary_v1(self.cross_game_summary)
        if self.summary_fingerprint != (self.cross_game_summary.cross_game_summary_fingerprint):
            raise ValueError("summary_fingerprint must match the exact Summary.")
        if verify_identity and self.export_id != _build_export_id(self.cross_game_summary):
            raise ValueError("export_id must cover the exact Summary export.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_dataset_summary_export_version": (
                self.learning_dataset_summary_export_version
            ),
            "document_kind": self.document_kind,
            "export_id": self.export_id,
            "summary_fingerprint": self.summary_fingerprint,
            "cross_game_summary": self.cross_game_summary.to_dict(),
        }


def build_learning_dataset_v2_cross_game_summary_export_v1(
    summary: LearningDatasetCrossGameSummaryV1,
) -> LearningDatasetCrossGameSummaryExportV1:
    """Wraps one already-built Summary without rebuilding any source."""
    _validate_learning_dataset_cross_game_summary_v1(summary)
    return LearningDatasetCrossGameSummaryExportV1._from_validated(
        learning_dataset_summary_export_version=LEARNING_DATASET_SUMMARY_EXPORT_VERSION,
        document_kind=LEARNING_DATASET_SUMMARY_DOCUMENT_KIND,
        export_id=_build_export_id(summary),
        summary_fingerprint=summary.cross_game_summary_fingerprint,
        cross_game_summary=summary,
    )


def serialize_learning_dataset_v2_cross_game_summary_export_v1(
    export: LearningDatasetCrossGameSummaryExportV1,
) -> bytes:
    """Returns deterministic private UTF-8 bytes without accepting a path."""
    if type(export) is not LearningDatasetCrossGameSummaryExportV1:
        raise ValueError("export must be an exact cross-game Summary Export.")
    export._validate(verify_identity=True, validate_summary=True)
    return (
        json.dumps(
            export.to_dict(),
            ensure_ascii=True,
            allow_nan=False,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")
