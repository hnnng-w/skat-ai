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

## Examples

For example input files, example commands, post-game review examples, claim/concession examples, overbid examples, multi-step simulation examples, and policy-comparison examples, see:

[Examples documentation](docs/examples.md)

## Input JSON

For the detailed input format, supported fields, card notation, metadata, completed tricks, and validation rules, see:

[Input JSON documentation](docs/input_json.md)

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
| `isko_list` | Partially implemented ISkO-style single-game rating for the fixed three-player table. Full list/series/tournament aggregation is not implemented yet. |

If omitted, `performance_rating_summary.rating_system` is `null`.

Unknown values are rejected during input validation.

For details about `performance_rating_system` and partial ISkO rating, see:

[Performance rating documentation](docs/performance_rating.md)

## Optional analysis metadata

Input files may include optional metadata. Some fields are stored for reporting and future logic. Profile-based presets currently affect multi-step simulation policy selection when enabled. The immediate single-trick analysis still uses the base opponent strategy path.

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

Game-end metadata such as `game_end_reason` is supported. For supported values and validation rules, see:

[Game-end handling documentation](docs/game_end.md)

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

### Overbid handling

For `bid_value`, `overbid_summary`, `required_game_value`, `effective_game_value`, and supported Suit/Grand overbid settlement, see:

[Overbid handling documentation](docs/overbid.md)

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

## Game-end handling

For normal completion, claim, concession, remaining-point assignment, and `adjusted_game_result_summary`, see:

[Game-end handling documentation](docs/game_end.md)

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

## Output JSON

For the detailed output structure and field descriptions, see:

[Output JSON documentation](docs/output_json.md)

## Architecture

For the project structure and module overview, see:

[Architecture documentation](docs/architecture.md)

## Roadmap and limitations

For completed areas, known limitations, planned improvements, and issue-cleanup notes, see:

[Roadmap documentation](docs/roadmap.md)

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

### Simulation engine

- Improve opponent behavior policies
- Improve consistency of sampled opponent hands
- Add stronger game-end handling
- Add better handling of known and unknown skat cards
- Improve defender cooperation logic
- Improve lead-card selection based on game phase and score

## Scoring and settlement

For card points, game value, Schneider/Schwarz, game result summaries, and final single-game settlement, see:

[Scoring and settlement documentation](docs/scoring.md)

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

## Documentation

Detailed documentation is split into topic-specific files:

- [Input JSON](docs/input_json.md)
- [Output JSON](docs/output_json.md)
- [Scoring and settlement](docs/scoring.md)
- [Game-end handling](docs/game_end.md)
- [Overbid handling](docs/overbid.md)
- [Performance rating](docs/performance_rating.md)
- [Examples](docs/examples.md)
- [Architecture](docs/architecture.md)
- [Roadmap](docs/roadmap.md)