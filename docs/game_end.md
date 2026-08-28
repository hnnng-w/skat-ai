# Game-end handling

This document explains normal completion, structured concessions and exposure,
bounded defender open play, open-card throwing, the Historical-only party-wide
Claim, continuation chains, legacy claim/concession assignment, and impossible
Null.

## Purpose

Game-end handling separates the raw known card-point state from the adjusted final result used for settlement.

The raw card-point result is stored in:

```text
game_result_summary
```

The game-end-adjusted result is stored in:

```text
adjusted_game_result_summary
```

`final_settlement_summary` uses `adjusted_game_result_summary`, not the raw `game_result_summary`.

## Legacy game_end_reason values

| Value                                 | Meaning                                                       |
| ------------------------------------- | ------------------------------------------------------------- |
| `not_ended`                           | The game is still in progress.                                |
| `normal_completion`                   | The game ended normally and all 120 card points are assigned. |
| `declarer_claimed_remaining_tricks`   | The declarer claimed the remaining tricks.                    |
| `declarer_conceded_remaining_tricks`  | Simplified legacy assignment after declarer concession.       |
| `defenders_conceded_remaining_tricks` | The defenders conceded the remaining tricks.                  |
| `impossible_null_declaration`          | An impossible Null declaration ended the game immediately.     |

## Analysis mode

Ended game reasons are post-game information.

Therefore, these values require:

```json
{
  "analysis_mode": "post_game_review"
}
```

This applies to:

* `normal_completion`
* `declarer_claimed_remaining_tricks`
* `declarer_conceded_remaining_tricks`
* `defenders_conceded_remaining_tricks`
* `impossible_null_declaration`

Live decision analysis should use:

```json
{
  "analysis_mode": "live_decision",
  "game_end_reason": "not_ended"
}
```

## Legacy remaining-point assignment

Legacy early-end reasons assign remaining card points according to
`game_end_reason`. This behavior remains backward compatible.

| game_end_reason                       | Remaining points go to |
| ------------------------------------- | ---------------------- |
| `declarer_claimed_remaining_tricks`   | declarer               |
| `defenders_conceded_remaining_tricks` | declarer               |
| `declarer_conceded_remaining_tricks`  | defenders              |
| `not_ended`                           | no assignment          |
| `normal_completion`                   | no assignment          |
| `impossible_null_declaration`          | no assignment          |

Example:

```json
{
  "game_result_summary": {
    "declarer_points": 46,
    "defender_points": 45,
    "points_remaining": 29,
    "is_complete": false,
    "winner": "undecided"
  },
  "adjusted_game_result_summary": {
    "declarer_points": 75,
    "defender_points": 45,
    "points_remaining": 0,
    "is_complete": true,
    "winner": "declarer",
    "game_end_reason": "declarer_claimed_remaining_tricks",
    "remaining_points_recipient": "declarer",
    "remaining_points_assigned": 29
  }
}
```

## Normal completion

`normal_completion` means the game ended by playing all tricks.

For Suit and Grand, validation expects all 120 card points to be assigned. For
Null, the completed result can instead be based on a reliable ten-trick history
with completed-trick ownership.

For Suit and Grand settlement, a normally completed ten-trick history can also
prove Schwarz through `completed_tricks[].winner_role`: if the losing side took
zero tricks, achieved Schwarz can affect `effective_game_value`. Card points
alone do not prove Schwarz.

For point-based Suit and Grand completion, validation expects:

```text
points_remaining = 0
```

If a Suit or Grand game has fewer than 120 assigned card points, it should not use `normal_completion`.

## Structured declarer concession

`game_shortening` schema version 1 represents an accepted concealed or verbal
declarer concession under ISkO 4.4.1 or 4.4.2. Nine or ten declarer hand cards
require no defender consent and record count zero. One through eight cards
require consent from one or two defenders.

Reliable local hand or opponent hand-size evidence must match the supplied
count. The output reports `confirmed` when it can reconcile that evidence and
`not_verifiable` when the generic position lacks a concrete declarer.

The adjusted result is a final adjudicated defender win. Observed point totals
and unplayed points remain unchanged; no side receives remaining points. Final
settlement doubles the declared or supported overbid-required value as a loss.
Declared levels and matadors remain effective, but unfinished play never creates
an achieved Schneider or Schwarz level.

See [Declarer concessions](declarer_concessions.md) for the full contract.

### Historical declarer concession

The historical workflow has a separate versioned `game_end` event with stable
player IDs. It replays an empty, complete-trick, or final partial-trick prefix
from the complete deal, confirms the declarer hand count, applies the same
consent matrix and adjudicator, and preserves observed plus unresolved points.
Snapshots, review, external-profile review, training conversion, and partition
audits follow the exact played-card count. Statistics aggregation and rolling
evaluation support normal completion and all six historical shortened kinds. Statistics count
the completed record once; rolling targets evaluate only actual cards. See
[Historical declarer concessions](historical_declarer_concessions.md).

### Historical defender concession

Historical version 1 also accepts `game_end_reason: "defender_concession"` with
one exact stable conceding defender ID and either `explicit_verbal` or
`adjudicated_unambiguous_conduct`. One defender binds the complete defending
party without partner consent. Exact prefix replay, unresolved-point privacy,
flat adjudication parity, variable decision artifacts, statistics, and rolling
evaluation are documented in
[Historical defender concessions](historical_defender_concessions.md).

### Historical declarer card exposure

Historical version 1 accepts `game_end_reason: "declarer_card_exposure"` only
for a terminal unanimously accepted event. Exact replay must confirm every
remaining declarer card, both stable defenders must accept exactly once, and an
optional shown-to ID must identify a defender. The shared flat adjudicator
preserves preexisting decisions and applies accepted claims, mandatory levels,
supported overbid requirements, and Suit, Grand, and Null settlement without
simulating cards or assigning unresolved points. See
[Historical declarer card exposure](historical_declarer_card_exposure.md).

### Historical defender open play

Historical version 1 accepts `game_end_reason: "defender_open_play"` only for
terminal adjudication after at least five completed tricks. Exact replay derives
all remaining hands; the exposing stable defender's supplied cards must match
that complete current hand. The existing bounded exact solver and adjudicator
retain existential exposing-defender and universal declarer/partner quantifiers,
assign all unresolved tricks and points, preserve prior decisions, and settle
Suit, Grand, and all Null variants. Stable-ID proof lines redact both private
hands. See [Historical defender open play](historical_defender_open_play.md).

### Historical open card throw

Historical version 1 accepts `game_end_reason: "open_card_throw"` with one exact
stable participant and that player's complete reconstructed current hand. Exact
prefix replay supports zero through 29 plays. The existing 4.4.6 adjudicator
assigns all unresolved tricks and points to the opposing party, preserves any
preexisting decision, applies the jack-only Schwarz exclusion, and reuses normal
declaration, overbid, Null, and settlement behavior. It does not create a
`game_events` member or future-play proof. See
[Historical open card throw](historical_open_card_throw.md).

### Historical continuation before terminal shortening

Version 1 permits at most one non-terminal
`declarer_card_exposure_continuation` or
`defender_open_play_continuation` in `game_events[0]`, followed by normal
completion or one of the six supported terminal reasons in top-level
`game_end_reason` and `game_end`. The terminal object is never copied into
`game_events`, and both schema versions remain `1`.

For shortening, chronology requires the continuation boundary to be no later
than the final recorded play count, which remains below 30. Equality is valid, so
the terminal action can occur before another card is played. Exact replay
validates any partial final trick and removes public cards only when their owner
actually plays them. The surviving public hand must exactly match the owner's
reconstructed terminal hand.

The continuation remains non-adjudicating. Its summary keeps proof, game-end,
and settlement flags false, while the separate reason-specific terminal summary
comes from the existing terminal adjudicator. Earlier snapshots, Immediate and
Search review, training features, statistics decisions, and rolling evaluation
never receive future terminal evidence or final hidden hands.

## Structured defender concession

The second version-1 `game_shortening` variant records one concrete defender's
accepted concession under ISkO 4.4.3. The conceding player must differ from the
concrete declarer. Joint liability binds the complete defending party, so the
other defender does not need to consent and has no veto.

Before ending play, the adjudicator derives `undecided`,
`declarer_already_won`, or `defenders_already_won`. Suit and Grand use observed
61/60 point decisions plus failed announced and supported overbid-required
Schneider/Schwarz conditions. Null uses reliable completed declarer-trick
ownership. An undecided contract is granted to the declarer; an existing winner
is preserved, including a declarer loss.

Observed and unplayed points remain separate. No current trick is completed, no
remaining points are assigned, and no artificial 120-point result is created.
Settlement retains declared and still-possible mandatory values without adding
optional levels from hypothetical future play. See
[Defender concessions](defender_concessions.md).

## Accepted declarer card exposure

The third version-1 union member records all remaining declarer cards laid open
or shown to one defender under ISkO 4.4.4. Showing one defender triggers the
event, but both concrete defenders must independently accept for this final
workflow. One defender cannot bind the other.

Reliable exposed-card contradictions are rejected. Exact remaining-hand evidence
produces `confirmed`; incomplete evidence produces `not_verifiable` without card
inference. The adjudicator shares the bounded preexisting decision logic used by
defender concession. It grants an undecided announced contract, preserves an
existing winner, and never reverses a preexisting declarer loss.

Suit and Grand may request simple, Schneider, or Schwarz settlement. Declared
mandatory levels remain effective, and supported overbid-required levels must be
covered by the declaration or accepted claim. Null requires simple and uses its
fixed value. Accepted levels are not labeled as achieved during play. Observed
and unplayed points remain separate, with no recipient or artificial 120-point
total. See [Accepted declarer card exposure](declarer_card_exposure.md).

## Rejected exposure continuation

At least one `continue` response prevents the ISkO 4.4.4 exposure from ending
the game. This uses separate `game_continuation`, keeps the declarer's exact
current hand public, and continues ordinary play. It does not assign points,
select a winner, accept the requested level, or invoke settlement. Actual later
play determines achieved levels and the final result. Reactionary defender
cards remain hidden. See
[Declarer card exposure continuation](declarer_card_exposure_continuation.md).

## Open card throw

The fifth version-1 `game_shortening` member applies ISkO 4.4.6 equally to the
declarer and defending parties. One concrete player throws that player's complete
current hand openly. One defender binds the full defending party without partner
approval.

The throwing party keeps only completed tricks and observed points. Every
unresolved trick and outstanding point goes to the opposing party. A one-card or
two-card current trick is unresolved and included exactly once. Completed plus
assigned tricks total ten; Suit and Grand observed plus assigned points total
120. No card order or individual future winner is simulated.

The pre-throw decision is recorded separately. A preexisting result remains
binding. For an undecided game, a declarer throw normally gives the game to the
defenders and a defender throw normally gives it to the declarer. Schneider
comes from the final rule-assigned point state. Schwarz additionally requires
zero losing-party tricks and no jack-only theoretical exclusion. Reliable losing-
party ownership of `CJ` or all `SJ`, `HJ`, and `DJ` excludes Schwarz; unknown
ownership and skat jacks do not establish exclusion.

Declarations, matadors, Hand, announcements, ouvert, and supported overbid
requirements remain effective. Rule levels are not achieved normal-play levels.
All Null variants use completed and assigned trick ownership and fixed values.
See [Open card throw](open_card_throw.md).

## Defender open play continuation

Under ISkO 4.4.5 and 4.1.6, a completed continuation request uses separate
`game_continuation`. The exposing defender takes the cards back, but the complete
current returned hand stays known to all players and constrains Immediate,
supported Multi-Step, Policy Comparison, and flat review.

The original rest-trick claim is not adjudicated. The exact solver and its
five-trick bound are not used; no rest tricks, points, decided winner, mandatory
awarded level, settlement basis, or final settlement are produced. The original
declaration remains binding, requesting continuation adds no optional Schneider
or Schwarz obligation, and actual later play determines achieved levels and the
result. See [Defender open play continuation](defender_open_play_continuation.md).

## Historical party-wide Claim

Issue #186 implements `party_wide_all_remaining_tricks_claim` only through the
existing Historical Game workflow. Its strict event contains one stable claimant
Player ID and claiming party `declarer` or `defenders`. It is post-game and
Retrospective only, requires the complete Deal, exact play prefix, and optional
current incomplete Trick state, and preserves the Matrix five-unresolved-Trick
bound. The claiming party has existential legal choices and the opposing party
has universal legal responses.

Issue #184 executes an available preparation through the retained strict
`ExactSearchState`, canonical legal Cards, immutable exact transitions, party-
level AND/OR quantifiers, and invocation-local exact-state memoization. It returns
exactly one existing complete `valid` or `invalid` proof Result; an unavailable
preparation passes through without execution. A valid proof has an exact proof-
level assignment, while an invalid proof has no assignment and stops its
diagnostic line at the first opposing-party Trick.

The Historical path performs one replay, builds Evidence from that retained
replay, prepares and executes proof once when available, and adjudicates exactly
one valid Result. A valid proof receives complete unresolved point and Trick
assignment, preexisting-winner preservation, completed Suit/Grand/Null semantics,
and one existing Final Settlement build through the private adjudicator. Invalid
or unavailable proof rejects the asserted terminal record with no opposing-party
assignment, Settlement, alternate ending, or Generic Search fallback.

The public Historical summary contains only a diagnostic decisive line,
assignment and proof counters, and a bounded adjudication summary. Exact
remaining hands, exact state, memo tables, and the complete AND/OR tree remain
private. The Claim remains absent from flat `game_shortening`, live Position,
Session, Match Capture, and Corpus entry. See [Historical party-wide
Claim](historical_party_wide_claim.md), [Party-wide Claim contracts](party_wide_claim_contracts.md), [Party-wide Claim
proof executor](party_wide_claim_proof_executor.md), [Party-wide Claim
adjudication](party_wide_claim_adjudication.md), and [Claim and Settlement v1
boundaries](claim_and_settlement_v1_boundaries.md).

## Legacy claims and concessions

The three legacy reasons are modeled by assigning all remaining card points to
the appropriate side. They are not reinterpreted as structured adjudication.

Examples:

| Scenario                           | game_end_reason                       | Result                            |
| ---------------------------------- | ------------------------------------- | --------------------------------- |
| Declarer claims remaining tricks   | `declarer_claimed_remaining_tricks`   | Remaining points go to declarer.  |
| Defenders concede remaining tricks | `defenders_conceded_remaining_tricks` | Remaining points go to declarer.  |
| Declarer concedes remaining tricks | `declarer_conceded_remaining_tricks`  | Remaining points go to defenders. |

This is intentionally a scoring adjustment, not a full simulation of the remaining tricks.

Because claim and concession handling assigns remaining card points without
recording the actual remaining trick ownership, claims and concessions do not
establish Schwarz for settlement in the current implementation slice.

## Impossible Null declaration

ISkO 3.6.2 and the International Skat Court decision collection section 3.6.2,
inquiries 1-3, establish an immediate lost Suit or Grand game when the announced
Null value cannot cover the final bid. The declarer may select an eligible
favorable Suit or Grand replacement for valuation. `skatmind` records that
external selection and does not optimize across unknown alternatives.

The reason requires a post-game Null input, a bid above the original fixed Null
variant value, and no card play or assigned points. The adjusted result is final
with `winner: "defenders"`, zero assigned remaining points, and Schneider and
Schwarz statuses marked `not_applicable`. Replacement metadata is optional;
omitting it leaves only final settlement incomplete.

## Validation rules

The engine validates `game_end_reason` against the known card-point state.

Rules:

* `not_ended` requires remaining card points.
* `normal_completion` requires zero remaining card points.
* legacy claim/concession reasons require remaining card points.
* structured declarer concession requires `1..10` hand cards and the exact consent matrix.
* every structured shortening requires incomplete play and a calculable declaration.
* structured defender concession requires distinct concrete declarer and conceding defender identities.
* declarer card exposure requires all remaining cards and exactly both concrete defender acceptances.
* exposure continuation requires exactly both defender responses, at least one continuation request, an exact nonempty current public declarer hand, and neutral `not_ended` state.
* defender-open-play continuation requires a concrete exposing defender, the exact nonempty returned current hand, `request_continued_play`, reliable hand-size and turn reconciliation, and neutral `not_ended` state.
* historical defender-open-play continuation is not a `game_end_reason`; it is a timed non-terminal `game_events` member before normal completion or one supported terminal shortening.
* historical declarer-card-exposure continuation is likewise a timed non-terminal `game_events` member with both stable defender responses and the exact public declarer hand.
* a shortened chain requires the continuation boundary to be no later than the final recorded play, permits equality, and reconciles the shrinking public hand with its owner's exact terminal hand.
* a Historical party-wide Claim requires a matching strict Claim object, one through five unresolved Tricks, complete-world Evidence, and one valid exact Proof; invalid or unavailable proof rejects the record.
* open card throw requires one concrete throwing player, the complete nonempty current thrown hand, deterministic hand-size and turn reconciliation, and neutral `not_ended` state.
* structured game shortening cannot coexist with an active legacy end reason,
  impossible Null, list workflows, or historical workflows.
* unknown `game_end_reason` values are rejected.
* remaining card points cannot be negative.
* ended game reasons are rejected in `live_decision`.
* `impossible_null_declaration` requires an overbid Null declaration before any
  card play and rejects assigned card points.

This prevents inconsistent inputs such as:

* a normally completed game with only 86 assigned card points
* an unfinished game with all 120 card points already assigned
* claim/concession when no card points remain
* ended game metadata in live decision mode

## Relationship to settlement

`final_settlement_summary` uses the adjusted result.

Structured adjudication and legacy assignment can decide the final winner
before settlement is calculated. Legacy endings, defender open play, and open
card throw can change adjusted point accounting. Open throw records observed and
assigned party-level tricks and points without invoking exact proof.

For example:

1. `game_result_summary` may be incomplete.
2. `adjusted_game_result_summary` assigns remaining points.
3. `adjusted_game_result_summary.winner` becomes complete.
4. `final_settlement_summary` uses the adjusted winner and game value.

## Current limitations

* Legacy claims and concessions still assign remaining points.
* Structured support covers bounded declarer and defender concessions, unanimously accepted declarer card exposure, bounded exact defender open play, bounded open card throw, and the Historical-only bounded party-wide Claim.
* Flat continued declarer exposure and bounded defender-open-play continuation are separate ongoing workflows.
* Multiple continuation events, arbitrary event streams, simultaneous throws,
  specific future-Trick Claims, free-text or natural-language Claims, unlimited
  exact solving, generalized correction, generalized non-jack exclusion, and
  defender-open-play proof beyond five unresolved Tricks are
  `not_supported_v1`.
* Defender open play proves a bounded final adjudication; it does not simulate or create continued play.
* The approved party-wide Claim and Final Settlement runtime slice is complete
  only through Historical Game input. Flat `game_shortening`, live Position,
  Session, Match Capture, and Corpus Claim entry remain open.
* Claims and Final Settlement remain partially supported beyond the approved
  bounded cases. This document does not claim complete official-rule, claim,
  concession, or settlement coverage; see the
  [Settlement Normative Matrix](settlement_normative_matrix.md) and
  [Claim and Settlement v1 boundaries](claim_and_settlement_v1_boundaries.md).
