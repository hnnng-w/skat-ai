from dataclasses import dataclass
from typing import Any, Literal

from skat_ai.deck import get_full_deck
from skat_ai.matador_inference import infer_matadors_from_known_ownership
from skat_ai.rules import get_legal_cards

HISTORICAL_DECISION_SNAPSHOT_SCHEMA_VERSION = 1
HISTORICAL_DECISION_INFORMATION_POLICY = "decision_time"

HistoricalSeat = Literal["forehand", "middlehand", "rearhand"]
HistoricalSide = Literal["declarer", "defenders"]
RelativePlayer = Literal["left", "right"]
SkatVisibility = Literal["unknown", "known_to_declarer"]


@dataclass(frozen=True)
class HistoricalSnapshotPlay:
    """One publicly visible play in a historical decision snapshot."""

    player_id: str
    card: str


@dataclass(frozen=True)
class HistoricalSnapshotCompletedTrick:
    """One trick completed before a historical decision."""

    trick_number: int
    plays: tuple[HistoricalSnapshotPlay, ...]
    winner_player_id: str
    winner_side: HistoricalSide
    trick_points: int


@dataclass(frozen=True)
class HistoricalSnapshotOpponentHandSize:
    """One opponent's public remaining-card count."""

    relative_player: RelativePlayer
    player_id: str
    remaining_card_count: int


@dataclass(frozen=True)
class HistoricalSnapshotExposedCards:
    """One player's publicly exposed remaining cards."""

    player_id: str
    cards: tuple[str, ...]


@dataclass(frozen=True)
class HistoricalSnapshotDeclaration:
    """Public declaration facts plus decision-time visible matadors."""

    hand_game: bool
    ouvert: bool
    schneider_announced: bool
    schwarz_announced: bool
    matadors: int | None
    bid_value: int


@dataclass(frozen=True)
class HistoricalSnapshotVisibleState:
    """Information available to the acting player before one actual play."""

    game_type: str
    declaration: HistoricalSnapshotDeclaration
    own_hand: tuple[str, ...]
    legal_cards: tuple[str, ...]
    skat_visibility: SkatVisibility
    known_skat_cards: tuple[str, ...]
    public_exposed_cards: tuple[HistoricalSnapshotExposedCards, ...]
    completed_tricks: tuple[HistoricalSnapshotCompletedTrick, ...]
    current_trick: tuple[HistoricalSnapshotPlay, ...]
    declarer_trick_points: int
    defender_trick_points: int
    opponent_hand_sizes: tuple[HistoricalSnapshotOpponentHandSize, ...]


@dataclass(frozen=True)
class HistoricalDecisionSnapshot:
    """The information-safe state immediately before one historical play."""

    source_game_id: str
    decision_index: int
    trick_number: int
    play_index: int
    acting_player_id: str
    acting_seat: HistoricalSeat
    acting_side: HistoricalSide
    actual_card_played: str
    information_cutoff: Literal["before_actual_play"]
    relative_player_map: dict[str, str]
    visible_state: HistoricalSnapshotVisibleState


@dataclass(frozen=True)
class HistoricalDecisionSnapshotSummary:
    """The ordered decision snapshots for one normal-play historical game."""

    schema_version: int
    information_policy: Literal["decision_time"]
    snapshot_count: int
    snapshots: tuple[HistoricalDecisionSnapshot, ...]


def _serialize_play(play: HistoricalSnapshotPlay) -> dict[str, str]:
    return {"player_id": play.player_id, "card": play.card}


def _serialize_completed_trick(
    trick: HistoricalSnapshotCompletedTrick,
) -> dict[str, Any]:
    return {
        "trick_number": trick.trick_number,
        "plays": [_serialize_play(play) for play in trick.plays],
        "winner_player_id": trick.winner_player_id,
        "winner_side": trick.winner_side,
        "trick_points": trick.trick_points,
    }


def build_serializable_historical_decision_snapshot_summary(
    summary: HistoricalDecisionSnapshotSummary,
) -> dict[str, Any]:
    """Builds the stable JSON representation of historical decision snapshots."""
    snapshots = []
    for snapshot in summary.snapshots:
        visible_state = snapshot.visible_state
        declaration = visible_state.declaration
        snapshots.append(
            {
                "source_game_id": snapshot.source_game_id,
                "decision_index": snapshot.decision_index,
                "trick_number": snapshot.trick_number,
                "play_index": snapshot.play_index,
                "acting_player_id": snapshot.acting_player_id,
                "acting_seat": snapshot.acting_seat,
                "acting_side": snapshot.acting_side,
                "actual_card_played": snapshot.actual_card_played,
                "information_cutoff": snapshot.information_cutoff,
                "relative_player_map": snapshot.relative_player_map.copy(),
                "visible_state": {
                    "game_type": visible_state.game_type,
                    "declaration": {
                        "hand_game": declaration.hand_game,
                        "ouvert": declaration.ouvert,
                        "schneider_announced": declaration.schneider_announced,
                        "schwarz_announced": declaration.schwarz_announced,
                        "matadors": declaration.matadors,
                        "bid_value": declaration.bid_value,
                    },
                    "own_hand": list(visible_state.own_hand),
                    "legal_cards": list(visible_state.legal_cards),
                    "skat_visibility": visible_state.skat_visibility,
                    "known_skat_cards": list(visible_state.known_skat_cards),
                    "public_exposed_cards": [
                        {
                            "player_id": exposure.player_id,
                            "cards": list(exposure.cards),
                        }
                        for exposure in visible_state.public_exposed_cards
                    ],
                    "completed_tricks": [
                        _serialize_completed_trick(trick)
                        for trick in visible_state.completed_tricks
                    ],
                    "current_trick": [
                        _serialize_play(play) for play in visible_state.current_trick
                    ],
                    "declarer_trick_points": visible_state.declarer_trick_points,
                    "defender_trick_points": visible_state.defender_trick_points,
                    "opponent_hand_sizes": [
                        {
                            "relative_player": opponent.relative_player,
                            "player_id": opponent.player_id,
                            "remaining_card_count": opponent.remaining_card_count,
                        }
                        for opponent in visible_state.opponent_hand_sizes
                    ],
                },
            }
        )

    return {
        "schema_version": summary.schema_version,
        "information_policy": summary.information_policy,
        "snapshot_count": summary.snapshot_count,
        "snapshots": snapshots,
    }


def _build_playable_hands(record: dict[str, Any]) -> dict[str, list[str]]:
    hands = {
        player["player_id"]: list(player["initial_hand"])
        for player in record["players"]
    }
    declaration = record["declaration"]
    if not declaration["hand_game"]:
        declarer_hand = hands[record["declarer_player_id"]]
        declarer_hand.extend(record["skat"])
        for card in record["discarded_cards"]:
            declarer_hand.remove(card)
    return hands


def _build_relative_player_map(
    acting_player_id: str,
    seat_order_player_ids: list[str],
) -> dict[str, str]:
    acting_index = seat_order_player_ids.index(acting_player_id)
    return {
        "me": acting_player_id,
        "left": seat_order_player_ids[(acting_index + 1) % 3],
        "right": seat_order_player_ids[(acting_index - 1) % 3],
    }


def _infer_visible_matadors(
    *,
    game_type: str,
    hand_game: bool,
    acting_player_id: str,
    declarer_player_id: str,
    own_hand: list[str],
    known_skat_cards: list[str],
    completed_tricks: tuple[HistoricalSnapshotCompletedTrick, ...],
    current_trick: tuple[HistoricalSnapshotPlay, ...],
    public_exposed_cards: tuple[HistoricalSnapshotExposedCards, ...],
) -> int | None:
    if game_type == "null":
        return None

    declarer_owned_cards = []
    non_declarer_owned_cards = []
    public_plays = [
        *(play for trick in completed_tricks for play in trick.plays),
        *current_trick,
    ]
    for play in public_plays:
        if play.player_id == declarer_player_id:
            declarer_owned_cards.append(play.card)
        else:
            non_declarer_owned_cards.append(play.card)

    if acting_player_id == declarer_player_id:
        declarer_owned_cards.extend(own_hand)
        declarer_owned_cards.extend(known_skat_cards)
        if not hand_game:
            declarer_owned_set = set(declarer_owned_cards)
            non_declarer_owned_cards = [
                card for card in get_full_deck() if card not in declarer_owned_set
            ]
    else:
        non_declarer_owned_cards.extend(own_hand)

    for exposure in public_exposed_cards:
        if exposure.player_id == declarer_player_id:
            declarer_owned_cards.extend(exposure.cards)

    return infer_matadors_from_known_ownership(
        game_type=game_type,
        declarer_owned_cards=declarer_owned_cards,
        non_declarer_owned_cards=non_declarer_owned_cards,
    )


def _build_completed_trick(
    derived_trick: dict[str, Any],
) -> HistoricalSnapshotCompletedTrick:
    return HistoricalSnapshotCompletedTrick(
        trick_number=derived_trick["trick_number"],
        plays=tuple(
            HistoricalSnapshotPlay(
                player_id=play["player_id"],
                card=play["card"],
            )
            for play in derived_trick["plays"]
        ),
        winner_player_id=derived_trick["winner_player_id"],
        winner_side=derived_trick["winner_side"],
        trick_points=derived_trick["trick_points"],
    )


def build_historical_decision_snapshots(
    historical_game_result: dict[str, Any],
) -> HistoricalDecisionSnapshotSummary:
    """Builds decision-time snapshots from one validated historical replay result."""
    record = historical_game_result["record"]
    declaration = record["declaration"]
    declarer_player_id = record["declarer_player_id"]
    players_by_id = {
        player["player_id"]: player for player in record["players"]
    }
    players_by_seat = {player["seat"]: player for player in record["players"]}
    seat_order_player_ids = [
        players_by_seat[seat]["player_id"]
        for seat in ("forehand", "middlehand", "rearhand")
    ]
    hands = _build_playable_hands(record)
    completed_tricks: list[HistoricalSnapshotCompletedTrick] = []
    declarer_trick_points = 0
    defender_trick_points = 0
    snapshots = []
    decision_index = 0

    for trick_index, trick in enumerate(record["tricks"]):
        current_trick: list[HistoricalSnapshotPlay] = []
        for play_index, play in enumerate(trick["plays"], start=1):
            decision_index += 1
            acting_player_id = play["player_id"]
            actual_card_played = play["card"]
            own_hand = hands[acting_player_id]
            current_trick_cards = [current_play.card for current_play in current_trick]
            legal_cards = get_legal_cards(
                hand=own_hand,
                current_trick=current_trick_cards,
                game_type=declaration["game_type"],
            )
            if actual_card_played not in own_hand or actual_card_played not in legal_cards:
                raise ValueError(
                    "Historical decision snapshots require an already validated "
                    f"replay; decision {decision_index} is inconsistent."
                )

            relative_player_map = _build_relative_player_map(
                acting_player_id=acting_player_id,
                seat_order_player_ids=seat_order_player_ids,
            )
            is_declarer = acting_player_id == declarer_player_id
            known_skat_cards = (
                list(record["discarded_cards"])
                if is_declarer and not declaration["hand_game"]
                else []
            )
            skat_visibility: SkatVisibility = (
                "known_to_declarer" if known_skat_cards else "unknown"
            )
            public_exposed_cards = (
                (
                    HistoricalSnapshotExposedCards(
                        player_id=declarer_player_id,
                        cards=tuple(hands[declarer_player_id]),
                    ),
                )
                if declaration["ouvert"]
                else ()
            )
            visible_matadors = _infer_visible_matadors(
                game_type=declaration["game_type"],
                hand_game=declaration["hand_game"],
                acting_player_id=acting_player_id,
                declarer_player_id=declarer_player_id,
                own_hand=own_hand,
                known_skat_cards=known_skat_cards,
                completed_tricks=tuple(completed_tricks),
                current_trick=tuple(current_trick),
                public_exposed_cards=public_exposed_cards,
            )
            snapshots.append(
                HistoricalDecisionSnapshot(
                    source_game_id=record["game_id"],
                    decision_index=decision_index,
                    trick_number=trick["trick_number"],
                    play_index=play_index,
                    acting_player_id=acting_player_id,
                    acting_seat=players_by_id[acting_player_id]["seat"],
                    acting_side="declarer" if is_declarer else "defenders",
                    actual_card_played=actual_card_played,
                    information_cutoff="before_actual_play",
                    relative_player_map=relative_player_map,
                    visible_state=HistoricalSnapshotVisibleState(
                        game_type=declaration["game_type"],
                        declaration=HistoricalSnapshotDeclaration(
                            hand_game=declaration["hand_game"],
                            ouvert=declaration["ouvert"],
                            schneider_announced=declaration.get(
                                "schneider_announced", False
                            ),
                            schwarz_announced=declaration.get(
                                "schwarz_announced", False
                            ),
                            matadors=visible_matadors,
                            bid_value=declaration["bid_value"],
                        ),
                        own_hand=tuple(own_hand),
                        legal_cards=tuple(legal_cards),
                        skat_visibility=skat_visibility,
                        known_skat_cards=tuple(known_skat_cards),
                        public_exposed_cards=public_exposed_cards,
                        completed_tricks=tuple(completed_tricks),
                        current_trick=tuple(current_trick),
                        declarer_trick_points=declarer_trick_points,
                        defender_trick_points=defender_trick_points,
                        opponent_hand_sizes=(
                            HistoricalSnapshotOpponentHandSize(
                                relative_player="left",
                                player_id=relative_player_map["left"],
                                remaining_card_count=len(
                                    hands[relative_player_map["left"]]
                                ),
                            ),
                            HistoricalSnapshotOpponentHandSize(
                                relative_player="right",
                                player_id=relative_player_map["right"],
                                remaining_card_count=len(
                                    hands[relative_player_map["right"]]
                                ),
                            ),
                        ),
                    ),
                )
            )

            own_hand.remove(actual_card_played)
            current_trick.append(
                HistoricalSnapshotPlay(
                    player_id=acting_player_id,
                    card=actual_card_played,
                )
            )

        completed_trick = _build_completed_trick(
            historical_game_result["derived_tricks"][trick_index]
        )
        completed_tricks.append(completed_trick)
        if completed_trick.winner_side == "declarer":
            declarer_trick_points += completed_trick.trick_points
        else:
            defender_trick_points += completed_trick.trick_points

    if decision_index != 30:
        raise ValueError(
            "Historical decision snapshots require exactly 30 validated plays."
        )

    return HistoricalDecisionSnapshotSummary(
        schema_version=HISTORICAL_DECISION_SNAPSHOT_SCHEMA_VERSION,
        information_policy=HISTORICAL_DECISION_INFORMATION_POLICY,
        snapshot_count=len(snapshots),
        snapshots=tuple(snapshots),
    )
