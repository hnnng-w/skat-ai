# Interactive session contracts

Issue #150 begins the `v0.14.0` interactive-capture milestone with an internal,
immutable contract foundation. It defines the language that later transition,
export, persistence, Public API, and CLI layers may consume. It does not make
interactive Session capture executable.

## Contract identity

The independent internal versions are:

```text
SESSION_CONTRACT_VERSION = 1
SESSION_COMMAND_VERSION = 1
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
    -> Position Analysis export
    -> Historical Game export
```

Only the contract values and structural relationships in the first two lines
exist. There is no command-application function, phase-advancement engine,
Position exporter, Historical exporter, parser, persistence loader, or Session
Root workflow.

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

Normal command application will advance phases monotonically. No Command sets a
phase, and Issue #150 does not implement phase advancement. A future Undo may
move the active head to an earlier linear revision; version 1 has no branching.

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

Issue #151 will enforce this metadata during actual transitions.

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

State performs only structural validation. It checks declared Player references,
promotion and Mode relationships, and accepted revision continuity. Before
promotion, a Live Player-hand Command may target only the local Player. After
promotion, or in an initially Retrospective Session, every declared Player may
be targeted structurally.

State does not validate complete Deal cardinality, cross-Command Card identity,
actual ownership, legal play, Turn Order, phase progression, Declaration
readiness, or Game-end adjudication.

## Information policy

Before Live promotion, later transitions must permit only the local concrete
initial hand, forbid concrete opponent hands and actual hidden ownership, accept
concrete Skat only when legitimately known, and accept public Plays or authorized
public hands. Search, inference, simulation, or recommendation output can never
be recorded as actual ownership.

Retrospective capture may record exact three hands, exact Skat, Discards, and
exact Plays. Later validation and export must reconcile those facts with exact
ownership and legal replay. Complete private facts remain post-game-only for
Engine export.

Issue #150 structurally enforces the pre-promotion Player-hand restriction and
documents the remaining rules. Issue #151 owns stateful enforcement.

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
Diagnostics. Issue #150 validates supplied values but does not calculate
readiness from a command projection.

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

These are constructor semantics only. No `apply_session_command()` function
exists yet.

## Serialization

Every Session value has deterministic internal `to_dict()` serialization with
stable field order, canonical tuple order, explicit nulls, and fresh mutable
JSON-compatible copies. Caller JSON payloads are copied recursively into
immutable mappings and tuples with deterministic object-key order.

Serialization includes no Python class-name protocol field, generated identity,
generated timestamp, environment value, or filesystem path. There is no Session
Schema or persistence loader.

## Boundaries and remaining work

Session contracts are internal. They are not exported from `skat_ai`,
`skat_ai.api`, `skat_ai.api.v1`, or `skat_ai.errors`. The seven Root workflows,
Public API functions, installed/module/Legacy CLI, 62 Schemas, examples, and 77
generated-output scenarios are unchanged. Package version remains `0.13.0`.

Remaining `v0.14.0` work includes actual Command application, phase advancement,
incremental rule and information-policy enforcement, live and retrospective
capture, Position and Historical exports, Decision checkpoints, Undo and
correction, persistence and resume, Public Session API, Session Provenance,
Session Schemas, CLI Session Assistant, examples, generated outputs, and any
later local interface. No UI technology or platform integration is selected.
