# Accepted declarer card exposure

This document describes the bounded version-1 final adjudication for declarer
card exposure under ISkO 4.4.4. It covers only an event in which the declarer
laid open or showed every remaining hand card and both concrete defenders
accepted the shortening.

## Scope

The feature is available only in the flat position/result workflow with
`analysis_mode: "post_game_review"`. Showing all cards to one defender is enough
to record an exposure event, but it does not let that defender bind the other:
both defenders must separately accept.

This workflow records already classified `explicit` or
`unambiguous_conduct` acceptance. It does not interpret natural language,
physical conduct, or ambiguity. A defender objection requires continued play
with exposed cards; that continuation is not supported by Issue #88 and is
rejected rather than simulated.

Defender open play under ISkO 4.4.5, open throwing under ISkO 4.4.6, historical
exposure records, solver proof, and exposed-card recommendation simulation are
separate unsupported workflows.

## Input

```json
{
  "game_shortening": {
    "schema_version": 1,
    "kind": "declarer_card_exposure",
    "exposure": {
      "form": "laid_open",
      "exposed_cards": ["CA", "C10", "CJ"]
    },
    "claimed_play_level": "schneider",
    "defender_responses": [
      {"player": "left", "response": "accept", "form": "explicit"},
      {
        "player": "right",
        "response": "accept",
        "form": "unambiguous_conduct"
      }
    ]
  }
}
```

`exposure.form` is `laid_open` or `shown_to_defender`. A shown exposure requires
`shown_to_player`; a laid-open exposure forbids it. The shown player must be a
concrete defender. `exposed_cards` contains all `1..10` remaining declarer cards
in existing notation, without duplicates.

`defender_responses` contains exactly the two players other than the concrete
declarer, each exactly once. Only `response: "accept"` is supported. Input order
does not affect adjudication; output uses deterministic concrete-player order.

Suit and Grand accept `simple`, `schneider`, or `schwarz`.
`schwarz` includes Schneider. Every Null variant requires `simple`. The field is
an explicit requested play level, not an interpretation of free text. Ouvert
cannot be added after declaration.

## Card reconciliation

The engine checks exposed cards against reliable local declarer-hand evidence,
hand-size and play-timing evidence, completed tricks, the incomplete current
trick, legacy played cards, known skat cards, and a local defender hand. Cards
already played or reliably owned elsewhere are rejected. A reliable complete
declarer hand must match exactly; missing cards are never inferred.

Output reports `confirmed` for an exact reliable hand match and
`not_verifiable` when only bounded count or incomplete ownership evidence is
available. Hidden defender cards are not copied into output.

## Decision and settlement

Before exposure, the shared bounded decision helper derives `undecided`,
`declarer_already_won`, or `defenders_already_won`. Suit and Grand use observed
61/60 point decisions, failed mandatory Schneider/Schwarz or ouvert conditions,
completed-trick ownership, and supported overbid requirements. An incomplete
current trick is not proof. Null is already lost only when a reliable completed
trick was won by the declarer.

Unanimous acceptance grants an undecided announced contract to the declarer. A
preexisting winner is preserved, so acceptance cannot reverse an existing
declarer loss. Null uses its fixed value. Suit and Grand preserve matadors, Hand,
and declared levels. Declared mandatory play levels and accepted Schneider or
Schwarz claims contribute to winning settlement without being labeled as
achieved during normal play.

A supported overbid-required Schneider or Schwarz level must be covered by the
declaration or accepted claim. Otherwise the exposure settles as an overbid
loss. Requirements beyond the bounded Schneider/Schwarz support are rejected.

`settlement_basis` separates:

* declared mandatory Schneider and Schwarz application
* unanimously accepted claimed Schneider and Schwarz application
* levels secured through observed play
* overbid-required valuation and coverage
* preexisting versus adjudicated winner basis

Observed declarer points, observed defender points, current-trick accounting,
and `points_remaining` remain unchanged. `remaining_points_recipient` is `null`
and `remaining_points_assigned` is `0`. No fictitious 120-point result is
created, and the exposed cards are not used to simulate future play.

## Compatibility

The new object is the third member of the version-1 `game_shortening` union.
Structured declarer concession, structured defender concession, all legacy
claim/concession reasons, impossible Null, and normal completion retain their
existing behavior. Only one effective game-ending mechanism may be active.

See [`examples/declarer_card_exposure.json`](../examples/declarer_card_exposure.json)
for the public deterministic example.
