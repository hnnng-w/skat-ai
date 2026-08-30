# Learning Corpus browser workflows

Issue #179 completes the functional private local Learning Corpus and Learning
Dataset version `2` workflow planned for `v0.16.0`. It connects the existing
Issue #171 through #178 contracts through one explicit local Corpus root, exact
caller uploads, explicit preparation, a minimized browser dashboard, and seven
canonical downloads. It does not add an eighth Root workflow, another Console
Script, a Public API, a Schema, derived-artifact persistence, or automatic
analysis.

Issue #180 prepared Package version `0.16.0` and current Release documentation
without changing product behavior. Python remains `>=3.13`; Public API contract
version `1`, seven Root workflows, the one `skat-ai = skat_ai.cli:main` Console
Script, 63 authoritative Schemas, 63 Packaged Schema Resources, six Session
examples, 85 generated outputs, Training Dataset version `1`, and Learning
Dataset version `2` remain unchanged. Functional private local `v0.16.0` work is
complete through Issue #179, and Release preparation is complete through Issue
#180. The maintainer published `v0.16.0` manually on 2026-08-18 at commit
`91b1360`, and Issue #181 synchronizes publication status without product
functionality. GitHub Releases is the authoritative publication record; no
Package-index or PyPI publication is claimed.

Issue #195 extends the current private browser workflow with a separate Current-
Snapshot-only Tactical Motif Evidence family and exact descriptive cross-game
Summary. It adds two authenticated canonical downloads, bringing the current set
to nine, while preserving the historical Issue #179 seven-artifact chain. Human,
Strategy Teacher, and Tactical Evidence remain separate; Learning Dataset
version `2` remains unchanged. No Package/API/workflow/Console-Script/Schema/
example/generated-output count changes.

Issue #196 adds one separate deterministic Tactical Cross-game Coaching artifact
from exact retained Tactical Motif and Strategy Teacher Evidence. It adds one
authenticated canonical download, bringing the current set to ten, while
preserving the historical Issue #179 seven-artifact and Issue #195 nine-artifact
chains. All three prepared families publish and invalidate atomically. Learning
Dataset version `2`, public/versioned surfaces, and existing counts remain
unchanged.

## CLI startup

The Learning Corpus browser is a separate private command family available in
all three supported forms:

```powershell
skatmind corpus --corpus CORPUS_ROOT
python -m skatmind corpus --corpus CORPUS_ROOT
python main.py corpus --corpus CORPUS_ROOT
```

Its exact options are:

```text
--corpus PATH       required explicit private Learning Corpus root
--port INTEGER      optional loopback port from 1 through 65535; default 8766
--no-open           do not open the bootstrap URL in the default browser
-h, --help          command help
```

There is no default root, host, remote-bind, Workspace, output, force, repair,
generate, authentication-disable, daemon, database, or cloud option. The command
prints the token-bearing local bootstrap URL. Unless `--no-open` is supplied, it
attempts to open that URL. Browser-open failure emits a warning and leaves the
server running. Normal `Ctrl+C` shutdown succeeds; expected startup, strict
Resume, bind, or filesystem failures use Exit Code `1`, and parser misuse uses
Exit Code `2`.

Leading `corpus` dispatch is separate from leading `capture`, leading `session`,
and the seven-workflow Root parser. All forms still use the one Console Script;
repository-root `main.py` remains the Legacy facade and is not installed.

These remain current standalone advanced-interface requirements. Issue #210 adds
the unified shell and a `Learning & cross-game insights` placeholder but does not
list, create, open, or resume Corpus items. Issue #212 owns direct reuse of Corpus
operations in the one app server; it must not proxy, iframe, or start this
standalone server as a child. `skatmind corpus` and its explicit `--corpus`
contract remain supported for advanced use. Current selection, preparation,
Report transfer, and downloads remain explicit. See [Application shell](unified_local_frontend_application_shell.md)
and [Unified local frontend contract](unified_local_frontend_contract.md).

## One explicit root

One server owns exactly the path supplied through `--corpus`:

* the parent directory must already exist;
* an absent root or existing empty root starts an uninitialized browser;
* the initialization form requires a caller-supplied non-empty, non-padded
  `corpus_id`;
* initialization creates the existing fixed Corpus layout and revision-zero
  Catalog without generating a Corpus ID or timestamp;
* a non-empty existing root is strictly resumed before the server starts;
* an invalid existing root, file in place of the root, missing parent, invalid
  Catalog, missing referenced object, malformed object, or fingerprint mismatch
  is rejected rather than repaired or overwritten.

The browser never discovers another root, changes roots, creates a parent,
chooses a default location, or exposes the root path in its page or state
projection. Initialization, Resume, Reload, import, and Current-selection
changes execute no analysis or materialization workflow.

## Strict uploads

Workspace and Strategy Teacher Report-source imports use strict
`multipart/form-data`. The complete request body, including multipart framing
and text fields, has an exact maximum of `16,777,216` bytes (16 MiB). Requests
over that limit return HTTP `413`. `Content-Length` is required and transfer
encoding is unsupported.

Each multipart request must contain exactly one allowed file field:

```text
workspace_file
report_source_file
```

The parser requires one valid ASCII multipart boundary, unique allowlisted text
fields, no nested multipart, no transfer encoding, and an uploaded file with
`application/json` when a part Content-Type is supplied. The uploaded content
must be a finite UTF-8 JSON object without a BOM, duplicate object key, `NaN`, or
infinity. Unknown fields, repeated fields, extra files, unsupported file fields,
and malformed framing are rejected.

Caller filenames are ignored. They are not used as server paths, retained in
state, persisted in the Corpus, or included in diagnostics. Exact uploaded bytes
are written only to a server-owned temporary `.json` file when an existing
strict file boundary requires a path. The temporary filename is server-generated
and the file is removed after success or every failure path.

## Workspace import and Current selection

The import form supplies the current Catalog revision plus two explicit options:

```text
selection_mode:
    select_imported
    keep_current

same_revision_resolution:
    reject
    retain
```

The displayed browser defaults are `select_imported` and `reject`. Import uses
the existing revision-conflict-first and content-fingerprint compare-and-swap
orchestration. It strictly loads the uploaded Workspace, builds one immutable
content-addressed Match Snapshot, classifies it once, publishes a new object
without clobbering equal content, saves the Catalog at most once, and strictly
reloads the resulting Store.

The exact import statuses remain:

```text
applied
unchanged
revision_conflict
persistence_conflict
resolution_required
```

`reject` returns `resolution_required` for distinct content at the same retained
Workspace revision. `retain` permits both immutable Snapshots, after which the
selection mode still decides whether the imported Snapshot becomes Current.
`revision_conflict` and `persistence_conflict` return HTTP `409`;
`resolution_required` is a normal no-change Result that requires a new explicit
`retain` submission. Unchanged and no-change Results write no Catalog.
Object publication before a Catalog persistence conflict may intentionally
leave one valid orphan reported by the next strict Resume. There is no retry,
merge, overwrite, automatic newest selection, or orphan deletion.

Every represented logical Match retains exactly one explicit Current Snapshot.
The dashboard lists all retained Snapshots and provides `Select Current` for a
non-current entry. Selection uses the displayed expected Catalog revision and
the same optimistic persistence boundary and returns `applied`, `unchanged`,
`revision_conflict`, or `persistence_conflict`; both conflicts use HTTP `409`. It
never infers Current from revision, import order, played time, filename, or
evidence quality.

An applied Workspace import or applied Current-selection change invalidates all
prepared process-local artifacts. `unchanged`, `revision_conflict`,
`persistence_conflict`, and `resolution_required` preserve the loaded context
and any still-matching prepared artifacts.

## Reload behavior

`Reload Corpus` strictly loads the same explicit root. A successful Reload
replaces the loaded Store only after complete strict validation, increments the
context generation, and invalidates prepared artifacts. Process-local Strategy
Teacher sources remain loaded and are reclassified against the newly Current
Snapshot set.

A failed Reload retains the prior loaded Store, source store, prepared artifacts,
and context generation. It does not partially replace state, clear sources,
repair data, retry, merge, or fall back to an empty Corpus.

## Match Capture Report-source transfer

An executed Match Capture Decision Analysis report page now provides:

```text
Download for Learning Corpus
```

The authenticated route is:

```text
/api/v1/reports/<report_id>/strategy-source.json
```

The link exists only for a current executed `decision_analysis` report. It is not
available for unavailable Decision reports, Historical Analysis reports, or
materialization reports. The downloaded filename is the existing deterministic
Decision Root-artifact basename with `-strategy-source.json` appended.

The strict source document has exactly:

```text
match_analysis_report_source_export_version = 1
document_kind = skatmind_match_analysis_report_source
report_id
report
```

The Report-source reader also accepts the exact pre-rename kind and Report-ID
domain as strict input-only compatibility. A current download or rewritten
serialization always emits the canonical kind and canonical Report ID. See
[SkatMind rename and migration](skatmind_rename_and_migration.md).

The nested value must be the complete canonical version-1 Match Analysis Report
for one executed Decision Analysis. It must retain exact identity fields,
execution status `executed`, null unavailable/skipped reasons, exact analysis
options, exact relative Profile binding, one Position Request wrapper, and one
Position Result wrapper including warnings. Fixed wrappers reject missing or
unknown fields, wrong native scalar types, unsupported workflow or report kind,
identity changes, and non-canonical nested Request or Result content. The
document is canonical UTF-8 JSON with ASCII escaping, two-space indentation, LF
line endings, and exactly one trailing LF.

Issue #191 keeps source-export version `1` and accepts exact Information-set
Decision Reports. Resume validates the nested Information-set Request settings,
safe aggregate Result, retained comparison, and fixed-policy relationships in
addition to the existing wrapper checks.

The Corpus upload form additionally requires the caller to select one explicit
Current Match Snapshot. Import constructs one exact Snapshot-to-Report source
binding and validates Match, revision, Game, Decision, acting Player, observed
actual Card, rebuilt Position Request, Profile binding, and retained Result
against that Current Snapshot without executing analysis. Selecting a different
Current Snapshot later does not rewrite the source; it classifies the source as
`non_current`.

There is no automatic Report capture, Historical Report import, report-directory
scan, Report persistence, or Capture-to-Corpus background connection.

## Process-local Strategy Teacher sources

One server retains at most `2,048` exact Strategy Teacher source bindings in
memory. Equal source bindings are `unchanged`; a different source under the same
binding ID is rejected. Sources use deterministic canonical order and expose
only minimized dashboard facts: source/report/Snapshot identities, Match,
position, Decision, recommendation method, and binding status.

Binding status is exactly:

```text
current
non_current
```

Only `current` sources may enter preparation. Any `non_current` source remains
visible and blocks preparation until the caller removes it, restores the matching
Current selection, or clears all sources. `Remove` deletes one exact binding;
`Clear Sources` deletes all process-local bindings. Applied add, remove, and
clear operations invalidate prepared artifacts. Duplicate add, missing remove,
and empty clear are `unchanged` and do not invalidate.

Sources are never added to `catalog.json`, Match Snapshot objects, the source
Workspace, or another file. They disappear on server shutdown.

Canonical source ordering now covers all four flat methods, with
`information_set_search` after the existing Immediate, bounded Search, and
`auto` methods.

## Explicit artifact preparation

Preparation is one explicit browser action. Its fields and displayed defaults
are:

```text
dataset_id          <corpus_id>-learning-dataset-v2
known_player_seed   0
unseen_player_seed  0
train_weight        70
validation_weight   15
test_weight         15
```

`dataset_id` must be non-empty, non-padded text. Seeds are strict integers and
may be negative. Each weight is a strict positive integer. The browser defaults
are explicit submitted values; they do not add defaults to the underlying
Dataset-v2 partition Request contract.

Preparation requires no non-current Strategy Teacher source and builds the
following exact values in this order:

1. Current-Snapshot Player Catalog.
2. Current-Snapshot Human Commentary and Response Evidence.
3. Current-Snapshot-bound Strategy Teacher Evidence.
4. Unpartitioned task-neutral Learning Dataset version `2`.
5. `known_player` partition preparation Result.
6. `unseen_player` partition preparation Result.
7. Cross-game Summary using those exact two supplied partition Results.
8. Current-Snapshot-only Tactical Motif Evidence Collection, with every observed
   Decision represented by exact Evidence or an explicit skip.
9. Tactical Motif Cross-game Summary using that exact Collection and the exact
   Player Catalog from step 1.
10. Tactical Cross-game Coaching Report using the exact retained Tactical
    Collection/Summary, Strategy Teacher Collection, and Player Catalog.

Each source artifact is built once; the partition Request builder and partition
preparation each run once per mode. Empty or insufficient source data can
produce valid Dataset or partition `empty`/`unavailable` states. Preparation
does not execute Match Analysis, Position, Historical, Training Dataset,
Search, Profile derivation, or another Root workflow. Step 10 assesses retained
Teacher values only and executes no analysis, Search, or Tactical detection.

The existing Strategy Teacher step carries focused Information-set Evidence
through the existing Dataset-v2 joins and cross-game Summary. The first seven
Issue #179 steps and their execute-no-workflow rule are unchanged. The two
Issue #195 steps call the exact shared single-game Tactical detector after safe
Match Decision-state reconstruction; they execute no Historical Application,
Search, Coaching, Profile, or Dataset-v2 mutation.

Potentially long generation runs outside the synchronized context lock. Before
publishing, the server reacquires the lock and compares the loaded Store identity,
Catalog revision, Catalog content fingerprint, Strategy source-store revision,
and context generation captured at start. If any source changed, it invalidates
prepared artifacts, publishes nothing, and returns `source_changed` with HTTP
`409`. There is no retry or partial artifact set.

## Invalidation matrix

Prepared artifacts are a single exact process-local set:

| Event | Strategy sources | Prepared artifacts |
| --- | --- | --- |
| Applied Workspace import | retained and reclassified | invalidated |
| Unchanged/conflicted/resolution-required import | retained | retained |
| Applied Current selection | retained and reclassified | invalidated |
| Unchanged/conflicted Current selection | retained | retained |
| Applied Report-source add/remove/clear | changed | invalidated |
| Unchanged Report-source add/remove/clear | unchanged | retained |
| Successful Reload | retained and reclassified | invalidated |
| Failed Reload | retained | retained |
| Successful Prepare | retained | replaced by the new exact set |
| Source change during unlocked Prepare | current source state retained | invalidated; no publication; HTTP `409` |
| Download or dashboard read | retained | retained; no rebuild |
| Server shutdown | cleared | cleared |

Successful Reload invalidates even when the loaded bytes are equal. A source
that becomes non-current blocks the next preparation. Downloads also verify the
prepared Store identity, generation, source revision, Catalog revision, and
Catalog content fingerprint: missing artifacts return HTTP `404`, while a
detected source mismatch returns HTTP `409`.

Issue #195 stores the first seven artifacts and the two Tactical artifacts in
separate immutable process-local wrappers, but publication is one atomic prepared
generation. Before publication, both wrappers must share the exact Catalog
revision and content fingerprint, and the Tactical Summary must retain the exact
Player Catalog fingerprint from the existing wrapper. Any invalidating event or
source change clears both wrappers; successful preparation replaces both; a
no-change/conflicted operation preserves both when their sources still match.
There is no Tactical-only retry or partial publication.

Issue #196 adds a third immutable prepared wrapper. It must retain the same
Catalog revision/content fingerprint, Player Catalog fingerprint, exact Strategy
Teacher collection fingerprint, Tactical collection fingerprint, and Tactical
Summary fingerprint used by the Coaching Report. Publication, invalidation,
preservation, and replacement always apply to all three wrappers. There is no
Coaching-only preparation, retry, or partial publication.

## Dashboard privacy

The server-rendered dashboard is a minimized path-free projection, not a public
redaction layer. It shows Corpus identity and counts, retained/Current Snapshot
identity and summary counts, source-binding summaries, preparation readiness and
evidence counts, and a bounded Player Catalog summary with stable Player IDs,
observed labels, Match counts, alias-conflict counts, and Statistics-observation
counts.

For the Tactical family, the dashboard adds only collection status, Evidence
count, skipped Decision count, motif occurrence count, Player Summary count, and
recurrence count. It does not expose individual observations, actual Cards,
per-Player motif counts, recurrence identities, complete hands, legal-Card sets,
Commentary, Strategy Teacher values, fingerprints, or paths.

For Coaching, it adds only report status, Decision count, Teacher Assessment
count, focus-area count, and Player-with-focus count. It does not expose Player
focus rows, Guidance, motifs, Cards, ranks, aggregate metrics, source identities,
fingerprints, or paths.

Dashboard state and HTML omit:

* the Corpus root and every caller/server filesystem path;
* bootstrap token and persistence fingerprints;
* raw Workspace, Catalog, Match Snapshot, Request, Result, or Report JSON;
* complete hands, Skat, Discards, and record pools;
* Commentary text and complete Statistics records;
* Search Worlds, private Search state, stack traces, and exception details.

The retained Corpus, uploaded Report sources, prepared values, and downloads are
still private local unredacted data. Minimized presentation does not make those
values public or non-sensitive.

## Ten authenticated downloads

Issue #179 historically introduced the first seven downloads below. Issue #195
added two Tactical downloads, and Issue #196 adds the final Coaching download,
so after successful current preparation the browser exposes exactly ten
downloads in this order:

| Artifact | Route | Filename suffix |
| --- | --- | --- |
| Player Catalog | `/downloads/player-catalog.json` | `player-catalog` |
| Human Evidence | `/downloads/human-evidence.json` | `human-evidence` |
| Strategy Teacher Evidence | `/downloads/strategy-teacher-evidence.json` | `strategy-teacher-evidence` |
| Learning Dataset v2 | `/downloads/learning-dataset-v2.json` | `learning-dataset-v2` |
| Known-player partitions | `/downloads/known-player-partitions.json` | `known-player-partitions` |
| Unseen-player partitions | `/downloads/unseen-player-partitions.json` | `unseen-player-partitions` |
| Cross-game Summary | `/downloads/cross-game-summary.json` | `cross-game-summary` |
| Tactical Motif Evidence | `/downloads/tactical-motif-evidence.json` | `tactical-motif-evidence` |
| Tactical Motif Cross-game Summary | `/downloads/tactical-motif-cross-game-summary.json` | `tactical-motif-cross-game-summary` |
| Tactical Cross-game Coaching | `/downloads/tactical-cross-game-coaching.json` | `tactical-cross-game-coaching` |

Filenames are exactly:

```text
<safe-source-id>-<artifact-suffix>-<identity-first-12>.json
```

Player Catalog, Human Evidence, and Strategy Teacher Evidence use `corpus_id` as
the source ID. Learning Dataset v2, both partition Results, and the Summary use
`dataset_id`. Both Tactical artifacts and Coaching use `corpus_id`. Unsafe filename runs
become `-`; leading/trailing `.`, `_`, and `-`
are removed; the readable source portion is limited to 64 ASCII characters; an
empty safe value becomes `artifact`. Player Catalog uses its Catalog fingerprint
as identity. The remaining artifacts use their canonical export IDs.

The response bytes equal the existing canonical serializers: UTF-8, ASCII
escaping, finite JSON, two-space indentation, LF line endings, and exactly one
trailing LF. Downloading does not rebuild a source, run preparation, write a
server file, or mutate the Corpus. Routes require the established authenticated
cookie and valid loopback Host, accept no query or server path, and return an
ASCII-safe `Content-Disposition` attachment basename.

## No-JavaScript baseline

Initialization, Reload, Workspace upload, Current selection, Report-source
upload/remove/clear, preparation, and all downloads work through ordinary
server-rendered HTML forms and links without JavaScript. Packaged local vanilla
JavaScript provides progressive file-selection feedback only. It owns no Corpus
identity, import, Current-selection, source-validation,
Dataset, partition, Summary, or security rule.

## Loopback security and network boundary

The Standard Library server binds only to `127.0.0.1`. Startup creates a random
token used only in the initial bootstrap query. A valid bootstrap request sets
the `skatmind_corpus_token` cookie with `Path=/`, `HttpOnly`, and
`SameSite=Strict`, then redirects to a token-free URL. Access logging is disabled
so the bootstrap token is not written by the server.

All requests require an exact valid `Host` for `127.0.0.1` or `localhost`, with
the actual port where supplied. Authenticated GETs require the cookie and reject
queries. Mutating POSTs require the cookie plus an exact `http` loopback
`Origin` whose host and port equal the request Host. No permissive CORS response
is emitted.

Every response includes `no-store`, `nosniff`, `no-referrer`, frame denial, a
restrictive Permissions Policy, and this Content Security Policy:

```text
default-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'; style-src 'self'; script-src 'self'; img-src 'self' data:; connect-src 'self'; font-src 'none'; media-src 'none'; object-src 'none'
```

Only allowlisted Package-owned HTML, CSS, and JavaScript resources are served.
There is no CDN, external font, remote image, Node.js dependency, source URL
fetch, platform API call, telemetry, update check, or other external network
request. Loopback authentication reduces accidental local exposure; it is not
an account system, encryption, authenticated authorship, secure storage, remote
deployment, or multi-user access control.

## Lifetime and open boundaries

The loaded Corpus Store points to persistent exact Catalog and Match Snapshot
objects under the explicit root. Strategy Teacher Report sources and all ten
prepared artifacts exist only for the current server process. Server shutdown
clears both process-local stores and closes the HTTP server; it does not delete
or modify persisted Corpus content.

Issue #179 persists no Player Catalog, Human Evidence, Strategy Teacher Evidence,
Learning Dataset-v2, partition Result, Summary, Report source, or download. It
adds no Public API export, Public Match API, JSON Schema, Root workflow, example,
generated output, task builder, target, communication taxonomy, derived tag,
evaluation, rating, ranking, or model training.

Issue #195 likewise persists no Tactical Motif Evidence Collection, Tactical
Motif Cross-game Summary, prepared wrapper, or download. Its exact occurrence,
distinct-Game, distinct-Match, Player, role, seat, phase, contract, and recurrence
Counts make no trait, rate, quality, correctness, significance, intent,
communication, causal, or Coaching claim. Issue #196 consumes these observations
without changing them. See [Learning Corpus Tactical
Motif evidence and summaries](learning_corpus_tactical_motif_evidence_and_summaries.md).

Issue #196 persists no Coaching Report, prepared wrapper, or download. Its
retained complete-Search comparison is a bounded Teacher assessment, not a
ground-truth, perfect-play, Player-rating, intent, communication, causal, or
significance claim. Human Commentary and Response Links remain unconsumed, and
Dataset version `2` remains unchanged. See [Learning Corpus Tactical Cross-game
Coaching](learning_corpus_tactical_cross_game_coaching.md).

Deletion, garbage collection, recovery, persisted aliases/assertions,
merge/split, all-revision Player views, derived artifact persistence, automatic
Report capture, Historical Report import, task-specific behavior/strategy/
communication builders, evaluation, ratings, and training remain open. Database,
remote/hosted deployment, cloud synchronization, collaboration, distributed
locking, encryption/key management, and automatic backup remain open as well.

Issue #191 uses this unchanged upload, process-local preparation, and seven-
download workflow. It adds no browser operation, route, download, persisted
object, Public API, Schema, example, or generated scenario. See
[Match Information-set Search and Strategy Teacher Evidence](match_information_set_search_and_strategy_teacher.md).

See [Learning Corpus identity and Catalogs](learning_corpus_identity_and_catalogs.md),
[Learning Corpus persistence and Workspace import](learning_corpus_persistence_and_import.md),
[Learning Corpus Player Catalog and Statistics history](learning_corpus_player_catalog_and_statistics_history.md),
[Learning Corpus human Commentary and Response evidence](learning_corpus_human_commentary_and_response_evidence.md),
[Learning Corpus Strategy Teacher Evidence](learning_corpus_strategy_teacher_evidence.md),
[Learning Dataset version 2](learning_dataset_v2.md),
[Learning Dataset version 2 partition preparation](learning_dataset_v2_partition_preparation.md),
[Learning Dataset version 2 cross-game summaries](learning_dataset_v2_cross_game_summaries.md),
[Learning Corpus Tactical Motif evidence and summaries](learning_corpus_tactical_motif_evidence_and_summaries.md),
[Learning Corpus Tactical Cross-game Coaching](learning_corpus_tactical_cross_game_coaching.md),
[Match analysis and exports](match_analysis_and_exports.md), and
[Unified local frontend contract](unified_local_frontend_contract.md).
