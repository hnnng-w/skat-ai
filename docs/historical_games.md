# Historical games

`skat-ai` supports a separate versioned workflow for three-player games that
ended through normal play or a bounded declarer or defender concession. It validates the
initial 32-card deal, final declaration, skat handling, every supplied play,
result, and settlement. All supported endings can reconstruct a local
`me`/`left`/`right` information view immediately before every actual play.

Historical-game representation remains `partially_supported`. The bounded
decision workflow reviews actual plays and can be wrapped by the
separate training-dataset workflow. Base historical output also supports
declarer concession under ISkO 4.4.1 and 4.4.2 or defender concession under
ISkO 4.4.3, but it does not provide
ouvert-aware recommendation simulation,
other claims/concessions, full auction events, player
statistics directly from one historical-game invocation, or list/tournament
aggregation. A timestamped collection wrapped by the training-dataset workflow
can separately produce bounded historical player statistics. Direct snapshot
output remains a state-reconstruction record rather than a training record.
The same timestamped dataset container can also evaluate rolling profile-policy
behavior, but only in its separate sample-free mode; it does not turn one
historical-game invocation into a recommendation or policy evaluation.

## Public input

The top-level input contains only `historical_game_input`:

```json
{
  "historical_game_input": {
    "schema_version": 1,
    "game_id": "game-001",
    "played_at": "2026-07-24T18:30:00+02:00",
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

`played_at` is optional and means the instant when the game began. When present,
it must be RFC 3339 with an explicit offset and is preserved without rewriting.
It becomes required only when external profiles are applied to historical
review or when the game is partition-selected for reusable historical opponent-
statistics aggregation; existing timestamp-free version-1 games remain valid
otherwise.

Exactly three players are required, with unique IDs and exactly one each of
`forehand`, `middlehand`, and `rearhand`. Every player supplies ten unique cards;
the original skat supplies two. The three hands and skat must equal the standard
32-card deck exactly.

The focused structural schema is
[`schemas/historical_game.schema.json`](../schemas/historical_game.schema.json).
Its historical game-end union references strict version-1 declarer- and
defender-concession event schemas.
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

Normal completion keeps its original contract: no `game_end`, exactly ten
consecutively numbered tricks, three plays per trick, and all 30 playable cards:

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

`game_end_reason: "declarer_concession"` requires a matching version-1
`game_end` and changes `tricks` to an exact legal prefix. The prefix may be empty,
may contain zero through nine complete tricks, and may end with one incomplete
trick of one or two plays. Only the final trick may be incomplete. Replay derives
exact remaining hands and the next player without inferring unplayed cards. See
[Historical declarer concessions](historical_declarer_concessions.md).

`game_end_reason: "defender_concession"` uses the same exact prefix and requires
one stable conceding defender ID plus one supported structured form. One defender
binds both defenders without partner consent. See
[Historical defender concessions](historical_defender_concessions.md).

## Derived output

Historical input produces only `input_file` and `historical_game_summary`. The
summary contains:

* the canonical versioned `record`, including normalized declaration metadata
* optional preserved game-start `played_at`
* `derived_tricks` with winner player, winner side, and trick points for each completed trick
* declarer and defender trick points
* applicable skat points
* normal final points totaling 120, or concession observed/unresolved accounting totaling 120 without assignment
* the Suit/Grand card-point or Null trick-ownership winner
* `game_result_summary`
* `game_value_summary`
* `overbid_summary`
* `final_settlement_summary`

Suit/Grand overbids use the existing required-game-value and doubled-loss
settlement behavior. Overbid Null records require the separate impossible-Null
settlement workflow and are rejected by this normal-play branch.

Base historical output emits no recommendation, simulation, local position,
opponent policy, profile, list, or training-data output.

Concession output additionally contains `play_prefix_summary`, optional
`incomplete_current_trick`, `point_accounting`, and
`historical_game_end_summary`. It exposes derived remaining hand sizes but not
the reconstructed remaining card lists.

With `--historical-decision-snapshots`, the summary additionally contains an
optional `decision_snapshot_summary` with one chronological pre-play
states. The actual card is a retrospective label outside the visible state.
Snapshot hands, legal cards, prior tricks, point state, hand sizes, skat
knowledge, matadors, and ouvert exposure follow the acting player's decision-time
information boundary. See
[Historical decision snapshots](historical_decision_snapshots.md).

With `--historical-game-review`, the summary additionally contains
`historical_game_review_summary`. Every actual snapshot is evaluated through the
existing immediate recommendation and post-game review logic. Final result and
settlement fields remain beside the review but do not influence it. See
[Historical game review](historical_game_review.md).

## CLI

Print a concise summary:

```powershell
python main.py --input examples/historical_grand_normal_completion.json
```

Print a declarer-concession summary:

```powershell
python main.py --input examples/historical_grand_declarer_concession.json
```

Print a defender-concession summary:

```powershell
python main.py --input examples/historical_grand_defender_concession.json
```

Write structured output without successful stdout:

```powershell
python main.py --input examples/historical_grand_normal_completion.json --output outputs/historical.json --quiet
```

Generate decision snapshots:

```powershell
python main.py --input examples/historical_grand_normal_completion.json --historical-decision-snapshots
```

Review every historical decision:

```powershell
python main.py --input examples/historical_grand_normal_completion.json --historical-game-review --samples 100 --seed 42
```

Apply pre-game external profiles by stable participant ID:

```powershell
python main.py --input examples/historical_grand_normal_completion.json --historical-game-review --opponent-statistics-file examples/historical_opponent_statistics.json --use-profile-presets --samples 20 --seed 42
```

Historical games accept `--input`, `--output`, `--quiet`, and the optional
snapshot and review flags. `--samples` and `--seed` are accepted only with
historical review. External statistics, profile-preset opt-in, and existing
global or side policy precedence are accepted only for profile-enabled review.
Live left/right binding IDs, comparison, and multi-step options are rejected.
See [Historical opponent profiles](historical_opponent_profiles.md).
Both concession records also accept snapshot, review, external-profile,
review-policy, sample, and seed options. The terminal event itself is not a card
decision. Dataset-level statistics aggregation, export, and rolling evaluation
support normal completion, declarer concession, and defender concession; rolling targets use only
actual plays. See
[Shortened historical opponent workflows](shortened_historical_opponent_workflows.md).

## Remaining scope

Later work is still required for:

* claims, card exposure/open play/throwing, passed-in games, and other approved end reasons
* complete auction event history
* impossible Null historical play records
* rule-violation adjudication
* exposed-card-aware ouvert simulation and complete-game coaching
* unbounded player-statistics history, weighting, merging, multiple captures, policy-effect evaluation, and learned models
* list, series, and tournament aggregation from historical records

Four-player tables remain out of scope.

Supported historical records can be wrapped with provenance and explicit
partitions by the separate [training data](training_data.md) workflow. That
workflow uses snapshots rather than historical review, so ouvert records remain
valid and no recommendation simulation is invoked.
The same dataset wrapper can instead aggregate exact per-player statistics from
selected timestamped games without generating samples. See
[Historical opponent statistics](historical_opponent_statistics.md).
