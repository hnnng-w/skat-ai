# Historical decision snapshots

Historical decision snapshots reconstruct the information available immediately
before each actual card in an already validated normal-play historical game.
Snapshot-only output does not run recommendations or create training-dataset
records. The optional historical game review uses these same snapshots as its
only decision-state input. The separate training-dataset workflow also reuses
them, converting stable player IDs to relative feature references without
changing snapshot-only output.

## Requesting snapshots

Use the historical-only CLI flag:

```powershell
python main.py --input examples/historical_grand_normal_completion.json --historical-decision-snapshots
```

For automation-friendly structured output:

```powershell
python main.py --input examples/historical_grand_normal_completion.json --historical-decision-snapshots --output outputs/historical-snapshots.json --quiet
```

Without the flag, historical output is unchanged and omits
`decision_snapshot_summary`. Position inputs reject the flag.

## Summary and ordering

The optional object is nested under `historical_game_summary`:

```json
{
  "decision_snapshot_summary": {
    "schema_version": 1,
    "information_policy": "decision_time",
    "snapshot_count": 30,
    "snapshots": []
  }
}
```

There is exactly one snapshot immediately before each actual play. Snapshots are
ordered chronologically with `decision_index` values `1..30`, trick numbers
`1..10`, and play indices `1..3`. `source_game_id` preserves the historical game
ID. The pair of `source_game_id` and `decision_index` is the snapshot identity.

Optional `source_played_at` preserves the original historical game-start
timestamp when supplied. It is provenance and does not add future game facts to
the visible decision state.

`actual_card_played` is a retrospective label outside `visible_state`. It is in
the pre-play `own_hand` and `legal_cards`, but it is not inserted into
`current_trick` before the decision.

## Relative players

Each snapshot maps stable player IDs into the acting player's local view:

```json
{
  "relative_player_map": {
    "me": "player-a",
    "left": "player-b",
    "right": "player-c"
  }
}
```

`me` is the acting player. `left` is the next player and `right` is the previous
player in fixed `forehand -> middlehand -> rearhand` seat order. Leadership does
not change this mapping. Opponent hand-size rows use `left`, then `right` order.

## Visible state

`visible_state` contains:

* the game type and public declaration facts
* the acting player's remaining pre-play hand
* legal cards derived from that hand, current trick, and contract
* decision-time skat visibility and known skat cards
* remaining publicly exposed declarer cards for ouvert games
* only tricks completed before the decision
* only earlier plays in the current trick
* declarer and defender points from prior completed tricks only
* both opponents' public remaining-card counts without card identities

Completed tricks include ordered stable player IDs and cards, the derived winner
ID and side, and trick points. Current-trick lengths are `0`, `1`, and `2` before
the first, second, and third play. Point totals exclude the incomplete current
trick and exclude original or discarded skat points.

## Skat and matadors

A non-Hand declarer sees the two final discarded cards with
`skat_visibility: "known_to_declarer"`. Defenders see neither card. In a Hand
game, every player receives `skat_visibility: "unknown"` and an empty
`known_skat_cards` array.

Snapshot matadors are inferred independently from visible ownership evidence.
A non-Hand declarer can use complete ownership known after pickup and discard.
Hand declarers and defenders receive `null` unless their own cards, prior public
plays, and public exposure determine the count safely. The final historical
matador value is never copied into snapshots.

For Suit, Grand, and Null ouvert games, `public_exposed_cards` contains only the
declarer's currently remaining playable cards. Non-ouvert games use an empty
array. Hidden skat and discarded cards are never exposed. Ouvert visibility is
represented here but is not consumed by current opponent-hand simulation.
Historical review returns `public_exposed_cards_not_supported` without running
simulation for such snapshots.

## Leakage boundary

Snapshots do not contain future plays, future winners, future points, hidden
opponent hands, final points, final winner, achieved Schneider or Schwarz, final
game value, overbid outcome, settlement, recommendations, or decision-quality
ratings. The builder consumes the validated historical replay result and does
not perform a second competing complete-game validation.

External profile application does not add source statistics or hidden cards to
`visible_state`. Historical review uses the existing `relative_player_map` only
to select time-safe stable-ID profiles for the two opponent policy slots.

Snapshots are not complete-game review results and are not themselves
training/evaluation dataset records. The separate
[historical game review](historical_game_review.md) evaluates them through the
existing immediate recommendation workflow. The separate
[training data](training_data.md) workflow derives identity-free features and an
actual-card label without running that workflow. Complete-game retrospective
analysis remains partial because ouvert recommendation simulation, later end
reasons, and other approved gaps remain.

The stable structure is defined by
[`schemas/historical_decision_snapshot.schema.json`](../schemas/historical_decision_snapshot.schema.json)
and referenced by the public output schema. Runtime tests remain authoritative
for temporal prefixes, ownership, legality, visibility, and leakage-sensitive
semantics.
