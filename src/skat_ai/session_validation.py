from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from skat_ai.field_provenance import parse_json_pointer
from skat_ai.session_commands import (
    SessionCommandV1,
    is_session_command_v1,
    serialize_session_command_v1,
)
from skat_ai.session_contracts import (
    SESSION_CONTRACT_VERSION,
    SESSION_PHASES,
    SessionStateV1,
)

SESSION_TRANSITION_STATUSES = ("applied", "rejected", "revision_conflict")
SESSION_EXPORT_TARGETS = ("position_analysis", "historical_game")
SESSION_EXPORT_READINESS_STATUSES = ("available", "unavailable")
SESSION_DIAGNOSTIC_SEVERITIES = ("error", "warning", "info")
SESSION_DIAGNOSTIC_CODES = (
    "missing_required_value",
    "invalid_value",
    "phase_violation",
    "player_reference_violation",
    "card_identity_violation",
    "card_ownership_violation",
    "turn_order_violation",
    "declaration_violation",
    "information_policy_violation",
    "event_sequence_violation",
    "game_end_violation",
    "export_unavailable",
    "revision_conflict",
)

_SEVERITY_ORDER = {
    severity: index for index, severity in enumerate(SESSION_DIAGNOSTIC_SEVERITIES)
}
_DIAGNOSTIC_CODE_ORDER = {
    code: index for index, code in enumerate(SESSION_DIAGNOSTIC_CODES)
}


def _require_non_negative_integer(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer.")
    return value


def _require_boolean(value: object, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be a boolean.")
    return value


def _require_ordered_values(value: object, field_name: str) -> tuple[object, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        raise ValueError(f"{field_name} must be an ordered array.")
    return tuple(value)


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionValidationDiagnosticV1:
    """One stable machine-readable Session validation diagnostic."""

    code: str
    path: str
    message: str
    severity: str
    blocks_command: bool
    blocks_position_export: bool
    blocks_historical_export: bool

    def __post_init__(self) -> None:
        if self.code not in SESSION_DIAGNOSTIC_CODES:
            raise ValueError(f"code must be one of {list(SESSION_DIAGNOSTIC_CODES)}.")
        if not isinstance(self.path, str):
            raise ValueError("path must be a canonical RFC 6901 JSON Pointer.")
        parse_json_pointer(self.path)
        if not isinstance(self.message, str) or not self.message:
            raise ValueError("message must be a non-empty string.")
        if self.severity not in SESSION_DIAGNOSTIC_SEVERITIES:
            raise ValueError(
                f"severity must be one of {list(SESSION_DIAGNOSTIC_SEVERITIES)}."
            )
        _require_boolean(self.blocks_command, "blocks_command")
        _require_boolean(self.blocks_position_export, "blocks_position_export")
        _require_boolean(self.blocks_historical_export, "blocks_historical_export")
        if self.blocks_command and self.severity != "error":
            raise ValueError("Only error diagnostics may block Command application.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "path": self.path,
            "message": self.message,
            "severity": self.severity,
            "blocks_command": self.blocks_command,
            "blocks_position_export": self.blocks_position_export,
            "blocks_historical_export": self.blocks_historical_export,
        }


def _diagnostic_sort_key(
    diagnostic: SessionValidationDiagnosticV1,
) -> tuple[int, str, str, str]:
    return (
        _SEVERITY_ORDER[diagnostic.severity],
        diagnostic.path,
        diagnostic.code,
        diagnostic.message,
    )


def _canonicalize_diagnostics(
    value: object,
) -> tuple[SessionValidationDiagnosticV1, ...]:
    diagnostics = _require_ordered_values(value, "diagnostics")
    if any(
        not isinstance(diagnostic, SessionValidationDiagnosticV1)
        for diagnostic in diagnostics
    ):
        raise ValueError(
            "diagnostics must contain only SessionValidationDiagnosticV1 values."
        )
    if len(diagnostics) != len(set(diagnostics)):
        raise ValueError("Duplicate Session validation diagnostics are not allowed.")
    return tuple(sorted(diagnostics, key=_diagnostic_sort_key))


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionExportReadinessV1:
    """Normal available or unavailable status for one Engine export target."""

    target: str
    status: str
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.target not in SESSION_EXPORT_TARGETS:
            raise ValueError(f"target must be one of {list(SESSION_EXPORT_TARGETS)}.")
        if self.status not in SESSION_EXPORT_READINESS_STATUSES:
            raise ValueError(
                "status must be one of "
                f"{list(SESSION_EXPORT_READINESS_STATUSES)}."
            )
        raw_reasons = _require_ordered_values(self.reason_codes, "reason_codes")
        if any(reason not in SESSION_DIAGNOSTIC_CODES for reason in raw_reasons):
            raise ValueError(
                "reason_codes must contain only version-1 Session diagnostic codes."
            )
        if len(raw_reasons) != len(set(raw_reasons)):
            raise ValueError("reason_codes must not contain duplicates.")
        reasons = tuple(sorted(raw_reasons, key=_DIAGNOSTIC_CODE_ORDER.__getitem__))
        if self.status == "available" and reasons:
            raise ValueError("available export readiness requires no reason_codes.")
        if self.status == "unavailable" and not reasons:
            raise ValueError("unavailable export readiness requires reason_codes.")
        object.__setattr__(self, "reason_codes", reasons)

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "status": self.status,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionValidationResultV1:
    """Validated structural, completeness, and export-readiness Session status."""

    session_contract_version: int = SESSION_CONTRACT_VERSION
    revision: int
    phase: str
    structurally_valid: bool
    valid_incomplete: bool
    game_complete: bool
    position_export: SessionExportReadinessV1
    historical_export: SessionExportReadinessV1
    diagnostics: tuple[SessionValidationDiagnosticV1, ...]

    def __post_init__(self) -> None:
        if (
            type(self.session_contract_version) is not int
            or self.session_contract_version != SESSION_CONTRACT_VERSION
        ):
            raise ValueError(
                f"session_contract_version must equal {SESSION_CONTRACT_VERSION}."
            )
        _require_non_negative_integer(self.revision, "revision")
        if self.phase not in SESSION_PHASES:
            raise ValueError(f"phase must be one of {list(SESSION_PHASES)}.")
        _require_boolean(self.structurally_valid, "structurally_valid")
        _require_boolean(self.valid_incomplete, "valid_incomplete")
        _require_boolean(self.game_complete, "game_complete")
        if self.valid_incomplete != (self.structurally_valid and not self.game_complete):
            raise ValueError(
                "valid_incomplete must equal structurally_valid and not game_complete."
            )
        if self.game_complete != (self.phase == "ended"):
            raise ValueError("game_complete must be true exactly when phase is 'ended'.")
        if not isinstance(self.position_export, SessionExportReadinessV1):
            raise ValueError("position_export must be a SessionExportReadinessV1.")
        if self.position_export.target != "position_analysis":
            raise ValueError("position_export must target position_analysis.")
        if not isinstance(self.historical_export, SessionExportReadinessV1):
            raise ValueError("historical_export must be a SessionExportReadinessV1.")
        if self.historical_export.target != "historical_game":
            raise ValueError("historical_export must target historical_game.")
        if not self.structurally_valid and (
            self.position_export.status != "unavailable"
            or self.historical_export.status != "unavailable"
        ):
            raise ValueError("A structurally invalid Session has both exports unavailable.")
        if not self.game_complete and self.historical_export.status == "available":
            raise ValueError("Historical export is available only for a complete game.")

        diagnostics = _canonicalize_diagnostics(self.diagnostics)
        position_blockers = {
            diagnostic.code
            for diagnostic in diagnostics
            if diagnostic.blocks_position_export
        }
        historical_blockers = {
            diagnostic.code
            for diagnostic in diagnostics
            if diagnostic.blocks_historical_export
        }
        if position_blockers != set(self.position_export.reason_codes):
            raise ValueError(
                "position_export reason_codes must equal its blocking diagnostic codes."
            )
        if historical_blockers != set(self.historical_export.reason_codes):
            raise ValueError(
                "historical_export reason_codes must equal its blocking diagnostic codes."
            )
        object.__setattr__(self, "diagnostics", diagnostics)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_contract_version": self.session_contract_version,
            "revision": self.revision,
            "phase": self.phase,
            "structurally_valid": self.structurally_valid,
            "valid_incomplete": self.valid_incomplete,
            "game_complete": self.game_complete,
            "position_export": self.position_export.to_dict(),
            "historical_export": self.historical_export.to_dict(),
            "diagnostics": [diagnostic.to_dict() for diagnostic in self.diagnostics],
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionTransitionResultV1:
    """Immutable applied, rejected, or revision-conflict Transition outcome."""

    session_contract_version: int = SESSION_CONTRACT_VERSION
    status: str
    expected_revision: int
    previous_revision: int
    current_revision: int
    command: SessionCommandV1
    state: SessionStateV1
    diagnostics: tuple[SessionValidationDiagnosticV1, ...]

    def __post_init__(self) -> None:
        if (
            type(self.session_contract_version) is not int
            or self.session_contract_version != SESSION_CONTRACT_VERSION
        ):
            raise ValueError(
                f"session_contract_version must equal {SESSION_CONTRACT_VERSION}."
            )
        if self.status not in SESSION_TRANSITION_STATUSES:
            raise ValueError(
                f"status must be one of {list(SESSION_TRANSITION_STATUSES)}."
            )
        _require_non_negative_integer(self.expected_revision, "expected_revision")
        _require_non_negative_integer(self.previous_revision, "previous_revision")
        _require_non_negative_integer(self.current_revision, "current_revision")
        if not is_session_command_v1(self.command):
            raise ValueError("command must be one SessionCommandV1 member.")
        if self.command.expected_revision != self.expected_revision:
            raise ValueError(
                "expected_revision must equal command.expected_revision."
            )
        if not isinstance(self.state, SessionStateV1):
            raise ValueError("state must be a SessionStateV1.")
        diagnostics = _canonicalize_diagnostics(self.diagnostics)
        blocking_diagnostics = tuple(
            diagnostic for diagnostic in diagnostics if diagnostic.blocks_command
        )

        if self.status == "applied":
            if self.expected_revision != self.previous_revision:
                raise ValueError("An applied Transition requires the expected revision.")
            if self.current_revision != self.previous_revision + 1:
                raise ValueError("An applied Transition increments the revision by one.")
            if self.state.revision != self.current_revision:
                raise ValueError("Applied State revision must equal current_revision.")
            if not self.state.command_log:
                raise ValueError("An applied Transition requires a final Command Log record.")
            final_record = self.state.command_log[-1]
            if (
                final_record.revision != self.current_revision
                or final_record.command != self.command
            ):
                raise ValueError(
                    "The applied Command must be the final accepted Command Log record."
                )
            if blocking_diagnostics:
                raise ValueError("An applied Transition cannot have blocking diagnostics.")
        elif self.status == "rejected":
            if self.expected_revision != self.previous_revision:
                raise ValueError("A rejected Transition requires the expected revision.")
            if self.current_revision != self.previous_revision:
                raise ValueError("A rejected Transition does not change the revision.")
            if self.state.revision != self.previous_revision:
                raise ValueError("A rejected Transition returns the unchanged State revision.")
            if not blocking_diagnostics:
                raise ValueError("A rejected Transition requires a blocking diagnostic.")
        else:
            if self.expected_revision == self.previous_revision:
                raise ValueError("A revision conflict requires a stale or future revision.")
            if self.current_revision != self.previous_revision:
                raise ValueError("A revision conflict does not change the revision.")
            if self.state.revision != self.previous_revision:
                raise ValueError(
                    "A revision conflict returns the unchanged State revision."
                )
            conflict_diagnostics = tuple(
                diagnostic
                for diagnostic in diagnostics
                if diagnostic.code == "revision_conflict"
            )
            if len(conflict_diagnostics) != 1 or not conflict_diagnostics[0].blocks_command:
                raise ValueError(
                    "A revision conflict requires exactly one blocking "
                    "revision_conflict diagnostic."
                )

        object.__setattr__(self, "diagnostics", diagnostics)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_contract_version": self.session_contract_version,
            "status": self.status,
            "expected_revision": self.expected_revision,
            "previous_revision": self.previous_revision,
            "current_revision": self.current_revision,
            "command": serialize_session_command_v1(self.command),
            "state": self.state.to_dict(),
            "diagnostics": [diagnostic.to_dict() for diagnostic in self.diagnostics],
        }
