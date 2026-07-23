# Schema validation

This document explains how JSON Schema validation is used in `skat-ai`.

## Validation layers

The project uses multiple validation layers.

| Layer                   | Purpose                                                                                    |
| ----------------------- | ------------------------------------------------------------------------------------------ |
| JSON Schema             | Checks stable JSON structure, required fields, primitive types, canonical enums, object and array shapes, and simple size limits. |
| Python input validation | Checks Skat-specific cross-field rules, gameplay consistency, phase-specific rules, and settlement reliability requirements.      |
| Pytest regression tests | Verifies behavior, outputs, examples, and edge cases.                                      |

These layers are complementary.

JSON Schema does not replace Python validation.

Passing JSON Schema validation does not guarantee that the input describes a legal Skat state.

## Input schema

The input schema is located at:

```text
schemas/input.schema.json
```

Its alternative `historical_game_input`, `training_dataset_input`, and
`opponent_statistics_input` branches reference focused versioned schemas. The
validation script registers `schemas/historical_game.schema.json`,
`schemas/training_dataset.schema.json`, and
`schemas/opponent_statistics.schema.json` locally; it does not fetch schema
definitions over the network.

It validates example input files in `examples/`.

Run:

```powershell
python scripts/validate_examples_schema.py
```

The project check script also runs this validation:

```powershell
.\scripts\check.ps1
```

The input schema checks things such as:

* required top-level input fields
* stable required nested fields, such as completed-trick `cards` and `winner_role`
* valid card notation
* known `game_type` values
* known player and position values
* concrete declarer identity and supported role/identity combinations
* basic object and array shapes
* maximum hand size
* maximum skat size
* maximum current-trick size
* maximum opponent hand sizes and sample count
* unique cards within individual card arrays
* exact completed-trick card counts and player counts
* point fields between 0 and 120
* supported `analysis_mode` values
* supported `skat_visibility` values
* supported `game_end_reason` values
* supported `left_player_profile` and `right_player_profile` field types and numeric ranges
* supported `performance_rating_system` values
* optional `rated_player_id` and `game_id` primitive shapes for per-game list inputs
* fixed three-player `list_standings_input` structure
* canonical opponent policy and policy-preset values
* basic `actual_card_played` type and card notation
* top-level and optional nested `game_declaration` declaration field types
* complete historical-game player, deal, declaration, discard, and ten-trick shapes
* training dataset versions, record/provenance shapes, partition values, and target
* external opponent-statistics versions, identity, provenance, complete percentage fields, and `0..100` bounds

Runtime input validation mirrors selected public schema bounds and shapes so
direct Python callers receive stable `ValueError` failures for malformed public
input. This includes non-null array checks for card-array fields, max hand and
Skat lengths, non-negative opponent hand sizes, max opponent hand sizes,
max `sample_count`, player-profile object
shapes, and unsupported keys in `completed_tricks` entries. The runtime still
does not execute the full JSON Schema during loading.

## Output schema

The output schema is located at:

```text
schemas/output.schema.json
```

It validates generated outputs from an explicit deterministic scenario matrix.
Each scenario invokes the real CLI and output writer, writes a temporary output
file, parses that generated file, checks the scenario-specific output branch,
and validates the result against `schemas/output.schema.json`.

Run:

```powershell
python scripts/validate_generated_outputs_schema.py
```

The project check script also runs this validation:

```powershell
.\scripts\check.ps1
```

The output schema checks the main output structure, including:

* `game_declaration`
* `game_value_summary`
* `overbid_summary`
* `score_summary`
* `game_result_summary`
* `adjusted_game_result_summary`
* `final_settlement_summary`
* `performance_rating_summary`
* `list_performance_summary`, when a single-rated-player list performance input mode is supplied
* `list_standings_summary`, when fixed three-player standings input is supplied
* `recommendation`
* `post_game_review_summary`
* `information_policy_summary`
* `opponent_policy_settings`
* `left_opponent_policy_settings`
* `right_opponent_policy_settings`
* `profile_preset_settings`
* `multi_step_result`, when Multi-Step simulation is requested
* `policy_comparison_result`, when policy comparison is requested
* the separate `historical_game_summary` branch
* optional versioned historical decision snapshots through the focused referenced schema
* optional versioned complete historical game review through its focused referenced schema
* the separate versioned `training_dataset_summary` branch through its strict focused schema
* the separate versioned `opponent_statistics_summary` branch through its strict focused schema

Generated-output validation covers 28 deterministic scenarios. Position
scenarios use CLI settings such as `--samples 20` and `--seed 42`, plus
scenario-specific mode arguments where needed. The historical-game scenario
omits position-only overrides. It is separate from input-example schema validation: input validation
checks the example JSON files, while generated-output validation checks the
production JSON output emitted from those inputs.

The scenario matrix is intentionally bounded. It covers representative
user-facing CLI workflows, including explicit-input live recommendation, JSON
output writing, quiet JSON-output automation, local and opponent-turn Multi-Step
simulation, policy comparison, comparison-only policy output, side-specific
opponent policies, completed-game settlement/rating, post-game review,
Null-objective post-game review, defender-perspective post-game review,
claim/overbid/list-performance summaries from aggregated totals, normalized
game contributions, and local analysis results, fixed three-player standings
summaries, late-game history-heavy live input, and local defender redaction for
`known_to_declarer` Skat visibility, plus complete normal-play historical-game
validation, settlement, information-safe decision snapshots, one seeded
30-decision historical game review, one versioned 30-sample training dataset,
and one versioned external opponent-statistics conversion.

The output schema is intentionally not a fully strict representation of every
nested analysis detail, but stable branch contracts such as
`post_game_review_summary`, `multi_step_result`, and
`policy_comparison_result` are explicitly structured. Historical decision
snapshots use `schemas/historical_decision_snapshot.schema.json`, referenced by
the public output schema. Complete historical review uses
`schemas/historical_game_review.schema.json`. Training dataset output uses
`schemas/training_dataset_output.schema.json`. Opponent statistics use
`schemas/opponent_statistics_output.schema.json`. The local validator registry
loads the focused schemas; runtime validation and tests enforce temporal,
reconciliation, recommendation-consistency, and information-leakage semantics
that JSON Schema cannot express.

## Post-game review schema coverage

`post_game_review_summary` is schema-validated because it is part of the stable output contract.

The schema covers:

* availability fields
* actual and recommended cards
* expected point swing values
* decision quality
* decision factors
* decision explanation
* recommendation gap details
* candidate counts and ranks

Important fields include:

* `decision_quality`
* `decision_factors`
* `decision_explanation`
* `actual_card_rank`
* `recommended_card_rank`
* `candidate_count`
* `better_card_count`

Generated-output validation includes representative available review scenarios
for normal Suit/Grand review, Null contract-objective review, and local
defender-perspective review. Focused pytest example invariants cover the clear
mistake and acceptable-alternative example outcomes.

## Why additionalProperties may still be allowed

Some schema objects use:

```json
"additionalProperties": true
```

This is intentional.

The project is still evolving, and many result objects contain metadata or nested analysis details that may change over time.

The schema is currently used as a stable documentation and compatibility layer, not as a full lock-down of every internal field.

Some stable summary objects are stricter and may use:

```json
"additionalProperties": false
```

This is useful for output areas that should remain predictable, such as selected summary blocks.

## What JSON Schema does not validate

Some checks are intentionally handled by Python validation instead of JSON Schema.

Examples:

* duplicate cards across multiple known-card lists
* card uniqueness across hand, skat, current trick, played cards, and completed tricks
* completed-trick sequence consistency
* completed-trick player seating order
* whether completed-trick `winner_player` is included in `players`
* whether a recorded `winner_player` actually won a trick
* whether a recorded `winner_role` matches the rule-derived winner side when `cards`, `players`, and declarer identity are known
* whether completed-trick `winner_role` matches the local declarer or defender identity
* whether `trick_leader` matches the previous trick winner
* legal current-turn state and phase-specific hand sizes
* whether `game_end_reason` is consistent with remaining card points
* whether known explicit points plus completed-trick points exceed 120
* whether `actual_card_played` is in the player's hand
* whether `actual_card_played` is legal in the analyzed position
* whether known skat cards are allowed in the selected `analysis_mode`
* whether ended game states are allowed in `live_decision`
* claim and concession semantics
* game-type-specific declaration rules
* top-level-versus-nested declaration precedence
* Null declaration restrictions such as rejecting `matadors`, Schneider
  announced, or Schwarz announced on Null games
* completed Null and Schwarz settlement reliability requirements
* how profile-derived opponent policy presets are selected from validated profile fields
* overbid settlement support for Null games
* strategic live-vs-post-game information rules
* whether matadors can be inferred from the currently known declarer-card context and conservative concrete-declarer completed-trick ownership facts
* whether per-game list entries consistently describe one supplied `rated_player_id`
* whether supplied per-game list `game_id` values are unique
* whether fixed three-player standings player IDs are unique
* whether standings declarer player IDs reference declared standings players
* whether historical review totals reconcile with all decision and player rows
* whether each reviewed actual card and recommendation is legal and represented exactly once
* whether decision seeds follow the base-seed derivation rule
* whether hidden hands, future plays, final results, overbid, or settlement influence an earlier historical review
* duplicate training record, game, and complete source identities
* cross-partition game and source leakage
* exact sample-ID derivation and record/partition/total count reconciliation
* relative-only feature player references and absence of stable identities
* whether each training label is the legal pre-play historical actual card
* whether future plays, final outcomes, settlement, recommendations, or review quality leak into training features or labels
* duplicate opponent-statistics player identities
* RFC 3339 capture-time time-zone requirements and finite percentage values
* inclusive `98..102` role and contract-distribution sums
* zero-role dependent-percentage rules
* deterministic percentage-point normalization and null role-specific counts
* opponent-statistics output reconciliation and absence of confidence or policy derivation

These checks require cross-field or Skat-specific logic and are easier to test and maintain in Python.

For list aggregation metadata, JSON Schema validates only that optional
`rated_player_id` and `game_id` fields are strings with at least one character.
Python validation rejects whitespace-only identifiers, leading or trailing
whitespace, partial `rated_player_id` presence, conflicting `rated_player_id`
values, and duplicate supplied `game_id` values. Passing schema validation does
not prove list-level identity consistency.

For `list_standings_input`, JSON Schema validates the stable object structure,
exact three-player array size, required game fields, supported outcomes, and
settlement-score sign bounds. Python validation rejects duplicate player IDs,
unknown declarer player IDs, whitespace-padded identifiers and labels, and
duplicate supplied `game_id` values.

## Adding new examples

When adding a new file to `examples/`:

1. Keep it valid JSON.
2. Run input schema validation:

```powershell
python scripts/validate_examples_schema.py
```

3. Run generated-output schema validation:

```powershell
python scripts/validate_generated_outputs_schema.py
```

4. Run the full project check:

```powershell
.\scripts\check.ps1
```

If schema validation fails, decide whether:

* the example is invalid and should be fixed
* the schema is too strict and should be updated
* the field is intentionally new and should be documented
* generated output changed intentionally and the output schema should be updated

## Adding new output fields

When adding a new stable output field:

1. Add or update the producing code.
2. Add focused tests for the field.
3. Update `schemas/output.schema.json` if the field belongs to a schema-validated summary object.
4. Update `docs/output_json.md`.
5. Update any relevant topic-specific docs.
6. Run generated-output schema validation.
7. Run the full check script.

For experimental or unstable nested analysis fields, it may be better to leave them in a schema area with `additionalProperties: true` until the structure stabilizes.

## Relationship to docs

The schema files are linked from:

* [`docs/input_json.md`](input_json.md)
* [`docs/output_json.md`](output_json.md)

The human-readable docs explain the meaning of fields.

The schema files provide machine-readable structure.
