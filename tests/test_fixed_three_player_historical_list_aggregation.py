import inspect
from dataclasses import FrozenInstanceError, fields, replace
from typing import get_type_hints

import pytest
from test_fixed_three_player_historical_list import build_list_input
from test_historical_game import build_historical_input

from skat_ai.fixed_three_player_historical_list import (
    FIXED_THREE_PLAYER_HISTORICAL_LIST_SCHEMA_VERSION,
    FIXED_THREE_PLAYER_LIST_ENTRY_COUNT,
    build_fixed_three_player_historical_list,
    build_fixed_three_player_historical_list_entry_facts,
)
from skat_ai.fixed_three_player_historical_list_aggregation import (
    FIXED_THREE_PLAYER_HISTORICAL_LIST_AGGREGATION_VERSION,
    FIXED_THREE_PLAYER_HISTORICAL_LIST_RANKING_STATUSES,
    FIXED_THREE_PLAYER_HISTORICAL_LIST_STANDINGS_BASIS,
    FixedThreePlayerHistoricalListAggregation,
    FixedThreePlayerHistoricalListPlayerTotals,
    add_fixed_three_player_historical_list_contribution,
    build_fixed_three_player_historical_list_aggregation,
    build_fixed_three_player_historical_list_zero_player_totals,
    build_serializable_fixed_three_player_historical_list_aggregation,
    build_serializable_fixed_three_player_historical_list_player_totals,
    validate_fixed_three_player_historical_list_player_totals,
)
from skat_ai.fixed_three_player_historical_list_progression import (
    FixedThreePlayerHistoricalListProgressionSnapshot,
    build_serializable_fixed_three_player_historical_list_progression_snapshot,
)
from skat_ai.fixed_three_player_historical_list_standings import (
    FixedThreePlayerHistoricalListStanding,
    FixedThreePlayerHistoricalListStandingsResult,
    build_fixed_three_player_historical_list_standings,
    build_serializable_fixed_three_player_historical_list_standing,
)
from skat_ai.performance_rating import (
    build_list_performance_summary,
    build_list_performance_summary_from_game_contributions,
    build_list_standings_summary,
    get_list_standings_ranking_key,
)

NUMERIC_FIELDS = (
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
    "player_game_points",
    "own_game_bonus_points",
    "opponent_loss_bonus_points",
    "total_performance_points",
)


def build_game(*, declarer_player_id: str) -> dict:
    return build_historical_input(
        game_type="null",
        declarer_player_id=declarer_player_id,
    )


def build_validated_list(played_declarers: dict[int, str]):
    return build_fixed_three_player_historical_list(
        build_list_input(
            played_games={
                entry_number: build_game(declarer_player_id=declarer_player_id)
                for entry_number, declarer_player_id in played_declarers.items()
            }
        )
    )


@pytest.fixture(scope="module")
def all_passed_list():
    return build_validated_list({})


@pytest.fixture(scope="module")
def two_way_tie_list():
    return build_validated_list({2: "player-b"})


@pytest.fixture(scope="module")
def three_way_tie_list():
    return build_validated_list(
        {
            1: "player-b",
            2: "player-b",
            3: "player-b",
        }
    )


@pytest.fixture(scope="module")
def unique_list():
    return build_validated_list(
        {
            2: "player-b",
            3: "player-b",
            5: "player-b",
        }
    )


@pytest.fixture(scope="module")
def mixed_list():
    return build_validated_list(
        {
            1: "player-a",
            2: "player-b",
        }
    )


@pytest.fixture(scope="module")
def all_played_list():
    return build_validated_list({entry_number: "player-b" for entry_number in range(1, 37)})


def build_independent_oracle(historical_list, *, lot_order=None) -> dict:
    facts = build_fixed_three_player_historical_list_entry_facts(historical_list)
    totals = {
        player.player_id: {
            "player_id": player.player_id,
            "player_label": player.player_label,
            "table_place": player.table_place,
            **{field_name: 0 for field_name in NUMERIC_FIELDS},
        }
        for player in historical_list.players
    }
    progression = []
    for fact in facts:
        for contribution in fact.player_contributions:
            row = totals[contribution.player_id]
            row["list_entry_count"] += contribution.list_entry_count
            row["played_game_count"] += contribution.played_game_count
            row["passed_deal_count"] += contribution.passed_deal_count
            row["declarer_game_count"] += contribution.declarer_game_count
            row["defender_game_count"] += contribution.defender_game_count
            row["own_games_won"] += contribution.own_games_won
            row["own_games_lost"] += contribution.own_games_lost
            row["defender_games_won"] += contribution.defender_games_won
            row["defender_games_lost"] += contribution.defender_games_lost
            row["other_players_lost_games"] += (
                contribution.other_players_lost_games
            )
            row["player_game_points"] += contribution.player_game_points
            row["own_game_bonus_points"] = (
                row["own_games_won"] * 50 - row["own_games_lost"] * 50
            )
            row["opponent_loss_bonus_points"] = (
                row["other_players_lost_games"] * 40
            )
            row["total_performance_points"] = (
                row["player_game_points"]
                + row["own_game_bonus_points"]
                + row["opponent_loss_bonus_points"]
            )
        progression.append(
            tuple(
                {field_name: row[field_name] for field_name in row}
                for row in totals.values()
            )
        )

    table_order = {
        player.player_id: index
        for index, player in enumerate(historical_list.players)
    }
    standings = sorted(
        (dict(row) for row in totals.values()),
        key=lambda row: (
            -row["total_performance_points"],
            -row["own_games_won"],
            row["own_games_lost"],
            table_order[row["player_id"]],
        ),
    )
    previous_key = None
    for index, row in enumerate(standings):
        key = (
            -row["total_performance_points"],
            -row["own_games_won"],
            row["own_games_lost"],
        )
        row["rank"] = standings[index - 1]["rank"] if key == previous_key else index + 1
        previous_key = key

    tied_rows = []
    for row in standings:
        key = (
            row["total_performance_points"],
            row["own_games_won"],
            row["own_games_lost"],
        )
        group = [
            candidate
            for candidate in standings
            if (
                candidate["total_performance_points"],
                candidate["own_games_won"],
                candidate["own_games_lost"],
            )
            == key
        ]
        if len(group) > 1:
            tied_rows = group
            break
    tied_player_ids = tuple(row["player_id"] for row in tied_rows)

    if lot_order is not None:
        if (
            not isinstance(lot_order, list)
            or len(lot_order) not in {2, 3}
            or len(set(lot_order)) != len(lot_order)
            or set(lot_order) != set(tied_player_ids)
        ):
            raise ValueError("Invalid independent-oracle lot order.")
        tie_start = standings.index(tied_rows[0])
        tied_by_id = {row["player_id"]: row for row in tied_rows}
        standings[tie_start : tie_start + len(tied_rows)] = [
            tied_by_id[player_id] for player_id in lot_order
        ]
        for index in range(tie_start, tie_start + len(tied_rows)):
            standings[index]["rank"] = index + 1

    return {
        "facts": facts,
        "totals": tuple(totals.values()),
        "progression": tuple(progression),
        "standings": tuple(standings),
        "tied_player_ids": tied_player_ids,
    }


def totals_by_player(aggregation) -> dict:
    return {total.player_id: total for total in aggregation.player_totals}


def simplified_standings_input(historical_list, *, lot_order=None) -> dict:
    facts = build_fixed_three_player_historical_list_entry_facts(historical_list)
    result = {
        "players": [
            {
                "player_id": player.player_id,
                **(
                    {}
                    if player.player_label is None
                    else {"player_label": player.player_label}
                ),
            }
            for player in historical_list.players
        ],
        "games": [
            {
                "game_id": fact.game_id,
                "declarer_player_id": fact.declarer_player_id,
                "game_outcome": fact.entry_outcome,
                "settlement_score": fact.settlement_score,
            }
            for fact in facts
            if fact.entry_kind == "played_game"
        ],
    }
    if lot_order is not None:
        result["lot_order"] = lot_order
    return result


def assert_simplified_equivalence(historical_list, *, lot_order=None) -> None:
    aggregation = build_fixed_three_player_historical_list_aggregation(
        historical_list,
        lot_order=lot_order,
    )
    old = build_list_standings_summary(
        simplified_standings_input(historical_list, lot_order=lot_order),
        "isko_list",
    )
    new_by_id = totals_by_player(aggregation)
    comparable_fields = {
        "declarer_games": "declarer_game_count",
        "defender_games": "defender_game_count",
        "own_games_won": "own_games_won",
        "own_games_lost": "own_games_lost",
        "defender_games_won": "defender_games_won",
        "defender_games_lost": "defender_games_lost",
        "other_players_lost_games": "other_players_lost_games",
        "player_game_points": "player_game_points",
        "own_game_bonus_points": "own_game_bonus_points",
        "opponent_loss_bonus_points": "opponent_loss_bonus_points",
        "total_performance_points": "total_performance_points",
    }
    for old_row in old["standings"]:
        new = new_by_id[old_row["player_id"]]
        assert old_row["games_played"] == new.played_game_count
        for old_field, new_field in comparable_fields.items():
            assert old_row[old_field] == getattr(new, new_field)
        assert get_list_standings_ranking_key(old_row) == (
            -new.total_performance_points,
            -new.own_games_won,
            new.own_games_lost,
        )
    assert [row["player_id"] for row in old["standings"]] == [
        row.player_totals.player_id for row in aggregation.final_standings
    ]
    assert [row["rank"] for row in old["standings"]] == [
        row.rank for row in aggregation.final_standings
    ]
    assert old["ranking_status"] == aggregation.ranking_status
    assert tuple(old["lot_required_player_ids"]) == (
        aggregation.lot_required_player_ids
    )
    assert (
        None if old["applied_lot_order"] is None else tuple(old["applied_lot_order"])
    ) == aggregation.applied_lot_order


def make_totals(
    player_id: str,
    table_place: str,
    *,
    own_games_won: int = 0,
    own_games_lost: int = 0,
    player_game_points: int = 0,
) -> FixedThreePlayerHistoricalListPlayerTotals:
    declarer_games = own_games_won + own_games_lost
    own_bonus = own_games_won * 50 - own_games_lost * 50
    return FixedThreePlayerHistoricalListPlayerTotals(
        player_id=player_id,
        player_label=None,
        table_place=table_place,
        list_entry_count=declarer_games,
        played_game_count=declarer_games,
        passed_deal_count=0,
        declarer_game_count=declarer_games,
        defender_game_count=0,
        own_games_won=own_games_won,
        own_games_lost=own_games_lost,
        defender_games_won=0,
        defender_games_lost=0,
        other_players_lost_games=0,
        player_game_points=player_game_points,
        own_game_bonus_points=own_bonus,
        opponent_loss_bonus_points=0,
        total_performance_points=player_game_points + own_bonus,
    )


def test_aggregation_constants_and_source_contract_are_unchanged() -> None:
    assert FIXED_THREE_PLAYER_HISTORICAL_LIST_AGGREGATION_VERSION == 1
    assert FIXED_THREE_PLAYER_HISTORICAL_LIST_STANDINGS_BASIS == (
        "fixed_three_player_historical_36_position_list"
    )
    assert FIXED_THREE_PLAYER_HISTORICAL_LIST_RANKING_STATUSES == (
        "final",
        "lot_required",
    )
    assert FIXED_THREE_PLAYER_HISTORICAL_LIST_SCHEMA_VERSION == 1
    assert FIXED_THREE_PLAYER_LIST_ENTRY_COUNT == 36
    assert tuple(
        field.name for field in fields(FixedThreePlayerHistoricalListPlayerTotals)
    ) == (
        "player_id",
        "player_label",
        "table_place",
        *NUMERIC_FIELDS,
    )
    assert tuple(
        inspect.signature(
            build_fixed_three_player_historical_list_aggregation
        ).parameters
    ) == ("historical_list", "lot_order")


def test_all_aggregation_contracts_are_frozen_and_hashable(all_passed_list) -> None:
    aggregation = build_fixed_three_player_historical_list_aggregation(all_passed_list)
    values = (
        aggregation,
        aggregation.player_totals[0],
        aggregation.progression[0],
        aggregation.final_standings[0],
        build_fixed_three_player_historical_list_standings(
            aggregation.player_totals
        ),
    )
    expected_types = (
        FixedThreePlayerHistoricalListAggregation,
        FixedThreePlayerHistoricalListPlayerTotals,
        FixedThreePlayerHistoricalListProgressionSnapshot,
        FixedThreePlayerHistoricalListStanding,
        FixedThreePlayerHistoricalListStandingsResult,
    )
    for value, expected_type in zip(values, expected_types, strict=True):
        assert isinstance(value, expected_type)
        assert expected_type.__dataclass_params__.frozen is True
        assert isinstance(hash(value), int)
        with pytest.raises(FrozenInstanceError):
            value.rank = 99
    assert get_type_hints(FixedThreePlayerHistoricalListProgressionSnapshot)
    assert get_type_hints(FixedThreePlayerHistoricalListStanding)


def test_zero_totals_and_addition_are_immutable(mixed_list) -> None:
    player = mixed_list.players[0]
    zero = build_fixed_three_player_historical_list_zero_player_totals(player)
    fact = build_fixed_three_player_historical_list_entry_facts(mixed_list)[0]
    contribution = fact.player_contributions[0]

    result = add_fixed_three_player_historical_list_contribution(zero, contribution)

    assert all(getattr(zero, field_name) == 0 for field_name in NUMERIC_FIELDS)
    assert result is not zero
    assert result.list_entry_count == 1
    for field_name in NUMERIC_FIELDS:
        assert getattr(result, field_name) == getattr(contribution, field_name)


def test_addition_rejects_mismatched_contribution_identity(mixed_list) -> None:
    zero = build_fixed_three_player_historical_list_zero_player_totals(
        mixed_list.players[0]
    )
    contribution = build_fixed_three_player_historical_list_entry_facts(mixed_list)[
        0
    ].player_contributions[0]

    with pytest.raises(ValueError, match="player ID must match"):
        add_fixed_three_player_historical_list_contribution(
            zero,
            replace(contribution, player_id="player-b"),
        )


def test_aggregation_rejects_noncanonical_contribution_order(
    all_passed_list,
    monkeypatch,
) -> None:
    from skat_ai import fixed_three_player_historical_list_aggregation as module

    facts = build_fixed_three_player_historical_list_entry_facts(all_passed_list)
    first = facts[0]
    invalid_facts = (
        replace(
            first,
            player_contributions=(
                first.player_contributions[1],
                first.player_contributions[0],
                first.player_contributions[2],
            ),
        ),
        *facts[1:],
    )
    monkeypatch.setattr(
        module,
        "build_fixed_three_player_historical_list_entry_facts",
        lambda historical_list: invalid_facts,
    )

    with pytest.raises(ValueError, match="order must match"):
        build_fixed_three_player_historical_list_aggregation(all_passed_list)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"list_entry_count": 1}, "Played and passed"),
        ({"played_game_count": 1, "list_entry_count": 1}, "Declarer and defender"),
        (
            {
                "played_game_count": 1,
                "list_entry_count": 1,
                "declarer_game_count": 1,
            },
            "Own wins and losses",
        ),
        (
            {
                "played_game_count": 1,
                "list_entry_count": 1,
                "defender_game_count": 1,
            },
            "Defender wins and losses",
        ),
        ({"other_players_lost_games": 1}, "Other-player losses"),
        ({"own_game_bonus_points": 1}, "Own-game bonus"),
        ({"opponent_loss_bonus_points": 1}, "Opponent-loss bonus"),
        ({"total_performance_points": 1}, "Total performance"),
        ({"passed_deal_count": -1}, "non-negative"),
        ({"list_entry_count": True}, "integer"),
    ],
)
def test_every_player_total_invariant_is_validated(
    all_passed_list,
    changes: dict,
    message: str,
) -> None:
    zero = build_fixed_three_player_historical_list_zero_player_totals(
        all_passed_list.players[0]
    )
    invalid = replace(zero, **changes)

    with pytest.raises(ValueError, match=message):
        validate_fixed_three_player_historical_list_player_totals(invalid)


def test_entry_facts_are_derived_exactly_once(all_passed_list, monkeypatch) -> None:
    from skat_ai import fixed_three_player_historical_list_aggregation as module

    original = module.build_fixed_three_player_historical_list_entry_facts
    calls = 0

    def counting_builder(historical_list):
        nonlocal calls
        calls += 1
        return original(historical_list)

    monkeypatch.setattr(
        module,
        "build_fixed_three_player_historical_list_entry_facts",
        counting_builder,
    )

    build_fixed_three_player_historical_list_aggregation(all_passed_list)

    assert calls == 1


def test_aggregation_requires_a_validated_version_one_source(all_passed_list) -> None:
    with pytest.raises(ValueError, match="validated historical list"):
        build_fixed_three_player_historical_list_aggregation({})
    with pytest.raises(ValueError, match="source schema version 1"):
        build_fixed_three_player_historical_list_aggregation(
            replace(all_passed_list, schema_version=2)
        )
    with pytest.raises(ValueError, match="source schema version 1"):
        build_fixed_three_player_historical_list_aggregation(
            replace(all_passed_list, schema_version=True)
        )

    duplicate_entries = (
        all_passed_list.entries[0],
        all_passed_list.entries[0],
        *all_passed_list.entries[2:],
    )
    with pytest.raises(ValueError, match="duplicate entry_id"):
        build_fixed_three_player_historical_list_aggregation(
            replace(all_passed_list, entries=duplicate_entries)
        )


def test_progression_rejects_non_authoritative_round_numbers(
    all_passed_list,
    monkeypatch,
) -> None:
    from skat_ai import fixed_three_player_historical_list_aggregation as module

    facts = build_fixed_three_player_historical_list_entry_facts(all_passed_list)
    invalid_facts = (replace(facts[0], round_number=2), *facts[1:])
    monkeypatch.setattr(
        module,
        "build_fixed_three_player_historical_list_entry_facts",
        lambda historical_list: invalid_facts,
    )

    with pytest.raises(ValueError, match="authoritative round numbers"):
        build_fixed_three_player_historical_list_aggregation(all_passed_list)


def test_standings_reject_formula_inconsistent_totals(all_passed_list) -> None:
    aggregation = build_fixed_three_player_historical_list_aggregation(all_passed_list)
    invalid_totals = (
        replace(aggregation.player_totals[0], total_performance_points=999),
        *aggregation.player_totals[1:],
    )

    with pytest.raises(ValueError, match="Total performance"):
        build_fixed_three_player_historical_list_standings(invalid_totals)


def test_final_reconciliation_rejects_final_status_without_required_lot(
    all_passed_list,
) -> None:
    from skat_ai import fixed_three_player_historical_list_aggregation as module

    aggregation = build_fixed_three_player_historical_list_aggregation(all_passed_list)

    with pytest.raises(ValueError, match="status does not match"):
        module._validate_final_aggregation(
            replace(
                aggregation,
                ranking_status="final",
                lot_required_player_ids=(),
            ),
            settlement_score_sum=0,
        )


def test_all_passed_progression_has_36_no_score_snapshots(all_passed_list) -> None:
    aggregation = build_fixed_three_player_historical_list_aggregation(all_passed_list)

    assert len(aggregation.progression) == 36
    assert aggregation.played_game_count == 0
    assert aggregation.passed_deal_count == 36
    for entry_number, snapshot in enumerate(aggregation.progression, start=1):
        assert snapshot.entry_fact.entry_number == entry_number
        assert snapshot.entry_fact.entry_kind == "passed_deal"
        assert all(
            total.list_entry_count == entry_number
            and total.passed_deal_count == entry_number
            and total.played_game_count == 0
            and total.declarer_game_count == 0
            and total.defender_game_count == 0
            and total.total_performance_points == 0
            for total in snapshot.cumulative_player_totals
        )
        assert snapshot.tied_player_ids == (
            "player-a",
            "player-b",
            "player-c",
        )
        assert [row.rank for row in snapshot.provisional_standings] == [1, 1, 1]


def test_mixed_progression_adds_each_entry_once_and_never_applies_lot(mixed_list) -> None:
    aggregation = build_fixed_three_player_historical_list_aggregation(mixed_list)
    oracle = build_independent_oracle(mixed_list)

    assert aggregation.played_game_count == 2
    assert aggregation.passed_deal_count == 34
    for snapshot, expected_totals in zip(
        aggregation.progression,
        oracle["progression"],
        strict=True,
    ):
        assert tuple(
            build_serializable_fixed_three_player_historical_list_player_totals(total)
            for total in snapshot.cumulative_player_totals
        ) == expected_totals
        assert all(
            standing.rank >= 1 for standing in snapshot.provisional_standings
        )
    assert aggregation.progression[-1].cumulative_player_totals == (
        aggregation.player_totals
    )


def test_unique_final_standings_use_the_existing_ranking_contract(unique_list) -> None:
    aggregation = build_fixed_three_player_historical_list_aggregation(unique_list)

    assert aggregation.ranking_status == "final"
    assert aggregation.tied_player_ids == ()
    assert aggregation.lot_required_player_ids == ()
    assert aggregation.applied_lot_order is None
    assert [row.rank for row in aggregation.final_standings] == [1, 2, 3]
    assert [row.player_totals.player_id for row in aggregation.final_standings] == [
        "player-a",
        "player-b",
        "player-c",
    ]


def test_two_and_three_player_final_ties_preserve_competition_ranks(
    two_way_tie_list,
    three_way_tie_list,
) -> None:
    two_way = build_fixed_three_player_historical_list_aggregation(two_way_tie_list)
    three_way = build_fixed_three_player_historical_list_aggregation(three_way_tie_list)

    assert two_way.ranking_status == "lot_required"
    assert two_way.tied_player_ids == ("player-b", "player-c")
    assert two_way.lot_required_player_ids == two_way.tied_player_ids
    assert [row.rank for row in two_way.final_standings] == [1, 2, 2]
    assert three_way.ranking_status == "lot_required"
    assert three_way.tied_player_ids == ("player-a", "player-b", "player-c")
    assert [row.rank for row in three_way.final_standings] == [1, 1, 1]


def test_official_own_win_and_own_loss_tie_breaks_are_reused() -> None:
    own_win_totals = (
        make_totals("player-a", "place_1", own_games_won=1),
        make_totals("player-b", "place_2", player_game_points=50),
        make_totals("player-c", "place_3", player_game_points=-1),
    )
    own_loss_totals = (
        make_totals("player-a", "place_1"),
        make_totals(
            "player-b",
            "place_2",
            own_games_lost=1,
            player_game_points=50,
        ),
        make_totals("player-c", "place_3", player_game_points=-1),
    )

    own_win = build_fixed_three_player_historical_list_standings(own_win_totals)
    own_loss = build_fixed_three_player_historical_list_standings(own_loss_totals)

    assert [row.player_totals.player_id for row in own_win.standings] == [
        "player-a",
        "player-b",
        "player-c",
    ]
    assert [row.player_totals.player_id for row in own_loss.standings] == [
        "player-a",
        "player-b",
        "player-c",
    ]
    assert own_win.tied_player_ids == ()
    assert own_loss.tied_player_ids == ()


def test_valid_external_lots_resolve_exact_ties_and_preserve_metrics(
    two_way_tie_list,
    three_way_tie_list,
) -> None:
    unresolved = build_fixed_three_player_historical_list_aggregation(two_way_tie_list)
    two_way = build_fixed_three_player_historical_list_aggregation(
        two_way_tie_list,
        lot_order=["player-c", "player-b"],
    )
    three_way = build_fixed_three_player_historical_list_aggregation(
        three_way_tie_list,
        lot_order=["player-c", "player-a", "player-b"],
    )

    assert two_way.ranking_status == "final"
    assert two_way.tied_player_ids == ("player-b", "player-c")
    assert two_way.lot_required_player_ids == ()
    assert two_way.applied_lot_order == ("player-c", "player-b")
    assert [row.player_totals.player_id for row in two_way.final_standings] == [
        "player-a",
        "player-c",
        "player-b",
    ]
    assert [row.rank for row in two_way.final_standings] == [1, 2, 3]
    assert three_way.applied_lot_order == ("player-c", "player-a", "player-b")
    assert [row.rank for row in three_way.final_standings] == [1, 2, 3]
    assert totals_by_player(unresolved) == totals_by_player(two_way)

    supplied_order = ["player-c", "player-b"]
    frozen = build_fixed_three_player_historical_list_aggregation(
        two_way_tie_list,
        lot_order=supplied_order,
    )
    supplied_order.reverse()
    assert frozen.applied_lot_order == ("player-c", "player-b")


@pytest.mark.parametrize(
    ("fixture_name", "lot_order", "message"),
    [
        ("two_way_tie_list", ["player-b"], "two or three"),
        ("two_way_tie_list", ["player-b", "player-b"], "duplicate"),
        ("two_way_tie_list", ["player-b", "unknown"], "unknown"),
        (
            "two_way_tie_list",
            ["player-a", "player-b"],
            "exactly the unresolved tied players",
        ),
        (
            "three_way_tie_list",
            ["player-a", "player-b"],
            "exactly the unresolved tied players",
        ),
        ("unique_list", ["player-a", "player-b"], "when no unresolved tie"),
        ("two_way_tie_list", ("player-b", "player-c"), "must be a list"),
    ],
)
def test_invalid_external_lots_are_rejected(
    request,
    fixture_name: str,
    lot_order,
    message: str,
) -> None:
    historical_list = request.getfixturevalue(fixture_name)

    with pytest.raises(ValueError, match=message):
        build_fixed_three_player_historical_list_aggregation(
            historical_list,
            lot_order=lot_order,
        )


def test_complete_cross_player_reconciliation_matches_required_equations(
    mixed_list,
) -> None:
    aggregation = build_fixed_three_player_historical_list_aggregation(mixed_list)
    totals = aggregation.player_totals
    played = aggregation.played_game_count
    passed = aggregation.passed_deal_count
    wins = aggregation.declarer_win_count
    losses = aggregation.declarer_loss_count
    facts = build_fixed_three_player_historical_list_entry_facts(mixed_list)

    assert played + passed == aggregation.entry_count
    assert all(
        total.declarer_game_count + total.defender_game_count
        == total.played_game_count
        for total in totals
    )
    assert sum(total.declarer_game_count for total in totals) == played
    assert sum(total.defender_game_count for total in totals) == 2 * played
    assert sum(total.passed_deal_count for total in totals) == 3 * passed
    assert sum(total.defender_games_won for total in totals) == 2 * losses
    assert sum(total.defender_games_lost for total in totals) == 2 * wins
    assert sum(total.other_players_lost_games for total in totals) == 2 * losses
    assert sum(total.player_game_points for total in totals) == sum(
        fact.settlement_score for fact in facts if fact.entry_kind == "played_game"
    )


def test_old_standings_equivalence_for_all_played_list(all_played_list) -> None:
    assert_simplified_equivalence(all_played_list)
    assert_simplified_equivalence(
        all_played_list,
        lot_order=["player-c", "player-a", "player-b"],
    )


def test_old_standings_equivalence_for_mixed_list_and_lot(two_way_tie_list) -> None:
    assert_simplified_equivalence(two_way_tie_list)
    assert_simplified_equivalence(
        two_way_tie_list,
        lot_order=["player-c", "player-b"],
    )


@pytest.mark.parametrize(
    "fixture_name",
    [
        "unique_list",
        "two_way_tie_list",
        "three_way_tie_list",
        "mixed_list",
        "all_passed_list",
    ],
)
def test_independent_oracle_agrees_for_all_required_fixture_families(
    request,
    fixture_name: str,
) -> None:
    historical_list = request.getfixturevalue(fixture_name)
    aggregation = build_fixed_three_player_historical_list_aggregation(historical_list)
    oracle = build_independent_oracle(historical_list)

    assert tuple(
        build_serializable_fixed_three_player_historical_list_player_totals(total)
        for total in aggregation.player_totals
    ) == oracle["totals"]
    assert aggregation.tied_player_ids == oracle["tied_player_ids"]
    assert [row.player_totals.player_id for row in aggregation.final_standings] == [
        row["player_id"] for row in oracle["standings"]
    ]
    assert [row.rank for row in aggregation.final_standings] == [
        row["rank"] for row in oracle["standings"]
    ]


def test_independent_oracle_agrees_after_exact_external_lot(two_way_tie_list) -> None:
    lot_order = ["player-c", "player-b"]
    aggregation = build_fixed_three_player_historical_list_aggregation(
        two_way_tie_list,
        lot_order=lot_order,
    )
    oracle = build_independent_oracle(two_way_tie_list, lot_order=lot_order)

    assert [row.player_totals.player_id for row in aggregation.final_standings] == [
        row["player_id"] for row in oracle["standings"]
    ]
    assert [row.rank for row in aggregation.final_standings] == [
        row["rank"] for row in oracle["standings"]
    ]


def collect_keys(value) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {
            nested_key
            for nested_value in value.values()
            for nested_key in collect_keys(nested_value)
        }
    if isinstance(value, list):
        return {
            nested_key
            for nested_value in value
            for nested_key in collect_keys(nested_value)
        }
    return set()


def test_serialization_is_deterministic_and_privacy_safe(mixed_list) -> None:
    aggregation = build_fixed_three_player_historical_list_aggregation(mixed_list)

    first = build_serializable_fixed_three_player_historical_list_aggregation(
        aggregation
    )
    second = build_serializable_fixed_three_player_historical_list_aggregation(
        aggregation
    )

    assert first == second
    assert build_serializable_fixed_three_player_historical_list_progression_snapshot(
        aggregation.progression[0]
    ) == first["progression"][0]
    assert build_serializable_fixed_three_player_historical_list_standing(
        aggregation.final_standings[0]
    ) == first["final_standings"][0]
    assert first["aggregation_version"] == 1
    assert len(first["progression"]) == 36
    assert collect_keys(first).isdisjoint(
        {
            "historical_game",
            "players",
            "initial_hand",
            "hand",
            "skat",
            "discarded_cards",
            "tricks",
            "game_events",
            "private_ownership",
            "search_state",
        }
    )


def test_existing_simplified_performance_workflows_remain_unchanged() -> None:
    assert build_list_performance_summary(
        {
            "player_game_points": 120,
            "own_games_won": 3,
            "own_games_lost": 1,
            "other_players_lost_games": 2,
        },
        "isko_list",
    )["total_performance_points"] == 300
    assert build_list_performance_summary_from_game_contributions(
        [
            {
                "player_role": "defender",
                "game_outcome": "declarer_loss",
                "settlement_score": -72,
            }
        ],
        "isko_list",
    )["total_performance_points"] == 40
