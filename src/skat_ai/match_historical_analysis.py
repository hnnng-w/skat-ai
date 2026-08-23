from __future__ import annotations

from typing import Any

from skat_ai.api.v1.contracts import RequestDocumentV1, WorkflowV1
from skat_ai.api.v1.schema_validation import validate_output_document
from skat_ai.application.contracts import (
    ApplicationExecutionOptions,
    ApplicationExternalDocuments,
)
from skat_ai.application.execution import (
    ApplicationWorkflowDependencies,
    build_application_invocation,
    execute_application_invocation,
)
from skat_ai.errors import SkatAIInvariantError
from skat_ai.historical_game import build_serializable_historical_record
from skat_ai.input_loader import build_historical_game_from_document
from skat_ai.match_analysis_contracts import (
    MatchHistoricalAnalysisOptionsV1,
    MatchHistoricalAnalysisResultV1,
)
from skat_ai.match_historical_information_set_analysis import (
    build_match_historical_application_options_v1,
    reconcile_match_historical_information_set_result_v1,
    uses_match_historical_information_set_family_v1,
)
from skat_ai.match_historical_materialization import (
    materialize_match_observed_game_historical_v1,
)
from skat_ai.match_player_statistics_preparation import (
    MatchPlayerStatisticsPreparationV1,
    build_match_player_statistics_preparation_v1,
)
from skat_ai.match_workspace_contracts import MatchWorkspaceV1
from skat_ai.opponent_statistics import build_serializable_opponent_statistics_input


def _build_historical_external_documents(
    workspace: MatchWorkspaceV1,
    statistics: MatchPlayerStatisticsPreparationV1,
    options: MatchHistoricalAnalysisOptionsV1,
) -> ApplicationExternalDocuments:
    if (
        not (
            options.immediate_review
            or uses_match_historical_information_set_family_v1(options)
        )
        or not options.use_profile_presets
        or statistics.opponent_statistics_input is None
    ):
        return ApplicationExternalDocuments()
    return ApplicationExternalDocuments(
        opponent_statistics_document=build_serializable_opponent_statistics_input(
            statistics.opponent_statistics_input
        ),
        opponent_statistics_reference=(
            f"match:{workspace.match_definition.match_id}:workspace:"
            f"{workspace.revision}:eligible-player-statistics"
        ),
    )


def _reconcile_historical_profile_summary(
    document: dict[str, Any],
    *,
    statistics: MatchPlayerStatisticsPreparationV1,
    external_documents: ApplicationExternalDocuments,
    game_id: str,
    requires_immediate_review: bool,
) -> None:
    summary = document.get("historical_opponent_profile_application_summary")
    has_external = external_documents.opponent_statistics_document is not None
    if not has_external:
        if summary is not None:
            raise SkatAIInvariantError(
                "Historical Result unexpectedly contains Profile application."
            )
        return
    if not isinstance(summary, dict):
        raise SkatAIInvariantError(
            "Historical Result omitted the requested Profile application summary."
        )
    if (
        summary.get("statistics_input_file")
        != external_documents.opponent_statistics_reference
        or summary.get("game_id") != game_id
    ):
        raise SkatAIInvariantError(
            "Historical Profile summary changed its source identity."
        )
    participant_matches = summary.get("participant_matches")
    if not isinstance(participant_matches, list) or len(participant_matches) != 3:
        raise SkatAIInvariantError(
            "Historical Profile summary must retain three participants."
        )
    expected_contexts = {
        context.player_id: context for context in statistics.participant_contexts
    }
    if {item.get("player_id") for item in participant_matches} != set(
        expected_contexts
    ):
        raise SkatAIInvariantError(
            "Historical Profile summary changed participant identities."
        )
    for item in participant_matches:
        context = expected_contexts[item["player_id"]]
        expected_match_status = (
            "matched" if context.eligible_for_match_analysis else "unmatched"
        )
        if item.get("match_status") != expected_match_status:
            raise SkatAIInvariantError(
                "Historical Profile summary disagrees with temporal eligibility."
            )
    historical_summary = document.get("historical_game_summary")
    review = (
        historical_summary.get("historical_game_review_summary")
        if isinstance(historical_summary, dict)
        else None
    )
    if requires_immediate_review and not isinstance(review, dict):
        raise SkatAIInvariantError(
            "Historical Profile application requires Immediate Review Decisions."
        )
    if isinstance(review, dict):
        decisions = review.get("decisions")
        if not isinstance(decisions, list):
            raise SkatAIInvariantError(
                "Historical Profile application requires Immediate Review Decisions."
            )
        participant_ids = set(expected_contexts)
        for decision in decisions:
            application = decision.get("opponent_profile_application")
            if not isinstance(application, dict):
                raise SkatAIInvariantError(
                    "Historical Profile application omitted one Decision binding."
                )
            identities = {
                application.get("acting_player_id"),
                application.get("left_opponent_player_id"),
                application.get("right_opponent_player_id"),
            }
            if identities != participant_ids:
                raise SkatAIInvariantError(
                    "Historical Decision Profile binding changed stable identities."
                )


def execute_match_historical_analysis_v1(
    workspace: MatchWorkspaceV1,
    *,
    match_position: int,
    options: MatchHistoricalAnalysisOptionsV1,
    dependencies: ApplicationWorkflowDependencies | None = None,
) -> MatchHistoricalAnalysisResultV1:
    """Executes the existing Historical Application once when evidence is strict."""
    if type(options) is not MatchHistoricalAnalysisOptionsV1:
        raise ValueError("options must be MatchHistoricalAnalysisOptionsV1.")
    historical = materialize_match_observed_game_historical_v1(
        workspace,
        match_position=match_position,
    )
    if historical.historical_game is None:
        return MatchHistoricalAnalysisResultV1(
            status="unavailable",
            match_id=historical.match_id,
            workspace_revision=workspace.revision,
            match_position=match_position,
            game_id=historical.game_id,
            unavailable_reason=historical.unavailable_reason,
            options=options,
            request=None,
            result=None,
        )

    statistics = build_match_player_statistics_preparation_v1(
        workspace.match_definition
    )
    root = {
        "historical_game_input": build_serializable_historical_record(
            historical.historical_game
        )
    }
    try:
        rebuilt = build_historical_game_from_document(root)
    except SkatAIInvariantError:
        raise
    except Exception as error:
        raise SkatAIInvariantError(
            "Materialized Match Game could not build a Historical Request."
        ) from error
    if rebuilt != historical.historical_game:
        raise SkatAIInvariantError(
            "Materialized Match Game changed during Historical Request construction."
        )
    request = RequestDocumentV1(
        workflow=WorkflowV1.HISTORICAL_GAME,
        document=root,
    )
    external_documents = _build_historical_external_documents(
        workspace,
        statistics,
        options,
    )
    has_external = external_documents.opponent_statistics_document is not None
    application_options = ApplicationExecutionOptions(
        historical_game=build_match_historical_application_options_v1(
            options,
            inject_statistics=has_external,
        )
    )
    input_reference = (
        f"match:{historical.match_id}:workspace:{workspace.revision}:"
        f"position:{match_position}:historical"
    )
    invocation = build_application_invocation(
        root,
        input_reference=input_reference,
        options=application_options,
        external_documents=external_documents,
    )
    execution = execute_application_invocation(
        invocation,
        dependencies=dependencies,
    )
    result = execution.result
    if result.workflow is not WorkflowV1.HISTORICAL_GAME:
        raise SkatAIInvariantError("Match Historical execution changed workflow identity.")
    result_document = result.to_dict()["document"]
    validate_output_document(result_document)
    if result_document.get("input_file") != input_reference:
        raise SkatAIInvariantError("Match Historical Result changed input identity.")
    summary = result_document.get("historical_game_summary")
    if not isinstance(summary, dict) or summary.get("game_id") != historical.game_id:
        raise SkatAIInvariantError("Match Historical Result changed Game identity.")
    reconcile_match_historical_information_set_result_v1(
        summary,
        game_id=historical.game_id,
        options=options,
    )
    _reconcile_historical_profile_summary(
        result_document,
        statistics=statistics,
        external_documents=external_documents,
        game_id=historical.game_id,
        requires_immediate_review=options.immediate_review,
    )
    return MatchHistoricalAnalysisResultV1(
        status="executed",
        match_id=historical.match_id,
        workspace_revision=workspace.revision,
        match_position=match_position,
        game_id=historical.game_id,
        unavailable_reason=None,
        options=options,
        request=request,
        result=result,
    )
