# AGENTS.md

This file contains project-specific instructions for AI coding agents working on `skat-ai`.

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
* `docs/project_handoff.md`
* `docs/roadmap.md`
* `docs/architecture.md`
* `docs/input_json.md`
* `docs/output_json.md`
* `docs/application_orchestration.md`
* `docs/installed_cli.md`
* `docs/examples.md`
* `docs/schema_validation.md`
* `docs/requirements_traceability.md`
* `docs/v1_scope.md`

Do not assume old behavior if documentation or tests say otherwise.

## Current release state

The current published stable release is `v0.12.0`, with release theme "Fixed-
three-player historical lists and deterministic dataset preparation" and GitHub
Release title "v0.12.0 — Fixed-three-player historical lists and deterministic
dataset preparation". It points to commit `bbf955e`. The package version is
`0.12.0`, the Python requirement remains `>=3.13`, and the published baseline
validates 70 deterministic generated-output scenarios and passes 4,762 pytest
tests. Issues #127 through #134 complete the functional milestone, and Issue #135
completed release preparation. Publication was performed manually by the
maintainer, and GitHub Releases remains authoritative for publication status.

The historical published `v0.11.0` release, with release theme "Information-safe
Replay Coaching and structured historical outcomes", points to commit `cfd28e5`,
validates 64 deterministic generated-output scenarios, and passes 4,392 pytest
tests. Issues #118 through #124 complete that functional milestone, and Issue
#125 completed release preparation.

The active implementation milestone is `v0.13.0`. Issue #137 establishes public
API contract version `1`, the stable `skat_ai.api.v1` and `skat_ai.errors`
namespaces, immutable JSON document wrappers, compatibility metadata, stable
errors, Exit Code constants, and the legacy CLI-error alias. Issue #139 adds
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
Coaching, and an all-leaf partial-legacy Historical Result ledger. Public,
Dataset, Dataset Preparation, list, general Opponent, and complete non-legacy
Result provenance integration remain open.

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
* exact-prefix historical records for all five supported shortened terminal events
* variable-length historical snapshots, review decisions, and training samples, including zero-decision records
* shortened-game historical statistics, export, and rolling opponent-policy evaluation
* declarer-concession integration in historical statistics, export, and rolling opponent-policy evaluation
* unanimously accepted declarer-card-exposure historical records and variable-length workflow integration
* terminal bounded exact defender-open-play historical records and variable-length workflow integration
* timed non-terminal historical defender-open-play continuation with persistent public-hand information
* timed non-terminal historical declarer-card-exposure continuation with persistent public-hand information
* declared-Ouvert-aware Immediate, Multi-Step, Policy Comparison, flat review, and historical review simulation
* coherent private hidden-world ownership across each Multi-Step path and shared-root Policy Comparison
* exact compatible-world counting, marginals, and DP-guided sampling from confirmed public failure-to-follow evidence
* immutable information-safe bounded-Search views and exact legal states
* Suit, Grand, and all four normal non-overbid Null exact-world Minimax
* exact compatible-world counting, canonical enumeration, deterministic IID sampling with replacement, and common-prefix aggregation
* strict Search, Search-first auto, Multi-Step, Policy Comparison, flat post-game, Historical Search Review, and dataset-evaluation integration
* immutable Search budget profiles, strict-improvement and convergence fixtures, and measured reference performance
* immutable 61-case normative settlement matrix and bounded continuation-before-shortening historical chains
* information-safe one-game Replay Coaching evidence, prioritization, patterns, deterministic recommendations, complete report, public schema, JSON, CLI, examples, and generated-output coverage
* fixed-three-player 36-position historical-list contracts, aggregation, progression, standings, exact external-lot application, independent-list comparison, public JSON/schema/CLI workflows, examples, and generated-output coverage
* deterministic public automatic Training Dataset preparation with temporal Known-opponent and Player-disjoint unseen-player assignment, complete or unavailable Plans, lossless materialization, strict schemas, CLI, examples, and generated-output coverage
* stable public API contract version 1 with exact exports, immutable JSON Request and Result wrappers, compatibility metadata, public errors, and legacy Root CLI compatibility
* internal field-level information provenance contract version 1 with immutable sidecar ledgers, deterministic coverage auditing, dependency and temporal validation, context-use policy, public redaction, and safe serialization
* internal Application orchestration version 1 with immutable contracts and options, seven in-memory workflow handlers, five isolated Training Dataset operations, injected Opponent Statistics, auxiliary artifacts, no-I/O dispatch, and legacy CLI transport parity
* executable public Python API version 1 with immutable direct options, all-seven-workflow execution, separate artifacts, lazy Package Resource schema validation, and stable boundary errors
* installation-ready Setuptools Wheel and sdist artifacts with byte-identical packaged schemas, typing metadata, Package version export, and clean-install validation
* Package-owned installed and module CLI entry points with canonical parsing, direct Application execution, Legacy Root compatibility, and clean Wheel/sdist command validation
* internal live Position provenance enforcement across Immediate, Search,
  Hidden-card inference, Multi-Step, and Policy Comparison without public output
* internal retrospective provenance enforcement across flat post-game Position
  Analysis, Historical Review and Search Review, Replay Coaching, and selected
  Position/Historical Result branches without public output
* updated README, docs, roadmap, and project handoff

Current limitations include general and specific-trick claim verification,
defender-open-play proof beyond five unresolved tricks, multiple historical
continuations, historical end reasons beyond the supported bounded set,
incomplete settlement nuance, no additional preparation algorithms, algorithm
overrides, fallback or partial plans, global optimization, ratio guarantees,
Sample- or Player-count balancing, or component splitting, incomplete non-
Position, complete-Result, and public field-provenance integration, heuristic rule-based recommendations and
opponent behavior, and structural rather than calibrated or tactical hidden-card
inference. Search remains bounded late-game determinization subject to Strategy
Fusion, not an optimal imperfect-information policy or complete-contract Search;
exact world counts do not identify the real deal, sampled ownership is not
calibrated probability, measured timings are not latency guarantees, and timeout
activation is machine-dependent. Overbid Null replacement selection,
information-set Search, tactical motif detection, cross-game Coaching, causal
attribution, player ratings, complete field-level information provenance, and
interactive input/session capture remain open before `v1.0.0`.
No learned model, model-training workflow, website, browser integration,
four-player support, or claim of complete official rule coverage exists.

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
[`docs/v1_scope.md`](docs/v1_scope.md).

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
