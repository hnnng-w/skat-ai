from typing import Any

from skat_ai.historical_decision_snapshot import HistoricalDecisionSnapshot


def _relative_player_lookup(snapshot: HistoricalDecisionSnapshot) -> dict[str, str]:
    return {
        player_id: relative_player
        for relative_player, player_id in snapshot.relative_player_map.items()
    }


def _serialize_relative_play(
    play: Any,
    relative_player_by_id: dict[str, str],
) -> dict[str, str]:
    return {
        "player": relative_player_by_id[play.player_id],
        "card": play.card,
    }


def build_training_feature_view(
    snapshot: HistoricalDecisionSnapshot,
) -> dict[str, Any]:
    """Converts one information-safe snapshot to identity-free model features."""
    visible_state = snapshot.visible_state
    declaration = visible_state.declaration
    relative_player_by_id = _relative_player_lookup(snapshot)

    return {
        "information_policy": "decision_time",
        "game_type": visible_state.game_type,
        "declaration": {
            "hand_game": declaration.hand_game,
            "ouvert": declaration.ouvert,
            "schneider_announced": declaration.schneider_announced,
            "schwarz_announced": declaration.schwarz_announced,
            "matadors": declaration.matadors,
            "bid_value": declaration.bid_value,
        },
        "acting_position": snapshot.acting_seat,
        "acting_side": snapshot.acting_side,
        "own_hand": list(visible_state.own_hand),
        "legal_cards": list(visible_state.legal_cards),
        "current_trick": [
            _serialize_relative_play(play, relative_player_by_id)
            for play in visible_state.current_trick
        ],
        "completed_tricks": [
            {
                "trick_number": trick.trick_number,
                "plays": [
                    _serialize_relative_play(play, relative_player_by_id)
                    for play in trick.plays
                ],
                "winner": relative_player_by_id[trick.winner_player_id],
                "winner_side": trick.winner_side,
                "trick_points": trick.trick_points,
            }
            for trick in visible_state.completed_tricks
        ],
        "declarer_trick_points": visible_state.declarer_trick_points,
        "defender_trick_points": visible_state.defender_trick_points,
        "opponent_hand_sizes": [
            {
                "player": opponent.relative_player,
                "remaining_card_count": opponent.remaining_card_count,
            }
            for opponent in visible_state.opponent_hand_sizes
        ],
        "skat_visibility": visible_state.skat_visibility,
        "known_skat_cards": list(visible_state.known_skat_cards),
        "public_exposed_cards": [
            {
                "player": relative_player_by_id[exposure.player_id],
                "cards": list(exposure.cards),
            }
            for exposure in visible_state.public_exposed_cards
        ],
    }
