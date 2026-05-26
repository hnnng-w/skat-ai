# Scoring and settlement

This document explains card points, game value, and single-game settlement in `skat-ai`.

## Card points

Skat card points are:

| Rank | Points |
|---|---:|
| Ace | 11 |
| Ten | 10 |
| King | 4 |
| Queen | 3 |
| Jack | 2 |
| Nine | 0 |
| Eight | 0 |
| Seven | 0 |

A complete game has 120 card points.

## Game value

`game_value_summary` calculates the declared game value.

For suit and grand games, the game value is based on:

```text
base_value * game_level
```

Base values:

| Game type | Base value |
|---|---:|
| Clubs | 12 |
| Spades | 11 |
| Hearts | 10 |
| Diamonds | 9 |
| Grand | 24 |

The game level is based on:

- matador multiplier
- hand game
- Schneider announced
- Schwarz announced
- ouvert

If `matadors` is `null`, the game value remains incomplete for suit and grand games.

## Null games

Null games use fixed game values.

Typical supported Null values:

| Type | Value |
|---|---:|
| Null | 23 |
| Null hand | 35 |
| Null ouvert | 46 |
| Null ouvert hand | 59 |

## Schneider and Schwarz

`game_result_summary` tracks raw and effective Schneider/Schwarz status.

The engine distinguishes between:

- raw point-based Schneider/Schwarz status
- effective final-state-aware Schneider/Schwarz status

This prevents incomplete games from being treated as final Schneider or Schwarz outcomes too early.

## Score summary

`score_summary` combines explicit points and completed-trick points.

Example:

```json
"score_summary": {
  "explicit_declarer_points": 20,
  "explicit_defender_points": 10,
  "completed_trick_declarer_points": 31,
  "completed_trick_defender_points": 25,
  "total_declarer_points": 51,
  "total_defender_points": 35
}
```

## Game result summary

`game_result_summary` describes the raw card-point result before game-end adjustment.

Important fields include:

| Field | Meaning |
|---|---|
| `declarer_points` | Known declarer card points. |
| `defender_points` | Known defender card points. |
| `points_remaining` | Remaining unassigned card points. |
| `is_complete` | Whether all 120 card points are assigned. |
| `winner` | `declarer`, `defenders`, or `undecided`. |

## Final settlement

`final_settlement_summary` describes single-game settlement.

It combines:

```text
game_value_summary
adjusted_game_result_summary
overbid_summary
```

It does not calculate list, series, or tournament performance rating. That is handled by `performance_rating_summary`.

## Effective game value

`effective_game_value` is the value used for settlement scoring.

In normal cases:

```text
effective_game_value = game_value
```

In supported Suit/Grand overbid cases:

```text
effective_game_value = required_game_value
```

## Settlement score

Current simplified settlement scoring:

```text
Declarer wins:
settlement_score = effective_game_value

Declarer loses:
settlement_score = -2 * effective_game_value
```

Supported Suit/Grand overbid cases force the declarer into a settlement loss and use the required game value.

## Current limitations

- Full official settlement nuances are not completely modeled yet.
- List, series, and tournament performance rating are handled separately.
- The engine relies on declared metadata such as `matadors`; it does not yet infer matadors automatically.