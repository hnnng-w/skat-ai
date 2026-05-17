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

## Example positions

The project includes example JSON input files in the `examples/` folder.

```text
examples/
  grand_leading.json
  grand_second_position.json
  grand_third_position.json
  hearts_leading.json
  null_second_position.json
```

Run an example:

```powershell
python main.py --input examples/grand_leading.json
```

Run another example:

```powershell
python main.py --input examples/null_second_position.json
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

## Optional analysis metadata

Input files may include optional metadata. These fields are currently stored and passed through the analysis pipeline, but they do not yet change recommendations.

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

Optional game declaration fields:

hand_game
ouvert
schneider_announced
schwarz_announced
matadors

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

- `input_file`
- `position`
- `settings`
- `analysis_metadata`
- `legal_cards`
- `analysis_report`
- `strategic_summary`
- `score_summary`
- `recommendation`
- `multi_step_result`
- `policy_comparison_result`

`multi_step_result` contains a serializable multi-step summary, context summary, final state, and step list.

`policy_comparison_result` contains one compact result per card-selection policy and a `recommended_policy`.

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

## Known limitations

Current limitations:

- Opponent behavior is still simplified.
- Player profiles are stored but do not yet influence decisions.
- Strategic metadata is stored but does not yet influence recommendations.
- Early termination logic is not implemented yet.
- Claiming remaining tricks is not implemented yet.
- Conceding or gifting remaining points is not implemented yet.
- Skat visibility is tracked as metadata but not yet used to change decision logic.
- Multi-step simulations still rely on sampled hidden cards.
- Opponent hand consistency has improved, but the engine is not yet a full perfect-information or full-game solver.
- Bidding logic, game value calculation, Schneider, Schwarz, Hand, Ouvert, and complete final scoring are not fully modeled yet.
- The tool currently focuses on analysis and simulation, not on training a machine-learning model.
- Opponent policy presets are still simple rule-based approximations.
- Profile-based presets use rough heuristics and are not yet learned from data.
- Player profiles influence simulations only when profile-based presets are explicitly enabled.
- The same combined opponent preset is currently applied to both opponents.
- The engine does not yet model different individual policies for left and right opponents during the same simulation.
- Game declaration metadata is stored, but full game-value scoring is not complete yet.

## Running tests

Run:

python -m pytest

Or run the combined check script:

.\scripts\check.ps1

The exact number of tests may change as the project grows. The important result is that all tests pass.

The test suite also validates all JSON files in the examples/ folder. If an example position contains invalid cards, duplicate cards, inconsistent trick leader information, or invalid simulation settings, the tests will fail.

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