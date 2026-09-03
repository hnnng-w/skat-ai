from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date

PROFILE_DRIVEN_FORM_DEFAULTS_VERSION = 1

MAX_KNOWN_PLAYERS = 512
MAX_ALIASES_PER_PLAYER = 16
MAX_PLATFORM_IDS_PER_PLAYER = 16
MAX_PLAYER_NAME_CHARACTERS = 120
MAX_PLATFORM_PLAYER_ID_CHARACTERS = 255
MAX_MANAGED_ITEM_DISPLAY_LABELS = 2_048
MAX_MANAGED_ITEM_DISPLAY_NAME_CHARACTERS = 160

MANAGED_ITEM_FAMILIES = ("sessions", "matches", "corpora")

_FRONTEND_PLAYER_ID = re.compile(r"frontend-player-[0-9a-f]{64}\Z")


def _require_bounded_text(value: object, name: str, maximum: int) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise ValueError(f"{name} must be non-empty trimmed text.")
    if len(value) > maximum:
        raise ValueError(f"{name} must contain at most {maximum} Unicode characters.")
    if any(not character.isprintable() for character in value):
        raise ValueError(f"{name} must not contain control characters.")
    return value


def normalize_player_display_name_v1(value: str) -> str:
    """Normalize only Unicode composition and case for duplicate-name checks."""

    _require_bounded_text(value, "display_name", MAX_PLAYER_NAME_CHARACTERS)
    return unicodedata.normalize("NFC", value).casefold()


@dataclass(frozen=True, slots=True)
class KnownPlayerPlatformIdV1:
    platform: str
    player_id: str

    def __post_init__(self) -> None:
        _require_bounded_text(self.platform, "platform", MAX_PLAYER_NAME_CHARACTERS)
        _require_bounded_text(
            self.player_id,
            "platform player_id",
            MAX_PLATFORM_PLAYER_ID_CHARACTERS,
        )

    def to_dict(self) -> dict[str, object]:
        return {"platform": self.platform, "player_id": self.player_id}


@dataclass(frozen=True, slots=True)
class KnownPlayerV1:
    player_id: str
    display_name: str
    aliases: tuple[str, ...]
    platform_player_ids: tuple[KnownPlayerPlatformIdV1, ...]

    def __post_init__(self) -> None:
        if type(self.player_id) is not str or _FRONTEND_PLAYER_ID.fullmatch(self.player_id) is None:
            raise ValueError("player_id must be one generated frontend Player identifier.")
        _require_bounded_text(
            self.display_name,
            "display_name",
            MAX_PLAYER_NAME_CHARACTERS,
        )
        if type(self.aliases) is not tuple:
            raise ValueError("aliases must be an exact tuple.")
        if len(self.aliases) > MAX_ALIASES_PER_PLAYER:
            raise ValueError("aliases must contain at most 16 values.")
        for alias in self.aliases:
            _require_bounded_text(alias, "alias", MAX_PLAYER_NAME_CHARACTERS)
        if len(set(self.aliases)) != len(self.aliases):
            raise ValueError("aliases must not repeat.")
        if type(self.platform_player_ids) is not tuple:
            raise ValueError("platform_player_ids must be an exact tuple.")
        if len(self.platform_player_ids) > MAX_PLATFORM_IDS_PER_PLAYER:
            raise ValueError("platform_player_ids must contain at most 16 values.")
        if any(type(value) is not KnownPlayerPlatformIdV1 for value in self.platform_player_ids):
            raise ValueError("platform_player_ids must contain exact platform identifiers.")
        if len(set(self.platform_player_ids)) != len(self.platform_player_ids):
            raise ValueError("platform_player_ids must not repeat.")

    def to_dict(self) -> dict[str, object]:
        return {
            "player_id": self.player_id,
            "display_name": self.display_name,
            "aliases": list(self.aliases),
            "platform_player_ids": [value.to_dict() for value in self.platform_player_ids],
        }


@dataclass(frozen=True, slots=True)
class ManagedItemDisplayLabelV1:
    family: str
    product_id: str
    display_name: str
    played_date: str | None = None

    def __post_init__(self) -> None:
        if self.family not in MANAGED_ITEM_FAMILIES:
            raise ValueError("family must identify Sessions, Matches, or Corpora.")
        if (
            type(self.product_id) is not str
            or not self.product_id
            or self.product_id != self.product_id.strip()
        ):
            raise ValueError("product_id must be non-empty trimmed text.")
        _require_bounded_text(
            self.display_name,
            "display_name",
            MAX_MANAGED_ITEM_DISPLAY_NAME_CHARACTERS,
        )
        if self.played_date is not None:
            if self.family != "matches":
                raise ValueError("played_date is permitted only for Matches.")
            if type(self.played_date) is not str:
                raise ValueError("played_date must be null or exact YYYY-MM-DD.")
            try:
                parsed = date.fromisoformat(self.played_date)
            except ValueError as exc:
                raise ValueError("played_date must be null or exact YYYY-MM-DD.") from exc
            if parsed.isoformat() != self.played_date:
                raise ValueError("played_date must be null or exact YYYY-MM-DD.")

    def to_dict(self) -> dict[str, object]:
        return {
            "family": self.family,
            "product_id": self.product_id,
            "display_name": self.display_name,
            "played_date": self.played_date,
        }
