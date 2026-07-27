# Historical declarer concessions

Version-1 `historical_game_input` supports a structured declarer concession
under ISkO 4.4.1 and 4.4.2. This is the first shortened historical-game record
and uses an exact legal play prefix plus a versioned historical game-end event.
It does not change existing normal-completion records.

## Event contract

Use `game_end_reason: "declarer_concession"` with exactly one required
`game_end` object:

```json
{
  "game_end_reason": "declarer_concession",
  "game_end": {
    "schema_version": 1,
    "kind": "declarer_concession",
    "declarer_hand_cards_remaining": 6,
    "defender_consent": {
      "status": "granted",
      "consenting_defender_player_ids": ["player-b"]
    }
  }
}
```

The outer historical schema and event schema both remain version `1`.
`game_end_reason` and `game_end.kind` must agree. Normal completion requires
`game_end` to be absent. Unknown reasons, kinds, versions, and properties are
rejected. The historical event uses stable player IDs rather than flat-position
`me`, `left`, or `right` identities and remains a separate extensible union from
`game_shortening`.

## Exact play prefix

`tricks` contains every card actually played before the event. It may be empty,
contain zero through nine complete tricks, and end with one optional incomplete
trick of one or two plays. Concession may also occur between complete tricks.
Only the final trick may be incomplete, and concession after all 30 playable
cards is invalid.

Replay starts from the complete initial deal and final playable hands after
pickup/discard or Hand skat handling. It validates consecutive trick numbers,
forehand's first lead, winner-led later tricks, fixed seat order, ownership,
duplicate use, unplayable skat/discards, and Suit, Grand, or Null follow rules.
No unplayed card is inferred or simulated.

The immutable replay state reconstructs every exact remaining hand internally,
the optional current incomplete trick, the next player, completed trick count,
and total play count. Public output exposes remaining hand sizes, not complete
remaining hand card lists.

## Hand count and consent

`declarer_hand_cards_remaining` is a required strict integer in `1..10` and must
equal the reconstructed declarer hand size immediately after the final supplied
play. Complete-deal evidence always reports `confirmed`; mismatches are rejected.

| Declarer cards | Consent status | Stable consenting defender IDs | Rule |
| --- | --- | --- | --- |
| `9..10` | `not_required` | empty | ISkO 4.4.1 |
| `1..8` | `granted` | one or both defenders | ISkO 4.4.2 |

The declarer, unknown IDs, duplicate IDs, missing required consent, and consent
when not required are rejected. Canonical output orders consent IDs by fixed
historical seat order.

## Points and result

Completed-trick points remain observed. Applicable final skat points are
observed declarer points. Points in an incomplete current trick and cards still
held in player hands remain separately unresolved. Observed declarer points,
observed defender points, and unresolved points total 120, but unresolved points
are not assigned to either side.

The result is complete by adjudication, with `winner: "defenders"`,
`outcome_source: "adjudicated"`, no remaining-points recipient, and zero points
assigned. Unfinished play does not infer achieved Schneider or Schwarz.

## Settlement

Historical adjudication delegates to the existing structured declarer-
concession behavior. Suit and Grand preserve the declaration, Hand,
announcements, ouvert, inferred or verified matadors, and supported overbid-
required value. The loss is twice the effective game value. Null, Null Hand,
Null ouvert, and Null ouvert Hand use fixed values 23, 35, 46, and 59 and the
same doubled-loss rule. Overbid Null remains unsupported.

For equivalent declaration, bid, points, and concession facts, flat and
historical workflows have the same winner and effective settlement value.

## Output and CLI

Run the bounded example with:

```powershell
python main.py --input examples/historical_grand_declarer_concession.json
```

Quiet JSON output is supported with `--output ... --quiet`. Structured output
preserves the exact supplied record and adds derived completed tricks,
`play_prefix_summary`, optional `incomplete_current_trick`, `point_accounting`,
`historical_game_end_summary`, result, value, overbid, and settlement. It does
not emit reconstructed complete remaining hands.

## Workflow boundary

Shortened records produce one snapshot, review decision, and training sample per
actual supplied play, including cards in an incomplete final trick. Empty
prefixes produce zero artifacts. External-profile review and record/player
partition audits are supported. The concession and consent remain outside
decision-time state. Historical opponent-statistics aggregation counts every
concession once, including zero-play records, with a declarer loss and two
defender wins from final settlement. Completed concessions may contribute to
later rolling profiles; target concessions contribute only actual card plays,
including valid zero-decision targets. No concession-specific signal exists.
See [Shortened historical opponent workflows](shortened_historical_opponent_workflows.md).

Historical defender concession, card exposure, defender open play, open card
throwing, continuation, claims of remaining tricks, and every other historical
end kind remain unsupported.
