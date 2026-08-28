from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from skatmind.learning_corpus_tactical_coaching_contracts import (
    LEARNING_CORPUS_TACTICAL_CROSS_GAME_COACHING_EXPORT_ID_DOMAIN,
    LEARNING_CORPUS_TACTICAL_CROSS_GAME_COACHING_EXPORT_VERSION,
    LearningCorpusTacticalCrossGameCoachingReportV1,
    _build_coaching_identifier_v1,
    _require_hash,
    _require_version,
    _validate_learning_corpus_tactical_cross_game_coaching_report_v1,
)

LEARNING_CORPUS_TACTICAL_CROSS_GAME_COACHING_DOCUMENT_KIND = (
    "skatmind_learning_corpus_tactical_cross_game_coaching"
)


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningCorpusTacticalCrossGameCoachingExportV1:
    learning_corpus_tactical_cross_game_coaching_export_version: int
    document_kind: str
    export_id: str
    report_fingerprint: str
    tactical_cross_game_coaching: LearningCorpusTacticalCrossGameCoachingReportV1

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "LearningCorpusTacticalCrossGameCoachingExportV1 requires its focused builder."
        )

    @classmethod
    def _from_validated(
        cls,
        *,
        export_id: str,
        tactical_cross_game_coaching: LearningCorpusTacticalCrossGameCoachingReportV1,
    ) -> LearningCorpusTacticalCrossGameCoachingExportV1:
        value = object.__new__(cls)
        object.__setattr__(
            value,
            "learning_corpus_tactical_cross_game_coaching_export_version",
            LEARNING_CORPUS_TACTICAL_CROSS_GAME_COACHING_EXPORT_VERSION,
        )
        object.__setattr__(
            value,
            "document_kind",
            LEARNING_CORPUS_TACTICAL_CROSS_GAME_COACHING_DOCUMENT_KIND,
        )
        object.__setattr__(value, "export_id", export_id)
        object.__setattr__(
            value,
            "report_fingerprint",
            tactical_cross_game_coaching.tactical_cross_game_coaching_report_fingerprint,
        )
        object.__setattr__(
            value,
            "tactical_cross_game_coaching",
            tactical_cross_game_coaching,
        )
        value._validate(verify_export_id=False, validate_report=False)
        return value

    def _validate(self, *, verify_export_id: bool, validate_report: bool) -> None:
        _require_version(
            self.learning_corpus_tactical_cross_game_coaching_export_version,
            LEARNING_CORPUS_TACTICAL_CROSS_GAME_COACHING_EXPORT_VERSION,
            "learning_corpus_tactical_cross_game_coaching_export_version",
        )
        if self.document_kind != LEARNING_CORPUS_TACTICAL_CROSS_GAME_COACHING_DOCUMENT_KIND:
            raise ValueError("document_kind must identify Tactical Cross-game Coaching.")
        _require_hash(self.export_id, "export_id")
        _require_hash(self.report_fingerprint, "report_fingerprint")
        if validate_report:
            _validate_learning_corpus_tactical_cross_game_coaching_report_v1(
                self.tactical_cross_game_coaching
            )
        if self.report_fingerprint != (
            self.tactical_cross_game_coaching.tactical_cross_game_coaching_report_fingerprint
        ):
            raise ValueError("report_fingerprint must match the retained Coaching Report.")
        if verify_export_id and self.export_id != _build_export_id(
            self.tactical_cross_game_coaching
        ):
            raise ValueError("export_id must cover the exact Tactical Coaching export.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_corpus_tactical_cross_game_coaching_export_version": (
                self.learning_corpus_tactical_cross_game_coaching_export_version
            ),
            "document_kind": self.document_kind,
            "export_id": self.export_id,
            "report_fingerprint": self.report_fingerprint,
            "tactical_cross_game_coaching": self.tactical_cross_game_coaching.to_dict(),
        }


def _build_export_id(report: LearningCorpusTacticalCrossGameCoachingReportV1) -> str:
    return _build_coaching_identifier_v1(
        LEARNING_CORPUS_TACTICAL_CROSS_GAME_COACHING_EXPORT_ID_DOMAIN,
        {
            "learning_corpus_tactical_cross_game_coaching_export_version": (
                LEARNING_CORPUS_TACTICAL_CROSS_GAME_COACHING_EXPORT_VERSION
            ),
            "document_kind": LEARNING_CORPUS_TACTICAL_CROSS_GAME_COACHING_DOCUMENT_KIND,
            "report_fingerprint": report.tactical_cross_game_coaching_report_fingerprint,
            "tactical_cross_game_coaching": report.to_dict(),
        },
    )


def build_learning_corpus_tactical_cross_game_coaching_export_v1(
    report: LearningCorpusTacticalCrossGameCoachingReportV1,
) -> LearningCorpusTacticalCrossGameCoachingExportV1:
    _validate_learning_corpus_tactical_cross_game_coaching_report_v1(report)
    return LearningCorpusTacticalCrossGameCoachingExportV1._from_validated(
        export_id=_build_export_id(report),
        tactical_cross_game_coaching=report,
    )


def serialize_learning_corpus_tactical_cross_game_coaching_export_v1(
    export: LearningCorpusTacticalCrossGameCoachingExportV1,
) -> bytes:
    if type(export) is not LearningCorpusTacticalCrossGameCoachingExportV1:
        raise ValueError(
            "export must be an exact LearningCorpusTacticalCrossGameCoachingExportV1."
        )
    export._validate(verify_export_id=True, validate_report=True)
    return (
        json.dumps(
            export.to_dict(),
            ensure_ascii=True,
            allow_nan=False,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")
