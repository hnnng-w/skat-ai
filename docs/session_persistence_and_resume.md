# Session persistence and resume

Issue #155 adds internal Session Persistence version `1`. It stores one
authoritative accepted-Log Session State and optional caller-supplied frozen
Decision Checkpoints in a private local document, strictly reconstructs and
replays that content on resume, recomputes Checkpoint Lineage, and provides an
optimistic atomic file-save boundary. It does not execute analysis. Issue #157
exposes the file boundary through a focused stable public subnamespace without
changing the persistence document.

Issue #156 exposes only in-memory `build_session_persistence_document()` and
`resume_session_document()`. Construction preserves canonical Checkpoint order
and both fingerprints; resume validates the supplied mapping against the packaged
Session Schema before strict reconstruction, fingerprint verification, replay,
and lineage recomputation. Neither in-memory operation reads or writes a file or
retains a path or timestamp.

Issue #157 adds the separate stable `skatmind.api.v1.session.files` version-1
transport over the unchanged low-level Save/Load behavior. It also adds CLI
automatic Checkpoint collection and optimistic file orchestration. Paths remain
caller-supplied transport arguments and are not retained in public Results,
Session State, or the persistence document.

Issue #163 adds a separate internal Match Workspace persistence boundary. It
mirrors the strict JSON, optimistic content-fingerprint, and atomic local-file
model without importing private Session-persistence helpers or changing Session
documents, fingerprints, Resume, public files, CLI behavior, or versions. Match
Workspace files are not Session files, and no materialization exists between the
two boundaries.

Issue #172 adds another separate private Learning Corpus persistence boundary.
It does not import private Session-persistence helpers and does not change
Session documents, canonical bytes, fingerprints, Resume, public files, CLI, or
versions. Session files are not Learning Corpus source objects.

Issue #205 adds a strict input-only profile for exact pre-rename version-1
Session documents. Load/Resume verifies the original kind and both original
fingerprint domains without writing the file. Mixed canonical/legacy identity is
rejected. The next explicit successful Save compares against the loaded legacy
content fingerprint and atomically writes the canonical SkatMind kind and
fingerprints. See [SkatMind rename and migration](skatmind_rename_and_migration.md).

## Contract identity

The exact constants and policies are:

```text
SESSION_PERSISTENCE_VERSION = 1
SESSION_PERSISTENCE_DOCUMENT_KIND = skatmind_session
SESSION_PERSISTENCE_STATE_POLICY = authoritative_accepted_log_state
SESSION_PERSISTENCE_CHECKPOINT_POLICY = caller_supplied_frozen_checkpoints
SESSION_PERSISTENCE_STATE_FINGERPRINT_POLICY = sha256_canonical_session_state_v1
SESSION_PERSISTENCE_CONTENT_FINGERPRINT_POLICY = sha256_canonical_document_without_content_fingerprint
SESSION_PERSISTENCE_CONFLICT_POLICY = expected_content_fingerprint_compare_and_swap
SESSION_PERSISTENCE_WRITE_POLICY = same_directory_temp_file_atomic_replace
SESSION_PERSISTENCE_RESUME_POLICY = strict_parse_fingerprint_replay_and_lineage
SESSION_PERSISTENCE_ENCODING = utf-8
SESSION_PERSISTENCE_WRITE_STATUSES = (saved, unchanged, conflict)
```

Session Persistence version `1` is independent of the Package version, Public
API contract version `1`, Application orchestration version `1`, installed
CLI contract version `1`, Session and Command version `1`, transition and
projection version `1`, Request-export versions, Decision-Checkpoint and Lineage
versions, Provenance versions, and Schema versions.

Issue #155 changes none of the historical published `v0.13.0` facts. That
baseline remains 62 authoritative and packaged Schemas and 77 generated outputs;
the published `v0.14.0` baseline has 63 byte-identical authoritative and packaged
Schemas and 85 generated outputs.

## Private document

`SessionPersistenceDocumentV1` is frozen, slotted, keyword-only, and contains
exactly:

```text
session_persistence_version
document_kind
state_fingerprint
content_fingerprint
state
decision_checkpoints
```

`document_kind` is exactly `skatmind_session`. `state` is one exact
`SessionStateV1`; its accepted Command Log remains authoritative. The document
does not persist a separate projection, derived Game State, Undo or Correction
Result, removed or discarded suffix, Redo stack, analysis Result, Search World,
simulation ownership, proof state, cache, principal variation, field-level
Provenance, generated timestamp, host, or file path.

Persistence does not add fields to `SessionStateV1`. Session State itself still
contains no filesystem path, persistence version, State fingerprint, or content
fingerprint. A path is caller-supplied only to file load/save, while fingerprints
and optimistic-write identity belong only to the separate persistence boundary.

`decision_checkpoints` is optional and defaults to an empty tuple when the caller
builds a document. The persistence builder itself does not collect Checkpoints.
Issue #157 CLI orchestration can collect them before building the replacement
document. Every supplied value must be an exact canonical
`SessionDecisionCheckpointV1` for the same Session ID. Exact duplicates are
rejected.

The builder canonicalizes Checkpoints by:

```text
source_revision
decision_index
trick_number
play_index
canonical compact Position Request bytes
canonical compact complete Checkpoint bytes
```

The array is therefore independent of caller input order, including when two
different Checkpoints share one source revision. Checkpoints remain frozen and
retain their source revision, information cutoff, relative Player map, and local-
private Position Request. Persistence attaches no Decision Observation, actual
Card, review Request, or analysis Result; those values are derived from the
active accepted Log when requested.

## Canonical fingerprints

Both fingerprints are lowercase 64-character SHA-256 hexadecimal values. Their
canonical compact JSON bytes use:

```python
json.dumps(
    value,
    allow_nan=False,
    ensure_ascii=True,
    separators=(",", ":"),
    sort_keys=True,
).encode("utf-8")
```

The State identity is:

```text
SHA-256(
    b"skatmind\0session_state_v1\0"
    + canonical_compact_json(state.to_dict())
)
```

The content identity is:

```text
SHA-256(
    b"skatmind\0session_persistence_v1\0"
    + canonical_compact_json(document without content_fingerprint)
)
```

The content material contains, in semantic terms:

```text
session_persistence_version
document_kind
state_fingerprint
state
decision_checkpoints
```

The explicit NUL-delimited domains separate Session State identity from complete
persistence-content identity. The State fingerprint covers the complete replay-
verified State, including its accepted Log and derived Validation. Equal numeric
revisions with corrected Logs therefore have different State and content
fingerprints. Adding or changing only a frozen Checkpoint preserves the State
fingerprint but changes the content fingerprint.

Fingerprint identity is independent of file whitespace and JSON object-key
order. It is not independent of canonical array order or semantic value changes.
The fingerprints are deterministic identity and integrity checks, not digital
signatures, authenticated authorship, confidentiality, or access control.

## Build and strict resume

`build_session_state_fingerprint_v1(state)` first replays the complete accepted
Log and then fingerprints the exact replay-verified State.

`build_session_persistence_document_v1(state, decision_checkpoints=...)` performs
one complete State replay, validates and canonicalizes the supplied Checkpoints,
and computes the State and content fingerprints without file I/O. A forged or
semantically invalid internal State is not persisted as authoritative content.

`resume_session_document_v1(document)` accepts one typed persistence document or
one already loaded mapping. Resume is strict rather than a best-effort migration:

1. The root and every supported nested contract require their exact field set;
   missing and unknown fields are rejected.
2. Players, Commands, accepted records, Declaration and event/end payloads,
   Validation, readiness, Checkpoints, and embedded Position Requests are rebuilt
   through their current exact version-1 contracts.
3. Canonical round trips are required, including canonical Player, Log,
   Diagnostic, reason-code, Card, and Checkpoint ordering.
4. The accepted Command Log is replayed and the stored Capture Mode, revision,
   phase, Validation, and readiness must match the replayed projection.
5. The State fingerprint is recomputed from the replay-verified State and must
   match.
6. The content fingerprint is recomputed from the complete canonical document
   without its `content_fingerprint` field and must match.
7. Checkpoint Lineage is derived again from the resumed State and frozen
   Checkpoints.

There is no permissive fallback, unknown-field retention, fingerprint repair,
partial resume, or use of a stored projection. Content that no longer matches
either stored fingerprint is rejected even when its State revision is unchanged.

## Recomputed lineage

`SessionResumeResultV1` contains exactly:

```text
session_persistence_version
document
checkpoint_lineage
```

Lineage is not a persistence-document field and is never trusted from disk. The
resume path derives one `SessionCheckpointLineageV1` per canonical Checkpoint in
the same order. It reconstructs accepted prefixes and the expected information-
safe Position Request where the current State reaches the Checkpoint revision.

The existing relationships retain their exact meanings:

* `current`: the State has the same revision and exactly reproduces the frozen
  Checkpoint;
* `ancestor`: the later State has an unchanged effective accepted prefix through
  the Checkpoint;
* `future`: the resumed State revision is earlier than the frozen Checkpoint;
* `diverged`: the State reaches the revision but the accepted prefix no longer
  reproduces the complete frozen Checkpoint.

Future and diverged Checkpoints remain caller-retained historical values. Resume
reports their lineage instead of deleting, rewriting, or silently promoting
them.

## Optimistic write results

`SessionPersistenceWriteResultV1` contains exactly:

```text
session_persistence_version
status
session_id
revision
expected_content_fingerprint
existing_content_fingerprint
requested_content_fingerprint
```

It contains no path. `save_session_persistence_file_v1()` requires the caller to
supply `expected_content_fingerprint`, using `null` to assert that the target is
absent. The existing target, when present, is strictly loaded and resumed before
its content fingerprint is compared. Invalid existing content raises an error
and is never treated as an absent or overwriteable target.

The normal outcomes are:

| Existing target | Expected fingerprint | Requested content | Status |
| --- | --- | --- | --- |
| absent | `null` | any valid document | `saved` |
| absent | non-null | any valid document | `conflict` |
| present | different from existing | any valid document | `conflict` |
| present | equals existing | equals existing | `unchanged` |
| present | equals existing | differs from existing | `saved` |

An `unchanged` Result requires the expected, existing, and requested content
fingerprints to be the same non-null value. A `saved` Result requires expected
and existing identity to match and, for an existing target, requested identity to
differ. A `conflict` Result reports the latest observed existing fingerprint or
`null` when the target is absent and performs no replacement.

The save path checks the target once before creating a temporary file and again
immediately before replacement. An existence or content-fingerprint change at
the second check returns `conflict` and removes the owned temporary file. This is
optimistic conflict detection rather than file locking; atomic replacement does
not claim a filesystem-wide transaction with uncontrolled writers.

## Canonical file bytes

`save_session_persistence_file_v1()` emits deterministic pretty JSON bytes:

* UTF-8 without a byte-order mark;
* ASCII escaping through `ensure_ascii=True`;
* finite JSON only;
* two-space indentation;
* LF line endings with exactly one final LF;
* stable contract field and canonical array order;
* recursively sorted object keys inside each embedded Checkpoint Position
  Request document.

Equal canonical documents produce byte-identical files when an actual write is
performed. The pretty file bytes are not the fingerprint input: compact sorted
canonical JSON is. A valid semantically canonical document may therefore be
loaded from different whitespace or object-key ordering and retain the same
content fingerprint. An `unchanged` save preserves those existing bytes; a later
actual write emits the one canonical pretty representation.

## Atomic save protocol

An actual write requires the target parent to exist and be a directory. Save does
not create directories. For a changed or new document, the implementation:

1. creates an owned temporary file in the target's directory;
2. writes the complete canonical bytes, flushes them, and calls `os.fsync()` on
   the temporary file;
3. reloads the target fingerprint for the final optimistic conflict check;
4. calls `os.replace()` for atomic same-directory name replacement;
5. attempts a best-effort `fsync()` of the parent directory.

Owned temporary files are removed on conflict or failure before replacement.
Unrelated stale temporary files are neither interpreted nor deleted. A temporary
write, flush, file-`fsync`, or `os.replace()` failure is propagated and preserves
an existing target. Directory-`fsync` is explicitly best effort because support
varies by operating system and filesystem; its failure is ignored and no stronger
cross-platform durability guarantee is claimed.

## File loading and errors

`load_session_persistence_file_v1(path)` requires a regular file, reads bytes,
strictly decodes UTF-8, parses JSON, and invokes the same strict resume path. It
rejects a UTF-8 BOM, invalid UTF-8, malformed JSON, duplicate object keys at any
depth, non-finite numbers, a non-object root, unsupported fields, non-canonical
typed values, replay conflicts, and either fingerprint mismatch.

Malformed, non-canonical, replay-inconsistent, or tampered persisted content uses
`SkatMindValidationError` with the most specific available RFC 6901 path. An
internally supplied typed document that fails save-time consistency verification
is a `SkatMindInvariantError`. Invalid direct Python argument types or fingerprint
shapes use `ValueError`. Loading a missing file, non-regular targets, missing
write parents, permission failures, and write/replace failures preserve their
filesystem exceptions. Save never overwrites an existing target that cannot
first be strictly loaded and verified.

## Privacy and security boundary

Session persistence is private local working data. A Retrospective Session may
contain the complete three hands, Skat, Discards, and Plays as accepted Commands.
Optional Decision Checkpoints contain local-private Position Requests, including
the acting local hand and other information legitimate at that decision cutoff.

The persistence document itself has no public redaction step. Optional Session
Provenance describes the exact returned value and redacts only provenance
references/dependencies; it neither removes nor widens document content. Public
Root output privacy contracts do not apply to the document. Fingerprints are
integrity identities, not provenance or authorship. Issue #155 makes
no encryption, key management, access-control, secure-deletion, backup,
synchronization, multi-user storage, or remote-transport claim. Callers are
responsible for file location, operating-system permissions, copies, and backups.
SHA-256 verification detects content that does not match its stored identities;
because those identities are unkeyed and can be recomputed, it is not an
authentication mechanism against a writer who can replace the document.

## Public file and CLI boundary

The low-level implementation remains under `skatmind.session_persistence*`.
`save_session_persistence_file_v1` and `load_session_persistence_file_v1` remain
private functions. The exact `SessionPersistenceWriteResultV1` type is re-exported
only from stable `skatmind.api.v1.session.files`, whose `save_session_file()` and
`load_session_file()` delegate once and retain no path.

Installed, module, and Legacy Session CLI mutations load one exact document,
retain its content fingerprint, perform one operation, build one replacement,
and save with compare-and-swap. Applied Commands/Undo and applied or partial
Corrections can persist; rejected, conflicted, and unchanged Session operations
do not rewrite the file. A Save conflict returns CLI Code `1` and leaves the
target unchanged. Automatic collection writes the State and canonical
Checkpoint tuple together but starts no analysis.

Persistence itself does not execute Immediate Analysis, bounded Search, hidden-
card inference, Multi-Step, Policy Comparison, Historical processing, Review,
Coaching, scoring, Settlement, or any Application workflow. Explicit CLI
`analyze`, `review`, and `finalize` export first and then execute the existing
Application outside persistence; analysis Results are never stored in the
Session document. There is no eighth Root workflow, default path, backup, merge,
retry loop, GUI, cloud synchronization, distributed lock, encryption/key
management, or automatic backup policy. Issue #158 completed Package version
`0.14.0` and Release-documentation preparation without changing persistence
behavior before manual maintainer publication. See
[Session CLI and end-to-end capture](session_cli_and_end_to_end_capture.md).
