from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from skat_ai.api.v1.contracts import RequestDocumentV1, WorkflowV1
from skat_ai.session_validation import (
    SESSION_DIAGNOSTIC_SEVERITIES,
    SessionValidationDiagnosticV1,
)

SESSION_REQUEST_EXPORT_VERSION = 1

SESSION_REQUEST_EXPORT_POLICY = "existing_root_request_contract"
SESSION_HISTORICAL_EXPORT_POLICY = "exact_ready_retrospective_state"
SESSION_EXPORT_STATUSES = (
    "available",
    "unavailable",
)

_HISTORICAL_TARGET = "historical_game"
_SEVERITY_ORDER = {
    severity: index for index, severity in enumerate(SESSION_DIAGNOSTIC_SEVERITIES)
}


def _require_identifier(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{field_name} must be a non-empty, non-padded string.")
    return value


def _require_non_negative_integer(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer.")
    return value


def _canonicalize_diagnostics(
    value: object,
) -> tuple[SessionValidationDiagnosticV1, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        raise ValueError("diagnostics must be an ordered array.")
    diagnostics = tuple(value)
    if any(
        not isinstance(diagnostic, SessionValidationDiagnosticV1)
        for diagnostic in diagnostics
    ):
        raise ValueError(
            "diagnostics must contain only SessionValidationDiagnosticV1 values."
        )
    if len(diagnostics) != len(set(diagnostics)):
        raise ValueError("Duplicate Session export diagnostics are not allowed.")
    return tuple(
        sorted(
            diagnostics,
            key=lambda diagnostic: (
                _SEVERITY_ORDER[diagnostic.severity],
                diagnostic.path,
                diagnostic.code,
                diagnostic.message,
            ),
        )
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionRequestExportV1:
    """One immutable available or unavailable Session Request export."""

    session_request_export_version: int = SESSION_REQUEST_EXPORT_VERSION
    session_id: str
    source_revision: int
    target: str
    status: str
    request: RequestDocumentV1 | None
    diagnostics: tuple[SessionValidationDiagnosticV1, ...]

    def __post_init__(self) -> None:
        if (
            type(self.session_request_export_version) is not int
            or self.session_request_export_version != SESSION_REQUEST_EXPORT_VERSION
        ):
            raise ValueError(
                "session_request_export_version must equal "
                f"{SESSION_REQUEST_EXPORT_VERSION}."
            )
        _require_identifier(self.session_id, "session_id")
        _require_non_negative_integer(self.source_revision, "source_revision")
        if self.target != _HISTORICAL_TARGET:
            raise ValueError(f"target must equal {_HISTORICAL_TARGET!r}.")
        if self.status not in SESSION_EXPORT_STATUSES:
            raise ValueError(f"status must be one of {list(SESSION_EXPORT_STATUSES)}.")

        diagnostics = _canonicalize_diagnostics(self.diagnostics)
        if self.status == "available":
            if not isinstance(self.request, RequestDocumentV1):
                raise ValueError("An available Session export requires one RequestDocumentV1.")
            if diagnostics:
                raise ValueError("An available Session export requires no diagnostics.")
            if self.request.workflow is not WorkflowV1.HISTORICAL_GAME:
                raise ValueError("The Request workflow must match the Session export target.")
            if set(self.request.document) != {"historical_game_input"}:
                raise ValueError(
                    "A Historical Session export Request must contain exactly "
                    "historical_game_input."
                )
        else:
            if self.request is not None:
                raise ValueError("An unavailable Session export must not contain a Request.")
            if not diagnostics:
                raise ValueError(
                    "An unavailable Session export requires target-blocking diagnostics."
                )
            if any(not diagnostic.blocks_historical_export for diagnostic in diagnostics):
                raise ValueError(
                    "Unavailable Session export diagnostics must all block the target."
                )

        object.__setattr__(self, "diagnostics", diagnostics)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_request_export_version": self.session_request_export_version,
            "session_id": self.session_id,
            "source_revision": self.source_revision,
            "target": self.target,
            "status": self.status,
            "request": None if self.request is None else self.request.to_dict(),
            "diagnostics": [diagnostic.to_dict() for diagnostic in self.diagnostics],
        }
