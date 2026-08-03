from dataclasses import dataclass
from typing import Any

from skat_ai.deck import get_full_deck
from skat_ai.historical_play_prefix import HistoricalReplayState
from skat_ai.public_hand_constraint import (
    PUBLIC_HAND_VISIBILITY_SCOPE,
    canonicalize_cards,
)
from skat_ai.rules import get_card_points

HISTORICAL_DEFENDER_OPEN_PLAY_CONTINUATION_KIND = (
    "defender_open_play_continuation"
)
HISTORICAL_DEFENDER_OPEN_PLAY_CONTINUATION_SCHEMA_VERSION = 1
HISTORICAL_DEFENDER_OPEN_PLAY_CONTINUATION_RESPONSE = "request_continued_play"


@dataclass(frozen=True)
class HistoricalDefenderOpenPlayContinuationEvent:
    """One timed, non-terminal defender-open-play continuation event."""

    schema_version: int
    kind: str
    after_play_count: int
    exposing_defender_player_id: str
    exposed_cards: tuple[str, ...]
    declarer_response: str


@dataclass(frozen=True)
class HistoricalDefenderOpenPlayContinuationContext:
    """Exact event-time state reconstructed from the complete historical deal."""

    event: HistoricalDefenderOpenPlayContinuationEvent
    replay: HistoricalReplayState
    non_exposing_defender_player_id: str
    observed_declarer_points: int
    observed_defender_points: int


def build_historical_continuation_public_hand_state(
    event: HistoricalDefenderOpenPlayContinuationEvent,
    played_cards_after_event: tuple[str, ...],
) -> tuple[str, ...]:
    """Removes actually played cards from the permanently known defender hand."""
    played_cards = set(played_cards_after_event)
    return tuple(card for card in event.exposed_cards if card not in played_cards)


def _require_identifier(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{field_name} must be a non-empty, non-padded string.")
    return value


def build_historical_defender_open_play_continuation_event(
    value: Any,
    *,
    player_ids: tuple[str, ...],
    declarer_player_id: str,
    game_id: str,
) -> HistoricalDefenderOpenPlayContinuationEvent:
    """Builds the strict version-1 continuation event input."""
    field_name = f"Historical game '{game_id}' game_events[0]"
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be an object.")
    required_fields = {
        "schema_version",
        "kind",
        "after_play_count",
        "exposing_defender_player_id",
        "exposed_cards",
        "declarer_response",
    }
    missing_fields = sorted(required_fields - value.keys())
    if missing_fields:
        raise ValueError(f"{field_name} is missing required fields: {missing_fields}.")
    unexpected_fields = sorted(value.keys() - required_fields)
    if unexpected_fields:
        raise ValueError(f"{field_name} has unsupported fields: {unexpected_fields}.")

    schema_version = value["schema_version"]
    if (
        isinstance(schema_version, bool)
        or not isinstance(schema_version, int)
        or schema_version != HISTORICAL_DEFENDER_OPEN_PLAY_CONTINUATION_SCHEMA_VERSION
    ):
        raise ValueError(f"{field_name}.schema_version must be exactly 1.")
    kind = value["kind"]
    if kind != HISTORICAL_DEFENDER_OPEN_PLAY_CONTINUATION_KIND:
        raise ValueError(
            f"{field_name}.kind must be "
            f"'{HISTORICAL_DEFENDER_OPEN_PLAY_CONTINUATION_KIND}'."
        )

    after_play_count = value["after_play_count"]
    if (
        isinstance(after_play_count, bool)
        or not isinstance(after_play_count, int)
        or not 0 <= after_play_count <= 29
    ):
        raise ValueError(f"{field_name}.after_play_count must be an integer from 0 to 29.")

    exposing_defender_player_id = _require_identifier(
        value["exposing_defender_player_id"],
        f"{field_name}.exposing_defender_player_id",
    )
    if exposing_defender_player_id in {"me", "left", "right"}:
        raise ValueError(
            f"{field_name}.exposing_defender_player_id must use a stable identity, "
            "not a relative identity."
        )
    if exposing_defender_player_id not in player_ids:
        raise ValueError(
            f"{field_name}.exposing_defender_player_id must reference an exact "
            "stable participant."
        )
    if exposing_defender_player_id == declarer_player_id:
        raise ValueError(
            f"{field_name}.exposing_defender_player_id must identify a defender, "
            "not the declarer."
        )

    raw_cards = value["exposed_cards"]
    if not isinstance(raw_cards, list) or not 1 <= len(raw_cards) <= 10:
        raise ValueError(f"{field_name}.exposed_cards must contain between 1 and 10 cards.")
    valid_cards = set(get_full_deck())
    invalid_cards = [
        card for card in raw_cards if not isinstance(card, str) or card not in valid_cards
    ]
    if invalid_cards:
        raise ValueError(f"{field_name}.exposed_cards contains invalid cards: {invalid_cards}.")
    if len(raw_cards) != len(set(raw_cards)):
        raise ValueError(f"{field_name}.exposed_cards contains duplicate cards.")

    declarer_response = value["declarer_response"]
    if declarer_response == "accept_adjudication":
        raise ValueError(
            "Accepted historical defender-open-play adjudication must use the terminal "
            "game_end_reason='defender_open_play' contract."
        )
    if declarer_response != HISTORICAL_DEFENDER_OPEN_PLAY_CONTINUATION_RESPONSE:
        raise ValueError(
            f"{field_name}.declarer_response must be "
            f"'{HISTORICAL_DEFENDER_OPEN_PLAY_CONTINUATION_RESPONSE}'."
        )

    return HistoricalDefenderOpenPlayContinuationEvent(
        schema_version=schema_version,
        kind=kind,
        after_play_count=after_play_count,
        exposing_defender_player_id=exposing_defender_player_id,
        exposed_cards=canonicalize_cards(tuple(raw_cards)),
        declarer_response=declarer_response,
    )


def validate_historical_defender_open_play_continuation(
    record: Any,
    event: HistoricalDefenderOpenPlayContinuationEvent,
    replay: HistoricalReplayState,
) -> HistoricalDefenderOpenPlayContinuationContext:
    """Confirms the exact exposing hand and derives the event-time context."""
    exposing_hand = replay.remaining_hand_for(event.exposing_defender_player_id)
    if not exposing_hand:
        raise ValueError(
            f"Historical game '{record.game_id}': the exposing defender must retain "
            "at least one card at the event boundary."
        )
    if set(event.exposed_cards) != set(exposing_hand):
        raise ValueError(
            f"Historical game '{record.game_id}': exposed_cards must exactly equal the "
            "exposing defender's reconstructed complete hand at the event boundary."
        )

    non_exposing_defender_player_id = next(
        player.player_id
        for player in record.players
        if player.player_id
        not in {record.declarer_player_id, event.exposing_defender_player_id}
    )
    final_skat = record.skat if record.declaration.hand_game else record.discarded_cards
    observed_declarer_points = sum(get_card_points(card) for card in final_skat)
    observed_defender_points = 0
    for trick in replay.completed_tricks:
        if trick.winner_side == "declarer":
            observed_declarer_points += trick.trick_points
        else:
            observed_defender_points += trick.trick_points

    return HistoricalDefenderOpenPlayContinuationContext(
        event=event,
        replay=replay,
        non_exposing_defender_player_id=non_exposing_defender_player_id,
        observed_declarer_points=observed_declarer_points,
        observed_defender_points=observed_defender_points,
    )


def build_historical_defender_open_play_continuation_summary(
    record: Any,
    context: HistoricalDefenderOpenPlayContinuationContext,
    *,
    event_index: int,
    final_recorded_play_count: int = 30,
    final_game_end_reason: str = "normal_completion",
    terminal_shortening: bool = False,
) -> dict[str, Any]:
    """Builds the privacy-safe, non-adjudicating historical event summary."""
    event = context.event
    replay = context.replay
    return {
        "event_index": event_index,
        "kind": event.kind,
        "rule_sections": ["4.4.5", "4.1.6"],
        "after_play_count": event.after_play_count,
        "after_completed_trick_count": len(replay.completed_tricks),
        "event_during_incomplete_trick": replay.current_trick is not None,
        "next_player_id": replay.next_player_id,
        "declarer_player_id": record.declarer_player_id,
        "exposing_defender_player_id": event.exposing_defender_player_id,
        "non_exposing_defender_player_id": context.non_exposing_defender_player_id,
        "exposed_cards": list(event.exposed_cards),
        "exposed_card_count": len(event.exposed_cards),
        "card_reconciliation": "confirmed",
        "declarer_response": event.declarer_response,
        "cards_returned_to_hand": True,
        "hand_physically_open": False,
        "visibility_scope": PUBLIC_HAND_VISIBILITY_SCOPE,
        "rest_trick_claim": "all_remaining_tricks",
        "rest_trick_claim_status": "not_adjudicated_due_to_continued_play",
        "continued_play_effect": "open_play_consequence_disregarded",
        "first_affected_decision_index": event.after_play_count + 1,
        "actual_plays_after_event": final_recorded_play_count - event.after_play_count,
        "exact_proof_applied": False,
        "game_end_applied": False,
        "settlement_applied": False,
        "final_game_end_reason": final_game_end_reason,
        "final_outcome_source": (
            "subsequent_terminal_shortening"
            if terminal_shortening
            else "actual_continued_play"
        ),
    }
