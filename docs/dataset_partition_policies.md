# Dataset partition policies

Version-1 `training_dataset_input` supports optional explicit partition intent:

```json
{
  "partition_policy": {
    "policy_version": 1,
    "mode": "known_opponent"
  }
}
```

Supported stored modes are `known_opponent` and `unseen_player`. The object is
optional, so existing datasets remain valid with unspecified partition intent.
`report_only` is an audit CLI mode and cannot be stored in dataset metadata.
Policy metadata is preserved by canonical dataset conversion and in bounded
historical-aggregation and rolling-evaluation source provenance.

## Leakage and overlap

Record leakage and player overlap are different concepts. Duplicate record IDs,
historical game IDs, or complete source identities are invalid within or across
partitions under every policy. Player overlap means that the same exact stable
historical `player_id` occurs in more than one partition. It may be intentional
or invalid depending on the declared policy.

Player identity is exact, opaque, and case-sensitive. Labels and seats do not
define identity, so a seat change does not create another player and two IDs
with the same label remain distinct. Every game contributes all three participant
IDs. Repeated games for one player inside a single partition are valid and are
not cross-partition leakage.

## Known opponents

`known_opponent` permits overlap. It supports workflows where earlier source
games describe the same stable players in later evaluation games. A valid
dataset may still have zero overlap; that means zero partition-membership
coverage, not unseen-player intent.

The audit reports directed membership coverage for `train -> validation`,
`train -> test`, and `validation -> test`. These summaries do not prove that a
source game occurred before a target game. The rolling opponent-policy evaluator
remains authoritative for strict `source.played_at < target.played_at`
eligibility and rejects datasets declaring `unseen_player`.

## Unseen players

`unseen_player` requires every stable player to occur in exactly one of `train`,
`validation`, or `test`. Repeated appearances within that one partition remain
valid. Normal dataset loading rejects a declared unseen-player dataset with any
pairwise or three-way overlap and reports every conflicting player and canonical
partition list in deterministic first-appearance order.

An undeclared dataset may be audited with requested `unseen_player` semantics.
That audit returns a complete `non_compliant` report instead of converting the
request into invalid stored metadata. This distinction keeps violations
inspectable without weakening declared-policy validation.

## Audit workflow

Run the default audit:

```powershell
python main.py --input examples/training_dataset_partition_audit.json --audit-dataset-partitions
```

Request explicit semantics:

```powershell
python main.py --input examples/training_dataset_partition_audit.json --audit-dataset-partitions --dataset-partition-mode known_opponent
```

Mode resolution uses the supplied CLI mode, otherwise the declared policy,
otherwise `report_only`. A supplied known-opponent or unseen-player mode that
contradicts stored metadata is rejected. `report_only` never claims policy
compliance.

The audit reports complete ordered player membership, record and game IDs by
partition, game counts, first appearance, partition totals, exact
train/validation, train/test, validation/test, and three-way overlap, bounded
directed known-opponent coverage, and unseen-player compliance. Pairwise groups
include three-way players. Output order follows canonical record appearance and
canonical `train`, `validation`, `test` partition order.

Audit mode does not replay games to generate samples, aggregate statistics, run
rolling evaluation, review historical decisions, recommend cards, simulate
play, train a model, modify records, or repartition data. Automatic splitting,
balancing, record movement, unseen-player profile prediction, machine-learning
training, and model generalization evaluation remain unsupported.

Stable structures are defined by:

* [`schemas/dataset_partition_policy.schema.json`](../schemas/dataset_partition_policy.schema.json)
* [`schemas/dataset_partition_audit.schema.json`](../schemas/dataset_partition_audit.schema.json)
* [`schemas/training_dataset.schema.json`](../schemas/training_dataset.schema.json)
