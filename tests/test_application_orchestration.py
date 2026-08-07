import builtins
import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

import main as main_module
import skat_ai.application.execution as application_execution_module
import skat_ai.application.training_dataset_workflow as training_workflow_module
from skat_ai.api.v1 import WorkflowV1
from skat_ai.application import (
    APPLICATION_INPUT_REFERENCE_POLICY,
    APPLICATION_ORCHESTRATION_VERSION,
    ApplicationExecutionOptions,
    ApplicationExternalDocuments,
    HistoricalGameApplicationOptions,
    PositionAnalysisApplicationOptions,
    TrainingDatasetApplicationOptions,
    build_application_invocation,
    execute_application_invocation,
)
from skat_ai.application.contracts import ApplicationArtifact
from skat_ai.errors import SkatAIValidationError, SkatAIWorkflowError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = PROJECT_ROOT / "examples"


def load_example(name: str) -> dict[str, object]:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def execute_example(
    name: str,
    *,
    options: ApplicationExecutionOptions | None = None,
    external_documents: ApplicationExternalDocuments | None = None,
    input_reference: str = "caller-reference",
):
    invocation = build_application_invocation(
        load_example(name),
        input_reference=input_reference,
        options=options,
        external_documents=external_documents,
    )
    return execute_application_invocation(invocation)


def test_application_contract_constants_are_versioned_independently() -> None:
    assert APPLICATION_ORCHESTRATION_VERSION == 1
    assert APPLICATION_INPUT_REFERENCE_POLICY == "caller_supplied"


def test_invocation_defensively_freezes_documents_options_and_sequences() -> None:
    root = load_example("training_dataset_normal_play.json")
    partitions = ["validation", "test"]
    options = ApplicationExecutionOptions(
        training_dataset=TrainingDatasetApplicationOptions(
            operation="bounded_search_evaluation",
            bounded_search_seed=71,
            bounded_search_partitions=partitions,
            bounded_search_max_decisions=1,
        )
    )
    invocation = build_application_invocation(
        root,
        input_reference="opaque://request/139",
        options=options,
    )
    partitions.clear()
    root["training_dataset_input"]["records"].clear()

    assert invocation.options.training_dataset is not None
    assert invocation.options.training_dataset.bounded_search_partitions == (
        "validation",
        "test",
    )
    assert len(invocation.request.document["training_dataset_input"]["records"]) == 2
    with pytest.raises(FrozenInstanceError):
        invocation.input_reference = "changed"
    with pytest.raises(TypeError):
        invocation.request.document["extra"] = True


def test_external_documents_require_document_and_reference_together() -> None:
    with pytest.raises(SkatAIValidationError, match="supplied together"):
        ApplicationExternalDocuments(
            opponent_statistics_document=load_example("opponent_statistics.json")
        )
    with pytest.raises(SkatAIValidationError, match="supplied together"):
        ApplicationExternalDocuments(opponent_statistics_reference="statistics.json")


@pytest.mark.parametrize(
    ("example_name", "expected_workflow", "expected_result_key"),
    [
        (
            "grand_second_position.json",
            WorkflowV1.POSITION_ANALYSIS,
            "position",
        ),
        (
            "historical_grand_normal_completion.json",
            WorkflowV1.HISTORICAL_GAME,
            "historical_game_summary",
        ),
        (
            "training_dataset_normal_play.json",
            WorkflowV1.TRAINING_DATASET,
            "training_dataset_summary",
        ),
        (
            "training_dataset_preparation_unavailable.json",
            WorkflowV1.TRAINING_DATASET_PREPARATION,
            "training_dataset_preparation_summary",
        ),
        (
            "opponent_statistics.json",
            WorkflowV1.OPPONENT_STATISTICS,
            "opponent_statistics_summary",
        ),
        (
            "fixed_three_player_historical_list_mixed.json",
            WorkflowV1.FIXED_THREE_PLAYER_HISTORICAL_LIST,
            "fixed_three_player_historical_list_summary",
        ),
        (
            "fixed_three_player_historical_list_comparison.json",
            WorkflowV1.FIXED_THREE_PLAYER_HISTORICAL_LIST_COMPARISON,
            "fixed_three_player_historical_list_comparison_summary",
        ),
    ],
)
def test_all_seven_root_workflow_handlers_execute_in_memory(
    example_name: str,
    expected_workflow: WorkflowV1,
    expected_result_key: str,
) -> None:
    execution = execute_example(example_name)
    result = execution.result.to_dict()

    assert execution.orchestration_version == 1
    assert result["workflow"] == expected_workflow.value
    assert result["warnings"] == []
    assert result["document"]["input_file"] == "caller-reference"
    assert expected_result_key in result["document"]
    assert execution.artifacts == ()
    if expected_workflow is WorkflowV1.HISTORICAL_GAME:
        assert execution.provenance is None
    else:
        assert execution.provenance is not None


def test_invocation_builder_selects_root_workflow_once(monkeypatch) -> None:
    call_count = 0
    real_get_input_workflow = application_execution_module.get_input_workflow

    def counted_get_input_workflow(root_document):
        nonlocal call_count
        call_count += 1
        return real_get_input_workflow(root_document)

    monkeypatch.setattr(
        application_execution_module,
        "get_input_workflow",
        counted_get_input_workflow,
    )
    invocation = build_application_invocation(
        load_example("training_dataset_normal_play.json"),
        input_reference="one-selection",
    )

    execute_application_invocation(invocation)

    assert call_count == 1


@pytest.mark.parametrize(
    ("example_name", "options", "expected_key"),
    [
        (
            "training_dataset_normal_play.json",
            TrainingDatasetApplicationOptions(operation="summary"),
            "training_dataset_summary",
        ),
        (
            "training_dataset_partition_audit.json",
            TrainingDatasetApplicationOptions(
                operation="partition_audit",
                partition_audit_mode="report_only",
            ),
            "dataset_partition_audit_summary",
        ),
        (
            "historical_opponent_policy_evaluation_dataset.json",
            TrainingDatasetApplicationOptions(
                operation="rolling_opponent_policy_evaluation"
            ),
            "rolling_opponent_policy_evaluation_summary",
        ),
        (
            "training_dataset_normal_play.json",
            TrainingDatasetApplicationOptions(
                operation="bounded_search_evaluation",
                bounded_search_seed=71,
                bounded_search_max_decisions=1,
            ),
            "bounded_search_evaluation_summary",
        ),
        (
            "training_dataset_normal_play.json",
            TrainingDatasetApplicationOptions(
                operation="historical_opponent_statistics_aggregation"
            ),
            "historical_opponent_statistics_aggregation_summary",
        ),
    ],
)
def test_all_five_training_dataset_operations_are_isolated(
    example_name: str,
    options: TrainingDatasetApplicationOptions,
    expected_key: str,
) -> None:
    execution = execute_example(
        example_name,
        options=ApplicationExecutionOptions(training_dataset=options),
    )
    document = execution.result.to_dict()["document"]

    assert set(document) == {"input_file", expected_key}


def test_training_dataset_is_built_once_and_only_selected_operation_runs(
    monkeypatch,
) -> None:
    build_count = 0
    real_builder = training_workflow_module.build_training_dataset_from_document

    def counted_builder(root_document, **kwargs):
        nonlocal build_count
        build_count += 1
        return real_builder(root_document, **kwargs)

    def unexpected_call(*_args, **_kwargs):
        raise AssertionError("An unselected Training Dataset operation ran.")

    monkeypatch.setattr(
        training_workflow_module,
        "build_training_dataset_from_document",
        counted_builder,
    )
    for name in (
        "audit_training_dataset_partitions",
        "evaluate_rolling_opponent_policy_predictions",
        "evaluate_bounded_search_dataset",
        "aggregate_historical_opponent_statistics",
    ):
        monkeypatch.setattr(training_workflow_module, name, unexpected_call)

    execution = execute_example(
        "training_dataset_normal_play.json",
        options=ApplicationExecutionOptions(
            training_dataset=TrainingDatasetApplicationOptions(operation="summary")
        ),
    )

    assert build_count == 1
    assert "training_dataset_summary" in execution.result.to_dict()["document"]


def test_historical_aggregation_returns_requested_auxiliary_artifact() -> None:
    execution = execute_example(
        "training_dataset_normal_play.json",
        options=ApplicationExecutionOptions(
            training_dataset=TrainingDatasetApplicationOptions(
                operation="historical_opponent_statistics_aggregation",
                export_opponent_statistics=True,
            )
        ),
    )

    assert [artifact.name for artifact in execution.artifacts] == [
        "opponent_statistics_input"
    ]
    artifact = execution.artifacts[0]
    assert set(artifact.to_dict()) == {"opponent_statistics_input"}
    assert "opponent_statistics_input" not in execution.result.to_dict()["document"]
    with pytest.raises(TypeError):
        artifact.document["extra"] = True


def test_position_injects_external_statistics_with_opaque_reference() -> None:
    execution = execute_example(
        "grand_second_position.json",
        options=ApplicationExecutionOptions(
            position_analysis=PositionAnalysisApplicationOptions(
                sample_count_override=1,
                random_seed_override=42,
                use_profile_presets_override=True,
                left_opponent_player_id="opponent-123",
            )
        ),
        external_documents=ApplicationExternalDocuments(
            opponent_statistics_document=load_example("opponent_statistics.json"),
            opponent_statistics_reference="memory://opponents/current",
        ),
    )
    summary = execution.result.to_dict()["document"][
        "opponent_profile_application_summary"
    ]

    assert summary["statistics_input_file"] == "memory://opponents/current"


def test_historical_injects_statistics_with_descriptive_reference() -> None:
    execution = execute_example(
        "historical_grand_normal_completion.json",
        options=ApplicationExecutionOptions(
            historical_game=HistoricalGameApplicationOptions(
                immediate_review=True,
                immediate_sample_count=1,
                immediate_base_random_seed=42,
                use_profile_presets_override=True,
            )
        ),
        external_documents=ApplicationExternalDocuments(
            opponent_statistics_document=load_example(
                "historical_opponent_statistics.json"
            ),
            opponent_statistics_reference="caller:historical-statistics",
        ),
    )
    application = execution.result.to_dict()["document"][
        "historical_opponent_profile_application_summary"
    ]

    assert application["statistics_input_file"] == (
        "caller:historical-statistics"
    )


def test_execution_performs_no_transport_io_or_printing(monkeypatch) -> None:
    root = load_example("opponent_statistics.json")
    invocation = build_application_invocation(
        root,
        input_reference="already-loaded",
    )

    def unexpected_call(*_args, **_kwargs):
        raise AssertionError("Application execution attempted transport I/O.")

    monkeypatch.setattr(Path, "open", unexpected_call)
    monkeypatch.setattr(builtins, "print", unexpected_call)

    execution = execute_application_invocation(invocation)

    assert execution.result.workflow is WorkflowV1.OPPONENT_STATISTICS


def test_application_modules_have_no_transport_dependencies() -> None:
    application_dir = PROJECT_ROOT / "src" / "skat_ai" / "application"
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(application_dir.glob("*.py"))
    )

    assert "import argparse" not in source
    assert "import sys" not in source
    assert "skat_ai.output_writer" not in source
    assert "write_analysis_result_to_json" not in source
    assert "Path.open" not in source
    assert "print(" not in source


@pytest.mark.parametrize(
    "options",
    [
        ApplicationExecutionOptions(
            position_analysis=PositionAnalysisApplicationOptions(
                comparison_only=True
            )
        ),
        ApplicationExecutionOptions(
            position_analysis=PositionAnalysisApplicationOptions(
                compare_policies=True
            )
        ),
        ApplicationExecutionOptions(
            historical_game=HistoricalGameApplicationOptions(search_review=True)
        ),
        ApplicationExecutionOptions(
            training_dataset=TrainingDatasetApplicationOptions(
                operation="bounded_search_evaluation"
            )
        ),
    ],
)
def test_invalid_application_option_combinations_use_workflow_error(
    options: ApplicationExecutionOptions,
) -> None:
    if options.historical_game is not None:
        root = load_example("historical_grand_normal_completion.json")
    elif options.training_dataset is not None:
        root = load_example("training_dataset_normal_play.json")
    else:
        root = load_example("grand_second_position.json")
    invocation = build_application_invocation(
        root,
        input_reference="invalid-options",
        options=options,
    )

    with pytest.raises(SkatAIWorkflowError):
        execute_application_invocation(invocation)


def test_workflow_option_mismatch_uses_workflow_error() -> None:
    invocation = build_application_invocation(
        load_example("opponent_statistics.json"),
        input_reference="invalid-options",
        options=ApplicationExecutionOptions(
            position_analysis=PositionAnalysisApplicationOptions()
        ),
    )

    with pytest.raises(SkatAIWorkflowError, match="cannot be used"):
        execute_application_invocation(invocation)


def test_unavailable_preparation_is_a_normal_result() -> None:
    execution = execute_example("training_dataset_preparation_unavailable.json")
    summary = execution.result.to_dict()["document"][
        "training_dataset_preparation_summary"
    ]

    assert summary["plan"]["status"] == "unavailable"
    assert summary["training_dataset_input"] is None


def test_incomplete_live_position_is_a_normal_result() -> None:
    execution = execute_example(
        "grand_second_position.json",
        options=ApplicationExecutionOptions(
            position_analysis=PositionAnalysisApplicationOptions(
                sample_count_override=1,
                random_seed_override=42,
            )
        ),
    )
    document = execution.result.to_dict()["document"]

    assert document["game_result_summary"]["is_complete"] is False
    assert document["final_settlement_summary"]["is_complete"] is False


def test_position_application_and_legacy_wrapper_json_are_equal(tmp_path) -> None:
    input_path = EXAMPLES / "grand_second_position.json"
    output_path = tmp_path / "legacy.json"
    options = PositionAnalysisApplicationOptions(
        sample_count_override=1,
        random_seed_override=42,
        multi_step_count=1,
        card_selection_policy="highest_point",
        expected_value_sample_count=1,
        compare_policies=True,
    )
    application = execute_example(
        "grand_second_position.json",
        input_reference=str(input_path),
        options=ApplicationExecutionOptions(position_analysis=options),
    )

    main_module.run_json_position_analysis(
        file_path=str(input_path),
        sample_count_override=1,
        random_seed_override=42,
        output_path=str(output_path),
        multi_step_count=1,
        card_selection_policy="highest_point",
        expected_value_sample_count=1,
        compare_policies=True,
        quiet=True,
    )

    assert json.loads(output_path.read_text(encoding="utf-8")) == (
        application.result.to_dict()["document"]
    )


def test_injected_document_application_and_legacy_json_are_equal(tmp_path) -> None:
    input_path = EXAMPLES / "grand_second_position.json"
    statistics_path = EXAMPLES / "opponent_statistics.json"
    output_path = tmp_path / "legacy-external.json"
    options = PositionAnalysisApplicationOptions(
        sample_count_override=1,
        random_seed_override=42,
        use_profile_presets_override=True,
        left_opponent_player_id="opponent-123",
        right_opponent_player_id="opponent-789",
    )
    application = execute_example(
        "grand_second_position.json",
        input_reference=str(input_path),
        options=ApplicationExecutionOptions(position_analysis=options),
        external_documents=ApplicationExternalDocuments(
            opponent_statistics_document=load_example("opponent_statistics.json"),
            opponent_statistics_reference=str(statistics_path),
        ),
    )

    main_module.run_json_position_analysis(
        file_path=str(input_path),
        sample_count_override=1,
        random_seed_override=42,
        output_path=str(output_path),
        use_profile_presets_override=True,
        opponent_statistics_file=str(statistics_path),
        left_opponent_player_id="opponent-123",
        right_opponent_player_id="opponent-789",
        quiet=True,
    )

    assert json.loads(output_path.read_text(encoding="utf-8")) == (
        application.result.to_dict()["document"]
    )


@pytest.mark.parametrize(
    ("example_name", "wrapper_name"),
    [
        (
            "historical_grand_normal_completion.json",
            "run_json_historical_game_analysis",
        ),
        (
            "training_dataset_normal_play.json",
            "run_json_training_dataset_conversion",
        ),
        (
            "training_dataset_preparation_unavailable.json",
            "run_json_training_dataset_preparation",
        ),
        (
            "opponent_statistics.json",
            "run_json_opponent_statistics_conversion",
        ),
        (
            "fixed_three_player_historical_list_mixed.json",
            "run_json_fixed_three_player_historical_list_analysis",
        ),
        (
            "fixed_three_player_historical_list_comparison.json",
            "run_json_fixed_three_player_historical_list_comparison",
        ),
    ],
)
def test_default_application_and_legacy_wrapper_json_are_equal(
    tmp_path,
    example_name: str,
    wrapper_name: str,
) -> None:
    input_path = EXAMPLES / example_name
    output_path = tmp_path / "legacy.json"
    application = execute_example(
        example_name,
        input_reference=str(input_path),
    )

    wrapper = getattr(main_module, wrapper_name)
    wrapper(
        file_path=str(input_path),
        output_path=str(output_path),
        quiet=True,
    )

    assert json.loads(output_path.read_text(encoding="utf-8")) == (
        application.result.to_dict()["document"]
    )


def test_legacy_root_wrapper_names_remain_available() -> None:
    names = (
        "build_analysis_result",
        "run_json_position_analysis",
        "run_json_historical_game_analysis",
        "run_json_training_dataset_conversion",
        "run_json_training_dataset_preparation",
        "run_json_bounded_search_evaluation",
        "run_json_dataset_partition_audit",
        "run_json_rolling_opponent_policy_evaluation",
        "run_json_historical_opponent_statistics_aggregation",
        "run_json_fixed_three_player_historical_list_analysis",
        "run_json_fixed_three_player_historical_list_comparison",
        "run_json_opponent_statistics_conversion",
    )

    assert all(callable(getattr(main_module, name)) for name in names)
    assert main_module.CliUsageError.__name__ == "SkatAICliUsageError"


def test_legacy_training_dataset_patch_point_remains_active(
    monkeypatch,
    tmp_path,
) -> None:
    output_path = tmp_path / "summary.json"
    expected_summary = {
        "dataset_id": "patched",
        "dataset_version": "1",
        "record_count": 0,
        "sample_count": 0,
        "partition_counts": {},
    }
    monkeypatch.setattr(
        main_module,
        "build_training_dataset_summary",
        lambda _dataset: expected_summary,
    )

    main_module.run_json_training_dataset_conversion(
        file_path=str(EXAMPLES / "training_dataset_normal_play.json"),
        output_path=str(output_path),
        quiet=True,
    )

    result = json.loads(output_path.read_text(encoding="utf-8"))
    assert result["training_dataset_summary"] == expected_summary


def test_legacy_partition_audit_invalid_mode_remains_cli_usage_error() -> None:
    with pytest.raises(main_module.CliUsageError, match="supported audit mode"):
        main_module.run_json_dataset_partition_audit(
            file_path=str(EXAMPLES / "training_dataset_partition_audit.json"),
            requested_mode="invalid",
            quiet=True,
        )


def test_artifact_rejects_unknown_names() -> None:
    with pytest.raises(SkatAIValidationError, match="must be one of"):
        ApplicationArtifact(name="unknown", document={})
