# Session Decision observations

Issue #157 adds immutable retrospective observation and Checkpoint review-export
contracts. A pre-Play Decision Checkpoint remains frozen. The actual Card is
derived later from the authoritative accepted Command Log and is attached only
to a newly constructed post-game-review Request.

## Observation identity

The independent version-1 identity is:

```text
SESSION_DECISION_OBSERVATION_VERSION = 1
SESSION_DECISION_OBSERVATION_POLICY = first_observed_local_play_after_checkpoint
SESSION_DECISION_OBSERVATION_STATUSES = (
    observed,
    pending,
    future,
    diverged,
    ended_without_play,
)
SESSION_DECISION_OBSERVATION_REASON_CODES = (
    local_play_not_recorded,
    state_before_checkpoint,
    checkpoint_diverged,
    game_ended_before_local_play,
)
```

Canonical status and reason order is stable.

## Immutable observation

`SessionDecisionObservationV1` contains:

```text
session_decision_observation_version
status
session_id
checkpoint_revision
state_revision
decision_index
lineage
observed_play_revision
actual_card
reason_codes
```

`lineage` is one immutable `SessionCheckpointLineageV1`. Status relationships
are exact:

| Status | Required lineage | Card and Play revision | Reason code |
| --- | --- | --- | --- |
| `observed` | `ancestor` | Both non-null; the accepted Play follows the Checkpoint and does not exceed the State revision. | none |
| `pending` | `current` or `ancestor` | both null | `local_play_not_recorded` |
| `future` | `future` | both null | `state_before_checkpoint` |
| `diverged` | `diverged` | both null | `checkpoint_diverged` |
| `ended_without_play` | `ancestor` | both null | `game_ended_before_local_play` |

Decision indexes remain one-based and bounded by 30. The observation duplicates
neither the Checkpoint nor the State document.

## Derivation

`observe_session_decision_checkpoint_v1(state=..., checkpoint=...)` validates
the exact types, replay-validates the State through lineage classification, and
classifies the frozen Checkpoint once. A `future` or `diverged` relationship
returns immediately.

For a current or ancestor Checkpoint, the builder inspects accepted records after
the source revision in order. The first accepted `record_play` must be by the
frozen acting Player and becomes `observed`, with that accepted revision and
exact Card. An accepted Game End encountered first becomes
`ended_without_play`. If neither occurs, the status is `pending`.

The builder does not infer a Card, inspect a future State, mutate the Checkpoint,
or execute analysis. A turn-order disagreement in otherwise accepted valid
history is an invariant failure rather than guessed ownership.

## Checkpoint review export

The independent review-export identity is:

```text
SESSION_CHECKPOINT_REVIEW_EXPORT_VERSION = 1
SESSION_CHECKPOINT_REVIEW_EXPORT_POLICY = frozen_request_plus_observed_card
SESSION_CHECKPOINT_REVIEW_EXPORT_STATUSES = (
    available,
    unavailable,
    diverged,
)
```

`SessionCheckpointReviewExportV1` contains:

```text
session_checkpoint_review_export_version
status
session_id
checkpoint_revision
observation_revision
observation
request
diagnostics
```

An `available` export requires an `observed` Decision Observation, one immutable
Position `RequestDocumentV1`, and no Diagnostics. `pending`, `future`, and
`ended_without_play` produce `unavailable` with no Request. A diverged
observation produces `diverged` with no Request.

## Review isolation

`export_session_checkpoint_review_request_v1(state=..., checkpoint=...)`
derives one observation. It returns the normal unavailable or diverged result
without building a Request unless the observation is `observed`.

For an observed decision it copies the exact frozen Checkpoint Position document
and changes only:

```text
analysis_mode = post_game_review
actual_card_played = observed actual Card
```

The existing Position builder validates the result. The frozen recommendation
method, Search settings, local hand, completed and current Tricks, authorized
public hands, legitimately known Skat, and all other decision-time settings are
preserved exactly. No later private Session fact enters the Request. The observed
Card is retrospective evidence, not a ground-truth optimal label.

The export contains no analysis Result, does not mutate or duplicate the
Checkpoint, and does not execute Position Analysis. The CLI `session review`
separately executes the existing Position Application once only when this export
is available.

## Public Session API

The canonical `SESSION_API_OPERATIONS` tuple appends:

```text
observe_checkpoint
export_checkpoint_review
```

The stable `skatmind.api.v1.session` namespace preserves its first 52 exports and
then appends, before `files`:

```text
SESSION_DECISION_OBSERVATION_VERSION
SESSION_CHECKPOINT_REVIEW_EXPORT_VERSION
SessionDecisionObservationV1
SessionCheckpointReviewExportV1
observe_session_decision_checkpoint
export_session_checkpoint_review_request
```

The public wrappers are:

```python
observe_session_decision_checkpoint(
    *,
    state,
    checkpoint,
    options=SessionApiOptionsV1(),
)

export_session_checkpoint_review_request(
    *,
    state,
    checkpoint,
    options=SessionApiOptionsV1(),
)
```

They return `SessionApiResultV1` operation `observe_checkpoint` with
`SessionDecisionObservationV1`, or operation `export_checkpoint_review` with
`SessionCheckpointReviewExportV1`. `SessionApiVersionInfoV1` reports the
observation and review-export versions additively.

## Provenance

Both public operations support the existing default-omitted Session Provenance.
Observation provenance covers the frozen Checkpoint, source State, lineage,
status/reasons, accepted observed Play revision, and actual Card when available.
Review-export provenance covers the frozen Request, observation, retrospective
Card attachment, generated post-game-review Request, status, and Diagnostics.

The frozen decision-time Request remains available from `current_decision`; the
actual Card uses origin `retrospective_attachment`. Later private facts remain
outside the review Request. Redacted provenance must retain complete exact-value
coverage, and provenance construction does not rerun observation or export.

## Automatic collection relationship

The internal Checkpoint collection contract has policy
`exact_position_ready_revision_and_request` and statuses `collected`, `existing`,
and `unavailable`. It freezes exact Position-ready Requests, deduplicates equal
Checkpoints, permits different Requests at one revision, mutates no input, and
never starts analysis.

Session CLI mutation captures the source decision immediately before an accepted
local Play, so the later accepted `record_play` is available for deterministic
observation. Undo and correction retain immutable Checkpoints and can therefore
make their lineage current, ancestor, future, or diverged without rewriting
their source revision or Request.

See [Session CLI and end-to-end capture](session_cli_and_end_to_end_capture.md)
for collection, persistence, and review command behavior.

## Boundaries

Decision Observations and review exports are derived values. They are not stored
in Session State or persistence, and analysis Results are not persisted. They add
no hidden-card inference, optimal label, causal attribution, final-outcome
evidence, new Root workflow, GUI, platform adapter, cloud transport, or encryption
contract.
