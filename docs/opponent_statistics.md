# Opponent statistics

`skat-ai` supports a separate version-1 workflow for externally supplied
opponent statistics. It validates stable player identity, required source
provenance, rounded percentages, and deterministic conversion to existing
`PlayerProfile` rate semantics.

This workflow only validates and normalizes supplied statistics. It does not
derive confidence, select policy presets, predict behavior, or apply the values
to live recommendations, historical review, or simulation.

## Input workflow

The top-level input contains only `opponent_statistics_input`:

```json
{
  "opponent_statistics_input": {
    "schema_version": 1,
    "records": []
  }
}
```

It cannot be combined with position fields, historical or training-dataset
input, list modes, simulation or recommendation settings, opponent policies, or
manually supplied live-position profiles.

Each record requires `player_id`, `source`, `games_played`, and all eight
statistics. `player_label` is optional. IDs and labels are opaque,
case-sensitive, non-empty strings without leading or trailing whitespace. The
engine does not generate, trim, lowercase, or otherwise normalize identity.
Duplicate `player_id` values in one version-1 input are rejected, and input order
is preserved.

## Provenance

Every record requires:

* `source_type`: `online_platform` or `manual_entry`
* `source_name`
* `captured_at`: valid RFC 3339 date-time with an explicit time-zone offset

Optional source fields are `source_player_id` and `notes`. All source strings
must be non-empty and unpadded. Unknown source fields are rejected. Output
preserves every supplied provenance value unchanged.

The workflow does not scrape platforms, merge captures, or maintain statistics
history. Multiple captures for one player require future versioning or history
functionality and cannot appear as duplicate IDs in one input.

## Percentage definitions

Public input uses percentage points from `0` through `100`. Internal normalized
profile rates use values from `0` through `1`.

| Input field | Exact denominator |
| --- | --- |
| `solo_games_played_percent` | Declarer games divided by all games. |
| `defender_games_played_percent` | Defender games divided by all games. |
| `solo_games_won_percent` | Won declarer games divided by declarer games. |
| `solo_hand_percent` | Hand games divided by declarer games. |
| `suit_games_percent` | Suit declarer games divided by declarer games. |
| `grand_games_percent` | Grand declarer games divided by declarer games. |
| `null_games_percent` | Null declarer games divided by declarer games. |
| `defender_games_won_percent` | Games won as defender divided by defender games. |

Contract-distribution percentages are percentages of declarer games, not all
games. `games_played` must be an integer of at least `1`. Booleans are not
accepted as integers or percentages. Every percentage must be finite and in the
inclusive `0..100` range.

## Rounded-value consistency

Source values may be rounded. The fixed tolerance is `2.0` percentage points,
so these sums must be in the inclusive range `98..102`:

```text
solo_games_played_percent + defender_games_played_percent
```

When `solo_games_played_percent` is greater than zero, this sum has the same
requirement:

```text
suit_games_percent + grand_games_percent + null_games_percent
```

When `solo_games_played_percent` is zero, `solo_games_won_percent`,
`solo_hand_percent`, and all three contract-distribution percentages must be
zero. When `defender_games_played_percent` is zero,
`defender_games_won_percent` must be zero. A zero individual contract share or
zero defender win rate remains valid when that role exists.

Tolerance checks do not rewrite source values.

## Canonical normalization

Every percentage is divided by `100` and mapped as follows:

| Source percentage | Normalized `PlayerProfile` field |
| --- | --- |
| `solo_games_played_percent` | `solo_rate` |
| `solo_games_won_percent` | `solo_win_rate` |
| `solo_hand_percent` | `hand_game_rate` |
| `suit_games_percent` | `suit_game_rate` |
| `grand_games_percent` | `grand_rate` |
| `null_games_percent` | `null_game_rate` |
| `defender_games_won_percent` | `defender_win_rate` |

`games_played` is copied exactly. `solo_games_played` and
`defender_games_played` remain `null`: rounded percentages are not converted
into allegedly exact role-specific counts. No declarer wins, defender wins, or
contract counts are inferred.

The structured output keeps the original percentage-point `statistics`
separate from `normalized_profile_statistics`. Each record also contains:

```json
{
  "validation_metadata": {
    "percentage_sum_tolerance_points": 2.0
  }
}
```

## CLI and schemas

Run the public example:

```powershell
python main.py --input examples/opponent_statistics.json
```

Write only structured successful output:

```powershell
python main.py --input examples/opponent_statistics.json --output outputs/opponent-statistics.json --quiet
```

Normal output prints the record count and one percentage-based summary per
player. Only `--input`, `--output`, and `--quiet` are accepted for this workflow.

The focused schemas are:

* [`schemas/opponent_statistics.schema.json`](../schemas/opponent_statistics.schema.json)
* [`schemas/opponent_statistics_output.schema.json`](../schemas/opponent_statistics_output.schema.json)

JSON Schema enforces structure, required fields, enums, and simple ranges.
Runtime validation remains authoritative for duplicate identity, RFC 3339
time-zone requirements, finite numbers, sum consistency, zero-role rules,
deterministic normalization, and output reconciliation.

## Current limitations

Historical-game-derived player-statistics aggregation remains unsupported. This
workflow does not aggregate historical games, infer confidence, derive or apply
policy presets, classify behavior, train a model, or consume statistics in live
or historical recommendations.
