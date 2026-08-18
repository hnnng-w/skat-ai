# Learning Corpus identity and Catalogs

Issue #171 establishes the first internal foundation for the active
`v0.16.0 - Learning-ready behavior and communication data` milestone. It defines
immutable content-addressed Match Snapshots, Snapshot-closed references, and a
lightweight Catalog with explicit current selections. It adds no persistence,
import operation, Dataset version `2`, workflow, CLI, browser operation, Public
API, Schema, example, or generated output.

Issue #172 adds a separate private deterministic persistence and explicit
Workspace-file import layer over these unchanged values. It does not change any
Issue #171 identity, reference, Catalog, ordering, or classification behavior.
See [Learning Corpus persistence and Workspace import](learning_corpus_persistence_and_import.md).

Issue #173 derives a separate non-persisted Player Catalog and time-safe
Statistics history from only the explicit Current selections. It changes no
Issue #171 identity or Catalog contract. See
[Learning Corpus Player Catalog and Statistics history](learning_corpus_player_catalog_and_statistics_history.md).

Issue #174 derives a separate non-persisted minimized Human Commentary and linked
Response Evidence collection and canonical in-memory export from the same explicit
Current selections. It changes no Issue #171 identity, Reference, Snapshot, or
Catalog contract. See
[Learning Corpus human Commentary and Response evidence](learning_corpus_human_commentary_and_response_evidence.md).

Issue #175 derives a separate non-persisted method-bound Strategy Teacher
Evidence collection and canonical in-memory export from explicit caller-bound
executed Decision Analysis Reports. Sources must bind the same explicit Current
selections, but no Issue #171 identity, Reference, Snapshot, or Catalog contract
changes. See
[Learning Corpus Strategy Teacher Evidence](learning_corpus_strategy_teacher_evidence.md).

Issue #176 derives a separate non-persisted, unpartitioned, task-neutral Learning
Dataset version `2` from the exact Store and supplied Current-Snapshot Player,
Human, and Strategy Teacher sources. It changes no Issue #171 identity,
Reference, Snapshot, Catalog, object-kind, or persistence contract. See
[Learning Dataset version 2](learning_dataset_v2.md).

## Source-of-truth boundary

The exact source and derived-data relationships are:

```text
Match Workspace:
    editable capture source

Learning Corpus Match Snapshot:
    immutable source copy

Catalog:
    lightweight identity/current-selection manifest

Learning Corpus Player Catalog:
    derived current-Snapshot Player and Statistics view, not persisted

Statistics Selection:
    derived strict as-of Result, not persisted

Strategy Teacher Evidence:
    separate Current-Snapshot-bound derived Report evidence, not persisted

future annotation artifacts:
    separate derived objects

Learning Dataset v2:
    separate Current-Snapshot-derived task-neutral export, not persisted

Human Commentary and Response Evidence:
    separate minimized Current-Snapshot-derived export
```

Corpus behavior never mutates a source Workspace. A corrected Workspace
persistence document becomes a distinct Match Snapshot. Equal exact source
content deduplicates by Snapshot ID. Reports, analysis values, annotations,
Datasets, paths, storage locations, and import times are not Snapshot or Catalog
fields.

## Contract identity

The independent internal versions are:

```text
LEARNING_CORPUS_IDENTITY_VERSION = 1
LEARNING_CORPUS_MATCH_SNAPSHOT_VERSION = 1
LEARNING_CORPUS_REFERENCE_VERSION = 1
LEARNING_CORPUS_CATALOG_VERSION = 1
LEARNING_CORPUS_SNAPSHOT_CLASSIFICATION_VERSION = 1
```

The append-only object-kind tuple is:

```text
LEARNING_CORPUS_OBJECT_KINDS = (
    match_workspace_snapshot,
)
```

Report and annotation object kinds do not exist yet. The exact policies are:

```text
LEARNING_CORPUS_SOURCE_OF_TRUTH_POLICY =
    immutable_imported_workspace_snapshot

LEARNING_CORPUS_IDENTITY_POLICY =
    logical_identity_plus_content_addressed_revision

LEARNING_CORPUS_OBJECT_KIND_POLICY =
    append_only_object_kinds

LEARNING_CORPUS_DUPLICATE_POLICY =
    equal_content_deduplicates_by_snapshot_id

LEARNING_CORPUS_REVISION_POLICY =
    same_match_distinct_content_retains_distinct_snapshot

LEARNING_CORPUS_SAME_REVISION_POLICY =
    same_revision_distinct_content_requires_explicit_resolution

LEARNING_CORPUS_CURRENT_SELECTION_POLICY =
    explicit_current_snapshot_per_logical_match

LEARNING_CORPUS_PLAYER_IDENTITY_POLICY =
    exact_stable_player_ids_without_fuzzy_merge

LEARNING_CORPUS_REFERENCE_POLICY =
    snapshot_closed_derived_references

LEARNING_CORPUS_PRIVACY_POLICY =
    private_local_unredacted_learning_data
```

## Canonical identity material

Every new identifier uses SHA-256 over one domain prefix followed by finite
canonical JSON. Canonical JSON uses UTF-8, `ensure_ascii=true`,
`allow_nan=false`, sorted keys, and separators `(",", ":")`.

The exact domains are:

```text
skat-ai\0learning_corpus_match_snapshot_v1\0
skat-ai\0learning_corpus_player_observation_v1\0
skat-ai\0learning_corpus_game_content_v1\0
skat-ai\0learning_corpus_game_reference_v1\0
skat-ai\0learning_corpus_decision_reference_v1\0
skat-ai\0learning_corpus_commentary_reference_v1\0
skat-ai\0learning_corpus_response_reference_v1\0
```

The Match Snapshot identity material contains exactly:

```text
learning_corpus_match_snapshot_version
object_kind
source_workspace_fingerprint
source_content_fingerprint
workspace
```

Player Observation identity contains every Player Observation field except its
derived ID. Observed-Game content identity contains the complete canonical
`ObservedGameRecordV1` serialization and no Snapshot identity. Game Reference
identity contains its version, Game content fingerprint, Snapshot ID, Match ID,
Match position, and Game ID. Decision, Commentary, and Response identity contains
each corresponding reference field except its derived ID. Redundant closed
references are intentional identity boundaries.

Existing Workspace and Match Analysis fingerprint implementations are unchanged.
Fingerprints and IDs provide deterministic content identity, not confidentiality,
authenticated authorship, source provenance, quality, or Confidence.

## Match Snapshot source verification

`build_learning_corpus_match_snapshot_v1()` accepts only the exact
`MatchWorkspacePersistenceDocumentV1` type. It performs no file I/O. Construction:

1. serializes the supplied in-memory document through `to_dict()`;
2. strictly resumes it through `resume_match_workspace_document_v1()`;
3. requires exact resumed document equality and canonical dictionary equality;
4. retains the original exact validated Workspace object;
5. retains the source Workspace and content fingerprints;
6. derives the Snapshot ID and every closed reference;
7. validates complete reference reconciliation.

An inconsistent internally supplied exact document raises
`SkatAIInvariantError`. A mapping, subclass, Workspace, file path, or another
source type is not accepted as a Match Snapshot source.

## Match Snapshot contract

`LearningCorpusMatchSnapshotV1` is frozen, slotted, keyword-only, and
builder-controlled. It contains:

```text
learning_corpus_match_snapshot_version
object_kind
match_snapshot_id
match_id
workspace_revision
source_workspace_fingerprint
source_content_fingerprint
workspace
player_observations
game_references
decision_references
commentary_references
response_references
```

The Snapshot retains the complete private Workspace, including exact source
metadata, Cards, Match-bound Player Statistics, Commentary, and Response Links.
It stores no path, import time, report, analysis result, derived annotation,
Dataset, or storage location.

Match ID is logical Match identity. Snapshot ID is exact source-content revision
identity. Equal persistence documents produce equal Snapshot IDs. Different
content produces a different Snapshot and new Snapshot-scoped references even
when Match ID and Workspace revision are equal.

## Player Observations

Every Match Snapshot derives exactly three
`LearningCorpusPlayerObservationV1` values in canonical `place_1`, `place_2`,
`place_3` order. Each value retains:

```text
learning_corpus_reference_version
player_observation_id
match_snapshot_id
player_id
table_place
player_label
game_platform
platform_player_id
statistics_snapshot_id
```

Player IDs use exact case-sensitive equality. Labels, aliases, and platform IDs
are not merged. Issue #171 does not choose a global canonical label or itself
define a Player Catalog; Issue #173 separately derives one without changing
these source observations.

## Game and Decision references

`build_learning_corpus_game_content_fingerprint_v1()` is a pure helper over one
exact `ObservedGameRecordV1`. The fingerprint is independent of a Match Snapshot,
while `LearningCorpusGameReferenceV1` is Snapshot-scoped. Logical Game identity
is the pair `(match_id, game_id)`.

One Game Reference is created for each observed-Game Slot in Match-position
order. Empty and Passed Deal Slots create none. A Game Reference contains the
Game content fingerprint and the ordered Decision, Commentary, and Response
Reference ID tuples for that Game.

One `LearningCorpusDecisionReferenceV1` is created for each retained observed
Play in source order. It retains the acting stable Player ID and Decision index,
but no Card, recommendation, quality, feature, label, or analysis value. Decision
Reference identity is Snapshot-scoped. There is no automatic cross-Snapshot
Decision lineage.

## Commentary and Response references

One `LearningCorpusCommentaryReferenceV1` is created for each retained canonical
Commentary value in existing canonical Commentary order. It retains only the
source Commentary ID and its same-Snapshot subject Decision Reference ID.
Original text, commentator identity, and timecode remain only inside the retained
Workspace Snapshot. The Corpus does not normalize, classify, interpret, redact,
or translate Commentary.

One `LearningCorpusResponseReferenceV1` is created for each existing canonical
Response Link. It retains the source Link ID, same-Snapshot Commentary Reference
ID, and same-Snapshot response Decision Reference ID. It records the original
caller association only. It does not infer causality, correctness, tactical
meaning, communication quality, or strategic value.

## Closed one-pass derivation

After one strict in-memory Resume, reference derivation traverses the 36
authoritative Slots once. It creates observed-Game references only, preserves
each source order, and rejects duplicate derived identities or orphaned
Commentary/Response references. Every child reference points to the same
Snapshot and exact parent Game Reference. Each Game Reference's child ID tuples
must equal the complete ordered child sets for that Game.

The builder executes no Match Analysis, Historical materialization, Profile
derivation, report import, Training Dataset generation, Dataset preparation,
Search, Coaching, Public API, or transport behavior.

## Catalog entries

`LearningCorpusMatchSnapshotCatalogEntryV1` is built only from a fully validated
Match Snapshot. It is a lightweight value containing source identity and summary
metadata:

```text
learning_corpus_catalog_version
object_kind
match_snapshot_id
match_id
workspace_revision
source_workspace_fingerprint
source_content_fingerprint
played_at
source_kind
source_title
game_platform
perspective_player_id
player_ids
observed_game_count
passed_deal_count
empty_slot_count
decision_count
commentary_count
response_link_count
```

The three Slot counts reconcile to 36. Reference counts reconcile with the
validated Snapshot. The entry embeds no Workspace, report, Dataset, path, storage
location, or import metadata.

## Catalog and current selections

`LearningCorpusCurrentMatchSelectionV1` contains Catalog version, Match ID, and
Snapshot ID. `LearningCorpusCatalogV1` contains:

```text
learning_corpus_catalog_version
corpus_id
revision
match_snapshots
current_matches
```

The caller supplies a stable Corpus ID and a non-negative revision. The builder
orders entries by Match ID, Workspace revision, then Snapshot ID. It orders
current selections by Match ID. Snapshot IDs and source content fingerprints are
globally unique within one Catalog.

Multiple content revisions and same-revision content conflicts for one logical
Match are valid Catalog content. Every represented Match has exactly one explicit
current selection, and every selection references an entry for that same Match.
The Catalog never infers the newest revision or changes a selection. Empty
Catalog creation produces revision zero with no entries or selections. Issue
#171 defines no Catalog mutation, persistence, deletion, or garbage collection.
The explicit Current selections are the complete source set for Issues #173
through #176; non-current entries and orphan objects do not enter the derived
Player, Human Evidence, Strategy Teacher Evidence, or Learning Dataset views.

## Snapshot classification

`classify_learning_corpus_match_snapshot_v1()` is pure and non-mutating. Its
exact relation tuple is:

```text
new_match
duplicate_snapshot
newer_revision
older_revision
same_revision_content_conflict
```

Classification applies this precedence:

1. `new_match` when the logical Match has no Catalog entry;
2. `duplicate_snapshot` when the exact Snapshot ID already exists;
3. `same_revision_content_conflict` when distinct content shares a retained
   Workspace revision;
4. `newer_revision` relative to the explicit current selection;
5. `older_revision` relative to the explicit current selection.

The result retains candidate/current identity and revision plus all same-Match
and same-revision Snapshot IDs. It makes no import, replacement, merge, current-
selection, or deletion decision.

## Privacy and current limits

Learning Corpus Match Snapshots are private local unredacted learning data. They
may contain hands, Skat, Discards, Plays, Commentary, Response Links, Player
Statistics, source URLs, titles, and timecodes. Issue #171 adds no redaction,
encryption, access-control, network, remote-storage, cloud, backup, or secure-
deletion claim.

Issue #172 implements fixed-root Corpus persistence, immutable object storage,
strict Workspace-file import, pure Catalog import, explicit Current-selection
updates, strict Store Resume, valid orphan reporting, no-clobber object
publication, and optimistic Catalog Save. Issue #173 adds a derived
Current-Snapshot Player Catalog, exact observed aliases/conflicts, and retained
time-safe multi-Match Statistics history. Player Catalog persistence, persisted
alias assertions, merge/split operations, all-revision views, deletion, garbage
collection, and automatic Report capture remain open. Issue #174 supplies the separate
private minimized Commentary/Response Evidence collection and in-memory export.
Issue #175 supplies separate exact executed Decision Report Strategy Teacher
Evidence and an in-memory export without changing Corpus persistence. Human and
Strategy Teacher Evidence persistence, browser/CLI/API/Schema transport, derived
tags, Historical Report import, Dataset-v2 persistence, task builders, persisted
split artifacts, Summary persistence/transport/UI, examples, generated scenarios,
and model training remain open. Issues #176 through #178's in-memory Dataset,
partition, Summary, and export values change no Corpus persistence bytes.

Package version remains `0.15.0`. Public API contract version `1`, the seven Root
workflows, one Console Script, 63 authoritative and packaged Schemas, six Session
examples, 85 generated outputs, existing Workspace persistence bytes, Match
Analysis report behavior, and Training Dataset version `1` target
`actual_card_played` are unchanged.
