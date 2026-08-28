from typing import Any

from skatmind.defender_concession import (
    DefenderConcession,
    adjudicate_defender_concession,
)
from skatmind.final_settlement import build_final_settlement_summary
from skatmind.game_result import build_game_result_summary_from_score_summary
from skatmind.game_value import build_game_value_summary
from skatmind.historical_game_end import HistoricalDefenderConcession
from skatmind.historical_play_prefix import (
    HistoricalReplayState,
    build_serializable_incomplete_trick,
)
from skatmind.overbid import build_overbid_summary
from skatmind.rules import get_card_points


def adjudicate_historical_defender_concession(
    record: Any,
    replay: HistoricalReplayState,
) -> dict[str, Any]:
    """Adjudicates a stable-ID historical event through flat concession behavior."""
    event = record.game_end
    if not isinstance(event, HistoricalDefenderConcession):
        raise ValueError("Historical defender-concession adjudication requires its event.")

    declarer_trick_points = sum(
        trick.trick_points
        for trick in replay.completed_tricks
        if trick.winner_side == "declarer"
    )
    defender_trick_points = sum(
        trick.trick_points
        for trick in replay.completed_tricks
        if trick.winner_side == "defenders"
    )
    final_skat = record.skat if record.declaration.hand_game else record.discarded_cards
    skat_points = sum(get_card_points(card) for card in final_skat)
    observed_declarer_points = declarer_trick_points + skat_points
    observed_defender_points = defender_trick_points
    unresolved_current_trick_points = (
        sum(get_card_points(card) for _, card in replay.current_trick.plays)
        if replay.current_trick is not None
        else 0
    )
    unresolved_remaining_hand_points = sum(
        get_card_points(card)
        for _, remaining_hand in replay.remaining_hands
        for card in remaining_hand
    )
    total_unresolved_points = (
        unresolved_current_trick_points + unresolved_remaining_hand_points
    )
    if observed_declarer_points + observed_defender_points + total_unresolved_points != 120:
        raise ValueError(
            f"Historical game '{record.game_id}': observed and unresolved card points "
            "must total 120."
        )

    scoring_tricks = [
        {"winner_role": trick.winner_side} for trick in replay.completed_tricks
    ]
    raw_result = build_game_result_summary_from_score_summary(
        score_summary={
            "total_declarer_points": observed_declarer_points,
            "total_defender_points": observed_defender_points,
        },
        game_type=record.declaration.game_type,
        completed_tricks=scoring_tricks,
        game_end_reason=record.game_end_reason,
    )
    game_value_summary = build_game_value_summary(record.declaration)
    overbid_summary = build_overbid_summary(
        game_value_summary=game_value_summary,
        bid_value=record.declaration.bid_value,
    )
    if record.declaration.game_type == "null" and overbid_summary["is_overbid"]:
        raise ValueError(
            f"Historical game '{record.game_id}': overbid Null records require the "
            "impossible-Null settlement workflow and are not supported."
        )
    adjudication = adjudicate_defender_concession(
        game_shortening=DefenderConcession(
            schema_version=event.schema_version,
            kind=event.kind,
            conceding_player=event.conceding_defender_player_id,
            concession_form=event.concession_form,
        ),
        game_result_summary=raw_result,
        game_value_summary=game_value_summary,
        overbid_summary=overbid_summary,
        completed_tricks=scoring_tricks,
    )
    game_result_summary = adjudication.game_result_summary
    final_settlement_summary = build_final_settlement_summary(
        game_value_summary=game_value_summary,
        game_result_summary=game_result_summary,
        overbid_summary=overbid_summary,
        completed_tricks=scoring_tricks,
    )
    if not final_settlement_summary["is_complete"]:
        raise ValueError(
            f"Historical game '{record.game_id}': final settlement is incomplete: "
            f"{final_settlement_summary['missing_inputs']}."
        )

    defender_ids = [
        player.player_id
        for player in record.players
        if player.player_id != record.declarer_player_id
    ]
    non_conceding_defender_id = next(
        player_id
        for player_id in defender_ids
        if player_id != event.conceding_defender_player_id
    )
    end_summary = adjudication.game_shortening_summary.copy()
    end_summary.pop("conceding_player")
    end_summary.update(
        {
            "conceding_defender_player_id": event.conceding_defender_player_id,
            "non_conceding_defender_player_id": non_conceding_defender_id,
            "event_after_play_count": replay.played_card_count,
            "event_after_completed_trick_count": len(replay.completed_tricks),
            "event_during_incomplete_trick": replay.current_trick is not None,
        }
    )
    play_prefix_summary = {
        "played_card_count": replay.played_card_count,
        "completed_trick_count": len(replay.completed_tricks),
        "current_trick_card_count": (
            len(replay.current_trick.plays) if replay.current_trick is not None else 0
        ),
        "remaining_hand_sizes": {
            player_id: len(cards) for player_id, cards in replay.remaining_hands
        },
        "next_player_id": replay.next_player_id,
    }
    point_accounting = {
        "completed_trick_declarer_points": declarer_trick_points,
        "completed_trick_defender_points": defender_trick_points,
        "skat_points": skat_points,
        "observed_declarer_points": observed_declarer_points,
        "observed_defender_points": observed_defender_points,
        "unresolved_current_trick_points": unresolved_current_trick_points,
        "unresolved_remaining_hand_points": unresolved_remaining_hand_points,
        "total_unresolved_points": total_unresolved_points,
        "total_card_points": 120,
    }
    result = {
        "declarer_trick_points": declarer_trick_points,
        "defender_trick_points": defender_trick_points,
        "skat_points": skat_points,
        "declarer_points": observed_declarer_points,
        "defender_points": observed_defender_points,
        "winner": game_result_summary["winner"],
        "schneider_status": (
            "not_applicable"
            if record.declaration.game_type == "null"
            else game_result_summary["effective_schneider_status"]
        ),
        "schwarz_status": "not_applicable",
        "play_prefix_summary": play_prefix_summary,
        "point_accounting": point_accounting,
        "historical_game_end_summary": end_summary,
        "game_result_summary": game_result_summary,
        "game_value_summary": game_value_summary,
        "overbid_summary": overbid_summary,
        "final_settlement_summary": final_settlement_summary,
    }
    if replay.current_trick is not None:
        result["incomplete_current_trick"] = build_serializable_incomplete_trick(
            replay.current_trick
        )
    return result
