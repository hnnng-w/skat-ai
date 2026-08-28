from dataclasses import fields

from skatmind.fixed_three_player_historical_list_aggregation import (
    FixedThreePlayerHistoricalListAggregation,
    FixedThreePlayerHistoricalListPlayerTotals,
    validate_fixed_three_player_historical_list_aggregation,
)
from skatmind.fixed_three_player_historical_list_comparison_summary import (
    FixedThreePlayerHistoricalListComparisonCompactStanding,
    FixedThreePlayerHistoricalListComparisonResult,
    FixedThreePlayerHistoricalListComparisonSourceSummary,
    FixedThreePlayerHistoricalListPairwiseComparison,
    FixedThreePlayerHistoricalListPlayerComparison,
    FixedThreePlayerHistoricalListPlayerTotalsDelta,
)

FIXED_THREE_PLAYER_HISTORICAL_LIST_COMPARISON_VERSION = 1
FIXED_THREE_PLAYER_HISTORICAL_LIST_COMPARISON_BASIS = (
    "independent_completed_fixed_three_player_historical_lists"
)
MIN_FIXED_THREE_PLAYER_HISTORICAL_LIST_COMPARISON_COUNT = 2
FIXED_THREE_PLAYER_HISTORICAL_LIST_RANK_COMPARISON_STATUSES = (
    "available",
    "reference_lot_required",
    "comparison_lot_required",
    "both_lot_required",
)

_PLAYER_TOTAL_NUMERIC_FIELDS = tuple(
    field.name
    for field in fields(FixedThreePlayerHistoricalListPlayerTotals)
    if field.name not in {"player_id", "player_label", "table_place"}
)


def _totals_by_player_id(
    aggregation: FixedThreePlayerHistoricalListAggregation,
) -> dict[str, FixedThreePlayerHistoricalListPlayerTotals]:
    return {total.player_id: total for total in aggregation.player_totals}


def _build_source_summary(
    aggregation: FixedThreePlayerHistoricalListAggregation,
) -> FixedThreePlayerHistoricalListComparisonSourceSummary:
    return FixedThreePlayerHistoricalListComparisonSourceSummary(
        comparison_version=FIXED_THREE_PLAYER_HISTORICAL_LIST_COMPARISON_VERSION,
        basis=FIXED_THREE_PLAYER_HISTORICAL_LIST_COMPARISON_BASIS,
        list_id=aggregation.list_id,
        source_list_schema_version=aggregation.source_list_schema_version,
        entry_count=aggregation.entry_count,
        round_count=aggregation.round_count,
        played_game_count=aggregation.played_game_count,
        passed_deal_count=aggregation.passed_deal_count,
        declarer_win_count=aggregation.declarer_win_count,
        declarer_loss_count=aggregation.declarer_loss_count,
        ranking_status=aggregation.ranking_status,
        tied_player_ids=aggregation.tied_player_ids,
        lot_required_player_ids=aggregation.lot_required_player_ids,
        applied_lot_order=aggregation.applied_lot_order,
        final_standings=tuple(
            FixedThreePlayerHistoricalListComparisonCompactStanding(
                rank=standing.rank,
                player_id=standing.player_totals.player_id,
                player_label=standing.player_totals.player_label,
                table_place=standing.player_totals.table_place,
                total_performance_points=(standing.player_totals.total_performance_points),
                own_games_won=standing.player_totals.own_games_won,
                own_games_lost=standing.player_totals.own_games_lost,
            )
            for standing in aggregation.final_standings
        ),
    )


def _resolve_canonical_labels(
    aggregations: tuple[FixedThreePlayerHistoricalListAggregation, ...],
    player_ids: tuple[str, ...],
) -> dict[str, str | None]:
    labels_by_player_id: dict[str, list[str]] = {player_id: [] for player_id in player_ids}
    for aggregation in aggregations:
        for total in aggregation.player_totals:
            if total.player_label is not None:
                labels_by_player_id[total.player_id].append(total.player_label)

    result = {}
    for player_id in player_ids:
        labels = labels_by_player_id[player_id]
        distinct_labels = tuple(dict.fromkeys(labels))
        if len(distinct_labels) > 1:
            raise ValueError(
                f"Stable player {player_id!r} has conflicting non-null labels "
                f"across source lists: {list(distinct_labels)}."
            )
        result[player_id] = distinct_labels[0] if distinct_labels else None
    return result


def _build_totals_delta(
    reference: FixedThreePlayerHistoricalListPlayerTotals,
    comparison: FixedThreePlayerHistoricalListPlayerTotals,
) -> FixedThreePlayerHistoricalListPlayerTotalsDelta:
    return FixedThreePlayerHistoricalListPlayerTotalsDelta(
        **{
            field_name: getattr(comparison, field_name) - getattr(reference, field_name)
            for field_name in _PLAYER_TOTAL_NUMERIC_FIELDS
        }
    )


def _rank_comparison_status(
    reference: FixedThreePlayerHistoricalListAggregation,
    comparison: FixedThreePlayerHistoricalListAggregation,
) -> str:
    reference_requires_lot = reference.ranking_status == "lot_required"
    comparison_requires_lot = comparison.ranking_status == "lot_required"
    if reference_requires_lot and comparison_requires_lot:
        return "both_lot_required"
    if reference_requires_lot:
        return "reference_lot_required"
    if comparison_requires_lot:
        return "comparison_lot_required"
    return "available"


def _build_pairwise_comparison(
    reference: FixedThreePlayerHistoricalListAggregation,
    comparison: FixedThreePlayerHistoricalListAggregation,
    *,
    reference_summary: FixedThreePlayerHistoricalListComparisonSourceSummary,
    comparison_summary: FixedThreePlayerHistoricalListComparisonSourceSummary,
    player_ids: tuple[str, ...],
    canonical_labels: dict[str, str | None],
) -> FixedThreePlayerHistoricalListPairwiseComparison:
    reference_totals = _totals_by_player_id(reference)
    comparison_totals = _totals_by_player_id(comparison)
    status = _rank_comparison_status(reference, comparison)
    ranks_available = status == "available"
    reference_ranks = {
        standing.player_totals.player_id: standing.rank for standing in reference.final_standings
    }
    comparison_ranks = {
        standing.player_totals.player_id: standing.rank for standing in comparison.final_standings
    }
    player_comparisons = []
    for player_id in player_ids:
        reference_total = reference_totals[player_id]
        comparison_total = comparison_totals[player_id]
        reference_rank = reference_ranks[player_id] if ranks_available else None
        comparison_rank = comparison_ranks[player_id] if ranks_available else None
        player_comparisons.append(
            FixedThreePlayerHistoricalListPlayerComparison(
                comparison_version=(FIXED_THREE_PLAYER_HISTORICAL_LIST_COMPARISON_VERSION),
                player_id=player_id,
                player_label=canonical_labels[player_id],
                reference_table_place=reference_total.table_place,
                comparison_table_place=comparison_total.table_place,
                reference_totals=reference_total,
                comparison_totals=comparison_total,
                deltas=_build_totals_delta(reference_total, comparison_total),
                rank_comparison_status=status,
                reference_rank=reference_rank,
                comparison_rank=comparison_rank,
                rank_position_change=(
                    None if not ranks_available else reference_rank - comparison_rank
                ),
            )
        )

    return FixedThreePlayerHistoricalListPairwiseComparison(
        comparison_version=FIXED_THREE_PLAYER_HISTORICAL_LIST_COMPARISON_VERSION,
        reference_list_id=reference.list_id,
        comparison_list_id=comparison.list_id,
        reference_summary=reference_summary,
        comparison_summary=comparison_summary,
        played_game_count_delta=(comparison.played_game_count - reference.played_game_count),
        passed_deal_count_delta=(comparison.passed_deal_count - reference.passed_deal_count),
        declarer_win_count_delta=(comparison.declarer_win_count - reference.declarer_win_count),
        declarer_loss_count_delta=(comparison.declarer_loss_count - reference.declarer_loss_count),
        final_rank_comparison_available=ranks_available,
        player_comparisons=tuple(player_comparisons),
    )


def _validate_comparison_result(
    result: FixedThreePlayerHistoricalListComparisonResult,
    aggregations: tuple[FixedThreePlayerHistoricalListAggregation, ...],
    canonical_labels: dict[str, str | None],
) -> None:
    if result.comparison_version != FIXED_THREE_PLAYER_HISTORICAL_LIST_COMPARISON_VERSION:
        raise ValueError("Comparison result uses an unsupported version.")
    if result.basis != FIXED_THREE_PLAYER_HISTORICAL_LIST_COMPARISON_BASIS:
        raise ValueError("Comparison result uses an unsupported basis.")
    if result.list_count != len(aggregations):
        raise ValueError("Comparison result list count does not match its sources.")
    if result.reference_list_id != aggregations[0].list_id:
        raise ValueError("Comparison result must preserve the first source as reference.")
    if result.player_ids != tuple(total.player_id for total in aggregations[0].player_totals):
        raise ValueError("Comparison result must preserve reference player order.")
    expected_summaries = tuple(_build_source_summary(item) for item in aggregations)
    if result.source_lists != expected_summaries:
        raise ValueError("Comparison result source summaries do not match source order.")
    if len(result.comparisons) != len(aggregations) - 1:
        raise ValueError("Comparison result must contain one row per non-reference list.")

    for index, pairwise in enumerate(result.comparisons, start=1):
        expected = _build_pairwise_comparison(
            aggregations[0],
            aggregations[index],
            reference_summary=expected_summaries[0],
            comparison_summary=expected_summaries[index],
            player_ids=result.player_ids,
            canonical_labels=canonical_labels,
        )
        if pairwise != expected:
            raise ValueError("Pairwise comparison does not reconcile with its sources.")
        if tuple(row.player_id for row in pairwise.player_comparisons) != result.player_ids:
            raise ValueError("Player comparisons must preserve reference player order.")
        expected_status = _rank_comparison_status(
            aggregations[0],
            aggregations[index],
        )
        for row in pairwise.player_comparisons:
            if row.rank_comparison_status not in (
                FIXED_THREE_PLAYER_HISTORICAL_LIST_RANK_COMPARISON_STATUSES
            ):
                raise ValueError("Player comparison uses an unsupported rank status.")
            if row.rank_comparison_status != expected_status:
                raise ValueError("Player rank status does not match source rankings.")
            ranks = (row.reference_rank, row.comparison_rank, row.rank_position_change)
            if expected_status == "available":
                if any(isinstance(value, bool) or not isinstance(value, int) for value in ranks):
                    raise ValueError("Available rank comparisons require integer ranks.")
                if row.rank_position_change != row.reference_rank - row.comparison_rank:
                    raise ValueError("Rank-position change does not match source ranks.")
            elif ranks != (None, None, None):
                raise ValueError("Unresolved rank comparisons require null rank fields.")


def build_fixed_three_player_historical_list_comparison(
    aggregations: tuple[FixedThreePlayerHistoricalListAggregation, ...],
) -> FixedThreePlayerHistoricalListComparisonResult:
    """Compares each later completed list independently with the first source."""
    if not isinstance(aggregations, tuple):
        raise ValueError("aggregations must be an immutable tuple.")
    if len(aggregations) < MIN_FIXED_THREE_PLAYER_HISTORICAL_LIST_COMPARISON_COUNT:
        raise ValueError("aggregations must contain at least two completed lists.")
    for aggregation in aggregations:
        validate_fixed_three_player_historical_list_aggregation(aggregation)

    list_ids = tuple(aggregation.list_id for aggregation in aggregations)
    if len(set(list_ids)) != len(list_ids):
        raise ValueError("Independent source lists must use unique list_id values.")
    seen_game_ids: dict[str, str] = {}
    for aggregation in aggregations:
        for snapshot in aggregation.progression:
            game_id = snapshot.entry_fact.game_id
            if game_id is None:
                continue
            if game_id in seen_game_ids:
                raise ValueError(
                    f"Played Game ID {game_id!r} is reused across source lists "
                    f"{seen_game_ids[game_id]!r} and {aggregation.list_id!r}."
                )
            seen_game_ids[game_id] = aggregation.list_id

    player_ids = tuple(total.player_id for total in aggregations[0].player_totals)
    reference_player_set = set(player_ids)
    for aggregation in aggregations[1:]:
        source_player_set = {total.player_id for total in aggregation.player_totals}
        if source_player_set != reference_player_set:
            missing = sorted(reference_player_set - source_player_set)
            additional = sorted(source_player_set - reference_player_set)
            raise ValueError(
                "Independent source lists must contain the same stable players; "
                f"missing={missing}, additional={additional}."
            )

    canonical_labels = _resolve_canonical_labels(aggregations, player_ids)
    source_summaries = tuple(_build_source_summary(item) for item in aggregations)
    reference = aggregations[0]
    comparisons = tuple(
        _build_pairwise_comparison(
            reference,
            comparison,
            reference_summary=source_summaries[0],
            comparison_summary=source_summaries[index],
            player_ids=player_ids,
            canonical_labels=canonical_labels,
        )
        for index, comparison in enumerate(aggregations[1:], start=1)
    )
    result = FixedThreePlayerHistoricalListComparisonResult(
        comparison_version=FIXED_THREE_PLAYER_HISTORICAL_LIST_COMPARISON_VERSION,
        basis=FIXED_THREE_PLAYER_HISTORICAL_LIST_COMPARISON_BASIS,
        reference_list_id=reference.list_id,
        list_count=len(aggregations),
        player_ids=player_ids,
        source_lists=source_summaries,
        comparisons=comparisons,
    )
    _validate_comparison_result(result, aggregations, canonical_labels)
    return result
