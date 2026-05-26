# Game-end handling

This document explains how `skat-ai` handles normal completion, claim, and concession.

## Supported game_end_reason values

| Value | Meaning |
|---|---|
| `not_ended` | The game is still in progress. |
| `normal_completion` | The game ended normally and all 120 card points are assigned. |
| `declarer_claimed_remaining_tricks` | The declarer claimed the remaining tricks. |
| `declarer_conceded_remaining_tricks` | The declarer conceded the remaining tricks. |
| `defenders_conceded_remaining_tricks` | The defenders conceded the remaining tricks. |

## Raw and adjusted result

The original card-point result is stored in:

```text
game_result_summary
```

The game-end-adjusted result is stored in:

```text
adjusted_game_result_summary
```

`final_settlement_summary` uses `adjusted_game_result_summary`, not the raw `game_result_summary`.

## Remaining-point assignment

When a game ends early, remaining card points are assigned according to `game_end_reason`.

| game_end_reason | Remaining points go to |
|---|---|
| `declarer_claimed_remaining_tricks` | declarer |
| `defenders_conceded_remaining_tricks` | declarer |
| `declarer_conceded_remaining_tricks` | defenders |
| `not_ended` | no assignment |
| `normal_completion` | no assignment |

Example:

```json
{
  "game_result_summary": {
    "declarer_points": 46,
    "defender_points": 45,
    "points_remaining": 29,
    "is_complete": false
  },
  "adjusted_game_result_summary": {
    "declarer_points": 75,
    "defender_points": 45,
    "points_remaining": 0,
    "is_complete": true,
    "winner": "declarer",
    "game_end_reason": "declarer_claimed_remaining_tricks",
    "remaining_points_recipient": "declarer",
    "remaining_points_assigned": 29
  }
}
```

## Validation rules

The engine validates `game_end_reason` against the known card-point state.

Rules:

- `not_ended` requires remaining card points.
- `normal_completion` requires zero remaining card points.
- claim/concession reasons require remaining card points.
- unknown `game_end_reason` values are rejected.
- remaining card points cannot be negative.

This prevents inconsistent inputs such as:

- a normally completed game with only 86 assigned card points
- an unfinished game with all 120 card points already assigned
- claim/concession when no card points remain

## Current limitations

- Claim and concession handling currently assigns all remaining card points according to `game_end_reason`.
- It does not simulate the actual remaining tricks.
- The engine does not yet verify whether a claim was strategically or legally justified.
- The engine does not yet model player agreement or disputes around claim/concession.