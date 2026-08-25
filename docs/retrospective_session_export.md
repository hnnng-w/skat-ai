# Retrospective Session export

Issue #152 adds the internal version-1 export from one Historical-ready Session
to the existing canonical Historical Game Root Request. It constructs a Request
only. It does not execute the Historical workflow. Issue #154 edited States use
this same unchanged exporter after readiness is recomputed from their active Log.
Issue #155 resumed States use it in exactly the same way.

## Contract identity

The independent export constants are:

```text
SESSION_REQUEST_EXPORT_VERSION = 1
SESSION_REQUEST_EXPORT_POLICY = existing_root_request_contract
SESSION_HISTORICAL_EXPORT_POLICY = exact_ready_retrospective_state
SESSION_EXPORT_STATUSES = (available, unavailable)
```

This version does not change Session, Command, transition, projection,
Historical Game, Public API, Application, CLI, Schema, or Provenance versions.
Package version is `0.17.0`. Session Persistence version `1` is separately
versioned and does not change this export contract.

## Immutable export result

`SessionRequestExportV1` is frozen, slotted, and keyword-only. It contains:

```text
session_request_export_version
session_id
source_revision
target
status
request
diagnostics
```

For this exporter, an `available` result has target `historical_game`, exactly
one immutable `RequestDocumentV1`, and no Diagnostics. An `unavailable` result
has no Request and retains only the current canonical Diagnostics that block
Historical export. Unavailability is a normal result, not an exception.
Serialization is deterministic and returns fresh JSON-compatible values. Issue
#153 generalizes the same result contract for target `position_analysis` with
matching workflow, document-shape, and target-blocking-Diagnostic invariants.

Session identity and source revision remain in the export result. They are not
added to `historical_game_input`.

## Replay and readiness gate

`export_session_historical_game_request_v1(state)` requires the exact
`SessionStateV1` type and performs one full accepted-Log replay. Replay verifies
that stored Mode, phase, revision, Validation, identity, and accepted Log equal
the deterministic reconstruction.

Export is available only when all three conditions hold:

* current Capture Mode is `retrospective`;
* phase is `ended`;
* replay-verified Historical readiness is `available`.

If readiness is unavailable, the function returns before constructing a
Historical document or invoking the Historical builder. If readiness says
available but the replayed projection, builder, or canonical round trip
disagrees, the function raises `SkatAIInvariantError`. Builder failures are
retained as the exception cause.

Optional caller-supplied `played_at` does not block export. A late-promoted Live
Session with an incomplete Deal remains unavailable even if its phase is ended.
An earlier promotion may become exportable only after accepted Commands provide
every exact Retrospective fact and normal readiness becomes available.

## Projection-to-Historical mapping

The provisional nested document uses only existing Historical fields:

```text
schema_version
game_id
optional played_at
players
skat
declarer_player_id
declaration
discarded_cards
game_end_reason
optional game_end
optional game_events
tricks
```

No Session Mode, phase, revision, Log, Validation, readiness, export status,
projection, option, result, path, generated identity, timestamp, or Provenance
field enters the Historical document.

### Players and Deal

Players retain stable Player ID, optional label, canonical forehand-middlehand-
rearhand seat order, and each exact initial ten-card hand. The exporter uses
`initial_known_hands`, never shrinking remaining hands. The exact known two-card
Skat is preserved. Existing Session readiness and the Historical builder require
these 32 Cards to form the complete deck; Card collections use canonical order.

### Declaration and Discards

The exporter serializes the accepted `GameDeclaration`. For Suit and Grand, a
null Matador count is omitted provisionally so the existing complete-deal
Historical builder infers it. A supplied count must already have survived exact
Session ownership validation and must match the builder's inference. The final
Request uses the rebuilt canonical Declaration. No new Matador algorithm exists.

Null preserves Hand and Ouvert while canonical output omits Matadors, Schneider
announced, and Schwarz announced. Hand Games export an empty Discard array.
Non-Hand Games require and preserve exactly two accepted Discards. The exporter
infers no Discard.

### Tricks and endings

Completed and optional incomplete final Session Tricks map to only:

```text
trick_number
leader_player_id
plays:
    player_id
    card
```

Derived winner, side, points, and next Player are omitted. Flattened exported
Plays must equal the chronological Session projection exactly.

Normal completion requires ten complete Tricks and 30 Plays and omits
`game_end`. A supported terminal record has fewer than 30 Plays, includes the
exact existing serialized Game-end object, and may preserve one incomplete final
Trick. All five current terminal reasons are supported. Export performs no
adjudication or Settlement calculation.

### Continuation events

At most one accepted declarer-card-exposure or defender-open-play continuation
is exported through the existing event serializer. The exact accepted kind,
`after_play_count`, identities, responses, and originally authorized Cards are
preserved. The exporter uses the retained event, not the current shrinking
public hand. Either event may precede normal completion or any currently
supported terminal ending.

## Canonical validation and Request construction

The available path performs one provisional Historical build, one canonical
serialization, and one canonical rebuild. The two immutable
`HistoricalGameRecord` values must be equal. Repeated exports and serialization
of the equal rebuilt record are stable. The canonical nested serialization is
wrapped exactly as:

```json
{
  "historical_game_input": {}
}
```

The returned Request is:

```python
RequestDocumentV1(
    workflow=WorkflowV1.HISTORICAL_GAME,
    document=root_document,
)
```

The exporter does not construct Application options or invocations and does not
call Application or Public API execution.

## Information and execution boundaries

The exporter uses only accepted Session facts, replayed projection values, and
existing Historical builders and serializers. It does not infer opponent hands,
Skat, Discards, ownership, events, or endings. Search, hidden-card inference,
simulation, proof, review, Coaching, score, Result, Value, Overbid, Settlement,
Command application, file I/O, and workflow execution are absent.

Public `export_session_historical_request()` wraps this exporter exactly once as
operation `export_historical`, returning the existing `SessionRequestExportV1`
with target `historical_game`. Available/unavailable behavior is unchanged and no
Historical workflow executes. Optional Session Provenance belongs to the outer
Session Result, not the exported Root Request. Issue #157 exposes this no-
execution operation through `session export-historical`; the separate
`session finalize` command explicitly passes an available Request to the
existing Historical Application once. The published `v0.14.0` baseline has 63
authoritative and packaged Schemas, seven Root workflows, and 85 generated-output
scenarios.

## Current boundary

Position Request export and Decision checkpoints are implemented separately by
Issue #153. Strict-prefix Undo, one-command correction, suffix replay, and
Checkpoint lineage are implemented separately by Issue #154. Removed or
discarded records are absent from the edited State and cannot influence later
Historical export; no history operation executes export automatically. See
[Session Undo, correction, and Checkpoint lineage](session_undo_and_correction.md).

Issue #155 private persistence wraps only the unchanged active State and optional
caller-supplied Checkpoints. Strict Load/Resume verifies fingerprints and the
accepted Log and returns a normal resumed `SessionStateV1`; it neither invokes
this exporter nor executes the Historical workflow. See
[Session persistence and Resume](session_persistence_and_resume.md).

Issue #157 adds public file Save/Load, CLI export/finalize, automatic Position
Checkpoints, Decision Observation/review, examples, generated outputs, and end-
to-end Retrospective capture without changing this exporter. Export itself still
performs no workflow execution. Issue #158 completed Release preparation for the
functional `v0.14.0` milestone before manual maintainer publication;
GUI/platform/cloud/encryption work remains open.
See [Session Position export and Decision checkpoints](live_session_position_export.md)
and [Session CLI and end-to-end capture](session_cli_and_end_to_end_capture.md).

Issue #161 observed Games remain outside Session State and this exporter. An
evidence summary can describe reconstruction capability but does not materialize
a Session Log or Historical Request. A later explicit materialization contract
must preserve the existing readiness and canonical Historical builder boundary.
