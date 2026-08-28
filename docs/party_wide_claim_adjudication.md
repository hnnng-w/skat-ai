# Party-wide Claim adjudication

## Status and scope

Issue #185 adds private immutable adjudication for one existing
`PartyWideClaimProofResultV1`. It completes the private sequence:

```text
structured Claim and exact Evidence
    -> exact Proof Request and preparation
    -> bounded exhaustive Proof Result
    -> private Claim adjudication
    -> existing Final Settlement composition
```

This layer does not execute proof. It consumes one retained Proof Result and
does not replay Historical play, rebuild the exact state, traverse future play,
run Search, or call a Recommendation workflow.

Issue #186 calls this layer exactly once after one valid Proof in the focused
Historical adapter. The existing `historical_game` Root workflow then reuses its
complete Result and Settlement in strict public output. The Claim remains absent
from flat Position and `GameShortening`, Session, Match Capture, and Learning
Corpus entry. Settlement Normative Matrix version `3` retains 61 cases and marks
the approved bounded Claim `supported_as_is`.

## Versions and results

The independent private versions are:

```text
PARTY_WIDE_CLAIM_ADJUDICATION_FACTS_VERSION = 1
PARTY_WIDE_CLAIM_ADJUDICATION_RESULT_VERSION = 1
```

`PartyWideClaimAdjudicationResultV1` has two statuses:

| Status | Reason | Outcome |
| --- | --- | --- |
| `adjudicated` | `valid_proof` | Complete Facts, Game value, Overbid, private Game Result, and Final Settlement. |
| `no_outcome` | `invalid_proof` | Retained invalid Proof Result and no downstream value. |
| `no_outcome` | `unavailable_proof` | Retained unavailable Proof Result and no downstream value. |

An unavailable Result includes both an unavailable preparation and an available
preparation deliberately retained as `party_wide_claim_proof_not_executed`.
Adjudication never invokes the Proof Executor automatically.

## Strict reconciliation

The entry point is:

```python
adjudicate_party_wide_claim_proof_v1(proof_result)
```

It requires one exact `PartyWideClaimProofResultV1`. Before adjudicating a valid
Result, it reconciles:

* the Result version and status relationships;
* preparation, Claim, Evidence, Proof Request, and Exact State Context;
* canonical Deal partitions, Declaration and Matadors, legal retained Card
  ownership, and remaining-hand order;
* Claiming Player and party;
* valid assignment recipient and unresolved Trick, Card, and point totals;
* Representative Line legality and completeness through the existing Result
  constructor.

Forged immutable values raise `SkatMindInvariantError`. Reconciliation does not
replay the Historical prefix, rebuild `ExactSearchState`, execute proof, or use
the Representative Line as assignment authority.

## No-outcome behavior

Invalid and unavailable Proof Results are normal no-outcome values. They retain
the exact Proof Result but contain null:

```text
facts
game_value_summary
overbid_summary
game_result_summary
final_settlement_summary
```

No winner, assignment, opposing-party fallback, legacy remaining-point
assignment, or Settlement is created. No Game-value, Overbid, Game Result, or
Final Settlement builder runs on these paths.

These remain valid private no-outcome contracts. The Issue #186 Historical
terminal adapter does not serialize them as successful output: unavailable
preparation is rejected before execution, and an invalid Proof rejects the
asserted terminal record before adjudication.

## Point accounting

For a valid proof, observed points are:

```text
out_of_play_points = points in Evidence.out_of_play_cards

observed_declarer_points =
    Evidence.declarer_trick_points + out_of_play_points

observed_defender_points =
    Evidence.defender_trick_points
```

Hand games use the original Skat as out-of-play Cards. Non-Hand games use the
exact Discards. These two Cards always belong to the Declarer's point account.
Cards already in an incomplete current Trick remain unresolved and are not
included in observed completed-Trick points.

The valid proof assignment gives every unresolved in-play card point to the
claiming party. No card point is inferred, sampled, or counted twice. Final
Declarer and Defender points total exactly 120.

## Trick ownership

Observed completed-Trick winner parties are retained in exact chronology. The
claiming party is then appended once for each unresolved Trick in the proof
assignment.

The current incomplete Trick is one unresolved Trick, whether it contains one or
two Cards. Its Cards and points are assigned once, and its ownership is appended
once. Final ownership contains exactly ten party values and reconciles with final
Declarer and Defender Trick counts.

The proof assignment is authoritative for unresolved ownership. The diagnostic
Representative Line is not replayed to choose or recalculate future winners.

## Pre-Claim decision

The adjudicator builds the existing Game-value and Overbid summaries once. It
also builds one observed pre-Claim Game Result from observed points and calls
`determine_decision_state_before_game_end()` once with only observed completed-
Trick ownership.

The resulting state is one of:

```text
undecided
declarer_already_won
defenders_already_won
```

Assigned future points and Tricks do not enter this decision. An already decided
winner remains binding even when the opposing party validly proves every
remaining Trick.

## Completed winner

A preexisting winner uses outcome source and winner basis
`preexisting_game_decision`.

An undecided pre-Claim state uses:

```text
outcome_source = exact_party_wide_claim_adjudication
winner_basis = completed_claim_assignment
```

Suit and Grand derive the candidate winner from complete final points. Null
derives the candidate winner from exact ten-Trick ownership. Existing declared
and supported Overbid-required Schneider or Schwarz requirements remain
mandatory. A failed requirement produces the existing loss behavior.

Proof satisfaction does not make the claiming party the Game winner. A Defender
Claim can preserve an already established Declarer win, and a Declarer Claim can
preserve an already established Defender win.

## Schneider, Schwarz, and Null

Suit and Grand derive achieved Schneider from final points through the existing
point helper. They derive achieved Schwarz from exact final Trick ownership
through the existing completed-Trick helper. Zero card points do not establish
Schwarz when the zero-point party retained a completed Trick.

Declared Schneider, Schwarz, and Ouvert remain in the existing Game-value model.
Supported Overbid-required levels use the existing required-level helpers.
Optional achieved levels retain the existing application and Overbid suppression
behavior and are not applied twice.

All four Null variants use fixed existing values and exact completed-Trick winner
semantics. Their adjudication Facts use:

```text
achieved_schneider_status = not_applicable
achieved_schwarz_status = not_applicable
achieved_schneider_applied = false
achieved_schwarz_applied = false
```

No Claim-specific Null level or replacement contract exists.

## Private Game Result

One valid proof creates a complete private `game_result_summary`. It retains the
exact final points, winner, pre-Claim decision, Claim and proof facts, assignment,
level application, and Overbid-required-value application. Its private end
reason and kind are:

```text
party_wide_all_remaining_tricks_claim
```

The Result uses `final_decided` when preserving a preexisting winner and
`final_adjudicated` otherwise. It never marks a mandatory level as automatically
awarded. The completed assignment either satisfies or fails the existing
requirement.

This private kind is now adapted into the Historical ending union and strict
Historical Claim input/output Schemas. It remains absent from `GameShortening`
and flat Position validation; the private Result contract itself is unchanged.

## Settlement composition

The adjudicator does not duplicate settlement scoring. It creates one private,
ephemeral projection from the completed Claim Game Result and changes only:

```text
game_end_reason = normal_completion
game_end_kind = normal_completion
```

It supplies the exact ten final `winner_role` values and calls
`build_final_settlement_summary()` exactly once. The projection is not returned,
persisted, or exposed. The returned private Claim Game Result keeps its Claim end
kind.

The resulting Final Settlement must be complete, have no missing inputs, and
reconcile its winner, Game value, bid, Overbid status, required value, and score
with the retained private result. Existing win/loss scoring is used unchanged.
There is no Claim bonus, penalty, rating, list score, or opposing-party fallback.

## Determinism and privacy

Facts and Result values are frozen, slotted, builder-controlled, recursively
immutable, and defensively serialized. Equal Proof Results produce equal
adjudication Results. No path, timestamp, generated ID, environment value,
random value, process value, logging, file I/O, network I/O, or background work
enters adjudication.

The private Result retains the private Proof Result and therefore may indirectly
contain the complete Deal. Issue #186 exports only a strict bounded Historical
summary and redacts private Evidence, exact state, memo tables, and the complete
proof tree.

## Integration boundary

Issue #186 completes the approved bounded v1 Claim and Final Settlement runtime
slice through the Historical workflow, including public diagnostic output,
Provenance, CLI/example/generated-output coverage, Review/Coaching, Dataset,
list, and statistics compatibility. It does not change this adjudicator or build
Settlement a second time.

Flat `GameShortening`, live Position, Session, Match Capture, and Learning Corpus
Claim entry remain absent. Broader Claim boundaries remain `not_supported_v1`.
Complete official-rule, Claim, concession, or Settlement coverage is not
claimed. See [Historical party-wide Claim](historical_party_wide_claim.md).
