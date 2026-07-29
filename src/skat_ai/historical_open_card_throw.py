from typing import Any

from skat_ai.final_settlement import build_final_settlement_summary
from skat_ai.game_result import build_game_result_summary_from_score_summary
from skat_ai.game_value import build_game_value_summary
from skat_ai.historical_game_end import HistoricalOpenCardThrow
from skat_ai.historical_play_prefix import (
    HistoricalReplayState,
    build_serializable_incomplete_trick,
)
from skat_ai.historical_player_mapping import build_historical_player_mapping
from skat_ai.matador_inference import JACK_ORDER
from skat_ai.open_card_throw import (
    OpenCardThrow,
    OpenCardThrowContext,
    adjudicate_open_card_throw,
)
from skat_ai.overbid import build_overbid_summary
from skat_ai.rules import get_card_points
from skat_ai.theoretical_level_exclusion import JackOwnershipEvidence


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
    current_points = (
        sum(get_card_points(card) for _, card in replay.current_trick.plays)
        if replay.current_trick is not None
        else 0
    )
    remaining_points = sum(
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
        "unresolved_current_trick_points": current_points,
        "unresolved_remaining_hand_points": remaining_points,
        "total_unresolved_points": current_points + remaining_points,
        "total_card_points": 120,
    }


def _build_exact_jack_evidence(
    record: Any,
    replay: HistoricalReplayState,
    throwing_player_id: str,
) -> tuple[JackOwnershipEvidence, ...]:
    ownership: dict[str, str] = {}
    sources: dict[str, set[str]] = {card: set() for card in JACK_ORDER}

    def add(card: str, player_id: str | None, source: str) -> None:
        if card not in JACK_ORDER:
            return
        party = (
            "skat"
            if player_id is None
            else "declarer"
            if player_id == record.declarer_player_id
            else "defenders"
        )
        existing = ownership.get(card)
        if existing is not None and existing != party:
            raise ValueError(
                f"Historical game '{record.game_id}': exact jack ownership for "
                f"{card} is contradictory."
            )
        ownership[card] = party
        sources[card].add(source)

    for player_id, cards in replay.remaining_hands:
        source = (
            "thrown_cards"
            if player_id == throwing_player_id
            else "historical_reconstructed_hand"
        )
        for card in cards:
            add(card, player_id, source)
    for trick in replay.completed_tricks:
        for player_id, card in trick.plays:
            add(card, player_id, "completed_tricks")
    if replay.current_trick is not None:
        for player_id, card in replay.current_trick.plays:
            add(card, player_id, "current_trick")
    final_skat = record.skat if record.declaration.hand_game else record.discarded_cards
    for card in final_skat:
        add(card, None, "skat")

    return tuple(
        JackOwnershipEvidence(
            card=card,
            ownership=ownership.get(card, "unknown"),
            sources=tuple(sorted(sources[card])),
        )
        for card in JACK_ORDER
    )


def adjudicate_historical_open_card_throw(
    record: Any,
    replay: HistoricalReplayState,
) -> dict[str, Any]:
    """Adapts exact historical facts to the shared ISkO 4.4.6 adjudicator."""
    event = record.game_end
    if not isinstance(event, HistoricalOpenCardThrow):
        raise ValueError("Historical open-card-throw adjudication requires its event.")
    completed_trick_count = len(replay.completed_tricks)
    if completed_trick_count >= 10:
        raise ValueError(
            f"Historical game '{record.game_id}': at least one trick must remain "
            "unresolved for open card throw."
        )
    reconstructed_hand = replay.remaining_hand_for(event.throwing_player_id)
    if not reconstructed_hand:
        raise ValueError(
            f"Historical game '{record.game_id}': the throwing player must have at "
            "least one remaining hand card."
        )
    if set(event.thrown_cards) != set(reconstructed_hand):
        raise ValueError(
            f"Historical game '{record.game_id}': thrown_cards must exactly equal the "
            "throwing player's reconstructed complete current hand."
        )

    mapping = build_historical_player_mapping(record)
    throwing_party = (
        "declarer"
        if event.throwing_player_id == record.declarer_player_id
        else "defenders"
    )
    opposing_party = "defenders" if throwing_party == "declarer" else "declarer"
    observed_tricks = {"declarer": 0, "defenders": 0}
    for trick in replay.completed_tricks:
        observed_tricks[trick.winner_side] += 1
    remaining_trick_count = 10 - completed_trick_count
    assigned_tricks = {"declarer": 0, "defenders": 0}
    assigned_tricks[opposing_party] = remaining_trick_count
    final_tricks = {
        party: observed_tricks[party] + assigned_tricks[party]
        for party in observed_tricks
    }
    if sum(final_tricks.values()) != 10:
        raise ValueError(
            f"Historical game '{record.game_id}': completed and assigned tricks must "
            "total ten."
        )
    context = OpenCardThrowContext(
        declarer_player="me",
        throwing_party=throwing_party,
        opposing_party=opposing_party,
        joint_liability=throwing_party == "defenders",
        card_reconciliation="confirmed",
        remaining_trick_count=remaining_trick_count,
        assigned_card_count=remaining_trick_count * 3,
        observed_trick_counts=tuple(observed_tricks.items()),
        rule_assigned_trick_counts=tuple(assigned_tricks.items()),
        final_trick_counts=tuple(final_tricks.items()),
        jack_ownership_evidence=_build_exact_jack_evidence(
            record, replay, event.throwing_player_id
        ),
    )
    flat_event = OpenCardThrow(
        schema_version=event.schema_version,
        kind=event.kind,
        throwing_player=mapping.to_flat(event.throwing_player_id),
        thrown_cards=event.thrown_cards,
        statement_classification=event.statement_classification,
    )
    completed_tricks = [
        {
            "cards": [card for _, card in trick.plays],
            "winner_role": trick.winner_side,
        }
        for trick in replay.completed_tricks
    ]
    points = _build_point_accounting(record, replay)
    if (
        points["observed_declarer_points"]
        + points["observed_defender_points"]
        + points["total_unresolved_points"]
        != 120
    ):
        raise ValueError(
            f"Historical game '{record.game_id}': observed and unresolved card "
            "points must total 120."
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
    adjudication = adjudicate_open_card_throw(
        flat_event,
        context,
        raw_result,
        game_value_summary,
        overbid_summary,
        completed_tricks,
    )
    game_result_summary = adjudication.game_result_summary
    settlement = build_final_settlement_summary(
        game_value_summary,
        game_result_summary,
        overbid_summary,
        completed_tricks,
    )
    if not settlement["is_complete"]:
        raise ValueError(
            f"Historical game '{record.game_id}': final settlement is incomplete: "
            f"{settlement['missing_inputs']}."
        )

    flat_end = adjudication.game_shortening_summary
    end_summary = {
        key: value
        for key, value in flat_end.items()
        if key != "throwing_player"
    }
    end_summary.update(
        {
            "declarer_player_id": record.declarer_player_id,
            "throwing_player_id": event.throwing_player_id,
            "event_after_play_count": replay.played_card_count,
            "event_after_completed_trick_count": completed_trick_count,
            "event_during_incomplete_trick": replay.current_trick is not None,
        }
    )
    points.update(
        {
            "assigned_declarer_points": game_result_summary["rule_assigned_points"][
                "declarer"
            ],
            "assigned_defender_points": game_result_summary["rule_assigned_points"][
                "defenders"
            ],
            "final_declarer_points": game_result_summary["declarer_points"],
            "final_defender_points": game_result_summary["defender_points"],
        }
    )
    effective_schwarz = game_result_summary["effective_schwarz_status"]
    current_cards = (
        [card for _, card in replay.current_trick.plays]
        if replay.current_trick is not None
        else []
    )
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
            "current_trick_card_count": len(current_cards),
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
        "final_settlement_summary": settlement,
    }
    if replay.current_trick is not None:
        result["incomplete_current_trick"] = build_serializable_incomplete_trick(
            replay.current_trick
        )
    return result
