# Interactive session contracts

Issue #150 begins the `v0.14.0` interactive-capture milestone with an internal,
immutable contract foundation. Issue #151 makes that language executable through
deterministic internal transitions and incremental validation. Issue #152 exports
Historical-ready Retrospective Sessions to canonical existing Historical Game
Requests. Issue #153 adds information-safe Position Request export, declared-
Ouvert public-hand capture, and immutable pre-Play Decision Checkpoints. Issue
#154 adds immutable strict-prefix Undo, one-command correction, deterministic
suffix replay, partial corrected States, and Checkpoint lineage. Persistence,
Public API, Provenance, Schemas, CLI, and end-to-end capture remain later layers.

## Contract identity

The independent internal versions are:

```text
SESSION_CONTRACT_VERSION = 1
SESSION_COMMAND_VERSION = 1
SESSION_TRANSITION_ENGINE_VERSION = 1
SESSION_PROJECTION_VERSION = 1
SESSION_REPLAY_POLICY = full_accepted_log_before_apply
SESSION_REQUEST_EXPORT_VERSION = 1
SESSION_REQUEST_EXPORT_POLICY = existing_root_request_contract
SESSION_HISTORICAL_EXPORT_POLICY = exact_ready_retrospective_state
SESSION_POSITION_EXPORT_OPTIONS_VERSION = 1
SESSION_POSITION_EXPORT_POLICY = information_safe_ready_local_decision
SESSION_DECISION_CHECKPOINT_VERSION = 1
SESSION_DECISION_CHECKPOINT_POLICY = frozen_pre_play_request
SESSION_DECISION_INFORMATION_CUTOFF = before_local_play
SESSION_HISTORY_EDIT_VERSION = 1
SESSION_UNDO_POLICY = immutable_strict_prefix_rewind
SESSION_CORRECTION_POLICY = replace_one_command_then_replay_suffix
SESSION_CORRECTION_SUFFIX_POLICY = stop_before_first_rejected_command
SESSION_HISTORY_STATE_POLICY = accepted_log_length_per_immutable_state
SESSION_BRANCHING_POLICY = unsupported
SESSION_REDO_POLICY = caller_retained_suffix_only
SESSION_CHECKPOINT_LINEAGE_VERSION = 1
```

They do not derive from Package version `0.13.0`, Public API version `1`,
Application orchestration version `1`, installed CLI version `1`, Provenance
versions, Root Schema versions, Historical Game version, or another Domain
version.

The stable policies are:

```text
SESSION_STATE_POLICY = command_log_authoritative
SESSION_REVISION_POLICY = linear_append_only
SESSION_REJECTED_COMMAND_POLICY = not_recorded
SESSION_MODE_TRANSITION_POLICY = live_to_retrospective_only
SESSION_IDENTIFIER_POLICY = caller_supplied
SESSION_TIME_POLICY = caller_supplied_or_null
```

No Session or Command ID, timestamp, filesystem path, environment value, branch,
or merge identity is generated.

## Layer boundary

The intended flow is:

```text
Session Commands
    -> immutable accepted Session State
    -> validation and export readiness
    -> canonical Position Analysis Request export and optional Checkpoint
    -> canonical Historical Game Request export
```

Commands are applied atomically, the full accepted Log can be replayed into an
immutable projection, phases and Validation are recomputed, and both export
targets receive normal readiness status. Issues #152 and #153 implement the
Historical and Position exporters; Issue #153 can freeze an available local pre-
Play Position export as a Decision Checkpoint. Issue #154 can derive another
immutable State from a strict accepted prefix or one replacement plus the valid
original suffix, and can classify the frozen Checkpoint against that history.
There is no parser, persistence loader, Public Session API, or Session Root
workflow.

`GameState` remains the mutable local analysis and simulation value.
`HistoricalGameRecord` remains the strict immutable final historical contract.
Neither is embedded in or weakened for Session State.

## Players

`SessionPlayerV1` is frozen, slotted, and keyword-only. It contains:

```text
player_id
player_label
seat
```

The Player ID is a caller-supplied, non-empty, non-padded stable identity and
cannot use Position-relative `me`, `left`, or `right`. The nullable label is
display metadata. Player identity contains no hand or game state.

Every Session has exactly three unique Players and exactly one existing
Historical seat each:

```text
forehand
middlehand
rearhand
```

State construction canonicalizes Players to that seat order. Four-player
Sessions are rejected.

## Capture modes

The modes are:

```text
live
retrospective
```

An initially Live Session requires one declared `local_player_id`. It remains
Live until exactly one accepted `promote_to_retrospective` Command, after which
it is Retrospective and preserves the local Player identity.

An initially Retrospective Session remains Retrospective. Its local Player may
be null or one declared Player, and its accepted Log cannot contain a promotion.
Retrospective-to-Live transitions and multiple promotions are invalid.

Promotion adds no opponent hand, Skat, Discard, ownership, event, or Game End.
It preserves every earlier Command and cannot rewrite an earlier information
cutoff.

## Phases

The canonical phases are:

```text
setup
deal
declaration
skat_and_discard
play
ended
```

`setup` establishes Session identity, Players, Mode, local perspective, and
optional metadata. `deal` represents incremental authorized card entry.
`declaration` represents Declarer and final Declaration entry.
`skat_and_discard` represents authorized non-Hand Skat and Discard facts, while
Hand Games require no Discards. `play` represents public Plays and supported
events. `ended` represents normal completion or one supported terminal end.

Issue #151 Command application advances phases monotonically. No Command sets a
phase. Issue #154 Undo may derive another immutable State at an earlier accepted
revision, and correction may rederive a phase from changed accepted facts.
Version 1 has no mutable active head or branching.

## Commands

Every Command is frozen, slotted, keyword-only, versioned, and contains its
class-defined `kind`, `command_version`, and non-negative
`expected_revision`. Booleans are not revisions. Caller kind overrides are
rejected.

The closed version-1 union is, in canonical order:

| Kind | Caller payload |
| --- | --- |
| `set_game_metadata` | Nullable `game_id` and nullable RFC 3339 `played_at`; at least one is non-null. |
| `record_dealt_card` | One valid Card, destination `player_hand` with one stable Player ID or destination `skat` with null Player ID. |
| `set_declarer` | One stable Declarer Player ID. |
| `set_declaration` | One existing validated `GameDeclaration`. |
| `record_discard` | One valid Card. |
| `record_play` | One stable Player ID and one valid public Card action. |
| `set_game_event` | One recursively immutable JSON object using an existing declarer-card-exposure or defender-open-play continuation kind. |
| `set_game_end` | One existing supported Historical end reason and a recursively immutable terminal JSON object, or normal completion with null details. |
| `promote_to_retrospective` | No payload. |
| `set_public_hand` | Source `declared_ouvert`, one stable Declarer Player ID, and the exact canonical current public Card array. |

Card notation, Declaration dependencies, RFC 3339 parsing, continuation-kind
names, and Historical Game-end reason names reuse existing contracts. Event and
end objects are not adjudicated. Commands contain no resulting revision, phase,
legal-card list, turn, trick result, score, Settlement, Recommendation, Search
Result, generated time, arbitrary note, or inferred ownership.

The immutable allowed-phase metadata is:

| Command | Allowed phases |
| --- | --- |
| `set_game_metadata` | `setup`, `deal`, `declaration`, `skat_and_discard`, `play` |
| `record_dealt_card` | `setup`, `deal`, `declaration`, `skat_and_discard` |
| `set_declarer` | `declaration` |
| `set_declaration` | `declaration` |
| `record_discard` | `skat_and_discard` |
| `record_play` | `play` |
| `set_game_event` | `play` |
| `set_game_end` | `play` |
| `promote_to_retrospective` | every phase |
| `set_public_hand` | `play` |

Issue #151 enforces this metadata before Command-specific validation.

## State and accepted Log

`SessionStateV1` contains exactly:

```text
session_contract_version
session_id
initial_capture_mode
capture_mode
revision
phase
players
local_player_id
command_log
validation
```

The caller supplies the stable Session ID. The accepted Command Log is the
authoritative history; State has no mutable projection, Engine State, Search
State, cache, random stream, result, generated timestamp, or path.

`SessionCommandRecordV1` pairs resulting positive revision `n` with a Command
whose expected revision is `n - 1`. An accepted Log begins at `1`, is contiguous,
and has no duplicates or gaps. State revision equals accepted Log length;
revision `0` has an empty Log. Rejected Commands and revision conflicts are not
new accepted records.

State construction retains the Issue #150 structural checks for Player
references, promotion and Mode relationships, revision continuity, and Live
hand-entry protection. Issue #151 deliberately keeps derived projection data out
of State and replays the authoritative Log to validate Deal cardinality, cross-
Command Card identity, known ownership, legal play, Turn Order, phase
progression, Declaration readiness, continuation chronology, and Game-end shape.
It does not adjudicate an ending.

## Information policy

Before Live promotion, transitions permit only the local concrete
initial hand, forbid concrete opponent hands and actual hidden ownership, accept
concrete Skat only when legitimately known, and accept public Plays or authorized
public hands. Search, inference, simulation, or recommendation output can never
be recorded as actual ownership.

Issue #153 permits one narrow `declared_ouvert` public-hand Command during Play.
It requires the exact current Declarer hand, validates remaining-card count and
ownership conflicts, and cannot introduce an arbitrary private opponent hand.
Declared-Ouvert and continuation public hands coexist by stable owner and shrink
only when that owner Plays.

Retrospective capture records exact three hands, exact Skat, Discards, and exact
Plays. Incremental validation reconciles those facts with exact ownership and
legal replay. Issue #152 exports these facts only after exact Historical
readiness. Promotion preserves every existing fact and phase while switching
future requirements to Retrospective rules.

## Diagnostics and readiness

`SessionValidationDiagnosticV1` contains one stable code, canonical RFC 6901
path, human message, severity, and separate Command, Position-export, and
Historical-export block flags. The canonical severities are `error`, `warning`,
and `info`. Only an error may block a Command.

The initial code registry is:

```text
missing_required_value
invalid_value
phase_violation
player_reference_violation
card_identity_violation
card_ownership_violation
turn_order_violation
declaration_violation
information_policy_violation
event_sequence_violation
game_end_violation
export_unavailable
revision_conflict
history_revision_violation
```

Diagnostics are unique and ordered by severity, path, code, then message.

`SessionExportReadinessV1` uses target `position_analysis` or `historical_game`
and status `available` or `unavailable`. Available has no reason codes;
unavailable has at least one unique, canonically ordered code. Unavailability is
a normal status, not an exception and not an automatic export attempt.

`SessionValidationResultV1` records the matching revision and phase, structural
validity, valid-incomplete status, game completeness, both readiness values, and
ordered Diagnostics. `valid_incomplete` means structurally valid and not game
complete. Game completeness is equivalent to phase `ended`. A structurally
invalid Session has both exports unavailable, Historical export requires a
complete game, and export reason codes exactly reconcile with blocking
Diagnostics. Issue #151 recomputes these values from the accepted projection at
revision zero and after every accepted Command. State Diagnostics describe only
current export blockers and never retain a rejected Command's Diagnostics.

## Transition results

`SessionTransitionResultV1` has statuses:

```text
applied
rejected
revision_conflict
```

An applied result matches expected and previous revision, increments exactly
once, returns State at the current revision, places the accepted Command in the
final Log record, and has no Command-blocking Diagnostic.

A rejected result matches expected and previous revision, leaves current
revision and returned State revision unchanged, adds no accepted record, and has
at least one Command-blocking Diagnostic.

A revision conflict has an expected revision different from the current previous
revision, leaves the revision and returned State revision unchanged, adds no new
accepted record, and contains exactly one blocking `revision_conflict`
Diagnostic. This result can describe a stale retry even when an equal Command
was accepted at an earlier revision.

Issue #151 implements the versioned internal
`apply_session_command_v1(state, command)` function. It replays the prior Log
once, handles revision conflicts before candidate semantics, applies at most one
candidate, and returns these existing Result values. The unversioned name remains
absent.

`create_session_state_v1()` builds the canonical revision-zero State.
`replay_session_state_v1()` replays the full accepted Log and requires the
derived Capture Mode, phase, revision, and Validation to equal stored State.
Forged or semantically invalid accepted State raises `SkatAIInvariantError`.
Normal next-Command rejection is not an exception.

## History editing and Checkpoint lineage

Session History Edit version `1` keeps one immutable linear accepted Log per
State. `rewind_session_state_v1()` replay-validates the source once and rebuilds
an earlier accepted prefix from revision zero. Applied Undo returns the exact
removed source suffix. A current target is unchanged, a target beyond the source
is rejected with `history_revision_violation`, and a mismatched expected revision
returns `revision_conflict` before target-range semantics.

`SessionCommandCorrectionV1` replaces one positive accepted revision with one
current Command whose expected revision matches that position.
`correct_session_command_v1()` rebuilds the preceding prefix, applies the
replacement once, and linearly replays original later Commands. Complete replay
is `applied`; exact equality is `unchanged`; replacement failure is `rejected`;
and the first invalid later Command returns a valid `partial` State plus exact
replayed and discarded source records. No later source Command is evaluated.

Every resulting State derives current Capture Mode, phase, Validation, and both
readiness values from its actual active Log. Removed and discarded records live
only in operation Results. Undo and correction are not Commands and create no
branch or stored Redo stack.

`classify_session_decision_checkpoint_v1()` reproduces the exact accepted prefix
and expected Position Request where possible. Its relationships are `current`,
`ancestor`, `future`, and `diverged`. Checkpoints remain separate immutable
values; no source revision, Request, actual Card, or Result is rewritten. See
[Session Undo, correction, and Checkpoint lineage](session_undo_and_correction.md).

## Serialization

Every Session value has deterministic internal `to_dict()` serialization with
stable field order, canonical tuple order, explicit nulls, and fresh mutable
JSON-compatible copies. Caller JSON payloads are copied recursively into
immutable mappings and tuples with deterministic object-key order.

Serialization includes no Python class-name protocol field, generated identity,
generated timestamp, environment value, or filesystem path. There is no Session
Schema or persistence loader.

The separate frozen `SessionProjectionV1` retains metadata, canonical initial
and remaining known hands, known Skat, Declarer, Declaration, Discards,
chronological Plays, completed and incomplete trick state, next Player, optional
continuation, owner-keyed shrinking exact public hands, the accepted declared-
Ouvert public-hand marker, optional Game End, and Play count.
Unknown private hands are absent. Projection serialization is internal and is not
added to `SessionStateV1`.

## Boundaries and remaining work

Session contracts are internal. They are not exported from `skat_ai`,
`skat_ai.api`, `skat_ai.api.v1`, or `skat_ai.errors`. The seven Root workflows,
Public API functions, installed/module/Legacy CLI, 62 Schemas, examples, and 77
generated-output scenarios are unchanged. Package version remains `0.13.0`.

Internal canonical Retrospective Historical Request export is implemented. It
returns an immutable available/unavailable result, replays once, invokes no
Historical builder while unavailable, and constructs but does not execute the
existing `RequestDocumentV1`. See
[Retrospective Session export](retrospective_session_export.md).

Information-safe Position Request export and immutable pre-Play Decision
Checkpoints are also implemented without workflow execution. See
[Session Position export and Decision checkpoints](live_session_position_export.md).

Remaining `v0.14.0` work includes persistence and resume, Session-triggered
analysis, actual-card Checkpoint attachment, Public Session
API, Session Provenance, Session Schemas, CLI Session Assistant, examples,
generated outputs, automatic Checkpoint collection, end-to-end capture, and any
later local interface. No UI technology or platform integration is selected.
See [Incremental Session transitions](incremental_session_transitions.md).
