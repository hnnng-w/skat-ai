import copy
import json
from dataclasses import FrozenInstanceError, fields

import pytest
from test_learning_corpus_strategy_teacher import _changed_report, _source_bundle

from skatmind.errors import SkatMindValidationError
from skatmind.match_analysis_contracts import (
    MatchDecisionAnalysisOptionsV1,
    build_match_analysis_report_v1,
    prepare_match_materialization_report_v1,
)
from skatmind.match_analysis_report_source_codec import (
    resume_match_analysis_report_source_export_v1,
)
from skatmind.match_analysis_report_source_export import (
    MATCH_ANALYSIS_REPORT_SOURCE_DOCUMENT_KIND,
    MATCH_ANALYSIS_REPORT_SOURCE_EXPORT_VERSION,
    MatchAnalysisReportSourceExportV1,
    build_match_analysis_report_source_export_v1,
    serialize_match_analysis_report_source_export_v1,
)
from skatmind.match_decision_analysis import execute_match_decision_analysis_v1


@pytest.fixture(scope="module")
def report_bundle():
    workspace, _snapshot, _result, report, _source, _store = _source_bundle()
    return workspace, report


def _target(document: dict, path: tuple[str, ...]) -> dict:
    value = document
    for field_name in path:
        value = value[field_name]
    return value


def test_source_export_shape_version_kind_and_defensive_serialization(report_bundle) -> None:
    _workspace, report = report_bundle
    export = build_match_analysis_report_source_export_v1(report)

    assert MATCH_ANALYSIS_REPORT_SOURCE_EXPORT_VERSION == 1
    assert MATCH_ANALYSIS_REPORT_SOURCE_DOCUMENT_KIND == ("skatmind_match_analysis_report_source")
    assert tuple(field.name for field in fields(MatchAnalysisReportSourceExportV1)) == (
        "match_analysis_report_source_export_version",
        "document_kind",
        "report_id",
        "report",
    )
    assert export.to_dict() == {
        "match_analysis_report_source_export_version": 1,
        "document_kind": "skatmind_match_analysis_report_source",
        "report_id": report.report_id,
        "report": report.to_dict(),
    }
    mutable = export.to_dict()
    mutable["report"]["value"]["options"]["recommendation_method"] = "changed"
    assert (
        export.to_dict()["report"]["value"]["options"]["recommendation_method"]
        == "immediate_expected_value"
    )
    with pytest.raises(FrozenInstanceError):
        export.report_id = "0" * 64
    with pytest.raises(ValueError, match="version must equal 1"):
        MatchAnalysisReportSourceExportV1(
            match_analysis_report_source_export_version=True,
            report_id=report.report_id,
            report=report,
        )
    with pytest.raises(ValueError, match="exact report ID"):
        MatchAnalysisReportSourceExportV1(
            report_id="0" * 64,
            report=report,
        )


def test_source_export_bytes_are_deterministic_ascii_utf8_and_canonical(
    report_bundle,
) -> None:
    _workspace, report = report_bundle
    export = build_match_analysis_report_source_export_v1(report)
    expected = (
        json.dumps(
            export.to_dict(),
            ensure_ascii=True,
            allow_nan=False,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")

    first = serialize_match_analysis_report_source_export_v1(export)
    assert first == expected
    assert serialize_match_analysis_report_source_export_v1(export) == first
    assert first.isascii()
    assert first.endswith(b"\n") and not first.endswith(b"\n\n")


def test_source_export_and_resume_reject_non_decision_or_unavailable_reports(
    report_bundle,
) -> None:
    workspace, report = report_bundle
    materialization = build_match_analysis_report_v1(
        prepare_match_materialization_report_v1(workspace)
    )
    unavailable = build_match_analysis_report_v1(
        execute_match_decision_analysis_v1(
            workspace,
            match_position=3,
            decision_index=99,
            options=MatchDecisionAnalysisOptionsV1(immediate_sample_count=1),
        )
    )

    with pytest.raises(ValueError, match="Decision Analysis"):
        build_match_analysis_report_source_export_v1(materialization)
    with pytest.raises(ValueError, match="executed"):
        build_match_analysis_report_source_export_v1(unavailable)

    document = build_match_analysis_report_source_export_v1(report).to_dict()
    document["report"]["report_kind"] = "historical_analysis"
    with pytest.raises(SkatMindValidationError):
        resume_match_analysis_report_source_export_v1(document)


def test_resume_reconstructs_complete_exact_nested_report(report_bundle) -> None:
    _workspace, report = report_bundle
    document = build_match_analysis_report_source_export_v1(report).to_dict()
    resumed = resume_match_analysis_report_source_export_v1(document)

    assert type(resumed) is MatchAnalysisReportSourceExportV1
    assert resumed.to_dict() == document
    assert resumed.report == report
    assert resumed.report is not report
    assert resumed.report.value.request is not report.value.request
    assert resumed.report.value.result is not report.value.result


@pytest.mark.parametrize(
    "path",
    (
        (),
        ("report",),
        ("report", "value"),
        ("report", "value", "options"),
        ("report", "value", "profile_binding"),
        ("report", "value", "request"),
        ("report", "value", "result"),
    ),
)
def test_resume_rejects_unknown_fields_at_every_fixed_wrapper_level(
    report_bundle,
    path: tuple[str, ...],
) -> None:
    _workspace, report = report_bundle
    document = build_match_analysis_report_source_export_v1(report).to_dict()
    _target(document, path)["unknown"] = True

    with pytest.raises(SkatMindValidationError, match="Unsupported fields"):
        resume_match_analysis_report_source_export_v1(document)


@pytest.mark.parametrize(
    ("path", "field_name"),
    (
        ((), "document_kind"),
        (("report",), "match_id"),
        (("report", "value"), "game_id"),
        (("report", "value", "options"), "recommendation_method"),
        (("report", "value", "profile_binding"), "acting_player_id"),
        (("report", "value", "request"), "document"),
        (("report", "value", "result"), "warnings"),
    ),
)
def test_resume_rejects_missing_fields_at_every_fixed_wrapper_level(
    report_bundle,
    path: tuple[str, ...],
    field_name: str,
) -> None:
    _workspace, report = report_bundle
    document = build_match_analysis_report_source_export_v1(report).to_dict()
    del _target(document, path)[field_name]

    with pytest.raises(SkatMindValidationError, match="Missing required fields"):
        resume_match_analysis_report_source_export_v1(document)


@pytest.mark.parametrize(
    ("path", "field_name", "changed"),
    (
        ((), "match_analysis_report_source_export_version", True),
        ((), "document_kind", "other_kind"),
        ((), "report_id", "0" * 64),
        (("report",), "report_id", "0" * 64),
        (("report",), "report_kind", "materialization"),
        (("report", "value"), "status", "unavailable"),
        (("report", "value"), "workspace_revision", True),
        (("report", "value", "options"), "immediate_sample_count", True),
        (("report", "value", "profile_binding"), "decision_index", True),
        (("report", "value", "request"), "workflow", "historical_game"),
        (("report", "value", "result"), "workflow", "historical_game"),
        (("report", "value", "request"), "api_contract_version", True),
        (("report", "value", "result"), "api_contract_version", True),
    ),
)
def test_resume_rejects_tampered_identity_kinds_status_and_native_scalars(
    report_bundle,
    path: tuple[str, ...],
    field_name: str,
    changed: object,
) -> None:
    _workspace, report = report_bundle
    document = build_match_analysis_report_source_export_v1(report).to_dict()
    _target(document, path)[field_name] = changed

    with pytest.raises(SkatMindValidationError):
        resume_match_analysis_report_source_export_v1(document)


@pytest.mark.parametrize("wrapper", ("request", "result"))
def test_resume_rejects_changed_nested_request_or_result(
    report_bundle,
    wrapper: str,
) -> None:
    _workspace, report = report_bundle
    document = copy.deepcopy(build_match_analysis_report_source_export_v1(report).to_dict())
    document["report"]["value"][wrapper]["document"]["tampered"] = True

    with pytest.raises(SkatMindValidationError, match="identity fields"):
        resume_match_analysis_report_source_export_v1(document)


def test_information_set_source_round_trip_and_semantic_tampering() -> None:
    _workspace, _snapshot, result, report, _source, _store = _source_bundle(
        recommendation_method="information_set_search",
        decision_index=30,
        match_id="match-information-set-source",
        search_random_seed=7,
        search_budget_profile="interactive_v1",
    )
    document = build_match_analysis_report_source_export_v1(report).to_dict()
    assert resume_match_analysis_report_source_export_v1(document).to_dict() == document

    request_document = result.request.to_dict()["document"]
    request_document["information_set_search_settings"]["max_selected_worlds"] = 63
    changed_request_report = build_match_analysis_report_source_export_v1(
        _changed_report(result, request_document=request_document)
    ).to_dict()
    with pytest.raises(SkatMindValidationError, match="Request changed"):
        resume_match_analysis_report_source_export_v1(changed_request_report)

    result_document = result.result.to_dict()["document"]
    result_document["information_set_search_result"]["private_worlds"] = []
    changed_result_report = build_match_analysis_report_source_export_v1(
        _changed_report(result, result_document=result_document)
    ).to_dict()
    with pytest.raises(SkatMindValidationError):
        resume_match_analysis_report_source_export_v1(changed_result_report)

    result_document = result.result.to_dict()["document"]
    result_document["information_set_search_result"]["candidate_results"][0][
        "local_contract_success_rate"
    ] = 0.5
    changed_result_report = build_match_analysis_report_source_export_v1(
        _changed_report(result, result_document=result_document)
    ).to_dict()
    with pytest.raises(SkatMindValidationError, match="aggregate Result"):
        resume_match_analysis_report_source_export_v1(changed_result_report)

    result_document = result.result.to_dict()["document"]
    comparison = result_document["information_set_search_comparison"]
    comparison["information_set_immediate_same_card"] = not comparison[
        "information_set_immediate_same_card"
    ]
    changed_result_report = build_match_analysis_report_source_export_v1(
        _changed_report(result, result_document=result_document)
    ).to_dict()
    with pytest.raises(SkatMindValidationError, match="agreement facts"):
        resume_match_analysis_report_source_export_v1(changed_result_report)
