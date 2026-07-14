# Performance rating

This document explains the performance-rating layer in `skat-ai`.

Performance rating is intentionally separated from single-game settlement.

## Settlement vs performance rating

`final_settlement_summary` describes the settlement of a single Skat game.

It answers questions such as:

* Did the declarer win or lose the individual game?
* What is the game value?
* Was the game overbid?
* Which effective game value is used for settlement?
* What is the individual settlement score?

`performance_rating_summary` is a separate output layer for list, series, or tournament rating.

This separation is important because official Skat performance rating can add or subtract rating points beyond the individual game value.

## performance_rating_system

Input files may optionally include:

```json
{
  "performance_rating_system": "isko_list"
}
```

Supported values:

| Value         | Meaning                                                                               |
| ------------- | ------------------------------------------------------------------------------------- |
| `placeholder` | Generic placeholder rating system.                                                    |
| `isko_list`   | Partially implemented SkWO-style performance scoring for the fixed three-player table. |

If omitted, `performance_rating_summary.rating_system` is `null`.

Unknown values are rejected during input validation.

## Fixed three-player table assumption

The project assumes a fixed three-player table.

There is no supported public `table_size` input field. A top-level `table_size`, if supplied as extra metadata, is ignored by rating logic.

The fixed assumption is exposed in the output:

```json
{
  "table_player_count": 3
}
```

Four-player table performance rating is not modeled.

## Partial SkWO list performance

The project includes a partial SkWO-style performance implementation for a single game.

Current assumptions:

* The table is always a fixed three-player table.
* `rating_system` must be set to `isko_list`.
* The implementation currently covers the declarer's single-game rating perspective.
* Already aggregated list or series totals can be supplied directly.
* Normalized per-game list or series contributions can be supplied directly.
* Explicit fixed three-player standings game results can be supplied directly.
* Raw full-game aggregation beyond explicit standings input, multi-list rollups, full tournament aggregation, and official report formats are not implemented yet.

Implemented rating points:

| Game outcome   | Declarer rating points |  Counterparty rating points |
| -------------- | ---------------------: | --------------------------: |
| Declarer wins  |                    +50 |                           0 |
| Declarer loses |                    -50 | +40 per counterparty player |

## Declarer rating score

`declarer_rating_score` is the current implemented SkWO-style score from the declarer's perspective.

```text
declarer_rating_score = settlement_score + declarer_rating_points
```

`rating_score` is currently an alias for `declarer_rating_score`.

Examples:

| Settlement score | Declarer rating points | Declarer rating score |
| ---------------: | ---------------------: | --------------------: |
|               72 |                     50 |                   122 |
|             -144 |                    -50 |                  -194 |

The counterparty rating points are shown separately and are not added to the declarer's `rating_score`.

## Counterparty rating points

`counterparty_rating_points` describes the points per counterparty player.

For the fixed three-player table:

| Game outcome   | counterparty_rating_points |
| -------------- | -------------------------: |
| Declarer wins  |                          0 |
| Declarer loses |                         40 |

`defender_rating_points` is currently an alias for `counterparty_rating_points`.

## List or series input modes

Input files may optionally include already aggregated list or series totals:

```json
{
  "performance_rating_system": "isko_list",
  "list_performance_input": {
    "player_game_points": 120,
    "own_games_won": 3,
    "own_games_lost": 1,
    "other_players_lost_games": 2
  }
}
```

`list_performance_input` is optional. If it is absent, no `list_performance_summary` key is emitted.

When `list_performance_input` is present, `performance_rating_system` must be `isko_list`.

The input totals are already aggregated. The engine does not aggregate raw individual games in this mode.

See `examples/grand_list_performance_input.json` for a complete input example.

As an alternative, input files may include normalized per-game contributions:

```json
{
  "performance_rating_system": "isko_list",
  "list_game_contributions": [
    {
      "player_role": "declarer",
      "game_outcome": "declarer_win",
      "settlement_score": 96
    },
    {
      "player_role": "defender",
      "game_outcome": "declarer_loss",
      "settlement_score": -144
    }
  ]
}
```

See `examples/grand_list_game_contributions.json` for a complete input example.

As a third alternative, input files may include local analysis results:

```json
{
  "performance_rating_system": "isko_list",
  "list_analysis_results": [
    {
      "position": {
        "player_role": "declarer"
      },
      "final_settlement_summary": {
        "is_complete": true,
        "is_loss": false,
        "settlement_score": 96
      }
    }
  ]
}
```

See `examples/grand_list_analysis_results.json` for a complete input example.

Each `list_analysis_results` entry is assumed to represent the same rated
player as local `me`. The minimal required subset is `position.player_role`,
`final_settlement_summary.is_complete`, and, for complete settlements,
`final_settlement_summary.is_loss` plus `final_settlement_summary.settlement_score`.
Complete generated analysis-result objects are accepted as supersets; the input
schema intentionally does not embed the full output schema.

Per-game input modes also accept validation-only stable metadata:

```json
{
  "rated_player_id": "player-123",
  "game_id": "game-001"
}
```

`rated_player_id` and `game_id` are optional for `list_game_contributions` and
`list_analysis_results`. They are opaque, case-sensitive strings. The engine
does not trim, normalize, parse, infer, or generate them.

Within one active per-game input mode, `rated_player_id` is all-or-none: either
no entry supplies it, or every entry supplies the same value. This verifies that
the aggregation describes one rated local player. The rated player's role may
still vary from game to game; declarer and defender roles affect scoring but do
not define identity.

`game_id` may be supplied for all, some, or no per-game entries. Duplicate
supplied `game_id` values are rejected. Duplicate detection is identifier-based
only: the engine does not hash entry content or compare entries structurally for
duplicates.

Identifiers do not appear in `list_performance_summary` and have no effect on
SkWO formulas, contribution counts, settlement scores, or summary basis values.
They do not introduce player-by-player standings, a tournament identity model,
or an opponent identity model.

Already aggregated `list_performance_input` remains totals-only. It cannot
support game-level duplicate detection because the per-game records are no
longer available after aggregation.

`list_performance_input`, `list_game_contributions`, and
`list_analysis_results` are single-rated-player input modes. They do not emit
three-player standings because they do not safely describe all three player
identities and totals.

`list_performance_input`, `list_game_contributions`, `list_analysis_results`,
and `list_standings_input` are alternative input modes. Supplying more than one
is rejected.

An empty `list_game_contributions` array is valid and emits a zeroed
`list_performance_summary`.

An empty `list_analysis_results` array is also valid and emits a zeroed
`list_performance_summary`. Incomplete analysis results and results with
`position.player_role: "unknown"` are skipped. Malformed analysis results are
rejected instead of skipped.

Each normalized contribution contains the rated player's role, the declarer's
game outcome, and the declarer's settlement score before performance points.

For a fixed three-player table, the summary uses:

```text
own_game_bonus_points = own_games_won * 50 + own_games_lost * -50
opponent_loss_bonus_points = other_players_lost_games * 40
total_performance_points = player_game_points + own_game_bonus_points + opponent_loss_bonus_points
```

Example output:

```json
"list_performance_summary": {
  "rating_system": "isko_list",
  "basis": "aggregated_list_or_series_totals",
  "table_size": 3,
  "player_game_points": 120,
  "own_games_won": 3,
  "own_games_lost": 1,
  "other_players_lost_games": 2,
  "own_game_bonus_points": 100,
  "opponent_loss_bonus_points": 80,
  "total_performance_points": 300
}
```

Contribution-derived summaries use the same field set with
`"basis": "normalized_game_contributions"`.

Analysis-result-derived summaries use the same field set with
`"basis": "local_analysis_results"`.

`list_performance_summary` is independent from `final_settlement_summary` and does not change `performance_rating_summary`.

## Fixed three-player standings input

`list_standings_input` provides an explicit fixed three-player list model:

```json
{
  "performance_rating_system": "isko_list",
  "list_standings_input": {
    "players": [
      {"player_id": "alice", "player_label": "Alice"},
      {"player_id": "bob", "player_label": "Bob"},
      {"player_id": "carol", "player_label": "Carol"}
    ],
    "games": [
      {
        "game_id": "game-1",
        "declarer_player_id": "alice",
        "game_outcome": "declarer_win",
        "settlement_score": 96
      }
    ]
  }
}
```

Validation rules:

* exactly three players are required
* `player_id` values must be unique non-empty strings
* `player_label` is optional and is echoed as `null` when omitted
* `games` may be empty
* each `declarer_player_id` must reference one declared player
* `game_outcome` is `declarer_win` or `declarer_loss`
* `declarer_win` requires a positive `settlement_score`
* `declarer_loss` requires a negative `settlement_score`
* `game_id` is optional, but supplied IDs must be unique

The output is `list_standings_summary`, not `list_performance_summary`.

See `examples/grand_list_standings_input.json` for a complete input example.

For each player:

```text
games_played = total number of games
declarer_games = games where declarer_player_id equals player_id
defender_games = game_count - declarer_games
own_games_won = declarer wins by that player
own_games_lost = declarer losses by that player
defender_games_won = defender games where the declarer lost
defender_games_lost = defender games where the declarer won
other_players_lost_games = defender_games_won
player_game_points = sum of settlement_score for own declarer games
own_game_bonus_points = own_games_won * 50 + own_games_lost * -50
opponent_loss_bonus_points = other_players_lost_games * 40
total_performance_points = player_game_points + own_game_bonus_points + opponent_loss_bonus_points
```

Standings are ordered by `total_performance_points` descending,
`player_game_points` descending, `own_games_won` descending, `own_games_lost`
ascending, `opponent_loss_bonus_points` descending, `player_id` ascending, then
`input_order` ascending. Ranks are unique row positions `1`, `2`, and `3`.

This is a fixed three-player list-aware review output contract. It is not a
four-player model, official federation report format, or full tournament/series
report.

## Implemented and unsupported scope

`performance_rating_summary` exposes the current implementation scope.

For `rating_system = "isko_list"`:

```json
{
  "is_implemented": false,
  "is_partially_implemented": true,
  "implemented_scope": "declarer_single_game_rating",
  "unsupported_scope": "full_list_series_tournament_rating"
}
```

Meaning:

| Field                      | Meaning                                                                    |
| -------------------------- | -------------------------------------------------------------------------- |
| `is_implemented`           | `false`, because full list/series/tournament rating is not complete.       |
| `is_partially_implemented` | `true` for `isko_list`, because single-game declarer rating is calculated. |
| `implemented_scope`        | The part that is currently calculated.                                     |
| `unsupported_scope`        | The part that is still missing.                                            |

## Example output

Example `performance_rating_summary` for a won declarer game:

```json
"performance_rating_summary": {
  "is_implemented": false,
  "is_partially_implemented": true,
  "implemented_scope": "declarer_single_game_rating",
  "unsupported_scope": "full_list_series_tournament_rating",
  "rating_system": "isko_list",
  "table_player_count": 3,
  "basis": "individual_game_settlement",
  "game_outcome": "declarer_win",
  "settlement_score": 72,
  "rating_score": 122,
  "declarer_rating_score": 122,
  "declarer_rating_points": 50,
  "counterparty_rating_points": 0,
  "defender_rating_points": 0,
  "unsupported_reason": "full_list_series_tournament_rating_not_implemented"
}
```

Example for a lost declarer game:

```json
"performance_rating_summary": {
  "is_implemented": false,
  "is_partially_implemented": true,
  "implemented_scope": "declarer_single_game_rating",
  "unsupported_scope": "full_list_series_tournament_rating",
  "rating_system": "isko_list",
  "table_player_count": 3,
  "basis": "individual_game_settlement",
  "game_outcome": "declarer_loss",
  "settlement_score": -144,
  "rating_score": -194,
  "declarer_rating_score": -194,
  "declarer_rating_points": -50,
  "counterparty_rating_points": 40,
  "defender_rating_points": 40,
  "unsupported_reason": "full_list_series_tournament_rating_not_implemented"
}
```

## Relationship to final settlement

Performance rating depends on completed single-game settlement.

If `final_settlement_summary` is incomplete, performance rating cannot produce a complete single-game rating score.

This can happen when required settlement inputs are missing, such as incomplete game value or unsupported overbid settlement state.

## Current limitations

* SkWO-style performance scoring is partially implemented for a fixed three-player table.
* The current SkWO performance implementation covers single-game declarer perspective only.
* `rating_score` currently equals `declarer_rating_score`.
* Counterparty points are exposed separately and are not aggregated into the declarer's rating score.
* Already aggregated list or series totals can be calculated when supplied via `list_performance_input`.
* Normalized per-game contributions can be calculated when supplied via `list_game_contributions`.
* Fixed three-player standings can be calculated when supplied via `list_standings_input`.
* Optional `rated_player_id` and `game_id` metadata can validate per-game list inputs, but does not affect scoring.
* Duplicate-game detection only uses supplied `game_id` values; content-based duplicate detection is not implemented.
* Raw full-game aggregation, multi-list rollups, full tournament aggregation, and official federation report formats are not implemented yet.
* Four-player table performance rating is not modeled because the project currently assumes a fixed three-player table.
