# Skat AI

![Check](https://github.com/hnnng-w/skat-ai/actions/workflows/check.yml/badge.svg)

Skat AI Analysis Tool is a Python-based analysis engine for Skat positions.

It evaluates legal card choices, estimates immediate trick outcomes with simulation, tracks game state, and can run basic multi-step projections. The project currently focuses on rule-based and probability-based analysis rather than machine learning.

The long-term goal is to support more advanced strategic analysis, including opponent tendencies and post-game review.

## Current capabilities

The tool currently supports:

- JSON-based position analysis
- Legal card detection
- Immediate trick simulation
- Expected point swing calculation
- Card recommendation based on expected value
- Score summaries from completed tricks
- Multi-step simulation
- Opponent lead and response simulation
- Simulation context tracking
- Duplicate-card warnings in simulation context
- Strict context mode
- Policy comparison across card-selection strategies
- JSON output for analysis results
- Optional strategic metadata and player profile fields
- Game declaration metadata
- Game value summary
- Card-point result summary
- Final settlement summary
- Game-end handling for claim and concession
- Adjusted game result summary
- Completed-trick structure and rule validation
- Example regression tests
- Opponent policy presets
- Optional profile-based opponent policy presets

## Requirements

- Python 3.11 or newer
- pytest for running tests

## Installation

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install -e ".[dev]"
```

Run checks:

```powershell
.\scripts\check.ps1
```

This installs the local package plus development tools such as `pytest` and `ruff`.

## Running the tool

Run the default analysis:

```powershell
python main.py
```

Run analysis with a specific input file:

```powershell
python main.py --input examples/grand_second_position.json
```

Override simulation settings:

```powershell
python main.py --input examples/grand_second_position.json --samples 100 --seed 42
```

Write output to JSON:

```powershell
python main.py --input examples/grand_second_position.json --output outputs/result.json
```

Run a complete settlement example:

```powershell
python main.py --input examples/grand_complete_declarer_win.json --output outputs/complete_declarer_win.json
```

Run a complete declarer-loss example:

```powershell
python main.py --input examples/grand_complete_declarer_loss.json --output outputs/complete_declarer_loss.json
```

Run an overbid example where the declarer wins card points but loses settlement:

```powershell
python main.py --input examples/grand_overbid_declarer_card_points_win.json --output outputs/overbid_test.json
```

## Example positions

The project includes example JSON input files in the `examples/` folder.

```text
examples/
  grand_claimed_remaining_tricks.json
  grand_complete_declarer_loss.json
  grand_complete_declarer_win.json
  grand_declarer_conceded_remaining_tricks.json
  grand_defenders_conceded_remaining_tricks.json
  grand_leading.json
  grand_midgame_declarer_ahead.json
  grand_midgame_defenders_ahead.json
  grand_post_game_known_skat.json
  grand_second_position.json
  grand_second_position_with_metadata.json
  grand_third_position.json
  hearts_leading.json
  null_second_position.json
```

Run an example:

```powershell
python main.py --input examples/grand_leading.json
```

Run a mid-game example:

```powershell
python main.py --input examples/grand_midgame_declarer_ahead.json
```

Run a complete settlement example:

```powershell
python main.py --input examples/grand_complete_declarer_win.json --output outputs/complete_declarer_win.json
```

Run a post-game review example with known skat cards:

```powershell
python main.py --input examples/grand_post_game_known_skat.json --output outputs/post_game_known_skat.json
```

The examples are used as regression tests. They are expected to remain valid and to produce stable key output values such as score summaries, game values, settlement status, and metadata output.

Run a declarer-claim example:

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

## Input JSON format

A basic input file describes one Skat position:

```json
{
  "game_type": "grand",
  "player_role": "declarer",
  "player_position": "middlehand",
  "trick_leader": "left",
  "hand": ["SA", "S10", "S9", "H10", "D7"],
  "current_trick": ["S7"],
  "played_cards": [],
  "skat": [],
  "completed_tricks": [],
  "declarer_points": 0,
  "defender_points": 0,
  "next_player": "me",
  "left_hand_size": 5,
  "right_hand_size": 5,
  "sample_count": 1000,
  "random_seed": 42,
  "use_basic_opponent_strategy": true,
  "hand_game": false,
  "ouvert": false,
  "schneider_announced": false,
  "schwarz_announced": false,
  "matadors": null
}
```

Important fields:

- `game_type`: currently supports game types such as `grand`, suit games, and null games according to the implemented rule logic.
- `player_role`: whether the player is `declarer` or `defender`.
- `player_position`: position of the player in the current trick.
- `trick_leader`: player who led the current trick.
- `hand`: current player hand.
- `current_trick`: cards already played in the current trick.
- `played_cards`: known played cards outside completed tricks.
- `skat`: skat cards, if known.
- `completed_tricks`: previously completed tricks.
- `declarer_points` / `defender_points`: explicit current score values.
- `next_player`: next player to act, if known.
- `left_hand_size` / `right_hand_size`: assumed remaining opponent hand sizes.
- `sample_count`: number of simulation samples.
- `random_seed`: optional seed for reproducible simulations.
- `use_basic_opponent_strategy`: whether basic opponent strategy is used during simulation.
- `game_end_reason`: describes whether the game is still running, completed normally, or ended early through claim/concession.

### Performance rating system

Input files may optionally include `performance_rating_system`.

```json
{
  "performance_rating_system": "isko_list"
}
```

Supported values:

| Value | Meaning |
|---|---|
| `placeholder` | Generic placeholder rating system. |
| `isko_list` | ISkO-style list/performance rating placeholder. Known, but not implemented yet. |

If omitted, `performance_rating_summary.rating_system` is `null`.

Unknown values are rejected during input validation.

For partial ISkO-style single-game rating, use:

```json
"performance_rating_system": "isko_list"
```
The current implementation assumes a fixed three-player table. No table-size input field is required.

## Optional analysis metadata

Input files may include optional metadata. Some fields are stored for reporting and future logic. Profile-based presets can optionally influence opponent policy selection when `use_profile_presets` is enabled.

```json
{
  "analysis_mode": "post_game_review",
  "skat_visibility": "known_post_game",
  "game_end_reason": "normal_completion",
  "use_profile_presets": true,
  "opponent_policy_preset": "cautious_defender",
  "opponent_lead_policy": "basic_defender_lead",
  "opponent_response_policy": "basic_defender_response",
  "left_player_profile": {
    "games_played": 1240,
    "solo_games_played": 380,
    "defender_games_played": 860,
    "solo_rate": 0.31,
    "solo_win_rate": 0.66,
    "hand_game_rate": 0.08,
    "suit_game_rate": 0.46,
    "grand_rate": 0.22,
    "null_game_rate": 0.04,
    "defender_win_rate": 0.54
  },
  "right_player_profile": {
    "games_played": 520,
    "solo_games_played": 160,
    "defender_games_played": 360,
    "solo_rate": 0.28,
    "solo_win_rate": 0.59,
    "hand_game_rate": 0.05,
    "suit_game_rate": 0.51,
    "grand_rate": 0.18,
    "null_game_rate": 0.06,
    "defender_win_rate": 0.49
  }
}
```
`opponent_policy_preset`, `opponent_lead_policy`, `opponent_response_policy`, and `use_profile_presets` are optional.

If both a preset and explicit lead/response policies are provided, the explicit lead/response policies win.
If use_profile_presets true, player profiles are used to derive opponent policy presets. Explicit opponent policy fields and CLI lead/response overrides still take precedence.

Supported `analysis_mode` values:

- `live_decision`
- `post_game_review`

Supported `skat_visibility` values:

- `unknown`
- `known_to_declarer`
- `known_post_game`

Supported `game_end_reason` values:

- `not_ended`
- `normal_completion`
- `declarer_claimed_remaining_tricks`
- `declarer_conceded_remaining_tricks`
- `defenders_conceded_remaining_tricks`

`game_end_reason` must be consistent with the current card-point state:

- use `not_ended` while card points are still remaining
- use `normal_completion` only when all 120 card points are assigned
- use claim/concession reasons only when card points are still remaining

Optional game declaration fields:

hand_game
ouvert
schneider_announced
schwarz_announced
matadors

The tool also calculates a basic game_value_summary from the declaration metadata.

For suit and grand games:

game value = base value × game level

Current base values:
- clubs: 12
- spades: 11
- hearts: 10
- diamonds: 9
- grand: 24

Current game level:
- matadors + 1
- plus hand_game
- plus schneider_announced
- plus schwarz_announced
- plus ouvert

If `matadors` is `null`, the game value remains incomplete for suit and grand games. This prevents the engine from guessing a game value when the matador count is unknown.

Null games use fixed values:
- null: 23
- null hand: 35
- null ouvert: 46
- null hand ouvert: 59

## Multi-step simulation

Run a multi-step simulation:

```powershell
python main.py --input examples/grand_second_position.json --multi-step 2
```

Use a specific card-selection policy:

```powershell
python main.py --input examples/grand_second_position.json --multi-step 2 --card-policy lowest_point
```

Use expected-value card selection:

```powershell
python main.py --input examples/grand_second_position.json --multi-step 2 --card-policy highest_expected_value --expected-value-samples 20
```

Run strict context mode:

```powershell
python main.py --input examples/grand_second_position.json --multi-step 3 --strict-context
```

Strict context mode fails if duplicate simulated opponent cards are detected during a multi-step run.

Opponent lead and response policies can be configured:

```powershell
python main.py --input examples/grand_second_position.json --multi-step 2 --opponent-lead-policy highest_point --opponent-response-policy basic_trick_play
```

Supported opponent policies:

lowest_point
highest_point
random_legal
basic_trick_play
basic_defender_response
basic_defender_lead

basic_defender_response tries to add points when the defenders partner is currently winning the trick. Otherwise it falls back to basic trick-play behavior.
basic_defender_lead prefers low-point non-trump cards when opening a trick.

Opponent policy presets are available:

simple_lowest:
- lead: lowest_point
- response: lowest_point

cautious_defender:
- lead: basic_defender_lead
- response: basic_defender_response

aggressive_points:
- lead: highest_point
- response: highest_point

random:
- lead: random_legal
- response: random_legal

python main.py --input examples/grand_second_position.json --multi-step 2 --opponent-policy-preset cautious_defender
Explicit --opponent-lead-policy and --opponent-response-policy override the preset values.

Player profiles can now be translated into recommended opponent policy presets for informational output.

This does not yet automatically affect the simulation.

High-confidence defensive profile:
- recommended preset: cautious_defender

Aggressive profile:
- recommended preset: aggressive_points

Unknown or low-confidence profile:
- recommended preset: simple_lowest

Profile-based opponent presets can be enabled explicitly:

python main.py --input examples/grand_second_position_with_metadata.json --multi-step 2 --use-profile-presets

When enabled, the tool derives an opponent policy preset from the left and right player profiles.

This is optional. By default, player profiles are stored and reported but do not affect simulation behavior.

## Policy comparison

Compare all available card-selection policies:

```powershell
python main.py --input examples/grand_second_position.json --multi-step 2 --compare-policies --expected-value-samples 20
```

Print only the policy comparison without individual multi-step details:

```powershell
python main.py --input examples/grand_second_position.json --multi-step 2 --compare-policies --comparison-only --expected-value-samples 20
```

Write policy comparison to JSON:

```powershell
python main.py --input examples/grand_second_position.json --multi-step 2 --compare-policies --comparison-only --expected-value-samples 20 --output outputs/policy_comparison.json
```

Policy comparison results are sorted by:

1. Higher final point swing
2. Higher declarer points gained
3. Lower defender points gained
4. Higher number of simulated steps
5. Policy name alphabetically

The comparison also includes a `recommended_policy`.

## Opponent modeling

Opponent behavior can be configured through opponent card policies, policy presets, and optional profile-based presets.

This is still rule-based. The tool does not yet train or use a machine-learning model.

### Opponent policy priority

Opponent policies are resolved in this order:

1. Default values: `lowest_point` / `lowest_point`
2. Input JSON `opponent_policy_preset`
3. Input JSON `use_profile_presets`
4. Input JSON explicit `opponent_lead_policy` / `opponent_response_policy`
5. CLI `--opponent-policy-preset`
6. CLI `--use-profile-presets`
7. CLI explicit `--opponent-lead-policy` / `--opponent-response-policy`

Explicit lead and response policies always have the highest priority.

### Opponent card policies

Supported opponent policies:

- `lowest_point`
- `highest_point`
- `random_legal`
- `basic_trick_play`
- `basic_defender_response`
- `basic_defender_lead`

Policy meanings:

- `lowest_point`: choose the legal card with the lowest point value.
- `highest_point`: choose the legal card with the highest point value.
- `random_legal`: choose a random legal card.
- `basic_trick_play`: win with the lowest-point winning card if possible; otherwise play the lowest-point legal card.
- `basic_defender_response`: if the defender's partner is currently winning the trick, add points with the highest-point legal card; otherwise fall back to `basic_trick_play`.
- `basic_defender_lead`: when leading a trick, prefer low-point non-trump cards; otherwise fall back to the lowest-point card.

Configure lead and response policies directly:

```powershell
python main.py --input examples/grand_second_position.json --multi-step 2 --opponent-lead-policy basic_defender_lead --opponent-response-policy basic_defender_response
```

### Opponent policy presets

Opponent policy presets combine a lead policy and a response policy.

Supported presets:

| Preset | Lead policy | Response policy |
|---|---|---|
| `simple_lowest` | `lowest_point` | `lowest_point` |
| `cautious_defender` | `basic_defender_lead` | `basic_defender_response` |
| `aggressive_points` | `highest_point` | `highest_point` |
| `random` | `random_legal` | `random_legal` |

Use a preset:

```powershell
python main.py --input examples/grand_second_position.json --multi-step 2 --opponent-policy-preset cautious_defender
```

Explicit lead or response policies override preset values:

```powershell
python main.py --input examples/grand_second_position.json --multi-step 2 --opponent-policy-preset cautious_defender --opponent-response-policy highest_point
```

### Profile-based presets

Player profiles can be used to derive an opponent policy preset.

This is optional. By default, player profiles are stored and reported but do not affect simulation behavior.

Enable profile-based presets:

```powershell
python main.py --input examples/grand_second_position_with_metadata.json --multi-step 2 --use-profile-presets
```

Profile-based preset selection currently uses simple rule-based heuristics:

- unknown or low-confidence profiles → `simple_lowest`
- aggressive profiles → `aggressive_points`
- reliable defender profiles → `cautious_defender`

Profile confidence currently depends on `games_played`.

Explicit lead and response policy overrides still take precedence over profile-based presets.

## Game history fields

The preferred way to record completed tricks is `completed_tricks`.

Example:

```json
"completed_tricks": [
  {
    "cards": ["CA", "C10", "CK"],
    "winner_role": "defenders"
  }
]
```

Allowed `winner_role` values:

```text
declarer
defenders
```

The field `played_cards` is still supported for backward compatibility with older inputs, but new inputs should prefer `completed_tricks`.

Do not list the same card in both `played_cards` and `completed_tricks`, because duplicate known cards are rejected by input validation.

### Completed trick validation

The preferred way to record completed tricks is `completed_tricks`.

A detailed completed trick can include:

```json
{
  "cards": ["CJ", "SJ", "DJ"],
  "players": ["me", "left", "right"],
  "winner_role": "declarer",
  "winner_player": "me"
}
```

When detailed completed-trick metadata is provided, the engine validates structure, sequence consistency, and the actual trick winner.

Validation rules:

- `cards` must contain exactly three cards.
- `players` must contain exactly three unique players when provided.
- `players` must follow the known seating order:
  - `["me", "left", "right"]`
  - `["left", "right", "me"]`
  - `["right", "me", "left"]`
- `winner_player` must be valid when provided.
- `winner_role` must be valid when provided.
- `winner_role` is checked against `winner_player` when the local `player_role` allows a safe inference.
- the winner of one completed trick must lead the next completed trick.
- if `current_trick` is not empty, `trick_leader` must match the winner of the last completed trick.
- when `cards`, `players`, and `winner_player` are provided, the engine validates that `winner_player` actually won the trick according to the implemented Skat rules.

Older completed-trick entries without `players` or `winner_player` remain supported, but they cannot be checked as strictly.

The field `played_cards` is still supported for backward compatibility with older inputs, but new inputs should prefer `completed_tricks`.

Do not list the same card in both `played_cards` and `completed_tricks`, because duplicate known cards are rejected by input validation.

### Adding new example positions

When adding a new example file:

- Avoid duplicate known cards across `hand`, `current_trick`, `played_cards`, `skat`, and `completed_tricks`.
- Prefer `completed_tricks` over manually duplicating played cards in `played_cards`.
- If `players` are provided in completed tricks, make sure the order matches the seating order.
- Make sure `winner_player` matches the actual trick winner.
- Make sure the winner of one completed trick leads the next completed trick.
- If a current trick is already in progress, `trick_leader` must match the previous trick winner.
- Use `matadors` when the game value should be complete.
- Use `matadors: null` when the game value should intentionally remain incomplete.
- Use `analysis_mode: post_game_review` and `skat_visibility: known_post_game` for post-game review examples.

### Completed trick validation

The preferred way to record completed tricks is `completed_tricks`.

When detailed completed-trick metadata is provided, the engine validates both structure and consistency.

A detailed completed trick can include:

```json
{
  "cards": ["CJ", "SJ", "DJ"],
  "players": ["me", "left", "right"],
  "winner_role": "declarer",
  "winner_player": "me"
}
```

Validation rules:

- `cards` must contain exactly three cards.
- `players` must contain exactly three unique players when provided.
- `players` must follow the known seating order:
  - `["me", "left", "right"]`
  - `["left", "right", "me"]`
  - `["right", "me", "left"]`
- `winner_player` must be valid when provided.
- `winner_role` must be valid when provided.
- `winner_role` is checked against `winner_player` when the local `player_role` allows a safe inference.
- the winner of one completed trick must lead the next completed trick.
- if `current_trick` is not empty, `trick_leader` must match the winner of the last completed trick.
- when `cards`, `players`, and `winner_player` are provided, the engine validates that `winner_player` actually won the trick according to the implemented Skat rules.

Older completed-trick entries without `players` or `winner_player` remain supported, but they cannot be checked as strictly.

## Card notation

The tool uses compact English card notation.

### Suits

```text
C = Clubs
S = Spades
H = Hearts
D = Diamonds
```

### Ranks

```text
A  = Ace
10 = Ten
K  = King
Q  = Queen
J  = Jack
9  = Nine
8  = Eight
7  = Seven
```

Examples:

```text
CJ  = Jack of Clubs
SA  = Ace of Spades
H10 = Ten of Hearts
D7  = Seven of Diamonds
```

## Game types

Allowed values:

```text
clubs
spades
hearts
diamonds
grand
null
```

## Scoring and settlement

The tool separates card points, declared game value, card-point result status, and final settlement.

These concepts are intentionally modeled separately.

### Score summary

`score_summary` describes the currently known card points.

It combines:

- explicit declarer points
- explicit defender points
- points from completed tricks

Example output:

```json
{
  "explicit_declarer_points": 0,
  "explicit_defender_points": 0,
  "completed_trick_declarer_points": 90,
  "completed_trick_defender_points": 30,
  "total_declarer_points": 90,
  "total_defender_points": 30
}
```

### Game declaration

`game_declaration` describes the declared game and scoring metadata.

Example:

```json
{
  "game_type": "grand",
  "hand_game": false,
  "ouvert": false,
  "schneider_announced": false,
  "schwarz_announced": false,
  "bid_value": 72,
  "matadors": 2
}
```

Important:

- `position.hand` means the player's cards.
- `game_declaration.hand_game` means whether the game was declared as Hand.
- `matadors` must be known to calculate a complete suit or grand game value.
- `bid_value`: optional integer. The bid value at which the declarer won the auction / accepted the game. Used for overbid detection and final settlement.
- If `matadors` is `null`, the game value remains incomplete.

### Bid value and overbid detection

Input files can optionally include `bid_value`.

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

### Game value summary

`game_value_summary` describes the declared game value if it can be calculated.

For suit and grand games:

```text
game value = base value × game level
```

Current base values:

| Game type | Base value |
|---|---:|
| clubs | 12 |
| spades | 11 |
| hearts | 10 |
| diamonds | 9 |
| grand | 24 |

Current game level:

```text
matadors + 1
+ hand_game
+ schneider_announced
+ schwarz_announced
+ ouvert
```

Example:

```json
{
  "game_type": "grand",
  "is_null_game": false,
  "base_value": 24,
  "game_level": 3,
  "game_value": 72,
  "details": {
    "matadors": 2,
    "matador_multiplier": 3,
    "hand_game": false,
    "schneider_announced": false,
    "schwarz_announced": false,
    "ouvert": false,
    "modifier_multiplier": 0,
    "is_complete": true
  }
}
```

If `matadors` is unknown:

```json
{
  "game_level": null,
  "game_value": null,
  "details": {
    "matadors": null,
    "matador_multiplier": null,
    "is_complete": false
  }
}
```

### Null game values

Null games use fixed values:

| Game | Value |
|---|---:|
| null | 23 |
| null hand | 35 |
| null ouvert | 46 |
| null hand ouvert | 59 |

### Overbid summary

`overbid_summary` describes whether the declared game value covers the bid value.

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

### Game result summary

`game_result_summary` describes the current or final card-point result.

The declarer wins by card points with at least 61 points.

The defenders win by card points with at least 60 points.

Example:

```json
{
  "declarer_points": 90,
  "defender_points": 30,
  "points_remaining": 0,
  "is_complete": true,
  "winner": "declarer",
  "status": "final_decided",
  "raw_schneider_status": "declarer_made_schneider",
  "raw_schwarz_status": "none",
  "effective_schneider_status": "declarer_made_schneider",
  "effective_schwarz_status": "none"
}
```

Raw Schneider and Schwarz indicators are based on the currently known card points and may change while the game is still in progress.

Effective Schneider and Schwarz indicators are only final once all 120 card points have been assigned. Until then, they return `pending`.

### Game-end handling

The tool supports explicit game-end reasons through `game_end_reason`.

This field describes whether the game is still running, completed normally, or ended early through claim or concession.

Supported values:

| Value | Meaning |
|---|---|
| `not_ended` | The game is still in progress. |
| `normal_completion` | The game ended normally and all 120 card points are assigned. |
| `declarer_claimed_remaining_tricks` | The declarer claimed the remaining tricks. |
| `declarer_conceded_remaining_tricks` | The declarer conceded the remaining tricks. |
| `defenders_conceded_remaining_tricks` | The defenders conceded the remaining tricks. |

The original card-point result is stored in `game_result_summary`.

The game-end-adjusted result is stored in `adjusted_game_result_summary`.

`final_settlement_summary` uses `adjusted_game_result_summary`, not the raw `game_result_summary`.

#### Remaining-point assignment

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

#### Game-end validation

The engine validates `game_end_reason` against the known card-point state.

Rules:

- `not_ended` requires remaining card points.
- `normal_completion` requires zero remaining card points.
- claim/concession reasons require remaining card points.
- unknown `game_end_reason` values are rejected.

This prevents inconsistent inputs such as a normally completed game with only 86 assigned card points, or an unfinished game with all 120 points already assigned.

### Final settlement summary

`final_settlement_summary` combines `game_value_summary` and `adjusted_game_result_summary`.

This means early game-end reasons such as claim or concession can affect the final settlement.

It calculates a basic settlement score if both the game value and final card-point result are complete.

Current simplified settlement rule:

```text
declarer wins  → settlement_score = game_value
declarer loses → settlement_score = -2 × game_value
```

Example declarer win:

```json
{
  "is_complete": true,
  "missing_inputs": [],
  "declarer_won_by_card_points": true,
  "winner": "declarer",
  "game_value": 72,
  "settlement_score": 72,
  "is_loss": false,
  "is_overbid": null
}
```

Example declarer loss:

```json
{
  "is_complete": true,
  "missing_inputs": [],
  "declarer_won_by_card_points": false,
  "winner": "defenders",
  "game_value": 72,
  "settlement_score": -144,
  "is_loss": true,
  "is_overbid": null
}
```

If required information is missing, the summary remains incomplete:

```json
{
  "is_complete": false,
  "missing_inputs": [
    "complete_card_points",
    "game_value"
  ],
  "settlement_score": null
}
```

### Settlement vs. performance rating

The project intentionally separates individual game settlement from list, series, or tournament performance rating.

`final_settlement_summary` describes the settlement of a single Skat game.

It answers questions such as:

- Did the declarer win or lose the individual game?
- What is the game value?
- Was the game overbid?
- Which effective game value is used for settlement?
- What is the individual settlement score?

`performance_rating_summary` is a separate output layer for future list, series, or tournament rating.

It is intentionally not mixed into `final_settlement_summary`.

This separation is important because official Skat performance rating can add or subtract rating points beyond the individual game value. Those rating systems should be modeled separately from the settlement of a single game.

### Performance rating summary

`performance_rating_summary` is currently a scaffold.

Example:

```json
"performance_rating_summary": {
  "is_implemented": false,
  "rating_system": "isko_list",
  "basis": "individual_game_settlement",
  "game_outcome": "declarer_win",
  "settlement_score": 72,
  "rating_score": null,
  "declarer_rating_points": null,
  "defender_rating_points": null,
  "unsupported_reason": "isko_list_rating_not_implemented",
  "notes": [
    "Performance rating is separate from individual game settlement.",
    "List, series, and tournament rating are not implemented yet.",
    "final_settlement_summary remains the source for single-game settlement."
  ]
}
```

Fields:

| Field | Meaning |
|---|---|
| `is_implemented` | Whether this rating system is fully implemented. Currently `false`. |
| `rating_system` | Requested performance rating system, or `null`. |
| `basis` | The source layer used as basis. Currently `individual_game_settlement`. |
| `game_outcome` | One of `incomplete`, `declarer_win`, `declarer_loss`, or `unknown`. |
| `settlement_score` | The individual game settlement score from `final_settlement_summary`. |
| `rating_score` | Future final rating score. Currently `null`. |
| `declarer_rating_points` | Future declarer-side rating points. Currently `null`. |
| `defender_rating_points` | Future defender-side rating points. Currently `null`. |
| `unsupported_reason` | Explains why no performance rating score is calculated yet. |

### Overbid settlement

`final_settlement_summary` uses `overbid_summary` when calculating settlement.

For non-overbid games:

```text
effective_game_value = game_value
```

For overbid Suit/Grand games:

```text
effective_game_value = required_game_value
settlement_score = -2 * effective_game_value
```

This means the declarer can win by card points but still lose the settlement because the bid value was not covered by the calculated game value.

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

In this example, the calculated game value is 48, but the bid was 60. The smallest Grand/Suit game value that covers 60 is 72, so the overbid loss is counted as `-2 * 72 = -144`.

The raw card-point winner remains visible through:

```json
"winner": "declarer",
"declarer_won_by_card_points": true
```

The settlement loss is visible through:

```json
"is_loss": true,
"is_overbid": true
```

### Partial ISkO list rating implementation

The project includes a partial ISkO-style performance rating implementation for single-game declarer perspective.

This is separate from `final_settlement_summary`.

Current assumptions:

- The table is always a fixed three-player table.
- Four-player table rating is not modeled.
- `rating_system` must be set to `isko_list`.
- The implementation currently covers single-game declarer rating only.
- Full list, series, and tournament aggregation is not implemented yet.

Implemented rating points:

| Game outcome | Declarer rating points | Counterparty rating points |
|---|---:|---:|
| Declarer wins | +50 | 0 |
| Declarer loses | -50 | +40 per counterparty player |

The project exposes the fixed table assumption through:

```json
"table_player_count": 3
```

#### Declarer rating score

`declarer_rating_score` is the current implemented ISkO-style score from the declarer's perspective.

```text
declarer_rating_score = settlement_score + declarer_rating_points
```

`rating_score` is currently an alias for `declarer_rating_score`.

Examples:

| Settlement score | Declarer rating points | Declarer rating score |
|---:|---:|---:|
| 72 | 50 | 122 |
| -144 | -50 | -194 |

The counterparty rating points are shown separately and are not added to the declarer's `rating_score`.

Relevant output fields:

| Field | Meaning |
|---|---|
| `rating_score` | Alias for `declarer_rating_score`. |
| `declarer_rating_score` | Settlement score plus declarer rating points. |
| `declarer_rating_points` | +50 for declarer win, -50 for declarer loss. |
| `counterparty_rating_points` | Points per counterparty player. Currently 0 for declarer win and 40 for declarer loss. |
| `defender_rating_points` | Alias for `counterparty_rating_points`. |

#### Implemented and unsupported rating scope

`performance_rating_summary` also exposes the current implementation scope.

For `rating_system = "isko_list"`:

```json
{
  "is_implemented": false,
  "is_partially_implemented": true,
  "implemented_scope": "declarer_single_game_rating",
  "unsupported_scope": "full_list_series_tournament_rating"
}
```

Meaning:

| Field | Meaning |
|---|---|
| `is_implemented` | `false`, because full list/series/tournament rating is not complete. |
| `is_partially_implemented` | `true` for `isko_list`, because single-game declarer rating is calculated. |
| `implemented_scope` | The part that is currently calculated. |
| `unsupported_scope` | The part that is still missing. |

#### Null-game overbid safeguard

Null games use fixed game values rather than base-value multipliers.

For this reason, overbid settlement scoring is currently supported for Suit and Grand games when `required_game_value` is available.

If a Null game is detected as overbid and no `required_game_value` is available, `final_settlement_summary` remains incomplete instead of guessing a settlement score.

In that case:

```json
{
  "is_complete": false,
  "missing_inputs": ["overbid_required_game_value"],
  "is_overbid": true,
  "settlement_score": null
}
```

### Individual game settlement vs. performance rating

`final_settlement_summary` describes the settlement of a single game.

It does not represent list, series, or tournament performance scoring.

Performance rating according to tournament/list rules is a separate layer. It may include additional values such as:

- bonus points for own won games
- penalty points for own lost games
- bonus points for opponents' lost games
- table-size-dependent values

This should be implemented separately in a future `performance_rating` module and should not be mixed into `final_settlement_summary`.

## Player roles

Allowed values:

```text
declarer
defender
unknown
```

## Player positions

Allowed values:

```text
forehand
middlehand
rearhand
unknown
```

## Trick leaders

Allowed values:

```text
me
left
right
unknown
```

Basic consistency rules:

- If `current_trick` is empty, `trick_leader` can be `me` or `unknown`.
- If `current_trick` is not empty, `trick_leader` cannot be `me`.

## Simulation settings

### `left_hand_size`

Number of currently unknown cards assigned to the left opponent in each simulation sample.

### `right_hand_size`

Number of currently unknown cards assigned to the right opponent in each simulation sample.

### `sample_count`

Number of simulation samples.

Higher values usually produce more stable estimates but take longer.

### `random_seed`

Optional integer seed for reproducible results.

Use `null` if reproducibility is not required.

### `use_basic_opponent_strategy`

If `true`, opponents use a simple deterministic strategy:

```text
If the opponent can currently win the trick, play the lowest-point winning card.
Otherwise, play the lowest-point legal card.
```

If `false`, opponents choose a random legal card.

## Output

The tool prints:

- Input summary
- Legal cards
- Card analysis report
- Recommended card
- Strategic summary

Example output section:

```text
Card analysis report

Card   Win rate  Avg trick    Avg won   Avg lost      Swing  Recommendation
-----------------------------------------------------------------------------
SA        0.742      14.23      10.56       3.67       6.89        <-- best
S9        0.000       3.12       0.00       3.12      -3.12
D7        0.000       3.45       0.00       3.45      -3.45
H10       0.000      13.28       0.00      13.28     -13.28
S10       0.000      15.04       0.00      15.04     -15.04
```

## JSON output

The JSON output contains the full structured result.

Example command:

```powershell
python main.py --input examples/grand_second_position.json --multi-step 2 --compare-policies --output outputs/result.json
```

Top-level fields may include:

- input_file
- position
- settings
- opponent_policy_settings
- profile_preset_settings
- analysis_metadata
- game_declaration
- game_value_summary
- legal_cards
- analysis_report
- strategic_summary
- score_summary
- game_result_summary
- adjusted_game_result_summary
- final_settlement_summary
- recommendation
- multi_step_result
- policy_comparison_result
- overbid_summary
- performance_rating_summary

`game_result_summary` contains the raw card-point result before game-end adjustment.

`adjusted_game_result_summary` contains the card-point result after applying `game_end_reason`, such as claim or concession.

`final_settlement_summary` combines `game_value_summary` and `adjusted_game_result_summary`.

`multi_step_result` contains a serializable multi-step summary, context summary, final state, and step list.

`policy_comparison_result` contains one compact result per card-selection policy and a `recommended_policy`.


Example `performance_rating_summary` for a won declarer game:

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
  "unsupported_reason": "isko_list_rating_not_implemented"
}
```

Example for a lost declarer game:

```json
"performance_rating_summary": {
  "game_outcome": "declarer_loss",
  "settlement_score": -144,
  "rating_score": -194,
  "declarer_rating_score": -194,
  "declarer_rating_points": -50,
  "counterparty_rating_points": 40,
  "defender_rating_points": 40
}
```

## Architecture overview

Key modules:

- `main.py`: CLI entry point and human-readable printing
- `input_loader.py`: loads JSON input and builds initial state/settings
- `input_validation.py`: validates input data
- `game_state.py`: core game state structure
- `rules.py`: Skat rule logic such as legal cards and trick winners
- `simulation.py`: immediate trick simulation and opponent hand sampling
- `simulation_step.py`: simulate-and-advance logic for one player action
- `multi_step_simulation.py`: multi-step simulation orchestration
- `opponent_lead.py`: low-level opponent lead and response behavior
- `opponent_sequence.py`: prepares opponent action sequences before the player acts
- `simulation_context.py`: tracks simulated opponent cards and run events
- `known_cards.py`: central known-card utilities
- `sampling_validation.py`: validates card availability for sampling
- `multi_step_summary.py`: compact multi-step score summaries
- `policy_comparison.py`: compares card-selection policies
- `result_serialization.py`: JSON-serializable output structures
- `analysis_metadata.py`: optional metadata bundle for strategic context and player profiles
- `strategic_metadata.py`: analysis mode, skat visibility, and game-end metadata
- `player_profile.py`: placeholder structure for future opponent modeling
- `game_history.py`: completed-trick representation, score extraction, and completed-trick consistency validation
- `game_end.py`: game-end reason handling and remaining-point assignment for claim/concession scenarios

## Known limitations

Current limitations:

- Opponent behavior is still simplified and rule-based.
- Player profiles influence simulations only when profile-based presets are explicitly enabled.
- Profile-based presets use rough heuristics and are not learned from data.
- The same combined opponent preset is currently applied to both opponents.
- The engine does not yet model different individual policies for left and right opponents during the same simulation.
- Multi-step simulations still rely on sampled hidden cards.
- The engine is not yet a full perfect-information or full-game solver.
- Skat visibility is tracked as metadata but is not yet used to change live decision logic.
- Game value calculation uses declared metadata and does not yet infer matadors automatically.
- Schneider and Schwarz raw status is point-based. Effective Schneider and Schwarz status is final-state aware, but settlement scoring is still simplified.
- `final_settlement_summary` currently uses simplified settlement scoring and does not yet support overbid handling.
- Performance rating should be modeled separately from individual game settlement.
- Completed trick validation checks implemented rule logic, but the engine still depends on the correctness of the provided position context.
- Older completed-trick inputs without `players` or `winner_player` are supported but cannot be fully validated.
- Claim and concession handling currently assigns all remaining card points according to `game_end_reason`; it does not simulate the actual remaining tricks.
- The engine does not yet verify whether a claim was strategically or legally justified.
- The engine does not yet model player agreement or disputes around claim/concession.
- Bidding logic, game declaration value constraints, and full official settlement scoring are not fully modeled yet.
- The tool currently focuses on analysis and simulation, not on training a machine-learning model.
- Overbid settlement is supported for Suit and Grand games when `required_game_value` is available.
- Null-game overbid detection is supported, but settlement scoring remains conservative when no `required_game_value` is available.
- Full official settlement scoring is still simplified and does not yet cover every tournament/rules nuance.
- Individual game settlement and performance rating are intentionally separated.
- `performance_rating_summary` is currently a scaffold and does not yet calculate official list, series, or tournament rating points.
- `performance_rating_system = "isko_list"` is recognized and validated.
- ISkO performance rating is partially implemented for single-game declarer perspective, but full list/series/tournament aggregation is not implemented yet.
- `final_settlement_summary` remains the source of truth for single-game settlement.
- ISkO-style performance rating is partially implemented for a fixed three-player table.
- The current ISkO rating implementation covers single-game declarer perspective only.
- `rating_score` currently equals `declarer_rating_score`.
- Counterparty points are exposed separately and are not aggregated into the declarer's rating score.
- Full list, series, and tournament aggregation is not implemented yet.
- Four-player table performance rating is not modeled because the project currently assumes a fixed three-player table.

## Running tests

Run:

```powershell
python -m pytest
```

Or run the combined check script:

```powershell
.\scripts\check.ps1
```

The exact number of tests may change as the project grows. The important result is that all tests pass.

The test suite also validates all JSON files in the examples/ folder. If an example position contains invalid cards, duplicate cards, inconsistent trick leader information, or invalid simulation settings, the tests will fail.

The test suite also validates all JSON files in the `examples/` folder.

Example tests check that:

- every example can be loaded and validated
- every example can build a game state and settings
- every example has legal cards for the current position
- every example can build an analysis report
- key example output invariants remain stable

Concrete example invariants are tested in `tests/test_examples.py`.

General CLI and result-structure behavior is tested in `tests/test_cli.py`.

## Code quality

This project uses Ruff for linting, import sorting, and formatting.

Run lint checks:

```powershell
python -m ruff check .
```

Apply automatic fixes:

```powershell
python -m ruff check . --fix
```

Format code:

```powershell
python -m ruff format .
```

After formatting or fixing code, run the tests:

```powershell
python -m pytest
```

## Helper scripts

The project includes PowerShell helper scripts for common development commands.

Run lint checks and tests:

```powershell
.\scripts\check.ps1
```

Apply automatic Ruff fixes and format the code:

```powershell
.\scripts\format.ps1
```

If PowerShell blocks script execution, allow local scripts for the current user:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## Disclaimer

This tool provides statistical and rule-based recommendations based on simplified simulations. It is intended as a learning and analysis aid, not as a perfect Skat engine.

## Roadmap

Planned next areas:

### Simulation engine

- Improve opponent behavior policies
- Improve consistency of sampled opponent hands
- Add stronger game-end handling
- Add claim/concession logic
- Add better handling of known and unknown skat cards
- Improve defender cooperation logic
- Improve lead-card selection based on game phase and score

### Scoring and settlement

- Infer matadors automatically from known cards
- Add overbid handling
- Improve final settlement scoring
- Add performance rating for list/series/tournament scoring
- Keep individual game settlement separate from performance rating

### Player modeling

- Use `PlayerProfile` values to influence opponent decisions
- Add confidence weighting based on `games_played`
- Model aggressive and conservative opponents
- Model strong and weak defenders
- Support separate left/right opponent policies
- Improve profile-to-policy mapping
- Add confidence weighting based on profile sample size
- Learn profile behavior from real game history

### Analysis modes

- Distinguish live decision support from post-game review
- Prevent post-game-only information from influencing live recommendations
- Use known skat information only when allowed by `skat_visibility`

### Output and usability

- Improve JSON schema documentation
- Add more examples
- Add compact reporting modes
- Prepare a first `0.1.0` release