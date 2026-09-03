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
from .profile_player_contracts import (
    KnownPlayerPlatformIdV1,
    KnownPlayerV1,
    ManagedItemDisplayLabelV1,
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
_DEFAULT_INTERFACE_PREFERENCES = FrontendInterfacePreferencesV1()
_DEFAULT_WORKFLOW_PREFERENCES = FrontendWorkflowPreferencesV1()


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


def _payload_dict(
    *,
    revision: int,
    language: str | None,
    interface_preferences: FrontendInterfacePreferencesV1,
    own_player_id: str | None,
    known_players: tuple[KnownPlayerV1, ...],
    preferred_perspective_player_id: str | None,
    preferred_game_platform: str | None,
    workflow_preferences: FrontendWorkflowPreferencesV1,
    managed_item_display_labels: tuple[ManagedItemDisplayLabelV1, ...],
) -> dict[str, object]:
    return {
        "local_frontend_profile_version": LOCAL_FRONTEND_PROFILE_VERSION,
        "document_kind": LOCAL_FRONTEND_PROFILE_DOCUMENT_KIND,
        "revision": revision,
        "language": language,
        "interface_preferences": interface_preferences.to_dict(),
        "own_player_id": own_player_id,
        "known_players": [player.to_dict() for player in known_players],
        "preferred_perspective_player_id": preferred_perspective_player_id,
        "preferred_game_platform": preferred_game_platform,
        "workflow_preferences": workflow_preferences.to_dict(),
        "managed_item_display_labels": [label.to_dict() for label in managed_item_display_labels],
    }


def build_frontend_profile_fingerprint_v1(
    *,
    revision: int,
    language: str | None,
    interface_preferences: FrontendInterfacePreferencesV1 = _DEFAULT_INTERFACE_PREFERENCES,
    own_player_id: str | None = None,
    known_players: tuple[KnownPlayerV1, ...] = (),
    preferred_perspective_player_id: str | None = None,
    preferred_game_platform: str | None = None,
    workflow_preferences: FrontendWorkflowPreferencesV1 = _DEFAULT_WORKFLOW_PREFERENCES,
    managed_item_display_labels: tuple[ManagedItemDisplayLabelV1, ...] = (),
) -> str:
    candidate = LocalFrontendProfileV1(
        revision=revision,
        language=language,
        interface_preferences=interface_preferences,
        own_player_id=own_player_id,
        known_players=known_players,
        preferred_perspective_player_id=preferred_perspective_player_id,
        preferred_game_platform=preferred_game_platform,
        workflow_preferences=workflow_preferences,
        managed_item_display_labels=managed_item_display_labels,
        content_fingerprint="0" * 64,
    )
    payload = _payload_dict(
        revision=candidate.revision,
        language=candidate.language,
        interface_preferences=candidate.interface_preferences,
        own_player_id=candidate.own_player_id,
        known_players=candidate.known_players,
        preferred_perspective_player_id=candidate.preferred_perspective_player_id,
        preferred_game_platform=candidate.preferred_game_platform,
        workflow_preferences=candidate.workflow_preferences,
        managed_item_display_labels=candidate.managed_item_display_labels,
    )
    return hashlib.sha256(
        FRONTEND_PROFILE_FINGERPRINT_DOMAIN + _canonical_json_bytes(payload)
    ).hexdigest()


def build_local_frontend_profile_v1(
    *,
    revision: int = 0,
    language: str | None = None,
    interface_preferences: FrontendInterfacePreferencesV1 = _DEFAULT_INTERFACE_PREFERENCES,
    own_player_id: str | None = None,
    known_players: tuple[KnownPlayerV1, ...] = (),
    preferred_perspective_player_id: str | None = None,
    preferred_game_platform: str | None = None,
    workflow_preferences: FrontendWorkflowPreferencesV1 = _DEFAULT_WORKFLOW_PREFERENCES,
    managed_item_display_labels: tuple[ManagedItemDisplayLabelV1, ...] = (),
) -> LocalFrontendProfileV1:
    return LocalFrontendProfileV1(
        revision=revision,
        language=language,
        interface_preferences=interface_preferences,
        own_player_id=own_player_id,
        known_players=known_players,
        preferred_perspective_player_id=preferred_perspective_player_id,
        preferred_game_platform=preferred_game_platform,
        workflow_preferences=workflow_preferences,
        managed_item_display_labels=managed_item_display_labels,
        content_fingerprint=build_frontend_profile_fingerprint_v1(
            revision=revision,
            language=language,
            interface_preferences=interface_preferences,
            own_player_id=own_player_id,
            known_players=known_players,
            preferred_perspective_player_id=preferred_perspective_player_id,
            preferred_game_platform=preferred_game_platform,
            workflow_preferences=workflow_preferences,
            managed_item_display_labels=managed_item_display_labels,
        ),
    )


def build_frontend_profile_bytes_v1(document: LocalFrontendProfileV1) -> bytes:
    if type(document) is not LocalFrontendProfileV1:
        raise ValueError("document must be an exact LocalFrontendProfileV1.")
    canonical = build_local_frontend_profile_v1(
        revision=document.revision,
        language=document.language,
        interface_preferences=document.interface_preferences,
        own_player_id=document.own_player_id,
        known_players=document.known_players,
        preferred_perspective_player_id=document.preferred_perspective_player_id,
        preferred_game_platform=document.preferred_game_platform,
        workflow_preferences=document.workflow_preferences,
        managed_item_display_labels=document.managed_item_display_labels,
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
    if type(known_players) is not list:
        raise ValueError("known_players must be an array.")
    if type(labels) is not list:
        raise ValueError("managed_item_display_labels must be an array.")
    resumed_players: list[KnownPlayerV1] = []
    for index, value in enumerate(known_players):
        player = _exact_mapping(
            value,
            ("player_id", "display_name", "aliases", "platform_player_ids"),
            f"known_players[{index}]",
        )
        aliases = player["aliases"]
        platform_ids = player["platform_player_ids"]
        if type(aliases) is not list or type(platform_ids) is not list:
            raise ValueError("Known Player aliases and platform IDs must be arrays.")
        resumed_platform_ids: list[KnownPlayerPlatformIdV1] = []
        for platform_index, platform_value in enumerate(platform_ids):
            platform_id = _exact_mapping(
                platform_value,
                ("platform", "player_id"),
                f"known_players[{index}].platform_player_ids[{platform_index}]",
            )
            resumed_platform_ids.append(
                KnownPlayerPlatformIdV1(
                    platform=platform_id["platform"],
                    player_id=platform_id["player_id"],
                )
            )
        resumed_players.append(
            KnownPlayerV1(
                player_id=player["player_id"],
                display_name=player["display_name"],
                aliases=tuple(aliases),
                platform_player_ids=tuple(resumed_platform_ids),
            )
        )
    resumed_labels: list[ManagedItemDisplayLabelV1] = []
    for index, value in enumerate(labels):
        label = _exact_mapping(
            value,
            ("family", "product_id", "display_name", "played_date"),
            f"managed_item_display_labels[{index}]",
        )
        resumed_labels.append(
            ManagedItemDisplayLabelV1(
                family=label["family"],
                product_id=label["product_id"],
                display_name=label["display_name"],
                played_date=label["played_date"],
            )
        )
    result = LocalFrontendProfileV1(
        local_frontend_profile_version=document["local_frontend_profile_version"],
        document_kind=document["document_kind"],
        revision=document["revision"],
        language=document["language"],
        interface_preferences=FrontendInterfacePreferencesV1(
            advanced_settings_expanded=interface["advanced_settings_expanded"]
        ),
        own_player_id=document["own_player_id"],
        known_players=tuple(resumed_players),
        preferred_perspective_player_id=document["preferred_perspective_player_id"],
        preferred_game_platform=document["preferred_game_platform"],
        workflow_preferences=FrontendWorkflowPreferencesV1(
            position_analysis=workflow["position_analysis"],
            historical_review=workflow["historical_review"],
        ),
        managed_item_display_labels=tuple(resumed_labels),
        content_fingerprint=document["content_fingerprint"],
    )
    if result != build_local_frontend_profile_v1(
        revision=result.revision,
        language=result.language,
        interface_preferences=result.interface_preferences,
        own_player_id=result.own_player_id,
        known_players=result.known_players,
        preferred_perspective_player_id=result.preferred_perspective_player_id,
        preferred_game_platform=result.preferred_game_platform,
        workflow_preferences=result.workflow_preferences,
        managed_item_display_labels=result.managed_item_display_labels,
    ):
        raise ValueError("Frontend profile fingerprint is invalid.")
    return result
