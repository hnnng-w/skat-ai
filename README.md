# Skat AI

A local Python-based Skat analysis and simulation tool.

The project analyzes a given Skat position, checks legal cards, simulates immediate trick outcomes, estimates expected point swings, and recommends a card based on the current situation.

## Current capabilities

- Card parsing
- Card point calculation
- Trump detection
- Effective suit detection
- Legal card detection
- Trick winner calculation
- Trick point calculation
- Full 32-card deck tracking
- Seen and unseen card tracking
- JSON-based position input
- Input validation
- Random opponent hand generation
- Basic opponent strategy
- Immediate trick simulation
- Win-rate estimation
- Expected point swing estimation
- Strategic summary generation
- Reproducible simulations with `random_seed`

## Project structure

```text
skat-ai/
  input_position.json
  main.py
  pyproject.toml
  pytest.ini
  README.md
  src/
    skat_ai/
      __init__.py
      analysis_report.py
      card_tracking.py
      deck.py
      game_state.py
      input_loader.py
      input_validation.py
      recommender.py
      rules.py
      simulation.py
  tests/
    test_rules.py
```

## Requirements

- Python 3.11 or newer
- pytest for running tests

## Installation

Create and activate a virtual environment:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

Install the package with development dependencies:

```powershell
python -m pip install -e ".[dev]"
```

This installs the local package plus development tools such as `pytest` and `ruff`.

## Running the tool

Edit the file:

```text
input_position.json
```

Then run:

```powershell
python main.py
```

You can also pass a specific input file:

```powershell
python main.py --input input_position.json
```

Example:

```powershell
python main.py --input examples/grand_second_position.json
```

Show command-line help:

```powershell
python main.py --help
```

Override the number of simulation samples:

```powershell
python main.py --input examples/grand_leading.json --samples 5000
```

Override the random seed:

```powershell
python main.py --input examples/grand_leading.json --seed 123
```

Override both:

```powershell
python main.py --input examples/grand_leading.json --samples 5000 --seed 123
```

Override the opponent strategy:

```powershell
python main.py --input examples/grand_leading.json --opponent-strategy basic
```

Use random legal opponent moves instead:

```powershell
python main.py --input examples/grand_leading.json --opponent-strategy random
```

Combine CLI overrides:

```powershell
python main.py --input examples/grand_leading.json --samples 5000 --seed 123 --opponent-strategy random
```

Write the analysis result to a JSON file:

```powershell
python main.py --input examples/grand_leading.json --output analysis_result.json
```

Write the result to a folder:

```powershell
python main.py --input examples/grand_leading.json --output outputs/grand_leading_result.json
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

## Input format

Example `input_position.json`:

```json
{
  "game_type": "grand",
  "player_role": "declarer",
  "player_position": "forehand",
  "trick_leader": "left",
  "hand": ["SA", "S10", "S9", "H10", "D7"],
  "current_trick": ["S7"],
  "played_cards": [],
  "skat": [],
  "left_hand_size": 5,
  "right_hand_size": 5,
  "sample_count": 1000,
  "random_seed": 42,
  "use_basic_opponent_strategy": true
}
```

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

## Running tests

Run:

```powershell
python -m pytest
```

Expected result at the current project stage:

```text
111 passed
```

The test suite also validates all JSON files in the `examples/` folder. If an example position contains invalid cards, duplicate cards, inconsistent trick leader information, or invalid simulation settings, the tests will fail.

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

## Current limitations

This project is currently an immediate-trick analysis tool, not a full Skat game engine.

Current limitations:

- The simulation only evaluates the current trick.
- It does not yet simulate the full rest of the game.
- Opponent behavior is still simple.
- Reizphase, bidding logic, game declaration value, Schneider, Schwarz, Hand, Ouvert, and full scoring are not fully modeled yet.
- Opponent card distributions are random among unseen cards and do not yet account for bidding clues or previous strategic signals.
- The strategic summary is rule-based and not generated by a language model.

## Development roadmap

Possible next steps:

1. Add full-game state tracking.
2. Model player order and trick ownership more precisely.
3. Simulate multiple future tricks.
4. Add smarter opponent behavior.
5. Use bidding and play-history clues to constrain opponent hands.
6. Add game score calculation.
7. Add a command-line interface.
8. Add a simple local UI.
9. Add optional LLM-based explanations.
10. Train a model on simulated or real game data.

## Disclaimer

This tool provides statistical and rule-based recommendations based on simplified simulations. It is intended as a learning and analysis aid, not as a perfect Skat engine.