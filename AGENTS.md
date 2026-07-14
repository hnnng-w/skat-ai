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
* JSON input/output for regression-friendly testing

The project is not a machine-learning model, not a full official tournament system, and not a perfect-information Skat solver.

## Language rules

Repository code, tests, comments, docstrings, JSON keys, CLI output, and program output must remain in English.

Planning conversation may be in German, but all repository changes must be written in English.

## Table assumption

The project assumes a fixed three-player Skat table.

Do not prioritize four-player table support unless explicitly requested.

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

## Git workflow

Use feature branches for new work.

Do not commit directly to `main`.

Recommended workflow:

```powershell
git checkout main
git pull
git checkout -b feature/<issue-number>-short-description
```

Before committing:

```powershell
git status
.\scripts\check.ps1
git diff
```

Commit messages must be concise and in English.

Examples:

```powershell
git commit -m "Add left right opponent policy example"
git commit -m "Improve post-game review examples"
git commit -m "Use profile confidence in opponent policy presets"
```

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

Do not assume old behavior if documentation or tests say otherwise.

## Current release state

The current stable baseline is `v0.5.0`.

`v0.5.0` has been tagged and released.

`v0.6.0` is prepared for release but has not yet been tagged, published as a
GitHub Release, or closed out in GitHub issue tracking.

Current package version in release-prep work: `0.6.0`.

Generated-output validation currently covers 22 deterministic scenarios.

Major completed areas include:

* automatic matador inference
* post-game review decision quality
* post-game review decision factors and explanations
* post-game review recommendation gap details
* CLI output for post-game review summaries
* left/right opponent policy support
* basic defender cooperation improvements
* final settlement and overbid handling
* partial fixed-three-player ISkO-style rating
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

## Current useful next action

Selected `v0.6.0` release theme:

* from single-position analysis to credible list-aware review workflows

The `v0.6.0` release-preparation work documents completed issues #62 through
#67:

* #62 fixed three-player list standings output
* #63 expanded list-performance examples and generated-output validation
* #64 improved post-game review example quality and explanation coverage
* #65 added controlled left/right opponent policy effect coverage
* #66 used profile confidence in bounded opponent-strategy decisions
* #67 audited settlement and overbid edge-case coverage

Recommended next action after a clean release-prep check is commit, merge, tag,
and publish the `v0.6.0` release. Do not add more feature work unless a blocker
is discovered.

Deferred outside the prepared `v0.6.0` release unless explicitly scoped:

* four-player support
* full official tournament or series formats
* machine learning or learned opponent models
* perfect-information solving
* broad hidden-card inference
* broad `main.py` or CLI refactors
* full claim/concession legal-dispute modeling

## Safety rules for agent behavior

Do not run destructive Git commands unless explicitly requested.

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

At the end of issue-related work, always provide a ready-to-paste GitHub issue update comment.

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
