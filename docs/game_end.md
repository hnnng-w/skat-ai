# Game-end handling

This document explains how `skat-ai` handles normal completion, claim, and concession.

## Purpose

Game-end handling separates the raw known card-point state from the adjusted final result used for settlement.

The raw card-point result is stored in:

```text
game_result_summary
```

The game-end-adjusted result is stored in:

```text
adjusted_game_result_summary
```

`final_settlement_summary` uses `adjusted_game_result_summary`, not the raw `game_result_summary`.

## Supported game_end_reason values

| Value                                 | Meaning                                                       |
| ------------------------------------- | ------------------------------------------------------------- |
| `not_ended`                           | The game is still in progress.                                |
| `normal_completion`                   | The game ended normally and all 120 card points are assigned. |
| `declarer_claimed_remaining_tricks`   | The declarer claimed the remaining tricks.                    |
| `declarer_conceded_remaining_tricks`  | The declarer conceded the remaining tricks.                   |
| `defenders_conceded_remaining_tricks` | The defenders conceded the remaining tricks.                  |

## Analysis mode

Ended game reasons are post-game information.

Therefore, these values require:

```json
{
  "analysis_mode": "post_game_review"
}
```

This applies to:

* `normal_completion`
* `declarer_claimed_remaining_tricks`
* `declarer_conceded_remaining_tricks`
* `defenders_conceded_remaining_tricks`

Live decision analysis should use:

```json
{
  "analysis_mode": "live_decision",
  "game_end_reason": "not_ended"
}
```

## Remaining-point assignment

When a game ends early, remaining card points are assigned according to `game_end_reason`.

| game_end_reason                       | Remaining points go to |
| ------------------------------------- | ---------------------- |
| `declarer_claimed_remaining_tricks`   | declarer               |
| `defenders_conceded_remaining_tricks` | declarer               |
| `declarer_conceded_remaining_tricks`  | defenders              |
| `not_ended`                           | no assignment          |
| `normal_completion`                   | no assignment          |

Example:

```json
{
  "game_result_summary": {
    "declarer_points": 46,
    "defender_points": 45,
    "points_remaining": 29,
    "is_complete": false,
    "winner": "undecided"
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

## Normal completion

`normal_completion` means the game ended by playing all tricks.

For Suit and Grand, validation expects all 120 card points to be assigned. For
Null, the completed result can instead be based on a reliable ten-trick history
with completed-trick ownership.

For Suit and Grand settlement, a normally completed ten-trick history can also
prove Schwarz through `completed_tricks[].winner_role`: if the losing side took
zero tricks, achieved Schwarz can affect `effective_game_value`. Card points
alone do not prove Schwarz.

For point-based Suit and Grand completion, validation expects:

```text
points_remaining = 0
```

If a Suit or Grand game has fewer than 120 assigned card points, it should not use `normal_completion`.

## Claim and concession

Claim and concession scenarios are modeled by assigning all remaining card points to the appropriate side.

Examples:

| Scenario                           | game_end_reason                       | Result                            |
| ---------------------------------- | ------------------------------------- | --------------------------------- |
| Declarer claims remaining tricks   | `declarer_claimed_remaining_tricks`   | Remaining points go to declarer.  |
| Defenders concede remaining tricks | `defenders_conceded_remaining_tricks` | Remaining points go to declarer.  |
| Declarer concedes remaining tricks | `declarer_conceded_remaining_tricks`  | Remaining points go to defenders. |

This is intentionally a scoring adjustment, not a full simulation of the remaining tricks.

Because claim and concession handling assigns remaining card points without
recording the actual remaining trick ownership, claims and concessions do not
establish Schwarz for settlement in the current implementation slice.

## Validation rules

The engine validates `game_end_reason` against the known card-point state.

Rules:

* `not_ended` requires remaining card points.
* `normal_completion` requires zero remaining card points.
* claim/concession reasons require remaining card points.
* unknown `game_end_reason` values are rejected.
* remaining card points cannot be negative.
* ended game reasons are rejected in `live_decision`.

This prevents inconsistent inputs such as:

* a normally completed game with only 86 assigned card points
* an unfinished game with all 120 card points already assigned
* claim/concession when no card points remain
* ended game metadata in live decision mode

## Relationship to settlement

`final_settlement_summary` uses the adjusted result.

This means claim/concession handling can decide the final winner before settlement is calculated.

For example:

1. `game_result_summary` may be incomplete.
2. `adjusted_game_result_summary` assigns remaining points.
3. `adjusted_game_result_summary.winner` becomes complete.
4. `final_settlement_summary` uses the adjusted winner and game value.

## Current limitations

* Claim and concession handling currently assigns all remaining card points according to `game_end_reason`.
* It does not simulate the actual remaining tricks.
* It does not prove Schwarz trick ownership for settlement.
* The engine does not yet verify whether a claim was strategically or legally justified.
* The engine does not yet model player agreement or disputes around claim/concession.
