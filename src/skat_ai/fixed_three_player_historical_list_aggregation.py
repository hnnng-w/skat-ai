from dataclasses import dataclass
from typing import Any

from skat_ai.fixed_three_player_historical_list import (
    FIXED_THREE_PLAYER_HISTORICAL_LIST_SCHEMA_VERSION,
    FIXED_THREE_PLAYER_LIST_ENTRY_COUNT,
    FIXED_THREE_PLAYER_LIST_ROUND_COUNT,
    FixedThreePlayerHistoricalList,
    FixedThreePlayerHistoricalListEntryFact,
    FixedThreePlayerHistoricalListPlayer,
    FixedThreePlayerHistoricalPassedDealEntry,
    FixedThreePlayerHistoricalPlayedGameEntry,
    _resolve_canonical_player_labels,
    _validate_entry_ids,
    _validate_timestamp_order,
    build_fixed_three_player_historical_list_entry_facts,
)
from skat_ai.fixed_three_player_historical_list_progression import (
    FixedThreePlayerHistoricalListProgressionSnapshot,
    build_serializable_fixed_three_player_historical_list_progression_snapshot,
)
from skat_ai.fixed_three_player_historical_list_standings import (
    FixedThreePlayerHistoricalListStanding,
    build_fixed_three_player_historical_list_standings,
    build_serializable_fixed_three_player_historical_list_standing,
)
from skat_ai.fixed_three_player_historical_list_totals import (
    FixedThreePlayerHistoricalListPlayerTotals,
)
from skat_ai.fixed_three_player_list_contribution import (
    FixedThreePlayerListContribution,
    build_fixed_three_player_list_contributions,
)
from skat_ai.fixed_three_player_list_rotation import (
    FIXED_THREE_PLAYER_LIST_TABLE_PLACES,
    FixedThreePlayerListSeatAssignment,
    build_fixed_three_player_list_seat_assignment,
)
from skat_ai.historical_game_end import HISTORICAL_GAME_END_REASONS
from skat_ai.performance_rating import (
    calculate_isko_list_performance_points,
    validate_stable_list_entry_identifier,
    validate_stable_list_player_label,
)
from skat_ai.rfc3339 import parse_rfc3339_datetime

FIXED_THREE_PLAYER_HISTORICAL_LIST_AGGREGATION_VERSION = 1
FIXED_THREE_PLAYER_HISTORICAL_LIST_STANDINGS_BASIS = (
    "fixed_three_player_historical_36_position_list"
)
FIXED_THREE_PLAYER_HISTORICAL_LIST_RANKING_STATUSES = (
    "final",
    "lot_required",
)

_COUNT_FIELDS = (
    "list_entry_count",
    "played_game_count",
    "passed_deal_count",
    "declarer_game_count",
    "defender_game_count",
    "own_games_won",
    "own_games_lost",
    "defender_games_won",
    "defender_games_lost",
    "other_players_lost_games",
)
_POINT_FIELDS = (
    "player_game_points",
    "own_game_bonus_points",
    "opponent_loss_bonus_points",
    "total_performance_points",
)
_NUMERIC_FIELDS = _COUNT_FIELDS + _POINT_FIELDS


@dataclass(frozen=True)
class FixedThreePlayerHistoricalListAggregation:
    """One reconciled version-1 cumulative 36-position list result."""

    aggregation_version: int
    basis: str
    source_list_schema_version: int
    list_id: str
    entry_count: int
    round_count: int
    played_game_count: int
    passed_deal_count: int
    declarer_win_count: int
    declarer_loss_count: int
    player_totals: tuple[FixedThreePlayerHistoricalListPlayerTotals, ...]
    progression: tuple[FixedThreePlayerHistoricalListProgressionSnapshot, ...]
    ranking_status: str
    tied_player_ids: tuple[str, ...]
    lot_required_player_ids: tuple[str, ...]
    applied_lot_order: tuple[str, ...] | None
    final_standings: tuple[FixedThreePlayerHistoricalListStanding, ...]


def _require_integer(value: Any, field_name: str, *, non_negative: bool) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer.")
    if non_negative and value < 0:
        raise ValueError(f"{field_name} must be non-negative.")


def _validate_count_and_formula_invariants(value: Any, field_prefix: str) -> None:
    for field_name in _COUNT_FIELDS:
        _require_integer(
            getattr(value, field_name),
            f"{field_prefix}.{field_name}",
            non_negative=True,
        )
    for field_name in _POINT_FIELDS:
        _require_integer(
            getattr(value, field_name),
            f"{field_prefix}.{field_name}",
            non_negative=False,
        )

    if value.list_entry_count != value.played_game_count + value.passed_deal_count:
        raise ValueError("Played and passed counts must equal list-entry count.")
    if value.played_game_count != value.declarer_game_count + value.defender_game_count:
        raise ValueError("Declarer and defender games must equal played games.")
    if value.declarer_game_count != value.own_games_won + value.own_games_lost:
        raise ValueError("Own wins and losses must equal declarer games.")
    if value.defender_game_count != (value.defender_games_won + value.defender_games_lost):
        raise ValueError("Defender wins and losses must equal defender games.")
    if value.other_players_lost_games != value.defender_games_won:
        raise ValueError("Other-player losses must equal defender wins.")

    expected_points = calculate_isko_list_performance_points(
        player_game_points=value.player_game_points,
        own_games_won=value.own_games_won,
        own_games_lost=value.own_games_lost,
        other_players_lost_games=value.other_players_lost_games,
    )
    if value.own_game_bonus_points != expected_points["own_game_bonus_points"]:
        raise ValueError("Own-game bonus points do not match the performance formula.")
    if value.opponent_loss_bonus_points != expected_points["opponent_loss_bonus_points"]:
        raise ValueError("Opponent-loss bonus points do not match the performance formula.")
    if value.total_performance_points != expected_points["total_performance_points"]:
        raise ValueError("Total performance points do not match the performance formula.")


def validate_fixed_three_player_historical_list_player_totals(
    totals: FixedThreePlayerHistoricalListPlayerTotals,
) -> None:
    """Validates identity, count, role, result, and performance invariants."""
    if not isinstance(totals, FixedThreePlayerHistoricalListPlayerTotals):
        raise ValueError("totals must be historical-list player totals.")
    if not isinstance(totals.player_id, str) or not totals.player_id:
        raise ValueError("totals.player_id must be a stable player ID.")
    if totals.player_id != totals.player_id.strip():
        raise ValueError("totals.player_id must not contain outer whitespace.")
    if totals.player_label is not None and (
        not isinstance(totals.player_label, str)
        or not totals.player_label
        or totals.player_label != totals.player_label.strip()
    ):
        raise ValueError("totals.player_label must be null or a stable label.")
    if totals.table_place not in FIXED_THREE_PLAYER_LIST_TABLE_PLACES:
        raise ValueError("totals.table_place must be a canonical table place.")
    _validate_count_and_formula_invariants(totals, "totals")


def build_fixed_three_player_historical_list_zero_player_totals(
    player: FixedThreePlayerHistoricalListPlayer,
) -> FixedThreePlayerHistoricalListPlayerTotals:
    """Builds immutable zero totals for one validated fixed-list player."""
    if not isinstance(player, FixedThreePlayerHistoricalListPlayer):
        raise ValueError("player must be a fixed historical-list player.")
    totals = FixedThreePlayerHistoricalListPlayerTotals(
        player_id=player.player_id,
        player_label=player.player_label,
        table_place=player.table_place,
        list_entry_count=0,
        played_game_count=0,
        passed_deal_count=0,
        declarer_game_count=0,
        defender_game_count=0,
        own_games_won=0,
        own_games_lost=0,
        defender_games_won=0,
        defender_games_lost=0,
        other_players_lost_games=0,
        player_game_points=0,
        own_game_bonus_points=0,
        opponent_loss_bonus_points=0,
        total_performance_points=0,
    )
    validate_fixed_three_player_historical_list_player_totals(totals)
    return totals


def add_fixed_three_player_historical_list_contribution(
    totals: FixedThreePlayerHistoricalListPlayerTotals,
    contribution: FixedThreePlayerListContribution,
) -> FixedThreePlayerHistoricalListPlayerTotals:
    """Adds one existing immutable entry contribution to immutable totals."""
    validate_fixed_three_player_historical_list_player_totals(totals)
    if not isinstance(contribution, FixedThreePlayerListContribution):
        raise ValueError("contribution must be a fixed-list contribution.")
    _validate_count_and_formula_invariants(contribution, "contribution")
    if contribution.list_entry_count != 1:
        raise ValueError("A contribution must count exactly one list entry.")
    if contribution.player_id != totals.player_id:
        raise ValueError("Contribution player ID must match cumulative totals.")

    values = {
        field_name: getattr(totals, field_name) + getattr(contribution, field_name)
        for field_name in _NUMERIC_FIELDS
    }
    result = FixedThreePlayerHistoricalListPlayerTotals(
        player_id=totals.player_id,
        player_label=totals.player_label,
        table_place=totals.table_place,
        **values,
    )
    validate_fixed_three_player_historical_list_player_totals(result)
    return result


def _add_contributions(
    player_totals: tuple[FixedThreePlayerHistoricalListPlayerTotals, ...],
    contributions: tuple[FixedThreePlayerListContribution, ...],
) -> tuple[FixedThreePlayerHistoricalListPlayerTotals, ...]:
    if tuple(total.player_id for total in player_totals) != tuple(
        contribution.player_id for contribution in contributions
    ):
        raise ValueError("Contribution order must match canonical cumulative totals.")
    return tuple(
        add_fixed_three_player_historical_list_contribution(total, contribution)
        for total, contribution in zip(player_totals, contributions, strict=True)
    )


def _reconcile_totals(
    player_totals: tuple[FixedThreePlayerHistoricalListPlayerTotals, ...],
    *,
    entry_count: int,
    played_game_count: int,
    passed_deal_count: int,
    declarer_win_count: int,
    declarer_loss_count: int,
    settlement_score_sum: int,
) -> None:
    if played_game_count + passed_deal_count != entry_count:
        raise ValueError("Played and passed entries must equal list entries.")
    if declarer_win_count + declarer_loss_count != played_game_count:
        raise ValueError("Declarer wins and losses must equal played entries.")
    if any(total.list_entry_count != entry_count for total in player_totals):
        raise ValueError("Every player must count every authoritative list entry.")
    for total in player_totals:
        validate_fixed_three_player_historical_list_player_totals(total)

    expected_sums = {
        "list_entry_count": 3 * entry_count,
        "played_game_count": 3 * played_game_count,
        "passed_deal_count": 3 * passed_deal_count,
        "declarer_game_count": played_game_count,
        "defender_game_count": 2 * played_game_count,
        "own_games_won": declarer_win_count,
        "own_games_lost": declarer_loss_count,
        "defender_games_won": 2 * declarer_loss_count,
        "defender_games_lost": 2 * declarer_win_count,
        "other_players_lost_games": 2 * declarer_loss_count,
        "player_game_points": settlement_score_sum,
    }
    for field_name, expected in expected_sums.items():
        actual = sum(getattr(total, field_name) for total in player_totals)
        if actual != expected:
            raise ValueError(
                f"Cross-player {field_name} total must equal {expected}; got {actual}."
            )


def _validate_progression_delta(
    snapshot: FixedThreePlayerHistoricalListProgressionSnapshot,
    previous: FixedThreePlayerHistoricalListProgressionSnapshot | None,
) -> None:
    expected_entry_number = 1 if previous is None else previous.entry_fact.entry_number + 1
    if snapshot.entry_fact.entry_number != expected_entry_number:
        raise ValueError("Progression snapshots must follow authoritative entry order.")
    expected_round_number = (expected_entry_number - 1) // 3 + 1
    if snapshot.entry_fact.round_number != expected_round_number:
        raise ValueError("Progression snapshots must use authoritative round numbers.")
    if snapshot.aggregation_version != (FIXED_THREE_PLAYER_HISTORICAL_LIST_AGGREGATION_VERSION):
        raise ValueError("Progression snapshot uses an unsupported aggregation version.")
    if snapshot.entry_fact.list_id != snapshot.list_id or (
        previous is not None and previous.list_id != snapshot.list_id
    ):
        raise ValueError("Progression snapshots must preserve list identity.")

    previous_by_player_id = (
        {}
        if previous is None
        else {total.player_id: total for total in previous.cumulative_player_totals}
    )
    contributions_by_player_id = {
        contribution.player_id: contribution
        for contribution in snapshot.entry_fact.player_contributions
    }
    for total in snapshot.cumulative_player_totals:
        contribution = contributions_by_player_id[total.player_id]
        for field_name in _NUMERIC_FIELDS:
            previous_value = (
                0
                if previous is None
                else getattr(previous_by_player_id[total.player_id], field_name)
            )
            if getattr(total, field_name) - previous_value != getattr(contribution, field_name):
                raise ValueError("A progression contribution was not added exactly once.")
            if previous is not None:
                previous_total = previous_by_player_id[total.player_id]
                if (
                    total.player_label != previous_total.player_label
                    or total.table_place != previous_total.table_place
                ):
                    raise ValueError("Progression must preserve player metadata.")

    expected_standings = build_fixed_three_player_historical_list_standings(
        snapshot.cumulative_player_totals
    )
    if snapshot.provisional_standings != expected_standings.standings or (
        snapshot.tied_player_ids != expected_standings.tied_player_ids
    ):
        raise ValueError("Progression standings do not match cumulative player totals.")


def _build_progression(
    historical_list: FixedThreePlayerHistoricalList,
    facts: tuple,
) -> tuple[FixedThreePlayerHistoricalListProgressionSnapshot, ...]:
    player_totals = tuple(
        build_fixed_three_player_historical_list_zero_player_totals(player)
        for player in historical_list.players
    )
    snapshots = []
    previous = None
    for fact in facts:
        player_totals = _add_contributions(player_totals, fact.player_contributions)
        standings_result = build_fixed_three_player_historical_list_standings(player_totals)
        snapshot = FixedThreePlayerHistoricalListProgressionSnapshot(
            aggregation_version=(FIXED_THREE_PLAYER_HISTORICAL_LIST_AGGREGATION_VERSION),
            list_id=historical_list.list_id,
            entry_fact=fact,
            cumulative_player_totals=player_totals,
            provisional_standings=standings_result.standings,
            tied_player_ids=standings_result.tied_player_ids,
        )
        prefix_facts = facts[: fact.entry_number]
        played_count = sum(item.entry_kind == "played_game" for item in prefix_facts)
        passed_count = len(prefix_facts) - played_count
        win_count = sum(item.entry_outcome == "declarer_win" for item in prefix_facts)
        loss_count = sum(item.entry_outcome == "declarer_loss" for item in prefix_facts)
        settlement_sum = sum(
            item.settlement_score or 0 for item in prefix_facts if item.entry_kind == "played_game"
        )
        _reconcile_totals(
            player_totals,
            entry_count=fact.entry_number,
            played_game_count=played_count,
            passed_deal_count=passed_count,
            declarer_win_count=win_count,
            declarer_loss_count=loss_count,
            settlement_score_sum=settlement_sum,
        )
        _validate_progression_delta(snapshot, previous)
        snapshots.append(snapshot)
        previous = snapshot
    return tuple(snapshots)


def _validate_historical_list_source(
    historical_list: FixedThreePlayerHistoricalList,
) -> None:
    if not isinstance(historical_list, FixedThreePlayerHistoricalList):
        raise ValueError("historical_list must be a validated historical list.")
    if (
        isinstance(historical_list.schema_version, bool)
        or not isinstance(historical_list.schema_version, int)
        or historical_list.schema_version != FIXED_THREE_PLAYER_HISTORICAL_LIST_SCHEMA_VERSION
    ):
        raise ValueError("historical_list must use source schema version 1.")
    validate_stable_list_entry_identifier(
        historical_list.list_id,
        "historical_list.list_id",
    )
    if not isinstance(historical_list.players, tuple) or len(historical_list.players) != 3:
        raise ValueError("historical_list must contain exactly three players.")
    for index, player in enumerate(historical_list.players):
        if not isinstance(player, FixedThreePlayerHistoricalListPlayer):
            raise ValueError("historical_list players must use the version-1 contract.")
        validate_stable_list_entry_identifier(
            player.player_id,
            f"historical_list.players[{index}].player_id",
        )
        if player.player_label is not None:
            validate_stable_list_player_label(
                player.player_label,
                f"historical_list.players[{index}].player_label",
            )
    if len({player.player_id for player in historical_list.players}) != 3:
        raise ValueError("historical_list players must identify three distinct players.")
    if tuple(player.table_place for player in historical_list.players) != (
        FIXED_THREE_PLAYER_LIST_TABLE_PLACES
    ):
        raise ValueError("historical_list players must use canonical table-place order.")
    if (
        not isinstance(historical_list.entries, tuple)
        or len(historical_list.entries) != FIXED_THREE_PLAYER_LIST_ENTRY_COUNT
    ):
        raise ValueError("historical_list must contain exactly 36 entries.")
    for index, entry in enumerate(historical_list.entries):
        if not isinstance(
            entry,
            (
                FixedThreePlayerHistoricalPlayedGameEntry,
                FixedThreePlayerHistoricalPassedDealEntry,
            ),
        ):
            raise ValueError("historical_list entries must use the version-1 union.")
        validate_stable_list_entry_identifier(
            entry.entry_id,
            f"historical_list.entries[{index}].entry_id",
        )
        if isinstance(entry, FixedThreePlayerHistoricalPlayedGameEntry):
            if entry.entry_kind != "played_game":
                raise ValueError("Played historical-list entries must use played_game.")
        elif isinstance(entry, FixedThreePlayerHistoricalPassedDealEntry):
            if entry.entry_kind != "passed_deal":
                raise ValueError("Passed historical-list entries must use passed_deal.")
            if entry.played_at is not None:
                validate_stable_list_entry_identifier(
                    entry.played_at,
                    f"historical_list.entries[{index}].played_at",
                )
    _validate_entry_ids(historical_list.entries)
    _validate_timestamp_order(historical_list.entries)
    if (
        _resolve_canonical_player_labels(
            historical_list.players,
            historical_list.entries,
        )
        != historical_list.players
    ):
        raise ValueError("historical_list players must use canonical labels.")


def _validate_final_aggregation(
    aggregation: FixedThreePlayerHistoricalListAggregation,
    *,
    settlement_score_sum: int,
) -> None:
    if aggregation.aggregation_version != 1:
        raise ValueError("Unsupported historical-list aggregation version.")
    if aggregation.basis != FIXED_THREE_PLAYER_HISTORICAL_LIST_STANDINGS_BASIS:
        raise ValueError("Unsupported historical-list standings basis.")
    if aggregation.entry_count != FIXED_THREE_PLAYER_LIST_ENTRY_COUNT:
        raise ValueError("Final aggregation must contain exactly 36 entries.")
    if aggregation.round_count != FIXED_THREE_PLAYER_LIST_ROUND_COUNT:
        raise ValueError("Final aggregation must contain exactly twelve rounds.")
    if len(aggregation.progression) != aggregation.entry_count:
        raise ValueError("Progression must contain one snapshot per list entry.")
    if aggregation.progression[-1].cumulative_player_totals != aggregation.player_totals:
        raise ValueError("Final progression totals must equal final player totals.")
    _reconcile_totals(
        aggregation.player_totals,
        entry_count=aggregation.entry_count,
        played_game_count=aggregation.played_game_count,
        passed_deal_count=aggregation.passed_deal_count,
        declarer_win_count=aggregation.declarer_win_count,
        declarer_loss_count=aggregation.declarer_loss_count,
        settlement_score_sum=settlement_score_sum,
    )

    standings_ids = tuple(
        standing.player_totals.player_id for standing in aggregation.final_standings
    )
    if set(standings_ids) != {total.player_id for total in aggregation.player_totals}:
        raise ValueError("Final standings must contain every player exactly once.")
    if aggregation.ranking_status not in (FIXED_THREE_PLAYER_HISTORICAL_LIST_RANKING_STATUSES):
        raise ValueError("Unsupported final ranking status.")
    unresolved_tie = bool(aggregation.tied_player_ids) and (aggregation.applied_lot_order is None)
    expected_status = "lot_required" if unresolved_tie else "final"
    expected_lot_required_ids = aggregation.tied_player_ids if unresolved_tie else ()
    if aggregation.ranking_status != expected_status or (
        aggregation.lot_required_player_ids != expected_lot_required_ids
    ):
        raise ValueError("Final ranking status does not match tie and lot fields.")
    if aggregation.applied_lot_order is not None and (
        set(aggregation.applied_lot_order) != set(aggregation.tied_player_ids)
    ):
        raise ValueError("Applied lot order must equal the unresolved tie group.")

    expected_standings = build_fixed_three_player_historical_list_standings(
        aggregation.player_totals,
        lot_order=(
            None if aggregation.applied_lot_order is None else list(aggregation.applied_lot_order)
        ),
    )
    if aggregation.final_standings != expected_standings.standings:
        raise ValueError("Final standings do not match final player totals.")
    if aggregation.tied_player_ids != expected_standings.tied_player_ids:
        raise ValueError("Final tied player IDs do not match the ranking metrics.")


def _validate_stable_player_id_tuple(
    value: Any,
    field_name: str,
    *,
    known_player_ids: set[str],
) -> None:
    if not isinstance(value, tuple):
        raise ValueError(f"{field_name} must be an immutable tuple.")
    for index, player_id in enumerate(value):
        validate_stable_list_entry_identifier(
            player_id,
            f"{field_name}[{index}]",
        )
    if len(set(value)) != len(value):
        raise ValueError(f"{field_name} must not contain duplicate player IDs.")
    if not set(value).issubset(known_player_ids):
        raise ValueError(f"{field_name} contains an unknown player ID.")


def _validate_player_totals_tuple(
    value: Any,
    field_name: str,
    *,
    expected_metadata: tuple[tuple[str, str | None, str], ...] | None = None,
) -> tuple[FixedThreePlayerHistoricalListPlayerTotals, ...]:
    if not isinstance(value, tuple) or len(value) != 3:
        raise ValueError(f"{field_name} must contain exactly three immutable totals.")
    for total in value:
        validate_fixed_three_player_historical_list_player_totals(total)
    if tuple(total.table_place for total in value) != FIXED_THREE_PLAYER_LIST_TABLE_PLACES:
        raise ValueError(f"{field_name} must use canonical table-place order.")
    if len({total.player_id for total in value}) != 3:
        raise ValueError(f"{field_name} must identify three distinct players.")
    metadata = tuple((total.player_id, total.player_label, total.table_place) for total in value)
    if expected_metadata is not None and metadata != expected_metadata:
        raise ValueError(f"{field_name} must preserve canonical player metadata.")
    return value


def _validate_standings_tuple(
    value: Any,
    field_name: str,
) -> tuple[FixedThreePlayerHistoricalListStanding, ...]:
    if not isinstance(value, tuple) or len(value) != 3:
        raise ValueError(f"{field_name} must contain exactly three immutable standings.")
    for index, standing in enumerate(value):
        if not isinstance(standing, FixedThreePlayerHistoricalListStanding):
            raise ValueError(f"{field_name}[{index}] must be a historical-list standing.")
        _require_integer(
            standing.rank,
            f"{field_name}[{index}].rank",
            non_negative=True,
        )
        if standing.rank < 1:
            raise ValueError(f"{field_name}[{index}].rank must be positive.")
        validate_fixed_three_player_historical_list_player_totals(standing.player_totals)
    return value


def _validate_retained_entry_fact(
    fact: Any,
    *,
    aggregation: FixedThreePlayerHistoricalListAggregation,
    entry_number: int,
    player_ids: tuple[str, ...],
    player_id_by_place: dict[str, str],
) -> tuple[FixedThreePlayerListContribution, ...]:
    field_name = f"aggregation.progression[{entry_number - 1}].entry_fact"
    if not isinstance(fact, FixedThreePlayerHistoricalListEntryFact):
        raise ValueError(f"{field_name} must use the version-1 entry-fact contract.")
    _require_integer(fact.schema_version, f"{field_name}.schema_version", non_negative=True)
    _require_integer(fact.entry_number, f"{field_name}.entry_number", non_negative=True)
    _require_integer(fact.round_number, f"{field_name}.round_number", non_negative=True)
    if fact.schema_version != aggregation.source_list_schema_version:
        raise ValueError("Progression Entry Facts must use the source schema version.")
    if fact.list_id != aggregation.list_id:
        raise ValueError("Progression Entry Facts must preserve list identity.")
    if fact.entry_number != entry_number:
        raise ValueError("Progression Entry Facts must follow authoritative entry order.")
    if fact.round_number != (entry_number - 1) // 3 + 1:
        raise ValueError("Progression Entry Facts must use authoritative round numbers.")
    validate_stable_list_entry_identifier(fact.entry_id, f"{field_name}.entry_id")
    if fact.played_at is not None:
        validate_stable_list_entry_identifier(fact.played_at, f"{field_name}.played_at")
        parse_rfc3339_datetime(fact.played_at, f"{field_name}.played_at")

    expected_assignment = build_fixed_three_player_list_seat_assignment(
        entry_number,
        player_id_by_place,
    )
    if not isinstance(fact.seat_assignment, FixedThreePlayerListSeatAssignment) or (
        fact.seat_assignment != expected_assignment
    ):
        raise ValueError("Progression Entry Facts must preserve dealer and seat rotation.")
    if fact.dealer_player_id != expected_assignment.dealer_player_id:
        raise ValueError("Progression Entry Facts must preserve dealer identity.")

    if fact.entry_kind == "played_game":
        if fact.entry_outcome not in {"declarer_win", "declarer_loss"}:
            raise ValueError("A played Entry Fact must contain a declarer outcome.")
        validate_stable_list_entry_identifier(fact.game_id, f"{field_name}.game_id")
        if fact.game_end_reason not in HISTORICAL_GAME_END_REASONS:
            raise ValueError("A played Entry Fact must contain a supported end reason.")
        if fact.declarer_player_id not in player_ids:
            raise ValueError("A played Entry Fact declarer must be one fixed player.")
        _require_integer(
            fact.settlement_score,
            f"{field_name}.settlement_score",
            non_negative=False,
        )
        if fact.entry_outcome == "declarer_win" and fact.settlement_score <= 0:
            raise ValueError("A declarer-win Entry Fact requires a positive settlement score.")
        if fact.entry_outcome == "declarer_loss" and fact.settlement_score >= 0:
            raise ValueError("A declarer-loss Entry Fact requires a negative settlement score.")
    elif fact.entry_kind == "passed_deal":
        if fact.entry_outcome != "passed_deal" or any(
            value is not None
            for value in (
                fact.game_id,
                fact.game_end_reason,
                fact.declarer_player_id,
                fact.settlement_score,
            )
        ):
            raise ValueError("A Passed Deal Entry Fact must not contain game fields.")
    else:
        raise ValueError("Progression Entry Facts must use played_game or passed_deal.")

    if not isinstance(fact.player_contributions, tuple) or len(fact.player_contributions) != 3:
        raise ValueError("Every retained Entry Fact must contain three contributions.")
    for contribution in fact.player_contributions:
        if not isinstance(contribution, FixedThreePlayerListContribution):
            raise ValueError("Entry Fact contributions must use the version-1 contract.")
        _validate_count_and_formula_invariants(contribution, "entry_fact.contribution")
        if contribution.list_entry_count != 1:
            raise ValueError("Every Entry Fact contribution must count one list entry.")
    expected_contributions = build_fixed_three_player_list_contributions(
        player_ids=player_ids,
        entry_outcome=fact.entry_outcome,
        declarer_player_id=fact.declarer_player_id,
        settlement_score=fact.settlement_score,
    )
    if fact.player_contributions != expected_contributions:
        raise ValueError("Retained Entry Fact contributions do not match their source facts.")
    return expected_contributions


def validate_fixed_three_player_historical_list_aggregation(
    aggregation: FixedThreePlayerHistoricalListAggregation,
) -> None:
    """Strictly validates one retained immutable version-1 aggregation."""
    if not isinstance(aggregation, FixedThreePlayerHistoricalListAggregation):
        raise ValueError("aggregation must be a historical-list aggregation.")
    _require_integer(
        aggregation.aggregation_version,
        "aggregation.aggregation_version",
        non_negative=True,
    )
    _require_integer(
        aggregation.source_list_schema_version,
        "aggregation.source_list_schema_version",
        non_negative=True,
    )
    if aggregation.aggregation_version != FIXED_THREE_PLAYER_HISTORICAL_LIST_AGGREGATION_VERSION:
        raise ValueError("Unsupported historical-list aggregation version.")
    if aggregation.basis != FIXED_THREE_PLAYER_HISTORICAL_LIST_STANDINGS_BASIS:
        raise ValueError("Unsupported historical-list standings basis.")
    if aggregation.source_list_schema_version != FIXED_THREE_PLAYER_HISTORICAL_LIST_SCHEMA_VERSION:
        raise ValueError("Unsupported historical-list source schema version.")
    validate_stable_list_entry_identifier(aggregation.list_id, "aggregation.list_id")
    for field_name, expected in (
        ("entry_count", FIXED_THREE_PLAYER_LIST_ENTRY_COUNT),
        ("round_count", FIXED_THREE_PLAYER_LIST_ROUND_COUNT),
    ):
        _require_integer(
            getattr(aggregation, field_name),
            f"aggregation.{field_name}",
            non_negative=True,
        )
        if getattr(aggregation, field_name) != expected:
            raise ValueError(f"aggregation.{field_name} must equal {expected}.")
    for field_name in (
        "played_game_count",
        "passed_deal_count",
        "declarer_win_count",
        "declarer_loss_count",
    ):
        _require_integer(
            getattr(aggregation, field_name),
            f"aggregation.{field_name}",
            non_negative=True,
        )

    player_totals = _validate_player_totals_tuple(
        aggregation.player_totals,
        "aggregation.player_totals",
    )
    player_ids = tuple(total.player_id for total in player_totals)
    player_metadata = tuple(
        (total.player_id, total.player_label, total.table_place) for total in player_totals
    )
    player_id_by_place = {total.table_place: total.player_id for total in player_totals}
    known_player_ids = set(player_ids)
    if (
        not isinstance(aggregation.progression, tuple)
        or len(aggregation.progression) != FIXED_THREE_PLAYER_LIST_ENTRY_COUNT
    ):
        raise ValueError("aggregation.progression must contain 36 immutable snapshots.")

    running_totals = tuple(
        build_fixed_three_player_historical_list_zero_player_totals(
            FixedThreePlayerHistoricalListPlayer(
                player_id=total.player_id,
                player_label=total.player_label,
                table_place=total.table_place,
            )
        )
        for total in player_totals
    )
    entry_ids: set[str] = set()
    game_ids: set[str] = set()
    previous_instant = None
    played_count = passed_count = win_count = loss_count = settlement_score_sum = 0
    for entry_number, snapshot in enumerate(aggregation.progression, start=1):
        field_name = f"aggregation.progression[{entry_number - 1}]"
        if not isinstance(snapshot, FixedThreePlayerHistoricalListProgressionSnapshot):
            raise ValueError(f"{field_name} must use the progression snapshot contract.")
        _require_integer(
            snapshot.aggregation_version,
            f"{field_name}.aggregation_version",
            non_negative=True,
        )
        if snapshot.aggregation_version != aggregation.aggregation_version:
            raise ValueError("Progression snapshots must preserve aggregation version.")
        if snapshot.list_id != aggregation.list_id:
            raise ValueError("Progression snapshots must preserve list identity.")
        contributions = _validate_retained_entry_fact(
            snapshot.entry_fact,
            aggregation=aggregation,
            entry_number=entry_number,
            player_ids=player_ids,
            player_id_by_place=player_id_by_place,
        )
        fact = snapshot.entry_fact
        if fact.entry_id in entry_ids:
            raise ValueError("Retained Entry Facts contain duplicate entry IDs.")
        entry_ids.add(fact.entry_id)
        if fact.game_id is not None:
            if fact.game_id in game_ids:
                raise ValueError("Retained Entry Facts contain duplicate game IDs.")
            game_ids.add(fact.game_id)
        if fact.played_at is not None:
            instant = parse_rfc3339_datetime(fact.played_at, f"{field_name}.played_at")
            if previous_instant is not None and instant < previous_instant:
                raise ValueError("Retained Entry Fact timestamps must be non-decreasing.")
            previous_instant = instant

        running_totals = _add_contributions(running_totals, contributions)
        supplied_totals = _validate_player_totals_tuple(
            snapshot.cumulative_player_totals,
            f"{field_name}.cumulative_player_totals",
            expected_metadata=player_metadata,
        )
        if supplied_totals != running_totals:
            raise ValueError("Progression cumulative totals do not match retained facts.")
        if any(total.list_entry_count != entry_number for total in supplied_totals):
            raise ValueError("Progression totals must count every authoritative entry.")

        if fact.entry_kind == "played_game":
            played_count += 1
            settlement_score_sum += fact.settlement_score
            if fact.entry_outcome == "declarer_win":
                win_count += 1
            else:
                loss_count += 1
        else:
            passed_count += 1
        _reconcile_totals(
            supplied_totals,
            entry_count=entry_number,
            played_game_count=played_count,
            passed_deal_count=passed_count,
            declarer_win_count=win_count,
            declarer_loss_count=loss_count,
            settlement_score_sum=settlement_score_sum,
        )

        supplied_standings = _validate_standings_tuple(
            snapshot.provisional_standings,
            f"{field_name}.provisional_standings",
        )
        expected_standings = build_fixed_three_player_historical_list_standings(supplied_totals)
        if supplied_standings != expected_standings.standings:
            raise ValueError("Progression standings do not match cumulative totals.")
        _validate_stable_player_id_tuple(
            snapshot.tied_player_ids,
            f"{field_name}.tied_player_ids",
            known_player_ids=known_player_ids,
        )
        if snapshot.tied_player_ids != expected_standings.tied_player_ids:
            raise ValueError("Progression tied IDs do not match cumulative totals.")

    if running_totals != aggregation.player_totals:
        raise ValueError("Progression endpoint must equal final player totals.")
    expected_counts = (
        played_count,
        passed_count,
        win_count,
        loss_count,
    )
    supplied_counts = (
        aggregation.played_game_count,
        aggregation.passed_deal_count,
        aggregation.declarer_win_count,
        aggregation.declarer_loss_count,
    )
    if supplied_counts != expected_counts:
        raise ValueError("Final aggregation counts do not match retained Entry Facts.")

    if aggregation.ranking_status not in FIXED_THREE_PLAYER_HISTORICAL_LIST_RANKING_STATUSES:
        raise ValueError("Unsupported final ranking status.")
    _validate_stable_player_id_tuple(
        aggregation.tied_player_ids,
        "aggregation.tied_player_ids",
        known_player_ids=known_player_ids,
    )
    _validate_stable_player_id_tuple(
        aggregation.lot_required_player_ids,
        "aggregation.lot_required_player_ids",
        known_player_ids=known_player_ids,
    )
    if aggregation.applied_lot_order is not None:
        _validate_stable_player_id_tuple(
            aggregation.applied_lot_order,
            "aggregation.applied_lot_order",
            known_player_ids=known_player_ids,
        )
        if len(aggregation.applied_lot_order) not in {2, 3}:
            raise ValueError("aggregation.applied_lot_order must contain two or three IDs.")
    _validate_standings_tuple(
        aggregation.final_standings,
        "aggregation.final_standings",
    )
    _validate_final_aggregation(
        aggregation,
        settlement_score_sum=settlement_score_sum,
    )


def build_fixed_three_player_historical_list_aggregation(
    historical_list: FixedThreePlayerHistoricalList,
    *,
    lot_order: Any = None,
) -> FixedThreePlayerHistoricalListAggregation:
    """Builds cumulative progression and final standings from one validated list."""
    _validate_historical_list_source(historical_list)
    facts = build_fixed_three_player_historical_list_entry_facts(historical_list)
    progression = _build_progression(historical_list, facts)
    player_totals = progression[-1].cumulative_player_totals
    standings_result = build_fixed_three_player_historical_list_standings(
        player_totals,
        lot_order=lot_order,
    )

    played_game_count = sum(fact.entry_kind == "played_game" for fact in facts)
    passed_deal_count = len(facts) - played_game_count
    declarer_win_count = sum(fact.entry_outcome == "declarer_win" for fact in facts)
    declarer_loss_count = sum(fact.entry_outcome == "declarer_loss" for fact in facts)
    unresolved_tie = bool(standings_result.tied_player_ids) and lot_order is None
    result = FixedThreePlayerHistoricalListAggregation(
        aggregation_version=FIXED_THREE_PLAYER_HISTORICAL_LIST_AGGREGATION_VERSION,
        basis=FIXED_THREE_PLAYER_HISTORICAL_LIST_STANDINGS_BASIS,
        source_list_schema_version=historical_list.schema_version,
        list_id=historical_list.list_id,
        entry_count=len(facts),
        round_count=max(fact.round_number for fact in facts),
        played_game_count=played_game_count,
        passed_deal_count=passed_deal_count,
        declarer_win_count=declarer_win_count,
        declarer_loss_count=declarer_loss_count,
        player_totals=player_totals,
        progression=progression,
        ranking_status="lot_required" if unresolved_tie else "final",
        tied_player_ids=standings_result.tied_player_ids,
        lot_required_player_ids=(standings_result.tied_player_ids if unresolved_tie else ()),
        applied_lot_order=standings_result.applied_lot_order,
        final_standings=standings_result.standings,
    )
    validate_fixed_three_player_historical_list_aggregation(result)
    return result


def build_serializable_fixed_three_player_historical_list_player_totals(
    totals: FixedThreePlayerHistoricalListPlayerTotals,
) -> dict[str, Any]:
    """Serializes one cumulative player-total row in stable field order."""
    return {
        "player_id": totals.player_id,
        "player_label": totals.player_label,
        "table_place": totals.table_place,
        "list_entry_count": totals.list_entry_count,
        "played_game_count": totals.played_game_count,
        "passed_deal_count": totals.passed_deal_count,
        "declarer_game_count": totals.declarer_game_count,
        "defender_game_count": totals.defender_game_count,
        "own_games_won": totals.own_games_won,
        "own_games_lost": totals.own_games_lost,
        "defender_games_won": totals.defender_games_won,
        "defender_games_lost": totals.defender_games_lost,
        "other_players_lost_games": totals.other_players_lost_games,
        "player_game_points": totals.player_game_points,
        "own_game_bonus_points": totals.own_game_bonus_points,
        "opponent_loss_bonus_points": totals.opponent_loss_bonus_points,
        "total_performance_points": totals.total_performance_points,
    }


def build_serializable_fixed_three_player_historical_list_aggregation(
    aggregation: FixedThreePlayerHistoricalListAggregation,
) -> dict[str, Any]:
    """Serializes only facts, cumulative metrics, ranks, and lot metadata."""
    return {
        "aggregation_version": aggregation.aggregation_version,
        "basis": aggregation.basis,
        "source_list_schema_version": aggregation.source_list_schema_version,
        "list_id": aggregation.list_id,
        "entry_count": aggregation.entry_count,
        "round_count": aggregation.round_count,
        "played_game_count": aggregation.played_game_count,
        "passed_deal_count": aggregation.passed_deal_count,
        "declarer_win_count": aggregation.declarer_win_count,
        "declarer_loss_count": aggregation.declarer_loss_count,
        "player_totals": [
            build_serializable_fixed_three_player_historical_list_player_totals(total)
            for total in aggregation.player_totals
        ],
        "progression": [
            build_serializable_fixed_three_player_historical_list_progression_snapshot(snapshot)
            for snapshot in aggregation.progression
        ],
        "ranking_status": aggregation.ranking_status,
        "tied_player_ids": list(aggregation.tied_player_ids),
        "lot_required_player_ids": list(aggregation.lot_required_player_ids),
        "applied_lot_order": (
            None if aggregation.applied_lot_order is None else list(aggregation.applied_lot_order)
        ),
        "final_standings": [
            build_serializable_fixed_three_player_historical_list_standing(standing)
            for standing in aggregation.final_standings
        ],
    }
