import sys
import warnings
from types import SimpleNamespace

import pytest

import main as main_module
from skat_ai.errors import (
    CLI_EXIT_CODE_FAILURE,
    CLI_EXIT_CODE_SUCCESS,
    CLI_EXIT_CODE_USAGE,
    SkatAICliUsageError,
    SkatAIDeprecationWarning,
    SkatAIError,
    SkatAIInformationPolicyError,
    SkatAIInvariantError,
    SkatAIResourceError,
    SkatAISchemaError,
    SkatAISerializationError,
    SkatAIValidationError,
    SkatAIWorkflowError,
)

ERROR_CODES = (
    (SkatAIError, "skat_ai_error"),
    (SkatAIValidationError, "validation_error"),
    (SkatAIWorkflowError, "workflow_error"),
    (SkatAIInformationPolicyError, "information_policy_error"),
    (SkatAISchemaError, "schema_error"),
    (SkatAISerializationError, "serialization_error"),
    (SkatAIResourceError, "resource_error"),
    (SkatAIInvariantError, "invariant_error"),
    (SkatAICliUsageError, "cli_usage_error"),
)


def test_public_error_hierarchy_preserves_builtin_catch_compatibility() -> None:
    assert issubclass(SkatAIError, Exception)
    assert issubclass(SkatAIValidationError, SkatAIError)
    assert issubclass(SkatAIValidationError, ValueError)
    assert issubclass(SkatAIWorkflowError, SkatAIValidationError)
    assert issubclass(SkatAIInformationPolicyError, SkatAIValidationError)
    assert issubclass(SkatAISchemaError, SkatAIValidationError)
    assert issubclass(SkatAISerializationError, SkatAIError)
    assert issubclass(SkatAISerializationError, ValueError)
    assert not issubclass(SkatAISerializationError, SkatAIValidationError)
    assert issubclass(SkatAIResourceError, SkatAIError)
    assert issubclass(SkatAIResourceError, OSError)
    assert issubclass(SkatAIInvariantError, SkatAIError)
    assert issubclass(SkatAIInvariantError, RuntimeError)
    assert issubclass(SkatAICliUsageError, SkatAIWorkflowError)
    assert issubclass(SkatAICliUsageError, ValueError)
    assert issubclass(SkatAIDeprecationWarning, DeprecationWarning)


@pytest.mark.parametrize(("error_type", "code"), ERROR_CODES)
def test_error_codes_and_serialization_are_stable(error_type: type, code: str) -> None:
    error = error_type("Human-readable message.")

    assert error_type.code == code
    assert error.message == "Human-readable message."
    assert error.code == code
    assert error.path is None
    assert str(error) == "Human-readable message."
    assert error.to_dict() == {
        "code": code,
        "message": "Human-readable message.",
        "path": None,
    }


def test_error_path_is_serialized_without_private_state() -> None:
    error = SkatAISchemaError("Field is invalid.", path="document.records[0]")

    assert error.to_dict() == {
        "code": "schema_error",
        "message": "Field is invalid.",
        "path": "document.records[0]",
    }
    assert set(error.to_dict()) == {"code", "message", "path"}


def test_error_code_cannot_be_overridden_per_instance() -> None:
    error = SkatAIValidationError("Invalid value.")

    with pytest.raises(AttributeError):
        error.code = "caller_override"
    with pytest.raises(TypeError):
        SkatAIValidationError("Invalid value.", code="caller_override")
    error.__dict__["code"] = "caller_override"
    assert error.code == "validation_error"


@pytest.mark.parametrize("message", ["", None, 1])
def test_error_requires_a_non_empty_string_message(message: object) -> None:
    with pytest.raises(ValueError, match="message"):
        SkatAIError(message)


def test_error_path_must_be_a_string_or_none() -> None:
    with pytest.raises(ValueError, match="path"):
        SkatAIError("Invalid.", path=1)


def test_public_deprecation_category_emits_no_warning_yet() -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        SkatAIDeprecationWarning("Future warning category.")

    assert caught == []


def test_legacy_cli_error_is_exact_public_alias() -> None:
    assert main_module.CliUsageError is SkatAICliUsageError
    assert str(main_module.CliUsageError("Same wording.")) == "Same wording."


def test_cli_exit_code_constants_are_exact() -> None:
    assert CLI_EXIT_CODE_SUCCESS == 0
    assert CLI_EXIT_CODE_FAILURE == 1
    assert CLI_EXIT_CODE_USAGE == 2


def test_main_uses_usage_exit_constant_and_preserves_wording(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        main_module,
        "parse_arguments",
        lambda: SimpleNamespace(input="unused.json"),
    )
    monkeypatch.setattr(
        main_module,
        "load_json_object",
        lambda _path: (_ for _ in ()).throw(SkatAICliUsageError("Invalid invocation.")),
    )

    assert main_module.main() == CLI_EXIT_CODE_USAGE
    assert capsys.readouterr().err == "CLI error: Invalid invocation.\n"


def test_main_uses_failure_exit_constant_and_preserves_wording(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        main_module,
        "parse_arguments",
        lambda: SimpleNamespace(input="unused.json"),
    )
    monkeypatch.setattr(
        main_module,
        "load_json_object",
        lambda _path: (_ for _ in ()).throw(ValueError("Invalid input.")),
    )

    assert main_module.main() == CLI_EXIT_CODE_FAILURE
    assert capsys.readouterr().err == "Error: Invalid input.\n"


def test_main_uses_success_exit_constant(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["main.py"])
    monkeypatch.setattr(main_module, "load_json_object", lambda _path: {})
    monkeypatch.setattr(main_module, "get_input_workflow", lambda _data: "opponent_statistics")
    monkeypatch.setattr(main_module, "validate_cli_arguments", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        main_module,
        "validate_opponent_statistics_cli_arguments",
        lambda _args: None,
    )
    monkeypatch.setattr(
        main_module,
        "run_json_opponent_statistics_conversion",
        lambda **kwargs: None,
    )

    assert main_module.main() == CLI_EXIT_CODE_SUCCESS
