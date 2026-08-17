# Match review and materialization

Issue #167 adds an internal evidence-aware preparation and materialization layer
between one validated Match Workspace and existing Historical, Training Dataset,
and fixed-three-player list contracts. It prepares reusable values but executes
no analysis or Root workflow.

## Contract identity

The independent versions are:

```text
MATCH_DECISION_REVIEW_PREPARATION_VERSION = 1
MATCH_HISTORICAL_GAME_MATERIALIZATION_VERSION = 1
MATCH_TRAINING_SOURCE_COLLECTION_VERSION = 1
MATCH_WORKSPACE_MATERIALIZATION_VERSION = 1
```

The stable policies are:

```text
MATCH_DECISION_REVIEW_INFORMATION_POLICY =
    reconstruct_decision_time_own_hand_without_future_opponent_information

MATCH_PROFILE_BINDING_POLICY =
    prepare_eligible_relative_opponents_without_policy_application

MATCH_HISTORICAL_MATERIALIZATION_POLICY =
    existing_normal_completion_contract_with_complete_initial_deal

MATCH_MATERIALIZED_PLAYED_AT_POLICY =
    retain_match_played_at_without_media_offset_derivation

MATCH_TRAINING_SOURCE_POLICY =
    existing_unpartitioned_record_from_materialized_historical_game

MATCH_LIST_MATERIALIZATION_POLICY =
    existing_fixed_three_player_36_position_contract

MATCH_COMMENTARY_MATERIALIZATION_POLICY =
    remain_workspace_sidecar_without_analysis_influence
```

These contracts remain internal. Issue #168 consumes them through explicit
private browser analysis and download actions without itself changing the then-
current Package version, Public API contract version `1`, the seven Root
workflows, the Root, Session, or Capture CLI contracts, Workspace persistence,
Historical Game version `1`, Training Dataset version `1`, fixed-list version
`1`, or any public export.

## Two evidence boundaries

Decision Review Preparation and strict Historical materialization intentionally
have different evidence requirements.

A Decision is preparable when the acting Player's exact current playable hand
can be reconstructed. This supports Perspective-Player Decisions in a partial
trace when the retained Perspective evidence determines that hand, and all 30
Player Decisions when one complete legal trace determines every playable hand.

A strict Historical Game is materializable only when the observed Game has a
Declarer and complete Declaration including `bid_value`, a complete legal
30-Play trace, known original Skat, and exact Discards. For Hand Games, exact
Discards means the retained empty array. Those facts must reconstruct the
complete original 32-Card Deal. Decision preparation may retain an unknown bid
as null because own-hand reconstruction does not depend on it.

A complete trace can therefore make every Decision preparable while Historical,
Training source, and played-list materialization remain unavailable because
original Skat or Discards are unknown. No missing Card is completed from a deck
complement merely to cross the stricter boundary.

## Observed reconstruction

`build_match_observed_game_reconstruction_v1()` validates one observed trace and
retains only exactly reconstructable playable hands. For a partial trace, the
existing observed-Game rules provide the Perspective playable hand only for:

* a Defender with a known Perspective initial hand;
* a Hand Declarer with a known Perspective initial hand;
* a non-Hand Declarer with a known Perspective initial hand, original Skat, and
  exact Discards.

For a complete legal trace, each Player's ten observed Cards reconstruct that
Player's playable starting hand. This later evidence may be used only to recover
the acting Player's own hand at that Player's Decision. It does not authorize an
opponent hand in the snapshot, and a non-Hand Declarer's playable hand is not
treated as the original dealt hand.

Reconstructed hands are derived values. They are not written back into the
observed Game or persisted Workspace.

## Decision Review Preparation

`build_match_decision_review_preparation_v1()` validates the Workspace, requires
one observed-Game Slot, prepares Match Player Statistics once, validates the
trace once, and traverses retained Plays in source order. Its result has status:

```text
available     every retained Play has one prepared snapshot
partial       at least one but not every retained Play is prepared
unavailable   no retained Play is prepared
```

Every Play is represented exactly once by either an existing immutable
`HistoricalDecisionSnapshot` or a `MatchSkippedDecisionV1`. Canonical skip
reasons are:

```text
acting_hand_unavailable
required_public_hand_unavailable
```

The summary retains source Play, prepared, and skipped counts; snapshots,
skipped Decisions, and Profile bindings preserve Decision order.

### Decision-time cutoff

Each prepared snapshot represents the state immediately before the observed
Card is played. It contains the acting stable Player, seat and side, relative
`me`/`left`/`right` map, exact acting hand, legal Cards, prior completed Tricks,
the current incomplete Trick, prior points, public opponent hand sizes, and
authorized Skat or exposed-Card information.

The visible state is built before `actual_card_played` is attached. The actual
Card is retrospective evidence, not an input to legal-card derivation,
recommendation, or any other Decision-time field. No recommendation or quality
classification is computed by this layer.

Future observed Plays may reconstruct the acting Player's own playable hand.
They must not expose future opponent ownership, future public Trick state,
future points, final Result, Settlement, tactical intent, Commentary, or Response
Links. Earlier visible state therefore remains independent of later opponent
Card ownership and order except for public hand-size arithmetic.

### Skat visibility

The existing Historical snapshot semantics remain authoritative:

* a non-Hand Declarer sees exact retained Discards as the current Skat with
  `known_to_declarer`;
* a non-Hand Declarer without exact Discards has `unknown` Skat;
* a Defender never receives original Skat or Discards as decision-time Skat;
* a Hand Declarer has `unknown` Skat.

Later observer knowledge does not become Defender knowledge.

### Declared Ouvert

For declared Ouvert, the exact shrinking Declarer playable hand is public only
when it is reconstructable. It is included in `public_exposed_cards` for every
relevant snapshot at its Decision-time size. If the acting hand is known but the
required public Declarer hand is not, that Decision is skipped with
`required_public_hand_unavailable`; the layer does not invent an Ouvert hand from
an incomplete trace.

### Relative Profile bindings

Each prepared snapshot receives one
`MatchDecisionOpponentProfileBindingV1`. Left and right are resolved from that
Decision's acting-Player-relative circular map. The acting Player's own Snapshot
is never used as an opponent binding.

Temporal statuses and Profile availability come from the existing Match Player
Statistics Contexts. Only Snapshots with `captured_at < match.played_at` can
provide an eligible Profile or actionable preset. Bindings report those values
for later use but apply no Profile, preset, opponent policy, override, or
recommendation setting.

## Strict Historical materialization

`materialize_match_observed_game_historical_v1()` returns an available existing
`HistoricalGameRecord` or normal unavailability. Canonical unavailable reasons
are:

```text
slot_empty
passed_deal
declaration_unavailable
incomplete_play_trace
original_skat_unavailable
discarded_cards_unavailable
```

Available materialization uses only the existing normal-completion contract. It
creates three Players in canonical historical-seat order, exact initial ten-Card
hands, original Skat, exact Discards, the retained Declaration, ten complete
Tricks, and `game_end_reason = normal_completion`. It creates no Game End or Game
Event and does not reinterpret Commentary.

Defender and Hand-Declarer initial hands equal their complete playable hands.
The non-Hand Declarer's original hand is reconstructed as:

```text
original Declarer hand = playable hand + discarded Cards - original Skat
```

The raw value is built through `build_historical_game_record()`, serialized with
the existing canonical serializer, rebuilt, and required to compare equal. The
existing Historical summary must report a complete Game and complete Settlement.
No shortened Historical Game is synthesized from a partial observed trace.

## Match-level played time

Every materialized Historical Game and Passed Deal uses the optional
`match_definition.played_at`. If that value is null, the materialized value
remains null. Game and Decision media offsets are not converted to RFC 3339
timestamps, so all positions in one Match may retain the same Match-start
instant. Media timecodes remain private Workspace evidence and do not create a
false within-Match absolute ordering.

## Training source Records

Strict available Historical materialization can produce one existing immutable
`UnpartitionedTrainingDatasetRecord`. Its deterministic ID is:

```text
{match_id}-record-{match_position:02d}
```

The existing Training Provenance uses `manual_entry`, the Match source title,
the observed Game ID as `source_record_id`, and null `collected_at` and `notes`.
Record, Game, and complete source identities are validated for uniqueness.

`MatchTrainingSourceCollectionV1` retains available Records in Match-position
order and separately reports unavailable positions. Passed Deals and observed
Games without strict Historical materialization produce no Record.

These are unpartitioned source Records only. This layer creates no Dataset ID,
Dataset mode, partition, weights, seed, Plan, audit, preparation Request, sample,
feature, or label conversion. Existing public Dataset preparation and ordinary
sample generation remain separate workflows.

## Workspace and fixed-list materialization

`build_match_workspace_materialization_v1()` validates one Workspace, prepares
Player Statistics once, traverses exactly 36 Slots in Match-position order, and
returns one per-Slot value containing evidence, Decision preparation when an
observed Game exists, Historical and Training-source availability, and
Commentary/Response counts.

Workspace materialization status is:

```text
empty      no Slot is occupied
partial    at least one Slot is occupied but full-list materialization is absent
complete   the existing 36-position historical list is available
```

The summary reconciles prepared and skipped Decisions, materialized Historical
Games, Training source Records, Passed Deals, Commentaries, and Response Links.
`complete` does not mean every Commentary was interpreted or a Dataset was
partitioned.

### Passed Deals

Passed Deals remain authoritative occupied Match positions. They create no
synthetic Game ID, Historical Game, or Training source Record. In a complete
fixed list they become existing `passed_deal` entries with deterministic Entry
IDs and Match-level `played_at`, and they continue to advance the existing Dealer
rotation.

### Complete 36-position list

Full-list materialization is available only when no Slot is empty and every
observed Game has strict Historical materialization. Otherwise the result reports
`workspace_not_structurally_complete` or
`observed_game_not_historical_materializable` and the exact unavailable
positions.

An available result reuses the existing fixed-three-player list builder with:

```text
list_id = {match_id}-list
entry_id = {match_id}-entry-{match_position:02d}
```

It preserves Match participant order, stable IDs, labels, fixed table places,
all 36 positions, exact seat rotation, played Games, and Passed Deals. It then
uses the existing aggregation builder, Progression, SkWO standings, unresolved
`lot_required` behavior, and optional exact external `lot_order`. It generates no
random lot and does not execute list comparison.

## Commentary boundary

Commentary and Response Links remain authoritative private Workspace sidecars.
Their counts are reported for traceability, but their text and links do not
influence Play validation, Decision snapshots, Profile preparation, policy
settings, Historical Result or Settlement, Training Dataset version `1`, or the
fixed-list contract. No Commentary text is copied into Historical Games or
Training source Records.

## Issue #168 execution boundary

Issue #168 selects one prepared snapshot and executes the existing Position
Application once with explicit Immediate, bounded Search, or `auto` settings.
The resulting flat Position is nonterminal post-game review: the observed Card
is attached as retrospective evidence after the Decision-time state, not as an
optimal label. A partial preparation can therefore support one Decision even
when strict Historical materialization is unavailable.

Eligible relative Profile bindings enter only the existing Application path.
The acting Player is excluded from opponent bindings; disabled Profile Presets
and eligible but nonactionable derivations change no policy. Profiles are not
Search-world weights and do not alter bounded Search.

For one strictly available Historical Game, Issue #168 executes the existing
Historical Application once with at least one selected Snapshot, Immediate
Review, Search Review, or Replay Coaching mode. Historical Profiles are injected
only for enabled Immediate Review and existing Profile-Preset behavior. This is
not a claim that Profiles affect Search Review or Coaching. Commentary and
Response Links remain outside all analysis inputs and Coaching.

The Match-wide materialization browser action still invokes no Root workflow. It
prepares the existing 36-Slot materialization once and presents counts,
Historical unavailability, Training sources, fixed-list standings, unresolved
lot state, and twelve round ends. Canonical private browser downloads expose the
materialization, available Historical collection, Training source collection,
and available list input/aggregation. See
[Match analysis and exports](match_analysis_and_exports.md).

## Execution and public boundaries

Issue #167 itself still performs no file Load/Save or workflow execution and
changes no Workspace persistence bytes. Issue #168 adds a separate explicit
private browser execution layer over those values. Reports remain ephemeral and
are not persisted in the Workspace; downloads are caller-initiated responses,
not server-side report files.

There is still no Match Root workflow, Public Match API, Match Schema or JSON/data
workflow, additional Capture CLI option, public Match export, example, or
generated scenario. Materialization does not execute Dataset conversion, Dataset
partitioning, list Root workflow, list comparison, or any analysis.

The unchanged baselines are:

```text
Package version: 0.15.0
Root workflows: 7
Authoritative and packaged Schemas: 63
Session examples: 6
Generated-output scenarios: 85
```

Existing examples, Public API and CLI exports, Historical, Dataset, fixed-list,
Profile, Provenance, Session, Match Capture, and Workspace contract versions are
unchanged.

Issue #168 completes the functional `v0.15.0` local Match Capture milestone.
Issue #169 completed Package version `0.15.0` and release-documentation
preparation without product behavior changes. The maintainer published the
Release manually at commit `ec1c154`, and Issue #170 synchronizes publication
status. Public Match
contracts, Match Schema and JSON/data workflow, a public/persisted Player Catalog,
communication-aware Dataset work, database/remote deployment, and broader pre-v1
work remain open. YouTube and EuroSkat integration also remain absent. Persistent
Workspace reports are intentionally not added.
