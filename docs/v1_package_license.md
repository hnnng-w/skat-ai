# v1 Package license

## Maintainer decision

Issue #204 licenses the current Package under the GNU Affero General Public
License version 3 only:

| Field | Exact value |
| --- | --- |
| License | GNU Affero General Public License v3.0 only |
| SPDX expression | `AGPL-3.0-only` |
| Copyright | `Copyright (C) 2026 Henning Wiese` |

`AGPL-3.0-only` is deliberate. The project does not grant the
`AGPL-3.0-or-later` option. The generic application example inside the
unmodified license text does not change the project's exact SPDX grant.

The complete text is the SPDX license-list plain-text copy of the official GNU
AGPL version 3 text:

* GNU: <https://www.gnu.org/licenses/agpl-3.0.html>
* SPDX definition: <https://spdx.org/licenses/AGPL-3.0-only.html>
* exact plain-text source: <https://raw.githubusercontent.com/spdx/license-list-data/main/text/AGPL-3.0-only.txt>

Repository `LICENSE` is UTF-8 without a BOM, uses LF line endings and one final
LF, and has this deterministic SHA-256 digest:

```text
d8a6cc31abc16b6748c7a21f21611f5a1ec33f67d22ca23d7da1c19b95496bee
```

Repository `COPYRIGHT` has exactly the approved one-line notice and one final
LF. It intentionally contains no product name, company attribution, rights
assignment, support promise, or additional condition.

## Package metadata

The PEP 639 source contract in `pyproject.toml` is:

```toml
license = "AGPL-3.0-only"
license-files = ["LICENSE", "COPYRIGHT"]
```

PEP 639 and Setuptools guidance are the metadata references:

* <https://peps.python.org/pep-0639/>
* <https://setuptools.pypa.io/en/latest/userguide/license_migration.html>

Wheel, sdist, and installed Core Metadata use version `2.4` or a later
compatible version and contain one `License-Expression: AGPL-3.0-only` header
and exactly two `License-File` headers in the declared order. They contain no
legacy unstructured `License` header and no license classifier.

The exact legal-file locations are:

| Surface | `LICENSE` | `COPYRIGHT` |
| --- | --- | --- |
| Repository | `LICENSE` | `COPYRIGHT` |
| Wheel | `<distribution>.dist-info/licenses/LICENSE` | `<distribution>.dist-info/licenses/COPYRIGHT` |
| sdist | `<sdist-root>/LICENSE` | `<sdist-root>/COPYRIGHT` |
| Installed project | `<distribution>.dist-info/licenses/LICENSE` | `<distribution>.dist-info/licenses/COPYRIGHT` |

The Wheel `RECORD` covers both installed files with exact SHA-256 hashes and
sizes. `scripts/validate_distribution_artifacts.py` validates repository bytes,
source metadata, both built artifacts, Wheel `RECORD`, and both clean-installed
projects without changing the existing Package, module, Schema, browser-asset,
CLI, workflow, or download contracts. Focused tests use deterministic local
fixtures and perform no network access.

No author, classifier, homepage, domain, project URL, second Console Script, or
GUI Script metadata is added. Issue #204 originally preserved the then-active
Package identity. Issue #205 subsequently changes the current distribution and
import namespace to `skatmind` and the one Console Script to
`skatmind = skatmind.cli:main`. Package version remains `0.17.0` and Python
metadata remains `>=3.13`.

## Direct dependency audit

The exact declared build, runtime, and development dependency inventory was
reviewed for this bounded Package decision. No dependency source is vendored in
the repository and Issue #204 changes no dependency declaration.

| Declaration | Purpose and scope | Upstream license source | Upstream license | Vendored | Bounded distribution conclusion |
| --- | --- | --- | --- | --- | --- |
| `setuptools>=77.0.3` | PEP 517 build backend; build time | <https://github.com/pypa/setuptools/blob/main/LICENSE> | MIT | No | Its permissive terms do not conflict with distributing this project's source and artifacts under `AGPL-3.0-only`. |
| `jsonschema>=4.23.0` | JSON Schema validation; direct runtime dependency | <https://github.com/python-jsonschema/jsonschema/blob/main/COPYING> | MIT | No | Its permissive terms do not conflict with the selected project license. |
| `referencing>=0.31.0` | Local JSON Schema resource registry and reference resolution; direct runtime dependency | <https://github.com/python-jsonschema/referencing/blob/main/COPYING> | MIT | No | Its permissive terms do not conflict with the selected project license. |
| `build>=1.2.2` | Wheel/sdist frontend; development only | <https://github.com/pypa/build/blob/main/LICENSE> | MIT | No | It is development tooling and its permissive terms do not conflict with the selected project license. |
| `pytest>=9.0.0` | Automated tests; development only | <https://github.com/pytest-dev/pytest/blob/main/LICENSE> | MIT | No | It is development tooling and its permissive terms do not conflict with the selected project license. |
| `ruff>=0.14.0` | Linting and formatting; development only | <https://github.com/astral-sh/ruff/blob/main/LICENSE> | MIT | No | It is development tooling and its permissive terms do not conflict with the selected project license. |

Issue #204 itself changed no dependency. Issue #206 subsequently reconciles the
two direct Production imports with the exact ordered declarations above and
validates the minimum-supported versions `jsonschema==4.23.0` and
`referencing==0.31.0` in isolated Wheel and sdist environments. Neither direct
dependency is vendored and neither has an upper bound. Both remain MIT-licensed;
no license incompatibility is identified. Issue #206 closes B-05 after the local
Windows and merged Ubuntu evidence passes. Future dependency upgrades still
require normal dependency and license review.

This is a bounded repository audit, not an automated legal opinion or a claim
about every future transitive version.

## Bundled asset audit

The current bundled and repository evidence families were reviewed as follows:

| Family | Audit result |
| --- | --- |
| Python source | Project source under `src/skatmind`; no third-party source tree or generated vendor directory found. |
| JSON Schemas | The 71 authoritative files under `schemas/` and their byte-identical Package Resource mirrors are project schemas; no third-party metaschema is bundled. |
| Capture HTML/CSS/JavaScript | The template, stylesheet, and vanilla JavaScript are first-party Package Data with no framework, CDN, font, image, or copied library. |
| Corpus HTML/CSS/JavaScript | The template, stylesheet, and vanilla JavaScript are first-party Package Data with no framework, CDN, font, image, or copied library. |
| benchmark fixtures | The two repository-local JSON corpora are deterministic project evidence, not third-party source or data. |
| examples | Repository-authored JSON requests and Session records; no third-party asset was identified. |
| documentation assets | Repository-authored Markdown only; no bundled font, image, PDF, or copied documentation package was identified. |
| generated and copied material | Generated-output fixtures are derived from project examples and code. The unmodified AGPL text itself is the only newly copied legal text. |

No incompatible or unresolved bundled license was found. The audit found no
concrete requirement for a third-party `NOTICE` file, so none is added.

## Network and reuse boundary

`AGPL-3.0-only` does not prohibit commercial use. The maintainer currently does
not plan commercial sale, but that intent is not an added license condition.
Modified versions used to provide remote network interaction remain subject to
the AGPL network-source provisions in the exact license text.

Already released AGPL versions remain available under the rights granted with
those versions. Future maintainer-owned versions may be offered under different
or additional licenses only when the maintainer owns the rights required to do
so. External contributions can constrain later relicensing unless their rights
are separately addressed. The `COPYRIGHT` file makes no contributor-rights
assignment claim.

No hosted or remote service is claimed. Capture and Corpus remain private,
loopback-only local transports. Issue #204 adds no legal-notice control,
network-source endpoint, hosted deployment, or browser behavior. A future hosted
deployment requires a separate compliance and security review.

The project makes no Package-index or PyPI publication, hosted-service, support,
or warranty claim. This documentation records the project boundary and is not
individualized legal advice.

## v1 gates and rename

Issue #204 closes B-04 after applying the exact legal files, PEP 639 metadata,
artifact validation, tests, and documentation. The separate maintainer decision
for the future product is `SkatMind`, with repository `hnnng-w/skatmind`,
distribution and import namespace `skatmind`, and primary CLI `skatmind`.
Issue #204 implements none of that rename; the current `skat-ai` / `skat_ai`
surfaces remain unchanged.

P-09 moves from `product_decision_required` to `implementation_required` under:

```text
B-08 / Issue #205:
    Complete the pre-v1 SkatMind product, repository, distribution,
    import-namespace, CLI, resource, identifier, compatibility, and migration
    boundary.
```

A separate Release-process Gate remains outside the 53-row ledger:

```text
B-09 / Issue #208:
    Complete hands-on maintainer user acceptance testing after the final
    technical readiness audit and resolve all accepted findings before Release
    preparation.
```

The completed technical sequence and next action are:

1. #205: completed the SkatMind rename and migration boundary.
2. #206: completed the v1 installation and supported-platform matrix and closed
   B-05 after both merged Ubuntu jobs passed.
3. #207: completed the final technical audit and closed B-06.
4. #208: perform maintainer v1.0.0 user acceptance testing next.

Release preparation remains B-07 and occurs only after #208 and any accepted
findings are resolved. Its Issue number is not frozen; it is expected to be #209
only if #208 creates no remediation Issues. Publication and post-publication
synchronization remain human-controlled.
