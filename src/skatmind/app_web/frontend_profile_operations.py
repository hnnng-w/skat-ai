from __future__ import annotations

import re
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from .frontend_profile_codec import build_local_frontend_profile_v1
from .frontend_profile_contracts import (
    FrontendInterfacePreferencesV1,
    LocalFrontendProfileV1,
)
from .frontend_profile_persistence import save_frontend_profile_file_v1
from .frontend_profile_state import state_from_saved_profile_v1

if TYPE_CHECKING:
    from .context import AppWebContextV1

FRONTEND_LANGUAGE_ACTION_ROUTE = "/actions/profile/language"
FRONTEND_PROFILE_RESET_ACTION_ROUTE = "/actions/profile/reset"
FRONTEND_PROFILE_PLAYER_ADD_ACTION_ROUTE = "/actions/profile/players/add"
FRONTEND_PROFILE_PLAYER_UPDATE_ACTION_ROUTE = "/actions/profile/players/update"
FRONTEND_PROFILE_PLAYER_REMOVE_ACTION_ROUTE = "/actions/profile/players/remove"
FRONTEND_PROFILE_PREFERENCES_ACTION_ROUTE = "/actions/profile/preferences"
FRONTEND_PROFILE_RECOMMENDED_RESET_ACTION_ROUTE = "/actions/profile/recommended-defaults/reset"
FRONTEND_PROFILE_MANAGED_LABEL_ACTION_ROUTE = "/actions/profile/managed-label"
FRONTEND_PROFILE_ACTION_ROUTES = (
    FRONTEND_LANGUAGE_ACTION_ROUTE,
    FRONTEND_PROFILE_RESET_ACTION_ROUTE,
    FRONTEND_PROFILE_PLAYER_ADD_ACTION_ROUTE,
    FRONTEND_PROFILE_PLAYER_UPDATE_ACTION_ROUTE,
    FRONTEND_PROFILE_PLAYER_REMOVE_ACTION_ROUTE,
    FRONTEND_PROFILE_PREFERENCES_ACTION_ROUTE,
    FRONTEND_PROFILE_RECOMMENDED_RESET_ACTION_ROUTE,
    FRONTEND_PROFILE_MANAGED_LABEL_ACTION_ROUTE,
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


def save_prepared_frontend_profile_v1(
    context: AppWebContextV1,
    *,
    requested: LocalFrontendProfileV1,
    expected_generation: int,
    allow_invalid_reset: bool = False,
) -> str:
    if type(requested) is not LocalFrontendProfileV1:
        raise ValueError("requested must be an exact frontend profile.")
    if type(expected_generation) is not int or expected_generation < 0:
        raise ValueError("expected_generation must be a non-negative integer.")
    if type(allow_invalid_reset) is not bool:
        raise ValueError("allow_invalid_reset must be a boolean.")
    with context.profile_lock:
        with context.lock:
            state = context.frontend_profile
            if state.generation != expected_generation:
                raise StaleFrontendProfileGenerationError
            if state.load_status == "invalid" and not allow_invalid_reset:
                raise InvalidFrontendProfileResetRequiredError
            expected_revision = 0 if state.document is None else state.document.revision + 1
            if requested.revision != expected_revision:
                raise ValueError("Prepared profile revision must advance exactly once.")
        result = save_frontend_profile_file_v1(
            context.managed_home.root,
            requested,
            expected_fingerprint=state.expected_fingerprint,
            expected_invalid_raw_digest=(state.invalid_raw_digest if allow_invalid_reset else None),
        )
        if result.status == "conflict":
            raise FrontendProfilePersistenceConflictError
        _publish_profile(
            context,
            generation=expected_generation,
            document=requested,
        )
        return result.status


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
                interface_preferences=(
                    FrontendInterfacePreferencesV1()
                    if state.document is None
                    else state.document.interface_preferences
                ),
                own_player_id=(None if state.document is None else state.document.own_player_id),
                known_players=(() if state.document is None else state.document.known_players),
                preferred_perspective_player_id=(
                    None
                    if state.document is None
                    else state.document.preferred_perspective_player_id
                ),
                preferred_game_platform=(
                    None if state.document is None else state.document.preferred_game_platform
                ),
                workflow_preferences=(
                    state.document.workflow_preferences
                    if state.document is not None
                    else build_local_frontend_profile_v1().workflow_preferences
                ),
                managed_item_display_labels=(
                    () if state.document is None else state.document.managed_item_display_labels
                ),
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


def reset_frontend_recommended_defaults_v1(
    context: AppWebContextV1,
    *,
    expected_generation: int,
) -> str:
    if type(expected_generation) is not int or expected_generation < 0:
        raise ValueError("expected_generation must be a non-negative integer.")
    with context.lock:
        state = context.frontend_profile
        if state.generation != expected_generation:
            raise StaleFrontendProfileGenerationError
        if state.load_status == "invalid":
            raise InvalidFrontendProfileResetRequiredError
        document = state.document
        if document is None:
            return "unchanged"
        if (
            document.preferred_perspective_player_id is None
            and document.preferred_game_platform is None
            and document.interface_preferences.advanced_settings_expanded is False
        ):
            return "unchanged"
        requested = build_local_frontend_profile_v1(
            revision=document.revision + 1,
            language=document.language,
            interface_preferences=FrontendInterfacePreferencesV1(),
            own_player_id=document.own_player_id,
            known_players=document.known_players,
            preferred_perspective_player_id=None,
            preferred_game_platform=None,
            workflow_preferences=document.workflow_preferences,
            managed_item_display_labels=document.managed_item_display_labels,
        )
    return save_prepared_frontend_profile_v1(
        context,
        requested=requested,
        expected_generation=expected_generation,
    )


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
            revision = 0 if state.document is None else state.document.revision + 1
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
