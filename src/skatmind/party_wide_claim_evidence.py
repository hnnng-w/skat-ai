from dataclasses import dataclass
from typing import Any

from skatmind.deck import get_full_deck
from skatmind.exact_search_state import ExactSearchState, build_exact_search_state
from skatmind.game_declaration import GameDeclaration, build_serializable_game_declaration
from skatmind.game_value import build_game_value_summary
from skatmind.historical_game import HistoricalPlay, HistoricalPlayer, HistoricalTrick
from skatmind.historical_play_prefix import (
    HistoricalDerivedCompletedTrick,
    HistoricalIncompleteTrick,
    HistoricalReplayState,
    build_serializable_derived_trick,
    build_serializable_incomplete_trick,
    replay_historical_play_prefix,
)
from skatmind.historical_player_mapping import (
    FLAT_PLAYERS,
    HISTORICAL_SEATS,
    build_historical_player_mapping,
)
from skatmind.matador_inference import infer_matadors_from_known_ownership
from skatmind.overbid import build_overbid_summary
from skatmind.party_wide_claim_contracts import (
    PartyWideAllRemainingTricksClaimV1,
    _require_stable_player_id,
    validate_party_wide_claim_against_evidence_v1,
)
from skatmind.rules import get_card_points, get_trick_points, get_trick_winner

PARTY_WIDE_CLAIM_EVIDENCE_VERSION = 1
PARTY_WIDE_CLAIM_EXACT_STATE_CONTEXT_VERSION = 1

_FULL_DECK = tuple(get_full_deck())
_FULL_DECK_SET = frozenset(_FULL_DECK)
_CARD_ORDER = {card: index for index, card in enumerate(_FULL_DECK)}


def _require_identifier(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{field_name} must be a non-empty, non-padded string.")
    return value


def _canonicalize_cards(
    cards: object,
    field_name: str,
    *,
    expected_count: int | None = None,
) -> tuple[str, ...]:
    if isinstance(cards, str):
        raise ValueError(f"{field_name} must be a Card collection.")
    try:
        copied = tuple(cards)  # type: ignore[arg-type]
    except TypeError as error:
        raise ValueError(f"{field_name} must be a Card collection.") from error
    if expected_count is not None and len(copied) != expected_count:
        raise ValueError(f"{field_name} must contain exactly {expected_count} Cards.")
    invalid = [card for card in copied if not isinstance(card, str) or card not in _FULL_DECK_SET]
    if invalid:
        raise ValueError(f"{field_name} contains invalid Cards: {invalid}.")
    if len(copied) != len(set(copied)):
        raise ValueError(f"{field_name} contains duplicate Cards.")
    return tuple(sorted(copied, key=_CARD_ORDER.__getitem__))


def _copy_players(players: object, game_id: str) -> tuple[HistoricalPlayer, ...]:
    if isinstance(players, (str, bytes)):
        raise ValueError("players must contain exactly three Historical Players.")
    try:
        supplied = tuple(players)  # type: ignore[arg-type]
    except TypeError as error:
        raise ValueError("players must contain exactly three Historical Players.") from error
    if len(supplied) != 3 or any(not isinstance(player, HistoricalPlayer) for player in supplied):
        raise ValueError("players must contain exactly three Historical Players.")

    copied = []
    for index, player in enumerate(supplied):
        player_id = _require_stable_player_id(
            player.player_id,
            f"Party-wide Claim Evidence '{game_id}' players[{index}].player_id",
        )
        if player.player_label is not None:
            _require_identifier(
                player.player_label,
                f"Party-wide Claim Evidence '{game_id}' players[{index}].player_label",
            )
        if player.seat not in HISTORICAL_SEATS:
            raise ValueError(
                f"Party-wide Claim Evidence '{game_id}' has invalid Historical seat "
                f"'{player.seat}'."
            )
        copied.append(
            HistoricalPlayer(
                player_id=player_id,
                player_label=player.player_label,
                seat=player.seat,
                initial_hand=_canonicalize_cards(
                    player.initial_hand,
                    f"Party-wide Claim Evidence '{game_id}' initial hand for '{player_id}'",
                    expected_count=10,
                ),
            )
        )

    player_ids = tuple(player.player_id for player in copied)
    if len(set(player_ids)) != 3:
        raise ValueError("Party-wide Claim Evidence Player IDs must be unique.")
    seats = tuple(player.seat for player in copied)
    if set(seats) != set(HISTORICAL_SEATS):
        raise ValueError(
            "Party-wide Claim Evidence must contain exactly one forehand, middlehand, and rearhand."
        )
    return tuple(
        next(player for player in copied if player.seat == seat) for seat in HISTORICAL_SEATS
    )


def _copy_declaration(
    declaration: object,
    *,
    players: tuple[HistoricalPlayer, ...],
    skat: tuple[str, ...],
    declarer_player_id: str,
) -> GameDeclaration:
    if not isinstance(declaration, GameDeclaration):
        raise ValueError("declaration must be a valid GameDeclaration.")
    declarer = next(player for player in players if player.player_id == declarer_player_id)
    defender_cards = tuple(
        card
        for player in players
        if player.player_id != declarer_player_id
        for card in player.initial_hand
    )
    inferred_matadors = infer_matadors_from_known_ownership(
        game_type=declaration.game_type,
        declarer_owned_cards=[*declarer.initial_hand, *skat],
        non_declarer_owned_cards=list(defender_cards),
    )
    if declaration.game_type != "null":
        if inferred_matadors is None:
            raise ValueError("Matadors could not be inferred from the complete Claim Deal.")
        if declaration.matadors is not None and declaration.matadors != inferred_matadors:
            raise ValueError("declaration.matadors contradicts complete Claim Deal ownership.")
    elif declaration.matadors is not None:
        raise ValueError("Null Claim Evidence cannot contain Matadors.")

    copied = GameDeclaration(
        game_type=declaration.game_type,
        hand_game=declaration.hand_game,
        ouvert=declaration.ouvert,
        schneider_announced=declaration.schneider_announced,
        schwarz_announced=declaration.schwarz_announced,
        matadors=inferred_matadors,
        bid_value=declaration.bid_value,
    )
    game_value_summary = build_game_value_summary(copied)
    if game_value_summary["game_value"] is None:
        raise ValueError("Claim Evidence requires a complete supported game value.")
    build_overbid_summary(game_value_summary, copied.bid_value)
    return copied


def _copy_tricks(
    tricks: object,
    *,
    game_id: str,
    participant_ids: frozenset[str],
) -> tuple[HistoricalTrick, ...]:
    if isinstance(tricks, (str, bytes)):
        raise ValueError("tricks must be a chronological Historical Trick collection.")
    try:
        supplied = tuple(tricks)  # type: ignore[arg-type]
    except TypeError as error:
        raise ValueError("tricks must be a chronological Historical Trick collection.") from error
    if len(supplied) > 10:
        raise ValueError("Party-wide Claim Evidence may contain at most ten Tricks.")

    copied = []
    for index, trick in enumerate(supplied):
        if not isinstance(trick, HistoricalTrick):
            raise ValueError("tricks must contain only HistoricalTrick values.")
        expected_number = index + 1
        if (
            isinstance(trick.trick_number, bool)
            or not isinstance(trick.trick_number, int)
            or trick.trick_number != expected_number
        ):
            raise ValueError(f"Party-wide Claim Evidence trick_number must be {expected_number}.")
        leader = _require_stable_player_id(
            trick.leader_player_id,
            f"Party-wide Claim Evidence '{game_id}' trick {expected_number} leader",
        )
        if leader not in participant_ids:
            raise ValueError("Historical Trick leader must identify one Evidence Player.")
        if not isinstance(trick.plays, tuple) or not 1 <= len(trick.plays) <= 3:
            raise ValueError("Each supplied Historical Trick must contain one to three Plays.")
        if len(trick.plays) < 3 and index != len(supplied) - 1:
            raise ValueError("Only the final supplied Historical Trick may be incomplete.")
        plays = []
        for play in trick.plays:
            if not isinstance(play, HistoricalPlay):
                raise ValueError("Historical Tricks must contain HistoricalPlay values.")
            player_id = _require_stable_player_id(
                play.player_id,
                f"Party-wide Claim Evidence '{game_id}' trick {expected_number} Player",
            )
            if player_id not in participant_ids:
                raise ValueError("Historical Play must identify one Evidence Player.")
            card = _canonicalize_cards(
                (play.card,),
                f"Party-wide Claim Evidence '{game_id}' trick {expected_number} Card",
                expected_count=1,
            )[0]
            plays.append(HistoricalPlay(player_id=player_id, card=card))
        copied.append(
            HistoricalTrick(
                trick_number=expected_number,
                leader_player_id=leader,
                plays=tuple(plays),
            )
        )
    return tuple(copied)


@dataclass(frozen=True, slots=True)
class _PartyWideClaimHistoricalSource:
    game_id: str
    players: tuple[HistoricalPlayer, ...]
    skat: tuple[str, ...]
    declarer_player_id: str
    declaration: GameDeclaration
    discarded_cards: tuple[str, ...]
    tricks: tuple[HistoricalTrick, ...]


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class PartyWideClaimEvidenceV1:
    """One private complete-world Deal and exact legal retrospective prefix."""

    party_wide_claim_evidence_version: int
    game_id: str
    players: tuple[HistoricalPlayer, ...]
    skat: tuple[str, str]
    declarer_player_id: str
    declaration: GameDeclaration
    discarded_cards: tuple[str, ...]
    tricks: tuple[HistoricalTrick, ...]
    completed_tricks: tuple[HistoricalDerivedCompletedTrick, ...]
    current_trick: HistoricalIncompleteTrick | None
    remaining_hands: tuple[tuple[str, tuple[str, ...]], ...]
    next_player_id: str
    declarer_trick_points: int
    defender_trick_points: int
    declarer_completed_tricks: int
    defender_completed_tricks: int
    out_of_play_cards: tuple[str, str]
    played_card_count: int
    unresolved_card_count: int
    unresolved_card_points: int
    remaining_trick_count: int

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("PartyWideClaimEvidenceV1 must be constructed by its focused builder.")

    @classmethod
    def _from_validated(cls, **values: object) -> "PartyWideClaimEvidenceV1":
        evidence = object.__new__(cls)
        for field_name, field_value in values.items():
            object.__setattr__(evidence, field_name, field_value)
        return evidence

    def to_dict(self) -> dict[str, Any]:
        return {
            "party_wide_claim_evidence_version": self.party_wide_claim_evidence_version,
            "game_id": self.game_id,
            "players": [
                {
                    "player_id": player.player_id,
                    "player_label": player.player_label,
                    "seat": player.seat,
                    "initial_hand": list(player.initial_hand),
                }
                for player in self.players
            ],
            "skat": list(self.skat),
            "declarer_player_id": self.declarer_player_id,
            "declaration": build_serializable_game_declaration(self.declaration),
            "discarded_cards": list(self.discarded_cards),
            "tricks": [
                {
                    "trick_number": trick.trick_number,
                    "leader_player_id": trick.leader_player_id,
                    "plays": [
                        {"player_id": play.player_id, "card": play.card} for play in trick.plays
                    ],
                }
                for trick in self.tricks
            ],
            "completed_tricks": [
                build_serializable_derived_trick(trick) for trick in self.completed_tricks
            ],
            "current_trick": (
                build_serializable_incomplete_trick(self.current_trick)
                if self.current_trick is not None
                else None
            ),
            "remaining_hands": {
                player_id: list(cards) for player_id, cards in self.remaining_hands
            },
            "next_player_id": self.next_player_id,
            "declarer_trick_points": self.declarer_trick_points,
            "defender_trick_points": self.defender_trick_points,
            "declarer_completed_tricks": self.declarer_completed_tricks,
            "defender_completed_tricks": self.defender_completed_tricks,
            "out_of_play_cards": list(self.out_of_play_cards),
            "played_card_count": self.played_card_count,
            "unresolved_card_count": self.unresolved_card_count,
            "unresolved_card_points": self.unresolved_card_points,
            "remaining_trick_count": self.remaining_trick_count,
        }


def _build_party_wide_claim_historical_source(
    *,
    game_id: str,
    players: tuple[HistoricalPlayer, ...],
    skat: tuple[str, ...],
    declarer_player_id: str,
    declaration: GameDeclaration,
    discarded_cards: tuple[str, ...],
    tricks: tuple[HistoricalTrick, ...],
) -> _PartyWideClaimHistoricalSource:
    game_id = _require_identifier(game_id, "game_id")
    normalized_players = _copy_players(players, game_id)
    normalized_skat = _canonicalize_cards(skat, "skat", expected_count=2)
    dealt_cards = (
        tuple(card for player in normalized_players for card in player.initial_hand)
        + normalized_skat
    )
    if len(dealt_cards) != 32 or set(dealt_cards) != _FULL_DECK_SET:
        raise ValueError("Initial hands and Skat must form the complete 32-Card Deal.")
    if len(set(dealt_cards)) != 32:
        raise ValueError("Initial hands and Skat contain duplicate Cards.")

    declarer_player_id = _require_stable_player_id(declarer_player_id, "declarer_player_id")
    participant_ids = frozenset(player.player_id for player in normalized_players)
    if declarer_player_id not in participant_ids:
        raise ValueError("declarer_player_id must identify one Evidence Player.")
    normalized_declaration = _copy_declaration(
        declaration,
        players=normalized_players,
        skat=normalized_skat,
        declarer_player_id=declarer_player_id,
    )
    normalized_discards = _canonicalize_cards(discarded_cards, "discarded_cards")
    declarer = next(
        player for player in normalized_players if player.player_id == declarer_player_id
    )
    if normalized_declaration.hand_game:
        if normalized_discards:
            raise ValueError("Hand Claim Evidence requires no discarded Cards.")
    else:
        if len(normalized_discards) != 2:
            raise ValueError("Non-Hand Claim Evidence requires exactly two discarded Cards.")
        available_to_declarer = {*declarer.initial_hand, *normalized_skat}
        if not set(normalized_discards) <= available_to_declarer:
            raise ValueError("Discarded Cards must have been available to the Declarer.")

    normalized_tricks = _copy_tricks(
        tricks,
        game_id=game_id,
        participant_ids=participant_ids,
    )
    return _PartyWideClaimHistoricalSource(
        game_id=game_id,
        players=normalized_players,
        skat=(normalized_skat[0], normalized_skat[1]),
        declarer_player_id=declarer_player_id,
        declaration=normalized_declaration,
        discarded_cards=normalized_discards,
        tricks=normalized_tricks,
    )


def _build_party_wide_claim_evidence_from_replay_v1(
    source: _PartyWideClaimHistoricalSource,
    replay: HistoricalReplayState,
) -> PartyWideClaimEvidenceV1:
    if not isinstance(replay, HistoricalReplayState):
        raise ValueError("replay must be a HistoricalReplayState.")
    _validate_retained_replay_matches_source(source, replay)
    completed_tricks = tuple(
        HistoricalDerivedCompletedTrick(
            trick_number=trick.trick_number,
            leader_player_id=trick.leader_player_id,
            plays=tuple(trick.plays),
            winner_player_id=trick.winner_player_id,
            winner_side=trick.winner_side,
            trick_points=trick.trick_points,
        )
        for trick in replay.completed_tricks
    )
    current_trick = (
        HistoricalIncompleteTrick(
            trick_number=replay.current_trick.trick_number,
            leader_player_id=replay.current_trick.leader_player_id,
            plays=tuple(replay.current_trick.plays),
            next_player_id=replay.current_trick.next_player_id,
        )
        if replay.current_trick is not None
        else None
    )
    remaining_hands = tuple(
        (player_id, _canonicalize_cards(cards, f"remaining hand for '{player_id}'"))
        for player_id, cards in replay.remaining_hands
    )
    out_of_play = source.skat if source.declaration.hand_game else source.discarded_cards
    current_trick_cards = (
        tuple(card for _, card in current_trick.plays) if current_trick is not None else ()
    )
    unresolved_cards = (
        tuple(card for _, cards in remaining_hands for card in cards) + current_trick_cards
    )
    unresolved_card_count = len(unresolved_cards)
    if unresolved_card_count % 3 != 0:
        raise ValueError("Unresolved Claim Cards must form complete Tricks.")
    remaining_trick_count = unresolved_card_count // 3
    declarer_completed_tricks = sum(trick.winner_side == "declarer" for trick in completed_tricks)
    defender_completed_tricks = len(completed_tricks) - declarer_completed_tricks
    declarer_trick_points = sum(
        trick.trick_points for trick in completed_tricks if trick.winner_side == "declarer"
    )
    defender_trick_points = sum(
        trick.trick_points for trick in completed_tricks if trick.winner_side == "defenders"
    )
    unresolved_card_points = sum(get_card_points(card) for card in unresolved_cards)
    out_of_play_points = sum(get_card_points(card) for card in out_of_play)
    if (
        declarer_trick_points + defender_trick_points + unresolved_card_points + out_of_play_points
        != 120
    ):
        raise ValueError("Claim Evidence Card points must account for all 120 points.")
    if remaining_trick_count + len(completed_tricks) != 10:
        raise ValueError("Completed and unresolved Claim Tricks must total ten.")

    return PartyWideClaimEvidenceV1._from_validated(
        party_wide_claim_evidence_version=PARTY_WIDE_CLAIM_EVIDENCE_VERSION,
        game_id=source.game_id,
        players=source.players,
        skat=source.skat,
        declarer_player_id=source.declarer_player_id,
        declaration=source.declaration,
        discarded_cards=source.discarded_cards,
        tricks=source.tricks,
        completed_tricks=completed_tricks,
        current_trick=current_trick,
        remaining_hands=remaining_hands,
        next_player_id=replay.next_player_id,
        declarer_trick_points=declarer_trick_points,
        defender_trick_points=defender_trick_points,
        declarer_completed_tricks=declarer_completed_tricks,
        defender_completed_tricks=defender_completed_tricks,
        out_of_play_cards=(out_of_play[0], out_of_play[1]),
        played_card_count=replay.played_card_count,
        unresolved_card_count=unresolved_card_count,
        unresolved_card_points=unresolved_card_points,
        remaining_trick_count=remaining_trick_count,
    )


def _validate_retained_replay_matches_source(
    source: _PartyWideClaimHistoricalSource,
    replay: HistoricalReplayState,
) -> None:
    seat_order = tuple(
        next(player.player_id for player in source.players if player.seat == seat)
        for seat in HISTORICAL_SEATS
    )
    expected_hands = {player.player_id: list(player.initial_hand) for player in source.players}
    if not source.declaration.hand_game:
        declarer_hand = expected_hands[source.declarer_player_id]
        declarer_hand.extend(source.skat)
        for card in source.discarded_cards:
            declarer_hand.remove(card)

    expected_completed = []
    expected_current = None
    expected_next_player = seat_order[0]
    expected_played_count = 0
    for trick in source.tricks:
        serialized_plays = tuple((play.player_id, play.card) for play in trick.plays)
        for play in trick.plays:
            if play.card not in expected_hands[play.player_id]:
                raise ValueError("Retained Claim replay does not match its Historical record.")
            expected_hands[play.player_id].remove(play.card)
            expected_played_count += 1
        leader_index = seat_order.index(trick.leader_player_id)
        player_order = tuple(
            seat_order[(leader_index + offset) % len(seat_order)]
            for offset in range(len(seat_order))
        )
        if len(trick.plays) < 3:
            expected_next_player = player_order[len(trick.plays)]
            expected_current = HistoricalIncompleteTrick(
                trick_number=trick.trick_number,
                leader_player_id=trick.leader_player_id,
                plays=serialized_plays,
                next_player_id=expected_next_player,
            )
            continue
        cards = [play.card for play in trick.plays]
        winner_index = get_trick_winner(cards, source.declaration.game_type)
        winner_player_id = trick.plays[winner_index].player_id
        expected_completed.append(
            HistoricalDerivedCompletedTrick(
                trick_number=trick.trick_number,
                leader_player_id=trick.leader_player_id,
                plays=serialized_plays,
                winner_player_id=winner_player_id,
                winner_side=(
                    "declarer" if winner_player_id == source.declarer_player_id else "defenders"
                ),
                trick_points=get_trick_points(cards),
            )
        )
        expected_next_player = winner_player_id

    expected_remaining_hands = tuple(
        (
            player_id,
            _canonicalize_cards(
                expected_hands[player_id],
                f"expected remaining hand for '{player_id}'",
            ),
        )
        for player_id in seat_order
    )
    normalized_replay = HistoricalReplayState(
        completed_tricks=replay.completed_tricks,
        current_trick=replay.current_trick,
        remaining_hands=tuple(
            (
                player_id,
                _canonicalize_cards(cards, f"remaining hand for '{player_id}'"),
            )
            for player_id, cards in replay.remaining_hands
        ),
        next_player_id=replay.next_player_id,
        played_card_count=replay.played_card_count,
    )
    if normalized_replay != HistoricalReplayState(
        completed_tricks=tuple(expected_completed),
        current_trick=expected_current,
        remaining_hands=expected_remaining_hands,
        next_player_id=expected_next_player,
        played_card_count=expected_played_count,
    ):
        raise ValueError("Retained Claim replay does not match its Historical record.")


def build_party_wide_claim_evidence_v1(
    *,
    game_id: str,
    players: tuple[HistoricalPlayer, ...],
    skat: tuple[str, ...],
    declarer_player_id: str,
    declaration: GameDeclaration,
    discarded_cards: tuple[str, ...],
    tricks: tuple[HistoricalTrick, ...],
) -> PartyWideClaimEvidenceV1:
    source = _build_party_wide_claim_historical_source(
        game_id=game_id,
        players=players,
        skat=skat,
        declarer_player_id=declarer_player_id,
        declaration=declaration,
        discarded_cards=discarded_cards,
        tricks=tricks,
    )
    return _build_party_wide_claim_evidence_from_replay_v1(
        source,
        replay_historical_play_prefix(source),
    )


def build_party_wide_claim_evidence_from_historical_replay_v1(
    record: Any,
    replay: HistoricalReplayState,
) -> PartyWideClaimEvidenceV1:
    """Builds exact Claim Evidence from one already-retained Historical replay."""
    source = _build_party_wide_claim_historical_source(
        game_id=record.game_id,
        players=record.players,
        skat=record.skat,
        declarer_player_id=record.declarer_player_id,
        declaration=record.declaration,
        discarded_cards=record.discarded_cards,
        tricks=record.tricks,
    )
    return _build_party_wide_claim_evidence_from_replay_v1(source, replay)


def _serialize_exact_state(state: ExactSearchState) -> dict[str, Any]:
    return {
        "declaration": build_serializable_game_declaration(state.declaration),
        "declarer_player": state.declarer_player,
        "hands": {player: list(state.hand_for(player)) for player in FLAT_PLAYERS},
        "current_trick": [
            {"player": play.player, "card": play.card} for play in state.current_trick
        ],
        "next_player": state.next_player,
        "declarer_trick_points": state.declarer_trick_points,
        "defender_trick_points": state.defender_trick_points,
        "declarer_completed_tricks": state.declarer_completed_tricks,
        "defender_completed_tricks": state.defender_completed_tricks,
        "out_of_play_cards": list(state.out_of_play_cards),
    }


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class PartyWideClaimExactStateContextV1:
    """Stable identity reconciliation around one untraversed exact state."""

    party_wide_claim_exact_state_context_version: int
    stable_to_flat_player_map: tuple[tuple[str, str], ...]
    flat_to_stable_player_map: tuple[tuple[str, str], ...]
    claimant_flat_player: str
    claiming_party_flat_players: tuple[str, ...]
    opposing_party_flat_players: tuple[str, ...]
    exact_state: ExactSearchState

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "PartyWideClaimExactStateContextV1 must be constructed by its focused builder."
        )

    @classmethod
    def _from_validated(cls, **values: object) -> "PartyWideClaimExactStateContextV1":
        context = object.__new__(cls)
        for field_name, field_value in values.items():
            object.__setattr__(context, field_name, field_value)
        return context

    def to_dict(self) -> dict[str, Any]:
        return {
            "party_wide_claim_exact_state_context_version": (
                self.party_wide_claim_exact_state_context_version
            ),
            "stable_to_flat_player_map": dict(self.stable_to_flat_player_map),
            "flat_to_stable_player_map": dict(self.flat_to_stable_player_map),
            "claimant_flat_player": self.claimant_flat_player,
            "claiming_party_flat_players": list(self.claiming_party_flat_players),
            "opposing_party_flat_players": list(self.opposing_party_flat_players),
            "exact_state": _serialize_exact_state(self.exact_state),
        }


def build_party_wide_claim_exact_state_context_v1(
    claim: PartyWideAllRemainingTricksClaimV1,
    evidence: PartyWideClaimEvidenceV1,
) -> PartyWideClaimExactStateContextV1:
    if not isinstance(evidence, PartyWideClaimEvidenceV1):
        raise ValueError("evidence must be a PartyWideClaimEvidenceV1.")
    validate_party_wide_claim_against_evidence_v1(claim, evidence)
    mapping = build_historical_player_mapping(evidence)
    current_plays = evidence.current_trick.plays if evidence.current_trick is not None else ()
    exact_state = build_exact_search_state(
        declaration=evidence.declaration,
        declarer_player=mapping.to_flat(evidence.declarer_player_id),
        remaining_hands=tuple(
            (mapping.to_flat(player_id), cards) for player_id, cards in evidence.remaining_hands
        ),
        current_trick=tuple(
            (mapping.to_flat(player_id), card) for player_id, card in current_plays
        ),
        next_player=mapping.to_flat(evidence.next_player_id),
        declarer_trick_points=evidence.declarer_trick_points,
        defender_trick_points=evidence.defender_trick_points,
        declarer_completed_tricks=evidence.declarer_completed_tricks,
        defender_completed_tricks=evidence.defender_completed_tricks,
        out_of_play_cards=evidence.out_of_play_cards,
    )

    claiming_party_flat_players = (
        ("me",) if claim.claiming_party == "declarer" else ("left", "right")
    )
    opposing_party_flat_players = tuple(
        player for player in FLAT_PLAYERS if player not in claiming_party_flat_players
    )
    context = PartyWideClaimExactStateContextV1._from_validated(
        party_wide_claim_exact_state_context_version=(PARTY_WIDE_CLAIM_EXACT_STATE_CONTEXT_VERSION),
        stable_to_flat_player_map=tuple(mapping.stable_to_flat),
        flat_to_stable_player_map=tuple(mapping.flat_to_stable),
        claimant_flat_player=mapping.to_flat(claim.claimant_player_id),
        claiming_party_flat_players=claiming_party_flat_players,
        opposing_party_flat_players=opposing_party_flat_players,
        exact_state=exact_state,
    )
    validate_party_wide_claim_exact_state_context_v1(claim, evidence, context)
    return context


def validate_party_wide_claim_exact_state_context_v1(
    claim: PartyWideAllRemainingTricksClaimV1,
    evidence: PartyWideClaimEvidenceV1,
    context: PartyWideClaimExactStateContextV1,
) -> None:
    """Reconciles a retained exact context without replaying or rebuilding it."""
    if not isinstance(evidence, PartyWideClaimEvidenceV1):
        raise ValueError("evidence must be a PartyWideClaimEvidenceV1.")
    if not isinstance(context, PartyWideClaimExactStateContextV1):
        raise ValueError("context must be a PartyWideClaimExactStateContextV1.")
    validate_party_wide_claim_against_evidence_v1(claim, evidence)
    mapping = build_historical_player_mapping(evidence)
    if (
        context.stable_to_flat_player_map != mapping.stable_to_flat
        or context.flat_to_stable_player_map != mapping.flat_to_stable
    ):
        raise ValueError("Exact State Context Player maps contradict Claim Evidence.")
    if context.claimant_flat_player != mapping.to_flat(claim.claimant_player_id):
        raise ValueError("Exact State Context claimant contradicts the Claim.")
    expected_claiming = ("me",) if claim.claiming_party == "declarer" else ("left", "right")
    expected_opposing = tuple(player for player in FLAT_PLAYERS if player not in expected_claiming)
    if (
        context.claiming_party_flat_players != expected_claiming
        or context.opposing_party_flat_players != expected_opposing
    ):
        raise ValueError("Exact State Context parties contradict the Claim.")

    exact_state = context.exact_state
    expected_hands = {
        mapping.to_flat(player_id): cards for player_id, cards in evidence.remaining_hands
    }
    if exact_state.declaration != evidence.declaration:
        raise ValueError("Exact State Declaration contradicts Claim Evidence.")
    if exact_state.declarer_player != "me":
        raise ValueError("Historical Claim mapping must map the Declarer to me.")
    if any(exact_state.hand_for(player) != expected_hands[player] for player in FLAT_PLAYERS):
        raise ValueError("Exact State remaining hands contradict Claim Evidence.")
    current_plays = evidence.current_trick.plays if evidence.current_trick is not None else ()
    expected_current = tuple(
        (mapping.to_flat(player_id), card) for player_id, card in current_plays
    )
    if tuple((play.player, play.card) for play in exact_state.current_trick) != expected_current:
        raise ValueError("Exact State current Trick contradicts Claim Evidence.")
    if exact_state.next_player != mapping.to_flat(evidence.next_player_id):
        raise ValueError("Exact State next Player contradicts Claim Evidence.")
    if (
        exact_state.declarer_trick_points != evidence.declarer_trick_points
        or exact_state.defender_trick_points != evidence.defender_trick_points
        or exact_state.declarer_completed_tricks != evidence.declarer_completed_tricks
        or exact_state.defender_completed_tricks != evidence.defender_completed_tricks
        or exact_state.out_of_play_cards != evidence.out_of_play_cards
        or exact_state.remaining_tricks != evidence.remaining_trick_count
    ):
        raise ValueError("Exact State counters contradict Claim Evidence.")
    exact_unresolved_cards = tuple(card for hand in exact_state.hands for card in hand) + tuple(
        play.card for play in exact_state.current_trick
    )
    if (
        len(exact_unresolved_cards) != evidence.unresolved_card_count
        or sum(get_card_points(card) for card in exact_unresolved_cards)
        != evidence.unresolved_card_points
    ):
        raise ValueError("Exact State unresolved Cards contradict Claim Evidence.")
