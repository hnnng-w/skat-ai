# Roadmap

This document tracks completed areas, known limitations, and planned improvements for `skat-ai`.

## Completed major areas

### Interactive Session contract, Request export, Checkpoint, and persistence foundation

Implemented by Issue #150 for the active `v0.14.0` milestone:

* Internal Session and Command version `1` with independent policy identifiers
* Exactly three stable Players in canonical Historical seat order
* Live and Retrospective Capture Modes with explicit one-way promotion
* Canonical setup-through-ended phases and immutable allowed-phase metadata
* Ten typed caller-fact Commands and recursively immutable event/end payloads,
  including narrow declared-Ouvert current-public-hand capture
* Authoritative accepted Command Log with contiguous linear revisions
* Structural pre-promotion Live hand protection
* Canonical Diagnostics, Position/Historical export readiness, valid-incomplete
  status, and Transition Result constructor semantics
* Deterministic fresh JSON-compatible serialization without generated identity,
  time, environment, or path data
* Transition-engine and projection version `1` with full accepted-Log replay
* Canonical revision-zero creation and computed initial Validation
* Atomic Command application, revision-conflict precedence, and exact unchanged-
  State rejection
* Monotonic phase advancement and incremental Deal, Declaration, Skat/Discard,
  Play, ownership, legal-card, trick, continuation, Game-end, promotion, and
  information-policy validation
* Position and Historical readiness recomputation plus forged-State detection
* Session Request Export version `1` with exact policies and immutable
  available/unavailable Results
* One-replay Historical readiness gating and no Historical builder call while
  unavailable
* Exact Retrospective projection mapping through the existing Historical builder,
  canonical serialization and rebuild, and immutable `RequestDocumentV1`
* Normal completion, all five terminal endings, both continuation events, and all
  supported continuation/end chains without workflow execution
* Position Export Options version `1` with existing recommendation-configuration
  validation and immutable explicit analysis settings
* One-replay Position readiness gating, stable-to-relative information-safe
  mapping, and existing flat Position builder validation without execution
* Decision-visible Skat and Matadors plus owner-aware declared-Ouvert and
  continuation public-hand coexistence and shrinking
* Frozen pre-Play Decision Checkpoint version `1` with replay-verified source
  revision, actor/seat/index metadata, relative map, and Position Request
* Session History Edit version `1` with immutable Undo/correction policies,
  Results, exact source suffix reporting, and caller-retained Redo policy
* Strict-prefix Undo through projection-level replay and one final Validation
* One-command replacement plus deterministic original-suffix replay that stops
  before the first rejected later Command and returns a valid partial State
* Checkpoint Lineage version `1` with current, ancestor, future, and diverged
  classification from exact accepted-Log prefixes and rebuilt Position Requests
* Private Session Persistence document version `1` with authoritative accepted-
  Log State and canonically ordered caller-supplied frozen Decision Checkpoints
* Domain-separated deterministic State and content fingerprints, strict typed
  reconstruction, full accepted-Log replay, fingerprint verification, and
  resume-time Checkpoint Lineage recomputation
* Optimistic expected-content-fingerprint writes with exact `saved`, `unchanged`,
  and `conflict` outcomes, including a second pre-replacement conflict check
* Canonical UTF-8 JSON files written through a durable same-directory temporary
  file and atomic replacement, with cleanup that preserves the prior target

Issue #151 executes the internal Commands but does not itself export an Engine
Request. Issue #152 adds only canonical Retrospective Historical Request export.
Issue #153 adds information-safe Position Request export, declared-Ouvert public-
hand capture, and immutable Decision Checkpoints. Issue #154 adds strict-prefix
Undo, one-command correction, deterministic suffix replay, and Checkpoint
lineage. Issue #155 adds private deterministic Session persistence and resume,
including expected-fingerprint stale-write conflict detection and atomic file
replacement. Session-triggered analysis, actual-card Checkpoint attachment,
Public API, Session Provenance, Schemas, CLI Session Assistant, examples,
generated outputs, automatic Checkpoint collection, end-to-end capture, and UI
remain open. See
[Interactive session contracts](interactive_session_contracts.md) and
[Retrospective Session export](retrospective_session_export.md), and
[Session Position export and Decision checkpoints](live_session_position_export.md),
[Session Undo, correction, and Checkpoint lineage](session_undo_and_correction.md),
and [Session persistence and resume](session_persistence_and_resume.md).

### Public API contract foundation

Implemented:

* Public API contract version `1` under `skat_ai.api.v1`
* Minimal Package-Root exports limited to `api`, `errors`, and `__version__`
* Exact canonical seven-workflow `WorkflowV1` contract
* Frozen, slotted, keyword-only Request, Result, execution-option,
  compatibility-policy, and API-version contracts
* Recursive defensive immutable JSON storage with fresh mutable serialization
* Stable public error hierarchy, codes, deterministic serialization, and built-in catch compatibility
* Stable CLI Exit Code constants and exact legacy `main.CliUsageError` alias
* Additive compatibility, internal-import, version-independence, and future deprecation policies
* Executable all-seven-workflow `parse_request`, `execute`, `execute_document`,
  and `serialize_result` facade
* Direct immutable workflow options, paired external Opponent Statistics,
  separate public artifacts, and flattened deterministic execution results
* Lazy Package Resource Root input/output/artifact schema validation with RFC
  6901 errors and stable boundary translation
* Explicit Setuptools build metadata, `skat_ai*` discovery, Package Data, and the
  current `0.13.0` Package version
* Byte-identical private Schema resources with deterministic synchronization and
  local/CI parity checks
* PEP 561 `py.typed`, Package-Root version metadata, one Wheel and one sdist,
  artifact inspection, and separate clean-install public-API smoke tests
* Public field-provenance version `1` with immutable attachment/artifact/bundle
  contracts, seven explicit Result mappings, default-false opt-in, and unchanged
  flattened execution envelope

The executable facade is available from source, Editable, Wheel, and sdist
installations. Installed CLI entry points are implemented separately below.
Internal live Position provenance propagation is implemented. Internal
retrospective Position, Historical Review, Historical Search Review, and Replay
Coaching propagation is also implemented. Dataset, Preparation, Opponent,
Profile, historical-list, and comparison propagation is implemented with
complete non-legacy Root ledgers. Complete non-legacy Position/base Historical
Result propagation is also implemented. Bounded public Root Result and actual-
artifact exposure is implemented; broader enforcement remains open.
Internal Application extraction is covered separately below.

### Application orchestration foundation

Implemented:

* Internal Application orchestration contract version `1` with a caller-supplied
  input-reference policy
* Frozen, slotted, keyword-only invocations, workflow options, external
  documents, results, and auxiliary artifacts with defensive JSON immutability
* Generic transport-free dispatch across all seven canonical Root workflows
* Exactly five isolated Training Dataset operations
* Optional already-loaded Opponent Statistics injection for Position Analysis
  and Historical Game execution
* Optional `opponent_statistics_input` auxiliary export artifact kept outside the
  primary result and without a transport path
* Legacy Root CLI retained as the argument/file/output/presentation boundary with
  existing wrapper names and JSON parity
* Stable public facade reuse without changes to Root schemas, examples,
  scenarios, or Package version
* Optional internal live Position provenance bundles with complete decision
  attachments and an exact complete Position Result attachment
* Optional internal retrospective Position and Historical provenance bundles
  with retained decision stages, requested aggregate reviews, Replay Coaching,
  and an exact complete Historical Result attachment
* Internal Dataset, Preparation, Opponent, Profile, historical-list, and
  comparison bundles with complete exact Root Result attachments

Installed CLI entry points consume this Application layer directly. By default
they omit internal bundles; `--include-provenance` selects only one redacted Root
Result plus artifacts actually returned. See
[Application orchestration](application_orchestration.md).

### Installed CLI foundation

Implemented:

* Installed CLI contract version `1`
* Exact `skat-ai = skat_ai.cli:main` Console Script and no GUI Script or alias
* `python -m skat_ai` through the same Package-owned implementation
* Legacy `python main.py` compatibility facade through at least `v1.0.0`
* One canonical parser preserving every option, with `--version` from Issue #142
  and cross-form `--include-provenance` from Issue #147
* Invocation-specific help with generic installed paths and repository Legacy
  examples
* Direct internal Application execution with unchanged JSON, presentation,
  quiet mode, output/export behavior, errors, and Exit Codes
* Exact installed/module/Legacy/Application/Public API parity for all seven Root
  workflows and representative submodes
* Exact Wheel and sdist metadata plus clean-install command validation in the
  existing two distribution environments

Issue #142 itself changed no Package version, Schema, example, generated
scenario, Provenance contract, or publication behavior. Issue #147 adds the
cross-form provenance flag without a Package-version or publication change. See
[Installed CLI](installed_cli.md).

### Field-level provenance contract foundation

Implemented:

* Internal field-provenance contract version `1`, independent of Package, API,
  schema, and other Domain versions
* Canonical RFC 6901 JSON Pointer helpers with Root, object, array, escape, and
  strict resolution behavior
* Frozen, slotted source references, field/subtree entries, exemptions, sidecar
  ledgers, coverage summaries, and Information Use Context values
* Complete, partial-legacy, and unavailable ledger status relationships
* Deterministic JSON-leaf enumeration, exact/subtree coverage auditing, and
  missing, orphaned, and overlapping-path detection
* Same-document dependency validation, deterministic cycle detection, and
  coarse availability monotonicity
* Visibility- and availability-aware use validation with stable information-
  policy errors
* Pure engine-private public redaction and deterministic public-safe serialization
* Explicit Confidence separation and unchanged specialized provenance contracts

Issue #143 constructs complete internal ledgers for flat and simulated live
Position decisions, propagates Immediate, Search, inference, Multi-Step, and
Policy Comparison provenance, and accounts for every Position Result leaf with
a partial-legacy ledger. Issue #144 extends internal retained-stage propagation
through flat retrospective Position Analysis, Historical Snapshots, Immediate
and Search Review, Replay Coaching, and selected Position/Historical Result
branches. Issue #145 adds all Dataset operations, Preparation, Opponent, Profile,
historical-list, comparison, and complete non-legacy Root workflow ledgers.
Issue #146 subsequently completes the Position/base Historical Result ledgers.
Issue #147 adds bounded public API exposure, strict Schema, Root output, and CLI
presentation for one complete redacted Result plus actual artifacts. Public
decision/intermediate attachments and broader enforcement remain open.

### Core analysis

Implemented:

* Core card rules and legal-card handling
* Card-point calculation
* Trump and trick-winner logic
* JSON-based position analysis
* Monte Carlo-style card analysis
* Expected point swing calculation
* Card recommendation
* JSON output for regression-friendly analysis

### Simulation

Implemented:

* Immediate trick simulation
* Multi-step simulation
* Canonical turn-phase enforcement for Immediate and Multi-Step analysis
* Opponent-turn Multi-Step preparation for supported left/right lead and response phases
* Simulation context tracking
* Strict simulation context checks
* Policy comparison across card-selection strategies
* Result serialization for multi-step and policy-comparison output
* One immutable private hidden-world root per Multi-Step path with owner-aware card removal and a fixed hypothetical skat
* One shared Policy Comparison root with equal independent immutable copies for policy paths
* Privacy-safe coherent-world count and status summaries without hidden cards
* Exact hidden-card constraints from local/public ownership, legitimately known skat, attributed public play, and confirmed legal failure to follow
* Exact DP compatible-world counts and ownership marginals with deterministic uniform labeled-assignment sampling
* Common compatible worlds for Immediate candidates, compatible Multi-Step roots, shared Policy Comparison models/roots, and later visible evidence progression
* Version-1 bounded-search information, private immutable exact complete-world state, deterministic legal transitions, eligibility, structural budget, terminal utility, aggregate result, privacy, and strict standalone-schema contracts
* Executable `perfect_information_minimax_v1` for one exact Suit, Grand, or normal non-overbid Null state with at most five remaining tricks, canonical full-window root values, deterministic below-root Alpha-Beta, invocation-local exact-only transposition reuse, and exact terminal settlement utility; all four Null variants use trick ownership, fixed-value settlement, and no card-point secondary objective
* Private compatible Search-world construction from `SearchInformationView`, exact counting with or without void evidence, canonical bounded enumeration, deterministic uniform IID sampling with replacement, retained duplicate accounting, strict exact-state materialization, and one frozen common legal-root world order
* Executable `compatible_world_minimax_v1` with shared exact-world recursion, frozen-order common-prefix scheduling, global nodes, per-world depth and exact-only cache, one post-selection timeout window, equal duplicate-sample weighting, aggregate ranking, and threshold-gated partial or timeout recommendations
* Explicit flat live `immediate_expected_value`, strict `bounded_search`, and Search-first `auto` recommendation methods with validated budgets, separate seeds, explicit fallback, report separation, schema output, CLI summaries, and privacy-safe examples
* Opt-in Search-aware Multi-Step and Policy Comparison with public-state re-search at every local decision, fresh per-decision budgets, domain-separated child seeds, coherent execution-world separation, strict stopping, auto fallback, eligibility-aware ranking, and compact privacy-safe diagnostics
* Flat post-game bounded Search with an independently executed Immediate baseline plus actual-card and Search-versus-Immediate aggregate comparisons
* Historical Search Review over every decision-time snapshot with stable private per-decision seeds and reconciled status, coverage, agreement, quality, and performance summaries
* Bounded-Search dataset evaluation over canonical validation/test defaults, optional stable global decision-prefix caps, and preserved zero-decision records
* Immutable `interactive_v1`, `historical_review_v1`, and `evaluation_v1` work-budget profiles
* Independent exhaustive Suit, Grand, and Null strict-improvement fixtures plus 32/64/128-draw convergence evidence
* Deterministic Suit/Grand/Null benchmark corpus and measured performance documentation with no calibrated latency guarantee

### Game history and scoring

Implemented:

* Completed-trick structure validation
* Completed-trick sequence validation
* Completed-trick rule-winner validation
* Explicit and completed-trick point summaries
* Game result summaries
* Schneider/Schwarz status summaries
* Versioned complete normal-play historical-game records
* Full-deal, ownership, play-order, follow-rule, winner, point, and settlement replay validation
* Exact-prefix historical records for declarer concession, defender concession, accepted declarer-card exposure, bounded defender open play, and open-card throwing
* One timed non-terminal defender-open-play or declarer-card-exposure continuation before normal completion or one supported terminal shortening
* Variable-length decision artifacts based on actual supplied play count

### Game declaration and settlement

Implemented:

* Game declaration metadata
* Canonical Suit and Grand declaration dependencies
* Official Suit `1..11` and Grand `1..4` matador bounds
* Game value summaries for suit, grand, and null games
* Automatic matador inference from known declarer-card context and safe concrete-declarer completed-trick ownership facts where possible
* Final single-game settlement summary
* Supported Suit/Grand overbid detection
* Supported Suit/Grand overbid settlement loss handling
* Bounded impossible Null settlement from an externally supplied Suit or Grand replacement
* Immutable [version-1 normative settlement matrix](settlement_normative_matrix.md)
  with direct-rule,
  approved-bounded, legacy, implementation-required, decision-required, and
  `v0.11.0` exclusion classifications

### Game-end handling

Implemented:

* Normal completion
* Declarer claims remaining tricks
* Structured concealed or verbal declarer concession with exact hand-card and defender-consent rules
* Structured defender concession with concrete party validation, joint liability, and preexisting-result preservation
* Unanimously accepted declarer card exposure with complete-card reconciliation and claimed-level settlement
* Ongoing ISkO 4.4.4 play after an objection with an exact all-player public declarer hand across Immediate, Multi-Step, Policy Comparison, and flat review
* Bounded exact defender open play for at most five unresolved tricks
* Ongoing ISkO 4.4.5/4.1.6 play with the exposing defender's exact returned public hand
* Open-card throwing with opposing-party assignment and bounded jack-only theoretical Schwarz exclusion
* Legacy declarer concession remaining-point assignment
* Defenders concede remaining tricks
* Immediate impossible Null declaration end handling
* Remaining-point assignment for legacy claim/concession scenarios
* No-assignment adjudicated defender win and declared/overbid settlement for structured declarer concession
* No-assignment defender-concession adjudication for Suit, Grand, and all Null variants
* Adjusted game-result summaries

### Performance rating

Implemented:

* Partial fixed-three-player SkWO-style single-game performance rating
* Declarer rating score
* Declarer rating points
* Counterparty/defender rating points
* Explicit separation between settlement score and rating score
* Single-rated-player list performance summaries from already aggregated totals, normalized contributions, and local analysis results
* Explicit fixed three-player list standings output
* SkWO 6.3.1 shared ranks for unresolved ties and optional external lot order
* Immutable version-1 fixed-three-player 36-position historical-list
  contracts with fixed stable identities, dedicated passed deals, dealer and
  historical-seat rotation, optional timestamp auditing, settlement-derived
  non-cumulative contributions, reconciliation, and deterministic serialization
* Immutable cumulative player totals and one provisional standings
  snapshot for every historical-list position
* Final SkWO standings with shared unresolved-tie ranks and optional exact
  external-lot application
* Immutable version-1 comparison of two or more independent completed
  lists with one reference, stable-ID alignment, final count and player-total
  deltas, resolved-only rank movement, and no progression or series aggregation
* Strict public source, request, aggregation, and comparison schemas with
  root-selected JSON and concise CLI workflows
* Three bounded examples and generated-output scenarios covering applied lot,
  unresolved all-passed tie, and resolved independent comparison

### Metadata and information control

Implemented:

* Strategic metadata
* Player profiles
* Profile-based policy recommendations
* Versioned overall, declarer, and defender profile evidence and heuristic confidence
* Explainable confidence-gated signals, classifications, and preset metadata
* Live-vs-post-game information enforcement
* `information_policy_summary` output
* Rejection of post-game-only information in `live_decision`
* Requirement that ended game reasons use `post_game_review`
* Version-1 privacy-safe hidden-card inference summaries with explicit non-behavioral, non-calibrated, no-future-information flags
* Internal version-1 field-provenance sidecar language with deterministic
  coverage, dependency, temporal, context-use, redaction, and serialization
  contracts
* Opt-in public version-1 Result and actual-artifact provenance with complete
  post-redaction exact-document coverage and no unredacted or intermediate
  attachment exposure

### Opponent modeling

Implemented:

* Opponent policy presets
* Optional profile-based policy presets
* Profile-confidence conflict resolution for cautious/aggressive preset evidence
* Deterministic aggressive-over-defender conflict precedence within one profile
* External opponent-statistics derivation and explicit stable-ID live application
* Independent left/right external bindings with actionable-only gating and manual/policy precedence
* Strict pre-game external-profile application to historical review through exact participant IDs and per-decision relative remapping
* Exact opponent-statistics aggregation from canonical timestamped training-dataset partitions with a strict optional cutoff
* Settlement-based role, win, Hand, and contract counts with per-player historical provenance and reusable export
* Rolling game-start as-of known-opponent profiles with strict temporal source selection
* Acting-player preferred-card and exact-card behavioral matching against the fixed `simple_lowest` baseline
* Actionable-only paired comparisons, coverage, and bounded evaluation breakdowns
* Separate left/right opponent policy settings
* Left/right profile-derived presets applied to effective left/right multi-step policies
* Left/right opponent policy input fields
* Left/right opponent policy CLI overrides
* Left/right opponent policy output settings
* Shared effective opponent-policy resolver for immediate, multi-step, and policy-comparison paths
* Left/right policy handling in multi-step opponent lead and response paths
* Explicitly activated opponent response policies in immediate analysis
* Explicitly activated opponent response policies in multi-step candidate completion
* Unified response-policy precedence for input presets, profile presets, and CLI overrides
* Basic defender cooperation improvements and issue #22's current heuristic defender-partnership scope:

  * safer defender lead
  * avoiding overtaking a winning partner when a partner-safe legal card exists
  * safe smear while preserving the partner's winning position
  * forced partner overtake using the lowest-point legal winning card
  * equal-point forced-overtake tie-break using weakest sufficient trick strength
  * winning-card selection using the lowest-point legal winner
  * equal-point winning-card tie-break using weakest sufficient trick strength
  * equal-point safe-smear tie-break using weakest trick strength
  * narrow second-hand trump conservation on zero-point non-trump leads when only trump wins and a losing discard exists
  * safer discard when the declarer is winning and the defender cannot win

### Post-game review

Implemented:

* Optional `actual_card_played` input
* Validation that the actual card is valid and legal in the analyzed position
* `post_game_review_summary` output
* Comparison between actual card and recommended card
* Expected point swing difference between actual and recommended card
* Decision quality classification:

  * `not_available`
  * `optimal`
  * `acceptable`
  * `suboptimal`
  * `mistake`
* Machine-readable decision factors
* Human-readable decision explanation
* Recommendation gap details:

  * `actual_card_rank`
  * `recommended_card_rank`
  * `candidate_count`
  * `better_card_count`
* Human-readable CLI output for post-game review summaries, including objective-aware Null review wording
* Unavailable post-game review shape when Immediate Analysis is unavailable
* Information-safe pre-play snapshots for every actual play in each supported historical terminal record
* Variable-length historical review, including zero-decision records, with deterministic seeds and reconciled player summaries
* Declared-Ouvert and continuation public hands at their exact decision-time visibility boundaries
* Flat and Historical Search review with independent Immediate baselines and strict aggregate comparison output
* Replay Coaching contract version 1 with separate decision-time evidence and retrospective actual-card assessment, deterministic Search-first evidence priority, stable impact tiers/factors/limitations, and unchanged existing review output
* Replay Coaching prioritization version 1 with at most five deterministic Key Decisions, separate decision-opportunity and recorded-outcome Turning Points, complete-normal Null fallback, threshold-free high impact, and no causal claim
* Replay Coaching guidance version 1 with two-occurrence one-game
  patterns by player, role, phase, and contract; separate actionable and
  descriptive patterns; one fixed-template recommendation per Key Decision; and
  at most five ranked, evidence-deduplicated actionable pattern recommendations
* Complete Replay Coaching report version 1 composed from one retained
  Historical Search Review coaching analysis, with privacy-safe game context,
  separately attached final outcome context, reconciled coverage, zero-preserving
  scope summaries, canonical limitations, and unchanged existing review output
* Internal retrospective provenance version 1 with decision-time input and
  analysis separated from actual-card assessment, complete Snapshot/Review/
  Coaching attachments, final-outcome isolation, and no additional analysis pass
* Public `--historical-replay-coaching` JSON and human-readable output, strict
  standalone schema, conditional coaching-only attachment, one-pass combined
  Search Review output, and normal Grand/Null/shortened generated scenarios

### Training and evaluation data

Implemented:

* Versioned normal-play and shortened-game training and evaluation dataset records
* Required source provenance and explicit `train`, `validation`, and `test` partitions
* Deterministic zero-through-30 sample conversion from each supported historical game
* Relative model-facing features and `actual_card_played` version-1 labels
* Duplicate identity and cross-partition game/source leakage rejection
* Optional version-1 known-opponent and unseen-player partition policy metadata
* Deterministic exact-player membership, pairwise/three-way overlap, directed known-opponent coverage, and unseen-player compliance audits
* Strict declared unseen-player disjointness with backward-compatible unspecified policy intent
* Reuse of the dataset as the multi-game source for sample-free historical opponent-statistics aggregation
* Deterministic bounded-Search evaluation on selected partitions with one global decision cap, zero-decision preservation, quality-gate arithmetic, and aggregate breakdowns
* Internal preparation version `1` with unpartitioned source Records, explicit
  positive integer weights, split-safe facts, order-independent identity/content
  fingerprints, and mode-separated deterministic SHA-256 seed helpers
* Internal partition-plan version `1` with caller-supplied complete assignment
  validation, reasoned unavailable plans, exact Record-count target arithmetic,
  strict Known-opponent temporal coverage, strict unseen-player disjointness,
  existing-audit reuse, and lossless version-1 dataset materialization
* Exact deterministic `temporal_known_opponent_v1` assignment generation with
  parsed-instant groups, exhaustive contiguous two-cut scanning, complete Train
  player coverage, integer Record-count optimization, tie-only seed semantics,
  source-order-independent proofs, and one final plan construction
* Deterministic `component_balanced_unseen_player_v1` assignment generation with
  exact transitive Player-connected components, dedicated content-isolated
  selector identities, non-empty greedy Record-count placement, strict whole-
  component move/swap improvement, source-order independence, and one final plan
* Public `training_dataset_preparation_input` workflow with fixed mode-to-
  algorithm dispatch, complete or explicit unavailable Plans, lossless existing
  version-1 Training Dataset materialization, and a reconciled partition audit

### Validation and documentation

Implemented:

* Input JSON schema
* Output JSON schema
* Focused historical-game, decision-snapshot, historical-review, training-dataset, and historical opponent-statistics aggregation schemas
* Focused strict hidden-card inference summary schema
* Focused strict bounded-search aggregate result schema
* Focused strict flat post-game Search, Historical Search Review, Historical Replay Coaching, and bounded-Search evaluation schemas
* Strict automatic Training Dataset preparation request, partition Plan, and
  preparation output schemas
* Strict public field-provenance Schema referenced from every Root output branch
* Input example schema validation
* Generated-output schema validation
* Full check script with Ruff, packaged-schema parity, input schema validation,
  generated-output validation, distribution validation, and pytest
* Topic-specific documentation split into `docs/`
* Project handoff documentation
* Authoritative requirements traceability and testable `v1.0.0` scope
* Version-1 settlement normative matrix and table-driven runtime-kind coverage
* Exact public API export, immutable-document, compatibility, error, and legacy CLI tests
* Focused public facade parsing, schema, option mapping, all-workflow execution,
  artifacts, parity, no-I/O, error translation, and normal-state tests
* Focused field-provenance constants, JSON Pointer, immutable-value, coverage,
  dependency, temporal, Information Use Context, redaction, serialization,
  Confidence-separation, and compatibility tests
* Focused retrospective provenance ordering, cardinality, temporal isolation,
  Search-status, continuation, external-profile, redaction, no-rerun, and public-
  boundary tests
* Focused Dataset/list/opponent provenance constants, ordering, all-workflow
  bundles, Feature/Target separation, audit isolation, rolling/Search stages,
  split restrictions, materialization, Profile derivation, 36 Entry Facts,
  progression prefix safety, external lots, comparison deltas, redaction,
  call-count, and public-boundary tests
* Focused complete Result provenance tests across Declaration, Value, Overbid,
  score, raw/adjusted Results, Settlement, Performance, lists, every Position
  ending and continuation, canonical Historical replay, all terminal/event
  combinations, dependency rejection, redaction, determinism, and call counts
* Focused public field-provenance API/CLI parity, seven Result mappings, actual-
  artifact mapping, privacy rejection, complete recomputed coverage, and seven
  appended generated-output scenarios
* Focused Session revision-zero, conflict, atomic rejection, metadata, phase,
  Live/Retrospective Deal, Declaration, Matador, Skat/Discard, ownership,
  Bedienpflicht, trick, continuation, Game-end, promotion, readiness,
  deterministic replay, forged-State, and execution-count tests
* Focused Session export constants, result invariants, unavailable gating,
  exact Root/Player/Deal/Declaration/Discard/Trick mapping, normal and terminal
  endings, continuation chains, canonical round trips, immutability, promotion,
  determinism, no-execution counts, and public-boundary tests
* Focused Session Position export, declared-Ouvert public-hand, Decision
  Checkpoint, Undo/correction, suffix-replay, and lineage tests
* Focused private Session persistence contract, fingerprint-oracle, strict codec,
  replay, lineage, canonical-file, optimistic-conflict, and atomic-replacement
  tests in `tests/test_session_persistence_contracts.py`,
  `tests/test_session_persistence_codec.py`, and
  `tests/test_session_persistence.py`

### CLI and workflow usability

Implemented:

* Improved CLI help text and command discoverability
* Optional `--quiet` mode for automation-friendly JSON-output runs
* Curated workflow walkthroughs for common user-facing CLI commands
* Generated-output validation for representative user-facing workflows, including late-game history-heavy live input
* Policy-comparison-only CLI output handling
* CLI sample-bound validation fixes
* Complete historical-game validation, optional snapshot output, and optional historical review
* Separate training-dataset conversion with strict rejection of unrelated analysis options
* Historical opponent-statistics aggregation with partition/cutoff selection, separate normal output and export paths, and quiet output
* Isolated `--audit-dataset-partitions` workflow with optional policy-mode resolution
* `--historical-search-review` with explicit `--search-seed` and named profile selection
* `--historical-replay-coaching` with shared Search/Immediate settings and optional combined Search Review output
* `--evaluate-bounded-search` with repeatable partition selection and optional global decision cap
* Root-selected automatic Training Dataset preparation with only `--input`,
  `--output`, `--quiet`, and the cross-workflow `--include-provenance` option,
  concise card-free Plan presentation, and no algorithm or weight override
* Installed, module, and Legacy invocation parity through one Package-owned CLI
* Exact `--version`, command-specific help, unchanged output and error behavior,
  and clean-install command validation

## Current known limitations

### Gameplay and rules

* The engine has one bounded exact-state Suit, Grand, and normal non-overbid Null
  perfect-information solver, not a full or general hidden-information solver.
* The engine is not a complete official tournament system.
* The engine focuses on analysis and simulation, not on training a machine-learning model.
* The public Python API and installed CLI execute all seven Root workflows from
  source, Editable, Wheel, and sdist installations.
* Full official settlement nuance coverage is not complete.
* Legacy claim and concession reasons assign remaining points; the first three structured shortening kinds preserve them as unplayed, bounded defender open play records exact rule assignment, and open card throw records unconditional opposing-party rule assignment.
* The engine verifies only bounded ISkO 4.4.5 defender rest-trick claims; no general claim-verification protocol exists.
* Structured declarer concession models accepted defender consent; structured defender concession applies joint liability without partner consent. Disputes are not modeled.
* Multi-Step intentionally does not auto-complete every opponent-only continuation; valid phases where the local player has already acted stop with `unsupported_turn_phase`.
* Impossible Null settlement requires an external Suit or Grand replacement selection; it remains incomplete when that selection or its required matadors are unavailable.
* Matador inference uses currently known declarer-card context and safe concrete-declarer completed-trick ownership facts; it does not reconstruct all possible matador information from complete historical trick ownership in every scenario.
* Historical records support normal completion and all five terminal shortenings with at most one optional timed defender-open-play or declarer-card-exposure continuation. Multiple non-terminal events, arbitrary event streams, other claims, and other end reasons are not represented there.
* Historical corrected play and isolated or specific-trick claims remain incomplete; unlimited proof, simultaneous throws, and arbitrary event streams are outside `v0.11.0`; general settlement coverage is incomplete.
* Dataset, Preparation, Opponent, Profile, list, comparison, live Position,
  retrospective Review/Coaching, and complete Position/Historical Root Results
  have internal provenance. Public output exposes only the bounded redacted Root
  Result plus actual artifacts; decision/intermediate and end-to-end provenance
  remains incomplete.
* A coherent Multi-Step root is one compatible hypothetical execution world, not proof of the real deal or exhaustive search. Hidden-card inference is bounded to confirmed structural decision-time evidence and does not infer tactics or actual ownership.
* Version-1 bounded-search contracts, direct exact-world and compatible-world
  Suit/Grand/Null Minimax, and private deterministic compatible-world selection
  with strict exact-state materialization exist. Compatible execution retains
  only one exact common completed prefix and remains determinization-based and
  subject to strategy fusion. Null requires a bid no greater than its fixed
  value; overbid Null replacement selection remains unsupported. Flat and
  opt-in Multi-Step/Policy Comparison live routing, CLI summaries, and explicit
  auto fallback exist. Flat post-game Search, Historical Search Review, and
  Search-versus-Immediate dataset evaluation now use immutable versioned work
  profiles. Search remains bounded late-game determinization, sampled quality is
  not calibrated, and measured performance provides no latency guarantee.
* Complete Known-opponent and unseen-player plans can be generated, validated,
  and losslessly materialized through the public mode-derived workflow. It has no
  new algorithms, algorithm selector or override, default weights, CLI overrides,
  fallback, or partial Plan. Global optimization, ratio guarantees, Sample- or
  Player-count balancing, component splitting, model training, and automatic
  evaluation are not implemented.
* Replay Coaching now has public version-1 evidence, impact, prioritization, one-
  game cross-decision patterns, deterministic actionable recommendations, strict
  schema/CLI/report output, and isolated retrospective context. Tactical motifs,
  cross-game player analysis, broader Search, and causal attribution remain
  unimplemented.

### Performance rating

* Performance rating is partially implemented for fixed three-player single-game declarer rating and bounded list-aware summaries.
* The complete historical 36-position contracts provide cumulative aggregation,
  progression, final standings, and independent-list comparison through strict
  public JSON/schema/CLI workflows.
* `rating_score` currently equals `declarer_rating_score`.
* Counterparty points are exposed separately and are not aggregated into the declarer's rating score.
* Formal series aggregation, tournament management, and official federation report formats are not required product workflows.
* Four-player table performance rating is not modeled because the project assumes a fixed three-player table.

### Opponent modeling

* Opponent behavior is still simplified and rule-based.
* Defender cooperation has improved, but it is still heuristic and not a full tactical model.
* Defender cooperation assumes the fixed three-player table.
* Defender partnership inference is strongest in the currently supported second-hand path.
* There is no complete rear-hand partnership model.
* There is no dedicated null-game defender-partnership strategy.
* There is no stable declarer/partner identity when the local player itself is only known generically as `defender`.
* Defender cooperation does not use perfect-information solving, search, machine learning, behavioral/Bayesian inference, or broader tactical hidden-card inference.
* Opt-in profiles can influence policy presets, and exact statistics can be aggregated from historical games, but profile behavior is not learned.
* Profile derivation uses documented deterministic thresholds and heuristic evidence bands, not calibrated uncertainty.
* External-statistics derivations require profile-preset opt-in plus either explicit live side bindings or exact time-safe historical participant matching.
* Historical aggregation accepts compliant known-opponent and unseen-player datasets but does not infer policy, weight or merge sources, manage multiple captures, apply policies automatically, or learn behavior. The separate rolling evaluation measures observed behavioral matching only, not profile quality or strategic strength.

### Information modeling

* The project enforces the main live-vs-post-game information boundaries.
* The engine still depends on the correctness of the provided position context.
* Some older or intentionally minimal completed-trick inputs may not contain enough metadata for full verification.
* Live decision examples should not contain post-game-only information.
* ISkO 4.4.4 continuation is a narrow rule-authorized exception that exposes only the exact current declarer hand; defender reaction cards remain hidden.
* ISkO 4.4.5/4.1.6 continuation is a second narrow exception that fixes only the exposing defender's returned complete current hand; the declarer, partner, and skat remain protected.
* Declared Ouvert fixes only the exact current declarer hand from declaration visibility; it can coexist with a disjoint returned defender hand.
* ISkO 4.4.6 open throw exposes only the complete thrown hand. A non-throwing local hand is redacted, and no hidden complete hand or exact proof is emitted.

## Release baselines

### v0.13.0: Stable API, installable tooling, and public field provenance

The published `v0.13.0` milestone is complete through functional Issues #137
through #147. Issue #148 completed Release preparation. The Release points to
commit `abd1ad3`, contains 62 authoritative Schemas and 62 Packaged Schema
Resources, validates 77 deterministic generated-output scenarios, passes 5,399
pytest tests, and requires Python 3.13 or newer. Publication was performed
manually by the maintainer, and GitHub Releases remains authoritative. No
Package-index or PyPI publication is claimed.

The milestone provides stable API contract version `1`, reusable Application
orchestration version `1`, the executable public facade, Setuptools Wheel and
sdist artifacts, Package Resource schemas, typing and version metadata,
installed/module/Legacy CLI parity, complete internal Root Result provenance for
all seven workflows, and bounded opt-in public Root Result and actual-artifact
provenance. Default Root output remains unchanged when provenance is omitted.

The active `v0.14.0` milestone targets interactive Live and Retrospective Session
capture. Issue #150 implements the internal contract foundation, and Issue #151
implements deterministic internal Command application and incremental
validation. Issue #152 implements internal canonical Retrospective Historical
Request export without workflow execution. Issue #153 implements internal
information-safe Position Request export, declared-Ouvert public-hand capture,
and immutable pre-Play Decision Checkpoints without workflow execution. Issue
#154 implements immutable strict-prefix Undo, one-command correction, linear
suffix replay, valid partial corrected States, and Checkpoint lineage. Issue #155
implements private deterministic Session persistence/resume, State and content
fingerprints, strict reconstruction and replay, caller-supplied frozen
Checkpoints with recomputed lineage, optimistic expected-fingerprint writes,
canonical files, and atomic same-directory replacement. Session-triggered
analysis, actual-card Checkpoint attachment, Public API, Provenance, Schemas, CLI,
examples/generated output, automatic Checkpoint collection, end-to-end capture,
and UI work remains.
Online-platform adapters, browser extensions, and website scraping remain
outside this bounded milestone.

### v0.12.0: Fixed-three-player historical lists and deterministic dataset preparation

The published `v0.12.0` milestone is complete through functional Issues #127
through #134 and release-preparation Issue #135. The release points to commit
`bbf955e`, validates 70 deterministic generated-output scenarios, passes 4,762
pytest tests, and requires Python 3.13 or newer. Publication was performed
manually by the maintainer, and GitHub Releases remains authoritative. Issue
#136 synchronized the historical publication status.

The milestone exposes fixed-three-player historical-list source, cumulative
aggregation, and independent comparison through strict JSON/schema/CLI workflows.
It also exposes bounded automatic Training Dataset preparation through fixed
mode dispatch, complete or explicit unavailable results, strict schemas, CLI,
and three examples. The prior 67 scenarios remain unchanged; the three Issue
#134 scenarios bring the package matrix to 70.

### v0.11.0: Information-safe Replay Coaching and structured historical outcomes

The historical published `v0.11.0` milestone is complete. Issues #118 through
#124 complete the functional milestone, and Issue #125 completed release
preparation. The release points to commit `cfd28e5`, validates 64
deterministic generated-output scenarios, and passes 4,392 pytest tests.
Publication was performed manually by the maintainer, and GitHub Releases remains
authoritative for publication status.
Issue #126 synchronized the historical publication status.

The milestone provides the immutable 61-case settlement matrix, one bounded
continuation-before-shortening historical chain, information-safe Replay
Coaching evidence and impact, deterministic Key Decisions and both Turning Point
types, one-game patterns, deterministic recommendations, complete report
composition, and the opt-in public JSON/schema/CLI workflow.

### v0.10.0: Information-safe bounded Search across compatible worlds

The historical published `v0.10.0` release completed Issues #107 through #115 as
its functional milestone. Issue #116 completed release preparation, followed by
manual maintainer publication. The release points to commit `b4c8738`, validates
59 deterministic generated-output scenarios, and passes 4,075 pytest tests.
Issue #117 synchronized the historical publication status.

The milestone provides bounded-Search contracts, immutable exact state, Suit,
Grand, and all four normal non-overbid Null solving, compatible-world counting
and selection, common-prefix aggregation, live and simulated integration,
fallback, Historical Search Review, dataset evaluation, immutable profiles,
quality and convergence evidence, and measured reference performance.

### v0.9.0: Structured game endings and coherent hidden information

The historical published `v0.9.0` release tag points to commit `0679760`, and
Issues #86 through #104 are complete:

* #86 through #92 added structured concessions and exposures, bounded defender-open-play adjudication, open-card throwing, and both exact-public-hand continuation paths.
* #93 through #101 added all five exact-prefix historical terminal events, both timed non-terminal continuation events, variable-length decision and dataset workflows, and shortened-game opponent workflows.
* #102 made Immediate, supported Multi-Step, Policy Comparison, flat review, and Historical Review recommendation paths declared-Ouvert-aware.
* #103 preserved one coherent private hidden world per Multi-Step path and one shared root across independent Policy Comparison copies.
* #104 added exact evidence-constrained compatible-world counts, marginals, deterministic uniform sampling, decision-time-safe workflow integration, and privacy-safe uncalibrated summaries.

The published baseline validates 52 deterministic generated-output scenarios
and passes 3,558 pytest tests. GitHub Releases is the authoritative publication
record. Issue #105 completed release preparation, and Issue #106 synchronized
the publication status.

### v0.8.0: Explainable and time-safe opponent intelligence

The bounded Issues #78 through #84 milestone is complete:

* #78 added versioned external opponent-statistics records with stable identity, provenance, eight percentages, and optional exact counts.
* #79 added deterministic explainable profile derivation with scoped heuristic confidence and actionable gating.
* #80 applied actionable profiles to independent live left/right sides through exact stable-ID bindings while preserving manual and explicit policy precedence.
* #81 applied profiles to historical review through exact participant matching, strict `captured_at < played_at` safety, and per-decision side remapping.
* #82 aggregated exact settlement-based statistics from timestamped historical dataset games and exported records for existing live and historical loaders.
* #83 evaluated rolling acting-player card imitation with strict as-of history, the fixed `simple_lowest` baseline, policy-equivalent preferred cards, and actionable paired metrics.
* #84 added known-opponent and unseen-player dataset policies, exact membership and overlap audits, directed coverage, and strict declared unseen-player disjointness.

### v0.7.0: Rules confidence and information-safe historical workflows

The documented `v0.7.0` issue scope is complete:

* #69 defined the v1.0 scope, requirements traceability, and project baseline.
* #70 enforced canonical Suit/Grand declaration dependencies and matador bounds.
* #71 aligned fixed three-player standings ties with SkWO 6.3.1.
* #72 added bounded settlement for impossible Null declarations.
* #73 added complete normal-play historical-game records.
* #74 added information-safe snapshots for all 30 historical decisions.
* #75 added bounded complete historical-game decision review.
* #76 added versioned historical training and evaluation dataset records.

### v0.6.0: From single-position analysis to credible list-aware review workflows

The documented `v0.6.0` issue scope is complete:

* #62 added fixed three-player list standings output.
* #63 expanded list-performance examples and generated-output validation.
* #64 improved post-game review example quality and explanation coverage.
* #65 added controlled left/right opponent policy effect coverage.
* #66 used profile confidence in bounded opponent-strategy decisions.
* #67 audited settlement and overbid edge-case coverage.
* #68 prepared release metadata, changelog, roadmap, and handoff documentation.

No `v0.6.0` commit, merge, tag, publication, release, or issue-closeout action
remains pending.

## v1.0 direction

The [requirements traceability matrix](requirements_traceability.md) is the
authoritative audit of current ISkO, SkWO, and skat-ai product support. The
[v1.0 scope](v1_scope.md) defines required product directions, unresolved
implementation details, and testable completion gates.

Before `v1.0.0`, the project still requires tactical and cross-game Coaching,
remaining approved settlement nuance, broader field-level provenance
enforcement, and end-to-end interactive live and retrospective Session capture.
The immutable internal Session contract, deterministic transition and history-
edit foundations, canonical Retrospective Historical and information-safe
Position Request export, replay-verified Decision Checkpoints, and private
deterministic persistence/resume now exist. The executable
public facade, internal Application layer, installable library distributions,
and stable installed CLI interface are implemented. API contract
version `1`, exact public namespaces, immutable document wrappers, compatibility
metadata, and stable public errors are implemented. General claim verification
and historical end reasons outside the
supported bounded set also remain incomplete. Structured concessions and
exposures, bounded defender open play, open-card throwing, supported historical
terminal and continuation events, variable-length workflows, Ouvert-aware
recommendation, coherent hidden worlds, and bounded structural inference are
already implemented.
The approved [settlement matrix](settlement_normative_matrix.md) defines their
normative scope, and the bounded continuation-plus-terminal-shortening sequence
is implemented through delegation to the existing terminal cases. Claims,
Concessions, and Final Settlement remain partially supported.

Full auction modeling, learned opponent profiles, machine-learning card-decision
models, and platform or browser adapters are planned after `v1.0.0`. Formal
series aggregation, tournament management, and official federation report
formats are not required. Four-player tables are the only unconditional
exclusion.

The published `v0.10.0` milestone is complete.
Version-1 bounded Search/Solver
information, quality, determinism, budget, exactness, aggregate-result, privacy,
exact complete-world state, and deterministic legal-transition contracts are
implemented together with bounded direct and compatible-world Minimax for late
Suit, Grand, and normal non-overbid Null states. Compatible execution uses the
same exact evaluator in frozen selected order, retains only complete common-
prefix aggregates, and preserves equal duplicate-draw weight. Exhaustive
coverage is exact across compatible worlds, while sampled and partial claims are
narrower; determinization and strategy fusion prevent an optimal imperfect-
information policy claim. Flat live workflow and explicit fallback integration
are implemented; opt-in Multi-Step and Policy Comparison, flat post-game review,
Historical Search Review, and Search-versus-Immediate dataset evaluation are also
integrated. Immutable work profiles, independent quality fixtures, sampled
convergence checks, and a reproducible performance corpus provide bounded
evidence. They do not provide calibrated sample quality, a latency guarantee,
information-set policy search, or complete-contract solving, so the stronger-
search completion gate is not closed.

The published `v0.11.0` milestone is complete through functional Issue #124, and
Issue #125 completed release preparation. The milestone establishes the
settlement matrix and bounded continuation-before-shortening sequence, then
delivers public one-game Replay Coaching through schema, CLI, examples, and
generated-output coverage. Tactical motifs, cross-game Coaching, ratings, causal
attribution, and stronger Search remain outside this bounded result.

The published `v0.12.0` milestone is complete. Issue #127 adds
internal list contract version `1` for all 36 ordered positions and passed
deals, Issue #128 adds internal cumulative totals, progression, final standings,
and exact external-lot application, and Issue #129 adds independent completed-
list comparison without series aggregation. Issue #130 exposes those retained
contracts through strict root-selected JSON, schemas, CLI output, exactly three
examples, and exactly three appended generated-output scenarios. Issue #131 adds
the internal version-1 source, weight, fact, fingerprint, seed, complete/
unavailable plan, validation, audit-reuse, and materialization contracts. Issue
#132 adds the deterministic temporal Known-opponent generator. Issue #133 adds
deterministic Player-connected unseen-player assignment with greedy placement and
strict local improvement. Issue #134 exposes those contracts through the root-selected
`training_dataset_preparation` workflow, strict request/Plan/output schemas,
exactly three examples, and exactly three appended generated-output scenarios.
Its original CLI accepted only `--input`/`--output`/`--quiet`; Issue #147 later
adds the cross-workflow `--include-provenance` option without an algorithm
override. Complete results materialize the existing
version-1 dataset and audit; unavailable results succeed with null dataset/audit
and no partial Plan. No new algorithm, algorithm override, fallback, default
weight, balancing guarantee, model training, or automatic evaluation is added.
Issue #135 completed package metadata and release-documentation preparation
before the maintainer's manual publication at commit `bbf955e`. The published
baseline validates 70 generated outputs and passes 4,762 pytest tests.

The `v0.13.0` package baseline includes the foundation from Issue #137 through
stable API contract version `1`, exact public exports,
immutable JSON documents, compatibility metadata, stable errors, and unchanged
legacy Root CLI behavior. Issue #138 adds the internal field-provenance
language, immutable sidecar ledger, coverage and dependency validation,
Information Use Context, public redaction, and safe serialization. Issue #143
adds internal live Position propagation and adversarial enforcement. Issue #144
adds internal retrospective Position, Historical Review, Historical Search
Review, and Replay Coaching propagation. Issue #145 adds Dataset, Preparation,
Opponent, Profile, historical-list, and comparison propagation with complete
Root ledgers. Issue #146 completes non-legacy Position/base Historical Result
propagation. Issue #147 adds bounded public Root Result and actual-artifact
provenance, strict Schema, API/CLI opt-in, and seven append-only scenarios. Issue
#139 completes internal
Application extraction with immutable orchestration version `1` contracts, all
seven no-I/O handlers, five Training Dataset operations, injected Opponent
Statistics, auxiliary artifacts, and legacy CLI transport parity. Public API
exports remained unchanged at that issue boundary. Issue #140 adds the
executable public facade, direct immutable options, public results and artifacts,
lazy schema validation, stable error translation, and all-seven-workflow parity.
Issue #141 adds Setuptools
metadata, Package Resource schemas, typing and version metadata, Wheel/sdist and
clean-install validation, and local/CI gates without an installed CLI or
publication. Issue #142 adds the exact installed Console Script, module entry
point, Package-owned canonical CLI, Legacy facade, version output, and clean-
install CLI/API parity without publication. The published `v0.13.0` baseline has
62 schemas and 77 generated-output scenarios; published `v0.12.0` facts remain
70 scenarios and 4,762 tests. Issue #148 set Package version `0.13.0` and
completed Release metadata and current-state documentation preparation without
product behavior changes before manual publication at commit `abd1ad3`. Later
milestone numbers remain planning containers rather than fixed contractual
releases.

## Open technical cleanup

Recommended cleanup areas:

* Maintain `CHANGELOG.md` for release notes as future milestones are completed.
* Keep README short and topic-focused.
* Keep topic-specific docs in `docs/` aligned with implemented behavior.
* Continue improving JSON schema coverage where useful without duplicating too much Python validation logic.
* Centralize any remaining duplicated CLI/configuration constants.
* Consider fully centralizing immediate and multi-step opponent-policy precedence once the existing multi-step compatibility behavior can be changed safely.

## GitHub issue status

Issue tracking should continue to use small, focused follow-ups. New issues
should distinguish the current published `v0.13.0` baseline, historical
`v0.12.0` and older Release evidence, the authoritative publication state shown
by GitHub Releases, the active `v0.14.0` development milestone and its implemented
Issue #150 Session contracts, Issue #151 transition foundation, Issue #152
Retrospective Historical Request export, Issue #153 Position export and Decision
Checkpoints, Issue #154 Undo/correction and Checkpoint lineage, and Issue #155
private deterministic persistence/resume and stale-write conflict detection;
requirements explicitly required for `v1.0.0`; planned post-v1.0 work;
not-required workflows, and unconditional exclusions.
