# Live opponent profiles

`skat-ai` can attach one reusable external opponent-statistics file to a live
position analysis. Explicit CLI bindings identify which validated statistics
record represents the current left or right opponent.

## CLI workflow

```powershell
python main.py `
  --input examples/grand_second_position.json `
  --opponent-statistics-file examples/opponent_statistics.json `
  --left-opponent-player-id opponent-123 `
  --right-opponent-player-id opponent-789 `
  --use-profile-presets `
  --samples 20 `
  --seed 42
```

Either side may be omitted. IDs are opaque and case-sensitive, must be
non-empty and unpadded, and must match exactly one validated record. Additional
unbound records are ignored. Left and right cannot use the same ID.

The companion file must contain only the existing version-1
`opponent_statistics_input` workflow. The existing loader validates source
provenance, percentages, rounded sums, and identities. The existing
normalization and profile derivation provide `PlayerProfile`, `defender_rate`,
scoped evidence and confidence, classification, recommended and actionable
presets, explanations, and capture provenance. No second parser or derivation is
used.

## Activation and precedence

External bindings are accepted only for a position whose effective
`analysis_mode` is `live_decision`. Profile presets must be enabled by either
the input `use_profile_presets: true` field or `--use-profile-presets`.
Supplying bindings without this opt-in is an error.

Profile source precedence is independent for each side:

1. manually supplied side profile
2. bound external normalized profile
3. no profile

Manual and external profiles are never merged. A matched external binding is
still reported when a manual side profile wins.

The selected profile enters the existing effective opponent-policy resolver.
Only `actionable_policy_preset` may affect analysis. A recommendation of
`simple_lowest`, a low-confidence candidate, a neutral profile, or insufficient
data does not overwrite defaults. Existing input and CLI policy precedence is
unchanged, including global and side-specific overrides. Different actionable
left and right profiles remain separate; no combined external classification is
created.

The resulting side-specific response policies affect immediate analysis. The
same effective lead and response policies also affect multi-step simulation and
policy comparison where the existing manual profile path already participates.
Seeds, legal-card rules, and live information boundaries are unchanged.

## Output

Live output contains `opponent_profile_application_summary` only when a
companion statistics file is supplied. It reports:

* the companion file path and profile-preset opt-in;
* requested or unrequested binding status for each side;
* the effective manual, external, or absent profile source;
* compact external provenance and derivation details;
* whether the profile was applied, was not actionable, or lost to manual or
  explicit-policy precedence;
* the applied actionable preset, if any;
* effective lead and response policies that reconcile with the existing side
  policy fields.

Normal CLI output prints one concise line per requested side. `--quiet` remains
silent. Source percentage statistics are not copied into the application
summary. See
[`schemas/opponent_profile_application.schema.json`](../schemas/opponent_profile_application.schema.json).

## Restrictions

Live-only left/right binding IDs are rejected for post-game position review,
complete historical games, historical decision review, training datasets,
standalone opponent-statistics conversion, list-performance workflows,
impossible-Null settlement, and every other non-live workflow. Historical review
has a separate automatic stable-participant matching path and does not weaken
these live validation rules.

The preserved `captured_at` value is provenance only. Live analysis has no
analysis timestamp to compare with it. Historical application separately uses a
required game-start time and strict older-than comparison. Neither feature adds
historical aggregation, multiple captures, profile persistence,
newest-capture selection, website integration, scraping, learned models,
machine-learning training, or new tactical policies.
