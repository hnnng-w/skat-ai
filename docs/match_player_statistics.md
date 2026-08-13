# Match Player Statistics

Issue #166 adds editable private Match-bound Player Statistics Snapshots and
time-safe Profile preparation. It reuses the existing Match participant Snapshot,
Opponent Statistics, normalized `PlayerProfile`, Profile derivation, Workspace
definition replacement, and persistence contracts without changing their
versions or persisted shape.

## Match-bound history

Each Match participant retains at most one optional immutable Snapshot. A later
Match may retain a separate Snapshot for the same stable Player. There is no
global Player Catalog, multiple-Snapshot Match history, automatic newest
selection, source merge, weighting, or platform lookup.

The browser can add or replace one Snapshot from `manual_entry` or
`online_platform` form data and can clear any retained Snapshot. It derives the
record Player ID and optional label from the selected Match participant. Loaded
`historical_games` records and their complete aggregation provenance are shown
read-only; they remain clearable or replaceable by a new manual or online record.

## Existing Statistics validation

Browser form values are assembled into exactly one existing version-1
`OpponentStatisticsRecord` through `build_opponent_statistics_input()`. The form
captures source name, observed/captured RFC 3339 instant, optional source Player
ID and notes, Games played, all eight percentage values, and either no exact
Counts or the complete existing eight-Count set. No value is corrected or
inferred by the browser.

The internal set operation accepts any valid existing record, including
`historical_games`. `observed_at` and `source.captured_at` must represent the same
aware instant. Player IDs must match, non-null labels must agree, and Snapshot IDs
must remain unique in the Match.

## Context and temporal safety

`MatchPlayerStatisticsContextV1` version `1` describes each participant through:

```text
player_id
table_place
snapshot_id
observed_at
temporal_status
eligible_for_match_analysis
normalized_profile
profile_derivation
```

Temporal statuses are, in exact order:

```text
absent
eligible
match_time_unavailable
captured_not_before_match
```

The only eligible relationship is:

```text
source.captured_at < match.played_at
```

Both values are parsed as aware RFC 3339 instants. Equality, including equivalent
instants written with different offsets, and later capture are ineligible.
Missing Match time is ineligible. Every valid ineligible Snapshot remains
unchanged as descriptive Match metadata; there is no tolerance or bypass.

Every retained Snapshot is normalized through the existing
`build_player_profile_from_opponent_statistics()` and derived through the
existing `derive_opponent_profile()`. Existing Confidence bands, Signals,
Classification, recommended preset, actionable preset, derivation status, and
explanations are reused exactly. The Match layer adds no threshold, Signal,
Classification, Confidence rule, or preset.

## Match-wide preparation

`MatchPlayerStatisticsPreparationV1` version `1` contains exactly three Contexts
in `place_1`, `place_2`, `place_3` order. Status is `available` when at least one
Snapshot is temporally eligible and otherwise `unavailable`.

The prepared `OpponentStatisticsInput` contains only eligible records in the
same canonical order. The Perspective Player is retained when eligible.
`eligible_player_ids` and `actionable_player_ids` preserve that order. Preparation
itself removes no actor, binds no relative side, and applies no Profile or policy.
Issue #167's Decision preparation centers the stable circular map on each actor,
excludes that Player from opponent slots, and reports eligible left/right
Profiles and actionable presets. Issue #168 can pass those exact bindings into
one explicit existing Position Application invocation. Disabled Profile Presets
retain the binding but apply no preset; eligible nonactionable derivations also
change no policy. See [Match review and materialization](match_review_and_materialization.md)
and [Match analysis and exports](match_analysis_and_exports.md).

Metadata correction recomputes all Contexts and the Preparation when
`played_at` changes. That time correction does not alter Snapshot content and
adds no revision beyond the existing metadata operation. Platform-ID correction
retains the Snapshot unchanged. A non-null Player-label correction immutably
reconciles the retained record label under the deterministic ID for that same
metadata revision rather than dropping the observation or weakening the existing
label contract.

## Immutable updates

`set_match_player_statistics_snapshot_v1()` and
`clear_match_player_statistics_snapshot_v1()` return
`MatchPlayerStatisticsUpdateResultV1` version `1`. Operations are
`set_snapshot` and `clear_snapshot`; statuses are `applied`, `unchanged`, and
`revision_conflict`.

Default IDs are deterministic:

```text
{match_id}-{player_id}-statistics-r{workspace.revision + 1}
```

An ID is generated only for an applied content change. An equal semantic
submission without an explicit new ID retains the existing ID. Reusing an
existing ID with changed content is rejected; an explicit valid new unique ID is
accepted.

Both operations delegate one candidate definition to the existing Workspace
replacement operation. Only the selected participant changes, all 36 Slots are
preserved, applied updates increment revision once, and unchanged or conflicted
updates preserve revision. Clearing an absent Snapshot is unchanged. Result
Context and Preparation are derived from the returned Workspace.

## Browser and autosave

The private local browser presents one Player Statistics card for each
participant, including retained source, Games, percentages, optional Counts,
temporal status, eligibility, normalized Profile, Confidence, Classification,
derivation status, presets, and explanations. Add, Replace, and Clear are
ordinary server-rendered forms and work without JavaScript. JavaScript remains
progressive enhancement and contains no Statistics or Profile rules.

Applied updates use the existing locked one-file context and perform at most one
definition replacement, one persistence-document build, and one Save. Unchanged
and revision-conflict results do not Save. A persistence conflict does not
replace context and requires the existing explicit Reload; there is no retry,
merge, or automatic Reload.

## Boundaries

Snapshots are private local Workspace data and receive no public redaction. This
feature performs no external request, global history lookup, or profile learning.
Issue #168 can explicitly consume eligible records through the existing Position
or Historical Application behavior. Position execution uses actor-relative
opponent bindings. Historical injection requires enabled Immediate Review and
Profile Presets. Neither path claims that Profiles alter bounded Search,
Historical Search Review, or Replay Coaching.

The prepared Package baseline is `0.15.0`. Public exports, seven Root workflows,
Capture CLI options, the one Console Script, 63 authoritative and packaged
Schemas, six Session examples, and 85 generated-output scenarios are unchanged.
Manual GitHub publication remains pending. Private browser
analysis and authenticated local downloads are implemented; Public Match APIs
and Schemas, public Match exports, a global Player Catalog, and learned Profiles
remain future work.
