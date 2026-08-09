from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from skat_ai.deck import get_full_deck
from skat_ai.game_declaration import (
    GameDeclaration,
    build_serializable_game_declaration,
)
from skat_ai.historical_declarer_card_exposure_continuation import (
    HistoricalDeclarerCardExposureContinuationEvent,
)
from skat_ai.historical_defender_open_play_continuation import (
    HistoricalDefenderOpenPlayContinuationEvent,
)
from skat_ai.historical_game import HISTORICAL_SEATS
from skat_ai.historical_game_end import (
    HistoricalDeclarerCardExposure,
    HistoricalDeclarerConcession,
    HistoricalDefenderConcession,
    HistoricalDefenderOpenPlay,
    HistoricalGameEnd,
    HistoricalOpenCardThrow,
    build_serializable_historical_game_end,
)
from skat_ai.historical_game_event import (
    HistoricalGameEvent,
    build_serializable_historical_game_event,
)
from skat_ai.historical_play_prefix import (
    HistoricalDerivedCompletedTrick,
    HistoricalIncompleteTrick,
    build_serializable_derived_trick,
    build_serializable_incomplete_trick,
)
from skat_ai.public_hand_constraint import canonicalize_cards
from skat_ai.session_contracts import (
    SESSION_CAPTURE_MODES,
    SESSION_PHASES,
    SessionPlayerV1,
)

SESSION_PROJECTION_VERSION = 1

type SessionProjectedHandV1 = tuple[str, tuple[str, ...]]
type SessionProjectedPlayV1 = tuple[str, str]

_GAME_EVENT_TYPES = (
    HistoricalDefenderOpenPlayContinuationEvent,
    HistoricalDeclarerCardExposureContinuationEvent,
)
_GAME_END_TYPES = (
    HistoricalDeclarerConcession,
    HistoricalDefenderConcession,
    HistoricalDeclarerCardExposure,
    HistoricalDefenderOpenPlay,
    HistoricalOpenCardThrow,
)


def _require_identifier(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{field_name} must be a non-empty, non-padded string.")
    return value


def _canonicalize_players(value: object) -> tuple[SessionPlayerV1, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        raise ValueError("players must be an ordered array.")
    if len(value) != 3 or any(not isinstance(player, SessionPlayerV1) for player in value):
        raise ValueError("players must contain exactly three SessionPlayerV1 values.")
    player_ids = tuple(player.player_id for player in value)
    seats = tuple(player.seat for player in value)
    if len(player_ids) != len(set(player_ids)):
        raise ValueError("Session Player IDs must be unique.")
    if len(seats) != len(set(seats)) or set(seats) != set(HISTORICAL_SEATS):
        raise ValueError("players must contain exactly one forehand, middlehand, and rearhand.")
    player_by_seat = {player.seat: player for player in value}
    return tuple(player_by_seat[seat] for seat in HISTORICAL_SEATS)


def _canonicalize_hands(
    value: object,
    *,
    field_name: str,
    player_ids: tuple[str, ...],
) -> tuple[SessionProjectedHandV1, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        raise ValueError(f"{field_name} must be an ordered array.")
    hands_by_player: dict[str, tuple[str, ...]] = {}
    for item in value:
        if (
            not isinstance(item, (list, tuple))
            or len(item) != 2
            or not isinstance(item[0], str)
            or isinstance(item[1], (str, bytes))
            or not isinstance(item[1], (list, tuple))
        ):
            raise ValueError(f"{field_name} must contain Player ID and Card-array pairs.")
        player_id = item[0]
        if player_id not in player_ids:
            raise ValueError(f"{field_name} references an unknown Session Player.")
        if player_id in hands_by_player:
            raise ValueError(f"{field_name} must contain each Player at most once.")
        cards = tuple(item[1])
        valid_cards = set(get_full_deck())
        if any(not isinstance(card, str) or card not in valid_cards for card in cards):
            raise ValueError(f"{field_name} contains an invalid Card.")
        if len(cards) != len(set(cards)):
            raise ValueError(f"{field_name} contains duplicate Cards for one Player.")
        hands_by_player[player_id] = canonicalize_cards(cards)
    all_cards = [card for cards in hands_by_player.values() for card in cards]
    if len(all_cards) != len(set(all_cards)):
        raise ValueError(f"{field_name} assigns one Card to multiple Players.")
    return tuple(
        (player_id, hands_by_player[player_id])
        for player_id in player_ids
        if player_id in hands_by_player
    )


def _canonicalize_cards(value: object, field_name: str) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        raise ValueError(f"{field_name} must be an ordered Card array.")
    cards = tuple(value)
    valid_cards = set(get_full_deck())
    if any(not isinstance(card, str) or card not in valid_cards for card in cards):
        raise ValueError(f"{field_name} contains an invalid Card.")
    if len(cards) != len(set(cards)):
        raise ValueError(f"{field_name} contains duplicate Cards.")
    return canonicalize_cards(cards)


def _canonicalize_plays(
    value: object,
    *,
    player_ids: tuple[str, ...],
) -> tuple[SessionProjectedPlayV1, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        raise ValueError("plays must be an ordered array.")
    plays = []
    for item in value:
        if (
            not isinstance(item, (list, tuple))
            or len(item) != 2
            or item[0] not in player_ids
            or not isinstance(item[1], str)
            or item[1] not in get_full_deck()
        ):
            raise ValueError("plays must contain valid Player ID and Card pairs.")
        plays.append((item[0], item[1]))
    cards = tuple(card for _, card in plays)
    if len(cards) != len(set(cards)):
        raise ValueError("plays must not contain repeated Cards.")
    return tuple(plays)


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionProjectionV1:
    """Immutable accepted-fact projection derived from one Session Command Log."""

    session_projection_version: int = SESSION_PROJECTION_VERSION
    session_id: str
    initial_capture_mode: str
    capture_mode: str
    phase: str
    players: tuple[SessionPlayerV1, ...]
    local_player_id: str | None
    game_id: str | None
    played_at: str | None
    initial_known_hands: tuple[SessionProjectedHandV1, ...]
    remaining_known_hands: tuple[SessionProjectedHandV1, ...]
    known_skat: tuple[str, ...]
    declarer_player_id: str | None
    declaration: GameDeclaration | None
    discarded_cards: tuple[str, ...]
    plays: tuple[SessionProjectedPlayV1, ...]
    completed_tricks: tuple[HistoricalDerivedCompletedTrick, ...]
    incomplete_trick: HistoricalIncompleteTrick | None
    next_player_id: str | None
    continuation_event: HistoricalGameEvent | None
    exact_public_hands: tuple[SessionProjectedHandV1, ...]
    declared_ouvert_public_hand_set: bool
    game_end_reason: str | None
    game_end: HistoricalGameEnd | None
    played_card_count: int

    def __post_init__(self) -> None:
        if (
            type(self.session_projection_version) is not int
            or self.session_projection_version != SESSION_PROJECTION_VERSION
        ):
            raise ValueError(f"session_projection_version must equal {SESSION_PROJECTION_VERSION}.")
        _require_identifier(self.session_id, "session_id")
        if self.initial_capture_mode not in SESSION_CAPTURE_MODES:
            raise ValueError(f"initial_capture_mode must be one of {list(SESSION_CAPTURE_MODES)}.")
        if self.capture_mode not in SESSION_CAPTURE_MODES:
            raise ValueError(f"capture_mode must be one of {list(SESSION_CAPTURE_MODES)}.")
        if self.phase not in SESSION_PHASES:
            raise ValueError(f"phase must be one of {list(SESSION_PHASES)}.")

        players = _canonicalize_players(self.players)
        player_ids = tuple(player.player_id for player in players)
        if self.local_player_id is not None and self.local_player_id not in player_ids:
            raise ValueError("local_player_id must reference a declared Session Player.")
        if self.initial_capture_mode == "live" and self.local_player_id is None:
            raise ValueError("An initially Live Session requires local_player_id.")
        if self.game_id is not None:
            _require_identifier(self.game_id, "game_id")
        if self.played_at is not None:
            _require_identifier(self.played_at, "played_at")
        if self.declarer_player_id is not None and self.declarer_player_id not in player_ids:
            raise ValueError("declarer_player_id must reference a Session Player.")
        if self.declaration is not None and not isinstance(self.declaration, GameDeclaration):
            raise ValueError("declaration must be a GameDeclaration or None.")

        initial_known_hands = _canonicalize_hands(
            self.initial_known_hands,
            field_name="initial_known_hands",
            player_ids=player_ids,
        )
        remaining_known_hands = _canonicalize_hands(
            self.remaining_known_hands,
            field_name="remaining_known_hands",
            player_ids=player_ids,
        )
        exact_public_hands = _canonicalize_hands(
            self.exact_public_hands,
            field_name="exact_public_hands",
            player_ids=player_ids,
        )
        if not isinstance(self.declared_ouvert_public_hand_set, bool):
            raise ValueError("declared_ouvert_public_hand_set must be a boolean.")
        known_skat = _canonicalize_cards(self.known_skat, "known_skat")
        discarded_cards = _canonicalize_cards(self.discarded_cards, "discarded_cards")
        plays = _canonicalize_plays(self.plays, player_ids=player_ids)
        if any(
            not isinstance(trick, HistoricalDerivedCompletedTrick)
            for trick in self.completed_tricks
        ):
            raise ValueError(
                "completed_tricks must contain HistoricalDerivedCompletedTrick values."
            )
        if self.incomplete_trick is not None and not isinstance(
            self.incomplete_trick, HistoricalIncompleteTrick
        ):
            raise ValueError("incomplete_trick must be a HistoricalIncompleteTrick or None.")
        if self.next_player_id is not None and self.next_player_id not in player_ids:
            raise ValueError("next_player_id must reference a Session Player or be None.")
        if self.continuation_event is not None and not isinstance(
            self.continuation_event, _GAME_EVENT_TYPES
        ):
            raise ValueError("continuation_event must be a supported event or None.")
        if self.game_end is not None and not isinstance(self.game_end, _GAME_END_TYPES):
            raise ValueError("game_end must be a supported Historical Game End or None.")
        if (
            isinstance(self.played_card_count, bool)
            or not isinstance(self.played_card_count, int)
            or self.played_card_count != len(plays)
        ):
            raise ValueError("played_card_count must equal the chronological Play count.")

        object.__setattr__(self, "players", players)
        object.__setattr__(self, "initial_known_hands", initial_known_hands)
        object.__setattr__(self, "remaining_known_hands", remaining_known_hands)
        object.__setattr__(self, "known_skat", known_skat)
        object.__setattr__(self, "discarded_cards", discarded_cards)
        object.__setattr__(self, "plays", plays)
        object.__setattr__(self, "completed_tricks", tuple(self.completed_tricks))
        object.__setattr__(self, "exact_public_hands", exact_public_hands)

    @property
    def player_ids(self) -> tuple[str, ...]:
        return tuple(player.player_id for player in self.players)

    def initial_hand_for(self, player_id: str) -> tuple[str, ...] | None:
        return next(
            (
                cards
                for candidate_id, cards in self.initial_known_hands
                if candidate_id == player_id
            ),
            None,
        )

    def remaining_hand_for(self, player_id: str) -> tuple[str, ...] | None:
        return next(
            (
                cards
                for candidate_id, cards in self.remaining_known_hands
                if candidate_id == player_id
            ),
            None,
        )

    def public_hand_for(self, player_id: str) -> tuple[str, ...] | None:
        return next(
            (cards for candidate_id, cards in self.exact_public_hands if candidate_id == player_id),
            None,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_projection_version": self.session_projection_version,
            "session_id": self.session_id,
            "initial_capture_mode": self.initial_capture_mode,
            "capture_mode": self.capture_mode,
            "phase": self.phase,
            "players": [player.to_dict() for player in self.players],
            "local_player_id": self.local_player_id,
            "game_id": self.game_id,
            "played_at": self.played_at,
            "initial_known_hands": [
                {"player_id": player_id, "cards": list(cards)}
                for player_id, cards in self.initial_known_hands
            ],
            "remaining_known_hands": [
                {"player_id": player_id, "cards": list(cards)}
                for player_id, cards in self.remaining_known_hands
            ],
            "known_skat": list(self.known_skat),
            "declarer_player_id": self.declarer_player_id,
            "declaration": (
                None
                if self.declaration is None
                else build_serializable_game_declaration(self.declaration)
            ),
            "discarded_cards": list(self.discarded_cards),
            "plays": [{"player_id": player_id, "card": card} for player_id, card in self.plays],
            "completed_tricks": [
                build_serializable_derived_trick(trick) for trick in self.completed_tricks
            ],
            "incomplete_trick": (
                None
                if self.incomplete_trick is None
                else build_serializable_incomplete_trick(self.incomplete_trick)
            ),
            "next_player_id": self.next_player_id,
            "continuation_event": (
                None
                if self.continuation_event is None
                else build_serializable_historical_game_event(self.continuation_event)
            ),
            "exact_public_hands": [
                {"player_id": player_id, "cards": list(cards)}
                for player_id, cards in self.exact_public_hands
            ],
            "declared_ouvert_public_hand_set": self.declared_ouvert_public_hand_set,
            "game_end_reason": self.game_end_reason,
            "game_end": (
                None
                if self.game_end is None
                else build_serializable_historical_game_end(self.game_end)
            ),
            "played_card_count": self.played_card_count,
        }


def create_empty_session_projection_v1(
    *,
    session_id: str,
    players: tuple[SessionPlayerV1, ...] | list[SessionPlayerV1],
    capture_mode: str,
    local_player_id: str | None = None,
) -> SessionProjectionV1:
    """Creates the canonical empty accepted-fact projection for revision zero."""
    return SessionProjectionV1(
        session_id=session_id,
        initial_capture_mode=capture_mode,
        capture_mode=capture_mode,
        phase="setup",
        players=tuple(players),
        local_player_id=local_player_id,
        game_id=None,
        played_at=None,
        initial_known_hands=(),
        remaining_known_hands=(),
        known_skat=(),
        declarer_player_id=None,
        declaration=None,
        discarded_cards=(),
        plays=(),
        completed_tricks=(),
        incomplete_trick=None,
        next_player_id=None,
        continuation_event=None,
        exact_public_hands=(),
        declared_ouvert_public_hand_set=False,
        game_end_reason=None,
        game_end=None,
        played_card_count=0,
    )
