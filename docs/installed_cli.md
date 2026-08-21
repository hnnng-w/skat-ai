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
three forms. The Package version is `0.16.0`.

Issue #189 adds the same Root Information-set Search modes and validation to all
three forms without adding a Root workflow, command family, or Console Script.

Issues #150 through #156 establish the Session contracts, replay, export,
Checkpoint, history-edit, persistence, Public API, Provenance, and standalone
Schema foundations. Issue #157 adds Session CLI contract version `1`, stable
public file transport, automatic Checkpoint collection, actual-card observation,
Checkpoint review, explicit Session-triggered Position/Historical execution, and
a phase-aware Assistant. Issue #158 completed Release preparation for the
functional `v0.14.0` milestone, which the maintainer subsequently published
manually at commit `d5589f8`. See
[Public Session API version 1](public_session_api_v1.md)
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
skat-ai 0.16.0
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

Issue #165 adds the separate local Match Capture family with the same parity:

```powershell
skat-ai capture --workspace MATCH.json
python -m skat_ai capture --workspace MATCH.json
python main.py capture --workspace MATCH.json
```

Its exact options are required `--workspace PATH`, optional `--port INTEGER`
defaulting to `0`, and `--no-open`. It has no host, remote-bind, force,
authentication-disable, daemon, default-path, or output-file option.

Issue #179 adds the separate private local Learning Corpus family with equal
installed, module, and Legacy behavior:

```powershell
skat-ai corpus --corpus CORPUS_ROOT
python -m skat_ai corpus --corpus CORPUS_ROOT
python main.py corpus --corpus CORPUS_ROOT
```

Its exact options are required `--corpus PATH`, optional `--port INTEGER` from
`1` through `65535` defaulting to `8766`, and `--no-open`. It has no host,
remote-bind, Workspace, force, generate, daemon, default-root, or output option.

## Options and execution

All three forms share canonical parsers and the same option names, aliases,
destinations, actions, defaults, choices, repeatability, and semantic validation.
Issue #142 added `--version`; Issue #147 added Root `--include-provenance`;
Issue #157 delegates a leading `session` token to the separate Session parser.
Issue #165 adds leading `capture` dispatch before Session. Issue #179 adds leading
`corpus` dispatch before Capture. Every other invocation preserves the existing
Root parser. The full current option lists are available through `--help`,
`session --help`, `capture --help`, and `corpus --help`.

The Information-set Search Root additions are:

```text
--historical-information-set-search-review
--information-set-search-evaluation
```

Both require explicit `--search-seed` and reuse
`--search-budget-profile`. Historical Review also reuses `--samples` and
`--seed`; its default profile is `historical_review_v1`. It conflicts with
`--historical-search-review` and `--historical-replay-coaching` rather than
combining with either. Dataset evaluation is mutually exclusive with
`--evaluate-bounded-search` and the other Training Dataset operations. It
defaults to canonical validation/test order and profile `evaluation_v1`;
repeatable `--search-evaluation-partition` and positive
`--search-evaluation-max-decisions` retain their existing meanings.

Flat Position input selects
`recommendation_method: "information_set_search"` and supplies all nine strict
`information_set_search_settings` fields in JSON. There are no separate flat
CLI budget overrides. Existing `auto` remains PIMC first with its existing
Immediate fallback and never silently selects Information-set Search.

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

Capture transport is private and internal. It strictly resumes or creates one
explicit Match Workspace, binds only to `127.0.0.1`, and delegates one browser
operation at a time to existing Match Capture services followed by optimistic
atomic Save. Ordinary capture operations do not execute analysis. Issue #168's
separate explicit analysis actions invoke the existing Position or Historical
Application once; materialization executes no workflow.

Corpus transport is private and internal. It strictly resumes one explicit
non-empty Corpus or presents caller-ID initialization for an absent/empty root,
then composes existing Corpus import/selection and Dataset-v2 builders through
explicit browser actions. Strategy Teacher Report sources and prepared derived
artifacts are process-local. It executes no analysis and adds no Root workflow,
Public API, Schema, or derived persistence. See
[Learning Corpus browser workflows](learning_corpus_browser_workflows.md).

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
Capture parser misuse uses Code `2`; invalid existing Workspace, missing parent,
bind, or filesystem failures use Code `1`; a normal `Ctrl+C` shutdown uses Code
`0`. Browser validation uses HTTP `400`, security rejection `403`, unknown route
`404`, unsupported method `405`, revision or persistence conflict `409`, request
limit `413`, and generic internal failure `500`.

Corpus parser misuse uses Code `2`; invalid root/Store, missing parent, bind, or
filesystem failures use Code `1`; normal `Ctrl+C` uses Code `0`. Corpus browser
validation uses HTTP `400`, security rejection `403`, unavailable download `404`,
unsupported method `405`, revision/persistence/source-change conflict `409`,
request limit `413`, and generic internal failure `500`.

## Compatibility

The canonical implementation is under `skat_ai.cli`. Root `main.py` is a thin
compatibility facade that preserves its existing importable wrappers, validators,
formatters, Exit Code constants, `CliUsageError` alias, callable signatures, and
established monkeypatch seams. A patched Root seam affects Legacy execution but
does not require the installed Package CLI to import Root `main.py`.

Issue #162 keeps `skat_ai.cli.execution` and `skat_ai.cli.session` as explicit
compatibility facades while focused internal modules own parsing, validation,
Application adaptation, dispatch, transport, persistence/Checkpoint
orchestration, and presentation. The Session Assistant imports those focused
services rather than facade-private helpers. This changes no command, option,
output, Exit Code, Console Script, or compatibility version. See
[CLI internal architecture](cli_internal_architecture.md).

CLI functions and installed-CLI constants remain internal and are not stable
Public Python API exports. Issue #147 additively extends `skat_ai.api.v1`, Root
JSON Schema, and generated scenarios while preserving default Root JSON and the
flattened Public API envelope.

## Distribution validation

The existing single distribution validator builds one Wheel and one sdist. Its
clean environments verify exact Console Script metadata, module entry-point
inclusion, Root-main exclusion, help, version, Root JSON parity, normal failure
boundaries, provenance/quiet behavior, all 69 Schema Resources, and `py.typed`.
Issue #157 also verifies the public Session file namespace and Save/Load,
installed/module Session help, `new`/`apply`/`show`, Position analysis,
observation/review, Retrospective finalization, and an injected-I/O Assistant
smoke flow. Legacy Session parity is checked from the repository checkout. No
second Console Script is installed. Issue #165 additionally verifies Capture
resources, installed/module Capture help, loopback token bootstrap, browser
creation, Game start, Declaration, Card append, strict persistence Resume, and
clean shutdown. Legacy Capture parity remains a repository-checkout gate. The
local full check and CI invoke that validator once.
Issue #179 additionally verifies Corpus Web resource bytes, installed/module and
Legacy Corpus help, one-root initialization, strict Workspace import, explicit
Current selection, exact Match Report-source transfer, explicit Dataset-v2
preparation, all seven canonical downloads, invalidation, and shutdown. It adds
no second Console Script or 64th Schema.
Issue #189 additionally verifies installed/module/Legacy Information-set Search
help and execution parity, packaged four-Schema loading, strict Live execution,
Historical Review, and Training Dataset evaluation. It adds no eighth Root
workflow, second Console Script, or Public API contract version.

## Boundaries

Functional Issues #165 and #179 themselves changed no Package version, Root
workflow, Root parser meaning, second Console Script, publication state, default
Session path, Public API, Schema, example, or generated scenario. Issue #180
changes only Package version and matching release expectations to `0.16.0`.
Session persistence
files and explicit JSON outputs remain private caller-controlled data; concise
human output does not print complete private hands, full Skat, frozen Requests,
fingerprints, provenance entries, or file contents by default. The Match and
Learning Corpus browsers are private loopback-only local transports. Session
GUI/browser UI, hosted or remote browser deployment, online-platform integration,
cloud synchronization,
distributed locking,
encryption/key management, and automatic backups remain open.
Information-set Search remains bounded to its documented flat, Historical Review,
and Training Dataset evaluation routes. Multi-Step, Policy Comparison, Match
Capture, Strategy Teacher, and Replay Coaching classification integration remain
open for Issue #190 or later work.
See [Local Match Capture interface](local_match_capture_interface.md) and
[Learning Corpus browser workflows](learning_corpus_browser_workflows.md) and
[Public field provenance](public_field_provenance.md).
