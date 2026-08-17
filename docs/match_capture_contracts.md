# Match capture contracts

Issue #160 began the `v0.15.0` milestone with internal immutable
identity and metadata contracts for manual post-game capture of one EuroSkat
36er Standard Match from a video or manual observation source. These contracts
do not themselves make Match capture executable through a Public API, CLI, or
UI. Issue #163 now persists the unchanged Match definition inside an internal
36-position Workspace. Issue #164 consumes that unchanged definition through
internal transport-free rapid-entry Application services.

## Contract identity

The independent internal versions and policies are:

```text
MATCH_CAPTURE_CONTRACT_VERSION = 1
MATCH_SOURCE_METADATA_VERSION = 1
MEDIA_TIMECODE_VERSION = 1
MATCH_TOURNAMENT_FORMAT_VERSION = 1
MATCH_PLAYER_STATISTICS_SNAPSHOT_VERSION = 1

MATCH_TOURNAMENT_FORMAT_REGISTRY_POLICY =
    append_only_named_format_definitions

MATCH_PERSPECTIVE_POLICY =
    one_declared_match_player
```

These values are independent from the Package, Public API, Session, Historical
Game, fixed-list, Opponent Statistics, Provenance, and Schema versions. Issue
#160 changes none of those existing contracts.

## Game platform and media source

`game_platform` describes where the Match was played, for example `EuroSkat`.
The Match source describes where the observation came from, for example a
YouTube video. They are separate descriptive values.

A YouTube source stores only caller-supplied evidence:

* the video URL;
* the video title;
* an optional channel name;
* optional Match-level media bounds.

The URL is retained exactly. Validation is limited to a non-empty, non-padded
absolute HTTP or HTTPS URL. The engine does not verify a YouTube host, issue a
network request, follow redirects, call an API, parse an embed, download media,
or scrape a website.

## Media timecodes

`MediaTimecodeV1` contains:

```text
media_timecode_version
start_offset_ms
end_offset_ms
```

Offsets are strict non-negative integer milliseconds; booleans are not
integers. The end is nullable and, when present, cannot precede the start. Equal
bounds are valid. The contract stores no authoritative formatted time string and
generates no current time. Issue #161 reuses the same value for optional Game,
Decision, and commentary bounds and validates known child bounds against their
known enclosing Game or Match bounds.

## Source metadata

`MatchSourceMetadataV1` preserves explicit nulls and supports these canonical
source kinds in order:

```text
youtube_video
other_video
manual_observation
```

| Source kind | URL | Title | Channel | Match timecode |
| --- | --- | --- | --- | --- |
| `youtube_video` | Required | Required | Nullable | Nullable |
| `other_video` | Required | Required | Nullable | Nullable |
| `manual_observation` | Null | Required | Null | Nullable |

All non-null strings are non-empty and non-padded. Source metadata is
descriptive only and cannot change rules, Search, scoring, list points,
Settlement, or analysis behavior.

## Tournament format registry

The immutable version-1 registry contains exactly one executable format:

```text
format_id = euroskat_36_standard_v1
provider = EuroSkat
display_name = 36er Standard
player_count = 3
game_count = 36
```

`get_match_tournament_format_v1()` performs exact-ID lookup and returns the
canonical frozen object. A `MatchCaptureDefinitionV1` accepts that exact object,
not a caller-created count override. Registry evolution is append-only: later
definitions may be appended without renaming or reordering the existing ID.

The format definition includes no ranking, qualification, prize, entry-fee,
loss-fee, or bonus-program rule. It does not define operational semantics for
EuroSkat 36er Zocker, 18er Rangliste, or Rocket.

## Player statistics snapshots

`MatchPlayerStatisticsSnapshotV1` contains a caller-supplied stable Snapshot ID,
an RFC 3339 observation time, and one exact existing immutable
`OpponentStatisticsRecord`. The snapshot does not duplicate percentage, count,
or provenance validation.

The observation time and the record's `source.captured_at` must represent the
same instant; their retained RFC 3339 text may use different offsets. Participant
reconciliation requires the statistics-record Player ID to equal the Match
Player ID. Two non-null labels for that Player must agree.

Serialization reuses the existing Opponent Statistics input serializer. It does
not derive a `PlayerProfile`, merge captures, replace an earlier snapshot, or
apply a policy. A Player can therefore appear in later Matches with a separate
immutable snapshot while the earlier Match retains its historical observation.

## Match participants

`MatchParticipantV1` contains:

```text
player_id
player_label
platform_player_id
table_place
statistics_snapshot
```

The Player ID is stable, case-sensitive, non-empty, non-padded, and not the
relative identity `me`, `left`, or `right`. Label, platform identity, and
statistics snapshot are nullable. Table places reuse, without duplication, the
existing canonical order:

```text
place_1
place_2
place_3
```

A participant stores no hand, historical seat, role, result, Cards, or mutable
Match state.

## Match definition

`MatchCaptureDefinitionV1` contains:

```text
match_capture_contract_version
match_id
title
game_platform
external_match_id
played_at
tournament_format
source
participants
perspective_player_id
```

The Match ID, title, and game platform are required descriptive values. External
Match ID and RFC 3339 played time are nullable. The definition requires the exact
canonical supported format, exactly three participants in canonical table-place
order, unique Player IDs, unique non-null platform Player IDs, and unique
non-null Snapshot IDs.

It contains no individual Game slots, Cards, hands, Skat, Discards, Plays,
comments, Decision annotations, progress, standings, Analysis Results, path,
generated timestamp, or generated identity.

## Perspective semantics

The three identities are deliberately separate:

```text
application user:
    not persisted by this contract

perspective player:
    one exact declared Match participant

match participants:
    exactly three stable Players
```

The perspective identifies the Match Player whose hand is visible in the source.
It does not assert that the person operating the application participated in the
Match. It is independent from a later Game's Declarer, historical seat, and role,
and it does not limit which later decisions may receive annotations.

## Deterministic serialization

Every new value has deterministic `to_dict()` serialization with stable field
order, canonical participant order, explicit new-contract nulls, and fresh
mutable JSON-compatible containers. Construction defensively copies nested
source, timecode, participant, snapshot, and statistics values. Serialization
adds no environment data, filesystem path, current time, generated ID,
network-derived metadata, or Player Profile.

## Current boundary

All Match and observed-Game values remain internal. Issue #161 adds one
Match-linked observed Game, Game/Decision/commentary timecodes, bounded partial
and exact complete Play validation, free-text commentary on any Player Decision,
linked later responses, and deterministic evidence summaries. See
[Observed Game capture contracts](observed_game_capture_contracts.md).

Issue #163 adds exactly 36 internal Workspace Slots, fixed-list rotation, partial
observed-Game placement, explicit passed deals, immutable revisions, Progress,
fingerprints, and strict private persistence. See
[Match Workspace contracts](match_workspace_contracts.md).

Issue #164 adds the internal Position View, exact/bounded Card palette, Game and
setup updates, automatic Player/Decision append, truncation, annotation editing,
and passed/clear wrappers without changing this definition. See
[Match Capture Application services](match_capture_application_services.md).

Issue #165 adds private browser creation and bounded metadata correction through
the local Capture transport without adding fields or versions to this definition.
See [Local Match Capture interface](local_match_capture_interface.md).

Issue #166 adds deterministic set/clear editing and strict-before-Match Context
and Preparation over the existing Snapshot field. It reuses existing Statistics
validation, normalized Profile conversion, Profile derivation, definition
replacement, and persistence without changing this contract. See
[Match Player Statistics](match_player_statistics.md).

Issue #167 adds a separate internal preparation layer that can build information-
safe Decision snapshots and, with complete exact Deal evidence, existing
Historical, unpartitioned Training-source, and fixed-list values without changing
this contract. Issue #168 separately adds explicit private Position/Historical
execution, eligible Profile application through existing behavior, no-workflow
materialization, ephemeral reports, and authenticated local downloads without
changing the Match definition. There is still no Match Root workflow, Public
Match API, Match Schema/data workflow, example, generated scenario, global
Player Catalog persistence/public exposure, public Match export, YouTube integration, or EuroSkat
integration. The published Package baseline is `0.15.0`; seven Root workflows, 63
authoritative and packaged Schemas, six Session examples, and 85 generated-output
scenarios remain unchanged. The maintainer published `v0.15.0` manually at commit
`ec1c154`, and Issue #170 synchronizes publication status.
