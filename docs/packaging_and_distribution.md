# Packaging and distribution

This document defines the installation-ready Package artifacts introduced by
Issue #141, the installed interfaces added by Issue #142, and the Issue #157
clean-install coverage for stable Session file transport and end-to-end Session
capture. Issue #200 freezes the repository-root Legacy CLI for Package 1.x; any
removal can occur no earlier than `2.0.0` after a prior warning and migration
note. Issue #204 applies the exact `AGPL-3.0-only` PEP 639 Package-license
boundary without changing product behavior or active Package identity.

## Build metadata

`pyproject.toml` uses the PEP 517 Setuptools backend:

```toml
[build-system]
requires = ["setuptools>=77.0.3"]
build-backend = "setuptools.build_meta"
```

Package discovery is rooted at `src/` and explicitly includes `skatmind*`.
Package Data is declared for:

* `skatmind/py.typed`;
* every `skatmind.schema_resources/*.schema.json` resource;
* `skatmind.capture_web` HTML, CSS, and JavaScript resources;
* `skatmind.corpus_web` HTML, CSS, and JavaScript resources;
* `skatmind.app_web` HTML, CSS, optional JavaScript, and German/English locale JSON resources.

The Package name remains `skatmind`, the Package version is `0.17.0`, and the
Python requirement remains `>=3.13`. The exact ordered direct runtime
dependencies are `jsonschema>=4.23.0` and `referencing>=0.31.0`. The `dev` extra
includes `build`, pytest, and Ruff.

The project declares exactly one Console Script:

```toml
[project.scripts]
skatmind = "skatmind.cli:main"
```

The project declares exactly:

```toml
license = "AGPL-3.0-only"
license-files = ["LICENSE", "COPYRIGHT"]
```

The project does not use `setup.py`, repository `setup.cfg`, non-Package
`data-files`, GUI Scripts, a second Console Script, authors, classifiers, or
publication URLs. It uses no deprecated license table, legacy unstructured
`License` metadata, or license Trove classifier. Setuptools may generate backend-
owned compatibility metadata inside an sdist; `pyproject.toml` remains
authoritative.

## License files

Root `LICENSE` is the complete unmodified GNU AGPL version 3 text and root
`COPYRIGHT` contains exactly `Copyright (C) 2026 Henning Wiese`. Both are UTF-8
without a BOM, LF-only, and end with one LF. Their authoritative decision,
source, deterministic license digest, dependency/asset audit, network-use
boundary, and contributor boundary are documented in
[v1 Package license](v1_package_license.md).

Core Metadata version `2.4` or later contains exactly:

```text
License-Expression: AGPL-3.0-only
License-File: LICENSE
License-File: COPYRIGHT
```

Wheel and installed locations are
`<distribution>.dist-info/licenses/LICENSE` and
`<distribution>.dist-info/licenses/COPYRIGHT`. The sdist places both exact files
at its root. The Wheel `RECORD` includes their exact SHA-256 hashes and sizes.

## Installed entry points

The three supported forms are:

```text
skatmind
python -m skatmind
python main.py
```

The first two are installed Package interfaces. `skatmind/__main__.py` delegates
module execution to the same `skatmind.cli:main` implementation. Root `main.py`
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
and downloads are not. Issue #180 changes only Package version and matching
release expectations to `0.16.0`.
Issue #198 changes only Package version and matching Release-candidate
expectations to `0.17.0`. The maintainer subsequently published `v0.17.0` on
2026-08-25 at `8187fbe`, and Issue #199 synchronizes that publication without
changing Package metadata or behavior.

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

The 71 files under repository `schemas/` are the authoritative JSON Schemas for
the published `v0.17.0` Package baseline.
Issue #156 adds strict standalone `session.schema.json`; Issue #157 extends that
same file for Session creation, file API, observation, and review contracts
without adding a 64th Schema. Wheel and sdist contain its byte-identical Package
Resource mirror. The historical published `v0.16.0`, `v0.15.0`, and `v0.14.0`
baselines have 63 Schemas; the historical published `v0.13.0` baseline remains
at 62 Schemas. Issues #186, #189, #192, and #194 add the eight published
`v0.17.0` Schemas.
Every `*.schema.json` file is mirrored without transformation into:

```text
src/skatmind/schema_resources/
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
private `skatmind.schema_resources` Package. It no longer derives a repository
root, reads the authoritative source directory at runtime, depends on the current
working directory, or requires concrete filesystem paths.

Loading remains lazy. Importing `skatmind` or `skatmind.api.v1` does not enumerate
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

The private app, Capture Web, and Learning Corpus transports load HTML templates,
CSS, optional vanilla JavaScript, and unified-app translation catalogs through
`importlib.resources`. Assets are lazy, current-working-directory independent,
locally packaged, and contain no external dependency, CDN, font, image, or
build-system requirement. Issue #210 adds the app template and CSS; Issue #216
adds strict German and English catalog resources; Issues #168 and #179 retain the
Capture and Corpus assets. Match reports, Corpus Report sources, and
prepared values remain process memory, and downloads are HTTP responses rather
than Package Data or installed writable files.

## Typing and version metadata

`src/skatmind/py.typed` marks the distribution as typed under PEP 561. It adds no
runtime type-checker dependency.

The Package Root exports `skatmind.__version__`. Installed and Editable
distributions resolve it through:

```python
importlib.metadata.version("skatmind")
```

The current value is `0.17.0`. A source-only environment without installed
distribution metadata returns `0+unknown` without reading `pyproject.toml` or
another repository file. Package version remains independent of API contract,
Application, Schema, Provenance, and Domain versions. It is not added to API
Results or `ApiVersionInfoV1`.

## Artifact validation

`scripts/validate_distribution_artifacts.py` is the single integration gate for
real distribution builds. It validates exactly one Wheel and one sdist.

Wheel inspection verifies:

* PEP 639-capable core metadata, exact `AGPL-3.0-only`, exactly two declared
  legal files, no legacy `License`, and no classifier;
* exact `.dist-info/licenses/` legal-file bytes and their complete Wheel
  `RECORD` hashes and sizes;
* the declared runtime and development dependencies;
* every `skatmind` Python module;
* `py.typed` and all 71 byte-identical schema resources;
* exact Capture Web template, CSS, and JavaScript resource bytes;
* exact Corpus Web template, CSS, and JavaScript resource bytes;
* exact unified-app template and CSS resource bytes;
* exact unified-app German and English catalog bytes plus strict key and
  interpolation-placeholder parity;
* a valid pure-Python Wheel and RECORD;
* exact `skatmind = skatmind.cli:main` Console Script metadata and
  `skatmind/__main__.py`;
* absence of repository tests, examples, generated outputs, root `main.py`, a
  second Console Script, GUI Script, or script payload.

sdist inspection verifies:

* `pyproject.toml`, `README.md`, exact root `LICENSE` and `COPYRIGHT`, Package
  sources, `py.typed`, and every schema, Capture Web, Corpus Web, and unified-app
  resource;
* build and core metadata sufficient to build and install the same Package;
* exact Console Script metadata and `src/skatmind/__main__.py`;
* absence of a source-authored `setup.py`, root `main.py`, a second command, and
  any GUI Script.

For each artifact, the script creates a separate clean virtual environment,
installs from an external working directory with `PYTHONPATH` removed, and
verifies:

* imports resolve from that environment's `site-packages`;
* `skatmind.__version__ == "0.17.0"`;
* exact installed `License-Expression` and `License-File` metadata plus exact
  `.dist-info/licenses/LICENSE` and `.dist-info/licenses/COPYRIGHT` bytes;
* `py.typed` is locatable;
* every installed schema has exact repository filename and byte parity, valid
  UTF-8 and JSON, and its unchanged `$id`;
* Root input/output references resolve locally with output validation enabled;
* `parse_request()` and `execute_document()` run all seven Root workflows with
  default Provenance omission, complete opt-in Provenance, warnings, and actual
  artifacts;
* `skatmind --help`, `skatmind --version`, `python -m skatmind --help`, and
  `python -m skatmind --version` succeed with no repository or `PYTHONPATH`;
* installed and module CLI quiet JSON exactly matches the Public API Root result;
* `skatmind.api.v1.session.files` imports and public Session Save/Load preserve
  strict resume and path-free Results;
* installed `skatmind session --help` and module
  `python -m skatmind session --help` succeed;
* installed `skatmind capture --help` and module
  `python -m skatmind capture --help` succeed;
* installed `skatmind corpus --help` and module
  `python -m skatmind corpus --help` succeed with exact options and default port;
* installed/module `app --help` and repository Legacy `app --help` preserve exact
  launch options and invocation identities;
* packaged app resources load byte-for-byte, strict German and English catalogs
  have exact parity, and one isolated in-process app server creates only the
  three managed categories without creating a profile, authenticates all seven
  navigation routes, serves local CSS, resolves browser-derived German, saves an
  explicit language with saved-language precedence, reloads the profile,
  executes one guided Analyze action, downloads its retained Request/Result
  bytes, enters guided Review, and shuts down;
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
  Decision Report source, prepares the existing, Tactical, and Coaching families,
  authenticates all ten byte-exact canonical downloads, and invalidates them
  after source removal;
* installed, module, and Public Session API results have parity where
  applicable;
* a valid unavailable Dataset Preparation Result remains successful;
* one unknown option returns usage Code `2` and one missing input returns expected
  failure Code `1`;
* no GUI Script, second Console Script, or installed root `main` module exists.

Wheel and sdist smoke Results must be equal. Every clean environment now also
runs `pip check`, imports both direct runtime dependencies, and records their
exact installed versions. Legacy Session CLI parity remains a
repository-checkout gate because root `main.py` is intentionally not installed.
Legacy Capture and Corpus help parity are repository-checkout gates for the same
reason.

Issue #206 adds the separate reusable
`scripts/validate_v1_supported_platform_matrix.py` around these existing smoke
helpers instead of duplicating them. It validates resolved source, Editable,
Wheel, and sdist installations, plus Wheel and sdist installed with `--no-deps`
against exact `jsonschema==4.23.0` and `referencing==0.31.0` floors. Every cell
runs outside the repository, runs `pip check`, and participates in complete
semantic comparison with normalization limited to approved
`wall_clock_elapsed_ms` values. Static import inventory requires every
Production third-party import to match Package metadata. Content snapshots reject
repository mutation, and successful JSON retains no path, credential, machine-
identity, timestamp, or elapsed-time field. See
[v1 installation and supported-platform matrix](v1_installation_and_supported_platform_matrix.md).

## Local and CI gates

The complete local check runs, in fail-fast order:

1. Ruff;
2. packaged-schema parity;
3. Root and Session example schema validation;
4. validation of all 98 generated-output scenarios;
5. distribution artifact and clean-install validation;
6. pytest.

GitHub Actions retains the existing `check` job with Python 3.13 and the Editable
`.[dev]` installation, then runs the same parity and distribution scripts in
addition to Ruff, schema, generated-output, and pytest gates. The separate job
named exactly `v1-supported-platform-matrix` uses `ubuntu-latest` and Python 3.13,
installs only required build tooling, runs the standalone matrix, and does not
rerun full pytest. No CI step uploads or publishes an artifact.

## Remaining boundaries

For the bounded v1 Package, release acceptance uses CPython 3.13 on Windows 11
through Windows PowerShell 5.1 and on Ubuntu through the dedicated GitHub Actions
job. Package metadata remains `>=3.13`, but no Python 3.14, macOS, hardware,
named-browser, or cross-machine latency matrix is claimed. Issue #206 reconciles
both direct Production imports with exact lower bounds and implements all-seven-
workflow source/Editable/Wheel/sdist evidence. P-34 is `satisfied`, and B-05 is
closed after the local Windows matrix/full check and merged Ubuntu `check` and
`v1-supported-platform-matrix` jobs pass. Issue #204 intentionally changed no
dependency; Issue #206 owns the later metadata correction.

Issue #142 added the installed `skat-ai` command and `python -m skat_ai` without a
public schema-resource API, new workflow, Root-output metadata, Provenance field,
Package-version change, or Package publication. Issue #147 subsequently added
opt-in bounded public Provenance without publication. Issue #157 completes the
functional `v0.14.0` Session milestone, and Issue #158 completed Package version
`0.14.0` and Release-documentation preparation. The published `v0.14.0` baseline
at commit `d5589f8` has 63 authoritative and packaged Schemas and 85 generated-
output scenarios, while the historical `v0.13.0` 77 scenarios remain unchanged.

Issue #204 applies `AGPL-3.0-only`, closes B-04, and leaves Package and Release
publication human-controlled. It adds no Package-index or PyPI publication.
Issue #205 subsequently changes the active distribution, import namespace,
module, and sole Console Script to `skatmind`, changes the version display to
`SkatMind 0.17.0`, preserves Package version `0.17.0`, and closes B-08. Session
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
workflow planned for `v0.16.0` without changing the then-current Package version
`0.15.0`, the one Console Script, seven Root workflows, 63 Schemas/resources, six
Session examples, or 85 generated outputs. Issue #180 prepared Package `0.16.0`,
matching assertions, Changelog, and Release-state documentation without product
behavior changes. The maintainer published `v0.16.0` manually on 2026-08-18 at
commit `91b1360`, and Issue #181 synchronizes publication status without product
functionality. GitHub Releases is the authoritative publication record; no
Package-index or PyPI publication is claimed. Derived artifacts remain non-
persisted and private.
Issue #197 records the documentation-only `v0.17.0` scope and Release-readiness
audit. Issue #198 prepared Package `0.17.0`, matching assertions, Changelog, and
Release-candidate documentation without changing product behavior, dependencies,
the build backend, Package Data, or non-Package contract versions. The maintainer
published `v0.17.0` manually on 2026-08-25 at `8187fbe`; Issue #199 synchronizes
the post-publication documentation only. GitHub Releases is authoritative, and
no Package-index or PyPI publication is claimed.

The authoritative license boundary is in [v1 Package license](v1_package_license.md).
The executable v1 packaging, platform, and distribution matrix is in
[v1 installation and supported-platform matrix](v1_installation_and_supported_platform_matrix.md),
and its Gate classification is in the
[v1.0 scope and traceability audit](v1_0_scope_and_traceability_audit.md).
