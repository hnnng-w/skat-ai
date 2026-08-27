# Dataset, list, and opponent provenance

Issue #145 extends the internal field-level information-provenance system through
Training Dataset, automatic Dataset Preparation, Opponent Statistics, and
fixed-three-player historical-list workflows. It uses the unchanged shared
version-1 language and Application sidecar contracts defined in
[Field-level information provenance](field_level_information_provenance.md).

Issue #145 propagation remains internal. Issue #147 now selects each workflow's
exact complete Root Result attachment for bounded opt-in public output and, when
actually returned, the Training Dataset Opponent Statistics export attachment.
All consumed-input, Record, Feature, Target, prediction, Search, Plan, Profile,
Entry, progression, and comparison-stage attachments remain internal.

## Contract identity

The focused propagation versions are:

```text
TRAINING_DATASET_PROVENANCE_VERSION = 1
DATASET_PREPARATION_PROVENANCE_VERSION = 1
OPPONENT_WORKFLOW_PROVENANCE_VERSION = 1
HISTORICAL_LIST_PROVENANCE_VERSION = 1
```

They are internal and are not exported from `skat_ai`, `skat_ai.api`,
`skat_ai.api.v1`, or `skat_ai.errors`. They do not change any existing Domain,
Application, public API, Package, or Schema version.

The focused implementation modules are:

* `training_dataset_provenance.py`;
* `dataset_preparation_provenance.py`;
* `opponent_workflow_provenance.py`;
* `historical_list_provenance.py`.

## Application bundles

The following Root workflows now always return a non-null internal bundle:

```text
training_dataset
training_dataset_preparation
opponent_statistics
fixed_three_player_historical_list
fixed_three_player_historical_list_comparison
```

Every attachment in these bundles uses `status = complete`, has no exemption or
legacy limitation, and accounts for every current document leaf exactly once.
The final Root attachments are:

```text
training_dataset_result
dataset_preparation_result
opponent_statistics_result
historical_list_result
historical_list_comparison_result
```

They attach the exact existing Root Result and are last in their workflow. The
Position and base Historical Game Result statuses were completed subsequently by
Issue #146. See [Complete Result provenance](complete_result_provenance.md).

## Attachment order

Issue #143 and #144 ordering remains unchanged. The new families are appended in
this order, with numeric components sorted numerically:

```text
training_dataset/input
training_dataset/record/<record-index>
training_dataset/sample/<record-index>/<decision-index>/feature
training_dataset/sample/<record-index>/<decision-index>/target
training_dataset/rolling/<target-index>/<decision-index>/prediction
training_dataset/rolling/<target-index>/<decision-index>/actual
training_dataset/search/<record-index>/<decision-index>/input
training_dataset/search/<record-index>/<decision-index>/immediate
training_dataset/search/<record-index>/<decision-index>/search
training_dataset/search/<record-index>/<decision-index>/comparison
training_dataset/search/<record-index>/<decision-index>/actual
training_dataset/search/<record-index>/<decision-index>/retrospective
training_dataset/<selected-operation>
training_dataset/opponent_statistics_input
training_dataset_result

dataset_preparation/input
dataset_preparation/source/<source-index>
dataset_preparation/plan
dataset_preparation/materialized_dataset
dataset_preparation_result

opponent_statistics/input
opponent_statistics/record/<record-index>
opponent_statistics/profile/<record-index>
opponent_statistics/summary
opponent_statistics_result

historical_list/input
historical_list/entry/<entry-number>
historical_list/aggregation
historical_list_result

historical_list_comparison/input
historical_list_comparison/source/<source-index>
historical_list_comparison/pair/<pair-index>
historical_list_comparison_result
```

The optional `training_dataset/opponent_statistics_input` attachment describes
the already returned auxiliary artifact. Issue #147 maps public artifact name
`opponent_statistics_input` to this attachment with scope `artifact_document`.
The artifact remains separate from the Root Result, and the exported document
itself has no nested `field_provenance` field.

## Training Dataset

Every execution attaches the canonical validated Dataset input and one canonical
source Record attachment per input position. Record names use stable zero-based
input indexes rather than caller IDs. Source references carry opaque Record or
Game identity only; they do not embed source values.

Summary generation additionally attaches every generated Feature View and Target.
A zero-sample Record retains its input and Record attachments and creates no
artificial sample attachment.

### Feature and Target boundary

A Feature attachment contains exactly the generated decision-time Feature View.
It uses the acting Player perspective and `decision_time`. Own hand and visible
Skat fields are `local_private`; legal cards are deterministic rule derivations;
visible replay fields are Historical reconstruction. It contains no target,
actual card, later card, final hidden hand, final private Skat, final Result, or
Settlement.

A Target attachment contains exactly the generated label and uses
`after_actual_play`. Target references identify only the retrospective
observation for that Game and decision. Summary Feature leaves reference their
matching Feature attachment identity, while label leaves reference their matching
Target identity. Consequently, changing a Target for an equal pre-play state does
not change Feature attachment documents or ledgers.

Dataset identity, partition, Record, sample, and total counts are deterministic
aggregates. Provenance consumes the existing generated summary; it does not rerun
Historical Snapshot or Feature generation.

## Partition Audit

The selected `training_dataset/partition_audit` attachment is one complete
offline Ledger over the existing audit result. Its derivation is bounded to:

* Dataset identity;
* Record and Historical Game IDs;
* Record partitions;
* stable Player IDs;
* the declared partition policy;
* the requested or resolved audit mode.

It covers every membership, overlap, coverage, compliance, and count field for
`report_only`, `known_opponent`, and `unseen_player`. Its source references do not
identify cards, contracts, outcomes, Settlement, Features, Targets, or notes. The
audit is consumed once and is not rerun for provenance.

## Rolling Opponent Policy Evaluation

Each evaluated decision has two stage attachments:

* `prediction` contains visible decision identity, legal cards, Profile status,
  existing Confidence values, policy selection, predicted card, and preferred
  cards at `decision_time`;
* `actual` contains actual-card observations, match booleans, and comparison
  outcomes at `after_actual_play`.

Profile-based prediction references are restricted to the exact source Record IDs
already retained in the target's as-of Profile. Those Records are strictly earlier
than the target Game. Baseline prediction uses only the baseline-policy algorithm
reference. No target can depend on a future evaluation Record, in-game Profile
update, or final Settlement. Confidence remains the existing separate Profile
contract and is not added to the field-provenance contract.

The complete evaluation attachment covers selection, temporal coverage, Profiles,
predictions, retrospective agreement, rates, breakdowns, and aggregate metrics.
The existing Profiles and predictions are consumed without rerunning them.

## Bounded Search Dataset Evaluation

Each selected decision attaches:

* the decision-time input;
* the retained Immediate baseline, excluding the derived effective random seed;
* the retained bounded-Search aggregate;
* Search-versus-Immediate comparison;
* the actual card;
* retrospective Search-to-actual comparison.

The Search aggregate uses the existing Historical Search provenance mapping:
requested budgets are validated copies, exact compatible-world counts are exact
aggregates, candidate metrics distinguish exact and sampled compatible-world
coverage, and ranking/recommendation fields retain deterministic dependencies.
Complete, partial, timeout, unavailable, exact, sampled, and zero-completion
Search results are supported.

No attachment adds a concrete Search World, ownership assignment, exact private
Search state, cache, branch, principal variation, hidden-card sentinel, tie key,
or derived seed. Search and Immediate are each consumed from the existing
evaluation decision and are not rerun.

## Historical Opponent Statistics

The aggregation attachment covers Dataset identity, included partitions, optional
cutoff, excluded counts, source Record and Game IDs, first and last times, exact
per-Player counts, percentages, normalized rates, Profile derivation, and final
summary counts. Percentage fields depend on their exact numerator and denominator;
normalized Profile fields depend on the corresponding exact counts.

Source references identify selected Records and aggregates without embedding card
identity. When export is requested, the canonical `opponent_statistics_input`
artifact receives its own complete internal attachment and remains outside the
Root Result.

## Dataset Preparation

Preparation attaches the validated request, one split-safe source-fact document
per source index, the complete or unavailable Plan, an optional materialized
Dataset, and the exact Root Result. Source facts contain only source index, Record
and Game identity, optional complete source identity, Historical timestamp, stable
Player IDs, diagnostic Sample Count, and zero-sample status.

### Known-opponent assignment

Assignment provenance may use only Record IDs, Game IDs, Player IDs, Historical
timestamps, explicit weights, the caller base seed, source-identity fingerprint,
and fixed algorithm identity. It does not use cards, outcomes, Settlement, Sample
Count, labels, or notes. Equal timestamps and temporal coverage remain properties
of the existing Plan algorithm.

### Unseen-player assignment

Assignment provenance may use only Record IDs, Game IDs, Player IDs, explicit
weights, the caller base seed, selector identity, and fixed algorithm identity.
It does not use timestamps, source provenance, Sample Count, cards, outcomes,
Settlement, labels, or notes.

Tie keys, derived seeds, component identity, and move or swap history remain
engine-private and are absent from attachments and references.

### Materialization

For each materialized Record, only `/records/<index>/partition` has
`dataset_assignment` provenance. Every other Record field is a validated copy of
the matching source Record. Record order, IDs, existing Training Provenance,
Historical Games, and zero-sample Records remain unchanged. An unavailable Plan
has no materialized-Dataset attachment.

## Opponent Statistics and Profiles

Opponent execution attaches the canonical validated input, every source Record,
every normalized Profile plus derivation, the complete summary, and the exact Root
Result. External records use `external_record` references; historically aggregated
records use `aggregate` references.

Exact counts and supplied percentages retain source provenance. Normalized rates
are deterministic rule derivations. Signals, Classification, recommended and
actionable Policy Presets, derivation status, decisive codes, and explanations are
heuristic derivations from the normalized Profile. Existing Confidence values are
covered as output fields but remain a separate Profile-confidence contract. Source
notes are metadata and are not referenced by Profile derivation, Classification,
or Preset provenance. No learned or causal claim is added.

## Historical lists

A single-list bundle contains the validated list request, all 36 retained Entry
Facts, the complete aggregation, and the exact Root Result.

Played Entry references identify only source list, Entry, and Game identity.
Rotation, seats, roles, contribution counts, bonuses, and performance points are
deterministic rule derivations; outcome and settlement score are validated
Historical aggregates. No source reference copies hands, cards, Skat, discards,
tricks, or a Settlement object.

A Passed Deal has no Historical Game reference. Its nullable Game, declarer, end-
reason, and settlement fields are positively provenanced; rotation advances; all
played, role, Result, and point contributions remain zero.

Progression cumulative fields depend on the current Entry contribution and, after
the first Entry, the matching previous cumulative field. Provisional standings
depend only on the current cumulative ranking metrics. The list-specific validator
rejects any dependency from progression snapshot `n` to a later snapshot. Final
standings use the existing SkWO order. A caller-supplied lot affects only final
tied order, ranks, and lot state; it never affects progression or Player metrics,
and no random lot exists.

## Independent-list comparison

Comparison preserves source order and attaches every compact source summary plus
every comparison between source zero and one later source. Stable Player IDs,
not tuple positions or table places, align Player rows. Every list-count and
Player-total delta remains comparison minus reference. Rank movement remains
reference rank minus comparison rank, and rank fields remain null under the
existing unresolved-lot statuses.

Comparison provenance adds no progression-position comparison, series totals,
averages, winners, ratings, or recommendations.

## Determinism and execution counts

Attachment identity uses stable Record, source, target, pair, and decision indexes.
Bundles are canonically sorted, and repeated execution over equal inputs produces
equal documents and ledgers. Collectors consume values already retained by the
selected workflow. They do not add Dataset parsing, Snapshot, Feature, audit,
evaluation, Search, Immediate, aggregation, Preparation, Profile, list, or
comparison executions.

## Retained boundary

Issue #147 implements the bounded public API, strict Schema, Root Result field,
CLI presentation, and actual-artifact mapping. Public exposure of the detailed
internal stages documented above remains intentionally absent. Issue #202
enforces the relevant exact Root source, retained-stage, and final-serialization
boundaries internally. Existing Profile Confidence is
covered only as an ordinary Result field and is not integrated into the
field-provenance language.
