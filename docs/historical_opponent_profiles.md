# Historical opponent profiles

Historical game review can apply validated external opponent profiles without
using statistics captured during or after the reviewed game. The feature reuses
the existing opponent-statistics loader, normalized `PlayerProfile`, scoped
confidence, classification, and actionable preset derivation. It does not derive
statistics from the reviewed game. Its companion may be a separate historical
aggregation export only when that export's per-player latest included game is
strictly older than the reviewed game.

## CLI

```powershell
python main.py `
  --input examples/historical_grand_normal_completion.json `
  --historical-game-review `
  --opponent-statistics-file examples/historical_opponent_statistics.json `
  --use-profile-presets `
  --samples 20 `
  --seed 42
```

The external file is accepted only with `--historical-game-review` and effective
profile-preset opt-in. Historical summary, snapshot-only, training-dataset,
standalone statistics, list, impossible-Null, and unrelated position workflows
reject it. `--left-opponent-player-id` and `--right-opponent-player-id` remain
live-only and are rejected for historical review.

## Game time and temporal safety

Version-1 historical games may include:

```json
"played_at": "2026-07-24T18:30:00+02:00"
```

`played_at` is the instant when the game began. It must be a valid RFC 3339
date-time with an explicit UTC offset. The original text is preserved in the
canonical record, historical summary, decision provenance, and training source
provenance. Existing games may omit it unless external profiles are requested.

Every statistics record matched to a participant must satisfy:

```text
source.captured_at < played_at
```

Both values are parsed as aware date-time instants before comparison. Equality,
including equivalent instants written with different offsets, is rejected.
Later captures are rejected. There is no tolerance or bypass. Unmatched records
are ignored and are not temporally compared.

For `source_type: "historical_games"`, `captured_at` is the matched player's
latest included source-game `played_at`, not the aggregation's global latest
game. The same strict comparison therefore rejects an export containing the
target game or any later game for that player.

## Participant matching

Statistics records match the three historical participants by exact, opaque,
case-sensitive `player_id`. Labels, record order, and approximate text are never
used. At least one participant must match; one, two, or three matches are valid.
Extra non-participant records are ignored, and unmatched participants retain the
existing default opponent behavior.

Each decision uses the existing snapshot `relative_player_map`. The acting
player maps to `me`; the stable IDs already mapped to `left` and `right` select
the corresponding matched profiles independently. Profiles therefore follow
stable players as acting players change and may move between relative sides.
The acting player's own profile is never supplied as an opponent profile.

## Actionability and precedence

Only `actionable_policy_preset` can affect review. Actionable
`aggressive_points` and `cautious_defender` presets enter the existing effective
opponent-policy resolver. `simple_lowest`, neutral, low-confidence,
insufficient-confidence, and insufficient-data derivations do not override
defaults.

Existing explicit policy precedence is retained for each decision:

1. explicit side-specific policy
2. explicit global policy or preset
3. actionable external profile preset
4. existing default policy

The effective side response policies are passed to the same immediate
recommendation path used by equivalent live or manual profiles. Profiles are
not merged, and there are no manual historical side bindings.

## Output

The root output adds `historical_opponent_profile_application_summary` only when
the companion file is used. It reports the file, game, original `played_at`,
strict temporal rule, all three participant match rows, matched count, unmatched
IDs, compact source provenance, derivation metadata, and actionability. Source
percentage values are not copied into this summary.

Every review decision adds `opponent_profile_application` with the acting,
left-opponent, and right-opponent stable IDs. Each side reports match,
classification, derivation, actionable preset, application status, reason,
applied preset, and the effective lead and response policies actually resolved.
Full source statistics are not duplicated in decision rows.

`opponent_profile_application_counts` reports bounded decision, side, stable
player, and preset application counts. These counts describe application only.
They do not show that a policy improved a recommendation, that a player followed
the profile, or that a preset is optimal.

## Preserved behavior and limits

Deterministic per-decision seed derivation, legal cards, information-safe
snapshots, actual-card comparisons, replay, scoring, final settlement, and the
Ouvert review limitation are unchanged. Without a companion file, historical
records without `played_at`, summaries, snapshots, reviews, and training-dataset
generation retain their existing behavior. Live profile binding semantics are
unchanged.

Profiles remain explainable rule-based policy inputs, not learned models.
Bounded statistics aggregation is a separate invocation and never derives a
profile from the reviewed game automatically. Multiple captures per player,
automatic newest-capture selection, profile history, weighting or merging,
recommendation-policy quality evaluation and machine-learning training are not
implemented. The separate rolling behavioral evaluation derives profiles from
earlier source-partition games and evaluates the acting player's own observed
cards; it does not use this review path's relative opponent slots or apply a
profile to recommendations.

The focused schema is
[`schemas/historical_opponent_profile_application.schema.json`](../schemas/historical_opponent_profile_application.schema.json).
