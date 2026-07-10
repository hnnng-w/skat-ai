# Overbid handling

This document explains bid value handling and overbid settlement in `skat-ai`.

## Purpose

Overbid handling compares the declared or bid value with the calculated game value.

If the bid value is higher than the game value, the declarer is overbid.

For supported Suit and Grand games, the engine can calculate the required game value needed to cover the bid and use it for settlement loss calculation.

## bid_value input

Input files can optionally include `bid_value`.

Top-level example:

```json
{
  "game_type": "grand",
  "matadors": 1,
  "bid_value": 60
}
```

Nested game declaration example:

```json
{
  "game_declaration": {
    "matadors": 1,
    "bid_value": 60
  }
}
```

If both top-level and nested `bid_value` are present, the non-null top-level
value overrides the nested value. `bid_value: null` means the bid value is
unknown and allows a nested value to be used when one is present.

If `bid_value` is missing, overbid status is unknown.

## Basic comparison

The engine compares `bid_value` with `game_value`.

| game_value | bid_value | Result             |
| ---------: | --------: | ------------------ |
|         72 |        72 | not overbid        |
|         72 |        60 | not overbid        |
|         48 |        60 | overbid            |
|       null |        60 | unknown game value |
|         72 |      null | unknown bid value  |

## overbid_summary

Example:

```json
"overbid_summary": {
  "bid_value": 60,
  "game_value": 48,
  "is_overbid": true,
  "margin": -12,
  "required_game_value": 72,
  "status": "overbid"
}
```

Fields:

| Field                 | Meaning                                                                 |
| --------------------- | ----------------------------------------------------------------------- |
| `bid_value`           | The bid value from the input, or `null` if unknown.                     |
| `game_value`          | The calculated game value, or `null` if incomplete.                     |
| `is_overbid`          | `true`, `false`, or `null` if unknown.                                  |
| `margin`              | `game_value - bid_value`. Negative means overbid.                       |
| `required_game_value` | The smallest reachable Suit/Grand game value that covers the bid.       |
| `status`              | `not_overbid`, `overbid`, `unknown_bid_value`, or `unknown_game_value`. |

## required_game_value

For Suit and Grand games, game values are multiples of the base value.

If a game is overbid, the engine calculates the smallest reachable value that covers the bid.

Example:

```text
Grand base value = 24
game_value = 48
bid_value = 60
required_game_value = 72
```

This means the declarer needed a Grand value of 72 to cover the bid.

## effective_game_value

`final_settlement_summary` uses `effective_game_value` for settlement scoring.

For non-overbid games:

```text
effective_game_value = game_value
```

For supported Suit/Grand overbid games:

```text
effective_game_value = required_game_value
```

## Suit/Grand overbid settlement

If a Suit or Grand game is overbid:

```text
declarer loses settlement
settlement_score = -2 * required_game_value
```

Example:

```json
{
  "declarer_won_by_card_points": true,
  "winner": "declarer",
  "game_value": 48,
  "effective_game_value": 72,
  "bid_value": 60,
  "is_loss": true,
  "is_overbid": true,
  "settlement_score": -144
}
```

In this example, the declarer may still have won by card points.

The raw card-point result remains visible through:

```json
{
  "declarer_won_by_card_points": true
}
```

The settlement loss is visible through:

```json
{
  "winner": "declarer",
  "is_loss": true,
  "is_overbid": true
}
```

## Relationship to game value

Overbid handling depends on `game_value_summary`.

If the game value is incomplete, overbid status may be unknown.

Automatic matador inference can make some Suit/Grand game values complete even when `matadors` was not explicitly provided, as long as the currently known declarer-card context or safe concrete-declarer completed-trick ownership facts are sufficient.

## Null-game safeguard

Null games use fixed game values rather than base-value multipliers.

For this reason, overbid settlement scoring is currently supported for Suit and Grand games when `required_game_value` is available.

If a Null game is detected as overbid and no `required_game_value` is available, `final_settlement_summary` remains incomplete instead of guessing a settlement score.

Example:

```json
{
  "is_complete": false,
  "missing_inputs": ["overbid_required_game_value"],
  "is_overbid": true,
  "settlement_score": null
}
```

## Current limitations

* Suit/Grand overbid settlement is supported when `required_game_value` can be calculated.
* Null-game overbid settlement remains conservative when no `required_game_value` is available.
* The engine does not yet model all official settlement nuances.
