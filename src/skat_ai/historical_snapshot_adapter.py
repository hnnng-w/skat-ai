from dataclasses import dataclass
from typing import Literal

from skat_ai.game_declaration import GameDeclaration
from skat_ai.game_state import GameState
from skat_ai.historical_decision_snapshot import HistoricalDecisionSnapshot
from skat_ai.historical_game import HistoricalGameRecord
from skat_ai.rules import get_legal_cards


@dataclass(frozen=True)
class HistoricalSnapshotPosition:
    """A local immediate-analysis position built from one safe snapshot."""

    state: GameState
    legal_cards: tuple[str, ...]
    left_hand_size: int
    right_hand_size: int
    game_declaration: GameDeclaration
    game_end_reason: Literal["not_ended"] = "not_ended"


def _build_stable_to_local_player_map(
    snapshot: HistoricalDecisionSnapshot,
) -> dict[str, str]:
    relative_player_map = snapshot.relative_player_map
    if set(relative_player_map) != {"me", "left", "right"}:
        raise ValueError("Historical snapshot relative player mapping is incomplete.")
    if relative_player_map["me"] != snapshot.acting_player_id:
        raise ValueError("Historical snapshot acting player must map to me.")
    if len(set(relative_player_map.values())) != 3:
        raise ValueError("Historical snapshot player mapping must contain three players.")
    return {
        stable_player_id: local_player
        for local_player, stable_player_id in relative_player_map.items()
    }


def build_position_from_historical_snapshot(
    snapshot: HistoricalDecisionSnapshot,
    historical_record: HistoricalGameRecord,
) -> HistoricalSnapshotPosition:
    """Converts only decision-time snapshot facts into a local analysis state."""
    if snapshot.source_game_id != historical_record.game_id:
        raise ValueError("Historical snapshot and record game IDs must match.")

    stable_to_local = _build_stable_to_local_player_map(snapshot)
    if historical_record.declarer_player_id not in stable_to_local:
        raise ValueError("Historical declarer must be present in the snapshot mapping.")

    visible_state = snapshot.visible_state
    completed_tricks = [
        {
            "cards": [play.card for play in trick.plays],
            "players": [stable_to_local[play.player_id] for play in trick.plays],
            "winner_player": stable_to_local[trick.winner_player_id],
            "winner_role": trick.winner_side,
        }
        for trick in visible_state.completed_tricks
    ]
    current_trick = [play.card for play in visible_state.current_trick]
    trick_leader = (
        stable_to_local[visible_state.current_trick[0].player_id]
        if visible_state.current_trick
        else "me"
    )

    opponent_hand_sizes = {
        opponent.relative_player: opponent.remaining_card_count
        for opponent in visible_state.opponent_hand_sizes
    }
    if set(opponent_hand_sizes) != {"left", "right"}:
        raise ValueError("Historical snapshot must contain left and right hand sizes.")
    for opponent in visible_state.opponent_hand_sizes:
        expected_player_id = snapshot.relative_player_map[opponent.relative_player]
        if opponent.player_id != expected_player_id:
            raise ValueError("Historical snapshot opponent hand-size mapping is inconsistent.")

    state = GameState(
        game_type=visible_state.game_type,
        player_role=(
            "declarer" if snapshot.acting_side == "declarer" else "defender"
        ),
        hand=list(visible_state.own_hand),
        current_trick=current_trick,
        skat=list(visible_state.known_skat_cards),
        player_position=snapshot.acting_seat,
        declarer_player=stable_to_local[historical_record.declarer_player_id],
        trick_leader=trick_leader,
        completed_tricks=completed_tricks,
        declarer_points=visible_state.declarer_trick_points,
        defender_points=visible_state.defender_trick_points,
        next_player="me",
    )
    legal_cards = tuple(
        get_legal_cards(
            hand=state.hand,
            current_trick=state.current_trick,
            game_type=state.game_type,
        )
    )
    if legal_cards != visible_state.legal_cards:
        raise ValueError("Historical snapshot legal cards do not match the local state.")

    declaration = visible_state.declaration
    game_declaration = GameDeclaration(
        game_type=visible_state.game_type,
        hand_game=declaration.hand_game,
        ouvert=declaration.ouvert,
        schneider_announced=declaration.schneider_announced,
        schwarz_announced=declaration.schwarz_announced,
        matadors=declaration.matadors,
        bid_value=declaration.bid_value,
    )

    return HistoricalSnapshotPosition(
        state=state,
        legal_cards=legal_cards,
        left_hand_size=opponent_hand_sizes["left"],
        right_hand_size=opponent_hand_sizes["right"],
        game_declaration=game_declaration,
    )
