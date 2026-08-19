# Party-wide Claim contracts

## Status and scope

Issue #183 implements private immutable version-1 contracts and exact-state
preparation for the one Claim approved by Settlement Normative Matrix version
`2`:

```text
party_wide_all_remaining_tricks_claim
```

The Claim means that the complete claiming party can force ownership of every
unresolved Trick. It is structured, Retrospective, complete-world, post-game
only, and private. It is not accepted by an existing Runtime input, Historical
ending, Public API, Schema, CLI, Session, Match Capture, example, or generated
scenario.

Issue #183 does not traverse the prepared state. Proof execution, adjudication,
Historical integration, Final Settlement integration, and any public exposure
remain open. Claims and Final Settlement remain partially supported.

## Independent versions

The private contracts use six independent strict integer versions:

```text
PARTY_WIDE_CLAIM_VERSION = 1
PARTY_WIDE_CLAIM_EVIDENCE_VERSION = 1
PARTY_WIDE_CLAIM_EXACT_STATE_CONTEXT_VERSION = 1
PARTY_WIDE_CLAIM_PROOF_REQUEST_VERSION = 1
PARTY_WIDE_CLAIM_PROOF_PREPARATION_VERSION = 1
PARTY_WIDE_CLAIM_PROOF_RESULT_VERSION = 1
```

These versions do not change Package version `0.16.0`, Public API contract
version `1`, Matrix version `2`, Historical version `1`, Search, Dataset,
Provenance, Schema, or other Domain versions.

The exact stable tuples are:

```text
claiming parties: (declarer, defenders)
preparation statuses: (available, unavailable)
proof statuses: (valid, invalid, unavailable)
```

No partial, timeout, Search, or Recommendation status is reused.

## Policy metadata

The private contracts retain these exact non-executable policy labels:

```text
structured_retrospective_complete_world_only
claimant_must_belong_to_claiming_party
complete_deal_and_exact_legal_play_prefix
historical_replay_then_exact_state_validation
claiming_party_existential_opposing_party_universal
at_most_five_unresolved_tricks_including_current
valid_proof_assigns_every_unresolved_trick_to_claiming_party
invalid_proof_creates_no_terminal_outcome
unavailable_proof_creates_no_terminal_outcome
dedicated_exact_claim_proof_without_search_fallback
private_internal_contract_without_public_surface
```

The labels describe scope and invariants. They execute no proof or Settlement
and make no information-set-consistent team-strategy claim.

## Structured Claim

`PartyWideAllRemainingTricksClaimV1` retains only:

* the exact Claim contract version;
* kind `party_wide_all_remaining_tricks_claim`;
* one stable, non-relative `claimant_player_id`;
* claiming party `declarer` or `defenders`.

The claimant identifies the Player who asserts the Claim. The claiming party is
the complete side to which proof quantifiers apply. A Declarer Claim must be
asserted by the Declarer. A Defender Claim may be asserted by either Defender,
but proof covers both Defenders as one claiming party. This does not assert that
either Defender knew the partner's hand or communicated during original play.

The Claim has no text, requested Trick count, specific Trick identity, claimed
level, Recommendation, explanation, timestamp, or generated identity.

## Exact Evidence

`PartyWideClaimEvidenceV1` is builder-controlled private Retrospective evidence.
It validates and retains:

* one Game ID;
* exactly three stable Players in forehand, middlehand, rearhand order;
* exactly ten initial Cards per Player;
* the exact two-card Skat;
* one complete 32-card Deal;
* the exact Declarer and `GameDeclaration`;
* inferred and reconciled Suit/Grand Matadors or valid Null metadata;
* the final bid and inputs needed to validate existing game-value/Overbid
  support, without retaining mutable derived summaries;
* no Discards for Hand or exactly two legal Declarer Discards for non-Hand;
* zero through 30 chronological observed Plays as exact Historical Tricks.

The builder calls `replay_historical_play_prefix()` exactly once. That existing
replay remains authoritative for ownership, play order, Bedienpflicht,
completed-Trick winners and points, the current incomplete Trick, next Player,
remaining hands, played-Card count, and complete Card accounting. No Historical
Game ending is required or created.

The Evidence derives:

* completed Tricks and one optional current incomplete Trick;
* remaining hands and next Player;
* Declarer and Defender completed-Trick counts;
* Declarer and Defender completed-Trick points;
* exact Hand Skat or non-Hand Discards as out-of-play Cards;
* unresolved Card count and points, including Cards already in the current Trick;
* remaining Trick count, including the current incomplete Trick.

Unordered Card collections use existing deck order. Plays and Tricks preserve
chronology. Suit, Grand, Null, Null Hand, Null Ouvert, and Null Hand Ouvert are
supported when the retained declaration and Overbid context are supported.
Missing ownership is never inferred, sampled, aggregated, or completed through
Compatible Worlds.

## Exact State Context

`PartyWideClaimExactStateContextV1` uses the existing deterministic Historical
Player mapping. The Declarer maps to flat `me`; clockwise successors map to
`left` and `right`. It retains both stable/flat maps, the flat claimant, complete
claiming and opposing flat party tuples, and one exact state.

The context calls `build_exact_search_state()` exactly once and reconciles its
Declaration, concrete Declarer, remaining hands, current Trick, next Player,
completed points, completed-Trick counts, out-of-play Cards, unresolved Cards,
unresolved points, and remaining Trick count against Evidence.

The exact-state builder validates the already supplied current-Trick legality.
The context does not enumerate future legal moves, apply state transitions, call
Perfect-Information Minimax or compatible-world Minimax, run bounded Search, or
invoke an exact Claim proof executor.

## Proof Request and preparation

`PartyWideClaimProofRequestV1` retains the reconciled Claim, Evidence, exact
state context, Matrix proof policy
`party_wide_all_remaining_tricks_claim_v1`, maximum `5`, and exact Matrix
quantifiers:

| Party | Quantifier |
| --- | --- |
| claiming party | existential |
| opposing party | universal |

The separate private policy label
`claiming_party_existential_opposing_party_universal` describes those
quantifiers; it does not replace the Matrix proof-policy identifier.

`PartyWideClaimProofPreparationV1` has status `available` or `unavailable`.
Availability requires reconciled exact Evidence, a supported contract, a
concrete turn, one through five unresolved Tricks, and one exact state context.
Zero unresolved Tricks is unavailable. Six through ten unresolved Tricks are
unavailable. A current incomplete Trick counts toward the limit.

Canonical unavailable reasons are:

```text
party_wide_claim_evidence_incomplete
party_wide_claim_evidence_contradictory
party_wide_claim_unsupported_contract
party_wide_claim_unsupported_turn_phase
party_wide_claim_no_unresolved_tricks
party_wide_claim_unresolved_trick_limit_exceeded
party_wide_claim_proof_not_executed
```

Malformed direct Evidence remains a validation error. A focused unavailable
constructor provides the future adapter seam for incomplete or contradictory
external source evidence without silently catching malformed direct inputs.

## Result contracts

`PartyWideClaimProofResultV1` defines `valid`, `invalid`, and `unavailable`
relationships for a later executor. Issue #183 produces no valid or invalid
Result automatically. An available preparation can currently be wrapped only
as unavailable with reason `party_wide_claim_proof_not_executed`.

A valid supplied Result is complete, satisfies the Claim, has no unavailable
reason or counterexample, evaluates at least one terminal state, and retains an
exact `PartyWideClaimProofAssignmentV1`. That assignment gives every unresolved
Trick, unresolved in-play Card, and unresolved Card point to the claiming party.
It is proof-level evidence only: it is not a winner, Game Result, Schneider or
Schwarz award, Overbid calculation, Historical ending, or Settlement.

An invalid supplied Result is complete, does not satisfy the Claim, has no
assignment or unavailable reason, reports a counterexample, and evaluates at
least one terminal state. Invalidity does not assign the Game to the opposing
party and creates no terminal outcome.

An unavailable Result is incomplete, has null Claim satisfaction, one canonical
reason, no assignment, no representative line, no counterexample, and zero
state counters. It creates no terminal outcome or Settlement.

## Diagnostic representative lines

`PartyWideClaimProofMoveV1` retains one stable acting Player, Card, and both
completed-Trick winner fields only when that Move completes a Trick. Supplied
valid and invalid Results retain one chronological legal representative line.

The line is diagnostic. One successful line is not the complete quantified
strategy certificate for existential claiming-party choices against universal
opposing responses. One counterexample line is not a complete negated-strategy
certificate. The later executor must establish the complete quantified Result
independently.

## Search, Runtime, and privacy boundaries

The dedicated proof policy is
`dedicated_exact_claim_proof_without_search_fallback`. Generic Search,
Compatible Worlds, hidden-card inference, Immediate Analysis, Recommendation,
Coaching, legacy remaining-point assignment, and generative adjudication are not
fallbacks and do not establish this Claim.

The Matrix case remains `implementation_required`, has empty
`implementation_modules`, and retains Matrix unavailable reason
`party_wide_claim_not_implemented`. The private contract modules do not make the
case executable. `GameShortening`, Historical endings/events, Game Result, Final
Settlement, Public API, CLI, Schemas, examples, generated scenarios, Search,
Coaching, Provenance, and Package metadata remain unchanged.

Evidence and exact-state serialization is deterministic, defensive, and
private. It intentionally contains the complete Deal and ownership required by
the contract. No existing public value receives those Cards, and no public
redaction or export contract is added.

## Remaining work

Later independently reviewed work must:

1. implement exhaustive party-wide proof traversal and memoization;
2. adjudicate only complete valid proof;
3. integrate a Historical Claim ending;
4. reuse existing result, level, Overbid, and Final Settlement behavior;
5. separately decide any Public API, Schema, CLI, Session, Match Capture,
   example, generated-output, or Provenance exposure.
