# Information-set Search contracts

## Purpose

Issue #187 defines the private version-1 foundation for bounded
information-set-consistent Search. Issue #188 adds its separate private bounded
executor. Issue #189 integrates those retained values through strict flat,
retrospective, Historical Review, and Training Dataset evaluation boundaries.
Issue #190 adds strict Multi-Step and Policy Comparison integration version `1`.

The existing `compatible_world_minimax_v1` method evaluates each selected exact
Compatible World separately. A future action can therefore differ between two
worlds even when the acting Player cannot distinguish those worlds. This is
Strategy Fusion. Exact enumeration removes world-sampling uncertainty but does
not remove this policy inconsistency.

The new private method identifier is:

```text
bounded_information_set_policy_search_v1
```

It remains separate from `BOUNDED_SEARCH_METHODS`, `bounded_search`, and `auto`.
Issue #189 exposes it as flat `information_set_search`, a separate Historical
Information-set Search Review, and a separate Training Dataset evaluation. Issue
#190 routes the same strict method through Multi-Step and Policy Comparison; it
adds no `information_set_auto`. Match Capture, Match Analysis Reports, Strategy
Teacher Evidence, Replay Coaching classification, and performance integration
remain absent.

## Versioned values

The independent World State, Observation, Policy Settings, Budget, Request,
Preparation, and Result contract versions are all `1`. They do not change the
Package version, Public API contract, existing bounded-Search schema, Compatible-
world selection, Exact State, Dataset, Provenance, or Domain versions.

All new values are frozen, slotted, recursively immutable, and deterministically
serializable. Cards use full-deck order; Players use `me`, `left`, `right`;
Tricks retain chronology; public hands, public voids, and fixed Policies use
canonical Player order. No selected-world index, random UUID, current time,
process identity, path, or unordered iteration is retained.

## Controlled and fixed Players

Version 1 controls exactly `me`, the root
`SearchInformationView.perspective_player`. Equal future observations for `me`
select one equal action. The executor is a best response for this root Player
against supplied fixed Policies, not a three-player equilibrium
or joint Defender-team optimization.

`left` and `right` remain separate fixed-policy actors. This remains true when
`me` is a Defender: the partner is not jointly optimized and never receives
`me`'s hand. Each actor receives only their own private hand and public facts.

The deterministic fixed-policy values are:

```text
lowest_point
highest_point
basic_trick_play
basic_defender_response
basic_defender_lead
```

`random_legal` is excluded because it has no deterministic preferred-card set.
Defender-specific lead and response Policies require a Defender actor. The
selection primitive reuses `get_preferred_opponent_cards_by_policy()` and chooses
the first preferred legal Card in canonical deck order. Partner-currently-
winning status is derived only from the public current Trick; no partner hand or
random generator is supplied.

## World State

`InformationSetSearchWorldStateV1` pairs one selected `ExactSearchState` with
the complete public history omitted by that exact state. It retains:

* source and information cutoff;
* root perspective;
* legitimate root-visible out-of-play Cards;
* one exact selected state;
* every public completed Trick;
* authorized exact public hands;
* public failure-to-follow constraints.

The focused builder strictly reconciles Declaration, Declarer, current Trick,
next Player, points, completed-Trick counts, all remaining-hand sizes, the local
hand, visible out-of-play Cards, public hands, and public voids. Public completed
Cards must equal the exact state's implicit completed-Card set. Contradictions
are invariant errors rather than unsupported Search outcomes.

Selected-world identity and sampled-draw index are absent. Repeated IID draws of
one exact state therefore produce equal World State values while remaining
repeated entries in the selected sequence.

## Public hands and voids

Authorized public hands retain their existing source and `all_players`
visibility. Every public play by their owner removes that Card from the public
hand. An empty public-hand constraint remains after its last Card is played so
the authorization and public history remain explicit.

`InformationSetPublicVoidConstraintV1` contains only one Player and canonical
forbidden effective categories. It contains no exact hidden ownership. Root
constraints are reconstructed from public completed Tricks and the current
Trick, then reconciled with the existing hidden-card inference constraints.

A future response extends public void evidence only when its effective category
differs from the led category. A lead never establishes a void. Suit and Grand
use the existing trump-aware effective categories; Null uses printed suits.

## Pure transition

`apply_information_set_search_card_v1()` is a state primitive, not Search
execution. For one legal Card it:

1. calls `apply_exact_search_card()` exactly once;
2. uses the returned exact next state;
3. appends the returned completed Trick when present;
4. shrinks the acting owner's authorized public hand;
5. adds only publicly proved failure-to-follow evidence;
6. retains source, cutoff, root perspective, and root-visible out-of-play Cards.

It does not independently calculate legal Cards, remove exact Cards, derive the
next Player, calculate a winner or points, or modify exact counters.

## Actor observations

`InformationSetSearchObservationV1` is the exact Information-set key. It
contains:

* actor identity and side;
* exact actor remaining hand;
* actor-visible out-of-play Cards;
* Declaration, Declarer, and game type;
* complete public play history and current Trick;
* points, Trick counts, and all public remaining-hand sizes;
* authorized shrinking public hands;
* public void constraints;
* exact legal Cards;
* information cutoff.

It does not contain another Player's exact hand, hidden out-of-play ownership,
selected-world identity, sampled-draw index, future Play, final outcome,
Settlement, Search value, or coherent Multi-Step root identity.

Out-of-play visibility is actor-specific:

* a non-Hand Declarer sees the exact two Discards;
* a Hand Declarer does not see the original Skat;
* a Defender does not see hidden Skat or Discards;
* legitimate root-visible Cards remain visible to `me`.

Structural Observation equality defines one Information Set. Different hidden
opponent ownership or hidden Defender-partner ownership alone does not split it.
Different own hands, public histories, current Tricks, authorized public hands,
public void evidence, legal Cards, or visible Discards do split it.

## Budget and Request

`InformationSetSearchBudgetV1` adds `max_information_sets` beside the existing
depth, state-node, selected-world, sampled-world, comparable-world, and optional
timeout limits. All structural limits are strict positive integers. The timeout
is null or a strict positive integer and remains an operational cutoff rather
than a latency promise.

Version 1 allows at most three unresolved Tricks, including a current incomplete
Trick. Sampling cannot exceed selected worlds and minimum comparable worlds
cannot exceed selected worlds. Issue #189 maps the existing named Search profiles
to this Budget for retrospective workflows; it adds no profile identifier.

`InformationSetSearchRequestV1` contains one existing safe
`SearchInformationView`, the new Budget, an explicit non-boolean integer world-
selection seed, and exact Policy Settings. It contains no exact opponent hand,
selected world, coherent execution root, Immediate settings, fallback, Profile,
or Statistics input. Direct views are rejected unless every nested Card and
category collection is an immutable canonical tuple, opponent exact ownership
has an equal authorized public hand, and out-of-play visibility is role-safe.

## Preparation

`prepare_information_set_search_v1()` performs no Policy Search. It:

1. validates one Request;
2. assesses existing Search eligibility with the three-Trick maximum;
3. builds at most one existing Compatible-world space;
4. performs at most one existing Compatible-world selection;
5. builds one World State and root Observation per selected draw;
6. verifies that all selected root Observations and legal-Card tuples are equal.

Existing exact enumeration and deterministic uniform IID sampling are reused
unchanged. Selected order is not sorted, and duplicate draws are not deduplicated.
The existing selection stream remains the only stream.

An available Preparation retains the selection, ordered World States, one root
Information Set, and canonical legal Cards. An unavailable Preparation retains a
canonical reason and no World States or root Information Set. Malformed direct
inputs and exact/public contradictions remain validation errors.

Issue #188 adds strict retained-Preparation reconciliation before execution. It
validates the retained Request, eligibility, selection counts and order, sampled
duplicate multiplicity, exact/public World facts, root Observation and legal
Cards, fixed-policy roles, and three-Trick eligibility without rebuilding or
reselecting Worlds.

## Result semantics

`InformationSetSearchResultV1` is now constructed by the private Issue-#188
executor. It reuses
`AggregateSearchCandidateResult` and `rank_search_candidate_results()` unchanged.
Ranking remains:

1. local contract success rate;
2. mean local-side game score;
3. Suit/Grand mean local-side card-point margin;
4. canonical Card order.

Null has no card-point-margin objective.

Status semantics are:

* `complete`: every selected world completed, one recommendation exists, the
  claim is `exact_selected_world_policy`, and equal controlled observations use
  one action; the recommendation equals the one depth-zero controlled decision,
  which reaches every selected world;
* `partial`: a structural budget ended execution, the claim is
  `common_policy_prefix`, the named structural limit exactly matches its
  consumed count, only fully resolved controlled Decisions are retained, and
  version 1 emits no Candidates, completed Worlds, or recommendation;
* `timeout`: a requested wall-clock cutoff activated, no Policy claim or
  Candidates, controlled Policy, completed Worlds, or recommendation are
  retained;
* `unavailable`: coverage and claims are `none`, candidates and controlled
  Policy are empty, recommendation is null, and consumed counts are zero.

`exact_selected_world_policy` means exact only over the retained selected world
sequence under the supplied fixed-policy model. With sampled coverage it is not
exact over every Compatible World. It makes no equilibrium, Nash, perfect-play,
global-optimality, complete-contract, or calibrated-probability claim.

For complete execution, the retained controlled Policy count equals both fully
resolved controlled Decisions and evaluated Information Sets. For partial
execution, its count equals fully resolved Decisions and may be lower than
started Information Sets. Duplicate Information Sets and conflicting actions
remain invalid.
All retained controlled Information Sets share one Declaration, Declarer, and
cutoff, and supplied fixed Policies remain valid for those Player roles.

## Workflow boundary and integration

The private contracts and executor still import no PIMC executor, coherent
Multi-Step world, Public API, CLI, or file/network transport. Preparation does
not evaluate terminal utility, aggregate Candidates, rank recommendations, or use
fallback. The executor uses exact transitions, actor Observations, fixed
Policies, existing terminal utility, existing Candidate aggregation, and
deterministic ranking. It retains invocation-local World and ordered-bundle
caches and performs no I/O.

Issue #189 adds strict flat routing without baseline or fallback; retrospective
same-selection PIMC plus independent Immediate comparison; separate Historical
Review and Training Dataset evaluation; safe public serialization; retained-
stage internal and opt-in public Provenance; four strict Schemas; one example;
and four generated scenarios. Issue #190 adds fresh strict public-state Search at
each Multi-Step local decision, domain-separated child seeds, no Search World or
controlled-Policy reuse, strict no-recommendation stopping, safe nested Decision
Results, and one appended Policy Comparison row with compact diagnostics. It
does not change the contracts or executor algorithm described above.

Match Capture, Match Analysis Reports, Strategy Teacher Evidence, Replay Coaching
classification, and performance evidence remain outside this integration. There
is no cross-decision global Policy, equilibrium, global optimality, or calibrated-
probability claim.

See [Information-set Search executor](information_set_search_executor.md) for
the Issue-#188 algorithm, memoization, counter, Policy, and incomplete-Result
semantics. See [Information-set Search workflows](information_set_search_workflows.md)
for Issue #189 routing, comparison, privacy, Provenance, CLI, and Schema behavior.
See [Information-set Search Multi-Step and Policy Comparison](information_set_search_multi_step_and_policy_comparison.md)
for the Issue-#190 integration boundary.
