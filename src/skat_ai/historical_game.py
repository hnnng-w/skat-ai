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
from skat_ai.matador_inference import infer_matadors_from_known_ownership
from skat_ai.overbid import build_overbid_summary
from skat_ai.rfc3339 import parse_rfc3339_datetime
from skat_ai.rules import get_card_points, get_legal_cards, get_trick_points, get_trick_winner

HISTORICAL_GAME_SCHEMA_VERSION = 1
HISTORICAL_GAME_END_REASON = "normal_completion"
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
    """One ordered three-card trick from a complete historical game."""

    trick_number: int
    leader_player_id: str
    plays: tuple[HistoricalPlay, ...]


@dataclass(frozen=True)
class HistoricalGameRecord:
    """A validated complete historical game ending through normal play."""

    schema_version: int
    game_id: str
    played_at: str | None
    players: tuple[HistoricalPlayer, ...]
    skat: tuple[str, ...]
    declarer_player_id: str
    declaration: GameDeclaration
    discarded_cards: tuple[str, ...]
    game_end_reason: str
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
        player_id = _require_identifier(
            player_data["player_id"], f"{field_name}.player_id"
        )
        player_label = player_data.get("player_label")
        if player_label is not None:
            player_label = _require_identifier(
                player_label, f"{field_name}.player_label"
            )
        seat = player_data["seat"]
        if seat not in HISTORICAL_SEATS:
            raise ValueError(
                f"{field_name}.seat must be one of {list(HISTORICAL_SEATS)}."
            )
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
    declarer = next(
        player for player in players if player.player_id == declarer_player_id
    )
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
    supplied_null_excluded_fields = sorted(
        null_excluded_fields.intersection(declaration_data)
    )
    if game_type == "null" and supplied_null_excluded_fields:
        raise ValueError(
            f"{field_name} does not allow Null metadata fields: "
            f"{supplied_null_excluded_fields}."
        )
    if game_type != "null":
        if inferred_matadors is None:
            raise ValueError(
                f"{field_name}.matadors could not be inferred from the complete deal."
            )
        if (
            "matadors" in declaration_data
            and declaration_data["matadors"] != inferred_matadors
        ):
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


def _build_tricks(value: Any, game_id: str) -> tuple[HistoricalTrick, ...]:
    if not isinstance(value, list) or len(value) != 10:
        raise ValueError(f"Historical game '{game_id}': tricks must contain exactly ten tricks.")

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
                f"{field_name}.trick_number must be {trick_number}, "
                f"got {supplied_trick_number}."
            )
        leader_player_id = _require_identifier(
            trick_data["leader_player_id"], f"{field_name}.leader_player_id"
        )
        raw_plays = trick_data["plays"]
        if not isinstance(raw_plays, list) or len(raw_plays) != 3:
            raise ValueError(f"{field_name}.plays must contain exactly three plays.")

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
            player_id = _require_identifier(
                play_data["player_id"], f"{play_field}.player_id"
            )
            card = _require_card_array(
                [play_data["card"]], f"{play_field}.card", expected_count=1
            )[0]
            plays.append(HistoricalPlay(player_id=player_id, card=card))

        tricks.append(
            HistoricalTrick(
                trick_number=trick_number,
                leader_player_id=leader_player_id,
                plays=tuple(plays),
            )
        )
    return tuple(tricks)


def build_historical_game_record(data: dict[str, Any]) -> HistoricalGameRecord:
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
        optional_fields={"played_at"},
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
    skat = _require_card_array(
        data["skat"], f"Historical game '{game_id}' skat", expected_count=2
    )
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
    declarer = next(
        player for player in players if player.player_id == declarer_player_id
    )
    if declaration.hand_game:
        if discarded_cards:
            raise ValueError(
                f"Historical game '{game_id}': Hand games require discarded_cards to be empty."
            )
    else:
        if len(discarded_cards) != 2:
            raise ValueError(
                f"Historical game '{game_id}': non-Hand games require exactly two "
                "discarded_cards."
            )
        available_to_declarer = set((*declarer.initial_hand, *skat))
        unavailable_discards = sorted(set(discarded_cards) - available_to_declarer)
        if unavailable_discards:
            raise ValueError(
                f"Historical game '{game_id}': discarded_cards were not owned by the "
                f"declarer after pickup: {unavailable_discards}."
            )

    if data["game_end_reason"] != HISTORICAL_GAME_END_REASON:
        raise ValueError(
            f"Historical game '{game_id}': game_end_reason must be "
            f"'{HISTORICAL_GAME_END_REASON}'."
        )
    tricks = _build_tricks(data["tricks"], game_id)
    return HistoricalGameRecord(
        schema_version=HISTORICAL_GAME_SCHEMA_VERSION,
        game_id=game_id,
        played_at=played_at,
        players=players,
        skat=skat,
        declarer_player_id=declarer_player_id,
        declaration=declaration,
        discarded_cards=discarded_cards,
        game_end_reason=HISTORICAL_GAME_END_REASON,
        tricks=tricks,
    )


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
                "plays": [
                    {"player_id": play.player_id, "card": play.card}
                    for play in trick.plays
                ],
            }
            for trick in record.tricks
        ],
    }
    if record.played_at is not None:
        result["played_at"] = record.played_at
    return result


def _build_playable_hands(record: HistoricalGameRecord) -> dict[str, list[str]]:
    hands = {player.player_id: list(player.initial_hand) for player in record.players}
    if not record.declaration.hand_game:
        declarer_hand = hands[record.declarer_player_id]
        declarer_hand.extend(record.skat)
        for card in record.discarded_cards:
            declarer_hand.remove(card)
    return hands


def _get_player_order_from_leader(
    leader_player_id: str,
    seat_order_player_ids: list[str],
) -> list[str]:
    leader_index = seat_order_player_ids.index(leader_player_id)
    return [
        seat_order_player_ids[(leader_index + offset) % len(seat_order_player_ids)]
        for offset in range(len(seat_order_player_ids))
    ]


def _derive_tricks(
    record: HistoricalGameRecord,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    hands = _build_playable_hands(record)
    player_by_seat = {player.seat: player.player_id for player in record.players}
    seat_order_player_ids = [player_by_seat[seat] for seat in HISTORICAL_SEATS]
    expected_leader = seat_order_player_ids[0]
    derived_tricks = []
    scoring_tricks = []
    discarded_or_hand_skat = (
        set(record.skat) if record.declaration.hand_game else set(record.discarded_cards)
    )

    for trick in record.tricks:
        trick_name = f"Historical game '{record.game_id}' trick {trick.trick_number}"
        if trick.leader_player_id not in hands:
            raise ValueError(
                f"{trick_name}.leader_player_id references unknown player "
                f"'{trick.leader_player_id}'."
            )
        if trick.leader_player_id != expected_leader:
            raise ValueError(
                f"{trick_name} must be led by '{expected_leader}', got "
                f"'{trick.leader_player_id}'."
            )

        expected_order = _get_player_order_from_leader(
            trick.leader_player_id, seat_order_player_ids
        )
        supplied_order = [play.player_id for play in trick.plays]
        if supplied_order != expected_order:
            raise ValueError(
                f"{trick_name} play order must be {expected_order}, got {supplied_order}."
            )

        trick_cards = []
        for play_index, play in enumerate(trick.plays):
            play_name = f"{trick_name} play {play_index + 1} player '{play.player_id}'"
            if play.player_id not in hands:
                raise ValueError(f"{play_name} references an unknown player.")
            if play.card in discarded_or_hand_skat:
                raise ValueError(
                    f"{play_name} uses unplayable skat or discarded card '{play.card}'."
                )
            if play.card not in hands[play.player_id]:
                owner = next(
                    (
                        player_id
                        for player_id, remaining_hand in hands.items()
                        if play.card in remaining_hand
                    ),
                    None,
                )
                owner_text = f"; remaining owner is '{owner}'" if owner is not None else ""
                raise ValueError(
                    f"{play_name} does not own remaining card '{play.card}'{owner_text}."
                )
            legal_cards = get_legal_cards(
                hand=hands[play.player_id],
                current_trick=trick_cards,
                game_type=record.declaration.game_type,
            )
            if play.card not in legal_cards:
                raise ValueError(
                    f"{play_name} illegally plays '{play.card}'; legal cards are "
                    f"{legal_cards}."
                )
            hands[play.player_id].remove(play.card)
            trick_cards.append(play.card)

        winner_index = get_trick_winner(trick_cards, record.declaration.game_type)
        winner_player_id = trick.plays[winner_index].player_id
        winner_side = (
            "declarer"
            if winner_player_id == record.declarer_player_id
            else "defenders"
        )
        trick_points = get_trick_points(trick_cards)
        derived_tricks.append(
            {
                "trick_number": trick.trick_number,
                "leader_player_id": trick.leader_player_id,
                "plays": [
                    {"player_id": play.player_id, "card": play.card}
                    for play in trick.plays
                ],
                "winner_player_id": winner_player_id,
                "winner_side": winner_side,
                "trick_points": trick_points,
            }
        )
        scoring_tricks.append({"cards": trick_cards, "winner_role": winner_side})
        expected_leader = winner_player_id

    unplayed_cards = {
        player_id: remaining_hand
        for player_id, remaining_hand in hands.items()
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
    derived_tricks, scoring_tricks = _derive_tricks(record)
    declarer_trick_points = sum(
        trick["trick_points"]
        for trick in derived_tricks
        if trick["winner_side"] == "declarer"
    )
    defender_trick_points = sum(
        trick["trick_points"]
        for trick in derived_tricks
        if trick["winner_side"] == "defenders"
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
        "not_applicable"
        if is_null_game
        else game_result_summary["effective_schneider_status"]
    )
    schwarz_status = (
        "not_applicable"
        if is_null_game
        else get_completed_trick_schwarz_status(scoring_tricks)
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
    if record.played_at is not None:
        result["played_at"] = record.played_at
    return result


def build_historical_game_summary_from_input(data: dict[str, Any]) -> dict[str, Any]:
    """Builds one historical summary directly from the nested public input object."""
    return build_historical_game_summary(build_historical_game_record(data))
