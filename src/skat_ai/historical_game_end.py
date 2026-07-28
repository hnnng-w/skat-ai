from dataclasses import dataclass
from typing import Any

from skat_ai.deck import get_full_deck
from skat_ai.declarer_card_exposure import (
    DECLARER_CARD_EXPOSURE_KIND,
    VALID_ACCEPTANCE_FORMS,
    VALID_CLAIMED_PLAY_LEVELS,
    VALID_EXPOSURE_FORMS,
)
from skat_ai.declarer_concession import (
    DECLARER_CONCESSION_KIND,
    VALID_CONSENT_STATUSES,
    is_strict_integer,
)
from skat_ai.defender_concession import (
    DEFENDER_CONCESSION_KIND,
    VALID_CONCESSION_FORMS,
)
from skat_ai.defender_open_play import DEFENDER_OPEN_PLAY_KIND

HISTORICAL_GAME_END_SCHEMA_VERSION = 1
HISTORICAL_NORMAL_COMPLETION = "normal_completion"
HISTORICAL_DECLARER_CONCESSION = DECLARER_CONCESSION_KIND
HISTORICAL_DEFENDER_CONCESSION = DEFENDER_CONCESSION_KIND
HISTORICAL_DECLARER_CARD_EXPOSURE = DECLARER_CARD_EXPOSURE_KIND
HISTORICAL_DEFENDER_OPEN_PLAY = DEFENDER_OPEN_PLAY_KIND
HISTORICAL_GAME_END_REASONS = {
    HISTORICAL_NORMAL_COMPLETION,
    HISTORICAL_DECLARER_CONCESSION,
    HISTORICAL_DEFENDER_CONCESSION,
    HISTORICAL_DECLARER_CARD_EXPOSURE,
    HISTORICAL_DEFENDER_OPEN_PLAY,
}


@dataclass(frozen=True)
class HistoricalDefenderConsent:
    """Stable defender identities that consented to a historical concession."""

    status: str
    consenting_defender_player_ids: tuple[str, ...]


@dataclass(frozen=True)
class HistoricalDeclarerConcession:
    """Version-1 historical declarer-concession event."""

    schema_version: int
    kind: str
    declarer_hand_cards_remaining: int
    defender_consent: HistoricalDefenderConsent


@dataclass(frozen=True)
class HistoricalDefenderConcession:
    """Version-1 historical defender-concession event."""

    schema_version: int
    kind: str
    conceding_defender_player_id: str
    concession_form: str


@dataclass(frozen=True)
class HistoricalDeclarerCardExposureDetails:
    """Exact remaining declarer cards exposed in a historical game."""

    form: str
    exposed_cards: tuple[str, ...]
    shown_to_defender_player_id: str | None


@dataclass(frozen=True)
class HistoricalDefenderExposureResponse:
    """One stable defender's accepted historical exposure response."""

    defender_player_id: str
    response: str
    form: str


@dataclass(frozen=True)
class HistoricalDeclarerCardExposure:
    """Version-1 unanimously accepted historical declarer-card exposure."""

    schema_version: int
    kind: str
    exposure: HistoricalDeclarerCardExposureDetails
    claimed_play_level: str
    defender_responses: tuple[HistoricalDefenderExposureResponse, ...]


@dataclass(frozen=True)
class HistoricalDefenderOpenPlay:
    """Version-1 terminal historical defender-open-play event."""

    schema_version: int
    kind: str
    exposing_defender_player_id: str
    exposed_cards: tuple[str, ...]
    declarer_response: str


type HistoricalGameEnd = (
    HistoricalDeclarerConcession
    | HistoricalDefenderConcession
    | HistoricalDeclarerCardExposure
    | HistoricalDefenderOpenPlay
)


def _require_exact_fields(
    data: dict[str, Any], required_fields: set[str], field_name: str
) -> None:
    missing_fields = sorted(required_fields - data.keys())
    if missing_fields:
        raise ValueError(f"{field_name} is missing required fields: {missing_fields}.")
    unexpected_fields = sorted(data.keys() - required_fields)
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


def build_historical_game_end(
    value: Any,
    *,
    game_end_reason: str,
    declarer_player_id: str,
    seat_order_player_ids: tuple[str, ...],
    game_id: str,
) -> HistoricalGameEnd | None:
    """Builds the versioned historical end-event union and validates stable IDs."""
    field_name = f"Historical game '{game_id}' game_end"
    if game_end_reason not in HISTORICAL_GAME_END_REASONS:
        raise ValueError(
            f"Historical game '{game_id}': unsupported game_end_reason "
            f"'{game_end_reason}'."
        )
    if game_end_reason == HISTORICAL_NORMAL_COMPLETION:
        if value is not None:
            raise ValueError(
                f"Historical game '{game_id}': game_end must be absent for "
                "game_end_reason='normal_completion'."
            )
        return None
    if value is None:
        raise ValueError(
            f"Historical game '{game_id}': game_end is required for "
            f"game_end_reason='{game_end_reason}'."
        )
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be an object.")

    if game_end_reason == HISTORICAL_DEFENDER_OPEN_PLAY:
        relative_player_ids = sorted(
            set(seat_order_player_ids).intersection({"me", "left", "right"})
        )
        if relative_player_ids:
            raise ValueError(
                f"{field_name} requires stable historical player IDs and must not "
                f"use relative identities: {relative_player_ids}."
            )
        _require_exact_fields(
            value,
            {
                "schema_version",
                "kind",
                "exposing_defender_player_id",
                "exposed_cards",
                "declarer_response",
            },
            field_name,
        )
        if not is_strict_integer(value["schema_version"]) or value["schema_version"] != 1:
            raise ValueError(f"{field_name}.schema_version must be exactly 1.")
        if value["kind"] != HISTORICAL_DEFENDER_OPEN_PLAY:
            raise ValueError(
                f"{field_name}.kind must match game_end_reason "
                f"'{HISTORICAL_DEFENDER_OPEN_PLAY}'."
            )
        exposing_defender_player_id = _require_stable_defender_id(
            value["exposing_defender_player_id"],
            field_name=f"{field_name}.exposing_defender_player_id",
            declarer_player_id=declarer_player_id,
            seat_order_player_ids=seat_order_player_ids,
        )
        raw_cards = value["exposed_cards"]
        if not isinstance(raw_cards, list):
            raise ValueError(f"{field_name}.exposed_cards must be an array.")
        if not 1 <= len(raw_cards) <= 5:
            raise ValueError(
                f"{field_name}.exposed_cards must contain between 1 and 5 cards."
            )
        valid_cards = set(get_full_deck())
        invalid_cards = [
            card for card in raw_cards if not isinstance(card, str) or card not in valid_cards
        ]
        if invalid_cards:
            raise ValueError(
                f"{field_name}.exposed_cards contains invalid cards: {invalid_cards}."
            )
        if len(raw_cards) != len(set(raw_cards)):
            raise ValueError(f"{field_name}.exposed_cards must not contain duplicates.")
        card_order = {card: index for index, card in enumerate(get_full_deck())}
        exposed_cards = tuple(sorted(raw_cards, key=card_order.__getitem__))
        declarer_response = value["declarer_response"]
        if declarer_response == "request_continued_play":
            raise ValueError(
                "Historical defender-open-play continuation remains separate future work."
            )
        if declarer_response != "accept_adjudication":
            raise ValueError(
                f"{field_name}.declarer_response must be 'accept_adjudication'."
            )
        return HistoricalDefenderOpenPlay(
            schema_version=HISTORICAL_GAME_END_SCHEMA_VERSION,
            kind=HISTORICAL_DEFENDER_OPEN_PLAY,
            exposing_defender_player_id=exposing_defender_player_id,
            exposed_cards=exposed_cards,
            declarer_response=declarer_response,
        )

    if game_end_reason == HISTORICAL_DEFENDER_CONCESSION:
        _require_exact_fields(
            value,
            {
                "schema_version",
                "kind",
                "conceding_defender_player_id",
                "concession_form",
            },
            field_name,
        )
        if not is_strict_integer(value["schema_version"]) or value["schema_version"] != 1:
            raise ValueError(f"{field_name}.schema_version must be exactly 1.")
        if value["kind"] != HISTORICAL_DEFENDER_CONCESSION:
            raise ValueError(
                f"{field_name}.kind must match game_end_reason "
                f"'{HISTORICAL_DEFENDER_CONCESSION}'."
            )
        conceding_player_id = value["conceding_defender_player_id"]
        if (
            not isinstance(conceding_player_id, str)
            or not conceding_player_id
            or conceding_player_id != conceding_player_id.strip()
        ):
            raise ValueError(
                f"{field_name}.conceding_defender_player_id must be a non-empty, "
                "non-padded stable player ID."
            )
        if conceding_player_id not in seat_order_player_ids:
            raise ValueError(
                f"{field_name}.conceding_defender_player_id must reference an exact "
                "stable participant ID."
            )
        if conceding_player_id == declarer_player_id:
            raise ValueError(
                f"{field_name}.conceding_defender_player_id must identify a member "
                "of the defending party."
            )
        concession_form = value["concession_form"]
        if concession_form not in VALID_CONCESSION_FORMS:
            raise ValueError(
                f"{field_name}.concession_form must be 'explicit_verbal' or "
                "'adjudicated_unambiguous_conduct'."
            )
        return HistoricalDefenderConcession(
            schema_version=HISTORICAL_GAME_END_SCHEMA_VERSION,
            kind=HISTORICAL_DEFENDER_CONCESSION,
            conceding_defender_player_id=conceding_player_id,
            concession_form=concession_form,
        )

    if game_end_reason == HISTORICAL_DECLARER_CARD_EXPOSURE:
        _require_exact_fields(
            value,
            {
                "schema_version",
                "kind",
                "exposure",
                "claimed_play_level",
                "defender_responses",
            },
            field_name,
        )
        if not is_strict_integer(value["schema_version"]) or value["schema_version"] != 1:
            raise ValueError(f"{field_name}.schema_version must be exactly 1.")
        if value["kind"] != HISTORICAL_DECLARER_CARD_EXPOSURE:
            raise ValueError(
                f"{field_name}.kind must match game_end_reason "
                f"'{HISTORICAL_DECLARER_CARD_EXPOSURE}'."
            )

        exposure_field = f"{field_name}.exposure"
        exposure_value = value["exposure"]
        if not isinstance(exposure_value, dict):
            raise ValueError(f"{exposure_field} must be an object.")
        exposure_form = exposure_value.get("form")
        if exposure_form not in VALID_EXPOSURE_FORMS:
            raise ValueError(
                f"{exposure_field}.form must be 'laid_open' or 'shown_to_defender'."
            )
        exposure_fields = {"form", "exposed_cards"}
        if exposure_form == "shown_to_defender":
            exposure_fields.add("shown_to_defender_player_id")
        _require_exact_fields(exposure_value, exposure_fields, exposure_field)

        raw_cards = exposure_value["exposed_cards"]
        if not isinstance(raw_cards, list):
            raise ValueError(f"{exposure_field}.exposed_cards must be an array.")
        if not 1 <= len(raw_cards) <= 10:
            raise ValueError(
                f"{exposure_field}.exposed_cards must contain between 1 and 10 cards."
            )
        valid_cards = set(get_full_deck())
        invalid_cards = [
            card for card in raw_cards if not isinstance(card, str) or card not in valid_cards
        ]
        if invalid_cards:
            raise ValueError(
                f"{exposure_field}.exposed_cards contains invalid cards: {invalid_cards}."
            )
        if len(raw_cards) != len(set(raw_cards)):
            raise ValueError(f"{exposure_field}.exposed_cards must not contain duplicates.")
        card_order = {card: index for index, card in enumerate(get_full_deck())}
        exposed_cards = tuple(sorted(raw_cards, key=card_order.__getitem__))

        shown_to_defender_player_id = None
        if exposure_form == "shown_to_defender":
            shown_to_defender_player_id = _require_stable_defender_id(
                exposure_value["shown_to_defender_player_id"],
                field_name=f"{exposure_field}.shown_to_defender_player_id",
                declarer_player_id=declarer_player_id,
                seat_order_player_ids=seat_order_player_ids,
            )

        claimed_play_level = value["claimed_play_level"]
        if claimed_play_level not in VALID_CLAIMED_PLAY_LEVELS:
            raise ValueError(
                f"{field_name}.claimed_play_level must be 'simple', 'schneider', "
                "or 'schwarz'."
            )

        raw_responses = value["defender_responses"]
        if not isinstance(raw_responses, list) or len(raw_responses) != 2:
            raise ValueError(
                f"{field_name}.defender_responses must contain exactly two defender "
                "acceptances."
            )
        responses_by_player: dict[str, HistoricalDefenderExposureResponse] = {}
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
                    f"{field_name}.defender_responses must identify each defender "
                    "exactly once."
                )
            if raw_response["response"] != "accept":
                raise ValueError(
                    "Both defenders must use response='accept'. Historical "
                    "exposed-hand continuation remains separate future work."
                )
            acceptance_form = raw_response["form"]
            if acceptance_form not in VALID_ACCEPTANCE_FORMS:
                raise ValueError(
                    f"{response_field}.form must be 'explicit' or "
                    "'unambiguous_conduct'."
                )
            responses_by_player[defender_player_id] = HistoricalDefenderExposureResponse(
                defender_player_id=defender_player_id,
                response="accept",
                form=acceptance_form,
            )
        defender_ids = {
            player_id
            for player_id in seat_order_player_ids
            if player_id != declarer_player_id
        }
        if set(responses_by_player) != defender_ids:
            raise ValueError(
                f"{field_name}.defender_responses must identify each stable defender "
                "exactly once."
            )
        ordered_responses = tuple(
            responses_by_player[player_id]
            for player_id in seat_order_player_ids
            if player_id in responses_by_player
        )
        return HistoricalDeclarerCardExposure(
            schema_version=HISTORICAL_GAME_END_SCHEMA_VERSION,
            kind=HISTORICAL_DECLARER_CARD_EXPOSURE,
            exposure=HistoricalDeclarerCardExposureDetails(
                form=exposure_form,
                exposed_cards=exposed_cards,
                shown_to_defender_player_id=shown_to_defender_player_id,
            ),
            claimed_play_level=claimed_play_level,
            defender_responses=ordered_responses,
        )

    _require_exact_fields(
        value,
        {
            "schema_version",
            "kind",
            "declarer_hand_cards_remaining",
            "defender_consent",
        },
        field_name,
    )
    if not is_strict_integer(value["schema_version"]) or value["schema_version"] != 1:
        raise ValueError(f"{field_name}.schema_version must be exactly 1.")
    if value["kind"] != HISTORICAL_DECLARER_CONCESSION:
        raise ValueError(
            f"{field_name}.kind must match game_end_reason "
            f"'{HISTORICAL_DECLARER_CONCESSION}'."
        )

    hand_count = value["declarer_hand_cards_remaining"]
    if not is_strict_integer(hand_count):
        raise ValueError(f"{field_name}.declarer_hand_cards_remaining must be an integer.")
    if not 1 <= hand_count <= 10:
        raise ValueError(
            f"{field_name}.declarer_hand_cards_remaining must be between 1 and 10."
        )

    consent_field = f"{field_name}.defender_consent"
    consent_value = value["defender_consent"]
    if not isinstance(consent_value, dict):
        raise ValueError(f"{consent_field} must be an object.")
    _require_exact_fields(
        consent_value,
        {"status", "consenting_defender_player_ids"},
        consent_field,
    )
    status = consent_value["status"]
    if status not in VALID_CONSENT_STATUSES:
        raise ValueError(f"{consent_field}.status must be 'not_required' or 'granted'.")
    raw_ids = consent_value["consenting_defender_player_ids"]
    if not isinstance(raw_ids, list) or any(
        not isinstance(player_id, str) for player_id in raw_ids
    ):
        raise ValueError(
            f"{consent_field}.consenting_defender_player_ids must be an array of strings."
        )
    if len(raw_ids) != len(set(raw_ids)):
        raise ValueError(
            f"{consent_field}.consenting_defender_player_ids must not contain duplicates."
        )
    defender_ids = {
        player_id for player_id in seat_order_player_ids if player_id != declarer_player_id
    }
    invalid_ids = [player_id for player_id in raw_ids if player_id not in defender_ids]
    if invalid_ids:
        raise ValueError(
            f"{consent_field}.consenting_defender_player_ids must reference exact stable "
            f"defender IDs; invalid={invalid_ids}."
        )
    ordered_ids = tuple(
        player_id for player_id in seat_order_player_ids if player_id in raw_ids
    )
    if hand_count >= 9:
        if status != "not_required" or ordered_ids:
            raise ValueError(
                "A historical declarer concession with 9 or 10 hand cards requires "
                "defender_consent.status='not_required' and no consenting defenders."
            )
    elif status != "granted" or len(ordered_ids) not in {1, 2}:
        raise ValueError(
            "A historical declarer concession with 1 to 8 hand cards requires "
            "defender_consent.status='granted' and one or two consenting defenders."
        )

    return HistoricalDeclarerConcession(
        schema_version=HISTORICAL_GAME_END_SCHEMA_VERSION,
        kind=HISTORICAL_DECLARER_CONCESSION,
        declarer_hand_cards_remaining=hand_count,
        defender_consent=HistoricalDefenderConsent(
            status=status,
            consenting_defender_player_ids=ordered_ids,
        ),
    )


def build_serializable_historical_game_end(
    game_end: HistoricalGameEnd,
) -> dict[str, Any]:
    """Serializes one historical game-end union member deterministically."""
    if isinstance(game_end, HistoricalDefenderConcession):
        return {
            "schema_version": game_end.schema_version,
            "kind": game_end.kind,
            "conceding_defender_player_id": game_end.conceding_defender_player_id,
            "concession_form": game_end.concession_form,
        }
    if isinstance(game_end, HistoricalDefenderOpenPlay):
        return {
            "schema_version": game_end.schema_version,
            "kind": game_end.kind,
            "exposing_defender_player_id": game_end.exposing_defender_player_id,
            "exposed_cards": list(game_end.exposed_cards),
            "declarer_response": game_end.declarer_response,
        }
    if isinstance(game_end, HistoricalDeclarerCardExposure):
        exposure = {
            "form": game_end.exposure.form,
            "exposed_cards": list(game_end.exposure.exposed_cards),
        }
        if game_end.exposure.shown_to_defender_player_id is not None:
            exposure["shown_to_defender_player_id"] = (
                game_end.exposure.shown_to_defender_player_id
            )
        return {
            "schema_version": game_end.schema_version,
            "kind": game_end.kind,
            "exposure": exposure,
            "claimed_play_level": game_end.claimed_play_level,
            "defender_responses": [
                {
                    "defender_player_id": response.defender_player_id,
                    "response": response.response,
                    "form": response.form,
                }
                for response in game_end.defender_responses
            ],
        }
    return {
        "schema_version": game_end.schema_version,
        "kind": game_end.kind,
        "declarer_hand_cards_remaining": game_end.declarer_hand_cards_remaining,
        "defender_consent": {
            "status": game_end.defender_consent.status,
            "consenting_defender_player_ids": list(
                game_end.defender_consent.consenting_defender_player_ids
            ),
        },
    }
