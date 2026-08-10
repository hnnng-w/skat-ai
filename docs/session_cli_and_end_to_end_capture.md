# Session CLI and end-to-end capture

Issue #157 completes the functional `v0.14.0` Live and Retrospective Session
capture milestone. It adds stable public Session file transport, one additive
Session CLI command family, automatic Decision Checkpoint collection,
Checkpoint-based review, explicit Position and Historical execution, and a
phase-aware Assistant. Issue #158 completed Package version `0.14.0` and Release-
documentation preparation without changing this behavior; the maintainer
subsequently published the Release manually at commit `d5589f8`.

The Session layer still does not add an eighth Engine Root workflow. It exports
existing Position and Historical Requests and, only for explicit execution
subcommands, passes those Requests to the existing Application once.

## Public Session file API

The stable file-transport namespace is:

```text
PUBLIC_SESSION_FILE_API_VERSION = 1
PUBLIC_SESSION_FILE_API_NAMESPACE = skat_ai.api.v1.session.files
PUBLIC_SESSION_FILE_API_COMPATIBILITY_POLICY = additive_until_v1_0
SESSION_FILE_API_OPERATIONS = (save, load)
```

`files` is appended to `skat_ai.api.v1.session.__all__`. The exact
`skat_ai.api.v1.session.files.__all__` order is:

```text
PUBLIC_SESSION_FILE_API_VERSION
PUBLIC_SESSION_FILE_API_NAMESPACE
PUBLIC_SESSION_FILE_API_COMPATIBILITY_POLICY
SESSION_FILE_API_OPERATIONS
SessionFileApiVersionInfoV1
SessionFileApiOptionsV1
SessionFileApiResultV1
SessionPersistenceWriteResultV1
get_session_file_api_version_info_v1
save_session_file
load_session_file
serialize_session_file_result
```

`SessionPersistenceWriteResultV1` is the exact existing persistence type.
Fingerprint builders, low-level persistence codecs, and temporary-file helpers
remain private.

`SessionFileApiVersionInfoV1` reports API contract, Public Session API, Public
Session File API, and persistence versions plus namespace, compatibility policy,
and canonical operations. Package and Schema versions are independent and are
not fields. `SessionFileApiOptionsV1` contains only the strict Boolean
`validate_output = true`. Disabling it skips final file-Result Schema validation
only; strict parsing, resume, replay, fingerprints, and conflict checks remain
mandatory.

`SessionFileApiResultV1` contains:

```text
api_contract_version
public_session_api_version
public_session_file_api_version
operation
value
```

The exact operation/value pairs are `save` with
`SessionPersistenceWriteResultV1` and `load` with `SessionResumeResultV1`. A
Result retains no path, timestamp, request ID, or transport metadata.

The public operations are:

```python
save_session_file(
    file_path,
    document,
    *,
    expected_content_fingerprint,
    options=SessionFileApiOptionsV1(),
)

load_session_file(
    file_path,
    *,
    options=SessionFileApiOptionsV1(),
)

serialize_session_file_result(result)
```

Save preserves the existing `saved`, `unchanged`, and `conflict` outcomes,
strict expected-content-fingerprint compare-and-swap, invalid-existing-file
protection, and same-directory atomic replacement. Load preserves strict UTF-8,
duplicate-key, finite-number, fingerprint, accepted-Log replay, and Checkpoint
lineage validation. Neither operation executes a Session operation or Engine
workflow, and neither Result retains the caller path.

## CLI identity and dispatch

Installed Session CLI contract version `1` defines:

```text
SESSION_CLI_CONTRACT_VERSION = 1
SESSION_CLI_COMMAND = session
SESSION_CLI_SUBCOMMANDS = (
    new,
    show,
    apply,
    undo,
    correct,
    checkpoint,
    export-position,
    export-historical,
    analyze,
    review,
    finalize,
    assistant,
)
SESSION_CLI_PERSISTENCE_POLICY = load_operate_compare_and_swap_save
SESSION_CLI_ANALYSIS_POLICY = export_then_existing_application_once
SESSION_CLI_AUTOMATIC_CHECKPOINT_POLICY = collect_without_automatic_analysis
```

All three supported forms use the same Session parser and implementation:

```powershell
skat-ai session --help
python -m skat_ai session --help
python main.py session --help
```

A leading `session` token selects the separate Session parser. Every other
invocation continues through the unchanged Root parser. There is one Console
Script, no second alias, no Session Root workflow, and no migration of the Root
parser to subparsers.

## Common options

Every applicable non-Assistant subcommand accepts an explicit `--session PATH`.
There is no default path or Session directory.

The common options are:

| Option | Meaning |
| --- | --- |
| `--session PATH` | Required private Session persistence file. |
| `--output PATH` | Optional for `new`, `show`, `apply`, `undo`, `correct`, and `checkpoint`; required for both exports, `analyze`, `review`, and `finalize`. |
| `--quiet` | Suppress successful human-readable output and file confirmations; errors remain visible. |
| `--include-provenance` | Include public Session provenance in Session operation JSON or existing Root provenance in Engine Result JSON. It is not accepted by `show` or `assistant`. |

Position-related `apply`, `undo`, `correct`, `checkpoint`, `export-position`,
and `analyze` accept:

```text
--samples N
--seed N
--opponent-strategy basic|random
--recommendation-method immediate_expected_value|bounded_search|auto
--search-budget-profile PROFILE
```

The defaults are 100 samples, seed `0`, basic opponent strategy, omitted
recommendation method, and `interactive_v1`. Existing sample bounds,
recommendation methods, and Search budget identifiers remain authoritative.

`finalize` accepts the existing Historical execution controls:

```text
--historical-decision-snapshots
--historical-game-review
--historical-search-review
--historical-replay-coaching
--search-seed N
--search-budget-profile PROFILE
--samples N
--seed N
```

## Subcommands

### `new`

```powershell
skat-ai session new --session SESSION.json --input CREATE.json
```

The strict creation object contains exactly `session_id`, `capture_mode`,
`local_player_id`, and `players`. It calls public `create_session()` once, builds
one persistence document, and saves with a null expected fingerprint. An existing
target is a normal Save conflict and exits with Code `1`; no parent directory is
created. Optional `--output` contains the `SessionApiResultV1` creation Result.

### `show`

```powershell
skat-ai session show --session SESSION.json
```

`show` loads and strictly resumes once, performs no Save or analysis, and reports
Session ID, revision, Mode, phase, both readiness values, Players/seats,
Checkpoint count, each Checkpoint index/revision/decision/lineage, observation
status, and an available observed Card. Optional `--output` contains the public
`SessionFileApiResultV1` load Result.

### `apply`

```powershell
skat-ai session apply --session SESSION.json --input COMMAND.json
```

The command is strict JSON parsed by `parse_session_command()`. Applied,
rejected, and revision-conflict outcomes remain typed Session Results. Only an
applied State is persisted. Rejected and revision-conflict Results exit with
Code `0` and do not rewrite the file. Checkpoints are collected around accepted
local Plays as described below.

### `undo`

```powershell
skat-ai session undo --session SESSION.json --target-revision N
```

Undo calls public `rewind_session()` once. Only `applied` is saved; `unchanged`,
`rejected`, and revision-conflict outcomes are normal Code `0` Results. The
active Checkpoint tuple is retained and lineage is recomputed on resume.

### `correct`

```powershell
skat-ai session correct --session SESSION.json --input CORRECTION.json
```

The strict correction object contains exactly
`session_history_edit_version`, `expected_revision`, `target_revision`, and
`replacement_command`. Applied and partial corrected States are saved.
Unchanged and rejected Results do not rewrite the file. Replayed, discarded, and
first-failed source records retain the existing correction semantics.

### `checkpoint`

```powershell
skat-ai session checkpoint --session SESSION.json
```

This constructs Position Export Options, collects or reuses the exact current
Checkpoint, and saves only when collection status is `collected`. `existing` and
`unavailable` are normal Code `0` outcomes. No analysis executes. Optional
`--output` contains the corresponding public Session API Checkpoint or
unavailable Position-export Result.

### `export-position`

```powershell
skat-ai session export-position \
    --session SESSION.json \
    --output POSITION_REQUEST.json
```

This calls public Position export once and writes the serialized
`SessionApiResultV1`. An available export collects and persists an exact matching
Checkpoint. Unavailability is Code `0`. Position Analysis does not execute.

### `export-historical`

```powershell
skat-ai session export-historical \
    --session SESSION.json \
    --output HISTORICAL_REQUEST.json
```

This calls public Historical export once and writes the serialized Session
Result. Unavailability is Code `0`. It neither executes the Historical workflow
nor modifies the Session file.

### `analyze`

```powershell
skat-ai session analyze \
    --session SESSION.json \
    --output POSITION_RESULT.json
```

This exports one Position-ready decision, collects or reuses the exact pre-Play
Checkpoint, persists a newly collected Checkpoint before execution, and invokes
the existing Position Application once. A persistence conflict aborts before
analysis. The output is the existing Root Position Result, including Root field
provenance when requested. Position unavailability is a normal Session Result,
executes no Application workflow, and exits with Code `0`.

### `review`

```powershell
skat-ai session review \
    --session SESSION.json \
    --checkpoint-index N \
    --output REVIEW_RESULT.json
```

The index is zero-based in the canonical persisted Checkpoint order. Review
derives one Decision Observation and exports one frozen-request-plus-observed-
Card post-game-review Request. It executes the existing Position Application
once only when the review export is `available`. Pending, future, diverged, and
ended-without-play observations write the normal unavailable Session Result and
exit with Code `0`. Review never modifies the Session or Checkpoint.

### `finalize`

```powershell
skat-ai session finalize \
    --session SESSION.json \
    --output HISTORICAL_RESULT.json
```

This exports once and executes the existing Historical Application once only
when Historical readiness is available. It supports the existing Snapshot,
Immediate Review, Search Review, Replay Coaching, Search seed/profile, and
Immediate sample/seed controls. The output is the existing Root Historical
Result. Unavailability is Code `0`; finalization does not modify the Session.

### `assistant`

```powershell
skat-ai session assistant --session SESSION.json
```

The Assistant creates a missing Session through explicit prompts or resumes an
existing file. It displays phase, revision, readiness, and concise Checkpoint
status and offers only phase-valid actions for metadata, Deal Card, Skat,
Declarer, Declaration, Discard, Play, public hand, continuation event, Game End,
promotion, Undo, correction, Checkpoint, analysis, review, finalization, and
quit. Applied State-changing actions are saved immediately and collect exact
Checkpoints. Complex Declaration, continuation, Game-end, and correction values
use strict JSON prompts. The Assistant does not perform natural-language rule
interpretation, infer hidden Cards, or print complete private opponent hands.
EOF exits successfully after preserving the last successful save.

## Automatic Decision Checkpoints

Automatic collection uses internal version `1`, policy
`exact_position_ready_revision_and_request`, and statuses `collected`,
`existing`, and `unavailable`. It exports the current Position once, freezes the
exact Request when available, deduplicates equal Checkpoints, and permits
different Requests at the same revision when their analysis options differ.

For `apply`, `undo`, and `correct`, the CLI inspects source and resulting States.
It captures a Position-ready source immediately before an accepted local
`record_play`, and captures a Position-ready resulting State. The State and
updated canonical Checkpoint tuple are written together through one optimistic
atomic Save. Ordinary collection never starts analysis. `checkpoint`,
`export-position`, and `analyze` also collect or reuse the exact requested
Position configuration.

Observed-card derivation and review isolation are documented in
[Session Decision observations](session_decision_observations.md).

## Persistence and conflicts

Every mutating invocation follows one load-operate-build-save cycle:

1. Strictly load or explicitly create one persistence document.
2. Retain its content fingerprint.
3. Perform one Session operation.
4. Build one replacement persistence document.
5. Save with the retained fingerprint as the expected value.
6. Return Code `1` if compare-and-swap reports `conflict`.

There is no force overwrite, invalid-file overwrite, default path, hidden reload,
retry loop, merge, backup file, or automatic directory creation. A conflict
leaves the target unchanged. Atomic replacement remains same-directory and does
not claim distributed locking.

## Privacy

Human-readable summaries may show Session identity, revision, Mode, phase,
readiness, operation status, Diagnostics, Player IDs and seats, hand sizes,
public Plays, Checkpoint identity/lineage, observed actual Cards, and Save status.
They do not print complete Retrospective hands, exact hidden opponent hands, the
full private Skat, complete frozen Requests, fingerprints, provenance entries, or
file contents by default.

Explicit `--output` JSON remains private caller-controlled data. A persistence
file may contain all Retrospective hands, Skat, Discards, accepted Plays, and
local-private frozen Position Requests. It receives no content redaction. The
file API Result omits paths, but that does not make the persistence document
public-safe.

## Errors and Exit Codes

The Session command family preserves the stable process codes:

```text
0 = success and normal Session statuses
1 = expected execution, resource, invalid-file, filesystem, or Save-conflict failure
2 = CLI syntax or usage failure
```

Rejected Commands, revision-conflict Command Results, unavailable exports,
unchanged Undo, partial Correction, pending observations, and diverged
Checkpoints are normal typed Results. Parser misuse uses Code `2`; persistence
conflicts and filesystem failures use Code `1`. Installed, module, and Legacy
forms use equal wording.

## Examples and generated scenarios

Issue #157 adds exactly six repository development examples:

```text
examples/session_create_live.json
examples/session_create_retrospective.json
examples/session_command_record_play.json
examples/session_correction_record_play.json
examples/session_live_persistence.json
examples/session_retrospective_persistence.json
```

They cover strict creation, one Play Command, one correction, and canonical Live
and Retrospective persistence with valid embedded fingerprints. They are not
installed Package Data.

Eight deterministic Session scenarios are appended after the previous 77:

```text
session_live_create
session_live_apply_and_resume
session_live_analyze_with_checkpoint
session_live_observed_card_review
session_undo_and_partial_correction
session_persistence_conflict
session_retrospective_export
session_retrospective_finalize
```

The active total is 85. Session operation outputs validate against the single
`session.schema.json`; executed Position and Historical Results validate against
`output.schema.json`. The previous 77 scenarios and published `v0.13.0` facts
remain unchanged. The active authoritative and packaged Schema count remains 63.

## Distribution and boundaries

Wheel and sdist clean-install validation covers the public file namespace,
Save/Load, installed and module Session help, `new`/`apply`/`show`, Session-
triggered Position analysis, observation/review, Retrospective finalization, and
an injected-I/O Assistant smoke flow. Legacy parity is validated from the
repository checkout. There is still exactly one Console Script, and Package
version is `0.14.0`.

Issue #157 adds no GUI or browser UI, online-platform adapter, browser extension,
website scraping, cloud synchronization, distributed lock, collaborative merge,
encryption or key management, automatic backup policy, default Session directory,
or natural-language rule inference. Broader provenance, Search, Claim,
Settlement, and Coaching gaps remain open independently.
