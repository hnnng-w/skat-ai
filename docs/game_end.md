# Game-end handling

This document explains normal completion, the structured concealed or verbal
declarer concession, legacy claim/concession assignment, and impossible Null.

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
favorable Suit or Grand replacement for valuation. `skat-ai` records that
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
* either structured concession requires incomplete play and a calculable declaration.
* structured defender concession requires distinct concrete declarer and conceding defender identities.
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

Both structured adjudication and legacy assignment can decide the final winner
before settlement is calculated, but only the legacy path changes card points.

For example:

1. `game_result_summary` may be incomplete.
2. `adjusted_game_result_summary` assigns remaining points.
3. `adjusted_game_result_summary.winner` becomes complete.
4. `final_settlement_summary` uses the adjusted winner and game value.

## Current limitations

* Legacy claims and concessions still assign remaining points.
* Structured support covers bounded declarer and defender concessions.
* Continued play, exposed cards, defender open play, and open throwing are unsupported.
* Historical-game shortening and solver-backed claim proof are unsupported.
* No game-shortening path simulates hypothetical continuation.
