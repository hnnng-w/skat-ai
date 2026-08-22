# Learning Dataset version 2 cross-game summaries

Issue #178 adds private internal descriptive summaries over the exact Learning
Dataset version `2`, Player Catalog, and supplied partition-preparation Results.
The summaries report Counts, Coverage, and existing split availability. They do
not evaluate Players, communication, Teachers, or models.

## Source boundary

`build_learning_dataset_v2_cross_game_summary_v1()` consumes exact in-memory
values:

```text
LearningDatasetV2
LearningCorpusPlayerCatalogV1
one known_player LearningDatasetPartitionPreparationResultV1
one unseen_player LearningDatasetPartitionPreparationResultV1
```

The builder validates the Dataset and Player Catalog once and requires exact
agreement on:

* Corpus ID;
* source Catalog revision;
* Catalog fingerprint;
* Catalog content fingerprint;
* ordered Current Match Snapshot IDs;
* retained, Current, and orphan Snapshot Counts;
* the Player Catalog fingerprint retained by the Dataset.

The builder requires exactly one Result for each canonical partition mode. For
each supplied Result, it rebuilds one partition preparation Request from the
exact Dataset, Player Catalog, Plan mode, seed, and weights. The rebuilt Request
fingerprint must equal the Result and Plan request fingerprint. A complete
Result must retain the exact source Dataset in its Partitioned View. An
unavailable Result is a normal valid source.

The builder does not rebuild the Dataset or Player Catalog, regenerate a Plan,
execute analysis or Search, load or save a file, access a network, evaluate a
model, or train a model.

## Versions and Coverage

The nine independent internal versions are:

```text
LEARNING_DATASET_SUMMARY_PRIMITIVE_VERSION = 1
LEARNING_DATASET_MATCH_SUMMARY_VERSION = 1
LEARNING_DATASET_PLAYER_SUMMARY_VERSION = 1
LEARNING_DATASET_COMMUNICATION_SUMMARY_VERSION = 1
LEARNING_DATASET_STRATEGY_SUMMARY_VERSION = 1
LEARNING_DATASET_PARTITION_READINESS_VERSION = 1
LEARNING_DATASET_READINESS_SUMMARY_VERSION = 1
LEARNING_DATASET_CROSS_GAME_SUMMARY_VERSION = 1
LEARNING_DATASET_SUMMARY_EXPORT_VERSION = 1
```

Coverage statuses are:

```text
absent
partial
complete
```

Coverage families are:

```text
decision_state
observed_behavior
player_context
strategy_teacher
human_commentary
linked_response
```

`absent` means the covered Count is zero. `partial` means the covered Count is
positive and below the total. `complete` means the covered Count equals a
positive total. A zero denominator is `absent`. Coverage stores exact covered,
uncovered, and total integer Counts and no floating-point percentage.

Decision-state Coverage uses all observed Decisions as its denominator. The
five evidence-family Coverage values use safe Records as their denominator.
Observed behavior and structural Player Context are present for every safe
Record; Player Context selection availability is reported separately.

## Summary primitives

`LearningDatasetSummaryCategoricalCountV1` stores one exact category and
non-negative Count. `LearningDatasetSummaryIntegerCountV1` stores one integer
value and non-negative Count. Category tuples are unique and canonical; integer
tuples are unique and ascending.

`LearningDatasetSummaryCoverageV1` adds one domain-separated Coverage identity
and exact Count reconciliation. No primitive stores a rate, average, score,
grade, or threshold.

## Match summaries

One `LearningDatasetMatchSummaryV1` exists for every Current Match Snapshot.
Values are ordered by Match ID and Snapshot ID. Each Summary retains Match and
Snapshot identity, optional played time, three stable Players in table-place
order, and the exact Perspective Player.

The Match Summary reports:

* observed Games represented by Decision references;
* safe Records, skipped Decisions, and Decision-state Coverage;
* game-type, acting-side, acting-seat, Trick-number, and play-index Counts;
* forced choices with exactly one legal Card;
* multi-choice Decisions with more than one legal Card;
* available and unavailable Player Context selections;
* Strategy Teacher, Commentary, and Response Counts;
* Records with each optional evidence family;
* unjoined Commentary and Response Counts.

The per-Match observed-Game Count is the number of distinct Game Reference IDs
represented by safe or skipped Decisions. A valid observed Game with no Decision
therefore contributes to the exact global Dataset observed-Game Count but not to
a per-Match Decision-represented Count; the prescribed Dataset/Catalog source
boundary exposes no per-Match allocation for such a Game.

Legal Card identities are not emitted. The legal Card list is used only for its
exact nonzero cardinality. Match summaries contain no hand, Skat, Discards,
Teacher metrics, Statistics content, outcomes, Settlement, rating, or quality
value.

## Player summaries

One `LearningDatasetPlayerSummaryV1` exists for every exact stable Player in the
supplied Player Catalog. Players are ordered by stable Player ID. The Summary
retains all observed labels without selecting a canonical label, Match and
Snapshot IDs, Match Count, Perspective Match Count, and the full retained
Statistics Observation Count.

Acting safe and skipped Decisions are counted by game type, side, seat, Trick,
and play index. Forced-choice and multi-choice Counts use only legal-Card
cardinality. Exact observed Card frequencies use the canonical full-deck order
and describe behavior only.

Player Context Counts include every `me`, `left`, and `right` reference to the
Player. Availability and exact existing unavailability reasons remain separate
from the complete Statistics history Count.

Strategy fields report Evidence Count, distinct Decisions, Recommendation
availability, and exact observed/Recommendation Card Match or Difference
Counts. A Match means only exact Card equality. Commentary fields distinguish a
Player as subject from a Match-Player author. External commentator names are
never resolved to a stable Player. Response fields retain outgoing, incoming,
same-Trick, and later-Trick association Counts.

No Player Summary contains a rate, average, score, grade, rating, ranking, or
quality assessment.

## Communication summary

`LearningDatasetCommunicationSummaryV1` uses joined Human Evidence structure and
the explicit unjoined Counts. It reports:

* Commentary and distinct commented-Decision Counts;
* every canonical commentator identity kind, including zero Counts;
* Perspective and non-Perspective subjects;
* Commentaries with and without joined Responses;
* Response, same-Trick, and later-Trick Counts;
* ascending Decision-offset Counts;
* subject and response role and seat Counts;
* canonical `subject->response` role and seat pair Counts;
* unjoined Commentary and Response Counts.

The Summary never reads, emits, normalizes, classifies, or groups Commentary
text. It emits no external commentator name, Card, sentiment, topic, taxonomy,
intent, quality, success, correctness, or causal value. A Response Link remains
the caller's factual association.

## Strategy summary

`LearningDatasetStrategySummaryV1` reports exact method-bound Strategy Teacher
structure:

* Evidence and distinct Decision Counts;
* multi-Teacher Decision Count and maximum Teachers per Decision;
* distinct semantic fingerprint and semantic duplicate-group Counts;
* Recommendation available and unavailable Counts;
* requested and effective method Counts;
* all canonical Search-status Counts;
* fallback, Profile-Preset-enabled, and Profile-application-summary Counts;
* exact observed/Recommendation Card Match, Difference, and unavailable Counts.

Requested-method Counts use the four canonical flat methods and include
`information_set_search`; effective-method Counts include
`bounded_information_set_policy_search_v1` when retained. Existing Search-status,
fallback, Profile, recommendation, and exact Card-equality semantics are
unchanged.

A semantic duplicate group contains more than one exact Evidence value with the
same existing semantic fingerprint. Values are not merged. The Summary does not
average Candidate or Search metrics, select a Teacher, create consensus, vote,
weight, rank, or call exact Card equality accuracy.
Information-set Candidate metrics, policy quality, World quality, and comparison
deltas are not aggregated.

## Partition readiness

One `LearningDatasetPartitionReadinessV1` exists for `known_player` and one for
`unseen_player`. Each value retains the supplied mode, algorithm, status,
unavailable reason, request and Plan fingerprints, seed, weights, and source
active, inactive, Record, and skipped-Decision Counts.

A complete Result additionally retains the exact existing three Partition
Summaries, compliant leakage status, and all-partitions-have-Records fact.
Known-player readiness reports time-group Count plus Validation and Test Train-
coverage facts. Unseen-player readiness reports component Count, Player
disjointness, and local move/swap optimality facts. Mode constraints are true
only when every matching supplied compliance fact is true.

An unavailable Result retains no Partition Summary or audit detail. Readiness
embeds no assignment, Partitioned View, or source Dataset and never regenerates a
Plan. `complete` means only that the existing split contract succeeded. It is not
a model-readiness or Dataset-sufficiency claim.

## Dataset readiness

`LearningDatasetReadinessSummaryV1` retains Dataset status, Decision-state and
evidence-family Coverage, both fixed skipped reasons including zero Counts,
Player Context totals and exact unavailability reasons, selected Statistics
Context Count, Statistics Observation pool Count, unjoined Human Evidence
Counts, and both supplied partition-readiness values.

It defines no `model_ready` field, minimum size, statistical power, production
readiness, evaluation result, or training decision.

## Cross-game summary and identity

`LearningDatasetCrossGameSummaryV1` retains exact Dataset, Player Catalog,
Corpus, and Catalog fingerprints and Counts, canonical Match and Player
Summaries, Communication Summary, Strategy Summary, and Dataset Readiness
Summary. It embeds no source Dataset, Player Catalog, Plan, Commentary value,
Response value, Strategy Teacher value, or Statistics record. An empty Corpus
produces a valid empty Summary.

All identities reuse finite Learning Corpus canonical JSON:

```text
UTF-8
ensure_ascii = true
allow_nan = false
sort_keys = true
separators = (",", ":")
```

The ten required domain-separated SHA-256 families are defined for Summary
Counts, Coverage, Match, Player, Communication, Strategy, Partition Readiness,
Dataset Readiness, Cross-game Summary, and Export. The exact Count primitive
contracts contain no identity field, so the Count domain is reserved while
stored identities begin with Coverage. Exact source fingerprints are part of the
final Summary identity. A Commentary-text or Teacher Candidate-metric change
can therefore change the source Dataset and final Summary fingerprint while
leaving descriptive grouping Counts unchanged.

## Export and privacy

The path-free document kind is:

```text
skat_ai_learning_dataset_v2_cross_game_summary
```

`build_learning_dataset_v2_cross_game_summary_export_v1()` accepts one already-
built Summary and does not rebuild it. The Export ID covers export version,
document kind, Summary fingerprint, and complete Summary value.

`serialize_learning_dataset_v2_cross_game_summary_export_v1()` accepts no path,
writes no file, and returns deterministic UTF-8 JSON with ASCII escaping, finite
values, two-space indentation, LF line endings, and one trailing LF.

The private Summary may retain stable Player, Match, Snapshot, source
fingerprint, category Count, and exact Card-frequency metadata. It contains no
complete hand, Skat, Discards, Commentary text, external commentator names,
source URL, complete Statistics record, Candidate metrics, Search World, Search
state, or per-Decision Recommendation.

Fingerprints provide deterministic identity, not confidentiality, authorship,
encryption, access control, backup, or secure storage.

## Compatibility and open work

Issue #178 adds no persistence, Corpus object kind, Catalog field, browser, CLI,
Public API, Root workflow, Schema, example, generated scenario, evaluation, or
training. Issue #179 explicitly builds this Summary last from the exact Dataset,
Player Catalog, and both just-prepared Results in a private local browser and
offers a canonical authenticated download. The Summary remains process-local and
non-persisted; no Public API or Schema is added. See
[Learning Corpus browser workflows](learning_corpus_browser_workflows.md).
Issue #180 changes only Package version and Release expectations to `0.16.0`;
Python remains `>=3.13`; Public API
contract version remains `1`; seven Root workflows, one Console Script, 63
authoritative and packaged Schemas, six Session examples, 85 generated outputs,
Learning Dataset version `2`, and Training Dataset version `1` target
`actual_card_played` remain unchanged.

Summary and Dataset-v2 persistence and public transport, task-specific Feature
and Target builders, communication taxonomies, derived tags, annotation
Confidence, Player Ratings and rankings, model evaluation and baselines, and
model training remain open.

Issue #191 extends only the values counted by this existing Summary contract.
Summary version `1`, Dataset version `2`, fields, persistence, Public API, Schema,
evaluation, and rating boundaries remain unchanged. See
[Match Information-set Search and Strategy Teacher Evidence](match_information_set_search_and_strategy_teacher.md).
