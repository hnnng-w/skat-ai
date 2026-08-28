# SkatMind rename and migration

## Decision

Issue #205 completes the one maintainer-approved pre-v1 active identity break.
The canonical identities are:

| Surface | Canonical value |
| --- | --- |
| Product display name | `SkatMind` |
| Repository target | `hnnng-w/skatmind` |
| Distribution | `skatmind` |
| Import namespace | `skatmind` |
| Console Script | `skatmind = skatmind.cli:main` |
| Module execution | `python -m skatmind` |
| Version output | `SkatMind 0.17.0` |
| Schema base | `https://example.local/skatmind/` |
| Default memory input reference | `memory://skatmind/request` |
| Canonical document-kind prefix | `skatmind_` |
| Canonical SHA-256 domain prefix | `skatmind\0` |

Package version `0.17.0`, Python `>=3.13`, API contract version `1`, the seven
Root workflows, one Console Script, 71 authoritative and packaged Schemas, six
Session examples, 98 generated scenarios, ten private Corpus downloads, and
Settlement Matrix version `3` with 61 cases remain unchanged.

## Hard cut

Clean current installations expose only `skatmind`. They do not install a
`skat_ai` Package, a `skat-ai` Console Script, or public aliases for renamed
`SkatAI...` symbols. Repository-root `main.py` remains the repository-only Legacy
launcher and delegates exclusively to `skatmind.cli`.

Public callers migrate as follows:

```text
Old:
    from skat_ai.api.v1 import ...
    skat-ai ...
    python -m skat_ai ...

New:
    from skatmind.api.v1 import ...
    skatmind ...
    python -m skatmind ...
```

The stable namespaces are `skatmind`, `skatmind.api`, `skatmind.api.v1`,
`skatmind.api.v1.session`, `skatmind.api.v1.session.files`, and
`skatmind.errors`. Public classes and warnings use the `SkatMind` prefix. Their
semantics, inheritance, export order, API version, workflow values, and
brand-neutral error codes remain unchanged except that the former brand-bearing
base error code is now `skatmind_error`.

## Package and resources

Setuptools discovers `src/skatmind`. Package Resources resolve through
`skatmind.schema_resources`, `skatmind.capture_web`, and `skatmind.corpus_web`.
`py.typed`, all Schema mirrors, Capture assets, and Corpus assets remain Package
Data. Wheel and sdist names use `skatmind-0.17.0`; the distribution validator
rejects the old active distribution and namespace.

The 71 authoritative Schema filenames and JSON field structures are unchanged.
Their `$id` and internal `$ref` graph use
`https://example.local/skatmind/`, and packaged resources remain byte-identical
to the authoritative files.

## Persisted identities

New writers emit these canonical kinds:

| Format | Canonical kind | Strict legacy input kind |
| --- | --- | --- |
| Session persistence | `skatmind_session` | `skat_ai_session` |
| Match Workspace persistence | `skatmind_match_workspace` | `skat_ai_match_workspace` |
| Learning Corpus Catalog | `skatmind_learning_corpus_catalog` | `skat_ai_learning_corpus_catalog` |
| Match Analysis Report source | `skatmind_match_analysis_report_source` | `skat_ai_match_analysis_report_source` |

Legacy support is input-only. Each reader selects one complete canonical or
legacy profile from the document kind and verifies every fingerprint or ID with
that profile's exact domains. Mixed old/new kinds, fingerprints, IDs, or nested
identity relationships are rejected. There is no fallback that tries both
domains after one profile fails.

The mutable legacy fingerprint domains are:

```text
skat-ai\0session_state_v1\0
skat-ai\0session_persistence_v1\0
skat-ai\0match_workspace_v1\0
skat-ai\0match_workspace_persistence_v1\0
skat-ai\0learning_corpus_catalog_v1\0
skat-ai\0learning_corpus_persistence_v1\0
skat-ai\0match_analysis_report_v1\0
```

Their canonical replacements use the same suffixes after `skatmind\0`. Loading
or resuming a legacy file reconstructs the same typed values and performs no
write. The next explicit successful Session, Workspace, or Catalog Save compares
against the loaded legacy content fingerprint and atomically writes the
canonical kind and canonical fingerprints. Rewritten Report-source serialization
emits the canonical kind and canonical Report ID. A subsequent Resume therefore
uses only the canonical profile.

## Corpus objects

Previously published immutable Learning Corpus object identities remain verified
opaque IDs. Strict Store Resume verifies legacy Match Snapshot and closed
reference relationships with their original domains:

```text
skat-ai\0learning_corpus_match_snapshot_v1\0
skat-ai\0learning_corpus_player_observation_v1\0
skat-ai\0learning_corpus_game_content_v1\0
skat-ai\0learning_corpus_game_reference_v1\0
skat-ai\0learning_corpus_decision_reference_v1\0
skat-ai\0learning_corpus_commentary_reference_v1\0
skat-ai\0learning_corpus_response_reference_v1\0
```

New objects use the corresponding `skatmind\0` domains. One current Catalog may
reference both verified legacy and new objects. Load, selection, orphan
reporting, and unchanged publication do not rehash, rename, rewrite, duplicate,
or delete a legacy object. Catalog Save canonicalizes only the mutable Catalog
document.

## Deterministic behavior

Seven pre-rename salts are frozen behavior protocols rather than emitted product
identities. They retain their original `skat-ai\0` material so the rename cannot
change simulation, historical Search, Recommendation, dataset partition, or
benchmark behavior:

1. coherent hidden-world child seeds;
2. Dataset-v1 partition seeds;
3. Dataset-v1 partition tie-break keys;
4. Historical Information-set Search decision seeds;
5. Historical bounded-Search decision seeds;
6. Dataset-v2 partition seeds; and
7. Dataset-v2 partition tie-break keys.

Focused tests freeze all seven exact numeric outputs. Every newly emitted
content-addressed identity uses `skatmind\0`; the retained salts are not used as
document, artifact, or object IDs.

## Browser and exports

Capture and Corpus titles and visible headings use SkatMind. Their cookie names
use `skatmind_capture_token` and `skatmind_corpus_token`; old cookie names are not
recognized as authenticated current cookies. Loopback binding, token handling,
same-origin checks, CSP, Host validation, routes, operations, and no-external-
resource behavior are unchanged.

New private exports, deterministic product-branded filenames, source references,
and document kinds use `skatmind`. There are still exactly ten authenticated
Corpus downloads. Report-source compatibility does not expose a legacy download
mode; current serialization is canonical.

## Examples and generated outputs

The six Session examples use canonical SkatMind persistence kinds and
fingerprints. Dedicated migration tests retain exact legacy values separately;
current examples are not legacy fixtures.

The ordered 98-scenario registry and every scenario ID remain unchanged. The
generated-output validator regenerates all scenarios through the renamed CLI and
validates them against the renamed Schema graph. Only approved brand, Schema,
source, document-kind, filename, and identity-domain values may differ. Frozen
seed protocols prevent gameplay, Search, Recommendation, Settlement, Coaching,
Tactical, Dataset, list, Statistics, and benchmark drift.

## Historical evidence

Published Releases, tags, Changelog entries, completed release audits, and exact
point-in-time Issue evidence continue to use the identities that existed when
they were recorded. For example, a published `v0.17.0` statement may retain
`skat-ai = skat_ai.cli:main`. Such text is historical evidence, not a supported
current command or import.

`CHANGELOG.md` is not rewritten. The deterministic rename inventory records every
remaining old-name occurrence as `legacy_persisted_input`,
`historical_evidence`, or the frozen behavior-protocol exception. The repository
test rejects any unreviewed occurrence and does not use broad directory
wildcards.

## Manual repository rename

OpenCode does not rename the GitHub repository. After the implementation is
committed, fast-forward merged, and pushed, the maintainer performs:

1. Confirm the merged main commit.
2. Rename the GitHub repository to `skatmind`.
3. Verify the old repository URL redirects.
4. Update the local origin URL.
5. Verify default branch, Issues, tags, Releases, and Actions.
6. Verify current documentation links.
7. Confirm CI on the renamed repository.
8. Close Issue #205 only after the repository rename is verified.

Recommended local commands after the GitHub rename are:

```powershell
git remote set-url origin https://github.com/hnnng-w/skatmind.git
git remote -v
```

## Gate result

Issue #205 makes P-09 `satisfied` and closes B-08 at the technical ledger level.
Manual GitHub rename and redirect verification remain the final human Issue-
closure step. The 53 required rows are then 18 `satisfied`, 34
`satisfied_with_approved_bounded_scope`, 1 `evidence_required`, 0
`implementation_required`, and 0 `product_decision_required`.

The remaining blockers are B-05, B-06, B-07, and B-09. B-09 remains outside the
53-row ledger. The exact next action is Issue #206, **Complete the v1 installation
and supported-platform matrix**. The rename changes product identity, packaging,
migration, and presentation only; it does not change Skat rules, Search,
Recommendation, Settlement, Coaching, Tactical, Dataset, list, Statistics,
security, dependency, build-backend, license, or Package-version behavior.
