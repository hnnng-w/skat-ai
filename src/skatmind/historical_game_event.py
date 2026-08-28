from dataclasses import dataclass
from typing import Any

from skatmind.historical_declarer_card_exposure_continuation import (
    HISTORICAL_DECLARER_CARD_EXPOSURE_CONTINUATION_KIND,
    HistoricalDeclarerCardExposureContinuationEvent,
    build_historical_declarer_card_exposure_continuation_event,
    build_historical_declarer_card_exposure_continuation_summary,
    build_historical_declarer_public_hand_state,
    validate_historical_declarer_card_exposure_continuation,
)
from skatmind.historical_defender_open_play_continuation import (
    HISTORICAL_DEFENDER_OPEN_PLAY_CONTINUATION_KIND,
    HistoricalDefenderOpenPlayContinuationEvent,
    build_historical_continuation_public_hand_state,
    build_historical_defender_open_play_continuation_event,
    build_historical_defender_open_play_continuation_summary,
    validate_historical_defender_open_play_continuation,
)
from skatmind.historical_play_prefix import (
    HistoricalReplayState,
    derive_historical_state_at_play_boundary_from_retained_replay,
    replay_historical_play_prefix,
)

HISTORICAL_GAME_EVENTS_SCHEMA_VERSION = 1
type HistoricalGameEvent = (
    HistoricalDefenderOpenPlayContinuationEvent | HistoricalDeclarerCardExposureContinuationEvent
)


@dataclass(frozen=True)
class HistoricalGameEventChainContext:
    """Exact chronology and public-hand state for one bounded historical chain."""

    continuation_event: HistoricalGameEvent
    continuation_play_boundary: int
    final_recorded_play_count: int
    plays_after_continuation: tuple[tuple[str, str], ...]
    final_game_end_reason: str
    terminal_shortening: bool
    continuation_replay: HistoricalReplayState
    final_replay: HistoricalReplayState


def build_historical_game_events(
    value: Any,
    *,
    game_end_reason: str,
    has_game_end: bool,
    seat_order_player_ids: tuple[str, ...],
    declarer_player_id: str,
    game_type: str,
    game_id: str,
) -> tuple[HistoricalGameEvent, ...]:
    """Builds the optional version-1 non-terminal historical event union."""
    if value is None:
        return ()
    if not isinstance(value, list) or len(value) != 1:
        raise ValueError(
            f"Historical game '{game_id}': game_events must contain exactly one event when present."
        )
    if (game_end_reason == "normal_completion") == has_game_end:
        raise ValueError(
            f"Historical game '{game_id}': game_events requires normal completion "
            "without game_end or a supported terminal reason with game_end."
        )
    raw_event = value[0]
    if not isinstance(raw_event, dict):
        raise ValueError(f"Historical game '{game_id}' game_events[0] must be an object.")
    event_kind = raw_event.get("kind")
    if event_kind == HISTORICAL_DEFENDER_OPEN_PLAY_CONTINUATION_KIND:
        return (
            build_historical_defender_open_play_continuation_event(
                raw_event,
                player_ids=seat_order_player_ids,
                declarer_player_id=declarer_player_id,
                game_id=game_id,
            ),
        )
    if event_kind == HISTORICAL_DECLARER_CARD_EXPOSURE_CONTINUATION_KIND:
        return (
            build_historical_declarer_card_exposure_continuation_event(
                raw_event,
                seat_order_player_ids=seat_order_player_ids,
                declarer_player_id=declarer_player_id,
                game_type=game_type,
                game_id=game_id,
            ),
        )
    raise ValueError(
        f"Historical game '{game_id}': unsupported historical game event kind '{event_kind}'."
    )


def build_historical_game_event_chain_context(
    record: Any,
    *,
    final_replay: HistoricalReplayState | None = None,
) -> HistoricalGameEventChainContext:
    """Validates one continuation followed by completion or terminal shortening."""
    if len(record.game_events) != 1:
        raise ValueError(
            f"Historical game '{record.game_id}': an event chain requires exactly "
            "one continuation event."
        )
    event = record.game_events[0]
    replay = final_replay or replay_historical_play_prefix(record)
    final_play_count = replay.played_card_count
    terminal_shortening = record.game_end_reason != "normal_completion"
    if terminal_shortening and final_play_count >= 30:
        raise ValueError(
            f"Historical game '{record.game_id}': a terminal shortening after a "
            "continuation must occur before all 30 plays."
        )
    if event.after_play_count > final_play_count:
        raise ValueError(
            f"Historical game '{record.game_id}': continuation boundary "
            f"{event.after_play_count} exceeds the final recorded play count "
            f"{final_play_count}."
        )

    continuation_replay = derive_historical_state_at_play_boundary_from_retained_replay(
        record,
        replay,
        event.after_play_count,
    )
    all_plays = tuple(
        (play.player_id, play.card) for trick in record.tricks for play in trick.plays
    )
    plays_after_continuation = all_plays[event.after_play_count :]
    if isinstance(event, HistoricalDefenderOpenPlayContinuationEvent):
        validate_historical_defender_open_play_continuation(
            record,
            event,
            continuation_replay,
        )
        public_hand_owner = event.exposing_defender_player_id
        final_public_hand = build_historical_continuation_public_hand_state(
            event,
            tuple(
                card
                for player_id, card in plays_after_continuation
                if player_id == public_hand_owner
            ),
        )
    else:
        validate_historical_declarer_card_exposure_continuation(
            record,
            event,
            continuation_replay,
        )
        public_hand_owner = record.declarer_player_id
        final_public_hand = build_historical_declarer_public_hand_state(
            event,
            tuple(
                card
                for player_id, card in plays_after_continuation
                if player_id == public_hand_owner
            ),
        )

    final_exact_hand = replay.remaining_hand_for(public_hand_owner)
    if set(final_public_hand) != set(final_exact_hand):
        raise ValueError(
            f"Historical game '{record.game_id}': the continuation public hand must "
            "exactly equal its owner's reconstructed remaining hand at the final "
            "recorded play boundary."
        )
    if not terminal_shortening and final_exact_hand:
        raise ValueError(
            f"Historical game '{record.game_id}': continued normal play must consume "
            "every card from the public hand."
        )

    return HistoricalGameEventChainContext(
        continuation_event=event,
        continuation_play_boundary=event.after_play_count,
        final_recorded_play_count=final_play_count,
        plays_after_continuation=plays_after_continuation,
        final_game_end_reason=record.game_end_reason,
        terminal_shortening=terminal_shortening,
        continuation_replay=continuation_replay,
        final_replay=replay,
    )


def build_serializable_historical_game_event(
    event: HistoricalGameEvent,
) -> dict[str, Any]:
    """Serializes one canonical version-1 historical event."""
    if isinstance(event, HistoricalDefenderOpenPlayContinuationEvent):
        return {
            "schema_version": event.schema_version,
            "kind": event.kind,
            "after_play_count": event.after_play_count,
            "exposing_defender_player_id": event.exposing_defender_player_id,
            "exposed_cards": list(event.exposed_cards),
            "declarer_response": event.declarer_response,
        }
    exposure = {"form": event.exposure.form}
    if event.exposure.shown_to_defender_player_id is not None:
        exposure["shown_to_defender_player_id"] = event.exposure.shown_to_defender_player_id
    return {
        "schema_version": event.schema_version,
        "kind": event.kind,
        "after_play_count": event.after_play_count,
        "exposure": exposure,
        "claimed_play_level": event.claimed_play_level,
        "defender_responses": [
            {
                "defender_player_id": response.defender_player_id,
                "response": response.response,
                "form": response.form,
            }
            for response in event.defender_responses
        ],
        "public_declarer_cards": list(event.public_declarer_cards),
    }


def build_historical_game_events_summary(
    record: Any,
    *,
    chain_context: HistoricalGameEventChainContext | None = None,
) -> dict[str, Any]:
    """Reconstructs and summarizes all supported non-terminal game events."""
    context = chain_context or build_historical_game_event_chain_context(record)
    events = []
    for event_index, event in enumerate(record.game_events, start=1):
        if isinstance(event, HistoricalDefenderOpenPlayContinuationEvent):
            event_context = validate_historical_defender_open_play_continuation(
                record,
                event,
                context.continuation_replay,
            )
            events.append(
                build_historical_defender_open_play_continuation_summary(
                    record,
                    event_context,
                    event_index=event_index,
                    final_recorded_play_count=context.final_recorded_play_count,
                    final_game_end_reason=context.final_game_end_reason,
                    terminal_shortening=context.terminal_shortening,
                )
            )
            continue
        event_context = validate_historical_declarer_card_exposure_continuation(
            record,
            event,
            context.continuation_replay,
        )
        events.append(
            build_historical_declarer_card_exposure_continuation_summary(
                record,
                event_context,
                event_index=event_index,
                final_recorded_play_count=context.final_recorded_play_count,
                final_game_end_reason=context.final_game_end_reason,
                terminal_shortening=context.terminal_shortening,
            )
        )
    return {
        "schema_version": HISTORICAL_GAME_EVENTS_SCHEMA_VERSION,
        "event_count": len(events),
        "events": events,
    }
