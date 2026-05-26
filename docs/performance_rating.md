# Performance rating

This document explains the performance-rating layer in `skat-ai`.

Performance rating is intentionally separated from single-game settlement.

## Settlement vs performance rating

`final_settlement_summary` describes the settlement of a single Skat game.

It answers questions such as:

- Did the declarer win or lose the individual game?
- What is the game value?
- Was the game overbid?
- Which effective game value is used for settlement?
- What is the individual settlement score?

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

| Value | Meaning |
|---|---|
| `placeholder` | Generic placeholder rating system. |
| `isko_list` | Partially implemented ISkO-style single-game rating for the fixed three-player table. |

If omitted, `performance_rating_summary.rating_system` is `null`.

Unknown values are rejected during input validation.

## Fixed three-player table assumption

The project assumes a fixed three-player table.

No table-size input field is required.

The fixed assumption is exposed in the output:

```json
"table_player_count": 3
```

Four-player table performance rating is not modeled.

## Partial ISkO list rating

The project includes a partial ISkO-style performance rating implementation for a single game.

Current assumptions:

- The table is always a fixed three-player table.
- `rating_system` must be set to `isko_list`.
- The implementation currently covers the declarer's single-game rating perspective.
- Full list, series, and tournament aggregation is not implemented yet.

Implemented rating points:

| Game outcome | Declarer rating points | Counterparty rating points |
|---|---:|---:|
| Declarer wins | +50 | 0 |
| Declarer loses | -50 | +40 per counterparty player |

## Declarer rating score

`declarer_rating_score` is the current implemented ISkO-style score from the declarer's perspective.

```text
declarer_rating_score = settlement_score + declarer_rating_points
```

`rating_score` is currently an alias for `declarer_rating_score`.

Examples:

| Settlement score | Declarer rating points | Declarer rating score |
|---:|---:|---:|
| 72 | 50 | 122 |
| -144 | -50 | -194 |

The counterparty rating points are shown separately and are not added to the declarer's `rating_score`.

## Counterparty rating points

`counterparty_rating_points` describes the points per counterparty player.

For the fixed three-player table:

| Game outcome | counterparty_rating_points |
|---|---:|
| Declarer wins | 0 |
| Declarer loses | 40 |

`defender_rating_points` is currently an alias for `counterparty_rating_points`.

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

| Field | Meaning |
|---|---|
| `is_implemented` | `false`, because full list/series/tournament rating is not complete. |
| `is_partially_implemented` | `true` for `isko_list`, because single-game declarer rating is calculated. |
| `implemented_scope` | The part that is currently calculated. |
| `unsupported_scope` | The part that is still missing. |

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
  "game_outcome": "declarer_loss",
  "settlement_score": -144,
  "rating_score": -194,
  "declarer_rating_score": -194,
  "declarer_rating_points": -50,
  "counterparty_rating_points": 40,
  "defender_rating_points": 40
}
```

## Current limitations

- ISkO-style performance rating is partially implemented for a fixed three-player table.
- The current ISkO rating implementation covers single-game declarer perspective only.
- `rating_score` currently equals `declarer_rating_score`.
- Counterparty points are exposed separately and are not aggregated into the declarer's rating score.
- Full list, series, and tournament aggregation is not implemented yet.
- Four-player table performance rating is not modeled because the project currently assumes a fixed three-player table.