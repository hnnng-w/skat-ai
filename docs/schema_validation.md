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

Its alternative `historical_game_input`, `training_dataset_input`,
`opponent_statistics_input`, `fixed_three_player_historical_list_input`, and
`fixed_three_player_historical_list_comparison_input` branches reference focused
versioned schemas. The
validation script registers the focused historical, shortening, continuation,
training-dataset, partition-policy, opponent-statistics, and all five fixed-list
schemas locally; it does not fetch schema definitions over the network.

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
* the three recommendation methods and strict complete bounded-Search settings object
* Search-only flat live/post-game, not-ended, actual-card, attributed-history, and workflow constraints
* optional exact `public_declarer_cards` card-array structure for declared Ouvert
* top-level and optional nested `game_declaration` declaration field types
* strict version-1 declarer-concession, defender-concession, and declarer-card-exposure union shapes
* strict version-1 continuation union with declarer-exposure responses and cards or defender-open-play response, exposing defender, and returned public hand
* complete historical-game player, deal, declaration, discard, normal or shortened trick shapes, and one optional continuation before normal completion or one terminal shortening
* training dataset versions, record/provenance shapes, partition values, optional partition policy, and target
* opponent-statistics versions, identity, external or historical provenance, complete percentage fields, optional exact counts, and `0..100` bounds
* strict fixed-list request versions, canonical three-place players, exactly 36 Played Game or Passed Deal entries, explicit nullable lots, and comparison arrays of at least two sources

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
* optional `game_shortening_summary` through its strict focused schema
* optional `game_continuation_summary` through its strict focused schema
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
* optional live `opponent_profile_application_summary` through its focused schema
* `multi_step_result`, when Multi-Step simulation is requested
* `policy_comparison_result`, when policy comparison is requested
* optional `hidden_card_inference_summary` through its strict focused version-1 schema at position, Multi-Step, Policy Comparison, and historical-review decision locations
* optional `recommendation_method_summary` plus `bounded_search_result` through the registered strict standalone bounded-Search schema
* optional flat `bounded_search_post_game_review_summary` through its strict focused schema
* the separate `historical_game_summary` branch
* versioned historical game-end and non-terminal game-event unions plus declarer-concession, defender-concession, declarer-card-exposure, terminal defender-open-play, terminal open-card-throw, and both timed continuation input/output schemas
* optional versioned historical decision snapshots through the focused referenced schema
* optional versioned complete historical game review through its focused referenced schema
* optional versioned Historical Search Review through its strict focused schema
* optional versioned Historical Replay Coaching through its strict focused schema
* optional historical participant, temporal, per-decision policy, and aggregate profile application through its focused schema
* the separate versioned `training_dataset_summary` branch through its strict focused schema
* the separate versioned `opponent_statistics_summary` branch and referenced profile derivation through strict focused schemas
* the separate versioned `historical_opponent_statistics_aggregation_summary` branch through its strict focused schema
* the separate versioned `rolling_opponent_policy_evaluation_summary` branch through its strict focused schema
* the separate versioned `dataset_partition_audit_summary` branch through its strict focused schema
* the separate versioned `bounded_search_evaluation_summary` branch through its strict focused schema
* the complete versioned `fixed_three_player_historical_list_summary` branch through its strict focused aggregation schema
* the compact versioned `fixed_three_player_historical_list_comparison_summary` branch through its strict focused comparison schema

The published stable `v0.11.0` generated-output matrix covers 64 deterministic
scenarios and passes 4,392 pytest tests. The historical published `v0.10.0`
baseline passes 4,075 pytest tests and covers 59 scenarios. The historical
published `v0.9.0` baseline passes 3,558 pytest tests and covers 52 scenarios. Position
scenarios use CLI settings such as `--samples 20` and `--seed 42`, plus
scenario-specific mode arguments where needed. Historical-game scenarios,
including all five shortened kinds, omit position-only overrides. It is separate from input-example schema validation: input validation
checks the example JSON files, while generated-output validation checks the
production JSON output emitted from those inputs.

The current Issue #130 development matrix appends three deterministic list
scenarios to those unchanged 64 and therefore validates 67 outputs: mixed list
with an applied lot, all-Passed-Deal list with an unresolved three-player tie,
and compact independent comparison with changed table places, disjoint Game IDs,
different Passed Deal counts, and resolved ranks.

The scenario matrix is intentionally bounded. It covers representative
user-facing CLI workflows, including explicit-input live recommendation, JSON
output writing, quiet JSON-output automation, local and opponent-turn Multi-Step
simulation, policy comparison, one shared-root coherent hidden-world Policy
Comparison, comparison-only policy output, side-specific
opponent policies, completed-game settlement/rating, post-game review,
Null-objective post-game review, defender-perspective post-game review,
legacy claim, all five structured shortening kinds including accepted declarer
card exposure, exact defender open play, and open card throw, both ongoing public-hand continuations,
overbid, and list-performance summaries from aggregated totals, normalized
game contributions, and local analysis results, fixed three-player standings
summaries, late-game history-heavy live input, and local defender redaction for
`known_to_declarer` Skat visibility, plus complete normal-play historical-game
validation, settlement, information-safe decision snapshots, one seeded
30-decision ordinary historical game review, one seeded 30-decision declared-
Ouvert historical review with exact public ownership, one versioned two-record/60-sample training
dataset, one 14-sample variable-length concession dataset,
one exact-prefix unanimously accepted historical declarer-card-exposure result,
one bounded exact historical defender-open-play result,
one timed historical visibility transition for each continuation kind, two
bounded continuation-then-terminal chains with post-event and same-boundary
chronology,
one versioned external opponent-statistics conversion, and one seeded live
external-profile binding with distinct left/right presets, plus one seeded
time-safe historical external-profile review, and one exact historical
opponent-statistics aggregation with strict selection and standalone export,
and one rolling as-of opponent-policy evaluation with baseline-only low-
confidence coverage, plus one exact stable-player dataset-partition audit.
It also covers flat bounded-Search post-game comparison, Historical Search Review
with eligible and unavailable decisions, and bounded-Search dataset evaluation
with default validation/test partitions and a deterministic one-decision cap.
Three public Replay Coaching scenarios cover normal Grand with Key Decisions,
Turning Points, and recommendations; normal Null without card-point-margin
advice; and a continuation before terminal shortening with snapshot output.
The additional hidden-card inference scenario uses
`examples/grand_hidden_card_inference.json` with two Multi-Step decisions. It
semantically verifies the exact root count `275275`, a confirmed right-player
Grand clubs void, exact ownership marginals, shared root evidence, later visible
simulated evidence progression, compatible coherent ownership, uncalibrated
confidence, and privacy-safe output.
The additional rolling scenario uses a normal source, a zero-play concession
source, and a 14-decision concession target. Its schema permits empty target
decision arrays, zero overall decisions, null zero-denominator rates, and
participant-based target-player coverage without a version increment.

Two additional deterministic position scenarios cover one complete exhaustive
live bounded Search recommendation and one structural node-budget auto fallback.
They verify method-summary relationships, report separation, independent seeds,
fallback metadata, standalone-schema registration, and absence of private Search
state. Prior generated scenarios remain unchanged because omitted methods emit no
new fields.

Two further deterministic scenarios cover Search-aware Multi-Step execution and
Search-inclusive Policy Comparison. The schema references the standalone bounded-
Search result instead of duplicating it, rejects private or unknown decision
properties, distinguishes executed and stopped decisions, constrains strict and
auto fallback shapes, validates Search-only summary fields and compact ordered
comparison diagnostics, and permits a null recommended policy. Runtime
validation remains authoritative for card identity, count arithmetic, per-
decision budget equality, eligibility selection, and public/coherent-world
separation.

The coherent-world scenario uses
`examples/grand_coherent_hidden_world.json`, three Multi-Step steps,
`highest_expected_value`, and all four compared card-selection policies. It
semantically verifies one shared root, equal independent policy-path worlds,
owner-aware count reconciliation, a fixed hypothetical skat, no resampling, and
the absence of private hidden-card fields.

`schemas/hidden_card_inference_summary.schema.json` defines the strict version-1
summary and is referenced by position, Multi-Step, Policy Comparison, and
historical-review output. It fixes evidence and confidence enums, `0.85` and
`0.65` thresholds, exact compatible-world metadata, and all privacy flags.
Runtime validation remains authoritative for attributed chronology, effective-
category follow evidence, exact-hand contradictions, compatible assignment
existence, DP counts and marginals, and uniform sampling semantics.

`schemas/bounded_search_result.schema.json` is registered locally and referenced
from `schemas/output.schema.json`; its structure is not duplicated there. The
position output schema separately validates requested/effective method,
Search-attempt, fallback, report-method, normalized-settings, and null-versus-
object relationships. It also rejects explicit-method settings without a method
summary, nonempty Immediate reports for report method `none`, incompatible
top-level recommendation nullability, and disagreement between workflow and
Search-result fallback markers. Runtime validation remains authoritative for
budget cross-field limits and request/result equality, attributed history, flat
live/post-game workflow eligibility, contextual Search method and game type, top-level
effective-card identity, and fallback execution.

`schemas/bounded_search_post_game_review.schema.json`,
`schemas/historical_search_review.schema.json`, and
`schemas/bounded_search_evaluation.schema.json` are also Draft 2020-12 strict
schemas registered locally. They recursively reject unknown and private fields,
constrain methods, profiles, statuses, coverage, relations, ranks, rates, counts,
Null margin nullability, records, and breakdown structures, and reference the
standalone bounded-Search result rather than duplicating it. Runtime tests remain
authoritative for aggregate arithmetic, profile-to-budget identity, stable global
prefix selection, derived seed rules and non-serialization, shared-prefix
information safety, and zero-decision record preservation.

`schemas/historical_replay_coaching.schema.json` is a separate Draft 2020-12
strict schema registered locally and referenced optionally from
`historical_game_summary`. It fixes the report/method/policy constants and the
complete context, assessment, prioritization, guidance, coverage, scope-summary,
outcome, and limitation shapes. Runtime validation remains authoritative for
cross-object identity and count reconciliation, one-pass Search/Immediate reuse,
recursive private-field rejection, Null wording, and non-causal/non-rating
claims.

The five fixed-list schemas are separate strict Draft 2020-12 resources and are
registered locally with no network resolution. The source schema references the
existing Historical Game schema; request schemas reference the source rather
than duplicating it; root input and output schemas reference all new standalone
contracts. Aggregation output recursively rejects unknown fields across Entry
Facts, contributions, cumulative totals, progression, and standings. Comparison
output recursively rejects unknown fields across compact sources, all fourteen
deltas, rank status, and nullable rank fields, and references aggregation player
totals rather than duplicating that shape. Python remains authoritative for
identity, rotation, chronology, settlement, tie, independence, alignment,
arithmetic, and relational reconciliation.

The output schema is intentionally not a fully strict representation of every
nested analysis detail, but stable branch contracts such as
`post_game_review_summary`, `multi_step_result`, and
`policy_comparison_result` are explicitly structured. Structured game shortening
uses `schemas/game_shortening.schema.json`; its summary and settlement basis use
`schemas/declarer_concession_output.schema.json` or
`schemas/defender_concession_output.schema.json`,
`schemas/declarer_card_exposure_output.schema.json`,
`schemas/defender_open_play_output.schema.json`, or
`schemas/open_card_throw_output.schema.json`. Open card throw also uses
`schemas/open_card_throw.schema.json` and
`schemas/theoretical_level_assessment.schema.json`; runtime validation remains
authoritative for party derivation, complete-hand and turn reconciliation,
assignment, preexisting decisions, jack-only exclusion, settlement, and privacy.
Defender open play also uses
`schemas/defender_open_play.schema.json` and the referenced
`schemas/exact_rest_trick_proof.schema.json`; runtime validation remains
authoritative for exact card accounting, party membership, turn phase, the
five-trick bound, adjudication, and private-hand protection.
Flat ongoing continuation uses the two-member
`schemas/game_continuation.schema.json` union, the focused declarer- and
defender-open-play continuation schemas, their focused output schemas, and
`schemas/public_hand_constraint.schema.json`. Runtime validation remains
authoritative for party membership, response semantics, exact current-hand and
turn reconciliation, workflow exclusivity, information authorization, and
known-card path continuity. Historical continuation additionally uses the
version-1 `historical_game_event` union and focused event/output schemas. Neither
timed continuation invokes solver proof, assignment, or settlement; runtime
replay verifies the exact event boundary, owner-only hand shrinkage, and exact
final public hand. A later terminal shortening reuses its existing input and
output schema and adjudicator; all historical and event schema versions remain
`1`.
Declared Ouvert reuses the public-hand constraint schema with source
`declared_ouvert`. Runtime validation is authoritative for concrete declarer
identity, local-hand equality, opponent hand size, known-card contradictions,
multi-source deduplication, disjoint ownership, and canonical output.
Historical decision
snapshots use `schemas/historical_decision_snapshot.schema.json`, referenced by
the public output schema. Complete historical review uses
`schemas/historical_game_review.schema.json`. Training dataset output uses
`schemas/training_dataset_output.schema.json`. Opponent statistics use
`schemas/opponent_statistics_output.schema.json`, which references
`schemas/opponent_profile_derivation.schema.json`. Historical aggregation uses
`schemas/historical_opponent_statistics_aggregation.schema.json`. The local
rolling evaluation uses
`schemas/rolling_opponent_policy_evaluation.schema.json`. Partition audit uses
`schemas/dataset_partition_audit.schema.json`, which references
`schemas/dataset_partition_policy.schema.json`. The local
validator registry also loads the live and historical profile-application
schemas. Runtime validation and tests enforce identity lookup, strict instant
ordering, source/policy precedence, temporal reconciliation,
recommendation-consistency, and information-leakage semantics
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
* legacy claim/concession assignment and structured declarer-concession consent
* defender-concession concrete party membership and joint liability
* declarer-card-exposure form, exact defender unanimity, and shown-player membership
* exposed-card notation, uniqueness, count, ownership, and exact-hand reconciliation
* reliable declarer hand-count reconciliation and structured incomplete-play exclusivity
* defender pre-concession decision, mandatory-level feasibility, and Null trick ownership
* prevention of remaining-point assignment and separation of accepted claimed from achieved levels
* game-type-specific declaration rules
* top-level-versus-nested declaration precedence
* Null declaration restrictions such as rejecting `matadors`, Schneider
  announced, or Schwarz announced on Null games
* completed Null and Schwarz settlement reliability requirements
* how profile-derived opponent policy presets are selected from validated profile fields
* exact and estimated profile-evidence precedence and count/rate consistency
* scoped heuristic confidence boundaries and signal actionability
* aggressive-over-defender conflict precedence and output reconciliation
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
* whether Historical Search and Immediate run before the observed card is introduced
* whether historical Search seeds use the stable domain, game ID, and decision index and remain non-serialized
* whether Search status, coverage, availability, recommendation, agreement, quality, and performance counts reconcile
* whether the bounded-Search evaluation cap is one stable global prefix while preserving zero-decision records
* whether named Search profiles serialize their exact immutable requested budgets
* duplicate opponent-statistics player identities
* RFC 3339 capture-time time-zone requirements and finite percentage values
* inclusive `98..102` role and contract-distribution sums
* zero-role dependent-percentage rules
* deterministic percentage-point normalization and null or exact role-specific counts
* exact-count integer invariants and percentage reconciliation
* historical source-player, identifier-array, timestamp, and `captured_at` reconciliation
* opponent-statistics derivation reconciliation and absence of policy application, recommendations, or simulation
* canonical historical aggregation partition selection and strict temporal cutoff
* `played_at` presence on every partition-selected aggregation source game
* stable case-sensitive player aggregation, first-appearance order, and label conflict handling
* settlement-based declarer/defender wins, including overbid loss and wins for both defenders
* aggregation/source count reconciliation and absence of training samples

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
