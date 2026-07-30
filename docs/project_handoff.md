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
* exact evidence-constrained hidden-card inference and compatible-world sampling
* opponent policy modeling
* game result and settlement summaries
* automatic matador inference where supported by known declarer-card context and safe concrete-declarer completed-trick ownership
* post-game review support
* complete normal-play and five supported exact-prefix shortened historical-game records
* two supported timed non-terminal historical continuation events
* information-safe variable-length historical decision snapshots and complete-game review
* versioned training and evaluation dataset records
* external and historically aggregated opponent statistics
* explainable confidence-gated opponent profiles
* live and time-safe historical profile application
* rolling opponent-policy evaluation
* dataset partition policies and stable-player overlap audits
* JSON input/output for regression-friendly testing

The project is not a machine-learning model or a full official tournament
system. It has one bounded exact-state perfect-information solver, but not a
general hidden-information Skat solver.

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

Formal series aggregation, tournament management, and official federation report
formats are not required product workflows.

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
* one immutable private hidden-world root per path, owner-aware card removal, and a fixed hypothetical skat
* shared-root Policy Comparison with equal independent immutable policy-path copies
* privacy-safe coherent-world count and status summaries without hidden card identities

### Hidden-card inference

Implemented:

* hard constraints only from the local exact hand, exact public hands,
  legitimately known skat, attributed public played ownership, and confirmed
  legal failure to follow the effective Suit/Grand/Null category
* evidence beginning after the proving public play, persistent for later
  decisions, and never retroactive; current-trick use requires concrete
  leader/order
* trusted canonical attributed completed history and stricter legal historical
  replay, without guessing ownership from legacy `played_cards` or unattributed
  tricks
* immutable contradiction-checked constraints, exact DP compatible-world counts
  and marginals, and deterministic uniform labeled-assignment sampling without a
  rejection loop
* concentration-only confidence: one-owner `confirmed`, `high` from `0.85`,
  `medium` from `0.65`, and `low` below `0.65`, explicitly not calibrated
* one model and common compatible worlds for Immediate candidates, one
  compatible coherent Multi-Step root, and one shared Policy Comparison
  model/root with immutable path copies
* historical review constrained only by the visible decision prefix, current
  trick, authorized public hands, and legitimately known skat
* strict version-1 privacy-safe summaries without sampled hands/skat/root,
  actual historical hidden hands, or DP tables

The feature excludes tactical choices, declarations, profiles, concessions,
timing, future play, complete post-game hands, result, value, overbid, and
settlement evidence. It adds no behavioral, Bayesian, calibrated, learned, or
new policy model. See [Hidden-card inference](hidden_card_inference.md).

### Bounded-search contracts

Implemented on the active `v0.10.0` development branch:

* immutable version-1 live and historical decision-time search information views
* explicit local-decision eligibility without compatible-world inspection
* deterministic requested and consumed structural budgets plus a separate wall-clock cutoff
* stable status, stop-reason, world-coverage, and solution-claim semantics
* local-side terminal utility version 1 for Suit, Grand, and Null
* privacy-safe aggregate candidate and overall result contracts
* deterministic serialization and a strict standalone Draft 2020-12 schema
* one private immutable perspective-neutral exact complete-world state with
  strict construction, canonical legal-card generation, pure transitions,
  completed-trick accounting, and neutral normal-terminal facts
* executable `perfect_information_minimax_v1` for one fully specified Suit,
  Grand, or normal non-overbid Null `ExactSearchState`, limited by the lower of
  five remaining tricks and the requested budget
* canonical full-window root values, deterministic below-root Alpha-Beta,
  invocation-local exact-only transposition reuse, and declarer-versus-
  cooperating-defenders utility orientation
* exact terminal composition through existing result, value, overbid, final
  settlement, and utility semantics
* all four Null variants with exact zero-trick declarer wins, one-or-more-trick
  defender wins, fixed-value settlement reuse, and no card-point secondary
  objective; missing or over-value Null bids stop before search
* shared legal transition reuse by the specialized five-trick defender-open-play proof

The exact solver returns no partial recommendation or fallback after a node,
depth, or timeout abort. Compatible-world and hidden-information search,
recommendation integration, CLI output, default or production budgets, and a
latency contract do not exist yet. See
[Bounded search contracts](bounded_search_contracts.md).

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
* exact legal prefixes and remaining-hand reconstruction for all five supported shortened terminal events
* one optional timed defender-open-play or declarer-card-exposure continuation in a normal-completion record
* variable-length snapshots, review decisions, and training samples based on actual play count

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

* normal completion and legacy remaining-trick assignment
* structured declarer and defender concessions
* unanimously accepted declarer-card exposure and non-terminal exposed-hand continuation
* bounded exact defender open play for at most five unresolved tricks and non-terminal returned-hand continuation
* open-card throwing with bounded jack-only theoretical Schwarz exclusion
* preexisting-result preservation, mandatory-level handling, supported overbid settlement, and privacy-safe summaries

General claims, specific-trick claims, defender-open-play proof beyond five
unresolved tricks, and broader settlement nuance remain unsupported.

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
* focused historical-game, historical game-end/concession, historical-decision-snapshot, historical-game-review, and training-dataset schemas
* strict version-1 hidden-card inference summary schema
* strict standalone version-1 bounded-search aggregate result schema
* input example schema validation
* generated output schema validation
* schema validation documentation

Generated-output validation currently covers 52 deterministic scenarios.

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
* no perfect-information solving, search, machine learning, behavioral/Bayesian inference, or broader tactical hidden-card inference is used by defender cooperation

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
* information-safe pre-play snapshots for every actual play in each supported historical terminal record
* bounded review of every actual supported historical card decision through existing immediate recommendation logic
* deterministic per-decision seeds and variable reconciled game and player quality summaries

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
* `declarer_concession.py`
* `defender_concession.py`
* `declarer_card_exposure.py`
* `declarer_card_exposure_continuation.py`
* `defender_open_play.py`
* `defender_open_play_continuation.py`
* `open_card_throw.py`
* `overbid.py`
* `impossible_null_settlement.py`
* `final_settlement.py`
* `performance_rating.py`

### Historical games and datasets

* `historical_game.py`
* `historical_game_end.py`
* `historical_game_event.py`
* `historical_play_prefix.py`
* `historical_declarer_concession.py`
* `historical_defender_concession.py`
* `historical_declarer_card_exposure.py`
* `historical_declarer_card_exposure_continuation.py`
* `historical_defender_open_play.py`
* `historical_defender_open_play_continuation.py`
* `historical_open_card_throw.py`
* `historical_decision_snapshot.py`
* `historical_snapshot_adapter.py`
* `historical_game_review.py`
* `training_dataset.py`
* `training_feature_view.py`
* `dataset_partition_policy.py`
* `dataset_partition_audit.py`
* `historical_opponent_statistics.py`
* `historical_opponent_profile_binding.py`
* `historical_opponent_profile_application.py`

### Simulation

* `simulation.py`
* `hidden_card_inference.py`
* `coherent_hidden_world.py`
* `bounded_search_information.py`
* `exact_search_state.py`
* `exact_terminal_utility.py`
* `perfect_information_minimax.py`
* `terminal_utility.py`
* `bounded_search_result.py`
* `ouvert_simulation.py`
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
* `opponent_statistics.py`
* `opponent_profile_derivation.py`
* `opponent_profile_application.py`
* `live_opponent_profile_binding.py`
* `rolling_opponent_policy_evaluation.py`
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
* `docs/historical_declarer_card_exposure_continuation.md`
* `docs/historical_defender_open_play_continuation.md`
* `docs/historical_decision_snapshots.md`
* `docs/historical_game_review.md`
* `docs/ouvert_aware_simulation.md`
* `docs/coherent_hidden_world_simulation.md`
* `docs/hidden_card_inference.md`
* `docs/bounded_search_contracts.md`
* `docs/historical_opponent_profiles.md`
* `docs/training_data.md`
* `docs/dataset_partition_policies.md`
* `docs/opponent_statistics.md`
* `docs/opponent_profile_derivation.md`
* `docs/live_opponent_profiles.md`
* `docs/historical_opponent_statistics.md`
* `docs/opponent_policy_evaluation.md`
* `docs/requirements_traceability.md`
* `docs/v1_scope.md`
* `docs/roadmap.md`
* `docs/project_handoff.md`

## Release status

Current published stable release: `v0.9.0`.

Current package version: `0.9.0`.

Release theme: "Structured game endings and coherent hidden information."

The published release tag points to commit `0679760`.

Issues #86 through #104 are complete in the published baseline. GitHub Releases
is the authoritative publication record.

The published `v0.9.0` baseline validates 52 deterministic generated-output
scenarios and passes 3,558 pytest tests.

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

The `v0.8.0` explainable and time-safe opponent-intelligence issue range #78
through #84 is complete:

* #78 added versioned external opponent-statistics records with exact and estimated evidence
* #79 added scoped, explainable, confidence-gated rule-based profile derivation
* #80 applied actionable external profiles to live analysis through stable-ID side bindings
* #81 applied profiles to historical review with strict pre-game temporal safety
* #82 aggregated and exported exact reusable statistics from timestamped historical games
* #83 evaluated rolling as-of known-opponent policy behavior against `simple_lowest`
* #84 added dataset partition policies and deterministic stable-player overlap audits

The `v0.9.0` structured game endings and coherent hidden information issue range
#86 through #104 is complete:

* #86 and #87 added structured declarer and defender concessions
* #88 and #89 added accepted declarer exposure and continued exposed-hand play
* #90 and #91 added bounded defender open play and continued returned-hand play
* #92 added structured open-card throwing
* #93 added exact-prefix historical declarer concession with stable-ID consent and settlement
* #94 generalized snapshots, review, training samples, external-profile review, and partition audits to actual played-card cardinality
* #95 integrated concession records into game-weighted statistics/export and actual-decision rolling evaluation
* #96 added exact-prefix historical defender concession with stable-ID joint liability
* #97 added exact-prefix unanimously accepted declarer-card exposure and integrated all variable-length workflows
* #98 added bounded terminal historical defender open play with exact flat adjudication reuse and privacy-safe stable-ID proof output
* #99 added timed non-terminal historical defender-open-play continuation with persistent public-hand information
* #100 added timed non-terminal historical declarer-card-exposure continuation with the same information-safe downstream boundary
* #101 added exact-prefix historical open-card throwing and variable-length workflow integration
* #102 connected declared-Ouvert exact public hands to flat and historical recommendation simulation while preserving existing scoring, policies, training versions, and rolling as-of safety
* #103 preserved one private hidden-world assignment across every Multi-Step path and one shared root across independent Policy Comparison paths, with privacy-safe summaries
* #104 added exact structural hidden-card constraints, DP compatible-world counts and marginals, uniform sampling, workflow sharing, historical leakage controls, and privacy-safe summaries

## Current implementation baseline

**v0.9.0: Structured game endings and coherent hidden information**

Completed implementation scope:

* all bounded `v0.8.0` opponent-intelligence workflows remain supported
* five structured flat terminal endings and two exact-public-hand continuation paths
* exact-prefix records for all five supported historical shortened terminal events
* variable-length historical decision artifacts for normal completion and all five shortened kinds
* shortened-game historical statistics, export, and rolling evaluation
* timed normal-completion continuation with an exact shrinking public defender or declarer hand
* declared-Ouvert exact public-hand constraints in Immediate Analysis, supported Multi-Step, Policy Comparison, flat review, and historical review
* coherent private hidden-world ownership across each Multi-Step path and shared-root Policy Comparison
* exact evidence-constrained hidden-card inference across Immediate, Multi-Step, Policy Comparison, and historical review

## Current high-priority limitations

* Historical records support normal completion with either one timed continuation kind, exact-prefix declarer and defender concessions, unanimously accepted declarer-card exposure, bounded terminal defender open play, and terminal open-card throw; multiple events, continuation followed by shortening, other claims, and other end reasons remain unsupported.
* Historical opponent-statistics aggregation and rolling policy evaluation support normal completion and all five shortened terminal reasons; other end reasons remain unsupported.
* General claim verification, concession disputes, and approved settlement completeness remain incomplete.
* General live position input lacks complete field-level provenance.
* Evidence-constrained sampling does not infer the real deal or provide exhaustive search.
* Hidden-card inference beyond confirmed structural decision-time evidence and
  general stronger search remain incomplete. The bounded exact-state Suit,
  Grand, and supported Null Minimax solver is not connected to compatible worlds
  or product workflows; overbid Null replacement selection remains outside it.
* Complete-game coaching and full fixed-three-player 36-game list aggregation are not implemented.
* Interactive live or retrospective input and a stable installed CLI/library interface are not implemented.
* Opponent behavior and confidence remain heuristic and rule-based; behavioral evaluation does not prove stronger play.
* No learned model or model-training workflow exists.
* No website or browser integration exists.
* The product supports fixed three-player tables only; four-player tables are unconditionally out of scope.

## Next recommended action

`v0.9.0` is published. The active next development milestone is `v0.10.0`.
Version-1 bounded Search/Solver information, quality, determinism, budget,
result, exact complete-world state, and legal-transition contracts are now
implemented together with one bounded exact-state Suit, Grand, and normal
non-overbid Null Minimax solver. All four Null variants are covered while
preserving its five-trick, budget, Alpha-Beta, transposition, determinism, and
privacy contracts. Compatible-world, hidden-information, and workflow
integration remain the next solver dependencies, so the overall stronger-search
gate stays open. Remaining
pre-`v1.0.0` work also includes fuller Replay Coaching, approved settlement
nuance, fixed-three-player 36-game list aggregation, automatic dataset
preparation, field-level live provenance, interactive session capture, and a
stable installed API and CLI interface.

## Open future topics

The approved pre-`v1.0.0`, post-`v1.0.0`, not-required, and excluded product
areas are recorded in [v1.0 scope](v1_scope.md). Four-player tables remain the
only unconditional exclusion.

## New-thread starter instruction

When continuing in a new ChatGPT thread, provide:

1. the repository URL
2. this file
3. the current roadmap
4. the next desired milestone
5. the instruction that code and program output should remain in English while discussion can remain in German
