# Examples

This document describes the example input files in `examples/`.

The examples are used for:

* manual testing
* regression tests
* input schema validation
* generated-output schema validation
* documentation of supported workflows

## Example validation

All example JSON files should remain valid.

Run the full project check:

```powershell
.\scripts\check.ps1
```

The check script validates:

* Ruff checks
* input JSON schema validation
* generated output JSON schema validation
* pytest regression tests

Run input schema validation directly:

```powershell
python scripts/validate_examples_schema.py
```

Run generated-output schema validation directly:

```powershell
python scripts/validate_generated_outputs_schema.py
```

## Live decision examples

These examples represent ongoing positions where the tool recommends a card.

Typical metadata:

```json
{
  "analysis_mode": "live_decision",
  "skat_visibility": "unknown",
  "game_end_reason": "not_ended"
}
```

Live decision examples must not include post-game-only information such as known skat cards or completed game-end reasons.

| File                                       | Purpose                                                                                                                      |
| ------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------- |
| `grand_second_position.json`               | Grand game, local player acts second. Also demonstrates automatic matador inference from known declarer cards when possible. |
| `grand_second_position_with_metadata.json` | Grand second-position example with strategic metadata.                                                                       |
| `grand_third_position.json`                | Grand game, local player acts third.                                                                                         |
| `grand_leading.json`                       | Grand game where local player leads the trick.                                                                               |
| `grand_left_right_opponent_policies.json`  | Grand game with distinct global, left-opponent, and right-opponent policy settings.                                           |
| `hearts_leading.json`                      | Suit game example.                                                                                                           |
| `null_second_position.json`                | Null game example.                                                                                                           |

## Midgame examples

| File                                      | Purpose                                                                                       |
| ----------------------------------------- | --------------------------------------------------------------------------------------------- |
| `grand_midgame_declarer_ahead.json`       | Midgame position where declarer is ahead by known points.                                     |
| `grand_midgame_defenders_ahead.json`      | Midgame position where defenders are ahead by known points.                                   |
| `grand_midgame_profile_preset_live.json`  | Live midgame position with strategic metadata, player profiles, and profile preset settings.  |
| `spades_midgame_defender_rearhand_live.json` | Live midgame defender rearhand position with completed-trick metadata and unknown skat.        |

## Post-game review examples

These examples represent completed or retrospectively analyzed games.

Typical metadata:

```json
{
  "analysis_mode": "post_game_review",
  "skat_visibility": "known_post_game",
  "game_end_reason": "normal_completion"
}
```

Post-game review examples may include known skat cards and completed game information.

| File                                       | Purpose                                                                                                                      |
| ------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------- |
| `grand_post_game_known_skat.json`          | Post-game review with known skat and completed tricks.                                                                       |
| `grand_post_game_mistake_actual_card.json` | Post-game review where the actual card is ranked below the recommendation and gap details are populated.                     |
| `spades_post_game_actual_card_played.json` | Post-game review with `actual_card_played`, decision quality, decision factors, explanation, and recommendation gap details. |
| `grand_complete_declarer_win.json`         | Complete game where declarer wins. Also demonstrates `bid_value` and partial ISkO performance-rating metadata.               |
| `grand_complete_declarer_loss.json`        | Complete game where declarer loses. Also demonstrates fixed three-player ISkO counterparty points.                           |

Run a post-game review example with actual-card comparison:

```powershell
python main.py --input examples/spades_post_game_actual_card_played.json
```

Run a post-game review example with a missed recommendation:

```powershell
python main.py --input examples/grand_post_game_mistake_actual_card.json
```

The output includes:

* `post_game_review_summary.is_available`
* `actual_card_played`
* `recommended_card`
* `actual_expected_point_swing`
* `recommended_expected_point_swing`
* `expected_point_swing_difference`
* `decision_quality`
* `decision_factors`
* `decision_explanation`
* `actual_card_rank`
* `recommended_card_rank`
* `candidate_count`
* `better_card_count`

## Claim and concession examples

These examples test game-end handling where remaining card points are assigned without normal trick completion.

Supported game-end reasons include:

* `declarer_claimed_remaining_tricks`
* `declarer_conceded_remaining_tricks`
* `defenders_conceded_remaining_tricks`

These examples should use:

```json
{
  "analysis_mode": "post_game_review"
}
```

because ended game reasons are post-game review information.

| File                                             | Purpose                             |
| ------------------------------------------------ | ----------------------------------- |
| `grand_claimed_remaining_tricks.json`            | Declarer claims remaining tricks.   |
| `grand_declarer_conceded_remaining_tricks.json`  | Declarer concedes remaining tricks. |
| `grand_defenders_conceded_remaining_tricks.json` | Defenders concede remaining tricks. |

## Overbid examples

| File                                          | Purpose                                                                        |
| --------------------------------------------- | ------------------------------------------------------------------------------ |
| `grand_overbid_declarer_card_points_win.json` | Declarer wins by card points but loses settlement because the game is overbid. |

## Matador inference examples

Automatic matador inference is demonstrated by examples where `matadors` is missing or `null`, but known declarer-card context is sufficient.

The engine currently infers matadors from known declarer cards in:

* `hand`
* `skat`, when available and allowed by the analysis mode

If an explicit `matadors` value is provided, the explicit value is preserved.

Null games do not use matadors.

## Example commands

Run a basic analysis:

```powershell
python main.py --input examples/grand_second_position.json --output outputs/result.json
```

Run a post-game review example:

```powershell
python main.py --input examples/grand_post_game_known_skat.json --output outputs/post_game_review.json
```

Run a post-game review example with actual-card comparison:

```powershell
python main.py --input examples/spades_post_game_actual_card_played.json --output outputs/post_game_actual_card.json
```

Run an overbid example:

```powershell
python main.py --input examples/grand_overbid_declarer_card_points_win.json --output outputs/overbid_test.json
```

Run a claim example:

```powershell
python main.py --input examples/grand_claimed_remaining_tricks.json --output outputs/claim_test.json
```

Run a declarer-concession example:

```powershell
python main.py --input examples/grand_declarer_conceded_remaining_tricks.json --output outputs/declarer_concession_test.json
```

Run a defenders-concession example:

```powershell
python main.py --input examples/grand_defenders_conceded_remaining_tricks.json --output outputs/defenders_concession_test.json
```

## Multi-step simulation examples

Run a two-step simulation:

```powershell
python main.py --input examples/grand_second_position.json --multi-step 2
```

Run a two-step simulation with explicit opponent policies:

```powershell
python main.py --input examples/grand_second_position.json --multi-step 2 --opponent-lead-policy highest_point --opponent-response-policy basic_trick_play
```

## Policy comparison examples

Run a policy comparison:

```powershell
python main.py --input examples/grand_second_position.json --compare-policies
```

## Left/right opponent policy examples

The project supports separate left/right opponent policy settings.

Input fields:

```json
{
  "opponent_lead_policy": "lowest_point",
  "opponent_response_policy": "lowest_point",
  "left_opponent_lead_policy": "highest_point",
  "left_opponent_response_policy": "basic_trick_play",
  "right_opponent_lead_policy": "basic_defender_lead",
  "right_opponent_response_policy": "basic_defender_response"
}
```

Global policy fields remain backward-compatible and are used as fallback values.

Current multi-step behavior:

* if `right` leads, `right_opponent_lead_policy` is used
* if `left` leads, `left_opponent_lead_policy` is used
* if `left` leads and `right` responds, `right_opponent_response_policy` is used

Run a multi-step simulation with separate left/right opponent policies:

```powershell
python main.py --input examples/grand_left_right_opponent_policies.json --multi-step 2
```

## Notes

The examples are also used as regression fixtures in `tests/test_examples.py`.

When adding new examples:

* keep card notation valid
* avoid duplicate known cards
* keep point totals within 120
* set `analysis_mode` consistently with the example type
* keep live decision examples free of post-game-only information
* use `post_game_review` for completed games, claim/concession scenarios, known post-game skat, and `actual_card_played`
* set `game_end_reason` consistently with known card points
* add explicit `players` to completed tricks when winner metadata must be verifiable
* prefer `completed_tricks` over `played_cards`
* use `performance_rating_system: "isko_list"` only when partial ISkO rating output should be demonstrated
* omit `matadors` only when automatic inference from known declarer cards is intended
* run `.\scripts\check.ps1` before committing

## Expected output behavior

Generated outputs may include:

* `position`
* `settings`
* `opponent_policy_settings`
* `left_opponent_policy_settings`
* `right_opponent_policy_settings`
* `analysis_metadata`
* `information_policy_summary`
* `game_declaration`
* `game_value_summary`
* `overbid_summary`
* `score_summary`
* `game_result_summary`
* `adjusted_game_result_summary`
* `final_settlement_summary`
* `performance_rating_summary`
* `recommendation`
* `post_game_review_summary`
* `multi_step_result`, if multi-step simulation is requested
* `policy_comparison_result`, if policy comparison is requested

For detailed output field descriptions, see:

* [Output JSON documentation](output_json.md)
