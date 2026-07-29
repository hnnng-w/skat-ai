# Rolling opponent-policy evaluation

This workflow accepts exactly normal-completion, including either timed
continuation kind, declarer-concession, defender-concession, declarer-card-exposure,
terminal defender-open-play, and open-card-throw
historical dataset records. Normal targets contribute 30 decisions; concession
and other shortened targets contribute their validated zero through 29 actual
card plays. Open-card-throw targets include no throw or statement decision.

`skat-ai` can evaluate whether an existing profile-derived deterministic policy
describes observed historical card choices better than the fixed
`simple_lowest` baseline. This is a known-opponent behavioral imitation
evaluation. It does not measure optimal play, expected value, recommendation
quality, game outcomes, strategic strength, or machine-learning performance.

A continuation source contributes one ordinary game-level result. A continuation
target contributes 30 actual decisions: pre-event snapshots do not contain the
event, and post-event snapshots carry the exact shrinking public hand. No event,
claim, or response prediction is created, and the target result remains absent
from its own as-of profile.
Declared-Ouvert targets carry the exact shrinking declarer hand from decision 1
in the same snapshots supplied to baseline and profile prediction. Existing
policies may remain behaviorally identical because they do not add an Ouvert-
specific tactic.

## CLI

Run the focused example with the default `train` source partition and default
`validation`, `test` evaluation partitions:

```powershell
python main.py --input examples/historical_opponent_policy_evaluation_dataset.json --evaluate-opponent-policy-profiles --output outputs/opponent-policy-evaluation.json
```

The mixed shortened example uses the equivalent public alias:

```powershell
python main.py --input examples/training_dataset_shortened_opponent_workflows.json --evaluate-rolling-opponent-policies
```

Source and evaluation options are repeatable:

```powershell
python main.py --input examples/historical_opponent_policy_evaluation_dataset.json --evaluate-opponent-policy-profiles --profile-source-partition train --profile-evaluation-partition validation --quiet
```

Duplicate partition arguments are de-duplicated and output always uses
`train`, `validation`, `test` order. Source and evaluation partitions must be
disjoint. Every selected source partition must be populated, and the selected
evaluation partitions must contain at least one target. Repeated stable player
IDs across the two roles are expected; this is not player-disjoint or unseen-
player evaluation.

The evaluator accepts datasets with unspecified intent or declared
`known_opponent` policy and rejects declared `unseen_player` policy as
semantically incompatible.

The mode rejects training-sample overrides, historical review and aggregation,
statistics export or binding, explicit policies or presets, recommendation,
Multi-Step, comparison, list, and unrelated workflow options. It emits no
training samples and does not apply a profile to a live or historical
recommendation path.

## Rolling as-of profiles

For each target game, the evaluator compares normalized offset-aware RFC 3339
instants and includes a selected source game only when:

```text
source.played_at < target.played_at
```

Equal instants, including equivalent instants written with different offsets,
and later games are excluded. The evaluator reuses exact historical opponent-
statistics aggregation, exact profile conversion, and the existing explainable
derivation. The latest eligible source timestamp becomes `captured_at` and is
strictly earlier than target `played_at`.

Every eligible normal or concession source contributes one statistics game,
including a zero-play concession. Source play count does not weight profiles.

One immutable game-start profile state is built for each target participant by
exact, opaque, case-sensitive `player_id`. Labels and seats do not identify a
player, so stable identities survive seat changes. The target game never enters
its own profile, no target decision updates the profile, and evaluation games do
not become source history for later targets.

Targets before all selected sources remain visible as
`no_prior_source_games`. A participant absent from an otherwise available
aggregation is `no_player_history`. The invocation must contain at least one
target participant with prior source history, but no actionable profile is
required.

## Decision information

Every actual target decision is reconstructed from the existing decision-time
historical snapshots. A prediction may use the acting player's identity and
side, visible declaration and game type, own hand, current trick, legal cards,
public completed tricks, stable relative identities, and the game-start as-of
profile. It cannot use future plays or winners, another player's hidden hand,
final result or settlement, later games, or source games at or after target
start. The actual card is read only after prediction as the comparison label.
Declared-Ouvert public cards are allowed decision-time information; no hidden
defender hand or skat is added.
The terminal concession, consent, unresolved cards, and knowledge that play will
end are absent. No card decision is padded and no terminal event is predicted.

The evaluator does not run Multi-Step and does not receive its private coherent
execution root or coherence summaries. Actual future target hands remain
excluded. Feature version `1`, preferred-card candidates, profile derivation,
strict as-of selection, and every rolling metric are unchanged by Issue #103.

The acting player's own profile is evaluated. It is not attached to historical
`left` or `right` recommendation slots. Defender partner-winning context is
derived only from the visible current trick and stable declarer identity; a
declarer has no defender partner.

## Policies and candidates

Version 1 fixes the baseline to the existing `simple_lowest` preset:

* lead policy: `lowest_point`
* response policy: `lowest_point`

Target input cannot override it. Profile predictions use only the existing
`actionable_policy_preset`. The supported actionable presets remain
`aggressive_points` and `cautious_defender`, with their existing phase-specific
lead and response selectors. Low-confidence, neutral, insufficient-data, and
missing-history profiles retain their complete derivation but produce no
profile prediction. `simple_lowest` remains non-actionable.

`get_preferred_opponent_cards_by_policy()` exposes every legal card equally
preferred before incidental stable list-order tie-breaking for the supported
deterministic selectors. Candidate order preserves legal-hand order, and the
existing chooser's deterministic selected card must be present. Existing
policy-specific partner-safety, trump-conservation, and trick-strength
preferences remain part of the candidate criteria. Existing chooser results
are unchanged. `random_legal` is not evaluated.

## Metrics

Every prediction contains its preset, concrete phase policy, deterministic
card, ordered preferred cards, actual card, exact-card match, and preferred-card
match. Preferred-card matching is the primary metric:

```text
preferred_card_match = actual_card in preferred_cards
```

Exact-card matching is the stricter secondary metric and remains sensitive to
deterministic tie-breaking. Actionable decisions receive preferred and exact
paired outcomes: `both_match`, `profile_only`, `baseline_only`, or
`neither_match`. Other decisions use `not_available` while retaining the
baseline result and profile unavailability reason.

The baseline covers every target decision. Profile and paired-baseline rates
use only decisions with actionable profile predictions; they never divide by
all target decisions. Deltas are profile rate minus paired-baseline rate in
percentage points. Zero-actionable evaluations remain valid with zero counts
and null rates and deltas. No confidence intervals or significance claims are
calculated.

Metrics remain decision-weighted. A zero-decision target is retained with empty
decision rows, zero counts, and null denominator-zero rates; an all-zero target
set is valid when prior participant history exists.

## Output and reconciliation

The dedicated `rolling_opponent_policy_evaluation_summary` includes source
dataset identity, `evaluation_mode: "known_opponent"`, selected-partition stable
player overlap, partition and temporal selection, coverage, all-decision
baseline results, actionable paired results, bounded breakdowns, and ordered
target games. Breakdowns cover stable player, acting side, game type, lead or
response phase, actionable preset, overall confidence, and role-relevant
confidence.

Selected-partition overlap is membership-only metadata. It does not claim that
an individual target has eligible history; strict timestamp filtering remains
authoritative for every target game.

Each target game includes record and game identity, preserved timestamp,
contract, participants, as-of source count and latest timestamp, compact player
profile/provenance summaries, reconciled aggregate results, and zero through 30 ordered
decision rows. Player summaries contain only bounded source IDs, timestamps,
exact and normalized statistics, and derivation, never full source games.
Decision rows expose legal cards but no hidden opponent hands.

Target game and distinct-player coverage use all three participants, including
players who did not act before concession. Decision breakdowns still contain
only actual actors. Target decision totals reconcile with per-game rows,
coverage, baseline counts, paired counts, and breakdowns.

Coverage explicitly counts missing as-of games, missing players,
insufficient-confidence, neutral, insufficient-data, explainable, and
actionable states. Runtime validation reconciles availability, baseline,
paired-outcome, target-game, player, and acting-side totals. The focused schema
is
[`schemas/rolling_opponent_policy_evaluation.schema.json`](../schemas/rolling_opponent_policy_evaluation.schema.json).

The checked-in example demonstrates strict rolling selection, repeated stable
identity with seat changes, complete baseline evaluation, and low-confidence
coverage. Focused tests construct 100 repeated source records to exercise
medium-confidence actionable paired behavior without making the public example
impractically large.

See [Shortened historical opponent workflows](shortened_historical_opponent_workflows.md)
for the shared game-level versus decision-level evidence boundary.

## Limitations

A higher preferred-card match rate means only that the selected deterministic
profile policy imitated the observed cards more often on the paired known-
opponent decisions. It does not prove stronger or optimal Skat play. Version 1
does not support overlapping partition names, target-partition rolling updates,
player-disjoint evaluation, unseen-player generalization, threshold tuning,
policy optimization, expected-value or game-outcome comparison, statistical
significance, learned profiles, or machine-learning models.
