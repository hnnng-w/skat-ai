from __future__ import annotations

import re

from skatmind.errors import SkatMindWorkflowError

from .form_parsing import FormFieldErrorV1
from .form_registry import FrontendFormDefinitionV1
from .validation_contracts import FrontendValidationIssueV1


def _issue(
    field: str | None,
    key: str,
    **arguments: object,
) -> FrontendValidationIssueV1:
    return FrontendValidationIssueV1(
        field_key=field,
        message_key=key,
        interpolation_arguments=tuple(
            sorted((name, str(value)) for name, value in arguments.items())
        ),
    )


def _known_field(
    definition: FrontendFormDefinitionV1,
    candidate: str | None,
) -> str | None:
    fields = {field.field_key for field in definition.safe_fields}
    return candidate if candidate in fields else None


def _mapped_message(field: str | None, message: str) -> FrontendValidationIssueV1:
    lowered = message.lower()
    minimum = re.search(r"at least ([0-9]+)", lowered)
    maximum = re.search(r"at most ([0-9]+)", lowered)
    if minimum is not None:
        return _issue(field, "validation.message.minimum", minimum=minimum.group(1))
    if maximum is not None:
        return _issue(field, "validation.message.maximum", maximum=maximum.group(1))
    if "required" in lowered or "must be non-empty" in lowered or "must contain exactly" in lowered:
        return _issue(field, "validation.message.required")
    if "integer" in lowered or "number" in lowered:
        return _issue(field, "validation.message.integer")
    if "duplicate" in lowered or "unique" in lowered or "already" in lowered:
        return _issue(field, "validation.message.duplicate")
    if "card" in lowered:
        return _issue(field, "validation.message.card_conflict")
    if (
        "rfc 3339" in lowered
        or "date" in lowered
        or "timecode" in lowered
        or "timestamp" in lowered
    ):
        return _issue(field, "validation.message.date_time")
    if "source" in lowered:
        return _issue(field, "validation.message.source_combination")
    if (
        "choice" in lowered
        or "supported" in lowered
        or "identify one" in lowered
        or "must be one" in lowered
    ):
        return _issue(field, "validation.message.choice")
    return _issue(field, "validation.message.product_rejected")


def map_form_field_errors_v1(
    errors: tuple[FormFieldErrorV1, ...],
    definition: FrontendFormDefinitionV1,
) -> tuple[FrontendValidationIssueV1, ...]:
    return tuple(
        _mapped_message(
            _known_field(definition, None if error.field == "_form" else error.field),
            error.message,
        )
        for error in errors
    )


def map_frontend_exception_v1(
    error: Exception,
    definition: FrontendFormDefinitionV1,
    *,
    status: int,
) -> tuple[FrontendValidationIssueV1, ...]:
    fields = tuple(field.field_key for field in definition.safe_fields)
    lowered = str(error).lower()
    field = next(
        (
            candidate
            for candidate in sorted(fields, key=len, reverse=True)
            if re.search(rf"(?<![a-z0-9_]){re.escape(candidate.lower())}(?![a-z0-9_])", lowered)
        ),
        None,
    )
    if status == 409:
        key = (
            "validation.message.persistence_conflict"
            if any(word in lowered for word in ("disk", "file", "persist", "exists"))
            else "validation.message.stale"
        )
        return (_issue(field, key),)
    if isinstance(error, SkatMindWorkflowError):
        return (_issue(field, "validation.message.unsupported_workflow"),)
    return (_mapped_message(field, str(error)),)


def upload_validation_issues_v1(
    definition: FrontendFormDefinitionV1,
    *,
    status: int,
) -> tuple[FrontendValidationIssueV1, ...]:
    file_field = next(
        (field.field_key for field in definition.safe_fields if field.control_type == "file"),
        None,
    )
    key = (
        "validation.message.upload_size"
        if status == 413
        else "validation.message.upload_type"
        if status == 415
        else "validation.message.invalid_upload"
    )
    issues = [_issue(file_field, key)]
    if definition.file_reselection_behavior == "required":
        issues.append(_issue(file_field, "validation.message.file_reselection"))
    return tuple(issues)
