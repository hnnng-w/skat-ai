# Input JSON

This document describes the supported input JSON format for `skat-ai`.

## JSON schema

A draft input JSON schema is available at:

[`schemas/input.schema.json`](../schemas/input.schema.json)

The schema is intended as a documentation and validation aid. Runtime validation is still handled by the Python input-validation layer.

Example files can be validated against the schema with:

```powershell
python scripts/validate_examples_schema.py

The project check script also runs schema validation if it is enabled in scripts/check.ps1.
```

The schema intentionally checks stable structural constraints such as:

- valid card notation
- maximum hand size
- maximum skat size
- maximum current-trick size
- unique cards within individual card arrays
- card-point fields between 0 and 120
- supported analysis and game-end metadata values

More advanced cross-field validation, such as duplicate cards across all known-card lists or completed-trick sequence consistency, is handled by the Python validation layer.

For the validation-layer overview and schema limitations, see:

[Schema validation documentation](schema_validation.md)

## Required fields

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

Core fields:

| Field | Meaning |
|---|---|
| `game_type` | One of `clubs`, `spades`, `hearts`, `diamonds`, `grand`, or `null`. |
| `player_role` | Local player role, usually `declarer` or `defender`. |
| `player_position` | Local player position such as `forehand`, `middlehand`, `rearhand`, or `unknown`. |
| `trick_leader` | Player who leads the current trick. |
| `hand` | Known local hand cards. |
| `current_trick` | Cards already played in the current trick. |
| `played_cards` | Backward-compatible list of previously played cards. Prefer `completed_tricks` for new inputs. |
| `completed_tricks` | Detailed completed trick history. |
| `declarer_points` | Explicit declarer points already known outside completed tricks. |
| `defender_points` | Explicit defender points already known outside completed tricks. |
| `next_player` | Player whose turn it is. |
| `skat` | Known skat cards, if visible. |
| `left_hand_size` | Number of unknown cards held by the left opponent. |
| `right_hand_size` | Number of unknown cards held by the right opponent. |
| `sample_count` | Number of Monte Carlo samples. |
| `random_seed` | Random seed for reproducibility. |
| `use_basic_opponent_strategy` | Whether to use basic opponent strategy. |

## Card notation

Cards are represented as short strings:

| Suit | Meaning |
|---|---|
| `C` | Clubs |
| `S` | Spades |
| `H` | Hearts |
| `D` | Diamonds |

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

| Field | Meaning |
|---|---|
| `hand_game` | Whether the game was announced as a hand game. |
| `ouvert` | Whether the game was announced as ouvert. |
| `schneider_announced` | Whether Schneider was announced. |
| `schwarz_announced` | Whether Schwarz was announced. |
| `matadors` | Matador count. Required for complete suit/grand game value calculation. |
| `bid_value` | Optional bid value used for overbid detection and settlement. |

If `matadors` is `null`, the game value remains incomplete for suit and grand games.

## Analysis metadata fields

Input files may include optional strategic metadata:

```json
{
  "analysis_mode": "live_decision",
  "skat_visibility": "unknown",
  "game_end_reason": "not_ended"
}
```

Supported `analysis_mode` values:

| Value | Meaning |
|---|---|
| `live_decision` | Live decision state. |
| `post_game_review` | Post-game review state. |

Supported `skat_visibility` values:

| Value | Meaning |
|---|---|
| `unknown` | Skat is not visible. |
| `known_post_game` | Skat is known for post-game review. |

Supported `game_end_reason` values:

| Value | Meaning |
|---|---|
| `not_ended` | Game is still in progress. |
| `normal_completion` | Game ended normally with all 120 card points assigned. |
| `declarer_claimed_remaining_tricks` | Declarer claimed the remaining tricks. |
| `declarer_conceded_remaining_tricks` | Declarer conceded the remaining tricks. |
| `defenders_conceded_remaining_tricks` | Defenders conceded the remaining tricks. |

## Performance rating fields

Input files may optionally include:

```json
{
  "performance_rating_system": "isko_list"
}
```

Supported values:

| Value | Meaning |
|---|---|
| `placeholder` | Generic placeholder rating system. |
| `isko_list` | Partially implemented ISkO-style single-game rating for the fixed three-player table. |

If omitted, `performance_rating_summary.rating_system` is `null`.

The project assumes a fixed three-player table. No table-size input field is required.

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

- `cards` must contain exactly three cards.
- `players` must contain exactly three unique players when provided.
- `players` must follow the known seating order:
  - `["me", "left", "right"]`
  - `["left", "right", "me"]`
  - `["right", "me", "left"]`
- `winner_player` must be valid when provided.
- `winner_role` must be valid when provided.
- `winner_role` is checked against `winner_player` when the local `player_role` allows a safe inference.
- The winner of one completed trick must lead the next completed trick.
- If `current_trick` is not empty, `trick_leader` must match the winner of the last completed trick.
- When `cards`, `players`, and `winner_player` are provided, the engine validates that `winner_player` actually won the trick according to the implemented Skat rules.

Older completed-trick entries without `players` or `winner_player` remain supported, but they cannot be checked as strictly.

## Validation rules

Input validation rejects:

- invalid game types
- invalid card notation
- duplicate known cards
- invalid completed-trick structures
- invalid completed-trick winner metadata
- inconsistent completed-trick sequence
- negative point values
- known card points above 120
- unknown `game_end_reason`
- inconsistent `game_end_reason` and remaining card points
- invalid `bid_value`
- unknown `performance_rating_system`