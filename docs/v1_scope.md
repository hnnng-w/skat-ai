# v1.0 scope

This document defines the product requirements and observable completion gates
for `skat-ai` `v1.0.0`. Current implementation status remains in
[Requirements traceability](requirements_traceability.md).

The current published stable and latest stable GitHub Release is `v0.17.0`, with
Release theme "Rules, Search, Coaching, and performance closure" and GitHub
Release title "v0.17.0 — Rules, Search, Coaching, and performance closure". The
maintainer published it manually on 2026-08-25 at commit
`8187fbe684559f9c0c2ba444be1bf33950359ad2` (`8187fbe`). Package version
`0.17.0` requires Python `>=3.13`, retains Public API contract version `1`, seven
Root workflows, and one Console Script. The published baseline has Matrix version
`3` with 61 cases, 71 authoritative and packaged Schemas, six Session examples,
98 generated outputs, ten private Corpus prepared downloads, and 7,479 passing
pytest tests in 921.96s. GitHub Releases is the authoritative publication record;
no Package-index or PyPI publication is claimed.

The historical published `v0.16.0 — Learning-ready behavior and communication
data` baseline was published manually on 2026-08-18 at commit `91b1360`. It has
63 authoritative and packaged Schemas, six Session examples, 85 generated
outputs, and 6,925 passing pytest tests in 1083.48s. Issues #171 through #179
complete that functional milestone, Issue #180 completed Release preparation,
and Issue #181 synchronized publication status without product functionality.

The published `v0.17.0` functional history uses Package version `0.17.0`, Python
`>=3.13`, Public API contract version `1`, seven Root workflows, one Console
Script, and six Session examples. Issue #186 updates the Settlement Normative
Matrix to version `3` with the same 61 cases, completes the approved Claim
through Historical Game input only. Issue #189 adds four Information-set Search
Schemas, one example, and four generated-output scenarios. Issue #190 adds strict
Multi-Step and Policy Comparison integration, one example, and two scenarios
without adding a Schema, bringing the working totals to 69 authoritative and
packaged Schemas and 94 scenarios. The published `v0.16.0` facts above remain
unchanged.

Issue #191 adds strict private one-Decision Match Information-set Search, exact
Report-source transfer, focused Strategy Teacher Evidence, Dataset-v2 joins,
cross-game counts, and existing Corpus workflow support without changing those
counts or public/versioned surfaces.

Issue #192 subsequently adds separate Information-set Replay Coaching, private
Match Historical Information-set Review/Coaching, one strict Schema, one Root
example, and two append-only scenarios. The Issue #192 point-in-time totals are 70
authoritative and packaged Schemas and 96 scenarios. Package version, Public API
contract, seven Root workflows, one Console Script, Settlement Matrix version
`3` with 61 cases, and six Session examples remain unchanged.

Issue #193 adds a deterministic synthetic Information-set Search benchmark
corpus, a strict repository-local runner and focused regression tests, and
documented local reference measurements. It changes no production code, Schema,
route, profile, Public API, Package version, example, generated scenario, or the
working counts above.

Issue #194 adds deterministic Historical Tactical Motif Review, private Match
browser controls, one strict Schema, one Root example, and two append-only
scenarios. The final published totals are 71 authoritative and packaged Schemas
and 98 scenarios. Existing Package/API/workflow/Console-Script/Settlement/
Session baselines remain unchanged.

Issue #195 adds private Current-Match-Snapshot-only Tactical Motif Evidence,
explicit Decision skips, exact descriptive cross-game summaries, atomic process-
local Corpus preparation, minimized presentation, and two authenticated
downloads. It changes no Package/API/workflow/Console-Script/Schema/example/
generated-scenario/Session/Dataset-v2 baseline, so those working totals remain
unchanged.

Issue #196 adds private deterministic Tactical Cross-game Coaching and a tenth
authenticated download. It changes no Package/API/workflow/Console-Script/
Schema/example/generated-scenario/Session/Dataset-v2 baseline, so the current
working totals remain 71 authoritative and packaged Schemas, six Session
examples, and 98 scenarios.

Issue #197 records the documentation-only scope and Release-readiness audit.
Issue #198 changes only Package metadata, current version expectations,
Changelog, and Release-candidate documentation. The maintainer subsequently
published `v0.17.0` on 2026-08-25 at `8187fbe`, and Issue #199 synchronizes that
publication without product functionality. Issues #182 through #196 are the
functional milestone; Issues #197, #198, and #199 add no product functionality.

The historical published `v0.15.0` Release points to commit `ec1c154`. Package
version `0.15.0` requires Python 3.13 or newer, retains Public API contract
version `1` and exactly seven Root workflows, and contains 63 authoritative
Schemas, 63 Packaged Schema Resources, six Session examples, 85 deterministic
generated-output scenarios, and 6,510 passing pytest tests. Issues #160 through
#168 complete the functional milestone, Issue #169 completed Release
preparation, and Issue #170 synchronized publication status.

The historical published `v0.14.0` Release points to commit `d5589f8`. Its
Package baseline contains the same 63 authoritative and packaged Schemas, six
Session examples, and 85 generated-output scenarios, and passed 5,892 pytest
tests. Issues #150 through #157 complete that functional milestone, Issue #158
completed Release preparation, and Issue #159 synchronized publication status.

The historical published `v0.13.0` baseline at commit `abd1ad3` contains 62
authoritative Schemas and 62 Packaged Schema Resources, validates 77
deterministic generated-output scenarios, and passes 5,399 pytest tests. Issues
#137 through #147 complete its functional milestone, Issue #148 completed Release
preparation, and Issue #149 synchronized its publication status.

The historical published `v0.12.0` release points to commit `bbf955e`, validates
70 deterministic generated-output scenarios, and passes
4,762 pytest tests. Issues #127 through #134 complete the functional milestone,
and Issue #135 completed release preparation. Issue #136 synchronized the
historical publication status.

The historical published `v0.11.0` baseline validates 64 deterministic generated-
output scenarios and passes 4,392 pytest tests. Issues #118 through #124 complete
that functional milestone, and Issue #125 completed release preparation. The
historical published `v0.10.0` baseline remains evidence for 59 scenarios and
4,075 pytest tests.

The published `v0.13.0` baseline establishes public
API contract version `1`, exact stable namespaces and exports, immutable JSON
Request and Result wrappers, compatibility and version metadata, stable public
errors and Exit Codes, and unchanged legacy Root CLI behavior. Issue #139 adds
internal Application orchestration version `1`, immutable invocation and option
contracts, generic no-I/O dispatch for all seven Root workflows, all five
Training Dataset operations, injected Opponent Statistics, auxiliary artifacts,
and legacy CLI transport parity. Issue #140 adds public `parse_request`,
`execute`, `execute_document`, and `serialize_result`; direct immutable options;
public execution results and artifacts; lazy source/editable schema validation;
stable boundary errors; and no-I/O execution parity for all seven workflows.
Issue #141 adds explicit Setuptools metadata, private Package Resource schemas,
`py.typed`, Package `__version__`, Wheel/sdist and clean-install validation, and
local/CI distribution gates. Issue #142 adds installed CLI contract version `1`,
the exact `skat-ai` Console Script, `python -m skat_ai`, one Package-owned
canonical implementation, Legacy Root compatibility, and clean-install CLI/API
parity. Issue #138 adds the internal
field-level provenance contract version `1`, immutable sidecar ledgers, RFC 6901
paths, coverage and dependency validation, Information Use Context, public
redaction, and safe serialization. Issue #143 implements internal live Position
propagation and adversarial enforcement. Issue #144 implements internal flat
retrospective Position, Historical Review, Historical Search Review, Replay
Coaching, and selected Position/Historical Result propagation. Issue #145 adds
Dataset, Preparation, Opponent, Profile, historical-list, and comparison
propagation with complete non-legacy Root ledgers. Issue #146 completes non-
legacy Position and Historical Root Result provenance, including result-only
base Historical bundles. Issue #147 adds bounded public field-provenance version
`1`, immutable attachments/artifacts/bundles, seven explicit Root Result
mappings, the actual Opponent Statistics export-artifact mapping, existing-
helper redaction, complete recomputed coverage, default-false API and all-three-
form CLI opt-in, and strict Schema. The published `v0.13.0` baseline has 62
schemas and 77 generated-output scenarios; the seven additions are append-only
and do not rewrite the historical published `v0.12.0` facts.

The published `v0.14.0` milestone provides interactive Live and Retrospective
Session capture. Issue #150 implements the immutable internal Session contract
foundation. Issue #151 implements deterministic internal Command application,
full accepted-Log replay, projection, phase advancement, incremental validation,
and readiness. Issue #152 adds immutable internal available/unavailable Session
Request Export version `1`, exact ready-Retrospective Historical mapping,
canonical builder round trip, and existing `RequestDocumentV1` construction.
Issue #153 adds immutable Position Export Options version `1`, information-safe
Position Request construction, declared-Ouvert public-hand capture, and frozen
replay-verified pre-Play Decision Checkpoints. Issue #154 adds immutable Session
History Edit and Checkpoint Lineage version `1`, strict-prefix Undo, one-command
correction, deterministic first-rejection suffix replay, valid partial corrected
States, and current/ancestor/future/diverged lineage. Issue #155 adds private
Session Persistence document version `1`, deterministic State and content
fingerprints, strict reconstruction and accepted-Log replay, caller-supplied
frozen Checkpoints with recomputed lineage, optimistic expected-fingerprint
`saved`/`unchanged`/`conflict` writes, canonical files, and atomic same-directory
replacement. Session-triggered analysis, actual-card Checkpoint attachment,
public file Save/Load, CLI, examples/generated output, automatic Checkpoint
collection, end-to-end capture, and UI were the remaining gap after Issue #155.
Issue #156 adds stable
`skat_ai.api.v1.session` version `1`, exact immutable exports, ten in-memory
operations, strict Command parsing and Result serialization, optional complete
Session Provenance, standalone Session Schema, 63-Schema Package parity, and
clean-install validation. Issue #157 adds stable public Session file transport,
accepted-Log Decision Observation, isolated Checkpoint review export, automatic
exact Checkpoints, all 12 installed/module/Legacy Session CLI subcommands,
explicit Position/Historical execution, the phase-aware Assistant, six examples,
and eight append-only scenarios. The `v0.14.0` Package baseline therefore has 63
Schemas and 85 generated outputs. Issue #158 completed Package version `0.14.0`
and Release-documentation preparation without changing product behavior. The
maintainer subsequently published the Release manually at commit `d5589f8`.
Session GUI/browser UI, online-platform
adapters, browser
extensions, website scraping, cloud synchronization, distributed locking,
encryption/key management, and automatic backup policy remain open.

The published `v0.15.0` milestone provides usable manual
post-game capture of one EuroSkat 36er Standard Match from descriptive video
evidence. Issue #160 supplies the internal immutable
Match identity and metadata
foundation. Issue #161 adds internal evidence-aware observed Games, exact public
Play validation, free-text Decision commentary, linked later responses, and
derived evidence capabilities. Issue #163 adds persistent internal 36-position
Workspaces, passed deals, Progress, fingerprints, strict Resume, and optimistic
atomic local Save. Issue #164 adds internal transport-free rapid-entry
Application services with Position Views, exact/bounded Card selection, setup
updates, automatic Play derivation, truncation cleanup, annotation editing, and
passed/clear wrappers. Issue #165 adds the private local no-JSON browser and
Capture CLI with strict Resume/browser creation, all 36 positions, rapid Card
and annotation forms, loopback token/same-origin protection, packaged assets,
optimistic autosave, and explicit conflict Reload. `v1.0.0` remains unready
after this focused milestone. Issue #166 adds editable Match-bound Snapshots,
strict temporal eligibility, canonical eligible preparation, and existing
Profile derivation without policy application. Issue #167 adds internal
information-safe Decision preparation, strict normal-completion Historical
materialization, unpartitioned Training source Records, and complete fixed-list
construction plus existing aggregation without workflow execution. Issue #168
adds explicit one-Decision Position and strict Historical Application execution,
existing-behavior eligible Profile application, no-workflow Match
materialization, deterministic max-eight ephemeral reports, concurrency
invalidation, and authenticated canonical local downloads. It completes the
functional local Match Capture milestone. Issue #169 completed Package-version
and Release-documentation preparation without changing product behavior. The
maintainer published the Release manually at commit `ec1c154`, and Issue #170
synchronizes publication status. Public
Match API and Schema/data
workflow, public/persisted Player Catalog, public/task-specific Dataset workflows,
Dataset-v2 persistence,
database/remote deployment, and broader pre-v1 work remain open. `v1.0.0`
remains unready, and its final planning still
requires a separate audit of this document and
[Requirements traceability](requirements_traceability.md).

The historical published Package milestone `v0.16.0 — Learning-ready behavior
and communication data` defines its first private internal foundation in Issue #171: immutable
content-addressed copies of exact Workspace persistence documents, exact Player
Observations, observed-Game fingerprints, Snapshot-scoped closed references,
lightweight Catalog entries, explicit current-Match selections, and non-mutating
duplicate/revision classification. Issue #172 adds one explicit fixed-root
private Store, deterministic Catalog/content fingerprints, strict reconstruction
and full Resume, valid orphan reporting, pure Catalog import and Current-selection
changes, no-clobber objects, optimistic atomic Catalog Save, strict Workspace-file
import, and persisted selection updates. Issue #173 adds a private derived
Current-Snapshot-only Player Catalog, exact aliases/conflicts, complete
Match-bound Statistics history, and strict time-safe selection. Issue #174 adds a
private deterministic Current-Snapshot-only minimized Human Commentary and linked
Response Evidence collection plus canonical in-memory export, without analysis,
Dataset generation, persistence, or public exposure. Issue #175 adds private
Current-Snapshot-bound method-specific Strategy Teacher Evidence from exact
executed Decision Analysis Reports, with one no-execution Request rebuild,
retained Result validation, exact and semantic identities, and canonical in-memory
export. Issue #176 adds a private Current-Snapshot-only unpartitioned Learning
Dataset version `2` with safe/skipped Decision coverage, separate Decision State,
observed behavior, Player Context, Strategy Teacher, Commentary, and linked
Response families, deterministic identities, normalized pools, and canonical
path-free export. Issue #177 adds private Match-group-safe partition Plans,
strict temporal Known-player and Player-component unseen-player algorithms,
complete leakage audits, lossless partition indexes, and canonical path-free
export. Issue #178 adds private deterministic exact-Count cross-game Match,
Player, Communication, Strategy Teacher, Coverage, Dataset Readiness, and
supplied Partition Readiness summaries plus canonical path-free export. Deletion and
garbage collection, Player Catalog persistence, persisted identity assertions,
merge/split operations, all-revision Player views, Human or Strategy Teacher
Evidence persistence and public transport, automatic Report capture, Historical
Report import, Dataset-v2 persistence, separate task-specific behavior/strategy/
communication Features and Targets, annotations, evaluation baselines, ratings,
derived AI tags, and public exposure remain open. No production model is planned.

Issue #179 completes the functional private local Learning Corpus/Dataset-v2
workflow with a separate installed/module/Legacy `corpus` command, one explicit
root, strict Workspace and executed-Decision Report-source uploads, explicit
Current selection, bounded process-local sources, exact no-execution artifact
preparation, minimized loopback presentation, and seven authenticated canonical
downloads. Issue #180 prepared Package version `0.16.0` and current Release
documentation without product behavior changes. The maintainer published the
Release manually on 2026-08-18 at commit `91b1360`, and Issue #181 synchronizes
publication status without product functionality. No
Public API, Schema, Root workflow, derived-artifact
persistence, automatic Report capture, Historical Report import, database/
remote/cloud/collaboration, task builder, taxonomy/tag, evaluation, rating, or
training is added. See
[Learning Corpus browser workflows](learning_corpus_browser_workflows.md).

Issue #195 adds a separate Current-Snapshot-only Tactical Motif Evidence family
and exact descriptive cross-game Summary. Every observed Decision becomes safe
Evidence or an explicit skip; the exact Issue #194 detector is reused; partial
Matches and incomplete final Tricks remain bounded. Exact global, Player, role,
seat, phase, contract, distinct-Game, distinct-Match, and recurrence Counts make
no trait, rate, quality, correctness, significance, communication, causal, or
Coaching claim. Human, Strategy Teacher, and Tactical Evidence remain separate;
Learning Dataset version `2` remains unchanged. The browser atomically publishes
the two additional process-local artifacts with the existing family and exposes
the Issue #195 point-in-time total of nine authenticated downloads. See [Learning
Corpus Tactical Motif
evidence and summaries](learning_corpus_tactical_motif_evidence_and_summaries.md).

The `v0.17.0 — Rules, Search, Coaching, and performance closure` functional
milestone is complete through Issue #196. Issue #182 closes the Claim product-decision gate, and
Issue #183
adds private structured Claim, complete Evidence, exact-state, Proof Request/
preparation, assignment, diagnostic-line, and Result contracts without proof or
Runtime execution. Issue #184 adds private bounded exhaustive exact AND/OR proof
execution without Runtime behavior. Issue #185 adds private valid-proof-only
adjudication, complete assignment and Game Result, and composition through the
existing Final Settlement; invalid or unavailable proof creates no outcome. The
61-case Matrix version `3` marks the approved bounded Claim `supported_as_is`
through Historical Game input only. It remains absent from Runtime
`GameShortening`, flat Position, Session, Match Capture, and Corpus entry, and
every other current Claim boundary remains `not_supported_v1`. Claims and Final
Settlement remain `partially_supported` beyond the bounded implemented slice.
Issue #187 defines the private information-set Search World State, actor
Observation, fixed Policy, Budget, Request, Preparation, controlled-Policy, and
Result foundation. Issue #188 adds its private bounded exhaustive selected-world
best-response executor and prevents Strategy Fusion for controlled Player `me`
over the selected sequence. Issue #189 adds strict flat routing, same-selection
PIMC plus independently seeded Immediate retrospective comparison, separate
Historical Review and Training Dataset evaluation, safe aggregate Results,
retained-stage Provenance, CLI, four Schemas, one example, and four scenarios.
Issue #190 adds strict Multi-Step and Policy Comparison integration with fresh
per-decision public-state Search, private independent coherent execution, no
Search World or Policy reuse, no fallback, safe Results and diagnostics, existing
ranking, and complete Provenance. Existing `auto` remains unchanged. Match
Capture, Match Analysis Reports, and Strategy Teacher are integrated for the
bounded one-Decision path by Issue #191 together with Dataset-v2 and Corpus
propagation. Issue #192 separately adds Match Historical Information-set
Review/Coaching and complete-Candidate-only Information-set Replay Coaching with
diagnostic PIMC/Immediate and no fallback. Issue #193 adds repository-local
benchmark evidence for the unchanged executor. Broader Strategy-Fusion
correction is post-v1.
Issue #194 adds deterministic Historical Tactical Motif Review without changing
either Coaching family. Issue #195 adds separate Current-Snapshot Tactical Motif
Evidence and exact descriptive cross-game Counts without changing Dataset
version `2`. Issue #196 adds separate deterministic Tactical Cross-game Coaching
from exact retained Tactical/Teacher evidence, complete-Search-only consensus,
bounded repeated cross-Game focus and fixed Guidance, and a tenth Corpus download
without changing Dataset version `2`. Issue #200 classifies broader tactical/
Rating work and latency guarantees as not required for v1, accepts deterministic
functional/structural performance, and retains broader internal Provenance as a
blocker. Issue #193
satisfies the bounded v0.17.0 performance-evidence contract. Issues #182 through
#196 are the frozen functional history. Issue #197 completes the documentation-
only audit, and Issue #198 prepares Package `0.17.0` and the Release candidate
without product behavior changes. The maintainer published `v0.17.0` on
2026-08-25 at `8187fbe`, and Issue #199 synchronizes that publication without
product functionality. Issue #200 freezes the bounded `v1.0.0` scope, classifies
every required traceability row, and records seven blockers plus the exact #201
through #207 sequence. Issue #201 adds independent exhaustive official-rule
evidence for R-01 and R-06, closes B-01 without product-code change, and leaves
six blockers B-02 through B-07. The milestone remains not ready, and Issue #202
is next.

The November 2022 ISkO and SkWO publication is the normative source for official
rules and competition behavior. Product capabilities such as simulation,
recommendations, historical data, and opponent modeling are specified here and
must not be presented as official-rule requirements.

## Product concepts

| Concept | Definition for skat-ai | Explicit boundary |
| --- | --- | --- |
| Live position | A position analyzed using only facts legitimately available to the selected player at that decision time. | Post-game skat, future plays, later outcomes, and retrospective labels must be rejected or redacted. |
| Retrospective single-decision review | One historical decision reconstructed with the actual card and facts available at that point, then compared with the engine recommendation. | It is not a complete-game replay. Retrospective facts may explain the result but must not leak into the reconstructed decision analysis. |
| Complete historical game review | All eligible decisions from one complete historical game, independently reconstructed from decision-time snapshots and compared with Immediate or, in the separate Search workflow, bounded Search plus an independent Immediate baseline. | It is not a perfect-information solver, complete-contract optimization, player rating, or training/evaluation record. |
| Complete historical game | One coherent record of the deal, players/seats, final bid and declaration facts, skat handling, ordered play events, end reason, result, and settlement. | A position plus selected completed tricks is not a complete historical game; a full auction sequence is planned after v1.0. |
| Historical game used as training or evaluation data | A complete historical game wrapped in a validated record with provenance, stable identity, intended labels/targets, and explicit dataset partition metadata. | Representation and evaluation use do not imply that a machine-learning model is trained. |
| Externally captured opponent statistics | A versioned record of supplied total games and percentage-point statistics with stable player identity, source provenance, capture time, and deterministic explainable profile derivation. | Explicit live side bindings or strict pre-game historical participant matching may apply confidence-gated actionable presets; external values do not imply exact counts, predict behavior, or learn a profile. |
| Statistics derived from historical player data | Reproducible exact aggregates computed from selected timestamped supported historical dataset games for a stable case-sensitive player identity, with per-player source provenance and reusable export. | Bounded aggregation differs from manually supplied values and learned parameters; it does not weight or merge sources, manage multiple captures, or apply a policy automatically. |
| Rule-based player or opponent profile | Explicit fields and deterministic rules that select or parameterize explainable behavior. | It is not learned from data, even when its input statistics were historically derived. |
| Rolling opponent-policy evaluation | A strict game-start as-of comparison of an acting player's observed cards with an actionable deterministic profile policy and the fixed `simple_lowest` baseline. | Preferred-card and exact-card matches measure behavioral imitation only, not strategic strength, optimality, recommendation quality, statistical significance, or unseen-player generalization. |
| Dataset partition policy | Optional declared `known_opponent` or `unseen_player` intent plus exact stable-player membership and overlap auditing. Public version-1 preparation derives one fixed mode-specific algorithm, validates complete temporal or player-disjoint plans, generates deterministic assignments, and losslessly materializes complete plans. | Known-opponent evaluation intentionally permits player overlap; declared unseen-player datasets require player-disjoint partitions. Preparation has no algorithm override, fallback, partial Plan, default weights, global optimization, ratio guarantee, Sample- or Player-count balancing, or component splitting. |
| Evidence-constrained hidden-card inference | Exact compatible left/right/hypothetical-skat assignments narrowed only by local and authorized public ownership plus confirmed legal failure to follow an effective category. | It is structural decision-time inference, not behavioral, Bayesian, calibrated, learned, tactically weighted, or proof of the actual hidden deal. |
| Public field provenance | Opt-in version-1 provenance for one complete redacted Root Result and artifacts actually returned, with exact declared document scopes and recomputed coverage. | It does not expose consumed inputs, decisions, intermediate stages, unredacted internals, Confidence, or complete end-to-end product provenance. |
| Public Session API | Stable `skat_ai.api.v1.session` version `1` with exact immutable type identity, twelve one-call operations, strict parsing, typed Results, Decision Observation/review export, in-memory persistence build/resume, and appended stable `files` Save/Load transport. | It adds no Session Root workflow, automatic analysis after every Command, persisted analysis Result, default path, GUI, platform adapter, cloud synchronization, distributed lock, encryption, or automatic backup. |
| Session Provenance | Default-omitted version-1 complete provenance over exactly one returned Session operation value, with engine-private redaction and recomputed coverage. | It is independent of Root Result provenance and Confidence, does not cover consumed inputs or itself, and does not widen access to private Session values. |
| Interactive Session capture | Immutable fixed-three-player Live/Retrospective authoring State, accepted typed Log, deterministic replay/transitions, readiness, no-execution Position/Historical export, frozen Checkpoints, accepted-Log observations, isolated review, automatic collection, explicit existing-Application execution, and a phase-aware local Assistant. | Issues #150 through #157 complete the bounded local end-to-end workflow. GUI/browser UI and platform/cloud/encryption concerns remain separate open layers. |
| Match Capture metadata | Internal immutable Match identity, descriptive media/manual source, reusable millisecond bounds, exact named format, three fixed-place participants, optional historical Opponent Statistics snapshots, and one perspective Match Player. | Issues #160 through #167 define, edit, persist, and prepare the value. Issue #168 consumes it for private analysis without changing persistence. Public Match API/Schema/data workflow, public or persisted Player Catalog, YouTube/EuroSkat integration, ranking, qualification, and commercial rules remain absent. |
| Observed Game capture | Internal immutable Match-linked Game facts, exact historical seats, optional perspective hand/original Skat/Discards, zero through 30 public Plays, free-text commentary on any Player Decision, linked later responses, and deterministic evidence capabilities. | Issue #168 can analyze one safely prepared Decision or one strict Historical Game. The actual Card remains retrospective behavior evidence, not an optimal label; Commentary and Response Links remain outside analysis and Coaching. Public Match API/CLI/Schema and tactical interpretation remain absent. |
| Private Match Workspace | Internal immutable exact 36-position EuroSkat Workspace with fixed rotation, revisions, Progress, fingerprints, strict Resume, and optimistic atomic local files. | Issue #168 derives max-eight process-local revision-scoped reports without persisting them. Applied mutation, Reload, shutdown, stale revision, and concurrent-change behavior is explicit. No distributed lock, retry/merge, remote/cloud/encryption/backup, public materialization, or Public Match API/Schema exists. |
| Private Learning Corpus identity, Catalog, persistence, Workspace import, derived Player history, Human Evidence, and Strategy Teacher Evidence | Internal immutable content-addressed Match Snapshots built only from exact strictly resumed Workspace persistence documents, with exact closed References, lightweight entries, explicit Current selections, one fixed explicit local Store, strict Resume, valid orphan reporting, pure Catalog changes, no-clobber objects, optimistic atomic Catalog Save, source-preserving Workspace import, one non-persisted Current-Snapshot Player Catalog with time-safe Statistics selection, one minimized exact Human Commentary/linked Response Evidence export, and one deterministic collection/export of Current-Snapshot-bound method-specific Immediate/Search/Auto Strategy Teacher Evidence from explicitly bound exact executed Decision Analysis Reports, with one no-execution Request rebuild and retained Result validation per source plus exact and semantic identities. | Issues #171 through #174 keep Match Workspaces as editable authority, imported Snapshot objects immutable, `catalog.json` authoritative, valid unreferenced objects as reported orphans, and both Player history and Human Evidence derived from explicit Current selections only. Issue #175 binds exact executed Decision Analysis Reports to explicit Current Match Snapshots and deterministically derives method-bound Strategy Teacher Evidence without execution or persistence. Human text remains exact, observed Cards remain behavior, and Response Links remain caller associations. Human and Strategy Teacher Evidence remain distinct; method-bound Strategy Teacher evidence is not ground truth. Other future analysis/annotation artifacts remain separate. Dataset version `2` is implemented as the separate private contract below. Issue #179 adds only private process-local browser upload, preparation, and download transport. No deletion, garbage collection, Player Catalog persistence, Human or Strategy Teacher Evidence persistence/public transport, persisted aliases/assertions, merge/split, all-revision view, automatic Report capture, Historical Report import, Teacher ranking/consensus, Public API, Schema, derived tags, or model training exists. See [Learning Corpus identity and Catalogs](learning_corpus_identity_and_catalogs.md), [Learning Corpus persistence and Workspace import](learning_corpus_persistence_and_import.md), [Learning Corpus Player Catalog and Statistics history](learning_corpus_player_catalog_and_statistics_history.md), [Learning Corpus human Commentary and Response evidence](learning_corpus_human_commentary_and_response_evidence.md), [Learning Corpus Strategy Teacher Evidence](learning_corpus_strategy_teacher_evidence.md), and [Learning Corpus browser workflows](learning_corpus_browser_workflows.md). |
| Private Learning Dataset version 2 | One Current-Snapshot-only unpartitioned task-neutral Dataset with exact information-safe Decision State, separate observed behavior, latest-unambiguous time-safe Player Context, all exact method-bound Teachers, exact Commentary, joined outgoing/incoming Responses, explicit skipped Decisions, unjoined Human Evidence, normalized pools, deterministic identities, canonical path-free export, separate Match-Snapshot-group-safe partition preparation, and deterministic exact-Count descriptive cross-game Match, Player, Communication, Strategy, Coverage, and supplied-partition-readiness summaries with canonical path-free export. | Issue #176 defines the unchanged source Dataset. Issue #177 adds complete/unavailable temporal Known-player and component-based unseen-player Plans, leakage audits, and lossless index-only views. Issue #178 consumes the exact Dataset, Player Catalog, and supplied Results without regeneration and adds no rating, ranking, interpretation, evaluation, model-readiness claim, persistence, CLI, browser, Public API, Schema, example, generated scenario, or model training. Training Dataset version `1` remains separate and unchanged. |
| Private Learning Corpus browser workflow | Separate internal version-1 installed/module/Legacy `corpus` transport over one explicit root, with strict initialization/Resume/Reload, strict 16-MiB Workspace and exact executed-Decision Report-source uploads, optimistic import, explicit Current selection, max-2,048 process-local sources, exact unlocked Player/Human/Strategy/Dataset-v2/known/unseen/Summary preparation, minimized no-JavaScript-capable presentation, and seven authenticated canonical downloads. | Issue #179 completes the functional private local workflow without adding a Root workflow, Public API, Schema, derived persistence, automatic Report capture, Historical Report import, remote/cloud/collaboration, task builder, evaluation, rating, or training. Issue #180 prepared Package `0.16.0`, and Issue #181 synchronizes publication status without product functionality. |
| Private Learning Corpus Tactical Motif evidence and summaries | Separate Current-Snapshot-only Evidence-or-skip coverage over every observed Decision, exact Issue #194 detector reuse, safe partial-Match and incomplete-final-Trick handling, deterministic path-free exports, and exact global, Player, role, seat, phase, contract, distinct-Game, distinct-Match, and bounded recurrence Counts. | Issue #195 keeps Human, Strategy Teacher, and Tactical Evidence separate; changes no Learning Dataset version `2` contract; atomically publishes both prepared families; adds minimized Tactical counts and two authenticated downloads for nine current downloads; and makes no trait, rate, quality, correctness, significance, intent, communication, causal, or Coaching claim. No derived persistence, Public API, Schema, example, or generated scenario is added. |
| Private Learning Corpus Tactical Cross-game Coaching | Separate deterministic exact Tactical/Strategy Teacher joins, one Assessment per exact Report, semantic Decision consensus, complete-Search-only actionable evidence, repeated cross-Game focus, bounded Catalog-order Player Reports, and fixed Guidance. | Issue #196 atomically publishes a third process-local prepared family, exposes aggregate private dashboard Counts and a tenth authenticated path-free download, and changes no Learning Dataset version `2`, existing Summary, persistence, Public API, Schema, example, or generated scenario. Immediate, partial, unavailable, and mixed evidence remains descriptive; no ground-truth, perfect-play, trait, Rating, intent, communication, causal, significance, equilibrium, or model claim is made. |
| Match Capture Application services | Internal transport-free rapid-entry operations over one loaded Workspace, with UI-ready Views, exact/bounded Cards, automatic Player/Decision derivation, truncation cleanup, annotations, and revisioned Results. | Browser mutations still compose these no-I/O/no-analysis services directly. Issues #167 and #168 remain separate preparation and analysis/report/export layers. Public Match API/Schema/data workflow and tactical interpretation remain absent. |
| Match review and materialization preparation | Internal evidence-aware acting-own-hand Decision snapshots, strict complete-Deal normal-completion Historical Games, unpartitioned Training source Records, and complete fixed-three-player list plus aggregation materialization. | Issue #167 preserves the actual-Card cutoff, excludes future-opponent leakage, retains Skat/Ouvert semantics, prepares relative Profile bindings without application, uses Match-level `played_at`, preserves Passed Deals and Commentary sidecars, and executes no workflow. Issue #168 exposes explicit private preparation reports and canonical downloads; materialization still executes no workflow. See [Match review and materialization](match_review_and_materialization.md). |
| Match analysis and private exports | Internal explicit one-Decision Immediate/Search/Auto Position execution, strict selected-mode Historical execution, existing-behavior eligible Profile application, ephemeral reports, and authenticated local downloads. | One available selection invokes the existing matching Application exactly once. Actor exclusion, disabled/nonactionable Profiles, strict Historical availability, no Profile effect on Search/Coaching, no Commentary in Coaching, no-workflow materialization, deterministic SHA-256/max-eight reports, and stale/concurrent invalidation are retained. It adds no Public Match API/Schema/Root/CLI or persisted report. See [Match analysis and exports](match_analysis_and_exports.md). |
| Local Match Capture interface | Internal version-1 Web, Protocol, and Capture CLI private transport with one explicit file, loopback token/same-origin server, no-JSON creation, 36-position UI, capture/Statistics/analysis forms, CAS autosave, explicit Reload, ephemeral report pages, authenticated downloads, and packaged progressive assets. | It is not a Root workflow or Public API and adds no remote bind, account/encryption claim, automatic analysis, external source integration, new Capture CLI option, Schema, example, or generated scenario. See [Local Match Capture interface](local_match_capture_interface.md) and [Match Player Statistics](match_player_statistics.md). |
| Session History Edit and Checkpoint lineage | Immutable version-1 strict-prefix Undo, one-command replacement with deterministic original-suffix replay, valid partial corrected States, and exact Checkpoint relationships. | Public API and all-three-form CLI exposure are implemented. Automatic Redo, merging, arbitrary Log surgery, and branching remain absent. |
| Private Session persistence and resume | Immutable private version-1 document containing the authoritative accepted-Log State and canonical frozen Checkpoints, with deterministic fingerprints, strict reconstruction/replay, recomputed lineage, and optimistic atomic writes. | Stable public Save/Load and CLI CAS orchestration are implemented without adding distributed locking, migration, merge/retry, encryption, cloud sync, or automatic backups. See [Session persistence and resume](session_persistence_and_resume.md). |
| Learned opponent model | A versioned artifact whose behavior or parameters were fit from data and are used during inference. | It requires separate training, evaluation, deployment, fallback, and explainability decisions. |
| Training a machine-learning model | Running a reproducible process that fits model parameters from an approved training dataset and evaluates them on separated data. | It is distinct from storing historical games, generating labels, calculating statistics, or running rule-based simulation. |

## Required before v1.0.0

The following directions are required for `v1.0.0`:

* Analyze live game situations at fixed three-player tables.
* Enforce field-level live-information provenance across inputs, analysis,
  simulation, recommendations, and output. The current broad live/post-game
  boundary and internal live Position propagation provide partial support. The
  shared version-1 language defines paths, entries, ledgers, coverage,
  dependencies, context use, redaction, and serialization. Live Position
  Application execution now enforces complete flat and simulated decision
  ledgers and attaches a complete non-legacy exact Result ledger. Retrospective
  Position and Historical execution now separates decision-time input/analysis
  from actual-card assessment and covers requested review and Coaching stages.
  Dataset, Preparation, Opponent, Profile, list, and comparison execution now has
  complete internal workflow and Root ledgers. Historical execution now also has
  complete non-legacy exact Root Result coverage, including result-only base
  execution. Issue #147 exposes the bounded redacted Root Result and actual-
  artifact subset through Public API, Root JSON, strict Schema, and all CLI
  forms. Broader loading, decision, intermediate-stage, and serialization
  enforcement remains open.
* Support retrospective single-decision review and complete-game coaching
  without future-information leakage into reconstructed decisions. Bounded
  variable-cardinality review exists for supported endings. Public Replay
  Coaching contract version 1 separates decision-time evidence from
  retrospective observed-card attachment and defines impact semantics.
  Prioritization version 1 adds deterministic Key Decisions, separate
  counterfactual and recorded-path Turning Points, and high-impact classification.
  Guidance version 1 adds two-occurrence one-game patterns by player, role,
  phase, and contract plus deterministic decision and actionable pattern
  recommendations. Report version 1 exposes the complete one-game report through
  a strict schema and CLI with privacy-safe context, final-outcome isolation,
  coverage, and scope summaries. Separate Tactical Motif Review version 1 adds
  deterministic structural evidence with strict timing and privacy but no
  quality, signaling, communication, causal, or cross-game conclusion.
* Represent complete historical games with structured claims, concessions, and
  approved additional game-end reasons, then analyze rules, result, approved
  settlement, and eligible decisions retrospectively. Current complete records
  support normal completion, all six exact-prefix shortened terminal reasons,
  including the Historical-only party-wide Claim, and one timed non-terminal defender-open-play or declarer-card-exposure
  continuation before normal completion or one supported terminal shortening.
  The approved party-wide Claim now has private contracts, exact-state
  preparation, bounded proof execution, valid-proof-only adjudication, complete
  assignment and Game Result, and existing Final Settlement composition through
  the Historical workflow. Invalid or unavailable proof rejects the asserted
  terminal record and creates no outcome. Runtime `GameShortening` remains
  absent.
* Complete the approved
  [normative settlement matrix](settlement_normative_matrix.md), including
  structured claim and concession outcomes, while preserving the bounded impossible Null
  interpretation from the International Skat Court decision collection. Matrix
  version `3` defines the approved classifications and policy boundaries. The
  party-wide all-remaining-Tricks Claim is the only supported v1 Claim;
  `V1_IMPLEMENTATION_REQUIRED_CLAIM_CASE_IDS` is empty, no canonical case remains
  `decision_required`, and every other current Claim boundary is
  `not_supported_v1`.
* Represent complete historical games as validated training and evaluation data
  without requiring model training.
* Preserve versioned external and exact historically aggregated opponent
  statistics, scoped exact or estimated evidence, deterministic explainable
  profiles, actionable gating, explicit live stable-ID bindings, strict time-safe
  historical application, and rolling known-opponent behavioral evaluation.
  These bounded requirements are implemented for normal completion and all
  six shortened kinds, including zero-play source games and variable-cardinality rolling
  targets; profiles remain rule-based and confidence remains heuristic.
* Preserve optional known-opponent and unseen-player dataset policies, exact
  stable-player overlap audits, and strict declared unseen-player disjointness.
  This bounded requirement is implemented.
* Preserve bounded public automatic Training Dataset preparation. Root
  `training_dataset_preparation_input` dispatches `known_opponent` to
  `temporal_known_opponent_v1` and `unseen_player` to
  `component_balanced_unseen_player_v1`. Complete results losslessly materialize
  the existing version-1 dataset and audit; unavailable results succeed with
  explicit null dataset/audit and no partial Plan. This bounded requirement is
  implemented without model training or automatic evaluation.
* Preserve the bounded stronger Search and solver functionality with documented
  information, quality, determinism, and budget contracts. Version-1 information, private
  exact complete-world state, deterministic legal transition, eligibility,
  budget, utility, result, exactness, privacy, and standalone-schema contracts,
  bounded `perfect_information_minimax_v1`, compatible-world Minimax and
  aggregation, explicit flat live strict/auto routing, and opt-in Multi-Step and
  Policy Comparison routing are implemented. Flat post-game Search, Historical
  Search Review, bounded dataset Search-versus-Immediate evaluation, immutable
  versioned work profiles, deterministic quality/convergence regressions, and a
  reproducible local performance baseline are also implemented. Issues #187 and
  #188 add a separate private three-Trick selected-world information-set
  foundation and controlled-Player best-response executor. Issue #189 adds
  strict flat routing, safe aggregate output, descriptive same-selection PIMC and
  independent Immediate retrospective comparison, separate Historical Review
  and Training Dataset evaluation, retained-stage Provenance, CLI, four Schemas,
  one example, and four scenarios. Issue #190 completes strict Multi-Step and
  Policy Comparison integration with per-decision Search isolation and unchanged
  `auto`. Issue #191 adds the bounded one-Decision Match/Report/Teacher/Dataset/
  Corpus path. Issue #192 adds separate Match Historical Information-set
  Review/Coaching and Information-set Replay Coaching with retained Review reuse
  and no baseline fallback. Issue #193 adds a strict synthetic benchmark corpus,
  focused tests, and documented local reference measurements for the unchanged
  executor. Issue #200 accepts deterministic functional and structural-work
  evidence as the bounded v1 performance contract. Broader solvers, calibrated
  probabilities, complete-contract Search, and wider bounds are post-v1.
  Cross-machine latency guarantees and dedicated production Budget profiles are
  not required. See
  [Bounded search contracts](bounded_search_contracts.md) and the
  [Information-set Search workflows](information_set_search_workflows.md), plus
  [Information-set Search Multi-Step and Policy Comparison](information_set_search_multi_step_and_policy_comparison.md)
  and [Information-set Search performance](information_set_search_performance.md).
* Preserve one coherent hidden-world assignment across each simulated path.
  Multi-Step and shared-root Policy Comparison now satisfy this bounded
  execution-consistency requirement; broader Search is post-v1.
* Preserve bounded information-safe hidden-card inference with explicit allowed
  evidence and confidence semantics. Issue #104 satisfies this gate using only
  exact decision-time ownership and confirmed legal failure-to-follow evidence,
  exact DP compatible-world counts and marginals, uniform labeled assignments,
  and uncalibrated concentration labels. Behavioral, Bayesian, learned, and
  broader tactical inference remain outside this bounded gate.
* Preserve exposed-card use in Ouvert-aware recommendation simulation without
  violating decision-time information boundaries. This bounded gate is implemented.
* Aggregate complete fixed-three-player 36-game lists while preserving SkWO
  6.3.1 performance formulas and tie handling. Contract version `1`
  now validates all 36 ordered played or passed positions, fixed identities,
  rotation, historical settlement extraction, and non-cumulative contribution
  facts. Internal aggregation version `1` adds cumulative player totals, one
  provisional standings snapshot per position, final standings, unresolved
  ties, and optional exact external-lot application. Internal comparison version
  `1` aligns the same stable players across independent completed lists, preserves
  one reference, reports final count and player-total deltas, and compares ranks
  only when both sources are final. Issue #130 exposes these retained contracts
  through strict root-selected JSON, standalone schemas, concise CLI output,
  three bounded examples, and generated-output coverage. The public workflow is
  functionally complete; series aggregation, ratings, winner analysis,
  tournament management, and official reporting remain outside it.
* Support interactive live and retrospective input and Session capture. Issue
  #150 establishes internal Session and Command version `1`, stable Players,
  Modes, phases, typed Commands, accepted Log authority, linear revisions,
  Diagnostics, readiness, valid-incomplete State, and Transition Result
  semantics. Issue #151 adds transition and projection version `1`, canonical
  revision-zero creation, deterministic full accepted-Log replay, atomic
  application/rejection, monotonic phases, incremental rule and information-
  policy validation, trick/event/end derivation, promotion, readiness, and
  forged-State detection. Issue #152 adds exact Historical readiness gating,
  projection-to-`historical_game_input` mapping, existing builder validation,
  canonical round trip, and immutable `RequestDocumentV1` construction without
  execution. Issue #153 adds exact Position readiness gating, information-safe
  projection-to-flat-Position mapping, declared-Ouvert public-hand capture,
  existing Position builder validation, and immutable replay-verified pre-Play
  Checkpoints without execution. Issue #154 adds strict-prefix Undo,
  one-command correction, stop-before-first-rejection suffix replay, valid
  partial corrected States, and exact Checkpoint lineage. Issue #155 adds private
  deterministic persistence/resume with authoritative State, caller-supplied
  frozen Checkpoints, State/content fingerprints, strict reconstruction and
  replay, recomputed lineage, optimistic expected-fingerprint writes, canonical
  files, and atomic same-directory replacement. Issue #156 adds Public API,
  Provenance, Schema, and clean-install support. Issue #157 adds public file
  transport, actual-card observation and isolated review, automatic Checkpoints,
  all 12 CLI subcommands, explicit analysis/finalization, the Assistant, six
  examples, and eight scenarios. The bounded local end-to-end capture direction
  is implemented; Session GUI/browser UI and platform/cloud/encryption integration
  are not v1 requirements.
* Support usable manual post-game Match capture for one EuroSkat 36er Standard
  Match from descriptive video evidence. Issue #160 implements internal
  version-1 source, timecode, named-format registry, participant, optional Player
  Statistics Snapshot, Match identity, perspective, and deterministic
  serialization contracts. Issue #161 adds Match-linked observed Games, optional
  Card evidence, bounded partial and exact complete Play validation, free-text
  commentary, linked later responses, and evidence summaries. Issue #163 adds
  exactly 36 internal Slots, rotation, passed deals, immutable changes, Progress,
  fingerprints, strict Resume, and optimistic atomic local persistence. Issue
  #164 adds internal rapid entry with UI-ready Views, exact/bounded palettes,
  setup updates, automatic append, truncation, annotations, and passed/clear
  wrappers. Issue #165 adds the usable private local browser/Capture CLI and
  autosave transport. Issue #166 adds editable Match-bound Statistics Snapshots,
  deterministic IDs, strict-before-Match Context/Preparation, existing Profile
  derivation, and browser Add/Replace/Clear without applying a policy. Issue #167
  adds internal acting-own-hand Decision preparation, strict normal-completion
  Historical materialization, existing unpartitioned Training source Records,
  and complete fixed-list construction plus aggregation with Passed Deals and
  external-lot behavior, without workflow execution. Issue #168 adds explicit
  one-Decision and strict Historical execution, existing-behavior eligible
  Profile application, no-workflow materialization reports, and authenticated
  local downloads, completing the functional local milestone. Issues #171 through
  #179 subsequently add separate private immutable Learning Corpus Snapshot/
  reference and lightweight Catalog identity, deterministic persistence, and
  Workspace-import foundations plus derived Player/Statistics history, Human
  Evidence, exact Decision Report Strategy Teacher Evidence, one unpartitioned
  task-neutral Learning Dataset version `2`, group-safe partition preparation,
  descriptive exact-Count cross-game summaries, and the private local one-root
  Corpus/Dataset-v2 browser workflow without changing Workspace authority.
  Public Match/Corpus/Dataset-v2 APIs and Schemas, Player Catalog and derived-
  artifact persistence, and database deployment are not v1 requirements.
  Hosted/remote deployment is post-v1.
  YouTube and EuroSkat integration are not required before v1.0.
* Provide a stable library API and installed CLI/package interface. Public API
  contract version `1`, immutable JSON documents, compatibility metadata, stable
  errors, and legacy Root CLI compatibility are implemented. Internal Application
  orchestration version `1` now executes all seven Root workflows from immutable
  in-memory invocations and keeps transport in the legacy CLI adapter. The public
  facade now parses and executes those workflows from already loaded documents,
  validates Root input/output and artifacts, and exposes artifacts separately.
  Public field-provenance opt-in adds one typed bundle and Root sidecar while
  preserving the flattened execution envelope and default output.
  The library now builds and cleanly installs from Wheel and sdist with private
  byte-identical Package Resource schemas, typing metadata, and Package version
  metadata. Installed and module CLI entry points now execute all seven workflows
  through the same internal Application layer, while Legacy `python main.py`
  remains compatible through at least `v1.0.0`. Issue #162 modularizes the
  internal Root and Session transports behind compatibility facades and enforces
  the leaf-transport import direction without changing the stable interface.
* Support all final declared Suit, Grand, and Null variants in the approved v1.0
  contract, including valid dependencies, matadors, Hand, Schneider, Schwarz,
  Ouvert, game end, and final settlement.
* Preserve stable, schema-validated JSON inputs and outputs and deterministic
  regression workflows.

The Python baseline for v1.0 development and release is Python 3.13 or newer.

## Planned after v1.0.0

These areas are useful planned later work, not requirements for the first major
release. Their implementation details and acceptance criteria are not yet
approved:

* Full bidding and auction sequence modeling.
* Learned opponent profiles.
* Machine-learning models for the engine's own card decisions.
* Online-platform adapters, browser extensions, or hosted/remote browser
  integration.
* Broader solver algorithms, complete-contract Search, wider Information-set
  bounds, equilibrium/CFR research, and calibrated probabilities.

## Not required

These areas are not required for the intended product:

* Formal series aggregation as a dedicated workflow. A simple comparison or
  summary across independent completed lists is publicly implemented without a
  formal series model.
* Tournament management.
* Official federation list or report formats.
* Public Match, Corpus, or Learning Dataset-v2 APIs or Schemas.
* Player Catalog, Dataset-v2, Tactical, or Coaching derived persistence.
* Automatic Report capture, Historical Report import, and database deployment.
* Broader Player Ratings, tactical-truth classification, and causal attribution.
* Session GUI/browser UI, cross-machine latency guarantees, dedicated production
  Budget profiles, and pre-v1 persisted-document migration tooling.

## Unconditional exclusion

Four-player table support is the project's only unconditional out-of-scope
area. No other area is unconditionally excluded.

## Completion gates

Every gate below must have automated evidence unless it explicitly names a
manual release artifact. A feature field or example without source behavior,
validation, and tests does not satisfy a gate.

For the table below, Issue #193 supersedes older broad wording that says
Information-set Search performance evidence remains open. Repository-local
benchmark evidence implements the bounded v0.17.0 performance contract.
Issue #200 accepts deterministic functional and structural work as the bounded v1
performance contract. Final Windows and Ubuntu candidate evidence remains
required; cross-machine latency guarantees are not required.

Issue #200 supersedes any pre-audit completion-row wording below that calls an
accepted bounded limitation open before v1. Bounded solver, Claim, Settlement,
Coaching, Tactical, private-surface, persistence, and Rating boundaries are
accepted, post-v1, or not required exactly as classified in the Issue #200 audit.
In the historical completion rows below, `open`, `absent`, or `unsupported`
continues to describe factual capability only; it is not a v1 blocker unless the
Issue #200 ledger classifies it as one.

For the Search gate, Issue #114 added opt-in live Multi-Step and Policy
Comparison routing to the flat strict/auto baseline described in the compact
table. Issue #115 adds flat post-game Search, information-safe Historical Search
Review, bounded dataset evaluation, immutable work profiles, independent quality
and convergence evidence, and a measured local performance baseline. Historical
decisions use domain-separated private child seeds while future-private facts
remain outside the reconstructed Search view. Sampled quality is not calibrated,
the determinization aggregate is not an optimal imperfect-information policy,
and measured wall time is not a latency guarantee. The functional `v0.10.0`
milestone and Issues #187 through #193 satisfy the approved bounded v1 solver
gate. Broader solver directions are post-v1.

Issue #190 completes only strict Information-set Search Multi-Step and Policy
Comparison integration. It adds fresh per-decision public-state Search, private
independent coherent execution, no Search World or controlled-Policy reuse, no
fallback, safe Results and diagnostics, unchanged ranking, and complete
Provenance. Issue #191 subsequently adds the bounded one-Decision Match/Report/
Teacher/Dataset/Corpus path with no new Schema or scenario. At that point, Match
Historical Information-set execution and Replay Coaching classification remained
open; both are completed separately by Issue #192 with one new Schema and two
scenarios. Issue #193 completes bounded repository-local benchmark evidence.
Final supported-platform evidence remains required. Latency guarantees are not a
v1 gate, and broader solver directions are post-v1.

Issues #156 and #157 supersede older rows below that call the Public Session API,
Session Provenance/Schema, public file transport, automatic/actual-card
Checkpoints, CLI, examples/generated outputs, or end-to-end local capture absent.
The published `v0.14.0` baseline validates 63 Schemas, six Session examples, 85
generated outputs, and 5,892 pytest tests; the historical published `v0.13.0`
baseline remains 62 Schemas and 77 outputs. Issue #158 completed Release
preparation before manual maintainer publication.
GUI/platform/cloud/encryption layers are not v1 requirements.

| Area | Observable completion condition |
| --- | --- |
| Private Learning Corpus workflow | Issue #179 provides exact installed/module/Legacy `corpus` options with default port `8766`; one-root initialization/strict Resume/Reload and failed-Reload retention; strict 16-MiB uploads with ignored filenames and temporary cleanup; optimistic import statuses/conflicts/invalidation and explicit Current selection; exact Match Capture Report-source transfer; max-2,048 current/non-current process-local sources with remove/clear; explicit Player/Human/Strategy/Dataset-v2/known/unseen/Summary preparation outside the lock with source-change HTTP `409`; minimized no-JavaScript dashboard; seven authenticated byte-canonical downloads and deterministic filenames; token/cookie/Host/origin/CSP loopback security; no external network; and shutdown cleanup. Derived persistence, Public APIs/Schemas, remote/cloud/collaboration, automatic Report capture, Historical Report import, task builders/taxonomies/tags, evaluation, ratings, and training remain open. |
| Learning Corpus Tactical Motif evidence and summaries | Issue #195 requires explicit Current Match Snapshots only; one safe Evidence or explicit skip per observed Decision; exact shared single-game detector reuse; safe partial-Match/final-Trick handling; deterministic identities; exact global/Player/scope/distinct-Game/distinct-Match/recurrence Counts; separate Human/Strategy/Tactical families; unchanged Dataset version `2`; atomic generation-safe process-local publication/invalidation; minimized presentation; and two authenticated canonical path-free downloads for nine current downloads. Tactical quality, trait, rate, significance, causal, communication, and cross-game Coaching claims remain absent. |
| Learning Corpus Tactical Cross-game Coaching | Issue #196 requires exact Current-Snapshot Tactical/Teacher source reconciliation; strict five-fact joins and explicit unjoined Teachers; one retained Assessment per exact Teacher Report; semantic one-per-Decision consensus; canonical Immediate, bounded Search, Auto, and Information-set handling without analysis rerun; unanimous complete-Search-only actionable focus; at least two below-best Decisions in at least two Games; objective-impact priority and at most five focus areas per Player; zero-count Catalog-order Player Reports; fixed Guidance and canonical limitations; deterministic path-free identities/bytes; atomic third-family publication/invalidation; aggregate-only dashboard facts; and one tenth authenticated download. Dataset version `2`, existing summaries, public/versioned surfaces, persistence, and truth/trait/Rating/intent/communication/causal/significance/model claims remain unchanged or absent. |
| Match capture | Issues #160 through #167 retain exact internal metadata, observed Games, 36-Slot Workspace/persistence, rapid-entry services, private no-JSON browser/autosave transport, Match-bound Statistics, information-safe Decision preparation, strict Historical and unpartitioned Training-source materialization, and complete fixed-list aggregation. Issue #168 adds explicit one-Decision Immediate/Search/Auto and strict Historical execution through one existing Application invocation, existing-behavior eligible Profile application, no-workflow materialization, deterministic max-eight ephemeral reports, concurrency invalidation, and authenticated canonical downloads. The functional local `v0.15.0` Package baseline is published at commit `ec1c154`. Issues #171 through #179 add private content-addressed Learning Corpus identity/persistence, derived Current-Snapshot Player/Statistics, Human and Strategy Teacher Evidence, Learning Dataset-v2, Match-group-safe partition preparation, descriptive cross-game summaries, and the functional private local Corpus browser workflow. Issue #194 adds explicit Historical Tactical Motif Review, strict Root reconciliation, and a curated escaped safe browser view without making Historical Reports Strategy Teacher sources. Deletion/garbage collection, Public Match API, Match Schema/data workflow, public/persisted Player Catalog, task-specific Dataset work, derived persistence, and database/remote deployment remain open; YouTube and EuroSkat integration are not required before v1.0. |
| Rules and settlement coverage | Every ISkO row marked required before v1.0 in the traceability matrix is `supported`, or has an explicitly approved bounded interpretation; a normative table-driven suite covers winning, losing, achieved/announced levels, overbid, impossible Null, claim, concession, and incomplete-evidence outcomes. |
| Supported contract variants | Input validation accepts every legal Suit, Grand, Null, Hand, and ouvert variant in the documented v1 contract; rejects every documented illegal modifier dependency; and produces tested game values and settlement for each accepted variant. |
| Live-position analysis | Every canonical three-player turn phase is either analyzed when the local player acts or advances through a documented opponent-preparation path; unsupported states fail explicitly without mutating the supplied position. |
| Live information control | Internal field-provenance contract version `1` defines RFC 6901 paths, immutable entries and sidecar ledgers, deterministic coverage auditing, dependency and temporal validation, Information Use Context, engine-private redaction, safe serialization, and Confidence separation. Application propagation enforces complete live and retrospective decision/stage ledgers and complete non-legacy Root Results across all seven workflows. Public version `1` exposes one explicitly mapped redacted Root Result plus actual artifacts under scopes `root_result_without_field_provenance` and `artifact_document`, with complete recomputed coverage and no consumed-input, decision, intermediate-stage, or unredacted exposure. Completion still requires broader loading, matador, review, serialization, and end-to-end enforcement. |
| Post-game analysis | A legal actual card can be compared with all legal alternatives for Suit, Grand, and Null from declarer and defender perspectives; unavailable and invalid cases have stable schema-valid output and focused tests. |
| Complete-game retrospective analysis and coaching | A complete historical record can be replayed in order, each eligible decision is reconstructed using only information available then, rule/result/settlement summaries and actionable coaching explanations are produced, and end-to-end tests detect future-information leakage and event-order corruption. Public Replay Coaching version 1 exposes information-safe evidence, prioritization, patterns, recommendations, scope summaries, and isolated outcome context through a strict schema and CLI. Separate Tactical Motif Review version 1 reuses one retained Snapshot sequence and exposes exact structural lead/void/Trick-control/Defender-partnership/hand-shape/outcome evidence through strict Schema, CLI, Provenance, and Match controls. It is not a quality, intent, signaling, communication, causal, or cross-game analysis. Issue #200 accepts this bounded v1 gate; broader Search is post-v1, while broader tactical quality, Ratings, and causal attribution are not required. |
| Complete-game historical representation | A versioned schema and Runtime model represent stable game/player IDs, fixed seats, initial deal, final bid/declaration facts, Skat pickup/discards or Hand state, every play, structured Claims/concessions and approved additional end reasons, final result, and Settlement; valid records round-trip and inconsistent ownership, order, legality, totals, or outcomes are rejected. Matrix version `3` preserves all 61 cases and marks the approved bounded party-wide Claim `supported_as_is`. Historical Game input, strict Schemas, valid-proof-only execution, diagnostic public output, Provenance, CLI, Review/Coaching, Dataset, list, and statistics integration are implemented; invalid or unavailable proof rejects the terminal record. Runtime `GameShortening`, flat Position, Session, Match Capture, and Corpus Claim entry remain absent and are not v1 requirements. Issue #200 accepts the bounded Claim and Final Settlement slice as the complete v1 boundary. |
| Training-data representation | A versioned schema links a complete historical game to provenance, labels/targets, feature-generation version, explicit training/evaluation partition, and optional partition policy; conversion and exact-player overlap audits are deterministic, and tests reject duplicates, missing provenance, invalid labels, partition leakage, and declared unseen-player overlap. Public version-1 unpartitioned requests add explicit weights, split-safe facts, deterministic fingerprints/seeds, complete/unavailable Plans, strict temporal or player-disjoint proof, exact Record-count arithmetic, lossless materialization, exact temporal Known-opponent assignment generation, and deterministic locally optimized whole-component unseen-player assignment. Strict root input/output schemas, fixed mode dispatch, file-only CLI options, three examples, and complete/unavailable generated scenarios cover the bounded workflow without generating samples, training a model, or automatically evaluating it. |
| Input validation | JSON Schema and runtime validation agree on public types, bounds, enums, and cross-field requirements for every stable input branch; parity tests cover malformed and contradictory records. |
| Public Session interface | The stable Session subnamespace preserves the first 52 names exactly and appends six observation/review names plus `files`; twelve operation/value pairs, persistence mappings, optional provenance, and complete Results validate through the standalone packaged Session Schema. The independently versioned file subnamespace exposes exact path-free Save/Load Results. Export and review-export wrappers execute no analysis. |
| Structured output stability | Every stable output branch has a documented versioned schema, deterministic serialization, explicit unavailable/incomplete states, and compatibility tests; public `field_provenance` is strict, opt-in, versioned independently, and omitted by default; intentional breaking changes are recorded before release. |
| Simulation behavior | Seeded immediate and multi-step simulations are reproducible, play only legal cards, preserve one coherent hidden-card ownership assignment across a simulated path, never reuse cards, maintain point/trick ownership exactly once, and terminate every canonical phase with a documented reason. Multi-Step now preserves one immutable private root per path with owner-aware removals and a fixed hypothetical skat; Policy Comparison uses one shared root with equal independent immutable path copies. Unsupported phases remain explicit. |
| Search and hidden-card inference | The stronger-search portion remains open. Version-1 contracts and `perfect_information_minimax_v1` reproducibly solve one fully specified non-terminal Suit, Grand, or normal non-overbid Null exact state for the current actor, limited by the lower of five remaining tricks and the request. All four Null variants use exact completed-trick ownership, fixed-value settlement, no card-point secondary objective, and require a bid no greater than the fixed value; overbid Null replacement selection remains unsupported. Canonical full-window root values, deterministic below-root Alpha-Beta, invocation-local exact-only cache reuse, declarer-versus-cooperating-defenders utility, existing settlement reuse, explicit node/depth/timeout outcomes, and complete-versus-zero-completion claims are implemented without partial direct-world recommendations. Private Search spaces count structural compatible worlds with or without void evidence, canonically enumerate bounded complete spaces, deterministically sample larger spaces IID with replacement while retaining duplicates, materialize strict exact states, and freeze one common legal-root order. `compatible_world_minimax_v1` evaluates that order with the shared exact evaluator, one global node budget, per-world depth reset and cache, one global post-selection timeout, and first-incomplete-world common-prefix aggregation. Duplicate draws retain equal repeated weight. Complete exhaustive coverage is exact across all compatible worlds; sampled completion is exact only per selected sample, and partial results are exact only over their completed prefix. The method is determinization-based, is subject to strategy fusion, and does not prove an optimal imperfect-information policy. Explicit flat ongoing live routing implements `immediate_expected_value`, strict `bounded_search`, and Search-first `auto` fallback, with input/output schemas, CLI summaries, report and Immediate/Search seed separation, attributed-history and declared-Ouvert/continuation public-hand authorization, and privacy-safe deterministic examples. Remaining Search work includes Match Capture and Match Analysis Report integration, Strategy Teacher and Replay Coaching classification, default/production budgets, latency/performance evidence, broader Strategy-Fusion correction, and release preparation. The bounded inference portion is implemented: only local/exact public ownership, legitimate skat, attributed public play, and confirmed legal failure to follow constrain exact compatible assignments; chronology, contradiction rejection, DP counts/marginals, uniform sampling, uncalibrated confidence, historical leakage controls, and privacy-safe output are tested. |
| Information-set Search | Issue #189 provides strict flat `information_set_search` with exactly nine settings, no Live baseline or fallback, safe aggregate Results, descriptive same-selection PIMC and independently seeded Immediate retrospective comparison, separate Historical Review and Training Dataset evaluation, retained-stage Provenance, CLI, Schemas, example, and generated scenarios. Issue #190 completes strict Multi-Step and Policy Comparison version `1`: every local decision derives a domain-separated child seed, runs fresh public-state Search independently of the private coherent execution World, reuses no Search World or controlled Policy, and stops without fallback; safe Decisions, nested Results, exact 16-field diagnostics, append-once-last ordering, shared-root independent path copies, stopped-row ineligibility, existing ranking, and retained-Result complete Provenance are implemented. Issue #191 adds bounded one-Decision Match analysis, exact Report-source transfer, Strategy Teacher Evidence, Dataset-v2 joins, and Corpus propagation. Issue #192 adds separate Information-set Replay Coaching and Match Historical Information-set Review/Coaching. Issue #193 adds a strict synthetic benchmark corpus, frozen functional and structural signatures, focused tests, and local reference measurements for the unchanged executor. Fixed left/right Policies derive from existing effective settings; `random_legal` and role-invalid Policies are unavailable. Existing `auto` is unchanged and no `information_set_auto` exists. Exact Worlds, hidden hands, Observations, controlled Policy tables, caches, and derived seeds remain private. This is not a cross-decision global Policy, equilibrium, global optimality, calibrated probability, complete Strategy-Fusion correction, complete-contract solving, product/runtime performance gate, or latency guarantee. |
| Ouvert-aware simulation | Historical and live Ouvert analysis uses legitimately exposed cards in recommendation simulation, never treats unexposed cards as public, and has deterministic contract- and perspective-specific tests. |
| Recommendation behavior | Recommendations always select from legal candidates, use the documented Suit/Grand or Null objective, preserve player-side perspective, expose enough evidence to reproduce ranking, and have deterministic tie behavior under fixed settings. |
| Opponent modeling | Every supported global and left/right rule-based policy has documented semantics, precedence, and controlled tests proving its effect in each analysis path where it is claimed to apply; no policy is described as learned. External and historical statistics preserve stable identity and provenance, and strict time-safe historical application never uses a capture from the target game or later. |
| Profile confidence and behavioral evaluation | Accepted profile fields, exact or estimated evidence scopes, heuristic confidence, activation boundaries, conflict rules, and exact behavioral influence are documented and tested at every boundary. Rolling evaluation uses strict game-start as-of history and reports preferred/exact behavioral matching without strategic, optimality, significance, or unseen-player claims. |
| Dataset partition policies | Optional known-opponent and unseen-player intent remains backward-compatible; exact membership, pairwise/three-way overlap, directed known-opponent coverage, and strict declared unseen-player disjointness are deterministic and schema-valid. |
| Automatic Training Dataset preparation | Root `training_dataset_preparation_input` selects workflow `training_dataset_preparation`; mode alone selects `temporal_known_opponent_v1` or `component_balanced_unseen_player_v1`. Complete output under `training_dataset_preparation_summary` losslessly materializes the existing version-1 dataset and a matching audit. Unavailable output succeeds with an explicit reason, null dataset/audit, and no partial assignments or summaries. The request has no algorithm field or default weights; the CLI accepts only `--input`, `--output`, `--quiet`, and the cross-workflow `--include-provenance` option; Plan and CLI output are card-free while the complete nested reusable dataset retains source cards. |
| List and standings functionality | Every documented totals, contribution, local-result, and explicit three-player standings input mode produces SkWO 6.3.1 performance totals from validated inputs; complete historical records aggregate into fixed-three-player 36-position lists; standings use more own wins, fewer own losses, then an explicit unresolved or executed lot; tests reconcile every supplied game contribution and tie case. Contracts version `1` supply the immutable played/passed representation, rotation, settlement-derived Entry Facts, cumulative totals, one standings snapshot per position, final standings, exact external-lot application, and independent completed-list comparison with one reference, stable-ID alignment, all fourteen final player-total deltas, and resolved-only rank movement. Strict root input/output schemas, runtime validation, concise CLI output, exactly three examples, recursive privacy checks, one-pass source execution, and three appended generated-output scenarios complete the bounded public workflow. It adds no series rollup, ratings, winner analysis, tournament management, or official reporting. |
| Interactive input and session capture | Issues #150 through #156 provide immutable fixed-three-player Session contracts, replay/transitions, readiness, information-safe Position and canonical Historical export, frozen Checkpoints, history editing, strict persistence, Public API/Provenance, and Schema. Issue #157 adds stable files, accepted-Log observation, isolated review, automatic exact Checkpoints, all 12 installed/module/Legacy subcommands, explicit existing-Application execution, Assistant capture, six examples, and eight scenarios. Export-only operations and ordinary mutations execute no analysis; no eighth Root workflow exists. |
| Stable installed interface | API contract version `1` exposes seven Root workflows and stable errors/results; installed, module, and Legacy forms preserve Root parity and share the additive Session parser, 12 subcommands, private Capture and Corpus command families, explicit paths, privacy-safe output, CAS persistence, and Exit Codes through one Console Script. Issue #189 adds Root modes and flags, Issue #192 adds the Historical Information-set Coaching flag, and Issue #194 adds the Historical Tactical Motif Review flag without adding a workflow or Console Script. Wheel/sdist clean installs verify 71 packaged Schemas, public Session files, Historical Claim, Information-set Coaching, and Tactical Motif execution, Session workflows, exact Capture/Corpus resources and help, and both local browser smoke flows. No Package-index publication is implied. |
| Session history editing | Version-1 contracts and behavior provide four Undo statuses, five Correction statuses, four Checkpoint relationships, strict-prefix reconstruction, exact suffix reporting, valid partial States, and deterministic replay. Public wrappers and CLI Undo/Correction with CAS Save and automatic resulting-State Checkpoints are implemented. Automatic Redo, arbitrary Log surgery, branching, and merge remain open. |
| Private Session persistence and resume | The private version-1 document/codec/file boundary provides deterministic State/content fingerprints, strict typed reconstruction and accepted-Log replay, canonical Checkpoints, recomputed lineage, canonical UTF-8 files, optimistic outcomes, and atomic replacement. Stable public Save/Load and all-three-form CLI orchestration preserve those semantics and omit paths from Results. Distributed locking, migration, merge/retry, encryption, cloud sync, and automatic backup remain open. |
| Examples | Examples cover each supported Root contract family and six strict Session creation/Command/correction/persistence documents; every example passes its applicable Schema and semantic validation. |
| Generated-output validation | The published `v0.17.0` matrix has 98 scenarios: the historical published `v0.16.0`, `v0.15.0`, and `v0.14.0` 85 remain unchanged, followed by three Issue #186 Historical Claim scenarios, four Issue #189 Information-set Search scenarios, two Issue #190 Multi-Step/Policy Comparison scenarios, two Issue #192 Information-set Replay Coaching scenarios, and two Issue #194 Tactical Motif Review scenarios. The historical published `v0.13.0` first 77 and historical published `v0.12.0` 70 remain Release evidence. |
| Python 3.13 | `pyproject.toml` requires Python 3.13 or newer, Ruff targets `py313`, GitHub Actions uses Python 3.13, Editable, Wheel, and sdist installation succeed on Python 3.13, and the full check passes there without a version matrix. |
| Regression testing | Ruff, 71-Schema packaged parity, Root and Session example validation, 98-scenario generated-output validation, distribution build and clean-install API/installed/module Root, Session, Capture, and Corpus CLI validation are the published `v0.17.0` gates. The published Package passes 7,479 tests in 921.96s. The historical published `v0.16.0` Package passes 6,925 tests in 1083.48s with its 63-Schema and 85-scenario baseline. The historical published `v0.15.0` Package baseline passed 6,510 tests, and the published `v0.14.0` baseline remains historical evidence for 5,892 tests. |
| Documentation | README, public field provenance, installed CLI, packaging, architecture, input/output, scoring, game-end, overbid, performance, examples, schema validation, roadmap, handoff, traceability, and scope documentation agree with behavior, rule ownership, stable fields, limitations, Python baseline, and release baseline. |
| Release hygiene | The human-reviewed `v0.17.0` candidate had only intended changes; Package metadata and Changelog used the approved version; `git diff --check` and the full check passed; the human maintainer created the tag and GitHub Release on 2026-08-25 at `8187fbe`. Issue #199 synchronizes that publication without product changes. |

The complete-game row's absent cross-game analysis is scoped to the public
Historical workflow. Issues #195 and #196 separately provide private Current-
Snapshot Tactical cross-game Counts and bounded Coaching. The Issue #195
nine-download statements are point-in-time boundaries; Issue #196 adds the
current tenth authenticated download.

Issue #191 supersedes the Match/Report/Teacher gap in the Information-set Search
row for the bounded private one-Decision path. Issue #192 supersedes its Match
Historical and Replay Coaching gap: the separate Coaching path uses complete
Information-set Candidates as primary evidence, treats PIMC/Immediate as
diagnostics without fallback, and reuses one retained Review; private Match
Historical controls use one Application invocation and time-safe fixed Policies.
Issue #193 adds repository-local benchmark evidence for the unchanged executor
and satisfies the bounded v0.17.0 performance-evidence contract. Issue #200
accepts the deterministic functional/structural contract for v1. Final Windows
and Ubuntu candidate evidence remains required; latency guarantees are not a v1
gate and do not retroactively block the published v0.17.0 Release.
See
[Match Information-set Search and Strategy Teacher Evidence](match_information_set_search_and_strategy_teacher.md)
and [Information-set Replay Coaching and Match Historical analysis](information_set_replay_coaching_and_match_historical_analysis.md),
plus [Information-set Search performance](information_set_search_performance.md).

The historical-game workflow satisfies deal-through-settlement for
`normal_completion`, exact-prefix declarer and defender concessions,
unanimously accepted declarer-card exposure, bounded terminal defender open
play, terminal open-card throwing, and a valid bounded party-wide Claim. Any
supported final reason may contain at
most one timed non-terminal defender-open-play or declarer-card-exposure
continuation. Normal completion retains all ten tricks and 30 actual plays; a
terminal chain ends after zero through 29 plays. Every supported terminal record can reconstruct one
information-safe pre-play state per actual card, including valid zero-decision
records. Continuation public hands are visible only after their event boundary,
and declared-Ouvert hands are visible from decision 1. Bounded review and
versioned provenance-aware training/evaluation records use that same actual-play
cardinality.
Training-data representation supports normal completion and all six shortened kinds
with one sample per actual play. Optional partition intent, exact overlap audits,
and strict declared unseen-player disjointness are implemented. Public complete
and unavailable Plan handling, lossless materialization, temporal Known-opponent
assignment, and Player-connected unseen-player assignment are also implemented.
Unseen-player optimization is local rather than global. Additional algorithms,
algorithm overrides, fallback or partial Plans, guaranteed ratios, Sample- or
Player-count balancing, component splitting, model training, and automatic
evaluation remain absent. General automatic splitting and unseen-player model
evaluation are not v1 requirements. Bounded
declared-Ouvert recommendation analysis is implemented; approved later end
reasons remain open. Historical statistics and rolling policy evaluation support
normal completion and all six shortened terminal reasons with game-level
source weighting, actual-play target weighting, and strict as-of safety. The
bounded flat 4.4.4 continuation hand constraint and bounded flat 4.4.5/4.1.6 returned-defender-hand
constraint are implemented for flat and timed historical play. At most one
supported non-terminal continuation may be followed by normal completion or at
most one supported terminal shortening. Multiple non-terminal continuation events and
arbitrary event streams are `not_supported_v1`. Full auction representation is
planned after v1.0.

Replay Coaching contract version `1` uses
`decision_time_then_retrospective_attachment`. Its decision-time value contains
no observed card, future play, later event, final hidden hand, final Skat,
winner, result, or settlement. Its retrospective value adds one legal observed
card and comparison fields without final-outcome context. Search evidence has
priority over Immediate evidence; compatible-world aggregation remains bounded
determinization subject to Strategy Fusion, and the observed card is not a
ground-truth optimal label. This foundation adds no causal outcome claim.
Prioritization version `1` adds at most five deterministic Key
Decisions, separate decision-opportunity and recorded-outcome Turning Points,
and threshold-free high-impact classification. Guidance version `1` adds
repeated one-game player, role, phase, and contract patterns plus bounded fixed-
template decision and pattern recommendations. Report version `1` composes one
complete report after guidance, then attaches allowlisted final outcome
context under `final_context_after_coaching`; outcome is not decision evidence.
The report adds privacy-safe game/player context, coverage, zero-preserving scope
summaries, and canonical limitations. Issue #124 exposes that exact report through
`--historical-replay-coaching`, a strict public schema, concise CLI presentation,
and normal Grand/Null/shortened generated-output coverage. It adds no tactical
motifs, cross-game analysis, player rating, or causal claim. See
[Replay coaching contracts](replay_coaching_contracts.md).

The generic position workflow now has bounded version-1 declarer-concession
adjudication under ISkO 4.4.1 and 4.4.2 plus defender-concession adjudication
under ISkO 4.4.3 with bounded 4.1.3 through 4.1.5 effects, plus unanimously
accepted final declarer-card-exposure adjudication under ISkO 4.4.4. A separate
flat-position continuation records both defender responses and constrains
Immediate, Multi-Step, Policy Comparison, and flat review with the exact public
declarer hand after an objection. Bounded exact post-game defender open-play
adjudication under the November 2022 wording of ISkO 4.4.5 supports at most five
unresolved tricks with private exact three-hand evidence. Separate continued
play under 4.1.6 fixes only the exposing defender's returned public hand and
creates no proof, assignment, result, settlement, or optional level obligation.
Bounded flat post-game open card throw under 4.4.6 supports either party, one
concrete complete thrown hand, empty through two-card current tricks, opposing-
party assignment, preexisting decisions, all four Null variants, and jack-only
theoretical Schwarz exclusion without exact proof or simulation.
Private version-1 party-wide Claim contracts, one exact-state preparation,
bounded exhaustive proof execution, valid-proof-only adjudication, complete
assignment and Game Result, and existing Final Settlement composition are
integrated through Historical Game input. Invalid or unavailable proof rejects
the asserted terminal record and creates no outcome. The 61-case Matrix version
`3` marks that bounded case `supported_as_is`. Runtime `GameShortening`, flat
Position, Session, Match Capture, and Corpus entry remain absent, and complete
Settlement coverage remains open. Claims and Final Settlement remain
`partially_supported` beyond this bounded slice. Specific
future-Trick Claims, generalized corrected play, generalized non-jack theoretical
exclusion, multiple non-terminal events, arbitrary event streams, simultaneous
throws, unlimited proof, free-text or natural-language interpretation, generative
adjudication, unclassified conduct, and defender proof beyond five unresolved
Tricks are `not_supported_v1`.

Bounded historical player-statistics aggregation is supported from the same
dataset container under either compliant policy, but it does not infer or change policy and is not a
training, quality-evaluation, or automatic policy-application gate.
Rolling known-opponent policy imitation is also supported with disjoint
partition names, intentional stable-player overlap, and strict as-of profiles. Its preferred-card match delta is not a
strategic recommendation-quality, optimality, significance, or unseen-player
generalization claim and does not close those broader gates.

The coherent hidden-world gate is bounded to Multi-Step execution consistency.
Issue #104 additionally constrains Immediate candidate worlds and coherent roots
with exact structural evidence while preserving private ownership boundaries.
It does not use tactical choices, profiles, historical future hands, results, or
settlement; change legal cards, policies, objectives, ties, training feature
version `1`, or rolling behavior; infer the real deal; or satisfy the separate
stronger-search gate. The privacy-safe summary remains schema version `1`. See
[Hidden-card inference](hidden_card_inference.md).

The version-1 bounded-search contract adds an immutable shared decision boundary,
a private perspective-neutral exact complete-world state with deterministic
legal transitions and neutral normal-terminal facts, explicit eligibility and
budgets, independent selected-world coverage and per-selected-world solution
claims, local-side terminal utility, privacy-safe common-prefix aggregates, and
a strict standalone schema. Exact solutions for a sampled selected set are
explicitly not exact over all compatible worlds. The executable exact-state
solver covers one Suit, Grand, or normal non-overbid Null world, uses canonical
full-window root values and deterministic below-root Alpha-Beta, and returns no
partial recommendation or fallback. Null uses exact trick ownership and fixed-
value settlement without a card-point secondary objective; overbid Null remains
unavailable. The private version-1 compatible-world layer constructs canonical
spaces, counts exactly, enumerates bounded spaces, samples larger spaces IID with
replacement, retains duplicate order, materializes strict exact states, and
verifies common legal roots. Compatible-world Minimax evaluates that frozen
order with one global node and timeout controller, fresh per-world exact-only
caches, per-world depth reset, and exact common-prefix aggregation. Timeout claim
`none` denies a reproducible complete selected-world solution, not exactness of
retained prefix values. It exposes no ownership and does not inspect coherent
execution roots. It remains determinization-based and subject to strategy
fusion; even exhaustive enumeration does not prove an optimal imperfect-
information policy. Explicit ongoing live recommendations now support strict
Search and Search-first auto fallback in flat and opt-in Multi-Step/Policy
Comparison paths. Multi-Step re-searches each public decision with a fresh
per-decision budget and domain-separated child seed, then executes the card in a
separate coherent world. Output includes privacy-safe decision, summary,
eligibility, and compact comparison diagnostics. Flat post-game Search,
Historical Search Review, bounded dataset evaluation, immutable profiles, and a
local performance baseline are implemented. Issue #200 accepts this as the
bounded v1 solver gate. Calibrated sampled quality and broader imperfect-
information policy solving are post-v1; guaranteed latency is not required. See
[Bounded search contracts](bounded_search_contracts.md).

Issue #190 applies the separate controlled-Player Information-set executor at
each Multi-Step public decision with a domain-separated child seed. Its Search
Worlds and private controlled Policy are decision-local and independent of the
coherent execution World. Policy Comparison appends the method exactly once and
last to the default four paths, keeps one shared coherent root through independent
copies, retains stopped rows as visible but ineligible, and preserves existing
ranking. It emits safe nested Results and exact 16-field diagnostics, with no
fallback and no change to `auto`, flat, Historical, or Dataset behavior. See
[Information-set Search Multi-Step and Policy Comparison](information_set_search_multi_step_and_policy_comparison.md).

Issue #191 adds the separate strict one-Decision Match/Report path and focused
Teacher/Dataset/Corpus propagation without changing the Issue #190 Multi-Step
behavior. See
[Match Information-set Search and Strategy Teacher Evidence](match_information_set_search_and_strategy_teacher.md).

Issue #192 adds the separate Information-set Replay Coaching and Match Historical
Information-set Review/Coaching path without changing that one-Decision Teacher
flow. See [Information-set Replay Coaching and Match Historical analysis](information_set_replay_coaching_and_match_historical_analysis.md).

Issue #193 adds the separate synthetic benchmark corpus, runner, focused tests,
and local reference measurements without changing production behavior. See
[Information-set Search performance](information_set_search_performance.md).

Issue #194 adds separate deterministic Historical Tactical Motif Review and
private Match browser controls without changing either Replay Coaching family.
See [Tactical motif evidence](tactical_motif_evidence.md).

Issue #195 adds separate private Current-Snapshot Tactical Motif Evidence, exact
descriptive cross-game summaries, and the Issue #195 point-in-time nine-download
Corpus integration without changing Dataset version `2` or any Package/API/
Schema/example/scenario count. See [Learning Corpus Tactical Motif evidence and
summaries](learning_corpus_tactical_motif_evidence_and_summaries.md).

Issue #196 adds separate deterministic Tactical Cross-game Coaching from exact
retained Tactical/Teacher evidence, complete-Search-only semantic consensus,
bounded repeated cross-Game focus and fixed Guidance, atomic third-family
publication, aggregate-only dashboard facts, and a tenth authenticated download.
It changes no Dataset version `2` or Package/API/Schema/example/scenario count.
See [Learning Corpus Tactical Cross-game Coaching](learning_corpus_tactical_cross_game_coaching.md).

## Release decision rule

The authoritative current status ledger, accepted limitations, closed B-01,
remaining B-02 through B-07 blockers, and ordered #201 through #207 plan are in the
[v1.0 scope and traceability audit](v1_0_scope_and_traceability_audit.md).

`v1.0.0` is not ready while any required gate lacks evidence, any validation or
test listed for a v1.0-required traceability row remains incomplete, any such
row remains less than `supported` without an approved bounded interpretation,
or any unresolved rule ambiguity affects a required settlement.
Post-v1.0 and not-required areas do not block the first major release. Remaining
implementation details for required areas must be approved and recorded before
their implementation begins.
