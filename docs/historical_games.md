# Historical games

`skat-ai` supports a separate versioned workflow for complete three-player games
that ended through normal play. It validates the initial 32-card deal, final
declaration, skat handling, all 30 plays, result, and settlement without mapping
stable player IDs to the position workflow's local `me`/`left`/`right` model.

Historical-game representation remains `partially_supported`. This workflow
does not provide complete-game decision review, replay recommendations, training
dataset metadata, claims, concessions, full auction events, player statistics,
or list/tournament aggregation.

## Public input

The top-level input contains only `historical_game_input`:

```json
{
  "historical_game_input": {
    "schema_version": 1,
    "game_id": "game-001",
    "players": [],
    "skat": [],
    "declarer_player_id": "player-a",
    "declaration": {},
    "discarded_cards": [],
    "game_end_reason": "normal_completion",
    "tricks": []
  }
}
```

`schema_version` currently accepts only `1`. Game IDs, player IDs, and optional
player labels are opaque, case-sensitive, non-empty strings. They are preserved
without trimming or normalization. Leading or trailing whitespace is invalid.

Exactly three players are required, with unique IDs and exactly one each of
`forehand`, `middlehand`, and `rearhand`. Every player supplies ten unique cards;
the original skat supplies two. The three hands and skat must equal the standard
32-card deck exactly.

The focused structural schema is
[`schemas/historical_game.schema.json`](../schemas/historical_game.schema.json).
The public [`input.schema.json`](../schemas/input.schema.json) references it as a
mutually exclusive alternative to the existing position branch.

## Declaration and skat

`declaration.game_type` and `declaration.bid_value` are required. The optional
declaration fields are:

* `hand_game`
* `ouvert`
* `schneider_announced`
* `schwarz_announced`
* `matadors`

Suit and Grand declaration dependencies use the existing canonical declaration
rules. Complete ownership deterministically infers matadors from the declarer's
initial hand plus the original skat. A supplied count must match the inferred
count. Null rejects matador, Schneider, and Schwarz metadata.

For non-Hand games, `discarded_cards` contains exactly two cards from the
declarer's initial hand plus the picked-up skat. Those cards become the final
skat, are unplayable, and count toward declarer points. For Hand games,
`discarded_cards` is empty, the original skat remains unplayed, and it still
belongs to the declarer for matador and point calculation. The record does not
claim to prove whether the declarer physically inspected the skat.

## Trick history

Only `game_end_reason: "normal_completion"` is supported. The input contains
exactly ten consecutively numbered tricks and three plays per trick:

```json
{
  "trick_number": 1,
  "leader_player_id": "player-a",
  "plays": [
    {"player_id": "player-a", "card": "CJ"},
    {"player_id": "player-b", "card": "SJ"},
    {"player_id": "player-c", "card": "HJ"}
  ]
}
```

Forehand leads the first trick. Play then follows fixed seat order:

```text
forehand -> middlehand -> rearhand -> forehand
```

The engine verifies ownership against each remaining playable hand and enforces
the existing Suit, Grand, or Null follow/trump obligations at every play. It
derives each winner and requires that winner to lead the next trick. Input does
not accept supplied winner or trick-point fields.

## Derived output

Historical input produces only `input_file` and `historical_game_summary`. The
summary contains:

* the canonical versioned `record`, including normalized declaration metadata
* ten `derived_tricks` with winner player, winner side, and trick points
* declarer and defender trick points
* applicable skat points
* final declarer and defender card points totaling 120
* the Suit/Grand card-point or Null trick-ownership winner
* `game_result_summary`
* `game_value_summary`
* `overbid_summary`
* `final_settlement_summary`

Suit/Grand overbids use the existing required-game-value and doubled-loss
settlement behavior. Overbid Null records require the separate impossible-Null
settlement workflow and are rejected by this normal-play branch.

No recommendation, simulation, local position, opponent policy, profile, list,
or training-data output is emitted for a historical game.

## CLI

Print a concise summary:

```powershell
python main.py --input examples/historical_grand_normal_completion.json
```

Write structured output without successful stdout:

```powershell
python main.py --input examples/historical_grand_normal_completion.json --output outputs/historical.json --quiet
```

Historical games accept `--input`, `--output`, and `--quiet`. Analysis,
recommendation, policy, comparison, profile, seed/sample, and simulation options
are rejected instead of being ignored.

## Remaining scope

Later work is still required for:

* claims, concessions, passed-in games, and other approved end reasons
* complete auction event history
* impossible Null historical play records
* rule-violation adjudication
* decision-by-decision replay and complete-game coaching
* training/evaluation dataset wrappers and provenance
* historical player statistics and learned models
* list, series, and tournament aggregation from historical records

Four-player tables remain out of scope.
