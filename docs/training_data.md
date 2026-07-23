# Training data

`skat-ai` supports a separate versioned workflow that converts complete
normal-play historical games into deterministic training or evaluation records.
It stores provenance and explicit partitions and derives one information-safe
sample for every historical card play. It does not train, select, evaluate, or
deploy a machine-learning model.

Training-data representation remains `partially_supported`. Version 1 accepts
only complete historical games with `game_end_reason: "normal_completion"`.
Claims, concessions, passed-in games, and other later historical end reasons
require separate support.

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
    "records": []
  }
}
```

`schema_version` and `feature_generation_version` currently accept only `1`.
The only version-1 target is `actual_card_played`. Dataset IDs and versions are
opaque, case-sensitive, non-empty, and may not have leading or trailing
whitespace. They are not package versions.

The workflow is mutually exclusive with position analysis,
`historical_game_input`, list-performance inputs, impossible-Null settlement,
profiles, and opponent-policy settings.

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
leakage. Player-disjoint partitioning is not yet defined or enforced.

## Sample generation

Each accepted record is replayed once through the existing historical-game
implementation. The validated result is passed to the existing decision
snapshot generator, producing exactly 30 samples in `decision_index` order.
No recommender, recommendation simulation, or historical review is run.

Dataset sample order is record input order followed by decision indices `1..30`.
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

The label card is the historical actual card. It must be in the pre-play own
hand and legal-card set and absent from the pre-play current trick. A
recommendation, review quality, or final result is never a version-1 target.

## Output and counts

The dedicated output branch contains only `input_file` and
`training_dataset_summary`. The summary preserves dataset versions and target,
contains canonical historical records and all samples, and reports reconciled
record and sample totals. `partition_counts` always includes `train`,
`validation`, and `test`, including zero-count partitions. Every record has 30
samples, so total `sample_count` is `record_count * 30`.

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

Normal output prints dataset ID and version, total record and sample counts, and
all three partition counts. Historical snapshot/review flags and all position,
recommendation, simulation, comparison, policy, profile, sample-count, and seed
options are rejected instead of ignored.
