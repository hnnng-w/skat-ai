# Input JSON

This document describes the supported input JSON format for `skat-ai`.

## JSON schema

The input JSON schema is available at:

[`schemas/input.schema.json`](../schemas/input.schema.json)

Complete historical records use the focused referenced schema:

[`schemas/historical_game.schema.json`](../schemas/historical_game.schema.json)

The schema is intended as a documentation and validation aid.

Example files can be validated against the schema with:

```powershell
python scripts/validate_examples_schema.py
```

The project check script also runs input schema validation:

```powershell
.\scripts\check.ps1
```

The schema checks stable structural constraints such as:

* valid card notation
* maximum hand size
* maximum skat size
* maximum current-trick size
* maximum opponent hand sizes and sample count
* required array/object shapes for supplied public fields
* unique cards within individual card arrays
* card-point fields between 0 and 120
* supported analysis metadata values
* supported game-end metadata values
* supported player profile field types and numeric ranges
* supported opponent policy values
* supported performance rating values
* matador values from 1 through 11 and direct top-level Grand values through 4
* direct top-level Suit/Grand declaration contradictions

More advanced cross-field validation is handled by the Python validation layer.

Python validation covers Skat-specific rules such as:

* duplicate known cards across all known-card lists
* completed-trick sequence consistency
* completed-trick winner validation where enough metadata is available
* live-vs-post-game information rules
* game-end consistency
* legality of `actual_card_played`
* point consistency
* stable historical player/seat references and complete 32-card deals
* historical pickup/discard ownership, final playable hands, all 30 plays, follow obligations, winners, points, matadors, and settlement

For the validation-layer overview and schema limitations, see:

[Schema validation documentation](schema_validation.md)

## Input workflows

The public schema has two mutually exclusive branches:

* the existing flat position-analysis input described below
* a complete historical game under `historical_game_input`

A historical-game file contains no position fields, simulation settings,
`actual_card_played`, profiles, policies, list inputs, or impossible-Null
settlement selection:

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

See [Historical games](historical_games.md) for the complete identity, deal,
declaration, skat, play, and runtime-validation contract.

## Minimal position input

A basic input position requires:

```json
{
  "game_type": "grand",
  "player_role": "declarer",
  "player_position": "middlehand",
  "trick_leader": "right",
  "hand": ["SA", "S10", "S9"],
  "current_trick": ["S7"],
  "played_cards": [],
  "completed_tricks": [],
  "declarer_points": 0,
  "defender_points": 0,
  "next_player": "me",
  "skat": [],
  "left_hand_size": 5,
  "right_hand_size": 5,
  "sample_count": 1000,
  "random_seed": 42,
  "use_basic_opponent_strategy": true
}
```

## Core fields

| Field                         | Meaning                                                                                        |
| ----------------------------- | ---------------------------------------------------------------------------------------------- |
| `game_type`                   | One of `clubs`, `spades`, `hearts`, `diamonds`, `grand`, or `null`.                            |
| `player_role`                 | Local player role, usually `declarer` or `defender`.                                           |
| `declarer_player`             | Concrete declarer seat: `me`, `left`, `right`, or `unknown`.                                   |
| `player_position`             | Local player position such as `forehand`, `middlehand`, `rearhand`, or `unknown`.              |
| `trick_leader`                | Player who leads the current trick.                                                            |
| `hand`                        | Known local hand cards.                                                                        |
| `current_trick`               | Cards already played in the current trick.                                                     |
| `played_cards`                | Backward-compatible list of previously played cards. Prefer `completed_tricks` for new inputs. |
| `completed_tricks`            | Detailed completed trick history.                                                              |
| `declarer_points`             | Explicit declarer points already known outside completed tricks.                               |
| `defender_points`             | Explicit defender points already known outside completed tricks.                               |
| `next_player`                 | Player whose turn it is.                                                                       |
| `skat`                        | Known skat cards, if visible.                                                                  |
| `left_hand_size`              | Number of unknown cards held by the left opponent. Late-game positions may use `0`.             |
| `right_hand_size`             | Number of unknown cards held by the right opponent. Late-game positions may use `0`.            |
| `sample_count`                | Number of Monte Carlo samples.                                                                 |
| `random_seed`                 | Random seed for reproducibility.                                                               |
| `use_basic_opponent_strategy` | Whether to use basic opponent strategy.                                                        |

## Turn phase

`current_trick` is card-only. It contains the cards already played in the
current trick, in play order, but it does not contain player-card ownership.

For concrete turn phases, `trick_leader`, `len(current_trick)`, and
`next_player` must follow the fixed three-player order `me -> left -> right`:

| `trick_leader` | `len(current_trick)` | `next_player` |
| -------------- | -------------------: | ------------- |
| `me`           |                    0 | `me`          |
| `me`           |                    1 | `left`        |
| `me`           |                    2 | `right`       |
| `left`         |                    0 | `left`        |
| `left`         |                    1 | `right`       |
| `left`         |                    2 | `me`          |
| `right`        |                    0 | `right`       |
| `right`        |                    1 | `me`          |
| `right`        |                    2 | `left`        |

If both `trick_leader` and `next_player` are concrete, contradictory
combinations are rejected. If one field is concrete and the other is missing or
`unknown`, the missing or unknown counterpart is derived from the table when the
answer is deterministic.

For a non-empty `current_trick`, both `trick_leader` and `next_player` cannot be
missing or `unknown`, because the card ownership cannot be reconstructed safely.
For an empty `current_trick`, `unknown`/`unknown` remains supported for legacy,
historical, or unavailable states.

When the last completed trick provides a concrete
`completed_tricks[-1].winner_player`, that player is the leader of the following
current trick. A missing or `unknown` current `trick_leader` is normalized to
that winner. A conflicting concrete `trick_leader` is rejected. Side-only
`winner_role` values never determine a concrete leader or next player.

Immediate Analysis is available only for normalized local-action positions where
`next_player` is `me` and the game has not ended. If the normalized current actor
is `left` or `right`, the input remains valid when the phase is canonical, but
Immediate Analysis returns an unavailable recommendation instead of analyzing a
nonexistent local decision.

Multi-Step can prepare these opponent-turn phases until the local player is next:

| Starting phase | Preparation |
| -------------- | ----------- |
| `trick_leader = left`, empty `current_trick`, `next_player = left` | Simulate left lead and right response. |
| `trick_leader = right`, empty `current_trick`, `next_player = right` | Simulate right lead. |
| `trick_leader = left`, one-card `current_trick`, `next_player = right` | Preserve the lead card and simulate only right's response. |

Valid phases where the local player has already acted and only an opponent action
remains are not automatically completed. Multi-Step stops with
`unsupported_turn_phase` and leaves the state unchanged for those phases.

## Declarer identity

`player_role` describes the local player's side. `declarer_player` identifies the concrete player who declared the game.

Valid combinations are:

| `player_role` | `declarer_player` input | Normalized meaning |
| ------------- | ----------------------- | ------------------ |
| `declarer`    | missing                 | `me`               |
| `declarer`    | `me`                    | `me`               |
| `defender`    | `left`                  | declarer is left, local defender partner is right |
| `defender`    | `right`                 | declarer is right, local defender partner is left |
| `unknown`     | missing                 | `unknown`          |
| `unknown`     | `unknown`               | `unknown`          |

Invalid combinations are rejected. In particular, defender inputs must provide `declarer_player` as `left` or `right`. The engine does not infer `declarer_player` from completed tricks, trick leaders, player positions, hand sizes, player profiles, or seating heuristics.

## Card notation

Cards are represented as short strings.

Suits:

| Suit | Meaning  |
| ---- | -------- |
| `C`  | Clubs    |
| `S`  | Spades   |
| `H`  | Hearts   |
| `D`  | Diamonds |

Ranks:

```text
A, 10, K, Q, J, 9, 8, 7
```

Examples:

```text
SA = Ace of Spades
H10 = Ten of Hearts
CJ = Jack of Clubs
```

## Game declaration fields

Game declaration fields describe the announced game.

The project supports backward-compatible top-level declaration fields:

```json
{
  "game_type": "grand",
  "hand_game": false,
  "ouvert": false,
  "schneider_announced": false,
  "schwarz_announced": false,
  "matadors": 2,
  "bid_value": 72
}
```

The project also supports nested declaration metadata:

```json
{
  "game_declaration": {
    "hand_game": false,
    "ouvert": false,
    "schneider_announced": false,
    "schwarz_announced": false,
    "matadors": 2,
    "bid_value": 72
  }
}
```

Both forms are supported for the same fields. If both forms provide the same
field, the explicit top-level field overrides the nested `game_declaration`
field. Mixing forms is supported for compatibility, but using one form is
clearer.

| Field                 | Meaning                                                       |
| --------------------- | ------------------------------------------------------------- |
| `hand_game`           | Whether the game was announced as a hand game.                |
| `ouvert`              | Whether the game was announced as ouvert.                     |
| `schneider_announced` | Whether Schneider was announced.                              |
| `schwarz_announced`   | Whether Schwarz was announced.                                |
| `matadors`            | Matador count for suit and grand games.                       |
| `bid_value`           | Optional bid value used for overbid detection and settlement. |

Boolean declaration fields must be JSON booleans. Explicit `false` values are
preserved and override nested `true` values. Boolean `null` is invalid.

Suit and Grand declaration levels are hierarchical. The effective declaration
is normalized after top-level-over-nested precedence is applied:

* `schneider_announced: true` implies `hand_game: true`.
* `schwarz_announced: true` implies `schneider_announced: true` and
  `hand_game: true`.
* `ouvert: true` implies `schwarz_announced: true`,
  `schneider_announced: true`, and `hand_game: true`.

An omitted prerequisite is added as `true` to the canonical declaration. An
explicit `false` prerequisite is a contradiction and is rejected instead of
being overwritten. This applies equally to nested, top-level, and mixed inputs
after the documented precedence rules are resolved.

`matadors` uses this resolution order: non-null top-level `matadors`, non-null
nested `game_declaration.matadors`, safe deterministic inference, then `null`.
Explicit Suit values must be from `1` through `11`; explicit Grand values must
be from `1` through `4`. Zero is invalid. `matadors: null` means the count is
unknown and the field is missing for precedence and inference purposes.

`bid_value` uses this resolution order: non-null top-level `bid_value`, non-null
nested `game_declaration.bid_value`, then `null`. It must be a positive integer
when provided. `bid_value: null` means the bid value is unknown.

Null declarations use `game_type: "null"` plus `hand_game` and `ouvert` to
represent Null, Null Hand, Null Ouvert, and Null Ouvert Hand. Null games do not
use `matadors`, `schneider_announced`, or `schwarz_announced`; those combinations
are rejected by runtime validation. Null `ouvert` and Null Hand are independent:
`ouvert: true` does not imply `hand_game: true` for a Null game.

### Impossible Null settlement selection

An impossible Null declaration can optionally record the externally selected
Suit or Grand game used only for settlement:

```json
{
  "game_end_reason": "impossible_null_declaration",
  "impossible_null_settlement": {
    "replacement_game_type": "clubs",
    "matadors": 1
  }
}
```

`replacement_game_type` accepts `clubs`, `spades`, `hearts`, `diamonds`, or
`grand`. Both fields are required when the object is present. Suit matadors must
be `1..11`; Grand matadors must be `1..4`; zero, booleans, Null, missing fields,
and unknown fields are rejected.

This object is separate from `game_declaration`. The original declaration stays
Null and does not receive matadors. The replacement inherits `hand_game` from
the original Null skat-pickup status, but Null `ouvert`, Schneider announced,
and Schwarz announced are not transferred. The selection is supplied by an
online result, historical import, manual record, or adjudication; `skat-ai` does
not optimize across alternatives whose contract-specific matador counts are
unknown.

Automatic matador inference can use known declarer-card context from:

* the local declarer `hand`
* `skat`, when available and allowed by the analysis mode
* `completed_tricks`, but only from tricks that provide both `cards` and ordered `players`, and only when `declarer_player` is concrete

Completed-trick ownership inference is intentionally conservative:

* It maps each completed-trick card to declarer or non-declarer ownership from the paired `cards`, ordered `players`, and concrete `declarer_player` entries.
* It can use completed-trick ownership from declarer or defender perspective when the concrete declarer seat is known.
* It does not infer ownership from `winner_role`, `winner_player`, or trick winner alone.
* It does not infer completed-trick ownership when `declarer_player` is missing or `unknown`.
* It does not guess hidden cards.
* If completed-trick ownership is incomplete or inconclusive, inference falls back only to deterministic known-card behavior.

If matadors still cannot be inferred for a suit or grand game, the game value may remain incomplete.

For Suit and Grand games, the canonical hierarchy makes declaration levels
cumulative: Hand adds one level; Schneider announced includes Hand and adds two
levels; Schwarz announced includes Schneider announced and Hand and adds three
levels; ouvert includes all three prerequisites and adds four levels.

## Analysis metadata fields

Input files may include optional analysis metadata:

```json
{
  "analysis_mode": "live_decision",
  "skat_visibility": "unknown",
  "game_end_reason": "not_ended"
}
```

Supported `analysis_mode` values:

| Value              | Meaning                 |
| ------------------ | ----------------------- |
| `live_decision`    | Live decision state.    |
| `post_game_review` | Post-game review state. |

Supported `skat_visibility` values:

| Value                 | Meaning                                           |
| --------------------- | ------------------------------------------------- |
| `unknown`             | Skat is not visible.                              |
| `known_to_declarer`   | Skat is known only to the declarer during play.   |
| `known_post_game`     | Skat is known for post-game review.               |

Supported `game_end_reason` values:

| Value                                 | Meaning                                                |
| ------------------------------------- | ------------------------------------------------------ |
| `not_ended`                           | Game is still in progress.                             |
| `normal_completion`                   | Game ended normally with all 120 card points assigned. |
| `declarer_claimed_remaining_tricks`   | Declarer claimed the remaining tricks.                 |
| `declarer_conceded_remaining_tricks`  | Declarer conceded the remaining tricks.                |
| `defenders_conceded_remaining_tricks` | Defenders conceded the remaining tricks.               |
| `impossible_null_declaration`          | Impossible Null declaration; immediate declarer loss.   |

`impossible_null_declaration` is post-game only. It requires a Null contract,
a bid above the fixed value of the declared Null variant, no played cards,
empty current and completed tricks, and zero assigned card points. The
replacement object may be omitted; the loss is then known but settlement stays
incomplete.

## Player profile fields

Input files may include optional left/right player profiles:

```json
{
  "left_player_profile": {
    "games_played": 860,
    "solo_rate": 0.2,
    "grand_rate": 0.13,
    "hand_game_rate": 0.03,
    "defender_win_rate": 0.56
  },
  "right_player_profile": {
    "games_played": 720,
    "solo_rate": 0.42,
    "grand_rate": 0.28,
    "hand_game_rate": 0.11,
    "defender_win_rate": 0.48
  }
}
```

Supported profile fields:

| Field                   | Validation                      | Current policy use                                      |
| ----------------------- | ------------------------------- | ------------------------------------------------------- |
| `games_played`          | Non-negative integer.           | Derives rough profile confidence.                       |
| `solo_games_played`     | Non-negative integer.           | Informational only.                                     |
| `defender_games_played` | Non-negative integer.           | Informational only.                                     |
| `solo_rate`             | Number between `0` and `1`.     | Aggressive-profile signal at `0.35` or higher.          |
| `solo_win_rate`         | Number between `0` and `1`.     | Informational only.                                     |
| `hand_game_rate`        | Number between `0` and `1`.     | Aggressive-profile signal at `0.10` or higher.          |
| `suit_game_rate`        | Number between `0` and `1`.     | Informational only.                                     |
| `grand_rate`            | Number between `0` and `1`.     | Aggressive-profile signal at `0.25` or higher.          |
| `null_game_rate`        | Number between `0` and `1`.     | Informational only.                                     |
| `defender_win_rate`     | Number between `0` and `1`.     | Cautious-defender signal at `0.52` or higher with enough confidence and no aggressive signal. |

Profile confidence is derived from `games_played` only:

| `games_played` value | Confidence |
| -------------------- | ---------- |
| Missing              | `unknown`  |
| `0` to `99`          | `low`      |
| `100` to `499`       | `medium`   |
| `500` or more        | `high`     |

When `use_profile_presets` is enabled, profile-derived presets can affect opponent policy settings only when the derived profile confidence makes the preset actionable. Unknown confidence, low confidence, and neutral profiles that map to `simple_lowest` do not overwrite existing explicit or default policies. Medium- or high-confidence profiles that map to existing non-simple presets such as `aggressive_points` or `cautious_defender` can be applied. If cautious and aggressive actionable profile-derived presets conflict, the higher-confidence side wins. If both conflicting sides have equal confidence, `aggressive_points` remains the fallback over `cautious_defender` for backward-compatible behavior.

When a player profile is supplied, it must be a JSON object. Explicit `null` is
not accepted for `left_player_profile`, `right_player_profile`, or known profile
fields such as `games_played`. Unknown extra profile fields remain accepted as
metadata.

Left and right actionable profile presets affect their respective effective left/right policies in immediate analysis and multi-step simulation. `simple_lowest` remains an informational profile recommendation, not an active profile-derived override. Explicit side-specific input and CLI overrides remain authoritative.

## Live vs post-game information rules

The project separates live decision analysis from post-game review.

`live_decision` is intended for in-game decisions and must not use post-game-only information.

`post_game_review` is intended for completed or retrospectively analyzed games.

Important validation rules:

* `analysis_mode = "live_decision"` cannot use `skat_visibility = "known_post_game"`.
* `analysis_mode = "live_decision"` can include concrete Skat cards only with `skat_visibility = "known_to_declarer"`.
* With `skat_visibility = "known_to_declarer"`, declarer analysis may use the supplied Skat cards, while defender analysis validates them and then redacts them from the local analysis view.
* `skat_visibility = "unknown"` cannot include concrete Skat cards in `skat`.
* `skat_visibility = "known_to_declarer"` and `skat_visibility = "known_post_game"` require either zero or two concrete Skat cards.
* `skat` must be an array and can contain at most two cards.
* `game_end_reason` values other than `not_ended` require `analysis_mode = "post_game_review"`.
* `analysis_mode = "live_decision"` cannot describe a completed game with all 120 card points assigned.
* In `live_decision`, completed-trick winner metadata such as `winner_player` or `winner_role` must be verifiable.
* In `live_decision`, `winner_role` is accepted only when the winning side can be derived from `cards`, `players`, `game_type`, and concrete `declarer_player`.
* In `live_decision`, completed tricks with `winner_role` but without `players` are rejected.
* In `live_decision`, completed tricks with `players` are rejected if `winner_role` contradicts the rule-derived winner side or if the winner side cannot be derived.

Examples:

```json
{
  "analysis_mode": "live_decision",
  "skat_visibility": "known_to_declarer",
  "game_end_reason": "not_ended",
  "skat": ["C7", "D8"]
}
```

```json
{
  "analysis_mode": "live_decision",
  "skat_visibility": "unknown",
  "game_end_reason": "not_ended"
}
```

```json
{
  "analysis_mode": "post_game_review",
  "skat_visibility": "known_post_game",
  "game_end_reason": "normal_completion",
  "skat": ["C7", "D8"]
}
```

## Post-game review fields

Post-game review can include the optional `actual_card_played` field.

Example:

```json
{
  "analysis_mode": "post_game_review",
  "skat_visibility": "known_post_game",
  "actual_card_played": "C7"
}
```

| Field                | Meaning                                                     |
| -------------------- | ----------------------------------------------------------- |
| `actual_card_played` | The card that was actually played in the analyzed position. |

Validation rules:

* `actual_card_played` is optional.
* If provided, it must be valid card notation.
* If provided, it must be in the local player's known `hand`.
* If provided, it must be legal in the analyzed position.
* `actual_card_played` is intended for `post_game_review`.

When `actual_card_played` is provided, the output contains a `post_game_review_summary` comparing the actual card with the recommended card.

## Performance rating fields

Input files may optionally include:

```json
{
  "performance_rating_system": "isko_list"
}
```

Supported values:

| Value         | Meaning                                                                               |
| ------------- | ------------------------------------------------------------------------------------- |
| `placeholder` | Generic placeholder rating system.                                                    |
| `isko_list`   | Partially implemented SkWO-style performance scoring for the fixed three-player table. |

If omitted, `performance_rating_summary.rating_system` is `null`.

The project assumes a fixed three-player table. There is no supported public `table_size` input field. A top-level `table_size`, if supplied as extra metadata, is ignored by rating logic and should not be used for workflow configuration.

Input files may also include already aggregated list or series totals:

```json
{
  "performance_rating_system": "isko_list",
  "list_performance_input": {
    "player_game_points": 120,
    "own_games_won": 3,
    "own_games_lost": 1,
    "other_players_lost_games": 2
  }
}
```

Fields:

| Field                       | Meaning                                                               |
| --------------------------- | --------------------------------------------------------------------- |
| `player_game_points`        | Already aggregated game points for the rated player. May be negative. |
| `own_games_won`             | Count of the rated player's won own games.                            |
| `own_games_lost`            | Count of the rated player's lost own games.                           |
| `other_players_lost_games`  | Count of lost games by the other two players.                         |

Validation rules:

* `list_performance_input` is optional.
* If provided, `performance_rating_system` must be `isko_list`.
* All four fields are required and must be integers.
* `player_game_points` may be negative, zero, or positive.
* The three game counters must be non-negative.
* `table_size` is fixed at `3`. Do not include `table_size` inside `list_performance_input`; a top-level `table_size`, if supplied as extra metadata, is ignored and is not part of the supported public contract.
* Raw individual games are not aggregated in this input mode.

As an alternative to already aggregated totals, input files may include
normalized per-game list or series contributions:

```json
{
  "performance_rating_system": "isko_list",
  "list_game_contributions": [
    {
      "player_role": "declarer",
      "game_outcome": "declarer_win",
      "settlement_score": 96
    },
    {
      "player_role": "defender",
      "game_outcome": "declarer_loss",
      "settlement_score": -144
    }
  ]
}
```

Contribution fields:

| Field              | Meaning                                                            |
| ------------------ | ------------------------------------------------------------------ |
| `player_role`      | Rated player's role in that game: `declarer` or `defender`.        |
| `game_outcome`     | Declarer's game outcome: `declarer_win` or `declarer_loss`.        |
| `settlement_score` | Declarer's single-game settlement score before performance points. |
| `rated_player_id`  | Optional opaque stable identifier for the rated player.            |
| `game_id`          | Optional opaque stable identifier for the game.                    |

Validation rules:

* `list_game_contributions` is optional.
* If provided, `performance_rating_system` must be `isko_list`.
* It must be an array. An empty array is valid.
* Each contribution must contain `player_role`, `game_outcome`, and `settlement_score`.
* Each contribution may also contain `rated_player_id` and `game_id`.
* Other additional contribution fields are rejected.
* `player_role` must be `declarer` or `defender`.
* `game_outcome` must be `declarer_win` or `declarer_loss`.
* `settlement_score` must be an integer.
* `declarer_win` requires a positive `settlement_score`.
* `declarer_loss` requires a negative `settlement_score`.
* `rated_player_id` and `game_id`, when supplied, must be non-empty strings without leading or trailing whitespace.
* Identifiers are opaque and case-sensitive. They are not lowercased, uppercased, trimmed, parsed, inferred, or generated.
* If any contribution supplies `rated_player_id`, every contribution must supply the same `rated_player_id`.
* Partial `rated_player_id` presence is rejected because same-player verification would be ambiguous.
* `game_id` may be supplied for all, some, or no contributions.
* Duplicate supplied `game_id` values are rejected. Duplicate detection applies only to supplied IDs.
* Identifiers are input validation metadata only and are not echoed in output summaries.
As another alternative, input files may include explicit fixed three-player list
standings input:

```json
{
  "performance_rating_system": "isko_list",
  "list_standings_input": {
    "players": [
      {"player_id": "alice", "player_label": "Alice"},
      {"player_id": "bob", "player_label": "Bob"},
      {"player_id": "carol", "player_label": "Carol"}
    ],
    "games": [
      {
        "game_id": "game-1",
        "declarer_player_id": "alice",
        "game_outcome": "declarer_win",
        "settlement_score": 96
      }
    ],
    "lot_order": ["carol", "bob"]
  }
}
```

Standings input fields:

| Field                         | Meaning                                                    |
| ----------------------------- | ---------------------------------------------------------- |
| `players[].player_id`         | Required stable player identifier.                         |
| `players[].player_label`      | Optional display label.                                    |
| `games[].game_id`             | Optional stable game identifier.                           |
| `games[].declarer_player_id`  | Declarer player identifier for the game.                   |
| `games[].game_outcome`        | `declarer_win` or `declarer_loss`.                         |
| `games[].settlement_score`    | Declarer's settlement score before performance bonuses.    |
| `lot_order`                   | Optional externally determined best-to-worst lot order.    |

Validation rules:

* exactly three players are required
* player IDs must be unique non-empty strings without leading or trailing whitespace
* player labels are optional non-empty strings without leading or trailing whitespace
* `games` may be empty
* every `declarer_player_id` must reference one of the declared players
* `declarer_win` requires a positive `settlement_score`
* `declarer_loss` requires a negative `settlement_score`
* supplied `game_id` values must be unique
* `lot_order`, when supplied, must be an array of two or three unique declared player IDs
* `lot_order` must contain exactly every player in the one tie group remaining after total performance points, own wins, and own losses are compared
* omitted tied players, unknown players, players outside the tie, and a lot result supplied without an unresolved tie are rejected
* the engine does not execute a random lot; `lot_order` only records an externally executed decision
* `list_standings_input` emits `list_standings_summary`, not `list_performance_summary`

Existing single-rated-player modes do not emit standings because they do not
safely describe all three player identities and totals.

The standings formula and tie handling follow SkWO 6.3.1. The public
`performance_rating_system: "isko_list"` identifier remains unchanged for
compatibility. Without a valid external `lot_order`, an official tie remains
unresolved and the resulting standings are not final.

* `list_performance_input`, `list_game_contributions`, `list_analysis_results`, and `list_standings_input` are alternative input modes and cannot be combined.
* `table_size` is fixed at `3`. There is no supported `table_size` input for this mode; a top-level `table_size`, if supplied as extra metadata, is ignored.

As another alternative, input files may include already-built local analysis
results. Each entry is assumed to represent the same rated player as local
`me`; the project does not validate stable player identities across entries.

```json
{
  "performance_rating_system": "isko_list",
  "list_analysis_results": [
    {
      "position": {
        "player_role": "declarer"
      },
      "final_settlement_summary": {
        "is_complete": true,
        "is_loss": false,
        "settlement_score": 96
      }
    },
    {
      "position": {
        "player_role": "defender"
      },
      "final_settlement_summary": {
        "is_complete": true,
        "is_loss": true,
        "settlement_score": -144
      }
    }
  ]
}
```

Required analysis-result subset:

| Field                                             | Meaning                                                            |
| ------------------------------------------------- | ------------------------------------------------------------------ |
| `rated_player_id`                                 | Optional opaque stable identifier for the rated player.            |
| `game_id`                                         | Optional opaque stable identifier for the game.                    |
| `position.player_role`                            | Rated player's local role: `declarer`, `defender`, or `unknown`.   |
| `final_settlement_summary.is_complete`            | Whether the settlement is complete.                                |
| `final_settlement_summary.is_loss`                | Required only for complete settlements.                            |
| `final_settlement_summary.settlement_score`       | Required only for complete settlements.                            |

Validation rules:

* `list_analysis_results` is optional.
* If provided, `performance_rating_system` must be `isko_list`.
* It must be an array. An empty array is valid.
* Each item must be an object with `position` and `final_settlement_summary` objects.
* Additional fields are accepted on each item, on `position`, and on `final_settlement_summary`, so complete generated analysis-result objects can be supplied.
* Complete output objects are accepted as supersets, but the input schema does not embed the full output schema.
* `final_settlement_summary.is_complete` must be a boolean.
* If `is_complete` is `false`, the result is valid and skipped for list aggregation.
* If `is_complete` is `true`, `is_loss` must be a boolean and `settlement_score` must be an integer.
* `is_loss: false` requires a positive `settlement_score`.
* `is_loss: true` requires a negative `settlement_score`.
* Results with `position.player_role: "unknown"` are skipped.
* Malformed results are rejected and include the list index in validation errors.
* `rated_player_id` and `game_id` are optional top-level fields on each list entry, not fields inside `position` or `final_settlement_summary`.
* `rated_player_id` and `game_id`, when supplied, must be non-empty strings without leading or trailing whitespace.
* Identifiers are opaque and case-sensitive. They are not lowercased, uppercased, trimmed, parsed, inferred, or generated.
* No identity is inferred from `me`, `left`, `right`, `player_role`, `player_position`, `trick_leader`, display names, or player profiles.
* If any analysis result supplies `rated_player_id`, every analysis result must supply the same `rated_player_id`.
* Partial `rated_player_id` presence is rejected because same-player verification would be ambiguous.
* `game_id` may be supplied for all, some, or no analysis results.
* Duplicate supplied `game_id` values are rejected. Duplicate detection applies only to supplied IDs.
* Identical content without `game_id` is not treated as a duplicate. Identical content with different `game_id` values is valid. Different content with the same `game_id` is rejected.
* Identifiers are input validation metadata only and are not echoed in output summaries.
* `list_performance_input`, `list_game_contributions`, `list_analysis_results`, and `list_standings_input` are mutually exclusive.

Already aggregated `list_performance_input` cannot support game-level duplicate detection because per-game records are no longer present. A future player label could be added for aggregated totals, but issue #29 duplicate protection applies only to per-game input modes.

## Opponent policy fields

Input files can define opponent card-selection policies.

Global opponent policy fields are backward-compatible and apply as defaults:

```json
{
  "opponent_lead_policy": "lowest_point",
  "opponent_response_policy": "lowest_point"
}
```

Supported opponent card policies:

Policy values are canonical, exact, and case-sensitive. The runtime does not accept aliases or perform case normalization.

| Value                     | Meaning                               |
| ------------------------- | ------------------------------------- |
| `lowest_point`            | Choose the lowest-point legal card.   |
| `highest_point`           | Choose the highest-point legal card.  |
| `random_legal`            | Choose a random legal card.           |
| `basic_trick_play`        | Use basic trick-play behavior.        |
| `basic_defender_lead`     | Use a cautious defender lead policy.  |
| `basic_defender_response` | Use a basic defender response policy. |

Named presets can set both lead and response policies:

```json
{
  "opponent_policy_preset": "cautious_defender"
}
```

Supported opponent policy presets:

| Value                | Lead policy             | Response policy             |
| -------------------- | ----------------------- | --------------------------- |
| `simple_lowest`      | `lowest_point`          | `lowest_point`              |
| `cautious_defender`  | `basic_defender_lead`   | `basic_defender_response`   |
| `aggressive_points`  | `highest_point`         | `highest_point`             |
| `random`             | `random_legal`          | `random_legal`              |

Preset values are also exact and case-sensitive. Aliases and normalized casing are not supported.

The project also supports separate left/right opponent policy fields:

```json
{
  "left_opponent_lead_policy": "highest_point",
  "left_opponent_response_policy": "basic_trick_play",
  "right_opponent_lead_policy": "basic_defender_lead",
  "right_opponent_response_policy": "basic_defender_response"
}
```

Effective policy behavior:

* Global presets and global lead/response policies cascade to both `left` and `right`.
* Left/right fields override only their side.
* Actionable profile-derived policies affect only their side when `use_profile_presets` is enabled.
* CLI policy overrides use the same resolver as input fields, and side-specific CLI overrides win last.

Multi-step behavior:

* If `right` leads, the engine uses `right_opponent_lead_policy`.
* If `left` leads, the engine uses `left_opponent_lead_policy`.
* If `left` leads and `right` responds, the engine uses `right_opponent_response_policy`.
* Candidate trick completion uses activated side response policies when an explicit response source exists.

Global policy fields remain supported for backward compatibility.

Immediate candidate analysis starts with the local candidate card and only simulates remaining opponent responses. It does not simulate a new opponent lead. Opponent lead policies are used during multi-step opponent-turn preparation.

Immediate response-policy behavior is activated only by explicit policy sources:

* `opponent_policy_preset`
* `opponent_response_policy`
* `left_opponent_response_policy`
* `right_opponent_response_policy`
* `use_profile_presets: true`
* relevant CLI overrides

Absent fields normalized to defaults, `use_profile_presets: false`, lead-only policy sources, and player profiles without enabled actionable profile presets do not activate policy-driven immediate analysis or multi-step candidate completion. In those cases, those paths keep the legacy basic or random opponent response behavior from `use_basic_opponent_strategy`.

Shared policy precedence, from lowest to highest, is:

1. built-in lowest-point defaults
2. input global policy preset
3. explicit input global lead and response policies
4. input-activated profile-derived side policies
5. explicit input side lead and response policies
6. global CLI policy preset
7. CLI-activated profile-derived side policies
8. explicit global CLI lead and response policies
9. explicit side-specific CLI lead and response policies

Response-policy activation uses the same order but only response-bearing sources activate the sparse response map:

1. input global policy preset
2. explicit input global response policy
3. input-activated profile-derived side response policies
4. explicit input side response policies
5. global CLI policy preset
6. CLI-activated profile-derived side response policies
7. explicit global CLI response policy
8. explicit side-specific CLI response policies

Global presets and global response policies apply to both `left` and `right`. Profile-derived policies and side-specific response policies affect only their side. The activated response-policy map is sparse, so an explicit left-side policy alone does not populate a right-side default entry.

## Completed tricks

The preferred way to record completed tricks is `completed_tricks`.

A detailed completed trick can include:

```json
{
  "cards": ["CJ", "SJ", "DJ"],
  "players": ["me", "left", "right"],
  "winner_role": "declarer",
  "winner_player": "me"
}
```

For input, every completed-trick entry requires `cards` and `winner_role`. The `players` and `winner_player` fields remain optional for backward-compatible partial histories.

Validation rules:

* `cards` must contain exactly three cards.
* `winner_role` is required and must be `declarer` or `defenders`.
* `players` must contain exactly three unique players when provided.
* Completed-trick entries reject unsupported keys; supported keys are `cards`, `players`, `winner_role`, and `winner_player`.
* Input trick players are `me`, `left`, or `right`; `unknown` is not accepted inside `completed_tricks[].players` or `completed_tricks[].winner_player`.
* `players` must follow the known seating order:

  * `["me", "left", "right"]`
  * `["left", "right", "me"]`
  * `["right", "me", "left"]`
* `winner_player` must be valid when provided.
* `winner_role` is checked against `winner_player` when concrete declarer identity allows safe side ownership resolution.
* The winner of one completed trick must lead the next completed trick.
* If `current_trick` is not empty, `trick_leader` must match the winner of the last completed trick.
* When `cards` and `players` are provided, the engine derives the actual trick winner according to the implemented Skat rules.
* When `winner_player` is provided with `cards` and `players`, it must match the derived trick winner.
* When `winner_role` is provided with `cards`, `players`, and concrete declarer identity, it must match the derived winner side even if `winner_player` is omitted.
* In `live_decision`, `winner_role` must be verifiable from `cards`, `players`, `game_type`, and concrete `declarer_player`; unverifiable or contradictory live `winner_role` values are rejected.

Older completed-trick entries without `players` or `winner_player` remain supported, but they cannot be checked as strictly. Existing explicit `winner_role` values remain accepted as side-level facts unless concrete `players` plus declarer identity, or concrete `winner_player` plus declarer identity, prove a conflict.

For matador inference, completed tricks contribute ownership facts only when `cards`, ordered `players`, and concrete `declarer_player` are present. `winner_role`, `winner_player`, and trick winner alone are not used to infer matador ownership.

Basic structural schema acceptance does not require ten completed tricks. Ten reliable trick owners are required only for particular final-result features, such as completed Null contract derivation and Schwarz settlement reliability.

## Validation rules

Input validation rejects:

* invalid game types
* invalid card notation
* explicit `null` or non-array values for card-array fields
* hands with more than 10 cards
* negative opponent hand sizes
* opponent hand sizes above 10
* sample counts above 100000
* duplicate known cards
* invalid completed-trick structures
* unsupported completed-trick keys
* invalid completed-trick winner metadata
* inconsistent completed-trick sequence
* negative point values
* known card points above 120
* unknown `game_end_reason`
* inconsistent `game_end_reason` and remaining card points
* invalid `bid_value`
* contradictory Suit or Grand declaration prerequisites
* zero or out-of-range explicit matador values
* Null declarations with Schneider, Schwarz, or matador values
* unknown `performance_rating_system`
* invalid `list_performance_input`
* invalid `list_standings_input`
* invalid opponent policy values
* invalid live-vs-post-game information combinations
* known Skat cards in live decision mode unless `skat_visibility = "known_to_declarer"`
* ended game reasons outside post-game review mode
* complete 120-point game states in live decision mode
* invalid or illegal `actual_card_played`
* impossible Null metadata outside `impossible_null_declaration`
* impossible Null reasons with live mode, a non-Null contract, an absent or
  insufficient bid, played cards/tricks, or assigned card points
* incomplete, unknown, or out-of-range impossible Null replacement fields
