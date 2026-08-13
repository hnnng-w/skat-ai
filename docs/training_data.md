# Training data

`skat-ai` supports a separate versioned workflow that converts supported
historical play prefixes into deterministic training or evaluation records.
It stores provenance and explicit partitions and derives one information-safe
sample for every historical card play. It does not train, select, evaluate, or
deploy a machine-learning model.

Training-data representation remains `partially_supported`. Version 1 accepts
normal completion, declarer concession, defender concession, accepted
declarer-card exposure, defender open play, and open-card throwing. Normal
records produce 30 samples; shortened records produce zero through 29 samples
from their actual play prefix, subject to event prerequisites. Historical end
reasons beyond this bounded set remain unsupported.

A normal-completion record may contain one timed defender-open-play or declarer-
card-exposure continuation and still produces exactly 30 samples. Samples before
the boundary contain no event information; later samples use the existing
relative `public_exposed_cards` feature for the shrinking public hand.
Declared-Ouvert records expose the exact shrinking declarer hand from decision 1
through the same feature.

Issue #161 observed-Game evidence summaries may state that perspective or
all-Player Decision samples are reconstructable. Issue #167 can internally
prepare those information-safe snapshots and, only after strict normal-
completion Historical materialization, create existing unpartitioned Training
source Records in Match-position order. It creates no version-1 Dataset input,
partition, Plan, audit, feature, label, or sample. Free-text Commentary and
Response Links remain Workspace sidecars and are not version-1 features, targets,
labels, categories, or quality values. See
[Match review and materialization](match_review_and_materialization.md).

Issue #168 can prepare that Match materialization explicitly in the private
browser and download the exact unpartitioned Training source collection. This
still runs no Training Dataset Root workflow and creates no Dataset identity,
partition, Plan, audit, sample, feature, or label. The retained historical actual
Card remains behavior evidence and the existing version-1 target only after a
separate Dataset workflow; Match Decision analysis does not reinterpret it as an
optimal label. See [Match analysis and exports](match_analysis_and_exports.md).

## Dataset input

The top-level input contains only `training_dataset_input`:

```json
{
  "training_dataset_input": {
    "schema_version": 1,
    "dataset_id": "online-games-2026",
    "dataset_version": "1",
    "feature_generation_version": 1,
    "target": "actual_card_played",
    "partition_policy": {
      "policy_version": 1,
      "mode": "known_opponent"
    },
    "records": []
  }
}
```

`schema_version`, `feature_generation_version`, and supplied policy version
currently accept only `1`.
The only version-1 target is `actual_card_played`. Dataset IDs and versions are
opaque, case-sensitive, non-empty, and may not have leading or trailing
whitespace. They are not package versions.

The workflow is mutually exclusive with position analysis,
`historical_game_input`, list-performance inputs, impossible-Null settlement,
profiles, and opponent-policy settings.

Issues #131 through #133 define the retained version-1 preparation request and
mode-specific generators; Issue #134 exposes them through the separate public
root `training_dataset_preparation_input`. Its Records do not contain
`partition`. It requires explicit positive integer Train/Validation/Test weights
and generates either a deterministic temporal Known-opponent or Player-disjoint
unseen-player Plan. The mode derives the algorithm, so the request has no
algorithm field. It does not change the partitioned `training_dataset_input`
shown above. See
[Automatic dataset preparation contracts](automatic_dataset_preparation_contracts.md)
and [Temporal Known-opponent dataset splits](temporal_known_opponent_dataset_splits.md).
The unseen-player generator is documented in
[Player-disjoint unseen-player dataset splits](player_disjoint_unseen_player_dataset_splits.md).

## Records and provenance

Every record contains:

```json
{
  "record_id": "record-001",
  "partition": "train",
  "provenance": {
    "source_type": "online_platform",
    "source_name": "Example platform",
    "source_record_id": "platform-game-123"
  },
  "historical_game": {}
}
```

Supported partitions are `train`, `validation`, and `test`. Input record order
is preserved. Each `historical_game` uses the existing version-1 historical
structure and the existing validator and replay; the dataset workflow does not
define a second game validator.

If the historical game supplies `played_at`, canonical record output preserves
it. Record and sample source provenance also exposes `source_played_at`. The
timestamp remains metadata and is never a model-facing feature. Existing dataset
records without a historical timestamp remain valid and behaviorally unchanged.

Every provenance object requires `source_type` and `source_name`. Supported
source types are `online_platform`, `manual_entry`, `imported_file`, `synthetic`,
and `other`. Optional fields are `source_record_id`, RFC 3339 `collected_at`, and
`notes`. Supplied strings must be non-empty and unpadded. Unknown fields are
rejected, and accepted provenance is preserved in output.

The runtime rejects duplicate `record_id` values, historical `game_id` values,
and complete source identities formed from `source_type`, `source_name`, and
`source_record_id`. A duplicate is invalid within one partition and across
partitions. Cross-partition game or source duplication is reported as partition
leakage. This is separate from stable-player overlap. Optional `known_opponent`
policy permits player overlap; `unseen_player` requires every exact stable
`player_id` to occur in one partition only. Repetition within one partition is
valid. Existing datasets without policy metadata retain unspecified intent.
See [Dataset partition policies](dataset_partition_policies.md).

The same validated dataset can be reused as the multi-game source for
[historical opponent statistics](historical_opponent_statistics.md). In that
mode, partition selection remains canonical but does not imply player-disjoint
partitions. Every partition-selected historical game must have `played_at`, even
if no cutoff is supplied.

Public preparation materializes only a validated complete Plan. It preserves
Record order, Record and Game IDs, provenance, complete Historical Game Records,
zero-sample Records, feature version, and target, then adds only `partition` and
the existing version-1 policy. Materialization reuses this dataset validator and
the existing partition audit. It does not generate samples; later ordinary
conversion therefore retains the same `record_id:decision_index` identities.
Both generators balance Record Count, not Sample Count. A zero-sample Record
remains an indivisible assignment and full Player-membership unit; in unseen-
player mode it may connect an entire transitive Player component.

## Automatic preparation

Root `training_dataset_preparation_input` selects workflow identifier
`training_dataset_preparation`. Mode dispatch is fixed:

* `known_opponent` -> `temporal_known_opponent_v1`
* `unseen_player` -> `component_balanced_unseen_player_v1`

The public result is `training_dataset_preparation_summary` with exactly
`preparation_version`, `plan`, `training_dataset_input`, and `partition_audit`.
A complete result contains a losslessly reusable existing version-1 Training
Dataset and the matching audit. Reusing that nested object later in an ordinary
`training_dataset_input` wrapper preserves Records and established sample IDs.

An unavailable Plan is a successful result, not an input error. It has an
explicit reason, no assignments or partition summaries, and null
`training_dataset_input` and `partition_audit`; there is no partial Plan or
fallback. The request has no default weights or algorithm override, and the CLI
has no weight or algorithm override. Plan serialization and concise CLI output
are card-free. A complete wrapper contains source cards only because the nested
reusable dataset losslessly preserves each Historical Game Record.

Stable structures are defined by:

* [`schemas/training_dataset_preparation.schema.json`](../schemas/training_dataset_preparation.schema.json)
* [`schemas/dataset_partition_plan.schema.json`](../schemas/dataset_partition_plan.schema.json)
* [`schemas/training_dataset_preparation_output.schema.json`](../schemas/training_dataset_preparation_output.schema.json)

## Sample generation

Each accepted record is replayed once through the existing historical-game
implementation. The validated result is passed to the existing decision
snapshot generator, producing one sample per actual play in `decision_index` order.
No recommender, recommendation simulation, or historical review is run.

Dataset sample order is record input order followed by consecutive one-based
decision indices.
The stable sample ID is:

```text
record_id + ":" + decision_index
```

Repeated conversion of the same input produces the same structured JSON.

## Metadata, features, and labels

Each sample separates traceability, model-facing state, and target:

```json
{
  "sample_id": "record-001:1",
  "metadata": {},
  "features": {},
  "label": {
    "target": "actual_card_played",
    "card": "CJ"
  }
}
```

Metadata contains dataset and record identity, source game identity, partition,
decision/trick/play indices, acting player identity, seat and side, and preserved
provenance. Stable dataset, record, source, platform, game, and player identities
remain metadata and are not model-facing features.

Features contain only the state visible immediately before the play:

* contract and decision-time public declaration
* acting seat and side
* own remaining hand and legal cards
* current trick and completed tricks
* points from prior completed tricks
* left/right opponent hand sizes
* skat visibility and safely known skat cards
* decision-time visible matadors
* public exposed cards

All player references inside features use only `me`, `left`, and `right`.
Features contain no future plays, hidden opponent cards, final winner or points,
achieved future Schneider/Schwarz result, final game value, overbid outcome,
settlement, recommendation, or decision-quality value.
The terminal event, defender consent, unresolved points, and the fact that a
concession will occur are also absent from model-facing features.
The continuation event, claim, and responses are not targets or direct features;
only the rule-authorized post-event public hand is represented.
Declared-Ouvert cards are ordinary decision-time information, not an Ouvert or
exposure prediction target. Feature-generation version `1`, target
`actual_card_played`, and stable sample IDs remain unchanged.

Multi-Step's private coherent execution root is not a feature source. Root-world
ownership, hypothetical skat cards, ownership transitions, coherence summaries,
and actual future historical hands remain excluded from version-1 features and
labels. Dataset conversion does not run Multi-Step, so Issue #103 does not change
feature values, sample cardinality, or schema versions.

Issue #104 likewise does not run inference during feature generation and adds no
inference evidence, compatible-world count, ownership marginal, confidence,
privacy summary, statistic, or signal to features, metadata, or labels. Feature-
generation version `1`, target `actual_card_played`, stable
`record_id:decision_index` sample IDs, profile inputs, and sample cardinality are
unchanged. See [Hidden-card inference](hidden_card_inference.md).

The label card is the historical actual card. It must be in the pre-play own
hand and legal-card set and absent from the pre-play current trick. A
recommendation, review quality, or final result is never a version-1 target.

## Bounded Search evaluation

`--evaluate-bounded-search --search-seed INTEGER` is a separate evaluation-only
use of the validated dataset container. It does not run ordinary sample
conversion or change dataset schema version `1`, feature-generation version `1`,
the `actual_card_played` target, features, labels, or sample IDs.

Selection defaults to canonical `validation`, then `test`. The default immutable
work profile is `evaluation_v1`; the optional positive maximum-decision value
caps one stable global decision prefix rather than each record. Selected records
remain present even when they contain zero source decisions or the cap leaves an
empty evaluated prefix.

Each selected decision runs information-safe bounded Search and an independent
Immediate baseline before the observed card is introduced. Output uses the
separate strict `bounded_search_evaluation_summary` branch with status, coverage,
agreement, Search-not-worse quality-gate, aggregate, breakdown, and performance
metrics. It is bounded regression evidence, not calibrated sampled-world
probability or proof of an optimal imperfect-information policy. See
[Bounded search contracts](bounded_search_contracts.md) and
[`bounded_search_evaluation.schema.json`](../schemas/bounded_search_evaluation.schema.json).

## Output and counts

The dedicated output branch contains only `input_file` and
`training_dataset_summary`. The summary preserves dataset versions, target, and
supplied partition policy,
contains canonical historical records and all samples, and reports reconciled
record and sample totals. `partition_counts` always includes `train`,
`validation`, and `test`, including zero-count partitions. Record counts remain
independent of sample counts; each partition and dataset sample total is the sum
of actual record sample counts. Zero-sample records and all-zero-sample datasets
are valid.

The public example currently has two games in `train` and `validation`, repeated
stable players in changed seats, explicit timestamps, and opposite final
settlement outcomes. Normal conversion therefore emits `record_count: 2`, 30
samples per record, and `sample_count: 60`. The same file is the aggregation
source, but aggregation emits exact player records rather than these samples.

The three automatic preparation examples cover complete Known-opponent,
complete unseen-player, and unavailable Known-opponent results. Preparation does
not generate training samples; complete materialization creates the reusable
partitioned source object consumed by the existing conversion workflow.

`examples/training_dataset_variable_length.json` contains a 14-play concession
prefix ending in an incomplete trick. It produces 14 samples and no terminal-
event target.

`examples/training_dataset_shortened_opponent_workflows.json` combines an
earlier normal source, an earlier zero-play concession source, and a later
14-play concession target. Sample counts remain actual-play counts, while
statistics count each record once.

The stable structures are defined by:

* [`schemas/training_dataset.schema.json`](../schemas/training_dataset.schema.json)
* [`schemas/training_dataset_output.schema.json`](../schemas/training_dataset_output.schema.json)

## CLI

Convert the public example:

```powershell
python main.py --input examples/training_dataset_normal_play.json
```

Write only structured output:

```powershell
python main.py --input examples/training_dataset_normal_play.json --output outputs/training-dataset.json --quiet
```

Audit partition membership without generating samples:

```powershell
python main.py --input examples/training_dataset_partition_audit.json --audit-dataset-partitions --dataset-partition-mode known_opponent
```

Prepare complete datasets or inspect explicit unavailability:

```powershell
python main.py --input examples/training_dataset_preparation_known_opponent.json
python main.py --input examples/training_dataset_preparation_unseen_player.json
python main.py --input examples/training_dataset_preparation_unavailable.json
```

Preparation accepts only `--input`, `--output`, and `--quiet`. Every analysis,
review, simulation, sample, seed, policy, profile, evaluation, audit, algorithm,
and weight override is rejected rather than ignored.

Normal output prints dataset ID and version, total record and sample counts, and
all three partition counts. Historical snapshot/review flags and all position,
recommendation, simulation, comparison, policy, profile, sample-count, and seed
options are rejected instead of ignored.

With `--aggregate-opponent-statistics`, this input takes the separate
aggregation branch. Its only additional options are repeatable
`--opponent-statistics-partition`, strict `--opponent-statistics-before`, and
`--export-opponent-statistics`; `--output` and `--quiet` retain their normal
meanings. Samples, seeds, review, simulation, comparison, policy, profile, and
binding options are rejected. Without the aggregation flag, sample conversion is
unchanged.
Aggregation accepts exactly normal completion, declarer concession, defender
concession, declarer-card exposure, defender open play, and open card throw; zero-
sample shortened records remain full game-level evidence.

With `--evaluate-opponent-policy-profiles`, the dataset instead feeds the
separate known-opponent rolling behavioral evaluation. It accepts unspecified
or `known_opponent` intent and rejects `unseen_player`. Source partitions default to `train`;
evaluation partitions default to `validation` and `test`; the roles must be
disjoint. This mode emits no samples and leaves normal conversion unchanged.
Normal targets contribute 30 decisions and shortened targets contribute their
actual zero through 29 decisions without padding. Target participant coverage
always includes all three stable IDs.
See [Rolling opponent-policy evaluation](opponent_policy_evaluation.md).

## Internal field provenance

Issue #145 adds internal complete field-level provenance for Dataset input and
Records, decision-time Feature Views, retrospective Targets, summary conversion,
all partition-audit modes, rolling evaluation, bounded-Search evaluation,
historical Opponent Statistics aggregation, and the optional export artifact.
Zero-sample Records receive no artificial sample attachment. Public Dataset JSON,
Schemas, CLI output, and examples remain unchanged. See
[Dataset, list, and opponent provenance](dataset_list_and_opponent_provenance.md).
