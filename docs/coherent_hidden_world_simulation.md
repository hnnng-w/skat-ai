# Coherent hidden-world simulation

Multi-Step simulation now executes each path against one coherent private
hidden-card assignment. The assignment is sampled once at path start and is not
resampled between steps. This is an execution-consistency guarantee, not a
perfect-information solver or a claim that the sampled world is the real deal.

## Path root

One immutable private execution root assigns every currently unknown opponent
card to `left` or `right` and assigns the remaining unseen cards to one fixed
hypothetical skat. Public state and every exact `PublicHandConstraint` are
reconciled before the root is accepted. When attributed public play confirms a
failure to follow, the root is sampled uniformly from only the exact compatible
labeled assignments counted by the hidden-card inference model.

The root ownership assignment is preserved for the complete path:

* opponent-turn preparation and candidate-trick completion use the same world;
* an opponent may play only a card assigned to that opponent;
* each opponent play creates a new immutable world value with that card removed
  from its owner;
* a played card cannot move to the other hand, return later, or enter the skat;
* the hypothetical skat remains fixed and is never played;
* hand sizes, known state, public constraints, and ownership transitions are
  reconciled at every supported step.

Exact public constraints remain authoritative. This includes a declared-Ouvert
declarer hand, either continuation hand, and the supported coexistence of two
disjoint public hands. A public card is assigned to its exact owner at the root
and disappears only when that owner plays it.

## Information boundary

The private execution root is internal path state. Local card-selection decision
policies receive the public decision-time state, hand sizes, and authorized
public constraints, never the private root ownership of unplayed cards. JSON
output likewise emits no hidden card identities, hidden-world digest, or
hypothetical skat cards.

`highest_expected_value` retains its existing public decision-time
counterfactual Monte Carlo samples. Those samples rank legal local candidates;
they do not expose, replace, or mutate the private execution root used to carry
the selected action forward. Other local card-selection policies are unchanged.

Opt-in `bounded_search` and `auto` decisions use the same separation. Opponent
actions first prepare the public decision in the coherent world. Search then
receives only that prepared public state, public counts, authorized public hands,
legitimate Skat visibility, and decision-time evidence. It reconstructs separate
compatible worlds without receiving or comparing against the coherent root. The
recommended legal local card is subsequently executed in the coherent world.

Immediate Analysis does not create a persistent Multi-Step execution root. It
derives one exact inference model for the decision and gives every legal
candidate the same compatible-world sequence. Legal cards, policies, objectives,
and tie behavior are unchanged.

## Random streams

Seeded Multi-Step execution derives stable separate random streams for the root
world, opponent actions, and each step's `highest_expected_value`
counterfactual samples. Root sampling therefore does not consume opponent-action
randomness, and counterfactual sampling does not advance either execution
stream. Search-aware Multi-Step derives the additional per-decision stream
`multi_step_bounded_search_decision_v1` from the explicit Search base seed. It is
not mixed with the coherent root, opponent actions, Immediate seed, policy name,
outcome, or ownership. Unseeded legacy execution remains probabilistic.

## Policy Comparison

Policy Comparison samples one shared root assignment for the comparison. Every
policy path receives an equal independent immutable copy of that root. Paths may
then diverge through their selected local actions and resulting opponent plays
without mutating another policy's world. They share one root inference model;
later visible simulated failure-to-follow evidence may diverge by path after
their public plays diverge.

This keeps compared policies equal on initial hidden ownership as well as public
constraints and settings. Differences cannot come from a separately resampled
root. The existing ranking objective, tie-breakers, supported policies, and
opponent-policy precedence are unchanged.

Without Search configuration, the compared set remains exactly the four legacy
policies. With explicit `bounded_search` or `auto`, exactly that policy is
appended last. Its coherent copy is used only for opponent preparation and
execution, never as a Search world or Search input. A no-recommendation Search
path remains visible but is ineligible for recommended-policy selection.

## Output summaries

Multi-Step exposes privacy-safe status and count metadata under
`context_summary.hidden_world` and each `steps[].coherence_summary`. The summary
reports mode, initial and remaining location sizes, one-root sampling status,
ownership-transition counts, reconciliation status, fixed-skat status, and that
no hidden cards were emitted. It never serializes either opponent hand or the
hypothetical skat.

Policy Comparison adds `policy_comparison_result.hidden_world` with shared-root,
root-sample-count, independent-path, policy-path-count, and privacy status. Each
policy row's context summary reports the same privacy-safe per-path coherence
shape.

When confirmed failure-to-follow evidence exists, Multi-Step and Policy
Comparison also emit the version-1 privacy-safe
`hidden_card_inference_summary`. Multi-Step may emit a later step summary after
new visible simulated evidence. Neither summary emits sampled ownership,
hypothetical skat cards, or dynamic-programming tables.

See [Output JSON](output_json.md) for the stable fields and
[`examples/grand_coherent_hidden_world.json`](../examples/grand_coherent_hidden_world.json)
for the deterministic three-step Policy Comparison scenario.

## Historical and data boundaries

Historical review remains an Immediate Analysis workflow. Its inference model
uses only the visible attributed prefix, current trick, public hands, and
legitimately known skat. The actual next card, future hands and plays, complete-
deal ownership, result, settlement, and not-yet-public events are excluded. The
Multi-Step root does not authorize future-hand leakage into historical review.

Training feature generation remains version `1` with target
`actual_card_played`. No root-world card, simulated ownership, coherence field,
inference feature, ownership statistic, evidence signal, or future hand is added
to model-facing features or labels. Rolling
opponent-policy evaluation remains a snapshot-based deterministic behavioral
comparison and does not run Multi-Step or consume a private execution root.

## Unchanged scope and non-goals

Supported and unsupported turn phases and `unsupported_turn_phase` stops are
unchanged. Search integration does not add automatic completion of opponent-only
phases, new input fields, opponent Search, coherent-root access, path-global
budgets, cross-decision caches, principal-line execution, behavioral or Bayesian
hidden-card inference, learned behavior, model training, or confidence that the
sampled root matches the real deal. Scoring, settlement, training versions, and
rolling metrics remain unchanged. See
[Hidden-card inference](hidden_card_inference.md).
