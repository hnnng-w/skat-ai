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
* automatic matador inference where supported by known declarer-card context
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

## Current stable baseline

The current stable baseline is `v0.4.0`.

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
* CLI usability improvements including discoverable help text and optional quiet JSON-output runs
* generated-output validation for representative user-facing workflows
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

## Current useful future issues

Likely future work includes:

* adding dedicated left/right opponent policy examples
* adding richer post-game review examples
* improving realistic example positions
* using PlayerProfile confidence in opponent modeling
* improving advanced defender partnership decisions
* extending official settlement nuance coverage
* inferring matadors from completed-trick ownership where safe
* implementing full list, series, and tournament performance rating

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
