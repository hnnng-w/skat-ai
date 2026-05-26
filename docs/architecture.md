# Architecture

This document describes the project structure and main modules.

## Main entry point

| File | Purpose |
|---|---|
| `main.py` | CLI entry point, orchestration, output construction, multi-step execution, and optional policy comparison. |

## Core rules

| File | Purpose |
|---|---|
| `src/skat_ai/rules.py` | Card notation, card points, trump logic, legal-card logic, trick winner logic. |

The internal card-strength values in `rules.py` are comparison values only. They are not Skat card points and must not be used for scoring.

## Input loading and validation

| File | Purpose |
|---|---|
| `src/skat_ai/input_loader.py` | Loads JSON input and converts it into internal structures. |
| `src/skat_ai/input_validation.py` | Validates input fields, cards, metadata, points, game-end consistency, and rating-system metadata. |
| `src/skat_ai/known_cards.py` | Tracks and validates known cards. |

## Game history

| File | Purpose |
|---|---|
| `src/skat_ai/game_history.py` | Completed-trick structure, sequence, role, and rule-winner validation. |

## Game value and result

| File | Purpose |
|---|---|
| `src/skat_ai/game_declaration.py` | Game declaration metadata and serialization. |
| `src/skat_ai/game_value.py` | Game value calculation for suit, grand, and null games. |
| `src/skat_ai/game_result.py` | Raw card-point result, winner, remaining points, Schneider/Schwarz status. |
| `src/skat_ai/score.py` | Known point summary from explicit points and completed tricks. |

## Game end and settlement

| File | Purpose |
|---|---|
| `src/skat_ai/game_end.py` | Game-end reason handling and remaining-point assignment for claim/concession scenarios. |
| `src/skat_ai/overbid.py` | Bid-value comparison, overbid detection, and required game-value calculation. |
| `src/skat_ai/final_settlement.py` | Simplified single-game settlement scoring, including supported Suit/Grand overbid loss handling. |
| `src/skat_ai/performance_rating.py` | Performance-rating layer, partial fixed-three-player ISkO single-game rating, and separation from settlement. |

## Simulation

| File | Purpose |
|---|---|
| `src/skat_ai/simulation.py` | Monte Carlo simulation logic. |
| `src/skat_ai/simulation_context.py` | Simulation context creation. |
| `src/skat_ai/simulation_step.py` | Single simulation-step handling. |
| `src/skat_ai/state_transition.py` | Applies card plays and transitions game state. |
| `src/skat_ai/multi_step_simulation.py` | Multi-step simulation orchestration. |
| `src/skat_ai/multi_step_summary.py` | Serializable multi-step result summaries. |

## Opponent modeling

| File | Purpose |
|---|---|
| `src/skat_ai/opponent_policy.py` | Opponent policy definitions and selection logic. |
| `src/skat_ai/opponent_lead.py` | Opponent lead behavior. |
| `src/skat_ai/opponent_sequence.py` | Opponent play sequencing. |
| `src/skat_ai/opponent_policy_preset.py` | Named policy presets. |
| `src/skat_ai/opponent_profile_policy.py` | Profile-based policy recommendation. |
| `src/skat_ai/player_profile.py` | Player profile modeling. |

## Analysis and recommendation

| File | Purpose |
|---|---|
| `src/skat_ai/analysis_report.py` | Card analysis report construction. |
| `src/skat_ai/card_selection.py` | Card selection helpers. |
| `src/skat_ai/recommender.py` | Recommendation and strategic summary logic. |
| `src/skat_ai/policy_comparison.py` | Policy comparison logic. |
| `src/skat_ai/analysis_metadata.py` | Analysis-mode and metadata handling. |
| `src/skat_ai/strategic_metadata.py` | Strategic metadata helpers. |

## Output

| File | Purpose |
|---|---|
| `src/skat_ai/output_writer.py` | Writes JSON output. |
| `src/skat_ai/result_serialization.py` | Serialization helpers. |

## Tests

Tests are organized by module and behavior in `tests/`.

Important regression areas:

- rules and legal-card logic
- completed-trick validation
- game value and final settlement
- game-end handling
- overbid handling
- performance rating
- example files
- CLI result structure
- multi-step simulation
- opponent policies