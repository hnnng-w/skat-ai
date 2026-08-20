# Party-wide Claim proof executor

## Status and scope

Issue #184 implements one private deterministic exhaustive executor for an
available `PartyWideClaimProofPreparationV1`. It proves whether the complete
claiming party can force ownership of every unresolved Trick in the one exact
complete world retained by Issue #183.

The executor is not a Runtime Claim, Historical ending, Game Result, Settlement,
Search workflow, Public API, CLI, Schema, example, generated scenario, or Corpus
value. It creates no game end or public output. Claims and Final Settlement
remain partially supported.

## Version and policies

The executor has independent version:

```text
PARTY_WIDE_CLAIM_PROOF_EXECUTOR_VERSION = 1
```

Its method and policies are:

```text
party_wide_all_remaining_tricks_exact_and_or_v1
exhaustive_complete_world_and_or_proof
claiming_party_existential_opposing_party_universal
canonical_legal_card_order
exact_state_outcome_and_representative_suffix
opposing_trick_invalidates_otherwise_normal_completion_validates
first_canonical_decisive_branch
unique_uncached_exact_states_and_proof_terminal_states
complete_without_partial_timeout_or_budget
```

The entry point is:

```python
execute_party_wide_claim_proof_v1(preparation)
```

It returns the existing `PartyWideClaimProofResultV1` contract. No existing
Claim, Evidence, exact-state, Request, preparation, Move, assignment, or Result
contract version changes.

## Preparation handling

An unavailable preparation passes directly through to the existing unavailable
Result builder with the exact preparation reason. Execution performs no Request
rebuild, legal-Card lookup, transition, state evaluation, Search, or assignment.

An available preparation is fully reconciled before traversal. The executor:

1. validates the retained preparation, Claim, Evidence, Request, exact context,
   and exact state types and versions;
2. rebuilds the existing Proof Request exactly once from the retained Claim,
   Evidence, and Exact State Context;
3. requires exact equality with the stored Request;
4. raises `SkatAIInvariantError` for forged internal inconsistency.

It does not rebuild Evidence, replay Historical play, rebuild the Exact State
Context, or construct another `ExactSearchState`.

## Root proof facts

The traversal retains the root opposing completed-Trick count. For a Declarer
Claim, this is the root Defender completed-Trick count. For a Defender Claim,
this is the root Declarer completed-Trick count.

Existing opposing-party Tricks before the Claim are therefore only a baseline.
They do not invalidate the Claim. The first newly completed opposing-party Trick
does invalidate it.

At every uncached exact state, the executor evaluates in this order:

1. If the opposing completed-Trick count exceeds the root baseline, classify a
   proof-terminal failure.
2. Otherwise, if normal exact play is terminal, classify a proof-terminal
   success.
3. Otherwise, enumerate and traverse legal child states.

Failure precedes normal completion because the final unresolved Trick can both
complete the Game and invalidate the Claim.

## Party quantifiers

The acting Player is classified through the retained Exact State Context:

| Acting party | Quantifier | Traversal behavior |
| --- | --- | --- |
| claiming party | existential | The first satisfied canonical child succeeds. If none succeeds, the first canonical failed line is retained. |
| opposing party | universal | The first failed canonical child invalidates. If none fails, the first canonical successful line is retained. |

For a Declarer Claim, the Declarer is existential and both Defenders are
universal. For a Defender Claim, both Defenders are existential and the Declarer
is universal. The existential scope is the complete claiming party, not only the
Player who asserted the Claim.

Defender-party cooperation is a complete-world proof convention. It does not
claim that either Defender knew the partner's private hand, communicated during
play, or followed an information-set-consistent team policy.

## Exact legal play

Future traversal uses only:

```text
get_exact_search_legal_cards()
apply_exact_search_card()
```

The exact kernel supplies canonical legal-Card order and immutable transitions.
The executor does not remove Cards, derive the next Player, complete Tricks,
calculate winners or points, or update counters independently. A non-terminal
state without a legal Card is an invariant failure.

## Memoization and counters

The invocation-local memo maps each `ExactSearchState` to:

```text
satisfied boolean + Representative Line suffix
```

There is no global cache. Every uncached state increments
`evaluated_state_count` and is memoized exactly once. Proof-terminal states also
increment `terminal_state_count`. Cache hits change no counter and are not
exposed.

For every completed execution:

```text
memoized_state_count == evaluated_state_count
```

The counters mean:

* `evaluated_state_count`: unique uncached exact states;
* `memoized_state_count`: final exact-state memo size;
* `terminal_state_count`: unique memoized states classified as proof success or
  failure terminals.

## Representative line

Every retained Move is built through the existing focused Move builder. Flat
Players are converted to stable IDs through the retained context mapping. A
Trick-completing Move uses only the exact transition's winner Player and winner
party; the executor does not recompute either value.

Canonical short-circuiting selects the first decisive branch. A valid line
contains every future Card play, reaches normal completion, and contains no
opposing-party Trick. An invalid line stops immediately after the first
opposing-party Trick and contains no later Move.

The line is diagnostic. It is not a serialized complete strategy tree.

## Results and assignment

A satisfied root builds the existing exact proof assignment from Evidence:

* every unresolved Trick;
* every unresolved in-play Card, including Cards already in an incomplete
  current Trick;
* every unresolved in-play Card point;
* recipient equal to the claiming party.

It then builds the existing `valid` Result. A failed root builds the existing
`invalid` Result with no assignment, one decisive counterexample line, and a
complete proof. Available execution returns only `valid` or `invalid`.

`party_wide_claim_proof_not_executed` remains available to a caller that chooses
not to invoke the executor. It is not returned by available execution.

## Bound and determinism

The existing one-through-five unresolved-Trick preparation bound is the complete
execution bound. The executor adds no node budget, depth budget, timeout, clock,
seed, sampling, randomness, partial prefix, cancellation, or background work.

Equal available preparations produce equal Results, counters, assignments, and
Representative Lines. Determinism follows from the retained exact state,
canonical legal-Card order, exact immutable transitions, fixed quantifiers,
canonical short-circuiting, and invocation-local exact-state memoization.

## Compatibility and privacy

The existing defender-open-play proof remains separate and unchanged. Its
exposing Defender is existential while the Declarer and non-exposing Defender
are universal. The party-wide executor does not wrap, redirect, or reinterpret
that event-specific proof.

Settlement Normative Matrix version `2` retains all 61 cases. The approved Claim
case remains `implementation_required`, Runtime-module-free, and unavailable to
Runtime as `party_wide_claim_not_implemented`. The executor is not added to the
Matrix module tuple.

Complete Evidence and proof Results remain private Retrospective values and may
contain the exact complete Deal. No private Card is attached to an existing
public value. Package version `0.16.0`, Public API contract version `1`, seven
Root workflows, one Console Script, 63 Schemas and Packaged Schema Resources,
six Session examples, and 85 generated outputs remain unchanged.

## Remaining work

Separate later work is still required for:

1. Runtime Claim input and GameShortening integration;
2. a Retrospective Historical Claim ending;
3. any Public API, CLI, Schema, Session, Match Capture, Corpus, example,
   generated-output, Provenance, Confidence, Recommendation, or Coaching
   exposure.

Issue #185 separately completes private valid-proof adjudication and existing
Game Result, level, Overbid, and Final Settlement composition. It does not change
this executor or execute proof again. See [Party-wide Claim
adjudication](party_wide_claim_adjudication.md).
