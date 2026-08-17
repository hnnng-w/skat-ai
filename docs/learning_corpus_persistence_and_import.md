# Learning Corpus persistence and Workspace import

Issue #172 adds the private deterministic persistence and explicit Match
Workspace import layer for the Issue #171 Learning Corpus identity and Catalog
contracts. It adds no CLI, browser operation, Public API, Root workflow, Schema,
example, generated scenario, Dataset version `2`, or Player Catalog.

## Source-of-truth boundary

The exact relationship is:

```text
editable Match Workspace file:
    authoritative capture source

content-addressed Match Snapshot object:
    immutable imported source copy

catalog.json:
    authoritative lightweight manifest and Current selections

valid unreferenced Match Snapshot object:
    orphaned immutable content, not Catalog state
```

Import never mutates the source Workspace file. Catalog changes never mutate or
rewrite a Match Snapshot object. Selecting another Current Snapshot changes only
the Catalog. Source Workspace paths, Corpus paths, filenames, import times, save
times, host values, and process values are not persisted contract fields.

## Versions and policies

The independent internal versions are:

```text
LEARNING_CORPUS_PERSISTENCE_VERSION = 1
LEARNING_CORPUS_STORE_VERSION = 1
LEARNING_CORPUS_CATALOG_CHANGE_VERSION = 1
LEARNING_CORPUS_IMPORT_VERSION = 1
```

The exact policies are:

```text
LEARNING_CORPUS_LAYOUT_POLICY =
    explicit_root_catalog_and_content_addressed_objects

LEARNING_CORPUS_CATALOG_FINGERPRINT_POLICY =
    sha256_canonical_learning_corpus_catalog_v1

LEARNING_CORPUS_CONTENT_FINGERPRINT_POLICY =
    sha256_canonical_document_without_content_fingerprint

LEARNING_CORPUS_CONFLICT_POLICY =
    expected_catalog_content_fingerprint_compare_and_swap

LEARNING_CORPUS_OBJECT_WRITE_POLICY =
    immutable_no_clobber_content_addressed_publish

LEARNING_CORPUS_CATALOG_WRITE_POLICY =
    same_directory_temp_file_atomic_replace

LEARNING_CORPUS_RESUME_POLICY =
    strict_catalog_and_referenced_object_validation

LEARNING_CORPUS_IMPORT_POLICY =
    strict_workspace_file_to_immutable_match_snapshot

LEARNING_CORPUS_ORPHAN_POLICY =
    catalog_authoritative_unreferenced_objects_reported_not_deleted

LEARNING_CORPUS_SELECTION_UPDATE_POLICY =
    explicit_select_imported_or_keep_current
```

These policies make no cloud, remote-storage, encryption, access-control,
secure-deletion, backup, or distributed-locking claim.

## Fixed directory layout

Every operation receives one explicit Corpus root. There is no default root.
Version `1` uses exactly:

```text
CORPUS_ROOT/
    catalog.json
    objects/
        match_workspace_snapshot/
            <match_snapshot_id>.json
```

Object paths are derived only from the fixed object kind and one canonical
lowercase 64-character Match Snapshot ID. Callers do not supply object paths.
No platform-dependent separator is persisted.

Initialization accepts an absent root or an existing empty root, requires its
parent to exist, and creates only the fixed directories plus one empty
revision-zero Catalog. The caller supplies the Corpus ID; initialization
generates no identity or timestamp. A failed attempt performs best-effort cleanup
only for paths it created.

## Catalog persistence document

`LearningCorpusCatalogPersistenceDocumentV1` contains exactly:

```text
learning_corpus_persistence_version
document_kind
catalog_fingerprint
content_fingerprint
catalog
```

The document kind is `skat_ai_learning_corpus_catalog`. The nested Catalog is the
complete lightweight Issue #171 value: it contains entries and explicit Current
selections, not Match Snapshot objects. The persistence document contains no
path, directory name, timestamp, analysis Result, Dataset artifact, or report.

The Catalog fingerprint uses domain:

```text
skat-ai\0learning_corpus_catalog_v1\0
```

over the exact validated `LearningCorpusCatalogV1.to_dict()` value. Its material
is exactly:

```text
learning_corpus_catalog_version
corpus_id
revision
match_snapshots
current_matches
```

The persistence-content fingerprint uses domain:

```text
skat-ai\0learning_corpus_persistence_v1\0
```

over persistence version, document kind, Catalog fingerprint, and Catalog. It
excludes only `content_fingerprint`. Both use the Issue #171 finite compact
canonical JSON contract, so mapping order and pretty-file whitespace do not
affect identity.

## Strict reconstruction

Catalog Resume requires exact top-level, Catalog, entry, and Current-selection
field sets. It reconstructs entries and selections through the existing focused
contracts, reconstructs the complete Catalog through the Issue #171 builder,
requires canonical typed serialization to equal the supplied mapping, and
verifies both fingerprints. Missing or unknown fields, wrong versions or kind,
malformed relationships, non-canonical arrays, and fingerprint mismatches are
rejected.

Match Snapshot object Resume does not trust persisted derived references. It:

1. requires the exact Issue #171 Snapshot and nested reference field sets;
2. reconstructs the embedded Workspace through the existing strict Match
   Workspace Resume path using the retained Workspace and content fingerprints;
3. rebuilds the complete canonical Match Snapshot through Issue #171;
4. requires exact persisted identity, source facts, Player Observations, and
   Game, Decision, Commentary, and Response References;
5. requires the object filename to equal the rebuilt Match Snapshot ID at file
   Load.

Externally persisted invalid content raises `SkatAIValidationError`. Impossible
disagreement among already validated internal values raises
`SkatAIInvariantError`. Native filesystem failures remain filesystem exceptions.

## Canonical files

Catalog and Match Snapshot object files use:

```text
UTF-8 without BOM
ensure_ascii = true
allow_nan = false
two-space indentation
LF line endings
one trailing LF
stable contract field order
```

Load also accepts semantically canonical alternate whitespace or object-key
order because fingerprints use compact sorted canonical JSON. It rejects a BOM,
invalid UTF-8, malformed JSON, duplicate keys at any depth, NaN, infinity, and
non-object roots.

## Strict Store Resume and orphans

`load_learning_corpus_directory_v1()` requires the root directory, regular
`catalog.json`, fixed object directory, and every Catalog-referenced object. It
strictly validates and reconciles each referenced Match Snapshot with every
lightweight Catalog entry field and returns objects in Catalog-entry order.

The object directory is scanned for canonical content-addressed filenames.
Every unreferenced canonical object is strictly validated before its ID is
reported in sorted `orphan_match_snapshot_ids`. A malformed canonical object is
an error even when unreferenced. Hidden temporary files and unrelated filenames
are not interpreted as objects.

An orphan is never automatically added, selected, deleted, moved, rewritten, or
repaired. No garbage-collection operation exists in version `1`.

## Pure Catalog operations

`apply_learning_corpus_match_snapshot_import_v1()` and
`select_learning_corpus_current_match_snapshot_v1()` perform no file I/O.
Expected revision conflicts precede candidate or target semantics. An applied
change increments the Catalog revision exactly once; unchanged, revision-
conflict, and resolution-required Results preserve the source Catalog.

Import classifies the Snapshot exactly once through Issue #171:

* `new_match` adds the Snapshot and selects the only available Snapshot under
  either selection mode;
* `duplicate_snapshot` adds no entry; `keep_current` preserves selection and
  `select_imported` can explicitly select the retained duplicate;
* `newer_revision` and `older_revision` both retain the immutable Snapshot;
* `same_revision_content_conflict` with `reject` returns
  `resolution_required` and changes nothing;
* `same_revision_content_conflict` with `retain` adds the distinct immutable
  Snapshot.

For an existing Match, selection mode is always explicit:

```text
select_imported
keep_current
```

There is no automatic newest, highest-revision, import-order, played-time,
filesystem-time, source-filename, or evidence-quality selection.

The pure Current-selection operation requires an existing Snapshot of the
supplied logical Match. Selecting the already Current Snapshot is unchanged;
selecting another retained Snapshot increments the Catalog revision once and
does not alter entries.

## Immutable object publication

Objects are published before the updated Catalog. Publication validates the
exact Snapshot and derives its fixed path. An equal existing object is unchanged.
A malformed or different object under the same filename is corruption and is
never overwritten.

A new object is written completely to one same-directory temporary file,
flushed, file-`fsync`ed, and published through a no-clobber same-filesystem link.
If another writer publishes first, the winning object is strictly loaded and
must be equal. Directory `fsync` is best effort. The operation cleans only its
owned temporary file and never mutates an existing object.

## Optimistic Catalog Save

Catalog Save writes only `catalog.json`. It strictly validates any existing
Catalog before comparing the expected content fingerprint. Invalid existing
content is never overwritten. Normal outcomes are `saved`, `unchanged`, and
`conflict`.

An actual Save writes and file-`fsync`s one complete same-directory temporary
file, revalidates the target, atomically replaces it with `os.replace`, attempts
best-effort directory `fsync`, and cleans its owned temporary file. There is no
retry or merge. This is optimistic conflict detection, not distributed locking;
an uncontrolled writer can still race after final revalidation and before atomic
replacement.

## Workspace-file import

`import_match_workspace_file_into_learning_corpus_v1()` performs this bounded
sequence:

1. strictly load the current Store;
2. check expected Catalog revision;
3. check expected Catalog content fingerprint;
4. return without reading the source Workspace when either value is stale;
5. strictly load the Workspace through existing Match Workspace persistence;
6. build one Issue #171 Match Snapshot;
7. classify once and apply one pure Catalog import;
8. return for unchanged, revision conflict, or resolution required;
9. publish the immutable object only for a new Catalog entry;
10. build one Catalog persistence document and Save once;
11. strictly reload the final authoritative Store.

It performs no Match mutation, analysis, Search, Coaching, Historical
materialization, Profile derivation, Dataset generation, Dataset preparation,
network request, or background work.

If object publication succeeds but Catalog Save conflicts, import returns
`persistence_conflict`, retains the external Catalog, performs no retry or merge,
and does not delete the object. The object remains a valid orphan. Later Store
Resume reports it, and a repeated import may reuse it with object status
`unchanged` before publishing the Catalog.

The focused persisted Current-selection operation follows the same revision and
content-fingerprint precedence, applies one pure selection, writes no object,
saves the Catalog at most once, and strictly reloads after success.

## Privacy and current limits

Match Snapshot objects are private local unredacted data and may contain complete
Workspace source metadata, Cards, Player Statistics, Commentary, Response Links,
URLs, and timecodes. The lightweight Catalog contains only Issue #171 entry and
selection values. No public redaction is applied. Fingerprints provide
deterministic identity and consistency verification, not confidentiality or
authenticated authorship.

Deletion, garbage collection, orphan cleanup, recovery UI, Player Catalog,
aliases, Snapshot-history browsing or named selections beyond Current,
Commentary/Response export, Match Analysis
Report import, strategy-teacher evidence, Derived Tags, Dataset version `2`,
Dataset samples/partitions/splits, cross-game summaries, browser workflows, CLI,
Public API, Schema, examples, generated scenarios, and model training remain
open.

Package version remains `0.15.0`. Python remains `>=3.13`; the seven Root
workflows, one Console Script, 63 authoritative and packaged Schemas, six Session
examples, 85 generated outputs, Match Workspace and Session persistence bytes,
and Training Dataset version `1` target `actual_card_played` are unchanged.
