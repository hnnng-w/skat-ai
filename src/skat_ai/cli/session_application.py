from __future__ import annotations

import argparse
from collections.abc import Callable
from typing import Any

from skat_ai.application.contracts import (
    ApplicationExecutionOptions,
    HistoricalGameApplicationOptions,
    PositionAnalysisApplicationOptions,
)
from skat_ai.cli.root_application import execute_legacy_application
from skat_ai.cli.session_context import SessionContext

LegacyApplicationExecutor = Callable[..., tuple[dict[str, Any], object]]


def execute_position_request_with_application(
    request: object,
    *,
    input_reference: str,
    include_provenance: bool,
    execute_application: LegacyApplicationExecutor,
) -> dict[str, Any]:
    result, _artifacts = execute_application(
        request.to_dict()["document"],
        input_reference=input_reference,
        options=ApplicationExecutionOptions(
            position_analysis=PositionAnalysisApplicationOptions()
        ),
        include_provenance=include_provenance,
    )
    return result


def execute_position_request(
    request: object,
    *,
    input_reference: str,
    include_provenance: bool,
) -> dict[str, Any]:
    return execute_position_request_with_application(
        request,
        input_reference=input_reference,
        include_provenance=include_provenance,
        execute_application=execute_legacy_application,
    )


def session_input_reference(context: SessionContext) -> str:
    return f"session:{context.state.session_id}:revision:{context.state.revision}"


def historical_application_options(args: argparse.Namespace) -> ApplicationExecutionOptions:
    return ApplicationExecutionOptions(
        historical_game=HistoricalGameApplicationOptions(
            decision_snapshots=args.historical_decision_snapshots,
            immediate_review=args.historical_game_review,
            search_review=args.historical_search_review,
            replay_coaching=args.historical_replay_coaching,
            search_seed=args.search_seed,
            search_budget_profile=args.search_budget_profile,
            immediate_sample_count=args.samples,
            immediate_base_random_seed=args.seed,
        )
    )


def execute_historical_request_with_application(
    request: object,
    *,
    input_reference: str,
    include_provenance: bool,
    options: ApplicationExecutionOptions,
    execute_application: LegacyApplicationExecutor,
) -> dict[str, Any]:
    result, _artifacts = execute_application(
        request.to_dict()["document"],
        input_reference=input_reference,
        options=options,
        include_provenance=include_provenance,
    )
    return result


def execute_historical_request(
    request: object,
    *,
    input_reference: str,
    include_provenance: bool,
    options: ApplicationExecutionOptions,
) -> dict[str, Any]:
    return execute_historical_request_with_application(
        request,
        input_reference=input_reference,
        include_provenance=include_provenance,
        options=options,
        execute_application=execute_legacy_application,
    )


_execute_position_request = execute_position_request
_session_input_reference = session_input_reference
_historical_application_options = historical_application_options
_execute_historical_request = execute_historical_request
