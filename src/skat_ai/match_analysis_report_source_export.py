from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from skat_ai.api.v1.contracts import RequestDocumentV1, ResultDocumentV1
from skat_ai.match_analysis_contracts import (
    MatchAnalysisReportV1,
    MatchDecisionAnalysisOptionsV1,
    MatchDecisionAnalysisResultV1,
    build_match_analysis_report_v1,
)
from skat_ai.match_decision_review_preparation import (
    MatchDecisionOpponentProfileBindingV1,
)

MATCH_ANALYSIS_REPORT_SOURCE_EXPORT_VERSION = 1
MATCH_ANALYSIS_REPORT_SOURCE_DOCUMENT_KIND = "skat_ai_match_analysis_report_source"


def _validate_exact_executed_decision_report(report: object) -> MatchAnalysisReportV1:
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
    if rebuilt.to_dict() != report.to_dict():
        raise ValueError("report must equal its canonical Match Analysis Report.")
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
        if self.document_kind != MATCH_ANALYSIS_REPORT_SOURCE_DOCUMENT_KIND:
            raise ValueError(
                f"document_kind must equal {MATCH_ANALYSIS_REPORT_SOURCE_DOCUMENT_KIND!r}."
            )
        report = _validate_exact_executed_decision_report(self.report)
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
    return (
        json.dumps(
            export.to_dict(),
            ensure_ascii=True,
            allow_nan=False,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")
