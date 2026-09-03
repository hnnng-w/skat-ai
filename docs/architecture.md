# Architecture

This document describes the project structure and main modules.

## Overview

SkatMind is organized as a small rule-based analysis engine around a JSON input/output workflow.

Issues #160, #161, #163, #164, #165, #166, #167, and #168 add internal Match,
observed-Game, persistent Workspace, transport-free Capture Application, private
local browser transport, downstream preparation/materialization, and explicit
analysis/report/export layers:

```text
descriptive video or manual source metadata
    -> immutable media bounds
    -> exact named tournament-format registry entry
    -> exactly three fixed-place Match participants
    -> optional immutable existing Opponent Statistics snapshots
    -> one declared perspective Match Player
    -> immutable Match Capture identity
    -> one evidence-aware observed Game with historical seats
    -> bounded partial or exact complete public Play validation
    -> free-text Decision commentary and linked later responses
    -> deterministic evidence and reconstruction capabilities
    -> authoritative immutable 36-position Workspace
    -> exact fixed-list rotation, partial Games, and passed deals
    -> evidence-derived Progress and deterministic fingerprints
    -> strict private Resume and optimistic atomic local Save
    -> UI-ready Position Views and exact/bounded Card palettes
    -> automatic Player/Decision append and focused evidence updates
    -> truncation, annotation reconciliation, and passed/clear wrappers
    -> locked one-file compare-and-swap autosave orchestration
    -> loopback-only token/same-origin browser and Capture CLI
    -> editable Match-bound Statistics snapshots
    -> strict-before-Match Context and canonical eligible preparation
    -> existing normalized Profile conversion and derivation
    -> information-safe acting-own-hand Decision preparation
    -> strict normal-completion Historical and unpartitioned Training sources
    -> complete existing fixed-list construction and aggregation
    -> explicit one-Decision Position or strict Historical Application execution
    -> existing eligible relative Profile application where supported
    -> ephemeral revision-scoped reports and authenticated local downloads
    -> strict one-Decision Match Information-set Search and exact Report transfer
    -> strict Match Historical Information-set Review and Coaching
    -> strict Match Historical Tactical Motif Review and safe browser projection
    -> immutable content-addressed Learning Corpus Match Snapshots
    -> lightweight Catalog entries and explicit Current selections
    -> one explicit fixed-root private Store and strict full Resume
    -> immutable no-clobber objects and valid orphan reporting
    -> strict source-preserving Workspace import and optimistic Catalog Save
    -> derived Current-Snapshot-only Player Catalog and exact alias conflicts
    -> retained exact Statistics history and strict time-safe selection
    -> minimized Current-Snapshot-only Human Commentary/Response Evidence
    -> method-bound Current-Snapshot Strategy Teacher Evidence
    -> focused safe Information-set Strategy Teacher Evidence
    -> private unpartitioned task-neutral Learning Dataset version 2
    -> separate Decision State, observed behavior, Player Context, and evidence pools
    -> private Match-Snapshot-safe partition Plans and leakage audits
    -> temporal Known-player or Player-component unseen-player partition indexes
    -> private exact-Count cross-game Match, Player, Communication, and Strategy summaries
    -> Dataset Coverage and supplied-partition-readiness summaries with path-free export
    -> separate Current-Snapshot-only Tactical Motif Evidence or explicit skips
    -> exact global, Player, scope, distinct-Game/Match, and recurrence Counts
    -> exact Tactical/Teacher joins and bounded Tactical Cross-game Coaching
    -> separate loopback-only Learning Corpus CLI and browser over one explicit root
    -> strict Workspace/Decision-Report uploads and explicit Current selection
    -> process-local atomic exact preparation and ten authenticated canonical downloads
    -> frozen private local Match/Corpus/Dataset-v2 v1 boundary
```

The game platform is separate from the media source, and the perspective Player
is separate from the application user. Observed facts remain distinct from
derived trace and evidence values: missing original Skat or Discards are not
completed from the deck complement. Issue #167 internally prepares Decision
snapshots, strict existing Historical Games, unpartitioned Training source
Records, and a complete existing fixed list plus aggregation. Issue #168
explicitly executes one existing Position or Historical Application invocation
when the selected value is available; materialization still executes no workflow.
It retains at most eight deterministic SHA-256 reports in process memory and
serves authenticated canonical local downloads without server paths. Capture
mutations perform no automatic analysis, and reports are never persisted in the
Workspace. Capture Application operations still receive an already loaded
Workspace and perform no file or network I/O; the leaf transport alone
orchestrates private persistence, local HTTP requests, analysis actions, and
downloads. No YouTube or EuroSkat integration or public Match export occurs.

Issue #179 composes the Issue #171 through #178 private values in a separate leaf
transport. It strictly initializes or resumes one explicit Corpus root, imports
caller-uploaded Workspaces and exact executed Decision Report sources, keeps at
most 2,048 Report sources and all prepared derived artifacts in process memory,
and explicitly builds Player, Human, Strategy Teacher, Dataset-v2, known-player,
unseen-player, and Summary values outside the context lock. A generation/source
check prevents stale publication. The minimized server-rendered dashboard and
seven authenticated canonical downloads add no derived persistence, Public API,
Schema, or Root workflow. Issue #179 completed the functional private local
`v0.16.0` work without changing Package `0.15.0`; Issue #180 then prepared
Package `0.16.0` and Release documentation without product behavior changes. The
maintainer published `v0.16.0` manually on 2026-08-18 at commit `91b1360`, and
Issue #181 synchronizes publication status without product functionality. GitHub
Releases is the authoritative publication record; no Package-index or PyPI
publication is claimed.

Issue #195 composes a separate Current-Snapshot-only Tactical family beside that
published seven-artifact chain. It safely reconstructs each observed Decision or
retains an explicit skip, calls the exact shared Historical Tactical detector,
and builds deterministic descriptive global, Player, role, seat, phase,
contract, distinct-Game, distinct-Match, and recurrence Counts. Human, Strategy
Teacher, and Tactical Evidence remain separate, and Learning Dataset version `2`
is unchanged. The browser publishes the existing and Tactical process-local
families atomically after one generation/source check, renders only minimized
Tactical counts, and adds two authenticated path-free downloads for nine current
artifacts. It adds no persistence, Public API, Schema, Root workflow, example, or
generated-output scenario.

Issue #196 composes a third process-local Tactical Cross-game Coaching family
from the exact retained Tactical and Strategy Teacher values. It preserves every
exact Teacher Assessment, deduplicates only Decision consensus by existing
semantic fingerprint, limits actionable consensus to unanimous distinct-
semantic complete-Search evidence, and requires repeated below-best Decisions
across at least two Games. Player Reports retain exact Catalog order, including
zero-count Players, and at most five fixed-Guidance focus areas per Player. The
builder executes no analysis or detector. All three prepared families publish
and invalidate atomically, the dashboard exposes aggregate Coaching Counts only,
and one authenticated path-free download brings the current set to ten. Learning
Dataset version `2`, Dataset-v2 Summary, persistence, Public API, Schema, Root
workflow, example, and generated-output contracts remain unchanged.

Issue #197 records the documentation-only `v0.17.0` scope and Release-readiness
audit. Issue #198 prepared Package `0.17.0`, matching expectations, Changelog,
and Release-candidate documentation without changing this architecture or any
product behavior. The maintainer published `v0.17.0` manually on 2026-08-25 at
`8187fbe`, and Issue #199 synchronizes the post-publication documentation without
changing product functionality. It is the current and latest stable GitHub
Release; GitHub Releases remains authoritative, and no Package-index or PyPI
publication is claimed.

Issue #200 freezes the existing private local Match, Capture, Corpus, and
Dataset-v2 architecture as the v1 boundary. No Public Match/Corpus/Dataset-v2
API, Schema, Root workflow, or derived persistence is required for v1. Issue #202
subsequently completes mandatory internal load-to-final-serialization Provenance
without widening public Provenance. Issue #203 completes all nine concrete
canonical Multi-Step phases without widening Search or public contracts. Broader
solvers and hosted/remote integration are post-v1.

Issue #204 applies `AGPL-3.0-only` and closes B-04 without changing product
behavior or active Package identity. Issue #205 completes the hard-cut SkatMind
Package/import/CLI/resource/Schema/identifier migration, strict legacy input-only
compatibility, and reviewed historical-evidence boundary. P-09 is `satisfied`
and B-08 is closed. Issue #206 adds exact direct dependency floors and a reusable
validation-only source/Editable/Wheel/sdist supported-platform matrix. P-34 is
`satisfied`, and B-05 is closed after both merged Ubuntu jobs pass. Issue #207
finds no material technical blocker and closes B-06. B-09 and B-07 remain; B-09
is outside the 53-row ledger. Issue #208 then begins maintainer UAT; UAT-01 fails
with three accepted findings, and UAT-02 through UAT-12 are paused.

Issue #210 implements the first [unified local frontend](unified_local_frontend_application_shell.md)
slice: one foreground process, one `127.0.0.1` server on an operating-system-
selected port, one authenticated browser session, one navigation, and one
managed data root. Issue #211 adds private process-local guided Position and
Historical form translation, strict in-memory JSON transfer, one-call Public
Application execution, retained immutable Results, and public-Result-only
presentation. It is documented in [Guided analysis and Results](unified_local_frontend_guided_analysis_and_results.md).
Issue #212 adds direct managed Session, Match, and Corpus adapters, bounded
direct-child discovery, guided Session entry, namespaced reuse of the existing
Capture and Corpus bodies, and explicit Match-to-Corpus transfer. The shell still
does not proxy or iframe standalone servers. Explicit Session, Capture, Corpus,
and Root paths remain supported. Issue #213 adds lightweight Product help,
canonical explicit-input `run`, grouped Root automation help, and unchanged
Package-1.x direct Root compatibility through one Root implementation. Repeated
UAT-01 then exposed UAT-FINDING-004, and Issue #214 implemented
`Referrer-Policy: origin` across the three local browser surfaces. Maintainer
Microsoft Edge verification resolved Issue #214 and UAT-FINDING-004. Repeated
UAT-01 nevertheless failed. Issue #215 freezes the authoritative future
[bilingual profile-driven frontend UX contract](bilingual_profile_driven_frontend_ux_contract.md),
and Issue #216 implements its private profile persistence, strict German/English
catalogs, locale resolution, authenticated language selection, bilingual common
shell, and explicit English workflow-body boundary. The implementation is
documented in [Local frontend profile and localization](local_frontend_profile_and_localization.md).
Post-merge Ubuntu CI at `087f497` reopened Issue #216 for its CPython-3.13.15
parser-header compatibility correction and a separate stale matrix-smoke
filename correction. The correction and both required Ubuntu jobs passed,
completing Issue #216. Issue #217 adds the grouped bilingual Home, clarified
Product concepts, safe related links, and useful stateful empty states. Issue
#218 adds private registry-driven safe submitted-value preservation, accepted-
state isolation, localized accessible validation, contextual `400`/`409`
responses, and successful `303` PRG without changing standalone servers. Issue
#219 adds private known Players, generated Player/Product identities and opaque
selection handles, saved creation defaults and labels, bilingual name-first
Session/Match/Learning creation, and strict Product-first/profile-second
publication. The implementation is documented in [Profile-driven stateful
creation](profile_driven_stateful_creation.md). Issue #220 is the exact next
action. Issue #208 remains open; UAT-02 through
UAT-12 remain paused; B-09 and B-07 remain open; B-06 remains closed; and
Package `1.0.0` and Release preparation are not ready. See
[Advanced CLI automation](advanced_cli_automation_interface.md).

Issues #160 through #168 form the published `v0.15.0` Package baseline, and Issue
#169 updated only Package/release metadata and documentation to complete Release
preparation. Issue #170 synchronizes the subsequent manual publication at commit
`ec1c154`. Python remains
`>=3.13`; Public API, Application, CLI, Match, Session, Provenance, Schema,
Search, Dataset, list, Coaching, and Settlement contract versions remain
unchanged.

Issue #150 adds a separate internal authoring and control-plane contract before
the existing Engine workflows:

```text
Session Commands
    -> stable skatmind.api.v1.session wrapper and optional returned-value provenance
    -> immutable accepted Session State
    -> optional immutable Undo or one-command correction
    -> optional private persistence document and atomic local save
    -> strict resume, accepted-Log replay, fingerprint verification, and lineage
    -> validation and export readiness
    -> canonical Position Request export and optional Decision Checkpoint
    -> canonical Historical Game Request export
    -> optional accepted-Log Decision Observation and isolated review Request
    -> explicit existing Position or Historical Application execution
    -> strict standalone Session Result Schema validation
```

The immutable Session language, deterministic accepted-Log replay, frozen
projection, atomic Command application, monotonic phase advancement, and
incremental validation are implemented. Historical-ready Retrospective Sessions
also map through the existing Historical builder and canonical serializer into
an immutable Request without executing it. Position-ready Sessions map through
the existing flat Position builder into an information-safe immutable Request,
and an available export can be frozen as a replay-verified pre-Play Checkpoint.
The history layer can now reconstruct a strict accepted prefix, replace one
Command, replay the original suffix through the same validator, stop with a valid
partial State before the first rejected later Command, and derive Checkpoint
lineage. Issue #155 can retain the authoritative State and optional caller-
supplied frozen Checkpoints in one private version-1 document, strictly resume it,
recompute lineage, and optimistically save canonical local bytes through same-
directory atomic replacement. Issue #156 adds `api/v1/session` as a stable
in-memory wrapper, `session_provenance.py` for complete redacted returned-
value ledgers, and standalone Package Resource Schema validation. Each public
operation delegates once to its existing internal function and remains outside
Application orchestration. Issue #157 adds stable `api/v1/session/files` Save and
Load, exact Checkpoint collection, accepted-Log actual-card observation, frozen-
Request review export, the 12-subcommand Session CLI, explicit existing-
Application execution, and the phase-aware Assistant. Issue #158 completed
Release preparation for the functional `v0.14.0` milestone, which the maintainer
subsequently published manually at commit `d5589f8`; Issue #159 synchronized its
publication status. There is still no eighth Root workflow or persisted analysis
Result.

The position-analysis flow is:

1. Load and validate JSON input.
2. Build exact immutable Request, effective-option, and optional external-source
   provenance and enforce Information Use Context.
3. Build an internal game state.
4. Apply workflow information-policy checks.
5. If the normalized current actor is the local player, analyze legal card choices.
6. Estimate expected point swings for available local decisions.
7. Build card recommendations or an unavailable Immediate Analysis shape.
8. Optionally run phase-aware multi-step simulation or policy comparison.
9. Build game-result, settlement, performance-rating, and post-game review summaries.
10. Link retained stages and reconcile the complete exact Result envelope and
    actual artifacts.
11. Serialize output for CLI and JSON use.

The alternative historical-game flow loads `historical_game_input`, builds a
stable-ID record, and strictly replays either ten normal-completion tricks or an
exact legal prefix ending in a versioned declarer-concession, defender-concession,
unanimously accepted declarer-card-exposure, terminal defender-open-play, open-
card-throw, or party-wide all-remaining-Tricks Claim event. Normal completion
or one supported terminal shortening may follow at most one separate timed non-
terminal defender-open-play or declarer-card-exposure continuation event. It
derives points and ownership, reuses the declaration/value/overbid/settlement
helpers, and emits `historical_game_summary`.
A ready Retrospective Session can now construct that existing Root input through
the internal Issue #152 exporter. Historical workflow execution remains a
separate explicit API, Application, or CLI action. Issue #157 `session finalize`
performs that explicit Application execution once when export is available.
One Position-ready Live or Retrospective Session can construct the existing flat
Position Root input through the internal Issue #153 exporter. It maps stable
Players to the local `me`/`left`/`right` perspective, emits only decision-visible
Skat, Matador, Ouvert, and continuation facts, validates through the existing
Position builder, and does not execute analysis. A separate Issue #153 builder
verifies and freezes that exact export with source revision and decision
metadata before the local Play.
Issue #157 `session analyze` executes that frozen Position Request explicitly.
`session review` derives the first accepted local Play after a Checkpoint, copies
the frozen Request, changes only review mode and actual Card, and executes the
existing Position Application once when available.
When requested, the flow derives one pre-play decision snapshot per actual
supplied play from that
validated replay result. Historical review adapts each snapshot independently
to the existing local state, runs the existing immediate recommendation once,
builds the candidate report from those values, and reuses post-game review.
Historical Search Review instead builds the same decision-time position, runs
bounded Search and a separate Immediate baseline before introducing the observed
card, and emits reconciled decision, status, coverage, agreement, quality, and
performance summaries.
Historical Information-set Search Review is a separate conflicting opt-in. It
runs bounded Information-set Search, PIMC on the exact retained selected-world
sequence, and an independently seeded Immediate baseline before attaching the
observed Card. It emits descriptive agreement and aggregate differences without
an accuracy or truth claim.
Information-set Replay Coaching is a separate Issue-#192 mode over exactly one
retained Historical Information-set Search Review. Complete Information-set
Candidates are primary evidence; PIMC and Immediate remain diagnostics and never
provide fallback. The observed Card is attached after decision-time analysis,
and final Outcome Context is attached only after assessment, prioritization,
patterns, and Guidance.

Historical Tactical Motif Review is a separate Issue-#194 mode over the same
retained Decision Snapshot sequence. It derives safe decision-time structural
facts before reading the actual Card, attaches immediate partial-Trick facts
after the Card, and attaches completed-Trick outcomes only after completion. The
detector executes no Search or Coaching and emits no quality, intent, signaling,
communication, or causal classification. When multiple Historical attachments
need Snapshots, the Application builds that sequence once and shares it.

The Issue-#195 Corpus builder reuses the pure
`build_tactical_decision_observation_from_snapshot_v1()` seam directly after the
existing Match Decision-state reconstruction. It does not invoke the Historical
Application, Search, or Coaching. Partial Matches and incomplete final Tricks
therefore retain the same exact complete/partial evidence-time semantics without
requiring strict Historical materialization.

The training-dataset flow validates dataset identity, provenance, optional
known-opponent or unseen-player partition policy, and duplicate protection, then reuses the historical validator/replay and
decision snapshot generator. It converts stable player references to the local
`me`/`left`/`right` model in features, keeps traceability identities in metadata,
and emits one legal actual-card sample per snapshot. It does not call the
recommender or simulation.

The separate bounded-Search dataset-evaluation mode selects canonical dataset
partitions, preserves every selected record including zero-decision records,
and evaluates one stable global decision prefix with the same historical Search
and independent Immediate comparison. It does not alter training samples or
partition policy.
The separate Information-set Search evaluation uses the same stable selection
boundary, defaults to validation/test, and evaluates Information-set Search,
same-selection PIMC, and independently seeded Immediate. It changes no Dataset
Record, Feature, target, label, sample ID, or partition.

The dataset-partition audit flow scans exact stable participant IDs without
replaying games. It emits deterministic membership, overlap, directed coverage,
and unseen-player compliance. Declared unseen-player overlap is rejected during
normal loading; an undeclared dataset requested as unseen-player remains
inspectable as a complete non-compliant audit.

The opponent-statistics flow validates a versioned collection of external
percentage-point records, stable player identity, and required capture
provenance. It checks rounded source consistency and deterministically converts
percentages to `PlayerProfile` rate semantics while preserving source values and
leaving exact role-specific counts unknown unless optional exact counts are
supplied. It calls the isolated profile
derivation module to expose unrounded role-evidence estimates, scoped heuristic
confidence, signals, classification, and preset metadata. It does not apply a
policy or call recommendation, historical, or simulation code.

The historical opponent-statistics flow reuses `TrainingDatasetInput` only as a
validated multi-game, provenance, and partition container. It selects canonical
partitions, requires `played_at` on every partition-selected game, applies an
optional strict instant cutoff, and reuses historical replay and final settlement
to aggregate exact per-player role, result, Hand, and contract counts. It then
reuses opponent-statistics normalization and profile derivation and can serialize
a standalone `opponent_statistics_input`. It does not generate samples or run
recommendation, review, policy application, quality evaluation, or training.
Normal-completion, declarer-concession, defender-concession, declarer-card-
exposure, defender-open-play, open-card-throw, and party-wide-Claim records are
explicitly supported and each contributes one game regardless of play count.

The rolling opponent-policy evaluation is explicitly a known-opponent flow. It
selects disjoint source and target partitions, reports membership overlap,
invokes the same strict historical aggregation at each target start,
matches the acting player's own stable identity, and predicts each snapshot's
actual card with the fixed `simple_lowest` baseline and any existing actionable
profile preset. It evaluates deterministic preferred-card and exact-card
matches without calling recommendation, expected-value simulation, historical
decision-quality review, policy application, or model training.
Sources use equal game-level weight. Targets use their shared validated actual-
play cardinality, including zero-decision concessions, while player coverage is
participant-based and decision breakdowns remain actor-based.

The project is not a machine-learning model. Its behavior is based on Skat rules, deterministic helpers, and simulation.

## Tactical motif evidence

| File | Purpose |
| --- | --- |
| `src/skatmind/tactical_motif_contracts.py` | Immutable version-1 facts, occurrences, observations, report/scopes, exact taxonomy, policies, limitations, and serialization. |
| `src/skatmind/tactical_motif_detection.py` | Pure decision-time fact construction and deterministic after-play/after-Trick motif predicates over retained Snapshots. |
| `src/skatmind/historical_tactical_motif_review.py` | One-game chronology, complete/partial observation composition, canonical aggregates, and exact source reconciliation. |
| `src/skatmind/match_historical_tactical_motif_analysis.py` | Private Match option adaptation, validated Root reconciliation, and safe browser report projection. |

These modules execute no Search, Coaching, Commentary, Response-Link, Profile,
or opponent Policy stage. See [Tactical motif evidence](tactical_motif_evidence.md).

## Information provenance

| File | Purpose |
| --- | --- |
| `src/skatmind/field_provenance.py` | Shared immutable field-level provenance language, dependencies, and serialization. |
| `src/skatmind/field_provenance_coverage.py` | Deterministic JSON-leaf coverage auditing. |
| `src/skatmind/field_provenance_policy.py` | Information Use Context validation and public redaction. |
| `src/skatmind/live_analysis_provenance.py` | Live Position decision collection and complete Result attachment orchestration. |
| `src/skatmind/retrospective_review_provenance.py` | Flat retrospective stage separation and shared complete-attachment construction. |
| `src/skatmind/historical_review_provenance.py` | Historical decision, review-summary, Coaching, and complete Result attachment orchestration. |
| `src/skatmind/replay_coaching_provenance.py` | Replay Coaching evidence, assessment, prioritization, guidance, and report mapping. |
| `src/skatmind/information_set_search_provenance.py` | Privacy-safe retained-stage Information-set Search, same-selection PIMC, Immediate, actual-Card, and comparison provenance entries. |
| `src/skatmind/position_result_provenance.py` | Complete Position Root Result mapping and dependency enforcement. |
| `src/skatmind/historical_result_provenance.py` | Complete Historical Root Result mapping and dependency enforcement. |
| `src/skatmind/settlement_result_provenance.py` | Shared retained Settlement Result entry construction. |
| `src/skatmind/application/provenance.py` | Immutable attachments and canonical per-workflow bundle ordering. |
| `src/skatmind/v1_information_provenance_sources.py` | Exact consumed Request/effective-option/external sources, canonical ledgers, and invocation-local bindings. |
| `src/skatmind/v1_information_provenance_enforcement.py` | Four-stage contract identity, pre-analysis context enforcement, workflow-scoped reference authorization, and retained linkage. |
| `src/skatmind/v1_information_provenance_serialization.py` | Shared Result/artifact mappings, exact final reconciliation, and immutable lifecycle checkpoints. |

Live and retrospective provenance is retained as an internal Application
sidecar. Existing workflow values are observed through optional hooks; analysis,
Search, Snapshot, and Coaching stages are not rerun. Public API and CLI adapters
omit it by default. Explicit provenance opt-in selects only one redacted complete
Root Result attachment plus artifacts actually returned, recomputes complete
coverage, and exposes the strict public sidecar through Root JSON. Consumed-input,
decision, intermediate-stage, and unredacted attachments remain internal.
Issue #202 additionally requires the internal four-stage checkpoint for every
canonical Root execution before that optional public conversion.

## Main entry point

| File | Purpose |
| --- | --- |
| `src/skatmind/cli/entrypoint.py` | Lightweight Package entry with shell-first bare/leading-`app` dispatch before broad Root imports. |
| `src/skatmind/cli/execution.py` | Package-owned compatibility facade with `app`, `corpus`, `capture`, `session`, and Root dispatch. |
| `src/skatmind/cli/app.py` | Unified shell managed-home preparation, browser opening, foreground lifecycle, and Exit Code transport. |
| `src/skatmind/app_web/` | Private managed-data and information-architecture contracts, bounded discovery, Session/Match/Learning adapters, cross-area transfer, strict local profile persistence, known Players, generated identifiers and opaque handles, profile-driven creation preparation, bilingual friendly rendering and local settings, locale resolution, German/English catalogs, browser-safe validation, security, one Standard Library server, template, and packaged assets. |
| `src/skatmind/cli/corpus.py` | Private local Learning Corpus CLI startup, browser opening, shutdown, and Exit Code transport. |
| `src/skatmind/cli/capture.py` | Private local Capture CLI startup and Exit Code transport. |
| `src/skatmind/cli/session.py` | Session compatibility facade over focused parser and orchestration services. |
| `src/skatmind/__main__.py` | Module invocation delegation. |
| `main.py` | Thin Legacy compatibility facade and Root monkeypatch adapter. |

Root parsing, validation, Legacy dependency resolution, Application adaptation,
dispatch, transport, and presentation are separate focused modules. Corpus,
Capture, and Session parsing, strict JSON input, context/persistence,
Checkpoints, operations, Application adaptation, and presentation are also
separate. CLI is a leaf
transport: Application, Public API, Match, and observed-Game modules do not
import it. See [CLI internal architecture](cli_internal_architecture.md).

## Core rules

| File                   | Purpose                                                                            |
| ---------------------- | ---------------------------------------------------------------------------------- |
| `src/skatmind/deck.py`  | Deck and card helpers.                                                             |
| `src/skatmind/rules.py` | Card notation, card points, trump logic, legal-card logic, and trick-winner logic. |

The internal card-strength values in `rules.py` are comparison values only. They are not Skat card points and must not be used for scoring.

## Input loading and validation

| File                                | Purpose                                                                                                             |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| `src/skatmind/input_loader.py`       | Loads JSON input, extracts settings, and converts input into internal structures.                                   |
| `src/skatmind/input_validation.py`   | Validates input fields, cards, metadata, points, game-end consistency, policy settings, and rating-system metadata. |
| `src/skatmind/known_cards.py`        | Tracks and validates known cards.                                                                                   |
| `src/skatmind/information_policy.py` | Centralizes live-vs-post-game information rules and builds `information_policy_summary`.                            |
| `src/skatmind/turn_phase.py`         | Normalizes and validates canonical `trick_leader` and `next_player` from the current trick length.                  |
| `src/skatmind/historical_game.py`    | Typed stable-ID historical records, complete-deal validation, strict play replay, and historical result serialization. |
| `src/skatmind/historical_game_end.py` | Versioned stable-ID historical game-end union parsing and canonical serialization. |
| `src/skatmind/historical_game_event.py` | Versioned non-terminal historical event union, boundary replay, and event summary orchestration. |
| `src/skatmind/historical_play_prefix.py` | Exact immutable prefix replay, remaining-hand reconstruction, and incomplete-trick state. |
| `src/skatmind/historical_declarer_concession.py` | Historical point accounting and shared declarer-concession adjudication/settlement adaptation. |
| `src/skatmind/historical_defender_concession.py` | Stable-ID historical adaptation of shared defender-concession adjudication and settlement. |
| `src/skatmind/historical_declarer_card_exposure.py` | Exact stable-ID reconciliation and shared accepted-exposure adjudication/settlement adaptation. |
| `src/skatmind/historical_declarer_card_exposure_continuation.py` | Timed exact declarer-hand reconciliation and non-adjudicating historical continuation semantics. |
| `src/skatmind/historical_defender_open_play.py` | Exact historical state reconstruction, bounded flat adjudication reuse, stable-ID proof mapping, and privacy-safe assignment output. |
| `src/skatmind/historical_defender_open_play_continuation.py` | Timed exact-hand reconciliation and non-adjudicating historical continuation semantics. |
| `src/skatmind/historical_player_mapping.py` | Shared deterministic circular mapping between stable historical IDs and flat player order. |
| `src/skatmind/historical_decision_cardinality.py` | Shared actual-play cardinality for snapshots, review decisions, training samples, and rolling targets. |
| `src/skatmind/historical_decision_snapshot.py` | Typed information-safe pre-play snapshot reconstruction and serialization over a validated historical result. |
| `src/skatmind/historical_snapshot_adapter.py` | Decision-time snapshot to local immediate-analysis position conversion. |
| `src/skatmind/historical_game_review.py` | Historical decision evaluation, deterministic seeds, unavailable handling, and complete-game aggregation. |
| `src/skatmind/historical_search_review.py` | Decision-time bounded Search plus independent Immediate analysis, stable private seed derivation, and reconciled historical aggregates. |
| `src/skatmind/training_dataset.py` | Typed dataset/provenance records, duplicate and partition validation, historical replay reuse, sample generation, and count reconciliation. |
| `src/skatmind/bounded_search_evaluation.py` | Canonical dataset selection, stable global decision-prefix evaluation, zero-decision preservation, and aggregate Search quality output. |
| `src/skatmind/information_set_search_contracts.py` | Private versioned method, Policy, Budget, Request, controlled-Decision, consumed-budget, and Result contracts without execution. |
| `src/skatmind/information_set_search_state.py` | Exact-world/public-history reconciliation, actor Information Sets, shrinking public hands, public voids, and pure exact-transition delegation. |
| `src/skatmind/information_set_search_policy.py` | Deterministic information-safe fixed-Player Policy validation and canonical action selection. |
| `src/skatmind/information_set_search_preparation.py` | Three-Trick eligibility, existing Compatible-world selection reuse, ordered World State construction, equal-root reconciliation, and strict retained-Preparation validation without reselection. |
| `src/skatmind/information_set_search_executor.py` | Private bounded selected-world best response, fixed-player rollout, controlled Information-set grouping, complete contingent Policy retention, exact counters, and invocation-local memoization. |
| `src/skatmind/information_set_search_workflow.py` | Strict flat routing, exact nine-field settings, effective left/right fixed-Policy mapping, and no-fallback execution. |
| `src/skatmind/information_set_search_public.py` | Safe aggregate public Result projection without Worlds, Observations, or the private controlled Policy table. |
| `src/skatmind/information_set_search_comparison.py` | Retained same-selection PIMC and independent Immediate comparison with post-analysis actual-Card attachment. |
| `src/skatmind/information_set_search_multi_step.py` | Version-1 Multi-Step Decision, domain-separated child settings, safe serialization, and compact Policy Comparison diagnostics. |
| `src/skatmind/historical_information_set_search_review.py` | Information-safe Historical Decision execution, deterministic seeds, descriptive metrics, and breakdowns. |
| `src/skatmind/information_set_search_evaluation.py` | Stable Dataset-v1 validation/test selection, global Decision cap, and no-training aggregate evaluation. |
| `src/skatmind/information_set_replay_coaching_evidence.py` | Exact pre-actual evidence reconstruction and retained actual-Card comparison reconciliation without rerunning analysis. |
| `src/skatmind/information_set_replay_coaching_assessment.py` | Information-set evidence bases, assessability, aggregate-equivalence, impact, factors, and canonical limitations. |
| `src/skatmind/information_set_replay_coaching_report.py` | Version-1 report composition over shared Key Decision, Turning Point, pattern, Guidance, scope, and Outcome Context behavior. |
| `src/skatmind/replay_coaching_method_neutral.py` | Narrow private adapters that let existing deterministic Coaching algorithms consume either assessment family. |
| `src/skatmind/dataset_partition_policy.py` | Versioned policy parsing, canonical serialization, exact stable-player membership extraction, and unseen-player conflict formatting. |
| `src/skatmind/dataset_partition_audit.py` | Deterministic partition, membership, overlap, known-opponent coverage, and unseen-player compliance auditing. |
| `src/skatmind/training_feature_view.py` | Information-safe conversion from stable-ID snapshots to relative model-facing features. |
| `src/skatmind/opponent_statistics.py` | Typed external statistics/provenance records, percentage validation, normalized profile conversion, and serialization. |
| `src/skatmind/historical_opponent_statistics.py` | Canonical partition/time selection, exact historical aggregation, provenance, summary, and reusable export construction. |
| `src/skatmind/historical_opponent_workflow.py` | Explicit supported-end-reason validation shared by historical opponent workflows. |
| `src/skatmind/opponent_profile_derivation.py` | Typed versioned evidence, scoped confidence, signal, classification, and explanation derivation. |
| `src/skatmind/rolling_opponent_policy_evaluation.py` | Strict rolling as-of profile construction, snapshot policy prediction, metrics, breakdowns, and reconciliation. |
| `src/skatmind/rfc3339.py` | Shared offset-aware RFC 3339 parsing for preserved timestamp text and instant comparison. |

## Interactive Sessions

| File | Purpose |
| --- | --- |
| `src/skatmind/session_commands.py` | Version-1 typed caller-fact Commands, immutable event/end payloads, and allowed-phase metadata. |
| `src/skatmind/session_contracts.py` | Stable three-Player identity, Capture Modes, phases, accepted Command records, authoritative Log, and immutable Session State. |
| `src/skatmind/session_validation.py` | Diagnostics, Position/Historical readiness, valid-incomplete status, and Transition Result invariants. |
| `src/skatmind/session_projection.py` | Frozen canonical accepted-fact projection and deterministic internal serialization. |
| `src/skatmind/session_incremental_validation.py` | One-Command phase, rule, ownership, information-policy, event/end, and readiness validation. |
| `src/skatmind/session_transitions.py` | Revision-zero creation, full accepted-Log replay, forged-State checks, conflicts, atomic append, and Transition Results. |
| `src/skatmind/session_export_contracts.py` | Immutable version-1 available/unavailable Request export result and policy invariants. |
| `src/skatmind/session_historical_export.py` | One-replay Historical readiness gate, exact projection mapping, canonical builder round trip, and immutable existing Root Request construction. |
| `src/skatmind/session_position_export.py` | Immutable analysis options, one-replay Position readiness gate, stable-to-relative information-safe mapping, existing builder validation, and immutable Root Request construction. |
| `src/skatmind/session_decision_checkpoint.py` | Immutable local pre-Play metadata and replay-verified frozen Position Request construction. |
| `src/skatmind/session_history_contracts.py` | History Edit policies, immutable Undo/Correction contracts, and Checkpoint Lineage relationships. |
| `src/skatmind/session_history.py` | Strict-prefix reconstruction, Undo, one-command correction, first-rejection suffix replay, and exact Checkpoint lineage classification. |
| `src/skatmind/session_persistence_contracts.py` | Private version-1 persistence, resume, and optimistic write contracts and exact policy constants. |
| `src/skatmind/session_persistence_codec.py` | Canonical domain-separated fingerprints, strict typed reconstruction, accepted-Log replay, fingerprint verification, and resumed lineage derivation. |
| `src/skatmind/session_persistence.py` | Strict private file loading and canonical optimistic same-directory atomic save transport. |
| `src/skatmind/session_decision_observation.py` | Immutable observation statuses and first accepted local-Play derivation from Checkpoint lineage and accepted history. |
| `src/skatmind/session_checkpoint_review.py` | Frozen-request-plus-observed-Card post-game-review Request export without execution. |
| `src/skatmind/session_checkpoint_collection.py` | Exact Position-ready Checkpoint collection, canonical retention, and equality deduplication without analysis. |
| `src/skatmind/api/v1/session/files/` | Stable version-1 public file Save/Load contracts, strict Result validation, and stable error translation. |
| `src/skatmind/cli/session.py` | Compatibility facade for the separate 12-subcommand Session CLI. |
| `src/skatmind/cli/session_parser.py` | Session parser and Position export-option mapping. |
| `src/skatmind/cli/session_transport.py` | Strict caller-file JSON loading. |
| `src/skatmind/cli/session_context.py` | Context, persistence-document, and optimistic Save orchestration. |
| `src/skatmind/cli/session_checkpoints.py` | Source/result/correction Checkpoint collection and retention. |
| `src/skatmind/cli/session_operations.py` | Twelve handlers, dispatch, and Save/no-Save decisions. |
| `src/skatmind/cli/session_application.py` | Existing Position/Historical Application execution without Session file I/O. |
| `src/skatmind/cli/session_presentation.py` | Privacy-safe Session and Engine Result transport presentation. |
| `src/skatmind/cli/session_assistant.py` | Deterministic phase-aware prompts over explicit focused services. |

Session State contains no `GameState`, Search World, cache, random stream,
analysis Result, generated timestamp, path, or fingerprint. Persistence paths and
the State/content fingerprints belong to the separate private persistence
boundary, not `SessionStateV1`. Session State reuses Historical seats,
`GameDeclaration`, Card notation, RFC 3339 parsing, continuation kinds,
Historical end reasons, legal-card/trick helpers, and RFC 6901 paths without
running analysis or adjudication. See
[Interactive session contracts](interactive_session_contracts.md) and
[Incremental Session transitions](incremental_session_transitions.md). See
[Retrospective Session export](retrospective_session_export.md) for the separate
internal no-execution Historical boundary and
[Session Position export and Decision checkpoints](live_session_position_export.md)
for the information-safe Position boundary, and
[Session Undo, correction, and Checkpoint lineage](session_undo_and_correction.md)
for immutable linear history editing. See
[Session persistence and resume](session_persistence_and_resume.md) for private
local document identity, verification, and atomic save behavior. See
[Session Decision observations](session_decision_observations.md) for actual-card
and review isolation and
[Session CLI and end-to-end capture](session_cli_and_end_to_end_capture.md) for
public files, automatic collection, execution, and Assistant behavior.

## Match and Observed-Game Capture

| File | Purpose |
| --- | --- |
| `src/skatmind/match_source_metadata.py` | Version-1 media timecodes and descriptive YouTube, other-video, or manual source metadata without network access. |
| `src/skatmind/match_tournament_format.py` | Immutable append-only named-format registry and canonical EuroSkat 36er Standard definition. |
| `src/skatmind/match_player_snapshot.py` | Fixed-place Match participants and optional immutable existing Opponent Statistics snapshots. |
| `src/skatmind/match_player_statistics_context.py` | Per-participant strict temporal eligibility plus existing normalized Profile conversion and derivation. |
| `src/skatmind/match_player_statistics_preparation.py` | Canonical fixed-place eligible Opponent Statistics input without side binding or policy application. |
| `src/skatmind/match_player_statistics_updates.py` | Deterministic Snapshot IDs and immutable conflict-first set/clear wrappers over definition replacement. |
| `src/skatmind/match_capture_contracts.py` | Exact three-Player Match identity, metadata, canonical format, uniqueness, perspective, and serialization reconciliation. |
| `src/skatmind/observed_game_contracts.py` | Match-linked observed Game identity, historical seats, optional Card evidence, complete reconciliation, and serialization. |
| `src/skatmind/observed_game_trace.py` | Chronological partial and complete Play validation, Turn Order, existing rule reuse, and derived trace summary. |
| `src/skatmind/observed_game_commentary.py` | Authoritative free-text Decision commentary, commentator identity, later response links, and canonical ordering. |
| `src/skatmind/observed_game_evidence.py` | Pure retained-fact capability derivation without Request construction or workflow execution. |
| `src/skatmind/match_workspace_contracts.py` | Exact 36-Slot Workspace, passed-deal and derived position-fact contracts, canonical validation, and revision-zero creation. |
| `src/skatmind/match_workspace_rotation.py` | Existing fixed-list rotation reuse and twelve-round derived position facts. |
| `src/skatmind/match_workspace_operations.py` | Immutable observed-Game, passed-deal, clearing, and Match-definition correction operations with revision conflicts. |
| `src/skatmind/match_workspace_progress.py` | Occupancy and observed-evidence Progress derivation without materialization. |
| `src/skatmind/match_workspace_persistence_contracts.py` | Private Workspace document, Resume, optimistic write, and exact policy contracts. |
| `src/skatmind/match_workspace_persistence_codec.py` | Domain-separated fingerprints and strict nested Workspace reconstruction. |
| `src/skatmind/match_workspace_persistence.py` | Strict private Load and canonical optimistic same-directory atomic Save transport. |
| `src/skatmind/learning_corpus_identity.py` | Finite canonical JSON, object kinds, policies, and domain-separated source/reference identities. |
| `src/skatmind/learning_corpus_references.py` | Snapshot-scoped Player, Game, Decision, Commentary, and Response References. |
| `src/skatmind/learning_corpus_match_snapshot.py` | Immutable exact Workspace Match Snapshot derivation and closed-reference validation. |
| `src/skatmind/learning_corpus_catalog.py` | Lightweight entries, explicit Current selections, canonical Catalogs, and pure classification. |
| `src/skatmind/learning_corpus_persistence_contracts.py` | Private persistence, Store, Catalog Change, write, import, and persisted-selection Results plus fixed policies. |
| `src/skatmind/learning_corpus_persistence_codec.py` | Catalog/content fingerprints, strict Catalog and Match Snapshot reconstruction, and canonical file bytes. |
| `src/skatmind/learning_corpus_catalog_operations.py` | Pure conflict-first Snapshot import and explicit Current-selection changes. |
| `src/skatmind/learning_corpus_persistence.py` | Fixed layout initialization, strict Store Resume, orphan scan, immutable object publication, and atomic Catalog Save. |
| `src/skatmind/learning_corpus_import.py` | Strict Workspace-file import and persisted Current-selection orchestration. |
| `src/skatmind/learning_corpus_current_snapshots.py` | Shared strict in-memory resolution of explicit Current Match Snapshots for derived Corpus views. |
| `src/skatmind/learning_corpus_player_catalog.py` | Derived Current-Snapshot Player observations, exact stable-ID entries, reconciled counts, and one deterministic Catalog fingerprint. |
| `src/skatmind/learning_corpus_player_aliases.py` | Exact participant/source alias observations, conflict reporting, and pure resolution without merge. |
| `src/skatmind/learning_corpus_player_statistics.py` | Exact Statistics fingerprints/history and strict latest-unambiguous or explicit-observation as-of selection without Profile derivation. |
| `src/skatmind/learning_corpus_human_evidence.py` | Minimized Human Evidence contracts, exact source fingerprints, Snapshot-scoped IDs, collection reconciliation, and privacy policies. |
| `src/skatmind/learning_corpus_human_evidence_builder.py` | One-pass Current-Snapshot source/reference reconciliation and factual Commentary/Response behavior derivation without analysis or I/O. |
| `src/skatmind/learning_corpus_human_evidence_export.py` | Builder-independent private export identity and canonical in-memory JSON bytes. |
| `src/skatmind/learning_corpus_strategy_teacher.py` | Exact Decision Report source bindings, immutable minimized method-bound Evidence, collection counts, and domain-separated identities. |
| `src/skatmind/learning_corpus_information_set_strategy_teacher.py` | Builder-only minimized safe Information-set Result/comparison Evidence and focused extension policies. |
| `src/skatmind/learning_corpus_strategy_teacher_builder.py` | Current-Snapshot/Game/Decision closure, one exact Request rebuild, retained Result validation, and strategy-field extraction without analysis execution. |
| `src/skatmind/learning_corpus_strategy_teacher_export.py` | Builder-independent private Strategy Teacher export identity and canonical path-free JSON bytes. |
| `src/skatmind/learning_dataset_v2_contracts.py` | Private task-neutral Dataset-v2 contracts, statuses, separated evidence families, immutable values, counts, and domain-separated identities. |
| `src/skatmind/learning_dataset_v2_builder.py` | Exact four-source reconciliation, Current-only safe/skipped Decision derivation, cached Statistics Contexts, strict evidence joins, and normalized pools without execution or I/O. |
| `src/skatmind/learning_dataset_v2_export.py` | Builder-independent Dataset export identity and canonical path-free JSON bytes. |
| `src/skatmind/learning_dataset_v2_partition_contracts.py` | Private partition vocabulary, immutable group/Plan/audit/view/Result contracts, and strict complete/unavailable invariants. |
| `src/skatmind/learning_dataset_v2_partition_identity.py` | Domain-separated source, request, seed, Plan, audit, view, and export identities. |
| `src/skatmind/learning_dataset_v2_partition_algorithms.py` | Exact integer objective, temporal Known-player generation, Player-component unseen-player allocation, and strict local improvement. |
| `src/skatmind/learning_dataset_v2_partition_audit.py` | Match/Record/evidence closure, Statistics temporal safety, Player overlap, and component local-optimality auditing. |
| `src/skatmind/learning_dataset_v2_partition_preparation.py` | Exact source reconciliation, Match-group derivation, complete/unavailable orchestration, summaries, and lossless indexes. |
| `src/skatmind/learning_dataset_v2_partition_export.py` | Builder-independent partition Result export identity and canonical path-free JSON bytes. |
| `src/skatmind/learning_dataset_v2_summary_contracts.py` | Private exact-Count primitives, Match/Player/Communication/Strategy/readiness summaries, policies, validation, and domain-separated identities. |
| `src/skatmind/learning_dataset_v2_summary_builder.py` | One-pass Dataset/Catalog/evidence aggregation and exact supplied-partition Result reconciliation without Plan generation. |
| `src/skatmind/learning_dataset_v2_summary_export.py` | Builder-independent cross-game Summary export identity and canonical path-free JSON bytes. |
| `src/skatmind/learning_corpus_tactical_motif_evidence.py` | Current-Snapshot Tactical Evidence/skip/collection contracts, exact coverage, policies, validation, and domain-separated identities. |
| `src/skatmind/learning_corpus_tactical_motif_builder.py` | Safe Match Decision-state reconstruction and exact shared Tactical detector reuse without Historical execution. |
| `src/skatmind/learning_corpus_tactical_motif_summary.py` | Exact global, Player, role, seat, phase, contract, distinct-Game/Match, and bounded recurrence summaries without interpretation. |
| `src/skatmind/learning_corpus_tactical_motif_export.py` | Builder-independent private Tactical Evidence/Summary export identities and canonical path-free JSON bytes. |
| `src/skatmind/learning_corpus_tactical_coaching_contracts.py` | Immutable exact Teacher Assessment, Decision Summary, focus, Player Report, Coaching Report, policy, limitation, and identity contracts. |
| `src/skatmind/learning_corpus_tactical_coaching_assessment.py` | Exact Tactical/Teacher joins and retained-method assessment without analysis execution. |
| `src/skatmind/learning_corpus_tactical_cross_game_coaching.py` | Semantic Decision consensus, repeated cross-Game thresholds, bounded priority, fixed Guidance, and Player Catalog ordering. |
| `src/skatmind/learning_corpus_tactical_coaching_export.py` | Builder-independent private Tactical Coaching export identity and canonical path-free JSON bytes. |
| `src/skatmind/match_analysis_report_source_export.py` | Exact executed Decision Report source envelope and canonical private transfer bytes. |
| `src/skatmind/match_analysis_report_source_codec.py` | Strict complete Report/Request/Result reconstruction and canonical identity verification for uploads. |
| `src/skatmind/corpus_web/` | Private one-root context, strict uploads, optimistic operations, bounded process-local sources, unlocked preparation, minimized rendering, authenticated downloads, security, and HTTP lifecycle. |
| `src/skatmind/match_capture_application_contracts.py` | Capture versions/policies, caller Card entries, builder-controlled Position Views, and immutable Application Results. |
| `src/skatmind/match_capture_position_view.py` | Current Slot/Trick/Player, exact or bounded selectable Cards, blockers, evidence, and Progress derivation. |
| `src/skatmind/match_capture_game_updates.py` | Defensive complete-Game rebuilding, deterministic IDs, automatic Play derivation, truncation cleanup, and annotation updates. |
| `src/skatmind/match_capture_application.py` | Conflict-first orchestration over existing Workspace operations without persistence or analysis. |
| `src/skatmind/match_observed_reconstruction.py` | One validated observed trace plus only its exactly reconstructable playable hands and evidence summary. |
| `src/skatmind/match_decision_review_preparation.py` | Information-safe acting-own-hand Decision snapshots, actual-Card cutoff, skipped reasons, and relative eligible Profile bindings without application. |
| `src/skatmind/match_historical_materialization.py` | Strict complete-Deal normal-completion Historical availability, construction, canonical round trip, and Match-level played-time policy. |
| `src/skatmind/match_training_source_materialization.py` | Existing unpartitioned Training source Records and ordered available/unavailable collection without Plans, partitions, or samples. |
| `src/skatmind/match_workspace_materialization.py` | Exact 36-Slot preparation, counts/status, Passed Deals, Commentary sidecars, and existing complete-list construction plus aggregation without workflow execution. |
| `src/skatmind/match_analysis_contracts.py` | Explicit Match analysis options/results, normal unavailability, no-workflow materialization reports, deterministic report IDs, and bounded report-store/export policies. |
| `src/skatmind/match_decision_analysis.py` | One prepared Decision to one validated flat Position Request and exact existing Application execution with actor-relative eligible Profiles. |
| `src/skatmind/match_information_set_search.py` | Match budget mapping, strict safe Result/comparison reconciliation, and curated browser diagnostics for one-Decision Information-set Search. |
| `src/skatmind/match_historical_analysis.py` | Strict Historical availability, selected existing modes, bounded Profile injection, one exact Application invocation, and Result reconciliation. |
| `src/skatmind/match_historical_information_set_analysis.py` | Match Historical mode adaptation, one shared Information-set Review, fixed-Policy Profile behavior, strict Result reconciliation, and safe rendering views. |
| `src/skatmind/match_analysis_exports.py` | Canonical private Root Result, materialization, Historical, Training-source, list-input, and list-aggregation download documents. |
| `src/skatmind/capture_web/` | Private Web/Protocol contracts, timecode presentation, locked context, browser-safe state, direct operation delegation, explicit analysis, max-eight report store, rendering, security, Standard Library server, downloads, and packaged assets. |
| `src/skatmind/cli/capture_parser.py` | Exact three-option Capture parser and command identity. |
| `src/skatmind/cli/capture.py` | Startup, browser open, loopback server lifecycle, interrupt, and Exit Code transport. |

The only executable format identity is `euroskat_36_standard_v1`, with provider
`EuroSkat`, display name `36er Standard`, three Players, and 36 Games. This is a
named product format contract, not ranking, qualification, prize, fee, bonus,
integration, or tournament-management behavior. See
[Match capture contracts](match_capture_contracts.md),
[Observed Game capture contracts](observed_game_capture_contracts.md),
[Match Workspace contracts](match_workspace_contracts.md), and
[Match Capture Application services](match_capture_application_services.md),
[Local Match Capture interface](local_match_capture_interface.md), and
[Match Player Statistics](match_player_statistics.md), and
[Match review and materialization](match_review_and_materialization.md), and
[Match analysis and exports](match_analysis_and_exports.md),
[Information-set Replay Coaching and Match Historical analysis](information_set_replay_coaching_and_match_historical_analysis.md),
[Learning Corpus identity and Catalogs](learning_corpus_identity_and_catalogs.md),
[Learning Corpus persistence and Workspace import](learning_corpus_persistence_and_import.md),
[Learning Corpus Player Catalog and Statistics history](learning_corpus_player_catalog_and_statistics_history.md),
[Learning Corpus human Commentary and Response evidence](learning_corpus_human_commentary_and_response_evidence.md),
[Learning Corpus Strategy Teacher Evidence](learning_corpus_strategy_teacher_evidence.md),
[Learning Dataset version 2](learning_dataset_v2.md),
[Learning Dataset version 2 partition preparation](learning_dataset_v2_partition_preparation.md),
[Learning Dataset version 2 cross-game summaries](learning_dataset_v2_cross_game_summaries.md),
[Learning Corpus Tactical Motif evidence and summaries](learning_corpus_tactical_motif_evidence_and_summaries.md),
[Learning Corpus Tactical Cross-game Coaching](learning_corpus_tactical_cross_game_coaching.md), and
[Learning Corpus browser workflows](learning_corpus_browser_workflows.md).

Validation is split between JSON Schema and Python validation:

1. JSON Schema validates stable input/output structure.
2. Python validation handles Skat-specific cross-field rules.
3. Pytest covers behavior and regression scenarios.

## Game history

| File                          | Purpose                                                                |
| ----------------------------- | ---------------------------------------------------------------------- |
| `src/skatmind/game_history.py` | Completed-trick structure, sequence, role, and rule-winner validation. |

Completed-trick validation is used to prevent inconsistent historical game states, duplicate cards, impossible sequences, and mismatched trick winners where enough information is available. When `cards` and ordered `players` are present, validation derives the rule winner and checks both `winner_player` and concrete `winner_role` metadata against that derived result. In live-decision input, supplied `winner_role` must be verifiable from `cards`, `players`, `game_type`, and concrete `declarer_player`; post-game legacy side-only histories remain supported when that evidence is absent.

Complete historical games do not use this local-perspective compatibility model.
`historical_game.py` preserves stable player IDs and fixed seats, validates all
three remaining hands at each play, and only projects derived
`declarer`/`defenders` ownership into the established scoring helpers.

## Game value and result

| File                               | Purpose                                                                                                   |
| ---------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `src/skatmind/game_declaration.py`  | Game declaration metadata, default handling, matador inference integration, and serialization.            |
| `src/skatmind/matador_inference.py` | Automatic matador inference from known declarer-card context where possible.                              |
| `src/skatmind/game_value.py`        | Game value calculation for suit, grand, and null games.                                                   |
| `src/skatmind/game_result.py`       | Raw card-point result, winner, remaining points, Schneider/Schwarz status, and adjusted result summaries. |
| `src/skatmind/game_history.py`      | Known point summary from explicit points and completed tricks.                                            |

Matador inference is intentionally conservative. It uses currently known declarer-card context and safe completed-trick ownership facts where `cards`, ordered `players`, and concrete `declarer_player` identify who played each card. It does not infer ownership from `winner_role`, `winner_player`, trick winner, hidden cards, or sampled worlds, and it does not reconstruct every possible matador state from historical trick ownership.

The historical-game branch is stricter: its validated complete deal provides
deterministic declarer and non-declarer ownership for complete matador inference.
Historical decision snapshots do not reuse that final count. They infer only
from the acting player's own cards, legitimate non-Hand declarer skat knowledge,
prior public plays, and ouvert exposure, returning `null` when evidence is
insufficient.

## Game end and settlement

| File                                | Purpose                                                                                                       |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| `src/skatmind/game_end.py`           | Legacy game-end reason handling and remaining-point assignment.                                               |
| `src/skatmind/declarer_concession.py` | Typed version-1 validation, hand-count reconciliation, and no-assignment declarer-concession adjudication.    |
| `src/skatmind/defender_concession.py` | Typed party validation, pre-concession decision derivation, and no-assignment defender-concession adjudication. |
| `src/skatmind/declarer_card_exposure.py` | Typed 4.4.4 exposure, exact defender unanimity, card reconciliation, and accepted-claim adjudication. |
| `src/skatmind/declarer_card_exposure_continuation.py` | Separate typed 4.4.4 ongoing continuation, response validation, reconciliation, and summary. |
| `src/skatmind/defender_open_play_continuation.py` | Typed 4.4.5/4.1.6 returned-hand continuation, reconciliation, and non-adjudicating summary. |
| `src/skatmind/game_continuation.py` | Runtime dispatcher for the version-1 ongoing continuation union. |
| `src/skatmind/defender_open_play.py` | Typed 4.4.5 exact-state validation, adjudication, rule assignment, and privacy-safe summary. |
| `src/skatmind/exact_rest_trick_proof.py` | Immutable, canonical, memoized exact game tree with existential exposing-defender and universal other-player nodes. |
| `src/skatmind/open_card_throw.py` | Typed 4.4.6 event, hand reconciliation, party-level unresolved assignment, and result adjudication. |
| `src/skatmind/historical_open_card_throw.py` | Exact historical replay adapter, stable-ID mapping, confirmed hand reconciliation, and shared 4.4.6 adjudication. |
| `src/skatmind/theoretical_level_exclusion.py` | Bounded jack-only theoretical Schwarz exclusion and privacy-safe evidence. |
| `src/skatmind/public_hand_constraint.py` | Immutable exact public-hand ownership constraint and stable serialization. |
| `src/skatmind/ouvert_simulation.py` | Declared-Ouvert exact-hand validation, construction, and deterministic multi-source constraint resolution. |
| `src/skatmind/game_decision.py`       | Shared bounded pre-game-end decision state for defender concession and declarer card exposure.                |
| `src/skatmind/game_shortening.py`    | Runtime dispatcher for the version-1 structured game-shortening union.                                        |
| `src/skatmind/settlement_normative_matrix.py` | Internal immutable version-3 policy matrix with 61 preserved cases, one supported bounded Historical Claim, and durable v1 exclusions. |
| `src/skatmind/party_wide_claim_contracts.py` | Private structured Claim identity, party reconciliation, exact policies, and deterministic serialization. |
| `src/skatmind/party_wide_claim_evidence.py` | Private complete-world Evidence, one Historical-prefix replay, stable/flat mapping, and one untraversed exact-state preparation. |
| `src/skatmind/party_wide_claim_proof_contracts.py` | Private Proof Request/preparation, assignment, diagnostic Move, and supplied valid/invalid/unavailable Result invariants without execution. |
| `src/skatmind/party_wide_claim_proof_executor.py` | Private bounded exhaustive exact AND/OR traversal, invocation-local memoization, counters, canonical decisive lines, and existing Result construction. |
| `src/skatmind/party_wide_claim_adjudication_contracts.py` | Private immutable adjudication Facts/Result, exact statuses, policies, no-outcome relationships, and defensive serialization. |
| `src/skatmind/party_wide_claim_adjudication.py` | Strict retained-Proof reconciliation, exact assignment composition, preexisting-winner preservation, completed private Result, and existing Final Settlement reuse. |
| `src/skatmind/historical_party_wide_claim.py` | Focused one-replay Historical Claim adaptation, one Proof/adjudication pipeline, privacy-bounded output mapping, and retained Settlement reuse. |
| `src/skatmind/overbid.py`            | Bid-value comparison, overbid detection, and required game-value calculation.                                 |
| `src/skatmind/final_settlement.py`   | Simplified single-game settlement scoring, including supported Suit/Grand overbid loss handling.              |
| `src/skatmind/performance_rating.py` | Performance layer, partial fixed-three-player SkWO scoring, and separation from settlement. |

The first three structured shortening paths bypass legacy point assignment and
preserve observed and unplayed points. Defender open play instead records an
explicit party-level assignment after complete exact proof. Declarer concession forces a defender win.
Defender concession derives the preexisting decision, grants only an undecided
game to the declarer, and separates mandatory awarded levels from levels secured
during play. Accepted declarer card exposure requires both concrete defenders,
preserves a preexisting loss, and separates declared, accepted claimed, achieved,
and overbid-required levels. Legacy reasons retain their existing simplified
assignment behavior. The separate `game_continuation` path does not adjudicate
a game end: it supplies one rule-authorized exact current public hand to analysis
while ordinary play and eventual actual settlement remain authoritative. This
can be the declarer's exposed hand under 4.4.4 or the exposing defender's returned
hand under 4.4.5 and 4.1.6. Accepted defender open play is the bounded exception:
it proves at most five unresolved tricks
exactly, without Monte Carlo, policies, or assumed play, and adjudicates rather
than continuing play.

Open card throw is a separate final rule path. It assigns every unresolved trick
and outstanding point to the opposing party, preserves preexisting decisions,
and applies only the jack-only theoretical Schwarz assessment. It does not import
or call the exact proof engine, simulation, or opponent policy. Only the thrown
hand becomes public; no second complete hand is serialized.

Issue #183 adds private version-1 structured Claim, complete Evidence,
stable-to-flat exact-state, Proof Request/preparation, assignment, diagnostic
Move, and Result contracts. It prepares one `ExactSearchState` through the
existing Historical replay and exact-state validators. Issue #184 adds the
separate private bounded exhaustive exact AND/OR executor. It reuses
`ExactSearchState`, `get_exact_search_legal_cards()`,
`apply_exact_search_card()`, and exact transitions for at most five unresolved
Tricks, with claiming-party existential and opposing-party universal choices,
exact-state memoization, canonical short-circuiting, and stable diagnostic lines.
It does not route through Generic Search, compatible-world aggregation, or an
information-set policy. Issue #185 consumes one retained Proof Result in a
separate private adjudicator. A valid proof assigns every unresolved Trick,
Card, and point to the claiming party, preserves a preexisting winner, otherwise
derives the completed Suit, Grand, or Null result, and composes one complete
Settlement through the existing normal-completion builder. Invalid and
unavailable proof create normal no-outcome Results without scoring work.

Issue #186 dispatches the approved Claim only from the Historical workflow after
one retained replay. The focused adapter builds Evidence without a second replay,
executes one available Proof, accepts only `valid`, adjudicates once, and reuses
the resulting Settlement. Matrix version `3` marks the case `supported_as_is`.
Flat `game_shortening`, live Position, Session, Match Capture, and Corpus Claim
entry remain absent. See [Historical party-wide Claim](historical_party_wide_claim.md), [Party-wide
Claim contracts](party_wide_claim_contracts.md), [Party-wide Claim proof
executor](party_wide_claim_proof_executor.md), [Party-wide Claim
adjudication](party_wide_claim_adjudication.md), and [Claim and Settlement v1
boundaries](claim_and_settlement_v1_boundaries.md).

## Simulation

| File                                   | Purpose                                                |
| -------------------------------------- | ------------------------------------------------------ |
| `src/skatmind/simulation.py`            | Monte Carlo simulation logic.                          |
| `src/skatmind/coherent_hidden_world.py` | Immutable private path ownership, reconciliation, privacy-safe summaries, and child-seed derivation. |
| `src/skatmind/hidden_card_inference.py` | Exact public-evidence constraints, compatible-world DP counts and marginals, uniform sampling, and privacy-safe summaries. |
| `src/skatmind/simulation_context.py`    | Simulation context creation and strict-context checks. |
| `src/skatmind/simulation_step.py`       | Single simulation-step handling.                       |
| `src/skatmind/canonical_multi_step_phase.py` | Immutable version-1 exact nine-row phase-plan contract, policy constants, and builder validation. |
| `src/skatmind/state_transition.py`      | Applies local plays and immutable existing-Trick completion transitions. |
| `src/skatmind/multi_step_simulation.py` | Multi-step simulation orchestration.                   |
| `src/skatmind/multi_step_recommendation.py` | Immutable privacy-safe compatible-world Search decision and compact comparison diagnostics. |
| `src/skatmind/multi_step_summary.py`    | Serializable multi-step result summaries.              |
| `src/skatmind/search_budget_profiles.py` | Immutable versioned Search budgets for interactive, historical-review, and evaluation workflows. |
| `src/skatmind/retrospective_search_comparison.py` | Search actual-card and Search-versus-Immediate aggregate comparisons. |
| `src/skatmind/bounded_search_post_game_review.py` | Flat post-game Search comparison summary construction. |

The simulation layer is probabilistic and heuristic. It is designed for analysis support, not for perfect-information solving.

The exact defender-open-play engine is intentionally outside this simulation
layer. It receives complete private post-game hands, reuses legal-card and
trick-winner rules, and exhaustively evaluates the bounded game tree. Its proof
hands never become simulation information.

Each continuation and declared Ouvert add exact public-hand constraints. Hidden
worlds fix those cards to the concrete owners and sample only genuinely unknown
hands and skat cards. Immediate, Multi-Step, and Policy Comparison share the
resolved constraints. Identical declarer evidence is deduplicated with
`declared_ouvert` precedence, while a disjoint public defender hand may coexist.

When attributed public play confirms a legal failure to follow,
`hidden_card_inference.py` adds an immutable forbidden effective-category
constraint for later decisions. Effective categories reuse `get_effective_suit`:
Suit and Grand distinguish side suits from trump, while Null uses printed suits.
Only local and exact public hands, legitimately known skat, attributed public
played ownership, and confirmed failure to follow are admitted. Tactical choices,
declarations, profiles, concessions, timing, future play, complete post-game
hands, and final result or settlement are excluded. Contradictions reject the
state rather than weakening evidence.

The inference layer uses dynamic programming to count every compatible labeled
left/right/hypothetical-skat assignment and compute exact ownership marginals.
Sampling follows DP completion counts uniformly and deterministically under a
seed; it does not use a rejection loop. Confidence is uncalibrated compatible-
world concentration only: `confirmed` means one possible owner, `high` starts at
`0.85`, `medium` starts at `0.65`, and lower concentration is `low`.

Multi-Step samples one immutable private root ownership assignment per path.
Opponent-turn preparation and candidate-trick completion use that same world;
opponent cards are removed only from their assigned owner, and the hypothetical
skat remains fixed. Every current world is reconciled with known state, hand
sizes, ownership transitions, and all public constraints, including two exact
public hands. Local card-selection policies receive only public decision-time
state and constraints. `highest_expected_value` retains separate public
counterfactual Monte Carlo samples rather than reading the private path root.

Explicit `bounded_search` or `auto` Multi-Step policies call the existing
recommendation workflow after opponent preparation has become public. Each call
receives the normalized declaration, current public opponent counts, current
public-hand constraints and evidence, legitimate Skat visibility, a separate
Immediate seed, and a per-decision Search configuration. It never receives the
coherent world. The selected card is validated and then executed through the
ordinary coherent transition. Search runs again at every local decision with a
fresh copy of the requested budget and a child of
`multi_step_bounded_search_decision_v1`.

Issue #190 adds strict `information_set_search` through the same public decision
boundary. Each local call changes only the world-selection seed through
`multi_step_information_set_search_decision_v1`, constructs fresh Search Worlds,
and retains no selected World or controlled Policy for another step. A missing
recommendation stops before local play with no fallback. The coherent execution
World stays private and independent of every Search selection.

Seeded root sampling, opponent actions, and per-step expected-value samples use
stable separate derived streams. Policy Comparison samples one shared root and
gives equal independent immutable copies to all policy paths. Serialization
exposes only count and status summaries, never hidden hands or hypothetical skat
cards. Immediate Analysis derives one inference model per decision and gives all
legal candidates a common compatible-world sequence without using a persistent
root. See [Hidden-card inference](hidden_card_inference.md) and
[Coherent hidden-world simulation](coherent_hidden_world_simulation.md).

Policy Comparison retains the four legacy defaults. Explicit Search appends
exactly the configured `bounded_search`, `auto`, or `information_set_search`
method last. Every result remains visible, but a Search path stopped without a
recommendation is marked ineligible, sorted after eligible paths, and excluded
from the recommended-policy selection. All paths receive independent copies of
one shared coherent root; the Information-set path still performs fresh public-
state Search and emits only its safe Decision Result and 16-field diagnostics.

Flat post-game Search retains the normal Search recommendation but reruns
Immediate independently from the same public position. The existing Immediate
post-game review remains intact, while the Search-specific summary aligns the
actual, Search, and Immediate cards against Search's aggregate metrics.

Historical Search Review derives each Search seed from the explicit base seed,
`historical_bounded_search_decision_v1`, stable game ID, and decision index. The
derived seed is never serialized. Search and Immediate see only the reconstructed
pre-play snapshot; future play and complete private deal ownership remain outside
the analysis. Dataset evaluation reuses this row builder, defaults to validation
and test partitions, fixes the Immediate baseline to 100 samples with base seed
0, and optionally caps one global stable decision prefix.

The named profiles are immutable structural work budgets:
`interactive_v1`, `historical_review_v1`, and `evaluation_v1`. They do not imply
calibrated latency. Search remains limited to late positions and compatible-
world determinization; sampled aggregate evidence is not an optimal policy proof.
See [Bounded search contracts](bounded_search_contracts.md) and
[Bounded Search performance](bounded_search_performance.md).

The Issue-#187 information-set Search foundation and Issue-#188 executor control
only root `me`; `left` and `right` remain separate fixed information-safe actors,
including a Defender partner. Selected exact states are paired with complete
public history, and actor Observations expose an exact own hand plus legitimate
out-of-play visibility and public facts only. Structural equality defines an
Information Set, so selected-world identity and sample multiplicity cannot split
equal observations. Preparation reuses ordered Compatible-world enumeration or
IID sampling, preserves duplicate draws, and is limited to three unresolved
Tricks. The executor groups equal controlled Observations, evaluates one common
canonical action, aggregates exact terminal utility, and retains a private
counterfactual controlled Policy with invocation-local memoization.

Issue #189 adds strict flat `information_set_search` with exactly nine settings.
Effective fixed Policies derive from existing left/right settings; `random_legal`
and role-invalid Policies produce explicit unavailability. Live execution runs
no PIMC or Immediate baseline and has no fallback. Flat Post-game Review,
Historical Review, and Training Dataset evaluation run PIMC only on the exact
retained selection, run Immediate independently, and attach the actual Card
afterward. Existing `auto` remains compatible-world PIMC followed by its existing
Immediate fallback. Public output and opt-in Provenance omit private Worlds,
Observations, hands, controlled Policy tables, caches, and seeds. Issue #190 adds
strict Multi-Step and Policy Comparison integration with retained-Result complete
provenance, without changing `auto`. Issue #191 adds strict one-Decision Match
Capture execution, revision-scoped Reports and exact transfer, focused Strategy
Teacher Evidence, Dataset-v2 propagation, Summary counts, and existing local
Corpus workflow support. At that Issue #191 baseline, Replay Coaching
classification and performance evidence remained open. Issue #192 adds
separate Information-set Replay Coaching
and private Match Historical Information-set Review/Coaching. It reuses one
retained Review, permits only complete Candidate evidence except factual forced
moves, treats PIMC and Immediate as diagnostics without fallback, and retains
time-safe Profile-derived fixed Policies without World weighting. Issue #193
adds a strict synthetic corpus, frozen functional and structural signatures,
focused regression tests, and repository-local reference timings for the
unchanged executor. This satisfies the bounded v0.17.0 performance-evidence
contract. Issue #200 accepts that deterministic functional and structural-work
evidence for v1; product SLA and cross-machine latency guarantees are not v1
requirements. See [Information-set Search contracts](information_set_search_contracts.md),
the [Information-set Search executor](information_set_search_executor.md),
[Information-set Search workflows](information_set_search_workflows.md), and
[Information-set Search Multi-Step and Policy Comparison](information_set_search_multi_step_and_policy_comparison.md),
plus [Match Information-set Search and Strategy Teacher Evidence](match_information_set_search_and_strategy_teacher.md).
See also [Information-set Replay Coaching and Match Historical analysis](information_set_replay_coaching_and_match_historical_analysis.md).
The benchmark boundary is documented in [Information-set Search performance](information_set_search_performance.md).

Immediate Analysis is available only when the normalized input state has
`next_player = "me"` and the game has not ended. Opponent-turn input keeps the
top-level position unchanged and returns an unavailable Immediate Analysis shape.

Multi-step simulation uses the normalized turn phase, not `next_player` alone.
It classifies all nine concrete canonical leader/Trick-length/next-Player rows.
Three rows begin directly at a local action, three prepare an opponent lead or
response through the first new local Decision, and three complete an already
started Trick containing the local Card before continuing from its exact winner.
Only unresolved non-concrete phases can stop with `unsupported_turn_phase`. See
[Canonical Multi-Step phase coverage](canonical_multi_step_phase_coverage.md).

Historical review may derive the same exact model from each snapshot's visible
prefix, current trick, public hands, and legitimate skat knowledge. It excludes
the actual next card, future plays and hands, results, settlement, and event facts
not yet public. Snapshot, training-feature, and rolling-evaluation flows do not
consume the Multi-Step private root; feature generation stays at version `1` and
rolling behavior remains unchanged.

## Opponent modeling

| File                                     | Purpose                                          |
| ---------------------------------------- | ------------------------------------------------ |
| `src/skatmind/opponent_policy.py`         | Opponent policy definitions and selection logic. |
| `src/skatmind/opponent_lead.py`           | Opponent lead/response behavior and coherent existing-Trick completion. |
| `src/skatmind/opponent_sequence.py`       | Canonical phase classification, bounded opponent sequencing, and continuation to the next local Decision. |
| `src/skatmind/opponent_policy_preset.py`  | Named policy presets.                            |
| `src/skatmind/opponent_profile_policy.py` | Profile-based policy recommendation.             |
| `src/skatmind/player_profile.py`          | Player profile modeling.                         |
| `src/skatmind/opponent_statistics.py`     | External statistics normalization and derivation serialization without policy application. |
| `src/skatmind/historical_opponent_statistics.py` | Exact settlement-based aggregation and reusable statistics export without policy application. |
| `src/skatmind/opponent_profile_derivation.py` | Deterministic explainable profile derivation. |
| `src/skatmind/live_opponent_profile_binding.py` | Exact left/right lookup in a validated external statistics summary. |
| `src/skatmind/opponent_profile_application.py` | Manual/external source precedence and stable live application summary. |
| `src/skatmind/historical_opponent_profile_binding.py` | Exact participant matching, strict pre-game temporal validation, and compact top-level provenance. |
| `src/skatmind/historical_opponent_profile_application.py` | Per-snapshot stable-ID left/right profile resolution and effective-policy reconciliation. |

Opponent policy handling supports both global and separate left/right opponent policy settings.

Profile derivation is deterministic and rule-based. Overall, declarer, and
defender evidence use the same unknown/low/medium/high heuristic bands at the
unavailable, `100`, and `500` boundaries, but every signal uses the confidence
of its own denominator. Exact role counts take precedence over unrounded rate
estimates. Actionable aggressive evidence precedes actionable defender evidence;
`simple_lowest` is never an actionable profile override. The combined legacy
left/right helper retains its established higher-overall-confidence and
aggressive tie fallback after each side has produced an actionable result.

When profile presets are enabled, actionable left and right player profiles can affect their respective effective left/right opponent response policies in immediate analysis and their effective left/right opponent policy settings in multi-step simulation. Explicit side-specific input and CLI overrides remain authoritative.

Some profile fields are currently behavioral-signal neutral even when they
provide evidence: `solo_win_rate`, `suit_game_rate`, and `null_game_rate`.

Standalone opponent-statistics output remains a conversion-only workflow. For
live positions, explicit case-sensitive CLI bindings can select normalized
records for left and right. Manual side profiles win over external profiles;
otherwise the external profile enters the same effective policy flow. Only its
actionable preset can apply. Historical review matches participant IDs once,
rejects matched captures at or after `played_at`, and uses each snapshot's
existing relative mapping to feed the same resolver per decision.
Historically aggregated exports enter these unchanged loaders as ordinary
version-1 statistics inputs. Their exact role counts replace estimated role
evidence, while derivation and policy precedence remain unchanged.

The current defender cooperation model is heuristic, explainable, and implemented for the fixed three-player table. It includes:

* safer defender lead behavior
* avoiding overtaking a winning partner when a partner-safe legal card exists
* safe smear while preserving the partner's winning position
* forced partner overtake using the lowest-point legal winning card
* equal-point forced-overtake tie-break using weakest sufficient trick strength
* winning-card selection using the lowest-point legal winner
* equal-point winning-card tie-break using weakest sufficient trick strength
* equal-point safe-smear tie-break using weakest trick strength
* safer discard when the declarer is winning and the defender cannot win
* narrow second-hand trump conservation on zero-point non-trump leads when only trump wins and a losing discard exists

Issue #22's current heuristic and explainable defender-partnership scope is implemented. Current limitations remain future strategy work rather than blockers for that issue:

* partnership inference is strongest in the currently supported second-hand path
* no complete rear-hand partnership model exists
* no dedicated null-game defender-partnership strategy exists
* defender partnership heuristics depend on the concrete `declarer_player` identity supplied by the input
* no perfect-information solving, search, machine learning, behavioral/Bayesian inference, or broader hidden-card inference is used by defender cooperation

## Left/right opponent policy flow

Opponent policy handling is centralized in `src/skatmind/effective_opponent_policy.py`.
The Position Application workflow builds one `EffectiveOpponentPolicySettings` value per analysis invocation
and shares it with immediate analysis, multi-step simulation, and multi-step policy
comparison.

Shared precedence, from lowest to highest, is:

1. built-in lowest-point defaults
2. input global policy preset
3. explicit input global lead and response policies
4. input-activated profile-derived side policies
5. explicit input side lead and response policies
6. global CLI policy preset
7. CLI-activated profile-derived side policies
8. explicit global CLI lead and response policies
9. explicit side-specific CLI lead and response policies

Global presets and global lead/response policies cascade to both `left` and `right`.
Actionable profile-derived policies and side-specific overrides affect only their side.
External bindings do not add a combined classification rule and do not change
this precedence. The application summary uses internal policy-source labels to
explain whether the profile or a later explicit source produced each effective
side policy.

Response-policy activation is tracked separately from complete effective side settings.
Presets, response policies, and enabled profile presets activate the sparse response map;
lead-only policy sources do not. When the sparse map is absent, immediate analysis and
multi-step candidate completion keep the legacy basic or random opponent response
behavior selected by `use_basic_opponent_strategy`.

Public declarer cards alter legal ownership information only. They add no lead,
response, or tactical policy and disclose no co-defender hand.

Immediate candidate analysis does not simulate an opponent lead and only runs for
local-action phases. It starts with the local candidate card and applies the
activated response map only to the remaining acting opponents. Multi-step
opponent-turn preparation uses the effective left/right
lead and response settings. Multi-step candidate completion and policy comparison
receive the same activated response map as immediate analysis.

`opponent_policy.py` contains the shared card-selection helpers used by these paths.

## Analysis and recommendation

| File                                | Purpose                                     |
| ----------------------------------- | ------------------------------------------- |
| `src/skatmind/analysis_report.py`    | Card analysis report construction.          |
| `src/skatmind/card_selection.py`     | Card selection helpers.                     |
| `src/skatmind/recommender.py`        | Recommendation and strategic summary logic. |
| `src/skatmind/policy_comparison.py`  | Policy comparison logic.                    |
| `src/skatmind/analysis_metadata.py`  | Analysis-mode and metadata handling.        |
| `src/skatmind/strategic_metadata.py` | Strategic metadata helpers.                 |

The analysis report is the basis for recommendations, post-game comparison, and several CLI/JSON summaries when a local decision is available. Opponent-turn and ended-game positions intentionally use an empty report.

Historical review calls the same immediate recommender and builds the report
from its returned candidate values, avoiding a second simulation pass or a
second recommendation algorithm.

Flat Information-set Search is a separate recommendation route. In Live mode it
uses only its own aggregate Result. In Post-game mode its PIMC and Immediate
baselines are retained separately before the observed Card is read; their
comparison is descriptive and does not classify accuracy or truth.

Suit and Grand candidate ranking uses expected local card-point swing. Null
candidate ranking uses an internal contract-objective utility: local declarers
prefer avoiding declarer-won evaluated tricks, while local defenders prefer
making the concrete declarer win an evaluated trick. Public point fields remain
card-point metrics.

## Post-game review

| File                              | Purpose                                                                                                                      |
| --------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `src/skatmind/post_game_review.py` | Actual-card comparison, decision quality classification, decision factors, explanation text, and recommendation gap details. |

Post-game review uses the regular analysis report and optionally compares it with `actual_card_played`. If Immediate Analysis is unavailable because there is no current local decision, post-game review returns an unavailable summary instead of comparing against an empty report.

Complete historical review applies this same comparison independently to every
snapshot. Only stable player/declarer identity is read outside the snapshot for
relative mapping and player summaries. Prior review rows and final historical
result or settlement fields are never inputs to later or earlier decisions.
Ouvert snapshots use the ordinary review path. The adapter maps the exact current
declarer hand from each decision-time snapshot into a `declared_ouvert`
constraint; no complete defender hand or future play is imported.

Current post-game review output includes:

* availability and reason
* actual card
* recommended card
* actual expected point swing
* recommended expected point swing
* expected point swing difference
* decision quality
* decision factors
* decision explanation
* actual card rank
* recommended card rank
* candidate count
* better card count

## Output

| File                                  | Purpose                                                                    |
| ------------------------------------- | -------------------------------------------------------------------------- |
| `src/skatmind/output_writer.py`        | Writes JSON output.                                                        |
| `src/skatmind/result_serialization.py` | Serialization helpers for nested and simulation-related output structures. |

Output is designed to be regression-friendly and schema-validatable.

## Schemas and validation scripts

| File                                           | Purpose                                                                  |
| ---------------------------------------------- | ------------------------------------------------------------------------ |
| `schemas/input.schema.json`                    | Stable input JSON structure.                                             |
| `schemas/game_shortening.schema.json`          | Strict version-1 structured game-shortening input union.                  |
| `schemas/declarer_concession_output.schema.json` | Strict adjudication summary and settlement-basis output.                |
| `schemas/defender_concession_output.schema.json` | Strict joint-liability, decision-state, adjudication, and settlement-basis output. |
| `schemas/declarer_card_exposure_output.schema.json` | Strict exposure, unanimity, reconciliation, decision-state, and settlement-basis output. |
| `schemas/historical_game.schema.json`          | Versioned normal or explicitly supported shortened historical-game input structure. |
| `schemas/historical_game_end.schema.json` | Extensible version-1 historical game-end union. |
| `schemas/historical_game_event.schema.json` | Version-1 non-terminal historical game-event union. |
| `schemas/historical_declarer_card_exposure_continuation_event.schema.json` | Strict timed stable-ID public-declarer-hand event. |
| `schemas/historical_declarer_card_exposure_continuation_event_output.schema.json` | Non-adjudicating declarer exposure continuation summary. |
| `schemas/historical_defender_open_play_continuation_event.schema.json` | Strict timed stable-ID continuation event. |
| `schemas/historical_game_events_output.schema.json` | Non-adjudicating historical event summary. |
| `schemas/historical_declarer_concession.schema.json` | Strict stable-ID historical concession event. |
| `schemas/historical_declarer_concession_output.schema.json` | Prefix, incomplete-trick, point, and event-summary output. |
| `schemas/historical_defender_concession.schema.json` | Strict stable-ID historical defender-concession event. |
| `schemas/historical_defender_concession_output.schema.json` | Joint-liability historical defender-concession event summary. |
| `schemas/historical_declarer_card_exposure.schema.json` | Strict stable-ID unanimously accepted historical exposure event. |
| `schemas/historical_declarer_card_exposure_output.schema.json` | Exact exposure reconciliation and stable-ID event summary. |
| `schemas/historical_defender_open_play.schema.json` | Strict stable-ID terminal historical defender-open-play event. |
| `schemas/historical_defender_open_play_output.schema.json` | Stable-ID exact proof, assignment, privacy, and final point accounting. |
| `schemas/historical_open_card_throw.schema.json` | Strict stable-participant historical open-card-throw event. |
| `schemas/historical_open_card_throw_output.schema.json` | Stable-ID throw, assignment, theoretical assessment, and final rule accounting. |
| `schemas/historical_decision_snapshot.schema.json` | Versioned historical decision snapshot output structure.             |
| `schemas/historical_game_review.schema.json` | Versioned complete historical decision-review output structure.             |
| `schemas/information_set_search_result.schema.json` | Strict safe aggregate Information-set Search Result. |
| `schemas/information_set_search_comparison.schema.json` | Strict same-selection PIMC, independent Immediate, and actual-Card comparison. |
| `schemas/historical_information_set_search_review.schema.json` | Strict per-Decision Historical Information-set Search Review and aggregates. |
| `schemas/historical_information_set_replay_coaching.schema.json` | Strict separate Information-set Replay Coaching evidence, assessments, coverage, Guidance, scopes, Outcome Context, and limitations. |
| `schemas/historical_tactical_motif_review.schema.json` | Strict separate structural Tactical Decision Facts, after-play/completed-Trick observations, exact motif/family counts, scopes, and limitations. |
| `schemas/information_set_search_evaluation.schema.json` | Strict Training Dataset-v1 Information-set Search evaluation. |
| `schemas/training_dataset.schema.json`       | Versioned training dataset input, records, provenance, and partitions.      |
| `schemas/training_dataset_output.schema.json` | Strict training dataset output, metadata, features, labels, and counts.     |
| `schemas/dataset_partition_policy.schema.json` | Optional version-1 known-opponent or unseen-player dataset policy. |
| `schemas/dataset_partition_audit.schema.json` | Strict partition-audit output, membership, overlap, coverage, and compliance. |
| `schemas/opponent_statistics.schema.json` | Versioned external opponent-statistics input and provenance. |
| `schemas/opponent_statistics_output.schema.json` | Strict preserved-source and normalized-profile output. |
| `schemas/historical_opponent_statistics_aggregation.schema.json` | Strict selected-game aggregation, exact records, and provenance output. |
| `schemas/opponent_profile_derivation.schema.json` | Strict versioned confidence, signal, classification, preset, and explanation output. |
| `schemas/hidden_card_inference_summary.schema.json` | Strict version-1 compatible-world evidence, marginals, confidence semantics, and privacy flags. |
| `schemas/output.schema.json`                   | Stable output JSON structure.                                            |
| `schemas/session.schema.json`                  | Strict standalone Public Session API Commands, values, Results, creation input, persistence/file transport, observations, review exports, and optional provenance. |
| `scripts/validate_examples_schema.py`          | Validates input examples against the input schema.                       |
| `scripts/validate_generated_outputs_schema.py` | Generates selected outputs and validates them against the output schema. |
| `scripts/validate_v1_supported_platform_matrix.py` | Builds external artifacts/environments and validates the version-1 installation, dependency-lane, and Windows/Ubuntu surface matrix without publication. |
| `scripts/check.ps1`                            | Runs the combined project check.                                         |

## Tests

Tests are organized by module and behavior in `tests/`.

Important regression areas:

* rules and legal-card logic
* completed-trick validation
* game value and final settlement
* matador inference
* game-end handling
* overbid handling
* performance rating
* information policy
* post-game review
* historical snapshot adaptation, complete review, seeds, aggregation, and leakage control
* training dataset identities, provenance, partitions, duplicate leakage, deterministic samples, and feature safety
* exact stable-player membership, policy enforcement, overlap groups, directed coverage, and audit isolation
* opponent-statistics identity, provenance, optional exact counts, percentages, normalization, explainable derivation, and workflow isolation
* historical aggregation partition/time selection, settlement outcomes, identity/label reconciliation, exact counts, provenance, and reusable export
* example files
* CLI result structure
* multi-step simulation
* opponent policies
* left/right opponent policy behavior
* schema validation
* exact hidden-card evidence, contradictions, DP counts and marginals, uniform sampling, workflow sharing, historical leakage control, and output privacy
* strict Information-set Search benchmark loading, the eight-case contract/role/
  turn/depth/profile matrix, frozen functional and structural signatures,
  same-selection PIMC and independent Immediate diagnostics, Strategy-Fusion
  common-action behavior, duplicate sampled-world weighting, timing-output shape
  without elapsed-time thresholds, fixture privacy, and unchanged package/count
  boundaries
* immutable Session Players, Commands, Logs, revisions, mode relationships,
  Diagnostics, readiness, Transition Results, serialization, revision-zero
  creation, full replay, conflicts, atomic rejection, phase advancement,
  incremental rule/information validation, trick/event/end derivation,
  promotion, forged-State rejection, export-result invariants, unavailable
  gating, exact Historical mapping, all ending/continuation chains, canonical
  round trips, immutable Requests, execution counts, and public-boundary
  compatibility
* immutable strict-prefix Undo, exact removed suffixes, one-command correction,
  deterministic replayed/discarded suffixes, first-rejection partial States,
  information safety, edited export compatibility, and current/ancestor/future/
  diverged Checkpoint lineage
* private Session persistence contracts, exact compact canonical SHA-256 domains,
  strict reconstruction and accepted-Log replay, fingerprint-mismatch rejection,
  optional Checkpoint canonicalization, recomputed lineage, optimistic conflict
  outcomes, canonical UTF-8/LF bytes, and atomic-replacement failure cleanup
* public Session file namespace identity, Save/Load Result discrimination,
  path-free Results, strict load, optimistic conflicts, and one-call delegation
* Decision Observation statuses/reasons, exact accepted Play revision/Card,
  frozen Checkpoint immutability, review Request isolation, and complete optional
  Session Provenance
* automatic Checkpoint collection/deduplication, all 12 Session subcommands,
  installed/module/Legacy parity, privacy-safe presentation, Assistant flows,
  execution counts, six examples, and eight append-only generated scenarios
* Match source-kind relationships, millisecond bounds, immutable format registry,
  statistics Snapshot identity/time reconciliation, exact fixed-place
  participants, perspective relationships, uniqueness, defensive serialization,
  no-network behavior, and unchanged public/package/count boundaries
* Match Player Statistics versions/policies, absent/eligible/ineligible Contexts,
  offset-aware strict temporal comparison, canonical Preparation, existing
  normalization/derivation equality, deterministic IDs, immutable set/clear,
  complete browser forms/state, historical read-only provenance, autosave and
  persistence conflicts, metadata-time recomputation, and clean-install capture

## Validation layers

The project uses four main validation layers:

1. JSON Schema validation for stable input/output structure.
2. Python validation for Skat-specific cross-field rules.
3. Pytest regression tests for behavior and examples.
4. Ruff for code quality.

## Design principles

Current design principles:

* Keep behavior test-driven.
* Prefer small focused modules over large orchestration files.
* Keep JSON output explicit and regression-friendly.
* Keep CLI output human-readable but secondary to structured JSON.
* Keep live-decision mode separate from post-game-review mode.
* Keep code, technical contracts, and non-browser program output in English;
  unified browser presentation supports German and English.
* Preserve the fixed three-player table; four-player support is unconditionally out of scope.

Requirements and rule-source ownership are mapped in
[Requirements traceability](requirements_traceability.md). The target product
boundary is defined in [v1.0 scope](v1_scope.md), and the authoritative bounded
classifications and blockers are frozen in the
[v1.0 scope and traceability audit](v1_0_scope_and_traceability_audit.md).
The [Unified local frontend contract](unified_local_frontend_contract.md)
governs the implemented current frontend. Its private profile and localization
foundation is documented in [Local frontend profile and localization](local_frontend_profile_and_localization.md).
The grouped Home and Product-concept presentation is documented in
[Bilingual Home information architecture](bilingual_home_information_architecture.md).
The profile-backed creation adapter is documented in [Profile-driven stateful
creation](profile_driven_stateful_creation.md). The implemented foundation and
remaining Issue-#220 task-first and complete-translation UX are governed by the
[Bilingual profile-driven frontend UX contract](bilingual_profile_driven_frontend_ux_contract.md).
