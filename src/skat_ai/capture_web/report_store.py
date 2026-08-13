from __future__ import annotations

from dataclasses import dataclass, field

from skat_ai.match_analysis_contracts import (
    MATCH_ANALYSIS_REPORT_STORE_LIMIT,
    MATCH_ANALYSIS_REPORT_STORE_VERSION,
    MatchAnalysisReportV1,
)


@dataclass(slots=True)
class MatchAnalysisReportStoreV1:
    """Bounded process-local reports in deterministic insertion order."""

    match_analysis_report_store_version: int = MATCH_ANALYSIS_REPORT_STORE_VERSION
    _reports: dict[str, MatchAnalysisReportV1] = field(
        default_factory=dict,
        init=False,
        repr=False,
    )
    _generation: int = field(default=0, init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.match_analysis_report_store_version) is not int
            or self.match_analysis_report_store_version
            != MATCH_ANALYSIS_REPORT_STORE_VERSION
        ):
            raise ValueError(
                "match_analysis_report_store_version must equal "
                f"{MATCH_ANALYSIS_REPORT_STORE_VERSION}."
            )

    def add(self, report: MatchAnalysisReportV1) -> MatchAnalysisReportV1:
        """Stores one report without refreshing an existing insertion position."""
        if type(report) is not MatchAnalysisReportV1:
            raise ValueError("report must be MatchAnalysisReportV1.")
        self._reports[report.report_id] = report
        while len(self._reports) > MATCH_ANALYSIS_REPORT_STORE_LIMIT:
            del self._reports[next(iter(self._reports))]
        return report

    def put(self, report: MatchAnalysisReportV1) -> MatchAnalysisReportV1:
        return self.add(report)

    def get(self, report_id: str) -> MatchAnalysisReportV1 | None:
        if not isinstance(report_id, str):
            raise ValueError("report_id must be a string.")
        return self._reports.get(report_id)

    def list(self) -> tuple[MatchAnalysisReportV1, ...]:
        return tuple(self._reports.values())

    @property
    def generation(self) -> int:
        """Returns the private invalidation generation for in-flight reconciliation."""
        return self._generation

    def clear(self) -> None:
        self._reports.clear()
        self._generation += 1

    def __len__(self) -> int:
        return len(self._reports)
