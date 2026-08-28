import copy
import json
from collections import Counter
from dataclasses import replace
from pathlib import Path

import pytest

from skatmind.api.v1 import ExecutionOptionsV1, WorkflowV1, execute_document
from skatmind.api.v1.execution import _translate_workflow_options
from skatmind.application import (
    ApplicationExecutionOptions,
    ApplicationExternalDocuments,
    HistoricalGameApplicationOptions,
    TrainingDatasetApplicationOptions,
    build_application_invocation,
    execute_application_invocation,
)
from skatmind.application.execution import (
    ApplicationWorkflowDependencies,
    validate_application_invocation,
)
from skatmind.application.historical_game_workflow import (
    HistoricalGameWorkflowDependencies,
)
from skatmind.application.training_dataset_workflow import (
    TrainingDatasetWorkflowDependencies,
)
from skatmind.bounded_search_information import build_historical_search_information_view
from skatmind.compatible_world_minimax import (
    solve_compatible_world_minimax_on_selection_v1,
)
from skatmind.effective_opponent_policy import build_effective_opponent_policy_settings
from skatmind.errors import SkatMindWorkflowError
from skatmind.historical_decision_snapshot import build_historical_decision_snapshots
from skatmind.historical_game import (
    build_historical_game_record,
    build_historical_game_summary,
)
from skatmind.historical_information_set_search_review import (
    HistoricalInformationSetSearchPreActualDependenciesV1,
    HistoricalInformationSetSearchReviewSettingsV1,
    build_historical_information_set_search_decision_review_v1,
    build_historical_information_set_search_pre_actual_analysis_v1,
    build_serializable_historical_information_set_search_decision_v1,
)
from skatmind.information_set_search_contracts import (
    build_information_set_search_request_v1,
)
from skatmind.information_set_search_executor import execute_information_set_search_v1
from skatmind.information_set_search_preparation import prepare_information_set_search_v1
from skatmind.recommender import recommend_card_by_expected_value

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str):
    return json.loads((ROOT / "examples" / name).read_text("utf-8"))


def _invocation(root, workflow_options, external_documents=None):
    return build_application_invocation(
        root,
        input_reference="memory://issue-189",
        options=workflow_options,
        external_documents=external_documents,
    )


def _zero_decision_historical_root():
    data = copy.deepcopy(
        _load("training_dataset_variable_length.json")["training_dataset_input"][
            "records"
        ][0]["historical_game"]
    )
    data["tricks"] = []
    data["game_end"]["declarer_hand_cards_remaining"] = 10
    data["game_end"]["defender_consent"] = {
        "status": "not_required",
        "consenting_defender_player_ids": [],
    }
    return {"historical_game_input": data}


def test_options_and_public_api_translation_are_additive_and_operation_scoped() -> None:
    historical_defaults = HistoricalGameApplicationOptions()
    dataset_defaults = TrainingDatasetApplicationOptions()

    assert historical_defaults.information_set_search_review is False
    assert dataset_defaults.information_set_search_seed is None
    assert dataset_defaults.information_set_search_partitions == (
        "validation",
        "test",
    )
    assert dataset_defaults.information_set_search_budget_profile == "evaluation_v1"
    assert dataset_defaults.information_set_search_max_decisions is None

    historical = _translate_workflow_options(
        WorkflowV1.HISTORICAL_GAME,
        {
            "information_set_search_review": True,
            "search_seed": 17,
            "immediate_sample_count": 2,
        },
    ).historical_game
    assert historical is not None
    assert historical.information_set_search_review is True
    assert historical.search_seed == 17
    assert historical.immediate_sample_count == 2

    dataset = _translate_workflow_options(
        WorkflowV1.TRAINING_DATASET,
        {
            "operation": "information_set_search_evaluation",
            "information_set_search_seed": 19,
            "information_set_search_partitions": ["test"],
            "information_set_search_budget_profile": "evaluation_v1",
            "information_set_search_max_decisions": 3,
        },
    ).training_dataset
    assert dataset is not None
    assert dataset.information_set_search_partitions == ("test",)
    assert dataset.information_set_search_max_decisions == 3

    with pytest.raises(SkatMindWorkflowError, match="does not accept"):
        _translate_workflow_options(
            WorkflowV1.TRAINING_DATASET,
            {
                "operation": "information_set_search_evaluation",
                "information_set_search_seed": 19,
                "bounded_search_seed": 23,
            },
        )


def test_public_api_executes_both_new_options_on_zero_decision_inputs() -> None:
    historical = execute_document(
        _zero_decision_historical_root(),
        options=ExecutionOptionsV1(
            validate_output=False,
            workflow_options={
                "information_set_search_review": True,
                "search_seed": 67,
                "immediate_sample_count": 1,
            },
        ),
    )
    historical_summary = historical.result.to_dict()["document"][
        "historical_game_summary"
    ]["historical_information_set_search_review_summary"]

    dataset_root = _load("training_dataset_variable_length.json")
    zero_record = copy.deepcopy(dataset_root["training_dataset_input"]["records"][0])
    zero_record["partition"] = "test"
    zero_record["historical_game"] = _zero_decision_historical_root()[
        "historical_game_input"
    ]
    dataset_root["training_dataset_input"]["records"] = [zero_record]
    evaluation = execute_document(
        dataset_root,
        options=ExecutionOptionsV1(
            validate_output=False,
            workflow_options={
                "operation": "information_set_search_evaluation",
                "information_set_search_seed": 71,
                "information_set_search_partitions": ["test"],
                "information_set_search_max_decisions": 1,
            },
        ),
    )
    evaluation_summary = evaluation.result.to_dict()["document"][
        "information_set_search_evaluation_summary"
    ]

    assert historical_summary["decision_count"] == 0
    assert evaluation_summary["record_count"] == 1
    assert evaluation_summary["zero_decision_record_count"] == 1
    assert evaluation_summary["decision_count"] == 0


@pytest.mark.parametrize(
    ("options", "message"),
    [
        (
            HistoricalGameApplicationOptions(
                information_set_search_review=True,
            ),
            "require search_seed",
        ),
        (
            HistoricalGameApplicationOptions(
                information_set_search_review=True,
                search_review=True,
                search_seed=1,
            ),
            "cannot be combined with Search Review",
        ),
        (
            HistoricalGameApplicationOptions(
                information_set_search_review=True,
                replay_coaching=True,
                search_seed=1,
            ),
            "cannot be combined with Replay Coaching",
        ),
    ],
)
def test_historical_information_set_search_option_conflicts_are_strict(
    options,
    message,
) -> None:
    invocation = _invocation(
        _load("historical_grand_normal_completion.json"),
        ApplicationExecutionOptions(historical_game=options),
    )

    with pytest.raises(SkatMindWorkflowError, match=message):
        validate_application_invocation(invocation)


@pytest.mark.parametrize(
    ("options", "message"),
    [
        (
            TrainingDatasetApplicationOptions(
                operation="information_set_search_evaluation",
            ),
            "requires information_set_search_seed",
        ),
        (
            TrainingDatasetApplicationOptions(
                operation="information_set_search_evaluation",
                information_set_search_seed=1,
                bounded_search_seed=2,
            ),
            "Bounded Search settings require",
        ),
        (
            TrainingDatasetApplicationOptions(information_set_search_seed=1),
            "Information-set Search settings require",
        ),
        (
            TrainingDatasetApplicationOptions(
                operation="information_set_search_evaluation",
                information_set_search_seed=1,
                information_set_search_max_decisions=0,
            ),
            "max_decisions must be positive",
        ),
    ],
)
def test_dataset_information_set_search_option_conflicts_are_strict(
    options,
    message,
) -> None:
    invocation = _invocation(
        _load("training_dataset_normal_play.json"),
        ApplicationExecutionOptions(training_dataset=options),
    )

    with pytest.raises(SkatMindWorkflowError, match=message):
        validate_application_invocation(invocation)


def test_historical_application_attaches_one_review_and_resolves_profile_precedence() -> None:
    calls = []

    def build_review(**kwargs):
        calls.append(kwargs)
        policies = kwargs["effective_policy_settings_by_decision"]
        assert len(policies) == kwargs["snapshot_summary"].snapshot_count
        assert all(item.left_response_policy == "lowest_point" for item in policies.values())
        assert all(item.right_response_policy == "highest_point" for item in policies.values())
        assert all(item.left_response_source == "cli_explicit" for item in policies.values())
        assert all(item.right_response_source == "cli_explicit" for item in policies.values())
        return {"review": "information-set"}

    invocation = _invocation(
        _load("historical_grand_normal_completion.json"),
        ApplicationExecutionOptions(
            historical_game=HistoricalGameApplicationOptions(
                information_set_search_review=True,
                search_seed=31,
                immediate_sample_count=1,
                immediate_base_random_seed=41,
                opponent_response_policy_override="highest_point",
                left_opponent_response_policy_override="lowest_point",
                use_profile_presets_override=True,
            )
        ),
        ApplicationExternalDocuments(
            opponent_statistics_document=_load("historical_opponent_statistics.json"),
            opponent_statistics_reference="memory://historical-profiles",
        ),
    )
    dependencies = ApplicationWorkflowDependencies(
        historical_game=HistoricalGameWorkflowDependencies(
            build_information_set_search_review=build_review,
        )
    )

    execution = execute_application_invocation(invocation, dependencies=dependencies)
    document = execution.result.to_dict()["document"]
    summary = document["historical_game_summary"]

    assert len(calls) == 1
    assert calls[0]["settings"] == HistoricalInformationSetSearchReviewSettingsV1(
        base_search_seed=31,
        immediate_sample_count=1,
        immediate_base_random_seed=41,
    )
    assert summary["historical_information_set_search_review_summary"] == {
        "review": "information-set"
    }
    assert "historical_search_review_summary" not in summary
    assert "historical_replay_coaching_summary" not in summary
    assert document["historical_opponent_profile_application_summary"][
        "statistics_input_file"
    ] == "memory://historical-profiles"
    assert execution.provenance is not None


def test_production_pre_actual_builder_runs_each_available_stage_once_and_is_safe() -> None:
    root = _load("historical_grand_normal_completion.json")
    record = build_historical_game_record(root["historical_game_input"])
    snapshots = build_historical_decision_snapshots(build_historical_game_summary(record))
    snapshot = snapshots.snapshots[-1]
    counts = Counter()

    def counted(name, callback):
        def run(*args, **kwargs):
            counts[name] += 1
            if name == "request":
                assert set(kwargs) == {
                    "information_view",
                    "requested_budget",
                    "world_selection_seed",
                    "policy_settings",
                }
            return callback(*args, **kwargs)

        return run

    dependencies = HistoricalInformationSetSearchPreActualDependenciesV1(
        build_information_view=counted(
            "information_view",
            build_historical_search_information_view,
        ),
        build_request=counted("request", build_information_set_search_request_v1),
        prepare_search=counted("preparation", prepare_information_set_search_v1),
        execute_search=counted("executor", execute_information_set_search_v1),
        solve_same_selection_pimc=counted(
            "pimc",
            solve_compatible_world_minimax_on_selection_v1,
        ),
        recommend_immediate=counted("immediate", recommend_card_by_expected_value),
    )

    def build_pre_actual(decision_input):
        assert not hasattr(decision_input, "actual_card")
        assert not hasattr(decision_input, "historical_record")
        return build_historical_information_set_search_pre_actual_analysis_v1(
            decision_input,
            dependencies=dependencies,
        )

    decision = build_historical_information_set_search_decision_review_v1(
        snapshot,
        record,
        HistoricalInformationSetSearchReviewSettingsV1(
            base_search_seed=43,
            immediate_sample_count=1,
            immediate_base_random_seed=47,
        ),
        pre_actual_analysis_builder=build_pre_actual,
    )
    serialized = build_serializable_historical_information_set_search_decision_v1(
        decision
    )
    public_search = serialized["information_set_search_result"]

    assert counts == {
        "information_view": 1,
        "request": 1,
        "preparation": 1,
        "executor": 1,
        "pimc": 1,
        "immediate": 1,
    }
    assert public_search["schema_version"] == 1
    assert "controlled_policy" not in public_search
    assert "world_states" not in public_search
    assert "root_information_set" not in public_search
    assert "request" not in public_search


def test_random_fixed_policy_still_runs_independent_immediate_without_search_or_pimc() -> None:
    root = _load("historical_grand_normal_completion.json")
    record = build_historical_game_record(root["historical_game_input"])
    snapshot = build_historical_decision_snapshots(
        build_historical_game_summary(record)
    ).snapshots[-1]
    captured = []

    def capture_input(decision_input):
        captured.append(decision_input)
        return build_historical_information_set_search_pre_actual_analysis_v1(
            replace(
                decision_input,
                effective_opponent_policy_settings=(
                    build_effective_opponent_policy_settings(
                        data={},
                        opponent_policy_preset_override="random",
                    )
                ),
            ),
            dependencies=HistoricalInformationSetSearchPreActualDependenciesV1(
                build_information_view=build_historical_search_information_view,
                build_request=lambda **_kwargs: pytest.fail("Request must not run."),
                prepare_search=lambda _request: pytest.fail("Preparation must not run."),
                execute_search=lambda _preparation: pytest.fail("Executor must not run."),
                solve_same_selection_pimc=lambda **_kwargs: pytest.fail(
                    "PIMC must not run."
                ),
                recommend_immediate=recommend_card_by_expected_value,
            ),
        )

    decision = build_historical_information_set_search_decision_review_v1(
        snapshot,
        record,
        HistoricalInformationSetSearchReviewSettingsV1(
            base_search_seed=53,
            immediate_sample_count=1,
            immediate_base_random_seed=59,
        ),
        pre_actual_analysis_builder=capture_input,
    )

    assert len(captured) == 1
    assert decision.information_set_result is None
    assert decision.information_set_public_result is not None
    assert decision.information_set_public_result["status"] == "unavailable"
    assert (
        decision.information_set_public_result["stop_reason"]
        == "nondeterministic_fixed_policy"
    )
    assert decision.comparison.information_set_status == "unavailable"
    assert decision.pimc_result is None
    assert decision.immediate_recommended_card in snapshot.visible_state.legal_cards


def test_dataset_application_returns_only_information_set_evaluation_summary() -> None:
    calls = []

    def evaluate(dataset, **kwargs):
        calls.append((dataset, kwargs))
        return {"evaluation": "information-set"}

    invocation = _invocation(
        _load("training_dataset_normal_play.json"),
        ApplicationExecutionOptions(
            training_dataset=TrainingDatasetApplicationOptions(
                operation="information_set_search_evaluation",
                information_set_search_seed=61,
                information_set_search_partitions=("validation",),
                information_set_search_max_decisions=2,
            )
        ),
    )
    dependencies = ApplicationWorkflowDependencies(
        training_dataset=TrainingDatasetWorkflowDependencies(
            evaluate_information_set_search=evaluate,
        )
    )

    execution = execute_application_invocation(invocation, dependencies=dependencies)
    document = execution.result.to_dict()["document"]

    assert set(document) == {
        "input_file",
        "information_set_search_evaluation_summary",
    }
    assert document["information_set_search_evaluation_summary"] == {
        "evaluation": "information-set"
    }
    assert len(calls) == 1
    dataset, kwargs = calls[0]
    assert dataset.target == "actual_card_played"
    assert kwargs == {
        "base_search_seed": 61,
        "partitions": ("validation",),
        "search_budget_profile": "evaluation_v1",
        "max_decisions": 2,
    }
    assert execution.provenance is not None


def test_omitted_new_options_do_not_run_new_operations() -> None:
    def unexpected(*_args, **_kwargs):
        raise AssertionError("An omitted Information-set operation ran.")

    historical = execute_application_invocation(
        _invocation(
            _load("historical_grand_normal_completion.json"),
            ApplicationExecutionOptions(
                historical_game=HistoricalGameApplicationOptions()
            ),
        ),
        dependencies=ApplicationWorkflowDependencies(
            historical_game=HistoricalGameWorkflowDependencies(
                build_information_set_search_review=unexpected,
            )
        ),
    )
    dataset = execute_application_invocation(
        _invocation(
            _load("training_dataset_normal_play.json"),
            ApplicationExecutionOptions(
                training_dataset=TrainingDatasetApplicationOptions()
            ),
        ),
        dependencies=ApplicationWorkflowDependencies(
            training_dataset=TrainingDatasetWorkflowDependencies(
                evaluate_information_set_search=unexpected,
            )
        ),
    )

    historical_summary = historical.result.to_dict()["document"][
        "historical_game_summary"
    ]
    assert "historical_information_set_search_review_summary" not in historical_summary
    assert "training_dataset_summary" in dataset.result.to_dict()["document"]
    assert historical.provenance is not None
    assert dataset.provenance is not None
