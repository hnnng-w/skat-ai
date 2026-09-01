from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

from .frontend_profile_contracts import (
    FRONTEND_PROFILE_FINGERPRINT_DOMAIN,
    LOCAL_FRONTEND_PROFILE_DOCUMENT_KIND,
    LOCAL_FRONTEND_PROFILE_VERSION,
    FrontendInterfacePreferencesV1,
    FrontendWorkflowPreferencesV1,
    LocalFrontendProfileV1,
)

_PROFILE_FIELDS = (
    "local_frontend_profile_version",
    "document_kind",
    "revision",
    "language",
    "interface_preferences",
    "own_player_id",
    "known_players",
    "preferred_perspective_player_id",
    "preferred_game_platform",
    "workflow_preferences",
    "managed_item_display_labels",
    "content_fingerprint",
)


def _canonical_json_bytes(value: Mapping[str, object]) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")


def _payload_dict(*, revision: int, language: str | None) -> dict[str, object]:
    return {
        "local_frontend_profile_version": LOCAL_FRONTEND_PROFILE_VERSION,
        "document_kind": LOCAL_FRONTEND_PROFILE_DOCUMENT_KIND,
        "revision": revision,
        "language": language,
        "interface_preferences": {"advanced_settings_expanded": False},
        "own_player_id": None,
        "known_players": [],
        "preferred_perspective_player_id": None,
        "preferred_game_platform": None,
        "workflow_preferences": {
            "position_analysis": None,
            "historical_review": None,
        },
        "managed_item_display_labels": [],
    }


def build_frontend_profile_fingerprint_v1(*, revision: int, language: str | None) -> str:
    if type(revision) is not int or revision < 0:
        raise ValueError("revision must be a non-negative integer.")
    if language not in {None, "de", "en"}:
        raise ValueError("language must be de, en, or null.")
    payload = _payload_dict(revision=revision, language=language)
    return hashlib.sha256(
        FRONTEND_PROFILE_FINGERPRINT_DOMAIN + _canonical_json_bytes(payload)
    ).hexdigest()


def build_local_frontend_profile_v1(
    *,
    revision: int = 0,
    language: str | None = None,
) -> LocalFrontendProfileV1:
    return LocalFrontendProfileV1(
        revision=revision,
        language=language,
        content_fingerprint=build_frontend_profile_fingerprint_v1(
            revision=revision,
            language=language,
        ),
    )


def build_frontend_profile_bytes_v1(document: LocalFrontendProfileV1) -> bytes:
    if type(document) is not LocalFrontendProfileV1:
        raise ValueError("document must be an exact LocalFrontendProfileV1.")
    canonical = build_local_frontend_profile_v1(
        revision=document.revision,
        language=document.language,
    )
    if canonical != document:
        raise ValueError("Frontend profile document is not canonical.")
    return _canonical_json_bytes(document.to_dict())


def _exact_mapping(value: object, fields: tuple[str, ...], name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or tuple(value) != fields:
        raise ValueError(f"{name} must contain exact canonical fields in order.")
    return value


def resume_local_frontend_profile_v1(
    value: Mapping[str, object],
) -> LocalFrontendProfileV1:
    document = _exact_mapping(value, _PROFILE_FIELDS, "Frontend profile")
    interface = _exact_mapping(
        document["interface_preferences"],
        ("advanced_settings_expanded",),
        "interface_preferences",
    )
    workflow = _exact_mapping(
        document["workflow_preferences"],
        ("position_analysis", "historical_review"),
        "workflow_preferences",
    )
    known_players = document["known_players"]
    labels = document["managed_item_display_labels"]
    if type(known_players) is not list or known_players:
        raise ValueError("known_players must be an empty array.")
    if type(labels) is not list or labels:
        raise ValueError("managed_item_display_labels must be an empty array.")
    result = LocalFrontendProfileV1(
        local_frontend_profile_version=document["local_frontend_profile_version"],
        document_kind=document["document_kind"],
        revision=document["revision"],
        language=document["language"],
        interface_preferences=FrontendInterfacePreferencesV1(
            advanced_settings_expanded=interface["advanced_settings_expanded"]
        ),
        own_player_id=document["own_player_id"],
        known_players=(),
        preferred_perspective_player_id=document["preferred_perspective_player_id"],
        preferred_game_platform=document["preferred_game_platform"],
        workflow_preferences=FrontendWorkflowPreferencesV1(
            position_analysis=workflow["position_analysis"],
            historical_review=workflow["historical_review"],
        ),
        managed_item_display_labels=(),
        content_fingerprint=document["content_fingerprint"],
    )
    if result != build_local_frontend_profile_v1(
        revision=result.revision,
        language=result.language,
    ):
        raise ValueError("Frontend profile fingerprint is invalid.")
    return result
