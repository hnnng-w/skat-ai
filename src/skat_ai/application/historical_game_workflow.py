from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from skat_ai.application.contracts import HistoricalGameApplicationOptions
from skat_ai.historical_decision_snapshot import (
    build_historical_decision_snapshots,
    build_serializable_historical_decision_snapshot_summary,
)
from skat_ai.historical_game import build_historical_game_summary
from skat_ai.historical_game_review import build_historical_game_review_summary
from skat_ai.historical_opponent_profile_binding import (
    HistoricalOpponentProfileBindings,
    resolve_historical_opponent_profile_bindings,
)
from skat_ai.historical_search_review import build_historical_search_review_summary
from skat_ai.input_loader import (
    build_historical_game_from_document,
    build_opponent_statistics_from_document,
)
from skat_ai.replay_coaching_report import (
    build_historical_replay_coaching_public_summaries,
)
from skat_ai.simulation import DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT


@dataclass(frozen=True, slots=True)
class HistoricalGameWorkflowDependencies:
    """Legacy patch seams for Historical Game orchestration."""

    build_snapshots: Callable[..., Any] = build_historical_decision_snapshots
    build_immediate_review: Callable[..., Any] = build_historical_game_review_summary
    build_search_review: Callable[..., Any] = build_historical_search_review_summary
    build_replay_coaching: Callable[..., Any] = (
        build_historical_replay_coaching_public_summaries
    )


_DEFAULT_DEPENDENCIES = HistoricalGameWorkflowDependencies()


def execute_historical_game_workflow(
    root_document: dict[str, Any],
    *,
    input_reference: str,
    options: HistoricalGameApplicationOptions,
    opponent_statistics_document: dict[str, Any] | None = None,
    opponent_statistics_reference: str | None = None,
    dependencies: HistoricalGameWorkflowDependencies = _DEFAULT_DEPENDENCIES,
) -> dict[str, Any]:
    """Executes the complete Historical Game workflow without transport I/O."""
    record = build_historical_game_from_document(
        root_document,
        validate_workflow=False,
    )
    historical_game_summary = build_historical_game_summary(record)
    opponent_profile_bindings: HistoricalOpponentProfileBindings | None = None
    if opponent_statistics_document is not None:
        statistics_input = build_opponent_statistics_from_document(
            opponent_statistics_document
        )
        opponent_profile_bindings = resolve_historical_opponent_profile_bindings(
            record,
            statistics_input,
            statistics_input_file=opponent_statistics_reference,
        )

    snapshot_summary = None
    if (
        options.decision_snapshots
        or options.immediate_review
        or options.search_review
        or options.replay_coaching
    ):
        snapshot_summary = dependencies.build_snapshots(historical_game_summary)
    if options.decision_snapshots:
        if snapshot_summary is None:
            raise ValueError("Historical decision snapshots were not generated.")
        historical_game_summary["decision_snapshot_summary"] = (
            build_serializable_historical_decision_snapshot_summary(snapshot_summary)
        )
    if options.immediate_review:
        if snapshot_summary is None:
            raise ValueError("Historical decision snapshots were not generated.")
        historical_game_summary["historical_game_review_summary"] = (
            dependencies.build_immediate_review(
                snapshot_summary=snapshot_summary,
                historical_record=record,
                sample_count=(
                    options.immediate_sample_count
                    if options.immediate_sample_count is not None
                    else DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT
                ),
                base_random_seed=options.immediate_base_random_seed,
                opponent_profile_bindings=opponent_profile_bindings,
                opponent_policy_preset_override=(
                    options.opponent_policy_preset_override
                ),
                opponent_lead_policy_override=options.opponent_lead_policy_override,
                opponent_response_policy_override=(
                    options.opponent_response_policy_override
                ),
                left_opponent_lead_policy_override=(
                    options.left_opponent_lead_policy_override
                ),
                left_opponent_response_policy_override=(
                    options.left_opponent_response_policy_override
                ),
                right_opponent_lead_policy_override=(
                    options.right_opponent_lead_policy_override
                ),
                right_opponent_response_policy_override=(
                    options.right_opponent_response_policy_override
                ),
            )
        )
    if options.replay_coaching:
        if snapshot_summary is None:
            raise ValueError("Historical decision snapshots were not generated.")
        if options.search_seed is None:
            raise ValueError(
                "Historical Replay Coaching requires an explicit Search seed."
            )
        public_summaries = dependencies.build_replay_coaching(
            snapshot_summary=snapshot_summary,
            historical_record=record,
            base_search_seed=options.search_seed,
            search_budget_profile=options.search_budget_profile,
            immediate_sample_count=(
                options.immediate_sample_count
                if options.immediate_sample_count is not None
                else DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT
            ),
            immediate_base_random_seed=options.immediate_base_random_seed,
        )
        historical_game_summary["historical_replay_coaching_summary"] = (
            public_summaries["historical_replay_coaching_summary"]
        )
        if options.search_review:
            historical_game_summary["historical_search_review_summary"] = (
                public_summaries["historical_search_review_summary"]
            )
    elif options.search_review:
        if snapshot_summary is None:
            raise ValueError("Historical decision snapshots were not generated.")
        if options.search_seed is None:
            raise ValueError(
                "Historical Search Review requires an explicit Search seed."
            )
        historical_game_summary["historical_search_review_summary"] = (
            dependencies.build_search_review(
                snapshot_summary=snapshot_summary,
                historical_record=record,
                base_search_seed=options.search_seed,
                search_budget_profile=options.search_budget_profile,
                immediate_sample_count=(
                    options.immediate_sample_count
                    if options.immediate_sample_count is not None
                    else DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT
                ),
                immediate_base_random_seed=options.immediate_base_random_seed,
            )
        )

    result = {
        "input_file": input_reference,
        "historical_game_summary": historical_game_summary,
    }
    if opponent_profile_bindings is not None:
        result["historical_opponent_profile_application_summary"] = (
            opponent_profile_bindings.application_summary
        )
    return result
