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
from skat_ai.v1_information_provenance_enforcement import (
    enforce_v1_information_provenance_before_analysis,
    validate_v1_retained_stage_linkage,
)
from skat_ai.v1_information_provenance_serialization import (
    reconcile_v1_information_provenance_serialization,
)
from skat_ai.v1_information_provenance_sources import (
    V1InformationProvenanceSourceMetadata,
    build_v1_information_provenance_sources,
    consumed_v1_request_document,
    exact_v1_json_equal,
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
    supplied_workflow_option_names: tuple[str, ...] | None = None,
    validate_output: bool = True,
    validate_output_supplied: bool = False,
    include_provenance: bool = False,
    include_provenance_supplied: bool = False,
) -> ApplicationInvocation:
    """Builds one immutable invocation from a caller-supplied Root document."""
    if not isinstance(root_document, Mapping):
        raise SkatAIWorkflowError("Root document must be an object.")
    if "field_provenance" in root_document:
        raise SkatAIWorkflowError(
            "field_provenance is an output-only Root field."
        )
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
    selected_options = {
        WorkflowV1.POSITION_ANALYSIS: invocation_options.position_analysis,
        WorkflowV1.HISTORICAL_GAME: invocation_options.historical_game,
        WorkflowV1.TRAINING_DATASET: invocation_options.training_dataset,
    }.get(workflow)
    supplied_names_overridden = supplied_workflow_option_names is not None
    if not supplied_names_overridden:
        if options is None or selected_options is None:
            supplied_workflow_option_names = ()
        else:
            supplied_workflow_option_names = (
                selected_options._provenance_supplied_option_names
            )
    application_options_supplied = (
        bool(supplied_workflow_option_names)
        if supplied_names_overridden
        else options is not None and selected_options is not None
    )
    return ApplicationInvocation(
        request=RequestDocumentV1(workflow=workflow, document=root_document),
        input_reference=input_reference,
        options=invocation_options,
        external_documents=invocation_external_documents,
        provenance_source_metadata=V1InformationProvenanceSourceMetadata(
            application_options_supplied=application_options_supplied,
            supplied_execution_option_names=(
                ("workflow_options",) if application_options_supplied else ()
            ),
            supplied_workflow_option_names=supplied_workflow_option_names,
            validate_output=validate_output,
            validate_output_supplied=validate_output_supplied,
            include_provenance=include_provenance,
            include_provenance_supplied=include_provenance_supplied,
        ),
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
        raise SkatAIWorkflowError(
            f"{information_set_mode} cannot be combined with {existing_mode}."
        )
    needs_search = existing_search_family or information_set_search_family
    if needs_search and options.search_seed is None:
        raise SkatAIWorkflowError(
            "Historical Search operations require search_seed."
        )
    if options.search_seed is not None and not needs_search:
        raise SkatAIWorkflowError(
            "search_seed requires a Historical Search operation."
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
            "search_budget_profile requires a Historical Search operation."
        )
    has_review = (
        options.immediate_review
        or needs_search
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
    if has_external and not (
        options.immediate_review or information_set_search_family
    ):
        raise SkatAIWorkflowError(
            "Injected opponent statistics require Immediate Historical Review or "
            "Information-set Search Review or Coaching."
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
    _validate_partitions(
        options.information_set_search_partitions,
        "information_set_search_partitions",
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
    if options.operation == "information_set_search_evaluation":
        if options.information_set_search_seed is None:
            raise SkatAIWorkflowError(
                "information_set_search_evaluation requires "
                "information_set_search_seed."
            )
        if (
            options.information_set_search_budget_profile
            not in SEARCH_BUDGET_PROFILE_IDENTIFIERS
        ):
            raise SkatAIWorkflowError(
                "information_set_search_budget_profile must be a supported profile."
            )
        if (
            options.information_set_search_max_decisions is not None
            and options.information_set_search_max_decisions <= 0
        ):
            raise SkatAIWorkflowError(
                "information_set_search_max_decisions must be positive."
            )
    elif (
        options.information_set_search_seed is not None
        or options.information_set_search_partitions
        != defaults.information_set_search_partitions
        or options.information_set_search_budget_profile
        != defaults.information_set_search_budget_profile
        or options.information_set_search_max_decisions is not None
    ):
        raise SkatAIWorkflowError(
            "Information-set Search settings require the "
            "information_set_search_evaluation operation."
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
    if "field_provenance" in invocation.request.document:
        raise SkatAIWorkflowError(
            "field_provenance is an output-only Root field."
        )
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
    root: Mapping[str, object],
    invocation: ApplicationInvocation,
    dependencies: ApplicationWorkflowDependencies,
    *,
    match_decision_review: bool = False,
) -> tuple[
    dict[str, Any],
    tuple[ApplicationArtifact, ...],
    ApplicationProvenanceBundle | None,
    tuple[tuple[str, Mapping[str, object]], ...],
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

        provenance_collector = FlatRetrospectiveProvenanceCollector(
            invocation.request.to_dict()["document"]
        )
    else:
        provenance_collector = None
    external_document = invocation.external_documents.opponent_statistics_document
    result = execute_position_analysis_workflow(
        root,
        input_reference=invocation.input_reference,
        options=options,
        opponent_statistics_document=external_document,
        opponent_statistics_reference=(
            invocation.external_documents.opponent_statistics_reference
        ),
        match_decision_review=match_decision_review,
        provenance_collector=provenance_collector,
        dependencies=dependencies.position,
    )
    if not exact_v1_json_equal(
        external_document,
        invocation.external_documents.opponent_statistics_document,
    ):
        raise SkatAIInvariantError("Application consumed external input changed.")
    provenance = (
        provenance_collector.build_bundle(
            result,
            external_reference=(
                invocation.external_documents.opponent_statistics_reference
            ),
            source_document=invocation.request.to_dict()["document"],
        )
        if provenance_collector is not None
        else None
    )
    return (result, (), provenance, ())


def _historical_handler(
    root: Mapping[str, object],
    invocation: ApplicationInvocation,
    dependencies: ApplicationWorkflowDependencies,
) -> tuple[
    dict[str, Any],
    tuple[ApplicationArtifact, ...],
    ApplicationProvenanceBundle | None,
    tuple[tuple[str, Mapping[str, object]], ...],
]:
    options = invocation.options.historical_game
    if options is None:
        raise SkatAIInvariantError(
            "Historical handler received no Historical options."
        )
    from skat_ai.historical_review_provenance import (
        HistoricalReviewProvenanceCollector,
    )

    provenance_collector = HistoricalReviewProvenanceCollector(
        external_reference=(
            invocation.external_documents.opponent_statistics_reference
        )
    )
    external_document = invocation.external_documents.opponent_statistics_document
    result = execute_historical_game_workflow(
        root,
        input_reference=invocation.input_reference,
        options=options,
        opponent_statistics_document=external_document,
        opponent_statistics_reference=(
            invocation.external_documents.opponent_statistics_reference
        ),
        provenance_collector=provenance_collector,
        dependencies=dependencies.historical_game,
    )
    if not exact_v1_json_equal(
        external_document,
        invocation.external_documents.opponent_statistics_document,
    ):
        raise SkatAIInvariantError("Application consumed external input changed.")
    provenance = provenance_collector.build_bundle(
        result,
        source_document=invocation.request.to_dict()["document"],
    )
    snapshot_checkpoint = provenance_collector.snapshot_summary_checkpoint()
    checkpoints = (
        (("historical_snapshot_summary", snapshot_checkpoint),)
        if snapshot_checkpoint is not None
        else ()
    )
    return (result, (), provenance, checkpoints)


def _training_dataset_handler(
    root: Mapping[str, object],
    invocation: ApplicationInvocation,
    _dependencies: ApplicationWorkflowDependencies,
) -> tuple[
    dict[str, Any],
    tuple[ApplicationArtifact, ...],
    ApplicationProvenanceBundle | None,
    tuple[tuple[str, Mapping[str, object]], ...],
]:
    options = invocation.options.training_dataset
    if options is None:
        raise SkatAIInvariantError(
            "Training Dataset handler received no Training Dataset options."
        )
    from skat_ai.training_dataset_provenance import (
        TrainingDatasetProvenanceCollector,
    )

    provenance_collector = TrainingDatasetProvenanceCollector(options)
    result, artifacts = execute_training_dataset_workflow(
        root,
        input_reference=invocation.input_reference,
        options=options,
        provenance_collector=provenance_collector,
        dependencies=_dependencies.training_dataset,
    )
    provenance = provenance_collector.build_bundle(result, artifacts)
    return result, artifacts, provenance, ()


def _preparation_handler(
    root: Mapping[str, object],
    invocation: ApplicationInvocation,
    _dependencies: ApplicationWorkflowDependencies,
) -> tuple[
    dict[str, Any],
    tuple[ApplicationArtifact, ...],
    ApplicationProvenanceBundle | None,
    tuple[tuple[str, Mapping[str, object]], ...],
]:
    from skat_ai.dataset_preparation_provenance import (
        DatasetPreparationProvenanceCollector,
    )

    provenance_collector = DatasetPreparationProvenanceCollector()
    result = execute_training_dataset_preparation_workflow(
        root,
        input_reference=invocation.input_reference,
        provenance_collector=provenance_collector,
        dependencies=_dependencies.simple,
    )
    return result, (), provenance_collector.build_bundle(result), ()


def _statistics_handler(
    root: Mapping[str, object],
    invocation: ApplicationInvocation,
    _dependencies: ApplicationWorkflowDependencies,
) -> tuple[
    dict[str, Any],
    tuple[ApplicationArtifact, ...],
    ApplicationProvenanceBundle | None,
    tuple[tuple[str, Mapping[str, object]], ...],
]:
    from skat_ai.opponent_workflow_provenance import (
        OpponentWorkflowProvenanceCollector,
    )

    provenance_collector = OpponentWorkflowProvenanceCollector()
    result = execute_opponent_statistics_workflow(
        root,
        input_reference=invocation.input_reference,
        provenance_collector=provenance_collector,
        dependencies=_dependencies.simple,
    )
    return result, (), provenance_collector.build_bundle(result), ()


def _list_handler(
    root: Mapping[str, object],
    invocation: ApplicationInvocation,
    dependencies: ApplicationWorkflowDependencies,
) -> tuple[
    dict[str, Any],
    tuple[ApplicationArtifact, ...],
    ApplicationProvenanceBundle | None,
    tuple[tuple[str, Mapping[str, object]], ...],
]:
    from skat_ai.historical_list_provenance import HistoricalListProvenanceCollector

    provenance_collector = HistoricalListProvenanceCollector()
    result = execute_fixed_three_player_historical_list_workflow(
        root,
        input_reference=invocation.input_reference,
        provenance_collector=provenance_collector,
        dependencies=dependencies.simple,
    )
    source_document = invocation.request.to_dict()["document"]
    assert isinstance(source_document, dict)
    return (
        result,
        (),
        provenance_collector.build_bundle(
            result,
            source_document=source_document["fixed_three_player_historical_list_input"],
        ),
        (),
    )


def _comparison_handler(
    root: Mapping[str, object],
    invocation: ApplicationInvocation,
    dependencies: ApplicationWorkflowDependencies,
) -> tuple[
    dict[str, Any],
    tuple[ApplicationArtifact, ...],
    ApplicationProvenanceBundle | None,
    tuple[tuple[str, Mapping[str, object]], ...],
]:
    from skat_ai.historical_list_provenance import (
        HistoricalListComparisonProvenanceCollector,
    )

    provenance_collector = HistoricalListComparisonProvenanceCollector()
    result = execute_fixed_three_player_historical_list_comparison_workflow(
        root,
        input_reference=invocation.input_reference,
        provenance_collector=provenance_collector,
        dependencies=dependencies.simple,
    )
    source_document = invocation.request.to_dict()["document"]
    assert isinstance(source_document, dict)
    return (
        result,
        (),
        provenance_collector.build_bundle(
            result,
            source_document=source_document[
                "fixed_three_player_historical_list_comparison_input"
            ],
        ),
        (),
    )


_Handler = Callable[
    [Mapping[str, object], ApplicationInvocation, ApplicationWorkflowDependencies],
    tuple[
        dict[str, Any],
        tuple[ApplicationArtifact, ...],
        ApplicationProvenanceBundle | None,
        tuple[tuple[str, Mapping[str, object]], ...],
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


def _execute_application_invocation(
    invocation: ApplicationInvocation,
    *,
    dependencies: ApplicationWorkflowDependencies | None = None,
    match_decision_review: bool = False,
) -> ApplicationExecutionResult:
    validate_application_invocation(invocation)
    sources = build_v1_information_provenance_sources(invocation)
    enforce_v1_information_provenance_before_analysis(invocation, sources)
    workflow = invocation.request.workflow
    try:
        handler = _HANDLERS[workflow]
    except KeyError as error:
        raise SkatAIInvariantError(
            f"No Application handler is registered for {workflow.value!r}."
        ) from error
    request_data = consumed_v1_request_document(sources)
    expected_consumed_request = request_data
    effective_dependencies = dependencies or ApplicationWorkflowDependencies()
    if match_decision_review:
        if workflow is not WorkflowV1.POSITION_ANALYSIS:
            raise SkatAIInvariantError(
                "Match Decision execution requires Position Analysis."
            )
        result_document, artifacts, provenance, retained_checkpoints = _position_handler(
            request_data,
            invocation,
            effective_dependencies,
            match_decision_review=True,
        )
    else:
        result_document, artifacts, provenance, retained_checkpoints = handler(
            request_data,
            invocation,
            effective_dependencies,
        )
    if not exact_v1_json_equal(request_data, expected_consumed_request):
        raise SkatAIInvariantError("Application consumed Request input changed.")
    result = ResultDocumentV1(
        workflow=workflow,
        document=result_document,
        warnings=(),
    )
    if result.workflow is not workflow:
        raise SkatAIInvariantError("Application result workflow identity changed.")
    if provenance is None:
        raise SkatAIInvariantError(
            "V1 Root execution requires a retained provenance bundle."
        )
    linkage = validate_v1_retained_stage_linkage(
        invocation,
        sources,
        provenance,
        trusted_checkpoint_documents=retained_checkpoints,
    )
    checkpoint = reconcile_v1_information_provenance_serialization(
        invocation=invocation,
        sources=sources,
        linkage=linkage,
        result=result,
        artifacts=artifacts,
        provenance=provenance,
    )
    return ApplicationExecutionResult(
        orchestration_version=APPLICATION_ORCHESTRATION_VERSION,
        result=result,
        artifacts=artifacts,
        provenance=provenance,
        information_provenance_enforcement=checkpoint,
    )


def execute_application_invocation(
    invocation: ApplicationInvocation,
    *,
    dependencies: ApplicationWorkflowDependencies | None = None,
) -> ApplicationExecutionResult:
    """Validates, dispatches, and executes exactly one in-memory Root workflow."""
    return _execute_application_invocation(invocation, dependencies=dependencies)


def _execute_match_decision_application_invocation(
    invocation: ApplicationInvocation,
    *,
    dependencies: ApplicationWorkflowDependencies | None = None,
) -> ApplicationExecutionResult:
    """Executes one private flat Match Decision through the Position Application."""
    return _execute_application_invocation(
        invocation,
        dependencies=dependencies,
        match_decision_review=True,
    )
