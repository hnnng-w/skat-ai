from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from skatmind.deck import get_full_deck
from skatmind.game_declaration import GameDeclaration
from skatmind.match_source_metadata import MediaTimecodeV1
from skatmind.performance_rating import validate_stable_list_entry_identifier
from skatmind.rules import get_legal_cards, get_trick_points, get_trick_winner

OBSERVED_PLAY_VERSION = 1
OBSERVED_GAME_TRACE_POLICY = "chronological_public_play_trace"

_RELATIVE_PLAYER_IDS = frozenset({"me", "left", "right"})
_FULL_DECK = tuple(get_full_deck())
_VALID_CARDS = frozenset(_FULL_DECK)
_CARD_ORDER = {card: index for index, card in enumerate(_FULL_DECK)}


def _require_version(value: object, expected: int, field_name: str) -> None:
    if type(value) is not int or value != expected:
        raise ValueError(f"{field_name} must equal {expected}.")


def validate_observed_player_id_v1(value: object, field_name: str) -> None:
    """Validates one stable non-relative observed Match Player identity."""
    validate_stable_list_entry_identifier(value, field_name)
    if value in _RELATIVE_PLAYER_IDS:
        raise ValueError(f"{field_name} must be a stable, non-relative Player ID.")


def canonicalize_observed_cards_v1(
    value: object,
    field_name: str,
    *,
    allowed_counts: frozenset[int],
) -> tuple[str, ...]:
    """Validates one observed Card set and returns canonical deck order."""
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        raise ValueError(f"{field_name} must be an array.")
    if len(value) not in allowed_counts:
        expected = ", ".join(str(count) for count in sorted(allowed_counts))
        raise ValueError(f"{field_name} must contain exactly one of these Card counts: {expected}.")
    invalid_cards = [
        card
        for card in value
        if not isinstance(card, str) or card not in _VALID_CARDS
    ]
    if invalid_cards:
        raise ValueError(f"{field_name} contains invalid Cards: {invalid_cards}.")
    if len(value) != len(set(value)):
        raise ValueError(f"{field_name} contains duplicate Cards.")
    return tuple(sorted(value, key=_CARD_ORDER.__getitem__))


def copy_observed_timecode_v1(
    value: MediaTimecodeV1 | None,
    field_name: str,
) -> MediaTimecodeV1 | None:
    """Returns a validated defensive copy of one optional observation timecode."""
    if value is None:
        return None
    if not isinstance(value, MediaTimecodeV1):
        raise ValueError(f"{field_name} must be null or MediaTimecodeV1.")
    return MediaTimecodeV1(
        media_timecode_version=value.media_timecode_version,
        start_offset_ms=value.start_offset_ms,
        end_offset_ms=value.end_offset_ms,
    )


def validate_observed_timecode_containment_v1(
    child: MediaTimecodeV1 | None,
    parent: MediaTimecodeV1 | None,
    *,
    child_name: str,
    parent_name: str,
) -> None:
    """Validates all known child bounds against all known enclosing bounds."""
    if child is None or parent is None:
        return
    outside = child.start_offset_ms < parent.start_offset_ms
    if parent.end_offset_ms is not None:
        outside = outside or child.start_offset_ms > parent.end_offset_ms
        if child.end_offset_ms is not None:
            outside = outside or child.end_offset_ms > parent.end_offset_ms
    if outside:
        raise ValueError(f"{child_name} must lie within {parent_name}.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ObservedPlayV1:
    """One caller-observed public Play without derived Trick metadata."""

    observed_play_version: int = OBSERVED_PLAY_VERSION
    decision_index: int
    player_id: str
    card: str
    decision_timecode: MediaTimecodeV1 | None

    def __post_init__(self) -> None:
        _require_version(
            self.observed_play_version,
            OBSERVED_PLAY_VERSION,
            "observed_play_version",
        )
        if type(self.decision_index) is not int or self.decision_index <= 0:
            raise ValueError("decision_index must be a positive integer.")
        validate_observed_player_id_v1(self.player_id, "player_id")
        if not isinstance(self.card, str) or self.card not in _VALID_CARDS:
            raise ValueError("card must be one valid Skat Card.")
        object.__setattr__(
            self,
            "decision_timecode",
            copy_observed_timecode_v1(self.decision_timecode, "decision_timecode"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "observed_play_version": self.observed_play_version,
            "decision_index": self.decision_index,
            "player_id": self.player_id,
            "card": self.card,
            "decision_timecode": (
                None
                if self.decision_timecode is None
                else self.decision_timecode.to_dict()
            ),
        }


def copy_observed_play_v1(value: ObservedPlayV1) -> ObservedPlayV1:
    """Returns a validated defensive copy of one observed Play."""
    if not isinstance(value, ObservedPlayV1):
        raise ValueError("plays must contain only ObservedPlayV1 values.")
    return ObservedPlayV1(
        observed_play_version=value.observed_play_version,
        decision_index=value.decision_index,
        player_id=value.player_id,
        card=value.card,
        decision_timecode=value.decision_timecode,
    )


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class ObservedGameTraceSummaryV1:
    """Derived trace facts retained outside the observed source record."""

    plays: tuple[ObservedPlayV1, ...]
    completed_trick_count: int
    current_trick_play_count: int
    winner_player_ids: tuple[str, ...]
    trick_points: tuple[int, ...]
    next_player_id: str
    player_play_counts: tuple[tuple[str, int], ...]
    complete_play_trace: bool
    playable_hands: tuple[tuple[str, tuple[str, ...]], ...] | None

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "ObservedGameTraceSummaryV1 must be constructed by the trace validator."
        )

    @classmethod
    def _from_validated(
        cls,
        *,
        plays: tuple[ObservedPlayV1, ...],
        completed_trick_count: int,
        current_trick_play_count: int,
        winner_player_ids: tuple[str, ...],
        trick_points: tuple[int, ...],
        next_player_id: str,
        player_play_counts: tuple[tuple[str, int], ...],
        complete_play_trace: bool,
        playable_hands: tuple[tuple[str, tuple[str, ...]], ...] | None,
    ) -> "ObservedGameTraceSummaryV1":
        value = object.__new__(cls)
        for field_name, field_value in (
            ("plays", plays),
            ("completed_trick_count", completed_trick_count),
            ("current_trick_play_count", current_trick_play_count),
            ("winner_player_ids", winner_player_ids),
            ("trick_points", trick_points),
            ("next_player_id", next_player_id),
            ("player_play_counts", player_play_counts),
            ("complete_play_trace", complete_play_trace),
            ("playable_hands", playable_hands),
        ):
            object.__setattr__(value, field_name, field_value)
        return value

    def to_dict(self) -> dict[str, Any]:
        return {
            "plays": [play.to_dict() for play in self.plays],
            "completed_trick_count": self.completed_trick_count,
            "current_trick_play_count": self.current_trick_play_count,
            "winner_player_ids": list(self.winner_player_ids),
            "trick_points": list(self.trick_points),
            "next_player_id": self.next_player_id,
            "player_play_counts": [
                {"player_id": player_id, "play_count": play_count}
                for player_id, play_count in self.player_play_counts
            ],
            "complete_play_trace": self.complete_play_trace,
            "playable_hands": (
                None
                if self.playable_hands is None
                else [
                    {"player_id": player_id, "cards": list(cards)}
                    for player_id, cards in self.playable_hands
                ]
            ),
        }


def _player_order_from_leader(
    leader_player_id: str,
    seat_order_player_ids: tuple[str, ...],
) -> tuple[str, ...]:
    leader_index = seat_order_player_ids.index(leader_player_id)
    return tuple(
        seat_order_player_ids[(leader_index + offset) % len(seat_order_player_ids)]
        for offset in range(len(seat_order_player_ids))
    )


def _validate_perspective_replay(
    *,
    plays: tuple[ObservedPlayV1, ...],
    perspective_player_id: str,
    perspective_playable_hand: tuple[str, ...],
    declaration: GameDeclaration,
) -> None:
    remaining_hand = list(perspective_playable_hand)
    current_trick: list[str] = []
    for play in plays:
        if play.player_id == perspective_player_id:
            if play.card not in remaining_hand:
                raise ValueError(
                    f"Observed decision {play.decision_index}: perspective Player does "
                    f"not own remaining Card '{play.card}'."
                )
            legal_cards = get_legal_cards(
                remaining_hand,
                current_trick,
                declaration.game_type,
            )
            if play.card not in legal_cards:
                raise ValueError(
                    f"Observed decision {play.decision_index}: perspective Player "
                    f"illegally plays '{play.card}'; legal Cards are {legal_cards}."
                )
            remaining_hand.remove(play.card)
        current_trick.append(play.card)
        if len(current_trick) == 3:
            current_trick = []


def _validate_complete_replay(
    *,
    plays: tuple[ObservedPlayV1, ...],
    seat_order_player_ids: tuple[str, ...],
    declaration: GameDeclaration,
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    playable_hands = {
        player_id: [play.card for play in plays if play.player_id == player_id]
        for player_id in seat_order_player_ids
    }
    initial_playable_hands = tuple(
        (
            player_id,
            tuple(sorted(playable_hands[player_id], key=_CARD_ORDER.__getitem__)),
        )
        for player_id in seat_order_player_ids
    )
    current_trick: list[str] = []
    for play in plays:
        hand = playable_hands[play.player_id]
        if play.card not in hand:
            raise ValueError(
                f"Observed decision {play.decision_index}: Player '{play.player_id}' "
                f"does not own remaining Card '{play.card}'."
            )
        legal_cards = get_legal_cards(hand, current_trick, declaration.game_type)
        if play.card not in legal_cards:
            raise ValueError(
                f"Observed decision {play.decision_index}: Player '{play.player_id}' "
                f"illegally plays '{play.card}'; legal Cards are {legal_cards}."
            )
        hand.remove(play.card)
        current_trick.append(play.card)
        if len(current_trick) == 3:
            current_trick = []
    if current_trick or any(playable_hands.values()):
        raise ValueError("A complete observed trace must consume ten complete playable hands.")
    return initial_playable_hands


def validate_observed_game_trace_v1(
    *,
    plays: Sequence[ObservedPlayV1],
    seat_order_player_ids: tuple[str, ...],
    perspective_player_id: str,
    perspective_initial_hand: tuple[str, ...] | None,
    perspective_playable_hand: tuple[str, ...] | None,
    declarer_player_id: str | None,
    declaration: GameDeclaration | None,
    original_skat: tuple[str, ...] | None,
    discarded_cards: tuple[str, ...] | None,
    game_timecode: MediaTimecodeV1 | None,
) -> ObservedGameTraceSummaryV1:
    """Validates one bounded public trace without completing unknown ownership."""
    if isinstance(plays, (str, bytes)) or not isinstance(plays, (list, tuple)):
        raise ValueError("plays must be an ordered array.")
    retained_plays = tuple(copy_observed_play_v1(play) for play in plays)
    if len(retained_plays) > 30:
        raise ValueError("plays may contain at most 30 observed Plays.")
    if retained_plays and (declarer_player_id is None or declaration is None):
        raise ValueError("Observed Plays require both Declarer and Declaration facts.")

    player_ids = frozenset(seat_order_player_ids)
    play_counts = {player_id: 0 for player_id in seat_order_player_ids}
    seen_cards: set[str] = set()
    previous_present_timecode: int | None = None
    for expected_index, play in enumerate(retained_plays, start=1):
        if play.decision_index != expected_index:
            raise ValueError(
                "plays must use chronological contiguous one-based decision_index values."
            )
        if play.player_id not in player_ids:
            raise ValueError(
                f"Observed decision {play.decision_index} references an unknown Game Player."
            )
        if play.card in seen_cards:
            raise ValueError(f"Observed Card '{play.card}' is played more than once.")
        seen_cards.add(play.card)
        play_counts[play.player_id] += 1
        if play_counts[play.player_id] > 10:
            raise ValueError("A Game Player may have at most ten observed Plays.")
        validate_observed_timecode_containment_v1(
            play.decision_timecode,
            game_timecode,
            child_name=f"plays[{expected_index - 1}].decision_timecode",
            parent_name="game_timecode",
        )
        if play.decision_timecode is not None:
            start = play.decision_timecode.start_offset_ms
            if previous_present_timecode is not None and start < previous_present_timecode:
                raise ValueError("Present Decision timecodes must be non-decreasing.")
            previous_present_timecode = start

        if discarded_cards is not None and play.card in discarded_cards:
            raise ValueError(f"Discarded Card '{play.card}' cannot appear in Plays.")
        if (
            perspective_initial_hand is not None
            and play.card in perspective_initial_hand
            and play.player_id != perspective_player_id
        ):
            raise ValueError(
                f"Observed Card '{play.card}' belongs to the perspective initial hand."
            )
        if original_skat is not None and play.card in original_skat and declaration is not None:
            if declaration.hand_game:
                raise ValueError(f"Hand-game original Skat Card '{play.card}' cannot be played.")
            if play.player_id != declarer_player_id:
                raise ValueError(
                    f"Original Skat Card '{play.card}' may be played only by the Declarer."
                )

    expected_leader = seat_order_player_ids[0]
    current_trick_cards: list[str] = []
    current_trick_plays: list[ObservedPlayV1] = []
    winner_player_ids: list[str] = []
    trick_points: list[int] = []
    for play in retained_plays:
        expected_order = _player_order_from_leader(expected_leader, seat_order_player_ids)
        expected_player_id = expected_order[len(current_trick_plays)]
        if play.player_id != expected_player_id:
            raise ValueError(
                f"Observed decision {play.decision_index} must be played by "
                f"'{expected_player_id}', got '{play.player_id}'."
            )
        current_trick_plays.append(play)
        current_trick_cards.append(play.card)
        if len(current_trick_plays) == 3:
            assert declaration is not None
            winner_index = get_trick_winner(current_trick_cards, declaration.game_type)
            winner_player_id = current_trick_plays[winner_index].player_id
            winner_player_ids.append(winner_player_id)
            trick_points.append(get_trick_points(current_trick_cards))
            expected_leader = winner_player_id
            current_trick_cards = []
            current_trick_plays = []

    if perspective_playable_hand is not None:
        assert declaration is not None
        _validate_perspective_replay(
            plays=retained_plays,
            perspective_player_id=perspective_player_id,
            perspective_playable_hand=perspective_playable_hand,
            declaration=declaration,
        )

    complete_play_trace = len(retained_plays) == 30
    playable_hands = None
    if complete_play_trace:
        if any(count != 10 for count in play_counts.values()):
            raise ValueError("A complete observed trace requires exactly ten Plays per Player.")
        if len(winner_player_ids) != 10 or current_trick_plays:
            raise ValueError("A complete observed trace requires exactly ten complete Tricks.")
        assert declaration is not None
        playable_hands = _validate_complete_replay(
            plays=retained_plays,
            seat_order_player_ids=seat_order_player_ids,
            declaration=declaration,
        )

    next_player_id = (
        _player_order_from_leader(expected_leader, seat_order_player_ids)[
            len(current_trick_plays)
        ]
        if current_trick_plays
        else expected_leader
    )
    return ObservedGameTraceSummaryV1._from_validated(
        plays=retained_plays,
        completed_trick_count=len(winner_player_ids),
        current_trick_play_count=len(current_trick_plays),
        winner_player_ids=tuple(winner_player_ids),
        trick_points=tuple(trick_points),
        next_player_id=next_player_id,
        player_play_counts=tuple(
            (player_id, play_counts[player_id]) for player_id in seat_order_player_ids
        ),
        complete_play_trace=complete_play_trace,
        playable_hands=playable_hands,
    )
