# Match Workspace contracts

Issue #163 adds persistent internal Workspaces for one
`euroskat_36_standard_v1` Match. A Workspace is the authoritative local capture
container for exactly 36 Match positions. It can retain empty positions, partial
or complete observed Games, and explicit passed deals without persisting a
Historical Game, list, report, Dataset, or analysis Result.

The implementation remains internal. Issue #164 now wraps its unchanged
operations with transport-free rapid-entry Application services. Issue #165
adds the private local browser/Capture CLI and autosave orchestration without
changing the Workspace contracts or persisted bytes. Issue #167 derives
internal preparation/materialization values from an already loaded Workspace
without adding a Workspace field or persistence byte. There is still no Public
Match API, Root workflow, Match Schema/data workflow, example, or generated
scenario.

## Contract identity

The independent versions are:

```text
MATCH_WORKSPACE_CONTRACT_VERSION = 1
MATCH_WORKSPACE_SLOT_VERSION = 1
MATCH_PASSED_DEAL_VERSION = 1
MATCH_WORKSPACE_PROGRESS_VERSION = 1
MATCH_WORKSPACE_CHANGE_VERSION = 1
MATCH_WORKSPACE_PERSISTENCE_VERSION = 1
```

The exact policy identifiers are:

```text
MATCH_WORKSPACE_SLOT_POLICY =
    fixed_authoritative_36_position_array

MATCH_WORKSPACE_ROTATION_POLICY =
    reuse_fixed_three_player_list_rotation

MATCH_WORKSPACE_PROGRESS_POLICY =
    derived_from_slot_occupancy_and_observed_evidence

MATCH_WORKSPACE_STATE_FINGERPRINT_POLICY =
    sha256_canonical_match_workspace_v1

MATCH_WORKSPACE_CONTENT_FINGERPRINT_POLICY =
    sha256_canonical_document_without_content_fingerprint

MATCH_WORKSPACE_CONFLICT_POLICY =
    expected_content_fingerprint_compare_and_swap

MATCH_WORKSPACE_WRITE_POLICY =
    same_directory_temp_file_atomic_replace

MATCH_WORKSPACE_RESUME_POLICY =
    strict_parse_fingerprint_validate_and_progress
```

The persistence document kind is:

```text
skatmind_match_workspace
```

Issue #205 also reads exact pre-rename version-1 Workspace documents through a
strict input-only kind/domain profile. Load never rewrites the source; mixed
identity is rejected; the next explicit successful compare-and-swap Save writes
the canonical kind and SkatMind fingerprint domains. See
[SkatMind rename and migration](skatmind_rename_and_migration.md).

These versions are independent from the Package, Public API, Session, Match
Capture, observed-Game, fixed-list, Historical, Provenance, and Schema versions.

## Workspace and Slots

`MatchWorkspaceV1` contains only:

```text
match_workspace_contract_version
revision
match_definition
slots
```

The exact canonical `euroskat_36_standard_v1` Match definition is required.
Construction defensively rebuilds all nested Match, participant, snapshot, and
Slot values. A Workspace has exactly 36 Slots in authoritative position order
`1..36`; it has no current-position field, path, fingerprint, Progress, standings,
or generated timestamp.

Each `MatchWorkspaceSlotV1` has one of these exact kinds:

```text
empty
observed_game
passed_deal
```

The payload relationships are exclusive:

| Slot kind | `observed_game` | `passed_deal` |
| --- | --- | --- |
| `empty` | null | null |
| `observed_game` | one exact `ObservedGameRecordV1` | null |
| `passed_deal` | null | one exact `MatchPassedDealV1` |

Partial observed Games are first-class Workspace content. Missing Plays, hands,
original Skat, Discards, commentary, or response links remain missing; Workspace
placement does not infer hidden Cards or complete evidence.

`MatchPassedDealV1` stores only its version and an optional media timecode. It has
no synthetic Game ID, Declarer, Declaration, score, Settlement, role, or
Historical/list entry.

## Rotation and rounds

For every position, Workspace validation builds the fixed-place Player mapping
from the Match participants and calls the existing
`build_fixed_three_player_list_seat_assignment()` helper. Rotation arithmetic is
not duplicated.

The Dealer is always Rearhand. For canonical table places, position 1 has
`place_1` as Dealer/Rearhand, `place_2` as Forehand, and `place_3` as Middlehand.
The Dealer advances at every position, including passed deals. Three positions
form one round:

```text
round_number = ((match_position - 1) // 3) + 1
```

The 36 positions therefore form exactly twelve rounds, and every fixed Match
participant deals twelve times. Observed Game Player order must equal the exact
Forehand, Middlehand, Rearhand assignment for its position.

`MatchWorkspacePositionFactV1` derives one position's round, Slot kind, Dealer,
three historical seats, optional Game ID, Play count, and complete-trace flag.
Position Facts are not persisted.

## Creation and immutable changes

`create_match_workspace_v1(match_definition)` creates revision zero with 36
empty Slots. It generates no Game ID, path, or timestamp.

The immutable update functions are:

```python
set_match_workspace_observed_game_v1(...)
mark_match_workspace_passed_deal_v1(...)
clear_match_workspace_slot_v1(...)
replace_match_workspace_definition_v1(...)
```

Every update requires `expected_revision`. The normal statuses are:

```text
applied
unchanged
revision_conflict
```

Revision conflict is checked before target semantics. A conflict returns the
exact source Workspace. A semantically equal valid change is `unchanged` and
also returns the source Workspace. An applied change increments revision by
exactly one and returns a newly validated Workspace. The previous Slot is
retained in Slot-operation Results; definition replacement has no target Slot.

An observed Game may replace an empty Slot, a passed deal, an earlier partial
Game, a complete Game, or another Game at the same position. A passed deal may
replace empty or observed content. Clearing an occupied Slot applies one change;
clearing an empty Slot is unchanged. Game IDs must remain globally unique across
the Workspace.

## Match-definition correction

Definition replacement may correct descriptive values, including:

```text
title
game platform
external Match ID
played_at
source metadata and bounds
Player labels
platform Player IDs
Player Statistics Snapshots
```

It must preserve:

```text
Match ID
euroskat_36_standard_v1 format
Participant Player IDs
Participant table places
perspective Player ID
```

Every retained observed Game and passed-deal timecode is revalidated against the
replacement source bounds. Existing observed Games and Slots are otherwise
unchanged.

Issue #166 set/clear operations rebuild only the selected participant and use
this same definition replacement exactly once. Applied updates increment
revision once and preserve all 36 Slots; equal or conflicted updates preserve
revision. The existing Workspace fingerprint and strict persistence already
cover complete Snapshots, including historical aggregation provenance, so no
persistence migration or new field is required.

## Time ordering

An occupied Slot's effective timecode is its observed Game timecode or passed-
deal timecode. Empty Slots and missing timecodes contribute no ordering value.
Present start offsets must be non-decreasing in Match-position order. Equal
starts, overlapping intervals, missing intermediate values, and out-of-order
data entry are valid when the resulting Workspace order is valid. All present
child timecodes remain subject to existing Match-source containment rules.

## Progress

`build_match_workspace_progress_v1()` derives Progress from the current Slots.
It does not persist or materialize downstream values. The status is:

```text
empty        no occupied Slots
in_progress  1 through 35 occupied Slots
complete     all 36 Slots classified
```

`complete` is structural only. It does not mean every observed Game has 30
Plays, complete hands, Skat, Discards, commentary, or materialization-ready
evidence.

Progress reports exact empty, observed-Game, passed-deal, occupied, and evidence-
capability counts plus commentary, response-link, and next-empty-position counts.
For each observed Game it reuses
`build_observed_game_evidence_summary_v1()`; it does not duplicate evidence rules.

## Fingerprints

The Workspace fingerprint is lowercase SHA-256 over compact, key-sorted,
ASCII-escaped, finite canonical JSON for the complete validated
`workspace.to_dict()`, prefixed by the NUL-separated domain:

```text
skatmind\0match_workspace_v1\0
```

It includes revision, Match metadata and snapshots, all Slot kinds, observed
facts, passed-deal timecodes, Plays, commentary, and response links. It excludes
path and environment data. Equal numeric revisions can therefore have different
Workspace fingerprints.

The content fingerprint uses the separate domain:

```text
skatmind\0match_workspace_persistence_v1\0
```

Its material contains persistence version, document kind, Workspace fingerprint,
and the complete Workspace. Only `content_fingerprint` itself is excluded.
Caller mapping order and file formatting do not affect either identity.

Fingerprints provide deterministic identity and consistency verification. They
do not provide confidentiality, authenticated authorship, or provenance.

## Strict persistence and Resume

`MatchWorkspacePersistenceDocumentV1` contains exactly:

```text
match_workspace_persistence_version
document_kind
workspace_fingerprint
content_fingerprint
workspace
```

It contains no path, save time, Progress, analysis, or materialized result.

`resume_match_workspace_document_v1()` requires exact field sets and strictly
reconstructs every nested Match source, timecode, canonical tournament format,
participant, Statistics Snapshot and record, Declaration, observed Player, Play,
commentary, response link, observed Game, passed deal, Slot, and Workspace through
their existing constructors or builders. It rejects missing or unknown fields,
invalid versions, non-canonical arrays, invalid linkage or rotation, chronology
conflicts, and either fingerprint mismatch. Progress is freshly derived after
verification and is not persisted authority.

Malformed or tampered persisted content raises `SkatMindValidationError`. A
post-verification disagreement among internally produced values raises
`SkatMindInvariantError`.

## File Load and Save

`load_match_workspace_file_v1()` requires a regular file and strict UTF-8 without
a BOM. It rejects invalid UTF-8, malformed JSON, duplicate keys at any depth,
NaN, infinity, non-object roots, and every strict Resume failure.

Canonical save bytes use `ensure_ascii=True`, two-space indentation, LF line
endings, and exactly one trailing LF. Save requires an existing parent directory
and never creates directories, chooses a default path, creates a backup, retries,
or merges content.

Save compares the caller's expected content fingerprint with the currently
verified target:

| Target | Expected | Result |
| --- | --- | --- |
| missing | null | `saved` |
| missing | non-null | `conflict` |
| existing | null or different | `conflict` |
| existing | equal and requested content equal | `unchanged` |
| existing | equal and requested content different | `saved` |

Invalid existing content is never overwritten. An actual write uses one unique
same-directory temporary file, completes the write, flushes, file-`fsync`s,
strictly revalidates the target, atomically calls `os.replace`, attempts a best-
effort directory `fsync`, and cleans up its owned temporary file on failure.
The old target is preserved before replacement failures.

This is optimistic conflict detection, not distributed locking. Another writer
can still race after the final target check and before replacement. No lock,
retry, merge, cloud, or multi-user coordination claim is made.

## Private-data boundary

Workspace files are private local working data. They may contain source URLs and
titles, Player Statistics, perspective hands, Plays, original Skat, Discards,
free-text commentary, and response links. No public redaction is applied.
Callers are responsible for file location, operating-system permissions, copies,
and backups.

Workspace files do not store Search Worlds, Simulation ownership, Analysis
Results, internal Provenance, or synthetic hidden Cards.

## Execution bounds

Workspace validation and each immutable change inspect exactly 36 Slots.
Position Facts and Progress inspect the same bounded array; Progress derives each
retained observed-Game evidence summary once. Fingerprint construction performs
two SHA-256 hashes per persistence build or Resume. Save performs no retry or
merge loop; its only data-dependent loop completes the finite canonical byte
write.

## Current boundary

Issue #163 adds only the internal Workspace, operations, Progress, fingerprints,
strict persistence, Resume, Load, and Save layers. Issue #164 adds internal rapid
card-entry Application services over those unchanged operations. Position Views
and returned Progress are derived, not persisted, and no Capture operation loads
or saves a Workspace. See
[Match Capture Application services](match_capture_application_services.md).

Issue #165's leaf transport composes those operations with strict startup Resume,
one locked explicit-file context, exact-revision changes, content-fingerprint
CAS Save, unchanged/conflict no-write behavior, and explicit Reload. See
[Local Match Capture interface](local_match_capture_interface.md).
Issue #166 adds Match-bound Snapshot editing and time-safe eligible Statistics
preparation without applying a Profile. See
[Match Player Statistics](match_player_statistics.md).
Issue #167 adds a separate internal traversal over all 36 authoritative Slots.
It reports materialization status `empty`, `partial`, or `complete`; exact
Decision, skipped, Historical, Training-source, Passed Deal, Commentary, and
Response-Link counts; and one per-Slot value. Strict Historical Games require
normal-completion complete-Deal evidence. Passed Deals create no synthetic Game,
and a complete materializable Workspace reuses the existing fixed-list builder,
aggregation, Progression, standings, and external-lot behavior. Commentary and
Response Links remain Workspace sidecars. See
[Match review and materialization](match_review_and_materialization.md).

Issue #168 separately derives ephemeral reports and private downloads without
changing Workspace fields or persistence bytes. It adds explicit private
Position/Historical execution and existing-behavior eligible Profile application;
reports remain process-local and are never persisted. Public Match API, Match
Schema/data workflow, public Match export, YouTube integration, and EuroSkat
integration remain absent.

Issue #171 keeps the Workspace as editable authoritative capture source and can
retain one exact strictly resumed persistence document as a separate immutable
content-addressed Learning Corpus Match Snapshot. Corpus construction never
mutates the Workspace or changes its persistence bytes. Corrected Workspace
content becomes a distinct Snapshot. The lightweight Corpus Catalog embeds no
Workspace. Issue #172 can strictly import one explicit Workspace file into a
separate fixed-root private Corpus without mutating the source file or changing
Workspace persistence bytes. Issue #176's in-memory Dataset version `2` likewise
does not mutate Workspace persistence. Issue #179 adds private browser import
and exact executed-Decision Report-source transfer without changing those bytes.
Derived-artifact persistence, Historical Report import, and public exposure
remain open. See
[Learning Corpus identity and Catalogs](learning_corpus_identity_and_catalogs.md)
[Learning Corpus persistence and Workspace import](learning_corpus_persistence_and_import.md),
[Learning Dataset version 2](learning_dataset_v2.md), and
[Learning Corpus browser workflows](learning_corpus_browser_workflows.md).

The published Package baseline is `0.15.0`; seven Root workflows, Public API and
CLI contracts, 63 authoritative and packaged Schemas, six Session examples, and
85 generated-output scenarios remain unchanged. The maintainer published
`v0.15.0` manually at commit `ec1c154`, and Issue #170 synchronizes publication
status.
