# Fixed-three-player 36-game list contracts

This document defines source contract version `1` for one complete
ordered fixed-three-player historical list. It is the source foundation for the
separate
[36-position aggregation contract](fixed_three_player_36_game_list_aggregation.md),
and is exposed through the public JSON and CLI workflow added in Issue #130. It
is not an official list format.

## Rule and product ownership

### Direct rules

The contract preserves the following rule-owned behavior from the November 2022
ISkO and SkWO publication:

* the three table places remain fixed during the series under ISkO 3.2.1;
* the dealer advances through those fixed places under ISkO 3.2.19;
* a deal in which all players pass still advances the dealer under ISkO 3.3.7;
* list entries and current totals remain distinct list-recording concepts under
  SkWO 6.2.1 through 6.2.3;
* SkWO 6.3.1 adds `+50` for an own game won, `-50` for an own game lost, and,
  at a three-player table, `+40` to each defender when the declarer loses.

SkWO 6.1.3 is part of the documented list context. This internal contract does
not claim to implement every procedural, correction, signature, submission, or
reporting requirement around an official list.

### Product contract

Version `1` deliberately fixes these software boundaries:

* exactly 36 authoritative positions;
* exactly three fixed, stable, case-sensitive player identities;
* exactly 12 rounds of three entries;
* no participant replacement;
* exactly `played_game` or `passed_deal` at every position;
* authoritative entry-array order with no sorting;
* optional RFC 3339 timestamp auditing across present timestamps;
* strict reconciliation between table-place rotation and historical seats;
* no four-player support.

The 36-position boundary is the version-1 product contract. A passed deal is a
real list position but is not a fabricated historical game.

## Stable constants

The internal implementation defines:

```text
FIXED_THREE_PLAYER_HISTORICAL_LIST_SCHEMA_VERSION = 1
FIXED_THREE_PLAYER_LIST_PLAYER_COUNT = 3
FIXED_THREE_PLAYER_LIST_ENTRY_COUNT = 36
FIXED_THREE_PLAYER_LIST_ENTRIES_PER_ROUND = 3
FIXED_THREE_PLAYER_LIST_ROUND_COUNT = 12
```

Canonical table places are `place_1`, `place_2`, and `place_3`. Canonical entry
kinds are `played_game` and `passed_deal`. Canonical outcomes are
`declarer_win`, `declarer_loss`, and `passed_deal`.

## Players and labels

Players are serialized in canonical place order. IDs are opaque, stable,
case-sensitive, non-empty strings. Leading or trailing whitespace is rejected;
the builder never trims, changes case, parses, generates, or infers an ID from a
label or historical seat.

Labels are nullable display metadata. For each stable ID, the deterministic
canonical label is the one non-null value encountered first from the list player
and then from played historical records in authoritative entry order. Repeated
equal values and missing labels are accepted. Two distinct non-null values for
the same stable ID are rejected instead of choosing or normalizing one.

Players contain no cards, ratings, totals, ranks, or tournament metadata.

## Entry union

A played entry contains only its stable entry ID, `played_game` kind, and one
existing `HistoricalGameRecord`. Raw nested records are built with the current
historical-game builder and serialized with the canonical historical-record
serializer. The list does not accept caller-supplied result, winner, value,
Overbid, or settlement copies.

A passed entry contains only its stable entry ID, `passed_deal` kind, and a
nullable `played_at`. It has no game ID, historical game, declarer, declaration,
cards, Skat, discards, end reason, winner, or settlement. It consumes its normal
entry and round number and advances dealer rotation.

Entry IDs are unique. Historical game IDs are unique across played entries, so
the same game cannot appear under another entry ID.

## Entry and round numbers

Entry-array order is authoritative:

```text
entry_number = 1..36
round_number = floor((entry_number - 1) / 3) + 1
```

The builder does not sort by ID, timestamp, place, seat, outcome, or entry kind.

## Time audit

Played-game time comes only from `HistoricalGameRecord.played_at`. Passed-deal
time comes from its nullable `played_at`. Present values use the existing RFC
3339 parser and must be non-decreasing as chronological instants. Equal values
and missing values are allowed. Source timestamp text is retained, and time
validation never changes authoritative entry order.

## Dealer and seat rotation

Entry 1 is dealt by `place_1`. Dealer places then repeat as `place_1`,
`place_2`, `place_3`, including passed deals. Every fixed participant therefore
deals exactly 12 positions.

For each position, the next canonical place after the dealer is forehand, the
following place is middlehand, and the dealer is rearhand. The immutable seat
assignment contains dealer, forehand, middlehand, and rearhand player IDs.

Every played `HistoricalGameRecord` must contain exactly the list's three stable
IDs and must assign them to the expected rotating historical seats. A table
place is fixed across the list; a historical seat is not.

## Historical outcome extraction

For every played position, the list layer:

1. reuses the existing immutable historical record;
2. checks exact participant-set equality and rotating seats;
3. calls the existing historical summary;
4. requires complete final settlement;
5. derives `declarer_win` or `declarer_loss` through the existing performance
   helper;
6. requires a positive settlement score for a win and a negative score for a
   loss.

This supports normal completion, every currently supported shortened terminal
family, and either currently supported non-terminal continuation. The list
layer does not recalculate scoring, game result, game value, Overbid, Null,
shortening adjudication, or final settlement.

## Per-entry contributions

Every entry fact contains three contributions in canonical player order.

For a declarer win, the declarer receives the positive settlement score as game
points and the existing `+50` own-game bonus. Both defenders record a defender
loss and receive no bonus.

For a declarer loss, the declarer receives the negative settlement score as game
points and the existing `-50` own-game bonus. Both defenders record a defender
win, one other-player loss, and the existing `+40` bonus.

For a passed deal, every player records one list entry and one passed deal. All
played-game, declarer, defender, result, and point fields are zero. A passed deal
is not a defender game and has no zero settlement value.

Every per-entry total is checked through the existing performance formula.

## Entry facts and reconciliation

Each immutable fact includes schema/list identity, entry and round numbers,
entry identity/kind/outcome, optional time, dealer and seat assignment, nullable
game fields, and the three per-player contributions.

Validation reconciles exactly 36 facts, 12 rounds, 12 dealer positions per
player, played-plus-passed cardinality, played and passed role counts, exactly
two `+40` contributions for each declarer loss, zero passed-deal bonuses, and all
per-entry performance totals.

Facts remain non-cumulative. The separate internal aggregation layer immutably
adds these facts into cumulative totals, 36 progression snapshots, and final
standings without changing this source schema version or fact contract.

## Serialization and boundary

Internal source serializers preserve player, entry, historical seat, and contribution
order and retain nullable passed-deal fact fields. Canonical serialization can be
built again into an equivalent immutable list.

The public root field `fixed_three_player_historical_list_input` wraps the source
under `historical_list`, requires request `schema_version: 1`, and requires an
explicit `lot_order` that is null or a two/three-player external order. The
standalone strict schemas are
`schemas/fixed_three_player_historical_list.schema.json` and
`schemas/fixed_three_player_historical_list_input.schema.json`. Runtime
validation remains authoritative for stable identities, labels, seat rotation,
timestamps, settlement, and exact lot-group membership.

The implementation lives in:

* `fixed_three_player_historical_list.py`;
* `fixed_three_player_list_rotation.py`;
* `fixed_three_player_list_contribution.py`;
* `fixed_three_player_historical_list_aggregation.py`;
* `fixed_three_player_historical_list_comparison.py`;
* `fixed_three_player_historical_list_comparison_summary.py`;
* `fixed_three_player_historical_list_progression.py`;
* `fixed_three_player_historical_list_standings.py`;
* `fixed_three_player_historical_list_totals.py`.

Issue #130 adds no CLI flag: the root JSON field selects the workflow, and only
`--input`, `--output`, and `--quiet` are accepted. Public output is the complete
existing aggregation serialization under
`fixed_three_player_historical_list_summary`; it does not echo this source list
or any Historical Game Record. Existing `list_performance_input`,
`list_game_contributions`, `list_analysis_results`, and `list_standings_input`
remain unchanged and do not accept `passed_deal`.

Issue #145 adds internal complete validated-input, 36 Entry Fact, aggregation,
and Root Result ledgers. Played Entry references retain only source list, Entry,
and Game identity; Passed Deals have no Historical Game or Settlement reference.
Public input and output remain unchanged. See
[Dataset, list, and opponent provenance](dataset_list_and_opponent_provenance.md).

## Remaining scope

The source and aggregation contracts also feed the public versioned
[independent-list comparison contract](fixed_three_player_36_game_list_comparison.md).
The following remain open:

* series or tournament state.

Issue #160's internal `euroskat_36_standard_v1` Match format identity is separate
from this historical-list source and aggregation workflow. It does not change
entry rotation, Played Game or Passed Deal semantics, SkWO scoring, standings,
or comparison, and it adds no ranking or commercial tournament rules.

Automatic Training Dataset preparation is now a separate root-selected workflow
and does not consume or change this historical-list contract.
