# SkatMind

![Check](https://github.com/hnnng-w/skatmind/actions/workflows/check.yml/badge.svg)

SkatMind is a local Python-based analysis, simulation, and historical-data engine
for Skat positions and supported complete or shortened historical games.

It evaluates legal card choices, estimates expected point swings, recommends cards, tracks game state, simulates multi-step play, and supports post-game review workflows. The project focuses on rule-based and probability-based analysis rather than machine learning.

SkatMind is experimental. It includes bounded late-game Perfect-Information
Minimax for exact worlds, but it is not a general hidden-information or complete-
contract solver, a full official tournament system, or a replacement for
official Skat rules arbitration.

## Features

### Core analysis

* JSON-based Skat position analysis
* Legal-card detection
* Card-point calculation
* Trump and trick-winner logic
* Immediate trick simulation
* Configured opponent response policies for immediate analysis and multi-step candidate completion
* Expected point swing calculation
* Card recommendations
* Optional bounded compatible-world Minimax recommendations for eligible late live positions
* Strict Search and Search-first `auto` routing with explicit Immediate fallback metadata
* Flat post-game bounded Search with an independently executed Immediate baseline
* Strict three-Trick flat `information_set_search` with exact settings, safe aggregate output, and no Live fallback
* Descriptive same-selection PIMC and independent Immediate comparison for Information-set Post-game Review
* JSON output for regression-friendly analysis

### Simulation and policy comparison

* Multi-step simulation
* Configurable card-selection policies
* Policy comparison across card-selection strategies
* Opt-in bounded Search, `auto`, or strict `information_set_search` at every Multi-Step local decision
* Exact coverage of all nine concrete canonical Multi-Step phases, including
  same-World completion when the local Card is already in the current Trick
* Optional five-policy comparison with one configured Search method appended last
* Safe nested Information-set Search Decisions and 16-field compact Policy Comparison diagnostics
* Declared-Ouvert exact public-hand ownership in Immediate Analysis, all concrete canonical Multi-Step paths, and Policy Comparison
* Opponent lead and response simulation
* Opponent policy presets
* Optional profile-based policy presets
* Separate left/right opponent policy settings
* Left/right opponent policy CLI overrides
* Shared opponent-policy precedence for immediate and multi-step paths
* Basic defender cooperation heuristics
* Exact evidence-constrained hidden-card worlds from confirmed public failures to follow
* Exact compatible-world counts and ownership marginals with privacy-safe confidence summaries

### Game history, scoring, and settlement

* Completed-trick structure validation
* Completed-trick sequence validation
* Completed-trick rule-winner validation
* Explicit and completed-trick point summaries
* Score and game-result summaries
* Game declaration and game-value summaries
* Automatic matador inference from known declarer-card context where possible
* Structured concealed or verbal declarer-concession adjudication under ISkO 4.4.1 and 4.4.2
* Structured defender-concession adjudication under ISkO 4.4.3
* Unanimously accepted declarer-card-exposure adjudication under ISkO 4.4.4
* Continued play with the exact public declarer hand after rejected shortening under ISkO 4.4.4
* Bounded exact defender open-play adjudication under ISkO 4.4.5 for up to five unresolved tricks
* Continued play with the exposing defender's exact returned public hand under ISkO 4.4.5 and 4.1.6
* Internal Settlement Normative Matrix version `3` with 61 preserved cases, one
  supported bounded Retrospective party-wide Claim, private version-1 structured
  Claim/Evidence/Proof contracts, bounded exhaustive exact proof execution,
  valid-proof adjudication, and Historical-only existing Final Settlement reuse,
  plus durable v1 exclusions
* Legacy claim/concession remaining-point assignment
* Adjusted game-result summaries
* Final single-game settlement summaries
* Supported Suit/Grand overbid settlement
* Bounded impossible Null settlement with an externally supplied Suit or Grand replacement
* Partial fixed-three-player SkWO-style performance rating
* SkWO 6.3.1 shared ranks for unresolved standings ties and optional external lot order
* Public fixed-three-player historical 36-position list aggregation with Played Games, Passed Deals, progression, final standings, and optional external lot application
* Compact comparison of two or more independent completed lists with one reference, final deltas, and resolved-only rank movement
* Versioned complete historical-game records for normal play and six supported shortened terminal events, including the Historical-only party-wide Claim
* Two timed non-terminal historical continuation events with exact public-hand boundaries
* Bounded historical chains with at most one continuation followed by normal completion or one supported terminal shortening
* Full deal, pickup/discard, Hand, ownership, play-order, and follow-rule validation
* Derived historical trick winners, points, game value, overbid, and settlement
* Optional information-safe pre-play snapshots for every actual play in supported historical endings
* Optional decision-time review of those actual historical plays through the existing immediate recommendation logic
* Optional Historical Search Review with per-decision and aggregate Search-versus-Immediate comparisons
* Optional complete Historical Replay Coaching Report with Key Decisions, Turning Points, one-game patterns, actionable recommendations, scope summaries, and separately attached retrospective outcome context
* Separate Historical Information-set Replay Coaching with complete Information-set Candidates as primary evidence, diagnostic PIMC/Immediate baselines, no fallback, and explicit not-assessable coverage
* Separate deterministic Historical Tactical Motif Review with decision-time facts, after-play and after-Trick evidence, exact structural taxonomy, safe counts, and no quality, signaling, communication, or causal claim
* Separate Current-Match-Snapshot-only Learning Corpus Tactical Motif Evidence with exact Evidence-or-skip coverage and descriptive cross-game recurrence Counts without trait, quality, rate, significance, or causal claims
* Private deterministic Tactical Cross-game Coaching from exact Tactical/Teacher joins, complete-Search-only consensus, repeated cross-Game thresholds, and bounded fixed Guidance without a ground-truth, Player-rating, or causal claim
* Versioned training/evaluation dataset records with provenance and explicit train, validation, and test partitions
* Deterministic bounded-Search dataset evaluation over selected decision prefixes
* Optional known-opponent or unseen-player partition policies with deterministic stable-player overlap audits
* Deterministic information-safe samples using the legal historical actual card as the version-1 target
* Versioned external opponent-statistics records with required provenance
* Percentage-point validation and deterministic normalization to existing profile-rate semantics
* Versioned explainable rule-based profile derivation with scoped heuristic confidence
* Exact reusable opponent-statistics aggregation from selected timestamped historical games
* Standalone historical-statistics export compatible with existing live and historical profile loaders
* Strict time-safe historical profile application by stable participant identity
* Rolling known-opponent policy evaluation against the fixed `simple_lowest` baseline

### Information policy

* Live-vs-post-game information enforcement
* Rejection of post-game-only information in live-decision mode
* Information policy summary output
* Rule-authorized all-player public-hand constraints for bounded exposure continuations
* Rule-authorized exact current declarer hands for declared Ouvert
* Private exact defender-open-play proof evidence with only the exposing defender's cards emitted
* Internal version-1 field-level provenance language with immutable sidecar
  ledgers, RFC 6901 paths, deterministic coverage auditing, dependency and
  temporal validation, Information Use Context, public redaction, and safe
  serialization
* Internal version-1 live Position provenance with complete pre-selection
  decision ledgers and Immediate, Search, inference, Multi-Step, Policy
  Comparison propagation
* Internal version-1 retrospective provenance across flat post-game Position
  Analysis, Historical Snapshots, Immediate, bounded and Information-set Search
  Review, and both Replay Coaching families
* Internal version-1 Dataset, Preparation, Opponent, Profile, historical-list,
  and independent-list comparison provenance with complete non-legacy Root
  Result ledgers
* Internal version-1 complete Position and Historical Result provenance covering
  Declaration, Value, Overbid, scoring, Results, Settlement, Performance, lists,
  endings, continuations, canonical Historical records, replay, and points
* Mandatory internal version-1 exact Request/effective-option/external-source,
  pre-analysis context, retained-stage authorization, and final Result/artifact
  serialization enforcement for all seven Root workflows
* Opt-in public field-provenance version `1` for one complete redacted Root Result
  plus artifacts actually returned, with recomputed exact-document coverage and
  no consumed-input, decision, intermediate-stage, or unredacted exposure

### Post-game review

* Optional `actual_card_played` input
* Validation that the actual card is valid and legal
* Comparison between actual card and recommended card
* Expected point swing difference
* Decision quality classification:

  * `not_available`
  * `optimal`
  * `acceptable`
  * `suboptimal`
  * `mistake`
* Machine-readable decision factors
* Human-readable decision explanations
* Recommendation gap details:

  * `actual_card_rank`
  * `recommended_card_rank`
  * `candidate_count`
  * `better_card_count`
* Human-readable CLI output for post-game review summaries
* Complete historical-game quality counts and three reconciled player summaries

### Validation

* Input JSON schema validation
* Output JSON schema validation
* Generated-output schema validation for selected examples
* Packaged-schema byte parity and Wheel/sdist clean-install API/CLI validation
* Pytest regression coverage
* Ruff checks
* Combined project check script

### Public Python API contracts

* Stable API contract version `1` under `skatmind.api.v1`
* Exact seven-value Root `WorkflowV1` contract
* Recursively immutable JSON `RequestDocumentV1` and `ResultDocumentV1` wrappers
* Immutable `ExecutionOptionsV1`, compatibility policy, and API-version metadata
* Stable public errors, error codes, serialization, and CLI Exit Code constants
* Minimal Package-Root exports: `api`, `errors`, and `__version__`
* Internal Application orchestration version `1` with immutable invocations,
  options, results, external documents, and auxiliary artifacts
* Generic no-I/O dispatch for all seven Root workflows, including six isolated
  Training Dataset operations and optional injected Opponent Statistics
* Executable `parse_request`, `execute`, `execute_document`, and
  `serialize_result` facade functions for all seven workflows
* Lazy Package Resource Root input, Root output, and artifact schema validation
  with stable public boundary errors
* Immutable public field-provenance attachments, artifacts, and bundles with
  seven explicit Result mappings and default-false execution opt-in
* Setuptools Wheel and sdist builds with `py.typed`, packaged byte-identical JSON
  Schemas, and clean-install validation

### End-to-end Live and Retrospective Session capture

* Internal Session and Command contract version `1`
* Exactly three stable Players with canonical forehand, middlehand, and rearhand seats
* Live and Retrospective Capture Modes with explicit one-way promotion
* Immutable typed incremental Commands and an authoritative accepted Command Log
* Linear revisions, validation Diagnostics, Position/Historical export readiness,
  and applied/rejected/revision-conflict Result semantics
* Deterministic internal serialization with no generated IDs or timestamps
* Internal transition engine and projection version `1` with canonical revision-
  zero creation, full accepted-Log replay, atomic Command application, monotonic
  phase advancement, and forged-State detection
* Incremental Deal, Declaration, Skat/Discard, Play, trick, continuation,
  Game-end, promotion, information-policy, and readiness validation
* Internal Session Request Export version `1` with normal available/unavailable
  Results and exact one-replay Historical readiness gating
* Exact Retrospective projection mapping through the existing Historical builder,
  canonical serialization and rebuild, and immutable `RequestDocumentV1`
* Internal Position Export Options version `1` and information-safe one-replay
  export to the existing flat Position Analysis `RequestDocumentV1`
* Stable-to-relative Player mapping, decision-visible Matadors, legitimate Skat
  visibility, and declared-Ouvert or continuation public-hand mapping
* Appended `set_public_hand` Command for the exact current declared-Ouvert
  Declarer hand, with owner-aware coexistence and shrinking
* Immutable replay-verified pre-Play Decision Checkpoint version `1` with source
  revision, actor, seat, decision/trick/play indexes, relative map, and frozen
  Position Request
* Internal Session History Edit version `1` with immutable strict-prefix Undo,
  exact removed-suffix reporting, and Mode, phase, Validation, and readiness
  recomputation
* Immutable one-command correction with deterministic original-suffix replay,
  normal partial corrected States at the first rejected later Command, and exact
  replayed/discarded record reporting
* Derived Checkpoint Lineage version `1` with `current`, `ancestor`, `future`, and
  `diverged` relationships from exact accepted-prefix and Position Request
  reconstruction
* Internal Session Persistence version `1` with an authoritative accepted-Log
  State, optional caller-supplied frozen Decision Checkpoints, and recomputed
  lineage on resume
* Domain-separated compact canonical SHA-256 State and complete-content
  fingerprints, including distinct identity for corrected equal-revision Logs
* Strict private-document reconstruction, accepted-Log replay, canonical round
  trips, and State/content fingerprint verification
* Optimistic expected-content-fingerprint `saved`, `unchanged`, and `conflict`
  results plus canonical pretty UTF-8/LF save bytes and same-directory atomic
  replacement
* Stable in-memory `skatmind.api.v1.session` version-1 namespace with exact
  immutable Session type identity, strict public Command parsing, one-call
  wrappers for twelve operations, and one immutable Result envelope
* Default-omitted, opt-in Session Provenance version `1` with complete exact-
  value coverage, engine-private redaction, and recomputed coverage
* Strict standalone Draft 2020-12 `session.schema.json` mirrored into Package
  Resources, bringing the active authoritative and packaged Schema count to 63
* Stable `skatmind.api.v1.session.files` version `1` with path-free Save/Load
  Results, strict resume, expected-content-fingerprint compare-and-swap, and
  atomic same-directory replacement
* Immutable Decision Observation version `1` with explicit observed, pending,
  future, diverged, and ended-without-play statuses derived from accepted history
* Frozen-request-plus-observed-Card Checkpoint review export with no later private
  facts and no interpretation of the Card as an optimal label
* Automatic exact Checkpoint collection before accepted local Plays and at
  Position-ready resulting States, with equality deduplication and no automatic
  analysis
* Installed/module/Legacy `session` CLI parity with 12 subcommands for creation,
  status, mutation, history editing, Checkpoints, export, explicit Position and
  Historical execution, review, and the phase-aware Assistant
* Six strict Session examples and eight append-only generated scenarios, bringing
  the `v0.14.0` Package total to 85 while preserving the previous 77

The stable Python Session API exposes creation, Command application, Undo,
correction, both Request exports, Checkpoint construction/classification,
persistence-document construction/resume, Decision Observation, and Checkpoint
review export. Stable public file Save/Load and the end-to-end Session CLI are
implemented. Export-only operations still do not execute workflows; explicit
`analyze`, `review`, and `finalize` invoke the existing Application once when an
export is available. No Session Root workflow exists. Session State itself still
contains no filesystem path or fingerprint; those values belong to the private
persistence envelope and caller-supplied file transport. These capabilities were
introduced in the historical published `v0.14.0` Release and remain part of the
current published baseline. See
[Public Session API version 1](docs/public_session_api_v1.md),
[Session provenance](docs/session_provenance.md),
[Session Decision observations](docs/session_decision_observations.md),
[Session CLI and end-to-end capture](docs/session_cli_and_end_to_end_capture.md),
[Interactive session contracts](docs/interactive_session_contracts.md),
[Incremental Session transitions](docs/incremental_session_transitions.md),
[Retrospective Session export](docs/retrospective_session_export.md),
[Session Position export and Decision checkpoints](docs/live_session_position_export.md),
[Session Undo, correction, and Checkpoint lineage](docs/session_undo_and_correction.md),
and [Session persistence and resume](docs/session_persistence_and_resume.md).

Session persistence files are private local working data. They may contain
complete retrospective cards and local-private Checkpoint Position Requests,
receive no public redaction, and make no encryption or access-control claim.
Their fingerprints provide deterministic content identity and verification, not
confidentiality or authenticated authorship.

### Local Match Capture interface

The published `v0.15.0` milestone provides usable manual post-game capture
of one
EuroSkat 36er Standard Match from a video source. Issue #160 adds internal
immutable version-1 Match source, media-timecode, tournament-format,
participant, optional Player-statistics snapshot, identity, and perspective
contracts. `euroskat_36_standard_v1` is the only executable format definition
and requires exactly three Players and 36 Games.

The game platform and media source are separate: a Match may have game platform
`EuroSkat` and descriptive source kind `youtube_video`. The source stores the
caller URL, title, optional channel, and optional Match bounds without any
YouTube or EuroSkat integration. The perspective is one observed Match Player,
not the application user. Issue #161 adds internal immutable observed-Game,
chronological Play-trace, free-text Decision commentary, linked later-response,
and derived evidence-summary contracts. Partial traces validate only provable
ownership and legal play; complete traces reconstruct all playable hands and
replay all 30 Decisions. Missing original Skat and Discards remain null.

Issue #163 adds internal persistent EuroSkat 36er Standard Workspaces with
exactly 36 authoritative Slots, existing Dealer and historical-seat rotation,
partial observed Games, explicit passed deals, immutable revisioned changes,
evidence-derived Progress, domain-separated Workspace/content fingerprints,
strict Resume, and optimistic same-directory atomic Save. Structural `complete`
means all Slots are classified, not that all evidence is complete.

Issue #164 adds internal transport-free rapid-entry Application services over an
already loaded Workspace. They derive a UI-ready Position View, rotation,
current Trick, next Player, Play counts, Evidence Summary, and Progress; start
Games with deterministic IDs; update setup evidence; derive Players and Decision
indexes while appending one or more Cards atomically; truncate mistaken Play
suffixes; reconcile free-text commentary and later-response links; and wrap
passed-deal and clear operations. Selectable Cards are exact legal choices only
for an exactly known current perspective hand and otherwise bounded observation
candidates that exclude only proven-unavailable Cards.

Issue #165 adds internal Match Capture Web, Web Protocol, and Capture CLI
version `1`. Start the private local browser through any supported CLI form:

```powershell
skatmind capture --workspace MATCH.json
python -m skatmind capture --workspace MATCH.json
python main.py capture --workspace MATCH.json
```

The server requires one explicit Workspace file, binds only to `127.0.0.1`,
strictly resumes a valid existing file, or presents a no-JSON Match-creation
form while the target is absent. The browser provides the complete 36-position
overview, setup Card selectors and Declaration forms, exact or bounded Play
palettes, automatic acting-Player and Decision derivation, atomic Card batches,
Play truncation, Commentary and Response Links on any Player, Passed Deals,
clearing, metadata correction, and explicit conflict Reload.

Issue #166 adds Add, Replace, and Clear forms for one optional Match-bound Player
Statistics Snapshot per participant. Browser-created records reuse the existing
Opponent Statistics validator and are limited to manual entry or online-platform
provenance; loaded historical aggregations remain read-only except for clear or
replacement. The browser presents source percentages and optional exact Counts,
the existing normalized Profile and derivation, and strict temporal eligibility.
Only `captured_at < played_at` enters canonical Match-wide preparation. Missing
Match time and equal or later captures remain descriptive.

Issue #167 adds an internal evidence-aware review and materialization layer.
Partial traces can prepare only Decisions whose acting own hand is exact; a
complete legal trace can prepare all 30 acting own hands without exposing future
opponent ownership. The actual Card remains a retrospective attachment after the
Decision-time state, and Skat and declared-Ouvert visibility retain existing
Historical semantics. Eligible Match-bound Profiles are bound to relative left
and right opponents without applying a Profile or Policy during preparation.

Strict Historical materialization remains narrower: it requires one complete
legal trace, original Skat, exact Discards, and a reconstructable complete Deal,
and creates only an existing normal-completion Historical Game. Available Games
can become unpartitioned Training source Records. A fully classified Workspace
can become the existing fixed-three-player 36-position list and aggregation only
when every played position is strictly materializable; Passed Deals remain
Passed Deals, external-lot behavior is unchanged, and Commentary/Response Links
remain Workspace sidecars. Materialized Games and Passed Deals conservatively
use Match-level `played_at`, never media-offset-derived absolute times. No
analysis, Dataset partition/sample generation, or Root workflow executes.

Issue #168 explicitly connects these prepared values to the private browser.
One selected prepared Decision can execute the existing Position Application
once through Immediate, bounded Search, or `auto`, even when only a partial trace
supports that Decision. The actual Card remains retrospective evidence, not an
optimal label. Eligible Profile bindings exclude the actor and enter only the
existing side-specific Application behavior; disabled or nonactionable Profiles
change no policy, and Profiles do not alter Search.

One strictly materializable Game can execute the existing Historical Application
once with selected Decision Snapshots, Immediate Review, Search Review, and/or
Replay Coaching. Historical Profile application is limited to enabled existing
Immediate Review behavior; it is not claimed for Search or Coaching. A separate
Match-wide materialization action executes no workflow and presents counts,
standings, unresolved lot state, and all twelve round ends.

Every accepted mutation uses the exact Workspace revision and retained content
fingerprint for one compare-and-swap atomic Save before success is shown.
Unchanged and revision-conflict operations do not write. Persistence conflicts
perform no retry, merge, or hidden Reload. A random startup token, HttpOnly
Strict cookie, same-origin mutation checks, Host validation, restrictive browser
headers, a one-MiB request cap, and allowlisted packaged local assets protect the
loopback transport. No external network request is made.

Workspace files, ephemeral analysis reports, and downloaded artifacts are
private local data and receive no public redaction. Reports use deterministic
SHA-256 IDs, are current-revision process memory only, retain at most eight
entries, and are cleared by applied mutations, Reload, or server shutdown.
Concurrent Workspace changes discard stale analysis without retry.
Authenticated loopback downloads expose exact Root Results and canonical
materialization, Historical, unpartitioned Training-source, list-input, and list-
aggregation JSON where available. The browser never displays absolute paths,
fingerprints, tokens, raw persistence JSON, or stack traces.

Issue #168 completes the functional `v0.15.0` local Match Capture milestone, and
Issue #169 completed Package version `0.15.0` and Release-documentation
preparation. The maintainer published the Release manually at commit `ec1c154`,
and Issue #170 synchronizes publication status. All seven Root workflows, 63
Schemas, six Session examples, and 85 generated scenarios remain unchanged.
The published baseline has no Public Match API,
Match Schema/data workflow, Match Root workflow, Match CLI export, automatic
analysis, persisted Workspace report, public/persisted Player Catalog, communication-aware
Dataset workflow, database/remote deployment, YouTube integration, or EuroSkat
integration.
See [Match capture contracts](docs/match_capture_contracts.md),
[Observed Game capture contracts](docs/observed_game_capture_contracts.md),
[Match Workspace contracts](docs/match_workspace_contracts.md), and
[Match Capture Application services](docs/match_capture_application_services.md),
[Local Match Capture interface](docs/local_match_capture_interface.md), and
[Match Player Statistics](docs/match_player_statistics.md), and
[Match review and materialization](docs/match_review_and_materialization.md), and
[Match analysis and exports](docs/match_analysis_and_exports.md).

### Private Learning Corpus identity, Player history, and evidence

Issue #171 begins the `v0.16.0 - Learning-ready behavior and communication data`
milestone with internal immutable Learning Corpus identity and Catalog
contracts. Match Workspaces remain editable authoritative capture sources. A
Match Snapshot retains one exact strictly resumed Workspace persistence document
as an immutable content-addressed source copy; corrected content creates a new
Snapshot without mutating the source Workspace.

Each Snapshot derives exactly three stable-ID Player Observations plus Snapshot-
scoped Game, Decision, Commentary, and Response References in canonical source
order. Empty and Passed Deal Slots create no Game Reference. Original Cards,
Commentary text, commentator identity, URLs, and timecodes remain in the private
Workspace copy rather than being duplicated into references.

The separate lightweight Catalog stores Snapshot entries and exactly one explicit
current Snapshot selection per represented logical Match. It permits multiple
revisions and same-revision content conflicts, performs non-mutating duplicate
and revision classification, and never chooses a newest revision automatically.
Issue #172 adds one explicit private Corpus root with authoritative
`catalog.json`, immutable content-addressed Match Snapshot objects, deterministic
Catalog fingerprints, strict full Resume, valid orphan reporting, no-clobber
object publication, optimistic atomic Catalog Save, strict Workspace-file import,
and persisted explicit Current-selection changes. Object publication precedes
Catalog publication, so a Catalog conflict intentionally leaves a valid reported
orphan that later import can reuse. No automatic latest selection, repair,
deletion, or garbage collection occurs.

Issue #173 adds a separate deterministic derived Player Catalog over only the
explicit Current Match Snapshots. It groups exact case-sensitive stable Player
IDs, retains label and exact platform-alias observations, reports alias conflicts,
retains every Match-bound exact Statistics record, and supports strict
latest-unambiguous or explicit-observation as-of selection. Non-current revisions
and orphans do not contribute. The Player Catalog is not persisted, performs no
Player merge or Profile derivation, and changes no Issue #171/#172 bytes.

Issue #174 adds a separate deterministic minimized Human Evidence collection and
canonical in-memory export from those same explicit Current Match Snapshots. It
preserves exact original human Commentary, commentator identity, subject observed
Card, explicitly linked later Response behavior, source metadata, and timecodes,
while excluding private deals, unrelated Cards, Statistics, Profiles, analysis,
recommendations, and derived tags. A Response Link remains a caller association,
not a causal claim, and an observed Card remains behavior rather than an optimal
label. Human Evidence is private, non-persisted, and isolated from Match Analysis,
Coaching, and Training Dataset version `1`.

Issue #175 adds separate method-bound Strategy Teacher Evidence from caller-bound
exact executed Decision Analysis Reports. Each Report must reconcile with the
explicit Current Match Snapshot, closed Game/Decision References, observed Card,
one rebuilt Position Request, exact Profile binding, and one validated retained
Result without workflow execution. Immediate/Search/Auto method, budget, status,
Candidates, fallback, reviews, and Profile/policy context are retained without a
ground-truth claim or preferred Teacher. Exact Report/Request/Result fingerprints
and a wall-clock-normalized semantic Teacher fingerprint keep distinct source
Reports separate. The collection and path-free canonical export are private and
non-persisted.

Issue #176 adds a separate private unpartitioned Learning Dataset version `2`.
It reconciles the exact Store, Player Catalog, Human Evidence, and Strategy
Teacher collections; reuses the Issue #167 safe Decision-state seam; separates
observed behavior, time-safe Player Context, all method-bound Teachers, exact
Commentary, and joined outgoing/incoming Responses; reports skipped Decisions
and unjoined Human Evidence; and provides stable Record identities plus one
canonical path-free export. It defines no universal target, label, or task and
changes no Training Dataset version `1` behavior. Issue #177 adds separate
private Match-Snapshot-group-safe partition preparation: strict temporal Known-
player blocks, transitive Player-disjoint unseen-player components, exact Record-
primary and Match-secondary balancing, complete leakage audits, lossless index-
only partitioned views, and canonical path-free export. Issue #178 adds private
behavior, Communication, Strategy Teacher, evidence Coverage, Dataset Readiness,
and supplied `known_player`/`unseen_player` Partition Readiness summaries plus
canonical path-free export. It adds no rating, ranking, interpretation,
evaluation, model-readiness claim, persistence, or public surface. Issues #171
through #178 add no Root workflow, Public API, Schema, example, or generated
scenario.

Issue #179 completes the planned private local Learning Corpus/Dataset-v2
workflow through a separate installed/module/Legacy `corpus` command, one
explicit Corpus root, strict Workspace and executed-Decision Report-source
uploads, explicit Current selection, process-local Strategy Teacher sources and
artifact preparation, a minimized no-JavaScript-capable dashboard, and seven
authenticated canonical downloads. Preparation builds Player Catalog, Human
Evidence, Strategy Teacher Evidence, Learning Dataset v2, known-player and
unseen-player partition Results, then the Cross-game Summary without analysis
execution. Derived artifacts remain non-persisted and no public contract or
Schema is added. Issue #180 completed Package version `0.16.0` and Release-
documentation preparation without changing product behavior. The maintainer
published `v0.16.0` manually on 2026-08-18 at commit `91b1360`, and Issue #181
synchronizes publication status. GitHub Releases is the authoritative
publication record; no Package-index or PyPI publication is claimed.

Issue #191 extends the published `v0.17.0` baseline with strict one-Decision Match
`information_set_search`, safe revision-scoped diagnostics, exact Report-source
transfer, focused Current-Snapshot Strategy Teacher Evidence, existing Dataset-v2
joins and cross-game method counts, and the unchanged local Corpus preparation
and seven-download workflow. It adds no automatic capture, persistence, Public
API, Schema, example, or generated scenario. See
[Match Information-set Search and Strategy Teacher Evidence](docs/match_information_set_search_and_strategy_teacher.md).
Start it with
`skatmind corpus --corpus CORPUS_ROOT`,
`python -m skatmind corpus --corpus CORPUS_ROOT`, or
`python main.py corpus --corpus CORPUS_ROOT`. See
[Learning Corpus identity and Catalogs](docs/learning_corpus_identity_and_catalogs.md),
[Learning Corpus persistence and Workspace import](docs/learning_corpus_persistence_and_import.md),
[Learning Corpus Player Catalog and Statistics history](docs/learning_corpus_player_catalog_and_statistics_history.md),
[Learning Corpus human Commentary and Response evidence](docs/learning_corpus_human_commentary_and_response_evidence.md),
[Learning Corpus Strategy Teacher Evidence](docs/learning_corpus_strategy_teacher_evidence.md),
[Learning Dataset version 2](docs/learning_dataset_v2.md),
[Learning Dataset version 2 partition preparation](docs/learning_dataset_v2_partition_preparation.md),
[Learning Dataset version 2 cross-game summaries](docs/learning_dataset_v2_cross_game_summaries.md),
[Learning Corpus Tactical Motif evidence and summaries](docs/learning_corpus_tactical_motif_evidence_and_summaries.md),
[Learning Corpus Tactical Cross-game Coaching](docs/learning_corpus_tactical_cross_game_coaching.md), and
[Learning Corpus browser workflows](docs/learning_corpus_browser_workflows.md).

Issue #192 adds separate Information-set Replay Coaching and private Match
Historical Information-set Review/Coaching controls. It reuses one retained
Historical Information-set Review, treats PIMC and Immediate as diagnostics with
no fallback, preserves the existing bounded Coaching path, and adds complete
internal/public Provenance. See
[Information-set Replay Coaching and Match Historical analysis](docs/information_set_replay_coaching_and_match_historical_analysis.md).

Issue #194 adds separate deterministic Historical Tactical Motif Review. It
reuses one retained Decision Snapshot sequence, attaches actual Cards only after
decision-time facts and completed-Trick outcomes only after completion, and
exposes explicit Root CLI and private Match browser controls. Existing bounded
and Information-set Replay Coaching reports remain unchanged. See [Tactical motif
evidence](docs/tactical_motif_evidence.md).

Issue #195 reuses the exact Issue #194 single-game detector over explicit Current
Match Snapshots to build a separate process-local Tactical Motif Evidence family.
Every observed Decision produces safe Evidence or an explicit skip; partial
Matches and incomplete final Tricks remain bounded and factual. A separate
Summary reports exact global, Player, role, seat, phase, contract, distinct-Game,
distinct-Match, and `single_game_only`/`multiple_games_one_match`/
`multiple_matches` recurrence Counts without rates, traits, quality,
significance, correctness, causal, communication, or Coaching claims. Human,
Strategy Teacher, and Tactical Evidence remain separate, and Learning Dataset
version `2` is unchanged.

The existing browser action prepares the two Tactical artifacts with the seven
Issue #179 artifacts as one generation-safe process-local publication. It adds a
minimized Tactical dashboard summary and two authenticated canonical downloads,
bringing the Issue #195 point-in-time set to nine:

* `/downloads/tactical-motif-evidence.json`
* `/downloads/tactical-motif-cross-game-summary.json`

Both exports remain deterministic, path-free, private, loopback-authenticated,
and non-persisted. Issue #195 adds no Package/API/workflow/Console-Script/Schema/
example/generated-scenario or Dataset-v2 contract change. See [Learning Corpus
Tactical Motif evidence and summaries](docs/learning_corpus_tactical_motif_evidence_and_summaries.md).

Issue #196 adds a separate deterministic Tactical Cross-game Coaching artifact.
It exact-joins Tactical Evidence with every method-bound Strategy Teacher Report,
keeps exact Reports while counting equal semantic Teachers once per Decision,
and permits a focus only when every distinct semantic complete-Search Teacher
ranks the observed Card below an alternative on at least two Decisions in at
least two Games. Mixed, Immediate-only, partial, timeout, unavailable, and
not-assessable evidence remains descriptive. One Player Report is retained for
every Player Catalog entry, at most five focus areas are selected by fixed
objective-impact priority, and fixed Guidance makes no ground-truth, perfect-
play, Player-rating, intent, communication, causal, or significance claim.

The existing preparation action atomically publishes the existing, Tactical,
and Coaching families and exposes only aggregate Coaching Counts on the private
dashboard. The tenth authenticated canonical download is:

* `/downloads/tactical-cross-game-coaching.json`

The report is process-local, deterministic, path-free, and non-persisted. Issue
#196 changes no Package/API/workflow/Console-Script/Schema/example/generated-
scenario, Learning Dataset version `2`, or Dataset-v2 Summary contract. See
[Learning Corpus Tactical Cross-game Coaching](docs/learning_corpus_tactical_cross_game_coaching.md).

The facade executes already loaded Root documents without caller transport I/O
and preserves Root JSON output by default. Its lazy schema backend uses packaged
resources and works from source, Editable, Wheel, and sdist installations. Installed CLI
contract version `1` adds the exact `skatmind` Console Script and
`python -m skatmind`; repository-root `main.py` remains a compatible Legacy
facade over the same Package implementation. Field-level provenance is
internally enforced and attached for live and retrospective Position and
Historical execution and for Dataset, Preparation, Opponent, Profile, list, and
comparison workflows. All seven Root workflows have complete internal Result
ledgers. Issue #147 additively exposes only the mapped Root Result and actual
artifacts through Public API `include_provenance=True`, Root
`field_provenance`, strict Schema, and CLI `--include-provenance`. Issue #202
binds the exact consumed Request, effective options, and optional external source
to pre-analysis Information Use Context, retained stages, and exact final
Result/artifact serialization without widening that public view. See
[Public Python API v1](docs/public_python_api_v1.md),
[Application orchestration](docs/application_orchestration.md),
[Complete Result provenance](docs/complete_result_provenance.md), and
[Public field provenance](docs/public_field_provenance.md), and
[v1 information provenance enforcement](docs/v1_information_provenance_enforcement.md).

## Requirements

* Python 3.13 or newer
* PowerShell for helper scripts on Windows
* Exact direct runtime dependencies:

  * `jsonschema>=4.23.0`
  * `referencing>=0.31.0`
* Development dependencies from `.[dev]`, including:

  * `build`
  * `pytest`
  * `ruff`

## Installation

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the project with development dependencies:

```powershell
python -m pip install -e ".[dev]"
```

Run the combined check script:

```powershell
.\scripts\check.ps1
```

Build one Wheel and one sdist without publishing them:

```powershell
python -m build
```

See [Packaging and distribution](docs/packaging_and_distribution.md) for Package
Data and artifact validation, and the
[v1 installation and supported-platform matrix](docs/v1_installation_and_supported_platform_matrix.md)
for exact dependencies, installation forms, platform evidence, and boundaries.

The installation exposes both Package CLI forms:

```powershell
skatmind
python -m skatmind
skatmind app --help
python -m skatmind app --help
skatmind --help
python -m skatmind --help
skatmind session --help
python -m skatmind session --help
skatmind capture --help
python -m skatmind capture --help
skatmind corpus --help
python -m skatmind corpus --help
```

See [Installed CLI](docs/installed_cli.md) for invocation identities, output,
errors, compatibility, and clean-install validation. Repository examples are not
installed as Package Data. The one approved pre-v1 namespace break and strict
persisted-input boundary are documented in
[SkatMind rename and migration](docs/skatmind_rename_and_migration.md).

The behavior-preserving internal Root and Session transport split, Legacy patch
facades, and one-way import boundary are documented in
[CLI internal architecture](docs/cli_internal_architecture.md).

## Usage

Open the unified local application shell:

```powershell
skatmind
```

Bare installed, module, and Legacy invocation now open the same private
loopback-only shell. `skatmind app` is the explicit form. Home and About are
complete; guided process-local Position analysis, one-Decision Post-game Review,
normal-completion Historical entry, strict JSON import/download, and readable
Results are available. Managed Session entry and execution, Match Capture,
Learning workflows, and explicit Match-to-Corpus transfer are also available
without normal-user paths or ports. See [Guided analysis and Results](docs/unified_local_frontend_guided_analysis_and_results.md),
the [managed stateful workflows](docs/unified_local_frontend_stateful_workflows.md),
and the [application shell](docs/unified_local_frontend_application_shell.md).

Parse and execute an already loaded Root JSON document:

```python
import json
from pathlib import Path

from skatmind.api.v1 import ExecutionOptionsV1, execute_document, serialize_result

document = json.loads(Path("examples/grand_second_position.json").read_text())
result = execute_document(
    document,
    options=ExecutionOptionsV1(
        include_provenance=True,
        workflow_options={"sample_count_override": 20},
    ),
)
serialized = serialize_result(result)
```

See [Public API contracts](docs/public_api_contracts.md) for exports,
compatibility, errors, and normal Result states, and
[Public Python API v1](docs/public_python_api_v1.md) for executable facade usage.

Show available CLI options and common command examples:

```powershell
skatmind --help
python -m skatmind --help
python main.py --help
```

The first two commands are installed Package interfaces. `python main.py` is the
Legacy repository interface and remains compatible through at least `v1.0.0`.

Create, inspect, and continue one explicit private Session file:

```powershell
skatmind session new --session session.json --input examples/session_create_live.json
skatmind session show --session session.json
skatmind session assistant --session session.json
```

The same `session` family is available through `python -m skatmind` and
`python main.py`. It has no default path. See
[Session CLI and end-to-end capture](docs/session_cli_and_end_to_end_capture.md)
for all 12 subcommands, options, persistence conflicts, privacy, and Exit Codes.

Capture one EuroSkat 36er Standard Match without authoring JSON:

```powershell
skatmind capture --workspace MATCH.json
```

The same `capture` family is available through `python -m skatmind` and
`python main.py`. It has no default path and always binds to loopback. See
[Local Match Capture interface](docs/local_match_capture_interface.md) for
Workspace creation and Resume, forms, rapid Card entry, autosave, conflicts,
explicit analysis and materialization, authenticated local downloads, local
security, and privacy.

Run analysis from the repository root with the root `input_position.json`
quick-start fixture:

```powershell
python main.py --input input_position.json
```

Run analysis with a specific input file:

```powershell
python main.py --input examples/grand_second_position.json
```

Aggregate one complete fixed-three-player historical list or compare independent
completed lists. The JSON root selects the workflow; there is no list-specific
CLI flag:

```powershell
python main.py --input examples/fixed_three_player_historical_list_mixed.json
python main.py --input examples/fixed_three_player_historical_list_all_passed.json
python main.py --input examples/fixed_three_player_historical_list_comparison.json
```

These workflows accept only `--input`, `--output`, `--quiet`, and
`--include-provenance`. Single-list
output retains all 36 privacy-safe progression Entry Facts and final standings.
Comparison output is compact: it retains source summaries and final deltas but no
progression, Historical Game Records, series rollup, ratings, or winner claim.

The existing Immediate expected-value recommendation remains the default. JSON
input may explicitly select `immediate_expected_value`, strict `bounded_search`,
`auto`, or strict `information_set_search`. Bounded Search and `auto` require a
complete `bounded_search_settings` object; Information-set Search requires its
exact nine-field `information_set_search_settings` object. These methods support
ongoing `live_decision` positions plus their documented bounded flat
`post_game_review` positions with `actual_card_played`:

```powershell
python main.py --input examples/grand_bounded_search_exhaustive.json
python main.py --input examples/grand_auto_search_fallback.json
python main.py --input examples/grand_bounded_search_post_game_review.json
python main.py --input examples/information_set_search.json
```

Strict Search never falls back. `auto` runs Immediate only when Search returns a
valid result without a recommendation, and marks fallback only when Immediate
returns a card. Search uses its own required seed; the existing top-level seed
continues to control Immediate and auto fallback. No CLI method override is
provided. `information_set_search` has no fallback and does not change `auto`;
there is no `information_set_auto`.

The same configured Search method becomes the local Multi-Step policy when
`--multi-step` is supplied and `--card-policy` is omitted. An explicit
`--card-policy` must match that Search method; a legacy policy conflict, a
Search-method mismatch, or a Search card policy without matching JSON settings
is rejected. Legacy inputs still default to `first_legal`.

```powershell
python main.py --input examples/grand_bounded_search_exhaustive.json --multi-step 1
python main.py --input examples/grand_bounded_search_exhaustive.json --multi-step 1 --compare-policies
python main.py --input examples/information_set_search_multi_step.json --multi-step 1
python main.py --input examples/information_set_search_multi_step.json --multi-step 1 --compare-policies
```

Search is rerun from the prepared public state at every local decision. Each
decision receives the full configured budget freshly and a deterministic child
of the explicit Search seed. Search never receives the coherent execution root;
the selected public recommendation is executed separately in that root.
Information-set Search also retains no Search World or controlled Policy across
decisions and stops before local play without fallback when no recommendation is
available.

Run Historical Search Review with an explicit Search seed. It uses the immutable
`historical_review_v1` profile by default and runs an independent Immediate
baseline at every decision:

```powershell
python main.py --input examples/historical_grand_normal_completion.json --historical-search-review --search-seed 71 --output outputs/historical-search.json
```

Build the complete public Replay Coaching Report from the same information-safe
decision analysis. Coaching-only output omits the separate Historical Search
Review summary; supplying both flags emits both summaries from one shared pass:

```powershell
python main.py --input examples/historical_grand_normal_completion.json --historical-replay-coaching --search-seed 71 --samples 20 --seed 42 --output outputs/replay-coaching.json
python main.py --input examples/historical_grand_normal_completion.json --historical-search-review --historical-replay-coaching --search-seed 71 --samples 20 --seed 42
```

Evaluate bounded Search against Immediate on the default `validation` and `test`
dataset partitions. `evaluation_v1` is the default profile, and the optional cap
is one stable global decision prefix:

```powershell
python main.py --input examples/training_dataset_normal_play.json --evaluate-bounded-search --search-seed 71 --search-evaluation-max-decisions 10 --output outputs/search-evaluation.json
```

`--search-budget-profile` accepts `interactive_v1`, `historical_review_v1`, or
`evaluation_v1`. These profiles are immutable work budgets, not latency
guarantees. See [Bounded search contracts](docs/bounded_search_contracts.md) and
[Bounded Search performance](docs/bounded_search_performance.md).
The separate Information-set Search corpus and local reference measurements are
documented in [Information-set Search performance](docs/information_set_search_performance.md).

Run immediate analysis with a configured opponent response policy:

```powershell
python main.py --input examples/grand_second_position.json --opponent-response-policy highest_point
```

Run a multi-step analysis:

```powershell
python main.py --input examples/grand_second_position.json --multi-step 2
```

Run the deterministic hidden-card inference example with two Multi-Step decisions:

```powershell
python main.py --input examples/grand_hidden_card_inference.json --multi-step 2
```

Its attributed public Grand history confirms that `right` failed to follow
clubs. The exact root compatible-world count is `275275`, and the generated
scenario also demonstrates later simulated public-evidence progression.

Compare all multi-step local card-selection policies:

```powershell
python main.py --input examples/grand_second_position.json --multi-step 1 --compare-policies
```

Print only policy-comparison output, suppressing the normal analysis and
individual multi-step details:

```powershell
python main.py --input examples/grand_second_position.json --multi-step 1 --compare-policies --comparison-only
```

Run a multi-step analysis with separate left/right opponent policies:

```powershell
python main.py --input examples/grand_left_right_opponent_policies.json --multi-step 2 --left-opponent-lead-policy highest_point --right-opponent-response-policy basic_defender_response
```

Global policy presets and policies cascade to both opponents. Side-specific input fields or CLI overrides win for their side.

Write output to JSON:

```powershell
python main.py --input examples/grand_second_position.json --output outputs/result.json
```

Add the bounded public-safe field-provenance sidecar through any supported CLI
form:

```powershell
skatmind --input examples/grand_second_position.json --include-provenance --output outputs/result.json
python -m skatmind --input examples/grand_second_position.json --include-provenance --output outputs/result.json
python main.py --input examples/grand_second_position.json --include-provenance --output outputs/result.json
```

Without `--quiet`, all forms append one concise aggregate Field Provenance
section. With `--quiet`, the section is suppressed while the JSON sidecar is
still written.

Suppress successful human-readable stdout output for automation-friendly JSON runs:

```powershell
python main.py --input examples/grand_second_position.json --output outputs/result.json --quiet
```

Without `--quiet`, default CLI behavior is unchanged and successful analysis output is still printed to `stdout`. With `--quiet`, analysis still runs normally and JSON output is still written when `--output` is provided. Expected errors are not suppressed and still go to `stderr`.

Run an overbid example where the declarer wins card points but loses settlement:

```powershell
python main.py --input examples/grand_overbid_declarer_card_points_win.json --output outputs/overbid_test.json
```

Run a structured declarer concession that preserves all unplayed points:

```powershell
python main.py --input examples/declarer_concession.json
```

Run a structured defender concession with joint defender liability and no
remaining-point assignment:

```powershell
python main.py --input examples/defender_concession.json
```

Run a post-game review example with an actual played card:

```powershell
python main.py --input examples/spades_post_game_actual_card_played.json
```

Validate and summarize a complete normally played historical game:

```powershell
python main.py --input examples/historical_grand_normal_completion.json
```

Validate timed continued play after historical defender open play:

```powershell
python main.py --input examples/historical_grand_defender_open_play_continuation.json --historical-decision-snapshots
```

Validate timed continued play after historical declarer-card exposure:

```powershell
python main.py --input examples/historical_grand_declarer_card_exposure_continuation.json --historical-decision-snapshots
```

Validate an exact historical play prefix ending in declarer concession:

```powershell
python main.py --input examples/historical_grand_declarer_concession.json
```

Validate an exact historical prefix ending in joint-liability defender concession:

```powershell
python main.py --input examples/historical_grand_defender_concession.json
```

Validate an exact historical prefix ending in unanimously accepted declarer-card
exposure:

```powershell
python main.py --input examples/historical_grand_declarer_card_exposure.json
```

Add one information-safe snapshot immediately before each actual play:

```powershell
python main.py --input examples/historical_grand_normal_completion.json --historical-decision-snapshots
```

Review all 30 historical decisions with deterministic immediate analysis:

```powershell
python main.py --input examples/historical_grand_normal_completion.json --historical-game-review --samples 100 --seed 42
```

Review a complete Grand Ouvert with the exact shrinking declarer hand from
decision 1:

```powershell
python main.py --input examples/historical_grand_ouvert_review.json --historical-game-review --samples 20 --seed 42
```

Apply exact stable-ID external profiles captured strictly before the game:

```powershell
python main.py --input examples/historical_grand_normal_completion.json --historical-game-review --opponent-statistics-file examples/historical_opponent_statistics.json --use-profile-presets --samples 20 --seed 42
```

Historical-game inputs form a separate workflow. External profile application
requires `played_at`, historical review, profile-preset opt-in, at least one exact
participant match, and captures strictly older than the game. Live-only relative
binding IDs are rejected. `--samples` and `--seed` are accepted only with review.
Historical declarer and defender concessions, accepted declarer-card exposure,
terminal defender open play, open-card throwing, and a valid party-wide Claim
support snapshots, review, time-safe external profiles, variable training
samples, and record/player partition audits for every actual supplied play. The
terminal event is not reviewed or used as a target.
Either timed continuation may precede normal completion or one supported terminal
shortening; only post-event card decisions receive the exact shrinking public
defender or declarer hand, and the terminal action is never a decision target.
Historical opponent statistics, reusable export, rolling profile construction,
and rolling policy evaluation support normal completion and all six shortened
terminal events, including open-card throwing and the party-wide Claim.
Normal-completion event details add no statistic or profile signal.
Each source record has one game of statistics weight, while targets contribute
only actual card decisions, including valid zero-decision targets. See
[Shortened historical opponent workflows](docs/shortened_historical_opponent_workflows.md).

Convert a versioned training/evaluation dataset without running
recommendations or simulation:

```powershell
python main.py --input examples/training_dataset_normal_play.json
```

The variable-length example produces 14 samples from a concession prefix:

```powershell
python main.py --input examples/training_dataset_variable_length.json
```

Audit exact stable-player membership without generating samples:

```powershell
python main.py --input examples/training_dataset_partition_audit.json --audit-dataset-partitions --dataset-partition-mode known_opponent
```

Known-opponent policy permits cross-partition player overlap. Unseen-player
policy enforces player-disjoint partitions. Datasets without policy metadata
remain valid with unspecified intent. See
[Dataset partition policies](docs/dataset_partition_policies.md).

Automatically prepare a reusable partitioned version-1 Training Dataset from
unpartitioned Records:

```powershell
python main.py --input examples/training_dataset_preparation_known_opponent.json
python main.py --input examples/training_dataset_preparation_unseen_player.json
python main.py --input examples/training_dataset_preparation_unavailable.json
```

The root `training_dataset_preparation_input` selects the separate
`training_dataset_preparation` workflow. Mode `known_opponent` dispatches to
`temporal_known_opponent_v1`; mode `unseen_player` dispatches to
`component_balanced_unseen_player_v1`. The request has no algorithm selector,
default weights, CLI overrides, or fallback. A complete Plan materializes a
losslessly reusable existing version-1 `training_dataset_input` and its audit. An
unavailable Plan is still a successful result and returns explicit null dataset
and audit values without partial assignments or summaries. Only `--input`,
`--output`, `--quiet`, and `--include-provenance` are accepted. Plan data and
concise CLI output are
card-free; a complete structured output necessarily retains source cards inside
the nested reusable dataset. See [Automatic dataset preparation
contracts](docs/automatic_dataset_preparation_contracts.md).

Training-dataset inputs form a separate workflow. Only `--input`, `--output`,
`--quiet`, and `--include-provenance` are accepted for normal sample conversion.
The same
input can instead act as the versioned multi-game container for exact historical
opponent-statistics aggregation:

```powershell
python main.py --input examples/training_dataset_normal_play.json --aggregate-opponent-statistics --opponent-statistics-partition train --opponent-statistics-partition validation --opponent-statistics-before 2026-07-21T00:00:00Z --output outputs/historical-statistics.json --export-opponent-statistics outputs/opponent-statistics.json
```

Aggregation requires `played_at` on every partition-selected game, uses a strict
exclusive cutoff, derives wins from final settlement, emits no decision samples,
and does not apply a policy. See
[Historical opponent statistics](docs/historical_opponent_statistics.md).

The mixed normal/concession example supports aggregation and export with the
same commands:

```powershell
python main.py --input examples/training_dataset_shortened_opponent_workflows.json --aggregate-opponent-statistics
```

Evaluate rolling game-start profiles against observed known-opponent card choices:

```powershell
python main.py --input examples/historical_opponent_policy_evaluation_dataset.json --evaluate-opponent-policy-profiles --output outputs/opponent-policy-evaluation.json
```

Use `--evaluate-rolling-opponent-policies` with
`examples/training_dataset_shortened_opponent_workflows.json` to evaluate its
14-decision concession target against two strictly earlier source games.

This workflow uses disjoint source and evaluation partition names, strict as-of
history, and preferred-card matching. It measures behavioral imitation only, not
strategic quality or optimal play. See
[Rolling opponent-policy evaluation](docs/opponent_policy_evaluation.md).

Validate, normalize, and derive an explainable profile from externally supplied
opponent statistics:

```powershell
python main.py --input examples/opponent_statistics.json
```

Opponent-statistics inputs form a separate workflow. Only `--input`, `--output`,
`--quiet`, and `--include-provenance` are accepted. Public values use percentage
points;
canonical profile rates use `0..1`. When optional exact counts are absent, they
are not inferred; role evidence may instead be exposed as an unrounded estimate.
The standalone conversion does not run analysis.

Attach the same validated statistics file to a live position with exact,
case-sensitive left/right player IDs:

```powershell
python main.py --input examples/grand_second_position.json --opponent-statistics-file examples/opponent_statistics.json --left-opponent-player-id opponent-123 --right-opponent-player-id opponent-789 --use-profile-presets --samples 20 --seed 42
```

Either side may be bound. Only confidence-gated actionable presets affect the
existing side-specific live policy path. Manual side profiles and existing
explicit policy settings retain precedence. See
[Live opponent profiles](docs/live_opponent_profiles.md) and
[Historical opponent profiles](docs/historical_opponent_profiles.md).

CLI exit codes:

* `0` = success
* `1` = expected input, runtime, or output failure
* `2` = invalid CLI usage

Expected errors are written to `stderr`. Successful analysis output remains on `stdout`.

For a concise walkthrough of common CLI workflows, see [Examples documentation](docs/examples.md#workflow-walkthroughs).

## Documentation

Detailed documentation is split into topic-specific files:

* [Input JSON](docs/input_json.md)
* [Public API contracts](docs/public_api_contracts.md)
* [Public Python API v1](docs/public_python_api_v1.md)
* [Public Session API version 1](docs/public_session_api_v1.md)
* [Session provenance](docs/session_provenance.md)
* [Session Decision observations](docs/session_decision_observations.md)
* [Session CLI and end-to-end capture](docs/session_cli_and_end_to_end_capture.md)
* [Installed CLI](docs/installed_cli.md)
* [CLI internal architecture](docs/cli_internal_architecture.md)
* [Packaging and distribution](docs/packaging_and_distribution.md)
* [Application orchestration](docs/application_orchestration.md)
* [Interactive session contracts](docs/interactive_session_contracts.md)
* [Match capture contracts](docs/match_capture_contracts.md)
* [Observed Game capture contracts](docs/observed_game_capture_contracts.md)
* [Match Workspace contracts](docs/match_workspace_contracts.md)
* [Match Capture Application services](docs/match_capture_application_services.md)
* [Local Match Capture interface](docs/local_match_capture_interface.md)
* [Match Player Statistics](docs/match_player_statistics.md)
* [Match review and materialization](docs/match_review_and_materialization.md)
* [Match analysis and exports](docs/match_analysis_and_exports.md)
* [Match Information-set Search and Strategy Teacher Evidence](docs/match_information_set_search_and_strategy_teacher.md)
* [Information-set Replay Coaching and Match Historical analysis](docs/information_set_replay_coaching_and_match_historical_analysis.md)
* [Learning Corpus identity and Catalogs](docs/learning_corpus_identity_and_catalogs.md)
* [Learning Corpus persistence and Workspace import](docs/learning_corpus_persistence_and_import.md)
* [Learning Corpus Player Catalog and Statistics history](docs/learning_corpus_player_catalog_and_statistics_history.md)
* [Learning Corpus human Commentary and Response evidence](docs/learning_corpus_human_commentary_and_response_evidence.md)
* [Learning Corpus Strategy Teacher Evidence](docs/learning_corpus_strategy_teacher_evidence.md)
* [Learning Dataset version 2](docs/learning_dataset_v2.md)
* [Learning Dataset version 2 partition preparation](docs/learning_dataset_v2_partition_preparation.md)
* [Learning Dataset version 2 cross-game summaries](docs/learning_dataset_v2_cross_game_summaries.md)
* [Learning Corpus Tactical Motif evidence and summaries](docs/learning_corpus_tactical_motif_evidence_and_summaries.md)
* [Learning Corpus Tactical Cross-game Coaching](docs/learning_corpus_tactical_cross_game_coaching.md)
* [Learning Corpus browser workflows](docs/learning_corpus_browser_workflows.md)
* [Incremental Session transitions](docs/incremental_session_transitions.md)
* [Retrospective Session export](docs/retrospective_session_export.md)
* [Session Position export and Decision checkpoints](docs/live_session_position_export.md)
* [Session Undo, correction, and Checkpoint lineage](docs/session_undo_and_correction.md)
* [Session persistence and resume](docs/session_persistence_and_resume.md)
* [Field-level information provenance](docs/field_level_information_provenance.md)
* [Public field provenance](docs/public_field_provenance.md)
* [Live analysis provenance](docs/live_analysis_provenance.md)
* [Retrospective review provenance](docs/retrospective_review_provenance.md)
* [Dataset, list, and opponent provenance](docs/dataset_list_and_opponent_provenance.md)
* [Complete Result provenance](docs/complete_result_provenance.md)
* [Input JSON schema](schemas/input.schema.json)
* [Declarer concessions](docs/declarer_concessions.md)
* [Defender concessions](docs/defender_concessions.md)
* [Accepted declarer card exposure](docs/declarer_card_exposure.md)
* [Declarer card exposure continuation](docs/declarer_card_exposure_continuation.md)
* [Defender open play](docs/defender_open_play.md)
* [Defender open play continuation](docs/defender_open_play_continuation.md)
* [Open card throw](docs/open_card_throw.md)
* [Game-shortening input schema](schemas/game_shortening.schema.json)
* [Game-continuation input schema](schemas/game_continuation.schema.json)
* [Declarer-concession output schema](schemas/declarer_concession_output.schema.json)
* [Defender-concession output schema](schemas/defender_concession_output.schema.json)
* [Declarer-card-exposure output schema](schemas/declarer_card_exposure_output.schema.json)
* [Declarer-card-exposure continuation output schema](schemas/declarer_card_exposure_continuation_output.schema.json)
* [Defender-open-play input schema](schemas/defender_open_play.schema.json)
* [Defender-open-play output schema](schemas/defender_open_play_output.schema.json)
* [Defender-open-play continuation input schema](schemas/defender_open_play_continuation.schema.json)
* [Defender-open-play continuation output schema](schemas/defender_open_play_continuation_output.schema.json)
* [Open-card-throw input schema](schemas/open_card_throw.schema.json)
* [Open-card-throw output schema](schemas/open_card_throw_output.schema.json)
* [Theoretical-level assessment schema](schemas/theoretical_level_assessment.schema.json)
* [Exact rest-trick proof schema](schemas/exact_rest_trick_proof.schema.json)
* [Public-hand constraint schema](schemas/public_hand_constraint.schema.json)
* [Historical games](docs/historical_games.md)
* [Historical declarer card exposure](docs/historical_declarer_card_exposure.md)
* [Historical declarer-card-exposure continuation](docs/historical_declarer_card_exposure_continuation.md)
* [Historical defender open play](docs/historical_defender_open_play.md)
* [Historical open card throw](docs/historical_open_card_throw.md)
* [Historical defender open-play continuation](docs/historical_defender_open_play_continuation.md)
* [Historical decision snapshots](docs/historical_decision_snapshots.md)
* [Historical game review](docs/historical_game_review.md)
* [Replay coaching contracts](docs/replay_coaching_contracts.md)
* [Ouvert-aware simulation](docs/ouvert_aware_simulation.md)
* [Coherent hidden-world simulation](docs/coherent_hidden_world_simulation.md)
* [Hidden-card inference](docs/hidden_card_inference.md)
* [Bounded search contracts](docs/bounded_search_contracts.md)
* [Bounded Search performance](docs/bounded_search_performance.md)
* [Information-set Search performance](docs/information_set_search_performance.md)
* [Bounded Search post-game review schema](schemas/bounded_search_post_game_review.schema.json)
* [Historical Search Review schema](schemas/historical_search_review.schema.json)
* [Historical Replay Coaching schema](schemas/historical_replay_coaching.schema.json)
* [Bounded Search evaluation schema](schemas/bounded_search_evaluation.schema.json)
* [Hidden-card inference summary schema](schemas/hidden_card_inference_summary.schema.json)
* [Historical opponent profiles](docs/historical_opponent_profiles.md)
* [Training data](docs/training_data.md)
* [Dataset partition policies](docs/dataset_partition_policies.md)
* [Automatic dataset preparation contracts](docs/automatic_dataset_preparation_contracts.md)
* [Temporal Known-opponent dataset splits](docs/temporal_known_opponent_dataset_splits.md)
* [Player-disjoint unseen-player dataset splits](docs/player_disjoint_unseen_player_dataset_splits.md)
* [Opponent statistics](docs/opponent_statistics.md)
* [Historical opponent statistics](docs/historical_opponent_statistics.md)
* [Rolling opponent-policy evaluation](docs/opponent_policy_evaluation.md)
* [Shortened historical opponent workflows](docs/shortened_historical_opponent_workflows.md)
* [Fixed-three-player historical-list contracts](docs/fixed_three_player_36_game_list_contracts.md)
* [Fixed-three-player historical-list aggregation](docs/fixed_three_player_36_game_list_aggregation.md)
* [Fixed-three-player historical-list comparison](docs/fixed_three_player_36_game_list_comparison.md)
* [Opponent profile derivation](docs/opponent_profile_derivation.md)
* [Live opponent profiles](docs/live_opponent_profiles.md)
* [Historical-game schema](schemas/historical_game.schema.json)
* [Historical defender-open-play input schema](schemas/historical_defender_open_play.schema.json)
* [Historical defender-open-play output schema](schemas/historical_defender_open_play_output.schema.json)
* [Historical open-card-throw input schema](schemas/historical_open_card_throw.schema.json)
* [Historical open-card-throw output schema](schemas/historical_open_card_throw_output.schema.json)
* [Historical party-wide Claim input schema](schemas/historical_party_wide_claim.schema.json)
* [Historical party-wide Claim output schema](schemas/historical_party_wide_claim_output.schema.json)
* [Historical game-event schema](schemas/historical_game_event.schema.json)
* [Historical declarer-card-exposure continuation event schema](schemas/historical_declarer_card_exposure_continuation_event.schema.json)
* [Historical declarer-card-exposure continuation output schema](schemas/historical_declarer_card_exposure_continuation_event_output.schema.json)
* [Historical defender-open-play continuation event schema](schemas/historical_defender_open_play_continuation_event.schema.json)
* [Historical game-events output schema](schemas/historical_game_events_output.schema.json)
* [Historical decision snapshot schema](schemas/historical_decision_snapshot.schema.json)
* [Historical game review schema](schemas/historical_game_review.schema.json)
* [Historical opponent profile application schema](schemas/historical_opponent_profile_application.schema.json)
* [Training dataset input schema](schemas/training_dataset.schema.json)
* [Training dataset output schema](schemas/training_dataset_output.schema.json)
* [Dataset partition policy schema](schemas/dataset_partition_policy.schema.json)
* [Dataset partition audit schema](schemas/dataset_partition_audit.schema.json)
* [Training Dataset preparation input schema](schemas/training_dataset_preparation.schema.json)
* [Dataset partition Plan schema](schemas/dataset_partition_plan.schema.json)
* [Training Dataset preparation output schema](schemas/training_dataset_preparation_output.schema.json)
* [Opponent statistics input schema](schemas/opponent_statistics.schema.json)
* [Opponent statistics output schema](schemas/opponent_statistics_output.schema.json)
* [Historical opponent statistics aggregation schema](schemas/historical_opponent_statistics_aggregation.schema.json)
* [Rolling opponent-policy evaluation schema](schemas/rolling_opponent_policy_evaluation.schema.json)
* [Fixed-three-player historical-list schema](schemas/fixed_three_player_historical_list.schema.json)
* [Fixed-three-player historical-list request schema](schemas/fixed_three_player_historical_list_input.schema.json)
* [Fixed-three-player historical-list comparison request schema](schemas/fixed_three_player_historical_list_comparison_input.schema.json)
* [Fixed-three-player historical-list aggregation schema](schemas/fixed_three_player_historical_list_aggregation.schema.json)
* [Fixed-three-player historical-list comparison schema](schemas/fixed_three_player_historical_list_comparison.schema.json)
* [Opponent profile derivation schema](schemas/opponent_profile_derivation.schema.json)
* [Live opponent profile application schema](schemas/opponent_profile_application.schema.json)
* [Output JSON](docs/output_json.md)
* [Output JSON schema](schemas/output.schema.json)
* [Schema validation](docs/schema_validation.md)
* [Scoring and settlement](docs/scoring.md)
* [Game-end handling](docs/game_end.md)
* [Claim and Settlement v1 boundaries](docs/claim_and_settlement_v1_boundaries.md)
* [Historical party-wide Claim](docs/historical_party_wide_claim.md)
* [Party-wide Claim contracts](docs/party_wide_claim_contracts.md)
* [Party-wide Claim proof executor](docs/party_wide_claim_proof_executor.md)
* [Party-wide Claim adjudication](docs/party_wide_claim_adjudication.md)
* [Settlement Normative Matrix](docs/settlement_normative_matrix.md)
* [Overbid handling](docs/overbid.md)
* [Performance rating](docs/performance_rating.md)
* [Examples](docs/examples.md)
* [Architecture](docs/architecture.md)
* [v1 installation and supported-platform matrix](docs/v1_installation_and_supported_platform_matrix.md)
* [Requirements traceability](docs/requirements_traceability.md)
* [v1.0 scope](docs/v1_scope.md)
* [v1.0 scope and traceability audit](docs/v1_0_scope_and_traceability_audit.md)
* [Roadmap](docs/roadmap.md)
* [Project handoff](docs/project_handoff.md)

## Development

Run all checks:

```powershell
.\scripts\check.ps1
```

Run tests directly:

```powershell
python -m pytest
```

Run Ruff checks:

```powershell
python -m ruff check .
```

Apply Ruff fixes and format code:

```powershell
.\scripts\format.ps1
```

The test suite also validates JSON files in `examples/`. If an example contains invalid cards, duplicate known cards, inconsistent completed-trick metadata, invalid game-end metadata, invalid information-policy metadata, or invalid simulation settings, the tests will fail.

## Project status

The current published stable and latest stable GitHub Release is `v0.17.0`, with
Release theme "Rules, Search, Coaching, and performance closure" and GitHub
Release title "v0.17.0 — Rules, Search, Coaching, and performance closure". The
maintainer published it manually on 2026-08-25 at commit
`8187fbe684559f9c0c2ba444be1bf33950359ad2` (`8187fbe`). Package version
`0.17.0` requires Python `>=3.13`, retains Public API contract version `1`,
exactly seven Root workflows, and the one `skat-ai = skat_ai.cli:main` Console
Script. The published baseline has Settlement Normative Matrix version `3` with
61 cases, 71 authoritative Schemas, 71 Packaged Schema Resources, six Session
examples, 98 deterministic generated outputs, ten private Corpus prepared
downloads, and 7,479 passing pytest tests in 921.96s. GitHub Releases is the
authoritative publication record; no Package-index or PyPI publication is
claimed.

The historical published `v0.16.0 — Learning-ready behavior and communication
data` baseline was published manually by the maintainer on 2026-08-18 at commit
`91b1360`. It contains 63 authoritative Schemas, 63 Packaged Schema Resources,
six Session examples, 85 deterministic generated outputs, and 6,925 passing
pytest tests in 1083.48s. Issues #171 through #179 complete that functional
milestone, Issue #180 completed Release preparation, and Issue #181 synchronized
publication status without product behavior changes.

The published `v0.17.0` functional history uses Package version `0.17.0`, Python
`>=3.13`, Public API contract version `1`, exactly seven Root workflows, one
Console Script, and six Session examples. Issue #186 updates the Settlement
Normative Matrix to version `3` with the same 61 cases and adds the Historical-
only bounded party-wide Claim. Issue #189 adds four Information-set Search
Schemas, one example, and four generated-output scenarios. Issue #190 adds strict
Information-set Search Multi-Step and Policy Comparison integration, one example,
and two scenarios without adding a Schema, bringing the working tree to 69
authoritative and packaged Schemas and 94 scenarios. The published `v0.16.0`
counts above remain unchanged Release facts.

Issue #191 adds the private Match/Report/Teacher/Dataset/Corpus Information-set
integration without changing those working counts, Package version, Public API,
Root workflows, Console Script, or Session examples.

Issue #192 subsequently adds one strict Information-set Replay Coaching Schema,
one Root example, and two append-only scenarios. Its point-in-time working totals
are therefore 70 authoritative and packaged Schemas and 96 scenarios. Package
version, Public API contract, Root workflows, Console Script, Settlement Matrix
version `3` and 61 cases, and six Session examples remain unchanged.

Issue #193 adds a deterministic synthetic Information-set Search benchmark
corpus, a strict repository-local runner and focused tests, and documented local
reference measurements. It changes no production code, Schema, route, profile,
Public API, Package version, example, or generated scenario, so those working
counts and published Release facts remain unchanged.

Issue #194 adds one strict Tactical Motif Review Schema, one Root example, and
two append-only scenarios. The final published totals are therefore 71
authoritative and packaged Schemas and 98 scenarios. Package version, Public API
contract, Root workflows, Console Script, Settlement Matrix version `3` and 61
cases, and six Session examples remain unchanged.

Issue #195 adds private process-local Learning Corpus Tactical Motif Evidence,
exact descriptive cross-game summaries, and two authenticated downloads. It adds
no Schema, example, generated scenario, Package/API/workflow/Console-Script/
Session change, or Learning Dataset version `2` mutation, so those current
working totals remain unchanged.

Issue #196 adds private deterministic Tactical Cross-game Coaching and a tenth
authenticated download. It changes no Package/API/workflow/Console-Script/
Schema/example/generated-scenario/Session/Dataset-v2 baseline, so the current
working totals remain 71 authoritative and packaged Schemas, six Session
examples, and 98 scenarios.

Issue #197 records the documentation-only scope and Release-readiness audit.
Issue #198 changes only Package metadata, current version expectations,
Changelog, and Release-candidate documentation to prepare `v0.17.0` without
product behavior changes. The maintainer subsequently published `v0.17.0` on
2026-08-25 at `8187fbe`, and Issue #199 performs only the post-publication
documentation synchronization. Issues #182 through #196 are the functional
milestone; Issues #197, #198, and #199 add no product functionality.

The historical published `v0.15.0` GitHub Release has
release theme "Local EuroSkat 36er Match capture, analysis, and exports" and
GitHub Release title
"v0.15.0 — Local EuroSkat 36er Match capture, analysis, and exports". It points
to commit `ec1c154`. Package version `0.15.0` requires Python 3.13 or newer,
retains Public API contract version `1`, exactly seven Root workflows, and the
one `skat-ai = skat_ai.cli:main` Console Script, contains 63 authoritative
Schemas and 63 Packaged Schema Resources, includes six Session examples,
validates 85 deterministic generated-output scenarios, and passes 6,510 pytest
tests. Issues #160 through #168 complete the functional milestone, Issue #169
completed Release preparation, and Issue #170 synchronized publication status.
Publication was performed manually by the maintainer. GitHub Releases remains
authoritative for publication status; no Package-index or PyPI publication is
claimed.

The Release provides usable manual post-game capture of one EuroSkat 36er
Standard Match from
descriptive video evidence. Issue #160 provides the internal immutable
Match identity and metadata
foundation. Issue #161 adds internal evidence-aware observed Games, partial and
complete Play validation, free-text Decision commentary on any Player, linked
later responses, and deterministic evidence summaries. Issue #163 adds persistent
internal 36-position Workspaces, exact rotation, passed deals, Progress,
fingerprints, strict Resume, and optimistic atomic Save. Issue #164 adds the
internal transport-free rapid-entry Application foundation, including derived
Position Views, setup updates, automatic Player/Decision append, truncation, and
annotation editing. Issue #165 adds the private local no-JSON browser and Capture
CLI with loopback protection, packaged assets, compare-and-swap autosave, and
explicit conflict Reload. Issue #166 adds editable Match-bound Statistics
Snapshots, strict-before-Match eligibility, existing normalized Profile
derivation, and canonical eligible preparation without policy application. Issue
#167 adds internal information-safe Decision preparation and strict existing-
contract Historical, unpartitioned Training-source, and complete fixed-list
materialization without workflow execution. Issue #168 adds explicit private
one-Decision Position and strict Historical Application execution,
existing-behavior eligible Profile application, no-workflow Match
materialization, deterministic max-eight ephemeral reports, concurrency
invalidation, and authenticated canonical local downloads. It completes the
functional milestone. Issue #169 changed only the Package version, matching
version expectations, Changelog, and current-state documentation to complete
Release preparation. Issue #170 records the subsequent manual publication.
Public Match API and Schema/data workflow, public/persisted Player Catalog,
public/task-specific Dataset workflows, Dataset-v2 persistence,
database/remote deployment, and broader pre-v1
work remain open. That published `v0.15.0` baseline keeps Persistence, Public
APIs, CLI contracts, seven Root workflows, 63 Schemas, examples, and 85 generated
outputs unchanged.

The historical published `v0.14.0` Release has release theme "End-to-end Live
and Retrospective Session capture" and GitHub Release title
"v0.14.0 — End-to-end Live and Retrospective Session capture". It points to
commit `d5589f8`, contains 63 authoritative Schemas and 63 Packaged Schema
Resources, includes six Session examples, validates 85 deterministic generated-
output scenarios, and passes 5,892 pytest tests. Issues #150 through #157
complete its functional milestone, Issue #158 completed Release preparation,
and Issue #159 synchronized its publication status.

The historical published `v0.13.0` release has release theme "Stable API,
installable tooling, and public field provenance" and GitHub Release title
"v0.13.0 — Stable API, installable tooling, and public field provenance". It
points to commit `abd1ad3`, contains 62 authoritative Schemas and 62 Packaged
Schema Resources, validates 77 deterministic generated-output scenarios, and
passes 5,399 pytest tests. Issues #137 through #147 complete its functional
milestone, Issue #148 completed Release preparation, and Issue #149 synchronized
its publication status.

The historical published `v0.12.0` release has release theme
"Fixed-three-player historical lists and deterministic dataset preparation" and
GitHub Release title
"v0.12.0 — Fixed-three-player historical lists and deterministic dataset
preparation". It points to commit `bbf955e`, validates 70 deterministic
generated-output scenarios, and passes 4,762 pytest tests. Issues #127 through
#134 complete the functional milestone, and Issue #135 completed release
preparation. Issue #136 synchronized the historical publication status.

The historical published `v0.11.0` release, with release theme "Information-safe
Replay Coaching and structured historical outcomes", points to commit `cfd28e5`,
validates 64 deterministic generated-output scenarios, and passes 4,392 pytest
tests. Issues #118 through #124 complete that functional milestone, and Issue
#125 completed release preparation.

The historical published `v0.10.0` release points to commit `b4c8738`, validates
59 deterministic generated-output scenarios, and passes 4,075 pytest tests.

The historical `v0.11.0` package baseline adds an immutable 61-case normative settlement
matrix and the bounded historical sequence of at most one continuation followed
by normal completion or one supported terminal shortening. Existing terminal
adjudicators remain authoritative. Direct, bounded, compatibility-only legacy,
undecided, and excluded scopes are explicit. Current structured endings include
declarer and defender concessions, accepted declarer-card exposure, bounded
defender open play, and open-card throwing. Defender-open-play proof remains
bounded to five unresolved tricks, and open-card-throw exclusion remains jack-
only. General claims, specific-trick claims, generalized correction, broader
settlement, and complete official-rule coverage remain incomplete.

Replay Coaching builds decision-time evidence before attaching the observed card
as retrospective evidence rather than ground truth. Search-first impact follows
Contract success, settlement score, then Suit/Grand card-point margin; Null has no
margin objective. Forced and aggregate-equivalent decisions are non-errors, and
Immediate-only evidence remains explicitly bounded to one-trick analysis.
Deterministic Key Decisions, separate decision-opportunity and recorded-outcome
Turning Points, two-occurrence one-game patterns, and deterministic decision and
pattern recommendations make no tactical, causal, psychological, skill, or
statistical-significance claims.

The opt-in historical-game command `--historical-replay-coaching` emits the full
`historical_replay_coaching_summary`, validated by
`historical_replay_coaching.schema.json`. It reuses `--search-seed`,
`--search-budget-profile`, `--samples`, and `--seed`, and can run alone or in one
pass with Historical Search Review. JSON retains the complete report while CLI
output stays concise; `--quiet` behavior is unchanged. Three deterministic public
scenarios cover normal Grand, Null, and a shortened chain.

Final outcome context describes how the recorded game ended. It is not decision-
time evidence and does not change Coaching classification. Public Coaching output
does not expose hands, final hidden ownership, Skat identities, discards,
compatible-world identities or contents, private Search states, derived seeds,
caches, branches, principal variations, ratings, or rankings. Aggregate world
counts and coverage remain privacy-safe evidence metadata. Player, role, phase,
and contract summaries are descriptive counts, not rankings.

The published `v0.10.0` milestone adds five structured game-shortening forms,
five matching historical terminal events, two historical non-terminal continuations, and
variable-length decision snapshots, Historical Review, training samples, and
shortened-game opponent workflows. Declared-Ouvert decisions use exact public
declarer ownership in supported recommendation paths. See
[Historical games](docs/historical_games.md),
[Historical game review](docs/historical_game_review.md), and
[Shortened historical opponent workflows](docs/shortened_historical_opponent_workflows.md).

Multi-Step preserves one coherent hypothetical hidden world per path, while
Policy Comparison gives independent path copies of one shared root. Exact
evidence-constrained inference counts and samples uniformly weighted labeled
assignments compatible with public ownership and confirmed failure-to-follow
evidence. These worlds do not prove the real deal, and confidence is not
calibrated. See
[Coherent hidden-world simulation](docs/coherent_hidden_world_simulation.md) and
[Hidden-card inference](docs/hidden_card_inference.md).

Issue #203 classifies all nine concrete canonical phases. The three former gaps
complete an already started Trick by simulating only its missing opponent Cards,
preserve the already played local Card and local remaining hand, then continue
from the exact winner through existing opponent preparation. Completion and
preparation consume no local step; the first new local Decision remains index
`0`. See [Canonical Multi-Step phase coverage](docs/canonical_multi_step_phase_coverage.md).

Bounded Search supports flat post-game comparison, Historical Search Review,
and deterministic Search-versus-Immediate dataset evaluation with immutable
named work profiles. Independent Suit, Grand, and Null fixtures demonstrate
strict improvements and 32/64/128-draw convergence against exhaustive references.
It provides exact compatible-world counts, canonical enumeration, deterministic
uniform IID sampling with replacement and retained duplicate weighting, and
common completed-world-prefix aggregation. Exhaustive results are exact across
all compatible worlds; sampled and partial exactness claims are limited to their
selected draws or completed prefix.

Search remains bounded late-game determinization with a five-remaining-trick
implementation maximum. It is subject to Strategy Fusion, is not an optimal
imperfect-information policy or complete-contract Search, and exact compatible-
world counts do not identify the real deal. Sampled ownership quality is not
calibrated probability. Bounded-Search and Information-set Search benchmark
timings are separate local reference measurements rather than cross-machine
guarantees, and wall-clock timeout activation is machine-dependent. Overbid Null remains outside normal Search when no external
replacement is available. Immediate remains the omitted default and Search is
opt-in, so existing omitted-method workflows require no migration.

Issues #187 and #188 add a separate three-remaining-Trick foundation and bounded
executor for information-set-consistent Search. They pair selected exact Worlds
with public history, derive actor-own-hand/public-fact Observations, fix `left`
and `right` to separate deterministic Policies, preserve sampled duplicates, and
require one common action for equal `me` Observations.

Issue #189 adds strict flat `information_set_search` with exactly nine settings.
Effective fixed Policies derive from existing left/right policy settings;
`random_legal` and role-invalid Policies produce explicit unavailability. Live
execution has no baseline or fallback. Flat Post-game Review, separate Historical
Review, and Training Dataset-v1 evaluation compare the retained Result with PIMC
on the exact same selection and with independently seeded Immediate before the
actual Card is attached. Comparisons are descriptive, not accuracy or truth
claims. Public Results and opt-in Provenance omit exact Worlds, private hands,
Observations, the controlled Policy table, caches, and derived seeds. Existing
`auto` remains PIMC first with its existing Immediate fallback. See
[Information-set Search contracts](docs/information_set_search_contracts.md),
the [Information-set Search executor](docs/information_set_search_executor.md),
and [Information-set Search workflows](docs/information_set_search_workflows.md).

Issue #190 adds strict Multi-Step and Policy Comparison integration version `1`.
Each local decision derives a domain-separated child seed, executes fresh Search
from current public state, and keeps the coherent execution World private and
independent. Search Worlds and controlled Policies are never reused across
decisions. A no-recommendation Result stops without fallback. Policy Comparison
appends the method exactly once and last to the default four policies, preserves
one shared coherent root with independent path copies, keeps a stopped row
visible but ineligible under existing ranking, and exposes only safe nested
Results and 16-field compact diagnostics. Existing `auto`, flat, Historical, and
Dataset behavior is unchanged. See [Information-set Search Multi-Step and Policy
Comparison](docs/information_set_search_multi_step_and_policy_comparison.md).

Issue #203 preserves that Search boundary across every canonical phase. Existing-
Trick completion occurs first in the private coherent World; Search begins only
at the resulting public local Decision and receives no coherent ownership.

Issue #191 adds strict one-Decision Match execution through the existing Position
Application exactly once, exact Report-source transfer, minimized
Current-Snapshot Strategy Teacher Evidence, Dataset-v2 joins, cross-game method
counts, and existing local Corpus workflow support. Effective time-safe Profile
policies become fixed Search policies without weighting Worlds. Partial, timeout,
and unavailable Results do not fall back. See
[Match Information-set Search and Strategy Teacher Evidence](docs/match_information_set_search_and_strategy_teacher.md).

Issue #192 adds a separate Historical Information-set Replay Coaching path. It
uses complete Information-set Candidate aggregates as primary evidence, retains
same-selection PIMC and independent Immediate only as diagnostics, marks
incomplete Search Decisions not assessable except for factual forced moves, and
reuses the existing deterministic Key Decision, Turning Point, pattern,
Guidance, and Outcome Context algorithms. Match Historical analysis exposes the
Information-set Review and Coaching controls through one Application invocation;
eligible time-safe Profiles affect fixed left/right Policies but never weight or
select Worlds. The existing bounded-PIMC Replay Coaching path is unchanged. See
[Information-set Replay Coaching and Match Historical analysis](docs/information_set_replay_coaching_and_match_historical_analysis.md).

Issue #193 adds a strict eight-case synthetic benchmark corpus, frozen
functional and structural signatures, same-selection PIMC and independent
Immediate diagnostics, Strategy-Fusion and duplicate-weight checks, and local
reference timings. It changes no executor, runtime route, Profile, public
contract, Schema, example, or generated scenario. See [Information-set Search
performance](docs/information_set_search_performance.md).

Issue #194 adds deterministic structural tactical observations for every
recorded Historical Card. Decision-time legal-choice counts remain separate from
the retrospective actual Card and optional completed-Trick outcome. The exact
lead, void-response, Trick-control, Defender-partnership, hand-shape, and outcome
taxonomy makes no quality, intent, signaling, communication, or causal claim.
Existing Replay Coaching remains byte-compatible when the new option is omitted.
See [Tactical motif evidence](docs/tactical_motif_evidence.md).

Issue #195 reuses the exact detector through
`build_tactical_decision_observation_from_snapshot_v1()` for every safely
reconstructable observed Decision in explicit Current Match Snapshots and emits
an explicit skip otherwise. It adds exact occurrence, distinct-Game, distinct-
Match, Player, scope, and bounded recurrence Counts, but no trait, rate, quality,
correctness, significance, intent, communication, causal, or Coaching inference.
The Human, Strategy Teacher, and Tactical families remain separate; Dataset
version `2` remains unchanged. See [Learning Corpus Tactical Motif evidence and
summaries](docs/learning_corpus_tactical_motif_evidence_and_summaries.md).

Issue #200 freezes the bounded v1 scope. Public Match/Corpus/Dataset-v2 surfaces, derived persistence, broader Player Ratings and tactical-quality claims,
and cross-machine latency guarantees are not technical-ledger v1 requirements. That completed ledger did not require Session GUI work; Issue #209 later adds
unified local frontend implementation as required B-09 remediation outside the 53 rows. Broader solver, auction, learned-model, and hosted/remote work is
post-v1. The
Issue #201 [official-rule evidence](docs/v1_official_rule_evidence.md) closes the
R-01/R-06 evidence gate B-01 without product-code change. Issue #202 closes B-02
with mandatory internal end-to-end Provenance enforcement and makes P-10 and
P-13 `satisfied`. Issue #203 completes canonical Multi-Step phase coverage,
makes P-19 `satisfied`, and closes B-03. Issues #204 through #207 subsequently
close B-04, B-08, B-05, and B-06. The remaining v1 blockers are maintainer user
acceptance testing and Package `1.0.0` Release preparation. Issue #204 applies
the approved `AGPL-3.0-only` Package license and
closes B-04 without product behavior or active branding changes. The
approved party-wide all-remaining-
Tricks Claim now has
  private structured contracts, complete Evidence, exact-state preparation,
  bounded exhaustive proof execution, valid-proof adjudication, and Historical-
  only Final Settlement runtime integration with strict public diagnostic output,
  Provenance, CLI, Review/Coaching, Dataset, list, and statistics compatibility.
  Flat Position, Session, Match Capture, and Corpus Claim entry are accepted v1
  limitations.
  Specific future-Trick Claims, defender-open-play proof beyond five
unresolved Tricks, multiple continuation events, arbitrary event streams, and
the other documented durable v1 Claim exclusions are `not_supported_v1`.
Historical end reasons outside the supported set remain unsupported. Current
recommendations, opponent policies, and confidence are heuristic; no learned
model or model-training workflow is included. The product supports fixed
three-player tables only; four-player tables are excluded, and complete official
rule coverage is not claimed.

The published `v0.12.0` package baseline implements the bounded historical-list
source, aggregation, comparison, and public JSON/CLI workflow from Issues #127 through
#130. Issues #131 through #133 implement the retained preparation contracts and
mode-specific generators; Issue #134 exposes fixed mode dispatch through strict
JSON, schemas, CLI, three examples, and three appended generated-output
scenarios. Issue #135 completed release preparation before manual maintainer
publication. Issue #137 is the first implemented `v0.13.0` foundation: it adds
API contract version `1`, exact public exports, immutable JSON Request and Result
wrappers, compatibility metadata, stable public errors, and unchanged legacy
Root CLI behavior. Issue #138 adds the internal version-1 field-provenance
contract foundation with RFC 6901 paths, immutable sidecar ledgers, coverage,
dependency, context-use, redaction, and serialization contracts. Issue #139 adds
internal all-seven-workflow Application orchestration. Issue #140 adds the
executable public facade, direct immutable options, public results and artifacts,
lazy schema validation, and stable boundary errors. Issue #141 adds explicit
Setuptools build metadata, byte-identical packaged Schema resources, `py.typed`,
Package `__version__`, Wheel/sdist inspection, and clean installation gates.
Issue #142 adds installed CLI contract version `1`, the exact `skat-ai` Console
Script, `python -m skat_ai`, a Package-owned canonical implementation, Legacy
Root compatibility, and clean-install CLI/API parity. Issue #143 adds internal
live Position provenance enforcement across Immediate, Search, Hidden-card
inference, Multi-Step, and Policy Comparison while preserving every public
surface. Issue #144 extends the same internal sidecars through flat
retrospective Position Analysis, Historical Snapshots and Review, Historical
Search Review, Replay Coaching, and selected partial-legacy Result branches.
Issue #145 propagates complete internal field provenance through all five
Training Dataset operations, automatic Dataset Preparation, Opponent Statistics
and Profiles, fixed-three-player list aggregation, and independent-list
comparison, with complete non-legacy Root ledgers. Complete non-legacy Position
and base Historical Result ledgers are completed by Issue #146 from retained
workflow values, including scoring, Settlement, endings, Historical replay, and
private-proof-safe dependencies. Issue #147 adds public field-provenance contract
version `1`, immutable public attachments/artifacts/bundles, seven explicit Root
Result mappings, one actual-artifact mapping, opt-in Public API and all-three-
form CLI transport, strict `field_provenance.schema.json`, and seven append-only
generated-output scenarios. The published `v0.13.0` release matrix has 77
scenarios and 62 schemas. Together, Issues #137 through #147 define the
published baseline with 77 scenarios and 62 schemas; the historical published
`v0.12.0` facts remain 70 scenarios and 4,762 pytest tests. Issue #148 completed Release preparation before
manual maintainer publication at commit `abd1ad3`. Broader end-to-end field-level
enforcement remained incomplete at that baseline and is completed internally by
Issue #202 without widening public Provenance.

The published `v0.14.0` milestone begins with Issue #150's immutable internal
Session contract foundation, Issue #151's deterministic transition engine,
Issue #152's canonical Retrospective Historical Request export, and Issue #153's
information-safe Position Request export and Decision Checkpoints. Issue #154
adds deterministic strict-prefix Undo, one-command correction, suffix replay,
partial corrected States, and Checkpoint lineage. Issue #155 adds private
internal Session Persistence version `1`, strict reconstruction/replay and
fingerprint verification, caller-supplied frozen Checkpoint retention with
recomputed lineage, optimistic expected-content-fingerprint writes, and canonical
atomic local file replacement.
Issue #156 adds the stable `skat_ai.api.v1.session` namespace, exact immutable
contract exports, all ten in-memory operations, public Command parsing, the
Session Result envelope, optional complete Session Provenance, strict standalone
Session Schema, 63-Schema Package Resource parity, and clean-install validation.
Session and Command version `1`, transition and projection version `1`, stable
Players, Capture Modes, typed Commands, an authoritative accepted Log, full
replay, atomic application, monotonic phases, incremental validation, Diagnostics,
export readiness, immutable export Results, exact Historical and information-safe
Position mapping, declared-Ouvert public-hand capture, canonical Request
construction, frozen local pre-Play Checkpoints, and internal history editing now
exist. Private file persistence and public in-memory persistence construction and
strict resume also exist. Issue #157 adds the stable public Session file
namespace, accepted-Log Decision Observation and isolated Checkpoint review
export, automatic exact Checkpoint collection, all 12 installed/module/Legacy
Session subcommands, explicit Position/Historical execution, the phase-aware
Assistant, six examples, and eight append-only scenarios for a total of 85.
Issue #158 completed Package version `0.14.0` and Release-documentation
preparation under the release theme "End-to-end Live and Retrospective Session
capture" without changing product behavior. The maintainer subsequently
published `v0.14.0` at commit `d5589f8`; its baseline has 63 Schemas, six Session
examples, 85 generated outputs, and 5,892 passing pytest tests. The historical
published `v0.13.0` baseline remains 62 Schemas and 77 scenarios. GUI/browser
UI, online-platform adapters, browser
extensions, website scraping, cloud synchronization, distributed locking,
encryption/key management, automatic backups, and unrelated pre-v1 gaps remain
open.
Issue #209 later approves the local Session browser integration only as part of
the unified frontend B-09 remediation; the other listed layers remain open.

The current working Package `0.17.0` opens the unified local shell for bare
installed, module, and Legacy invocation and supports explicit `skatmind app`.
It creates only the managed data root and category directories on startup;
managed contents are discovered only when a stateful area is opened.
Issue #211 adds process-local guided analysis/Review, the bounded
normal-completion Historical editor, strict optional JSON transfer, and readable
Results without implicit persistence. Issue #212 adds managed Session, Match, and
Learning lifecycles through the same authenticated server while preserving
existing persistence and standalone advanced interfaces. `run` and final top-
level help remain Issue #213 work. See [Guided analysis and Results](docs/unified_local_frontend_guided_analysis_and_results.md)
and [Managed stateful workflows](docs/unified_local_frontend_stateful_workflows.md).

Issue #159 synchronized the historical `v0.14.0` publication status. The
published `v0.15.0` milestone covers usable EuroSkat 36er Standard post-game
capture. Issue #160 establishes internal Match
metadata, and Issue #161 adds
internal evidence-aware observed Games and free-text Decision commentary. Issue
#163 adds private persistent Workspaces, and Issue #164 adds transport-free rapid
entry over those Workspaces. Issue #165 adds the private local browser/Capture
CLI and autosave transport. Issue #166 adds Match-bound Snapshot editing and
time-safe Profile preparation. Issue #167 adds internal Decision preparation and
strict Historical, unpartitioned Training-source, and complete fixed-list
materialization without execution. Issue #168 adds explicit private analysis,
existing-behavior Profile application, ephemeral reports, and authenticated
local downloads while materialization remains no-workflow. Public Match API and
Schema/data workflow, public/persisted Player Catalog, public/task-specific Dataset workflows,
database/remote deployment, and broader pre-v1 work remain open. `v1.0.0`
remains unready after this milestone; its final Issue sequence and implementation
architecture still require focused scope and traceability review.

Issue #169 completed Release preparation, the maintainer published `v0.15.0`
manually at commit `ec1c154`, and Issue #170 synchronized publication status.

The historical published Package milestone `v0.16.0 — Learning-ready behavior
and communication data` remains the origin of Issue #171's private internal content-addressed Match
Snapshot, Player Observation, observed-Game fingerprint, Snapshot-scoped
reference, lightweight Catalog, explicit current-selection, and duplicate/
revision-classification foundation. Issue #172 adds deterministic private Corpus
persistence, strict Store Resume and orphan reporting, immutable no-clobber
objects, optimistic atomic Catalog Save, strict Workspace-file import, and
persisted explicit Current-selection updates. Issue #173 adds the private
derived Current-Snapshot-only Player Catalog, exact alias conflicts, retained
multi-Match Statistics history, and strict time-safe as-of selection. Issue #174
adds minimized exact human Commentary and linked Response evidence from Current
Snapshots only, plus deterministic canonical in-memory export. Issue #175 adds
Current-Snapshot-bound method-specific Strategy Teacher Evidence from exact
executed Decision Analysis Reports, with exact source and semantic identities,
strict no-execution reconciliation, deterministic counts, and canonical in-memory
export. Issue #176 adds the private Current-Snapshot-only, unpartitioned,
task-neutral Learning Dataset version `2`, with information-safe Decision State,
separate observed behavior and Player Context, exact Teacher/Commentary/Response
joins, skipped and unjoined evidence reporting, deterministic identities, and a
canonical path-free export. Issue #177 adds internal group-safe Dataset-v2
partition Plans, fixed Known-player and unseen-player algorithms, leakage
audits, index-only views, and canonical export. Issue #178 adds private
deterministic exact-Count cross-game Match, Player, Communication, Strategy
Teacher, Coverage, Dataset Readiness, and supplied Partition Readiness summaries
plus canonical path-free export. Issue #179 completes the functional private
local workflow with the separate `corpus` CLI/browser, strict Workspace and
executed-Decision Report-source uploads, explicit Current selection, bounded
process-local sources, exact no-execution artifact preparation, minimized
presentation, and seven authenticated canonical downloads. Issue #180 changed
only Package version and current expectations, Changelog, and Release-state
documentation to prepare `v0.16.0`. The maintainer published the Release
manually on 2026-08-18 at commit `91b1360`, and Issue #181 synchronizes
publication status. Deletion and
garbage collection, persisted alias assertions, Player merge/split operations,
all-revision Player views, Human and Strategy Teacher Evidence persistence/public
transport, automatic Report capture, Historical Report import, Dataset-v2
persistence and persisted partition artifacts, separate behavior and
communication task builders, communication-aware annotations, evaluation,
ratings, derived AI tags, public API/Schema exposure, and model training remain
open. No production model is included.

The `v0.17.0 — Rules, Search, Coaching, and performance closure` functional
milestone is complete through Issue #196. Issue #182 closes the Claim product-
decision gate.
Issue #183 adds private
version-1 structured Claim, exact Evidence, exact-state, Proof Request,
preparation, assignment, diagnostic-line, and Result contracts without proof or
Runtime execution. Issue #184 adds the private bounded exhaustive exact AND/OR
  proof executor without Runtime behavior. Issue #185 adds private valid-proof
  adjudication and existing Final Settlement composition while preserving normal
  no-outcome Results for invalid and unavailable proofs. Issue #186 updates
  Matrix version `3` without changing its 61 cases and completes the Historical-
  only approved Claim and Final Settlement runtime slice. All other current Claim
  boundaries remain durable v1 exclusions. Session, Match Capture, and Corpus
  Claim entry remain open. Issue #187 defines the private information-set Search
  contracts and no-execution Preparation foundation, and Issue #188 adds its
  private bounded executor. Issue #189 adds strict flat routing, descriptive
  retained-selection Post-game comparison, separate Historical Review and
  Training Dataset evaluation, safe output, Provenance, CLI, four Schemas, one
  example, and four scenarios. Issue #190 adds strict Multi-Step and Policy
  Comparison integration, one example, and two scenarios. Issue #191 adds strict
  one-Decision Match Capture and Reports, exact source transfer, focused Strategy
  Teacher/Dataset evidence, Summary counts, and existing Corpus workflow support
  without changing those counts. Issue #192 adds separate Information-set Replay
  Coaching, Match Historical Information-set Review/Coaching, one Schema, one
  example, and two scenarios, bringing the working baseline to 70 Schemas and 96
  scenarios. Issue #193 adds repository-local Information-set Search benchmark
  evidence without changing those counts or product surfaces. Issue #194 adds
  deterministic Historical Tactical Motif Review, one Schema, one example, and
  two scenarios, bringing the working baseline to 71 Schemas and 98 scenarios.
  Issue #195 adds separate private Current-Snapshot Tactical Motif Evidence,
  descriptive cross-game summaries, atomic browser preparation, and two more
  downloads without changing those counts or Dataset version `2`. Issue #196
  adds exact Tactical/Teacher joins, deterministic complete-Search-only repeated
  cross-Game Coaching, atomic third-family publication, and a tenth download
  without changing those counts or Dataset version `2`. Issue #193 satisfies the
  bounded v0.17.0 performance-evidence contract. Issue #200 accepts deterministic
  functional/structural performance for v1, classifies latency guarantees and
  broader tactical/Rating work as not required, and identifies broader internal
  Provenance as a blocker. Issue #202 subsequently closes that blocker without
  widening public Provenance. Issues #182 through #196 are the
  frozen functional history. Issue #197 completes the documentation-only scope
  and Release-readiness audit, and Issue #198 prepares Package `0.17.0` and the
  Release candidate without product behavior changes. The maintainer published
  `v0.17.0` on 2026-08-25 at `8187fbe`, and Issue #199 synchronizes the
  publication without product functionality. Issue #200 freezes the bounded
  `v1.0.0` scope, seven blockers, and the exact #201 through #207 sequence. The
  Issue #201 independent official-rule oracle closes R-01, R-06, and B-01
without product-code change. Issue #202 closes B-02 and makes P-10 and P-13
  `satisfied`. Issue #203 completes all nine concrete canonical Multi-Step
  phases, makes P-19 `satisfied`, and closes B-03. Issue #204 applies the exact
  `AGPL-3.0-only` Package boundary and closes B-04. Issue #205 completes the
  hard-cut SkatMind Package, import, CLI, resource, Schema, identifier, and strict
  legacy persisted-input migration boundary, makes P-09 `satisfied`, and closes
  B-08. Issue #206 declares the exact direct runtime dependencies, adds the
  source/Editable/Wheel/sdist resolved matrix plus minimum Wheel/sdist evidence,
  makes P-34 `satisfied`, and closes B-05 after both merged Ubuntu jobs pass.
  Issue #207 completes the final technical audit, finds no material technical
  blocker, and closes B-06. The separate B-09 maintainer-UAT Gate sits outside
  the 53-row ledger. Issue #208 then starts UAT; UAT-01 fails with three accepted
  findings, and UAT-02 through UAT-12 are paused. Issue #209 freezes the approved
  unified local frontend contract. Issue #210 implements the application shell,
  Issue #211 adds guided analysis, Historical Review, and readable Results, and
  Issue #212 adds managed Session, Match, and Learning workflows.
  UAT-FINDING-001 remains open pending repeated UAT, and Issue #212 implements
  the Product work owned by UAT-FINDING-003. Issue #213 is next. B-09 and B-07 remain open, Release
  preparation is not ready, and no v1 Release title, theme, date, tag, or
  publication commit is frozen.

Current support and known limitations are tracked in the
[requirements traceability matrix](docs/requirements_traceability.md). Product
scope and completion gates are defined in the [v1.0 scope](docs/v1_scope.md).
The required-row classifications are in the [scope and traceability
audit](docs/v1_0_scope_and_traceability_audit.md); the current conclusion is in
the [final technical Release-readiness audit](docs/v1_0_final_technical_release_readiness_audit.md).
The local Product entry is documented in the [application shell](docs/unified_local_frontend_application_shell.md),
the current Analyze/Review behavior is in [Guided analysis and Results](docs/unified_local_frontend_guided_analysis_and_results.md),
the managed Session/Match/Learning behavior is in [Managed stateful workflows](docs/unified_local_frontend_stateful_workflows.md),
and the remaining UAT remediation architecture is in the [unified local frontend contract](docs/unified_local_frontend_contract.md).
The Historical integration is documented in [Historical party-wide
  Claim](docs/historical_party_wide_claim.md). The private boundary is documented in [Party-wide Claim
  contracts](docs/party_wide_claim_contracts.md), the [Party-wide Claim proof
  executor](docs/party_wide_claim_proof_executor.md), and [Party-wide Claim
  adjudication](docs/party_wide_claim_adjudication.md).
Historical tactical observations are documented in [Tactical motif
evidence](docs/tactical_motif_evidence.md).
Their private Corpus Evidence and cross-game descriptive summaries are documented
in [Learning Corpus Tactical Motif evidence and summaries](docs/learning_corpus_tactical_motif_evidence_and_summaries.md).
The frozen functional scope and Release-readiness decision are documented in the
[v0.17.0 scope and Release-readiness audit](docs/v0_17_release_readiness_audit.md).

## License

License: GNU Affero General Public License v3.0 only

SPDX: `AGPL-3.0-only`

Copyright: `Copyright (C) 2026 Henning Wiese`

See [LICENSE](LICENSE), [COPYRIGHT](COPYRIGHT), and the focused
[v1 Package license](docs/v1_package_license.md) decision, dependency/asset
audit, metadata contract, and network-use boundary.

## Disclaimer

This project is not a full official Skat rules engine, tournament system, general
hidden-information solver, or complete-contract solver.

It is intended as an experimental analysis and simulation tool.
