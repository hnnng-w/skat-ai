# Player-disjoint unseen-player dataset splits

`component_balanced_unseen_player_v1` is the deterministic assignment
generator for a version-1 preparation request whose mode is `unseen_player`. Its
entry point is
`generate_component_balanced_unseen_player_dataset_partition_plan(request)`.
It returns the existing complete or unavailable Dataset Partition Plan. Issue
#134 exposes it only through public mode-derived workflow
`training_dataset_preparation`: root `training_dataset_preparation_input` selects
`unseen_player`, not an algorithm field or CLI override.

## Information boundary

The generator builds the existing split-safe source facts exactly once. Selection
uses only Record IDs, Historical Game IDs, exact stable Player IDs, explicit
partition weights, the base seed, a dedicated unseen-player selection
fingerprint, and deterministic tie keys. Player IDs are exact and case-sensitive.

Timestamps, provenance, Player labels, cards, hands, Skat, discards,
declarations, game types, actual-card sequences, outcomes, settlements, Feature
Views, labels, and Sample Counts cannot affect component membership or
assignment. Sample Count and zero-sample status remain component and plan
diagnostics. Existing generic source and plan fingerprints retain their broader
contracts and may change when assignment does not.

Source-fact construction replays each Historical Game and builds decision
snapshots once. Component ordering, greedy candidates, moves, and swaps do not
replay games, build snapshots, generate samples, materialize datasets, run
partition audits, or build candidate plans.

## Player-connected components

Records are graph nodes. Two Records are connected when their exact stable
Player-ID sets intersect. Union-find constructs the transitive closure, so a
shared-player chain is one indivisible component even when its first and last
Records do not directly share a Player.

Each component retains deterministic sorted Record IDs, Historical Game IDs,
Player IDs, and source facts, together with Record Count, diagnostic Sample
Count, and diagnostic Zero-sample Record Count. Every Record occurs in exactly
one component. A Player cannot occur in two different components, so distinct
components are Player-disjoint.

Connectivity ignores timestamps, labels, provenance, Sample Count, cards,
declarations, outcomes, and settlement. Zero-sample Records participate fully
and may connect otherwise separate Records.

## Identities

The canonical SHA-256 component identity covers only:

* `component_balanced_unseen_player_v1`
* sorted Record IDs
* sorted Historical Game IDs
* sorted stable Player IDs

The dedicated unseen-player selection fingerprint covers only preparation
version, dataset ID and version, the algorithm, sorted Record IDs, sorted
Historical Game IDs, and sorted stable Player IDs by Record. It excludes source
order, timestamps, provenance, labels, Sample Counts, card content, declaration,
outcome, and settlement. Only this fingerprint is supplied to unseen-player tie
keys; the final plan keeps the existing generic fingerprints unchanged.

## Component order

Components are ordered by:

1. Record Count descending
2. unseen-player component tie key ascending
3. canonical component identity ascending

The tie key uses mode `unseen_player`, the request seed, the dedicated selection
fingerprint, and component identity. The seed therefore affects only equal
Record-count ordering.

## Record-count objective

The generator shares the temporal selector's exact integer objective. For each
partition, signed deviation is actual Record Count multiplied by total weight
minus source Record Count multiplied by that partition's weight. Candidate
objectives are the ascending tuple:

```text
(
    total absolute deviation,
    maximum absolute deviation,
    absolute Train deviation,
    absolute Validation deviation,
    absolute Test deviation,
)
```

Record Count is the only balance basis. Sample Count, Player Count, timestamps,
game types, outcomes, and settlement are not objectives. Exact weights are
targets rather than a ratio-realization guarantee.

## Initial greedy placement

The generator processes each component once in deterministic order and evaluates
all three canonical target partitions. A placement is eligible only when the
number of remaining components is at least the number of partitions that would
remain empty. With at least three components, this invariant guarantees one
non-empty initial allocation.

Eligible placements are ranked by projected five-metric objective, deterministic
placement tie key, then canonical partition index. Placement identity includes
the algorithm, `initial_placement`, component identity, and target partition. A
better objective always outranks a seed-derived key. Components are never split.

## Strict local improvement

After greedy placement, the generator repeatedly evaluates every valid
single-component move and every two-component swap between partitions. A move
cannot empty its source partition. Only a strictly smaller five-metric objective
is eligible.

Strict improvements are ranked by resulting objective, deterministic operation
tie key, and canonical operation identity. Operation identity includes the
algorithm, `local_improvement`, operation kind, component identities, and source
and target partitions. Equal-objective operations are never accepted. Strict
descent over a finite allocation set terminates when no move or swap improves
the objective; this is local optimality for that neighborhood, not a global
optimality or guaranteed-ratio claim.

## Seed and source order

The same request and seed reproduce component identities and order, Record-to-
partition mapping, summaries, audits, and plan fingerprint. Different seeds may
change only exact non-seed ties; they cannot override a better Record-count
objective. The existing plan fingerprint still includes the seed and therefore
changes when the seed changes even if assignment does not.

Permuting source Records preserves component membership and order, assignment
mapping, summaries, audits, and plan fingerprint. Assignments and materialized
Records remain in each request's source order.

## Unavailable boundary

Fewer than three independent Player-connected components returns the existing
unavailable plan with reason `insufficient_player_components`. It contains no
assignments, summaries, temporal audit, or partition audit.

At least three valid components always proceed to one complete plan. This
generator does not emit `component_distribution_infeasible` or
`non_empty_partition_requirement_unsatisfied`; an internal failure after the
component-count precondition is an invariant error. Malformed requests remain
validation errors rather than unavailable plans.

## Plan, audit, and materialization

The final allocation assigns every component wholly to one partition and creates
one assignment per source Record in request order. The generator invokes the
existing source-fact-aware complete-plan builder exactly once. The resulting plan
has three non-empty partitions, `temporal_audit = null`, the existing compliant
`unseen_player` partition audit, exact Record-count summaries, and a valid
order-independent plan fingerprint.

Ordinary plan validation rebuilds the proof from the request. Materialization
preserves source order, complete Historical Game Records, provenance, IDs, and
zero-sample Records, adds only `partition` and the existing version-1
`unseen_player` policy, and reuses the existing Training Dataset validator and
partition audit. Later sample conversion retains established
`record_id:decision_index` identities.

## Complexity and limits

Union-find construction and greedy placement are linear apart from stable sorts.
Each strict local-search pass evaluates all single-component moves and all
cross-partition component swaps, then accepts one strict improvement. The finite
strict objective descent terminates without a timeout or fallback. The generator
does not perform exponential exhaustive production allocation and makes no hard
latency, global-optimality, or ratio guarantee.

Public complete results losslessly materialize the existing version-1 dataset and
audit; unavailable results succeed with null dataset/audit and no partial Plan.
The CLI accepts only `--input`, `--output`, and `--quiet`. Additional algorithms,
algorithm overrides, fallback, general repartitioning, global optimization,
ratio guarantees, Sample- or Player-count balancing, component splitting, model
training, and automatic evaluation remain open or separate work.
