# Open card throw

This document describes the bounded version-1 final adjudication for openly
throwing a complete remaining hand under ISkO 4.4.6.

## Scope

The flat feature is available in the position workflow with
`analysis_mode: "post_game_review"`. The historical terminal adapter is
documented separately in [Historical open card throw](historical_open_card_throw.md).
Both support one concrete declarer or
defender throwing that player's complete current hand. One defender's throw
binds the complete defending party through joint liability; partner approval is
not required.

The event ends play. It is not a concession, accepted declarer exposure,
defender open play, normal completion, or a continuation. It does not simulate
card order, invent individual future trick winners, use opponent policy, or call
the exact rest-trick solver.

## Input

```json
{
  "game_shortening": {
    "schema_version": 1,
    "kind": "open_card_throw",
    "throwing_player": "left",
    "thrown_cards": ["C10", "S10"],
    "statement_classification": "attempted_level_limitation"
  }
}
```

`throwing_player` is exactly `me`, `left`, or `right`. The concrete
`declarer_player` determines whether the throwing party is `declarer` or
`defenders`; the opposing party and defender joint-liability flag are derived.

`thrown_cards` contains all `1..10` cards physically held by that player at the
throw. Cards use existing notation and must be valid and unique. Runtime
validation rejects overlap with completed tricks, the incomplete current trick,
legacy played cards, the skat, or reliable ownership by another player. A local
throwing hand or other supported exact hand must match exactly. Deterministic
hand-size progression must match the completed-trick count and current-trick
participation. Exact independent ownership reports `confirmed`; count-only or
otherwise incomplete evidence reports `not_verifiable`. The supplied thrown
hand remains authoritative event evidence in either state.

The only statement classifications are:

* `none`
* `generic_concession`
* `attempted_level_limitation`

They record provenance and never affect the result. Free text is not parsed. A
structured assertion about one or more specific future tricks is rejected and
requires a separate classified trick-claim workflow.

## Rule assignment

The throwing party keeps only completed tricks and already assigned observed
points. Every unresolved trick and every outstanding card point goes to the
opposing party. An empty current trick and valid one-card or two-card current
trick are supported. An incomplete current trick is unresolved, so all its cards
and points are included once in the opposing-party assignment.

The assignment is party-level. It does not create an order of play or individual
future trick winners. Completed plus assigned tricks must total ten. Existing
observed points plus assigned points must total 120 for Suit and Grand. The
authoritative observed-point summary and existing skat treatment are reused.

Before assignment, shared bounded decision logic records `undecided`,
`declarer_already_won`, or `defenders_already_won`. A preexisting winner remains
binding even when the later rule-assigned point state would otherwise point in
the opposite direction. For an undecided game, a declarer throw normally gives
the game to the defenders and a defender throw normally gives it to the
declarer.

## Schneider and Schwarz

Suit and Grand Schneider comes from the final rule-assigned point state. The
losing party is Schneider at 30 or fewer final points and is not Schneider at
31 or more. Its source is `open_card_throw_final_point_state`, not achieved
normal play.

Schwarz requires both:

* zero final tricks for the losing party
* no theoretical exclusion

Version 1 implements only the documented jack-only theoretical assessment.
Schwarz is excluded when reliable original ownership proves that the losing
party held the Kreuz-Bube (`CJ`) or all three lower jacks (`SJ`, `HJ`, and `DJ`).
Evidence may come from the thrown cards, an exact local hand, concrete completed-
trick players, current-trick order, or the skat. A jack in the skat belongs to
neither party. Unknown ownership and one or two lower jacks do not establish
exclusion. No arbitrary non-jack combination or exact rest-trick search is
inspected.

Output keeps achieved-during-play flags separate from
`open_throw_schneider_applied` and `open_throw_schwarz_applied`. The bounded
assessment exposes only jack ownership status and sources, never another
complete hand.

## Declaration and settlement

The original declaration, matadors, Hand, announcements, ouvert, and supported
overbid requirement remain effective. An already failed mandatory level remains
a loss. A still-possible declared or supported overbid-required Schneider or
Schwarz level may be covered by the open-throw rule state. Required Schwarz is
not covered when the jack-only assessment excludes it. Open throwing creates no
new announcement and never labels a rule-assigned level as achieved normal play.

Suit and Grand use the existing doubled lost-game score. Without overbid, each
applicable open-throw Schneider or Schwarz level adds one base-value level.
Supported overbid settlement uses the existing minimum required effective value.

All four Null variants use fixed values and completed plus rule-assigned trick
ownership, not card points. If the declarer throws before taking a completed
trick, all unresolved tricks go to the defenders and the Null contract is won.
A prior completed declarer trick preserves the loss. If a defender throws, every
unresolved trick goes to the declarer, so an undecided Null is lost. Schneider
and Schwarz do not apply.

## Output and information control

`game_shortening_summary` records the concrete player, derived parties, joint
liability, canonical thrown cards, reconciliation, statement provenance,
pre-throw decision, observed and assigned points and tricks, final winner,
open-throw levels, and theoretical Schwarz assessment.

`adjusted_game_result_summary` and `final_settlement_summary.settlement_basis`
preserve the same reconciliation and level sources. Only the thrown hand becomes
public through this event. When another player throws, the ordinary serialized
local hand is redacted so no second complete hand is emitted. Quiet JSON output
remains silent.

## Boundaries

Version 1 does not add simultaneous unordered throws, natural-language parsing,
specific future-trick assertions, isolated decisive-card claims, continued play,
Monte Carlo analysis, open-throw prediction, policy signals, full-card
theoretical solving, exact rest-trick proof, or four-player
tables. Complete settlement nuance remains unfinished outside this bounded path.

See [`examples/open_card_throw.json`](../examples/open_card_throw.json) for the
deterministic defender-throw example.
