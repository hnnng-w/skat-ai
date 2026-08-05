# Automatic dataset preparation contracts

Issue #131 defines the internal version-1 contracts used before a partitioned
Training Dataset exists. Issues #132 and #133 add deterministic assignment
generation for `temporal_known_opponent_v1` and
`component_balanced_unseen_player_v1`; caller-supplied complete plans remain
supported.
The contracts add no public workflow, generate no samples, and train no model.

## Versions and fixed values

The internal preparation version and partition-plan version are both `1`.
`record_count` is the only version-1 balance basis. The existing Training Dataset
schema, feature-generation, target, partition-policy, and partition-audit
versions remain unchanged.

The reserved supplied-plan algorithms are:

* `temporal_known_opponent_v1` for `known_opponent`
* `component_balanced_unseen_player_v1` for `unseen_player`

The reserved SHA-256 seed domains are
`dataset_known_opponent_split_v1` and `dataset_unseen_player_split_v1`.

`generate_temporal_known_opponent_dataset_partition_plan(request)` implements
the first reserved algorithm.
`generate_component_balanced_unseen_player_dataset_partition_plan(request)`
implements the second. Each requires its matching mode, accepts no extra
settings, RNG, or assignments, and returns the existing complete or unavailable
plan union.

## Preparation request

One request contains the preparation version, dataset ID and version, feature-
generation version, `actual_card_played` target, partition mode, non-boolean
integer base seed, explicit partition weights, and a non-empty ordered tuple of
unpartitioned Records.

Each source Record contains only:

```text
record_id
provenance
historical_game
```

There is no `partition`. Existing provenance and Historical Game models,
validation, and serialization are reused. Record IDs, Historical Game IDs, and
complete non-null provenance source identities must each be unique. Source
Record order is preserved through request serialization and materialization.

Partition weights require exactly `train`, `validation`, and `test`. Every value
must be a positive integer and must not be a boolean. Supplied values are
preserved exactly; there are no defaults, percentages, normalization, or implied
ratios.

## Split-safe source facts

Each Record is replayed once through the existing Historical Game and decision-
snapshot path to derive:

```text
source_index
record_id
historical_game_id
source_identity
played_at
player_ids
sample_count
zero_sample
```

Stable Player IDs are exact, case-sensitive, and sorted canonically in each fact.
Snapshot count supplies the diagnostic sample count. No Feature View or training
sample is generated. Zero-sample Records remain full assignment, membership, and
audit units.

Facts contain no cards, hands, Skat, discards, declarations, outcomes,
settlement, targets, labels, notes, profiles, or Feature Views. Future assignment
logic may use only Record and Game IDs, stable Player IDs, Historical Game
`played_at`, exact weights, and deterministic seed data. Sample Count is
diagnostic and must not influence assignment or balancing.

## Fingerprints and deterministic values

Both source fingerprints are order-independent lowercase SHA-256 hexadecimal
values built from canonical JSON, never Python `hash()`:

* `source_identity_fingerprint` covers preparation/dataset identity and mode plus
  only stable Record, Game, Player, provenance-source, and Historical Game time
  fields. It excludes source order, player labels, provenance notes, cards,
  declarations, outcomes, settlement, and target labels.
* `source_content_fingerprint` covers the exact canonical request identity,
  provenance, and Historical Game source content. It proves that a plan belongs
  to the exact source request while remaining order-independent.
* The dedicated unseen-player selection fingerprint covers only preparation
  version, dataset ID/version, algorithm, and sorted Record, Game, and stable
  Player identities. It excludes timestamps, provenance, labels, Sample Counts,
  and game content and is used only for unseen-player tie keys.

The mode-specific partition-seed and stable-item tie-key helpers use the reserved
domain, base seed, source identity fingerprint, and a fixed purpose marker. The
tie key additionally uses one non-empty, non-padded stable item identity. Both
return the unsigned big-endian integer represented by the first eight SHA-256
digest bytes. They do not use source order, labels, card content, outcomes,
module-global random state, or Python `hash()`. Derived seeds and tie keys are not
serialized.

## Complete plans

A complete plan assigns every whole Record exactly once to one canonical
partition. Assignments are normalized to source-request order. Partial,
duplicate, unknown, sample-level, or omitted assignments are invalid.

Exactly three summaries, in canonical partition order, report requested weight,
Record Count, diagnostic Sample Count, distinct stable players, Player IDs, and
exact target arithmetic:

```text
target_record_count_numerator = source_record_count * partition_weight
target_record_count_denominator = total_partition_weight
record_count_deviation_numerator =
    actual_record_count * total_partition_weight
    - target_record_count_numerator
```

Record Count is the balance basis; exact weighted targets are objectives rather
than a claim that every source can realize the ratio.

### Known opponent

A complete `temporal_known_opponent_v1` plan requires `played_at` on every
Historical Game, three non-empty partitions, strict chronological Train,
Validation, and Test blocks, and unsplit parsed RFC 3339 time groups. Equivalent
instants with different offsets belong to one group. Validation requires:

```text
max(train) < min(validation)
max(validation) < min(test)
```

Every Validation and Test Player ID must occur in Train. The immutable temporal
audit records canonical UTC partition boundaries, time-group counts, Train and
target memberships, covered IDs, uncovered IDs, and coverage booleans. Historical
Game time is authoritative; provenance collection time is not used.

This proof is stricter than the existing Known-opponent partition audit. That
audit intentionally remains membership-only and behaviorally unchanged.

### Unseen player

A complete `component_balanced_unseen_player_v1` plan requires three non-empty
partitions and exactly one partition for every stable Player ID. Shared-player
Records, including transitive groups and zero-sample Records, therefore remain in
one partition. Timestamps are optional. Materialization declares the existing
`unseen_player` policy and must pass the existing dataset validator and partition
audit.

## Unavailable plans

Plan status is exactly `complete` or `unavailable`. An unavailable plan has no
assignments, summaries, temporal audit, or partition audit. Supported reasons
are:

* Known opponent: `missing_played_at`, `insufficient_time_groups`,
  `known_opponent_train_coverage_unsatisfied`, and
  `non_empty_partition_requirement_unsatisfied`
* Unseen player: `insufficient_player_components`,
  `component_distribution_infeasible`, and
  `non_empty_partition_requirement_unsatisfied`

Malformed requests and malformed supplied plans are validation errors, not
unavailable results. There is no partial or best-effort plan status.

## Plan proof and materialization

The order-independent plan fingerprint covers plan version, algorithm, mode,
status, unavailable reason, source content fingerprint, base seed, exact weights,
and canonical assignments. Changing source content, assignment, seed, weight,
status, or reason changes the fingerprint.

Complete-plan validation rebuilds and reconciles source counts, snapshot counts,
source fingerprints, assignments, exact arithmetic, chronology, coverage,
disjointness, both applicable audits, all status fields, and the plan
fingerprint. The builder validates assignments supplied by its caller; it does
not generate them.

The temporal generator instead builds facts once, scans every chronological
two-cut group boundary with complete Train player coverage, selects the exact
best Record-count objective, and invokes the complete builder once with the
winning assignments and reused facts. Its generated partition audit uses stable
canonical Record/Game order while assignments and materialized Records retain
request order. See
[Temporal Known-opponent dataset splits](temporal_known_opponent_dataset_splits.md).

The unseen-player generator builds exact transitive shared-Player components,
orders them by descending Record Count and dedicated tie keys, creates one
non-empty greedy allocation, and repeatedly accepts the best strict whole-
component move or swap until locally optimal. It invokes the final builder once
with reused facts and canonical audit ordering. See
[Player-disjoint unseen-player dataset
splits](player_disjoint_unseen_player_dataset_splits.md).

Materialization accepts only a validated complete plan. It preserves source
order, Record IDs, Game IDs, provenance, complete Historical Game Records,
zero-sample Records, dataset and feature versions, and target, and adds only the
partition. It attaches partition-policy version `1` with the request mode, uses
the existing `TrainingDatasetInput` validator, and reuses the existing version-1
partition audit. It does not generate Feature Views or samples, so later ordinary
conversion retains the established `record_id:decision_index` sample identities.

Plan serialization includes fingerprints, assignments, summaries, temporal
proof, and the existing partition audit. It contains no Historical Game card
data and no derived seed or tie key. No public schema, input root, output branch,
CLI option, example, or generated-output scenario is registered.

## Remaining work

All public preparation workflows remain unimplemented. Version 1 does not
provide global assignment optimization, guaranteed ratios, Sample-count or
Player-count balancing, component splitting, or model training.
