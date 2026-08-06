# Packaging and distribution

This document defines the installation-ready Package artifacts introduced by
Issue #141. It covers the library distribution only. The repository-root legacy
CLI remains supported, but no installed command or `python -m skat_ai` entry
point is provided yet.

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
* every `skat_ai.schema_resources/*.schema.json` resource.

The Package name remains `skat-ai`, the Package version remains `0.12.0`, the
Python requirement remains `>=3.13`, and `jsonschema` remains the runtime
dependency. The `dev` extra includes `build`, pytest, and Ruff.

The project does not use `setup.py`, repository `setup.cfg`, non-Package
`data-files`, Console Scripts, GUI Scripts, authors, classifiers, publication
URLs, or license metadata. Setuptools may generate backend-owned compatibility
metadata inside an sdist; `pyproject.toml` remains authoritative.

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

The 61 files under repository `schemas/` remain the authoritative JSON Schemas.
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

## Typing and version metadata

`src/skat_ai/py.typed` marks the distribution as typed under PEP 561. It adds no
runtime type-checker dependency.

The Package Root exports `skat_ai.__version__`. Installed and Editable
distributions resolve it through:

```python
importlib.metadata.version("skat-ai")
```

The current value is `0.12.0`. A source-only environment without installed
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
* `py.typed` and all 61 byte-identical schema resources;
* a valid pure-Python Wheel and RECORD;
* absence of repository tests, examples, generated outputs, root `main.py`, and
  installed scripts.

sdist inspection verifies:

* `pyproject.toml`, `README.md`, Package sources, `py.typed`, and every schema
  resource;
* build and core metadata sufficient to build and install the same Package;
* absence of a source-authored `setup.py` and any declared installed CLI.

For each artifact, the script creates a separate clean virtual environment,
installs from an external working directory with `PYTHONPATH` removed, and
verifies:

* imports resolve from that environment's `site-packages`;
* `skat_ai.__version__ == "0.12.0"`;
* `py.typed` is locatable;
* every installed schema has exact repository filename and byte parity, valid
  UTF-8 and JSON, and its unchanged `$id`;
* Root input/output references resolve locally with output validation enabled;
* `parse_request()` and `execute_document()` run a compact copied existing
  Opponent Statistics Root example;
* no Console Script, GUI Script, `skat_ai.__main__`, or installed root `main`
  module exists.

Wheel and sdist smoke Results must be equal.

## Local and CI gates

The complete local check runs, in fail-fast order:

1. Ruff;
2. packaged-schema parity;
3. Root and example schema validation;
4. generated-output validation;
5. distribution artifact and clean-install validation;
6. pytest.

GitHub Actions retains Python 3.13 and the Editable `.[dev]` installation, then
runs the same parity and distribution scripts in addition to the existing Ruff,
schema, generated-output, and pytest gates. No CI step uploads or publishes an
artifact.

## Remaining boundaries

Issue #141 does not add the installed `skat-ai` command, `python -m skat_ai`, a
public schema-resource API, a new workflow, a Provenance field, or Package
publication. The Package license decision also remains unresolved, so no license
metadata is declared. Publication and all release actions remain human-controlled.
