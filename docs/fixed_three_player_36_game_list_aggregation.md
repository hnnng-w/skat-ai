# Fixed-three-player 36-game list aggregation

This document defines internal aggregation contract version `1` for one validated
[fixed-three-player 36-position historical list](fixed_three_player_36_game_list_contracts.md).
It adds cumulative totals, one progression snapshot per position, and final SkWO
standings without adding a public input, output, schema, CLI workflow, or
package-root API.

## Stable contract

The aggregation layer defines:

```text
FIXED_THREE_PLAYER_HISTORICAL_LIST_AGGREGATION_VERSION = 1
FIXED_THREE_PLAYER_HISTORICAL_LIST_STANDINGS_BASIS =
    fixed_three_player_historical_36_position_list
```

The entry point accepts one validated source-schema-version-`1` historical list
and an optional externally supplied final `lot_order`. It derives the 36 existing
entry facts exactly once through the source-contract builder. It does not inspect
cards or independently calculate result, game value, shortening, or settlement.
There is no RNG or seed input.

## Cumulative player totals

Every immutable player-total row preserves stable identity, nullable label, and
canonical table place. It cumulatively records list entries, played games, passed
deals, declarer and defender games, own and defender results, other-player losses,
game points, both bonus components, and total performance points.

Totals are built only by immutable addition of the three existing contributions
at each entry. Every row validates:

```text
list_entry_count = played_game_count + passed_deal_count
played_game_count = declarer_game_count + defender_game_count
declarer_game_count = own_games_won + own_games_lost
defender_game_count = defender_games_won + defender_games_lost
other_players_lost_games = defender_games_won

own_game_bonus_points = own_games_won * 50 + own_games_lost * -50
opponent_loss_bonus_points = other_players_lost_games * 40
total_performance_points =
    player_game_points
    + own_game_bonus_points
    + opponent_loss_bonus_points
```

Counts are non-negative integers. Point values are integers and may be negative.
Defender games are never derived from total list positions.

## Progression

The aggregation contains exactly 36 frozen snapshots in authoritative source
order. Snapshot `n` contains source fact `n`, cumulative totals from facts `1`
through `n`, provisional standings, and the unresolved tied player IDs.

Every player's `list_entry_count` equals `n`. The current entry contribution is
reconciled as the exact delta from the previous snapshot. Identity, labels, and
table places remain fixed. Provisional standings use the same ranking contract as
final standings, including shared competition ranks, but never apply a lot.

A Passed Deal still creates the next snapshot. It increments each player's
list-entry and passed-deal counts while changing no played-game, role, result,
point, bonus, or performance value.

## Final standings

Standings use only the SkWO 6.3.1 comparison sequence already implemented by the
project:

1. total performance points descending;
2. own games won descending;
3. own games lost ascending;
4. an externally executed lot for the exact remaining tie.

Canonical table-place order is only deterministic pre-lot ordering. It is not an
official tie-break. Without a tie, `ranking_status` is `final`. An unresolved tie
uses shared competition ranks, reports `ranking_status: lot_required`, and exposes
the exact two- or three-player lot group.

The optional lot must be a unique two- or three-ID list exactly equal to the one
unresolved final tie group. Partial groups, unknown or non-tied IDs, duplicate IDs,
and a lot when no tie exists are rejected. A valid lot changes only tied row order
and ranks, sets `ranking_status` to `final`, and is frozen as `applied_lot_order`.
The engine never generates or executes a random lot.

## Reconciliation

Every progression prefix and the final result reconcile Played Games and Passed
Deals separately. Final validation includes:

```text
played entries + passed entries = 36
declarer wins + declarer losses = played entries
sum declarer games = played entries
sum defender games = 2 * played entries
sum passed-deal counts = 3 * passed entries
sum defender wins = 2 * declarer losses
sum defender losses = 2 * declarer wins
sum other-player losses = 2 * declarer losses
sum player game points = sum played-entry settlement scores
```

The final progression totals equal the final player totals. Final standings are
rebuilt from and reconciled with those totals, including metrics, ranks, ties,
ranking status, required lot IDs, and applied lot order.

## Existing standings equivalence

For lists with no Passed Deals, every comparable scored metric, ranking key, tie,
rank, and external-lot result matches the existing simplified fixed-three-player
standings path. For mixed lists, the equivalent simplified input contains Played
Game facts only and produces the same comparable result. The old `games_played`
field corresponds to the new `played_game_count`, not `list_entry_count`.

The existing simplified input modes retain their current semantics and do not
accept Passed Deals.

## Serialization and privacy

Deterministic internal serializers cover player totals, standings rows,
progression snapshots, and the final aggregation. Snapshot entry facts reuse the
existing safe entry-fact serializer.

Aggregation serialization does not include source historical records, hands,
Skat, discards, tricks, private ownership, or Search state. The serializers are
internal and are not registered in a public schema or output field.

## Remaining scope

The following remain open:

* comparison across independent completed lists;
* public historical-list input and output;
* public schemas, CLI integration, examples, and generated scenarios;
* automatic dataset preparation;
* series aggregation and standings;
* tournament management and official federation reporting.

Four-player tables remain unconditionally out of scope.
