# Installed CLI

Issue #142 adds installed CLI contract version `1`. The three supported
invocation forms are:

```text
skat-ai
python -m skat_ai
python main.py
```

`skat-ai` and `python -m skat_ai` are installed Package interfaces. Repository-
root `python main.py` is the Legacy compatibility interface and remains supported
through at least `v1.0.0`.

Issue #147 adds the same optional `--include-provenance` transport flag to all
three forms. The Package version is `0.13.0`.

Issues #150 through #156 establish the Session contracts, replay, export,
Checkpoint, history-edit, persistence, Public API, Provenance, and standalone
Schema foundations. Issue #157 adds Session CLI contract version `1`, stable
public file transport, automatic Checkpoint collection, actual-card observation,
Checkpoint review, explicit Session-triggered Position/Historical execution, and
a phase-aware Assistant. The functional `v0.14.0` milestone is complete pending
release preparation. See [Public Session API version 1](public_session_api_v1.md)
and [Session CLI and end-to-end capture](session_cli_and_end_to_end_capture.md).

## Installation

An Editable, Wheel, or sdist installation exposes exactly one Console Script:

```toml
[project.scripts]
skat-ai = "skat_ai.cli:main"
```

No GUI Script or second command alias is installed. `python -m skat_ai` delegates
through `skat_ai/__main__.py` to the same Package-owned implementation. The
repository-root `main.py` file is not installed.

## Help and version

Use either installed form from any caller working directory:

```powershell
skat-ai --help
python -m skat_ai --help
skat-ai --version
python -m skat_ai --version
```

The exact installed version output is:

```text
skat-ai 0.13.0
```

The source-only fallback, when distribution metadata is unavailable, is:

```text
skat-ai 0+unknown
```

Help and version exit with Code `0`, write no error output, read no input or
Schema Resource, execute no workflow, and write no output file. Installed and
module help use generic caller paths. Repository examples are not Package Data
and are not implied to exist in an installation. Legacy help retains repository-
focused `examples/...` commands.

Session help is available with equal installed, module, and Legacy behavior:

```powershell
skat-ai session --help
python -m skat_ai session --help
python main.py session --help
```

## Options and execution

All three forms share canonical parsers and the same option names, aliases,
destinations, actions, defaults, choices, repeatability, and semantic validation.
Issue #142 added `--version`; Issue #147 added Root `--include-provenance`;
Issue #157 delegates a leading `session` token to the separate Session parser.
Every other invocation preserves the existing Root parser. The full current
option lists are available through `--help` and `session --help`.

The CLI preserves this transport sequence:

1. Parse arguments.
2. Load the Root input.
3. Detect the Root workflow.
4. Validate CLI-only options.
5. Load optional external Opponent Statistics.
6. Construct internal Application options.
7. Execute the Application directly.
8. Optionally attach bounded public-safe field provenance.
9. Write requested Root output.
10. Write a requested auxiliary Opponent Statistics export.
11. Print human-readable output unless `--quiet` is supplied.
12. Print file confirmations unless `--quiet` is supplied.

The CLI does not execute `skat_ai.api.v1` as an intermediate layer. It uses the
same internal Application orchestration as the Public Python API while retaining
CLI-specific file transport, validation, and presentation.

Session transport is the bounded exception: Session operations use the stable
Public Session and Public Session File APIs, while explicit `analyze`, `review`,
and `finalize` export Requests and invoke the same existing Application once.
This does not add an Engine workflow.

## Input and output

Use caller-owned paths with either installed form:

```powershell
skat-ai --input position.json
python -m skat_ai --input historical-game.json --output result.json --quiet
skat-ai --input position.json --include-provenance --output result.json
```

Without `--quiet`, successful workflows preserve the existing human-readable
headings, labels, ordering, and privacy boundaries. By default, `--output` writes
the unchanged Root JSON document. `--quiet` suppresses successful human-readable
output and file confirmations but does not suppress errors.

`--include-provenance` adds Root `field_provenance` for every Root workflow.
Without `--quiet`, the CLI prints only a concise aggregate section with version,
status, Result attachment, covered/total leaves, whether private dependencies
were redacted, and artifact attachment count. It does not print ledger entries,
field paths, references, cards, or Player IDs. With `--quiet`, the section is
suppressed while the JSON sidecar is still written.

Historical Opponent Statistics aggregation may write its separate reusable
artifact with `--export-opponent-statistics`. The auxiliary JSON remains outside
the primary Root output and uses the existing `opponent_statistics_input` shape.
When provenance is requested, the Root sidecar maps that actual artifact to
`training_dataset/opponent_statistics_input` with scope `artifact_document`; the
separate export document itself remains unchanged and has no nested sidecar.

## Session command family

The canonical Session subcommands are, in order:

```text
new
show
apply
undo
correct
checkpoint
export-position
export-historical
analyze
review
finalize
assistant
```

`new` creates an explicit caller-selected private file from strict JSON; `show`
strictly loads it; `apply`, `undo`, and `correct` save only applicable State
changes; and `checkpoint` collects or reuses one exact Position-ready frozen
Request. `export-position` and `export-historical` construct existing Requests
without execution. `analyze`, `review`, and `finalize` explicitly execute the
existing Position or Historical Application once when their export is available.
`assistant` provides deterministic phase-aware prompts and saves each accepted
State change.

Applicable commands use required `--session PATH`, optional or required
`--output PATH`, `--quiet`, and `--include-provenance`. Position-related commands
use `--samples`, `--seed`, `--opponent-strategy`, `--recommendation-method`, and
`--search-budget-profile`. `finalize` uses the existing Historical Snapshot,
Immediate Review, Search Review, Replay Coaching, Search seed/profile, and
Immediate sample/seed options. `assistant` accepts only explicit `--session`.

Mutations use strict load-operate-compare-and-swap-save with the loaded content
fingerprint. There is no default path, directory creation, force overwrite,
backup, merge, retry, or hidden reload. Automatic Checkpoint collection captures
Position-ready source decisions before accepted local Plays and Position-ready
resulting States, deduplicates exact equal Checkpoints, and never starts analysis
on its own.

See [Session CLI and end-to-end capture](session_cli_and_end_to_end_capture.md)
for exact per-subcommand options, JSON output shapes, privacy, persistence, and
Assistant behavior.

## Errors and Exit Codes

The stable process Exit Codes are:

```text
0 = success
1 = expected execution or resource failure
2 = CLI usage failure
```

Semantic CLI errors use `SkatAICliUsageError`, the `CLI error:` prefix, and Code
`2`. Standard `argparse` syntax and unknown-option errors also use Code `2`.
Expected `ValueError` and `OSError` failures use the `Error:` prefix and Code
`1`. Unexpected exception classes are not broadly caught.

Valid incomplete or unavailable Domain states remain successful, including
Search `partial`, `timeout`, or `unavailable`, Dataset Preparation `unavailable`,
list `lot_required`, Coaching `not_assessable`, rejected or revision-conflict
Session Commands, unavailable Session exports, unchanged Undo, partial
Correction, pending observations, and diverged Checkpoints. Session Save
conflicts, invalid persistence files, and filesystem failures use Code `1`.

## Compatibility

The canonical implementation is under `skat_ai.cli`. Root `main.py` is a thin
compatibility facade that preserves its existing importable wrappers, validators,
formatters, Exit Code constants, `CliUsageError` alias, callable signatures, and
established monkeypatch seams. A patched Root seam affects Legacy execution but
does not require the installed Package CLI to import Root `main.py`.

CLI functions and installed-CLI constants remain internal and are not stable
Public Python API exports. Issue #147 additively extends `skat_ai.api.v1`, Root
JSON Schema, and generated scenarios while preserving default Root JSON and the
flattened Public API envelope.

## Distribution validation

The existing single distribution validator builds one Wheel and one sdist. Its
clean environments verify exact Console Script metadata, module entry-point
inclusion, Root-main exclusion, help, version, Root JSON parity, normal failure
boundaries, provenance/quiet behavior, all 63 Schema Resources, and `py.typed`.
Issue #157 also verifies the public Session file namespace and Save/Load,
installed/module Session help, `new`/`apply`/`show`, Position analysis,
observation/review, Retrospective finalization, and an injected-I/O Assistant
smoke flow. Legacy Session parity is checked from the repository checkout. No
second Console Script is installed. The local full check and CI invoke that
validator once.

## Boundaries

Issue #157 changes no Package version, Root workflow, Root parser meaning, second
Console Script, publication state, or default Session path. Session persistence
files and explicit JSON outputs remain private caller-controlled data; concise
human output does not print complete private hands, full Skat, frozen Requests,
fingerprints, provenance entries, or file contents by default. GUI/browser UI,
online-platform integration, cloud synchronization, distributed locking,
encryption/key management, and automatic backups remain open.
See [Public field provenance](public_field_provenance.md).
