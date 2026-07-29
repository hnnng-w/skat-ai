# Historical declarer card exposure continuation

Version-1 historical games can record one timed non-terminal declarer-card-
exposure continuation under ISkO 4.4.4. The declarer exposed the complete
current hand, at least one defender required continued play, and that hand
remained physically open to all players. Actual later play determines the final
result.

## Record contract

The containing game remains an ordinary normal completion:

```json
{
  "game_end_reason": "normal_completion",
  "game_events": [
    {
      "schema_version": 1,
      "kind": "declarer_card_exposure_continuation",
      "after_play_count": 12,
      "exposure": {
        "form": "shown_to_defender",
        "shown_to_defender_player_id": "player-a"
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
          "response": "continue",
          "form": "unambiguous_conduct"
        }
      ],
      "public_declarer_cards": ["D7", "HQ", "D8", "HK", "H10", "HA"]
    }
  ],
  "tricks": []
}
```

`game_events` is optional. Version 1 accepts at most one event and that event is
either `declarer_card_exposure_continuation` or
`defender_open_play_continuation`. When an event is present, the record requires
`game_end_reason: "normal_completion"`, no terminal `game_end`, exactly ten
complete tricks, and all 30 actual plays. Multiple events and continuation
followed by a shortened end remain unsupported.

The event schema version is independent of the historical-game schema version;
both currently equal `1`. The focused input schema is
[`schemas/historical_declarer_card_exposure_continuation_event.schema.json`](../schemas/historical_declarer_card_exposure_continuation_event.schema.json).

## Boundary and exact hand

`after_play_count` is a strict integer from `0` through `29`. It identifies the
boundary after that many chronological plays and before the next actual play.
Replay reconstructs completed tricks, any incomplete current trick, the next
player, and every exact remaining hand without sampling or hidden-world
assignment.

`exposure.form` is `laid_open` or `shown_to_defender`. The latter requires one
exact stable `shown_to_defender_player_id` on the defending side; relative
`me`, `left`, and `right` identities are invalid. `public_declarer_cards`
contains one through ten unique cards and must exactly equal the declarer's
complete reconstructed hand at the boundary.

Exactly both stable defenders respond once. Responses are `accept` or
`continue`, forms are `explicit` or `unambiguous_conduct`, and at least one
response must be `continue`. Unanimous acceptance belongs to the terminal
`game_end_reason: "declarer_card_exposure"` contract.

## Continued-play semantics

Suit and Grand preserve claimed `simple`, `schneider`, or `schwarz` only as
non-settling provenance. Null permits only `simple`. The claim does not prove or
assign a result and has status
`continuation_required_no_immediate_settlement_effect`.

The event does not call a solver, adjudicate the claim, assign a card, trick, or
point, produce an event-specific result, select a winner, create a game end, or
create settlement. The output
explicitly reports no exact proof, game end, or settlement effect. Its focused
summary schema is
[`schemas/historical_declarer_card_exposure_continuation_event_output.schema.json`](../schemas/historical_declarer_card_exposure_continuation_event_output.schema.json).

## Public hand over time

For an event after `N` plays, decisions `1..N` retain their pre-event
information and decisions `N+1..30` contain the declarer's exact current public
hand. The hand remains physically open with `visibility_scope: "all_players"`
and remains in the declarer's legal possession. It shrinks only when the
declarer actually plays one of its cards. Continued normal play must consume the
complete hand.

Snapshots and historical review map the stable declarer to `me`, `left`, or
`right` for each actor and reuse the existing `PublicHandConstraint` and exact
sampler. No additional card enters the declarer's hand; only genuinely unknown
cards are sampled. Every compared policy receives the same constraint.

Historical review remains Immediate Analysis and does not use the later complete
deal to construct a Multi-Step root. Actual future hands remain excluded from
every pre-play decision state.

## Downstream workflows

The event is not a decision. Snapshots, review, training conversion, and rolling
targets still contain exactly 30 actual-card decisions or samples. Pre-event
artifacts contain no event information; post-event artifacts contain only the
authorized shrinking hand through the existing public-exposure feature. There
is no event, claim, response, result, settlement, or profile target or signal.

All ten actual trick winners and ordinary normal-completion scoring remain
authoritative. Historical statistics and rolling source profiles use only final
results and count the record as one ordinary game. Dataset partitions and audits
remain record-, participant-, and stable-ID-based.

See the implementation in
[`src/skat_ai/historical_declarer_card_exposure_continuation.py`](../src/skat_ai/historical_declarer_card_exposure_continuation.py),
the deterministic
[`examples/historical_grand_declarer_card_exposure_continuation.json`](../examples/historical_grand_declarer_card_exposure_continuation.json),
and [Historical declarer card exposure](historical_declarer_card_exposure.md) for
the separate unanimously accepted terminal form.
