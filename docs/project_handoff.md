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
* complete normal-play and six supported exact-prefix shortened historical-game records
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
* strict Information-set Search across flat, Multi-Step, Policy Comparison,
  descriptive same-selection post-game, Historical Review, and Training Dataset
  evaluation workflows
* immutable version-3 Settlement Normative Matrix with 61 preserved cases, one
  supported bounded Historical party-wide Claim, and durable v1 Claim exclusions
* private immutable version-1 structured party-wide Claim, complete Evidence,
  exact-state, Proof Request/preparation, assignment, diagnostic-line, and Result
  contracts plus bounded exhaustive exact AND/OR proof execution, private
  valid-proof adjudication, and existing Final Settlement composition with
  Historical-only runtime integration and privacy-bounded public output
* immutable version-1 Replay Coaching decision-time evidence and retrospective impact contracts
* deterministic Replay Coaching Key Decisions, Turning Points, one-game patterns, and actionable recommendations
* complete public version-1 Replay Coaching Report with strict schema, CLI, human-readable presentation, and generated-output coverage
* separate version-1 Information-set Replay Coaching from one retained Historical
  Information-set Review, complete Candidate-only primary evidence, diagnostic
  PIMC/Immediate without fallback, shared deterministic Coaching composition,
  isolated Outcome Context, strict Schema, CLI, and complete Provenance
* separate version-1 Historical Tactical Motif Review from one retained Decision
  Snapshot sequence, deterministic structural taxonomy, after-play and after-
  Trick evidence, strict Schema, CLI, Match browser controls, and complete
  Provenance without quality, signaling, communication, or causal claims
* separate private Current-Snapshot-only Tactical Motif Evidence with exact
  Evidence-or-skip Decision coverage, shared detector reuse, safe partial-Match
  behavior, and exact descriptive cross-game scope and recurrence Counts
* separate private deterministic Tactical Cross-game Coaching with exact
  Tactical/Teacher joins, one Assessment per exact Teacher Report, semantic
  Decision consensus, complete-Search-only repeated cross-Game focus, fixed
  Guidance, and bounded Player Reports without truth, trait, or causal claims
* stable public API contract version `1` with exact namespaces and exports,
  immutable JSON Request and Result wrappers, compatibility/version metadata,
  stable errors and Exit Codes, and unchanged legacy Root CLI behavior
* internal field-level provenance contract version `1` with RFC 6901 paths,
  immutable sidecar ledgers, exact/subtree coverage audits, dependency and
  temporal validation, Information Use Context, public redaction, and safe
  deterministic serialization
* internal Application and live-analysis provenance version `1` with complete
  pre-selection decision ledgers across Immediate, Search, inference,
  Multi-Step, and Policy Comparison
* internal retrospective and Replay Coaching provenance version `1` with
  separated pre-actual and post-actual flat Position and Historical decision
  stages and complete requested review/report ledgers
* internal Dataset, Preparation, Opponent, Profile, historical-list, and
  independent-list comparison provenance version `1` with complete non-legacy
  Root Result ledgers
* internal complete Result provenance version `1` for Position and Historical
  execution, including Declaration, scoring, Settlement, endings,
  continuations, canonical Historical records, replay, and points
* mandatory internal version-1 exact Request/effective-option/external-source,
  pre-analysis context, retained-stage authorization, and final Result/artifact
  serialization enforcement for all seven Root workflows
* bounded public field-provenance contract version `1` with immutable public
  attachments, artifact mappings, bundles, seven explicit Root Result mappings,
  complete post-redaction coverage, and opt-in API/CLI Root output
* internal Application orchestration version `1` with immutable invocations,
  workflow options, injected external documents, results, and auxiliary
  artifacts; generic no-I/O dispatch for all seven Root workflows; six isolated
  Training Dataset operations; and legacy CLI transport parity
* executable public Python API version `1` with immutable direct workflow
  options, all-seven-workflow Application execution, separate artifacts, lazy
  Package Resource schema validation, stable boundary errors, and no caller
  transport I/O
* installation-ready Setuptools packaging with private byte-identical Schema
  resources, `py.typed`, Package `__version__`, one Wheel and one sdist,
  artifact inspection, and separate clean-install public-API smoke tests
* installed CLI contract version `1` with the exact `skat-ai` Console Script,
  `python -m skat_ai`, a Package-owned canonical parser and transport, Legacy
  Root compatibility, and clean-install CLI/API parity
* internal Session and Command contract version `1` with fixed stable Players,
  Live and Retrospective Capture Modes, phases, typed Commands, an authoritative
  accepted revision Log, Diagnostics, export readiness, Transition Result
  semantics, and deterministic serialization
* internal Session transition and projection version `1` with canonical
  revision-zero creation, full accepted-Log replay, atomic application and
  rejection, monotonic phases, incremental rule/information validation, trick,
  continuation, and end derivation, promotion, and forged-State detection
* internal Session Request Export version `1` with immutable available or
  unavailable Results, exact Retrospective Historical readiness gating,
  canonical Historical mapping and round trip, and immutable existing Root
  Request construction without workflow execution
* internal information-safe Session Position export with immutable explicit
  analysis options, stable-to-relative mapping, declared-Ouvert and continuation
  public hands, existing Position validation, and no workflow execution
* immutable internal pre-Play Decision Checkpoints with replay-verified source
  revision, actor/seat/index metadata, relative Player map, and frozen existing
  Position Request
* internal Session History Edit version `1` with immutable strict-prefix Undo,
  exact removed suffixes, one-command replacement, deterministic first-rejection
  suffix replay, valid partial corrected States, and Checkpoint lineage
* private deterministic Session Persistence version `1` with authoritative
  accepted-Log State, caller-supplied frozen Checkpoints, State/content
  fingerprints, strict replay-verified resume, optimistic conflict detection,
  canonical files, and atomic same-directory replacement
* stable Public Session API and Public Session File API version `1` with exact
  immutable exports, strict Save/Load, path-free Results, and optional complete
  Session Provenance for in-memory operations
* accepted-Log Decision Observation, frozen-request-plus-observed-Card review
  export, automatic exact Checkpoint collection, and review isolation
* installed/module/Legacy 12-subcommand Session CLI parity, explicit existing
  Position/Historical Application execution, phase-aware Assistant, six examples,
  and eight append-only scenarios
* internal immutable version-1 Match Capture identity and metadata, descriptive
  video/manual source evidence, reusable millisecond time bounds, one canonical
  EuroSkat 36er Standard format, exact fixed-place participants, optional
  existing Opponent Statistics snapshots, and one perspective Match Player
* internal immutable version-1 evidence-aware observed Games, exact historical
  seats, bounded partial and complete Play validation, free-text commentary on
  any Player Decision, linked later responses, and deterministic evidence
  capability summaries without hidden completion
* internal immutable version-1 EuroSkat 36er Standard Match Workspaces with
  exactly 36 Slots, existing rotation, partial observed Games, passed deals,
  revisioned changes, Progress, fingerprints, strict Resume, and optimistic
  atomic private persistence
* internal transport-free version-1 Match Capture Application services with
  immutable Card entries, Position Views and Results, exact/bounded Card
  selection, deterministic Game/annotation IDs, focused setup updates, automatic
  Play derivation, truncation cleanup, annotation editing, and Passed Deal/clear
  wrappers
* internal local Match Capture Web, Web Protocol, and Capture CLI version `1`
  with one explicit Workspace file, loopback token/same-origin protection,
  no-JSON creation and rapid entry, packaged assets, compare-and-swap autosave,
  and explicit conflict Reload
* editable Match-bound Player Statistics Snapshots with deterministic IDs,
  strict-before-Match eligibility, existing Profile derivation, canonical
  eligible preparation, and private browser forms
* internal evidence-aware Match Decision preparation with acting-own-hand
  reconstruction, actual-Card cutoff, no future-opponent leakage, Skat/Ouvert
  visibility, and time-safe relative Profile bindings without application
* internal strict normal-completion Historical Game materialization,
  unpartitioned Training source Records, and complete existing fixed-three-
  player list plus aggregation materialization with Passed Deals and Commentary
  retained as Workspace sidecars, without workflow execution
* internal explicit one-Decision Position and strict Historical Application
  execution, existing-behavior eligible Profile application, no-workflow Match
  materialization, deterministic max-eight ephemeral reports, and authenticated
  canonical local downloads
* internal immutable Learning Corpus identity and Catalog version-1 contracts
  with exact strictly resumed Workspace Snapshots, content-addressed revisions,
  Player Observations, Snapshot-scoped Game/Decision/Commentary/Response
  References, explicit current selections, and duplicate/revision classification
* internal deterministic Learning Corpus Persistence, Store, Catalog Change, and
  Workspace Import version-1 contracts with one explicit root, strict Resume,
  valid orphan reporting, immutable object publication, optimistic atomic
  Catalog Save, strict Workspace import, and persisted Current-selection changes
* internal derived Learning Corpus Player Catalog, Player Match Observation,
  Platform Alias, Player Statistics Observation, and Statistics Selection
  version-1 contracts with Current-Snapshot-only history and no persistence
* internal Learning Corpus Human Evidence, Human Evidence Game, Commentary
  Evidence, Response Evidence, and Human Evidence Export version-1 contracts
  with Current-Snapshot-only minimized exact human source evidence, deterministic
  identities, and canonical in-memory bytes
* internal Learning Corpus Strategy Teacher Source, Evidence, Collection, and
  Export version-1 contracts with exact executed Decision Report binding,
  Current-Snapshot/Reference closure, no-execution Request/Result reconciliation,
  method-bound Immediate/Search/Auto evidence, and canonical in-memory bytes
* internal Learning Dataset version `2` plus Source Context, Decision State,
  Observed Behavior, Player Context, Record, skipped Decision, and Export version-
  `1` contracts, with Current-only source reconciliation, separate evidence
  families, deterministic identities, and canonical path-free bytes
* internal Dataset-v2 partition preparation with Match-Snapshot-indivisible
  groups, temporal Known-player and Player-component unseen-player modes, leakage
  audits, lossless indexes, and canonical path-free bytes
* internal Dataset-v2 exact-Count cross-game Match, Player, Communication,
  Strategy, Coverage, Dataset Readiness, and supplied Partition Readiness
  summaries with deterministic identities and canonical path-free bytes
* internal private local Learning Corpus Web, Protocol, and CLI version `1` with
  one explicit root, strict Workspace and executed-Decision Report uploads,
  explicit Current selection, max-2,048 process-local sources, unlocked exact
  Player/Human/Strategy/Dataset/partition/Summary preparation, minimized
  no-JavaScript presentation, atomic existing/Tactical/Coaching publication, and ten
  authenticated canonical downloads
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
* packaged-schema filename and byte parity
* input JSON schema validation
* generated output JSON schema validation
* Wheel, sdist, and clean-install distribution validation
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

### Public API contract foundation

Implemented by Issue #137 for `v0.13.0`:

* stable `skat_ai.api.v1` and `skat_ai.errors` namespaces
* Package-Root exports limited to `api` and `errors`
* the exact seven-value string `WorkflowV1` contract
* recursively immutable, defensively copied Request and Result JSON documents
* immutable execution options, compatibility policy, and API-version metadata
* stable public error hierarchy, class-defined codes, and deterministic error serialization
* stable CLI Exit Code constants and exact `main.CliUsageError` compatibility alias
* additive compatibility and future deprecation policy through `v1.0.0`

Issue #140 extends this foundation with `parse_request`, `execute`,
`execute_document`, `serialize_result`, public execution artifacts and results,
direct immutable workflow options, lazy Root schema validation, and stable
boundary-error translation. Issue #141 adds installable Wheel and sdist
artifacts, private Package Resource schemas, typing and Package version metadata,
and clean-install validation. Issue #142 adds the installed and module CLI entry
points without changing Public API exports. Field-level provenance now propagates
internally through live and retrospective Position/Historical execution and all
Dataset, Preparation, Opponent, Profile, list, and comparison Root workflows,
and Issue #147 exposes the bounded redacted Root Result plus actual-artifact
subset. Issue #202 completes exact consumed-source, Information Use Context,
retained-linkage, and final-serialization enforcement around all seven Root
workflows without widening that public subset. See
[Public API contracts](public_api_contracts.md) and
[Public Python API v1](public_python_api_v1.md), and
[Public field provenance](public_field_provenance.md).

### Application orchestration foundation

Implemented by Issue #139 for `v0.13.0`:

* orchestration contract version `1` with caller-supplied input references
* frozen, slotted, keyword-only invocation, workflow-option, external-document,
  result, and auxiliary-artifact values with defensive JSON immutability
* one generic no-I/O dispatcher for all seven canonical Root workflows
* exactly five isolated Training Dataset operations: summary, partition audit,
  rolling Opponent Policy evaluation, bounded-Search evaluation, and historical
  Opponent Statistics aggregation
* optional already-loaded Opponent Statistics injection for Position Analysis
  and Historical Game execution with the existing binding and temporal rules
* one optional `opponent_statistics_input` auxiliary export artifact, separate
  from the primary result and without a transport path
* Package-owned CLI transport over the Application layer, with repository-root
  `main.py` retained as a compatibility facade preserving wrapper names, patches,
  and JSON behavior
* an internal boundary consumed by the Issue #140 public facade
* internal Issue #143 live Position, Issue #144 retrospective
  Position/Historical, Issue #145 Dataset/list/opponent, and Issue #146 complete
  Result provenance attachments
* Issue #147 public conversion selecting only one redacted Root Result plus
  artifacts actually returned, without exposing consumed-input, decision,
  intermediate-stage, or unredacted attachments

The public facade now exposes generic parse, execute, execute-document, and
serialization functions without exporting these Application types. Workflow-
specific execution helpers remain absent. Installed entry points are implemented
by Issue #142; broader Domain error migration and end-to-end field-level
enforcement remain open. See
[Application orchestration](application_orchestration.md).

### Interactive Session contract, Request export, Checkpoint, and persistence foundation

Implemented by Issue #150 for the `v0.14.0` Package milestone:

* independent internal Session and Command version `1`
* exactly three stable Players with canonical Historical seats
* Live and Retrospective Capture Modes with one-way explicit promotion
* setup, deal, declaration, Skat/discard, play, and ended phases
* nine initial immutable typed Commands with exact allowed-phase metadata
* an authoritative contiguous accepted Command Log and linear revisions
* structural Live hand-entry protection before promotion
* canonical validation Diagnostics and Position/Historical export readiness
* valid-incomplete Session status and applied, rejected, and revision-conflict
  Transition Result constructor semantics
* recursively immutable caller JSON and fresh deterministic serialization

Implemented by Issue #151:

* transition-engine and projection version `1` with replay policy
  `full_accepted_log_before_apply`
* canonical revision-zero State creation with computed Validation
* frozen accepted-fact projection with canonical Player and Card ordering
* deterministic full accepted-Log replay and stored-State equality checks
* revision-conflict precedence and exact unchanged-State atomic rejection
* monotonic phase advancement from Deal through explicit Game End
* incremental metadata, Deal, Declaration, Skat/Discard, Play, ownership,
  legal-card, trick, continuation, terminal-shape, and promotion validation
* Position and Historical readiness recomputation without Request export
* forged revision, Mode, phase, Validation, duplicate Card, illegal Play, and
  invalid accepted event/end rejection through `SkatAIInvariantError`

Implemented by Issue #152:

* independent Session Request Export version `1` with policies
  `existing_root_request_contract` and `exact_ready_retrospective_state`
* frozen available/unavailable `SessionRequestExportV1` with one optional
  existing `RequestDocumentV1`
* one accepted-Log replay and exact Historical readiness gate, with no builder
  call or partial Request when unavailable
* exact initial Player hands, Skat, metadata, Declaration, Discard, Play, trick,
  continuation, and Game-end mapping from the replayed projection
* existing Historical builder validation, canonical serialization and rebuild,
  immutable Root wrapping, equality verification, and deterministic output
* normal completion, every supported terminal ending, both continuation events,
  and every supported continuation/end chain without analysis or execution

Implemented by Issue #153:

* immutable Position Export Options version `1` with explicit Immediate/Search
  settings and existing recommendation-configuration validation
* one-replay information-safe Position readiness gate with no builder call while
  unavailable and one existing Position build while available
* exact stable-to-relative mapping of local hand, trick state, points, hand
  sizes, decision-visible Skat and Matadors, and authorized public hands
* appended `set_public_hand` Command with sole source `declared_ouvert`, exact
  current Declarer-hand validation, owner-aware coexistence, and shrinking
* generalized `SessionRequestExportV1` invariants for Position and Historical
  targets without changing its version
* immutable Decision Checkpoint version `1` with exact source identity/revision,
  Capture Mode, decision/trick/play indexes, actor/seat, information cutoff,
  relative map, and frozen Position Request
* replay and expected-Request equality verification without analysis,
  Application, Public API, transport, or workflow execution

Implemented by Issue #154:

* independent Session History Edit version `1` with exact Undo, correction,
  suffix, State, branching, and caller-retained-Redo policies
* immutable applied/unchanged/rejected/revision-conflict Undo Results with exact
  removed source suffixes
* revision-zero prefix reconstruction through the existing projection-level
  validator and one final Validation calculation
* immutable one-command Correction Requests and applied/unchanged/partial/
  rejected/revision-conflict Results
* deterministic original-suffix replay that stops before the first rejected
  later Command and returns exact replayed and discarded source records
* Mode, phase, trick, public-hand, Validation, and export-readiness recomputation
  from the actual active accepted Log
* immutable Checkpoint Lineage version `1` with current, ancestor, future, and
  diverged classification from exact prefix and Position Request reconstruction

Implemented by Issue #155:

* private Session Persistence document version `1` with document kind
  `skat_ai_session`, authoritative accepted-Log State, and caller-supplied frozen
  Decision Checkpoints in canonical order
* domain-separated deterministic SHA-256 State and content fingerprints that
  distinguish corrected same-revision histories and checkpoint-content changes
* strict exact-field reconstruction of persisted State, Commands, Validation,
  Position Requests, and Checkpoints, followed by full accepted-Log replay and
  both fingerprint checks
* resume-time recomputation of current, ancestor, future, or diverged Checkpoint
  lineage rather than persisted lineage authority
* optimistic expected-content-fingerprint writes with normal `saved`,
  `unchanged`, and `conflict` Results, including a second pre-replacement check
* canonical UTF-8 JSON files and durable same-directory temporary-file writes
  completed by atomic replacement, with owned temporary-file cleanup on failure

Implemented by Issue #156:

* stable `skat_ai.api.v1.session` version-1 namespace with exact immutable type
  identity, strict public Command parsing, and one typed Result envelope
* ten one-call in-memory operations covering create/apply, history edits, both
  exports, Checkpoint construction/classification, and persistence build/resume
* default-omitted complete redacted Session Provenance over exact returned values
* strict standalone `session.schema.json`, 63-Schema Package parity, and clean-
  install Session create/apply/export/persistence/resume validation

Implemented by Issue #157:

* stable `skat_ai.api.v1.session.files` version `1`, exact 12-name exports,
  path-free typed Save/Load Results, strict resume, and optimistic atomic Save
* appended `observe_checkpoint` and `export_checkpoint_review` Public Session
  operations with complete optional Session Provenance
* first accepted local-Play observation with explicit observed, pending, future,
  diverged, and ended-without-play statuses
* frozen-request-plus-observed-Card review export with no later private facts and
  no automatic analysis
* automatic exact Position-ready Checkpoint collection and equality
  deduplication, including source capture before accepted local Plays
* all 12 Session subcommands across installed, module, and Legacy forms, with
  optimistic persistence, privacy-safe summaries, and stable Exit Codes
* explicit Position analysis, Checkpoint review, and Historical finalization
  through the existing Application once when export is available
* deterministic phase-aware Assistant, six examples, and eight append-only
  generated scenarios for the published `v0.14.0` total of 85

Issue #158 completed Release preparation for the functional `v0.14.0` milestone,
which the maintainer subsequently published manually at commit `d5589f8`. GUI
or browser UI, platform adapters,
cloud synchronization, distributed locking, encryption/key management, and
automatic backup policy remain open. See
[Interactive session contracts](interactive_session_contracts.md) and
[Retrospective Session export](retrospective_session_export.md), and
[Session Position export and Decision checkpoints](live_session_position_export.md),
[Session Undo, correction, and Checkpoint lineage](session_undo_and_correction.md),
and [Session persistence and resume](session_persistence_and_resume.md).
The dedicated public contracts are documented in
[Public Session API version 1](public_session_api_v1.md),
[Session provenance](session_provenance.md),
[Session Decision observations](session_decision_observations.md), and
[Session CLI and end-to-end capture](session_cli_and_end_to_end_capture.md).

### Field-level provenance contract foundation

Implemented by Issue #138 for `v0.13.0`:

* canonical RFC 6901 JSON Pointer escaping, parsing, construction, and resolution
* frozen, slotted entries, source references, exemptions, ledgers, coverage
  summaries, and Information Use Context values
* exact-field and current-subtree coverage with deterministic JSON-leaf auditing
* complete, partial-legacy, and unavailable ledger status invariants
* same-ledger dependency, cycle, and coarse temporal monotonicity validation
* visibility- and availability-aware context-use validation
* pure engine-private public redaction and safe deterministic serialization
* explicit separation of provenance from existing Confidence contracts

Issue #143 constructs complete live decision ledgers and one partial-legacy
Position Result ledger inside Application execution. Issue #144 extends internal
propagation through flat retrospective Position Analysis, Historical Review,
Historical Search Review, Replay Coaching, and selected Position/Historical
Result branches. Issue #145 adds all five Training Dataset operations, automatic
Preparation, Opponent Statistics and Profiles, historical-list aggregation, and
independent-list comparison with complete non-legacy Root ledgers. Issue #146
completes Position/base Historical Result propagation. Issue #147 adds public
exposure only for the complete redacted Root Result and actual artifacts. See
[Field-level information provenance](field_level_information_provenance.md),
[Live analysis provenance](live_analysis_provenance.md),
[Retrospective review provenance](retrospective_review_provenance.md), and
[Dataset, list, and opponent provenance](dataset_list_and_opponent_provenance.md),
[Complete Result provenance](complete_result_provenance.md), and
[Public field provenance](public_field_provenance.md).

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
* exact nine-row canonical turn-phase classification
* preparation for empty left lead, empty right lead, and right response to an existing left lead
* same-World completion of the three former valid gaps without replaying the already played local Card
* continuation from the exact completed-Trick winner to the first new local Decision
* zero-step completion/preparation and unresolved-only `unsupported_turn_phase`
* one immutable private hidden-world root per path, owner-aware card removal, and a fixed hypothetical skat
* shared-root Policy Comparison with equal independent immutable policy-path copies
* privacy-safe coherent-world count and status summaries without hidden card identities
* strict Information-set Search with a domain-separated child seed and fresh
  public-state Search at every local decision
* safe nested Information-set Search Decisions, no-fallback stopping, and exact
  16-field compact Policy Comparison diagnostics

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

### Information-set Search

Implemented in the published `v0.17.0` baseline:

* the private three-Trick selected-world controlled-Player best-response executor;
* strict flat, Post-game, Historical Review, and Training Dataset evaluation
  routing from Issue #189;
* strict Multi-Step and Policy Comparison integration version `1` from Issue
  #190;
* per-local-decision child seed domain
  `multi_step_information_set_search_decision_v1` and fresh public-state Search;
* a private coherent execution World independent of every Search selection;
* no selected-World, controlled-Policy, cache, or memoized-bundle reuse across
  decisions;
* no-recommendation stopping before local play with no fallback;
* safe executed and stopped Decisions with the existing aggregate Result nested
  beneath them;
* exactly 16 compact Policy Comparison diagnostics;
* the default four comparison policies followed by exactly one configured
  `information_set_search` row, with shared-root independent path copies;
* visible but ineligible stopped rows under unchanged ranking; and
* retained-Result complete Position provenance without rerunning Search.
* strict one-Decision Match execution through one existing Position Application,
  safe browser diagnostics, and exact revision-scoped Report-source transfer;
* focused Current-Snapshot Strategy Teacher Evidence, Dataset-v2 joins, cross-
  game method counts, and existing local Corpus workflow support from Issue #191;
* separate Information-set Replay Coaching and private Match Historical
  Information-set Review/Coaching through one retained Review and one Historical
  Application invocation from Issue #192; and
* a strict eight-case synthetic benchmark corpus, frozen functional and
  structural signatures, Strategy-Fusion and duplicate-weight diagnostics,
  focused tests, and documented local measurements from Issue #193.

Existing `auto` remains PIMC then Immediate, and no `information_set_auto`
exists. Product/runtime performance acceptance gates and latency guarantees
remain open. There is no
cross-decision global Policy, equilibrium, global-optimality, complete-contract,
or calibrated-probability claim. See [Information-set Search Multi-Step and
Policy Comparison](information_set_search_multi_step_and_policy_comparison.md)
and [Match Information-set Search and Strategy Teacher Evidence](match_information_set_search_and_strategy_teacher.md),
plus [Information-set Replay Coaching and Match Historical analysis](information_set_replay_coaching_and_match_historical_analysis.md)
and [Information-set Search performance](information_set_search_performance.md).

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
* exact legal prefixes and remaining-hand reconstruction for all six supported shortened terminal events
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
* immutable version-3 Settlement Normative Matrix covering current support,
  bounded interpretations, legacy compatibility, one supported bounded
  Historical Claim, and durable `not_supported_v1` boundaries
* private version-1 party-wide Claim, complete Evidence, exact-state, Proof
  Request/preparation, assignment, diagnostic Move, and Result contracts
* private bounded exhaustive exact AND/OR Claim proof execution with canonical
  legal Cards, exact transitions, invocation-local memoization, and stable lines
* private valid-proof-only Claim adjudication with complete point/Trick
  assignment, preexisting-winner preservation, Suit/Grand/Null semantics, and
  existing Final Settlement composition
* focused Historical-only Claim integration with one retained replay, one
  available Proof execution, valid-only acceptance, strict diagnostic output,
  Provenance, CLI, Review/Coaching, Dataset, list, and statistics compatibility

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

The approved party-wide Claim contracts, exact-state preparation, bounded proof
execution, valid-proof adjudication, and existing Final Settlement composition
are integrated through Historical Game input only. Flat Position, Session, Match
Capture, and Corpus Claim entry remain open. Specific
future-Trick Claims, defender-open-play
proof beyond five unresolved Tricks, and the other durable v1 Claim exclusions
are `not_supported_v1`; broader Settlement nuance remains incomplete.
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
* root-selected CLI execution with only `--input`, `--output`, `--quiet`, and the
  cross-workflow `--include-provenance` option, full single-list progression, and
  compact comparison presentation
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
* strict public field-provenance schema referenced from every Root output branch
* input example schema validation
* generated output schema validation
* schema validation documentation

The published `v0.12.0` baseline covers 70 deterministic generated-output
scenarios and 4,762 pytest tests. The published `v0.11.0` baseline remains
historical evidence for 64 scenarios and 4,392 pytest tests. The historical published `v0.10.0`
release baseline remains 59 scenarios and 4,075 tests, and the historical
published `v0.9.0` baseline remains 52 scenarios and 3,558 tests.

Issue #130 appends three historical-list scenarios. Issue #134 preserves those
67 scenarios and appends three automatic Training Dataset preparation scenarios,
so the published `v0.12.0` package baseline validates exactly 70 outputs without changing
the historical published baselines.
Issue #147 preserves those 70 published scenarios and appends seven public
field-provenance scenarios, one per Root workflow. The `v0.13.0` package baseline
has 62 schemas and 77 generated-output scenarios, while the published `v0.12.0`
facts remain
70 scenarios and 4,762 tests.

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
Issues #194 and #195 now provide separate deterministic structural Tactical
Motif detection and descriptive cross-game Counts. Stronger Search, tactical
quality outside retained complete-Search Teacher evidence, broader interpreted
Coaching, and causal language remain unimplemented. Issue #196 provides the
separate bounded deterministic Tactical Cross-game Coaching slice. See
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
* installed `skat-ai`, module `python -m skat_ai`, and Legacy `python main.py`
  invocation forms over one canonical Package parser and transport
* exact `--version` output, invocation-specific help, unchanged Exit Codes, and
  clean-install CLI/API parity

## Current important modules

### Public API contracts

* `api/v1/contracts.py`
  * API constants, workflows, immutable documents, options, public execution
    results and artifacts, policy, and version info
* `api/v1/execution.py`
  * Request parsing and verification, workflow-option translation, one-pass
    Application execution, artifact and optional public-provenance conversion,
    and stable boundary errors
* `api/v1/provenance.py`
  * public version, Root field and scopes, immutable attachment/artifact/bundle
    values, seven Result mappings, and strict public invariants
* `api/v1/schema_validation.py`
  * lazy Package Resource Draft 2020-12 Root schema validation with local-only
    resolution and deterministic RFC 6901 errors
* `_version.py`
  * installed Package version lookup and source-only fallback
* `errors.py`
  * stable errors, error codes, serialization, warning category, and Exit Codes

### Field-level provenance

* `field_provenance.py`
  * immutable entries, source references, exemptions and ledgers, RFC 6901
    helpers, dependencies, temporal validation, and serialization
* `field_provenance_coverage.py`
  * deterministic JSON-leaf enumeration and exact/subtree coverage auditing
* `field_provenance_policy.py`
  * Information Use Context, use validation, and engine-private public redaction
* `v1_information_provenance_sources.py`
  * exact consumed Request/effective-option/external sources, canonical ledgers,
    and invocation-local bindings
* `v1_information_provenance_enforcement.py`
  * four-stage identity, pre-analysis policy validation, source authorization,
    and retained-stage linkage
* `v1_information_provenance_serialization.py`
  * exact final Result/artifact reconciliation and immutable checkpoints
* `live_analysis_provenance.py`
  * complete decision documents, live Result mapping, deterministic collection,
    and Application bundle construction
* `retrospective_review_provenance.py`
  * flat review stage separation, complete attachment construction, privacy
    validation, and nested Search mapping
* `historical_review_provenance.py`
  * Historical decision, aggregate review, Coaching, and complete Root Result
    collection
* `position_result_provenance.py`
  * complete branch-specific Position Result mapping and dependency enforcement
* `historical_result_provenance.py`
  * canonical record, replay, point, event, terminal, and complete Historical
    Result mapping
* `settlement_result_provenance.py`
  * shared Result entries for Game Value, Overbid, and final Settlement
* `replay_coaching_provenance.py`
  * retained evidence, assessment, prioritization, guidance, and complete report
    provenance
* `search_provenance.py`
  * complete aggregate-only Search Result provenance for every status
* `simulation_provenance.py`
  * public/local decision-hook contract and seed-free selection settings
* `training_dataset_provenance.py`
  * Dataset input, Record, Feature/Target, audit, rolling, Search-evaluation,
    historical aggregation, artifact, and complete Root provenance
* `dataset_preparation_provenance.py`
  * split-safe source facts, assignment restrictions, Plan, materialization, and
    complete Root provenance
* `opponent_workflow_provenance.py`
  * external/historical source distinction, normalized Profile derivation, and
    complete Root provenance
* `historical_list_provenance.py`
  * 36 Entry Facts, prefix-safe progression, standings, external lot,
    independent comparison, and complete Root provenance
* `public_field_provenance.py`
  * bounded Result/artifact selection, existing-helper redaction, complete
    recomputed coverage, and Root sidecar attachment

### Application orchestration

* `application/contracts.py`
  * orchestration version, immutable invocations, workflow options, injected
    documents, results, optional provenance, and auxiliary artifacts
* `application/provenance.py`
  * immutable matching attachments and canonical Application bundles
* `application/execution.py`
  * workflow-option validation, mandatory four-stage Provenance lifecycle, and
    generic seven-handler dispatch
* `application/position_workflow.py`
  * transport-free Position Analysis, Multi-Step, Policy Comparison, and live
    Opponent Statistics application
* `application/historical_game_workflow.py`
  * transport-free Historical Game, review, Search, Coaching, and time-safe
    Opponent Statistics application
* `application/training_dataset_workflow.py`
  * six isolated Training Dataset operations and optional export artifact
* `application/simple_workflows.py`
  * transport-free preparation, statistics, list, and comparison handlers

### CLI entry points

* `cli/execution.py`
  * Root compatibility facade preserving established imports and patch seams
* `cli/root_parser.py`, `cli/root_validation.py`, and `cli/root_dispatch.py`
  * exact Root parser, CLI-only validation, workflow selection, and Exit Codes
* `cli/root_compatibility.py` and `cli/root_application.py`
  * Legacy dependency resolution and one-invocation Application adaptation
* `cli/root_transport.py` and `cli/presentation/`
  * file/output transport and pure already-produced-Result presentation
* `cli/__init__.py`
  * exact `skat_ai.cli:main` Console Script target
* `__main__.py`
  * `python -m skat_ai` delegation
* repository-root `main.py`
  * Legacy compatibility facade and Root monkeypatch adapter through `v1.0.0`

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

### Match capture and Workspaces

* `match_capture_contracts.py`, `match_source_metadata.py`,
  `match_tournament_format.py`, and `match_player_snapshot.py`
  * immutable Match identity, source bounds, canonical format, fixed participants,
    perspective, and optional Statistics Snapshots
* `observed_game_contracts.py`, `observed_game_trace.py`,
  `observed_game_commentary.py`, and `observed_game_evidence.py`
  * partial and complete observed Games, exact public Play validation,
    commentary/response links, and derived evidence capabilities
* `match_workspace_contracts.py` and `match_workspace_rotation.py`
  * exact 36-Slot Workspace creation/validation and existing fixed-list rotation
* `match_workspace_operations.py` and `match_workspace_progress.py`
  * immutable revisioned Slot/definition changes and evidence-derived Progress
* `match_workspace_persistence_contracts.py`,
  `match_workspace_persistence_codec.py`, and `match_workspace_persistence.py`
  * private fingerprinted documents, strict nested Resume, canonical Load, and
    optimistic same-directory atomic Save
* `match_capture_application_contracts.py`,
  `match_capture_position_view.py`, `match_capture_game_updates.py`, and
  `match_capture_application.py`
  * transport-free Capture contracts, UI-ready View derivation, defensive Game
    rebuilding, automatic Play/annotation updates, and revision orchestration
* `match_observed_reconstruction.py` and
  `match_decision_review_preparation.py`
  * validated exact playable-hand reconstruction, information-safe Decision
    snapshots, skipped reasons, actual-Card cutoff, and relative eligible Profile
    bindings without application
* `match_historical_materialization.py` and
  `match_training_source_materialization.py`
  * strict existing normal-completion Historical Games, Match-level played time,
    and unpartitioned Training source Records without Plans or samples
* `match_workspace_materialization.py`
  * exact 36-Slot status/count reconciliation, Passed Deals, Commentary sidecars,
    and complete existing fixed-list construction plus aggregation without
    workflow execution
* `learning_corpus_identity.py`, `learning_corpus_references.py`,
  `learning_corpus_match_snapshot.py`, and `learning_corpus_catalog.py`
  * private canonical identity domains, exact immutable Workspace source copies,
    closed Snapshot-scoped references, lightweight Catalog entries, explicit
    current selections, and non-mutating duplicate/revision classification
* `learning_corpus_player_catalog.py`, `learning_corpus_player_aliases.py`, and
  `learning_corpus_player_statistics.py`
  * derived Current-Snapshot Player entries, exact aliases/conflicts, complete
    Match-bound Statistics history, and strict time-safe selection without merge
    or Profile derivation
* `learning_corpus_human_evidence.py`,
  `learning_corpus_human_evidence_builder.py`, and
  `learning_corpus_human_evidence_export.py`
  * exact Current-only Commentary/Response source evidence and canonical export
* `learning_corpus_strategy_teacher.py`,
  `learning_corpus_information_set_strategy_teacher.py`,
  `learning_corpus_strategy_teacher_builder.py`, and
  `learning_corpus_strategy_teacher_export.py`
  * exact Current-bound method-specific Teacher evidence and canonical export
* `learning_corpus_tactical_motif_evidence.py`,
  `learning_corpus_tactical_motif_builder.py`,
  `learning_corpus_tactical_motif_summary.py`, and
  `learning_corpus_tactical_motif_export.py`
  * exact Current-only safe Tactical observations or explicit skips, descriptive
    global/Player/scope/recurrence Counts, and two canonical private exports
* `learning_dataset_v2_contracts.py`, `learning_dataset_v2_builder.py`, and
  `learning_dataset_v2_export.py`
  * private unpartitioned task-neutral Decision records, safe/skipped coverage,
    cached Player Context, exact evidence joins/pools, and canonical export
* `learning_dataset_v2_partition_contracts.py`,
  `learning_dataset_v2_partition_identity.py`,
  `learning_dataset_v2_partition_algorithms.py`,
  `learning_dataset_v2_partition_audit.py`,
  `learning_dataset_v2_partition_preparation.py`, and
  `learning_dataset_v2_partition_export.py`
  * private Match-group-safe Known-player and unseen-player Plans, exact balance
    identities, leakage audits, lossless partition indexes, and canonical export
* `learning_dataset_v2_summary_contracts.py`,
  `learning_dataset_v2_summary_builder.py`, and
  `learning_dataset_v2_summary_export.py`
  * private descriptive Match, Player, Communication, Strategy, Coverage, and
    readiness summaries over exact sources and supplied partition Results
* `match_analysis_report_source_export.py` and
  `match_analysis_report_source_codec.py`
  * exact executed Decision Report transfer bytes and strict complete reconstruction
* `match_information_set_search.py`
  * Match profile-to-budget mapping, strict safe Result/comparison reconciliation,
    and curated Information-set browser diagnostics
* `learning_corpus_tactical_coaching_contracts.py`,
  `learning_corpus_tactical_coaching_assessment.py`,
  `learning_corpus_tactical_cross_game_coaching.py`, and
  `learning_corpus_tactical_coaching_export.py`
  * exact retained-evidence Teacher Assessments, semantic Decision consensus,
    bounded cross-Game focus/Guidance, Player Reports, and path-free export
* `cli/corpus_parser.py`, `cli/corpus.py`, and `corpus_web/`
  * private one-root CLI/HTTP transport, strict uploads, process-local sources
    and prepared artifacts, minimized rendering, security, and ten downloads

### Interactive Session contracts

* `session_commands.py`
  * typed caller-fact Commands and exact allowed-phase metadata
* `session_contracts.py`
  * Player identity, Modes, phases, accepted Log records, and immutable State
* `session_validation.py`
  * Diagnostics, export readiness, validation status, and Transition Results
* `session_projection.py`
  * immutable accepted-fact projection and deterministic internal serialization
* `session_incremental_validation.py`
  * one-Command phase/rule/information validation and readiness computation
* `session_transitions.py`
  * revision-zero creation, accepted-Log replay, conflicts, atomic append, and
    forged-State detection
* `session_export_contracts.py`
  * immutable available/unavailable Request export contract and policies
* `session_historical_export.py`
  * one-replay readiness gate, exact Historical mapping, canonical round trip,
    and immutable existing Root Request construction
* `session_position_export.py`
  * information-safe Position readiness gate and existing Request construction
* `session_decision_checkpoint.py`
  * replay-verified immutable local pre-Play Checkpoint construction
* `session_history_contracts.py`
  * immutable History Edit and Checkpoint Lineage versions, policies, and Results
* `session_history.py`
  * strict-prefix Undo, one-command correction, linear suffix replay, and lineage
* `session_persistence_contracts.py`
  * private document, Resume and Write Result contracts, policies, and statuses
* `session_persistence_codec.py`
  * State/content fingerprints, strict reconstruction and replay, canonical
    Checkpoint retention, and lineage recomputation
* `session_persistence.py`
  * strict private file loading, canonical expected-fingerprint saves, conflict
    detection, and atomic same-directory replacement
* `session_decision_observation.py`
  * accepted-Log actual-card derivation, lineage/status relationships, and
    deterministic immutable observations
* `session_checkpoint_review.py`
  * isolated frozen-request-plus-observed-Card review Request export
* `session_checkpoint_collection.py`
  * exact Position-ready Checkpoint collection and equality deduplication
* `api/v1/session/`
  * stable contracts, exact re-exports, strict Schema boundaries, and twelve
    public operation wrappers
* `api/v1/session/files/`
  * stable Save/Load contracts, path-free Results, strict boundary translation,
    and standalone Session Schema validation
* `session_provenance.py`
  * complete operation-value ledgers, public redaction, coverage recomputation,
    and public Session Provenance bundle construction
* `cli/session.py`
  * Session compatibility facade retaining established constants, functions,
    helper aliases, and signatures
* `cli/session_parser.py`, `cli/session_transport.py`, and `cli/session_context.py`
  * separate parser, strict JSON input, context, and optimistic persistence
* `cli/session_checkpoints.py` and `cli/session_operations.py`
  * automatic Checkpoints, all 12 handlers, Save decisions, and dispatch
* `cli/session_application.py` and `cli/session_presentation.py`
  * explicit existing-Application execution and privacy-safe output
* `cli/session_assistant.py`
  * phase-aware prompts over explicit focused services, exact typed Commands,
    per-mutation Save, and injectable input/output functions

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
* `party_wide_claim_contracts.py`
* `party_wide_claim_evidence.py`
* `party_wide_claim_proof_contracts.py`
* `party_wide_claim_proof_executor.py`
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
* `learning_dataset_v2_contracts.py`
* `learning_dataset_v2_builder.py`
* `learning_dataset_v2_export.py`
* `learning_dataset_v2_partition_contracts.py`
* `learning_dataset_v2_partition_identity.py`
* `learning_dataset_v2_partition_algorithms.py`
* `learning_dataset_v2_partition_audit.py`
* `learning_dataset_v2_partition_preparation.py`
* `learning_dataset_v2_partition_export.py`
* `learning_dataset_v2_summary_contracts.py`
* `learning_dataset_v2_summary_builder.py`
* `learning_dataset_v2_summary_export.py`
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
* `canonical_multi_step_phase.py`
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
* `docs/public_api_contracts.md`
* `docs/public_python_api_v1.md`
* `docs/installed_cli.md`
* `docs/packaging_and_distribution.md`
* `docs/application_orchestration.md`
* `docs/interactive_session_contracts.md`
* `docs/incremental_session_transitions.md`
* `docs/retrospective_session_export.md`
* `docs/live_session_position_export.md`
* `docs/session_undo_and_correction.md`
* `docs/session_persistence_and_resume.md`
* `docs/public_session_api_v1.md`
* `docs/session_provenance.md`
* `docs/session_decision_observations.md`
* `docs/session_cli_and_end_to_end_capture.md`
* `docs/field_level_information_provenance.md`
* `docs/v1_information_provenance_enforcement.md`
* `docs/public_field_provenance.md`
* `docs/complete_result_provenance.md`
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
* `docs/information_set_search_performance.md`
* `docs/replay_coaching_contracts.md`
* `docs/historical_opponent_profiles.md`
* `docs/training_data.md`
* `docs/dataset_partition_policies.md`
* `docs/automatic_dataset_preparation_contracts.md`
* `docs/temporal_known_opponent_dataset_splits.md`
* `docs/player_disjoint_unseen_player_dataset_splits.md`
* `docs/opponent_statistics.md`
* `docs/match_capture_contracts.md`
* `docs/observed_game_capture_contracts.md`
* `docs/match_workspace_contracts.md`
* `docs/match_capture_application_services.md`
* `docs/local_match_capture_interface.md`
* `docs/match_player_statistics.md`
* `docs/match_review_and_materialization.md`
* `docs/match_analysis_and_exports.md`
* `docs/match_information_set_search_and_strategy_teacher.md`
* `docs/learning_corpus_identity_and_catalogs.md`
* `docs/learning_corpus_persistence_and_import.md`
* `docs/learning_corpus_player_catalog_and_statistics_history.md`
* `docs/learning_corpus_human_commentary_and_response_evidence.md`
* `docs/learning_corpus_strategy_teacher_evidence.md`
* `docs/learning_dataset_v2.md`
* `docs/learning_dataset_v2_partition_preparation.md`
* `docs/learning_dataset_v2_cross_game_summaries.md`
* `docs/learning_corpus_tactical_motif_evidence_and_summaries.md`
* `docs/learning_corpus_tactical_cross_game_coaching.md`
* `docs/learning_corpus_browser_workflows.md`
* `docs/opponent_profile_derivation.md`
* `docs/live_opponent_profiles.md`
* `docs/historical_opponent_statistics.md`
* `docs/opponent_policy_evaluation.md`
* `docs/requirements_traceability.md`
* `docs/settlement_normative_matrix.md`
* `docs/claim_and_settlement_v1_boundaries.md`
* `docs/party_wide_claim_contracts.md`
* `docs/party_wide_claim_proof_executor.md`
* `docs/v0_17_release_readiness_audit.md`
* `docs/v1_scope.md`
* `docs/v1_0_scope_and_traceability_audit.md`
* `docs/roadmap.md`
* `docs/project_handoff.md`

## Release status

Current published stable and latest stable GitHub Release: `v0.17.0`.

Current Package version: `0.17.0`.

Current Package baseline: published `v0.17.0`.

Published Release theme: "Rules, Search, Coaching, and performance closure".

Published GitHub Release title: "v0.17.0 — Rules, Search, Coaching, and
performance closure".

Historical `v0.16.0` Release theme: "Learning-ready behavior and communication data".

Historical `v0.16.0` GitHub Release title: "v0.16.0 — Learning-ready behavior and
communication data".

Published Release commit: `8187fbe684559f9c0c2ba444be1bf33950359ad2`
(`8187fbe`).

Publication date: 2026-08-25.

The Package requires Python `>=3.13` and retains Public API contract version `1`,
exactly seven Root workflows, and the one
`skat-ai = skat_ai.cli:main` Console Script. The current published baseline has
Settlement Normative Matrix version `3` with 61 cases, 71 authoritative Schemas,
71 Packaged Schema Resources, six Session examples, 98 generated outputs, ten
private Corpus prepared downloads, and 7,479 passing pytest tests in 921.96s.
GitHub Releases is the authoritative publication record; no Package-index or
PyPI publication is claimed.

The historical published `v0.16.0` baseline at `91b1360`, published on
2026-08-18, has 63 authoritative and packaged Schemas, six Session examples, 85
generated outputs, and 6,925 passing pytest tests in 1083.48s. Functional Issues
#171 through #179 implement that milestone, Issue #180 completed Release
preparation, and Issue #181 synchronized publication status without product
functionality.

The published `v0.17.0` functional history uses Package version `0.17.0`, Python
`>=3.13`, Public API contract version `1`, seven Root workflows, one Console
Script, and six Session examples. Issue #186 updates the Matrix to version `3`
with the same 61 cases. Issue #189 adds four Information-set Search Schemas, one
example, and four generated-output scenarios. Issue #190 adds strict Multi-Step
and Policy Comparison integration, one example, and two scenarios without a new
Schema, bringing the working totals to 69 authoritative and packaged Schemas and
94 scenarios. The published `v0.16.0` counts above remain unchanged Release
facts.

Issue #191 adds private one-Decision Match Information-set Search, exact Report-
source transfer, focused Teacher Evidence, Dataset-v2 joins, Summary counts, and
existing Corpus workflow support without changing those counts.

Issue #192 adds one strict Information-set Replay Coaching Schema, one Root
example, and two append-only scenarios after that 69/94 Issue #190 baseline. The
Issue #192 point-in-time totals are 70 authoritative and packaged Schemas and 96
scenarios. Package/API/workflow/Console-Script/Session baselines and Settlement
Matrix version `3` with 61 cases remain unchanged.

Issue #193 adds a deterministic synthetic Information-set Search benchmark
corpus, a strict repository-local runner and focused tests, and documented local
reference measurements. It changes no production code, Schema, route, profile,
Public API, Package version, example, generated scenario, or working count.

Issue #194 adds one strict Historical Tactical Motif Review Schema, one Root
example, and two append-only scenarios. The final published totals are 71
authoritative and packaged Schemas and 98 scenarios. Package/API/workflow/
Console-Script/Session baselines and Settlement Matrix version `3` with 61 cases
remain unchanged.

Issue #195 adds private Current-Match-Snapshot-only Tactical Motif Evidence,
explicit skips, exact descriptive cross-game summaries, atomic process-local
Corpus preparation, minimized presentation, and two authenticated downloads. It
changes no Package/API/workflow/Console-Script/Schema/example/generated-scenario/
Session/Dataset-v2 baseline, so the published totals remain 71 Schemas and
98 scenarios.

Issue #196 adds private deterministic Tactical Cross-game Coaching, exact
Tactical/Teacher joins, retained exact and semantic Teacher accounting,
complete-Search-only repeated cross-Game focus, bounded fixed Guidance, atomic
third-family Corpus publication, minimized aggregate presentation, and one tenth
authenticated download. It changes no Package/API/workflow/Console-Script/
Schema/example/generated-scenario/Session/Dataset-v2 baseline, so the current
working totals remain 71 Schemas and 98 scenarios.

Issue #197 records the documentation-only scope and Release-readiness audit.
Issue #198 changes only Package metadata, current version expectations,
Changelog, and Release-candidate documentation. The maintainer subsequently
published `v0.17.0` on 2026-08-25 at `8187fbe`, and Issue #199 synchronizes that
publication without product functionality. Issues #182 through #196 are the
functional milestone; Issues #197, #198, and #199 add no product functionality.

Historical published `v0.15.0` Release theme: "Local EuroSkat 36er Match
capture, analysis, and exports".

Historical GitHub Release title: "v0.15.0 — Local EuroSkat 36er Match capture,
analysis, and exports".

Historical Release commit: `ec1c154`.

The historical `v0.15.0` baseline contains 63 authoritative Schemas and 63
Packaged Schema Resources, six Session examples, 85 generated-output scenarios,
and 6,510 passing pytest tests. Issues #160 through #168 implement its functional
milestone, Issue #169 completed Release preparation, and Issue #170 synchronized
publication status after manual maintainer publication.

Historical published `v0.14.0` Release theme: "End-to-end Live and Retrospective
Session capture".

Historical GitHub Release title: "v0.14.0 — End-to-end Live and Retrospective
Session capture".

Historical Release commit: `d5589f8`.

The historical `v0.14.0` baseline contains 63 authoritative Schemas and 63
Packaged Schema Resources, six Session examples, 85 generated-output scenarios,
and 5,892 passing pytest tests. Issues #150 through #157 implement its functional
milestone, Issue #158 completed Release preparation, and Issue #159 synchronized
publication status after manual maintainer publication.

The historical published `v0.16.0 — Learning-ready behavior and communication
data` Package milestone is functionally complete through Issue #179's private local
Learning Corpus/Dataset-v2 workflow. Issue #180 changed only Package version,
matching expectations, Changelog, and Release-state documentation to complete
Release preparation without product behavior changes. The Package retains 63
authoritative and packaged Schemas, six Session examples, 85 generated outputs,
and 6,925 pytest tests. The maintainer published the Release manually on
2026-08-18 at commit `91b1360`, and Issue #181 synchronizes publication status.
No Package-index or PyPI publication is claimed.

The `v0.17.0 — Rules, Search, Coaching, and performance closure` functional
milestone is complete through Issue #196. Issue #182 closes the Claim product-
decision gate, and
Issue #183 adds private structured Claim and exact-proof contracts plus one
untraversed exact-state preparation. Issue #184 adds private bounded exhaustive
exact AND/OR proof execution. Issue #185 adds private valid-proof adjudication
and existing Final Settlement composition. Issue #186 updates Matrix version `3`
without changing its 61 cases and completes the approved bounded Claim and Final
Settlement runtime slice through Historical Game input only. All other current
Claim boundaries remain durable v1 exclusions. Session, Match Capture, and Corpus
Claim entry remain open. Stronger information-set Search
and Strategy Fusion mitigation now include Issue #187's private contracts and
Issue #188's bounded selected-world controlled-Player executor. Issue #189 adds
strict flat routing, same-selection PIMC plus independently seeded Immediate
retrospective comparison, separate Historical Review and Training Dataset
evaluation, safe public Results, retained-stage Provenance, CLI, Schemas, an
example, and generated scenarios. Issue #190 adds strict Multi-Step and Policy
Comparison integration with fresh per-decision Search, safe Results/diagnostics,
no fallback, existing ranking, and complete Provenance. Match Capture, Match
Analysis Reports, and Strategy Teacher are integrated for the bounded one-
Decision path by Issue #191 together with Dataset-v2 and Corpus propagation.
Issue #192 adds separate Information-set Replay Coaching and private Match
Historical Information-set Review/Coaching with retained Review reuse,
complete-Candidate primary evidence, diagnostic PIMC/Immediate without fallback,
time-safe fixed Profile Policies, and complete Provenance. Issue #193 adds
repository-local benchmark evidence without changing production behavior.
Issue #194 adds deterministic Historical Tactical Motif Review, exact structural
lead/void/Trick-control/Defender-partnership/hand-shape/outcome evidence, shared
Snapshot reuse, complete Provenance, strict Root Schema and CLI, and private
Match browser controls. It does not add tactical quality assessment, intent,
signaling, communication, or causality. Issue #195 reuses the same exact detector
for separate Current-Snapshot Corpus Evidence and descriptive cross-game Counts,
including bounded recurrence scopes, without adding those interpretations or
changing Learning Dataset version `2`.
Issue #196 adds separate deterministic Tactical Cross-game Coaching from exact
retained Tactical and Teacher evidence. It preserves every exact Report, counts
semantic duplicates once per Decision consensus, treats only unanimous complete-
Search evidence as focus-eligible, requires at least two qualifying Decisions in
at least two Games, retains at most five fixed-Guidance focus areas per Player,
and keeps zero-count Players in Catalog order. It executes no analysis and makes
no truth, perfect-play, Player-rating, intent, communication, causal, or
significance claim.
Issue #193 satisfies the bounded v0.17.0 performance-evidence contract. Issue
#200 accepts deterministic functional/structural performance for v1, classifies
latency guarantees and broader tactical/Rating work as not required, and retains
broader internal Provenance as a blocker. Issue #202 subsequently closes that
blocker without widening public Provenance. Issues #182 through #196 are the
frozen functional history. Issue #197 completes the documentation-only audit,
and Issue #198 prepares Package `0.17.0` and the Release candidate without
product behavior changes. The maintainer published `v0.17.0` on 2026-08-25 at
`8187fbe`, and Issue #199 synchronizes that publication without product
functionality. Issue #200 freezes the bounded `v1.0.0` scope and exact #201
through #207 sequence. Issue #201 adds independent exhaustive official-rule
evidence for R-01 and R-06 without product-code change and closes B-01. Six
blockers B-02 through B-07 remained at that point. Issue #202 makes P-10 and P-13
`satisfied`, closes B-02, and leaves five blockers B-03 through B-07 at that
point. Issue #203 completes all nine concrete canonical Multi-Step phases, makes
P-19 `satisfied`, and closes B-03 without widening Search or public contracts.
Four blockers B-04 through B-07 remained at that point. Issue #204 applies exact
`AGPL-3.0-only` legal files and PEP 639 metadata and closes B-04. P-09 is now
`implementation_required` under B-08/#205, while B-09 adds maintainer UAT
outside the 53-row ledger. Five blockers B-05 through B-09 remain. The milestone
is not ready, and Issue #205 is next.

Historical published Package milestone: `v0.15.0`, providing usable manual post-
game capture of one EuroSkat 36er Standard Match from descriptive video evidence.
Issues #160 and #161 implement the internal immutable Match identity/metadata and
observed single-Game/commentary foundations. Issue #163 adds persistent internal
36-position Workspaces. Issue #164 adds internal transport-free rapid-entry
Application services over those Workspaces. Issue #165 adds the private local
browser/Capture CLI with loopback security and optimistic autosave. Issue #166
adds Match-bound Snapshot editing and time-safe Profile preparation. Issue #167
adds internal Decision preparation and strict Historical, unpartitioned
Training-source, and complete fixed-list materialization without workflow
execution. Issue #168 adds explicit one-Decision Position and strict Historical
Application execution, existing-behavior eligible Profile application,
no-workflow Match materialization, deterministic max-eight revision-scoped
reports, concurrency invalidation, and authenticated canonical local downloads.
It completes the functional milestone. Issue #169 updated only the Package
version, matching assertions, Changelog, and release-state documentation to
complete Release preparation. The maintainer published `v0.15.0` manually at
commit `ec1c154`, and Issue #170 synchronizes that publication status.

Historical published `v0.13.0` Release theme: "Stable API, installable tooling,
and public field provenance".

Historical GitHub Release title: "v0.13.0 — Stable API, installable tooling, and
public field provenance".

Historical Release commit: `abd1ad3`.

The historical published `v0.13.0` baseline requires Python `>=3.13`, retains
Public API contract version `1`, contains 62 authoritative Schemas and 62
Packaged Schema Resources, validates 77 deterministic generated-output
scenarios, and passes 5,399 pytest tests. Issues #137 through #147 complete its
functional milestone, Issue #148 completed Release preparation, and Issue #149
synchronized its publication status.

Historical published `v0.12.0` Release theme: "Fixed-three-player historical
lists and deterministic dataset preparation".

Historical GitHub Release title: "v0.12.0 — Fixed-three-player historical lists
and deterministic dataset preparation".

Historical Release commit: `bbf955e`.

The historical published baseline requires Python `>=3.13`, validates 70
deterministic generated-output scenarios, and passes 4,762 pytest tests.

Issues #127 through #134 complete the functional milestone, and Issue #135
completed release preparation. Publication was performed manually by the
maintainer, and GitHub Releases remains authoritative. Issue #136 synchronized
the historical publication status.

Historical published `v0.11.0` release theme: "Information-safe Replay Coaching
and structured historical outcomes".

Historical GitHub Release title: "v0.11.0 — Information-safe Replay Coaching
and structured historical outcomes".

The historical release points to commit `cfd28e5`, validates 64 deterministic
generated-output scenarios, and passes 4,392 pytest tests.

Issues #118 through #124 complete the functional `v0.11.0` milestone, and Issue
#125 completed release preparation. Publication was performed manually by the
maintainer. GitHub Releases is the authoritative publication record.

The published `v0.12.0` package baseline implements the immutable
historical-list source, cumulative aggregation, independent comparison, and
strict public JSON/schema/CLI workflow, plus internal version-1 unpartitioned
dataset-preparation and supplied split-plan contracts plus deterministic
temporal Known-opponent and Player-disjoint unseen-player assignment generators.
Issue #134 adds the root-selected public preparation workflow, strict schemas,
CLI, and three examples. The prior 67 scenarios are unchanged, and that
historical published baseline validates 70 while the historical published
`v0.11.0` baseline remains 64. Issue #135 completed release preparation before
manual maintainer publication.

Issue #137 is the first implemented `v0.13.0` foundation. It adds API contract
version `1`, exact public exports, immutable JSON Request and Result wrappers,
compatibility metadata, stable errors, and unchanged legacy Root CLI behavior.
It changes no Package version, schema, workflow execution, example, or generated
scenario.

Issue #138 adds the internal version-1 field-level provenance language,
immutable sidecar ledger, deterministic coverage and dependency validation,
Information Use Context, public redaction, and safe serialization. It changes no
Package version, public API export, schema, workflow output, CLI, example, or
generated scenario. Subsequent Issues #143 through #147 add the bounded workflow
and public propagation described below.

Issue #143 adds internal Application provenance version `1` and live-analysis
provenance version `1`, complete decision-time enforcement for flat and simulated
live Position selection, aggregate-only Search and structural inference mapping,
and exact partial-legacy Position Result coverage. It changes no Package version,
public API export, Root output, schema, CLI, example, or generated scenario.

Issue #144 adds retrospective-review and Replay Coaching provenance version `1`,
separates pre-actual and post-actual Position/Historical stages, reuses retained
Immediate and Search values, covers requested review and report summaries, and
adds exact partial-legacy Historical Result coverage. It changes no Package
version, public API export, Root output, schema, CLI, example, or generated
scenario.

Issue #145 adds four focused internal propagation versions, complete non-legacy
Root ledgers for Dataset, Preparation, Opponent, list, and comparison workflows,
and retained-stage Feature/Target, audit, rolling, Search, split, Profile, Entry,
progression, standings, lot, and comparison provenance. It changes no Package
version, public API export, Root output, Schema, CLI, example, or generated
scenario.

Issue #146 adds complete Result provenance version `1`, replaces the Position
and Historical partial-legacy Root ledgers with complete non-legacy mappings,
adds a result-only bundle for base Historical execution, and enforces
forward-only scoring, Result, Settlement, Performance, list, replay, event, and
terminal dependencies with private-proof-safe redaction. It changes no Package
version, public API export, Root output, Schema, CLI, example, generated
scenario, or established workflow call count.

Issue #147 adds public field-provenance version `1`, Root field
`field_provenance`, document scopes `root_result_without_field_provenance` and
`artifact_document`, immutable public attachment/artifact/bundle contracts, seven
explicit Result mappings, and the actual `opponent_statistics_input` to
`training_dataset/opponent_statistics_input` mapping. Existing-helper redaction
is followed by complete recomputed coverage. Public API
`ExecutionOptionsV1.include_provenance` defaults to false, while all three CLI
forms accept `--include-provenance` with concise or quiet behavior. The strict
Schema raises the eventual `v0.13.0` resource count to 62; seven append-only
scenarios raise the eventual `v0.13.0` matrix to 77. Package version and
published `v0.12.0` evidence remain
unchanged at the Issue #147 boundary. Issue #148 sets Package version `0.13.0`
and completes Release metadata and current-state documentation preparation
without product behavior changes.

Issue #139 adds internal Application orchestration version `1` for all seven Root
workflows, five isolated Training Dataset operations, injected Opponent
Statistics, auxiliary artifacts, and legacy CLI parity. Issue #140 adds the
executable public facade over that boundary, lazy Root schema
validation, direct immutable options, public artifacts and execution results,
and stable boundary errors. Neither issue changes Package version, Root schemas,
examples, generated scenarios, or provenance output.

Issue #141 adds explicit Setuptools build metadata, private Package Resource
schemas with exact authoritative parity, `py.typed`, Package-Root `__version__`,
Wheel and sdist inspection, separate clean installations, external-working-
directory API smoke tests, and local/CI distribution gates. It changes no
Package version, Root schema meaning, workflow, generated scenario, legacy CLI,
or provenance output, and it does not publish an artifact.

Issue #142 adds installed CLI contract version `1`, the exact `skat-ai` Console
Script, `python -m skat_ai`, one Package-owned canonical implementation, the
Legacy Root facade, `--version`, and Wheel/sdist clean-install CLI/API parity. It
changes no Package version, Root schema, example, generated scenario, Provenance
output, or publication state.

The historical published `v0.10.0` release points to commit `b4c8738`, validates
59 deterministic generated-output scenarios, and passes 4,075 pytest tests.

The historical published `v0.9.0` release points to commit `0679760`, validates
52 deterministic generated-output scenarios, and passes 3,558 pytest tests.

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

**Published v0.17.0 Package baseline; historical published v0.16.0 preserved**

Completed implementation scope:

* all bounded `v0.8.0` opponent-intelligence workflows remain supported
* five structured flat terminal endings and two exact-public-hand continuation paths
* exact-prefix records for all six supported historical shortened terminal events
* variable-length historical decision artifacts for normal completion and all six shortened kinds
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
* private bounded Information-set Policy Search with strict flat routing, safe
  aggregate Results, same-selection PIMC and independent Immediate retrospective
  comparison, separate Historical Review and Training Dataset evaluation,
  retained-stage Provenance, CLI, four Schemas, two examples, six scenarios, and
  strict Multi-Step/Policy Comparison integration
* immutable 61-case Settlement Normative Matrix version `3` with direct,
  bounded, legacy, one supported bounded Historical Claim, and durable v1
  exclusion classifications
* private version-1 party-wide Claim contracts, exact-state preparation, bounded
  exhaustive exact AND/OR proof execution, valid-proof adjudication, and existing
  Final Settlement composition with Historical-only runtime integration
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
* stable public API contract version 1 with immutable JSON documents,
  compatibility metadata, stable errors, and legacy CLI compatibility
* internal all-seven-workflow Application orchestration and executable public
  Python facade with lazy Package Resource schema validation, direct immutable
  options, separate artifacts, and stable boundary errors
* installation-ready Wheel and sdist artifacts with synchronized schemas,
  `py.typed`, Package version metadata, and clean-install validation
* installed and module CLI entry points with canonical Package execution, Legacy
  compatibility, unchanged default Root JSON, and clean-install Public API parity
* internal field-level provenance contract version 1 with immutable sidecar
  ledgers, RFC 6901 paths, coverage and dependency audits, context-use policy,
  public redaction, and safe serialization
* internal live Position provenance with complete flat and simulated decision
  ledgers
* internal retrospective provenance across flat Position review, Historical
  Snapshots, Immediate and Search Review, and Replay Coaching
* internal Dataset, Preparation, Opponent, Profile, historical-list, and
  comparison provenance with complete non-legacy Root Result ledgers
* complete non-legacy Position and Historical Root Result provenance, including
  base Historical execution without review options
* bounded opt-in public Root Result and actual-artifact field provenance with
  immutable API values, strict Schema, installed/module/Legacy CLI parity,
  existing-helper redaction, and complete recomputed coverage
* mandatory internal all-seven-workflow source-to-final-serialization
  Provenance enforcement with exact source bindings, pre-analysis context
  validation, retained-stage authorization, and adversarial mutation rejection
* immutable internal Session and Command version-1 contracts with stable seated
  Players, Modes, phases, typed Commands, accepted revisions, Diagnostics,
  readiness, Transition Results, and deterministic serialization
* executable internal Session transition/projection version 1 with revision-zero
  creation, full accepted-Log replay, atomic application, monotonic phases,
  incremental validation, and forged-State rejection
* internal Session Request Export version 1 with immutable available/unavailable
  Results, exact ready-Retrospective Historical mapping, canonical builder round
  trip, and existing immutable Request construction without workflow execution
* internal information-safe Session Position Request export, declared-Ouvert
  public-hand capture, and immutable replay-verified pre-Play Decision Checkpoints
* immutable internal strict-prefix Undo, one-command correction, deterministic
  first-rejection suffix replay, valid partial corrected States, and Checkpoint
  lineage
* private deterministic Session Persistence version 1 with authoritative State,
  caller-supplied frozen Checkpoints, State/content fingerprints, strict resume,
  optimistic expected-fingerprint writes, canonical files, and atomic same-
  directory replacement
* stable Public Session API and Public Session File API version 1, exact
  immutable type identity, accepted-Log Decision Observation, isolated
  Checkpoint review export, automatic exact Checkpoint collection, and optional
  complete default-omitted Session Provenance
* installed/module/Legacy 12-subcommand Session CLI parity, explicit Position
  and Historical execution, phase-aware Assistant, six examples, and eight
  append-only scenarios for the published `v0.14.0` total of 85
* internal immutable Match Capture, source metadata, Media Timecode, named
  tournament-format registry, Match Participant, optional Player Statistics
  Snapshot, exact perspective, and deterministic serialization contracts
* internal immutable observed Game, chronological Play trace, free-text Decision
  commentary, linked later response, complete-card reconciliation, and derived
  evidence-summary contracts
* internal immutable 36-position Match Workspaces with fixed rotation, partial
  Games, passed deals, revisioned changes, evidence Progress, fingerprints,
  strict Resume, and optimistic atomic private persistence
* internal transport-free Match Capture Application version 1 with Card entries,
  UI-ready Position Views, exact/bounded selectable Cards, deterministic IDs,
  setup updates, automatic Player/Decision append, truncation cleanup,
  annotation editing, and Passed Deal/clear wrappers
* internal version-1 private local Match Capture Web/Protocol/CLI with exact
  browser state, all 36 positions, setup and Card forms, Play correction,
  Commentary/Response Links, Passed Deals, metadata correction, token-protected
  loopback serving, optimistic autosave, and explicit Reload
* internal Match Player Statistics Context, Preparation, and Update version `1`
  with deterministic Snapshot IDs, immutable set/clear, strict-before-Match
  eligibility, existing normalized Profile derivation, canonical eligible input,
  browser Add/Replace/Clear, and unchanged optimistic persistence
* internal Match Decision Review Preparation version `1` with partial
  Perspective-only or complete all-Player acting-own-hand reconstruction,
  information-safe before-actual-Card snapshots, Skat/Ouvert visibility, and
  relative eligible Profile bindings without policy application
* internal Match Historical Game Materialization and Training Source Collection
  version `1` with strict complete-Deal normal-completion availability,
  Match-level `played_at`, and existing unpartitioned Records without Plans,
  partitions, samples, or workflow execution
* internal Match Workspace Materialization version `1` with exactly 36 Slot
  values, `empty`/`partial`/`complete` status, reconciled Decision/Historical/
  Training/Passed/Commentary counts, and complete fixed-list construction plus
  existing aggregation and external-lot behavior
* internal Match analysis contracts with one explicit prepared-Decision
  Immediate/Search/Auto/Information-set Position execution, strict selected-mode Historical
  execution, one exact existing Application invocation, normal unavailability,
  and existing-behavior eligible relative Profile application
* private browser Match materialization with no workflow execution, counts,
  standings, unresolved lot state, and twelve round ends
* deterministic SHA-256 revision-scoped process-local reports capped at eight,
  mutation/reload/shutdown invalidation, concurrent-change discard without retry,
  and authenticated canonical Root/Historical/Training/list downloads
* internal Learning Corpus identity version `1`, Match Snapshot version `1`,
  Reference version `1`, Catalog version `1`, and Snapshot Classification version
  `1`, with immutable exact Workspace copies
* internal Learning Corpus Persistence, Store, Catalog Change, and Workspace
  Import version `1`, with fixed-root canonical files, strict Store Resume,
  valid orphan reporting, no-clobber objects, optimistic atomic Catalog Save,
  source-preserving Workspace import, and no public surface
* internal Learning Corpus Player Catalog, Player Match Observation, Platform
  Alias, Player Statistics Observation, and Statistics Selection version `1`,
  with exact Current-Snapshot-only derivation and no persistence
* internal Learning Corpus Human Evidence, Game Evidence, Commentary Evidence,
  Response Evidence, and Export version `1`, with exact Current-Snapshot-only
  human text and observed linked behavior, minimized private fields, deterministic
  fingerprints, and no persistence or public transport
* internal Learning Corpus Strategy Teacher Source, Evidence, Collection, and
  Export version `1`, with exact executed Decision Analysis Reports bound to
  Current Snapshots, one no-execution Request rebuild, validated retained Results,
  exact and semantic identities, deterministic coverage, and no persistence or
  public transport
* focused internal Information-set Strategy Teacher extension version `1`, with
  safe aggregate Result/comparison Evidence and wall-clock-normalized semantic
  identity
* internal Learning Dataset version `2` with nested contract versions `1`, exact
  four-source Current-Snapshot reconciliation, safe/skipped Decision coverage,
  separate observed behavior/Player/Teacher/Commentary/Response families,
  normalized pools, deterministic Record/content/Dataset/export identities, and
  no persistence, target, public transport, or model task
* internal Dataset-v2 partition preparation plus exact-Count cross-game Match,
  Player, Communication, Strategy, Coverage, Dataset Readiness, and supplied
  Partition Readiness summaries, with deterministic path-free exports
* internal private Learning Corpus browser/CLI with one explicit root, strict
  16-MiB uploads, optimistic import/selection, process-local exact Report sources
  and prepared existing/Tactical/Coaching artifacts, no-JavaScript forms,
  loopback security, and ten canonical downloads without derived persistence or
  public contracts

## Current high-priority limitations

* Historical records support normal completion or one of six terminal shortenings, optionally after one timed continuation kind. The approved party-wide Claim has Historical-only runtime integration, strict public diagnostic output, and downstream Review/Dataset/list/statistics support. Multiple non-terminal events, arbitrary event streams, specific future-Trick Claims, and the other durable v1 Claim exclusions are `not_supported_v1`; other end reasons remain unsupported.
* Historical opponent-statistics aggregation and rolling policy evaluation support normal completion and all six shortened terminal reasons; other end reasons remain unsupported.
* Flat Position, Session, Match Capture, and Corpus Claim entry, concession
  disputes, and broader Settlement completeness remain incomplete.
* All seven Root workflows have complete internal Root Result provenance,
  including base Historical execution. Bounded public Result and actual-artifact
  exposure is implemented. Issue #202 completes internal consumed-source,
  retained-stage, context, and final-serialization enforcement; consumed-input,
  Decision, intermediate-stage, unredacted, binding, and checkpoint attachments
  remain intentionally unavailable through the public contract.
* Evidence-constrained sampling does not infer the real deal or provide exhaustive search.
* Hidden-card inference beyond confirmed structural decision-time evidence and
  general stronger Search remain incomplete. Issue #187 defines private
  three-Trick information-set World State, actor Observation, deterministic fixed-
  Player Policy, Budget, Request, Preparation, controlled-Policy, and Result
  contracts. It preserves ordered Compatible-world selection and sampled
  duplicate weight and prevents conflicting actions for equal controlled-player
  Observations. Issue #188 adds the private bounded executor with fixed-player
  rollout, equal-Observation grouping, exhaustive canonical controlled actions,
  existing exact terminal utility and Candidate ranking, complete contingent
  controlled Policies, conservative partial/timeout Results, and invocation-
  local World and ordered-bundle memoization. Issue #189 routes strict flat
  Information-set Search and adds descriptive same-selection post-game,
  Historical Review, and Training Dataset evaluation. Issue #190 adds strict
  Multi-Step and Policy Comparison integration with per-decision Search isolation
  and unchanged `auto`. Issue #191 adds the bounded one-Decision Match/Report/
  Teacher/Dataset/Corpus path. Issue #192 adds separate Information-set Replay
  Coaching and Match Historical Information-set Review/Coaching. Issue #193 adds
  repository-local benchmark evidence and satisfies the bounded v0.17.0
  performance-evidence contract. Issue #200 accepts deterministic functional and
  structural-work evidence for v1; cross-machine latency guarantees are not v1
  requirements, while fresh supported-platform evidence remains required.
  Compatible-world Minimax evaluates the frozen selected
  sequence and aggregates one exact common prefix, but it is determinization-based
  and subject to strategy fusion. Neither method is an optimal imperfect-
  information policy proof. Overbid Null replacement selection remains outside
  both methods.
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
  Plan. The request has no algorithm field or default weights, and the CLI has no
  algorithm overrides or fallback. Its transport options and cross-workflow
  provenance opt-in do not affect assignment. Plan/CLI presentation is card-free.
  The complete nested reusable dataset retains source cards.
  Additional algorithms, algorithm overrides, fallback or partial Plans, global
  optimization, ratio guarantees, Sample- or Player-count balancing, component
  splitting, model training, and automatic evaluation remain unsupported.
* Replay Coaching has a public version-1 one-game report with information-safe
  evidence, impact, prioritization, patterns, recommendations, scope summaries,
  and isolated outcome context. Separate Historical Tactical Motif Review adds
  deterministic structural evidence without changing Coaching. Issue #195 adds
  separate exact descriptive cross-game Tactical Motif Counts and recurrence
  scopes from Current Match Snapshots. Issue #196 adds bounded deterministic
  cross-Game focus from unanimous retained complete-Search Teacher evidence.
  Tactical quality beyond that exact evidence, broader interpreted cross-game
  patterns, Player Ratings, and causal attribution remain unimplemented and are
  not v1 requirements; broader Search is post-v1.
* Immutable Live and Retrospective Session contracts plus deterministic
  Command application, replay, phase advancement, projection, incremental
  validation, readiness, canonical Retrospective Historical and information-safe
  Position Request exports, declared-Ouvert public-hand capture, and immutable
  pre-Play Decision Checkpoints are implemented. Immutable strict-prefix Undo,
  one-command correction, first-rejection suffix replay, valid partial corrected
  States, and Checkpoint lineage are also implemented. Private deterministic
  persistence now stores the authoritative State and caller-supplied frozen
  Checkpoints, strictly reconstructs and replays them, recomputes lineage, and
  uses content-fingerprint conflict checks plus canonical atomic file replacement.
  Stable Public Session and file APIs, actual-card Decision Observation, isolated
  review export, automatic Checkpoint collection, all 12 CLI subcommands,
  explicit Position/Historical execution, the Assistant, examples, and generated
  outputs are implemented. Export-only operations execute no workflow, and the
  reusable Application still has only seven Root workflows. Session GUI/browser UI,
  online-platform adapters, cloud synchronization, distributed locking,
  encryption/key management, and automatic backups remain absent and are not v1
  requirements.
* Opponent behavior and confidence remain heuristic and rule-based; behavioral evaluation does not prove stronger play.
* No learned model or model-training workflow exists.
* Match Capture contains identity/metadata, evidence-aware observed Games and
  commentary, persistent internal 36-position Workspaces, transport-free
  rapid-entry Application services, and the private local browser/Capture CLI
  with autosave. Match-bound Player Statistics editing and time-safe Profile
  preparation are implemented. Internal Decision preparation and strict
  Historical, unpartitioned Training-source, and complete fixed-list
  materialization are implemented. Explicit one-Decision and Historical
  Application execution, existing-behavior eligible Profile application,
  no-workflow materialization reports, and authenticated local downloads complete
  the functional `v0.15.0` local milestone. Reports are ephemeral and Commentary
  does not enter Coaching. Public Match API/export, Match Schema/data workflow,
  public/persisted Player Catalog, public/task-specific communication Dataset
  workflows, Dataset-v2 persistence/task builders, database/remote deployment,
  YouTube integration, and EuroSkat integration remain absent. No
  hosted website, remote browser deployment, browser extension, or online-
  platform adapter exists.
  Issue #191 adds strict one-Decision Information-set Search, safe aggregate
  diagnostics, and exact source transfer without changing report persistence or
  public boundaries.
  Issue #192 adds strict Historical Information-set Review/Coaching controls and
  safe rendering through one existing Historical Application invocation.
  Historical Reports remain ineligible for Strategy Teacher source transfer.
* Issues #171 through #179 provide private Learning Corpus source identity, exact
  Match Snapshots, closed references, Catalog entries/current selections,
  deterministic fixed-root persistence, strict Store Resume and orphan reporting,
  pure Catalog mutation, strict Workspace import, and persisted selection
  changes, plus a derived exact Player Catalog and time-safe Statistics history
  and separate minimized human Commentary/linked Response and method-bound
  Strategy Teacher Evidence exports plus one Current-only unpartitioned,
  task-neutral Learning Dataset version `2` plus Match-group-safe deterministic
  partition preparation and leakage audits, plus descriptive cross-game Match,
  Player, Communication, Strategy Teacher, Coverage, and readiness summaries,
  plus one private local workflow for strict source upload, explicit Current
  selection, exact preparation, minimized inspection, and canonical download.
  Strategy Teacher sources accept only exact
  executed Decision Analysis Reports, rebuild no-execution Requests, validate
  retained Results, and make no optimality or preferred-Teacher claim.
  Issue #191 adds focused Information-set Teacher Evidence through those exact
  sources and carries it through existing Dataset-v2 joins, Summary counts, and
  the historical Issue #179 seven-download chain without derived persistence.
  Issue #195 separately reuses the exact Tactical detector over Current Match
  Snapshots, represents every observed Decision as Evidence or an explicit skip,
  builds exact global/Player/scope/distinct-Game/distinct-Match/recurrence Counts,
  and atomically publishes two additional process-local artifacts for nine
  current authenticated downloads. Human, Strategy Teacher, and Tactical
  Evidence remain separate, and Learning Dataset version `2` is unchanged.
  Issue #196 adds a separate Coaching join and report over those exact retained
  values, atomically publishes a third prepared family, and adds a tenth current
  authenticated download. Exact Teacher Reports remain distinct, semantic
  duplicates count once per Decision consensus, only unanimous complete-Search
  below-best evidence can create repeated cross-Game focus, and every Player
  Catalog entry receives one bounded Report. Dataset version `2` remains
  unchanged, and no Coaching artifact is persisted or made public.
  Deletion, garbage collection, recovery UI, persisted aliases/assertions,
  merge/split operations, all-revision Player views, Human Evidence persistence
  and public transport, Strategy Teacher persistence and public transport,
  Dataset-v2 persistence, task builders, persisted partition artifacts, derived
  artifact persistence, automatic Report capture, Historical Report import, and
  public exposure remain absent and are not v1 requirements. Database deployment,
  evaluation, and Ratings beyond the accepted bounded contracts are not v1
  requirements; remote/cloud/collaboration and model training are post-v1.
* The product supports fixed three-player tables only; four-player tables are unconditionally out of scope.

## Next recommended action

Begin Issue #205, **Rename the complete project and public Package surface to
SkatMind**. Issues #201 through #203 close B-01 through B-03. Issue #204 applies
the exact `AGPL-3.0-only` Package boundary and closes B-04 without changing
product behavior or active Package identity. P-09 remains
`implementation_required` under B-08/#205. #206 owns installation/platform
evidence, #207 owns the final technical audit, and #208 owns the separate B-09
maintainer-UAT Gate outside the 53-row ledger. B-07 Release preparation occurs
only after #208 and remediation of accepted findings; its Issue number is not
frozen. The published functional history remains Issues #182 through #196;
Issues #197 through #199 remain audit, Release preparation, and publication
synchronization only. `v1.0.0` is not ready, and no Release title, theme, date,
tag, or publication commit is frozen.

Keep immutable imported Workspace Snapshots separate from derived artifacts.
Public Match/Corpus/Dataset-v2 surfaces, derived persistence, broader Player
Ratings and tactical truth, latency guarantees, Session GUI, database deployment,
and Historical Teacher import are not v1 requirements. Broader solver, auction,
learned-model, and hosted/remote work is post-v1.

Do not infer automatic newest selection, fuzzy Player merging, cross-revision
Decision lineage, deletion, garbage collection, Human Evidence persistence,
Strategy Teacher persistence, Historical Report import, ground-truth teacher
labels, Dataset-v2 persistence/task builders, automatic Report capture, or
public exposure from Issues #171 through #179. Those areas require separate acceptance
criteria. No production model is
planned.

## Open future topics

The approved pre-`v1.0.0`, post-`v1.0.0`, not-required, and excluded product
areas are recorded in [v1.0 scope](v1_scope.md) and frozen by the
[v1.0 scope and traceability audit](v1_0_scope_and_traceability_audit.md).
Four-player tables remain the only unconditional exclusion.

## New-thread starter instruction

When continuing in a new ChatGPT thread, provide:

1. the repository URL
2. this file
3. the current roadmap
4. the next desired milestone
5. the instruction that code and program output should remain in English while discussion can remain in German
