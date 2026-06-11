# Scoring and settlement

This document explains card points, game value, and single-game settlement in `skat-ai`.

## Card points

Skat card points are:

| Rank  | Points |
| ----- | -----: |
| Ace   |     11 |
| Ten   |     10 |
| King  |      4 |
| Queen |      3 |
| Jack  |      2 |
| Nine  |      0 |
| Eight |      0 |
| Seven |      0 |

A complete game has 120 card points.

## Game value

`game_value_summary` calculates the declared game value.

For suit and grand games, the game value is based on:

```text
base_value * game_level
```

Base values:

| Game type | Base value |
| --------- | ---------: |
| Clubs     |         12 |
| Spades    |         11 |
| Hearts    |         10 |
| Diamonds  |          9 |
| Grand     |         24 |

The game level is based on:

* matador multiplier
* hand game
* Schneider announced
* Schwarz announced
* ouvert

## Matadors

Suit and grand games use matadors.

If `matadors` is explicitly provided in the input, the explicit value is used.

If `matadors` is missing or `null`, the engine tries to infer the matador count from currently known declarer cards where possible.

Automatic inference currently uses known declarer-card context from:

* `hand`
* `skat`, when available and allowed by the analysis mode

If matadors cannot be inferred for a suit or grand game, the game value remains incomplete.

Null games do not use matadors.

## Null games

Null games use fixed game values.

Typical supported Null values:

| Type             | Value |
| ---------------- | ----: |
| Null             |    23 |
| Null hand        |    35 |
| Null ouvert      |    46 |
| Null ouvert hand |    59 |

## Schneider and Schwarz

`game_result_summary` tracks raw and effective Schneider/Schwarz status.

The engine distinguishes between:

* raw point-based Schneider/Schwarz status
* effective final-state-aware Schneider/Schwarz status

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

| Field              | Meaning                                   |
| ------------------ | ----------------------------------------- |
| `declarer_points`  | Known declarer card points.               |
| `defender_points`  | Known defender card points.               |
| `points_remaining` | Remaining unassigned card points.         |
| `is_complete`      | Whether all 120 card points are assigned. |
| `winner`           | `declarer`, `defenders`, or `undecided`.  |

## Adjusted game result summary

`adjusted_game_result_summary` applies `game_end_reason`.

For claim and concession scenarios, remaining card points are assigned according to the declared game-end reason.

Examples:

| game_end_reason                       | Remaining points go to |
| ------------------------------------- | ---------------------- |
| `declarer_claimed_remaining_tricks`   | declarer               |
| `defenders_conceded_remaining_tricks` | declarer               |
| `declarer_conceded_remaining_tricks`  | defenders              |
| `not_ended`                           | no assignment          |
| `normal_completion`                   | no assignment          |

The adjusted result is used by final settlement.

## Final settlement

`final_settlement_summary` describes single-game settlement.

It combines:

```text
game_value_summary
adjusted_game_result_summary
overbid_summary
```

It does not calculate full list, series, or tournament performance rating.

That is handled separately by `performance_rating_summary`.

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
Declarer wins: settlement_score = effective_game_value
Declarer loses: settlement_score = -2 * effective_game_value
```

Supported Suit/Grand overbid cases force the declarer into a settlement loss and use the required game value.

Example:

```json
"final_settlement_summary": {
  "is_complete": true,
  "declarer_won_by_card_points": true,
  "winner": "defenders",
  "game_value": 48,
  "effective_game_value": 72,
  "bid_value": 60,
  "settlement_score": -144,
  "is_loss": true,
  "is_overbid": true,
  "overbid_required_game_value": 72
}
```

In this example, the declarer won by card points but loses settlement because the game was overbid.

## Performance rating separation

Single-game settlement and performance rating are intentionally separate.

`final_settlement_summary` answers:

* Did the declarer win or lose the individual game?
* What game value or effective game value is used?
* What is the settlement score?

`performance_rating_summary` answers:

* Which performance-rating system is active?
* Which part of the rating system is currently implemented?
* What single-game declarer rating score is calculated?
* Which counterparty/defender points are exposed?

Current partial ISkO-style rating is documented in:

[Performance rating documentation](performance_rating.md)

## Current limitations

* Full official settlement nuances are not completely modeled yet.
* Claim and concession handling assigns remaining card points according to `game_end_reason`; it does not simulate the actual remaining tricks.
* The engine does not yet verify whether a claim was strategically or legally justified.
* Null-game overbid settlement remains conservative when no `required_game_value` is available.
* List, series, and tournament performance rating are handled separately and are not fully implemented yet.
* Automatic matador inference is conservative and currently uses known declarer cards from hand and skat context where possible.