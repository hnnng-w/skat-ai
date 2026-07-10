# Examples

This document describes the example input files in `examples/`.

The repository-root quick-start command `python main.py` reads the root
`input_position.json` fixture. Files under `examples/` are selected explicitly
with `--input`.

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

## Workflow walkthroughs

These commands cover the main user-facing CLI workflows. They reuse existing repository fixtures and can be run from the repository root.

Show CLI help and command examples:

```powershell
python main.py --help
```

Run the default live recommendation using the root `input_position.json` fixture:

```powershell
python main.py
```

Run live recommendation with an explicit input file:

```powershell
python main.py --input examples/grand_second_position.json
```

Write structured JSON output:

```powershell
python main.py --input examples/grand_second_position.json --output outputs/result.json
```

Write JSON output without successful human-readable stdout output:

```powershell
python main.py --input examples/grand_second_position.json --output outputs/result.json --quiet
```

The `--quiet` flag suppresses successful human-readable stdout output, including the output-file confirmation. Expected errors still go to `stderr`.

Prepare an opponent-turn position with Multi-Step until the local player acts:

```powershell
python main.py --input examples/grand_left_to_act_live.json --multi-step 1 --card-policy highest_point
```

Run local live Multi-Step analysis:

```powershell
python main.py --input examples/grand_second_position.json --multi-step 2
```

Compare local card-selection policies:

```powershell
python main.py --input examples/grand_second_position.json --multi-step 1 --compare-policies
```

Print only policy-comparison output in the human-readable CLI view:

```powershell
python main.py --input examples/grand_second_position.json --multi-step 1 --compare-policies --comparison-only
```

Run Multi-Step with side-specific opponent lead policies:

```powershell
python main.py --input examples/grand_left_right_opponent_policies.json --multi-step 2 --left-opponent-lead-policy highest_point --right-opponent-lead-policy basic_defender_lead
```

Run post-game review with actual-card comparison:

```powershell
python main.py --input examples/spades_post_game_actual_card_played.json
```

Validate example inputs and generated output workflows:

```powershell
python scripts/validate_examples_schema.py
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

Live decision examples must not include post-game-only information such as `known_post_game` Skat visibility or completed game-end reasons. They may include `known_to_declarer` Skat cards when those cards are declarer-private live information.

| File                                       | Purpose                                                                                                                      |
| ------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------- |
| `grand_second_position.json`               | Grand game, local player acts second. Also demonstrates automatic matador inference from known declarer-card context when possible. |
| `grand_declarer_known_to_declarer_live.json` | Grand live declarer position where the local declarer has declarer-private Skat visibility.                                 |
| `grand_third_position.json`                | Grand game, local player acts third.                                                                                         |
| `grand_leading.json`                       | Grand game where local player leads the trick.                                                                               |
| `grand_late_game_history_heavy_live.json`  | Late-game live defender position with zero opponent hand sizes, nine ordered completed tricks, and completed-trick matador inference. |
| `grand_left_right_opponent_policies.json`  | Grand game with distinct global, left-opponent, and right-opponent policy settings.                                           |
| `hearts_leading.json`                      | Suit game example.                                                                                                           |
| `null_second_position.json`                | Null game example.                                                                                                           |

## Midgame examples

| File                                      | Purpose                                                                                       |
| ----------------------------------------- | --------------------------------------------------------------------------------------------- |
| `grand_midgame_declarer_ahead.json`       | Midgame position where declarer is ahead by known points.                                     |
| `grand_midgame_defenders_ahead.json`      | Midgame position where defenders are ahead by known points.                                   |
| `grand_midgame_profile_preset_live.json`  | Live midgame position with strategic metadata, player profiles, and profile preset settings.  |
| `spades_midgame_defender_rearhand_live.json` | Live midgame defender rearhand position with explicit declarer seat, completed-trick metadata, and unknown skat. |

## Opponent-turn multi-step examples

These examples represent live positions where the local player is not the next
player to act. They are intended for the supported multi-step workflow, where
opponent action is simulated until the local player reaches a decision point.
Their Immediate Analysis output is intentionally unavailable: `legal_cards` and
`analysis_report` are empty, and `recommendation.card` is `null`.

| File                            | Purpose                                                                                     |
| ------------------------------- | ------------------------------------------------------------------------------------------- |
| `grand_left_to_act_live.json`   | `next_player: "left"`; multi-step simulates a left lead, right response, then local action. |
| `grand_right_to_act_live.json`  | `next_player: "right"`; multi-step simulates a right lead, then local action.               |

Run the left-to-act example:

```powershell
python main.py --input examples/grand_left_to_act_live.json --multi-step 1 --card-policy highest_point
```

Run the right-to-act example:

```powershell
python main.py --input examples/grand_right_to_act_live.json --multi-step 1 --card-policy highest_point
```

Both files are input-schema validated with all examples. They are covered by
focused behavioral assertions in `tests/test_examples.py` because their primary
supported workflow is multi-step opponent-turn preparation. Selected
opponent-turn generated outputs are also covered by generated-output schema
validation.

Multi-step also supports a one-card partial trick where `left` has already led
and `right` is next. In that phase the existing lead card is preserved and only
right's response is simulated before the local third-hand decision.

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
| `grand_second_position_with_metadata.json` | Post-game metadata example with known post-game skat visibility, profile presets, and player profiles.                       |
| `grand_post_game_known_skat.json`          | Post-game review with known skat and completed tricks.                                                                       |
| `grand_post_game_mistake_actual_card.json` | Post-game review where the actual card is ranked below the recommendation and gap details are populated.                     |
| `spades_post_game_actual_card_played.json` | Post-game review with `actual_card_played`, decision quality, decision factors, explanation, and recommendation gap details. |
| `grand_complete_declarer_win.json`         | Complete game where declarer wins. Also demonstrates `bid_value` and partial ISkO performance-rating metadata.               |
| `grand_complete_declarer_loss.json`        | Complete game where declarer loses. Also demonstrates fixed three-player ISkO counterparty points.                           |
| `grand_list_performance_input.json`        | Complete game with partial ISkO single-game rating plus already aggregated list performance input and output.                 |
| `grand_list_analysis_results.json`         | Complete game with partial ISkO single-game rating plus list performance aggregated from local analysis-result objects.       |

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

## Performance rating examples

`grand_list_performance_input.json` demonstrates `performance_rating_system: "isko_list"` with optional already aggregated list or series totals:

```json
"list_performance_input": {
  "player_game_points": 120,
  "own_games_won": 3,
  "own_games_lost": 1,
  "other_players_lost_games": 2
}
```

Expected list performance calculation for the fixed three-player table:

* `own_game_bonus_points`: `3 * 50 + 1 * -50 = 100`
* `opponent_loss_bonus_points`: `2 * 40 = 80`
* `total_performance_points`: `120 + 100 + 80 = 300`
* `table_size`: `3` in the emitted `list_performance_summary`

The example still emits the normal single-game `performance_rating_summary`; `list_performance_summary` is additional and does not change it.

`grand_list_analysis_results.json` demonstrates `performance_rating_system: "isko_list"` with local analysis-result objects for one consistently represented local player:

```json
"list_analysis_results": [
  {
    "position": {
      "player_role": "declarer"
    },
    "final_settlement_summary": {
      "is_complete": true,
      "is_loss": false,
      "settlement_score": 96
    }
  }
]
```

The example file includes one local declarer win with score `96`, one local declarer loss with score `-72`, and one local defender game where the declarer loses with score `-120`.

Expected local analysis-result list calculation for the example:

* `player_game_points`: `96 + (-72) = 24`
* `own_game_bonus_points`: `1 * 50 + 1 * (-50) = 0`
* `opponent_loss_bonus_points`: `1 * 40 = 40`
* `total_performance_points`: `24 + 0 + 40 = 64`
* `basis`: `local_analysis_results`
* `table_size`: `3` in the emitted `list_performance_summary`

The top-level completed game still emits its normal single-game `performance_rating_summary`; the local analysis-result aggregation only adds `list_performance_summary`.

## Matador inference examples

Automatic matador inference is demonstrated by examples where `matadors` is missing or `null`, but known declarer-card context is sufficient.

The engine currently infers matadors from known declarer-card context in:

* `hand`
* `skat`, when available and allowed by the analysis mode
* `completed_tricks`, but only from conservative concrete-declarer ownership facts with both `cards`, ordered `players`, and concrete `declarer_player`

If an explicit `matadors` value is provided, the explicit value is preserved.

`grand_late_game_history_heavy_live.json` omits explicit `matadors` and uses ordered completed-trick ownership from a concrete defender perspective to infer the Grand game value late in the game.

Null games do not use matadors.

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

Global policy fields remain backward-compatible and cascade to both opponents. Side-specific fields override only their side.

Multi-step behavior:

* if `right` leads, `right_opponent_lead_policy` is used
* if `left` leads, `left_opponent_lead_policy` is used
* if `left` leads and `right` responds, `right_opponent_response_policy` is used
* candidate trick completion uses activated side response policies when an explicit response source exists

Run a multi-step simulation with separate left/right opponent policies:

```powershell
python main.py --input examples/grand_left_right_opponent_policies.json --multi-step 2
```

Override side-specific opponent policies from the CLI:

```powershell
python main.py --input examples/grand_left_right_opponent_policies.json --multi-step 2 --left-opponent-lead-policy highest_point --right-opponent-response-policy basic_defender_response
```

## Notes

The examples are also used as regression fixtures in `tests/test_examples.py`.

When adding new examples:

* keep card notation valid
* avoid duplicate known cards
* keep point totals within 120
* set `analysis_mode` consistently with the example type
* keep live decision examples free of post-game-only information
* include `declarer_player` as `left` or `right` when `player_role` is `defender`
* use `post_game_review` for completed games, claim/concession scenarios, known post-game skat, and `actual_card_played`
* set `game_end_reason` consistently with known card points
* add explicit `players` to completed tricks when winner metadata must be verifiable
* prefer `completed_tricks` over `played_cards`
* use `performance_rating_system: "isko_list"` only when partial ISkO rating output should be demonstrated
* omit `matadors` only when automatic inference from known declarer-card context is intended
* prefer either top-level declaration fields or nested `game_declaration`; mixing is supported, with top-level fields taking precedence
* use only documented declaration fields inside nested `game_declaration`; unrelated nested metadata is not part of the supported public input contract
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
* `list_performance_summary`, if a list performance input mode is provided
* `recommendation`
* `post_game_review_summary`
* `multi_step_result`, if multi-step simulation is requested
* `policy_comparison_result`, if policy comparison is requested

For detailed output field descriptions, see:

* [Output JSON documentation](output_json.md)
