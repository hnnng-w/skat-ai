from dataclasses import dataclass
from typing import Any

from skat_ai.deck import get_full_deck
from skat_ai.final_settlement import build_final_settlement_summary
from skat_ai.game_declaration import (
    BOOLEAN_DECLARATION_FIELDS,
    GameDeclaration,
    build_serializable_game_declaration,
)
from skat_ai.game_end import apply_remaining_points_assignment
from skat_ai.game_result import (
    build_game_result_summary_from_score_summary,
    get_completed_trick_schwarz_status,
)
from skat_ai.game_value import build_game_value_summary
from skat_ai.historical_declarer_card_exposure import (
    adjudicate_historical_declarer_card_exposure,
)
from skat_ai.historical_declarer_concession import (
    adjudicate_historical_declarer_concession,
)
from skat_ai.historical_defender_concession import (
    adjudicate_historical_defender_concession,
)
from skat_ai.historical_defender_open_play import (
    adjudicate_historical_defender_open_play,
)
from skat_ai.historical_game_end import (
    HISTORICAL_DECLARER_CARD_EXPOSURE,
    HISTORICAL_DECLARER_CONCESSION,
    HISTORICAL_DEFENDER_CONCESSION,
    HISTORICAL_DEFENDER_OPEN_PLAY,
    HISTORICAL_NORMAL_COMPLETION,
    HISTORICAL_OPEN_CARD_THROW,
    HISTORICAL_PARTY_WIDE_ALL_REMAINING_TRICKS_CLAIM,
    HistoricalGameEnd,
    build_historical_game_end,
    build_serializable_historical_game_end,
)
from skat_ai.historical_game_event import (
    HistoricalGameEvent,
    build_historical_game_event_chain_context,
    build_historical_game_events,
    build_historical_game_events_summary,
    build_serializable_historical_game_event,
)
from skat_ai.historical_open_card_throw import adjudicate_historical_open_card_throw
from skat_ai.historical_play_prefix import (
    build_serializable_derived_trick,
    replay_historical_play_prefix,
)
from skat_ai.matador_inference import infer_matadors_from_known_ownership
from skat_ai.overbid import build_overbid_summary
from skat_ai.rfc3339 import parse_rfc3339_datetime
from skat_ai.rules import get_card_points

HISTORICAL_GAME_SCHEMA_VERSION = 1
HISTORICAL_GAME_END_REASON = HISTORICAL_NORMAL_COMPLETION
HISTORICAL_SEATS = ("forehand", "middlehand", "rearhand")


@dataclass(frozen=True)
class HistoricalPlayer:
    """One stable player identity and the player's initial ten-card hand."""

    player_id: str
    player_label: str | None
    seat: str
    initial_hand: tuple[str, ...]


@dataclass(frozen=True)
class HistoricalPlay:
    """One card play by a stable player identity."""

    player_id: str
    card: str


@dataclass(frozen=True)
class HistoricalTrick:
    """One ordered historical trick, optionally incomplete only at the prefix end."""

    trick_number: int
    leader_player_id: str
    plays: tuple[HistoricalPlay, ...]


@dataclass(frozen=True)
class HistoricalGameRecord:
    """A validated historical game with a supported version-1 end reason."""

    schema_version: int
    game_id: str
    played_at: str | None
    players: tuple[HistoricalPlayer, ...]
    skat: tuple[str, ...]
    declarer_player_id: str
    declaration: GameDeclaration
    discarded_cards: tuple[str, ...]
    game_end_reason: str
    game_end: HistoricalGameEnd | None
    game_events: tuple[HistoricalGameEvent, ...]
    tricks: tuple[HistoricalTrick, ...]


def _require_object(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be an object.")
    return value


def _require_exact_fields(
    data: dict[str, Any],
    required_fields: set[str],
    optional_fields: set[str],
    field_name: str,
) -> None:
    missing_fields = sorted(required_fields - data.keys())
    if missing_fields:
        raise ValueError(f"{field_name} is missing required fields: {missing_fields}.")

    unexpected_fields = sorted(data.keys() - required_fields - optional_fields)
    if unexpected_fields:
        raise ValueError(f"{field_name} has unsupported fields: {unexpected_fields}.")


def _require_identifier(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{field_name} must be a non-empty, non-padded string.")
    return value


def _require_card_array(
    value: Any,
    field_name: str,
    expected_count: int | None = None,
) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be an array.")
    if expected_count is not None and len(value) != expected_count:
        raise ValueError(f"{field_name} must contain exactly {expected_count} cards.")
    if any(not isinstance(card, str) for card in value):
        raise ValueError(f"{field_name} must contain only card strings.")

    valid_cards = set(get_full_deck())
    invalid_cards = [card for card in value if card not in valid_cards]
    if invalid_cards:
        raise ValueError(f"{field_name} contains invalid cards: {invalid_cards}.")
    if len(value) != len(set(value)):
        raise ValueError(f"{field_name} contains duplicate cards.")
    return tuple(value)


def _build_players(value: Any, game_id: str) -> tuple[HistoricalPlayer, ...]:
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError(
            f"Historical game '{game_id}': players must contain exactly three players."
        )

    players = []
    for player_index, raw_player in enumerate(value):
        field_name = f"Historical game '{game_id}' players[{player_index}]"
        player_data = _require_object(raw_player, field_name)
        _require_exact_fields(
            player_data,
            required_fields={"player_id", "seat", "initial_hand"},
            optional_fields={"player_label"},
            field_name=field_name,
        )
        player_id = _require_identifier(player_data["player_id"], f"{field_name}.player_id")
        player_label = player_data.get("player_label")
        if player_label is not None:
            player_label = _require_identifier(player_label, f"{field_name}.player_label")
        seat = player_data["seat"]
        if seat not in HISTORICAL_SEATS:
            raise ValueError(f"{field_name}.seat must be one of {list(HISTORICAL_SEATS)}.")
        initial_hand = _require_card_array(
            player_data["initial_hand"],
            f"{field_name}.initial_hand",
            expected_count=10,
        )
        players.append(
            HistoricalPlayer(
                player_id=player_id,
                player_label=player_label,
                seat=seat,
                initial_hand=initial_hand,
            )
        )

    player_ids = [player.player_id for player in players]
    if len(player_ids) != len(set(player_ids)):
        raise ValueError(f"Historical game '{game_id}': player_id values must be unique.")
    seats = [player.seat for player in players]
    if set(seats) != set(HISTORICAL_SEATS):
        raise ValueError(
            f"Historical game '{game_id}': seats must contain exactly one forehand, "
            "one middlehand, and one rearhand."
        )
    return tuple(players)


def _validate_complete_deal(
    players: tuple[HistoricalPlayer, ...],
    skat: tuple[str, ...],
    game_id: str,
) -> None:
    dealt_cards = [
        *(card for player in players for card in player.initial_hand),
        *skat,
    ]
    if len(dealt_cards) != len(set(dealt_cards)):
        raise ValueError(
            f"Historical game '{game_id}': initial hands and skat contain duplicate cards."
        )
    if set(dealt_cards) != set(get_full_deck()):
        missing_cards = sorted(set(get_full_deck()) - set(dealt_cards))
        unexpected_cards = sorted(set(dealt_cards) - set(get_full_deck()))
        raise ValueError(
            f"Historical game '{game_id}': initial hands and skat must form the complete "
            f"32-card deck; missing={missing_cards}, unexpected={unexpected_cards}."
        )


def _build_declaration(
    value: Any,
    players: tuple[HistoricalPlayer, ...],
    skat: tuple[str, ...],
    declarer_player_id: str,
    game_id: str,
) -> GameDeclaration:
    field_name = f"Historical game '{game_id}' declaration"
    declaration_data = _require_object(value, field_name)
    _require_exact_fields(
        declaration_data,
        required_fields={"game_type", "bid_value"},
        optional_fields={*BOOLEAN_DECLARATION_FIELDS, "matadors"},
        field_name=field_name,
    )

    game_type = declaration_data["game_type"]
    declarer = next(player for player in players if player.player_id == declarer_player_id)
    defender_cards = [
        card
        for player in players
        if player.player_id != declarer_player_id
        for card in player.initial_hand
    ]
    inferred_matadors = infer_matadors_from_known_ownership(
        game_type=game_type,
        declarer_owned_cards=[*declarer.initial_hand, *skat],
        non_declarer_owned_cards=defender_cards,
    )

    null_excluded_fields = {
        "matadors",
        "schneider_announced",
        "schwarz_announced",
    }
    supplied_null_excluded_fields = sorted(null_excluded_fields.intersection(declaration_data))
    if game_type == "null" and supplied_null_excluded_fields:
        raise ValueError(
            f"{field_name} does not allow Null metadata fields: {supplied_null_excluded_fields}."
        )
    if game_type != "null":
        if inferred_matadors is None:
            raise ValueError(f"{field_name}.matadors could not be inferred from the complete deal.")
        if "matadors" in declaration_data and declaration_data["matadors"] != inferred_matadors:
            raise ValueError(
                f"{field_name}.matadors={declaration_data['matadors']} conflicts with "
                f"inferred matadors={inferred_matadors}."
            )

    declaration_values = {
        field: declaration_data[field]
        for field in BOOLEAN_DECLARATION_FIELDS
        if field in declaration_data
    }
    return GameDeclaration(
        game_type=game_type,
        matadors=inferred_matadors,
        bid_value=declaration_data["bid_value"],
        **declaration_values,
    )


def _build_tricks(
    value: Any,
    game_id: str,
    game_end_reason: str,
) -> tuple[HistoricalTrick, ...]:
    if not isinstance(value, list):
        raise ValueError(f"Historical game '{game_id}': tricks must be an array.")
    if game_end_reason == HISTORICAL_NORMAL_COMPLETION and len(value) != 10:
        raise ValueError(f"Historical game '{game_id}': tricks must contain exactly ten tricks.")
    if (
        game_end_reason
        in {
            HISTORICAL_DECLARER_CARD_EXPOSURE,
            HISTORICAL_DECLARER_CONCESSION,
            HISTORICAL_DEFENDER_CONCESSION,
            HISTORICAL_DEFENDER_OPEN_PLAY,
            HISTORICAL_OPEN_CARD_THROW,
            HISTORICAL_PARTY_WIDE_ALL_REMAINING_TRICKS_CLAIM,
        }
        and len(value) > 10
    ):
        raise ValueError(
            f"Historical game '{game_id}': a shortened play prefix may "
            "contain at most ten trick entries."
        )

    tricks = []
    for trick_index, raw_trick in enumerate(value):
        trick_number = trick_index + 1
        field_name = f"Historical game '{game_id}' trick {trick_number}"
        trick_data = _require_object(raw_trick, field_name)
        _require_exact_fields(
            trick_data,
            required_fields={"trick_number", "leader_player_id", "plays"},
            optional_fields=set(),
            field_name=field_name,
        )
        supplied_trick_number = trick_data["trick_number"]
        if (
            isinstance(supplied_trick_number, bool)
            or not isinstance(supplied_trick_number, int)
            or supplied_trick_number != trick_number
        ):
            raise ValueError(
                f"{field_name}.trick_number must be {trick_number}, got {supplied_trick_number}."
            )
        leader_player_id = _require_identifier(
            trick_data["leader_player_id"], f"{field_name}.leader_player_id"
        )
        raw_plays = trick_data["plays"]
        expected_play_counts = {3} if game_end_reason == HISTORICAL_NORMAL_COMPLETION else {1, 2, 3}
        if not isinstance(raw_plays, list) or len(raw_plays) not in expected_play_counts:
            if game_end_reason == HISTORICAL_NORMAL_COMPLETION:
                raise ValueError(f"{field_name}.plays must contain exactly three plays.")
            raise ValueError(f"{field_name}.plays must contain one, two, or three plays.")
        if len(raw_plays) < 3 and trick_index != len(value) - 1:
            raise ValueError(
                f"{field_name} is incomplete; only the final historical trick may be incomplete."
            )

        plays = []
        for play_index, raw_play in enumerate(raw_plays):
            play_field = f"{field_name} play {play_index + 1}"
            play_data = _require_object(raw_play, play_field)
            _require_exact_fields(
                play_data,
                required_fields={"player_id", "card"},
                optional_fields=set(),
                field_name=play_field,
            )
            player_id = _require_identifier(play_data["player_id"], f"{play_field}.player_id")
            card = _require_card_array([play_data["card"]], f"{play_field}.card", expected_count=1)[
                0
            ]
            plays.append(HistoricalPlay(player_id=player_id, card=card))

        tricks.append(
            HistoricalTrick(
                trick_number=trick_number,
                leader_player_id=leader_player_id,
                plays=tuple(plays),
            )
        )
    return tuple(tricks)


def build_historical_game_record(
    data: dict[str, Any],
    *,
    validate_game_event_chain: bool = True,
) -> HistoricalGameRecord:
    """Builds and validates one canonical complete historical game record."""
    _require_exact_fields(
        data,
        required_fields={
            "schema_version",
            "game_id",
            "players",
            "skat",
            "declarer_player_id",
            "declaration",
            "discarded_cards",
            "game_end_reason",
            "tricks",
        },
        optional_fields={"played_at", "game_end", "game_events"},
        field_name="historical_game_input",
    )
    if (
        isinstance(data["schema_version"], bool)
        or not isinstance(data["schema_version"], int)
        or data["schema_version"] != HISTORICAL_GAME_SCHEMA_VERSION
    ):
        raise ValueError(
            "historical_game_input.schema_version must currently equal "
            f"{HISTORICAL_GAME_SCHEMA_VERSION}."
        )
    game_id = _require_identifier(data["game_id"], "historical_game_input.game_id")
    played_at = data.get("played_at")
    if played_at is not None:
        played_at = _require_identifier(played_at, f"Historical game '{game_id}' played_at")
        parse_rfc3339_datetime(played_at, f"Historical game '{game_id}' played_at")
    players = _build_players(data["players"], game_id)
    skat = _require_card_array(data["skat"], f"Historical game '{game_id}' skat", expected_count=2)
    _validate_complete_deal(players, skat, game_id)

    declarer_player_id = _require_identifier(
        data["declarer_player_id"],
        f"Historical game '{game_id}' declarer_player_id",
    )
    if declarer_player_id not in {player.player_id for player in players}:
        raise ValueError(
            f"Historical game '{game_id}': declarer_player_id '{declarer_player_id}' "
            "does not reference a declared player."
        )
    declaration = _build_declaration(
        data["declaration"], players, skat, declarer_player_id, game_id
    )
    discarded_cards = _require_card_array(
        data["discarded_cards"], f"Historical game '{game_id}' discarded_cards"
    )
    declarer = next(player for player in players if player.player_id == declarer_player_id)
    if declaration.hand_game:
        if discarded_cards:
            raise ValueError(
                f"Historical game '{game_id}': Hand games require discarded_cards to be empty."
            )
    else:
        if len(discarded_cards) != 2:
            raise ValueError(
                f"Historical game '{game_id}': non-Hand games require exactly two discarded_cards."
            )
        available_to_declarer = set((*declarer.initial_hand, *skat))
        unavailable_discards = sorted(set(discarded_cards) - available_to_declarer)
        if unavailable_discards:
            raise ValueError(
                f"Historical game '{game_id}': discarded_cards were not owned by the "
                f"declarer after pickup: {unavailable_discards}."
            )

    game_end_reason = data["game_end_reason"]
    seat_order_player_ids = tuple(
        next(player.player_id for player in players if player.seat == seat)
        for seat in HISTORICAL_SEATS
    )
    game_end = build_historical_game_end(
        data.get("game_end"),
        game_end_reason=game_end_reason,
        declarer_player_id=declarer_player_id,
        seat_order_player_ids=seat_order_player_ids,
        game_id=game_id,
    )
    game_events = build_historical_game_events(
        data.get("game_events"),
        game_end_reason=game_end_reason,
        has_game_end=game_end is not None,
        seat_order_player_ids=seat_order_player_ids,
        declarer_player_id=declarer_player_id,
        game_type=declaration.game_type,
        game_id=game_id,
    )
    tricks = _build_tricks(data["tricks"], game_id, game_end_reason)
    record = HistoricalGameRecord(
        schema_version=HISTORICAL_GAME_SCHEMA_VERSION,
        game_id=game_id,
        played_at=played_at,
        players=players,
        skat=skat,
        declarer_player_id=declarer_player_id,
        declaration=declaration,
        discarded_cards=discarded_cards,
        game_end_reason=game_end_reason,
        game_end=game_end,
        game_events=game_events,
        tricks=tricks,
    )
    if record.game_events and validate_game_event_chain:
        build_historical_game_event_chain_context(record)
    return record


def build_serializable_historical_record(
    record: HistoricalGameRecord,
) -> dict[str, Any]:
    """Serializes the supplied game with its canonical declaration metadata."""
    players = []
    for player in record.players:
        serialized_player: dict[str, Any] = {
            "player_id": player.player_id,
            "seat": player.seat,
            "initial_hand": list(player.initial_hand),
        }
        if player.player_label is not None:
            serialized_player["player_label"] = player.player_label
        players.append(serialized_player)

    serialized_declaration = build_serializable_game_declaration(record.declaration)
    if record.declaration.game_type == "null":
        for excluded_field in (
            "matadors",
            "schneider_announced",
            "schwarz_announced",
        ):
            serialized_declaration.pop(excluded_field)

    result = {
        "schema_version": record.schema_version,
        "game_id": record.game_id,
        "players": players,
        "skat": list(record.skat),
        "declarer_player_id": record.declarer_player_id,
        "declaration": serialized_declaration,
        "discarded_cards": list(record.discarded_cards),
        "game_end_reason": record.game_end_reason,
        "tricks": [
            {
                "trick_number": trick.trick_number,
                "leader_player_id": trick.leader_player_id,
                "plays": [{"player_id": play.player_id, "card": play.card} for play in trick.plays],
            }
            for trick in record.tricks
        ],
    }
    if record.game_end is not None:
        result["game_end"] = build_serializable_historical_game_end(record.game_end)
    if record.game_events:
        result["game_events"] = [
            build_serializable_historical_game_event(event) for event in record.game_events
        ]
    if record.played_at is not None:
        result["played_at"] = record.played_at
    return result


def _derive_tricks(
    record: HistoricalGameRecord,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    replay = replay_historical_play_prefix(record)
    derived_tricks = [build_serializable_derived_trick(trick) for trick in replay.completed_tricks]
    scoring_tricks = [
        {
            "cards": [card for _, card in trick.plays],
            "winner_role": trick.winner_side,
        }
        for trick in replay.completed_tricks
    ]
    unplayed_cards = {
        player_id: list(remaining_hand)
        for player_id, remaining_hand in replay.remaining_hands
        if remaining_hand
    }
    if unplayed_cards:
        raise ValueError(
            f"Historical game '{record.game_id}': every playable card must be used "
            f"exactly once; unplayed cards={unplayed_cards}."
        )
    return derived_tricks, scoring_tricks


def build_historical_game_summary(record: HistoricalGameRecord) -> dict[str, Any]:
    """Validates all plays and derives the complete result and settlement."""
    if record.game_end_reason in {
        HISTORICAL_DECLARER_CARD_EXPOSURE,
        HISTORICAL_DECLARER_CONCESSION,
        HISTORICAL_DEFENDER_CONCESSION,
        HISTORICAL_DEFENDER_OPEN_PLAY,
        HISTORICAL_OPEN_CARD_THROW,
        HISTORICAL_PARTY_WIDE_ALL_REMAINING_TRICKS_CLAIM,
    }:
        replay = replay_historical_play_prefix(record)
        if (
            replay.played_card_count >= 30
            and record.game_end_reason != HISTORICAL_PARTY_WIDE_ALL_REMAINING_TRICKS_CLAIM
        ):
            raise ValueError(
                f"Historical game '{record.game_id}': a shortened event cannot "
                "occur after all 30 playable cards were played."
            )
        derived_tricks = [
            build_serializable_derived_trick(trick) for trick in replay.completed_tricks
        ]
        chain_context = None
        if record.game_events:
            chain_context = build_historical_game_event_chain_context(
                record,
                final_replay=replay,
            )
        if record.game_end_reason == HISTORICAL_DECLARER_CONCESSION:
            adjudicated_end = adjudicate_historical_declarer_concession(record, replay)
        elif record.game_end_reason == HISTORICAL_DEFENDER_CONCESSION:
            adjudicated_end = adjudicate_historical_defender_concession(record, replay)
        elif record.game_end_reason == HISTORICAL_DEFENDER_OPEN_PLAY:
            adjudicated_end = adjudicate_historical_defender_open_play(record, replay)
        elif record.game_end_reason == HISTORICAL_OPEN_CARD_THROW:
            adjudicated_end = adjudicate_historical_open_card_throw(record, replay)
        elif record.game_end_reason == HISTORICAL_PARTY_WIDE_ALL_REMAINING_TRICKS_CLAIM:
            from skat_ai.historical_party_wide_claim import (
                adjudicate_historical_party_wide_claim,
            )

            adjudicated_end = adjudicate_historical_party_wide_claim(record, replay)
        else:
            adjudicated_end = adjudicate_historical_declarer_card_exposure(record, replay)
        result = {
            "schema_version": record.schema_version,
            "game_id": record.game_id,
            "status": "complete",
            "record": build_serializable_historical_record(record),
            "derived_tricks": derived_tricks,
            **adjudicated_end,
        }
        if record.played_at is not None:
            result["played_at"] = record.played_at
        if chain_context is not None:
            result["historical_game_events_summary"] = build_historical_game_events_summary(
                record,
                chain_context=chain_context,
            )
        return result

    derived_tricks, scoring_tricks = _derive_tricks(record)
    declarer_trick_points = sum(
        trick["trick_points"] for trick in derived_tricks if trick["winner_side"] == "declarer"
    )
    defender_trick_points = sum(
        trick["trick_points"] for trick in derived_tricks if trick["winner_side"] == "defenders"
    )
    final_skat = record.skat if record.declaration.hand_game else record.discarded_cards
    skat_points = sum(get_card_points(card) for card in final_skat)
    declarer_points = declarer_trick_points + skat_points
    defender_points = defender_trick_points
    if declarer_points + defender_points != 120:
        raise ValueError(
            f"Historical game '{record.game_id}': final declarer and defender card "
            "points must total 120."
        )

    score_summary = {
        "total_declarer_points": declarer_points,
        "total_defender_points": defender_points,
    }
    game_result_summary = build_game_result_summary_from_score_summary(
        score_summary=score_summary,
        game_type=record.declaration.game_type,
        completed_tricks=scoring_tricks,
        game_end_reason=record.game_end_reason,
    )
    game_result_summary = apply_remaining_points_assignment(
        game_result_summary=game_result_summary,
        game_end_reason=record.game_end_reason,
    )
    game_value_summary = build_game_value_summary(record.declaration)
    overbid_summary = build_overbid_summary(
        game_value_summary=game_value_summary,
        bid_value=record.declaration.bid_value,
        game_end_reason=record.game_end_reason,
    )
    if record.declaration.game_type == "null" and overbid_summary["is_overbid"]:
        raise ValueError(
            f"Historical game '{record.game_id}': overbid Null records require the "
            "impossible-Null settlement workflow and are not supported."
        )
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

    is_null_game = record.declaration.game_type == "null"
    schneider_status = (
        "not_applicable" if is_null_game else game_result_summary["effective_schneider_status"]
    )
    schwarz_status = (
        "not_applicable" if is_null_game else get_completed_trick_schwarz_status(scoring_tricks)
    )

    result = {
        "schema_version": record.schema_version,
        "game_id": record.game_id,
        "status": "complete",
        "record": build_serializable_historical_record(record),
        "derived_tricks": derived_tricks,
        "declarer_trick_points": declarer_trick_points,
        "defender_trick_points": defender_trick_points,
        "skat_points": skat_points,
        "declarer_points": declarer_points,
        "defender_points": defender_points,
        "winner": game_result_summary["winner"],
        "schneider_status": schneider_status,
        "schwarz_status": schwarz_status,
        "game_result_summary": game_result_summary,
        "game_value_summary": game_value_summary,
        "overbid_summary": overbid_summary,
        "final_settlement_summary": final_settlement_summary,
    }
    if record.game_events:
        result["historical_game_events_summary"] = build_historical_game_events_summary(record)
    if record.played_at is not None:
        result["played_at"] = record.played_at
    return result


def build_historical_game_summary_from_input(data: dict[str, Any]) -> dict[str, Any]:
    """Builds one historical summary directly from the nested public input object."""
    return build_historical_game_summary(
        build_historical_game_record(data, validate_game_event_chain=False)
    )
