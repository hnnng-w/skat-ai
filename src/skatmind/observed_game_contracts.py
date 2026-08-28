from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from skatmind.deck import get_full_deck
from skatmind.game_declaration import (
    GameDeclaration,
    build_serializable_game_declaration,
)
from skatmind.historical_game import HISTORICAL_SEATS
from skatmind.match_capture_contracts import MatchCaptureDefinitionV1
from skatmind.match_source_metadata import MediaTimecodeV1
from skatmind.observed_game_commentary import (
    ObservedDecisionCommentaryV1,
    ObservedDecisionResponseLinkV1,
    canonicalize_observed_annotations_v1,
)
from skatmind.observed_game_trace import (
    ObservedGameTraceSummaryV1,
    ObservedPlayV1,
    _require_version,
    canonicalize_observed_cards_v1,
    copy_observed_timecode_v1,
    validate_observed_game_trace_v1,
    validate_observed_player_id_v1,
    validate_observed_timecode_containment_v1,
)
from skatmind.performance_rating import validate_stable_list_entry_identifier

OBSERVED_GAME_CONTRACT_VERSION = 1
OBSERVED_GAME_FACT_POLICY = "caller_observed_without_hidden_completion"

_FULL_DECK = tuple(get_full_deck())


@dataclass(frozen=True, slots=True, kw_only=True)
class ObservedGamePlayerV1:
    """One stable Match Player in one observed Game's historical seat."""

    player_id: str
    seat: str

    def __post_init__(self) -> None:
        validate_observed_player_id_v1(self.player_id, "player_id")
        if self.seat not in HISTORICAL_SEATS:
            raise ValueError(f"seat must be one of {list(HISTORICAL_SEATS)}.")

    def to_dict(self) -> dict[str, str]:
        return {"player_id": self.player_id, "seat": self.seat}


def _copy_game_player(value: ObservedGamePlayerV1) -> ObservedGamePlayerV1:
    if not isinstance(value, ObservedGamePlayerV1):
        raise ValueError("players must contain only ObservedGamePlayerV1 values.")
    return ObservedGamePlayerV1(player_id=value.player_id, seat=value.seat)


def _copy_declaration(value: GameDeclaration | None) -> GameDeclaration | None:
    if value is None:
        return None
    if not isinstance(value, GameDeclaration):
        raise ValueError("declaration must be null or GameDeclaration.")
    return GameDeclaration(
        game_type=value.game_type,
        hand_game=value.hand_game,
        ouvert=value.ouvert,
        schneider_announced=value.schneider_announced,
        schwarz_announced=value.schwarz_announced,
        matadors=value.matadors,
        bid_value=value.bid_value,
    )


def _optional_card_set(
    value: object,
    field_name: str,
    *,
    allowed_counts: frozenset[int],
) -> tuple[str, ...] | None:
    if value is None:
        return None
    return canonicalize_observed_cards_v1(
        value,
        field_name,
        allowed_counts=allowed_counts,
    )


def _build_game_players(
    match_definition: MatchCaptureDefinitionV1,
    seat_order_player_ids: Sequence[str],
) -> tuple[ObservedGamePlayerV1, ...]:
    if isinstance(seat_order_player_ids, (str, bytes)) or not isinstance(
        seat_order_player_ids, (list, tuple)
    ):
        raise ValueError("seat_order_player_ids must be an ordered array.")
    if len(seat_order_player_ids) != 3:
        raise ValueError("seat_order_player_ids must contain exactly three Players.")
    for index, player_id in enumerate(seat_order_player_ids):
        validate_observed_player_id_v1(player_id, f"seat_order_player_ids[{index}]")
    if len(seat_order_player_ids) != len(set(seat_order_player_ids)):
        raise ValueError("seat_order_player_ids must contain unique Player IDs.")
    match_player_ids = {participant.player_id for participant in match_definition.participants}
    if set(seat_order_player_ids) != match_player_ids:
        raise ValueError(
            "seat_order_player_ids must contain exactly the Match participant Player IDs."
        )
    return tuple(
        ObservedGamePlayerV1(player_id=player_id, seat=seat)
        for seat, player_id in zip(HISTORICAL_SEATS, seat_order_player_ids, strict=True)
    )


def _build_perspective_playable_hand(
    *,
    perspective_player_id: str,
    perspective_initial_hand: tuple[str, ...] | None,
    declarer_player_id: str | None,
    declaration: GameDeclaration | None,
    original_skat: tuple[str, ...] | None,
    discarded_cards: tuple[str, ...] | None,
) -> tuple[str, ...] | None:
    if perspective_initial_hand is None or declaration is None:
        return None
    if perspective_player_id != declarer_player_id or declaration.hand_game:
        return perspective_initial_hand
    if original_skat is None or discarded_cards is None:
        return None
    available = set((*perspective_initial_hand, *original_skat))
    unavailable_discards = set(discarded_cards) - available
    if unavailable_discards:
        raise ValueError(
            "Known non-Hand Declarer Discards must come from the perspective initial "
            "hand or original Skat."
        )
    playable = available - set(discarded_cards)
    if len(playable) != 10:
        raise ValueError("Known non-Hand Declarer evidence must form ten playable Cards.")
    return tuple(card for card in _FULL_DECK if card in playable)


def build_observed_perspective_playable_hand_v1(
    *,
    perspective_player_id: str,
    perspective_initial_hand: tuple[str, ...] | None,
    declarer_player_id: str | None,
    declaration: GameDeclaration | None,
    original_skat: tuple[str, ...] | None,
    discarded_cards: tuple[str, ...] | None,
) -> tuple[str, ...] | None:
    """Exposes the existing exact perspective-hand transformation internally."""
    return _build_perspective_playable_hand(
        perspective_player_id=perspective_player_id,
        perspective_initial_hand=perspective_initial_hand,
        declarer_player_id=declarer_player_id,
        declaration=declaration,
        original_skat=original_skat,
        discarded_cards=discarded_cards,
    )


def _reconcile_complete_cards(
    *,
    trace,
    perspective_player_id: str,
    perspective_initial_hand: tuple[str, ...] | None,
    declarer_player_id: str,
    declaration: GameDeclaration,
    original_skat: tuple[str, ...] | None,
    discarded_cards: tuple[str, ...] | None,
) -> None:
    if not trace.complete_play_trace:
        return
    assert trace.playable_hands is not None
    playable_hands = dict(trace.playable_hands)
    played_cards = {play.card for play in trace.plays}
    unplayed_cards = tuple(card for card in _FULL_DECK if card not in played_cards)
    if len(unplayed_cards) != 2:
        raise ValueError("A complete observed trace must leave exactly two unplayed Cards.")

    if declaration.hand_game:
        if original_skat is not None and original_skat != unplayed_cards:
            raise ValueError("Known Hand-game original Skat must equal the unplayed Cards.")
        if (
            perspective_initial_hand is not None
            and perspective_initial_hand != playable_hands[perspective_player_id]
        ):
            raise ValueError(
                "Known perspective initial hand must equal the complete Hand-game playable hand."
            )
        return

    if discarded_cards is not None and discarded_cards != unplayed_cards:
        raise ValueError("Known non-Hand Discards must equal the unplayed Cards.")
    if original_skat is not None:
        declarer_available = set(playable_hands[declarer_player_id]) | set(unplayed_cards)
        if not set(original_skat) <= declarer_available:
            raise ValueError(
                "Known original Skat conflicts with the complete Declarer playable hand."
            )
    if perspective_initial_hand is None:
        return
    if perspective_player_id != declarer_player_id:
        if perspective_initial_hand != playable_hands[perspective_player_id]:
            raise ValueError(
                "Known Defender perspective hand must equal the reconstructed playable hand."
            )
        return
    if original_skat is not None and discarded_cards is not None:
        original_declarer_hand = (
            set(playable_hands[declarer_player_id]) | set(discarded_cards)
        ) - set(original_skat)
        canonical_initial_hand = tuple(
            card for card in _FULL_DECK if card in original_declarer_hand
        )
        if len(canonical_initial_hand) != 10:
            raise ValueError("Complete non-Hand evidence must reconstruct ten dealt Cards.")
        if perspective_initial_hand != canonical_initial_hand:
            raise ValueError(
                "Known non-Hand Declarer perspective hand conflicts with original Skat, "
                "Discards, and complete Plays."
            )


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class ObservedGameRecordV1:
    """One immutable observed Game linked to an existing Match definition."""

    observed_game_contract_version: int = OBSERVED_GAME_CONTRACT_VERSION
    game_id: str
    match_id: str
    match_position: int
    game_timecode: MediaTimecodeV1 | None
    players: tuple[ObservedGamePlayerV1, ...]
    perspective_player_id: str
    perspective_initial_hand: tuple[str, ...] | None
    declarer_player_id: str | None
    declaration: GameDeclaration | None
    original_skat: tuple[str, ...] | None
    discarded_cards: tuple[str, ...] | None
    plays: tuple[ObservedPlayV1, ...]
    commentaries: tuple[ObservedDecisionCommentaryV1, ...]
    response_links: tuple[ObservedDecisionResponseLinkV1, ...]

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("ObservedGameRecordV1 must be constructed by its focused builder.")

    @classmethod
    def _from_validated(
        cls,
        *,
        game_id: str,
        match_id: str,
        match_position: int,
        game_timecode: MediaTimecodeV1 | None,
        players: tuple[ObservedGamePlayerV1, ...],
        perspective_player_id: str,
        perspective_initial_hand: tuple[str, ...] | None,
        declarer_player_id: str | None,
        declaration: GameDeclaration | None,
        original_skat: tuple[str, ...] | None,
        discarded_cards: tuple[str, ...] | None,
        plays: tuple[ObservedPlayV1, ...],
        commentaries: tuple[ObservedDecisionCommentaryV1, ...],
        response_links: tuple[ObservedDecisionResponseLinkV1, ...],
    ) -> "ObservedGameRecordV1":
        value = object.__new__(cls)
        for field_name, field_value in (
            ("observed_game_contract_version", OBSERVED_GAME_CONTRACT_VERSION),
            ("game_id", game_id),
            ("match_id", match_id),
            ("match_position", match_position),
            ("game_timecode", game_timecode),
            ("players", players),
            ("perspective_player_id", perspective_player_id),
            ("perspective_initial_hand", perspective_initial_hand),
            ("declarer_player_id", declarer_player_id),
            ("declaration", declaration),
            ("original_skat", original_skat),
            ("discarded_cards", discarded_cards),
            ("plays", plays),
            ("commentaries", commentaries),
            ("response_links", response_links),
        ):
            object.__setattr__(value, field_name, field_value)
        value._validate_version()
        return value

    def _validate_version(self) -> None:
        _require_version(
            self.observed_game_contract_version,
            OBSERVED_GAME_CONTRACT_VERSION,
            "observed_game_contract_version",
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "observed_game_contract_version": self.observed_game_contract_version,
            "game_id": self.game_id,
            "match_id": self.match_id,
            "match_position": self.match_position,
            "game_timecode": (None if self.game_timecode is None else self.game_timecode.to_dict()),
            "players": [player.to_dict() for player in self.players],
            "perspective_player_id": self.perspective_player_id,
            "perspective_initial_hand": (
                None
                if self.perspective_initial_hand is None
                else list(self.perspective_initial_hand)
            ),
            "declarer_player_id": self.declarer_player_id,
            "declaration": (
                None
                if self.declaration is None
                else build_serializable_game_declaration(self.declaration)
            ),
            "original_skat": (None if self.original_skat is None else list(self.original_skat)),
            "discarded_cards": (
                None if self.discarded_cards is None else list(self.discarded_cards)
            ),
            "plays": [play.to_dict() for play in self.plays],
            "commentaries": [item.to_dict() for item in self.commentaries],
            "response_links": [item.to_dict() for item in self.response_links],
        }


def _build_observed_game_record_v1(
    match_definition: MatchCaptureDefinitionV1,
    *,
    game_id: str,
    match_position: int,
    game_timecode: MediaTimecodeV1 | None,
    seat_order_player_ids: tuple[str, str, str],
    perspective_initial_hand: tuple[str, ...] | None,
    declarer_player_id: str | None,
    declaration: GameDeclaration | None,
    original_skat: tuple[str, ...] | None,
    discarded_cards: tuple[str, ...] | None,
    plays: tuple[ObservedPlayV1, ...],
    commentaries: tuple[ObservedDecisionCommentaryV1, ...],
    response_links: tuple[ObservedDecisionResponseLinkV1, ...],
    _validated_trace_output: list[ObservedGameTraceSummaryV1] | None = None,
) -> ObservedGameRecordV1:
    """Builds one observed Game and optionally returns its validated trace."""
    if not isinstance(match_definition, MatchCaptureDefinitionV1):
        raise ValueError("match_definition must be MatchCaptureDefinitionV1.")
    validate_stable_list_entry_identifier(game_id, "game_id")
    if (
        type(match_position) is not int
        or not 1 <= match_position <= match_definition.tournament_format.game_count
    ):
        raise ValueError("match_position must be an integer from 1 through the Match game_count.")
    retained_game_timecode = copy_observed_timecode_v1(game_timecode, "game_timecode")
    validate_observed_timecode_containment_v1(
        retained_game_timecode,
        match_definition.source.match_timecode,
        child_name="game_timecode",
        parent_name="Match source match_timecode",
    )
    players = _build_game_players(match_definition, seat_order_player_ids)
    perspective_player_id = match_definition.perspective_player_id

    retained_initial_hand = _optional_card_set(
        perspective_initial_hand,
        "perspective_initial_hand",
        allowed_counts=frozenset({10}),
    )
    retained_original_skat = _optional_card_set(
        original_skat,
        "original_skat",
        allowed_counts=frozenset({2}),
    )
    if (
        retained_initial_hand is not None
        and retained_original_skat is not None
        and set(retained_initial_hand).intersection(retained_original_skat)
    ):
        raise ValueError("perspective_initial_hand and original_skat must be disjoint.")

    retained_declaration = _copy_declaration(declaration)
    if (declarer_player_id is None) != (retained_declaration is None):
        raise ValueError("declarer_player_id and declaration must be both null or both present.")
    player_ids = tuple(player.player_id for player in players)
    if declarer_player_id is not None:
        validate_observed_player_id_v1(declarer_player_id, "declarer_player_id")
        if declarer_player_id not in player_ids:
            raise ValueError("declarer_player_id must reference one exact Game Player.")

    retained_discards = _optional_card_set(
        discarded_cards,
        "discarded_cards",
        allowed_counts=frozenset({0, 2}),
    )
    if retained_declaration is not None and retained_discards is not None:
        if retained_declaration.hand_game and retained_discards:
            raise ValueError("Known Hand games require discarded_cards to be empty.")
        if not retained_declaration.hand_game and len(retained_discards) != 2:
            raise ValueError("Known non-Hand games require exactly two discarded Cards.")
    if (
        retained_initial_hand is not None
        and retained_discards is not None
        and retained_declaration is not None
        and perspective_player_id != declarer_player_id
        and set(retained_initial_hand).intersection(retained_discards)
    ):
        raise ValueError("Known Defender perspective hand cannot contain a discarded Card.")

    perspective_playable_hand = _build_perspective_playable_hand(
        perspective_player_id=perspective_player_id,
        perspective_initial_hand=retained_initial_hand,
        declarer_player_id=declarer_player_id,
        declaration=retained_declaration,
        original_skat=retained_original_skat,
        discarded_cards=retained_discards,
    )
    trace = validate_observed_game_trace_v1(
        plays=plays,
        seat_order_player_ids=player_ids,
        perspective_player_id=perspective_player_id,
        perspective_initial_hand=retained_initial_hand,
        perspective_playable_hand=perspective_playable_hand,
        declarer_player_id=declarer_player_id,
        declaration=retained_declaration,
        original_skat=retained_original_skat,
        discarded_cards=retained_discards,
        game_timecode=retained_game_timecode,
    )
    if trace.complete_play_trace:
        assert declarer_player_id is not None
        assert retained_declaration is not None
        _reconcile_complete_cards(
            trace=trace,
            perspective_player_id=perspective_player_id,
            perspective_initial_hand=retained_initial_hand,
            declarer_player_id=declarer_player_id,
            declaration=retained_declaration,
            original_skat=retained_original_skat,
            discarded_cards=retained_discards,
        )

    canonical_commentaries, canonical_response_links = canonicalize_observed_annotations_v1(
        commentaries=commentaries,
        response_links=response_links,
        plays=trace.plays,
        game_player_ids=player_ids,
        game_timecode=retained_game_timecode,
    )
    if _validated_trace_output is not None:
        _validated_trace_output.append(trace)
    return ObservedGameRecordV1._from_validated(
        game_id=game_id,
        match_id=match_definition.match_id,
        match_position=match_position,
        game_timecode=retained_game_timecode,
        players=tuple(_copy_game_player(player) for player in players),
        perspective_player_id=perspective_player_id,
        perspective_initial_hand=retained_initial_hand,
        declarer_player_id=declarer_player_id,
        declaration=retained_declaration,
        original_skat=retained_original_skat,
        discarded_cards=retained_discards,
        plays=trace.plays,
        commentaries=canonical_commentaries,
        response_links=canonical_response_links,
    )


def build_observed_game_record_v1(
    match_definition: MatchCaptureDefinitionV1,
    *,
    game_id: str,
    match_position: int,
    game_timecode: MediaTimecodeV1 | None,
    seat_order_player_ids: tuple[str, str, str],
    perspective_initial_hand: tuple[str, ...] | None,
    declarer_player_id: str | None,
    declaration: GameDeclaration | None,
    original_skat: tuple[str, ...] | None,
    discarded_cards: tuple[str, ...] | None,
    plays: tuple[ObservedPlayV1, ...],
    commentaries: tuple[ObservedDecisionCommentaryV1, ...],
    response_links: tuple[ObservedDecisionResponseLinkV1, ...],
) -> ObservedGameRecordV1:
    """Builds one evidence-safe observed Game from one exact Match definition."""
    return _build_observed_game_record_v1(
        match_definition,
        game_id=game_id,
        match_position=match_position,
        game_timecode=game_timecode,
        seat_order_player_ids=seat_order_player_ids,
        perspective_initial_hand=perspective_initial_hand,
        declarer_player_id=declarer_player_id,
        declaration=declaration,
        original_skat=original_skat,
        discarded_cards=discarded_cards,
        plays=plays,
        commentaries=commentaries,
        response_links=response_links,
    )
