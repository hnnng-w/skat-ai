# Schema validation

This document explains how JSON Schema validation is used in `skat-ai`.

## Validation layers

The project uses multiple validation layers.

| Layer                   | Purpose                                                                                    |
| ----------------------- | ------------------------------------------------------------------------------------------ |
| JSON Schema             | Checks stable JSON structure, required fields, basic types, enums, and simple size limits. |
| Python input validation | Checks Skat-specific cross-field rules and gameplay consistency.                           |
| Pytest regression tests | Verifies behavior, outputs, examples, and edge cases.                                      |

These layers are complementary.

JSON Schema does not replace Python validation.

## Input schema

The input schema is located at:

```text
schemas/input.schema.json
```

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
* valid card notation
* known `game_type` values
* known player and position values
* maximum hand size
* maximum skat size
* maximum current-trick size
* unique cards within individual card arrays
* point fields between 0 and 120
* supported `analysis_mode` values
* supported `skat_visibility` values
* supported `game_end_reason` values
* supported `performance_rating_system` values
* supported opponent policy values
* basic `actual_card_played` type and card notation

## Output schema

The output schema is located at:

```text
schemas/output.schema.json
```

It validates generated outputs for selected example files.

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
* `recommendation`
* `post_game_review_summary`
* `information_policy_summary`
* `opponent_policy_settings`
* `left_opponent_policy_settings`
* `right_opponent_policy_settings`

The output schema is intentionally not a fully strict representation of every nested analysis detail.

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
* completed-trick sequence consistency
* whether a recorded `winner_player` actually won a trick
* whether `trick_leader` matches the previous trick winner
* whether `game_end_reason` is consistent with remaining card points
* whether known explicit points plus completed-trick points exceed 120
* whether `actual_card_played` is in the player's hand
* whether `actual_card_played` is legal in the analyzed position
* whether known skat cards are allowed in the selected `analysis_mode`
* whether ended game states are allowed in `live_decision`
* overbid settlement support for Null games
* strategic live-vs-post-game information rules
* whether matadors can be inferred from the currently known declarer-card context

These checks require cross-field or Skat-specific logic and are easier to test and maintain in Python.

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