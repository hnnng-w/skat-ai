# Changelog

## v0.15.0

**Release theme: Local EuroSkat 36er Match capture, analysis, and exports**

### Match metadata and observed-game evidence

* Add immutable internal Match source, media-timecode, EuroSkat 36er Standard
  format, exactly-three-participant, optional Statistics Snapshot, and one
  Perspective Player contracts without platform integration (Issue #160).
* Add evidence-aware observed Games with bounded partial and exact complete Play
  traces, optional Perspective hand, original Skat and Discards, free-text
  Commentary on any Player Decision, linked later Responses, and no hidden
  completion (Issue #161).

### CLI modularization and persistent Match Workspaces

* Modularize the existing Root and Session CLI transports behind compatibility
  facades while preserving installed, module, and Legacy behavior, one Console
  Script, and all seven Root workflows (Issue #162).
* Add private persistent 36-position Workspaces with exact rotation, Passed
  Deals, immutable revisions, evidence-derived Progress, deterministic
  fingerprints, strict Resume, and optimistic atomic Save (Issue #163).

### Rapid capture services and local browser interface

* Add transport-free rapid capture services with UI-ready Position Views,
  automatic Player and Decision derivation, exact or bounded selectable Cards,
  atomic Play append, correction, annotation editing, and Passed Deal wrappers
  (Issue #164).
* Add the private Capture CLI and local no-JSON browser with one explicit
  Workspace path, packaged local assets, loopback-only token and same-origin
  protection, compare-and-swap autosave, and explicit conflict Reload (Issue
  #165).

### Match-bound Player Statistics and Profile preparation

* Add editable Match-bound Player Statistics Snapshots with deterministic IDs,
  strict `captured_at < played_at` eligibility, existing Profile derivation,
  canonical eligible preparation, and private Add, Replace, and Clear forms
  without policy application (Issue #166).

### Decision review and strict downstream materialization

* Add information-safe acting-own-hand Decision preparation without future-
  opponent leakage, strict normal-completion Historical materialization,
  unpartitioned Training source Records, and complete fixed-list construction
  and aggregation without workflow execution (Issue #167).

### Explicit Match analysis, reports, and exports

* Add explicit one-Decision Immediate, bounded Search, or Auto Position
  execution; selected strict Historical Review, Search Review, and Replay
  Coaching; and eligible relative Profile application through existing supported
  behavior (Issue #168).
* Add deterministic max-eight revision-scoped ephemeral reports, no-workflow
  Match materialization, concurrency invalidation, and private authenticated
  canonical Root, Historical, Training-source, list, and aggregation downloads
  (Issue #168).

### Information safety, determinism, and compatibility

* Keep Workspace files, process-local reports, and downloads private and
  unredacted; add no encryption, secure-storage, cloud, remote-access, backup,
  hidden-ownership inference, actual-Card optimal-label, Commentary
  interpretation, Search-world exposure, persisted report, or external-network
  claim. Capture and ordinary page rendering perform no automatic analysis.
* Preserve Python `>=3.13`, Public API contract version `1`, exactly seven Root
  workflows, one `skat-ai = skat_ai.cli:main` Console Script, Root and Session
  compatibility, all non-Package contract versions, and existing Root and
  Session input/output contracts. Existing Root and Session callers require no
  migration. Capture remains an additive private transport; Workspace
  persistence remains private internal version `1`, reports remain ephemeral,
  and no Public Match API, Match Schema, or eighth Root workflow is added.

### Validation

* Validate 63 authoritative and byte-identical Packaged Schema Resources, six
  unchanged Session examples, 85 unchanged deterministic generated outputs, and
  6,510 pytest tests on Python 3.13.
* Validate Ruff, Schema/example/generated-output checks, Wheel and sdist
  metadata, clean-install API and installed/module Root, Session, and Capture
  CLI behavior, exact `0.15.0` version output, and Legacy Capture help.

## v0.14.0

**Release theme: End-to-end Live and Retrospective Session capture**

### Immutable Session contracts and deterministic transitions

* Add independent Session and Command contract version `1` for exactly three
  stable seated Players, Live and Retrospective Modes, typed Commands, an
  authoritative accepted Command Log, linear revisions, Diagnostics, and
  Position/Historical readiness (Issue #150).
* Add deterministic revision-zero creation, full accepted-Log replay, immutable
  projection, atomic application and rejection, monotonic phase advancement,
  incremental rule and information-policy validation, and forged-State
  detection (Issue #151).

### Canonical Request export and Decision Checkpoints

* Add immutable available/unavailable canonical Historical Request export from
  exactly ready Retrospective Sessions through the existing builder and
  `RequestDocumentV1`, without workflow execution (Issue #152).
* Add information-safe Position Request export, declared-Ouvert public-hand
  capture, and frozen replay-verified pre-Play Decision Checkpoints with stable-
  to-relative Player mapping and decision metadata (Issue #153).

### Undo, correction, and Checkpoint lineage

* Add immutable strict-prefix Undo and one-command correction with deterministic
  original-suffix replay, stop-before-first-rejection behavior, valid partial
  corrected States, exact suffix reporting, and `current`, `ancestor`, `future`,
  or `diverged` Checkpoint lineage (Issue #154).

### Persistence and crash-safe Resume

* Add private Session Persistence version `1` with authoritative accepted-Log
  State, optional frozen Checkpoints, domain-separated State and content
  fingerprints, strict reconstruction and replay, recomputed lineage, and
  canonical Resume (Issue #155).
* Add optimistic expected-content-fingerprint conflict detection and durable-
  intent same-directory temporary-file writes followed by atomic replacement,
  without distributed locking, encryption, cloud synchronization, or automatic
  backup claims (Issue #155).

### Public Session API, Schema, and Provenance

* Add stable `skat_ai.api.v1.session` version `1` with exact immutable public
  type identity, strict Command parsing, transport-free in-memory operations,
  typed Results, and default-omitted complete Session Provenance (Issue #156).
* Add the strict standalone `session.schema.json` Package Resource while
  preserving Public API contract version `1`, the seven-value `WorkflowV1`, and
  every independent Session and Domain contract version (Issue #156).

### Installed Session CLI and end-to-end capture

* Add stable `skat_ai.api.v1.session.files` Save/Load, path-free Results,
  accepted-Log Decision Observation, isolated frozen-Request Checkpoint review,
  and automatic exact Checkpoint collection without automatic analysis (Issue
  #157).
* Add the separate 12-subcommand `session` parser across `skat-ai`,
  `python -m skat_ai`, and Legacy `python main.py`, with explicit
  Position/Historical execution, optimistic persistence, privacy-safe human
  output, and the strict phase-aware Assistant (Issue #157).

### Information safety, determinism, and compatibility

* Derive observed Cards only from accepted history and build review Requests from
  the frozen decision-time Request plus that Card, without later private facts,
  hidden inference, or an optimal-label claim.
* Keep private Session files unredacted and caller-controlled while omitting
  paths, fingerprints, complete private hands, and full frozen Requests from
  normal human output; fingerprints provide identity and verification, not
  confidentiality, authorship, or Confidence.
* Preserve all seven Root workflows, Root APIs and parser behavior, one Console
  Script, Public API contract version `1`, and every existing non-Package
  contract version. Existing non-Session users require no migration, and direct
  internal imports remain unsupported.

### Validation

* Validate 63 authoritative and byte-identical packaged Schemas, six strict
  Session examples, and 85 deterministic generated outputs, including eight
  appended Session scenarios while preserving the previous 77 scenarios.
* Validate Python 3.13 packaging metadata, all Root and Session CLI forms, Wheel
  and sdist clean installations, Public Session APIs, provenance and privacy
  boundaries, Ruff, and the complete pytest suite.

## v0.13.0

**Release theme: Stable API, installable tooling, and public field provenance**

### Stable public API and compatibility contracts

* Add stable API contract version `1` under `skat_ai.api.v1`, exact public
  exports, recursively immutable Request and Result documents, compatibility
  metadata, normal Result states, stable public errors and codes, and CLI Exit
  Code constants (Issue #137).
* Guarantee additive public compatibility through `v1.0.0` while keeping direct
  internal imports unsupported and Package, API, Schema, Application,
  Provenance, and Domain versions independent (Issue #137).

### Reusable Application orchestration and executable facade

* Add internal Application orchestration version `1` with immutable invocations,
  options, injected external documents, Results, and auxiliary artifacts, plus
  transport-free handlers for all seven Root workflows (Issue #139).
* Add executable public `parse_request`, `execute`, `execute_document`, and
  `serialize_result` functions with immutable workflow options and artifacts,
  mandatory input validation, default output validation, no caller file or
  terminal I/O, and stable boundary-error translation (Issue #140).

### Packaging, Schema Resources, and installed CLI

* Add explicit Setuptools PEP 517 metadata, one Wheel and one sdist, 62
  byte-identical Schemas loaded through `importlib.resources`, `py.typed`,
  Package `__version__`, artifact inspection, and separate clean-install API
  validation (Issue #141).
* Add installed CLI contract version `1`, the exact `skat-ai = skat_ai.cli:main`
  Console Script, `python -m skat_ai`, and one canonical Package-owned CLI while
  preserving Legacy `python main.py`, stable help, `--version`, errors, and Exit
  Codes (Issue #142).
* Run the same packaged-Schema, Wheel/sdist, clean-install API, installed CLI,
  and module CLI gates locally and in CI without publishing a Package or
  artifact (Issues #141 and #142).

### Field-level Provenance contracts and internal propagation

* Add internal field-Provenance contract version `1` with RFC 6901 paths,
  immutable Ledgers, Origins, Visibility, Availability, Derivation, dependency
  and temporal validation, Information Use Context, redaction, exact Coverage,
  deterministic serialization, and explicit separation from Confidence (Issue
  #138).
* Propagate retained, information-safe provenance through live Position
  Analysis, Immediate, Search, inference, Multi-Step, and Policy Comparison;
  flat retrospective review; Historical Snapshots, Search Review, and Replay
  Coaching; and Dataset, Preparation, Opponent, Profile, list, and comparison
  workflows (Issues #143 through #145).
* Complete non-legacy internal Position and Historical Result provenance so all
  seven Root workflows have complete internal Root Result Ledgers without
  rerunning established workflow stages (Issue #146).

### Public Provenance integration

* Add public field-Provenance version `1`, immutable attachments, artifacts, and
  bundles, seven explicit Root Result mappings, and the actual
  `opponent_statistics_input` artifact mapping (Issue #147).
* Add default-false Public API and `skat-ai`, module, and Legacy CLI opt-in; the
  optional Root `field_provenance` covers one complete redacted Root Result plus
  artifacts actually returned (Issue #147).
* Add strict public Schema validation, existing-helper redaction, complete
  post-redaction Coverage, and seven append-only generated-output scenarios,
  including the actual Training Dataset export artifact (Issue #147).

### Information safety, determinism, and compatibility

* Preserve unchanged Root output when Provenance is omitted. Public Provenance
  exposes no consumed-input, decision, intermediate-stage, unredacted, or full
  internal Application attachments and adds no Confidence or optimality claim.
* Preserve all API, Application, installed CLI, internal and public Provenance,
  Schema, Search, Dataset, list, Replay Coaching, Settlement, and budget-profile
  contract versions while changing only the Package version to `0.13.0`.
* Retain explicit limitations for broader end-to-end Provenance enforcement,
  Confidence integration, interactive Sessions, broader Search and Strategy
  Fusion, general and specific-trick Claims, Settlement completeness, tactical
  and cross-game Coaching, Ratings, model training, online-platform adapters,
  complete official-rule coverage, and four-player tables.

### Validation

* Validate 62 authoritative and packaged Schemas with exact filename and byte
  parity and 77 deterministic generated outputs, including seven opt-in public
  Provenance scenarios.
* Validate Wheel and sdist metadata, Package Resources, clean installations,
  Public API execution, all CLI version forms, Root JSON parity, normal
  unavailable Results, provenance opt-in, Ruff, and the complete pytest suite on
  Python 3.13.

## v0.12.0

**Release theme: Fixed-three-player historical lists and deterministic dataset preparation**

### Historical 36-position list contracts

* Add the immutable version-1 product contract for exactly three fixed stable
  participants, 36 authoritative ordered positions, and twelve rounds, with no
  participant replacement or four-player support (Issue #127).
* Represent every position as `played_game` or `passed_deal`. Passed Deals have
  no declarer or settlement, produce zero score and role counts, are not Defender
  Games, and still advance dealer rotation while fixed table places map to
  rotating historical seats (Issue #127).
* Preserve authoritative entry-array order and support optional timestamp audit
  without presenting the 36-position product boundary as a direct official-rule
  requirement.

### Aggregation, standings, and independent comparison

* Add immutable per-entry contributions, cumulative Player totals, all 36
  progression snapshots, provisional standings, and final standings with the
  existing SkWO performance components (Issue #128).
* Rank by performance points, own wins, own losses, then an exact externally
  executed lot. Preserve shared competition ranks and `lot_required` for
  unresolved ties; never generate a random lot, and let a valid lot change only
  tied ordering and ranks (Issue #128).
* Compare independent completed lists by stable Player ID, using the first list
  as reference, permitting changed table places, requiring disjoint Played Game
  IDs, and reporting `comparison - reference` deltas (Issue #129).
* Report rank changes only when both rankings are final and retain explicit
  unresolved-lot statuses. Add no progression-position comparison, combined
  totals, averages, series standings, series winner, rating, or recommendation
  (Issue #129).

### Public historical-list workflows

* Add root-selected `fixed_three_player_historical_list_input` and
  `fixed_three_player_historical_list_comparison_input` workflows with outputs
  `fixed_three_player_historical_list_summary` and
  `fixed_three_player_historical_list_comparison_summary` (Issue #130).
* Accept only `--input`, `--output`, and `--quiet`; retain explicit JSON lot
  input, complete JSON progression, twelve concise round-end CLI rows, and
  descriptive comparison CLI output (Issue #130).
* Add strict standalone schemas and three deterministic scenarios without
  changing existing list-performance inputs (Issue #130).

### Automatic Dataset preparation contracts

* Add version-1 unpartitioned source Records, explicit positive integer weights
  with no default ratio, split-safe source facts, identity/content fingerprints,
  and deterministic SHA-256 seed domains (Issue #131).
* Assign whole Records, preserve Zero-sample Records, use Record Count as the
  primary balance basis and Sample Count only as diagnostics, and return only
  `complete` or stable-reason `unavailable` Plans with no partial or fallback
  Plan (Issue #131).
* Losslessly materialize complete Plans into the existing
  `TrainingDatasetInput`, adding only `partition` while retaining the current
  Dataset, Feature Generation, and Partition Policy versions (Issue #131).

### Deterministic Known-opponent and unseen-player splits

* Add `temporal_known_opponent_v1` with required Historical Game timestamps,
  parsed-instant equal-time groups, three contiguous chronological blocks,
  exhaustive two-cut evaluation, complete Train Player coverage for Validation
  and Test, an exact Record-count objective, tie-only seed use, source-order-
  independent mapping, request-order materialization, and stable unavailable-
  reason precedence (Issue #132).
* Add `component_balanced_unseen_player_v1` with direct and transitive Player-
  connected components, Zero-sample connectivity, at least three components,
  deterministic largest-component-first ordering, non-empty greedy placement,
  strict component moves and swaps, and exact Player disjointness (Issue #133).
* Keep unseen-player optimization local to the declared move/swap neighborhood.
  Add no global-optimality or exact-ratio guarantee, Sample- or Player-count
  balancing, or component splitting (Issue #133).

### Public Dataset-preparation workflow

* Add root `training_dataset_preparation_input`, fixed mode dispatch with no
  public algorithm override, explicit seed and weights, and output
  `training_dataset_preparation_summary` (Issue #134).
* Call exactly one generator, materialize complete Plans only, treat unavailable
  Plans as successful results, and provide no fallback, automatic evaluation, or
  model training (Issue #134).
* Add strict request, Plan, and output schemas plus three deterministic
  preparation scenarios. Complete output contains a reusable nested
  `training_dataset_input` (Issue #134).

### Information safety, determinism, and compatibility

* The Dataset Partition Plan and concise CLI output contain no Historical Game
  card data. A complete JSON output intentionally contains the exact source
  Historical Game Records inside the nested reusable `training_dataset_input`.
  Only `partition` is added. Unavailable output contains no materialized
  Historical Games.
* Preserve existing workflows, manually partitioned Datasets, Dataset audit
  semantics, Search, Replay Coaching, Historical Game workflows, Opponent
  Statistics, and list-performance inputs. No migration is required when the new
  Root workflows are omitted.
* Preserve all contract, schema, Dataset, Feature Generation, Partition Policy,
  Plan, fixed-list, Search, Replay Coaching, and budget-profile versions.
* Keep explicit boundaries: no formal series or tournament management, official
  federation reports, arbitrary list sizes, participant replacement, four-player
  tables, or random lot; no globally optimal unseen-player split, exact ratio
  guarantee, Sample- or Player-count balancing, or component splitting; and no
  model training or automatic evaluation. Broader Search, claims, settlement,
  provenance, stable API, installed CLI, and interactive-session gaps remain.

### Validation

* Validate 70 deterministic generated-output scenarios, including three public
  historical-list and three automatic Dataset-preparation scenarios.
* Pass the complete pytest suite together with Ruff, input/example schema
  validation, and generated-output schema validation on Python 3.13.

## v0.11.0

**Release theme: Information-safe Replay Coaching and structured historical outcomes**

### Normative settlement and historical event chains

* Add the immutable 61-case normative settlement matrix, classifying direct,
  bounded, compatibility-only legacy, undecided, and excluded scope without
  changing adjudication or settlement behavior (Issue #118).
* Document the current structured endings, bounded defender-open-play proof,
  jack-only open-card-throw exclusion, decision-required future claims, and the
  explicitly incomplete general claim, concession, and settlement boundary.
* Support one timed non-terminal historical continuation followed by normal
  completion or one supported terminal shortening, with unchanged terminal
  adjudicators and settlement semantics (Issue #119).

### Replay Coaching evidence and prioritization

* Build decision-time evidence before attaching the observed card, retain the
  observed card only as retrospective evidence rather than ground truth, and use
  Search-first Contract-success, settlement-score, then Suit/Grand-margin impact
  ordering with an explicit Immediate-only boundary (Issue #120).
* Treat forced and aggregate-equivalent decisions as non-errors. Add at most five
  deterministic Key Decisions plus separate decision-opportunity and recorded-
  outcome Turning Points without single-card causality claims (Issue #121).

### Patterns and actionable recommendations

* Add one-game player, role, phase, and contract patterns under a two-occurrence
  convention, separating actionable from descriptive patterns (Issue #122).
* Add deterministic objective-aware decision and pattern recommendations without
  tactical, psychological, skill, statistical-significance, causal, or
  generative-text claims (Issue #122).

### Complete report and public workflow

* Compose the complete internal one-game report from retained assessment,
  prioritization, and guidance artifacts, then attach isolated Outcome Context
  with non-ranking player, role, phase, and contract summaries (Issue #123).
* Expose the opt-in `--historical-replay-coaching` historical-game workflow under
  `historical_replay_coaching_summary`, validated by
  `historical_replay_coaching.schema.json` (Issue #124).
* Reuse `--search-seed`, `--search-budget-profile`, `--samples`, and `--seed`;
  support Coaching-only output or one-pass combination with Historical Search
  Review; preserve full JSON, concise CLI, and quiet-mode behavior (Issue #124).

### Information safety, determinism, and compatibility

* Keep final outcome context outside decision-time evidence: it describes how
  the recorded game ended and does not change Coaching classification.
* Recursively exclude hands, final hidden ownership, Skat identities, discards,
  compatible-world identities and contents, private Search states, derived
  seeds, caches, branches, principal variations, ratings, and rankings from
  public Coaching output.
* Preserve all schema, Search, Replay Coaching, normative-matrix, historical,
  budget-profile, and dataset versions. Existing workflows remain unchanged when
  Replay Coaching is omitted.

### Validation

* Validate 64 deterministic generated-output scenarios, including three public
  Replay Coaching scenarios and two continuation-before-shortening scenarios.
* Pass the complete pytest suite together with Ruff, input/example schema
  validation, and generated-output schema validation on Python 3.13.

## v0.10.0

**Release theme: Information-safe bounded Search across compatible worlds**

### Search contracts and exact-world solving

* Add immutable information-safe Search views, explicit eligibility, deterministic
  node/depth/sample budgets, a separate machine-dependent timeout, and stable
  `complete`, `partial`, `timeout`, and `unavailable` result semantics (Issue
  #107).
* Add immutable perspective-neutral exact states, canonical legal-card
  generation, pure transitions, neutral terminal facts, and shared exact
  transition reuse (Issue #108).
* Add bounded Perfect-Information Minimax for exact Suit and Grand worlds with
  deterministic Alpha-Beta search, exact-only transposition reuse, and existing
  result, value, overbid, settlement, and utility semantics (Issue #109).
* Extend exact-world solving to Null, Null Hand, Null Ouvert, and Null Hand
  Ouvert when they are normal non-overbid contracts (Issue #110). Search remains
  limited to the lower of five remaining tricks and the requested budget.

### Compatible worlds and aggregate Search

* Build private compatible-world spaces from the information-safe view, count
  worlds exactly, canonically enumerate bounded complete spaces, and sample
  larger spaces as deterministic uniform IID draws with replacement (Issue
  #111). Duplicate draws retain their repeated aggregate weight.
* Evaluate one frozen selected-world sequence with exact-world Minimax and retain
  only the common completed-world prefix (Issue #112). Exhaustive completion is
  exact across all compatible worlds, sampled completion is exact only per
  selected draw, and partial or timeout values are exact only over the retained
  completed prefix.
* Exact compatible-world counts do not identify the real deal, and sampled
  ownership quality is not calibrated probability. Compatible-world Minimax is
  determinization subject to Strategy Fusion, not an optimal imperfect-
  information policy.

### Live and simulated workflow integration

* Add explicit flat `bounded_search` and Search-first `auto` routing while
  preserving Immediate expected value as the omitted default (Issue #113).
  Strict Search never falls back; auto uses Immediate only after a valid Search
  result has no recommendation.
* Integrate opt-in Search into Multi-Step local decisions and Policy Comparison
  with fresh deterministic per-decision budgets and seeds, public-state
  reconstruction, coherent execution-world separation, and privacy-safe
  diagnostics (Issue #114).
* Keep Search opt-in and information-safe across live, Multi-Step, and Policy
  Comparison workflows. Existing omitted-method workflows require no migration.

### Retrospective review and evaluation

* Add flat post-game Search with an independently executed Immediate baseline,
  actual-card aggregate ranking, and Search-versus-Immediate comparison (Issue
  #115).
* Add information-safe Historical Search Review with private stable decision
  seeds and reconciled status, coverage, agreement, quality, and performance
  summaries (Issue #115).
* Add deterministic bounded-Search dataset evaluation over selected decision
  prefixes while preserving zero-decision records and existing dataset,
  feature, target, and schema versions (Issue #115).

### Budgets, quality, determinism, and performance

* Add the immutable `interactive_v1`, `historical_review_v1`, and
  `evaluation_v1` named work-budget profiles (Issue #115).
* Add Search-versus-Immediate quality gates, independent exhaustive Suit, Grand,
  and Null strict-improvement fixtures, and 32/64/128-draw convergence evidence
  against exhaustive references (Issue #115).
* Add the deterministic version-1 Suit/Grand/Null benchmark corpus and measured
  local reference performance with node and world diagnostics (Issue #115).
  Timings are reference measurements, not cross-machine guarantees, and
  wall-clock timeout activation is machine-dependent.
* Search remains bounded late-game determinization, not complete-contract Search.
  Overbid Null remains outside normal Search when no external replacement is
  available. No machine-learning model exists, four-player tables remain
  excluded, and complete official rule coverage is not claimed.

### Validation

* Validate 59 deterministic generated-output scenarios without changing schema,
  example, or generated-scenario versions.
* Pass 4,075 pytest tests together with Ruff, input/example schema validation,
  and generated-output schema validation on Python 3.13.

## v0.9.0

**Release theme: Structured game endings and coherent hidden information**

### Structured game-end handling

* Add structured declarer concession, defender concession, unanimously accepted
  declarer-card exposure, bounded exact defender open play, and open-card
  throwing for Suit, Grand, and all four Null variants (Issues #86 through #92).
* Continue play after rejected declarer-card exposure with the exact public
  declarer hand, or after defender open play with the exposing defender's exact
  returned public hand, without adjudication or settlement.
* Preserve preexisting results where required, enforce mandatory declaration
  levels and supported overbid behavior, and serialize privacy-safe proof and
  event summaries without exposing unrelated hands.
* Bound exact defender-open-play proof to five unresolved tricks. Open-card
  throwing uses bounded jack-only theoretical Schwarz exclusion; unsupported
  general claims and specific-trick claims remain outside this release.

### Historical shortened games

* Add versioned terminal events for declarer concession, defender concession,
  unanimously accepted declarer-card exposure, bounded defender open play, and
  open-card throwing (Issues #93 through #101).
* Replay exact legal prefixes, including an optional incomplete final trick,
  reconstruct exact remaining hands, preserve stable player identities, and
  round-trip canonical privacy-safe records and summaries.
* Add timed non-terminal defender-open-play and declarer-card-exposure
  continuations with exact public-hand visibility only after the event boundary.
* Keep continuations non-terminal. Version 1 supports at most one non-terminal
  event; continuation followed by a shortened terminal end remains unsupported,
  and terminal-event choices never become training targets.

### Decision, dataset, and opponent workflows

* Derive snapshot, review, and training-sample counts from the actual played-card
  count, including valid zero-decision and zero-sample shortened records.
* Preserve information-safe historical review, feature-generation version `1`,
  and target `actual_card_played`; no terminal-event target or event-specific
  profile field or signal is added.
* Apply existing dataset partition audits to shortened records while preserving
  strict temporal and partition safety.
* Aggregate one game of opponent-statistics weight per supported record and use
  actual decision counts plus participant-based target coverage in rolling
  opponent-policy evaluation.

### Ouvert-aware recommendation

* Apply declared-Ouvert public-hand constraints and exact declarer-hand
  reconciliation to live and historical Suit, Grand, Null Ouvert, and Null Hand
  Ouvert decisions (Issue #102).
* Reuse the exact public hand in Immediate Analysis, supported Multi-Step paths,
  Policy Comparison, flat review, and Historical Review, including coexistence
  with continuation public hands and information-safe matador evidence.
* Keep declaration and settlement rules unchanged. No Ouvert-specific tactical
  policy or perfect-information solver is added; current policies remain
  heuristic.

### Coherent hidden worlds

* Sample one immutable hidden execution root per Multi-Step path, preserve
  ownership through owner-aware transitions, and keep one fixed hypothetical
  skat (Issue #103).
* Give Policy Comparison paths independent copies of one shared root and use
  separated deterministic random streams for root sampling, opponent actions,
  and expected-value samples.
* Keep candidate selection on information-safe local state and serialize only
  privacy-safe coherence summaries. One coherent world is one hypothetical
  sample, not proof of the real deal; Immediate Analysis remains independently
  sampled and unsupported Multi-Step phases remain unchanged.

### Evidence-constrained hidden-card inference

* Constrain Suit, Grand, and Null hidden ownership using exact public ownership,
  legitimately known skat, attributed public play, and confirmed legal failure
  to follow the effective category (Issue #104).
* Count exact compatible labeled worlds and ownership marginals, then sample
  deterministic uniform compatible assignments with dynamic programming.
* Integrate common compatible worlds into Immediate Analysis, coherent roots
  into Multi-Step and Policy Comparison, and decision-time-safe evidence into
  Historical Review with strict privacy-safe output.
* Report `confirmed`, `high`, `medium`, and `low` concentration labels. Ownership
  estimates are conditional on uniformly weighted structurally compatible
  labeled assignments; confidence is not calibrated real-deal probability.
* Only confirmed structural evidence creates hard constraints. No behavioral,
  profile-weighted, Bayesian, or learned ownership model is added.

### Validation

* Validate 52 deterministic generated-output scenarios.
* Pass 3,558 pytest tests together with Ruff, input/example schema validation,
  and generated-output schema validation.

## v0.8.0

**Release theme: Explainable and time-safe opponent intelligence**

### Opponent statistics and profiles

* Add versioned external opponent-statistics records with stable player identity, required source provenance, all eight supported percentage statistics, and deterministic normalization to existing profile-rate semantics.
* Preserve optional exact historical role, win, Hand, and contract counts while keeping rounded external percentages distinguishable from exact evidence.
* Derive overall, declarer, and defender evidence scopes with heuristic confidence bands and explainable signals, classifications, reason codes, and preset recommendations.
* Distinguish actionable profile results from informational low-confidence, neutral, or insufficient-data results; profiles remain deterministic and rule-based rather than learned.

### Live and historical application

* Add explicit live left/right bindings by stable player ID, with independent relative-side behavior and actionable-only profile application.
* Preserve manual profile and explicit policy precedence over external profile presets.
* Add automatic historical participant matching with strict `captured_at < played_at` temporal safety and per-decision relative-side remapping.
* Preserve historical replay, settlement, deterministic seeds, and decision-time information boundaries when profiles are applied.

### Historical aggregation and export

* Aggregate exact opponent statistics from timestamped `training_dataset_input` games using canonical partition selection and an optional strict cutoff.
* Derive declarer and defender wins from final settlement and preserve exact role, win, Hand, and contract counts; both defenders receive a defender win when their side wins.
* Add versioned `historical_games` provenance and reusable standalone opponent-statistics export compatible with live bindings and time-safe historical matching.

### Behavioral evaluation

* Add rolling game-start as-of profiles using disjoint source and evaluation partition names and the fixed `simple_lowest` baseline.
* Evaluate the acting player's own observed card choice against ordered policy-equivalent preferred-card candidates.
* Report preferred-card and exact-card match metrics, actionable-only paired comparisons, coverage, and bounded breakdowns.
* Keep behavioral matching explicitly separate from strategic-quality, recommendation-quality, or optimal-play evaluation.

### Dataset partition policies

* Add optional `known_opponent` and `unseen_player` metadata while preserving backward compatibility for datasets without declared partition intent.
* Audit exact stable-player membership, pairwise and three-way overlap, and directed known-opponent coverage deterministically.
* Enforce strict player-disjoint partitions for declared unseen-player datasets while retaining rolling policy evaluation as a known-opponent workflow.

### Project scope and documentation

* Synchronize release-state documentation and record the approved pre-`v1.0.0`, post-`v1.0.0`, not-required, and unconditionally excluded product areas.
* Preserve the limitations of normal-play-only historical records, simplified claims and concessions, incomplete settlement nuance, heuristic opponent behavior, and bounded simulation and input interfaces.

### Validation

* Validate 33 deterministic generated-output scenarios.
* Pass 2,640 pytest tests together with Ruff, input/example schema validation, and generated-output schema validation.

## v0.7.0

**Release theme: Rules confidence and information-safe historical workflows**

### Rules and settlement

* Canonicalize Suit and Grand declaration dependencies and reject explicit contradictions while preserving the independent Null variants.
* Enforce official matador bounds of `1..11` for Suit and `1..4` for Grand.
* Align fixed three-player standings ties with SkWO 6.3.1 by using shared ranks for unresolved ties and optional externally executed lot order.
* Add bounded post-game settlement for impossible Null declarations while preserving the original Null contract and requiring an external Suit or Grand replacement selection.

### Historical-game workflows

* Add versioned complete normal-play historical-game records with full-deal, pickup or Hand, discard, ownership, play-order, follow-rule, winner, point, game-value, overbid, and settlement validation.
* Add 30 chronological information-safe pre-play snapshots without future-play, hidden-hand, or final-result leakage.
* Add bounded review of all 30 historical decisions through the existing immediate recommendation and post-game review logic, including deterministic seeds and reconciled game and player summaries.

### Training and evaluation data

* Add versioned training and evaluation dataset records with explicit provenance and `train`, `validation`, and `test` partitions.
* Deterministically derive 30 identity-safe decision samples per normal-play historical game using `actual_card_played` as the version-1 target.
* Reject duplicate record, game, and source identities and cross-partition game or source leakage.

### Project scope and documentation

* Establish the official November 2022 ISkO/SkWO publication as the normative rules source.
* Add an authoritative requirements traceability matrix and testable `v1.0.0` scope and completion gates.
* Synchronize release-state, roadmap, handoff, schema-validation, and user documentation for the `v0.7.0` baseline.

### Validation

* Validate 27 deterministic generated-output scenarios.
* Pass 2,302 pytest tests together with Ruff, input/example schema validation, and generated-output schema validation.

## v0.6.0

### List-aware review workflows

* Add fixed three-player list standings output for explicit list standings input.
* Expand list-performance examples and generated-output validation across aggregated totals, normalized contributions, local analysis results, and standings workflows.
* Improve post-game review examples and explanation coverage for mistakes, acceptable alternatives, Null objective reviews, and defender-perspective reviews.

### Opponent policy and settlement coverage

* Add controlled coverage for left/right opponent policy effects in immediate and multi-step paths.
* Use profile confidence in bounded opponent-policy behavior while preserving explicit policy override precedence.
* Audit settlement and overbid edge-case coverage, including supported Suit/Grand overbid settlement behavior.

## v0.5.0

### Late-game and history-heavy inputs

* Allow zero opponent hand sizes for late-game public inputs.
* Enforce stricter live completed-trick `winner_role` verifiability from concrete trick facts.
* Expand conservative matador inference from completed-trick ownership when `cards`, ordered `players`, and concrete declarer identity make ownership safe.

### Review wording and validation

* Add focused late-game and history-heavy workflow coverage, including generated-output validation.
* Improve objective-aware post-game review CLI wording, especially for Null contract-objective reviews.
* Expand regression coverage around late-game inputs, live winner metadata, matador inference, examples, CLI output, and post-game review behavior.

## v0.4.0

### Documentation and release-state updates

* Refresh roadmap and project handoff direction for the completed `v0.4.0` usability milestone.
* Add curated workflow walkthroughs for common CLI usage, JSON output, quiet automation, Multi-Step, policy comparison, side-specific opponent policies, post-game review, and schema validation.
* Clean stale metadata, player-profile, matador, and input/output documentation wording so docs match current behavior.
* Remove stale tracked generated output artifacts before release preparation.

### CLI usability and validation

* Improve CLI help text and command discoverability.
* Add optional `--quiet` mode for automation-friendly JSON-output runs.
* Expand generated-output validation for representative user-facing CLI workflows.
* Fix CLI `--comparison-only` behavior and sample-count maximum validation issues.

## v0.3.0

### Bug fixes

* Use Null contract-objective utility for live recommendations and expected-value ranking.
* Prevent advanced states from double-counting completed-trick points.
* Validate completed-trick ownership from cards, player order, game type, and concrete declarer identity when derivable.

### Validation and schemas

* Align runtime validation with documented schema bounds and public input shapes.
* Support `known_to_declarer` Skat visibility consistently in runtime validation, schemas, and output metadata.
* Reject malformed or out-of-bounds public inputs earlier and consistently.

### CLI and examples

* Return non-zero exit codes for invalid CLI usage and expected runtime/input failures.
* Send expected errors to `stderr`.
* Restore a valid documented default `python main.py` quick-start input.

### Documentation

* Document Null objective ranking, reusable final-state point representation, CLI exit codes, `known_to_declarer`, completed-trick ownership validation, and runtime validation parity.

### Internal compatibility

* Preserve public point fields as card-point metrics while using objective utility internally for Null ranking.
* Preserve explicit point fields as reusable state fields separate from completed-trick point contributions.
