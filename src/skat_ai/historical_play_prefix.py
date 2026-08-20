from dataclasses import dataclass, replace
from typing import Any

from skat_ai.deck import get_full_deck
from skat_ai.rules import get_legal_cards, get_trick_points, get_trick_winner

HISTORICAL_SEATS = ("forehand", "middlehand", "rearhand")


@dataclass(frozen=True)
class HistoricalDerivedCompletedTrick:
    trick_number: int
    leader_player_id: str
    plays: tuple[tuple[str, str], ...]
    winner_player_id: str
    winner_side: str
    trick_points: int


@dataclass(frozen=True)
class HistoricalIncompleteTrick:
    trick_number: int
    leader_player_id: str
    plays: tuple[tuple[str, str], ...]
    next_player_id: str


@dataclass(frozen=True)
class HistoricalReplayState:
    """Exact immutable state reconstructed from a complete deal and play prefix."""

    completed_tricks: tuple[HistoricalDerivedCompletedTrick, ...]
    current_trick: HistoricalIncompleteTrick | None
    remaining_hands: tuple[tuple[str, tuple[str, ...]], ...]
    next_player_id: str
    played_card_count: int

    def remaining_hand_for(self, player_id: str) -> tuple[str, ...]:
        return next(
            cards for candidate_id, cards in self.remaining_hands if candidate_id == player_id
        )


def _build_playable_hands(record: Any) -> dict[str, list[str]]:
    hands = {player.player_id: list(player.initial_hand) for player in record.players}
    if not record.declaration.hand_game:
        declarer_hand = hands[record.declarer_player_id]
        declarer_hand.extend(record.skat)
        for card in record.discarded_cards:
            declarer_hand.remove(card)
    return hands


def _get_player_order_from_leader(
    leader_player_id: str,
    seat_order_player_ids: list[str],
) -> list[str]:
    leader_index = seat_order_player_ids.index(leader_player_id)
    return [
        seat_order_player_ids[(leader_index + offset) % len(seat_order_player_ids)]
        for offset in range(len(seat_order_player_ids))
    ]


def replay_historical_play_prefix(record: Any) -> HistoricalReplayState:
    """Validates and exactly replays every supplied historical play."""
    hands = _build_playable_hands(record)
    player_by_seat = {player.seat: player.player_id for player in record.players}
    seat_order_player_ids = [player_by_seat[seat] for seat in HISTORICAL_SEATS]
    expected_leader = seat_order_player_ids[0]
    completed_tricks = []
    current_trick = None
    played_card_count = 0
    discarded_or_hand_skat = (
        set(record.skat) if record.declaration.hand_game else set(record.discarded_cards)
    )

    for trick_index, trick in enumerate(record.tricks):
        trick_name = f"Historical game '{record.game_id}' trick {trick.trick_number}"
        if trick.leader_player_id not in hands:
            raise ValueError(
                f"{trick_name}.leader_player_id references unknown player "
                f"'{trick.leader_player_id}'."
            )
        if trick.leader_player_id != expected_leader:
            raise ValueError(
                f"{trick_name} must be led by '{expected_leader}', got '{trick.leader_player_id}'."
            )
        expected_order = _get_player_order_from_leader(
            trick.leader_player_id, seat_order_player_ids
        )
        supplied_order = [play.player_id for play in trick.plays]
        if supplied_order != expected_order[: len(trick.plays)]:
            raise ValueError(
                f"{trick_name} play order must start with "
                f"{expected_order[: len(trick.plays)]}, got {supplied_order}."
            )

        trick_cards = []
        for play_index, play in enumerate(trick.plays):
            play_name = f"{trick_name} play {play_index + 1} player '{play.player_id}'"
            if play.card in discarded_or_hand_skat:
                raise ValueError(
                    f"{play_name} uses unplayable skat or discarded card '{play.card}'."
                )
            if play.card not in hands[play.player_id]:
                owner = next(
                    (
                        player_id
                        for player_id, remaining_hand in hands.items()
                        if play.card in remaining_hand
                    ),
                    None,
                )
                owner_text = f"; remaining owner is '{owner}'" if owner is not None else ""
                raise ValueError(
                    f"{play_name} does not own remaining card '{play.card}'{owner_text}."
                )
            legal_cards = get_legal_cards(
                hand=hands[play.player_id],
                current_trick=trick_cards,
                game_type=record.declaration.game_type,
            )
            if play.card not in legal_cards:
                raise ValueError(
                    f"{play_name} illegally plays '{play.card}'; legal cards are {legal_cards}."
                )
            hands[play.player_id].remove(play.card)
            trick_cards.append(play.card)
            played_card_count += 1

        serialized_plays = tuple((play.player_id, play.card) for play in trick.plays)
        if len(trick.plays) < 3:
            if trick_index != len(record.tricks) - 1:
                raise ValueError(
                    f"{trick_name} is incomplete; only the final historical trick may "
                    "be incomplete."
                )
            current_trick = HistoricalIncompleteTrick(
                trick_number=trick.trick_number,
                leader_player_id=trick.leader_player_id,
                plays=serialized_plays,
                next_player_id=expected_order[len(trick.plays)],
            )
            expected_leader = current_trick.next_player_id
            continue

        winner_index = get_trick_winner(trick_cards, record.declaration.game_type)
        winner_player_id = trick.plays[winner_index].player_id
        completed_tricks.append(
            HistoricalDerivedCompletedTrick(
                trick_number=trick.trick_number,
                leader_player_id=trick.leader_player_id,
                plays=serialized_plays,
                winner_player_id=winner_player_id,
                winner_side=(
                    "declarer" if winner_player_id == record.declarer_player_id else "defenders"
                ),
                trick_points=get_trick_points(trick_cards),
            )
        )
        expected_leader = winner_player_id

    all_played_cards = [play.card for trick in record.tricks for play in trick.plays]
    remaining_cards = [card for hand in hands.values() for card in hand]
    final_skat = record.skat if record.declaration.hand_game else record.discarded_cards
    accounted_cards = [*all_played_cards, *remaining_cards, *final_skat]
    if len(accounted_cards) != 32 or set(accounted_cards) != set(get_full_deck()):
        raise ValueError(
            f"Historical game '{record.game_id}': replay must account for all 32 "
            "dealt cards exactly once."
        )

    return HistoricalReplayState(
        completed_tricks=tuple(completed_tricks),
        current_trick=current_trick,
        remaining_hands=tuple(
            (player_id, tuple(hands[player_id])) for player_id in seat_order_player_ids
        ),
        next_player_id=expected_leader,
        played_card_count=played_card_count,
    )


def replay_historical_state_at_play_boundary(
    record: Any,
    after_play_count: int,
) -> HistoricalReplayState:
    """Replays exactly the supplied number of chronological historical plays."""
    total_play_count = sum(len(trick.plays) for trick in record.tricks)
    if (
        isinstance(after_play_count, bool)
        or not isinstance(after_play_count, int)
        or not 0 <= after_play_count <= total_play_count
    ):
        raise ValueError(
            f"Historical game '{record.game_id}': play boundary must be an integer "
            f"from 0 to {total_play_count}."
        )

    remaining_count = after_play_count
    prefix_tricks = []
    for trick in record.tricks:
        if remaining_count == 0:
            break
        play_count = min(remaining_count, len(trick.plays))
        prefix_tricks.append(replace(trick, plays=trick.plays[:play_count]))
        remaining_count -= play_count
        if play_count < len(trick.plays):
            break
    if remaining_count != 0:
        raise ValueError(
            f"Historical game '{record.game_id}': play boundary exceeds supplied plays."
        )
    return replay_historical_play_prefix(replace(record, tricks=tuple(prefix_tricks)))


def derive_historical_state_at_play_boundary_from_retained_replay(
    record: Any,
    final_replay: HistoricalReplayState,
    after_play_count: int,
) -> HistoricalReplayState:
    """Derives an earlier boundary after one retained full-prefix replay."""
    total_play_count = sum(len(trick.plays) for trick in record.tricks)
    if (
        not isinstance(final_replay, HistoricalReplayState)
        or final_replay.played_card_count != total_play_count
    ):
        raise ValueError("final_replay must match the complete recorded play prefix.")
    if (
        isinstance(after_play_count, bool)
        or not isinstance(after_play_count, int)
        or not 0 <= after_play_count <= total_play_count
    ):
        raise ValueError(
            f"Historical game '{record.game_id}': play boundary must be an integer "
            f"from 0 to {total_play_count}."
        )

    completed_by_number = {trick.trick_number: trick for trick in final_replay.completed_tricks}
    hands = _build_playable_hands(record)
    player_by_seat = {player.seat: player.player_id for player in record.players}
    seat_order = tuple(player_by_seat[seat] for seat in HISTORICAL_SEATS)
    completed_tricks = []
    current_trick = None
    remaining_count = after_play_count
    next_player_id = seat_order[0]

    for trick in record.tricks:
        if remaining_count == 0:
            break
        selected_count = min(remaining_count, len(trick.plays))
        selected_plays = trick.plays[:selected_count]
        for play in selected_plays:
            hands[play.player_id].remove(play.card)
        serialized_plays = tuple((play.player_id, play.card) for play in selected_plays)
        leader_index = seat_order.index(trick.leader_player_id)
        player_order = tuple(
            seat_order[(leader_index + offset) % len(seat_order)]
            for offset in range(len(seat_order))
        )
        if selected_count < 3:
            next_player_id = player_order[selected_count]
            current_trick = HistoricalIncompleteTrick(
                trick_number=trick.trick_number,
                leader_player_id=trick.leader_player_id,
                plays=serialized_plays,
                next_player_id=next_player_id,
            )
            remaining_count = 0
            break
        try:
            completed = completed_by_number[trick.trick_number]
        except KeyError as error:
            raise ValueError("final_replay does not contain a recorded completed Trick.") from error
        if completed.plays != serialized_plays:
            raise ValueError("final_replay does not match the recorded play prefix.")
        completed_tricks.append(completed)
        next_player_id = completed.winner_player_id
        remaining_count -= selected_count

    if remaining_count != 0:
        raise ValueError(
            f"Historical game '{record.game_id}': play boundary exceeds supplied plays."
        )
    return HistoricalReplayState(
        completed_tricks=tuple(completed_tricks),
        current_trick=current_trick,
        remaining_hands=tuple((player_id, tuple(hands[player_id])) for player_id in seat_order),
        next_player_id=next_player_id,
        played_card_count=after_play_count,
    )


def build_serializable_derived_trick(
    trick: HistoricalDerivedCompletedTrick,
) -> dict[str, Any]:
    return {
        "trick_number": trick.trick_number,
        "leader_player_id": trick.leader_player_id,
        "plays": [{"player_id": player_id, "card": card} for player_id, card in trick.plays],
        "winner_player_id": trick.winner_player_id,
        "winner_side": trick.winner_side,
        "trick_points": trick.trick_points,
    }


def build_serializable_incomplete_trick(
    trick: HistoricalIncompleteTrick,
) -> dict[str, Any]:
    return {
        "trick_number": trick.trick_number,
        "leader_player_id": trick.leader_player_id,
        "plays": [{"player_id": player_id, "card": card} for player_id, card in trick.plays],
        "next_player_id": trick.next_player_id,
    }
