# Historical opponent statistics

`skat-ai` can deterministically aggregate exact reusable opponent statistics
from complete normal-play historical games. The source is the existing
version-1 `training_dataset_input`; no second multi-game format is introduced.
The dataset is reused as a validated container for games, stable identities,
provenance, and partitions. Aggregation does not generate decision samples,
train or evaluate a model, or apply a policy.

## Source selection

Run aggregation with:

```powershell
python main.py `
  --input examples/training_dataset_normal_play.json `
  --aggregate-opponent-statistics
```

Every included dataset record contributes exactly one validated historical
game. Existing training-dataset checks continue to reject duplicate record,
game, and complete source identities and cross-partition game/source leakage.
The historical contract remains limited to complete `normal_completion` games.

Every record selected by partition must have a valid offset-aware RFC 3339
`historical_game.played_at`, even when no temporal cutoff is supplied. This
requirement applies before temporal filtering, so a selected missing timestamp
is not hidden by a cutoff.

### Partitions

Repeat `--opponent-statistics-partition` to select one or more of `train`,
`validation`, and `test`:

```powershell
python main.py `
  --input examples/training_dataset_normal_play.json `
  --aggregate-opponent-statistics `
  --opponent-statistics-partition validation `
  --opponent-statistics-partition train
```

Without the option, all three partitions are eligible. Repeated values are
deterministically de-duplicated, and output always uses canonical `train`,
`validation`, `test` order regardless of argument order. An explicitly selected
partition with no source records is rejected. Partition filtering is applied
before temporal filtering. Partition selection records dataset membership; it
does not enforce or claim player-disjoint partitions.

### Strict cutoff

The optional cutoff is exclusive:

```text
historical_game.played_at < --opponent-statistics-before
```

Values are compared as offset-aware instants. A game at the same instant is
excluded, including when the cutoff and game use different offsets. Later games
are also excluded, the original cutoff text is preserved in structured output,
and a selection that leaves no games is rejected. There is no tolerance or
inclusive mode.

## Identity and order

Players aggregate by exact stable `player_id`. IDs are opaque and
case-sensitive; seats and labels are not identity. A player may change seats or
roles between games. Output player order follows first appearance in selected
dataset record order, and per-player source record/game IDs preserve that order.

One consistent non-null `player_label` is preserved. Missing labels and one
consistent non-null label resolve to that label. Conflicting non-null labels for
the same ID are rejected. IDs and labels are never trimmed, case-normalized, or
approximately matched.

## Exact counts

Each included game contributes one `games_played` to all three participants,
one declarer game to the declarer, and one defender game to each defender. The
following exact non-negative integer counts are emitted for every player:

| Field | Definition |
| --- | --- |
| `solo_games_played` | Included games where the player is declarer. |
| `solo_games_won` | Declarer games won according to final settlement. |
| `solo_hand_games` | Declarer games with `hand_game: true`. |
| `suit_games` | Declarer games with Clubs, Spades, Hearts, or Diamonds. |
| `grand_games` | Declarer games with Grand. |
| `null_games` | Declarer games with Null. |
| `defender_games_played` | Included games where the player is not declarer. |
| `defender_games_won` | Defender games where final settlement is a declarer loss. |

The authoritative `final_settlement_summary.is_loss` determines the winner,
not raw card points. `false` credits a declarer win; `true` credits a defender
win. An overbid declarer loss therefore counts as a declarer loss, and both
defenders receive one defender win when their side wins.

Exact counts obey:

```text
solo_games_played + defender_games_played == games_played
solo_games_won <= solo_games_played
solo_hand_games <= solo_games_played
suit_games + grand_games + null_games == solo_games_played
defender_games_won <= defender_games_played
```

## Percentages

Structured percentages are computed directly from exact integers using normal
Python floating-point division and multiplication by `100`; they are not rounded
before JSON serialization. Human-readable CLI output formats selected values to
two decimal places without changing structured values.

| Percentage | Numerator / denominator |
| --- | --- |
| `solo_games_played_percent` | `solo_games_played / games_played` |
| `defender_games_played_percent` | `defender_games_played / games_played` |
| `solo_games_won_percent` | `solo_games_won / solo_games_played` |
| `solo_hand_percent` | `solo_hand_games / solo_games_played` |
| `suit_games_percent` | `suit_games / solo_games_played` |
| `grand_games_percent` | `grand_games / solo_games_played` |
| `null_games_percent` | `null_games / solo_games_played` |
| `defender_games_won_percent` | `defender_games_won / defender_games_played` |

Each ratio is multiplied by `100`. When `solo_games_played` is zero, all five
declarer-dependent percentages are exactly `0.0`. When
`defender_games_played` is zero, `defender_games_won_percent` is exactly `0.0`.
No percentage is used to reconstruct an exact historical count.

## Provenance and derivation

Every aggregated statistics record has `source_type: "historical_games"`, the
dataset ID as `source_name`, and the player ID as `source_player_id`. Its
`historical_aggregation` object contains aggregation version `1`, dataset ID and
version, that player's canonical included partitions, ordered source record and
game IDs, and original `first_played_at` and `last_played_at` timestamp text.

`source.captured_at` is the original `played_at` text of that player's latest
included game and represents the same instant as `last_played_at`. It is a
per-player value, not necessarily the aggregation's top-level latest timestamp.
This makes an export compatible with the existing historical loader's strict
rule `captured_at < target played_at`, preventing use of a profile containing
the target game or a later game.

The existing normalization and version-1 profile derivation are reused
unchanged. `games_played`, `solo_games_played`, and
`defender_games_played` provide exact overall, declarer, and defender evidence.
Existing confidence bands, thresholds, signals, classifications, preset
metadata, explanations, and actionability are unchanged. Win, Hand, and
contract exact counts remain available even when a current signal does not use
them.

## Structured output and export

`--output` writes the dedicated aggregation result:

```json
{
  "input_file": "examples/training_dataset_normal_play.json",
  "historical_opponent_statistics_aggregation_summary": {
    "schema_version": 1,
    "aggregation_version": 1,
    "source_dataset": {},
    "selection": {},
    "source_record_count": 2,
    "source_game_count": 2,
    "player_count": 3,
    "first_played_at": "2026-07-10T18:00:00+02:00",
    "last_played_at": "2026-07-20T19:00:00+02:00",
    "records": []
  }
}
```

`source_record_count` and `source_game_count` are equal because each selected
record contains one game. `selection` reports canonical included partitions,
the nullable preserved cutoff, excluded counts for all three partitions, and
the temporal exclusion count. Records include exact counts, percentages,
normalized profile statistics, derivation, and historical provenance. The
summary contains no decision samples, hands, tricks, recommendations, review, or
policy-application result.

Use `--export-opponent-statistics` to additionally write a standalone existing
workflow:

```powershell
python main.py `
  --input examples/training_dataset_normal_play.json `
  --aggregate-opponent-statistics `
  --output outputs/historical-statistics.json `
  --export-opponent-statistics outputs/opponent-statistics.json
```

The export contains only `opponent_statistics_input` version `1`. It round-trips
through the existing opponent-statistics loader and can be used by standalone
normalization, exact live left/right bindings, and strict time-safe historical
participant matching. Export does not automatically apply the records in the
same invocation. Input, normal output, and export paths must resolve to distinct
paths.

Normal output prints source game/player counts, canonical partitions, and one
short line per player. `--quiet` suppresses all successful human-readable output
and file confirmations while still writing requested normal and export files.
Expected errors remain visible through the normal CLI error path.

The focused output schema is
[`schemas/historical_opponent_statistics_aggregation.schema.json`](../schemas/historical_opponent_statistics_aggregation.schema.json).
Exported records use the existing
[`schemas/opponent_statistics.schema.json`](../schemas/opponent_statistics.schema.json).

## Restrictions and non-goals

Aggregation options are accepted only with `training_dataset_input` and
`--aggregate-opponent-statistics`. Position, single historical-game, historical
review, standalone opponent-statistics, list, impossible-Null, and unrelated
workflows reject them. Aggregation also rejects historical snapshot/review,
samples, seeds, recommendation, simulation, comparison, policy, profile,
external binding, and live binding options. Without the aggregation flag, the
existing training-dataset conversion remains unchanged.

This bounded workflow does not provide player-disjoint partition enforcement,
recency weighting, count-based rolling windows, merging with platform/manual
statistics, multiple captures per player, capture selection or persistence,
automatic policy use, recommendation-quality evaluation, strategic policy-
quality claims, learned behavior, machine-learning training, or
claims/concessions and other historical end reasons.

The separate [rolling opponent-policy evaluation](opponent_policy_evaluation.md)
reuses this exact aggregation with one strict target-start cutoff per game. It
measures observed-card imitation only and does not alter or automatically apply
the aggregated profiles.
