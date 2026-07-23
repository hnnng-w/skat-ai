# Opponent profile derivation

`skat-ai` provides a deterministic, rule-based opponent-profile derivation for
`PlayerProfile` values. Derivation version `1` identifies the evidence bands,
signal thresholds, classification precedence, and output semantics. It is
independent of package version `0.7.0`.

Profiles are not learned, confidence is not a calibrated probability or
confidence interval, and a recommended preset is not claimed to be optimal.
External opponent-statistics output exposes the derivation. An explicit live
stable-ID binding may apply only its `actionable_policy_preset` through the
existing side-specific resolver. Historical review applies the same actionable
result after strict timestamp and stable-participant matching.

## Evidence and confidence

Evidence is derived separately for `overall`, `declarer`, and `defender`:

| Scope | Precedence |
| --- | --- |
| `overall` | Exact `games_played`, otherwise unavailable. |
| `declarer` | Exact `solo_games_played`; otherwise `games_played * solo_rate`; otherwise unavailable. |
| `defender` | Exact `defender_games_played`; otherwise `games_played * defender_rate`; otherwise `games_played * (1 - solo_rate)`; otherwise unavailable. |

Evidence kinds are `exact`, `estimated_from_rate`,
`estimated_from_complement`, and `unavailable`. Estimated role counts may be
decimal values and are never rounded into purported exact historical counts.
External percentages may themselves be rounded, so their estimates must not be
interpreted as exact observations.

Exact role counts cannot exceed total games. When both exact role counts are
present, they must sum to total games. Exact counts and matching rates must agree
within the existing `2.0` percentage-point rounding tolerance.

Every scope uses the same heuristic evidence bands:

| Evidence count | Level |
| --- | --- |
| Unavailable | `unknown` |
| Below `100` | `low` |
| `100` through below `500` | `medium` |
| At least `500` | `high` |

The boundaries are inclusive as stated: `99.999` is low, `100` is medium,
`499.999` is medium, and `500` is high. These are heuristic bands, not
statistical certainty. `get_profile_data_confidence()` remains the
backward-compatible helper for the `overall` level.

## Version-1 signals

| Code | Source | Match | Confidence scope |
| --- | --- | --- | --- |
| `frequent_declarer` | `solo_rate` | `>= 0.35` | `overall` |
| `grand_oriented` | `grand_rate` | `>= 0.25` | `declarer` |
| `hand_oriented` | `hand_game_rate` | `>= 0.10` | `declarer` |
| `reliable_defender` | `defender_win_rate` | `>= 0.52` | `defender` |

Each signal records its source field, observed value, comparison, threshold,
confidence scope and level, threshold match, actionability, and reason code. A
matched signal is actionable only with medium or high confidence from its own
denominator. Low- or unknown-confidence matches remain explanatory. Missing
values are not inferred.

Reason codes are `threshold_matched`, `threshold_not_matched`,
`value_unavailable`, and `insufficient_confidence`.

## Classification and presets

Actionable declarer signals classify the profile as `aggressive`. If none are
actionable, an actionable `reliable_defender` signal classifies it as
`cautious_defender`; otherwise it is `neutral`. When aggressive and defender
signals are both actionable, aggressive evidence takes precedence.

Classifications map to recommendations as follows:

| Classification | Recommended preset |
| --- | --- |
| `aggressive` | `aggressive_points` |
| `cautious_defender` | `cautious_defender` |
| `neutral` | `simple_lowest` |

If only low- or unknown-confidence signals match, the strongest candidate is
retained as the classification and recommendation, but
`actionable_policy_preset` is `null` and the status is
`insufficient_confidence`. Aggressive candidates take precedence over defender
candidates. A profile with evaluable evidence but no match has status `neutral`.
A profile whose supported classifications cannot be evaluated has status
`insufficient_data`.

`simple_lowest` is always a neutral fallback in this contract. It is never an
actionable profile-derived override.

## API and output

The typed API is:

```python
derive_opponent_profile(profile: PlayerProfile) -> OpponentProfileDerivation
```

It accepts external-statistics and manually constructed profiles, validates the
evidence used by the contract, does not mutate the profile, and does not apply a
policy. Each result includes scoped confidence, all four signals, classification,
recommended and actionable presets, status, decisive signal codes, and concise
English explanations.

The stable schema is
[`schemas/opponent_profile_derivation.schema.json`](../schemas/opponent_profile_derivation.schema.json).
External workflow details are documented in
[Opponent statistics](opponent_statistics.md). The same normalized profile and
derivation are reused for live bindings and time-safe historical participant
matching; no second percentage or classification implementation exists.

## Compatibility and limits

`defender_rate` is optional for manually supplied profiles, so profiles that
omit it remain valid. Existing profile-policy helpers delegate threshold and
actionability decisions to the derivation while retaining their established
neutral fallback and explicit/default policy precedence. Existing opt-in manual
profile policy application and external-statistics conversion remain separate;
the live binding layer connects a validated normalized record without changing
derivation semantics.

Derivation does not aggregate historical games, infer table seats, store
captures, predict behavior, evaluate policy effects, or train a model. Live
bindings map an explicit ID to a relative side. Historical review instead uses
the existing decision snapshot mapping to move exact stable-ID profiles between
relative sides. Neither path activates a merely recommended or `simple_lowest`
preset.
