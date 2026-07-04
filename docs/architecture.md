# Architecture

This document describes the project structure and main modules.

## Overview

`skat-ai` is organized as a small rule-based analysis engine around a JSON input/output workflow.

The main flow is:

1. Load and validate JSON input.
2. Build an internal game state.
3. Apply information-policy checks.
4. If the normalized current actor is the local player, analyze legal card choices.
5. Estimate expected point swings for available local decisions.
6. Build card recommendations or an unavailable Immediate Analysis shape.
7. Optionally run phase-aware multi-step simulation or policy comparison.
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
| `src/skat_ai/turn_phase.py`         | Normalizes and validates canonical `trick_leader` and `next_player` from the current trick length.                  |

Validation is split between JSON Schema and Python validation:

1. JSON Schema validates stable input/output structure.
2. Python validation handles Skat-specific cross-field rules.
3. Pytest covers behavior and regression scenarios.

## Game history

| File                          | Purpose                                                                |
| ----------------------------- | ---------------------------------------------------------------------- |
| `src/skat_ai/game_history.py` | Completed-trick structure, sequence, role, and rule-winner validation. |

Completed-trick validation is used to prevent inconsistent historical game states, duplicate cards, impossible sequences, and mismatched trick winners where enough information is available. When `cards` and ordered `players` are present, validation derives the rule winner and checks both `winner_player` and concrete `winner_role` metadata against that derived result.

## Game value and result

| File                               | Purpose                                                                                                   |
| ---------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `src/skat_ai/game_declaration.py`  | Game declaration metadata, default handling, matador inference integration, and serialization.            |
| `src/skat_ai/matador_inference.py` | Automatic matador inference from known declarer cards where possible.                                     |
| `src/skat_ai/game_value.py`        | Game value calculation for suit, grand, and null games.                                                   |
| `src/skat_ai/game_result.py`       | Raw card-point result, winner, remaining points, Schneider/Schwarz status, and adjusted result summaries. |
| `src/skat_ai/game_history.py`      | Known point summary from explicit points and completed tricks.                                            |

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

Immediate Analysis is available only when the normalized input state has
`next_player = "me"` and the game has not ended. Opponent-turn input keeps the
top-level position unchanged and returns an unavailable Immediate Analysis shape.

Multi-step simulation uses the normalized turn phase, not `next_player` alone.
It can prepare an empty left lead through right response, an empty right lead,
or right's response to an existing one-card left lead. Valid phases where the
local player has already acted and only opponents remain stop with
`unsupported_turn_phase` without mutating the state.

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

When profile presets are enabled, the left and right player profiles can affect their respective effective left/right opponent response policies in immediate analysis and their effective left/right opponent policy settings in multi-step simulation. Explicit side-specific CLI overrides are applied last and remain authoritative.

Some profile fields are currently informational only: `solo_games_played`, `defender_games_played`, `solo_win_rate`, `suit_game_rate`, and `null_game_rate`.

The current defender cooperation model is heuristic, explainable, and implemented for the fixed three-player table. It includes:

* safer defender lead behavior
* avoiding overtaking a winning partner when a partner-safe legal card exists
* safe smear while preserving the partner's winning position
* forced partner overtake using the lowest-point legal winning card
* equal-point forced-overtake tie-break using weakest sufficient trick strength
* winning-card selection using the lowest-point legal winner
* equal-point winning-card tie-break using weakest sufficient trick strength
* equal-point safe-smear tie-break using weakest trick strength
* safer discard when the declarer is winning and the defender cannot win
* narrow second-hand trump conservation on zero-point non-trump leads when only trump wins and a losing discard exists

Issue #22's current heuristic and explainable defender-partnership scope is implemented. Current limitations remain future strategy work rather than blockers for that issue:

* partnership inference is strongest in the currently supported second-hand path
* no complete rear-hand partnership model exists
* no dedicated null-game defender-partnership strategy exists
* defender partnership heuristics depend on the concrete `declarer_player` identity supplied by the input
* no perfect-information solving, search, machine learning, or hidden-card inference is used

## Left/right opponent policy flow

Opponent policy handling is centralized in `src/skat_ai/effective_opponent_policy.py`.
`main.py` builds one `EffectiveOpponentPolicySettings` value per analysis invocation
and shares it with immediate analysis, multi-step simulation, and multi-step policy
comparison.

Shared precedence, from lowest to highest, is:

1. built-in lowest-point defaults
2. input global policy preset
3. explicit input global lead and response policies
4. input-activated profile-derived side policies
5. explicit input side lead and response policies
6. global CLI policy preset
7. CLI-activated profile-derived side policies
8. explicit global CLI lead and response policies
9. explicit side-specific CLI lead and response policies

Global presets and global lead/response policies cascade to both `left` and `right`.
Profile-derived policies and side-specific overrides affect only their side.

Response-policy activation is tracked separately from complete effective side settings.
Presets, response policies, and enabled profile presets activate the sparse response map;
lead-only policy sources do not. When the sparse map is absent, immediate analysis and
multi-step candidate completion keep the legacy basic or random opponent response
behavior selected by `use_basic_opponent_strategy`.

Immediate candidate analysis does not simulate an opponent lead and only runs for
local-action phases. It starts with the local candidate card and applies the
activated response map only to the remaining acting opponents. Multi-step
opponent-turn preparation uses the effective left/right
lead and response settings. Multi-step candidate completion and policy comparison
receive the same activated response map as immediate analysis.

`opponent_policy.py` contains the shared card-selection helpers used by these paths.

## Analysis and recommendation

| File                                | Purpose                                     |
| ----------------------------------- | ------------------------------------------- |
| `src/skat_ai/analysis_report.py`    | Card analysis report construction.          |
| `src/skat_ai/card_selection.py`     | Card selection helpers.                     |
| `src/skat_ai/recommender.py`        | Recommendation and strategic summary logic. |
| `src/skat_ai/policy_comparison.py`  | Policy comparison logic.                    |
| `src/skat_ai/analysis_metadata.py`  | Analysis-mode and metadata handling.        |
| `src/skat_ai/strategic_metadata.py` | Strategic metadata helpers.                 |

The analysis report is the basis for recommendations, post-game comparison, and several CLI/JSON summaries when a local decision is available. Opponent-turn and ended-game positions intentionally use an empty report.

Suit and Grand candidate ranking uses expected local card-point swing. Null
candidate ranking uses an internal contract-objective utility: local declarers
prefer avoiding declarer-won evaluated tricks, while local defenders prefer
making the concrete declarer win an evaluated trick. Public point fields remain
card-point metrics.

## Post-game review

| File                              | Purpose                                                                                                                      |
| --------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `src/skat_ai/post_game_review.py` | Actual-card comparison, decision quality classification, decision factors, explanation text, and recommendation gap details. |

Post-game review uses the regular analysis report and optionally compares it with `actual_card_played`. If Immediate Analysis is unavailable because there is no current local decision, post-game review returns an unavailable summary instead of comparing against an empty report.

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
