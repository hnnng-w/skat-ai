# Architecture

This document describes the project structure and main modules.

## Overview

`skat-ai` is organized as a small rule-based analysis engine around a JSON input/output workflow.

The position-analysis flow is:

1. Load and validate JSON input.
2. Build an internal game state.
3. Apply information-policy checks.
4. If the normalized current actor is the local player, analyze legal card choices.
5. Estimate expected point swings for available local decisions.
6. Build card recommendations or an unavailable Immediate Analysis shape.
7. Optionally run phase-aware multi-step simulation or policy comparison.
8. Build game-result, settlement, performance-rating, and post-game review summaries.
9. Serialize output for CLI and JSON use.

The alternative historical-game flow loads `historical_game_input`, builds a
stable-ID record, strictly replays ten tricks from complete playable hands,
derives points and ownership, reuses the declaration/value/overbid/settlement
helpers, and emits `historical_game_summary`.
When requested, the flow then derives 30 pre-play decision snapshots from that
validated replay result. Historical review adapts each snapshot independently
to the existing local state, runs the existing immediate recommendation once,
builds the candidate report from those values, and reuses post-game review.

The training-dataset flow validates dataset identity, provenance, partitions,
and duplicate protection, then reuses the historical validator/replay and
decision snapshot generator. It converts stable player references to the local
`me`/`left`/`right` model in features, keeps traceability identities in metadata,
and emits exactly 30 legal actual-card samples per record. It does not call the
recommender or simulation.

The opponent-statistics flow validates a versioned collection of external
percentage-point records, stable player identity, and required capture
provenance. It checks rounded source consistency and deterministically converts
percentages to `PlayerProfile` rate semantics while preserving source values and
leaving exact role-specific counts unknown. It calls the isolated profile
derivation module to expose unrounded role-evidence estimates, scoped heuristic
confidence, signals, classification, and preset metadata. It does not apply a
policy or call recommendation, historical, or simulation code.

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
| `src/skat_ai/historical_game.py`    | Typed stable-ID historical records, complete-deal validation, strict play replay, and historical result serialization. |
| `src/skat_ai/historical_decision_snapshot.py` | Typed information-safe pre-play snapshot reconstruction and serialization over a validated historical result. |
| `src/skat_ai/historical_snapshot_adapter.py` | Decision-time snapshot to local immediate-analysis position conversion. |
| `src/skat_ai/historical_game_review.py` | Historical decision evaluation, deterministic seeds, unavailable handling, and complete-game aggregation. |
| `src/skat_ai/training_dataset.py` | Typed dataset/provenance records, duplicate and partition validation, historical replay reuse, sample generation, and count reconciliation. |
| `src/skat_ai/training_feature_view.py` | Information-safe conversion from stable-ID snapshots to relative model-facing features. |
| `src/skat_ai/opponent_statistics.py` | Typed external statistics/provenance records, percentage validation, normalized profile conversion, and serialization. |
| `src/skat_ai/opponent_profile_derivation.py` | Typed versioned evidence, scoped confidence, signal, classification, and explanation derivation. |

Validation is split between JSON Schema and Python validation:

1. JSON Schema validates stable input/output structure.
2. Python validation handles Skat-specific cross-field rules.
3. Pytest covers behavior and regression scenarios.

## Game history

| File                          | Purpose                                                                |
| ----------------------------- | ---------------------------------------------------------------------- |
| `src/skat_ai/game_history.py` | Completed-trick structure, sequence, role, and rule-winner validation. |

Completed-trick validation is used to prevent inconsistent historical game states, duplicate cards, impossible sequences, and mismatched trick winners where enough information is available. When `cards` and ordered `players` are present, validation derives the rule winner and checks both `winner_player` and concrete `winner_role` metadata against that derived result. In live-decision input, supplied `winner_role` must be verifiable from `cards`, `players`, `game_type`, and concrete `declarer_player`; post-game legacy side-only histories remain supported when that evidence is absent.

Complete historical games do not use this local-perspective compatibility model.
`historical_game.py` preserves stable player IDs and fixed seats, validates all
three remaining hands at each play, and only projects derived
`declarer`/`defenders` ownership into the established scoring helpers.

## Game value and result

| File                               | Purpose                                                                                                   |
| ---------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `src/skat_ai/game_declaration.py`  | Game declaration metadata, default handling, matador inference integration, and serialization.            |
| `src/skat_ai/matador_inference.py` | Automatic matador inference from known declarer-card context where possible.                              |
| `src/skat_ai/game_value.py`        | Game value calculation for suit, grand, and null games.                                                   |
| `src/skat_ai/game_result.py`       | Raw card-point result, winner, remaining points, Schneider/Schwarz status, and adjusted result summaries. |
| `src/skat_ai/game_history.py`      | Known point summary from explicit points and completed tricks.                                            |

Matador inference is intentionally conservative. It uses currently known declarer-card context and safe completed-trick ownership facts where `cards`, ordered `players`, and concrete `declarer_player` identify who played each card. It does not infer ownership from `winner_role`, `winner_player`, trick winner, hidden cards, or sampled worlds, and it does not reconstruct every possible matador state from historical trick ownership.

The historical-game branch is stricter: its validated complete deal provides
deterministic declarer and non-declarer ownership for complete matador inference.
Historical decision snapshots do not reuse that final count. They infer only
from the acting player's own cards, legitimate non-Hand declarer skat knowledge,
prior public plays, and ouvert exposure, returning `null` when evidence is
insufficient.

## Game end and settlement

| File                                | Purpose                                                                                                       |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| `src/skat_ai/game_end.py`           | Game-end reason handling and remaining-point assignment for claim/concession scenarios.                       |
| `src/skat_ai/overbid.py`            | Bid-value comparison, overbid detection, and required game-value calculation.                                 |
| `src/skat_ai/final_settlement.py`   | Simplified single-game settlement scoring, including supported Suit/Grand overbid loss handling.              |
| `src/skat_ai/performance_rating.py` | Performance layer, partial fixed-three-player SkWO scoring, and separation from settlement. |

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
| `src/skat_ai/opponent_statistics.py`     | External statistics normalization and derivation serialization without policy application. |
| `src/skat_ai/opponent_profile_derivation.py` | Deterministic explainable profile derivation. |

Opponent policy handling supports both global and separate left/right opponent policy settings.

Profile derivation is deterministic and rule-based. Overall, declarer, and
defender evidence use the same unknown/low/medium/high heuristic bands at the
unavailable, `100`, and `500` boundaries, but every signal uses the confidence
of its own denominator. Exact role counts take precedence over unrounded rate
estimates. Actionable aggressive evidence precedes actionable defender evidence;
`simple_lowest` is never an actionable profile override. The combined legacy
left/right helper retains its established higher-overall-confidence and
aggressive tie fallback after each side has produced an actionable result.

When profile presets are enabled, actionable left and right player profiles can affect their respective effective left/right opponent response policies in immediate analysis and their effective left/right opponent policy settings in multi-step simulation. Explicit side-specific input and CLI overrides remain authoritative.

Some profile fields are currently behavioral-signal neutral even when they
provide evidence: `solo_win_rate`, `suit_game_rate`, and `null_game_rate`.

External opponent-statistics output includes the derivation but is not fed into
the policy-application flow. It does not change live, historical, or simulation
settings.

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
Actionable profile-derived policies and side-specific overrides affect only their side.

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

Historical review calls the same immediate recommender and builds the report
from its returned candidate values, avoiding a second simulation pass or a
second recommendation algorithm.

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

Complete historical review applies this same comparison independently to every
snapshot. Only stable player/declarer identity is read outside the snapshot for
relative mapping and player summaries. Prior review rows and final historical
result or settlement fields are never inputs to later or earlier decisions.
Ouvert snapshots bypass simulation because exposed opponent-card identities are
not supported by the current sampler.

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
| `schemas/historical_game.schema.json`          | Versioned complete historical-game input structure.                      |
| `schemas/historical_decision_snapshot.schema.json` | Versioned historical decision snapshot output structure.             |
| `schemas/historical_game_review.schema.json` | Versioned complete historical decision-review output structure.             |
| `schemas/training_dataset.schema.json`       | Versioned training dataset input, records, provenance, and partitions.      |
| `schemas/training_dataset_output.schema.json` | Strict training dataset output, metadata, features, labels, and counts.     |
| `schemas/opponent_statistics.schema.json` | Versioned external opponent-statistics input and provenance. |
| `schemas/opponent_statistics_output.schema.json` | Strict preserved-source and normalized-profile output. |
| `schemas/opponent_profile_derivation.schema.json` | Strict versioned confidence, signal, classification, preset, and explanation output. |
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
* historical snapshot adaptation, complete review, seeds, aggregation, and leakage control
* training dataset identities, provenance, partitions, duplicate leakage, deterministic samples, and feature safety
* opponent-statistics identity, provenance, percentages, normalization, explainable derivation, and workflow isolation
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
* Preserve the fixed three-player table; four-player support is unconditionally out of scope.

Requirements and rule-source ownership are mapped in
[Requirements traceability](requirements_traceability.md). The target product
boundary is defined in [v1.0 scope](v1_scope.md).
