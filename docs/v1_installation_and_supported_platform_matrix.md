# v1 installation and supported-platform matrix

## Purpose

Issue #206 defines the validation-only installation and platform evidence for
the bounded SkatMind v1 candidate. It changes Package dependency metadata and
repository validation only. It does not change product behavior, Package version,
Public API contract, Root workflows, Console Scripts, Settlement, Schemas,
examples, generated outputs, Corpus downloads, persistence, license, or security
behavior.

The reusable runner is:

```text
scripts/validate_v1_supported_platform_matrix.py
```

It builds one Wheel and one sdist in an external temporary directory, creates
isolated external consumer environments, performs no publication, emits one
finite deterministic JSON object, and verifies that repository content is
unchanged.

## Runtime dependencies

The exact ordered direct runtime dependency declarations are:

```toml
dependencies = [
    "jsonschema>=4.23.0",
    "referencing>=0.31.0",
]
```

No upper bound, environment marker, lock file, vendored copy, or new development
dependency is added. The exact minimum-supported lane installs:

```text
jsonschema==4.23.0
referencing==0.31.0
```

Both are direct Production imports used by packaged-Schema validation. The
runner statically inventories every import in `src/skatmind` and repository
Legacy `main.py`, classifies standard-library and first-party imports, and
requires every remaining import root to have an explicit Package dependency
mapping. Availability through a transitive dependency is not sufficient.

The minimum Wheel and sdist cells install the artifact with `--no-deps`, install
the two exact direct floors while allowing their required transitive
dependencies, import both direct dependencies, verify that neither direct floor
was replaced by a newer version, and run `pip check`.

## Matrix contract

The validation-only matrix version is `1`. These constants are not exported from
public `skatmind.__all__`.

Supported platform identifiers, in order:

```text
windows_11_powershell_5_1_cpython_3_13
ubuntu_github_actions_cpython_3_13
```

Installation forms, in order:

```text
source
editable
wheel
sdist
```

Dependency lanes, in order:

```text
resolved
minimum_supported
```

Surface families, in order:

```text
package_metadata
public_python_api
installed_cli
module_cli
legacy_main
session
capture
corpus
package_resources
provenance
errors_and_exit_codes
```

The executable cells are all four resolved forms plus minimum-supported Wheel
and sdist. Source and Editable minimum cells are unnecessary because the exact
floor is an artifact acceptance boundary; both source forms remain covered by
normal dependency resolution.

## Validated behavior

Every resolved form validates:

* exact Package metadata, import namespace, Package Root, version, Python
  metadata, license, one Console Script, and absence of old active identities;
* all seven Root workflows through the Public API with output validation,
  warnings, actual artifacts, default Provenance omission, and complete opt-in
  Provenance;
* all seven Root workflows through installed, module, and repository Legacy CLI
  forms;
* stable public errors, all three Exit Codes, and all seven normal Result-state
  values without a machine-clock timeout trigger;
* Session API, file Save/Load, strict persistence, installed/module CLI,
  Checkpoint analysis/review, finalization, and Assistant smoke;
* Capture help, three packaged assets, authenticated loopback creation and
  mutation, strict reload, bounded analysis, and authenticated downloads;
* Corpus help, three packaged assets, authenticated loopback import and
  preparation, exact Report-source transfer, all three prepared families, and
  all ten authenticated canonical downloads;
* `py.typed`, all 71 byte-identical packaged Schema Resources, local reference
  resolution, exact legal files, and `pip check`.

Minimum Wheel and sdist cells additionally prove the exact direct floors, load
all 71 Schemas, execute all seven Root workflows, and exercise installed and
module CLI smoke. The existing deterministic injected-clock repository tests
remain the evidence for timing-sensitive `timeout`; the matrix does not add a
wall-clock timing test.

## Semantic parity

The runner compares the complete semantic smoke output across every executable
cell. Normalization is limited to existing approved
`wall_clock_elapsed_ms` values. Inputs use stable consumer filenames, so no
contract value requires path normalization. Recommendations, Candidate metrics,
Search counters, World counts, Settlement, Coaching, Tactical, Dataset, list,
Statistics, Provenance, warnings, and Artifact values are never normalized.

Successful JSON retains only compact statuses, exact dependency versions,
surface results, Root warning/artifact summaries, and a semantic digest. It
retains no filesystem path, token, username, hostname, timestamp, or elapsed-time
field. Temporary source, build, environment, consumer, Match, Session, and Corpus
files are removed. A content snapshot rejects repository mutation.

## Supported platforms

Package metadata remains Python `>=3.13`; the certified v1 runtime is CPython
3.13 only.

Windows acceptance uses Windows 11 and Windows PowerShell 5.1:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command `
  "py -3.13 scripts/validate_v1_supported_platform_matrix.py"
```

The final local repository check is separately run once through Windows
PowerShell 5.1:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command `
  "& { function python { py -3.13 @args }; .\scripts\check.ps1 }"
```

Ubuntu acceptance is the separate GitHub Actions job named exactly
`v1-supported-platform-matrix`. It uses `ubuntu-latest`, CPython 3.13, installs
only required build tooling, runs this matrix with the explicit Ubuntu expected-
platform identifier, performs no full pytest rerun, publishes nothing, and
uploads no Release asset. The existing `check` job remains unchanged in purpose
and continues to run the complete repository gate.

No macOS support, Python 3.14 certification, named browser-vendor matrix,
hardware requirement, cross-machine latency guarantee, Docker/remote-hosting
support, or Package-index publication is claimed.

## Gate result

The technical ledger prepared by Issue #206 is:

```text
P-34:
    satisfied

B-05:
    closed by Issue #206
```

That closure becomes effective only when all three conditions hold on the exact
candidate history:

1. The local Windows matrix and final full check pass.
2. The merged Ubuntu `check` job passes.
3. The merged Ubuntu `v1-supported-platform-matrix` job passes.

Until both merged Ubuntu jobs are green, Issue #206 remains open and the
maintainer must not claim completed Ubuntu evidence. After those conditions, the
53 required rows are 19 `satisfied`, 34
`satisfied_with_approved_bounded_scope`, and zero in each remaining required-row
status. The remaining blockers are B-06, B-07, and B-09, with B-09 outside the
53-row ledger. The exact next Issue is #207, **Perform the final technical
v1.0.0 release-readiness audit**.
