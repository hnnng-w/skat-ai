# Architecture

This document describes the project structure and main modules.

## Overview

`skat-ai` is organized as a small rule-based analysis engine around a JSON input/output workflow.

The main flow is:

1. Load and validate JSON input.
2. Build an internal game state.
3. Apply information-policy checks.
4. Analyze legal card choices.
5. Estimate expected point swings.
6. Build card recommendations.
7. Optionally run multi-step simulation or policy comparison.
8. Build game-result, settlement, performance-rating, and post-game review summaries.
9. Serialize output for CLI and JSON use.

The project is not a machine-learning model. Its behavior is based on Skat rules, deterministic helpers, and simulation.

## Main entry point

| File      | Purpose                                                                                                                           |
| --------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `main.py` | CLI entry point, orchestration, output construction, multi-step execution, optional policy comparison, and human-readable output. |

## Core rules

| File                   | Purpose                                                                            |
| ---------------------- | ---------------------------------------------------------------------------------- |
| `src/skat_ai/deck.py`  | Deck and card helpers.                                                             |
| `src/skat_ai/rules.py` | Card notation, card points, trump logic, legal-card logic, and trick-winner logic. |

The internal card-strength values in `rules.py` are comparison values only. They are not Skat card points and must not be used for scoring.

## Input loading and validation

| File                                | Purpose                                                                                                             |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| `src/skat_ai/input_loader.py`       | Loads JSON input, extracts settings, and converts input into internal structures.                                   |
| `src/skat_ai/input_validation.py`   | Validates input fields, cards, metadata, points, game-end consistency, policy settings, and rating-system metadata. |
| `src/skat_ai/known_cards.py`        | Tracks and validates known cards.                                                                                   |
| `src/skat_ai/information_policy.py` | Centralizes live-vs-post-game information rules and builds `information_policy_summary`.                            |

Validation is split between JSON Schema and Python validation:

1. JSON Schema validates stable input/output structure.
2. Python validation handles Skat-specific cross-field rules.
3. Pytest covers behavior and regression scenarios.

## Game history

| File                          | Purpose                                                                |
| ----------------------------- | ---------------------------------------------------------------------- |
| `src/skat_ai/game_history.py` | Completed-trick structure, sequence, role, and rule-winner validation. |

Completed-trick validation is used to prevent inconsistent historical game states, duplicate cards, impossible sequences, and mismatched trick winners where enough information is available.

## Game value and result

| File                               | Purpose                                                                                                   |
| ---------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `src/skat_ai/game_declaration.py`  | Game declaration metadata, default handling, matador inference integration, and serialization.            |
| `src/skat_ai/matador_inference.py` | Automatic matador inference from known declarer cards where possible.                                     |
| `src/skat_ai/game_value.py`        | Game value calculation for suit, grand, and null games.                                                   |
| `src/skat_ai/game_result.py`       | Raw card-point result, winner, remaining points, Schneider/Schwarz status, and adjusted result summaries. |
| `src/skat_ai/score.py`             | Known point summary from explicit points and completed tricks.                                            |

Matador inference is intentionally conservative. It uses currently known declarer-card context where possible and does not yet reconstruct every possible matador state from all historical trick ownership scenarios.

## Game end and settlement

| File                                | Purpose                                                                                                       |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| `src/skat_ai/game_end.py`           | Game-end reason handling and remaining-point assignment for claim/concession scenarios.                       |
| `src/skat_ai/overbid.py`            | Bid-value comparison, overbid detection, and required game-value calculation.                                 |
| `src/skat_ai/final_settlement.py`   | Simplified single-game settlement scoring, including supported Suit/Grand overbid loss handling.              |
| `src/skat_ai/performance_rating.py` | Performance-rating layer, partial fixed-three-player ISkO single-game rating, and separation from settlement. |

Claim and concession handling assigns remaining card points according to `game_end_reason`. It does not simulate the actual remaining tricks or verify whether a claim was strategically justified.

## Simulation

| File                                   | Purpose                                                |
| -------------------------------------- | ------------------------------------------------------ |
| `src/skat_ai/simulation.py`            | Monte Carlo simulation logic.                          |
| `src/skat_ai/simulation_context.py`    | Simulation context creation and strict-context checks. |
| `src/skat_ai/simulation_step.py`       | Single simulation-step handling.                       |
| `src/skat_ai/state_transition.py`      | Applies card plays and transitions game state.         |
| `src/skat_ai/multi_step_simulation.py` | Multi-step simulation orchestration.                   |
| `src/skat_ai/multi_step_summary.py`    | Serializable multi-step result summaries.              |

The simulation layer is probabilistic and heuristic. It is designed for analysis support, not for perfect-information solving.

## Opponent modeling

| File                                     | Purpose                                          |
| ---------------------------------------- | ------------------------------------------------ |
| `src/skat_ai/opponent_policy.py`         | Opponent policy definitions and selection logic. |
| `src/skat_ai/opponent_lead.py`           | Opponent lead behavior.                          |
| `src/skat_ai/opponent_sequence.py`       | Opponent play sequencing.                        |
| `src/skat_ai/opponent_policy_preset.py`  | Named policy presets.                            |
| `src/skat_ai/opponent_profile_policy.py` | Profile-based policy recommendation.             |
| `src/skat_ai/player_profile.py`          | Player profile modeling.                         |

Opponent policy handling supports both global and separate left/right opponent policy settings.

Profile-based policy presets use rough, rule-based `PlayerProfile` heuristics. Profile confidence is derived from `games_played` only: missing data is `unknown`, fewer than 100 games is `low`, fewer than 500 games is `medium`, and 500 or more games is `high`. When cautious and aggressive profile-derived presets conflict, the higher-confidence side wins; equal confidence preserves the existing `aggressive_points` over `cautious_defender` fallback.

When profile presets are enabled for multi-step simulation, the left and right player profiles can affect their respective effective left/right opponent policy settings. Explicit side-specific CLI overrides are applied last and remain authoritative.

Some profile fields are currently informational only: `solo_games_played`, `defender_games_played`, `solo_win_rate`, `suit_game_rate`, and `null_game_rate`.

The current defender cooperation model includes:

* safer defender lead behavior
* safe smear when the partner is currently winning
* safer discard when the declarer is winning and the defender cannot win

These behaviors are still heuristic and not a full partnership model.

## Left/right opponent policy flow

Opponent policy handling starts with global settings and normalized left/right settings.

Flow:

1. `input_loader.py` normalizes global and left/right policy settings.
2. `input_validation.py` validates policy values.
3. `main.py` applies profile-derived left/right presets when enabled for multi-step simulation.
4. `main.py` applies explicit side-specific CLI overrides last.
5. `multi_step_simulation.py` passes settings into opponent sequence preparation.
6. `opponent_sequence.py` selects left/right lead and response policies.
7. `opponent_policy.py` contains shared policy selection helpers.

## Analysis and recommendation

| File                                | Purpose                                     |
| ----------------------------------- | ------------------------------------------- |
| `src/skat_ai/analysis_report.py`    | Card analysis report construction.          |
| `src/skat_ai/card_selection.py`     | Card selection helpers.                     |
| `src/skat_ai/recommender.py`        | Recommendation and strategic summary logic. |
| `src/skat_ai/policy_comparison.py`  | Policy comparison logic.                    |
| `src/skat_ai/analysis_metadata.py`  | Analysis-mode and metadata handling.        |
| `src/skat_ai/strategic_metadata.py` | Strategic metadata helpers.                 |

The analysis report is the basis for recommendations, post-game comparison, and several CLI/JSON summaries.

## Post-game review

| File                              | Purpose                                                                                                                      |
| --------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `src/skat_ai/post_game_review.py` | Actual-card comparison, decision quality classification, decision factors, explanation text, and recommendation gap details. |

Post-game review uses the regular analysis report and optionally compares it with `actual_card_played`.

Current post-game review output includes:

* availability and reason
* actual card
* recommended card
* actual expected point swing
* recommended expected point swing
* expected point swing difference
* decision quality
* decision factors
* decision explanation
* actual card rank
* recommended card rank
* candidate count
* better card count

## Output

| File                                  | Purpose                                                                    |
| ------------------------------------- | -------------------------------------------------------------------------- |
| `src/skat_ai/output_writer.py`        | Writes JSON output.                                                        |
| `src/skat_ai/result_serialization.py` | Serialization helpers for nested and simulation-related output structures. |

Output is designed to be regression-friendly and schema-validatable.

## Schemas and validation scripts

| File                                           | Purpose                                                                  |
| ---------------------------------------------- | ------------------------------------------------------------------------ |
| `schemas/input.schema.json`                    | Stable input JSON structure.                                             |
| `schemas/output.schema.json`                   | Stable output JSON structure.                                            |
| `scripts/validate_examples_schema.py`          | Validates input examples against the input schema.                       |
| `scripts/validate_generated_outputs_schema.py` | Generates selected outputs and validates them against the output schema. |
| `scripts/check.ps1`                            | Runs the combined project check.                                         |

## Tests

Tests are organized by module and behavior in `tests/`.

Important regression areas:

* rules and legal-card logic
* completed-trick validation
* game value and final settlement
* matador inference
* game-end handling
* overbid handling
* performance rating
* information policy
* post-game review
* example files
* CLI result structure
* multi-step simulation
* opponent policies
* left/right opponent policy behavior
* schema validation

## Validation layers

The project uses four main validation layers:

1. JSON Schema validation for stable input/output structure.
2. Python validation for Skat-specific cross-field rules.
3. Pytest regression tests for behavior and examples.
4. Ruff for code quality.

## Design principles

Current design principles:

* Keep behavior test-driven.
* Prefer small focused modules over large orchestration files.
* Keep JSON output explicit and regression-friendly.
* Keep CLI output human-readable but secondary to structured JSON.
* Keep live-decision mode separate from post-game-review mode.
* Keep code and program output in English.
* Preserve the fixed three-player table assumption unless explicitly expanded later.
