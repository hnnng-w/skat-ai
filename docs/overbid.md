# Overbid handling

This document explains bid value handling and overbid settlement.

## bid_value

Input files can optionally include `bid_value`.

Example:

```json
{
  "game_type": "grand",
  "matadors": 1,
  "bid_value": 60
}
```

The engine compares `bid_value` with the calculated `game_value`.

Examples:

| game_value | bid_value | Result |
|---:|---:|---|
| 72 | 72 | not overbid |
| 72 | 60 | not overbid |
| 48 | 60 | overbid |
| null | 60 | unknown game value |
| 72 | null | unknown bid value |

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

| Field | Meaning |
|---|---|
| `bid_value` | The bid value from the input, or `null` if unknown. |
| `game_value` | The calculated game value, or `null` if incomplete. |
| `is_overbid` | `true`, `false`, or `null` if unknown. |
| `margin` | `game_value - bid_value`. Negative means overbid. |
| `required_game_value` | The smallest reachable Suit/Grand game value that covers the bid. |
| `status` | One of `not_overbid`, `overbid`, `unknown_bid_value`, or `unknown_game_value`. |

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
  "game_value": 48,
  "bid_value": 60,
  "is_overbid": true,
  "effective_game_value": 72,
  "settlement_score": -144
}
```

In this example, the declarer may still have won by card points. The settlement loss is caused by overbidding.

The raw card-point result remains visible through:

```json
"winner": "declarer",
"declarer_won_by_card_points": true
```

The settlement loss is visible through:

```json
"is_loss": true,
"is_overbid": true
```

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