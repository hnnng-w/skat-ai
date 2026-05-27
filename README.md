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
- Opponent policy presets
- Optional profile-based policy presets
- Completed-trick structure, sequence, and rule-winner validation
- Game declaration and game-value summaries
- Score and game-result summaries
- Claim/concession game-end handling
- Final single-game settlement summaries
- Supported Suit/Grand overbid settlement
- Partial fixed-three-player ISkO-style performance rating
- JSON output for regression-friendly analysis

## Requirements

- Python 3.11 or newer
- PowerShell for helper scripts on Windows
- `pytest` and `ruff` for development checks

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
- [Scoring and settlement](docs/scoring.md)
- [Game-end handling](docs/game_end.md)
- [Overbid handling](docs/overbid.md)
- [Performance rating](docs/performance_rating.md)
- [Examples](docs/examples.md)
- [Architecture](docs/architecture.md)
- [Roadmap](docs/roadmap.md)

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

Skat AI is an experimental analysis tool. It already supports a broad set of single-position analysis, game-result, settlement, overbid, and partial fixed-three-player ISkO rating features.

Known limitations and planned improvements are tracked in [Roadmap documentation](docs/roadmap.md).

## Disclaimer

This project is not a full official Skat rules engine, tournament system, or perfect-information solver. It is intended as an experimental analysis and simulation tool.
