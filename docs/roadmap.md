# Roadmap

This document tracks completed areas, known limitations, and planned improvements for `skat-ai`.

## Historical published milestone: v0.15.0

`v0.15.0` provides usable manual post-game capture of one EuroSkat 36er Standard
Match from a descriptive video source. Issue #160 establishes the internal
immutable version-1 Match metadata foundation:

* Match Capture identity and caller-supplied metadata;
* millisecond media bounds;
* `youtube_video`, `other_video`, and `manual_observation` source relationships;
* an append-only named tournament-format registry;
* the sole executable `euroskat_36_standard_v1` definition with three Players
  and 36 Games;
* exactly three fixed-place Match participants;
* optional immutable snapshots of existing Opponent Statistics records;
* one explicit perspective Match Player, separate from the application user;
* deterministic defensive serialization without network, path, generated ID,
  or generated time data.

Issue #161 adds the internal observed single-Game and commentary foundation:

* exact Match linkage, Match position, historical seats, and perspective;
* optional perspective initial hand, original Skat, and null-versus-empty
  Discard evidence;
* zero through 30 chronological Plays with bounded partial validation;
* exact complete Suit, Grand, and Null replay from reconstructed playable hands;
* free-text commentary on any Player Decision and linked later responses;
* deterministic evidence and reconstruction-capability summaries without hidden
  completion.

Issue #163 adds the internal persistent Match Workspace foundation:

* exactly 36 authoritative empty, observed-Game, or passed-deal Slots;
* exact existing Dealer and historical-seat rotation across twelve rounds;
* partial observed-Game placement and immutable revisioned changes;
* bounded Match-definition correction and global media-time ordering;
* deterministic occupancy/evidence Progress without materialization;
* domain-separated Workspace and content SHA-256 fingerprints;
* strict nested Resume and private canonical UTF-8 file Load;
* expected-content-fingerprint conflicts and same-directory atomic Save.

Issue #164 adds the internal transport-free rapid-entry Application foundation:

* immutable Card entries, Position Views, and Capture Results;
* exact rotation, capture state, current Trick, next Player, blockers, Evidence
  Summary, and Progress derivation;
* exact legal perspective choices or bounded observation candidates without
  hidden completion;
* deterministic Game and annotation IDs;
* focused setup updates through complete observed-Game rebuilding;
* atomic single/batch Play append with automatic Player and Decision derivation;
* Play truncation with invalid-annotation cleanup;
* free-text Commentary and later-response-link editing;
* existing Passed Deal and clear-operation wrappers.

Issue #165 adds the first usable private local no-JSON Match Capture interface:

* leading installed/module/Legacy `capture` dispatch with one Console Script;
* one explicit Workspace, strict Resume or browser creation, and all 36 Slots;
* setup, canonical Card, correction, Commentary, Response Link, pass, clear, and
  metadata forms with automatic Player/Decision derivation;
* locked exact-revision plus content-fingerprint compare-and-swap autosave;
* explicit Reload after persistence conflict with no retry or merge;
* token/same-origin loopback security and packaged progressive local assets.

Issue #166 adds editable Match-bound Player Statistics preparation:

* one optional immutable Snapshot per participant and separate later-Match
  Snapshots for the same stable Player;
* deterministic revision-bound IDs plus immutable set, replace, unchanged,
  conflict, and clear outcomes over existing definition replacement;
* existing Opponent Statistics validation, normalized Profile conversion, and
  explainable Profile derivation without new thresholds;
* strict `captured_at < played_at` eligibility and canonical fixed-place eligible
  input preparation, including an eligible Perspective Player;
* private browser Add, Replace, and Clear forms, read-only historical aggregation
  presentation, temporal warnings, prepared Profile presentation, and unchanged
  optimistic autosave.

Issue #167 adds internal evidence-aware review and materialization preparation:

* partial Perspective-only and complete all-Player acting-own-hand Decision
  reconstruction without future-opponent leakage;
* before-actual-Card snapshots with existing Skat and declared-Ouvert semantics;
* time-safe relative left/right Profile bindings without application;
* strict complete-Deal normal-completion Historical Game materialization using
  Match-level `played_at` without media-offset-derived absolute times;
* existing unpartitioned Training source Records without Plans, partitions, or
  samples;
* exact 36-Slot `empty`, `partial`, or `complete` Workspace summaries and counts;
* complete fixed-list construction with Passed Deals, existing aggregation,
  Progression, standings, and external-lot behavior;
* Commentary and Response Links retained only as Workspace sidecars;
* no workflow execution and no persistence, browser, public, Schema, example,
  generated-output, CLI, or Package-version change.

Issue #168 completes the functional local Match Capture milestone:

* one explicit prepared-Decision Position execution through Immediate, bounded
  Search, or `auto`, including supported partial snapshots;
* retrospective actual-Card attachment without an optimal-label claim;
* eligible actor-relative Profile binding and application only through existing
  supported Position behavior, including disabled and nonactionable outcomes;
* strict Historical availability plus selected Snapshot, Immediate Review,
  Search Review, and Replay Coaching modes through one existing Application
  invocation;
* Historical Profile application only through existing enabled Immediate Review
  behavior, with no claimed Profile effect on Search or Coaching;
* no-workflow Match materialization with counts, standings, unresolved lot state,
  and twelve round ends;
* deterministic SHA-256, revision-scoped, process-local reports capped at eight,
  cleared or discarded under the documented mutation/reload/concurrency rules;
* authenticated loopback canonical Root Result, materialization, Historical,
  unpartitioned Training-source, list-input, and list-aggregation downloads.

Issue #168 completed the functional milestone without changing the Package.
Issue #169 completed Package version `0.15.0`, matching version assertions,
Changelog, and current-state documentation as Release preparation. The
maintainer published `v0.15.0` manually at commit `ec1c154`, and Issue #170
synchronizes publication status. Public Match
API and Schema/data workflow, public/persisted Player Catalog,
public or task-specific communication Dataset workflows, database/remote
deployment, and broader pre-v1 work remain open. Issues #171 through #179
subsequently add separate private
immutable Learning Corpus Snapshot/reference and lightweight Catalog contracts,
deterministic fixed-root persistence, strict Store Resume and orphan reporting,
explicit Workspace import, and a derived Current-Snapshot Player/Statistics view
plus minimized Human Commentary/Response and method-bound Strategy Teacher
Evidence exports, one unpartitioned task-neutral Learning Dataset version `2`,
and private Match-group-safe partition preparation with leakage audits
plus deterministic descriptive cross-game summaries and path-free export
plus the private local one-root Learning Corpus/Dataset-v2 browser workflow
without changing the published `v0.15.0` Package.
No YouTube or EuroSkat integration, ranking, qualification, prize, fee, or bonus
behavior is implemented.

Issue #162 characterizes and modularizes the existing Root and Session CLI
transport boundaries before those later layers. Compatibility facades preserve
installed/module/Legacy behavior, while focused modules separate parsing,
validation, Application adaptation, dispatch, transport, persistence,
Checkpoints, handlers, and presentation. CLI remains a leaf adapter. Issue #164
supplies the transport-free Capture Application layer; Issue #165 composes it in
the separate leaf browser/CLI transport without changing Root or Session rules.

## Completed major areas

### End-to-end Live and Retrospective Session capture

Implemented by Issue #150 for the published `v0.14.0` milestone:

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
replacement. Issue #156 adds the stable Public Session API, optional complete
Session Provenance, a standalone Schema that brought the published `v0.14.0`
baseline to 63-Schema parity, and clean-install
validation. Issue #157 adds stable public file Save/Load, Decision Observation,
isolated Checkpoint review export, automatic exact Checkpoint collection, all 12
installed/module/Legacy Session subcommands, explicit Position/Historical
execution, the phase-aware Assistant, six examples, and eight append-only
generated scenarios. Issue #158 completed Release preparation, and the
maintainer subsequently published `v0.14.0` manually at commit `d5589f8`. See
[Interactive session contracts](interactive_session_contracts.md) and
[Retrospective Session export](retrospective_session_export.md), and
[Session Position export and Decision checkpoints](live_session_position_export.md),
[Session Undo, correction, and Checkpoint lineage](session_undo_and_correction.md),
and [Session persistence and resume](session_persistence_and_resume.md),
[Session Decision observations](session_decision_observations.md), and
[Session CLI and end-to-end capture](session_cli_and_end_to_end_capture.md).

Issue #156 completes the stable `skat_ai.api.v1.session` version-1 namespace,
exact immutable contract exposure, strict Command parsing, typed Result
serialization, all ten transport-free in-memory operations, optional complete
redacted Session Provenance, strict standalone Session Schema, 63-Schema Package
parity, and clean-install validation. Issue #157 appends two public Session
operations and the `files` module without changing the first 52 exports. That
published Package version is `0.14.0`; its baseline has 85 generated outputs, six
Session examples, 63 Schemas, and 5,892 passing pytest tests. The historical
published `v0.13.0` baseline remains 62 Schemas and 77 scenarios.

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
  current `0.17.0` Package version
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
* Additive 12-subcommand `session` family with installed/module/Legacy parity,
  one shared parser, no second Console Script, and unchanged Root parsing
* Explicit caller-selected private persistence paths, optimistic CAS Save,
  privacy-safe status output, automatic Checkpoints, and Assistant capture

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
* Strict Information-set Search Multi-Step and Policy Comparison version `1` with fresh public-state Search, per-decision child seeds, no Search World or Policy reuse, no fallback, safe nested Results, exact 16-field diagnostics, append-once-last ordering, stopped-row ineligibility, and retained-Result complete Provenance
* Flat post-game bounded Search with an independently executed Immediate baseline plus actual-card and Search-versus-Immediate aggregate comparisons
* Historical Search Review over every decision-time snapshot with stable private per-decision seeds and reconciled status, coverage, agreement, quality, and performance summaries
* Bounded-Search dataset evaluation over canonical validation/test defaults, optional stable global decision-prefix caps, and preserved zero-decision records
* Immutable `interactive_v1`, `historical_review_v1`, and `evaluation_v1` work-budget profiles
* Independent exhaustive Suit, Grand, and Null strict-improvement fixtures plus 32/64/128-draw convergence evidence
* Deterministic Suit/Grand/Null benchmark corpus and measured performance documentation with no calibrated latency guarantee
* Separate deterministic eight-case Information-set Search benchmark corpus,
  strict local runner, frozen functional and structural signatures,
  Strategy-Fusion and duplicate-weight diagnostics, focused tests, and measured
  local reference documentation without elapsed-time gates

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
* Immutable [version-3 Settlement Normative Matrix](settlement_normative_matrix.md)
  with all 61 case IDs preserved, direct-rule, approved-bounded, one supported
  Historical Claim, legacy, and durable `not_supported_v1` classifications
* Private version-1 structured party-wide Claim, complete Evidence, exact-state,
  Proof Request/preparation, assignment, diagnostic Move, and Result contracts,
  plus bounded exhaustive exact AND/OR proof execution, private valid-proof
  adjudication, and existing Final Settlement composition with Historical-only
  runtime integration

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
* Version-3 Settlement Normative Matrix with 61 preserved case IDs, exact v1
  Claim status groups, and table-driven Runtime-kind coverage
* Focused party-wide Claim executor metadata, unavailable passthrough, Request
  reconciliation, AND/OR quantifiers, exact transitions, memoization, counters,
  representative lines, assignments, determinism, and compatibility tests
* Focused party-wide Claim adjudication versions, vocabularies, no-outcome
  behavior, exact point/Trick assignment, winner and level semantics, Settlement
  projection/reuse, call counts, privacy, and compatibility tests
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
* Focused Session file API, Decision Observation, Checkpoint review isolation,
  automatic collection, all-subcommand CLI parity, Assistant, Schema, example,
  generated-scenario, and clean-install tests for Issue #157
* Focused Match Workspace creation, rotation, Slot relationship, immutable
  change, chronology, Progress, fingerprint, strict nested reconstruction,
  private Load, optimistic Save, atomic-failure, privacy, and compatibility tests
  for Issue #163
* Focused Match Capture Application contract, Position View, exact/bounded Card
  selection, Game/setup update, automatic append, atomic rejection, truncation,
  annotation cleanup/editing, Passed Deal/clear, revision, no-I/O, architecture,
  and compatibility tests for Issue #164
* Focused Match Capture Web/Protocol/CLI, timecode, context, state, rendering,
  security, HTTP, no-JavaScript, autosave/conflict, packaging, clean-install, and
  compatibility tests for Issue #165
* Focused Match Player Statistics Context/Preparation/Update, strict temporal
  eligibility, Profile reuse, deterministic ID, set/clear, browser form/state,
  historical provenance, autosave/conflict, metadata-time, execution-boundary,
  packaging, and compatibility tests for Issue #166

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
* Additive `session` dispatch with `new`, `show`, `apply`, `undo`, `correct`,
  `checkpoint`, both exports, `analyze`, `review`, `finalize`, and `assistant`
* Strict load-operate-compare-and-swap-save persistence, privacy-safe human
  output, explicit analysis only, and automatic Checkpoint collection without
  automatic analysis
* Leading `capture` dispatch and private loopback browser for one explicit Match
  Workspace, with no-JSON creation, rapid Card entry, correction, annotations,
  optimistic autosave, and explicit conflict Reload

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
* The engine verifies only bounded ISkO 4.4.5 defender rest-Trick Claims and the
  separately approved complete-world party-wide Claim. The latter has private
  contracts, exact-state preparation, bounded proof execution, valid-proof
  adjudication, and Historical-only Final Settlement runtime integration with
  privacy-bounded public output.
* Structured declarer concession models accepted defender consent; structured defender concession applies joint liability without partner consent. Disputes are not modeled.
* Multi-Step intentionally does not auto-complete every opponent-only continuation; valid phases where the local player has already acted stop with `unsupported_turn_phase`.
* Impossible Null settlement requires an external Suit or Grand replacement selection; it remains incomplete when that selection or its required matadors are unavailable.
* Matador inference uses currently known declarer-card context and safe concrete-declarer completed-trick ownership facts; it does not reconstruct all possible matador information from complete historical trick ownership in every scenario.
* Historical records support normal completion and all six terminal shortenings with at most one optional timed defender-open-play or declarer-card-exposure continuation. Multiple non-terminal events, arbitrary event streams, other claims, and other end reasons are not represented there.
* Specific future-Trick Claims, generalized correction and non-jack exclusion,
  unlimited proof, simultaneous throws, arbitrary event streams, and the other
  documented durable v1 Claim exclusions are `not_supported_v1`; general
  Settlement coverage remains incomplete.
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
* Information-set Search is integrated across flat, Multi-Step, Policy
  Comparison, Historical Review/evaluation, one-Decision Match/Teacher/Dataset/
  Corpus, and Match Historical/Replay Coaching boundaries. Issue #193 adds
  repository-local benchmark evidence. It still does not provide a global
  Policy, equilibrium, global optimality, calibrated probability, complete
  Strategy-Fusion correction, product/runtime performance gate, or latency
  guarantee.
* Complete Known-opponent and unseen-player plans can be generated, validated,
  and losslessly materialized through the public mode-derived workflow. It has no
  new algorithms, algorithm selector or override, default weights, CLI overrides,
  fallback, or partial Plan. Global optimization, ratio guarantees, Sample- or
  Player-count balancing, component splitting, model training, and automatic
  evaluation are not implemented.
* Replay Coaching now has public version-1 evidence, impact, prioritization, one-
  game cross-decision patterns, deterministic actionable recommendations, strict
  schema/CLI/report output, and isolated retrospective context. Separate
  Historical Tactical Motif Review adds deterministic structural evidence.
  Tactical quality assessment, cross-game player analysis, broader Search, and
  causal attribution remain unimplemented.

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

### v0.17.0: Rules, Search, Coaching, and performance closure

The current published stable and latest stable GitHub Release completes
functional Issues #182 through #196, the documentation-only scope and Release-
readiness audit in Issue #197, and Release preparation in Issue #198. Issue #199
subsequently synchronizes post-publication documentation without changing that
published baseline. Package version `0.17.0` requires Python 3.13
or newer, retains Public API contract version `1`, exactly seven Root workflows,
and one Console Script, contains 71 authoritative and packaged Schemas, includes
six unchanged Session examples, validates 98 deterministic generated outputs,
and passes 7,479 pytest tests in 921.96s.

The Release theme is "Rules, Search, Coaching, and performance closure", and the
GitHub Release title is "v0.17.0 — Rules, Search, Coaching, and performance
closure". The maintainer published it manually on 2026-08-25 at commit
`8187fbe684559f9c0c2ba444be1bf33950359ad2` (`8187fbe`). GitHub Releases remains
authoritative, and no Package-index or PyPI publication is claimed.

### v0.16.0: Learning-ready behavior and communication data

The historical published `v0.16.0` Release completes
functional Issues #171 through #179. Issue #180 completed Release preparation.
Its Release theme is "Learning-ready behavior and communication data", and its
GitHub Release title is
"v0.16.0 — Learning-ready behavior and communication data". The maintainer
published it manually on 2026-08-18 at commit `91b1360`. Package version `0.16.0`
requires Python 3.13 or newer, retains Public API contract version `1`, exactly
seven Root workflows, and one Console Script, contains 63 authoritative and
packaged Schemas, includes six unchanged Session examples, validates 85 unchanged
generated-output scenarios, and passes 6,925 pytest tests in 1083.48s. Issue #181
synchronizes the post-publication repository documentation.

The Package baseline provides private content-addressed Learning Corpus identity
and persistence, a derived Current-Snapshot Player Catalog and time-safe
Statistics history, Human and Strategy Teacher Evidence, Learning Dataset version
`2`, group-safe partition preparation and leakage audits, descriptive cross-game
summaries, and the separate private local Corpus CLI/browser workflow. Issue #180
changed no product behavior, and Issue #181 changes no product functionality.
GitHub Releases is the authoritative publication record; no Package-index or
PyPI publication is claimed.

### v0.15.0: Local EuroSkat 36er Match capture, analysis, and exports

The published `v0.15.0` Release completes functional Issues #160 through #168.
Issue #169 completed Release preparation, and Issue #170 synchronized
publication status. Its Release theme is
"Local EuroSkat 36er Match capture, analysis, and exports". The GitHub Release
title is
"v0.15.0 — Local EuroSkat 36er Match capture, analysis, and exports", and the
Release points to commit `ec1c154`. Package version `0.15.0` requires Python 3.13
or newer, retains Public API contract version `1`, exactly seven Root workflows,
and one Console Script, contains 63 authoritative and packaged Schemas, includes
six unchanged Session examples, validates 85 unchanged deterministic generated-
output scenarios, and passes 6,510 pytest tests.

The milestone provides Match metadata and observed evidence, persistent
36-position Workspaces, transport-free rapid capture, the private local browser
and Capture CLI, Match-bound Statistics and time-safe Profile preparation,
information-safe Decision preparation, strict Historical and downstream
materialization, explicit Position and Historical analysis, ephemeral reports,
and private authenticated exports. Publication was performed manually by the
maintainer. GitHub Releases remains authoritative, and no Package-index or PyPI
publication is claimed.

### v0.14.0: End-to-end Live and Retrospective Session capture

The published `v0.14.0` Release completes functional Issues #150 through #157.
Issue #158 completed Package version `0.14.0`, Changelog, and current-state
documentation preparation without changing product behavior. The Release points
to commit `d5589f8`, requires Python 3.13 or newer, retains Public API contract
version `1` and seven Root workflows, contains 63 authoritative and packaged
Schemas, includes six strict Session examples, validates 85 deterministic
generated-output scenarios, including eight append-only Session scenarios, and
passes 5,892 pytest tests.

The milestone provides immutable fixed-three-player Live and Retrospective
Session contracts, deterministic accepted-Log transitions and replay, canonical
Position/Historical Request export, frozen Decision Checkpoints, Undo and
correction with lineage, strict fingerprinted persistence and optimistic atomic
Save, stable Public Session and File APIs, complete optional Session Provenance,
Decision Observation and isolated review, automatic Checkpoints, all 12 Session
CLI subcommands, explicit existing-Application execution, and the phase-aware
Assistant.

Publication was performed manually by the maintainer, and Issue #159 synchronized
its publication status. GitHub Releases remains authoritative, and no Package-
index or PyPI publication is claimed.

### v0.13.0: Stable API, installable tooling, and public field provenance

The published `v0.13.0` milestone is complete through functional Issues #137
through #147. Issue #148 completed Release preparation. The Release points to
commit `abd1ad3`, contains 62 authoritative Schemas and 62 Packaged Schema
Resources, validates 77 deterministic generated-output scenarios, passes 5,399
pytest tests, and requires Python 3.13 or newer. Publication was performed
manually by the maintainer, and GitHub Releases remains authoritative. No
Package-index or PyPI publication is claimed. Issue #149 synchronized the
publication status.

The milestone provides stable API contract version `1`, reusable Application
orchestration version `1`, the executable public facade, Setuptools Wheel and
sdist artifacts, Package Resource schemas, typing and version metadata,
installed/module/Legacy CLI parity, complete internal Root Result provenance for
all seven workflows, and bounded opt-in public Root Result and actual-artifact
provenance. Default Root output remains unchanged when provenance is omitted.

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

## Published Package milestone: v0.16.0

`v0.16.0 — Learning-ready behavior and communication data` is a historical
published Package milestone. Issues #171 through #179 establish and connect its private internal
foundations:

* immutable content-addressed copies of exact strictly resumed Match Workspace
  persistence documents;
* exact source Workspace/content fingerprint retention and deterministic Match
  Snapshot identity;
* exactly three canonical stable-ID Player Observations;
* observed-Game content fingerprints and Snapshot-scoped Game, Decision,
  Commentary, and Response References with closed reconciliation;
* lightweight Catalog entries with canonical order and one explicit current
  Snapshot selection for every represented logical Match;
* non-mutating `new_match`, duplicate, same-revision conflict, newer-revision,
  and older-revision classification;
* one explicit fixed-root private Store with authoritative `catalog.json` and
  immutable content-addressed Match Snapshot objects;
* deterministic Catalog and persistence-content fingerprints, strict Catalog
  and Snapshot reconstruction, and canonical UTF-8/LF files;
* strict Store Resume requiring every referenced object and reporting valid
  sorted orphan IDs without automatic repair or deletion;
* pure revision-conflict-first Catalog import and explicit Current selection;
* no-clobber object publication, optimistic atomic Catalog Save, and deliberate
  object-before-Catalog conflict orphan behavior;
* strict source-preserving Workspace-file import and persisted explicit Current-
  selection updates;
* a deterministic non-persisted Player Catalog over explicit Current Match
  Snapshots only, excluding retained non-current revisions and orphans;
* exact stable-ID Player aggregation, observed labels, participant and online-
  source aliases, and immutable exact alias conflict reporting without merge;
* complete Match-bound exact Statistics history with shared source-Match temporal
  status and strict latest-unambiguous or explicit-observation as-of selection;
* deterministic minimized Human Commentary and explicitly linked Response
  Evidence over explicit Current Match Snapshots only;
* exact original text, commentator identity, subject/response observed Cards,
  source metadata, and nullable timecodes without normalization or interpretation;
* content-separated Commentary/Response fingerprints, Snapshot-scoped Evidence
  IDs, complete child relationships, reconciled collection identity, and
  canonical in-memory export bytes;
* Human Evidence exclusion of retained non-current revisions, orphan objects, private deals,
  unrelated Cards, Statistics, Profiles, analysis, Coaching, Dataset version `1`,
  and derived tags;
* a private local unredacted source boundary with no workflow, API, CLI, browser,
  Schema, example, or generated-output addition;
* exact executed Decision Analysis Report sources explicitly bound to Current
  Match Snapshots, observed Game/Decision References, and actual Cards;
* one exact Position Request rebuild and retained Root Result validation per
  source without analysis, Search, Profile, Dataset, persistence, or I/O work;
* minimized method-bound Immediate/Search/Auto Candidate, budget, status,
  fallback, review, Profile, and policy evidence without a ground-truth claim;
* exact Report/Request/Result/source identities, wall-clock-normalized semantic
  Teacher identities, retained multiple Reports per Decision, deterministic
  coverage counts, and canonical in-memory export bytes;
* one private Current-Snapshot-only unpartitioned Learning Dataset version `2`
  over the exact Store, supplied Player Catalog, Human Evidence, and Strategy
  Teacher collection;
* information-safe Decision State reuse, separate observed behavior, cached
  latest-unambiguous Player Context, exact Teacher/Commentary/Response joins,
  explicit safe/skipped and joined/unjoined coverage, normalized evidence pools,
  stable Record IDs, enriched content fingerprints, and canonical path-free
  export bytes without a default target;
* Match-Snapshot-safe partition Plans with strict temporal Known-player blocks,
  transitive Player-connected unseen-player components, exact Record-primary and
  Match-secondary balancing, complete leakage audits, lossless indexes, and
  canonical path-free export;
* exact Dataset, Player Catalog, and supplied Known-player/unseen-player Result
  reconciliation without Dataset, Catalog, or Plan regeneration;
* descriptive exact-Count Match, Player, Communication, Strategy Teacher,
  evidence Coverage, Dataset Readiness, and Partition Readiness summaries;
* deterministic sub-summary and final identities plus canonical path-free export
  without rating, ranking, evaluation, or model-readiness claims;
* separate installed/module/Legacy `corpus` dispatch through the one Console
  Script, with required explicit root and default loopback port `8766`;
* absent/empty-root caller-ID initialization, strict Store Resume and Reload,
  strict 16-MiB Workspace and executed-Decision Report-source uploads, optimistic
  import, and explicit Current selection;
* exact Match Capture `Download for Learning Corpus` source transfer, a bounded
  max-2,048 process-local source store, and explicit current/non-current removal
  handling without automatic Report capture;
* exact unlocked Player/Human/Strategy/Dataset-v2/known/unseen/Summary preparation
  with source-generation verification, deterministic invalidation, and no
  analysis execution;
* minimized server-rendered no-JavaScript-capable dashboard, packaged local
  assets, token/cookie/Host/origin/CSP loopback security, no external network,
  and seven authenticated canonical downloads;
* separate Current-Match-Snapshot-only Tactical Motif Evidence with every
  observed Decision represented by exact Evidence or an explicit skip, exact
  shared single-game detector reuse, and safe partial-Match/final-Trick behavior;
* exact descriptive Tactical Motif global, Player, role, seat, phase, contract,
  distinct-Game, distinct-Match, and bounded recurrence Counts without rates,
  traits, quality, significance, communication, causal, or Coaching claims;
* atomic existing-plus-Tactical process-local publication, minimized Tactical
  presentation, and two additional authenticated canonical downloads for nine
  current downloads;
* no derived artifact persistence, Public API, Schema, example, generated output,
  database, remote/cloud/collaboration behavior, task builder, evaluation,
  rating, or training addition.

Match Workspaces remain editable authoritative capture sources. A correction
creates a distinct immutable Match Snapshot; Corpus behavior never mutates the
Workspace. Analysis and annotation artifacts remain separate derived objects,
and Learning Dataset version `2` plus its derived Cross-game Summary remain
separate non-persisted exports.

Issue #179 completes the functional private local Learning Corpus/Dataset-v2
workflow. Issue #180 updates only Package version, matching expectations,
Changelog, and Release-state documentation to complete Release preparation. The
maintainer published the Release manually on 2026-08-18 at commit `91b1360`, and
Issue #181 synchronizes publication status without product functionality. The
Package preserves 63 authoritative and packaged Schemas, six Session examples,
85 generated outputs, and 6,925 pytest tests.

The published `v0.17.0` Package baseline uses Package version `0.17.0`, Public
API contract version `1`, seven Root workflows, one Console Script, and six
Session examples. Issue #186 updates the Matrix to version `3` with the same 61
cases. Issue #189 adds four Information-set Search Schemas, one example, and four
generated outputs. Issue #190 adds strict Multi-Step and Policy Comparison
integration, one example, and two generated outputs without adding a Schema,
bringing the working totals to 69 authoritative and packaged Schemas and 94
generated outputs. The published `v0.16.0` facts above remain unchanged.

Issue #191 adds strict private one-Decision Match Information-set Search, exact
Report-source transfer, focused Strategy Teacher Evidence, Dataset-v2 joins,
cross-game counts, and existing Corpus browser workflow support. It adds no
Schema, example, generated output, Public API, persistence, or new command.

Issue #192 subsequently adds separate Information-set Replay Coaching, private
Match Historical Information-set Review/Coaching, one strict Schema, one Root
example, and two append-only generated outputs. Its point-in-time baseline is
therefore 70 authoritative and packaged Schemas, six Session examples, and 96
generated outputs. Package version, Public API contract, seven Root workflows,
one Console Script, and Settlement Matrix version `3` with 61 cases remain
unchanged.

Issue #193 adds a deterministic synthetic Information-set Search benchmark
corpus, a strict repository-local runner and focused tests, and documented local
reference measurements. It changes no production code, Schema, route, profile,
Public API, Package version, example, generated output, or working count.

Issue #194 adds deterministic Historical Tactical Motif Review with one retained
Decision Snapshot sequence, exact structural lead/void/Trick-control/Defender-
partnership/hand-shape/outcome evidence, complete Provenance, one strict Schema,
one Root example, two append-only generated outputs, and private Match browser
controls. The final published baseline is therefore 71 authoritative and
packaged Schemas, six Session examples, and 98 generated outputs. Package/API/
workflow/Console-Script/Settlement baselines remain unchanged.

Issue #195 reuses the exact Tactical detector over explicit Current Match
Snapshots, adds Evidence-or-skip coverage and exact descriptive cross-game
summaries, and integrates two process-local artifacts into atomic browser
preparation. Human, Strategy Teacher, and Tactical Evidence remain separate;
Learning Dataset version `2` and the current 71-Schema/98-output counts remain
unchanged.

Issue #196 adds separate deterministic Tactical Cross-game Coaching from exact
retained Tactical/Teacher evidence, complete-Search-only consensus, repeated
cross-Game focus, fixed Guidance, atomic third-family publication, and a tenth
authenticated download. Dataset version `2` and the current 71-Schema/98-output
counts remain unchanged.

Deletion and garbage collection, recovery UI, Player Catalog persistence,
persisted aliases/assertions, merge/split operations, all-revision Player views,
Human Evidence persistence and public API/Schema transport, Strategy Teacher
Evidence persistence and public transport, automatic Report capture, Historical
Report import, task-specific
behavior/strategy/communication Feature and Target builders, Dataset-v2
persistence, Summary persistence and public API/Schema transport,
communication-aware annotations,
evaluation baselines, ratings, derived AI tags, and public
exposure remain open. No production model is planned for this milestone. See
[Learning Corpus identity and Catalogs](learning_corpus_identity_and_catalogs.md),
[Learning Corpus persistence and Workspace import](learning_corpus_persistence_and_import.md),
[Learning Corpus Player Catalog and Statistics history](learning_corpus_player_catalog_and_statistics_history.md),
[Learning Corpus human Commentary and Response evidence](learning_corpus_human_commentary_and_response_evidence.md),
[Learning Corpus Strategy Teacher Evidence](learning_corpus_strategy_teacher_evidence.md),
[Learning Dataset version 2](learning_dataset_v2.md),
[Learning Dataset version 2 partition preparation](learning_dataset_v2_partition_preparation.md),
[Learning Dataset version 2 cross-game summaries](learning_dataset_v2_cross_game_summaries.md),
[Learning Corpus Tactical Motif evidence and summaries](learning_corpus_tactical_motif_evidence_and_summaries.md), and
[Learning Corpus browser workflows](learning_corpus_browser_workflows.md).

## Published Package milestone: v0.17.0

`v0.17.0 — Rules, Search, Coaching, and performance closure` is functionally
complete through Issue #196. Issue #182 closes the v1 Claim product-decision gate through
an approved bounded direction. Issue #183 adds private structured Claim and exact-proof
contracts plus one untraversed exact-state preparation without Runtime behavior.
Issue #184 adds the private bounded exhaustive exact AND/OR executor without
Runtime behavior. Issue #185 adds private valid-proof adjudication and existing
Final Settlement composition, with no outcome for invalid or unavailable proof.
Issue #186 updates Matrix version `3` without changing its 61 cases and completes
the one bounded Retrospective party-wide all-remaining-Tricks Claim through
Historical Game input only. Every other current Claim boundary remains
`not_supported_v1`; Session, Match Capture, and Corpus Claim entry remain open.
Stronger information-set Search and Strategy Fusion mitigation begins with
Issue #187's private version-1 World State, actor Observation, deterministic
fixed-Player Policy, Budget, Request, Preparation, controlled-Policy, and Result
contracts. It reuses ordered Compatible-world selection, preserves sampled
duplicates, and performs no public integration. Issue #188 adds the private
bounded exhaustive selected-world best-response executor with strict retained-
Preparation validation, fixed-player rollout, controlled Information-set
grouping, existing terminal utility and Candidate ranking, complete contingent
Policy retention, bounded partial/timeout semantics, and invocation-local World
and bundle memoization. Issue #189 adds strict flat `information_set_search`,
safe aggregate Results, same-selection PIMC plus independently seeded Immediate
retrospective comparison, separate Historical Review and Training Dataset
evaluation, retained-stage Provenance, CLI, four Schemas, one example, and four
generated scenarios. Issue #190 adds strict Multi-Step and Policy Comparison
integration with per-decision child seeds and fresh public-state Search, private
independent coherent execution, no Search World or Policy reuse, no fallback,
safe nested Results and 16-field diagnostics, existing ranking, and complete
Provenance. Existing `auto` remains unchanged. Match Capture, Match Analysis
Reports, and Strategy Teacher are integrated for this bounded one-Decision path
by Issue #191 together with Dataset-v2 and Corpus propagation. Match Historical
Information-set execution and Replay Coaching classification are completed
separately by Issue #192 through one retained Review, complete-Candidate primary
evidence, diagnostic PIMC/Immediate without fallback, time-safe fixed Profile
Policies, and complete Provenance. Issue #193 adds repository-local benchmark
evidence without changing production behavior or counts. Issue #194 adds
deterministic Historical Tactical Motif Review. Issue #195 adds separate
Current-Snapshot-only Tactical Motif Evidence and exact descriptive cross-game
Counts without changing Dataset version `2`. Issue #196 adds separate
deterministic Tactical Cross-game Coaching from exact retained Tactical/Teacher
evidence, complete-Search-only consensus, bounded repeated cross-Game focus and
fixed Guidance, and one tenth Corpus download without changing Dataset version
`2`. Issue #193 satisfies the bounded v0.17.0 performance-evidence contract;
production acceptance criteria and cross-machine latency guarantees remain later
v1 decisions rather than Release blockers. Broader tactical quality outside
retained complete-Search evidence, carefully bounded Player Ratings where
approved, broader Provenance and Confidence integration, and the remaining pre-
v1 scope audit also remain open. See [Information-set Search workflows](information_set_search_workflows.md),
[Information-set Search Multi-Step and Policy Comparison](information_set_search_multi_step_and_policy_comparison.md),
and [Information-set Search performance](information_set_search_performance.md).
Issues #182 through #196 are the frozen functional history. Issue #197 completes
the documentation-only scope and Release-readiness audit, and Issue #198 prepares
Package `0.17.0`, the Changelog, current expectations, and Release-candidate
documentation without product behavior changes. The maintainer published
`v0.17.0` on 2026-08-25 at `8187fbe`, and Issue #199 synchronizes that
publication without product functionality. `v1.0.0` remains unready. See the
[v0.17.0 scope and Release-readiness audit](v0_17_release_readiness_audit.md).

## Later planning milestone: v1.0.0

The [requirements traceability matrix](requirements_traceability.md) is the
authoritative audit of current ISkO, SkWO, and skat-ai product support. The
[v1.0 scope](v1_scope.md) defines required product directions, unresolved
implementation details, and testable completion gates.

`v1.0.0` remains planning-only and not ready after the published `v0.17.0`
Package baseline through
internal Match metadata, observed-Game and
commentary, persistent Workspace, rapid-entry Application, private local browser
and autosave transport, Match-bound Statistics editing and time-safe Profile
preparation, Decision/Historical/Training-source/fixed-list materialization,
explicit analysis, ephemeral reports, and authenticated local downloads.
A separate audit of both documents must precede its final Issue sequence or
implementation architecture.

Before `v1.0.0`, the project still requires broader tactical quality and Coaching
beyond Issue #196's retained complete-Search slice, remaining approved settlement
nuance, and broader field-level provenance
enforcement. End-to-end local Live and Retrospective Session capture is complete
through Issues #150 through #157, including public files, automatic Checkpoints,
accepted-Log observation, isolated review, explicit analysis, all 12 CLI
subcommands, and the Assistant. The executable
public facade, internal Application layer, installable library distributions,
and stable installed CLI interface are implemented. API contract
version `1`, exact public namespaces, immutable document wrappers, compatibility
metadata, and stable public errors are implemented. The approved party-wide
Claim has private contracts, exact-state preparation, bounded proof execution,
valid-proof adjudication, and Historical-only Final Settlement runtime
integration with strict public diagnostic output. Flat Position, Session, Match
Capture, Corpus entry, and historical end reasons outside the supported bounded
set remain incomplete.
Structured concessions and
exposures, bounded defender open play, open-card throwing, supported historical
terminal and continuation events, variable-length workflows, Ouvert-aware
recommendation, coherent hidden worlds, and bounded structural inference are
already implemented.
The approved [settlement matrix](settlement_normative_matrix.md) defines their
normative scope, and the bounded continuation-plus-terminal-shortening sequence
is implemented through delegation to the existing terminal cases. Claims,
Concessions, and Final Settlement remain partially supported. See
[Claim and Settlement v1 boundaries](claim_and_settlement_v1_boundaries.md).

Full auction modeling, learned opponent profiles, machine-learning card-decision
models, and online-platform, hosted-browser, or browser-extension adapters are
planned after `v1.0.0`. Formal
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
evidence. They do not provide calibrated sample quality or a latency guarantee.
Issues #187 and #188 add a private three-Trick information-set Policy Search
foundation and bounded executor. Issue #189 adds strict flat routing, descriptive
retrospective comparison, separate Historical Review and Training Dataset
evaluation, safe output, Provenance, CLI, Schemas, example, and scenarios.
Multi-Step and Policy Comparison integration is completed by Issue #190. Issue
#191 adds the bounded one-Decision Match/Report/Teacher/Dataset/Corpus path. Issue
#192 adds separate Information-set Replay Coaching and Match Historical
Information-set Review/Coaching. Issue #193 supplies bounded repository-local
benchmark evidence. Issue #194 adds separate deterministic Historical Tactical
Motif Review and Match browser integration without tactical quality, signaling,
communication, causal, or cross-game claims. Complete Strategy-Fusion correction, calibrated quality,
product/runtime performance acceptance gates, and latency guarantees remain
open, so the stronger-search completion gate is not closed.

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
should distinguish the current published stable `v0.17.0` Release from the
historical published `v0.16.0`, `v0.15.0`, and `v0.14.0` Releases,
Match Capture work through internal Issues #160, #161, #163, and #164 plus
private browser/Statistics Issues #165 and #166 and internal materialization
Issue #167 and functional completion Issue #168, historical
`v0.13.0`, `v0.12.0`, and older Release evidence, the authoritative publication
state shown by GitHub Releases, functional Issues #150 through #157 and completed
release-preparation Issue #158 and publication-synchronization Issue #159, the
historical 63-Schema, six-Session-example, 85-scenario, and 5,892-test `v0.14.0`
baseline, functional Issues #160 through #168, completed Release-preparation
Issue #169, publication-synchronization Issue #170, the historical published
63-Schema, six-Session-example, 85-scenario, and 6,510-test `v0.15.0` baseline,
the historical published `v0.16.0` Package and Issues #171-#179 identity, Catalog, persistence,
Workspace-import, Player Catalog, Statistics-history, Human Evidence, and
Strategy Teacher Evidence plus Learning Dataset-v2, partition, descriptive
cross-game Summary, and functional private local browser workflow,
requirements
explicitly required for `v1.0.0`, planned post-v1.0 work, not-required workflows,
and unconditional exclusions. Functional private local `v0.16.0` work is
complete through Issue #179, Issue #180 completed Release preparation, and Issue
#181 synchronizes the manual publication at commit `91b1360`. The published
`v0.17.0` functional history begins with Issue #182's completed Claim and Settlement
boundary audit, Issue #183's private contracts and exact-state preparation, and
Issue #184's bounded exhaustive proof execution. Issue #185 adds private
adjudication and existing Final Settlement composition. Issue #186 adds the
Historical-only approved Claim runtime slice. Issue #187 adds the private
information-set Search contracts and no-execution Preparation foundation. Issue
#188 adds the private bounded executor. Issue #189 adds strict flat routing,
descriptive retrospective comparison, separate Historical Review and Training
Dataset evaluation, safe output, Provenance, CLI, Schemas, example, and scenario
coverage. Issue #190 adds strict Multi-Step and Policy Comparison integration.
Issue #191 adds strict one-Decision Match/Report execution and focused
Teacher/Dataset/Corpus propagation without changing schemas or scenarios.
Issue #192 adds separate Information-set Replay Coaching, Match Historical
Information-set Review/Coaching, one Schema, one example, and two scenarios.
Issue #193 adds repository-local benchmark evidence without changing product
surfaces or counts. Issue #194 adds Historical Tactical Motif Review, one Schema,
one example, and two scenarios, bringing the working baseline to 71 Schemas and
98 scenarios. Issue #195 adds separate private Current-Snapshot Tactical Motif
Evidence, exact descriptive cross-game summaries, and the Issue #195 point-in-
time nine-download Corpus integration without changing those counts. Issue #196
adds separate
bounded deterministic Tactical Cross-game Coaching and a tenth download without
changing those counts or Dataset version `2`. Issues #182 through #196 are the
frozen v0.17.0 functional history, Issue #197 is the completed documentation-only
audit, and Issue #198 prepares the Package candidate without product behavior
changes. The maintainer published it on 2026-08-25 at `8187fbe`, and Issue #199
synchronizes that publication without product functionality. The active next
planning milestone is `v1.0.0`; its separate scope and traceability audit is the
next action. Production performance criteria, latency
guarantees, broader tactical
quality/Coaching, Player-rating boundaries, and the final `v1.0.0` Issue split
and architecture remain later work rather than v0.17.0 Release blockers.
