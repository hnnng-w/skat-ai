# Requirements traceability

This document is the authoritative audit of current rule and product support.
It preserves the published `v0.15.0`, `v0.14.0`, `v0.13.0`, `v0.12.0`,
`v0.11.0`, `v0.10.0`, and `v0.9.0` release baselines as historical evidence and
does not claim complete compliance with the official rules. The current
published stable and latest stable GitHub Release is `v0.16.0`, with release
theme "Learning-ready behavior and communication data" and GitHub Release title
"v0.16.0 — Learning-ready behavior and communication data". It was published
manually by the maintainer on 2026-08-18 at commit `91b1360`. Package version
`0.16.0` requires Python `>=3.13`, retains Public API contract version `1`, seven
Root workflows, and the one `skat-ai = skat_ai.cli:main` Console Script. It
contains 63 authoritative Schemas, 63 Packaged Schema Resources, six Session
examples, 85 deterministic generated-output scenarios, and 6,925 passing pytest
tests in 1083.48s. Functional Issues #171 through #179 complete the milestone,
Issue #180 completed Release preparation, and Issue #181 synchronizes
publication status without changing product behavior. GitHub Releases is the
authoritative publication record; no Package-index or PyPI publication is
claimed.

The current unreleased working baseline keeps Package version `0.16.0`, Python
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

The historical published `v0.15.0` Release points to commit `ec1c154`. Package
version `0.15.0` requires Python `>=3.13`, retains Public API contract version
`1` and exactly seven Root workflows, and contains 63 authoritative Schemas, 63
Packaged Schema Resources, six Session examples, 85 deterministic generated-
output scenarios, and 6,510 passing pytest tests. Issues #160 through #168
complete the functional milestone, Issue #169 completed Release preparation,
and Issue #170 synchronized publication status.

The historical published `v0.14.0` Release points to commit `d5589f8`. Its
baseline has the same 63 authoritative and packaged Schemas, six Session
examples, and 85 generated-output scenarios, and passed 5,892 pytest tests.
Issues #150 through #157 complete that functional milestone, Issue #158 completed
Release preparation, and Issue #159 synchronized publication status.

## Normative sources

The normative rules source is the official November 2022 publication:

* [Official ISkO/SkWO 2022 PDF](https://dskv.de/app/uploads/sites/43/2022/11/ISkO-2022.pdf)

ISkO governs an individual game: cards, bidding, declaration, play, game end,
valuation, and settlement. SkWO governs organized competition: table and list
procedures, performance calculation, standings, event administration, and
records. The explanatory `Wissenswertes fur Skatspieler` pages in the same PDF
are useful guidance, but are not numbered ISkO or SkWO provisions.

Analysis, simulation, historical-data, training-data, recommendation, and
opponent-model behavior are `skat-ai` product requirements. They are not
official game rules. Fixed three-player operation is a product constraint;
SkWO permits three-player tables in section 6.1.1 but does not define a
software product limited to them.

Rule references below are section numbers from the November 2022 PDF. Published
baseline facts were verified against source modules, schemas, examples,
validation scripts, and focused tests. Issues #127 through #134 complete the
`v0.12.0` functional milestone, and Issue #135 completed release preparation.
Issue #136 synchronized the historical publication status. That historical
published baseline validates 70 deterministic generated-output scenarios and
passes 4,762 pytest tests. The historical published `v0.11.0` baseline remains
evidence for 64 scenarios and 4,392 pytest tests; Issues #118 through #124
complete that functional milestone, and Issue #125 completed release
preparation. The published `v0.10.0` baseline remains historical evidence for 59
scenarios and 4,075 pytest tests; the published `v0.9.0` baseline remains
historical evidence for 52 scenarios and 3,558 tests.

The published `v0.12.0` package baseline exposes the Issue #127 through #129
fixed-three-player historical-list contracts and the automatic Training Dataset preparation
contracts through strict JSON, schemas, CLI output, examples, and generated-
output validation. Issue #130 appends three historical-list scenarios. Issues
#131 through #133 add the retained unpartitioned request, Plan, materialization,
and deterministic mode-specific generators. Issue #134 adds fixed public mode
dispatch, complete or explicit unavailable output, and three preparation
scenarios. The prior 67 scenarios are unchanged, and the package matrix is 70.
Issue #135 completed release metadata and documentation without changing product
behavior. The `v0.13.0` package baseline adds
public API contract version `1`, exact stable namespaces and exports, immutable
JSON document wrappers, compatibility metadata, stable errors and Exit Codes,
and unchanged legacy Root CLI behavior. Issue #139 adds internal Application
orchestration version `1`, immutable contracts and workflow options, no-I/O
dispatch across all seven Root workflows, all five Training Dataset operations,
injected Opponent Statistics, one auxiliary export artifact, and legacy CLI
transport parity. Issue #140 adds the executable public version-1 facade, direct
immutable workflow options, public execution results and artifacts, all-seven-
workflow Application execution, lazy source/editable schema validation, and
stable boundary errors. Issue #141 adds explicit Setuptools metadata, private
Package Resource schemas with authoritative byte parity, typing and Package
version metadata, Wheel/sdist artifact inspection, separate clean installations,
and local/CI distribution gates. Issue #142 adds installed CLI contract version
`1`, the exact Console Script and module entry point, one canonical Package CLI,
Legacy compatibility, and clean-install CLI/API parity. A license decision
remains open; no Package-index publication is claimed. Issue #138 adds the
internal version-1 field-level provenance language, immutable sidecar ledgers, RFC 6901
paths, deterministic coverage and dependency validation, Information Use
Context, public redaction, and safe serialization. Issue #143 adds internal live
Position propagation and adversarial enforcement. Issue #144 adds internal flat
retrospective Position, Historical Review, Historical Search Review, Replay
Coaching, and selected Position/Historical Result propagation. Issue #145 adds
all Training Dataset operations, automatic Preparation, Opponent Statistics and
Profiles, historical-list aggregation, independent comparison, and complete non-
legacy Root ledgers. Issue #146 completes non-legacy Position/base Historical
Result provenance, including base Historical execution. Issue #147 implements
bounded public Root Result and actual-artifact provenance version `1`, immutable
public attachments/artifacts/bundles, seven explicit Result mappings, the
`opponent_statistics_input` artifact mapping, existing-helper redaction,
complete recomputed coverage, default-false API and all-three-form CLI opt-in,
and strict Schema. The published `v0.13.0` baseline has 62 schemas and 77
generated-output scenarios. The seven provenance scenarios are append-only, so
the historical published `v0.12.0` facts remain 70 scenarios and 4,762 tests.
Issue #148 completed Release preparation by changing only the Package version,
current Release documentation, and matching assertions.

The published `v0.14.0` milestone provides interactive Live and Retrospective
Session capture. Issue #150 implements internal immutable Session and Command
version `1`, fixed Players and seats, Capture Modes, phases, an authoritative accepted
Command Log, linear revisions, Diagnostics, export readiness, and Transition
Result semantics. Issue #151 adds deterministic revision-zero creation, full
accepted-Log replay, immutable projection, atomic Command application, monotonic
phase advancement, incremental rule/information validation, trick/event/end
derivation, promotion, readiness, and forged-State detection. Issue #152 adds
immutable available/unavailable Session Request Export version `1`, one-replay
Historical readiness gating, exact canonical Retrospective mapping, existing
Historical builder round trip, and immutable Request construction. Issue #153
adds Position Export Options version `1`, information-safe one-replay Position
Request export, declared-Ouvert public-hand capture, and immutable replay-
verified pre-Play Decision Checkpoints. Issue #154 adds immutable Session History
Edit and Checkpoint Lineage version `1`, strict-prefix Undo, one-command
correction, deterministic first-rejection suffix replay, valid partial corrected
States, and exact current/ancestor/future/diverged lineage. Issue #155 adds the
private Session Persistence document version `1`, deterministic State/content
fingerprints, strict reconstruction and accepted-Log replay, caller-supplied
frozen Checkpoints with recomputed lineage, optimistic expected-fingerprint
writes, canonical files, and atomic same-directory replacement. Issue #156 adds
stable `skat_ai.api.v1.session` version `1`, exact immutable exports, strict
Command parsing, ten transport-free in-memory operations, one typed Result,
optional complete redacted Session Provenance, standalone Session Schema,
63-Schema Package parity, and clean-install validation. Issue #157 adds stable
public Session file Save/Load, accepted-Log Decision Observation, isolated
Checkpoint review export, automatic exact Checkpoint collection, all 12
installed/module/Legacy Session CLI subcommands, explicit Position/Historical
execution, the phase-aware Assistant, six examples, and eight append-only
scenarios. The `v0.14.0` Package baseline therefore has 85 generated outputs and
63 Schemas. The functional milestone is complete, and Issue #158 completed
Package version `0.14.0` and Release-documentation preparation without changing
product behavior. The maintainer subsequently published `v0.14.0` manually at
commit `d5589f8`. Session GUI or
browser UI, online-platform adapters, browser extensions, website scraping,
cloud synchronization, distributed locking, encryption/key management, and
automatic backup policy remain open.

The published `v0.15.0` milestone provides usable manual
post-game capture of one EuroSkat 36er Standard Match from descriptive video
evidence. Issue #160 begins that milestone with internal
immutable Match source,
timecode, format-registry, participant, optional statistics-snapshot, identity,
perspective, and serialization contracts. Issue #161 adds internal immutable
observed Games, partial and complete Play validation, free-text commentary on
any Player Decision, linked later responses, and deterministic evidence
capabilities. Issue #163 adds persistent internal 36-position Workspaces, passed
deals, Progress, fingerprints, strict Resume, and optimistic atomic local Save.
Issue #164 adds internal transport-free rapid-entry Application services with
Position Views, exact/bounded Card selection, setup updates, automatic Play
derivation, truncation cleanup, annotation editing, and passed/clear wrappers.
Issue #165 adds internal Web, Protocol, and Capture CLI version `1`, one explicit
Workspace, strict Resume or no-JSON browser creation, all 36 positions, setup and
rapid Card forms, Play correction, Commentary/Response Links, loopback token and
same-origin protection, packaged assets, compare-and-swap autosave, and explicit
conflict Reload. Issue #166 adds internal Match Player Statistics Context,
Preparation, and Update version `1`, deterministic Snapshot IDs, immutable
set/clear, strict-before-Match eligibility, existing Profile derivation,
canonical eligible input, and browser Add/Replace/Clear. Issue #167 adds internal
evidence-aware Decision preparation, strict normal-completion Historical
materialization, unpartitioned Training source Records, and complete fixed-list
construction plus existing aggregation without workflow execution. Issue #168
adds explicit one-Decision Position and strict Historical execution through the
existing Application, bounded eligible Profile application through existing
behavior, no-workflow Match materialization, deterministic max-eight ephemeral
reports, concurrency invalidation, and authenticated canonical local downloads.
It completes the functional milestone. Issue #169 changed only the Package
version, current version expectations, Changelog, and release-state
documentation to complete Release preparation. The maintainer published the
Release manually at commit `ec1c154`, and Issue #170 synchronizes publication
status. Public Match API and Schema/data workflow, global Player Catalog
exposure/persistence, public/task-specific Dataset workflows, Dataset-v2
persistence and public/task-specific partition workflows, database/remote deployment,
YouTube/EuroSkat integration, and broader pre-v1 work remain open. `v1.0.0`
remains unready.

The current published Package milestone is `v0.16.0 — Learning-ready behavior and
communication data`. Issue #171 implements the first private internal identity foundation:
content-addressed exact Workspace Match Snapshots, Player Observations,
observed-Game fingerprints, Snapshot-scoped closed references, lightweight
Catalog entries, explicit current selections, and duplicate/revision
classification. Issue #172 adds deterministic fixed-root persistence, strict
Catalog and Match Snapshot reconstruction, strict Store Resume and valid orphan
reporting, pure Catalog import and selection changes, immutable no-clobber object
publication, optimistic atomic Catalog Save, strict Workspace-file import, and
persisted explicit Current selection. Issue #173 adds a deterministic derived
Current-Snapshot Player Catalog, exact alias conflicts, retained Match-bound
Statistics history, and strict time-safe selection. Issue #174 adds deterministic
Current-Snapshot-only minimized Human Commentary and linked Response Evidence,
exact source/evidence/collection/export identities, and canonical in-memory
serialization without analysis, Dataset generation, persistence, or public
exposure. Issue #175 adds Current-Snapshot-bound method-specific Strategy Teacher
Evidence from exact executed Decision Analysis Reports, one no-execution Request
rebuild and retained Result validation per source, exact and semantic identities,
deterministic coverage, and canonical in-memory serialization without persistence
or public exposure. Issue #176 adds one private Current-Snapshot-only,
unpartitioned, task-neutral Learning Dataset version `2` with information-safe
Decision State, separate observed behavior and Player Context, exact Teacher and
Human joins, safe/skipped and joined/unjoined coverage, normalized evidence
pools, deterministic identities, and canonical path-free export without
persistence or public exposure. Issue #177 separately adds Match-group-safe
deterministic Dataset-v2 partition Plans, strict temporal Known-player and
Player-component unseen-player algorithms, complete leakage audits, lossless
partition indexes, and canonical export. Issue #178 adds private deterministic
exact-Count cross-game Match, Player, Communication, Strategy Teacher, Coverage,
Dataset Readiness, and supplied Partition Readiness summaries plus canonical
path-free export. Deletion and garbage
collection, Player Catalog persistence, persisted aliases/assertions, merge/split,
all-revision views, Human or Strategy Teacher Evidence persistence and public
transport, automatic Report capture, Historical Report import, Dataset-v2
persistence, task-specific Feature/Target separation, annotations, evaluation
baselines, ratings, derived AI tags, and public exposure remain open.
No production model is defined.

Issue #179 completes the functional private local Learning Corpus/Dataset-v2
workflow. The separate installed/module/Legacy `corpus` command opens one
explicit root, strictly uploads Workspaces and exact executed Decision Report
sources, preserves explicit Current selection, keeps at most 2,048 sources and
all prepared derived values process-local, builds Player/Human/Strategy/Dataset-
v2/known/unseen/Summary values explicitly without analysis, and provides a
minimized no-JavaScript-capable loopback dashboard with seven authenticated
canonical downloads. Issue #180 prepared Package version `0.16.0` and current
Release documentation without product behavior changes. The maintainer published
the Release manually on 2026-08-18 at commit `91b1360`, and Issue #181
synchronizes publication status without product functionality. Derived
persistence, Public APIs/Schemas, database/
remote/cloud/collaboration, automatic Report capture, Historical Report import,
task builders/taxonomies/tags, evaluation, ratings, and training remain open.
See [Learning Corpus browser workflows](learning_corpus_browser_workflows.md).

The active next planning milestone is `v0.17.0 — Rules, Search, Coaching,
and performance closure`. Issue #182 closes the v1 Claim product-decision gate
and preserves all 61 case IDs.
Issue #183 adds private structured Claim, complete Evidence, exact-state, Proof
Request/preparation, assignment, diagnostic-line, and Result contracts without
proof or Runtime execution. Issue #184 adds private bounded exhaustive exact
AND/OR proof execution without Runtime behavior. Issue #185 adds private
immutable adjudication Facts and Result, valid-proof-only exact point and Trick
assignment, preexisting-winner preservation, Suit/Grand/Null level semantics,
and composition through existing Final Settlement; invalid or unavailable proof
creates no outcome. Issue #186 updates Matrix version `3` and completes the
approved bounded Claim and Final Settlement runtime slice through Historical Game
input only, with strict public diagnostic output and downstream compatibility.
All other current Claim boundaries remain `not_supported_v1`. Session, Match
Capture, and Corpus Claim entry remain open. Issue #187 adds the private
information-set Search contracts, actor observations, pure transitions, fixed
Policies, and no-execution three-Trick Preparation foundation. Issue #188 adds
the private bounded exhaustive selected-world best-response executor, strict
retained-Preparation reconciliation, invocation-local memoization, complete
contingent controlled Policies, and conservative partial/timeout Results.
Issue #189 adds strict flat `information_set_search`, safe aggregate Results,
same-selection PIMC plus independently seeded Immediate retrospective comparison,
separate Historical Review and Training Dataset evaluation, retained-stage
Provenance, CLI, four Schemas, one example, and four generated scenarios. Existing
`auto` remains unchanged. Issue #190 adds strict Multi-Step and Policy Comparison
integration version `1` with fresh per-decision public-state Search, private
independent coherent execution, no Search World or Policy reuse, no fallback,
safe Decisions and 16-field diagnostics, stopped-row ineligibility, existing
ranking, and retained-Result complete Provenance. Match Capture, Match Analysis
Reports, and Strategy Teacher are integrated for the bounded one-Decision path
by Issue #191 together with Dataset-v2 and Corpus propagation. Match Historical
Information-set execution, Replay Coaching classification, and performance
evidence remain open. Tactical and cross-game Coaching, carefully bounded
Player Ratings where approved, broader Provenance and Confidence integration, and
the remaining pre-v1 scope audit also remain open. Final Issue titles, count,
architecture, solver design, Rating boundary, Coaching taxonomy, and Release date
are not finalized. `v1.0.0` remains unready.

## Status vocabulary

Only these values are used in the `Current status` column:

* `supported`: implemented behavior has direct validation and focused tests for
  the stated bounded requirement.
* `partially_supported`: useful behavior exists, but a stated rule, input,
  continuity, validation, or coverage gap remains.
* `planned`: an approved direction has no implementation yet.
* `not_supported`: the current repository has no implementation of the stated
  requirement or cannot produce the required result.
* `not_applicable`: the requirement does not apply to the stated product area.
* `decision_required`: product intent is not sufficiently defined.

An output field alone is not evidence of support.

## ISkO individual-game matrix

| Requirement | Source | Rule section | Current status | Current implementation | Required input or information | Known limitation | Required validation or tests | Target milestone | Required before v1.0 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Private local Learning Corpus browser and CLI transport | skat-ai product | Not applicable | `supported` | Issue #179 adds separate installed/module/Legacy `corpus` dispatch, one explicit-root local server, caller-ID initialization, strict 16-MiB Workspace and executed-Decision Report-source uploads, optimistic import and explicit Current selection, a max-2,048 process-local source store, exact unlocked seven-stage preparation with generation verification, minimized server-rendered forms, and seven authenticated canonical downloads. | One explicit root with existing parent, caller Corpus ID when absent/empty, authenticated loopback browser, exact uploads, explicit Current selections, optional exact current Report sources, Dataset ID, seeds, and positive weights. | Private local transport only. Derived artifacts and Report sources are not persisted. No Public API, Schema, automatic Report capture, Historical Report import, database/remote/cloud/collaboration, task builder, taxonomy/tag, evaluation, rating, or training is added. | Retain exact CLI options/default port, strict startup/Reload retention/uploads/temp cleanup, import statuses/conflicts/invalidation, source current/non-current lifecycle and cap, no-execution preparation order, unlocked source-change HTTP `409`, minimized state, no-JavaScript forms, seven byte-exact filenames/downloads, loopback token/cookie/Host/origin/CSP security, no external network, and shutdown cleanup. | v0.16.0 functional private local workflow published; Issue #181 synchronizes publication status | No |
| Card ordering and card points | ISkO | 1.2.1-1.2.2; 2.2.1-2.2.4 | `supported` | `rules.py` defines all points and Suit, Grand, and Null rank strength; `test_rules.py` and opponent-policy tests exercise scoring and ordering. | Valid card notation and game type. | Tests do not use one exhaustive table that asserts every card/rank combination. | Add a parameterized full point and rank-order table while retaining trick tests. | v1.0 | Yes |
| Trump rules | ISkO | 2.2.1-2.2.4 | `supported` | `get_trump_suit`, `is_trump`, and effective-suit logic implement Suit jacks plus trump suit, Grand jacks, and no Null trumps. | Game type and card. | Does not adjudicate rule violations or exposed-card consequences. | Retain focused Suit, Grand, Null, and all-jack ordering tests. | v1.0 | Yes |
| Following suit and legal-card rules | ISkO | 4.1.1-4.1.2; 4.2.1-4.2.3 | `supported` | `get_legal_cards` requires the led effective suit or trump when held; historical games replay every supplied normal or concession-prefix card against the player's exact remaining hand. | Current hand, led cards, and game type; complete playable hands for historical replay. | General revoke adjudication and rule-consequence correction are not modeled; only bounded open-play continuation under 4.1.6 is represented. | Retain Suit/Grand/Null follow tests and strict historical violation tests. | v1.0 | Yes |
| Trick resolution | ISkO | 4.3.1-4.3.4 | `supported` | `get_trick_winner` derives each winner; complete historical records derive stable winner IDs, side ownership, points, and next leaders for all ten tricks. | Three ordered cards, game type, and player order for ownership validation. | Partial legacy histories without players still cannot prove a concrete winner identity. | Retain rule-winner, strict complete-history ownership, and next-leader tests. | v1.0 | Yes |
| Bidding and declarations | ISkO | 3.3.1-3.3.11; 3.5.1-3.5.6 | `partially_supported` | `GameDeclaration` represents the final contract and bid value; runtime validation canonicalizes Suit/Grand declaration dependencies and checks Null exclusions. | Final game type, declaration modifiers, optional matadors, and optional bid value. | No auction sequence, bid/hold/pass model, declarer derivation, legal bid-value validation, or passed-in game. | Retain final-declaration dependency and precedence tests; full auction modeling is planned after v1.0 and needs separate acceptance criteria. | v1.0 final declaration; post-v1.0 auction | Final declaration: Yes; full auction: No |
| Suit and Grand game values | ISkO | 2.4.1; 2.5.1-2.5.8 | `partially_supported` | Base values, cumulative canonical declaration levels, and multiplier calculation are implemented in `game_declaration.py` and `game_value.py`. | Valid final declaration and known matador count. | The complete official outcome and settlement combination matrix is not yet covered. | Parameterize every base value and retain legal-level, invalid-dependency, and boundary-count tests. | v1.0 | Yes |
| Null game values | ISkO | 2.4.2; 2.5.9 | `supported` | Null, Null Hand, Null Ouvert, and Null Hand Ouvert map to 23, 35, 46, and 59 with focused tests. | Null game type plus Hand and Ouvert flags. | This row covers fixed values, not impossible Null overbid settlement. | Retain all four variant tests and declaration-exclusion tests. | v1.0 | Yes |
| Matadors | ISkO | 2.3.1-2.3.4; 2.5.2-2.5.3 | `partially_supported` | Explicit Suit `1..11` and Grand `1..4` bounds plus conservative position inference are tested; all supported complete historical deals deterministically infer and verify the count from declarer ownership including the original skat. | Explicit count or deterministic declarer ownership including the skat where known. | Partial positions can remain ambiguous; other complete-game claims and shortening forms are not represented. | Retain boundary, with/without sequence, Hand skat, complete-deal consistency, and ambiguity tests. | v1.0 | Yes |
| Hand games | ISkO | 2.1.1-2.1.2; 2.6.1-2.6.4; 3.5.1 | `partially_supported` | `hand_game` contributes one game-value level, is required for Suit/Grand announcements, and complete historical records enforce no discards, unplayed original skat, and declarer skat ownership for points/matadors across the supported end reasons. | Final declaration and cards needed for valuation; full deal for strict historical validation. | The engine cannot prove whether the skat was physically inspected; historical end reasons beyond the supported bounded set remain absent. | Retain historical pickup/Hand, declaration hierarchy, and skat-dependent valuation tests. | v1.0 | Yes |
| Schneider and Schwarz | ISkO | 2.5.4-2.5.8; 3.6.4; 4.4.6 | `partially_supported` | Card-point Schneider and ten-trick ownership-based Schwarz affect settlement; announced levels are canonicalized with their required Hand hierarchy. Bounded valid defender open play can guarantee defender-side rest-trick Schwarz. Open card throw derives Schneider from final rule-assigned points and Schwarz from zero losing-party tricks plus bounded jack-only theoretical non-exclusion. | Complete points; reliable trick owners, a complete bounded exact 4.4.5 state, or a valid 4.4.6 throw; declaration flags and reliable jack ownership where available. | Full rule-violation and non-jack theoretical exclusion coverage is absent. | Retain both-party, zero-point-trick, announcement, exact-proof, open-throw rule-level, jack-exclusion, higher-level, incomplete-history, and invalid-declaration tests. | v1.0 | Yes |
| Ouvert declarations | ISkO | 2.5.8-2.5.9; 2.6.5; 3.5.1 | `supported` | Suit/Grand Ouvert is canonicalized to Hand, Schneider announced, and Schwarz announced; Null Ouvert variants retain fixed values; flat and historical decisions represent the exact shrinking current declarer hand from the legitimate visibility boundary. | Final declaration, concrete declarer, and exact current declarer hand from local ownership, flat public input, or a safe historical snapshot. | Physical exposure is trusted as input or validated historical record evidence; this row does not claim optimal Ouvert strategy. | Retain declaration dependencies, all four contract families, exact ownership, played-card removal, value, result, and settlement tests. | v1.0 | Yes |
| Overbid handling | ISkO | 3.5.6; 3.6.1; 3.6.3-3.6.4 | `partially_supported` | Suit/Grand comparison and the smallest base-value multiple covering the bid drive a doubled loss, including complete normal-play pickup and Hand records. | Bid, game value, base value, and complete result. | Pre-first-trick impossibility and rule-violation interactions remain incomplete; historical overbid Null uses the separate impossible-Null workflow and is rejected here. | Retain pickup, Hand, matador-in-skat, announcement, and rule-interaction cases against approved interpretations. | v1.0 | Yes |
| Impossible Null declarations | ISkO and International Skat Court decision collection | 3.6.2; inquiries 1-3 | `supported` | A post-game-only immediate loss preserves the original Null declaration and calculates a separately supplied Suit/Grand replacement from its base value, matadors, inherited Hand status, and final bid. | Final bid, original Null Hand/ouvert flags, and optional external replacement selection with contract-specific matadors. | The engine records the supplied favorable selection but does not optimize across alternatives or infer every alternative's matadors. | Retain all Null variants, replacement bases/bounds, rounding, Hand/ouvert, immediate-loss, incomplete-metadata, schema, CLI, example, and generated-output tests. | v1.0 | Yes |
| Normal game completion | ISkO | 3.2.6; 4.1.1; 4.3.1-4.3.2; 4.4.1 | `partially_supported` | The historical branch validates a complete 32-card deal and all 30 legal plays, derives ten winners, assigns the applicable skat, totals 120 points, and completes Suit, Grand, or Null settlement. | Complete versioned historical record, or legacy complete points/trick evidence in the position workflow. | Legacy positions can still represent completion without a full deal; shortened terminal records are covered by separate bounded rows. | Retain complete normal-play contract, point, winner, settlement, and unchanged serialization tests. | v1.0 | Yes |
| Claims | ISkO | 4.4.4-4.4.6; bounded 4.1.3-4.1.6 | `partially_supported` | Flat positions support both 4.4.4 declarer-exposure branches, bounded exact final 4.4.5 defender open play, non-adjudicating 4.4.5/4.1.6 continuation, and final 4.4.6 open-card throw for either party. Historical games support all six terminal shortenings, including the Historical-only party-wide all-remaining-Tricks Claim, timed non-terminal continuation for either public-hand branch, and one continuation before one terminal shortening. Matrix version `3` preserves all 61 cases and marks the approved bounded Claim `supported_as_is`. Issues #183 through #185 provide private complete-world contracts, exact AND/OR execution, valid-proof adjudication, and Final Settlement composition. Issue #186 adds strict Historical input/output, one retained replay, one available Proof execution, valid-only terminal acceptance, diagnostic public output, Provenance, CLI, Review/Coaching, Dataset, list, and statistics integration. | Existing flat paths require their documented public or private evidence. The Historical Claim requires one stable claimant and exact party, the complete Deal and legal final play prefix, exact remaining hands and optional incomplete current Trick, and one through five unresolved Tricks. Claiming-party choices are existential and opposing-party choices universal. | Flat `game_shortening`, live Position, Session, Match Capture, and Corpus Claim entry remain absent. Invalid or unavailable proof rejects the asserted ending with no fallback or outcome. Specific future-Trick Claims, generalized non-jack exclusion, generalized correction, free text, natural language, simultaneous throws, arbitrary streams, unlimited proof, generative adjudication, unclassified conduct, multiple non-terminal events, and defender proof beyond five unresolved Tricks are `not_supported_v1`. Complete official Claim coverage is not claimed. | Retain claimant/party, complete-world, replay/proof/adjudication call-count, valid-only, no-fallback, incomplete-Trick, continuation, all-contract, assignment, winner/level/Overbid/Settlement reuse, public diagnostic-line/privacy, Review/Dataset/list/statistics, Provenance, CLI, Matrix, flat-boundary, and compatibility-count tests. | v1.0 approved bounded Historical Claim runtime slice complete; broader Claim boundaries excluded | Yes |
| Concessions | ISkO | 4.4.1-4.4.3; bounded 4.1.3-4.1.5 | `partially_supported` | The version-1 flat-position union adjudicates accepted declarer concessions and one concrete defender concession. Historical version 1 records exact-prefix declarer and defender concessions with stable IDs, shared settlement, one information-safe decision artifact per actual play, one game-level statistics contribution, and actual-play rolling evaluation. Defender joint liability needs no partner consent; the normative matrix keeps the three simplified remaining-point reasons explicitly legacy-only. | Post-game flat position or complete-deal historical prefix, valid final declaration/value, concrete parties or stable IDs, incomplete play, and supported overbid valuation. | Concession-choice prediction, disputes, language interpretation, historical continued play, and general solver proof are not modeled. | Retain party, consent, prefix ownership/order/follow, cardinality, feature safety, game weighting, rolling safety, boundary, evidence, Suit/Grand/Null, matador, overbid, flat parity, no-assignment, schema, CLI, example, privacy, isolation, and legacy-only matrix tests. | v1.0 | Yes |
| Final settlement | ISkO | 2.5.1-2.5.11; 3.6.1-3.6.4; bounded 4.1.3-4.1.6 | `partially_supported` | `final_settlement.py` covers existing paths plus historical/flat declarer-concession and accepted-exposure parity, exact defender-open-play assignment, open-card-throw opposing-party assignment, all Null variants, mandatory levels, supported overbid requirements, achieved levels, and settlement basis separation. A historical continuation before shortening delegates settlement unchanged to the selected terminal case. Issue #185 privately composes valid-proof-only party-wide Claim adjudication through the existing Final Settlement while preserving a preexisting winner and applying Suit/Grand/Null level semantics. Issue #186 reuses that exact Result and Settlement in Historical output without a second build. | Complete or adjudicated result, valid declaration, game value, bid, and reliable Trick ownership, exact Historical prefix, bounded proof, or validated open-throw evidence where required. Historical Claim composition additionally requires one valid Proof and exact adjudication Facts with complete point and Trick assignment. | General Settlement remains explicitly partial. Invalid or unavailable Claim proof creates no outcome. Flat Position, Session, Match Capture, Corpus Claim entry, unsupported endings, and rule violations remain gaps. A continuation has no immediate Settlement. | Retain normative table coverage, shortening parity, assignment, continuation no-settlement, mandatory-versus-achieved-versus-rule-level, Null, overbid, theoretical-exclusion, unsafe-evidence, no-leakage, preexisting-winner preservation, Claim composition/reuse, call counts, and invalid/unavailable-proof no-outcome boundaries. | v1.0 | Yes |

Immutable [settlement normative matrix](settlement_normative_matrix.md) version
`3` provides the required contract/level/outcome classification without changing
any of its 61 case IDs. It keeps Claims, Concessions, and Final Settlement
`partially_supported`; distinguishes direct rules, approved bounded behavior,
legacy compatibility, one supported bounded Historical Claim, and durable v1
exclusions; and retains table-driven coverage for every current
shortening, historical terminal and continuation kind, legacy end reason, normal
completion, and impossible Null. The approved historical extension is at most
one supported non-terminal continuation followed by at most one supported
terminal shortening, with `supported_as_is` status and delegation to existing
terminal cases. The party-wide all-remaining-Tricks Claim is the only supported
v1 Claim case. It is Retrospective-only, complete-world,
party-existential/opponent-universal, and bounded to five unresolved Tricks.
Private contracts, exact-state preparation, bounded proof execution, immutable
adjudication Facts/Result, and Final Settlement composition are integrated
through Historical Game input. The Matrix implementation tuple names the
focused private and Historical modules and has no Runtime unavailable reason.
Invalid or unavailable proof rejects the asserted terminal record and creates
no terminal outcome or Settlement. Every other current Claim boundary is
`not_supported_v1`; no canonical case remains `decision_required` or uses the
historical `out_of_scope_v0_11` status. See
[Claim and Settlement v1 boundaries](claim_and_settlement_v1_boundaries.md).

## SkWO list and competition matrix

The public identifier `isko_list` is retained for compatibility. The formula it
selects is governed by SkWO 6.3.1, so documentation calls it SkWO-style
performance scoring.

| Requirement | Source | Rule section | Current status | Current implementation | Required input or information | Known limitation | Required validation or tests | Target milestone | Required before v1.0 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Fixed three-player list performance | SkWO | 6.1.1-6.1.5; 6.3.1 | `supported` | Implements game points plus 50 per own win, minus 50 per own loss, and 40 per other declarer loss from totals, contributions, local results, or explicit standings games. Historical-list contract version 1 validates exactly 36 ordered Played Game or Passed Deal positions, three fixed identities, rotation, settlement-derived contributions, cumulative player totals, 36 progression snapshots, complete reconciliation, and deterministic privacy-safe serialization. The strict public root workflow builds and aggregates one source exactly once. Public comparison validates two or more independent sources, aligns the same players by stable ID, preserves the first source as reference, reports comparison-minus-reference final count and all fourteen player-total deltas, and compares ranks only when both sources are final. | One player's totals/contributions, three identified players and declarer results, one complete public historical-list request, or at least two public independent source requests with unique list IDs and disjoint Played Game IDs. | Comparison adds no progression matching, cross-list totals, series standings, ratings, winner, recommendation, tournament management, or official reporting. | Retain every existing input-mode formula; test exact historical identities, all endings, Passed Deal zero-score progression, cumulative invariants, source-fact single derivation, old-path equivalence, independent-oracle agreement, one-pass source execution, source independence, participant reconciliation, final deltas, rank availability, strict schemas, CLI isolation, exact examples/scenarios, and recursive serialization privacy. | v1.0 bounded requirement complete | Yes |
| Standings | SkWO | 6.3.1 | `supported` | Produces exactly three standings rows ordered by total performance points, own wins, own losses, then an optional externally executed lot; unresolved ties use shared ranks and explicit `lot_required` status. Public historical-list aggregation produces provisional standings after every position and final standings after position 36. Public independent-list comparison reports rank movement only between two resolved final rankings and preserves four explicit availability statuses. | Three player identities and supplied game outcomes/scores, one complete public historical-list request, or two or more independent source requests; optional exact tied-player `lot_order` for final standings. | Table/input order is presentation-only, the engine does not execute a random lot or infer ranks from unresolved ties, and official reporting remains unsupported. | Retain ordering, shared-rank, exact lot-group validation, old-path equivalence, resolved and unresolved comparison status, schemas, CLI, generated-output, and privacy tests. | v1.0 bounded requirement complete | Yes |
| Series aggregation | SkWO | 4.2(c); 5.4; 6.1.3-6.1.4; 6.2.4 | `partially_supported` | Already aggregated values may be labeled list or series totals. | Pre-aggregated totals. | No dedicated series identity, list membership, multi-list rollup, seating, corrections, or series-level standings. | Preserve bounded summaries; formal series aggregation is not required for the intended product. | Not required | No |
| Tournament aggregation | SkWO | 1.1-1.6; 2.3-2.4; 3.1-3.4; 4.1-4.5; 5.1-5.5 | `not_supported` | No tournament model exists. | Event plan, participants, series, tables, officials, results, and accounting data. | Governance and procedural requirements are broader than score aggregation. | No implementation gate; tournament management is not required for the intended product. | Not required | No |
| Official reporting | SkWO | 4.5; 6.2.1-6.2.7; 6.4.1-6.4.3 | `not_supported` | General JSON and CLI reports exist, but no official list or federation report format. | List entries, running totals, signatures/approvals, corrections, submission, and retention metadata. | SkWO prescribes duties but no official digital interchange or layout in this PDF. | No implementation gate; official federation report formats are not required for the intended product. | Not required | No |

## skat-ai product matrix

Issue #115 completes the functional `v0.10.0` bounded-search milestone beyond
live and Multi-Step use. Flat post-game Search now runs an independent Immediate
baseline; Historical Search Review and dataset Search-versus-Immediate
evaluation report strict decision and aggregate summaries; and immutable named
profiles, independent Suit/Grand/Null quality fixtures, convergence evidence,
and a reproducible performance corpus now exist. Search remains late-game
determinization, sampled quality is not calibrated, and there is no latency or
optimal imperfect-information policy guarantee. The bounded-search row therefore
remains `partially_supported`; Issue #115 does not close every stronger-solver
requirement for v1.0.

The `v0.10.0` milestone is complete, but the general v1.0 stronger-solver
direction remains only partially supported. Its open requirements include an
information-set Policy Search extension beyond the flat, Historical Review, and
Training Dataset evaluation routes; complete Strategy Fusion correction beyond
the controlled Player; complete-contract solving; calibrated sampled
probabilities; and latency guarantees. Issues #187 and #188 define and execute the
private controlled-Player foundation. Issue #189 routes strict flat analysis and
adds descriptive same-selection PIMC and independent Immediate comparison. It
does not claim equilibrium, global optimality, a complete-contract solution, or
calibrated probability.

Issue #120 adds internal Replay Coaching contract version `1`. It separates
decision-time evidence from retrospective observed-card attachment, reuses one
Historical Search Review Search run and one Immediate run, and defines stable
phase, status, evidence-basis, impact, factor, limitation, validation, and
serialization semantics. It adds no public Coaching Report, schema, CLI field,
example, or generated output and makes no causal final-outcome claim. Complete-
game retrospective analysis therefore remains `partially_supported`.

Issue #121 adds internal prioritization version `1`: at most five deterministic
Key Decisions, separate Contract-success decision opportunities and first
recorded-prefix outcome Turning Points, complete-normal fallback, threshold-free
high-impact classification, and non-causal factors and limitations. Existing
public review output remains unchanged. Patterns, advice, and a complete public
Coaching Report remain absent, so complete-game retrospective analysis remains
`partially_supported`.

Issue #122 adds internal guidance version `1`: patterns by acting player, role,
phase, and normalized contract require two occurrences; actionable missed-impact
and Search-versus-Immediate review patterns remain separate from descriptive
aggregate-equivalent, forced, and Search-unavailable patterns; every Key
Decision receives one fixed-template recommendation; and at most five actionable
pattern recommendations are ranked and deduplicated by type plus decision
evidence. No tactical motif, player rating, causal claim, public schema, CLI, or
complete Coaching Report is added, so complete-game retrospective analysis
remains `partially_supported`.

Issue #123 adds complete internal report version `1` and method
`historical_replay_coaching_v1`. It composes privacy-safe game/player context,
separately attached final outcome context, reconciled coverage, every retained
assessment, prioritization, guidance, zero-preserving player/role/phase/current-
contract summaries, and canonical limitations from one existing coaching
analysis. Search and Immediate call counts and public Historical Search Review
output remain unchanged. No public schema, CLI, example, generated output,
tactical motif, rating, ranking, or causal claim is added, so complete-game
retrospective analysis remains `partially_supported`.

Issue #124 exposes that exact retained report through
`--historical-replay-coaching` and
`historical_game_summary.historical_replay_coaching_summary`. The strict public
schema, concise CLI presentation, recursive privacy checks, normal Grand/Null/
shortened generated scenarios, and combined one-pass Historical Search Review
path preserve all existing analysis semantics. Tactical motifs, cross-game
analysis, stronger Search, ratings, and causal attribution remain absent, so
complete-game retrospective analysis remains `partially_supported`.

Issue #134 exposes the retained preparation contracts through root
`training_dataset_preparation_input`, workflow identifier
`training_dataset_preparation`, and output
`training_dataset_preparation_summary`. Mode alone dispatches Known-opponent to
`temporal_known_opponent_v1` and unseen-player to
`component_balanced_unseen_player_v1`. Complete output losslessly materializes
the existing version-1 Training Dataset and audit. Unavailable output succeeds
with explicit null dataset/audit and no partial Plan. The request has no
algorithm field or default weights; the CLI accepts only `--input`, `--output`,
`--quiet`, and the cross-workflow `--include-provenance` option; Plan and CLI output are card-free while a complete nested dataset
retains source cards. The strict request, Plan, and output schemas plus three
examples and generated scenarios cover this bounded public workflow. Additional
algorithms, algorithm overrides, fallback or partial Plans, global optimization,
ratio guarantees, Sample- or Player-count balancing, component splitting, model
training, and automatic evaluation remain unsupported.

Issue #138 defines the shared internal provenance language without changing any
existing workflow. Version 1 includes immutable field and subtree entries,
structured source references, explicit exemptions and ledger statuses,
deterministic leaf-coverage auditing, same-document dependency and temporal
validation, Information Use Context, engine-private public redaction, and safe
serialization. Confidence remains a separate contract. No public API export,
schema, output field, CLI behavior, example, or generated scenario changes.

Issue #139 defines the separate internal Application orchestration language and
executes existing workflows without transport I/O. Version 1 includes immutable
invocation, option, external-document, result, and artifact contracts; one
handler for every `WorkflowV1` value; exactly five isolated Training Dataset
operations; optional injected Opponent Statistics for Position and Historical
execution; and one optional `opponent_statistics_input` export artifact. Legacy
`main.py` remains the argument, file, output, and presentation boundary. The
public API export snapshots, schemas, examples, generated scenarios, Package
version, and provenance outputs remain unchanged.

Issue #140 exposes the Application boundary through public `parse_request`,
`execute`, `execute_document`, and `serialize_result`. It validates Root input,
Root output, and reusable artifacts lazily against local repository schemas;
preserves Root output and normal states; separates artifacts; translates direct
workflow options and raw boundary errors; performs no caller transport I/O; and
keeps Package, CLI, schema, example, generated-scenario, and provenance contracts
unchanged.

Issue #141 replaces the source/editable schema backend with lazy private Package
Resources and adds explicit Setuptools build metadata, `py.typed`, Package-Root
`__version__`, exact schema synchronization, one Wheel and one sdist, artifact
inspection, separate clean installations, external-working-directory public-API
smoke tests, and local/CI gates. It changes no Package version, Root schema
meaning, workflow, Result, generated scenario, legacy CLI behavior, or provenance
output. It adds no installed CLI and performs no publication.

Issue #142 adds exactly `skat-ai = skat_ai.cli:main`, `python -m skat_ai`, a
Package-owned canonical parser/transport, `--version`, unchanged workflow output,
Legacy Root facade compatibility, and Wheel/sdist clean-install command and
Public API parity. It changes no Package version, Root Schema, example, generated
scenario, Public API export, Provenance output, or publication state.

Issue #143 adds Application provenance version `1` and live-analysis provenance
version `1`. Live Position execution now constructs complete decision documents
before flat and simulated local selection, validates every entry in a
decision-time Information Use Context, maps existing Immediate, Search, inference,
Multi-Step, Policy Comparison, continuation, and external-profile evidence, and
attaches an all-leaf partial-legacy ledger for the exact Position Result. The
public API, Root JSON, schemas, CLI, examples, and generated scenarios remain
unchanged.

Issue #144 adds retrospective-review provenance version `1` and Replay Coaching
provenance version `1`. Flat retrospective Position and Historical execution now
retain decision input and decision-time analysis before actual-card assessment,
reuse already executed Immediate and Search values, cover requested Snapshot and
review summaries plus the complete Coaching report, and attach selected
partial-legacy Position/Historical Result provenance. The public API, Root JSON,
schemas, CLI, examples, generated scenarios, Package version, and established
workflow call counts remain unchanged.

Issue #145 adds Training Dataset, Dataset Preparation, Opponent workflow, and
historical-list provenance version `1`. All five Training Dataset operations,
complete/unavailable Preparation, external and historically aggregated Opponent
records and Profile derivation, 36-position list aggregation, standings,
external lots, and independent comparison now use complete internal attachments
and complete non-legacy exact Root Result ledgers. Decision-time Features and
predictions remain separate from retrospective Targets and metrics; audit and
assignment dependencies are information-restricted; list progression is prefix-
safe; and existing values are consumed without workflow reruns. The public API,
Root JSON, schemas, CLI, examples, 70 generated scenarios, Package version, and
established call counts remain unchanged.

Issue #146 adds complete Result provenance version `1`. Position and Historical
Root Result ledgers now have `complete` status, no limitations or legacy
exemptions, exact leaf coverage, forward-only Declaration/Value/Overbid/score/
Result/Settlement/Performance/list/replay/event dependencies, private-proof-safe
redaction, and unchanged workflow call counts. Base Historical execution now has
a result-only provenance bundle. Public API, Root JSON, Schemas, CLI, examples,
70 generated scenarios, Package version, and distribution contracts remain
unchanged.

Issue #147 selects exactly one mapped Root Result attachment plus attachments for
artifacts actually returned. It applies the existing pure public-redaction helper
and recomputes complete coverage over scope
`root_result_without_field_provenance` or `artifact_document`; consumed-input,
decision, intermediate-stage, and unredacted attachments are not exposed. Public
API `ExecutionOptionsV1.include_provenance` defaults to false,
`ExecutionResultV1.field_provenance` is typed while its flattened envelope stays
unchanged, and installed/module/Legacy CLIs share `--include-provenance` with
concise and quiet behavior. Strict `field_provenance.schema.json` raises the
eventual `v0.13.0` Schema count to 62. Seven append-only scenarios raise the
eventual `v0.13.0` matrix to 77 without rewriting the published 70-scenario
`v0.12.0` evidence. Confidence contracts remain separate.

Issue #150 begins `v0.14.0` with a separate internal Session authoring language.
It adds immutable fixed-three-Player identity, Live and Retrospective Modes,
phases, nine typed Commands, an authoritative accepted Log, linear revisions,
Diagnostics, Position/Historical readiness, valid-incomplete State, Transition
Result semantics, and deterministic serialization. It changes no Engine State,
Historical replay, Public API export, Root workflow, CLI, Schema, example,
generated scenario, or Package version, and does not apply Commands.

Issue #151 executes that internal language through transition-engine and
projection version `1`. It adds canonical revision-zero State creation, one-pass
full accepted-Log replay, stored-State equality checks, atomic candidate
application and unchanged-State rejection, revision-conflict precedence,
monotonic phase advancement, incremental Deal, Declaration, Skat/Discard, Play,
ownership, legal-card, trick, continuation, terminal-shape, promotion, and
information-policy validation, plus Position/Historical readiness calculation.
It invokes no Search, analysis, review, adjudication, Settlement, Application, or
Public API path and changes no public export, Root workflow, CLI, Schema,
example, generated scenario, Historical record, Game State, or Package version.

Issue #152 exports only a Historical-ready Retrospective Session. It adds Session
Request Export version `1`, immutable available/unavailable Results, one accepted-
Log replay, exact readiness gating, projection-to-`historical_game_input`
mapping, existing Historical builder validation, canonical serialization and
rebuild, and immutable `RequestDocumentV1` construction. It executes no
Historical workflow, Application, or Public API path and changes no public
export, Root workflow, CLI, Schema, example, generated scenario, Historical
contract, Game State, Provenance contract, or Package version. The count remains
seven Root workflows, 62 authoritative and packaged Schemas, 77 generated-output
scenarios, and Package version `0.13.0`.

Issue #153 exports a Position-ready local decision without executing it. It adds
immutable Position Export Options version `1`, exact Position readiness gating,
stable-to-relative information-safe mapping, decision-visible Skat and Matador
handling, one narrow declared-Ouvert public-hand Command, existing Position
builder validation, and immutable replay-verified pre-Play Decision Checkpoints.
It generalizes Session Request Export version `1` for the existing Position
target without changing that version. It invokes no Position workflow,
Application, or Public API path and changes no public export, Root workflow, CLI,
Schema, example, generated scenario, Position input contract, Provenance
contract, or Package version. The count remains seven Root workflows, 62
authoritative and packaged Schemas, 77 generated-output scenarios, and Package
version `0.13.0`.

Issue #154 edits only internal immutable Session history. It adds four exact Undo
statuses, five exact Correction statuses, four exact Checkpoint relationships,
revision-conflict precedence, strict-prefix projection replay, replacement at one
accepted revision, replay of only the original later source suffix, stop-before-
first-rejection semantics, valid partial corrected States, and exact-prefix plus
rebuilt-Request lineage classification. Original States, Logs, records, Commands,
Requests, Checkpoints, and Options remain unchanged; Redo ownership remains with
the caller. It executes no Root workflow, Application, Public API, CLI, Schema,
example, generated scenario, or Provenance path and changes no public export or
Package version. The count remains seven Root workflows, 62 authoritative and
packaged Schemas, 77 generated-output scenarios, and Package version `0.13.0`.

Issue #155 adds private deterministic Session persistence and resume. Immutable
version-1 documents retain the authoritative accepted-Log State plus canonically
ordered caller-supplied frozen Decision Checkpoints. Domain-separated SHA-256
State and content fingerprints distinguish same-revision corrected histories and
checkpoint-content changes. Resume strictly reconstructs every typed value,
replays the accepted Log, verifies both fingerprints, and recomputes Checkpoint
lineage. Canonical UTF-8 files use expected-content-fingerprint compare-and-swap
with `saved`, `unchanged`, and `conflict` Results, a second pre-replacement check,
and durable same-directory temporary-file atomic replacement. It adds no Root
workflow, Application, Public API, CLI, Schema, example, generated scenario,
Provenance path, automatic Checkpoint collection, or Package version. The count
remains seven Root workflows, 62 authoritative and packaged Schemas, 77
generated-output scenarios, and Package version `0.13.0`.

Issue #156 adds the stable Public Session API, exact immutable contract identity,
strict Command parsing, ten one-call in-memory operations, typed Results,
optional complete redacted Session Provenance, and strict standalone Session
Schema. Issue #157 appends two operations, the stable Public Session File API,
Decision Observation/review, automatic Checkpoints, CLI/Assistant transport,
explicit Application execution, examples, and scenarios. The published `v0.14.0`
baseline has seven unchanged Root workflows, 63 authoritative and packaged
Schemas, six Session examples, 85 generated outputs, 5,892 passing pytest tests,
and Package version `0.14.0`; the historical published `v0.13.0` baseline remains
62 Schemas and 77 scenarios. Issue #158 completed Release preparation before the
maintainer's manual publication. See
[Session persistence and resume](session_persistence_and_resume.md),
[Session Decision observations](session_decision_observations.md), and
[Session CLI and end-to-end capture](session_cli_and_end_to_end_capture.md).

| Requirement | Source | Rule section | Current status | Current implementation | Required input or information | Known limitation | Required validation or tests | Target milestone | Required before v1.0 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Match Capture identity and metadata | skat-ai product | Not applicable | `partially_supported` | Issues #160 through #167 define and consume internal Match identity, source/timecode, format, participants, perspective, optional Statistics Snapshots, persistence, browser editing, and preparation. Issue #168 consumes the unchanged definition for private analysis and reports. | Caller-supplied Match identity/title/platform, optional external ID and played time, one canonical format, one descriptive source, exactly three participants, one perspective Player, and optional Match-bound statistics snapshots. | Public Match API and Schema/data workflow, public or persisted Player Catalog, YouTube/EuroSkat integration, ranking, qualification, prize, fee, and bonus rules remain absent. | Retain source/no-network behavior, registry identity, deterministic Snapshot IDs, temporal eligibility, fixed-place/perspective relationships, browser editing, uniqueness, and unchanged public/count baselines. | v0.15.0 functional local capture complete; public use open | Yes |
| Observed Game evidence and commentary | skat-ai product | Not applicable | `partially_supported` | Issue #161 defines observed Games and annotations; Issues #163 through #167 persist, edit, validate, and prepare them. Issue #168 executes only explicitly selected safe Decisions or strict Historical Games. The actual Card is retrospective evidence, not an optimal label; Commentary and Response Links do not enter analysis or Coaching. | One exact Match definition, selected position, optional Declarer/Card evidence, zero through 30 public Plays, and optional annotations. | Public Match API/Schema/data workflow and tactical interpretation remain absent. Missing Skat/Discards can block Historical execution while a Decision remains preparable. | Retain information cutoff, automatic actor/index derivation, annotation isolation, partial-vs-strict availability, and no inferred taxonomy or causal claim. | v0.15.0 functional local observation and analysis complete | Yes |
| Persistent EuroSkat Match Workspace | skat-ai product | Not applicable | `partially_supported` | Issue #163 defines exact 36-Slot persistence; Issues #165 and #166 add one-file CAS autosave and Snapshot updates. Issue #168 derives reports without changing persisted bytes. | One exact Match definition, optional observed Games/passed deals/Snapshots, exact revisions, one explicit existing-parent file path, and retained fingerprint. | Structural completion does not imply Historical materializability. Reports are process-local, max-eight, revision-scoped, and not Workspace-persisted. No Public Match API/Schema, distributed lock, retry/merge, remote/cloud/encryption/backup exists. | Retain persistence bytes, one operation/at-most-one Save, no context replacement on conflict, explicit Reload, report invalidation/concurrency discard, and private path/fingerprint omission. | v0.15.0 functional local persistence complete | Yes |
| Private Learning Corpus identity, Catalog, persistence, Workspace import, derived Player history, Human Evidence, and Strategy Teacher Evidence | skat-ai product | Not applicable | `partially_supported` | Issues #171 and #172 define immutable Match Snapshots/references, authoritative Catalog/Current selections, fixed-root strict persistence, orphan reporting, pure Catalog changes, no-clobber objects, atomic Save, and Workspace import. Issue #173 derives a non-persisted Current-Snapshot-only Player Catalog with exact stable identity, label history, participant/online-source aliases and conflicts, complete exact Statistics observations, shared source-Match temporal status, and latest-unambiguous or explicit-observation as-of selection. Issue #174 derives minimized exact human Commentary and explicitly linked Response behavior from Current Snapshots only, with exact media context, deterministic identities, reconciled counts/references, and canonical in-memory export. Issue #175 binds exact executed Decision Analysis Report sources to explicit Current Match Snapshots, performs one no-execution Request rebuild and retained Result validation per source, preserves method-bound Immediate/Search/Auto evidence, derives exact and semantic identities, and builds deterministic collections and canonical in-memory exports. Issue #179 exposes exact private browser initialization, import, Current selection, Report-source transfer, process-local preparation, and canonical downloads without changing persistence. | One exact strict Store Result; persistence operations additionally require the explicit root/source/expected revision and fingerprint options. Statistics selection requires exact stable Player ID, target time, mode, and an explicit observation ID where applicable. Human Evidence requires only the strict Store Result. Strategy Teacher Evidence additionally requires explicitly Snapshot-bound exact executed Decision Reports. Browser transport requires one explicit root, exact uploads, explicit Current selections, preparation values, and loopback authentication. | No deletion, garbage collection, recovery UI, Player Catalog persistence, Human or Strategy Teacher Evidence persistence/public transport, persisted aliases/assertions, merge/split, all-revision view, automatic Report capture, Historical Report import, Teacher ranking/consensus, derived tags, or model training exists. Orphans are reported but never included automatically. | Retain exact versions/tuples/policies/domains, strict JSON and canonical bytes, Current-only and orphan exclusion, exact identity/label/alias behavior, source Commentary/Response fingerprints, original text and commentator identity, observed subject/response Cards and timecodes, noncausal associations, minimized privacy, record fingerprints/provenance, strict RFC 3339 eligibility and ambiguity, no merge/Profile/analysis/Dataset-v1 behavior, persistence compatibility, exact executed-Report acceptance and Snapshot/Decision/actual-Card reconciliation, one-rebuild/no-execution semantics, retained Result validation, exact and semantic identities, method/fallback/Candidate preservation, duplicate-source rejection, deterministic collection counts/order/export, Human/Teacher separation, browser upload/preparation/download isolation, no reranking/consensus/ground-truth claim, and unchanged 0.15.0/63/6/85 baselines. | v0.16.0 functional private local Corpus workflow complete; derived persistence and public layers open | No |
| Private Learning Dataset version 2 | skat-ai product | Not applicable | `supported` | Issue #176 reconciles exact Current Corpus sources into the unchanged unpartitioned task-neutral Dataset. Issue #177 reconciles that exact Dataset with its Player Catalog, derives indivisible active Match groups and inactive Snapshots, generates strict temporal Known-player or Player-component unseen-player complete/unavailable Plans, audits Match/Record/skipped/Teacher/Human/Statistics closure, and builds lossless partition indexes plus canonical export. Issue #178 reconciles the exact Dataset, Player Catalog, and one supplied Result per mode into descriptive exact-Count Match, Player, Communication, Strategy Teacher, Coverage, Dataset Readiness, and Partition Readiness summaries with deterministic identities and canonical export. Issue #179 explicitly builds and downloads that exact seven-artifact process-local chain in the private Corpus browser. | Partition preparation requires the exact matching in-memory Dataset and Player Catalog, mode, caller seed, and three positive integer weights. Summary construction requires the exact Dataset, Player Catalog, one `known_player` Result, and one `unseen_player` Result. Browser preparation requires an explicit Dataset ID, both seeds, and all three positive weights. | No Dataset-v2 or Summary persistence, Corpus object kind, task-specific Feature/Target builder, derived tag, Public API, Schema, example, generated scenario, rating, ranking, communication interpretation, evaluation, model-readiness claim, global unseen-player optimality, or model training. Training Dataset version `1` is separate. | Retain source/fingerprint reconciliation, group indivisibility, equal-time and Train-coverage rules, transitive components, exact objective and seed ties, closure/temporal audits, supplied-Result-only readiness, exact Count/Coverage reconciliation, stable identities, lossless view, privacy, deterministic export/download bytes, no execution, process-local invalidation, and all compatibility baselines. | v0.16.0 private Dataset, partition, summary, and local preparation workflow complete | No |
| Rapid post-game Match Capture Application services | skat-ai product | Not applicable | `partially_supported` | Issue #164 defines transport-free rapid-entry services; Issue #165 maps browser mutations to them. Issues #166 through #168 remain separate Statistics, preparation, analysis, report, and export layers. | One loaded Workspace, selected position, exact revision, and operation-specific observed evidence. | Capture services themselves still perform no I/O, analysis, or downstream preparation. Bounded Card candidates do not assert ownership or legality. Public Match API/Schema/data workflow, tactical interpretation, and AI commentary remain absent. | Retain service identities, direct mutation delegation, conflict precedence, atomic batches, automatic actors/indexes, no hidden completion, and import direction. | v0.15.0 functional local transport complete | Yes |
| Match review and materialization preparation | skat-ai product | Not applicable | `supported` | Issue #167 defines information-safe Decision preparation, strict normal-completion Historical materialization, unpartitioned Training sources, and complete fixed-list aggregation. Issue #168 exposes explicit private preparation reports and canonical downloads while materialization itself executes no workflow. | One validated Workspace; exact acting hand per Decision; strict complete Deal for Historical/Training; complete 36-Slot evidence for list aggregation; optional exact lot order. | Preparation itself applies no policy and executes no workflow. No Dataset Plan/partition/sample, list comparison, persisted report, Public Match export/API/Schema, or media-offset timestamp derivation exists. | Retain Decision/Historical evidence separation, actual-Card cutoff, Skat/Ouvert visibility, canonical round trips, Match time, Passed Deals, Commentary isolation, counts, standings, unresolved lot, and twelve round ends. | v0.15.0 bounded internal preparation complete | Yes |
| Match analysis and private exports | skat-ai product | Not applicable | `supported` | Issue #168 adds explicit one-Decision Immediate/Search/Auto Position execution from prepared snapshots; strict selected-mode Historical execution; eligible actor-relative Profile application through existing supported behavior; one exact Application invocation; deterministic SHA-256 reports capped at eight; and authenticated canonical Root/Historical/Training/list downloads. | Explicit authenticated action, exact expected revision, selected preparable Decision or strict Historical Game, deterministic options/seeds, and optional eligible Match Statistics. | No automatic analysis, Workspace report persistence, Profile weighting of Search, Profile effect on Coaching, Commentary in Coaching, Public Match API/Schema/Root/CLI, calibrated ML, optimal hidden-information Search, or full official-rule claim. | Retain normal unavailability, actor exclusion, disabled/nonactionable Profile behavior, one-call execution, no-workflow materialization, privacy, canonical bytes/names, stale/concurrent invalidation, and bounded/Strategy Fusion/noncausal limitations. | v0.15.0 published bounded Match analysis complete | Yes |
| Local Match Capture browser and CLI transport | skat-ai product | Not applicable | `supported` | Issues #165 and #166 add the private Web/Protocol/Capture CLI and 19 capture/statistics operations. Issue #168 appends three explicit analysis/materialization operations for 22 total, curated report pages, ephemeral report navigation, and authenticated downloads under Web Protocol version `1`. | One explicit Workspace path with existing parent, startup token/cookie, exact local origin, selected position, expected revision, and operation form or JSON body. | Private local transport only. No remote bind, account/encryption claim, external request, Public Match API/Schema/Root workflow, new Capture CLI option, Player Catalog browser operation, database/cloud/backup, or source integration. | Retain versions/routes/options, no-JavaScript forms, 36 positions, all capture/Statistics/analysis flows, explicit-only execution, autosave/conflicts/Reload, security/privacy, one Console Script, the published `v0.16.0` 63/85 baseline, and the current 69/94 working baseline. | v0.15.0 published bounded local transport complete | Yes |
| Public Session APIs | skat-ai product | Not applicable | `supported` | Stable `skat_ai.api.v1.session` version `1` preserves the first 52 exports and appends Decision Observation, Checkpoint Review Export, and `files`; twelve one-call in-memory operations, strict Command parsing, typed Results, optional complete returned-value provenance, and standalone Schema validation are implemented. Stable `skat_ai.api.v1.session.files` version `1` exposes exact path-free Save/Load Results over strict persistence. | Existing typed Session values or strict JSON-object Command/persistence mappings; caller-supplied file path and expected fingerprint for Save. | No Session Root workflow, automatic analysis after every Command, persisted analysis Result, default path, GUI, platform adapter, cloud synchronization, distributed lock, encryption, or automatic backup. | Retain exact export order/identity, operation/value pairs, observation/review isolation, file Result discrimination, normal statuses, one-call delegation, default provenance omission, strict Schema, 69-Schema parity, and clean-install execution. | v0.14.0 bounded public interface complete | Yes |
| Stable public Python and installed CLI contract | skat-ai product | Not applicable | `supported` | API contract version `1` defines seven Root workflows. Installed, module, and Legacy forms preserve Root parity, the 12-subcommand Session parser, Issue #165 leading private `capture` dispatch, and Issue #179 leading private `corpus` dispatch through one Console Script. Capture and Corpus stay internal and outside `WorkflowV1` and public exports. Issue #189 adds Root flags and modes without adding a workflow or Console Script; Issue #190 uses existing Multi-Step and comparison fields without adding a flag. | Root JSON; explicit Session path/documents; one explicit Match Workspace path for Capture; or one explicit Learning Corpus root for Corpus. | Broader Domain-error migration, license selection, hosted/platform/cloud/encryption integration, and end-to-end field enforcement remain open. | Retain `corpus -> capture -> session -> Root`, exact existing Root/Session parsers and exact Capture/Corpus parsers, seven workflows, 12 Session subcommands, one Console Script, public exports, Legacy seams, import direction, clean installs, 69 Schemas, and 94 scenarios. | v0.14.0 public interface plus v0.15.0 private Capture and v0.16.0 private Corpus transports | Yes |
| Field-level information provenance | skat-ai product | Not applicable | `partially_supported` | Internal contract version `1` defines RFC 6901 paths, immutable ledgers, exact coverage, dependencies, Information Use Context, redaction, serialization, and Confidence separation. All seven workflows have complete non-legacy Root Result ledgers. Public version `1` exposes one explicitly mapped redacted Root Result plus actual artifacts, uses scopes `root_result_without_field_provenance` and `artifact_document`, and requires complete recomputed coverage. | A supported Application invocation with matching retained sidecars; public exposure additionally requires API or CLI opt-in. | Public consumed-input, decision, intermediate-stage, and unredacted attachments are intentionally absent. Broader loading and end-to-end field enforcement remain incomplete; Confidence and specialized source provenance remain separate. | Retain internal enforcement plus public immutable types, seven Result mappings, actual-artifact mapping, redaction and coverage recomputation, strict Schema, default omission, API/CLI parity, privacy rejection, and 77 generated outputs. | v0.13.0 bounded public contract complete; broader v1.0 enforcement open | Yes |
| Interactive Session capture | skat-ai product | Not applicable | `supported` | Issues #150 through #156 provide immutable fixed-three-player Session contracts, deterministic transitions/replay, information-safe Position and canonical Historical export, frozen Checkpoints, Undo/correction/lineage, strict persistence, stable Public API/Provenance, and standalone Schema. Issue #157 adds public file transport, accepted-Log actual-card observation, isolated review Requests, automatic exact Checkpoints, all 12 installed/module/Legacy CLI subcommands, explicit Position/Historical execution, Assistant capture, six examples, and eight scenarios. | Caller-supplied Session identity, three seated Players, Mode/local Player, typed expected-revision Commands, explicit file path, and operation-specific Position/Historical options. | The bounded local capture workflow adds no GUI/browser UI, platform adapter, cloud synchronization, distributed lock, collaborative merge, encryption/key management, automatic backup, default path, natural-language interpretation, or eighth Root workflow. | Retain Live information restrictions, Retrospective exact ownership, replay/readiness, history edits, CAS persistence, observation/review isolation, collection deduplication, privacy/Exit Codes, invocation parity, clean installs, six examples, and the published 85 Session-era scenarios plus current append-only additions. | v0.14.0 published bounded capture complete | Yes |
| Private Session persistence and resume | skat-ai product | Not applicable | `supported` | The immutable version-1 document, strict codec, accepted-Log replay, fingerprints, canonical Checkpoints, recomputed lineage, optimistic `saved`/`unchanged`/`conflict` writes, and same-directory atomic replacement remain authoritative. Issue #157 exposes strict path-free public Save/Load Results and CLI load-operate-CAS-save orchestration without changing the document. | One replay-valid State, optional canonical Checkpoints, explicit existing parent/path, and expected current content fingerprint or null for an expected missing target. | No distributed lock, directory creation, merge/retry, recovery migration, encryption, access control, cloud synchronization, or automatic backup policy. Analysis Results, observations, and review Requests are not persisted. | Retain private contract/codec/file tests plus public file identity, one-call delegation, strict errors, path omission, conflict-without-replacement, and CLI mutation tests. | v0.14.0 bounded persistence scope complete | Yes |
| Live information boundaries | skat-ai product | Not applicable | `partially_supported` | Existing broad enforcement remains, and live Position Application execution validates complete pre-selection decision ledgers and attaches a complete exact Result ledger. Declared Ouvert and both continuation branches authorize only their exact current public hands. Issue #147 can expose the redacted complete `position_result` with recomputed coverage. Accepted 4.4.5 proof hands, other hands, hidden skat, future cards, private worlds, and derived seeds remain unavailable. | Explicit mode, local perspective, verifiable public history, valid declared-Ouvert or continuation public hands, effective seed-free settings, and the exact Application Result. | General position input still trusts supplied context. The public sidecar covers the final Root Result, not every load or decision boundary. | Retain decision-time enforcement, all-leaf accounting, dependency rejection/redaction, Ouvert and continuation exceptions, hidden proof evidence, post-game and private-world leakage, public Result opt-in, determinism, and call counts. | v1.0 | Yes |
| Retrospective information | skat-ai product | Not applicable | `supported` | Post-game mode permits known skat and ended states; every supported historical terminal record reconstructs each actual decision from its decision-time snapshot without future leakage. Internal retained-stage provenance separates decision input and analysis from actual-card assessment and final Outcome Context. Public opt-in can expose the redacted complete Position or Historical Root Result ledger without exposing those internal stages. | Post-game mode and supplied retrospective facts, or a validated historical snapshot, plus an Application provenance bundle for field-level auditing. | Public decision and retrospective-stage ledgers remain internal; Root Result exposure does not make final outcome decision-time evidence. | Retain complete-history versus decision-time separation, 0-30 cardinality, continuation boundaries, actual/future/outcome isolation, redaction, strict public Result coverage, and default-output compatibility. | v1.0 bounded requirement complete | Yes |
| Immediate simulation | skat-ai product | Not applicable | `supported` | Monte Carlo analysis samples unseen cards, evaluates legal responses with deterministic seeds, and fixes every resolved declared-Ouvert or continuation public hand exactly to its owner with a common seeded unknown-world sequence across Ouvert candidates. | Valid position, hand sizes, sample count, seed, policies, and optional public-hand constraints. | It estimates immediate trick outcomes, not complete-contract expected value or perfect-information play. | Retain legality, reproducibility, perspective, point, Null-objective, side-ownership, declared-Ouvert, continuation, and two-public-hand tests. | v1.0 | Yes |
| Evidence-constrained hidden-card inference | skat-ai product | Not applicable | `supported` | `hidden_card_inference.py` derives immutable exact constraints only from the local hand, exact public hands, legitimately known skat, attributed public ownership, and confirmed legal failure to follow the `get_effective_suit` category. Evidence starts after the proving play, persists without retroactive effect, and feeds exact DP compatible-world counts, marginals, uniform labeled-assignment sampling, and uncalibrated concentration labels (`confirmed`, `high >= 0.85`, `medium >= 0.65`, `low`). Immediate candidates share one model and compatible-world sequence; Multi-Step samples one compatible root and may derive later public evidence; Policy Comparison shares one model/root with immutable copies. | Concrete attributed public history or historical replay, valid hand sizes, and any exact public-hand or legitimate skat facts visible at the decision. Current-trick evidence requires a concrete leader/order. | Tactical choices, bidding/declaration behavior, profiles, concessions, timing, future play, final result/value/overbid/settlement, complete post-game hands, and unattributed legacy play are excluded. This is not behavioral, Bayesian, calibrated, learned, broader tactical inference, or proof of the real deal. | Retain Suit/Grand/Null effective-category, chronology, provenance, contradiction, zero-world, exact DP count/marginal, uniform deterministic sampling, confidence-boundary, common-candidate, coherent-root, shared-policy-root, later-evidence, historical leakage, strict-schema, and privacy tests. | v1.0 bounded requirement complete | Yes |
| Bounded search contracts | skat-ai product | Not applicable | `partially_supported` | Version-1 information, exact-state, transition, budget, utility, aggregate-result, privacy, and strict schema contracts are implemented. `perfect_information_minimax_v1` solves one exact late Suit, Grand, or normal non-overbid Null world. `compatible_world_minimax_v1` evaluates a frozen compatible-world sequence with global nodes, per-world depth/cache, common-prefix stopping, and equal duplicate-draw weight. Explicit flat live routing, opt-in Multi-Step/Policy Comparison, flat post-game comparison with an independent Immediate baseline, Historical Search Review, and bounded-Search dataset evaluation are integrated. Historical output reconciles decision/status/coverage/agreement/quality/performance metrics; evaluation defaults to validation/test, supports one stable global decision cap, and preserves zero-decision records. `interactive_v1`, `historical_review_v1`, and `evaluation_v1` are immutable work profiles. Independent exhaustive fixtures show strict Search improvement over Immediate in Suit, Grand, and Null, while 32/64/128-draw fixtures provide bounded convergence evidence. A deterministic Suit/Grand/Null corpus records reproducible structural work and local elapsed measurements. | A safe live or flat retrospective local view, reconstructed historical snapshot, or validated training dataset; an explicit non-boolean integer Search seed; and an explicit flat budget or named immutable historical/evaluation profile. Suit and Grand require bid and matadors; Null requires a bid no greater than its fixed value. | Search remains limited to late positions; overbid Null replacement selection remains unsupported. Compatible-world aggregation is determinization-based and subject to strategy fusion, so exhaustive aggregation is not an optimal imperfect-information policy proof. Sampled quality evidence is not calibrated, and benchmark timings provide no latency guarantee. Direct exact aborts expose zero completed candidates; compatible incomplete work can recommend only from a qualified exact common prefix. Existing omitted-method Immediate behavior is unchanged. Exact hands, out-of-play cards, assignments, states, hashes, derived seeds, per-world values, caches, branches, and principal variations are not serialized. The broader stronger-solver v1.0 gate remains open. | Retain exact-state/transition invariants, terminal-input precedence, late-game limits, Suit/Grand/all Null variants, exact and sampled independent references, 32/64/128 convergence, duplicate weighting, all perspectives/root seats, budget boundaries, prefix thresholds, deterministic seed domains, information safety, profile immutability, flat/historical/evaluation comparison arithmetic, zero-decision preservation, strict schemas, generated examples, benchmark reproducibility, and no-latency/no-policy-proof wording. | v0.10.0 bounded retrospective/evaluation evidence; v1.0 broader stronger-solver completion | Yes |
| Information-set Search | skat-ai product | Not applicable | `partially_supported` | Issues #187 and #188 define and execute the private three-Trick controlled-Player selected-world best response. Issue #189 adds strict flat `information_set_search` with exactly nine settings, safe aggregate Results, no Live baseline or fallback, descriptive same-selection PIMC and independently seeded Immediate retrospective comparison, separate Historical Review and Training Dataset evaluation, retained-stage Provenance, CLI, four Schemas, one example, and four scenarios. Issue #190 adds strict Multi-Step and Policy Comparison version `1`: a domain-separated child seed and fresh public-state Search at each local decision, private independent coherent execution, no Search World or controlled-Policy reuse, no fallback, safe nested Decisions, 16-field diagnostics, append-once-last ordering, shared-root independent path copies, stopped-row ineligibility, existing ranking, and retained-Result complete Provenance. Existing `auto` remains unchanged. | A safe eligible Position, Historical decision Snapshot, Training Dataset-v1 Record, or supported live Multi-Step local decision; explicit deterministic fixed left/right Policies; an explicit Search seed; and a valid bounded Budget or mapped existing work profile. | This is not a cross-decision global Policy, equilibrium, global optimality, complete-contract solving, calibrated probability, complete Strategy-Fusion correction, or a latency guarantee. Exact Worlds, hidden hands, Observations, controlled Policy tables, caches, and derived seeds remain private. Match Capture, Match Analysis Reports, Strategy Teacher, Replay Coaching classification, and performance integration remain open. | Retain equal-Observation common action, ordered selected-world reuse, duplicate weight, fixed Policies, exact counters, no-fallback semantics, same-selection comparison, actual-Card cutoff, Historical/Dataset ordering, per-decision seed/fresh-Search isolation, safe Decision/diagnostic shapes, append-once-last ordering, eligibility/ranking, privacy, complete Provenance, Schema, CLI, example, and scenario coverage. | v1.0 broader solver gate remains open; Issue #190 Multi-Step/Policy Comparison integration complete | Yes |
| Multi-step simulation | skat-ai product | Not applicable | `partially_supported` | Sequential local actions and selected opponent-turn preparations are serialized against one private immutable root ownership assignment per path; preparation and completion share the world, cards are removed only from their owner, the hypothetical skat stays fixed, one or two exact public hands remain reconciled, and confirmed structural evidence constrains the sampled root. Strict `information_set_search` now performs fresh public-state Search per local decision and stops without fallback when no recommendation exists. | Valid position, step count, hand sizes, seed, policies, optional public-hand constraints, and available attributed public evidence; Information-set Search additionally requires its exact settings and effective fixed Policies. | Some valid phases still stop as `unsupported_turn_phase`; the sampled root is one compatible hypothetical execution world, not exhaustive search or proof of the real deal. Information-set Search adds no cross-decision global Policy. | Retain every canonical phase, ownership/removal, fixed-skat, no-resampling, inference constraints, later visible evidence, all public-hand sources and coexistence, privacy, deterministic-stream, per-decision Search isolation, strict stop, and state/point continuity tests. | v1.0 | Yes |
| Card recommendations | skat-ai product | Not applicable | `supported` | Immediate expected value remains the omitted default. Explicit flat live or retrospective methods add strict `bounded_search` and Search-first `auto` using `compatible_world_minimax_v1`; qualified partial/timeout Search recommendations remain usable, and auto fallback is explicit. | A current local decision and Immediate settings; Search methods additionally require a separate seed and complete requested budget. | Immediate remains a bounded one-trick heuristic. Compatible-world Search is late-game, determinization-based, subject to strategy fusion, and not proof of an optimal imperfect-information policy. | Retain legal-candidate, perspective, method routing, strict/fallback, independent retrospective baseline, report separation, deterministic-seed, tie, objective, privacy, schema, example, and CLI tests. | v1.0 | Yes |
| Opponent policies | skat-ai product | Not applicable | `supported` | Global, left/right, preset, CLI, lead, response, and defender heuristics affect immediate and multi-step paths; Policy Comparison samples one compatible root and gives equal independent immutable copies to all policy paths. Local card-selection policies receive public decision-time state rather than private root ownership. | Policy settings, concrete side/perspective, and public ownership where applicable. | Policies remain simplified rule-based behavior; exact structural inference adds no behavioral/Bayesian tactic, policy, or optimality claim. | Retain precedence, controlled effects, equal shared-root setup, independent path evolution, identical public constraints, decision-policy privacy, and no-new-policy tests. | v1.0 | Yes |
| Player and opponent profiles | skat-ai product | Not applicable | `partially_supported` | Supplied, externally normalized, or exactly historically aggregated profile fields support a versioned explainable rule-based derivation; opt-in manual profiles, explicitly bound live records, and time-safe automatically matched historical records can select bounded side-specific presets. A separate known-opponent rolling as-of workflow compares actionable acting-player policy imitation with a fixed baseline. | Supplied or aggregated profile statistics, exact stable identities, required historical game starts, disjoint source/evaluation partition names with player overlap, and effective profile-preset opt-in where profiles are applied. | Profiles are not learned; behavioral match rates do not measure strategic or recommendation quality, and unseen-player profile evaluation is unsupported. | Retain field validation, exact binding/matching, temporal safety, partition-policy compatibility, derivation, side remapping, policy precedence, neutral behavior, preferred candidates, paired metrics, and workflow-isolation tests. | v1.0 | Yes |
| Profile confidence | skat-ai product | Not applicable | `partially_supported` | Version 1 derives separate overall, declarer, and defender exact or estimated evidence, applies fixed heuristic bands, gates every signal by its denominator scope, and permits only actionable live or time-safe historical external presets to affect analysis. | Total games and available exact role counts or normalized role rates plus signal values. | Bands are not calibrated uncertainty; application is bounded rule-based policy selection, not prediction or learned inference. | Retain every boundary, evidence precedence, contradiction, missing-data, low-confidence, signal, conflict, live/historical application, and output-reconciliation test. | v1.0 | Yes |
| Post-game decision review | skat-ai product | Not applicable | `supported` | One supplied actual local card or each decision-time historical snapshot is compared with an independently executed Immediate recommendation. Explicit flat Search additionally compares the actual card and Immediate card against the same Search aggregate. Declared Ouvert and both timed continuation kinds reuse exact authorized public-hand constraints without inferring proof or settlement. | A retrospective decision position or safe historical snapshot, actual card, and enough Immediate/Search context. | Immediate remains a one-trick heuristic; Search remains bounded late-game determinization, and aggregate comparison is not policy proof. | Retain Suit, Grand, Null, declarer, defender, declared-Ouvert, both continuation members, independent-baseline ordering, tie equivalence, unavailable, legality, strict schema, and historical aggregation tests. | v1.0 | Yes |
| Complete-game retrospective analysis | skat-ai product | Not applicable | `partially_supported` | Every supported historical game can produce and evaluate one ordered information-safe pre-play state per actual card. Historical Search Review runs Search and independent Immediate before introducing the observed card and reconciles decision, status, coverage, agreement, quality, performance, and bounded breakdown summaries. Public Replay Coaching version 1 reuses that retained pass, separates decision-time evidence from retrospective attachment, prioritizes Key Decisions and Turning Points, aggregates two-occurrence one-game patterns by player/role/phase/contract, builds deterministic recommendations, and emits privacy-safe context, outcome isolation, coverage, scope summaries, and canonical limitations through a strict schema and CLI. Declared Ouvert and either continuation preserve their exact visibility boundaries. | Complete historical record, validated replay result, explicit Search seed and immutable profile for Search review/coaching, approved Immediate samples/seed, or selected dataset partitions for evaluation. | Early decisions can be outside the late-game profile; event-choice quality, shortening-choice quality, later end reasons, complete-contract optimization, tactical motifs, cross-game analysis, ratings, and causal attribution remain absent. | Retain variable/zero decisions, event-prefix parity, Ouvert/continuation ownership, stable non-serialized seed derivation, profile budgets, aggregate arithmetic, strict schemas and CLI, coaching-contract/report validation, pattern/recommendation ordering and deduplication, recursive privacy, actual/future/final-outcome isolation, outcome allowlists, scope reconciliation, Null wording, one-pass call counts, conditional output, and unchanged existing review tests. | v1.0 | Yes |
| Historical-game representation | skat-ai product | Not applicable | `partially_supported` | Version 1 preserves stable IDs, optional `played_at`, fixed seats, complete deal, declaration, skat handling, all six terminal shortenings, including the valid-proof-only party-wide Claim, and at most one timed continuation before normal completion or one terminal shortening. Public hands are reconciled at both continuation and final boundaries. | Complete `historical_game_input` ending with a supported reason; optional one-event `game_events`; full deal and exact supplied play; matching top-level terminal object where shortened; `played_at` where profile/statistics workflows require it. | Flat Position Claim input, Session/Match/Corpus Claim entry, other end reasons, auction events, disputes, multiple non-terminal events, arbitrary event streams, and terminal-event prediction are absent. | Retain normal serialization/count compatibility, Ouvert and continuation boundaries, ownership/order/follow, Claim proof/adjudication/privacy, cardinality, statistics/rolling parity, round-trip, CLI, schema, and settlement-parity tests. | v1.0 | Yes |
| Training-data representation | skat-ai product | Not applicable | `partially_supported` | A separate version-1 dataset workflow validates provenance, explicit train/validation/test partitions, optional known-opponent or unseen-player policy, deterministic exact-player overlap audits, and declared unseen-player disjointness; it derives information-safe actual-card samples. Public preparation version `1` adds unpartitioned source Records, explicit integer weights, split-safe facts, deterministic fingerprints and seed helpers, complete/unavailable Plan contracts, exact Record-count arithmetic, and lossless materialization into the unchanged dataset input. Mode dispatch is fixed: `known_opponent` uses `temporal_known_opponent_v1`, and `unseen_player` uses `component_balanced_unseen_player_v1`. The strict root-selected JSON/schema/CLI workflow returns a reusable dataset and audit for complete Plans or explicit null values with no partial Plan when unavailable. Bounded-Search evaluation remains separate. | Supported historical games, dataset/record/source identities, provenance, feature version, target, explicit weights or partition metadata, optional policy intent, deterministic base seeds, one matching mode, and an explicit Search seed only for separate bounded evaluation. | Later historical end reasons, additional preparation algorithms, algorithm overrides, fallback or partial Plans, default weights, CLI overrides, global unseen-player optimization, ratio guarantees, Sample- or Player-count balancing, component splitting, unseen-player model evaluation, calibrated Search quality, model training, and automatic evaluation are unsupported. | Retain schema/runtime, variable/zero counts, exact identities, fingerprints/seeds, Plan status/reason/mode validation, temporal and unseen-player generator objectives/ties/order/isolation/execution bounds, independent graph/local-optimum checks, exact arithmetic, chronology/coverage/disjointness, lossless materialization, card-free Plan/CLI output, nested-dataset card preservation, policy resolution, provenance, duplicate/leakage, feature safety, CLI isolation, all three examples, complete/unavailable outputs, and ordinary conversion compatibility tests. | v1.0 | Yes |
| Dataset partition policies and overlap audits | skat-ai product | Not applicable | `supported` | Optional version-1 `known_opponent` and `unseen_player` metadata preserves unspecified legacy intent; deterministic audits report exact stable-player membership, pairwise and three-way overlap, directed known-opponent coverage, and strict declared unseen-player compliance. The separate public preparation workflow generates temporal Known-opponent or component-balanced Player-disjoint unseen-player assignments and reuses the existing audit. | Stable case-sensitive player IDs, explicit dataset partitions and optional declared policy intent, or one public unpartitioned preparation request with explicit weights and mode. | General repartitioning beyond the two fixed algorithms, global optimization, guaranteed ratios, Sample- or Player-count balancing, component splitting, fallback, and unseen-player generalization evaluation are unsupported; rolling policy evaluation intentionally remains a known-opponent workflow. | Retain policy resolution, exact membership, overlap, directed coverage, strict unseen-player rejection, report-only audit, mode-derived generator disjointness, schemas, CLI isolation, and compatibility tests. | v1.0 bounded requirement complete | Yes |
| External opponent-statistics representation | skat-ai product | Not applicable | `supported` | A separate version-1 workflow preserves stable identity and external or historical provenance, validates eight percentage-point values and optional exact counts, emits normalized rates including `defender_rate`, and includes the unchanged explainable profile derivation; exact live bindings and strict time-safe historical participant matches reuse the records. Issue #173 separately fingerprints and retains exact Match-bound records in private derived Corpus history. | Total games, all eight percentages, source identity, RFC 3339 capture time, optional exact evidence, explicit live side bindings or historical game `played_at`, and profile opt-in. | External records may omit exact counts; capture time is not comparable in live analysis, and the public workflow has no multiple-capture history. The private selector is Current-Snapshot-only and non-persisted. | Retain schema/runtime, denominator, provenance, consistency, no-invented-count, exact-count, scoped-confidence, binding/matching, temporal ordering, precedence, CLI, examples, output, private history isolation, and no Profile derivation by Issue #173. | v1.0 | Yes |
| Historical player statistics | skat-ai product | Not applicable | `supported` | Version 1 deterministically aggregates one game per selected normal-completion or six supported shortened terminal records into exact role, settlement-result, Hand, and contract counts plus the existing eight percentages, preserves canonical partition/cutoff and policy provenance, and exports a reusable statistics input. | A validated `training_dataset_input` of supported games, stable case-sensitive player IDs, explicit partitions, and `played_at` on every partition-selected game. | Policy intent and play/sample counts do not alter game weight; aggregation does not add event-specific signals, infer policy, merge sources, maintain multiple captures, evaluate quality, apply profiles, or learn behavior. | Retain policy compatibility, partition/cutoff, timestamp, identity/label, settlement/overbid, shortened outcome, zero-play weighting, exact invariants, provenance, derivation, export/loader, CLI, schema, example, and isolation tests. | v1.0 | Yes |
| Rolling opponent-policy evaluation | skat-ai product | Not applicable | `supported` | A dedicated known-opponent workflow builds strict game-start as-of profiles from every supported source reason, evaluates each actual zero-through-30 target card against ordered policy-equivalent preferred candidates and exact choices, retains zero-decision targets, and reports baseline, actionable-only paired, participant coverage, and bounded breakdown metrics. | Timestamped supported source and target games with stable player overlap, disjoint partition names, and unspecified or `known_opponent` dataset intent. | Behavioral matching does not predict terminal events or measure strategic strength, recommendation quality, optimal play, unseen-player generalization, or statistical significance. | Retain temporal/target exclusion, identity and seat remapping, prefix parity, event isolation, participant coverage, baseline, preferred/exact matching, actionable pairing, zero decisions, reconciliation, schema, CLI, and isolation tests. | v1.0 bounded requirement complete | Yes |
| Learned opponent models | skat-ai product | Not applicable | `not_supported` | No learned model exists; current profiles and policies are deterministic and rule-based. | Approved historical features, model artifact, versioning, and inference contract. | Training, evaluation, deployment, fallback, and explainability details are not designed. | Define separate post-v1.0 acceptance criteria before implementation. | Post-v1.0 | No |
| Machine-learning model training | skat-ai product | Not applicable | `not_supported` | No training pipeline exists. | Approved dataset, target, evaluation protocol, reproducibility, and artifact policy. | Historical training-data representation does not itself authorize model training. | Define separate post-v1.0 card-decision model acceptance criteria before implementation. | Post-v1.0 | No |
| Generated-output validation | skat-ai product | Not applicable | `supported` | The current unreleased matrix generates, semantically checks, and schema-validates 94 deterministic scenarios. Issue #186 preserves the published `v0.16.0` first 85 and appends three Historical Claim scenarios; Issue #189 appends four Information-set Search scenarios; Issue #190 appends Multi-Step and Policy Comparison scenarios. Historical published `v0.13.0`, `v0.12.0`, `v0.11.0`, and `v0.10.0` counts remain 77, 70, 64, and 59. | Repository examples/fixtures, 69 schemas, and deterministic Root/Session CLI settings. | The matrix is representative rather than exhaustive; append-only additions do not rewrite historical published Release evidence. | Keep active and published counts explicit; retain prior order and add deterministic coverage for each stable user-facing branch. | v1.0 | Yes |
| Release and regression checks | skat-ai product | Not applicable | `supported` | `scripts/check.ps1` and CI run Ruff, 69-Schema parity, Root/Session examples, 94 scenarios, Wheel/sdist inspection, clean API/Root/Session/Capture/Corpus CLI and browser smoke, and pytest on Python 3.13. | Development dependencies and supported platform tooling. | Passing checks proves tested behavior, not complete ISkO/SkWO compliance or Package-index publication; GitHub Releases is the authoritative publication record. | Require clean local/CI checks, exact Capture/Corpus resources, one Console Script, installed/module/Legacy/API parity, and human-controlled publication. | v1.0 | Yes |

Issue #191 extends the private Learning Corpus/Strategy Teacher, Dataset-v2,
Match analysis/export, local Match browser, and Information-set Search rows with
the bounded one-Decision Match/Report/Teacher/Dataset/Corpus path. The exact
source, safe Result/comparison, effective fixed policies, Teacher privacy and
identity, Dataset joins, Summary counts, browser diagnostics, strict no-fallback
execution, and existing local upload/preparation/download behavior have focused
validation. Match Historical Information-set execution, Replay Coaching
classification, and performance evidence remain open. See
[Match Information-set Search and Strategy Teacher Evidence](match_information_set_search_and_strategy_teacher.md).

## Interpretations and unresolved rule questions

* For ISkO 3.6.2, the International Skat Court decision collection section
  3.6.2, inquiries 1-3, permits the declarer to select an eligible favorable Suit
  or Grand replacement. `skat-ai` records an external selection and does not
  optimize across alternatives whose contract-specific matadors are unknown.
* ISkO 4.4.4-4.4.6 defines specific open-card shortcuts. It does not define a
  general solver-backed claim protocol. Both 4.4.4 branches, bounded exact 4.4.5
  adjudication, bounded non-adjudicating 4.1.6 continuation, and bounded 4.4.6
  opposing-party assignment with jack-only theoretical exclusion are supported.
  One continuation followed by one supported terminal shortening is implemented
  by delegating to the existing terminal semantics. Multiple non-terminal
  events, arbitrary event streams, simultaneous throws, unlimited proof,
  generalized non-jack theoretical solving, and specific future-Trick Claims are
  `not_supported_v1`. Issue #183 implements private structured party-wide
  all-remaining-Tricks Claim and exact-proof contracts plus untraversed exact-
  state preparation. Issue #184 implements bounded exhaustive exact AND/OR proof
  execution. Issue #185 adds private immutable adjudication Facts/Result,
  valid-proof-only exact point and Trick assignment, preexisting-winner
  preservation, Suit/Grand/Null level semantics, and composition through existing
  Final Settlement; invalid or unavailable proof creates no outcome.
  Issue #186 integrates the approved bounded Claim only through Historical Game
  input with valid-only acceptance, strict diagnostic public output, Provenance,
  CLI, Review/Coaching, Dataset, list, and statistics compatibility. Flat
  `game_shortening`, Session, Match Capture, and Corpus entry remain absent.
* Ten cards per player and three cards per trick imply ten normal tricks, while
  ISkO 4.4.1 says games are generally played to the end. The numbered rules do
  not provide one standalone `normal_completion` data definition; the v1.0
  complete-history contract must state its software evidence explicitly.
* SkWO 6.3.1 standings use total performance points, more own wins, fewer own
  losses, then lot. The engine represents an unresolved lot explicitly or
  records an externally executed result; it does not perform a random lot.
* The historical-list contract treats exactly 36 positions as its
  version-1 product boundary. Passed deals advance rotation but contribute zero;
  aggregation version `1` now builds cumulative totals, all 36 progression
  snapshots, and final standings from those facts. Comparison version `1` uses
  one fixed reference for independent completed lists, preserves unresolved lots,
  and adds no progression matching or series aggregation. Issue #130 exposes
  those retained contracts through strict root-selected JSON, schemas, concise
  CLI output, examples, and generated-output validation.
* The Match tournament-format identity `euroskat_36_standard_v1` is a named
  product capture contract, not an implementation of EuroSkat ranking,
  qualification, prize, fee, bonus, integration, or broader tournament
  management rules. Match metadata remains separate from fixed-list aggregation.
* SkWO defines list, event, signature, correction, submission, and retention
  duties, but the November 2022 PDF does not prescribe an official digital file
  format. Any such format needs a named external authority and conformance
  source.

See [v1.0 scope](v1_scope.md) for product classifications and completion gates.
