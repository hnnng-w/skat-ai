from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from skat_ai.api.v1.contracts import PUBLIC_API_CONTRACT_VERSION
from skat_ai.api.v1.session.contracts import PUBLIC_SESSION_API_VERSION
from skat_ai.errors import SkatAIValidationError
from skat_ai.session_persistence_contracts import (
    SESSION_PERSISTENCE_VERSION,
    SessionPersistenceWriteResultV1,
    SessionResumeResultV1,
)

PUBLIC_SESSION_FILE_API_VERSION = 1
PUBLIC_SESSION_FILE_API_NAMESPACE = "skat_ai.api.v1.session.files"
PUBLIC_SESSION_FILE_API_COMPATIBILITY_POLICY = "additive_until_v1_0"

SESSION_FILE_API_OPERATIONS = (
    "save",
    "load",
)


def _validation_error(message: str, *, path: str) -> SkatAIValidationError:
    return SkatAIValidationError(message, path=path)


def _validate_version(value: object, expected: int, *, path: str) -> None:
    if type(value) is not int or value != expected:
        raise _validation_error(f"{path} must equal {expected}.", path=path)


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionFileApiVersionInfoV1:
    """Stable version information for the public Session file API."""

    api_contract_version: int = PUBLIC_API_CONTRACT_VERSION
    public_session_api_version: int = PUBLIC_SESSION_API_VERSION
    public_session_file_api_version: int = PUBLIC_SESSION_FILE_API_VERSION
    namespace: str = PUBLIC_SESSION_FILE_API_NAMESPACE
    compatibility_policy: str = PUBLIC_SESSION_FILE_API_COMPATIBILITY_POLICY
    operations: tuple[str, ...] = SESSION_FILE_API_OPERATIONS
    persistence_version: int = SESSION_PERSISTENCE_VERSION

    def __post_init__(self) -> None:
        for path, value, expected in (
            ("api_contract_version", self.api_contract_version, PUBLIC_API_CONTRACT_VERSION),
            (
                "public_session_api_version",
                self.public_session_api_version,
                PUBLIC_SESSION_API_VERSION,
            ),
            (
                "public_session_file_api_version",
                self.public_session_file_api_version,
                PUBLIC_SESSION_FILE_API_VERSION,
            ),
            ("persistence_version", self.persistence_version, SESSION_PERSISTENCE_VERSION),
        ):
            _validate_version(value, expected, path=path)
        if self.namespace != PUBLIC_SESSION_FILE_API_NAMESPACE:
            raise _validation_error(
                f"namespace must equal {PUBLIC_SESSION_FILE_API_NAMESPACE!r}.",
                path="namespace",
            )
        if self.compatibility_policy != PUBLIC_SESSION_FILE_API_COMPATIBILITY_POLICY:
            raise _validation_error(
                "compatibility_policy must equal the public Session file API policy.",
                path="compatibility_policy",
            )
        if self.operations != SESSION_FILE_API_OPERATIONS:
            raise _validation_error(
                "operations must equal the canonical Session file API operation order.",
                path="operations",
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "api_contract_version": self.api_contract_version,
            "public_session_api_version": self.public_session_api_version,
            "public_session_file_api_version": self.public_session_file_api_version,
            "namespace": self.namespace,
            "compatibility_policy": self.compatibility_policy,
            "operations": list(self.operations),
            "persistence_version": self.persistence_version,
        }


def get_session_file_api_version_info_v1() -> SessionFileApiVersionInfoV1:
    """Returns deterministic public Session file API compatibility information."""
    return SessionFileApiVersionInfoV1()


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionFileApiOptionsV1:
    """Non-transport controls for one public Session file API operation."""

    validate_output: bool = True

    def __post_init__(self) -> None:
        if type(self.validate_output) is not bool:
            raise _validation_error(
                "validate_output must be a boolean.",
                path="validate_output",
            )

    def to_dict(self) -> dict[str, bool]:
        return {"validate_output": self.validate_output}


_OPERATION_VALUE_TYPES = {
    "save": SessionPersistenceWriteResultV1,
    "load": SessionResumeResultV1,
}


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionFileApiResultV1:
    """One immutable result from the stable Session file API."""

    api_contract_version: int = PUBLIC_API_CONTRACT_VERSION
    public_session_api_version: int = PUBLIC_SESSION_API_VERSION
    public_session_file_api_version: int = PUBLIC_SESSION_FILE_API_VERSION
    operation: str
    value: object

    def __post_init__(self) -> None:
        for path, value, expected in (
            ("api_contract_version", self.api_contract_version, PUBLIC_API_CONTRACT_VERSION),
            (
                "public_session_api_version",
                self.public_session_api_version,
                PUBLIC_SESSION_API_VERSION,
            ),
            (
                "public_session_file_api_version",
                self.public_session_file_api_version,
                PUBLIC_SESSION_FILE_API_VERSION,
            ),
        ):
            _validate_version(value, expected, path=path)
        if self.operation not in SESSION_FILE_API_OPERATIONS:
            raise _validation_error(
                "operation must be one canonical Session file API operation.",
                path="operation",
            )
        expected_type = _OPERATION_VALUE_TYPES[self.operation]
        if type(self.value) is not expected_type:
            raise _validation_error(
                f"value must be a {expected_type.__name__} for {self.operation!r}.",
                path="value",
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "api_contract_version": self.api_contract_version,
            "public_session_api_version": self.public_session_api_version,
            "public_session_file_api_version": self.public_session_file_api_version,
            "operation": self.operation,
            "value": self.value.to_dict(),
        }
