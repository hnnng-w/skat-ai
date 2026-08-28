# Historical party-wide Claim

## Scope

Issue #186 implements the one approved bounded v1 Claim as a terminal ending of
the existing `historical_game` Root workflow:

```text
party_wide_all_remaining_tricks_claim
```

The Claim means exactly:

```text
The claiming party can force ownership of every unresolved Trick.
```

This is a structured, Retrospective, post-game, complete-world Claim. It is not
a live input, a flat Position ending, a Search mode, or a Recommendation or
Coaching target. Historical Game and Historical Game End schema versions remain
`1`; the Claim input and output summaries each have their own version `1`.

## Exact input

The Claim uses the existing `historical_game_input` Root branch. The Historical
record must set the matching reason and terminal object:

```json
{
  "historical_game_input": {
    "game_end_reason": "party_wide_all_remaining_tricks_claim",
    "game_end": {
      "schema_version": 1,
      "kind": "party_wide_all_remaining_tricks_claim",
      "claimant_player_id": "player-b",
      "claiming_party": "declarer"
    }
  }
}
```

These are the exact Claim-specific fields inside an otherwise complete existing
Historical Game record; all surrounding required Historical fields still have
to satisfy that schema. The strict Claim object contains exactly:

```text
schema_version
kind
claimant_player_id
claiming_party
```

`schema_version` is `1`, `kind` is the exact Claim kind, and
`claimant_player_id` is one stable non-relative Historical participant ID. IDs
`me`, `left`, and `right` are rejected. `claiming_party` is `declarer` or
`defenders`. A Declarer Claim requires the Declarer as claimant; a Defender
Claim permits either exact Defender as claimant and binds the complete defending
party. The two Defenders are evaluated cooperatively for this complete-world
proof, without asserting that either Defender knew the partner's hand during
original play.

The public input supplies no free text, Proof Result, remaining hands,
assignment, requested Trick count, specific Trick identity, executor counter,
Representative Line, Settlement value, or exact-state object.

## Evidence and bound

The complete Historical record provides all three initial hands, the Skat,
pickup/discard or Hand facts, declaration, exact legal play prefix, completed
Trick ownership, and any current incomplete Trick. Exact replay derives all
three remaining hands. No hidden ownership is inferred, sampled, or completed
through Compatible Worlds.

The Claim requires one through five unresolved Tricks. The current incomplete
Trick, if any, counts once. A terminal Claim therefore has five through nine
completed Tricks and may have zero, one, or two Cards in only the final supplied
Trick. Six unresolved Tricks and a Claim after all ten Tricks are rejected.

Supported contracts are Clubs, Spades, Hearts, Diamonds, Grand, and all four
Null variants, including their already represented Hand, announcement, Schwarz,
and Ouvert combinations. Existing Suit/Grand Matador and supported Overbid
behavior is reused. Null has no Schneider or Schwarz level. Overbid Null remains
rejected through the existing impossible-Null boundary; no replacement contract
is selected automatically.

## Single-pass execution

One accepted Historical Claim follows this pipeline:

```text
one Historical replay
    -> one structured Claim build
    -> one Evidence build from the retained replay
    -> one Proof preparation
    -> at most one exhaustive Proof execution
    -> one adjudication for a valid Proof
    -> one Historical output mapping
```

`replay_historical_play_prefix()` runs exactly once. Evidence construction reuses
that retained replay and does not rebuild or mutate the record. An unavailable
preparation invokes neither the Proof Executor nor adjudication. An available
preparation invokes the bounded exact AND/OR Proof Executor exactly once and
must return `valid` or `invalid`. No stage is rerun for output or Provenance.
There is no retry, fallback, Generic Search, Immediate Analysis,
compatible-world construction, or second Settlement calculation.

The claiming party has existential legal choices and the opposing party has
universal legal choices. A valid Proof assigns every unresolved Trick, in-play
Card, and Card point to the claiming party. Proof satisfaction does not
automatically make that party the Game winner: adjudication preserves a
preexisting decision or derives the winner from the complete assigned outcome
and all existing mandatory-level and Overbid rules.

## Terminal acceptance

Only a valid Proof is accepted as this Historical terminal ending. It produces
one complete result with 120 points, exactly ten final Trick owners, and one
complete Final Settlement.

An invalid Proof rejects the Historical input as semantically invalid. An
unavailable preparation rejects it as unsupported or insufficient for the
asserted ending and retains the canonical unavailable reason. Neither path
produces a successful `unavailable` Historical summary, opposing-party
assignment, winner, Settlement, alternate ending, or legacy remaining-point
fallback. A caller that needs to retain an unsuccessful Claim attempt must record
continued observed play or another supported terminal ending.

The preparation reasons that reject a terminal Historical Claim are:

```text
party_wide_claim_no_unresolved_tricks
party_wide_claim_unresolved_trick_limit_exceeded
party_wide_claim_unsupported_contract
party_wide_claim_unsupported_turn_phase
party_wide_claim_evidence_incomplete
party_wide_claim_evidence_contradictory
```

For a valid Proof, `adjudicate_party_wide_claim_proof_v1()` runs exactly once.
The Historical adapter reuses its completed point accounting, Trick assignment,
winner, Schneider/Schwarz result, Game Value, Overbid summary, Game Result, and
Final Settlement. The adjudicator alone creates the private normal-completion
projection and calls the existing Final Settlement builder once.

## Incomplete Trick and continuation

A Claim may occur at a completed-Trick boundary or after one or two Cards in the
current final Trick. Current-Trick Cards stay unresolved, are assigned exactly
once, and are not repeated in the Representative Line. The current Trick is one
of the one through five remaining Tricks, and final ownership still contains
exactly ten Tricks.

Exactly one existing non-terminal event may precede the terminal Claim:

```text
declarer_card_exposure_continuation
defender_open_play_continuation
```

Existing continuation validation and exact public-hand state remain
authoritative. The Claim is evaluated at the final recorded play prefix. The
continuation performs no Claim proof or Settlement. Its event summary uses the
Claim as `final_game_end_reason` and
`final_outcome_source = subsequent_terminal_shortening`. Multiple continuation
events remain `not_supported_v1`.

## Public result

The Root result follows the existing shortened-Historical structure and has
`status = complete`. It retains the canonical record, observed derived Tricks,
optional `incomplete_current_trick`, exact observed and assigned point
accounting, final winner and levels, Game Value, Overbid, Game Result, and Final
Settlement. The strict `historical_game_end_summary` identifies the Matrix case,
claimant, claiming party, Declarer and Defenders, play boundary, incomplete-Trick
state, remaining-Trick count, proof policy and quantifiers, exact diagnostic
Proof summary, adjudication summary, and applied Settlement.

The public exact-Proof summary contains only:

```text
executor_version
execution_method
status
proof_complete
claim_satisfied
evaluated_state_count
memoized_state_count
terminal_state_count
counterexample_found
assignment
representative_line
representative_line_scope
```

Accepted output always reports a complete `valid` Proof and
`representative_line_scope = diagnostic_decisive_branch_only`. The chronological
line uses stable Player IDs. It is one canonical decisive branch for diagnostics,
not the complete quantified strategy certificate, full AND/OR tree, or every
universal branch.

The public adjudication summary reports the adjudicated status and reason,
decision state before the Claim, outcome source and winner basis, final winner,
point and Trick totals, assigned remaining points, achieved-level status and
application, and supported Overbid-required level/value application. It is a
bounded projection of the private adjudication Result, not a private Settlement
projection.

Its strict fields are:

```text
adjudication_result_version
adjudication_facts_version
status
reason
decision_state_before_claim
outcome_source
winner_basis
adjudicated_winner
final_declarer_points
final_defender_points
final_declarer_tricks
final_defender_tricks
remaining_points_recipient
remaining_points_assigned
achieved_schneider_status
achieved_schwarz_status
achieved_schneider_applied
achieved_schwarz_applied
overbid_required_level
overbid_required_value_applied
```

## Review, Coaching, Dataset, lists, and statistics

Historical Decision Snapshots, Immediate Review, Historical Search Review, and
Replay Coaching use one decision per actually played Card. There is no Snapshot,
review decision, Coaching decision, or target for the terminal Claim event.
Pre-play Decision State never receives future Claim Evidence, the exact Proof
state, or final private ownership. Replay Coaching outcome context may use the
adjudicated final Result and Settlement only after Coaching evidence is built.

Training Dataset version `1` accepts valid Claim-ending records and preserves
the canonical Historical source. It emits samples only for actual plays, keeps
`actual_card_played` as the only target, and adds no terminal Claim sample.
Zero-decision behavior, Dataset versions, sample identities, and partition
behavior are unchanged.

Fixed-three-player Historical Lists, list aggregation, independent-list
comparison, historical Opponent Statistics aggregation, and rolling evaluation
accept valid Claim-ending Games where their existing requirements are met. They
reuse the existing Settlement and performance values. There is no Claim-specific
score, rating, list position, statistics signal, or Passed Deal behavior.

## Provenance

Complete internal and opt-in public field Provenance covers every new Root
Result field. The claimant and claiming party originate from exact Historical
input. Proof status, assignment, counters, winner, levels, and Settlement have
exact derived origins. The Representative Line is post-game-only. Provenance is
built from the retained request and result and executes no replay, Proof,
adjudication, or Settlement stage again.

Public redaction removes engine-private Evidence and exact-state references
while retaining complete coverage. Omitting Provenance leaves the non-Provenance
result unchanged.

## CLI and public surface

The existing `historical_game` Root workflow accepts the Claim through installed,
module, and Legacy CLI forms. No eighth Root workflow, Public API export, CLI
option, or Console Script is added. Existing public error translation and
`--quiet` behavior are unchanged.

For example:

```powershell
skatmind --input examples/historical_party_wide_claim.json
python -m skatmind --input examples/historical_party_wide_claim.json
python main.py --input examples/historical_party_wide_claim.json
```

Concise output identifies the Claim kind, claimant, claiming party, valid exact
Proof and evaluated-state count, adjudicated winner, and final Settlement score.
It does not print complete hands, private exact state, the Proof tree, or the full
Representative Line.

## Privacy and unsupported entry paths

The public record necessarily preserves the caller-supplied complete Historical
source. Outside that record, output does not duplicate complete remaining hands,
the complete Deal, private `ExactSearchState`, memo table, universal-branch tree,
hidden-world data, or Search value. Private Evidence and Proof state remain
engine-private.

The Claim is deliberately absent from flat `game_shortening` and all Position
input. Those contracts lack complete opponent ownership and cannot satisfy the
complete-world Retrospective evidence boundary. Live Claim input, Session Claim
Commands or Historical export, Match Capture forms or Workspace fields,
automatic Claim capture, and Learning Corpus Claim sources remain open. Session,
Match Capture, and Corpus callers require no migration when the new ending is
omitted.

Broader Claim boundaries, including specific future-Trick Claims, remain
`not_supported_v1`. Complete official Claim or Settlement coverage is not
claimed. Issue #186 completes only the approved bounded v1 Claim and Final
Settlement runtime slice. Issues #187 through #193 subsequently add the bounded
Information-set Search contracts, executor, selected workflow integrations,
Replay Coaching, and repository-local performance evidence without broadening
the Claim boundary.

## Compatibility baseline

The Issue #186 point-in-time baseline is Settlement Normative Matrix version `3`
with the same 61 cases, 65 authoritative Schemas, 65 Packaged Schema Resources,
six Session examples, and 88 generated-output scenarios. The published `v0.17.0`
baseline after Issues #189, #192, #194, and #198 has 71 authoritative and
packaged Schemas, six Session examples, and 98 scenarios. Issue #199 changes only
post-publication documentation. The current Package
version is `0.17.0`; Python `>=3.13`, Public API contract version `1`, seven Root
workflows, and one `skat-ai = skat_ai.cli:main` Console Script are unchanged. The published
`v0.17.0` Release is at commit `8187fbe`; the `v0.16.0` baseline remains the
historical 63-Schema, 85-scenario Release at commit `91b1360`.

See [Party-wide Claim contracts](party_wide_claim_contracts.md), [Party-wide
Claim proof executor](party_wide_claim_proof_executor.md), [Party-wide Claim
adjudication](party_wide_claim_adjudication.md), [Settlement normative
matrix](settlement_normative_matrix.md), and [Claim and Settlement v1
boundaries](claim_and_settlement_v1_boundaries.md).
