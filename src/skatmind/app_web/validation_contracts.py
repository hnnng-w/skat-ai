from __future__ import annotations

import re
from dataclasses import dataclass

from .form_parsing import FormValuesV1

FRONTEND_VALIDATION_PRESERVATION_VERSION = 1

FRONTEND_VALIDATION_STATUSES = ("invalid", "conflict")
FRONTEND_VALIDATION_ACTIVE_FAMILIES = (
    "analyze",
    "review",
    "profile",
    "sessions",
    "matches",
    "learning",
)

_MESSAGE_KEY = re.compile(r"validation\.[a-z0-9_.]+\Z")
_ARGUMENT_KEY = re.compile(r"[a-z][a-z0-9_]*\Z")


@dataclass(frozen=True, slots=True, kw_only=True)
class FrontendValidationIssueV1:
    """One locale-neutral, browser-safe validation issue."""

    field_key: str | None
    message_key: str
    interpolation_arguments: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if self.field_key is not None and (
            type(self.field_key) is not str
            or not self.field_key
            or len(self.field_key) > 96
            or not self.field_key.replace("_", "").isalnum()
        ):
            raise ValueError("field_key must be null or one bounded canonical field key.")
        if type(self.message_key) is not str or _MESSAGE_KEY.fullmatch(self.message_key) is None:
            raise ValueError("message_key must be one validation translation key.")
        arguments = tuple(self.interpolation_arguments)
        object.__setattr__(self, "interpolation_arguments", arguments)
        names = tuple(name for name, _value in arguments)
        if (
            any(
                type(name) is not str
                or _ARGUMENT_KEY.fullmatch(name) is None
                or type(value) is not str
                or len(value) > 80
                for name, value in arguments
            )
            or len(names) != len(set(names))
            or names != tuple(sorted(names))
        ):
            raise ValueError("interpolation_arguments must be unique, sorted, bounded text pairs.")

    def interpolation_values(self) -> dict[str, str]:
        return dict(self.interpolation_arguments)


@dataclass(frozen=True, slots=True, kw_only=True)
class FrontendSubmittedFormStateV1:
    """One rejected form attempt, separate from authoritative Product state."""

    contract_version: int
    form_key: str
    originating_route: str
    active_family_binding: str | None
    review_wizard_step: int | None
    form_instance: int | None
    safe_visible_values: FormValuesV1
    validation_issues: tuple[FrontendValidationIssueV1, ...]
    status: str
    feedback_generation: int

    def __post_init__(self) -> None:
        if self.contract_version != FRONTEND_VALIDATION_PRESERVATION_VERSION:
            raise ValueError("contract_version must be the strict validation version.")
        if (
            type(self.form_key) is not str
            or not self.form_key
            or len(self.form_key) > 128
            or any(part == "" for part in self.form_key.split("."))
        ):
            raise ValueError("form_key must be one bounded canonical form key.")
        if (
            type(self.originating_route) is not str
            or not self.originating_route.startswith("/")
            or "?" in self.originating_route
            or "#" in self.originating_route
        ):
            raise ValueError("originating_route must be one canonical absolute Route.")
        if self.active_family_binding is not None and (
            self.active_family_binding not in FRONTEND_VALIDATION_ACTIVE_FAMILIES
        ):
            raise ValueError("active_family_binding must be null or canonical.")
        if self.review_wizard_step is not None and (
            type(self.review_wizard_step) is not int or not 1 <= self.review_wizard_step <= 7
        ):
            raise ValueError("review_wizard_step must be null or from 1 through 7.")
        if self.form_instance is not None and (
            type(self.form_instance) is not int or not 0 <= self.form_instance <= 2048
        ):
            raise ValueError("form_instance must be null or one bounded ordinal.")
        if type(self.safe_visible_values) is not FormValuesV1:
            raise ValueError("safe_visible_values must be exact immutable form values.")
        issues = tuple(self.validation_issues)
        object.__setattr__(self, "validation_issues", issues)
        if not issues or any(type(issue) is not FrontendValidationIssueV1 for issue in issues):
            raise ValueError("validation_issues must contain exact structured issues.")
        if self.status not in FRONTEND_VALIDATION_STATUSES:
            raise ValueError("status must be invalid or conflict.")
        if type(self.feedback_generation) is not int or self.feedback_generation < 1:
            raise ValueError("feedback_generation must be a positive integer.")
