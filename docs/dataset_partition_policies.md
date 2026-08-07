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
Datasets and audits accept normal-completion, including either optional timed
continuation kind, plus declarer-concession, defender-concession,
declarer-card-exposure, terminal defender-open-play, and open-card-throwing
records. The event does not change record identity or participant membership.
Membership remains record- and participant-based, so zero-sample records still
participate fully in overlap and coverage checks.

Issue #145 adds an internal complete audit Ledger derived only from Dataset
identity, Record/Game identity, partitions, stable Player IDs, declared policy,
and requested audit mode. Cards, outcomes, Settlement, Features, and Targets do
not drive audit provenance. It also constrains automatic split-assignment
provenance as documented in
[Dataset, list, and opponent provenance](dataset_list_and_opponent_provenance.md).

## Leakage and overlap

Record leakage and player overlap are different concepts. Duplicate record IDs,
historical game IDs, or complete source identities are invalid within or across
partitions under every policy. Player overlap means that the same exact stable
historical `player_id` occurs in more than one partition. It may be intentional
or invalid depending on the declared policy.

Player identity is exact, opaque, and case-sensitive. Labels and seats do not
define identity, so a seat change does not create another player and two IDs
with the same label remain distinct. Every game, including a zero-play
concession, contributes all three participant
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

The separate `temporal_known_opponent_v1` complete-Plan validator is
stricter. It requires Historical Game `played_at` on every Record, unsplit equal-
instant groups, non-empty strict Train/Validation/Test time blocks, and complete
Train membership coverage for every Validation and Test player. Its temporal
audit does not change or replace the membership-only public audit.

The generator parses and groups equal instants, evaluates every
contiguous chronological two-cut boundary, rejects candidates without complete
Train coverage, and selects the exact best weighted Record-count objective.
Deterministic seed-derived keys apply only after all Record-count metrics tie.
Zero-sample Records contribute membership normally. See
[Temporal Known-opponent dataset splits](temporal_known_opponent_dataset_splits.md).

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

The `component_balanced_unseen_player_v1` complete-Plan validator adds
the non-empty three-partition requirement and then reuses declared-policy loading
and this existing overlap audit. Whole zero-sample Records and transitive shared-
player groups participate fully. The generator constructs exact
transitive Player-connected Record components, requires at least three, creates
one deterministic non-empty greedy Record-count allocation, and applies strict
whole-component move/swap improvement. See
[Player-disjoint unseen-player dataset splits](player_disjoint_unseen_player_dataset_splits.md).

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
play, train a model, modify records, or repartition data. Public or general
automatic splitting, balancing, record movement, unseen-player profile
prediction, machine-learning training, and model generalization evaluation
remain unsupported. The separate public preparation workflow validates explicit
weights and complete or unavailable Plans and generates temporal Known-opponent
or component-balanced unseen-player assignments. General repartitioning,
additional algorithms, algorithm overrides, fallback or partial Plans, global
optimization, ratio guarantees, Sample- or Player-count balancing, component
splitting, model training, and automatic evaluation remain unsupported. See
[Automatic dataset preparation contracts](automatic_dataset_preparation_contracts.md).

Run the mode-derived preparation examples:

```powershell
python main.py --input examples/training_dataset_preparation_known_opponent.json
python main.py --input examples/training_dataset_preparation_unseen_player.json
python main.py --input examples/training_dataset_preparation_unavailable.json
```

Preparation is root-selected and accepts only `--input`, `--output`, and
`--quiet`; it does not change the separate audit CLI.

Historical opponent-statistics aggregation and rolling opponent-policy
evaluation support exactly normal completion, including either timed event,
declarer concession, defender concession, declarer-card exposure, defender open
play, and open-card throwing. Standalone
aggregation retains all policy modes; rolling remains incompatible with declared
`unseen_player`. Zero-sample source membership and all target participants remain
part of coverage.

Stable structures are defined by:

* [`schemas/dataset_partition_policy.schema.json`](../schemas/dataset_partition_policy.schema.json)
* [`schemas/dataset_partition_audit.schema.json`](../schemas/dataset_partition_audit.schema.json)
* [`schemas/training_dataset.schema.json`](../schemas/training_dataset.schema.json)
* [`schemas/training_dataset_preparation.schema.json`](../schemas/training_dataset_preparation.schema.json)
* [`schemas/dataset_partition_plan.schema.json`](../schemas/dataset_partition_plan.schema.json)
* [`schemas/training_dataset_preparation_output.schema.json`](../schemas/training_dataset_preparation_output.schema.json)
