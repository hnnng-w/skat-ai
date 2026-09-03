# Unified local frontend managed stateful workflows

## Status

Issue #212 implements managed Session, Match Capture, and Learning Corpus
workflows inside the existing unified local frontend. It extends the Issue #210
[application shell](unified_local_frontend_application_shell.md) and the Issue
#211 [guided analysis and Results](unified_local_frontend_guided_analysis_and_results.md).
Issue #218 adds separate bounded submitted-form state and localized contextual
validation without changing the existing Session, Match, or Corpus contracts.
Issue #219 adds private profile-driven normal creation, generated identities,
known Players, defaults, and managed display labels without changing those
authoritative Product contracts. See [Profile-driven stateful
creation](profile_driven_stateful_creation.md).

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
PROFILE_DRIVEN_FORM_DEFAULTS_VERSION = 1
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

Browser state contains a domain-separated opaque handle, profile-backed display
label or localized fallback, Product display identity where safely reconstructed,
revision, phase/summary, status, active marker, and discovery generation. It
contains no path or storage basename. Normal creation generates Product
identities; imported Product identities remain unchanged.
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

Create and import reject an existing canonical destination. Session and Match
landing-page order is normal Create, existing managed items, then secondary
Advanced import. Browser upload
filenames are never authoritative. Session and Match imports accept one strict
finite UTF-8 JSON object without a BOM, duplicate keys, non-finite numbers, or a
non-object root. Uploaded JSON content is bounded to `16,777,216` bytes.

## Sessions

`/sessions` lists managed Sessions and provides strict creation and import.
Normal creation asks for a Game name, recording mode, three saved-or-new Player
names, and a visible perspective seat, then generates the Session and any new
Player IDs. Saving new Players and the selected perspective is explicit.
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
remain normal visible states; rejected/unavailable responses use contextual HTTP
`400`, and conflict/stale responses use contextual HTTP `409`.

## Match Capture

`/matches` lists managed Workspaces, offers a bilingual no-JSON Match creation
flow and strict secondary Workspace import, and embeds the existing Capture body and
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

Normal Match creation asks for a title, optional display date, friendly platform,
three saved-or-new Player names, perspective seat, and optional source URL. The
fixed format is presented as `EuroSkat 36-game standard`; uncommon exact Product
metadata remains under Advanced. A date alone does not invent `played_at`, and
saved platform IDs are never copied into Product metadata without explicit
submission.

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

Normal creation asks only for a learning-collection name and generates the
Corpus ID. It performs no import, Current selection, preparation, or analysis.

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

## Validation Feedback

All lifecycle and active-item POST forms are covered by the private canonical
registry documented in
[Frontend validation state and localized feedback](frontend_validation_state_and_localized_feedback.md).
The complete unified registry has 44 POST routes and 77 definitions. Creation
and settings forms use profile-generation checks and exact opaque form identity.
Rejected safe values remain on the exact originating form. The active Session,
Match, or Learning Corpus is retained, and switching that exact active object
invalidates older feedback. Successful actions retain HTTP `303`. File controls
are always cleared and require explicit reselection. Raw Product, persistence,
path, handle, and exception details do not become validation presentation.

The unified app adapts existing Capture and Corpus HTML only after their shared
renderers return. Standalone `skatmind capture` and `skatmind corpus` output and
transport therefore remain unchanged.

Creation validates values and current profile state, generates identities, and
persists the authoritative Product exactly once before attempting one optional
profile update. A Product failure makes no profile change. A later profile
conflict, capacity, size, or storage failure leaves the Product persisted,
active, and discoverable and displays a localized warning; there is no cross-file
transaction or rollback claim.

## Current boundary

Normal users can now create, import where supported, list, open/resume, reload,
edit, analyze, transfer, and download managed stateful Product data without a
typed filesystem path or port. Advanced `session`, `capture`, and `corpus`
commands remain available and unchanged.

Issue #214 and UAT-FINDING-004 are resolved after maintainer Microsoft Edge
verification. Repeated UAT-01 nevertheless failed. Issue #208 remains open;
UAT-02 through UAT-12 remain paused; B-09 and B-07 remain open; B-06 remains
closed; and Package `1.0.0` and Release preparation are not ready.

Issue #215 freezes the authoritative
[bilingual profile-driven frontend UX contract](bilingual_profile_driven_frontend_ux_contract.md).
Issue #216 implements the shared private profile/localization foundation. When
German is active, remaining future-owned active Session, Match, and Learning
bodies retain explicit language boundaries pending Issue #220. Issue #217 adds localized Product-
unit guidance, safe related links, and useful no-Session, no-Match, no-collection,
and active-empty-collection states outside those regions. Issue #218 implements
contextual stateful validation without changing Product operations. Issue #219
implements bilingual profile-driven creation and local Player/default/label
management. Issue #220 is the exact next action.
