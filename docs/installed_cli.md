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
skat-ai 0.12.0
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
`--version` is the only option added by Issue #142. The full current option list
is available through `--help`.

The CLI preserves this transport sequence:

1. Parse arguments.
2. Load the Root input.
3. Detect the Root workflow.
4. Validate CLI-only options.
5. Load optional external Opponent Statistics.
6. Construct internal Application options.
7. Execute the Application directly.
8. Write requested Root output.
9. Write a requested auxiliary Opponent Statistics export.
10. Print human-readable output unless `--quiet` is supplied.
11. Print file confirmations unless `--quiet` is supplied.

The CLI does not execute `skat_ai.api.v1` as an intermediate layer. It uses the
same internal Application orchestration as the Public Python API while retaining
CLI-specific file transport, validation, and presentation.

## Input and output

Use caller-owned paths with either installed form:

```powershell
skat-ai --input position.json
python -m skat_ai --input historical-game.json --output result.json --quiet
```

Without `--quiet`, successful workflows preserve the existing human-readable
headings, labels, ordering, and privacy boundaries. `--output` writes the
unchanged Root JSON document. `--quiet` suppresses successful human-readable
output and file confirmations but does not suppress errors.

Historical Opponent Statistics aggregation may write its separate reusable
artifact with `--export-opponent-statistics`. The auxiliary JSON remains outside
the primary Root output and uses the existing `opponent_statistics_input` shape.

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

The Package Root, `skat_ai.api`, `skat_ai.api.v1`, and `skat_ai.errors` export
surfaces are unchanged. CLI functions and installed-CLI constants are internal
and are not stable Public Python API exports. Root JSON, Public API behavior,
Schemas, examples, and generated scenarios are unchanged.

## Distribution validation

The existing single distribution validator builds one Wheel and one sdist. Its
two existing clean environments verify exact Console Script metadata, module
entry-point inclusion, Root-main exclusion, help, version, successful Root JSON
parity, one unavailable Result, one usage failure, one expected resource failure,
and exact CLI/Public API output parity. All 61 Schema Resources and `py.typed`
remain required. The local full check and CI invoke that validator once.

## Boundaries

Issue #142 adds no workflow, Root field, Schema, example, generated scenario,
interactive session, license metadata, Package-version change, publication, or
upload. It adds no Provenance option, output, Schema, export, or propagation.
Field-level Provenance integration remains separate open work.
