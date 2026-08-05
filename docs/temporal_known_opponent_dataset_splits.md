# Temporal Known-opponent dataset splits

`temporal_known_opponent_v1` is the deterministic assignment generator
for a version-1 preparation request whose mode is `known_opponent`. Its entry
point is
`generate_temporal_known_opponent_dataset_partition_plan(request)`. It returns
one existing complete or unavailable Dataset Partition Plan. Issue #134 exposes
it only through public mode-derived workflow `training_dataset_preparation`: root
`training_dataset_preparation_input` selects `known_opponent`, not an algorithm
field or CLI override.

## Information boundary

The generator first builds the existing split-safe source-fact tuple. Selection
uses only Record IDs, Historical Game IDs, exact stable Player IDs, Historical
Game `played_at`, explicit partition weights, the base seed, the source identity
fingerprint, and deterministic candidate tie keys. Player IDs are exact and
case-sensitive.

Cards, hands, Skat, discards, declaration, result, settlement, actual-card
sequence, Player labels, provenance notes, Feature Views, labels, profiles, and
Sample Count cannot affect assignment. Sample Count remains diagnostic plan
metadata. Content and plan fingerprints still cover their existing source and
seed contracts and may therefore change when assignment does not.

Each source Historical Game and decision-snapshot path is executed once while
building facts. Candidate evaluation does not replay games, rebuild snapshots,
generate Feature Views or Training Samples, materialize a dataset, run a
partition audit, or build a plan.

## Time groups

Every `played_at` value is parsed with the existing RFC 3339 parser. Records are
grouped by parsed instant rather than source timestamp text, so equivalent
offsets form one indivisible group. Groups are sorted chronologically. Records
inside a group are ordered by stable Record ID and Historical Game ID; caller
source order does not define group identity.

Every Record occurs in exactly one group. A group is never split, sampled, or
interleaved across partitions.

## Candidate scan

For `G` groups, the generator evaluates every boundary pair:

```text
train_cut = 1 .. G - 2
validation_cut = train_cut + 1 .. G - 1
```

The corresponding contiguous blocks are:

```text
groups[0:train_cut] -> train
groups[train_cut:validation_cut] -> validation
groups[validation_cut:G] -> test
```

The boundary ranges make all three partitions non-empty. There is no Record-
level sampling, group splitting, Record removal, non-contiguous partition, or
fallback heuristic.

## Train coverage

A candidate is eligible only if every Validation and Test Player ID occurs in
Train:

```text
validation_players <= train_players
test_players <= train_players
```

The implementation precomputes cumulative Train player sets and future suffix
sets. Requiring the complete post-Train suffix set to be a subset of Train is
exactly equivalent to both directed checks for every Validation cut. Player
membership is Record-based, so a zero-sample Record contributes all three
players normally.

## Exact objective

For each eligible candidate, version 1 uses Record Count only. With positive
integer weights and `total_weight` equal to their sum, it computes:

```text
train_deviation =
    train_count * total_weight - source_count * train_weight
validation_deviation =
    validation_count * total_weight - source_count * validation_weight
test_deviation =
    test_count * total_weight - source_count * test_weight
```

Candidates are ranked by the ascending tuple:

```text
(
    abs(train_deviation)
        + abs(validation_deviation)
        + abs(test_deviation),
    max(
        abs(train_deviation),
        abs(validation_deviation),
        abs(test_deviation),
    ),
    abs(train_deviation),
    abs(validation_deviation),
    abs(test_deviation),
    deterministic_tie_break_key,
    train_boundary_utc,
    validation_boundary_utc,
)
```

All arithmetic is integer arithmetic. Sample Count and content-distribution
metrics do not participate. Because the three signed deviations sum to zero,
the maximum and final Test terms are algebraically redundant after their prior
terms, but they remain explicit parts of the exact version-1 objective.

## Tie and seed semantics

The generator first finds the best five Record-count metrics. It calls
`derive_dataset_partition_tie_break_key(...)` only when two or more candidates
tie exactly on all five. The helper receives mode `known_opponent`, the request
base seed, the source identity fingerprint, and a canonical stable identity
containing `temporal_known_opponent_v1`, canonical UTC Train end, and canonical
UTC Validation end. Canonical UTC boundaries resolve a theoretical equal-key
collision. Tie keys are never serialized.

The same request and seed produce the same mapping and plan. A seed change
changes the existing plan fingerprint. It can change assignment only among exact
five-metric ties and cannot change a uniquely optimal assignment. No random
shuffle, RNG object, module-global random state, or Python `hash()` is used.

## Unavailable results

Unavailable-reason precedence is fixed:

1. `missing_played_at` if any source fact lacks Historical Game `played_at`.
2. `insufficient_time_groups` if parsing produces fewer than three distinct
   instants.
3. `known_opponent_train_coverage_unsatisfied` if at least three groups exist but
   no boundary pair has complete Train coverage.

The selector does not emit
`non_empty_partition_requirement_unsatisfied`; three distinct groups already
provide the structural non-empty boundary. Malformed requests remain validation
errors rather than unavailable plans.

## Plan and materialization

After selecting one candidate, the generator creates one whole-Record assignment
for every source Record, normalizes assignments into request source order, and
builds exactly one existing complete plan. The final builder reuses the already-
derived facts, validates the assignments and strict temporal proof, materializes
the unchanged Training Dataset shape internally, and runs the existing membership
audit once.

Generated plan audits use canonical stable Record/Game order so the audit proof
is source-order independent. Assignment serialization and the final materialized
Training Dataset still preserve each request's Record order. Reordering source
Records therefore preserves the Record-ID mapping, selected boundaries,
summaries, temporal audit, partition audit, and plan fingerprint while changing
only request-ordered assignment and materialized Record presentation.

Ordinary materialization validates the complete plan, preserves complete source
Records including zero-sample Records, adds only the selected partition and the
existing version-1 `known_opponent` policy, and reuses the existing dataset
validator. Later sample generation retains established
`record_id:decision_index` identities.

## Complexity

Time-group construction and cumulative facts are linear apart from stable sorts.
The exact boundary scan is `O(G^2)` lightweight candidate scoring with cumulative
Record Counts and cumulative/suffix Player sets. There is no timeout, sampled
candidate subset, fallback, partial result, or elapsed-time guarantee.

Player-disjoint unseen-player component construction and assignment are the
separate `component_balanced_unseen_player_v1` generator. Complete public results
losslessly materialize the existing version-1 dataset and audit; unavailable
results succeed with null dataset/audit and no partial Plan. The CLI accepts only
`--input`, `--output`, and `--quiet`. No fallback, additional algorithm, global
optimization, ratio guarantee, Sample- or Player-count balancing, component
splitting, model training, or automatic evaluation is added. See
[Player-disjoint unseen-player dataset splits](player_disjoint_unseen_player_dataset_splits.md).
