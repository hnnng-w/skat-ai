# Learning Corpus Player Catalog and Statistics history

Issue #173 adds a private internal version-1 Player Catalog and time-safe
multi-Match Statistics history to the
`v0.16.0 - Learning-ready behavior and communication data` milestone. The
Catalog is deterministic derived data. It is not persisted, does not change
`catalog.json`, and does not change Match Snapshot object files.
Issue #174 reuses the same narrow Current-Snapshot resolver for a separate Human
Evidence builder; it does not consume or change this Player Catalog.

## Source boundary

The source-of-truth chain is:

```text
editable Match Workspace:
    authoritative capture source

immutable Learning Corpus Match Snapshot:
    imported source copy

Learning Corpus Catalog:
    authoritative retained membership and explicit Current selections

Learning Corpus Player Catalog:
    derived current-Snapshot Player view

Statistics Selection:
    time-safe query over retained exact observations
```

`build_learning_corpus_player_catalog_v1()` accepts one exact
`LearningCorpusStoreResumeResultV1`, strictly validates it once in memory, and
uses only the Match Snapshots selected by `current_matches`. Retained non-current
revisions and valid orphan objects contribute no Player, alias, label, or
Statistics observation. Current Matches are resolved in Match-ID order, and each
Current Snapshot is traversed once. The operation performs no file or network
I/O.

Changing an explicit Current selection changes the next derived Player Catalog.
Version 1 has no all-revisions mode and never infers a newest Snapshot.
Issue #179 can trigger that derivation explicitly in the private local browser
and download the exact process-local Catalog. It does not persist the Catalog,
select a canonical label, or change the derivation contract. See
[Learning Corpus browser workflows](learning_corpus_browser_workflows.md).

## Versions and policies

The independent versions are:

```text
LEARNING_CORPUS_PLAYER_CATALOG_VERSION = 1
LEARNING_CORPUS_PLAYER_MATCH_OBSERVATION_VERSION = 1
LEARNING_CORPUS_PLATFORM_ALIAS_VERSION = 1
LEARNING_CORPUS_PLAYER_STATISTICS_OBSERVATION_VERSION = 1
LEARNING_CORPUS_PLAYER_STATISTICS_SELECTION_VERSION = 1
```

The stable tuples are:

```text
LEARNING_CORPUS_PLATFORM_ALIAS_SOURCES = (
    match_participant,
    statistics_source,
)

LEARNING_CORPUS_PLATFORM_ALIAS_RESOLUTION_STATUSES = (
    not_observed,
    resolved,
    conflict,
)

LEARNING_CORPUS_PLAYER_STATISTICS_SELECTION_MODES = (
    latest_unambiguous,
    explicit_observation,
)

LEARNING_CORPUS_PLAYER_STATISTICS_SELECTION_STATUSES = (
    available,
    unavailable,
)
```

Unavailable reasons are, in order:

```text
player_not_found
target_time_unavailable
no_statistics_history
no_prior_snapshot
explicit_observation_not_found
explicit_observation_not_before_target
ambiguous_latest_instant
```

The exact policies retain explicit Current Match Snapshots only, observed labels
without canonicalization, exact aliases without merge, Match-bound Statistics
observations without merge, strict-before-target temporal eligibility, latest
unambiguous content only, explicit temporal eligibility, no source combination,
rebuild without persistence, and private local unredacted history. The existing
stable Player policy remains
`exact_stable_player_ids_without_fuzzy_merge`.

## Canonical identity

All new IDs and fingerprints reuse the finite Issue #171 canonical JSON:

```text
UTF-8
ensure_ascii = true
allow_nan = false
sort_keys = true
separators = (",", ":")
```

The six SHA-256 domains are:

```text
skat-ai\0learning_corpus_player_catalog_v1\0
skat-ai\0learning_corpus_player_match_observation_v1\0
skat-ai\0learning_corpus_platform_alias_observation_v1\0
skat-ai\0learning_corpus_platform_alias_conflict_v1\0
skat-ai\0learning_corpus_player_statistics_record_v1\0
skat-ai\0learning_corpus_player_statistics_observation_v1\0
```

Paths, current time, filesystem metadata, environment values, and import order do
not enter identity. Existing Corpus, Workspace, Match Snapshot, Session, and
Analysis fingerprints are unchanged.

## Player observations and entries

Each Current Match contributes exactly three
`LearningCorpusPlayerMatchObservationV1` values. Each value references the exact
Issue #171 Player Observation and retains stable Player ID, Match and Snapshot
identity, Workspace revision, table place, nullable source label and platform ID,
Match title/external ID/played time, source kind/title, Perspective status, and
nullable Match-bound Statistics Snapshot ID. It retains no path, source URL,
Profile, Analysis Result, or current time.

Player entries group only by exact case-sensitive stable Player ID. Equal labels
do not merge distinct IDs, different labels do not split one ID, and case changes
remain distinct IDs. `observed_labels` contains every unique non-null Match or
Statistics-record label in sorted order. No canonical display label or label
Confidence exists.

Entries order Match observations by Match ID and Snapshot ID, aliases by exact
platform key/source/Match/observation ID, and Statistics observations by parsed
capture instant and observation ID. Counts and Current Snapshot IDs reconcile
with the retained observations.

## Platform aliases

A platform alias is the exact case-sensitive pair:

```text
platform_name
platform_player_id
```

Match-participant observations exist only for non-null participant platform IDs
and use the Match `game_platform`. Statistics-source observations exist only for
`online_platform` records with a non-null source Player ID and use the exact
source name. Manual-entry and historical-games source IDs are not platform
aliases.

Aliases are descriptive evidence, not identity authority. Values are not
trimmed beyond existing validation, normalized, case-folded, fuzzy-matched,
asserted, or mutated. The same exact alias for one stable Player is consistent.
The same alias for multiple stable Player IDs creates one immutable conflict with
canonical Player and observation IDs. No winner, merge, replacement, Confidence,
or recommendation is selected.

`resolve_learning_corpus_platform_alias_v1()` performs a pure exact lookup and
returns `not_observed`, `resolved`, or `conflict`. It never mutates the Catalog or
merges Players.

## Statistics history

Every Match-bound `MatchPlayerStatisticsSnapshotV1` in a Current Match becomes
one `LearningCorpusPlayerStatisticsObservationV1`. The observation retains the
complete exact defensively reconstructed `OpponentStatisticsRecord`, including
source metadata, optional notes, all percentages, optional exact Counts, and
historical aggregation provenance. No source is merged, weighted, averaged, or
overwritten.

The Statistics record fingerprint covers the complete existing canonical record.
Changing Player labels, percentages, exact Counts, source type/name/Player ID,
capture text, notes, or historical provenance changes the fingerprint. The
observation identity additionally includes Current Snapshot ID, stable Player ID,
Statistics Snapshot ID, exact observed timestamp text, and record fingerprint.

The existing Match temporal semantics are shared through
`classify_match_player_statistics_temporal_status_v1()`:

```text
captured_at < source Match played_at:
    eligible

source Match played_at is null:
    match_time_unavailable

captured_at >= source Match played_at:
    captured_not_before_match
```

RFC 3339 values compare as aware instants, so equivalent offsets are equal and
ineligible. Source-Match status is descriptive history. An observation ineligible
for its source Match remains retained and may be strictly eligible for a later
target. The helper derives no Profile.

## Time-safe selection

`select_learning_corpus_player_statistics_as_of_v1()` always uses:

```text
captured_at < target_played_at
```

Candidate IDs contain every eligible observation in chronological order.
Equality, including offset-equivalent text, is ineligible. There is no tolerance,
source priority, file-order behavior, weighting, averaging, or source merge.

`latest_unambiguous` requires no explicit observation ID. It examines only the
latest eligible instant. If all observations at that instant have one exact
record fingerprint, the lexicographically smallest observation ID is selected
and all same-content IDs are reported as equivalents. Different fingerprints at
that instant return `ambiguous_latest_instant`; selection does not fall back to
an older observation.

`explicit_observation` requires one retained SHA-256 observation ID belonging to
the selected stable Player. A strictly earlier observation is returned exactly.
This mode can resolve same-instant content ambiguity but cannot bypass equality
or a later capture. No combined Statistics record is created.

Issue #176 uses only `latest_unambiguous` at each Match `played_at` value, caches
one selection per distinct Player/target-time pair, preserves every selection
status/reason/ID field, and embeds every referenced exact Observation once. It
introduces no explicit override, Profile, Policy, merge, weighting, or averaging.

## Privacy and compatibility

The Player Catalog is private local unredacted derived data. It may retain stable
IDs, labels, platform/source IDs, notes, Counts, historical provenance, Match
titles, and source titles. Fingerprints provide deterministic identity, not
confidentiality or authenticated authorship. No path, external request,
encryption, access-control, cloud, or backup claim is added.

Issue #173 adds no persistence file, Catalog field, object kind, workflow, CLI,
browser operation, Public API, Schema, example, generated scenario, Dataset
sample, Profile derivation, Policy application, or Match Analysis. Issue #180
changes only Package version and Release expectations to `0.16.0`; Python remains
`>=3.13`; seven Root workflows, one
Console Script, 63 authoritative and packaged Schemas, six Session examples, 85
generated outputs, and Training Dataset version `1` target
`actual_card_played` remain unchanged.

Persisted aliases/assertions, Player merge/split operations, Catalog persistence,
all-revision Player views, canonical labels, Human Evidence persistence or
public API/Schema transport, Strategy Teacher Evidence persistence or public
API/Schema transport, automatic Report capture, Historical Report import,
Dataset-v2 persistence and task builders, persisted split artifacts, and model
training remain open. Issue #179's private process-local browser preparation and
download add no public exposure.

The private Current-Snapshot-only minimized Commentary/Response Evidence export
itself is implemented separately by Issue #174. See
[Learning Corpus human Commentary and Response evidence](learning_corpus_human_commentary_and_response_evidence.md).

The private Current-Snapshot-bound exact Decision Report Strategy Teacher
Evidence export is implemented separately by Issue #175. See
[Learning Corpus Strategy Teacher Evidence](learning_corpus_strategy_teacher_evidence.md).

The private unpartitioned task-neutral Dataset version `2` consumes the supplied
exact Player Catalog without rebuilding it. See
[Learning Dataset version 2](learning_dataset_v2.md).

Issue #178 consumes that exact supplied Player Catalog without rebuilding it and
derives descriptive Player and Match summaries without selecting a canonical
label, rating, or ranking. See
[Learning Dataset version 2 cross-game summaries](learning_dataset_v2_cross_game_summaries.md).
