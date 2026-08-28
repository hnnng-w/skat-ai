# Learning Dataset version 2

Issue #176 adds one private internal, unpartitioned, task-neutral Learning
Dataset version `2`. It is a derived in-memory view over exact Current Learning
Corpus sources. It is separate from public Training Dataset version `1`.

Training Dataset version `1` remains unchanged: it requires supported Historical
Game records, creates information-safe samples in explicit Train, Validation,
and Test partitions, and uses the one target `actual_card_played`. Learning
Dataset version `2` defines no universal target, label, reward, quality class,
Teacher winner, communication category, default Feature list, or model task.

## Source boundary

`build_learning_dataset_v2()` requires exact in-memory values:

```text
LearningCorpusStoreResumeResultV1
LearningCorpusPlayerCatalogV1
LearningCorpusHumanEvidenceCollectionV1
LearningCorpusStrategyTeacherEvidenceCollectionV1
```

The builder strictly reconciles their Corpus ID, Catalog revision, Catalog
fingerprint, Catalog content fingerprint, ordered Current Match Snapshot IDs,
and retained/current/orphan counts. It does not rebuild the supplied Player
Catalog or evidence collections and performs no file load, import, save, Match
mutation, analysis, Search, Profile derivation, Root workflow, network request,
partitioning, or Training Dataset conversion.

Only `LearningCorpusCatalogV1.current_matches` contributes. Retained non-current
revisions and orphan objects remain excluded. Current Snapshots are resolved in
canonical Match order. Each Current Workspace and all its traces are validated
once, and each observed Game is reconstructed once.

## Versions and stable tuples

```text
LEARNING_DATASET_VERSION = 2
LEARNING_DATASET_SOURCE_CONTEXT_VERSION = 1
LEARNING_DATASET_DECISION_STATE_VERSION = 1
LEARNING_DATASET_OBSERVED_BEHAVIOR_VERSION = 1
LEARNING_DATASET_PLAYER_CONTEXT_VERSION = 1
LEARNING_DATASET_RECORD_VERSION = 1
LEARNING_DATASET_SKIPPED_DECISION_VERSION = 1
LEARNING_DATASET_EXPORT_VERSION = 1
```

```text
LEARNING_DATASET_STATUSES = (
    empty,
    unavailable,
    partial,
    complete,
)

LEARNING_DATASET_EVIDENCE_FAMILIES = (
    observed_behavior,
    player_context,
    strategy_teacher,
    human_commentary,
    linked_response,
)

LEARNING_DATASET_RELATIVE_PLAYERS = (
    me,
    left,
    right,
)
```

`decision_state` is structural source state, not an optional evidence-family
value. Every Record has observed behavior and three Player Context selection
Results. The remaining evidence families may be absent.

## Policies

The exact stable policy values are:

```text
explicit_current_match_snapshots_only
before_actual_play_information_safe_state
actual_card_is_observed_behavior_not_universal_target
behavior_strategy_and_communication_remain_separate
preserve_exact_human_evidence_without_interpretation
retain_all_method_bound_teacher_evidence_without_preference
latest_unambiguous_strictly_prior_statistics_without_profile_derivation
preserve_selection_status_reason_and_source_observation_ids
unpartitioned_match_snapshot_grouping_reserved_for_later_preparation
task_neutral_no_default_target_or_label
no_derived_communication_tags_in_version_2
private_local_unredacted_learning_evidence
deterministic_path_free_json_document
```

These strings describe contract boundaries. They do not select a model,
operation, Teacher, communication interpretation, or persistence mechanism.

## Record families

Each safe `LearningDatasetRecordV1` keeps these siblings separate:

```text
source_context
decision_state
observed_behavior
player_contexts
strategy_teacher_evidence_ids
commentary_evidence_ids
outgoing_response_evidence_ids
incoming_response_evidence_ids
```

Top-level normalized pools embed each exact referenced Statistics Observation,
Strategy Teacher Evidence, joined Commentary Evidence, and joined Response
Evidence once. Records retain IDs only. The complete Player Catalog and source
collections are not embedded.

Issue #191 carries focused Information-set Strategy Teacher Evidence through the
same existing normalized Teacher pool and ID references. It introduces no new
Record sibling, top-level pool, or evidence family.

### Source Context

`LearningDatasetSourceContextV1` retains exact Match Snapshot, Game Reference,
Match, Workspace revision, Match position, Game, title, optional external ID,
optional played time, platform, descriptive source, optional URL/channel, Match
and Game timecodes, exact observed Play Decision timecode, Perspective Player,
historical seats, and Declarer. It performs no URL fetch or time conversion and
retains no path, private hand, Skat, Discards, Statistics, analysis, or
Commentary.

### Decision State

`LearningDatasetDecisionStateV1` is built from the existing exact
`HistoricalDecisionSnapshot`. The narrow Issue #167 seam accepts one already
validated observed-Game reconstruction and returns safe snapshots, exact skipped
Decisions, and source count without Statistics or Profile derivation. Existing
Match Decision review preparation composes that seam and still derives its
unchanged Profile bindings afterward.

Decision State retains the exact before-play Decision identity, acting Player,
seat and side, `before_actual_play` cutoff, relative stable Player map, and
recursively immutable existing visible state. The visible state may contain the
acting own hand, legal Cards, current and completed public Tricks, prior points,
opponent hand sizes, authorized Skat visibility, and authorized public exposed
Cards.

Decision State excludes the actual Card, future Plays, hidden opponent hands,
final Result, Settlement, Recommendation, Search, Commentary, Response
relations, and Player Profile values.

### Observed Behavior

`LearningDatasetObservedBehaviorV1` contains the Decision Reference and one exact
observed Card. The builder reconciles that Card with the source Play, existing
snapshot, acting hand, legal Cards, and current Trick. It is factual observed
behavior, not an optimal, correct, recommended, target, or label Card.

### Player Context

For `me`, `left`, and `right`, `LearningDatasetPlayerContextV1` copies one exact
existing `latest_unambiguous` Statistics selection at Match `played_at`:

```text
captured_at < played_at
```

It preserves selection status, unavailable reason, candidate Observation IDs,
selected Observation ID, equivalent IDs, and ambiguous IDs. Missing Match time,
missing history, and same-instant different-content ambiguity remain normal
unavailability. There is no explicit-observation override, fallback after
ambiguity, Profile, Confidence, classification, signal, source merge, weighting,
averaging, or Policy derivation.

One Dataset build caches one selection per distinct `(player_id,
target_played_at)` pair. Every Observation referenced by any selection field is
embedded once in Player ID, parsed capture instant, and Observation ID order.

## Safe and skipped Decisions

Every observed Play in Current Snapshots becomes exactly one Record or one
`LearningDatasetSkippedDecisionV1`. Record order and skipped order use Match ID,
Match position, Decision index, and their stable ID.

Skipped Decisions reuse the exact Issue #167 reasons:

```text
acting_hand_unavailable
required_public_hand_unavailable
```

They retain exact Snapshot/Game/Decision identity and associated unjoined Human
Evidence IDs. They contain no guessed state and no duplicate actual Card.
Strategy Teacher Evidence may not reference a skipped Decision.

Dataset status describes only safe Decision-state coverage:

```text
empty        no observed Decision exists
unavailable  observed Decisions exist and all are skipped
partial      at least one Record and at least one skipped Decision exist
complete     every observed Decision has a Record
```

Commentary, Teacher Evidence, Statistics, Historical strictness, partitions, and
model targets do not affect status.

## Evidence joins

Every Strategy Teacher Evidence value joins by exact Decision Reference to one
Record. Snapshot, Game, Decision, acting Player, and actual Card must reconcile.
All distinct Teachers remain in source collection order. No preferred Teacher,
consensus, vote, merge, rank, weight, average, or ground-truth claim is added.
Information-set evidence uses the same exact Current Snapshot, Game, Decision,
acting Player, actual-Card, and source-order reconciliation.

Commentary joins by subject Decision Reference only when that Decision has a
Record. Snapshot, Game, subject identity, and actual Card reconcile. Exact text
and source order are preserved without normalization, taxonomy, interpretation,
or correctness claim. Commentary on a skipped Decision is excluded from the
joined pool, reported in `unjoined_commentary_evidence_ids`, and attached to the
skipped Decision.

A Response joins only when its subject Commentary is joined and both subject and
response Decisions have Records. Its ID is outgoing on the subject Record and
incoming on the response Record, while the exact Response value is embedded once.
If either Record is absent, the Response is reported in
`unjoined_response_evidence_ids` and attached to relevant skipped Decisions. No
causality, signaling success, correctness, or quality is inferred.

## Identity and canonical JSON

Compact identity JSON reuses the Issue #171 contract:

```text
UTF-8
ensure_ascii = true
allow_nan = false
sort_keys = true
separators = (",", ":")
```

Exact SHA-256 domains are:

```text
skatmind\0learning_dataset_v2_source_context_v1\0
skatmind\0learning_dataset_v2_decision_state_v1\0
skatmind\0learning_dataset_v2_observed_behavior_v1\0
skatmind\0learning_dataset_v2_record_v1\0
skatmind\0learning_dataset_v2_record_content_v1\0
skatmind\0learning_dataset_v2_skipped_decision_v1\0
skatmind\0learning_dataset_v2_collection_v2\0
skatmind\0learning_dataset_v2_export_v1\0
```

A Record ID covers only Record version, Match Snapshot ID, and Decision Reference
ID. Evidence enrichment therefore preserves it. The separate Record content
fingerprint covers the complete enriched Record except itself. The Dataset
fingerprint covers every Dataset field except itself, including caller-supplied
case-sensitive Dataset ID, source identities, counts, Records, skipped Decisions,
pools, and unjoined IDs.

Adding Information-set Teacher Evidence therefore preserves the stable Record ID
while changing the enriched Record content fingerprint and Dataset fingerprint
as appropriate.

No path, current time, random value, environment value, filesystem metadata, or
network value participates.

## Dataset and export

`LearningDatasetV2` retains exact source fingerprints and counts; observed Game,
Decision, Record, skipped, selected Statistics Context, pool, Record-with-
evidence, and unjoined evidence counts; ordered Records and skipped Decisions;
normalized evidence pools; and unjoined Human Evidence IDs. All counts and
references reconcile exactly.

The path-free export document kind is:

```text
skatmind_learning_dataset_v2
```

`build_learning_dataset_v2_export_v1()` accepts an already-built Dataset,
validates it once, and calculates an export ID over export version, document kind,
Dataset fingerprint, and complete Dataset value. It does not rebuild the Dataset.

`serialize_learning_dataset_v2_export_v1()` accepts no path, writes no file, and
returns deterministic UTF-8 JSON with ASCII escaping, finite values, two-space
indentation, LF line endings, and exactly one trailing LF. Unicode Commentary
round-trips after JSON parsing.

## Privacy and compatibility

Learning Dataset version `2` is private local unredacted evidence. It may contain
private acting own hands, legal Cards, stable Player IDs, source titles and URLs,
human text, observed Cards, exact Statistics source records, strategy metrics,
and copied Teacher Profile/policy application context. It adds no public
redaction, confidentiality, encryption, access-control, cloud, backup, remote-
storage, authenticated-authorship, or external-request claim. Fingerprints are
deterministic identities, not secrecy controls.

Issue #176 adds no persistence file, Corpus object kind, Catalog field, Current-
selection operation, task-specific Feature or Target builder, derived
communication tag, Confidence, evaluation, cross-game summary, browser, CLI,
Public API, Root workflow, Schema, example, generated scenario, or model training.

Issue #177 adds a separate private preparation layer over this unchanged
unpartitioned source. It keeps each Match Snapshot indivisible and provides two
fixed deterministic modes:

* `known_player` uses strict temporal Match blocks, keeps equal timestamps
  together, and requires every Validation/Test Player to have earlier Train
  context;
* `unseen_player` assigns transitive Player-connected Match components and keeps
  Players disjoint across Train, Validation, and Test.

Both modes use one exact integer Record-primary and Match-secondary objective,
return complete or explicitly unavailable Plans, and require compliant closure,
temporal-safety, and mode-specific leakage audits. Complete Plans produce index-
only lossless partition views and canonical path-free exports. This layer adds no
task, label, persisted split, public workflow, or Training Dataset version `1`
change. See
[Learning Dataset version 2 partition preparation](learning_dataset_v2_partition_preparation.md).

Issue #178 adds a separate private descriptive summary layer over this unchanged
Dataset, its exact Player Catalog, and supplied `known_player` and `unseen_player`
partition Results. It reports exact Match, Player, Communication, Strategy
Teacher, Coverage, Dataset Readiness, and Partition Readiness Counts without text
grouping, rating, ranking, evaluation, or model-readiness claims, and provides a
canonical path-free export. See
[Learning Dataset version 2 cross-game summaries](learning_dataset_v2_cross_game_summaries.md).

Issue #179 explicitly builds this Dataset after the exact Player, Human, and
Strategy Teacher sources in the private local Corpus browser, then prepares
known-player and unseen-player Results and the Summary. The Dataset and all
derived artifacts remain process-local; authenticated canonical download adds no
persistence, Public API, Schema, task, or model claim. See
[Learning Corpus browser workflows](learning_corpus_browser_workflows.md).

Issue #180 changes only Package version and Release expectations to `0.16.0`;
Python remains `>=3.13`; Public API contract version remains `1`; seven Root
workflows, one Console Script, 63 authoritative
and packaged Schemas, six Session examples, 85 generated outputs, Corpus/Match
Workspace/Session persistence bytes, and Training Dataset version `1` target
`actual_card_played` remain unchanged.

Issue #191 changes no Dataset version, field, task, label, partition algorithm,
Schema, or persistence boundary. Its focused Information-set Teacher extension
propagates transitively through the existing pool and joins and into the existing
cross-game method counts. See
[Match Information-set Search and Strategy Teacher Evidence](match_information_set_search_and_strategy_teacher.md).

Issue #195 adds a third, separate private Learning Corpus evidence family for
Tactical Motif observations and explicit skips. It is not a fifth Dataset source,
Record sibling, normalized pool, join, Coverage family, partition fact, Summary
field, target, label, Feature, or task. The four exact inputs listed above,
Dataset version `2`, every Dataset identity/byte, and both partition algorithms
remain unchanged. Human, Strategy Teacher, and Tactical Evidence may reference
the same source Decision but Issue #195 creates no cross-family join. See
[Learning Corpus Tactical Motif evidence and summaries](learning_corpus_tactical_motif_evidence_and_summaries.md).

Issue #196 exact-joins that separate Tactical family with Strategy Teacher
Evidence only in a separate private Tactical Cross-game Coaching Report. The join
does not feed this Dataset, and Coaching IDs, Assessments, Decision consensus,
focus areas, Guidance, Counts, and fingerprints are not Dataset sources, pools,
Records, evidence families, targets, labels, Features, tasks, partitions, or
Summary fields. Dataset version `2`, every identity/byte, and both partition
algorithms remain unchanged. See [Learning Corpus Tactical Cross-game
Coaching](learning_corpus_tactical_cross_game_coaching.md).
