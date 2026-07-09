# Skat AI

![Check](https://github.com/hnnng-w/skat-ai/actions/workflows/check.yml/badge.svg)

Skat AI is a local Python-based analysis and simulation engine for Skat positions.

It evaluates legal card choices, estimates expected point swings, recommends cards, tracks game state, simulates multi-step play, and supports post-game review workflows. The project focuses on rule-based and probability-based analysis rather than machine learning.

Skat AI is experimental. It is not a full official tournament system, not a perfect-information solver, and not a complete replacement for official Skat rules arbitration.

## Features

### Core analysis

* JSON-based Skat position analysis
* Legal-card detection
* Card-point calculation
* Trump and trick-winner logic
* Immediate trick simulation
* Configured opponent response policies for immediate analysis and multi-step candidate completion
* Expected point swing calculation
* Card recommendations
* JSON output for regression-friendly analysis

### Simulation and policy comparison

* Multi-step simulation
* Configurable card-selection policies
* Policy comparison across card-selection strategies
* Opponent lead and response simulation
* Opponent policy presets
* Optional profile-based policy presets
* Separate left/right opponent policy settings
* Left/right opponent policy CLI overrides
* Shared opponent-policy precedence for immediate and multi-step paths
* Basic defender cooperation heuristics

### Game history, scoring, and settlement

* Completed-trick structure validation
* Completed-trick sequence validation
* Completed-trick rule-winner validation
* Explicit and completed-trick point summaries
* Score and game-result summaries
* Game declaration and game-value summaries
* Automatic matador inference from known declarer-card context where possible
* Claim/concession game-end handling
* Adjusted game-result summaries
* Final single-game settlement summaries
* Supported Suit/Grand overbid settlement
* Partial fixed-three-player ISkO-style performance rating

### Information policy

* Live-vs-post-game information enforcement
* Rejection of post-game-only information in live-decision mode
* Information policy summary output

### Post-game review

* Optional `actual_card_played` input
* Validation that the actual card is valid and legal
* Comparison between actual card and recommended card
* Expected point swing difference
* Decision quality classification:

  * `not_available`
  * `optimal`
  * `acceptable`
  * `suboptimal`
  * `mistake`
* Machine-readable decision factors
* Human-readable decision explanations
* Recommendation gap details:

  * `actual_card_rank`
  * `recommended_card_rank`
  * `candidate_count`
  * `better_card_count`
* Human-readable CLI output for post-game review summaries

### Validation

* Input JSON schema validation
* Output JSON schema validation
* Generated-output schema validation for selected examples
* Pytest regression coverage
* Ruff checks
* Combined project check script

## Requirements

* Python 3.11 or newer
* PowerShell for helper scripts on Windows
* Development dependencies from `.[dev]`, including:

  * `pytest`
  * `ruff`
  * `jsonschema`

## Installation

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the project with development dependencies:

```powershell
python -m pip install -e ".[dev]"
```

Run the combined check script:

```powershell
.\scripts\check.ps1
```

## Usage

Show available CLI options and common command examples:

```powershell
python main.py --help
```

Run the default analysis from the repository root. This reads the root
`input_position.json` quick-start fixture:

```powershell
python main.py
```

Run analysis with a specific input file:

```powershell
python main.py --input examples/grand_second_position.json
```

Run immediate analysis with a configured opponent response policy:

```powershell
python main.py --input examples/grand_second_position.json --opponent-response-policy highest_point
```

Run a multi-step analysis:

```powershell
python main.py --input examples/grand_second_position.json --multi-step 2
```

Compare all multi-step local card-selection policies:

```powershell
python main.py --input examples/grand_second_position.json --multi-step 1 --compare-policies
```

Print only policy-comparison output, suppressing the normal analysis and
individual multi-step details:

```powershell
python main.py --input examples/grand_second_position.json --multi-step 1 --compare-policies --comparison-only
```

Run a multi-step analysis with separate left/right opponent policies:

```powershell
python main.py --input examples/grand_left_right_opponent_policies.json --multi-step 2 --left-opponent-lead-policy highest_point --right-opponent-response-policy basic_defender_response
```

Global policy presets and policies cascade to both opponents. Side-specific input fields or CLI overrides win for their side.

Write output to JSON:

```powershell
python main.py --input examples/grand_second_position.json --output outputs/result.json
```

Suppress successful human-readable stdout output for automation-friendly JSON runs:

```powershell
python main.py --input examples/grand_second_position.json --output outputs/result.json --quiet
```

Without `--quiet`, default CLI behavior is unchanged and successful analysis output is still printed to `stdout`. With `--quiet`, analysis still runs normally and JSON output is still written when `--output` is provided. Expected errors are not suppressed and still go to `stderr`.

Run an overbid example where the declarer wins card points but loses settlement:

```powershell
python main.py --input examples/grand_overbid_declarer_card_points_win.json --output outputs/overbid_test.json
```

Run a post-game review example with an actual played card:

```powershell
python main.py --input examples/spades_post_game_actual_card_played.json
```

CLI exit codes:

* `0` = success
* `1` = expected input, runtime, or output failure
* `2` = invalid CLI usage

Expected errors are written to `stderr`. Successful analysis output remains on `stdout`.

For more examples, see [Examples documentation](docs/examples.md).

## Documentation

Detailed documentation is split into topic-specific files:

* [Input JSON](docs/input_json.md)
* [Input JSON schema](schemas/input.schema.json)
* [Output JSON](docs/output_json.md)
* [Output JSON schema](schemas/output.schema.json)
* [Schema validation](docs/schema_validation.md)
* [Scoring and settlement](docs/scoring.md)
* [Game-end handling](docs/game_end.md)
* [Overbid handling](docs/overbid.md)
* [Performance rating](docs/performance_rating.md)
* [Examples](docs/examples.md)
* [Architecture](docs/architecture.md)
* [Roadmap](docs/roadmap.md)
* [Project handoff](docs/project_handoff.md)

## Development

Run all checks:

```powershell
.\scripts\check.ps1
```

Run tests directly:

```powershell
python -m pytest
```

Run Ruff checks:

```powershell
python -m ruff check .
```

Apply Ruff fixes and format code:

```powershell
.\scripts\format.ps1
```

The test suite also validates JSON files in `examples/`. If an example contains invalid cards, duplicate known cards, inconsistent completed-trick metadata, invalid game-end metadata, invalid information-policy metadata, or invalid simulation settings, the tests will fail.

## Project status

Skat AI already supports a broad set of single-position analysis, multi-step simulation, opponent-policy modeling, game-result summaries, game-value summaries, settlement summaries, overbid handling, live-vs-post-game information enforcement, post-game review output, and partial fixed-three-player ISkO-style rating features.

Known limitations and planned improvements are tracked in [Roadmap documentation](docs/roadmap.md).

## Disclaimer

This project is not a full official Skat rules engine, tournament system, or perfect-information solver.

It is intended as an experimental analysis and simulation tool.
