# AGENTS.md

This file contains project-specific instructions for AI coding agents working on `skatmind`.

## Project overview

SkatMind is a local Python-based Skat analysis and simulation tool.

The project focuses on:

* legal-card detection
* rule-based Skat position analysis
* Monte Carlo-style card analysis
* expected point swing estimation
* card recommendations
* multi-step simulation
* exact evidence-constrained hidden-card inference and compatible-world sampling
* information-safe bounded Search over exact and compatible worlds
* opponent policy modeling
* game result and settlement summaries
* automatic matador inference where supported by known declarer-card context and safe concrete-declarer completed-trick ownership
* post-game review support
* complete normal-play and supported shortened historical-game records
* two supported non-terminal historical continuation events
* information-safe historical decision snapshots and complete-game review
* versioned training and evaluation dataset records
* external and historically aggregated opponent statistics
* explainable confidence-gated opponent profiles
* live and time-safe historical profile application
* rolling opponent-policy evaluation
* dataset partition policies and stable-player overlap audits
* immutable internal interactive Live and Retrospective Session contracts,
  typed Commands, accepted revision Logs, deterministic transitions and replay,
  incremental validation, projections, export readiness, and canonical internal
  Retrospective Historical Request export
* deterministic internal strict-prefix Session Undo, one-command correction,
  first-rejection suffix replay, and Decision Checkpoint lineage
* private internal Session persistence and resume with canonical fingerprints,
  strict accepted-Log verification, optimistic conflict detection, and atomic
  same-directory file replacement
* stable public Session and Session file APIs, accepted-Log Decision
  Observations, isolated Checkpoint review export, automatic exact Checkpoint
  collection, installed/module/Legacy Session CLI parity, explicit Session-
  triggered analysis, and phase-aware local Assistant capture
* private internal persistent EuroSkat 36er Standard Match Workspaces with exact
  Slots and rotation, passed deals, revisioned changes, Progress, fingerprints,
  strict Resume, and optimistic atomic local Save
* private loopback-only local Match Capture browser transport with one explicit
  Workspace file, no-JSON creation and rapid entry, compare-and-swap autosave,
  explicit conflict Reload, packaged local assets, and Capture CLI parity
* editable Match-bound Player Statistics Snapshots with deterministic IDs,
  strict-before-Match eligibility, existing Profile derivation, canonical
  eligible preparation, and private browser Add, Replace, and Clear forms
* internal evidence-aware Match Decision preparation and strict existing-
  contract Historical, unpartitioned Training-source, and complete fixed-list
  materialization without workflow execution
* explicit private Match Decision and strict Historical Application execution,
  ephemeral revision-scoped reports, no-workflow Match materialization, and
  authenticated canonical loopback downloads
* private internal Learning Corpus identity, immutable exact Match Snapshots,
  closed References, lightweight Catalogs, deterministic fixed-root persistence,
  strict Store Resume and orphan reporting, immutable object publication,
  optimistic atomic Catalog Save, explicit Workspace import, and persisted
  Current-selection changes
* private internal Current-Snapshot-only minimized human Commentary and linked
  Response Evidence with exact source fingerprints, factual observed behavior,
  reconciled collection identity, and canonical in-memory export
* private internal Current-Snapshot-bound method-specific Strategy Teacher
  Evidence from exact executed Decision Analysis Reports with exact Request
  reconstruction, retained Result validation, deterministic identities/counts,
  and canonical in-memory export
* private internal Current-Snapshot-only Tactical Motif Evidence with safe
  reconstructed Decisions or explicit skips, exact shared single-game detector
  reuse, deterministic identities, and canonical path-free export
* private internal exact-Count Tactical Motif cross-game summaries with global,
  Player, role, seat, phase, contract, distinct-Game, distinct-Match, and bounded
  recurrence scopes without trait, quality, causal, or significance claims
* private internal deterministic Tactical Cross-game Coaching with exact
  Tactical/Teacher joins, retained exact Assessments, semantic Decision
  consensus, complete-Search-only repeated cross-Game focus, bounded Player
  Reports, and fixed Guidance without truth, trait, Rating, or causal claims
* private internal Current-Snapshot-only unpartitioned Learning Dataset version
  `2` with information-safe Decision State, separate observed behavior, time-safe
  Player Context, exact Teacher/Commentary/Response joins, skipped and unjoined
  evidence, deterministic identities, and canonical in-memory export
* private internal Match-Snapshot-safe Dataset-v2 partition preparation with
  temporal Known-player and Player-component unseen-player algorithms, leakage
  audits, lossless indexes, and canonical export
* private internal Dataset-v2 cross-game Match, Player, Communication, Strategy,
  Coverage, and supplied-partition-readiness summaries with exact Counts,
  deterministic identities, and canonical path-free export
* private loopback-only local Learning Corpus browser workflow with one explicit
  root, strict Workspace and executed-Decision Report-source uploads, explicit
  Current selection, bounded process-local sources, exact unlocked artifact
  preparation, atomic generation-safe publication, minimized presentation, and
  ten authenticated canonical
  downloads without derived persistence or public contracts
* JSON input/output for regression-friendly testing

The current implementation is not a machine-learning model or a full official
tournament system. It includes bounded late-game Perfect-Information Minimax for
exact worlds, but not a general hidden-information, complete-contract, or full
official Skat solver. Future product scope is defined in
[`docs/v1_scope.md`](docs/v1_scope.md).

## Language rules

Repository code, tests, comments, docstrings, JSON keys, CLI output, and program output must remain in English.

Planning conversation may be in German, but all repository changes must be written in English.

## Table assumption

The project assumes a fixed three-player Skat table. Four-player table support
is unconditionally out of scope.

## Development workflow

Use small, test-driven changes.

For each task:

1. Inspect the relevant files before editing.
2. Propose a short implementation plan.
3. Make the smallest useful change.
4. Add or update focused tests.
5. Run targeted tests first.
6. Run the full check script before considering the task complete.
7. Do not update unrelated files.
8. Do not perform broad refactors unless explicitly requested.

## Standard check command

Use this command for the full project check:

```powershell
.\scripts\check.ps1
```

The full check covers:

* Ruff checks
* packaged-schema filename and byte parity
* input JSON schema validation
* generated output JSON schema validation
* Wheel, sdist, and clean-install API/installed/module CLI validation
* pytest regression tests

## Useful focused checks

Run specific tests when working on focused areas:

```powershell
python -m pytest tests/test_post_game_review.py
python -m pytest tests/test_matador_inference.py
python -m pytest tests/test_cli.py
python -m pytest tests/test_examples.py
python scripts/validate_examples_schema.py
python scripts/validate_generated_outputs_schema.py
```

## Agent governance

OpenCode and all other coding agents must not:

* commit or amend commits
* push changes
* create, switch, rename, or delete branches
* create, move, or delete tags
* create or modify GitHub Releases
* create, update, comment on, close, reopen, or otherwise modify GitHub issues

Agents may:

* inspect the repository and Git history
* edit files for an explicitly assigned task
* run focused checks and the full project check
* inspect `git status` and `git diff`
* provide a ready-to-paste concise English commit message
* provide a ready-to-paste English GitHub issue update comment

Git and GitHub publication actions are performed manually by a human maintainer.

## Documentation sources

Before larger changes, read the relevant documentation:

* `README.md`
* `docs/v0_17_release_readiness_audit.md`
* `docs/v1_0_scope_and_traceability_audit.md`
* `docs/project_handoff.md`
* `docs/roadmap.md`
* `docs/architecture.md`
* `docs/skatmind_rename_and_migration.md`
* `docs/input_json.md`
* `docs/output_json.md`
* `docs/application_orchestration.md`
* `docs/session_persistence_and_resume.md`
* `docs/public_session_api_v1.md`
* `docs/session_provenance.md`
* `docs/session_decision_observations.md`
* `docs/session_cli_and_end_to_end_capture.md`
* `docs/match_capture_contracts.md`
* `docs/match_workspace_contracts.md`
* `docs/local_match_capture_interface.md`
* `docs/match_review_and_materialization.md`
* `docs/match_analysis_and_exports.md`
* `docs/match_information_set_search_and_strategy_teacher.md`
* `docs/learning_dataset_v2.md`
* `docs/learning_corpus_browser_workflows.md`
* `docs/learning_corpus_tactical_motif_evidence_and_summaries.md`
* `docs/learning_corpus_tactical_cross_game_coaching.md`
* `docs/information_set_search_workflows.md`
* `docs/information_set_search_multi_step_and_policy_comparison.md`
* `docs/information_set_replay_coaching_and_match_historical_analysis.md`
* `docs/information_set_search_performance.md`
* `docs/tactical_motif_evidence.md`
* `docs/installed_cli.md`
* `docs/public_field_provenance.md`
* `docs/v1_information_provenance_enforcement.md`
* `docs/examples.md`
* `docs/schema_validation.md`
* `docs/requirements_traceability.md`
* `docs/v1_scope.md`

Do not assume old behavior if documentation or tests say otherwise.

## Current release state

The current published stable and latest stable GitHub Release is `v0.17.0`, with
release theme "Rules, Search, Coaching, and performance closure" and GitHub
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
`91b1360`. Package version `0.16.0` requires Python `>=3.13`, retains Public API
contract version `1`, exactly seven Root workflows, and one Console Script. It
contains 63 authoritative Schemas, 63 Packaged Schema Resources, six Session
examples, 85 deterministic generated outputs, and 6,925 passing pytest tests in
1083.48s. Issues #171 through #179 complete that functional milestone, Issue
#180 completed Release preparation, and Issue #181 synchronized publication
status without changing product behavior.

The published `v0.17.0` functional history uses Package version `0.17.0`, Python
`>=3.13`, Public API contract version `1`, exactly seven Root workflows, one
Console Script, and six Session examples. Issue #186 updates the Settlement
Normative Matrix to version `3` with the same 61 cases and implements the approved
Claim through Historical Game input only. Issue #189 adds four Information-set
Search Schemas, one example, and four generated-output scenarios. Issue #190
adds strict Information-set Search Multi-Step and Policy Comparison integration,
one example, and two scenarios without adding a Schema, bringing the working tree
to 69 authoritative and packaged Schemas and 94 scenarios. The published
`v0.16.0` counts above remain unchanged Release facts.

Issue #191 adds strict private one-Decision Match Information-set Search, exact
Report-source transfer, focused Strategy Teacher Evidence, Dataset-v2 joins,
cross-game counts, and existing Corpus workflow support without changing those
counts or public/versioned surfaces.

Issue #192 adds separate Historical Information-set Replay Coaching, private
Match Historical Information-set Review and Coaching controls, one strict
Schema, one Root example, and two append-only scenarios. The working baseline at
that point therefore has 70 authoritative and packaged Schemas and
96 scenarios.
Package version, Public API contract, seven Root workflows, one Console Script,
Settlement Matrix version `3` with 61 cases, and six Session examples remain
unchanged.

Issue #193 adds a deterministic synthetic Information-set Search benchmark
corpus, a strict repository-local runner and focused regression tests, and
documented local reference measurements. It changes no production code, Schema,
route, profile, Public API, Package version, example, generated scenario, or the
working counts above.

Issue #194 adds deterministic Historical Tactical Motif Review, private Match
browser controls, one strict Schema, one Root example, and two append-only
scenarios. The final published baseline therefore has 71 authoritative and
packaged Schemas and 98 scenarios. Existing Package/API/workflow/Console-Script/
Settlement/Session baselines remain unchanged.

Issue #195 adds private Current-Match-Snapshot-only Tactical Motif Evidence,
explicit Decision skips, exact global/Player/scope/recurrence summaries, atomic
process-local Corpus preparation, minimized presentation, and two authenticated
canonical downloads. It changes no Package/API/workflow/Console-Script/Schema/
example/generated-scenario/Session/Dataset-v2 baseline, so the working counts
above remain unchanged.

Issue #196 adds private deterministic Tactical Cross-game Coaching from exact
Tactical/Teacher joins, one Assessment per exact Teacher Report, semantic
Decision consensus, complete-Search-only repeated cross-Game focus, bounded
fixed Guidance, atomic third-family Corpus publication, minimized aggregate
presentation, and a tenth authenticated canonical download. It changes no
Package/API/workflow/Console-Script/Schema/example/generated-scenario/Session/
Dataset-v2 baseline, so the working counts above remain unchanged.

Issue #197 records the documentation-only scope and Release-readiness audit.
Issue #198 changes only Package metadata, current version expectations,
Changelog, and Release-candidate documentation to prepare `v0.17.0` without
product behavior changes. The maintainer subsequently published `v0.17.0` on
2026-08-25 at `8187fbe`, and Issue #199 performs only the post-publication
documentation synchronization. Issues #182 through #196 are the functional
milestone; Issues #197, #198, and #199 add no product functionality.

The historical published `v0.15.0` GitHub Release has release theme "Local
EuroSkat 36er Match capture, analysis, and exports" and GitHub Release title
"v0.15.0 — Local EuroSkat 36er Match capture, analysis, and exports". It points
to commit `ec1c154`. Package version `0.15.0` requires Python `>=3.13`, retains
Public API contract version `1`, exactly seven Engine Root workflows, and the one
`skat-ai = skat_ai.cli:main` Console Script, and contains 63 authoritative
Schemas, 63 Packaged Schema Resources, six Session examples, 85 deterministic
generated-output scenarios, and 6,510 passing pytest tests. Issues #160 through
#168 complete the functional milestone, Issue #169 completed Release
preparation, and Issue #170 synchronized publication status. Publication was
performed manually by the maintainer. GitHub Releases remains authoritative for
publication status; no Package-index or PyPI publication is claimed.

The historical published `v0.14.0` GitHub Release has release theme
"End-to-end Live and Retrospective Session capture" and GitHub Release title
"v0.14.0 — End-to-end Live and Retrospective Session capture". It points to
commit `d5589f8`. That Package version requires Python `>=3.13`, retains
Public API contract version `1` and exactly seven Engine Root workflows, and
contains 63 authoritative Schemas, 63 Packaged Schema Resources, six Session
examples, 85 deterministic generated-output scenarios, and 5,892 passing pytest
tests. Issues #150 through #157 complete the functional milestone, and Issue
#158 completed Release preparation. Publication was performed manually by the
maintainer, and Issue #159 synchronized its publication status. GitHub Releases
remains authoritative for publication status; no Package-index or PyPI
publication is claimed.

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

The published `v0.13.0` baseline implements public API contract version `1`
through Issue #137, which establishes the stable `skat_ai.api.v1` and
`skat_ai.errors` namespaces, immutable JSON document wrappers, compatibility
metadata, stable errors, Exit Code constants, and the legacy CLI-error alias. Issue #139 adds
internal Application orchestration version `1`, immutable invocation, option,
result, external-document, and artifact contracts, no-I/O dispatch for all seven
Root workflows, legacy CLI transport parity, and unchanged public API exports.
Issue #140 adds the executable public Python API v1 facade, direct immutable
workflow options, public execution results and artifacts, lazy source/editable
schema validation, stable boundary-error translation, and all-seven-workflow
Application parity. Issue #141 adds explicit Setuptools build metadata, Package
Resource schemas, schema synchronization and parity, `py.typed`, Package
`__version__`, one Wheel and one sdist, artifact inspection, clean-install API
smoke validation, and local/CI distribution gates. Issue #142 adds installed CLI
contract version `1`, the exact `skat-ai` Console Script, `python -m skat_ai`, a
Package-owned canonical CLI, the Legacy Root compatibility facade, `--version`,
and clean-install CLI/API parity. Issue #138 adds the internal version-
1 field-level provenance language, immutable sidecar ledgers, RFC 6901 paths,
coverage and dependency validation, Information Use Context, public redaction,
and safe serialization. Issue #143 adds internal Application provenance bundles,
complete live decision ledgers, Immediate, Search, inference, Multi-Step, and
Policy Comparison propagation, and an all-leaf partial-legacy Position Result
ledger. Issue #144 extends internal provenance through flat retrospective
Position Analysis, Historical Snapshots, Immediate and Search Review, Replay
Coaching, and an all-leaf partial-legacy Historical Result ledger. Issue #145
adds internal Dataset, Preparation, Opponent, Profile,
historical-list, and comparison provenance with complete non-legacy Root Result
ledgers. Issue #146 completes the remaining non-legacy Position and Historical
Result ledgers from retained Declaration, Value, Overbid, score, Result,
Settlement, Performance, list, ending, continuation, canonical record, replay,
and point values. Issue #147 adds bounded public field-provenance contract
version `1`, immutable attachments/artifacts/bundles, seven explicit Root Result
mappings, the actual
`opponent_statistics_input` artifact mapping, complete post-redaction coverage,
default-false Public API and all-three-form CLI opt-in, strict Schema, and seven
append-only generated-output scenarios. The published baseline has 62 schemas and
77 generated-output scenarios, while the historical published `v0.12.0` facts
remain 70 scenarios and 4,762 tests.

The published `v0.14.0` milestone has the release theme "End-to-end Live and
Retrospective Session capture". Issue #150 establishes internal Session
contract and Command version `1`, stable Players and seats, Capture Modes,
phases, an authoritative accepted Command Log, linear revisions, Diagnostics,
export readiness, and Transition Result semantics. Issue #151 adds deterministic
revision-zero creation, accepted-Log replay, immutable projection, atomic Command
application, phase advancement, incremental rule and information-policy
validation, trick/event/end derivation, promotion, and Position/Historical
readiness. Issue #152 adds immutable available/unavailable Session Request
Export version `1`, exact ready-Retrospective projection mapping, canonical
Historical builder round trip, and internal `RequestDocumentV1` construction.
Issue #153 adds immutable Position Export Options version `1`, information-safe
one-replay Position Request export, declared-Ouvert public-hand capture, existing
Position builder validation, and immutable replay-verified pre-Play Decision
Checkpoints. Issue #154 adds internal Session History Edit version `1`, immutable
strict-prefix Undo, one-command correction with deterministic first-rejection
suffix replay, partial corrected States, and current/ancestor/future/diverged
Checkpoint lineage. Issue #155 adds internal Session Persistence version `1`,
canonical State/content fingerprints, strict reconstruction and replay, optional
caller-supplied frozen Checkpoints with recomputed lineage, optimistic content-
fingerprint conflicts, canonical local file load, and atomic save. Session-
triggered analysis and transport are added later by Issue #157. Issue #156 adds stable
`skat_ai.api.v1.session` version `1`, exact immutable contract re-exports, public
Command parsing, ten transport-free in-memory operations, one typed Result
envelope, default-omitted complete redacted Session Provenance, strict standalone
Session Schema, 63-Schema Package parity, and clean-install validation. Issue
#157 adds stable `skat_ai.api.v1.session.files` Save/Load, Decision Observation,
isolated Checkpoint review export, automatic collection, all 12 Session CLI
subcommands across installed/module/Legacy invocation, explicit Position and
Historical execution, the phase-aware Assistant, six examples, and eight
append-only scenarios. The `v0.14.0` Package baseline has 85 generated outputs
and 63 authoritative and packaged Schemas. Issue #158 completed Package version
`0.14.0` and Release-documentation preparation without changing product
behavior. The maintainer subsequently published the Release manually at commit
`d5589f8`.
Online-platform adapters, browser extensions, website scraping, cloud
synchronization, distributed locking, encryption/key management, and automatic
backup policy remain open.

The published `v0.15.0` milestone provides usable manual
post-game capture of one EuroSkat 36er Standard Match from descriptive video
evidence.
Issue #160 begins it with internal Match source, timecode, tournament-format,
participant, optional statistics-snapshot, identity, perspective, and
deterministic serialization contracts. Issue #161 adds internal evidence-aware
observed Games, partial and complete Play validation, free-text Decision
commentary on any Player, linked later responses, and deterministic evidence
summaries. Issue #163 adds internal persistent 36-position Match Workspaces,
explicit passed deals, immutable changes, Progress, fingerprints, strict Resume,
and optimistic atomic local Save. Issue #164 adds internal transport-free rapid-
entry Application services with UI-ready Position Views, automatic Player and
Decision derivation, exact or bounded selectable Cards, setup updates, atomic
Play append, truncation, annotation reconciliation, and passed/clear wrappers.
Issue #165 adds the private local version-1 Web/Protocol and Capture CLI,
loopback token and same-origin protection, no-JSON creation and strict Resume,
the 36-position browser interface, packaged assets, and optimistic autosave with
explicit conflict Reload. Issue #166 adds Match-bound Snapshot editing,
deterministic IDs, strict-before-Match Context/Preparation, existing Profile
derivation, and private browser forms without policy application. Issue #167
adds internal information-safe Decision preparation, strict normal-completion
Historical materialization, unpartitioned Training source Records, and complete
36-position list construction with existing aggregation and external-lot
behavior. Issue #168 adds explicit private one-Decision Position and strict
Historical execution through the existing Application, eligible relative Profile
application through existing supported behavior, no-workflow Match
materialization, ephemeral revision-scoped reports, and authenticated canonical
loopback downloads. It completes the functional `v0.15.0` local Match Capture
milestone. Issue #169 changed only the Package version, current version
assertions, Changelog, and release-state documentation to complete Release
preparation. The maintainer published the Release manually at commit `ec1c154`,
and Issue #170 synchronizes that publication status. No Package-index or PyPI
publication is claimed. Public
Match API, Match Schema/data workflow, public/persisted Player Catalog, communication-
aware Dataset work, database/remote deployment, YouTube integration, and
EuroSkat integration remain absent. `v1.0.0` remains unready.

The published `v0.16.0` milestone is `v0.16.0 — Learning-ready behavior
and communication data`. Issues #171 through #179 implement private immutable Match
Snapshot identity, closed References, lightweight Catalogs, deterministic Corpus
persistence, strict Resume and orphan reporting, explicit Workspace import, and
persisted explicit Current-selection changes, plus a derived Current-Snapshot
Player Catalog, exact alias conflicts, retained Statistics history, and time-safe
selection, plus minimized exact human Commentary and linked Response Evidence
export, plus exact executed Decision Report Strategy Teacher Evidence with
Current-Snapshot reconciliation and canonical export, plus one Current-Snapshot-
only unpartitioned task-neutral Learning Dataset version `2` with separate
Decision State, observed behavior, Player Context, Strategy Teacher, Commentary,
and linked Response families, plus Match-group-safe deterministic partition
preparation, temporal Known-player and component-based unseen-player algorithms,
leakage audits, lossless partition indexes, and canonical export, plus private
exact-Count cross-game Match, Player, Communication, Strategy Teacher, Coverage,
Dataset Readiness, and supplied Partition Readiness summaries with deterministic
path-free export. Issue #179 completes the functional private local workflow with
the separate installed/module/Legacy `corpus` command, strict uploads, explicit
Current selection, process-local Report sources and prepared values, and seven
authenticated canonical downloads. Issue #180 changes only Package version and
current version expectations, Changelog, and Release-state documentation to
prepare `v0.16.0` without product behavior changes. The Package version is
`0.16.0`; that published baseline retains 63 authoritative and packaged Schemas,
six Session examples, 85 generated outputs, and 6,925 pytest tests. The maintainer published the
Release manually on 2026-08-18 at commit `91b1360`, and Issue #181 synchronizes
that publication status. GitHub Releases is the authoritative publication
record; no Package-index or PyPI publication is claimed.

The `v0.17.0 — Rules, Search, Coaching, and performance closure` functional
milestone is complete through Issue #196. Issue #182 closes the Claim product-
decision gate and approves one
bounded Retrospective party-wide all-remaining-Tricks Claim, and classifies every
other current Claim boundary as `not_supported_v1`. Issue #183 adds private
version-1 structured Claim, complete Evidence, exact-state, Proof Request,
preparation, assignment, diagnostic-line, and Result contracts without proof or
Runtime execution. Issue #184 adds private bounded exhaustive exact AND/OR proof
execution without Runtime behavior. Issue #185 adds private valid-proof
adjudication and existing Final Settlement composition. Issue #186 updates
Settlement Normative Matrix version `3` while preserving all 61 case IDs and
completes the approved bounded Claim and Final Settlement runtime slice through
Historical Game input only. Session, Match Capture, and Corpus Claim entry remain
open. Issue #187 defines private information-set Search World State, actor
Observation, fixed Policy, Budget, Request, Preparation, controlled-Policy, and
Result contracts. Issue #188 adds the private bounded exhaustive selected-world
best-response executor with retained-Preparation validation, fixed-player
rollout, controlled Information-set grouping, exact terminal utility, complete
contingent Policy retention, structural partial/timeout behavior, and invocation-
local memoization. Issue #189 adds strict flat `information_set_search`,
same-selection PIMC plus independently seeded Immediate retrospective comparison,
separate Historical Review and Training Dataset evaluation, safe public Results,
retained-stage Provenance, CLI, four Schemas, one example, and four generated
scenarios. Issue #190 adds strict Multi-Step and Policy Comparison integration
version `1`: fresh public-state Search with domain-separated child seeds at each
local decision, private independent coherent execution Worlds, no Search World or
Policy reuse, no-recommendation stopping without fallback, safe nested Results,
16-field diagnostics, shared-root independent comparison paths, append-once-last
ordering, stopped-row ineligibility, and retained-Result complete Provenance.
Existing `auto` is unchanged. Match Capture, Match Analysis Reports, Strategy
Teacher are integrated for the bounded one-Decision path by Issue #191 together
with Dataset-v2 and Corpus propagation. Issue #192 adds separate Information-set
Replay Coaching and Match Historical Information-set Review/Coaching with one
retained Review, no PIMC/Immediate fallback, time-safe fixed Profile Policies,
 and complete Provenance. Issue #193 adds repository-local benchmark evidence
without changing product behavior or versioned surfaces. Issue #194 adds
deterministic Historical Tactical Motif Review and private Match browser controls
without changing either Coaching family. Issue #195 reuses that exact detector
for separate Current-Snapshot-only Corpus Evidence, exact descriptive cross-game
summaries, and nine current browser downloads without changing Learning Dataset
version `2`. Issue #196 adds separate deterministic Tactical Cross-game Coaching
from exact retained Tactical/Teacher evidence, complete-Search-only consensus,
bounded repeated cross-Game focus and fixed Guidance, and a tenth current browser
download without changing Dataset version `2`. Issue #193 satisfies the bounded
v0.17.0 performance-evidence contract. Issues #182 through #196
are the frozen functional history. Issue #197 completes the documentation-only
scope and Release-readiness audit, and Issue #198 prepares Package `0.17.0` and
the Release candidate without product behavior changes. The maintainer published
`v0.17.0` on 2026-08-25 at `8187fbe`, and Issue #199 synchronizes that publication
without product functionality. Issue #200 freezes the bounded `v1.0.0` scope,
classifies all 53 required traceability rows, and records seven blockers plus the
exact #201 through #207 follow-up sequence without changing product code.
Issue #201 adds independent exhaustive official-rule evidence for R-01 and R-06
without changing product code and closes B-01. Issue #202 completes mandatory
internal load-to-final-serialization Provenance for all seven Root workflows,
makes P-10 and P-13 `satisfied`, and closes B-02 without widening public
Provenance. Issue #203 completes all nine concrete canonical Multi-Step phases,
makes P-19 `satisfied`, and closes B-03 without widening Search or public
contracts. Issue #204 applies the `AGPL-3.0-only` Package boundary and closes
B-04. Issue #205 completes the hard-cut SkatMind Package/import/CLI/resource/
Schema/identifier migration, strict legacy persisted-input support, and reviewed
historical-evidence boundary, makes P-09 `satisfied`, and closes B-08. B-09 adds
maintainer UAT outside the 53-row ledger. Issue #206 adds exact direct dependency
floors and the validation-only source/Editable/Wheel/sdist Windows/Ubuntu matrix,
makes P-34 `satisfied`, and closes B-05 after both merged Ubuntu jobs pass. Issue
#207 completes the final technical audit, closes B-06 with no material technical
blocker, and approves Issue #208 maintainer UAT as the next action. B-09 and B-07
remain open, so `v1.0.0` is not ready.
No v1 Release title, theme, date, tag, publication commit, or production model is
frozen.

Major completed areas include:

* automatic matador inference
* post-game review decision quality
* post-game review decision factors and explanations
* post-game review recommendation gap details
* CLI output for post-game review summaries
* left/right opponent policy support
* basic defender cooperation improvements
* final settlement and overbid handling
* partial fixed-three-player SkWO-style performance rating
* fixed three-player list standings output
* list-performance examples and generated-output validation
* CLI usability improvements including discoverable help text and optional quiet JSON-output runs
* generated-output validation for representative user-facing workflows
* late-game public input support including zero opponent hand sizes
* strict live completed-trick `winner_role` verifiability
* conservative matador inference from concrete completed-trick ownership
* objective-aware post-game review CLI wording
* richer post-game review examples and explanation coverage
* controlled left/right opponent policy effect coverage
* bounded profile-confidence opponent policy behavior
* settlement and overbid edge-case coverage audit
* canonical Suit and Grand declaration dependencies and official matador bounds
* SkWO 6.3.1 unresolved standings ties and external lot order
* bounded impossible Null settlement
* complete normal-play historical-game records
* information-safe snapshots for all 30 historical decisions
* bounded complete historical-game decision review
* versioned provenance-aware training and evaluation dataset records
* versioned external opponent statistics with exact or estimated scoped evidence
* deterministic explainable confidence-gated opponent profiles
* stable-ID live profile bindings and strict time-safe historical application
* exact historical opponent-statistics aggregation and reusable export
* rolling known-opponent behavioral policy evaluation
* known-opponent and unseen-player dataset policies with overlap audits
* public mode-derived automatic Training Dataset preparation with complete or explicit unavailable results, lossless version-1 dataset materialization, partition audits, strict schemas, CLI, examples, and generated-output coverage
* structured declarer and defender concessions, accepted declarer-card exposure, bounded defender open play, and open-card throwing
* continued play with exact public hands after declarer-card exposure or defender open play
* exact-prefix historical records for all six supported shortened terminal events
* variable-length historical snapshots, review decisions, and training samples, including zero-decision records
* shortened-game historical statistics, export, and rolling opponent-policy evaluation
* declarer-concession integration in historical statistics, export, and rolling opponent-policy evaluation
* unanimously accepted declarer-card-exposure historical records and variable-length workflow integration
* terminal bounded exact defender-open-play historical records and variable-length workflow integration
* timed non-terminal historical defender-open-play continuation with persistent public-hand information
* timed non-terminal historical declarer-card-exposure continuation with persistent public-hand information
* declared-Ouvert-aware Immediate, Multi-Step, Policy Comparison, flat review, and historical review simulation
* coherent private hidden-world ownership across each Multi-Step path and shared-root Policy Comparison
* exact nine-row canonical Multi-Step phase classification, same-World completion
  of the three former opponent-only gaps, and local-Decision-only step counting
* exact compatible-world counting, marginals, and DP-guided sampling from confirmed public failure-to-follow evidence
* immutable information-safe bounded-Search views and exact legal states
* Suit, Grand, and all four normal non-overbid Null exact-world Minimax
* exact compatible-world counting, canonical enumeration, deterministic IID sampling with replacement, and common-prefix aggregation
* strict Search, Search-first auto, Multi-Step, Policy Comparison, flat post-game, Historical Search Review, and dataset-evaluation integration
* immutable Search budget profiles, strict-improvement and convergence fixtures, and measured reference performance
* immutable 61-case Settlement Normative Matrix version `3`, closed v1 Claim
  product decisions, one supported bounded Historical Claim, and bounded
  continuation-before-shortening historical chains
* private immutable version-1 party-wide Claim, complete Evidence, exact-state,
  Proof Request/preparation, assignment, diagnostic-line, and Result contracts
  plus bounded exhaustive exact AND/OR proof execution, private valid-proof
  adjudication, and existing Final Settlement composition with Historical-only
  runtime integration, strict diagnostic output, Provenance, CLI,
  Review/Coaching, Dataset, list, and statistics compatibility
* private version-1 information-set Search World State, actor Observation,
  deterministic fixed-Player Policy, Budget, Request, Preparation, controlled-
  Policy, consumed-budget, and Result contracts with ordered Compatible-world
  reuse and pure exact transitions, plus private bounded exhaustive selected-
  world best-response execution, strict retained-Preparation validation, fixed-
  player rollout, equal controlled-Observation grouping, complete contingent
  Policies, conservative partial/timeout Results, and invocation-local World and
  ordered-bundle memoization, plus strict flat routing, safe aggregate output,
  same-selection retrospective comparison, separate Historical Review and
  Training Dataset evaluation, retained-stage Provenance, CLI, Schemas, example,
  and generated-output coverage, plus strict Multi-Step and Policy Comparison
  integration with per-decision Search isolation, safe Decisions/diagnostics,
  no fallback, shared coherent comparison setup, and complete Provenance
* deterministic synthetic Information-set Search benchmark coverage with strict
  loading, frozen functional and structural signatures, Strategy-Fusion and
  duplicate-weight diagnostics, and local reference timings without elapsed-time
  gates
* separate version-1 Information-set Replay Coaching with retained Historical
  Information-set Review reuse, complete Candidate-only assessment, diagnostic
  PIMC/Immediate without fallback, existing Key Decision/Turning Point/pattern/
  Guidance reuse, isolated Outcome Context, complete Provenance, strict Schema,
  CLI, example, generated scenarios, and private Match Historical controls
* separate version-1 Historical Tactical Motif Review with one retained Snapshot
  sequence, exact structural lead/void/Trick-control/Defender-partnership/hand-
  shape/outcome evidence, strict timing and privacy, complete Provenance, Schema,
  CLI, example, generated scenarios, and private Match browser controls
* private Current-Snapshot-only Learning Corpus Tactical Motif Evidence with
  every observed Decision represented by exact Evidence or an explicit skip,
  safe partial-Match/final-Trick behavior, deterministic identities, and
  canonical path-free export
* private exact-Count Tactical Motif cross-game global, Player, role, seat,
  phase, contract, distinct-Game, distinct-Match, and recurrence summaries
  without rates, traits, quality, significance, causal, or communication claims
* private deterministic Tactical Cross-game Coaching with one retained
  Assessment per exact Teacher Report, exact semantic Decision consensus,
  unanimous complete-Search-only focus eligibility, at-least-two-Decision and
  at-least-two-Game thresholds, at most five fixed-Guidance focus areas per
  Player, zero-count Catalog-order Player Reports, and no truth, perfect-play,
  Rating, intent, communication, causal, or significance claim
* information-safe one-game Replay Coaching evidence, prioritization, patterns, deterministic recommendations, complete report, public schema, JSON, CLI, examples, and generated-output coverage
* fixed-three-player 36-position historical-list contracts, aggregation, progression, standings, exact external-lot application, independent-list comparison, public JSON/schema/CLI workflows, examples, and generated-output coverage
* deterministic public automatic Training Dataset preparation with temporal Known-opponent and Player-disjoint unseen-player assignment, complete or unavailable Plans, lossless materialization, strict schemas, CLI, examples, and generated-output coverage
* stable public API contract version 1 with exact exports, immutable JSON Request and Result wrappers, compatibility metadata, public errors, and legacy Root CLI compatibility
* internal field-level information provenance contract version 1 with immutable sidecar ledgers, deterministic coverage auditing, dependency and temporal validation, context-use policy, public redaction, and safe serialization
* mandatory internal version-1 exact Request/effective-option/external-source,
  pre-analysis context, retained-stage authorization, and final Result/artifact
  serialization enforcement for all seven Root workflows
* internal Application orchestration version 1 with immutable contracts and options, seven in-memory workflow handlers, six isolated Training Dataset operations, injected Opponent Statistics, auxiliary artifacts, no-I/O dispatch, and legacy CLI transport parity
* executable public Python API version 1 with immutable direct options, all-seven-workflow execution, separate artifacts, lazy Package Resource schema validation, and stable boundary errors
* installation-ready Setuptools Wheel and sdist artifacts with byte-identical packaged schemas, typing metadata, Package version export, and clean-install validation
* Package-owned installed and module CLI entry points with canonical parsing, direct Application execution, Legacy Root compatibility, and clean Wheel/sdist command validation
* internal live Position provenance enforcement across Immediate, Search,
  Hidden-card inference, Multi-Step, and Policy Comparison without public output
* internal retrospective provenance enforcement across flat post-game Position
  Analysis, Historical Review and Search Review, Replay Coaching, and selected
  Position/Historical Result branches without public output
* internal Dataset, Preparation, Opponent, Profile, historical-list, and
  comparison provenance with complete non-legacy Root Result ledgers and no
  public output
* complete internal non-legacy Position and Historical Root Result provenance,
  including base Historical execution without review options
* bounded opt-in public Root Result and actual-artifact field provenance with
  immutable public API values, strict Schema, CLI parity, redaction, and complete
  recomputed coverage
* immutable internal version-1 Session and Command contracts for Live and
  Retrospective authoring, including fixed Players, Capture Modes, phases,
  accepted revision Logs, Diagnostics, readiness, and Transition Results
* deterministic internal Session transition engine and projection version `1`
  with revision-zero creation, full accepted-Log replay, atomic rejection,
  monotonic phases, incremental Deal-through-end validation, and export readiness
* internal Session Request Export version `1` with normal available/unavailable
  Results, one-replay Historical readiness gating, exact projection mapping,
  canonical Historical validation and round trip, and immutable existing Root
  Request construction without workflow execution
* internal information-safe Session Position Request export with immutable
  explicit analysis options, stable-to-relative mapping, declared-Ouvert and
  continuation public hands, and existing Position validation without execution
* immutable internal pre-Play Decision Checkpoints with replay-verified source
  revision, actor/seat/index metadata, relative Player map, and frozen existing
  Position Request
* immutable internal Session History Edit version `1` with exact-prefix Undo,
  one-command correction, linear suffix replay, normal partial results, and
  derived Decision Checkpoint lineage
* internal Session Persistence version `1` with private authoritative-Log
  documents, optional frozen Checkpoints, domain-separated SHA-256 identity,
  strict resume, derived lineage, optimistic conflict results, and durable-
  intent same-directory atomic replacement
* stable public Session API version `1` with exact immutable type identity,
  strict Command parsing, ten one-call in-memory operations, typed Results,
  optional complete redacted Session Provenance, a standalone packaged Session
  Schema, and clean-install validation
* stable public Session file API version `1` with exact Save/Load exports,
  path-free Results, strict resume, optimistic compare-and-swap, and atomic Save
* immutable accepted-Log Decision Observation and frozen-request-plus-observed-
  Card Checkpoint review export with optional complete Session Provenance
* automatic exact Decision Checkpoint collection with equality deduplication and
  no automatic analysis
* installed/module/Legacy 12-subcommand Session CLI parity, explicit Position
  and Historical execution, phase-aware Assistant, six examples, and eight
  append-only generated scenarios
* internal immutable Match Capture identity and metadata contracts with one
  canonical EuroSkat 36er Standard format, descriptive video/manual sources,
  exact three-Player perspective semantics, and optional historical Player-
  statistics snapshots
* internal immutable evidence-aware observed Game contracts with exact Match
  linkage, historical seats, optional perspective hand/original Skat/Discards,
  bounded partial and complete trace validation, free-text commentary, linked
  later responses, and deterministic reconstruction-capability summaries
* internal immutable EuroSkat 36er Standard Match Workspaces with exact 36-Slot
  rotation, partial observed Games, passed deals, immutable revisioned changes,
  evidence-derived Progress, deterministic fingerprints, strict Resume, and
  optimistic same-directory atomic persistence
* internal transport-free Match Capture Application services with immutable
  Card entries, Position Views and Results, exact/bounded Card selection,
  deterministic Game/annotation IDs, setup updates, automatic Play derivation,
  truncation cleanup, annotation editing, and Passed Deal/clear wrappers
* internal local Match Capture Web, Protocol, and CLI version `1` with one
  loopback-only explicit Workspace, browser creation and rapid entry, packaged
  assets, token/same-origin protection, compare-and-swap autosave, and explicit
  conflict Reload
* editable Match-bound Player Statistics Snapshots with deterministic IDs,
  strict-before-Match Context and canonical Preparation, existing normalized
  Profile derivation, and private browser Add, Replace, and Clear forms
* internal evidence-aware Match Decision preparation with acting-own-hand
  reconstruction, actual-Card cutoff, no future-opponent leakage, Skat/Ouvert
  visibility, and time-safe relative Profile bindings without application
* internal strict normal-completion Historical Game materialization,
  unpartitioned Training source Records, and complete existing fixed-three-
  player list plus aggregation materialization with Passed Deals and Commentary
  retained as Workspace sidecars, without workflow execution
* internal Match analysis and export contracts with explicit one-Decision
  Immediate/Search/Auto/Information-set Position execution, strict selected-mode Historical
  execution, eligible actor-relative Profile application through existing
  behavior, deterministic max-eight ephemeral reports, concurrency invalidation,
  and authenticated canonical browser downloads
* internal Learning Corpus persistence and Store version `1` with one explicit
  fixed root, deterministic Catalog/content fingerprints, strict Catalog and
  Match Snapshot reconstruction, full Store Resume, and valid sorted orphan
  reporting without automatic repair or deletion
* pure revision-conflict-first Catalog import and Current-selection operations,
  immutable no-clobber object publication, optimistic atomic Catalog Save,
  strict source-preserving Workspace-file import, object-before-Catalog conflict
  orphans, and persisted explicit selection updates
* deterministic non-persisted Learning Corpus Player Catalog version `1` from
  explicit Current Match Snapshots only, with exact stable-ID aggregation, label
  history, platform aliases/conflicts, retained exact Statistics history, and
  strict latest-unambiguous or explicit-observation selection
* deterministic private Learning Corpus Human Evidence version `1` from explicit
  Current Match Snapshots only, with exact original text and commentator identity,
  observed subject/response Cards and timecodes, noncausal links, minimized Game
  context, source/evidence/collection/export identities, and canonical bytes
* deterministic private Learning Corpus Strategy Teacher Source, Evidence,
  Collection, and Export version `1` from exact executed Decision Analysis Reports
  explicitly bound to Current Match Snapshots, with one no-execution Request
  rebuild, retained Result validation, exact and semantic fingerprints,
  method-bound Immediate/Search/Auto evidence, and canonical bytes
* focused private Information-set Strategy Teacher extension version `1` with
  safe aggregate Result/comparison Evidence, exact fixed-policy reconciliation,
  and wall-clock-normalized semantic identity
* deterministic private unpartitioned Learning Dataset version `2` over exact
  Current Corpus sources, with safe/skipped Decision coverage, separate evidence
  families, time-safe Statistics selection, normalized exact pools, strict joins,
  stable Record IDs, enriched content fingerprints, and canonical export bytes
* deterministic private Dataset-v2 partition preparation with Match-Snapshot
  groups, fixed Known-player and unseen-player algorithms, leakage audits,
  lossless indexes, and canonical export bytes
* deterministic private Dataset-v2 cross-game summaries over exact Dataset,
  Player Catalog, and supplied partition Results, with descriptive Match, Player,
  Communication, Strategy, Coverage, and readiness Counts plus canonical export
* internal local Learning Corpus Web, Protocol, and CLI version `1` with one
  explicit root, caller-ID initialization, strict 16-MiB uploads, optimistic
  import/selection, max-2,048 process-local Report sources, explicit source-safe
  preparation, atomic existing-plus-Tactical-plus-Coaching publication, minimized
  no-JavaScript presentation, loopback security, and ten canonical downloads without derived
  persistence
* updated README, docs, roadmap, and project handoff

Current limitations include the absence of flat Position, Session, Match
Capture, and Corpus entry for the approved party-wide Claim. Its Historical-only
runtime path, private contracts, exact-state preparation, bounded proof execution,
valid-proof adjudication, public diagnostic summary, Provenance, and existing
Final Settlement reuse are implemented. Specific-
Trick Claims and the other durable v1 Claim exclusions are not supported before
v1. Other limitations include defender-open-play proof beyond five unresolved
tricks, multiple historical
continuations, historical end reasons beyond the supported bounded set,
incomplete settlement nuance, no additional preparation algorithms, algorithm
overrides, fallback or partial plans, global optimization, ratio guarantees,
Sample- or Player-count balancing, or component splitting, incomplete broader
public Provenance exposure,
heuristic rule-based recommendations and
opponent behavior, and structural rather than calibrated or tactical hidden-card
inference. Routed Search remains bounded late-game determinization subject to
Strategy Fusion, not an optimal imperfect-information policy or complete-
contract Search. The private three-Trick Information-set executor prevents
Strategy Fusion only for controlled Player `me` over its selected sequence;
exact world counts do not identify the real deal, sampled ownership is not
calibrated probability, measured timings are not latency guarantees, and timeout
activation is machine-dependent. Flat, Historical Review, and Training Dataset
evaluation routing plus strict Multi-Step and Policy Comparison integration are
implemented. Issue #191 adds the bounded one-Decision Match/Report/Teacher/
Dataset/Corpus path. Issue #192 adds separate Information-set Replay Coaching and
Match Historical Information-set Review/Coaching. Issue #193 adds separate local
benchmark evidence for the unchanged executor. Performance acceptance for v1 is
the deterministic functional and structural-work contract; supported-platform
evidence is complete under Issue #206 on Windows and merged Ubuntu CI, while
latency guarantees are not a v1 gate.
There is no
cross-decision global Policy, equilibrium, global optimality, or calibrated
probability claim. Issue #194 adds deterministic structural Historical Tactical
Motif Review without quality, intent, signaling, communication, or causal
classification. Issue #195 adds separate descriptive cross-game Tactical Motif
counts and bounded recurrence scopes without making those classifications or
changing Dataset version `2`. Issue #196 adds bounded deterministic Tactical
Cross-game Coaching from exact retained Tactical/Teacher evidence without a truth
or Player-rating claim. Overbid Null replacement selection, broader tactical
quality assessment outside retained complete-Search evidence, causal
attribution, and player ratings are not required for v1; complete internal
field-level information provenance is complete under Issue #202 without widening
the public contract. Issue #203 completes canonical Multi-Step phase coverage;
Issue #204 closes the Package-license decision with exact `AGPL-3.0-only` legal
files and PEP 639 metadata. Issue #205 completes the SkatMind rename and closes
B-08. Issue #206 completes the technical platform matrix and closes B-05 after
merged Ubuntu CI passes. Issue #207 closes B-06; #208 maintainer UAT is next,
before B-07 Release preparation.
End-to-end local Live and Retrospective Session
capture is implemented through public file Save/Load, automatic Checkpoints,
accepted-Log actual-card observation, isolated review, explicit analysis, the
12-subcommand CLI, and Assistant. Session GUI/browser UI, online-platform adapters,
cloud synchronization, distributed locking, encryption/key management, and
automatic backup policy remain absent and are not v1 requirements. The
historical published `v0.14.0` baseline
has 63 authoritative and byte-identical packaged Schemas and 85 generated-output
scenarios; the historical published `v0.13.0` baseline remains 62 Schemas and 77
scenarios. The historical published `v0.16.0` and `v0.15.0` Packages preserve
the 63-Schema, six-Session-example, and 85-scenario sets.
Match Capture now contains identity/metadata, individual evidence-aware observed
Games and commentary, persistent internal 36-position Workspaces,
transport-free rapid-entry Application services, and the private local no-JSON
browser/CLI with autosave. Match-bound Player Statistics editing and time-safe
Profile preparation are implemented. Internal Decision review preparation and
strict existing-contract Historical, unpartitioned Training-source, and complete
fixed-list materialization are implemented. Explicit browser analysis,
existing-behavior Profile application, ephemeral reports, and authenticated
local downloads are also implemented, while materialization itself executes no
workflow. Issue #191 adds strict one-Decision Information-set Search, curated
safe diagnostics, and exact source transfer without changing persistence or
public boundaries. Issue #192 adds explicit Match Historical Information-set
Review/Coaching controls and safe rendering through one Historical Application
invocation; Reports remain ephemeral and Historical Reports remain ineligible
for Strategy Teacher transfer. Public Match API/export, Match Schema/data
workflow, public/persisted Player
Catalog, public or task-specific communication Dataset workflows,
database/remote deployment, YouTube
integration, and EuroSkat integration remain absent.
Learning Corpus persistence, Workspace import, explicit Current selection, exact
Report-source transfer, Dataset-v2 preparation, summaries, and downloads are now
available through the private local `corpus` browser workflow. The derived Player
Catalog and Statistics history, Human and Strategy Teacher Evidence, Dataset-v2,
partition Results, Dataset-v2 Summary, Tactical Motif Evidence, and Tactical
Motif Cross-game Summary, and Tactical Cross-game Coaching remain process-local
and non-persisted; there is no
Public API, Schema, example, or generated scenario for Issue #195. Focused
Information-set Teacher Evidence still propagates through the existing Dataset-v2
joins and Summary counts; the separate Tactical family leaves Dataset version `2`
unchanged. Issue #196 adds the separate exact Coaching join without changing
Dataset version `2` and brings the current authenticated download set from nine
to ten.
Deletion,
garbage collection, Player Catalog or Human Evidence persistence,
persisted aliases/assertions, merge/split operations, all-revision views,
public Human or Strategy Teacher Evidence API transport, automatic Report
capture, Historical Report import, Dataset-v2 persistence, task builders,
persisted partition artifacts, and model training remain absent and are not v1
requirements. Session State itself contains no path
or fingerprint; those values belong only to the private persistence boundary.
No learned model, model-training workflow, hosted website, browser extension,
remote browser deployment, four-player support, or claim of complete official
rule coverage exists.

## Important design principles

* Keep behavior test-driven.
* Keep output regression-friendly.
* Keep JSON schemas synchronized with stable output fields.
* Keep live decision mode separate from post-game review mode.
* Preserve backward compatibility when reasonable.
* Prefer focused modules over large orchestration changes.
* Avoid broad rewrites of `main.py` unless specifically requested.
* Keep CLI output human-readable but secondary to structured JSON.
* Do not remove existing examples unless they are explicitly obsolete and covered by replacement examples.

## Current product baseline

The authoritative rules and product audit is in
[`docs/requirements_traceability.md`](docs/requirements_traceability.md). The
requirements and completion gates for `v1.0.0` are in
[`docs/v1_scope.md`](docs/v1_scope.md). The authoritative current technical
conclusion and next action are in
[`docs/v1_0_final_technical_release_readiness_audit.md`](docs/v1_0_final_technical_release_readiness_audit.md).

Do not describe undecided future areas as permanently out of scope. Four-player
tables are the only unconditional exclusion; other candidate areas use the
classifications in `docs/v1_scope.md`.

## Safety rules for agent behavior

Do not run destructive Git commands.

Avoid commands such as:

```powershell
git reset --hard
git clean -fd
git push --force
```

Do not delete files unless the task explicitly requires it.

Do not change dependency versions unless the task explicitly requires it.

Do not introduce new dependencies unless clearly justified and approved.

## GitHub issue update comments

At the end of issue-related work, always provide a ready-to-paste GitHub issue
update comment. Do not post it.

The issue update comment should include:

* what was implemented
* changed files or areas
* checks that were run
* whether the full check passed
* whether product code changed
* whether the issue is ready to close or should remain open

## Completion criteria

A task is complete only when:

* implementation is done
* focused tests pass
* full check passes
* documentation is updated if behavior or stable output changed
* `git status` shows only intended changes
