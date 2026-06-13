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
| `isko_list`   | Partially implemented ISkO-style rating for the fixed three-player table.             |

If omitted, `performance_rating_summary.rating_system` is `null`.

Unknown values are rejected during input validation.

## Fixed three-player table assumption

The project assumes a fixed three-player table.

No table-size input field is required.

The fixed assumption is exposed in the output:

```json
{
  "table_player_count": 3
}
```

Four-player table performance rating is not modeled.

## Partial ISkO list rating

The project includes a partial ISkO-style performance rating implementation for a single game.

Current assumptions:

* The table is always a fixed three-player table.
* `rating_system` must be set to `isko_list`.
* The implementation currently covers the declarer's single-game rating perspective.
* Already aggregated list or series totals can be supplied directly.
* Normalized per-game list or series contributions can be supplied directly.
* Raw full-game aggregation, player-by-player list models, and tournament aggregation are not implemented yet.

Implemented rating points:

| Game outcome   | Declarer rating points |  Counterparty rating points |
| -------------- | ---------------------: | --------------------------: |
| Declarer wins  |                    +50 |                           0 |
| Declarer loses |                    -50 | +40 per counterparty player |

## Declarer rating score

`declarer_rating_score` is the current implemented ISkO-style score from the declarer's perspective.

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

Each `list_analysis_results` entry is assumed to represent the same rated
player as local `me`. The minimal required subset is `position.player_role`,
`final_settlement_summary.is_complete`, and, for complete settlements,
`final_settlement_summary.is_loss` plus `final_settlement_summary.settlement_score`.
Complete generated analysis-result objects are accepted as supersets; the input
schema intentionally does not embed the full output schema.

`list_performance_input`, `list_game_contributions`, and
`list_analysis_results` are alternative input modes. Supplying more than one is
rejected.

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

* ISkO-style performance rating is partially implemented for a fixed three-player table.
* The current ISkO rating implementation covers single-game declarer perspective only.
* `rating_score` currently equals `declarer_rating_score`.
* Counterparty points are exposed separately and are not aggregated into the declarer's rating score.
* Already aggregated list or series totals can be calculated when supplied via `list_performance_input`.
* Normalized per-game contributions can be calculated when supplied via `list_game_contributions`.
* Raw full-game aggregation, player-by-player list models, multi-list rollups, and tournament aggregation are not implemented yet.
* Four-player table performance rating is not modeled because the project currently assumes a fixed three-player table.
