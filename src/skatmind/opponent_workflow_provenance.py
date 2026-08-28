from __future__ import annotations

from collections.abc import Mapping

from skatmind.api.v1.contracts import WorkflowV1
from skatmind.application.provenance import (
    ApplicationProvenanceAttachment,
    ApplicationProvenanceBundle,
)
from skatmind.field_provenance import FieldProvenanceEntry, FieldProvenanceSourceReference
from skatmind.field_provenance_policy import InformationUseContext
from skatmind.opponent_statistics import (
    OpponentStatisticsInput,
    OpponentStatisticsRecord,
    build_serializable_opponent_statistics_input,
)
from skatmind.retrospective_review_provenance import (
    _entry,
    _reference,
    build_complete_provenance_attachment,
)

OPPONENT_WORKFLOW_PROVENANCE_VERSION = 1


def _context() -> InformationUseContext:
    return InformationUseContext(
        workflow="opponent_statistics",
        stage="offline_review",
        perspective_player_id=None,
        perspective_side=None,
        decision_index=None,
        event_index=None,
    )


def _record_reference(
    record: OpponentStatisticsRecord,
    record_index: int,
) -> FieldProvenanceSourceReference:
    reference_type = (
        "aggregate" if record.source.source_type == "historical_games" else "external_record"
    )
    return _reference(reference_type, f"opponent_statistics_record/{record_index}")


def _offline_entry(
    path: str,
    *,
    origin: str,
    derivation: str,
    references: tuple[FieldProvenanceSourceReference, ...],
    subject_player_id: str | None = None,
) -> FieldProvenanceEntry:
    entry = _entry(
        path,
        origin=origin,
        visibility="post_game_only",
        available_from="offline_review",
        derivation=derivation,
        decision_index=None,
        perspective_player_id=None,
        source_references=references,
    )
    if subject_player_id is None:
        return entry
    return FieldProvenanceEntry(
        field_path=entry.field_path,
        coverage_kind=entry.coverage_kind,
        origin=entry.origin,
        visibility=entry.visibility,
        available_from=entry.available_from,
        available_from_decision_index=entry.available_from_decision_index,
        available_from_event_index=entry.available_from_event_index,
        derivation=entry.derivation,
        source_references=entry.source_references,
        dependency_paths=entry.dependency_paths,
        subject_player_id=subject_player_id,
        perspective_player_id=entry.perspective_player_id,
    )


def _input_attachment(
    statistics_input: OpponentStatisticsInput,
) -> ApplicationProvenanceAttachment:
    document = build_serializable_opponent_statistics_input(statistics_input)[
        "opponent_statistics_input"
    ]

    def build(path: str, tokens: tuple[str, ...]) -> FieldProvenanceEntry:
        if len(tokens) >= 2 and tokens[0] == "records" and tokens[1].isdecimal():
            record_index = int(tokens[1])
            record = statistics_input.records[record_index]
            return _offline_entry(
                path,
                origin="external_source",
                derivation="validated",
                references=(_record_reference(record, record_index),),
                subject_player_id=record.player_id,
            )
        return _offline_entry(
            path,
            origin="validated_copy",
            derivation="validated",
            references=(_reference("request", "opponent_statistics_input"),),
        )

    return build_complete_provenance_attachment(
        name="opponent_statistics/input",
        document_role="consumed_input",
        document=document,
        information_use_context=_context(),
        entry_builder=build,
    )


def _record_attachment(
    statistics_input: OpponentStatisticsInput,
    input_document: Mapping[str, object],
    record_index: int,
) -> ApplicationProvenanceAttachment:
    records = input_document["records"]
    assert isinstance(records, list)
    document = records[record_index]
    assert isinstance(document, Mapping)
    record = statistics_input.records[record_index]
    return build_complete_provenance_attachment(
        name=f"opponent_statistics/record/{record_index}",
        document_role="consumed_input",
        document=document,
        information_use_context=_context(),
        entry_builder=lambda path, _tokens: _offline_entry(
            path,
            origin="external_source",
            derivation="validated",
            references=(_record_reference(record, record_index),),
            subject_player_id=record.player_id,
        ),
    )


def _profile_attachment(
    statistics_input: OpponentStatisticsInput,
    summary_record: Mapping[str, object],
    record_index: int,
) -> ApplicationProvenanceAttachment:
    record = statistics_input.records[record_index]
    document = {
        "player_id": summary_record["player_id"],
        "normalized_profile_statistics": summary_record["normalized_profile_statistics"],
        "profile_derivation": summary_record["profile_derivation"],
    }
    reference = _record_reference(record, record_index)

    def build(path: str, tokens: tuple[str, ...]) -> FieldProvenanceEntry:
        dependencies: tuple[str, ...] = ()
        if tokens and tokens[0] == "normalized_profile_statistics":
            origin = "rule_derived"
            derivation = "deterministic_rule"
            references = (
                _reference("algorithm", "opponent_profile_normalization_v1"),
            )
        elif tokens and tokens[0] == "profile_derivation":
            origin = "heuristic_analysis"
            derivation = "heuristic"
            references = (
                _reference("algorithm", "opponent_profile_normalization_v1"),
            )
            dependencies = tuple(
                f"/normalized_profile_statistics/{field_name}"
                for field_name in document["normalized_profile_statistics"]
            )
        else:
            origin = "validated_copy"
            derivation = "validated"
            references = (reference,)
        entry = _offline_entry(
            path,
            origin=origin,
            derivation=derivation,
            references=references,
            subject_player_id=record.player_id,
        )
        if not dependencies:
            return entry
        return FieldProvenanceEntry(
            field_path=entry.field_path,
            coverage_kind=entry.coverage_kind,
            origin=entry.origin,
            visibility=entry.visibility,
            available_from=entry.available_from,
            available_from_decision_index=entry.available_from_decision_index,
            available_from_event_index=entry.available_from_event_index,
            derivation=entry.derivation,
            source_references=entry.source_references,
            dependency_paths=dependencies,
            subject_player_id=entry.subject_player_id,
            perspective_player_id=entry.perspective_player_id,
        )

    return build_complete_provenance_attachment(
        name=f"opponent_statistics/profile/{record_index}",
        document_role="result",
        document=document,
        information_use_context=_context(),
        entry_builder=build,
    )


def _summary_attachment(
    statistics_input: OpponentStatisticsInput,
    summary: Mapping[str, object],
) -> ApplicationProvenanceAttachment:
    records = summary["records"]
    assert isinstance(records, list)

    def build(path: str, tokens: tuple[str, ...]) -> FieldProvenanceEntry:
        if len(tokens) >= 2 and tokens[0] == "records" and tokens[1].isdecimal():
            record_index = int(tokens[1])
            record = statistics_input.records[record_index]
            if len(tokens) >= 3 and tokens[2] == "normalized_profile_statistics":
                origin = "rule_derived"
                derivation = "deterministic_rule"
                references = (
                    _reference("algorithm", "opponent_profile_normalization_v1"),
                )
            elif len(tokens) >= 3 and tokens[2] == "profile_derivation":
                origin = "heuristic_analysis"
                derivation = "heuristic"
                references = (
                    _reference("algorithm", "opponent_profile_normalization_v1"),
                )
            else:
                origin = "external_source"
                derivation = "validated"
                references = (_record_reference(record, record_index),)
            return _offline_entry(
                path,
                origin=origin,
                derivation=derivation,
                references=references,
                subject_player_id=record.player_id,
            )
        return _offline_entry(
            path,
            origin="historical_aggregation",
            derivation="exact_aggregate",
            references=(_reference("aggregate", "opponent_statistics_summary"),),
        )

    return build_complete_provenance_attachment(
        name="opponent_statistics/summary",
        document_role="result",
        document=summary,
        information_use_context=_context(),
        entry_builder=build,
    )


def _root_attachment(result: Mapping[str, object]) -> ApplicationProvenanceAttachment:
    def build(path: str, tokens: tuple[str, ...]) -> FieldProvenanceEntry:
        if tokens == ("input_file",):
            return _offline_entry(
                path,
                origin="caller_supplied",
                derivation="direct",
                references=(_reference("request", "application_input_reference"),),
            )
        return _offline_entry(
            path,
            origin="historical_aggregation",
            derivation="exact_aggregate",
            references=(_reference("aggregate", "opponent_statistics_summary"),),
        )

    return build_complete_provenance_attachment(
        name="opponent_statistics_result",
        document_role="result",
        document=result,
        information_use_context=_context(),
        entry_builder=build,
    )


class OpponentWorkflowProvenanceCollector:
    """Builds normalization and Profile provenance without deriving twice."""

    def __init__(self) -> None:
        self._statistics_input: OpponentStatisticsInput | None = None

    def capture_input(self, statistics_input: OpponentStatisticsInput) -> None:
        self._statistics_input = statistics_input

    def build_bundle(
        self,
        root_result: Mapping[str, object],
    ) -> ApplicationProvenanceBundle:
        if self._statistics_input is None:
            raise ValueError("Opponent provenance did not capture its input.")
        input_document = build_serializable_opponent_statistics_input(self._statistics_input)[
            "opponent_statistics_input"
        ]
        summary = root_result["opponent_statistics_summary"]
        assert isinstance(summary, Mapping)
        summary_records = summary["records"]
        assert isinstance(summary_records, list)
        attachments: list[ApplicationProvenanceAttachment] = [
            _input_attachment(self._statistics_input),
            *(
                _record_attachment(self._statistics_input, input_document, record_index)
                for record_index in range(len(self._statistics_input.records))
            ),
            *(
                _profile_attachment(
                    self._statistics_input,
                    summary_record,
                    record_index,
                )
                for record_index, summary_record in enumerate(summary_records)
                if isinstance(summary_record, Mapping)
            ),
            _summary_attachment(self._statistics_input, summary),
            _root_attachment(root_result),
        ]
        return ApplicationProvenanceBundle(
            workflow=WorkflowV1.OPPONENT_STATISTICS,
            attachments=tuple(attachments),
        )
