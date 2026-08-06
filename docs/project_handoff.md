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
* public unpartitioned dataset-preparation requests, deterministic split-plan
  proofs, strict supplied-assignment validation, and lossless materialization
* exact deterministic temporal Known-opponent assignment generation over parsed
  time groups with complete Train player coverage and Record-count optimization
* deterministic Player-connected unseen-player assignment with component
  identities, non-empty greedy placement, and strict local move/swap improvement
* root-selected automatic Training Dataset preparation with fixed mode dispatch,
  complete or explicit unavailable results, strict schemas, concise CLI output,
  three examples, and generated-output coverage
* JSON input/output for regression-friendly testing
* bounded Search post-game, historical-review, and dataset-evaluation workflows
* immutable version-1 normative settlement and approved claim-boundary matrix
* immutable version-1 Replay Coaching decision-time evidence and retrospective impact contracts
* deterministic Replay Coaching Key Decisions, Turning Points, one-game patterns, and actionable recommendations
* complete public version-1 Replay Coaching Report with strict schema, CLI, human-readable presentation, and generated-output coverage
* public immutable version-1 fixed-three-player 36-position historical-list
  contracts with passed deals, rotating historical seats, settlement-derived
  per-entry contribution facts, cumulative player totals, 36-position
  progression, SkWO standings, optional external-lot application,
  strict retained-aggregation validation, independent completed-list comparison,
  reconciliation, deterministic privacy-safe serialization, strict schemas,
  root-selected JSON workflows, concise CLI output, examples, and generated-
  output coverage

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

Implemented in the published `v0.10.0` release baseline:

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
* private compatible Search-world spaces built only from the information view,
  including exact counting without void evidence, canonical bounded exhaustive
  enumeration, deterministic uniform IID sampling with replacement, retained
  duplicate accounting, strict exact-state materialization, and one frozen
  common legal-root sequence
* executable `compatible_world_minimax_v1` over that frozen sequence, using the
  same internal exact-world evaluator as direct Minimax, one global node budget,
  per-world depth reset and exact-only cache, one post-selection timeout window,
  and first-incomplete-world common-prefix stopping
* equal-weight card-identity aggregation of exact completed-world success,
  settlement score, and Suit/Grand margin, including repeated duplicate draws,
  threshold-gated partial/timeout recommendations, and privacy-safe results
* explicit flat live recommendation methods `immediate_expected_value`,
  `bounded_search`, and `auto`, with Immediate still the omitted default
* strict Search without fallback, validated Search-result-only auto fallback,
  separate Immediate/Search seeds, report separation, and privacy-safe CLI/output
* opt-in Search-aware Multi-Step with one fresh public-state Search call and
  immutable requested budget per local decision
* deterministic `multi_step_bounded_search_decision_v1` child seeds separated
  from coherent-root, opponent-action, and Immediate streams
* coherent-world separation: Search reconstructs compatible worlds from public
  state, then the selected card executes in the private path world
* Search-inclusive Policy Comparison with one appended configured method,
  eligibility-aware recommendation, and compact aggregate-only diagnostics
* flat post-game Search with an independently executed Immediate baseline,
  actual-card aggregate ranking, and Search-versus-Immediate comparison
* Historical Search Review for every actual decision with reconciled status,
  coverage, agreement, quality, and performance summaries
* stable private SHA-256 decision seeds in domain
  `historical_bounded_search_decision_v1`, derived from base seed, game ID, and
  decision index and never serialized
* bounded-Search dataset evaluation with default validation/test partitions, one
  stable global decision cap, and preservation of selected zero-decision records
* immutable `interactive_v1`, `historical_review_v1`, and `evaluation_v1`
  structural work profiles
* independent exhaustive strict-improvement fixtures for Suit, Grand, and Null,
  plus sampled convergence evidence at 32, 64, and 128 worlds
* a deterministic late-game Suit/Grand/Null benchmark corpus and measured
  performance documentation without a calibrated latency guarantee
* shared legal transition reuse by the specialized five-trick defender-open-play proof

The direct exact solver returns no partial recommendation or fallback after a
node, depth, or timeout abort. Compatible-world Minimax may recommend only from
an exact common completed prefix that reaches the configured minimum. The flat
live workflow now exposes strict Search and Search-first auto routing; auto may
mark Immediate fallback only after a valid no-recommendation Search result.
These additions remain bounded late-game determinization. Search aggregates do
not prove an optimal imperfect-information policy, sampled quality is not
calibrated, no latency guarantee exists, and omitted-method Immediate behavior
is unchanged. The stronger-search v1.0 gate therefore remains open. See
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
* one optional timed defender-open-play or declarer-card-exposure continuation before normal completion or one supported terminal shortening
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
* immutable version-1 normative settlement matrix covering current support,
  bounded interpretations, legacy compatibility, approved later semantics,
  decision-required claims, and `v0.11.0` exclusions

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
The normative boundaries and implemented one-continuation-plus-one-terminal-
shortening historical sequence are defined in
[Settlement normative matrix](settlement_normative_matrix.md).

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
* strict internal 36-position historical-list representation with fixed stable
  participants, passed deals, rotation, timestamp auditing, and non-cumulative
  contribution facts
* internal immutable cumulative totals, one provisional standings snapshot per
  historical-list position, final SkWO standings, unresolved ties, and optional
  exact external-lot application
* internal immutable comparison of two or more independent completed lists with
  one fixed reference, stable-ID alignment, final count and player-total deltas,
  resolved-only rank movement, and privacy-safe serialization
* public strict JSON request and output schemas for one complete list or two or
  more independent lists
* root-selected CLI execution with only `--input`, `--output`, and `--quiet`,
  full single-list progression, and compact comparison presentation
* three bounded examples and generated-output scenarios for applied lot,
  unresolved all-passed tie, and resolved independent comparison

Not implemented:

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
* strict flat post-game Search, Historical Search Review, Historical Replay Coaching, and bounded-Search evaluation schemas
* strict historical-list source, request, aggregation, and comparison schemas
* strict Training Dataset preparation request, partition Plan, and preparation
  output schemas
* input example schema validation
* generated output schema validation
* schema validation documentation

The `v0.12.0` package baseline covers 70 deterministic generated-output
scenarios and is pending manual publication. The published `v0.11.0` baseline
remains historical evidence for 64 scenarios and 4,392 pytest tests. The historical published `v0.10.0`
release baseline remains 59 scenarios and 4,075 tests, and the historical
published `v0.9.0` baseline remains 52 scenarios and 3,558 tests.

Issue #130 appends three historical-list scenarios. Issue #134 preserves those
67 scenarios and appends three automatic Training Dataset preparation scenarios,
so the `v0.12.0` package baseline validates exactly 70 outputs without changing
the historical published baselines.

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

### Replay Coaching

Implemented as a `v0.11.0` information-safe public workflow:

* immutable contract version `1` with information policy
  `decision_time_then_retrospective_attachment`
* separate decision-time evidence and retrospective observed-card assessment
* normalized reuse of existing Immediate evidence, bounded-Search results, and
  Search comparisons without rerunning either analysis
* opening, middle, and endgame phase conventions
* stable statuses, evidence-basis priority, impact tiers, factors, limitations,
  strict validation, and privacy-safe deterministic serialization
* unchanged Immediate Historical Review and Historical Search Review output
* one retained chronological assessment tuple from the same Historical Search
  Review execution, without additional Search or Immediate calls
* deterministic selection of at most five strictly-below-best Key Decisions by
  impact, evidence, positive primary gap, alternative count, and chronology
* separate Contract-success decision-opportunity and first recorded-prefix
  outcome Turning Points
* complete-normal-play fallback for still-undecided terminal contracts, including
  a ten-trick Null declarer win without a declarer trick
* threshold-free high-impact classification, stable factors and limitations,
  strict game-level reconciliation, and deterministic internal serialization
* one-game player, role, phase, and contract patterns requiring two occurrences
* separate actionable and descriptive pattern contracts with canonical counts,
  ordering, factors, limitations, and deterministic serialization
* one fixed-template recommendation per Key Decision and at most five ranked,
  evidence-deduplicated actionable pattern recommendations
* explicit Contract-success, settlement-score, Suit/Grand-margin, Null, Immediate-
  only, and Search-versus-Immediate wording boundaries
* one retained internal guidance result from the same Historical Search Review
  execution without additional Search or Immediate calls
* complete report version `1` and method
  `historical_replay_coaching_v1`, composed from that retained analysis
* privacy-safe player/game context, separately attached final outcome context,
  reconciled coverage, and zero-preserving player/role/phase/contract summaries
* explicit `final_context_after_coaching` isolation, deterministic internal
  serialization, canonical report limitations, and no private deal or Search
  state in report output
* opt-in `--historical-replay-coaching` with explicit Search seed and the shared
  immutable Search/Immediate settings
* coaching-only conditional JSON output and combined one-pass emission with the
  retained Historical Search Review summary
* strict standalone Draft 2020-12 schema registered from the main output schema
* concise human-readable Key Decision, Turning Point, recommendation, scope,
  outcome-context, and limitation sections
* normal Grand, Null, and continuation-before-shortening generated-output
  coverage within the exact 64-scenario matrix

The observed card is not ground truth, no causal final-outcome claim is made,
and exhaustive compatible-world aggregation remains subject to Strategy Fusion.
Tactical motif detectors, cross-game analysis, stronger Search, and any causal
language remain unimplemented. See
[Replay coaching contracts](replay_coaching_contracts.md).

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
* `settlement_normative_matrix.py`
* `performance_rating.py`
* `fixed_three_player_historical_list.py`
* `fixed_three_player_historical_list_request.py`
* `fixed_three_player_list_rotation.py`
* `fixed_three_player_list_contribution.py`
* `fixed_three_player_historical_list_aggregation.py`
* `fixed_three_player_historical_list_comparison.py`
* `fixed_three_player_historical_list_comparison_summary.py`
* `fixed_three_player_historical_list_progression.py`
* `fixed_three_player_historical_list_standings.py`
* `fixed_three_player_historical_list_totals.py`

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
* `training_dataset_preparation.py`
* `dataset_preparation_identity.py`
* `dataset_partition_plan.py`
* `temporal_known_opponent_split.py`
* `dataset_partition_objective.py`
* `player_disjoint_unseen_player_split.py`
* `training_dataset_preparation_workflow.py`
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
* `bounded_search_post_game_review.py`
* `retrospective_search_comparison.py`
* `historical_search_review.py`
* `replay_coaching_evidence.py`
* `replay_coaching_assessment.py`
* `replay_coaching_patterns.py`
* `replay_coaching_recommendations.py`
* `replay_coaching_guidance.py`
* `bounded_search_evaluation.py`
* `search_budget_profiles.py`
* `recommendation_workflow.py`
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
* `docs/fixed_three_player_36_game_list_contracts.md`
* `docs/fixed_three_player_36_game_list_aggregation.md`
* `docs/fixed_three_player_36_game_list_comparison.md`
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
* `docs/bounded_search_performance.md`
* `docs/replay_coaching_contracts.md`
* `docs/historical_opponent_profiles.md`
* `docs/training_data.md`
* `docs/dataset_partition_policies.md`
* `docs/automatic_dataset_preparation_contracts.md`
* `docs/temporal_known_opponent_dataset_splits.md`
* `docs/player_disjoint_unseen_player_dataset_splits.md`
* `docs/opponent_statistics.md`
* `docs/opponent_profile_derivation.md`
* `docs/live_opponent_profiles.md`
* `docs/historical_opponent_statistics.md`
* `docs/opponent_policy_evaluation.md`
* `docs/requirements_traceability.md`
* `docs/settlement_normative_matrix.md`
* `docs/v1_scope.md`
* `docs/roadmap.md`
* `docs/project_handoff.md`

## Release status

Current published stable release: `v0.11.0`.

Current package version: `0.12.0`.

Current package baseline: `v0.12.0`.

Package release theme: "Fixed-three-player historical lists and deterministic
dataset preparation".

Intended GitHub Release title: "v0.12.0 — Fixed-three-player historical lists
and deterministic dataset preparation".

`v0.12.0` has not yet been tagged or published. Publication is a manual
maintainer action, and GitHub Releases remains authoritative.

Published `v0.11.0` release theme: "Information-safe Replay Coaching and structured
historical outcomes".

Published GitHub Release title: "v0.11.0 — Information-safe Replay Coaching and
structured historical outcomes".

The latest stable GitHub Release points to commit `cfd28e5`. It requires Python
`>=3.13`, validates 64 deterministic generated-output scenarios, and passes
4,392 pytest tests.

Issues #118 through #124 complete the functional `v0.11.0` milestone, and Issue
#125 completed release preparation. Publication was performed manually by the
maintainer. GitHub Releases is the authoritative publication record.

The `v0.12.0` package baseline implements the immutable
historical-list source, cumulative aggregation, independent comparison, and
strict public JSON/schema/CLI workflow, plus internal version-1 unpartitioned
dataset-preparation and supplied split-plan contracts plus deterministic
temporal Known-opponent and Player-disjoint unseen-player assignment generators.
Issue #134 adds the root-selected public preparation workflow, strict schemas,
CLI, and three examples. The prior 67 scenarios are unchanged, and the package
baseline validates 70 while the published `v0.11.0` baseline remains 64. Issue
#135 prepares release metadata and documentation before manual publication.

The historical published `v0.10.0` release points to commit `b4c8738`, validates
59 deterministic generated-output scenarios, and passes 4,075 pytest tests.

The historical published `v0.9.0` baseline validates 52 deterministic generated-
output scenarios and passes 3,558 pytest tests.

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

The published `v0.10.0` information-safe bounded Search issue range #107 through
#115 is complete:

* #107 defined bounded-Search information, budget, result, exactness, and privacy contracts
* #108 added immutable exact states and legal transitions
* #109 added Suit and Grand Perfect-Information Minimax
* #110 added all four normal non-overbid Null variants
* #111 added exact compatible-world counting, canonical enumeration, deterministic IID sampling, and selection
* #112 added compatible-world Minimax with retained duplicate weighting and common-prefix aggregation
* #113 added flat live strict Search and Search-first auto fallback
* #114 integrated Search into Multi-Step and Policy Comparison
* #115 added flat post-game and Historical Search Review, dataset evaluation, immutable profiles, quality and convergence evidence, and measured performance baselines

Issue #116 completed release preparation before the maintainer's manual
publication.

## Current implementation baseline

**Package v0.12.0: Fixed-three-player historical lists and deterministic dataset preparation**

Completed implementation scope:

* all bounded `v0.8.0` opponent-intelligence workflows remain supported
* five structured flat terminal endings and two exact-public-hand continuation paths
* exact-prefix records for all five supported historical shortened terminal events
* variable-length historical decision artifacts for normal completion and all five shortened kinds
* shortened-game historical statistics, export, and rolling evaluation
* timed continuation with an exact shrinking public defender or declarer hand before normal completion or one supported terminal shortening
* declared-Ouvert exact public-hand constraints in Immediate Analysis, supported Multi-Step, Policy Comparison, flat review, and historical review
* coherent private hidden-world ownership across each Multi-Step path and shared-root Policy Comparison
* exact evidence-constrained hidden-card inference across Immediate, Multi-Step, Policy Comparison, and historical review
* immutable information-safe Search views and exact-world legal states
* bounded exact-state Suit, Grand, and all four normal non-overbid Null Minimax
* exact compatible-world counting, canonical enumeration, deterministic IID sampling with replacement, retained duplicate weighting, and common-prefix aggregation
* live, Multi-Step, Policy Comparison, post-game, Historical Search Review, and dataset-evaluation integration
* immutable budget profiles, quality and convergence fixtures, and deterministic measured reference performance
* immutable 61-case normative settlement matrix with direct, bounded, legacy,
  undecided, and excluded scope classifications
* one supported non-terminal continuation before normal completion or one
  supported terminal shortening, delegated to unchanged terminal adjudicators
* information-safe one-game Replay Coaching evidence, impact, Key Decisions,
  both Turning Point types, patterns, deterministic recommendations, complete
  report, public JSON/schema/CLI, examples, and generated-output coverage
* fixed-three-player 36-position historical-list source, aggregation,
  progression, standings, exact external lots, independent comparison, and
  strict public JSON/schema/CLI workflows
* deterministic automatic Training Dataset preparation with fixed mode dispatch,
  complete or unavailable Plans, temporal Known-opponent and Player-disjoint
  unseen-player assignment, and lossless existing-dataset materialization

## Current high-priority limitations

* Historical records support normal completion or one of five terminal shortenings, optionally after one timed continuation kind. Multiple non-terminal events, arbitrary event streams, other claims, and other end reasons remain unsupported.
* Historical opponent-statistics aggregation and rolling policy evaluation support normal completion and all five shortened terminal reasons; other end reasons remain unsupported.
* General claim verification, concession disputes, and approved settlement completeness remain incomplete.
* General live position input lacks complete field-level provenance.
* Evidence-constrained sampling does not infer the real deal or provide exhaustive search.
* Hidden-card inference beyond confirmed structural decision-time evidence and
  general stronger search remain incomplete. Compatible-world Minimax now
  evaluates the frozen selected sequence and aggregates one exact common prefix,
  but it is determinization-based and subject to strategy fusion. It is not an
  optimal imperfect-information policy proof. Explicit live methods, opt-in
  Multi-Step and Policy Comparison, flat post-game review, Historical Search
  Review, and bounded dataset evaluation are connected. Overbid Null replacement
  selection remains outside it.
* The immutable fixed-three-player 36-position historical-list contracts now
  include Passed Deals, cumulative aggregation, progression, final SkWO
  standings, unresolved ties, exact external-lot application, and independent-
  list comparison with one reference and no series rollup. Public workflows
  now expose the retained contracts through strict schemas, root-selected JSON,
  concise CLI output, three examples, and privacy-safe generated-output coverage.
  Series aggregation, ratings, tournament management, and official reporting
  remain outside this bounded workflow.
* Automatic Training Dataset preparation now derives the fixed
  `temporal_known_opponent_v1` or
  `component_balanced_unseen_player_v1` algorithm from mode. A complete result
  losslessly materializes the existing version-1 dataset and audit; an
  unavailable result succeeds with explicit null dataset/audit and no partial
  Plan. The request has no algorithm field or default weights, the CLI has no
  overrides or fallback and accepts only file options, and Plan/CLI presentation
  is card-free. The complete nested reusable dataset retains source cards.
  Additional algorithms, algorithm overrides, fallback or partial Plans, global
  optimization, ratio guarantees, Sample- or Player-count balancing, component
  splitting, model training, and automatic evaluation remain unsupported.
* Replay Coaching has a public version-1 one-game report with information-safe
  evidence, impact, prioritization, patterns, recommendations, scope summaries,
  and isolated outcome context. Tactical motif detection, cross-game patterns,
  broader Search, and causal attribution remain unimplemented.
* Interactive live or retrospective input and a stable installed CLI/library interface are not implemented.
* Opponent behavior and confidence remain heuristic and rule-based; behavioral evaluation does not prove stronger play.
* No learned model or model-training workflow exists.
* No website or browser integration exists.
* The product supports fixed three-player tables only; four-player tables are unconditionally out of scope.

## Next recommended action

The maintainer can complete manual `v0.12.0` publication after reviewing the
release candidate and validation evidence. Until then, the package baseline is
`v0.12.0`, the published release remains `v0.11.0`, and GitHub Releases remains
authoritative.

The next provisional planning milestone is `v0.13.0`, directed at stable API,
packaging, and field-level information provenance. Its final issue sequence and
architecture are not yet defined.

Future dataset-preparation work remains narrower: additional algorithms,
algorithm overrides, fallback or partial Plans, global optimization, guaranteed
ratios, Sample- or Player-count balancing, component splitting, model training,
and automatic evaluation require separate scope. Tactical motifs, cross-game
Coaching, ratings, causal attribution, broader Search, general claims, and
settlement completeness also remain separate open work.

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
