# Incremental Session transitions

Issue #151 makes the internal version-1 Session Command language executable. It
adds deterministic revision-zero creation, accepted-Log replay, immutable
projection, atomic Command application, incremental rule validation, and export
readiness calculation. It does not export an Engine Request or add a public
Session workflow. Issue #152 separately consumes its replay and Historical
readiness boundary to construct an internal canonical Historical Request. Issue
#153 consumes Position readiness to construct an existing flat Position Request
and a separately frozen pre-Play Checkpoint without workflow execution.
Issue #154 wraps these immutable States with deterministic strict-prefix Undo,
one-command correction, linear suffix replay, and Checkpoint lineage. Issue #155
adds private persistence and strict Resume around the resulting unchanged State.

## Contract identity

The independent versions and replay policy are:

```text
SESSION_TRANSITION_ENGINE_VERSION = 1
SESSION_PROJECTION_VERSION = 1
SESSION_REPLAY_POLICY = full_accepted_log_before_apply
```

Existing Session contract version `1` and Command version `1` are unchanged.
Package version is `0.14.0`. Public API, Application, CLI, Provenance,
Schema, Historical Game, and other Domain versions remain independent.
Session Persistence version `1` is also independent of the transition and
projection versions.

## Modules

The implementation is separated into:

| Module | Responsibility |
| --- | --- |
| `session_projection.py` | Frozen accepted-fact projection and deterministic internal serialization. |
| `session_incremental_validation.py` | Allowed-phase checks, one-Command candidate validation, rule derivation, and readiness calculation. |
| `session_transitions.py` | Revision-zero State creation, full accepted-Log replay, forged-State verification, conflicts, atomic append, and Transition Result construction. |

These modules are internal. They are not exported from `skat_ai`,
`skat_ai.api`, `skat_ai.api.v1`, or `skat_ai.errors`.

## Initial State

`create_session_state_v1()` accepts caller-supplied Session identity, exactly
three seated Players, Capture Mode, and the optional local Player. It creates:

```text
revision = 0
phase = setup
command_log = ()
initial_capture_mode = capture_mode
```

Validation is calculated immediately and both exports are unavailable. The
builder generates no ID, time, Command, path, environment value, or random data.

## Projection

`SessionProjectionV1` is frozen, slotted, and separate from `SessionStateV1`. It
retains only accepted caller facts and deterministic rule derivations:

* Session, Player, local-perspective, Capture Mode, and phase metadata;
* caller-supplied Game ID and timestamp;
* initial and remaining concrete known hands, with unknown private hands absent;
* known Skat, Declarer, Declaration, and Discards;
* chronological Plays;
* completed tricks, an optional incomplete trick, and next Player;
* at most one typed continuation event and owner-keyed shrinking exact public
  hands, including a separately accepted declared-Ouvert hand;
* Game End reason and typed terminal object;
* played-card count.

Players use forehand, middlehand, rearhand order. Card collections use canonical
deck order. Chronological Plays retain their accepted order. `to_dict()` returns
a deterministic fresh mutable JSON-compatible representation for internal tests.
Projection data is not copied into `SessionStateV1`.

## Replay and forged State

`replay_session_state_v1()` starts from revision zero and applies the complete
accepted Log once. Every accepted record must have its canonical resulting
revision and must pass the same phase, rule, ownership, information-policy,
event, and ending checks used for a new candidate.

Replay recomputes projection, Capture Mode, phase, and Validation. The recomputed
State must equal the supplied stored State. A forged revision, Mode, phase,
Validation value, duplicate Card, illegal Play, or invalid accepted event/end
sequence raises `SkatAIInvariantError`. A normal next-Command rejection remains
a Transition Result rather than an exception.

## Atomic application

`apply_session_command_v1()` performs exactly this sequence:

1. Replay the current accepted Log once.
2. Compare `command.expected_revision` with the current revision.
3. Validate allowed phase.
4. Validate and derive one candidate projection.
5. Return an unchanged rejection or append exactly one accepted record.
6. Recompute phase and Validation.
7. Build the existing `SessionTransitionResultV1` contract.

A revision mismatch is handled before candidate semantic validation. It returns
the exact unchanged State and one blocking `revision_conflict` Diagnostic at
`/command/expected_revision`.

Other rejected Commands also return the exact unchanged State. They add no Log
record, do not advance revision or phase, and do not copy rejection Diagnostics
into State Validation. An applied Command increments revision exactly once and
becomes the final accepted Log record.

## Phase advancement

Phases advance monotonically:

```text
setup
    first accepted Deal card -> deal

deal
    mode-specific complete Deal -> declaration

declaration
    Declarer plus Declaration complete
        Hand -> play
        Live local Defender -> play
        Live local Declarer non-Hand -> skat_and_discard
        Retrospective non-Hand -> skat_and_discard

skat_and_discard
    exact Skat plus two valid Discards -> play

play
    accepted explicit Game End -> ended
```

Metadata and promotion do not change phase. Thirty Plays do not end a Session;
normal completion remains an explicit `set_game_end` Command. No phase
regression exists during normal append. A separate history edit reconstructs
another immutable State from its actual retained or corrected Log and may
therefore derive an earlier phase.

## Deal and Declaration

Incremental Deal validation enforces ten Cards per hand, two Cards in the Skat,
valid Card identity, and no duplicate initial assignment. Before promotion, a
Live Session accepts only the local hand. It accepts the Skat only for the local
non-Hand Declarer during `skat_and_discard`, and never accepts a concrete
opponent hand.

Retrospective capture requires ten Cards for every Player, two Skat Cards, and
exact 32-card accounting before ordinary Declaration entry. Promotion preserves
the current phase and facts. Before Play, its remaining requirements switch to
the Retrospective rules without reopening an earlier phase.

Declarer and Declaration may be supplied in either order and each may be set
once. Player identity and the existing `GameDeclaration` rules remain
authoritative. Concrete Live Matadors are rejected for a Defender and accepted
for a local Declarer only when known ownership verifies them. Complete
Retrospective ownership verifies any supplied count through the existing
matador helper. No new inference algorithm is introduced.

## Skat and Discards

A non-Hand Retrospective Session or Live local-Declarer Session requires the
exact two-card Skat before Discards. Exactly two unique Discards must belong to
the Declarer's hand plus Skat and must not already have been played. The second
accepted Discard derives an exact ten-card playable Declarer hand and advances
to `play`.

Hand Games, Live Defenders, incomplete Skat, wrong ownership, duplicate Cards,
and wrong phases are rejected atomically.

## Play and trick derivation

Play validation enforces:

* forehand as the first leader;
* fixed seat order within a trick;
* the previous rule-derived winner as the next leader;
* at most ten Plays per Player and 30 total;
* no repeated, discarded, or unplayable Hand-Skat Card;
* no conflict with another exact known or public hand;
* exact ownership and `get_legal_cards()` for Retrospective hands, the Live local
  hand, and exact public hands.

An unknown Live opponent hand remains absent. The transition checks only public
facts and does not reject a Play merely because Bedienpflicht cannot be proved.

One `set_public_hand` Command may record the exact current Declarer hand when an
ongoing Declaration is Ouvert. It is accepted only during Play, uses source
`declared_ouvert`, requires the exact remaining-card count, rejects conflicts
with every known/public hand and unavailable Card, and shrinks with later
Declarer Plays. It may coexist with a continuation public hand owned by another
Player.

Completed tricks reuse `get_trick_winner()` and `get_trick_points()` to derive
winner Player, winner side, points, and next leader. Incomplete-trick and next-
Player state are derived after every Play. Score, Result, Value, Overbid, and
Settlement are not calculated.

## Continuations and Game End

Continuation Commands reuse the existing strict Historical continuation
builders. Version 1 accepts at most one event at exactly the current Play
boundary. Stable identities, Game Type, Card conflicts, remaining-card count,
and exact known ownership are validated. The event is not adjudicated. Its exact
public hand shrinks only when its owner later Plays.

Game End Commands reuse `build_historical_game_end()` for shape and identities.
Normal completion requires exactly 30 Plays, no incomplete trick, null details,
and an empty continuation public hand. A supported terminal ending requires
fewer than 30 Plays, a matching non-null typed object, chronological consistency,
and exact remaining-hand reconciliation where known. Terminal adjudication,
claim proof, Result, Value, Overbid, and Settlement are not run.

## Promotion

One explicit `live -> retrospective` promotion is accepted in any phase. It
preserves local Player, phase, Log, and all recorded facts, and infers nothing.
Late promotion does not reopen Deal or Declaration phases and may therefore
remain unavailable for Historical export. Issue #154 correction can replace an
earlier accepted Command and replay the suffix, but it never infers missing facts
or bypasses current phase rules.

## Validation and readiness

`SessionValidationResultV1` is recomputed after every accepted Command. Its
Diagnostics describe current export blockers, never earlier rejected Commands.

Position readiness requires phase `play`, a local Player who is next, complete
Declarer and Declaration, an exact non-empty local playable hand, valid current
trick state, and no Game End. If an opponent is the Ouvert Declarer, readiness
also requires that Declarer's exact current public hand.

Historical readiness requires Retrospective Mode, phase `ended`, stable Game ID,
exact 32-card Deal, complete Declarer and Declaration, valid Hand/Discard state,
an exact incrementally legal Play prefix, valid continuation/end chronology, and
either normal 30-Play completion or one supported terminal ending.

Readiness is a normal available/unavailable status. Issue #151 itself exports
neither Request. Issue #152 now uses Historical readiness as an exact gate;
Issue #153 uses Position readiness as an information-safe exact gate.

## Performance and boundaries

Public `create_session()` and `apply_session_command()` expose revision-zero
creation and atomic application through `skat_ai.api.v1.session`. Application
accepts an exact typed Command or one strictly Schema-parsed Command mapping;
applied, rejected, and revision-conflict outcomes remain normal typed Results.
Each wrapper calls the existing internal function once. Optional complete
returned-value provenance and final Session Result Schema validation do not
replay the transition.

One Command application performs at most one full replay of the prior accepted
Log and one candidate application. It starts no random stream, timeout,
background task, Search, Immediate Analysis, Historical Review, Replay Coaching,
Settlement, Application execution, Public API execution, or history branch.

Root Public API exports, all seven Root workflows, and Application orchestration
remain unchanged. Issue #157 adds installed/module/Legacy Session CLI transport,
six Session examples, and eight append-only scenarios, bringing the `v0.14.0`
Package baseline to 85 generated outputs and 63 Schemas. One Historical export performs one replay, no builder call when
unavailable, or one provisional build, one canonical serialization, and one
canonical rebuild when available. One Position export performs one replay and no
builder call when unavailable or one existing Position build when available. A
Checkpoint builder performs one replay and reconstructs the expected Request
without executing analysis. One Undo adds at most one prefix reconstruction; one
correction adds one prefix reconstruction, one replacement, and one linear suffix
pass that stops before the first rejection; lineage adds at most one prefix and
expected-Request reconstruction. None uses State-level Command application per
suffix record.

Issue #155 persists only the authoritative accepted-Log State plus optional
caller-supplied frozen Checkpoints. Strict Resume verifies the State and content
fingerprints, replays that Log, and recomputes Checkpoint lineage; the resumed
`SessionStateV1` remains compatible with normal Command application, history
operations, and both exporters. Persistence Load/Resume does not automatically
export or analyze. See
[Session persistence and Resume](session_persistence_and_resume.md).

Issue #157 layers public file Save/Load, automatic exact Checkpoint collection,
accepted-Log actual-card observation, explicit Session-triggered analysis, and a
phase-aware Assistant over these unchanged transitions. Ordinary mutation and
Checkpoint collection still execute no analysis. Issue #158 prepares the
completed functional `v0.14.0` milestone as an unpublished Package release
candidate; GUI/platform/cloud/encryption work remains open. See
[Retrospective Session export](retrospective_session_export.md) and
[Session Position export and Decision checkpoints](live_session_position_export.md),
[Session Undo, correction, and Checkpoint lineage](session_undo_and_correction.md),
and [Session CLI and end-to-end capture](session_cli_and_end_to_end_capture.md).
