# Schema validation

This document explains how JSON Schema validation is used in `skat-ai`.

## Validation layers

The project uses multiple validation layers.

| Layer | Purpose |
|---|---|
| JSON Schema | Checks stable JSON structure, required fields, basic types, enums, and simple size limits. |
| Python input validation | Checks Skat-specific cross-field rules and gameplay consistency. |
| Pytest regression tests | Verifies behavior, outputs, examples, and edge cases. |

These layers are complementary. JSON Schema does not replace Python validation.

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

The project check script also runs this validation.

The input schema checks things such as:

- required top-level input fields
- valid card notation
- known `game_type` values
- known player and position values
- maximum hand size
- maximum skat size
- maximum current-trick size
- unique cards within individual card arrays
- point fields between 0 and 120
- supported `game_end_reason` values
- supported `performance_rating_system` values

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

The project check script also runs this validation.

The output schema checks the main output structure, including:

- `game_declaration`
- `game_value_summary`
- `overbid_summary`
- `score_summary`
- `game_result_summary`
- `adjusted_game_result_summary`
- `final_settlement_summary`
- `performance_rating_summary`
- `recommendation`

The output schema is intentionally not a fully strict representation of every nested analysis detail.

## Why additionalProperties is still allowed

Some schema objects use:

```json
"additionalProperties": true
```

This is intentional.

The project is still evolving, and many result objects contain metadata or nested analysis details that may change over time.

The schema is currently used as a stable documentation and compatibility layer, not as a full lock-down of every internal field.

## What JSON Schema does not validate

Some checks are intentionally handled by Python validation instead of JSON Schema.

Examples:

- duplicate cards across multiple known-card lists
- completed-trick sequence consistency
- whether a recorded `winner_player` actually won a trick
- whether `trick_leader` matches the previous trick winner
- whether `game_end_reason` is consistent with remaining card points
- whether known explicit points plus completed-trick points exceed 120
- overbid settlement support for Null games
- strategic live-vs-post-game information rules

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

- the example is invalid and should be fixed
- the schema is too strict and should be updated
- the field is intentionally new and should be documented

## Relationship to docs

The schema files are linked from:

- [`docs/input_json.md`](input_json.md)
- [`docs/output_json.md`](output_json.md)

The human-readable docs explain the meaning of fields. The schema files provide machine-readable structure.