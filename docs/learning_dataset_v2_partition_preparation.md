# Learning Dataset version 2 partition preparation

Issue #177 adds private internal group-safe partition preparation and leakage
audits for Learning Dataset version `2`. It consumes one already-built exact
`LearningDatasetV2` and its exact `LearningCorpusPlayerCatalogV1`; it does not
rebuild either source.

This layer remains separate from public Training Dataset version `1`. Training
Dataset version `1` still partitions complete Historical Game records and uses
the target `actual_card_played`. Dataset-v2 preparation partitions private,
task-neutral evidence metadata and defines no target, label, reward, Feature
list, Teacher selection, communication category, evaluation, or model task.

## Versions and fixed vocabulary

The seven independent versions are:

```text
LEARNING_DATASET_PARTITION_PREPARATION_VERSION = 1
LEARNING_DATASET_MATCH_GROUP_VERSION = 1
LEARNING_DATASET_PLAYER_COMPONENT_VERSION = 1
LEARNING_DATASET_PARTITION_PLAN_VERSION = 1
LEARNING_DATASET_PARTITION_AUDIT_VERSION = 1
LEARNING_DATASET_PARTITIONED_VIEW_VERSION = 1
LEARNING_DATASET_PARTITION_EXPORT_VERSION = 1
```

The canonical partitions remain:

```text
train
validation
test
```

Modes and their sole algorithms are:

```text
known_player
    -> temporal_known_player_match_group_v1

unseen_player
    -> component_balanced_unseen_player_match_group_v1
```

There is no algorithm override, fallback, automatic mode change, Partial Plan,
or default partition weight. Each Train, Validation, and Test weight is an
explicit strict positive integer.

## Source reconciliation

The Request reconciles the Dataset and Player Catalog by exact:

* Corpus ID;
* source Catalog revision;
* Catalog fingerprint;
* Catalog content fingerprint;
* ordered Current Match Snapshot IDs;
* retained, Current, and orphan Snapshot counts;
* Player Catalog fingerprint retained by the Dataset.

Malformed or stale source values are validation errors. An inability to produce
three valid partitions is instead a normal `unavailable` Result.

## Active Match groups

One Current Match Snapshot is active when it contains at least one Dataset
Record or one skipped Decision. A skipped-only Snapshot is active and remains an
indivisible zero-Record assignment unit. A Current Snapshot containing neither a
Record nor a skipped Decision is inactive, receives no assignment, and remains
listed in `inactive_current_match_snapshot_ids`.

Each active `LearningDatasetMatchGroupV1` contains only split-safe identity and
count facts:

* Match Snapshot and logical Match IDs;
* Match `played_at` text;
* exactly three sorted stable Player IDs from matching Player Catalog Match
  observations;
* source-ordered Record and skipped Decision IDs;
* reconciled Record, skipped, and observed Decision counts;
* diagnostic Teacher, Commentary, Response, and unjoined Human Evidence counts.

The diagnostic evidence counts never influence assignment. All Records, skipped
Decisions, Teachers, Commentary, Responses, and unjoined Human Evidence from one
Match Snapshot follow that Match assignment.

## Identity and information boundary

Compact identities reuse the finite Learning Corpus canonical JSON contract:

```text
UTF-8
ensure_ascii = true
allow_nan = false
sort_keys = true
separators = (",", ":")
```

The exact SHA-256 domains are:

```text
skatmind\0learning_dataset_v2_partition_source_identity_v1\0
skatmind\0learning_dataset_v2_partition_source_content_v1\0
skatmind\0learning_dataset_v2_partition_request_v1\0
skatmind\0learning_dataset_v2_match_group_v1\0
skatmind\0learning_dataset_v2_player_component_v1\0
skatmind\0learning_dataset_v2_partition_plan_v1\0
skatmind\0learning_dataset_v2_partition_audit_v1\0
skatmind\0learning_dataset_v2_partitioned_view_v1\0
skatmind\0learning_dataset_v2_partition_export_v1\0
```

Mode-specific seed domains are:

```text
learning_dataset_v2_known_player_split_v1
learning_dataset_v2_unseen_player_split_v1
```

The source identity fingerprint uses only Dataset ID/version, Match Snapshot and
Match IDs, Match times, stable Player IDs, Record and skipped Decision IDs,
counts, and mode. Evidence enrichment that preserves those facts preserves the
source identity. The separate source content fingerprint covers the exact
Dataset fingerprint, exact Player Catalog fingerprint, mode, and complete Match-
group diagnostics.

Assignment may additionally use explicit positive weights and the caller seed.
It never uses Cards, hands, legal Cards, declarations, observed behavior values,
Statistics contents, Teacher methods or metrics, recommendations, Commentary
text or commentator identity, Response Cards, evidence-family presence, Record
content fingerprints, source URLs, outcomes, or Settlement.

## Exact balance objective

Balancing uses exact integer arithmetic. For each partition and basis, the
signed deviation numerator is:

```text
partition_count * total_weight - source_count * partition_weight
```

The lexicographic objective is:

1. total absolute Record-count deviation;
2. maximum absolute Record-count deviation;
3. Train, Validation, and Test Record deviations;
4. total absolute Match-count deviation;
5. maximum absolute Match-count deviation;
6. Train, Validation, and Test Match deviations.

Record Count is primary and Match Snapshot Count is secondary. Skipped Decision,
Player, sample, Teacher, Commentary, and Response counts are not balance bases.
No floating-point ratio is calculated. The seed is consulted only after an exact
objective tie and cannot replace a strictly better objective.

## Known-player mode

`temporal_known_player_match_group_v1`:

1. requires at least one safe Record, three active Match groups, and enough
   Records for three non-empty Record partitions;
2. requires `played_at` on every active Match group;
3. parses RFC 3339 values through the existing parser and groups offset-
   equivalent equal instants;
4. exhaustively evaluates every pair of chronological cut boundaries without
   splitting an equal-time group;
5. requires at least one Record in each partition;
6. requires every Validation and Test Player to occur in Train;
7. minimizes the exact Record-primary, Match-secondary objective.

Every complete Plan proves:

```text
max(train.played_at) < min(validation.played_at)
max(validation.played_at) < min(test.played_at)
```

The temporal audit reports canonical UTC boundaries, time-group and Match/Record
counts, all partition Player sets, covered and uncovered later Players, equal-
time preservation, and strict chronology. There is no shuffle or non-temporal
fallback.

## Unseen-player mode

`component_balanced_unseen_player_match_group_v1` connects active Match groups
through exact shared stable Player IDs. Connectivity is transitive. Every
`LearningDatasetPlayerComponentV1` retains canonical Match Snapshot and Player
IDs plus diagnostic counts and remains indivisible, including skipped-only
zero-Record groups.

The algorithm requires at least three components and at least three positive-
Record components. It orders components by descending Record Count, Match Count,
and Player Count, followed by the seed tie key and Component ID. It initializes
the three partitions with distinct positive-Record components, greedily places
the remainder through the exact objective, and repeatedly accepts only strict
whole-component move or swap improvements. Every move or swap preserves a
positive Record Count in all partitions.

The component audit proves exact Player disjointness, one assignment per
component, positive Record coverage, and local move/swap optimality. This is a
deterministic local optimum for the declared neighborhood. It is not a global-
optimality, exact-ratio, Player-count-balance, or component-splitting claim.

## Leakage audit

Every complete Plan contains one compliant general leakage audit and one
compliant mode-specific audit. The general audit covers:

* complete and unique active Match Snapshot assignment;
* no Match Snapshot or logical Match overlap;
* Record and skipped Decision closure;
* Teacher closure through its Record;
* Commentary closure through its subject Record;
* Response closure through both subject and response Records;
* unjoined Commentary and Response closure through associated skipped Decisions;
* strict `captured_at < target_played_at` safety for every candidate, selected,
  equivalent, and ambiguous Statistics Observation reference.

The same prior Statistics Observation may be used in more than one Known-player
partition. The audit reports that sharing diagnostically and remains compliant.
Shared Player-specific Statistics Context across unseen-player partitions is a
violation.

## Plans, slices, and views

A `LearningDatasetPartitionPlanV1` is exactly `complete` or `unavailable`.

A complete Plan contains one assignment per active Match Snapshot, three
canonical partition summaries, one matching mode audit, one compliant leakage
audit, and a deterministic fingerprint. Summaries retain exact weights, Match,
Record, skipped, observed, Teacher, Commentary, Response, and distinct-Player
counts plus exact target and deviation numerators.

An unavailable Plan contains one reason and no assignments, summaries, audits,
or partitioned view. Reason precedence is stable and there is no partial output
or fallback.

The partitioned view preserves the exact source `LearningDatasetV2` object and
adds three `LearningDatasetPartitionSliceV1` indexes. Slices contain IDs only:
Match Snapshots, Records, skipped Decisions, Statistics Observations, Teachers,
Commentary, Responses, and unjoined Human Evidence. Source order is preserved.
Statistics usage IDs may overlap in Known-player mode. No Dataset Record or
evidence contract gains a `partition` field.

## Export and privacy

The path-free export document kind is:

```text
skatmind_learning_dataset_v2_partition_preparation
```

The export builder accepts an already-prepared complete or unavailable Result
and does not rerun preparation. Serialization returns deterministic UTF-8 bytes
with ASCII escaping, finite JSON, two-space indentation, LF line endings, and
one trailing LF. It accepts no path and writes no file.

Partition metadata is private local derived data. It may contain stable Match,
Player, Record, and evidence IDs, played times, and counts. It contains no
complete private hand, Skat, Discards, human text, Search World, recommendation
metric, or complete Statistics record. The lossless prepared view intentionally
retains the exact private source Dataset separately from the Plan metadata.
Fingerprints provide deterministic identity, not confidentiality, authorship,
encryption, access control, backup, or secure storage.

Issue #177 adds no Dataset-v2 persistence, Corpus object kind, Catalog field,
Current-selection change, browser, CLI, Public API, Root workflow, Schema,
example, generated scenario, evaluation, cross-game summary, communication
taxonomy, derived tag, task-specific builder, or model training. Issue #180
changes only Package version and Release expectations to `0.16.0`; Python remains
`>=3.13`; seven Root workflows, one Console
Script, 63 authoritative and packaged Schemas, six Session examples, 85
generated outputs, and Training Dataset version `1` remain unchanged.

Issue #178 separately consumes one exact Result for each canonical mode together
with the exact Dataset and Player Catalog. It reports existing complete or
unavailable Partition Readiness without regenerating either Plan or changing
partition preparation. See
[Learning Dataset version 2 cross-game summaries](learning_dataset_v2_cross_game_summaries.md).

Issue #179's browser requires explicit seeds and positive weights, with displayed
defaults `0`, `0`, and `70`/`15`/`15`; those are submitted browser values, not
defaults added to this Request contract. It prepares `known_player` before
`unseen_player`, retains complete or unavailable Results process-locally, and
offers canonical authenticated downloads without persisting a split. See
[Learning Corpus browser workflows](learning_corpus_browser_workflows.md).
