from __future__ import annotations

import re
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from .frontend_profile_codec import build_local_frontend_profile_v1
from .frontend_profile_persistence import save_frontend_profile_file_v1
from .frontend_profile_state import state_from_saved_profile_v1

if TYPE_CHECKING:
    from .context import AppWebContextV1

FRONTEND_LANGUAGE_ACTION_ROUTE = "/actions/profile/language"
FRONTEND_PROFILE_RESET_ACTION_ROUTE = "/actions/profile/reset"
FRONTEND_PROFILE_ACTION_ROUTES = (
    FRONTEND_LANGUAGE_ACTION_ROUTE,
    FRONTEND_PROFILE_RESET_ACTION_ROUTE,
)

_SAFE_STATIC_HTML_ROUTES = {
    "/",
    "/analyze",
    "/review",
    "/sessions",
    "/sessions/current",
    "/matches",
    "/matches/new",
    "/matches/current",
    "/learning",
    "/learning/current",
    "/about",
}
_SAFE_MATCH_POSITION = re.compile(r"/matches/position/(?:[1-9]|[12][0-9]|3[0-6])\Z")
_SAFE_MATCH_REPORT = re.compile(r"/matches/reports/[0-9a-f]{64}\Z")


class StaleFrontendProfileGenerationError(RuntimeError):
    pass


class InvalidFrontendProfileResetRequiredError(RuntimeError):
    pass


class FrontendProfilePersistenceConflictError(RuntimeError):
    pass


def is_safe_frontend_return_path_v1(value: object) -> bool:
    if type(value) is not str or not value or len(value) > 512:
        return False
    try:
        parsed = urlsplit(value)
    except ValueError:
        return False
    if (
        parsed.scheme
        or parsed.netloc
        or parsed.query
        or parsed.fragment
        or parsed.path != value
        or not value.startswith("/")
        or value.startswith("//")
    ):
        return False
    return (
        value in _SAFE_STATIC_HTML_ROUTES
        or _SAFE_MATCH_POSITION.fullmatch(value) is not None
        or _SAFE_MATCH_REPORT.fullmatch(value) is not None
    )


def _publish_profile(
    context: AppWebContextV1,
    *,
    generation: int,
    document,
) -> None:
    with context.lock:
        if context.frontend_profile.generation != generation:
            raise StaleFrontendProfileGenerationError
        context.frontend_profile = state_from_saved_profile_v1(
            context.frontend_profile,
            document,
        )


def set_frontend_language_v1(
    context: AppWebContextV1,
    *,
    language: str,
    expected_generation: int,
) -> str:
    if language not in {"de", "en"}:
        raise ValueError("language must be de or en.")
    if type(expected_generation) is not int or expected_generation < 0:
        raise ValueError("expected_generation must be a non-negative integer.")
    with context.profile_lock:
        with context.lock:
            state = context.frontend_profile
            if state.generation != expected_generation:
                raise StaleFrontendProfileGenerationError
            if state.load_status == "invalid":
                raise InvalidFrontendProfileResetRequiredError
            if state.document is not None and state.document.language == language:
                return "unchanged"
            revision = 0 if state.document is None else state.document.revision + 1
            requested = build_local_frontend_profile_v1(
                revision=revision,
                language=language,
            )
        result = save_frontend_profile_file_v1(
            context.managed_home.root,
            requested,
            expected_fingerprint=state.expected_fingerprint,
        )
        if result.status == "conflict":
            raise FrontendProfilePersistenceConflictError
        _publish_profile(
            context,
            generation=expected_generation,
            document=requested,
        )
        return result.status


def reset_frontend_profile_v1(
    context: AppWebContextV1,
    *,
    expected_generation: int,
) -> str:
    if type(expected_generation) is not int or expected_generation < 0:
        raise ValueError("expected_generation must be a non-negative integer.")
    with context.profile_lock:
        with context.lock:
            state = context.frontend_profile
            if state.generation != expected_generation:
                raise StaleFrontendProfileGenerationError
            revision = (
                0 if state.document is None else state.document.revision + 1
            )
            requested = build_local_frontend_profile_v1(revision=revision)
        result = save_frontend_profile_file_v1(
            context.managed_home.root,
            requested,
            expected_fingerprint=state.expected_fingerprint,
            expected_invalid_raw_digest=state.invalid_raw_digest,
        )
        if result.status == "conflict":
            raise FrontendProfilePersistenceConflictError
        _publish_profile(
            context,
            generation=expected_generation,
            document=requested,
        )
        return result.status
