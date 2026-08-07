from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from skat_ai.api.v1.contracts import RequestDocumentV1, ResultDocumentV1, WorkflowV1
from skat_ai.application.contracts import (
    APPLICATION_ORCHESTRATION_VERSION,
    TRAINING_DATASET_APPLICATION_OPERATIONS,
    ApplicationArtifact,
    ApplicationExecutionOptions,
    ApplicationExecutionResult,
    ApplicationExternalDocuments,
    ApplicationInvocation,
    HistoricalGameApplicationOptions,
    PositionAnalysisApplicationOptions,
    TrainingDatasetApplicationOptions,
)
from skat_ai.application.historical_game_workflow import (
    HistoricalGameWorkflowDependencies,
    execute_historical_game_workflow,
)
from skat_ai.application.position_workflow import (
    PositionWorkflowDependencies,
    execute_position_analysis_workflow,
)
from skat_ai.application.provenance import ApplicationProvenanceBundle
from skat_ai.application.simple_workflows import (
    SimpleWorkflowDependencies,
    execute_fixed_three_player_historical_list_comparison_workflow,
    execute_fixed_three_player_historical_list_workflow,
    execute_opponent_statistics_workflow,
    execute_training_dataset_preparation_workflow,
)
from skat_ai.application.training_dataset_workflow import (
    TrainingDatasetWorkflowDependencies,
    execute_training_dataset_workflow,
)
from skat_ai.card_selection import VALID_MULTI_STEP_POLICIES
from skat_ai.errors import SkatAIInvariantError, SkatAIWorkflowError
from skat_ai.input_loader import get_input_workflow
from skat_ai.input_validation import MAX_SAMPLE_COUNT
from skat_ai.opponent_policy import VALID_OPPONENT_CARD_POLICIES
from skat_ai.search_budget_profiles import (
    HISTORICAL_REVIEW_SEARCH_BUDGET_PROFILE,
    SEARCH_BUDGET_PROFILE_IDENTIFIERS,
)

_PARTITIONS = ("train", "validation", "test")
_POSITION_POLICY_PRESETS = (
    "simple_lowest",
    "cautious_defender",
    "aggressive_points",
    "random",
)


@dataclass(frozen=True, slots=True)
class ApplicationWorkflowDependencies:
    """Internal dependency seams used by legacy Root wrappers and tests."""

    position: PositionWorkflowDependencies = PositionWorkflowDependencies()
    historical_game: HistoricalGameWorkflowDependencies = (
        HistoricalGameWorkflowDependencies()
    )
    training_dataset: TrainingDatasetWorkflowDependencies = (
        TrainingDatasetWorkflowDependencies()
    )
    simple: SimpleWorkflowDependencies = SimpleWorkflowDependencies()


def _default_options_for_workflow(workflow: WorkflowV1) -> ApplicationExecutionOptions:
    if workflow is WorkflowV1.POSITION_ANALYSIS:
        return ApplicationExecutionOptions(
            position_analysis=PositionAnalysisApplicationOptions()
        )
    if workflow is WorkflowV1.HISTORICAL_GAME:
        return ApplicationExecutionOptions(
            historical_game=HistoricalGameApplicationOptions()
        )
    if workflow is WorkflowV1.TRAINING_DATASET:
        return ApplicationExecutionOptions(
            training_dataset=TrainingDatasetApplicationOptions()
        )
    return ApplicationExecutionOptions()


def build_application_invocation(
    root_document: Mapping[str, object],
    *,
    input_reference: str,
    options: ApplicationExecutionOptions | None = None,
    external_documents: ApplicationExternalDocuments | None = None,
) -> ApplicationInvocation:
    """Builds one immutable invocation from a caller-supplied Root document."""
    if not isinstance(root_document, Mapping):
        raise SkatAIWorkflowError("Root document must be an object.")
    workflow_name = get_input_workflow(dict(root_document))
    try:
        workflow = WorkflowV1(workflow_name)
    except ValueError as error:
        raise SkatAIInvariantError(
            f"Unsupported workflow returned by get_input_workflow(): {workflow_name!r}."
        ) from error
    invocation_options = options or _default_options_for_workflow(workflow)
    invocation_external_documents = (
        external_documents or ApplicationExternalDocuments()
    )
    return ApplicationInvocation(
        request=RequestDocumentV1(workflow=workflow, document=root_document),
        input_reference=input_reference,
        options=invocation_options,
        external_documents=invocation_external_documents,
    )


def _validate_positive_sample_count(value: int | None, name: str) -> None:
    if value is None:
        return
    if value <= 0:
        raise SkatAIWorkflowError(f"{name} must be a positive integer.")
    if value > MAX_SAMPLE_COUNT:
        raise SkatAIWorkflowError(
            f"{name} must be at most {MAX_SAMPLE_COUNT}."
        )


def _validate_policy(value: str | None, name: str) -> None:
    if value is not None and value not in VALID_OPPONENT_CARD_POLICIES:
        raise SkatAIWorkflowError(
            f"{name} must be one of {tuple(VALID_OPPONENT_CARD_POLICIES)}."
        )


def _validate_position_options(
    options: PositionAnalysisApplicationOptions,
    external_documents: ApplicationExternalDocuments,
) -> None:
    _validate_positive_sample_count(
        options.sample_count_override,
        "sample_count_override",
    )
    _validate_positive_sample_count(
        options.expected_value_sample_count,
        "expected_value_sample_count",
    )
    if options.multi_step_count is not None and options.multi_step_count <= 0:
        raise SkatAIWorkflowError("multi_step_count must be a positive integer.")
    if options.opponent_strategy_override not in (None, "basic", "random"):
        raise SkatAIWorkflowError(
            "opponent_strategy_override must be 'basic', 'random', or None."
        )
    if (
        options.opponent_policy_preset_override is not None
        and options.opponent_policy_preset_override not in _POSITION_POLICY_PRESETS
    ):
        raise SkatAIWorkflowError(
            "opponent_policy_preset_override must be a supported preset."
        )
    for name in (
        "opponent_lead_policy_override",
        "opponent_response_policy_override",
        "left_opponent_lead_policy_override",
        "left_opponent_response_policy_override",
        "right_opponent_lead_policy_override",
        "right_opponent_response_policy_override",
    ):
        _validate_policy(getattr(options, name), name)
    if (
        options.card_selection_policy is not None
        and options.card_selection_policy not in VALID_MULTI_STEP_POLICIES
    ):
        raise SkatAIWorkflowError(
            "card_selection_policy must be a supported Multi-Step policy."
        )
    if options.compare_policies and options.multi_step_count is None:
        raise SkatAIWorkflowError("compare_policies requires multi_step_count.")
    if options.comparison_only and not options.compare_policies:
        raise SkatAIWorkflowError(
            "comparison_only requires compare_policies to be enabled."
        )
    left_id = options.left_opponent_player_id
    right_id = options.right_opponent_player_id
    for name, player_id in (
        ("left_opponent_player_id", left_id),
        ("right_opponent_player_id", right_id),
    ):
        if player_id is not None and (
            not player_id or player_id != player_id.strip()
        ):
            raise SkatAIWorkflowError(
                f"{name} must be a non-empty, non-padded string."
            )
    if left_id is not None and left_id == right_id:
        raise SkatAIWorkflowError(
            "left_opponent_player_id and right_opponent_player_id must be different."
        )
    has_external = external_documents.opponent_statistics_document is not None
    if not has_external and (left_id is not None or right_id is not None):
        raise SkatAIWorkflowError(
            "Opponent player IDs require injected opponent statistics."
        )
    if has_external and left_id is None and right_id is None:
        raise SkatAIWorkflowError(
            "Injected opponent statistics require at least one opponent player ID."
        )


def _historical_profile_option_names(
    options: HistoricalGameApplicationOptions,
) -> tuple[str, ...]:
    names = (
        "opponent_policy_preset_override",
        "opponent_lead_policy_override",
        "opponent_response_policy_override",
        "left_opponent_lead_policy_override",
        "left_opponent_response_policy_override",
        "right_opponent_lead_policy_override",
        "right_opponent_response_policy_override",
    )
    supplied = tuple(name for name in names if getattr(options, name) is not None)
    if options.use_profile_presets_override:
        supplied += ("use_profile_presets_override",)
    return supplied


def _validate_historical_options(
    options: HistoricalGameApplicationOptions,
    external_documents: ApplicationExternalDocuments,
) -> None:
    _validate_positive_sample_count(
        options.immediate_sample_count,
        "immediate_sample_count",
    )
    needs_search = options.search_review or options.replay_coaching
    if needs_search and options.search_seed is None:
        raise SkatAIWorkflowError(
            "Historical Search Review and Replay Coaching require search_seed."
        )
    if options.search_seed is not None and not needs_search:
        raise SkatAIWorkflowError(
            "search_seed requires Search Review or Replay Coaching."
        )
    if options.search_budget_profile not in SEARCH_BUDGET_PROFILE_IDENTIFIERS:
        raise SkatAIWorkflowError(
            "search_budget_profile must be a supported Search budget profile."
        )
    if (
        not needs_search
        and options.search_budget_profile
        != HISTORICAL_REVIEW_SEARCH_BUDGET_PROFILE
    ):
        raise SkatAIWorkflowError(
            "search_budget_profile requires Search Review or Replay Coaching."
        )
    has_review = (
        options.immediate_review
        or options.search_review
        or options.replay_coaching
    )
    if (
        options.immediate_sample_count is not None
        or options.immediate_base_random_seed is not None
    ) and not has_review:
        raise SkatAIWorkflowError(
            "Immediate samples and seed require a Historical Review operation."
        )
    has_external = external_documents.opponent_statistics_document is not None
    profile_options = _historical_profile_option_names(options)
    if has_external and not options.immediate_review:
        raise SkatAIWorkflowError(
            "Injected opponent statistics require Immediate Historical Review."
        )
    if has_external and not options.use_profile_presets_override:
        raise SkatAIWorkflowError(
            "Injected opponent statistics require effective Profile Presets opt-in."
        )
    if not has_external and profile_options:
        raise SkatAIWorkflowError(
            "Historical opponent policy and Profile Preset overrides require "
            "injected opponent statistics."
        )
    for name in profile_options:
        if name == "use_profile_presets_override":
            continue
        value = getattr(options, name)
        if name == "opponent_policy_preset_override":
            if value not in _POSITION_POLICY_PRESETS:
                raise SkatAIWorkflowError(
                    "opponent_policy_preset_override must be a supported preset."
                )
        else:
            _validate_policy(value, name)


def _validate_partitions(values: tuple[str, ...], name: str) -> None:
    if not values or any(value not in _PARTITIONS for value in values):
        raise SkatAIWorkflowError(
            f"{name} must contain supported Dataset partitions."
        )


def _validate_training_dataset_options(
    options: TrainingDatasetApplicationOptions,
) -> None:
    if options.operation not in TRAINING_DATASET_APPLICATION_OPERATIONS:
        raise SkatAIWorkflowError(
            "Training Dataset operation must be exactly one supported operation."
        )
    _validate_partitions(
        options.rolling_source_partitions,
        "rolling_source_partitions",
    )
    _validate_partitions(
        options.rolling_evaluation_partitions,
        "rolling_evaluation_partitions",
    )
    _validate_partitions(
        options.bounded_search_partitions,
        "bounded_search_partitions",
    )
    if options.aggregation_included_partitions is not None:
        _validate_partitions(
            options.aggregation_included_partitions,
            "aggregation_included_partitions",
        )
    defaults = TrainingDatasetApplicationOptions()
    if options.operation == "partition_audit":
        if options.partition_audit_mode not in (
            None,
            "report_only",
            "known_opponent",
            "unseen_player",
        ):
            raise SkatAIWorkflowError(
                "partition_audit_mode must be a supported audit mode."
            )
    elif options.partition_audit_mode is not None:
        raise SkatAIWorkflowError(
            "partition_audit_mode requires the partition_audit operation."
        )
    if options.operation == "rolling_opponent_policy_evaluation":
        overlap = sorted(
            set(options.rolling_source_partitions).intersection(
                options.rolling_evaluation_partitions
            )
        )
        if overlap:
            raise SkatAIWorkflowError(
                "Rolling source and evaluation partitions must be disjoint; "
                f"overlap: {overlap}."
            )
    elif (
        options.rolling_source_partitions != defaults.rolling_source_partitions
        or options.rolling_evaluation_partitions
        != defaults.rolling_evaluation_partitions
    ):
        raise SkatAIWorkflowError(
            "Rolling partition settings require the "
            "rolling_opponent_policy_evaluation operation."
        )
    if options.operation == "bounded_search_evaluation":
        if options.bounded_search_seed is None:
            raise SkatAIWorkflowError(
                "bounded_search_evaluation requires bounded_search_seed."
            )
        if (
            options.bounded_search_budget_profile
            not in SEARCH_BUDGET_PROFILE_IDENTIFIERS
        ):
            raise SkatAIWorkflowError(
                "bounded_search_budget_profile must be a supported profile."
            )
        if (
            options.bounded_search_max_decisions is not None
            and options.bounded_search_max_decisions <= 0
        ):
            raise SkatAIWorkflowError(
                "bounded_search_max_decisions must be positive."
            )
    elif (
        options.bounded_search_seed is not None
        or options.bounded_search_partitions
        != defaults.bounded_search_partitions
        or options.bounded_search_budget_profile
        != defaults.bounded_search_budget_profile
        or options.bounded_search_max_decisions is not None
    ):
        raise SkatAIWorkflowError(
            "Bounded Search settings require the bounded_search_evaluation operation."
        )
    aggregation_settings_supplied = (
        options.aggregation_included_partitions is not None
        or options.aggregation_before is not None
        or options.export_opponent_statistics
    )
    if (
        options.operation != "historical_opponent_statistics_aggregation"
        and aggregation_settings_supplied
    ):
        raise SkatAIWorkflowError(
            "Historical aggregation settings require the "
            "historical_opponent_statistics_aggregation operation."
        )


def validate_application_invocation(invocation: ApplicationInvocation) -> None:
    """Validates workflow and non-transport option compatibility."""
    if not isinstance(invocation, ApplicationInvocation):
        raise SkatAIWorkflowError("invocation must be an ApplicationInvocation.")
    workflow = invocation.request.workflow
    options = invocation.options
    configured = {
        WorkflowV1.POSITION_ANALYSIS: options.position_analysis,
        WorkflowV1.HISTORICAL_GAME: options.historical_game,
        WorkflowV1.TRAINING_DATASET: options.training_dataset,
    }
    for option_workflow, workflow_options in configured.items():
        if option_workflow is workflow:
            if workflow_options is None:
                raise SkatAIWorkflowError(
                    f"{workflow.value} requires matching Application options."
                )
        elif workflow_options is not None:
            raise SkatAIWorkflowError(
                f"{option_workflow.value} options cannot be used with "
                f"{workflow.value}."
            )

    external = invocation.external_documents
    if workflow not in (
        WorkflowV1.POSITION_ANALYSIS,
        WorkflowV1.HISTORICAL_GAME,
    ) and external.opponent_statistics_document is not None:
        raise SkatAIWorkflowError(
            "Injected opponent statistics are supported only for Position Analysis "
            "and Historical Game workflows."
        )
    if workflow is WorkflowV1.POSITION_ANALYSIS:
        assert options.position_analysis is not None
        _validate_position_options(options.position_analysis, external)
    elif workflow is WorkflowV1.HISTORICAL_GAME:
        assert options.historical_game is not None
        _validate_historical_options(options.historical_game, external)
    elif workflow is WorkflowV1.TRAINING_DATASET:
        assert options.training_dataset is not None
        _validate_training_dataset_options(options.training_dataset)


def _position_handler(
    root: dict[str, Any],
    invocation: ApplicationInvocation,
    dependencies: ApplicationWorkflowDependencies,
) -> tuple[
    dict[str, Any],
    tuple[ApplicationArtifact, ...],
    ApplicationProvenanceBundle | None,
]:
    options = invocation.options.position_analysis
    if options is None:
        raise SkatAIInvariantError("Position handler received no Position options.")
    analysis_mode = root.get("analysis_mode", "live_decision")
    if analysis_mode == "live_decision":
        from skat_ai.live_analysis_provenance import LiveAnalysisProvenanceCollector

        provenance_collector = LiveAnalysisProvenanceCollector()
    elif analysis_mode == "post_game_review":
        from skat_ai.retrospective_review_provenance import (
            FlatRetrospectiveProvenanceCollector,
        )

        provenance_collector = FlatRetrospectiveProvenanceCollector()
    else:
        provenance_collector = None
    result = execute_position_analysis_workflow(
        root,
        input_reference=invocation.input_reference,
        options=options,
        opponent_statistics_document=(
            invocation.external_documents.opponent_statistics_to_dict()
        ),
        opponent_statistics_reference=(
            invocation.external_documents.opponent_statistics_reference
        ),
        provenance_collector=provenance_collector,
        dependencies=dependencies.position,
    )
    provenance = (
        provenance_collector.build_bundle(
            result,
            external_reference=(
                invocation.external_documents.opponent_statistics_reference
            ),
        )
        if provenance_collector is not None
        else None
    )
    return (result, (), provenance)


def _historical_handler(
    root: dict[str, Any],
    invocation: ApplicationInvocation,
    dependencies: ApplicationWorkflowDependencies,
) -> tuple[
    dict[str, Any],
    tuple[ApplicationArtifact, ...],
    ApplicationProvenanceBundle | None,
]:
    options = invocation.options.historical_game
    if options is None:
        raise SkatAIInvariantError(
            "Historical handler received no Historical options."
        )
    needs_provenance = any(
        (
            options.decision_snapshots,
            options.immediate_review,
            options.search_review,
            options.replay_coaching,
        )
    )
    provenance_collector = None
    if needs_provenance:
        from skat_ai.historical_review_provenance import (
            HistoricalReviewProvenanceCollector,
        )

        provenance_collector = HistoricalReviewProvenanceCollector(
            external_reference=(
                invocation.external_documents.opponent_statistics_reference
            )
        )
    result = execute_historical_game_workflow(
        root,
        input_reference=invocation.input_reference,
        options=options,
        opponent_statistics_document=(
            invocation.external_documents.opponent_statistics_to_dict()
        ),
        opponent_statistics_reference=(
            invocation.external_documents.opponent_statistics_reference
        ),
        provenance_collector=provenance_collector,
        dependencies=dependencies.historical_game,
    )
    provenance = (
        provenance_collector.build_bundle(result)
        if provenance_collector is not None
        else None
    )
    return (result, (), provenance)


def _training_dataset_handler(
    root: dict[str, Any],
    invocation: ApplicationInvocation,
    _dependencies: ApplicationWorkflowDependencies,
) -> tuple[
    dict[str, Any],
    tuple[ApplicationArtifact, ...],
    ApplicationProvenanceBundle | None,
]:
    options = invocation.options.training_dataset
    if options is None:
        raise SkatAIInvariantError(
            "Training Dataset handler received no Training Dataset options."
        )
    result, artifacts = execute_training_dataset_workflow(
        root,
        input_reference=invocation.input_reference,
        options=options,
        dependencies=_dependencies.training_dataset,
    )
    return result, artifacts, None


def _preparation_handler(
    root: dict[str, Any],
    invocation: ApplicationInvocation,
    _dependencies: ApplicationWorkflowDependencies,
) -> tuple[
    dict[str, Any],
    tuple[ApplicationArtifact, ...],
    ApplicationProvenanceBundle | None,
]:
    return (
        execute_training_dataset_preparation_workflow(
            root,
            input_reference=invocation.input_reference,
            dependencies=_dependencies.simple,
        ),
        (),
        None,
    )


def _statistics_handler(
    root: dict[str, Any],
    invocation: ApplicationInvocation,
    _dependencies: ApplicationWorkflowDependencies,
) -> tuple[
    dict[str, Any],
    tuple[ApplicationArtifact, ...],
    ApplicationProvenanceBundle | None,
]:
    return (
        execute_opponent_statistics_workflow(
            root,
            input_reference=invocation.input_reference,
            dependencies=_dependencies.simple,
        ),
        (),
        None,
    )


def _list_handler(
    root: dict[str, Any],
    invocation: ApplicationInvocation,
    dependencies: ApplicationWorkflowDependencies,
) -> tuple[
    dict[str, Any],
    tuple[ApplicationArtifact, ...],
    ApplicationProvenanceBundle | None,
]:
    return (
        execute_fixed_three_player_historical_list_workflow(
            root,
            input_reference=invocation.input_reference,
            dependencies=dependencies.simple,
        ),
        (),
        None,
    )


def _comparison_handler(
    root: dict[str, Any],
    invocation: ApplicationInvocation,
    dependencies: ApplicationWorkflowDependencies,
) -> tuple[
    dict[str, Any],
    tuple[ApplicationArtifact, ...],
    ApplicationProvenanceBundle | None,
]:
    return (
        execute_fixed_three_player_historical_list_comparison_workflow(
            root,
            input_reference=invocation.input_reference,
            dependencies=dependencies.simple,
        ),
        (),
        None,
    )


_Handler = Callable[
    [dict[str, Any], ApplicationInvocation, ApplicationWorkflowDependencies],
    tuple[
        dict[str, Any],
        tuple[ApplicationArtifact, ...],
        ApplicationProvenanceBundle | None,
    ],
]

_HANDLERS: dict[WorkflowV1, _Handler] = {
    WorkflowV1.POSITION_ANALYSIS: _position_handler,
    WorkflowV1.HISTORICAL_GAME: _historical_handler,
    WorkflowV1.TRAINING_DATASET: _training_dataset_handler,
    WorkflowV1.TRAINING_DATASET_PREPARATION: _preparation_handler,
    WorkflowV1.OPPONENT_STATISTICS: _statistics_handler,
    WorkflowV1.FIXED_THREE_PLAYER_HISTORICAL_LIST: _list_handler,
    WorkflowV1.FIXED_THREE_PLAYER_HISTORICAL_LIST_COMPARISON: (
        _comparison_handler
    ),
}


def execute_application_invocation(
    invocation: ApplicationInvocation,
    *,
    dependencies: ApplicationWorkflowDependencies | None = None,
) -> ApplicationExecutionResult:
    """Validates, dispatches, and executes exactly one in-memory Root workflow."""
    validate_application_invocation(invocation)
    workflow = invocation.request.workflow
    try:
        handler = _HANDLERS[workflow]
    except KeyError as error:
        raise SkatAIInvariantError(
            f"No Application handler is registered for {workflow.value!r}."
        ) from error
    request_data = invocation.request.to_dict()["document"]
    if not isinstance(request_data, dict):
        raise SkatAIInvariantError("RequestDocumentV1 did not thaw to an object.")
    result_document, artifacts, provenance = handler(
        request_data,
        invocation,
        dependencies or ApplicationWorkflowDependencies(),
    )
    result = ResultDocumentV1(
        workflow=workflow,
        document=result_document,
        warnings=(),
    )
    if result.workflow is not workflow:
        raise SkatAIInvariantError("Application result workflow identity changed.")
    return ApplicationExecutionResult(
        orchestration_version=APPLICATION_ORCHESTRATION_VERSION,
        result=result,
        artifacts=artifacts,
        provenance=provenance,
    )
