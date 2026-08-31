from __future__ import annotations

import json

import pytest

import skatmind.app_web.execution as execution_module
from skatmind.api.v1 import (
    ExecutionArtifactV1,
    ExecutionOptionsV1,
    ExecutionResultV1,
    RequestDocumentV1,
    ResultDocumentV1,
    WorkflowV1,
)
from skatmind.app_web.execution import (
    ANALYZE_INPUT_REFERENCE,
    REVIEW_INPUT_REFERENCE,
    GuidedFrontendExecutionV1,
    execute_guided_frontend_analysis_v1,
    execute_guided_frontend_review_v1,
)
from skatmind.app_web.position_form import (
    build_guided_position_execution_v1,
    parse_position_form_v1,
)
from skatmind.errors import SkatMindWorkflowError


def _request(
    workflow: WorkflowV1,
    *,
    analysis_mode: str | None = None,
) -> RequestDocumentV1:
    document: dict[str, object] = {"marker": "request"}
    if analysis_mode is not None:
        document["analysis_mode"] = analysis_mode
    return RequestDocumentV1(workflow=workflow, document=document)


def _result(workflow: WorkflowV1) -> ExecutionResultV1:
    return ExecutionResultV1(
        result=ResultDocumentV1(
            workflow=workflow,
            document={"z": 2, "a": 1},
            warnings=("Retained warning.",),
        ),
        artifacts=(
            ExecutionArtifactV1(
                name="opponent_statistics_input",
                document={"opponent_statistics_input": {"schema_version": 1}},
            ),
        ),
    )


@pytest.mark.parametrize(
    ("runner_name", "workflow", "mode", "input_reference"),
    (
        (
            "execute_guided_frontend_analysis_v1",
            WorkflowV1.POSITION_ANALYSIS,
            None,
            ANALYZE_INPUT_REFERENCE,
        ),
        (
            "execute_guided_frontend_review_v1",
            WorkflowV1.POSITION_ANALYSIS,
            "post_game_review",
            REVIEW_INPUT_REFERENCE,
        ),
        (
            "execute_guided_frontend_review_v1",
            WorkflowV1.HISTORICAL_GAME,
            None,
            REVIEW_INPUT_REFERENCE,
        ),
    ),
)
def test_execution_calls_public_boundary_once_and_precomputes_exact_root_bytes(
    monkeypatch: pytest.MonkeyPatch,
    runner_name: str,
    workflow: WorkflowV1,
    mode: str | None,
    input_reference: str,
) -> None:
    request = _request(workflow, analysis_mode=mode)
    options = ExecutionOptionsV1(include_provenance=True)
    retained_result = _result(workflow)
    execute_calls: list[tuple[object, object, str]] = []
    serialize_calls: list[object] = []
    real_serialize = execution_module.serialize_result

    def execute(
        supplied_request: RequestDocumentV1,
        *,
        options: ExecutionOptionsV1,
        input_reference: str,
    ) -> ExecutionResultV1:
        execute_calls.append((supplied_request, options, input_reference))
        return retained_result

    def serialize_result(result: ExecutionResultV1) -> dict[str, object]:
        serialize_calls.append(result)
        return real_serialize(result)

    monkeypatch.setattr(execution_module, "execute", execute)
    monkeypatch.setattr(execution_module, "serialize_result", serialize_result)
    runner = getattr(execution_module, runner_name)
    execution = runner(request, options=options)

    assert type(execution) is GuidedFrontendExecutionV1
    assert execute_calls == [(request, options, input_reference)]
    assert serialize_calls == [retained_result]
    assert execution.request is request
    assert execution.options is options
    assert execution.result is retained_result
    assert json.loads(execution.request_json_bytes) == request.to_dict()["document"]
    assert json.loads(execution.result_json_bytes) == real_serialize(retained_result)
    assert json.loads(execution.result_json_bytes)["warnings"] == ["Retained warning."]
    assert json.loads(execution.result_json_bytes)["artifacts"] == [
        retained_result.artifacts[0].to_dict()
    ]
    assert execution.result.result.warnings == ("Retained warning.",)
    assert execution.result.artifacts == retained_result.artifacts
    assert execution.request_json_bytes.endswith(b"\n")
    assert execution.result_json_bytes.endswith(b"\n")
    assert b"\r\n" not in execution.request_json_bytes
    assert b"\r\n" not in execution.result_json_bytes

    for _index in range(3):
        assert execution.request_json_bytes
        assert execution.result_json_bytes
    assert len(execute_calls) == 1
    assert len(serialize_calls) == 1


def test_execution_never_reparses_an_imported_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _request(WorkflowV1.POSITION_ANALYSIS)
    result = _result(WorkflowV1.POSITION_ANALYSIS)
    execute_calls = 0

    def execute(*_args: object, **_kwargs: object) -> ExecutionResultV1:
        nonlocal execute_calls
        execute_calls += 1
        return result

    def parse_request(_document: object) -> RequestDocumentV1:
        raise AssertionError("Execution reparsed an immutable request.")

    monkeypatch.setattr(execution_module, "execute", execute)
    monkeypatch.setattr("skatmind.api.v1.parse_request", parse_request)

    retained = execute_guided_frontend_analysis_v1(
        request,
        options=ExecutionOptionsV1(),
    )
    assert retained.request is request
    assert execute_calls == 1


def test_execution_rejects_wrong_page_workflow_before_public_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def execute(*_args: object, **_kwargs: object) -> ExecutionResultV1:
        nonlocal calls
        calls += 1
        raise AssertionError("Invalid page workflow was executed.")

    monkeypatch.setattr(execution_module, "execute", execute)
    options = ExecutionOptionsV1()

    with pytest.raises(SkatMindWorkflowError, match="historical_game"):
        execute_guided_frontend_analysis_v1(
            _request(WorkflowV1.HISTORICAL_GAME),
            options=options,
        )
    with pytest.raises(SkatMindWorkflowError, match="post_game_review"):
        execute_guided_frontend_review_v1(
            _request(WorkflowV1.POSITION_ANALYSIS),
            options=options,
        )
    with pytest.raises(SkatMindWorkflowError, match="training_dataset"):
        execute_guided_frontend_review_v1(
            _request(WorkflowV1.TRAINING_DATASET),
            options=options,
        )
    assert calls == 0


def test_frontend_cannot_disable_public_output_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def execute(*_args: object, **_kwargs: object) -> ExecutionResultV1:
        nonlocal calls
        calls += 1
        raise AssertionError("Disabled output validation reached execution.")

    monkeypatch.setattr(execution_module, "execute", execute)
    with pytest.raises(ValueError, match="requires output validation"):
        execute_guided_frontend_analysis_v1(
            _request(WorkflowV1.POSITION_ANALYSIS),
            options=ExecutionOptionsV1(validate_output=False),
        )
    assert calls == 0


def test_result_workflow_mismatch_is_rejected_without_execution_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def execute(*_args: object, **_kwargs: object) -> ExecutionResultV1:
        nonlocal calls
        calls += 1
        return _result(WorkflowV1.HISTORICAL_GAME)

    monkeypatch.setattr(execution_module, "execute", execute)
    with pytest.raises(ValueError, match="workflow must match"):
        execute_guided_frontend_analysis_v1(
            _request(WorkflowV1.POSITION_ANALYSIS),
            options=ExecutionOptionsV1(),
        )
    assert calls == 1


def test_guided_position_executes_through_the_real_public_boundary() -> None:
    request, options = build_guided_position_execution_v1(
        parse_position_form_v1(
            {
                "game_type": ["grand"],
                "player_role": ["declarer"],
                "player_position": ["forehand"],
                "trick_leader": ["me"],
                "hand": [
                    "CJ",
                    "CA",
                    "C10",
                    "CK",
                    "CQ",
                    "C9",
                    "C8",
                    "C7",
                    "SA",
                    "S10",
                ],
                "sample_count": ["1"],
            }
        )
    )

    execution = execute_guided_frontend_analysis_v1(request, options=options)

    assert execution.result.result.workflow is WorkflowV1.POSITION_ANALYSIS
    assert execution.result.result.document["settings"]["sample_count"] == 1
    assert execution.request_json_bytes.endswith(b"\n")
    assert execution.result_json_bytes.endswith(b"\n")
