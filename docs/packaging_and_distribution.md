# Packaging and distribution

This document defines the installation-ready Package artifacts introduced by
Issue #141, the installed interfaces added by Issue #142, and the Issue #157
clean-install coverage for stable Session file transport and end-to-end Session
capture. The repository-root Legacy CLI remains supported through at least
`v1.0.0`.

## Build metadata

`pyproject.toml` uses the PEP 517 Setuptools backend:

```toml
[build-system]
requires = ["setuptools>=77.0.3"]
build-backend = "setuptools.build_meta"
```

Package discovery is rooted at `src/` and explicitly includes `skat_ai*`.
Package Data is declared for:

* `skat_ai/py.typed`;
* every `skat_ai.schema_resources/*.schema.json` resource;
* `skat_ai.capture_web` HTML, CSS, and JavaScript resources;
* `skat_ai.corpus_web` HTML, CSS, and JavaScript resources.

The Package name remains `skat-ai`, the Package version is `0.15.0`, the
Python requirement remains `>=3.13`, and `jsonschema` remains the runtime
dependency. The `dev` extra includes `build`, pytest, and Ruff.

The project declares exactly one Console Script:

```toml
[project.scripts]
skat-ai = "skat_ai.cli:main"
```

The project does not use `setup.py`, repository `setup.cfg`, non-Package
`data-files`, GUI Scripts, a second Console Script, authors, classifiers,
publication URLs, or license metadata. Setuptools may generate backend-owned
compatibility metadata inside an sdist; `pyproject.toml` remains authoritative.

## Installed entry points

The three supported forms are:

```text
skat-ai
python -m skat_ai
python main.py
```

The first two are installed Package interfaces. `skat_ai/__main__.py` delegates
module execution to the same `skat_ai.cli:main` implementation. Root `main.py`
is a repository-only Legacy facade and is not installed. All three share option,
validation, Application execution, JSON, presentation, error, and Exit Code
semantics. Help changes only its command identity and examples: installed and
module help uses generic caller paths, while Legacy help may use repository
`examples/...` paths. See [Installed CLI](installed_cli.md).

Issue #157 adds a leading `session` command family to all three forms through the
same Package-owned implementation and a separate Session parser. Its 12
subcommands cover file creation/resume, Command application, Undo/correction,
automatic Checkpoint collection, Request export, explicit Position analysis,
Checkpoint review, Historical finalization, and the phase-aware Assistant. It
adds no second Console Script and no eighth Engine Root workflow; explicit
analysis reuses the existing Position or Historical Application handler once.
Issue #165 adds leading `capture` dispatch before Session and Root, using the
same Console Script for the loopback-only one-Workspace browser transport.
Issue #168 extends that already packaged private browser with explicit analysis,
ephemeral reports, and authenticated local downloads. It adds no Console Script,
CLI option, Root workflow, public import, Schema resource, or Package Data kind.
Issue #179 adds leading `corpus` dispatch before Capture, using the same Console
Script for one explicit private Learning Corpus root. Its local HTML, CSS, and
JavaScript are Package Data; its process-local Report sources, prepared artifacts,
and downloads are not. Package version remains `0.15.0`.

## Building artifacts

Install the Editable development environment:

```powershell
python -m pip install -e ".[dev]"
```

Build one Wheel and one sdist manually when local artifact inspection is needed:

```powershell
python -m build
```

That direct command writes to `dist/`. Normal project checks instead use:

```powershell
python scripts/validate_distribution_artifacts.py
```

The validation script copies the source tree to a temporary directory, invokes
`python -m build` there, and removes the artifacts and clean environments when
the check finishes. It does not publish either artifact.

## Schema resources

The 63 files under repository `schemas/` are the authoritative JSON Schemas.
Issue #156 adds strict standalone `session.schema.json`; Issue #157 extends that
same file for Session creation, file API, observation, and review contracts
without adding a 64th Schema. Wheel and sdist contain its byte-identical Package
Resource mirror. The published `v0.14.0` baseline has 63 Schemas; the historical
published `v0.13.0` baseline remains at 62 Schemas.
Every `*.schema.json` file is mirrored without transformation into:

```text
src/skat_ai/schema_resources/
```

Synchronize the mirror after an intentional authoritative schema change:

```powershell
python scripts/sync_packaged_schemas.py
```

Check the mirror without modifying files:

```powershell
python scripts/sync_packaged_schemas.py --check
```

Check mode validates the exact filename set and exact bytes. Missing, additional,
and changed resources produce deterministic diagnostics. The local check and CI
run check mode before schema and distribution validation.

## Runtime loading

The public Python API loads schemas through `importlib.resources` from the
private `skat_ai.schema_resources` Package. It no longer derives a repository
root, reads the authoritative source directory at runtime, depends on the current
working directory, or requires concrete filesystem paths.

Loading remains lazy. Importing `skat_ai` or `skat_ai.api.v1` does not enumerate
or read schema resources. The first input or output validation builds the
corresponding cached Draft 2020-12 validator from every packaged resource.

The registry:

* validates UTF-8, JSON object shape, supported Schema dialect, and schema shape;
* requires unique non-empty `$id` values;
* resolves Root input, Root output, and artifact references from local packaged
  resources;
* rejects all unregistered retrieval rather than accessing the network;
* retains the input `FormatChecker`;
* retains deterministic first-error selection and canonical RFC 6901 paths.

No schema-loading helper is exported publicly.

The private Capture Web and Learning Corpus transports also load their HTML
templates, CSS, and vanilla JavaScript through `importlib.resources`. Assets are
lazy, current-working-directory independent, locally packaged, and contain no
external dependency, CDN, font, image, or build-system requirement.
Issue #168 uses the Capture assets and discovered Python Package modules; Issue
#179 uses the separate Corpus assets. Match reports, Corpus Report sources, and
prepared values remain process memory, and downloads are HTTP responses rather
than Package Data or installed writable files.

## Typing and version metadata

`src/skat_ai/py.typed` marks the distribution as typed under PEP 561. It adds no
runtime type-checker dependency.

The Package Root exports `skat_ai.__version__`. Installed and Editable
distributions resolve it through:

```python
importlib.metadata.version("skat-ai")
```

The current value is `0.15.0`. A source-only environment without installed
distribution metadata returns `0+unknown` without reading `pyproject.toml` or
another repository file. Package version remains independent of API contract,
Application, Schema, Provenance, and Domain versions. It is not added to API
Results or `ApiVersionInfoV1`.

## Artifact validation

`scripts/validate_distribution_artifacts.py` is the single integration gate for
real distribution builds. It validates exactly one Wheel and one sdist.

Wheel inspection verifies:

* valid core metadata and the declared runtime and development dependencies;
* every `skat_ai` Python module;
* `py.typed` and all 63 byte-identical schema resources;
* exact Capture Web template, CSS, and JavaScript resource bytes;
* exact Corpus Web template, CSS, and JavaScript resource bytes;
* a valid pure-Python Wheel and RECORD;
* exact `skat-ai = skat_ai.cli:main` Console Script metadata and
  `skat_ai/__main__.py`;
* absence of repository tests, examples, generated outputs, root `main.py`, a
  second Console Script, GUI Script, or script payload.

sdist inspection verifies:

* `pyproject.toml`, `README.md`, Package sources, `py.typed`, and every schema,
  Capture Web, and Corpus Web resource;
* build and core metadata sufficient to build and install the same Package;
* exact Console Script metadata and `src/skat_ai/__main__.py`;
* absence of a source-authored `setup.py`, root `main.py`, a second command, and
  any GUI Script.

For each artifact, the script creates a separate clean virtual environment,
installs from an external working directory with `PYTHONPATH` removed, and
verifies:

* imports resolve from that environment's `site-packages`;
* `skat_ai.__version__ == "0.15.0"`;
* `py.typed` is locatable;
* every installed schema has exact repository filename and byte parity, valid
  UTF-8 and JSON, and its unchanged `$id`;
* Root input/output references resolve locally with output validation enabled;
* `parse_request()` and `execute_document()` run a compact copied existing
  Opponent Statistics Root example;
* `skat-ai --help`, `skat-ai --version`, `python -m skat_ai --help`, and
  `python -m skat_ai --version` succeed with no repository or `PYTHONPATH`;
* installed and module CLI quiet JSON exactly matches the Public API Root result;
* `skat_ai.api.v1.session.files` imports and public Session Save/Load preserve
  strict resume and path-free Results;
* installed `skat-ai session --help` and module
  `python -m skat_ai session --help` succeed;
* installed `skat-ai capture --help` and module
  `python -m skat_ai capture --help` succeed;
* installed `skat-ai corpus --help` and module
  `python -m skat_ai corpus --help` succeed with exact options and default port;
* Session `new`, `apply`, and `show` operate through a caller-selected file;
* Session-triggered Position analysis, Checkpoint observation/review, and
  Retrospective finalization reuse the existing Application workflows;
* the Session Assistant completes a deterministic smoke flow through injected
  input/output functions;
* one in-process loopback Capture server performs token bootstrap, renders the
  absent-Workspace page, creates and persists a Workspace, sets and clears one
  Match-bound Player Statistics Snapshot, starts a Game, sets a Declaration,
  appends one automatically attributed Card, strictly reloads the file, and
  shuts down cleanly;
* installed Match analysis imports prepare a partial safe Decision, execute
  Immediate and bounded Search Position paths, execute strict Historical Review,
  apply eligible actor-relative Profiles through existing behavior, prepare
  materialization, render the explicit browser controls, authenticate exact Root,
  materialization, and Historical-collection downloads, and invalidate reports
  after an applied mutation;
* one in-process loopback Corpus server initializes an explicit root, strictly
  imports the persisted Match Workspace, preserves explicit Current selection,
  prepares empty-Teacher Dataset-v2 values, strictly imports the exact executed
  Decision Report source, prepares the complete seven-artifact set, authenticates
  byte-exact canonical downloads, and invalidates them after source removal;
* installed, module, and Public Session API results have parity where
  applicable;
* a valid unavailable Dataset Preparation Result remains successful;
* one unknown option returns usage Code `2` and one missing input returns expected
  failure Code `1`;
* no GUI Script, second Console Script, or installed root `main` module exists.

Wheel and sdist smoke Results must be equal. Legacy Session CLI parity remains a
repository-checkout gate because root `main.py` is intentionally not installed.
Legacy Capture and Corpus help parity are repository-checkout gates for the same
reason.

## Local and CI gates

The complete local check runs, in fail-fast order:

1. Ruff;
2. packaged-schema parity;
3. Root and Session example schema validation;
4. validation of all 85 generated-output scenarios;
5. distribution artifact and clean-install validation;
6. pytest.

GitHub Actions retains Python 3.13 and the Editable `.[dev]` installation, then
runs the same parity and distribution scripts in addition to the existing Ruff,
schema, generated-output, and pytest gates. Installed CLI checks reuse the same
Wheel/sdist build and two clean environments; no duplicate build or distribution
step exists. No CI step uploads or publishes an artifact.

## Remaining boundaries

Issue #142 added the installed `skat-ai` command and `python -m skat_ai` without a
public schema-resource API, new workflow, Root-output metadata, Provenance field,
Package-version change, or Package publication. Issue #147 subsequently added
opt-in bounded public Provenance without publication. Issue #157 completes the
functional `v0.14.0` Session milestone, and Issue #158 completed Package version
`0.14.0` and Release-documentation preparation. The published `v0.14.0` baseline
at commit `d5589f8` has 63 authoritative and packaged Schemas and 85 generated-
output scenarios, while the historical `v0.13.0` 77 scenarios remain unchanged.

The Package license decision remains unresolved, so no license
metadata is declared. Package and release publication remain human-controlled. Session
file paths are caller-selected; no default directory, second Console Script,
remote browser deployment, online-platform adapter, cloud synchronization,
distributed locking, encryption/key management, or automatic backup policy is
added. The Issue #165 browser is a private loopback-only local transport; it is
not a hosted GUI or Public Match API. Issue #168 completes the functional
`v0.15.0` local Match Capture milestone without itself changing the Package.
Issue #169 completed Package version `0.15.0`, matching assertions, Changelog,
and release-state documentation as Release preparation without product behavior
changes. The maintainer published `v0.15.0` manually at commit `ec1c154`, and
Issue #170 synchronizes publication status. Public
Match API and Schema/data workflow, database/remote deployment, and public Match
exports remain open. No Package-index or PyPI publication is claimed.
Issue #179 completes the functional private local Learning Corpus/Dataset-v2
workflow planned for `v0.16.0` without changing Package version `0.15.0`, the one
Console Script, seven Root workflows, 63 Schemas/resources, six Session examples,
or 85 generated outputs. `v0.16.0` Release preparation and publication remain
open; derived artifacts remain non-persisted and private.
