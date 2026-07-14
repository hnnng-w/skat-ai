# Output JSON

This document describes the JSON output produced by `skat-ai`.

## JSON schema

The output JSON schema is available at:

[`schemas/output.schema.json`](../schemas/output.schema.json)

The schema is intended as a documentation and validation aid. It checks the main output structure, important summary fields, and stable optional branch structures such as Multi-Step and policy-comparison results.

Generated outputs for selected examples can be validated against the schema with:

```powershell
python scripts/validate_generated_outputs_schema.py
```

The project check script also runs generated-output schema validation:

```powershell
.\scripts\check.ps1
```

Generated-output schema validation uses the real CLI and output writer. Position
scenarios use deterministic settings such as `--samples 20` and `--seed 42`;
the historical-game scenario uses no position-only overrides. The
validator writes temporary output files, parses the generated JSON, validates it
against `schemas/output.schema.json`.

For the validation-layer overview and schema limitations, see:

[Schema validation documentation](schema_validation.md)

## Output workflows

Position analysis retains the existing top-level result. Complete historical
games instead produce exactly:

```json
{
  "input_file": "examples/historical_grand_normal_completion.json",
  "historical_game_summary": {}
}
```

`historical_game_summary` contains the canonical versioned record, ten derived
tricks, trick and skat points, final 120-point allocation, winner, game result,
game value, overbid, and final settlement. It contains no position,
recommendation, simulation, profile, policy, or list result. See
[Historical games](historical_games.md).

## Position top-level fields

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
| `game_result_summary`            | Raw game result before game-end adjustment.                 |
| `adjusted_game_result_summary`   | Game result after game-end adjustment.                      |
| `final_settlement_summary`       | Single-game settlement summary.                             |
| `performance_rating_summary`     | Performance-rating layer.                                   |
| `list_standings_summary`         | Optional fixed three-player list standings.                 |
| `recommendation`                 | Recommended card and reason.                                |
| `post_game_review_summary`       | Actual-card comparison and post-game review result.         |
| `multi_step_result`              | Optional multi-step simulation result.                      |
| `policy_comparison_result`       | Optional policy-comparison result.                          |
| `information_policy_summary`     | Summary of the active live-vs-post-game information policy. |
| `left_opponent_policy_settings`  | Normalized policy settings for the left opponent.           |
| `right_opponent_policy_settings` | Normalized policy settings for the right opponent.          |

`profile_preset_settings` is emitted in production output and is required by
the output schema.

## Position

`position` echoes normalized position metadata. It includes `declarer_player`, the concrete declarer seat after input normalization.

`position` describes the normalized input position. For opponent-turn inputs it
can legitimately show `next_player` as `left` or `right`. It is not replaced by
any internally prepared Multi-Step state.

For local declarer inputs that omit `declarer_player`, output uses:

```json
"declarer_player": "me"
```

For local defender inputs, `declarer_player` is required in input and is echoed as `left` or `right`.

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

The three settings objects are resolved effective settings. Global presets and global
lead/response policies cascade to both sides, and side-specific settings override only
their side.

Multi-step behavior:

* `right` lead uses `right_opponent_policy_settings.opponent_lead_policy`.
* `left` lead uses `left_opponent_policy_settings.opponent_lead_policy`.
* `right` response after a left lead uses `right_opponent_policy_settings.opponent_response_policy`.
* Candidate trick completion uses the same activated response-policy map as immediate analysis.

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

`matadors` can be explicitly provided in the input. If it is missing or `null`, the engine may infer it from known declarer-card context where possible, including conservative concrete-declarer completed-trick ownership facts when `cards`, ordered `players`, and concrete `declarer_player` are available.

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

Suit and Grand game values are `base_value * game_level`. The supported base
values are Clubs `12`, Spades `11`, Hearts `10`, Diamonds `9`, and Grand `24`.
The game level combines the matador multiplier with supported declaration
modifiers such as Hand, Schneider announced, Schwarz announced, and Ouvert.
Null variants use fixed values: Null `23`, Null Hand `35`, Null Ouvert `46`, and
Null Ouvert Hand `59`.

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
| `impossible_null_settlement` | Calculated replacement summary for the impossible Null branch, otherwise absent; `null` when its selection is missing. |

For a complete impossible Null selection, the dedicated summary is:

```json
"impossible_null_settlement": {
  "replacement_game_type": "clubs",
  "matadors": 1,
  "hand_game": false,
  "base_value": 12,
  "minimum_game_value": 24,
  "required_game_value": 24
}
```

The original Null `game_value`, bid, margin, and overbid status remain visible.
The replacement is not serialized as a changed declaration. Its Hand status
follows the original skat-pickup status; Null ouvert is not transferred.

## Score summary

`score_summary` combines explicit points and completed-trick points.
Explicit side points exclude card points already represented by
`completed_tricks`; completed-trick cards provide their own point contribution.

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

`game_result_summary` describes the raw game result before game-end adjustment.
Suit and Grand results use card points. Normally completed Null results use
completed-trick ownership when ten reliable completed tricks are available:
the declarer wins only with zero declarer tricks, and any declarer trick loses
Null even if that trick is worth zero card points. Incomplete Null games remain
incomplete and are not declared wins merely because the declarer has not yet
taken a trick.

The `winner` field represents the game or contract winner, not the side that
won the most tricks.

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

For `impossible_null_declaration`, it instead records a final defenders' win
without assigning card points. Raw zero-point values remain visible, while raw
and effective Schneider/Schwarz statuses are `not_applicable` because no card
play occurred.

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

The public field `declarer_won_by_card_points` is retained for compatibility.
For Suit and Grand it describes the card-point result. For Null it reflects the
base contract result, even though Null is decided by trick ownership rather than
card points.

For completed non-null suit and grand games with achieved Schneider,
`effective_game_value` includes one additional base-value level while
`game_value` remains the declared/pre-result value.

For completed non-null suit and grand games with achieved Schwarz,
`effective_game_value` includes one additional Schwarz base-value level when a
reliable ten-trick completed history proves that the losing side took no tricks.
Schwarz is not inferred from card points. If Schwarz was announced and reliable
trick ownership proves the announcement failed, `is_loss` is `true` and
`settlement_score` is negative even when `winner` and
`declarer_won_by_card_points` show a declarer card-point win.

This slice does not add a public Schwarz-status field to
`final_settlement_summary`. Schwarz settlement is reflected through existing
fields: `effective_game_value`, `settlement_score`, `is_loss`, and the derived
`performance_rating_summary.game_outcome`.

For supported Suit/Grand overbid cases, `effective_game_value` equals `required_game_value`.

For an impossible Null declaration, `declarer_won_by_card_points` is `null`,
`winner` is `defenders`, and `is_loss` is `true`. Complete replacement metadata
sets `effective_game_value` to its `required_game_value` and scores
`-2 * required_game_value` without requiring points or tricks. Missing metadata
leaves `settlement_score` `null`, sets
`missing_inputs` to `["impossible_null_settlement"]`, and exposes the dedicated
summary as `null`.

For completed Null settlements, the fixed Null variant value is used directly.
A won Null settlement scores `+game_value`; a lost Null settlement scores
`-2 * game_value`. Normally completed Null results are based on reliable
ten-trick ownership, not card-point winner thresholds.

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

| Field                                                  | Meaning                                                                                |
| ------------------------------------------------------ | -------------------------------------------------------------------------------------- |
| `analysis_mode`                                        | Active analysis mode.                                                                  |
| `skat_visibility`                                      | Whether the skat is unknown, declarer-private during play, or known from post-game review. |
| `game_end_reason`                                      | Game-end metadata used for remaining-point assignment.                                 |
| `live_information_enforced`                            | Whether live-information restrictions are active.                                      |
| `known_post_game_skat_allowed`                         | Whether post-game skat visibility is allowed.                                          |
| `known_skat_cards_allowed`                             | Whether known skat cards are allowed in the input under the selected visibility.       |
| `ended_game_allowed`                                   | Whether completed game states are allowed.                                             |
| `unverifiable_completed_trick_winner_metadata_allowed` | Whether winner metadata without full verification context is allowed.                  |

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
| `table_size`                 | Fixed three-player table size used for SkWO-style points.     |
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

Existing single-rated-player list modes do not emit `list_standings_summary`.

## Fixed three-player list standings summary

`list_standings_summary` is emitted only when the input contains
`list_standings_input`.

Example:

```json
"list_standings_summary": {
  "rating_system": "isko_list",
  "basis": "fixed_three_player_game_results",
  "table_size": 3,
  "player_count": 3,
  "game_count": 1,
  "ranking_status": "lot_required",
  "lot_required_player_ids": ["bob", "carol"],
  "applied_lot_order": null,
  "standings": [
    {
      "rank": 1,
      "input_order": 1,
      "player_id": "alice",
      "player_label": "Alice",
      "games_played": 1,
      "declarer_games": 1,
      "defender_games": 0,
      "own_games_won": 1,
      "own_games_lost": 0,
      "defender_games_won": 0,
      "defender_games_lost": 0,
      "other_players_lost_games": 0,
      "player_game_points": 96,
      "own_game_bonus_points": 50,
      "opponent_loss_bonus_points": 0,
      "total_performance_points": 146
    }
  ]
}
```

Summary fields:

| Field          | Meaning                                      |
| -------------- | -------------------------------------------- |
| `rating_system` | Always `isko_list`.                        |
| `basis`        | Always `fixed_three_player_game_results`.    |
| `table_size`   | Fixed table size, always `3`.                |
| `player_count` | Number of standings players, always `3`.     |
| `game_count`   | Number of supplied list games.               |
| `ranking_status` | `final` or `lot_required`.                 |
| `lot_required_player_ids` | IDs in the unresolved tie group, or an empty array. |
| `applied_lot_order` | Applied external lot order, or `null`.  |
| `standings`    | Exactly three ranked player rows.            |

Standing row fields:

| Field                         | Meaning                                                    |
| ----------------------------- | ---------------------------------------------------------- |
| `rank`                        | Final rank or shared competition rank for an unresolved tie. |
| `input_order`                 | One-based input position used only for deterministic serialization. |
| `player_id`                   | Stable player identifier.                                  |
| `player_label`                | Optional display label, or `null`.                         |
| `games_played`                | Total number of supplied games.                            |
| `declarer_games`              | Games where this player was declarer.                      |
| `defender_games`              | `game_count - declarer_games`.                             |
| `own_games_won`               | Own declarer games won.                                    |
| `own_games_lost`              | Own declarer games lost.                                   |
| `defender_games_won`          | Defender games where the declarer lost.                    |
| `defender_games_lost`         | Defender games where the declarer won.                     |
| `other_players_lost_games`    | Same value as `defender_games_won`.                        |
| `player_game_points`          | Sum of settlement scores for own declarer games.           |
| `own_game_bonus_points`       | `own_games_won * 50 + own_games_lost * -50`.               |
| `opponent_loss_bonus_points`  | `other_players_lost_games * 40`.                           |
| `total_performance_points`    | Sum of game points and performance bonuses.                |

SkWO 6.3.1 orders standings by `total_performance_points` descending,
`own_games_won` descending, and `own_games_lost` ascending. A remaining tie is
resolved only by an externally supplied `lot_order`. `player_game_points`,
`opponent_loss_bonus_points`, player IDs, labels, and input order do not decide
rank. The `isko_list` rating-system identifier remains for compatibility.

Without a supplied lot result, tied rows receive standard competition ranks:
`1, 1, 3`, `1, 2, 2`, or `1, 1, 1`. The summary then uses
`ranking_status: "lot_required"`, lists the tied IDs in deterministic input
order, and leaves `applied_lot_order` as `null`. Input order determines only
serialization and does not imply an order within the tie, so these standings
are not final.

When no tie remains, the status is `final`, both lot fields are empty or
`null`, respectively. A valid external lot result also produces `final` status,
unique ranks for only the tied players, and echoes the supplied order in
`applied_lot_order`. The engine never executes a random lot.

This standings output is fixed to three players. It is not four-player support,
full tournament reporting, or an official federation report format.

## Analysis report

`analysis_report` contains one entry per legal card.

Immediate Analysis is local-action only. When the normalized input position does
not have `next_player = "me"`, or when the game has already ended,
`legal_cards` is `[]`, `analysis_report` is `[]`, and `recommendation.card` is
`null`.

Immediate win-rate and point-value fields are local-side based. For a local
declarer, `win_rate` means the declarer side wins the trick. For a local
defender, `win_rate` means either defender wins the trick. `average_points_won`,
`average_points_lost`, and `expected_point_swing` use the same local-side
perspective.

For Null games, candidate ordering and `is_recommended` use the Null contract
objective instead of card-point swing. A local Null declarer prefers avoiding
declarer-won evaluated tricks. A local Null defender prefers making the concrete
declarer win an evaluated trick. The point fields above remain card-point
metrics and are not redefined as contract utility.

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

For opponent-turn inputs, Immediate Analysis does not create a local card
recommendation. The unavailable shape is:

```json
"recommendation": {
  "card": null,
  "reason": "Immediate analysis is unavailable because the local player is not next."
}
```

## Post-game review summary

`post_game_review_summary` compares the actual played card with the recommended card.
It requires an available local Immediate Analysis report.

If `actual_card_played` was not provided, the summary is still present but marked as unavailable.
If Immediate Analysis is unavailable, the summary is also unavailable and uses
`reason: "immediate_analysis_unavailable"`.

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

For Null games, post-game review uses the same Null contract objective as the
recommendation for ranks, better-card counts, and decision quality. The public
point fields keep their card-point meanings. Null-specific decision factors may
include `no_missed_null_objective`,
`lower_null_objective_than_recommendation`, `small_null_objective_gap`,
`medium_null_objective_gap`, and `large_null_objective_gap`.

Representative examples:

* `examples/grand_post_game_mistake_actual_card.json` shows a clear missed recommendation with a large expected-point-swing gap.
* `examples/grand_post_game_acceptable_actual_card.json` shows a small missed expected-point-swing gap classified as `acceptable`.
* `examples/null_post_game_objective_actual_card.json` shows a Null review where the actual card differs from the recommendation but has no missed Null contract-objective utility.
* `examples/spades_post_game_defender_actual_card.json` shows local defender-perspective review with a concrete declarer seat.

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

Nested `steps[].prepared_state` is the state after any supported opponent-turn
preparation and before the local candidate card is simulated. This separates the
original top-level `position` from the internally advanced local-action state.

Nested `final_state` follows the same reusable-state invariant as input
positions: `declarer_points` and `defender_points` contain only explicit points
not already represented by `completed_tricks`. Points from simulated completed
tricks are contributed by the completed-trick cards and are reflected in the
summary totals.

Nested `steps[].detailed_result` uses explicit ownership fields:

| Field                  | Meaning                                                            |
| ---------------------- | ------------------------------------------------------------------ |
| `did_win`              | Whether the local player's side won the completed trick.           |
| `local_side_won`       | Same local-side ownership value as `did_win`.                      |
| `candidate_card_won`   | Whether the candidate card itself won the completed trick.         |
| `completed_trick`      | Completed trick entry with winner side and, when known, winner player. |

Nested `summary.score_summary` includes both declarer-perspective and
local-perspective swing fields:

| Field                 | Meaning                                                            |
| --------------------- | ------------------------------------------------------------------ |
| `final_point_swing`   | `declarer_points_gained - defender_points_gained`.                 |
| `local_point_swing`   | Local-side swing. This matches `final_point_swing` for a local declarer and is `defender_points_gained - declarer_points_gained` for a local defender. |

The output schema defines the stable `multi_step_result` structure, including
serialized steps, `steps[].prepared_state`, candidate detailed results,
`final_state`, context summaries, stop reasons such as
`unsupported_turn_phase`, and both `final_point_swing` and
`local_point_swing`.

## Policy comparison result

When policy comparison is requested, `policy_comparison_result.policy_results`
contains one row per compared card-selection policy.

Each row includes `final_point_swing` for the declarer-perspective swing and
`local_point_swing` for the local player's side. Policy results and
`recommended_policy` are ranked by `local_point_swing`, then by the documented
tie-breakers.

The output schema defines the stable `policy_comparison_result` structure,
including requested settings, compared policies, per-policy result rows,
context summaries, and `recommended_policy`.
