# Session Undo, correction, and Checkpoint lineage

Issue #154 adds the internal version-1 history-edit layer around immutable
Session States. It rewinds one accepted Command Log to a strict prefix, replaces
one accepted Command and replays the original later suffix, and classifies frozen
Decision Checkpoints against the resulting linear history. Issue #155 adds a
separate private persistence wrapper for the resulting active State and optional
caller-supplied Checkpoints, without changing this history layer. Issue #156 adds
stable `rewind_session()`, `correct_session_command()`, and
`classify_session_decision_checkpoint()` wrappers over the existing operations.

## Contract identity

The independent constants are:

```text
SESSION_HISTORY_EDIT_VERSION = 1
SESSION_UNDO_POLICY = immutable_strict_prefix_rewind
SESSION_CORRECTION_POLICY = replace_one_command_then_replay_suffix
SESSION_CORRECTION_SUFFIX_POLICY = stop_before_first_rejected_command
SESSION_HISTORY_STATE_POLICY = accepted_log_length_per_immutable_state
SESSION_BRANCHING_POLICY = unsupported
SESSION_REDO_POLICY = caller_retained_suffix_only
SESSION_CHECKPOINT_LINEAGE_VERSION = 1
```

History Edit and Checkpoint Lineage versions are independent of the Package,
Public API, Application, installed CLI, Session, Command, transition, projection,
Request-export, Position-option, Decision-Checkpoint, Provenance, Schema, and
other Domain versions. Package version remains `0.13.0`. Session Persistence
version `1` is also independent of both versions here.

The canonical Undo statuses are:

```text
applied
unchanged
rejected
revision_conflict
```

The canonical Correction statuses are:

```text
applied
unchanged
partial
rejected
revision_conflict
```

## Immutable source-State model

History operations never mutate the source `SessionStateV1`. The source remains
one immutable accepted Log and may be retained by the caller. A successful edit
constructs another immutable State containing exactly one active linear accepted
Log.

Revision remains:

```text
revision = len(command_log)
```

Undo may lower the numeric revision. A complete one-for-one correction may keep
the same numeric revision while changing the accepted Log. Numeric revision is
therefore not a globally unique history identity. Generation, branch, commit,
merge, active-head, and fingerprint fields are absent. Persisted content
fingerprints and cross-process stale-write detection belong only to the separate
persistence wrapper; State remains the authoritative accepted Log and gains no
persistence field or path.

## Strict-prefix Undo

`rewind_session_state_v1()` first replay-validates the exact source State once.
It then handles revision conflict before target-range semantics.

An earlier valid target reconstructs from the empty revision-zero projection
through exactly the retained accepted prefix. It uses the existing projection-
level Command validator, preserves the original accepted Commands and revision
fields, calculates Validation once from the final projection, and constructs one
canonical State. It does not call normal State-level Command application for
each prefix record.

`SessionUndoResultV1` reports:

```text
session_history_edit_version
status
session_id
expected_revision
source_revision
target_revision
current_revision
state
removed_records
diagnostics
```

An applied result contains the exact source suffix beginning at
`target_revision + 1`. An unchanged result targets the current revision. A target
beyond the source revision is a normal rejected Result with the appended
`history_revision_violation` Diagnostic at `/target_revision`. A stale or future
expected revision returns exactly one blocking `revision_conflict` Diagnostic.
Negative and Boolean revision inputs remain contract errors.

Undo is not a Command. It appends no accepted record and stores no removed suffix
inside the resulting State. Undo Results and removed suffixes are never persisted.

## Mode, phase, and readiness recomputation

The retained Log is authoritative. Prefix reconstruction derives current Capture
Mode, phase, Validation, Position readiness, and Historical readiness from only
the retained Commands.

Consequences include:

* removing Game End returns an ended Session to `play`;
* removing Plays rederives completed and incomplete Tricks and the next Player;
* removing Discards, Declaration, Declarer, Deal Cards, or metadata removes their
  facts and may return to `skat_and_discard`, `declaration`, `deal`, or `setup`;
* removing a continuation or public-hand Command removes that public state;
* removing promotion returns an initially Live Session to current Mode `live`.

Initial Capture Mode, canonical Players, and the local Player identity never
change. No private or public fact is retained after its accepted Command leaves
the active prefix.

## One-command correction

`SessionCommandCorrectionV1` contains:

```text
session_history_edit_version
expected_revision
target_revision
replacement_command
```

The target is positive and no greater than the expected source revision. The
replacement is exactly one current `SessionCommandV1` whose expected revision is
`target_revision - 1`. Every current Command kind is supported through the same
existing validator. There is no deletion, insertion, JSON Patch, multi-command,
or caller-supplied suffix form.

`correct_session_command_v1()` performs one source replay, reconstructs the
prefix immediately before the target, applies the replacement once, and then
replays each original later Command in order through the projection-level
validator. Original suffix Commands retain their payload and original revision
numbers.

`SessionCorrectionResultV1` reports:

```text
session_history_edit_version
status
session_id
expected_revision
source_revision
target_revision
current_revision
replacement_command
state
original_record
replayed_suffix_records
discarded_suffix_records
failed_original_revision
diagnostics
```

An exact replacement equality is an unchanged no-op and evaluates no suffix.
Replacement rejection retains the exact source State and evaluates no suffix.
Complete replay returns `applied`, preserves the source numeric revision, and
reports every original later record as replayed.

If one later original Command becomes invalid, correction stops before it and
evaluates no later source Command. The normal `partial` Result contains the
corrected valid prefix, reports all successfully replayed records, reports the
failed and remaining records as the exact discarded suffix, identifies the first
failed original revision, and retains the existing Command-specific blocker
Diagnostics. Discarded records are not stored in the resulting State.
Correction Results and replayed or discarded suffix reports are never persisted.

## Information safety

Correction adds no semantic shortcut. Existing phase, exact ownership, legal-
card, turn, Declaration, Matador, Skat, Discard, public-hand, continuation,
Game-end, and information-policy rules remain authoritative for the replacement
and every suffix Command.

Removing or replacing promotion can therefore make later Retrospective private-
hand entry invalid. Replacing an earlier Play rederives every later Turn and
Trick. Replacing a Declaration can invalidate Skat, Discards, Ouvert public hands,
and Plays. Replacing a public hand can invalidate a later owner Play. The history
layer never infers ownership, Skat, Discards, private hands, public hands, events,
or endings to preserve a suffix.

Search Worlds, simulation ownership, inference results, proof states,
Provenance attachments, Recommendations, and workflow Results are not caller
facts and cannot enter correction through a Session Command.

## No branching or Redo stack

Version 1 has one active linear Log. Removed and discarded records exist only in
the operation Result. There is no branch identity, alternate head, merge,
automatic retry, or stored Redo stack. A caller may retain returned records and
submit a later explicit operation, but the Session State stores none of them.
Persistence stores only that active State plus optional caller-supplied frozen
Checkpoints, never a Result, suffix, or Redo value.

## Checkpoint lineage

`SessionCheckpointLineageV1` contains only:

```text
session_checkpoint_lineage_version
relationship
session_id
checkpoint_revision
state_revision
```

`classify_session_decision_checkpoint_v1()` replay-validates the State and, when
the State reaches the Checkpoint revision, reconstructs that exact accepted
prefix and the expected information-safe Position Request. It compares the full
expected Checkpoint, including Mode, decision indexes, actor, seat, relative map,
and frozen Request.

Relationships are:

* `current`: equal revisions and exact Checkpoint reproduction;
* `ancestor`: a later State has an unchanged effective prefix through the
  Checkpoint;
* `future`: the State revision is below the Checkpoint revision;
* `diverged`: the State reaches the Checkpoint revision but its actual prefix no
  longer reproduces the frozen Checkpoint.

A correction at or before the Checkpoint normally diverges, but may remain
current or ancestor when the complete effective frozen Checkpoint is exactly
equal. A correction strictly after it remains ancestor.

Undo and correction never mutate, delete, rewrite, or attach data to a
Checkpoint. Its source revision and Request remain frozen. Issue #157 derives an
actual-card Decision Observation from the accepted Log and automatically
collects exact Checkpoints in CLI orchestration without changing this rule.

Strict Resume reconstructs optional persisted Checkpoints and recomputes each
`current`, `ancestor`, `future`, or `diverged` relationship against the resumed
active State. Lineage Results themselves are derived and are not persisted.

## Export compatibility

History edits execute no export automatically and cache no Request. Callers may
pass the resulting active State to the existing Position or Historical Session
exporter. Each exporter replays that edited State normally and uses its recomputed
readiness. Removed and discarded Commands cannot influence the export because
they are absent from the active accepted Log. Existing frozen Checkpoints remain
separate values.

A resumed State is the same `SessionStateV1` and remains compatible with Undo,
correction, lineage classification, and both exporters. Persistence Load/Resume
does not automatically run a history operation, export a Request, or execute
analysis. See [Session persistence and Resume](session_persistence_and_resume.md).

## Determinism and execution bounds

For equal typed inputs, Undo, correction, State, suffix reports, Diagnostics,
lineage, and serialization are equal. No operation adds random state, current
time, generated identity, fingerprint, environment path, or file path.

One Undo performs at most one source replay and one prefix reconstruction. One
correction performs at most one source replay, one prefix reconstruction, one
replacement application, and one linear suffix pass. One lineage classification
performs at most one source replay, one prefix reconstruction, and one expected-
Request reconstruction.

Each public wrapper invokes its matching internal history operation exactly once
and returns the existing Undo, Correction, or lineage value in a Session Result.
Optional complete provenance and final standalone-Session-Schema validation do
not add replay. These operations run no Search, Immediate Analysis, hidden-card inference,
Multi-Step, Policy Comparison, Historical workflow, Review, Coaching, scoring,
Settlement, Application, file I/O, timeout, or background task.

## Current boundary

The implementation remains under `skat_ai.session_history*` and is exposed
through the additive `skat_ai.api.v1.session` namespace. Issue #157 adds
installed/module/Legacy `session undo` and `session correct`, optimistic file
Save, automatic collection of a newly Position-ready State, lineage display,
examples, and generated scenarios without changing history semantics. Only
applied Undo and applied or partial Correction States are saved; unchanged and
rejected Results do not rewrite the file.

The active boundary remains seven Root workflows, 63 authoritative and packaged
Schemas, 85 generated outputs, and Package version `0.13.0`. The functional
`v0.14.0` milestone is complete pending release preparation. Automatic Redo,
branching/merge, arbitrary Log surgery, GUI/platform/cloud/encryption, and
unrelated pre-v1 gaps remain open. See
[Session CLI and end-to-end capture](session_cli_and_end_to_end_capture.md).
