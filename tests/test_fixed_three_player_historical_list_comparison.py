from dataclasses import FrozenInstanceError, fields, replace

import pytest
from test_fixed_three_player_historical_list import (
    build_list_input,
    replace_player_ids,
)
from test_historical_game import build_historical_input

from skatmind.fixed_three_player_historical_list import (
    build_fixed_three_player_historical_list,
)
from skatmind.fixed_three_player_historical_list_aggregation import (
    FIXED_THREE_PLAYER_HISTORICAL_LIST_AGGREGATION_VERSION,
    FIXED_THREE_PLAYER_HISTORICAL_LIST_STANDINGS_BASIS,
    build_fixed_three_player_historical_list_aggregation,
    validate_fixed_three_player_historical_list_aggregation,
)
from skatmind.fixed_three_player_historical_list_comparison import (
    FIXED_THREE_PLAYER_HISTORICAL_LIST_COMPARISON_BASIS,
    FIXED_THREE_PLAYER_HISTORICAL_LIST_COMPARISON_VERSION,
    FIXED_THREE_PLAYER_HISTORICAL_LIST_RANK_COMPARISON_STATUSES,
    MIN_FIXED_THREE_PLAYER_HISTORICAL_LIST_COMPARISON_COUNT,
    build_fixed_three_player_historical_list_comparison,
)
from skatmind.fixed_three_player_historical_list_comparison_summary import (
    FixedThreePlayerHistoricalListComparisonCompactStanding,
    FixedThreePlayerHistoricalListComparisonResult,
    FixedThreePlayerHistoricalListComparisonSourceSummary,
    FixedThreePlayerHistoricalListPairwiseComparison,
    FixedThreePlayerHistoricalListPlayerComparison,
    FixedThreePlayerHistoricalListPlayerTotalsDelta,
    build_serializable_fixed_three_player_historical_list_comparison,
    build_serializable_fixed_three_player_historical_list_comparison_source_summary,
    build_serializable_fixed_three_player_historical_list_pairwise_comparison,
    build_serializable_fixed_three_player_historical_list_player_comparison,
    build_serializable_fixed_three_player_historical_list_player_totals_delta,
)
from skatmind.fixed_three_player_historical_list_totals import (
    FixedThreePlayerHistoricalListPlayerTotals,
)

NUMERIC_FIELDS = tuple(
    field.name
    for field in fields(FixedThreePlayerHistoricalListPlayerTotals)
    if field.name not in {"player_id", "player_label", "table_place"}
)


def build_source_aggregation(
    played_declarers: dict[int, str],
    *,
    list_id: str,
    game_id_prefix: str,
    player_id_replacements: dict[str, str] | None = None,
    labels: dict[str, str | None] | None = None,
    lot_order: list[str] | None = None,
):
    data = build_list_input(
        played_games={
            entry_number: build_historical_input(
                game_type="null",
                declarer_player_id=declarer_player_id,
            )
            for entry_number, declarer_player_id in played_declarers.items()
        }
    )
    if player_id_replacements is not None:
        data = replace_player_ids(data, player_id_replacements)
    data["list_id"] = list_id
    for entry in data["entries"]:
        if entry["entry_kind"] == "played_game":
            entry["historical_game"]["game_id"] = f"{game_id_prefix}-{entry['entry_id']}"
    for player in data["players"]:
        label = (labels or {}).get(player["player_id"])
        if label is None:
            player.pop("player_label", None)
        else:
            player["player_label"] = label
    historical_list = build_fixed_three_player_historical_list(data)
    return build_fixed_three_player_historical_list_aggregation(
        historical_list,
        lot_order=lot_order,
    )


@pytest.fixture(scope="module")
def reference_final():
    return build_source_aggregation(
        {2: "player-b", 3: "player-b", 5: "player-b"},
        list_id="reference-final",
        game_id_prefix="reference",
        labels={"player-a": "Alice"},
    )


@pytest.fixture(scope="module")
def comparison_final():
    return build_source_aggregation(
        {1: "player-b", 3: "player-b", 4: "player-b"},
        list_id="comparison-final",
        game_id_prefix="comparison",
        labels={"player-a": "Alice", "player-b": "Bob"},
    )


@pytest.fixture(scope="module")
def unresolved():
    return build_source_aggregation(
        {2: "player-b"},
        list_id="unresolved",
        game_id_prefix="unresolved",
    )


def independent_comparison_oracle(reference, comparison) -> dict:
    reference_totals = {total.player_id: total for total in reference.player_totals}
    comparison_totals = {total.player_id: total for total in comparison.player_totals}
    player_ids = tuple(total.player_id for total in reference.player_totals)
    labels = {}
    for player_id in player_ids:
        source_labels = [
            totals[player_id].player_label
            for totals in (reference_totals, comparison_totals)
            if totals[player_id].player_label is not None
        ]
        labels[player_id] = source_labels[0] if source_labels else None

    if reference.ranking_status == "final" and comparison.ranking_status == "final":
        status = "available"
    elif reference.ranking_status == "lot_required" and comparison.ranking_status == "lot_required":
        status = "both_lot_required"
    elif reference.ranking_status == "lot_required":
        status = "reference_lot_required"
    else:
        status = "comparison_lot_required"
    reference_ranks = {row.player_totals.player_id: row.rank for row in reference.final_standings}
    comparison_ranks = {row.player_totals.player_id: row.rank for row in comparison.final_standings}
    players = []
    for player_id in player_ids:
        reference_total = reference_totals[player_id]
        comparison_total = comparison_totals[player_id]
        reference_rank = reference_ranks[player_id] if status == "available" else None
        comparison_rank = comparison_ranks[player_id] if status == "available" else None
        players.append(
            {
                "player_id": player_id,
                "player_label": labels[player_id],
                "deltas": {
                    field_name: getattr(comparison_total, field_name)
                    - getattr(reference_total, field_name)
                    for field_name in NUMERIC_FIELDS
                },
                "rank_comparison_status": status,
                "reference_rank": reference_rank,
                "comparison_rank": comparison_rank,
                "rank_position_change": (
                    None if status != "available" else reference_rank - comparison_rank
                ),
            }
        )
    return {
        "list_deltas": {
            field_name: getattr(comparison, field_name) - getattr(reference, field_name)
            for field_name in (
                "played_game_count",
                "passed_deal_count",
                "declarer_win_count",
                "declarer_loss_count",
            )
        },
        "players": tuple(players),
    }


def collect_keys(value) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {
            nested_key
            for nested_value in value.values()
            for nested_key in collect_keys(nested_value)
        }
    if isinstance(value, list):
        return {nested_key for nested_value in value for nested_key in collect_keys(nested_value)}
    return set()


def test_version_one_constants_and_immutable_contracts_are_stable(
    reference_final,
    comparison_final,
) -> None:
    assert FIXED_THREE_PLAYER_HISTORICAL_LIST_COMPARISON_VERSION == 1
    assert FIXED_THREE_PLAYER_HISTORICAL_LIST_COMPARISON_BASIS == (
        "independent_completed_fixed_three_player_historical_lists"
    )
    assert MIN_FIXED_THREE_PLAYER_HISTORICAL_LIST_COMPARISON_COUNT == 2
    assert FIXED_THREE_PLAYER_HISTORICAL_LIST_RANK_COMPARISON_STATUSES == (
        "available",
        "reference_lot_required",
        "comparison_lot_required",
        "both_lot_required",
    )

    result = build_fixed_three_player_historical_list_comparison(
        (reference_final, comparison_final)
    )
    values = (
        result,
        result.source_lists[0],
        result.source_lists[0].final_standings[0],
        result.comparisons[0],
        result.comparisons[0].player_comparisons[0],
        result.comparisons[0].player_comparisons[0].deltas,
    )
    expected_types = (
        FixedThreePlayerHistoricalListComparisonResult,
        FixedThreePlayerHistoricalListComparisonSourceSummary,
        FixedThreePlayerHistoricalListComparisonCompactStanding,
        FixedThreePlayerHistoricalListPairwiseComparison,
        FixedThreePlayerHistoricalListPlayerComparison,
        FixedThreePlayerHistoricalListPlayerTotalsDelta,
    )
    for value, expected_type in zip(values, expected_types, strict=True):
        assert expected_type.__dataclass_params__.frozen is True
        assert isinstance(value, expected_type)
        assert isinstance(hash(value), int)
        with pytest.raises(FrozenInstanceError):
            value.comparison_version = 2

    assert (
        tuple(field.name for field in fields(FixedThreePlayerHistoricalListPlayerTotalsDelta))
        == NUMERIC_FIELDS
    )


def test_input_requires_an_immutable_tuple_with_at_least_two_lists(
    reference_final,
) -> None:
    with pytest.raises(ValueError, match="immutable tuple"):
        build_fixed_three_player_historical_list_comparison([reference_final, reference_final])
    with pytest.raises(ValueError, match="at least two"):
        build_fixed_three_player_historical_list_comparison((reference_final,))


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: replace(value, aggregation_version=2),
        lambda value: replace(value, basis="forged"),
        lambda value: replace(value, source_list_schema_version=2),
        lambda value: replace(value, entry_count=35),
        lambda value: replace(value, round_count=11),
        lambda value: replace(value, played_game_count=value.played_game_count + 1),
        lambda value: replace(value, player_totals=value.player_totals[:2]),
        lambda value: replace(value, progression=value.progression[:35]),
        lambda value: replace(value, final_standings=value.final_standings[:2]),
        lambda value: replace(
            value,
            progression=(
                replace(
                    value.progression[0],
                    cumulative_player_totals=value.progression[1].cumulative_player_totals,
                ),
                *value.progression[1:],
            ),
        ),
        lambda value: replace(
            value,
            final_standings=(
                replace(value.final_standings[0], rank=True),
                *value.final_standings[1:],
            ),
        ),
    ],
)
def test_forged_frozen_source_aggregations_are_rejected(
    reference_final,
    comparison_final,
    mutation,
) -> None:
    forged = mutation(reference_final)
    with pytest.raises(ValueError):
        validate_fixed_three_player_historical_list_aggregation(forged)
    with pytest.raises(ValueError):
        build_fixed_three_player_historical_list_comparison((forged, comparison_final))


def test_source_list_ids_must_be_unique(reference_final) -> None:
    duplicate_list_id = build_source_aggregation(
        {1: "player-b"},
        list_id=reference_final.list_id,
        game_id_prefix="duplicate-list-id",
        labels={"player-a": "Alice"},
    )
    with pytest.raises(ValueError, match="unique list_id"):
        build_fixed_three_player_historical_list_comparison((reference_final, duplicate_list_id))


def test_played_game_ids_must_be_disjoint_across_lists(reference_final) -> None:
    comparison = build_source_aggregation(
        {2: "player-b"},
        list_id="reused-game-list",
        game_id_prefix="reference",
    )
    with pytest.raises(ValueError, match="reused across source lists"):
        build_fixed_three_player_historical_list_comparison((reference_final, comparison))


def test_entry_ids_remain_list_scoped_and_may_repeat(
    reference_final,
    comparison_final,
) -> None:
    result = build_fixed_three_player_historical_list_comparison(
        (reference_final, comparison_final)
    )
    assert result.list_count == 2


def test_sources_require_the_same_stable_player_set(reference_final) -> None:
    replacement = build_source_aggregation(
        {1: "player-b"},
        list_id="replacement-list",
        game_id_prefix="replacement",
        player_id_replacements={"player-c": "player-d"},
    )
    with pytest.raises(ValueError, match="same stable players"):
        build_fixed_three_player_historical_list_comparison((reference_final, replacement))


def test_players_align_by_id_when_table_places_change(reference_final) -> None:
    changed_places = build_source_aggregation(
        {1: "player-b", 3: "player-b", 4: "player-b"},
        list_id="changed-places",
        game_id_prefix="changed-places",
        player_id_replacements={"player-a": "player-b", "player-b": "player-a"},
        labels={"player-a": "Alice"},
    )
    result = build_fixed_three_player_historical_list_comparison((reference_final, changed_places))
    rows = {row.player_id: row for row in result.comparisons[0].player_comparisons}

    assert result.player_ids == ("player-a", "player-b", "player-c")
    assert rows["player-a"].reference_table_place == "place_1"
    assert rows["player-a"].comparison_table_place == "place_2"
    assert rows["player-b"].reference_table_place == "place_2"
    assert rows["player-b"].comparison_table_place == "place_1"


def test_labels_use_reference_then_first_non_null_source_order(reference_final) -> None:
    second = build_source_aggregation(
        {},
        list_id="label-second",
        game_id_prefix="label-second",
        labels={"player-c": "Carol"},
    )
    third = build_source_aggregation(
        {},
        list_id="label-third",
        game_id_prefix="label-third",
        labels={"player-b": "Bob", "player-c": "Carol"},
    )
    result = build_fixed_three_player_historical_list_comparison((reference_final, second, third))
    labels = {row.player_id: row.player_label for row in result.comparisons[1].player_comparisons}
    assert labels == {
        "player-a": "Alice",
        "player-b": "Bob",
        "player-c": "Carol",
    }


def test_conflicting_non_null_labels_are_rejected(reference_final) -> None:
    conflicting = build_source_aggregation(
        {},
        list_id="conflicting-label",
        game_id_prefix="conflicting-label",
        labels={"player-a": "Alicia"},
    )
    with pytest.raises(ValueError, match="conflicting non-null labels"):
        build_fixed_three_player_historical_list_comparison((reference_final, conflicting))


def test_two_and_three_sources_preserve_reference_and_source_order(
    reference_final,
    comparison_final,
) -> None:
    third = build_source_aggregation(
        {},
        list_id="third-list",
        game_id_prefix="third",
        labels={"player-a": "Alice", "player-b": "Bob"},
    )
    result = build_fixed_three_player_historical_list_comparison(
        (reference_final, comparison_final, third)
    )

    assert result.reference_list_id == "reference-final"
    assert [summary.list_id for summary in result.source_lists] == [
        "reference-final",
        "comparison-final",
        "third-list",
    ]
    assert [comparison.comparison_list_id for comparison in result.comparisons] == [
        "comparison-final",
        "third-list",
    ]
    assert all(
        comparison.reference_list_id == "reference-final" for comparison in result.comparisons
    )


def test_mixed_passed_deals_produce_all_comparison_minus_reference_list_deltas() -> None:
    reference = build_source_aggregation(
        {},
        list_id="all-passed-reference",
        game_id_prefix="all-passed-reference",
    )
    comparison = build_source_aggregation(
        {1: "player-a", 2: "player-b"},
        list_id="mixed-comparison",
        game_id_prefix="mixed-comparison",
    )
    pairwise = build_fixed_three_player_historical_list_comparison(
        (reference, comparison)
    ).comparisons[0]

    assert pairwise.played_game_count_delta == 2
    assert pairwise.passed_deal_count_delta == -2
    assert pairwise.declarer_win_count_delta == 1
    assert pairwise.declarer_loss_count_delta == 1


def test_every_player_numeric_delta_matches_the_independent_oracle(
    reference_final,
    comparison_final,
) -> None:
    pairwise = build_fixed_three_player_historical_list_comparison(
        (reference_final, comparison_final)
    ).comparisons[0]
    oracle = independent_comparison_oracle(reference_final, comparison_final)

    assert {
        "played_game_count": pairwise.played_game_count_delta,
        "passed_deal_count": pairwise.passed_deal_count_delta,
        "declarer_win_count": pairwise.declarer_win_count_delta,
        "declarer_loss_count": pairwise.declarer_loss_count_delta,
    } == oracle["list_deltas"]
    for actual, expected in zip(
        pairwise.player_comparisons,
        oracle["players"],
        strict=True,
    ):
        assert actual.player_id == expected["player_id"]
        assert {
            field_name: getattr(actual.deltas, field_name) for field_name in NUMERIC_FIELDS
        } == expected["deltas"]


def test_final_rank_changes_use_reference_minus_comparison(
    reference_final,
    comparison_final,
) -> None:
    rows = {
        row.player_id: row
        for row in build_fixed_three_player_historical_list_comparison(
            (reference_final, comparison_final)
        )
        .comparisons[0]
        .player_comparisons
    }

    assert rows["player-a"].rank_position_change == -2
    assert rows["player-b"].rank_position_change == 0
    assert rows["player-c"].rank_position_change == 2
    assert all(row.rank_comparison_status == "available" for row in rows.values())


@pytest.mark.parametrize(
    ("reference_kind", "comparison_kind", "expected_status"),
    [
        ("unresolved", "final", "reference_lot_required"),
        ("final", "unresolved", "comparison_lot_required"),
        ("unresolved", "unresolved", "both_lot_required"),
    ],
)
def test_unresolved_rank_statuses_null_every_rank_field(
    reference_final,
    comparison_final,
    unresolved,
    reference_kind: str,
    comparison_kind: str,
    expected_status: str,
) -> None:
    sources = {
        "final": reference_final,
        "unresolved": unresolved,
    }
    reference = sources[reference_kind]
    comparison = sources[comparison_kind]
    if reference.list_id == comparison.list_id:
        comparison = build_source_aggregation(
            {2: "player-b"},
            list_id="second-unresolved",
            game_id_prefix="second-unresolved",
        )
    pairwise = build_fixed_three_player_historical_list_comparison(
        (reference, comparison)
    ).comparisons[0]

    assert pairwise.final_rank_comparison_available is False
    assert all(
        row.rank_comparison_status == expected_status
        and row.reference_rank is None
        and row.comparison_rank is None
        and row.rank_position_change is None
        for row in pairwise.player_comparisons
    )


def test_applied_external_lots_count_as_resolved_final_rankings() -> None:
    reference = build_source_aggregation(
        {2: "player-b"},
        list_id="lot-reference",
        game_id_prefix="lot-reference",
        lot_order=["player-c", "player-b"],
    )
    comparison = build_source_aggregation(
        {2: "player-b"},
        list_id="lot-comparison",
        game_id_prefix="lot-comparison",
        lot_order=["player-b", "player-c"],
    )
    pairwise = build_fixed_three_player_historical_list_comparison(
        (reference, comparison)
    ).comparisons[0]

    assert pairwise.final_rank_comparison_available is True
    assert all(
        row.rank_comparison_status == "available"
        and row.reference_rank is not None
        and row.comparison_rank is not None
        for row in pairwise.player_comparisons
    )


def test_pairwise_and_overall_results_reconcile_without_series_output(
    reference_final,
    comparison_final,
) -> None:
    result = build_fixed_three_player_historical_list_comparison(
        (reference_final, comparison_final)
    )
    pairwise = result.comparisons[0]

    assert result.list_count == 2
    assert len(result.source_lists) == 2
    assert len(result.comparisons) == 1
    assert pairwise.reference_summary == result.source_lists[0]
    assert pairwise.comparison_summary == result.source_lists[1]
    assert tuple(row.player_id for row in pairwise.player_comparisons) == result.player_ids
    assert not hasattr(result, "series_totals")
    assert not hasattr(result, "combined_standings")
    assert not hasattr(result, "series_winner")
    assert not hasattr(result, "recommendation")


@pytest.mark.parametrize(
    "source_pair",
    [
        ("final", "final"),
        ("unresolved", "final"),
        ("final", "unresolved"),
        ("unresolved", "unresolved"),
    ],
)
def test_independent_oracle_agrees_across_rank_availability_cases(
    reference_final,
    comparison_final,
    unresolved,
    source_pair: tuple[str, str],
) -> None:
    sources = {
        "final": reference_final,
        "unresolved": unresolved,
    }
    reference = sources[source_pair[0]]
    comparison = sources[source_pair[1]]
    if reference is comparison:
        if source_pair[0] == "final":
            comparison = comparison_final
        else:
            comparison = build_source_aggregation(
                {2: "player-b"},
                list_id="oracle-second-unresolved",
                game_id_prefix="oracle-second-unresolved",
            )
    pairwise = build_fixed_three_player_historical_list_comparison(
        (reference, comparison)
    ).comparisons[0]
    oracle = independent_comparison_oracle(reference, comparison)

    for actual, expected in zip(
        pairwise.player_comparisons,
        oracle["players"],
        strict=True,
    ):
        assert actual.rank_comparison_status == expected["rank_comparison_status"]
        assert actual.reference_rank == expected["reference_rank"]
        assert actual.comparison_rank == expected["comparison_rank"]
        assert actual.rank_position_change == expected["rank_position_change"]
        assert {
            field_name: getattr(actual.deltas, field_name) for field_name in NUMERIC_FIELDS
        } == expected["deltas"]


def test_source_summaries_are_compact_and_reconcile_final_standings(
    reference_final,
    comparison_final,
) -> None:
    summaries = build_fixed_three_player_historical_list_comparison(
        (reference_final, comparison_final)
    ).source_lists
    for summary, source in zip(
        summaries,
        (reference_final, comparison_final),
        strict=True,
    ):
        assert summary.entry_count == 36
        assert summary.round_count == 12
        assert summary.played_game_count + summary.passed_deal_count == 36
        assert summary.declarer_win_count + summary.declarer_loss_count == (
            summary.played_game_count
        )
        assert [row.player_id for row in summary.final_standings] == [
            row.player_totals.player_id for row in source.final_standings
        ]


def test_serialization_is_deterministic_ordered_and_privacy_safe(
    reference_final,
    comparison_final,
) -> None:
    result = build_fixed_three_player_historical_list_comparison(
        (reference_final, comparison_final)
    )
    first = build_serializable_fixed_three_player_historical_list_comparison(result)
    second = build_serializable_fixed_three_player_historical_list_comparison(result)

    assert first == second
    assert [source["list_id"] for source in first["source_lists"]] == [
        "reference-final",
        "comparison-final",
    ]
    assert [row["player_id"] for row in first["comparisons"][0]["player_comparisons"]] == [
        "player-a",
        "player-b",
        "player-c",
    ]
    assert (
        build_serializable_fixed_three_player_historical_list_comparison_source_summary(
            result.source_lists[0]
        )
        == first["source_lists"][0]
    )
    assert (
        build_serializable_fixed_three_player_historical_list_pairwise_comparison(
            result.comparisons[0]
        )
        == first["comparisons"][0]
    )
    assert (
        build_serializable_fixed_three_player_historical_list_player_comparison(
            result.comparisons[0].player_comparisons[0]
        )
        == first["comparisons"][0]["player_comparisons"][0]
    )
    assert (
        build_serializable_fixed_three_player_historical_list_player_totals_delta(
            result.comparisons[0].player_comparisons[0].deltas
        )
        == first["comparisons"][0]["player_comparisons"][0]["deltas"]
    )
    assert collect_keys(first).isdisjoint(
        {
            "progression",
            "entry_fact",
            "historical_game",
            "initial_hand",
            "hand",
            "skat",
            "discarded_cards",
            "tricks",
            "ownership",
            "private_ownership",
            "search_state",
            "series_totals",
            "combined_standings",
            "series_winner",
        }
    )


def test_issue_127_and_128_constants_and_builders_remain_unchanged(
    reference_final,
) -> None:
    assert FIXED_THREE_PLAYER_HISTORICAL_LIST_AGGREGATION_VERSION == 1
    assert FIXED_THREE_PLAYER_HISTORICAL_LIST_STANDINGS_BASIS == (
        "fixed_three_player_historical_36_position_list"
    )
    validate_fixed_three_player_historical_list_aggregation(reference_final)
