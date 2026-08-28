CLI_EXIT_CODE_SUCCESS = 0
CLI_EXIT_CODE_FAILURE = 1
CLI_EXIT_CODE_USAGE = 2


class _ErrorCode:
    def __init__(self, value: str) -> None:
        self.value = value

    def __get__(self, instance: object, owner: type | None = None) -> str:
        return self.value

    def __set__(self, instance: object, value: object) -> None:
        raise AttributeError("error code is defined by the error class")


class SkatMindError(Exception):
    """Base class for stable public skatmind errors."""

    code = _ErrorCode("skatmind_error")

    def __init__(self, message: str, *, path: str | None = None) -> None:
        if not isinstance(message, str) or not message:
            raise ValueError("message must be a non-empty string.")
        if path is not None and not isinstance(path, str):
            raise ValueError("path must be a string or None.")

        self.message = message
        self.path = path
        super().__init__(message)

    def to_dict(self) -> dict[str, str | None]:
        """Returns the deterministic public error representation."""
        return {
            "code": self.code,
            "message": self.message,
            "path": self.path,
        }


class SkatMindValidationError(SkatMindError, ValueError):
    """Indicates invalid data at a public validation boundary."""

    code = _ErrorCode("validation_error")
    __slots__ = ()


class SkatMindWorkflowError(SkatMindValidationError):
    """Indicates an invalid workflow request or workflow combination."""

    code = _ErrorCode("workflow_error")
    __slots__ = ()


class SkatMindInformationPolicyError(SkatMindValidationError):
    """Indicates a violation of a public information policy."""

    code = _ErrorCode("information_policy_error")
    __slots__ = ()


class SkatMindSchemaError(SkatMindValidationError):
    """Indicates that a public document violates its JSON Schema contract."""

    code = _ErrorCode("schema_error")
    __slots__ = ()


class SkatMindSerializationError(SkatMindError, ValueError):
    """Indicates that a public value cannot be serialized."""

    code = _ErrorCode("serialization_error")
    __slots__ = ()


class SkatMindResourceError(SkatMindError, OSError):
    """Indicates a public file or other resource failure."""

    code = _ErrorCode("resource_error")
    __slots__ = ()


class SkatMindInvariantError(SkatMindError, RuntimeError):
    """Indicates an internal invariant failure exposed at a public boundary."""

    code = _ErrorCode("invariant_error")
    __slots__ = ()


class SkatMindCliUsageError(SkatMindWorkflowError):
    """Indicates invalid semantic use of the command-line interface."""

    code = _ErrorCode("cli_usage_error")
    __slots__ = ()


class SkatMindDeprecationWarning(DeprecationWarning):
    """Public warning category for future version-1 API deprecations."""


__all__ = (
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
