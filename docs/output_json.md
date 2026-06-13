# Output JSON

This document describes the JSON output produced by `skat-ai`.

## JSON schema

The output JSON schema is available at:

[`schemas/output.schema.json`](../schemas/output.schema.json)

The schema is intended as a documentation and validation aid. It checks the main output structure and important summary fields, but it is intentionally not a fully strict representation of every nested analysis detail.

Generated outputs for selected examples can be validated against the schema with:

```powershell
python scripts/validate_generated_outputs_schema.py
```

The project check script also runs generated-output schema validation:

```powershell
.\scripts\check.ps1
```

For the validation-layer overview and schema limitations, see:

[Schema validation documentation](schema_validation.md)

## Top-level fields

Typical top-level fields include:

| Field                            | Meaning                                                     |
| -------------------------------- | ----------------------------------------------------------- |
| `input_file`                     | Source input file.                                          |
| `position`                       | Normalized position data.                                   |
| `settings`                       | Simulation settings.                                        |
| `opponent_policy_settings`       | Global opponent policy configuration.                       |
| `profile_preset_settings`        | Profile-preset configuration.                               |
| `analysis_metadata`              | Strategic and analysis metadata.                            |
| `game_declaration`               | Serializable game declaration.                              |
| `game_value_summary`             | Game value calculation result.                              |
| `overbid_summary`                | Bid-value and overbid evaluation.                           |
| `legal_cards`                    | Legal cards for the current decision.                       |
| `analysis_report`                | Card analysis report.                                       |
| `strategic_summary`              | Human-readable strategic summary.                           |
| `score_summary`                  | Raw known card-point summary.                               |
| `game_result_summary`            | Raw game result from known card points.                     |
| `adjusted_game_result_summary`   | Game result after game-end adjustment.                      |
| `final_settlement_summary`       | Single-game settlement summary.                             |
| `performance_rating_summary`     | Performance-rating layer.                                   |
| `recommendation`                 | Recommended card and reason.                                |
| `post_game_review_summary`       | Actual-card comparison and post-game review result.         |
| `multi_step_result`              | Optional multi-step simulation result.                      |
| `policy_comparison_result`       | Optional policy-comparison result.                          |
| `information_policy_summary`     | Summary of the active live-vs-post-game information policy. |
| `left_opponent_policy_settings`  | Normalized policy settings for the left opponent.           |
| `right_opponent_policy_settings` | Normalized policy settings for the right opponent.          |

## Opponent policy settings

The output contains global and normalized left/right opponent policy settings.

Example:

```json
{
  "opponent_policy_settings": {
    "opponent_lead_policy": "lowest_point",
    "opponent_response_policy": "lowest_point"
  },
  "left_opponent_policy_settings": {
    "opponent_lead_policy": "highest_point",
    "opponent_response_policy": "basic_trick_play"
  },
  "right_opponent_policy_settings": {
    "opponent_lead_policy": "basic_defender_lead",
    "opponent_response_policy": "basic_defender_response"
  }
}
```

Meaning:

| Field                            | Meaning                                                           |
| -------------------------------- | ----------------------------------------------------------------- |
| `opponent_policy_settings`       | Global opponent policy settings and backward-compatible fallback. |
| `left_opponent_policy_settings`  | Normalized policy settings for the left opponent.                 |
| `right_opponent_policy_settings` | Normalized policy settings for the right opponent.                |

Current multi-step behavior:

* `right` lead uses `right_opponent_policy_settings.opponent_lead_policy`.
* `left` lead uses `left_opponent_policy_settings.opponent_lead_policy`.
* `right` response after a left lead uses `right_opponent_policy_settings.opponent_response_policy`.

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

`matadors` can be explicitly provided in the input. If it is missing or `null`, the engine may infer it from known declarer cards where possible.

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

If required inputs are missing and matadors cannot be inferred, `game_value` may be `null`.

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

| Field                 | Meaning                                                                 |
| --------------------- | ----------------------------------------------------------------------- |
| `bid_value`           | Bid value from input, or `null`.                                        |
| `game_value`          | Calculated game value, or `null`.                                       |
| `is_overbid`          | `true`, `false`, or `null` if unknown.                                  |
| `margin`              | `game_value - bid_value`. Negative means overbid.                       |
| `required_game_value` | Smallest reachable Suit/Grand game value that covers the bid.           |
| `status`              | `not_overbid`, `overbid`, `unknown_bid_value`, or `unknown_game_value`. |

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

For completed non-null suit and grand games with achieved Schneider,
`effective_game_value` includes one additional base-value level while
`game_value` remains the declared/pre-result value.

For supported Suit/Grand overbid cases, `effective_game_value` equals `required_game_value`.

## Information policy summary

`information_policy_summary` describes which information-boundary rules apply to the analysis.

Example for live analysis:

```json
{
  "analysis_mode": "live_decision",
  "skat_visibility": "unknown",
  "game_end_reason": "not_ended",
  "live_information_enforced": true,
  "known_post_game_skat_allowed": false,
  "known_skat_cards_allowed": false,
  "ended_game_allowed": false,
  "unverifiable_completed_trick_winner_metadata_allowed": false
}
```

Example for post-game review:

```json
{
  "analysis_mode": "post_game_review",
  "skat_visibility": "known_post_game",
  "game_end_reason": "normal_completion",
  "live_information_enforced": false,
  "known_post_game_skat_allowed": true,
  "known_skat_cards_allowed": true,
  "ended_game_allowed": true,
  "unverifiable_completed_trick_winner_metadata_allowed": true
}
```

Fields:

| Field                                                  | Meaning                                                               |
| ------------------------------------------------------ | --------------------------------------------------------------------- |
| `analysis_mode`                                        | Active analysis mode.                                                 |
| `skat_visibility`                                      | Whether the skat is unknown or known from post-game review.           |
| `game_end_reason`                                      | Game-end metadata used for remaining-point assignment.                |
| `live_information_enforced`                            | Whether live-information restrictions are active.                     |
| `known_post_game_skat_allowed`                         | Whether post-game skat visibility is allowed.                         |
| `known_skat_cards_allowed`                             | Whether known skat cards are allowed in the input.                    |
| `ended_game_allowed`                                   | Whether completed game states are allowed.                            |
| `unverifiable_completed_trick_winner_metadata_allowed` | Whether winner metadata without full verification context is allowed. |

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

| Field                        | Meaning                                      |
| ---------------------------- | -------------------------------------------- |
| `rating_score`               | Alias for `declarer_rating_score`.           |
| `declarer_rating_score`      | `settlement_score + declarer_rating_points`. |
| `declarer_rating_points`     | +50 for declarer win, -50 for declarer loss. |
| `counterparty_rating_points` | Points per counterparty player.              |
| `defender_rating_points`     | Alias for `counterparty_rating_points`.      |
| `implemented_scope`          | Scope currently calculated.                  |
| `unsupported_scope`          | Scope still missing.                         |

## List performance summary

`list_performance_summary` is emitted only when the input contains
`list_performance_input`, `list_game_contributions`, or
`list_analysis_results`.

It is separate from both `performance_rating_summary` and `final_settlement_summary`.

Example:

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

Meaning:

| Field                        | Meaning                                                       |
| ---------------------------- | ------------------------------------------------------------- |
| `basis`                      | `aggregated_list_or_series_totals`, `normalized_game_contributions`, or `local_analysis_results`. |
| `table_size`                 | Fixed three-player table size used for ISkO-style points.     |
| `player_game_points`         | Already aggregated game points for the rated player.          |
| `own_games_won`              | Count of the rated player's won own games.                    |
| `own_games_lost`             | Count of the rated player's lost own games.                   |
| `other_players_lost_games`   | Count of lost games by the other two players.                 |
| `own_game_bonus_points`      | +50 per own game won and -50 per own game lost.               |
| `opponent_loss_bonus_points` | +40 per lost game by another player at the three-player table.|
| `total_performance_points`   | Sum of game points, own-game bonus points, and opponent-loss bonus points. |

When the summary is derived from `list_game_contributions`, it keeps the same
field set and uses `basis: "normalized_game_contributions"`. No contribution
rows are echoed in the output.

When the summary is derived from `list_analysis_results`, it keeps the same
field set and uses `basis: "local_analysis_results"`. Analysis-result rows are
not echoed in the output.

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

## Post-game review summary

`post_game_review_summary` compares the actual played card with the recommended card.

If `actual_card_played` was not provided, the summary is still present but marked as unavailable.

Example without `actual_card_played`:

```json
"post_game_review_summary": {
  "is_available": false,
  "reason": "actual_card_played_not_provided",
  "actual_card_played": null,
  "recommended_card": "SA",
  "actual_expected_point_swing": null,
  "recommended_expected_point_swing": 6.0,
  "expected_point_swing_difference": null,
  "decision_quality": "not_available",
  "decision_factors": ["actual_card_played_not_provided"],
  "decision_explanation": "No post-game review decision quality is available because actual_card_played was not provided.",
  "actual_card_rank": null,
  "recommended_card_rank": 1,
  "candidate_count": 3,
  "better_card_count": null
}
```

Example with `actual_card_played`:

```json
"post_game_review_summary": {
  "is_available": true,
  "reason": "actual_card_played_provided",
  "actual_card_played": "S9",
  "recommended_card": "SA",
  "actual_expected_point_swing": -4.0,
  "recommended_expected_point_swing": 6.0,
  "expected_point_swing_difference": 10.0,
  "decision_quality": "mistake",
  "decision_factors": [
    "lower_expected_point_swing_than_recommendation",
    "large_expected_point_swing_gap"
  ],
  "decision_explanation": "The actual card has a much lower expected point swing than the recommended card. Missed expected point swing: 10.00.",
  "actual_card_rank": 3,
  "recommended_card_rank": 1,
  "candidate_count": 3,
  "better_card_count": 2
}
```

Fields:

| Field                              | Meaning                                                                                   |
| ---------------------------------- | ----------------------------------------------------------------------------------------- |
| `is_available`                     | Whether actual-card review is available.                                                  |
| `reason`                           | Availability reason.                                                                      |
| `actual_card_played`               | Actual card from input, or `null`.                                                        |
| `recommended_card`                 | Recommended card from analysis.                                                           |
| `actual_expected_point_swing`      | Expected point swing of the actual card, or `null`.                                       |
| `recommended_expected_point_swing` | Expected point swing of the recommended card.                                             |
| `expected_point_swing_difference`  | Recommended swing minus actual swing, or `null`.                                          |
| `decision_quality`                 | `not_available`, `optimal`, `acceptable`, `suboptimal`, or `mistake`.                     |
| `decision_factors`                 | Machine-readable explanation factors.                                                     |
| `decision_explanation`             | Human-readable explanation.                                                               |
| `actual_card_rank`                 | Rank of the actual card by expected point swing, or `null`.                               |
| `recommended_card_rank`            | Rank of the recommended card by expected point swing.                                     |
| `candidate_count`                  | Number of legal candidate cards in the analysis report.                                   |
| `better_card_count`                | Number of legal cards with a higher expected point swing than the actual card, or `null`. |

Decision quality thresholds are based on the missed expected point swing:

| Quality         | Meaning                                                   |
| --------------- | --------------------------------------------------------- |
| `not_available` | No actual card was provided.                              |
| `optimal`       | Actual card has no missed expected point swing.           |
| `acceptable`    | Actual card has only a small missed expected point swing. |
| `suboptimal`    | Actual card has a clearly lower expected point swing.     |
| `mistake`       | Actual card has a much lower expected point swing.        |

## Multi-step result

When a multi-step simulation is requested, the output can include `multi_step_result`.

`multi_step_result` contains the serialized multi-step simulation result, including:

| Field                            | Meaning                                                           |
| -------------------------------- | ----------------------------------------------------------------- |
| `card_selection_policy`          | Card-selection policy used for player decisions.                  |
| `requested_step_count`           | Number of requested simulation steps.                             |
| `steps_simulated`                | Number of steps that were actually simulated.                     |
| `stop_reason`                    | Reason why the simulation stopped.                                |
| `strict_context`                 | Whether strict simulation-context validation was active.          |
| `summary`                        | Multi-step score and context summary.                             |
| `context_summary`                | Summary of simulated opponent-card context.                       |
| `steps`                          | Serialized step-by-step simulation details.                       |
| `final_state`                    | Final serialized game state after the simulated steps.            |
| `opponent_policy_settings`       | Global opponent policy settings used as fallback.                 |
| `left_opponent_policy_settings`  | Left-opponent policy settings passed into multi-step simulation.  |
| `right_opponent_policy_settings` | Right-opponent policy settings passed into multi-step simulation. |

The exact fields depend on whether a multi-step simulation was requested.
