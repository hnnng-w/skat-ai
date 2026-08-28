from typing import Any

from skatmind.defender_open_play import (
    DefenderOpenPlay,
    adjudicate_defender_open_play,
    validate_exact_remaining_play_state,
)
from skatmind.final_settlement import build_final_settlement_summary
from skatmind.game_result import build_game_result_summary_from_score_summary
from skatmind.game_value import build_game_value_summary
from skatmind.historical_game_end import HistoricalDefenderOpenPlay
from skatmind.historical_play_prefix import (
    HistoricalReplayState,
    build_serializable_incomplete_trick,
)
from skatmind.historical_player_mapping import build_historical_player_mapping
from skatmind.overbid import build_overbid_summary
from skatmind.rules import get_card_points


def _build_point_accounting(record: Any, replay: HistoricalReplayState) -> dict[str, int]:
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
    return {
        "completed_trick_declarer_points": declarer_trick_points,
        "completed_trick_defender_points": defender_trick_points,
        "skat_points": skat_points,
        "observed_declarer_points": declarer_trick_points + skat_points,
        "observed_defender_points": defender_trick_points,
        "unresolved_current_trick_points": unresolved_current_trick_points,
        "unresolved_remaining_hand_points": unresolved_remaining_hand_points,
        "total_unresolved_points": (
            unresolved_current_trick_points + unresolved_remaining_hand_points
        ),
        "total_card_points": 120,
    }


def _map_exact_proof_to_stable_ids(
    exact_proof: dict[str, Any],
    player_mapping: Any,
) -> dict[str, Any]:
    mapped = {key: value for key, value in exact_proof.items() if not key.endswith("_line")}
    line_key = "successful_line" if exact_proof["status"] == "valid" else "counterexample_line"
    mapped[line_key] = [
        {
            "player_id": player_mapping.to_stable(move["player"]),
            "card": move["card"],
            "card_visibility": move["card_visibility"],
            "trick_winner_player_id": (
                player_mapping.to_stable(move["trick_winner"])
                if move["trick_winner"] is not None
                else None
            ),
        }
        for move in exact_proof[line_key]
    ]
    return mapped


def adjudicate_historical_defender_open_play(
    record: Any,
    replay: HistoricalReplayState,
) -> dict[str, Any]:
    """Reconstructs and exactly adjudicates terminal historical defender open play."""
    event = record.game_end
    if not isinstance(event, HistoricalDefenderOpenPlay):
        raise ValueError("Historical defender-open-play adjudication requires its event.")
    completed_trick_count = len(replay.completed_tricks)
    if completed_trick_count < 5:
        raise ValueError(
            f"Historical game '{record.game_id}': defender open play supports at most "
            "five unresolved tricks and requires at least five completed tricks."
        )
    if completed_trick_count >= 10:
        raise ValueError(
            f"Historical game '{record.game_id}': at least one trick must remain "
            "unresolved for defender open play."
        )

    reconstructed_exposing_hand = replay.remaining_hand_for(
        event.exposing_defender_player_id
    )
    if not reconstructed_exposing_hand:
        raise ValueError(
            f"Historical game '{record.game_id}': the exposing defender must have at "
            "least one remaining hand card."
        )
    if set(event.exposed_cards) != set(reconstructed_exposing_hand):
        raise ValueError(
            f"Historical game '{record.game_id}': exposed_cards must exactly equal the "
            "exposing defender's reconstructed complete current hand."
        )

    player_mapping = build_historical_player_mapping(record)
    flat_hands = {
        player_mapping.to_flat(player_id): cards
        for player_id, cards in replay.remaining_hands
    }
    open_play = DefenderOpenPlay(
        schema_version=event.schema_version,
        kind=event.kind,
        exposing_defender=player_mapping.to_flat(event.exposing_defender_player_id),
        remaining_hands=tuple(
            (player, flat_hands[player]) for player in ("me", "left", "right")
        ),
        declarer_response=event.declarer_response,
    )
    current_trick_cards = (
        [card for _, card in replay.current_trick.plays]
        if replay.current_trick is not None
        else []
    )
    current_leader_id = (
        replay.current_trick.leader_player_id
        if replay.current_trick is not None
        else replay.next_player_id
    )
    completed_tricks = [
        {
            "cards": [card for _, card in trick.plays],
            "winner_role": trick.winner_side,
        }
        for trick in replay.completed_tricks
    ]
    final_skat = record.skat if record.declaration.hand_game else record.discarded_cards
    context = validate_exact_remaining_play_state(
        {
            "game_type": record.declaration.game_type,
            "declarer_player": "me",
            "completed_tricks": completed_tricks,
            "current_trick": current_trick_cards,
            "trick_leader": player_mapping.to_flat(current_leader_id),
            "next_player": player_mapping.to_flat(replay.next_player_id),
            "skat": list(final_skat),
            "hand": list(flat_hands["me"]),
            "left_hand_size": len(flat_hands["left"]),
            "right_hand_size": len(flat_hands["right"]),
            "played_cards": [],
        },
        open_play,
    )

    points = _build_point_accounting(record, replay)
    if (
        points["observed_declarer_points"]
        + points["observed_defender_points"]
        + points["total_unresolved_points"]
        != 120
    ):
        raise ValueError(
            f"Historical game '{record.game_id}': observed and unresolved card points "
            "must total 120."
        )
    raw_result = build_game_result_summary_from_score_summary(
        {
            "total_declarer_points": points["observed_declarer_points"],
            "total_defender_points": points["observed_defender_points"],
        },
        game_type=record.declaration.game_type,
        completed_tricks=completed_tricks,
        game_end_reason=record.game_end_reason,
    )
    game_value_summary = build_game_value_summary(record.declaration)
    overbid_summary = build_overbid_summary(
        game_value_summary,
        record.declaration.bid_value,
    )
    if record.declaration.game_type == "null" and overbid_summary["is_overbid"]:
        raise ValueError(
            f"Historical game '{record.game_id}': overbid Null records require the "
            "impossible-Null settlement workflow and are not supported."
        )
    adjudication = adjudicate_defender_open_play(
        open_play,
        context,
        raw_result,
        game_value_summary,
        overbid_summary,
        completed_tricks,
    )
    game_result_summary = adjudication.game_result_summary
    final_settlement_summary = build_final_settlement_summary(
        game_value_summary,
        game_result_summary,
        overbid_summary,
        completed_tricks,
    )
    if not final_settlement_summary["is_complete"]:
        raise ValueError(
            f"Historical game '{record.game_id}': final settlement is incomplete: "
            f"{final_settlement_summary['missing_inputs']}."
        )

    flat_end = adjudication.game_shortening_summary
    end_summary = {
        "schema_version": flat_end["schema_version"],
        "kind": flat_end["kind"],
        "rule_sections": flat_end["rule_sections"],
        "declarer_player_id": record.declarer_player_id,
        "exposing_defender_player_id": event.exposing_defender_player_id,
        "non_exposing_defender_player_id": player_mapping.to_stable(
            flat_end["non_exposing_defender"]
        ),
        "defending_party_player_ids": [
            player_mapping.to_stable(player) for player in flat_end["defending_party"]
        ],
        "exposed_cards": flat_end["exposed_cards"],
        "exposed_card_count": flat_end["exposed_card_count"],
        "card_reconciliation": "confirmed",
        "declarer_response": flat_end["declarer_response"],
        "decision_state_before_shortening": flat_end[
            "decision_state_before_shortening"
        ],
        "remaining_trick_count": flat_end["remaining_trick_count"],
        "exact_proof": _map_exact_proof_to_stable_ids(
            flat_end["exact_proof"], player_mapping
        ),
        "rest_trick_assignment": flat_end["rest_trick_assignment"],
        "rest_tricks_recipient": flat_end["rest_tricks_recipient"],
        "adjudicated_winner": flat_end["adjudicated_winner"],
        "winner_basis": flat_end["winner_basis"],
        "continued_play_requested": False,
        "event_after_play_count": replay.played_card_count,
        "event_after_completed_trick_count": completed_trick_count,
        "event_during_incomplete_trick": replay.current_trick is not None,
    }
    assigned_recipient = game_result_summary["rest_tricks_recipient"]
    points.update(
        {
            "assigned_declarer_points": (
                points["total_unresolved_points"]
                if assigned_recipient == "declarer"
                else 0
            ),
            "assigned_defender_points": (
                points["total_unresolved_points"]
                if assigned_recipient == "defenders"
                else 0
            ),
            "final_declarer_points": game_result_summary["declarer_points"],
            "final_defender_points": game_result_summary["defender_points"],
        }
    )
    effective_schwarz = game_result_summary["effective_schwarz_status"]
    result = {
        "declarer_trick_points": points["completed_trick_declarer_points"],
        "defender_trick_points": points["completed_trick_defender_points"],
        "skat_points": points["skat_points"],
        "declarer_points": game_result_summary["declarer_points"],
        "defender_points": game_result_summary["defender_points"],
        "winner": game_result_summary["winner"],
        "schneider_status": (
            "not_applicable"
            if record.declaration.game_type == "null"
            else game_result_summary["effective_schneider_status"]
        ),
        "schwarz_status": (
            "not_applicable"
            if record.declaration.game_type == "null"
            else "declarer"
            if effective_schwarz == "declarer_made_schwarz"
            else "defenders"
            if effective_schwarz == "defenders_made_schwarz"
            else "none"
        ),
        "play_prefix_summary": {
            "played_card_count": replay.played_card_count,
            "completed_trick_count": completed_trick_count,
            "current_trick_card_count": len(current_trick_cards),
            "remaining_hand_sizes": {
                player_id: len(cards) for player_id, cards in replay.remaining_hands
            },
            "next_player_id": replay.next_player_id,
        },
        "point_accounting": points,
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
