# v1.0.0 final technical Release-readiness audit

## Audit purpose

This document is the authoritative Issue #207 final technical audit of the
bounded SkatMind v1 technical baseline. It reconciles Issues #201 through #206,
the complete required-before-v1 ledger, current executable contracts, Package
and platform evidence, and the remaining Release-process Gates. It changes
documentation only.

The audit finds no material technical Release blocker and records the technical
decision to close B-06. That closure and approval to begin hands-on maintainer
UAT under Issue #208 become final only after the Issue #207 change is merged and
its two required CI jobs are green. B-09 and B-07 remain open. Package `1.0.0`
is not prepared, Package version remains `0.17.0`, and `v1.0.0` is not Release-
ready.

This audit does not implement or fix product behavior, perform UAT, prepare a
Release candidate, change the Changelog, choose Release metadata, tag, publish,
or deploy anything.

## Authoritative source hierarchy

Conflicts are resolved through this seven-level hierarchy:

1. Official ISkO/SkWO and accepted International Skat Court material govern
   game and competition rules.
2. Approved repository product decisions and normative matrices govern the
   bounded SkatMind product scope.
3. Current executable contracts, constants, Package metadata, persistence, and
   source govern implemented behavior.
4. Authoritative Schemas and byte-identical packaged resources govern stable
   JSON documents.
5. Examples, generated outputs, benchmark corpora, validators, tests, complete
   checks, and CI provide executable evidence.
6. This audit and synchronized current-state documentation govern the current
   readiness conclusion.
7. Historical Changelog, Issue-era, readiness, and Release records remain
   point-in-time evidence and are not rewritten with later identities or counts.

GitHub Releases is authoritative for publication status. No Package-index or
PyPI publication is claimed.

## Published and current baselines

The three relevant states remain distinct:

```text
Published historical Release:
    v0.17.0

Current technical baseline:
    SkatMind Package 0.17.0

Future Release candidate:
    Package 1.0.0 not prepared
```

The published `v0.17.0 — Rules, Search, Coaching, and performance closure`
Release remains historical evidence with these exact point-in-time facts:

| Dimension | Published historical `v0.17.0` value |
| --- | --- |
| Publication commit | `8187fbe684559f9c0c2ba444be1bf33950359ad2` (`8187fbe`) |
| Publication date | 2026-08-25 |
| Package version | `0.17.0` |
| Distribution/import namespace | `skat-ai` / `skat_ai` |
| Console Script | `skat-ai = skat_ai.cli:main` |
| Python metadata | `>=3.13` |
| Public API contract | `1` |
| Root workflows | 7 |
| Console Scripts | 1 |
| Settlement Normative Matrix | version `3` |
| Canonical Settlement cases | 61 |
| Authoritative Schemas | 71 |
| Packaged Schema Resources | 71 |
| Session examples | 6 |
| Generated outputs | 98 |
| Private Corpus prepared downloads | 10 |
| Published pytest result | 7,479 passed in 921.96s |

Those former identities are historical evidence, not active aliases. The
current pre-v1 technical baseline is separately:

| Dimension | Current technical value |
| --- | --- |
| Product | SkatMind |
| Repository | `hnnng-w/skatmind` |
| Package version | `0.17.0` |
| Distribution/import namespace | `skatmind` |
| Console Script | `skatmind = skatmind.cli:main` |
| Python metadata | `>=3.13` |
| Certified v1 runtime | CPython 3.13 |
| License | `AGPL-3.0-only` |
| Direct runtime dependencies | `jsonschema>=4.23.0`, then `referencing>=0.31.0` |
| Public API contract | `1` |
| Root workflows | 7 |
| Console Scripts | 1 |
| Settlement Normative Matrix | version `3` |
| Canonical Settlement cases | 61 |
| Authoritative Schemas | 71 |
| Packaged Schema Resources | 71 |
| Session examples | 6 |
| Generated outputs | 98 |
| Private Corpus prepared downloads | 10 |

## Issues #201 through #206 closure inventory

| Issue | Exact technical outcome | Gate result |
| --- | --- | --- |
| #201 | Adds an independent literal rule oracle for 32 unique Cards, 120 total points, 25 strongest-to-weakest effective-category sequences, 674 strict pairwise comparisons, and 240 declared-value rows: 220 Suit and 20 Grand. It changes no product code. | R-01 and R-06 `satisfied`; B-01 closed. |
| #202 | Enforces the four internal stages `loaded_request`, `validated_consumed_input`, `retained_stage_linkage`, and `final_serialization` for all seven Root workflows. It covers exact Request/options/external sources, pre-analysis Information Use Context, retained-stage authorization, and final Result/artifact reconciliation without widening public Provenance. | P-10 and P-13 `satisfied`; B-02 closed. |
| #203 | Covers all nine canonical concrete Multi-Step phases, including same-World current-Trick completion, local-card preservation, local-Decision-only step counting, unchanged Search isolation, Policy Comparison parity, and one intentional existing-scenario behavior update without a Schema or scenario-count change. | P-19 `satisfied`; B-03 closed. |
| #204 | Applies `AGPL-3.0-only`, exact root legal files, PEP 639 metadata, Wheel/sdist/installed legal-file validation, and dependency/asset license review. `LICENSE` SHA-256 is `d8a6cc31abc16b6748c7a21f21611f5a1ec33f67d22ca23d7da1c19b95496bee`; `COPYRIGHT` is exactly `Copyright (C) 2026 Henning Wiese` plus LF. | B-04 closed. |
| #205 | Completes the hard-cut SkatMind product, repository, distribution, namespace, CLI, resource, Schema, active-identifier, and persistence migration. There is no active former Package/import/CLI alias. Strict released version-1 persisted input remains readable; canonical writes use SkatMind identities; verified immutable legacy Corpus IDs remain opaque. The reviewed occurrence inventory is exact. | P-09 `satisfied`; B-08 closed. |
| #206 | Declares the two exact direct dependency floors; validates resolved Source, Editable, Wheel, and sdist plus exact-minimum Wheel and sdist; exercises all seven workflows, APIs, CLI forms, Session, Capture, Corpus, Provenance, resources, errors, Exit Codes, semantic parity, `pip check`, and repository non-mutation on Windows and Ubuntu. | P-34 `satisfied`; B-05 closed. |

The exact merged Issue #206 commit is
`af9de1a63ed23b84cc758d0d0504a3c72073dbb0`. GitHub Actions run
[`33182864852`](https://github.com/hnnng-w/skatmind/actions/runs/33182864852)
passed both `check` in 1h 1m 36s and `v1-supported-platform-matrix` in
1h 8m 25s on `ubuntu-latest` with Python 3.13.

## Complete 53-row ledger reconciliation

The required-before-v1 ledger contains exactly 17 ISkO rows, two SkWO rows, and
34 Product rows. No row is omitted or duplicated.

| Audit status | Count |
| --- | ---: |
| `satisfied` | 19 |
| `satisfied_with_approved_bounded_scope` | 34 |
| `evidence_required` | 0 |
| `implementation_required` | 0 |
| `product_decision_required` | 0 |
| **Total** | **53** |

### Direct evidence anchors

The final audit retains these direct executable evidence anchors from
[the scope and traceability audit](v1_0_scope_and_traceability_audit.md):

| Anchor | Direct executable evidence |
| --- | --- |
| Rules | `tests/test_rules.py`, `tests/test_game_declaration.py`, `tests/test_game_value.py`, `tests/test_v1_official_rule_evidence.py` |
| Settlement | `tests/test_final_settlement.py`, `tests/test_settlement_normative_matrix.py`, `tests/test_claim_and_settlement_v1_compatibility.py` |
| Historical | `tests/test_historical_game.py`, `tests/test_historical_game_event_chain.py`, and focused shortening/Claim tests |
| List | `tests/test_fixed_three_player_historical_list.py`, `tests/test_fixed_three_player_historical_list_aggregation.py`, `tests/test_fixed_three_player_historical_list_comparison.py` |
| Match | `tests/test_match_capture_contracts.py`, `tests/test_match_workspace_persistence.py`, `tests/test_match_analysis_exports.py`, `tests/test_local_match_capture_web.py` |
| Session | `tests/test_public_session_api.py`, `tests/test_public_session_files.py`, `tests/test_session_transitions.py`, `tests/test_session_cli.py` |
| API | `tests/test_public_api_contracts.py`, `tests/test_public_python_api_v1.py`, `tests/test_installed_cli.py` |
| Provenance | `tests/test_field_provenance_coverage.py`, `tests/test_application_provenance.py`, `tests/test_complete_result_provenance.py`, `tests/test_public_field_provenance.py`, `tests/test_v1_input_provenance.py`, `tests/test_v1_provenance_enforcement.py`, `tests/test_v1_provenance_serialization.py`, `tests/test_v1_provenance_adversarial.py` |
| Simulation | `tests/test_simulation.py`, `tests/test_multi_step_simulation.py`, `tests/test_canonical_multi_step_phase.py`, `tests/test_canonical_multi_step_phase_execution.py`, `tests/test_simulation_provenance.py` |
| Inference | `tests/test_hidden_card_inference.py`, `tests/test_bounded_search_information.py` |
| Search | `tests/test_bounded_search_result.py`, `tests/test_bounded_search_quality_baselines.py`, `tests/test_bounded_search_benchmark.py` |
| Information-set | `tests/test_information_set_search_executor.py`, `tests/test_information_set_search_multi_step.py`, `tests/test_canonical_multi_step_phase_execution.py`, `tests/test_information_set_search_benchmark.py` |
| Recommendation | `tests/test_recommender.py`, `tests/test_recommendation_workflow.py`, `tests/test_live_search_recommendations.py` |
| Policy | `tests/test_opponent_policy.py`, `tests/test_opponent_profile_policy.py`, `tests/test_opponent_statistics.py`, `tests/test_opponent_profile_derivation.py`, `tests/test_historical_opponent_statistics.py`, `tests/test_rolling_opponent_policy_evaluation.py` |
| Review | `tests/test_post_game_review.py`, `tests/test_historical_search_review.py`, `tests/test_flat_retrospective_search_review.py` |
| Coaching | `tests/test_replay_coaching_report.py`, `tests/test_information_set_replay_coaching_report.py`, `tests/test_learning_corpus_tactical_coaching.py` |
| Tactical | `tests/test_historical_tactical_motif_review.py`, `tests/test_learning_corpus_tactical_motif.py` |
| Dataset | `tests/test_training_dataset.py`, `tests/test_training_dataset_preparation.py`, `tests/test_dataset_partition_audit.py`, `tests/test_learning_dataset_v2.py` |
| Output | `tests/test_examples.py`, `scripts/validate_examples_schema.py`, `scripts/validate_generated_outputs_schema.py` |
| Distribution | `tests/test_v1_package_license.py`, `tests/test_packaging_and_distribution.py`, `tests/test_v1_supported_platform_matrix.py`, `tests/test_installed_cli.py`, `scripts/validate_distribution_artifacts.py`, `scripts/validate_v1_supported_platform_matrix.py`, `scripts/check.ps1`, and the two Ubuntu jobs |

| ID | Traceability state | Final v1 audit status | Approved boundary and direct evidence | Missing v1 work / blocker |
| --- | --- | --- | --- | --- |
| R-01 | `supported` | `satisfied` | Exact 32-Card, 120-point, 25-sequence, 674-comparison Rules oracle. | None |
| R-02 | `supported` | `satisfied` | Suit, Grand, Null, and jack trump Rules tests. | None |
| R-03 | `supported` | `satisfied` | Legal-card and strict Historical replay Rules evidence. | None |
| R-04 | `supported` | `satisfied` | Trick winner, ownership, points, and next-leader evidence. | None |
| R-05 | `partially_supported` | `satisfied_with_approved_bounded_scope` | Final bid/declaration facts and dependencies; no auction reconstruction. | None within bounded scope |
| R-06 | `partially_supported` | `satisfied` | Exact 240-row independent Suit/Grand declared-value oracle. | None |
| R-07 | `supported` | `satisfied` | Fixed Null values 23, 35, 46, and 59. | None |
| R-08 | `partially_supported` | `satisfied_with_approved_bounded_scope` | Explicit bounds and safe complete-Historical Matador inference. | None within bounded scope |
| R-09 | `partially_supported` | `satisfied_with_approved_bounded_scope` | Hand declaration, value, ownership, points, and inference evidence. | None within bounded scope |
| R-10 | `partially_supported` | `satisfied_with_approved_bounded_scope` | Point/trick/announcement and bounded proof/open-throw evidence. | None within bounded scope |
| R-11 | `supported` | `satisfied` | Ouvert dependencies, values, public hands, Results, and Settlement. | None |
| R-12 | `partially_supported` | `satisfied_with_approved_bounded_scope` | Suit/Grand overbid and supplied impossible-Null replacement paths. | None within bounded scope |
| R-13 | `supported` | `satisfied_with_approved_bounded_scope` | Approved externally supplied favorable impossible-Null replacement. | None within bounded scope |
| R-14 | `partially_supported` | `satisfied_with_approved_bounded_scope` | Strict normal Historical completion and compatible legacy completed positions. | None within bounded scope |
| R-15 | `partially_supported` | `satisfied_with_approved_bounded_scope` | Historical party-wide all-remaining-Tricks Claim with exact bounded proof. | None within bounded scope |
| R-16 | `partially_supported` | `satisfied_with_approved_bounded_scope` | Structured declarer/defender concessions in supported flat/Historical paths. | None within bounded scope |
| R-17 | `partially_supported` | `satisfied_with_approved_bounded_scope` | Matrix version `3`, 61 cases, supported endings, Claim composition, and impossible Null. | None within bounded scope |
| W-01 | `supported` | `satisfied_with_approved_bounded_scope` | Fixed-three-player 36-position performance and aggregation. | None within fixed-three-player scope |
| W-02 | `supported` | `satisfied_with_approved_bounded_scope` | Standings, unresolved ties, and externally supplied lot. | None within bounded scope |
| P-01 | `partially_supported` | `satisfied_with_approved_bounded_scope` | Private local fixed-format Match identity and metadata; Match evidence. | None within private scope |
| P-02 | `partially_supported` | `satisfied_with_approved_bounded_scope` | Exact observed behavior and uninterpreted Commentary/Response evidence. | None within bounded scope |
| P-03 | `partially_supported` | `satisfied_with_approved_bounded_scope` | Private version-1 Match Workspace persistence and optimistic Save. | None within bounded scope |
| P-04 | `partially_supported` | `satisfied_with_approved_bounded_scope` | Transport-free rapid capture and private browser orchestration. | None within private scope |
| P-05 | `supported` | `satisfied_with_approved_bounded_scope` | Information-safe Decision, Historical, Training-source, and list preparation. | None within no-execution scope |
| P-06 | `supported` | `satisfied_with_approved_bounded_scope` | Explicit bounded Match analysis, ephemeral reports, and private exports. | None within private scope |
| P-07 | `supported` | `satisfied_with_approved_bounded_scope` | Loopback-only Capture browser and CLI under the sole Console Script. | None within loopback scope |
| P-08 | `supported` | `satisfied_with_approved_bounded_scope` | Frozen public Session and Session file APIs. | None within frozen API scope |
| P-09 | `supported` | `satisfied` | SkatMind hard cut, seven workflows, one Console Script, and migration evidence. | None |
| P-10 | `partially_supported` | `satisfied` | Four-stage all-workflow internal information-Provenance evidence. | None |
| P-11 | `supported` | `satisfied_with_approved_bounded_scope` | Local Session API/file/CLI/Assistant capture. | None within local scope |
| P-12 | `supported` | `satisfied_with_approved_bounded_scope` | Strict version-1 Session replay, fingerprints, CAS, and atomic Save. | None within local persistence scope |
| P-13 | `partially_supported` | `satisfied` | Enforced live source contexts through final serialization. | None |
| P-14 | `supported` | `satisfied_with_approved_bounded_scope` | Decision-time, observed-card, and final-outcome separation. | None within bounded scope |
| P-15 | `supported` | `satisfied` | Deterministic Immediate simulation. | None |
| P-16 | `supported` | `satisfied_with_approved_bounded_scope` | Exact structural compatible-world inference; uncalibrated labels. | None within bounded scope |
| P-17 | `partially_supported` | `satisfied_with_approved_bounded_scope` | Late exact/PIMC Search, integrations, profiles, and deterministic benchmarks. | None within bounded scope |
| P-18 | `partially_supported` | `satisfied_with_approved_bounded_scope` | Three-Trick controlled-player selected-world Information-set Search. | None within bounded scope |
| P-19 | `partially_supported` | `satisfied` | All nine canonical phases and same-World continuation evidence. | None |
| P-20 | `supported` | `satisfied` | Legal objective-aware Immediate/Search/Auto recommendations. | None |
| P-21 | `supported` | `satisfied` | Deterministic global and side-specific opponent Policies. | None |
| P-22 | `partially_supported` | `satisfied_with_approved_bounded_scope` | Explainable rule-based time-safe Profiles. | None within rule-based scope |
| P-23 | `partially_supported` | `satisfied_with_approved_bounded_scope` | Heuristic evidence bands and activation Gates. | None within heuristic scope |
| P-24 | `supported` | `satisfied` | Suit/Grand/Null declarer/defender Review, unavailable cases, and Search comparison. | None |
| P-25 | `partially_supported` | `satisfied_with_approved_bounded_scope` | One-game Replay/Information-set Coaching and structural Tactical Review. | None within bounded scope |
| P-26 | `supported` | `satisfied_with_approved_bounded_scope` | Exact timed structural Tactical Motif taxonomy without quality claims. | None within bounded scope |
| P-27 | `partially_supported` | `satisfied_with_approved_bounded_scope` | Normal completion, six shortenings, one continuation, and bounded Claim. | None within approved event scope |
| P-28 | `partially_supported` | `satisfied_with_approved_bounded_scope` | Public Dataset v1 and deterministic two-mode preparation without training. | None within bounded scope |
| P-29 | `supported` | `satisfied_with_approved_bounded_scope` | Known-opponent and Player-disjoint unseen-player policies and audits. | None within two fixed algorithms |
| P-30 | `supported` | `satisfied` | Version-1 external Opponent Statistics and Profile derivation. | None |
| P-31 | `supported` | `satisfied` | Exact supported-game Historical statistics and export. | None |
| P-32 | `supported` | `satisfied_with_approved_bounded_scope` | Time-safe behavioral-imitation rolling evaluation. | None within bounded scope |
| P-33 | `supported` | `satisfied` | Frozen ordered 98-scenario output matrix. | None |
| P-34 | `supported` | `satisfied` | Dependency, install-form, all-workflow, Windows, Ubuntu, and distribution evidence. | None; B-05 closed |

Every row retains a direct evidence anchor, has no missing v1 work, and has no
implementation blocker. Accepted bounded rows are not generalized beyond their
stated limits.

## Rules, Claims, Settlement, and Historical audit

The bounded Rules contract covers Card points/order, legal play, Tricks, final
declarations, Matadors where inferable, Suit/Grand values, all four Null values,
Overbid within the approved paths, normal Results, supported shortened endings,
one continuation before completion or shortening, and strict Historical Games.

Settlement Normative Matrix version `3` retains exactly 61 canonical case IDs:
48 `supported_as_is`, 13 `not_supported_v1`, and zero requiring implementation
or decision. The only v1 Claim is the Historical party-wide all-remaining-Tricks
Claim with one through five unresolved Tricks and valid exact AND/OR proof.
Invalid or unavailable proof rejects the terminal record without fallback.

The audit retains no general Claim interface, complete official Claim or
Settlement coverage, arbitrary event-stream adjudication, generalized conduct
or correction handling, or four-player support claim.

## Search, simulation, inference, and Recommendation audit

The current bounded contract includes deterministic Immediate Analysis, late
Perfect-Information Minimax, compatible-world PIMC, exact and sampled Worlds,
equal duplicate sampled-draw weight, structural budgets, explicit complete,
partial, timeout, and unavailable Results, selected-world Information-set
Search, all nine Multi-Step phases, Policy Comparison, Match/Historical/Dataset
integration, and deterministic functional/structural benchmarks.

Information-set execution controls Player `me` for at most three unresolved
Tricks. Other Players retain fixed deterministic Policies; equal controlled
Observations must choose equal actions. Exact Worlds, hidden ownership,
Observations, controlled Policies, branch state, and caches remain private.
Recommendation remains legal, perspective-aware, objective-aware, deterministic
under fixed inputs, and explicit when no recommendation is available.

The candidate claims no equilibrium, CFR, calibrated probability, complete-
contract solver, joint Defender optimization, global optimality, Information-
set-aware `auto`, complete Strategy-Fusion correction, or latency SLA.

## Information-Provenance audit

Internal information-Provenance contract version `1` and public Provenance
version `1` remain unchanged. The mandatory lifecycle is:

```text
loaded_request
validated_consumed_input
retained_stage_linkage
final_serialization
```

All seven Root workflows retain exact consumed Request, effective option, and
optional external-source attachments; enforce independent Information Use
Context before analysis; authorize retained-stage dependencies and temporal use;
and reconcile the final Result and artifacts actually returned. Mutation,
uncovered leaves, orphaned entries, cross-workflow references, widened
visibility, temporal inversion, and artifact mismatches are rejected.

Public conversion reruns no workflow. It remains default-omitted and exposes
only one exact redacted Root Result plus artifacts actually returned, with
coverage recomputed after redaction. Consumed-input, Decision, intermediate,
hidden-world, source-binding, and lifecycle-checkpoint evidence remains private.
Provenance and Confidence remain separate contracts.

## Public API, CLI, and error audit

The stable namespaces and exact ordered export counts are:

| Namespace | Exports |
| --- | ---: |
| `skatmind` | 3 |
| `skatmind.api` | 1 |
| `skatmind.api.v1` | 40 |
| `skatmind.api.v1.session` | 59 |
| `skatmind.api.v1.session.files` | 12 |
| `skatmind.errors` | 13 |

Runtime inspection and existing exact-order tests confirm the source-controlled
ordered `__all__` tuples. The Package Root is exactly `api`, `errors`, and
`__version__`; `skatmind.api` exports exactly `v1`. The 40 API-v1 exports retain
the contract/version values, immutable Request/options/Result/artifact values,
version information, `parse_request`, `execute`, `execute_document`,
`serialize_result`, public Provenance values, three Exit Codes, ten error/warning
classes, and the appended `session` namespace in their existing order.

The Session namespace retains 59 exports: version/namespace/policy constants,
the 12-operation tuple, Provenance values, version/options/Result values, all
Session contracts and typed Commands, parse/create/apply/rewind/correct/export/
checkpoint/persistence/serialization operations, Decision Observation and
Checkpoint Review contracts/operations, and the appended `files` namespace in
their existing order. The file namespace retains its three constants, four
public values, version query, Save, Load, and serializer in their existing
12-name order. `skatmind.errors` retains three Exit Code constants followed by
the stable error hierarchy and `SkatMindDeprecationWarning`.

The seven ordered `WorkflowV1` values remain:

```text
position_analysis
historical_game
training_dataset
training_dataset_preparation
opponent_statistics
fixed_three_player_historical_list
fixed_three_player_historical_list_comparison
```

The normal Result states remain `complete`, `partial`, `timeout`, `unavailable`,
`final`, `lot_required`, and `not_assessable`. Exit Codes remain `0`, `1`, and
`2`. Supported CLI forms remain installed `skatmind`, module
`python -m skatmind`, and repository Legacy `python main.py` through one Console
Script. The 12 Session subcommands remain `new`, `show`, `apply`, `undo`,
`correct`, `checkpoint`, `export-position`, `export-historical`, `analyze`,
`review`, `finalize`, and `assistant`. Private `capture` and `corpus` are CLI
families, not Root workflows or public Python namespaces. No active former
Package, import, module, or command alias exists.

## Schema, example, and generated-output audit

The current exact set is 71 authoritative `schemas/*.schema.json` files and 71
byte-identical packaged resources. Filename sets and bytes match; every `$id` is
unique and follows `https://example.local/skatmind/<filename>`; local `$ref`
resolution is complete and does not use the network.

All Root examples and exactly six Session examples pass their Schema and semantic
validators. The six Session files are `session_create_live.json`,
`session_create_retrospective.json`, `session_command_record_play.json`,
`session_correction_record_play.json`, `session_live_persistence.json`, and
`session_retrospective_persistence.json`.

The ordered generated-output registry remains exactly 98 scenarios: 1-70
pre-public-Provenance Root coverage, 71-77 one public-Provenance scenario per
Root workflow, 78-85 Session, 86-88 Historical Claim, 89-92 Information-set
Search, 93-94 Information-set Multi-Step/Policy Comparison, 95-96
Information-set Replay Coaching, and 97-98 Tactical Motif Review. Scenario IDs
and order remain stable. Historical Release counts remain historical.

## Session, Match, Corpus, and Dataset audit

The public Session API, Session version-1 persistence, automatic exact
Checkpoints, observations, request exports, analysis/review operations, public
file Save/Load, and all-three-form Session CLI remain the bounded public local
capture surface.

Match Capture remains a private local fixed-three-player workflow over one
explicit version-1 Workspace file. It provides rapid entry, evidence-aware
Games, annotations, information-safe preparation, explicit bounded analysis,
ephemeral Reports, authenticated downloads, and no Public Match API, Schema, or
eighth Root workflow.

Learning Corpus remains a private local workflow over one explicit version-1
root/Catalog/object store. Current-Snapshot Player Catalog, Human Evidence,
Strategy Teacher Evidence, Learning Dataset version `2`, partition preparation,
summaries, Tactical Evidence, Tactical Coaching, and all ten downloads remain
derived process-local values. They do not create a Public Corpus/Dataset-v2 API
or Schema and are not persisted as derived artifacts. Database, remote, and
collaborative deployment remain absent.

## Persistence and migration audit

Session documents, Match Workspace documents, Learning Corpus Catalogs and
immutable objects, and Match Analysis Report-source documents remain strict
version `1`. Canonical writers emit the active SkatMind kinds and SHA-256
domains. Released pre-rename documents are accepted only through an exact full
legacy profile; mixed kinds, fingerprint domains, IDs, or nested identity
relationships are rejected. Load does not mutate input. An explicit successful
rewrite emits canonical identities.

Compare-and-swap and same-directory atomic replacement remain required for
mutable local files. Immutable object publication remains no-clobber. Verified
legacy content-addressed Corpus IDs remain opaque and are not rekeyed, copied, or
deleted. There is no automatic destructive migration.

## Coaching, Tactical, and Player-analysis audit

The bounded contract includes Replay Coaching, Information-set Replay Coaching,
Historical Tactical Motif Review, Current-Snapshot Tactical Motif Evidence,
exact descriptive cross-game summaries, Tactical Cross-game Coaching, fixed
Guidance, time-safe Statistics, and rule-based Profiles.

Actual Cards are observed behavior rather than ground truth. Teacher evidence is
method-bound. Tactical Motifs are structural observations. Cross-game Focus
Areas are bounded review aids. The product makes no Player Rating, perfect-play,
trait, strength, weakness, intent, signaling, communication, causal, or
statistical-significance claim.

## Package, license, dependencies, and distribution audit

The Package remains `0.17.0`, Python metadata remains `>=3.13`, the build backend
remains `setuptools.build_meta` with `setuptools>=77.0.3`, and runtime dependencies
remain exactly `jsonschema>=4.23.0` then `referencing>=0.31.0`. There is one
`dev` extra, one Console Script, `py.typed`, 71 packaged Schemas, and packaged
Capture/Corpus HTML, CSS, and JavaScript.

Source, Editable, Wheel, and sdist resolved lanes and exact-minimum Wheel/sdist
lanes pass. The exact floor pair is `jsonschema==4.23.0` and
`referencing==0.31.0`; normal resolved evidence records the versions selected by
the resolver without imposing a latest-version claim. Every installed lane runs
`pip check`. Wheel, sdist, installed metadata, legal files, resources, APIs, CLI
forms, and semantic outputs are reconciled. No Package-index/PyPI publication is
claimed.

## Windows and Ubuntu supported-platform audit

The exact certified v1 boundary is:

```text
Windows:
    Windows 11
    Windows PowerShell 5.1
    CPython 3.13

Ubuntu:
    ubuntu-latest GitHub Actions
    CPython 3.13
```

Issue #206 local evidence used CPython 3.13.7, passed all six executable matrix
cells, passed `7,658` pytest tests in 1999.08s, ended with `All checks passed.`,
and passed `git diff --check`. The exact merged Ubuntu evidence is run
`33182864852` on commit
`af9de1a63ed23b84cc758d0d0504a3c72073dbb0`, with both required jobs green.

Issue #207 focused regression evidence on Windows/CPython 3.13.7 passed 510
tests in 784.94s. It covers official Rules, Claim/Settlement, internal/public
Provenance, canonical Multi-Step phases, license, rename/migration, platform
matrix contracts, Public API, installed CLI, Session, Match persistence, Corpus
persistence/downloads, and distribution. One unchanged-tree complete local check
runs after this documentation is final. Its exact result, full pytest count and
timing, clean diff/worktree evidence, merged commit, and both post-merge job
results are retained in the Issue completion record. The check is an Issue-
closure control, not a new product or platform contract.

No macOS, Python 3.14, named-browser, hardware-minimum, cross-machine latency,
Docker, production-SLA, or hosted-deployment certification is claimed.

## Privacy, security, and product-claim audit

Live and Retrospective information remain separated by exact visibility and
temporal contexts. Search Worlds, hidden ownership, controlled Policies, caches,
and branches remain private. Public Provenance is redacted and recomputed.
Match/Corpus dashboards and downloads remain minimized and path-free.

Capture and Corpus bind only to `127.0.0.1`, accept only loopback/localhost Host
values for the active port, require an unguessable bootstrap token and
constant-time cookie comparison, use `HttpOnly; SameSite=Strict` cookies, enforce
same-origin mutation requests, send no-store/nosniff/no-referrer/frame-denial,
CSP, and Permissions-Policy headers, use packaged local assets, and declare no
external runtime request. Focused browser tests reject bad Host, token, cookie,
Origin, method, size, route, and path traversal cases and verify token/path
non-disclosure.

This local boundary is not an encryption, key-management, account, remote-
hosting, cloud, collaboration, backup, or production-security claim.

## Accepted bounded v1 limitations

The following are accepted limitations, not technical blockers:

* final declaration rather than full auction reconstruction;
* one Historical-only party-wide Claim bounded to five unresolved Tricks;
* six supported terminal shortenings and at most one continuation;
* supplied impossible-Null replacement rather than optimization;
* bounded late-game exact/PIMC and three-Trick Information-set Search;
* no equilibrium, calibrated probability, complete-contract, global-optimality,
  or latency claim;
* structural inference, heuristic Confidence, and rule-based Profiles;
* structural Tactical evidence without truth, trait, communication, causality,
  significance, or Rating claims;
* private local Match and Corpus surfaces and process-local derived artifacts;
* strict local version-1 persistence without remote access, encryption, merge,
  or backup; and
* no Package-index/PyPI publication requirement.

## Post-v1 work

Post-v1 directions include full auction modeling, broader/complete-contract
solvers, wider imperfect-information policy solving, equilibrium/CFR research,
calibrated probability, learned Profiles, model training, online-platform
adapters, browser extensions, and remote/collaborative deployment after separate
security and operations decisions. These directions are not promoted into the
required v1 ledger.

## Not-required work

Formal series aggregation, tournament management, official federation reports,
Public Match/Corpus/Dataset-v2 APIs or Schemas, Match/Corpus Root workflows,
derived-artifact persistence, automatic Report capture, Historical Report
import, database deployment, broader Ratings, Provenance/Confidence unification,
Session GUI/browser UI, distributed locking, encryption/key management,
automatic backup, dedicated production Budget profiles, latency/SLO guarantees,
macOS or named-browser certification, Package-index metadata/publication,
Information-set-aware `auto`, and general natural-language Claim adjudication are
not required for v1.

## Unconditional exclusion

Four-player table support is the only unconditional exclusion.

## Technical blocker sweep

The audit searched current executable evidence and code-adjacent documentation
for contradictions in required-row status, metadata, public exports, workflow
counts, Schema count/identity, persistence, dependencies, installation forms,
platforms, license, output registry, identity, information boundaries, security,
and accepted limitations.

| Finding | Classification | Resolution |
| --- | --- | --- |
| Current-state summaries still described B-05 and Issue #206 as conditional on merged Ubuntu CI. | `documentation_correction` | Synchronized by Issue #207; the required run and both jobs passed. |
| `public_python_api_v1.md` said the active packaged registry had 63 resources. | `documentation_correction` | Corrected to the current exact count of 71; historical 63-count Release statements remain unchanged. |
| `bounded_search_contracts.md` said the stronger-Search v1 gate remained open. | `documentation_correction` | Corrected to the Issue #200 approved bounded v1 contract; broader Search remains post-v1. |
| The active architecture summary omitted the supported Historical party-wide Claim from two workflow lists. | `documentation_correction` | Added the bounded Historical-only Claim without broadening its contract. |
| The new published-baseline table introduced four reviewed former-name occurrences. | `documentation_correction` | Classified all four as `historical_evidence` in the exact rename inventory. |
| Historical Issue-era files retain former identities, old counts, and then-current next actions. | `historical_only` | Preserved as point-in-time evidence under the rename inventory and source hierarchy. |
| General Claim/Settlement behavior beyond the approved exact boundary is absent. | `accepted_bounded_limitation` | Preserved as the frozen bounded v1 contract. |
| Complete solvers, calibrated models, and remote/collaborative deployment are absent. | `post_v1` | Preserved as later directions requiring separate decisions and acceptance criteria. |
| Public private-workflow APIs, derived persistence, broader Ratings, and latency certification are absent. | `not_required` | Preserved as work not required for the frozen v1 product. |

No finding is a `material_blocker`. No remediation Issue is required before UAT.

## Post-merge closure control

Issue #207 remains open until the maintainer verifies both required GitHub
Actions jobs on the exact merged Issue #207 commit:

```text
check:
    succeeded

v1-supported-platform-matrix:
    succeeded
```

Only after that evidence is green may B-06 and Issue #207 be finally closed and
Issue #208 begin. If either job fails, B-06 remains open, UAT does not begin, and
the failure must be classified before proceeding. OpenCode cannot verify that
future merged-commit evidence.

Issue #208 performs hands-on maintainer v1.0.0 user acceptance testing. It must
exercise representative supported workflows and local interfaces, classify
findings, create focused remediation Issues for accepted material findings, and
close B-09 only when those findings are resolved or explicitly accepted as
non-blocking. Issue #207 performs no UAT.

B-07 Release preparation remains open. It may begin only after B-06 and B-09 are
closed and any affected technical evidence is refreshed. Issue #207 does not set
Package `1.0.0`, add a Changelog section, prepare Release metadata, tag, or
publish. The exact next action after the post-merge control is Issue #208,
**Perform maintainer v1.0.0 user acceptance testing**.

## Final technical conclusion

```text
Technical v1 scope:
    frozen

Required-row ledger:
    19 satisfied
    34 satisfied_with_approved_bounded_scope
    0 evidence_required
    0 implementation_required
    0 product_decision_required
    53 total

Technical implementation blockers:
    none

B-06:
    closed by Issue #207

Maintainer UAT:
    approved to begin under Issue #208

Release preparation:
    not ready

Remaining blockers:
    B-09
    B-07

Package version:
    0.17.0

Package 1.0.0 candidate:
    not prepared

Release title, theme, date, tag, and publication commit:
    not frozen
```

## Post-audit UAT note

This note records later Issue #208 through #210 state without rewriting the Issue
#207 technical conclusion above. Maintainer UAT began after the #207 merge and
required CI. UAT-01 technically executed but failed user acceptance with one
accepted blocker and two accepted major findings:

```text
UAT-FINDING-001:
    No acceptable primary Product user interface exists.

UAT-FINDING-002:
    Root CLI onboarding is an unstructured expert interface.

UAT-FINDING-003:
    Session, Match Workspace, and Learning Corpus are not understandable
    user concepts.
```

Issue #209 freezes the approved
[unified local frontend contract](unified_local_frontend_contract.md) and the
exact #210 through #213 implementation sequence. Issue #210 implements the
[application shell](unified_local_frontend_application_shell.md) and partially
remediates UAT-FINDING-001 without closing it. It does not repeat UAT-01 or resume
UAT-02 through UAT-12. Issue #211 is the exact next implementation action.

The post-audit Release-process state is:

```text
Issue #208:
    open

UAT-01:
    failed

UAT-02 through UAT-12:
    paused

B-09:
    open and blocked by accepted UAT findings

B-07:
    open

UAT-FINDING-001:
    partially remediated
    remains open

UAT-FINDING-002:
    open

UAT-FINDING-003:
    open

Release preparation:
    not ready
```

B-06 remains closed. The 53-row ledger remains exactly 19 `satisfied`, 34
`satisfied_with_approved_bounded_scope`, and zero in each unresolved
classification. Frontend remediation belongs to B-09 outside that ledger.
Package version remains `0.17.0`, and Package `1.0.0` remains unprepared.
