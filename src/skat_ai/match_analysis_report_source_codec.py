from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from skat_ai.api.v1.contracts import (
    PUBLIC_API_CONTRACT_VERSION,
    RequestDocumentV1,
    ResultDocumentV1,
    WorkflowV1,
)
from skat_ai.api.v1.schema_validation import (
    validate_input_document,
    validate_output_document,
)
from skat_ai.errors import SkatAIInvariantError, SkatAIValidationError
from skat_ai.information_set_search_workflow import (
    INFORMATION_SET_SEARCH_RECOMMENDATION_METHOD,
)
from skat_ai.match_analysis_contracts import (
    MATCH_ANALYSIS_EXECUTION_VERSION,
    MATCH_ANALYSIS_REPORT_VERSION,
    MATCH_DECISION_ANALYSIS_OPTIONS_VERSION,
    MatchAnalysisReportV1,
    MatchDecisionAnalysisOptionsV1,
    MatchDecisionAnalysisResultV1,
    build_match_analysis_report_v1,
)
from skat_ai.match_analysis_report_source_export import (
    MATCH_ANALYSIS_REPORT_SOURCE_DOCUMENT_KIND,
    MATCH_ANALYSIS_REPORT_SOURCE_EXPORT_VERSION,
    MatchAnalysisReportSourceExportV1,
)
from skat_ai.match_decision_review_preparation import (
    MatchDecisionOpponentProfileBindingV1,
)
from skat_ai.match_information_set_search import (
    reconcile_match_information_set_search_result_v1,
)

_EXPORT_FIELDS = {
    "match_analysis_report_source_export_version",
    "document_kind",
    "report_id",
    "report",
}
_REPORT_FIELDS = {
    "match_analysis_report_version",
    "report_id",
    "report_kind",
    "match_id",
    "workspace_revision",
    "match_position",
    "decision_index",
    "value",
}
_VALUE_FIELDS = {
    "match_analysis_execution_version",
    "status",
    "match_id",
    "workspace_revision",
    "match_position",
    "game_id",
    "decision_index",
    "unavailable_reason",
    "skipped_reason",
    "options",
    "profile_binding",
    "request",
    "result",
}
_OPTIONS_FIELDS = {
    "match_decision_analysis_options_version",
    "recommendation_method",
    "immediate_sample_count",
    "immediate_random_seed",
    "search_random_seed",
    "search_budget_profile",
    "use_profile_presets",
}
_PROFILE_BINDING_FIELDS = {
    "decision_index",
    "acting_player_id",
    "left_opponent_player_id",
    "right_opponent_player_id",
    "left_temporal_status",
    "right_temporal_status",
    "left_profile_available",
    "right_profile_available",
    "left_actionable_policy_preset",
    "right_actionable_policy_preset",
}
_REQUEST_FIELDS = {"api_contract_version", "workflow", "document"}
_RESULT_FIELDS = {"api_contract_version", "workflow", "document", "warnings"}


def _raise_validation(message: str, *, path: str) -> None:
    raise SkatAIValidationError(message, path=path)


def _require_object(
    value: object,
    *,
    fields: set[str],
    path: str,
) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        _raise_validation("Value must be a JSON object.", path=path)
    if any(type(key) is not str for key in value):
        _raise_validation("JSON object keys must be strings.", path=path)
    actual = set(value)
    missing = sorted(fields - actual)
    if missing:
        _raise_validation(f"Missing required fields: {missing}.", path=path)
    unknown = sorted(actual - fields)
    if unknown:
        _raise_validation(f"Unsupported fields: {unknown}.", path=path)
    return value


def _require_mapping(value: object, *, path: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        _raise_validation("Value must be a JSON object.", path=path)
    if any(type(key) is not str for key in value):
        _raise_validation("JSON object keys must be strings.", path=path)
    return value


def _require_version(
    value: object,
    expected: int,
    *,
    field_name: str,
    path: str,
) -> int:
    if type(value) is not int or value != expected:
        _raise_validation(f"{field_name} must equal {expected}.", path=path)
    return value


def _require_integer(value: object, *, field_name: str, path: str) -> int:
    if type(value) is not int:
        _raise_validation(f"{field_name} must be an integer.", path=path)
    return value


def _require_optional_integer(
    value: object,
    *,
    field_name: str,
    path: str,
) -> int | None:
    if value is not None and type(value) is not int:
        _raise_validation(f"{field_name} must be an integer or null.", path=path)
    return value


def _require_string(value: object, *, field_name: str, path: str) -> str:
    if type(value) is not str:
        _raise_validation(f"{field_name} must be a string.", path=path)
    return value


def _require_optional_string(
    value: object,
    *,
    field_name: str,
    path: str,
) -> str | None:
    if value is not None and type(value) is not str:
        _raise_validation(f"{field_name} must be a string or null.", path=path)
    return value


def _require_boolean(value: object, *, field_name: str, path: str) -> bool:
    if type(value) is not bool:
        _raise_validation(f"{field_name} must be a boolean.", path=path)
    return value


def _require_null(value: object, *, field_name: str, path: str) -> None:
    if value is not None:
        _raise_validation(f"{field_name} must be null.", path=path)


def _require_hash(value: object, *, field_name: str, path: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        _raise_validation(
            f"{field_name} must be a lowercase SHA-256 hexadecimal value.",
            path=path,
        )
    return value


def _construct(
    constructor: Callable[..., Any],
    *,
    path: str,
    **values: object,
) -> Any:
    try:
        return constructor(**values)
    except SkatAIValidationError:
        raise
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        raise SkatAIValidationError(str(error), path=path) from error


def _resume_options(value: object) -> MatchDecisionAnalysisOptionsV1:
    path = "/report/value/options"
    data = _require_object(value, fields=_OPTIONS_FIELDS, path=path)
    return _construct(
        MatchDecisionAnalysisOptionsV1,
        path=path,
        match_decision_analysis_options_version=_require_version(
            data["match_decision_analysis_options_version"],
            MATCH_DECISION_ANALYSIS_OPTIONS_VERSION,
            field_name="match_decision_analysis_options_version",
            path=f"{path}/match_decision_analysis_options_version",
        ),
        recommendation_method=_require_string(
            data["recommendation_method"],
            field_name="recommendation_method",
            path=f"{path}/recommendation_method",
        ),
        immediate_sample_count=_require_integer(
            data["immediate_sample_count"],
            field_name="immediate_sample_count",
            path=f"{path}/immediate_sample_count",
        ),
        immediate_random_seed=_require_integer(
            data["immediate_random_seed"],
            field_name="immediate_random_seed",
            path=f"{path}/immediate_random_seed",
        ),
        search_random_seed=_require_optional_integer(
            data["search_random_seed"],
            field_name="search_random_seed",
            path=f"{path}/search_random_seed",
        ),
        search_budget_profile=_require_string(
            data["search_budget_profile"],
            field_name="search_budget_profile",
            path=f"{path}/search_budget_profile",
        ),
        use_profile_presets=_require_boolean(
            data["use_profile_presets"],
            field_name="use_profile_presets",
            path=f"{path}/use_profile_presets",
        ),
    )


def _resume_profile_binding(
    value: object,
) -> MatchDecisionOpponentProfileBindingV1:
    path = "/report/value/profile_binding"
    data = _require_object(value, fields=_PROFILE_BINDING_FIELDS, path=path)
    values: dict[str, object] = {
        "decision_index": _require_integer(
            data["decision_index"],
            field_name="decision_index",
            path=f"{path}/decision_index",
        ),
    }
    for field_name in (
        "acting_player_id",
        "left_opponent_player_id",
        "right_opponent_player_id",
        "left_temporal_status",
        "right_temporal_status",
    ):
        values[field_name] = _require_string(
            data[field_name],
            field_name=field_name,
            path=f"{path}/{field_name}",
        )
    for field_name in ("left_profile_available", "right_profile_available"):
        values[field_name] = _require_boolean(
            data[field_name],
            field_name=field_name,
            path=f"{path}/{field_name}",
        )
    for field_name in (
        "left_actionable_policy_preset",
        "right_actionable_policy_preset",
    ):
        values[field_name] = _require_optional_string(
            data[field_name],
            field_name=field_name,
            path=f"{path}/{field_name}",
        )
    return _construct(MatchDecisionOpponentProfileBindingV1, path=path, **values)


def _resume_request(value: object) -> RequestDocumentV1:
    path = "/report/value/request"
    data = _require_object(value, fields=_REQUEST_FIELDS, path=path)
    workflow_value = _require_string(
        data["workflow"], field_name="workflow", path=f"{path}/workflow"
    )
    try:
        workflow = WorkflowV1(workflow_value)
    except ValueError as error:
        raise SkatAIValidationError(str(error), path=f"{path}/workflow") from error
    return _construct(
        RequestDocumentV1,
        path=path,
        api_contract_version=_require_version(
            data["api_contract_version"],
            PUBLIC_API_CONTRACT_VERSION,
            field_name="api_contract_version",
            path=f"{path}/api_contract_version",
        ),
        workflow=workflow,
        document=_require_mapping(data["document"], path=f"{path}/document"),
    )


def _resume_result(value: object) -> ResultDocumentV1:
    path = "/report/value/result"
    data = _require_object(value, fields=_RESULT_FIELDS, path=path)
    workflow_value = _require_string(
        data["workflow"], field_name="workflow", path=f"{path}/workflow"
    )
    try:
        workflow = WorkflowV1(workflow_value)
    except ValueError as error:
        raise SkatAIValidationError(str(error), path=f"{path}/workflow") from error
    warnings = data["warnings"]
    if not isinstance(warnings, list) or any(type(item) is not str for item in warnings):
        _raise_validation(
            "warnings must be a JSON array of strings.",
            path=f"{path}/warnings",
        )
    return _construct(
        ResultDocumentV1,
        path=path,
        api_contract_version=_require_version(
            data["api_contract_version"],
            PUBLIC_API_CONTRACT_VERSION,
            field_name="api_contract_version",
            path=f"{path}/api_contract_version",
        ),
        workflow=workflow,
        document=_require_mapping(data["document"], path=f"{path}/document"),
        warnings=warnings,
    )


def _resume_report(value: object) -> MatchAnalysisReportV1:
    path = "/report"
    data = _require_object(value, fields=_REPORT_FIELDS, path=path)
    _require_version(
        data["match_analysis_report_version"],
        MATCH_ANALYSIS_REPORT_VERSION,
        field_name="match_analysis_report_version",
        path=f"{path}/match_analysis_report_version",
    )
    supplied_report_id = _require_hash(
        data["report_id"], field_name="report_id", path=f"{path}/report_id"
    )
    report_kind = _require_string(
        data["report_kind"], field_name="report_kind", path=f"{path}/report_kind"
    )
    if report_kind != "decision_analysis":
        _raise_validation(
            "report_kind must equal 'decision_analysis'.",
            path=f"{path}/report_kind",
        )
    match_id = _require_string(data["match_id"], field_name="match_id", path=f"{path}/match_id")
    workspace_revision = _require_integer(
        data["workspace_revision"],
        field_name="workspace_revision",
        path=f"{path}/workspace_revision",
    )
    match_position = _require_integer(
        data["match_position"],
        field_name="match_position",
        path=f"{path}/match_position",
    )
    decision_index = _require_integer(
        data["decision_index"],
        field_name="decision_index",
        path=f"{path}/decision_index",
    )

    value_path = f"{path}/value"
    value = _require_object(data["value"], fields=_VALUE_FIELDS, path=value_path)
    _require_version(
        value["match_analysis_execution_version"],
        MATCH_ANALYSIS_EXECUTION_VERSION,
        field_name="match_analysis_execution_version",
        path=f"{value_path}/match_analysis_execution_version",
    )
    status = _require_string(value["status"], field_name="status", path=f"{value_path}/status")
    if status != "executed":
        _raise_validation("status must equal 'executed'.", path=f"{value_path}/status")
    _require_null(
        value["unavailable_reason"],
        field_name="unavailable_reason",
        path=f"{value_path}/unavailable_reason",
    )
    _require_null(
        value["skipped_reason"],
        field_name="skipped_reason",
        path=f"{value_path}/skipped_reason",
    )
    rebuilt_value = _construct(
        MatchDecisionAnalysisResultV1,
        path=value_path,
        match_analysis_execution_version=MATCH_ANALYSIS_EXECUTION_VERSION,
        status=status,
        match_id=_require_string(
            value["match_id"],
            field_name="match_id",
            path=f"{value_path}/match_id",
        ),
        workspace_revision=_require_integer(
            value["workspace_revision"],
            field_name="workspace_revision",
            path=f"{value_path}/workspace_revision",
        ),
        match_position=_require_integer(
            value["match_position"],
            field_name="match_position",
            path=f"{value_path}/match_position",
        ),
        game_id=_require_string(
            value["game_id"],
            field_name="game_id",
            path=f"{value_path}/game_id",
        ),
        decision_index=_require_integer(
            value["decision_index"],
            field_name="decision_index",
            path=f"{value_path}/decision_index",
        ),
        unavailable_reason=None,
        skipped_reason=None,
        options=_resume_options(value["options"]),
        profile_binding=_resume_profile_binding(value["profile_binding"]),
        request=_resume_request(value["request"]),
        result=_resume_result(value["result"]),
    )
    if rebuilt_value.options.recommendation_method == INFORMATION_SET_SEARCH_RECOMMENDATION_METHOD:
        assert rebuilt_value.request is not None
        assert rebuilt_value.result is not None
        request_document = rebuilt_value.request.to_dict()["document"]
        result_document = rebuilt_value.result.to_dict()["document"]
        try:
            validate_input_document(request_document)
            validate_output_document(result_document)
            reconcile_match_information_set_search_result_v1(
                options=rebuilt_value.options,
                request_document=request_document,
                result_document=result_document,
            )
        except SkatAIValidationError:
            raise
        except SkatAIInvariantError as error:
            raise SkatAIValidationError(
                error.message,
                path=f"{value_path}/result/document",
            ) from error
    rebuilt_report = _construct(
        build_match_analysis_report_v1,
        path=path,
        value=rebuilt_value,
    )
    if (
        rebuilt_report.report_id != supplied_report_id
        or rebuilt_report.match_id != match_id
        or rebuilt_report.workspace_revision != workspace_revision
        or rebuilt_report.match_position != match_position
        or rebuilt_report.decision_index != decision_index
    ):
        _raise_validation(
            "Report identity fields must equal the canonical nested report.",
            path=path,
        )
    return rebuilt_report


def resume_match_analysis_report_source_export_v1(
    mapping: Mapping[str, object],
) -> MatchAnalysisReportSourceExportV1:
    """Strictly reconstructs one uploaded executed Decision report source."""
    try:
        data = _require_object(mapping, fields=_EXPORT_FIELDS, path="")
        _require_version(
            data["match_analysis_report_source_export_version"],
            MATCH_ANALYSIS_REPORT_SOURCE_EXPORT_VERSION,
            field_name="match_analysis_report_source_export_version",
            path="/match_analysis_report_source_export_version",
        )
        document_kind = _require_string(
            data["document_kind"],
            field_name="document_kind",
            path="/document_kind",
        )
        if document_kind != MATCH_ANALYSIS_REPORT_SOURCE_DOCUMENT_KIND:
            _raise_validation(
                "document_kind is unsupported.",
                path="/document_kind",
            )
        report_id = _require_hash(data["report_id"], field_name="report_id", path="/report_id")
        report = _resume_report(data["report"])
        if report_id != report.report_id:
            _raise_validation(
                "report_id must equal the exact nested report ID.",
                path="/report_id",
            )
        resumed = _construct(
            MatchAnalysisReportSourceExportV1,
            path="",
            match_analysis_report_source_export_version=(
                MATCH_ANALYSIS_REPORT_SOURCE_EXPORT_VERSION
            ),
            document_kind=document_kind,
            report_id=report_id,
            report=report,
        )
        if resumed.to_dict() != dict(mapping):
            _raise_validation(
                "Uploaded source is not in exact canonical form.",
                path="",
            )
        return resumed
    except SkatAIValidationError:
        raise
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        raise SkatAIValidationError(str(error), path="") from error
