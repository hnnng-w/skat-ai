from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from skatmind.historical_game import HISTORICAL_SEATS
from skatmind.session_commands import (
    PromoteSessionToRetrospectiveCommandV1,
    RecordSessionDealtCardCommandV1,
    RecordSessionPlayCommandV1,
    SessionCommandV1,
    SetSessionDeclarerCommandV1,
    SetSessionPublicHandCommandV1,
    is_session_command_v1,
    serialize_session_command_v1,
)

if TYPE_CHECKING:
    from skatmind.session_validation import SessionValidationResultV1

SESSION_CONTRACT_VERSION = 1

SESSION_CAPTURE_MODES = ("live", "retrospective")
SESSION_PHASES = (
    "setup",
    "deal",
    "declaration",
    "skat_and_discard",
    "play",
    "ended",
)

SESSION_STATE_POLICY = "command_log_authoritative"
SESSION_REVISION_POLICY = "linear_append_only"
SESSION_REJECTED_COMMAND_POLICY = "not_recorded"
SESSION_MODE_TRANSITION_POLICY = "live_to_retrospective_only"
SESSION_IDENTIFIER_POLICY = "caller_supplied"
SESSION_TIME_POLICY = "caller_supplied_or_null"


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


def _require_ordered_values(value: object, field_name: str) -> tuple[object, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        raise ValueError(f"{field_name} must be an ordered array.")
    return tuple(value)


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionPlayerV1:
    """One stable Session Player identity without hand or game state."""

    player_id: str
    player_label: str | None
    seat: str

    def __post_init__(self) -> None:
        _require_player_identifier(self.player_id, "player_id")
        if self.player_label is not None:
            _require_identifier(self.player_label, "player_label")
        if self.seat not in HISTORICAL_SEATS:
            raise ValueError(f"seat must be one of {list(HISTORICAL_SEATS)}.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "player_label": self.player_label,
            "seat": self.seat,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionCommandRecordV1:
    """One accepted Command at its resulting positive Session revision."""

    revision: int
    command: SessionCommandV1

    def __post_init__(self) -> None:
        if isinstance(self.revision, bool) or not isinstance(self.revision, int):
            raise ValueError("revision must be a positive integer.")
        if self.revision <= 0:
            raise ValueError("revision must be a positive integer.")
        if not is_session_command_v1(self.command):
            raise ValueError("command must be one SessionCommandV1 member.")
        if self.command.expected_revision != self.revision - 1:
            raise ValueError(
                "command.expected_revision must equal the prior accepted revision."
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "revision": self.revision,
            "command": serialize_session_command_v1(self.command),
        }


def _canonicalize_players(value: object) -> tuple[SessionPlayerV1, ...]:
    players = _require_ordered_values(value, "players")
    if len(players) != 3:
        raise ValueError("players must contain exactly three Session Players.")
    if any(not isinstance(player, SessionPlayerV1) for player in players):
        raise ValueError("players must contain only SessionPlayerV1 values.")
    player_ids = tuple(player.player_id for player in players)
    if len(player_ids) != len(set(player_ids)):
        raise ValueError("Session Player IDs must be unique.")
    seats = tuple(player.seat for player in players)
    if len(seats) != len(set(seats)) or set(seats) != set(HISTORICAL_SEATS):
        raise ValueError(
            "players must contain exactly one forehand, middlehand, and rearhand."
        )
    player_by_seat = {player.seat: player for player in players}
    return tuple(player_by_seat[seat] for seat in HISTORICAL_SEATS)


def _canonicalize_command_log(value: object) -> tuple[SessionCommandRecordV1, ...]:
    records = _require_ordered_values(value, "command_log")
    if any(not isinstance(record, SessionCommandRecordV1) for record in records):
        raise ValueError("command_log must contain only SessionCommandRecordV1 values.")
    for expected_revision, record in enumerate(records, start=1):
        if record.revision != expected_revision:
            raise ValueError(
                "command_log revisions must be contiguous and begin at revision 1."
            )
    return records


def _validate_log_player_references(
    command_log: tuple[SessionCommandRecordV1, ...],
    *,
    player_ids: set[str],
    initial_capture_mode: str,
    local_player_id: str | None,
) -> int:
    promotion_count = 0
    promoted = False
    for record in command_log:
        command = record.command
        if isinstance(command, RecordSessionDealtCardCommandV1):
            if command.destination == "player_hand":
                if command.player_id not in player_ids:
                    raise ValueError(
                        "Player-hand Commands must reference a declared Session Player."
                    )
                if (
                    initial_capture_mode == "live"
                    and not promoted
                    and command.player_id != local_player_id
                ):
                    raise ValueError(
                        "Before promotion, a Live Session may record only the local "
                        "Player's concrete initial hand."
                    )
        elif isinstance(command, SetSessionDeclarerCommandV1):
            if command.declarer_player_id not in player_ids:
                raise ValueError(
                    "declarer_player_id must reference a declared Session Player."
                )
        elif isinstance(command, RecordSessionPlayCommandV1):
            if command.player_id not in player_ids:
                raise ValueError("Play Commands must reference a declared Session Player.")
        elif isinstance(command, SetSessionPublicHandCommandV1):
            if command.player_id not in player_ids:
                raise ValueError(
                    "Public-hand Commands must reference a declared Session Player."
                )
        elif isinstance(command, PromoteSessionToRetrospectiveCommandV1):
            promotion_count += 1
            promoted = True
    return promotion_count


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionStateV1:
    """Immutable Session identity plus its authoritative accepted Command Log."""

    session_contract_version: int = SESSION_CONTRACT_VERSION
    session_id: str
    initial_capture_mode: str
    capture_mode: str
    revision: int
    phase: str
    players: tuple[SessionPlayerV1, ...]
    local_player_id: str | None
    command_log: tuple[SessionCommandRecordV1, ...]
    validation: SessionValidationResultV1

    def __post_init__(self) -> None:
        if (
            type(self.session_contract_version) is not int
            or self.session_contract_version != SESSION_CONTRACT_VERSION
        ):
            raise ValueError(
                f"session_contract_version must equal {SESSION_CONTRACT_VERSION}."
            )
        _require_identifier(self.session_id, "session_id")
        if self.initial_capture_mode not in SESSION_CAPTURE_MODES:
            raise ValueError(
                f"initial_capture_mode must be one of {list(SESSION_CAPTURE_MODES)}."
            )
        if self.capture_mode not in SESSION_CAPTURE_MODES:
            raise ValueError(f"capture_mode must be one of {list(SESSION_CAPTURE_MODES)}.")
        _require_non_negative_integer(self.revision, "revision")
        if self.phase not in SESSION_PHASES:
            raise ValueError(f"phase must be one of {list(SESSION_PHASES)}.")

        players = _canonicalize_players(self.players)
        player_ids = {player.player_id for player in players}
        if self.local_player_id is not None:
            _require_player_identifier(self.local_player_id, "local_player_id")
            if self.local_player_id not in player_ids:
                raise ValueError("local_player_id must reference a declared Session Player.")
        if self.initial_capture_mode == "live" and self.local_player_id is None:
            raise ValueError("An initially Live Session requires local_player_id.")

        command_log = _canonicalize_command_log(self.command_log)
        if self.revision != len(command_log):
            raise ValueError("revision must equal the accepted command_log length.")
        promotion_count = _validate_log_player_references(
            command_log,
            player_ids=player_ids,
            initial_capture_mode=self.initial_capture_mode,
            local_player_id=self.local_player_id,
        )
        if promotion_count > 1:
            raise ValueError("A Session may contain at most one promotion Command.")
        if self.initial_capture_mode == "retrospective":
            if promotion_count:
                raise ValueError(
                    "An initially Retrospective Session cannot contain a promotion Command."
                )
            if self.capture_mode != "retrospective":
                raise ValueError(
                    "An initially Retrospective Session must remain retrospective."
                )
        else:
            required_mode = "retrospective" if promotion_count == 1 else "live"
            if self.capture_mode != required_mode:
                raise ValueError(
                    "capture_mode must match the accepted Live-to-Retrospective "
                    "promotion history."
                )

        from skatmind.session_validation import SessionValidationResultV1

        if not isinstance(self.validation, SessionValidationResultV1):
            raise ValueError("validation must be a SessionValidationResultV1.")
        if self.validation.revision != self.revision:
            raise ValueError("validation revision must match the Session revision.")
        if self.validation.phase != self.phase:
            raise ValueError("validation phase must match the Session phase.")

        object.__setattr__(self, "players", players)
        object.__setattr__(self, "command_log", command_log)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_contract_version": self.session_contract_version,
            "session_id": self.session_id,
            "initial_capture_mode": self.initial_capture_mode,
            "capture_mode": self.capture_mode,
            "revision": self.revision,
            "phase": self.phase,
            "players": [player.to_dict() for player in self.players],
            "local_player_id": self.local_player_id,
            "command_log": [record.to_dict() for record in self.command_log],
            "validation": self.validation.to_dict(),
        }
