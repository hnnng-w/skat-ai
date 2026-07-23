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
* opponent policy modeling
* game result and settlement summaries
* automatic matador inference where supported by known declarer-card context and safe concrete-declarer completed-trick ownership
* post-game review support
* complete normal-play historical-game records
* information-safe historical decision snapshots and complete-game review
* versioned training and evaluation dataset records
* JSON input/output for regression-friendly testing

The current implementation is not a machine-learning model, a full official
tournament system, or a perfect-information Skat solver. Future product scope is
defined in [`docs/v1_scope.md`](docs/v1_scope.md).

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
* input JSON schema validation
* generated output JSON schema validation
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
* `docs/examples.md`
* `docs/schema_validation.md`
* `docs/requirements_traceability.md`
* `docs/v1_scope.md`

Do not assume old behavior if documentation or tests say otherwise.

## Current release state

The current code and release-preparation baseline is `v0.7.0`.

The package version is `0.7.0`.

Generated-output validation currently covers 27 deterministic scenarios.

The documented `v0.7.0` issue scope, issues #69 through #76, is complete.
`v0.6.0` remains the latest human-published release until `v0.7.0` is tagged
and published by a maintainer.

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
* updated README, docs, roadmap, and project handoff

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
