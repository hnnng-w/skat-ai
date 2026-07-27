from dataclasses import dataclass
from typing import Any

from skat_ai.declarer_concession import (
    DECLARER_CONCESSION_KIND,
    VALID_CONSENT_STATUSES,
    is_strict_integer,
)

HISTORICAL_GAME_END_SCHEMA_VERSION = 1
HISTORICAL_NORMAL_COMPLETION = "normal_completion"
HISTORICAL_DECLARER_CONCESSION = DECLARER_CONCESSION_KIND
HISTORICAL_GAME_END_REASONS = {
    HISTORICAL_NORMAL_COMPLETION,
    HISTORICAL_DECLARER_CONCESSION,
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


type HistoricalGameEnd = HistoricalDeclarerConcession


def _require_exact_fields(
    data: dict[str, Any], required_fields: set[str], field_name: str
) -> None:
    missing_fields = sorted(required_fields - data.keys())
    if missing_fields:
        raise ValueError(f"{field_name} is missing required fields: {missing_fields}.")
    unexpected_fields = sorted(data.keys() - required_fields)
    if unexpected_fields:
        raise ValueError(f"{field_name} has unsupported fields: {unexpected_fields}.")


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
            "game_end_reason='declarer_concession'."
        )
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be an object.")

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
