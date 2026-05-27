# Output JSON

This document describes the JSON output produced by `skat-ai`.

## JSON schema

A draft output JSON schema is available at:

[`schemas/output.schema.json`](../schemas/output.schema.json)

The schema is intended as a documentation and validation aid. It checks the main output structure and important summary fields, but it is intentionally not a fully strict representation of every nested analysis detail.

Generated outputs for selected examples can be validated against the schema with:

```powershell
python scripts/validate_generated_outputs_schema.py

The project check script also runs generated-output schema validation.
```

## Top-level fields

Typical top-level fields include:

| Field | Meaning |
|---|---|
| `input_file` | Source input file. |
| `position` | Normalized position data. |
| `settings` | Simulation settings. |
| `opponent_policy_settings` | Opponent policy configuration. |
| `profile_preset_settings` | Profile-preset configuration. |
| `analysis_metadata` | Strategic metadata. |
| `game_declaration` | Serializable game declaration. |
| `game_value_summary` | Game value calculation result. |
| `overbid_summary` | Bid-value and overbid evaluation. |
| `legal_cards` | Legal cards for the current decision. |
| `analysis_report` | Card analysis report. |
| `strategic_summary` | Human-readable strategic summary. |
| `score_summary` | Raw known card-point summary. |
| `game_result_summary` | Raw game result from known card points. |
| `adjusted_game_result_summary` | Game result after game-end adjustment. |
| `final_settlement_summary` | Single-game settlement summary. |
| `performance_rating_summary` | Performance-rating layer. |
| `recommendation` | Recommended card and reason. |
| `multi_step_result` | Optional multi-step simulation result. |
| `policy_comparison_result` | Optional policy-comparison result. |

## Game declaration

Example:

```json
"game_declaration": {
  "game_type": "grand",
  "hand_game": false,
  "ouvert": false,
  "schneider_announced": false,
  "schwarz_announced": false,
  "matadors": 2,
  "bid_value": 72
}
```

## Game value summary

Example:

```json
"game_value_summary": {
  "game_type": "grand",
  "is_null_game": false,
  "base_value": 24,
  "game_level": 3,
  "game_value": 72,
  "details": {
    "is_complete": true,
    "matadors": 2,
    "matador_multiplier": 3,
    "hand_game": false,
    "schneider_announced": false,
    "schwarz_announced": false,
    "ouvert": false,
    "modifier_multiplier": 0
  }
}
```

If required inputs are missing, `game_value` may be `null`.

## Overbid summary

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
| `bid_value` | Bid value from input, or `null`. |
| `game_value` | Calculated game value, or `null`. |
| `is_overbid` | `true`, `false`, or `null` if unknown. |
| `margin` | `game_value - bid_value`. Negative means overbid. |
| `required_game_value` | Smallest reachable Suit/Grand game value that covers the bid. |
| `status` | `not_overbid`, `overbid`, `unknown_bid_value`, or `unknown_game_value`. |

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

`game_result_summary` describes the raw known card-point result before game-end adjustment.

Example:

```json
"game_result_summary": {
  "declarer_points": 75,
  "defender_points": 45,
  "points_remaining": 0,
  "is_complete": true,
  "winner": "declarer"
}
```

## Adjusted game result summary

`adjusted_game_result_summary` applies `game_end_reason`.

For example, if the declarer claims remaining tricks, remaining card points are assigned to the declarer.

Example:

```json
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
```

## Final settlement summary

`final_settlement_summary` describes single-game settlement.

Example:

```json
"final_settlement_summary": {
  "is_complete": true,
  "missing_inputs": [],
  "declarer_won_by_card_points": true,
  "winner": "declarer",
  "game_value": 72,
  "effective_game_value": 72,
  "bid_value": 72,
  "settlement_score": 72,
  "is_loss": false,
  "is_overbid": false,
  "overbid_margin": 0,
  "overbid_status": "not_overbid",
  "overbid_required_game_value": 72
}
```

`effective_game_value` is the value used for settlement scoring.

For supported Suit/Grand overbid cases, `effective_game_value` equals `required_game_value`.

## Performance rating summary

`performance_rating_summary` is separate from single-game settlement.

Example for a won declarer game with `rating_system = "isko_list"`:

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

Meaning:

| Field | Meaning |
|---|---|
| `rating_score` | Alias for `declarer_rating_score`. |
| `declarer_rating_score` | `settlement_score + declarer_rating_points`. |
| `declarer_rating_points` | +50 for declarer win, -50 for declarer loss. |
| `counterparty_rating_points` | Points per counterparty player. |
| `defender_rating_points` | Alias for `counterparty_rating_points`. |
| `implemented_scope` | Scope currently calculated. |
| `unsupported_scope` | Scope still missing. |

## Analysis report

`analysis_report` contains one entry per legal card.

Example:

```json
{
  "card": "SA",
  "win_rate": 0.659,
  "average_trick_points": 12.737,
  "average_points_won": 8.304,
  "average_points_lost": 4.433,
  "expected_point_swing": 3.871,
  "is_recommended": true
}
```

## Recommendation

Example:

```json
"recommendation": {
  "card": "SA",
  "reason": "This card has the highest estimated immediate expected point swing: 3.87."
}
```