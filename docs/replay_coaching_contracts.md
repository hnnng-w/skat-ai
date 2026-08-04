# Replay coaching contracts

## Version and scope

`src/skat_ai/replay_coaching_evidence.py`,
`src/skat_ai/replay_coaching_assessment.py`, and the focused prioritization
modules define internal Replay Coaching contracts:

```text
REPLAY_COACHING_CONTRACT_VERSION = 1
REPLAY_COACHING_PRIORITIZATION_VERSION = 1
MAX_REPLAY_COACHING_KEY_DECISIONS = 5
```

The contracts are frozen dataclasses with immutable tuples and deterministic
internal serializers. They do not add a stable package-root API, public JSON
schema, CLI field, example, or generated-output branch. Existing Immediate
Historical Review and Historical Search Review output remains unchanged.

The assessment contract defines evidence and impact semantics for one historical
card decision. Prioritization version 1 adds deterministic game-level Key
Decisions, Turning Points, and high-impact classification. It does not implement
patterns, advice, recommendations, tactical detectors, or a complete Coaching
Report.

The prioritization version, maximum, eligibility, ranking, Turning Point, and
high-impact rules are `skat-ai` product conventions. They are not official Skat
rule classifications.

## Information policy

The information policy is:

```text
decision_time_then_retrospective_attachment
```

The implementation creates two distinct immutable values:

* `DecisionTimeReplayCoachingEvidence`, built before the observed card is read;
* `ReplayCoachingDecisionAssessment`, built later by attaching one legal
  observed card and retrospective comparisons.

Decision-time evidence contains decision identity, perspective, phase, canonical
legal cards, normalized existing Immediate evidence, the existing aggregate
bounded-Search result, and the existing Search-versus-Immediate comparison. It
does not contain the actual card, future plays, later event details, final winner,
final game result, final settlement, final hidden hands, or final Skat.

The retrospective assessment may add only the observed legal card and comparison
or classification fields. It does not add final outcome or settlement context.
Search and Immediate are each run once before attachment; attachment reuses their
existing values and does not rerun either analysis.

## Game phases

Version 1 uses this product convention:

| Phase | Trick numbers |
| --- | --- |
| `opening` | 1 through 3 |
| `middle` | 4 through 7 |
| `endgame` | 8 through 10 |

Other trick numbers are invalid. This phase mapping is a Replay Coaching product
convention, not an official-rule classification.

## Immediate evidence

Immediate evidence normalizes the already completed Immediate analysis into:

* availability and one unavailable reason;
* the unchanged recommended card;
* candidate count;
* immutable candidates with card, one-based rank, recommendation marker,
  expected point swing, and game-type-aware objective utility.

Candidates use the existing objective: expected point swing for Suit and Grand,
and the existing Null contract-objective utility for Null. Candidate ranks reuse
the existing stable Immediate report order, including its tie-break, while the
separate legal-card tuple is canonicalized in deck order. Construction rejects
any misalignment among legal cards, report candidates, and the one existing
recommendation; normalization never changes that recommendation or introduces a
new tie-break.

The retrospective contract retains the existing Immediate `decision_quality`
only as `immediate_baseline_quality`. Those names are not Replay Coaching
statuses or Search impact tiers.

## Assessment statuses

Version 1 defines exactly:

* `forced_move`;
* `best_or_equivalent`;
* `strictly_below_best`;
* `not_assessable`.

A one-card legal set is always `forced_move`. These statuses deliberately do not
reuse `optimal`, `acceptable`, `suboptimal`, or `mistake` from Immediate review.

## Evidence bases

Evidence bases have this canonical priority order:

1. `all_compatible_worlds`;
2. `sampled_compatible_worlds`;
3. `completed_common_prefix`;
4. `immediate_expected_value`;
5. `none`.

When the existing Search actual-card comparison is available, its comparison
basis is authoritative. Immediate evidence is used only when that Search
comparison is unavailable. `none` is used when neither comparison is
assessable. This ordering is deterministic evidence selection, not calibrated
confidence.

`all_compatible_worlds` describes exhaustive structurally compatible-world
aggregation, not knowledge of the real deal. `sampled_compatible_worlds`
describes the selected IID sample. `completed_common_prefix` describes the exact
retained completed-world prefix of an incomplete Search call.

## Impact tiers

Version 1 defines exactly:

* `no_missed_impact`;
* `contract_success`;
* `settlement_score`;
* `card_point_margin`;
* `immediate_only`;
* `not_assessable`.

Search impact follows the existing aggregate lexicographic order:

1. local-side contract-success rate;
2. mean local-side settlement score;
3. Suit or Grand mean local-side card-point margin.

The first positive supported recommendation-minus-observed gap selects the
impact tier. Null has no card-point-margin objective and can never receive
`card_point_margin`. Version 1 adds no numeric coaching thresholds.

## Classification

### Forced moves

Exactly one legal card produces `forced_move` and `no_missed_impact`, regardless
of recommendation availability.

### Search comparisons

When Search comparison is available, zero strictly better aggregate cards
produces `best_or_equivalent` and `no_missed_impact`. This includes a different
canonical rank with aggregate metrics equal to the Search recommendation.

One or more strictly better aggregate cards produces `strictly_below_best`. The
impact is the first positive gap in contract success, settlement score, then
Suit/Grand card-point margin. A strictly-below-best Search comparison without a
positive supported gap is an invariant error.

### Immediate-only comparisons

When Search comparison is unavailable and Immediate evidence is available, the
existing objective utility determines the strict-better count. Zero produces
`best_or_equivalent` and `no_missed_impact`; a positive count produces
`strictly_below_best` and `immediate_only`. The informational Immediate expected-
point-swing gap and baseline quality remain attached, but Immediate quality
names are not mapped to Search impact.

### No evidence

When neither Search comparison nor Immediate evidence is available, the result
is `not_assessable` with evidence basis `none` and impact `not_assessable`.

## Aggregate equivalence

Aggregate equivalence compares Search metrics, not canonical rank. Two cards are
aggregate-equivalent when their supported aggregate metrics are equal. Canonical
card order still assigns deterministic ranks and the Search recommendation, but
a different canonical rank alone is not missed impact.

`aggregate_equivalent` is absent for Immediate-only and no-evidence assessments;
it is not inferred from Immediate quality labels.

## Factors

Factors use this deterministic canonical order:

1. `forced_move`;
2. `aggregate_equivalent_choice`;
3. `strictly_lower_contract_success`;
4. `strictly_lower_settlement_score`;
5. `strictly_lower_card_point_margin`;
6. `immediate_only_best_or_equivalent`;
7. `immediate_only_better_alternative`;
8. `search_unavailable`;
9. `no_assessable_evidence`;
10. `null_margin_not_applicable`.

Factors report only supported contract facts. They do not infer tactical plans,
causes, intentions, or player skill.

## Limitations

Limitations use this deterministic canonical order:

1. `bounded_late_game_search`;
2. `determinization_strategy_fusion`;
3. `sampled_compatible_worlds`;
4. `completed_common_prefix`;
5. `immediate_expected_value_only`;
6. `search_unavailable`;
7. `observed_card_not_ground_truth`;
8. `no_assessable_evidence`.

Every retrospective assessment includes `observed_card_not_ground_truth`.
Every Search assessment includes `bounded_late_game_search` and
`determinization_strategy_fusion`. Sampled and common-prefix assessments include
their corresponding narrower limitation. Immediate-only and no-evidence paths
state Search unavailability explicitly.

The observed card is historical behavior, not a ground-truth optimal label.
Likewise, exhaustive compatible-world coverage does not remove Strategy Fusion:
each determinized world can select a world-specific continuation. The aggregate
therefore does not prove an optimal imperfect-information policy.

## Validation and serialization

Construction validates contract version, decision chronology, trick phase,
play-index/root-seat mapping, stable identity, acting seat, local side, game type,
canonical unique legal cards, Immediate candidates and recommendation, Search
game type and candidates, actual-card legality, forced cardinality, aggregate
equivalence, impact gaps, Null margin exclusion, evidence-basis priority,
factor/limitation order, and not-assessable empty fields.

The decision-time serializer reuses the bounded-Search serializer and emits no
observed card. The assessment serializer nests that safe evidence, adds the
observed card and existing Search actual-card comparison, and emits no final
outcome. Neither serializer emits hidden worlds, derived seeds, private hands,
transposition state, principal variations, final hidden ownership, or final
Skat.

## No causal outcome claim

Version 1 classifies differences in the evidence available at one reconstructed
decision. It does not claim that one observed card caused the final winner,
result, settlement, or any later event. Final outcome context is deliberately
outside these contracts.

## Historical Search Review integration

One internal Historical Search Review execution now retains both the unchanged
public review summary and the chronological immutable assessment tuple. Search
and Immediate still run exactly once per decision. The existing public builder
returns the same serialized structure and values and does not expose the retained
assessments or prioritization.

The game-level builder accepts one validated historical record and exactly one
assessment per recorded card play. It validates contract version, source game,
contiguous one-based decision indices, chronological trick/play identity, acting
player and seat, side, game type, and actual-card alignment. Zero through 30
decisions are supported, including all current shortened records and a supported
continuation followed by terminal shortening.

## Key Decisions

Only `strictly_below_best` assessments with a supported positive missed-impact
tier are eligible. Forced moves, best or aggregate-equivalent choices,
not-assessable choices, and choices without missed impact are excluded.

Selection reasons, in priority order, are:

1. `contract_success_gap`;
2. `settlement_score_gap`;
3. `card_point_margin_gap`;
4. `immediate_only_gap`.

Within one reason, evidence basis uses the existing priority:

1. `all_compatible_worlds`;
2. `sampled_compatible_worlds`;
3. `completed_common_prefix`;
4. `immediate_expected_value`.

Remaining ordering is primary gap descending, strictly better card count
descending, then decision index ascending. At most five decisions are retained,
with contiguous one-based ranks and no duplicate decision.

Search primary gaps reuse the existing aggregate comparison field selected by
the impact tier. They are not recalculated. Immediate-only primary gaps use best
Immediate objective utility minus observed-card Immediate objective utility.
This preserves the Null contract objective and does not rank Null solely by raw
point swing. Every selected primary gap is finite and positive.

## Turning Points

Prioritization version 1 supports exactly these types, in canonical order:

1. `decision_opportunity`;
2. `recorded_outcome`.

Turning Points are sorted by decision index and then type order. Both types may
occur on one decision, but they remain separate objects with separate semantics.

A decision-opportunity Turning Point requires `strictly_below_best`,
`contract_success`, Search evidence, and a positive existing contract-success-
rate gap. Settlement-only, margin-only, Immediate-only, forced,
aggregate-equivalent, and not-assessable decisions cannot create one. It is a
counterfactual aggregate opportunity, not a causal statement about the recorded
result.

A recorded-outcome Turning Point is the first actual card-play-prefix transition
from `undecided` to `declarer_already_won` or `defenders_already_won`. The
timeline derives completed-trick cards, winner side, and points only from the
recorded prefix. It does not inspect remaining hands, hidden ownership, the final
Skat, future cards, or a terminal shortening. A continuation or shortening event
does not create a synthetic card decision. A forced actual card may carry this
Turning Point even though it cannot be a Key Decision.

Once decided, the recorded timeline may neither return to `undecided` nor switch
to the other side. An initially decided timeline is valid and creates no card
transition.

At the complete 30-card normal-play boundary only, a still-undecided state is
resolved with existing result, game-value, Overbid, and final-settlement helpers.
Point conservation supplies the terminal declarer total without reading final
Skat card identities. This supports a normal Null declarer win after all ten
tricks when the declarer took no trick. The fallback is never applied before the
complete prefix or to shortened games.

## High impact

No numeric threshold is used. High impact is true for every Turning Point, every
Key Decision with Contract-success impact, and every Key Decision on the same
decision as a recorded-outcome Turning Point. Settlement-score, card-point-
margin, and Immediate-only Key Decisions are otherwise not high impact.
Immediate quality names do not affect this classification. The game-level count
uses unique decisions, so two Turning Point types on one decision count once.

## Turning Point factors and limitations

Stable Turning Point factors use this canonical order:

1. `lower_contract_success_opportunity`;
2. `recorded_contract_became_decided`;
3. `recorded_declarer_became_decided`;
4. `recorded_defenders_became_decided`;
5. `forced_recorded_outcome_transition`.

Stable added limitations are:

1. `counterfactual_aggregate_not_causal`;
2. `recorded_path_only`;
3. `decision_not_single_cause`;
4. `observed_card_not_ground_truth`.

Decision opportunities retain their assessment limitations and add the
counterfactual non-causal limitation. Recorded outcomes use the recorded-path,
not-single-cause, and observed-card limitations. Neither type adds tactical,
intentional, skill, or causal interpretation.

## Prioritization result and serialization

The immutable game-level result records source identity, decision, assessable,
missed-impact, and unique high-impact counts, initial and final recorded states,
Key Decisions, and Turning Points. Construction reconciles counts, sources,
subsets, ranks, ordering, Turning Point references, and deterministic selection.

Internal serializers reuse the existing assessment serializer. They emit no
hidden hands, final Skat, compatible-world assignments, Search seeds,
transposition state, principal variations, final settlement, or causal free
text. No schema, CLI, example, generated scenario, or stable package-root API is
added.

## Remaining Replay Coaching work

Replay Coaching remains incomplete. Still missing are:

* cross-decision pattern aggregation;
* actionable coaching recommendations and explanations;
* tactical detectors;
* complete-game Coaching Report orchestration and presentation;
* public schemas, CLI output, examples, and generated-output coverage for such a
  future report;
* approved causal-language and outcome-context policy, if ever needed;
* broader Search, information-set policy solving, and Strategy Fusion correction.

These components require separate focused contracts and tests. Contract version
1 is only the information-safe evidence and impact foundation.
