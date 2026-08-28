from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from skatmind.api.v1.contracts import RequestDocumentV1, ResultDocumentV1
from skatmind.match_analysis_contracts import (
    MatchAnalysisReportV1,
    MatchDecisionAnalysisOptionsV1,
    MatchDecisionAnalysisResultV1,
    _validate_match_analysis_report_identity_v1,
    build_match_analysis_report_v1,
)
from skatmind.match_decision_review_preparation import (
    MatchDecisionOpponentProfileBindingV1,
)

MATCH_ANALYSIS_REPORT_SOURCE_EXPORT_VERSION = 1
MATCH_ANALYSIS_REPORT_SOURCE_DOCUMENT_KIND = "skatmind_match_analysis_report_source"
LEGACY_MATCH_ANALYSIS_REPORT_SOURCE_DOCUMENT_KIND = "skat_ai_match_analysis_report_source"
MATCH_ANALYSIS_REPORT_SOURCE_SUPPORTED_DOCUMENT_KINDS = (
    MATCH_ANALYSIS_REPORT_SOURCE_DOCUMENT_KIND,
    LEGACY_MATCH_ANALYSIS_REPORT_SOURCE_DOCUMENT_KIND,
)


def _validate_exact_executed_decision_report(
    report: object,
    *,
    legacy_identity: bool | None = None,
) -> MatchAnalysisReportV1:
    if type(report) is not MatchAnalysisReportV1:
        raise ValueError("report must be an exact MatchAnalysisReportV1.")
    value = report.value
    if report.report_kind != "decision_analysis" or type(value) is not (
        MatchDecisionAnalysisResultV1
    ):
        raise ValueError("report must be a Decision Analysis report.")
    if value.status != "executed":
        raise ValueError("report must contain an executed Decision analysis.")
    if (
        type(value.options) is not MatchDecisionAnalysisOptionsV1
        or type(value.profile_binding) is not MatchDecisionOpponentProfileBindingV1
        or type(value.request) is not RequestDocumentV1
        or type(value.result) is not ResultDocumentV1
    ):
        raise ValueError(
            "report must contain exact options, profile binding, Request, and Result values."
        )
    rebuilt = build_match_analysis_report_v1(value)
    if rebuilt._identity_document() != report._identity_document():
        raise ValueError("report must equal its canonical Match Analysis Report.")
    _validate_match_analysis_report_identity_v1(
        report,
        legacy_identity=legacy_identity,
    )
    return report


@dataclass(frozen=True, slots=True, kw_only=True)
class MatchAnalysisReportSourceExportV1:
    """One complete executed Decision report for private Learning Corpus import."""

    match_analysis_report_source_export_version: int = MATCH_ANALYSIS_REPORT_SOURCE_EXPORT_VERSION
    document_kind: str = MATCH_ANALYSIS_REPORT_SOURCE_DOCUMENT_KIND
    report_id: str
    report: MatchAnalysisReportV1

    def __post_init__(self) -> None:
        if (
            type(self.match_analysis_report_source_export_version) is not int
            or self.match_analysis_report_source_export_version
            != MATCH_ANALYSIS_REPORT_SOURCE_EXPORT_VERSION
        ):
            raise ValueError(
                "match_analysis_report_source_export_version must equal "
                f"{MATCH_ANALYSIS_REPORT_SOURCE_EXPORT_VERSION}."
            )
        if self.document_kind not in MATCH_ANALYSIS_REPORT_SOURCE_SUPPORTED_DOCUMENT_KINDS:
            raise ValueError(
                "document_kind must be one supported Match Analysis Report-source kind."
            )
        report = _validate_exact_executed_decision_report(
            self.report,
            legacy_identity=(
                self.document_kind == LEGACY_MATCH_ANALYSIS_REPORT_SOURCE_DOCUMENT_KIND
            ),
        )
        if self.report_id != report.report_id:
            raise ValueError("report_id must equal the exact report ID.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_analysis_report_source_export_version": (
                self.match_analysis_report_source_export_version
            ),
            "document_kind": self.document_kind,
            "report_id": self.report_id,
            "report": self.report.to_dict(),
        }


def build_match_analysis_report_source_export_v1(
    report: MatchAnalysisReportV1,
) -> MatchAnalysisReportSourceExportV1:
    """Builds one strict source envelope without executing analysis."""
    validated = _validate_exact_executed_decision_report(report)
    return MatchAnalysisReportSourceExportV1(
        report_id=validated.report_id,
        report=validated,
    )


def serialize_match_analysis_report_source_export_v1(
    export: MatchAnalysisReportSourceExportV1,
) -> bytes:
    """Serializes one source envelope with two spaces, LF, and one trailing LF."""
    if type(export) is not MatchAnalysisReportSourceExportV1:
        raise ValueError("export must be an exact MatchAnalysisReportSourceExportV1.")
    canonical_report = build_match_analysis_report_v1(export.report.value)
    canonical_export = MatchAnalysisReportSourceExportV1(
        report_id=canonical_report.report_id,
        report=canonical_report,
    )
    return (
        json.dumps(
            canonical_export.to_dict(),
            ensure_ascii=True,
            allow_nan=False,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")
