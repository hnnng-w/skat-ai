# Historical declarer card exposure

`skatmind` supports version-1 historical games that end through unanimously
accepted declarer-card exposure under ISkO 4.4.4. This is a terminal historical
record, not the separate flat or timed historical continuation workflow.

## Event contract

Use `game_end_reason: "declarer_card_exposure"` with a matching `game_end`:

```json
{
  "schema_version": 1,
  "kind": "declarer_card_exposure",
  "exposure": {
    "form": "shown_to_defender",
    "shown_to_defender_player_id": "player-a",
    "exposed_cards": ["H10", "HK", "HQ", "D8", "D7"]
  },
  "claimed_play_level": "schneider",
  "defender_responses": [
    {
      "defender_player_id": "player-a",
      "response": "accept",
      "form": "explicit"
    },
    {
      "defender_player_id": "player-c",
      "response": "accept",
      "form": "unambiguous_conduct"
    }
  ]
}
```

`exposure.form` is `laid_open` or `shown_to_defender`. `laid_open` forbids a
shown-to field. `shown_to_defender` requires
`shown_to_defender_player_id`, which must be one exact stable participant ID on
the defending side. Relative `me`, `left`, and `right` identities are not part
of this historical contract.

`claimed_play_level` is `simple`, `schneider`, or `schwarz`. Null permits only
`simple`. Each defender must occur exactly once in `defender_responses`; every
response is `accept`, and each form is `explicit` or
`unambiguous_conduct`. Input response order is canonicalized to historical
forehand, middlehand, rearhand seat order. An objection or continuation response
is rejected here and belongs to the separate timed
[historical declarer-card-exposure continuation](historical_declarer_card_exposure_continuation.md).

The focused input schema is
[`schemas/historical_declarer_card_exposure.schema.json`](../schemas/historical_declarer_card_exposure.schema.json).

## Exact replay and cards

The existing historical prefix replay remains authoritative. It supports zero
through 29 actual plays while at least one declarer card remains, including one
optional final incomplete trick with one or two cards. Ownership, leader, order,
follow-suit, duplicate, discard, and skat contradictions are rejected. Exposure
after all 30 playable cards, or with an empty reconstructed declarer hand, is
invalid.

`exposed_cards` must contain every current remaining declarer card and no other
card. The set is reconciled against the exact replay result and output always
reports `card_reconciliation: "confirmed"`. Empty, invalid, duplicate, missing,
or extra cards are rejected, including completed-play cards, current-trick
cards, discarded or Hand-skat cards, and defender-owned cards.

Canonical output orders cards by deck order. The exposed declarer cards are the
only event-authorized remaining cards. Output preserves remaining hand sizes but
does not emit either defender's reconstructed remaining hand. The incomplete
current trick has no winner or assigned points.

## Result and settlement

Historical adaptation constructs the existing flat `DeclarerCardExposure`,
`DeclarerCardExposureDetails`, and `DefenderExposureResponse` values internally
and calls `adjudicate_accepted_declarer_card_exposure(...)`. Stable IDs are
mapped to flat players only inside the adapter and are restored before
serialization. Historical and flat accepted-exposure result and settlement
behavior therefore agree.

The adjudicator does not simulate exposed cards, prove future play, infer
optional levels beyond the accepted claim, assign unresolved points, or label
accepted claimed levels as achieved in normal play. It preserves a declarer or
defender win already secured before exposure. For an undecided game, acceptance
awards the declarer the covered declared or claimed level; an uncovered supported
overbid requirement awards the defenders the game.

Suit and Grand preserve Hand, announcements, ouvert, matadors, mandatory levels,
supported overbid requirements, ordinary winning values, and doubled losing
values. Null, Null Hand, Null Ouvert, and Null Hand Ouvert retain their fixed
values and preexisting-trick decision behavior. Overbid Null remains in the
separate impossible-Null workflow.

Completed-trick and skat points are observed. Current-trick and remaining-hand
points remain unresolved, and all observed plus unresolved points reconcile to
120. Final settlement is the winner authority for downstream statistics.

The focused output schema is
[`schemas/historical_declarer_card_exposure_output.schema.json`](../schemas/historical_declarer_card_exposure_output.schema.json).

## Decision and opponent workflows

Exactly one snapshot, review decision, and training sample is generated for each
actual played card. Exposure, claim, either acceptance, and the terminal end
create no artifact or target. Feature-generation version remains `1` and the
only target remains `actual_card_played`.

Snapshot, review, external-profile review, training conversion, variable sample
counts, dataset summaries, and partition audits reuse the shared played-card
cardinality. Terminal exposure facts never enter earlier decision states,
features, profiles, or rolling prediction inputs. Changing exposure form,
shown-to defender, response order, acceptance form, or claimed level therefore
does not change artifacts for a shared play prefix.

Every record contributes one statistics game per participant, including a
zero-play record. Final settlement gives a normal covered accepted exposure one
declarer solo win and two defender losses. A preserved defender win or uncovered
overbid requirement gives one declarer solo loss and two defender wins. Export
uses the existing opponent-statistics contract. Rolling sources have one game of
weight and rolling targets contain only actual card decisions, including zero.

No exposure-specific statistic, signal, threshold, classification, profile
field, policy, exposure-choice target, or defender-acceptance target is added.

## CLI and boundaries

Run the deterministic example:

```powershell
python main.py run --input examples/historical_grand_declarer_card_exposure.json
```

The human-readable summary reports stable IDs, exposure form, card count,
unanimous acceptance, claimed level, actual play count, pre-event decision,
winner, unresolved-point policy, and settlement. `--quiet` preserves the normal
structured-only behavior.

Either single supported continuation may precede this terminal workflow. It does
not add multiple continuations, arbitrary event streams, free-text or gesture
interpretation, exposure-choice or acceptance prediction, exact future-play
proof, a learned model, or four-player support.
