from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from skat_ai.deck import get_full_deck
from skat_ai.game_declaration import (
    GameDeclaration,
    build_serializable_game_declaration,
    validate_game_declaration,
)
from skat_ai.historical_declarer_card_exposure_continuation import (
    HISTORICAL_DECLARER_CARD_EXPOSURE_CONTINUATION_KIND,
)
from skat_ai.historical_defender_open_play_continuation import (
    HISTORICAL_DEFENDER_OPEN_PLAY_CONTINUATION_KIND,
)
from skat_ai.historical_game_end import (
    HISTORICAL_DECLARER_CARD_EXPOSURE,
    HISTORICAL_DECLARER_CONCESSION,
    HISTORICAL_DEFENDER_CONCESSION,
    HISTORICAL_DEFENDER_OPEN_PLAY,
    HISTORICAL_NORMAL_COMPLETION,
    HISTORICAL_OPEN_CARD_THROW,
)
from skat_ai.rfc3339 import parse_rfc3339_datetime

SESSION_COMMAND_VERSION = 1

SESSION_COMMAND_KINDS = (
    "set_game_metadata",
    "record_dealt_card",
    "set_declarer",
    "set_declaration",
    "record_discard",
    "record_play",
    "set_game_event",
    "set_game_end",
    "promote_to_retrospective",
)
SESSION_DEAL_DESTINATIONS = ("player_hand", "skat")
SESSION_GAME_EVENT_KINDS = (
    HISTORICAL_DECLARER_CARD_EXPOSURE_CONTINUATION_KIND,
    HISTORICAL_DEFENDER_OPEN_PLAY_CONTINUATION_KIND,
)
SESSION_GAME_END_REASONS = (
    HISTORICAL_NORMAL_COMPLETION,
    HISTORICAL_DECLARER_CONCESSION,
    HISTORICAL_DEFENDER_CONCESSION,
    HISTORICAL_DECLARER_CARD_EXPOSURE,
    HISTORICAL_DEFENDER_OPEN_PLAY,
    HISTORICAL_OPEN_CARD_THROW,
)

SESSION_COMMAND_ALLOWED_PHASES = MappingProxyType(
    {
        "set_game_metadata": (
            "setup",
            "deal",
            "declaration",
            "skat_and_discard",
            "play",
        ),
        "record_dealt_card": (
            "setup",
            "deal",
            "declaration",
            "skat_and_discard",
        ),
        "set_declarer": ("declaration",),
        "set_declaration": ("declaration",),
        "record_discard": ("skat_and_discard",),
        "record_play": ("play",),
        "set_game_event": ("play",),
        "set_game_end": ("play",),
        "promote_to_retrospective": (
            "setup",
            "deal",
            "declaration",
            "skat_and_discard",
            "play",
            "ended",
        ),
    }
)


def _require_identifier(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{field_name} must be a non-empty, non-padded string.")
    return value


def _require_player_identifier(value: object, field_name: str) -> str:
    player_id = _require_identifier(value, field_name)
    if player_id in {"me", "left", "right"}:
        raise ValueError(f"{field_name} must be a stable, non-relative Player ID.")
    return player_id


def _require_non_negative_integer(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer.")
    return value


def _validate_command_header(command_version: object, expected_revision: object) -> None:
    if type(command_version) is not int or command_version != SESSION_COMMAND_VERSION:
        raise ValueError(f"command_version must equal {SESSION_COMMAND_VERSION}.")
    _require_non_negative_integer(expected_revision, "expected_revision")


def _require_card(value: object, field_name: str) -> str:
    if not isinstance(value, str) or value not in get_full_deck():
        raise ValueError(f"{field_name} must be one valid Skat card.")
    return value


def _freeze_json_value(value: object, field_name: str) -> object:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{field_name} JSON numbers must be finite.")
        return value
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise ValueError(f"{field_name} JSON object keys must be strings.")
        return MappingProxyType(
            {
                key: _freeze_json_value(value[key], f"{field_name}.{key}")
                for key in sorted(value)
            }
        )
    if isinstance(value, (list, tuple)):
        return tuple(
            _freeze_json_value(item, f"{field_name}[{index}]")
            for index, item in enumerate(value)
        )
    raise ValueError(f"{field_name} must contain only JSON-compatible values.")


def _freeze_json_object(value: object, field_name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be a JSON object.")
    frozen = _freeze_json_value(value, field_name)
    if not isinstance(frozen, Mapping):
        raise ValueError(f"{field_name} must be a JSON object.")
    return frozen


def _thaw_json_value(value: object) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_json_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json_value(item) for item in value]
    return value


@dataclass(frozen=True, slots=True, kw_only=True)
class SetSessionGameMetadataCommandV1:
    """Records caller-supplied optional identity or time metadata."""

    command_version: int = SESSION_COMMAND_VERSION
    kind: str = field(init=False, default="set_game_metadata")
    expected_revision: int
    game_id: str | None = None
    played_at: str | None = None

    def __post_init__(self) -> None:
        _validate_command_header(self.command_version, self.expected_revision)
        if self.game_id is None and self.played_at is None:
            raise ValueError("At least one of game_id or played_at must be non-null.")
        if self.game_id is not None:
            _require_identifier(self.game_id, "game_id")
        if self.played_at is not None:
            _require_identifier(self.played_at, "played_at")
            parse_rfc3339_datetime(self.played_at, "played_at")

    def to_dict(self) -> dict[str, Any]:
        return {
            "command_version": self.command_version,
            "kind": self.kind,
            "expected_revision": self.expected_revision,
            "game_id": self.game_id,
            "played_at": self.played_at,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class RecordSessionDealtCardCommandV1:
    """Records one caller-supplied initial hand or Skat card."""

    command_version: int = SESSION_COMMAND_VERSION
    kind: str = field(init=False, default="record_dealt_card")
    expected_revision: int
    destination: str
    player_id: str | None
    card: str

    def __post_init__(self) -> None:
        _validate_command_header(self.command_version, self.expected_revision)
        if self.destination not in SESSION_DEAL_DESTINATIONS:
            raise ValueError(
                f"destination must be one of {list(SESSION_DEAL_DESTINATIONS)}."
            )
        if self.destination == "player_hand":
            _require_player_identifier(self.player_id, "player_id")
        elif self.player_id is not None:
            raise ValueError("player_id must be null when destination is 'skat'.")
        _require_card(self.card, "card")

    def to_dict(self) -> dict[str, Any]:
        return {
            "command_version": self.command_version,
            "kind": self.kind,
            "expected_revision": self.expected_revision,
            "destination": self.destination,
            "player_id": self.player_id,
            "card": self.card,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class SetSessionDeclarerCommandV1:
    """Records one stable declarer Player ID without deriving a contract."""

    command_version: int = SESSION_COMMAND_VERSION
    kind: str = field(init=False, default="set_declarer")
    expected_revision: int
    declarer_player_id: str

    def __post_init__(self) -> None:
        _validate_command_header(self.command_version, self.expected_revision)
        _require_player_identifier(self.declarer_player_id, "declarer_player_id")

    def to_dict(self) -> dict[str, Any]:
        return {
            "command_version": self.command_version,
            "kind": self.kind,
            "expected_revision": self.expected_revision,
            "declarer_player_id": self.declarer_player_id,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class SetSessionDeclarationCommandV1:
    """Wraps one existing validated GameDeclaration."""

    command_version: int = SESSION_COMMAND_VERSION
    kind: str = field(init=False, default="set_declaration")
    expected_revision: int
    declaration: GameDeclaration

    def __post_init__(self) -> None:
        _validate_command_header(self.command_version, self.expected_revision)
        if not isinstance(self.declaration, GameDeclaration):
            raise ValueError("declaration must be a GameDeclaration.")
        validate_game_declaration(self.declaration)
        declaration = GameDeclaration(
            game_type=self.declaration.game_type,
            hand_game=self.declaration.hand_game,
            ouvert=self.declaration.ouvert,
            schneider_announced=self.declaration.schneider_announced,
            schwarz_announced=self.declaration.schwarz_announced,
            matadors=self.declaration.matadors,
            bid_value=self.declaration.bid_value,
        )
        object.__setattr__(self, "declaration", declaration)

    def to_dict(self) -> dict[str, Any]:
        return {
            "command_version": self.command_version,
            "kind": self.kind,
            "expected_revision": self.expected_revision,
            "declaration": build_serializable_game_declaration(self.declaration),
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class RecordSessionDiscardCommandV1:
    """Records one caller-supplied discard card."""

    command_version: int = SESSION_COMMAND_VERSION
    kind: str = field(init=False, default="record_discard")
    expected_revision: int
    card: str

    def __post_init__(self) -> None:
        _validate_command_header(self.command_version, self.expected_revision)
        _require_card(self.card, "card")

    def to_dict(self) -> dict[str, Any]:
        return {
            "command_version": self.command_version,
            "kind": self.kind,
            "expected_revision": self.expected_revision,
            "card": self.card,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class RecordSessionPlayCommandV1:
    """Records one public card play without derived trick metadata."""

    command_version: int = SESSION_COMMAND_VERSION
    kind: str = field(init=False, default="record_play")
    expected_revision: int
    player_id: str
    card: str

    def __post_init__(self) -> None:
        _validate_command_header(self.command_version, self.expected_revision)
        _require_player_identifier(self.player_id, "player_id")
        _require_card(self.card, "card")

    def to_dict(self) -> dict[str, Any]:
        return {
            "command_version": self.command_version,
            "kind": self.kind,
            "expected_revision": self.expected_revision,
            "player_id": self.player_id,
            "card": self.card,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class SetSessionGameEventCommandV1:
    """Records one supported non-terminal event object without adjudication."""

    command_version: int = SESSION_COMMAND_VERSION
    kind: str = field(init=False, default="set_game_event")
    expected_revision: int
    event: Mapping[str, object]

    def __post_init__(self) -> None:
        _validate_command_header(self.command_version, self.expected_revision)
        event = _freeze_json_object(self.event, "event")
        if event.get("kind") not in SESSION_GAME_EVENT_KINDS:
            raise ValueError(
                f"event.kind must be one of {list(SESSION_GAME_EVENT_KINDS)}."
            )
        object.__setattr__(self, "event", event)

    def to_dict(self) -> dict[str, Any]:
        return {
            "command_version": self.command_version,
            "kind": self.kind,
            "expected_revision": self.expected_revision,
            "event": _thaw_json_value(self.event),
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class SetSessionGameEndCommandV1:
    """Records one supported end reason and optional terminal fact object."""

    command_version: int = SESSION_COMMAND_VERSION
    kind: str = field(init=False, default="set_game_end")
    expected_revision: int
    game_end_reason: str
    game_end: Mapping[str, object] | None

    def __post_init__(self) -> None:
        _validate_command_header(self.command_version, self.expected_revision)
        if self.game_end_reason not in SESSION_GAME_END_REASONS:
            raise ValueError(
                f"game_end_reason must be one of {list(SESSION_GAME_END_REASONS)}."
            )
        if self.game_end_reason == HISTORICAL_NORMAL_COMPLETION:
            if self.game_end is not None:
                raise ValueError("normal_completion requires game_end to be null.")
            return
        if self.game_end is None:
            raise ValueError("A terminal game_end_reason requires a game_end object.")
        object.__setattr__(self, "game_end", _freeze_json_object(self.game_end, "game_end"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "command_version": self.command_version,
            "kind": self.kind,
            "expected_revision": self.expected_revision,
            "game_end_reason": self.game_end_reason,
            "game_end": (
                None if self.game_end is None else _thaw_json_value(self.game_end)
            ),
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class PromoteSessionToRetrospectiveCommandV1:
    """Explicitly promotes one Live Session without adding private facts."""

    command_version: int = SESSION_COMMAND_VERSION
    kind: str = field(init=False, default="promote_to_retrospective")
    expected_revision: int

    def __post_init__(self) -> None:
        _validate_command_header(self.command_version, self.expected_revision)

    def to_dict(self) -> dict[str, Any]:
        return {
            "command_version": self.command_version,
            "kind": self.kind,
            "expected_revision": self.expected_revision,
        }


type SessionCommandV1 = (
    SetSessionGameMetadataCommandV1
    | RecordSessionDealtCardCommandV1
    | SetSessionDeclarerCommandV1
    | SetSessionDeclarationCommandV1
    | RecordSessionDiscardCommandV1
    | RecordSessionPlayCommandV1
    | SetSessionGameEventCommandV1
    | SetSessionGameEndCommandV1
    | PromoteSessionToRetrospectiveCommandV1
)

SESSION_COMMAND_TYPES = (
    SetSessionGameMetadataCommandV1,
    RecordSessionDealtCardCommandV1,
    SetSessionDeclarerCommandV1,
    SetSessionDeclarationCommandV1,
    RecordSessionDiscardCommandV1,
    RecordSessionPlayCommandV1,
    SetSessionGameEventCommandV1,
    SetSessionGameEndCommandV1,
    PromoteSessionToRetrospectiveCommandV1,
)


def is_session_command_v1(value: object) -> bool:
    """Returns whether a value is exactly one closed version-1 Command member."""
    return type(value) in SESSION_COMMAND_TYPES


def serialize_session_command_v1(command: SessionCommandV1) -> dict[str, Any]:
    """Returns one deterministic fresh Command representation."""
    if not is_session_command_v1(command):
        raise ValueError("command must be one SessionCommandV1 member.")
    return command.to_dict()
