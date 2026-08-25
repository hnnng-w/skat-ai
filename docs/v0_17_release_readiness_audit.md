# v0.17.0 scope and release-readiness audit

## Audit scope

This document is the authoritative functional-scope and release-readiness audit
for `v0.17.0`. It reconciles Issues #182 through #196 against the current
repository without changing product behavior, public contracts, Package
metadata, Schemas, examples, generated-output definitions, benchmark values, or
the Changelog.

The audit distinguishes functional completion from Release preparation and
publication. It does not declare `v1.0.0` ready and does not broaden any bounded
Claim, Search, Coaching, Tactical, or Corpus claim.

## Authoritative source hierarchy

Conflicts are resolved in this order:

1. The official November 2022 ISkO/SkWO publication governs game and competition
   rules. Approved repository product decisions govern skat-ai-specific scope.
2. Current Package metadata, executable source constants and contracts, and
   canonical persisted or serialized contract definitions govern implemented
   product behavior.
3. Authoritative Schemas and their byte-identical Package Resources, example and
   generated-scenario registries, distribution validation, and benchmark corpus
   govern the corresponding bounded artifacts and counts.
4. Focused regression tests, benchmark tests, and the complete repository check
   provide executable evidence for those contracts.
5. Current-state documentation explains those facts. Historical Changelog and
   Release-baseline statements remain point-in-time evidence and are not
   rewritten with current working counts.

GitHub Releases is authoritative for publication status. No Package-index or
PyPI publication is claimed.

## Release identity

The Release identity is frozen as:

```text
Theme:
    Rules, Search, Coaching, and performance closure

Title:
    v0.17.0 — Rules, Search, Coaching, and performance closure
```

Issue #197 itself did not change the Package version, create a tag, publish a
Release, or add final Release notes. Issue #198 subsequently prepared the
Package and Release candidate without publication. The maintainer later
published the Release on 2026-08-25 at `8187fbe`, and Issue #199 synchronizes the
post-publication documentation without product functionality.

## Published Release state

The current published stable and latest stable GitHub Release is:

```text
Release:
    v0.17.0

Publication commit:
    8187fbe684559f9c0c2ba444be1bf33950359ad2 (8187fbe)

Publication date:
    2026-08-25

Release theme:
    Rules, Search, Coaching, and performance closure
```

That published Package requires Python `>=3.13`, retains Public API contract
version `1`, exactly seven Root workflows, and one Console Script. Its baseline
has Matrix version `3` with 61 cases, 71 authoritative and packaged Schemas, six
Session examples, 98 generated outputs, ten private Corpus prepared downloads,
and 7,479 passing pytest tests in 921.96s.

The historical published `v0.16.0 — Learning-ready behavior and communication
data` baseline remains at commit `91b1360`, published on 2026-08-18. It has 63
authoritative and packaged Schemas, six Session examples, 85 generated outputs,
and 6,925 passing pytest tests in 1083.48s. These historical facts are not
replaced by the `v0.17.0` counts.

## Historical prepared Release-candidate state

Issue #198 changed only Package metadata, current Package-version expectations,
the Changelog, and Release-candidate documentation. At completion of Issue #198,
the resulting point-in-time state was:

```text
Package baseline:
    0.17.0

Release candidate:
    prepared

Published stable Release:
    v0.16.0 at 91b1360

v0.17.0 publication:
    pending

v1.0.0:
    not ready
```

That historical candidate retained Python `>=3.13`, Public API contract version `1`,
seven Root workflows, one Console Script, Matrix version `3` with 61 cases, 71
authoritative and packaged Schemas, six Session examples, 98 generated outputs,
ten private Corpus downloads, and 7,479 passing pytest tests.

## Issue #197 audited working baseline

The working baseline audited by Issue #197 before Release preparation was:

| Dimension | Current value |
| --- | ---: |
| Package version | `0.16.0` |
| Python requirement | `>=3.13` |
| Public API contract | `1` |
| Root workflows | 7 |
| Console Scripts | 1 |
| Settlement Normative Matrix | version `3` |
| Canonical Settlement cases | 61 |
| Authoritative Schemas | 71 |
| Packaged Schema Resources | 71 |
| Session examples | 6 |
| Generated outputs | 98 |
| Corpus private prepared downloads | 10 |
| Pytest tests | 7,479 passing |

The Matrix retains exact canonical Case-ID ordering. Authoritative and packaged
Schema filenames and bytes match. Issue #197 adds no Schema, example, generated
scenario, benchmark case, route, or public surface.

## Functional Issue inventory

Issues #182 through #196 are the exact functional milestone history.

### Claims and Settlement

| Issue | Functional scope |
| --- | --- |
| #182 | Bounded v1 Claim and Settlement product-decision audit. |
| #183 | Structured Claim, Evidence, Exact State, Request, assignment, line, and Result contracts. |
| #184 | Bounded exhaustive party-wide Claim Proof execution. |
| #185 | Private Claim adjudication and existing Final Settlement composition. |
| #186 | Historical Game Claim workflow, Matrix version `3`, Schemas, public output, and downstream integration. |

### Information-set Search and performance

| Issue | Functional scope |
| --- | --- |
| #187 | Contracts, World State, Observations, fixed Policies, Budget, Request, Preparation, and Result. |
| #188 | Selected-world Information-set best-response executor. |
| #189 | Strict flat routing, safe output, Post-game comparison, Historical Review, and Dataset evaluation. |
| #190 | Multi-Step and Policy Comparison integration. |
| #191 | One-Decision Match Capture and Strategy Teacher integration. |
| #192 | Information-set Replay Coaching and Match Historical integration. |
| #193 | Deterministic functional/structural benchmark corpus and local timing reference. |

### Tactical evidence and Cross-game Coaching

| Issue | Functional scope |
| --- | --- |
| #194 | Historical Tactical Motif Evidence. |
| #195 | Current-Snapshot Tactical Evidence and descriptive cross-game summaries. |
| #196 | Conservative deterministic Tactical Cross-game Coaching. |

## Claim and Settlement audit

The Settlement Normative Matrix remains version `3` with exactly 61 canonical
cases in the frozen order. It approves one bounded party-wide all-remaining-
Tricks Claim. The public entry is Historical Game input only; there is no flat
`GameShortening` member and no Position, Session, Match Capture, or Corpus Claim
entry.

Preparation supports at most five unresolved Tricks. Bounded exhaustive exact
AND/OR Proof gives the claiming party existential choices and the opposing party
universal choices. A valid Proof produces exact assignment, adjudication, and
the existing Final Settlement composition. Invalid and unavailable Proofs
produce no terminal outcome, winner, assignment, or Settlement.

Specific-Trick Claims, generalized correction and non-jack exclusion, free-text
Claims, unlimited proof, arbitrary event streams, and the other documented
boundaries remain durable `not_supported_v1` exclusions. General Claim and
official Settlement completeness are not claimed. The implemented slice is
`complete_for_v0_17`.

## Information-set Search audit

The bounded executor controls exactly Player `me`; `left` and `right` remain
deterministic fixed-policy actors. Equal controlled Observations use one common
action. Preparation supports one through three unresolved Tricks, exact or
sampled Compatible-world selection, and sampled duplicate draws with retained
weight. Results distinguish `complete`, `partial`, `timeout`, and `unavailable`.

Strict integration exists for flat Live and Post-game routing, same-selection
PIMC diagnostics, independently seeded Immediate diagnostics, Historical Review,
Training Dataset evaluation, Multi-Step, Policy Comparison, one-Decision Match
Capture, method-bound Strategy Teacher Evidence, and Information-set Replay
Coaching. Multi-Step performs fresh public-state Search at each local Decision;
Policy Comparison appends the method once and last. A missing recommendation
stops without fallback.

There is no Information-set-aware `auto`. Existing `auto` remains compatible-
world PIMC followed by its existing Immediate fallback. The bounded executor is
not a global cross-decision Policy, joint Defender optimization, equilibrium,
Nash strategy, calibrated probability model, globally optimal Skat solver,
complete Strategy-Fusion correction, or complete-contract solver.

## Workflow-integration audit

Issues #189 through #192 carry the same bounded Search contract through Root
Position and Historical workflows, Training Dataset evaluation, Multi-Step,
Policy Comparison, private Match Decision and Historical analysis, exact Report-
source transfer, Current-Snapshot Strategy Teacher Evidence, Dataset-v2 joins,
Corpus summaries, and separate Information-set Replay Coaching. They add no
eighth Root workflow, second Console Script, new public namespace, or
Information-set `auto` route.

Existing Root callers remain compatible when optional fields are omitted.
Historical Match Reports remain ephemeral and ineligible for Strategy Teacher
source transfer.

## Coaching audit

The following remain separate evidence and report families:

* bounded Replay Coaching;
* Information-set Replay Coaching;
* Historical Tactical Motif Review;
* Current-Snapshot Tactical Motif Evidence;
* Tactical Cross-game Summary; and
* Tactical Cross-game Coaching.

Existing bounded Replay Coaching is unchanged. Information-set Coaching reuses
one retained Review, accepts complete Candidate Evidence as primary evidence,
and treats PIMC and Immediate as diagnostics only, never fallbacks.

Tactical Cross-game Coaching requires exact Tactical/Strategy Teacher joins and
retains one Assessment per exact Teacher Report. Semantic duplicate Reports
count once per Decision consensus. Actionable Focus requires unanimous distinct-
semantic complete-Search evidence, at least two qualifying Decisions in at least
two Games, and is capped at five deterministic fixed-Guidance Focus Areas per
Player. Immediate, partial, timeout, unavailable, not-assessable, and mixed
evidence remains descriptive.

## Tactical Evidence audit

Historical Tactical Motifs use the frozen 16-type structural taxonomy and exact
decision-time, after-play, and completed-Trick timing. Current-Snapshot Corpus
preparation represents every observed Decision with safe Evidence or an explicit
skip and handles partial Matches and incomplete final Tricks without hidden
completion.

Motifs and summaries are structural observations and exact descriptive Counts.
They do not establish correctness, tactical truth, actual-card ground truth,
Player traits, strengths or weaknesses, Ratings, intent, signaling,
communication, causality, or statistical significance.

## Learning Corpus artifact audit

The private browser prepares three separate process-local families: the existing
seven artifacts, two Tactical artifacts, and one Tactical Coaching artifact.
All three publish atomically only after exact same-generation source
reconciliation and invalidate jointly. Stale preparation cannot replace or erase
newer artifacts. Downloading does not rebuild analysis, mutate the Corpus, or
write a server file.

The ordinary dashboard remains minimized. Exactly ten private downloads require
the established loopback authentication. Derived artifacts are not persisted;
there is no Public Corpus or Dataset-v2 API or Schema. Human, Strategy Teacher,
Tactical, and Coaching evidence remains separate, and Learning Dataset version
`2` is unchanged.

## Performance-evidence audit

Performance closure for `v0.17.0` consists exactly of one strict eight-case
synthetic Information-set benchmark corpus; frozen functional and structural-
work signatures; same-selection PIMC and independent Immediate diagnostics;
Strategy-Fusion and sampled duplicate-weight characterization; and one
reproducible local Python 3.13 timing reference. Tests validate timing-output
shape, not elapsed time.

Cross-machine millisecond guarantees, production SLA, P95 or P99 promises,
dedicated production Information-set Budget profiles, complete-contract
performance, and wider-than-three-Trick Search are outside the `v0.17.0` Release
contract. Their absence is not a Release blocker.

## Privacy and information-safety audit

Live analysis receives only decision-time-visible facts; Retrospective actual
Cards and outcome context are attached only after decision analysis. Selected
Search Worlds, complete controlled Policies, exact opponent ownership, caches,
and derived seeds remain private. Match and Corpus dashboards expose minimized
facts rather than complete private source documents.

Actual Cards are observed behavior, not ground truth. Human Commentary remains
uninterpreted, Response Links remain noncausal, Strategy Teachers remain method-
bound, Tactical Motifs remain structural, and Cross-game Focus remains a bounded
review aid rather than a Player trait. No encryption, secure-storage, cloud,
remote-access, backup, or authenticated-authorship claim is introduced.

## Public API and compatibility audit

Public API contract version `1`, seven Root workflows, Python `>=3.13`, and the
sole `skat-ai = skat_ai.cli:main` Console Script remain unchanged. There is no
new public namespace or eighth workflow. Installed, module, and Legacy CLI forms
remain supported.

Session contracts and persistence remain version `1`. Match Workspace
persistence is unchanged. Corpus persistence remains private version `1`.
Existing optional-field omission preserves Root caller compatibility.

## Schema, example, and scenario audit

The current repository has 71 authoritative Schemas and 71 byte-identical
Packaged Schema Resources. Six Session examples and all Root examples validate.
The append-only generated-output matrix has 98 scenarios in stable order. Issue
#197 adds no Schema, example, scenario, generated output, or order change.

## Packaging and distribution audit

The unchanged Setuptools configuration builds one Wheel and one sdist. At the
time of the Issue #197 audit, clean-install validation checked Package `0.16.0`,
Python `>=3.13`, API execution,
installed/module CLI parity, the sole Console Script, all 71 packaged Schemas,
Session files and commands, private Capture and Corpus transports, all ten Corpus
downloads, and the absence of a second command or GUI Script. Distribution
validation publishes nothing. Issue #198 updates only the Package-version
expectation to `0.17.0` and leaves those other checks unchanged.

## Current limitations

The bounded Claim is Historical-only. Information-set Search is limited to the
selected Compatible-world sequence, controlled Player `me`, fixed opponent
Policies, and three unresolved Tricks. `auto` is not Information-set-aware.
Tactical quality outside retained complete-Search Teacher evidence, Player
Ratings, Commentary interpretation, communication and signaling inference,
derived-artifact persistence, remote/cloud deployment, complete official
Settlement coverage, complete-contract Search, and broader field-level
Provenance remain incomplete.

These limitations are explicit product boundaries; they do not contradict the
bounded `v0.17.0` functional contract.

## v0.17.0 Release blockers

No material functional, compatibility, validation, packaging, privacy, or
documentation blocker remains for Release preparation. The functional milestone
is complete through Issue #196.

## Non-blocking deferred work

The following require dedicated v1 audit or later product decisions rather than
blocking `v0.17.0`:

* final API and Schema freeze;
* deprecation and migration policy review;
* broader field-level Provenance enforcement;
* remaining official-rule and Settlement audit;
* approved Player-Rating boundary;
* production performance acceptance criteria and cross-machine latency policy;
* final v1 example and output matrix;
* final installation and packaging audit; and
* complete v1 scope and traceability review.

General Claim input, a complete-contract solver, joint-player equilibrium,
Information-set-aware `auto`, Commentary interpretation, communication or
signaling inference, derived-artifact persistence, and remote/cloud deployment
are likewise non-blocking bounded limitations for this Release.

## Release-note structure for Issue #198

Issue #198 must use this exact Changelog and GitHub Release structure:

```text
Highlights

Bounded Claim and Settlement completion

Information-set Search and selected-world Strategy consistency

Decision-analysis and simulation workflow integration

Information-set Replay Coaching

Tactical Motif Evidence

Learning Corpus Tactical Evidence and Cross-game Coaching

Performance, determinism, information safety, and compatibility

Validation

Limitations

Upgrade Notes
```

This structure was frozen here by Issue #197 and is added to `CHANGELOG.md` by
Issue #198.

## Release-preparation completion

Issue #198 prepared `v0.17.0`: it updated Package metadata and current version
expectations, added the frozen Changelog structure, reconciled final Release-
candidate documentation, and reran Release-preparation validation. It changed no
product code, behavior, dependency, build backend, Package Data, Schema, example,
generated output, benchmark value, persistence format, or non-Package contract
version. Tagging and GitHub Release publication were later manual maintainer
actions. The maintainer published the Release on 2026-08-25 at `8187fbe`; Issue
#199 changes only post-publication documentation.

## Release-readiness conclusion

```text
Functional milestone:
    complete through Issue #196

Release preparation:
    prepared by Issue #198

Package baseline:
    0.17.0

Published stable Release:
    v0.17.0 at 8187fbe

v0.17.0 publication:
    completed manually on 2026-08-25

Post-publication synchronization:
    Issue #199, documentation only

v1.0.0:
    planning only; not ready
```
