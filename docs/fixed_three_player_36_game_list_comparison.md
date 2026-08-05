# Fixed-three-player 36-game list comparison

This document defines internal comparison contract version `1` for two or more
independent completed
[fixed-three-player 36-position historical-list aggregations](fixed_three_player_36_game_list_aggregation.md).
It adds no public input, output, schema, CLI workflow, example, generated
scenario, or package-root API.

## Stable contract

The comparison layer defines:

```text
FIXED_THREE_PLAYER_HISTORICAL_LIST_COMPARISON_VERSION = 1

FIXED_THREE_PLAYER_HISTORICAL_LIST_COMPARISON_BASIS =
    independent_completed_fixed_three_player_historical_lists

MIN_FIXED_THREE_PLAYER_HISTORICAL_LIST_COMPARISON_COUNT = 2
```

It accepts an immutable tuple of at least two aggregation-version-`1` values.
Source order is authoritative. The first source is the one reference list, and
every later source is compared independently with that same reference. Exactly
one pairwise result is produced for each non-reference source.

## Source validation

Every supplied frozen aggregation is validated rather than trusted. The strict
internal validator verifies aggregation version and basis, source schema version,
36 entries, twelve rounds, three canonical player-total rows, all cumulative
formulas, all 36 retained Entry Facts and progression snapshots, the progression
endpoint, provisional and final standings, ranking status, ties, required-lot
IDs, and any applied external lot.

Validation reconstructs cumulative totals and standings from retained Entry
Facts. It does not reopen Historical Game Records or recalculate game results,
values, shortening adjudication, Overbid, or settlement.

## Identity and independence

Every source must use a unique `list_id`. Played Game `game_id` values must be
disjoint across all source lists. The comparison uses only the retained
progression Entry Facts for this independence audit. Passed Deals have no Game
ID. Entry IDs remain scoped to one list and may repeat in another list.

The comparison never inspects source Historical Game Records.

## Participant reconciliation

Every source must contain exactly the same three stable, case-sensitive player
IDs. Missing players, additional players, and replacements are rejected. Labels
never establish identity.

Players are aligned by stable ID, not source tuple position or table place. A
player may occupy a different table place in another independent list. Output
player order always follows the reference list's canonical table-place order.

The canonical comparison label for a stable player is:

1. the reference label when non-null;
2. otherwise the first non-null label in source order;
3. otherwise `null`.

Distinct non-null labels for one stable ID are rejected. Labels are display
metadata and do not alter alignment, totals, deltas, or ranks.

## Source summaries

Each source has one compact immutable privacy-safe summary containing comparison
version and basis, list ID, source schema version, entry and round counts, Played
Game and Passed Deal counts, declarer wins and losses, ranking status, tied and
lot-required IDs, applied lot order, and compact final standings.

Each compact standing contains only:

```text
rank
player_id
player_label
table_place
total_performance_points
own_games_won
own_games_lost
```

Source summaries do not contain progression, Entry Facts, Historical Game
Records, or cards.

## Delta direction

Every delta uses:

```text
comparison - reference
```

Pairwise list-level deltas cover Played Games, Passed Deals, declarer wins, and
declarer losses. They are descriptive count differences and are not interpreted
as list or player quality.

Each player delta contains every numeric
`FixedThreePlayerHistoricalListPlayerTotals` field. The comparison does not add
percentages, averages, normalization, or cross-list totals.

## Rank comparison

Canonical rank-comparison statuses are:

```text
available
reference_lot_required
comparison_lot_required
both_lot_required
```

Ranks are available only when both source `ranking_status` values are `final`.
Applied external lots therefore count as resolved final rankings. For available
ranks:

```text
rank_position_change = reference_rank - comparison_rank
```

A positive value means movement toward rank 1. A negative value means movement
away from rank 1.

If either source still requires a lot, the status identifies the unresolved
source or sources and all three fields are `null` for every player:

```text
reference_rank
comparison_rank
rank_position_change
```

Performance deltas remain available. The comparison does not infer ranks from
table-place order, shared competition ranks, or unresolved tie order.

## Pairwise and overall results

Each pairwise result identifies the fixed reference and one comparison list,
embeds their compact summaries, records the four list-level deltas, states
whether final-rank comparison is available, and contains three player rows in
reference-player order.

The overall result records comparison version and basis, reference list ID,
source-list count, reference-ordered player IDs, ordered source summaries, and
ordered pairwise comparisons. It does not declare a better list, better player,
series winner, champion, or recommendation.

## No progression or series comparison

Position `n` in one independent list has no declared strategic relationship to
position `n` in another. The comparison therefore produces no progression,
round, entry-by-entry, declarer-by-position, game-by-position, or strategic
deltas.

The result is not multi-list aggregation. It produces no summed cross-list
totals, averages, normalized scores, combined standings, player ratings, series
state, or series winner.

## Serialization and privacy

Deterministic internal serializers preserve source order, comparison order,
reference-player order, and explicit nullable rank fields. They serialize only
source summaries, player-total deltas, player comparisons, pairwise comparisons,
and the overall result.

They do not serialize progression, Entry Facts, Historical Game Records, hands,
Skat, discards, tricks, ownership, or Search state. No public schema is
registered.

## Remaining scope

Public historical-list input and output, schemas, CLI integration, examples,
generated scenarios, and automatic dataset preparation remain open. Formal
series aggregation, tournament management, official reporting, ratings, and
progression-position comparison are not part of this comparison contract.
