# Claim and Settlement v1 boundaries

## Decision status

Issue #182 closes the remaining v1 product-decision gate for Claims and updates
the internal Settlement Normative Matrix to version `2`. It approves exactly one
bounded Claim direction for later v1 implementation and classifies every other
currently known unresolved Claim boundary as `not_supported_v1`.

This is a product contract audit, not Runtime implementation. The repository
still has no party-wide Claim input, Runtime union member, Historical Claim
record, proof executor, Schema, Public API, CLI option, example, or generated
scenario. Claims and Final Settlement remain `partially_supported` until later
Issues implement and validate the approved Runtime path. Complete official-rule,
Claim, concession, or Settlement coverage is not claimed.

## Approved Claim

The only implementation-required Claim case is:

```text
claim_boundary.decision.party_wide_all_remaining_tricks_claim
```

Its matrix contract is:

```text
implementation_status: implementation_required
interpretation_scope: approved_bounded
evidence_class: bounded_exact_proof
proof_policy: party_wide_all_remaining_tricks_claim_v1
proof_maximum_unresolved_tricks: 5
stable_unavailable_reason: party_wide_claim_not_implemented
```

The future structured Claim means exactly:

```text
The claiming party can force ownership of every unresolved Trick.
```

It does not cover a specified count or identified subset of future Tricks.

## Future structured input

A later Runtime contract must use structured Retrospective input. It must retain
and reconcile all of the following:

* one exact `claimant_player_id`;
* one exact `claiming_party`, either `declarer` or `defenders`;
* the exact three retained Game participants and Declarer identity;
* the complete observed legal play prefix;
* the exact current Trick, including attributed Cards and turn state;
* the complete remaining hand of every Player;
* the original Skat and Discards or Hand-game ownership needed to reconcile the
  complete world;
* the existing declaration, game type, Matadors, bid, required value, completed
  Trick ownership, and point state needed by existing result and Settlement
  behavior.

The claimant Player must belong to the declared claiming party. All Cards,
hands, the current Trick, the play prefix, completed Tricks, Skat, and Discards
must reconcile as one exact legal Game state. The approved contract does not
define the eventual field layout, Schema version, public identifier, transport,
or serialization shape; those remain implementation work for later Issues.

## Evidence scope

The Claim is post-game and Retrospective only. It is unavailable for Live
adjudication. Proof requires complete remaining-hand evidence and one exact
current Trick and play prefix. No hidden ownership is inferred, sampled, or
aggregated.

The approved contract covers Suit, Grand, Null, Null Hand, Null Ouvert, and Null
Hand Ouvert. It is a bounded perfect-information proof over the retained complete
world. For a Defender-party Claim, the two Defenders may be evaluated as one
cooperative claiming party in that complete world. This does not assert that
either Defender knew the partner's private hand during play.

## Proof policy

`party_wide_all_remaining_tricks_claim_v1` uses exactly these party-level
quantifiers:

| Party | Quantifier |
| --- | --- |
| claiming party | existential |
| opposing party | universal |

The claiming party needs at least one legal strategy that wins every unresolved
Trick against every legal opposing-party response. The proof accepts at most
five unresolved Tricks, including a current incomplete Trick. More than five is
unavailable, not partial.

The proof does not establish:

* an information-set-consistent team policy;
* live communication or signaling;
* calibrated probability;
* optimal hidden-information Skat strategy;
* a Generic Search recommendation or Search solution claim.

## Valid proof

A future valid proof may create one terminal shortening. It must:

* assign every unresolved Trick to the claiming party;
* assign every unresolved Card and card point consistently with those Tricks;
* preserve an already established winner;
* otherwise derive the winner from the fully assigned result;
* preserve the existing declaration, bid, and required value;
* reuse existing Suit, Grand, Null, level, overbid, result, and Settlement
  behavior;
* apply no Schneider or Schwarz level to a Null contract;
* keep complete private proof hands out of public output.

The proof assigns the unresolved Game state to the claiming party. It does not
invent a different declaration, corrected play sequence, or replacement
contract.

## Invalid proof

An invalid proof creates no terminal outcome. In particular, it creates no:

* automatic assignment of unresolved Tricks or points to the opposing party;
* forced winner;
* Settlement;
* opposing-party penalty fallback;
* legacy remaining-point assignment.

The caller must instead retain continued observed play or provide another
already supported terminal ending. Invalidity is not proof that the opposing
party can force every unresolved Trick.

## Unavailable proof

Incomplete evidence, contradictory evidence, an unsupported state, or more than
five unresolved Tricks creates no terminal outcome and no Settlement. There is
no fallback to:

* Generic Search;
* compatible-world aggregation;
* heuristic hidden-card inference;
* legacy remaining-point assignment;
* generative adjudication.

While Runtime implementation is absent, the approved matrix case uses stable
reason `party_wide_claim_not_implemented`.

## Search separation

The future dedicated Claim proof may reuse the neutral exact legal-transition
kernel:

```text
ExactSearchState
get_exact_search_legal_cards()
apply_exact_search_card()
existing trick-winner and point helpers
```

That reuse does not make Perfect-Information Minimax, compatible-world Minimax,
Search aggregation, or bounded Search a Claim proof. The Claim contract has no
Search budget, cache, Recommendation, Search Result, compatible-world selection,
or information-set fallback. Issue #182 adds no imports between the matrix and
Search and changes neither exact-state nor Search Runtime behavior. The approved
proof is neither a Recommendation nor a Coaching contract.

## Legacy separation

These existing reasons remain legacy compatibility only:

```text
declarer_claimed_remaining_tricks
declarer_conceded_remaining_tricks
defenders_conceded_remaining_tricks
```

Their current serialization and simplified remaining-card-point assignment are
unchanged. They are not the approved structured party-wide Claim and do not
prove remaining Trick ownership.

## Durable v1 exclusions

The following exact boundaries are `not_supported_v1` and receive no Runtime
implementation plan before v1:

* specific future-Trick-count Claims;
* specific future-Trick-identity Claims;
* generalized non-jack theoretical exclusion;
* generalized rule-violation correction;
* free-text Claims;
* natural-language interpretation;
* simultaneous throws;
* arbitrary event streams;
* unlimited proof;
* generative adjudication;
* unclassified conduct;
* multiple non-terminal continuation events;
* defender-open-play proof beyond five unresolved Tricks.

Specific-Trick exclusions prohibit partial Trick assignment, subset Claims, and
an associated Settlement contract. The generalized non-jack decision preserves
the existing jack-only open-throw theoretical exclusion. The generalized
correction decision preserves specifically modeled effects but adds no engine
that rewinds arbitrary illegal play, invents a corrected continuation,
interprets unclassified violations, or rewrites an observed Historical record.

These are durable v1 exclusions, not unconditional permanent exclusions and not
post-v1 implementation promises. A later post-v1 audit may reconsider them.
Four-player tables remain the repository's only unconditional exclusion.

## Later implementation sequence

Later Issues must keep the implementation steps explicit and independently
reviewable:

1. Define private structured Claim request, evidence, proof Result, and stable
   unavailable contracts without extending a public surface.
2. Build the dedicated five-Trick party-wide exact proof over the existing legal-
   transition kernel and test Suit, Grand, and all four Null variants.
3. Add terminal adjudication only for a valid proof, with complete unresolved
   Trick/Card/point assignment and preexisting-winner preservation.
4. Integrate existing result, level, overbid, and Final Settlement behavior while
   retaining no-outcome semantics for invalid and unavailable proof.
5. Add the exact Retrospective Historical ending and information-safe output,
   then separately decide any Schema, Public API, CLI, Session, Match Capture,
   example, generated-output, or Provenance exposure.

Until those steps are implemented, tested, and documented, the approved case is
non-executable and Claims and Final Settlement remain partially supported.
