from typing import Any

from skat_ai.declarer_card_exposure import (
    DeclarerCardExposure,
    DeclarerCardExposureDetails,
    DeclarerExposedCardEvidence,
    DefenderExposureResponse,
    adjudicate_accepted_declarer_card_exposure,
)
from skat_ai.declarer_concession import DeclarerCardCountEvidence
from skat_ai.final_settlement import build_final_settlement_summary
from skat_ai.game_result import build_game_result_summary_from_score_summary
from skat_ai.game_value import build_game_value_summary
from skat_ai.historical_game_end import HistoricalDeclarerCardExposure
from skat_ai.historical_play_prefix import (
    HistoricalReplayState,
    build_serializable_incomplete_trick,
)
from skat_ai.historical_player_mapping import build_historical_player_mapping
from skat_ai.overbid import build_overbid_summary
from skat_ai.rules import get_card_points


def _build_exact_card_evidence(
    record: Any,
    replay: HistoricalReplayState,
) -> DeclarerExposedCardEvidence:
    unavailable_cards: list[tuple[str, str]] = []
    for trick in replay.completed_tricks:
        unavailable_cards.extend((card, "completed_tricks") for _, card in trick.plays)
    if replay.current_trick is not None:
        unavailable_cards.extend(
            (card, "current_trick") for _, card in replay.current_trick.plays
        )
    final_skat = record.skat if record.declaration.hand_game else record.discarded_cards
    final_skat_source = "Hand-skat" if record.declaration.hand_game else "discarded_cards"
    unavailable_cards.extend((card, final_skat_source) for card in final_skat)
    unavailable_cards.extend(
        (card, "defender_owned_cards")
        for player_id, hand in replay.remaining_hands
        if player_id != record.declarer_player_id
        for card in hand
    )
    exact_cards = replay.remaining_hand_for(record.declarer_player_id)
    return DeclarerExposedCardEvidence(
        declarer_player="me",
        exact_declarer_cards=exact_cards,
        declarer_card_count=DeclarerCardCountEvidence(
            hand_cards_remaining=len(exact_cards),
            source="exact_historical_play_prefix",
        ),
        unavailable_cards=tuple(unavailable_cards),
    )


def adjudicate_historical_declarer_card_exposure(
    record: Any,
    replay: HistoricalReplayState,
) -> dict[str, Any]:
    """Adjudicates one stable-ID accepted exposure through shared flat behavior."""
    event = record.game_end
    if not isinstance(event, HistoricalDeclarerCardExposure):
        raise ValueError(
            "Historical declarer-card-exposure adjudication requires its event."
        )
    remaining_declarer_cards = replay.remaining_hand_for(record.declarer_player_id)
    if not remaining_declarer_cards:
        raise ValueError(
            f"Historical game '{record.game_id}': declarer card exposure requires a "
            "non-empty reconstructed declarer hand."
        )

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

    player_mapping = build_historical_player_mapping(record)
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
    shared_exposure = DeclarerCardExposure(
        schema_version=event.schema_version,
        kind=event.kind,
        exposure=DeclarerCardExposureDetails(
            form=event.exposure.form,
            exposed_cards=event.exposure.exposed_cards,
            shown_to_player=(
                player_mapping.to_flat(event.exposure.shown_to_defender_player_id)
                if event.exposure.shown_to_defender_player_id is not None
                else None
            ),
        ),
        claimed_play_level=event.claimed_play_level,
        defender_responses=tuple(
            DefenderExposureResponse(
                player=player_mapping.to_flat(response.defender_player_id),
                response=response.response,
                form=response.form,
            )
            for response in event.defender_responses
        ),
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
    adjudication = adjudicate_accepted_declarer_card_exposure(
        game_shortening=shared_exposure,
        game_result_summary=raw_result,
        game_value_summary=game_value_summary,
        overbid_summary=overbid_summary,
        completed_tricks=scoring_tricks,
        card_evidence=_build_exact_card_evidence(record, replay),
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

    end_summary = adjudication.game_shortening_summary.copy()
    for flat_field in ("shown_to_player", "accepting_defenders", "acceptance_forms"):
        end_summary.pop(flat_field)
    response_by_id = {
        response.defender_player_id: response for response in event.defender_responses
    }
    accepting_ids = [response.defender_player_id for response in event.defender_responses]
    end_summary.update(
        {
            "declarer_player_id": record.declarer_player_id,
            "shown_to_defender_player_id": (
                event.exposure.shown_to_defender_player_id
            ),
            "accepting_defender_player_ids": accepting_ids,
            "acceptance_forms": {
                player_id: response_by_id[player_id].form for player_id in accepting_ids
            },
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
