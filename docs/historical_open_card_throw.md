# Historical open card throw

Version-1 historical games support one terminal open-card throw under ISkO
4.4.6. The event extends the historical `game_end` union; it is not a
`game_events` continuation. One supported non-terminal continuation may precede
it, but another terminal event cannot coexist with it.

## Event contract

```json
{
  "schema_version": 1,
  "kind": "open_card_throw",
  "throwing_player_id": "player-a",
  "thrown_cards": ["C7", "S10"],
  "statement_classification": "attempted_level_limitation"
}
```

`game_end_reason` must be `open_card_throw`. `throwing_player_id` must identify
exactly one stable participant and cannot use `me`, `left`, or `right`. The
declarer ID determines the throwing and opposing parties. Either defender binds
both defenders without partner consent and has joint liability. A declarer
throw has no defender joint liability.

The only statement classifications are `none`, `generic_concession`, and
`attempted_level_limitation`. They preserve provenance and never affect rules or
scoring. Free text and specific future-trick assertions are rejected.

## Exact replay and hand reconciliation

The supplied tricks are replayed through the shared exact historical prefix
validator. Zero through 29 actual plays are supported, with at most one final
incomplete trick of one or two cards. Ownership, leader, order, follow-suit,
duplicate-card, discard, and skat contradictions are rejected. The event occurs
immediately after the final supplied play. All 30 plays, ten completed tricks,
and a throwing player with no current hand cards are invalid.

`thrown_cards` must contain one through ten valid unique cards and must equal
the throwing player's complete reconstructed current hand. Input order is
canonicalized to deck order. Played cards, current-trick cards, final skat or
discarded cards, and another player's cards cannot occur in the thrown hand.
Historical reconciliation is always `confirmed`; only the thrown current hand
is included in the terminal summary.

## Rule assignment and result

The historical adapter builds exact stable-to-flat player mapping and delegates
to the existing `OpenCardThrow`, `OpenCardThrowContext`, and
`adjudicate_open_card_throw(...)` implementation. It does not implement a
second adjudicator or call the exact rest-trick solver.

The throwing party retains only completed tricks and observed points. Every
unresolved trick and point goes to the opposing party. Current incomplete-trick
cards and points are included exactly once. No future card order or individual
winner is invented. Completed plus assigned tricks total ten; final Suit and
Grand points total 120.

The pre-throw decision state is derived before assignment. A preexisting
declarer win, defender win, or Null loss remains binding and cannot be reversed
by the later throw.

Suit and Grand Schneider is derived from the final rule-assigned point state and
remains distinct from normally achieved Schneider. Schwarz requires zero final
tricks for the losing party and no theoretical exclusion. The shared jack-only
assessment excludes Schwarz when exact historical ownership shows that the
losing party originally held `CJ`, or all of `SJ`, `HJ`, and `DJ`. A final-skat
jack belongs to neither party. No non-jack combination, future-play simulation,
or full-card proof is inspected.

The shared declaration, game-value, overbid, and settlement paths preserve
Suit, Grand, all four Null variants, Hand, announcements, ouvert, matadors,
mandatory declared levels, and supported overbid-required levels. Suit and Grand
use ordinary won values and doubled lost values. Null uses fixed values and
completed plus assigned trick ownership only. A declarer throw wins an
otherwise undecided Null if no prior declarer trick exists; a defender throw
loses an otherwise undecided Null by assigning unresolved tricks to the
declarer. A prior declarer trick preserves the Null loss.

## Historical workflows and privacy

Exactly one decision artifact is generated per actual played card. No artifact
is generated for the throw, statement, rule assignment, theoretical assessment,
or settlement. Snapshots, normal and external-profile review, training records,
dataset summaries, partition audits, historical opponent statistics and export,
and rolling opponent-policy evaluation accept the new reason through the shared
variable-cardinality infrastructure. Feature generation remains version `1` and
the target remains `actual_card_played`.

The thrown hand becomes public only at the terminal event, after the final card
decision. Earlier snapshots, review inputs, training features, and rolling
predictions contain no throwing identity, thrown cards, statement, assignment,
theoretical assessment, winner, or settlement. Every selected record contributes
one statistics game per participant, using final settlement as the sole winner
authority. Play count, thrown-card count, unresolved tricks, and theoretical
assessment do not weight statistics. No open-throw-specific profile signal,
classification, threshold, policy, preset, or prediction target is added.

## Boundaries

Version 1 does not support simultaneous throws, a prior terminal event, multiple
continuations, arbitrary event streams, continued play after the throw, specific
future-trick claims, full-card theoretical solving, exact rest-trick proof, throw
or statement prediction, learned models, or four-player tables.

See
[`examples/historical_grand_open_card_throw.json`](../examples/historical_grand_open_card_throw.json),
[`schemas/historical_open_card_throw.schema.json`](../schemas/historical_open_card_throw.schema.json),
and
[`schemas/historical_open_card_throw_output.schema.json`](../schemas/historical_open_card_throw_output.schema.json).
