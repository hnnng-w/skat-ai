from dataclasses import dataclass
from typing import Any

from skat_ai.deck import get_full_deck
from skat_ai.declarer_card_exposure import (
    VALID_ACCEPTANCE_FORMS,
    VALID_CLAIMED_PLAY_LEVELS,
    VALID_EXPOSURE_FORMS,
)
from skat_ai.historical_play_prefix import HistoricalReplayState
from skat_ai.public_hand_constraint import (
    PUBLIC_HAND_VISIBILITY_SCOPE,
    canonicalize_cards,
)

HISTORICAL_DECLARER_CARD_EXPOSURE_CONTINUATION_KIND = (
    "declarer_card_exposure_continuation"
)
HISTORICAL_DECLARER_CARD_EXPOSURE_CONTINUATION_SCHEMA_VERSION = 1
CLAIMED_PLAY_LEVEL_STATUS = (
    "continuation_required_no_immediate_settlement_effect"
)
VALID_RESPONSES = {"accept", "continue"}


@dataclass(frozen=True)
class HistoricalDeclarerExposureContinuationDetails:
    """How the declarer's complete current hand was exposed."""

    form: str
    shown_to_defender_player_id: str | None = None


@dataclass(frozen=True)
class HistoricalDeclarerExposureContinuationResponse:
    """One stable defender's externally classified response."""

    defender_player_id: str
    response: str
    form: str


@dataclass(frozen=True)
class HistoricalDeclarerCardExposureContinuationEvent:
    """One timed, non-terminal declarer-card-exposure continuation event."""

    schema_version: int
    kind: str
    after_play_count: int
    exposure: HistoricalDeclarerExposureContinuationDetails
    claimed_play_level: str
    defender_responses: tuple[
        HistoricalDeclarerExposureContinuationResponse, ...
    ]
    public_declarer_cards: tuple[str, ...]


@dataclass(frozen=True)
class HistoricalDeclarerCardExposureContinuationContext:
    """Exact event-time state reconstructed from the complete historical deal."""

    event: HistoricalDeclarerCardExposureContinuationEvent
    replay: HistoricalReplayState


def _require_exact_fields(
    value: dict[str, Any], required_fields: set[str], field_name: str
) -> None:
    missing_fields = sorted(required_fields - value.keys())
    if missing_fields:
        raise ValueError(f"{field_name} is missing required fields: {missing_fields}.")
    unexpected_fields = sorted(value.keys() - required_fields)
    if unexpected_fields:
        raise ValueError(f"{field_name} has unsupported fields: {unexpected_fields}.")


def _require_stable_defender_id(
    value: Any,
    *,
    field_name: str,
    declarer_player_id: str,
    seat_order_player_ids: tuple[str, ...],
) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(
            f"{field_name} must be a non-empty, non-padded stable player ID."
        )
    if value in {"me", "left", "right"}:
        raise ValueError(f"{field_name} must not use a relative player identity.")
    if value not in seat_order_player_ids or value == declarer_player_id:
        raise ValueError(f"{field_name} must identify one exact stable defender ID.")
    return value


def _build_exposure(
    value: Any,
    *,
    field_name: str,
    declarer_player_id: str,
    seat_order_player_ids: tuple[str, ...],
) -> HistoricalDeclarerExposureContinuationDetails:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be an object.")
    form = value.get("form")
    if form not in VALID_EXPOSURE_FORMS:
        raise ValueError(f"{field_name}.form must be 'laid_open' or 'shown_to_defender'.")
    required_fields = {"form"}
    if form == "shown_to_defender":
        required_fields.add("shown_to_defender_player_id")
    _require_exact_fields(value, required_fields, field_name)
    shown_to_defender_player_id = None
    if form == "shown_to_defender":
        shown_to_defender_player_id = _require_stable_defender_id(
            value["shown_to_defender_player_id"],
            field_name=f"{field_name}.shown_to_defender_player_id",
            declarer_player_id=declarer_player_id,
            seat_order_player_ids=seat_order_player_ids,
        )
    return HistoricalDeclarerExposureContinuationDetails(
        form=form,
        shown_to_defender_player_id=shown_to_defender_player_id,
    )


def build_historical_declarer_card_exposure_continuation_event(
    value: Any,
    *,
    seat_order_player_ids: tuple[str, ...],
    declarer_player_id: str,
    game_type: str,
    game_id: str,
) -> HistoricalDeclarerCardExposureContinuationEvent:
    """Builds the strict version-1 historical continuation event input."""
    field_name = f"Historical game '{game_id}' game_events[0]"
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be an object.")
    _require_exact_fields(
        value,
        {
            "schema_version",
            "kind",
            "after_play_count",
            "exposure",
            "claimed_play_level",
            "defender_responses",
            "public_declarer_cards",
        },
        field_name,
    )

    schema_version = value["schema_version"]
    if (
        isinstance(schema_version, bool)
        or not isinstance(schema_version, int)
        or schema_version
        != HISTORICAL_DECLARER_CARD_EXPOSURE_CONTINUATION_SCHEMA_VERSION
    ):
        raise ValueError(f"{field_name}.schema_version must be exactly 1.")
    kind = value["kind"]
    if kind != HISTORICAL_DECLARER_CARD_EXPOSURE_CONTINUATION_KIND:
        raise ValueError(
            f"{field_name}.kind must be "
            f"'{HISTORICAL_DECLARER_CARD_EXPOSURE_CONTINUATION_KIND}'."
        )
    after_play_count = value["after_play_count"]
    if (
        isinstance(after_play_count, bool)
        or not isinstance(after_play_count, int)
        or not 0 <= after_play_count <= 29
    ):
        raise ValueError(f"{field_name}.after_play_count must be an integer from 0 to 29.")

    exposure = _build_exposure(
        value["exposure"],
        field_name=f"{field_name}.exposure",
        declarer_player_id=declarer_player_id,
        seat_order_player_ids=seat_order_player_ids,
    )
    claimed_play_level = value["claimed_play_level"]
    if claimed_play_level not in VALID_CLAIMED_PLAY_LEVELS:
        raise ValueError(
            f"{field_name}.claimed_play_level must be 'simple', 'schneider', or 'schwarz'."
        )
    if game_type == "null" and claimed_play_level != "simple":
        raise ValueError(
            "Historical Null declarer card exposure continuation requires "
            "claimed_play_level='simple'."
        )

    raw_responses = value["defender_responses"]
    if not isinstance(raw_responses, list) or len(raw_responses) != 2:
        raise ValueError(
            f"{field_name}.defender_responses must contain exactly two defender responses."
        )
    responses_by_player = {}
    for index, raw_response in enumerate(raw_responses):
        response_field = f"{field_name}.defender_responses[{index}]"
        if not isinstance(raw_response, dict):
            raise ValueError(f"{response_field} must be an object.")
        _require_exact_fields(
            raw_response,
            {"defender_player_id", "response", "form"},
            response_field,
        )
        defender_player_id = _require_stable_defender_id(
            raw_response["defender_player_id"],
            field_name=f"{response_field}.defender_player_id",
            declarer_player_id=declarer_player_id,
            seat_order_player_ids=seat_order_player_ids,
        )
        if defender_player_id in responses_by_player:
            raise ValueError(
                f"{field_name}.defender_responses must identify each defender exactly once."
            )
        response = raw_response["response"]
        if response not in VALID_RESPONSES:
            raise ValueError(f"{response_field}.response must be 'accept' or 'continue'.")
        response_form = raw_response["form"]
        if response_form not in VALID_ACCEPTANCE_FORMS:
            raise ValueError(
                f"{response_field}.form must be 'explicit' or 'unambiguous_conduct'."
            )
        responses_by_player[defender_player_id] = (
            HistoricalDeclarerExposureContinuationResponse(
                defender_player_id=defender_player_id,
                response=response,
                form=response_form,
            )
        )
    defender_ids = {
        player_id
        for player_id in seat_order_player_ids
        if player_id != declarer_player_id
    }
    if set(responses_by_player) != defender_ids:
        raise ValueError(
            f"{field_name}.defender_responses must identify each stable defender exactly once."
        )
    ordered_responses = tuple(
        responses_by_player[player_id]
        for player_id in seat_order_player_ids
        if player_id in responses_by_player
    )
    if all(response.response == "accept" for response in ordered_responses):
        raise ValueError(
            "Unanimous defender acceptance must use terminal historical "
            "game_end_reason='declarer_card_exposure'."
        )

    raw_cards = value["public_declarer_cards"]
    if not isinstance(raw_cards, list) or not 1 <= len(raw_cards) <= 10:
        raise ValueError(
            f"{field_name}.public_declarer_cards must contain between 1 and 10 cards."
        )
    valid_cards = set(get_full_deck())
    invalid_cards = [
        card for card in raw_cards if not isinstance(card, str) or card not in valid_cards
    ]
    if invalid_cards:
        raise ValueError(
            f"{field_name}.public_declarer_cards contains invalid cards: {invalid_cards}."
        )
    if len(raw_cards) != len(set(raw_cards)):
        raise ValueError(f"{field_name}.public_declarer_cards contains duplicate cards.")

    return HistoricalDeclarerCardExposureContinuationEvent(
        schema_version=schema_version,
        kind=kind,
        after_play_count=after_play_count,
        exposure=exposure,
        claimed_play_level=claimed_play_level,
        defender_responses=ordered_responses,
        public_declarer_cards=canonicalize_cards(tuple(raw_cards)),
    )


def build_historical_declarer_public_hand_state(
    event: HistoricalDeclarerCardExposureContinuationEvent,
    played_cards_after_event: tuple[str, ...],
) -> tuple[str, ...]:
    """Removes only actually played cards from the permanently open hand."""
    played_cards = set(played_cards_after_event)
    return tuple(
        card for card in event.public_declarer_cards if card not in played_cards
    )


def validate_historical_declarer_card_exposure_continuation(
    record: Any,
    event: HistoricalDeclarerCardExposureContinuationEvent,
    replay: HistoricalReplayState,
) -> HistoricalDeclarerCardExposureContinuationContext:
    """Confirms the exact current declarer hand at the supplied boundary."""
    declarer_hand = replay.remaining_hand_for(record.declarer_player_id)
    if not declarer_hand:
        raise ValueError(
            f"Historical game '{record.game_id}': the declarer must retain at least "
            "one card at the event boundary."
        )
    if set(event.public_declarer_cards) != set(declarer_hand):
        raise ValueError(
            f"Historical game '{record.game_id}': public_declarer_cards must exactly "
            "equal the declarer's reconstructed complete hand at the event boundary."
        )
    return HistoricalDeclarerCardExposureContinuationContext(event=event, replay=replay)


def build_historical_declarer_card_exposure_continuation_summary(
    record: Any,
    context: HistoricalDeclarerCardExposureContinuationContext,
    *,
    event_index: int,
) -> dict[str, Any]:
    """Builds the privacy-safe, non-adjudicating historical event summary."""
    event = context.event
    replay = context.replay
    responses = [
        {
            "defender_player_id": response.defender_player_id,
            "response": response.response,
            "form": response.form,
        }
        for response in event.defender_responses
    ]
    summary = {
        "event_index": event_index,
        "kind": event.kind,
        "rule_sections": ["4.4.4"],
        "after_play_count": event.after_play_count,
        "after_completed_trick_count": len(replay.completed_tricks),
        "event_during_incomplete_trick": replay.current_trick is not None,
        "next_player_id": replay.next_player_id,
        "declarer_player_id": record.declarer_player_id,
        "exposure_form": event.exposure.form,
        "defender_responses": responses,
        "continuing_defender_player_ids": [
            response["defender_player_id"]
            for response in responses
            if response["response"] == "continue"
        ],
        "accepting_defender_player_ids": [
            response["defender_player_id"]
            for response in responses
            if response["response"] == "accept"
        ],
        "unanimous_acceptance": False,
        "continuation_required": True,
        "public_declarer_cards": list(event.public_declarer_cards),
        "public_declarer_card_count": len(event.public_declarer_cards),
        "card_reconciliation": "confirmed",
        "cards_remain_in_declarer_hand": True,
        "hand_physically_open": True,
        "visibility_scope": PUBLIC_HAND_VISIBILITY_SCOPE,
        "claimed_play_level": event.claimed_play_level,
        "claimed_play_level_status": CLAIMED_PLAY_LEVEL_STATUS,
        "first_affected_decision_index": event.after_play_count + 1,
        "actual_plays_after_event": 30 - event.after_play_count,
        "exact_proof_applied": False,
        "game_end_applied": False,
        "settlement_applied": False,
        "final_game_end_reason": "normal_completion",
        "final_outcome_source": "actual_continued_play",
    }
    if event.exposure.shown_to_defender_player_id is not None:
        summary["shown_to_defender_player_id"] = (
            event.exposure.shown_to_defender_player_id
        )
    return summary
