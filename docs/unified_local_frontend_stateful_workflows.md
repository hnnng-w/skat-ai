# Unified local frontend managed stateful workflows

## Status

Issue #212 implements managed Session, Match Capture, and Learning Corpus
workflows inside the existing unified local frontend. It extends the Issue #210
[application shell](unified_local_frontend_application_shell.md) and the Issue
#211 [guided analysis and Results](unified_local_frontend_guided_analysis_and_results.md).

This is private Package behavior. Package version remains `0.17.0`, Python
remains `>=3.13`, the license remains `AGPL-3.0-only`, Public API contract
version remains `1`, the Root workflow count remains seven, and the distribution
still installs exactly one `skatmind = skatmind.cli:main` Console Script. No
Schema, example, generated output, persistence format, dependency, or Product
algorithm changes.

## Private contracts

The private versions are exactly:

```text
MANAGED_STATEFUL_FRONTEND_VERSION = 1
MANAGED_ITEM_DISCOVERY_VERSION = 1
GUIDED_SESSION_FRONTEND_VERSION = 1
UNIFIED_MATCH_CAPTURE_FRONTEND_VERSION = 1
UNIFIED_LEARNING_FRONTEND_VERSION = 1
FRONTEND_CROSS_AREA_TRANSFER_VERSION = 1
```

The exact ordered policies are:

```text
managed_category_discovery_is_explicit_and_non_recursive
opaque_browser_handles_never_expose_filesystem_paths
canonical_item_paths_are_derived_from_existing_product_identities
strict_create_import_open_resume_reload_without_silent_overwrite
existing_session_match_and_corpus_persistence_remains_authoritative
one_active_process_local_context_per_stateful_family
switching_items_discards_only_process_local_artifacts
all_mutations_reuse_existing_operations_and_conflict_semantics
cross_area_match_to_corpus_transfer_is_explicit_and_source_verified
unified_app_cookie_and_security_context_only
no_child_server_proxy_iframe_or_background_worker
no_implicit_analysis_selection_preparation_or_conversion
```

## Managed discovery

The managed families remain exactly `sessions`, `matches`, and `corpora`.
Discovery inspects only direct category children, rejects links and junctions,
does not recurse, and examines at most `2,048` candidates per explicit refresh.
Each candidate is classified as `available`, `invalid`, or
`resolution_required`. Duplicate semantic Product identities require explicit
resolution and cannot be opened.

Browser state contains a domain-separated opaque handle, Product display
identity where safely reconstructed, revision, phase/summary, status, active
marker, and discovery generation. It contains no path or storage basename.
Open resolves a handle only against the exact retained generation and rechecks
the direct child and reconstructed Product identity before activation. Every
active-item mutation form retains the opaque handle that rendered it; submission
after another item becomes active is rejected as a stale form before invoking a
Product operation.

Canonical managed storage names are derived from the existing Product identity:

```text
Session: session-<sha256>.json
Match:   match-<sha256>.json
Corpus:  corpus-<sha256>
```

Create and import reject an existing canonical destination. Browser upload
filenames are never authoritative. Session and Match imports accept one strict
finite UTF-8 JSON object without a BOM, duplicate keys, non-finite numbers, or a
non-object root. Uploaded JSON content is bounded to `16,777,216` bytes.

## Sessions

`/sessions` lists managed Sessions and provides strict creation and import.
Opening uses the stable Public Session File API and existing strict persistence
resume. The active guided page supports all ten existing typed Session Command
kinds, phase-aware entry, accepted-Log history, strict-prefix Undo, one-Command
correction, explicit Reload, automatic existing Decision Checkpoint collection,
and canonical Session JSON download.

Position analysis and completed-game Review are separate explicit actions. They
export through the existing Session contracts and execute through the existing
Public/Application boundary. Execution runs outside locks and publishes only if
the Session generation and content fingerprint remain unchanged. Request and
Result downloads use retained immutable bytes; no render or download executes a
workflow. Existing unavailable, rejected, conflict, partial, and stale outcomes
remain normal visible states.

## Match Capture

`/matches` lists managed Workspaces, offers the existing no-JSON Match creation
flow and strict Workspace import, and embeds the existing Capture body and
packaged progressive assets under namespaced routes. Every metadata, Game,
Card, Commentary, response, passed-deal, clear, Statistics, materialization,
Decision-analysis, Historical-analysis, Report, and export action delegates to
the existing Capture context and operations.

The browser projection uses the fixed safe display name `managed-match.json`.
The canonical managed storage basename and path never enter browser state.
Optimistic Workspace persistence, explicit conflict Reload, maximum-eight
revision-scoped Report behavior, and stale analysis publication rules are
unchanged. The standalone `skatmind capture` server remains supported and uses
its unchanged renderer and transport.

## Learning

`/learning` lists and creates managed Corpora and strictly opens existing Corpus
directories. The active page embeds the existing Learning Corpus body and local
assets under namespaced routes. Workspace and executed Decision Report-source
imports, explicit Current selection, Reload, source removal/clear, explicit
artifact preparation, and all ten authenticated canonical downloads reuse the
existing Corpus context and operations.

The active managed directory is revalidated as a direct non-link child under the
existing Corpus lock immediately before adapter access. A replaced link,
junction, or non-directory is rejected rather than followed.

Preparation remains process-local, runs outside the Corpus lock, and atomically
publishes only after exact source-lineage revalidation. It performs no implicit
analysis. Switching Corpora discards process-local sources/preparation through
the existing context shutdown and changes no persisted Catalog or immutable
object.

## Cross-area transfer

The active Match may be transferred explicitly to the active Corpus as exact
canonical Workspace bytes with caller-selected Current and same-revision
behavior. An eligible current Decision Report may be transferred explicitly to
one selected Current Match Snapshot as an exact Strategy Teacher Report source.

The application snapshots both active adapters under the app lock, then releases
that lock. Workspace or Report data is copied completely under the Match lock
before entering the Corpus operation. Match and Corpus locks are never held
together. Transfer summaries are path-free and source-verified. There is no
automatic Match import, Current selection, Report capture, analysis, preparation,
or Dataset conversion. Both source and target opaque handles are retained by the
form, and applied, unchanged, resolution-required, and conflict outcomes remain
visible in the refreshed Match page.

## Server and locking

`SkatMindAppWebServerV1` remains the sole transport. Stateful routes use the same
app Host, bootstrap token, `skatmind_app_token` cookie, same-origin mutation
check, `Referrer-Policy: origin`, CSP, and no-external-resource boundary as
Analyze and Review. The policy keeps a concrete browser POST Origin while
limiting Referer to scheme, host, and port without path or query. Null, forged,
and Host-mismatched Origins remain rejected. The application does not start,
proxy, iframe, or authenticate through
the standalone Capture or Corpus servers.

The app lock protects only active-adapter and discovery-generation snapshots or
publication. Discovery filesystem work, item load/save, Engine execution, and
Corpus preparation occur without the app lock. Existing Session, Match, and
Corpus locks remain authoritative. Switching an active item discards only the
prior family's process-local Result, Report, source, or preparation state.

The canonical top-level routes and navigation remain unchanged. Private
stateful descendants include lifecycle actions, `/sessions/current`,
`/matches/new`, `/matches/current`, `/matches/position/<1..36>`, Match Reports
and exports, `/learning/current`, Corpus operations and downloads, and the
namespaced Capture/Corpus assets. They are private browser transport, not a
public JSON API.

## Current boundary

Normal users can now create, import where supported, list, open/resume, reload,
edit, analyze, transfer, and download managed stateful Product data without a
typed filesystem path or port. Advanced `session`, `capture`, and `corpus`
commands remain available and unchanged.

Issue #214 and UAT-FINDING-004 are resolved after maintainer Microsoft Edge
verification. Repeated UAT-01 nevertheless failed. Issue #208 remains open;
UAT-02 through UAT-12 remain paused; B-09 and B-07 remain open; B-06 remains
closed; and Package `1.0.0` and Release preparation are not ready.

Issue #215 freezes the authoritative future
[bilingual profile-driven frontend UX contract](bilingual_profile_driven_frontend_ux_contract.md).
The exact next action is Issue #216.
