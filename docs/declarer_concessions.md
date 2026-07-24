# Declarer concessions

This document describes the bounded version-1 adjudication for a concealed or
verbal declarer concession under ISkO 4.4.1 and 4.4.2.

## Scope

The structured contract is supported only in the flat position/result workflow.
It represents an accepted declarer concession and immediately settles the game
as a declarer loss. It does not reveal cards, simulate future play, prove future
tricks, or assign unplayed card points.

The following remain separate from this contract:

* unanimously accepted declarer card exposure under ISkO 4.4.4, documented in [Accepted declarer card exposure](declarer_card_exposure.md)
* defender open play under ISkO 4.4.5
* open card throwing under ISkO 4.4.6
* solver-backed claims or hypothetical continuation
* historical-game shortening, snapshots after concession, and training samples

Defender concession under ISkO 4.4.3 is the separate version-1 union member
documented in [Defender concessions](defender_concessions.md). Its joint
liability and decision-state rules do not change this declarer-concession kind.

## Input contract

Use `game_shortening` with exactly schema version `1` and kind
`declarer_concession`:

```json
{
  "game_shortening": {
    "schema_version": 1,
    "kind": "declarer_concession",
    "declarer_hand_cards_remaining": 9,
    "defender_consent": {
      "status": "not_required",
      "consenting_defender_count": 0
    }
  }
}
```

`declarer_hand_cards_remaining` is the number of cards physically held by the
declarer at concession time. It is required, must be an integer rather than a
boolean, and must be in `1..10`. The value is never inferred from card points or
silently corrected.

The object and its nested consent object reject unknown properties. Future
game-shortening kinds can be added as schema-union variants without changing the
version-1 meaning.

## Consent

| Declarer hand cards | Status | Consenting defenders | Rule section |
| --- | --- | --- | --- |
| `9..10` | `not_required` | `0` | ISkO 4.4.1 |
| `1..8` | `granted` | `1` or `2` | ISkO 4.4.2 |

One defender's consent is sufficient below nine cards. The object represents a
validly accepted concession; there is no rejected-concession or continued-play
state.

## Reconciliation

Runtime validation compares the supplied count with reliable current-hand
evidence when the concrete declarer is known:

* local declarer: current `hand` length
* left declarer: `left_hand_size`
* right declarer: `right_hand_size`
* completed-trick count and concrete current-trick play timing

A contradiction is rejected. When the generic position does not identify a
concrete declarer, the concession remains valid and output reports
`not_verifiable`. The output reports `confirmed` when the supplied count matches
available evidence.

## Exclusivity

Structured concession requires `analysis_mode: "post_game_review"`, a valid
declaration with a calculable game value, and incomplete normal play. It accepts
an absent legacy `game_end_reason` or neutral `not_ended` only.

It is rejected with:

* any active legacy claim, concession, normal-completion, or impossible-Null reason
* `impossible_null_settlement`
* all ten completed tricks or all 120 points already assigned
* an unvalued Suit or Grand declaration
* an unsupported overbid-required value, including overbid Null
* list-performance or non-position workflows
* Multi-Step simulation

Historical games, historical review and snapshots, training datasets, opponent
statistics, partition audits, list workflows, and impossible-Null-only workflows
do not accept this object.

## Adjudicated result

The raw `game_result_summary` preserves observed points and the unplayed point
count. `adjusted_game_result_summary` then records:

* `is_complete: true`
* `winner: "defenders"`
* `status: "final_adjudicated"`
* `game_end_kind: "declarer_concession"`
* `outcome_source: "adjudicated"`
* `remaining_points_recipient: null`
* `remaining_points_assigned: 0`

The observed declarer and defender totals do not change. The totals therefore
need not sum to 120, and `points_remaining` continues to expose unplayed points.

## Settlement

Suit and Grand retain the declared value, actual matador basis, Hand status, and
announced Schneider, Schwarz, or ouvert levels already contained in that value.
Supported overbid settlement can replace it with the existing required game
value. The forced loss is:

```text
settlement_score = -2 * effective_game_value
```

Null, Null Hand, Null ouvert, and Null ouvert Hand use their fixed values and the
same doubled-loss rule.

No achieved Schneider or Schwarz level is inferred from observed points,
incomplete trick ownership, or possible future play. A higher value required by
overbidding is valuation only and is not labeled as an achieved play level.
`settlement_basis` exposes these decisions explicitly.

## Compatibility

The legacy `declarer_conceded_remaining_tricks` reason remains valid and retains
its existing simplified behavior of assigning all remaining points to the
defenders. It cannot coexist with `game_shortening` and is not silently mapped to
the structured rule-bounded adjudication. New integrations should prefer the
structured contract.
