from __future__ import annotations

import inspect
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from skatmind.application.contracts import HistoricalGameApplicationOptions
from skatmind.historical_decision_snapshot import (
    build_historical_decision_snapshots,
    build_serializable_historical_decision_snapshot_summary,
)
from skatmind.historical_game import build_historical_game_summary
from skatmind.historical_game_review import build_historical_game_review_summary
from skatmind.historical_information_set_search_review import (
    HistoricalInformationSetSearchReviewSettingsV1,
    build_historical_information_set_search_effective_policy_settings_v1,
    build_historical_information_set_search_review_v1,
    build_serializable_historical_information_set_search_review_v1,
)
from skatmind.historical_opponent_profile_binding import (
    HistoricalOpponentProfileBindings,
    resolve_historical_opponent_profile_bindings,
)
from skatmind.historical_search_review import build_historical_search_review_summary
from skatmind.historical_tactical_motif_review import (
    build_historical_tactical_motif_review_v1,
    build_serializable_historical_tactical_motif_review_v1,
)
from skatmind.information_set_replay_coaching_report import (
    build_information_set_replay_coaching_report_v1,
    build_serializable_information_set_replay_coaching_report_v1,
)
from skatmind.input_loader import (
    build_historical_game_from_document,
    build_opponent_statistics_from_document,
)
from skatmind.replay_coaching_report import (
    build_historical_replay_coaching_public_summaries,
)
from skatmind.simulation import DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT

if TYPE_CHECKING:
    from skatmind.historical_review_provenance import (
        HistoricalReviewProvenanceCollector,
    )


@dataclass(frozen=True, slots=True)
class HistoricalGameWorkflowDependencies:
    """Legacy patch seams for Historical Game orchestration."""

    build_snapshots: Callable[..., Any] = build_historical_decision_snapshots
    build_immediate_review: Callable[..., Any] = build_historical_game_review_summary
    build_search_review: Callable[..., Any] = build_historical_search_review_summary
    build_information_set_search_review: Callable[..., Any] = (
        build_historical_information_set_search_review_v1
    )
    serialize_information_set_search_review: Callable[..., Any] = (
        build_serializable_historical_information_set_search_review_v1
    )
    build_information_set_replay_coaching: Callable[..., Any] = (
        build_information_set_replay_coaching_report_v1
    )
    serialize_information_set_replay_coaching: Callable[..., Any] = (
        build_serializable_information_set_replay_coaching_report_v1
    )
    build_replay_coaching: Callable[..., Any] = build_historical_replay_coaching_public_summaries
    build_tactical_motif_review: Callable[..., Any] = (
        build_historical_tactical_motif_review_v1
    )
    serialize_tactical_motif_review: Callable[..., Any] = (
        build_serializable_historical_tactical_motif_review_v1
    )


_DEFAULT_DEPENDENCIES = HistoricalGameWorkflowDependencies()


def _call_with_optional_provenance(
    callback: Callable[..., Any],
    *,
    provenance_collector: HistoricalReviewProvenanceCollector | None,
    kwargs: dict[str, Any],
) -> Any:
    signature = inspect.signature(callback)
    supports_provenance = "provenance_collector" in signature.parameters or any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in signature.parameters.values()
    )
    if supports_provenance:
        kwargs["provenance_collector"] = provenance_collector
    return callback(**kwargs)


def _supports_keyword(callback: Callable[..., Any], keyword: str) -> bool:
    signature = inspect.signature(callback)
    return keyword in signature.parameters or any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in signature.parameters.values()
    )


def _build_effective_review_provenance_settings(
    options: HistoricalGameApplicationOptions,
) -> dict[str, object]:
    """Returns effective review settings without private random seeds."""
    settings: dict[str, object] = {
        "decision_snapshots": options.decision_snapshots,
        "immediate_review": options.immediate_review,
        "search_review": options.search_review,
        "information_set_search_review": options.information_set_search_review,
        "information_set_replay_coaching": (
            options.information_set_replay_coaching
        ),
        "replay_coaching": options.replay_coaching,
        "immediate_sample_count": (
            options.immediate_sample_count
            if options.immediate_sample_count is not None
            else DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT
        ),
        "search_budget_profile": (
            options.search_budget_profile
            if (
                options.search_review
                or options.information_set_search_review
                or options.information_set_replay_coaching
                or options.replay_coaching
            )
            else None
        ),
        "opponent_policy_preset_override": options.opponent_policy_preset_override,
        "opponent_lead_policy_override": options.opponent_lead_policy_override,
        "opponent_response_policy_override": options.opponent_response_policy_override,
        "left_opponent_lead_policy_override": (options.left_opponent_lead_policy_override),
        "left_opponent_response_policy_override": (options.left_opponent_response_policy_override),
        "right_opponent_lead_policy_override": (options.right_opponent_lead_policy_override),
        "right_opponent_response_policy_override": (
            options.right_opponent_response_policy_override
        ),
        "use_profile_presets_override": options.use_profile_presets_override,
    }
    if options.historical_tactical_motif_review:
        settings["historical_tactical_motif_review"] = True
    return settings


def execute_historical_game_workflow(
    root_document: dict[str, Any],
    *,
    input_reference: str,
    options: HistoricalGameApplicationOptions,
    opponent_statistics_document: dict[str, Any] | None = None,
    opponent_statistics_reference: str | None = None,
    provenance_collector: HistoricalReviewProvenanceCollector | None = None,
    dependencies: HistoricalGameWorkflowDependencies = _DEFAULT_DEPENDENCIES,
) -> dict[str, Any]:
    """Executes the complete Historical Game workflow without transport I/O."""
    existing_search_family = options.search_review or options.replay_coaching
    information_set_search_family = (
        options.information_set_search_review
        or options.information_set_replay_coaching
    )
    if existing_search_family and information_set_search_family:
        information_set_mode = (
            "Information-set Search Review"
            if options.information_set_search_review
            else "Information-set Replay Coaching"
        )
        existing_mode = (
            "Search Review" if options.search_review else "Replay Coaching"
        )
        raise ValueError(
            f"{information_set_mode} cannot be combined with {existing_mode}."
        )
    record = build_historical_game_from_document(
        root_document,
        validate_workflow=False,
        validate_game_event_chain=False,
    )
    historical_game_summary = build_historical_game_summary(record)
    opponent_profile_bindings: HistoricalOpponentProfileBindings | None = None
    if opponent_statistics_document is not None:
        statistics_input = build_opponent_statistics_from_document(opponent_statistics_document)
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
        or options.information_set_search_review
        or options.information_set_replay_coaching
        or options.replay_coaching
        or options.historical_tactical_motif_review
    ):
        snapshot_summary = dependencies.build_snapshots(historical_game_summary)
        serialized_snapshot_summary = (
            build_serializable_historical_decision_snapshot_summary(snapshot_summary)
        )
        if provenance_collector is not None:
            provenance_collector.capture_decision_inputs(
                snapshot_summary,
                effective_review_settings=(_build_effective_review_provenance_settings(options)),
            )
            if snapshot_summary.snapshots or options.decision_snapshots:
                provenance_collector.capture_snapshot_summary(serialized_snapshot_summary)
    if options.decision_snapshots:
        if snapshot_summary is None or serialized_snapshot_summary is None:
            raise ValueError("Historical decision snapshots were not generated.")
        historical_game_summary["decision_snapshot_summary"] = serialized_snapshot_summary
    if options.immediate_review:
        if snapshot_summary is None:
            raise ValueError("Historical decision snapshots were not generated.")
        immediate_review_summary = _call_with_optional_provenance(
            dependencies.build_immediate_review,
            provenance_collector=provenance_collector,
            kwargs={
                "snapshot_summary": snapshot_summary,
                "historical_record": record,
                "sample_count": (
                    options.immediate_sample_count
                    if options.immediate_sample_count is not None
                    else DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT
                ),
                "base_random_seed": options.immediate_base_random_seed,
                "opponent_profile_bindings": opponent_profile_bindings,
                "opponent_policy_preset_override": (options.opponent_policy_preset_override),
                "opponent_lead_policy_override": (options.opponent_lead_policy_override),
                "opponent_response_policy_override": (options.opponent_response_policy_override),
                "left_opponent_lead_policy_override": (options.left_opponent_lead_policy_override),
                "left_opponent_response_policy_override": (
                    options.left_opponent_response_policy_override
                ),
                "right_opponent_lead_policy_override": (
                    options.right_opponent_lead_policy_override
                ),
                "right_opponent_response_policy_override": (
                    options.right_opponent_response_policy_override
                ),
            },
        )
        historical_game_summary["historical_game_review_summary"] = immediate_review_summary
        if provenance_collector is not None:
            provenance_collector.capture_immediate_summary(immediate_review_summary)
    if information_set_search_family:
        if snapshot_summary is None:
            raise ValueError("Historical decision snapshots were not generated.")
        if options.search_seed is None:
            raise ValueError(
                "Historical Information-set Search Review or Coaching requires an explicit "
                "Search seed."
            )
        effective_policy_settings_by_decision = {
            snapshot.decision_index: (
                build_historical_information_set_search_effective_policy_settings_v1(
                    snapshot,
                    record,
                    opponent_profile_bindings=opponent_profile_bindings,
                    opponent_policy_preset_override=(
                        options.opponent_policy_preset_override
                    ),
                    opponent_lead_policy_override=(
                        options.opponent_lead_policy_override
                    ),
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
            for snapshot in snapshot_summary.snapshots
        }
        if provenance_collector is not None:
            for snapshot in snapshot_summary.snapshots:
                provenance_collector.capture_information_set_search_policy_settings(
                    snapshot=snapshot,
                    effective_settings=effective_policy_settings_by_decision[
                        snapshot.decision_index
                    ],
                )
        retained_information_set_search_review = (
            dependencies.build_information_set_search_review(
                snapshot_summary=snapshot_summary,
                historical_record=record,
                settings=HistoricalInformationSetSearchReviewSettingsV1(
                    base_search_seed=options.search_seed,
                    search_budget_profile=options.search_budget_profile,
                    immediate_sample_count=(
                        options.immediate_sample_count
                        if options.immediate_sample_count is not None
                        else DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT
                    ),
                    immediate_base_random_seed=(
                        options.immediate_base_random_seed
                    ),
                ),
                effective_policy_settings_by_decision=(
                    effective_policy_settings_by_decision
                ),
            )
        )
        if options.information_set_search_review:
            information_set_search_review_summary = (
                dict(retained_information_set_search_review)
                if isinstance(retained_information_set_search_review, Mapping)
                else dependencies.serialize_information_set_search_review(
                    retained_information_set_search_review
                )
            )
            historical_game_summary[
                "historical_information_set_search_review_summary"
            ] = information_set_search_review_summary
            if provenance_collector is not None:
                provenance_collector.capture_information_set_search_summary(
                    information_set_search_review_summary
                )
        if options.information_set_replay_coaching:
            information_set_replay_coaching_report = (
                dependencies.build_information_set_replay_coaching(
                    historical_record=record,
                    source_review=retained_information_set_search_review,
                    historical_game_summary=historical_game_summary,
                )
            )
            information_set_replay_coaching_summary = (
                dependencies.serialize_information_set_replay_coaching(
                    information_set_replay_coaching_report
                )
            )
            historical_game_summary[
                "historical_information_set_replay_coaching_summary"
            ] = information_set_replay_coaching_summary
            if provenance_collector is not None:
                provenance_collector.capture_information_set_replay_coaching_report(
                    information_set_replay_coaching_summary
                )
    if options.replay_coaching:
        if snapshot_summary is None:
            raise ValueError("Historical decision snapshots were not generated.")
        if options.search_seed is None:
            raise ValueError("Historical Replay Coaching requires an explicit Search seed.")
        replay_coaching_kwargs = {
            "snapshot_summary": snapshot_summary,
            "historical_record": record,
            "base_search_seed": options.search_seed,
            "search_budget_profile": options.search_budget_profile,
            "immediate_sample_count": (
                options.immediate_sample_count
                if options.immediate_sample_count is not None
                else DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT
            ),
            "immediate_base_random_seed": options.immediate_base_random_seed,
        }
        if _supports_keyword(
            dependencies.build_replay_coaching,
            "historical_game_summary",
        ):
            replay_coaching_kwargs["historical_game_summary"] = historical_game_summary
        public_summaries = _call_with_optional_provenance(
            dependencies.build_replay_coaching,
            provenance_collector=provenance_collector,
            kwargs=replay_coaching_kwargs,
        )
        historical_game_summary["historical_replay_coaching_summary"] = public_summaries[
            "historical_replay_coaching_summary"
        ]
        if options.search_review:
            historical_game_summary["historical_search_review_summary"] = public_summaries[
                "historical_search_review_summary"
            ]
            if provenance_collector is not None:
                provenance_collector.capture_search_summary(
                    public_summaries["historical_search_review_summary"]
                )
    elif options.search_review:
        if snapshot_summary is None:
            raise ValueError("Historical decision snapshots were not generated.")
        if options.search_seed is None:
            raise ValueError("Historical Search Review requires an explicit Search seed.")
        search_review_summary = _call_with_optional_provenance(
            dependencies.build_search_review,
            provenance_collector=provenance_collector,
            kwargs={
                "snapshot_summary": snapshot_summary,
                "historical_record": record,
                "base_search_seed": options.search_seed,
                "search_budget_profile": options.search_budget_profile,
                "immediate_sample_count": (
                    options.immediate_sample_count
                    if options.immediate_sample_count is not None
                    else DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT
                ),
                "immediate_base_random_seed": options.immediate_base_random_seed,
            },
        )
        historical_game_summary["historical_search_review_summary"] = search_review_summary
        if provenance_collector is not None:
            provenance_collector.capture_search_summary(search_review_summary)

    if options.historical_tactical_motif_review:
        if snapshot_summary is None:
            raise ValueError("Historical decision snapshots were not generated.")
        tactical_review = dependencies.build_tactical_motif_review(
            historical_game_result=historical_game_summary,
            decision_snapshot_summary=snapshot_summary,
        )
        tactical_summary = dependencies.serialize_tactical_motif_review(
            tactical_review
        )
        historical_game_summary[
            "historical_tactical_motif_review_summary"
        ] = tactical_summary
        if provenance_collector is not None:
            provenance_collector.capture_tactical_motif_summary(tactical_summary)

    result = {
        "input_file": input_reference,
        "historical_game_summary": historical_game_summary,
    }
    if opponent_profile_bindings is not None:
        result["historical_opponent_profile_application_summary"] = (
            opponent_profile_bindings.application_summary
        )
    return result
