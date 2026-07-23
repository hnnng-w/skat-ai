# Project handoff

This document summarizes the current state of `skat-ai` for continuing development in a new thread or with a new contributor.

## Project overview

`skat-ai` is a local Python-based Skat analysis and simulation tool.

The project focuses on:

* legal-card detection
* rule-based Skat position analysis
* Monte Carlo-style card analysis
* expected point swing estimation
* card recommendations
* multi-step simulation
* opponent policy modeling
* game result and settlement summaries
* automatic matador inference where supported by known declarer-card context and safe concrete-declarer completed-trick ownership
* post-game review support
* complete normal-play historical-game records
* information-safe historical decision snapshots and complete-game review
* versioned training and evaluation dataset records
* JSON input/output for regression-friendly testing

The project is not a machine-learning model, not a full official tournament system, and not a perfect-information Skat solver.

## Current development style

Development is milestone-based and test-driven. Each milestone is split into small parts.

Each part should:

* add one focused behavior or cleanup
* include tests
* keep existing behavior backward-compatible where possible
* run the full check script before manual review

The standard check command is:

```powershell
.\scripts\check.ps1
```

The project check currently covers:

* Ruff checks
* input JSON schema validation
* generated output JSON schema validation
* pytest regression tests

## Important assumptions

### Language

Repository code, tests, comments, docstrings, JSON keys, CLI output, and program output should remain in English.

Discussion and planning can be in German.

### Table size

The project assumes a fixed three-player Skat table.

Four-player table support is unconditionally out of scope.

### Performance rating

SkWO-style performance rating is partially implemented for fixed three-player single-game, local list-input, and explicit fixed three-player standings perspectives.

Series aggregation, tournament aggregation, and official report formats are not implemented yet.

### Live vs post-game mode

The project separates live decision analysis from post-game review.

`live_decision` is intended for in-game decisions and must not use post-game-only information.

`post_game_review` is intended for completed or retrospectively analyzed games.

## Major completed milestones

### Core rules and simulation

Implemented:

* card notation
* card points
* trump logic
* legal-card detection
* trick winner logic
* immediate trick simulation
* expected point swing calculation
* card recommendation

### Multi-step simulation

Implemented:

* sequential player-action simulation
* configurable card-selection policy
* strict simulation context checks
* policy comparison
* result serialization
* canonical turn-phase-aware opponent preparation
* supported preparation for empty left lead, empty right lead, and right response to an existing left lead
* deterministic `unsupported_turn_phase` stops for valid phases that do not prepare a current local decision

### Game history and scoring

Implemented:

* completed-trick structure validation
* completed-trick sequence validation
* completed-trick winner validation
* explicit and completed-trick point summaries
* game result summaries
* Schneider/Schwarz status summaries
* versioned complete normal-play historical-game records
* complete deal, pickup or Hand, discard, ownership, play-order, follow-rule, winner, point, and settlement replay validation

### Game declaration and settlement

Implemented:

* game declaration metadata
* canonical Suit and Grand declaration dependencies
* official Suit `1..11` and Grand `1..4` matador bounds
* game value summaries for suit, grand, and null games
* automatic matador inference from known declarer cards and safe concrete-declarer completed-trick ownership where possible
* final single-game settlement summary
* supported Suit/Grand overbid detection
* supported Suit/Grand overbid settlement loss handling
* bounded impossible Null settlement from an externally supplied Suit or Grand replacement

Known remaining areas:

* full official settlement nuance coverage is not complete
* impossible Null settlement remains incomplete when the external replacement selection or its required matadors are unavailable
* matador inference does not yet reconstruct completed-trick ownership beyond safe concrete `cards` and `players` facts

### Game-end handling

Implemented:

* normal completion
* declarer claims remaining tricks
* declarer concedes remaining tricks
* defenders concede remaining tricks
* impossible Null declaration ends the game immediately in post-game mode
* remaining-point assignment
* adjusted game-result summaries

### Performance rating

Implemented:

* `performance_rating_system`
* partial `isko_list` support
* fixed three-player table assumption
* single-game declarer rating score
* declarer rating points
* counterparty/defender rating points
* clear distinction between settlement score and rating score
* already aggregated list or series totals via `list_performance_input`
* normalized per-game list or series contributions via `list_game_contributions`
* local generated-output-style list inputs via `list_analysis_results`
* explicit fixed three-player list standings via `list_standings_input`
* SkWO 6.3.1 shared ranks for unresolved standings ties and optional external lot order

Not implemented:

* raw full-game list aggregation without explicit standings input
* series aggregation
* tournament aggregation
* official federation report formats

### JSON schema validation

Implemented:

* `schemas/input.schema.json`
* `schemas/output.schema.json`
* focused historical-game, historical-decision-snapshot, historical-game-review, and training-dataset schemas
* input example schema validation
* generated output schema validation
* schema validation documentation

Generated-output validation currently covers 27 deterministic scenarios.

### Live-vs-post-game information enforcement

Implemented:

* rejects `live_decision + known_post_game`
* rejects known skat cards in `live_decision`
* rejects ended game reasons in `live_decision`
* requires `post_game_review` for ended game reasons
* rejects complete 120-point game states in `live_decision`
* restricts unverifiable completed-trick winner metadata in `live_decision`
* adds `information_policy_summary` to output
* centralizes information policy in `information_policy.py`

### Left/right opponent policies

Implemented:

* global opponent policy settings remain backward-compatible
* normalized `left_opponent_policy_settings`
* normalized `right_opponent_policy_settings`
* left/right policy input fields
* left/right policy validation
* left/right CLI overrides
* centralized CLI policy choices via `VALID_OPPONENT_CARD_POLICIES`
* left/right settings in output
* left/right settings in multi-step serialization
* left/right settings threaded into multi-step simulation
* opponent lead uses the specific left/right lead policy
* right response uses `right_opponent_policy_settings` when left leads
* profile confidence derived from `games_played`
* profile-confidence conflict resolution for cautious/aggressive preset evidence
* left/right profile-derived presets applied to effective left/right multi-step policies
* explicit side-specific CLI policy overrides applied after profile-derived presets
* shared effective opponent-policy resolver used by immediate, multi-step, and policy-comparison paths
* configured response policies applied to immediate analysis when explicitly activated
* configured response policies applied to multi-step candidate completion when explicitly activated
* sparse activated response-policy maps that preserve legacy basic/random defaults
* opponent lead policies documented as multi-step preparation behavior

Known remaining areas:

* further defender-cooperation strategy can still be improved
* deeper PlayerProfile confidence usage beyond preset selection remains future work

### Defender cooperation

Implemented:

* safe smear while preserving the partner's winning position
* avoiding overtaking a winning partner when a partner-safe legal card exists
* forced partner overtake using the lowest-point legal winning card
* equal-point forced-overtake tie-break using weakest sufficient trick strength
* winning-card selection using the lowest-point legal winner
* equal-point winning-card tie-break using weakest sufficient trick strength
* equal-point safe-smear tie-break using weakest trick strength
* narrow second-hand trump conservation on zero-point non-trump leads when only trump wins and a losing discard exists
* safer discard when the declarer is currently winning and the defender cannot win
* safer defender lead that prefers low-point non-trumps when possible

Issue #22's current heuristic and explainable defender-partnership scope is implemented.

Known remaining areas:

* defender behavior is still heuristic and assumes a fixed three-player table
* partnership inference is strongest in the currently supported second-hand path
* no complete rear-hand partnership model exists yet
* no dedicated null-game defender-partnership strategy exists yet
* no stable declarer/partner identity exists when the local player itself is only known generically as `defender`
* no full partnership/tactical plan model exists yet
* no perfect-information solving, search, machine learning, or hidden-card inference is used

### Post-game review

Implemented:

* optional `actual_card_played` input
* actual-card validation
* legality validation for the actual card
* `post_game_review_summary` output
* comparison between actual and recommended card
* expected point swing difference
* decision quality classification
* decision factors
* decision explanation
* card-rank gap details
* CLI output for post-game review summaries
* unavailable summary when Immediate Analysis is unavailable because there is no current local decision
* information-safe pre-play snapshots for all 30 decisions in a normal-play historical game
* bounded review of all 30 historical decisions through existing immediate recommendation logic
* deterministic per-decision seeds and reconciled game and player quality summaries

Current output fields include:

* `decision_quality`
* `decision_factors`
* `decision_explanation`
* `actual_card_rank`
* `recommended_card_rank`
* `candidate_count`
* `better_card_count`

Current CLI wording uses review-objective language for rank and better-card
summaries. For Null games, the CLI distinguishes Null contract-objective gaps
from informational card-point swing fields.

### CLI and workflow usability

Implemented:

* improved CLI help text and command discoverability
* optional `--quiet` mode for automation-friendly JSON-output runs
* generated-output validation for representative user-facing CLI workflows
* comparison-only policy-comparison CLI output handling
* CLI sample-bound validation fixes
* curated documentation walkthroughs for common workflows
* complete historical-game validation and summary output
* optional historical decision snapshot and complete-review flags
* separate versioned training-dataset conversion workflow

## Current important modules

### Entry point

* `main.py`

  * CLI entry point
  * analysis orchestration
  * output construction
  * multi-step execution
  * policy comparison
  * human-readable output

### Input and validation

* `input_loader.py`

  * JSON loading
  * game state construction
  * settings extraction
  * left/right opponent policy normalization
* `input_validation.py`

  * raw input validation
  * card validation
  * completed-trick validation hooks
  * optional policy validation
  * optional player profile validation
* `information_policy.py`

  * live-vs-post-game information policy rules
  * information policy output summary

### Game state and rules

* `game_state.py`
* `rules.py`
* `deck.py`
* `known_cards.py`
* `game_history.py`

### Game result and settlement

* `game_declaration.py`
* `game_value.py`
* `matador_inference.py`
* `game_result.py`
* `game_end.py`
* `overbid.py`
* `impossible_null_settlement.py`
* `final_settlement.py`
* `performance_rating.py`

### Historical games and datasets

* `historical_game.py`
* `historical_decision_snapshot.py`
* `historical_snapshot_adapter.py`
* `historical_game_review.py`
* `training_dataset.py`
* `training_feature_view.py`

### Simulation

* `simulation.py`
* `simulation_step.py`
* `multi_step_simulation.py`
* `multi_step_summary.py`
* `simulation_context.py`
* `state_transition.py`

### Opponent modeling

* `opponent_policy.py`
* `opponent_lead.py`
* `opponent_sequence.py`
* `opponent_policy_preset.py`
* `opponent_profile_policy.py`
* `player_profile.py`

### Post-game review

* `post_game_review.py`

### Output

* `output_writer.py`
* `result_serialization.py`

## Current documentation structure

Main documentation files:

* `README.md`
* `docs/architecture.md`
* `docs/input_json.md`
* `docs/output_json.md`
* `docs/schema_validation.md`
* `docs/scoring.md`
* `docs/game_end.md`
* `docs/overbid.md`
* `docs/performance_rating.md`
* `docs/examples.md`
* `docs/historical_games.md`
* `docs/historical_decision_snapshots.md`
* `docs/historical_game_review.md`
* `docs/training_data.md`
* `docs/requirements_traceability.md`
* `docs/v1_scope.md`
* `docs/roadmap.md`
* `docs/project_handoff.md`

## Release status

Current code and release-preparation baseline: `v0.7.0`.

Current package version: `0.7.0`.

Latest tagged and human-published release: `v0.6.0`. It remains the published
release until a maintainer tags and publishes `v0.7.0`.

The `v0.7.0` release-preparation baseline validates 27 deterministic
generated-output scenarios and 2,302 pytest tests.

The `v0.3.0` stabilization issues #40 through #46 are complete:

* #40 Use Null contract objectives for live card recommendations
* #41 Prevent advanced states from double-counting completed-trick points
* #42 Return non-zero exit codes for invalid CLI invocations
* #43 Restore a valid documented default CLI input
* #44 Support `known_to_declarer` Skat visibility consistently
* #45 Validate completed-trick side ownership from cards and player order
* #46 Align runtime validation with documented input bounds and shapes

See [`CHANGELOG.md`](../CHANGELOG.md) for the release-note summary.

The `v0.4.0` CLI and user-facing usability issue range #47 through #53 is complete:

* #47 updated the post-`v0.3.0` roadmap and handoff direction
* #48 improved CLI help text and command discoverability
* #49 added optional `--quiet` mode for JSON-output CLI runs
* #50 expanded generated-output validation for user-facing CLI workflows
* #51 fixed remaining CLI usability validation bugs, including comparison-only and sample-bound handling
* #52 refreshed documentation and curated workflow walkthroughs
* #53 removed stale tracked generated output artifacts before release preparation

The `v0.5.0` trustworthy late-game and history-heavy public input issue range
#55 through #60 is complete:

* #55 allowed zero opponent hand sizes for late-game public inputs
* #56 enforced live completed-trick `winner_role` verifiability
* #57 expanded safe matador inference from completed-trick ownership
* #58 added focused late-game and history-heavy workflow coverage
* #59 improved objective-aware post-game review CLI wording
* #60 prepared the `v0.5.0` release

After the `v0.5.0` release, #61 selected the `v0.6.0` list-aware review
workflow direction.

The `v0.6.0` list-aware review workflow issue range #62 through #68 is complete:

* #62 added fixed three-player list standings output
* #63 expanded list-performance examples and generated-output validation
* #64 improved post-game review example quality and explanation coverage
* #65 added controlled left/right opponent policy effect coverage
* #66 used profile confidence in bounded opponent-strategy decisions
* #67 audited settlement and overbid edge-case coverage
* #68 prepared the `v0.6.0` release

The `v0.7.0` rules-confidence and information-safe historical-workflow issue
range #69 through #76 is complete:

* #69 defined the v1.0 scope, requirements traceability, and project baseline
* #70 enforced canonical Suit/Grand declaration dependencies and matador bounds
* #71 aligned fixed three-player standings ties with SkWO 6.3.1
* #72 added bounded settlement for impossible Null declarations
* #73 added complete normal-play historical-game records
* #74 added information-safe snapshots for all 30 historical decisions
* #75 added bounded complete historical-game decision review
* #76 added versioned historical training and evaluation dataset records

## Current implementation baseline

**v0.7.0: Rules confidence and information-safe historical workflows**

Completed implementation scope:

* authoritative ISkO/SkWO requirements traceability and v1.0 completion gates
* canonical declaration dependencies and official matador bounds
* SkWO-compliant unresolved standings ties and external lot order
* bounded impossible Null settlement
* complete normal-play historical-game validation and replay
* 30 information-safe historical decision snapshots
* bounded 30-decision historical review
* versioned provenance-aware training and evaluation datasets

## Current high-priority limitations

* Complete historical-game records do not yet cover claims, concessions, or other end reasons beyond normal completion.
* Claims, concessions, and general settlement behavior remain incomplete.
* Ouvert historical snapshots do not support exposed-card-aware recommendation simulation.
* General live position input lacks complete field-level provenance.
* Multi-Step simulation does not preserve one hidden-world assignment across every step.
* Training-dataset partitions are not player-disjoint.
* Historical opponent statistics and learned-model work remain undecided.
* The product supports fixed three-player tables only; four-player tables are unconditionally out of scope.

## Next recommended action

After human review and merge, create the `v0.7.0` tag and GitHub Release
manually, then use the [requirements traceability matrix](requirements_traceability.md)
and [v1.0 scope](v1_scope.md) for focused follow-up work. Do not treat undecided
areas as permanently excluded.

## Open future topics

Four-player tables are the only unconditional out-of-scope area. All other
candidate future areas retain the classifications in `docs/v1_scope.md` until
an explicit product decision changes them.

## New-thread starter instruction

When continuing in a new ChatGPT thread, provide:

1. the repository URL
2. this file
3. the current roadmap
4. the next desired milestone
5. the instruction that code and program output should remain in English while discussion can remain in German
