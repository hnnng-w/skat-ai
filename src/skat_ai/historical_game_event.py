from typing import Any

from skat_ai.historical_declarer_card_exposure_continuation import (
    HISTORICAL_DECLARER_CARD_EXPOSURE_CONTINUATION_KIND,
    HistoricalDeclarerCardExposureContinuationEvent,
    build_historical_declarer_card_exposure_continuation_event,
    build_historical_declarer_card_exposure_continuation_summary,
    build_historical_declarer_public_hand_state,
    validate_historical_declarer_card_exposure_continuation,
)
from skat_ai.historical_defender_open_play_continuation import (
    HISTORICAL_DEFENDER_OPEN_PLAY_CONTINUATION_KIND,
    HistoricalDefenderOpenPlayContinuationEvent,
    build_historical_continuation_public_hand_state,
    build_historical_defender_open_play_continuation_event,
    build_historical_defender_open_play_continuation_summary,
    validate_historical_defender_open_play_continuation,
)
from skat_ai.historical_play_prefix import replay_historical_state_at_play_boundary

HISTORICAL_GAME_EVENTS_SCHEMA_VERSION = 1
type HistoricalGameEvent = (
    HistoricalDefenderOpenPlayContinuationEvent
    | HistoricalDeclarerCardExposureContinuationEvent
)


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
            f"Historical game '{game_id}': game_events must contain exactly one "
            "event when present."
        )
    if game_end_reason != "normal_completion" or has_game_end:
        raise ValueError(
            f"Historical game '{game_id}': game_events version 1 requires "
            "game_end_reason='normal_completion' and no terminal game_end."
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
        f"Historical game '{game_id}': unsupported historical game event kind "
        f"'{event_kind}'."
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
        exposure["shown_to_defender_player_id"] = (
            event.exposure.shown_to_defender_player_id
        )
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


def build_historical_game_events_summary(record: Any) -> dict[str, Any]:
    """Reconstructs and summarizes all supported non-terminal game events."""
    events = []
    for event_index, event in enumerate(record.game_events, start=1):
        replay = replay_historical_state_at_play_boundary(
            record,
            event.after_play_count,
        )
        actual_plays = tuple(
            play.card for trick in record.tricks for play in trick.plays
        )
        if isinstance(event, HistoricalDefenderOpenPlayContinuationEvent):
            context = validate_historical_defender_open_play_continuation(
                record,
                event,
                replay,
            )
            final_public_hand = build_historical_continuation_public_hand_state(
                event,
                actual_plays[event.after_play_count :],
            )
            if final_public_hand:
                raise ValueError(
                    f"Historical game '{record.game_id}': continued normal play must "
                    "consume every card from the exposed defender hand."
                )
            events.append(
                build_historical_defender_open_play_continuation_summary(
                    record,
                    context,
                    event_index=event_index,
                )
            )
            continue
        context = validate_historical_declarer_card_exposure_continuation(
            record,
            event,
            replay,
        )
        final_public_hand = build_historical_declarer_public_hand_state(
            event,
            actual_plays[event.after_play_count :],
        )
        if final_public_hand:
            raise ValueError(
                f"Historical game '{record.game_id}': continued normal play must "
                "consume every card from the public declarer hand."
            )
        events.append(
            build_historical_declarer_card_exposure_continuation_summary(
                record,
                context,
                event_index=event_index,
            )
        )
    return {
        "schema_version": HISTORICAL_GAME_EVENTS_SCHEMA_VERSION,
        "event_count": len(events),
        "events": events,
    }
