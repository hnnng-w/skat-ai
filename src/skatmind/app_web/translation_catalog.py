from __future__ import annotations

import json
from collections.abc import Mapping
from functools import lru_cache
from importlib.resources import files
from string import Formatter
from types import MappingProxyType

from .localization_contracts import SUPPORTED_FRONTEND_LOCALES

_UTF8_BOM = b"\xef\xbb\xbf"
_CATALOG_PACKAGE = "skatmind.app_web"


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Frontend translation catalogs must not repeat keys.")
        result[key] = value
    return result


def _reject_non_finite(value: str) -> object:
    raise ValueError(f"Non-finite JSON number {value!r} is not allowed.")


def _placeholders(value: str) -> frozenset[str]:
    placeholders: set[str] = set()
    try:
        parsed = Formatter().parse(value)
        for _literal, field_name, format_spec, conversion in parsed:
            if field_name is None:
                continue
            if (
                not field_name.isidentifier()
                or format_spec
                or conversion is not None
                or field_name in placeholders
            ):
                raise ValueError("Translation placeholders must be unique simple names.")
            placeholders.add(field_name)
    except ValueError as error:
        raise ValueError("Frontend translation catalog has invalid interpolation.") from error
    return frozenset(placeholders)


def _load_catalog(locale: str) -> dict[str, str]:
    raw = files(_CATALOG_PACKAGE).joinpath(f"locales/{locale}.json").read_bytes()
    if raw.startswith(_UTF8_BOM):
        raise ValueError("Frontend translation catalogs must use UTF-8 without a BOM.")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise ValueError("Frontend translation catalog is not valid UTF-8.") from error
    try:
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_non_finite,
        )
    except json.JSONDecodeError as error:
        raise ValueError("Frontend translation catalog is not valid JSON.") from error
    if type(value) is not dict:
        raise ValueError("Frontend translation catalog root must be an object.")
    keys = list(value)
    if keys != sorted(keys) or len(keys) != len(set(keys)):
        mismatch = next(
            (
                f"{actual!r} before {expected!r}"
                for actual, expected in zip(keys, sorted(keys), strict=True)
                if actual != expected
            ),
            "duplicate key",
        )
        raise ValueError(
            "Frontend translation catalog keys must be lexicographically ordered: "
            f"{mismatch}."
        )
    if any(
        type(key) is not str
        or not key
        or type(message) is not str
        or not message.strip()
        for key, message in value.items()
    ):
        raise ValueError("Frontend translation catalog keys and values must be non-empty text.")
    return value


@lru_cache(maxsize=1)
def load_frontend_translation_catalogs_v1() -> Mapping[str, Mapping[str, str]]:
    loaded = {locale: _load_catalog(locale) for locale in SUPPORTED_FRONTEND_LOCALES}
    reference_keys = tuple(loaded["en"])
    for _locale, catalog in loaded.items():
        if tuple(catalog) != reference_keys:
            raise ValueError("Frontend translation catalogs must have exact key parity.")
        for key, message in catalog.items():
            if _placeholders(message) != _placeholders(loaded["en"][key]):
                raise ValueError(
                    "Frontend translation catalogs must have exact placeholder parity."
                )
    return MappingProxyType(
        {
            locale: MappingProxyType(dict(catalog))
            for locale, catalog in loaded.items()
        }
    )


def translate_frontend_message_v1(
    locale: str,
    key: str,
    /,
    **values: object,
) -> str:
    if locale not in SUPPORTED_FRONTEND_LOCALES:
        raise ValueError("locale must be a supported frontend locale.")
    if type(key) is not str or not key:
        raise ValueError("Translation key must be non-empty text.")
    catalogs = load_frontend_translation_catalogs_v1()
    catalog = catalogs[locale]
    if key not in catalog:
        raise KeyError(key)
    template = catalog[key]
    required = _placeholders(template)
    if set(values) != set(required):
        raise ValueError("Translation interpolation values must exactly match placeholders.")
    return template.format_map({name: str(value) for name, value in values.items()})
