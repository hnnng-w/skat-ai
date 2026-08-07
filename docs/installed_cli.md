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

## Options and execution

All three forms share one canonical parser and the same option names, aliases,
destinations, actions, defaults, choices, repeatability, and semantic validation.
Issue #142 added `--version`; Issue #147 adds `--include-provenance`. The full
current option list is available through `--help`.

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
list `lot_required`, and Coaching `not_assessable`.

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
two existing clean environments verify exact Console Script metadata, module
entry-point inclusion, Root-main exclusion, help, version, successful Root JSON
parity, one unavailable Result, one usage failure, one expected resource failure,
and exact CLI/Public API output parity, including provenance opt-in and quiet
behavior. All 62 Schema Resources and `py.typed` remain required. The local full
check and CI invoke that validator once.

## Boundaries

Issue #142 adds no workflow, interactive session, license metadata, Package-
version change, publication, or upload. Issues #143 through #146 provide the
complete internal Result ledgers. Issue #147 exposes only one redacted Result
attachment plus actual-artifact attachments through `--include-provenance`, the
strict public Schema, and a concise terminal section. Consumed-input, decision,
intermediate-stage, and unredacted Application attachments remain unavailable.
See [Public field provenance](public_field_provenance.md).
