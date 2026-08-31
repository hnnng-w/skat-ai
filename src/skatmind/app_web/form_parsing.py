from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FormValueV1:
    """One immutable, safely retained URL-encoded form value."""

    field: str
    values: tuple[str, ...]

    def __post_init__(self) -> None:
        if type(self.field) is not str or not self.field:
            raise ValueError("Form value field must be non-empty text.")
        values = tuple(self.values)
        object.__setattr__(self, "values", values)
        if not values or any(type(value) is not str for value in values):
            raise ValueError("Form values must be a non-empty tuple of strings.")


@dataclass(frozen=True, slots=True)
class FormValuesV1:
    """Immutable allowlisted values retained from one browser form."""

    entries: tuple[FormValueV1, ...] = ()

    def __post_init__(self) -> None:
        entries = tuple(self.entries)
        object.__setattr__(self, "entries", entries)
        if any(type(entry) is not FormValueV1 for entry in entries):
            raise ValueError("Form values must contain exact FormValueV1 entries.")
        fields = tuple(entry.field for entry in entries)
        if len(fields) != len(set(fields)):
            raise ValueError("Form values must contain each field at most once.")

    def contains(self, field: str) -> bool:
        return any(entry.field == field for entry in self.entries)

    def all(self, field: str) -> tuple[str, ...]:
        for entry in self.entries:
            if entry.field == field:
                return entry.values
        return ()

    def singular(self, field: str) -> str | None:
        values = self.all(field)
        return values[0] if len(values) == 1 else None


@dataclass(frozen=True, slots=True)
class FormFieldErrorV1:
    """One immutable field-local browser validation message."""

    field: str
    message: str

    def __post_init__(self) -> None:
        if type(self.field) is not str or not self.field:
            raise ValueError("Form error field must be non-empty text.")
        if type(self.message) is not str or not self.message:
            raise ValueError("Form error message must be non-empty text.")


@dataclass(frozen=True, slots=True)
class FormMappingResultV1:
    """Strict parsing result with allowlisted values and immutable errors."""

    values: FormValuesV1
    errors: tuple[FormFieldErrorV1, ...] = ()

    def __post_init__(self) -> None:
        if type(self.values) is not FormValuesV1:
            raise ValueError("Form mapping result requires exact FormValuesV1 values.")
        errors = tuple(self.errors)
        object.__setattr__(self, "errors", errors)
        if any(type(error) is not FormFieldErrorV1 for error in errors):
            raise ValueError("Form mapping errors must be exact FormFieldErrorV1 values.")


def parse_form_mapping_v1(
    values: Mapping[str, list[str] | tuple[str, ...]],
    *,
    allowed_fields: tuple[str, ...],
    multi_value_fields: tuple[str, ...] = (),
) -> FormMappingResultV1:
    """Strictly parses the shape produced by ``urllib.parse.parse_qs``.

    Unknown names, malformed value sequences, and repeated singular controls
    are retained as deterministic field errors. Unknown values are never
    retained in the safe draft.
    """

    if not isinstance(values, Mapping):
        return FormMappingResultV1(
            values=FormValuesV1(),
            errors=(
                FormFieldErrorV1(
                    field="_form",
                    message="Form values must be a mapping of field names to string lists.",
                ),
            ),
        )
    if (
        type(allowed_fields) is not tuple
        or any(type(field) is not str or not field for field in allowed_fields)
        or len(allowed_fields) != len(set(allowed_fields))
    ):
        raise ValueError("allowed_fields must be unique non-empty strings in a tuple.")
    if (
        type(multi_value_fields) is not tuple
        or any(type(field) is not str or not field for field in multi_value_fields)
        or len(multi_value_fields) != len(set(multi_value_fields))
        or not set(multi_value_fields).issubset(allowed_fields)
    ):
        raise ValueError("multi_value_fields must be an allowlisted unique string tuple.")

    errors: list[FormFieldErrorV1] = []
    supplied_names = set()
    for field in values:
        if type(field) is not str:
            errors.append(
                FormFieldErrorV1(
                    field="_form",
                    message="Form field names must be strings.",
                )
            )
            continue
        supplied_names.add(field)
    for field in sorted(supplied_names.difference(allowed_fields)):
        errors.append(
            FormFieldErrorV1(
                field=field,
                message=f"Unsupported form field: {field}.",
            )
        )

    entries: list[FormValueV1] = []
    multi_fields = set(multi_value_fields)
    for field in allowed_fields:
        if field not in values:
            continue
        raw_values = values[field]
        if not isinstance(raw_values, (list, tuple)):
            errors.append(
                FormFieldErrorV1(
                    field=field,
                    message="Form field values must be a list or tuple of strings.",
                )
            )
            continue
        retained = tuple(raw_values)
        if not retained or any(type(value) is not str for value in retained):
            errors.append(
                FormFieldErrorV1(
                    field=field,
                    message="Form field values must be a non-empty list or tuple of strings.",
                )
            )
            continue
        entries.append(FormValueV1(field=field, values=retained))
        if field not in multi_fields and len(retained) != 1:
            errors.append(
                FormFieldErrorV1(
                    field=field,
                    message="This field must be supplied exactly once.",
                )
            )

    return FormMappingResultV1(
        values=FormValuesV1(tuple(entries)),
        errors=tuple(errors),
    )


def parse_checkbox_v1(values: FormValuesV1, field: str) -> bool:
    """Returns the strict HTML-checkbox state (omitted or exactly ``on``)."""

    raw = values.all(field)
    if not raw:
        return False
    if raw == ("on",):
        return True
    raise ValueError("Checkbox value must be 'on' when selected.")


def parse_integer_text_v1(
    value: str,
    *,
    field: str,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    """Parses one unpadded base-10 integer and enforces optional bounds."""

    if type(value) is not str or not value:
        raise ValueError(f"{field} must be an integer.")
    unsigned = value[1:] if value.startswith("-") else value
    if not unsigned.isascii() or not unsigned.isdecimal():
        raise ValueError(f"{field} must be an integer.")
    if len(unsigned) > 1 and unsigned.startswith("0"):
        raise ValueError(f"{field} must be an integer without leading zeroes.")
    parsed = int(value)
    if minimum is not None and parsed < minimum:
        raise ValueError(f"{field} must be at least {minimum}.")
    if maximum is not None and parsed > maximum:
        raise ValueError(f"{field} must be at most {maximum}.")
    return parsed
