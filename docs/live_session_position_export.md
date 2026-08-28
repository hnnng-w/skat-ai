# Session Position export and Decision checkpoints

Issue #153 adds the internal version-1 export from one Position-ready Session to
the existing flat Position Analysis Root Request. It also adds an immutable
Checkpoint that freezes and identifies one replay-verified local pre-Play
Request. Neither operation executes Position Analysis.
Issue #154 classifies that frozen Checkpoint against immutable edited Session
histories without changing the export or executing analysis. Issue #155 can
persist caller-supplied Checkpoints alongside the unchanged active State and
strictly Resume both.

## Contract identity

The independent constants are:

```text
SESSION_POSITION_EXPORT_OPTIONS_VERSION = 1
SESSION_POSITION_EXPORT_POLICY = information_safe_ready_local_decision
SESSION_DECISION_CHECKPOINT_VERSION = 1
SESSION_DECISION_CHECKPOINT_POLICY = frozen_pre_play_request
SESSION_DECISION_INFORMATION_CUTOFF = before_local_play
SESSION_PUBLIC_HAND_SOURCES = (declared_ouvert,)
```

Session Request Export version `1` and policy
`existing_root_request_contract` now apply to both existing targets:

```text
position_analysis
historical_game
```

These additions do not change Session, Command, transition, projection,
Position input, Public API, Application, CLI, Schema, or Provenance versions.
Package version is `0.17.0`. Session Persistence version `1` is independent
of the export-options and Decision-Checkpoint versions.

## Position export options

`SessionPositionExportOptionsV1` is frozen, slotted, keyword-only, recursively
immutable, and contains:

```text
session_position_export_options_version
sample_count
random_seed
use_basic_opponent_strategy
recommendation_method
bounded_search_settings
```

The sample count is an integer from `1` through `100000`; the seed is a strict
integer; and opponent-strategy selection is a strict Boolean. Recommendation
method and bounded-Search settings reuse the existing Position configuration
validation and canonical serialization. Search settings are required exactly
for `bounded_search` and `auto`, forbidden for omitted or Immediate methods, and
copied defensively.

These values are caller-supplied analysis configuration. They are not retained
in Session State and do not start analysis during export.

## Replay and readiness gate

`export_session_position_analysis_request_v1(state, options)` requires the exact
internal State and options types. It performs one full accepted-Log replay and
uses the replay-verified Position readiness value.

Export is available only when the Session is in `play`, has a local Player who
is next, has complete Declarer and Declaration facts, has an exact non-empty
local playable hand, has coherent current-trick state, and has no Game End.
Opponent-declarer Ouvert additionally requires the exact current public
Declarer hand.

Unavailable readiness returns `SessionRequestExportV1` with target
`position_analysis`, no Request, and only current Position-blocking Diagnostics.
It invokes no Position builder. If readiness says available but replayed facts
cannot produce a valid existing Position document, the exporter raises
`SkatMindInvariantError` and retains the underlying builder failure as its cause.

## Stable-to-relative mapping

The exporter maps the local stable Player to `me`, the next Player in canonical
forehand-middlehand-rearhand seat order to `left`, and the preceding Player to
`right`. That circular map is used for Declarer, trick actors, winners,
continuation participants, and hand-size fields. Stable Player IDs, labels,
Session identity, revision, Mode, Log, and Validation do not enter the Position
document.

The existing flat Position document receives:

* accepted Game Type, role, Declarer, local seat, and Declaration;
* the exact current local hand;
* completed tricks with relative actors and verified winners;
* the current incomplete trick and rule-derived leader;
* zero explicit outside-history points because all accepted won points are
  already represented exactly once by attributed completed tricks;
* exact remaining left and right hand sizes derived from accepted Plays;
* local non-Hand Declarer knowledge represented by the two discarded Cards;
* current authorized continuation public hands where present;
* explicit analysis settings from `SessionPositionExportOptionsV1`;
* fixed `analysis_mode = live_decision` and `game_end_reason = not_ended`.

`played_cards` is empty because all accepted public Plays are represented by
`completed_tricks` and `current_trick`. Matadors are recomputed only from facts
visible to the local Player before the decision. The exporter does not copy a
final Retrospective Matador count into a decision Request.

The provisional document is validated through the existing Position builder and
wrapped as:

```python
RequestDocumentV1(
    workflow=WorkflowV1.POSITION_ANALYSIS,
    document=validated_position,
)
```

The exporter constructs no Application invocation and calls no Application,
Public API, Immediate, Search, inference, simulation, recommendation, review,
score, Result, Value, Overbid, Settlement, or file-I/O path.

## Declared-Ouvert public hands

`SetSessionPublicHandCommandV1` appends `set_public_hand` to the closed Command
version-1 union. Version `1` accepts only source `declared_ouvert`. The Command
contains one stable Player ID and one canonical exact current Card array and is
allowed only during `play`. The Card array must be non-empty.

Transition validation requires an ongoing Ouvert Declaration, the stable
Declarer as owner, exactly the owner's remaining-card count, no played,
discarded, or Hand-Skat Card, and no conflict with another exact known or public
hand. A Session accepts at most one declared-Ouvert public-hand Command. The
accepted projection records that source marker and shrinks the public hand when
its owner Plays.

Declared-Ouvert and continuation public hands are stored by owner and may
coexist. Recording either source does not replace another Player's public hand.
The Position Request exposes only the exact hands authorized by the Declaration
or accepted continuation. An opponent Declarer's Ouvert cards use the existing
`public_declarer_cards` field; a local Declarer's cards remain the local `hand`.

Retrospective Sessions with exact ownership may satisfy opponent-Ouvert
readiness from the exact remaining Declarer hand without a redundant public-hand
Command. Live Defenders must record the legitimately public hand explicitly.

## Decision checkpoint

`SessionDecisionCheckpointV1` is frozen, slotted, keyword-only, recursively
immutable, and contains:

```text
session_decision_checkpoint_version
session_id
source_revision
source_capture_mode
decision_index
trick_number
play_index
acting_player_id
acting_seat
information_cutoff
relative_player_map
request
```

Decision indexes are one-based from `1` through `30`; trick numbers are `1`
through `10`; play indexes are `1` through `3`; and all three reconcile exactly.
The acting Player is the stable local Player at the source revision. The
relative map contains exactly `me`, `left`, and `right`, identifies three unique
stable Players, and maps `me` to that actor. The embedded immutable Request must
target Position Analysis and describe the matching local live-decision position
before the Play.

`build_session_decision_checkpoint_v1(state=..., position_export=...)` accepts
only an available Position export from the same Session and revision. It replays
the State once, reconstructs the expected Position Request from the embedded
analysis options without another replay, and requires exact export equality.
Forged identity, revision, options, mapping, or Request content raises
`SkatMindInvariantError` or contract validation failure.

A Checkpoint is not appended to Session State and is not updated after later
Play, event, promotion, or other accepted Commands. It has no generated ID,
timestamp, fingerprint, actual Card, Result, private ownership, Search World,
Provenance sidecar, or execution output. Persistence fingerprints belong to the
separate wrapper document, not to the Checkpoint or State.

Issue #157 preserves that immutability. A separate Decision Observation derives
the first later accepted local Play from the authoritative Log. A separate review
export copies the frozen Request and adds only post-game-review mode plus that
observed Card. Neither value mutates the Checkpoint or is persisted. See
[Session Decision observations](session_decision_observations.md).

## Checkpoint lineage after history edits

Checkpoint Lineage version `1` derives one of:

```text
current
ancestor
future
diverged
```

`classify_session_decision_checkpoint_v1()` replay-validates the current State.
When that State reaches the frozen source revision, it reconstructs the exact
accepted prefix and expected information-safe Position Request and compares the
complete expected Checkpoint. Equal revisions reproduce `current`; a later State
with the same effective prefix is `ancestor`; an earlier State is `future`; and a
reached but changed prefix is `diverged`.

Undo and correction do not remove or mutate Checkpoint objects, rewrite their
source revisions or Requests, or attach actual Cards or Results. An edited State
may be passed explicitly to the existing Position exporter, which uses only its
active accepted Log and recomputed readiness. Removed and discarded suffixes do
not influence that export. See
[Session Undo, correction, and Checkpoint lineage](session_undo_and_correction.md).

Issue #155 strict Resume independently reconstructs every optional persisted
Checkpoint and recomputes its `current`, `ancestor`, `future`, or `diverged`
relationship to the resumed active State. It does not trust or persist a prior
lineage Result.

## Current boundary

Public `export_session_position_request()` returns operation `export_position`
with the existing `SessionRequestExportV1`; `build_session_decision_checkpoint()`
and `classify_session_decision_checkpoint()` return the existing Checkpoint and
lineage values. Each wrapper invokes one internal operation and executes no
analysis. Optional provenance covers the outer returned operation value; no
nested Checkpoint sidecar or actual Card is added. Issue #157 adds separate
observation and review-export operation values, public file/CLI orchestration,
six examples, and eight append-only scenarios. There is no eighth Root workflow
or Issue #157 Package-version change. The published `v0.14.0` baseline has 63
authoritative and packaged Schemas, seven Root workflows, and 85 generated-output
scenarios.

Persistence Load/Resume does not invoke this exporter or start Position Analysis;
export itself still performs no file I/O or workflow execution. See
[Session persistence and Resume](session_persistence_and_resume.md).

The Session CLI now collects or reuses exact Position-ready Checkpoints, including
the source immediately before an accepted local Play, and can explicitly execute
Position Analysis or an available Checkpoint review. Equal Checkpoints are
deduplicated; different Requests at one revision remain valid. Collection alone
never starts analysis. Issue #158 completed Release preparation for the
functional `v0.14.0` milestone before manual maintainer publication;
GUI/platform/cloud/encryption work remains open. See
[Interactive Session contracts](interactive_session_contracts.md),
[Incremental Session transitions](incremental_session_transitions.md), and
[Retrospective Session export](retrospective_session_export.md), and
[Session CLI and end-to-end capture](session_cli_and_end_to_end_capture.md).
