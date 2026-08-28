import importlib.util
import json
import subprocess
import sys
import tomllib
from dataclasses import FrozenInstanceError, fields
from pathlib import Path

import pytest

import skatmind
import skatmind.api
import skatmind.api.v1 as api_v1
import skatmind.errors
from skatmind.api.v1 import (
    DEFAULT_INPUT_REFERENCE_V1,
    EXECUTION_ARTIFACT_NAMES_V1,
    LEGACY_MAIN_COMPATIBILITY_TARGET,
    NORMAL_RESULT_STATES_V1,
    PUBLIC_API_COMPATIBILITY_POLICY,
    PUBLIC_API_CONTRACT_VERSION,
    PUBLIC_API_NAMESPACE,
    PUBLIC_FIELD_PROVENANCE_DOCUMENT_SCOPES,
    PUBLIC_FIELD_PROVENANCE_ROOT_FIELD,
    PUBLIC_FIELD_PROVENANCE_VERSION,
    ApiVersionInfoV1,
    CompatibilityPolicyV1,
    ExecutionOptionsV1,
    RequestDocumentV1,
    ResultDocumentV1,
    WorkflowV1,
    get_api_version_info_v1,
)
from skatmind.errors import SkatMindValidationError
from skatmind.input_loader import get_input_workflow

PROJECT_ROOT = Path(__file__).resolve().parents[1]

ERROR_EXPORTS = (
    "CLI_EXIT_CODE_SUCCESS",
    "CLI_EXIT_CODE_FAILURE",
    "CLI_EXIT_CODE_USAGE",
    "SkatMindError",
    "SkatMindValidationError",
    "SkatMindWorkflowError",
    "SkatMindInformationPolicyError",
    "SkatMindSchemaError",
    "SkatMindSerializationError",
    "SkatMindResourceError",
    "SkatMindInvariantError",
    "SkatMindCliUsageError",
    "SkatMindDeprecationWarning",
)
CONTRACT_EXPORTS = (
    "PUBLIC_API_CONTRACT_VERSION",
    "PUBLIC_API_NAMESPACE",
    "PUBLIC_API_COMPATIBILITY_POLICY",
    "LEGACY_MAIN_COMPATIBILITY_TARGET",
    "NORMAL_RESULT_STATES_V1",
    "DEFAULT_INPUT_REFERENCE_V1",
    "EXECUTION_ARTIFACT_NAMES_V1",
    "WorkflowV1",
    "RequestDocumentV1",
    "ExecutionOptionsV1",
    "ResultDocumentV1",
    "ExecutionArtifactV1",
    "ExecutionResultV1",
    "CompatibilityPolicyV1",
    "ApiVersionInfoV1",
    "get_api_version_info_v1",
    "parse_request",
    "execute",
    "execute_document",
    "serialize_result",
    "PUBLIC_FIELD_PROVENANCE_VERSION",
    "PUBLIC_FIELD_PROVENANCE_ROOT_FIELD",
    "PUBLIC_FIELD_PROVENANCE_DOCUMENT_SCOPES",
    "FieldProvenanceAttachmentV1",
    "FieldProvenanceArtifactV1",
    "FieldProvenanceBundleV1",
)
WORKFLOWS = (
    "position_analysis",
    "historical_game",
    "training_dataset",
    "training_dataset_preparation",
    "opponent_statistics",
    "fixed_three_player_historical_list",
    "fixed_three_player_historical_list_comparison",
)


def test_public_namespaces_have_exact_export_surfaces() -> None:
    assert skatmind.__all__ == ("api", "errors", "__version__")
    assert skatmind.api.__all__ == ("v1",)
    assert api_v1.__all__ == (*CONTRACT_EXPORTS, *ERROR_EXPORTS, "session")
    assert skatmind.errors.__all__ == ERROR_EXPORTS

    for name in api_v1.__all__:
        assert hasattr(api_v1, name)
    for name in skatmind.errors.__all__:
        assert getattr(api_v1, name) is getattr(skatmind.errors, name)


def test_package_import_loads_only_public_contract_modules() -> None:
    command = (
        "import importlib.resources, json, sys\n"
        "importlib.resources.files = lambda *args, **kwargs: (_ for _ in ()).throw("
        "AssertionError('package import loaded schema resources'))\n"
        "import skatmind\n"
        "print(json.dumps(sorted(name for name in sys.modules "
        "if name == 'skatmind' or name.startswith('skatmind.'))))\n"
    )

    completed = subprocess.run(
        [sys.executable, "-c", command],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == [
        "skatmind",
        "skatmind._version",
        "skatmind.api",
        "skatmind.api.v1",
        "skatmind.api.v1.contracts",
        "skatmind.api.v1.execution",
        "skatmind.api.v1.provenance",
        "skatmind.api.v1.schema_validation",
        "skatmind.errors",
    ]


def test_api_constants_are_exact_and_independent_from_package_version() -> None:
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert PUBLIC_API_CONTRACT_VERSION == 1
    assert PUBLIC_API_NAMESPACE == "skatmind.api.v1"
    assert PUBLIC_API_COMPATIBILITY_POLICY == "additive_until_v1_0"
    assert LEGACY_MAIN_COMPATIBILITY_TARGET == "v1.0.0"
    assert DEFAULT_INPUT_REFERENCE_V1 == "memory://skatmind/request"
    assert EXECUTION_ARTIFACT_NAMES_V1 == ("opponent_statistics_input",)
    assert PUBLIC_FIELD_PROVENANCE_VERSION == 1
    assert PUBLIC_FIELD_PROVENANCE_ROOT_FIELD == "field_provenance"
    assert PUBLIC_FIELD_PROVENANCE_DOCUMENT_SCOPES == (
        "root_result_without_field_provenance",
        "artifact_document",
    )
    assert pyproject["project"]["version"] == "0.17.0"
    assert str(PUBLIC_API_CONTRACT_VERSION) != pyproject["project"]["version"]


def test_workflow_contract_matches_root_detection_in_canonical_order() -> None:
    assert issubclass(WorkflowV1, str)
    assert tuple(workflow.value for workflow in WorkflowV1) == WORKFLOWS
    assert tuple(str(workflow) for workflow in WorkflowV1) == WORKFLOWS

    detected = (
        get_input_workflow({}),
        get_input_workflow({"historical_game_input": {}}),
        get_input_workflow({"training_dataset_input": {}}),
        get_input_workflow({"training_dataset_preparation_input": {}}),
        get_input_workflow({"opponent_statistics_input": {}}),
        get_input_workflow({"fixed_three_player_historical_list_input": {}}),
        get_input_workflow({"fixed_three_player_historical_list_comparison_input": {}}),
    )

    assert detected == WORKFLOWS
    with pytest.raises(ValueError):
        WorkflowV1("historical_search_review")


def test_request_document_is_recursive_defensive_and_immutable() -> None:
    source = {
        "root": {
            "array": [1, 2.5, True, None, {"card": "CA"}],
        }
    }
    request = RequestDocumentV1(
        workflow=WorkflowV1.POSITION_ANALYSIS,
        document=source,
    )
    equal_request = RequestDocumentV1(
        workflow=WorkflowV1.POSITION_ANALYSIS,
        document={"root": {"array": [1, 2.5, True, None, {"card": "CA"}]}},
    )

    source["root"]["array"][0] = 99
    source["root"]["array"][4]["card"] = "D7"

    assert request == equal_request
    assert request.api_contract_version == 1
    assert request.document["root"]["array"] == (
        1,
        2.5,
        True,
        None,
        {"card": "CA"},
    )
    with pytest.raises(TypeError):
        request.document["new"] = "value"
    with pytest.raises(TypeError):
        request.document["root"]["array"][4]["card"] = "D7"
    with pytest.raises(FrozenInstanceError):
        request.workflow = WorkflowV1.HISTORICAL_GAME


def test_request_to_dict_returns_fresh_mutable_json_document() -> None:
    request = RequestDocumentV1(
        workflow=WorkflowV1.HISTORICAL_GAME,
        document={"historical_game_input": {"tricks": [["CA", "C10", "CK"]]}},
    )

    first = request.to_dict()
    second = request.to_dict()
    first["document"]["historical_game_input"]["tricks"][0][0] = "D7"

    assert first == {
        "api_contract_version": 1,
        "workflow": "historical_game",
        "document": {"historical_game_input": {"tricks": [["D7", "C10", "CK"]]}},
    }
    assert second == {
        "api_contract_version": 1,
        "workflow": "historical_game",
        "document": {"historical_game_input": {"tricks": [["CA", "C10", "CK"]]}},
    }


@pytest.mark.parametrize(
    ("document", "match"),
    [
        ([], "root must be an object"),
        ({1: "value"}, "keys must be strings"),
        ({"nested": {1: "value"}}, "keys must be strings"),
        ({"unsupported": object()}, "JSON-compatible"),
        ({"unsupported": {"set"}}, "JSON-compatible"),
        ({"number": float("nan")}, "finite"),
        ({"number": float("inf")}, "finite"),
        ({"number": float("-inf")}, "finite"),
    ],
)
def test_request_rejects_values_outside_the_json_boundary(
    document: object,
    match: str,
) -> None:
    with pytest.raises(SkatMindValidationError, match=match):
        RequestDocumentV1(
            workflow=WorkflowV1.POSITION_ANALYSIS,
            document=document,
        )


def test_request_rejects_wrong_version_and_non_enum_workflow() -> None:
    for version in (2, 1.0, True):
        with pytest.raises(SkatMindValidationError, match="api_contract_version"):
            RequestDocumentV1(
                api_contract_version=version,
                workflow=WorkflowV1.POSITION_ANALYSIS,
                document={},
            )
    with pytest.raises(SkatMindValidationError, match="WorkflowV1"):
        RequestDocumentV1(workflow="position_analysis", document={})
    with pytest.raises(TypeError):
        RequestDocumentV1(WorkflowV1.POSITION_ANALYSIS, {})


def test_result_document_defensively_copies_document_and_warnings() -> None:
    source = {"status": "complete", "values": [True, None]}
    warnings = ["Bounded result.", "Review before use."]
    result = ResultDocumentV1(
        workflow=WorkflowV1.TRAINING_DATASET,
        document=source,
        warnings=warnings,
    )

    source["status"] = "changed"
    warnings.append("Late mutation.")

    assert result.document["status"] == "complete"
    assert result.warnings == ("Bounded result.", "Review before use.")
    assert result.to_dict() == {
        "api_contract_version": 1,
        "workflow": "training_dataset",
        "document": {"status": "complete", "values": [True, None]},
        "warnings": ["Bounded result.", "Review before use."],
    }
    with pytest.raises(FrozenInstanceError):
        result.warnings = ()


@pytest.mark.parametrize("warnings", [("",), (1,), "one warning"])
def test_result_rejects_invalid_warnings(warnings: object) -> None:
    with pytest.raises(SkatMindValidationError, match="warnings"):
        ResultDocumentV1(
            workflow=WorkflowV1.POSITION_ANALYSIS,
            document={},
            warnings=warnings,
        )


def test_execution_options_are_keyword_only_frozen_and_boolean() -> None:
    assert ExecutionOptionsV1().validate_output is True
    assert ExecutionOptionsV1(validate_output=True).validate_output is True
    assert ExecutionOptionsV1(validate_output=False).validate_output is False
    assert ExecutionOptionsV1().include_provenance is False
    assert ExecutionOptionsV1(include_provenance=True).include_provenance is True
    assert [field.name for field in fields(ExecutionOptionsV1)] == [
        "validate_output",
        "include_provenance",
        "workflow_options",
        "opponent_statistics_document",
        "opponent_statistics_reference",
    ]
    assert not hasattr(ExecutionOptionsV1(), "provenance")

    with pytest.raises(SkatMindValidationError, match="boolean"):
        ExecutionOptionsV1(validate_output=1)
    with pytest.raises(SkatMindValidationError, match="boolean"):
        ExecutionOptionsV1(include_provenance=1)
    with pytest.raises(FrozenInstanceError):
        options = ExecutionOptionsV1()
        options.validate_output = False
    with pytest.raises(TypeError):
        ExecutionOptionsV1(False)


def test_compatibility_policy_has_exact_fields_and_values() -> None:
    policy = CompatibilityPolicyV1()

    assert [field.name for field in fields(policy)] == [
        "policy_id",
        "public_namespace",
        "public_name_removal_before_v1_allowed",
        "public_name_renaming_before_v1_allowed",
        "additive_public_exports_allowed",
        "direct_internal_imports_stable",
        "legacy_main_supported_through",
        "package_version_independent",
        "schema_versions_independent",
        "deprecation_warning_name",
    ]
    assert policy.to_dict() == {
        "policy_id": "additive_until_v1_0",
        "public_namespace": "skatmind.api.v1",
        "public_name_removal_before_v1_allowed": False,
        "public_name_renaming_before_v1_allowed": False,
        "additive_public_exports_allowed": True,
        "direct_internal_imports_stable": False,
        "legacy_main_supported_through": "v1.0.0",
        "package_version_independent": True,
        "schema_versions_independent": True,
        "deprecation_warning_name": "SkatMindDeprecationWarning",
    }
    with pytest.raises(FrozenInstanceError):
        policy.policy_id = "changed"
    with pytest.raises(SkatMindValidationError, match="policy_id"):
        CompatibilityPolicyV1(policy_id="breaking")


def test_api_version_info_is_exact_immutable_and_deterministic() -> None:
    first = get_api_version_info_v1()
    second = get_api_version_info_v1()

    assert isinstance(first, ApiVersionInfoV1)
    assert first == second
    assert first is not second
    assert first.api_contract_version == 1
    assert first.namespace == "skatmind.api.v1"
    assert first.supported_workflows == tuple(WorkflowV1)
    assert first.normal_result_states == NORMAL_RESULT_STATES_V1
    assert first.compatibility_policy == CompatibilityPolicyV1()
    assert not hasattr(first, "package_version")
    assert first.to_dict() == {
        "api_contract_version": 1,
        "namespace": "skatmind.api.v1",
        "supported_workflows": list(WORKFLOWS),
        "normal_result_states": list(NORMAL_RESULT_STATES_V1),
        "compatibility_policy": CompatibilityPolicyV1().to_dict(),
    }
    with pytest.raises(FrozenInstanceError):
        first.namespace = "changed"


def test_normal_result_states_are_canonical_and_remain_results() -> None:
    assert NORMAL_RESULT_STATES_V1 == (
        "complete",
        "partial",
        "timeout",
        "unavailable",
        "final",
        "lot_required",
        "not_assessable",
    )

    for state in NORMAL_RESULT_STATES_V1:
        result = ResultDocumentV1(
            workflow=WorkflowV1.POSITION_ANALYSIS,
            document={"status": state},
        )
        assert result.to_dict()["document"]["status"] == state


def test_packaging_and_cli_add_no_public_api_exports() -> None:
    forbidden = {
        "get_schema",
        "load_schema",
        "list_schemas",
        "__version__",
    }
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert forbidden.isdisjoint(api_v1.__all__)
    assert all(not hasattr(api_v1, name) for name in forbidden)
    assert skatmind.__version__ == "0.17.0"
    assert importlib.util.find_spec("skatmind.__main__") is not None
    assert pyproject["build-system"]["build-backend"] == "setuptools.build_meta"
    assert pyproject["project"]["scripts"] == {"skatmind": "skatmind.cli:main"}
    assert "gui-scripts" not in pyproject["project"]
    assert "main" not in api_v1.__all__
    assert "run_cli" not in api_v1.__all__
    assert (PROJECT_ROOT / "src" / "skatmind" / "py.typed").is_file()


def test_jsonschema_is_runtime_dependency_and_dev_tools_remain_optional() -> None:
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["dependencies"] == ["jsonschema>=4.0.0"]
    assert pyproject["project"]["optional-dependencies"]["dev"] == [
        "build>=1.2.2",
        "pytest>=9.0.0",
        "ruff>=0.14.0",
    ]
