from collections import Counter
from dataclasses import dataclass, replace
from typing import Any

from skat_ai.fixed_three_player_list_contribution import (
    FixedThreePlayerListContribution,
    build_fixed_three_player_list_contributions,
    build_serializable_fixed_three_player_list_contribution,
)
from skat_ai.fixed_three_player_list_rotation import (
    FIXED_THREE_PLAYER_LIST_TABLE_PLACES,
    FixedThreePlayerListSeatAssignment,
    build_fixed_three_player_list_seat_assignment,
    build_serializable_fixed_three_player_list_seat_assignment,
)
from skat_ai.historical_game import (
    HISTORICAL_SEATS,
    HistoricalGameRecord,
    build_historical_game_record,
    build_historical_game_summary,
    build_serializable_historical_record,
)
from skat_ai.performance_rating import (
    ISKO_COUNTERPARTY_LOSS_BONUS_THREE_PLAYER_TABLE,
    calculate_isko_list_performance_points,
    get_game_outcome_for_rating,
    validate_stable_list_entry_identifier,
    validate_stable_list_player_label,
)
from skat_ai.rfc3339 import parse_rfc3339_datetime

FIXED_THREE_PLAYER_HISTORICAL_LIST_SCHEMA_VERSION = 1
FIXED_THREE_PLAYER_LIST_PLAYER_COUNT = 3
FIXED_THREE_PLAYER_LIST_ENTRY_COUNT = 36
FIXED_THREE_PLAYER_LIST_ENTRIES_PER_ROUND = 3
FIXED_THREE_PLAYER_LIST_ROUND_COUNT = 12
FIXED_THREE_PLAYER_LIST_ENTRY_KINDS = ("played_game", "passed_deal")
FIXED_THREE_PLAYER_LIST_ENTRY_OUTCOMES = (
    "declarer_win",
    "declarer_loss",
    "passed_deal",
)


@dataclass(frozen=True)
class FixedThreePlayerHistoricalListPlayer:
    """One fixed stable participant at one canonical table place."""

    player_id: str
    player_label: str | None
    table_place: str


@dataclass(frozen=True)
class FixedThreePlayerHistoricalPlayedGameEntry:
    """One played position backed by a canonical historical game."""

    entry_id: str
    entry_kind: str
    historical_game: HistoricalGameRecord


@dataclass(frozen=True)
class FixedThreePlayerHistoricalPassedDealEntry:
    """One passed position with no synthetic game or settlement."""

    entry_id: str
    entry_kind: str
    played_at: str | None


type FixedThreePlayerHistoricalListEntry = (
    FixedThreePlayerHistoricalPlayedGameEntry | FixedThreePlayerHistoricalPassedDealEntry
)


@dataclass(frozen=True)
class FixedThreePlayerHistoricalList:
    """One complete ordered fixed-three-player 36-position list."""

    schema_version: int
    list_id: str
    players: tuple[FixedThreePlayerHistoricalListPlayer, ...]
    entries: tuple[FixedThreePlayerHistoricalListEntry, ...]


@dataclass(frozen=True)
class FixedThreePlayerHistoricalListEntryFact:
    """One reconciled non-cumulative fact for a list position."""

    schema_version: int
    list_id: str
    entry_number: int
    round_number: int
    entry_id: str
    entry_kind: str
    entry_outcome: str
    played_at: str | None
    dealer_player_id: str
    seat_assignment: FixedThreePlayerListSeatAssignment
    game_id: str | None
    game_end_reason: str | None
    declarer_player_id: str | None
    settlement_score: int | None
    player_contributions: tuple[FixedThreePlayerListContribution, ...]


def _require_exact_fields(
    data: dict[str, Any],
    *,
    required_fields: set[str],
    optional_fields: set[str] = frozenset(),
    field_name: str,
) -> None:
    missing_fields = sorted(required_fields - data.keys())
    if missing_fields:
        raise ValueError(f"{field_name} is missing required fields: {missing_fields}.")
    unsupported_fields = sorted(data.keys() - required_fields - optional_fields)
    if unsupported_fields:
        raise ValueError(f"{field_name} has unsupported fields: {unsupported_fields}.")


def _build_players(value: Any) -> tuple[FixedThreePlayerHistoricalListPlayer, ...]:
    if not isinstance(value, list) or len(value) != FIXED_THREE_PLAYER_LIST_PLAYER_COUNT:
        raise ValueError("historical_list.players must contain exactly three players.")

    players = []
    for index, raw_player in enumerate(value):
        field_name = f"historical_list.players[{index}]"
        if not isinstance(raw_player, dict):
            raise ValueError(f"{field_name} must be an object.")
        _require_exact_fields(
            raw_player,
            required_fields={"player_id", "table_place"},
            optional_fields={"player_label"},
            field_name=field_name,
        )
        player_id = raw_player["player_id"]
        validate_stable_list_entry_identifier(player_id, f"{field_name}.player_id")
        player_label = raw_player.get("player_label")
        if player_label is not None:
            validate_stable_list_player_label(player_label, f"{field_name}.player_label")
        table_place = raw_player["table_place"]
        if table_place not in FIXED_THREE_PLAYER_LIST_TABLE_PLACES:
            raise ValueError(
                f"{field_name}.table_place must be one of "
                f"{list(FIXED_THREE_PLAYER_LIST_TABLE_PLACES)}."
            )
        players.append(
            FixedThreePlayerHistoricalListPlayer(
                player_id=player_id,
                player_label=player_label,
                table_place=table_place,
            )
        )

    player_ids = [player.player_id for player in players]
    if len(set(player_ids)) != len(player_ids):
        raise ValueError("historical_list.players contains duplicate player_id values.")
    places = tuple(player.table_place for player in players)
    if places != FIXED_THREE_PLAYER_LIST_TABLE_PLACES:
        raise ValueError("historical_list.players must cover all table places in canonical order.")
    return tuple(players)


def _build_entries(value: Any) -> tuple[FixedThreePlayerHistoricalListEntry, ...]:
    if not isinstance(value, list) or len(value) != FIXED_THREE_PLAYER_LIST_ENTRY_COUNT:
        raise ValueError("historical_list.entries must contain exactly 36 entries.")

    entries = []
    for index, raw_entry in enumerate(value):
        field_name = f"historical_list.entries[{index}]"
        if not isinstance(raw_entry, dict):
            raise ValueError(f"{field_name} must be an object.")
        entry_kind = raw_entry.get("entry_kind")
        if entry_kind == "played_game":
            _require_exact_fields(
                raw_entry,
                required_fields={"entry_id", "entry_kind", "historical_game"},
                field_name=field_name,
            )
        elif entry_kind == "passed_deal":
            _require_exact_fields(
                raw_entry,
                required_fields={"entry_id", "entry_kind", "played_at"},
                field_name=field_name,
            )
        else:
            raise ValueError(
                f"{field_name}.entry_kind must be one of "
                f"{list(FIXED_THREE_PLAYER_LIST_ENTRY_KINDS)}."
            )

        entry_id = raw_entry["entry_id"]
        validate_stable_list_entry_identifier(entry_id, f"{field_name}.entry_id")
        if entry_kind == "played_game":
            if not isinstance(raw_entry["historical_game"], dict):
                raise ValueError(f"{field_name}.historical_game must be an object.")
            entries.append(
                FixedThreePlayerHistoricalPlayedGameEntry(
                    entry_id=entry_id,
                    entry_kind=entry_kind,
                    historical_game=build_historical_game_record(raw_entry["historical_game"]),
                )
            )
            continue

        played_at = raw_entry["played_at"]
        if played_at is not None:
            validate_stable_list_entry_identifier(played_at, f"{field_name}.played_at")
            parse_rfc3339_datetime(played_at, f"{field_name}.played_at")
        entries.append(
            FixedThreePlayerHistoricalPassedDealEntry(
                entry_id=entry_id,
                entry_kind=entry_kind,
                played_at=played_at,
            )
        )
    return tuple(entries)


def _resolve_canonical_player_labels(
    players: tuple[FixedThreePlayerHistoricalListPlayer, ...],
    entries: tuple[FixedThreePlayerHistoricalListEntry, ...],
) -> tuple[FixedThreePlayerHistoricalListPlayer, ...]:
    labels_by_player_id = {
        player.player_id: ([] if player.player_label is None else [player.player_label])
        for player in players
    }
    for entry in entries:
        if not isinstance(entry, FixedThreePlayerHistoricalPlayedGameEntry):
            continue
        for historical_player in entry.historical_game.players:
            if historical_player.player_id in labels_by_player_id:
                if historical_player.player_label is not None:
                    labels_by_player_id[historical_player.player_id].append(
                        historical_player.player_label
                    )

    resolved_players = []
    for player in players:
        labels = labels_by_player_id[player.player_id]
        distinct_labels = tuple(dict.fromkeys(labels))
        if len(distinct_labels) > 1:
            raise ValueError(
                f"Stable player {player.player_id!r} has conflicting non-null labels: "
                f"{list(distinct_labels)}."
            )
        canonical_label = distinct_labels[0] if distinct_labels else None
        resolved_players.append(replace(player, player_label=canonical_label))
    return tuple(resolved_players)


def _validate_entry_ids(entries: tuple[FixedThreePlayerHistoricalListEntry, ...]) -> None:
    entry_ids = [entry.entry_id for entry in entries]
    duplicate_entry_ids = sorted(
        entry_id for entry_id, count in Counter(entry_ids).items() if count > 1
    )
    if duplicate_entry_ids:
        raise ValueError(
            f"historical_list.entries contains duplicate entry_id values: {duplicate_entry_ids}."
        )

    game_ids = [
        entry.historical_game.game_id
        for entry in entries
        if isinstance(entry, FixedThreePlayerHistoricalPlayedGameEntry)
    ]
    duplicate_game_ids = sorted(
        game_id for game_id, count in Counter(game_ids).items() if count > 1
    )
    if duplicate_game_ids:
        raise ValueError(
            f"historical_list.entries contains duplicate historical game IDs: {duplicate_game_ids}."
        )


def _entry_played_at(entry: FixedThreePlayerHistoricalListEntry) -> str | None:
    if isinstance(entry, FixedThreePlayerHistoricalPlayedGameEntry):
        return entry.historical_game.played_at
    return entry.played_at


def _validate_timestamp_order(
    entries: tuple[FixedThreePlayerHistoricalListEntry, ...],
) -> None:
    previous_instant = None
    previous_entry_number = None
    for entry_number, entry in enumerate(entries, start=1):
        played_at = _entry_played_at(entry)
        if played_at is None:
            continue
        instant = parse_rfc3339_datetime(
            played_at,
            f"historical_list.entries[{entry_number - 1}].played_at",
        )
        if previous_instant is not None and instant < previous_instant:
            raise ValueError(
                "Present historical list timestamps must be non-decreasing; "
                f"entry {entry_number} precedes entry {previous_entry_number}."
            )
        previous_instant = instant
        previous_entry_number = entry_number


def _build_fixed_three_player_historical_list(
    data: dict[str, Any],
    *,
    _entry_facts_output: list[tuple[FixedThreePlayerHistoricalListEntryFact, ...]] | None = None,
) -> FixedThreePlayerHistoricalList:
    """Builds one list and optionally returns its already-derived Entry Facts."""
    if not isinstance(data, dict):
        raise ValueError("historical_list must be an object.")
    _require_exact_fields(
        data,
        required_fields={"schema_version", "list_id", "players", "entries"},
        field_name="historical_list",
    )
    schema_version = data["schema_version"]
    if (
        isinstance(schema_version, bool)
        or not isinstance(schema_version, int)
        or schema_version != FIXED_THREE_PLAYER_HISTORICAL_LIST_SCHEMA_VERSION
    ):
        raise ValueError("historical_list.schema_version must currently equal 1.")
    list_id = data["list_id"]
    validate_stable_list_entry_identifier(list_id, "historical_list.list_id")
    players = _build_players(data["players"])
    entries = _build_entries(data["entries"])
    _validate_entry_ids(entries)
    players = _resolve_canonical_player_labels(players, entries)
    result = FixedThreePlayerHistoricalList(
        schema_version=schema_version,
        list_id=list_id,
        players=players,
        entries=entries,
    )
    _validate_timestamp_order(entries)
    facts = build_fixed_three_player_historical_list_entry_facts(result)
    if _entry_facts_output is not None:
        _entry_facts_output.append(facts)
    return result


def build_fixed_three_player_historical_list(
    data: dict[str, Any],
) -> FixedThreePlayerHistoricalList:
    """Builds and fully validates one internal version-1 historical list."""
    return _build_fixed_three_player_historical_list(data)


def _extract_played_game_facts(
    entry: FixedThreePlayerHistoricalPlayedGameEntry,
    *,
    list_player_ids: tuple[str, ...],
    seat_assignment: FixedThreePlayerListSeatAssignment,
) -> tuple[str, int]:
    historical_game = entry.historical_game
    historical_player_ids = {player.player_id for player in historical_game.players}
    if historical_player_ids != set(list_player_ids):
        missing = sorted(set(list_player_ids) - historical_player_ids)
        additional = sorted(historical_player_ids - set(list_player_ids))
        raise ValueError(
            f"Historical game {historical_game.game_id!r} must contain the exact "
            f"fixed list players; missing={missing}, additional={additional}."
        )

    player_id_by_seat = {player.seat: player.player_id for player in historical_game.players}
    expected_player_id_by_seat = dict(
        zip(
            HISTORICAL_SEATS,
            (
                seat_assignment.forehand_player_id,
                seat_assignment.middlehand_player_id,
                seat_assignment.rearhand_player_id,
            ),
            strict=True,
        )
    )
    if tuple(player_id_by_seat) != HISTORICAL_SEATS:
        player_id_by_seat = {seat: player_id_by_seat[seat] for seat in HISTORICAL_SEATS}
    if player_id_by_seat != expected_player_id_by_seat:
        raise ValueError(
            f"Historical game {historical_game.game_id!r} seats do not match the "
            "derived list rotation."
        )

    summary = build_historical_game_summary(historical_game)
    if summary.get("status") != "complete":
        raise ValueError(f"Historical game {historical_game.game_id!r} summary must be complete.")
    settlement = summary.get("final_settlement_summary")
    if not isinstance(settlement, dict) or settlement.get("is_complete") is not True:
        raise ValueError(
            f"Historical game {historical_game.game_id!r} requires complete final settlement."
        )
    outcome = get_game_outcome_for_rating(settlement)
    if outcome not in {"declarer_win", "declarer_loss"}:
        raise ValueError(
            f"Historical game {historical_game.game_id!r} has unsupported settlement outcome."
        )
    settlement_score = settlement.get("settlement_score")
    if isinstance(settlement_score, bool) or not isinstance(settlement_score, int):
        raise ValueError(
            f"Historical game {historical_game.game_id!r} settlement score must be an integer."
        )
    if outcome == "declarer_win" and settlement_score <= 0:
        raise ValueError("A declarer win requires a positive settlement score.")
    if outcome == "declarer_loss" and settlement_score >= 0:
        raise ValueError("A declarer loss requires a negative settlement score.")
    return outcome, settlement_score


def build_fixed_three_player_historical_list_entry_facts(
    historical_list: FixedThreePlayerHistoricalList,
) -> tuple[FixedThreePlayerHistoricalListEntryFact, ...]:
    """Derives and reconciles all 36 authoritative non-cumulative entry facts."""
    player_ids = tuple(player.player_id for player in historical_list.players)
    player_id_by_place = {
        player.table_place: player.player_id for player in historical_list.players
    }
    facts = []
    for entry_number, entry in enumerate(historical_list.entries, start=1):
        seat_assignment = build_fixed_three_player_list_seat_assignment(
            entry_number,
            player_id_by_place,
        )
        round_number = (entry_number - 1) // FIXED_THREE_PLAYER_LIST_ENTRIES_PER_ROUND + 1
        if isinstance(entry, FixedThreePlayerHistoricalPlayedGameEntry):
            entry_outcome, settlement_score = _extract_played_game_facts(
                entry,
                list_player_ids=player_ids,
                seat_assignment=seat_assignment,
            )
            historical_game = entry.historical_game
            declarer_player_id = historical_game.declarer_player_id
            game_id = historical_game.game_id
            game_end_reason = historical_game.game_end_reason
            played_at = historical_game.played_at
        else:
            entry_outcome = "passed_deal"
            settlement_score = None
            declarer_player_id = None
            game_id = None
            game_end_reason = None
            played_at = entry.played_at

        facts.append(
            FixedThreePlayerHistoricalListEntryFact(
                schema_version=FIXED_THREE_PLAYER_HISTORICAL_LIST_SCHEMA_VERSION,
                list_id=historical_list.list_id,
                entry_number=entry_number,
                round_number=round_number,
                entry_id=entry.entry_id,
                entry_kind=entry.entry_kind,
                entry_outcome=entry_outcome,
                played_at=played_at,
                dealer_player_id=seat_assignment.dealer_player_id,
                seat_assignment=seat_assignment,
                game_id=game_id,
                game_end_reason=game_end_reason,
                declarer_player_id=declarer_player_id,
                settlement_score=settlement_score,
                player_contributions=build_fixed_three_player_list_contributions(
                    player_ids=player_ids,
                    entry_outcome=entry_outcome,
                    declarer_player_id=declarer_player_id,
                    settlement_score=settlement_score,
                ),
            )
        )
    result = tuple(facts)
    _reconcile_entry_facts(result, player_ids)
    return result


def _reconcile_entry_facts(
    facts: tuple[FixedThreePlayerHistoricalListEntryFact, ...],
    player_ids: tuple[str, ...],
) -> None:
    if len(facts) != FIXED_THREE_PLAYER_LIST_ENTRY_COUNT:
        raise ValueError("Historical list facts must contain exactly 36 entries.")
    played_count = sum(fact.entry_kind == "played_game" for fact in facts)
    passed_count = sum(fact.entry_kind == "passed_deal" for fact in facts)
    if played_count + passed_count != FIXED_THREE_PLAYER_LIST_ENTRY_COUNT:
        raise ValueError("Played and passed list facts must total 36.")
    if {fact.round_number for fact in facts} != set(
        range(1, FIXED_THREE_PLAYER_LIST_ROUND_COUNT + 1)
    ):
        raise ValueError("Historical list facts must cover exactly twelve rounds.")
    dealer_counts = Counter(fact.dealer_player_id for fact in facts)
    if any(
        dealer_counts[player_id] != FIXED_THREE_PLAYER_LIST_ROUND_COUNT for player_id in player_ids
    ):
        raise ValueError("Every fixed list player must deal exactly twelve entries.")

    for fact in facts:
        contributions = fact.player_contributions
        if len(contributions) != FIXED_THREE_PLAYER_LIST_PLAYER_COUNT:
            raise ValueError("Every list entry must contain three player contributions.")
        if tuple(item.player_id for item in contributions) != player_ids:
            raise ValueError("List contribution order must match canonical player order.")
        declarer_roles = sum(item.declarer_game_count for item in contributions)
        defender_roles = sum(item.defender_game_count for item in contributions)
        if fact.entry_kind == "passed_deal":
            if declarer_roles or defender_roles:
                raise ValueError("A passed deal cannot contain declarer or defender roles.")
            if any(
                item.played_game_count
                or item.own_game_bonus_points
                or item.opponent_loss_bonus_points
                or item.total_performance_points
                for item in contributions
            ):
                raise ValueError("A passed deal must have zero game and point contributions.")
        elif declarer_roles != 1 or defender_roles != 2:
            raise ValueError("A played game must contain one declarer and two defenders.")

        expected_bonus_count = 2 if fact.entry_outcome == "declarer_loss" else 0
        actual_bonus_count = sum(
            item.opponent_loss_bonus_points == ISKO_COUNTERPARTY_LOSS_BONUS_THREE_PLAYER_TABLE
            for item in contributions
        )
        if actual_bonus_count != expected_bonus_count:
            raise ValueError("Declarer-loss entries must contain exactly two +40 bonuses.")

        for item in contributions:
            if item.list_entry_count != 1:
                raise ValueError("Every per-entry contribution must count one list entry.")
            expected_points = calculate_isko_list_performance_points(
                player_game_points=item.player_game_points,
                own_games_won=item.own_games_won,
                own_games_lost=item.own_games_lost,
                other_players_lost_games=item.other_players_lost_games,
            )
            if (
                item.own_game_bonus_points != expected_points["own_game_bonus_points"]
                or item.opponent_loss_bonus_points != expected_points["opponent_loss_bonus_points"]
                or item.total_performance_points != expected_points["total_performance_points"]
            ):
                raise ValueError("A per-entry contribution does not match the performance formula.")


def build_serializable_fixed_three_player_historical_list_player(
    player: FixedThreePlayerHistoricalListPlayer,
) -> dict[str, Any]:
    """Serializes one canonical fixed list participant."""
    return {
        "player_id": player.player_id,
        "player_label": player.player_label,
        "table_place": player.table_place,
    }


def build_serializable_fixed_three_player_historical_list_entry(
    entry: FixedThreePlayerHistoricalListEntry,
) -> dict[str, Any]:
    """Serializes one strict played-or-passed entry union member."""
    if isinstance(entry, FixedThreePlayerHistoricalPlayedGameEntry):
        return {
            "entry_id": entry.entry_id,
            "entry_kind": entry.entry_kind,
            "historical_game": build_serializable_historical_record(entry.historical_game),
        }
    return {
        "entry_id": entry.entry_id,
        "entry_kind": entry.entry_kind,
        "played_at": entry.played_at,
    }


def build_serializable_fixed_three_player_historical_list(
    historical_list: FixedThreePlayerHistoricalList,
) -> dict[str, Any]:
    """Serializes one complete list without sorting players or entries."""
    return {
        "schema_version": historical_list.schema_version,
        "list_id": historical_list.list_id,
        "players": [
            build_serializable_fixed_three_player_historical_list_player(player)
            for player in historical_list.players
        ],
        "entries": [
            build_serializable_fixed_three_player_historical_list_entry(entry)
            for entry in historical_list.entries
        ],
    }


def build_serializable_fixed_three_player_historical_list_entry_fact(
    fact: FixedThreePlayerHistoricalListEntryFact,
) -> dict[str, Any]:
    """Serializes one entry fact with nullable passed-deal game fields."""
    return {
        "schema_version": fact.schema_version,
        "list_id": fact.list_id,
        "entry_number": fact.entry_number,
        "round_number": fact.round_number,
        "entry_id": fact.entry_id,
        "entry_kind": fact.entry_kind,
        "entry_outcome": fact.entry_outcome,
        "played_at": fact.played_at,
        "dealer_player_id": fact.dealer_player_id,
        "seat_assignment": build_serializable_fixed_three_player_list_seat_assignment(
            fact.seat_assignment
        ),
        "game_id": fact.game_id,
        "game_end_reason": fact.game_end_reason,
        "declarer_player_id": fact.declarer_player_id,
        "settlement_score": fact.settlement_score,
        "player_contributions": [
            build_serializable_fixed_three_player_list_contribution(contribution)
            for contribution in fact.player_contributions
        ],
    }


def build_serializable_fixed_three_player_historical_list_entry_facts(
    facts: tuple[FixedThreePlayerHistoricalListEntryFact, ...],
) -> list[dict[str, Any]]:
    """Serializes authoritative entry facts without adding totals or ranks."""
    return [
        build_serializable_fixed_three_player_historical_list_entry_fact(fact) for fact in facts
    ]
