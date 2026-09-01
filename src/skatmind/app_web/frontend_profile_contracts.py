from __future__ import annotations

from dataclasses import dataclass

LOCAL_FRONTEND_PROFILE_VERSION = 1
LOCAL_FRONTEND_PROFILE_DOCUMENT_KIND = "skatmind_frontend_profile"
FRONTEND_PROFILE_FILENAME = "frontend-profile.json"
FRONTEND_PROFILE_MAX_FILE_BYTES = 1_048_576
FRONTEND_PROFILE_FINGERPRINT_DOMAIN = b"skatmind\0frontend_profile_v1\0"
FRONTEND_PROFILE_LOAD_STATUSES = ("absent", "available", "invalid")
FRONTEND_PROFILE_WRITE_STATUSES = ("saved", "unchanged", "conflict")


def _require_sha256(value: object, name: str) -> None:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{name} must be one lowercase SHA-256 value.")


@dataclass(frozen=True, slots=True)
class FrontendInterfacePreferencesV1:
    advanced_settings_expanded: bool = False

    def __post_init__(self) -> None:
        if self.advanced_settings_expanded is not False:
            raise ValueError("advanced_settings_expanded must remain false in version 1.")

    def to_dict(self) -> dict[str, object]:
        return {"advanced_settings_expanded": False}


@dataclass(frozen=True, slots=True)
class FrontendWorkflowPreferencesV1:
    position_analysis: None = None
    historical_review: None = None

    def __post_init__(self) -> None:
        if self.position_analysis is not None or self.historical_review is not None:
            raise ValueError("Workflow preferences must remain null in Issue #216.")

    def to_dict(self) -> dict[str, object]:
        return {"position_analysis": None, "historical_review": None}


@dataclass(frozen=True, slots=True)
class LocalFrontendProfileV1:
    revision: int
    language: str | None
    content_fingerprint: str
    local_frontend_profile_version: int = LOCAL_FRONTEND_PROFILE_VERSION
    document_kind: str = LOCAL_FRONTEND_PROFILE_DOCUMENT_KIND
    interface_preferences: FrontendInterfacePreferencesV1 = (
        FrontendInterfacePreferencesV1()
    )
    own_player_id: None = None
    known_players: tuple[object, ...] = ()
    preferred_perspective_player_id: None = None
    preferred_game_platform: None = None
    workflow_preferences: FrontendWorkflowPreferencesV1 = FrontendWorkflowPreferencesV1()
    managed_item_display_labels: tuple[object, ...] = ()

    def __post_init__(self) -> None:
        if (
            type(self.local_frontend_profile_version) is not int
            or self.local_frontend_profile_version != LOCAL_FRONTEND_PROFILE_VERSION
        ):
            raise ValueError("local_frontend_profile_version must be 1.")
        if self.document_kind != LOCAL_FRONTEND_PROFILE_DOCUMENT_KIND:
            raise ValueError("document_kind must identify a SkatMind frontend profile.")
        if type(self.revision) is not int or self.revision < 0:
            raise ValueError("revision must be a non-negative integer.")
        if self.language not in {None, "de", "en"}:
            raise ValueError("language must be de, en, or null.")
        if type(self.interface_preferences) is not FrontendInterfacePreferencesV1:
            raise ValueError("interface_preferences must be exact version-1 preferences.")
        if self.own_player_id is not None or self.preferred_perspective_player_id is not None:
            raise ValueError("Player preferences must remain null in Issue #216.")
        if self.preferred_game_platform is not None:
            raise ValueError("preferred_game_platform must remain null in Issue #216.")
        if type(self.known_players) is not tuple or self.known_players:
            raise ValueError("known_players must remain empty in Issue #216.")
        if type(self.workflow_preferences) is not FrontendWorkflowPreferencesV1:
            raise ValueError("workflow_preferences must be exact version-1 preferences.")
        if type(self.managed_item_display_labels) is not tuple or self.managed_item_display_labels:
            raise ValueError("managed_item_display_labels must remain empty in Issue #216.")
        _require_sha256(self.content_fingerprint, "content_fingerprint")

    def to_dict(self) -> dict[str, object]:
        return {
            "local_frontend_profile_version": self.local_frontend_profile_version,
            "document_kind": self.document_kind,
            "revision": self.revision,
            "language": self.language,
            "interface_preferences": self.interface_preferences.to_dict(),
            "own_player_id": None,
            "known_players": [],
            "preferred_perspective_player_id": None,
            "preferred_game_platform": None,
            "workflow_preferences": self.workflow_preferences.to_dict(),
            "managed_item_display_labels": [],
            "content_fingerprint": self.content_fingerprint,
        }


@dataclass(frozen=True, slots=True)
class FrontendProfileLoadResultV1:
    status: str
    document: LocalFrontendProfileV1 | None = None
    invalid_raw_digest: str | None = None

    def __post_init__(self) -> None:
        if self.status not in FRONTEND_PROFILE_LOAD_STATUSES:
            raise ValueError("Profile load status must be canonical.")
        if self.status == "available":
            if type(self.document) is not LocalFrontendProfileV1:
                raise ValueError("Available profile load requires one exact document.")
            if self.invalid_raw_digest is not None:
                raise ValueError("Available profile load must not retain an invalid digest.")
        elif self.document is not None:
            raise ValueError("Only an available profile load may retain a document.")
        if self.status == "invalid" and self.invalid_raw_digest is None:
            raise ValueError("Invalid profile load requires one observation digest.")
        if self.status != "invalid" and self.invalid_raw_digest is not None:
            raise ValueError("Only an invalid profile load may retain an invalid digest.")
        if self.invalid_raw_digest is not None:
            _require_sha256(self.invalid_raw_digest, "invalid_raw_digest")


@dataclass(frozen=True, slots=True)
class FrontendProfileWriteResultV1:
    status: str
    document: LocalFrontendProfileV1

    def __post_init__(self) -> None:
        if self.status not in FRONTEND_PROFILE_WRITE_STATUSES:
            raise ValueError("Profile write status must be canonical.")
        if type(self.document) is not LocalFrontendProfileV1:
            raise ValueError("Profile write result requires one exact document.")
