# Skat AI

![Check](https://github.com/hnnng-w/skat-ai/actions/workflows/check.yml/badge.svg)

Skat AI is a Python-based analysis engine for Skat positions.

It evaluates legal card choices, estimates immediate trick outcomes with simulation, tracks game state, and supports basic multi-step projections. The project focuses on rule-based and probability-based analysis rather than machine learning.

## Features

- JSON-based Skat position analysis
- Legal-card detection
- Immediate trick simulation
- Expected point swing calculation
- Card recommendations
- Multi-step simulation
- Policy comparison across card-selection strategies
- Opponent lead and response simulation
- Opponent policy presets
- Optional profile-based policy presets
- Separate left/right opponent policy settings
- Left/right opponent policy CLI overrides
- Completed-trick structure, sequence, and rule-winner validation
- Score and game-result summaries
- Game declaration and game-value summaries
- Claim/concession game-end handling
- Adjusted game-result summaries
- Final single-game settlement summaries
- Supported Suit/Grand overbid settlement
- Partial fixed-three-player ISkO-style performance rating
- Live-vs-post-game information enforcement
- Information policy summary output
- Input and output JSON schema validation
- Generated-output schema validation for selected examples
- JSON output for regression-friendly analysis

## Requirements

- Python 3.11 or newer
- PowerShell for helper scripts on Windows
- Development dependencies from `.[dev]`, including:
  - `pytest`
  - `ruff`
  - `jsonschema`

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

Run the default analysis:

```powershell
python main.py
```

Run analysis with a specific input file:

```powershell
python main.py --input examples/grand_second_position.json
```

Run a multi-step analysis:

```powershell
python main.py --input examples/grand_second_position.json --multi-step 2
```

Run a multi-step analysis with separate left/right opponent policies:

```powershell
python main.py --input examples/grand_second_position.json --multi-step 2 --left-opponent-lead-policy highest_point --right-opponent-response-policy basic_defender_response
```

Write output to JSON:

```powershell
python main.py --input examples/grand_second_position.json --output outputs/result.json
```

Run an overbid example where the declarer wins card points but loses settlement:

```powershell
python main.py --input examples/grand_overbid_declarer_card_points_win.json --output outputs/overbid_test.json
```

For more examples, see [Examples documentation](docs/examples.md).

## Documentation

Detailed documentation is split into topic-specific files:

- [Input JSON](docs/input_json.md)
- [Input JSON schema](schemas/input.schema.json)
- [Output JSON](docs/output_json.md)
- [Output JSON schema](schemas/output.schema.json)
- [Schema validation](docs/schema_validation.md)
- [Scoring and settlement](docs/scoring.md)
- [Game-end handling](docs/game_end.md)
- [Overbid handling](docs/overbid.md)
- [Performance rating](docs/performance_rating.md)
- [Examples](docs/examples.md)
- [Architecture](docs/architecture.md)
- [Roadmap](docs/roadmap.md)
- [Project handoff](docs/project_handoff.md)

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

The test suite also validates all JSON files in `examples/`. If an example contains invalid cards, duplicate known cards, inconsistent completed-trick metadata, invalid game-end metadata, or invalid simulation settings, the tests will fail.

## Project status

Skat AI is an experimental analysis tool. It already supports a broad set of single-position analysis, multi-step simulation, opponent-policy modeling, game-result, settlement, overbid, live-vs-post-game, and partial fixed-three-player ISkO rating features.

Known limitations and planned improvements are tracked in [Roadmap documentation](docs/roadmap.md).

## Disclaimer

This project is not a full official Skat rules engine, tournament system, or perfect-information solver. It is intended as an experimental analysis and simulation tool.
