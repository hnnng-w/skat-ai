from __future__ import annotations

from collections.abc import Mapping

from skatmind.errors import SkatMindError, SkatMindInvariantError
from skatmind.match_analysis_contracts import (
    MATCH_ANALYSIS_OPERATIONS,
    MatchAnalysisReportV1,
    MatchDecisionAnalysisOptionsV1,
    MatchHistoricalAnalysisOptionsV1,
    MatchMaterializationReportV1,
    build_match_analysis_report_v1,
    prepare_match_materialization_report_v1,
)
from skatmind.match_decision_analysis import execute_match_decision_analysis_v1
from skatmind.match_historical_analysis import execute_match_historical_analysis_v1
from skatmind.recommendation_workflow import FLAT_SEARCH_RECOMMENDATION_METHODS
from skatmind.simulation import DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT

from .context import MatchCaptureWebContextV1
from .contracts import MatchCaptureWebResultV1
from .state import build_match_capture_web_state_v1

_COMMON_FIELDS = {
    "operation",
    "expected_revision",
    "match_position",
}
_ANALYSIS_FIELDS = {
    "prepare_materialization": _COMMON_FIELDS,
    "analyze_decision": _COMMON_FIELDS
    | {
        "decision_index",
        "recommendation_method",
        "immediate_sample_count",
        "immediate_random_seed",
        "search_random_seed",
        "search_budget_profile",
        "use_profile_presets",
    },
    "analyze_historical_game": _COMMON_FIELDS
    | {
        "decision_snapshots",
        "tactical_motif_review",
        "immediate_review",
        "search_review",
        "information_set_search_review",
        "replay_coaching",
        "information_set_replay_coaching",
        "immediate_sample_count",
        "immediate_random_seed",
        "search_random_seed",
        "search_budget_profile",
        "use_profile_presets",
    },
}


def _text(
    values: Mapping[str, object],
    name: str,
    *,
    default: str | None = None,
) -> str:
    value = values.get(name, default)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be non-empty text.")
    return value


def _integer(
    values: Mapping[str, object],
    name: str,
    *,
    default: int | None = None,
) -> int:
    value = values.get(name, default)
    if type(value) is int:
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError as error:
            raise ValueError(f"{name} must be an integer.") from error
    raise ValueError(f"{name} must be an integer.")


def _optional_integer(values: Mapping[str, object], name: str) -> int | None:
    if values.get(name) in {None, ""}:
        return None
    return _integer(values, name)


def _boolean(
    values: Mapping[str, object],
    name: str,
    *,
    default: bool,
) -> bool:
    value = values.get(name, default)
    if type(value) is bool:
        return value
    if isinstance(value, str):
        normalized = value.lower()
        if normalized in {"1", "true", "on", "yes"}:
            return True
        if normalized in {"0", "false", "off", "no"}:
            return False
    raise ValueError(f"{name} must be a boolean.")


def _validate_fields(values: Mapping[str, object], operation: str) -> None:
    unexpected = sorted(set(values) - _ANALYSIS_FIELDS[operation])
    if unexpected:
        raise ValueError("Unsupported analysis form fields: " + ", ".join(unexpected) + ".")


def _position(values: Mapping[str, object]) -> int:
    position = _integer(values, "match_position")
    if not 1 <= position <= 36:
        raise ValueError("match_position must be an integer from 1 through 36.")
    return position


def _decision_options(
    values: Mapping[str, object],
    *,
    browser_form: bool,
) -> MatchDecisionAnalysisOptionsV1:
    method = _text(
        values,
        "recommendation_method",
        default="immediate_expected_value",
    )
    supplied_search_seed = _optional_integer(values, "search_random_seed")
    needs_search = method in FLAT_SEARCH_RECOMMENDATION_METHODS
    if browser_form:
        search_seed = supplied_search_seed if needs_search else None
    else:
        search_seed = supplied_search_seed
    if browser_form and needs_search and search_seed is None:
        search_seed = 0
    return MatchDecisionAnalysisOptionsV1(
        recommendation_method=method,
        immediate_sample_count=_integer(
            values,
            "immediate_sample_count",
            default=DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT,
        ),
        immediate_random_seed=_integer(
            values,
            "immediate_random_seed",
            default=0,
        ),
        search_random_seed=search_seed,
        search_budget_profile=_text(
            values,
            "search_budget_profile",
            default="historical_review_v1",
        ),
        use_profile_presets=_boolean(
            values,
            "use_profile_presets",
            default=not browser_form,
        ),
    )


def _historical_options(
    values: Mapping[str, object],
    *,
    browser_form: bool,
) -> MatchHistoricalAnalysisOptionsV1:
    decision_snapshots = _boolean(
        values,
        "decision_snapshots",
        default=False,
    )
    tactical_motif_review = _boolean(
        values,
        "tactical_motif_review",
        default=False,
    )
    immediate_review = _boolean(
        values,
        "immediate_review",
        default=not browser_form,
    )
    search_review = _boolean(values, "search_review", default=False)
    information_set_search_review = _boolean(
        values,
        "information_set_search_review",
        default=False,
    )
    replay_coaching = _boolean(values, "replay_coaching", default=False)
    information_set_replay_coaching = _boolean(
        values,
        "information_set_replay_coaching",
        default=False,
    )
    supplied_search_seed = _optional_integer(values, "search_random_seed")
    needs_search = (
        search_review
        or information_set_search_review
        or replay_coaching
        or information_set_replay_coaching
    )
    search_seed = supplied_search_seed
    if browser_form and not needs_search:
        search_seed = None
    if browser_form and needs_search and search_seed is None:
        search_seed = 0
    return MatchHistoricalAnalysisOptionsV1(
        decision_snapshots=decision_snapshots,
        tactical_motif_review=tactical_motif_review,
        immediate_review=immediate_review,
        search_review=search_review,
        information_set_search_review=information_set_search_review,
        replay_coaching=replay_coaching,
        information_set_replay_coaching=information_set_replay_coaching,
        immediate_sample_count=_integer(
            values,
            "immediate_sample_count",
            default=DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT,
        ),
        immediate_random_seed=_integer(
            values,
            "immediate_random_seed",
            default=0,
        ),
        search_random_seed=search_seed,
        search_budget_profile=_text(
            values,
            "search_budget_profile",
            default="historical_review_v1",
        ),
        use_profile_presets=_boolean(
            values,
            "use_profile_presets",
            default=not browser_form,
        ),
    )


def _browser_state(
    context: MatchCaptureWebContextV1,
    *,
    position: int,
    selected_report_id: str | None = None,
) -> dict[str, object]:
    return build_match_capture_web_state_v1(
        context.workspace,
        workspace_filename=context.workspace_filename,
        selected_position=position,
        report_store=context.report_store,
        selected_report_id=selected_report_id,
    )


def execute_match_capture_web_analysis_v1(
    context: MatchCaptureWebContextV1,
    values: Mapping[str, object],
    *,
    browser_form: bool = False,
) -> MatchCaptureWebResultV1:
    """Executes one explicit report operation outside the Capture context lock."""
    operation = _text(values, "operation")
    if operation not in MATCH_ANALYSIS_OPERATIONS:
        raise ValueError("operation must identify one supported analysis operation.")
    _validate_fields(values, operation)
    position = _position(values)
    expected_revision = _integer(values, "expected_revision")
    if expected_revision < 0:
        raise ValueError("expected_revision must be a non-negative integer.")
    if type(browser_form) is not bool:
        raise ValueError("browser_form must be a boolean.")

    with context.lock:
        workspace = context.workspace
        if workspace is None:
            raise ValueError("Create the Workspace before running analysis.")
        if expected_revision != workspace.revision:
            return MatchCaptureWebResultV1(
                operation=operation,
                status="revision_conflict",
                http_status=409,
                message="Workspace revision conflict; analysis was not executed.",
                state=_browser_state(context, position=position),
            )
        source_match_id = workspace.match_definition.match_id
        source_revision = workspace.revision
        source_fingerprint = context.content_fingerprint
        source_report_generation = context.report_store.generation

    decision_index = None
    decision_options = None
    historical_options = None
    if operation == "analyze_decision":
        decision_index = _integer(values, "decision_index")
        if decision_index <= 0:
            raise ValueError("decision_index must be a positive integer.")
        decision_options = _decision_options(values, browser_form=browser_form)
    elif operation == "analyze_historical_game":
        historical_options = _historical_options(values, browser_form=browser_form)

    try:
        if operation == "prepare_materialization":
            value = prepare_match_materialization_report_v1(workspace)
        elif operation == "analyze_decision":
            assert decision_index is not None
            assert decision_options is not None
            value = execute_match_decision_analysis_v1(
                workspace,
                match_position=position,
                decision_index=decision_index,
                options=decision_options,
            )
        else:
            assert historical_options is not None
            value = execute_match_historical_analysis_v1(
                workspace,
                match_position=position,
                options=historical_options,
            )
        report = build_match_analysis_report_v1(value)
    except SkatMindError:
        raise
    except (TypeError, ValueError) as error:
        raise SkatMindInvariantError(
            "Validated Capture Web analysis failed an internal Match invariant."
        ) from error

    with context.lock:
        current = context.workspace
        unchanged = (
            current is not None
            and current.match_definition.match_id == source_match_id
            and current.revision == source_revision
            and context.content_fingerprint == source_fingerprint
            and context.report_store.generation == source_report_generation
        )
        if not unchanged:
            return MatchCaptureWebResultV1(
                operation=operation,
                status="revision_conflict",
                http_status=409,
                message=(
                    "The Workspace changed during analysis; the stale report was "
                    "discarded without retry."
                ),
                state=_browser_state(context, position=position),
            )
        context.report_store.put(report)
        return MatchCaptureWebResultV1(
            operation=operation,
            status="applied",
            http_status=200,
            message="Private local analysis report prepared.",
            state=_browser_state(
                context,
                position=position,
                selected_report_id=report.report_id,
            ),
        )


def get_current_match_analysis_report_v1(
    context: MatchCaptureWebContextV1,
    report_id: str,
) -> tuple[str, MatchAnalysisReportV1 | None]:
    """Returns found, missing, or stale without exposing context fingerprints."""
    with context.lock:
        report = context.report_store.get(report_id)
        if report is None:
            return "missing", None
        workspace = context.workspace
        if (
            workspace is None
            or report.match_id != workspace.match_definition.match_id
            or report.workspace_revision != workspace.revision
        ):
            return "stale", None
        return "found", report


def get_current_materialization_report_v1(
    context: MatchCaptureWebContextV1,
) -> tuple[str, MatchAnalysisReportV1 | None]:
    """Selects the latest cached current-revision materialization report."""
    with context.lock:
        workspace = context.workspace
        materializations = [
            report
            for report in context.report_store.list()
            if report.report_kind == "materialization"
        ]
        if not materializations:
            return "missing", None
        report = materializations[-1]
        if (
            workspace is None
            or report.match_id != workspace.match_definition.match_id
            or report.workspace_revision != workspace.revision
        ):
            return "stale", None
        if type(report.value) is not MatchMaterializationReportV1:
            raise RuntimeError("Materialization report kind has an invalid value.")
        return "found", report
