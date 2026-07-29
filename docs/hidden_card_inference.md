# Hidden-card inference

`skat-ai` applies bounded exact hidden-card inference when public play proves
that a player legally failed to follow an effective card category. The model
narrows otherwise possible card assignments; it does not predict tactical
choices or claim to identify the actual hidden deal.

## Allowed evidence

Only hard decision-time ownership and legality evidence is accepted:

* the local player's exact current hand;
* exact public hands from declared Ouvert, declarer-card-exposure continuation,
  or defender-open-play continuation;
* the skat only when it is legitimately known to the acting player;
* public played cards with concrete attributed ownership; and
* a confirmed legal failure to follow the category led.

Effective categories reuse `get_effective_suit`. Suit games distinguish the
trump category, including all jacks, from each side suit. Grand distinguishes
the jack trump category from the four side suits. Null uses the four printed
suits and has no trump category in play.

A failure-to-follow constraint starts only after the public off-category play
that proves it. It persists for later decisions but is never applied
retroactively. A partially played current trick contributes evidence only when
its concrete leader determines the fixed three-player play order.

Canonical completed tricks with `cards` and ordered `players` are treated as
trusted legal attributed public history after normal input validation. Complete
historical games are stricter: exact prefix replay proves ownership, order, and
follow legality. Legacy `played_cards`, completed tricks without `players`, and
other unattributed plays are never assigned to a guessed owner. Mixed history
reports reduced provenance availability rather than inventing attribution.

## Excluded evidence

The inference model never derives a card constraint or weight from:

* tactical card choices;
* bidding or declaration behavior;
* opponent statistics, profiles, or policy presets;
* claims, concessions, exposure acceptance, or continuation responses;
* timing or latency;
* future play;
* final points, result, game value, overbid, or settlement; or
* complete post-game hands that were hidden at the decision.

The model is structural, not behavioral, Bayesian, calibrated, or learned.

## Exact compatible worlds

Every allowed fact becomes an immutable ownership or forbidden-category
constraint. Exact public hands remain authoritative. A contradiction between a
confirmed void and an exact hand or later attributed public ownership is
rejected; constraints are not weakened, reweighted, or silently corrected.

Unresolved labeled cards are assigned across exact `left` and `right` hand
slots and the remaining hypothetical skat slots. Dynamic programming computes
the exact number of compatible labeled assignments and exact per-card ownership
marginals. Each compatible labeled assignment has uniform probability.

Seeded sampling follows dynamic-programming completion counts to select one
compatible world uniformly and deterministically. It does not repeatedly shuffle
and reject incompatible deals, so there is no rejection loop.

The model is optional when no confirmed failure-to-follow evidence exists. When
hard constraints leave zero compatible worlds, analysis rejects the
contradictory position.

## Confidence

Per-card confidence describes only ownership concentration across the exact
compatible-world set:

| Confidence | Exact meaning |
| --- | --- |
| `confirmed` | Exactly one owner has non-zero compatible assignments. |
| `high` | Multiple owners remain and the largest ownership probability is at least `0.85`. |
| `medium` | Multiple owners remain and the largest ownership probability is at least `0.65` but below `0.85`. |
| `low` | Multiple owners remain and the largest ownership probability is below `0.65`. |

These labels are not calibrated probabilities of real-world correctness.
Confidence never creates a new constraint, changes a world weight, or influences
a policy independently of the exact compatible assignments.

## Analysis workflows

Immediate Analysis derives the model once for the decision and uses one common
seeded sequence of compatible worlds for every legal candidate. Hidden-card
inference does not change legal cards, opponent policies, Suit/Grand or Null
objectives, candidate ordering rules, or ties.

Multi-Step samples one compatible coherent root at path start. Opponent-turn
preparation and candidate completion preserve that root ownership and fixed
hypothetical skat. A later visible simulated failure to follow may add evidence
for a later decision; it cannot alter the immutable root or become retroactive.
`highest_expected_value` receives only the later public state and compatible
counterfactual samples, never private ownership of unplayed root cards.

Policy Comparison derives one shared inference model, samples one shared root,
and gives each policy an equal immutable copy. Paths may accumulate different
later public evidence after their simulated plays diverge, but no path mutates
another path or starts from a separately sampled model or root.

Declared-Ouvert and both continuation exact public hands remain authoritative in
all three workflows. Any conflict with inferred constraints rejects the state.

## Historical boundary

Historical review derives each model independently from the decision's visible
prefix: the local hand, attributed completed plays, earlier cards in the current
trick, exact public hands visible by then, and legitimately known skat. The
actual card for that decision remains a retrospective comparison label and does
not enter inference before analysis.

Inference cannot use the actual next card, later plays, future or complete
hidden hands, final result, game value, overbid, settlement, or terminal and
non-terminal event facts that are not yet public. Exact complete-game ownership
is available to replay validation but is not copied into a decision model.

## Output and privacy

When confirmed failure-to-follow evidence is available, position output,
Multi-Step, Policy Comparison, and reviewed historical decisions can include
`hidden_card_inference_summary`. Its strict schema is version `1`:

[`schemas/hidden_card_inference_summary.schema.json`](../schemas/hidden_card_inference_summary.schema.json)

The summary reports the decision cutoff, exact model and confidence semantics,
provenance status, compatible-world count, evidence, confirmed voids, exact
ownership marginals, thresholds, and explicit non-behavioral and no-future-
information flags. Its privacy flags confirm that output contains no sampled
hands, sampled hypothetical skat, coherent-root ownership, actual historical
hidden hands, or dynamic-programming tables.

The summary's ownership probabilities describe all exact compatible assignments;
they do not reveal which private world was sampled for execution.

## Example

Run the deterministic Grand example from the repository root:

```powershell
python main.py --input examples/grand_hidden_card_inference.json --multi-step 2
```

The root public history confirms that `right` is void in the Grand clubs side
category. The exact compatible-world count is `275275`. The two-step scenario
also demonstrates that a later visible simulated failure can increase the
evidence available at a later step without changing the original root.

Implementation and focused coverage are in:

* `src/skat_ai/hidden_card_inference.py`
* `schemas/hidden_card_inference_summary.schema.json`
* `examples/grand_hidden_card_inference.json`
* `tests/test_hidden_card_inference.py`

## Unchanged scope

Issue #104 adds no input field, policy, behavioral model, Bayesian model,
calibrated confidence, learned model, or model-training workflow. Rules, legal-
card detection, objectives, game results, game values, overbid handling, and
settlement are unchanged. Training feature generation remains version `1` with
target `actual_card_played`; sample IDs, opponent profiles, statistics, rolling
metrics, and profile signals are unchanged, and no inference feature or target
is added. The package version remains `0.8.0`.
