# Input JSON

This document describes the supported input JSON format for `skat-ai`.

## JSON schema

The input JSON schema is available at:

[`schemas/input.schema.json`](../schemas/input.schema.json)

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
* unique cards within individual card arrays
* card-point fields between 0 and 120
* supported analysis metadata values
* supported game-end metadata values
* supported opponent policy values
* supported performance rating values

More advanced cross-field validation is handled by the Python validation layer.

Python validation covers Skat-specific rules such as:

* duplicate known cards across all known-card lists
* completed-trick sequence consistency
* completed-trick winner validation where enough metadata is available
* live-vs-post-game information rules
* game-end consistency
* legality of `actual_card_played`
* point consistency

For the validation-layer overview and schema limitations, see:

[Schema validation documentation](schema_validation.md)

## Minimal input

A basic input position requires:

```json
{
  "game_type": "grand",
  "player_role": "declarer",
  "player_position": "middlehand",
  "trick_leader": "left",
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
| `left_hand_size`              | Number of unknown cards held by the left opponent.                                             |
| `right_hand_size`             | Number of unknown cards held by the right opponent.                                            |
| `sample_count`                | Number of Monte Carlo samples.                                                                 |
| `random_seed`                 | Random seed for reproducibility.                                                               |
| `use_basic_opponent_strategy` | Whether to use basic opponent strategy.                                                        |

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

| Field                 | Meaning                                                       |
| --------------------- | ------------------------------------------------------------- |
| `hand_game`           | Whether the game was announced as a hand game.                |
| `ouvert`              | Whether the game was announced as ouvert.                     |
| `schneider_announced` | Whether Schneider was announced.                              |
| `schwarz_announced`   | Whether Schwarz was announced.                                |
| `matadors`            | Matador count for suit and grand games.                       |
| `bid_value`           | Optional bid value used for overbid detection and settlement. |

If `matadors` is provided, the explicit value is used.

If `matadors` is missing or `null`, the engine tries to infer the matador count from currently known declarer cards where possible.

Automatic matador inference currently uses known declarer-card context from:

* `hand`
* `skat`, when available and allowed by the analysis mode

If matadors cannot be inferred for a suit or grand game, the game value may remain incomplete.

Null games do not use matadors.

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

| Value             | Meaning                             |
| ----------------- | ----------------------------------- |
| `unknown`         | Skat is not visible.                |
| `known_post_game` | Skat is known for post-game review. |

Supported `game_end_reason` values:

| Value                                 | Meaning                                                |
| ------------------------------------- | ------------------------------------------------------ |
| `not_ended`                           | Game is still in progress.                             |
| `normal_completion`                   | Game ended normally with all 120 card points assigned. |
| `declarer_claimed_remaining_tricks`   | Declarer claimed the remaining tricks.                 |
| `declarer_conceded_remaining_tricks`  | Declarer conceded the remaining tricks.                |
| `defenders_conceded_remaining_tricks` | Defenders conceded the remaining tricks.               |

## Live vs post-game information rules

The project separates live decision analysis from post-game review.

`live_decision` is intended for in-game decisions and must not use post-game-only information.

`post_game_review` is intended for completed or retrospectively analyzed games.

Important validation rules:

* `analysis_mode = "live_decision"` cannot use `skat_visibility = "known_post_game"`.
* `analysis_mode = "live_decision"` cannot include known skat cards in `skat`.
* `game_end_reason` values other than `not_ended` require `analysis_mode = "post_game_review"`.
* `analysis_mode = "live_decision"` cannot describe a completed game with all 120 card points assigned.
* In `live_decision`, completed-trick winner metadata such as `winner_player` or `winner_role` must be verifiable.
* If winner metadata is provided in `live_decision`, `players` should also be provided.

Examples:

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
| `isko_list`   | Partially implemented ISkO-style single-game rating for the fixed three-player table. |

If omitted, `performance_rating_summary.rating_system` is `null`.

The project assumes a fixed three-player table. No table-size input field is required.

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

| Value                     | Meaning                               |
| ------------------------- | ------------------------------------- |
| `lowest_point`            | Choose the lowest-point legal card.   |
| `highest_point`           | Choose the highest-point legal card.  |
| `random_legal`            | Choose a random legal card.           |
| `basic_trick_play`        | Use basic trick-play behavior.        |
| `basic_defender_lead`     | Use a cautious defender lead policy.  |
| `basic_defender_response` | Use a basic defender response policy. |

The project also supports separate left/right opponent policy fields:

```json
{
  "left_opponent_lead_policy": "highest_point",
  "left_opponent_response_policy": "basic_trick_play",
  "right_opponent_lead_policy": "basic_defender_lead",
  "right_opponent_response_policy": "basic_defender_response"
}
```

Normalization behavior:

* `left_opponent_lead_policy` falls back to `opponent_lead_policy`.
* `left_opponent_response_policy` falls back to `opponent_response_policy`.
* `right_opponent_lead_policy` falls back to `opponent_lead_policy`.
* `right_opponent_response_policy` falls back to `opponent_response_policy`.

Current multi-step behavior:

* If `right` leads, the engine uses `right_opponent_lead_policy`.
* If `left` leads, the engine uses `left_opponent_lead_policy`.
* If `left` leads and `right` responds, the engine uses `right_opponent_response_policy`.

Global policy fields remain supported for backward compatibility.

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

Validation rules:

* `cards` must contain exactly three cards.
* `players` must contain exactly three unique players when provided.
* `players` must follow the known seating order:

  * `["me", "left", "right"]`
  * `["left", "right", "me"]`
  * `["right", "me", "left"]`
* `winner_player` must be valid when provided.
* `winner_role` must be valid when provided.
* `winner_role` is checked against `winner_player` when the local `player_role` allows a safe inference.
* The winner of one completed trick must lead the next completed trick.
* If `current_trick` is not empty, `trick_leader` must match the winner of the last completed trick.
* When `cards`, `players`, and `winner_player` are provided, the engine validates that `winner_player` actually won the trick according to the implemented Skat rules.

Older completed-trick entries without `players` or `winner_player` remain supported, but they cannot be checked as strictly.

## Validation rules

Input validation rejects:

* invalid game types
* invalid card notation
* duplicate known cards
* invalid completed-trick structures
* invalid completed-trick winner metadata
* inconsistent completed-trick sequence
* negative point values
* known card points above 120
* unknown `game_end_reason`
* inconsistent `game_end_reason` and remaining card points
* invalid `bid_value`
* unknown `performance_rating_system`
* invalid opponent policy values
* invalid live-vs-post-game information combinations
* known skat cards in live decision mode
* ended game reasons outside post-game review mode
* complete 120-point game states in live decision mode
* invalid or illegal `actual_card_played`