from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from .localization_contracts import (
    FRONTEND_FALLBACK_LOCALE,
    FrontendLocaleResolutionV1,
)

_LANGUAGE_RANGE = re.compile(r"(?:[A-Za-z]{1,8}(?:-[A-Za-z0-9]{1,8})*|\*)\Z")
_QUALITY = re.compile(r"(?:0(?:\.[0-9]{0,3})?|1(?:\.0{0,3})?)\Z")


def _candidate_locale(language_range: str) -> str | None:
    primary = language_range.split("-", 1)[0].lower()
    return primary if primary in {"de", "en"} else None


def parse_accept_language_v1(value: str | None) -> str | None:
    if value is None or type(value) is not str or not value or len(value) > 8_192:
        return None
    candidates: list[tuple[Decimal, int, str]] = []
    for index, raw_item in enumerate(value.split(",")):
        parts = [part.strip() for part in raw_item.split(";")]
        language_range = parts[0] if parts else ""
        if not _LANGUAGE_RANGE.fullmatch(language_range):
            continue
        quality = Decimal("1")
        malformed = False
        quality_seen = False
        for parameter in parts[1:]:
            name, separator, raw_quality = parameter.partition("=")
            if (
                not separator
                or name.strip().lower() != "q"
                or quality_seen
                or not _QUALITY.fullmatch(raw_quality.strip())
            ):
                malformed = True
                break
            quality_seen = True
            try:
                quality = Decimal(raw_quality.strip())
            except InvalidOperation:
                malformed = True
                break
        if malformed or quality <= 0:
            continue
        locale = _candidate_locale(language_range)
        if locale is not None:
            candidates.append((quality, index, locale))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (-item[0], item[1]))
    return candidates[0][2]


def resolve_frontend_locale_v1(
    *,
    saved_language: str | None,
    accept_language: str | None,
    profile_status: str,
) -> FrontendLocaleResolutionV1:
    if saved_language is not None:
        if saved_language not in {"de", "en"}:
            raise ValueError("saved_language must be null or a supported locale.")
        if profile_status != "available":
            raise ValueError("A saved language requires an available profile.")
        return FrontendLocaleResolutionV1(locale=saved_language, source="saved_profile")
    if profile_status not in {"absent", "available", "invalid"}:
        raise ValueError("profile_status must be canonical.")
    if profile_status != "invalid":
        browser_locale = parse_accept_language_v1(accept_language)
        if browser_locale is not None:
            return FrontendLocaleResolutionV1(locale=browser_locale, source="browser")
    return FrontendLocaleResolutionV1(
        locale=FRONTEND_FALLBACK_LOCALE,
        source="fallback",
    )
